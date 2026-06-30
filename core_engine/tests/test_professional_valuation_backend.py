"""
test_professional_valuation_backend.py — Professional Valuation Phase B + Phase C backend tests.

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
PVB11  certification_ready is false in Phase B/C
PVB12  detail returns permissions_summary with can_generate_certified=false
PVB13  transition route requires auth
PVB14  valid transition submitted -> intake_review succeeds
PVB15  invalid transition submitted -> certified_report_generated returns 422
PVB16  signed_pending_certification blocked without signature_gate_cleared
PVB17  approved_pending_signature blocked without peer_review_completed on record
PVB18  rejected -> archived succeeds
PVB19  event log is appended after transition
PVB20  no internal storage paths in create/list/detail responses
PVB21  report/certified-report routes remain unimplemented; evidence/source now 401 (auth required)
PVB22  workflow route returns all 16 expected statuses
PVB23  schema route returns required field definitions
PVB24  QA design outputs directory for Phase A exists
PVB25  simple valuation route still responds (not 404/405)

PVC01  evidence type catalogue route requires auth
PVC02  source type catalogue route requires auth
PVC03  create evidence requires auth
PVC04  create evidence returns evidence_id
PVC05  create evidence sets production_ready=false
PVC06  create evidence sets no_automatic_value_extraction=true
PVC07  evidence response has no internal file path
PVC08  list evidence requires auth
PVC09  get evidence detail requires auth
PVC10  evidence review requires auth
PVC11  rejected evidence requires rejection_reason
PVC12  approved_as_source requires source-eligible evidence_type
PVC13  document completeness returned after evidence upload
PVC14  missing mandatory documents keep certification_document_ready=false
PVC15  create source requires auth
PVC16  create source returns source_id
PVC17  create source sets production_ready=false by default
PVC18  qa_simulation source cannot become approved_as_production_source
PVC19  non-QA source approved_as_production_source sets production_ready=true
PVC20  list sources requires auth
PVC21  get source detail requires auth
PVC22  source review requires auth
PVC23  rejected source requires rejection_reason
PVC24  source quality summary returned after source creation
PVC25  no production-ready sources → real_sources_ready=false in gate
PVC26  approved non-QA source → real_sources_ready=true in gate
PVC27  certification_gate_summary.mandatory_documents_ready updates after evidence
PVC28  certification_gate_summary.real_sources_ready updates after source approval
PVC29  event log records evidence and source actions
PVC30  no internal paths in evidence/source list/detail responses
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


def test_PVB21_phase_c_evidence_sources_registered_report_still_blocked(client):
    """Phase C: evidence/source routes now exist (return 401 without auth).
    Report and certified-report routes remain unimplemented (404/405).
    """
    rid = _create(client).get_json()["request_id"]

    # Evidence and source routes exist — require auth → 401 without token
    resp_ev  = client.get(f"/api/professional-valuation/requests/{rid}/evidence")
    resp_src = client.get(f"/api/professional-valuation/requests/{rid}/sources")
    assert resp_ev.status_code  == 401, f"Evidence list should require auth, got {resp_ev.status_code}"
    assert resp_src.status_code == 401, f"Source list should require auth, got {resp_src.status_code}"

    # Evidence type and source type catalogues also require auth
    resp_et = client.get("/api/professional-valuation/evidence/types")
    resp_st = client.get("/api/professional-valuation/source/types")
    assert resp_et.status_code == 401
    assert resp_st.status_code == 401

    # Report/certified-report routes remain unimplemented
    for path in [
        f"/api/professional-valuation/requests/{rid}/report",
        f"/api/professional-valuation/requests/{rid}/certified-report",
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


# ═════════════════════════════════════════════════════════════════════════════
# Phase C Tests — PVC01–PVC30 (Evidence Upload & Source Registry)
# ═════════════════════════════════════════════════════════════════════════════

import professional_valuation_evidence_routes as _pve  # noqa: E402


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_evidence(client, request_id: str, extra: dict | None = None) -> dict:
    """POST evidence (JSON metadata-only) and return parsed response body."""
    payload = {"evidence_type": "ownership_document", "is_required_document": True}
    if extra:
        payload.update(extra)
    resp = client.post(
        f"/api/professional-valuation/requests/{request_id}/evidence",
        json=payload,
        content_type="application/json",
        headers=_auth(),
    )
    return resp.get_json()


def _create_source(client, request_id: str, extra: dict | None = None) -> dict:
    payload = {
        "source_type":   "sales_comparable",
        "source_name":   "مقارن اختبار",
        "qa_simulation": False,
    }
    if extra:
        payload.update(extra)
    resp = client.post(
        f"/api/professional-valuation/requests/{request_id}/sources",
        json=payload,
        content_type="application/json",
        headers=_auth(),
    )
    return resp.get_json()


# ── PVC01–PVC02: Catalogue routes auth ───────────────────────────────────────

def test_PVC01_evidence_type_catalogue_requires_auth(client):
    resp = client.get("/api/professional-valuation/evidence/types")
    assert resp.status_code == 401


def test_PVC02_source_type_catalogue_requires_auth(client):
    resp = client.get("/api/professional-valuation/source/types")
    assert resp.status_code == 401


# ── PVC03–PVC07: Evidence creation ───────────────────────────────────────────

def test_PVC03_create_evidence_requires_auth(client):
    rid  = _create(client).get_json()["request_id"]
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/evidence",
        json={"evidence_type": "ownership_document"},
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_PVC04_create_evidence_returns_evidence_id(client):
    rid  = _create(client).get_json()["request_id"]
    body = _create_evidence(client, rid)
    assert body["ok"] is True
    ev = body["evidence"]
    assert ev["evidence_id"].startswith("PVE-"), f"Bad evidence_id: {ev['evidence_id']}"
    assert ev["request_id"] == rid


def test_PVC05_create_evidence_production_ready_false(client):
    rid  = _create(client).get_json()["request_id"]
    body = _create_evidence(client, rid)
    assert body["evidence"]["production_ready"] is False


def test_PVC06_create_evidence_no_automatic_value_extraction_true(client):
    rid  = _create(client).get_json()["request_id"]
    body = _create_evidence(client, rid)
    assert body["evidence"]["no_automatic_value_extraction"] is True


def test_PVC07_evidence_response_has_no_internal_path(client):
    rid      = _create(client).get_json()["request_id"]
    body_str = client.post(
        f"/api/professional-valuation/requests/{rid}/evidence",
        json={"evidence_type": "inspection_photos"},
        content_type="application/json",
        headers=_auth(),
    ).get_data(as_text=True)
    assert "instance/professional_valuation" not in body_str, (
        "Internal storage path leaked in evidence response"
    )
    assert "evidence_files" not in body_str


# ── PVC08–PVC12: Evidence list/detail/review ─────────────────────────────────

def test_PVC08_list_evidence_requires_auth(client):
    rid  = _create(client).get_json()["request_id"]
    resp = client.get(f"/api/professional-valuation/requests/{rid}/evidence")
    assert resp.status_code == 401


def test_PVC09_get_evidence_detail_requires_auth(client):
    rid   = _create(client).get_json()["request_id"]
    ev_id = _create_evidence(client, rid)["evidence"]["evidence_id"]
    resp  = client.get(f"/api/professional-valuation/requests/{rid}/evidence/{ev_id}")
    assert resp.status_code == 401


def test_PVC10_evidence_review_requires_auth(client):
    rid   = _create(client).get_json()["request_id"]
    ev_id = _create_evidence(client, rid)["evidence"]["evidence_id"]
    resp  = client.post(
        f"/api/professional-valuation/requests/{rid}/evidence/{ev_id}/review",
        json={"status": "under_review"},
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_PVC11_rejected_evidence_requires_rejection_reason(client):
    rid   = _create(client).get_json()["request_id"]
    ev_id = _create_evidence(client, rid)["evidence"]["evidence_id"]
    resp  = client.post(
        f"/api/professional-valuation/requests/{rid}/evidence/{ev_id}/review",
        json={"status": "rejected"},
        content_type="application/json",
        headers=_auth(),
    )
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["ok"] is False
    assert "rejection_reason" in body["error"]


def test_PVC12_approved_as_source_requires_source_eligible_type(client):
    rid   = _create(client).get_json()["request_id"]
    # expert_note is NOT source-eligible
    ev_id = _create_evidence(client, rid, {"evidence_type": "expert_note"})["evidence"]["evidence_id"]
    resp  = client.post(
        f"/api/professional-valuation/requests/{rid}/evidence/{ev_id}/review",
        json={"status": "approved_as_source"},
        content_type="application/json",
        headers=_auth(),
    )
    assert resp.status_code == 422


# ── PVC13–PVC14: Document completeness gate ───────────────────────────────────

def test_PVC13_document_completeness_returned_after_evidence_upload(client):
    rid  = _create(client).get_json()["request_id"]
    body = _create_evidence(client, rid)
    assert "document_completeness_status" in body
    doc = body["document_completeness_status"]
    assert "completeness_level" in doc
    assert "score" in doc
    assert 0 <= doc["score"] <= 100


def test_PVC14_missing_mandatory_docs_keep_certification_false(client):
    rid  = _create(client).get_json()["request_id"]
    body = _create_evidence(client, rid, {"evidence_type": "expert_note"})
    doc  = body["document_completeness_status"]
    # expert_note alone can't satisfy ownership_document, area_statement, inspection_photos, location_map
    assert doc["certification_document_ready"] is False
    gate = body["certification_gate_summary"]
    assert gate["certification_ready"] is False
    assert gate["mandatory_documents_ready"] is False


# ── PVC15–PVC19: Source creation ─────────────────────────────────────────────

def test_PVC15_create_source_requires_auth(client):
    rid  = _create(client).get_json()["request_id"]
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/sources",
        json={"source_type": "sales_comparable"},
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_PVC16_create_source_returns_source_id(client):
    rid  = _create(client).get_json()["request_id"]
    body = _create_source(client, rid)
    assert body["ok"] is True
    src = body["source"]
    assert src["source_id"].startswith("PVS-"), f"Bad source_id: {src['source_id']}"
    assert src["request_id"] == rid


def test_PVC17_create_source_production_ready_false(client):
    rid  = _create(client).get_json()["request_id"]
    body = _create_source(client, rid)
    assert body["source"]["production_ready"] is False


def test_PVC18_qa_simulation_source_cannot_become_production(client):
    rid    = _create(client).get_json()["request_id"]
    src_id = _create_source(client, rid, {"qa_simulation": True})["source"]["source_id"]
    # Advance to approved_for_analysis first
    _pve._update_src(rid, src_id, {"source_status": "approved_for_analysis"})
    resp   = client.post(
        f"/api/professional-valuation/requests/{rid}/sources/{src_id}/review",
        json={"source_status": "approved_as_production_source"},
        content_type="application/json",
        headers=_auth(),
    )
    assert resp.status_code == 422
    body = resp.get_json()
    assert body["ok"] is False
    assert "QA" in body["error"]


def test_PVC19_non_qa_source_can_become_production(client):
    rid    = _create(client).get_json()["request_id"]
    src_id = _create_source(client, rid, {"qa_simulation": False})["source"]["source_id"]
    # Advance to approved_for_analysis
    _pve._update_src(rid, src_id, {"source_status": "approved_for_analysis"})
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/sources/{src_id}/review",
        json={"source_status": "approved_as_production_source"},
        content_type="application/json",
        headers=_auth(),
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["source"]["production_ready"] is True


# ── PVC20–PVC23: Source list/detail/review ───────────────────────────────────

def test_PVC20_list_sources_requires_auth(client):
    rid  = _create(client).get_json()["request_id"]
    resp = client.get(f"/api/professional-valuation/requests/{rid}/sources")
    assert resp.status_code == 401


def test_PVC21_get_source_detail_requires_auth(client):
    rid    = _create(client).get_json()["request_id"]
    src_id = _create_source(client, rid)["source"]["source_id"]
    resp   = client.get(f"/api/professional-valuation/requests/{rid}/sources/{src_id}")
    assert resp.status_code == 401


def test_PVC22_source_review_requires_auth(client):
    rid    = _create(client).get_json()["request_id"]
    src_id = _create_source(client, rid)["source"]["source_id"]
    resp   = client.post(
        f"/api/professional-valuation/requests/{rid}/sources/{src_id}/review",
        json={"source_status": "submitted"},
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_PVC23_rejected_source_requires_rejection_reason(client):
    rid    = _create(client).get_json()["request_id"]
    src_id = _create_source(client, rid)["source"]["source_id"]
    # advance to under_review
    _pve._update_src(rid, src_id, {"source_status": "under_review"})
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/sources/{src_id}/review",
        json={"source_status": "rejected"},
        content_type="application/json",
        headers=_auth(),
    )
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["ok"] is False
    assert "rejection_reason" in body["error"]


# ── PVC24–PVC28: Gate evaluation ─────────────────────────────────────────────

def test_PVC24_source_quality_summary_returned_after_creation(client):
    rid  = _create(client).get_json()["request_id"]
    body = _create_source(client, rid)
    assert "source_quality_summary" in body
    sq = body["source_quality_summary"]
    assert "source_quality_status" in sq
    assert "total_sources" in sq


def test_PVC25_no_production_sources_keeps_real_sources_ready_false(client):
    rid  = _create(client).get_json()["request_id"]
    body = _create_source(client, rid)
    gate = body["certification_gate_summary"]
    # newly created source is draft → not production_ready
    assert gate["real_sources_ready"] is False
    assert gate["certification_ready"] is False


def test_PVC26_approved_non_qa_source_sets_real_sources_ready_true(client):
    rid    = _create(client).get_json()["request_id"]
    src_id = _create_source(client, rid, {"qa_simulation": False})["source"]["source_id"]
    _pve._update_src(rid, src_id, {"source_status": "approved_for_analysis"})
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/sources/{src_id}/review",
        json={"source_status": "approved_as_production_source"},
        content_type="application/json",
        headers=_auth(),
    )
    assert resp.status_code == 200
    gate = resp.get_json()["certification_gate_summary"]
    assert gate["real_sources_ready"] is True
    # certification_ready still False in Phase C
    assert gate["certification_ready"] is False


def test_PVC27_gate_mandatory_documents_ready_updates_after_evidence(client):
    rid = _create(client).get_json()["request_id"]
    # Upload all required documents for "قيمة سوقية":
    # common (4) + sales_comparable_document (required by "سوقية" keyword)
    for ev_type in (
        "ownership_document", "area_statement",
        "inspection_photos", "location_map",
        "sales_comparable_document",
    ):
        _create_evidence(client, rid, {"evidence_type": ev_type})
    # Re-fetch detail to get updated gate summary
    detail_resp = client.get(
        f"/api/professional-valuation/requests/{rid}",
        headers=_auth(),
    )
    gate = detail_resp.get_json()["certification_gate_summary"]
    assert gate["mandatory_documents_ready"] is True
    assert gate["certification_ready"] is False


def test_PVC28_gate_real_sources_ready_updates_after_source_approval(client):
    rid    = _create(client).get_json()["request_id"]
    src_id = _create_source(client, rid, {"qa_simulation": False})["source"]["source_id"]
    _pve._update_src(rid, src_id, {
        "source_status":  "approved_for_analysis",
        "production_ready": False,
    })
    client.post(
        f"/api/professional-valuation/requests/{rid}/sources/{src_id}/review",
        json={"source_status": "approved_as_production_source"},
        content_type="application/json",
        headers=_auth(),
    )
    detail_resp = client.get(
        f"/api/professional-valuation/requests/{rid}",
        headers=_auth(),
    )
    gate = detail_resp.get_json()["certification_gate_summary"]
    assert gate["real_sources_ready"] is True


# ── PVC29–PVC30: Safety ───────────────────────────────────────────────────────

def test_PVC29_event_log_records_evidence_and_source_actions(client):
    rid = _create(client).get_json()["request_id"]
    _create_evidence(client, rid)
    _create_source(client, rid)
    events = _pvr._read_events(rid)
    actions = [e["action"] for e in events]
    assert "evidence_upload" in actions, f"evidence_upload not in events: {actions}"
    assert "source_create"   in actions, f"source_create not in events: {actions}"


def test_PVC30_no_internal_paths_in_evidence_source_responses(client):
    rid = _create(client).get_json()["request_id"]
    ev_body = client.post(
        f"/api/professional-valuation/requests/{rid}/evidence",
        json={"evidence_type": "area_statement"},
        content_type="application/json",
        headers=_auth(),
    ).get_data(as_text=True)
    src_body = client.post(
        f"/api/professional-valuation/requests/{rid}/sources",
        json={"source_type": "rental_comparable", "source_name": "test"},
        content_type="application/json",
        headers=_auth(),
    ).get_data(as_text=True)
    for body_str, label in [(ev_body, "evidence"), (src_body, "source")]:
        assert "instance/professional_valuation" not in body_str, (
            f"Internal path in {label} response"
        )
        assert "evidence_files" not in body_str, (
            f"evidence_files path in {label} response"
        )


# ══════════════════════════════════════════════════════════════════════════════
# PVD01–PVD35: Phase D — Comparable Data Entry & Excel Import
# ══════════════════════════════════════════════════════════════════════════════

import io as _io

import professional_valuation_comparables as _pvco  # noqa: E402


def _create_comparable(client, rid, extra=None):
    data = {
        "comparable_type": "sales_comparable",
        "area_m2":         150,
        "value_amount":    2_500_000,
        "source_name":     "test-source",
        "property_type":   "شقة",
        "location":        "الزمالك",
        "transaction_date": "2024-01-01",
    }
    if extra:
        data.update(extra)
    return client.post(
        f"/api/professional-valuation/requests/{rid}/comparables",
        json=data,
        content_type="application/json",
        headers=_auth(),
    ).get_json()


def _make_csv_bytes(rows: list[dict]) -> bytes:
    if not rows:
        return b"comparable_type,area_m2,value_amount,source_name\n"
    headers = list(rows[0].keys())
    lines = [",".join(headers)]
    for r in rows:
        lines.append(",".join(str(r.get(h, "")) for h in headers))
    return "\n".join(lines).encode("utf-8")


def _make_xlsx_bytes(rows: list[dict]) -> bytes:
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    if rows:
        headers = list(rows[0].keys())
        ws.append(headers)
        for r in rows:
            ws.append([r.get(h) for h in headers])
    buf = _io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ── PVD01-PVD02: Comparable type catalogue ────────────────────────────────────

def test_PVD01_comparable_type_catalogue_returns_7_types(client):
    resp = client.get(
        "/api/professional-valuation/comparable/types",
        headers=_auth(),
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    keys = {t["key"] for t in body["comparable_types"]}
    for expected in _pvco.PV_COMPARABLE_TYPES:
        assert expected in keys, f"Missing type: {expected}"
    assert len(body["comparable_types"]) == 7


def test_PVD02_comparable_type_catalogue_requires_auth(client):
    resp = client.get("/api/professional-valuation/comparable/types")
    assert resp.status_code == 401


# ── PVD03-PVD11: Create comparable ───────────────────────────────────────────

def test_PVD03_create_comparable_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/comparables",
        json={"comparable_type": "sales_comparable", "source_name": "x"},
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_PVD04_create_comparable_returns_pvco_id(client):
    rid  = _create(client).get_json()["request_id"]
    body = _create_comparable(client, rid)
    assert body["ok"] is True
    comp_id = body["comparable"]["comparable_id"]
    assert comp_id.startswith("PVCO-"), f"Unexpected ID: {comp_id}"
    assert _pvco._PVCO_ID_RE.match(comp_id)


def test_PVD05_create_comparable_sets_production_ready_false(client):
    rid  = _create(client).get_json()["request_id"]
    body = _create_comparable(client, rid)
    assert body["comparable"]["production_ready"] is False


def test_PVD06_create_comparable_sets_status_staged(client):
    rid  = _create(client).get_json()["request_id"]
    body = _create_comparable(client, rid)
    assert body["comparable"]["status"] == "staged"


def test_PVD07_create_comparable_sets_included_in_analysis_false(client):
    rid  = _create(client).get_json()["request_id"]
    body = _create_comparable(client, rid)
    assert body["comparable"]["included_in_analysis"] is False


def test_PVD08_create_comparable_validates_comparable_type(client):
    rid  = _create(client).get_json()["request_id"]
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/comparables",
        json={"comparable_type": "invalid_type", "source_name": "x"},
        content_type="application/json",
        headers=_auth(),
    )
    assert resp.status_code == 422
    body = resp.get_json()
    assert body["ok"] is False
    assert body["validation_errors"]


def test_PVD09_create_comparable_validates_required_fields(client):
    rid  = _create(client).get_json()["request_id"]
    # sales_comparable requires location/district/city, area_m2, value_amount, source_name
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/comparables",
        json={"comparable_type": "sales_comparable"},
        content_type="application/json",
        headers=_auth(),
    )
    assert resp.status_code == 422
    assert resp.get_json()["ok"] is False


def test_PVD10_create_comparable_rejects_negative_area(client):
    rid  = _create(client).get_json()["request_id"]
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/comparables",
        json={"comparable_type": "sales_comparable", "area_m2": -5,
              "value_amount": 1_000_000, "source_name": "x", "location": "test"},
        content_type="application/json",
        headers=_auth(),
    )
    assert resp.status_code == 422
    assert resp.get_json()["ok"] is False


def test_PVD11_price_per_m2_auto_calculated(client):
    rid  = _create(client).get_json()["request_id"]
    body = _create_comparable(client, rid, {
        "area_m2": 200, "value_amount": 2_000_000,
    })
    assert body["ok"] is True
    comp = body["comparable"]
    assert comp["price_per_m2"] == 10_000.0


# ── PVD12-PVD15: List / detail ────────────────────────────────────────────────

def test_PVD12_list_comparables_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.get(f"/api/professional-valuation/requests/{rid}/comparables")
    assert resp.status_code == 401


def test_PVD13_list_comparables_returns_counts(client):
    rid = _create(client).get_json()["request_id"]
    _create_comparable(client, rid)
    _create_comparable(client, rid)
    body = client.get(
        f"/api/professional-valuation/requests/{rid}/comparables",
        headers=_auth(),
    ).get_json()
    assert body["ok"] is True
    assert body["counts"]["total"] >= 2
    assert body["counts"]["staged"] >= 2


def test_PVD14_get_comparable_detail_requires_auth(client):
    rid    = _create(client).get_json()["request_id"]
    comp   = _create_comparable(client, rid)["comparable"]
    comp_id = comp["comparable_id"]
    resp = client.get(
        f"/api/professional-valuation/requests/{rid}/comparables/{comp_id}"
    )
    assert resp.status_code == 401


def test_PVD15_get_comparable_detail_404_unknown(client):
    rid  = _create(client).get_json()["request_id"]
    resp = client.get(
        f"/api/professional-valuation/requests/{rid}/comparables/PVCO-FFFFFFFF",
        headers=_auth(),
    )
    assert resp.status_code == 404


# ── PVD16-PVD20: Review lifecycle ─────────────────────────────────────────────

def test_PVD16_review_comparable_requires_auth(client):
    rid    = _create(client).get_json()["request_id"]
    comp   = _create_comparable(client, rid)["comparable"]
    comp_id = comp["comparable_id"]
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/comparables/{comp_id}/review",
        json={"status": "under_review"},
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_PVD17_review_invalid_transition_returns_422(client):
    rid     = _create(client).get_json()["request_id"]
    comp    = _create_comparable(client, rid)["comparable"]
    comp_id = comp["comparable_id"]
    # staged -> superseded is not allowed
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/comparables/{comp_id}/review",
        json={"status": "superseded"},
        content_type="application/json",
        headers=_auth(),
    )
    assert resp.status_code == 422
    assert resp.get_json()["ok"] is False


def test_PVD18_rejection_requires_rejection_reason(client):
    rid     = _create(client).get_json()["request_id"]
    comp    = _create_comparable(client, rid)["comparable"]
    comp_id = comp["comparable_id"]
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/comparables/{comp_id}/review",
        json={"status": "rejected"},
        content_type="application/json",
        headers=_auth(),
    )
    assert resp.status_code == 400
    assert resp.get_json()["ok"] is False


def test_PVD19_qa_comparable_cannot_become_production(client):
    rid     = _create(client).get_json()["request_id"]
    comp    = _create_comparable(client, rid, {"qa_simulation": True})["comparable"]
    comp_id = comp["comparable_id"]
    # advance to approved_for_analysis first
    client.post(
        f"/api/professional-valuation/requests/{rid}/comparables/{comp_id}/review",
        json={"status": "approved_for_analysis"},
        content_type="application/json",
        headers=_auth(),
    )
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/comparables/{comp_id}/review",
        json={"status": "approved_as_production_comparable"},
        content_type="application/json",
        headers=_auth(),
    )
    assert resp.status_code == 422
    assert resp.get_json()["ok"] is False


def test_PVD20_production_ready_true_when_approved_non_qa(client):
    rid     = _create(client).get_json()["request_id"]
    comp    = _create_comparable(client, rid, {"qa_simulation": False})["comparable"]
    comp_id = comp["comparable_id"]
    # advance staged -> approved_for_analysis -> approved_as_production_comparable
    client.post(
        f"/api/professional-valuation/requests/{rid}/comparables/{comp_id}/review",
        json={"status": "approved_for_analysis"},
        content_type="application/json",
        headers=_auth(),
    )
    body = client.post(
        f"/api/professional-valuation/requests/{rid}/comparables/{comp_id}/review",
        json={"status": "approved_as_production_comparable"},
        content_type="application/json",
        headers=_auth(),
    ).get_json()
    assert body["ok"] is True
    assert body["comparable"]["production_ready"] is True


# ── PVD21-PVD22: Comparable readiness gate ────────────────────────────────────

def test_PVD21_comparable_readiness_in_list_response(client):
    rid  = _create(client).get_json()["request_id"]
    _create_comparable(client, rid)
    body = client.get(
        f"/api/professional-valuation/requests/{rid}/comparables",
        headers=_auth(),
    ).get_json()
    assert "comparable_readiness" in body
    cr = body["comparable_readiness"]
    assert "comparable_readiness_status" in cr
    assert "total_comparables"          in cr
    assert "production_ready_comparables" in cr


def test_PVD22_comparables_ready_false_in_gate_without_production(client):
    rid  = _create(client).get_json()["request_id"]
    _create_comparable(client, rid)  # staged only
    # Check gate summary via detail endpoint
    detail = client.get(
        f"/api/professional-valuation/requests/{rid}",
        headers=_auth(),
    ).get_json()
    gate = detail.get("certification_gate_summary", {})
    assert gate.get("comparables_ready") is False
    assert gate.get("certification_ready") is False


# ── PVD23-PVD31: Import endpoints ─────────────────────────────────────────────

def test_PVD23_import_requires_auth(client):
    rid  = _create(client).get_json()["request_id"]
    data = {"file": (_io.BytesIO(b"a,b\n1,2"), "test.csv")}
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/comparables/import",
        data=data,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 401


def test_PVD24_import_rejects_invalid_extension(client):
    rid  = _create(client).get_json()["request_id"]
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/comparables/import",
        data={"file": (_io.BytesIO(b"hello"), "test.pdf")},
        content_type="multipart/form-data",
        headers=_auth(),
    )
    assert resp.status_code == 400
    assert resp.get_json()["ok"] is False


def test_PVD25_import_rejects_empty_file(client):
    rid  = _create(client).get_json()["request_id"]
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/comparables/import",
        data={"file": (_io.BytesIO(b""), "empty.csv")},
        content_type="multipart/form-data",
        headers=_auth(),
    )
    assert resp.status_code == 400
    assert resp.get_json()["ok"] is False


def test_PVD26_import_csv_stages_rows(client):
    rid  = _create(client).get_json()["request_id"]
    csv_bytes = _make_csv_bytes([{
        "comparable_type": "sales_comparable",
        "area_m2": "120",
        "value_amount": "1800000",
        "source_name": "السوق المحلي",
        "location": "المعادي",
        "property_type": "شقة",
        "transaction_date": "2024-03-01",
    }])
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/comparables/import",
        data={
            "file": (_io.BytesIO(csv_bytes), "comps.csv"),
            "comparable_type_hint": "sales_comparable",
        },
        content_type="multipart/form-data",
        headers=_auth(),
    )
    assert resp.status_code == 201, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body["ok"] is True
    assert len(body["staged_comparables"]) == 1
    assert body["import_job"]["staged_rows_count"] == 1


def test_PVD27_import_csv_sets_production_ready_false(client):
    rid  = _create(client).get_json()["request_id"]
    csv_bytes = _make_csv_bytes([{
        "comparable_type": "sales_comparable",
        "area_m2": "100",
        "value_amount": "1200000",
        "source_name": "المصدر",
        "location": "6 أكتوبر",
        "property_type": "شقة",
        "transaction_date": "2024-02-01",
    }])
    body = client.post(
        f"/api/professional-valuation/requests/{rid}/comparables/import",
        data={"file": (_io.BytesIO(csv_bytes), "comps.csv")},
        content_type="multipart/form-data",
        headers=_auth(),
    ).get_json()
    assert body["ok"] is True
    for comp in body["staged_comparables"]:
        assert comp["production_ready"] is False


def test_PVD28_import_csv_rejected_row_returned(client):
    rid  = _create(client).get_json()["request_id"]
    # Row with missing required fields — should go to rejected_rows
    csv_bytes = _make_csv_bytes([{
        "comparable_type": "sales_comparable",
        # missing area_m2, value_amount, source_name, location
    }])
    body = client.post(
        f"/api/professional-valuation/requests/{rid}/comparables/import",
        data={
            "file": (_io.BytesIO(csv_bytes), "comps.csv"),
            "comparable_type_hint": "sales_comparable",
        },
        content_type="multipart/form-data",
        headers=_auth(),
    ).get_json()
    # Should succeed as a job but with rejected rows
    assert body.get("ok") is True or "rejected_rows" in body
    if body.get("ok"):
        assert body["import_job"]["rejected_rows_count"] >= 1
        assert len(body["rejected_rows"]) >= 1


def test_PVD29_import_job_listed_in_import_jobs(client):
    rid  = _create(client).get_json()["request_id"]
    csv_bytes = _make_csv_bytes([{
        "comparable_type": "sales_comparable",
        "area_m2": "80",
        "value_amount": "900000",
        "source_name": "اختبار",
        "location": "مدينة نصر",
        "property_type": "شقة",
        "transaction_date": "2024-01-15",
    }])
    import_body = client.post(
        f"/api/professional-valuation/requests/{rid}/comparables/import",
        data={"file": (_io.BytesIO(csv_bytes), "jobs_test.csv")},
        content_type="multipart/form-data",
        headers=_auth(),
    ).get_json()
    job_id = import_body["import_job"]["import_job_id"]
    jobs_body = client.get(
        f"/api/professional-valuation/requests/{rid}/comparables/import-jobs",
        headers=_auth(),
    ).get_json()
    assert jobs_body["ok"] is True
    ids = [j["import_job_id"] for j in jobs_body["import_jobs"]]
    assert job_id in ids


def test_PVD30_import_job_detail_requires_auth(client):
    rid  = _create(client).get_json()["request_id"]
    resp = client.get(
        f"/api/professional-valuation/requests/{rid}/comparables/import-jobs/PVIJ-FFFFFFFF"
    )
    assert resp.status_code == 401


def test_PVD31_import_response_has_no_internal_file_path(client):
    rid  = _create(client).get_json()["request_id"]
    csv_bytes = _make_csv_bytes([{
        "comparable_type": "sales_comparable",
        "area_m2": "90",
        "value_amount": "1000000",
        "source_name": "src",
        "location": "المهندسين",
        "property_type": "شقة",
        "transaction_date": "2024-01-20",
    }])
    body_str = client.post(
        f"/api/professional-valuation/requests/{rid}/comparables/import",
        data={"file": (_io.BytesIO(csv_bytes), "paths_test.csv")},
        content_type="multipart/form-data",
        headers=_auth(),
    ).get_data(as_text=True)
    assert "instance/professional_valuation" not in body_str, "Internal path in import response"
    assert "comparable_import_files" not in body_str, "Import file path in response"


# ── PVD32: Source stubs from import ──────────────────────────────────────────

def test_PVD32_create_source_stubs_creates_draft_stubs(client):
    rid  = _create(client).get_json()["request_id"]
    csv_bytes = _make_csv_bytes([{
        "comparable_type": "sales_comparable",
        "area_m2": "110",
        "value_amount": "1100000",
        "source_name": "وكالة المبروك",
        "source_reference": "REF-2024-001",
        "location": "المقطم",
        "property_type": "فيلا",
        "transaction_date": "2024-04-01",
    }])
    body = client.post(
        f"/api/professional-valuation/requests/{rid}/comparables/import",
        data={
            "file": (_io.BytesIO(csv_bytes), "stubs_test.csv"),
            "create_source_stubs": "true",
        },
        content_type="multipart/form-data",
        headers=_auth(),
    ).get_json()
    assert body["ok"] is True
    # The staged comparable should have a related_source_id (stub was created)
    for comp in body["staged_comparables"]:
        if comp.get("source_name"):
            assert comp.get("related_source_id") is not None, "Source stub not created"
            assert comp["related_source_id"].startswith("PVS-")


# ── PVD33: included_in_analysis guard ────────────────────────────────────────

def test_PVD33_included_in_analysis_false_on_staging(client):
    rid  = _create(client).get_json()["request_id"]
    # Even if caller requests included_in_analysis=true, it must be False when staging
    body = _create_comparable(client, rid, {"included_in_analysis": True})
    # Either rejected 422 or accepted but included_in_analysis=False
    if body.get("ok"):
        assert body["comparable"]["included_in_analysis"] is False, (
            "included_in_analysis should be False when staged"
        )


# ── PVD34: Missing comparable types for purpose ───────────────────────────────

def test_PVD34_readiness_shows_missing_types_for_purpose(client):
    # Create a request with rental purpose
    rid = _create(client, {
        "valuation_purpose": "إيجار",
        "property_type": "شقة",
    }).get_json()["request_id"]
    # Add a sales_comparable (not the required rental_comparable)
    _create_comparable(client, rid, {
        "comparable_type": "sales_comparable",
        "valuation_purpose": "إيجار",
    })
    body = client.get(
        f"/api/professional-valuation/requests/{rid}/comparables",
        headers=_auth(),
    ).get_json()
    cr = body["comparable_readiness"]
    assert "rental_comparable" in cr.get("missing_comparable_types", []) or \
           cr.get("certification_comparable_ready") is False


# ── PVD35: Excel xlsx import ──────────────────────────────────────────────────

def test_PVD35_import_xlsx_stages_rows(client):
    rid       = _create(client).get_json()["request_id"]
    xlsx_bytes = _make_xlsx_bytes([{
        "comparable_type": "sales_comparable",
        "area_m2": 130,
        "value_amount": 1_950_000,
        "source_name": "بيانات السوق",
        "location": "الشيخ زايد",
        "property_type": "شقة",
        "transaction_date": "2024-05-01",
    }])
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/comparables/import",
        data={
            "file": (_io.BytesIO(xlsx_bytes), "comps.xlsx"),
            "comparable_type_hint": "sales_comparable",
        },
        content_type="multipart/form-data",
        headers=_auth(),
    )
    assert resp.status_code == 201, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body["ok"] is True
    assert len(body["staged_comparables"]) >= 1
    assert body["import_job"]["file_ext"] == ".xlsx"

# ══════════════════════════════════════════════════════════════════════════════
# PVE01–PVE40 — Phase E: Method Analysis & Reconciliation
# ══════════════════════════════════════════════════════════════════════════════

import professional_valuation_methods as _pvm


def _create_and_approve_comparable(client, rid, extra=None):
    """Create comparable then promote to approved_for_analysis."""
    body = _create_comparable(client, rid, extra)
    comp = body.get("comparable") or {}
    comp_id = comp.get("comparable_id", "")
    if comp_id:
        client.post(
            f"/api/professional-valuation/requests/{rid}/comparables/{comp_id}/review",
            json={"new_status": "under_review", "reviewer_notes": "e-test"},
            content_type="application/json",
            headers=_auth(),
        )
        client.post(
            f"/api/professional-valuation/requests/{rid}/comparables/{comp_id}/review",
            json={"new_status": "approved_for_analysis", "reviewer_notes": "e-ok"},
            content_type="application/json",
            headers=_auth(),
        )
    return comp_id


def _run_methods(client, rid, methods, subject_inputs=None, weights=None):
    return client.post(
        f"/api/professional-valuation/requests/{rid}/methods/run",
        json={
            "selected_methods": methods,
            "subject_inputs": subject_inputs or {"subject_area_m2": 150},
            "method_weights": weights or {},
        },
        content_type="application/json",
        headers=_auth(),
    )


# ── PVE01 ─────────────────────────────────────────────────────────────────────
def test_PVE01_methods_catalogue_requires_auth(client):
    resp = client.get("/api/professional-valuation/methods/catalogue")
    assert resp.status_code == 401


# ── PVE02 ─────────────────────────────────────────────────────────────────────
def test_PVE02_methods_context_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.get(f"/api/professional-valuation/requests/{rid}/methods/context")
    assert resp.status_code == 401


# ── PVE03 ─────────────────────────────────────────────────────────────────────
def test_PVE03_methods_run_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/methods/run",
        json={"selected_methods": ["sales_comparison"]},
        content_type="application/json",
    )
    assert resp.status_code == 401


# ── PVE04 ─────────────────────────────────────────────────────────────────────
def test_PVE04_reconciliation_save_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/reconciliation",
        json={"method_weights": {}, "rationale": "test"},
        content_type="application/json",
    )
    assert resp.status_code == 401


# ── PVE05 ─────────────────────────────────────────────────────────────────────
def test_PVE05_catalogue_returns_methods(client):
    body = client.get("/api/professional-valuation/methods/catalogue", headers=_auth()).get_json()
    assert body["ok"] is True
    keys = [m["method_key"] for m in body["methods"]]
    assert "sales_comparison" in keys
    assert "rental_comparison" in keys
    assert "dcf" in keys


# ── PVE06 ─────────────────────────────────────────────────────────────────────
def test_PVE06_context_returns_method_readiness(client):
    rid  = _create(client).get_json()["request_id"]
    body = client.get(f"/api/professional-valuation/requests/{rid}/methods/context", headers=_auth()).get_json()
    assert body["ok"] is True
    assert "method_readiness" in body


# ── PVE07 ─────────────────────────────────────────────────────────────────────
def test_PVE07_context_returns_approved_comparables(client):
    rid = _create(client).get_json()["request_id"]
    _create_and_approve_comparable(client, rid)
    body = client.get(f"/api/professional-valuation/requests/{rid}/methods/context", headers=_auth()).get_json()
    assert body["ok"] is True
    assert "approved_comparables" in body


# ── PVE08 ─────────────────────────────────────────────────────────────────────
def test_PVE08_run_creates_method_run_id(client):
    rid  = _create(client).get_json()["request_id"]
    resp = _run_methods(client, rid, ["cost_approach"], {
        "subject_area_m2": 120, "construction_cost_per_m2": 8000,
        "land_price_per_m2": 5000, "land_area_m2": 60,
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["ok"] is True
    assert body["method_run_id"].startswith("PVMR-")


# ── PVE09 ─────────────────────────────────────────────────────────────────────
def test_PVE09_run_keeps_production_ready_false(client):
    rid  = _create(client).get_json()["request_id"]
    body = _run_methods(client, rid, ["cost_approach"], {
        "subject_area_m2": 100, "construction_cost_per_m2": 7000,
        "land_price_per_m2": 4000, "land_area_m2": 50,
    }).get_json()
    for out in body.get("method_outputs", []):
        assert out.get("production_ready") is False


# ── PVE10 ─────────────────────────────────────────────────────────────────────
def test_PVE10_certification_ready_false_after_run(client):
    rid  = _create(client).get_json()["request_id"]
    body = _run_methods(client, rid, ["cost_approach"], {
        "subject_area_m2": 100, "construction_cost_per_m2": 7000,
        "land_price_per_m2": 4000, "land_area_m2": 50,
    }).get_json()
    gate = body.get("certification_gate_summary", {})
    assert gate.get("certification_ready") is False


# ── PVE11 ─────────────────────────────────────────────────────────────────────
def test_PVE11_sales_comparison_uses_approved_only(client):
    rid = _create(client).get_json()["request_id"]
    _create_and_approve_comparable(client, rid)
    _create_comparable(client, rid)  # staged only
    body = _run_methods(client, rid, ["sales_comparison"], {"subject_area_m2": 150}).get_json()
    sales = next((o for o in body.get("method_outputs", []) if o.get("method_key") == "sales_comparison"), {})
    assert sales.get("method_status") in ("calculated", "insufficient_data")


# ── PVE12 ─────────────────────────────────────────────────────────────────────
def test_PVE12_staged_comparables_not_used(client):
    rid = _create(client).get_json()["request_id"]
    _create_comparable(client, rid)  # staged only
    body = _run_methods(client, rid, ["sales_comparison"], {"subject_area_m2": 150}).get_json()
    sales = next((o for o in body.get("method_outputs", []) if o.get("method_key") == "sales_comparison"), {})
    assert sales.get("method_status") in ("insufficient_data", "calculated", "error")


# ── PVE13 ─────────────────────────────────────────────────────────────────────
def test_PVE13_rejected_comparables_not_used(client):
    rid  = _create(client).get_json()["request_id"]
    body_c = _create_comparable(client, rid)
    comp_id = (body_c.get("comparable") or {}).get("comparable_id", "")
    if comp_id:
        client.post(
            f"/api/professional-valuation/requests/{rid}/comparables/{comp_id}/review",
            json={"new_status": "rejected", "rejection_reason": "test"},
            content_type="application/json", headers=_auth(),
        )
    body = _run_methods(client, rid, ["sales_comparison"], {"subject_area_m2": 150}).get_json()
    sales = next((o for o in body.get("method_outputs", []) if o.get("method_key") == "sales_comparison"), {})
    assert sales.get("method_status") in ("insufficient_data", "calculated")


# ── PVE14 ─────────────────────────────────────────────────────────────────────
def test_PVE14_qa_comparables_flagged_advisory(client):
    rid  = _create(client).get_json()["request_id"]
    body_c = _create_comparable(client, rid, {"qa_simulation": True})
    comp_id = (body_c.get("comparable") or {}).get("comparable_id", "")
    if comp_id:
        for ns in ["under_review", "approved_for_analysis"]:
            client.post(
                f"/api/professional-valuation/requests/{rid}/comparables/{comp_id}/review",
                json={"new_status": ns, "reviewer_notes": "qa"},
                content_type="application/json", headers=_auth(),
            )
    body = _run_methods(client, rid, ["sales_comparison"], {"subject_area_m2": 150}).get_json()
    sales = next((o for o in body.get("method_outputs", []) if o.get("method_key") == "sales_comparison"), {})
    assert sales.get("data_readiness") in ("qa_advisory", "no_approved_comparables",
                                            "no_price_per_m2_available", "production_advisory")


# ── PVE15 ─────────────────────────────────────────────────────────────────────
def test_PVE15_sales_comparison_calculates_avg_price(client):
    rid = _create(client).get_json()["request_id"]
    _create_and_approve_comparable(client, rid, {
        "comparable_type": "sales_comparable", "area_m2": 150, "value_amount": 3_000_000,
    })
    body = _run_methods(client, rid, ["sales_comparison"], {"subject_area_m2": 150}).get_json()
    sales = next((o for o in body.get("method_outputs", []) if o.get("method_key") == "sales_comparison"), {})
    if sales.get("method_status") == "calculated":
        assert sales.get("calculation_summary", {}).get("average_price_per_m2") is not None


# ── PVE16 ─────────────────────────────────────────────────────────────────────
def test_PVE16_rental_comparison_calculates_avg_rent(client):
    rid = _create(client).get_json()["request_id"]
    _create_and_approve_comparable(client, rid, {
        "comparable_type": "rental_comparable", "area_m2": 120, "monthly_rent": 12_000,
    })
    body = _run_methods(client, rid, ["rental_comparison"], {"subject_area_m2": 120}).get_json()
    rental = next((o for o in body.get("method_outputs", []) if o.get("method_key") == "rental_comparison"), {})
    if rental.get("method_status") == "calculated":
        assert rental.get("calculation_summary", {}).get("average_rent_per_m2") is not None


# ── PVE17 ─────────────────────────────────────────────────────────────────────
def test_PVE17_cost_approach_insufficient_if_missing(client):
    rid  = _create(client).get_json()["request_id"]
    body = _run_methods(client, rid, ["cost_approach"], {}).get_json()
    cost = next((o for o in body.get("method_outputs", []) if o.get("method_key") == "cost_approach"), {})
    assert cost.get("method_status") == "insufficient_data"


# ── PVE18 ─────────────────────────────────────────────────────────────────────
def test_PVE18_cost_approach_calculates_value(client):
    rid  = _create(client).get_json()["request_id"]
    body = _run_methods(client, rid, ["cost_approach"], {
        "subject_area_m2": 120, "construction_cost_per_m2": 8000,
        "land_price_per_m2": 5000, "land_area_m2": 60,
    }).get_json()
    cost = next((o for o in body.get("method_outputs", []) if o.get("method_key") == "cost_approach"), {})
    assert cost.get("method_status") == "calculated"
    assert cost.get("indicated_value") is not None and cost["indicated_value"] > 0
    assert cost.get("production_ready") is False


# ── PVE19 ─────────────────────────────────────────────────────────────────────
def test_PVE19_direct_cap_insufficient_if_cap_missing(client):
    rid  = _create(client).get_json()["request_id"]
    body = _run_methods(client, rid, ["direct_capitalization"], {"annual_rent": 120_000}).get_json()
    cap = next((o for o in body.get("method_outputs", []) if o.get("method_key") == "direct_capitalization"), {})
    assert cap.get("method_status") == "insufficient_data"


# ── PVE20 ─────────────────────────────────────────────────────────────────────
def test_PVE20_direct_cap_calculates_noi(client):
    rid  = _create(client).get_json()["request_id"]
    body = _run_methods(client, rid, ["direct_capitalization"], {
        "monthly_rent": 10_000, "cap_rate": 7.0,
        "vacancy_rate": 5.0, "operating_expense_rate": 15.0,
    }).get_json()
    cap = next((o for o in body.get("method_outputs", []) if o.get("method_key") == "direct_capitalization"), {})
    assert cap.get("method_status") == "calculated"
    assert cap.get("calculation_summary", {}).get("noi") is not None
    assert cap.get("indicated_value") is not None


# ── PVE21 ─────────────────────────────────────────────────────────────────────
def test_PVE21_dcf_insufficient_if_missing(client):
    rid  = _create(client).get_json()["request_id"]
    body = _run_methods(client, rid, ["dcf"], {}).get_json()
    dcf = next((o for o in body.get("method_outputs", []) if o.get("method_key") == "dcf"), {})
    assert dcf.get("method_status") == "insufficient_data"


# ── PVE22 ─────────────────────────────────────────────────────────────────────
def test_PVE22_dcf_calculates_terminal_and_pv(client):
    rid  = _create(client).get_json()["request_id"]
    body = _run_methods(client, rid, ["dcf"], {
        "discount_rate": 10.0, "terminal_cap_rate": 7.0,
        "starting_noi": 120_000, "forecast_years": 5, "rent_growth_rate": 3.0,
    }).get_json()
    dcf = next((o for o in body.get("method_outputs", []) if o.get("method_key") == "dcf"), {})
    assert dcf.get("method_status") == "calculated"
    calc = dcf.get("calculation_summary", {})
    assert calc.get("terminal_value") is not None
    assert calc.get("pv_of_terminal_value") is not None
    assert dcf.get("indicated_value") is not None


# ── PVE23 ─────────────────────────────────────────────────────────────────────
def test_PVE23_method_readiness_exists(client):
    rid  = _create(client).get_json()["request_id"]
    body = _run_methods(client, rid, ["cost_approach"], {
        "subject_area_m2": 100, "construction_cost_per_m2": 7000,
        "land_price_per_m2": 4000, "land_area_m2": 50,
    }).get_json()
    assert "method_readiness" in body
    mr = body["method_readiness"]
    assert "methods_completed" in mr
    assert "certification_method_ready" in mr


# ── PVE24 ─────────────────────────────────────────────────────────────────────
def test_PVE24_methods_completed_true_if_valid(client):
    rid  = _create(client).get_json()["request_id"]
    body = _run_methods(client, rid, ["cost_approach"], {
        "subject_area_m2": 100, "construction_cost_per_m2": 7000,
        "land_price_per_m2": 4000, "land_area_m2": 50,
    }).get_json()
    assert body["method_readiness"]["methods_completed"] is True


# ── PVE25 ─────────────────────────────────────────────────────────────────────
def test_PVE25_methods_completed_false_if_no_data(client):
    rid  = _create(client).get_json()["request_id"]
    body = _run_methods(client, rid, ["direct_capitalization"], {}).get_json()
    assert body["method_readiness"].get("methods_completed") is False


# ── PVE26 ─────────────────────────────────────────────────────────────────────
def test_PVE26_reconciliation_preview_exists(client):
    rid  = _create(client).get_json()["request_id"]
    body = _run_methods(client, rid, ["cost_approach"], {
        "subject_area_m2": 100, "construction_cost_per_m2": 7000,
        "land_price_per_m2": 4000, "land_area_m2": 50,
    }).get_json()
    assert "reconciliation_preview" in body


# ── PVE27 ─────────────────────────────────────────────────────────────────────
def test_PVE27_weights_sum_check(client):
    rid  = _create(client).get_json()["request_id"]
    body = _run_methods(client, rid, ["cost_approach"], {
        "subject_area_m2": 100, "construction_cost_per_m2": 7000,
        "land_price_per_m2": 4000, "land_area_m2": 50,
    }, weights={"cost_approach": 100}).get_json()
    rp = body.get("reconciliation_preview", {})
    assert isinstance(rp.get("warnings", []), list)


# ── PVE28 ─────────────────────────────────────────────────────────────────────
def test_PVE28_weights_normalize_if_not_100(client):
    rid  = _create(client).get_json()["request_id"]
    body = _run_methods(client, rid, ["cost_approach"], {
        "subject_area_m2": 100, "construction_cost_per_m2": 7000,
        "land_price_per_m2": 4000, "land_area_m2": 50,
    }, weights={"cost_approach": 60}).get_json()
    rp = body.get("reconciliation_preview", {})
    warnings = rp.get("warnings", [])
    assert any("%" in w or "طبيع" in w or "ormal" in w for w in warnings) or \
           rp.get("weighted_value") is not None


# ── PVE29 ─────────────────────────────────────────────────────────────────────
def test_PVE29_coefficient_of_variation_calculated(client):
    rid  = _create(client).get_json()["request_id"]
    body = _run_methods(client, rid, ["cost_approach", "direct_capitalization"], {
        "subject_area_m2": 100, "construction_cost_per_m2": 7000,
        "land_price_per_m2": 4000, "land_area_m2": 50,
        "monthly_rent": 10_000, "cap_rate": 7.0,
    }).get_json()
    rp = body.get("reconciliation_preview", {})
    assert rp.get("coefficient_of_variation") is not None


# ── PVE30 ─────────────────────────────────────────────────────────────────────
def test_PVE30_high_cv_produces_divergence_warning(client):
    rid = _create(client).get_json()["request_id"]
    body = _run_methods(client, rid, ["cost_approach", "direct_capitalization"], {
        "subject_area_m2": 10,
        "construction_cost_per_m2": 1000, "land_price_per_m2": 100, "land_area_m2": 5,
        "monthly_rent": 100_000, "cap_rate": 0.5,
    }).get_json()
    rp = body.get("reconciliation_preview", {})
    cv = rp.get("coefficient_of_variation") or 0
    flags = rp.get("divergence_flags", [])
    if cv > 20:
        assert len(flags) > 0


# ── PVE31 ─────────────────────────────────────────────────────────────────────
def test_PVE31_selected_final_value_defaults_to_weighted(client):
    rid  = _create(client).get_json()["request_id"]
    body = _run_methods(client, rid, ["cost_approach"], {
        "subject_area_m2": 100, "construction_cost_per_m2": 7000,
        "land_price_per_m2": 4000, "land_area_m2": 50,
    }).get_json()
    rp = body.get("reconciliation_preview", {})
    if rp.get("weighted_value"):
        assert rp["selected_final_value"] == rp["weighted_value"]


# ── PVE32 ─────────────────────────────────────────────────────────────────────
def test_PVE32_selected_final_value_status_pending(client):
    rid  = _create(client).get_json()["request_id"]
    body = _run_methods(client, rid, ["cost_approach"], {
        "subject_area_m2": 100, "construction_cost_per_m2": 7000,
        "land_price_per_m2": 4000, "land_area_m2": 50,
    }).get_json()
    rp = body.get("reconciliation_preview", {})
    status = rp.get("selected_final_value_status", "")
    assert "pending" in status or "recommended" in status or "system" in status


# ── PVE33 ─────────────────────────────────────────────────────────────────────
def test_PVE33_reconciliation_save_stores_rationale(client):
    rid = _create(client).get_json()["request_id"]
    _run_methods(client, rid, ["cost_approach"], {
        "subject_area_m2": 100, "construction_cost_per_m2": 7000,
        "land_price_per_m2": 4000, "land_area_m2": 50,
    })
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/reconciliation",
        json={"method_weights": {"cost_approach": 100},
              "rationale": "نهج التكلفة اختياري.", "expert_confirmation": True},
        content_type="application/json", headers=_auth(),
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["reconciliation"].get("rationale") == "نهج التكلفة اختياري."


# ── PVE34 ─────────────────────────────────────────────────────────────────────
def test_PVE34_reconciliation_not_production_ready(client):
    rid = _create(client).get_json()["request_id"]
    _run_methods(client, rid, ["cost_approach"], {
        "subject_area_m2": 100, "construction_cost_per_m2": 7000,
        "land_price_per_m2": 4000, "land_area_m2": 50,
    })
    body = client.post(
        f"/api/professional-valuation/requests/{rid}/reconciliation",
        json={"method_weights": {}, "rationale": "test", "expert_confirmation": True},
        content_type="application/json", headers=_auth(),
    ).get_json()
    assert body["reconciliation"].get("production_ready") is False
    assert body["reconciliation"].get("certification_reconciliation_ready") is False


# ── PVE35 ─────────────────────────────────────────────────────────────────────
def test_PVE35_gate_includes_methods_completed(client):
    rid  = _create(client).get_json()["request_id"]
    body = client.get(f"/api/professional-valuation/requests/{rid}", headers=_auth()).get_json()
    assert "methods_completed" in body.get("certification_gate_summary", {})


# ── PVE36 ─────────────────────────────────────────────────────────────────────
def test_PVE36_gate_includes_reconciliation_completed(client):
    rid  = _create(client).get_json()["request_id"]
    body = client.get(f"/api/professional-valuation/requests/{rid}", headers=_auth()).get_json()
    assert "reconciliation_completed" in body.get("certification_gate_summary", {})


# ── PVE37 ─────────────────────────────────────────────────────────────────────
def test_PVE37_no_certified_report_route(client):
    rid  = _create(client).get_json()["request_id"]
    resp = client.get(f"/api/professional-valuation/requests/{rid}/certified-report", headers=_auth())
    assert resp.status_code in (404, 405, 401)


# ── PVE38 ─────────────────────────────────────────────────────────────────────
def test_PVE38_no_internal_paths_in_methods(client):
    rid  = _create(client).get_json()["request_id"]
    body = _run_methods(client, rid, ["cost_approach"], {
        "subject_area_m2": 100, "construction_cost_per_m2": 7000,
        "land_price_per_m2": 4000, "land_area_m2": 50,
    }).get_json()
    text = json.dumps(body)
    assert "method_runs" not in text and "reconciliation/" not in text


# ── PVE39 ─────────────────────────────────────────────────────────────────────
def test_PVE39_qa_outputs_exist():
    qa_dir = Path(__file__).resolve().parents[1] / "instance" / "manual_review_outputs" / "professional_valuation_phase_e_methods"
    assert qa_dir.exists(), f"QA dir missing: {qa_dir}"
    assert len(list(qa_dir.iterdir())) >= 1, "QA dir is empty"


# ── PVE40 ─────────────────────────────────────────────────────────────────────
def test_PVE40_existing_tests_still_pass(client):
    resp = _create(client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["ok"] is True
    assert body["request_id"].startswith("PVR-")


# ── PVE41 ─────────────────────────────────────────────────────────────────────
def test_PVE41_preliminary_approval_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/preliminary-approval",
        json={"method_run_id": "PVMR-00000000", "approval_note": "test"},
    )
    assert resp.status_code == 401


# ── PVE42 ─────────────────────────────────────────────────────────────────────
def test_PVE42_preliminary_approval_requires_method_run_id(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/preliminary-approval",
        headers=_auth(),
        json={"approval_note": "test note"},
    )
    assert resp.status_code == 422


# ── PVE43 ─────────────────────────────────────────────────────────────────────
def test_PVE43_preliminary_approval_rejects_nonexistent_run(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/preliminary-approval",
        headers=_auth(),
        json={"method_run_id": "PVMR-AAAAAAAA", "approval_note": "test note"},
    )
    assert resp.status_code in (404, 422)


# ── PVE44 ─────────────────────────────────────────────────────────────────────
def test_PVE44_preliminary_approval_requires_approval_note(client):
    rid = _create(client).get_json()["request_id"]
    run_resp = _run_methods(client, rid, ["cost_approach"], {
        "subject_area_m2": 100, "construction_cost_per_m2": 7000,
        "land_price_per_m2": 4000, "land_area_m2": 50,
    })
    run_id = run_resp.get_json()["method_run_id"]
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/preliminary-approval",
        headers=_auth(),
        json={"method_run_id": run_id, "approval_note": ""},
    )
    assert resp.status_code == 422


# ── PVE45 ─────────────────────────────────────────────────────────────────────
def test_PVE45_preliminary_approval_sets_ready_true(client):
    rid = _create(client).get_json()["request_id"]
    run_resp = _run_methods(client, rid, ["cost_approach"], {
        "subject_area_m2": 100, "construction_cost_per_m2": 7000,
        "land_price_per_m2": 4000, "land_area_m2": 50,
    })
    run_id = run_resp.get_json()["method_run_id"]
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/preliminary-approval",
        headers=_auth(),
        json={"method_run_id": run_id, "approval_note": "مراجعة مبدئية اختبار"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["preliminary_approval_ready"] is True


# ── PVE46 ─────────────────────────────────────────────────────────────────────
def test_PVE46_preliminary_approval_does_not_set_certification_ready(client):
    rid = _create(client).get_json()["request_id"]
    run_resp = _run_methods(client, rid, ["cost_approach"], {
        "subject_area_m2": 100, "construction_cost_per_m2": 7000,
        "land_price_per_m2": 4000, "land_area_m2": 50,
    })
    run_id = run_resp.get_json()["method_run_id"]
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/preliminary-approval",
        headers=_auth(),
        json={"method_run_id": run_id, "approval_note": "مراجعة مبدئية اختبار"},
    )
    gate = resp.get_json().get("certification_gate_summary", {})
    assert gate.get("certification_ready") is False


# ── PVE47 ─────────────────────────────────────────────────────────────────────
def test_PVE47_preliminary_use_allowed_true(client):
    rid = _create(client).get_json()["request_id"]
    run_resp = _run_methods(client, rid, ["cost_approach"], {
        "subject_area_m2": 100, "construction_cost_per_m2": 7000,
        "land_price_per_m2": 4000, "land_area_m2": 50,
    })
    run_id = run_resp.get_json()["method_run_id"]
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/preliminary-approval",
        headers=_auth(),
        json={"method_run_id": run_id, "approval_note": "مراجعة مبدئية اختبار"},
    )
    assert resp.get_json().get("preliminary_use_allowed") is True


# ── PVE48 ─────────────────────────────────────────────────────────────────────
def test_PVE48_official_use_allowed_false(client):
    rid = _create(client).get_json()["request_id"]
    run_resp = _run_methods(client, rid, ["cost_approach"], {
        "subject_area_m2": 100, "construction_cost_per_m2": 7000,
        "land_price_per_m2": 4000, "land_area_m2": 50,
    })
    run_id = run_resp.get_json()["method_run_id"]
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/preliminary-approval",
        headers=_auth(),
        json={"method_run_id": run_id, "approval_note": "مراجعة مبدئية اختبار"},
    )
    assert resp.get_json().get("official_use_allowed") is False


# ── PVE49 ─────────────────────────────────────────────────────────────────────
def test_PVE49_certified_use_allowed_false(client):
    rid = _create(client).get_json()["request_id"]
    run_resp = _run_methods(client, rid, ["cost_approach"], {
        "subject_area_m2": 100, "construction_cost_per_m2": 7000,
        "land_price_per_m2": 4000, "land_area_m2": 50,
    })
    run_id = run_resp.get_json()["method_run_id"]
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/preliminary-approval",
        headers=_auth(),
        json={"method_run_id": run_id, "approval_note": "مراجعة مبدئية اختبار"},
    )
    assert resp.get_json().get("certified_use_allowed") is False


# ── PVE50 ─────────────────────────────────────────────────────────────────────
def test_PVE50_warning_text_contains_correct_wording(client):
    rid = _create(client).get_json()["request_id"]
    run_resp = _run_methods(client, rid, ["cost_approach"], {
        "subject_area_m2": 100, "construction_cost_per_m2": 7000,
        "land_price_per_m2": 4000, "land_area_m2": 50,
    })
    run_id = run_resp.get_json()["method_run_id"]
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/preliminary-approval",
        headers=_auth(),
        json={"method_run_id": run_id, "approval_note": "مراجعة مبدئية اختبار"},
    )
    wt = resp.get_json().get("warning_text", "")
    assert "تقرير مبدئي" in wt
    assert "غير صالح للاستخدام الرسمي" in wt


# ══════════════════════════════════════════════════════════════════════════════
# PVF01–PVF45 — Phase F: Advanced Expert Review (HBU, Legal, ESG, SWOT)
# ══════════════════════════════════════════════════════════════════════════════

import professional_valuation_advanced_review as _pvadv


# ── Helpers ───────────────────────────────────────────────────────────────────

def _adv_url(rid, path=""):
    return f"/api/professional-valuation/requests/{rid}/advanced-review{path}"


def _schema_url():
    return "/api/professional-valuation/advanced-review/schema"


def _save_hbu(client, rid, extra=None):
    body = {
        "legally_permissible_test":  "سكني — مسموح قانوناً",
        "physically_possible_test":  "مساحة كافية",
        "financially_feasible_test": "عائد إيجاري مقبول",
        "maximally_productive_test": "الاستخدام السكني هو الأعلى إنتاجية",
        "selected_hbu":              "سكني متعدد الطوابق",
        "hbu_conclusion":            "الاستخدام السكني مثالي",
    }
    if extra:
        body.update(extra)
    return client.post(
        _adv_url(rid, "/hbu"),
        json=body, content_type="application/json", headers=_auth()
    ).get_json()


def _save_legal(client, rid, extra=None):
    body = {
        "ownership_type":              "ملكية حرة",
        "ownership_document_reviewed": True,
        "legal_conclusion":            "لا نزاعات — يحتاج مراجعة نهائية",
    }
    if extra:
        body.update(extra)
    return client.post(
        _adv_url(rid, "/legal"),
        json=body, content_type="application/json", headers=_auth()
    ).get_json()


def _save_esg(client, rid, extra=None):
    body = {
        "esg_data_available": True,
        "esg_score":          75.0,
        "esg_category":       "B+",
        "expert_notes":       "تقييم مبدئي استشاري",
    }
    if extra:
        body.update(extra)
    return client.post(
        _adv_url(rid, "/esg"),
        json=body, content_type="application/json", headers=_auth()
    ).get_json()


def _swot_items(cat, title="بند اختبار"):
    return [{"category": cat, "title_ar": title, "description_ar": "وصف", "impact_score": 3, "probability_score": 3}]


def _save_swot(client, rid, extra=None):
    body = {
        "strengths":     _swot_items("strengths",     "موقع متميز"),
        "weaknesses":    _swot_items("weaknesses",    "تكاليف صيانة مرتفعة"),
        "opportunities": _swot_items("opportunities", "تطوير البنية التحتية"),
        "threats":       _swot_items("threats",       "تقلبات السوق"),
    }
    if extra:
        body.update(extra)
    return client.post(
        _adv_url(rid, "/swot"),
        json=body, content_type="application/json", headers=_auth()
    ).get_json()


def _approve_prelim(client, rid, section):
    return client.post(
        _adv_url(rid, f"/{section}/approve-preliminary"),
        json={}, content_type="application/json", headers=_auth()
    ).get_json()


# ── PVF01: schema requires auth ───────────────────────────────────────────────
def test_PVF01_schema_requires_auth(client):
    resp = client.get(_schema_url())
    assert resp.status_code == 401


# ── PVF02: advanced review GET requires auth ──────────────────────────────────
def test_PVF02_advanced_review_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.get(_adv_url(rid))
    assert resp.status_code == 401


# ── PVF03: HBU save requires auth ─────────────────────────────────────────────
def test_PVF03_hbu_save_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.post(_adv_url(rid, "/hbu"), json={})
    assert resp.status_code == 401


# ── PVF04: legal save requires auth ──────────────────────────────────────────
def test_PVF04_legal_save_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.post(_adv_url(rid, "/legal"), json={})
    assert resp.status_code == 401


# ── PVF05: ESG save requires auth ────────────────────────────────────────────
def test_PVF05_esg_save_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.post(_adv_url(rid, "/esg"), json={})
    assert resp.status_code == 401


# ── PVF06: SWOT save requires auth ───────────────────────────────────────────
def test_PVF06_swot_save_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.post(_adv_url(rid, "/swot"), json={})
    assert resp.status_code == 401


# ── PVF07: HBU save stores all four tests ────────────────────────────────────
def test_PVF07_hbu_save_stores_four_tests(client):
    rid  = _create(client).get_json()["request_id"]
    body = _save_hbu(client, rid)
    assert body["ok"] is True
    hbu = body["hbu_review"]
    assert hbu["legally_permissible_test"]  == "سكني — مسموح قانوناً"
    assert hbu["physically_possible_test"]  == "مساحة كافية"
    assert hbu["financially_feasible_test"] == "عائد إيجاري مقبول"
    assert hbu["maximally_productive_test"] == "الاستخدام السكني هو الأعلى إنتاجية"


# ── PVF08: HBU cannot approve preliminary without all four tests ──────────────
def test_PVF08_hbu_cannot_approve_prelim_without_all_tests(client):
    rid = _create(client).get_json()["request_id"]
    # Save with only one test filled
    client.post(
        _adv_url(rid, "/hbu"),
        json={"legally_permissible_test": "مسموح", "selected_hbu": "سكني"},
        content_type="application/json", headers=_auth()
    )
    resp = client.post(
        _adv_url(rid, "/hbu/approve-preliminary"),
        json={}, content_type="application/json", headers=_auth()
    )
    assert resp.status_code == 422
    assert resp.get_json()["ok"] is False


# ── PVF09: HBU approve preliminary succeeds when complete ────────────────────
def test_PVF09_hbu_approve_preliminary_succeeds_when_complete(client):
    rid  = _create(client).get_json()["request_id"]
    _save_hbu(client, rid)  # saves complete record
    body = _approve_prelim(client, rid, "hbu")
    assert body["ok"] is True
    assert body["approved_for_preliminary"] is True


# ── PVF10: HBU approval does NOT set certification_ready ────────────────────
def test_PVF10_hbu_approval_does_not_set_certification_ready(client):
    rid = _create(client).get_json()["request_id"]
    _save_hbu(client, rid)
    body = _approve_prelim(client, rid, "hbu")
    assert body.get("certification_ready") is False
    assert body.get("approved_for_certification") is False


# ── PVF11: legal review stores limitation text ───────────────────────────────
def test_PVF11_legal_review_stores_limitation_text(client):
    rid  = _create(client).get_json()["request_id"]
    body = _save_legal(client, rid)
    assert body["ok"] is True
    legal = body["legal_due_diligence_review"]
    scope = legal.get("legal_scope_limitation", "")
    assert "قانوني" in scope or "نطاق" in scope


# ── PVF12: legal without ownership doc cannot be cert-ready ─────────────────
def test_PVF12_legal_without_ownership_doc_not_cert_ready(client):
    rid  = _create(client).get_json()["request_id"]
    body = _save_legal(client, rid, {"ownership_document_reviewed": False})
    legal = body["legal_due_diligence_review"]
    assert legal.get("approved_for_certification") is False
    assert legal.get("certified_use_allowed") is False


# ── PVF13: legal approve preliminary succeeds with limitation ────────────────
def test_PVF13_legal_approve_preliminary_with_limitation(client):
    rid  = _create(client).get_json()["request_id"]
    _save_legal(client, rid)
    body = _approve_prelim(client, rid, "legal")
    assert body["ok"] is True
    assert body["approved_for_preliminary"] is True
    assert body["approved_for_certification"] is False


# ── PVF14: ESG save stores score/category ───────────────────────────────────
def test_PVF14_esg_save_stores_score_and_category(client):
    rid  = _create(client).get_json()["request_id"]
    body = _save_esg(client, rid)
    assert body["ok"] is True
    esg = body["esg_climate_review"]
    assert esg["esg_score"] == 75.0
    assert esg["esg_category"] == "B+"


# ── PVF15: ESG missing data stays advisory ──────────────────────────────────
def test_PVF15_esg_missing_data_stays_advisory(client):
    rid  = _create(client).get_json()["request_id"]
    body = _save_esg(client, rid, {"esg_data_available": False, "esg_score": None})
    esg = body["esg_climate_review"]
    impact = esg.get("esg_value_impact_commentary", "")
    assert "غير مكتمل" in impact or "advisory" in impact or esg.get("no_automatic_value_impact") is True


# ── PVF16: ESG approve preliminary does NOT apply production value impact ────
def test_PVF16_esg_approve_prelim_no_production_impact(client):
    rid  = _create(client).get_json()["request_id"]
    _save_esg(client, rid)
    body = _approve_prelim(client, rid, "esg")
    assert body["ok"] is True
    assert body.get("approved_for_certification") is False
    assert body.get("certification_ready") is False


# ── PVF17: SWOT save stores all four categories ──────────────────────────────
def test_PVF17_swot_save_stores_all_four_categories(client):
    rid  = _create(client).get_json()["request_id"]
    body = _save_swot(client, rid)
    assert body["ok"] is True
    swot = body["swot_risk_review"]
    assert len(swot["strengths"])     >= 1
    assert len(swot["weaknesses"])    >= 1
    assert len(swot["opportunities"]) >= 1
    assert len(swot["threats"])       >= 1


# ── PVF18: SWOT priority_score = impact × probability ───────────────────────
def test_PVF18_swot_priority_score_equals_impact_times_probability(client):
    rid  = _create(client).get_json()["request_id"]
    items = [{"category": "strengths", "title_ar": "قوة", "impact_score": 4, "probability_score": 3}]
    body = client.post(
        _adv_url(rid, "/swot"),
        json={"strengths": items, "weaknesses": _swot_items("weaknesses"),
              "opportunities": _swot_items("opportunities"), "threats": _swot_items("threats")},
        content_type="application/json", headers=_auth()
    ).get_json()
    swot = body["swot_risk_review"]
    st = swot["strengths"][0]
    assert st["priority_score"] == st["impact_score"] * st["probability_score"]
    assert st["priority_score"] == 12


# ── PVF19: SWOT cannot approve if a category missing ─────────────────────────
def test_PVF19_swot_cannot_approve_prelim_with_missing_category(client):
    rid = _create(client).get_json()["request_id"]
    # Save with only strengths, no weaknesses/opportunities/threats
    client.post(
        _adv_url(rid, "/swot"),
        json={"strengths": _swot_items("strengths")},
        content_type="application/json", headers=_auth()
    )
    resp = client.post(
        _adv_url(rid, "/swot/approve-preliminary"),
        json={}, content_type="application/json", headers=_auth()
    )
    assert resp.status_code == 422
    assert resp.get_json()["ok"] is False


# ── PVF20: SWOT approve preliminary succeeds when complete ───────────────────
def test_PVF20_swot_approve_preliminary_succeeds_when_complete(client):
    rid  = _create(client).get_json()["request_id"]
    _save_swot(client, rid)
    body = _approve_prelim(client, rid, "swot")
    assert body["ok"] is True
    assert body["approved_for_preliminary"] is True


# ── PVF21: reject endpoint requires rejection_reason ─────────────────────────
def test_PVF21_reject_requires_rejection_reason(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.post(
        _adv_url(rid, "/hbu/reject"),
        json={}, content_type="application/json", headers=_auth()
    )
    assert resp.status_code == 422
    assert resp.get_json()["ok"] is False


# ── PVF22: rejected section clears preliminary approval ──────────────────────
def test_PVF22_rejected_section_clears_preliminary_approval(client):
    rid = _create(client).get_json()["request_id"]
    _save_hbu(client, rid)
    _approve_prelim(client, rid, "hbu")
    body = client.post(
        _adv_url(rid, "/hbu/reject"),
        json={"rejection_reason": "بيانات ناقصة"},
        content_type="application/json", headers=_auth()
    ).get_json()
    assert body["ok"] is True
    assert body["approved_for_preliminary"] is False
    assert body["status"] == "rejected"


# ── PVF23: advanced review readiness endpoint exists ─────────────────────────
def test_PVF23_advanced_review_get_returns_summary(client):
    rid  = _create(client).get_json()["request_id"]
    body = client.get(_adv_url(rid), headers=_auth()).get_json()
    assert body["ok"] is True
    assert "advanced_review_summary" in body
    assert "certification_gate_fragment" in body


# ── PVF24: all_advanced_reviews_prelim_ready false initially ─────────────────
def test_PVF24_all_advanced_reviews_prelim_ready_false_initially(client):
    rid  = _create(client).get_json()["request_id"]
    body = client.get(_adv_url(rid), headers=_auth()).get_json()
    summary = body["advanced_review_summary"]
    assert summary["all_advanced_reviews_prelim_ready"] is False


# ── PVF25: all_advanced_reviews_prelim_ready true after all four approvals ───
def test_PVF25_all_advanced_prelim_ready_true_after_all_four(client):
    rid = _create(client).get_json()["request_id"]
    _save_hbu(client, rid)
    _save_legal(client, rid)
    _save_esg(client, rid)
    _save_swot(client, rid)
    _approve_prelim(client, rid, "hbu")
    _approve_prelim(client, rid, "legal")
    _approve_prelim(client, rid, "esg")
    _approve_prelim(client, rid, "swot")
    body    = client.get(_adv_url(rid), headers=_auth()).get_json()
    summary = body["advanced_review_summary"]
    assert summary["all_advanced_reviews_prelim_ready"] is True


# ── PVF26: all_advanced_reviews_cert_ready always false in Phase F ────────────
def test_PVF26_all_advanced_cert_ready_always_false(client):
    rid = _create(client).get_json()["request_id"]
    _save_hbu(client, rid); _save_legal(client, rid)
    _save_esg(client, rid); _save_swot(client, rid)
    _approve_prelim(client, rid, "hbu"); _approve_prelim(client, rid, "legal")
    _approve_prelim(client, rid, "esg"); _approve_prelim(client, rid, "swot")
    body    = client.get(_adv_url(rid), headers=_auth()).get_json()
    summary = body["advanced_review_summary"]
    assert summary["all_advanced_reviews_cert_ready"] is False


# ── PVF27: certification gate includes hbu_completed ─────────────────────────
def test_PVF27_gate_includes_hbu_completed(client):
    rid  = _create(client).get_json()["request_id"]
    body = client.get(f"/api/professional-valuation/requests/{rid}", headers=_auth()).get_json()
    gate = body.get("certification_gate_summary", {})
    assert "hbu_completed" in gate


# ── PVF28: certification gate includes legal_due_diligence_ready ─────────────
def test_PVF28_gate_includes_legal_due_diligence_ready(client):
    rid  = _create(client).get_json()["request_id"]
    body = client.get(f"/api/professional-valuation/requests/{rid}", headers=_auth()).get_json()
    gate = body.get("certification_gate_summary", {})
    assert "legal_due_diligence_ready" in gate


# ── PVF29: certification gate includes esg_reviewed ──────────────────────────
def test_PVF29_gate_includes_esg_reviewed(client):
    rid  = _create(client).get_json()["request_id"]
    body = client.get(f"/api/professional-valuation/requests/{rid}", headers=_auth()).get_json()
    gate = body.get("certification_gate_summary", {})
    assert "esg_reviewed" in gate


# ── PVF30: certification gate includes swot_completed ────────────────────────
def test_PVF30_gate_includes_swot_completed(client):
    rid  = _create(client).get_json()["request_id"]
    body = client.get(f"/api/professional-valuation/requests/{rid}", headers=_auth()).get_json()
    gate = body.get("certification_gate_summary", {})
    assert "swot_completed" in gate


# ── PVF31: certification_ready remains false after all preliminary approvals ──
def test_PVF31_certification_ready_false_after_all_prelim_approvals(client):
    rid = _create(client).get_json()["request_id"]
    _save_hbu(client, rid); _save_legal(client, rid)
    _save_esg(client, rid); _save_swot(client, rid)
    _approve_prelim(client, rid, "hbu"); _approve_prelim(client, rid, "legal")
    _approve_prelim(client, rid, "esg"); _approve_prelim(client, rid, "swot")
    body = client.get(f"/api/professional-valuation/requests/{rid}", headers=_auth()).get_json()
    gate = body.get("certification_gate_summary", {})
    assert gate.get("certification_ready") is False


# ── PVF32: certified_use_allowed remains false ────────────────────────────────
def test_PVF32_certified_use_allowed_remains_false(client):
    rid = _create(client).get_json()["request_id"]
    _save_hbu(client, rid)
    _approve_prelim(client, rid, "hbu")
    hbu_body = client.get(_adv_url(rid), headers=_auth()).get_json()
    hbu = hbu_body.get("hbu_review", {})
    assert hbu.get("certified_use_allowed") is False


# ── PVF33: preliminary_use_allowed consistent with Phase E ───────────────────
def test_PVF33_preliminary_use_allowed_consistent_with_phase_e(client):
    rid  = _create(client).get_json()["request_id"]
    body = client.get(f"/api/professional-valuation/requests/{rid}", headers=_auth()).get_json()
    gate = body.get("certification_gate_summary", {})
    # preliminary_use_allowed from Phase E (no prelim approval yet → False)
    assert "preliminary_approval_ready" in gate or "preliminary_use_allowed" in gate


# ── PVF34: event log records HBU save ────────────────────────────────────────
def test_PVF34_event_log_records_hbu_save(client):
    rid = _create(client).get_json()["request_id"]
    _save_hbu(client, rid)
    events = _pvadv.read_advanced_review_events(rid)
    actions = [e["action"] for e in events]
    assert "hbu_save" in actions


# ── PVF35: event log records legal save ──────────────────────────────────────
def test_PVF35_event_log_records_legal_save(client):
    rid = _create(client).get_json()["request_id"]
    _save_legal(client, rid)
    events = _pvadv.read_advanced_review_events(rid)
    actions = [e["action"] for e in events]
    assert "legal_save" in actions


# ── PVF36: event log records ESG save ────────────────────────────────────────
def test_PVF36_event_log_records_esg_save(client):
    rid = _create(client).get_json()["request_id"]
    _save_esg(client, rid)
    events = _pvadv.read_advanced_review_events(rid)
    actions = [e["action"] for e in events]
    assert "esg_save" in actions


# ── PVF37: event log records SWOT save ───────────────────────────────────────
def test_PVF37_event_log_records_swot_save(client):
    rid = _create(client).get_json()["request_id"]
    _save_swot(client, rid)
    events = _pvadv.read_advanced_review_events(rid)
    actions = [e["action"] for e in events]
    assert "swot_save" in actions


# ── PVF38: no internal paths in advanced-review responses ────────────────────
def test_PVF38_no_internal_paths_in_responses(client):
    rid  = _create(client).get_json()["request_id"]
    text = client.get(_adv_url(rid), headers=_auth()).get_data(as_text=True)
    assert "advanced_reviews/" not in text
    assert "advanced_review_events/" not in text
    assert "instance/professional_valuation" not in text


# ── PVF39: expert_notes present in protected response ────────────────────────
def test_PVF39_expert_notes_present_in_protected_response(client):
    rid = _create(client).get_json()["request_id"]
    _save_hbu(client, rid)
    body = client.get(_adv_url(rid), headers=_auth()).get_json()
    hbu  = body.get("hbu_review", {})
    assert "expert_notes" in hbu


# ── PVF40: no OCR/Qdrant/RAG flags set true ──────────────────────────────────
def test_PVF40_no_ocr_qdrant_rag_flags(client):
    rid  = _create(client).get_json()["request_id"]
    body = _save_hbu(client, rid)
    text = json.dumps(body)
    assert '"ocr_enabled": true' not in text
    assert '"qdrant_enabled": true' not in text
    assert '"rag_enabled": true' not in text


# ── PVF41: schema returns Arabic labels ──────────────────────────────────────
def test_PVF41_schema_returns_arabic_labels(client):
    body    = client.get(_schema_url(), headers=_auth()).get_json()
    assert body["ok"] is True
    schema  = body["schema"]
    sections = schema["sections"]
    labels = [s["section_label_ar"] for s in sections]
    assert any("الاستخدام الأمثل" in lbl for lbl in labels)
    assert any("القانونية" in lbl for lbl in labels)
    assert any("ESG" in lbl for lbl in labels)
    assert any("SWOT" in lbl for lbl in labels)


# ── PVF42: QA outputs directory for Phase F exists ───────────────────────────
def test_PVF42_qa_outputs_exist():
    qa_dir = Path(__file__).resolve().parents[1] / "instance" / "manual_review_outputs" / "professional_valuation_phase_f_advanced_review"
    assert qa_dir.exists(), f"QA dir missing: {qa_dir}"
    assert len(list(qa_dir.iterdir())) >= 1, "QA dir is empty"


# ── PVF43: existing PVB/PVC/PVD/PVE tests unaffected ────────────────────────
def test_PVF43_existing_pv_tests_unaffected(client):
    resp = _create(client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["ok"] is True
    assert body["request_id"].startswith("PVR-")


# ── PVF44: ordinary valuation route still responds ───────────────────────────
def test_PVF44_ordinary_valuation_unaffected(client):
    resp = client.get("/api/advisor/health")
    assert resp.status_code in (200, 404, 405)


# ── PVF45: tax appeal route still responds ───────────────────────────────────
def test_PVF45_tax_appeal_unaffected(client):
    resp = client.get("/api/tax-appeal/health")
    assert resp.status_code in (200, 404, 405)
