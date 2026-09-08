import hashlib
import hmac
import json
import struct
import threading
import time
from datetime import datetime,timezone
from pathlib import Path
from uuid import UUID,uuid4
from jsonschema import Draft202012Validator,FormatChecker
from jsonschema.exceptions import ValidationError
from lila.contracts.canonical import canonical,normalize

SCHEMA = json.loads((Path(__file__).resolve().parents[1]/"contracts/protocol-v1.schema.json").read_text(encoding="utf-8"))
GLOBAL_ID = "00000000-0000-4000-8000-000000000001"


class DomainError(Exception):
    def __init__(self,code,status=409):
        self.code,self.status = code,status
        super().__init__(code)


def validate(name,body):
    try:
        body = normalize(body)
        schema = dict(SCHEMA, **{"$ref":f"#/$defs/{name}"})
        Draft202012Validator(schema,format_checker=FormatChecker()).validate(body)
        return body
    except (ValueError,ValidationError):
        # Validator detail can contain personal values; never expose it in API errors.
        raise DomainError("INVALID_REQUEST",422) from None


def identifier(value):
    try:
        return str(UUID(value))
    except (ValueError,TypeError,AttributeError):
        raise DomainError("INVALID_REQUEST",422) from None


class Core:
    def __init__(self,writer,audit_key,clock=None,readiness=None,capability=None):
        self.writer,self.audit_key = writer,audit_key
        self.clock = clock or (lambda:datetime.now(timezone.utc).timestamp())
        self.readiness = readiness or (lambda:["WORKER_UNAVAILABLE","BROWSER_UNAVAILABLE"])
        self.capability = capability or (lambda account,domain,tab:False)
        self.dispatch_lock = threading.RLock()
        self.monotonic = time.monotonic
        self.lease_deadlines = {}
        self.last_wall_time = self.clock()
        self.time_unreliable = False

    def check_time(self):
        current = self.clock()
        if current < self.last_wall_time-60:
            self.time_unreliable = True
        self.last_wall_time = max(current,self.last_wall_time)
        if self.time_unreliable:
            raise DomainError('TIME_UNRELIABLE',503)

    def stamp(self):
        return datetime.fromtimestamp(self.clock(),timezone.utc).isoformat()

    def content(self,db,kind,value):
        data = canonical(value)
        entity = str(uuid4())
        db.execute("INSERT INTO content_versions VALUES(?,?,?,?,?)",(entity,kind,data.decode(),hashlib.sha256(data).hexdigest(),self.stamp()))
        return entity

    def value(self,db,version):
        row = db.execute("SELECT canonical_json FROM content_versions WHERE id=?",(version,)).fetchone()
        if not row:
            raise DomainError("NOT_FOUND",404)
        return json.loads(row[0])

    def account(self,db,account_id):
        account_id = identifier(account_id)
        if not db.execute("SELECT 1 FROM accounts WHERE id=?",(account_id,)).fetchone():
            raise DomainError("NOT_FOUND",404)
        return account_id

    def register_account(self,subject):
        """Trusted account adapter/bootstrap only; not a client-supplied identity assertion."""
        if not isinstance(subject,str) or not 1 <= len(subject) <= 300:
            raise DomainError("INVALID_REQUEST",422)
        def transaction(db):
            row = db.execute("SELECT id FROM accounts WHERE platform='linkedin' AND external_subject=?",(subject,)).fetchone()
            if row:
                return row[0]
            entity = str(uuid4())
            db.execute("INSERT INTO accounts VALUES(?,'linkedin',?,1)",(entity,subject))
            return entity
        return self.writer.call(transaction)

    def event(self,db,kind,entity_type,entity,revision,summary=None):
        timestamp = self.stamp()
        event_id = str(uuid4())
        summary = summary or {}
        db.execute("INSERT INTO events(event_id,entity_type,entity_id,revision,kind,summary_json,occurred_at) VALUES(?,?,?,?,?,?,?)",(event_id,entity_type,entity,revision,kind,canonical(summary).decode(),timestamp))
        prior = db.execute("SELECT sequence,tag,segment_id,occurred_at FROM audit_events ORDER BY sequence DESC LIMIT 1").fetchone()
        sequence = prior[0]+1 if prior else 1
        previous = prior[1] if prior else bytes(32)
        segment = prior[2] if prior else None
        segment_first = db.execute("SELECT first_sequence FROM audit_segments WHERE id=?",(segment,)).fetchone() if segment else None
        if not prior or sequence-segment_first[0]>=1000 or timestamp[:10]!=prior[3][:10]:
            if prior:
                db.execute("UPDATE audit_segments SET last_sequence=?,sealed_tag=? WHERE id=?",(prior[0],previous,segment))
            segment = str(uuid4())
            db.execute("INSERT INTO audit_segments VALUES(?,'1',?,NULL,?,NULL,NULL)",(segment,sequence,previous))
        minimal = {"event_id":event_id,"kind":kind,"entity_id":entity,"revision":revision,"occurred_at":timestamp}
        encoded = canonical(minimal)
        tag = hmac.digest(self.audit_key,b"lila-audit-v1\x00"+b"1\x00"+struct.pack(">Q",sequence)+previous+encoded,"sha256")
        db.execute("INSERT INTO audit_events VALUES(?,?,?,?,?,?,?,?,?)",(sequence,event_id,segment,kind,entity,encoded.decode(),previous,tag,timestamp))
        db.execute('UPDATE audit_head SET sequence=?,tag=? WHERE id=1',(sequence,tag))

    def verify_audit(self):
        """Verify retained local chain and segment boundaries, without claiming rollback immunity."""
        def read(db):
            previous,sequence = bytes(32),0
            segments = {}
            for row in db.execute('SELECT sequence,event_id,segment_id,kind,entity_id,minimal_json,previous_tag,tag,occurred_at FROM audit_events ORDER BY sequence'):
                seq,event_id,segment,kind,entity,encoded,prior_tag,tag,stamp = row
                value = json.loads(encoded)
                event = db.execute('SELECT entity_id,revision,kind,occurred_at FROM events WHERE event_id=?',(event_id,)).fetchone()
                expected = {'event_id':event_id,'kind':kind,'entity_id':entity,'revision':value.get('revision'),'occurred_at':stamp}
                if seq!=sequence+1 or prior_tag!=previous or value!=expected or canonical(value).decode()!=encoded or event!=(entity,value['revision'],kind,stamp):
                    raise DomainError('AUDIT_INTEGRITY_FAILURE',503)
                calculated = hmac.digest(self.audit_key,b'lila-audit-v1\x00'+b'1\x00'+struct.pack('>Q',seq)+previous+encoded.encode(),'sha256')
                if not hmac.compare_digest(calculated,tag):
                    raise DomainError('AUDIT_INTEGRITY_FAILURE',503)
                if segment not in segments:
                    segments[segment] = [seq,seq,previous,tag]
                elif segments[segment][1]!=seq-1:
                    raise DomainError('AUDIT_INTEGRITY_FAILURE',503)
                else:
                    segments[segment][1],segments[segment][3] = seq,tag
                previous,sequence = tag,seq
            rows = db.execute('SELECT id,key_generation,first_sequence,last_sequence,prior_tag,sealed_tag,retired_at FROM audit_segments ORDER BY first_sequence').fetchall()
            if len(rows)!=len(segments) or db.execute('SELECT sequence,tag FROM audit_head WHERE id=1').fetchone()!=(sequence,previous):
                raise DomainError('AUDIT_INTEGRITY_FAILURE',503)
            for index,(sid,key,first,last,prior,sealed,retired) in enumerate(rows):
                actual = segments.get(sid)
                active = index==len(rows)-1
                if not actual or key!='1' or retired is not None or first!=actual[0] or prior!=actual[2] or (active and (last is not None or sealed is not None)) or (not active and (last!=actual[1] or sealed!=actual[3])):
                    raise DomainError('AUDIT_INTEGRITY_FAILURE',503)
            return {'events_verified':sequence,'segments_verified':len(rows)}
        try:
            return self.writer.call(read,transaction=False)
        except (ValueError,KeyError,TypeError):
            raise DomainError('AUDIT_INTEGRITY_FAILURE',503) from None

    def command(self,principal,command_id,request,mutate):
        principal,command_id = identifier(principal),identifier(command_id)
        digest = hashlib.sha256(canonical(request)).hexdigest()
        def transaction(db):
            existing = db.execute("SELECT request_digest,result_json FROM command_receipts WHERE principal_id=? AND command_id=?",(principal,command_id)).fetchone()
            if existing:
                if existing[0]!=digest:
                    raise DomainError("COMMAND_ID_REUSED")
                return json.loads(existing[1])
            result = mutate(db)
            result = dict(result,command_id=command_id,accepted=True)
            db.execute("INSERT INTO command_receipts VALUES(?,?,?,200,?,?)",(principal,command_id,digest,canonical(result).decode(),self.stamp()))
            return result
        with self.dispatch_lock:
            return self.writer.call(transaction)

    def receipt(self,entity,revision,state,reasons=None):
        return {"entity_id":entity,"revision":revision,"state":state,"blocking_reasons":reasons or []}

    def get_receipt(self,principal,command_id):
        def read(db):
            row = db.execute("SELECT result_json FROM command_receipts WHERE principal_id=? AND command_id=?",(identifier(principal),identifier(command_id))).fetchone()
            if not row:
                raise DomainError("NOT_FOUND",404)
            return json.loads(row[0])
        return self.writer.call(read,transaction=False)
