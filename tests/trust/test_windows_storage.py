import secrets
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from lila.security.windows import protect, unprotect, OwnerLock
from lila.storage.connection import open_store, verify_integrity
from lila.storage.writer import StoreWriter
from lila.runtime.control_pipe import ControlPipe, request
from lila.runtime.supervisor import Supervisor, State


def test_dpapi_roundtrip_corruption():
    secret = secrets.token_bytes(32)
    protected = protect(secret)
    assert secret not in protected
    assert unprotect(protected) == secret
    with pytest.raises(Exception):
        unprotect(protected[:-5]+b"xxxxx")


def test_encrypted_database_and_wal_reopen_wrong_key(tmp_path):
    path, key = tmp_path/"business.db", secrets.token_bytes(32)
    db = open_store(path,key,"business")
    canary = "M1-PRIVATE-CANARY-"+secrets.token_hex(24)
    db.execute("INSERT INTO accounts VALUES('account','linkedin',?,1)",(canary,))
    assert db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert (tmp_path/"business.db-wal").exists()
    for file in tmp_path.glob("business.db*"):
        assert canary.encode() not in file.read_bytes()
    verify_integrity(db)
    db.close()
    reopened = open_store(path,key,"business")
    assert reopened.execute("SELECT external_subject FROM accounts").fetchone()[0] == canary
    reopened.close()
    with pytest.raises(Exception):
        open_store(path,secrets.token_bytes(32),"business")
    with pytest.raises(ValueError):
        open_store(path,key,"auth")
    modified = open_store(path,key,"business")
    modified.execute("UPDATE schema_migrations SET checksum='mismatched'")
    modified.close()
    with pytest.raises(RuntimeError,match="migration checksum"):
        open_store(path,key,"business")


def test_writer_serialization_rollback_and_shutdown(tmp_path):
    writer = StoreWriter(tmp_path/"auth.db",secrets.token_bytes(32),"auth")
    with ThreadPoolExecutor(8) as pool:
        list(pool.map(lambda _:writer.call(lambda db:db.execute("UPDATE auth_epoch SET epoch=epoch+1").rowcount),range(40)))
    assert writer.call(lambda db:db.execute("SELECT epoch FROM auth_epoch").fetchone()[0]) == 41
    def fail(db):
        db.execute("UPDATE auth_epoch SET epoch=99")
        raise ValueError("injected")
    with pytest.raises(ValueError):
        writer.call(fail)
    assert writer.call(lambda db:db.execute("SELECT epoch FROM auth_epoch").fetchone()[0]) == 41
    writer.close()
    with pytest.raises(RuntimeError):
        writer.call(lambda db:None)


def test_owner_mutex_and_control_pipe():
    identity = str(uuid4())
    first, second = OwnerLock(identity), OwnerLock(identity)
    assert first.acquire()
    try:
        assert not second.acquire()
        pipe = ControlPipe(identity,lambda operation:{"operation":operation})
        pipe.start()
        try:
            for _ in range(25):
                assert request(identity,"status") == {"operation":"status"}
            assert request(identity,"unsafe") == {"error":"INVALID_REQUEST"}
        finally:
            pipe.close()
    finally:
        first.close()
    assert second.acquire()
    second.close()


def test_crash_loop_and_intentional_quit():
    events = []
    supervisor = Supervisor(lambda:events.append("persist"),lambda:events.append("fence"))
    delays = []
    for index in range(12):
        value = supervisor.health(False,index*2)
        if value:
            delays.append(value)
    assert delays == [1,2,4]
    assert supervisor.blockers == ["INTERVENTION_REQUIRED"]
    assert supervisor.health(False,600) is None
    supervisor.quit()
    assert events[-2:] == ["persist","fence"]
    assert supervisor.health(False,60) is None
    supervisor.stopped()
    assert supervisor.state == State.STOPPED
