from uuid import uuid4,uuid5,NAMESPACE_URL
from lila.contracts.canonical import canonical
from lila.domain.core import DomainError, identifier, validate
from lila.security.sessions import seconds, timestamp


class Ledger:
    def _live(self, db, run_id):
        self.check_time()
        row = db.execute("SELECT r.state,r.individual_hold,r.stop_requested,t.account_id FROM runs r JOIN tasks t ON t.id=r.task_id WHERE r.id=?", (run_id,)).fetchone()
        if not row:
            raise DomainError("NOT_FOUND", 404)
        if row[0] in {"STOPPED", "COMPLETED"} or row[2]:
            raise DomainError("RUN_TERMINAL")
        if row[1] or db.execute("SELECT global_hold FROM execution_control WHERE id=1").fetchone()[0]:
            raise DomainError("EXECUTION_PAUSED")
        if self.readiness():
            raise DomainError("EXECUTION_UNAVAILABLE")
        return row[3]

    def issue_lease(self, run_id, worker_id, generation):
        """Trusted worker adapter supplies its authenticated identity/generation."""
        if type(generation) is not int or generation < 1:
            raise DomainError("INVALID_REQUEST", 422)
        def change(db):
            self._live(db, identifier(run_id))
            old = db.execute('SELECT max(generation) FROM leases WHERE run_id=?',(run_id,)).fetchone()[0]
            if old is not None and generation<=old:
                raise DomainError('STALE_LEASE',403)
            db.execute("UPDATE leases SET fenced=1 WHERE run_id=?", (run_id,))
            lease = str(uuid4())
            db.execute("INSERT INTO leases VALUES(?,?,?,?,?,0)", (lease, run_id, identifier(worker_id), generation, timestamp(self.clock()+10)))
            self.lease_deadlines[lease] = self.monotonic()+10
            return lease
        with self.dispatch_lock:
            return self.writer.call(change)

    def _lease(self, db, lease_id, worker_id, generation, run_id, *, require_live=True):
        row = db.execute("SELECT run_id,worker_id,generation,expires_at,fenced FROM leases WHERE id=?", (lease_id,)).fetchone()
        if not row or row[:3] != (run_id,worker_id,generation) or row[4] or seconds(row[3]) <= self.clock() or self.monotonic()>=self.lease_deadlines.get(lease_id,0):
            raise DomainError("STALE_LEASE", 403)
        if require_live:
            return self._live(db, run_id)
        self.check_time()
        return None

    def propose_action(self, worker_id, body, *, domain, tab_id):
        """Browser adapter supplies the observed domain/tab; these are not model claims."""
        body = validate("ActionProposal", body)
        if domain != "www.linkedin.com" or type(tab_id) is not int or tab_id < 0:
            raise DomainError("SCOPE_DENIED", 403)
        def change(db):
            account = self._lease(db,body["lease_id"],worker_id,body["generation"],body["run_id"])
            draft = db.execute("SELECT d.application_id,d.content_version,a.account_id FROM drafts d JOIN applications a ON a.id=d.application_id WHERE d.id=?", (body["draft_id"],)).fetchone()
            if draft != (body["application_id"],body["payload_version"],account):
                raise DomainError("SCOPE_DENIED",403)
            old = db.execute("SELECT id,application_id,kind,payload_version,draft_id,generation,revision,state FROM actions WHERE run_id=? AND logical_step_key=?", (body["run_id"],body["logical_step_key"])).fetchone()
            if old:
                if old[1:6] != (body["application_id"],body["kind"],body["payload_version"],body["draft_id"],body["generation"]):
                    raise DomainError("LOGICAL_STEP_REUSED")
                context = db.execute("SELECT domain,tab_id FROM action_contexts WHERE action_id=?",(old[0],)).fetchone()
                if context != (domain,tab_id):
                    raise DomainError("SCOPE_DENIED",403)
                return self.receipt(old[0],old[6],old[7])
            action = str(uuid4())
            db.execute("INSERT INTO actions VALUES(?,?,?,?,?,?,?,NULL,NULL,NULL,'PREPARED',?,1,?)",(action,body["logical_step_key"],body["application_id"],body["run_id"],body["kind"],body["payload_version"],body["draft_id"],body["generation"],self.stamp()))
            db.execute("INSERT INTO action_contexts VALUES(?,?,?)",(action,domain,tab_id))
            criteria_version = db.execute('SELECT t.criteria_version FROM tasks t JOIN runs r ON r.task_id=t.id WHERE r.id=?',(body['run_id'],)).fetchone()[0]
            db.execute('INSERT INTO action_criteria VALUES(?,?)',(action,criteria_version))
            job = db.execute('SELECT job_id FROM applications WHERE id=?',(body['application_id'],)).fetchone()[0]
            self._classify(db,body['run_id'],job)
            self.event(db,"ACTION_PREPARED","action",action,1)
            return self.receipt(action,1,"PREPARED")
        return self.command(worker_id,body["command_id"],["proposal",body,domain,tab_id],change)

    def _action(self,db,action_id):
        cursor = db.execute("SELECT * FROM actions WHERE id=?",(identifier(action_id),))
        row = cursor.fetchone()
        if not row:
            raise DomainError("NOT_FOUND",404)
        return dict(zip((c[0] for c in cursor.description),row))

    def _gate(self,db,action,policy_id,worker_id,lease_id,generation):
        account = self._lease(db,lease_id,worker_id,generation,action["run_id"])
        if db.execute('SELECT 1 FROM run_blockers WHERE run_id=?',(action['run_id'],)).fetchone():
            raise DomainError('READINESS_BLOCKED')
        if generation != action["generation"]:
            raise DomainError("STALE_LEASE",403)
        context = db.execute('SELECT domain,tab_id FROM action_contexts WHERE action_id=?',(action['id'],)).fetchone()
        if not context or self.capability(account,context[0],context[1]) is not True:
            raise DomainError('BROWSER_CAPABILITY_CHANGED',403)
        if not self._facts_ready(db,action["draft_id"],account):
            raise DomainError("FACTS_REQUIRED",422)
        from .grounding import validate_draft
        validate_draft(self,db,action["draft_id"],account)
        artifact = db.execute("SELECT artifact_version FROM drafts WHERE id=?",(action["draft_id"],)).fetchone()[0]
        selected = db.execute('SELECT version_id FROM selected_documents WHERE account_id=?',(account,)).fetchone()
        if artifact and selected and artifact!=selected[0]:
            raise DomainError('DOCUMENT_VERSION_CHANGED',422)
        if artifact:
            # Publication and integrity are checked by the artifact service before dispatch.
            if not hasattr(self,"artifacts"):
                raise DomainError("ARTIFACT_NOT_READY",422)
            self.artifacts.read_in_transaction(db,artifact,account)
        if action["kind"]=="submit_application":
            criteria_row = db.execute('SELECT t.criteria_version,c.criteria_version,j.metadata_version FROM actions a JOIN runs r ON r.id=a.run_id JOIN tasks t ON t.id=r.task_id JOIN action_criteria c ON c.action_id=a.id JOIN applications p ON p.id=a.application_id JOIN jobs j ON j.id=p.job_id WHERE a.id=?',(action['id'],)).fetchone()
            if not criteria_row or criteria_row[0]!=criteria_row[1]:
                raise DomainError('CRITERIA_CHANGED',422)
            from .criteria import evaluate
            classification = evaluate(self.value(db,criteria_row[0]),self.value(db,criteria_row[2]) if criteria_row[2] else {})
            if classification['eligibility']!='ELIGIBLE':
                raise DomainError('MANDATORY_CRITERIA_UNRESOLVED' if classification['eligibility']=='REVIEW' else 'CANDIDATE_EXCLUDED',422)
            self._identity_ready(db,action["application_id"])
            guard = db.execute("SELECT action_id FROM submission_guards WHERE application_id=?",(action["application_id"],)).fetchone()
            if guard and guard[0] != action["id"]:
                raise DomainError("DUPLICATE_APPLICATION")
        rejected = db.execute("SELECT 1 FROM approval_members m JOIN approvals p ON p.id=m.approval_id JOIN actions a ON a.id=m.action_id WHERE a.application_id=? AND m.payload_version=? AND p.state='REJECTED'",(action['application_id'],action['payload_version'])).fetchone()
        if rejected:
            raise DomainError('ACTION_REJECTED',403)
        approval = None
        if action['approval_id']:
            approval = db.execute("SELECT a.account_id,a.state,a.expires_at,m.payload_version FROM approvals a JOIN approval_members m ON m.approval_id=a.id WHERE a.id=? AND m.action_id=?",(action['approval_id'],action['id'])).fetchone()
        exact_authority = bool(approval and approval[0]==account and approval[1]=='ACTIVE' and seconds(approval[2])>self.clock() and approval[3]==action['payload_version'])
        if policy_id is None:
            # Exact approval authorizes this enumerated action once. It grants no AI spending
            # and creates no standing allowance; AI reservations are independently required.
            if not exact_authority:
                raise DomainError('APPROVAL_REQUIRED',403)
            return None
        policy = db.execute("SELECT account_id,revision,scope_version,expires_at,run_cap,daily_cap,budget_micro_usd,revoked_at FROM policies WHERE id=?",(policy_id,)).fetchone()
        if not policy or policy[0]!=account or policy[7] or seconds(policy[3])<=self.clock():
            raise DomainError("POLICY_REQUIRED",403)
        scope = self.value(db,policy[2])
        context = db.execute("SELECT domain,tab_id FROM action_contexts WHERE action_id=?",(action["id"],)).fetchone()
        kind = "prepare_application" if action["kind"] in {"fill_fields","advance_step","attach_document"} else action["kind"]
        if kind not in scope["action_kinds"] or context[0] not in scope["domains"] or context[1] not in scope["tab_scope"]:
            raise DomainError("SCOPE_DENIED",403)
        return policy

    def dispatch_intent(self, action_id, policy_id, worker_id, lease_id, generation):
        """Reserve under the same lock used by pause/stop. Produces no external effect."""
        def change(db):
            action = self._action(db,action_id)
            if action["state"] not in {"PREPARED","READY","WAITING_AUTH"}:
                raise DomainError("INVALID_STATE")
            policy = self._gate(db,action,policy_id,worker_id,lease_id,generation)
            if policy:
                window = self._window(db,policy_id)
                db.execute("INSERT OR IGNORE INTO run_counters VALUES(?,?,0,0)",(action["run_id"],policy_id))
                run = db.execute("SELECT submitted,reserved FROM run_counters WHERE run_id=? AND policy_id=?",(action["run_id"],policy_id)).fetchone()
                daily = db.execute("SELECT submitted,reserved_actions,consumed_micro_usd,reserved_micro_usd FROM budget_windows WHERE id=?",(window,)).fetchone()
                if sum(run)>=policy[4] or sum(daily[:2])>=policy[5]:
                    raise DomainError("ACTION_LIMIT")
                if policy[6] is None or sum(daily[2:])>policy[6]:
                    raise DomainError("BUDGET_LIMIT")
                db.execute("INSERT INTO reservations VALUES(?,?,?,?,NULL,0,'RESERVED')",(str(uuid4()),window,action["run_id"],action_id))
                self._window_delta(db,window,reserved=1)
                db.execute("UPDATE run_counters SET reserved=reserved+1 WHERE run_id=? AND policy_id=?",(action["run_id"],policy_id))
            db.execute("UPDATE actions SET policy_id=?,policy_revision=?,state='DISPATCH_INTENT',revision=revision+1 WHERE id=?",(policy_id,policy[1] if policy else None,action_id))
            if action["kind"]=="submit_application":
                db.execute("INSERT INTO submission_guards VALUES(?,?,'IN_FLIGHT',1)",(action["application_id"],action_id))
            self.event(db,"ACTION_INTENT","action",action_id,action["revision"]+1)
            db.execute('DELETE FROM action_blockers WHERE action_id=?',(action_id,))
            return self.receipt(action_id,action["revision"]+1,"DISPATCH_INTENT")
        return self._action_transition(action_id,change)

    def claim(self,action_id,worker_id,lease_id,generation):
        def change(db):
            action = self._action(db,action_id)
            if action["state"]!="DISPATCH_INTENT":
                raise DomainError("INVALID_STATE")
            if db.execute("SELECT 1 FROM actions WHERE id<>? AND state IN('CLAIMED','DISPATCHED') LIMIT 1",(action_id,)).fetchone():
                raise DomainError('EXECUTOR_BUSY')
            policy = self._gate(db,action,action["policy_id"],worker_id,lease_id,generation)
            if policy and policy[1]!=action["policy_revision"]:
                raise DomainError("POLICY_CHANGED")
            if policy:
                reservation = db.execute('SELECT id,window_id,state FROM reservations WHERE action_id=?',(action_id,)).fetchone()
                if not reservation or reservation[2]!='RESERVED':
                    raise DomainError('RESERVATION_REQUIRED')
                window = self._window(db,action['policy_id'])
                if reservation[1]!=window:
                    self._window_delta(db,reservation[1],reserved=-1)
                    self._window_delta(db,window,reserved=1)
                    db.execute('UPDATE reservations SET window_id=? WHERE id=?',(window,reservation[0]))
                run = db.execute('SELECT submitted,reserved FROM run_counters WHERE run_id=? AND policy_id=?',(action['run_id'],action['policy_id'])).fetchone()
                daily = db.execute('SELECT submitted,reserved_actions,consumed_micro_usd,reserved_micro_usd FROM budget_windows WHERE id=?',(window,)).fetchone()
                if sum(run)>policy[4] or sum(daily[:2])>policy[5]:
                    raise DomainError('ACTION_LIMIT')
                if policy[6] is None or sum(daily[2:])>policy[6]:
                    raise DomainError('BUDGET_LIMIT')
            db.execute("UPDATE actions SET state='CLAIMED',revision=revision+1 WHERE id=?",(action_id,))
            self.event(db,"ACTION_CLAIMED","action",action_id,action["revision"]+1)
            db.execute('DELETE FROM action_blockers WHERE action_id=?',(action_id,))
            return self.receipt(action_id,action["revision"]+1,"CLAIMED")
        return self._action_transition(action_id,change)

    def _action_transition(self,action_id,change):
        with self.dispatch_lock:
            try:
                return self.writer.call(change)
            except DomainError as exc:
                if exc.code in {'CRITERIA_CHANGED','MANDATORY_CRITERIA_UNRESOLVED','CANDIDATE_EXCLUDED','BROWSER_CAPABILITY_CHANGED','FACTS_REQUIRED','ARTIFACT_NOT_READY','ARTIFACT_CORRUPT','DOCUMENT_VERSION_CHANGED','POLICY_REQUIRED','POLICY_CHANGED','APPROVAL_REQUIRED','ACTION_REJECTED','ACTION_LIMIT','BUDGET_LIMIT','READINESS_BLOCKED','EXECUTION_PAUSED'}:
                    code = exc.code
                    def blocked(db):
                        prior = db.execute('SELECT reason FROM action_blockers WHERE action_id=?',(action_id,)).fetchone()
                        if prior==(code,):
                            return
                        db.execute('INSERT INTO action_blockers VALUES(?,?,?) ON CONFLICT(action_id) DO UPDATE SET reason=excluded.reason,occurred_at=excluded.occurred_at',(action_id,code,self.stamp()))
                        db.execute('UPDATE actions SET revision=revision+1 WHERE id=?',(action_id,))
                        revision = db.execute('SELECT revision FROM actions WHERE id=?',(action_id,)).fetchone()[0]
                        self.event(db,'ACTION_BLOCKED','action',action_id,revision,{'reason':code})
                    self.writer.call(blocked)
                raise

    def _cancel_unclaimed(self,db,action_id):
        action = self._action(db,action_id)
        if action["state"] not in {"PREPARED","READY","WAITING_AUTH","DISPATCH_INTENT"}:
            raise DomainError("INVALID_STATE")
        reservation = db.execute("SELECT id,window_id,state FROM reservations WHERE action_id=?",(action_id,)).fetchone()
        if reservation and reservation[2]=="RESERVED":
            self._window_delta(db,reservation[1],reserved=-1)
            db.execute("UPDATE run_counters SET reserved=reserved-1 WHERE run_id=? AND policy_id=?",(action["run_id"],action["policy_id"]))
            db.execute("UPDATE reservations SET state='RELEASED' WHERE id=?",(reservation[0],))
        db.execute("DELETE FROM submission_guards WHERE action_id=? AND reason='IN_FLIGHT'",(action_id,))
        db.execute("UPDATE actions SET state='CANCELED',revision=revision+1 WHERE id=?",(action_id,))
        self.event(db,"ACTION_CANCELED","action",action_id,action["revision"]+1)

    def record_outcome(self, action_id, outcome, *, evidence, not_submitted_proven=False):
        """Trusted reconciliation adapter only. Owner statements use manual_outcome."""
        if outcome not in {"CONFIRMED","FAILED","UNCERTAIN"} or type(not_submitted_proven) is not bool:
            raise DomainError("INVALID_REQUEST",422)
        if not isinstance(evidence,dict) or not evidence or (not_submitted_proven and outcome!="FAILED"):
            raise DomainError("EVIDENCE_REQUIRED",422)
        if outcome=="FAILED" and not not_submitted_proven:
            outcome = "UNCERTAIN"
        def change(db):
            action = self._action(db,action_id)
            if action["state"] in {"CONFIRMED","FAILED"}:
                return self._propose_correction(db,action,outcome,evidence,not_submitted_proven)
            if action["state"] not in {"CLAIMED","DISPATCHED","UNCERTAIN"}:
                raise DomainError("INVALID_STATE")
            return self._settle_outcome(db,action,outcome,evidence,not_submitted_proven)
        request = ['system_outcome',action_id,outcome,evidence,not_submitted_proven]
        command_id = str(uuid5(NAMESPACE_URL,canonical(request).decode()))
        return self.command('00000000-0000-4000-8000-000000000002',command_id,request,change)

    def manual_outcome(self,principal,application_id,body):
        body = validate("ManualOutcome",body)
        def change(db):
            row = db.execute("SELECT revision,effective_outcome FROM applications WHERE id=?",(identifier(application_id),)).fetchone()
            if not row:
                raise DomainError("NOT_FOUND",404)
            if row[0]!=body["expected_revision"]:
                raise DomainError("REVISION_CONFLICT")
            action = db.execute("SELECT id FROM actions WHERE application_id=? AND kind='submit_application' ORDER BY rowid DESC LIMIT 1",(application_id,)).fetchone()
            state = row[1]
            if body['operation'] in {'continue_manually','mark_submitted'}:
                for (pending,) in db.execute("SELECT id FROM actions WHERE application_id=? AND state IN('PREPARED','WAITING_AUTH','READY','DISPATCH_INTENT')",(application_id,)).fetchall():
                    self._cancel_unclaimed(db,pending)
            if body["operation"]=="mark_submitted" and state!="CONFIRMED":
                state = "USER_REPORTED"
                if action:
                    version = self.content(db,"owner_statement",{"note":body.get("note","")})
                    previous = db.execute("SELECT id FROM outcomes WHERE action_id=? ORDER BY rowid DESC LIMIT 1",(action[0],)).fetchone()
                    db.execute("INSERT INTO outcomes VALUES(?,?,'USER_REPORTED',0,'OWNER',?,?,?)",(str(uuid4()),action[0],version,previous[0] if previous else None,self.stamp()))
                db.execute("INSERT INTO submission_guards VALUES(?,?,'USER_REPORTED',1) ON CONFLICT(application_id) DO UPDATE SET reason='USER_REPORTED',revision=revision+1",(application_id,action[0] if action else None))
            # Owner statements cannot prove an uncertain external submission did not happen.
            db.execute("UPDATE applications SET effective_outcome=?,revision=revision+1 WHERE id=?",(state,application_id))
            self.event(db,"MANUAL_"+body["operation"].upper(),"application",application_id,row[0]+1)
            return self.receipt(application_id,row[0]+1,state)
        return self.command(principal,body["command_id"],["manual",application_id,body],change)
