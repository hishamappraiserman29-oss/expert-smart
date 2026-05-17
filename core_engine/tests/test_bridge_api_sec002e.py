"""
SEC-002e tests — DEFER_REVIEW endpoints auth hardening.

15 endpoints hardened with @require_auth:

SEC-002e-1 (file/AI/DB, 5):
  POST /api/valuation
  POST /api/advisor
  POST /api/comparables/search
  POST /api/price/intelligence
  POST /api/knowledge/enhance

SEC-002e-2 (engines + scenarios + standards + IAAO + language, 10):
  POST /api/valuation/dcf
  POST /api/engines/comparative
  POST /api/engines/cost
  POST /api/engines/income
  POST /api/scenarios/run
  POST /api/scenarios/monte_carlo
  POST /api/scenarios/sensitivity
  POST /api/scenarios/stress_test
  POST /api/standards/validate
  POST /api/iaao
  POST /api/language/set/<code>

No change:
  POST/GET /api/price-map  →  PUBLIC_OK (remains unprotected)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(str(_CORE))

from bridge_api import app  # noqa: E402
from auth.tokens import generate_token  # noqa: E402

_USER        = "regular-sec002e-user"
_TEST_SECRET = "test-secret-for-sec002e"


def _auth() -> dict:
    return {"Authorization": f"Bearer {generate_token(_USER)}"}


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", _TEST_SECRET)
    monkeypatch.setenv("ADMIN_USER_IDS", "admin-sec002e")
    monkeypatch.delenv("JWT_TTL_SECONDS", raising=False)


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── helper ────────────────────────────────────────────────────────────────────

def _assert_auth_gated(resp_no_token, resp_with_token):
    assert resp_no_token.status_code == 401, (
        f"Expected 401 without token, got {resp_no_token.status_code}"
    )
    assert resp_with_token.status_code not in (401, 403), (
        f"Expected handler reached with token, got {resp_with_token.status_code}"
    )


# ── SEC-002e-1: file/AI/DB endpoints ─────────────────────────────────────────

class TestSec002e1AuthGated:

    def test_valuation_requires_auth(self, client):
        r_anon = client.post("/api/valuation", json={})
        r_auth = client.post("/api/valuation", json={}, headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_advisor_requires_auth(self, client):
        r_anon = client.post("/api/advisor", json={})
        r_auth = client.post("/api/advisor", json={"question": "test"}, headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_comparables_search_requires_auth(self, client):
        r_anon = client.post("/api/comparables/search", json={})
        r_auth = client.post("/api/comparables/search", json={}, headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_price_intelligence_requires_auth(self, client):
        r_anon = client.post("/api/price/intelligence", json={})
        r_auth = client.post("/api/price/intelligence", json={"location": "test"},
                             headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_knowledge_enhance_requires_auth(self, client):
        r_anon = client.post("/api/knowledge/enhance", json={})
        r_auth = client.post("/api/knowledge/enhance", json={}, headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_options_preflight_always_allowed(self, client):
        for path in [
            "/api/valuation",
            "/api/advisor",
            "/api/comparables/search",
            "/api/price/intelligence",
            "/api/knowledge/enhance",
        ]:
            r = client.options(path)
            assert r.status_code == 200, f"OPTIONS {path} returned {r.status_code}"


# ── SEC-002e-2: engines + scenarios + standards + IAAO + language ─────────────

class TestSec002e2AuthGated:

    def test_valuation_dcf_requires_auth(self, client):
        r_anon = client.post("/api/valuation/dcf", json={})
        r_auth = client.post("/api/valuation/dcf", json={}, headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_engine_comparative_requires_auth(self, client):
        r_anon = client.post("/api/engines/comparative", json={})
        r_auth = client.post("/api/engines/comparative", json={}, headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_engine_cost_requires_auth(self, client):
        r_anon = client.post("/api/engines/cost", json={})
        r_auth = client.post("/api/engines/cost", json={}, headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_engine_income_requires_auth(self, client):
        r_anon = client.post("/api/engines/income", json={})
        r_auth = client.post("/api/engines/income", json={}, headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_scenarios_run_requires_auth(self, client):
        r_anon = client.post("/api/scenarios/run", json={})
        r_auth = client.post("/api/scenarios/run", json={"base_value": 1000},
                             headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_scenarios_monte_carlo_requires_auth(self, client):
        r_anon = client.post("/api/scenarios/monte_carlo", json={})
        r_auth = client.post("/api/scenarios/monte_carlo", json={"base_value": 1000},
                             headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_scenarios_sensitivity_requires_auth(self, client):
        r_anon = client.post("/api/scenarios/sensitivity", json={})
        r_auth = client.post("/api/scenarios/sensitivity", json={"base_value": 1000},
                             headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_scenarios_stress_test_requires_auth(self, client):
        r_anon = client.post("/api/scenarios/stress_test", json={})
        r_auth = client.post("/api/scenarios/stress_test", json={"base_value": 1000},
                             headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_standards_validate_requires_auth(self, client):
        r_anon = client.post("/api/standards/validate", json={})
        r_auth = client.post("/api/standards/validate", json={}, headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_iaao_requires_auth(self, client):
        r_anon = client.post("/api/iaao", json={})
        r_auth = client.post("/api/iaao", json={}, headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_language_set_requires_auth(self, client):
        r_anon = client.post("/api/language/set/ar")
        r_auth = client.post("/api/language/set/ar", headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_options_preflight_always_allowed(self, client):
        for path in [
            "/api/valuation/dcf",
            "/api/engines/comparative",
            "/api/engines/cost",
            "/api/engines/income",
            "/api/scenarios/run",
            "/api/scenarios/monte_carlo",
            "/api/scenarios/sensitivity",
            "/api/scenarios/stress_test",
            "/api/standards/validate",
            "/api/iaao",
            "/api/language/set/ar",
        ]:
            r = client.options(path)
            assert r.status_code == 200, f"OPTIONS {path} returned {r.status_code}"


# ── price-map stays PUBLIC_OK ─────────────────────────────────────────────────

class TestPriceMapPublicOk:
    """price-map was classified PUBLIC_OK and must NOT require auth."""

    def test_post_accessible_without_token(self, client):
        r = client.post("/api/price-map", json={"location": "Cairo"})
        assert r.status_code != 401, (
            f"/api/price-map POST should be public, got {r.status_code}"
        )

    def test_get_accessible_without_token(self, client):
        r = client.get("/api/price-map?location=Cairo")
        assert r.status_code != 401, (
            f"/api/price-map GET should be public, got {r.status_code}"
        )
