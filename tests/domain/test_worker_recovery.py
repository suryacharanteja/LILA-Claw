import pytest
from conftest import uid
from test_ai import budget
from lila.domain.core import DomainError
from lila.domain.worker_leases import renew


def test_worker_heartbeats_extend_valid_lease_but_never_revive_expiry(domain):
    ai,worker,args,_,_=budget(domain)
    domain.test_clock[0]+=8
    renew(domain,worker)
    domain.test_clock[0]+=8
    ai.reserve(worker,**args)
    domain.test_clock[0]+=11
    renew(domain,worker)
    with pytest.raises(DomainError,match='STALE_LEASE'):
        ai.claim(worker,args['invocation_id'],1)


def test_restart_releases_unsent_ai_and_retains_claimed_budget(domain):
    ai,worker,args,_,_=budget(domain)
    ai.reserve(worker,**args)
    unsent=args['invocation_id']
    args['invocation_id']=uid()
    ai.reserve(worker,**args)
    ai.claim(worker,args['invocation_id'],1)
    ai.recover()
    ai.recover()
    assert domain.writer.call(lambda db:db.execute('SELECT state FROM ai_invocations WHERE id=?',(unsent,)).fetchone())==('REJECTED',)
    assert domain.writer.call(lambda db:db.execute('SELECT state FROM ai_invocations WHERE id=?',(args['invocation_id'],)).fetchone())==('UNCERTAIN',)
    states=domain.writer.call(lambda db:db.execute('SELECT state FROM reservations ORDER BY state').fetchall())
    assert states==[('RELEASED',),('UNCERTAIN',)]
