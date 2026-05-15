"""Tests for core_engine/reports/db/migrations.py — Wave 7c.1."""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_CORE))
os.chdir(str(_CORE))

from reports.db.migrations import current_version, migrate  # noqa: E402
from reports.db.schema import SCHEMA_VERSION  # noqa: E402


@pytest.fixture()
def fresh_conn(tmp_path):
    """New SQLite connection on a temp file — no tables pre-created."""
    c = sqlite3.connect(str(tmp_path / "mig.db"))
    yield c
    c.close()


@pytest.fixture()
def memory_conn():
    """In-memory SQLite connection."""
    c = sqlite3.connect(":memory:")
    yield c
    c.close()


class TestCurrentVersion:
    def test_MIG01_fresh_db_returns_zero(self, fresh_conn):
        assert current_version(fresh_conn) == 0

    def test_MIG02_memory_db_fresh_returns_zero(self, memory_conn):
        assert current_version(memory_conn) == 0

    def test_MIG03_after_migrate_returns_correct_version(self, fresh_conn):
        migrate(fresh_conn)
        assert current_version(fresh_conn) == SCHEMA_VERSION

    def test_MIG04_version_is_int(self, fresh_conn):
        v = current_version(fresh_conn)
        assert isinstance(v, int)


class TestMigrateFunction:
    def test_MIG05_migrate_returns_target_version(self, fresh_conn):
        v = migrate(fresh_conn)
        assert v == SCHEMA_VERSION

    def test_MIG06_migrate_creates_reports_table(self, fresh_conn):
        migrate(fresh_conn)
        rows = fresh_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='reports'"
        ).fetchall()
        assert len(rows) == 1

    def test_MIG07_migrate_creates_schema_version_table(self, fresh_conn):
        migrate(fresh_conn)
        rows = fresh_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        ).fetchall()
        assert len(rows) == 1

    def test_MIG08_schema_version_row_inserted(self, fresh_conn):
        migrate(fresh_conn)
        row = fresh_conn.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] == 1

    def test_MIG09_idempotent_called_twice(self, fresh_conn):
        v1 = migrate(fresh_conn)
        v2 = migrate(fresh_conn)
        assert v1 == v2

    def test_MIG10_idempotent_no_duplicate_version_rows(self, fresh_conn):
        migrate(fresh_conn)
        migrate(fresh_conn)
        count = fresh_conn.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0]
        assert count == 1

    def test_MIG11_idempotent_on_memory_db(self, memory_conn):
        migrate(memory_conn)
        migrate(memory_conn)
        v = current_version(memory_conn)
        assert v == SCHEMA_VERSION

    def test_MIG12_migrate_with_explicit_target(self, fresh_conn):
        v = migrate(fresh_conn, target_version=1)
        assert v == 1

    def test_MIG13_migrate_target_zero_is_noop(self, fresh_conn):
        """target_version=0 means nothing to run — version stays 0."""
        v = migrate(fresh_conn, target_version=0)
        assert v == 0

    def test_MIG14_reports_table_columns_after_migration(self, fresh_conn):
        migrate(fresh_conn)
        pragma = fresh_conn.execute("PRAGMA table_info(reports)").fetchall()
        col_names = {row[1] for row in pragma}
        assert "report_id" in col_names
        assert "data_json" in col_names
        assert "profile_key" in col_names
        assert "status" in col_names

    def test_MIG15_indexes_present_after_migration(self, fresh_conn):
        migrate(fresh_conn)
        indexes = {
            row[1]
            for row in fresh_conn.execute(
                "SELECT * FROM sqlite_master WHERE type='index' AND tbl_name='reports'"
            ).fetchall()
        }
        assert "idx_reports_profile" in indexes
        assert "idx_reports_status" in indexes

    def test_MIG16_can_insert_and_query_after_migration(self, fresh_conn):
        """Sanity: the migrated schema accepts real data."""
        migrate(fresh_conn)
        fresh_conn.execute(
            """INSERT INTO reports
               (report_id, profile_key, status, appraiser_name, market_value,
                created_at, updated_at, data_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("r1", "legacy", "draft", "Test", 1_000_000.0,
             "2026-05-15T10:00:00", "2026-05-15T10:00:00", '{"k": 1}'),
        )
        fresh_conn.commit()
        row = fresh_conn.execute(
            "SELECT report_id FROM reports WHERE report_id='r1'"
        ).fetchone()
        assert row is not None
        assert row[0] == "r1"

    def test_MIG17_isolation_between_connections(self, tmp_path):
        """Two separate DB files are independent."""
        db_a = tmp_path / "a.db"
        db_b = tmp_path / "b.db"
        conn_a = sqlite3.connect(str(db_a))
        conn_b = sqlite3.connect(str(db_b))
        try:
            migrate(conn_a)
            assert current_version(conn_b) == 0
        finally:
            conn_a.close()
            conn_b.close()
