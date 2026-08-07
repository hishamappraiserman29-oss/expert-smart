"""Tests for core_engine/reports/db/schema.py — Wave 7c.1."""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_CORE))
_ORIG_CWD = os.getcwd()
try:
    os.chdir(str(_CORE))

    from reports.db.schema import (  # noqa: E402
        CREATE_TABLES_SQL,
        SCHEMA_VERSION,
        VALID_STATUSES,
    )
finally:
    os.chdir(_ORIG_CWD)


class TestSchemaConstants:
    def test_S01_schema_version_is_positive_int(self):
        assert isinstance(SCHEMA_VERSION, int)
        assert SCHEMA_VERSION >= 1

    def test_S02_schema_version_is_currently_one(self):
        assert SCHEMA_VERSION == 3

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


# ---------------------------------------------------------------------------
# Wave 4B2 — core_engine/database/schema.sql (mass_valuation_runs /
# property_predictions) provenance + ownership columns.
#
# This DDL is PostgreSQL-specific (uuid_generate_v4(), JSONB, `ADD COLUMN
# IF NOT EXISTS`) and cannot be executed against sqlite3 the way
# reports/db/schema.py is validated above. No live PostgreSQL instance is
# available in this local test environment, so per the Wave 4B2 fallback
# instruction this is a static structural check of the raw DDL text —
# the strongest deterministic check available here — not a substitute for
# executing the DDL against a real PostgreSQL database.
# ---------------------------------------------------------------------------

class TestMassValuationSchemaWave4B2:
    _SCHEMA_PATH = _CORE / "database" / "schema.sql"

    @staticmethod
    @pytest.fixture(scope="class")
    def schema_text():
        return TestMassValuationSchemaWave4B2._SCHEMA_PATH.read_text(encoding="utf-8")

    @staticmethod
    def _table_block(schema_text: str, table_name: str) -> str:
        import re
        match = re.search(
            rf"CREATE TABLE IF NOT EXISTS {re.escape(table_name)} \((.*?)\n\);",
            schema_text,
            re.DOTALL,
        )
        assert match, f"CREATE TABLE IF NOT EXISTS {table_name} block not found in schema.sql"
        return match.group(1)

    def test_S15_schema_sql_file_exists(self):
        assert self._SCHEMA_PATH.is_file()

    def test_S16_mass_valuation_runs_declares_provenance_columns(self, schema_text):
        block = self._table_block(schema_text, "mass_valuation_runs")
        assert "model_hash" in block
        assert "ood_backend" in block
        assert "currency" in block
        assert "created_by" in block

    def test_S17_mass_valuation_runs_currency_defaults_to_sar(self, schema_text):
        block = self._table_block(schema_text, "mass_valuation_runs")
        currency_line = next(
            line for line in block.splitlines() if line.strip().startswith("currency")
        )
        assert "NOT NULL" in currency_line
        assert "DEFAULT 'SAR'" in currency_line

    def test_S18_mass_valuation_runs_model_hash_is_char64(self, schema_text):
        block = self._table_block(schema_text, "mass_valuation_runs")
        hash_line = next(
            line for line in block.splitlines() if line.strip().startswith("model_hash")
        )
        assert "CHAR(64)" in hash_line

    def test_S19_mass_valuation_runs_has_idempotent_upgrade_path(self, schema_text):
        for col, coltype in (
            ("model_hash", "CHAR(64)"),
            ("ood_backend", "VARCHAR(20)"),
            ("currency", "VARCHAR(3)"),
        ):
            expected = (
                f"ALTER TABLE mass_valuation_runs ADD COLUMN IF NOT EXISTS "
                f"{col}"
            )
            assert any(
                line.strip().startswith(expected) for line in schema_text.splitlines()
            ), f"Missing idempotent ALTER TABLE ADD COLUMN IF NOT EXISTS for {col}"

    def test_S20_mass_valuation_runs_created_by_indexed(self, schema_text):
        assert any(
            line.strip().startswith("CREATE INDEX IF NOT EXISTS idx_mvr_created_by")
            and "ON mass_valuation_runs (created_by)" in line
            for line in schema_text.splitlines()
        ), (
            "created_by must be indexed — ownership-scoped queries filter on it "
            "for every admin caller on every request"
        )

    def test_S21_property_predictions_declares_provenance_columns(self, schema_text):
        block = self._table_block(schema_text, "property_predictions")
        assert "source_method" in block
        assert "ood_score" in block

    def test_S22_property_predictions_has_idempotent_upgrade_path(self, schema_text):
        for col in ("source_method", "ood_score"):
            expected = (
                f"ALTER TABLE property_predictions ADD COLUMN IF NOT EXISTS {col}"
            )
            assert any(
                line.strip().startswith(expected) for line in schema_text.splitlines()
            ), f"Missing idempotent ALTER TABLE ADD COLUMN IF NOT EXISTS for {col}"

    def test_S23_alter_table_statements_are_syntactically_paired(self, schema_text):
        """Every Wave 4B2 ALTER TABLE ADD COLUMN IF NOT EXISTS line ends with a semicolon."""
        alter_lines = [
            line.strip() for line in schema_text.splitlines()
            if line.strip().startswith("ALTER TABLE") and "ADD COLUMN IF NOT EXISTS" in line
        ]
        assert len(alter_lines) >= 5
        for line in alter_lines:
            assert line.endswith(";"), f"Malformed ALTER TABLE statement: {line!r}"
