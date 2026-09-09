"""Single coordinator with user control pipe and separately fenced worker."""
import hashlib
import json
import os
import socket
import threading
import time
from pathlib import Path
import uvicorn
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from lila.api.auth import create_app
from lila.runtime.control_pipe import ControlPipe
from lila.runtime.installation import load
from lila.runtime.supervisor import Supervisor
from lila.runtime.worker import WorkerRegistry, WorkerProcess
from lila.security.sessions import Sessions
from lila.security.tls import server_context, renew_leaf
from lila.security.windows import OwnerLock, write_private
from lila.storage.writer import StoreWriter


def bind_loopback(preferred=43127):
    listener = socket.socket()
    listener.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
    try:
        listener.bind(("127.0.0.1",preferred))
    except OSError as exc:
        if exc.winerror != 10048 and exc.errno != 10048:
            listener.close()
            raise
        listener.bind(("127.0.0.1",0))
    listener.listen(128)
    return listener


class Runtime:
    def __init__(self, root: Path, *, require_trust=True, preferred_port=43127, extension_id=None, embedded_test_worker=False, browser_adapter=None):
        self.root = root
        self.config,self.keys = load(root)
        if require_trust and not self.config["trust_confirmed"]:
            raise PermissionError("CurrentUser Root setup confirmation required")
        self.owner = OwnerLock(self.config["install_id"])
        self.preferred_port = preferred_port
        self.extension_id = extension_id
        self.embedded_test_worker = embedded_test_worker
        self.browser_adapter = browser_adapter
        self.workers = WorkerRegistry()
        self.worker = WorkerProcess(self.workers)
        self.shutdown = threading.Event()
        self.supervisor = Supervisor(self._intentional_stop,self.workers.fence)
        self.resources = []
        self.thread = None
        self.pipe = None
        self.server = None
        self.listener = None

    def _intentional_stop(self):
        write_private(self.root/"runtime-state.json",json.dumps({"intentional_stop":True}).encode())

    def status(self):
        return {"state":self.supervisor.state,"blockers":self.supervisor.blockers+["EXECUTION_NOT_IMPLEMENTED"],"port":self.port,"coordinator_pid":os.getpid(),"worker_pid":self.worker.process.pid if self.worker.process else None,"worker_healthy":self.workers.healthy(),"https_live":bool(self.thread and self.thread.is_alive())}

    def control(self, operation):
        if operation == "launch":
            return {"url":f"https://127.0.0.1:{self.port}/#bootstrap={self.sessions.issue_bootstrap()}"}
        if operation == "status":
            return self.status()
        if operation == "worker_boot":
            boot = self.workers.register()
            boot.update(port=self.port,server_spki_pin=self.pin,ca_path=str(self.root/"tls/ca.pem"))
            return boot
        if operation == "worker_fence":
            self.workers.fence()
            return {"fenced":True}
        self.supervisor.quit()
        self.shutdown.set()
        return {"state":"STOPPING"}

    def start(self):
        if not self.owner.acquire():
            return False
        try:
            renew_leaf(self.root/"tls")
            for kind in ("business","auth"):
                writer = StoreWriter(self.root/f"{kind}.db",self.keys[kind],kind)
                self.resources.append(writer)
            self.sessions = Sessions(self.resources[1],self.keys["session_hash"])
            from lila.domain.service import Domain
            from lila.domain.artifacts import Artifacts
            self.domain = Domain(self.resources[0],self.keys["audit"],
                readiness=lambda:([] if self.workers.healthy() else ['WORKER_UNAVAILABLE'])+([] if self.browser_adapter is not None else ['BROWSER_UNAVAILABLE']),
                capability=lambda account,domain,tab:self.browser_adapter is not None and self.browser_adapter.capability(account,domain,tab) is True)
            self.domain.verify_audit()
            self.domain.artifacts = Artifacts(self.domain,self.root/"objects",self.keys["artifact_wrap"])
            self.domain.recover()
            from lila.domain.ai import AI
            AI(self.domain).recover()
            self.domain.artifacts.recover()
            from lila.domain.documents import Documents
            self.domain.documents = Documents(self.domain,self.domain.artifacts)
            self.domain.documents.recover()
            self.listener = bind_loopback(self.preferred_port)
            self.port = self.listener.getsockname()[1]
            from lila.domain.worker_leases import renew
            app = create_app(self.sessions,self.port,self.status,self.workers,lambda worker:renew(self.domain,worker))
            from lila.api.domain import attach_domain
            attach_domain(app,self.sessions,self.domain,lambda:self.control("quit"))
            from lila.api.checkpoints import attach_checkpoints
            attach_checkpoints(app,self.domain,self.workers)
            from lila.api.extraction import attach_extraction
            attach_extraction(app,self.domain,self.workers)
            from lila.api.ai import attach_ai
            from lila.security.provider_credentials import ProviderCredentials
            attach_ai(app,self.domain,self.sessions,self.workers,ProviderCredentials(self.sessions,self.keys['session_hash']))
            from lila.domain.work import Work
            from lila.api.work import attach_work
            self.work = Work(self.domain,self.browser_adapter)
            attach_work(app,self.domain,self.sessions,self.workers,self.work)
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            from lila.security.pairing import Pairing
            from lila.api.extension import attach_extension
            pairing = Pairing(self.resources[1],Ed25519PrivateKey.from_private_bytes(self.keys["identity"]),self.keys["session_hash"])
            attach_extension(app,self.sessions,pairing,self.port,self.config["install_id"],self.extension_id)
            from fastapi.staticfiles import StaticFiles
            web_root = Path(__file__).resolve().parents[3]/"web/dist"
            if web_root.exists():
                app.mount("/",StaticFiles(directory=web_root,html=True),name="web")
            config = uvicorn.Config(app,access_log=False,log_config=None,log_level="critical",
                ssl_context_factory=lambda *_:server_context(self.root/"tls"),server_header=False,
                timeout_graceful_shutdown=10,ws_max_size=1024*1024)
            self.server = uvicorn.Server(config)
            self.thread = threading.Thread(target=lambda:self.server.run(sockets=[self.listener]),daemon=True,name="lila-http")
            self.thread.start()
            deadline = time.monotonic()+10
            while not self.server.started:
                if not self.thread.is_alive() or time.monotonic()>deadline:
                    raise RuntimeError("HTTPS startup failed")
                time.sleep(0.02)
            cert = x509.load_pem_x509_certificate((self.root/"tls/leaf.pem").read_bytes())
            self.pin = hashlib.sha256(cert.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)).hexdigest()
            if self.embedded_test_worker:
                self.worker.start(self.port,self.pin,self.root/"tls/ca.pem")
            self.pipe = ControlPipe(self.config["install_id"],self.control)
            self.pipe.start()
            write_private(self.root/"runtime-state.json",b'{"intentional_stop":false}')
            return True
        except BaseException:
            self.close()
            raise

    def monitor(self):
        while not self.shutdown.wait(2):
            if not self.embedded_test_worker:
                self.supervisor.health(self.workers.healthy(),time.monotonic())
                continue
            healthy = self.worker.process.poll() is None and self.workers.healthy()
            delay = self.supervisor.health(healthy,time.monotonic())
            if delay is not None:
                self.worker.close()
                if not self.shutdown.wait(delay):
                    self.worker.start(self.port,self.pin,self.root/"tls/ca.pem")

    def close(self):
        self.shutdown.set()
        self.worker.close()
        if self.pipe:
            self.pipe.close()
            self.pipe = None
        if self.server:
            self.server.should_exit = True
        if self.thread:
            self.thread.join(timeout=12)
            if self.thread.is_alive():
                raise RuntimeError("HTTPS shutdown incomplete")
        if self.listener:
            self.listener.close()
        for writer in reversed(self.resources):
            writer.close()
        self.resources.clear()
        self.owner.close()
