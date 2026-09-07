-- Separate keyed SQLCipher auth store; never included in business backup.
PRAGMA foreign_keys=ON;
CREATE TABLE auth_epoch(id INTEGER PRIMARY KEY CHECK(id=1),epoch INTEGER NOT NULL CHECK(epoch>0));
INSERT INTO auth_epoch VALUES(1,1);
CREATE TABLE principals(id TEXT PRIMARY KEY,kind TEXT NOT NULL CHECK(kind IN('UI','EXTENSION','WORKER')),scope_json TEXT NOT NULL CHECK(json_valid(scope_json)),revision INTEGER NOT NULL DEFAULT 1,revoked_at TEXT);
CREATE TABLE credentials(id TEXT PRIMARY KEY,principal_id TEXT NOT NULL REFERENCES principals(id),epoch INTEGER NOT NULL,secret_hash BLOB NOT NULL,protected_proof_secret BLOB,expires_at TEXT NOT NULL,revoked_at TEXT);
CREATE TABLE sessions(id TEXT PRIMARY KEY,principal_id TEXT NOT NULL REFERENCES principals(id),epoch INTEGER NOT NULL,token_hash BLOB NOT NULL UNIQUE,csrf_hash BLOB,expires_at TEXT NOT NULL,renewed_to TEXT REFERENCES sessions(id),overlap_until TEXT);
CREATE TABLE pairing(id TEXT PRIMARY KEY,protected_secret BLOB NOT NULL,server_nonce BLOB,client_nonce BLOB,attempts INTEGER NOT NULL DEFAULT 0 CHECK(attempts BETWEEN 0 AND 5),expires_at TEXT NOT NULL,state TEXT NOT NULL CHECK(state IN('CREATED','PROVED','OWNER_CONFIRMED','CONSUMED','EXPIRED','REVOKED')));
CREATE TABLE bootstrap(token_hash BLOB PRIMARY KEY,expires_at TEXT NOT NULL,consumed_at TEXT);
CREATE TABLE provider_secrets(id TEXT PRIMARY KEY,provider TEXT NOT NULL,dpapi_blob BLOB NOT NULL,revision INTEGER NOT NULL);
CREATE TABLE install_identity(id INTEGER PRIMARY KEY CHECK(id=1),install_id TEXT NOT NULL,certificate_thumbprint TEXT NOT NULL,leaf_spki_digest TEXT NOT NULL,protected_key_manifest BLOB NOT NULL,release_sequence INTEGER NOT NULL DEFAULT 0);
