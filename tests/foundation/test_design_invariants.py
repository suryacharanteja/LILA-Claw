"""Run approved SQL negative cases without modifying the approved evidence."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_approved_design_invariants(tmp_path):
    source = ROOT / "docs/lld/contracts"
    for name in ["verify_design.py", "schema-v1.sql", "auth-schema-v1.sql",
                 "protocol-v1.schema.json", "openapi-v1.json"]:
        shutil.copyfile(source / name, tmp_path / name)
    subprocess.run([sys.executable, str(tmp_path / "verify_design.py")], check=True, capture_output=True)
    report = json.loads((tmp_path / "validation-report.json").read_text())
    assert not any("NOT RUN" in check for check in report["checks"])
    assert report["business_tables"] == 38
    assert report["auth_tables"] == 8
