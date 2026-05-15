"""Tests for core_engine/reports/db/repository.py — Wave 7c.2."""

from __future__ import annotations

import os
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_CORE))
os.chdir(str(_CORE))

from reports.db.migrations import migrate  # noqa: E402
from reports.db.models import ReportRecord  # noqa: E402
from reports.db.repository import ReportRepository  # noqa: E402


@pytest.fixture()
def repo(tmp_path):
    """A ReportRepository over a fresh, migrated, temp DB."""
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    migrate(conn)
    yield ReportRepository(conn)
    conn.close()


@pytest.fixture()
def sample_data():
    return {
        "appraiser": {"name": "د. عبد الرؤوف محمد", "license": "EG-2026-00471"},
        "property_info": {"address": "القاهرة الجديدة", "area": 320},
        "valuation_results": {"market_value": 2_478_153.5, "confidence": "عالية"},
        "comparables": [{"ref": "ع1", "price": 2_400_000},
                        {"ref": "ع2", "price": 2_600_000}],
        "notes": None,
    }


# ── Create + Read ────────────────────────────────────────────────────

class TestSaveAndGet:
    def test_R01_save_returns_report_id(self, repo, sample_data):
        rid = repo.save(profile_key="legacy", data=sample_data)
        assert isinstance(rid, str) and len(rid) > 0

    def test_R02_save_then_get_round_trip(self, repo, sample_data):
        rid = repo.save(profile_key="legacy", data=sample_data)
        rec = repo.get(rid)
        assert rec is not None
        assert isinstance(rec, ReportRecord)
        assert rec.report_id == rid
        assert rec.profile_key == "legacy"
        assert rec.status == "draft"
        assert rec.data == sample_data

    def test_R03_round_trip_fidelity_complex(self, repo):
        """Nested dicts, Arabic, floats, lists, None, bool all survive."""
        data = {
            "ar": "تقرير التقييم العقاري",
            "nested": {"deep": {"deeper": [1, 2.5, "ثلاثة", None]}},
            "float": 2_478_153.99,
            "list": ["a", "ب", 3],
            "none": None,
            "bool": True,
        }
        rid = repo.save(profile_key="detailed", data=data)
        assert repo.get(rid).data == data

    def test_R04_get_missing_returns_none(self, repo):
        assert repo.get("nonexistent-id") is None

    def test_R05_caller_provided_report_id(self, repo, sample_data):
        rid = repo.save(profile_key="legacy", data=sample_data,
                        report_id="custom-001")
        assert rid == "custom-001"
        assert repo.get("custom-001") is not None

    def test_R06_duplicate_report_id_raises(self, repo, sample_data):
        repo.save(profile_key="legacy", data=sample_data, report_id="dup")
        with pytest.raises(sqlite3.IntegrityError):
            repo.save(profile_key="legacy", data=sample_data, report_id="dup")

    def test_R07_indexed_fields_extracted(self, repo, sample_data):
        rid = repo.save(profile_key="legacy", data=sample_data)
        rec = repo.get(rid)
        assert rec.appraiser_name == "د. عبد الرؤوف محمد"
        assert rec.market_value == pytest.approx(2_478_153.5)

    def test_R08_indexed_fields_missing_are_none(self, repo):
        rid = repo.save(profile_key="legacy", data={"x": 1})
        rec = repo.get(rid)
        assert rec.appraiser_name is None
        assert rec.market_value is None

    def test_R09_auto_generated_uuid_is_unique(self, repo, sample_data):
        r1 = repo.save(profile_key="legacy", data=sample_data)
        r2 = repo.save(profile_key="legacy", data=sample_data)
        assert r1 != r2


# ── JSON guard (modification #3) ────────────────────────────────────

class TestJsonGuard:
    def test_R10_non_serializable_data_raises_typeerror(self, repo):
        with pytest.raises(TypeError, match="not JSON-serializable"):
            repo.save(profile_key="legacy",
                      data={"bad": datetime(2026, 5, 15)})

    def test_R11_non_serializable_in_update_raises(self, repo, sample_data):
        rid = repo.save(profile_key="legacy", data=sample_data)
        with pytest.raises(TypeError, match="not JSON-serializable"):
            repo.update(rid, data={"bad": datetime(2026, 5, 15)})


# ── Status validation ────────────────────────────────────────────────

class TestStatusValidation:
    def test_R12_invalid_status_on_save_raises(self, repo, sample_data):
        with pytest.raises(ValueError, match="Invalid status"):
            repo.save(profile_key="legacy", data=sample_data, status="bogus")

    def test_R13_valid_statuses_accepted(self, repo, sample_data):
        for st in ("draft", "final", "archived"):
            rid = repo.save(profile_key="legacy", data=sample_data, status=st)
            assert repo.get(rid).status == st

    def test_R14_invalid_status_on_update_raises(self, repo, sample_data):
        rid = repo.save(profile_key="legacy", data=sample_data)
        with pytest.raises(ValueError, match="Invalid status"):
            repo.update(rid, status="bogus")


# ── Timestamps (modification #4) ────────────────────────────────────

class TestTimestamps:
    def test_R15_created_equals_updated_on_save(self, repo, sample_data):
        rid = repo.save(profile_key="legacy", data=sample_data)
        rec = repo.get(rid)
        assert rec.created_at == rec.updated_at

    def test_R16_timestamps_are_utc_iso_8601(self, repo, sample_data):
        rid = repo.save(profile_key="legacy", data=sample_data)
        rec = repo.get(rid)
        # ISO 8601 with timezone offset — parseable by datetime.fromisoformat
        dt = datetime.fromisoformat(rec.created_at)
        assert dt.tzinfo is not None  # timezone-aware

    def test_R17_update_advances_only_updated_at(self, repo, sample_data):
        rid = repo.save(profile_key="legacy", data=sample_data)
        before = repo.get(rid)
        time.sleep(0.02)
        repo.update(rid, status="final")
        after = repo.get(rid)
        assert after.created_at == before.created_at   # preserved
        assert after.updated_at > before.updated_at    # advanced


# ── Update ───────────────────────────────────────────────────────────

class TestUpdate:
    def test_R18_update_status(self, repo, sample_data):
        rid = repo.save(profile_key="legacy", data=sample_data)
        assert repo.update(rid, status="final") is True
        assert repo.get(rid).status == "final"

    def test_R19_update_data_reextracts_index_fields(self, repo, sample_data):
        rid = repo.save(profile_key="legacy", data=sample_data)
        new_data = {"appraiser": {"name": "م. أحمد"},
                    "valuation_results": {"market_value": 3_000_000}}
        repo.update(rid, data=new_data)
        rec = repo.get(rid)
        assert rec.data == new_data
        assert rec.appraiser_name == "م. أحمد"
        assert rec.market_value == pytest.approx(3_000_000)

    def test_R20_update_missing_id_returns_false(self, repo):
        assert repo.update("nonexistent", status="final") is False

    def test_R21_update_nothing_returns_false(self, repo, sample_data):
        rid = repo.save(profile_key="legacy", data=sample_data)
        assert repo.update(rid) is False

    def test_R22_update_data_only(self, repo, sample_data):
        rid = repo.save(profile_key="legacy", data=sample_data)
        new_data = {"x": 42}
        assert repo.update(rid, data=new_data) is True
        assert repo.get(rid).data == new_data
        assert repo.get(rid).status == "draft"  # unchanged

    def test_R23_update_status_only(self, repo, sample_data):
        rid = repo.save(profile_key="legacy", data=sample_data)
        assert repo.update(rid, status="archived") is True
        rec = repo.get(rid)
        assert rec.status == "archived"
        assert rec.data == sample_data  # unchanged


# ── List + Count ─────────────────────────────────────────────────────

class TestListAndCount:
    def _seed(self, repo, sample_data):
        repo.save(profile_key="legacy", data=sample_data, status="draft")
        repo.save(profile_key="legacy", data=sample_data, status="final")
        repo.save(profile_key="professional", data=sample_data, status="draft")

    def test_R24_list_all(self, repo, sample_data):
        self._seed(repo, sample_data)
        assert len(repo.list()) == 3

    def test_R25_list_filter_by_profile(self, repo, sample_data):
        self._seed(repo, sample_data)
        assert len(repo.list(profile_key="legacy")) == 2
        assert len(repo.list(profile_key="professional")) == 1

    def test_R26_list_filter_by_status(self, repo, sample_data):
        self._seed(repo, sample_data)
        assert len(repo.list(status="draft")) == 2
        assert len(repo.list(status="final")) == 1

    def test_R27_list_filter_combined(self, repo, sample_data):
        self._seed(repo, sample_data)
        assert len(repo.list(profile_key="legacy", status="draft")) == 1

    def test_R28_list_pagination(self, repo, sample_data):
        self._seed(repo, sample_data)
        page1 = repo.list(limit=2, offset=0)
        page2 = repo.list(limit=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 1

    def test_R29_list_empty_db(self, repo):
        assert repo.list() == []

    def test_R30_list_unknown_profile_returns_empty(self, repo, sample_data):
        self._seed(repo, sample_data)
        assert repo.list(profile_key="nonexistent") == []

    def test_R31_count(self, repo, sample_data):
        self._seed(repo, sample_data)
        assert repo.count() == 3
        assert repo.count(profile_key="legacy") == 2
        assert repo.count(status="final") == 1
        assert repo.count(profile_key="professional", status="final") == 0

    def test_R32_count_empty_db(self, repo):
        assert repo.count() == 0

    def test_R33_list_returns_report_records(self, repo, sample_data):
        self._seed(repo, sample_data)
        records = repo.list()
        assert all(isinstance(r, ReportRecord) for r in records)


# ── Delete ───────────────────────────────────────────────────────────

class TestDelete:
    def test_R34_delete_existing(self, repo, sample_data):
        rid = repo.save(profile_key="legacy", data=sample_data)
        assert repo.delete(rid) is True
        assert repo.get(rid) is None

    def test_R35_delete_missing_returns_false(self, repo):
        assert repo.delete("nonexistent") is False

    def test_R36_delete_reduces_count(self, repo, sample_data):
        r1 = repo.save(profile_key="legacy", data=sample_data)
        repo.save(profile_key="legacy", data=sample_data)
        assert repo.count() == 2
        repo.delete(r1)
        assert repo.count() == 1


# ── Isolation ────────────────────────────────────────────────────────

class TestIsolation:
    def test_R37_two_dbs_are_independent(self, tmp_path, sample_data):
        conn_a = sqlite3.connect(str(tmp_path / "a.db"))
        conn_b = sqlite3.connect(str(tmp_path / "b.db"))
        migrate(conn_a)
        migrate(conn_b)
        repo_a = ReportRepository(conn_a)
        repo_b = ReportRepository(conn_b)
        repo_a.save(profile_key="legacy", data=sample_data)
        assert repo_a.count() == 1
        assert repo_b.count() == 0
        conn_a.close()
        conn_b.close()
