import asyncio
import json
import httpx
import pytest
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from conftest import task,uid
from lila.api.auth import create_app
from lila.api.checkpoints import attach_checkpoints
from lila.api.work import attach_work
from lila.domain.work import Work
from lila.runtime.worker import WorkerRegistry
from lila.worker.task_loop import run_assignment
from lila.domain.core import DomainError


class Browser:
    def __init__(self,jobs=None):
        self.jobs=jobs or []
        self.calls=0
    def ready(self,account):
        return True
    def discover_page(self,account,criteria,cursor,size):
        self.calls+=1
        return {'jobs':self.jobs,'next_cursor':None,'exhausted':True}
    def form_context(self,account,job):
        return {'field_keys':['name'],'domain':'www.linkedin.com','tab_id':1,'narrative_required':False}


@pytest.mark.parametrize('blocker',['pause','unavailable'])
def test_completion_blocker_after_final_checkpoint_waits_and_recovers(domain,blocker):
    browser=Browser()
    tid,boot,work,app=prepare(domain,browser)
    original_readiness=domain.readiness
    class BlockCompletion(httpx.ASGITransport):
        injected=False
        async def handle_async_request(self,request):
            if request.url.path.endswith('/work/acknowledge') and json.loads(request.content)['state']=='DONE' and not self.injected:
                self.injected=True
                if blocker=='pause':
                    domain.task_command(domain.owner,tid,{'command_id':uid(),'expected_revision':domain.task(tid)['revision'],'operation':'pause'})
                else:
                    domain.readiness=lambda:['BROWSER_UNAVAILABLE']
            return await super().handle_async_request(request)
    async def run():
        async with httpx.AsyncClient(transport=BlockCompletion(app=app),base_url='https://127.0.0.1:43127',headers={'Authorization':'Bearer '+boot['token'],'X-Lila-Generation':'1'}) as client:
            assignment=(await client.post('/internal/v1/work/next',json={})).json()
            await run_assignment(client,assignment)
            reason='EXECUTION_PAUSED' if blocker=='pause' else 'EXECUTION_UNAVAILABLE'
            assert domain.writer.call(lambda db:db.execute('SELECT state,error_code FROM worker_jobs').fetchone())==('WAITING',reason)
            assert domain.task(tid)['state']!='COMPLETED'
            assert (await client.post('/internal/v1/work/next',json={})).json()=={'available':False}
            if blocker=='pause':
                assert domain.task(tid)['state']=='PAUSED'
                domain.task_command(domain.owner,tid,{'command_id':uid(),'expected_revision':domain.task(tid)['revision'],'operation':'resume'})
            else:
                domain.readiness=original_readiness
                domain.test_clock[0]+=5
            assignment=(await client.post('/internal/v1/work/next',json={})).json()
            assert assignment['available']
            await run_assignment(client,assignment)
    asyncio.run(run())
    assert domain.task(tid)['state']=='COMPLETED'
    assert browser.calls==1
    assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM actions').fetchone())==(0,)


def prepare(domain,browser):
    domain.monotonic=lambda:domain.test_clock[0]
    workers=WorkerRegistry()
    boot=workers.register()
    work=Work(domain,browser)
    tid=task(domain)
    work.configure(domain.owner,tid,uid(),1,2)
    domain.task_command(domain.owner,tid,{'command_id':uid(),'expected_revision':2,'operation':'start'})
    app=create_app(None,43127,workers=workers)
    app.state.fixture_workers=workers
    attach_checkpoints(app,domain,workers)
    attach_work(app,domain,None,workers,work)
    return tid,boot,work,app


def test_transient_checkpoint_read_failure_recovers_without_business_event(domain):
    tid,boot,work,app=prepare(domain,Browser())
    class FailRead(httpx.ASGITransport):
        failed=False
        async def handle_async_request(self,request):
            if request.method=='GET' and request.url.path=='/internal/v1/checkpoints' and not self.failed:
                self.failed=True
                raise httpx.ReadError('Injected unavailable checkpoint transport',request=request)
            return await super().handle_async_request(request)
    async def run():
        async with httpx.AsyncClient(transport=FailRead(app=app),base_url='https://127.0.0.1:43127',headers={'Authorization':'Bearer '+boot['token'],'X-Lila-Generation':'1'}) as client:
            assignment=(await client.post('/internal/v1/work/next',json={})).json()
            await run_assignment(client,assignment)
            assert domain.writer.call(lambda db:db.execute('SELECT error_code FROM worker_jobs').fetchone())==('WORKER_TRANSPORT_ERROR',)
            cursor=domain.writer.call(work._wake_cursor,transaction=False)
            assert (await client.post('/internal/v1/work/next',json={})).json()=={'available':False}
            domain.test_clock[0]+=5
            assert domain.writer.call(work._wake_cursor,transaction=False)==cursor
            assignment=(await client.post('/internal/v1/work/next',json={})).json()
            assert assignment['available']
            await run_assignment(client,assignment)
    asyncio.run(run())
    assert domain.task(tid)['state']=='COMPLETED'
    assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM actions').fetchone())==(0,)


@pytest.mark.parametrize('reason',['FACTS_REQUIRED','AI_RECONCILIATION_REQUIRED'])
def test_elapsed_time_does_not_clear_required_resolution(domain,reason):
    _,boot,work,_=prepare(domain,Browser())
    assignment=work.next(boot['worker_id'])
    work.acknowledge(boot['worker_id'],assignment['run_id'],assignment['lease_id'],1,'WAITING',reason)
    domain.test_clock[0]+=6
    assert work.next(boot['worker_id'])=={'available':False}


@pytest.mark.parametrize('commit',[False,True],ids=['before-ack-commit','after-ack-commit'])
def test_lost_completion_acknowledgement_recovers_without_repeating_discovery(domain,commit):
    browser=Browser()
    tid,boot,work,app=prepare(domain,browser)
    class LoseAcknowledgement(httpx.ASGITransport):
        lost=False
        async def handle_async_request(self,request):
            if request.url.path.endswith('/work/acknowledge') and not self.lost:
                self.lost=True
                if commit:
                    response=await super().handle_async_request(request)
                    assert response.status_code==200
                    await response.aclose()
                raise httpx.ReadError('Injected acknowledgement loss',request=request)
            return await super().handle_async_request(request)
    async def run():
        async with httpx.AsyncClient(transport=LoseAcknowledgement(app=app),base_url='https://127.0.0.1:43127',headers={'Authorization':'Bearer '+boot['token'],'X-Lila-Generation':'1'}) as client:
            assignment=(await client.post('/internal/v1/work/next',json={})).json()
            await run_assignment(client,assignment)
            next_assignment=(await client.post('/internal/v1/work/next',json={})).json()
            assert next_assignment['available'] is (not commit)
            if not commit:
                await run_assignment(client,next_assignment)
            assert (await client.post('/internal/v1/work/next',json={})).json()=={'available':False}
    asyncio.run(run())
    assert domain.task(tid)['state']=='COMPLETED'
    assert browser.calls==1
    assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM actions').fetchone())==(0,)
    assert domain.writer.call(lambda db:db.execute("SELECT count(*) FROM events WHERE kind='RUN_COMPLETE'").fetchone())==(1,)


def test_worker_http_assignment_zero_matches_completes_after_checkpoint(domain):
    browser=Browser()
    tid,boot,work,app=prepare(domain,browser)
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://127.0.0.1:43127',headers={'Authorization':'Bearer '+boot['token'],'X-Lila-Generation':'1'}) as client:
            assignment=(await client.post('/internal/v1/work/next',json={})).json()
            assert assignment['available']
            await run_assignment(client,assignment)
            assert (await client.post('/internal/v1/work/next',json={})).json()=={'available':False}
    asyncio.run(run())
    assert domain.task(tid)['state']=='COMPLETED'
    assert browser.calls==1
    assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM checkpoints').fetchone())[0]>0
    assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM actions').fetchone())[0]==0


def test_worker_waits_for_facts_then_prepares_one_stable_action(domain):
    browser=Browser([{'external_id':'12345','metadata':{'title':'Engineer'}}])
    tid,boot,work,app=prepare(domain,browser)
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://127.0.0.1:43127',headers={'Authorization':'Bearer '+boot['token'],'X-Lila-Generation':'1'}) as client:
            assignment=(await client.post('/internal/v1/work/next',json={})).json()
            await run_assignment(client,assignment)
            assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM actions').fetchone())[0]==0
            domain.fact_command(domain.owner,domain.account_id,{'command_id':uid(),'operation':'verify','field_key':'name','value':'Fixture Owner'})
            assignment=(await client.post('/internal/v1/work/next',json={})).json()
            assert assignment['available']
            await run_assignment(client,assignment)
            assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM actions').fetchone())[0]==1
            # Re-enter after the action-created event; no extra discovery or action.
            assignment=(await client.post('/internal/v1/work/next',json={})).json()
            if assignment['available']:
                await run_assignment(client,assignment)
            assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM actions').fetchone())[0]==1
    asyncio.run(run())
    assert browser.calls==1
    assert domain.task(tid)['state']!='COMPLETED'


def test_unconfigured_or_unavailable_work_never_claimed(domain):
    work=Work(domain)
    tid=task(domain)
    domain.task_command(domain.owner,tid,{'command_id':uid(),'expected_revision':1,'operation':'start'})
    assert work.next(uid())=={'available':False}
    assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM leases').fetchone())[0]==0


def test_browser_observation_does_not_block_pause_and_cannot_publish_after_pause(domain):
    entered,release=Event(),Event()
    class SlowBrowser(Browser):
        def discover_page(self,*args):
            entered.set()
            assert release.wait(5)
            return {'jobs':[{'external_id':'8888','metadata':{}}],'next_cursor':None,'exhausted':True}
    tid,boot,work,_=prepare(domain,SlowBrowser())
    assignment=work.next(boot['worker_id'])
    with ThreadPoolExecutor(2) as pool:
        pending=pool.submit(work.call,boot['worker_id'],assignment['run_id'],assignment['lease_id'],assignment['generation'],'discover_page',[None,25])
        assert entered.wait(2)
        try:
            revision=domain.task(tid)['revision']
            paused=pool.submit(domain.task_command,domain.owner,tid,{'command_id':uid(),'expected_revision':revision,'operation':'pause'})
            assert paused.result(timeout=2)['state']=='PAUSED'
        finally:
            release.set()
        with pytest.raises(DomainError,match='EXECUTION_PAUSED'):
            pending.result(timeout=3)
    assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM jobs').fetchone())[0]==0


def test_replacement_worker_resumes_same_checkpoints_without_rediscovery(domain):
    browser=Browser([{'external_id':'12345','metadata':{'title':'Engineer'}}])
    tid,boot,work,app=prepare(domain,browser)
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://127.0.0.1:43127',headers={'Authorization':'Bearer '+boot['token'],'X-Lila-Generation':'1'}) as client:
            assignment=(await client.post('/internal/v1/work/next',json={})).json()
            await run_assignment(client,assignment)
    asyncio.run(run())
    domain.test_clock[0]+=11
    domain.fact_command(domain.owner,domain.account_id,{'command_id':uid(),'operation':'verify','field_key':'name','value':'Fixture Owner'})
    worker=uid()
    replacement=work.next(worker)
    assert replacement['available'] and replacement['generation']==2
    with pytest.raises(DomainError,match='STALE_LEASE'):
        work.call(boot['worker_id'],replacement['run_id'],replacement['lease_id'],1,'criteria',[])
    assert browser.calls==1


def test_criteria_edit_during_observation_rejects_old_page(domain):
    class EditingBrowser(Browser):
        def discover_page(self,*args):
            domain.revise_criteria(domain.owner,tid,uid(),domain.task(tid)['revision'],{'titles':['Changed'],'locations':[],'conditions':[]})
            return {'jobs':[{'external_id':'9876','metadata':{}}],'next_cursor':None,'exhausted':True}
    tid,boot,work,_=prepare(domain,EditingBrowser())
    assignment=work.next(boot['worker_id'])
    with pytest.raises(DomainError,match='CRITERIA_CHANGED'):
        work.call(boot['worker_id'],assignment['run_id'],assignment['lease_id'],assignment['generation'],'discover_page',[None,25])
    assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM jobs').fetchone())[0]==0


def test_old_criteria_completion_acknowledgement_cannot_complete_revised_task(domain):
    tid,boot,work,_=prepare(domain,Browser([]))
    assignment=work.next(boot['worker_id'])
    domain.revise_criteria(domain.owner,tid,uid(),domain.task(tid)['revision'],{'titles':['Changed'],'locations':[],'conditions':[]})
    work.acknowledge(boot['worker_id'],assignment['run_id'],assignment['lease_id'],assignment['generation'],'DONE')
    assert domain.task(tid)['state']!='COMPLETED'
    assert domain.writer.call(lambda db:db.execute('SELECT state,error_code FROM worker_jobs WHERE run_id=?',(assignment['run_id'],)).fetchone())==('WAITING','CRITERIA_CHANGED')
    replacement=work.next(boot['worker_id'])
    assert replacement['available'] and replacement['namespace']!=assignment['namespace']
