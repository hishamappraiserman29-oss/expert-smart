"""Tests for tools/backup_reports.py."""
import sqlite3
import sys
import time
from pathlib import Path

import pytest

# Make tools importable
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from tools.backup_reports import backup, prune

from core_engine.reports.db.migrations import migrate


@pytest.fixture
def source_db(tmp_path):
    """A migrated v3 DB with one report row + one audit row."""
    db = tmp_path / "source.db"
    conn = sqlite3.connect(db)
    migrate(conn)
    conn.execute(
        "INSERT INTO reports (report_id, profile_key, status, created_at, "
        "updated_at, data_json) VALUES (?, ?, ?, ?, ?, ?)",
        ("r-1", "legacy", "final", "2026-01-01T00:00:00Z",
         "2026-01-01T00:00:00Z", '{"x": 1}'),
    )
    conn.execute(
        "INSERT INTO report_access_log (endpoint, method, status, created_at) "
        "VALUES (?, ?, ?, ?)",
        ("/api/reports", "GET", 200, "2026-01-01T00:00:00Z"),
    )
    conn.commit()
    conn.close()
    return db


class TestBackup:
    def test_creates_timestamped_file(self, source_db, tmp_path):
        dest = tmp_path / "backups"
        out = backup(source_db, dest)
        assert out.exists()
        assert out.name.startswith("reports_") and out.suffix == ".db"

    def test_backup_is_valid_sqlite(self, source_db, tmp_path):
        out = backup(source_db, tmp_path / "backups")
        conn = sqlite3.connect(out)
        try:
            rows = conn.execute(
                "SELECT COUNT(*) FROM reports"
            ).fetchone()
            assert rows[0] == 1
            rows = conn.execute(
                "SELECT COUNT(*) FROM report_access_log"
            ).fetchone()
            assert rows[0] == 1
        finally:
            conn.close()

    def test_backup_contains_schema_version_table(self, source_db, tmp_path):
        out = backup(source_db, tmp_path / "backups")
        conn = sqlite3.connect(out)
        try:
            row = conn.execute("SELECT version FROM schema_version").fetchone()
            assert row is not None
            assert row[0] == 3
        finally:
            conn.close()

    def test_dest_dir_created_if_missing(self, source_db, tmp_path):
        dest = tmp_path / "deep" / "nested" / "backups"
        assert not dest.exists()
        out = backup(source_db, dest)
        assert dest.exists()
        assert out.exists()

    def test_multiple_backups_distinct_files(self, source_db, tmp_path):
        dest = tmp_path / "backups"
        out1 = backup(source_db, dest)
        time.sleep(1.1)  # ensure different timestamp
        out2 = backup(source_db, dest)
        assert out1 != out2
        assert out1.exists() and out2.exists()

    def test_missing_source_returns_error(self, tmp_path):
        from tools.backup_reports import main
        sys.argv = [
            "backup", "--source", str(tmp_path / "nope.db"),
            "--dest-dir", str(tmp_path / "backups"),
        ]
        assert main() == 1


class TestPrune:
    def test_old_backups_deleted(self, tmp_path):
        dest = tmp_path / "backups"
        dest.mkdir()
        # Create an old backup file
        old = dest / "reports_19990101T000000Z.db"
        old.write_bytes(b"")
        import os
        old_ts = time.time() - 86400 * 100
        os.utime(old, (old_ts, old_ts))
        # Create a fresh one
        fresh = dest / "reports_29990101T000000Z.db"
        fresh.write_bytes(b"")
        deleted = prune(dest, retention_days=30)
        assert old in deleted
        assert fresh.exists()

    def test_nothing_deleted_when_all_fresh(self, tmp_path):
        dest = tmp_path / "backups"
        dest.mkdir()
        recent = dest / "reports_29990101T000000Z.db"
        recent.write_bytes(b"")
        assert prune(dest, retention_days=30) == []

    def test_prune_returns_list_of_deleted_paths(self, tmp_path):
        dest = tmp_path / "backups"
        dest.mkdir()
        import os
        for i in range(3):
            f = dest / f"reports_old{i}_20000101T000000Z.db"
            f.write_bytes(b"")
            old_ts = time.time() - 86400 * 40
            os.utime(f, (old_ts, old_ts))
        deleted = prune(dest, retention_days=30)
        assert len(deleted) == 3
        for p in deleted:
            assert not p.exists()

    def test_non_matching_files_untouched(self, tmp_path):
        dest = tmp_path / "backups"
        dest.mkdir()
        import os
        # old file with wrong prefix — must NOT be deleted
        other = dest / "other_old_file.db"
        other.write_bytes(b"")
        old_ts = time.time() - 86400 * 100
        os.utime(other, (old_ts, old_ts))
        prune(dest, retention_days=30)
        assert other.exists()
