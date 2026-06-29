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
