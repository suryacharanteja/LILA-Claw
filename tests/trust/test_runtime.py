import json
import socket
import time
import httpx
import pytest
from lila.runtime.installation import prepare
from lila.runtime.service import Runtime
from lila.runtime.control_pipe import request
from lila.security.tls import client_context
from lila.security.sessions import AuthError


def test_real_runtime_port_collision_worker_pipe_quit(tmp_path):
    root = tmp_path/"installation"
    config = prepare(root)
    with pytest.raises(PermissionError):
        Runtime(root)
    occupied = socket.socket()
    occupied.bind(("127.0.0.1",0))
    occupied.listen()
    port = occupied.getsockname()[1]
    runtime = Runtime(root,require_trust=False,preferred_port=port,embedded_test_worker=True)
    try:
        assert runtime.start()
        assert runtime.port != port
        duplicate = Runtime(root,require_trust=False)
        assert not duplicate.start()
        with httpx.Client(verify=client_context(root/"tls"),trust_env=False) as client:
            url = f"https://127.0.0.1:{runtime.port}"
            assert client.get(url+"/api/v1/health").json() == {"live":True}
            launch = request(config["install_id"],"launch")
            token = launch["url"].split("#bootstrap=")[1]
            assert client.post(url+"/api/v1/auth/bootstrap",json={"token":token},headers={"Origin":url}).status_code == 200
            assert client.get(url+"/api/v1/health").json()["blockers"]
            assert client.post(url+"/internal/v1/health",json={},headers={"X-Lila-Generation":"1"}).status_code == 403
        deadline = time.monotonic()+5
        while runtime.workers.current["last_seen"] == runtime.workers.current.get("initial_seen",0) and time.monotonic()<deadline:
            time.sleep(0.05)
        time.sleep(2.2)
        assert runtime.worker.process.poll() is None
        assert runtime.workers.healthy()
        old = dict(runtime.workers.current)
        runtime.worker.close()
        with pytest.raises(AuthError):
            runtime.workers.authenticate(old["token"],old["generation"])
        assert request(config["install_id"],"quit")["state"] == "STOPPING"
        assert json.loads((root/"runtime-state.json").read_text())["intentional_stop"]
    finally:
        runtime.close()
        occupied.close()
