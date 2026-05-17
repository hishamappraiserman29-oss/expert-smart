"""
Integration tests for the Bridge API validation gate (Wave BA.2).

Policy B1 (opt-in, blocking):
  - No "validate" key / validate=false  → zero behavior change (baseline preserved)
  - validate=true + no ERRORs           → 200, generation proceeds, response gets
                                          "validation" key with is_valid+issues
  - validate=true + ERRORs present      → 422, status="validation_error", no Excel

All tests mock:
  - bridge_api.advanced_valuation       (bypass heavy engine)
  - bridge_api.write_to_excel_template  (no file I/O)
  - bridge_api.write_word_summary       (no file I/O)
  - bridge_api._remove_legacy_advanced_sheets
  - reports.report_pipeline.validate_report_data  (control validation result)

Tests: VA01–VA24
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

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

_USER        = "validation-test-user"
_TEST_SECRET = "test-secret-for-validation"


def _auth() -> dict:
    return {"Authorization": f"Bearer {generate_token(_USER)}"}


# ── Helpers: fake validation issues ──────────────────────────────────────────

class _FakeError:
    code = "AREA_REQUIRED"
    message_ar = "المساحة مطلوبة ويجب أن تكون أكبر من صفر"
    message_en = "Area is required and must be positive"
    severity = type("S", (), {"value": "ERROR"})()


class _FakeWarning:
    code = "LICENSE_RECOMMENDED"
    message_ar = "رقم الترخيص موصى به"
    message_en = "License number is recommended"
    severity = type("S", (), {"value": "WARNING"})()


_PASS   = PipelineResult(is_valid=True,  errors=(),               warnings=())
_PASS_W = PipelineResult(is_valid=True,  errors=(),               warnings=(_FakeWarning(),))
_FAIL   = PipelineResult(is_valid=False, errors=(_FakeError(),),  warnings=())

# ── Shared mocks / fixtures ───────────────────────────────────────────────────

_ADV_STUB   = {"market_value": 2_000_000.0, "confidence": "عالية"}
_IO_PATCHES = (
    patch("bridge_api.advanced_valuation",          return_value=_ADV_STUB),
    patch("bridge_api.write_to_excel_template"),
    patch("bridge_api.write_word_summary"),
    patch("bridge_api._remove_legacy_advanced_sheets"),
)

_MINIMAL = {
    "location":        "القاهرة الجديدة",
    "area":            200,
    "property_type":   "شقة سكنية",
    "price_per_meter": 10_000,
}


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", _TEST_SECRET)
    monkeypatch.setenv("ADMIN_USER_IDS", "admin-validation")
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


# ── VA01–VA04: No validation → baseline preserved ────────────────────────────

class TestNoValidation:
    def test_VA01_missing_validate_key_returns_200(self, client):
        """No "validate" in payload → response identical to pre-BA.2 baseline."""
        r = client.post("/api/valuation", json=_MINIMAL, headers=_auth())
        assert r.status_code == 200
        data = r.get_json()
        assert data["status"] == "success"

    def test_VA02_no_validate_response_lacks_validation_key(self, client):
        """When validate is absent the response must NOT contain "validation"."""
        data = client.post("/api/valuation", json=_MINIMAL,
                           headers=_auth()).get_json()
        assert "validation" not in data

    def test_VA03_validate_false_same_as_absent(self, client):
        payload = {**_MINIMAL, "validate": False}
        r = client.post("/api/valuation", json=payload, headers=_auth())
        assert r.status_code == 200
        data = r.get_json()
        assert data["status"] == "success"
        assert "validation" not in data

    def test_VA04_existing_keys_intact_without_validate(self, client):
        """Core response shape must remain unchanged when validate is absent."""
        data = client.post("/api/valuation", json=_MINIMAL,
                           headers=_auth()).get_json()
        for key in ("market_value", "excel_url",
                    "report_style_requested", "report_style_used",
                    "template_used", "fallback_used", "fallback_reason"):
            assert key in data, f"Key missing from response: {key!r}"


# ── VA05–VA09: validate=true + valid data (no ERRORs) → 200 ──────────────────

class TestValidatePassThrough:
    @pytest.fixture(autouse=True)
    def _mock_vrd(self):
        with patch("reports.report_pipeline.validate_report_data",
                   return_value=_PASS) as m:
            self._mock = m
            yield

    def test_VA05_validate_true_valid_data_returns_200(self, client):
        payload = {**_MINIMAL, "validate": True}
        assert client.post("/api/valuation", json=payload,
                           headers=_auth()).status_code == 200

    def test_VA06_validate_true_response_has_validation_key(self, client):
        payload = {**_MINIMAL, "validate": True}
        data = client.post("/api/valuation", json=payload,
                           headers=_auth()).get_json()
        assert "validation" in data

    def test_VA07_validate_true_is_valid_true(self, client):
        payload = {**_MINIMAL, "validate": True}
        data = client.post("/api/valuation", json=payload,
                           headers=_auth()).get_json()
        assert data["validation"]["is_valid"] is True

    def test_VA08_validate_true_generation_proceeds(self, client):
        """Excel URL must be present — generation was not blocked."""
        payload = {**_MINIMAL, "validate": True}
        data = client.post("/api/valuation", json=payload,
                           headers=_auth()).get_json()
        assert "excel_url" in data
        assert data["excel_url"].startswith("http")

    def test_VA09_validate_true_issues_is_list(self, client):
        payload = {**_MINIMAL, "validate": True}
        data = client.post("/api/valuation", json=payload,
                           headers=_auth()).get_json()
        assert isinstance(data["validation"]["issues"], list)


# ── VA10–VA14: validate=true + ERRORs → 422 (blocking) ──────────────────────

class TestValidateBlocking:
    @pytest.fixture(autouse=True)
    def _mock_vrd_fail(self):
        with patch("reports.report_pipeline.validate_report_data",
                   return_value=_FAIL):
            yield

    def test_VA10_errors_return_422(self, client):
        payload = {**_MINIMAL, "validate": True}
        assert client.post("/api/valuation", json=payload,
                           headers=_auth()).status_code == 422

    def test_VA11_422_status_is_validation_error(self, client):
        payload = {**_MINIMAL, "validate": True}
        data = client.post("/api/valuation", json=payload,
                           headers=_auth()).get_json()
        assert data["status"] == "validation_error"

    def test_VA12_422_has_validation_key(self, client):
        payload = {**_MINIMAL, "validate": True}
        data = client.post("/api/valuation", json=payload,
                           headers=_auth()).get_json()
        assert "validation" in data

    def test_VA13_422_issues_is_non_empty_list(self, client):
        payload = {**_MINIMAL, "validate": True}
        data = client.post("/api/valuation", json=payload,
                           headers=_auth()).get_json()
        assert isinstance(data["validation"]["issues"], list)
        assert len(data["validation"]["issues"]) > 0

    def test_VA14_422_no_excel_url_in_response(self, client):
        """Generation must be blocked — no excel_url should appear."""
        payload = {**_MINIMAL, "validate": True}
        data = client.post("/api/valuation", json=payload,
                           headers=_auth()).get_json()
        assert "excel_url" not in data


# ── VA15–VA19: issue shape and bilingual messages ─────────────────────────────

class TestIssueShape:
    @pytest.fixture(autouse=True)
    def _mock_vrd_fail(self):
        with patch("reports.report_pipeline.validate_report_data",
                   return_value=_FAIL):
            yield

    def test_VA15_issue_has_required_keys(self, client):
        payload = {**_MINIMAL, "validate": True}
        data = client.post("/api/valuation", json=payload,
                           headers=_auth()).get_json()
        issue = data["validation"]["issues"][0]
        for key in ("code", "severity", "message_ar", "message_en"):
            assert key in issue, f"Issue missing key: {key!r}"

    def test_VA16_issue_code_is_string(self, client):
        payload = {**_MINIMAL, "validate": True}
        data = client.post("/api/valuation", json=payload,
                           headers=_auth()).get_json()
        assert isinstance(data["validation"]["issues"][0]["code"], str)

    def test_VA17_message_ar_is_nonempty_string(self, client):
        payload = {**_MINIMAL, "validate": True}
        data = client.post("/api/valuation", json=payload,
                           headers=_auth()).get_json()
        msg_ar = data["validation"]["issues"][0]["message_ar"]
        assert isinstance(msg_ar, str) and msg_ar

    def test_VA18_message_en_is_nonempty_string(self, client):
        payload = {**_MINIMAL, "validate": True}
        data = client.post("/api/valuation", json=payload,
                           headers=_auth()).get_json()
        msg_en = data["validation"]["issues"][0]["message_en"]
        assert isinstance(msg_en, str) and msg_en

    def test_VA19_severity_is_string(self, client):
        payload = {**_MINIMAL, "validate": True}
        data = client.post("/api/valuation", json=payload,
                           headers=_auth()).get_json()
        assert isinstance(data["validation"]["issues"][0]["severity"], str)


# ── VA20–VA22: warnings do not block ─────────────────────────────────────────

class TestWarningsPassThrough:
    @pytest.fixture(autouse=True)
    def _mock_vrd_warn(self):
        with patch("reports.report_pipeline.validate_report_data",
                   return_value=_PASS_W):
            yield

    def test_VA20_warnings_only_returns_200(self, client):
        payload = {**_MINIMAL, "validate": True}
        assert client.post("/api/valuation", json=payload,
                           headers=_auth()).status_code == 200

    def test_VA21_warnings_generation_proceeds(self, client):
        payload = {**_MINIMAL, "validate": True}
        data = client.post("/api/valuation", json=payload,
                           headers=_auth()).get_json()
        assert data["status"] == "success"
        assert "excel_url" in data

    def test_VA22_warnings_appear_in_issues(self, client):
        payload = {**_MINIMAL, "validate": True}
        data = client.post("/api/valuation", json=payload,
                           headers=_auth()).get_json()
        assert data["validation"]["is_valid"] is True
        assert len(data["validation"]["issues"]) == 1
        assert data["validation"]["issues"][0]["severity"] == "WARNING"


# ── VA23: profile_key forwarding ──────────────────────────────────────────────

class TestProfileKeyForwarding:
    @pytest.mark.parametrize("style,expected_key", [
        ("legacy",               "legacy"),
        ("detailed",             "detailed"),
        ("professional_template","professional_template"),
        ("bogus_style",          "legacy"),   # falls back to legacy
    ])
    def test_VA23_profile_key_forwarded_correctly(self, client, style, expected_key):
        with patch("reports.report_pipeline.validate_report_data",
                   return_value=_PASS) as mock_vrd:
            payload = {**_MINIMAL, "validate": True, "report_style": style}
            client.post("/api/valuation", json=payload, headers=_auth())
        _kw = mock_vrd.call_args.kwargs
        assert _kw.get("profile_key") == expected_key


# ── VA24: gate exception falls through ───────────────────────────────────────

class TestGateFallThrough:
    def test_VA24_gate_exception_falls_through_to_200(self, client):
        """If validate_report_data raises, the gate must log and fall through."""
        with patch("reports.report_pipeline.validate_report_data",
                   side_effect=RuntimeError("engine unavailable")):
            payload = {**_MINIMAL, "validate": True}
            r = client.post("/api/valuation", json=payload, headers=_auth())
        assert r.status_code == 200
        data = r.get_json()
        assert data["status"] == "success"
        assert "validation" not in data
