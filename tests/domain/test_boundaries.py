import secrets
from datetime import datetime,timezone
import pytest
from fastapi.testclient import TestClient
from lila.api.auth import create_app
from lila.api.domain import attach_domain
from lila.domain.core import DomainError,validate
from lila.security.sessions import Sessions,seconds
from lila.storage.writer import StoreWriter
from conftest import uid,action,policy


def test_timezone_changes_roundtrip_and_late_release(domain):
    a,w,l,t,_ = action(domain)
    p,body = policy(domain,cap=1)
    domain.dispatch_intent(a,p,w,l,1)
    domain.policy_command(domain.owner,p,uid(),1,'revise',dict(body,timezone='America/New_York'))
    domain.policy_command(domain.owner,p,uid(),2,'revise',body)
    assert domain.writer.call(lambda db:db.execute('SELECT reserved_actions FROM budget_windows').fetchall())==[(1,),(1,)]
    domain.task_command(domain.owner,t,{'command_id':uid(),'expected_revision':2,'operation':'stop'})
    assert domain.writer.call(lambda db:db.execute('SELECT reserved_actions FROM budget_windows').fetchall())==[(0,),(0,)]


@pytest.mark.parametrize('date,hours',[('2027-03-14T12:00:00+00:00',23),('2027-11-07T12:00:00+00:00',25)])
def test_calendar_windows_follow_dst(domain,date,hours):
    domain.test_clock[0]=datetime.fromisoformat(date).timestamp()
    p,_ = policy(domain,zone='America/New_York')
    window = domain.writer.call(lambda db:domain._window(db,p))
    start,end = domain.writer.call(lambda db:db.execute('SELECT starts_at,ends_at FROM budget_windows WHERE id=?',(window,)).fetchone())
    assert seconds(end)-seconds(start)==hours*3600


def test_cross_account_policy_and_exact_membership(domain):
    a,w,l,_,_ = action(domain)
    _,body = policy(domain)
    other = domain.register_account('other')
    p = domain.create_policy(domain.owner,dict(body,command_id=uid(),account_id=other))['entity_id']
    with pytest.raises(DomainError,match='POLICY_REQUIRED'):
        domain.dispatch_intent(a,p,w,l,1)
    preview = domain.prepare_review([a])
    with pytest.raises(DomainError,match='REVISION_CONFLICT'):
        domain.approval_command(domain.owner,preview['review_id'],{'command_id':uid(),'expected_revision':1,'operation':'approve','payload_version':preview['payload_version'],'members':[{'action_id':a,'payload_version':uid()}]})
    assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM approvals').fetchone()[0])==0


def test_repost_review_and_owner_report_are_distinct(domain):
    metadata = {'company':'Example','title':'Engineer','location':'Dubai'}
    first = domain.register_job(domain.account_id,external_id='111',metadata=metadata)
    second = domain.register_job(domain.account_id,external_id='222',metadata=metadata)
    with pytest.raises(DomainError,match='POSSIBLE_DUPLICATE'):
        domain.writer.call(lambda db:domain._identity_ready(db,second['application_id']))
    review = domain.writer.call(lambda db:db.execute('SELECT id FROM duplicate_reviews').fetchone()[0])
    domain.duplicate_decision(domain.owner,review,uid(),1,'SAME')
    receipt = domain.manual_outcome(domain.owner,first['application_id'],{'command_id':uid(),'expected_revision':1,'operation':'mark_submitted'})
    assert receipt['state']=='USER_REPORTED'
    with pytest.raises(DomainError,match='DUPLICATE_APPLICATION'):
        domain.writer.call(lambda db:domain._identity_ready(db,second['application_id']))


def test_api_session_csrf_schema_receipt_and_events(domain,tmp_path):
    auth = StoreWriter(tmp_path/'auth.db',secrets.token_bytes(32),'auth')
    try:
        sessions = Sessions(auth,secrets.token_bytes(32))
        app = create_app(sessions,43127)
        attach_domain(app,sessions,domain)
        url = 'https://127.0.0.1:43127'
        with TestClient(app,base_url=url) as client:
            assert client.get('/api/v1/events').status_code==401
            result = client.post('/api/v1/auth/bootstrap',headers={'Origin':url},json={'token':sessions.issue_bootstrap()})
            headers = {'Origin':url,'X-Lila-CSRF':result.json()['csrf_token']}
            body = {'command_id':uid(),'account_id':domain.account_id,'instruction':'Find jobs','criteria':{'titles':[],'locations':[],'conditions':[]}}
            assert client.post('/api/v1/tasks',headers={'Origin':url},json=body).status_code==403
            assert client.post('/api/v1/tasks',headers=headers,json=dict(body,authority=True)).status_code==422
            result = client.post('/api/v1/tasks',headers=headers,json=body)
            assert result.status_code==200
            receipt = result.json()
            assert client.get('/api/v1/commands/'+body['command_id']).json()==receipt
            assert client.get('/api/v1/tasks/'+receipt['entity_id']).json()['state']=='DRAFT'
            events = domain.events_page(result.json()['entity_id'])
            assert events['events'][0]['kind']=='TASK_CREATED'
            assert 'Find jobs' not in str(events)
            assert domain.events_page(result.json()['entity_id'],events['next_cursor'])['events']==[]
            assert client.get('/api/v1/tasks',params={'account_id':domain.account_id}).json()['items'][0]['id']==receipt['entity_id']
            assert client.get('/api/v1/tasks',params={'account_id':domain.account_id,'limit':10000}).status_code==422
    finally:
        auth.close()


@pytest.mark.parametrize('value',[1.5,2**63,float('nan')])
def test_invalid_fact_numbers_rejected(value):
    with pytest.raises(DomainError,match='INVALID_REQUEST'):
        validate('FactCommand',{'command_id':uid(),'operation':'verify','field_key':'age','value':value})
