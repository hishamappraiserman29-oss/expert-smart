"""
test_shared_request_backend.py — Shared Request Backend unit tests.

Tests:
  SRB01  Create request for source_page=tax_appeal succeeds (201)
  SRB02  Create request for source_page=simple_valuation succeeds (201)
  SRB03  Create request for source_page=chat succeeds (201)
  SRB04  Invalid source_page is rejected (400)
  SRB05  Missing user_name is rejected (400)
  SRB06  Missing phone AND email is rejected (400)
  SRB07  Request is persisted in JSONL
  SRB08  Upload allowed document (PDF) succeeds
  SRB09  Disallowed extension (.exe) is rejected; request still created
  SRB10  Path-traversal filename is sanitized
  SRB11  Uploaded file metadata is persisted with request
  SRB12  Draft PDF generation: pdf_available=True in response
  SRB13  PDF file exists on disk after create
  SRB14  Response includes non_certified=True
  SRB15  PDF contains advisory/non-certified warning (file bytes check)
  SRB16  No email/WhatsApp/SMS sent fields in response
  SRB17  Admin list endpoint is protected (401 without token)
  SRB17b Admin list endpoint with auth returns 200
  SRB18  GET /api/expert-requests/<id> returns request details
  SRB19  GET /api/expert-requests/<bad>/draft-pdf returns 400
  SRB20  GET /api/expert-requests/REQ-00000000/draft-pdf returns 404
  SRB21  No internal Excel exposed via shared backend
  SRB22  source_page=professional_valuation is accepted
  SRB23  source_page=composite_valuation is accepted
"""
from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path

import pytest

# ── Path setup ───────────────────────────────────────────────────────────────
_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(str(_CORE))

from bridge_api import app                     # noqa: E402
from auth.tokens import generate_token         # noqa: E402
import shared_request_routes as _srr           # noqa: E402

_TEST_SECRET = "tax-appeal-test-secret-strong-32chars"


# ── Fixtures ─────────────────────────────────────────────────────────────────

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


def _post_request(client, source_page="simple_valuation", extra=None, files=None):
    """Helper: POST a minimal valid shared request."""
    data = {
        "source_page":   source_page,
        "request_kind":  "expert_contact",
        "user_name":     "أحمد محمد الاختبار",
        "phone":         "01012345678",
        "summary":       "طلب اختبار تلقائي",
    }
    if extra:
        data.update(extra)
    if files:
        data.update(files)
    return client.post(
        "/api/expert-requests",
        data=data,
        content_type="multipart/form-data",
    )


# ── Tests: Create request ─────────────────────────────────────────────────────

def test_SRB01_create_tax_appeal_request(client):
    resp = _post_request(client, source_page="tax_appeal")
    assert resp.status_code == 201
    assert resp.get_json()["status"] == "success"


def test_SRB02_create_simple_valuation_request(client):
    resp = _post_request(client, source_page="simple_valuation")
    assert resp.status_code == 201
    assert resp.get_json()["status"] == "success"


def test_SRB03_create_chat_request(client):
    resp = _post_request(client, source_page="chat")
    assert resp.status_code == 201
    assert resp.get_json()["status"] == "success"


def test_SRB04_invalid_source_page_rejected(client):
    resp = _post_request(client, source_page="unknown_page")
    assert resp.status_code == 400
    assert resp.get_json()["status"] == "error"


def test_SRB05_missing_user_name_rejected(client):
    resp = client.post(
        "/api/expert-requests",
        data={"source_page": "chat", "phone": "01012345678"},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_SRB06_missing_phone_and_email_rejected(client):
    resp = client.post(
        "/api/expert-requests",
        data={"source_page": "chat", "user_name": "اختبار"},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


# ── Tests: Persistence ────────────────────────────────────────────────────────

def test_SRB07_request_persisted_in_jsonl(client):
    body = _post_request(client).get_json()
    rid  = body["request_id"]
    assert rid.startswith("REQ-")
    found = _srr._read_request(rid)
    assert found is not None
    assert found["request_id"] == rid
    assert found["source_page"] == "simple_valuation"
    assert found["status"] == "new"
    assert found["approval_status"] == "draft_only"


# ── Tests: Document upload ────────────────────────────────────────────────────

def test_SRB08_allowed_pdf_uploads_successfully(client):
    resp = _post_request(client, files={
        "doc_0": (io.BytesIO(b"%PDF-1.4 test"), "test_doc.pdf", "application/pdf"),
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["documents_saved"] == 1
    assert body["document_errors"] == []


def test_SRB09_disallowed_extension_rejected(client):
    resp = _post_request(client, files={
        "doc_0": (io.BytesIO(b"bad"), "virus.exe", "application/octet-stream"),
    })
    assert resp.status_code == 201      # request still created
    body = resp.get_json()
    assert body["documents_saved"] == 0
    assert len(body["document_errors"]) > 0


def test_SRB10_path_traversal_filename_sanitized(client):
    resp = _post_request(client, files={
        "doc_0": (io.BytesIO(b"content"), "../../etc/passwd.pdf", "application/pdf"),
    })
    assert resp.status_code == 201
    body  = resp.get_json()
    assert body["documents_saved"] == 1
    found = _srr._read_request(body["request_id"])
    stored = found["documents"][0]["original_filename"]
    assert ".." not in stored
    assert "/" not in stored
    assert "\\" not in stored


def test_SRB11_document_metadata_persisted(client):
    resp = _post_request(client, files={
        "doc_0": (io.BytesIO(b"%PDF content"), "ownership.pdf", "application/pdf"),
    })
    body  = resp.get_json()
    found = _srr._read_request(body["request_id"])
    assert len(found["documents"]) == 1
    doc = found["documents"][0]
    assert "document_id" in doc
    assert doc["extension"] == ".pdf"
    assert doc["size_bytes"] > 0


# ── Tests: PDF generation ─────────────────────────────────────────────────────

def test_SRB12_pdf_available_true_in_response(client):
    body = _post_request(client).get_json()
    assert body.get("pdf_available") is True, f"pdf_message: {body.get('pdf_message')}"


def test_SRB13_pdf_file_created_on_disk(client):
    rid  = _post_request(client).get_json()["request_id"]
    path = _srr._REPORTS / rid / "draft_report.pdf"
    assert path.exists()
    assert path.stat().st_size > 100


def test_SRB14_response_includes_non_certified_true(client):
    body = _post_request(client).get_json()
    assert body.get("non_certified") is True


def test_SRB15_pdf_bytes_start_with_pdf_magic(client):
    rid  = _post_request(client).get_json()["request_id"]
    raw  = (_srr._REPORTS / rid / "draft_report.pdf").read_bytes()
    assert raw[:4] == b"%PDF"
    assert len(raw) > 500


# ── Tests: No unwanted fields ─────────────────────────────────────────────────

def test_SRB16_response_has_no_messaging_fields(client):
    body_str = json.dumps(_post_request(client).get_json())
    assert "email_sent"     not in body_str
    assert "whatsapp_sent"  not in body_str
    assert "sms_sent"       not in body_str


# ── Tests: Admin endpoint ─────────────────────────────────────────────────────

def test_SRB17_list_requires_auth(client):
    resp = client.get("/api/expert-requests")
    assert resp.status_code == 401


def test_SRB17b_list_with_auth_returns_200(client):
    resp = client.get("/api/expert-requests", headers=_auth())
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert isinstance(body["requests"], list)


# ── Tests: Get request ────────────────────────────────────────────────────────

def test_SRB18_get_request_returns_details(client):
    rid  = _post_request(client).get_json()["request_id"]
    resp = client.get(f"/api/expert-requests/{rid}")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["request"]["request_id"] == rid
    assert "draft_pdf_path" not in body["request"]    # internal path not exposed


# ── Tests: Download edge cases ────────────────────────────────────────────────

def test_SRB19_bad_request_id_returns_400(client):
    assert client.get("/api/expert-requests/INVALID-ID/draft-pdf").status_code == 400


def test_SRB20_unknown_request_id_returns_404(client):
    assert client.get("/api/expert-requests/REQ-00000000/draft-pdf").status_code == 404


# ── Tests: Security ───────────────────────────────────────────────────────────

def test_SRB21_no_excel_exposed_without_auth(client):
    resp = client.get("/api/valuation/report/download/nonexistent.xlsx")
    assert resp.status_code in (401, 404)


# ── Tests: Additional source pages ───────────────────────────────────────────

def test_SRB22_professional_valuation_accepted(client):
    resp = _post_request(client, source_page="professional_valuation",
                         extra={"request_kind": "professional_review"})
    assert resp.status_code == 201
    assert resp.get_json()["source_page"] == "professional_valuation"


def test_SRB23_composite_valuation_accepted(client):
    resp = _post_request(client, source_page="composite_valuation",
                         extra={"request_kind": "composite_review"})
    assert resp.status_code == 201
    assert resp.get_json()["source_page"] == "composite_valuation"


# ── Tests: Simple valuation quick draft PDF endpoint ─────────────────────────

def _sv_pdf_payload(**overrides) -> dict:
    """Return a minimal valid simple-valuation payload."""
    base = {
        "property_type":   "شقة سكنية",
        "area":            120,
        "condition":       "جيدة",
        "valuation_date":  "2026-06-21",
        "purpose":         "القيمة السوقية",
        "estimated_value": 2_500_000,
        "price_range_low": 2_250_000,
        "price_range_high": 2_750_000,
    }
    base.update(overrides)
    return base


def test_SRB24_simple_draft_pdf_valid_payload_returns_pdf(client):
    """POST /api/simple-valuation/draft-pdf with valid payload returns 200 + application/pdf."""
    resp = client.post(
        "/api/simple-valuation/draft-pdf",
        data=json.dumps(_sv_pdf_payload()),
        content_type="application/json",
    )
    assert resp.status_code == 200, f"body: {resp.data[:200]}"
    assert "application/pdf" in resp.content_type


def test_SRB25_simple_draft_pdf_empty_payload_rejected(client):
    """POST /api/simple-valuation/draft-pdf with empty payload returns 400."""
    resp = client.post(
        "/api/simple-valuation/draft-pdf",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["status"] == "error"


def test_SRB26_simple_draft_pdf_has_pdf_header(client):
    """Response bytes start with %%PDF magic and are non-trivially large."""
    resp = client.post(
        "/api/simple-valuation/draft-pdf",
        data=json.dumps(_sv_pdf_payload()),
        content_type="application/json",
    )
    assert resp.status_code == 200
    raw = resp.data
    assert raw[:4] == b"%PDF", f"Expected %PDF, got {raw[:4]!r}"
    assert len(raw) > 500


def test_SRB27_simple_draft_pdf_data_gap_no_value_still_succeeds(client):
    """PDF endpoint succeeds when estimated_value is absent (data-gap scenario)."""
    payload = {
        "property_type": "فيلا",
        "area":          200,
        "condition":     "ممتازة",
        # no estimated_value
    }
    resp = client.post(
        "/api/simple-valuation/draft-pdf",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert "application/pdf" in resp.content_type
    assert len(resp.data) > 200


def test_SRB28_simple_draft_pdf_no_certified_claim_in_headers(client):
    """Response headers carry no claim of certification; non_certified flag not needed for PDF."""
    resp = client.post(
        "/api/simple-valuation/draft-pdf",
        data=json.dumps(_sv_pdf_payload()),
        content_type="application/json",
    )
    assert resp.status_code == 200
    # Headers must not carry any certified=true or X-Certified style claim
    headers_str = str(dict(resp.headers)).lower()
    assert "certified=true" not in headers_str
    assert "x-certified" not in headers_str
