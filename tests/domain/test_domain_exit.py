import pytest
from conftest import uid,action,policy,task
from lila.domain.core import DomainError
from lila.security.sessions import timestamp


def test_new_task_during_global_pause_is_held(domain):
    domain.global_command(domain.owner,{'command_id':uid(),'expected_revision':1,'operation':'pause_all'})
    t = task(domain)
    result = domain.task_command(domain.owner,t,{'command_id':uid(),'expected_revision':1,'operation':'start'})
    assert result['state']=='PAUSED'
    with pytest.raises(DomainError,match='EXECUTION_PAUSED'):
        domain.issue_lease(domain.task(t)['run_id'],uid(),1)


def test_resume_does_not_restore_expired_authority(domain):
    a,w,l,t,_ = action(domain)
    _,body = policy(domain)
    body.update(command_id=uid(),expires_at=timestamp(domain.clock()+4))
    p = domain.create_policy(domain.owner,body)['entity_id']
    domain.task_command(domain.owner,t,{'command_id':uid(),'expected_revision':2,'operation':'pause'})
    domain.test_clock[0]+=5
    domain.task_command(domain.owner,t,{'command_id':uid(),'expected_revision':3,'operation':'resume'})
    with pytest.raises(DomainError,match='POLICY_REQUIRED'):
        domain.dispatch_intent(a,p,w,l,1)


def test_distinct_repost_and_unknown_identity(domain):
    metadata={'company':'Example','title':'Engineer','location':'Dubai'}
    first = domain.register_job(domain.account_id,external_id='777',metadata=metadata)
    assert domain.register_job(domain.account_id,url='https://www.linkedin.com/jobs/view/777/?tracking=x',metadata=metadata)==first
    second = domain.register_job(domain.account_id,external_id='888',metadata=metadata)
    review = domain.writer.call(lambda db:db.execute('SELECT id FROM duplicate_reviews').fetchone()[0])
    domain.duplicate_decision(domain.owner,review,uid(),1,'DISTINCT')
    assert domain.writer.call(lambda db:domain._identity_ready(db,second['application_id']))==domain.account_id
    unknown = domain.register_job(domain.account_id)
    with pytest.raises(DomainError,match='IDENTITY_REQUIRED'):
        domain.writer.call(lambda db:domain._identity_ready(db,unknown['application_id']))


def test_fact_source_scope_and_immutability(domain):
    other = domain.register_account('other')
    source = domain.writer.call(lambda db:domain.content(db,'document_source',{'account_id':other}))
    with pytest.raises(DomainError,match='SCOPE_DENIED'):
        domain.fact_command(domain.owner,domain.account_id,{'command_id':uid(),'operation':'propose','field_key':'name','value':'Other','source_version':source})
    domain.fact_command(domain.owner,domain.account_id,{'command_id':uid(),'operation':'verify','field_key':'name','value':'Verified'})
    from sqlcipher3 import dbapi2
    with pytest.raises(dbapi2.IntegrityError,match='append fact version'):
        domain.writer.call(lambda db:db.execute("UPDATE fact_versions SET status='PROPOSED'"))
