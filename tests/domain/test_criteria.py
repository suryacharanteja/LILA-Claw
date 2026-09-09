import pytest
from conftest import uid,action,policy
from lila.domain.core import DomainError
from lila.domain.criteria import evaluate


def criteria(field,mode='MUST',values=None):
    return {'titles':['Engineer'],'locations':[],'conditions':[{'field':field,'mode':mode,'values':values or ['100000 USD/year']}]}


def test_unknown_salary_excluded_company_and_preferences():
    assert evaluate(criteria('salary'),{})['eligibility']=='REVIEW'
    assert evaluate(criteria('salary'),{'salary':'120000 EUR/year'})['eligibility']=='REVIEW'
    assert evaluate(criteria('company_exclude',values=['Excluded Co']),{'company':'excluded co'})['eligibility']=='EXCLUDED'
    result = evaluate(criteria('work_mode',mode='PREFERENCE',values=['Remote']),{'work_mode':'On-site'})
    assert result['eligibility']=='ELIGIBLE' and result['preferences'][0]['match'] is False


def test_criteria_edit_cancels_unclaimed_preserves_lineage_and_blocks_unknown(domain):
    a,w,l,t,app = action(domain)
    p,_ = policy(domain)
    domain.dispatch_intent(a,p,w,l,1)
    old = domain.writer.call(lambda db:db.execute('SELECT criteria_version FROM action_criteria WHERE action_id=?',(a,)).fetchone()[0])
    domain.revise_criteria(domain.owner,t,uid(),domain.task(t)['revision'],criteria('salary'))
    assert domain.writer.call(lambda db:db.execute('SELECT state FROM actions WHERE id=?',(a,)).fetchone()[0])=='CANCELED'
    assert domain.writer.call(lambda db:db.execute('SELECT criteria_version FROM action_criteria WHERE action_id=?',(a,)).fetchone()[0])==old
    assert domain.writer.call(lambda db:db.execute('SELECT reserved_actions FROM budget_windows').fetchone()[0])==0
    run,payload,draft = domain.writer.call(lambda db:db.execute('SELECT run_id,payload_version,draft_id FROM actions WHERE id=?',(a,)).fetchone())
    body = {'command_id':uid(),'lease_id':l,'generation':1,'run_id':run,'logical_step_key':uid(),'application_id':app,'payload_version':payload,'draft_id':draft,'kind':'submit_application'}
    new = domain.propose_action(w,body,domain='www.linkedin.com',tab_id=1)['entity_id']
    with pytest.raises(DomainError,match='MANDATORY_CRITERIA_UNRESOLVED'):
        domain.dispatch_intent(new,p,w,l,1)
    assert domain.writer.call(lambda db:db.execute('SELECT eligibility FROM candidates WHERE run_id=?',(run,)).fetchone()[0])=='REVIEW'


def test_conflicting_proposal_is_visible_without_discarding_verified_value(domain):
    domain.fact_command(domain.owner,domain.account_id,{'command_id':uid(),'operation':'verify','field_key':'name','value':'Verified'})
    domain.fact_command(domain.owner,domain.account_id,{'command_id':uid(),'expected_revision':1,'operation':'propose','field_key':'name','value':'Imported'})
    fact = domain.list_entities(domain.owner,'facts',domain.account_id)['items'][0]
    assert fact['value']=='Verified' and fact['revision']==2
    assert fact['proposals'][0]['value']=='Imported'
