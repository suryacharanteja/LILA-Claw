"""Versioned schema application shared by test connections and later M1 driver."""
from pathlib import Path

ROOT = Path(__file__).parent

def apply_initial_schema(connection, store: str):
    if store not in {"business", "auth"}:
        raise ValueError("unknown store")
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if version == 1:
        return
    if version != 0:
        raise ValueError(f"unsupported schema version {version}")
    tables = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    if tables:
        raise ValueError("refusing unversioned non-empty store")
    # Foreign keys must be enabled before BEGIN; the SQL repeats this harmlessly.
    connection.execute("PRAGMA foreign_keys=ON")
    sql = (ROOT / f"0001_{store}.sql").read_text(encoding="utf-8")
    try:
        connection.executescript("BEGIN IMMEDIATE;\n" + sql + "\nPRAGMA user_version=1;\nCOMMIT;")
    except Exception:
        connection.rollback()
        raise
