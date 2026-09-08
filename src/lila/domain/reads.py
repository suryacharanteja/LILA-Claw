import base64
import hashlib
import hmac
import json
from lila.contracts.canonical import canonical
from .core import DomainError,identifier


class Reads:
    def cursor(self,scope,position):
        data = canonical({'scope':scope,'position':position,'expires_at':int(self.clock())+86400})
        return base64.urlsafe_b64encode(data+hmac.digest(self.audit_key,b'lila-cursor-v1\0'+data,'sha256')).decode().rstrip('=')

    def cursor_position(self,token,scope):
        if not token:
            return 0
        try:
            if len(token)>4096:
                raise ValueError()
            raw = base64.b64decode(token+'='*(-len(token)%4),altchars=b'-_',validate=True)
            data,tag = raw[:-32],raw[-32:]
            if not hmac.compare_digest(tag,hmac.digest(self.audit_key,b'lila-cursor-v1\0'+data,'sha256')):
                raise ValueError()
            value = json.loads(data)
            if value['scope']!=scope or value['expires_at']<=self.clock() or type(value['position']) is not int or value['position']<0:
                raise ValueError()
            return value['position']
        except (ValueError,KeyError,TypeError):
            raise DomainError('CURSOR_EXPIRED',410) from None

    def events_page(self,principal,after=None,limit=100):
        if type(limit) is not int or not 1<=limit<=200:
            raise DomainError('INVALID_REQUEST',422)
        scope = ['events',identifier(principal)]
        position = self.cursor_position(after,scope)
        def read(db):
            rows = db.execute('SELECT cursor,event_id,entity_type,entity_id,revision,kind,summary_json,occurred_at FROM events WHERE cursor>? ORDER BY cursor LIMIT ?',(position,limit)).fetchall()
            events = [{'cursor':self.cursor(scope,r[0]),'event_id':r[1],'entity_type':r[2],'entity_id':r[3],'revision':r[4],'kind':r[5],'summary':json.loads(r[6]),'occurred_at':r[7]} for r in rows]
            return {'events':events,'next_cursor':events[-1]['cursor'] if events else after}
        return self.writer.call(read,transaction=False)

    def list_entities(self,principal,kind,account_id,after=None,limit=100):
        if type(limit) is not int or not 1<=limit<=200:
            raise DomainError('INVALID_REQUEST',422)
        # Fixed queries expose no secret columns, dynamic SQL or user filter expressions.
        queries = {
            'tasks':('SELECT rowid,id,revision,created_at FROM tasks WHERE account_id=? AND rowid>? ORDER BY rowid LIMIT ?',('rowid','id','revision','created_at')),
            'facts':('SELECT f.rowid,f.id,f.field_key,f.current_version,v.status,c.canonical_json FROM facts f JOIN fact_versions v ON v.id=f.current_version JOIN content_versions c ON c.id=v.value_version WHERE f.account_id=? AND f.rowid>? ORDER BY f.rowid LIMIT ?',('rowid','id','field_key','version_id','status','value_json')),
            'applications':('SELECT rowid,id,job_id,effective_outcome,revision FROM applications WHERE account_id=? AND rowid>? ORDER BY rowid LIMIT ?',('rowid','id','job_id','effective_outcome','revision')),
            'jobs':('SELECT j.rowid,j.id,j.external_id,j.canonical_url,j.identity_status,j.metadata_version FROM jobs j JOIN applications a ON a.job_id=j.id WHERE a.account_id=? AND j.rowid>? ORDER BY j.rowid LIMIT ?',('rowid','id','external_id','canonical_url','identity_status','metadata_version')),
            'documents':('SELECT rowid,id,document_id,media_type,byte_length,readiness FROM artifact_versions WHERE account_id=? AND rowid>? ORDER BY rowid LIMIT ?',('rowid','id','document_id','media_type','byte_length','readiness')),
            'policies':('SELECT rowid,id,revision,scope_version,expires_at,revoked_at FROM policies WHERE account_id=? AND rowid>? ORDER BY rowid LIMIT ?',('rowid','id','revision','scope_version','expires_at','revoked_at')),
            'history':('SELECT o.rowid,o.id,o.action_id,o.outcome,o.provenance,o.occurred_at,o.supersedes_id FROM outcomes o JOIN actions a ON a.id=o.action_id JOIN applications p ON p.id=a.application_id WHERE p.account_id=? AND o.rowid>? ORDER BY o.rowid LIMIT ?',('rowid','id','action_id','outcome','provenance','occurred_at','supersedes_id')),
        }
        if kind not in queries:
            raise DomainError('NOT_FOUND',404)
        scope = [kind,identifier(principal),identifier(account_id)]
        position = self.cursor_position(after,scope)
        def read(db):
            self.account(db,account_id)
            sql,columns = queries[kind]
            rows = db.execute(sql,(account_id,position,limit+1)).fetchall()
            more = len(rows)>limit
            rows = rows[:limit]
            items = []
            for row in rows:
                item = dict(zip(columns[1:],row[1:]))
                if 'value_json' in item:
                    item['value'] = json.loads(item.pop('value_json'))
                items.append(item)
            revision = db.execute('SELECT coalesce(max(cursor),0) FROM events').fetchone()[0]
            return {'items':items,'next_cursor':self.cursor(scope,rows[-1][0]) if more else None,'as_of_revision':revision,'coverage':'retained_records'}
        return self.writer.call(read,transaction=False)
