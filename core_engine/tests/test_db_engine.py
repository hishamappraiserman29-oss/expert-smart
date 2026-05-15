"""Integration tests for reports.db public API (db_engine) — Wave 7c.3."""

from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_CORE))
os.chdir(str(_CORE))

from reports.db import (  # noqa: E402
    ReportRecord,
    count_reports,
    delete_report,
    get_report,
    list_reports,
    save_report,
    update_report,
)


@pytest.fixture()
def db(tmp_path):
    """A temp DB path — never the DEFAULT_DB_PATH."""
    return tmp_path / "engine_test.db"


@pytest.fixture()
def sample_data():
    return {
        "appraiser": {"name": "د. عبد الرؤوف محمد"},
        "valuation_results": {"market_value": 2_478_153.0},
        "property_info": {"address": "القاهرة الجديدة"},
        "notes": None,
    }


# ── Auto connection management (modification #5) ─────────────────────

class TestConnectionManagement:
    def test_E01_save_auto_creates_db_and_parent_dir(self, tmp_path, sample_data):
        db = tmp_path / "nested" / "deep" / "reports.db"
        rid = save_report(sample_data, profile_key="legacy", db_path=db)
        assert db.exists()
        assert get_report(rid, db_path=db) is not None

    def test_E02_no_lingering_connection_lock(self, db, sample_data):
        """After save, further ops on the same file must succeed (conn closed)."""
        save_report(sample_data, profile_key="legacy", db_path=db)
        rid2 = save_report(sample_data, profile_key="detailed", db_path=db)
        assert get_report(rid2, db_path=db) is not None

    def test_E03_migrate_runs_automatically(self, db, sample_data):
        """First call on a fresh path must auto-migrate (no manual setup)."""
        rid = save_report(sample_data, profile_key="legacy", db_path=db)
        assert get_report(rid, db_path=db) is not None


# ── Full CRUD via public API ──────────────────────────────────────────

class TestPublicCrud:
    def test_E04_save_get_round_trip(self, db, sample_data):
        rid = save_report(sample_data, profile_key="legacy", db_path=db)
        rec = get_report(rid, db_path=db)
        assert isinstance(rec, ReportRecord)
        assert rec.data == sample_data
        assert rec.profile_key == "legacy"
        assert rec.status == "draft"

    def test_E05_get_missing_returns_none(self, db):
        assert get_report("nonexistent", db_path=db) is None

    def test_E06_update_status(self, db, sample_data):
        rid = save_report(sample_data, profile_key="legacy", db_path=db)
        assert update_report(rid, status="final", db_path=db) is True
        assert get_report(rid, db_path=db).status == "final"

    def test_E07_update_missing_returns_false(self, db):
        assert update_report("nonexistent", status="final", db_path=db) is False

    def test_E08_delete(self, db, sample_data):
        rid = save_report(sample_data, profile_key="legacy", db_path=db)
        assert delete_report(rid, db_path=db) is True
        assert get_report(rid, db_path=db) is None

    def test_E09_delete_missing_returns_false(self, db):
        assert delete_report("nonexistent", db_path=db) is False

    def test_E10_list_and_count(self, db, sample_data):
        save_report(sample_data, profile_key="legacy", db_path=db)
        save_report(sample_data, profile_key="legacy",
                    status="final", db_path=db)
        save_report(sample_data, profile_key="professional", db_path=db)

        assert count_reports(db_path=db) == 3
        assert count_reports(profile_key="legacy", db_path=db) == 2
        assert len(list_reports(status="final", db_path=db)) == 1
        assert len(list_reports(db_path=db)) == 3

    def test_E11_caller_provided_report_id(self, db, sample_data):
        rid = save_report(sample_data, profile_key="legacy",
                          report_id="custom-99", db_path=db)
        assert rid == "custom-99"
        assert get_report("custom-99", db_path=db) is not None

    def test_E12_list_returns_report_records(self, db, sample_data):
        save_report(sample_data, profile_key="legacy", db_path=db)
        records = list_reports(db_path=db)
        assert all(isinstance(r, ReportRecord) for r in records)

    def test_E13_count_empty_db(self, db):
        assert count_reports(db_path=db) == 0

    def test_E14_list_empty_db(self, db):
        assert list_reports(db_path=db) == []


# ── Error propagation ─────────────────────────────────────────────────

class TestErrorPropagation:
    def test_E15_invalid_status_raises(self, db, sample_data):
        with pytest.raises(ValueError, match="Invalid status"):
            save_report(sample_data, profile_key="legacy",
                        status="bogus", db_path=db)

    def test_E16_non_serializable_raises(self, db):
        with pytest.raises(TypeError, match="not JSON-serializable"):
            save_report({"bad": datetime(2026, 5, 15)},
                        profile_key="legacy", db_path=db)

    def test_E17_duplicate_id_raises(self, db, sample_data):
        save_report(sample_data, profile_key="legacy",
                    report_id="dup", db_path=db)
        with pytest.raises(sqlite3.IntegrityError):
            save_report(sample_data, profile_key="legacy",
                        report_id="dup", db_path=db)


# ── Isolation ─────────────────────────────────────────────────────────

class TestIsolation:
    def test_E18_two_db_paths_independent(self, tmp_path, sample_data):
        db_a = tmp_path / "a.db"
        db_b = tmp_path / "b.db"
        save_report(sample_data, profile_key="legacy", db_path=db_a)
        assert count_reports(db_path=db_a) == 1
        assert count_reports(db_path=db_b) == 0
