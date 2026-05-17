"""
SEC-003 security tests for enterprise tenant and SaaS tenant management endpoints.

All 16 endpoints require admin authorization:
  - No token → 401
  - Non-admin token → 403
  - Admin token → allowed (passes to handler)

Tests follow the pattern established in test_bridge_api_admin_audit.py.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from unittest.mock import MagicMock, patch

_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(str(_CORE))

from bridge_api import app  # noqa: E402
from auth.tokens import generate_token  # noqa: E402

_ADMIN_USER = "admin-test-user"
_NON_ADMIN   = "regular-user"
_TEST_SECRET = "test-secret-for-enterprise-security-tests"


def _auth(user: str) -> dict:
    return {"Authorization": f"Bearer {generate_token(user)}"}


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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _assert_401(resp):
    assert resp.status_code == 401
    body = resp.get_json() or {}
    assert body.get("status") == "unauthorized"


def _assert_403(resp):
    assert resp.status_code == 403
    body = resp.get_json() or {}
    assert body.get("status") == "forbidden"


def _assert_not_401_or_403(resp):
    """Admin request reached the handler (any response except 401/403)."""
    assert resp.status_code not in (401, 403), (
        f"Expected handler response, got {resp.status_code}: {resp.get_json()}"
    )


# ── Enterprise tenant endpoints ───────────────────────────────────────────────

class TestEnterpriseTenantAuth:
    """POST /api/enterprise/tenant — create tenant."""

    def test_no_token_returns_401(self, client):
        _assert_401(client.post("/api/enterprise/tenant", json={}))

    def test_non_admin_returns_403(self, client):
        _assert_403(client.post("/api/enterprise/tenant", json={}, headers=_auth(_NON_ADMIN)))

    def test_admin_reaches_handler(self, client):
        resp = client.post(
            "/api/enterprise/tenant",
            json={"organization_name": "Test Org", "country": "EG"},
            headers=_auth(_ADMIN_USER),
        )
        _assert_not_401_or_403(resp)


class TestEnterpriseTenantGetAuth:
    """GET /api/enterprise/tenant/<tenant_id> — fetch tenant."""

    def test_no_token_returns_401(self, client):
        _assert_401(client.get("/api/enterprise/tenant/t-001"))

    def test_non_admin_returns_403(self, client):
        _assert_403(client.get("/api/enterprise/tenant/t-001", headers=_auth(_NON_ADMIN)))

    def test_admin_reaches_handler(self, client):
        mock_tm = MagicMock()
        mock_tm.get_tenant_summary.return_value = None
        with patch("bridge_api._tenant_manager", mock_tm):
            resp = client.get("/api/enterprise/tenant/t-nonexistent", headers=_auth(_ADMIN_USER))
        # Handler returns 404 for missing tenant — that's the handler responding
        _assert_not_401_or_403(resp)


class TestEnterpriseAddUserAuth:
    """POST /api/enterprise/tenant/<tenant_id>/user — add user."""

    def test_no_token_returns_401(self, client):
        _assert_401(client.post("/api/enterprise/tenant/t-001/user", json={}))

    def test_non_admin_returns_403(self, client):
        _assert_403(client.post(
            "/api/enterprise/tenant/t-001/user",
            json={},
            headers=_auth(_NON_ADMIN),
        ))

    def test_admin_reaches_handler(self, client):
        resp = client.post(
            "/api/enterprise/tenant/t-001/user",
            json={"email": "test@example.com", "role": "admin"},
            headers=_auth(_ADMIN_USER),
        )
        _assert_not_401_or_403(resp)


class TestEnterpriseLicenseAuth:
    """GET /api/enterprise/tenant/<tenant_id>/license — validate subscription."""

    def test_no_token_returns_401(self, client):
        _assert_401(client.get("/api/enterprise/tenant/t-001/license"))

    def test_non_admin_returns_403(self, client):
        _assert_403(client.get(
            "/api/enterprise/tenant/t-001/license", headers=_auth(_NON_ADMIN)
        ))

    def test_admin_reaches_handler(self, client):
        mock_tm = MagicMock()
        mock_tm.get_tenant.return_value = None
        with patch("bridge_api._tenant_manager", mock_tm):
            resp = client.get(
                "/api/enterprise/tenant/t-nonexistent/license", headers=_auth(_ADMIN_USER)
            )
        _assert_not_401_or_403(resp)


class TestEnterpriseAuditAuth:
    """GET /api/enterprise/tenant/<tenant_id>/audit — audit trail."""

    def test_no_token_returns_401(self, client):
        _assert_401(client.get("/api/enterprise/tenant/t-001/audit"))

    def test_non_admin_returns_403(self, client):
        _assert_403(client.get(
            "/api/enterprise/tenant/t-001/audit", headers=_auth(_NON_ADMIN)
        ))

    def test_admin_reaches_handler(self, client):
        mock_tm = MagicMock()
        mock_tm.get_tenant.return_value = None
        with patch("bridge_api._tenant_manager", mock_tm):
            resp = client.get(
                "/api/enterprise/tenant/t-nonexistent/audit", headers=_auth(_ADMIN_USER)
            )
        _assert_not_401_or_403(resp)


# ── SaaS tenant endpoints ─────────────────────────────────────────────────────

class TestSaasCreateTenantAuth:
    """POST /api/saas/tenants."""

    def test_no_token_returns_401(self, client):
        _assert_401(client.post("/api/saas/tenants", json={}))

    def test_non_admin_returns_403(self, client):
        _assert_403(client.post("/api/saas/tenants", json={}, headers=_auth(_NON_ADMIN)))

    def test_admin_reaches_handler(self, client):
        resp = client.post(
            "/api/saas/tenants",
            json={"name": "TestCo", "domain": "testco.example.com"},
            headers=_auth(_ADMIN_USER),
        )
        _assert_not_401_or_403(resp)


class TestSaasListTenantsAuth:
    """GET /api/saas/tenants."""

    def test_no_token_returns_401(self, client):
        _assert_401(client.get("/api/saas/tenants"))

    def test_non_admin_returns_403(self, client):
        _assert_403(client.get("/api/saas/tenants", headers=_auth(_NON_ADMIN)))

    def test_admin_reaches_handler(self, client):
        resp = client.get("/api/saas/tenants", headers=_auth(_ADMIN_USER))
        _assert_not_401_or_403(resp)


class TestSaasGetTenantAuth:
    """GET /api/saas/tenants/<tenant_id>."""

    def test_no_token_returns_401(self, client):
        _assert_401(client.get("/api/saas/tenants/t-001"))

    def test_non_admin_returns_403(self, client):
        _assert_403(client.get("/api/saas/tenants/t-001", headers=_auth(_NON_ADMIN)))

    def test_admin_reaches_handler(self, client):
        resp = client.get("/api/saas/tenants/t-nonexistent", headers=_auth(_ADMIN_USER))
        _assert_not_401_or_403(resp)


class TestSaasAddUserAuth:
    """POST /api/saas/tenants/<tenant_id>/users."""

    def test_no_token_returns_401(self, client):
        _assert_401(client.post("/api/saas/tenants/t-001/users", json={}))

    def test_non_admin_returns_403(self, client):
        _assert_403(client.post(
            "/api/saas/tenants/t-001/users", json={}, headers=_auth(_NON_ADMIN)
        ))

    def test_admin_reaches_handler(self, client):
        resp = client.post(
            "/api/saas/tenants/t-001/users",
            json={"email": "user@example.com"},
            headers=_auth(_ADMIN_USER),
        )
        _assert_not_401_or_403(resp)


class TestSaasSubscriptionAuth:
    """PUT /api/saas/tenants/<tenant_id>/subscription."""

    def test_no_token_returns_401(self, client):
        _assert_401(client.put("/api/saas/tenants/t-001/subscription", json={}))

    def test_non_admin_returns_403(self, client):
        _assert_403(client.put(
            "/api/saas/tenants/t-001/subscription", json={}, headers=_auth(_NON_ADMIN)
        ))

    def test_admin_reaches_handler(self, client):
        resp = client.put(
            "/api/saas/tenants/t-001/subscription",
            json={"tier": "professional"},
            headers=_auth(_ADMIN_USER),
        )
        _assert_not_401_or_403(resp)


class TestSaasSuspendAuth:
    """POST /api/saas/tenants/<tenant_id>/suspend."""

    def test_no_token_returns_401(self, client):
        _assert_401(client.post("/api/saas/tenants/t-001/suspend", json={}))

    def test_non_admin_returns_403(self, client):
        _assert_403(client.post(
            "/api/saas/tenants/t-001/suspend", json={}, headers=_auth(_NON_ADMIN)
        ))

    def test_admin_reaches_handler(self, client):
        resp = client.post(
            "/api/saas/tenants/t-001/suspend",
            json={"reason": "test"},
            headers=_auth(_ADMIN_USER),
        )
        _assert_not_401_or_403(resp)


class TestSaasReactivateAuth:
    """POST /api/saas/tenants/<tenant_id>/reactivate."""

    def test_no_token_returns_401(self, client):
        _assert_401(client.post("/api/saas/tenants/t-001/reactivate", json={}))

    def test_non_admin_returns_403(self, client):
        _assert_403(client.post(
            "/api/saas/tenants/t-001/reactivate", json={}, headers=_auth(_NON_ADMIN)
        ))

    def test_admin_reaches_handler(self, client):
        resp = client.post(
            "/api/saas/tenants/t-001/reactivate", json={}, headers=_auth(_ADMIN_USER)
        )
        _assert_not_401_or_403(resp)


class TestSaasRecordUsageAuth:
    """POST /api/saas/tenants/<tenant_id>/billing/usage."""

    def test_no_token_returns_401(self, client):
        _assert_401(client.post("/api/saas/tenants/t-001/billing/usage", json={}))

    def test_non_admin_returns_403(self, client):
        _assert_403(client.post(
            "/api/saas/tenants/t-001/billing/usage", json={}, headers=_auth(_NON_ADMIN)
        ))

    def test_admin_reaches_handler(self, client):
        resp = client.post(
            "/api/saas/tenants/t-001/billing/usage",
            json={"metric": "api_call", "quantity": 1},
            headers=_auth(_ADMIN_USER),
        )
        _assert_not_401_or_403(resp)


class TestSaasGenerateInvoiceAuth:
    """POST /api/saas/tenants/<tenant_id>/billing/invoice."""

    def test_no_token_returns_401(self, client):
        _assert_401(client.post("/api/saas/tenants/t-001/billing/invoice", json={}))

    def test_non_admin_returns_403(self, client):
        _assert_403(client.post(
            "/api/saas/tenants/t-001/billing/invoice", json={}, headers=_auth(_NON_ADMIN)
        ))

    def test_admin_reaches_handler(self, client):
        resp = client.post(
            "/api/saas/tenants/t-001/billing/invoice", json={}, headers=_auth(_ADMIN_USER)
        )
        _assert_not_401_or_403(resp)


class TestSaasDashboardAuth:
    """GET /api/saas/tenants/<tenant_id>/dashboard."""

    def test_no_token_returns_401(self, client):
        _assert_401(client.get("/api/saas/tenants/t-001/dashboard"))

    def test_non_admin_returns_403(self, client):
        _assert_403(client.get(
            "/api/saas/tenants/t-001/dashboard", headers=_auth(_NON_ADMIN)
        ))

    def test_admin_reaches_handler(self, client):
        resp = client.get(
            "/api/saas/tenants/t-001/dashboard", headers=_auth(_ADMIN_USER)
        )
        _assert_not_401_or_403(resp)


class TestSaasPlatformStatsAuth:
    """GET /api/saas/stats."""

    def test_no_token_returns_401(self, client):
        _assert_401(client.get("/api/saas/stats"))

    def test_non_admin_returns_403(self, client):
        _assert_403(client.get("/api/saas/stats", headers=_auth(_NON_ADMIN)))

    def test_admin_reaches_handler(self, client):
        resp = client.get("/api/saas/stats", headers=_auth(_ADMIN_USER))
        _assert_not_401_or_403(resp)


# ── Regression: unrelated public endpoints unaffected ─────────────────────────

class TestUnrelatedEndpointsUnaffected:
    """Auth changes must not break public endpoints."""

    def test_health_still_public(self, client):
        resp = client.get("/api/advisor/health")
        assert resp.status_code == 200

    def test_valuation_still_accessible(self, client):
        # POST /api/valuation — no auth required, just needs valid body
        resp = client.post(
            "/api/valuation",
            json={
                "location": "القاهرة",
                "area": 100,
                "property_type": "شقة سكنية",
                "price_per_meter": 10000,
            },
        )
        assert resp.status_code != 401
        assert resp.status_code != 403
