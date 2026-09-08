import hashlib
import threading
from uuid import uuid4
from .core import DomainError,identifier
from .artifacts import MAX_SIZE,MEDIA


class Documents:
    def __init__(self,domain,artifacts):
        self.domain,self.artifacts = domain,artifacts
        self.lock = threading.Lock()

    def accept(self,principal,command_id,account_id,filename,data,media_type):
        if not isinstance(filename,str) or not 1<=len(filename)<=255 or any(c in filename for c in '/\\\x00') or filename in {'.','..'}:
            raise DomainError('INVALID_FILENAME',422)
        if not isinstance(data,bytes) or not 0<len(data)<=MAX_SIZE or media_type not in MEDIA:
            raise DomainError('INVALID_ARTIFACT',422)
        digest = hashlib.sha256(data).hexdigest()
        def change(db):
            self.domain.account(db,account_id)
            upload,operation = str(uuid4()),str(uuid4())
            metadata = self.domain.content(db,'upload_metadata',{'account_id':account_id,'filename':filename,'digest':digest,'media_type':media_type})
            db.execute("INSERT INTO operations VALUES(?,'DOCUMENT_UPLOAD','STAGING',?,1,NULL,?)",(operation,metadata,self.domain.stamp()))
            db.execute("INSERT INTO document_uploads VALUES(?,?,?,?,?,'STAGING',NULL,NULL,1)",(upload,operation,account_id,filename,digest))
            self.domain.event(db,'DOCUMENT_UPLOAD_ACCEPTED','document',upload,1)
            return dict(self.domain.receipt(upload,1,'STAGING'),upload_id=upload,operation_id=operation,status='STAGING')
        return self.domain.command(principal,command_id,['upload',account_id,filename,media_type,digest],change)

    def publish(self,upload_id,data,media_type):
        # File publication uses a separate lock so a long upload cannot hold the control lock.
        with self.lock:
            row = self.domain.writer.call(lambda db:db.execute('SELECT account_id,digest,state FROM document_uploads WHERE id=?',(identifier(upload_id),)).fetchone(),transaction=False)
            if not row:
                raise DomainError('NOT_FOUND',404)
            if row[2] in {'READY','FAILED'}:
                return
            if hashlib.sha256(data).hexdigest()!=row[1]:
                raise DomainError('COMMAND_ID_REUSED')
            try:
                version = self.artifacts.publish(row[0],data,media_type,document_id=upload_id)
            except (DomainError,OSError) as exc:
                self._failed(upload_id,exc.code if isinstance(exc,DomainError) else 'ARTIFACT_WRITE_FAILED')
                return
            self._ready(upload_id,version)

    def _failed(self,upload_id,code):
        def change(db):
            row = db.execute('SELECT operation_id,revision FROM document_uploads WHERE id=?',(upload_id,)).fetchone()
            db.execute("UPDATE document_uploads SET state='FAILED',error_code=?,revision=revision+1 WHERE id=?",(code,upload_id))
            db.execute("UPDATE operations SET phase='FAILED',error_code=? WHERE id=?",(code,row[0]))
            self.domain.event(db,'DOCUMENT_UPLOAD_FAILED','document',upload_id,row[1]+1,{'code':code})
        self.domain.writer.call(change)

    def _ready(self,upload_id,version):
        def change(db):
            row = db.execute('SELECT operation_id,revision,account_id FROM document_uploads WHERE id=?',(upload_id,)).fetchone()
            db.execute("UPDATE document_uploads SET state='READY',version_id=?,error_code=NULL,revision=revision+1 WHERE id=?",(version,upload_id))
            db.execute("UPDATE operations SET phase='COMPLETE',error_code=NULL WHERE id=?",(row[0],))
            source = self.domain.content(db,'document_extraction_input',{'account_id':row[2],'artifact_version':version,'max_output_characters':100000,'facts_status':'PROPOSED'})
            db.execute("INSERT INTO operations VALUES(?,'DOCUMENT_EXTRACT','QUEUED',?,1,NULL,?)",(str(uuid4()),source,self.domain.stamp()))
            self.domain.event(db,'DOCUMENT_UPLOAD_READY','document',upload_id,row[1]+1)
        self.domain.writer.call(change)

    def status(self,upload_id):
        def read(db):
            row = db.execute('SELECT operation_id,state,version_id,error_code,revision FROM document_uploads WHERE id=?',(identifier(upload_id),)).fetchone()
            if not row:
                raise DomainError('NOT_FOUND',404)
            return dict(zip(['operation_id','status','version_id','error_code','revision'],row),upload_id=upload_id)
        return self.domain.writer.call(read,transaction=False)

    def recover(self):
        rows = self.domain.writer.call(lambda db:db.execute("SELECT id,state FROM document_uploads WHERE state IN('STAGING','READY')").fetchall(),transaction=False)
        for upload,state in rows:
            version = self.domain.writer.call(lambda db:db.execute("SELECT id FROM artifact_versions WHERE document_id=? AND readiness='READY' ORDER BY rowid DESC LIMIT 1",(upload,)).fetchone(),transaction=False)
            if not version:
                self._failed(upload,'UPLOAD_INTERRUPTED' if state=='STAGING' else 'ARTIFACT_CORRUPT')
            elif state=='STAGING':
                self._ready(upload,version[0])

    def select(self,principal,document_id,command_id,expected_revision,source_version,format):
        if type(expected_revision) is not int or expected_revision<1 or format not in {'pdf','docx'}:
            raise DomainError('INVALID_REQUEST',422)
        def change(db):
            row = db.execute('SELECT account_id,revision,state FROM document_uploads WHERE id=?',(identifier(document_id),)).fetchone()
            if not row:
                raise DomainError('NOT_FOUND',404)
            if row[1]!=expected_revision:
                raise DomainError('REVISION_CONFLICT')
            artifact = db.execute('SELECT document_id,media_type FROM artifact_versions WHERE id=? AND account_id=?',(identifier(source_version),row[0])).fetchone()
            media = 'application/pdf' if format=='pdf' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            if not artifact or artifact!=(document_id,media) or row[2]!='READY':
                raise DomainError('ARTIFACT_NOT_READY',422)
            self.artifacts.read_in_transaction(db,source_version,row[0])
            db.execute('INSERT INTO selected_documents VALUES(?,?) ON CONFLICT(account_id) DO UPDATE SET version_id=excluded.version_id',(row[0],source_version))
            db.execute("UPDATE approvals SET state='REVOKED',revision=revision+1 WHERE state='ACTIVE' AND id IN(SELECT m.approval_id FROM approval_members m JOIN actions a ON a.id=m.action_id JOIN drafts d ON d.id=a.draft_id JOIN applications p ON p.id=d.application_id WHERE p.account_id=? AND d.artifact_version IS NOT NULL AND d.artifact_version<>?)",(row[0],source_version))
            db.execute('UPDATE document_uploads SET revision=revision+1 WHERE id=?',(document_id,))
            self.domain.event(db,'DOCUMENT_SELECTED','document',document_id,row[1]+1)
            return self.domain.receipt(document_id,row[1]+1,'SELECTED')
        return self.domain.command(principal,command_id,['select_document',document_id,expected_revision,source_version,format],change)
