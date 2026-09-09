from uuid import uuid4
from .core import DomainError,identifier,validate


def evaluate(criteria,metadata):
    """Deterministic post-filtering only; never claims native browser filters were applied."""
    excluded,unknown,preferences = [],[],[]
    for condition in criteria['conditions']:
        field = condition['field']
        key = 'company' if field in {'company_include','company_exclude'} else field
        actual = metadata.get(key)
        choices = [v.strip().casefold() for v in condition['values']]
        matched = None
        if field=='posting_age_days':
            if type(actual) is int and actual>=0 and all(v.isascii() and v.isdigit() for v in choices):
                matched = actual<=max(int(v) for v in choices)
        elif isinstance(actual,str) and actual.strip():
            matched = actual.strip().casefold() in choices
            if field=='company_exclude':
                matched = not matched
            elif field=='salary' and not matched:
                # Unspecified currencies/periods/range notation cannot be safely compared.
                matched = None
        if condition['mode']=='PREFERENCE':
            preferences.append({'field':field,'match':matched})
        elif matched is False:
            excluded.append(field)
        elif matched is None:
            unknown.append(field)
    return {'eligibility':'EXCLUDED' if excluded else 'REVIEW' if unknown else 'ELIGIBLE','mismatched_fields':excluded,'unknown_fields':unknown,'preferences':preferences,'evaluation':'post_filter'}


class Criteria:
    def _classify(self,db,run_id,job_id):
        row = db.execute('SELECT t.account_id,t.criteria_version,j.metadata_version FROM runs r JOIN tasks t ON t.id=r.task_id JOIN jobs j ON j.id=? WHERE r.id=?',(job_id,run_id)).fetchone()
        if not row or not db.execute('SELECT 1 FROM applications WHERE job_id=? AND account_id=?',(job_id,row[0])).fetchone():
            raise DomainError('SCOPE_DENIED',403)
        result = evaluate(self.value(db,row[1]),self.value(db,row[2]) if row[2] else {})
        old = db.execute('SELECT id FROM candidates WHERE run_id=? AND job_id=?',(run_id,job_id)).fetchone()
        candidate = old[0] if old else str(uuid4())
        relevance = self.content(db,'candidate_evaluation',result)
        db.execute('INSERT INTO candidates VALUES(?,?,?,?,?,?) ON CONFLICT(run_id,job_id) DO UPDATE SET criteria_version=excluded.criteria_version,eligibility=excluded.eligibility,relevance_version=excluded.relevance_version',(candidate,run_id,job_id,row[1],result['eligibility'],relevance))
        return result

    def revise_criteria(self,principal,task_id,command_id,expected_revision,criteria):
        task_id = identifier(task_id)
        criteria = validate('Criteria',criteria)
        if type(expected_revision) is not int or expected_revision<1:
            raise DomainError('INVALID_REQUEST',422)
        def change(db):
            task = self._task(db,task_id)
            if task[1]!=expected_revision:
                raise DomainError('REVISION_CONFLICT')
            run = self._run(db,task_id)
            if run and run[1] in {'COMPLETED','STOPPED'}:
                raise DomainError('RUN_TERMINAL')
            version = self.content(db,'criteria',criteria)
            db.execute('UPDATE tasks SET criteria_version=?,revision=revision+1 WHERE id=?',(version,task_id))
            if run:
                db.execute('UPDATE run_progress SET discovery_complete=0 WHERE run_id=?',(run[0],))
                for (action,) in db.execute("SELECT id FROM actions WHERE run_id=? AND state IN('PREPARED','WAITING_AUTH','READY','DISPATCH_INTENT')",(run[0],)).fetchall():
                    self._cancel_unclaimed(db,action)
                db.execute("UPDATE approvals SET state='REVOKED',revision=revision+1 WHERE state='ACTIVE' AND id IN(SELECT m.approval_id FROM approval_members m JOIN actions a ON a.id=m.action_id WHERE a.run_id=?)",(run[0],))
                for (job,) in db.execute('SELECT job_id FROM candidates WHERE run_id=?',(run[0],)).fetchall():
                    self._classify(db,run[0],job)
            self.event(db,'TASK_CRITERIA_REVISED','task',task_id,task[1]+1)
            snapshot = self._snapshot(db,task_id)
            return self.receipt(task_id,task[1]+1,snapshot['state'],snapshot['blocking_reasons'])
        return self.command(principal,command_id,['revise_criteria',task_id,expected_revision,criteria],change)
