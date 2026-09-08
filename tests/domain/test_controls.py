from concurrent.futures import ThreadPoolExecutor
import pytest
from lila.domain.core import DomainError
from conftest import uid,task,action,policy


def command(service,task_id,operation):
    return service.task_command(service.owner,task_id,{'command_id':uid(),'expected_revision':service.task(task_id)['revision'],'operation':operation})


def test_independent_holds_and_restart(domain):
    t = task(domain)
    command(domain,t,'start')
    first = domain.task(t)['run_id']
    command(domain,t,'pause')
    domain.global_command(domain.owner,{'command_id':uid(),'expected_revision':1,'operation':'pause_all'})
    domain.global_command(domain.owner,{'command_id':uid(),'expected_revision':2,'operation':'resume_all'})
    assert domain.task(t)['state']=='PAUSED'
    command(domain,t,'resume')
    assert domain.task(t)['state']=='QUEUED'
    command(domain,t,'stop')
    command(domain,t,'restart')
    assert domain.task(t)['run_id']!=first


def test_concurrent_command_replay_and_conflicting_reuse(domain):
    t = task(domain)
    body = {'command_id':uid(),'expected_revision':1,'operation':'start'}
    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(lambda _:domain.task_command(domain.owner,t,body),range(8)))
    assert all(r==results[0] for r in results)
    assert domain.task(t)['revision']==2
    assert domain.get_receipt(domain.owner,body['command_id'])==results[0]
    with pytest.raises(DomainError,match='COMMAND_ID_REUSED'):
        domain.task_command(domain.owner,t,dict(body,operation='stop'))
    with pytest.raises(DomainError,match='NOT_FOUND'):
        domain.get_receipt(uid(),body['command_id'])


def test_pause_blocks_claim_stop_releases_allowance(domain):
    a,w,l,t,_ = action(domain)
    p,_ = policy(domain)
    domain.dispatch_intent(a,p,w,l,1)
    command(domain,t,'pause')
    with pytest.raises(DomainError,match='EXECUTION_PAUSED'):
        domain.claim(a,w,l,1)
    command(domain,t,'stop')
    assert domain.writer.call(lambda db:db.execute('SELECT state FROM reservations').fetchone()[0])=='RELEASED'
    assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM submission_guards').fetchone()[0])==0
    assert domain.writer.call(lambda db:db.execute('SELECT reserved_actions FROM budget_windows').fetchone()[0])==0


def test_recovery_keeps_uncertainty_across_restart(domain):
    a,w,l,t,app = action(domain)
    p,_ = policy(domain)
    domain.dispatch_intent(a,p,w,l,1)
    domain.claim(a,w,l,1)
    domain.recover()
    command(domain,t,'stop')
    command(domain,t,'restart')
    assert 'OUTCOME_UNRESOLVED' in domain.task(t)['blocking_reasons']
    revision = domain.writer.call(lambda db:db.execute('SELECT revision FROM applications WHERE id=?',(app,)).fetchone()[0])
    domain.manual_outcome(domain.owner,app,{'command_id':uid(),'expected_revision':revision,'operation':'mark_not_submitted'})
    assert domain.writer.call(lambda db:db.execute('SELECT reason FROM submission_guards').fetchone()[0])=='UNCERTAIN'
    domain.record_outcome(a,'FAILED',evidence={'verified':'not submitted'},not_submitted_proven=True)
    assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM submission_guards').fetchone()[0])==0


def test_daily_cap_and_confirmed_duplicate(domain):
    a,w,l,t,_ = action(domain)
    p,_ = policy(domain,cap=1)
    domain.dispatch_intent(a,p,w,l,1)
    domain.claim(a,w,l,1)
    domain.record_outcome(a,'CONFIRMED',evidence={'fixture':'confirmation'})
    b,w,l,_,_ = action(domain,external_id='456')
    with pytest.raises(DomainError,match='ACTION_LIMIT'):
        domain.dispatch_intent(b,p,w,l,1)
    c,w,l,_,_ = action(domain,external_id='123')
    with pytest.raises(DomainError,match='DUPLICATE_APPLICATION'):
        domain.dispatch_intent(c,p,w,l,1)


def test_fact_edit_invalidates_exact_review(domain):
    a,w,l,_,_ = action(domain)
    preview = domain.prepare_review([a])
    domain.approval_command(domain.owner,preview['review_id'],{'command_id':uid(),'expected_revision':1,'operation':'approve','payload_version':preview['payload_version'],'members':preview['members']})
    domain.fact_command(domain.owner,domain.account_id,{'command_id':uid(),'expected_revision':1,'operation':'verify','field_key':'name','value':'Changed'})
    assert domain.writer.call(lambda db:db.execute('SELECT state FROM approvals').fetchone()[0])=='REVOKED'
    p,_ = policy(domain)
    with pytest.raises(DomainError,match='FACTS_REQUIRED'):
        domain.dispatch_intent(a,p,w,l,1)


def test_lease_expiry_and_policy_change_before_claim(domain):
    a,w,l,_,_ = action(domain)
    p,body = policy(domain)
    domain.dispatch_intent(a,p,w,l,1)
    domain.policy_command(domain.owner,p,uid(),1,'revoke')
    with pytest.raises(DomainError,match='POLICY_REQUIRED'):
        domain.claim(a,w,l,1)
    domain.test_clock[0]+=11
    with pytest.raises(DomainError,match='STALE_LEASE'):
        domain.claim(a,w,l,1)
