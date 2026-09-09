import asyncio
import io
import json
import secrets
from uuid import uuid4
import httpx
from fastapi.testclient import TestClient
from conftest import uid,task,policy
from test_ai import fixture_config,fact,narrative
from lila.api.auth import create_app
from lila.api.ai import attach_ai
from lila.api.checkpoints import attach_checkpoints
from lila.security.sessions import Sessions
from lila.security.provider_credentials import ProviderCredentials
from lila.storage.writer import StoreWriter
from lila.runtime.worker import WorkerRegistry
from lila.worker.ai_client import invoke
from lila.worker.provider import ResponsesProvider,MODEL


def test_private_ai_flow_dpapi_and_no_resend(domain,tmp_path):
    writer=StoreWriter(tmp_path/'auth.db',secrets.token_bytes(32),'auth')
    sessions=Sessions(writer,secrets.token_bytes(32),domain.clock)
    keys=ProviderCredentials(sessions,secrets.token_bytes(32))
    workers=WorkerRegistry()
    boot=workers.register()
    app=create_app(sessions,43127,workers=workers)
    attach_checkpoints(app,domain,workers)
    attach_ai(app,domain,sessions,workers,keys)
    origin='https://127.0.0.1:43127'
    try:
        with TestClient(app,base_url=origin) as client:
            response=client.post('/api/v1/auth/bootstrap',json={'token':sessions.issue_bootstrap()},headers={'Origin':origin})
            csrf=response.json()['csrf_token']
            headers={'Origin':origin,'X-Lila-CSRF':csrf}
            canary='fixture-provider-secret-'+secrets.token_hex(16)
            body={'command_id':uid(),'provider':'openai','api_key':canary}
            receipt=client.post('/api/v1/provider/credentials',json=body,headers=headers)
            assert receipt.status_code==200 and canary not in receipt.text
            credential=receipt.json()['credential_id']
            assert keys.read(credential)==canary
            assert client.post('/api/v1/provider/credentials',json=body,headers=headers).json()==receipt.json()
            body['api_key']={'invalid':canary}
            rejected=client.post('/api/v1/provider/credentials',json=body,headers=headers)
            assert rejected.status_code==422 and canary not in rejected.text
            assert canary.encode() not in (tmp_path/'auth.db').read_bytes()
            tid=task(domain)
            domain.task_command(domain.owner,tid,{'command_id':uid(),'expected_revision':1,'operation':'start'})
            run=domain.task(tid)['run_id']
            lease=domain.issue_lease(run,boot['worker_id'],1)
            pid,_=policy(domain)
            config=fixture_config(domain)
            version=domain.writer.call(lambda db:domain.content(db,'provider_config',config))
            domain.writer.call(lambda db:db.execute('INSERT INTO provider_settings VALUES(?,?,?,1)',(domain.account_id,version,credential)))
            invocation=uid()
            calls=[]
            def provider(request):
                calls.append(request)
                assert request.headers['Authorization']=='Bearer '+canary
                return httpx.Response(200,json={'id':'fixture-response','model':MODEL,'status':'completed',
                    'usage':{'input_tokens':100,'output_tokens':10},
                    'output':[{'type':'message','role':'assistant','content':[{'type':'output_text','text':json.dumps(narrative(fact()))}]}]})
            async def exercise():
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url=origin,
                    headers={'Authorization':'Bearer '+boot['token'],'X-Lila-Generation':str(boot['generation'])}) as coordinator:
                    args=dict(invocation_id=invocation,run_id=run,lease_id=lease,generation=1,config_version=version,policy_id=pid,facts=[fact()],job_excerpt='fixture job',provider=ResponsesProvider(transport=httpx.MockTransport(provider)))
                    assert (await invoke(coordinator,**args))['status']=='COMPLETED'
                    assert (await invoke(coordinator,**args))['status']=='RECONCILIATION_REQUIRED'
                    assert len(calls)==1
                    assert (await coordinator.post('/internal/v1/ai/credential',json={'invocation_id':invocation,'generation':1})).status_code==403
            asyncio.run(exercise())
    finally:
        writer.close()


def test_configuration_does_not_enable_unqualified_live_provider(domain,tmp_path):
    writer=StoreWriter(tmp_path/'auth.db',secrets.token_bytes(32),'auth')
    sessions=Sessions(writer,secrets.token_bytes(32),domain.clock)
    keys=ProviderCredentials(sessions,secrets.token_bytes(32))
    app=create_app(sessions,43127,workers=WorkerRegistry())
    attach_checkpoints(app,domain,WorkerRegistry())
    attach_ai(app,domain,sessions,WorkerRegistry(),keys)
    origin='https://127.0.0.1:43127'
    try:
        with TestClient(app,base_url=origin) as client:
            auth=client.post('/api/v1/auth/bootstrap',json={'token':sessions.issue_bootstrap()},headers={'Origin':origin}).json()
            headers={'Origin':origin,'X-Lila-CSRF':auth['csrf_token']}
            credential=client.post('/api/v1/provider/credentials',json={'command_id':uid(),'provider':'openai','api_key':'fixture-key'},headers=headers).json()['credential_id']
            config=fixture_config(domain)
            config.pop('token_bound_qualified')
            config.update(command_id=uid(),account_id=domain.account_id,expected_revision=0,credential_id=credential)
            result=client.post('/api/v1/provider/configuration',json=config,headers=headers)
            assert result.status_code==422 and result.json()['code']=='TOKEN_BOUND_QUALIFICATION_REQUIRED'
            config['enabled']=False
            assert client.post('/api/v1/provider/configuration',json=config,headers=headers).status_code==200
    finally:
        writer.close()
