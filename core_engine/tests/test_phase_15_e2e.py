"""
test_phase_15_e2e.py — Phase 15.1 Enterprise API routes (12 tests)

Tests:
  01  POST /api/enterprise/tenant — create org → 201, tenant dict returned
  02  POST /api/enterprise/tenant — missing organization_name → 400
  03  POST /api/enterprise/tenant — missing country → 400
  04  GET  /api/enterprise/tenant/<id> — fetch summary (users list, user_count)
  05  GET  /api/enterprise/tenant/<bad-id> — unknown tenant → 404
  06  POST /api/enterprise/tenant/<id>/user — add user → 201, user dict
  07  POST /api/enterprise/tenant/<id>/user — invalid role → 400
  08  POST /api/enterprise/tenant/<id>/user — unknown tenant → 404
  09  POST /api/enterprise/tenant/<id>/user — missing email → 400
  10  GET  /api/enterprise/tenant/<id>/license — valid subscription response
  11  GET  /api/enterprise/tenant/<bad-id>/license — unknown tenant → 404
  12  Full round-trip: create → add 2 users → get summary → check license
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_CORE))
os.chdir(str(_CORE))

os.environ.setdefault("JWT_SECRET", "test-secret-saas-suite")
os.environ.setdefault("ADMIN_USER_IDS", "test-admin-saas")

import bridge_api
from auth.tokens import generate_token as _gen_token

_client = bridge_api.app.test_client()
_ADMIN_HDR = {"Authorization": f"Bearer {_gen_token('test-admin-saas')}"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _post(path: str, body: dict):
    return _client.post(path, data=json.dumps(body), content_type="application/json",
                        headers=_ADMIN_HDR)

def _get(path: str):
    return _client.get(path, headers=_ADMIN_HDR)

def _json(resp) -> dict:
    return json.loads(resp.data)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_01_create_tenant_success():
    resp = _post("/api/enterprise/tenant", {
        "organization_name": "Alpha Realty",
        "country":           "Egypt",
        "subscription_tier": "enterprise",
    })
    assert resp.status_code == 201
    body = _json(resp)
    assert body["status"] == "success"
    t = body["tenant"]
    assert t["organization_name"] == "Alpha Realty"
    assert t["country"]           == "Egypt"
    assert t["subscription_tier"] == "enterprise"
    assert t["tenant_id"]


def test_02_create_tenant_missing_name():
    resp = _post("/api/enterprise/tenant", {"country": "Egypt"})
    assert resp.status_code == 400
    assert "organization_name" in _json(resp)["message"]


def test_03_create_tenant_missing_country():
    resp = _post("/api/enterprise/tenant", {"organization_name": "Acme"})
    assert resp.status_code == 400
    assert "country" in _json(resp)["message"]


def test_04_get_tenant_summary():
    # Create tenant first
    r = _post("/api/enterprise/tenant", {
        "organization_name": "Beta Props",
        "country": "UAE",
        "subscription_tier": "professional",
    })
    tid = _json(r)["tenant"]["tenant_id"]

    # Add a user
    _post(f"/api/enterprise/tenant/{tid}/user", {
        "email": "u@beta.com", "full_name": "Ali U", "role": "analyst"
    })

    resp = _get(f"/api/enterprise/tenant/{tid}")
    assert resp.status_code == 200
    body = _json(resp)
    assert body["status"]     == "success"
    assert body["user_count"] == 1
    assert len(body["users"]) == 1
    assert body["tenant"]["organization_name"] == "Beta Props"


def test_05_get_tenant_not_found():
    resp = _get("/api/enterprise/tenant/non-existent-id-xyz")
    assert resp.status_code == 404
    assert _json(resp)["status"] == "error"


def test_06_add_user_success():
    r   = _post("/api/enterprise/tenant", {
        "organization_name": "Gamma RE", "country": "Saudi Arabia"
    })
    tid = _json(r)["tenant"]["tenant_id"]

    resp = _post(f"/api/enterprise/tenant/{tid}/user", {
        "email":     "admin@gamma.com",
        "full_name": "Sami Admin",
        "role":      "admin",
    })
    assert resp.status_code == 201
    u = _json(resp)["user"]
    assert u["email"]     == "admin@gamma.com"
    assert u["role"]      == "admin"
    assert u["user_id"]
    assert u["is_active"] is True


def test_07_add_user_invalid_role():
    r   = _post("/api/enterprise/tenant", {
        "organization_name": "Delta RE", "country": "Kuwait"
    })
    tid = _json(r)["tenant"]["tenant_id"]

    resp = _post(f"/api/enterprise/tenant/{tid}/user", {
        "email": "x@delta.com", "full_name": "X", "role": "superadmin"
    })
    assert resp.status_code == 400
    assert "role" in _json(resp)["message"].lower() or "Invalid" in _json(resp)["message"]


def test_08_add_user_tenant_not_found():
    resp = _post("/api/enterprise/tenant/no-such-tenant/user", {
        "email": "x@x.com", "full_name": "X", "role": "viewer"
    })
    assert resp.status_code == 404


def test_09_add_user_missing_email():
    r   = _post("/api/enterprise/tenant", {
        "organization_name": "Epsilon RE", "country": "Bahrain"
    })
    tid = _json(r)["tenant"]["tenant_id"]
    resp = _post(f"/api/enterprise/tenant/{tid}/user", {
        "full_name": "No Email", "role": "viewer"
    })
    assert resp.status_code == 400
    assert "email" in _json(resp)["message"]


def test_10_license_valid_subscription():
    r   = _post("/api/enterprise/tenant", {
        "organization_name": "Zeta Corp",
        "country":           "Jordan",
        "subscription_tier": "enterprise",
    })
    tid = _json(r)["tenant"]["tenant_id"]

    resp = _get(f"/api/enterprise/tenant/{tid}/license")
    assert resp.status_code == 200
    body = _json(resp)
    assert body["status"]   == "success"
    assert body["is_valid"] is True
    assert body["tier"]     == "enterprise"
    f = body["features"]
    assert f["max_valuations_per_month"]    == 50_000
    assert f["webhooks_enabled"]            is True
    assert f["max_properties_in_portfolio"] == 10_000


def test_11_license_tenant_not_found():
    resp = _get("/api/enterprise/tenant/ghost-tenant/license")
    assert resp.status_code == 404
    assert _json(resp)["status"] == "error"


def test_12_full_roundtrip():
    # 1. Create
    r   = _post("/api/enterprise/tenant", {
        "organization_name": "Omega Valuations",
        "country":           "Egypt",
        "subscription_tier": "professional",
    })
    assert r.status_code == 201
    tid = _json(r)["tenant"]["tenant_id"]

    # 2. Add two users
    r1 = _post(f"/api/enterprise/tenant/{tid}/user", {
        "email": "ceo@omega.com", "full_name": "Hana CEO", "role": "admin"
    })
    r2 = _post(f"/api/enterprise/tenant/{tid}/user", {
        "email": "ops@omega.com", "full_name": "Karim Ops", "role": "operator"
    })
    assert r1.status_code == 201
    assert r2.status_code == 201

    # 3. Summary reflects both users
    summary_resp = _get(f"/api/enterprise/tenant/{tid}")
    assert summary_resp.status_code == 200
    summary = _json(summary_resp)
    assert summary["user_count"] == 2
    emails = {u["email"] for u in summary["users"]}
    assert "ceo@omega.com" in emails
    assert "ops@omega.com" in emails

    # 4. License shows professional limits
    lic_resp = _get(f"/api/enterprise/tenant/{tid}/license")
    assert lic_resp.status_code == 200
    lic = _json(lic_resp)
    assert lic["tier"]     == "professional"
    assert lic["is_valid"] is True
    assert lic["features"]["max_valuations_per_month"] == 500
    assert lic["features"]["api_access"] is True


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for fn in tests:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
            passed += 1
        except Exception as exc:
            import traceback
            print(f"  FAIL  {fn.__name__}: {exc}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed}/{passed + failed} tests passed")
