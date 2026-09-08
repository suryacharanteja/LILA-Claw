-- M2 implementation metadata for exact previews, scoped actions and timezone carries.
CREATE TABLE review_previews(id TEXT PRIMARY KEY, account_id TEXT NOT NULL REFERENCES accounts(id), payload_version TEXT NOT NULL REFERENCES content_versions(id), members_version TEXT NOT NULL REFERENCES content_versions(id), revision INTEGER NOT NULL, state TEXT NOT NULL CHECK(state IN('PENDING','APPROVED','REJECTED')));
CREATE TABLE action_contexts(action_id TEXT PRIMARY KEY REFERENCES actions(id), domain TEXT NOT NULL, tab_id INTEGER NOT NULL CHECK(tab_id>=0));
CREATE TABLE budget_window_carries(source_id TEXT NOT NULL REFERENCES budget_windows(id), target_id TEXT NOT NULL REFERENCES budget_windows(id), PRIMARY KEY(source_id,target_id), CHECK(source_id<>target_id));
CREATE TRIGGER fact_version_immutable BEFORE UPDATE ON fact_versions BEGIN SELECT RAISE(ABORT,'append fact version instead'); END;
