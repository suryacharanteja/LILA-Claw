from uuid import uuid4
from lila.domain.core import DomainError,validate,identifier


class Facts:
    def fact_command(self,principal,account_id,body):
        account_id = identifier(account_id)
        body = validate("FactCommand",body)
        def change(db):
            self.account(db,account_id)
            row = db.execute("SELECT id,current_version FROM facts WHERE account_id=? AND field_key=?",(account_id,body["field_key"])).fetchone()
            count = db.execute("SELECT count(*) FROM fact_versions WHERE fact_id=?",(row[0],)).fetchone()[0] if row else 0
            if row and body.get("expected_revision")!=count:
                raise DomainError("REVISION_CONFLICT")
            if not row and body.get("expected_revision") is not None:
                raise DomainError("REVISION_CONFLICT")
            source = body.get("source_version")
            if source:
                source_body = self.value(db,source)
                if not isinstance(source_body,dict) or source_body.get("account_id")!=account_id:
                    raise DomainError("SCOPE_DENIED",403)
            if not row:
                fact_id = str(uuid4())
                db.execute("INSERT INTO facts VALUES(?,?,?,NULL)",(fact_id,account_id,body["field_key"]))
                row = (fact_id,None)
            status = {"propose":"PROPOSED","verify":"VERIFIED","mark_stale":"STALE","reject":"REJECTED"}[body["operation"]]
            value = self.content(db,"fact_value",body["value"])
            version = str(uuid4())
            db.execute("INSERT INTO fact_versions VALUES(?,?,?,?,?,?,?)",(version,row[0],value,source,status,row[1],self.stamp()))
            db.execute("UPDATE facts SET current_version=? WHERE id=?",(version,row[0]))
            if row[1]:
                approvals = db.execute("SELECT DISTINCT m.approval_id FROM approval_members m JOIN actions a ON a.id=m.action_id JOIN draft_facts f ON f.draft_id=a.draft_id WHERE f.fact_version_id=?",(row[1],)).fetchall()
                for (approval,) in approvals:
                    db.execute("UPDATE approvals SET state='REVOKED',revision=revision+1 WHERE id=? AND state='ACTIVE'",(approval,))
            self.event(db,"FACT_"+status,"fact",row[0],count+1)
            return self.receipt(row[0],count+1,status)
        return self.command(principal,body["command_id"],["fact",account_id,body],change)

    def _facts_ready(self,db,draft_id,account_id):
        refs = db.execute("SELECT v.id,v.status,f.current_version,f.account_id FROM draft_facts d JOIN fact_versions v ON v.id=d.fact_version_id JOIN facts f ON f.id=v.fact_id WHERE d.draft_id=?",(draft_id,)).fetchall()
        return bool(refs) and all(status=="VERIFIED" and version==head and owner==account_id for version,status,head,owner in refs)

    def create_draft(self,application_id,value,fact_versions,artifact_version=None):
        """Internal preparation service; inputs are references, never action authority."""
        def change(db):
            application = db.execute("SELECT account_id FROM applications WHERE id=?",(identifier(application_id),)).fetchone()
            if not application:
                raise DomainError("NOT_FOUND",404)
            draft = str(uuid4())
            content = self.content(db,"draft",value)
            if artifact_version:
                artifact = db.execute("SELECT account_id,readiness FROM artifact_versions WHERE id=?",(identifier(artifact_version),)).fetchone()
                if not artifact or artifact!=(application[0],"READY"):
                    raise DomainError("ARTIFACT_NOT_READY",422)
            db.execute("INSERT INTO drafts VALUES(?,?,?,?,?)",(draft,application_id,content,artifact_version,self.stamp()))
            for version in set(fact_versions):
                db.execute("INSERT INTO draft_facts VALUES(?,?)",(draft,identifier(version)))
            if not self._facts_ready(db,draft,application[0]):
                raise DomainError("FACTS_REQUIRED",422)
            return {"draft_id":draft,"payload_version":content}
        return self.writer.call(change)
