"""
test_professional_valuation_backend.py — Professional Valuation Phase B backend tests.

PVB01  create request returns request_id
PVB02  create validates required client_name
PVB03  create validates required property_type
PVB04  create validates required valuation_purpose
PVB05  list requests requires auth (returns 401 without token)
PVB06  detail requires auth (returns 401 without token)
PVB07  workflow route requires auth
PVB08  schema route requires auth
PVB09  request list returns safe metadata (no internal paths)
PVB10  detail returns certification_gate_summary
PVB11  certification_ready is false in Phase B
PVB12  detail returns permissions_summary with can_generate_certified=false
PVB13  transition route requires auth
PVB14  valid transition submitted -> intake_review succeeds
PVB15  invalid transition submitted -> certified_report_generated returns 422
PVB16  signed_pending_certification blocked without signature_gate_cleared
PVB17  approved_pending_signature blocked without peer_review_completed on record
PVB18  rejected -> archived succeeds
PVB19  event log is appended after transition
PVB20  no internal storage paths in create/list/detail responses
PVB21  evidence/source/report generation routes not exposed in Phase B
PVB22  workflow route returns all 16 expected statuses
PVB23  schema route returns required field definitions
PVB24  QA design outputs directory for Phase A exists
PVB25  simple valuation route still responds (not 404/405)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

# ── Path setup ────────────────────────────────────────────────────────────────

_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(str(_CORE))

from bridge_api import app                           # noqa: E402
from auth.tokens import generate_token               # noqa: E402
import professional_valuation_routes as _pvr        # noqa: E402

_TEST_SECRET = "pvr-phase-b-test-secret-32chars!!"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", _TEST_SECRET)
    monkeypatch.delenv("JWT_TTL_SECONDS", raising=False)


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _auth() -> dict:
    return {"Authorization": f"Bearer {generate_token('test-admin')}"}


_VALID_PAYLOAD: dict = {
    "client_name":       "أحمد محمد الاختبار",
    "property_type":     "شقة سكنية",
    "valuation_purpose": "قيمة سوقية",
    "city":              "القاهرة",
    "district":          "الزمالك",
}


def _create(client, extra=None):
    data = dict(_VALID_PAYLOAD)
    if extra:
        data.update(extra)
    return client.post(
        "/api/professional-valuation/requests",
        json=data,
        content_type="application/json",
    )


# ── PVB01–PVB04: Create ───────────────────────────────────────────────────────

def test_PVB01_create_returns_request_id(client):
    resp = _create(client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["ok"] is True
    assert body["request_id"].startswith("PVR-")
    assert body["status"] == "submitted"


def test_PVB02_create_validates_client_name(client):
    resp = _create(client, {"client_name": ""})
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["ok"] is False
    assert "client_name" in body["error"]


def test_PVB03_create_validates_property_type(client):
    resp = _create(client, {"property_type": ""})
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["ok"] is False
    assert "property_type" in body["error"]


def test_PVB04_create_validates_valuation_purpose(client):
    resp = _create(client, {"valuation_purpose": ""})
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["ok"] is False
    assert "valuation_purpose" in body["error"]


# ── PVB05–PVB08: Auth guards ─────────────────────────────────────────────────

def test_PVB05_list_requires_auth(client):
    resp = client.get("/api/professional-valuation/requests")
    assert resp.status_code == 401


def test_PVB06_detail_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.get(f"/api/professional-valuation/requests/{rid}")
    assert resp.status_code == 401


def test_PVB07_workflow_requires_auth(client):
    resp = client.get("/api/professional-valuation/workflow")
    assert resp.status_code == 401


def test_PVB08_schema_requires_auth(client):
    resp = client.get("/api/professional-valuation/schema")
    assert resp.status_code == 401


# ── PVB09–PVB12: List / Detail content ───────────────────────────────────────

def test_PVB09_list_returns_safe_metadata(client):
    _create(client)
    resp = client.get("/api/professional-valuation/requests", headers=_auth())
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    items = body["requests"]
    assert len(items) >= 1
    first = items[0]
    # No internal filesystem paths exposed
    for key, val in first.items():
        if isinstance(val, str):
            assert "instance" not in val or "jsonl" not in val, (
                f"Internal storage path leaked in key '{key}': {val}"
            )


def test_PVB10_detail_returns_certification_gate_summary(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.get(f"/api/professional-valuation/requests/{rid}", headers=_auth())
    assert resp.status_code == 200
    body = resp.get_json()
    assert "certification_gate_summary" in body


def test_PVB11_certification_ready_is_false_in_phase_b(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.get(f"/api/professional-valuation/requests/{rid}", headers=_auth())
    gate = resp.get_json()["certification_gate_summary"]
    assert gate["certification_ready"] is False


def test_PVB12_detail_returns_permissions_summary(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.get(f"/api/professional-valuation/requests/{rid}", headers=_auth())
    body = resp.get_json()
    assert "permissions_summary" in body
    perm = body["permissions_summary"]
    assert perm["can_generate_certified"] is False
    assert perm["can_transition"] is True


# ── PVB13–PVB19: Transitions ─────────────────────────────────────────────────

def test_PVB13_transition_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/transition",
        json={"target_status": "intake_review"},
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_PVB14_valid_transition_submitted_to_intake_review(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/transition",
        json={"target_status": "intake_review", "note": "مراجعة أولية"},
        content_type="application/json",
        headers=_auth(),
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["from_status"] == "submitted"
    assert body["to_status"] == "intake_review"


def test_PVB15_invalid_transition_to_certified_returns_422(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/transition",
        json={"target_status": "certified_report_generated"},
        content_type="application/json",
        headers=_auth(),
    )
    assert resp.status_code == 422
    body = resp.get_json()
    assert body["ok"] is False
    assert body["error_code"] == "certified_blocked"


def test_PVB16_signed_pending_blocked_without_signature_gate(client):
    """approved_pending_signature -> signed_pending_certification
    must fail without signature_gate_cleared=True in request body."""
    rid = _create(client).get_json()["request_id"]
    # Push record to approved_pending_signature with peer_review_completed
    _pvr._update_pvr(rid, {
        "status": "approved_pending_signature",
        "peer_review_completed": True,
    })
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/transition",
        json={"target_status": "signed_pending_certification"},
        content_type="application/json",
        headers=_auth(),
    )
    assert resp.status_code == 422
    body = resp.get_json()
    assert body["ok"] is False
    assert body["error_code"] == "gate_blocked"


def test_PVB17_approved_pending_blocked_without_peer_review(client):
    """peer_review_in_progress -> approved_pending_signature
    must fail without peer_review_completed=True on record."""
    rid = _create(client).get_json()["request_id"]
    _pvr._update_pvr(rid, {
        "status": "peer_review_in_progress",
        "peer_review_completed": False,
    })
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/transition",
        json={"target_status": "approved_pending_signature"},
        content_type="application/json",
        headers=_auth(),
    )
    assert resp.status_code == 422
    body = resp.get_json()
    assert body["ok"] is False
    assert body["error_code"] == "gate_blocked"


def test_PVB18_rejected_to_archived_succeeds(client):
    rid = _create(client).get_json()["request_id"]
    _pvr._update_pvr(rid, {"status": "rejected"})
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/transition",
        json={"target_status": "archived"},
        content_type="application/json",
        headers=_auth(),
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["to_status"] == "archived"


def test_PVB19_event_log_appended_after_transition(client):
    rid = _create(client).get_json()["request_id"]
    client.post(
        f"/api/professional-valuation/requests/{rid}/transition",
        json={"target_status": "intake_review", "note": "test note"},
        content_type="application/json",
        headers=_auth(),
    )
    events = _pvr._read_events(rid)
    assert len(events) >= 2, f"Expected ≥2 events (create + transition), got {len(events)}"
    transition_events = [e for e in events if e["action"] == "transition"]
    assert len(transition_events) >= 1
    assert transition_events[0]["to_status"] == "intake_review"


# ── PVB20–PVB25: Safety / completeness ───────────────────────────────────────

def test_PVB20_no_internal_paths_in_create_response(client):
    resp = _create(client)
    body_str = resp.get_data(as_text=True)
    # Must not expose the JSONL storage path
    assert "professional_valuation/requests.jsonl" not in body_str
    assert "instance/professional_valuation" not in body_str


def test_PVB21_unimplemented_routes_not_exposed_in_phase_b(client):
    """Evidence/source/report generation endpoints must not exist yet."""
    test_id = "PVR-20260629-XXXX"
    for path in [
        f"/api/professional-valuation/requests/{test_id}/evidence",
        f"/api/professional-valuation/requests/{test_id}/sources",
        f"/api/professional-valuation/requests/{test_id}/report",
        f"/api/professional-valuation/requests/{test_id}/certified-report",
    ]:
        resp = client.get(path)
        assert resp.status_code in (404, 405), (
            f"Unexpected route exposed: GET {path} → {resp.status_code}"
        )


def test_PVB22_workflow_returns_all_16_expected_statuses(client):
    resp = client.get("/api/professional-valuation/workflow", headers=_auth())
    assert resp.status_code == 200
    body = resp.get_json()
    statuses = body["workflow"]["statuses"]
    assert len(statuses) == 16
    for s in ("submitted", "intake_review", "certified_report_generated", "archived"):
        assert s in statuses, f"Status missing from workflow: {s}"


def test_PVB23_schema_returns_required_field_definitions(client):
    resp = client.get("/api/professional-valuation/schema", headers=_auth())
    assert resp.status_code == 200
    body = resp.get_json()
    schema = body["schema"]
    req_fields = [f["field"] for f in schema["required_fields"]]
    assert "client_name"       in req_fields
    assert "property_type"     in req_fields
    assert "valuation_purpose" in req_fields


def test_PVB24_qa_design_outputs_dir_exists():
    """QA design output directory for Phase A must exist on disk."""
    qa_dir = (
        _CORE / "instance" / "manual_review_outputs"
        / "professional_valuation_phase_a_design"
    )
    assert qa_dir.exists(), (
        f"Phase A QA output directory not found: {qa_dir}"
    )


def test_PVB25_simple_valuation_route_still_works(client):
    """The simple-valuation draft-pdf route must still be registered."""
    resp = client.post(
        "/api/simple-valuation/draft-pdf",
        json={"property_type": "شقة", "area": 120},
        content_type="application/json",
    )
    assert resp.status_code not in (404, 405), (
        f"simple-valuation route broken: {resp.status_code}"
    )
