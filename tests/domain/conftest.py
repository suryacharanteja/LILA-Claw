import secrets
from uuid import uuid4
import pytest
from lila.domain.service import Domain
from lila.storage.writer import StoreWriter


def uid():
    return str(uuid4())


@pytest.fixture
def domain(tmp_path):
    writer = StoreWriter(tmp_path/'business.db',secrets.token_bytes(32),'business')
    clock = [1800000000.0]
    service = Domain(writer,secrets.token_bytes(32),clock=lambda:clock[0],readiness=lambda:[],capability=lambda account,domain,tab:True)
    service.test_clock = clock
    service.owner = uid()
    service.account_id = service.register_account('fixture-owner')
    yield service
    writer.close()


def task(service):
    receipt = service.create_task(service.owner,{'command_id':uid(),'account_id':service.account_id,'instruction':'Find suitable jobs','criteria':{'titles':['Engineer'],'locations':[],'conditions':[]}})
    return receipt['entity_id']


def action(service,external_id='123',task_id=None):
    task_id = task_id or task(service)
    snapshot = service.task(task_id)
    if not snapshot['run_id']:
        service.task_command(service.owner,task_id,{'command_id':uid(),'expected_revision':1,'operation':'start'})
    run = service.task(task_id)['run_id']
    job = service.register_job(service.account_id,external_id=external_id)
    fact = service.writer.call(lambda db:db.execute('SELECT current_version FROM facts LIMIT 1').fetchone())
    if not fact:
        service.fact_command(service.owner,service.account_id,{'command_id':uid(),'operation':'verify','field_key':'name','value':'Fixture Owner'})
        fact = service.writer.call(lambda db:db.execute('SELECT current_version FROM facts LIMIT 1').fetchone())
    draft = service.create_draft(job['application_id'],{'name':'Fixture Owner'},[fact[0]])
    worker = uid()
    lease = service.issue_lease(run,worker,1)
    body = {'command_id':uid(),'lease_id':lease,'generation':1,'run_id':run,'logical_step_key':uid(),'application_id':job['application_id'],**draft,'kind':'submit_application'}
    receipt = service.propose_action(worker,body,domain='www.linkedin.com',tab_id=1)
    return receipt['entity_id'],worker,lease,task_id,job['application_id']


def policy(service,cap=10,zone='Asia/Dubai'):
    body = {'command_id':uid(),'account_id':service.account_id,'action_kinds':['submit_application'],'domains':['www.linkedin.com'],'tab_scope':[1],'expires_at':'2030-01-01T00:00:00Z','run_cap':cap,'daily_cap':cap,'timezone':zone,'budget_micro_usd':1000000}
    return service.create_policy(service.owner,body)['entity_id'],body
