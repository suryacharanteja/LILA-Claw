import pytest
from conftest import uid,task,action,policy
from lila.domain.core import DomainError


def lifecycle(domain,t,w,l,operation,reasons=None):
    snapshot = domain.task(t)
    return domain.lifecycle(w,snapshot['run_id'],l,1,uid(),snapshot['revision'],operation,reasons)


def test_wait_survives_holds_and_zero_match_completion(domain):
    t = task(domain)
    domain.task_command(domain.owner,t,{'command_id':uid(),'expected_revision':1,'operation':'start'})
    run = domain.task(t)['run_id']
    w = uid()
    l = domain.issue_lease(run,w,1)
    assert lifecycle(domain,t,w,l,'activate')['state']=='ACTIVE'
    assert lifecycle(domain,t,w,l,'await_input',['FACTS_REQUIRED'])['state']=='AWAITING_INPUT'
    for operation in ['pause','resume']:
        domain.task_command(domain.owner,t,{'command_id':uid(),'expected_revision':domain.task(t)['revision'],'operation':operation})
    assert domain.task(t)['state']=='AWAITING_INPUT'
    assert domain.task(t)['blocking_reasons']==['FACTS_REQUIRED']
    lifecycle(domain,t,w,l,'ready')
    with pytest.raises(DomainError,match='DISCOVERY_INCOMPLETE'):
        lifecycle(domain,t,w,l,'complete')
    lifecycle(domain,t,w,l,'discovery_complete')
    assert lifecycle(domain,t,w,l,'complete')['state']=='COMPLETED'
    assert domain.writer.call(lambda db:db.execute("SELECT summary_json FROM events WHERE kind='RUN_COMPLETE'").fetchone()[0])=='{"reason":"ZERO_MATCHES"}'
    with pytest.raises(DomainError,match='STALE_LEASE'):
        lifecycle(domain,t,w,l,'ready')


def test_completion_rejects_prepared_work_and_blockers_deny_dispatch(domain):
    a,w,l,t,_ = action(domain)
    p,_ = policy(domain)
    lifecycle(domain,t,w,l,'block',['POLICY_REQUIRED'])
    with pytest.raises(DomainError,match='READINESS_BLOCKED'):
        domain.dispatch_intent(a,p,w,l,1)
    lifecycle(domain,t,w,l,'ready')
    lifecycle(domain,t,w,l,'discovery_complete')
    with pytest.raises(DomainError,match='OUTCOME_UNRESOLVED'):
        lifecycle(domain,t,w,l,'complete')


def test_conflicting_terminal_outcome_requires_exact_review_and_reconciles_counts(domain):
    a,w,l,_,app = action(domain)
    p,_ = policy(domain)
    domain.dispatch_intent(a,p,w,l,1)
    domain.claim(a,w,l,1)
    domain.record_outcome(a,'CONFIRMED',evidence={'receipt':'first'})
    correction = domain.record_outcome(a,'FAILED',evidence={'inspection':'verified no submission'},not_submitted_proven=True)
    assert correction['state']=='AWAITING_CONFIRMATION'
    assert domain.writer.call(lambda db:db.execute('SELECT effective_outcome FROM applications WHERE id=?',(app,)).fetchone()[0])=='CONFIRMED'
    preview = domain.correction(correction['entity_id'])
    with pytest.raises(DomainError,match='PREVIEW_STALE'):
        domain.confirm_correction(domain.owner,preview['operation_id'],uid(),1,'0'*64)
    command_id = uid()
    result = domain.confirm_correction(domain.owner,preview['operation_id'],command_id,1,preview['preview_digest'])
    assert result['state']=='APPLIED'
    assert domain.confirm_correction(domain.owner,preview['operation_id'],command_id,1,preview['preview_digest'])==result
    assert domain.writer.call(lambda db:db.execute('SELECT submitted,reserved_actions FROM budget_windows').fetchone())==(0,0)
    outcomes = domain.writer.call(lambda db:db.execute('SELECT id,supersedes_id FROM outcomes ORDER BY rowid').fetchall())
    assert len(outcomes)==2 and outcomes[1][1]==outcomes[0][0]
    domain.verify_audit()


def test_stale_correction_and_audit_tamper_detection(domain):
    a,w,l,_,app = action(domain)
    p,_ = policy(domain)
    domain.dispatch_intent(a,p,w,l,1)
    domain.claim(a,w,l,1)
    domain.record_outcome(a,'CONFIRMED',evidence={'receipt':'first'})
    correction = domain.record_outcome(a,'FAILED',evidence={'inspection':'not submitted'},not_submitted_proven=True)
    preview = domain.correction(correction['entity_id'])
    revision = domain.writer.call(lambda db:db.execute('SELECT revision FROM applications WHERE id=?',(app,)).fetchone()[0])
    domain.manual_outcome(domain.owner,app,{'command_id':uid(),'expected_revision':revision,'operation':'leave_unresolved'})
    with pytest.raises(DomainError,match='PREVIEW_STALE'):
        domain.confirm_correction(domain.owner,preview['operation_id'],uid(),1,preview['preview_digest'])
    assert domain.verify_audit()['events_verified']>0
    domain.writer.call(lambda db:db.execute('DELETE FROM audit_events WHERE sequence=(SELECT max(sequence) FROM audit_events)'))
    with pytest.raises(DomainError,match='AUDIT_INTEGRITY_FAILURE'):
        domain.verify_audit()
