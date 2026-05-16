"""Tests for tools/apply_retention.py."""
from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from core_engine.reports.db import save_report
from core_engine.reports.db.migrations import migrate

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "tools" / "apply_retention.py"


def _run(args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=60,
    )


@pytest.fixture
def db(tmp_path):
    """A migrated DB with a mix of fresh/old drafts + archived rows + audit rows."""
    path = tmp_path / "data.db"
    # Fresh rows (created now — won't be affected by 30-day threshold)
    save_report({"x": 1}, profile_key="legacy", report_id="r-fresh-draft",
                status="draft", db_path=path)
    save_report({"x": 2}, profile_key="legacy", report_id="r-fresh-archived",
                status="archived", db_path=path)
    # Old rows inserted directly with backdated timestamps
    conn = sqlite3.connect(path)
    conn.execute(
        "INSERT INTO reports (report_id, profile_key, status, "
        "created_at, updated_at, data_json) VALUES "
        "('r-old-draft', 'legacy', 'draft', "
        "'2020-01-01T00:00:00+00:00', '2020-01-01T00:00:00+00:00', '{}')"
    )
    conn.execute(
        "INSERT INTO reports (report_id, profile_key, status, "
        "created_at, updated_at, data_json) VALUES "
        "('r-old-archived', 'legacy', 'archived', "
        "'2020-01-01T00:00:00+00:00', '2020-01-01T00:00:00+00:00', '{}')"
    )
    # Old audit row + future audit row
    conn.execute(
        "INSERT INTO report_access_log (user_id, endpoint, method, status, created_at) "
        "VALUES ('u', '/x', 'GET', 200, '2020-01-01T00:00:00+00:00')"
    )
    conn.execute(
        "INSERT INTO report_access_log (user_id, endpoint, method, status, created_at) "
        "VALUES ('u', '/x', 'GET', 200, '2099-01-01T00:00:00+00:00')"
    )
    conn.commit()
    conn.close()
    return path


# ── Dry-run (default) ─────────────────────────────────────────────────────────

class TestDryRun:
    def test_dry_run_is_default(self, db):
        r = _run(["--db", str(db)])
        assert r.returncode == 0
        assert "DRY-RUN" in r.stdout

    def test_dry_run_prints_no_changes_message(self, db):
        r = _run(["--db", str(db)])
        assert "no changes applied" in r.stdout.lower()

    def test_dry_run_does_not_archive_old_draft(self, db):
        _run(["--db", str(db)])
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT status FROM reports WHERE report_id='r-old-draft'"
        ).fetchone()
        conn.close()
        assert row[0] == "draft"

    def test_dry_run_does_not_delete_audit_rows(self, db):
        _run(["--db", str(db)])
        conn = sqlite3.connect(db)
        cnt = conn.execute(
            "SELECT COUNT(*) FROM report_access_log"
        ).fetchone()[0]
        conn.close()
        assert cnt == 2


# ── Apply — drafts archival ───────────────────────────────────────────────────

class TestApplyDrafts:
    def test_archives_old_draft(self, db):
        r = _run(["--db", str(db), "--apply", "--drafts-to-archive", "30"])
        assert r.returncode == 0
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT status FROM reports WHERE report_id='r-old-draft'"
        ).fetchone()
        conn.close()
        assert row[0] == "archived"

    def test_keeps_fresh_draft_unchanged(self, db):
        _run(["--db", str(db), "--apply", "--drafts-to-archive", "30"])
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT status FROM reports WHERE report_id='r-fresh-draft'"
        ).fetchone()
        conn.close()
        assert row[0] == "draft"

    def test_negative_one_disables_drafts_archival(self, db):
        _run(["--db", str(db), "--apply", "--drafts-to-archive", "-1"])
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT status FROM reports WHERE report_id='r-old-draft'"
        ).fetchone()
        conn.close()
        assert row[0] == "draft"


# ── Apply — archived deletion ─────────────────────────────────────────────────

class TestApplyArchived:
    def test_deletes_old_archived_when_enabled(self, db):
        r = _run([
            "--db", str(db), "--apply",
            "--archived-to-delete", "30",
        ])
        assert r.returncode == 0
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT 1 FROM reports WHERE report_id='r-old-archived'"
        ).fetchone()
        conn.close()
        assert row is None

    def test_archived_deletion_disabled_by_default(self, db):
        _run(["--db", str(db), "--apply"])
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT 1 FROM reports WHERE report_id='r-old-archived'"
        ).fetchone()
        conn.close()
        assert row is not None

    def test_keeps_fresh_archived_when_threshold_set(self, db):
        _run([
            "--db", str(db), "--apply",
            "--archived-to-delete", "30",
        ])
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT 1 FROM reports WHERE report_id='r-fresh-archived'"
        ).fetchone()
        conn.close()
        assert row is not None


# ── Apply — audit purge ───────────────────────────────────────────────────────

class TestApplyAudit:
    def test_purges_old_audit_rows(self, db):
        r = _run(["--db", str(db), "--apply", "--audit-to-delete", "30"])
        assert r.returncode == 0
        conn = sqlite3.connect(db)
        rows = conn.execute(
            "SELECT created_at FROM report_access_log"
        ).fetchall()
        conn.close()
        assert len(rows) == 1
        assert "2099" in rows[0][0]

    def test_negative_one_disables_audit_purge(self, db):
        _run(["--db", str(db), "--apply", "--audit-to-delete", "-1"])
        conn = sqlite3.connect(db)
        cnt = conn.execute(
            "SELECT COUNT(*) FROM report_access_log"
        ).fetchone()[0]
        conn.close()
        assert cnt == 2


# ── Error handling ────────────────────────────────────────────────────────────

class TestErrors:
    def test_missing_db_returns_nonzero(self, tmp_path):
        r = _run(["--db", str(tmp_path / "nope.db")])
        assert r.returncode == 1
