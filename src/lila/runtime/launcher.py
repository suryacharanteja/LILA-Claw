"""User-session development launcher. No external agent actions at M1."""
import argparse
import json
import os
from pathlib import Path
import webbrowser
from lila.runtime.installation import prepare, load, confirm_trust
from lila.runtime.control_pipe import request
from lila.runtime.process_supervisor import ProcessSupervisor


def open_authenticated(config):
    # Narrow bootstrap-only exception recorded in the M1 decision approval.
    # Retain a per-installation opt-out; never print or log the capability URL.
    if not config.get("allow_fragment_launch",False):
        raise PermissionError("automatic bootstrap launch is disabled for this installation")
    webbrowser.open(request(config["install_id"],"launch")["url"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation",choices=["setup","run","open","status","quit"])
    parser.add_argument("--data-dir",type=Path,default=Path(os.environ["LOCALAPPDATA"])/"LILAClaw")
    args = parser.parse_args()
    root = args.data_dir.resolve()
    if args.operation == "setup":
        if (root/"installation.json").exists():
            config,_ = load(root)
        else:
            config = prepare(root)
        if config["trust_confirmed"]:
            print("This installation has already completed trust setup.")
            return
        print(f"Prepared installation {config['install_id']}. CA thumbprint: {config['ca_thumbprint']}")
        print("Setup adds this installation's localhost-only CA to your CurrentUser Root store. It does not change LocalMachine trust.")
        if input("Type INSTALL to install this certificate: ") != "INSTALL":
            print("Trust not installed. Runtime remains unavailable.")
            return
        confirm_trust(root,confirmation=True)
        return
    config,_ = load(root)
    if args.operation != "run":
        if args.operation == "open":
            open_authenticated(config)
            return
        result = request(config["install_id"],"launch" if args.operation=="open" else args.operation)
        print(json.dumps(result))
        return
    supervisor = ProcessSupervisor(root)
    if not supervisor.start():
        open_authenticated(config)
        return
    try:
        import time
        deadline = time.monotonic()+15
        while True:
            try:
                supervisor.status()
                break
            except OSError:
                if time.monotonic()>deadline:
                    raise RuntimeError("coordinator startup timeout")
                time.sleep(0.1)
        if config.get("allow_fragment_launch",False):
            open_authenticated(config)
        else:
            print("Runtime started. Automatic UI bootstrap awaits the documented design clarification.")
        supervisor.monitor()
    except KeyboardInterrupt:
        supervisor._persist_stop()
    finally:
        supervisor.close()


if __name__ == "__main__":
    main()
