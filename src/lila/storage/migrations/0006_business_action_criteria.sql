CREATE TABLE action_criteria(action_id TEXT PRIMARY KEY REFERENCES actions(id), criteria_version TEXT NOT NULL REFERENCES content_versions(id));
INSERT INTO action_criteria SELECT a.id,t.criteria_version FROM actions a JOIN runs r ON r.id=a.run_id JOIN tasks t ON t.id=r.task_id;
CREATE TRIGGER action_criteria_immutable BEFORE UPDATE ON action_criteria BEGIN SELECT RAISE(ABORT,'immutable action criteria'); END;
