"""Unit tests for core_engine.audit_log (Auth Wave S5)."""
from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import os
os.chdir(str(_CORE))

from audit_log import fetch_audit_logs, is_enabled, log_access  # noqa: E402
from reports.db.migrations import migrate  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def enable_audit(monkeypatch):
    """Override conftest.py autouse AUDIT_ENABLED=false for audit tests."""
    monkeypatch.setenv("AUDIT_ENABLED", "true")


@pytest.fixture()
def db(tmp_path, enable_audit):
    """Migrated temp DB for audit tests."""
    p = tmp_path / "audit_test.db"
    conn = sqlite3.connect(str(p))
    migrate(conn)
    conn.close()
    return p


# ── AU01–AU06: log_access ─────────────────────────────────────────────────────

class TestLogAccess:
    def test_AU01_logs_basic_row(self, db):
        log_access(
            user_id="alice", endpoint="/api/reports", method="GET",
            status=200, ip="127.0.0.1", db_path=db,
        )
        rows = fetch_audit_logs(db_path=db)
        assert len(rows) == 1
        r = rows[0]
        assert r["user_id"] == "alice"
        assert r["endpoint"] == "/api/reports"
        assert r["method"] == "GET"
        assert r["status"] == 200
        assert r["ip"] == "127.0.0.1"

    def test_AU02_anonymous_user_logged_as_null(self, db):
        log_access(
            user_id=None, endpoint="/api/reports", method="GET",
            status=401, db_path=db,
        )
        rows = fetch_audit_logs(db_path=db)
        assert rows[0]["user_id"] is None
        assert rows[0]["status"] == 401

    def test_AU03_report_id_captured(self, db):
        log_access(
            user_id="alice", endpoint="/api/reports/r-123",
            method="GET", status=200, report_id="r-123", db_path=db,
        )
        rows = fetch_audit_logs(db_path=db)
        assert rows[0]["report_id"] == "r-123"

    def test_AU04_created_at_is_utc_iso(self, db):
        log_access(
            user_id="alice", endpoint="/api/reports",
            method="GET", status=200, db_path=db,
        )
        ts = fetch_audit_logs(db_path=db)[0]["created_at"]
        assert "T" in ts
        assert "+" in ts or ts.endswith("Z")

    def test_AU05_disabled_no_write(self, db, monkeypatch):
        monkeypatch.setenv("AUDIT_ENABLED", "false")
        log_access(
            user_id="alice", endpoint="/api/reports",
            method="GET", status=200, db_path=db,
        )
        assert fetch_audit_logs(db_path=db) == []

    def test_AU06_write_failure_is_silent(self, enable_audit):
        """Bad db_path → log_access must not raise."""
        log_access(
            user_id="alice", endpoint="/api/reports",
            method="GET", status=200,
            db_path="/nonexistent/path/to/audit.db",
        )  # must not raise


# ── AU07–AU10: fetch_audit_logs ───────────────────────────────────────────────

class TestFetchAuditLogs:
    def test_AU07_filter_by_user(self, db):
        log_access(user_id="alice", endpoint="/api/reports",
                   method="GET", status=200, db_path=db)
        log_access(user_id="bob", endpoint="/api/reports",
                   method="GET", status=200, db_path=db)
        alice_rows = fetch_audit_logs(user_id="alice", db_path=db)
        assert len(alice_rows) == 1
        assert alice_rows[0]["user_id"] == "alice"

    def test_AU08_ordered_newest_first(self, db):
        log_access(user_id="first", endpoint="/api/reports",
                   method="GET", status=200, db_path=db)
        time.sleep(0.02)
        log_access(user_id="second", endpoint="/api/reports",
                   method="GET", status=200, db_path=db)
        rows = fetch_audit_logs(db_path=db)
        assert rows[0]["user_id"] == "second"

    def test_AU09_pagination(self, db):
        for i in range(5):
            log_access(user_id=f"u{i}", endpoint="/api/reports",
                       method="GET", status=200, db_path=db)
        page = fetch_audit_logs(limit=2, offset=0, db_path=db)
        assert len(page) == 2

    def test_AU10_returns_all_columns(self, db):
        log_access(user_id="alice", endpoint="/api/reports/r-1",
                   method="GET", status=200, report_id="r-1",
                   ip="10.0.0.1", db_path=db)
        row = fetch_audit_logs(db_path=db)[0]
        for col in ("id", "user_id", "endpoint", "method", "status",
                    "report_id", "ip", "created_at"):
            assert col in row, f"missing column: {col}"


# ── AU11–AU12: is_enabled ─────────────────────────────────────────────────────

class TestIsEnabled:
    def test_AU11_default_enabled(self, monkeypatch):
        monkeypatch.delenv("AUDIT_ENABLED", raising=False)
        assert is_enabled() is True

    def test_AU12_false_disables(self, monkeypatch):
        monkeypatch.setenv("AUDIT_ENABLED", "false")
        assert is_enabled() is False


# ── AU13–AU16: purge_audit_logs ───────────────────────────────────────────────

from audit_log import purge_audit_logs  # noqa: E402


class TestPurgeAuditLogs:
    def test_AU13_deletes_rows_before_cutoff(self, db):
        import sqlite3 as _sqlite3
        # seed a recent row via log_access
        log_access(user_id="alice", endpoint="/x", method="GET",
                   status=200, db_path=db)
        # manually insert an old row (backdated)
        conn = _sqlite3.connect(db)
        conn.execute(
            "INSERT INTO report_access_log "
            "(user_id, endpoint, method, status, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("old-user", "/x", "GET", 200, "2020-01-01T00:00:00+00:00"),
        )
        conn.commit()
        conn.close()

        n = purge_audit_logs(
            older_than_iso="2025-01-01T00:00:00+00:00",
            db_path=db,
        )
        assert n == 1
        rows = fetch_audit_logs(db_path=db)
        assert all(r["user_id"] != "old-user" for r in rows)

    def test_AU14_empty_cutoff_raises_value_error(self, db):
        with pytest.raises(ValueError):
            purge_audit_logs(older_than_iso="", db_path=db)

    def test_AU15_no_match_returns_zero(self, db):
        n = purge_audit_logs(
            older_than_iso="1900-01-01T00:00:00+00:00",
            db_path=db,
        )
        assert n == 0

    def test_AU16_multiple_old_rows_all_deleted(self, db):
        import sqlite3 as _sqlite3
        conn = _sqlite3.connect(db)
        for i in range(5):
            conn.execute(
                "INSERT INTO report_access_log "
                "(user_id, endpoint, method, status, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (f"u{i}", "/x", "GET", 200, "2019-01-01T00:00:00+00:00"),
            )
        conn.commit()
        conn.close()

        n = purge_audit_logs(
            older_than_iso="2025-01-01T00:00:00+00:00",
            db_path=db,
        )
        assert n == 5
        assert fetch_audit_logs(db_path=db) == []
