import hashlib
import secrets
from pathlib import Path
import pytest
from sqlcipher3 import dbapi2
from lila.storage.migrations import apply_initial_schema,ROOT
from lila.storage.connection import open_store
from lila.domain.core import DomainError
from lila.api.uploads import UploadParser
from lila.domain.artifacts import MAX_SIZE
from conftest import uid,action,policy,task


def test_v2_store_upgrades_without_changing_prior_checksums(tmp_path):
    key = secrets.token_bytes(32)
    path = tmp_path/'old.db'
    db = dbapi2.connect(str(path),isolation_level=None)
    db.execute(f"PRAGMA key=\"x'{key.hex()}'\"")
    apply_initial_schema(db,'business')
    second = ROOT/'0002_business_domain.sql'
    digest = hashlib.sha256(second.read_bytes()).hexdigest()
    db.executescript(second.read_text(encoding='utf-8'))
    db.execute("INSERT INTO schema_migrations VALUES(2,?,'fixture')",(digest,))
    account = uid()
    db.execute("INSERT INTO accounts VALUES(?,'linkedin','preserved',1)",(account,))
    db.execute('PRAGMA user_version=2')
    db.close()
    db = open_store(path,key,'business')
    try:
        assert db.execute('PRAGMA user_version').fetchone()[0]==5
        assert db.execute('SELECT id FROM accounts').fetchone()[0]==account
        assert db.execute('SELECT checksum FROM schema_migrations WHERE version=2').fetchone()[0]==digest
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
        db.execute("UPDATE schema_migrations SET checksum='tampered' WHERE version=3")
    finally:
        db.close()
    with pytest.raises(RuntimeError,match='migration checksum mismatch'):
        open_store(path,key,'business')


def test_capability_rechecked_and_blocking_reason_persisted(domain):
    a,w,l,_,_ = action(domain)
    p,_ = policy(domain)
    domain.dispatch_intent(a,p,w,l,1)
    domain.capability = lambda account,host,tab:False
    with pytest.raises(DomainError,match='BROWSER_CAPABILITY_CHANGED'):
        domain.claim(a,w,l,1)
    assert domain.writer.call(lambda db:db.execute('SELECT reason FROM action_blockers WHERE action_id=?',(a,)).fetchone()[0])=='BROWSER_CAPABILITY_CHANGED'
    assert domain.writer.call(lambda db:db.execute('SELECT state FROM actions WHERE id=?',(a,)).fetchone()[0])=='DISPATCH_INTENT'
    domain.capability = lambda account,host,tab:True
    domain.claim(a,w,l,1)
    assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM action_blockers').fetchone()[0])==0


def test_segment_rollover_and_wrong_audit_key(domain):
    def emit(db):
        for revision in range(1,1002):
            domain.event(db,'FIXTURE','task',domain.account_id,revision)
    domain.writer.call(emit)
    assert domain.verify_audit()=={'events_verified':1001,'segments_verified':2}
    domain.audit_key = secrets.token_bytes(32)
    with pytest.raises(DomainError,match='AUDIT_INTEGRITY_FAILURE'):
        domain.verify_audit()


def test_failed_intent_transaction_leaves_no_reservation_or_guard(domain):
    a,w,l,_,_ = action(domain)
    p,_ = policy(domain)
    original = domain.event
    def fail(db,kind,*args,**kwargs):
        if kind=='ACTION_INTENT':
            raise OSError('fixture storage failure')
        return original(db,kind,*args,**kwargs)
    domain.event = fail
    with pytest.raises(OSError,match='fixture storage failure'):
        domain.dispatch_intent(a,p,w,l,1)
    assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM reservations').fetchone()[0])==0
    assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM submission_guards').fetchone()[0])==0
    assert domain.writer.call(lambda db:db.execute('SELECT state FROM actions WHERE id=?',(a,)).fetchone()[0])=='PREPARED'


def test_full_100_mib_stream_limit_without_disk_spooling():
    boundary='lila-fixture'
    parser = UploadParser('multipart/form-data; boundary='+boundary)
    for name,value in [('command_id',uid()),('account_id',uid())]:
        parser.write(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    parser.write(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="fixture.pdf"\r\nContent-Type: application/pdf\r\n\r\n'.encode())
    chunk=b'x'*65536
    for _ in range(MAX_SIZE//len(chunk)):
        parser.write(chunk)
    parser.write(f'\r\n--{boundary}--\r\n'.encode())
    assert len(parser.result()['data'])==MAX_SIZE


def test_expired_policy_creation_replay_returns_original_receipt(domain):
    p,body = policy(domain)
    first = domain.get_receipt(domain.owner,body['command_id'])
    domain.test_clock[0]=2000000000
    assert domain.create_policy(domain.owner,body)==first


def test_claim_crossing_midnight_moves_daily_reservation(domain):
    from datetime import datetime
    domain.test_clock[0]=datetime.fromisoformat('2027-01-15T23:59:58+00:00').timestamp()
    a,w,l,_,_ = action(domain)
    p,_ = policy(domain,zone='UTC')
    domain.dispatch_intent(a,p,w,l,1)
    old = domain.writer.call(lambda db:db.execute('SELECT window_id FROM reservations').fetchone()[0])
    domain.test_clock[0]+=3
    domain.claim(a,w,l,1)
    new = domain.writer.call(lambda db:db.execute('SELECT window_id FROM reservations').fetchone()[0])
    assert old!=new
    assert domain.writer.call(lambda db:db.execute('SELECT reserved_actions FROM budget_windows WHERE id=?',(old,)).fetchone()[0])==0
    assert domain.writer.call(lambda db:db.execute('SELECT reserved_actions FROM budget_windows WHERE id=?',(new,)).fetchone()[0])==1
