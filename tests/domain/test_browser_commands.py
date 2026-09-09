from dataclasses import replace
import pytest
from conftest import uid
from lila.browser.commands import Context,validate_command
from lila.domain.core import DomainError


def command():
    body={'protocol_version':1,'action_id':uid(),'run_id':uid(),'generation':1,
          'account_id':uid(),'tab_id':4,'allowed_origin':'https://www.linkedin.com',
          'payload_version':uid(),'expires_at':'2030-01-01T00:00:00Z',
          'tool':'submit_application','adapter_id':'fixture-only',
          'form_fingerprint':'a'*64,'arguments':{}}
    context=Context(body['run_id'],1,body['account_id'],4,body['allowed_origin'],
                    body['adapter_id'],body['payload_version'],True,'a'*64)
    return body,context


def test_browser_command_accepts_matching_context_without_executing():
    body,context=command()
    assert validate_command(body,context,1800000000)==body


@pytest.mark.parametrize('field,value',[
    ('run_id','00000000-0000-4000-8000-000000000001'),('generation',2),
    ('account_id','00000000-0000-4000-8000-000000000001'),('tab_id',5),
    ('origin','https://www.linkedin.com.evil.example'),('origin','http://www.linkedin.com'),
    ('adapter_id','unqualified'),('payload_version','00000000-0000-4000-8000-000000000001'),
    ('connected',False),('form_fingerprint','b'*64),('form_fingerprint',None)])
def test_browser_context_change_rejects_command(field,value):
    body,context=command()
    with pytest.raises(DomainError):
        validate_command(body,replace(context,**{field:value}),1800000000)


def test_browser_expiry_and_arbitrary_code_rejected():
    body,context=command()
    with pytest.raises(DomainError,match='BROWSER_COMMAND_EXPIRED'):
        validate_command(body,context,1893456000)
    body['tool']='Runtime.evaluate'
    with pytest.raises(DomainError):
        validate_command(body,context,1800000000)


@pytest.mark.parametrize('arguments',[{}, {'field_values':[]}, {'field_values':[{'field_key':'name','value':'A'},{'field_key':'name','value':'B'}]}, {'expected_step':'review'}])
def test_fill_requires_nonempty_unique_typed_fields(arguments):
    body,context=command()
    body.update(tool='fill_fields',arguments=arguments)
    with pytest.raises(DomainError):
        validate_command(body,context,1800000000)
