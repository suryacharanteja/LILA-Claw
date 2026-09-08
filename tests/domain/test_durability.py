import asyncio
import secrets
from concurrent.futures import ThreadPoolExecutor
import pytest
from lila.domain.core import DomainError
from lila.domain.service import Domain
from lila.storage.writer import StoreWriter
from conftest import uid,action,policy,task


def test_receipts_and_holds_survive_reopen(tmp_path):
    key,audit = secrets.token_bytes(32),secrets.token_bytes(32)
    path = tmp_path/'business.db'
    writer = StoreWriter(path,key,'business')
    owner = uid()
    try:
        domain = Domain(writer,audit,readiness=lambda:[])
        domain.owner,domain.account_id = owner,domain.register_account('owner')
        t = task(domain)
        body = {'command_id':uid(),'expected_revision':1,'operation':'start'}
        receipt = domain.task_command(owner,t,body)
        domain.global_command(owner,{'command_id':uid(),'expected_revision':1,'operation':'pause_all'})
    finally:
        writer.close()
    writer = StoreWriter(path,key,'business')
    try:
        domain = Domain(writer,audit,readiness=lambda:[])
        domain.recover()
        assert domain.task_command(owner,t,body)==receipt
        assert domain.task(t)['global_hold']
        assert domain.task(t)['state']=='PAUSED'
    finally:
        writer.close()


def test_pause_claim_race_has_single_serial_order(domain):
    a,w,l,t,_ = action(domain)
    p,_ = policy(domain)
    domain.dispatch_intent(a,p,w,l,1)
    def claim():
        try:
            return domain.claim(a,w,l,1)
        except DomainError as exc:
            return exc.code
    with ThreadPoolExecutor(2) as pool:
        claim_future = pool.submit(claim)
        pause_future = pool.submit(domain.task_command,domain.owner,t,{'command_id':uid(),'expected_revision':2,'operation':'pause'})
        claimed,pause = claim_future.result(),pause_future.result()
    assert pause['state']=='PAUSED'
    assert claimed=='EXECUTION_PAUSED' or claimed['state']=='CLAIMED'
    with pytest.raises(DomainError,match='EXECUTION_PAUSED|INVALID_STATE'):
        domain.claim(a,w,l,1)


def test_identical_outcome_is_idempotent(domain):
    a,w,l,_,_ = action(domain)
    p,_ = policy(domain)
    domain.dispatch_intent(a,p,w,l,1)
    domain.claim(a,w,l,1)
    first = domain.record_outcome(a,'CONFIRMED',evidence={'fixture':'receipt'})
    assert domain.record_outcome(a,'CONFIRMED',evidence={'fixture':'receipt'})==first
    assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM outcomes').fetchone()[0])==1
    assert domain.writer.call(lambda db:db.execute('SELECT submitted FROM budget_windows').fetchone()[0])==1


def test_monotonic_lease_and_backward_wall_time_fail_closed(domain):
    a,w,l,_,_ = action(domain)
    p,_ = policy(domain)
    domain.monotonic = lambda:domain.lease_deadlines[l]+1
    with pytest.raises(DomainError,match='STALE_LEASE'):
        domain.dispatch_intent(a,p,w,l,1)
    domain.monotonic = lambda:domain.lease_deadlines[l]-1
    domain.test_clock[0]-=61
    with pytest.raises(DomainError,match='TIME_UNRELIABLE'):
        domain.dispatch_intent(a,p,w,l,1)


def test_list_cursor_scope_tamper_expiry(domain):
    task(domain)
    task(domain)
    page = domain.list_entities(domain.owner,'tasks',domain.account_id,limit=1)
    assert page['next_cursor']
    next_page = domain.list_entities(domain.owner,'tasks',domain.account_id,page['next_cursor'],limit=1)
    assert next_page['items'][0]['id']!=page['items'][0]['id']
    for owner,kind,token in [(uid(),'tasks',page['next_cursor']),(domain.owner,'facts',page['next_cursor']),(domain.owner,'tasks',page['next_cursor']+'x')]:
        with pytest.raises(DomainError,match='CURSOR_EXPIRED'):
            domain.list_entities(owner,kind,domain.account_id,token)
    domain.test_clock[0]+=86400
    with pytest.raises(DomainError,match='CURSOR_EXPIRED'):
        domain.list_entities(domain.owner,'tasks',domain.account_id,page['next_cursor'])


def test_sse_event_and_expired_cursor_signal(domain,tmp_path):
    from fastapi import Request
    from lila.api.auth import create_app,COOKIE
    from lila.api.domain import attach_domain
    from lila.security.sessions import Sessions
    auth = StoreWriter(tmp_path/'auth.db',secrets.token_bytes(32),'auth')
    try:
        sessions = Sessions(auth,secrets.token_bytes(32))
        session = sessions.consume_bootstrap(sessions.issue_bootstrap())
        app = create_app(sessions,43127)
        attach_domain(app,sessions,domain)
        endpoint = next(route.endpoint for route in app.routes if route.path=='/api/v1/events')
        task(domain)
        async def first(after=None):
            async def receive():
                await asyncio.sleep(100)
            request = Request({'type':'http','method':'GET','path':'/api/v1/events','headers':[(b'cookie',(COOKIE+'='+session['secret']).encode())]},receive)
            response = endpoint(request,after)
            try:
                return await anext(response.body_iterator)
            finally:
                await response.body_iterator.aclose()
        assert 'event: state_event' in asyncio.run(first())
        assert 'event: snapshot_required' in asyncio.run(first('tampered'))
    finally:
        auth.close()
