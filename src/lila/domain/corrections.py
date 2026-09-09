import hashlib
import hmac
from uuid import uuid4
from lila.contracts.canonical import canonical
from .core import DomainError,identifier


class Corrections:
    def _propose_correction(self,db,action,outcome,evidence,not_submitted_proven):
        app_revision = db.execute('SELECT revision FROM applications WHERE id=?',(action['application_id'],)).fetchone()[0]
        payload = {'action_id':action['id'],'action_revision':action['revision'],'application_revision':app_revision,'outcome':outcome,'evidence':evidence,'not_submitted_proven':not_submitted_proven}
        digest = hashlib.sha256(canonical(payload)).hexdigest()
        version,operation = self.content(db,'outcome_correction',payload),str(uuid4())
        db.execute("INSERT INTO operations VALUES(?,'OUTCOME_CORRECTION','AWAITING_CONFIRMATION',?,1,NULL,?)",(operation,version,self.stamp()))
        db.execute("INSERT INTO correction_previews VALUES(?,?,?,?,?,?,1,'PENDING')",(operation,action['id'],action['revision'],app_revision,version,digest))
        self.event(db,'OUTCOME_CORRECTION_PROPOSED','operation',operation,1)
        return self.receipt(operation,1,'AWAITING_CONFIRMATION')

    def correction(self,operation_id):
        def read(db):
            row = db.execute('SELECT payload_version,digest,revision,state FROM correction_previews WHERE operation_id=?',(identifier(operation_id),)).fetchone()
            if not row:
                raise DomainError('NOT_FOUND',404)
            return {'operation_id':operation_id,'preview':self.value(db,row[0]),'preview_digest':row[1],'revision':row[2],'state':row[3]}
        return self.writer.call(read,transaction=False)

    def confirm_correction(self,principal,operation_id,command_id,expected_revision,preview_digest):
        if type(expected_revision) is not int or expected_revision<1 or not isinstance(preview_digest,str):
            raise DomainError('INVALID_REQUEST',422)
        def change(db):
            row = db.execute('SELECT action_id,action_revision,application_revision,payload_version,digest,revision,state FROM correction_previews WHERE operation_id=?',(identifier(operation_id),)).fetchone()
            if not row:
                raise DomainError('NOT_FOUND',404)
            if row[5]!=expected_revision or row[6]!='PENDING' or not hmac.compare_digest(row[4],preview_digest):
                raise DomainError('PREVIEW_STALE')
            action = self._action(db,row[0])
            revision = db.execute('SELECT revision FROM applications WHERE id=?',(action['application_id'],)).fetchone()[0]
            if action['revision']!=row[1] or revision!=row[2]:
                raise DomainError('PREVIEW_STALE')
            payload = self.value(db,row[3])
            self._settle_outcome(db,action,payload['outcome'],payload['evidence'],payload['not_submitted_proven'])
            db.execute("UPDATE correction_previews SET state='APPLIED',revision=revision+1 WHERE operation_id=?",(operation_id,))
            db.execute("UPDATE operations SET phase='COMPLETE' WHERE id=?",(operation_id,))
            self.event(db,'OUTCOME_CORRECTION_APPLIED','operation',operation_id,row[5]+1)
            return self.receipt(operation_id,row[5]+1,'APPLIED')
        return self.command(principal,command_id,['confirm_correction',operation_id,expected_revision,preview_digest],change)

    def _settle_outcome(self,db,action,outcome,evidence,not_submitted_proven):
        action_id = action['id']
        previous = db.execute('SELECT id FROM outcomes WHERE action_id=? ORDER BY rowid DESC LIMIT 1',(action_id,)).fetchone()
        version = self.content(db,'outcome_evidence',evidence)
        db.execute('INSERT INTO outcomes VALUES(?,?,?,?,?,?,?,?)',(str(uuid4()),action_id,outcome,int(not_submitted_proven),'SYSTEM',version,previous[0] if previous else None,self.stamp()))
        reservation = db.execute('SELECT id,window_id,state FROM reservations WHERE action_id=?',(action_id,)).fetchone()
        if reservation:
            # A proven failed submission still consumed an attempted action.
            # Only cancellation before send claim releases action allowance.
            new_state = {'CONFIRMED':'CONSUMED','FAILED':'CONSUMED','UNCERTAIN':'UNCERTAIN'}[outcome]
            submitted = int(new_state=='CONSUMED')-int(reservation[2]=='CONSUMED')
            reserved = int(new_state in {'RESERVED','UNCERTAIN'})-int(reservation[2] in {'RESERVED','UNCERTAIN'})
            self._window_delta(db,reservation[1],submitted=submitted,reserved=reserved)
            db.execute('UPDATE run_counters SET reserved=reserved+?,submitted=submitted+? WHERE run_id=? AND policy_id=?',(reserved,submitted,action['run_id'],action['policy_id']))
            db.execute('UPDATE reservations SET state=? WHERE id=?',(new_state,reservation[0]))
        db.execute('UPDATE actions SET state=?,revision=revision+1 WHERE id=?',(outcome,action_id))
        if action['kind']=='submit_application':
            application = action['application_id']
            prior = db.execute('SELECT effective_outcome FROM applications WHERE id=?',(application,)).fetchone()[0]
            rows = db.execute("SELECT id,state FROM actions WHERE application_id=? AND kind='submit_application' ORDER BY rowid DESC",(application,)).fetchall()
            confirmed = next((aid for aid,state in rows if state=='CONFIRMED'),None)
            uncertain = next((aid for aid,state in rows if state=='UNCERTAIN'),None)
            pending = next((aid for aid,state in rows if state in {'DISPATCH_INTENT','CLAIMED','DISPATCHED'}),None)
            effective,guard_action,reason = ('CONFIRMED',confirmed,'CONFIRMED') if confirmed else ('USER_REPORTED',action_id,'USER_REPORTED') if prior=='USER_REPORTED' else ('UNCERTAIN',uncertain,'UNCERTAIN') if uncertain else ('PENDING',pending,'IN_FLIGHT') if pending else ('FAILED',None,None)
            db.execute('UPDATE applications SET effective_outcome=?,revision=revision+1 WHERE id=?',(effective,application))
            if reason:
                db.execute('INSERT INTO submission_guards VALUES(?,?,?,1) ON CONFLICT(application_id) DO UPDATE SET action_id=excluded.action_id,reason=excluded.reason,revision=revision+1',(application,guard_action,reason))
            else:
                db.execute('DELETE FROM submission_guards WHERE application_id=?',(application,))
        self.event(db,'OUTCOME_'+outcome,'action',action_id,action['revision']+1)
        return self.receipt(action_id,action['revision']+1,outcome)
