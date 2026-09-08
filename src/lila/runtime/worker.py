"""Worker credentials live only in memory and an explicitly inherited pipe."""
import hmac
import json
import os
import secrets
import subprocess
import sys
import threading
import time
from uuid import uuid4
import msvcrt
from lila.security.sessions import AuthError
from lila.runtime.python_process import command

_spawn_lock = threading.Lock()


class WorkerRegistry:
    def __init__(self):
        self.lock = threading.Lock()
        self.generation = 0
        self.current = None

    def register(self):
        with self.lock:
            self.generation += 1
            self.current = {"worker_id":str(uuid4()),"generation":self.generation,"token":secrets.token_urlsafe(32),"last_seen":time.monotonic()}
            return dict(self.current)

    def authenticate(self, secret, generation):
        with self.lock:
            if not isinstance(secret,str) or not secret.isascii() or not self.current or generation != self.generation or not hmac.compare_digest(self.current["token"],secret):
                raise AuthError("STALE_WORKER")
            self.current["last_seen"] = time.monotonic()
            return self.current["worker_id"]

    def healthy(self):
        with self.lock:
            return bool(self.current and time.monotonic()-self.current["last_seen"] < 5)

    def fence(self):
        with self.lock:
            self.current = None


class WorkerProcess:
    def __init__(self, registry):
        self.registry, self.process = registry, None

    def start(self, port, pin, ca_path, *, boot=None):
        if self.process and self.process.poll() is None:
            raise RuntimeError("worker already running")
        boot = dict(boot) if boot is not None else self.registry.register()
        boot.update(port=port,server_spki_pin=pin,ca_path=str(ca_path))
        with _spawn_lock:
            read_fd, write_fd = os.pipe()
            handle = msvcrt.get_osfhandle(read_fd)
            try:
                os.set_handle_inheritable(handle,True)
                startup = subprocess.STARTUPINFO()
                startup.lpAttributeList = {"handle_list":[handle]}
                self.process = subprocess.Popen(command("lila.runtime.worker_process",str(handle)),
                    close_fds=True,startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW,
                    stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                os.write(write_fd,json.dumps(boot).encode())
            except BaseException:
                self.registry.fence()
                if self.process and self.process.poll() is None:
                    self.process.terminate()
                    self.process.wait(timeout=10)
                raise
            finally:
                os.set_handle_inheritable(handle,False)
                os.close(read_fd)
                os.close(write_fd)

    def close(self):
        self.registry.fence()
        if self.process and self.process.poll() is None:
            # Worker exits on its next fenced heartbeat; force only after quiescence timeout.
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                self.process.wait(timeout=5)
