"""
Integration tests for the Bridge API auto-persist gate (Wave BA.3).

Policy P1 (non-fatal) + V1 (validation-aware ordering):
  - No "persist" key / persist=false  → zero behavior change (no persistence keys)
  - persist=true + DB success         → 200, report_db_id + persisted=true
  - persist=true + DB failure         → 200, persisted=false + persist_error (P1)
  - validate=true(ERROR) + persist    → 422, persist never called (V1)
  - validate=true(pass) + persist     → 200, both validation + persist keys present

All tests mock:
  - bridge_api.advanced_valuation              (bypass engine)
  - bridge_api.write_to_excel_template         (no file I/O)
  - bridge_api.write_word_summary              (no file I/O)
  - bridge_api._remove_legacy_advanced_sheets
  - reports.report_pipeline.persist_report_data (control DB result)

Tests: PA01–PA20
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

from bridge_api import app                          # noqa: E402
from reports.report_pipeline import PipelineResult  # noqa: E402
from auth.tokens import generate_token              # noqa: E402

# ── Auth helpers ──────────────────────────────────────────────────────────────

_USER        = "persist-test-user"
_TEST_SECRET = "test-secret-for-persist"


def _auth() -> dict:
    return {"Authorization": f"Bearer {generate_token(_USER)}"}


# ── Shared constants ──────────────────────────────────────────────────────────

_ADV_STUB = {"market_value": 2_000_000.0, "confidence": "عالية"}
_PERSIST_ID = "ES-20260515-ABCD"

_MINIMAL = {
    "location":        "القاهرة الجديدة",
    "area":            200,
    "property_type":   "شقة سكنية",
    "price_per_meter": 10_000,
}

_IO_PATCHES = (
    patch("bridge_api.advanced_valuation",          return_value=_ADV_STUB),
    patch("bridge_api.write_to_excel_template"),
    patch("bridge_api.write_word_summary"),
    patch("bridge_api._remove_legacy_advanced_sheets"),
)

# ── Fake validation results for combined tests ────────────────────────────────

class _FakeError:
    code = "AREA_REQUIRED"
    message_ar = "المساحة مطلوبة"
    message_en = "Area is required"
    severity = type("S", (), {"value": "ERROR"})()

_VAL_PASS = PipelineResult(is_valid=True,  errors=(),             warnings=())
_VAL_FAIL = PipelineResult(is_valid=False, errors=(_FakeError(),), warnings=())


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", _TEST_SECRET)
    monkeypatch.setenv("ADMIN_USER_IDS", "admin-persist")
    monkeypatch.delenv("JWT_TTL_SECONDS", raising=False)


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def _mock_io():
    with _IO_PATCHES[0], _IO_PATCHES[1], _IO_PATCHES[2], _IO_PATCHES[3]:
        yield


# ── PA01–PA04: No persist → baseline preserved ───────────────────────────────

class TestNoPersist:
    def test_PA01_missing_persist_key_returns_200(self, client):
        r = client.post("/api/valuation", json=_MINIMAL, headers=_auth())
        assert r.status_code == 200
        assert r.get_json()["status"] == "success"

    def test_PA02_no_persist_response_lacks_persistence_keys(self, client):
        data = client.post("/api/valuation", json=_MINIMAL,
                           headers=_auth()).get_json()
        assert "report_db_id"  not in data
        assert "persisted"     not in data
        assert "persist_error" not in data

    def test_PA03_persist_false_same_as_absent(self, client):
        data = client.post("/api/valuation",
                           json={**_MINIMAL, "persist": False},
                           headers=_auth()).get_json()
        assert data["status"] == "success"
        assert "report_db_id" not in data

    def test_PA04_existing_keys_intact_without_persist(self, client):
        data = client.post("/api/valuation", json=_MINIMAL,
                           headers=_auth()).get_json()
        for key in ("market_value", "excel_url",
                    "report_style_requested", "report_style_used"):
            assert key in data, f"Key missing: {key!r}"


# ── PA05–PA10: persist=true + DB success ─────────────────────────────────────

class TestPersistSuccess:
    @pytest.fixture(autouse=True)
    def _mock_prd(self):
        with patch("reports.report_pipeline.persist_report_data",
                   return_value=_PERSIST_ID) as m:
            self._mock = m
            yield

    def test_PA05_persist_true_returns_200(self, client):
        assert client.post("/api/valuation",
                           json={**_MINIMAL, "persist": True},
                           headers=_auth()).status_code == 200

    def test_PA06_persist_true_report_db_id_present(self, client):
        data = client.post("/api/valuation",
                           json={**_MINIMAL, "persist": True},
                           headers=_auth()).get_json()
        assert "report_db_id" in data
        assert data["report_db_id"] == _PERSIST_ID

    def test_PA07_persist_true_persisted_is_true(self, client):
        data = client.post("/api/valuation",
                           json={**_MINIMAL, "persist": True},
                           headers=_auth()).get_json()
        assert data["persisted"] is True

    def test_PA08_persist_true_persist_error_is_empty_string(self, client):
        data = client.post("/api/valuation",
                           json={**_MINIMAL, "persist": True},
                           headers=_auth()).get_json()
        assert data["persist_error"] == ""

    def test_PA09_persist_true_excel_url_still_present(self, client):
        """Generation must not be blocked — excel_url must survive."""
        data = client.post("/api/valuation",
                           json={**_MINIMAL, "persist": True},
                           headers=_auth()).get_json()
        assert "excel_url" in data
        assert data["excel_url"].startswith("http")

    def test_PA10_persist_called_exactly_once(self, client):
        client.post("/api/valuation", json={**_MINIMAL, "persist": True},
                    headers=_auth())
        self._mock.assert_called_once()


# ── PA11–PA15: persist=true + DB failure (P1: non-fatal) ─────────────────────

class TestPersistFailure:
    @pytest.fixture(autouse=True)
    def _mock_prd_fail(self):
        with patch("reports.report_pipeline.persist_report_data",
                   side_effect=RuntimeError("disk full")):
            yield

    def test_PA11_db_failure_still_returns_200(self, client):
        """P1: DB failure must not prevent the user from getting their Excel."""
        r = client.post("/api/valuation", json={**_MINIMAL, "persist": True},
                        headers=_auth())
        assert r.status_code == 200

    def test_PA12_db_failure_persisted_is_false(self, client):
        data = client.post("/api/valuation",
                           json={**_MINIMAL, "persist": True},
                           headers=_auth()).get_json()
        assert data["persisted"] is False

    def test_PA13_db_failure_persist_error_nonempty(self, client):
        data = client.post("/api/valuation",
                           json={**_MINIMAL, "persist": True},
                           headers=_auth()).get_json()
        assert isinstance(data["persist_error"], str)
        assert data["persist_error"]

    def test_PA14_db_failure_no_report_db_id(self, client):
        data = client.post("/api/valuation",
                           json={**_MINIMAL, "persist": True},
                           headers=_auth()).get_json()
        assert "report_db_id" not in data or data.get("report_db_id") is None

    def test_PA15_db_failure_excel_url_still_present(self, client):
        """Excel report delivered despite DB failure."""
        data = client.post("/api/valuation",
                           json={**_MINIMAL, "persist": True},
                           headers=_auth()).get_json()
        assert "excel_url" in data
        assert data["status"] == "success"


# ── PA16–PA17: validate + persist coexistence ────────────────────────────────

class TestValidateAndPersist:
    def test_PA16_validate_pass_and_persist_both_work(self, client):
        """V1: validation passes → persist runs → both keys in response."""
        with (
            patch("reports.report_pipeline.validate_report_data",
                  return_value=_VAL_PASS),
            patch("reports.report_pipeline.persist_report_data",
                  return_value=_PERSIST_ID),
        ):
            payload = {**_MINIMAL, "validate": True, "persist": True}
            data = client.post("/api/valuation", json=payload,
                               headers=_auth()).get_json()
        assert data["status"] == "success"
        assert data["validation"]["is_valid"] is True
        assert data["report_db_id"] == _PERSIST_ID
        assert data["persisted"] is True

    def test_PA17_validate_error_blocks_persist(self, client):
        """V1: ERROR from validation returns 422 before persist is ever called."""
        with (
            patch("reports.report_pipeline.validate_report_data",
                  return_value=_VAL_FAIL),
            patch("reports.report_pipeline.persist_report_data",
                  return_value=_PERSIST_ID) as mock_prd,
        ):
            payload = {**_MINIMAL, "validate": True, "persist": True}
            r = client.post("/api/valuation", json=payload, headers=_auth())
        assert r.status_code == 422
        mock_prd.assert_not_called()


# ── PA18: profile_key forwarding ──────────────────────────────────────────────

class TestProfileKeyForwarding:
    @pytest.mark.parametrize("style,expected", [
        ("legacy",                "legacy"),
        ("detailed",              "detailed"),
        # professional_template: template file absent in test env → fallback to legacy;
        # persist receives the *actual* _style_used (legacy), not the requested style.
        ("professional_template", "legacy"),
        ("bogus_style",           "legacy"),   # invalid style → falls back to legacy
    ])
    def test_PA18_profile_key_forwarded(self, client, style, expected):
        with patch("reports.report_pipeline.persist_report_data",
                   return_value=_PERSIST_ID) as mock_prd:
            payload = {**_MINIMAL, "persist": True, "report_style": style}
            client.post("/api/valuation", json=payload, headers=_auth())
        kw = mock_prd.call_args.kwargs
        assert kw.get("profile_key") == expected


# ── PA19–PA20: report_status forwarding ──────────────────────────────────────

class TestReportStatusForwarding:
    def test_PA19_report_status_final_forwarded(self, client):
        with patch("reports.report_pipeline.persist_report_data",
                   return_value=_PERSIST_ID) as mock_prd:
            payload = {**_MINIMAL, "persist": True, "report_status": "final"}
            client.post("/api/valuation", json=payload, headers=_auth())
        kw = mock_prd.call_args.kwargs
        assert kw.get("status") == "final"

    def test_PA20_invalid_report_status_falls_back_to_draft(self, client):
        with patch("reports.report_pipeline.persist_report_data",
                   return_value=_PERSIST_ID) as mock_prd:
            payload = {**_MINIMAL, "persist": True, "report_status": "invalid"}
            client.post("/api/valuation", json=payload, headers=_auth())
        kw = mock_prd.call_args.kwargs
        assert kw.get("status") == "draft"
