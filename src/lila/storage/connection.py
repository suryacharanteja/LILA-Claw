"""Keyed SQLCipher only. Never downgrade to SQLite or accept unkeyed stores."""
from pathlib import Path
from sqlcipher3 import dbapi2
from lila.security.windows import private_directory
from lila.storage.migrations import apply_initial_schema


def open_store(path: Path, key: bytes, store: str):
    if len(key) != 32 or store not in {"business", "auth"}:
        raise ValueError("invalid store configuration")
    private_directory(path.parent)
    db = dbapi2.connect(str(path), isolation_level=None)
    try:
        # Key is validated bytes, never logged or passed through user SQL.
        db.execute(f"PRAGMA key=\"x'{key.hex()}'\"")
        if not db.execute("PRAGMA cipher_version").fetchone():
            raise RuntimeError("SQLCipher unavailable")
        db.execute("PRAGMA cipher_compatibility=4")
        db.execute("SELECT count(*) FROM sqlite_master").fetchone()
        for pragma in ("foreign_keys=ON", "journal_mode=WAL", "synchronous=FULL", "temp_store=MEMORY", "busy_timeout=5000"):
            db.execute("PRAGMA " + pragma)
        apply_initial_schema(db, store)
        expected = "principals" if store == "auth" else "tasks"
        if not db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (expected,)).fetchone():
            raise ValueError("wrong database kind")
        return db
    except BaseException:
        db.close()
        raise


def verify_integrity(db):
    cipher = db.execute("PRAGMA cipher_integrity_check").fetchall()
    regular = db.execute("PRAGMA integrity_check").fetchall()
    if cipher or regular != [("ok",)] or db.execute("PRAGMA foreign_key_check").fetchall():
        raise RuntimeError("store integrity failure")
