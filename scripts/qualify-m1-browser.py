"""Explicitly authorized, temporary CurrentUser trust qualification. No external sites."""
import argparse
import json
import subprocess
import time
from pathlib import Path
from lila.runtime.installation import load, confirm_trust
from lila.runtime.service import Runtime
from lila.security.windows import write_private


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir",type=Path,required=True)
    parser.add_argument("--chrome",type=Path,required=True)
    parser.add_argument("--confirm-current-user-trust",action="store_true")
    args = parser.parse_args()
    if not args.confirm_current_user_trust:
        raise SystemExit("Explicit authorization required to add the prepared CA to CurrentUser Root.")
    root = args.data_dir.resolve()
    config,_ = load(root)
    runtime = None
    installed = False
    try:
        existing = subprocess.run(["certutil.exe","-user","-store","Root",config["ca_thumbprint"]],capture_output=True)
        if existing.returncode == 0:
            raise RuntimeError("temporary qualification will not replace or remove a pre-existing trusted certificate")
        confirm_trust(root,confirmation=True)
        installed = True
        runtime = Runtime(root,preferred_port=0,embedded_test_worker=True)
        assert runtime.start()
        (root/"chrome-profile/DevToolsActivePort").unlink(missing_ok=True)
        chrome = subprocess.Popen([str(args.chrome),"--headless=new","--no-first-run","--no-default-browser-check",
            "--disable-background-networking","--disable-component-update","--disable-sync",
            f"--user-data-dir={root/'chrome-profile'}","--remote-debugging-port=0","about:blank"],
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            # Test-only CDP, not a production browser controller. Bootstrap never enters argv.
            from websockets.sync.client import connect
            portfile = root/"chrome-profile/DevToolsActivePort"
            deadline = time.monotonic()+15
            while not portfile.exists():
                if chrome.poll() is not None or time.monotonic()>deadline:
                    raise RuntimeError("isolated Chrome startup failed")
                time.sleep(0.1)
            lines = portfile.read_text().splitlines()
            with connect(f"ws://127.0.0.1:{lines[0]}{lines[1]}",open_timeout=5) as ws:
                sequence = 0
                def command(method,params,session=None):
                    nonlocal sequence
                    sequence += 1
                    value = {"id":sequence,"method":method,"params":params}
                    if session:
                        value["sessionId"] = session
                    ws.send(json.dumps(value))
                    while True:
                        result = json.loads(ws.recv(timeout=10))
                        if result.get("id")==sequence:
                            if "error" in result:
                                raise RuntimeError("test browser protocol failed")
                            return result["result"]
                target = command("Target.createTarget",{"url":"about:blank"})["targetId"]
                session = command("Target.attachToTarget",{"targetId":target,"flatten":True})["sessionId"]
                navigation = command("Page.navigate",{"url":runtime.control("launch")["url"]},session)
                success = False
                if not navigation.get("errorText"):
                    deadline = time.monotonic()+10
                    while time.monotonic()<deadline:
                        result = command("Runtime.evaluate",{"expression":"document.body?.innerText || ''","returnByValue":True},session)
                        if "Local session connected." in result["result"].get("value",""):
                            success = True
                            break
                        time.sleep(0.1)
                command("Browser.close",{})
        finally:
            try:
                chrome.wait(timeout=5)
            except subprocess.TimeoutExpired:
                chrome.terminate()
                chrome.wait(timeout=5)
        # Never persist process arguments/bootstrap fragments or raw Chrome diagnostics.
        report = {"chrome_exit_code":chrome.returncode,"session_connected":success,
            "certificate_thumbprint":config["ca_thumbprint"],"trust_scope":"CurrentUser Root",
            "tls_bypass_flags":False,"isolated_profile":True,"trust_removed":False}
        output = Path("docs/implementation-evidence/M1/browser-qualification.json")
        output.write_text(json.dumps(report,indent=2)+"\n")
        if not success:
            raise RuntimeError("Chrome bootstrap qualification failed; inspect locally without logging bootstrap material")
    finally:
        if runtime:
            runtime.close()
        if installed:
            subprocess.run(["certutil.exe","-user","-delstore","Root",config["ca_thumbprint"]],check=True,capture_output=True)
            config["trust_confirmed"] = False
            write_private(root/"installation.json",json.dumps(config).encode())
            output = Path("docs/implementation-evidence/M1/browser-qualification.json")
            if output.exists():
                report = json.loads(output.read_text())
                report["trust_removed"] = True
                output.write_text(json.dumps(report,indent=2)+"\n")


if __name__ == "__main__":
    main()
