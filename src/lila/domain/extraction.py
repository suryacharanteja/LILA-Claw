"""Coordinator assignment and atomic publication of unverified document proposals."""
import hashlib
from uuid import uuid4
from lila.contracts.canonical import canonical
from lila.domain.core import DomainError,identifier
from lila.worker.documents import MAX_CHARACTERS,LABELS


class Extraction:
    def __init__(self,domain):
        self.domain=domain

    def next(self,worker,generation):
        worker=identifier(worker)
        def change(db):
            row=db.execute("SELECT o.id,o.subject_version,c.worker_id,c.generation FROM operations o LEFT JOIN extraction_claims c ON c.operation_id=o.id WHERE o.kind='DOCUMENT_EXTRACT' AND o.phase IN('QUEUED','RUNNING') ORDER BY o.created_at,o.id LIMIT 1").fetchone()
            if not row:
                return {'available':False}
            # A newer authenticated registry identity fences/reclaims interrupted work.
            db.execute("INSERT INTO extraction_claims(operation_id,worker_id,generation) VALUES(?,?,?) ON CONFLICT(operation_id) DO UPDATE SET worker_id=excluded.worker_id,generation=excluded.generation",(row[0],worker,generation))
            db.execute("UPDATE operations SET phase='RUNNING' WHERE id=?",(row[0],))
            source=self.domain.value(db,row[1])
            media=db.execute('SELECT media_type FROM artifact_versions WHERE id=? AND account_id=?',(source['artifact_version'],source['account_id'])).fetchone()
            if not media:
                raise DomainError('ARTIFACT_NOT_READY',422)
            return {'available':True,'operation_id':row[0],'media_type':media[0]}
        return self.domain.writer.call(change)

    def _scope(self,db,worker,generation,operation):
        row=db.execute("SELECT o.subject_version,o.phase,c.worker_id,c.generation,c.result_digest,c.result_version FROM operations o JOIN extraction_claims c ON c.operation_id=o.id WHERE o.id=? AND o.kind='DOCUMENT_EXTRACT'",(identifier(operation),)).fetchone()
        if not row or row[2:4]!=(identifier(worker),generation):
            raise DomainError('STALE_WORKER',403)
        return row

    def data(self,worker,generation,operation):
        def read(db):
            row=self._scope(db,worker,generation,operation)
            if row[1]!='RUNNING':
                raise DomainError('OPERATION_COMPLETE')
            return self.domain.value(db,row[0])
        source=self.domain.writer.call(read,transaction=False)
        return self.domain.artifacts.read(source['artifact_version'],source['account_id'])

    def result(self,worker,generation,operation,value):
        if not isinstance(value,dict) or set(value)!={'text','proposals','status'} or not isinstance(value['text'],str) or len(value['text'])>MAX_CHARACTERS or value['status'] not in {'EXTRACTED','TRUNCATED','MANUAL_ENTRY_REQUIRED','FAILED'} or not isinstance(value['proposals'],list) or len(value['proposals'])>100:
            raise DomainError('INVALID_REQUEST',422)
        for proposal in value['proposals']:
            if not isinstance(proposal,dict) or set(proposal)!={'field_key','value'} or proposal['field_key'] not in LABELS.values() or not isinstance(proposal['value'],str) or not 1<=len(proposal['value'])<=1000 or proposal['value'] not in value['text']:
                raise DomainError('INVALID_REQUEST',422)
        if value['status'] in {'MANUAL_ENTRY_REQUIRED','FAILED'} and (value['text'] or value['proposals']):
            raise DomainError('INVALID_REQUEST',422)
        digest=hashlib.sha256(canonical(value)).hexdigest()
        def change(db):
            row=self._scope(db,worker,generation,operation)
            if row[4]:
                if row[4]!=digest:
                    raise DomainError('EXTRACTION_RESULT_CONFLICT')
                return {'source_version':row[5],'facts_status':'PROPOSED'}
            source=self.domain.value(db,row[0])
            result_version=self.domain.content(db,'document_extracted',dict(value,account_id=source['account_id'],artifact_version=source['artifact_version'],facts_status='PROPOSED'))
            for proposal in value['proposals']:
                fact=db.execute('SELECT id,current_version FROM facts WHERE account_id=? AND field_key=?',(source['account_id'],proposal['field_key'])).fetchone()
                if not fact:
                    fact=(str(uuid4()),None)
                    db.execute('INSERT INTO facts VALUES(?,?,?,NULL)',(fact[0],source['account_id'],proposal['field_key']))
                version=str(uuid4())
                content=self.domain.content(db,'fact_value',proposal['value'])
                db.execute("INSERT INTO fact_versions VALUES(?,?,?,?,'PROPOSED',?,?)",(version,fact[0],content,result_version,fact[1],self.domain.stamp()))
                # Preserve all existing heads, including verified owner corrections.
                if fact[1] is None:
                    db.execute('UPDATE facts SET current_version=? WHERE id=?',(version,fact[0]))
                revision=db.execute('SELECT count(*) FROM fact_versions WHERE fact_id=?',(fact[0],)).fetchone()[0]
                self.domain.event(db,'FACT_PROPOSED','fact',fact[0],revision)
            db.execute('UPDATE extraction_claims SET result_digest=?,result_version=? WHERE operation_id=?',(digest,result_version,operation))
            db.execute("UPDATE operations SET phase=?,error_code=? WHERE id=?",('FAILED' if value['status']=='FAILED' else 'COMPLETE',value['status'] if value['status']!='EXTRACTED' else None,operation))
            self.domain.event(db,'DOCUMENT_EXTRACTED','operation',operation,2,{'status':value['status']})
            return {'source_version':result_version,'facts_status':'PROPOSED'}
        return self.domain.writer.call(change)
