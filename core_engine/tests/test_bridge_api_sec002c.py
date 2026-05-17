"""
SEC-002c tests — financial regulated endpoints + assets management + admin ops auth hardening.

All 22 endpoints now require auth:

Radar (2) — @_require_admin:
  POST /api/radar/start
  POST /api/radar/stop

Training (1) — @_require_admin:
  POST /api/training/register

Assets management (6) — @require_auth:
  GET  /api/assets
  POST /api/assets/register
  GET  /api/assets/<id>
  PUT/POST /api/assets/<id>/update
  GET  /api/assets/dashboard

Government financial (4) — @require_auth / @_require_admin:
  POST /api/government/compliance/check   → @require_auth
  POST /api/government/tax/calculate      → @require_auth
  POST /api/government/forms/generate     → @require_auth
  POST /api/government/portal/create      → @_require_admin

Banking regulated (5) — @require_auth / @_require_admin:
  POST /api/banking/collateral/value      → @require_auth
  POST /api/banking/ltv/calculate         → @require_auth
  POST /api/banking/collateral/register   → @require_auth
  GET  /api/banking/dashboard/<bank_id>   → @_require_admin
  POST /api/banking/compliance/check      → @require_auth

Funds / FRA (5) — @require_auth:
  POST /api/funds/fair-value/assess
  POST /api/funds/nav/calculate
  POST /api/funds/value
  POST /api/funds/compliance/check
  GET  /api/funds/dashboard/<manager_id>
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

_ADMIN_USER  = "admin-sec002c-test"
_NON_ADMIN   = "regular-sec002c-user"
_TEST_SECRET = "test-secret-for-sec002c"


def _admin_headers() -> dict:
    return {"Authorization": f"Bearer {generate_token(_ADMIN_USER)}"}


def _user_headers() -> dict:
    return {"Authorization": f"Bearer {generate_token(_NON_ADMIN)}"}


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", _TEST_SECRET)
    monkeypatch.setenv("ADMIN_USER_IDS", _ADMIN_USER)
    monkeypatch.delenv("JWT_TTL_SECONDS", raising=False)


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── helpers ───────────────────────────────────────────────────────────────────

def _assert_auth_gated(resp_no_token, resp_with_token):
    """No token → 401. Valid token → handler reached (not 401/403)."""
    assert resp_no_token.status_code == 401, (
        f"Expected 401 without token, got {resp_no_token.status_code}"
    )
    assert resp_with_token.status_code not in (401, 403), (
        f"Expected handler reached with token, got {resp_with_token.status_code}"
    )


def _assert_admin_gated(resp_no_token, resp_non_admin, resp_admin):
    """No token → 401. Non-admin → 403. Admin → handler reached (not 401/403)."""
    assert resp_no_token.status_code == 401, (
        f"Expected 401 without token, got {resp_no_token.status_code}"
    )
    assert resp_non_admin.status_code == 403, (
        f"Expected 403 for non-admin, got {resp_non_admin.status_code}"
    )
    assert resp_admin.status_code not in (401, 403), (
        f"Expected handler reached for admin, got {resp_admin.status_code}"
    )


# ── Radar (admin-only) ────────────────────────────────────────────────────────

class TestRadarAdminGated:

    def test_start_no_token_returns_401(self, client):
        assert client.post("/api/radar/start", json={}).status_code == 401

    def test_start_non_admin_returns_403(self, client):
        assert client.post("/api/radar/start", json={}, headers=_user_headers()).status_code == 403

    def test_start_admin_reaches_handler(self, client):
        assert client.post("/api/radar/start", json={}, headers=_admin_headers()).status_code not in (401, 403)

    def test_stop_no_token_returns_401(self, client):
        assert client.post("/api/radar/stop", json={}).status_code == 401

    def test_stop_non_admin_returns_403(self, client):
        assert client.post("/api/radar/stop", json={}, headers=_user_headers()).status_code == 403

    def test_stop_admin_reaches_handler(self, client):
        assert client.post("/api/radar/stop", json={}, headers=_admin_headers()).status_code not in (401, 403)

    def test_options_preflight_always_allowed(self, client):
        for path in ["/api/radar/start", "/api/radar/stop"]:
            r = client.options(path)
            assert r.status_code == 200, f"OPTIONS {path} returned {r.status_code}"


# ── Training (admin-only) ─────────────────────────────────────────────────────

class TestTrainingAdminGated:

    def test_register_no_token_returns_401(self, client):
        assert client.post("/api/training/register", json={}).status_code == 401

    def test_register_non_admin_returns_403(self, client):
        assert client.post("/api/training/register", json={}, headers=_user_headers()).status_code == 403

    def test_register_admin_reaches_handler(self, client):
        assert client.post("/api/training/register", json={}, headers=_admin_headers()).status_code not in (401, 403)

    def test_options_preflight_always_allowed(self, client):
        r = client.options("/api/training/register")
        assert r.status_code == 200


# ── Assets management (auth-required) ─────────────────────────────────────────

class TestAssetsAuthGated:

    def test_list_requires_auth(self, client):
        r_anon = client.get("/api/assets")
        r_auth = client.get("/api/assets", headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_register_requires_auth(self, client):
        r_anon = client.post("/api/assets/register", json={})
        r_auth = client.post("/api/assets/register", json={}, headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_get_requires_auth(self, client):
        r_anon = client.get("/api/assets/some-asset-id")
        r_auth = client.get("/api/assets/some-asset-id", headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_update_requires_auth(self, client):
        r_anon = client.post("/api/assets/some-asset-id/update", json={})
        r_auth = client.post("/api/assets/some-asset-id/update", json={}, headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_dashboard_requires_auth(self, client):
        r_anon = client.get("/api/assets/dashboard")
        r_auth = client.get("/api/assets/dashboard", headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_options_preflight_always_allowed(self, client):
        for path in [
            "/api/assets",
            "/api/assets/register",
            "/api/assets/some-id",
            "/api/assets/some-id/update",
            "/api/assets/dashboard",
        ]:
            r = client.options(path)
            assert r.status_code == 200, f"OPTIONS {path} returned {r.status_code}"


# ── Government financial ──────────────────────────────────────────────────────

class TestGovernmentAuthGated:

    def test_compliance_check_requires_auth(self, client):
        r_anon = client.post("/api/government/compliance/check", json={})
        r_auth = client.post("/api/government/compliance/check", json={}, headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_tax_calculate_requires_auth(self, client):
        r_anon = client.post("/api/government/tax/calculate", json={})
        r_auth = client.post("/api/government/tax/calculate", json={}, headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_forms_generate_requires_auth(self, client):
        r_anon = client.post("/api/government/forms/generate", json={})
        r_auth = client.post("/api/government/forms/generate", json={}, headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_portal_create_requires_admin(self, client):
        r_anon      = client.post("/api/government/portal/create", json={})
        r_non_admin = client.post("/api/government/portal/create", json={}, headers=_user_headers())
        r_admin     = client.post("/api/government/portal/create", json={}, headers=_admin_headers())
        _assert_admin_gated(r_anon, r_non_admin, r_admin)

    def test_options_preflight_always_allowed(self, client):
        for path in [
            "/api/government/compliance/check",
            "/api/government/tax/calculate",
            "/api/government/forms/generate",
            "/api/government/portal/create",
        ]:
            r = client.options(path)
            assert r.status_code == 200, f"OPTIONS {path} returned {r.status_code}"


# ── Banking regulated ─────────────────────────────────────────────────────────

class TestBankingAuthGated:

    def test_collateral_value_requires_auth(self, client):
        r_anon = client.post("/api/banking/collateral/value", json={})
        r_auth = client.post("/api/banking/collateral/value", json={}, headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_ltv_calculate_requires_auth(self, client):
        r_anon = client.post("/api/banking/ltv/calculate", json={})
        r_auth = client.post("/api/banking/ltv/calculate", json={}, headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_collateral_register_requires_auth(self, client):
        r_anon = client.post("/api/banking/collateral/register", json={})
        r_auth = client.post("/api/banking/collateral/register", json={}, headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_dashboard_requires_admin(self, client):
        r_anon      = client.get("/api/banking/dashboard/some-bank-id")
        r_non_admin = client.get("/api/banking/dashboard/some-bank-id", headers=_user_headers())
        r_admin     = client.get("/api/banking/dashboard/some-bank-id", headers=_admin_headers())
        _assert_admin_gated(r_anon, r_non_admin, r_admin)

    def test_compliance_check_requires_auth(self, client):
        r_anon = client.post("/api/banking/compliance/check", json={})
        r_auth = client.post("/api/banking/compliance/check", json={}, headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_options_preflight_always_allowed(self, client):
        for path in [
            "/api/banking/collateral/value",
            "/api/banking/ltv/calculate",
            "/api/banking/collateral/register",
            "/api/banking/dashboard/some-id",
            "/api/banking/compliance/check",
        ]:
            r = client.options(path)
            assert r.status_code == 200, f"OPTIONS {path} returned {r.status_code}"


# ── Funds / FRA ───────────────────────────────────────────────────────────────

class TestFundsAuthGated:

    def test_fair_value_assess_requires_auth(self, client):
        r_anon = client.post("/api/funds/fair-value/assess", json={})
        r_auth = client.post("/api/funds/fair-value/assess", json={}, headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_nav_calculate_requires_auth(self, client):
        r_anon = client.post("/api/funds/nav/calculate", json={})
        r_auth = client.post("/api/funds/nav/calculate", json={}, headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_value_requires_auth(self, client):
        r_anon = client.post("/api/funds/value", json={})
        r_auth = client.post("/api/funds/value", json={}, headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_compliance_check_requires_auth(self, client):
        r_anon = client.post("/api/funds/compliance/check", json={})
        r_auth = client.post("/api/funds/compliance/check", json={}, headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_dashboard_requires_auth(self, client):
        r_anon = client.get("/api/funds/dashboard/some-manager-id")
        r_auth = client.get("/api/funds/dashboard/some-manager-id", headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_options_preflight_always_allowed(self, client):
        for path in [
            "/api/funds/fair-value/assess",
            "/api/funds/nav/calculate",
            "/api/funds/value",
            "/api/funds/compliance/check",
            "/api/funds/dashboard/some-manager-id",
        ]:
            r = client.options(path)
            assert r.status_code == 200, f"OPTIONS {path} returned {r.status_code}"
