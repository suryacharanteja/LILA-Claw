import pytest
from conftest import action,policy
from lila.domain.core import DomainError


@pytest.mark.parametrize('point',['before_intent','after_intent','after_claim','after_outcome'])
def test_recovery_at_local_action_boundaries(domain,point):
    aid,worker,lease,_,_=action(domain)
    pid,_=policy(domain)
    if point!='before_intent':
        domain.dispatch_intent(aid,pid,worker,lease,1)
    if point in {'after_claim','after_outcome'}:
        domain.claim(aid,worker,lease,1)
    if point=='after_outcome':
        domain.record_outcome(aid,'CONFIRMED',evidence={'fixture':'receipt'})
    for _ in range(2):
        domain.recover()
        expected={'before_intent':'PREPARED','after_intent':'UNCERTAIN','after_claim':'UNCERTAIN','after_outcome':'CONFIRMED'}[point]
        assert domain.writer.call(lambda db:db.execute('SELECT state FROM actions WHERE id=?',(aid,)).fetchone())==(expected,)
        if point=='before_intent':
            assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM reservations').fetchone())==(0,)
        else:
            counters=domain.writer.call(lambda db:db.execute('SELECT submitted,reserved_actions FROM budget_windows').fetchone())
            assert counters==((1,0) if point=='after_outcome' else (0,1))
    with pytest.raises(DomainError):
        domain.claim(aid,worker,lease,1)
    assert domain.writer.call(lambda db:db.execute("SELECT count(*) FROM actions WHERE state IN ('CLAIMED','DISPATCHED')").fetchone())==(0,)


def test_failure_before_outcome_commit_rolls_back_then_reconciles_once(domain,monkeypatch):
    aid,worker,lease,_,_=action(domain)
    pid,_=policy(domain)
    domain.dispatch_intent(aid,pid,worker,lease,1)
    domain.claim(aid,worker,lease,1)
    original=domain.event
    def fail(db,kind,*args,**kwargs):
        if kind=='OUTCOME_CONFIRMED':
            raise RuntimeError('Injected before outcome transaction commit')
        return original(db,kind,*args,**kwargs)
    monkeypatch.setattr(domain,'event',fail)
    with pytest.raises(RuntimeError,match='Injected'):
        domain.record_outcome(aid,'CONFIRMED',evidence={'fixture':'receipt'})
    assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM outcomes').fetchone())==(0,)
    assert domain.writer.call(lambda db:db.execute('SELECT state FROM actions WHERE id=?',(aid,)).fetchone())==('CLAIMED',)
    assert domain.writer.call(lambda db:db.execute('SELECT submitted,reserved_actions FROM budget_windows').fetchone())==(0,1)
    monkeypatch.setattr(domain,'event',original)
    domain.recover()
    for _ in range(2):
        domain.record_outcome(aid,'CONFIRMED',evidence={'fixture':'receipt'})
    assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM outcomes').fetchone())==(1,)
    assert domain.writer.call(lambda db:db.execute('SELECT submitted,reserved_actions FROM budget_windows').fetchone())==(1,0)
    domain.verify_audit()
