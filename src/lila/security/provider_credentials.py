"""Owner-configured API credentials; DPAPI inside the separate encrypted auth store."""
import hashlib
import hmac
import json
from uuid import uuid4
from lila.security.windows import protect,unprotect
from lila.security.sessions import AuthError,timestamp


class ProviderCredentials:
    def __init__(self,sessions,digest_key):
        self.sessions=sessions
        self.digest_key=digest_key

    def save(self,secret,csrf,command_id,api_key):
        if not isinstance(api_key,str) or not 1<=len(api_key)<=1024 or not api_key.isascii() or any(c.isspace() for c in api_key):
            raise AuthError('INVALID_REQUEST')
        digest=hmac.digest(self.digest_key,b'provider-key-v1\x00'+api_key.encode(),'sha256').hex()
        protected=protect(api_key.encode())
        def change(db):
            actor=self.sessions._lookup(db,secret,csrf)[1]
            prior=db.execute('SELECT request_digest,result_json FROM auth_command_receipts WHERE principal_id=? AND command_id=?',(actor,command_id)).fetchone()
            if prior:
                if prior[0]!=digest:
                    raise AuthError('COMMAND_ID_REUSED')
                return json.loads(prior[1])
            credential=str(uuid4())
            db.execute("INSERT INTO provider_secrets VALUES(?,'openai',?,1)",(credential,protected))
            result={'credential_id':credential,'command_id':command_id,'accepted':True}
            db.execute('INSERT INTO auth_command_receipts VALUES(?,?,?,?,?)',(actor,command_id,digest,json.dumps(result),timestamp(self.sessions.clock())))
            return result
        return self.sessions.writer.call(change)

    def read(self,credential):
        row=self.sessions.writer.call(lambda db:db.execute("SELECT dpapi_blob FROM provider_secrets WHERE id=? AND provider='openai'",(credential,)).fetchone(),transaction=False)
        if not row:
            raise AuthError('PROVIDER_CREDENTIAL_REQUIRED')
        return unprotect(row[0]).decode()

    def exists(self,credential):
        return self.sessions.writer.call(lambda db:db.execute("SELECT 1 FROM provider_secrets WHERE id=? AND provider='openai'",(credential,)).fetchone() is not None,transaction=False)
