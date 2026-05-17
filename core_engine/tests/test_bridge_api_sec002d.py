"""
SEC-002d tests — integrations, analytics, remaining admin ops auth hardening.

18 endpoints hardened (matrix listed 16; final count after audit is 18):

Auth-required (@require_auth) — 12:
  POST /api/marketplace/plugins/<id>/reviews
  GET  /api/integrations/plugins
  GET  /api/integrations/webhooks
  POST /api/integrations/webhooks
  DELETE /api/integrations/webhooks/<id>
  GET  /api/integrations/oauth/<svc>/authorize
  POST /api/analytics/metrics/<id>/record
  GET  /api/analytics/metrics/<id>/statistics
  GET  /api/analytics/metrics/<id>/timeseries
  GET  /api/analytics/dashboards
  GET  /api/analytics/dashboards/<id>
  POST /api/analytics/risk/portfolio/<id>

Admin-required (@_require_admin) — 6:
  POST /api/hardening/integrations/register
  GET  /api/hardening/integrations/stats
  POST /api/integrations/sync
  POST /api/integrations/partners
  GET  /api/integrations/partners/<id>/dashboard
  POST /api/integrations/connector-webhooks
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

_ADMIN_USER  = "admin-sec002d-test"
_NON_ADMIN   = "regular-sec002d-user"
_TEST_SECRET = "test-secret-for-sec002d"


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
    assert resp_no_token.status_code == 401, (
        f"Expected 401 without token, got {resp_no_token.status_code}"
    )
    assert resp_with_token.status_code not in (401, 403), (
        f"Expected handler reached with token, got {resp_with_token.status_code}"
    )


def _assert_admin_gated(resp_no_token, resp_non_admin, resp_admin):
    assert resp_no_token.status_code == 401, (
        f"Expected 401 without token, got {resp_no_token.status_code}"
    )
    assert resp_non_admin.status_code == 403, (
        f"Expected 403 for non-admin, got {resp_non_admin.status_code}"
    )
    assert resp_admin.status_code not in (401, 403), (
        f"Expected handler reached for admin, got {resp_admin.status_code}"
    )


# ── Marketplace reviews (@require_auth) ───────────────────────────────────────

class TestMarketplaceReviewsAuthGated:

    def test_add_review_requires_auth(self, client):
        r_anon = client.post("/api/marketplace/plugins/some-plugin/reviews", json={})
        r_auth = client.post("/api/marketplace/plugins/some-plugin/reviews", json={},
                             headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_options_preflight_always_allowed(self, client):
        r = client.options("/api/marketplace/plugins/some-plugin/reviews")
        assert r.status_code == 200


# ── Integrations / Webhooks / OAuth (@require_auth) ──────────────────────────

class TestIntegrationsAuthGated:

    def test_plugins_list_requires_auth(self, client):
        r_anon = client.get("/api/integrations/plugins")
        r_auth = client.get("/api/integrations/plugins", headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_webhooks_list_requires_auth(self, client):
        r_anon = client.get("/api/integrations/webhooks")
        r_auth = client.get("/api/integrations/webhooks", headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_webhooks_create_requires_auth(self, client):
        r_anon = client.post("/api/integrations/webhooks", json={})
        r_auth = client.post("/api/integrations/webhooks", json={}, headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_webhooks_delete_requires_auth(self, client):
        r_anon = client.delete("/api/integrations/webhooks/some-webhook-id")
        r_auth = client.delete("/api/integrations/webhooks/some-webhook-id",
                               headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_oauth_authorize_requires_auth(self, client):
        r_anon = client.get("/api/integrations/oauth/github/authorize")
        r_auth = client.get("/api/integrations/oauth/github/authorize",
                            headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_options_preflight_always_allowed(self, client):
        for path in [
            "/api/integrations/plugins",
            "/api/integrations/webhooks",
            "/api/integrations/webhooks/some-id",
            "/api/integrations/oauth/github/authorize",
        ]:
            r = client.options(path)
            assert r.status_code == 200, f"OPTIONS {path} returned {r.status_code}"


# ── Analytics (user-scoped, @require_auth) ────────────────────────────────────

class TestAnalyticsAuthGated:

    def test_record_metric_requires_auth(self, client):
        r_anon = client.post("/api/analytics/metrics/some-metric/record", json={})
        r_auth = client.post("/api/analytics/metrics/some-metric/record", json={},
                             headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_metric_statistics_requires_auth(self, client):
        r_anon = client.get("/api/analytics/metrics/some-metric/statistics")
        r_auth = client.get("/api/analytics/metrics/some-metric/statistics",
                            headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_metric_timeseries_requires_auth(self, client):
        r_anon = client.get("/api/analytics/metrics/some-metric/timeseries")
        r_auth = client.get("/api/analytics/metrics/some-metric/timeseries",
                            headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_list_dashboards_requires_auth(self, client):
        r_anon = client.get("/api/analytics/dashboards")
        r_auth = client.get("/api/analytics/dashboards", headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_get_dashboard_requires_auth(self, client):
        r_anon = client.get("/api/analytics/dashboards/some-dashboard-id")
        r_auth = client.get("/api/analytics/dashboards/some-dashboard-id",
                            headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_portfolio_risk_requires_auth(self, client):
        r_anon = client.post("/api/analytics/risk/portfolio/some-portfolio-id", json={})
        r_auth = client.post("/api/analytics/risk/portfolio/some-portfolio-id", json={},
                             headers=_user_headers())
        _assert_auth_gated(r_anon, r_auth)

    def test_options_preflight_always_allowed(self, client):
        for path in [
            "/api/analytics/metrics/some-id/record",
            "/api/analytics/metrics/some-id/statistics",
            "/api/analytics/metrics/some-id/timeseries",
            "/api/analytics/dashboards",
            "/api/analytics/dashboards/some-id",
            "/api/analytics/risk/portfolio/some-id",
        ]:
            r = client.options(path)
            assert r.status_code == 200, f"OPTIONS {path} returned {r.status_code}"


# ── Hardening integrations (@_require_admin) ──────────────────────────────────

class TestHardeningIntegrationsAdminGated:

    def test_register_no_token_returns_401(self, client):
        assert client.post("/api/hardening/integrations/register", json={}).status_code == 401

    def test_register_non_admin_returns_403(self, client):
        assert client.post("/api/hardening/integrations/register", json={},
                           headers=_user_headers()).status_code == 403

    def test_register_admin_reaches_handler(self, client):
        assert client.post("/api/hardening/integrations/register", json={},
                           headers=_admin_headers()).status_code not in (401, 403)

    def test_stats_no_token_returns_401(self, client):
        assert client.get("/api/hardening/integrations/stats").status_code == 401

    def test_stats_non_admin_returns_403(self, client):
        assert client.get("/api/hardening/integrations/stats",
                          headers=_user_headers()).status_code == 403

    def test_stats_admin_reaches_handler(self, client):
        assert client.get("/api/hardening/integrations/stats",
                          headers=_admin_headers()).status_code not in (401, 403)

    def test_options_preflight_always_allowed(self, client):
        for path in ["/api/hardening/integrations/register",
                     "/api/hardening/integrations/stats"]:
            r = client.options(path)
            assert r.status_code == 200, f"OPTIONS {path} returned {r.status_code}"


# ── Integrations admin ops (@_require_admin) ──────────────────────────────────

class TestIntegrationsAdminGated:

    def test_sync_no_token_returns_401(self, client):
        assert client.post("/api/integrations/sync", json={}).status_code == 401

    def test_sync_non_admin_returns_403(self, client):
        assert client.post("/api/integrations/sync", json={},
                           headers=_user_headers()).status_code == 403

    def test_sync_admin_reaches_handler(self, client):
        assert client.post("/api/integrations/sync", json={},
                           headers=_admin_headers()).status_code not in (401, 403)

    def test_create_partner_no_token_returns_401(self, client):
        assert client.post("/api/integrations/partners", json={}).status_code == 401

    def test_create_partner_non_admin_returns_403(self, client):
        assert client.post("/api/integrations/partners", json={},
                           headers=_user_headers()).status_code == 403

    def test_create_partner_admin_reaches_handler(self, client):
        assert client.post("/api/integrations/partners", json={},
                           headers=_admin_headers()).status_code not in (401, 403)

    def test_partner_dashboard_no_token_returns_401(self, client):
        assert client.get("/api/integrations/partners/some-partner/dashboard").status_code == 401

    def test_partner_dashboard_non_admin_returns_403(self, client):
        assert client.get("/api/integrations/partners/some-partner/dashboard",
                          headers=_user_headers()).status_code == 403

    def test_partner_dashboard_admin_reaches_handler(self, client):
        assert client.get("/api/integrations/partners/some-partner/dashboard",
                          headers=_admin_headers()).status_code not in (401, 403)

    def test_register_webhook_no_token_returns_401(self, client):
        assert client.post("/api/integrations/connector-webhooks", json={}).status_code == 401

    def test_register_webhook_non_admin_returns_403(self, client):
        assert client.post("/api/integrations/connector-webhooks", json={},
                           headers=_user_headers()).status_code == 403

    def test_register_webhook_admin_reaches_handler(self, client):
        assert client.post("/api/integrations/connector-webhooks", json={},
                           headers=_admin_headers()).status_code not in (401, 403)

    def test_options_preflight_always_allowed(self, client):
        for path in [
            "/api/integrations/sync",
            "/api/integrations/partners",
            "/api/integrations/partners/some-id/dashboard",
            "/api/integrations/connector-webhooks",
        ]:
            r = client.options(path)
            assert r.status_code == 200, f"OPTIONS {path} returned {r.status_code}"
