"""
test_phase_15_2_e2e.py — Phase 15.2 Enterprise Audit Trail (12 tests)

Tests:
  01  AuditAction enum values present
  02  AuditEvent dataclass defaults and to_dict()
  03  AuditLog.record() + count_by_tenant() increments
  04  AuditLog.get_by_tenant() returns newest-first
  05  AuditLog.get_by_user() filters to matching user_id only
  06  AuditLog.count_by_action() filters by action string
  07  Tenant isolation — events from one tenant invisible to another
  08  details dict roundtrips through JSON correctly
  09  API: POST tenant → TENANT_CREATED event in audit trail
  10  API: POST user → USER_ADDED event in audit trail
  11  GET /api/enterprise/tenant/<id>/audit — event list, newest-first
  12  GET /api/enterprise/tenant/<bad-id>/audit — 404
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

_CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_CORE))
os.chdir(str(_CORE))

os.environ.setdefault("JWT_SECRET", "test-secret-saas-suite")
os.environ.setdefault("ADMIN_USER_IDS", "test-admin-saas")

from database.audit_log import AuditAction, AuditEvent, AuditLog

import bridge_api
from auth.tokens import generate_token as _gen_token
_client = bridge_api.app.test_client()
_ADMIN_HDR = {"Authorization": f"Bearer {_gen_token('test-admin-saas')}"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fresh_log() -> AuditLog:
    db = tempfile.mktemp(suffix=".db")
    return AuditLog(db_path=db)

def _event(tenant_id="t1", action=AuditAction.TENANT_CREATED,
           resource_type="tenant", resource_id="r1",
           user_id="", details=None) -> AuditEvent:
    return AuditEvent(
        tenant_id=tenant_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        details=details or {},
    )

def _post(path, body):
    return _client.post(path, data=json.dumps(body), content_type="application/json",
                        headers=_ADMIN_HDR)

def _get(path):
    return _client.get(path, headers=_ADMIN_HDR)

def _json(resp):
    return json.loads(resp.data)


# ── Unit tests ────────────────────────────────────────────────────────────────

def test_01_audit_action_enum_values():
    expected = {
        "TENANT_CREATED", "USER_ADDED", "USER_DEACTIVATED",
        "VALUATION_CREATED", "BATCH_SUBMITTED", "REPORT_GENERATED",
        "WEBHOOK_FIRED", "LICENSE_CHECKED",
    }
    actual = {a.value for a in AuditAction}
    assert expected == actual


def test_02_audit_event_defaults_and_to_dict():
    e = AuditEvent(
        tenant_id="t1", action=AuditAction.USER_ADDED,
        resource_type="user", resource_id="u1",
    )
    assert e.event_id          # non-empty uuid
    assert e.timestamp         # non-empty ISO string
    assert e.user_id    == ""
    assert e.ip_address == ""
    assert e.details    == {}

    d = e.to_dict()
    assert d["tenant_id"]     == "t1"
    assert d["action"]        == "USER_ADDED"
    assert d["resource_type"] == "user"
    assert d["resource_id"]   == "u1"
    assert d["event_id"]      == e.event_id


def test_03_record_and_count_by_tenant():
    al = _fresh_log()
    assert al.count_by_tenant("t1") == 0
    al.record(_event("t1"))
    assert al.count_by_tenant("t1") == 1
    al.record(_event("t1"))
    assert al.count_by_tenant("t1") == 2


def test_04_get_by_tenant_newest_first():
    al = _fresh_log()
    for resource_id in ["r1", "r2", "r3"]:
        al.record(_event("t1", resource_id=resource_id))
    rows = al.get_by_tenant("t1")
    assert len(rows) == 3
    ids = [r["id"] for r in rows]
    assert ids == sorted(ids, reverse=True)


def test_05_get_by_user_filters():
    al = _fresh_log()
    al.record(_event("t1", user_id="user-A", resource_id="r1"))
    al.record(_event("t1", user_id="user-B", resource_id="r2"))
    al.record(_event("t1", user_id="user-A", resource_id="r3"))

    rows_a = al.get_by_user("t1", "user-A")
    assert len(rows_a) == 2
    assert all(r["user_id"] == "user-A" for r in rows_a)

    rows_b = al.get_by_user("t1", "user-B")
    assert len(rows_b) == 1


def test_06_count_by_action():
    al = _fresh_log()
    al.record(_event("t1", action=AuditAction.TENANT_CREATED))
    al.record(_event("t1", action=AuditAction.USER_ADDED))
    al.record(_event("t1", action=AuditAction.USER_ADDED))
    assert al.count_by_action("t1", AuditAction.TENANT_CREATED) == 1
    assert al.count_by_action("t1", AuditAction.USER_ADDED)     == 2
    assert al.count_by_action("t1", AuditAction.BATCH_SUBMITTED) == 0


def test_07_tenant_isolation():
    al = _fresh_log()
    al.record(_event("tenant-X"))
    al.record(_event("tenant-X"))
    al.record(_event("tenant-Y"))
    assert al.count_by_tenant("tenant-X") == 2
    assert al.count_by_tenant("tenant-Y") == 1
    rows_x = al.get_by_tenant("tenant-X")
    assert all(r["tenant_id"] == "tenant-X" for r in rows_x)


def test_08_details_json_roundtrip():
    al = _fresh_log()
    original_details = {
        "organization_name": "Acme Corp",
        "country":           "Egypt",
        "tier":              "enterprise",
        "nested":            {"key": [1, 2, 3]},
    }
    e = AuditEvent(
        tenant_id="t1", action=AuditAction.TENANT_CREATED,
        resource_type="tenant", resource_id="t1",
        details=original_details,
    )
    al.record(e)
    rows = al.get_by_tenant("t1")
    assert len(rows) == 1
    assert rows[0]["details"] == original_details


# ── API integration tests ─────────────────────────────────────────────────────

def test_09_api_create_tenant_records_audit():
    resp = _post("/api/enterprise/tenant", {
        "organization_name": "Audit Test Org",
        "country":           "Egypt",
        "subscription_tier": "professional",
    })
    assert resp.status_code == 201
    tid = _json(resp)["tenant"]["tenant_id"]

    audit_resp = _get(f"/api/enterprise/tenant/{tid}/audit")
    assert audit_resp.status_code == 200
    body = _json(audit_resp)
    assert body["event_count"] >= 1
    actions = [e["action"] for e in body["events"]]
    assert "TENANT_CREATED" in actions


def test_10_api_add_user_records_audit():
    r   = _post("/api/enterprise/tenant", {
        "organization_name": "UserAudit Org", "country": "UAE"
    })
    tid = _json(r)["tenant"]["tenant_id"]

    _post(f"/api/enterprise/tenant/{tid}/user", {
        "email": "audit@user.com", "full_name": "Audit User", "role": "operator"
    })

    audit_resp = _get(f"/api/enterprise/tenant/{tid}/audit")
    body = _json(audit_resp)
    actions = [e["action"] for e in body["events"]]
    assert "USER_ADDED" in actions

    # details captured email + role
    user_events = [e for e in body["events"] if e["action"] == "USER_ADDED"]
    assert user_events[0]["details"]["email"] == "audit@user.com"
    assert user_events[0]["details"]["role"]  == "operator"


def test_11_api_audit_event_list_newest_first():
    r   = _post("/api/enterprise/tenant", {
        "organization_name": "Order Test Org", "country": "Saudi Arabia"
    })
    tid = _json(r)["tenant"]["tenant_id"]

    # Add two users → two USER_ADDED events
    for i in range(2):
        _post(f"/api/enterprise/tenant/{tid}/user", {
            "email": f"u{i}@order.com", "full_name": f"User {i}", "role": "analyst"
        })

    audit_resp = _get(f"/api/enterprise/tenant/{tid}/audit")
    body = _json(audit_resp)
    assert body["status"]      == "success"
    assert body["event_count"] >= 3          # TENANT_CREATED + 2× USER_ADDED
    ids = [e["id"] for e in body["events"]]
    assert ids == sorted(ids, reverse=True)  # newest first


def test_12_api_audit_unknown_tenant():
    resp = _get("/api/enterprise/tenant/ghost-org-xyz/audit")
    assert resp.status_code == 404
    assert _json(resp)["status"] == "error"


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
