CREATE TABLE task_execution(
 task_id TEXT PRIMARY KEY REFERENCES tasks(id),
 max_candidates INTEGER NOT NULL CHECK(max_candidates BETWEEN 1 AND 10000),
 policy_id TEXT REFERENCES policies(id), revision INTEGER NOT NULL CHECK(revision>=1)
);
CREATE TABLE worker_jobs(
 run_id TEXT PRIMARY KEY REFERENCES runs(id), lease_id TEXT NOT NULL REFERENCES leases(id),
 criteria_version TEXT NOT NULL REFERENCES content_versions(id),
 state TEXT NOT NULL CHECK(state IN('RUNNING','WAITING','DONE')),
 wake_cursor INTEGER NOT NULL DEFAULT 0, error_code TEXT
);
CREATE TABLE worker_pages(
 run_id TEXT NOT NULL REFERENCES runs(id), criteria_version TEXT NOT NULL REFERENCES content_versions(id),
 cursor_key TEXT NOT NULL, result_version TEXT NOT NULL REFERENCES content_versions(id),
 PRIMARY KEY(run_id,criteria_version,cursor_key)
);
CREATE TABLE worker_preparations(
 run_id TEXT NOT NULL REFERENCES runs(id), job_id TEXT NOT NULL REFERENCES jobs(id),
 criteria_version TEXT NOT NULL REFERENCES content_versions(id),
 draft_id TEXT NOT NULL REFERENCES drafts(id), context_version TEXT NOT NULL REFERENCES content_versions(id),
 PRIMARY KEY(run_id,job_id,criteria_version)
);
