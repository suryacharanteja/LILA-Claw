"""Explicit installation setup, separate from starting an existing runtime."""
import json
import secrets
import subprocess
from pathlib import Path
from uuid import uuid4
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from lila.security.windows import private_directory, protect, unprotect, write_private
from lila.security.tls import generate


def prepare(root: Path):
    private_directory(root)
    if any(root.iterdir()):
        raise ValueError("setup requires an empty managed directory")
    install_id = str(uuid4())
    thumbprint = generate(root / "tls", install_id)
    keys = {name: secrets.token_bytes(32).hex() for name in ("business", "auth", "session_hash", "artifact_wrap", "audit", "recovery")}
    keys["identity"] = Ed25519PrivateKey.generate().private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()).hex()
    write_private(root / "keys.dpapi", protect(json.dumps(keys).encode()))
    config = {"install_id": install_id, "ca_thumbprint": thumbprint, "trust_confirmed": False, "allow_fragment_launch": True}
    write_private(root / "installation.json", json.dumps(config).encode())
    return config


def load(root):
    config = json.loads((root / "installation.json").read_text())
    keys = {name: bytes.fromhex(value) for name,value in json.loads(unprotect((root / "keys.dpapi").read_bytes())).items()}
    return config, keys


def confirm_trust(root, *, confirmation=False):
    if not confirmation:
        raise PermissionError("explicit CurrentUser Root setup confirmation required")
    config, _ = load(root)
    subprocess.run(["certutil.exe", "-user", "-addstore", "Root", str(root / "tls/ca.pem")], check=True, capture_output=True)
    config["trust_confirmed"] = True
    write_private(root / "installation.json", json.dumps(config).encode())
