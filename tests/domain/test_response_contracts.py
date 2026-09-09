from conftest import uid,task,action,policy
from lila.domain.core import validate
from lila.domain.core import DomainError
import pytest


def test_task_receipt_and_stream_events_match_approved_schema(domain):
    t = task(domain)
    command = {'command_id':uid(),'expected_revision':1,'operation':'start'}
    receipt = domain.task_command(domain.owner,t,command)
    validate('Receipt',receipt)
    validate('TaskSnapshot',domain.task(t))
    a,w,l,_,_ = action(domain)
    p,_ = policy(domain)
    domain.capability = lambda account,host,tab:False
    with pytest.raises(DomainError,match='BROWSER_CAPABILITY_CHANGED'):
        domain.dispatch_intent(a,p,w,l,1)
    events = domain.events_page(domain.owner)
    assert events['next_cursor']
    for event in events['events']:
        validate('Event',event)
    assert domain.events_page(domain.owner,events['next_cursor'])['events']==[]
