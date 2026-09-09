import asyncio
import json
import httpx
import pytest
from conftest import uid,policy
from test_work_transport import Browser,prepare
from test_ai import fixture_config
from lila.api.ai import attach_ai
from lila.worker.provider import ResponsesProvider,MODEL
from lila.worker.task_loop import run_assignment


@pytest.mark.parametrize('fault',[None,'uncertain','invalid','lost_usage_reply','lost_publish_reply','oversized','budget','stale_prices'])
def test_graph_provider_result_is_grounded_and_replay_does_not_pay_twice(domain,monkeypatch,fault):
    class NarrativeBrowser(Browser):
        def form_context(self,*args):
            return dict(super().form_context(*args),narrative_required=True,field_keys=[f'field_{i}' for i in range(10)] if fault=='oversized' else ['name'])
    tid,boot,work,app=prepare(domain,NarrativeBrowser([{'external_id':'54321','metadata':{'title':'Engineer'}}]))
    domain.fact_command(domain.owner,domain.account_id,{'command_id':uid(),'operation':'verify','field_key':'name','value':'Fixture Owner'})
    if fault=='oversized':
        for i in range(10):
            domain.fact_command(domain.owner,domain.account_id,{'command_id':uid(),'operation':'verify','field_key':f'field_{i}','value':'X'*2000})
    pid,policy_body=policy(domain)
    if fault=='budget':
        policy_body['budget_micro_usd']=1
        domain.policy_command(domain.owner,pid,uid(),1,'revise',policy_body)
    config=fixture_config(domain)
    if fault=='stale_prices':
        config['checked_at']='2020-01-01T00:00:00Z'
    version=domain.writer.call(lambda db:domain.content(db,'provider_config',config))
    domain.writer.call(lambda db:db.execute('INSERT INTO provider_settings VALUES(?,?,?,1)',(domain.account_id,version,uid())))
    domain.writer.call(lambda db:db.execute('UPDATE task_execution SET policy_id=? WHERE task_id=?',(pid,tid)))
    class Credentials:
        def read(self,credential):
            return 'fixture-key'
    attach_ai(app,domain,None,app.state.fixture_workers,Credentials())
    calls=[]
    def provider(request):
        calls.append(request)
        context=json.loads(json.loads(request.content)['input'][0]['content'][0]['text'])
        fact=context['facts'][0]
        output={'segments':[{'kind':'fact','fact_ref':fact['version_id'],'text':fact['text']}],'missing_fields':[]}
        if fault=='uncertain':
            raise httpx.ReadTimeout('Injected provider timeout',request=request)
        if fault=='invalid':
            output['segments'][0]['text']='Invented qualification'
        return httpx.Response(200,json={'id':'fixture-response','model':MODEL,'status':'completed',
            'usage':{'input_tokens':100,'output_tokens':10},
            'output':[{'type':'message','role':'assistant','content':[{'type':'output_text','text':json.dumps(output)}]}]})
    monkeypatch.setattr('lila.worker.ai_client.ResponsesProvider',lambda:ResponsesProvider(transport=httpx.MockTransport(provider)))
    class LoseReply(httpx.ASGITransport):
        lost=False
        async def handle_async_request(self,request):
            response=await super().handle_async_request(request)
            target=(fault=='lost_usage_reply' and request.url.path.endswith('/ai/results')) or (fault=='lost_publish_reply' and request.url.path.endswith('/work/call') and json.loads(request.content).get('operation')=='publish_narrative')
            if target and not self.lost:
                self.lost=True
                await response.aclose()
                raise httpx.ReadError('Injected lost reply after commit',request=request)
            return response
    async def run():
        async with httpx.AsyncClient(transport=LoseReply(app=app),base_url='https://127.0.0.1:43127',headers={'Authorization':'Bearer '+boot['token'],'X-Lila-Generation':'1'}) as client:
            assignment=(await client.post('/internal/v1/work/next',json={})).json()
            await run_assignment(client,assignment)
            assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM actions').fetchone())[0]==(1 if fault is None else 0)
            expected={None:'OUTCOME_UNRESOLVED','uncertain':'AI_RECONCILIATION_REQUIRED','invalid':'AI_OUTPUT_INVALID','lost_usage_reply':'WORKER_TRANSPORT_ERROR','lost_publish_reply':'WORKER_TRANSPORT_ERROR','oversized':'AI_CONTEXT_TOO_LARGE','budget':'BUDGET_EXHAUSTED','stale_prices':'COST_CONFIGURATION_REQUIRED'}[fault]
            assert domain.writer.call(lambda db:db.execute('SELECT error_code FROM worker_jobs').fetchone())==(expected,)
            if fault in {'oversized','budget','stale_prices'}:
                return
            # A repeated graph resume cannot issue another provider request or action.
            if fault is not None:
                if fault in {'lost_usage_reply','lost_publish_reply'}:
                    domain.test_clock[0]+=5
                assignment=(await client.post('/internal/v1/work/next',json={})).json()
                assert assignment['available']
            await run_assignment(client,assignment)
    asyncio.run(run())
    if fault in {'oversized','budget','stale_prices'}:
        assert calls==[]
        assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM ai_invocations').fetchone())==(0,)
        assert domain.task(tid)['state']=='BLOCKED'
        return
    assert len(calls)==1
    if fault in {None,'lost_publish_reply'}:
        assert domain.writer.call(lambda db:db.execute('SELECT state,cost_micro_usd,response_version IS NOT NULL FROM ai_invocations').fetchone())==('COMPLETED',56,1)
        assert domain.writer.call(lambda db:db.execute('SELECT state FROM actions').fetchall())==[('PREPARED',)]
    else:
        assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM actions').fetchone())==(0,)
        assert domain.writer.call(lambda db:db.execute('SELECT error_code FROM worker_jobs').fetchone())==('AI_RECONCILIATION_REQUIRED',)
    assert domain.task(tid)['state']=='BLOCKED'
