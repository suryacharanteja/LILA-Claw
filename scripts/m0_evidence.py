"""Capture reproducible M0 environment, licenses and approved baseline hashes."""
import hashlib
import importlib.metadata as md
import json
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/implementation-evidence/M0"
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

packages = []
license_texts = OUT / "dependency-licenses"
license_texts.mkdir(exist_ok=True)
for dist in sorted(md.distributions(), key=lambda d: d.metadata["Name"].lower()):
    texts = []
    for rel in dist.files or []:
        if any(token in str(rel).lower() for token in ["license", "copying", "notice"]) and ".dist-info/" in str(rel).replace("\\", "/"):
            source = Path(dist.locate_file(rel))
            if source.is_file():
                target = license_texts / (dist.metadata["Name"] + "-" + str(rel).replace("/", "_").replace("\\", "_"))
                target.write_bytes(source.read_bytes())
                texts.append({"path": str(target.relative_to(ROOT)), "sha256": digest(target)})
    packages.append({
        "name": dist.metadata["Name"], "version": dist.version,
        "license": dist.metadata.get("License-Expression") or dist.metadata.get("License"),
        "classifiers": dist.metadata.get_all("Classifier") or [], "license_files": texts,
    })
write("python-licenses.json", packages)

lock = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8-sig"))
write("npm-licenses.json", [
    {"path": p, "version": d.get("version"), "license": d.get("license"),
     "integrity": d.get("integrity"), "resolved": d.get("resolved")}
    for p, d in lock["packages"].items() if p
])
baseline_paths = [
    "docs/BRD-linkedin-intelligent-suite.md", "docs/solution-design.md",
    "docs/FRD-LILA-Claw.md", "docs/HLD-LILA-Claw.md", "docs/LLD-LILA-Claw.md",
    "app.py", "runAiBot.py", "config_schema.py", "LICENSE", "NOTICE"
]
baseline_paths += [str(p.relative_to(ROOT)) for p in (ROOT / "docs/lld").rglob("*") if p.is_file()]
write("baseline-hashes.json", {p: digest(ROOT / p) for p in baseline_paths})
write("environment.json", {
    "python": platform.python_version(), "platform": platform.platform(),
    "machine": platform.machine(),
    "node": subprocess.check_output(["node", "--version"], text=True).strip(),
    "npm": subprocess.check_output(["npm.cmd", "--version"], text=True).strip(),
    "requirements_sha256": digest(ROOT / "requirements.lock"),
    "package_lock_sha256": digest(ROOT / "package-lock.json"),
    "python_executable_sha256": digest(Path(__import__("sys").executable)),
    "scope": "Development foundation; not clean-machine or release qualification",
})
print(f"Inventoried {len(packages)} Python distributions and {len(lock['packages']) - 1} npm lock entries.")
