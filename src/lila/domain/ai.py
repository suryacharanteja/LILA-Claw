"""Serialized AI reservations and billing reconciliation; no network in transactions."""
import hashlib
from uuid import uuid4
from lila.contracts.canonical import canonical
from lila.domain.core import DomainError, identifier
from lila.security.sessions import seconds
from lila.worker.provider import validate_config, ProviderError, money, MAX_INPUT, MAX_OUTPUT


class AI:
    def __init__(self, domain):
        self.domain = domain

    def recover(self):
        def change(db):
            rows=db.execute("SELECT a.id,a.state,r.id,r.window_id,r.amount_micro_usd FROM ai_invocations a JOIN reservations r ON r.id=a.reservation_id WHERE a.state IN('RESERVED','CLAIMED')").fetchall()
            for invocation,state,reservation,window,amount in rows:
                if state=='RESERVED':
                    self.domain._window_delta(db,window,money_reserved=-amount)
                    db.execute("UPDATE reservations SET state='RELEASED' WHERE id=?",(reservation,))
                    db.execute("UPDATE ai_invocations SET state='REJECTED' WHERE id=?",(invocation,))
                else:
                    db.execute("UPDATE reservations SET state='UNCERTAIN' WHERE id=?",(reservation,))
                    db.execute("UPDATE ai_invocations SET state='UNCERTAIN' WHERE id=?",(invocation,))
                self.domain.event(db,'AI_RECOVERED','invocation',invocation,3)
        with self.domain.dispatch_lock:
            self.domain.writer.call(change)

    def _config(self, db, version):
        row = db.execute("SELECT kind FROM content_versions WHERE id=?", (identifier(version),)).fetchone()
        if row != ("provider_config",):
            raise DomainError("COST_CONFIGURATION_REQUIRED",422)
        if db.execute("SELECT 1 FROM ai_invocations WHERE config_version=? AND state='BOUND_EXCEEDED'", (version,)).fetchone():
            raise DomainError("COST_BOUND_INVALIDATED",422)
        value = self.domain.value(db, version)
        try:
            return validate_config(value,self.domain.clock())
        except ProviderError as exc:
            raise DomainError(str(exc),422) from None

    def _current_config(self,db,run,version):
        row=db.execute('SELECT p.config_version FROM provider_settings p JOIN tasks t ON t.account_id=p.account_id JOIN runs r ON r.task_id=t.id WHERE r.id=?',(run,)).fetchone()
        if row and row!=(version,):
            raise DomainError('PROVIDER_CONFIGURATION_CHANGED',403)

    def reserve(self, worker, *, invocation_id, run_id, lease_id, generation, config_version, policy_id, request_digest):
        worker, invocation_id, run_id, lease_id, config_version, policy_id = map(identifier,(worker,invocation_id,run_id,lease_id,config_version,policy_id))
        if type(generation) is not int or generation<1 or not isinstance(request_digest,str) or len(request_digest)!=64 or any(c not in '0123456789abcdef' for c in request_digest):
            raise DomainError("INVALID_REQUEST",422)
        def change(db):
            account = self.domain._lease(db,lease_id,worker,generation,run_id)
            config = self._config(db,config_version)
            self._current_config(db,run_id,config_version)
            policy = db.execute("SELECT account_id,expires_at,revoked_at,budget_micro_usd FROM policies WHERE id=?",(policy_id,)).fetchone()
            if not policy or policy[0]!=account:
                raise DomainError("SCOPE_DENIED",403)
            if policy[2] or seconds(policy[1])<=self.domain.clock():
                raise DomainError("POLICY_EXPIRED",403)
            existing = db.execute("SELECT a.run_id,a.config_version,a.request_digest,a.reservation_id,o.worker_id,o.generation,o.lease_id,o.policy_id,a.state FROM ai_invocations a JOIN ai_ownership o ON o.invocation_id=a.id WHERE a.id=?",(invocation_id,)).fetchone()
            if existing:
                if (existing[0],existing[1],existing[2],*existing[4:8])!=(run_id,config_version,request_digest,worker,generation,lease_id,policy_id):
                    raise DomainError("INVOCATION_ID_REUSED")
                return {"reservation_id":existing[3],"state":existing[8],"may_send":False}
            amount = money(MAX_INPUT,MAX_OUTPUT,config["input_rate"],config["output_rate"])
            window = self.domain._window(db,policy_id)
            spent = db.execute("SELECT reserved_micro_usd+consumed_micro_usd FROM budget_windows WHERE id=?",(window,)).fetchone()[0]
            if spent+amount>policy[3]:
                raise DomainError("BUDGET_EXHAUSTED",422)
            reservation = str(uuid4())
            db.execute("INSERT INTO reservations VALUES(?,?,?,NULL,?,?,'RESERVED')",(reservation,window,run_id,invocation_id,amount))
            db.execute("INSERT INTO ai_invocations(id,run_id,config_version,request_digest,reservation_id,state) VALUES(?,?,?,?,?,'RESERVED')",(invocation_id,run_id,config_version,request_digest,reservation))
            db.execute("INSERT INTO ai_ownership VALUES(?,?,?,?,?,NULL,NULL)",(invocation_id,worker,generation,lease_id,policy_id))
            self.domain._window_delta(db,window,money_reserved=amount)
            self.domain.event(db,"AI_RESERVED","invocation",invocation_id,1)
            return {"reservation_id":reservation,"state":"RESERVED","amount_micro_usd":amount,"may_send":False}
        with self.domain.dispatch_lock:
            return self.domain.writer.call(change)

    def claim(self, worker, invocation_id, generation):
        """One-time permission to send. Replaying the claim never authorizes a resend."""
        def change(db):
            row = db.execute("SELECT a.run_id,a.state,o.worker_id,o.generation,o.lease_id,o.policy_id,a.config_version FROM ai_invocations a JOIN ai_ownership o ON o.invocation_id=a.id WHERE a.id=?",(identifier(invocation_id),)).fetchone()
            if not row or row[2:4]!=(identifier(worker),generation):
                raise DomainError("SCOPE_DENIED",403)
            self.domain._lease(db,row[4],worker,generation,row[0])
            self._config(db,row[6])
            self._current_config(db,row[0],row[6])
            policy = db.execute("SELECT expires_at,revoked_at,budget_micro_usd FROM policies WHERE id=?",(row[5],)).fetchone()
            window = self.domain._window(db,row[5])
            total = db.execute("SELECT reserved_micro_usd+consumed_micro_usd FROM budget_windows WHERE id=?",(window,)).fetchone()[0]
            reserved = db.execute("SELECT r.window_id,r.amount_micro_usd FROM reservations r JOIN ai_invocations a ON a.reservation_id=r.id WHERE a.id=?",(invocation_id,)).fetchone()
            if policy[1] or seconds(policy[0])<=self.domain.clock() or total+(reserved[1] if window!=reserved[0] and (window,) not in self.domain._linked_windows(db,reserved[0]) else 0)>policy[2]:
                raise DomainError("BUDGET_OR_POLICY_CHANGED",403)
            if row[1]!="RESERVED":
                return {"may_send":False,"state":row[1]}
            if window!=reserved[0]:
                self.domain._window_delta(db,reserved[0],money_reserved=-reserved[1])
                self.domain._window_delta(db,window,money_reserved=reserved[1])
                db.execute("UPDATE reservations SET window_id=? WHERE invocation_id=?",(window,invocation_id))
            db.execute("UPDATE ai_invocations SET state='CLAIMED' WHERE id=?",(invocation_id,))
            db.execute("UPDATE ai_ownership SET claimed_at=? WHERE invocation_id=?",(self.domain.stamp(),invocation_id))
            self.domain.event(db,"AI_CLAIMED","invocation",invocation_id,2)
            return {"may_send":True,"state":"CLAIMED"}
        with self.domain.dispatch_lock:
            return self.domain.writer.call(change)

    def result(self, worker, invocation_id, generation, *, status, input_tokens=None, output_tokens=None, provider_request_id=None):
        # Content publication is separate and requires a fresh lease and factual checks.
        # Old authenticated owners may reconcile billing for only their existing claim.
        if status not in {"COMPLETED","INVALID","REJECTED","UNCERTAIN","BOUND_EXCEEDED"}:
            raise DomainError("INVALID_REQUEST",422)
        if provider_request_id is not None and (not isinstance(provider_request_id,str) or not 1<=len(provider_request_id)<=200):
            raise DomainError("INVALID_REQUEST",422)
        if status in {"COMPLETED","INVALID","BOUND_EXCEEDED"}:
            if any(type(v) is not int or not 0<=v<2**63 for v in (input_tokens,output_tokens)):
                raise DomainError("INVALID_USAGE",422)
        elif input_tokens is not None or output_tokens is not None:
            raise DomainError("INVALID_USAGE",422)
        digest = hashlib.sha256(canonical([status,input_tokens,output_tokens,provider_request_id])).hexdigest()
        def change(db):
            row = db.execute("SELECT a.state,a.config_version,a.reservation_id,o.worker_id,o.generation,o.result_digest,r.window_id,r.amount_micro_usd,r.state FROM ai_invocations a JOIN ai_ownership o ON o.invocation_id=a.id JOIN reservations r ON r.id=a.reservation_id WHERE a.id=?",(identifier(invocation_id),)).fetchone()
            if not row or row[3:5]!=(identifier(worker),generation):
                raise DomainError("SCOPE_DENIED",403)
            if row[5] == digest:
                return {"state":row[0],"may_dispatch":False}
            if row[0] not in {"CLAIMED","UNCERTAIN"} or row[8] not in {"RESERVED","UNCERTAIN"}:
                raise DomainError("AI_RESULT_CONFLICT")
            cost = None
            if status=="UNCERTAIN":
                db.execute("UPDATE reservations SET state='UNCERTAIN' WHERE id=?",(row[2],))
            elif status=="REJECTED":
                cost = 0
                self.domain._window_delta(db,row[6],money_reserved=-row[7])
                db.execute("UPDATE reservations SET state='RELEASED' WHERE id=?",(row[2],))
            else:
                config = self.domain.value(db,row[1])  # Historical rates survive expiry.
                cost = money(input_tokens,output_tokens,config['input_rate'],config['output_rate'])
                if input_tokens>MAX_INPUT or output_tokens>MAX_OUTPUT:
                    effective_status = "BOUND_EXCEEDED"
                else:
                    effective_status = status
                self.domain._window_delta(db,row[6],money_reserved=-row[7],money_consumed=cost)
                db.execute("UPDATE reservations SET state='CONSUMED' WHERE id=?",(row[2],))
            final_status = effective_status if status not in {"UNCERTAIN","REJECTED"} else status
            db.execute("UPDATE ai_invocations SET state=?,input_tokens=?,output_tokens=?,cost_micro_usd=?,provider_request_id=? WHERE id=?",(final_status,input_tokens,output_tokens,cost,provider_request_id,invocation_id))
            db.execute("UPDATE ai_ownership SET result_digest=? WHERE invocation_id=?",(digest,invocation_id))
            self.domain.event(db,"AI_"+final_status,"invocation",invocation_id,3)
            return {"state":final_status,"cost_micro_usd":cost,"may_dispatch":False}
        with self.domain.dispatch_lock:
            return self.domain.writer.call(change)
