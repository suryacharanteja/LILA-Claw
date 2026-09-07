import importlib
import json
import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate
from openapi_spec_validator.readers import read_from_filename

from lila.contracts.generated_models import TaskCommand
from lila.storage.migrations import apply_initial_schema
from .harness import create_harness
from .doubles import FixtureBrowser, FixtureProvider

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "docs/lld/contracts"

def test_full_schema_and_openapi():
    schema = json.loads((CONTRACTS / "protocol-v1.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    spec, uri = read_from_filename(str(CONTRACTS / "openapi-v1.json"))
    validate(spec, base_uri=uri)

@pytest.mark.parametrize("store,source", [("business", "schema-v1.sql"), ("auth", "auth-schema-v1.sql")])
def test_migration_matches_baseline_and_reopens(store, source):
    expected = (CONTRACTS / source).read_bytes()
    actual = (ROOT / f"src/lila/storage/migrations/0001_{store}.sql").read_bytes()
    assert actual == expected
    db = sqlite3.connect(":memory:")
    apply_initial_schema(db, store)
    apply_initial_schema(db, store)
    assert db.execute("PRAGMA user_version").fetchone()[0] == 1
    assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert not db.execute("PRAGMA foreign_key_check").fetchall()
    db.close()

def test_unknown_or_legacy_store_is_not_overwritten():
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE legacy(value)")
    with pytest.raises(ValueError):
        apply_initial_schema(db, "business")
    assert db.execute("SELECT name FROM sqlite_master WHERE name='legacy'").fetchone()
    db.execute("PRAGMA user_version=99")
    with pytest.raises(ValueError):
        apply_initial_schema(db, "business")

def test_receipt_roundtrip_replay_conflict_and_restart(tmp_path):
    path = tmp_path / "fixture.db"
    task_id, command_id = str(uuid4()), str(uuid4())
    body = dict(command_id=command_id, expected_revision=1, operation="pause")
    app, db = create_harness(path)
    with TestClient(app) as client:
        url = f"/fixture/tasks/{task_id}/commands"
        first = client.post(url, json=body)
        assert first.status_code == 200
        assert first.json()["state"] == "FIXTURE_RECORDED"
        assert client.post(url, json=body).json() == first.json()
        assert client.post(url, json={**body, "operation": "stop"}).status_code == 409
        assert client.post(url, json={**body, "expected_revision": 0}).status_code == 422
        assert db.execute("SELECT count(*) FROM command_receipts").fetchone()[0] == 1
    db.close()
    app, db = create_harness(path)
    with TestClient(app) as client:
        assert client.post(url, json=body).json() == first.json()
    db.close()

@pytest.mark.parametrize("invalid", [
    {"command_id": "bad", "expected_revision": 1, "operation": "pause"},
    {"command_id": str(uuid4()), "expected_revision": 0, "operation": "pause"},
    {"command_id": str(uuid4()), "expected_revision": 1, "operation": "unsafe"},
    {"command_id": str(uuid4()), "expected_revision": 1, "operation": "pause", "extra": True},
])
def test_generated_model_and_schema_reject_invalid(invalid):
    schema = json.loads((CONTRACTS / "protocol-v1.schema.json").read_text())
    schema["$ref"] = "#/$defs/TaskCommand"
    assert list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(invalid))
    with pytest.raises(ValueError):
        TaskCommand.model_validate(invalid)

def test_offline_doubles():
    browser, provider = FixtureBrowser(), FixtureProvider()
    assert browser.discover()[0]["external_id"] == "fixture-job-001"
    assert provider.draft({"skill": "Python"}) == "skill: Python"
    with pytest.raises(ValueError):
        provider.draft({})

@pytest.mark.parametrize("module", [
    "fastapi", "pydantic", "uvicorn", "httpx", "sqlcipher3", "cryptography",
    "win32crypt", "langgraph.graph", "langgraph.checkpoint.base",
    "docx", "pypdf", "fpdf", "PyInstaller",
])
def test_selected_dependency_import(module):
    importlib.import_module(module)

def test_sqlcipher_binary_exposes_cipher():
    from sqlcipher3 import dbapi2
    db = dbapi2.connect(":memory:")
    assert db.execute("PRAGMA cipher_version").fetchone()[0]
    db.close()
