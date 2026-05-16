"""Tests for core_engine/reports/db/schema.py — Wave 7c.1."""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_CORE))
os.chdir(str(_CORE))

from reports.db.schema import (  # noqa: E402
    CREATE_TABLES_SQL,
    SCHEMA_VERSION,
    VALID_STATUSES,
)


class TestSchemaConstants:
    def test_S01_schema_version_is_positive_int(self):
        assert isinstance(SCHEMA_VERSION, int)
        assert SCHEMA_VERSION >= 1

    def test_S02_schema_version_is_currently_one(self):
        assert SCHEMA_VERSION == 2

    def test_S03_create_tables_sql_is_nonempty_string(self):
        assert isinstance(CREATE_TABLES_SQL, str)
        assert len(CREATE_TABLES_SQL.strip()) > 0

    def test_S04_valid_statuses_contains_required_values(self):
        assert "draft" in VALID_STATUSES
        assert "final" in VALID_STATUSES
        assert "archived" in VALID_STATUSES

    def test_S05_valid_statuses_is_frozenset(self):
        assert isinstance(VALID_STATUSES, frozenset)


class TestDDLExecution:
    @pytest.fixture()
    def conn(self, tmp_path):
        db = tmp_path / "test.db"
        c = sqlite3.connect(str(db))
        yield c
        c.close()

    def test_S06_ddl_executes_without_error(self, conn):
        conn.executescript(CREATE_TABLES_SQL)

    def test_S07_reports_table_created(self, conn):
        conn.executescript(CREATE_TABLES_SQL)
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='reports'"
        ).fetchall()
        assert len(rows) == 1

    def test_S08_schema_version_table_created(self, conn):
        conn.executescript(CREATE_TABLES_SQL)
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        ).fetchall()
        assert len(rows) == 1

    def test_S09_reports_table_has_required_columns(self, conn):
        conn.executescript(CREATE_TABLES_SQL)
        pragma = conn.execute("PRAGMA table_info(reports)").fetchall()
        col_names = {row[1] for row in pragma}
        required = {
            "report_id", "profile_key", "status",
            "appraiser_name", "market_value",
            "created_at", "updated_at", "data_json",
        }
        assert required.issubset(col_names)

    def test_S10_report_id_is_primary_key(self, conn):
        conn.executescript(CREATE_TABLES_SQL)
        pragma = conn.execute("PRAGMA table_info(reports)").fetchall()
        pk_cols = [row[1] for row in pragma if row[5] == 1]  # col 5 = pk flag
        assert "report_id" in pk_cols

    def test_S11_indexes_created(self, conn):
        conn.executescript(CREATE_TABLES_SQL)
        indexes = {
            row[1]
            for row in conn.execute(
                "SELECT * FROM sqlite_master WHERE type='index' AND tbl_name='reports'"
            ).fetchall()
        }
        assert "idx_reports_profile" in indexes
        assert "idx_reports_status" in indexes
        assert "idx_reports_appraiser" in indexes
        assert "idx_reports_created" in indexes

    def test_S12_ddl_is_idempotent(self, conn):
        conn.executescript(CREATE_TABLES_SQL)
        conn.executescript(CREATE_TABLES_SQL)

    def test_S13_status_default_is_draft(self, conn):
        conn.executescript(CREATE_TABLES_SQL)
        pragma = conn.execute("PRAGMA table_info(reports)").fetchall()
        status_col = next(row for row in pragma if row[1] == "status")
        assert status_col[4] == "'draft'"  # column default value

    def test_S14_data_json_column_not_null(self, conn):
        conn.executescript(CREATE_TABLES_SQL)
        pragma = conn.execute("PRAGMA table_info(reports)").fetchall()
        data_col = next(row for row in pragma if row[1] == "data_json")
        assert data_col[3] == 1  # notnull flag
