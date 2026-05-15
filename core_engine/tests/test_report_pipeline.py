"""
Unit tests for reports.report_pipeline (Wave BA.1 + BA.2 + BA.3 + BA.4a).

Verifies:
  - _build_engine_dto: correct field mapping from flat dict to nested DTO
  - PipelineResult: dataclass contract (frozen, required fields, defaults)
  - run_report_pipeline: all three opt-in steps (validate / pdf / persist)
  - run_report_pipeline: default (all off) returns a valid empty result
  - run_report_pipeline: report_id forwarded to save_report
  - validate_report_data: thin wrapper (validation only, BA.2)
  - persist_report_data: thin wrapper (persistence only, BA.3)
  - fetch_reports: history list facade (BA.4a)
  - fetch_report: history single facade (BA.4a)

Tests: PL01–PL36
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(str(_CORE))

from reports.report_pipeline import (  # noqa: E402
    PipelineResult,
    _build_engine_dto,
    fetch_report,
    fetch_reports,
    persist_report_data,
    run_report_pipeline,
    validate_report_data,
)


# ── Sample flat dict (bridge_api "full" shape) ────────────────────────────────

_FULL: dict = {
    "report_id":       "ES-20260515-ABCD",
    "expert":          "م. هشام المهدي",
    "location":        "القاهرة الجديدة",
    "area":            200,
    "property_type":   "شقة سكنية",
    "price_per_meter": 10_000,
    "market_value":    2_000_000.0,
    "confidence":      "عالية",
    "report_date":     "15/05/2026",
}

_FULL_WITH_COMPS: dict = {
    **_FULL,
    "comp_sales": [
        {"sale_price": 1_900_000, "area": 190},
        {"sale_price": 2_100_000, "area": 210},
    ],
    "cost_approach":  {"rcn": 1_500_000, "land_value": 600_000},
    "income_approach": {"gross_income": 180_000, "cap_rate": 6.0},
    "reconciliation": {"final_value": 2_000_000},
}


# ── _build_engine_dto ─────────────────────────────────────────────────────────

class TestBuildEngineDto:
    def test_PL01_appraiser_name_from_expert(self):
        dto = _build_engine_dto(_FULL)
        assert dto["appraiser"]["name"] == "م. هشام المهدي"

    def test_PL02_property_info_address_from_location(self):
        dto = _build_engine_dto(_FULL)
        assert dto["property_info"]["address"] == "القاهرة الجديدة"

    def test_PL03_property_info_area_is_float(self):
        dto = _build_engine_dto(_FULL)
        assert dto["property_info"]["area"] == 200.0
        assert isinstance(dto["property_info"]["area"], float)

    def test_PL04_property_info_type_from_property_type(self):
        dto = _build_engine_dto(_FULL)
        assert dto["property_info"]["type"] == "شقة سكنية"

    def test_PL05_market_value_is_float(self):
        dto = _build_engine_dto(_FULL)
        assert dto["valuation_results"]["market_value"] == 2_000_000.0

    def test_PL06_price_per_sqm_from_price_per_meter(self):
        dto = _build_engine_dto(_FULL)
        assert dto["valuation_results"]["price_per_sqm"] == 10_000.0

    def test_PL07_subject_mirrors_property_info(self):
        dto = _build_engine_dto(_FULL)
        assert dto["subject"]["address"] == dto["property_info"]["address"]
        assert dto["subject"]["area"]    == dto["property_info"]["area"]
        assert dto["subject"]["type"]    == dto["property_info"]["type"]

    def test_PL08_comparables_from_comp_sales(self):
        dto = _build_engine_dto(_FULL_WITH_COMPS)
        assert len(dto["comparables"]) == 2
        assert dto["comparables"][0]["sale_price"] == 1_900_000

    def test_PL09_cost_approach_passed_through(self):
        dto = _build_engine_dto(_FULL_WITH_COMPS)
        assert dto["cost_approach"]["rcn"] == 1_500_000

    def test_PL10_income_approach_passed_through(self):
        dto = _build_engine_dto(_FULL_WITH_COMPS)
        assert dto["income_approach"]["cap_rate"] == 6.0

    def test_PL11_empty_dict_produces_safe_defaults(self):
        dto = _build_engine_dto({})
        assert dto["appraiser"]["name"] == ""
        assert dto["property_info"]["area"] is None
        assert dto["valuation_results"]["market_value"] is None
        assert dto["comparables"] == []

    def test_PL12_reconciliation_passed_through(self):
        dto = _build_engine_dto(_FULL_WITH_COMPS)
        assert dto["reconciliation"]["final_value"] == 2_000_000


# ── PipelineResult dataclass ──────────────────────────────────────────────────

class TestPipelineResult:
    def test_PL13_is_frozen(self):
        r = PipelineResult(is_valid=True, errors=(), warnings=())
        with pytest.raises((AttributeError, TypeError)):
            r.is_valid = False  # type: ignore[misc]

    def test_PL14_defaults_are_none(self):
        r = PipelineResult(is_valid=True, errors=(), warnings=())
        assert r.report_db_id is None
        assert r.pdf_path is None
        assert r.validation_result is None

    def test_PL15_stores_errors_and_warnings(self):
        fake = MagicMock()
        r = PipelineResult(is_valid=False, errors=(fake,), warnings=())
        assert r.errors == (fake,)
        assert not r.is_valid


# ── run_report_pipeline — default (all off) ───────────────────────────────────

class TestRunPipelineDefaults:
    def test_PL16_default_returns_valid_result(self):
        result = run_report_pipeline(_FULL)
        assert isinstance(result, PipelineResult)
        assert result.is_valid is True
        assert result.errors == ()
        assert result.warnings == ()
        assert result.report_db_id is None
        assert result.pdf_path is None
        assert result.validation_result is None


# ── run_report_pipeline — opt-in steps ───────────────────────────────────────

class TestRunPipelineOptIn:
    def test_PL17_validate_step_calls_validate_report(self):
        fake_result = MagicMock()
        fake_result.is_valid = True
        fake_result.errors   = []
        fake_result.warnings = []
        with patch("reports.report_pipeline._val_report",
                   return_value=fake_result) as mock_val:
            result = run_report_pipeline(_FULL, validate=True)
        mock_val.assert_called_once()
        assert result.validation_result is fake_result
        assert result.is_valid is True

    def test_PL18_validate_false_skips_validate_report(self):
        with patch("reports.report_pipeline._val_report") as mock_val:
            run_report_pipeline(_FULL, validate=False)
        mock_val.assert_not_called()

    def test_PL19_generate_pdf_calls_pdf_generate(self, tmp_path):
        pdf_out = tmp_path / "test.pdf"
        with patch("reports.report_pipeline._pdf_generate",
                   return_value=pdf_out) as mock_pdf:
            result = run_report_pipeline(
                _FULL, generate_pdf=True, pdf_output_path=pdf_out,
            )
        mock_pdf.assert_called_once()
        assert result.pdf_path == pdf_out

    def test_PL20_generate_pdf_false_skips_pdf_generate(self, tmp_path):
        with patch("reports.report_pipeline._pdf_generate") as mock_pdf:
            run_report_pipeline(_FULL, generate_pdf=False)
        mock_pdf.assert_not_called()

    def test_PL21_persist_calls_save_report(self, tmp_path):
        db = tmp_path / "pl_test.db"
        with patch("reports.report_pipeline._db_save",
                   return_value="saved-id-123") as mock_save:
            result = run_report_pipeline(_FULL, persist=True, db_path=db)
        mock_save.assert_called_once()
        assert result.report_db_id == "saved-id-123"

    def test_PL22_persist_forwards_report_id_from_full(self, tmp_path):
        db = tmp_path / "pl_fwd.db"
        with patch("reports.report_pipeline._db_save",
                   return_value="ES-20260515-ABCD") as mock_save:
            run_report_pipeline(_FULL, persist=True, db_path=db)
        _call_kwargs = mock_save.call_args.kwargs
        assert _call_kwargs.get("report_id") == "ES-20260515-ABCD"


# ── validate_report_data — BA.2 thin wrapper ─────────────────────────────────

class TestValidateReportData:
    def test_PL23_returns_pipeline_result(self):
        fake = MagicMock()
        fake.is_valid = True
        fake.errors   = []
        fake.warnings = []
        with patch("reports.report_pipeline._val_report", return_value=fake):
            result = validate_report_data(_FULL)
        assert isinstance(result, PipelineResult)

    def test_PL24_valid_data_is_valid_true(self):
        fake = MagicMock()
        fake.is_valid = True
        fake.errors   = []
        fake.warnings = []
        with patch("reports.report_pipeline._val_report", return_value=fake):
            result = validate_report_data(_FULL, profile_key="legacy")
        assert result.is_valid is True
        assert result.errors == ()

    def test_PL25_invalid_data_is_valid_false(self):
        fake = MagicMock()
        fake.is_valid = False
        fake.errors   = [MagicMock()]
        fake.warnings = []
        with patch("reports.report_pipeline._val_report", return_value=fake):
            result = validate_report_data(_FULL, profile_key="legacy")
        assert result.is_valid is False
        assert len(result.errors) == 1


# ── persist_report_data — BA.3 thin wrapper ──────────────────────────────────

class TestPersistReportData:
    def test_PL26_returns_string_report_id(self, tmp_path):
        db = tmp_path / "pl26.db"
        with patch("reports.report_pipeline._db_save",
                   return_value="pl26-id-001") as mock_save:
            result = persist_report_data(_FULL, db_path=db)
        mock_save.assert_called_once()
        assert isinstance(result, str)
        assert result == "pl26-id-001"

    def test_PL27_forwards_profile_key_and_status(self, tmp_path):
        db = tmp_path / "pl27.db"
        with patch("reports.report_pipeline._db_save",
                   return_value="pl27-id") as mock_save:
            persist_report_data(
                _FULL, profile_key="detailed", status="final", db_path=db,
            )
        kw = mock_save.call_args.kwargs
        assert kw.get("profile_key") == "detailed"
        assert kw.get("status") == "final"

    def test_PL28_report_id_from_full_forwarded(self, tmp_path):
        db = tmp_path / "pl28.db"
        with patch("reports.report_pipeline._db_save",
                   return_value="ES-20260515-ABCD") as mock_save:
            result = persist_report_data(_FULL, db_path=db)
        kw = mock_save.call_args.kwargs
        assert kw.get("report_id") == "ES-20260515-ABCD"
        assert result == "ES-20260515-ABCD"


# ── fetch_reports — BA.4a history list facade ─────────────────────────────────

class _FakeRecord:
    """Minimal stub for ReportRecord returned by _db_list."""
    def __init__(self, rid, profile, status, mv, data):
        self.report_id   = rid
        self.profile_key = profile
        self.status      = status
        self.market_value = mv
        self.data        = data


_RECORD_1 = _FakeRecord(
    "ES-20260515-ABCD", "legacy", "draft", 2_000_000.0,
    {
        "appraiser":     {"name": "م. هشام المهدي", "date": "15/05/2026"},
        "property_info": {"address": "القاهرة الجديدة", "type": "شقة سكنية", "area": 200.0},
    },
)
_RECORD_2 = _FakeRecord(
    "ES-20260515-XYZ1", "detailed", "final", 5_000_000.0,
    {
        "appraiser":     {"name": "م. هشام المهدي", "date": "15/05/2026"},
        "property_info": {"address": "الشيخ زايد", "type": "فيلا", "area": 400.0},
    },
)


class TestFetchReports:
    def test_PL29_returns_dict_with_count_and_reports(self, tmp_path):
        db = tmp_path / "pl29.db"
        with (
            patch("reports.report_pipeline._db_list", return_value=[_RECORD_1]),
            patch("reports.report_pipeline._db_count", return_value=1),
        ):
            result = fetch_reports(db_path=db)
        assert isinstance(result, dict)
        assert "count" in result
        assert "reports" in result

    def test_PL30_calls_db_list_and_db_count(self, tmp_path):
        db = tmp_path / "pl30.db"
        with (
            patch("reports.report_pipeline._db_list",
                  return_value=[_RECORD_1]) as mock_list,
            patch("reports.report_pipeline._db_count",
                  return_value=1) as mock_count,
        ):
            fetch_reports(db_path=db)
        mock_list.assert_called_once()
        mock_count.assert_called_once()

    def test_PL31_profile_key_filter_forwarded(self, tmp_path):
        db = tmp_path / "pl31.db"
        with (
            patch("reports.report_pipeline._db_list", return_value=[]) as mock_list,
            patch("reports.report_pipeline._db_count", return_value=0),
        ):
            fetch_reports(profile_key="detailed", db_path=db)
        kw = mock_list.call_args.kwargs
        assert kw.get("profile_key") == "detailed"

    def test_PL32_status_filter_forwarded(self, tmp_path):
        db = tmp_path / "pl32.db"
        with (
            patch("reports.report_pipeline._db_list", return_value=[]) as mock_list,
            patch("reports.report_pipeline._db_count", return_value=0),
        ):
            fetch_reports(status="final", db_path=db)
        kw = mock_list.call_args.kwargs
        assert kw.get("status") == "final"

    def test_PL32b_summary_shape_correct(self, tmp_path):
        db = tmp_path / "pl32b.db"
        with (
            patch("reports.report_pipeline._db_list",
                  return_value=[_RECORD_1, _RECORD_2]),
            patch("reports.report_pipeline._db_count", return_value=2),
        ):
            result = fetch_reports(db_path=db)
        assert result["count"] == 2
        s = result["reports"][0]
        assert s["report_db_id"]  == "ES-20260515-ABCD"
        assert s["property_type"] == "شقة سكنية"
        assert s["location"]      == "القاهرة الجديدة"
        assert s["market_value"]  == 2_000_000.0
        assert s["status"]        == "draft"
        assert s["profile_key"]   == "legacy"


# ── fetch_report — BA.4a history single facade ───────────────────────────────

class _FakeFullRecord:
    """Stub for a single ReportRecord with all fields."""
    report_id    = "ES-20260515-ABCD"
    profile_key  = "legacy"
    status       = "draft"
    created_at   = "2026-05-15T10:00:00+00:00"
    updated_at   = "2026-05-15T10:00:00+00:00"
    data         = {"appraiser": {"name": "م. هشام المهدي"}}


class TestFetchReport:
    def test_PL33_returns_none_when_not_found(self, tmp_path):
        db = tmp_path / "pl33.db"
        with patch("reports.report_pipeline._db_get", return_value=None):
            result = fetch_report("MISSING-ID", db_path=db)
        assert result is None

    def test_PL34_returns_dict_when_found(self, tmp_path):
        db = tmp_path / "pl34.db"
        with patch("reports.report_pipeline._db_get",
                   return_value=_FakeFullRecord()):
            result = fetch_report("ES-20260515-ABCD", db_path=db)
        assert isinstance(result, dict)

    def test_PL35_result_has_required_keys(self, tmp_path):
        db = tmp_path / "pl35.db"
        with patch("reports.report_pipeline._db_get",
                   return_value=_FakeFullRecord()):
            result = fetch_report("ES-20260515-ABCD", db_path=db)
        for key in ("report_db_id", "profile_key", "status",
                    "created_at", "updated_at", "data"):
            assert key in result, f"Missing key: {key!r}"

    def test_PL36_result_values_match_record(self, tmp_path):
        db = tmp_path / "pl36.db"
        with patch("reports.report_pipeline._db_get",
                   return_value=_FakeFullRecord()):
            result = fetch_report("ES-20260515-ABCD", db_path=db)
        assert result["report_db_id"] == "ES-20260515-ABCD"
        assert result["profile_key"]  == "legacy"
        assert result["status"]       == "draft"
        assert result["data"]         == {"appraiser": {"name": "م. هشام المهدي"}}
