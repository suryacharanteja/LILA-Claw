"""Keyed SQLCipher only. Never downgrade to SQLite or accept unkeyed stores."""
from pathlib import Path
import hashlib
from sqlcipher3 import dbapi2
from lila.security.windows import private_directory
from lila.storage.migrations import apply_initial_schema, ROOT


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
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version not in ((0,1,2,3,4,5) if store=='business' else (0,1,2)):
            raise ValueError("unsupported schema version")
        if version == 0:
            apply_initial_schema(db, store)
        expected = "principals" if store == "auth" else "tasks"
        if not db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (expected,)).fetchone():
            raise ValueError("wrong database kind")
        second = "0002_auth_receipts.sql" if store=="auth" else "0002_business_domain.sql"
        table = "auth_schema_migrations" if store=="auth" else "schema_migrations"
        if db.execute("PRAGMA user_version").fetchone()[0] == 1:
            try:
                script = (ROOT/second).read_text(encoding="utf-8")
                versions = [(1,"0001_auth.sql"),(2,second)] if store=="auth" else [(2,second)]
                for version, filename in versions:
                    digest = hashlib.sha256((ROOT/filename).read_bytes()).hexdigest()
                    script += f"\nINSERT INTO {table} VALUES({version},'{digest}',strftime('%Y-%m-%dT%H:%M:%fZ','now'));"
                db.executescript("BEGIN IMMEDIATE;\n" + script + "\nPRAGMA user_version=2;\nCOMMIT;")
            except BaseException:
                db.rollback()
                raise
        table = "schema_migrations" if store == "business" else "auth_schema_migrations"
        expected_migrations = [(1,f"0001_{store}.sql"),(2,second)]
        for version, filename in expected_migrations:
            actual = db.execute(f"SELECT checksum FROM {table} WHERE version=?",(version,)).fetchone()
            if not actual or actual[0] != hashlib.sha256((ROOT/filename).read_bytes()).hexdigest():
                raise RuntimeError("migration checksum mismatch")
        if store=='business':
            filename = '0003_business_lifecycle.sql'
            digest = hashlib.sha256((ROOT/filename).read_bytes()).hexdigest()
            if db.execute('PRAGMA user_version').fetchone()[0]==2:
                try:
                    script = (ROOT/filename).read_text(encoding='utf-8')
                    db.executescript("BEGIN IMMEDIATE;\n"+script+f"\nINSERT INTO schema_migrations VALUES(3,'{digest}',strftime('%Y-%m-%dT%H:%M:%fZ','now'));\nPRAGMA user_version=3;\nCOMMIT;")
                except BaseException:
                    db.rollback()
                    raise
            if db.execute('SELECT checksum FROM schema_migrations WHERE version=3').fetchone()!=(digest,):
                raise RuntimeError('migration checksum mismatch')
            filename = '0004_business_documents.sql'
            digest = hashlib.sha256((ROOT/filename).read_bytes()).hexdigest()
            if db.execute('PRAGMA user_version').fetchone()[0]==3:
                try:
                    script = (ROOT/filename).read_text(encoding='utf-8')
                    db.executescript("BEGIN IMMEDIATE;\n"+script+f"\nINSERT INTO schema_migrations VALUES(4,'{digest}',strftime('%Y-%m-%dT%H:%M:%fZ','now'));\nPRAGMA user_version=4;\nCOMMIT;")
                except BaseException:
                    db.rollback()
                    raise
            if db.execute('SELECT checksum FROM schema_migrations WHERE version=4').fetchone()!=(digest,):
                raise RuntimeError('migration checksum mismatch')
            filename = '0005_business_action_blockers.sql'
            digest = hashlib.sha256((ROOT/filename).read_bytes()).hexdigest()
            if db.execute('PRAGMA user_version').fetchone()[0]==4:
                try:
                    script = (ROOT/filename).read_text(encoding='utf-8')
                    db.executescript("BEGIN IMMEDIATE;\n"+script+f"\nINSERT INTO schema_migrations VALUES(5,'{digest}',strftime('%Y-%m-%dT%H:%M:%fZ','now'));\nPRAGMA user_version=5;\nCOMMIT;")
                except BaseException:
                    db.rollback()
                    raise
            if db.execute('SELECT checksum FROM schema_migrations WHERE version=5').fetchone()!=(digest,):
                raise RuntimeError('migration checksum mismatch')
        return db
    except BaseException:
        db.close()
        raise


def verify_integrity(db):
    cipher = db.execute("PRAGMA cipher_integrity_check").fetchall()
    regular = db.execute("PRAGMA integrity_check").fetchall()
    if cipher or regular != [("ok",)] or db.execute("PRAGMA foreign_key_check").fetchall():
        raise RuntimeError("store integrity failure")
