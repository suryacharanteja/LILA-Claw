import sqlite3
import pytest
import lila.storage.migrations as migrations

def test_failed_migration_rolls_back_schema_and_version(tmp_path, monkeypatch):
    (tmp_path / "0001_business.sql").write_text("CREATE TABLE partial(x); INVALID SQL;")
    monkeypatch.setattr(migrations, "ROOT", tmp_path)
    db = sqlite3.connect(":memory:")
    with pytest.raises(sqlite3.Error):
        migrations.apply_initial_schema(db, "business")
    assert db.execute("PRAGMA user_version").fetchone()[0] == 0
    assert not db.execute("SELECT name FROM sqlite_master WHERE name='partial'").fetchall()

def test_store_name_cannot_select_arbitrary_file():
    db = sqlite3.connect(":memory:")
    with pytest.raises(ValueError):
        migrations.apply_initial_schema(db, "../business")
