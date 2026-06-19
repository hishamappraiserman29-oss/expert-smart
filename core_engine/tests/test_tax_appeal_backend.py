"""
test_tax_appeal_backend.py — Tax Appeal Backend Phase 1-3 unit tests.

Tests:
  TAB01  POST /api/tax-appeal/leads with valid data → 201 + lead_id
  TAB02  missing owner_name → 400
  TAB03  missing phone → 400
  TAB04  lead_id returned in response
  TAB05  lead is persisted in JSONL
  TAB06  allowed document (PDF) uploads successfully
  TAB07  disallowed extension (.exe) is rejected; lead still created
  TAB08  oversized file is rejected; lead still created
  TAB09  sanitized filename strips dangerous characters
  TAB10  path-traversal filename is neutralized
  TAB11  PDF generation returns pdf_available=True
  TAB12  PDF file is created on disk
  TAB13  response includes pdf_download_url
  TAB14  GET /api/tax-appeal/leads/<id>/pdf returns PDF bytes
  TAB15  PDF file is a valid PDF (starts with %PDF)
  TAB16  GET /api/tax-appeal/leads requires auth (returns 401 without token)
  TAB16b GET /api/tax-appeal/leads with auth returns 200
  TAB17  GET /api/tax-appeal/leads/<bad-id>/pdf returns 400
  TAB17b path-traversal in URL segment returns 400 or 404
  TAB18  unknown lead_id returns 404
  TAB19  response has no email/whatsapp_sent fields
  TAB20  no Excel exposed to unauthenticated users
"""
from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path

import pytest

# ── Path setup (same pattern as test_requirements_endpoint.py) ─────────────
_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(str(_CORE))

from bridge_api import app                   # noqa: E402
from auth.tokens import generate_token       # noqa: E402
import tax_appeal_routes as _tar            # noqa: E402

_TEST_SECRET = "tax-appeal-test-secret-strong-32chars"


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def env(monkeypatch):
    """Set JWT_SECRET for every test (same pattern as test_requirements_endpoint.py)."""
    monkeypatch.setenv("JWT_SECRET", _TEST_SECRET)
    monkeypatch.delenv("JWT_TTL_SECONDS", raising=False)


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _auth() -> dict:
    return {"Authorization": f"Bearer {generate_token('test-admin')}"}


def _post_lead(client, extra_form=None, files=None):
    """Helper: POST a minimal valid lead."""
    data = {
        "owner_name": "أحمد محمد الاختبار",
        "phone": "01012345678",
        "tax_type": "transfer",
        "asset_type": "residential",
        "country": "EG",
        "region": "القاهرة",
        "city": "مدينة نصر",
        "area": "250",
        "government_claim": "40000",
        "sale_value": "1000000",
        "calculated_estimated_tax": "25000",
        "calculated_potential_saving": "15000",
        "calculated_gap_percent": "60.0",
        "risk_level": "مرتفع",
    }
    if extra_form:
        data.update(extra_form)
    if files:
        data.update(files)
    return client.post(
        "/api/tax-appeal/leads",
        data=data,
        content_type="multipart/form-data",
    )


# ── Tests: Create Lead ───────────────────────────────────────────────────────

def test_TAB01_valid_lead_returns_201(client):
    resp = _post_lead(client)
    assert resp.status_code == 201


def test_TAB02_missing_owner_name_returns_400(client):
    resp = client.post(
        "/api/tax-appeal/leads",
        data={"phone": "01012345678"},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert resp.get_json()["status"] == "error"


def test_TAB03_missing_phone_returns_400(client):
    resp = client.post(
        "/api/tax-appeal/leads",
        data={"owner_name": "اختبار"},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert resp.get_json()["status"] == "error"


def test_TAB04_lead_id_returned(client):
    body = _post_lead(client).get_json()
    assert "lead_id" in body
    assert body["lead_id"].startswith("TAX-")
    assert len(body["lead_id"]) == 12          # "TAX-" + 8 hex chars


def test_TAB05_lead_persisted_in_jsonl(client):
    lead_id = _post_lead(client).get_json()["lead_id"]
    found = _tar._read_lead(lead_id)
    assert found is not None
    assert found["lead_id"] == lead_id
    assert found["source_page"] == "tax_appeal_tab"
    assert found["approval_status"] == "draft_lead"


# ── Tests: Document Upload ───────────────────────────────────────────────────

def test_TAB06_allowed_pdf_uploads_successfully(client):
    resp = _post_lead(client, files={
        "doc_0": (io.BytesIO(b"%PDF-1.4 test"), "form3.pdf", "application/pdf"),
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["documents_saved"] == 1
    assert body["document_errors"] == []


def test_TAB07_disallowed_extension_rejected(client):
    resp = _post_lead(client, files={
        "doc_0": (io.BytesIO(b"malicious"), "bad.exe", "application/octet-stream"),
    })
    assert resp.status_code == 201      # lead is still saved
    body = resp.get_json()
    assert body["documents_saved"] == 0
    assert len(body["document_errors"]) > 0
    assert "غير مدعومة" in body["document_errors"][0]


def test_TAB08_oversized_file_rejected(client):
    big = b"x" * (11 * 1024 * 1024)    # 11 MB > 10 MB limit
    resp = _post_lead(client, files={
        "doc_0": (io.BytesIO(big), "big.pdf", "application/pdf"),
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["documents_saved"] == 0
    assert len(body["document_errors"]) > 0


def test_TAB09_filename_sanitized(client):
    resp = _post_lead(client, files={
        "doc_0": (io.BytesIO(b"content"), "normal file!@#.pdf", "application/pdf"),
    })
    body = resp.get_json()
    assert body["documents_saved"] == 1
    lead = _tar._read_lead(body["lead_id"])
    stored = lead["documents"][0]["original_filename"]
    for ch in ("!", "@", "#", "/", "\\"):
        assert ch not in stored


def test_TAB10_path_traversal_neutralized(client):
    resp = _post_lead(client, files={
        "doc_0": (io.BytesIO(b"content"), "../../etc/passwd.pdf", "application/pdf"),
    })
    body = resp.get_json()
    assert body["documents_saved"] == 1
    lead = _tar._read_lead(body["lead_id"])
    stored = lead["documents"][0]["original_filename"]
    assert ".." not in stored
    assert "/" not in stored
    assert "\\" not in stored


# ── Tests: PDF Generation ────────────────────────────────────────────────────

def test_TAB11_pdf_available_true_in_response(client):
    body = _post_lead(client).get_json()
    assert body.get("pdf_available") is True, \
        f"pdf_message: {body.get('pdf_message')}"


def test_TAB12_pdf_file_created_on_disk(client):
    lead_id = _post_lead(client).get_json()["lead_id"]
    pdf_path = _tar._REPORTS / lead_id / "tax_screening_draft.pdf"
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 100


def test_TAB13_response_includes_pdf_download_url(client):
    body = _post_lead(client).get_json()
    assert body.get("pdf_download_url", "").startswith("/api/tax-appeal/leads/TAX-")
    assert body["pdf_download_url"].endswith("/pdf")


def test_TAB14_pdf_download_endpoint_returns_bytes(client):
    lead_id = _post_lead(client).get_json()["lead_id"]
    dl = client.get(f"/api/tax-appeal/leads/{lead_id}/pdf")
    assert dl.status_code == 200
    assert "pdf" in dl.content_type
    assert dl.data[:4] == b"%PDF"


def test_TAB15_pdf_file_is_valid_pdf(client):
    lead_id = _post_lead(client).get_json()["lead_id"]
    raw = (_tar._REPORTS / lead_id / "tax_screening_draft.pdf").read_bytes()
    assert raw[:4] == b"%PDF"
    assert len(raw) > 500          # non-trivial content


# ── Tests: Admin Endpoint ────────────────────────────────────────────────────

def test_TAB16_list_leads_requires_auth(client):
    resp = client.get("/api/tax-appeal/leads")
    assert resp.status_code == 401


def test_TAB16b_list_leads_with_auth_returns_200(client):
    resp = client.get("/api/tax-appeal/leads", headers=_auth())
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert isinstance(body["leads"], list)


# ── Tests: PDF Download Edge Cases ───────────────────────────────────────────

def test_TAB17_bad_lead_id_pattern_returns_400(client):
    assert client.get("/api/tax-appeal/leads/INVALID-ID/pdf").status_code == 400


def test_TAB17b_injection_in_url_returns_400_or_404(client):
    # Flask path routing handles traversal, expect 400 or 404
    resp = client.get("/api/tax-appeal/leads/TAX-GGGGGGGG/pdf")
    assert resp.status_code == 400          # non-hex uppercase → regex fail


def test_TAB18_unknown_lead_id_returns_404(client):
    assert client.get("/api/tax-appeal/leads/TAX-00000000/pdf").status_code == 404


# ── Tests: No Unwanted Behavior ──────────────────────────────────────────────

def test_TAB19_response_has_no_messaging_sent_fields(client):
    body_str = json.dumps(_post_lead(client).get_json())
    assert "email_sent" not in body_str
    assert "whatsapp_sent" not in body_str
    assert "sms_sent" not in body_str


def test_TAB20_no_excel_download_without_auth(client):
    resp = client.get("/api/valuation/report/download/nonexistent.xlsx")
    assert resp.status_code in (401, 404)
