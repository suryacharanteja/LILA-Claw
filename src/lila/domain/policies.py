from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from uuid import uuid4
from lila.domain.core import DomainError,validate,identifier
from lila.security.sessions import seconds,timestamp


class Policies:
    def _check_policy(self,body):
        body = validate("Policy",body)
        try:
            ZoneInfo(body["timezone"])
        except (ZoneInfoNotFoundError,ValueError):
            raise DomainError("INVALID_TIMEZONE",422)
        return body

    def create_policy(self,principal,body):
        body = self._check_policy(body)
        def change(db):
            if seconds(body['expires_at'])<=self.clock():
                raise DomainError('POLICY_EXPIRED',422)
            self.account(db,body["account_id"])
            entity = str(uuid4())
            version = self.content(db,"policy",body)
            db.execute("INSERT INTO policies VALUES(?,?,1,?,?,?,?,?,?,NULL)",(entity,body["account_id"],version,body["expires_at"],body["run_cap"],body["daily_cap"],body["timezone"],body["budget_micro_usd"]))
            db.execute("INSERT INTO policy_versions VALUES(?,1,?)",(entity,version))
            self.event(db,"POLICY_CREATED","policy",entity,1)
            return self.receipt(entity,1,"ACTIVE")
        return self.command(principal,body["command_id"],["policy",body],change)

    def _window(self,db,policy_id):
        policy = db.execute("SELECT timezone FROM policies WHERE id=?",(policy_id,)).fetchone()
        if not policy:
            raise DomainError("NOT_FOUND",404)
        zone = ZoneInfo(policy[0])
        local = datetime.fromtimestamp(self.clock(),zone)
        start = datetime.combine(local.date(),datetime.min.time(),zone)
        end = datetime.combine(local.date()+timedelta(days=1),datetime.min.time(),zone)
        starts,ends = timestamp(start.timestamp()),timestamp(end.timestamp())
        row = db.execute("SELECT id FROM budget_windows WHERE policy_id=? AND starts_at=? AND ends_at=?",(policy_id,starts,ends)).fetchone()
        if row:
            return row[0]
        entity = str(uuid4())
        db.execute("INSERT INTO budget_windows VALUES(?,?,?,?,?,0,0,0,0)",(entity,policy_id,starts,ends,policy[0]))
        return entity

    def _linked_windows(self,db,window):
        return db.execute("WITH RECURSIVE targets(id) AS (SELECT ? UNION SELECT CASE WHEN c.source_id=t.id THEN c.target_id ELSE c.source_id END FROM budget_window_carries c JOIN targets t ON c.source_id=t.id OR c.target_id=t.id) SELECT id FROM targets",(window,)).fetchall()

    def _window_delta(self,db,window,submitted=0,reserved=0,money_reserved=0,money_consumed=0):
        targets = self._linked_windows(db,window)
        for (target,) in targets:
            db.execute("UPDATE budget_windows SET submitted=submitted+?,reserved_actions=reserved_actions+?,reserved_micro_usd=reserved_micro_usd+?,consumed_micro_usd=consumed_micro_usd+? WHERE id=?",(submitted,reserved,money_reserved,money_consumed,target))

    def policy_command(self,principal,policy_id,command_id,expected_revision,operation,policy=None):
        if operation not in {"revise","revoke"}:
            raise DomainError("INVALID_REQUEST",422)
        if operation=="revise":
            policy = self._check_policy(policy)
        def change(db):
            row = db.execute("SELECT account_id,revision,timezone FROM policies WHERE id=?",(identifier(policy_id),)).fetchone()
            if not row:
                raise DomainError("NOT_FOUND",404)
            if row[1]!=expected_revision:
                raise DomainError("REVISION_CONFLICT")
            if operation=="revoke":
                db.execute("UPDATE policies SET revoked_at=?,revision=revision+1 WHERE id=?",(self.stamp(),policy_id))
            else:
                if seconds(policy['expires_at'])<=self.clock():
                    raise DomainError('POLICY_EXPIRED',422)
                if policy["account_id"]!=row[0]:
                    raise DomainError("SCOPE_DENIED",403)
                old_window = self._window(db,policy_id)
                version = self.content(db,"policy",policy)
                db.execute("UPDATE policies SET revision=revision+1,scope_version=?,expires_at=?,run_cap=?,daily_cap=?,timezone=?,budget_micro_usd=? WHERE id=?",(version,policy["expires_at"],policy["run_cap"],policy["daily_cap"],policy["timezone"],policy["budget_micro_usd"],policy_id))
                db.execute("INSERT INTO policy_versions VALUES(?,?,?)",(policy_id,row[1]+1,version))
                if policy["timezone"]!=row[2]:
                    new_window = self._window(db,policy_id)
                    if new_window!=old_window:
                        # Linked windows share one conservative allowance pool, including late outcomes.
                        # Returning to a previously linked timezone neither resets nor doubles usage.
                        if (new_window,) not in self._linked_windows(db,old_window):
                            old_counts = db.execute("SELECT submitted,reserved_actions,reserved_micro_usd,consumed_micro_usd FROM budget_windows WHERE id=?",(old_window,)).fetchone()
                            new_counts = db.execute("SELECT submitted,reserved_actions,reserved_micro_usd,consumed_micro_usd FROM budget_windows WHERE id=?",(new_window,)).fetchone()
                            self._window_delta(db,new_window,*old_counts)
                            self._window_delta(db,old_window,*new_counts)
                            db.execute("INSERT INTO budget_window_carries VALUES(?,?)",(old_window,new_window))
            self.event(db,"POLICY_"+operation.upper(),"policy",policy_id,row[1]+1)
            return self.receipt(policy_id,row[1]+1,"REVOKED" if operation=="revoke" else "ACTIVE")
        return self.command(principal,command_id,["policy_command",policy_id,expected_revision,operation,policy],change)

    def prepare_review(self,action_ids,*,principal=None,command_id=None):
        if not 1<=len(action_ids)<=100 or len(set(action_ids))!=len(action_ids):
            raise DomainError("INVALID_REQUEST",422)
        def change(db):
            members,accounts = [],set()
            for action in action_ids:
                row = db.execute("SELECT a.payload_version,p.account_id FROM actions a JOIN applications p ON p.id=a.application_id WHERE a.id=?",(identifier(action),)).fetchone()
                if not row:
                    raise DomainError("NOT_FOUND",404)
                members.append({"action_id":action,"payload_version":row[0]})
                accounts.add(row[1])
            if len(accounts)!=1:
                raise DomainError("SCOPE_DENIED",403)
            account = accounts.pop()
            entity = str(uuid4())
            version = self.content(db,"review",{"account_id":account,"members":members})
            member_version = self.content(db,"review_members",members)
            db.execute("INSERT INTO review_previews VALUES(?,?,?,?,1,'PENDING')",(entity,account,version,member_version))
            result = {"review_id":entity,"revision":1,"payload_version":version,"members":members}
            self.event(db,'REVIEW_PREPARED','review',entity,1)
            return dict(self.receipt(entity,1,'PENDING'),**result) if principal else result
        if principal:
            return self.command(principal,command_id,['prepare_review',action_ids],change)
        return self.writer.call(change)

    def review(self,review_id):
        def read(db):
            row = db.execute('SELECT account_id,payload_version,members_version,revision,state FROM review_previews WHERE id=?',(identifier(review_id),)).fetchone()
            if not row:
                raise DomainError('NOT_FOUND',404)
            actions = []
            members = self.value(db,row[2])
            for member in members:
                action = self._action(db,member['action_id'])
                target = db.execute('SELECT j.canonical_url,j.external_id FROM applications p JOIN jobs j ON j.id=p.job_id WHERE p.id=?',(action['application_id'],)).fetchone()
                artifact = db.execute('SELECT artifact_version FROM drafts WHERE id=?',(action['draft_id'],)).fetchone()[0]
                blockers = db.execute('SELECT reason FROM action_blockers WHERE action_id=?',(action['id'],)).fetchone()
                actions.append({'action_id':action['id'],'kind':action['kind'],'account_id':row[0],'destination':target[0],'external_job_id':target[1],'payload_version':member['payload_version'],'answers':self.value(db,member['payload_version']),'artifact_version':artifact,'facts_current':self._facts_ready(db,action['draft_id'],row[0]),'blocking_reasons':list(blockers or []),'policy_id':action['policy_id']})
            return {'review_id':review_id,'account_id':row[0],'payload_version':row[1],'members':members,'revision':row[3],'state':row[4],'actions':actions}
        return self.writer.call(read,transaction=False)

    def approval_command(self,principal,review_id,body):
        body = validate("ApprovalCommand",body)
        def change(db):
            row = db.execute("SELECT account_id,payload_version,members_version,revision,state FROM review_previews WHERE id=?",(identifier(review_id),)).fetchone()
            if not row:
                raise DomainError("NOT_FOUND",404)
            if row[3]!=body["expected_revision"] or row[4]!="PENDING" or row[1]!=body["payload_version"] or self.value(db,row[2])!=body["members"]:
                raise DomainError("REVISION_CONFLICT")
            expires = body.get("expires_at",timestamp(self.clock()+86400))
            if not self.clock()<seconds(expires)<=self.clock()+86400:
                raise DomainError("APPROVAL_EXPIRED",422)
            approved = body["operation"]=="approve"
            for member in body["members"]:
                action = db.execute("SELECT payload_version,draft_id FROM actions WHERE id=?",(member["action_id"],)).fetchone()
                if action[0]!=member["payload_version"] or (approved and not self._facts_ready(db,action[1],row[0])):
                    raise DomainError("PREVIEW_STALE",422)
            db.execute("INSERT INTO approvals VALUES(?,?,?,?,?)",(review_id,row[0],expires,"ACTIVE" if approved else "REJECTED",row[3]+1))
            for member in body["members"]:
                db.execute("INSERT INTO approval_members VALUES(?,?,?)",(review_id,member["action_id"],member["payload_version"]))
                if approved:
                    db.execute("UPDATE actions SET approval_id=?,revision=revision+1 WHERE id=?",(review_id,member["action_id"]))
            db.execute("UPDATE review_previews SET state=?,revision=revision+1 WHERE id=?",("APPROVED" if approved else "REJECTED",review_id))
            self.event(db,"REVIEW_"+body["operation"].upper(),"review",review_id,row[3]+1)
            return self.receipt(review_id,row[3]+1,"APPROVED" if approved else "REJECTED")
        return self.command(principal,body["command_id"],["approval",review_id,body],change)
