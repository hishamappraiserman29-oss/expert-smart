"""Owner isolation tests for the owner_user_id column (auth wave S1).

Design: owner_user_id is added by the versioned _migrate_to_v2 migration,
registered in _MIGRATIONS[2].  SCHEMA_VERSION = 2.  The column appears in
fresh DBs via CREATE_TABLES_SQL and in existing v1 DBs via ALTER TABLE inside
the migration.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parents[1]
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from reports.db.migrations import current_version, migrate
from reports.db import (
    count_reports,
    delete_report,
    get_report,
    list_reports,
    save_report,
)


@pytest.fixture
def db(tmp_path):
    return tmp_path / "owner.db"


# ── Schema + Column presence ─────────────────────────────────────────


class TestOwnerColumn:
    def test_fresh_db_has_owner_column(self, db):
        """A brand-new DB opened via save_report already has owner_user_id."""
        save_report({"x": 1}, profile_key="legacy", db_path=db)
        conn = sqlite3.connect(db)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(reports)")}
        conn.close()
        assert "owner_user_id" in cols

    def test_migration_idempotent(self, db):
        """Calling migrate() multiple times produces exactly one owner_user_id column."""
        conn = sqlite3.connect(db)
        migrate(conn)
        migrate(conn)
        migrate(conn)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(reports)")]
        conn.close()
        assert cols.count("owner_user_id") == 1

    def test_index_on_owner_created(self, db):
        """idx_reports_owner index is present after migrate()."""
        conn = sqlite3.connect(db)
        migrate(conn)
        indexes = [r[1] for r in conn.execute("PRAGMA index_list(reports)")]
        conn.close()
        assert "idx_reports_owner" in indexes

    def test_v1_db_migrates_to_v2_with_system_owner(self, db):
        """A v1 DB without owner_user_id migrates to v2 and stamps old rows."""
        conn = sqlite3.connect(db)
        conn.executescript("""
            CREATE TABLE schema_version (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                version INTEGER NOT NULL
            );
            CREATE TABLE reports (
                report_id TEXT PRIMARY KEY,
                profile_key TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                appraiser_name TEXT,
                market_value REAL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                data_json TEXT NOT NULL
            );
        """)
        conn.execute("INSERT INTO schema_version (id, version) VALUES (1, 1)")
        conn.execute(
            "INSERT INTO reports VALUES "
            "('old-1', 'legacy', 'final', NULL, NULL, "
            "'2025-01-01', '2025-01-01', '{}')"
        )
        conn.commit()

        migrate(conn)

        assert current_version(conn) == 2
        owner = conn.execute(
            "SELECT owner_user_id FROM reports WHERE report_id='old-1'"
        ).fetchone()[0]
        assert owner == "__system__"
        conn.close()

    def test_v1_db_gets_owner_column_via_db_engine(self, db):
        """Simulate a pre-auth v1 DB; opening via db_engine migrates transparently."""
        conn = sqlite3.connect(db)
        conn.executescript("""
            CREATE TABLE schema_version (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                version INTEGER NOT NULL
            );
            CREATE TABLE reports (
                report_id TEXT PRIMARY KEY,
                profile_key TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                appraiser_name TEXT,
                market_value REAL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                data_json TEXT NOT NULL
            );
        """)
        conn.execute("INSERT INTO schema_version (id, version) VALUES (1, 1)")
        conn.execute(
            "INSERT INTO reports VALUES "
            "('old-1','legacy','draft','pre-auth',100.0,"
            "'2025-01-01T00:00:00','2025-01-01T00:00:00','{}')"
        )
        conn.commit()
        conn.close()

        rec = get_report("old-1", db_path=db)
        assert rec is not None
        assert rec.owner_user_id == "__system__"


# ── Backward-compat: existing callers need no changes ────────────────


class TestBackwardCompat:
    def test_save_without_owner_defaults_to_system(self, db):
        rid = save_report({"x": 1}, profile_key="legacy", db_path=db)
        rec = get_report(rid, db_path=db)
        assert rec.owner_user_id == "__system__"

    def test_list_without_filter_returns_all_owners(self, db):
        save_report({"x": 1}, profile_key="legacy", db_path=db)
        save_report({"x": 2}, profile_key="legacy", owner_user_id="alice", db_path=db)
        assert len(list_reports(db_path=db)) == 2

    def test_get_without_owner_filter_ignores_owner(self, db):
        rid = save_report({"x": 1}, profile_key="legacy",
                          owner_user_id="alice", db_path=db)
        assert get_report(rid, db_path=db) is not None

    def test_delete_without_owner_filter_removes_any(self, db):
        rid = save_report({"x": 1}, profile_key="legacy",
                          owner_user_id="alice", db_path=db)
        assert delete_report(rid, db_path=db) is True

    def test_none_owner_on_save_maps_to_system(self, db):
        rid = save_report({"x": 1}, profile_key="legacy",
                          owner_user_id=None, db_path=db)
        rec = get_report(rid, db_path=db)
        assert rec.owner_user_id == "__system__"


# ── Owner-based isolation (new feature) ──────────────────────────────


class TestOwnerIsolation:
    def test_list_filters_by_owner(self, db):
        save_report({"x": 1}, profile_key="legacy", owner_user_id="alice", db_path=db)
        save_report({"x": 2}, profile_key="legacy", owner_user_id="bob", db_path=db)
        save_report({"x": 3}, profile_key="legacy", owner_user_id="alice", db_path=db)

        assert len(list_reports(owner_user_id="alice", db_path=db)) == 2
        assert len(list_reports(owner_user_id="bob", db_path=db)) == 1

    def test_get_with_matching_owner_returns_record(self, db):
        rid = save_report({"x": 1}, profile_key="legacy",
                          owner_user_id="alice", db_path=db)
        assert get_report(rid, owner_user_id="alice", db_path=db) is not None

    def test_get_with_wrong_owner_returns_none(self, db):
        rid = save_report({"x": 1}, profile_key="legacy",
                          owner_user_id="alice", db_path=db)
        assert get_report(rid, owner_user_id="bob", db_path=db) is None

    def test_delete_with_matching_owner_succeeds(self, db):
        rid = save_report({"x": 1}, profile_key="legacy",
                          owner_user_id="alice", db_path=db)
        assert delete_report(rid, owner_user_id="alice", db_path=db) is True

    def test_delete_with_wrong_owner_fails(self, db):
        rid = save_report({"x": 1}, profile_key="legacy",
                          owner_user_id="alice", db_path=db)
        assert delete_report(rid, owner_user_id="bob", db_path=db) is False

    def test_count_filters_by_owner(self, db):
        save_report({"x": 1}, profile_key="legacy", owner_user_id="alice", db_path=db)
        save_report({"x": 2}, profile_key="legacy", owner_user_id="bob", db_path=db)

        assert count_reports(owner_user_id="alice", db_path=db) == 1
        assert count_reports(db_path=db) == 2

    def test_round_trip_preserves_owner(self, db):
        rid = save_report({"x": "العربية"}, profile_key="legacy",
                          owner_user_id="user-123", db_path=db)
        rec = get_report(rid, db_path=db)
        assert rec.owner_user_id == "user-123"
        assert rec.data == {"x": "العربية"}

    def test_system_owner_saved_and_retrievable(self, db):
        rid = save_report({"x": 1}, profile_key="legacy",
                          owner_user_id="__system__", db_path=db)
        assert get_report(rid, owner_user_id="__system__", db_path=db) is not None
