"""Atomic bootstrap, renewable UI sessions, CSRF and epoch revocation."""
import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone
from uuid import uuid4


class AuthError(Exception):
    pass


def token():
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")


def now():
    return datetime.now(timezone.utc).timestamp()


def timestamp(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


def seconds(value):
    return datetime.fromisoformat(value).timestamp()


class Sessions:
    def __init__(self, writer, key, clock=now):
        if len(key) != 32:
            raise ValueError("invalid hash key")
        self.writer, self.key, self.clock = writer, key, clock
        self.revocation_listeners = []

    def digest(self, value):
        import re
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", value):
            raise AuthError("AUTH_REQUIRED")
        return hmac.digest(self.key, value.encode("ascii"), "sha256")

    def issue_bootstrap(self):
        secret = token()
        self.writer.call(lambda db: db.execute("INSERT INTO bootstrap VALUES(?,?,NULL)",
            (self.digest(secret), timestamp(self.clock() + 60))).rowcount)
        return secret

    def _new(self, db, principal):
        secret, session_id = token(), str(uuid4())
        csrf = self._csrf(session_id)
        epoch = db.execute("SELECT epoch FROM auth_epoch WHERE id=1").fetchone()[0]
        expires = timestamp(self.clock() + 86400)
        db.execute("INSERT INTO sessions VALUES(?,?,?,?,?,?,NULL,NULL)",
            (session_id, principal, epoch, self.digest(secret), self.digest(csrf), expires))
        return {"session_id": session_id, "principal_id": principal, "secret": secret,
            "csrf_token": csrf, "expires_at": expires, "credential_epoch": epoch}

    def _csrf(self, session_id):
        return base64.urlsafe_b64encode(hmac.digest(self.key, b"csrf-v1:" + session_id.encode(), "sha256")).decode().rstrip("=")

    def consume_bootstrap(self, secret):
        def transaction(db):
            row = db.execute("SELECT expires_at,consumed_at FROM bootstrap WHERE token_hash=?", (self.digest(secret),)).fetchone()
            if not row or row[1] or seconds(row[0]) <= self.clock():
                raise AuthError("AUTH_REQUIRED")
            db.execute("UPDATE bootstrap SET consumed_at=? WHERE token_hash=?", (timestamp(self.clock()), self.digest(secret)))
            principal = str(uuid4())
            db.execute("INSERT INTO principals(id,kind,scope_json) VALUES(?,'UI',?)", (principal, json.dumps(["admin"])))
            return self._new(db, principal)
        return self.writer.call(transaction)

    def _lookup(self, db, secret, csrf=None, renewing=False):
        row = db.execute("SELECT s.id,s.principal_id,s.expires_at,s.renewed_to,s.overlap_until,s.csrf_hash,s.epoch,p.revoked_at,e.epoch FROM sessions s JOIN principals p ON p.id=s.principal_id JOIN auth_epoch e ON e.id=1 WHERE s.token_hash=? AND p.kind='UI'", (self.digest(secret),)).fetchone()
        if not row or row[7] or row[6] != row[8] or seconds(row[2]) <= self.clock():
            raise AuthError("SESSION_EXPIRED")
        if row[3] and (renewing or not row[4] or seconds(row[4]) <= self.clock()):
            raise AuthError("SESSION_EXPIRED")
        if csrf is not None:
            try:
                valid = hmac.compare_digest(row[5], self.digest(csrf))
            except AuthError:
                valid = False
            if not valid:
                raise AuthError("CSRF_DENIED")
        return row

    def authenticate(self, secret, csrf=None):
        def read(db):
            row = self._lookup(db, secret, csrf)
            return {"session_id": row[0], "principal_id": row[1], "expires_at": row[2], "credential_epoch": row[6]}
        return self.writer.call(read, transaction=False)

    def session(self, secret):
        # Stable per session: opening a second tab must not invalidate the first.
        def change(db):
            row = self._lookup(db, secret)
            csrf = self._csrf(row[0])
            return {"principal_id": row[1], "expires_at": row[2], "credential_epoch": row[6], "csrf_token": csrf}
        return self.writer.call(change)

    def renew(self, secret, csrf):
        def change(db):
            row = self._lookup(db, secret, csrf, renewing=True)
            new = self._new(db, row[1])
            db.execute("UPDATE sessions SET renewed_to=?,overlap_until=? WHERE id=?", (new["session_id"], timestamp(self.clock()+30), row[0]))
            return new
        return self.writer.call(change)

    def revoke(self, principal, expected_revision):
        def change(db):
            updated = db.execute("UPDATE principals SET revoked_at=?,revision=revision+1 WHERE id=? AND revision=? AND revoked_at IS NULL", (timestamp(self.clock()), principal, expected_revision)).rowcount
            if updated != 1:
                raise AuthError("REVISION_CONFLICT")
        self.writer.call(change)
        for listener in self.revocation_listeners:
            listener(principal)

    def reset_epoch(self):
        def reset(db):
            db.execute("UPDATE auth_epoch SET epoch=epoch+1 WHERE id=1")
            db.execute("UPDATE bootstrap SET consumed_at=? WHERE consumed_at IS NULL",(timestamp(self.clock()),))
            db.execute("UPDATE pairing SET state='REVOKED',protected_secret=x'' WHERE state NOT IN ('CONSUMED','REVOKED')")
        self.writer.call(reset)
        for listener in self.revocation_listeners:
            listener(None)

    def revoke_command(self, secret, csrf, command_id, principal, expected_revision):
        payload_digest = hashlib.sha256(json.dumps([principal,expected_revision],separators=(",",":")).encode()).hexdigest()
        def change(db):
            actor = self._lookup(db,secret,csrf)[1]
            existing = db.execute("SELECT request_digest,result_json FROM auth_command_receipts WHERE principal_id=? AND command_id=?",(actor,command_id)).fetchone()
            if existing:
                if existing[0] != payload_digest:
                    raise AuthError("COMMAND_ID_REUSED")
                return json.loads(existing[1])
            if db.execute("UPDATE principals SET revoked_at=?,revision=revision+1 WHERE id=? AND revision=? AND revoked_at IS NULL",(timestamp(self.clock()),principal,expected_revision)).rowcount != 1:
                raise AuthError("REVISION_CONFLICT")
            result = {"command_id":command_id,"accepted":True,"entity_id":principal,"revision":expected_revision+1,"state":"REVOKED","blocking_reasons":[]}
            db.execute("INSERT INTO auth_command_receipts VALUES(?,?,?,?,?)",(actor,command_id,payload_digest,json.dumps(result),timestamp(self.clock())))
            return result
        result = self.writer.call(change)
        for listener in self.revocation_listeners:
            listener(principal)
        return result
