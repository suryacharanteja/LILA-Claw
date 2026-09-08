CREATE TABLE action_blockers(action_id TEXT PRIMARY KEY REFERENCES actions(id), reason TEXT NOT NULL, occurred_at TEXT NOT NULL);
