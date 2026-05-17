"""
Baseline contract snapshot for existing bridge_api endpoints.

Captures the public response shape of POST /api/valuation and
GET /api/advisor/health so that integration waves BA.1–BA.4 can
assert zero regressions without a live server.

All file I/O (Excel, Word, sheet-removal) is mocked so the test
runs without openpyxl, python-docx, or an OUTPUTS directory with
real content.

Tests: BL01–BL13
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
from auth.tokens import generate_token  # noqa: E402

_USER        = "baseline-test-user"
_TEST_SECRET = "test-secret-for-baseline"


def _auth() -> dict:
    """Return a valid Authorization header for the baseline JWT secret."""
    return {"Authorization": f"Bearer {generate_token(_USER)}"}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", _TEST_SECRET)
    monkeypatch.setenv("ADMIN_USER_IDS", "admin-baseline")
    monkeypatch.delenv("JWT_TTL_SECONDS", raising=False)


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


_MINIMAL = {
    "location":       "القاهرة الجديدة",
    "area":           200,
    "property_type":  "شقة سكنية",
    "price_per_meter": 10_000,
}
_ADV_STUB = {"market_value": 2_000_000.0, "confidence": "عالية"}

_IO_MOCKS = (
    patch("bridge_api.advanced_valuation", return_value=_ADV_STUB),
    patch("bridge_api.write_to_excel_template"),
    patch("bridge_api.write_word_summary"),
    patch("bridge_api._remove_legacy_advanced_sheets"),
)


# ── Health endpoint ───────────────────────────────────────────────────────────

class TestHealthBaseline:
    def test_BL01_health_returns_200(self, client):
        assert client.get("/api/advisor/health").status_code == 200

    def test_BL02_health_status_field_present(self, client):
        data = client.get("/api/advisor/health").get_json()
        assert "status" in data
        assert data["status"] in ("ok", "disabled")

    def test_BL03_health_has_boolean_rag_ready(self, client):
        data = client.get("/api/advisor/health").get_json()
        assert "rag_ready" in data
        assert isinstance(data["rag_ready"], bool)


# ── POST /api/valuation contract ─────────────────────────────────────────────

class TestValuationBaseline:
    @pytest.fixture(autouse=True)
    def _mock_io(self):
        with _IO_MOCKS[0], _IO_MOCKS[1], _IO_MOCKS[2], _IO_MOCKS[3]:
            yield

    # ── Status / HTTP ─────────────────────────────────────────────────────────

    def test_BL04_minimal_payload_returns_200(self, client):
        assert client.post("/api/valuation", json=_MINIMAL, headers=_auth()).status_code == 200

    def test_BL05_options_returns_200(self, client):
        assert client.options("/api/valuation").status_code == 200

    # ── Required response keys ────────────────────────────────────────────────

    def test_BL06_success_response_has_required_keys(self, client):
        data = client.post("/api/valuation", json=_MINIMAL, headers=_auth()).get_json()
        assert data["status"] == "success"
        required = (
            "market_value",
            "excel_url",
            "report_style_requested",
            "report_style_used",
            "template_used",
            "fallback_used",
            "fallback_reason",
        )
        for key in required:
            assert key in data, f"Missing key in response: {key!r}"

    def test_BL07_market_value_is_positive_number(self, client):
        data = client.post("/api/valuation", json=_MINIMAL, headers=_auth()).get_json()
        assert isinstance(data["market_value"], (int, float))
        assert data["market_value"] > 0

    def test_BL08_excel_url_is_http_string(self, client):
        data = client.post("/api/valuation", json=_MINIMAL, headers=_auth()).get_json()
        assert isinstance(data["excel_url"], str)
        assert data["excel_url"].startswith("http")

    def test_BL09_template_and_fallback_are_booleans(self, client):
        data = client.post("/api/valuation", json=_MINIMAL, headers=_auth()).get_json()
        assert isinstance(data["template_used"], bool)
        assert isinstance(data["fallback_used"], bool)
        assert isinstance(data["fallback_reason"], str)

    # ── Report-style semantics ────────────────────────────────────────────────

    def test_BL10_style_legacy(self, client):
        data = client.post("/api/valuation",
                           json={**_MINIMAL, "report_style": "legacy"},
                           headers=_auth()).get_json()
        assert data["report_style_requested"] == "legacy"
        assert data["report_style_used"] == "legacy"
        assert data["template_used"] is False

    def test_BL11_style_detailed(self, client):
        data = client.post("/api/valuation",
                           json={**_MINIMAL, "report_style": "detailed"},
                           headers=_auth()).get_json()
        assert data["report_style_requested"] == "detailed"
        assert data["report_style_used"] == "detailed"
        assert data["template_used"] is False

    def test_BL12_invalid_style_falls_back_to_legacy(self, client):
        data = client.post("/api/valuation",
                           json={**_MINIMAL, "report_style": "bogus_style"},
                           headers=_auth()).get_json()
        assert data["report_style_requested"] == "bogus_style"
        assert data["report_style_used"] == "legacy"

    # ── Robustness ────────────────────────────────────────────────────────────

    def test_BL13_empty_payload_returns_structured_json(self, client):
        """An empty payload must never cause an unstructured crash response."""
        r = client.post("/api/valuation", json={}, headers=_auth())
        assert r.status_code in (200, 400, 422, 500)
        data = r.get_json()
        assert data is not None
        assert "status" in data
