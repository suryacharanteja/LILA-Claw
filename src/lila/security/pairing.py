"""Extension proof/owner confirmation and short-lived challenge sessions."""
import base64
import hashlib
import hmac
import json
import secrets
import struct
from threading import RLock
from uuid import uuid4

from lila.security.sessions import AuthError, now, token, timestamp, seconds
from lila.security.windows import protect, unprotect


def transcript(*parts):
    return b"".join(struct.pack(">I", len(part)) + part for part in parts)


class Pairing:
    def __init__(self, writer, identity, hash_key, clock=now):
        self.writer, self.identity, self.hash_key, self.clock = writer, identity, hash_key, clock
        self.lock = RLock()
        self.challenges = {}
        self.failures = []

    def _hash(self, secret):
        return hmac.digest(self.hash_key, secret, "sha256")

    def create(self):
        pair_id, secret = str(uuid4()), secrets.token_bytes(32)
        self.writer.call(lambda db: db.execute("INSERT INTO pairing VALUES(?,?,NULL,NULL,0,?,'CREATED')", (pair_id, protect(secret), timestamp(self.clock()+300))).rowcount)
        return pair_id, secret

    def challenge_pair(self, pair_id):
        nonce = secrets.token_bytes(32)
        def change(db):
            changed = db.execute("UPDATE pairing SET server_nonce=? WHERE id=? AND state='CREATED' AND expires_at>? AND attempts<5", (nonce, pair_id, timestamp(self.clock()))).rowcount
            if changed != 1:
                raise AuthError("PAIRING_REPLAY")
            return nonce
        return self.writer.call(change)

    def prove(self, pair_id, client_nonce, proof):
        if len(client_nonce) != 32 or len(proof) != 32:
            raise AuthError("AUTH_REQUIRED")
        def change(db):
            row = db.execute("SELECT protected_secret,server_nonce,expires_at,state,attempts FROM pairing WHERE id=?", (pair_id,)).fetchone()
            if not row or row[3] != "CREATED" or row[4] >= 5 or seconds(row[2]) <= self.clock() or not row[1]:
                return None
            value = transcript(b"lila-pair-v1", pair_id.encode(), row[1], client_nonce)
            if not hmac.compare_digest(hmac.digest(unprotect(row[0]), value, "sha256"), proof):
                db.execute("UPDATE pairing SET attempts=attempts+1,server_nonce=NULL WHERE id=?", (pair_id,))
                return None
            db.execute("UPDATE pairing SET state='PROVED',client_nonce=? WHERE id=?", (client_nonce, pair_id))
            return self.identity.sign(hashlib.sha256(value + proof).digest())
        result = self.writer.call(change)
        if result is None:
            raise AuthError("AUTH_REQUIRED")
        return result

    def confirm(self, pair_id):
        def change(db):
            if db.execute("UPDATE pairing SET state='OWNER_CONFIRMED' WHERE id=? AND state='PROVED' AND expires_at>?", (pair_id, timestamp(self.clock()))).rowcount != 1:
                raise AuthError("PAIRING_REPLAY")
        self.writer.call(change)

    def consume(self, pair_id, client_nonce, proof):
        def change(db):
            row = db.execute("SELECT protected_secret,server_nonce,client_nonce,state,expires_at FROM pairing WHERE id=?", (pair_id,)).fetchone()
            if not row or row[3] != "OWNER_CONFIRMED" or seconds(row[4]) <= self.clock():
                raise AuthError("PAIRING_REPLAY")
            value = transcript(b"lila-pair-v1", pair_id.encode(), row[1], client_nonce)
            if client_nonce != row[2] or not hmac.compare_digest(hmac.digest(unprotect(row[0]), value, "sha256"), proof):
                raise AuthError("AUTH_REQUIRED")
            principal, credential, secret = str(uuid4()), str(uuid4()), secrets.token_bytes(32)
            epoch = db.execute("SELECT epoch FROM auth_epoch WHERE id=1").fetchone()[0]
            db.execute("INSERT INTO principals(id,kind,scope_json) VALUES(?,'EXTENSION',?)", (principal, json.dumps(["browser", "status", "controls"])))
            # Long-lived credential expiration is capped by revocation/epoch; sessions remain 15 minutes.
            db.execute("INSERT INTO credentials VALUES(?,?,?,?,?,?,NULL)", (credential, principal, epoch, self._hash(secret), protect(secret), "9999-12-31T00:00:00+00:00"))
            db.execute("UPDATE pairing SET state='CONSUMED',protected_secret=x'' WHERE id=?", (pair_id,))
            return {"principal_id": principal, "credential_id": credential, "secret": secret}
        return self.writer.call(change)

    def challenge(self, credential_id):
        with self.lock:
            self.challenges = {k:v for k,v in self.challenges.items() if v[1] > self.clock()}
            self.failures = [t for t in self.failures if self.clock()-t < 60]
            if len(self.failures) >= 5 or len(self.challenges) >= 100:
                raise AuthError("RATE_LIMITED")
            challenge_id, nonce = str(uuid4()), secrets.token_bytes(32)
            self.challenges[challenge_id] = (credential_id, self.clock()+60, nonce)
            return challenge_id, nonce

    def authenticate(self, challenge_id, client_nonce, proof):
        with self.lock:
            row = self.challenges.pop(challenge_id, None)
            if not row or row[1] <= self.clock() or len(client_nonce) != 32 or len(proof) != 32:
                self.failures.append(self.clock())
                raise AuthError("AUTH_REQUIRED")
            credential_id, _, nonce = row
            value = transcript(b"lila-extension-v1", credential_id.encode(), challenge_id.encode(), nonce, client_nonce)
            def change(db):
                credential = db.execute("SELECT c.principal_id,c.protected_proof_secret,c.epoch,c.revoked_at,p.revoked_at,e.epoch,c.expires_at FROM credentials c JOIN principals p ON p.id=c.principal_id JOIN auth_epoch e ON e.id=1 WHERE c.id=? AND p.kind='EXTENSION'", (credential_id,)).fetchone()
                if not credential or credential[3] or credential[4] or credential[2] != credential[5] or seconds(credential[6]) <= self.clock():
                    raise AuthError("AUTH_REQUIRED")
                if not hmac.compare_digest(hmac.digest(unprotect(credential[1]), value, "sha256"), proof):
                    raise AuthError("AUTH_REQUIRED")
                session_id, session_secret = str(uuid4()), token()
                expires = timestamp(self.clock()+900)
                db.execute("INSERT INTO sessions VALUES(?,?,?,?,NULL,?,NULL,NULL)", (session_id, credential[0], credential[2], self._hash(session_secret.encode()), expires))
                return {"session_secret": session_secret, "principal_id": credential[0], "expires_at": expires,
                    "signature": self.identity.sign(hashlib.sha256(value+proof).digest())}
            try:
                return self.writer.call(change)
            except AuthError:
                self.failures.append(self.clock())
                raise

    def validate_session(self, secret):
        def read(db):
            row = db.execute("SELECT s.principal_id,s.expires_at,s.epoch,e.epoch,p.revoked_at FROM sessions s JOIN principals p ON p.id=s.principal_id JOIN auth_epoch e ON e.id=1 WHERE s.token_hash=? AND p.kind='EXTENSION'", (self._hash(secret.encode()),)).fetchone()
            if not row or row[4] or row[2] != row[3] or seconds(row[1]) <= self.clock():
                raise AuthError("SESSION_EXPIRED")
            return row[0]
        return self.writer.call(read, transaction=False)
