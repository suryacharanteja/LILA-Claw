from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from conftest import task,uid
from test_ai import budget,fixture_config
from lila.domain.core import DomainError
from lila.worker.provider import money,MAX_INPUT,MAX_OUTPUT


def test_concurrent_runs_cannot_reserve_beyond_shared_daily_budget(domain):
    ai,worker,first,pid,body=budget(domain)
    amount=money(MAX_INPUT,MAX_OUTPUT,400000,1600000)
    body['budget_micro_usd']=amount
    domain.policy_command(domain.owner,pid,uid(),1,'revise',body)
    tid=task(domain)
    domain.task_command(domain.owner,tid,{'command_id':uid(),'expected_revision':1,'operation':'start'})
    run=domain.task(tid)['run_id']
    second=dict(first,invocation_id=uid(),run_id=run,lease_id=domain.issue_lease(run,worker,1))
    barrier=Barrier(2)
    def reserve(args):
        barrier.wait(timeout=5)
        try:
            return ai.reserve(worker,**args)['state']
        except DomainError as exc:
            return exc.code
    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(reserve,[first,second]))==['BUDGET_EXHAUSTED','RESERVED']
    assert domain.writer.call(lambda db:db.execute('SELECT reserved_micro_usd,consumed_micro_usd FROM budget_windows').fetchall())==[(amount,0)]
    assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM ai_invocations').fetchone())==(1,)


def test_timezone_roundtrip_and_late_usage_do_not_reset_or_double_budget(domain):
    ai,worker,args,pid,body=budget(domain)
    amount=ai.reserve(worker,**args)['amount_micro_usd']
    for revision,zone in enumerate(['America/New_York','Asia/Dubai'],1):
        body['timezone']=zone
        domain.policy_command(domain.owner,pid,uid(),revision,'revise',body)
    assert ai.claim(worker,args['invocation_id'],1)['may_send']
    ai.recover()
    windows=domain.writer.call(lambda db:db.execute('SELECT reserved_micro_usd,consumed_micro_usd FROM budget_windows').fetchall())
    assert len(windows)==2 and all(row==(amount,0) for row in windows)
    domain.test_clock[0]+=11
    for _ in range(2):
        assert ai.result(worker,args['invocation_id'],1,status='COMPLETED',input_tokens=100,output_tokens=10)['may_dispatch'] is False
    assert domain.writer.call(lambda db:db.execute('SELECT reserved_micro_usd,consumed_micro_usd FROM budget_windows').fetchall())==[(0,56),(0,56)]


def test_replacement_worker_cannot_claim_or_reconcile_predecessor_invocation(domain):
    ai,worker,args,_,_=budget(domain)
    ai.reserve(worker,**args)
    ai.claim(worker,args['invocation_id'],1)
    replacement=uid()
    domain.issue_lease(args['run_id'],replacement,2)
    with pytest.raises(DomainError,match='SCOPE_DENIED'):
        ai.claim(replacement,args['invocation_id'],2)
    with pytest.raises(DomainError,match='SCOPE_DENIED'):
        ai.result(replacement,args['invocation_id'],2,status='REJECTED')
    with pytest.raises(DomainError,match='STALE_LEASE'):
        ai.claim(worker,args['invocation_id'],1)
    ai.recover()
    assert ai.result(worker,args['invocation_id'],1,status='COMPLETED',input_tokens=100,output_tokens=10)['may_dispatch'] is False
    assert domain.writer.call(lambda db:db.execute('SELECT reserved_micro_usd,consumed_micro_usd FROM budget_windows').fetchall())==[(0,56)]
    assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM actions').fetchone())==(0,)


@pytest.mark.parametrize('rates',[{}, {'input_rate':0}, {'output_rate':-1}, {'input_rate':True}])
def test_unknown_or_invalid_rates_cannot_reserve_budget(domain,rates):
    ai,worker,args,_,_=budget(domain)
    config=fixture_config(domain)
    if not rates:
        config.pop('input_rate')
    else:
        config.update(rates)
    args['config_version']=domain.writer.call(lambda db:domain.content(db,'provider_config',config))
    with pytest.raises(DomainError,match='COST_CONFIGURATION_REQUIRED'):
        ai.reserve(worker,**args)
    assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM ai_invocations').fetchone())==(0,)
    assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM reservations').fetchone())==(0,)
