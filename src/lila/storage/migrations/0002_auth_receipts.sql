-- M1 implementation detail for LLD-07 idempotent auth revocation commands.
-- No tokens or CSRF values are stored in these receipts.
CREATE TABLE auth_schema_migrations(version INTEGER PRIMARY KEY, checksum TEXT NOT NULL, applied_at TEXT NOT NULL);
CREATE TABLE auth_command_receipts(
    principal_id TEXT NOT NULL REFERENCES principals(id),
    command_id TEXT NOT NULL,
    request_digest TEXT NOT NULL,
    result_json TEXT NOT NULL CHECK(json_valid(result_json)),
    created_at TEXT NOT NULL,
    PRIMARY KEY(principal_id,command_id)
);
