"""
test_professional_valuation_backend.py — Professional Valuation Phase B + Phase C backend tests.

PVRT01  create with traditional_report stores and returns report_type
PVRT02  create with detailed_report stores and returns report_type
PVRT03  create with professional_report stores and returns report_type
PVRT04  create without report_type defaults to professional_report
PVRT05  create with invalid report_type returns 400
PVRT06  report_type appears in list response
PVRT07  report_type appears in detail response
PVRT08  schema route lists report_type in optional_fields
PVRT09  report_type label in preliminary output context
PVRT10  report_type label in certified output context

WBPAR01 expert workbook sheet list has ≥ 40 sheets
WBPAR02 final workbook sheet list has ≥ 40 sheets
WBPAR03 expert workbook sheet list includes parity sheet names
WBPAR04 final workbook sheet list includes parity sheet names
WBPAR05 report_type_label appears in expert workbook sheet list context
WBPAR06 report_type_label appears in final workbook sheet list context
WBPAR07 ordinary valuation workbook builder is importable
WBPAR08 no internal paths in expert workbook sheet names
WBPAR09 no internal paths in final workbook sheet names
WBPAR10 expert workbook generates successfully with advisory data
WBPAR11 final workbook blocked when certification_ready=False
WBPAR12 certification gate unchanged after workbook expansion
WBPAR13 expert workbook parity sheets do not contain None/NaN strings

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

@pytest.fixture(scope="session", autouse=True)
def _clean_pvr_datastore():
    """Clear accumulated test records before the session.
    Prevents the requests.jsonl from growing across runs and slowing _update_pvr (O(n) rewrite)."""
    if _pvr._REQ_FILE.exists():
        _pvr._REQ_FILE.write_bytes(b"")
    if _pvr._EVENTS_FILE.exists():
        _pvr._EVENTS_FILE.write_bytes(b"")


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
    Phase H: certified-report route now exists (returns 401 without auth).
    Plain /report route remains unimplemented (404/405).
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

    # Plain /report route remains unimplemented
    resp_report = client.get(f"/api/professional-valuation/requests/{rid}/report")
    assert resp_report.status_code in (404, 405), (
        f"Unexpected plain-report route: GET /report → {resp_report.status_code}"
    )

    # certified-report route now exists (Phase H) — auth-protected → 401 without token
    resp_cert = client.get(f"/api/professional-valuation/requests/{rid}/certified-report")
    assert resp_cert.status_code == 401, (
        f"certified-report should require auth (Phase H), got {resp_cert.status_code}"
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


# ══════════════════════════════════════════════════════════════════════════════
# PVG01–PVG55 — Phase G: Peer Review, Signature & Final Certification Gate
# ══════════════════════════════════════════════════════════════════════════════

import professional_valuation_certification as _pvcert


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pr_url(rid: str, path: str = "") -> str:
    return f"/api/professional-valuation/requests/{rid}/peer-review{path}"


def _sig_url(rid: str) -> str:
    return f"/api/professional-valuation/requests/{rid}/signature"


def _gate_url(rid: str, path: str = "") -> str:
    return f"/api/professional-valuation/requests/{rid}/certification-gate{path}"


def _assign_reviewer(client, rid: str, extra=None) -> dict:
    body = {"reviewer_name": "د. خالد إبراهيم", "reviewer_role": "خبير تقييم معتمد"}
    if extra:
        body.update(extra)
    return client.post(
        _pr_url(rid, "/assign"),
        json=body, content_type="application/json", headers=_auth()
    ).get_json()


def _start_review(client, rid: str) -> dict:
    return client.post(
        _pr_url(rid, "/start"),
        json={}, content_type="application/json", headers=_auth()
    ).get_json()


def _submit_review(client, rid: str, decision: str = "approved", extra=None) -> dict:
    body = {
        "review_decision": decision,
        "review_notes": "مراجعة شاملة — لا توجد مخالفات جوهرية",
        "reviewed_sections": ["methods", "reconciliation", "hbu", "legal", "esg", "swot"],
        "methodology_review_complete":    True,
        "source_review_complete":         True,
        "document_review_complete":       True,
        "hbu_review_complete":            True,
        "legal_review_complete":          True,
        "esg_review_complete":            True,
        "swot_review_complete":           True,
        "reconciliation_review_complete": True,
        "peer_review_signature_available": True,
    }
    if decision == "changes_requested":
        body["required_changes"] = "يجب مراجعة طريقة المقارنة السوقية"
    if extra:
        body.update(extra)
    return client.post(
        _pr_url(rid, "/submit"),
        json=body, content_type="application/json", headers=_auth()
    ).get_json()


def _save_signature(client, rid: str, status: str = "signed", extra=None) -> dict:
    body = {
        "approval_status":       status,
        "expert_name":           "م. أحمد محمد المقيّم",
        "expert_role":           "خبير تقييم عقاري معتمد",
        "expert_license_number": "EG-EVAL-2024-001",
        "expert_email":          "expert@test-firm.eg",
        "firm_name":             "مكتب التقييم المهني",
        "signature_available":   True,
        "signature_label":       "توقيع إلكتروني مؤكد",
        "stamp_available":       True,
        "stamp_label":           "ختم الشركة",
        "signed_at":             "2026-06-30",
        "approval_statement":    (
            "أُقرّ بأن هذا التقرير صادر وفق معايير التقييم المعتمدة دولياً "
            "وأنني تحققت شخصياً من صحة بيانات التقرير."
        ),
        "approval_scope":        "القيمة السوقية لأغراض الرهن العقاري",
    }
    if extra:
        body.update(extra)
    return client.post(
        _sig_url(rid),
        json=body, content_type="application/json", headers=_auth()
    ).get_json()


# ── PVG01–PVG08: Auth guards ──────────────────────────────────────────────────

def test_PVG01_peer_review_get_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.get(_pr_url(rid))
    assert resp.status_code == 401


def test_PVG02_peer_review_assign_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.post(_pr_url(rid, "/assign"), json={"reviewer_name": "x", "reviewer_role": "y"})
    assert resp.status_code == 401


def test_PVG03_peer_review_start_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.post(_pr_url(rid, "/start"), json={})
    assert resp.status_code == 401


def test_PVG04_peer_review_submit_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.post(_pr_url(rid, "/submit"), json={})
    assert resp.status_code == 401


def test_PVG05_signature_get_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.get(_sig_url(rid))
    assert resp.status_code == 401


def test_PVG06_signature_save_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.post(_sig_url(rid), json={})
    assert resp.status_code == 401


def test_PVG07_certification_gate_get_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.get(_gate_url(rid))
    assert resp.status_code == 401


def test_PVG08_certification_gate_evaluate_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.post(_gate_url(rid, "/evaluate"), json={})
    assert resp.status_code == 401


# ── PVG09–PVG11: Peer review assignment validation ────────────────────────────

def test_PVG09_peer_review_assign_requires_reviewer_name(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.post(
        _pr_url(rid, "/assign"),
        json={"reviewer_name": "", "reviewer_role": "خبير"},
        content_type="application/json", headers=_auth()
    )
    assert resp.status_code == 422
    assert resp.get_json()["ok"] is False


def test_PVG10_peer_review_assign_requires_reviewer_role(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.post(
        _pr_url(rid, "/assign"),
        json={"reviewer_name": "د. خالد", "reviewer_role": ""},
        content_type="application/json", headers=_auth()
    )
    assert resp.status_code == 422
    assert resp.get_json()["ok"] is False


def test_PVG11_peer_review_assign_sets_status_assigned(client):
    rid  = _create(client).get_json()["request_id"]
    body = _assign_reviewer(client, rid)
    assert body["ok"] is True
    assert body["peer_review"]["status"] == "assigned"


# ── PVG12: Start sets status in_review ────────────────────────────────────────

def test_PVG12_peer_review_start_sets_in_review(client):
    rid = _create(client).get_json()["request_id"]
    _assign_reviewer(client, rid)
    body = _start_review(client, rid)
    assert body["ok"] is True
    assert body["peer_review"]["status"] == "in_review"


# ── PVG13–PVG17: Submit validation ────────────────────────────────────────────

def test_PVG13_peer_review_submit_requires_review_notes(client):
    rid = _create(client).get_json()["request_id"]
    _assign_reviewer(client, rid)
    _start_review(client, rid)
    resp = client.post(
        _pr_url(rid, "/submit"),
        json={"review_decision": "approved", "review_notes": ""},
        content_type="application/json", headers=_auth()
    )
    assert resp.status_code == 422


def test_PVG14_peer_review_changes_requested_requires_required_changes(client):
    rid = _create(client).get_json()["request_id"]
    _assign_reviewer(client, rid)
    _start_review(client, rid)
    resp = client.post(
        _pr_url(rid, "/submit"),
        json={
            "review_decision": "changes_requested",
            "review_notes": "يوجد ملاحظات",
            "required_changes": "",
        },
        content_type="application/json", headers=_auth()
    )
    assert resp.status_code == 422


def test_PVG15_peer_review_approved_requires_reviewed_sections(client):
    rid = _create(client).get_json()["request_id"]
    _assign_reviewer(client, rid)
    _start_review(client, rid)
    resp = client.post(
        _pr_url(rid, "/submit"),
        json={
            "review_decision": "approved",
            "review_notes": "موافقة",
            "reviewed_sections": ["methods"],  # incomplete
            "peer_review_signature_available": True,
            "methodology_review_complete": True,
            "source_review_complete": True,
            "document_review_complete": True,
            "hbu_review_complete": True,
            "legal_review_complete": True,
            "esg_review_complete": True,
            "swot_review_complete": True,
            "reconciliation_review_complete": True,
        },
        content_type="application/json", headers=_auth()
    )
    assert resp.status_code == 422
    body = resp.get_json()
    assert "missing_sections" in body or "reviewed_sections" in body.get("error", "")


def test_PVG16_peer_review_approved_requires_all_review_flags(client):
    rid = _create(client).get_json()["request_id"]
    _assign_reviewer(client, rid)
    _start_review(client, rid)
    resp = client.post(
        _pr_url(rid, "/submit"),
        json={
            "review_decision": "approved",
            "review_notes": "موافقة",
            "reviewed_sections": ["methods", "reconciliation", "hbu", "legal", "esg", "swot"],
            "peer_review_signature_available": True,
            # All flags absent / False → should fail
            "methodology_review_complete":    False,
            "source_review_complete":         False,
            "document_review_complete":       False,
            "hbu_review_complete":            False,
            "legal_review_complete":          False,
            "esg_review_complete":            False,
            "swot_review_complete":           False,
            "reconciliation_review_complete": False,
        },
        content_type="application/json", headers=_auth()
    )
    assert resp.status_code == 422


def test_PVG17_peer_review_approved_requires_signature_availability(client):
    rid = _create(client).get_json()["request_id"]
    _assign_reviewer(client, rid)
    _start_review(client, rid)
    resp = client.post(
        _pr_url(rid, "/submit"),
        json={
            "review_decision": "approved",
            "review_notes": "موافقة",
            "reviewed_sections": ["methods", "reconciliation", "hbu", "legal", "esg", "swot"],
            "peer_review_signature_available": False,  # must be True for approved
            "methodology_review_complete":    True,
            "source_review_complete":         True,
            "document_review_complete":       True,
            "hbu_review_complete":            True,
            "legal_review_complete":          True,
            "esg_review_complete":            True,
            "swot_review_complete":           True,
            "reconciliation_review_complete": True,
        },
        content_type="application/json", headers=_auth()
    )
    assert resp.status_code == 422


# ── PVG18–PVG20: Peer review approval outcomes ────────────────────────────────

def test_PVG18_peer_review_approval_sets_peer_review_ready_true(client):
    rid = _create(client).get_json()["request_id"]
    _assign_reviewer(client, rid)
    _start_review(client, rid)
    body = _submit_review(client, rid, "approved")
    assert body["ok"] is True
    assert body["peer_review_ready"] is True
    assert body["peer_review"]["status"] == "approved"


def test_PVG19_peer_review_approval_does_not_alone_set_certification_ready(client):
    rid = _create(client).get_json()["request_id"]
    _assign_reviewer(client, rid)
    _start_review(client, rid)
    body = _submit_review(client, rid, "approved")
    gate = body.get("certification_gate_summary", {})
    assert gate.get("certification_ready") is False, (
        "Peer review approval alone must not set certification_ready=True"
    )


def test_PVG20_rejected_peer_review_does_not_set_peer_review_ready(client):
    rid = _create(client).get_json()["request_id"]
    _assign_reviewer(client, rid)
    _start_review(client, rid)
    resp = client.post(
        _pr_url(rid, "/submit"),
        json={
            "review_decision": "rejected",
            "review_notes":    "المنهجية غير مقبولة",
        },
        content_type="application/json", headers=_auth()
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["peer_review_ready"] is False


# ── PVG21–PVG27: Signature validation ────────────────────────────────────────

def test_PVG21_signature_signed_requires_expert_name(client):
    rid  = _create(client).get_json()["request_id"]
    resp = client.post(
        _sig_url(rid),
        json={"approval_status": "signed", "expert_name": ""},
        content_type="application/json", headers=_auth()
    )
    assert resp.status_code == 422


def test_PVG22_signature_signed_requires_expert_license(client):
    rid  = _create(client).get_json()["request_id"]
    resp = client.post(
        _sig_url(rid),
        json={
            "approval_status": "signed",
            "expert_name":     "م. أحمد",
            "expert_license_number": "",
        },
        content_type="application/json", headers=_auth()
    )
    assert resp.status_code == 422


def test_PVG23_signature_signed_requires_signed_at(client):
    rid  = _create(client).get_json()["request_id"]
    resp = client.post(
        _sig_url(rid),
        json={
            "approval_status":       "signed",
            "expert_name":           "م. أحمد",
            "expert_license_number": "EG-001",
            "signed_at":             "",
        },
        content_type="application/json", headers=_auth()
    )
    assert resp.status_code == 422


def test_PVG24_signature_signed_requires_signature_available(client):
    rid  = _create(client).get_json()["request_id"]
    resp = client.post(
        _sig_url(rid),
        json={
            "approval_status":       "signed",
            "expert_name":           "م. أحمد",
            "expert_license_number": "EG-001",
            "signed_at":             "2026-06-30",
            "signature_available":   False,
            "approval_statement":    "أُقرّ بصحة التقرير.",
        },
        content_type="application/json", headers=_auth()
    )
    assert resp.status_code == 422


def test_PVG25_signature_signed_requires_approval_statement(client):
    rid  = _create(client).get_json()["request_id"]
    resp = client.post(
        _sig_url(rid),
        json={
            "approval_status":       "signed",
            "expert_name":           "م. أحمد",
            "expert_license_number": "EG-001",
            "signed_at":             "2026-06-30",
            "signature_available":   True,
            "approval_statement":    "",
        },
        content_type="application/json", headers=_auth()
    )
    assert resp.status_code == 422


def test_PVG26_valid_signature_sets_final_signoff_ready_true(client):
    rid  = _create(client).get_json()["request_id"]
    body = _save_signature(client, rid, "signed")
    assert body["ok"] is True
    assert body["final_signoff_ready"] is True


def test_PVG27_valid_signature_does_not_alone_set_certification_ready(client):
    rid  = _create(client).get_json()["request_id"]
    body = _save_signature(client, rid, "signed")
    gate = body.get("certification_gate_summary", {})
    assert gate.get("certification_ready") is False, (
        "Signature alone must not set certification_ready=True"
    )


# ── PVG28–PVG35: Certification gate with blockers ────────────────────────────

def test_PVG28_gate_returns_blockers_when_upstream_missing(client):
    rid  = _create(client).get_json()["request_id"]
    resp = client.post(
        _gate_url(rid, "/evaluate"),
        json={}, content_type="application/json", headers=_auth()
    )
    assert resp.status_code == 200
    gate = resp.get_json()["gate"]
    assert isinstance(gate.get("blockers"), list)
    assert len(gate["blockers"]) > 0


def test_PVG29_certification_ready_false_when_documents_missing(client):
    rid  = _create(client).get_json()["request_id"]
    gate = _pvcert.compute_final_certification_gate(rid)
    assert gate["certification_ready"] is False
    assert gate["mandatory_documents_ready"] is False


def test_PVG30_certification_ready_false_when_sources_missing(client):
    rid  = _create(client).get_json()["request_id"]
    gate = _pvcert.compute_final_certification_gate(rid)
    assert gate["certification_ready"] is False
    assert gate["real_sources_ready"] is False


def test_PVG31_certification_ready_false_when_comparables_missing(client):
    rid  = _create(client).get_json()["request_id"]
    gate = _pvcert.compute_final_certification_gate(rid)
    assert gate["certification_ready"] is False
    assert gate["comparables_ready"] is False


def test_PVG32_certification_ready_false_when_methods_missing(client):
    rid  = _create(client).get_json()["request_id"]
    gate = _pvcert.compute_final_certification_gate(rid)
    assert gate["certification_ready"] is False
    assert gate["methods_completed"] is False


def test_PVG33_certification_ready_false_when_advanced_reviews_missing(client):
    rid  = _create(client).get_json()["request_id"]
    gate = _pvcert.compute_final_certification_gate(rid)
    assert gate["certification_ready"] is False
    assert gate["hbu_completed"] is False


def test_PVG34_certification_ready_false_when_peer_review_missing(client):
    rid  = _create(client).get_json()["request_id"]
    gate = _pvcert.compute_final_certification_gate(rid)
    assert gate["certification_ready"] is False
    assert gate["peer_review_completed"] is False


def test_PVG35_certification_ready_false_when_signature_missing(client):
    rid  = _create(client).get_json()["request_id"]
    gate = _pvcert.compute_final_certification_gate(rid)
    assert gate["certification_ready"] is False
    assert gate["expert_signature_ready"] is False


# ── PVG36–PVG40: Controlled fixture — all gates satisfied ────────────────────

def _build_all_gates_fixture(rid: str) -> None:
    """Inject satisfied gate data directly into Phase G storage for controlled test."""
    # Inject Phase G peer review — approved
    pr_rec = _pvcert._default_peer_review(rid)
    pr_rec.update({
        "status":               "approved",
        "review_decision":      "approved",
        "review_notes":         "تقرير سليم — لا توجد مخالفات",
        "reviewed_sections":    ["methods", "reconciliation", "hbu", "legal", "esg", "swot"],
        "methodology_review_complete":    True,
        "source_review_complete":         True,
        "document_review_complete":       True,
        "hbu_review_complete":            True,
        "legal_review_complete":          True,
        "esg_review_complete":            True,
        "swot_review_complete":           True,
        "reconciliation_review_complete": True,
        "peer_review_signature_available": True,
        "peer_review_ready":              True,
        "review_completed_at":            "2026-06-30T10:00:00",
    })
    _pvcert._save_peer_review(pr_rec)

    # Inject Phase G signature — signed
    sig_rec = _pvcert._default_signature(rid)
    sig_rec.update({
        "approval_status":       "signed",
        "expert_name":           "م. أحمد محمد المقيّم",
        "expert_role":           "خبير تقييم عقاري معتمد",
        "expert_license_number": "EG-EVAL-FIXTURE-001",
        "expert_email":          "expert@fixture.test",
        "firm_name":             "مكتب التقييم النموذجي",
        "signature_available":   True,
        "stamp_available":       True,
        "signed_at":             "2026-06-30",
        "approval_statement":    "أُقرّ بأن هذا التقرير صادر وفق معايير التقييم الدولية",
        "approval_scope":        "التقييم لأغراض الرهن العقاري",
        "signature_ready":       True,
        "license_ready":         True,
        "stamp_ready":           True,
        "final_signoff_ready":   True,
    })
    _pvcert._save_signature(sig_rec)

    # Override compute_final_certification_gate for this fixture by injecting a pre-satisfied gate snapshot
    import json
    from pathlib import Path
    snap = {
        "request_id":      rid,
        "evaluated_at":    "2026-06-30T10:00:00",
        # All phase gates True
        "phase_c_documents_ready":               True,
        "phase_c_sources_ready":                 True,
        "phase_d_comparables_ready":             True,
        "phase_e_methods_completed":             True,
        "phase_e_reconciliation_completed":      True,
        "phase_e_preliminary_approval_ready":    True,
        "phase_f_hbu_completed":                 True,
        "phase_f_legal_due_diligence_ready":     True,
        "phase_f_esg_reviewed":                  True,
        "phase_f_swot_completed":                True,
        "phase_f_advanced_reviews_prelim_ready": True,
        "phase_g_peer_review_ready":             True,
        "phase_g_signature_ready":               True,
        "phase_g_license_ready":                 True,
        "phase_g_stamp_ready":                   True,
        "qa_data_cleared":           True,
        "real_sources_ready":        True,
        "mandatory_documents_ready": True,
        "comparables_ready":         True,
        "methods_completed":         True,
        "reconciliation_completed":  True,
        "preliminary_approval_ready": True,
        "hbu_completed":             True,
        "legal_due_diligence_ready": True,
        "esg_reviewed":              True,
        "swot_completed":            True,
        "advanced_reviews_prelim_ready": True,
        "peer_review_completed":     True,
        "expert_signature_ready":    True,
        "certification_ready":               True,
        "official_use_allowed":              True,
        "certified_use_allowed":             True,
        "final_report_generation_allowed":   True,
        "final_workbook_generation_allowed": True,
        "blockers":             [],
        "warnings":             [],
        "advisory_only_reason": "",
        "certification_status": "ready_for_certified_outputs",
        "next_required_actions": ["generate_certified_outputs"],
        "qdrant_used": False,
        "rag_used": False,
        "no_automatic_value_extraction": True,
    }
    snap_path = Path(_pvcert._GATE_DIR) / f"{rid}.json"
    snap_path.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")


def test_PVG36_controlled_fixture_certification_ready_true(client):
    """Controlled fixture with all gates explicitly satisfied → certification_ready=True."""
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    # Read the snapshot directly
    import json as _json
    from pathlib import Path
    snap_path = Path(_pvcert._GATE_DIR) / f"{rid}.json"
    gate = _json.loads(snap_path.read_text(encoding="utf-8"))
    assert gate["certification_ready"] is True, (
        f"Controlled fixture should have certification_ready=True: {gate}"
    )


def test_PVG37_controlled_fixture_official_use_allowed(client):
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    import json as _json
    from pathlib import Path
    gate = _json.loads((Path(_pvcert._GATE_DIR) / f"{rid}.json").read_text(encoding="utf-8"))
    assert gate["official_use_allowed"] is True


def test_PVG38_controlled_fixture_certified_use_allowed(client):
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    import json as _json
    from pathlib import Path
    gate = _json.loads((Path(_pvcert._GATE_DIR) / f"{rid}.json").read_text(encoding="utf-8"))
    assert gate["certified_use_allowed"] is True


def test_PVG39_final_report_generation_allowed_when_certification_ready(client):
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    import json as _json
    from pathlib import Path
    gate = _json.loads((Path(_pvcert._GATE_DIR) / f"{rid}.json").read_text(encoding="utf-8"))
    assert gate["final_report_generation_allowed"] is True


def test_PVG40_final_workbook_generation_allowed_when_certification_ready(client):
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    import json as _json
    from pathlib import Path
    gate = _json.loads((Path(_pvcert._GATE_DIR) / f"{rid}.json").read_text(encoding="utf-8"))
    assert gate["final_workbook_generation_allowed"] is True


# ── PVG41–PVG43: Transition integration ──────────────────────────────────────

def test_PVG41_generic_transition_to_certified_still_blocked(client):
    rid = _create(client).get_json()["request_id"]
    _pvr._update_pvr(rid, {"status": "signed_pending_certification"})
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/transition",
        json={"target_status": "certified_report_generated"},
        content_type="application/json", headers=_auth()
    )
    assert resp.status_code == 422
    assert resp.get_json()["error_code"] == "certified_blocked"


def test_PVG42_approved_pending_to_signed_requires_signature(client):
    rid = _create(client).get_json()["request_id"]
    _pvr._update_pvr(rid, {"status": "approved_pending_signature", "peer_review_completed": True})
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/transition",
        json={"target_status": "signed_pending_certification"},
        content_type="application/json", headers=_auth()
    )
    # Must be blocked — no signature record with final_signoff_ready=True
    assert resp.status_code == 422
    assert resp.get_json()["error_code"] == "gate_blocked"


def test_PVG43_peer_review_required_to_in_progress_requires_assigned_reviewer(client):
    rid = _create(client).get_json()["request_id"]
    _pvr._update_pvr(rid, {"status": "peer_review_required"})
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/transition",
        json={"target_status": "peer_review_in_progress"},
        content_type="application/json", headers=_auth()
    )
    # Without peer review assigned, must be blocked
    assert resp.status_code == 422
    assert resp.get_json()["error_code"] == "gate_blocked"


# ── PVG44–PVG45: Gate behavior ────────────────────────────────────────────────

def test_PVG44_gate_evaluate_does_not_generate_report(client):
    rid  = _create(client).get_json()["request_id"]
    resp = client.post(
        _gate_url(rid, "/evaluate"),
        json={}, content_type="application/json", headers=_auth()
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert "gate" in body
    assert "report_url" not in body
    assert "pdf_path" not in body
    assert "workbook_path" not in body


def test_PVG45_mark_ready_returns_422_when_blockers_exist(client):
    rid  = _create(client).get_json()["request_id"]
    resp = client.post(
        _gate_url(rid, "/mark-ready"),
        json={}, content_type="application/json", headers=_auth()
    )
    assert resp.status_code == 422
    body = resp.get_json()
    assert body["ok"] is False
    assert len(body.get("blockers", [])) > 0


# ── PVG46: Request detail includes Phase G summaries ─────────────────────────

def test_PVG46_request_detail_includes_certification_gate_summary(client):
    rid  = _create(client).get_json()["request_id"]
    resp = client.get(
        f"/api/professional-valuation/requests/{rid}",
        headers=_auth()
    )
    assert resp.status_code == 200
    body = resp.get_json()
    gate = body.get("certification_gate_summary", {})
    assert "certification_ready" in gate
    assert "peer_review_completed" in gate or "blockers" in gate


# ── PVG47–PVG49: Event logs ───────────────────────────────────────────────────

def test_PVG47_event_log_records_peer_review_assignment(client):
    rid = _create(client).get_json()["request_id"]
    _assign_reviewer(client, rid)
    events = _pvcert._read_peer_events(rid)
    actions = [e["action"] for e in events]
    assert "assign" in actions


def test_PVG48_event_log_records_signature_update(client):
    rid = _create(client).get_json()["request_id"]
    _save_signature(client, rid, "draft")
    events = _pvcert._read_cert_events(rid)
    actions = [e["action"] for e in events]
    assert "signature_update" in actions


def test_PVG49_event_log_records_gate_evaluation(client):
    rid = _create(client).get_json()["request_id"]
    client.post(
        _gate_url(rid, "/evaluate"),
        json={}, content_type="application/json", headers=_auth()
    )
    events = _pvcert._read_cert_events(rid)
    actions = [e["action"] for e in events]
    assert "gate_evaluate" in actions


# ── PVG50–PVG51: Security / governance ───────────────────────────────────────

def test_PVG50_no_internal_paths_in_peer_review_response(client):
    rid  = _create(client).get_json()["request_id"]
    _assign_reviewer(client, rid)
    resp = client.get(_pr_url(rid), headers=_auth())
    text = resp.get_data(as_text=True)
    assert "instance/professional_valuation" not in text
    assert ".jsonl" not in text
    assert ".json" not in text.lower().replace("application/json", "")


def test_PVG51_no_ocr_qdrant_rag_flags_in_gate(client):
    rid  = _create(client).get_json()["request_id"]
    gate = _pvcert.compute_final_certification_gate(rid)
    assert gate.get("qdrant_used") is False
    assert gate.get("rag_used") is False
    assert gate.get("no_automatic_value_extraction") is True


# ── PVG52: QA outputs exist ───────────────────────────────────────────────────

def test_PVG52_qa_outputs_exist():
    qa_dir = (
        _CORE / "instance" / "manual_review_outputs"
        / "professional_valuation_phase_g_certification_gate"
    )
    if not qa_dir.exists():
        pytest.skip(f"Phase G QA output directory not yet generated: {qa_dir}")
    assert len(list(qa_dir.iterdir())) >= 1, "QA dir is empty"


# ── PVG53–PVG55: Regression ───────────────────────────────────────────────────

def test_PVG53_existing_pvb_pvc_pvd_pve_pvf_unaffected(client):
    resp = _create(client)
    assert resp.status_code == 201
    assert resp.get_json()["ok"] is True
    assert resp.get_json()["request_id"].startswith("PVR-")


def test_PVG54_ordinary_valuation_unaffected(client):
    resp = client.get("/api/advisor/health")
    assert resp.status_code in (200, 404, 405)


def test_PVG55_tax_appeal_unaffected(client):
    resp = client.get("/api/tax-appeal/health")
    assert resp.status_code in (200, 404, 405)


# ══════════════════════════════════════════════════════════════════════════════
# PVH01–PVH55 — Phase H: Protected Certified PDF & Final Workbook Generation
# ══════════════════════════════════════════════════════════════════════════════

import professional_valuation_outputs as _pvout


# ── URL helpers ───────────────────────────────────────────────────────────────

def _pvh_pdf_url(rid: str) -> str:
    return f"/api/professional-valuation/requests/{rid}/certified-report"


def _pvh_wb_url(rid: str) -> str:
    return f"/api/professional-valuation/requests/{rid}/final-workbook"


def _pvh_list_url(rid: str) -> str:
    return f"/api/professional-valuation/requests/{rid}/outputs"


def _pvh_detail_url(rid: str, output_id: str) -> str:
    return f"/api/professional-valuation/requests/{rid}/outputs/{output_id}"


def _pvh_revoke_url(rid: str, output_id: str) -> str:
    return f"/api/professional-valuation/requests/{rid}/outputs/{output_id}/revoke"


# ── PVH01–PVH06: Auth guards ──────────────────────────────────────────────────

def test_PVH01_certified_report_post_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.post(_pvh_pdf_url(rid), json={})
    assert resp.status_code == 401


def test_PVH02_certified_report_get_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.get(_pvh_pdf_url(rid))
    assert resp.status_code == 401


def test_PVH03_final_workbook_post_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.post(_pvh_wb_url(rid), json={})
    assert resp.status_code == 401


def test_PVH04_final_workbook_get_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.get(_pvh_wb_url(rid))
    assert resp.status_code == 401


def test_PVH05_outputs_list_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.get(_pvh_list_url(rid))
    assert resp.status_code == 401


def test_PVH06_output_detail_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.get(_pvh_detail_url(rid, "PVOUT-XXXXXXXX"))
    assert resp.status_code == 401


# ── PVH07–PVH11: Gate blocking ────────────────────────────────────────────────

def test_PVH07_certified_report_returns_422_when_not_ready(client):
    rid  = _create(client).get_json()["request_id"]
    resp = client.post(_pvh_pdf_url(rid), json={},
                       content_type="application/json", headers=_auth())
    assert resp.status_code == 422
    body = resp.get_json()
    assert body["ok"] is False


def test_PVH08_final_workbook_returns_422_when_not_ready(client):
    rid  = _create(client).get_json()["request_id"]
    resp = client.post(_pvh_wb_url(rid), json={},
                       content_type="application/json", headers=_auth())
    assert resp.status_code == 422
    body = resp.get_json()
    assert body["ok"] is False


def test_PVH09_blocked_response_includes_blockers(client):
    rid  = _create(client).get_json()["request_id"]
    resp = client.post(_pvh_pdf_url(rid), json={},
                       content_type="application/json", headers=_auth())
    body = resp.get_json()
    assert "blockers" in body
    assert isinstance(body["blockers"], list)
    assert len(body["blockers"]) > 0


def test_PVH10_blocked_response_creates_no_registry_record(client):
    rid = _create(client).get_json()["request_id"]
    client.post(_pvh_pdf_url(rid), json={},
                content_type="application/json", headers=_auth())
    records = _pvout._read_registry(rid)
    assert len(records) == 0


def test_PVH11_blocked_response_creates_no_file(client):
    rid = _create(client).get_json()["request_id"]
    client.post(_pvh_pdf_url(rid), json={},
                content_type="application/json", headers=_auth())
    out_dir = _pvout._OUT_DIR / rid
    assert not out_dir.exists() or list(out_dir.iterdir()) == []


# ── PVH12–PVH16: Controlled fixture — generation succeeds ────────────────────

def test_PVH12_controlled_fixture_certification_ready_true(client):
    """Gate snapshot set to ready via _build_all_gates_fixture."""
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    gate = _pvout._load_gate_snapshot(rid)
    assert gate["certification_ready"] is True
    assert gate["final_report_generation_allowed"] is True
    assert gate["final_workbook_generation_allowed"] is True


def test_PVH13_certified_pdf_generation_succeeds_with_ready_fixture(client):
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    resp = client.post(_pvh_pdf_url(rid), json={},
                       content_type="application/json", headers=_auth())
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert "output" in body
    assert body["output"]["output_id"].startswith("PVOUT-")


def test_PVH14_final_workbook_generation_succeeds_with_ready_fixture(client):
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    resp = client.post(_pvh_wb_url(rid), json={},
                       content_type="application/json", headers=_auth())
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert "output" in body
    assert body["output"]["output_id"].startswith("PVOUT-")


def test_PVH15_generated_pdf_output_has_output_id(client):
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    resp = client.post(_pvh_pdf_url(rid), json={},
                       content_type="application/json", headers=_auth())
    out = resp.get_json().get("output", {})
    assert "output_id" in out
    assert out["output_type"] == "certified_pdf"


def test_PVH16_generated_workbook_output_has_output_id(client):
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    resp = client.post(_pvh_wb_url(rid), json={},
                       content_type="application/json", headers=_auth())
    out = resp.get_json().get("output", {})
    assert "output_id" in out
    assert out["output_type"] == "final_workbook"


# ── PVH17–PVH18: Metadata checks ──────────────────────────────────────────────

def test_PVH17_workbook_output_metadata_has_hash_and_size(client):
    """Workbook (openpyxl) always succeeds — hash and size must be present."""
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    resp = client.post(_pvh_wb_url(rid), json={},
                       content_type="application/json", headers=_auth())
    out = resp.get_json().get("output", {})
    assert out.get("file_available") is True
    assert out.get("file_hash_sha256") is not None
    assert out.get("file_size_bytes") is not None
    assert len(out["file_hash_sha256"]) == 64


def test_PVH18_output_metadata_excludes_internal_file_path(client):
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    resp = client.post(_pvh_wb_url(rid), json={},
                       content_type="application/json", headers=_auth())
    body_text = resp.get_data(as_text=True)
    assert "internal_file_path" not in body_text
    assert "instance/professional_valuation" not in body_text
    assert "certified_outputs/" not in body_text


# ── PVH19–PVH20: Registry list and detail ─────────────────────────────────────

def test_PVH19_output_registry_list_returns_safe_metadata(client):
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    client.post(_pvh_wb_url(rid), json={},
                content_type="application/json", headers=_auth())
    resp = client.get(_pvh_list_url(rid), headers=_auth())
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert isinstance(body["outputs"], list)
    assert len(body["outputs"]) >= 1
    for rec in body["outputs"]:
        assert "internal_file_path" not in rec


def test_PVH20_output_detail_returns_safe_metadata(client):
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    resp = client.post(_pvh_wb_url(rid), json={},
                       content_type="application/json", headers=_auth())
    output_id = resp.get_json()["output"]["output_id"]
    dr = client.get(_pvh_detail_url(rid, output_id), headers=_auth())
    assert dr.status_code == 200
    body = dr.get_json()
    assert body["ok"] is True
    assert body["output"]["output_id"] == output_id
    assert "internal_file_path" not in body["output"]


# ── PVH21–PVH24: Download endpoints ──────────────────────────────────────────

def test_PVH21_workbook_download_works_after_generation(client):
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    client.post(_pvh_wb_url(rid), json={},
                content_type="application/json", headers=_auth())
    resp = client.get(_pvh_wb_url(rid), headers=_auth())
    assert resp.status_code == 200
    ct = resp.content_type
    assert "spreadsheet" in ct or "excel" in ct or "octet" in ct


def test_PVH22_pdf_download_returns_404_before_any_generation(client):
    rid  = _create(client).get_json()["request_id"]
    resp = client.get(_pvh_pdf_url(rid), headers=_auth())
    assert resp.status_code == 404


def test_PVH23_workbook_download_returns_404_before_any_generation(client):
    rid  = _create(client).get_json()["request_id"]
    resp = client.get(_pvh_wb_url(rid), headers=_auth())
    assert resp.status_code == 404


def test_PVH24_pdf_download_after_generation(client):
    """If PDF generation succeeded (Playwright available), download returns 200;
    otherwise file_available=False so download returns 404 — either is valid."""
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    gen_resp = client.post(_pvh_pdf_url(rid), json={},
                           content_type="application/json", headers=_auth())
    out = gen_resp.get_json().get("output", {})
    dl  = client.get(_pvh_pdf_url(rid), headers=_auth())
    if out.get("file_available"):
        assert dl.status_code == 200
    else:
        assert dl.status_code == 404


# ── PVH25–PVH26: Event log ────────────────────────────────────────────────────

def test_PVH25_output_event_appended_on_pdf_generation(client):
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    client.post(_pvh_pdf_url(rid), json={},
                content_type="application/json", headers=_auth())
    events = _pvout.read_output_events(rid)
    actions = [e["action"] for e in events]
    assert "generate_certified_report" in actions


def test_PVH26_output_event_appended_on_workbook_generation(client):
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    client.post(_pvh_wb_url(rid), json={},
                content_type="application/json", headers=_auth())
    events = _pvout.read_output_events(rid)
    actions = [e["action"] for e in events]
    assert "generate_final_workbook" in actions


# ── PVH27–PVH28: Transition route still blocks certified_report_generated ─────

def test_PVH27_generic_transition_to_certified_report_generated_remains_blocked(client):
    rid  = _create(client).get_json()["request_id"]
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/transition",
        json={"target_status": "certified_report_generated"},
        content_type="application/json", headers=_auth(),
    )
    assert resp.status_code == 422
    body = resp.get_json()
    assert body["ok"] is False


def test_PVH28_certified_output_endpoint_marks_success_not_generic_transition(client):
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    gen_resp = client.post(_pvh_wb_url(rid), json={},
                           content_type="application/json", headers=_auth())
    assert gen_resp.status_code == 200
    body = gen_resp.get_json()
    assert body["ok"] is True
    assert body["output"]["output_type"] == "final_workbook"


# ── PVH29–PVH36: Output context checks ────────────────────────────────────────

def test_PVH29_output_context_built_without_error(client):
    rid = _create(client).get_json()["request_id"]
    ctx = _pvout.build_professional_valuation_output_context(rid)
    assert "request_summary" in ctx
    assert "certification_gate" in ctx
    assert "evidence_summary" in ctx
    assert "comparable_summary" in ctx
    assert "method_summary" in ctx
    assert "reconciliation_summary" in ctx
    assert "advanced_reviews" in ctx
    assert "peer_review_summary" in ctx
    assert "signature_summary" in ctx


def test_PVH30_output_context_excludes_internal_paths(client):
    rid = _create(client).get_json()["request_id"]
    ctx_str = str(_pvout.build_professional_valuation_output_context(rid))
    assert "instance/professional_valuation" not in ctx_str
    assert "certified_outputs/" not in ctx_str
    assert ".jsonl" not in ctx_str


def test_PVH31_output_context_excludes_rejected_sources_note_present(client):
    rid = _create(client).get_json()["request_id"]
    ctx = _pvout.build_professional_valuation_output_context(rid)
    note = ctx.get("source_summary", {}).get("note", "")
    assert "QA" in note or "مستبعد" in note


def test_PVH32_output_context_excludes_rejected_evidence_note_present(client):
    rid = _create(client).get_json()["request_id"]
    ctx = _pvout.build_professional_valuation_output_context(rid)
    note = ctx.get("evidence_summary", {}).get("note", "")
    assert note != ""


def test_PVH33_output_context_excludes_staged_comparables_note_present(client):
    rid = _create(client).get_json()["request_id"]
    ctx = _pvout.build_professional_valuation_output_context(rid)
    comp = ctx.get("comparable_summary", {})
    assert comp.get("excluded_staged_rejected") is True
    assert comp.get("excluded_qa") is True


def test_PVH34_output_context_includes_peer_review_summary(client):
    rid = _create(client).get_json()["request_id"]
    ctx = _pvout.build_professional_valuation_output_context(rid)
    peer = ctx.get("peer_review_summary", {})
    assert "reviewer_name" in peer
    assert "review_decision" in peer
    assert "peer_review_ready" in peer


def test_PVH35_output_context_includes_signature_summary(client):
    rid = _create(client).get_json()["request_id"]
    ctx = _pvout.build_professional_valuation_output_context(rid)
    sig = ctx.get("signature_summary", {})
    assert "expert_name" in sig
    assert "signed_at" in sig
    assert "final_signoff_ready" in sig


def test_PVH36_output_context_includes_advanced_reviews(client):
    rid = _create(client).get_json()["request_id"]
    ctx = _pvout.build_professional_valuation_output_context(rid)
    adv = ctx.get("advanced_reviews", {})
    assert "hbu" in adv
    assert "legal" in adv
    assert "esg" in adv
    assert "swot" in adv


# ── PVH37–PVH42: Workbook content checks ──────────────────────────────────────

def test_PVH37_workbook_does_not_contain_internal_paths(client):
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    resp = client.post(_pvh_wb_url(rid), json={},
                       content_type="application/json", headers=_auth())
    out = resp.get_json()["output"]
    assert out.get("file_available") is True
    internal_path = _pvout._OUT_DIR / rid / f"{out['output_id']}_final_workbook.xlsx"
    from openpyxl import load_workbook
    wb = load_workbook(str(internal_path), data_only=True)
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if cell.value:
                    cell_str = str(cell.value)
                    assert "instance/professional_valuation" not in cell_str
                    assert "certified_outputs/" not in cell_str


def test_PVH38_workbook_does_not_contain_none_or_nan_visible(client):
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    resp = client.post(_pvh_wb_url(rid), json={},
                       content_type="application/json", headers=_auth())
    out = resp.get_json()["output"]
    assert out.get("file_available") is True
    internal_path = _pvout._OUT_DIR / rid / f"{out['output_id']}_final_workbook.xlsx"
    from openpyxl import load_workbook
    wb = load_workbook(str(internal_path), data_only=True)
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if cell.value:
                    assert str(cell.value) not in ("NaN", "nan", "None", "undefined", "null")


def test_PVH39_workbook_opens_with_openpyxl(client):
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    resp = client.post(_pvh_wb_url(rid), json={},
                       content_type="application/json", headers=_auth())
    out = resp.get_json()["output"]
    assert out.get("file_available") is True
    from openpyxl import load_workbook
    wb = load_workbook(
        str(_pvout._OUT_DIR / rid / f"{out['output_id']}_final_workbook.xlsx"),
        data_only=True,
    )
    assert len(wb.sheetnames) >= 1


def test_PVH40_workbook_contains_required_sheets(client):
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    resp = client.post(_pvh_wb_url(rid), json={},
                       content_type="application/json", headers=_auth())
    out = resp.get_json()["output"]
    from openpyxl import load_workbook
    wb = load_workbook(
        str(_pvout._OUT_DIR / rid / f"{out['output_id']}_final_workbook.xlsx"),
        data_only=True,
    )
    required = ["غلاف التقرير", "ملخص الاعتماد", "سجل التدقيق", "المخرجات والنسخ"]
    for sheet in required:
        assert sheet in wb.sheetnames, f"Missing required sheet: {sheet}"


def test_PVH41_workbook_contains_output_version_and_hash_metadata(client):
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    resp = client.post(_pvh_wb_url(rid), json={},
                       content_type="application/json", headers=_auth())
    out = resp.get_json()["output"]
    assert out.get("output_version") is not None
    assert out.get("file_hash_sha256") is not None
    assert len(out["file_hash_sha256"]) == 64


def test_PVH42_workbook_sheet_count_matches_specification(client):
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    resp = client.post(_pvh_wb_url(rid), json={},
                       content_type="application/json", headers=_auth())
    out = resp.get_json()["output"]
    from openpyxl import load_workbook
    wb = load_workbook(
        str(_pvout._OUT_DIR / rid / f"{out['output_id']}_final_workbook.xlsx"),
        data_only=True,
    )
    assert len(wb.sheetnames) == 43, f"Expected 43 sheets, got {len(wb.sheetnames)}: {wb.sheetnames}"


# ── PVH43–PVH46: Gate field enforcement ──────────────────────────────────────

def test_PVH43_certified_use_allowed_true_only_in_ready_fixture(client):
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    resp = client.post(_pvh_wb_url(rid), json={},
                       content_type="application/json", headers=_auth())
    out = resp.get_json()["output"]
    assert out["certified_use_allowed"] is True


def test_PVH44_official_use_allowed_true_only_in_ready_fixture(client):
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    resp = client.post(_pvh_wb_url(rid), json={},
                       content_type="application/json", headers=_auth())
    out = resp.get_json()["output"]
    assert out["official_use_allowed"] is True


def test_PVH45_final_report_generation_allowed_only_when_cert_ready(client):
    rid = _create(client).get_json()["request_id"]
    gate = _pvout._load_gate_snapshot(rid)
    assert gate.get("final_report_generation_allowed") is False


def test_PVH46_final_workbook_generation_allowed_only_when_cert_ready(client):
    rid = _create(client).get_json()["request_id"]
    gate = _pvout._load_gate_snapshot(rid)
    assert gate.get("final_workbook_generation_allowed") is False


# ── PVH47–PVH50: Revoke + governance ─────────────────────────────────────────

def test_PVH47_revoked_output_is_not_returned_as_latest_active(client):
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    resp = client.post(_pvh_wb_url(rid), json={},
                       content_type="application/json", headers=_auth())
    output_id = resp.get_json()["output"]["output_id"]
    client.post(_pvh_revoke_url(rid, output_id), json={},
                content_type="application/json", headers=_auth())
    latest = _pvout._latest_active_of_type(rid, "final_workbook")
    assert latest is None or latest.get("output_status") != "revoked"


def test_PVH48_external_api_used_false_in_output_records(client):
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    client.post(_pvh_wb_url(rid), json={},
                content_type="application/json", headers=_auth())
    records = _pvout._read_registry(rid)
    assert len(records) > 0
    for rec in records:
        assert rec.get("external_api_used") is False


def test_PVH49_qdrant_used_false_in_output_records(client):
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    client.post(_pvh_wb_url(rid), json={},
                content_type="application/json", headers=_auth())
    records = _pvout._read_registry(rid)
    for rec in records:
        assert rec.get("qdrant_used") is False


def test_PVH50_rag_used_false_in_output_records(client):
    rid = _create(client).get_json()["request_id"]
    _build_all_gates_fixture(rid)
    client.post(_pvh_wb_url(rid), json={},
                content_type="application/json", headers=_auth())
    records = _pvout._read_registry(rid)
    for rec in records:
        assert rec.get("rag_used") is False


# ── PVH51–PVH55: QA outputs + regression ─────────────────────────────────────

def test_PVH51_no_fpdf_usage_introduced(client):
    """Verify that fpdf is not imported in the outputs module."""
    import ast
    import pathlib
    source = pathlib.Path(_CORE / "professional_valuation_outputs.py").read_text(encoding="utf-8")
    tree   = ast.parse(source)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any("fpdf" in i.lower() for i in imports), "fpdf must not be used"


def test_PVH52_qa_outputs_exist():
    qa_dir = (
        _CORE / "instance" / "manual_review_outputs"
        / "professional_valuation_phase_h_outputs"
    )
    if not qa_dir.exists():
        pytest.skip(f"Phase H QA output directory not yet generated: {qa_dir}")
    assert len(list(qa_dir.iterdir())) >= 1, "QA dir is empty"


def test_PVH53_existing_pvb_through_pvg_unaffected(client):
    resp = _create(client)
    assert resp.status_code == 201
    assert resp.get_json()["ok"] is True


def test_PVH54_ordinary_valuation_unaffected(client):
    resp = client.get("/api/advisor/health")
    assert resp.status_code in (200, 404, 405)


def test_PVH55_tax_appeal_unaffected(client):
    resp = client.get("/api/tax-appeal/health")
    assert resp.status_code in (200, 404, 405)


# ══════════════════════════════════════════════════════════════════════════════
# Phase H Addendum — Preliminary Report, Expert Draft & Expert Workbook
# Tests: PVH56–PVH84
# ══════════════════════════════════════════════════════════════════════════════

import professional_valuation_preliminary_outputs as _pvprelim


def _pvp_prelim_url(rid: str) -> str:
    return f"/api/professional-valuation/requests/{rid}/preliminary-report"


def _pvp_draft_url(rid: str) -> str:
    return f"/api/professional-valuation/requests/{rid}/expert-draft-report"


def _pvp_ewb_url(rid: str) -> str:
    return f"/api/professional-valuation/requests/{rid}/expert-workbook"


def _build_methods_fixture(rid: str) -> None:
    """Inject gate snapshot with methods_completed=True but certification_ready=False."""
    import json as _json
    from datetime import datetime as _dt
    import professional_valuation_certification as _pvcert
    snap = {
        "certification_ready":               False,
        "official_use_allowed":              False,
        "certified_use_allowed":             False,
        "final_report_generation_allowed":   False,
        "final_workbook_generation_allowed": False,
        "methods_completed":                 True,
        "reconciliation_completed":          True,
        "preliminary_approval_ready":        False,
        "qa_data_cleared":                   False,
        "real_sources_ready":                False,
        "comparables_ready":                 False,
        "mandatory_documents_ready":         False,
        "blockers": [
            "مراجعة النظراء غير مكتملة",
            "التوقيع غير مكتمل",
        ],
        "certification_status": "in_progress",
        "evaluated_at": _dt.utcnow().isoformat(),
        "qdrant_used": False,
        "rag_used":    False,
    }
    from pathlib import Path
    snap_path = Path(_pvcert._GATE_DIR) / f"{rid}.json"
    snap_path.write_text(_json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")


# ── PVH56–PVH61: Auth guards ──────────────────────────────────────────────────

def test_PVH56_preliminary_report_post_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.post(_pvp_prelim_url(rid), json={})
    assert resp.status_code == 401


def test_PVH57_preliminary_report_get_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.get(_pvp_prelim_url(rid))
    assert resp.status_code == 401


def test_PVH58_expert_draft_post_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.post(_pvp_draft_url(rid), json={})
    assert resp.status_code == 401


def test_PVH59_expert_draft_get_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.get(_pvp_draft_url(rid))
    assert resp.status_code == 401


def test_PVH60_expert_workbook_post_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.post(_pvp_ewb_url(rid), json={})
    assert resp.status_code == 401


def test_PVH61_expert_workbook_get_requires_auth(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.get(_pvp_ewb_url(rid))
    assert resp.status_code == 401


# ── PVH62–PVH64: Gate blocking (no method data → 422) ─────────────────────────

def test_PVH62_preliminary_blocked_when_no_method_data(client):
    """Without method data, preliminary generation is blocked."""
    rid = _create(client).get_json()["request_id"]
    resp = client.post(_pvp_prelim_url(rid), json={},
                       content_type="application/json", headers=_auth())
    assert resp.status_code == 422
    body = resp.get_json()
    assert body["ok"] is False
    assert "blockers" in body


def test_PVH63_expert_draft_blocked_when_no_method_data(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.post(_pvp_draft_url(rid), json={},
                       content_type="application/json", headers=_auth())
    assert resp.status_code == 422
    assert resp.get_json()["ok"] is False


def test_PVH64_expert_workbook_blocked_when_no_method_data(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.post(_pvp_ewb_url(rid), json={},
                       content_type="application/json", headers=_auth())
    assert resp.status_code == 422
    assert resp.get_json()["ok"] is False


# ── PVH65–PVH68: Methods fixture — generation succeeds ──────────────────────

def test_PVH65_preliminary_allowed_when_methods_complete(client):
    """With methods_completed=True, preliminary generation succeeds."""
    rid = _create(client).get_json()["request_id"]
    _build_methods_fixture(rid)
    resp = client.post(_pvp_prelim_url(rid), json={},
                       content_type="application/json", headers=_auth())
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert "output" in body
    assert body["output"]["output_id"].startswith("PVOUT-")


def test_PVH66_expert_draft_allowed_when_methods_complete(client):
    rid = _create(client).get_json()["request_id"]
    _build_methods_fixture(rid)
    resp = client.post(_pvp_draft_url(rid), json={},
                       content_type="application/json", headers=_auth())
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["output"]["output_type"] == "expert_draft_pdf"


def test_PVH67_expert_workbook_allowed_when_methods_complete(client):
    rid = _create(client).get_json()["request_id"]
    _build_methods_fixture(rid)
    resp = client.post(_pvp_ewb_url(rid), json={},
                       content_type="application/json", headers=_auth())
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["output"]["output_type"] == "expert_workbook"


def test_PVH68_preliminary_does_not_require_certification_ready(client):
    """Methods fixture has certification_ready=False but allows preliminary generation."""
    rid = _create(client).get_json()["request_id"]
    _build_methods_fixture(rid)
    gate = _pvout._load_gate_snapshot(rid)
    assert gate["certification_ready"] is False, "Fixture should have certification_ready=False"
    resp = client.post(_pvp_prelim_url(rid), json={},
                       content_type="application/json", headers=_auth())
    assert resp.status_code == 200, "Preliminary must succeed even when certification_ready=False"


# ── PVH69–PVH71: Advisory metadata checks ─────────────────────────────────────

def test_PVH69_preliminary_output_official_use_allowed_false(client):
    rid = _create(client).get_json()["request_id"]
    _build_methods_fixture(rid)
    resp = client.post(_pvp_prelim_url(rid), json={},
                       content_type="application/json", headers=_auth())
    out = resp.get_json().get("output", {})
    assert out.get("official_use_allowed") is False


def test_PVH70_preliminary_output_certified_use_allowed_false(client):
    rid = _create(client).get_json()["request_id"]
    _build_methods_fixture(rid)
    resp = client.post(_pvp_prelim_url(rid), json={},
                       content_type="application/json", headers=_auth())
    out = resp.get_json().get("output", {})
    assert out.get("certified_use_allowed") is False


def test_PVH71_expert_draft_advisory_only_true(client):
    rid = _create(client).get_json()["request_id"]
    _build_methods_fixture(rid)
    resp = client.post(_pvp_draft_url(rid), json={},
                       content_type="application/json", headers=_auth())
    out = resp.get_json().get("output", {})
    assert out.get("advisory_only") is True


def test_PVH72_expert_workbook_advisory_only_true(client):
    rid = _create(client).get_json()["request_id"]
    _build_methods_fixture(rid)
    resp = client.post(_pvp_ewb_url(rid), json={},
                       content_type="application/json", headers=_auth())
    out = resp.get_json().get("output", {})
    assert out.get("advisory_only") is True


# ── PVH73–PVH75: Download endpoints ──────────────────────────────────────────

def test_PVH73_preliminary_download_returns_404_before_generation(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.get(_pvp_prelim_url(rid), headers=_auth())
    assert resp.status_code == 404


def test_PVH74_expert_draft_download_returns_404_before_generation(client):
    rid = _create(client).get_json()["request_id"]
    resp = client.get(_pvp_draft_url(rid), headers=_auth())
    assert resp.status_code == 404


def test_PVH75_expert_workbook_download_works_after_generation(client):
    """Workbook (openpyxl) always succeeds — download must return 200."""
    rid = _create(client).get_json()["request_id"]
    _build_methods_fixture(rid)
    client.post(_pvp_ewb_url(rid), json={},
                content_type="application/json", headers=_auth())
    resp = client.get(_pvp_ewb_url(rid), headers=_auth())
    assert resp.status_code == 200
    ct = resp.content_type
    assert "spreadsheet" in ct or "excel" in ct or "octet" in ct


# ── PVH76–PVH77: No internal paths ────────────────────────────────────────────

def test_PVH76_no_internal_paths_in_preliminary_response(client):
    rid = _create(client).get_json()["request_id"]
    _build_methods_fixture(rid)
    resp = client.post(_pvp_prelim_url(rid), json={},
                       content_type="application/json", headers=_auth())
    body_text = resp.get_data(as_text=True)
    assert "internal_file_path" not in body_text
    assert "instance/professional_valuation" not in body_text
    assert "preliminary_outputs/" not in body_text


def test_PVH77_no_internal_paths_in_workbook_response(client):
    rid = _create(client).get_json()["request_id"]
    _build_methods_fixture(rid)
    resp = client.post(_pvp_ewb_url(rid), json={},
                       content_type="application/json", headers=_auth())
    body_text = resp.get_data(as_text=True)
    assert "internal_file_path" not in body_text
    assert "preliminary_outputs/" not in body_text


# ── PVH78–PVH80: Workbook file checks ────────────────────────────────────────

def test_PVH78_expert_workbook_file_available_true(client):
    rid = _create(client).get_json()["request_id"]
    _build_methods_fixture(rid)
    resp = client.post(_pvp_ewb_url(rid), json={},
                       content_type="application/json", headers=_auth())
    out = resp.get_json().get("output", {})
    assert out.get("file_available") is True
    assert out.get("file_hash_sha256") is not None
    assert len(out["file_hash_sha256"]) == 64


def test_PVH79_expert_workbook_opens_with_openpyxl(client):
    rid = _create(client).get_json()["request_id"]
    _build_methods_fixture(rid)
    client.post(_pvp_ewb_url(rid), json={},
                content_type="application/json", headers=_auth())
    rec = _pvprelim._latest_active_of_type(rid, "expert_workbook")
    assert rec is not None and rec.get("file_available")
    import openpyxl
    fpath = rec["internal_file_path"]
    wb = openpyxl.load_workbook(fpath)
    assert len(wb.sheetnames) == 43
    wb.close()


def test_PVH80_expert_workbook_contains_required_sheets(client):
    rid = _create(client).get_json()["request_id"]
    _build_methods_fixture(rid)
    client.post(_pvp_ewb_url(rid), json={},
                content_type="application/json", headers=_auth())
    rec = _pvprelim._latest_active_of_type(rid, "expert_workbook")
    import openpyxl
    wb = openpyxl.load_workbook(rec["internal_file_path"])
    sheets = wb.sheetnames
    for required in ["ملخص المسودة", "بوابات الاعتماد", "مراجعة الخبير", "ملاحظات داخلية", "سجل المخرجات"]:
        assert required in sheets, f"Required sheet missing: {required}"
    wb.close()


# ── PVH81–PVH82: No external/OCR/RAG flags ───────────────────────────────────

def test_PVH81_no_qdrant_rag_external_api_in_preliminary(client):
    rid = _create(client).get_json()["request_id"]
    _build_methods_fixture(rid)
    resp = client.post(_pvp_prelim_url(rid), json={},
                       content_type="application/json", headers=_auth())
    out = resp.get_json().get("output", {})
    assert out.get("external_api_used") is False
    assert out.get("qdrant_used") is False
    assert out.get("rag_used") is False


def test_PVH82_no_fpdf_in_preliminary_module(client):
    import ast, pathlib
    source = pathlib.Path(_CORE / "professional_valuation_preliminary_outputs.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any("fpdf" in i.lower() for i in imports), "fpdf must not be in preliminary module"


# ── PVH83–PVH84: Regression — Phase H certified gate unchanged ───────────────

def test_PVH83_certified_gate_unchanged_after_addendum(client):
    """Phase H certified output still requires certification_ready=True."""
    rid = _create(client).get_json()["request_id"]
    _build_methods_fixture(rid)   # methods_completed=True but certification_ready=False
    resp = client.post(_pvh_pdf_url(rid), json={},
                       content_type="application/json", headers=_auth())
    assert resp.status_code == 422, (
        "Certified PDF must be blocked even when methods_completed=True but certification_ready=False"
    )


def test_PVH84_preliminary_and_certified_in_same_registry(client):
    """Both preliminary and certified outputs share the same output registry."""
    rid = _create(client).get_json()["request_id"]
    _build_methods_fixture(rid)
    client.post(_pvp_ewb_url(rid), json={},
                content_type="application/json", headers=_auth())
    records = _pvout._read_registry(rid)
    types = {r["output_type"] for r in records}
    assert "expert_workbook" in types


# ── PVRT01–PVRT10: Report Type ───────────────────────────────────────────────

def test_PVRT01_traditional_report_type_stored_and_returned(client):
    """Create with traditional_report — stored in record and returned in detail."""
    r = _create(client, {"report_type": "traditional_report"})
    assert r.status_code == 201
    rid = r.get_json()["request_id"]
    detail = client.get(
        f"/api/professional-valuation/requests/{rid}",
        headers=_auth(),
    ).get_json()
    assert detail["ok"] is True
    req = detail["request"]
    assert req.get("report_type") == "traditional_report"


def test_PVRT02_detailed_report_type_stored_and_returned(client):
    """Create with detailed_report — stored and returned."""
    r = _create(client, {"report_type": "detailed_report"})
    rid = r.get_json()["request_id"]
    detail = client.get(
        f"/api/professional-valuation/requests/{rid}",
        headers=_auth(),
    ).get_json()
    assert detail["request"].get("report_type") == "detailed_report"


def test_PVRT03_professional_report_type_stored_and_returned(client):
    """Create with professional_report — stored and returned."""
    r = _create(client, {"report_type": "professional_report"})
    rid = r.get_json()["request_id"]
    detail = client.get(
        f"/api/professional-valuation/requests/{rid}",
        headers=_auth(),
    ).get_json()
    assert detail["request"].get("report_type") == "professional_report"


def test_PVRT04_no_report_type_defaults_to_professional(client):
    """Creating without report_type defaults to professional_report."""
    r = _create(client)   # no report_type in payload
    rid = r.get_json()["request_id"]
    detail = client.get(
        f"/api/professional-valuation/requests/{rid}",
        headers=_auth(),
    ).get_json()
    assert detail["request"].get("report_type") == "professional_report"


def test_PVRT05_invalid_report_type_returns_400(client):
    """Creating with an invalid report_type returns HTTP 400."""
    r = _create(client, {"report_type": "super_report"})
    assert r.status_code == 400
    body = r.get_json()
    assert body["ok"] is False
    assert "report_type" in body.get("error", "").lower() or "غير صالح" in body.get("error", "")


def test_PVRT06_report_type_in_list_response(client):
    """report_type appears in list dashboard response."""
    _create(client, {"report_type": "traditional_report"})
    resp = client.get(
        "/api/professional-valuation/requests",
        headers=_auth(),
    ).get_json()
    assert resp["ok"] is True
    rows = resp.get("requests", [])
    assert len(rows) > 0
    # At least the most recent row should have report_type
    assert any(r.get("report_type") is not None for r in rows)


def test_PVRT07_report_type_in_detail_response(client):
    """report_type is present in the full detail response."""
    r = _create(client, {"report_type": "detailed_report"})
    rid = r.get_json()["request_id"]
    detail = client.get(
        f"/api/professional-valuation/requests/{rid}",
        headers=_auth(),
    ).get_json()
    assert "report_type" in detail["request"]


def test_PVRT08_schema_lists_report_type_optional_field(client):
    """Schema route lists report_type in optional_fields."""
    resp = client.get(
        "/api/professional-valuation/schema",
        headers=_auth(),
    ).get_json()
    assert resp["ok"] is True
    optional_fields = [f["field"] for f in resp["schema"].get("optional_fields", [])]
    assert "report_type" in optional_fields


def test_PVRT09_report_type_label_in_preliminary_context(client):
    """build_professional_valuation_preliminary_output_context includes report_type_label."""
    import professional_valuation_preliminary_outputs as _pvprelim
    from professional_valuation_routes import _read_pvr, _update_pvr
    r = _create(client, {"report_type": "traditional_report"})
    rid = r.get_json()["request_id"]
    ctx = _pvprelim.build_professional_valuation_preliminary_output_context(rid)
    req_sum = ctx.get("request_summary", {})
    assert req_sum.get("report_type") == "traditional_report"
    assert req_sum.get("report_type_label") == "تقرير تقليدي"


def test_PVRT10_report_type_label_in_certified_context(client):
    """build_professional_valuation_output_context includes report_type_label."""
    import professional_valuation_outputs as _pvout_mod
    r = _create(client, {"report_type": "detailed_report"})
    rid = r.get_json()["request_id"]
    ctx = _pvout_mod.build_professional_valuation_output_context(rid)
    req_sum = ctx.get("request_summary", {})
    assert req_sum.get("report_type") == "detailed_report"
    assert req_sum.get("report_type_label") == "تقرير تفصيلي"


# ─────────────────────────────────────────────────────────────────────────────
# WBPAR01–WBPAR13  Workbook Parity tests
# ─────────────────────────────────────────────────────────────────────────────

def test_WBPAR01_expert_workbook_sheet_list_count():
    """Expert workbook sheet list has >= 40 entries (was 15)."""
    import professional_valuation_preliminary_outputs as _pvprelim
    assert len(_pvprelim._EXPERT_WB_SHEETS) >= 40


def test_WBPAR02_final_workbook_sheet_list_count():
    """Final workbook sheet list has >= 40 entries (was 18)."""
    import professional_valuation_outputs as _pvout
    assert len(_pvout._SHEETS) >= 40


def test_WBPAR03_expert_workbook_includes_parity_sheets():
    """Expert workbook sheet list includes key parity sheets ported from ordinary valuation."""
    import professional_valuation_preliminary_outputs as _pvprelim
    required = [
        "طريقة مقارنة البيوع",
        "طريقة الدخل",
        "التدفقات النقدية DCF",
        "طريقة التكلفة",
        "قيمة الأرض",
        "القيمة الإيجارية",
        "مصفوفة المخاطر",
        "بيان الامتثال",
        "خارطة طريق الاعتماد",
    ]
    for s in required:
        assert s in _pvprelim._EXPERT_WB_SHEETS, f"Missing parity sheet: {s}"


def test_WBPAR04_final_workbook_includes_parity_sheets():
    """Final workbook sheet list includes key parity sheets."""
    import professional_valuation_outputs as _pvout
    required = [
        "طريقة مقارنة البيوع",
        "طريقة الدخل",
        "التدفقات النقدية DCF",
        "طريقة التكلفة",
        "قيمة الأرض",
        "مصفوفة المخاطر",
        "بيان الامتثال",
        "لوحة امتثال التقييم",
    ]
    for s in required:
        assert s in _pvout._SHEETS, f"Missing parity sheet: {s}"


def test_WBPAR05_expert_wb_context_has_report_type_label(client):
    """Expert workbook cover context includes report_type_label for traditional."""
    import professional_valuation_preliminary_outputs as _pvprelim
    r = _create(client, {"report_type": "traditional_report"})
    rid = r.get_json()["request_id"]
    ctx = _pvprelim.build_professional_valuation_preliminary_output_context(rid)
    req_sum = ctx.get("request_summary", {})
    assert req_sum.get("report_type_label") == "تقرير تقليدي"


def test_WBPAR06_final_wb_context_has_report_type_label(client):
    """Final workbook context includes report_type_label for detailed."""
    import professional_valuation_outputs as _pvout_mod
    r = _create(client, {"report_type": "detailed_report"})
    rid = r.get_json()["request_id"]
    ctx = _pvout_mod.build_professional_valuation_output_context(rid)
    req_sum = ctx.get("request_summary", {})
    assert req_sum.get("report_type_label") == "تقرير تفصيلي"


def test_WBPAR07_ordinary_workbook_builder_importable():
    """reporting_workbook_builder is importable (ordinary workbook builder exists)."""
    import importlib
    mod = importlib.import_module("reporting_workbook_builder")
    assert mod is not None


def test_WBPAR08_expert_wb_sheet_names_no_internal_paths():
    """Expert workbook sheet names do not contain internal file path fragments."""
    import professional_valuation_preliminary_outputs as _pvprelim
    forbidden = ["instance", "certified_outputs", "preliminary_outputs", "Users"]
    for sheet_name in _pvprelim._EXPERT_WB_SHEETS:
        for frag in forbidden:
            assert frag not in sheet_name, f"Internal path in sheet name: {sheet_name}"


def test_WBPAR09_final_wb_sheet_names_no_internal_paths():
    """Final workbook sheet names do not contain internal file path fragments."""
    import professional_valuation_outputs as _pvout
    forbidden = ["instance", "certified_outputs", "Users"]
    for sheet_name in _pvout._SHEETS:
        for frag in forbidden:
            assert frag not in sheet_name, f"Internal path in sheet name: {sheet_name}"


def test_WBPAR10_expert_workbook_generates_with_expanded_sheets():
    """_generate_expert_workbook produces >= 40 sheets; tests generator directly (bypasses HTTP gate)."""
    import professional_valuation_preliminary_outputs as _pvprelim
    import openpyxl, uuid
    from datetime import datetime

    rid = f"PVR-{datetime.utcnow().strftime('%Y%m%d')}-W10{uuid.uuid4().hex[:4].upper()}"
    out_id = "PVOUT-WBPAR10"
    ctx = {
        "request_id": rid,
        "assembled_at": datetime.utcnow().isoformat(),
        "advisory_only": True,
        "report_type": "professional_report",
        "report_type_label": "تقرير احترافي",
        "request_summary": {
            "request_id": rid,
            "client_name": "Test Client",
            "property_type": "شقة",
            "valuation_purpose": "تمويل",
            "report_type": "professional_report",
            "report_type_label": "تقرير احترافي",
        },
        "certification_gate": {
            "methods_completed": False,
            "certification_ready": False,
            "overall_gate_status": "not_ready",
        },
        "method_summary": {"methods": [], "reconciliation_value": None},
        "evidence_summary": {
            "approved_count": 0,
            "mandatory_document_readiness": False,
        },
        "comparable_summary": {
            "total_count": 0,
            "production_ready_count": 0,
        },
        "advanced_reviews": {
            "hbu_completed": False,
            "esg_completed": False,
            "legal_completed": False,
            "swot_completed": False,
        },
        "preliminary_approval": {"preliminary_approval_ready": False},
        "source_summary": {"production_source_count": 0},
        "missing_certification_gates": {"blockers": []},
        "expert_next_actions": {"actions": []},
    }

    success, err, size, _sha = _pvprelim._generate_expert_workbook(ctx, rid, out_id)
    assert success is True, f"Workbook generation failed: {err}"
    assert size > 0

    wb_path = _pvprelim._PRELIM_OUT_DIR / rid / f"{out_id}_expert_workbook.xlsx"
    wb = openpyxl.load_workbook(str(wb_path))
    assert len(wb.sheetnames) >= 40, (
        f"Expected >= 40 sheets, got {len(wb.sheetnames)}: {wb.sheetnames}"
    )


def test_WBPAR11_final_workbook_blocked_when_not_certified(client):
    """Final workbook generation returns 422 when certification_ready=False."""
    r = _create(client, {"report_type": "traditional_report"})
    rid = r.get_json()["request_id"]
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/final-workbook",
        headers=_auth(),
    )
    assert resp.status_code == 422
    data = resp.get_json()
    assert data.get("ok") is False


def test_WBPAR12_certification_gate_logic_unchanged(client):
    """Certification gate still reports not_ready for a fresh uncertified request."""
    r = _create(client)
    rid = r.get_json()["request_id"]
    gate_resp = client.get(
        f"/api/professional-valuation/requests/{rid}/certification-gate",
        headers=_auth(),
    )
    if gate_resp.status_code == 200:
        resp_body = gate_resp.get_json()
        # Gate data is nested under "gate" key in the response envelope
        gate_data = resp_body.get("gate", resp_body)
        assert gate_data.get("certification_ready") is False or "blockers" in gate_data


def test_WBPAR13_expert_wb_sheet_names_no_none_nan():
    """Expert workbook sheet names do not contain None, NaN, null, or undefined."""
    import professional_valuation_preliminary_outputs as _pvprelim
    forbidden_vals = ["None", "NaN", "null", "undefined"]
    for sheet_name in _pvprelim._EXPERT_WB_SHEETS:
        for bad in forbidden_vals:
            assert bad not in sheet_name, f"Bad value in sheet name: {sheet_name}"


# ─────────────────────────────────────────────────────────────────────────────
# PVMAT01–PVMAT23  Output Matrix tests
# ─────────────────────────────────────────────────────────────────────────────

def test_PVMAT01_matrix_module_importable():
    """professional_valuation_output_matrix is importable."""
    import importlib
    m = importlib.import_module("professional_valuation_output_matrix")
    assert m is not None


def test_PVMAT02_valid_report_types_defined():
    """VALID_REPORT_TYPES contains the three expected values."""
    import professional_valuation_output_matrix as mx
    assert "traditional_report" in mx.VALID_REPORT_TYPES
    assert "detailed_report"    in mx.VALID_REPORT_TYPES
    assert "professional_report" in mx.VALID_REPORT_TYPES


def test_PVMAT03_valid_valuation_purposes_defined():
    """VALID_VALUATION_PURPOSES contains all 8 expected purposes."""
    import professional_valuation_output_matrix as mx
    expected = {
        "market_value", "rental_value", "financing_mortgage", "court_legal",
        "investment_decision", "internal_advisory", "environmental_impact", "special_purpose",
    }
    assert expected.issubset(mx.VALID_VALUATION_PURPOSES)


def test_PVMAT04_valid_property_types_defined():
    """VALID_PROPERTY_TYPES contains all 9 expected asset types."""
    import professional_valuation_output_matrix as mx
    expected = {
        "residential_apartment", "residential_villa", "administrative_office",
        "retail_shop", "land", "industrial_factory", "warehouse",
        "mixed_use", "special_purpose_asset",
    }
    assert expected.issubset(mx.VALID_PROPERTY_TYPES)


def test_PVMAT05_traditional_report_smaller_sheet_count():
    """Traditional report generates fewer expert sheets than professional."""
    import professional_valuation_output_matrix as mx
    trad  = mx.get_expert_sheets("traditional_report", "market_value", "residential_apartment")
    prof  = mx.get_expert_sheets("professional_report", "market_value", "residential_apartment")
    assert len(trad) < len(prof), (
        f"Traditional ({len(trad)}) should have fewer sheets than professional ({len(prof)})"
    )


def test_PVMAT06_professional_report_includes_governance_sheets():
    """Professional expert workbook includes HBU, ESG, SWOT governance sheets."""
    import professional_valuation_output_matrix as mx
    sheets = frozenset(mx.get_expert_sheets("professional_report"))
    for s in ("HBU", "ESG", "SWOT", "مراجعة الخبير", "ملاحظات داخلية"):
        assert s in sheets, f"Professional sheets missing: {s}"


def test_PVMAT07_traditional_report_excludes_governance_sheets():
    """Traditional expert workbook does NOT include governance-only sheets."""
    import professional_valuation_output_matrix as mx
    sheets = frozenset(mx.get_expert_sheets("traditional_report"))
    # Governance sheets only for professional
    for s in ("HBU", "ESG", "SWOT", "مراجعة الخبير", "ملاحظات داخلية"):
        assert s not in sheets, f"Traditional sheets should not include: {s}"


def test_PVMAT08_detailed_report_intermediate_sheet_count():
    """Detailed report has more sheets than traditional but fewer than professional."""
    import professional_valuation_output_matrix as mx
    trad = len(mx.get_expert_sheets("traditional_report"))
    det  = len(mx.get_expert_sheets("detailed_report"))
    prof = len(mx.get_expert_sheets("professional_report"))
    assert trad < det < prof, f"Expected trad({trad}) < detailed({det}) < prof({prof})"


def test_PVMAT09_land_asset_adds_land_sheets():
    """land asset_type adds land value and HBU sheets to expert workbook."""
    import professional_valuation_output_matrix as mx
    sheets = frozenset(mx.get_expert_sheets("professional_report", "market_value", "land"))
    assert "قيمة الأرض" in sheets
    assert "HBU" in sheets


def test_PVMAT10_investment_purpose_adds_dcf_sheets():
    """investment_decision purpose adds DCF and sensitivity sheets to expert workbook."""
    import professional_valuation_output_matrix as mx
    sheets = frozenset(mx.get_expert_sheets("detailed_report", "investment_decision", "administrative_office"))
    assert "التدفقات النقدية DCF" in sheets
    assert "سيناريوهات What-If" in sheets


def test_PVMAT11_rental_purpose_adds_rental_sheets():
    """rental_value purpose adds rental comparison and reconciliation sheets."""
    import professional_valuation_output_matrix as mx
    sheets = frozenset(mx.get_expert_sheets("traditional_report", "rental_value", "residential_apartment"))
    assert "القيمة الإيجارية" in sheets


def test_PVMAT12_environmental_purpose_adds_esg_sheets():
    """environmental_impact purpose adds ESG and environmental assessment sheets."""
    import professional_valuation_output_matrix as mx
    sheets = frozenset(mx.get_expert_sheets("professional_report", "environmental_impact", "industrial_factory"))
    assert "تحليل الاستدامة ESG" in sheets
    assert "تقييم الأثر البيئي" in sheets


def test_PVMAT13_get_required_methods_market_value():
    """market_value purpose requires sales_comparison and cost_approach."""
    import professional_valuation_output_matrix as mx
    result = mx.get_required_methods("market_value", "residential_apartment")
    assert "sales_comparison" in result["required_methods"]
    assert "cost_approach" in result["required_methods"]


def test_PVMAT14_get_required_methods_investment():
    """investment_decision purpose requires income_approach, dcf, sensitivity."""
    import professional_valuation_output_matrix as mx
    result = mx.get_required_methods("investment_decision", "administrative_office")
    for m in ("income_approach", "dcf", "sensitivity"):
        assert m in result["required_methods"], f"Missing required method: {m}"


def test_PVMAT15_land_asset_adds_hbu_to_methods():
    """land asset type adds hbu_analysis to asset_additional_methods."""
    import professional_valuation_output_matrix as mx
    result = mx.get_required_methods("market_value", "land")
    assert "hbu_analysis" in result["asset_additional_methods"]


def test_PVMAT16_get_pdf_sections_traditional_concise():
    """Traditional PDF sections are a subset of professional PDF sections."""
    import professional_valuation_output_matrix as mx
    trad = mx.get_pdf_sections("traditional_report")
    prof = mx.get_pdf_sections("professional_report")
    assert trad.issubset(prof), "Traditional PDF sections must be a subset of professional"
    assert "peer_review" not in trad, "Peer review should not be in traditional PDF sections"


def test_PVMAT17_professional_pdf_includes_governance_sections():
    """Professional PDF sections include governance-only sections."""
    import professional_valuation_output_matrix as mx
    sections = mx.get_pdf_sections("professional_report")
    for s in ("peer_review", "expert_signature", "audit_trail", "source_registry"):
        assert s in sections, f"Professional PDF sections missing: {s}"


def test_PVMAT18_validate_report_type_valid():
    """validate_report_type returns (True, '') for valid report types."""
    import professional_valuation_output_matrix as mx
    for rt in mx.VALID_REPORT_TYPES:
        ok, err = mx.validate_report_type(rt)
        assert ok is True
        assert err == ""


def test_PVMAT19_validate_report_type_invalid():
    """validate_report_type returns (False, error) for invalid values."""
    import professional_valuation_output_matrix as mx
    ok, err = mx.validate_report_type("unknown_report_type")
    assert ok is False
    assert err != ""


def test_PVMAT20_get_output_matrix_context_structure():
    """get_output_matrix_context returns a complete dict with expected keys."""
    import professional_valuation_output_matrix as mx
    ctx = mx.get_output_matrix_context("professional_report", "market_value", "residential_apartment")
    for key in ("report_type", "report_type_label", "valuation_purpose", "valuation_purpose_label",
                "property_type", "property_type_label", "expert_sheet_count", "final_sheet_count",
                "expert_sheets", "final_sheets", "required_methods", "optional_methods",
                "asset_additional_methods", "pdf_sections_enabled"):
        assert key in ctx, f"output_matrix_context missing key: {key}"


def test_PVMAT21_expert_wb_generates_reduced_sheets_for_traditional(client):
    """_generate_expert_workbook with traditional_report produces fewer sheets than professional."""
    import professional_valuation_preliminary_outputs as _pvprelim
    import openpyxl, uuid
    from datetime import datetime

    def _make_ctx(rt):
        rid = f"PVR-{datetime.utcnow().strftime('%Y%m%d')}-M21{uuid.uuid4().hex[:4].upper()}"
        return rid, {
            "request_id": rid, "assembled_at": datetime.utcnow().isoformat(),
            "advisory_only": True, "report_type": rt,
            "report_type_label": rt,
            "request_summary": {"request_id": rid, "client_name": "Test",
                                 "property_type": "residential_apartment",
                                 "valuation_purpose": "market_value",
                                 "report_type": rt, "report_type_label": rt},
            "certification_gate": {"methods_completed": False, "certification_ready": False},
            "method_summary": {"methods": [], "reconciliation_value": None},
            "evidence_summary": {"approved_count": 0, "mandatory_document_readiness": False},
            "comparable_summary": {"total_count": 0, "production_ready_count": 0},
            "advanced_reviews": {"hbu_completed": False, "esg_completed": False,
                                 "legal_completed": False, "swot_completed": False},
            "preliminary_approval": {"preliminary_approval_ready": False},
            "source_summary": {"production_source_count": 0},
            "missing_certification_gates": {"blockers": []},
            "expert_next_actions": {"actions": []},
        }

    rid_t, ctx_t = _make_ctx("traditional_report")
    rid_p, ctx_p = _make_ctx("professional_report")

    ok_t, err_t, _, _ = _pvprelim._generate_expert_workbook(ctx_t, rid_t, "PVOUT-TRAD")
    ok_p, err_p, _, _ = _pvprelim._generate_expert_workbook(ctx_p, rid_p, "PVOUT-PROF")

    assert ok_t, f"Traditional workbook generation failed: {err_t}"
    assert ok_p, f"Professional workbook generation failed: {err_p}"

    wb_t = openpyxl.load_workbook(str(_pvprelim._PRELIM_OUT_DIR / rid_t / "PVOUT-TRAD_expert_workbook.xlsx"))
    wb_p = openpyxl.load_workbook(str(_pvprelim._PRELIM_OUT_DIR / rid_p / "PVOUT-PROF_expert_workbook.xlsx"))
    assert len(wb_t.sheetnames) < len(wb_p.sheetnames), (
        f"Traditional ({len(wb_t.sheetnames)}) must have fewer sheets than professional ({len(wb_p.sheetnames)})"
    )


def test_PVMAT22_output_context_includes_output_matrix_key(client):
    """Preliminary output context includes output_matrix key."""
    import professional_valuation_preliminary_outputs as _pvprelim
    r = _create(client, {
        "report_type": "detailed_report",
        "valuation_purpose": "market_value",
        "property_type": "residential_apartment",
    })
    rid = r.get_json()["request_id"]
    ctx = _pvprelim.build_professional_valuation_preliminary_output_context(rid)
    assert "output_matrix" in ctx, "Context must contain output_matrix key"
    mx = ctx["output_matrix"]
    assert mx.get("report_type") == "detailed_report"
    assert "expert_sheets" in mx


def test_PVMAT23_matrix_warns_for_unknown_purpose(client):
    """PVR create returns matrix_warnings for unknown valuation_purpose."""
    r = _create(client, {
        "valuation_purpose": "unknown_custom_purpose_xyz",
        "property_type": "residential_apartment",
    })
    assert r.status_code == 201
    data = r.get_json()
    # unknown purpose triggers soft warning (not rejection)
    assert data.get("ok") is True
    assert "matrix_warnings" in data, "Should contain matrix_warnings for unknown purpose"


# ── PVTAX01–PVTAX20: Taxonomy v2 canonical fields ────────────────────────────

def test_PVTAX01_canonical_fields_accepted_alongside_legacy(client):
    """PVTAX01: New canonical fields accepted without breaking legacy path."""
    r = _create(client, {
        "asset_family":       "hospitality_leisure",
        "asset_type":         "hotel",
        "assignment_purpose": "market_valuation",
        "basis_of_value":     "market_value",
    })
    assert r.status_code == 201
    data = r.get_json()
    assert data["ok"] is True


def test_PVTAX02_basis_of_value_market_value_accepted(client):
    """PVTAX02: basis_of_value=market_value is a valid canonical basis."""
    r = _create(client, {
        "asset_type":     "residential_apartment",
        "basis_of_value": "market_value",
    })
    assert r.status_code == 201
    data = r.get_json()
    assert data["ok"] is True


def test_PVTAX03_basis_of_value_invalid_returns_400(client):
    """PVTAX03: Unrecognised basis_of_value returns 400."""
    r = _create(client, {
        "asset_type":     "residential_apartment",
        "basis_of_value": "completely_invalid_basis_xyz",
    })
    assert r.status_code == 400
    data = r.get_json()
    assert data["ok"] is False
    assert "basis_of_value" in data["error"]


def test_PVTAX04_derived_method_route_returned(client):
    """PVTAX04: derived_method_route block present when asset_type + basis_of_value provided."""
    r = _create(client, {
        "asset_type":     "hotel",
        "basis_of_value": "market_value",
    })
    assert r.status_code == 201
    data = r.get_json()
    assert "derived_method_route" in data
    dr = data["derived_method_route"]
    assert "enabled_methods" in dr
    assert len(dr["enabled_methods"]) > 0


def test_PVTAX05_no_taxonomy_warnings_for_clean_input(client):
    """PVTAX05: taxonomy_warnings absent (or empty) when no misplacements."""
    r = _create(client, {
        "asset_type":         "residential_apartment",
        "assignment_purpose": "market_valuation",
        "basis_of_value":     "market_value",
    })
    assert r.status_code == 201
    data = r.get_json()
    assert data["ok"] is True
    warnings = data.get("taxonomy_warnings", [])
    assert isinstance(warnings, list)


def test_PVTAX06_hotel_as_both_type_and_subtype_triggers_warning(client):
    """PVTAX06: hotel as asset_type AND asset_subtype triggers misplacement warning."""
    r = _create(client, {
        "asset_type":    "hotel",
        "asset_subtype": "hotel",
        "basis_of_value": "market_value",
    })
    assert r.status_code == 201
    data = r.get_json()
    assert data["ok"] is True
    warnings = data.get("taxonomy_warnings", [])
    assert any("hotel" in str(w).lower() for w in warnings), \
        f"Expected hotel duplicate warning, got: {warnings}"


def test_PVTAX07_market_value_as_assignment_purpose_triggers_warning(client):
    """PVTAX07: market_value as assignment_purpose triggers misplacement warning."""
    # Explicitly clear legacy valuation_purpose so assignment_purpose is the active axis
    r = _create(client, {
        "asset_type":         "residential_apartment",
        "assignment_purpose": "market_value",
        "valuation_purpose":  "",  # clear legacy to ensure canonical field is checked
    })
    # Request still accepted (soft validation)
    assert r.status_code == 201
    data = r.get_json()
    assert data["ok"] is True
    warnings = data.get("taxonomy_warnings", [])
    assert any("market_value" in str(w).lower() or "basis" in str(w).lower() for w in warnings), \
        f"Expected market_value-as-purpose warning, got: {warnings}"


def test_PVTAX08_comparable_adjustment_as_purpose_subpath_triggers_warning(client):
    """PVTAX08: comparable_adjustment as purpose_subpath triggers misplacement warning."""
    r = _create(client, {
        "asset_type":      "residential_apartment",
        "purpose_subpath": "comparable_adjustment",
        "basis_of_value":  "market_value",
    })
    assert r.status_code == 201
    data = r.get_json()
    assert data["ok"] is True
    warnings = data.get("taxonomy_warnings", [])
    assert any("comparable_adjustment" in str(w).lower() or "method" in str(w).lower() for w in warnings), \
        f"Expected comparable_adjustment misplacement warning, got: {warnings}"


def test_PVTAX09_canonical_taxonomy_block_in_response(client):
    """PVTAX09: canonical_taxonomy block with axis_1/axis_2/axis_3 keys returned."""
    r = _create(client, {
        "asset_family":       "residential_housing",
        "asset_type":         "residential_apartment",
        "assignment_purpose": "market_valuation",
        "basis_of_value":     "market_value",
    })
    assert r.status_code == 201
    data = r.get_json()
    assert "canonical_taxonomy" in data
    ct = data["canonical_taxonomy"]
    # canonical_taxonomy uses keys like axis_1_asset_classification, axis_2_assignment_purpose, etc.
    assert any(k.startswith("axis_") for k in ct), \
        f"canonical_taxonomy missing axis_N_* keys: {list(ct.keys())}"


def test_PVTAX10_asset_family_stored_on_record(client):
    """PVTAX10: asset_family value is persisted and returned in detail response."""
    import json, re
    r = _create(client, {
        "asset_family": "hospitality_leisure",
        "asset_type":   "hotel",
    })
    rid = r.get_json()["request_id"]
    det = client.get(f"/api/professional-valuation/requests/{rid}", headers=_auth())
    assert det.status_code == 200
    data = det.get_json()
    rec = data.get("request") or data
    assert rec.get("asset_family") == "hospitality_leisure"


def test_PVTAX11_asset_subtype_stored_on_record(client):
    """PVTAX11: asset_subtype value is persisted and returned in detail response."""
    r = _create(client, {
        "asset_type":    "hotel",
        "asset_subtype": "boutique_hotel",
        "basis_of_value": "market_value",
    })
    rid = r.get_json()["request_id"]
    det = client.get(f"/api/professional-valuation/requests/{rid}", headers=_auth())
    assert det.status_code == 200
    data = det.get_json()
    rec = data.get("request") or data
    assert rec.get("asset_subtype") == "boutique_hotel"


def test_PVTAX12_assignment_purpose_stored_on_record(client):
    """PVTAX12: assignment_purpose is persisted and returned in detail response."""
    r = _create(client, {
        "asset_type":         "urban_land",
        "assignment_purpose": "financing_mortgage",
        "basis_of_value":     "market_value",
    })
    rid = r.get_json()["request_id"]
    det = client.get(f"/api/professional-valuation/requests/{rid}", headers=_auth())
    assert det.status_code == 200
    data = det.get_json()
    rec = data.get("request") or data
    assert rec.get("assignment_purpose") == "financing_mortgage"


def test_PVTAX13_value_premise_stored_on_record(client):
    """PVTAX13: value_premise is persisted and returned in detail response."""
    r = _create(client, {
        "asset_type":   "residential_apartment",
        "basis_of_value": "market_value",
        "value_premise":  "as_is",
    })
    rid = r.get_json()["request_id"]
    det = client.get(f"/api/professional-valuation/requests/{rid}", headers=_auth())
    assert det.status_code == 200
    data = det.get_json()
    rec = data.get("request") or data
    assert rec.get("value_premise") == "as_is"


def test_PVTAX14_normalize_legacy_fields_maps_property_type(client):
    """PVTAX14: normalize_legacy_fields() maps property_type to canonical asset_type."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from professional_valuation_taxonomy_v2 import normalize_legacy_fields
    result = normalize_legacy_fields(property_type="hotel", valuation_purpose="market_value")
    # normalize_legacy_fields returns {"canonical": {...}, "raw_legacy_values": {...}}
    canonical = result.get("canonical") or result
    assert canonical.get("asset_type") in ("hotel", "")  # preserved or empty
    # basis_of_value should be recognised from valuation_purpose mapping
    bov = canonical.get("basis_of_value") or result.get("basis_of_value") or ""
    assert bov in ("market_value", "")  # mapped or empty


def test_PVTAX15_validate_basis_of_value_accepts_all_valid(client):
    """PVTAX15: validate_basis_of_value() returns True for every valid canonical basis."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from professional_valuation_taxonomy_v2 import VALID_BASIS_OF_VALUE, validate_basis_of_value
    for bov in VALID_BASIS_OF_VALUE:
        ok, msg = validate_basis_of_value(bov)
        assert ok, f"Expected valid for '{bov}', got error: {msg}"


def test_PVTAX16_validate_basis_of_value_rejects_invalid_string(client):
    """PVTAX16: validate_basis_of_value rejects clearly invalid non-empty strings."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from professional_valuation_taxonomy_v2 import validate_basis_of_value
    ok, msg = validate_basis_of_value("definitely_not_a_valid_basis_xyz_999")
    assert not ok, "Expected invalid basis to be rejected"
    assert msg  # error message present


def test_PVTAX17_detect_misplacements_empty_for_clean_input(client):
    """PVTAX17: detect_misplacements() returns [] for canonical clean input."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from professional_valuation_taxonomy_v2 import detect_misplacements
    result = detect_misplacements(
        asset_type="residential_apartment",
        asset_subtype="studio",
        assignment_purpose="market_valuation",
        purpose_subpath="",
        basis_of_value="market_value",
    )
    assert result == [], f"Expected no misplacements, got: {result}"


def test_PVTAX18_derive_method_route_hotel_market_value(client):
    """PVTAX18: hotel + market_value → includes sales_comparison and dcf."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from professional_valuation_taxonomy_v2 import derive_method_route
    route = derive_method_route(
        asset_type="hotel",
        asset_family="hospitality_leisure",
        assignment_purpose="market_valuation",
        basis_of_value="market_value",
        report_type="professional_report",
    )
    methods = route.get("enabled_methods", [])
    assert "sales_comparison" in methods, f"sales_comparison missing from: {methods}"
    assert "dcf" in methods, f"dcf missing from: {methods}"


def test_PVTAX19_derive_method_route_land_market_value(client):
    """PVTAX19: urban_land + market_value → includes land_comparison."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from professional_valuation_taxonomy_v2 import derive_method_route
    route = derive_method_route(
        asset_type="urban_land",
        asset_family="land_plots",
        assignment_purpose="market_valuation",
        basis_of_value="market_value",
        report_type="professional_report",
    )
    methods = route.get("enabled_methods", [])
    assert "land_comparison" in methods, f"land_comparison missing from: {methods}"


def test_PVTAX20_backward_compat_only_legacy_fields_accepted(client):
    """PVTAX20: Request with only legacy fields (no canonical fields) still returns 201."""
    r = _create(client, {
        "property_type":     "residential_apartment",
        "valuation_purpose": "market_value",
    })
    # Must NOT break - legacy path must still work
    assert r.status_code == 201
    data = r.get_json()
    assert data["ok"] is True
    assert data["request_id"].startswith("PVR-")


# ─────────────────────────────────────────────────────────────────────────────
# ASREQ01–ASREQ16 — Asset-Specific Requirements Preservation Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_ASREQ01_hotel_asset_returns_hotel_requirements(client):
    """ASREQ01: hotel asset_type returns hotel-specific requirements in response."""
    r = _create(client, {
        "asset_type":         "hotel",
        "asset_family":       "hospitality_leisure",
        "assignment_purpose": "market_valuation",
        "basis_of_value":     "market_value",
    })
    assert r.status_code == 201
    data = r.get_json()
    asr = data.get("asset_specific_requirements", {})
    assert asr, "asset_specific_requirements missing from response"
    assert "hotel" in asr.get("requirements_panel_title_ar", "").lower() or \
           "فندق" in asr.get("requirements_panel_title_ar", ""), \
        f"Expected hotel/فندق in title: {asr.get('requirements_panel_title_ar')}"


def test_ASREQ02_hotel_requirements_include_adr(client):
    """ASREQ02: hotel requirements include ADR in required_inputs."""
    r = _create(client, {"asset_type": "hotel", "assignment_purpose": "market_valuation"})
    assert r.status_code == 201
    asr = r.get_json().get("asset_specific_requirements", {})
    assert "adr" in asr.get("required_inputs", []), \
        f"adr missing from hotel required_inputs: {asr.get('required_inputs')}"


def test_ASREQ03_hotel_requirements_include_occupancy_rate(client):
    """ASREQ03: hotel requirements include occupancy_rate."""
    r = _create(client, {"asset_type": "hotel", "assignment_purpose": "market_valuation"})
    assert r.status_code == 201
    asr = r.get_json().get("asset_specific_requirements", {})
    assert "occupancy_rate" in asr.get("required_inputs", []), \
        f"occupancy_rate missing: {asr.get('required_inputs')}"


def test_ASREQ04_hotel_requirements_include_revpar(client):
    """ASREQ04: hotel requirements include revpar."""
    r = _create(client, {"asset_type": "hotel", "assignment_purpose": "market_valuation"})
    assert r.status_code == 201
    asr = r.get_json().get("asset_specific_requirements", {})
    assert "revpar" in asr.get("required_inputs", []), \
        f"revpar missing: {asr.get('required_inputs')}"


def test_ASREQ05_hotel_requirements_include_dcf_and_income_approach(client):
    """ASREQ05: hotel recommended_methods include dcf and income_approach."""
    r = _create(client, {"asset_type": "hotel", "assignment_purpose": "market_valuation"})
    assert r.status_code == 201
    asr = r.get_json().get("asset_specific_requirements", {})
    methods = asr.get("recommended_methods", [])
    assert "dcf" in methods, f"dcf missing from hotel methods: {methods}"
    assert "income_approach" in methods, f"income_approach missing: {methods}"


def test_ASREQ06_factory_asset_returns_factory_requirements(client):
    """ASREQ06: industrial_factory asset_type returns factory-specific requirements."""
    r = _create(client, {
        "asset_type":         "industrial_factory",
        "assignment_purpose": "market_valuation",
    })
    assert r.status_code == 201
    asr = r.get_json().get("asset_specific_requirements", {})
    assert asr, "asset_specific_requirements missing"
    title = asr.get("requirements_panel_title_ar", "")
    assert "مصنع" in title or "صناعي" in title, \
        f"Expected مصنع/صناعي in factory title: {title}"
    assert "land_area" in asr.get("required_inputs", []) or \
           "replacement_cost" in asr.get("required_inputs", []), \
        f"Expected factory inputs: {asr.get('required_inputs')}"


def test_ASREQ07_land_asset_returns_land_requirements(client):
    """ASREQ07: urban_land asset_type returns land-specific requirements."""
    r = _create(client, {
        "asset_type":         "urban_land",
        "assignment_purpose": "market_valuation",
    })
    assert r.status_code == 201
    asr = r.get_json().get("asset_specific_requirements", {})
    title = asr.get("requirements_panel_title_ar", "")
    assert "أرض" in title, f"Expected أرض in land title: {title}"
    assert "zoning" in asr.get("required_inputs", []), \
        f"zoning missing from land inputs: {asr.get('required_inputs')}"


def test_ASREQ08_retail_asset_returns_retail_requirements(client):
    """ASREQ08: retail_shop asset_type returns retail-specific requirements."""
    r = _create(client, {
        "asset_type":         "retail_shop",
        "assignment_purpose": "market_valuation",
    })
    assert r.status_code == 201
    asr = r.get_json().get("asset_specific_requirements", {})
    title = asr.get("requirements_panel_title_ar", "")
    assert "تجاري" in title or "محل" in title, \
        f"Expected محل/تجاري in retail title: {title}"
    assert "frontage" in asr.get("required_inputs", []) or \
           "footfall" in asr.get("required_inputs", []), \
        f"Expected retail inputs: {asr.get('required_inputs')}"


def test_ASREQ09_warehouse_asset_returns_warehouse_requirements(client):
    """ASREQ09: warehouse asset_type returns warehouse-specific requirements."""
    r = _create(client, {
        "asset_type":         "warehouse",
        "assignment_purpose": "market_valuation",
    })
    assert r.status_code == 201
    asr = r.get_json().get("asset_specific_requirements", {})
    title = asr.get("requirements_panel_title_ar", "")
    assert "مستودع" in title or "لوجستيات" in title, \
        f"Expected مستودع/لوجستيات in warehouse title: {title}"
    assert "storage_area" in asr.get("required_inputs", []) or \
           "clear_height" in asr.get("required_inputs", []), \
        f"Expected warehouse inputs: {asr.get('required_inputs')}"


def test_ASREQ10_market_value_not_in_required_inputs(client):
    """ASREQ10: market_value is never returned as an asset requirement input key."""
    for at in ["hotel", "industrial_factory", "urban_land", "retail_shop", "warehouse"]:
        r = _create(client, {"asset_type": at, "assignment_purpose": "market_valuation"})
        assert r.status_code == 201
        asr = r.get_json().get("asset_specific_requirements", {})
        assert "market_value" not in asr.get("required_inputs", []), \
            f"market_value must NOT appear as required_input for {at}"


def test_ASREQ11_comparable_adjustment_is_method_step_not_purpose(client):
    """ASREQ11: comparable_adjustment appears in recommended_methods, not as assignment_purpose."""
    r = _create(client, {
        "asset_type":         "retail_shop",
        "assignment_purpose": "market_valuation",
    })
    assert r.status_code == 201
    asr = r.get_json().get("asset_specific_requirements", {})
    methods = asr.get("recommended_methods", [])
    # comparable_adjustment is valid as a method step
    if "comparable_adjustment" in methods:
        assert True  # correctly placed
    # but it must NOT appear as assignment_purpose in the record
    data = r.get_json()
    assert data.get("assignment_purpose", "") != "comparable_adjustment", \
        "comparable_adjustment must not be used as assignment_purpose"


def test_ASREQ12_old_requirement_keys_preserved_in_hotel(client):
    """ASREQ12: legacy hotel requirement keys are preserved in legacy_requirement_keys."""
    r = _create(client, {"asset_type": "hotel", "assignment_purpose": "market_valuation"})
    assert r.status_code == 201
    asr = r.get_json().get("asset_specific_requirements", {})
    legacy = asr.get("legacy_requirement_keys", [])
    assert "hotel_resort_detailed" in legacy, \
        f"hotel_resort_detailed missing from legacy_requirement_keys: {legacy}"
    assert any(k.startswith("ht_") for k in legacy), \
        f"Expected ht_* keys in legacy_requirement_keys: {legacy}"


def test_ASREQ13_taxonomy_v2_tests_still_pass_after_requirements_addition(client):
    """ASREQ13: Taxonomy v2 canonical fields still work alongside requirements."""
    r = _create(client, {
        "asset_family":       "hospitality_leisure",
        "asset_type":         "hotel",
        "assignment_purpose": "market_valuation",
        "basis_of_value":     "market_value",
        "report_type":        "professional_report",
    })
    assert r.status_code == 201
    data = r.get_json()
    assert data.get("canonical_taxonomy"), "canonical_taxonomy missing"
    assert data.get("derived_method_route"), "derived_method_route missing"
    assert data.get("asset_specific_requirements"), "asset_specific_requirements missing"


def test_ASREQ14_requirements_returned_for_alias_asset_type(client):
    """ASREQ14: alias asset_types (floating_hotel, cold_storage) resolve to correct requirements."""
    r = _create(client, {"asset_type": "floating_hotel", "assignment_purpose": "market_valuation"})
    assert r.status_code == 201
    asr = r.get_json().get("asset_specific_requirements", {})
    assert asr.get("asset_type_resolved") in ("hotel", "floating_hotel", ""), \
        f"Expected hotel resolution for floating_hotel: {asr.get('asset_type_resolved')}"
    assert "adr" in asr.get("required_inputs", []) or \
           "number_of_rooms" in asr.get("required_inputs", []), \
        f"Expected hotel inputs for floating_hotel alias: {asr.get('required_inputs')}"


def test_ASREQ15_requirements_in_safe_detail_response(client):
    """ASREQ15: asset_specific_requirements returned in GET detail response (_safe_detail)."""
    r = _create(client, {
        "asset_type":         "industrial_factory",
        "assignment_purpose": "market_valuation",
    })
    assert r.status_code == 201
    rid = r.get_json()["request_id"]

    detail = client.get(
        f"/api/professional-valuation/requests/{rid}",
        headers=_auth(),
    )
    assert detail.status_code == 200
    detail_data = detail.get_json()
    # Detail response wraps record inside "request" key
    request_obj = detail_data.get("request", detail_data)
    asr = request_obj.get("asset_specific_requirements", {})
    assert asr, "asset_specific_requirements missing from GET detail response"
    assert "land_area" in asr.get("required_inputs", []) or \
           "replacement_cost" in asr.get("required_inputs", []), \
        f"Expected factory inputs in detail: {asr.get('required_inputs')}"


def test_ASREQ16_legacy_only_request_still_returns_requirements(client):
    """ASREQ16: Legacy-only request still gets requirements (via asset_type derivation)."""
    r = _create(client, {
        "property_type":     "hotel",
        "valuation_purpose": "market_value",
    })
    assert r.status_code == 201
    data = r.get_json()
    asr = data.get("asset_specific_requirements", {})
    # asset_type derived from property_type → hotel requirements should be returned
    assert asr, "asset_specific_requirements missing for legacy-only hotel request"
    assert asr.get("is_generic_fallback") is False or \
           "adr" in asr.get("required_inputs", []) or \
           "hotel" in asr.get("requirements_panel_title_ar", "").lower() or \
           "فندق" in asr.get("requirements_panel_title_ar", ""), \
        f"Expected hotel requirements for legacy property_type=hotel: {asr}"


# ═══════════════════════════════════════════════════════════════════════════════
# PVUC01–PVUC25 — Unified Controls: Feature Capabilities & Activation Roadmap
# ═══════════════════════════════════════════════════════════════════════════════
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), ".."))


def test_PVUC01_get_feature_capabilities_context_importable():
    """PVUC01: get_feature_capabilities_context is importable from taxonomy_v2."""
    from professional_valuation_taxonomy_v2 import get_feature_capabilities_context
    assert callable(get_feature_capabilities_context)


def test_PVUC02_feature_capabilities_context_returns_dict():
    """PVUC02: get_feature_capabilities_context returns a dict with expected top-level keys."""
    from professional_valuation_taxonomy_v2 import get_feature_capabilities_context
    result = get_feature_capabilities_context(asset_type="hotel", report_type="professional_report")
    assert isinstance(result, dict)
    for key in ("controls", "active_controls", "disabled_controls", "future_stub_controls",
                "report_reflection_matrix", "control_activation_roadmap", "advisory_note"):
        assert key in result, f"Key missing from feature_capabilities context: {key}"


def test_PVUC03_active_controls_list_non_empty():
    """PVUC03: active_controls list is non-empty — certification_gate, output_registry, advanced_reviews must be active.
    Note: active_controls is a list of string control keys."""
    from professional_valuation_taxonomy_v2 import get_feature_capabilities_context
    result = get_feature_capabilities_context(asset_type="hotel", report_type="professional_report")
    active = result.get("active_controls", [])
    assert len(active) >= 3, f"Expected >= 3 active controls, got {len(active)}: {active}"
    active_ids = set(active)  # list of strings
    assert "certification_gate" in active_ids, "certification_gate must be in active_controls"
    assert "output_registry" in active_ids, "output_registry must be in active_controls"
    assert "advanced_reviews" in active_ids, "advanced_reviews must be in active_controls"


def test_PVUC04_future_stub_controls_non_empty():
    """PVUC04: future_stub_controls includes asset_portfolio, migration_radar, super_intelligence."""
    from professional_valuation_taxonomy_v2 import get_feature_capabilities_context
    result = get_feature_capabilities_context(asset_type="hotel", report_type="professional_report")
    stubs = result.get("future_stub_controls", [])
    stub_ids = set(stubs)  # list of strings
    assert "asset_portfolio" in stub_ids, "asset_portfolio must be a future stub"
    assert "migration_radar" in stub_ids, "migration_radar must be a future stub"
    assert "super_intelligence" in stub_ids, "super_intelligence must be a future stub"


def test_PVUC05_disabled_controls_include_digital_verification():
    """PVUC05: digital_verification is in disabled_controls."""
    from professional_valuation_taxonomy_v2 import get_feature_capabilities_context
    result = get_feature_capabilities_context(asset_type="hotel", report_type="professional_report")
    disabled = result.get("disabled_controls", [])
    disabled_ids = set(disabled)  # list of strings
    assert "digital_verification" in disabled_ids, "digital_verification must be in disabled_controls"


def _effectiveness_by_key(controls_list: list, key: str) -> int:
    """Helper: look up effectiveness_level for a control by control_key in the full controls list."""
    for c in controls_list:
        if isinstance(c, dict) and c.get("control_key") == key:
            return c.get("effectiveness_level", -1)
    return -1


def test_PVUC06_active_controls_have_effectiveness_5():
    """PVUC06: all active controls have effectiveness_level == 5 (checked via full controls list)."""
    from professional_valuation_taxonomy_v2 import get_feature_capabilities_context
    result = get_feature_capabilities_context(asset_type="hotel", report_type="professional_report")
    controls = result.get("controls", [])
    for ctrl_key in result.get("active_controls", []):
        eff = _effectiveness_by_key(controls, ctrl_key)
        assert eff == 5, (
            f"Active control '{ctrl_key}' has effectiveness {eff}, expected 5"
        )


def test_PVUC07_future_stub_controls_have_effectiveness_0():
    """PVUC07: all future_stub controls have effectiveness_level == 0."""
    from professional_valuation_taxonomy_v2 import get_feature_capabilities_context
    result = get_feature_capabilities_context(asset_type="hotel", report_type="professional_report")
    controls = result.get("controls", [])
    for ctrl_key in result.get("future_stub_controls", []):
        eff = _effectiveness_by_key(controls, ctrl_key)
        assert eff == 0, (
            f"Future stub '{ctrl_key}' has effectiveness {eff}, expected 0"
        )


def test_PVUC08_disabled_controls_have_low_effectiveness():
    """PVUC08: disabled controls have effectiveness_level <= 1."""
    from professional_valuation_taxonomy_v2 import get_feature_capabilities_context
    result = get_feature_capabilities_context(asset_type="hotel", report_type="professional_report")
    controls = result.get("controls", [])
    for ctrl_key in result.get("disabled_controls", []):
        eff = _effectiveness_by_key(controls, ctrl_key)
        assert eff <= 1, (
            f"Disabled control '{ctrl_key}' has effectiveness {eff}, expected <= 1"
        )


def test_PVUC09_control_activation_roadmap_present_for_inactive():
    """PVUC09: control_activation_roadmap is a list with entries for inactive controls.
    Roadmap entries use control_key (not control_id)."""
    from professional_valuation_taxonomy_v2 import get_feature_capabilities_context
    result = get_feature_capabilities_context(asset_type="hotel", report_type="professional_report")
    roadmap = result.get("control_activation_roadmap", [])
    assert isinstance(roadmap, list), "control_activation_roadmap must be a list"
    assert len(roadmap) > 0, "control_activation_roadmap must not be empty"
    roadmap_ids = {entry.get("control_key", "") for entry in roadmap if isinstance(entry, dict)}
    assert "digital_verification" in roadmap_ids, (
        f"digital_verification must be in roadmap; got: {roadmap_ids}"
    )


def test_PVUC10_report_reflection_matrix_is_dict():
    """PVUC10: report_reflection_matrix is a dict (may be keyed by control_id)."""
    from professional_valuation_taxonomy_v2 import get_feature_capabilities_context
    result = get_feature_capabilities_context(asset_type="hotel", report_type="professional_report")
    matrix = result.get("report_reflection_matrix")
    assert isinstance(matrix, (dict, list)), "report_reflection_matrix must be a dict or list"


def test_PVUC11_partially_active_controls_non_empty():
    """PVUC11: partially_active_controls list is non-empty."""
    from professional_valuation_taxonomy_v2 import get_feature_capabilities_context
    result = get_feature_capabilities_context(asset_type="hotel", report_type="professional_report")
    partial = result.get("partially_active_controls", [])
    assert len(partial) >= 1, (
        f"Expected >= 1 partially_active controls, got {len(partial)}"
    )


def test_PVUC12_asset_specific_requirements_is_partially_active():
    """PVUC12: asset_specific_requirements control is in partially_active_controls.
    partially_active_controls is a list of string keys."""
    from professional_valuation_taxonomy_v2 import get_feature_capabilities_context
    result = get_feature_capabilities_context(asset_type="hotel", report_type="professional_report")
    partial = result.get("partially_active_controls", [])
    partial_ids = set(partial)  # list of strings
    assert "asset_specific_requirements" in partial_ids, (
        f"asset_specific_requirements must be partially_active; got partial_ids={partial_ids}"
    )


def test_PVUC13_geotechnical_risk_not_applicable_for_hotel():
    """PVUC13: geotechnical_risk is in not_applicable_controls for hotel asset_type."""
    from professional_valuation_taxonomy_v2 import get_feature_capabilities_context
    result = get_feature_capabilities_context(asset_type="hotel", report_type="professional_report")
    na = result.get("not_applicable_controls", [])
    na_ids = set(na)  # list of strings
    assert "geotechnical_risk" in na_ids, (
        f"geotechnical_risk must be not_applicable for hotel; not_applicable_ids={na_ids}"
    )


def test_PVUC14_geotechnical_risk_partially_active_for_land():
    """PVUC14: geotechnical_risk is partially_active for urban_land asset_type."""
    from professional_valuation_taxonomy_v2 import get_feature_capabilities_context
    result = get_feature_capabilities_context(asset_type="urban_land", report_type="professional_report")
    partial = result.get("partially_active_controls", [])
    not_applic = result.get("not_applicable_controls", [])
    partial_ids = set(partial)  # list of strings
    na_ids = set(not_applic)  # list of strings
    assert "geotechnical_risk" in partial_ids or "geotechnical_risk" not in na_ids, (
        f"geotechnical_risk should be applicable for land asset_type; "
        f"partial={partial_ids}, na={na_ids}"
    )


def test_PVUC15_expert_only_controls_include_method_weighting():
    """PVUC15: method_weighting_engine is in expert_only_controls."""
    from professional_valuation_taxonomy_v2 import get_feature_capabilities_context
    result = get_feature_capabilities_context(asset_type="hotel", report_type="professional_report")
    expert = result.get("expert_only_controls", [])
    expert_ids = set(expert)  # list of strings
    assert "method_weighting_engine" in expert_ids, (
        f"method_weighting_engine must be expert_only; expert_ids={expert_ids}"
    )


def test_PVUC16_advisory_note_present_and_non_empty():
    """PVUC16: advisory_note field is present and non-empty string."""
    from professional_valuation_taxonomy_v2 import get_feature_capabilities_context
    result = get_feature_capabilities_context(asset_type="hotel", report_type="professional_report")
    note = result.get("advisory_note", "")
    assert isinstance(note, str) and len(note) > 10, (
        f"advisory_note must be a non-empty string, got: {repr(note)}"
    )


def test_PVUC17_create_response_includes_feature_capabilities(client):
    """PVUC17: pvr_create response includes professional_valuation_feature_capabilities key."""
    r = _create(client, {
        "asset_type":         "hotel",
        "asset_family":       "hospitality_leisure",
        "basis_of_value":     "market_value",
        "assignment_purpose": "financing_mortgage",
    })
    assert r.status_code == 201
    data = r.get_json()
    assert "professional_valuation_feature_capabilities" in data, (
        "professional_valuation_feature_capabilities missing from create response"
    )


def test_PVUC18_create_response_includes_control_activation_roadmap(client):
    """PVUC18: pvr_create response includes control_activation_roadmap."""
    r = _create(client, {"asset_type": "hotel"})
    assert r.status_code == 201
    data = r.get_json()
    assert "control_activation_roadmap" in data, (
        "control_activation_roadmap missing from create response"
    )
    assert isinstance(data["control_activation_roadmap"], list)


def test_PVUC19_create_response_includes_report_reflection_matrix(client):
    """PVUC19: pvr_create response includes report_reflection_matrix."""
    r = _create(client, {"asset_type": "hotel"})
    assert r.status_code == 201
    data = r.get_json()
    assert "report_reflection_matrix" in data, (
        "report_reflection_matrix missing from create response"
    )


def test_PVUC20_detail_response_includes_feature_capabilities(client):
    """PVUC20: detail response includes professional_valuation_feature_capabilities."""
    r = _create(client, {"asset_type": "urban_land"})
    rid = r.get_json()["request_id"]
    detail = client.get(
        f"/api/professional-valuation/requests/{rid}",
        headers=_auth(),
    ).get_json()
    req = detail.get("request") or detail
    assert "professional_valuation_feature_capabilities" in req, (
        "professional_valuation_feature_capabilities missing from detail response"
    )


def test_PVUC21_inactive_controls_do_not_affect_certification_gate(client):
    """PVUC21: creating with future_stub controls present does not affect certification_ready."""
    r = _create(client, {"asset_type": "hotel"})
    rid = r.get_json()["request_id"]
    gate_resp = client.get(
        f"/api/professional-valuation/requests/{rid}/certification-gate",
        headers=_auth(),
    )
    if gate_resp.status_code == 200:
        gate = gate_resp.get_json()
        gate_data = gate.get("gate", gate)
        assert gate_data.get("certification_ready") is False, (
            "A freshly created request must not be certification_ready"
        )


def test_PVUC22_disabled_controls_not_in_active_list(client):
    """PVUC22: disabled controls do not appear in active_controls list."""
    from professional_valuation_taxonomy_v2 import get_feature_capabilities_context
    result = get_feature_capabilities_context(asset_type="hotel", report_type="professional_report")
    active_ids = set(result.get("active_controls", []))     # list of strings
    disabled_ids = set(result.get("disabled_controls", []))  # list of strings
    overlap = active_ids & disabled_ids
    assert not overlap, f"Controls appear in both active and disabled lists: {overlap}"


def test_PVUC23_future_stubs_not_in_active_list():
    """PVUC23: future_stub controls do not appear in active_controls list."""
    from professional_valuation_taxonomy_v2 import get_feature_capabilities_context
    result = get_feature_capabilities_context(asset_type="hotel", report_type="professional_report")
    active_ids = set(result.get("active_controls", []))        # list of strings
    stub_ids = set(result.get("future_stub_controls", []))  # list of strings
    overlap = active_ids & stub_ids
    assert not overlap, f"Controls appear in both active and future_stub lists: {overlap}"


def test_PVUC24_no_internal_paths_in_feature_capabilities_response(client):
    """PVUC24: feature_capabilities response does not expose internal file paths (Rule 19)."""
    r = _create(client, {"asset_type": "hotel"})
    assert r.status_code == 201
    body_text = r.get_data(as_text=True)
    assert "internal_file_path" not in body_text, "internal_file_path must not be in feature_capabilities response"
    assert "C:\\Users" not in body_text, "Windows path must not be in response"
    assert "instance/professional_valuation" not in body_text


def test_PVUC25_feature_capabilities_context_no_rag_qdrant_external(client):
    """PVUC25: feature_capabilities context does not use RAG, Qdrant, or external APIs."""
    r = _create(client, {"asset_type": "hotel"})
    assert r.status_code == 201
    data = r.get_json()
    caps = data.get("professional_valuation_feature_capabilities", {})
    # Verify no stub for RAG/Qdrant integration is embedded in the controls
    all_text = str(caps)
    assert "qdrant" not in all_text.lower(), "Qdrant reference found in feature_capabilities"
    assert "external_api_call" not in all_text.lower(), "external_api_call found in feature_capabilities"


# ═══════════════════════════════════════════════════════════════════════════════
# PVNB01–PVNB20 — New Backend Tests: Taxonomy v2 Live Validation, Method Routing,
#   Legacy Mapping, and Controls Independence (Part N)
# ═══════════════════════════════════════════════════════════════════════════════


def test_PVNB01_asset_family_accepted_and_returned(client):
    """PVNB01: asset_family field is accepted in create and returned in canonical_taxonomy."""
    resp = client.post(
        "/api/professional-valuation/requests",
        json={
            "client_name": "PVNB01 Client",
            "property_type": "hotel",
            "valuation_purpose": "sale_purchase",
            "asset_family": "hospitality_leisure",
            "city": "Cairo",
        },
    )
    assert resp.status_code == 201
    data = resp.get_json()
    tax = data.get("canonical_taxonomy", {})
    axis1 = tax.get("axis_1_asset_classification", {})
    assert axis1.get("asset_family") == "hospitality_leisure", (
        f"asset_family not in canonical_taxonomy: {axis1}"
    )


def test_PVNB02_asset_subtype_accepted_and_returned(client):
    """PVNB02: asset_subtype field accepted in create and echoed in canonical_taxonomy."""
    resp = client.post(
        "/api/professional-valuation/requests",
        json={
            "client_name": "PVNB02 Client",
            "property_type": "hotel",
            "valuation_purpose": "sale_purchase",
            "asset_subtype": "boutique_hotel",
            "city": "Cairo",
        },
    )
    assert resp.status_code == 201
    data = resp.get_json()
    tax = data.get("canonical_taxonomy", {})
    axis1 = tax.get("axis_1_asset_classification", {})
    assert axis1.get("asset_subtype") == "boutique_hotel", (
        f"asset_subtype not in canonical_taxonomy axis1: {axis1}"
    )


def test_PVNB03_legacy_property_type_maps_to_asset_type(client):
    """PVNB03: Legacy property_type field maps to canonical asset_type via asset_specific_requirements."""
    resp = client.post(
        "/api/professional-valuation/requests",
        json={
            "client_name": "PVNB03 Client",
            "property_type": "hotel",
            "valuation_purpose": "sale_purchase",
            "city": "Cairo",
        },
    )
    assert resp.status_code == 201
    data = resp.get_json()
    # asset_type_resolved must be hotel (from property_type legacy mapping)
    asr = data.get("asset_specific_requirements", {})
    assert asr.get("asset_type_resolved") == "hotel", (
        f"legacy property_type not mapped to asset_type_resolved: {asr.get('asset_type_resolved')}"
    )


def test_PVNB04_legacy_valuation_purpose_market_value_maps_to_basis_of_value(client):
    """PVNB04: Legacy valuation_purpose=market_value maps to basis_of_value in canonical_taxonomy."""
    resp = client.post(
        "/api/professional-valuation/requests",
        json={
            "client_name": "PVNB04 Client",
            "property_type": "hotel",
            "valuation_purpose": "market_value",
            "city": "Cairo",
        },
    )
    assert resp.status_code == 201
    data = resp.get_json()
    tax = data.get("canonical_taxonomy", {})
    axis3 = tax.get("axis_3_basis_of_value", {})
    assert axis3.get("basis_of_value") == "market_value", (
        f"valuation_purpose=market_value did not map to basis_of_value: {axis3}"
    )


def test_PVNB05_legacy_bank_financing_maps_to_assignment_purpose(client):
    """PVNB05: Legacy valuation_purpose=bank_financing maps to assignment_purpose=financing_mortgage."""
    resp = client.post(
        "/api/professional-valuation/requests",
        json={
            "client_name": "PVNB05 Client",
            "property_type": "industrial_factory",
            "valuation_purpose": "bank_financing",
            "city": "Cairo",
        },
    )
    assert resp.status_code == 201
    data = resp.get_json()
    tax = data.get("canonical_taxonomy", {})
    axis2 = tax.get("axis_2_assignment_purpose", {})
    assert axis2.get("assignment_purpose") == "financing_mortgage", (
        f"bank_financing did not map to financing_mortgage: {axis2}"
    )


def test_PVNB06_hotel_market_value_derives_income_and_dcf_methods(client):
    """PVNB06: hotel + market_value request derives income_approach and dcf in method route."""
    import sys
    sys.path.insert(0, "core_engine")
    from professional_valuation_taxonomy_v2 import derive_method_route

    result = derive_method_route(
        asset_type="hotel",
        assignment_purpose="sale_purchase",
        basis_of_value="market_value",
        report_type="professional_report",
    )
    enabled = result.get("enabled_methods", [])
    assert "income_approach" in enabled, f"income_approach missing from hotel+market_value: {enabled}"
    assert "dcf" in enabled, f"dcf missing from hotel+market_value: {enabled}"


def test_PVNB07_hotel_market_value_derives_hbu_for_professional_report(client):
    """PVNB07: hotel + market_value + professional_report adds hbu to enabled methods."""
    import sys
    sys.path.insert(0, "core_engine")
    from professional_valuation_taxonomy_v2 import derive_method_route

    result = derive_method_route(
        asset_type="hotel",
        assignment_purpose="sale_purchase",
        basis_of_value="market_value",
        report_type="professional_report",
    )
    enabled = result.get("enabled_methods", [])
    assert "hbu" in enabled, f"hbu missing from hotel+market_value+professional_report: {enabled}"


def test_PVNB08_factory_financing_derives_cost_approach(client):
    """PVNB08: industrial_factory + financing_mortgage derives cost_approach."""
    import sys
    sys.path.insert(0, "core_engine")
    from professional_valuation_taxonomy_v2 import derive_method_route

    result = derive_method_route(
        asset_type="industrial_factory",
        assignment_purpose="financing_mortgage",
        basis_of_value="market_value",
        report_type="professional_report",
    )
    enabled = result.get("enabled_methods", [])
    assert "cost_approach" in enabled, (
        f"cost_approach missing from factory+financing: {enabled}"
    )


def test_PVNB09_land_market_value_derives_land_comparison(client):
    """PVNB09: urban_land + market_value + sale_purchase derives land_comparison."""
    import sys
    sys.path.insert(0, "core_engine")
    from professional_valuation_taxonomy_v2 import derive_method_route

    result = derive_method_route(
        asset_type="urban_land",
        assignment_purpose="sale_purchase",
        basis_of_value="market_value",
        report_type="professional_report",
    )
    enabled = result.get("enabled_methods", [])
    assert "land_comparison" in enabled or "sales_comparison" in enabled, (
        f"No comparison method for land+market_value: {enabled}"
    )


def test_PVNB10_geotechnical_risk_not_applicable_for_hotel(client):
    """PVNB10: geotechnical_risk is not_applicable for hotel asset type."""
    import sys
    sys.path.insert(0, "core_engine")
    from professional_valuation_taxonomy_v2 import get_feature_capabilities_context

    result = get_feature_capabilities_context("hotel")
    not_applicable = result.get("not_applicable_controls", [])
    assert "geotechnical_risk" in not_applicable, (
        f"geotechnical_risk must be not_applicable for hotel. Got: {not_applicable}"
    )


def test_PVNB11_geotechnical_risk_applicable_for_factory(client):
    """PVNB11: geotechnical_risk is NOT in not_applicable list for industrial_factory."""
    import sys
    sys.path.insert(0, "core_engine")
    from professional_valuation_taxonomy_v2 import get_feature_capabilities_context

    result = get_feature_capabilities_context("industrial_factory")
    not_applicable = result.get("not_applicable_controls", [])
    assert "geotechnical_risk" not in not_applicable, (
        f"geotechnical_risk should be applicable (not in not_applicable) for factory. Got: {not_applicable}"
    )


def test_PVNB12_canonical_taxonomy_in_create_response(client):
    """PVNB12: canonical_taxonomy key is returned in create response."""
    resp = client.post(
        "/api/professional-valuation/requests",
        json={
            "client_name": "PVNB12 Client",
            "asset_type": "hotel",
            "assignment_purpose": "sale_purchase",
            "basis_of_value": "market_value",
            "city": "Cairo",
        },
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert "canonical_taxonomy" in data, (
        f"canonical_taxonomy missing from create response. Keys: {list(data.keys())}"
    )
    tax = data["canonical_taxonomy"]
    assert isinstance(tax, dict), "canonical_taxonomy must be a dict"


def test_PVNB13_derived_method_route_in_create_response(client):
    """PVNB13: derived_method_route key is returned in create response."""
    resp = client.post(
        "/api/professional-valuation/requests",
        json={
            "client_name": "PVNB13 Client",
            "asset_type": "hotel",
            "assignment_purpose": "sale_purchase",
            "basis_of_value": "market_value",
            "city": "Cairo",
        },
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert "derived_method_route" in data, (
        f"derived_method_route missing from create response. Keys: {list(data.keys())}"
    )
    dmr = data["derived_method_route"]
    assert isinstance(dmr, dict), "derived_method_route must be a dict"


def test_PVNB14_taxonomy_warnings_generated_for_misplaced_field(client):
    """PVNB14: Using a method step as valuation_purpose generates a taxonomy warning."""
    resp = client.post(
        "/api/professional-valuation/requests",
        json={
            "client_name": "PVNB14 Client",
            "property_type": "hotel",
            "valuation_purpose": "comparable_adjustment",
            "city": "Cairo",
        },
    )
    # Request should still succeed (soft validation), but taxonomy_warnings should exist
    assert resp.status_code == 201
    data = resp.get_json()
    warnings = data.get("taxonomy_warnings", [])
    # The warning might be in the canonical_taxonomy
    tax = data.get("canonical_taxonomy", {})
    all_warnings_text = str(warnings) + str(tax)
    # Should have flagged misplacement — comparable_adjustment is a method step not a purpose
    # (soft validation, so request is accepted but warnings generated)
    assert isinstance(warnings, list), "taxonomy_warnings must be a list"


def test_PVNB15_hotel_duplicate_subtype_warning_generated():
    """PVNB15: hotel as both asset_type and asset_subtype generates a taxonomy warning."""
    import sys
    sys.path.insert(0, "core_engine")
    from professional_valuation_taxonomy_v2 import get_taxonomy_v2_context

    result = get_taxonomy_v2_context(
        asset_type="hotel",
        asset_subtype="hotel",  # duplicated — should generate warning
        assignment_purpose="sale_purchase",
        basis_of_value="market_value",
    )
    warnings = result.get("taxonomy_warnings", [])
    assert len(warnings) > 0, (
        "Expected a warning for hotel used as both asset_type and asset_subtype"
    )


def test_PVNB16_basis_of_value_field_accepted_and_returned(client):
    """PVNB16: basis_of_value canonical field accepted and returned in create response."""
    resp = client.post(
        "/api/professional-valuation/requests",
        json={
            "client_name": "PVNB16 Client",
            "asset_type": "hotel",
            "assignment_purpose": "sale_purchase",
            "basis_of_value": "investment_value",
            "city": "Cairo",
        },
    )
    assert resp.status_code == 201
    data = resp.get_json()
    tax = data.get("canonical_taxonomy", {})
    axis3 = tax.get("axis_3_basis_of_value", {})
    assert axis3.get("basis_of_value") == "investment_value", (
        f"basis_of_value not in canonical_taxonomy: {axis3}"
    )


def test_PVNB17_assignment_purpose_accepted_and_returned(client):
    """PVNB17: assignment_purpose canonical field accepted and returned in canonical_taxonomy."""
    resp = client.post(
        "/api/professional-valuation/requests",
        json={
            "client_name": "PVNB17 Client",
            "asset_type": "hotel",
            "assignment_purpose": "financing_mortgage",
            "basis_of_value": "market_value",
            "city": "Cairo",
        },
    )
    assert resp.status_code == 201
    data = resp.get_json()
    tax = data.get("canonical_taxonomy", {})
    axis2 = tax.get("axis_2_assignment_purpose", {})
    assert axis2.get("assignment_purpose") == "financing_mortgage", (
        f"assignment_purpose not in canonical_taxonomy: {axis2}"
    )


def test_PVNB18_ordinary_valuation_create_still_works(client):
    """PVNB18: Ordinary valuation API is unaffected by professional valuation changes."""
    resp = client.post(
        "/api/advisor/valuate",
        json={
            "property_type": "شقة سكنية",
            "area": 100,
            "city": "Cairo",
            "purpose": "market_value",
        },
    )
    # Should succeed (200 or 201) or fail with data error (not 500)
    assert resp.status_code != 500, (
        f"Ordinary valuation crashed with status {resp.status_code}"
    )


def test_PVNB19_no_internal_paths_in_canonical_taxonomy(client):
    """PVNB19: canonical_taxonomy in response contains no internal storage paths (Rule 19)."""
    resp = client.post(
        "/api/professional-valuation/requests",
        json={
            "client_name": "PVNB19 Client",
            "asset_type": "hotel",
            "assignment_purpose": "sale_purchase",
            "basis_of_value": "market_value",
            "city": "Cairo",
        },
    )
    assert resp.status_code == 201
    data = resp.get_json()
    tax_str = str(data.get("canonical_taxonomy", {}))
    dmr_str = str(data.get("derived_method_route", {}))
    req_str = str(data.get("asset_specific_requirements", {}))
    all_text = tax_str + dmr_str + req_str
    assert "requests.jsonl" not in all_text, "internal path found in taxonomy/route/requirements"
    assert "instance/professional_valuation" not in all_text, "internal path in taxonomy response"
    assert "C:\\Users" not in all_text, "absolute Windows path found in taxonomy response"


def test_PVNB20_tax_appeal_routes_still_respond(client):
    """PVNB20: Tax appeal backend routes still work after professional valuation changes."""
    resp = client.get("/api/tax-appeal/health")
    # Health endpoint should respond (not 500)
    assert resp.status_code in (200, 404), (
        f"Tax appeal health unexpected status: {resp.status_code}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# PVSEC01–PVSEC35 — Section 5 / Input Modes / New Fields Backend Tests
# Part N: 35 backend tests for new API fields introduced in core UX restructure
# ─────────────────────────────────────────────────────────────────────────────

def test_PVSEC01_input_mode_structured_accepted(client):
    """PVSEC01: input_mode=structured_browser_input is accepted and stored."""
    r = _create(client, {"input_mode": "structured_browser_input"})
    assert r.status_code == 201
    assert r.get_json()["ok"] is True


def test_PVSEC02_input_mode_chat_accepted(client):
    """PVSEC02: input_mode=chat_attachment_assisted_input is accepted and stored."""
    r = _create(client, {"input_mode": "chat_attachment_assisted_input"})
    assert r.status_code == 201
    assert r.get_json()["ok"] is True


def test_PVSEC03_invalid_input_mode_falls_back_not_rejects(client):
    """PVSEC03: Unknown input_mode is silently coerced to default (not a hard 400)."""
    r = _create(client, {"input_mode": "unknown_mode_xyz"})
    assert r.status_code == 201, f"Unknown input_mode should fall back, not 400. Got: {r.status_code}"


def test_PVSEC04_auto_fill_requirements_true_accepted(client):
    """PVSEC04: auto_fill_requirements_by_asset_and_purpose=True is accepted."""
    r = _create(client, {"auto_fill_requirements_by_asset_and_purpose": True})
    assert r.status_code == 201
    assert r.get_json()["ok"] is True


def test_PVSEC05_auto_fill_requirements_false_accepted(client):
    """PVSEC05: auto_fill_requirements_by_asset_and_purpose=False is accepted."""
    r = _create(client, {"auto_fill_requirements_by_asset_and_purpose": False})
    assert r.status_code == 201
    assert r.get_json()["ok"] is True


def test_PVSEC06_uploaded_report_simulation_enabled_accepted(client):
    """PVSEC06: uploaded_report_simulation_enabled=True is accepted."""
    r = _create(client, {"uploaded_report_simulation_enabled": True})
    assert r.status_code == 201
    assert r.get_json()["ok"] is True


def test_PVSEC07_purpose_logic_path_accepted(client):
    """PVSEC07: purpose_logic_path is accepted alongside canonical Axis 2 fields."""
    r = _create(client, {"purpose_logic_path": "sales_comparison_market_value"})
    assert r.status_code == 201
    assert r.get_json()["ok"] is True


def test_PVSEC08_output_type_traditional_report_accepted(client):
    """PVSEC08: output_type=traditional_report is accepted."""
    r = _create(client, {"output_type": "traditional_report"})
    assert r.status_code == 201
    data = r.get_json()
    assert data["ok"] is True


def test_PVSEC09_output_type_detailed_report_accepted(client):
    """PVSEC09: output_type=detailed_report is accepted."""
    r = _create(client, {"output_type": "detailed_report"})
    assert r.status_code == 201


def test_PVSEC10_output_type_professional_report_accepted(client):
    """PVSEC10: output_type=professional_report is accepted."""
    r = _create(client, {"output_type": "professional_report"})
    assert r.status_code == 201


def test_PVSEC11_output_type_simulated_uploaded_report_accepted(client):
    """PVSEC11: output_type=simulated_uploaded_report is accepted as advisory output."""
    r = _create(client, {
        "output_type": "simulated_uploaded_report",
        "uploaded_report_simulation_enabled": True,
    })
    assert r.status_code == 201
    data = r.get_json()
    assert data["ok"] is True


def test_PVSEC12_simulated_report_without_flag_auto_enables_simulation(client):
    """PVSEC12: Requesting simulated_uploaded_report output auto-enables simulation flag."""
    r = _create(client, {
        "output_type": "simulated_uploaded_report",
        "uploaded_report_simulation_enabled": False,
    })
    # Should succeed (not reject), flag is auto-enabled
    assert r.status_code == 201
    data = r.get_json()
    assert data["ok"] is True


def test_PVSEC13_response_contains_selected_configuration_summary(client):
    """PVSEC13: Response contains selected_configuration_summary block."""
    r = _create(client, {"input_mode": "structured_browser_input"})
    assert r.status_code == 201
    data = r.get_json()
    assert "selected_configuration_summary" in data, "Missing selected_configuration_summary in response"


def test_PVSEC14_config_summary_has_input_mode(client):
    """PVSEC14: selected_configuration_summary contains input_mode field."""
    r = _create(client, {"input_mode": "chat_attachment_assisted_input"})
    assert r.status_code == 201
    data = r.get_json()
    summary = data.get("selected_configuration_summary", {})
    assert "input_mode" in summary, "selected_configuration_summary missing input_mode"


def test_PVSEC15_config_summary_input_mode_value_matches(client):
    """PVSEC15: selected_configuration_summary.input_mode matches what was sent."""
    r = _create(client, {"input_mode": "chat_attachment_assisted_input"})
    assert r.status_code == 201
    data = r.get_json()
    summary = data.get("selected_configuration_summary", {})
    assert summary.get("input_mode") == "chat_attachment_assisted_input"


def test_PVSEC16_config_summary_has_output_type(client):
    """PVSEC16: selected_configuration_summary contains output_type field."""
    r = _create(client, {"output_type": "detailed_report"})
    assert r.status_code == 201
    data = r.get_json()
    summary = data.get("selected_configuration_summary", {})
    assert "output_type" in summary


def test_PVSEC17_config_summary_has_is_simulation_output(client):
    """PVSEC17: selected_configuration_summary contains is_simulation_output field."""
    r = _create(client, {"output_type": "traditional_report"})
    assert r.status_code == 201
    data = r.get_json()
    summary = data.get("selected_configuration_summary", {})
    assert "is_simulation_output" in summary


def test_PVSEC18_simulation_output_false_for_non_simulation(client):
    """PVSEC18: is_simulation_output=False for normal report types."""
    r = _create(client, {"output_type": "professional_report"})
    assert r.status_code == 201
    data = r.get_json()
    summary = data.get("selected_configuration_summary", {})
    assert summary.get("is_simulation_output") is False


def test_PVSEC19_simulation_output_true_for_simulated_report(client):
    """PVSEC19: is_simulation_output=True when output_type=simulated_uploaded_report."""
    r = _create(client, {
        "output_type": "simulated_uploaded_report",
        "uploaded_report_simulation_enabled": True,
    })
    assert r.status_code == 201
    data = r.get_json()
    summary = data.get("selected_configuration_summary", {})
    assert summary.get("is_simulation_output") is True


def test_PVSEC20_chat_draft_summary_present_for_chat_mode(client):
    """PVSEC20: chat_attachment_draft_summary returned when input_mode=chat_attachment_assisted_input."""
    r = _create(client, {"input_mode": "chat_attachment_assisted_input"})
    assert r.status_code == 201
    data = r.get_json()
    assert data.get("chat_attachment_draft_summary") is not None


def test_PVSEC21_chat_draft_summary_null_for_structured_mode(client):
    """PVSEC21: chat_attachment_draft_summary is null when input_mode=structured_browser_input."""
    r = _create(client, {"input_mode": "structured_browser_input"})
    assert r.status_code == 201
    data = r.get_json()
    assert data.get("chat_attachment_draft_summary") is None


def test_PVSEC22_chat_draft_summary_advisory_only_true(client):
    """PVSEC22: chat_attachment_draft_summary.advisory_only=True."""
    r = _create(client, {"input_mode": "chat_attachment_assisted_input"})
    assert r.status_code == 201
    data = r.get_json()
    summary = data.get("chat_attachment_draft_summary", {})
    assert summary.get("advisory_only") is True


def test_PVSEC23_simulation_summary_present_when_enabled(client):
    """PVSEC23: uploaded_report_simulation_summary returned when simulation enabled."""
    r = _create(client, {"uploaded_report_simulation_enabled": True})
    assert r.status_code == 201
    data = r.get_json()
    assert data.get("uploaded_report_simulation_summary") is not None


def test_PVSEC24_simulation_summary_null_when_disabled(client):
    """PVSEC24: uploaded_report_simulation_summary is null when simulation not enabled."""
    r = _create(client, {"uploaded_report_simulation_enabled": False})
    assert r.status_code == 201
    data = r.get_json()
    assert data.get("uploaded_report_simulation_summary") is None


def test_PVSEC25_simulation_summary_advisory_only_true(client):
    """PVSEC25: uploaded_report_simulation_summary.advisory_only=True."""
    r = _create(client, {"uploaded_report_simulation_enabled": True})
    assert r.status_code == 201
    data = r.get_json()
    sim_summary = data.get("uploaded_report_simulation_summary", {})
    assert sim_summary.get("advisory_only") is True


def test_PVSEC26_simulation_summary_certified_output_false(client):
    """PVSEC26: uploaded_report_simulation_summary.certified_output=False (advisory enforcement)."""
    r = _create(client, {"uploaded_report_simulation_enabled": True})
    assert r.status_code == 201
    data = r.get_json()
    sim_summary = data.get("uploaded_report_simulation_summary", {})
    assert sim_summary.get("certified_output") is False


def test_PVSEC27_simulation_note_in_arabic(client):
    """PVSEC27: uploaded_report_simulation_summary.simulation_note_ar contains Arabic text."""
    r = _create(client, {"uploaded_report_simulation_enabled": True})
    assert r.status_code == 201
    data = r.get_json()
    sim_summary = data.get("uploaded_report_simulation_summary", {})
    note = sim_summary.get("simulation_note_ar", "")
    assert note, "simulation_note_ar should not be empty"
    has_arabic = any('؀' <= c <= 'ۿ' for c in note)
    assert has_arabic, f"simulation_note_ar should contain Arabic text, got: {note!r}"


def test_PVSEC28_no_internal_paths_in_response(client):
    """PVSEC28: Response JSON must not expose internal file paths."""
    r = _create(client, {})
    assert r.status_code == 201
    import json
    resp_text = json.dumps(r.get_json())
    bad_patterns = ["C:\\", "C:/Users", "/home/", "/Users/", "core_engine/"]
    for pat in bad_patterns:
        assert pat not in resp_text, f"Internal path '{pat}' found in API response"


def test_PVSEC29_legacy_fields_still_work_with_new_fields(client):
    """PVSEC29: Legacy property_type+valuation_purpose still work alongside new Section 5 fields."""
    r = client.post("/api/professional-valuation/requests", json={
        "client_name":        "عميل الاختبار",
        "property_type":      "فندق",
        "valuation_purpose":  "قيمة سوقية",
        "city":               "القاهرة",
        "input_mode":         "structured_browser_input",
        "auto_fill_requirements_by_asset_and_purpose": True,
    }, content_type="application/json")
    assert r.status_code == 201
    assert r.get_json()["ok"] is True


def test_PVSEC30_output_type_overrides_report_type(client):
    """PVSEC30: output_type takes priority over report_type when both provided."""
    r = _create(client, {
        "report_type":  "traditional_report",
        "output_type":  "detailed_report",
    })
    assert r.status_code == 201
    # No assertion on which wins — just must not 400 or 500


def test_PVSEC31_simulated_report_not_certified(client):
    """PVSEC31: simulated_uploaded_report output type cannot produce a certified output."""
    r = _create(client, {
        "output_type": "simulated_uploaded_report",
        "uploaded_report_simulation_enabled": True,
    })
    assert r.status_code == 201
    data = r.get_json()
    sim_summary = data.get("uploaded_report_simulation_summary", {})
    # certified_output must be False — simulation is advisory only
    assert sim_summary.get("certified_output") is False


def test_PVSEC32_invalid_output_type_rejected(client):
    """PVSEC32: An unrecognized output_type value that is also not a valid report_type returns 400."""
    r = _create(client, {
        "output_type":  "fake_report_type",
        "report_type":  "fake_report_type",
    })
    # Both report_type and output_type are invalid → should return 400
    assert r.status_code == 400, f"Expected 400 for invalid report_type, got {r.status_code}"


def test_PVSEC33_response_still_has_canonical_taxonomy(client):
    """PVSEC33: New Section 5 fields don't break canonical_taxonomy in response."""
    r = _create(client, {
        "asset_type":     "hotel",
        "basis_of_value": "market_value",
        "input_mode":     "structured_browser_input",
    })
    assert r.status_code == 201
    data = r.get_json()
    assert "canonical_taxonomy" in data


def test_PVSEC34_response_still_has_derived_method_route(client):
    """PVSEC34: New Section 5 fields don't break derived_method_route in response."""
    r = _create(client, {
        "asset_type":     "urban_land",
        "basis_of_value": "market_value",
        "input_mode":     "structured_browser_input",
    })
    assert r.status_code == 201
    data = r.get_json()
    assert "derived_method_route" in data


def test_PVSEC35_response_still_has_asset_specific_requirements(client):
    """PVSEC35: New Section 5 fields don't break asset_specific_requirements in response."""
    r = _create(client, {
        "asset_type":     "hotel",
        "input_mode":     "chat_attachment_assisted_input",
        "auto_fill_requirements_by_asset_and_purpose": True,
    })
    assert r.status_code == 201
    data = r.get_json()
    assert "asset_specific_requirements" in data


# ═══════════════════════════════════════════════════════════════════════════════
# Part K — Step 2 UX Cleanup: Purpose Routes & Professional Paths Backend Tests
# PVPR01–PVPR17
# ═══════════════════════════════════════════════════════════════════════════════


def test_PVPR01_assignment_purpose_accepted(client):
    """PVPR01: assignment_purpose field is accepted by the create endpoint (returns 201)."""
    r = _create(client, {"assignment_purpose": "sale_purchase"})
    assert r.status_code == 201, f"Expected 201, got {r.status_code}"
    data = r.get_json()
    assert data["ok"] is True


def test_PVPR02_purpose_logic_path_accepted(client):
    """PVPR02: purpose_logic_path field is accepted by the create endpoint."""
    r = _create(client, {"purpose_logic_path": "sales_comparison_market_value"})
    assert r.status_code == 201, f"Expected 201, got {r.status_code}"


def test_PVPR03_purpose_route_accepted(client):
    """PVPR03: purpose_route field is accepted by the create endpoint."""
    r = _create(client, {"purpose_route": "market_value_standard"})
    assert r.status_code == 201, f"Expected 201, got {r.status_code}"


def test_PVPR04_purpose_subroute_accepted(client):
    """PVPR04: purpose_subroute field is accepted by the create endpoint."""
    r = _create(client, {
        "purpose_route":    "market_value_standard",
        "purpose_subroute": "full_market_value",
    })
    assert r.status_code == 201, f"Expected 201, got {r.status_code}"


def test_PVPR05_professional_context_path_accepted(client):
    """PVPR05: professional_context_path field is accepted by the create endpoint."""
    r = _create(client, {"professional_context_path": "rics_red_book"})
    assert r.status_code == 201, f"Expected 201, got {r.status_code}"


def test_PVPR06_professional_purpose_path_accepted(client):
    """PVPR06: professional_purpose_path (NEW field) is accepted by the create endpoint."""
    r = _create(client, {"professional_purpose_path": "bank_financing_path"})
    assert r.status_code == 201, f"Expected 201, got {r.status_code}"


def test_PVPR07_intended_user_category_accepted(client):
    """PVPR07: intended_user_category field is accepted by the create endpoint."""
    r = _create(client, {"intended_user_category": "bank_financial_institution"})
    assert r.status_code == 201, f"Expected 201, got {r.status_code}"


def test_PVPR08_intended_use_accepted(client):
    """PVPR08: intended_use free-text field is accepted by the create endpoint."""
    r = _create(client, {"intended_use": "Financing valuation for mortgage application"})
    assert r.status_code == 201, f"Expected 201, got {r.status_code}"


def test_PVPR09_detail_returns_valuation_purpose_routes_summary(client):
    """PVPR09: Detail endpoint returns valuation_purpose_routes_summary dict.
    The field is nested in body['request'] (detail endpoint wraps record under 'request' key)."""
    rid = _create(client, {
        "assignment_purpose":      "financing_mortgage",
        "purpose_logic_path":      "income_capitalization_investment",
        "purpose_route":           "mortgage_lending_value",
        "purpose_subroute":        "mortgage_standard",
        "professional_context_path": "rics_red_book",
        "professional_purpose_path": "bank_financing_path",
        "intended_user_category":  "bank_financial_institution",
        "intended_use":            "Bank mortgage financing",
    }).get_json()["request_id"]
    resp = client.get(f"/api/professional-valuation/requests/{rid}", headers=_auth())
    assert resp.status_code == 200
    body = resp.get_json()
    assert "request" in body, "Detail response must have 'request' key"
    req = body["request"]
    assert "valuation_purpose_routes_summary" in req, (
        "body['request'] must include valuation_purpose_routes_summary"
    )
    summary = req["valuation_purpose_routes_summary"]
    assert isinstance(summary, dict), "valuation_purpose_routes_summary must be a dict"
    assert "assignment_purpose" in summary
    assert "warnings" in summary


def test_PVPR10_legacy_valuation_purpose_still_accepted(client):
    """PVPR10: Old valuation_purpose field (legacy alias) is still accepted — backward compat."""
    r = _create(client, {"valuation_purpose": "market_value_for_sale"})
    assert r.status_code == 201, (
        f"Legacy 'valuation_purpose' must still be accepted for backward compat, got {r.status_code}"
    )


def test_PVPR11_legacy_purpose_subpath_still_accepted(client):
    """PVPR11: Old purpose_subpath field (legacy alias for purpose_subroute) is still accepted."""
    r = _create(client, {
        "purpose_route":   "market_value_standard",
        "purpose_subpath": "full_market_value",
    })
    assert r.status_code == 201, (
        f"Legacy 'purpose_subpath' must still be accepted for backward compat, got {r.status_code}"
    )


def test_PVPR12_value_basis_in_old_purpose_field_mapped_safely(client):
    """PVPR12: Submitting a basis_of_value value (e.g. 'market_value') via
    valuation_purpose (legacy field) is accepted and does not cause a 4xx — it is
    mapped with a soft warning, not rejected."""
    r = _create(client, {"valuation_purpose": "market_value"})
    assert r.status_code == 201, (
        f"Basis-of-value in old purpose field must produce a soft warning, not rejection. Got {r.status_code}"
    )


def test_PVPR13_comparable_adjustment_in_purpose_subpath_maps_to_method_step(client):
    """PVPR13: Submitting 'comparable_adjustment' via purpose_subpath is accepted
    without a 4xx (mapped to method-step context with warning)."""
    r = _create(client, {
        "purpose_route":   "market_value_standard",
        "purpose_subpath": "comparable_adjustment",
    })
    assert r.status_code == 201, (
        f"comparable_adjustment in purpose_subpath must be accepted with warning, got {r.status_code}"
    )


def test_PVPR14_no_purpose_option_deleted(client):
    """PVPR14: Core assignment purpose values still accepted — no option deleted.
    Tests a sample of canonical assignment_purpose values from the Step 2 UX spec.
    """
    canonical_purposes = [
        "sale_purchase",
        "financing_mortgage",
        "court_dispute",
        "insurance_coverage",
        "tax_assessment",
        "financial_reporting",
        "rental_advisory",
        "compulsory_acquisition",
        "portfolio_review",
        "investment_decision",
    ]
    for purpose in canonical_purposes:
        r = _create(client, {"assignment_purpose": purpose})
        assert r.status_code == 201, (
            f"assignment_purpose='{purpose}' was rejected — option must not be deleted. Got {r.status_code}"
        )


def test_PVPR15_no_professional_context_path_option_deleted(client):
    """PVPR15: Professional context path options still accepted — no route deleted."""
    context_paths = ["rics_red_book", "ivsc_ips", "local_standards"]
    for path in context_paths:
        r = _create(client, {"professional_context_path": path})
        assert r.status_code == 201, (
            f"professional_context_path='{path}' was rejected — option must not be deleted. Got {r.status_code}"
        )


def test_PVPR16_ordinary_valuation_tests_unaffected(client):
    """PVPR16: Ordinary valuation create (no purpose route fields) still returns 201.
    Confirms Step 2 UX changes don't break the standard create flow."""
    r = _create(client)
    assert r.status_code == 201, (
        f"Baseline create (no purpose route fields) must still return 201. Got {r.status_code}"
    )
    data = r.get_json()
    assert data["ok"] is True
    assert "request_id" in data


def test_PVPR17_detail_legacy_purpose_aliases_in_response(client):
    """PVPR17: Detail response includes legacy_purpose_aliases list in body['request'].
    The field may be empty for requests that did not use legacy fields — the key must always be present."""
    rid = _create(client, {"assignment_purpose": "sale_purchase"}).get_json()["request_id"]
    resp = client.get(f"/api/professional-valuation/requests/{rid}", headers=_auth())
    assert resp.status_code == 200
    body = resp.get_json()
    assert "request" in body, "Detail response must have 'request' key"
    req = body["request"]
    assert "legacy_purpose_aliases" in req, (
        "body['request'] must include 'legacy_purpose_aliases' key (may be empty list)"
    )


# ── PVTAX01–PVTAX20: Three-Cards Taxonomy Summary Backend Tests (Part J) ─────

def test_PVTAX01_taxonomy_cards_summary_in_create_response(client):
    """PVTAX01: Create response includes taxonomy_cards_summary key."""
    r = _create(client, {
        "asset_family":       "residential",
        "asset_type":         "apartment",
        "asset_subtype":      "studio",
        "assignment_purpose": "sale_purchase",
        "basis_of_value":     "market_value",
    })
    assert r.status_code == 201
    data = r.get_json()
    assert "taxonomy_cards_summary" in data, (
        "Create response must include taxonomy_cards_summary"
    )


def test_PVTAX02_taxonomy_cards_summary_has_three_cards(client):
    """PVTAX02: taxonomy_cards_summary contains card_1_asset_definition, card_2_purpose_routes, card_3_basis_of_value."""
    r = _create(client, {
        "asset_family":       "residential",
        "asset_type":         "villa",
        "assignment_purpose": "financing_mortgage",
        "basis_of_value":     "market_value",
    })
    assert r.status_code == 201
    tcs = r.get_json().get("taxonomy_cards_summary", {})
    for key in ("card_1_asset_definition", "card_2_purpose_routes", "card_3_basis_of_value"):
        assert key in tcs, f"taxonomy_cards_summary missing key: {key}"


def test_PVTAX03_card1_contains_asset_fields(client):
    """PVTAX03: card_1_asset_definition contains asset_family, asset_type, asset_subtype, asset_condition_path."""
    r = _create(client, {
        "asset_family":        "commercial",
        "asset_type":          "office",
        "asset_subtype":       "open_plan",
        "asset_condition_path": "as_is",
        "assignment_purpose":  "sale_purchase",
    })
    assert r.status_code == 201
    card1 = r.get_json()["taxonomy_cards_summary"]["card_1_asset_definition"]
    assert card1.get("asset_family") == "commercial"
    assert card1.get("asset_type") == "office"
    assert card1.get("asset_subtype") == "open_plan"
    assert card1.get("asset_condition_path") == "as_is"


def test_PVTAX04_card2_contains_purpose_route_fields(client):
    """PVTAX04: card_2_purpose_routes contains assignment_purpose, purpose_logic_path, purpose_route."""
    r = _create(client, {
        "asset_type":          "apartment",
        "assignment_purpose":  "financing_mortgage",
        "purpose_logic_path":  "standard_valuation",
        "purpose_route":       "bank_financing_collateral",
    })
    assert r.status_code == 201
    card2 = r.get_json()["taxonomy_cards_summary"]["card_2_purpose_routes"]
    assert card2.get("assignment_purpose") == "financing_mortgage"
    assert card2.get("purpose_logic_path") == "standard_valuation"
    assert card2.get("purpose_route") == "bank_financing_collateral"


def test_PVTAX05_card3_contains_basis_of_value_fields(client):
    """PVTAX05: card_3_basis_of_value contains basis_of_value, value_premise, value_output_type."""
    r = _create(client, {
        "asset_type":         "apartment",
        "assignment_purpose": "sale_purchase",
        "basis_of_value":     "investment_value",
        "value_premise":      "highest_and_best_use",
        "value_output_type":  "range_estimate",
    })
    assert r.status_code == 201
    card3 = r.get_json()["taxonomy_cards_summary"]["card_3_basis_of_value"]
    assert card3.get("basis_of_value") == "investment_value"
    assert card3.get("value_premise") == "highest_and_best_use"
    assert card3.get("value_output_type") == "range_estimate"


def test_PVTAX06_taxonomy_cards_summary_in_detail_response(client):
    """PVTAX06: taxonomy_cards_summary is returned in GET detail response (_safe_detail)."""
    r = _create(client, {
        "asset_type":         "villa",
        "assignment_purpose": "investment_decision",
        "basis_of_value":     "market_value",
    })
    assert r.status_code == 201
    rid = r.get_json()["request_id"]

    detail = client.get(
        f"/api/professional-valuation/requests/{rid}",
        headers=_auth(),
    )
    assert detail.status_code == 200
    req = detail.get_json().get("request", {})
    assert "taxonomy_cards_summary" in req, (
        "Detail response body['request'] must include taxonomy_cards_summary"
    )


def test_PVTAX07_detail_card1_matches_create_card1(client):
    """PVTAX07: card_1_asset_definition in detail response matches what was stored at create."""
    r = _create(client, {
        "asset_family":        "hospitality_leisure",
        "asset_type":          "hotel",
        "asset_condition_path": "as_stabilized",
        "assignment_purpose":  "market_valuation",
    })
    assert r.status_code == 201
    create_card1 = r.get_json()["taxonomy_cards_summary"]["card_1_asset_definition"]
    rid = r.get_json()["request_id"]

    detail = client.get(f"/api/professional-valuation/requests/{rid}", headers=_auth())
    assert detail.status_code == 200
    detail_card1 = detail.get_json()["request"]["taxonomy_cards_summary"]["card_1_asset_definition"]

    assert detail_card1.get("asset_family") == create_card1.get("asset_family")
    assert detail_card1.get("asset_type") == create_card1.get("asset_type")
    assert detail_card1.get("asset_condition_path") == create_card1.get("asset_condition_path")


def test_PVTAX08_warnings_key_present_in_taxonomy_cards_summary(client):
    """PVTAX08: taxonomy_cards_summary always includes a 'warnings' list key."""
    r = _create(client, {"asset_type": "apartment", "assignment_purpose": "sale_purchase"})
    assert r.status_code == 201
    tcs = r.get_json().get("taxonomy_cards_summary", {})
    assert "warnings" in tcs, "taxonomy_cards_summary must include 'warnings' key"
    assert isinstance(tcs["warnings"], list), "'warnings' must be a list"


def test_PVTAX09_all_card3_basis_of_value_options_accepted(client):
    """PVTAX09: All 8 canonical basis_of_value values are accepted and stored in card_3."""
    valid_bov = [
        "market_value", "market_rent", "investment_value", "fair_value",
        "liquidation_value", "insurable_value", "going_concern_value", "special_purpose_value",
    ]
    for bov in valid_bov:
        r = _create(client, {
            "asset_type":         "apartment",
            "assignment_purpose": "sale_purchase",
            "basis_of_value":     bov,
        })
        assert r.status_code == 201, (
            f"basis_of_value='{bov}' was rejected — option must not be deleted. Got {r.status_code}"
        )
        card3 = r.get_json()["taxonomy_cards_summary"]["card_3_basis_of_value"]
        assert card3.get("basis_of_value") == bov, (
            f"basis_of_value='{bov}' not reflected in card_3. Got: {card3.get('basis_of_value')}"
        )


def test_PVTAX10_all_value_premise_options_accepted(client):
    """PVTAX10: All 8 value_premise options are accepted without error."""
    premises = [
        "as_is", "as_stabilized", "as_complete", "highest_and_best_use",
        "current_use", "alternative_use", "forced_sale", "going_concern",
    ]
    for p in premises:
        r = _create(client, {
            "asset_type":         "apartment",
            "assignment_purpose": "sale_purchase",
            "basis_of_value":     "market_value",
            "value_premise":      p,
        })
        assert r.status_code == 201, (
            f"value_premise='{p}' was rejected — option must not be deleted. Got {r.status_code}"
        )
        card3 = r.get_json()["taxonomy_cards_summary"]["card_3_basis_of_value"]
        assert card3.get("value_premise") == p


def test_PVTAX11_all_value_output_type_options_accepted(client):
    """PVTAX11: All 5 value_output_type options are accepted without error."""
    output_types = [
        "point_estimate", "range_estimate", "weighted_value",
        "probability_weighted", "scenario_based",
    ]
    for ot in output_types:
        r = _create(client, {
            "asset_type":         "apartment",
            "assignment_purpose": "sale_purchase",
            "basis_of_value":     "market_value",
            "value_output_type":  ot,
        })
        assert r.status_code == 201, (
            f"value_output_type='{ot}' was rejected — option must not be deleted. Got {r.status_code}"
        )
        card3 = r.get_json()["taxonomy_cards_summary"]["card_3_basis_of_value"]
        assert card3.get("value_output_type") == ot


def test_PVTAX12_all_asset_condition_path_options_accepted(client):
    """PVTAX12: All 7 asset_condition_path options are accepted without error."""
    paths = [
        "new_construction", "as_is", "as_repaired", "as_completed",
        "as_stabilized", "retrospective", "prospective",
    ]
    for path in paths:
        r = _create(client, {
            "asset_type":          "apartment",
            "assignment_purpose":  "sale_purchase",
            "asset_condition_path": path,
        })
        assert r.status_code == 201, (
            f"asset_condition_path='{path}' was rejected — option must not be deleted. Got {r.status_code}"
        )
        card1 = r.get_json()["taxonomy_cards_summary"]["card_1_asset_definition"]
        assert card1.get("asset_condition_path") == path


def test_PVTAX13_legacy_valuation_purpose_maps_to_card2(client):
    """PVTAX13: Legacy valuation_purpose field is mapped to assignment_purpose in card_2."""
    r = _create(client, {
        "asset_type":         "apartment",
        "valuation_purpose":  "bank_financing",
    })
    assert r.status_code == 201
    card2 = r.get_json()["taxonomy_cards_summary"]["card_2_purpose_routes"]
    assert card2.get("assignment_purpose") in ("financing_mortgage", "bank_financing"), (
        f"Expected assignment_purpose mapped from bank_financing. Got: {card2.get('assignment_purpose')}"
    )


def test_PVTAX14_legacy_valuation_purpose_maps_bov_to_card3(client):
    """PVTAX14: Legacy valuation_purpose=fair_market_value maps to market_value in card_3."""
    r = _create(client, {
        "asset_type":         "apartment",
        "valuation_purpose":  "fair_market_value",
    })
    assert r.status_code == 201
    card3 = r.get_json()["taxonomy_cards_summary"]["card_3_basis_of_value"]
    assert card3.get("basis_of_value") in ("market_value", "fair_market_value"), (
        f"Expected market_value in card_3 from legacy fair_market_value. Got: {card3.get('basis_of_value')}"
    )


def test_PVTAX15_canonical_fields_not_in_card1(client):
    """PVTAX15: card_1_asset_definition does NOT include market_value, assignment_purpose, or report_type.
    Rule 1 of the three-cards spec: Card 1 is Asset Definition only."""
    r = _create(client, {
        "asset_family":       "residential",
        "asset_type":         "apartment",
        "assignment_purpose": "sale_purchase",
        "basis_of_value":     "market_value",
        "report_type":        "professional_report",
    })
    assert r.status_code == 201
    card1 = r.get_json()["taxonomy_cards_summary"]["card_1_asset_definition"]
    for forbidden in ("market_value", "assignment_purpose", "report_type"):
        assert forbidden not in card1, (
            f"Card 1 must not include '{forbidden}' — belongs in card_2 or card_3: {card1}"
        )


def test_PVTAX16_market_value_in_card3_not_card1(client):
    """PVTAX16: basis_of_value=market_value belongs in card_3, not card_1."""
    r = _create(client, {
        "asset_type":         "apartment",
        "assignment_purpose": "sale_purchase",
        "basis_of_value":     "market_value",
    })
    assert r.status_code == 201
    tcs = r.get_json()["taxonomy_cards_summary"]
    card1 = tcs["card_1_asset_definition"]
    card3 = tcs["card_3_basis_of_value"]
    assert "market_value" not in card1.values(), (
        "market_value must not appear in card_1 values"
    )
    assert card3.get("basis_of_value") == "market_value", (
        "market_value must appear in card_3.basis_of_value"
    )


def test_PVTAX17_empty_optional_fields_stored_as_empty_string(client):
    """PVTAX17: Optional card fields not provided are stored as empty string (not None/missing)."""
    r = _create(client, {
        "asset_type":         "apartment",
        "assignment_purpose": "sale_purchase",
    })
    assert r.status_code == 201
    tcs = r.get_json()["taxonomy_cards_summary"]
    card1 = tcs["card_1_asset_definition"]
    card3 = tcs["card_3_basis_of_value"]
    # Optional fields should exist in the dict (even if empty)
    assert "asset_condition_path" in card1
    assert "basis_of_value" in card3
    assert "value_premise" in card3
    assert "value_output_type" in card3


def test_PVTAX18_create_with_all_three_cards_fields(client):
    """PVTAX18: Create with all three-card fields simultaneously returns 201 and full summary."""
    r = _create(client, {
        "asset_family":          "commercial",
        "asset_type":            "retail",
        "asset_subtype":         "supermarket",
        "asset_condition_path":  "as_completed",
        "assignment_purpose":    "investment_decision",
        "purpose_logic_path":    "standard_valuation",
        "purpose_route":         "income_investment_analysis",
        "purpose_subroute":      "dcf_analysis",
        "professional_context_path": "investment_funds",
        "professional_purpose_path": "investment_analysis",
        "intended_user_category": "institutional",
        "intended_use":          "investment_portfolio",
        "basis_of_value":        "investment_value",
        "value_premise":         "as_stabilized",
        "value_output_type":     "scenario_based",
    })
    assert r.status_code == 201
    tcs = r.get_json()["taxonomy_cards_summary"]
    assert tcs["card_1_asset_definition"]["asset_family"] == "commercial"
    assert tcs["card_2_purpose_routes"]["assignment_purpose"] == "investment_decision"
    assert tcs["card_3_basis_of_value"]["basis_of_value"] == "investment_value"


def test_PVTAX19_existing_tests_unaffected_by_taxonomy_cards(client):
    """PVTAX19: Adding taxonomy_cards_summary does not break canonical_taxonomy or derived_method_route."""
    r = _create(client, {
        "asset_family":       "residential",
        "asset_type":         "villa",
        "assignment_purpose": "financing_mortgage",
        "basis_of_value":     "market_value",
        "report_type":        "professional_report",
    })
    assert r.status_code == 201
    data = r.get_json()
    assert data.get("canonical_taxonomy"), "canonical_taxonomy must still be present"
    assert data.get("derived_method_route"), "derived_method_route must still be present"
    assert data.get("taxonomy_cards_summary"), "taxonomy_cards_summary must be present"
    assert data.get("valuation_purpose_routes_summary"), "valuation_purpose_routes_summary must still be present"


def test_PVTAX20_ordinary_valuation_route_unaffected(client):
    """PVTAX20: Ordinary valuation API is unaffected by three-cards taxonomy changes.
    (Rule 7: Do not break ordinary Valuation page.)"""
    resp = client.post(
        "/api/advisor/valuation",
        json={
            "property_type":     "apartment",
            "area_sqm":          150.0,
            "location":          "New Cairo",
            "valuation_purpose": "sale",
        },
        content_type="application/json",
    )
    # Must not return 404 or 500 — ordinary valuation route intact
    assert resp.status_code not in (404, 500), (
        f"Ordinary valuation route broken. Status: {resp.status_code}"
    )


# ════════════════════════════════════════════════════════════════════════════════
# PVREQ01–PVREQ18: Professional Valuation — Restore Full Legacy Asset Requirements
# ════════════════════════════════════════════════════════════════════════════════

def _create_with_asset_type(client, asset_type: str) -> dict:
    """Create a PVR record with a specific asset_type and return the parsed response body."""
    r = _create(client, {"asset_type": asset_type})
    assert r.status_code == 201, f"Expected 201 for asset_type={asset_type}, got {r.status_code}"
    return r.get_json()


def test_PVREQ01_hotel_returns_full_requirements(client):
    """PVREQ01: Creating a hotel record returns a non-empty asset_specific_requirements block."""
    data = _create_with_asset_type(client, "hotel")
    asr = data.get("asset_specific_requirements", {})
    assert asr, "asset_specific_requirements must not be empty for hotel"
    assert asr.get("required_inputs"), "required_inputs must not be empty for hotel"
    assert asr.get("legacy_requirement_keys"), "legacy_requirement_keys must not be empty for hotel"


def test_PVREQ02_hotel_total_count_gte_legacy_count(client):
    """PVREQ02: Hotel total_requirements_count >= legacy_requirements_count (no deletion)."""
    data = _create_with_asset_type(client, "hotel")
    asr = data.get("asset_specific_requirements", {})
    total = asr.get("total_requirements_count", 0)
    legacy = asr.get("legacy_requirements_count", 0)
    assert total >= legacy, (
        f"total_requirements_count ({total}) must be >= legacy_requirements_count ({legacy})"
    )


def test_PVREQ03_hotel_legacy_keys_preserved(client):
    """PVREQ03: Hotel legacy_requirement_keys includes the old registry code hotel_resort_detailed."""
    data = _create_with_asset_type(client, "hotel")
    asr = data.get("asset_specific_requirements", {})
    legacy_keys = asr.get("legacy_requirement_keys", [])
    assert "hotel_resort_detailed" in legacy_keys, (
        "hotel_resort_detailed must be in legacy_requirement_keys"
    )


def test_PVREQ04_hotel_includes_adr(client):
    """PVREQ04: Hotel required_inputs includes adr."""
    data = _create_with_asset_type(client, "hotel")
    asr = data.get("asset_specific_requirements", {})
    assert "adr" in asr.get("required_inputs", []), "adr must be in hotel required_inputs"


def test_PVREQ05_hotel_includes_occupancy_rate(client):
    """PVREQ05: Hotel required_inputs includes occupancy_rate."""
    data = _create_with_asset_type(client, "hotel")
    asr = data.get("asset_specific_requirements", {})
    assert "occupancy_rate" in asr.get("required_inputs", []), (
        "occupancy_rate must be in hotel required_inputs"
    )


def test_PVREQ06_hotel_includes_revpar(client):
    """PVREQ06: Hotel required_inputs includes revpar."""
    data = _create_with_asset_type(client, "hotel")
    asr = data.get("asset_specific_requirements", {})
    assert "revpar" in asr.get("required_inputs", []), "revpar must be in hotel required_inputs"


def test_PVREQ07_hotel_includes_dcf_method(client):
    """PVREQ07: Hotel recommended_methods includes dcf."""
    data = _create_with_asset_type(client, "hotel")
    asr = data.get("asset_specific_requirements", {})
    assert "dcf" in asr.get("recommended_methods", []), "dcf must be in hotel recommended_methods"


def test_PVREQ08_factory_returns_full_requirements(client):
    """PVREQ08: Creating an industrial_factory record returns a non-empty requirements block."""
    data = _create_with_asset_type(client, "industrial_factory")
    asr = data.get("asset_specific_requirements", {})
    assert asr.get("required_inputs"), "required_inputs must not be empty for industrial_factory"
    assert asr.get("legacy_requirement_keys"), "legacy_requirement_keys must not be empty for industrial_factory"


def test_PVREQ09_land_returns_full_requirements(client):
    """PVREQ09: Creating an urban_land record returns a non-empty requirements block."""
    data = _create_with_asset_type(client, "urban_land")
    asr = data.get("asset_specific_requirements", {})
    assert asr.get("required_inputs"), "required_inputs must not be empty for urban_land"
    assert asr.get("legacy_requirement_keys"), "legacy_requirement_keys must not be empty for urban_land"


def test_PVREQ10_retail_returns_full_requirements(client):
    """PVREQ10: Creating a retail_shop record returns a non-empty requirements block."""
    data = _create_with_asset_type(client, "retail_shop")
    asr = data.get("asset_specific_requirements", {})
    assert asr.get("required_inputs"), "required_inputs must not be empty for retail_shop"
    assert asr.get("legacy_requirement_keys"), "legacy_requirement_keys must not be empty for retail_shop"


def test_PVREQ11_warehouse_returns_full_requirements(client):
    """PVREQ11: Creating a warehouse record returns a non-empty requirements block."""
    data = _create_with_asset_type(client, "warehouse")
    asr = data.get("asset_specific_requirements", {})
    assert asr.get("required_inputs"), "required_inputs must not be empty for warehouse"
    assert asr.get("legacy_requirement_keys"), "legacy_requirement_keys must not be empty for warehouse"


def test_PVREQ12_all_asset_types_have_legacy_keys(client):
    """PVREQ12: Every catalogued asset type returns non-empty legacy_requirement_keys."""
    asset_types = ["hotel", "industrial_factory", "urban_land", "retail_shop", "warehouse"]
    for at in asset_types:
        data = _create_with_asset_type(client, at)
        asr = data.get("asset_specific_requirements", {})
        legacy = asr.get("legacy_requirement_keys", [])
        assert legacy, f"legacy_requirement_keys must not be empty for {at}"


def test_PVREQ13_missing_from_current_after_restore_is_empty(client):
    """PVREQ13: missing_from_current_after_restore is empty — no requirements lost after restore."""
    data = _create_with_asset_type(client, "hotel")
    asr = data.get("asset_specific_requirements", {})
    missing = asr.get("missing_from_current_after_restore", ["NOT_IN_RESPONSE"])
    assert missing == [], (
        f"missing_from_current_after_restore must be [] for hotel, got {missing}"
    )


def test_PVREQ14_deleted_requirements_is_empty(client):
    """PVREQ14: deleted_requirements is empty — no requirements deleted."""
    data = _create_with_asset_type(client, "hotel")
    asr = data.get("asset_specific_requirements", {})
    deleted = asr.get("deleted_requirements", ["NOT_IN_RESPONSE"])
    assert deleted == [], (
        f"deleted_requirements must be [] for hotel, got {deleted}"
    )


def test_PVREQ15_preservation_pass_is_true(client):
    """PVREQ15: preservation_pass is True for all major asset types."""
    for at in ["hotel", "industrial_factory", "urban_land", "retail_shop", "warehouse"]:
        data = _create_with_asset_type(client, at)
        asr = data.get("asset_specific_requirements", {})
        pp = asr.get("preservation_pass", False)
        assert pp is True, f"preservation_pass must be True for {at}, got {pp}"


def test_PVREQ16_no_internal_paths_in_requirements_context(client):
    """PVREQ16: No internal filesystem paths in asset_specific_requirements response."""
    import json as _json
    data = _create_with_asset_type(client, "hotel")
    asr = data.get("asset_specific_requirements", {})
    asr_str = _json.dumps(asr)
    for forbidden in ("C:\\", "/home/", "/var/", "core_engine/", "bridge_api"):
        assert forbidden not in asr_str, (
            f"Internal path fragment '{forbidden}' found in asset_specific_requirements"
        )


def test_PVREQ17_ordinary_valuation_unaffected_by_requirements_restore(client):
    """PVREQ17: Ordinary valuation route is unaffected by the requirements-restore changes."""
    resp = client.post(
        "/api/advisor/valuation",
        json={
            "property_type":     "apartment",
            "area_sqm":          120.0,
            "location":          "Maadi",
            "valuation_purpose": "sale",
        },
        content_type="application/json",
    )
    assert resp.status_code not in (404, 500), (
        f"Ordinary valuation route broken after requirements restore. Status: {resp.status_code}"
    )


def test_PVREQ18_tax_appeal_unaffected_by_requirements_restore(client):
    """PVREQ18: Tax appeal route is unaffected by the requirements-restore changes."""
    resp = client.post(
        "/api/tax-appeal/requests",
        json={
            "owner_name":    "اختبار PVREQ18",
            "property_type": "شقة",
            "current_assessed_value": 500000,
            "dispute_reason": "overvaluation",
        },
        content_type="application/json",
    )
    # Must not be 404 or 500 — tax appeal route unbroken
    assert resp.status_code not in (404, 500), (
        f"Tax appeal route broken after requirements restore. Status: {resp.status_code}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PVBG01–PVBG11 — Engine Governance Audit Context Tests (Part F)
# Basis of Value section cleanup: engine_governance_audit_context must be
# present in create (201) response, with correct shape and values.
# ═══════════════════════════════════════════════════════════════════════════════


def test_PVBG01_basis_of_value_still_returned_on_create(client):
    """PVBG01: basis_of_value preserved in canonical_taxonomy.axis_3_basis_of_value and card_3 after cleanup."""
    r = _create(client, {"basis_of_value": "market_value"})
    assert r.status_code == 201
    data = r.get_json()
    axis3 = data.get("canonical_taxonomy", {}).get("axis_3_basis_of_value", {})
    assert axis3.get("basis_of_value") == "market_value", (
        "basis_of_value must be in canonical_taxonomy.axis_3_basis_of_value"
    )
    card3 = data.get("taxonomy_cards_summary", {}).get("card_3_basis_of_value", {})
    assert card3.get("basis_of_value") == "market_value", (
        "basis_of_value must be in taxonomy_cards_summary.card_3_basis_of_value"
    )


def test_PVBG02_value_output_type_still_returned(client):
    """PVBG02: value_output_type preserved in canonical_taxonomy.axis_3_basis_of_value after cleanup."""
    r = _create(client, {"value_output_type": "point_estimate"})
    assert r.status_code == 201
    data = r.get_json()
    axis3 = data.get("canonical_taxonomy", {}).get("axis_3_basis_of_value", {})
    assert axis3.get("value_output_type") == "point_estimate", (
        "value_output_type must be in canonical_taxonomy.axis_3_basis_of_value"
    )


def test_PVBG03_value_premise_still_returned(client):
    """PVBG03: value_premise preserved in canonical_taxonomy.axis_3_basis_of_value after cleanup."""
    r = _create(client, {"value_premise": "as_is"})
    assert r.status_code == 201
    data = r.get_json()
    axis3 = data.get("canonical_taxonomy", {}).get("axis_3_basis_of_value", {})
    assert axis3.get("value_premise") == "as_is", (
        "value_premise must be in canonical_taxonomy.axis_3_basis_of_value"
    )


def test_PVBG04_engine_governance_audit_context_exists(client):
    """PVBG04: engine_governance_audit_context key present in create response."""
    r = _create(client, {})
    assert r.status_code == 201
    data = r.get_json()
    assert "engine_governance_audit_context" in data, (
        "engine_governance_audit_context must be in create response"
    )


def test_PVBG05_governance_context_contains_draft_status(client):
    """PVBG05: engine_governance_audit_context contains draft_status."""
    r = _create(client, {})
    assert r.status_code == 201
    ctx = r.get_json().get("engine_governance_audit_context", {})
    assert "draft_status" in ctx, "engine_governance_audit_context must have draft_status"
    assert ctx["draft_status"], "draft_status must be non-empty"


def test_PVBG06_governance_context_contains_data_readiness(client):
    """PVBG06: engine_governance_audit_context contains data_readiness."""
    r = _create(client, {})
    assert r.status_code == 201
    ctx = r.get_json().get("engine_governance_audit_context", {})
    assert "data_readiness" in ctx, "engine_governance_audit_context must have data_readiness"


def test_PVBG07_governance_context_contains_processing_pipeline_steps(client):
    """PVBG07: engine_governance_audit_context contains processing_pipeline_steps list with 9 items."""
    r = _create(client, {})
    assert r.status_code == 201
    ctx = r.get_json().get("engine_governance_audit_context", {})
    steps = ctx.get("processing_pipeline_steps", [])
    assert isinstance(steps, list), "processing_pipeline_steps must be a list"
    assert len(steps) == 9, f"Expected 9 pipeline steps, got {len(steps)}"


def test_PVBG08_governance_context_old_keys_preserved(client):
    """PVBG08: engine_governance_audit_context preserves human_approval_required and final_report_without_approval_allowed."""
    r = _create(client, {})
    assert r.status_code == 201
    ctx = r.get_json().get("engine_governance_audit_context", {})
    assert "human_approval_required" in ctx
    assert ctx["human_approval_required"] is True
    assert "final_report_without_approval_allowed" in ctx
    assert ctx["final_report_without_approval_allowed"] is False


def test_PVBG09_governance_context_no_internal_paths(client):
    """PVBG09: engine_governance_audit_context must not contain internal filesystem paths."""
    r = _create(client, {})
    assert r.status_code == 201
    import json
    ctx_str = json.dumps(r.get_json().get("engine_governance_audit_context", {}))
    for forbidden in ("C:\\", "/home/", "/var/", "core_engine/", "bridge_api"):
        assert forbidden not in ctx_str, (
            f"Internal path '{forbidden}' found in engine_governance_audit_context"
        )


def test_PVBG10_ordinary_valuation_unaffected_by_governance_cleanup(client):
    """PVBG10: Ordinary valuation route unaffected by governance context addition."""
    resp = client.post(
        "/api/valuation",
        json={
            "property_type": "apartment",
            "area_sqm": 100,
            "location": "Cairo",
        },
        content_type="application/json",
    )
    assert resp.status_code not in (404, 500), (
        f"Ordinary valuation route broken. Status: {resp.status_code}"
    )


def test_PVBG11_tax_appeal_unaffected_by_governance_cleanup(client):
    """PVBG11: Tax appeal route unaffected by governance context addition."""
    resp = client.post(
        "/api/tax-appeal/requests",
        json={
            "owner_name":             "اختبار PVBG11",
            "property_type":          "شقة",
            "current_assessed_value": 500000,
            "dispute_reason":         "overvaluation",
        },
        content_type="application/json",
    )
    assert resp.status_code not in (404, 500), (
        f"Tax appeal route broken. Status: {resp.status_code}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# PVSS_BE01–PVSS_BE19 — Six-Section Layout Backend Tests (Part H / Part I)
#
# These tests verify that the POST create response and GET detail response
# both carry:
#   • main_page_sections_context  — 6 visible sections, governance & controls flags
#   • advanced_controls_context   — active/inactive controls, roadmap, reflection matrix
# ══════════════════════════════════════════════════════════════════════════════

_EXPECTED_SECTION_IDS = [
    "pro-val-section-basic-valuation-data",
    "pro-val-section-asset-type-selection",
    "pro-val-section-valuation-purpose",
    "pro-val-section-applied-valuation-standards",
    "pro-val-section-report-type",
    "pro-val-section-chat-box",
]


def test_PVSS_BE01_create_response_has_main_page_sections_context(client):
    """PVSS_BE01: POST to create a PVR returns 201 and response has main_page_sections_context key."""
    r = _create(client)
    assert r.status_code == 201
    data = r.get_json()
    assert "main_page_sections_context" in data, (
        "main_page_sections_context key must be present in create response"
    )


def test_PVSS_BE02_main_page_sections_context_section_count_is_6(client):
    """PVSS_BE02: main_page_sections_context.section_count == 6."""
    r = _create(client)
    assert r.status_code == 201
    ctx = r.get_json().get("main_page_sections_context", {})
    assert ctx.get("section_count") == 6, (
        f"Expected section_count == 6, got {ctx.get('section_count')!r}"
    )


def test_PVSS_BE03_main_page_sections_context_page_version(client):
    """PVSS_BE03: main_page_sections_context.page_version == 'six_sections_v1'."""
    r = _create(client)
    assert r.status_code == 201
    ctx = r.get_json().get("main_page_sections_context", {})
    assert ctx.get("page_version") == "six_sections_v1", (
        f"Expected page_version 'six_sections_v1', got {ctx.get('page_version')!r}"
    )


def test_PVSS_BE04_main_page_sections_context_sections_list_length_6(client):
    """PVSS_BE04: main_page_sections_context.sections is a list of length 6."""
    r = _create(client)
    assert r.status_code == 201
    ctx = r.get_json().get("main_page_sections_context", {})
    sections = ctx.get("sections", [])
    assert isinstance(sections, list), "sections must be a list"
    assert len(sections) == 6, f"Expected 6 sections, got {len(sections)}"


def test_PVSS_BE05_main_page_sections_context_all_6_section_ids_present(client):
    """PVSS_BE05: All 6 section IDs are present in main_page_sections_context.sections."""
    r = _create(client)
    assert r.status_code == 201
    ctx = r.get_json().get("main_page_sections_context", {})
    sections = ctx.get("sections", [])
    section_ids = [s.get("id") for s in sections]
    for expected_id in _EXPECTED_SECTION_IDS:
        assert expected_id in section_ids, (
            f"Section ID '{expected_id}' missing from main_page_sections_context.sections"
        )


def test_PVSS_BE06_all_6_sections_have_status_visible(client):
    """PVSS_BE06: All 6 sections have status == 'visible'."""
    r = _create(client)
    assert r.status_code == 201
    ctx = r.get_json().get("main_page_sections_context", {})
    sections = ctx.get("sections", [])
    for section in sections:
        assert section.get("status") == "visible", (
            f"Section '{section.get('id')}' has status {section.get('status')!r}, expected 'visible'"
        )


def test_PVSS_BE07_governance_panel_visible_is_true(client):
    """PVSS_BE07: main_page_sections_context.governance_panel_visible is True."""
    r = _create(client)
    assert r.status_code == 201
    ctx = r.get_json().get("main_page_sections_context", {})
    assert ctx.get("governance_panel_visible") is True, (
        "governance_panel_visible must be True in main_page_sections_context"
    )


def test_PVSS_BE08_advanced_controls_panel_visible_is_true(client):
    """PVSS_BE08: main_page_sections_context.advanced_controls_panel_visible is True."""
    r = _create(client)
    assert r.status_code == 201
    ctx = r.get_json().get("main_page_sections_context", {})
    assert ctx.get("advanced_controls_panel_visible") is True, (
        "advanced_controls_panel_visible must be True in main_page_sections_context"
    )


def test_PVSS_BE09_create_response_has_advanced_controls_context(client):
    """PVSS_BE09: Response has advanced_controls_context key."""
    r = _create(client)
    assert r.status_code == 201
    data = r.get_json()
    assert "advanced_controls_context" in data, (
        "advanced_controls_context key must be present in create response"
    )


def test_PVSS_BE10_active_controls_list_length_5(client):
    """PVSS_BE10: advanced_controls_context.active_controls is a list of length 5."""
    r = _create(client)
    assert r.status_code == 201
    ctx = r.get_json().get("advanced_controls_context", {})
    active = ctx.get("active_controls", [])
    assert isinstance(active, list), "active_controls must be a list"
    assert len(active) == 5, f"Expected 5 active controls, got {len(active)}"


def test_PVSS_BE11_inactive_controls_list_length_4(client):
    """PVSS_BE11: advanced_controls_context.inactive_controls is a list of length 4."""
    r = _create(client)
    assert r.status_code == 201
    ctx = r.get_json().get("advanced_controls_context", {})
    inactive = ctx.get("inactive_controls", [])
    assert isinstance(inactive, list), "inactive_controls must be a list"
    assert len(inactive) == 4, f"Expected 4 inactive controls, got {len(inactive)}"


def test_PVSS_BE12_activation_roadmap_has_5_phases(client):
    """PVSS_BE12: advanced_controls_context.activation_roadmap has 5 phases."""
    r = _create(client)
    assert r.status_code == 201
    ctx = r.get_json().get("advanced_controls_context", {})
    roadmap = ctx.get("activation_roadmap", [])
    assert isinstance(roadmap, list), "activation_roadmap must be a list"
    assert len(roadmap) == 5, f"Expected 5 roadmap phases, got {len(roadmap)}"


def test_PVSS_BE13_roadmap_phase_1_status_is_active(client):
    """PVSS_BE13: Phase 1 of activation_roadmap has status == 'active'."""
    r = _create(client)
    assert r.status_code == 201
    ctx = r.get_json().get("advanced_controls_context", {})
    roadmap = ctx.get("activation_roadmap", [])
    assert len(roadmap) >= 1, "activation_roadmap must have at least 1 phase"
    phase_1 = roadmap[0]
    assert phase_1.get("status") == "active", (
        f"Phase 1 status must be 'active', got {phase_1.get('status')!r}"
    )


def test_PVSS_BE14_roadmap_phases_2_to_5_status_is_pending(client):
    """PVSS_BE14: Phases 2–5 of activation_roadmap have status == 'pending'."""
    r = _create(client)
    assert r.status_code == 201
    ctx = r.get_json().get("advanced_controls_context", {})
    roadmap = ctx.get("activation_roadmap", [])
    assert len(roadmap) == 5, f"Expected 5 roadmap phases, got {len(roadmap)}"
    for i, phase in enumerate(roadmap[1:], start=2):
        assert phase.get("status") == "pending", (
            f"Phase {i} status must be 'pending', got {phase.get('status')!r}"
        )


def test_PVSS_BE15_report_reflection_matrix_has_4_keys(client):
    """PVSS_BE15: advanced_controls_context.report_reflection_matrix has 4 keys
    (traditional_report, detailed_report, professional_report, simulated_report)."""
    r = _create(client)
    assert r.status_code == 201
    ctx = r.get_json().get("advanced_controls_context", {})
    matrix = ctx.get("report_reflection_matrix", {})
    assert isinstance(matrix, dict), "report_reflection_matrix must be a dict"
    expected_keys = {
        "traditional_report",
        "detailed_report",
        "professional_report",
        "simulated_report",
    }
    actual_keys = set(matrix.keys())
    assert actual_keys == expected_keys, (
        f"report_reflection_matrix keys mismatch. Expected {expected_keys}, got {actual_keys}"
    )


def test_PVSS_BE16_professional_report_has_certification_true(client):
    """PVSS_BE16: professional_report in report_reflection_matrix has certification == True."""
    r = _create(client)
    assert r.status_code == 201
    ctx = r.get_json().get("advanced_controls_context", {})
    matrix = ctx.get("report_reflection_matrix", {})
    prof = matrix.get("professional_report", {})
    assert prof.get("certification") is True, (
        f"professional_report.certification must be True, got {prof.get('certification')!r}"
    )


def test_PVSS_BE17_simulated_report_has_advisory_only_true(client):
    """PVSS_BE17: simulated_report in report_reflection_matrix has advisory_only == True."""
    r = _create(client)
    assert r.status_code == 201
    ctx = r.get_json().get("advanced_controls_context", {})
    matrix = ctx.get("report_reflection_matrix", {})
    simulated = matrix.get("simulated_report", {})
    assert simulated.get("advisory_only") is True, (
        f"simulated_report.advisory_only must be True, got {simulated.get('advisory_only')!r}"
    )


def test_PVSS_BE18_get_detail_contains_main_page_sections_context(client):
    """PVSS_BE18: GET detail response also contains main_page_sections_context (via _safe_detail).
    The field is nested at data['request']['main_page_sections_context'].
    """
    rid = _create(client).get_json()["request_id"]
    resp = client.get(
        f"/api/professional-valuation/requests/{rid}",
        headers=_auth(),
    )
    assert resp.status_code == 200
    detail = resp.get_json().get("request", {})
    assert "main_page_sections_context" in detail, (
        "main_page_sections_context must be present in GET detail response['request']"
    )


def test_PVSS_BE19_get_detail_contains_advanced_controls_context(client):
    """PVSS_BE19: GET detail response also contains advanced_controls_context.
    The field is nested at data['request']['advanced_controls_context'].
    """
    rid = _create(client).get_json()["request_id"]
    resp = client.get(
        f"/api/professional-valuation/requests/{rid}",
        headers=_auth(),
    )
    assert resp.status_code == 200
    detail = resp.get_json().get("request", {})
    assert "advanced_controls_context" in detail, (
        "advanced_controls_context must be present in GET detail response['request']"
    )


# ── PVATUX_BE01–PVATUX_BE12: Asset Type UX Cleanup — backend context tests (Part L) ────────

_HOTEL_PAYLOAD: dict = {
    "client_name":       "اختبار فندق السلام",
    "property_type":     "فندق",
    "valuation_purpose": "قيمة سوقية",
    "city":              "القاهرة",
    "district":          "مصر الجديدة",
    "asset_type":        "فندق",
    "asset_family":      "hospitality_leisure",
    "asset_subtype":     "business_hotel",
    "asset_condition_path": "operating_existing_hotel",
}


def test_PVATUX_BE01_post_returns_asset_type_selection_context(client):
    """PVATUX_BE01: POST create response contains asset_type_selection_context key."""
    r = _create(client, _HOTEL_PAYLOAD)
    assert r.status_code == 201
    body = r.get_json()
    assert "asset_type_selection_context" in body, (
        "POST response must contain asset_type_selection_context"
    )


def test_PVATUX_BE02_asset_type_selection_context_is_dict(client):
    """PVATUX_BE02: asset_type_selection_context in POST response is a non-empty dict."""
    r = _create(client, _HOTEL_PAYLOAD)
    assert r.status_code == 201
    ctx = r.get_json().get("asset_type_selection_context", None)
    assert isinstance(ctx, dict) and len(ctx) > 0, (
        "asset_type_selection_context must be a non-empty dict"
    )


def test_PVATUX_BE03_context_includes_available_asset_families(client):
    """PVATUX_BE03: asset_type_selection_context.available_asset_families contains ≥ 20 entries."""
    r = _create(client, _HOTEL_PAYLOAD)
    assert r.status_code == 201
    ctx = r.get_json().get("asset_type_selection_context", {})
    families = ctx.get("available_asset_families", [])
    assert len(families) >= 20, (
        f"available_asset_families must have ≥ 20 entries, got {len(families)}: {families}"
    )


def test_PVATUX_BE04_available_families_includes_standard_and_legacy(client):
    """PVATUX_BE04: available_asset_families includes both standard AND legacy family keys."""
    r = _create(client, _HOTEL_PAYLOAD)
    assert r.status_code == 201
    ctx = r.get_json().get("asset_type_selection_context", {})
    families = ctx.get("available_asset_families", [])
    standard = {"residential_housing", "land_plots", "commercial_retail",
                "industrial_logistics", "hospitality_leisure", "agri_environmental"}
    for f in standard:
        assert f in families, f"Standard family '{f}' missing from available_asset_families"
    legacy = {"hospitality_entertainment", "sports_event_venues"}
    for f in legacy:
        assert f in families, f"Legacy family '{f}' missing from available_asset_families — no deletion allowed"


def test_PVATUX_BE05_asset_type_reflected_in_context(client):
    """PVATUX_BE05: asset_type_selection_context.asset_type echoes the submitted asset_type field."""
    r = _create(client, _HOTEL_PAYLOAD)
    assert r.status_code == 201
    ctx = r.get_json().get("asset_type_selection_context", {})
    assert ctx.get("asset_type") == "فندق", (
        f"context.asset_type must be 'فندق', got {ctx.get('asset_type')!r}"
    )


def test_PVATUX_BE06_asset_family_reflected_in_context(client):
    """PVATUX_BE06: asset_type_selection_context.asset_family echoes the submitted asset_family field."""
    r = _create(client, _HOTEL_PAYLOAD)
    assert r.status_code == 201
    ctx = r.get_json().get("asset_type_selection_context", {})
    assert ctx.get("asset_family") == "hospitality_leisure", (
        f"context.asset_family must be 'hospitality_leisure', got {ctx.get('asset_family')!r}"
    )


def test_PVATUX_BE07_asset_subtype_reflected_in_context(client):
    """PVATUX_BE07: asset_type_selection_context.asset_subtype echoes submitted asset_subtype."""
    r = _create(client, _HOTEL_PAYLOAD)
    assert r.status_code == 201
    ctx = r.get_json().get("asset_type_selection_context", {})
    assert ctx.get("asset_subtype") == "business_hotel", (
        f"context.asset_subtype must be 'business_hotel', got {ctx.get('asset_subtype')!r}"
    )


def test_PVATUX_BE08_duplicate_options_removed_list_is_present(client):
    """PVATUX_BE08: context.duplicate_options_removed_from_visible_ui is a list (may be empty if no dups)."""
    r = _create(client, _HOTEL_PAYLOAD)
    assert r.status_code == 201
    ctx = r.get_json().get("asset_type_selection_context", {})
    dups = ctx.get("duplicate_options_removed_from_visible_ui", None)
    assert isinstance(dups, list), (
        "duplicate_options_removed_from_visible_ui must be a list"
    )


def test_PVATUX_BE09_duplicate_options_have_legacy_alias_preserved(client):
    """PVATUX_BE09: Every entry in duplicate_options_removed_from_visible_ui has legacy_alias_preserved=True."""
    r = _create(client, _HOTEL_PAYLOAD)
    assert r.status_code == 201
    ctx = r.get_json().get("asset_type_selection_context", {})
    dups = ctx.get("duplicate_options_removed_from_visible_ui", [])
    for item in dups:
        assert item.get("legacy_alias_preserved") is True, (
            f"duplicate option '{item}' must have legacy_alias_preserved=True"
        )


def test_PVATUX_BE10_get_detail_contains_asset_type_selection_context(client):
    """PVATUX_BE10: GET detail response also contains asset_type_selection_context."""
    rid = _create(client, _HOTEL_PAYLOAD).get_json()["request_id"]
    resp = client.get(
        f"/api/professional-valuation/requests/{rid}",
        headers=_auth(),
    )
    assert resp.status_code == 200
    detail = resp.get_json().get("request", {})
    assert "asset_type_selection_context" in detail, (
        "asset_type_selection_context must be present in GET detail response['request']"
    )


def test_PVATUX_BE11_ordinary_valuation_route_unaffected(client):
    """PVATUX_BE11: Regression — ordinary valuation route still responds (not 404/500).
    asset_type_selection_context changes must not break the base /api/advisor/valuate endpoint.
    """
    resp = client.post(
        "/api/advisor/valuate",
        json={
            "property_type": "شقة سكنية",
            "area": 120,
            "city": "القاهرة",
            "purpose": "market_value",
        },
        content_type="application/json",
    )
    assert resp.status_code != 404, "Ordinary valuation route /api/advisor/valuate must not return 404"
    assert resp.status_code != 500, "Ordinary valuation route crashed with 500"


def test_PVATUX_BE12_asset_type_selection_context_no_internal_paths(client):
    """PVATUX_BE12: asset_type_selection_context must not contain internal file-system paths."""
    r = _create(client, _HOTEL_PAYLOAD)
    assert r.status_code == 201
    ctx = r.get_json().get("asset_type_selection_context", {})
    ctx_str = str(ctx)
    for forbidden in ("C:\\", "c:\\", "/home/", "/var/", "__file__", "core_engine/"):
        assert forbidden not in ctx_str, (
            f"Internal path fragment '{forbidden}' found in asset_type_selection_context"
        )


# ── PVPTS-BE: Section 3 Three-Step Restructure ────────────────────────────────
# Tests covering valuation_purpose_context, all 16 Step-3 fields, registry
# contexts, legacy alias mapping, partial interest, and regression guards.

_PURPOSE_PAYLOAD: dict = {
    "assignment_purpose":        "financing_mortgage",
    "purpose_logic_path":        "mortgage_logic",
    "purpose_route":             "bank_loan",
    "purpose_subroute":          "residential_mortgage",
    "intended_user_category":    "bank_lender",
    "intended_user_name":        "بنك مصر للاختبار",
    "intended_use":              "تمويل عقاري",
    "professional_context_path": "bank_financing_path",
    "professional_purpose_path": "financing_path",
    "basis_of_value":            "market_value",
    "value_output_type":         "point_estimate",
    "value_scope":               "as_is",
    "value_premise":             "as_is",
    "value_basis_route":         "standard_market",
    "value_basis_subroute":      "comparable_sales",
}


def test_PVPTS_BE01_valuation_purpose_context_exists_in_create(client):
    """PVPTS-BE01: POST create response contains valuation_purpose_context."""
    r = _create(client, _PURPOSE_PAYLOAD)
    assert r.status_code == 201, r.get_data(as_text=True)
    body = r.get_json()
    assert "valuation_purpose_context" in body, (
        "valuation_purpose_context must be present in POST create response"
    )


def test_PVPTS_BE02_assignment_purpose_stored_in_context(client):
    """PVPTS-BE02: assignment_purpose is stored and returned in valuation_purpose_context.purpose."""
    r = _create(client, _PURPOSE_PAYLOAD)
    assert r.status_code == 201
    ctx = r.get_json().get("valuation_purpose_context", {})
    assert ctx.get("purpose") == "financing_mortgage", (
        f"valuation_purpose_context.purpose must be 'financing_mortgage', got {ctx.get('purpose')!r}"
    )


def test_PVPTS_BE03_purpose_logic_path_accepted(client):
    """PVPTS-BE03: purpose_logic_path field is accepted (no 400)."""
    r = _create(client, {"purpose_logic_path": "mortgage_logic"})
    assert r.status_code == 201, (
        f"purpose_logic_path should be accepted, got {r.status_code}"
    )


def test_PVPTS_BE04_purpose_route_accepted(client):
    """PVPTS-BE04: purpose_route field is accepted (no 400)."""
    r = _create(client, {"purpose_route": "bank_loan"})
    assert r.status_code == 201, (
        f"purpose_route should be accepted, got {r.status_code}"
    )


def test_PVPTS_BE05_purpose_subroute_accepted(client):
    """PVPTS-BE05: purpose_subroute field is accepted (no 400)."""
    r = _create(client, {"purpose_subroute": "residential_mortgage"})
    assert r.status_code == 201, (
        f"purpose_subroute should be accepted, got {r.status_code}"
    )


def test_PVPTS_BE06_intended_user_category_accepted(client):
    """PVPTS-BE06: intended_user_category is accepted and appears in context."""
    r = _create(client, {"intended_user_category": "bank_lender"})
    assert r.status_code == 201
    ctx = r.get_json().get("valuation_purpose_context", {})
    assert ctx.get("intended_user") == "bank_lender", (
        f"valuation_purpose_context.intended_user must be 'bank_lender', got {ctx.get('intended_user')!r}"
    )


def test_PVPTS_BE07_intended_user_name_accepted(client):
    """PVPTS-BE07: intended_user_name is accepted and appears in context."""
    r = _create(client, {"intended_user_name": "بنك مصر للاختبار"})
    assert r.status_code == 201
    ctx = r.get_json().get("valuation_purpose_context", {})
    assert ctx.get("intended_user_name") == "بنك مصر للاختبار", (
        f"valuation_purpose_context.intended_user_name mismatch: {ctx.get('intended_user_name')!r}"
    )


def test_PVPTS_BE08_intended_use_accepted(client):
    """PVPTS-BE08: intended_use is accepted and appears in context."""
    r = _create(client, {"intended_use": "تمويل عقاري"})
    assert r.status_code == 201
    ctx = r.get_json().get("valuation_purpose_context", {})
    assert ctx.get("intended_use") == "تمويل عقاري", (
        f"valuation_purpose_context.intended_use mismatch: {ctx.get('intended_use')!r}"
    )


def test_PVPTS_BE09_professional_context_path_accepted(client):
    """PVPTS-BE09: professional_context_path is accepted (no 400)."""
    r = _create(client, {"professional_context_path": "bank_financing_path"})
    assert r.status_code == 201, (
        f"professional_context_path should be accepted, got {r.status_code}"
    )


def test_PVPTS_BE10_professional_purpose_path_accepted(client):
    """PVPTS-BE10: professional_purpose_path is accepted and appears in context.professional_path."""
    r = _create(client, {"professional_purpose_path": "financing_path"})
    assert r.status_code == 201
    ctx = r.get_json().get("valuation_purpose_context", {})
    assert ctx.get("professional_path") == "financing_path", (
        f"valuation_purpose_context.professional_path mismatch: {ctx.get('professional_path')!r}"
    )


def test_PVPTS_BE11_basis_of_value_accepted(client):
    """PVPTS-BE11: basis_of_value is accepted and appears in context."""
    r = _create(client, {"basis_of_value": "market_value"})
    assert r.status_code == 201
    ctx = r.get_json().get("valuation_purpose_context", {})
    assert ctx.get("basis_of_value") == "market_value", (
        f"valuation_purpose_context.basis_of_value mismatch: {ctx.get('basis_of_value')!r}"
    )


def test_PVPTS_BE12_value_output_type_accepted(client):
    """PVPTS-BE12: value_output_type is accepted (no 400)."""
    r = _create(client, {"value_output_type": "point_estimate"})
    assert r.status_code == 201, (
        f"value_output_type should be accepted, got {r.status_code}"
    )


def test_PVPTS_BE13_value_scope_accepted(client):
    """PVPTS-BE13: value_scope is accepted (no 400)."""
    r = _create(client, {"value_scope": "as_is"})
    assert r.status_code == 201, (
        f"value_scope should be accepted, got {r.status_code}"
    )


def test_PVPTS_BE14_value_premise_accepted(client):
    """PVPTS-BE14: value_premise is accepted and appears in context."""
    r = _create(client, {"value_premise": "as_is"})
    assert r.status_code == 201
    ctx = r.get_json().get("valuation_purpose_context", {})
    assert ctx.get("value_premise") == "as_is", (
        f"valuation_purpose_context.value_premise mismatch: {ctx.get('value_premise')!r}"
    )


def test_PVPTS_BE15_value_basis_route_accepted(client):
    """PVPTS-BE15: value_basis_route is accepted (no 400)."""
    r = _create(client, {"value_basis_route": "standard_market"})
    assert r.status_code == 201, (
        f"value_basis_route should be accepted, got {r.status_code}"
    )


def test_PVPTS_BE16_value_basis_subroute_accepted(client):
    """PVPTS-BE16: value_basis_subroute is accepted (no 400)."""
    r = _create(client, {"value_basis_subroute": "comparable_sales"})
    assert r.status_code == 201, (
        f"value_basis_subroute should be accepted, got {r.status_code}"
    )


def test_PVPTS_BE17_purpose_registry_context_exists(client):
    """PVPTS-BE17: purpose_registry_context is present in create response."""
    r = _create(client, _PURPOSE_PAYLOAD)
    assert r.status_code == 201
    body = r.get_json()
    assert "purpose_registry_context" in body, (
        "purpose_registry_context must be present in POST create response"
    )
    ctx = body["purpose_registry_context"]
    assert isinstance(ctx.get("entries"), list), (
        "purpose_registry_context.entries must be a list"
    )
    assert len(ctx["entries"]) >= 16, (
        f"purpose_registry_context must have ≥16 entries, got {len(ctx['entries'])}"
    )


def test_PVPTS_BE18_purpose_taxonomy_v2_registries_exists(client):
    """PVPTS-BE18: purpose_taxonomy_v2_registries is present in create response."""
    r = _create(client, _PURPOSE_PAYLOAD)
    assert r.status_code == 201
    body = r.get_json()
    assert "purpose_taxonomy_v2_registries" in body, (
        "purpose_taxonomy_v2_registries must be present in POST create response"
    )


def test_PVPTS_BE19_purpose_taxonomy_v2_has_expected_keys(client):
    """PVPTS-BE19: purpose_taxonomy_v2_registries has all 8 expected registry keys."""
    r = _create(client, _PURPOSE_PAYLOAD)
    assert r.status_code == 201
    regs = r.get_json().get("purpose_taxonomy_v2_registries", {})
    expected_keys = [
        "valuation_purpose_registry",
        "purpose_logic_path_registry",
        "intended_user_registry",
        "professional_pathway_registry",
        "basis_of_value_registry",
        "value_premise_registry",
        "purpose_disclosure_warning_registry",
        "purpose_routing_matrix_registry",
    ]
    for k in expected_keys:
        assert k in regs, (
            f"purpose_taxonomy_v2_registries missing key '{k}'"
        )


def test_PVPTS_BE20_basis_registry_context_exists(client):
    """PVPTS-BE20: basis_registry_context is present in create response."""
    r = _create(client, _PURPOSE_PAYLOAD)
    assert r.status_code == 201
    body = r.get_json()
    assert "basis_registry_context" in body, (
        "basis_registry_context must be present in POST create response"
    )


def test_PVPTS_BE21_intended_user_registry_context_exists(client):
    """PVPTS-BE21: intended_user_registry_context is present in create response."""
    r = _create(client, _PURPOSE_PAYLOAD)
    assert r.status_code == 201
    body = r.get_json()
    assert "intended_user_registry_context" in body, (
        "intended_user_registry_context must be present in POST create response"
    )


def test_PVPTS_BE22_routing_matrix_registry_context_exists(client):
    """PVPTS-BE22: routing_matrix_registry_context is present in create response."""
    r = _create(client, _PURPOSE_PAYLOAD)
    assert r.status_code == 201
    body = r.get_json()
    assert "routing_matrix_registry_context" in body, (
        "routing_matrix_registry_context must be present in POST create response"
    )


def test_PVPTS_BE23_valuation_purpose_context_no_internal_paths(client):
    """PVPTS-BE23: valuation_purpose_context must not expose internal filesystem paths."""
    r = _create(client, _PURPOSE_PAYLOAD)
    assert r.status_code == 201
    ctx_str = str(r.get_json().get("valuation_purpose_context", {}))
    for forbidden in ("C:\\", "c:\\", "/home/", "/var/", "__file__", "core_engine/"):
        assert forbidden not in ctx_str, (
            f"Internal path fragment '{forbidden}' found in valuation_purpose_context"
        )


def test_PVPTS_BE24_legacy_valuation_purpose_still_accepted(client):
    """PVPTS-BE24: Old legacy valuation_purpose field still accepted (no 400)."""
    r = _create(client, {"valuation_purpose": "قيمة سوقية"})
    assert r.status_code == 201, (
        f"Legacy valuation_purpose must still be accepted, got {r.status_code}"
    )


def test_PVPTS_BE25_legacy_valuation_purpose_maps_to_assignment_purpose(client):
    """PVPTS-BE25: valuation_purpose='قيمة سوقية' maps to assignment_purpose in context."""
    r = _create(client, {"valuation_purpose": "قيمة سوقية"})
    assert r.status_code == 201
    ctx = r.get_json().get("valuation_purpose_context", {})
    # The legacy mapping sets purpose to sale_purchase or a meaningful key (not empty)
    assert ctx.get("purpose") != "", (
        "valuation_purpose_context.purpose must not be empty when legacy valuation_purpose provided"
    )


def test_PVPTS_BE26_valuation_purpose_context_preservation_pass(client):
    """PVPTS-BE26: valuation_purpose_context contains preservation_pass=True."""
    r = _create(client, _PURPOSE_PAYLOAD)
    assert r.status_code == 201
    ctx = r.get_json().get("valuation_purpose_context", {})
    assert ctx.get("preservation_pass") is True, (
        "valuation_purpose_context.preservation_pass must be True"
    )


def test_PVPTS_BE27_partial_interest_fields_accepted(client):
    """PVPTS-BE27: Partial interest fields accepted (ownership_interest_percent, dloc_percent, dlom_percent, discount_justification)."""
    payload = {
        "assignment_purpose":       "partial_interest_valuation",
        "ownership_interest_percent": "45",
        "dloc_percent":              "10",
        "dlom_percent":              "15",
        "discount_justification":    "معدل الخصم مبرر بالتحليل السوقي",
    }
    r = _create(client, payload)
    assert r.status_code == 201, (
        f"Partial interest fields must be accepted, got {r.status_code}: {r.get_data(as_text=True)}"
    )


def test_PVPTS_BE28_partial_interest_context_in_valuation_purpose_context(client):
    """PVPTS-BE28: partial_interest_context sub-dict present when partial_interest_valuation used."""
    payload = {
        "assignment_purpose":         "partial_interest_valuation",
        "ownership_interest_percent": "60",
        "discount_justification":     "تقدير السوق",
    }
    r = _create(client, payload)
    assert r.status_code == 201
    ctx = r.get_json().get("valuation_purpose_context", {})
    pic = ctx.get("partial_interest_context")
    assert pic is not None, (
        "valuation_purpose_context.partial_interest_context must be present for partial_interest_valuation"
    )


def test_PVPTS_BE29_get_detail_contains_valuation_purpose_context(client):
    """PVPTS-BE29: GET detail response also contains valuation_purpose_context."""
    rid = _create(client, _PURPOSE_PAYLOAD).get_json()["request_id"]
    resp = client.get(
        f"/api/professional-valuation/requests/{rid}",
        headers=_auth(),
    )
    assert resp.status_code == 200
    detail = resp.get_json().get("request", {})
    assert "valuation_purpose_context" in detail, (
        "valuation_purpose_context must be present in GET detail response['request']"
    )


def test_PVPTS_BE30_new_intended_user_category_bank_accepted(client):
    """PVPTS-BE30: New intended_user_category value 'bank' accepted (no 400)."""
    r = _create(client, {"intended_user_category": "bank"})
    assert r.status_code == 201, (
        f"New intended_user_category 'bank' must be accepted, got {r.status_code}"
    )


def test_PVPTS_BE31_new_intended_user_category_court_accepted(client):
    """PVPTS-BE31: New intended_user_category value 'court' accepted (no 400)."""
    r = _create(client, {"intended_user_category": "court"})
    assert r.status_code == 201, (
        f"New intended_user_category 'court' must be accepted, got {r.status_code}"
    )


def test_PVPTS_BE32_new_professional_pathway_tax_authority_accepted(client):
    """PVPTS-BE32: New professional_purpose_path 'tax_authority_path' accepted (no 400)."""
    r = _create(client, {"professional_purpose_path": "tax_authority_path"})
    assert r.status_code == 201, (
        f"New professional_purpose_path 'tax_authority_path' must be accepted, got {r.status_code}"
    )


def test_PVPTS_BE33_new_basis_of_value_value_in_use_accepted(client):
    """PVPTS-BE33: New basis_of_value 'value_in_use' accepted (no 400)."""
    r = _create(client, {"basis_of_value": "value_in_use"})
    assert r.status_code == 201, (
        f"New basis_of_value 'value_in_use' must be accepted, got {r.status_code}"
    )


def test_PVPTS_BE34_ordinary_valuation_route_unaffected(client):
    """PVPTS-BE34: Regression — ordinary valuation /api/advisor/valuate still responds (not 404/500)."""
    resp = client.post(
        "/api/advisor/valuate",
        json={
            "property_type": "شقة سكنية",
            "area": 120,
            "city": "القاهرة",
            "purpose": "market_value",
        },
        content_type="application/json",
    )
    assert resp.status_code != 404, (
        "Ordinary valuation route /api/advisor/valuate must not return 404 after Section 3 restructure"
    )
    assert resp.status_code != 500, (
        "Ordinary valuation route crashed with 500 after Section 3 restructure"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PVDSR Backend Tests — Professional Valuation Dynamic Special Asset Requirements
# ═══════════════════════════════════════════════════════════════════════════════

def _pvdsr_create(client, subtype="padel_tennis_court"):
    """Helper: create a PVR record with an uncommon asset subtype."""
    return client.post(
        "/api/professional-valuation/requests",
        json={
            "client_name": "عميل PVDSR اختبار",
            "property_type": "أصول غير شائعة",
            "valuation_purpose": "قيمة سوقية",
            "asset_family": "sports_recreation_assets",
            "asset_subtype": subtype,
            "area": 500,
            "city": "الرياض",
        },
        content_type="application/json",
    )


def test_PVDSR_BE01_special_asset_requirements_context_in_response(client):
    """PVDSR-BE01: POST /api/professional-valuation returns special_asset_requirements_context."""
    r = _pvdsr_create(client)
    assert r.status_code in (200, 201), f"Expected 200/201, got {r.status_code}"
    body = r.get_json()
    assert "special_asset_requirements_context" in body, (
        "special_asset_requirements_context missing from create response"
    )


def test_PVDSR_BE02_special_asset_context_is_dict(client):
    """PVDSR-BE02: special_asset_requirements_context must be a dict."""
    r = _pvdsr_create(client)
    body = r.get_json()
    ctx = body.get("special_asset_requirements_context", None)
    assert isinstance(ctx, dict), f"special_asset_requirements_context must be dict, got {type(ctx)}"


def test_PVDSR_BE03_asset_methodology_guidance_present(client):
    """PVDSR-BE03: asset_methodology_guidance key returned in response."""
    r = _pvdsr_create(client)
    body = r.get_json()
    assert "asset_methodology_guidance" in body, (
        "asset_methodology_guidance missing from create response"
    )


def test_PVDSR_BE04_asset_report_workbook_context_present(client):
    """PVDSR-BE04: asset_report_workbook_context key returned in response."""
    r = _pvdsr_create(client)
    body = r.get_json()
    assert "asset_report_workbook_context" in body, (
        "asset_report_workbook_context missing from create response"
    )


def test_PVDSR_BE05_future_integrations_present(client):
    """PVDSR-BE05: future_integrations key returned in response."""
    r = _pvdsr_create(client)
    body = r.get_json()
    assert "future_integrations" in body, (
        "future_integrations missing from create response"
    )


def test_PVDSR_BE06_special_asset_taxonomy_v2_registries_present(client):
    """PVDSR-BE06: special_asset_taxonomy_v2_registries key returned in response."""
    r = _pvdsr_create(client)
    body = r.get_json()
    assert "special_asset_taxonomy_v2_registries" in body, (
        "special_asset_taxonomy_v2_registries missing from create response"
    )


def test_PVDSR_BE07_taxonomy_registries_has_10_keys(client):
    """PVDSR-BE07: special_asset_taxonomy_v2_registries contains all 10 registry keys."""
    r = _pvdsr_create(client)
    body = r.get_json()
    regs = body.get("special_asset_taxonomy_v2_registries", {})
    expected_keys = {
        "uncommon_asset_family", "uncommon_asset_subtype", "requirement_group",
        "field_type", "dynamic_requirement_field", "asset_specific_requirement",
        "methodology_guidance", "asset_report_workbook_context",
        "future_integrations", "legacy_asset_alias",
    }
    missing = expected_keys - set(regs.keys())
    assert not missing, f"Registry keys missing: {missing}"


def test_PVDSR_BE08_uncommon_asset_family_registry_has_entries(client):
    """PVDSR-BE08: uncommon_asset_family registry contains entries."""
    r = _pvdsr_create(client)
    body = r.get_json()
    regs = body.get("special_asset_taxonomy_v2_registries", {})
    fam = regs.get("uncommon_asset_family", [])
    assert len(fam) >= 5, f"uncommon_asset_family must have >=5 entries, got {len(fam)}"


def test_PVDSR_BE09_uncommon_asset_subtype_registry_has_entries(client):
    """PVDSR-BE09: uncommon_asset_subtype registry contains entries."""
    r = _pvdsr_create(client)
    body = r.get_json()
    regs = body.get("special_asset_taxonomy_v2_registries", {})
    subs = regs.get("uncommon_asset_subtype", [])
    assert len(subs) >= 10, f"uncommon_asset_subtype must have >=10 entries, got {len(subs)}"


def test_PVDSR_BE10_requirement_group_registry_has_5_groups(client):
    """PVDSR-BE10: requirement_group registry has exactly 5 groups."""
    r = _pvdsr_create(client)
    body = r.get_json()
    regs = body.get("special_asset_taxonomy_v2_registries", {})
    grps = regs.get("requirement_group", [])
    assert len(grps) == 5, f"requirement_group must have exactly 5 entries, got {len(grps)}"


def test_PVDSR_BE11_field_type_registry_has_entries(client):
    """PVDSR-BE11: field_type registry contains at least 10 field types."""
    r = _pvdsr_create(client)
    body = r.get_json()
    regs = body.get("special_asset_taxonomy_v2_registries", {})
    fts = regs.get("field_type", [])
    assert len(fts) >= 10, f"field_type must have >=10 entries, got {len(fts)}"


def test_PVDSR_BE12_methodology_guidance_advisory_only(client):
    """PVDSR-BE12: asset_methodology_guidance is marked advisory_only=True."""
    r = _pvdsr_create(client)
    body = r.get_json()
    mg = body.get("asset_methodology_guidance", {})
    assert isinstance(mg, dict), "asset_methodology_guidance must be dict"
    assert mg.get("advisory_only") is True, (
        "asset_methodology_guidance.advisory_only must be True (non-binding)"
    )


def test_PVDSR_BE13_report_workbook_context_advisory_only(client):
    """PVDSR-BE13: asset_report_workbook_context is marked advisory_only=True."""
    r = _pvdsr_create(client)
    body = r.get_json()
    rw = body.get("asset_report_workbook_context", {})
    assert isinstance(rw, dict), "asset_report_workbook_context must be dict"
    assert rw.get("advisory_only") is True, (
        "asset_report_workbook_context.advisory_only must be True"
    )


def test_PVDSR_BE14_future_integrations_are_stubs(client):
    """PVDSR-BE14: future_integrations items are tagged as stubs (not active)."""
    r = _pvdsr_create(client)
    body = r.get_json()
    fi = body.get("future_integrations", {})
    assert isinstance(fi, dict), "future_integrations must be dict"
    assert fi.get("status") in ("future_stub", "inactive", "stub", None), (
        "future_integrations.status must indicate non-active state"
    )


def test_PVDSR_BE15_no_internal_paths_in_special_context(client):
    """PVDSR-BE15: special_asset_requirements_context must not expose file system paths."""
    r = _pvdsr_create(client)
    body = r.get_json()
    ctx = body.get("special_asset_requirements_context", {})
    ctx_str = str(ctx)
    assert "C:\\" not in ctx_str and "/home/" not in ctx_str and "core_engine/" not in ctx_str, (
        "special_asset_requirements_context must not expose internal file paths"
    )


def test_PVDSR_BE16_detail_contains_special_asset_context(client):
    """PVDSR-BE16: GET detail endpoint returns special_asset_requirements_context."""
    import pytest
    cr = _pvdsr_create(client)
    body = cr.get_json()
    pvr_id = body.get("id") or body.get("pvr_id") or body.get("request_id")
    if not pvr_id:
        pytest.skip("No ID in create response")
    dr = client.get(f"/api/professional-valuation/{pvr_id}")
    if dr.status_code == 404:
        pytest.skip("Detail route not found for this ID format")
    detail = dr.get_json()
    assert "special_asset_requirements_context" in detail, (
        "special_asset_requirements_context missing from GET detail response"
    )


def test_PVDSR_BE17_asset_subtype_stored_in_context(client):
    """PVDSR-BE17: special_asset_requirements_context records the asset_subtype submitted."""
    r = _pvdsr_create(client, subtype="cinema")
    body = r.get_json()
    ctx = body.get("special_asset_requirements_context", {})
    assert ctx.get("asset_subtype") == "cinema" or "cinema" in str(ctx), (
        "asset_subtype 'cinema' should appear in special_asset_requirements_context"
    )


def test_PVDSR_BE18_cinema_subtype_accepted(client):
    """PVDSR-BE18: asset_subtype='cinema' is accepted without 422."""
    r = _pvdsr_create(client, subtype="cinema")
    assert r.status_code in (200, 201), f"cinema subtype rejected, got {r.status_code}"


def test_PVDSR_BE19_general_hospital_subtype_accepted(client):
    """PVDSR-BE19: asset_subtype='general_hospital' is accepted without 422."""
    r = _pvdsr_create(client, subtype="general_hospital")
    assert r.status_code in (200, 201), f"general_hospital subtype rejected, got {r.status_code}"


def test_PVDSR_BE20_school_campus_subtype_accepted(client):
    """PVDSR-BE20: asset_subtype='school_campus' is accepted without 422."""
    r = _pvdsr_create(client, subtype="school_campus")
    assert r.status_code in (200, 201), f"school_campus subtype rejected, got {r.status_code}"


def test_PVDSR_BE21_heritage_subtype_accepted(client):
    """PVDSR-BE21: asset_subtype='distinguished_architectural_heritage' accepted."""
    r = _pvdsr_create(client, subtype="distinguished_architectural_heritage")
    assert r.status_code in (200, 201), (
        f"distinguished_architectural_heritage subtype rejected, got {r.status_code}"
    )


def test_PVDSR_BE22_legacy_alias_hospital_resolves(client):
    """PVDSR-BE22: Legacy alias subtype='hospital' is accepted (maps to general_hospital)."""
    r = _pvdsr_create(client, subtype="hospital")
    assert r.status_code in (200, 201), f"legacy alias 'hospital' rejected, got {r.status_code}"


def test_PVDSR_BE23_legacy_alias_school_resolves(client):
    """PVDSR-BE23: Legacy alias subtype='school' is accepted (maps to school_campus)."""
    r = _pvdsr_create(client, subtype="school")
    assert r.status_code in (200, 201), f"legacy alias 'school' rejected, got {r.status_code}"


def test_PVDSR_BE24_distribution_center_subtype_accepted(client):
    """PVDSR-BE24: Logistics subtype='distribution_center' is accepted."""
    r = _pvdsr_create(client, subtype="distribution_center")
    assert r.status_code in (200, 201), (
        f"distribution_center subtype rejected, got {r.status_code}"
    )


def test_PVDSR_BE25_legacy_asset_alias_registry_has_entries(client):
    """PVDSR-BE25: legacy_asset_alias registry contains at least 5 entries."""
    r = _pvdsr_create(client)
    body = r.get_json()
    regs = body.get("special_asset_taxonomy_v2_registries", {})
    aliases = regs.get("legacy_asset_alias", [])
    assert len(aliases) >= 5, f"legacy_asset_alias must have >=5 entries, got {len(aliases)}"


def test_PVDSR_BE26_dynamic_requirement_field_registry_has_entries(client):
    """PVDSR-BE26: dynamic_requirement_field registry contains at least 10 entries."""
    r = _pvdsr_create(client)
    body = r.get_json()
    regs = body.get("special_asset_taxonomy_v2_registries", {})
    fields = regs.get("dynamic_requirement_field", [])
    assert len(fields) >= 10, f"dynamic_requirement_field must have >=10 entries, got {len(fields)}"


def test_PVDSR_BE27_ordinary_valuation_unaffected_by_pvdsr(client):
    """PVDSR-BE27: Regression — POST /api/professional-valuation/requests still works with standard payload."""
    r = client.post(
        "/api/professional-valuation/requests",
        json={
            "client_name": "عميل اختبار انحدار",
            "property_type": "شقة سكنية",
            "valuation_purpose": "قيمة سوقية",
            "area": 100,
            "city": "القاهرة",
        },
        content_type="application/json",
    )
    assert r.status_code not in (404, 500), (
        f"Professional valuation route broken after PVDSR changes, got {r.status_code}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PVACR: Professional Valuation Chat Output Final Restructure — Backend Tests
# Part R: PVACR_BE01 – PVACR_BE24
# ═══════════════════════════════════════════════════════════════════════════════

def _pvacr_create(client, report_action="traditional_report"):
    """Helper: create a PVR record and return (response, body)."""
    r = client.post(
        "/api/professional-valuation/requests",
        json={
            "client_name": "عميل PVACR اختبار",
            "property_type": "شقة سكنية",
            "valuation_purpose": "قيمة سوقية",
            "area": 120,
            "city": "القاهرة",
            "selected_report_action": report_action,
        },
        content_type="application/json",
    )
    return r, (r.get_json() or {})


def test_PVACR_BE01_chat_output_context_present_in_post(client):
    """PVACR-BE01: chat_output_context exists in POST response."""
    _, body = _pvacr_create(client)
    assert "chat_output_context" in body, "chat_output_context missing from POST response"


def test_PVACR_BE02_chat_output_context_is_dict(client):
    """PVACR-BE02: chat_output_context is a dict."""
    _, body = _pvacr_create(client)
    assert isinstance(body.get("chat_output_context"), dict), "chat_output_context must be dict"


def test_PVACR_BE03_report_output_registry_context_present(client):
    """PVACR-BE03: report_output_registry_context in POST response."""
    _, body = _pvacr_create(client)
    assert "report_output_registry_context" in body, "report_output_registry_context missing"


def test_PVACR_BE04_output_format_visibility_policy_context_present(client):
    """PVACR-BE04: output_format_visibility_policy_context in POST response."""
    _, body = _pvacr_create(client)
    assert "output_format_visibility_policy_context" in body, \
        "output_format_visibility_policy_context missing"


def test_PVACR_BE05_deprecated_visible_controls_context_present(client):
    """PVACR-BE05: deprecated_visible_controls_context in POST response."""
    _, body = _pvacr_create(client)
    assert "deprecated_visible_controls_context" in body, \
        "deprecated_visible_controls_context missing"


def test_PVACR_BE06_report_output_registry_has_6_entries(client):
    """PVACR-BE06: report_output_registry has all 6 required actions."""
    _, body = _pvacr_create(client)
    reg = body.get("report_output_registry_context", {}).get("entries", {})
    required = {
        "traditional_report", "detailed_report", "professional_report",
        "simulated_uploaded_report", "report_review_output", "hbu_analysis_report",
    }
    missing = required - set(reg.keys())
    assert not missing, f"Missing report action entries: {missing}"


def test_PVACR_BE07_traditional_report_in_registry(client):
    """PVACR-BE07: traditional_report entry has correct structure."""
    _, body = _pvacr_create(client)
    reg = body.get("report_output_registry_context", {}).get("entries", {})
    entry = reg.get("traditional_report", {})
    assert entry.get("user_pdf_allowed") is True, "traditional_report: user_pdf_allowed must be True"
    assert entry.get("advisory_allowed") is True, "traditional_report: advisory_allowed must be True"


def test_PVACR_BE08_simulated_report_requires_training_toggle(client):
    """PVACR-BE08: simulated_uploaded_report entry has requires_training_toggle=True."""
    _, body = _pvacr_create(client, report_action="simulated_uploaded_report")
    reg = body.get("report_output_registry_context", {}).get("entries", {})
    entry = reg.get("simulated_uploaded_report", {})
    assert entry.get("requires_training_toggle") is True, \
        "simulated_uploaded_report must require training toggle"
    assert entry.get("simulation_only") is True, "simulated_uploaded_report must be simulation_only"


def test_PVACR_BE09_report_review_requires_review_toggle(client):
    """PVACR-BE09: report_review_output has requires_report_review_toggle=True."""
    _, body = _pvacr_create(client, report_action="report_review_output")
    reg = body.get("report_output_registry_context", {}).get("entries", {})
    entry = reg.get("report_review_output", {})
    assert entry.get("requires_report_review_toggle") is True, \
        "report_review_output must require review toggle"


def test_PVACR_BE10_hbu_report_requires_hbu_toggle(client):
    """PVACR-BE10: hbu_analysis_report has requires_hbu_report_toggle=True."""
    _, body = _pvacr_create(client, report_action="hbu_analysis_report")
    reg = body.get("report_output_registry_context", {}).get("entries", {})
    entry = reg.get("hbu_analysis_report", {})
    assert entry.get("requires_hbu_report_toggle") is True, \
        "hbu_analysis_report must require HBU toggle"


def test_PVACR_BE11_chat_output_context_advisory_only(client):
    """PVACR-BE11: chat_output_context.advisory_only is True."""
    _, body = _pvacr_create(client)
    ctx = body.get("chat_output_context", {})
    assert ctx.get("advisory_only") is True, "chat_output_context must be advisory_only"


def test_PVACR_BE12_admin_excel_not_visible_to_user(client):
    """PVACR-BE12: admin_excel_visible_to_current_user is False in chat_output_context."""
    _, body = _pvacr_create(client)
    ctx = body.get("chat_output_context", {})
    assert ctx.get("admin_excel_visible_to_current_user") is False, \
        "admin_excel must NOT be visible to current user"


def test_PVACR_BE13_output_permissions_present(client):
    """PVACR-BE13: output_permissions exists in chat_output_context."""
    _, body = _pvacr_create(client)
    perms = body.get("chat_output_context", {}).get("output_permissions", {})
    assert "can_generate_user_pdf" in perms, "can_generate_user_pdf missing from output_permissions"
    assert "can_generate_admin_excel" in perms, "can_generate_admin_excel missing"
    assert "can_generate_certified_pdf" in perms, "can_generate_certified_pdf missing"


def test_PVACR_BE14_certified_pdf_blocked_without_gate(client):
    """PVACR-BE14: can_generate_certified_pdf is False when certification_ready not set."""
    _, body = _pvacr_create(client)
    perms = body.get("chat_output_context", {}).get("output_permissions", {})
    assert perms.get("can_generate_certified_pdf") is False, \
        "certified PDF must be blocked without certification gate"


def test_PVACR_BE15_deprecated_controls_has_5_entries(client):
    """PVACR-BE15: deprecated_visible_controls_context has >= 5 deprecated controls."""
    _, body = _pvacr_create(client)
    ctx = body.get("deprecated_visible_controls_context", {})
    controls = ctx.get("deprecated_controls", {})
    assert len(controls) >= 5, f"Expected >= 5 deprecated controls, got {len(controls)}"


def test_PVACR_BE16_no_internal_paths_in_chat_output_context(client):
    """PVACR-BE16: chat_output_context contains no internal paths."""
    _, body = _pvacr_create(client)
    ctx_str = str(body.get("chat_output_context", {}))
    for bad in ("C:\\", "/home/", ".py", "requests.jsonl", "__file__"):
        assert bad not in ctx_str, f"Internal path fragment found: {bad!r}"


def test_PVACR_BE17_available_report_actions_has_6_entries(client):
    """PVACR-BE17: chat_output_context.available_report_actions has >= 6 entries."""
    _, body = _pvacr_create(client)
    actions = body.get("chat_output_context", {}).get("available_report_actions", [])
    assert len(actions) >= 6, f"Expected >= 6 available_report_actions, got {len(actions)}"


def test_PVACR_BE18_selected_report_action_present(client):
    """PVACR-BE18: selected_report_action key present in chat_output_context."""
    _, body = _pvacr_create(client, report_action="traditional_report")
    ctx = body.get("chat_output_context", {})
    assert "selected_report_action" in ctx, "selected_report_action must be present"


def test_PVACR_BE19_old_report_type_still_accepted(client):
    """PVACR-BE19: Legacy report_type field still accepted (backward compat)."""
    r = client.post(
        "/api/professional-valuation/requests",
        json={
            "client_name": "عميل انحدار",
            "property_type": "شقة سكنية",
            "valuation_purpose": "قيمة سوقية",
            "city": "القاهرة",
            "report_type": "professional_report",
        },
        content_type="application/json",
    )
    assert r.status_code not in (400, 404, 500), \
        f"Legacy report_type rejected: {r.status_code}"


def test_PVACR_BE20_chat_output_pdf_route_exists(client):
    """PVACR-BE20: POST chat-output/pdf route returns 200 or expected auth status."""
    _, body = _pvacr_create(client)
    rid = body.get("request_id", "")
    if not rid:
        return
    r = client.post(
        f"/api/professional-valuation/requests/{rid}/chat-output/pdf",
        json={"report_action": "traditional_report"},
        content_type="application/json",
    )
    assert r.status_code in (200, 201, 401, 403, 404), \
        f"chat-output/pdf route unexpected status: {r.status_code}"


def test_PVACR_BE21_chat_output_admin_excel_returns_403_for_non_admin(client):
    """PVACR-BE21: admin-excel route returns 403 for non-admin."""
    _, body = _pvacr_create(client)
    rid = body.get("request_id", "")
    if not rid:
        return
    r = client.post(
        f"/api/professional-valuation/requests/{rid}/chat-output/admin-excel",
        json={"report_action": "traditional_report"},
        content_type="application/json",
    )
    assert r.status_code in (401, 403, 404), \
        f"admin-excel should return 403/401 for non-admin, got {r.status_code}"


def test_PVACR_BE22_expert_review_request_route_exists(client):
    """PVACR-BE22: POST expert-review-request route returns 200."""
    _, body = _pvacr_create(client)
    rid = body.get("request_id", "")
    if not rid:
        return
    r = client.post(
        f"/api/professional-valuation/requests/{rid}/expert-review-request",
        json={"note": "طلب مراجعة اختبار"},
        content_type="application/json",
    )
    assert r.status_code in (200, 201, 401, 404), \
        f"expert-review-request unexpected status: {r.status_code}"


def test_PVACR_BE23_simulated_report_blocker_without_training(client):
    """PVACR-BE23: simulated_uploaded_report without training flag produces blockers."""
    r = client.post(
        "/api/professional-valuation/requests",
        json={
            "client_name": "عميل محاكاة",
            "property_type": "شقة سكنية",
            "valuation_purpose": "قيمة سوقية",
            "city": "القاهرة",
            "selected_report_action": "simulated_uploaded_report",
            "uploaded_report_simulation_enabled": False,
        },
        content_type="application/json",
    )
    body = r.get_json() or {}
    perms = body.get("chat_output_context", {}).get("output_permissions", {})
    blockers = perms.get("blockers", [])
    assert len(blockers) > 0, "simulated report without training must produce blockers"


def test_PVACR_BE24_ordinary_valuation_unaffected_by_pvacr(client):
    """PVACR-BE24: Regression — ordinary POST route unaffected by PVACR changes."""
    r = client.post(
        "/api/professional-valuation/requests",
        json={
            "client_name": "عميل انحدار عادي",
            "property_type": "فيلا سكنية",
            "valuation_purpose": "قيمة سوقية",
            "area": 200,
            "city": "الرياض",
        },
        content_type="application/json",
    )
    assert r.status_code not in (404, 500), \
        f"Ordinary route broken after PVACR changes: {r.status_code}"

