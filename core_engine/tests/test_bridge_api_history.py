"""
Integration tests for the Bridge API history endpoints (Wave BA.4a).

Endpoints under test:
  GET /api/reports            — list persisted reports (summary)
  GET /api/reports/<id>       — single report (full DTO)

Policies:
  - No application-level auth gate (infrastructure auth assumed — documented
    in bridge_api.py comments and here for traceability).
  - DB exceptions → 500 with {"status":"error","message":"<detail>"}.
  - Missing ID → 404 with {"status":"not_found","message":"Report <id> not found"}.
  - Filters (profile_key, status) and pagination (limit, offset) forwarded.
  - No production DB file created — all tests mock the pipeline facades.

Tests: HI01–HI15
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(str(_CORE))

from bridge_api import app  # noqa: E402

# ── Shared stubs ──────────────────────────────────────────────────────────────

_SUMMARY_1 = {
    "report_db_id":  "ES-20260515-AAA1",
    "property_type": "شقة سكنية",
    "location":      "القاهرة الجديدة",
    "market_value":  2_000_000.0,
    "report_date":   "15/05/2026",
    "status":        "draft",
    "profile_key":   "legacy",
}
_SUMMARY_2 = {
    "report_db_id":  "ES-20260515-AAA2",
    "property_type": "فيلا",
    "location":      "الشيخ زايد",
    "market_value":  5_000_000.0,
    "report_date":   "15/05/2026",
    "status":        "final",
    "profile_key":   "detailed",
}

_LIST_RESULT   = {"count": 2, "reports": [_SUMMARY_1, _SUMMARY_2]}
_EMPTY_RESULT  = {"count": 0, "reports": []}

_FULL_RECORD = {
    "report_db_id": "ES-20260515-AAA1",
    "profile_key":  "legacy",
    "status":       "draft",
    "created_at":   "2026-05-15T10:00:00+00:00",
    "updated_at":   "2026-05-15T10:00:00+00:00",
    "data": {
        "appraiser":         {"name": "م. هشام المهدي", "date": "15/05/2026"},
        "property_info":     {"address": "القاهرة الجديدة", "type": "شقة سكنية", "area": 200.0},
        "valuation_results": {"market_value": 2_000_000.0},
    },
}

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture()
def auth_header(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-s3-history")
    from auth.tokens import generate_token
    return lambda user_id="test-user": {"Authorization": f"Bearer {generate_token(user_id)}"}


# ── HI01–HI04: GET /api/reports baseline ─────────────────────────────────────

class TestReportsList:
    def test_HI01_returns_200(self, client, auth_header):
        with patch("reports.report_pipeline.fetch_reports",
                   return_value=_LIST_RESULT):
            r = client.get("/api/reports", headers=auth_header())
        assert r.status_code == 200

    def test_HI02_status_is_success(self, client, auth_header):
        with patch("reports.report_pipeline.fetch_reports",
                   return_value=_LIST_RESULT):
            data = client.get("/api/reports", headers=auth_header()).get_json()
        assert data["status"] == "success"

    def test_HI03_response_has_count(self, client, auth_header):
        with patch("reports.report_pipeline.fetch_reports",
                   return_value=_LIST_RESULT):
            data = client.get("/api/reports", headers=auth_header()).get_json()
        assert "count" in data
        assert data["count"] == 2

    def test_HI04_response_has_reports_list(self, client, auth_header):
        with patch("reports.report_pipeline.fetch_reports",
                   return_value=_LIST_RESULT):
            data = client.get("/api/reports", headers=auth_header()).get_json()
        assert isinstance(data["reports"], list)
        assert len(data["reports"]) == 2


# ── HI05–HI06: Pagination forwarding ─────────────────────────────────────────

class TestPagination:
    def test_HI05_limit_param_forwarded(self, client, auth_header):
        with patch("reports.report_pipeline.fetch_reports",
                   return_value=_EMPTY_RESULT) as mock_fr:
            client.get("/api/reports?limit=5", headers=auth_header())
        kw = mock_fr.call_args.kwargs
        assert kw.get("limit") == 5

    def test_HI06_offset_param_forwarded(self, client, auth_header):
        with patch("reports.report_pipeline.fetch_reports",
                   return_value=_EMPTY_RESULT) as mock_fr:
            client.get("/api/reports?offset=10", headers=auth_header())
        kw = mock_fr.call_args.kwargs
        assert kw.get("offset") == 10

    def test_HI06b_limit_capped_at_100(self, client, auth_header):
        with patch("reports.report_pipeline.fetch_reports",
                   return_value=_EMPTY_RESULT) as mock_fr:
            client.get("/api/reports?limit=999", headers=auth_header())
        kw = mock_fr.call_args.kwargs
        assert kw.get("limit") == 100

    def test_HI06c_invalid_limit_defaults_to_20(self, client, auth_header):
        with patch("reports.report_pipeline.fetch_reports",
                   return_value=_EMPTY_RESULT) as mock_fr:
            client.get("/api/reports?limit=notanint", headers=auth_header())
        kw = mock_fr.call_args.kwargs
        assert kw.get("limit") == 20


# ── HI07–HI08: Filter forwarding ─────────────────────────────────────────────

class TestFilters:
    def test_HI07_profile_key_filter_forwarded(self, client, auth_header):
        with patch("reports.report_pipeline.fetch_reports",
                   return_value=_EMPTY_RESULT) as mock_fr:
            client.get("/api/reports?profile_key=detailed", headers=auth_header())
        kw = mock_fr.call_args.kwargs
        assert kw.get("profile_key") == "detailed"

    def test_HI07b_professional_template_profile_forwarded(self, client, auth_header):
        with patch("reports.report_pipeline.fetch_reports",
                   return_value=_EMPTY_RESULT) as mock_fr:
            client.get("/api/reports?profile_key=professional_template", headers=auth_header())
        kw = mock_fr.call_args.kwargs
        assert kw.get("profile_key") == "professional_template"

    def test_HI08_status_filter_forwarded(self, client, auth_header):
        with patch("reports.report_pipeline.fetch_reports",
                   return_value=_EMPTY_RESULT) as mock_fr:
            client.get("/api/reports?status=final", headers=auth_header())
        kw = mock_fr.call_args.kwargs
        assert kw.get("status") == "final"

    def test_HI08b_absent_filters_are_none(self, client, auth_header):
        with patch("reports.report_pipeline.fetch_reports",
                   return_value=_EMPTY_RESULT) as mock_fr:
            client.get("/api/reports", headers=auth_header())
        kw = mock_fr.call_args.kwargs
        assert kw.get("profile_key") is None
        assert kw.get("status") is None


# ── HI09: GET /api/reports/<id> — found ──────────────────────────────────────

class TestReportsGet:
    def test_HI09_found_returns_200(self, client, auth_header):
        with patch("reports.report_pipeline.fetch_report",
                   return_value=_FULL_RECORD):
            r = client.get("/api/reports/ES-20260515-AAA1", headers=auth_header())
        assert r.status_code == 200

    def test_HI09b_found_status_success(self, client, auth_header):
        with patch("reports.report_pipeline.fetch_report",
                   return_value=_FULL_RECORD):
            data = client.get("/api/reports/ES-20260515-AAA1", headers=auth_header()).get_json()
        assert data["status"] == "success"

    def test_HI09c_found_report_key_present(self, client, auth_header):
        with patch("reports.report_pipeline.fetch_report",
                   return_value=_FULL_RECORD):
            data = client.get("/api/reports/ES-20260515-AAA1", headers=auth_header()).get_json()
        assert "report" in data
        assert data["report"]["report_db_id"] == "ES-20260515-AAA1"

    def test_HI09d_found_report_has_full_dto_fields(self, client, auth_header):
        with patch("reports.report_pipeline.fetch_report",
                   return_value=_FULL_RECORD):
            data = client.get("/api/reports/ES-20260515-AAA1", headers=auth_header()).get_json()
        report = data["report"]
        for key in ("report_db_id", "profile_key", "status",
                    "created_at", "updated_at", "data"):
            assert key in report, f"Missing key: {key!r}"


# ── HI10–HI11: GET /api/reports/<id> — not found ─────────────────────────────

class TestReportsGetNotFound:
    def test_HI10_missing_returns_404(self, client, auth_header):
        with patch("reports.report_pipeline.fetch_report", return_value=None):
            r = client.get("/api/reports/NONEXISTENT-ID", headers=auth_header())
        assert r.status_code == 404

    def test_HI11_missing_status_is_not_found(self, client, auth_header):
        with patch("reports.report_pipeline.fetch_report", return_value=None):
            data = client.get("/api/reports/NONEXISTENT-ID", headers=auth_header()).get_json()
        assert data["status"] == "not_found"

    def test_HI11b_missing_message_contains_id(self, client, auth_header):
        with patch("reports.report_pipeline.fetch_report", return_value=None):
            data = client.get("/api/reports/NONEXISTENT-ID", headers=auth_header()).get_json()
        assert "NONEXISTENT-ID" in data["message"]


# ── HI12–HI13: DB exception handling ─────────────────────────────────────────

class TestDBExceptions:
    def test_HI12_list_db_error_returns_500(self, client, auth_header):
        with patch("reports.report_pipeline.fetch_reports",
                   side_effect=RuntimeError("disk full")):
            r = client.get("/api/reports", headers=auth_header())
        assert r.status_code == 500

    def test_HI12b_list_db_error_status_is_error(self, client, auth_header):
        with patch("reports.report_pipeline.fetch_reports",
                   side_effect=RuntimeError("disk full")):
            data = client.get("/api/reports", headers=auth_header()).get_json()
        assert data["status"] == "error"
        assert data["message"]

    def test_HI13_get_db_error_returns_500(self, client, auth_header):
        with patch("reports.report_pipeline.fetch_report",
                   side_effect=RuntimeError("connection timeout")):
            r = client.get("/api/reports/ES-20260515-AAA1", headers=auth_header())
        assert r.status_code == 500

    def test_HI13b_get_db_error_status_is_error(self, client, auth_header):
        with patch("reports.report_pipeline.fetch_report",
                   side_effect=RuntimeError("connection timeout")):
            data = client.get("/api/reports/ES-20260515-AAA1", headers=auth_header()).get_json()
        assert data["status"] == "error"


# ── HI14: No production DB file created ──────────────────────────────────────

class TestNoProductionDB:
    def test_HI14_no_db_file_created_in_list(self, client, auth_header, tmp_path):
        """Mocking fetch_reports means the real DB is never touched."""
        prod_db = Path(_CORE) / "reports" / "db" / "data" / "reports.db"
        existed_before = prod_db.exists()
        with patch("reports.report_pipeline.fetch_reports",
                   return_value=_EMPTY_RESULT):
            client.get("/api/reports", headers=auth_header())
        # If it didn't exist before, it must not exist after.
        if not existed_before:
            assert not prod_db.exists()

    def test_HI14b_no_db_file_created_in_get(self, client, auth_header):
        """Mocking fetch_report means the real DB is never touched."""
        prod_db = Path(_CORE) / "reports" / "db" / "data" / "reports.db"
        existed_before = prod_db.exists()
        with patch("reports.report_pipeline.fetch_report", return_value=None):
            client.get("/api/reports/any-id", headers=auth_header())
        if not existed_before:
            assert not prod_db.exists()
