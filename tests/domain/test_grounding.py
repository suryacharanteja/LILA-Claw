import pytest
from conftest import uid
from lila.domain.core import DomainError


def test_fact_reference_cannot_launder_invented_answer(domain):
    domain.fact_command(domain.owner,domain.account_id,{'command_id':uid(),'operation':'verify','field_key':'name','value':'Fixture Owner'})
    version=domain.writer.call(lambda db:db.execute('SELECT current_version FROM facts').fetchone())[0]
    job=domain.register_job(domain.account_id,external_id='76543')
    for value in ({'name':'Invented name'},{'salary':100000},{'name':'Fixture Owner','degree':'Invented doctorate'}):
        with pytest.raises(DomainError,match='UNSUPPORTED_FACTUAL_ANSWER'):
            domain.create_draft(job['application_id'],value,[version])
    assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM drafts').fetchone())[0]==0


def test_grounded_narrative_rejects_stale_fact_before_publication(domain):
    domain.fact_command(domain.owner,domain.account_id,{'command_id':uid(),'operation':'verify','field_key':'summary','value':'I built a Python application.'})
    version=domain.writer.call(lambda db:db.execute('SELECT current_version FROM facts').fetchone())[0]
    job=domain.register_job(domain.account_id,external_id='76543')
    value={'narrative':{'segments':[{'kind':'fact','fact_ref':version,'text':'I built a Python application.'}],'missing_fields':[]}}
    assert domain.create_draft(job['application_id'],value,[version])['draft_id']
    domain.fact_command(domain.owner,domain.account_id,{'command_id':uid(),'expected_revision':1,'operation':'mark_stale','field_key':'summary','value':'I built a Python application.'})
    with pytest.raises(DomainError,match='FACTS_REQUIRED'):
        domain.create_draft(job['application_id'],value,[version])
