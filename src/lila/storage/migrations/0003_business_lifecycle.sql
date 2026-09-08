-- Additive M2 lifecycle and reviewed-operation metadata; preserve migrations 1/2.
CREATE TABLE run_progress(run_id TEXT PRIMARY KEY REFERENCES runs(id), discovery_complete INTEGER NOT NULL DEFAULT 0 CHECK(discovery_complete IN(0,1)));
INSERT INTO run_progress(run_id) SELECT id FROM runs;
CREATE TABLE run_blockers(run_id TEXT NOT NULL REFERENCES runs(id), reason TEXT NOT NULL, PRIMARY KEY(run_id,reason));
CREATE TABLE correction_previews(operation_id TEXT PRIMARY KEY REFERENCES operations(id), action_id TEXT NOT NULL REFERENCES actions(id), action_revision INTEGER NOT NULL, application_revision INTEGER NOT NULL, payload_version TEXT NOT NULL REFERENCES content_versions(id), digest TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1, state TEXT NOT NULL CHECK(state IN('PENDING','APPLIED','REJECTED')));
CREATE TABLE audit_head(id INTEGER PRIMARY KEY CHECK(id=1), sequence INTEGER NOT NULL, tag BLOB NOT NULL);
INSERT INTO audit_head SELECT 1,coalesce((SELECT max(sequence) FROM audit_events),0),coalesce((SELECT tag FROM audit_events ORDER BY sequence DESC LIMIT 1),zeroblob(32));
