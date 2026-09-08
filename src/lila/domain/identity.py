import re
from urllib.parse import urlsplit
from uuid import uuid4
from lila.domain.core import DomainError,identifier


class Identity:
    def register_job(self,account_id,*,external_id=None,url=None,metadata=None):
        metadata = metadata or {}
        if url:
            parsed = urlsplit(url)
            match = re.fullmatch(r"/jobs/view/(\d+)/?",parsed.path)
            if parsed.scheme!="https" or parsed.hostname!="www.linkedin.com" or parsed.username or parsed.port not in (None,443) or not match:
                raise DomainError("UNSUPPORTED_JOB_URL",422)
            if external_id is not None and external_id!=match[1]:
                raise DomainError("IDENTITY_CONFLICT")
            external_id = match[1]
        if external_id is not None and not re.fullmatch(r"[0-9]{1,30}",external_id):
            raise DomainError("INVALID_JOB_ID",422)
        canonical_url = f"https://www.linkedin.com/jobs/view/{external_id}/" if external_id else None
        def change(db):
            self.account(db,account_id)
            existing = db.execute("SELECT id FROM jobs WHERE platform='linkedin' AND external_id=?",(external_id,)).fetchone() if external_id else None
            job = existing[0] if existing else str(uuid4())
            version = self.content(db,"job_metadata",metadata)
            if existing:
                db.execute("UPDATE jobs SET metadata_version=? WHERE id=?",(version,job))
            else:
                db.execute("INSERT INTO jobs VALUES(?,'linkedin',?,?,?,?)",(job,external_id,canonical_url,"VERIFIED" if external_id else "UNKNOWN",version))
                if canonical_url:
                    db.execute("INSERT INTO job_identity_aliases VALUES('linkedin',?,?)",(canonical_url,job))
            identity_fields = ("company","title","location")
            signature = tuple(str(metadata.get(key,"")).strip().casefold() for key in identity_fields)
            if all(signature):
                for other,other_version in db.execute("SELECT id,metadata_version FROM jobs WHERE id<>?",(job,)).fetchall():
                    other_data = self.value(db,other_version) if other_version else {}
                    if tuple(str(other_data.get(key,"")).strip().casefold() for key in identity_fields)==signature:
                        found = db.execute("SELECT 1 FROM duplicate_reviews WHERE account_id=? AND ((job_id=? AND other_job_id=?) OR (job_id=? AND other_job_id=?))",(account_id,job,other,other,job)).fetchone()
                        if not found:
                            db.execute("INSERT INTO duplicate_reviews VALUES(?,?,?,?,'PENDING',1)",(str(uuid4()),account_id,job,other))
            application = db.execute("SELECT id FROM applications WHERE account_id=? AND job_id=?",(account_id,job)).fetchone()
            application_id = application[0] if application else str(uuid4())
            if not application:
                db.execute("INSERT INTO applications VALUES(?,?,?,'NONE',1)",(application_id,account_id,job))
            return {"job_id":job,"application_id":application_id}
        return self.writer.call(change)

    def duplicate_decision(self,principal,review_id,command_id,expected_revision,disposition):
        if disposition not in {"SAME","DISTINCT"}:
            raise DomainError("INVALID_REQUEST",422)
        def change(db):
            row = db.execute("SELECT revision FROM duplicate_reviews WHERE id=?",(identifier(review_id),)).fetchone()
            if not row:
                raise DomainError("NOT_FOUND",404)
            if row[0]!=expected_revision:
                raise DomainError("REVISION_CONFLICT")
            db.execute("UPDATE duplicate_reviews SET disposition=?,revision=revision+1 WHERE id=?",(disposition,review_id))
            self.event(db,"DUPLICATE_REVIEWED","duplicate_review",review_id,row[0]+1)
            return self.receipt(review_id,row[0]+1,disposition)
        return self.command(principal,command_id,["duplicate_review",review_id,expected_revision,disposition],change)

    def _identity_ready(self,db,application):
        row = db.execute("SELECT a.account_id,a.job_id,j.identity_status,a.effective_outcome FROM applications a JOIN jobs j ON j.id=a.job_id WHERE a.id=?",(application,)).fetchone()
        if not row or row[2]=="UNKNOWN":
            raise DomainError("IDENTITY_REQUIRED",422)
        if row[3] in {"CONFIRMED","USER_REPORTED","UNCERTAIN"}:
            raise DomainError("DUPLICATE_APPLICATION")
        related = db.execute("WITH RECURSIVE same(id) AS (SELECT ? UNION SELECT CASE WHEN d.job_id=s.id THEN d.other_job_id ELSE d.job_id END FROM duplicate_reviews d JOIN same s ON d.job_id=s.id OR d.other_job_id=s.id WHERE d.account_id=? AND d.disposition='SAME') SELECT id FROM same",(row[1],row[0])).fetchall()
        for (job,) in related:
            if db.execute("SELECT 1 FROM duplicate_reviews WHERE account_id=? AND (job_id=? OR other_job_id=?) AND disposition='PENDING'",(row[0],job,job)).fetchone():
                raise DomainError('POSSIBLE_DUPLICATE',422)
            if job!=row[1] and db.execute("SELECT 1 FROM applications a LEFT JOIN submission_guards g ON g.application_id=a.id WHERE a.account_id=? AND a.job_id=? AND (g.application_id IS NOT NULL OR a.effective_outcome IN('CONFIRMED','USER_REPORTED','UNCERTAIN'))",(row[0],job)).fetchone():
                raise DomainError('DUPLICATE_APPLICATION')
        return row[0]
