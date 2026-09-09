import pytest
from pathlib import Path
from conftest import action,policy,uid
from lila.domain.core import DomainError


@pytest.mark.parametrize('outcome',['CONFIRMED','FAILED','UNCERTAIN'])
def test_run_cap_counts_attempts_independently_of_daily_cap(domain,outcome):
    first,worker,lease,tid,_=action(domain)
    pid,body=policy(domain,cap=10)
    body['run_cap']=1
    domain.policy_command(domain.owner,pid,uid(),1,'revise',body)
    run=domain.task(tid)['run_id']
    job=domain.register_job(domain.account_id,external_id='456789')
    fact=domain.writer.call(lambda db:db.execute('SELECT current_version FROM facts').fetchone())[0]
    draft=domain.create_draft(job['application_id'],{'name':'Fixture Owner'},[fact])
    proposal={'command_id':uid(),'run_id':run,'lease_id':lease,'generation':1,'logical_step_key':uid(),
              'application_id':job['application_id'],**draft,'kind':'submit_application'}
    second=domain.propose_action(worker,proposal,domain='www.linkedin.com',tab_id=1)['entity_id']
    # Local preparation consumes no action allowance.
    assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM reservations').fetchone())==(0,)
    domain.dispatch_intent(first,pid,worker,lease,1)
    domain.claim(first,worker,lease,1)
    domain.record_outcome(first,outcome,evidence={'fixture':'observed outcome'},not_submitted_proven=outcome=='FAILED')
    with pytest.raises(DomainError,match='ACTION_LIMIT'):
        domain.dispatch_intent(second,pid,worker,lease,1)
    daily=domain.writer.call(lambda db:db.execute('SELECT submitted,reserved_actions FROM budget_windows').fetchone())
    assert sum(daily)==1 and sum(daily)<body['daily_cap']
    assert domain.writer.call(lambda db:db.execute('SELECT submitted,reserved FROM run_counters').fetchone())==daily
    assert domain.writer.call(lambda db:db.execute('SELECT state FROM actions WHERE id=?',(second,)).fetchone())==('PREPARED',)
    assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM reservations WHERE action_id=?',(second,)).fetchone())==(0,)
    assert domain.writer.call(lambda db:db.execute('SELECT reason FROM action_blockers WHERE action_id=?',(second,)).fetchone())==('ACTION_LIMIT',)


def test_failed_attempt_migration_repairs_linked_windows_once(domain):
    first,worker,lease,_,_=action(domain)
    pid,body=policy(domain)
    domain.dispatch_intent(first,pid,worker,lease,1)
    domain.claim(first,worker,lease,1)
    domain.record_outcome(first,'FAILED',evidence={'fixture':'no submission'},not_submitted_proven=True)
    domain.policy_command(domain.owner,pid,uid(),1,'revise',dict(body,timezone='America/New_York'))
    def old_state(db):
        db.execute("UPDATE reservations SET state='RELEASED' WHERE action_id=?",(first,))
        db.execute('UPDATE budget_windows SET submitted=0')
        db.execute('UPDATE run_counters SET submitted=0')
    domain.writer.call(old_state)
    script=(Path(__file__).resolve().parents[2]/'src/lila/storage/migrations/0011_business_failed_attempts.sql').read_text()
    def migrate(db):
        for statement in script.split(';'):
            if statement.strip():
                db.execute(statement)
    for _ in range(2):
        domain.writer.call(migrate)
        assert domain.writer.call(lambda db:db.execute('SELECT submitted,reserved_actions FROM budget_windows').fetchall())==[(1,0),(1,0)]
        assert domain.writer.call(lambda db:db.execute('SELECT submitted,reserved FROM run_counters').fetchall())==[(1,0)]
        assert domain.writer.call(lambda db:db.execute('SELECT state FROM reservations').fetchall())==[('CONSUMED',)]
