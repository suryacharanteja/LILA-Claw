import json
import os
import time
from lila.runtime.installation import prepare
from lila.runtime.process_supervisor import ProcessSupervisor
from lila.runtime.control_pipe import request
from lila.security.windows import write_private


def test_three_process_topology_and_intentional_shutdown(tmp_path):
    root = tmp_path/"installation"
    config = prepare(root)
    # Isolated backend test fixture: no Windows certificate-store mutation or browser claim.
    config["trust_confirmed"] = True
    write_private(root/"installation.json",json.dumps(config).encode())
    supervisor = ProcessSupervisor(root)
    try:
        assert supervisor.start()
        deadline = time.monotonic()+10
        while True:
            try:
                status = supervisor.status()
                break
            except OSError:
                if time.monotonic()>deadline:
                    raise
                time.sleep(0.1)
        assert len({os.getpid(),status["coordinator_pid"],status["worker_pid"]}) == 3
        assert supervisor.process.pid == status["coordinator_pid"]
        assert status["https_live"]
        assert not ProcessSupervisor(root).start()
        request(config["install_id"],"quit")
        supervisor.monitor()
        supervisor.process.wait(timeout=12)
        assert supervisor.process.returncode == 0
        assert supervisor._intentional()
    finally:
        supervisor.close()
