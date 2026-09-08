from .core import DomainError,identifier

REASONS = {'FACTS_REQUIRED','ARTIFACT_NOT_READY','BROWSER_UNAVAILABLE','WORKER_UNAVAILABLE','POLICY_REQUIRED','APPROVAL_REQUIRED','LIMIT_EXHAUSTED','OUTCOME_UNRESOLVED','UNSUPPORTED_VARIANT','TIME_UNRELIABLE'}


class Lifecycle:
    def lifecycle(self,worker_id,run_id,lease_id,generation,command_id,expected_revision,operation,reasons=None):
        """Authenticated worker service; transition acknowledgments share the control lock."""
        run_id = identifier(run_id)
        reasons = reasons or []
        if operation not in {'activate','await_input','block','ready','discovery_complete','complete'} or type(expected_revision) is not int or expected_revision<1:
            raise DomainError('INVALID_REQUEST',422)
        if not isinstance(reasons,list) or any(not isinstance(reason,str) or reason not in REASONS for reason in reasons):
            raise DomainError('INVALID_REQUEST',422)
        if operation in {'await_input','block'} and not reasons or operation not in {'await_input','block'} and reasons:
            raise DomainError('INVALID_REQUEST',422)
        def change(db):
            self._lease(db,lease_id,worker_id,generation,run_id,require_live=False)
            row = db.execute('SELECT r.task_id,r.state,r.individual_hold,t.revision,t.account_id FROM runs r JOIN tasks t ON t.id=r.task_id WHERE r.id=?',(run_id,)).fetchone()
            if not row or row[1] in {'STOPPED','COMPLETED'}:
                raise DomainError('RUN_TERMINAL')
            if row[3]!=expected_revision:
                raise DomainError('REVISION_CONFLICT')
            if operation in {'activate','complete'}:
                self._live(db,run_id)
                if db.execute('SELECT 1 FROM run_blockers WHERE run_id=?',(run_id,)).fetchone():
                    raise DomainError('READINESS_BLOCKED')
            state = row[1]
            summary = {}
            if operation=='discovery_complete':
                db.execute('UPDATE run_progress SET discovery_complete=1 WHERE run_id=?',(run_id,))
            elif operation=='complete':
                if not db.execute('SELECT discovery_complete FROM run_progress WHERE run_id=?',(run_id,)).fetchone()[0]:
                    raise DomainError('DISCOVERY_INCOMPLETE')
                if db.execute("SELECT 1 FROM actions a JOIN runs r ON r.id=a.run_id WHERE r.task_id=? AND (a.state IN('CLAIMED','DISPATCHED','DISPATCH_INTENT','UNCERTAIN') OR (a.run_id=? AND a.state IN('PREPARED','READY','WAITING_AUTH'))) LIMIT 1",(row[0],run_id)).fetchone():
                    raise DomainError('OUTCOME_UNRESOLVED')
                if db.execute("SELECT 1 FROM candidates c LEFT JOIN applications a ON a.job_id=c.job_id AND a.account_id=? WHERE c.run_id=? AND (c.eligibility='REVIEW' OR (c.eligibility='ELIGIBLE' AND coalesce(a.effective_outcome,'NONE') NOT IN('CONFIRMED','USER_REPORTED') AND NOT EXISTS(SELECT 1 FROM actions x WHERE x.run_id=c.run_id AND x.application_id=a.id AND x.state IN('CONFIRMED','FAILED')))) LIMIT 1",(row[4],run_id)).fetchone():
                    raise DomainError('CANDIDATES_UNPROCESSED')
                state = 'COMPLETED'
                count = db.execute('SELECT count(*) FROM candidates WHERE run_id=?',(run_id,)).fetchone()[0]
                summary = {'reason':'ALL_CANDIDATES_PROCESSED' if count else 'ZERO_MATCHES'}
                db.execute('UPDATE runs SET terminal_at=? WHERE id=?',(self.stamp(),run_id))
                db.execute('UPDATE leases SET fenced=1 WHERE run_id=?',(run_id,))
            else:
                state = {'activate':'ACTIVE','await_input':'AWAITING_INPUT','block':'BLOCKED','ready':'QUEUED'}[operation]
                if operation!='activate':
                    db.execute('DELETE FROM run_blockers WHERE run_id=?',(run_id,))
                    for reason in sorted(set(reasons)):
                        db.execute('INSERT INTO run_blockers VALUES(?,?)',(run_id,reason))
            db.execute('UPDATE runs SET state=?,revision=revision+1 WHERE id=?',(state,run_id))
            db.execute('UPDATE tasks SET revision=revision+1 WHERE id=?',(row[0],))
            self.event(db,'RUN_'+operation.upper(),'task',row[0],row[3]+1,summary)
            snapshot = self._snapshot(db,row[0])
            return self.receipt(row[0],row[3]+1,snapshot['state'],snapshot['blocking_reasons'])
        return self.command(worker_id,command_id,['lifecycle',run_id,lease_id,generation,expected_revision,operation,reasons],change)
