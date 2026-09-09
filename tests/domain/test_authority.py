import pytest
from lila.domain.core import DomainError
from conftest import uid,action,policy


def approve(domain,action_id,operation='approve'):
    preview = domain.prepare_review([action_id])
    return domain.approval_command(domain.owner,preview['review_id'],{'command_id':uid(),'expected_revision':1,'operation':operation,'payload_version':preview['payload_version'],'members':preview['members']})


def test_explicit_approval_grants_only_exact_members(domain):
    a,w,l,_,_ = action(domain)
    with pytest.raises(DomainError,match='APPROVAL_REQUIRED'):
        domain.dispatch_intent(a,None,w,l,1)
    approve(domain,a)
    domain.dispatch_intent(a,None,w,l,1)
    domain.claim(a,w,l,1)
    b,w,l,_,_ = action(domain,external_id='456')
    with pytest.raises(DomainError,match='APPROVAL_REQUIRED'):
        domain.dispatch_intent(b,None,w,l,1)


def test_rejection_blocks_standing_permission_for_rejected_version(domain):
    a,w,l,_,_ = action(domain)
    approve(domain,a,'reject')
    p,_ = policy(domain)
    with pytest.raises(DomainError,match='ACTION_REJECTED'):
        domain.dispatch_intent(a,p,w,l,1)


def test_preview_cannot_extend_approved_24_hour_expiry(domain):
    a,_,_,_,_ = action(domain)
    preview = domain.prepare_review([a])
    with pytest.raises(DomainError,match='APPROVAL_EXPIRED'):
        domain.approval_command(domain.owner,preview['review_id'],{'command_id':uid(),'expected_revision':1,'operation':'approve','payload_version':preview['payload_version'],'members':preview['members'],'expires_at':'2030-01-01T00:00:00Z'})


def test_single_executor_and_owner_report_survives_old_action_failure(domain):
    a,w,l,_,app = action(domain)
    approve(domain,a)
    domain.dispatch_intent(a,None,w,l,1)
    domain.claim(a,w,l,1)
    b,bw,bl,_,_ = action(domain,external_id='456')
    approve(domain,b)
    domain.dispatch_intent(b,None,bw,bl,1)
    with pytest.raises(DomainError,match='EXECUTOR_BUSY'):
        domain.claim(b,bw,bl,1)
    domain.manual_outcome(domain.owner,app,{'command_id':uid(),'expected_revision':1,'operation':'mark_submitted'})
    domain.record_outcome(a,'FAILED',evidence={'fixture':'old automation did not submit'},not_submitted_proven=True)
    assert domain.writer.call(lambda db:db.execute('SELECT effective_outcome FROM applications WHERE id=?',(app,)).fetchone()[0])=='USER_REPORTED'
    with pytest.raises(DomainError,match='DUPLICATE_APPLICATION'):
        domain.writer.call(lambda db:domain._identity_ready(db,app))


def test_review_preparation_replay_and_material_details(domain):
    a,_,_,_,_ = action(domain)
    command = uid()
    result = domain.prepare_review([a],principal=domain.owner,command_id=command)
    assert domain.prepare_review([a],principal=domain.owner,command_id=command)==result
    preview = domain.review(result['review_id'])
    assert preview['actions'][0]['destination']=='https://www.linkedin.com/jobs/view/123/'
    assert preview['actions'][0]['answers']=={'name':'Fixture Owner'}
    assert preview['actions'][0]['facts_current'] is True
