CREATE TABLE extraction_claims(
 operation_id TEXT PRIMARY KEY REFERENCES operations(id),
 worker_id TEXT NOT NULL, generation INTEGER NOT NULL CHECK(generation>=1),
 result_digest TEXT, result_version TEXT REFERENCES content_versions(id)
);
