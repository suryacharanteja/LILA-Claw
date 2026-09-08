"""Outer supervisor keeps coordinator crashes separate from its own lifecycle."""
import json
import subprocess
import sys
import time
from uuid import UUID,uuid5
from lila.runtime.control_pipe import request
from lila.runtime.installation import load
from lila.runtime.supervisor import Supervisor
from lila.security.windows import OwnerLock,write_private
from lila.runtime.python_process import command
from lila.runtime.worker import WorkerRegistry,WorkerProcess


class ProcessSupervisor:
    def __init__(self,root):
        self.root = root
        self.config,_ = load(root)
        if not self.config["trust_confirmed"]:
            raise PermissionError("CurrentUser Root setup confirmation required")
        self.owner = OwnerLock(str(uuid5(UUID(self.config["install_id"]),"supervisor")))
        self.process = None
        self.worker = WorkerProcess(WorkerRegistry())
        self.state = Supervisor(self._persist_stop,lambda:None)

    def _persist_stop(self):
        write_private(self.root/"runtime-state.json",b'{"intentional_stop":true}')

    def _spawn(self):
        self.process = subprocess.Popen(command("lila.runtime.coordinator_process","--data-dir",str(self.root)),
            close_fds=True,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW)
        deadline = time.monotonic()+15
        while True:
            try:
                self.status()
                break
            except (OSError,RuntimeError):
                if self.process.poll() is not None or time.monotonic()>deadline:
                    raise RuntimeError("coordinator startup failed")
                time.sleep(0.1)
        boot = request(self.config["install_id"],"worker_boot")
        self.worker.start(boot["port"],boot["server_spki_pin"],boot["ca_path"],boot=boot)

    def start(self):
        if not self.owner.acquire():
            return False
        write_private(self.root/"runtime-state.json",b'{"intentional_stop":false}')
        try:
            self._spawn()
        except BaseException:
            self.close()
            raise
        return True

    def status(self):
        result = request(self.config["install_id"],"status")
        if not self.process or result["coordinator_pid"] != self.process.pid or not result["https_live"]:
            raise RuntimeError("unexpected coordinator instance")
        result["worker_pid"] = self.worker.process.pid if self.worker.process else None
        return result

    def _intentional(self):
        try:
            return json.loads((self.root/"runtime-state.json").read_text()).get("intentional_stop") is True
        except (FileNotFoundError,ValueError):
            return False

    def monitor(self):
        while True:
            if self._intentional():
                return
            healthy = False
            if self.process.poll() is None:
                try:
                    result = self.status()
                    healthy = bool(result["worker_healthy"] and self.worker.process and self.worker.process.poll() is None)
                except (OSError,RuntimeError,TimeoutError):
                    pass
            delay = self.state.health(healthy,time.monotonic())
            if delay is not None:
                self._stop_child()
                if self._intentional():
                    return
                time.sleep(delay)
                if self._intentional():
                    return
                self._spawn()
            if self.state.intervention_required:
                write_private(self.root/"supervisor-status.json",b'{"state":"DEGRADED","blockers":["INTERVENTION_REQUIRED"]}')
                return
            time.sleep(2)

    def _stop_child(self):
        try:
            request(self.config["install_id"],"worker_fence")
        except OSError:
            pass
        self.worker.close()
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=10)

    def close(self):
        if self.process and self.process.poll() is None:
            try:
                request(self.config["install_id"],"quit")
                self.process.wait(timeout=12)
            except (OSError,RuntimeError,TimeoutError,subprocess.TimeoutExpired):
                self._stop_child()
        self.worker.close()
        self.owner.close()
