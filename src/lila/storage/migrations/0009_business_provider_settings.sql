CREATE TABLE provider_settings(
 account_id TEXT PRIMARY KEY REFERENCES accounts(id),
 config_version TEXT NOT NULL REFERENCES content_versions(id),
 credential_id TEXT NOT NULL,
 revision INTEGER NOT NULL CHECK(revision>=1)
);
