CREATE TABLE ai_ownership(
 invocation_id TEXT PRIMARY KEY REFERENCES ai_invocations(id),
 worker_id TEXT NOT NULL, generation INTEGER NOT NULL CHECK(generation>=1),
 lease_id TEXT NOT NULL REFERENCES leases(id), policy_id TEXT NOT NULL REFERENCES policies(id),
 result_digest TEXT, claimed_at TEXT
);
