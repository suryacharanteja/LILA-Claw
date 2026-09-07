"""In-process ASGI fixture only. No production entry point or network listener.

SQLite here validates schema/receipt behavior with synthetic data. Production
encrypted connections and authentication are M1 obligations.
"""
import hashlib
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException
from lila.contracts.generated_models import TaskCommand, Receipt
from lila.storage.migrations import apply_initial_schema

def create_harness(path: Path):
    db = sqlite3.connect(path, check_same_thread=False)
    apply_initial_schema(db, "business")
    lock = threading.Lock()
    app = FastAPI()
    principal = "offline-fixture-principal"

    @app.post("/fixture/tasks/{entity_id}/commands", response_model=Receipt)
    def command(entity_id: UUID, payload: TaskCommand):
        serialized = payload.model_dump_json()
        digest = hashlib.sha256((str(entity_id) + serialized).encode()).hexdigest()
        command_id = str(payload.command_id)
        with lock, db:
            prior = db.execute(
                "SELECT request_digest, result_json FROM command_receipts WHERE principal_id=? AND command_id=?",
                (principal, command_id),
            ).fetchone()
            if prior:
                if prior[0] != digest:
                    raise HTTPException(409, "command_id reused with different request")
                return json.loads(prior[1])
            receipt = Receipt(command_id=payload.command_id, accepted=True,
                entity_id=entity_id, revision=payload.expected_revision,
                state="FIXTURE_RECORDED", blocking_reasons=[])
            db.execute("INSERT INTO command_receipts VALUES(?,?,?,?,?,?)",
                (principal, command_id, digest, 200, receipt.model_dump_json(),
                 datetime.now(timezone.utc).isoformat()))
            return receipt

    return app, db
