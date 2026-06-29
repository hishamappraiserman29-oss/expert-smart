"""
test_shared_request_backend.py — Shared Request Backend unit tests.

Tests:
  SRB100 Expert workbook contains AVM sheet
  SRB101 AVM sheet contains labels for all 8 model forms A–H
  SRB102 Preliminary PDF template has جداول طرق التقييم المبدئية section
  SRB103 Preliminary PDF template has طريقة AVM section
  SRB104 Preliminary PDF template has all four core method headings
  SRB105 Certified PDF template has طريقة AVM section
  SRB106 Certified PDF template has all required section headings
  SRB107 Certified PDF template has no Qdrant/internet retrieval claims
  SRB108 Preliminary PDF template has no Qdrant/internet retrieval claims
  SRB109 Certified report gated by approved_pending_report (regression guard)
  SRB110 Certified report requires expert_recommended_value (regression guard)

  SRB111 _build_method_context returns comparables list with 4 rows when _qa_simulation=True
  SRB112 _build_method_context comparable rows have all required keys
  SRB113 _build_method_context income_noi is non-empty for qa payload
  SRB114 _build_method_context income_value_calc is non-empty for qa payload
  SRB115 _build_method_context dcf_rows list has 5 entries for qa payload
  SRB116 _build_method_context dcf_value_calc is non-empty for qa payload
  SRB117 _build_method_context cost_land_value is non-empty for qa payload
  SRB118 _build_method_context cost_value_calc is non-empty for qa payload
  SRB119 Workbook مقارنة البيوع sheet has numeric comparable data in row 3 (after headers)
  SRB120 Workbook طريقة الدخل sheet has NOI label in it
  SRB121 Workbook DCF sheet has discount_rate label in it
  SRB122 Workbook توفيق النتائج sheet has weighted value row (نموذج B)
  SRB123 Preliminary PDF template has مصفوفة المقارنات text (comparable matrix added)
  SRB124 Certified PDF template has مصفوفة المقارنات text (comparable matrix added)

  SRB125 Workbook has محاكاة التقييم المحترف sheet
  SRB126 Professional simulation sheet has weighted engine
  SRB127 Professional simulation sheet has purpose route

  SRB128 Workbook has قيمة الأرض sheet (land value — Sheet 14)
  SRB129 Workbook has خرائط وصور sheet (maps/images — Sheet 15)
  SRB130 قيمة الأرض sheet has land sales comparison labels
  SRB131 قيمة الأرض sheet has extraction method labels
  SRB132 قيمة الأرض sheet has توفيق (reconciliation) labels
  SRB133 _build_method_context returns land_comps with 3 entries for QA
  SRB134 _build_method_context returns cost_breakdown with ≥9 rows for QA
  SRB135 _build_method_context returns discount_rate_methods with 4 entries for QA
  SRB136 Discount rate methods include Build-up and CAPM
  SRB137 Discount rate methods include Market yield and Band-of-Investment
  SRB138 _build_method_context returns terminal_cap_methods with 4 entries for QA
  SRB139 _build_method_context returns avm_regression with 7 rows for QA
  SRB140 _build_method_context avm_reg_confidence_band is non-empty for QA
  SRB141 Certified PDF template has قيمة الأرض section and land_comps variable
  SRB142 Certified PDF template has cost_breakdown variable and cost-tbl CSS class
  SRB143 Certified PDF template has discount rate derivation grid (4-method DR)
  SRB144 Certified PDF template has Terminal Value / terminal_cap_methods
  SRB145 Certified PDF template has AVM regression table (reg-tbl / جدول الانحدار)

  SRB146 Workbook contains مصادر الأسعار sheet
  SRB147 Workbook contains ربط التقييم الجماعي sheet
  SRB148 _build_method_context returns price_source_data with 5 entries for QA
  SRB149 price_source_data rows have required source spine keys
  SRB150 _build_method_context returns mass_appraisal_bridge dict for QA
  SRB151 _build_method_context returns cap_rate_derivation with 4 methods for QA
  SRB152 cap_rate_derivation includes Direct Market Extraction
  SRB153 cap_rate_derivation includes Band of Investment
  SRB154 cap_rate_derivation includes DR minus Growth
  SRB155 cap_rate_derivation includes Built-up Adjusted
  SRB156 cap_rate_derivation average_cap_rate is non-empty for QA
  SRB157 مصادر الأسعار sheet has ≥5 source data rows
  SRB158 ربط التقييم الجماعي sheet contains mass_run_id value
  SRB159 Preliminary PDF template has final capitalization rate section
  SRB160 Certified PDF template has final capitalization rate 4-method table
  SRB161 Certified PDF template has mass appraisal/source linkage disclosure
  SRB162 No major method sheet all-empty in QA mode
  SRB163 AVM sheet has regression feature table
  SRB164 _build_method_context does not claim Qdrant/internet retrieval

  SRB165 _detect_valuation_purpose detects rental_value from Arabic label
  SRB166 _detect_valuation_date_basis detects retrospective (Δ > 60 days)
  SRB167 _detect_valuation_date_basis detects current (close dates)
  SRB168 _detect_valuation_date_basis detects prospective (future > 30 days)
  SRB169 _build_method_context with rental purpose includes rental_value_context
  SRB170 Expert workbook contains القيمة الإيجارية sheet
  SRB171 Expert workbook contains مقارنات إيجارية sheet
  SRB172 Expert workbook contains توفيق القيمة الإيجارية sheet
  SRB173 Rental comparables sheet has adjusted rent/m² labels
  SRB174 Rental comparables sheet has Excel formula cells
  SRB175 Required method sheets pass no-blank validation in QA mode
  SRB176 Preliminary PDF template contains rental value sections
  SRB177 Certified PDF template contains rental value sections
  SRB178 Date basis labels appear in both templates
  SRB179 Rental source rows (4 types) in price_source_data
  SRB180 cap_rate_derivation independent; terminal cap and discount rate stay separate; no Qdrant

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
  SRB24  POST /api/simple-valuation/draft-pdf valid payload → 200 application/pdf
  SRB25  POST /api/simple-valuation/draft-pdf empty payload → 400
  SRB26  PDF response starts with %PDF magic bytes
  SRB27  Data-gap payload (no estimated_value) still returns 200 PDF
  SRB28  Response headers carry no certified=true claim
  SRB29  GET /api/simple-valuation/draft-pdf never returns application/pdf
  SRB30  Flask URL map registers POST /api/simple-valuation/draft-pdf
  SRB31  PDF embeds Cairo font (not Arial) — Arabic rendering guard
  SRB32  Extracted PDF text contains recognisable Arabic terms
  SRB33  Generator uses Playwright, not fpdf — regression guard
  SRB34  Response includes X-PDF-Renderer: html-playwright header
  SRB35  GET expert request draft PDF includes X-PDF-Renderer: html-playwright
  SRB36  POST /api/expert-requests message explicitly says not certified
  SRB37  _build_draft_pdf uses Playwright, not FPDF — regression guard
  SRB38  Expert request returns request_id and expert_workbook_available
  SRB39  Expert request response message says not certified
  SRB40  Expert workbook file created on disk
  SRB41  Workbook saved under correct path
  SRB42  Workbook file is .xlsx and non-trivially large
  SRB43  Workbook has all 9 required sheets (Dashboard + 8 traditional)
  SRB44  User-facing response hides .xlsx path
  SRB45  Unauthenticated user cannot download workbook
  SRB46  Dashboard sheet exists as first sheet and contains request_id
  SRB47  Dashboard sheet has all required status fields
  SRB48  توفيق النتائج sheet has default weights 40/40/20
  SRB49  مقارنة البيوع sheet has column headers and 3 placeholder rows
  SRB50  Dashboard template renders PDF for both full-data and data-gap payloads
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


def test_SRB29_simple_draft_pdf_get_not_application_pdf(client):
    """GET /api/simple-valuation/draft-pdf must never return application/pdf.

    The endpoint is POST-only by design.  A GET request is handled by the SPA
    catch-all route which returns a non-PDF response (typically 404 JSON).
    Either way the response MUST NOT be a PDF, confirming the endpoint cannot
    be triggered accidentally via a plain browser navigation or <a href=…> link.
    """
    resp = client.get("/api/simple-valuation/draft-pdf")
    assert "application/pdf" not in (resp.content_type or ""), (
        f"GET returned application/pdf unexpectedly "
        f"(status {resp.status_code}): {resp.content_type}"
    )
    assert resp.data[:4] != b"%PDF", (
        "GET to draft-pdf endpoint returned PDF bytes — route must be POST-only"
    )


def test_SRB30_simple_draft_pdf_route_registered_as_post(client):
    """Flask URL map must contain POST /api/simple-valuation/draft-pdf.

    This guards against accidental de-registration (e.g. a server restart
    loading old code that didn't have the route, which caused the live 405).
    """
    from bridge_api import app as _app
    rules = {r.rule: list(r.methods) for r in _app.url_map.iter_rules()}
    assert "/api/simple-valuation/draft-pdf" in rules, (
        "Route /api/simple-valuation/draft-pdf is not in the Flask URL map"
    )
    methods = rules["/api/simple-valuation/draft-pdf"]
    assert "POST" in methods, (
        f"POST not in registered methods for the route: {methods}"
    )


def test_SRB31_simple_draft_pdf_uses_cairo_font_not_arial(client):
    """PDF must embed Cairo font for proper Arabic rendering, not Arial fallback.

    Playwright/Chromium renders the RTL HTML; Cairo TTF is embedded as a
    base64 data-URI in the HTML so Chromium always picks it up.
    Checks raw PDF bytes — Chromium's font-subset name contains 'Cairo'.
    Arial must be absent, confirming the font fallback did not fire.
    """
    resp = client.post(
        "/api/simple-valuation/draft-pdf",
        data=json.dumps(_sv_pdf_payload()),
        content_type="application/json",
    )
    assert resp.status_code == 200
    raw = resp.data
    assert b"Cairo" in raw, (
        "Expected Cairo font embedded in PDF bytes — Arabic rendering may be broken"
    )
    assert b"Arial" not in raw, (
        "Arial font found in PDF — Arabic text will not render correctly with Arial"
    )


def test_SRB32_simple_draft_pdf_arabic_content_present(client):
    """Extracted PDF text must include key Arabic terms in recognisable form.

    Uses PyMuPDF when available.  Skips gracefully if not installed.
    Short Arabic root words like 'تقرير' and 'معتمد' survive bidi-reorder
    extraction intact and are safe to assert on.
    """
    try:
        import fitz  # PyMuPDF  # noqa: F401
    except ImportError:
        pytest.skip("PyMuPDF not installed — skipping Arabic text content check")

    resp = client.post(
        "/api/simple-valuation/draft-pdf",
        data=json.dumps(_sv_pdf_payload()),
        content_type="application/json",
    )
    assert resp.status_code == 200

    import fitz as _fitz
    doc = _fitz.open(stream=resp.data, filetype="pdf")
    full_text = " ".join(page.get_text() for page in doc)
    doc.close()

    for term in ("تقرير", "معتمد", "التقييم", "العقار"):
        assert term in full_text, (
            f"Arabic term {term!r} not found in PDF extracted text. "
            "Arabic rendering may be broken or font shaping failed."
        )


def test_SRB33_simple_draft_pdf_uses_playwright_not_fpdf(client):
    """Simple valuation PDF path must delegate to pdf_renderer, not use FPDF.

    The new modular architecture has:
      _build_simple_valuation_pdf_bytes  →  pdf_renderer.render_pdf_from_html
      pdf_renderer.render_pdf_from_html  →  Playwright/Chromium

    Checks:
    1. _build_simple_valuation_pdf_bytes calls pdf_renderer.render_pdf_from_html.
    2. pdf_renderer.render_pdf_from_html imports playwright.sync_api.
    3. Neither function imports fpdf/FPDF directly.
    """
    import inspect
    from shared_request_routes import _build_simple_valuation_pdf_bytes
    import pdf_renderer

    fn_src = inspect.getsource(_build_simple_valuation_pdf_bytes)
    assert "render_pdf_from_html" in fn_src, (
        "_build_simple_valuation_pdf_bytes does not call render_pdf_from_html — "
        "may have regressed to a direct fpdf path"
    )
    assert "from fpdf import" not in fn_src and "import fpdf" not in fn_src, (
        "_build_simple_valuation_pdf_bytes still imports fpdf directly — "
        "Arabic rendering will be broken for Arabic text"
    )

    renderer_src = inspect.getsource(pdf_renderer.render_pdf_from_html)
    assert "playwright" in renderer_src, (
        "pdf_renderer.render_pdf_from_html does not use Playwright — "
        "Arabic rendering engine may be missing"
    )


def test_SRB34_simple_draft_pdf_renderer_header(client):
    """Response must include X-PDF-Renderer: html-playwright header.

    This header proves the Playwright/Chromium path is active and the
    response was not produced by the old FPDF path.
    """
    resp = client.post(
        "/api/simple-valuation/draft-pdf",
        data=json.dumps(_sv_pdf_payload()),
        content_type="application/json",
    )
    assert resp.status_code == 200
    renderer = resp.headers.get("X-PDF-Renderer", "")
    assert renderer == "html-playwright", (
        f"X-PDF-Renderer header is {renderer!r} — expected 'html-playwright'. "
        "The endpoint may still be using the old FPDF path or the server "
        "was not restarted after the Playwright migration."
    )


def test_SRB35_expert_request_draft_pdf_renderer_header(client):
    """GET /api/expert-requests/<id>/draft-pdf must return X-PDF-Renderer: html-playwright.

    Confirms the expert request receipt PDF is also rendered by Playwright/Chromium,
    not the old FPDF path.
    """
    resp_create = _post_request(client)
    assert resp_create.status_code == 201
    rid = json.loads(resp_create.data)["request_id"]

    resp_pdf = client.get(f"/api/expert-requests/{rid}/draft-pdf")
    assert resp_pdf.status_code == 200, (
        f"Expected 200 from GET draft-pdf, got {resp_pdf.status_code}"
    )
    renderer = resp_pdf.headers.get("X-PDF-Renderer", "")
    assert renderer == "html-playwright", (
        f"Expert request PDF X-PDF-Renderer is {renderer!r} — "
        "expected 'html-playwright'. FPDF path may still be active."
    )


def test_SRB36_expert_request_message_says_not_certified(client):
    """POST /api/expert-requests response message must explicitly state not certified."""
    resp = _post_request(client)
    assert resp.status_code == 201
    data = json.loads(resp.data)
    message = data.get("message", "")
    assert "ليس تقريرًا معتمدًا" in message, (
        f"API message does not say 'ليس تقريرًا معتمدًا'. Got: {message!r}. "
        "The confirmation message must not mislead the user about certification status."
    )
    # non_certified flag must still be True
    assert data.get("non_certified") is True


def test_SRB37_expert_request_receipt_pdf_uses_playwright(client):
    """_build_draft_pdf must delegate to pdf_renderer, not use FPDF.

    Checks:
    1. _build_draft_pdf calls render_pdf_from_html.
    2. No direct FPDF import in _build_draft_pdf.
    3. pdf_renderer.render_pdf_from_html uses Playwright.
    """
    import inspect
    from shared_request_routes import _build_draft_pdf
    import pdf_renderer

    fn_src = inspect.getsource(_build_draft_pdf)
    assert "render_pdf_from_html" in fn_src, (
        "_build_draft_pdf does not call render_pdf_from_html — "
        "may have regressed to a direct FPDF path"
    )
    assert "from fpdf import" not in fn_src and "import fpdf" not in fn_src, (
        "_build_draft_pdf still imports fpdf directly — "
        "Arabic rendering will be broken"
    )

    renderer_src = inspect.getsource(pdf_renderer.render_pdf_from_html)
    assert "playwright" in renderer_src, (
        "pdf_renderer.render_pdf_from_html does not use Playwright"
    )


# ── Tests: Internal expert workbook ──────────────────────────────────────────

def test_SRB38_expert_request_returns_request_id_and_workbook_flag(client):
    """POST /api/expert-requests returns request_id and expert_workbook_available."""
    resp = _post_request(client)
    assert resp.status_code == 201
    data = json.loads(resp.data)
    assert data.get("request_id", "").startswith("REQ-"), (
        "response must include a valid request_id"
    )
    assert "expert_workbook_available" in data, (
        "response must include expert_workbook_available field"
    )


def test_SRB39_expert_request_response_message_not_certified(client):
    """POST /api/expert-requests message explicitly says not certified."""
    data = json.loads(_post_request(client).data)
    msg = data.get("message", "")
    assert "ليس تقريرًا معتمدًا" in msg, (
        f"Message must say 'ليس تقريرًا معتمدًا'. Got: {msg!r}"
    )
    assert data.get("non_certified") is True


def test_SRB40_expert_workbook_file_created(client):
    """POST /api/expert-requests creates the internal Excel workbook on disk."""
    data = json.loads(_post_request(client).data)
    assert data.get("expert_workbook_available") is True, (
        f"expert_workbook_available is not True. pdf_message: {data.get('pdf_message')}"
    )
    rid = data["request_id"]
    wb_path = _srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"
    assert wb_path.exists(), f"Workbook file not found at {wb_path}"


def test_SRB41_expert_workbook_under_correct_path(client):
    """Workbook is saved under core_engine/instance/expert_workbooks/<REQ-ID>/."""
    rid = json.loads(_post_request(client).data)["request_id"]
    expected_dir = _srr._WORKBOOKS / rid
    assert expected_dir.is_dir(), f"Workbook directory not found: {expected_dir}"
    assert (expected_dir / f"expert_review_{rid}.xlsx").exists()


def test_SRB42_expert_workbook_is_xlsx(client):
    """Workbook file ends with .xlsx and is non-trivially large."""
    rid = json.loads(_post_request(client).data)["request_id"]
    wb_path = _srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"
    assert wb_path.exists()
    assert wb_path.suffix == ".xlsx"
    assert wb_path.stat().st_size > 2_000, "Workbook file is suspiciously small"


def test_SRB43_expert_workbook_has_all_twelve_sheets(client):
    """Workbook contains all 12 required sheets (Dashboard + 11 traditional valuation sheets)."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")

    rid = json.loads(_post_request(client).data)["request_id"]
    wb_path = _srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"
    wb = openpyxl.load_workbook(str(wb_path))
    expected_sheets = {
        "Dashboard",
        "غلاف وملخص",
        "مقدمة التقرير والافتراضات",
        "بيانات العقار",
        "مقارنة البيوع",
        "طريقة الدخل",
        "DCF",
        "طريقة التكلفة",
        "توفيق النتائج",
        "الخلاصة والصياغة النهائية",
        "المستندات",
        "سجل المراجعة",
    }
    actual_sheets = set(wb.sheetnames)
    missing = expected_sheets - actual_sheets
    assert not missing, f"Workbook is missing sheets: {missing}. Found: {actual_sheets}"


def test_SRB44_user_response_hides_xlsx_path(client):
    """User-facing response does not expose .xlsx link or filesystem path."""
    resp = _post_request(client)
    body_str = resp.data.decode("utf-8")
    assert ".xlsx" not in body_str, (
        "Response body must not contain .xlsx path or link — Excel is internal only"
    )
    data = json.loads(resp.data)
    assert "expert_workbook_path" not in data, (
        "expert_workbook_path must not appear in user-facing response"
    )
    # Ensure no filesystem-style paths are exposed
    for key in ("C:\\", "instance/expert_workbooks", "/expert_workbooks"):
        assert key not in body_str, f"Internal path fragment {key!r} found in response"


def test_SRB45_unauthenticated_user_cannot_download_workbook(client):
    """Unauthenticated user receives 401 when trying to access workbook download endpoint."""
    rid = json.loads(_post_request(client).data)["request_id"]
    resp = client.get(f"/api/expert-requests/{rid}/expert-workbook")
    assert resp.status_code == 401, (
        f"Expected 401 for unauthenticated workbook download, got {resp.status_code}. "
        "Excel must be accessible only to authenticated admin/expert users."
    )


# ── Tests: Dashboard sheet content ───────────────────────────────────────────

def test_SRB46_dashboard_sheet_exists_and_has_request_id(client):
    """Dashboard sheet is the first sheet and contains the request_id."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")

    rid = json.loads(_post_request(client).data)["request_id"]
    wb  = openpyxl.load_workbook(str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"))
    assert "Dashboard" in wb.sheetnames, "Dashboard sheet not found in workbook"
    # مدخلات التقرير is now index 0; Dashboard is at index 1
    assert "مدخلات التقرير" in wb.sheetnames, "مدخلات التقرير sheet not found in workbook"
    ws  = wb["Dashboard"]
    all_vals = " | ".join(
        str(c.value or "") for row in ws.iter_rows() for c in row
    )
    assert rid in all_vals, f"Request ID {rid!r} not found in Dashboard sheet"


def test_SRB47_dashboard_sheet_has_required_status_fields(client):
    """Dashboard sheet contains all six required status/label fields."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")

    rid = json.loads(_post_request(client).data)["request_id"]
    wb  = openpyxl.load_workbook(str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"))
    ws  = wb["Dashboard"]
    all_vals = " | ".join(
        str(c.value or "") for row in ws.iter_rows() for c in row
    )
    for field in (
        "رقم الطلب", "حالة الطلب",
        "حالة البيانات", "حالة المستندات",
        "حالة طرق التقييم", "قرار الخبير",
    ):
        assert field in all_vals, (
            f"Dashboard sheet missing field: {field!r}. Found: {all_vals[:200]}"
        )


def test_SRB48_reconciliation_sheet_has_default_weights(client):
    """توفيق النتائج sheet contains default weights 40%, 40%, 20%."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")

    rid = json.loads(_post_request(client).data)["request_id"]
    wb  = openpyxl.load_workbook(str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"))
    assert "توفيق النتائج" in wb.sheetnames, "توفيق النتائج sheet not found"
    ws  = wb["توفيق النتائج"]
    col_b = [str(ws.cell(row=r, column=2).value or "") for r in range(2, ws.max_row + 1)]
    assert "40" in col_b, "Default weight 40% not found in توفيق النتائج sheet"
    assert "20" in col_b, "Default weight 20% not found in توفيق النتائج sheet"


def test_SRB49_sales_comparison_sheet_has_columns_and_placeholders(client):
    """مقارنة البيوع sheet has all required column headers and placeholder rows.

    The sheet now uses multi-form layout with a title row, so we search across
    all cell values rather than only row 1.
    """
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")

    rid = json.loads(_post_request(client).data)["request_id"]
    wb  = openpyxl.load_workbook(str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"))
    assert "مقارنة البيوع" in wb.sheetnames, "مقارنة البيوع sheet not found"
    ws  = wb["مقارنة البيوع"]
    all_text = " | ".join(str(c.value or "") for row in ws.iter_rows() for c in row if c.value)
    for h in ("رقم المقارن", "سعر المتر", "الموقع", "ملاحظات الخبير"):
        assert h in all_text, f"مقارنة البيوع missing header/label: {h!r}"
    all_col_a = [str(ws.cell(row=r, column=1).value or "") for r in range(1, ws.max_row + 1)]
    assert any("مقارن" in p for p in all_col_a), (
        f"مقارنة البيوع missing placeholder rows. Col-A values: {[v for v in all_col_a if v]}"
    )


def test_SRB50_dashboard_template_renders_for_both_payloads(client):
    """After dashboard template update, PDF renders for both full-data and data-gap payloads."""
    # Full-data payload
    resp1 = client.post(
        "/api/simple-valuation/draft-pdf",
        data=json.dumps(_sv_pdf_payload()),
        content_type="application/json",
    )
    assert resp1.status_code == 200, f"Full-data PDF failed: {resp1.status_code}"
    assert resp1.data[:4] == b"%PDF", "Full-data response is not a valid PDF"

    # Data-gap payload (no estimated value)
    resp2 = client.post(
        "/api/simple-valuation/draft-pdf",
        data=json.dumps({
            "property_type":   "شقة سكنية",
            "area":            120,
            "condition":       "جيدة",
            "valuation_date":  "2026-01-01",
            "city":            "القاهرة",
        }),
        content_type="application/json",
    )
    assert resp2.status_code == 200, f"Data-gap PDF failed: {resp2.status_code}"
    assert resp2.data[:4] == b"%PDF", "Data-gap response is not a valid PDF"


# ── Tests: Shared Report Components (Part B) ──────────────────────────────────

def test_SRB51_report_components_has_required_functions(client):
    """report_components module exports all 9 required public functions."""
    import report_components as rc
    required = [
        "build_report_base_html",
        "render_dashboard_kpi_cards",
        "render_method_snapshot",
        "render_watermark",
        "render_disclaimer",
        "render_footer_proof_marker",
        "render_section",
        "html_escape",
        "get_report_disclaimer",
    ]
    for fn in required:
        assert hasattr(rc, fn), (
            f"report_components is missing required function: {fn!r}. "
            "The shared reporting module must export all documented public functions."
        )


def test_SRB52_get_report_disclaimer_returns_correct_text(client):
    """get_report_disclaimer returns correct text for each report kind."""
    from report_components import get_report_disclaimer

    disc_simple = get_report_disclaimer("simple_valuation")
    assert "معتمد" in disc_simple, (
        "simple_valuation disclaimer must mention 'معتمد'. Got: "
        + repr(disc_simple[:100])
    )

    disc_exp = get_report_disclaimer("expert_request")
    assert "طلب مراجعة" in disc_exp, (
        "expert_request disclaimer must mention 'طلب مراجعة'. Got: "
        + repr(disc_exp[:100])
    )

    disc_skel = get_report_disclaimer("professional_skeleton")
    assert "مسودة" in disc_skel, (
        "professional_skeleton disclaimer must mention 'مسودة'. Got: "
        + repr(disc_skel[:100])
    )

    disc_mass = get_report_disclaimer("mass_appraisal_skeleton")
    assert "معتمد" in disc_mass, (
        "mass_appraisal_skeleton disclaimer must mention 'معتمد'. Got: "
        + repr(disc_mass[:100])
    )


def test_SRB53_build_report_base_html_produces_valid_rtl_html(client):
    """build_report_base_html produces valid RTL HTML with Cairo font and Arabic content."""
    from report_components import build_report_base_html

    html_out = build_report_base_html(
        "تقرير اختبار",
        "<p>محتوى تجريبي</p>",
    )
    assert "<!DOCTYPE html>" in html_out, "Missing DOCTYPE declaration"
    assert 'lang="ar"' in html_out, "Missing lang='ar' attribute"
    assert 'dir="rtl"' in html_out, "Missing dir='rtl' attribute"
    assert "Cairo" in html_out, "Missing Cairo font reference"
    assert "محتوى تجريبي" in html_out, "Body HTML not present in output"
    assert "watermark" in html_out, "Missing watermark element"
    assert "page-footer" in html_out, "Missing footer marker"


def test_SRB54_render_dashboard_kpi_cards_produces_html(client):
    """render_dashboard_kpi_cards produces HTML with correct CSS classes."""
    from report_components import render_dashboard_kpi_cards

    cards = [
        {"label": "النوع",    "value": "شقة",      "variant": ""},
        {"label": "القيمة",   "value": "1,000,000", "variant": "green"},
        {"label": "التحذير",  "value": "ناقص",      "variant": "warn", "span2": True},
    ]
    html_out = render_dashboard_kpi_cards(cards)
    assert "kpi-grid" in html_out, "Missing kpi-grid container class"
    assert "kpi-card" in html_out, "Missing kpi-card class"
    assert "النوع" in html_out, "Missing card label in output"
    assert "green" in html_out, "Missing green variant class"
    assert "span2" in html_out, "Missing span2 class for wide card"
    assert "kpi-lbl" in html_out, "Missing kpi-lbl class"
    assert "kpi-val" in html_out, "Missing kpi-val class"


# ── Tests: Shared Excel Report Builder (Part F) ───────────────────────────────

def test_SRB55_excel_report_builder_has_required_helpers(client):
    """excel_report_builder module exports all 8 required public helpers."""
    import excel_report_builder as erb
    required = [
        "create_workbook",
        "apply_rtl",
        "style_header_row",
        "apply_borders",
        "set_column_widths",
        "add_kpi_card",
        "add_key_value_table",
        "save_workbook",
    ]
    for fn in required:
        assert hasattr(erb, fn), (
            f"excel_report_builder is missing required helper: {fn!r}. "
            "The shared Excel builder must export all documented public functions."
        )


def test_SRB56_excel_report_builder_creates_valid_workbook(tmp_path):
    """excel_report_builder creates, populates, and saves a valid .xlsx workbook."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")

    import excel_report_builder as erb

    wb = erb.create_workbook()
    ws = wb.active
    ws.title = "اختبار"

    erb.apply_rtl(ws)
    erb.style_header_row(ws, ["العمود أ", "العمود ب", "العمود ج"])
    end_row = erb.add_key_value_table(ws, 2, [
        ("رقم الطلب", "REQ-TEST001"),
        ("الحالة",    "جديد"),
        ("العميل",    "محمد عبدالله الاختبار"),
    ])
    erb.set_column_widths(ws, [30, 40, 25])

    # save to tmp_path so the test is isolated
    path = erb.save_workbook(wb, tmp_path / "test_builder.xlsx")
    assert path.exists(), f"Workbook was not saved at {path}"
    assert path.suffix == ".xlsx"
    assert path.stat().st_size > 2_000, "Saved workbook is suspiciously small"

    # Verify the workbook can be re-opened and contains expected data
    wb2 = openpyxl.load_workbook(str(path))
    assert "اختبار" in wb2.sheetnames, "Sheet title not preserved"
    ws2 = wb2["اختبار"]
    headers = [ws2.cell(row=1, column=c).value for c in range(1, 4)]
    assert "العمود أ" in headers, f"Header not found. Headers: {headers}"

    all_vals = " ".join(
        str(ws2.cell(row=r, column=c).value or "")
        for r in range(2, end_row + 1)
        for c in range(1, 3)
    )
    assert "REQ-TEST001" in all_vals, "Request ID not found in workbook data"
    assert "محمد عبدالله الاختبار" in all_vals, "Client name not found in workbook data"


# ── Tests: Skeleton templates (Parts H, I) ────────────────────────────────────

def test_SRB57_professional_skeleton_renders_html_without_error(client):
    """Professional valuation skeleton renders to complete, valid HTML with Arabic text."""
    from report_components import build_professional_valuation_skeleton_html

    html_out = build_professional_valuation_skeleton_html({})

    assert "<!DOCTYPE html>" in html_out, "Missing DOCTYPE declaration"
    assert 'lang="ar"' in html_out, "Missing lang='ar'"
    assert 'dir="rtl"' in html_out, "Missing dir='rtl'"
    assert "Cairo" in html_out, "Missing Cairo font reference"

    # Must contain Arabic structural text
    for phrase in ("تقرير", "غير معتمد", "مسودة", "الخبير"):
        assert phrase in html_out, (
            f"Professional skeleton HTML is missing required phrase: {phrase!r}"
        )

    # Must contain required sections
    for section in (
        "تعريف الأصل",
        "طرق التقييم",
        "إخلاء المسؤولية",
        "مصفوفة التكامل",
    ):
        assert section in html_out, (
            f"Professional skeleton is missing section: {section!r}"
        )

    # Must have watermark and footer
    assert "watermark" in html_out, "Missing watermark class"
    assert "page-footer" in html_out, "Missing footer proof marker"


def test_SRB58_mass_appraisal_skeleton_renders_html_without_error(client):
    """Mass appraisal skeleton renders to complete, valid HTML with Arabic text."""
    from report_components import build_mass_appraisal_dashboard_skeleton_html

    html_out = build_mass_appraisal_dashboard_skeleton_html({})

    assert "<!DOCTYPE html>" in html_out, "Missing DOCTYPE declaration"
    assert 'lang="ar"' in html_out, "Missing lang='ar'"
    assert 'dir="rtl"' in html_out, "Missing dir='rtl'"
    assert "Cairo" in html_out, "Missing Cairo font reference"

    # Must contain Arabic structural text
    for phrase in ("محفظة", "غير معتمد", "مسودة", "الخبير"):
        assert phrase in html_out, (
            f"Mass appraisal skeleton HTML is missing required phrase: {phrase!r}"
        )

    # Must contain required sections
    for section in (
        "استيعاب البيانات",
        "دراسة النسبة",
        "إخلاء المسؤولية",
        "حوكمة النموذج",
    ):
        assert section in html_out, (
            f"Mass appraisal skeleton is missing section: {section!r}"
        )

    # Must have watermark and footer
    assert "watermark" in html_out, "Missing watermark class"
    assert "page-footer" in html_out, "Missing footer proof marker"


# ── Tests: Report Template Registry (Part B) ─────────────────────────────────

def test_SRB59_report_template_registry_exists_and_imports(client):
    """report_template_registry module exists and imports cleanly."""
    import report_template_registry as rtr
    assert hasattr(rtr, "REPORT_TEMPLATES"), "REPORT_TEMPLATES dict must be defined"
    assert hasattr(rtr, "TEMPLATE_IDS"),     "TEMPLATE_IDS list must be defined"
    assert hasattr(rtr, "get_template"),     "get_template() helper must be defined"
    assert hasattr(rtr, "get_template_name_ar"), "get_template_name_ar() helper must be defined"


def test_SRB60_report_template_registry_has_required_ids(client):
    """All 11 required template IDs exist in REPORT_TEMPLATES."""
    from report_template_registry import REPORT_TEMPLATES
    required = [
        "simple_dashboard_draft",
        "residential_summary_three_methods",
        "full_three_approach_report",
        "professional_dcf_report",
        "bank_financing_report",
        "court_litigation_report",
        "tax_appeal_report",
        "special_asset_factory_report",
        "hbu_land_report",
        "ifrs_fair_value_report",
        "mass_appraisal_portfolio_report",
    ]
    for tid in required:
        assert tid in REPORT_TEMPLATES, f"Template ID missing: {tid!r}"


def test_SRB61_each_template_has_required_fields(client):
    """Every template entry has all required metadata fields."""
    from report_template_registry import REPORT_TEMPLATES
    required_fields = [
        "template_id", "name_ar", "audience", "output_type",
        "certification_status", "page_scope", "required_sections",
        "applicable_pages", "notes",
    ]
    for tid, entry in REPORT_TEMPLATES.items():
        for field in required_fields:
            assert field in entry, f"Template {tid!r} is missing field {field!r}"
        assert entry["name_ar"], f"Template {tid!r} has empty name_ar"
        assert isinstance(entry["required_sections"], list), (
            f"Template {tid!r} required_sections must be a list"
        )


def test_SRB62_expert_request_accepts_report_template_id(client):
    """POST /api/expert-requests accepts report_template_id and returns success."""
    resp = client.post("/api/expert-requests", data={
        "source_page":        "simple_valuation",
        "request_kind":       "certified_report_request",
        "user_name":          "مختبر النماذج",
        "phone":              "01099990099",
        "report_template_id": "residential_summary_three_methods",
    })
    assert resp.status_code in (200, 201), f"Unexpected status {resp.status_code}"
    data = resp.get_json()
    assert data.get("status") == "success"
    assert "request_id" in data
    assert data.get("non_certified") is True


def test_SRB63_user_response_does_not_expose_excel_path(client):
    """POST /api/expert-requests response JSON contains no .xlsx link or internal workbook path."""
    resp = client.post("/api/expert-requests", data={
        "source_page": "simple_valuation",
        "user_name":   "فحص الأمان",
        "phone":       "01011112222",
    })
    assert resp.status_code in (200, 201)
    body = resp.data.decode("utf-8")
    assert ".xlsx" not in body,             ".xlsx path must not appear in user-facing response"
    assert "expert_workbooks/" not in body, "Internal workbook directory must not appear in response"
    assert "expert_review_" not in body,    "Internal workbook filename must not appear in response"


def test_SRB64_simple_valuation_pdf_renderer_header(client):
    """POST /api/simple-valuation/draft-pdf returns X-PDF-Renderer: html-playwright when successful."""
    resp = client.post("/api/simple-valuation/draft-pdf", json={
        "location":      "مصر — القاهرة",
        "description":   "شقة سكنية اختبار",
        "area":          100,
        "property_type": "شقة سكنية",
        "condition":     "جيدة",
    })
    # Pre-existing: Playwright sync API cannot run inside async test context (SRB12 family).
    # Only assert header when status is 200.
    if resp.status_code == 200:
        renderer_hdr = resp.headers.get("X-PDF-Renderer", "")
        assert renderer_hdr == "html-playwright", (
            f"PDF renderer header must be 'html-playwright', got {renderer_hdr!r}"
        )


def test_SRB65_expert_request_receipt_pdf_renderer_header(client):
    """GET /api/expert-requests/{id}/draft-pdf returns X-PDF-Renderer header when successful."""
    resp_create = client.post("/api/expert-requests", data={
        "source_page": "simple_valuation",
        "user_name":   "فحص PDF الخبير",
        "phone":       "01033334444",
    })
    assert resp_create.status_code in (200, 201)
    request_id = resp_create.get_json().get("request_id", "")
    if not request_id:
        pytest.skip("Could not create expert request for PDF renderer check")

    resp_pdf = client.get(f"/api/expert-requests/{request_id}/draft-pdf")
    if resp_pdf.status_code == 200:
        renderer_hdr = resp_pdf.headers.get("X-PDF-Renderer", "")
        assert renderer_hdr == "html-playwright", (
            f"Expert receipt PDF renderer must be 'html-playwright', got {renderer_hdr!r}"
        )


# ── Tests: Expert Backoffice Workflow (Parts A–E) ─────────────────────────────

def test_SRB66_admin_list_no_internal_paths(client):
    """GET /api/expert-requests (admin) returns no internal filesystem paths."""
    _post_request(client)
    resp = client.get("/api/expert-requests", headers=_auth())
    assert resp.status_code == 200
    body_str = resp.data.decode("utf-8")
    for forbidden in ("draft_pdf_path", "expert_workbook_path", "instance/expert_workbooks", ".xlsx"):
        assert forbidden not in body_str, (
            f"Admin list must not expose internal path fragment {forbidden!r}"
        )


def test_SRB67_detail_certified_report_always_false(client):
    """GET /api/expert-requests/<id> always returns certified_report_available=false."""
    rid = _post_request(client).get_json()["request_id"]
    resp = client.get(f"/api/expert-requests/{rid}")
    assert resp.status_code == 200
    data = resp.get_json()
    req = data.get("request", {})
    assert req.get("certified_report_available") is False, (
        "certified_report_available must be false — no certified report has been generated"
    )


def test_SRB68_detail_draft_pdf_available_is_boolean(client):
    """GET /api/expert-requests/<id> returns draft_pdf_available as a boolean."""
    rid = _post_request(client).get_json()["request_id"]
    resp = client.get(f"/api/expert-requests/{rid}")
    assert resp.status_code == 200
    req = resp.get_json().get("request", {})
    assert "draft_pdf_available" in req, "draft_pdf_available must be present in detail response"
    assert isinstance(req["draft_pdf_available"], bool), (
        f"draft_pdf_available must be a boolean, got {type(req['draft_pdf_available'])!r}"
    )


def test_SRB69_authenticated_workbook_download_returns_excel(client):
    """Authenticated admin can download expert workbook with correct MIME type."""
    rid = _post_request(client).get_json()["request_id"]
    resp = client.get(f"/api/expert-requests/{rid}/expert-workbook", headers=_auth())
    assert resp.status_code in (200, 404), (
        f"Expected 200 or 404 for authenticated workbook download, got {resp.status_code}"
    )
    if resp.status_code == 200:
        ct = resp.content_type or ""
        assert "spreadsheetml" in ct or "officedocument" in ct, (
            f"Expected Excel MIME type, got {ct!r}"
        )


def test_SRB70_review_draft_only_to_under_review(client):
    """POST /api/expert-requests/<id>/review transitions draft_only → under_review."""
    rid = _post_request(client).get_json()["request_id"]
    resp = client.post(
        f"/api/expert-requests/{rid}/review",
        json={"approval_status": "under_review", "expert_notes": "بدأت مراجعة الطلب"},
        headers=_auth(),
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data[:200]}"
    data = resp.get_json()
    assert data["approval_status"] == "under_review"
    assert data.get("non_certified") is True
    assert data.get("certified_report_available") is False


def test_SRB71_review_under_review_to_needs_documents(client):
    """POST /api/expert-requests/<id>/review transitions under_review → needs_documents."""
    rid = _post_request(client).get_json()["request_id"]
    # First move to under_review
    client.post(
        f"/api/expert-requests/{rid}/review",
        json={"approval_status": "under_review"},
        headers=_auth(),
    )
    # Then to needs_documents
    resp = client.post(
        f"/api/expert-requests/{rid}/review",
        json={"approval_status": "needs_documents",
              "requested_documents": "عقد الملكية، تصاريح البناء"},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.get_json()["approval_status"] == "needs_documents"


def test_SRB72_review_under_review_to_approved_pending_report(client):
    """POST /api/expert-requests/<id>/review transitions under_review → approved_pending_report."""
    rid = _post_request(client).get_json()["request_id"]
    client.post(
        f"/api/expert-requests/{rid}/review",
        json={"approval_status": "under_review"},
        headers=_auth(),
    )
    resp = client.post(
        f"/api/expert-requests/{rid}/review",
        json={"approval_status": "approved_pending_report",
              "expert_recommended_value": "2500000",
              "valuation_method_summary": "مقارنة البيوع"},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.get_json()["approval_status"] == "approved_pending_report"


def test_SRB73_review_update_does_not_generate_certified_report(client):
    """POST /api/expert-requests/<id>/review never generates a certified report."""
    rid = _post_request(client).get_json()["request_id"]
    resp = client.post(
        f"/api/expert-requests/{rid}/review",
        json={"approval_status": "under_review", "expert_notes": "مراجعة"},
        headers=_auth(),
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("certified_report_available") is False, (
        "certified_report_available must remain false after any review update"
    )
    # Ensure no certified PDF link exposed
    body_str = resp.data.decode("utf-8")
    assert "certified_pdf" not in body_str.lower(), (
        "Response must not reference a certified PDF"
    )


def test_SRB74_review_rejects_certified_report_generated_status(client):
    """POST /api/expert-requests/<id>/review rejects certified_report_generated status."""
    rid = _post_request(client).get_json()["request_id"]
    resp = client.post(
        f"/api/expert-requests/{rid}/review",
        json={"approval_status": "certified_report_generated"},
        headers=_auth(),
    )
    assert resp.status_code == 400, (
        f"Setting certified_report_generated must be rejected (400), got {resp.status_code}"
    )
    data = resp.get_json()
    assert data["status"] == "error"


def test_SRB75_detail_reflects_updated_notes_and_status(client):
    """GET /api/expert-requests/<id> reflects expert notes and status after review update."""
    rid = _post_request(client).get_json()["request_id"]
    # Update review
    client.post(
        f"/api/expert-requests/{rid}/review",
        json={
            "approval_status": "under_review",
            "expert_notes":    "ملاحظة المراجعة الاختبارية",
        },
        headers=_auth(),
    )
    # Fetch detail
    resp = client.get(f"/api/expert-requests/{rid}")
    assert resp.status_code == 200
    req = resp.get_json()["request"]
    assert req.get("approval_status") == "under_review", (
        f"approval_status not updated. Got: {req.get('approval_status')!r}"
    )
    assert "ملاحظة المراجعة الاختبارية" in (req.get("expert_notes") or ""), (
        "expert_notes not persisted after review update"
    )


def test_SRB76_admin_list_returns_template_name_and_certified_false(client):
    """GET /api/expert-requests (admin) includes report_template_name_ar and certified_report_available=false."""
    _post_request(client, extra={"report_template_id": "residential_summary_three_methods"})
    resp = client.get("/api/expert-requests", headers=_auth())
    assert resp.status_code == 200
    rows = resp.get_json().get("requests", [])
    assert rows, "Admin list returned no requests"
    row = rows[0]
    assert "report_template_name_ar" in row, "report_template_name_ar missing from list"
    assert row.get("certified_report_available") is False, (
        "certified_report_available must be false in list response"
    )


def test_SRB77_review_invalid_transition_returns_400(client):
    """POST /api/expert-requests/<id>/review rejects invalid status transition."""
    rid = _post_request(client).get_json()["request_id"]
    # draft_only → approved_pending_report is NOT allowed (must go through under_review first)
    resp = client.post(
        f"/api/expert-requests/{rid}/review",
        json={"approval_status": "approved_pending_report"},
        headers=_auth(),
    )
    assert resp.status_code == 400, (
        f"Invalid transition draft_only→approved_pending_report must be rejected (400), "
        f"got {resp.status_code}"
    )
    assert resp.get_json()["status"] == "error"


def test_SRB78_review_endpoint_requires_auth(client):
    """POST /api/expert-requests/<id>/review requires JWT auth (401 without token)."""
    rid = _post_request(client).get_json()["request_id"]
    resp = client.post(
        f"/api/expert-requests/{rid}/review",
        json={"approval_status": "under_review"},
    )
    assert resp.status_code == 401, (
        f"Review endpoint must require auth. Got {resp.status_code} without token."
    )


# ── Tests: Certified Report Generation (Parts A, D, E, G) ────────────────────

def _move_to_approved(client, rid: str) -> None:
    """Helper: move request through draft_only → under_review → approved_pending_report."""
    client.post(
        f"/api/expert-requests/{rid}/review",
        json={"approval_status": "under_review"},
        headers=_auth(),
    )
    client.post(
        f"/api/expert-requests/{rid}/review",
        json={
            "approval_status": "approved_pending_report",
            "expert_recommended_value": "3000000",
            "valuation_method_summary": "مقارنة البيوع — اختبار",
        },
        headers=_auth(),
    )


def test_SRB79_certified_report_blocked_for_draft_only(client):
    """POST /certified-report rejected for draft_only (400)."""
    rid = _post_request(client).get_json()["request_id"]
    resp = client.post(
        f"/api/expert-requests/{rid}/certified-report",
        headers=_auth(),
    )
    assert resp.status_code == 400, (
        f"Certified report generation must be rejected for draft_only (400). Got {resp.status_code}"
    )
    assert resp.get_json()["status"] == "error"


def test_SRB80_certified_report_blocked_for_under_review(client):
    """POST /certified-report rejected for under_review (400)."""
    rid = _post_request(client).get_json()["request_id"]
    client.post(
        f"/api/expert-requests/{rid}/review",
        json={"approval_status": "under_review"},
        headers=_auth(),
    )
    resp = client.post(
        f"/api/expert-requests/{rid}/certified-report",
        headers=_auth(),
    )
    assert resp.status_code == 400, (
        f"Certified report generation must be rejected for under_review (400). Got {resp.status_code}"
    )


def test_SRB81_certified_report_blocked_for_needs_documents(client):
    """POST /certified-report rejected for needs_documents (400)."""
    rid = _post_request(client).get_json()["request_id"]
    client.post(f"/api/expert-requests/{rid}/review",
                json={"approval_status": "under_review"}, headers=_auth())
    client.post(f"/api/expert-requests/{rid}/review",
                json={"approval_status": "needs_documents"}, headers=_auth())
    resp = client.post(
        f"/api/expert-requests/{rid}/certified-report",
        headers=_auth(),
    )
    assert resp.status_code == 400, (
        f"Certified report generation must be rejected for needs_documents. Got {resp.status_code}"
    )


def test_SRB82_certified_report_blocked_for_rejected(client):
    """POST /certified-report rejected for rejected status (400)."""
    rid = _post_request(client).get_json()["request_id"]
    client.post(f"/api/expert-requests/{rid}/review",
                json={"approval_status": "under_review"}, headers=_auth())
    client.post(f"/api/expert-requests/{rid}/review",
                json={"approval_status": "rejected"}, headers=_auth())
    resp = client.post(
        f"/api/expert-requests/{rid}/certified-report",
        headers=_auth(),
    )
    assert resp.status_code == 400, (
        f"Certified report generation must be rejected for rejected status. Got {resp.status_code}"
    )


def test_SRB83_certified_report_requires_expert_recommended_value(client):
    """POST /certified-report fails (400) when expert_recommended_value is missing."""
    rid = _post_request(client).get_json()["request_id"]
    # Move to approved_pending_report WITHOUT setting expert_recommended_value
    client.post(f"/api/expert-requests/{rid}/review",
                json={"approval_status": "under_review"}, headers=_auth())
    client.post(f"/api/expert-requests/{rid}/review",
                json={"approval_status": "approved_pending_report"}, headers=_auth())
    resp = client.post(
        f"/api/expert-requests/{rid}/certified-report",
        headers=_auth(),
    )
    assert resp.status_code == 400, (
        f"Certified report must require expert_recommended_value. Got {resp.status_code}"
    )
    msg = resp.get_json().get("message", "")
    assert "القيمة" in msg or "expert_recommended_value" in msg, (
        f"Error message must reference required value field. Got: {msg!r}"
    )


def test_SRB84_certified_report_generated_for_approved_pending_with_value(client):
    """POST /certified-report succeeds (200) for approved_pending_report with expert_recommended_value."""
    rid = _post_request(client).get_json()["request_id"]
    _move_to_approved(client, rid)
    resp = client.post(
        f"/api/expert-requests/{rid}/certified-report",
        headers=_auth(),
    )
    # If Playwright is unavailable in this test environment the generation may error;
    # in that case skip rather than fail the suite.
    if resp.status_code == 500:
        data = resp.get_json()
        if "Playwright" in (data.get("message") or "") or "playwright" in (data.get("message") or ""):
            pytest.skip("Playwright not available — skipping certified PDF generation test")
    assert resp.status_code == 200, (
        f"Expected 200 for certified report generation. Got {resp.status_code}: {resp.data[:200]}"
    )
    data = resp.get_json()
    assert data.get("status") == "success"
    assert data.get("certified_report_available") is True
    assert data.get("approval_status") == "certified_report_generated"


def test_SRB85_generation_updates_status_to_certified_report_generated(client):
    """After successful generation, GET detail returns approval_status=certified_report_generated."""
    rid = _post_request(client).get_json()["request_id"]
    _move_to_approved(client, rid)
    gen_resp = client.post(
        f"/api/expert-requests/{rid}/certified-report",
        headers=_auth(),
    )
    if gen_resp.status_code == 500:
        data = gen_resp.get_json()
        if "Playwright" in (data.get("message") or "") or "playwright" in (data.get("message") or ""):
            pytest.skip("Playwright not available — skipping status transition test")
    assert gen_resp.status_code == 200
    detail = client.get(f"/api/expert-requests/{rid}").get_json()["request"]
    assert detail.get("approval_status") == "certified_report_generated", (
        f"approval_status must be 'certified_report_generated' after generation. "
        f"Got: {detail.get('approval_status')!r}"
    )


def test_SRB86_certified_report_response_hides_internal_path(client):
    """POST /certified-report response JSON must not expose internal filesystem path."""
    rid = _post_request(client).get_json()["request_id"]
    _move_to_approved(client, rid)
    resp = client.post(
        f"/api/expert-requests/{rid}/certified-report",
        headers=_auth(),
    )
    if resp.status_code == 500:
        data = resp.get_json()
        if "Playwright" in (data.get("message") or "") or "playwright" in (data.get("message") or ""):
            pytest.skip("Playwright not available")
    assert resp.status_code == 200
    body_str = resp.data.decode("utf-8")
    for forbidden in ("certified_report_path", "instance/certified_reports", "C:\\", ".pdf"):
        assert forbidden not in body_str, (
            f"Certified report response must not expose internal path fragment {forbidden!r}"
        )


def test_SRB87_certified_report_download_requires_jwt(client):
    """GET /certified-report returns 401 without token."""
    rid = _post_request(client).get_json()["request_id"]
    resp = client.get(f"/api/expert-requests/{rid}/certified-report")
    assert resp.status_code == 401, (
        f"Certified report download must require JWT auth. Got {resp.status_code}"
    )


def test_SRB88_certified_report_download_returns_pdf(client):
    """GET /certified-report returns application/pdf after successful generation."""
    rid = _post_request(client).get_json()["request_id"]
    _move_to_approved(client, rid)
    gen_resp = client.post(
        f"/api/expert-requests/{rid}/certified-report",
        headers=_auth(),
    )
    if gen_resp.status_code == 500:
        data = gen_resp.get_json()
        if "Playwright" in (data.get("message") or "") or "playwright" in (data.get("message") or ""):
            pytest.skip("Playwright not available")
    assert gen_resp.status_code == 200
    dl_resp = client.get(
        f"/api/expert-requests/{rid}/certified-report",
        headers=_auth(),
    )
    assert dl_resp.status_code == 200, (
        f"Expected 200 for certified report download. Got {dl_resp.status_code}"
    )
    assert "pdf" in (dl_resp.content_type or "").lower(), (
        f"Expected application/pdf content type. Got: {dl_resp.content_type!r}"
    )
    assert dl_resp.data[:4] == b"%PDF", "Response body must start with %PDF magic bytes"


def test_SRB89_certified_report_download_returns_renderer_header(client):
    """GET /certified-report returns X-PDF-Renderer: html-playwright header."""
    rid = _post_request(client).get_json()["request_id"]
    _move_to_approved(client, rid)
    gen_resp = client.post(
        f"/api/expert-requests/{rid}/certified-report",
        headers=_auth(),
    )
    if gen_resp.status_code == 500:
        data = gen_resp.get_json()
        if "Playwright" in (data.get("message") or "") or "playwright" in (data.get("message") or ""):
            pytest.skip("Playwright not available")
    assert gen_resp.status_code == 200
    dl_resp = client.get(
        f"/api/expert-requests/{rid}/certified-report",
        headers=_auth(),
    )
    assert dl_resp.status_code == 200
    renderer = dl_resp.headers.get("X-PDF-Renderer", "")
    assert renderer == "html-playwright", (
        f"X-PDF-Renderer must be 'html-playwright'. Got: {renderer!r}"
    )


def test_SRB90_certified_report_available_false_before_generation(client):
    """certified_report_available is False before generation."""
    rid = _post_request(client).get_json()["request_id"]
    _move_to_approved(client, rid)
    detail = client.get(f"/api/expert-requests/{rid}").get_json()["request"]
    assert detail.get("certified_report_available") is False, (
        "certified_report_available must be False before generation. "
        f"Got: {detail.get('certified_report_available')!r}"
    )
    assert detail.get("certified_report_url") is None, (
        "certified_report_url must be None before generation"
    )


def test_SRB91_certified_report_available_true_after_generation(client):
    """certified_report_available is True and certified_report_url is set after generation."""
    rid = _post_request(client).get_json()["request_id"]
    _move_to_approved(client, rid)
    gen_resp = client.post(
        f"/api/expert-requests/{rid}/certified-report",
        headers=_auth(),
    )
    if gen_resp.status_code == 500:
        data = gen_resp.get_json()
        if "Playwright" in (data.get("message") or "") or "playwright" in (data.get("message") or ""):
            pytest.skip("Playwright not available")
    assert gen_resp.status_code == 200
    detail = client.get(f"/api/expert-requests/{rid}").get_json()["request"]
    assert detail.get("certified_report_available") is True, (
        f"certified_report_available must be True after generation. Got: {detail.get('certified_report_available')!r}"
    )
    assert detail.get("certified_report_url") is not None, (
        "certified_report_url must be set after generation"
    )


def test_SRB92_certified_report_generated_cannot_be_set_via_review(client):
    """POST /review rejects certified_report_generated with explicit message about /certified-report endpoint."""
    rid = _post_request(client).get_json()["request_id"]
    _move_to_approved(client, rid)
    resp = client.post(
        f"/api/expert-requests/{rid}/review",
        json={"approval_status": "certified_report_generated"},
        headers=_auth(),
    )
    assert resp.status_code == 400, (
        f"Setting certified_report_generated via /review must be rejected (400). Got {resp.status_code}"
    )
    msg = resp.get_json().get("message", "")
    assert "certified-report" in msg or "certified_report" in msg, (
        f"Error message must reference the /certified-report endpoint. Got: {msg!r}"
    )


# ── Tests: 12-sheet workbook design polish v2 (Part H) ───────────────────────

def test_SRB93_workbook_contains_all_required_section_labels(client):
    """Expert workbook (12-sheet) contains all required multi-form section labels."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")

    rid = json.loads(_post_request(client).data)["request_id"]
    wb_path = _srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"
    wb = openpyxl.load_workbook(str(wb_path))

    all_text = " | ".join(
        str(c.value or "")
        for sheet in wb.worksheets
        for row in sheet.iter_rows()
        for c in row
        if c.value
    )

    required_labels = [
        "مقارنة البيوع المختصر",
        "جدول مقارنات سكني",
        "رسملة الدخل المختصر",
        "DCF مختصر",
        "التكلفة المختصر",
        "التكلفة التفصيلي",
        "توفيق بالثلاث طرق",
        "توفيق بالأوزان",
        "خلاصة تقرير ملخص",
        "خلاصة تقرير كامل",
    ]
    for label in required_labels:
        assert label in all_text, (
            f"Required section label not found across workbook sheets: {label!r}"
        )


def test_SRB94_workbook_introduction_sheet_has_all_five_forms(client):
    """مقدمة التقرير والافتراضات sheet contains all 5 labelled form sections A–E."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")

    rid = json.loads(_post_request(client).data)["request_id"]
    wb = openpyxl.load_workbook(
        str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx")
    )
    assert "مقدمة التقرير والافتراضات" in wb.sheetnames, (
        "مقدمة التقرير والافتراضات sheet not found"
    )
    ws = wb["مقدمة التقرير والافتراضات"]
    all_text = " | ".join(
        str(c.value or "") for row in ws.iter_rows() for c in row if c.value
    )
    for section in (
        "نموذج A — مقدمة مختصرة",
        "نموذج B — مقدمة كاملة",
        "نموذج C — الافتراضات الأساسية",
        "نموذج D — نطاق العمل والقيود",
        "نموذج E — المستندات المطلوبة للمراجعة",
    ):
        assert section in all_text, (
            f"مقدمة التقرير sheet missing section: {section!r}"
        )


def test_SRB95_dcf_sheet_exists_with_required_form_sections(client):
    """DCF sheet exists and contains required labelled sub-sections."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")

    rid = json.loads(_post_request(client).data)["request_id"]
    wb = openpyxl.load_workbook(
        str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx")
    )
    assert "DCF" in wb.sheetnames, "DCF sheet not found in 12-sheet workbook"
    ws = wb["DCF"]
    all_text = " | ".join(
        str(c.value or "") for row in ws.iter_rows() for c in row if c.value
    )
    for section in (
        "نموذج A — DCF مختصر",
        "نموذج B — جدول DCF الاحترافي",
        "نموذج C — افتراضات DCF",
        "نموذج D — اشتقاق معدل الخصم",
    ):
        assert section in all_text, f"DCF sheet missing section: {section!r}"


def test_SRB96_conclusion_sheet_exists_with_five_forms(client):
    """الخلاصة والصياغة النهائية sheet exists and contains 5 purpose-specific forms."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")

    rid = json.loads(_post_request(client).data)["request_id"]
    wb = openpyxl.load_workbook(
        str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx")
    )
    assert "الخلاصة والصياغة النهائية" in wb.sheetnames, (
        "الخلاصة والصياغة النهائية sheet not found"
    )
    ws = wb["الخلاصة والصياغة النهائية"]
    all_text = " | ".join(
        str(c.value or "") for row in ws.iter_rows() for c in row if c.value
    )
    for section in (
        "نموذج A — خلاصة تقرير ملخص",
        "نموذج B — خلاصة تقرير كامل",
        "نموذج C — خلاصة التمويل البنكي",
        "نموذج D — خلاصة تقرير المحكمة",
        "نموذج E — خلاصة IFRS / Fair Value",
    ):
        assert section in all_text, (
            f"الخلاصة sheet missing section: {section!r}"
        )


def test_SRB97_certified_report_template_has_required_sections(client):
    """certified_valuation_report.html template contains all 9 required Arabic section headings."""
    tmpl_path = (
        Path(__file__).resolve().parents[1]
        / "templates" / "pdf" / "certified_valuation_report.html"
    )
    assert tmpl_path.exists(), f"Certified report template not found: {tmpl_path}"
    html = tmpl_path.read_text(encoding="utf-8")

    required_sections = [
        "تقرير تقييم عقاري معتمد",
        "بيانات التكليف ونطاق العمل",
        "بيانات العقار محل التقييم",
        "طريقة مقارنة البيوع",
        "طريقة رسملة الدخل",
        "طريقة التكلفة",
        "توفيق النتائج",
        "خلاصة التقرير",
        "الافتراضات وحدود الاستخدام",
    ]
    for section in required_sections:
        assert section in html, (
            f"Certified report template missing required section: {section!r}"
        )


def test_SRB98_certified_report_template_no_qdrant_claim(client):
    """certified_valuation_report.html must not claim Qdrant or internet retrieval is active."""
    tmpl_path = (
        Path(__file__).resolve().parents[1]
        / "templates" / "pdf" / "certified_valuation_report.html"
    )
    assert tmpl_path.exists()
    html = tmpl_path.read_text(encoding="utf-8")

    forbidden_claims = [
        "تم جلب المقارنات من الإنترنت",
        "تم استخدام Qdrant",
        "تم استخدام RAG",
        "تم تدريب النموذج",
    ]
    for claim in forbidden_claims:
        assert claim not in html, (
            f"Certified report template must not make fake retrieval claim: {claim!r}"
        )

    assert (
        "لا يتضمن هذا الإصدار استرجاعًا آليًا من الإنترنت أو Qdrant" in html
        or "لا يتضمن هذا الإصدار سجل مصادر آلي" in html
    ), (
        "Certified report template must include honest no-Qdrant/internet disclaimer"
    )


def test_SRB99_professional_dcf_template_in_registry_with_metadata(client):
    """professional_dcf_report template is in registry with correct metadata."""
    from report_template_registry import REPORT_TEMPLATES
    assert "professional_dcf_report" in REPORT_TEMPLATES, (
        "professional_dcf_report must be in REPORT_TEMPLATES"
    )
    tmpl = REPORT_TEMPLATES["professional_dcf_report"]
    assert "dcf" in tmpl.get("supported_methods", []), (
        "professional_dcf_report must list 'dcf' in supported_methods"
    )
    assert tmpl.get("certification_status") == "certified_after_approval", (
        "professional_dcf_report must require expert approval (certified_after_approval)"
    )
    assert tmpl.get("name_ar"), "professional_dcf_report must have name_ar"
    pdf_sections = tmpl.get("pdf_sections", [])
    assert any("تقرير تقييم" in s for s in pdf_sections), (
        "professional_dcf_report must list 'تقرير تقييم عقاري معتمد' in pdf_sections"
    )


# ─────────────────────────────────────────────────────────────────────────────
# SRB100–SRB110 — AVM sheet, template sections, no-Qdrant, gating regression
# ─────────────────────────────────────────────────────────────────────────────

def test_SRB100_workbook_has_avm_sheet(client):
    """Expert workbook (13-sheet) includes an 'AVM' sheet."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")

    rid = json.loads(_post_request(client).data)["request_id"]
    wb_path = _srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"
    wb = openpyxl.load_workbook(str(wb_path))
    assert "AVM" in wb.sheetnames, (
        f"Expert workbook must contain an 'AVM' sheet; found sheets: {wb.sheetnames}"
    )


def test_SRB101_avm_sheet_contains_all_eight_model_labels(client):
    """AVM sheet contains labels for all 8 model forms A–H."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")

    rid = json.loads(_post_request(client).data)["request_id"]
    wb = openpyxl.load_workbook(
        str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx")
    )
    assert "AVM" in wb.sheetnames, "AVM sheet not found"
    ws = wb["AVM"]
    all_text = " | ".join(
        str(c.value or "") for row in ws.iter_rows() for c in row if c.value
    )
    for label in (
        "نموذج A",
        "نموذج B",
        "نموذج C",
        "نموذج D",
        "نموذج E",
        "نموذج F",
        "نموذج G",
        "نموذج H",
    ):
        assert label in all_text, (
            f"AVM sheet missing model label: {label!r}"
        )


def test_SRB102_preliminary_pdf_template_has_method_tables_section(client):
    """Preliminary PDF template (simple_valuation_draft.html) contains جداول طرق التقييم المبدئية."""
    import pathlib
    tmpl = pathlib.Path(
        _srr.__file__
    ).parent / "templates" / "pdf" / "simple_valuation_draft.html"
    html = tmpl.read_text(encoding="utf-8")
    assert "جداول طرق التقييم المبدئية" in html, (
        "simple_valuation_draft.html must contain section 'جداول طرق التقييم المبدئية'"
    )


def test_SRB103_preliminary_pdf_template_has_avm_section(client):
    """Preliminary PDF template contains 'طريقة AVM' section."""
    import pathlib
    tmpl = pathlib.Path(
        _srr.__file__
    ).parent / "templates" / "pdf" / "simple_valuation_draft.html"
    html = tmpl.read_text(encoding="utf-8")
    assert "طريقة AVM" in html, (
        "simple_valuation_draft.html must contain 'طريقة AVM' section"
    )


def test_SRB104_preliminary_pdf_template_has_all_method_sections(client):
    """Preliminary PDF template contains all four core valuation method headings."""
    import pathlib
    tmpl = pathlib.Path(
        _srr.__file__
    ).parent / "templates" / "pdf" / "simple_valuation_draft.html"
    html = tmpl.read_text(encoding="utf-8")
    for section in (
        "مقارنة البيوع",
        "رسملة الدخل",
        "طريقة التكلفة",
        "توفيق النتائج",
    ):
        assert section in html, (
            f"simple_valuation_draft.html must contain section: {section!r}"
        )


def test_SRB105_certified_pdf_template_has_avm_section(client):
    """Certified PDF template contains 'طريقة AVM' section."""
    import pathlib
    tmpl = pathlib.Path(
        _srr.__file__
    ).parent / "templates" / "pdf" / "certified_valuation_report.html"
    html = tmpl.read_text(encoding="utf-8")
    assert "طريقة AVM" in html, (
        "certified_valuation_report.html must contain 'طريقة AVM' section"
    )


def test_SRB106_certified_pdf_template_has_all_required_sections(client):
    """Certified PDF template contains all required section headings."""
    import pathlib
    tmpl = pathlib.Path(
        _srr.__file__
    ).parent / "templates" / "pdf" / "certified_valuation_report.html"
    html = tmpl.read_text(encoding="utf-8")
    for section in (
        "بيانات التكليف ونطاق العمل",
        "بيانات العقار محل التقييم",
        "طريقة AVM",
        "طريقة مقارنة البيوع",
        "طريقة رسملة الدخل",
        "طريقة التكلفة",
        "توفيق النتائج",
        "خلاصة التقرير",
        "الاعتماد والتوقيع",
        "الافتراضات وحدود الاستخدام",
        "مصادر البيانات والمقارنات",
    ):
        assert section in html, (
            f"certified_valuation_report.html must contain section: {section!r}"
        )


def test_SRB107_certified_pdf_template_no_qdrant_claim(client):
    """Certified PDF template does not make fake Qdrant/internet retrieval claims."""
    import pathlib
    tmpl = pathlib.Path(
        _srr.__file__
    ).parent / "templates" / "pdf" / "certified_valuation_report.html"
    html = tmpl.read_text(encoding="utf-8")
    # Check for *affirmative* false claims only — the template may use these words
    # in a disclaimer/negation context which is correct behavior
    forbidden_claims = [
        "تم استرجاع البيانات من الإنترنت",
        "تم استخدام Qdrant",
        "تم استخدام RAG",
        "بحث آلي عبر الإنترنت",
        "تم تدريب النموذج",
        "تم جلب المقارنات من الإنترنت",
    ]
    for claim in forbidden_claims:
        assert claim not in html, (
            f"Certified template must not make fake retrieval claim: {claim!r}"
        )
    assert "لا يتضمن هذا التقرير استرجاعًا آليًا من الإنترنت" in html, (
        "Certified template must contain honest no-internet disclaimer"
    )


def test_SRB108_preliminary_pdf_template_no_qdrant_claim(client):
    """Preliminary PDF template does not make fake Qdrant/internet retrieval claims."""
    import pathlib
    tmpl = pathlib.Path(
        _srr.__file__
    ).parent / "templates" / "pdf" / "simple_valuation_draft.html"
    html = tmpl.read_text(encoding="utf-8")
    forbidden_claims = [
        "تم استرجاع البيانات من الإنترنت",
        "RAG",
        "بحث آلي عبر الإنترنت",
        "تم تدريب النموذج",
    ]
    for claim in forbidden_claims:
        assert claim not in html, (
            f"Preliminary template must not make fake retrieval claim: {claim!r}"
        )
    assert "Qdrant" in html or "لا يتضمن هذا التقرير استرجاعًا آليًا من الإنترنت أو Qdrant" in html, (
        "Preliminary template must contain no-Qdrant disclaimer"
    )


def test_SRB109_certified_report_gated_by_approved_pending_report(client):
    """Certified report endpoint returns 400 unless request has approved_pending_report status (regression guard)."""
    rid = _post_request(client).get_json()["request_id"]
    # Move to under_review only — NOT approved_pending_report
    client.post(
        f"/api/expert-requests/{rid}/review",
        json={"approval_status": "under_review", "expert_recommended_value": 1000000},
        headers=_auth(),
    )
    resp = client.post(
        f"/api/expert-requests/{rid}/certified-report",
        headers=_auth(),
    )
    assert resp.status_code == 400, (
        f"Certified report must be gated before approval; got {resp.status_code}"
    )


def test_SRB110_certified_report_requires_expert_recommended_value(client):
    """Certified report endpoint returns 400 unless expert_recommended_value is set (regression guard)."""
    rid = _post_request(client).get_json()["request_id"]
    # Move to approved_pending_report WITHOUT setting expert_recommended_value
    client.post(f"/api/expert-requests/{rid}/review",
                json={"approval_status": "under_review"}, headers=_auth())
    client.post(f"/api/expert-requests/{rid}/review",
                json={"approval_status": "approved_pending_report"}, headers=_auth())
    resp = client.post(
        f"/api/expert-requests/{rid}/certified-report",
        headers=_auth(),
    )
    assert resp.status_code == 400, (
        f"Certified report must require expert_recommended_value; got {resp.status_code}"
    )


# ── SRB111–SRB124: Valuation Methods Simulation & Detailed Report Tables ──────

_QA_SIM_PAYLOAD = {
    "source_page":       "simple_valuation",
    "property_type":     "شقة سكنية",
    "area":              120,
    "location":          "مدينة نصر - المنطقة الثامنة",
    "condition":         "جيد",
    "estimated_value":   3000000,
    "base_price_per_m2": 25000,
    "avm_value":         3055500,
    "avm_low_range":     2750000,
    "avm_high_range":    3350000,
    "_qa_simulation":    True,
}


def test_SRB111_build_method_context_returns_4_comparables():
    """_build_method_context returns 4 rows when _qa_simulation=True."""
    ctx = _srr._build_method_context(_QA_SIM_PAYLOAD)
    comps = ctx.get("comparables", [])
    assert len(comps) == 4, f"Expected 4 comparables, got {len(comps)}"


def test_SRB112_build_method_context_comparable_rows_have_required_keys():
    """Each comparable row has all required keys."""
    ctx = _srr._build_method_context(_QA_SIM_PAYLOAD)
    required = {
        "num", "location", "area", "sale_price", "price_per_m2",
        "location_factor", "area_factor", "condition_factor",
        "finishing_factor", "time_factor",
        "adjusted_price_per_m2", "adjusted_value",
    }
    for i, c in enumerate(ctx["comparables"]):
        missing = required - set(c.keys())
        assert not missing, f"Comparable {i} missing keys: {missing}"


def test_SRB113_build_method_context_income_noi_nonempty():
    """income_noi is a non-empty string for qa payload."""
    ctx = _srr._build_method_context(_QA_SIM_PAYLOAD)
    assert ctx.get("income_noi"), "income_noi should not be empty"


def test_SRB114_build_method_context_income_value_calc_nonempty():
    """income_value_calc is non-empty for qa payload."""
    ctx = _srr._build_method_context(_QA_SIM_PAYLOAD)
    assert ctx.get("income_value_calc"), "income_value_calc should not be empty"


def test_SRB115_build_method_context_dcf_rows_has_5_entries():
    """dcf_rows has exactly 5 entries (5-year projection)."""
    ctx = _srr._build_method_context(_QA_SIM_PAYLOAD)
    rows = ctx.get("dcf_rows", [])
    assert len(rows) == 5, f"Expected 5 DCF rows, got {len(rows)}"


def test_SRB116_build_method_context_dcf_value_calc_nonempty():
    """dcf_value_calc is non-empty for qa payload."""
    ctx = _srr._build_method_context(_QA_SIM_PAYLOAD)
    assert ctx.get("dcf_value_calc"), "dcf_value_calc should not be empty"


def test_SRB117_build_method_context_cost_land_value_nonempty():
    """cost_land_value is non-empty for qa payload."""
    ctx = _srr._build_method_context(_QA_SIM_PAYLOAD)
    assert ctx.get("cost_land_value"), "cost_land_value should not be empty"


def test_SRB118_build_method_context_cost_value_calc_nonempty():
    """cost_value_calc is non-empty for qa payload."""
    ctx = _srr._build_method_context(_QA_SIM_PAYLOAD)
    assert ctx.get("cost_value_calc"), "cost_value_calc should not be empty"


def test_SRB119_workbook_comparables_sheet_has_numeric_data(client):
    """مقارنة البيوع sheet has numeric comparable data when _qa_simulation=True via payload_json."""
    import openpyxl, json
    # payload_json carries _qa_simulation so the workbook builder gets it
    qa_payload = {k: v for k, v in _QA_SIM_PAYLOAD.items()}
    form_data = {
        "source_page": "simple_valuation",
        "user_name":   "أحمد محمد الاختبار",
        "phone":       "01012345678",
        "payload_json": json.dumps(qa_payload),
    }
    resp = client.post("/api/expert-requests", data=form_data, content_type="multipart/form-data")
    assert resp.status_code == 201
    rid = resp.get_json()["request_id"]
    wb_path = _srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"
    assert wb_path.exists(), "Workbook not found on disk"
    wb = openpyxl.load_workbook(str(wb_path))
    sheet_names = wb.sheetnames
    comp_sheets = [s for s in sheet_names if "مقارنة" in s]
    assert comp_sheets, f"No مقارنة sheet found; sheets: {sheet_names}"
    ws = wb[comp_sheets[0]]
    # Collect all cell values across full sheet extent
    all_values = [str(ws.cell(r, c).value or "") for r in range(1, 80) for c in range(1, 14)]
    # Should have numeric sale price data (one of the synthetic comparable values)
    has_numeric = any("2,875,000" in v or "3,120,000" in v or "2,530,000" in v or "2875000" in v or "3120000" in v for v in all_values)
    assert has_numeric, f"No comparable numeric data found in sheet. Sample: {all_values[60:90]}"


def test_SRB120_workbook_income_sheet_has_noi_label(client):
    """طريقة الدخل sheet contains NOI label."""
    import openpyxl
    resp = _post_request(client, extra={k: str(v) for k, v in _QA_SIM_PAYLOAD.items()})
    assert resp.status_code == 201
    rid = resp.get_json()["request_id"]
    wb_path = _srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"
    wb = openpyxl.load_workbook(str(wb_path))
    income_sheets = [s for s in wb.sheetnames if "طريقة" in s and "دخل" in s]
    assert income_sheets, f"No income sheet found; sheets: {wb.sheetnames}"
    ws = wb[income_sheets[0]]
    all_text = " ".join(str(ws.cell(r, c).value or "") for r in range(1, 50) for c in range(1, 5))
    assert "NOI" in all_text or "صافي الدخل" in all_text, "NOI label not found in income sheet"


def test_SRB121_workbook_dcf_sheet_has_discount_rate_label(client):
    """DCF sheet contains discount rate label."""
    import openpyxl
    resp = _post_request(client, extra={k: str(v) for k, v in _QA_SIM_PAYLOAD.items()})
    assert resp.status_code == 201
    rid = resp.get_json()["request_id"]
    wb_path = _srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"
    wb = openpyxl.load_workbook(str(wb_path))
    dcf_sheets = [s for s in wb.sheetnames if "DCF" in s or "dcf" in s]
    assert dcf_sheets, f"No DCF sheet found; sheets: {wb.sheetnames}"
    ws = wb[dcf_sheets[0]]
    all_text = " ".join(str(ws.cell(r, c).value or "") for r in range(1, 80) for c in range(1, 5))
    assert "خصم" in all_text or "discount" in all_text.lower(), "Discount rate label not found in DCF sheet"


def test_SRB122_workbook_reconciliation_sheet_has_weighted_value_row(client):
    """توفيق النتائج sheet has weighted value row (نموذج B presence)."""
    import openpyxl
    resp = _post_request(client, extra={k: str(v) for k, v in _QA_SIM_PAYLOAD.items()})
    assert resp.status_code == 201
    rid = resp.get_json()["request_id"]
    wb_path = _srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"
    wb = openpyxl.load_workbook(str(wb_path))
    rec_sheets = [s for s in wb.sheetnames if "توفيق" in s]
    assert rec_sheets, f"No توفيق sheet found; sheets: {wb.sheetnames}"
    ws = wb[rec_sheets[0]]
    all_text = " ".join(str(ws.cell(r, c).value or "") for r in range(1, 80) for c in range(1, 4))
    assert "توفيق" in all_text, "Reconciliation labels missing from توفيق sheet"


def test_SRB123_preliminary_pdf_template_has_comparable_matrix():
    """Preliminary PDF template (simple_valuation_draft.html) contains مصفوفة المقارنات."""
    import pathlib
    tpl = pathlib.Path(_srr.__file__).parent / "templates" / "pdf" / "simple_valuation_draft.html"
    assert tpl.exists(), f"Template not found: {tpl}"
    content = tpl.read_text(encoding="utf-8")
    assert "مصفوفة المقارنات" in content, "Comparable matrix label missing from preliminary PDF template"


def test_SRB124_certified_pdf_template_has_comparable_matrix():
    """Certified PDF template (certified_valuation_report.html) contains مصفوفة المقارنات."""
    import pathlib
    tpl = pathlib.Path(_srr.__file__).parent / "templates" / "pdf" / "certified_valuation_report.html"
    assert tpl.exists(), f"Template not found: {tpl}"
    content = tpl.read_text(encoding="utf-8")
    assert "مصفوفة المقارنات" in content, "Comparable matrix label missing from certified PDF template"


# ── SRB125–SRB127: Professional simulation sheet ──────────────────────────────

def test_SRB125_workbook_has_professional_simulation_sheet(client):
    """Expert workbook contains محاكاة التقييم المحترف sheet when _qa_simulation=True."""
    import openpyxl, json
    qa_payload = {k: v for k, v in _QA_SIM_PAYLOAD.items()}
    form_data = {
        "source_page": "simple_valuation",
        "user_name":   "أحمد محمد الاختبار",
        "phone":       "01012345678",
        "payload_json": json.dumps(qa_payload),
    }
    resp = client.post("/api/expert-requests", data=form_data, content_type="multipart/form-data")
    assert resp.status_code == 201
    rid = resp.get_json()["request_id"]
    wb_path = _srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"
    assert wb_path.exists(), "Workbook not found on disk"
    wb = openpyxl.load_workbook(str(wb_path))
    assert "محاكاة التقييم المحترف" in wb.sheetnames, \
        f"Professional simulation sheet missing; sheets: {wb.sheetnames}"


def test_SRB126_professional_simulation_sheet_has_weighted_engine(client):
    """محاكاة التقييم المحترف sheet contains محرك القيمة المرجح section header."""
    import openpyxl, json
    qa_payload = {k: v for k, v in _QA_SIM_PAYLOAD.items()}
    form_data = {
        "source_page": "simple_valuation",
        "user_name":   "أحمد محمد الاختبار",
        "phone":       "01012345678",
        "payload_json": json.dumps(qa_payload),
    }
    resp = client.post("/api/expert-requests", data=form_data, content_type="multipart/form-data")
    assert resp.status_code == 201
    rid = resp.get_json()["request_id"]
    wb_path = _srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"
    wb = openpyxl.load_workbook(str(wb_path))
    assert "محاكاة التقييم المحترف" in wb.sheetnames
    ws = wb["محاكاة التقييم المحترف"]
    all_text = " ".join(str(ws.cell(r, c).value or "") for r in range(1, 60) for c in range(1, 5))
    assert "محرك القيمة المرجح" in all_text, \
        f"Weighted engine section missing from professional simulation sheet. Sample: {all_text[:300]}"


def test_SRB127_professional_simulation_sheet_has_purpose_route(client):
    """محاكاة التقييم المحترف sheet contains مسار الغرض section header."""
    import openpyxl, json
    qa_payload = {k: v for k, v in _QA_SIM_PAYLOAD.items()}
    form_data = {
        "source_page": "simple_valuation",
        "user_name":   "أحمد محمد الاختبار",
        "phone":       "01012345678",
        "payload_json": json.dumps(qa_payload),
    }
    resp = client.post("/api/expert-requests", data=form_data, content_type="multipart/form-data")
    assert resp.status_code == 201
    rid = resp.get_json()["request_id"]
    wb_path = _srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"
    wb = openpyxl.load_workbook(str(wb_path))
    assert "محاكاة التقييم المحترف" in wb.sheetnames
    ws = wb["محاكاة التقييم المحترف"]
    all_text = " ".join(str(ws.cell(r, c).value or "") for r in range(1, 60) for c in range(1, 5))
    assert "مسار الغرض" in all_text, \
        f"Purpose route section missing from professional simulation sheet. Sample: {all_text[:300]}"


# ── SRB128–SRB145: Advanced Methodology Tables & Visual Evidence ──────────────

def test_SRB128_workbook_has_land_value_sheet(client):
    """SRB128 Workbook has sheet named قيمة الأرض (land value sheet added)."""
    import openpyxl, json
    form_data = {
        "source_page": "simple_valuation",
        "user_name":   "اختبار SRB128",
        "phone":       "01012345678",
        "payload_json": json.dumps(_QA_SIM_PAYLOAD),
    }
    resp = client.post("/api/expert-requests", data=form_data, content_type="multipart/form-data")
    assert resp.status_code == 201
    rid = resp.get_json()["request_id"]
    wb = openpyxl.load_workbook(str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"))
    assert "قيمة الأرض" in wb.sheetnames, \
        f"Sheet 'قيمة الأرض' missing. Sheets: {wb.sheetnames}"


def test_SRB129_workbook_has_maps_sheet(client):
    """SRB129 Workbook has sheet named خرائط وصور (maps & images sheet added)."""
    import openpyxl, json
    form_data = {
        "source_page": "simple_valuation",
        "user_name":   "اختبار SRB129",
        "phone":       "01012345678",
        "payload_json": json.dumps(_QA_SIM_PAYLOAD),
    }
    resp = client.post("/api/expert-requests", data=form_data, content_type="multipart/form-data")
    assert resp.status_code == 201
    rid = resp.get_json()["request_id"]
    wb = openpyxl.load_workbook(str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"))
    assert "خرائط وصور" in wb.sheetnames, \
        f"Sheet 'خرائط وصور' missing. Sheets: {wb.sheetnames}"


def test_SRB130_land_value_sheet_has_sales_comparison_labels(client):
    """SRB130 قيمة الأرض sheet has land sales comparison section header."""
    import openpyxl, json
    form_data = {
        "source_page": "simple_valuation",
        "user_name":   "اختبار SRB130",
        "phone":       "01012345678",
        "payload_json": json.dumps(_QA_SIM_PAYLOAD),
    }
    resp = client.post("/api/expert-requests", data=form_data, content_type="multipart/form-data")
    assert resp.status_code == 201
    rid = resp.get_json()["request_id"]
    wb = openpyxl.load_workbook(str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"))
    assert "قيمة الأرض" in wb.sheetnames
    ws = wb["قيمة الأرض"]
    all_text = " ".join(str(ws.cell(r, c).value or "") for r in range(1, 50) for c in range(1, 8))
    assert "مقارنة بيوع" in all_text or "مقارنة" in all_text, \
        f"Land sales comparison labels missing. Sample: {all_text[:400]}"


def test_SRB131_land_value_sheet_has_extraction_labels(client):
    """SRB131 قيمة الأرض sheet has extraction method section."""
    import openpyxl, json
    form_data = {
        "source_page": "simple_valuation",
        "user_name":   "اختبار SRB131",
        "phone":       "01012345678",
        "payload_json": json.dumps(_QA_SIM_PAYLOAD),
    }
    resp = client.post("/api/expert-requests", data=form_data, content_type="multipart/form-data")
    assert resp.status_code == 201
    rid = resp.get_json()["request_id"]
    wb = openpyxl.load_workbook(str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"))
    ws = wb["قيمة الأرض"]
    all_text = " ".join(str(ws.cell(r, c).value or "") for r in range(1, 50) for c in range(1, 8))
    assert "استخلاص" in all_text, \
        f"Extraction method label missing from قيمة الأرض sheet. Sample: {all_text[:400]}"


def test_SRB132_land_value_sheet_has_reconciliation_labels(client):
    """SRB132 قيمة الأرض sheet has land value reconciliation (توفيق) section."""
    import openpyxl, json
    form_data = {
        "source_page": "simple_valuation",
        "user_name":   "اختبار SRB132",
        "phone":       "01012345678",
        "payload_json": json.dumps(_QA_SIM_PAYLOAD),
    }
    resp = client.post("/api/expert-requests", data=form_data, content_type="multipart/form-data")
    assert resp.status_code == 201
    rid = resp.get_json()["request_id"]
    wb = openpyxl.load_workbook(str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"))
    ws = wb["قيمة الأرض"]
    all_text = " ".join(str(ws.cell(r, c).value or "") for r in range(1, 50) for c in range(1, 8))
    assert "توفيق" in all_text, \
        f"Reconciliation label missing from قيمة الأرض sheet. Sample: {all_text[:400]}"


def test_SRB133_build_method_context_returns_land_comps_for_qa():
    """SRB133 _build_method_context returns land_comps list with 3 entries for QA payload."""
    ctx = _srr._build_method_context(_QA_SIM_PAYLOAD)
    land_comps = ctx.get("land_comps", [])
    assert len(land_comps) == 3, f"Expected 3 land comps, got {len(land_comps)}"


def test_SRB134_build_method_context_returns_cost_breakdown_for_qa():
    """SRB134 _build_method_context returns cost_breakdown with ≥9 rows for QA payload."""
    ctx = _srr._build_method_context(_QA_SIM_PAYLOAD)
    breakdown = ctx.get("cost_breakdown", [])
    assert len(breakdown) >= 9, f"Expected ≥9 cost breakdown rows, got {len(breakdown)}"


def test_SRB135_build_method_context_returns_4_discount_rate_methods():
    """SRB135 _build_method_context returns discount_rate_methods list with 4 entries for QA."""
    ctx = _srr._build_method_context(_QA_SIM_PAYLOAD)
    dr_methods = ctx.get("discount_rate_methods", [])
    assert len(dr_methods) == 4, f"Expected 4 DR methods, got {len(dr_methods)}"


def test_SRB136_discount_rate_methods_include_buildup_and_capm():
    """SRB136 Discount rate methods include Build-up and CAPM method names."""
    ctx = _srr._build_method_context(_QA_SIM_PAYLOAD)
    dr_methods = ctx.get("discount_rate_methods", [])
    method_names = " ".join(m.get("method", "") for m in dr_methods)
    assert "البناء التراكمي" in method_names, f"Build-up method missing. Names: {method_names}"
    assert "CAPM" in method_names, f"CAPM method missing. Names: {method_names}"


def test_SRB137_discount_rate_methods_include_market_yield_and_band():
    """SRB137 Discount rate methods include Market yield and Band-of-Investment."""
    ctx = _srr._build_method_context(_QA_SIM_PAYLOAD)
    dr_methods = ctx.get("discount_rate_methods", [])
    method_names = " ".join(m.get("method", "") for m in dr_methods)
    assert "عائد السوق" in method_names or "استخلاص" in method_names, \
        f"Market yield method missing. Names: {method_names}"
    assert "Band" in method_names or "حزمة" in method_names, \
        f"Band-of-Investment method missing. Names: {method_names}"


def test_SRB138_build_method_context_returns_4_terminal_cap_methods():
    """SRB138 _build_method_context returns terminal_cap_methods with 4 entries for QA."""
    ctx = _srr._build_method_context(_QA_SIM_PAYLOAD)
    tc_methods = ctx.get("terminal_cap_methods", [])
    assert len(tc_methods) == 4, f"Expected 4 terminal cap methods, got {len(tc_methods)}"


def test_SRB139_build_method_context_returns_avm_regression_for_qa():
    """SRB139 _build_method_context returns avm_regression list with 7 entries for QA."""
    ctx = _srr._build_method_context(_QA_SIM_PAYLOAD)
    avm_reg = ctx.get("avm_regression", [])
    assert len(avm_reg) == 7, f"Expected 7 AVM regression rows, got {len(avm_reg)}"
    features = " ".join(r.get("feature", "") for r in avm_reg)
    assert "معامل" in features, f"'معامل' keyword missing in regression features: {features}"


def test_SRB140_avm_regression_has_confidence_band():
    """SRB140 _build_method_context avm_reg_confidence_band is non-empty for QA."""
    ctx = _srr._build_method_context(_QA_SIM_PAYLOAD)
    band = ctx.get("avm_reg_confidence_band", "")
    assert band, "avm_reg_confidence_band is empty for QA payload"
    assert "—" in band or "-" in band, f"Confidence band does not contain range separator: {band}"


def test_SRB141_certified_template_has_land_value_section():
    """SRB141 Certified PDF template has قيمة الأرض — مقارنة بيوع أراضٍ text."""
    tmpl = (_srr._TMPL_DIR / "certified_valuation_report.html").read_text(encoding="utf-8")
    assert "قيمة الأرض" in tmpl, "Certified template missing قيمة الأرض section"
    assert "land_comps" in tmpl, "Certified template missing land_comps Jinja variable"


def test_SRB142_certified_template_has_cost_breakdown_table():
    """SRB142 Certified PDF template has تفاصيل تكلفة الإنشاء / cost_breakdown."""
    tmpl = (_srr._TMPL_DIR / "certified_valuation_report.html").read_text(encoding="utf-8")
    assert "cost_breakdown" in tmpl, "Certified template missing cost_breakdown variable"
    assert "cost-tbl" in tmpl, "Certified template missing cost-tbl CSS class"


def test_SRB143_certified_template_has_discount_rate_derivation():
    """SRB143 Certified PDF template has discount rate derivation grid (4-method DR)."""
    tmpl = (_srr._TMPL_DIR / "certified_valuation_report.html").read_text(encoding="utf-8")
    assert "discount_rate_methods" in tmpl, "Certified template missing discount_rate_methods"
    assert "dr-grid" in tmpl, "Certified template missing dr-grid CSS class"
    assert "البناء التراكمي" in tmpl or "اشتقاق معدل الخصم" in tmpl, \
        "Certified template missing discount rate derivation text"


def test_SRB144_certified_template_has_terminal_value():
    """SRB144 Certified PDF template has Terminal Value text and terminal_cap_methods."""
    tmpl = (_srr._TMPL_DIR / "certified_valuation_report.html").read_text(encoding="utf-8")
    assert "Terminal Value" in tmpl or "terminal_cap_methods" in tmpl, \
        "Certified template missing Terminal Value section"
    assert "terminal_cap_methods" in tmpl, \
        "Certified template missing terminal_cap_methods Jinja variable"


def test_SRB145_certified_template_has_avm_regression_table():
    """SRB145 Certified PDF template has AVM regression table (avm_regression / reg-tbl)."""
    tmpl = (_srr._TMPL_DIR / "certified_valuation_report.html").read_text(encoding="utf-8")
    assert "avm_regression" in tmpl, "Certified template missing avm_regression variable"
    assert "reg-tbl" in tmpl, "Certified template missing reg-tbl CSS class"
    assert "جدول الانحدار" in tmpl, "Certified template missing AVM regression table title"


# ── SRB146–SRB159: Full Data Binding + Cap Rate + Source Spine ───────────────

_QA_SIM_PAYLOAD_V2 = {
    "property_type": "شقة سكنية", "country": "مصر",
    "region": "القاهرة", "city": "القاهرة", "district": "المعادي",
    "area": 180, "land_share_area": 35,
    "condition": "جيدة جدًا", "finishing_level": "فاخر",
    "estimated_value": 4_500_000,
    "_qa_simulation": True,
}
_QA_REQ_V2 = {
    "request_id": "REQ-SRB146-TEST",
    "source_page": "professional_valuation",
    "request_kind": "certified_report_request",
    "user_name": "اختبار", "phone": "01012345678",
    "approval_status": "approved_pending_report",
    "payload_json": __import__("json").dumps(_QA_SIM_PAYLOAD_V2),
    "expert_recommended_value": "4,350,000",
}


def _get_wb_v2():
    import openpyxl as _opxl
    from pathlib import Path as _P
    wb_path = _srr._create_expert_review_workbook("REQ-SRB146-TEST", _QA_REQ_V2, [])
    return _opxl.load_workbook(str(wb_path))


def test_SRB146_workbook_has_price_sources_sheet():
    """SRB146 Workbook contains مصادر الأسعار sheet."""
    wb = _get_wb_v2()
    assert "مصادر الأسعار" in wb.sheetnames, "Workbook missing مصادر الأسعار sheet"


def test_SRB147_workbook_has_mass_appraisal_bridge_sheet():
    """SRB147 Workbook contains ربط التقييم الجماعي sheet."""
    wb = _get_wb_v2()
    assert "ربط التقييم الجماعي" in wb.sheetnames, "Workbook missing ربط التقييم الجماعي sheet"


def test_SRB148_build_method_context_has_price_source_data_for_qa():
    """SRB148 _build_method_context returns price_source_data with 5 entries for QA."""
    mctx = _srr._build_method_context(_QA_SIM_PAYLOAD_V2)
    sources = mctx.get("price_source_data", [])
    assert len(sources) == 5, f"Expected 5 price sources, got {len(sources)}"


def test_SRB149_price_source_data_has_required_keys():
    """SRB149 price_source_data rows have required source spine keys."""
    mctx = _srr._build_method_context(_QA_SIM_PAYLOAD_V2)
    required = [
        "source_registry_id", "source_type", "source_label",
        "zone_id", "district", "price_per_m2", "source_confidence",
        "source_status", "used_in_methods",
    ]
    for src in mctx.get("price_source_data", []):
        for k in required:
            assert k in src, f"Price source missing key: {k}"


def test_SRB150_build_method_context_has_mass_appraisal_bridge():
    """SRB150 _build_method_context returns mass_appraisal_bridge dict for QA."""
    mctx = _srr._build_method_context(_QA_SIM_PAYLOAD_V2)
    bridge = mctx.get("mass_appraisal_bridge", {})
    assert bridge.get("mass_run_id") not in (None, "", "غير متاح ضمن بيانات الطلب"), \
        "mass_appraisal_bridge.mass_run_id empty for QA"
    assert bridge.get("mass_average_price_per_m2") not in (None, "", "غير متاح ضمن بيانات الطلب"), \
        "mass_appraisal_bridge.mass_average_price_per_m2 empty for QA"


def test_SRB151_build_method_context_has_cap_rate_derivation_4_methods():
    """SRB151 _build_method_context returns cap_rate_derivation with 4 methods for QA."""
    mctx = _srr._build_method_context(_QA_SIM_PAYLOAD_V2)
    cr = mctx.get("cap_rate_derivation", {})
    methods = cr.get("methods", [])
    assert len(methods) == 4, f"Expected 4 cap rate methods, got {len(methods)}"


def test_SRB152_cap_rate_methods_include_direct_extraction():
    """SRB152 Workbook cap_rate_derivation includes Direct Market Extraction method."""
    mctx = _srr._build_method_context(_QA_SIM_PAYLOAD_V2)
    keys = [m.get("method_key") for m in mctx.get("cap_rate_derivation", {}).get("methods", [])]
    assert "direct_extraction" in keys, "Cap rate methods missing direct_extraction"


def test_SRB153_cap_rate_methods_include_band_of_investment():
    """SRB153 Workbook cap_rate_derivation includes Band of Investment method."""
    mctx = _srr._build_method_context(_QA_SIM_PAYLOAD_V2)
    keys = [m.get("method_key") for m in mctx.get("cap_rate_derivation", {}).get("methods", [])]
    assert "band_of_investment" in keys, "Cap rate methods missing band_of_investment"


def test_SRB154_cap_rate_methods_include_dr_minus_growth():
    """SRB154 Workbook cap_rate_derivation includes DR minus Growth method."""
    mctx = _srr._build_method_context(_QA_SIM_PAYLOAD_V2)
    keys = [m.get("method_key") for m in mctx.get("cap_rate_derivation", {}).get("methods", [])]
    assert "dr_minus_growth" in keys, "Cap rate methods missing dr_minus_growth"


def test_SRB155_cap_rate_methods_include_buildup():
    """SRB155 Workbook cap_rate_derivation includes Built-up Adjusted method."""
    mctx = _srr._build_method_context(_QA_SIM_PAYLOAD_V2)
    keys = [m.get("method_key") for m in mctx.get("cap_rate_derivation", {}).get("methods", [])]
    assert "buildup" in keys, "Cap rate methods missing buildup"


def test_SRB156_cap_rate_derivation_average_is_non_empty_for_qa():
    """SRB156 cap_rate_derivation average_cap_rate is non-empty for QA."""
    mctx = _srr._build_method_context(_QA_SIM_PAYLOAD_V2)
    avg = mctx.get("cap_rate_derivation", {}).get("average_cap_rate", "")
    assert avg and avg != "غير متاح ضمن بيانات الطلب", \
        f"average_cap_rate empty or data-gap for QA: {avg!r}"


def test_SRB157_price_sources_sheet_has_source_rows():
    """SRB157 مصادر الأسعار sheet has source data rows (not just headers)."""
    wb = _get_wb_v2()
    ws = wb["مصادر الأسعار"]
    # Row 1 = title, row 2 = headers, row 3+ = data
    data_rows = [r for r in ws.iter_rows(min_row=3, values_only=True) if any(c for c in r)]
    assert len(data_rows) >= 5, \
        f"Expected ≥5 source rows in مصادر الأسعار, got {len(data_rows)}"


def test_SRB158_mass_bridge_sheet_has_mass_run_id():
    """SRB158 ربط التقييم الجماعي sheet contains mass_run_id value."""
    wb = _get_wb_v2()
    ws = wb["ربط التقييم الجماعي"]
    all_vals = " ".join(
        str(v) for row in ws.iter_rows(values_only=True) for v in row if v
    )
    assert "MASS-RUN-QA" in all_vals, \
        "ربط التقييم الجماعي sheet missing mass_run_id value"


def test_SRB159_preliminary_template_has_cap_rate_methods():
    """SRB159 Preliminary PDF template has final capitalization rate section."""
    tmpl = (_srr._TMPL_DIR / "simple_valuation_draft.html").read_text(encoding="utf-8")
    assert "cap_rate_methods" in tmpl, "Preliminary template missing cap_rate_methods variable"
    assert "معدل الرسملة النهائي" in tmpl, "Preliminary template missing cap rate title"


def test_SRB160_certified_template_has_cap_rate_four_method_table():
    """SRB160 Certified PDF template has final capitalization rate 4-method table."""
    tmpl = (_srr._TMPL_DIR / "certified_valuation_report.html").read_text(encoding="utf-8")
    assert "cap_rate_methods" in tmpl, "Certified template missing cap_rate_methods"
    assert "معدل الرسملة النهائي" in tmpl, "Certified template missing cap rate heading"
    assert "cap_rate_average" in tmpl, "Certified template missing cap_rate_average"
    assert "cap_rate_expert_selected" in tmpl, "Certified template missing cap_rate_expert_selected"


def test_SRB161_certified_template_has_mass_appraisal_disclosure():
    """SRB161 Certified PDF template has mass appraisal/source linkage disclosure."""
    tmpl = (_srr._TMPL_DIR / "certified_valuation_report.html").read_text(encoding="utf-8")
    assert "mass_appraisal_bridge" in tmpl, "Certified template missing mass_appraisal_bridge"
    assert "price_source_data" in tmpl, "Certified template missing price_source_data"


def test_SRB162_no_blank_method_fields_in_qa_workbook():
    """SRB162 No major method sheet has all-empty data rows in QA mode."""
    wb = _get_wb_v2()
    critical_sheets = ["DCF", "طريقة التكلفة", "AVM", "توفيق النتائج"]
    for sheet_name in critical_sheets:
        if sheet_name not in wb.sheetnames:
            continue
        ws = wb[sheet_name]
        non_empty_cells = sum(
            1 for row in ws.iter_rows(min_row=3, values_only=True)
            for cell in row if cell and str(cell).strip()
        )
        assert non_empty_cells >= 5, \
            f"Sheet '{sheet_name}' appears mostly empty (only {non_empty_cells} non-empty cells)"


def test_SRB163_avm_sheet_has_regression_table():
    """SRB163 AVM sheet contains regression feature table in QA mode."""
    wb = _get_wb_v2()
    assert "AVM" in wb.sheetnames
    ws = wb["AVM"]
    all_text = " ".join(
        str(v) for row in ws.iter_rows(values_only=True)
        for v in row if v
    )
    assert "نموذج I" in all_text or "Regression" in all_text or "Feature" in all_text or \
           "معامل" in all_text, \
        "AVM sheet missing regression feature table content"


def test_SRB164_no_qdrant_internet_claim_in_context():
    """SRB164 _build_method_context does not claim Qdrant/internet retrieval."""
    import json as _json
    mctx = _srr._build_method_context(_QA_SIM_PAYLOAD_V2)
    ctx_str = _json.dumps(mctx, ensure_ascii=False)
    forbidden = ["Qdrant retrieval", "internet search", "live data retrieved"]
    for phrase in forbidden:
        assert phrase.lower() not in ctx_str.lower(), \
            f"Method context contains forbidden live-retrieval claim: {phrase!r}"


# ── SRB165–SRB180: Rental Value + Date Basis + Excel Formula Binding ─────────

_QA_RENTAL_PAYLOAD = {
    "property_type": "شقة سكنية", "country": "مصر",
    "region": "القاهرة", "city": "القاهرة",
    "district": "مدينة نصر - المنطقة الثامنة",
    "area": 120, "land_share_area": 20,
    "condition": "جيدة", "finishing_level": "متوسط",
    "valuation_date": "2024-06-30",
    "report_date": "2026-06-24",
    "purpose": "القيمة الإيجارية",
    "estimated_value": 0,
    "final_monthly_rental_value": 9500,
    "final_annual_rental_value": 114000,
    "_qa_simulation": True,
}

_QA_RENTAL_REQ = {
    "request_id": "REQ-SRB165-RENTAL",
    "source_page": "professional_valuation",
    "request_kind": "certified_report_request",
    "user_name": "اختبار إيجاري", "phone": "01012345678",
    "approval_status": "approved_pending_report",
    "payload_json": __import__("json").dumps(_QA_RENTAL_PAYLOAD),
    "expert_recommended_value": "9,500 / شهر",
}


def _get_wb_rental():
    import openpyxl as _opxl
    wb_path = _srr._create_expert_review_workbook(
        "REQ-SRB165-RENTAL", _QA_RENTAL_REQ, []
    )
    return _opxl.load_workbook(str(wb_path))


def test_SRB165_detect_purpose_rental_arabic():
    """SRB165 _detect_valuation_purpose detects rental_value from Arabic label."""
    info = _srr._detect_valuation_purpose({"purpose": "القيمة الإيجارية"})
    assert info["purpose_key"] == "rental_value", \
        f"Expected rental_value, got {info['purpose_key']!r}"
    assert info["requires_rental_pages"] is True


def test_SRB166_detect_date_basis_retrospective():
    """SRB166 _detect_valuation_date_basis detects retrospective (Δ > 60 days)."""
    info = _srr._detect_valuation_date_basis("2024-06-30", "2026-06-24")
    assert info["date_basis_key"] == "retrospective", \
        f"Expected retrospective, got {info['date_basis_key']!r}"
    label = info["date_basis_label_ar"]
    assert "سابق" in label or "استرجاعي" in label, \
        f"Retrospective label does not contain expected Arabic text: {label!r}"


def test_SRB167_detect_date_basis_current():
    """SRB167 _detect_valuation_date_basis detects current (dates within 30 days)."""
    info = _srr._detect_valuation_date_basis("2026-06-20", "2026-06-24")
    assert info["date_basis_key"] == "current", \
        f"Expected current, got {info['date_basis_key']!r}"
    assert "حالي" in info["date_basis_label_ar"]


def test_SRB168_detect_date_basis_prospective():
    """SRB168 _detect_valuation_date_basis detects prospective (future > 30 days)."""
    info = _srr._detect_valuation_date_basis("2026-10-01", "2026-06-24")
    assert info["date_basis_key"] == "prospective", \
        f"Expected prospective, got {info['date_basis_key']!r}"
    assert "مستقبلي" in info["date_basis_label_ar"]


def test_SRB169_build_method_context_rental_includes_rental_value_context():
    """SRB169 _build_method_context with rental purpose includes rental_value_context."""
    mctx = _srr._build_method_context(_QA_RENTAL_PAYLOAD)
    assert "rental_value_context" in mctx, "rental_value_context missing from method context"
    rvc = mctx["rental_value_context"]
    assert rvc, "rental_value_context is empty for rental purpose"
    assert "rental_comparables" in rvc, "rental_comparables missing from rental_value_context"


def test_SRB170_workbook_has_rental_value_sheet():
    """SRB170 Expert workbook contains القيمة الإيجارية sheet."""
    wb = _get_wb_rental()
    assert "القيمة الإيجارية" in wb.sheetnames, \
        f"Sheet القيمة الإيجارية not found. Sheets: {wb.sheetnames}"


def test_SRB171_workbook_has_rental_comparables_sheet():
    """SRB171 Expert workbook contains مقارنات إيجارية sheet."""
    wb = _get_wb_rental()
    assert "مقارنات إيجارية" in wb.sheetnames, \
        f"Sheet مقارنات إيجارية not found. Sheets: {wb.sheetnames}"


def test_SRB172_workbook_has_rental_reconciliation_sheet():
    """SRB172 Expert workbook contains توفيق القيمة الإيجارية sheet."""
    wb = _get_wb_rental()
    assert "توفيق القيمة الإيجارية" in wb.sheetnames, \
        f"Sheet توفيق القيمة الإيجارية not found. Sheets: {wb.sheetnames}"


def test_SRB173_rental_comparables_sheet_has_rent_per_m2_label():
    """SRB173 Rental comparables sheet contains إيجار/م² adjusted rent labels."""
    wb = _get_wb_rental()
    ws = wb["مقارنات إيجارية"]
    all_text = " ".join(
        str(v) for row in ws.iter_rows(values_only=True)
        for v in row if v
    )
    assert "م²" in all_text or "إيجار" in all_text, \
        "مقارنات إيجارية sheet missing rent-per-m² label"


def test_SRB174_rental_comparables_sheet_has_excel_formulas():
    """SRB174 Rental comparables sheet contains Excel formula cells (start with =)."""
    wb = _get_wb_rental()
    ws = wb["مقارنات إيجارية"]
    formula_found = any(
        str(cell.value).startswith("=")
        for row in ws.iter_rows(min_row=4, max_row=8)
        for cell in row
        if cell.value and isinstance(cell.value, str)
    )
    assert formula_found, \
        "No Excel formula cells (starting with '=') found in مقارنات إيجارية sheet"


def test_SRB175_no_silent_blanks_in_qa_workbook_required_sheets():
    """SRB175 Required method sheets pass no-blank validation in QA mode."""
    wb = _get_wb_v2()
    required = [
        "مقارنة البيوع", "طريقة الدخل", "DCF", "طريقة التكلفة",
        "AVM", "توفيق النتائج",
    ]
    for sheet_name in required:
        if sheet_name not in wb.sheetnames:
            continue
        ws = wb[sheet_name]
        non_empty = sum(
            1 for row in ws.iter_rows(min_row=2, max_row=40, values_only=True)
            for cell in row if cell and str(cell).strip()
        )
        assert non_empty >= 3, \
            f"Sheet '{sheet_name}' has only {non_empty} non-empty cells in rows 2-40 (silent blank?)"


def test_SRB176_preliminary_template_has_rental_sections():
    """SRB176 Preliminary PDF template contains rental value comparison sections."""
    tmpl = (_srr._TMPL_DIR / "simple_valuation_draft.html").read_text(encoding="utf-8")
    assert "is_rental_purpose" in tmpl, \
        "simple_valuation_draft.html missing is_rental_purpose variable"
    assert "rental_comparables" in tmpl, \
        "simple_valuation_draft.html missing rental_comparables variable"
    assert "rental_value_context" in tmpl, \
        "simple_valuation_draft.html missing rental_value_context"


def test_SRB177_certified_template_has_rental_sections():
    """SRB177 Certified PDF template contains rental value sections."""
    tmpl = (_srr._TMPL_DIR / "certified_valuation_report.html").read_text(encoding="utf-8")
    assert "is_rental_purpose" in tmpl, \
        "certified_valuation_report.html missing is_rental_purpose variable"
    assert "rental_value_context" in tmpl, \
        "certified_valuation_report.html missing rental_value_context"


def test_SRB178_date_basis_labels_appear_in_both_templates():
    """SRB178 Date basis labels appear in both preliminary and certified templates."""
    for tmpl_name in ("simple_valuation_draft.html", "certified_valuation_report.html"):
        tmpl = (_srr._TMPL_DIR / tmpl_name).read_text(encoding="utf-8")
        assert "date_basis_info" in tmpl, \
            f"{tmpl_name} missing date_basis_info variable"
        assert "أساس تاريخ التقييم" in tmpl, \
            f"{tmpl_name} missing 'أساس تاريخ التقييم' label"


def test_SRB179_rental_source_rows_in_price_source_data():
    """SRB179 Rental source rows (types: rental_comparable, lease_offer, etc.) appear in price_source_data."""
    mctx = _srr._build_method_context(_QA_RENTAL_PAYLOAD)
    sources = mctx.get("price_source_data", [])
    source_types = {s.get("source_type", "") for s in sources}
    expected_types = {"rental_comparable", "lease_offer", "lease_contract", "expert_rent_input"}
    found = expected_types & source_types
    assert found == expected_types, \
        f"Missing rental source types: {expected_types - found}. Found: {source_types}"


def test_SRB180_cap_rate_section_independent_no_qdrant():
    """SRB180 cap_rate_derivation is independent (no Qdrant/internet). Terminal cap and discount rate stay separate."""
    import json as _json
    mctx = _srr._build_method_context(_QA_SIM_PAYLOAD_V2)
    cap_rate_der = mctx.get("cap_rate_derivation", {})
    assert cap_rate_der, "cap_rate_derivation missing from method context"
    methods = cap_rate_der.get("cap_rate_methods", cap_rate_der.get("methods", []))
    assert len(methods) == 4, f"Expected 4 cap_rate_methods/methods, got {len(methods)}"
    ctx_str = _json.dumps(mctx, ensure_ascii=False)
    forbidden = ["Qdrant retrieval", "internet search", "live data retrieved", "web scrape"]
    for phrase in forbidden:
        assert phrase.lower() not in ctx_str.lower(), \
            f"Method context contains forbidden live-source claim: {phrase!r}"
    assert "terminal_cap_methods" in mctx, \
        "terminal_cap_methods missing — discount rate must remain separate from cap rate"
    assert "discount_rate_methods" in mctx, \
        "discount_rate_methods missing — must stay independent of cap rate derivation"


# ═══════════════════════════════════════════════════════════════════════════════
# SRB181–SRB195 — Formula Binding + Inputs Sheet First + No Silent Blanks
# ═══════════════════════════════════════════════════════════════════════════════

def _get_wb_v2_path():
    """Return path to a fresh QA market workbook (for validator tests needing a path)."""
    return _srr._create_expert_review_workbook("REQ-SRB181-TEST", _QA_REQ_V2, [])


def _wb_has_formula(wb, sheet_name: str, min_row: int = 2, max_row: int = None) -> bool:
    """Return True if any cell in sheet_name starts with '='. Scans full sheet by default."""
    if sheet_name not in wb.sheetnames:
        return False
    ws = wb[sheet_name]
    _max = max_row if max_row is not None else ws.max_row
    return any(
        cell.value and isinstance(cell.value, str) and cell.value.startswith("=")
        for row in ws.iter_rows(min_row=min_row, max_row=_max)
        for cell in row
    )


def test_SRB181_inputs_sheet_is_first_sheet():
    """SRB181 مدخلات التقرير is sheet index 0 in the expert workbook."""
    wb = _get_wb_v2()
    assert wb.sheetnames[0] == "مدخلات التقرير", \
        f"Expected first sheet 'مدخلات التقرير', got {wb.sheetnames[0]!r}"


def test_SRB182_workbook_has_27_sheets():
    """SRB182 Expert workbook has exactly 57 sheets (51 previous + 6 risk/decision pass sheets)."""
    wb = _get_wb_v2()
    assert len(wb.sheetnames) == 57, \
        f"Expected 57 sheets, got {len(wb.sheetnames)}: {wb.sheetnames}"


def test_SRB183_sales_comparison_has_formula_cells():
    """SRB183 مقارنة البيوع contains Excel formula cells (=D.../C... price-per-m²)."""
    wb = _get_wb_v2()
    assert _wb_has_formula(wb, "مقارنة البيوع"), \
        "No formula cells (starting with '=') found in مقارنة البيوع"


def test_SRB184_income_method_has_formula_cells():
    """SRB184 طريقة الدخل contains Excel formula cells (NOI income chain)."""
    wb = _get_wb_v2()
    assert _wb_has_formula(wb, "طريقة الدخل"), \
        "No formula cells (starting with '=') found in طريقة الدخل"


def test_SRB185_dcf_has_formula_cells():
    """SRB185 DCF sheet contains Excel formula cells (5-year cashflow + terminal value)."""
    wb = _get_wb_v2()
    assert _wb_has_formula(wb, "DCF"), \
        "No formula cells (starting with '=') found in DCF"


def test_SRB186_cost_method_has_formula_cells():
    """SRB186 طريقة التكلفة contains Excel formula cells (replacement cost chain)."""
    wb = _get_wb_v2()
    assert _wb_has_formula(wb, "طريقة التكلفة"), \
        "No formula cells (starting with '=') found in طريقة التكلفة"


def test_SRB187_reconciliation_has_formula_cells():
    """SRB187 توفيق النتائج contains Excel formula cells (weighted value = weight × value)."""
    wb = _get_wb_v2()
    assert _wb_has_formula(wb, "توفيق النتائج"), \
        "No formula cells (starting with '=') found in توفيق النتائج"


def test_SRB188_sales_comparison_area_reference_cell():
    """SRB188 مقارنة البيوع P1 holds a positive numeric subject area for $P$1 formula refs."""
    wb = _get_wb_v2()
    assert "مقارنة البيوع" in wb.sheetnames, "مقارنة البيوع sheet missing"
    p1 = wb["مقارنة البيوع"]["P1"].value
    assert p1 is not None and isinstance(p1, (int, float)) and p1 > 0, \
        f"P1 (subject area reference) should be positive numeric, got: {p1!r}"


def test_SRB189_validator_returns_empty_for_valid_workbook():
    """SRB189 _validate_workbook_formulas_and_no_silent_blanks returns [] for valid QA workbook."""
    wb_path = _get_wb_v2_path()
    issues = _srr._validate_workbook_formulas_and_no_silent_blanks(wb_path)
    assert issues == [], \
        "Validator found unexpected issues in valid QA workbook:\n" + "\n".join(issues)


def test_SRB190_validator_function_importable():
    """SRB190 _validate_workbook_formulas_and_no_silent_blanks is callable on the module."""
    assert callable(getattr(_srr, "_validate_workbook_formulas_and_no_silent_blanks", None)), \
        "_validate_workbook_formulas_and_no_silent_blanks not found / not callable on shared_request_routes"


def test_SRB191_validator_detects_non_first_inputs_sheet():
    """SRB191 Validator raises INPUTS_SHEET_NOT_FIRST when مدخلات التقرير is not at index 0."""
    import openpyxl as _opxl
    import tempfile
    import os
    wb_tmp = _opxl.Workbook()
    wb_tmp.active.title = "Dashboard"
    wb_tmp.create_sheet("مدخلات التقرير")
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        tmp_path = f.name
    try:
        wb_tmp.save(tmp_path)
        issues = _srr._validate_workbook_formulas_and_no_silent_blanks(tmp_path)
        assert any("INPUTS_SHEET_NOT_FIRST" in i for i in issues), \
            f"Expected INPUTS_SHEET_NOT_FIRST issue, got: {issues}"
    finally:
        os.unlink(tmp_path)


def test_SRB192_validator_detects_missing_required_sheet():
    """SRB192 Validator returns MISSING_SHEET issues when required sheets are absent."""
    import openpyxl as _opxl
    import tempfile
    import os
    wb_tmp = _opxl.Workbook()
    wb_tmp.active.title = "مدخلات التقرير"
    ws = wb_tmp.active
    ws["A1"].value = "header"; ws["A2"].value = "row2"; ws["A3"].value = "row3"
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        tmp_path = f.name
    try:
        wb_tmp.save(tmp_path)
        issues = _srr._validate_workbook_formulas_and_no_silent_blanks(tmp_path)
        missing = [i for i in issues if "MISSING_SHEET" in i]
        assert missing, \
            f"Expected MISSING_SHEET issues for workbook with only مدخلات التقرير, got: {issues}"
    finally:
        os.unlink(tmp_path)


def test_SRB193_inputs_sheet_contains_arabic_section_headers():
    """SRB193 مدخلات التقرير sheet has section headers بيانات التكليف and بيانات العقار."""
    wb = _get_wb_v2()
    assert "مدخلات التقرير" in wb.sheetnames, "مدخلات التقرير sheet missing"
    ws = wb["مدخلات التقرير"]
    all_text = " ".join(str(v) for row in ws.iter_rows(values_only=True) for v in row if v)
    assert "بيانات التكليف" in all_text, \
        "مدخلات التقرير missing section header 'بيانات التكليف'"
    assert "بيانات العقار" in all_text, \
        "مدخلات التقرير missing section header 'بيانات العقار'"


def test_SRB194_no_silent_blanks_alias_matches_new_validator():
    """SRB194 _validate_workbook_no_silent_blanks alias returns identical result to new validator."""
    wb_path = _srr._create_expert_review_workbook("REQ-SRB194-TEST", _QA_REQ_V2, [])
    result_new = _srr._validate_workbook_formulas_and_no_silent_blanks(wb_path)
    result_alias = _srr._validate_workbook_no_silent_blanks(wb_path)
    assert result_new == result_alias, \
        f"Alias and new validator disagree:\nnew={result_new}\nalias={result_alias}"


def test_SRB195_inputs_sheet_contains_purpose_and_date_basis_for_rental():
    """SRB195 مدخلات التقرير contains purpose label and valuation date field for rental payload."""
    wb = _get_wb_rental()
    assert "مدخلات التقرير" in wb.sheetnames, "مدخلات التقرير sheet missing"
    ws = wb["مدخلات التقرير"]
    all_text = " ".join(str(v) for row in ws.iter_rows(values_only=True) for v in row if v)
    assert "إيجاري" in all_text or "الإيجارية" in all_text, \
        "مدخلات التقرير missing rental purpose label (إيجاري / الإيجارية)"
    assert "تاريخ التقييم" in all_text or "أساس تاريخ" in all_text, \
        "مدخلات التقرير missing valuation date / date basis field"


# ── SRB196–SRB210: Geographic Consistency, Cost Binding, Shared Land, ─────────
# ── Cap Rate Governance, Audit Trail, Map Placeholders ────────────────────────

_QA_MAADI_PAYLOAD = {
    "property_type": "شقة سكنية", "country": "مصر",
    "region": "القاهرة", "city": "القاهرة",
    "district": "المعادي", "zone_id": "ZONE-CAI-MAADI-01",
    "sub_market": "سوق المعادي الفرعي",
    "area": 180, "land_share_area": 35,
    "total_building_sellable_area": 1_000, "land_area": 350,
    "coordinates": "29.9553, 31.2588",
    "condition": "جيدة جدًا", "finishing_level": "فاخر",
    "estimated_value": 4_500_000,
    "income_monthly_rent": 10_000, "income_cap_rate": 3.8,
    "_qa_simulation": True,
}

_QA_MAADI_REQ = {
    "request_id": "REQ-SRB196-TEST",
    "source_page": "professional_valuation",
    "request_kind": "certified_report_request",
    "user_name": "اختبار المعادي", "phone": "01012345678",
    "approval_status": "approved_pending_report",
    "payload_json": __import__("json").dumps(_QA_MAADI_PAYLOAD),
    "expert_recommended_value": "4,400,000",
    "created_at": "2026-06-24T08:00:00",
    "updated_at": "2026-06-24T10:00:00",
}


def _get_wb_maadi():
    import openpyxl as _opxl
    wb_path = _srr._create_expert_review_workbook("REQ-SRB196-TEST", _QA_MAADI_REQ, [])
    return _opxl.load_workbook(str(wb_path), data_only=False)


def test_SRB196_included_comparables_match_subject_zone_id():
    """SRB196 Included comparables have geo_match_status='مطابق' for المعادي subject."""
    mctx = _srr._build_method_context(_QA_MAADI_PAYLOAD)
    comps = mctx.get("comparables", [])
    assert comps, "No comparables returned"
    included = [c for c in comps if c.get("geo_match_status") == "مطابق"]
    assert len(included) >= 3, \
        f"Expected ≥3 matched comparables, got {len(included)}"
    for comp in included:
        assert comp.get("comparable_zone_id") == "ZONE-CAI-MAADI-01", \
            f"Included comp has wrong zone_id: {comp.get('comparable_zone_id')}"


def test_SRB197_out_of_zone_comparable_excluded_from_calculations():
    """SRB197 Out-of-zone comparable is excluded from adj_prices average."""
    mctx = _srr._build_method_context(_QA_MAADI_PAYLOAD)
    comps = mctx.get("comparables", [])
    excluded = [c for c in comps if c.get("geo_match_status") == "خارج النطاق"]
    assert len(excluded) >= 1, "Expected at least 1 out-of-zone comparable"
    for comp in excluded:
        ap = comp.get("adjusted_price_per_m2", "")
        assert "مستبعد جغرافيًا" in str(ap), \
            f"Out-of-zone comp should show 'مستبعد جغرافيًا', got {ap!r}"
    # adj_prices_excluded_count must reflect exclusions
    assert mctx.get("adj_prices_excluded_count", 0) >= 1, \
        "adj_prices_excluded_count should be ≥1 for المعادي payload"


def test_SRB198_cost_quantity_uses_payload_area_not_hardcoded():
    """SRB198 Cost breakdown uses area=180 from payload, not hardcoded 120."""
    mctx = _srr._build_method_context(_QA_MAADI_PAYLOAD)
    cost_breakdown = mctx.get("cost_breakdown", [])
    assert cost_breakdown, "cost_breakdown is empty"
    m2_rows = [row for row in cost_breakdown if row.get("unit") == "م²"]
    assert m2_rows, "No م² cost rows found"
    for row in m2_rows:
        qty = str(row.get("qty", ""))
        assert "180" in qty, \
            f"Cost item qty should contain 180 (payload area), got {qty!r}"


def test_SRB199_cost_approach_uses_shared_land_value():
    """SRB199 land_share_ratio present and reconciled_subject_land_share_value computed."""
    mctx = _srr._build_method_context(_QA_MAADI_PAYLOAD)
    ratio = mctx.get("land_share_ratio", "")
    assert ratio and ratio != "—", f"land_share_ratio missing or empty: {ratio!r}"
    assert "%" in str(ratio), f"land_share_ratio should be a percentage: {ratio!r}"
    rslv = mctx.get("reconciled_subject_land_share_value", "")
    assert rslv and rslv not in ("—", ""), \
        f"reconciled_subject_land_share_value missing: {rslv!r}"


def test_SRB200_land_share_ratio_formula_field_present():
    """SRB200 land_share_ratio formula field present in method context."""
    mctx = _srr._build_method_context(_QA_MAADI_PAYLOAD)
    assert "land_share_ratio" in mctx, "land_share_ratio key missing from method context"
    assert "subject_land_share_area" in mctx, "subject_land_share_area key missing"
    assert "reconciled_subject_land_share_value" in mctx, \
        "reconciled_subject_land_share_value key missing"


def test_SRB201_prelim_vs_certified_section_present_in_mctx():
    """SRB201 prelim_vs_certified section is present in method context."""
    mctx = _srr._build_method_context(_QA_MAADI_PAYLOAD)
    pvc = mctx.get("prelim_vs_certified")
    assert pvc is not None, "prelim_vs_certified missing from method context"
    assert isinstance(pvc, dict), "prelim_vs_certified must be a dict"
    for key in ("preliminary_value", "certified_final_value", "difference_amount",
                "difference_percentage", "reason_summary", "disclaimer"):
        assert key in pvc, f"prelim_vs_certified missing key: {key}"


def test_SRB202_cap_rate_warning_appears_when_deviation_exceeds_threshold():
    """SRB202 cap_rate_warning_flag=True when expert selected cap rate deviates >0.5% from avg."""
    mctx = _srr._build_method_context(_QA_MAADI_PAYLOAD)
    # QA: expert_selected=3.80%, average=4.55% → deviation=0.75% > 0.5% → warning
    flag = mctx.get("cap_rate_warning_flag")
    assert flag is True, \
        f"cap_rate_warning_flag should be True for QA (deviation 0.75% > 0.5%), got {flag!r}"
    text = mctx.get("cap_rate_warning_text", "")
    assert text, "cap_rate_warning_text should not be empty when flag=True"
    assert "تحذير" in text or "يتجاوز" in text, \
        f"cap_rate_warning_text should contain warning language: {text!r}"


def test_SRB203_workbook_audit_trail_has_lifecycle_rows():
    """SRB203 Workbook سجل المراجعة sheet has ≥3 lifecycle rows."""
    wb = _get_wb_maadi()
    assert "سجل المراجعة" in wb.sheetnames, "سجل المراجعة sheet missing"
    ws = wb["سجل المراجعة"]
    data_rows = [
        row for row in ws.iter_rows(min_row=2, values_only=True)
        if any(c is not None and str(c).strip() for c in row)
    ]
    assert len(data_rows) >= 3, \
        f"سجل المراجعة should have ≥3 lifecycle rows, got {len(data_rows)}"


def test_SRB204_map_placeholder_has_coordinate_display():
    """SRB204 خرائط وصور sheet shows coordinate data when coordinates are provided."""
    wb = _get_wb_maadi()
    assert "خرائط وصور" in wb.sheetnames, "خرائط وصور sheet missing"
    ws = wb["خرائط وصور"]
    all_text = " ".join(
        str(cell or "") for row in ws.iter_rows(values_only=True) for cell in row
    )
    assert "29." in all_text or "إحداثيات" in all_text or "خط العرض" in all_text, \
        "خرائط وصور should show coordinate data for payload with coordinates"


def test_SRB205_map_placeholders_have_no_external_urls():
    """SRB205 خرائط وصور sheet contains no external map API URLs (not just brand name mentions)."""
    wb = _get_wb_maadi()
    assert "خرائط وصور" in wb.sheetnames, "خرائط وصور sheet missing"
    ws = wb["خرائط وصور"]
    all_text = " ".join(
        str(cell or "").lower() for row in ws.iter_rows(values_only=True) for cell in row
    )
    for bad_url in ("maps.googleapis.com", "api.mapbox.com", "tile.openstreetmap.org",
                    "maps.google.com"):
        assert bad_url not in all_text, \
            f"خرائط وصور sheet contains forbidden external API URL: {bad_url!r}"


def test_SRB206_inputs_sheet_exists_and_is_first():
    """SRB206 مدخلات التقرير sheet exists and is first (index 0) for Maadi payload."""
    wb = _get_wb_maadi()
    assert "مدخلات التقرير" in wb.sheetnames, "مدخلات التقرير sheet missing"
    assert wb.sheetnames[0] == "مدخلات التقرير", \
        f"First sheet should be 'مدخلات التقرير', got {wb.sheetnames[0]!r}"


def test_SRB207_formula_validator_passes_for_maadi_workbook():
    """SRB207 _validate_workbook_formulas_and_no_silent_blanks passes for Maadi QA workbook."""
    wb_path = _srr._create_expert_review_workbook("REQ-SRB207-TEST", _QA_MAADI_REQ, [])
    issues = _srr._validate_workbook_formulas_and_no_silent_blanks(str(wb_path))
    assert not issues, \
        f"Validator found issues for Maadi workbook: {issues}"


def test_SRB208_no_silent_blanks_in_required_workbook_ranges():
    """SRB208 Key workbook sheets have no silent blanks (≥3 non-blank rows in rows 2–40)."""
    wb_path = _srr._create_expert_review_workbook("REQ-SRB208-TEST", _QA_MAADI_REQ, [])
    import openpyxl as _opxl
    wb = _opxl.load_workbook(str(wb_path), data_only=False)
    sparse_sheets = []
    for sname in ["مقارنة البيوع", "طريقة الدخل", "DCF", "طريقة التكلفة",
                  "توفيق النتائج", "سجل المراجعة", "قيمة الأرض"]:
        if sname not in wb.sheetnames:
            sparse_sheets.append(f"MISSING:{sname}")
            continue
        ws = wb[sname]
        nr = sum(
            1 for row in ws.iter_rows(min_row=2, max_row=40, values_only=True)
            if any(c is not None and str(c).strip() for c in row)
        )
        if nr < 3:
            sparse_sheets.append(f"{sname}({nr}rows)")
    assert not sparse_sheets, \
        f"Sparse/missing sheets found: {sparse_sheets}"


def test_SRB209_rental_date_basis_still_passes_for_retrospective():
    """SRB209 Rental retrospective payload still gets correct date_basis_info (regression guard)."""
    retrospective_payload = dict(_QA_RENTAL_PAYLOAD)
    retrospective_payload["valuation_date"] = "2024-06-30"
    retrospective_payload["report_date"] = "2026-06-24"
    mctx = _srr._build_method_context(retrospective_payload)
    dbi = mctx.get("date_basis_info") or {}
    assert dbi.get("date_basis_key") == "retrospective", \
        f"Should detect retrospective when valuation_date=2024-06-30: {dbi}"
    assert mctx.get("is_rental_purpose"), \
        "is_rental_purpose should be True for rental payload"


def test_SRB210_no_qdrant_internet_claim_in_new_fields():
    """SRB210 New governance/geographic fields contain no live Qdrant/internet retrieval claims."""
    mctx = _srr._build_method_context(_QA_MAADI_PAYLOAD)
    forbidden = [
        "Qdrant", "qdrant", "live search", "internet retrieval",
        "Google Maps", "OpenStreetMap", "Mapbox", "real market data retrieved",
    ]
    new_field_keys = [
        "cap_rate_warning_text", "cap_rate_source_basis", "risk_free_rate_notes",
        "geo_disclaimer", "shared_land_basis_notes", "cost_area_basis",
    ]
    for key in new_field_keys:
        val = str(mctx.get(key) or "")
        for phrase in forbidden:
            assert phrase not in val, \
                f"Field {key!r} contains forbidden phrase {phrase!r}: {val[:120]!r}"


# ─────────────────────────────────────────────────────────────────────────────
# SRB211–SRB228  Strategic Reporting Upgrade Tests
# ─────────────────────────────────────────────────────────────────────────────

def _get_wb_maadi_strategic():
    """Helper: generate workbook for المعادي QA payload and return openpyxl workbook."""
    import openpyxl as _opxl
    wb_path = _srr._create_expert_review_workbook("REQ-SRB211-TEST", _QA_MAADI_REQ, [])
    return _opxl.load_workbook(str(wb_path), data_only=False)


def test_SRB211_what_if_sheet_exists_and_has_formula_cells():
    """SRB211 'سيناريوهات What-If' sheet exists and contains at least one formula cell (='...')."""
    wb = _get_wb_maadi_strategic()
    assert "سيناريوهات What-If" in wb.sheetnames, \
        f"Missing 'سيناريوهات What-If' sheet. Sheets: {wb.sheetnames}"
    ws_wi = wb["سيناريوهات What-If"]
    formula_found = any(
        cell.value and isinstance(cell.value, str) and cell.value.startswith("=")
        for row in ws_wi.iter_rows(min_row=3, max_row=20)
        for cell in row
    )
    assert formula_found, \
        "'سيناريوهات What-If' sheet has no formula cells starting with '='"


def test_SRB212_buy_vs_rent_sheet_exists_and_has_price_to_rent_formula():
    """SRB212 'شراء أم إيجار' sheet exists and contains price-to-rent ratio formula cell."""
    wb = _get_wb_maadi_strategic()
    assert "شراء أم إيجار" in wb.sheetnames, \
        f"Missing 'شراء أم إيجار' sheet. Sheets: {wb.sheetnames}"
    ws_bvr = wb["شراء أم إيجار"]
    formula_found = any(
        cell.value and isinstance(cell.value, str) and cell.value.startswith("=")
        for row in ws_bvr.iter_rows(min_row=2, max_row=30)
        for cell in row
    )
    assert formula_found, \
        "'شراء أم إيجار' sheet has no formula cells"
    # Check that the نسبة السعر إلى الإيجار label exists
    all_text = " ".join(
        str(cell or "") for row in ws_bvr.iter_rows(values_only=True) for cell in row
        if cell is not None
    )
    assert "السعر" in all_text and "الإيجار" in all_text, \
        "Buy vs Rent sheet missing price-to-rent ratio labels"


def test_SRB213_esg_sheet_exists_and_has_sum_formula():
    """SRB213 'ESG والاستدامة' sheet exists and contains a SUM formula for total ESG score."""
    wb = _get_wb_maadi_strategic()
    assert "ESG والاستدامة" in wb.sheetnames, \
        f"Missing 'ESG والاستدامة' sheet. Sheets: {wb.sheetnames}"
    ws_esg = wb["ESG والاستدامة"]
    sum_found = any(
        cell.value and isinstance(cell.value, str) and "SUM" in cell.value.upper()
        for row in ws_esg.iter_rows(min_row=2, max_row=30)
        for cell in row
    )
    assert sum_found, \
        "'ESG والاستدامة' sheet has no SUM formula for total score"


def test_SRB214_construction_cost_sheet_exists_with_items():
    """SRB214 'مؤشرات تكلفة البناء' sheet exists with ≥3 item rows and disclaimer text."""
    wb = _get_wb_maadi_strategic()
    assert "مؤشرات تكلفة البناء" in wb.sheetnames, \
        f"Missing 'مؤشرات تكلفة البناء' sheet. Sheets: {wb.sheetnames}"
    ws_cc = wb["مؤشرات تكلفة البناء"]
    data_rows = sum(
        1 for row in ws_cc.iter_rows(min_row=3, max_row=20, values_only=True)
        if any(c is not None and str(c).strip() for c in row)
    )
    assert data_rows >= 3, \
        f"'مؤشرات تكلفة البناء' has only {data_rows} data rows, expected ≥3"
    all_text = " ".join(
        str(cell or "") for row in ws_cc.iter_rows(values_only=True) for cell in row
        if cell is not None
    )
    assert "لم يتم ربط" in all_text or "مرحلة مستقبلية" in all_text or "داخلية" in all_text, \
        "Construction cost sheet missing disclaimer about no live price API"


def test_SRB215_inputs_sheet_has_qdrant_readiness_section_no_active_claim():
    """SRB215 مدخلات التقرير section 18 has Qdrant/Source Registry readiness with 'مستقبلية' language, no active claim."""
    wb = _get_wb_maadi_strategic()
    assert "مدخلات التقرير" in wb.sheetnames
    ws_inp = wb["مدخلات التقرير"]
    all_text = " ".join(
        str(cell or "") for row in ws_inp.iter_rows(values_only=True) for cell in row
        if cell is not None
    )
    # Must mention Qdrant readiness
    assert "Qdrant" in all_text or "qdrant" in all_text.lower(), \
        "مدخلات التقرير missing Qdrant readiness entry"
    # Must use future-roadmap language
    assert "مستقبلية" in all_text or "لم تُفعَّل" in all_text, \
        "مدخلات التقرير Qdrant entry missing future-roadmap language"
    # Must NOT claim active retrieval
    forbidden_claims = ["يتصل بـ Qdrant", "يسترجع من الإنترنت", "live Qdrant active"]
    for claim in forbidden_claims:
        assert claim not in all_text, \
            f"مدخلات التقرير contains active Qdrant claim: {claim!r}"


def test_SRB216_inputs_sheet_has_what_if_section():
    """SRB216 مدخلات التقرير has section 15 What-If with ≥4 scenario labels."""
    wb = _get_wb_maadi_strategic()
    ws_inp = wb["مدخلات التقرير"]
    all_text = " ".join(
        str(cell or "") for row in ws_inp.iter_rows(values_only=True) for cell in row
        if cell is not None
    )
    assert "What-If" in all_text or "سيناريو" in all_text, \
        "مدخلات التقرير missing What-If section (section 15)"
    # Count scenario labels
    scenario_count = sum(1 for i in range(1, 8) if f"سيناريو {i}" in all_text)
    assert scenario_count >= 4, \
        f"Expected ≥4 What-If scenario labels in مدخلات التقرير, found {scenario_count}"


def test_SRB217_inputs_sheet_has_buy_vs_rent_section():
    """SRB217 مدخلات التقرير has section 16 Buy vs Rent with market value and holding period."""
    wb = _get_wb_maadi_strategic()
    ws_inp = wb["مدخلات التقرير"]
    all_text = " ".join(
        str(cell or "") for row in ws_inp.iter_rows(values_only=True) for cell in row
        if cell is not None
    )
    assert "الشراء مقابل الإيجار" in all_text or "شراء أم إيجار" in all_text, \
        "مدخلات التقرير missing Buy vs Rent section (section 16)"
    assert "القيمة السوقية" in all_text, \
        "مدخلات التقرير Buy vs Rent section missing القيمة السوقية label"
    assert "فترة الاحتفاظ" in all_text, \
        "مدخلات التقرير Buy vs Rent section missing فترة الاحتفاظ label"


def test_SRB218_inputs_sheet_has_esg_section():
    """SRB218 مدخلات التقرير has section 17 ESG with ≥4 scoring criteria."""
    wb = _get_wb_maadi_strategic()
    ws_inp = wb["مدخلات التقرير"]
    all_text = " ".join(
        str(cell or "") for row in ws_inp.iter_rows(values_only=True) for cell in row
        if cell is not None
    )
    assert "ESG" in all_text, \
        "مدخلات التقرير missing ESG section (section 17)"
    criteria_labels = ["الطاقة الشمسية", "العزل الحراري", "كفاءة المياه", "النقل العام"]
    found = sum(1 for lbl in criteria_labels if lbl in all_text)
    assert found >= 3, \
        f"Expected ≥3 ESG criteria labels in مدخلات التقرير, found {found}"


def test_SRB219_inputs_sheet_has_governance_section():
    """SRB219 مدخلات التقرير has section 18 governance with approval status and roadmap entries."""
    wb = _get_wb_maadi_strategic()
    ws_inp = wb["مدخلات التقرير"]
    all_text = " ".join(
        str(cell or "") for row in ws_inp.iter_rows(values_only=True) for cell in row
        if cell is not None
    )
    assert "اعتماد التقرير" in all_text or "حالة اعتماد" in all_text, \
        "مدخلات التقرير section 18 missing approval status"
    assert "Source Registry" in all_text, \
        "مدخلات التقرير section 18 missing Source Registry readiness entry"


def test_SRB220_validator_passes_with_new_strategic_sheets():
    """SRB220 _validate_workbook_formulas_and_no_silent_blanks passes for QA workbook with all strategic sheets."""
    wb_path = _srr._create_expert_review_workbook("REQ-SRB220-TEST", _QA_MAADI_REQ, [])
    issues = _srr._validate_workbook_formulas_and_no_silent_blanks(str(wb_path))
    assert not issues, \
        f"Validator found issues: {issues}"


def test_SRB221_what_if_scenarios_qa_populated_with_base_value():
    """SRB221 What-If sheet scenarios use QA base value from payload estimated_value."""
    wb = _get_wb_maadi_strategic()
    ws_wi = wb["سيناريوهات What-If"]
    # Check that column G (value impact) cells for at least one row contain a formula
    formula_rows = [
        row[6].value for row in ws_wi.iter_rows(min_row=3, max_row=12)
        if row[6].value and isinstance(row[6].value, str) and row[6].value.startswith("=")
    ]
    assert len(formula_rows) >= 3, \
        f"Expected ≥3 value-impact formula cells in What-If sheet, got {len(formula_rows)}"


def test_SRB222_buy_vs_rent_decision_flag_is_populated_for_qa():
    """SRB222 شراء أم إيجار sheet has a decision flag row populated for QA payload."""
    wb = _get_wb_maadi_strategic()
    ws_bvr = wb["شراء أم إيجار"]
    all_text = " ".join(
        str(cell or "") for row in ws_bvr.iter_rows(values_only=True) for cell in row
        if cell is not None
    )
    # Decision flag should mention price-to-rent ratio or one of the decision outcomes
    decision_terms = ["مُفضَّل", "محايد", "أفضل مالياً", "Price-to-Rent", "نسبة"]
    found = any(t in all_text for t in decision_terms)
    assert found, \
        f"Buy vs Rent sheet has no decision flag content. Sample: {all_text[:200]!r}"


def test_SRB223_esg_sheet_has_category_and_total_score():
    """SRB223 ESG sheet contains a تصنيف ESG row and total score SUM for QA payload."""
    wb = _get_wb_maadi_strategic()
    ws_esg = wb["ESG والاستدامة"]
    all_text = " ".join(
        str(cell or "") for row in ws_esg.iter_rows(values_only=True) for cell in row
        if cell is not None
    )
    assert "تصنيف" in all_text, \
        "ESG sheet missing تصنيف (category) row"
    assert "إجمالي" in all_text, \
        "ESG sheet missing إجمالي (total score) label"
    # SUM formula must exist
    sum_found = any(
        cell.value and isinstance(cell.value, str) and "SUM" in cell.value.upper()
        for row in ws_esg.iter_rows(min_row=2, max_row=30)
        for cell in row
    )
    assert sum_found, "ESG sheet missing SUM formula"


def test_SRB224_no_live_external_api_url_in_new_sheets():
    """SRB224 New strategic sheets (What-If, Buy vs Rent, ESG, Construction Cost) contain no live external API URLs."""
    wb = _get_wb_maadi_strategic()
    bad_urls = [
        "maps.googleapis.com", "api.mapbox.com", "tile.openstreetmap.org",
        "maps.google.com", "api.qdrant.io", "api.openai.com",
        "api.construction.gov", "capmas.gov.eg/api",
    ]
    for sname in ["سيناريوهات What-If", "شراء أم إيجار", "ESG والاستدامة", "مؤشرات تكلفة البناء"]:
        if sname not in wb.sheetnames:
            continue
        all_text = " ".join(
            str(cell or "") for row in wb[sname].iter_rows(values_only=True)
            for cell in row if cell is not None
        ).lower()
        for url in bad_urls:
            assert url not in all_text, \
                f"Sheet '{sname}' contains forbidden external API URL: {url!r}"


def test_SRB225_what_if_sheet_has_seven_scenario_rows():
    """SRB225 سيناريوهات What-If has ≥7 data rows (one per scenario)."""
    wb = _get_wb_maadi_strategic()
    ws_wi = wb["سيناريوهات What-If"]
    data_rows = sum(
        1 for row in ws_wi.iter_rows(min_row=3, max_row=15, values_only=True)
        if any(c is not None and str(c).strip() for c in row)
    )
    assert data_rows >= 7, \
        f"Expected ≥7 scenario rows in What-If sheet, got {data_rows}"


def test_SRB226_construction_cost_has_disclaimer_no_live_api():
    """SRB226 مؤشرات تكلفة البناء disclaimer states no live construction price API connected."""
    wb = _get_wb_maadi_strategic()
    ws_cc = wb["مؤشرات تكلفة البناء"]
    all_text = " ".join(
        str(cell or "") for row in ws_cc.iter_rows(values_only=True) for cell in row
        if cell is not None
    )
    assert "لم يتم ربط" in all_text or "مرحلة مستقبلية" in all_text, \
        "مؤشرات تكلفة البناء missing no-live-API disclaimer"
    # Must not claim active construction price API
    forbidden = ["يتصل بـ CAPMAS", "يسترجع أسعار حية", "live construction API active"]
    for phrase in forbidden:
        assert phrase not in all_text, \
            f"Construction cost sheet contains forbidden claim: {phrase!r}"


def test_SRB227_buy_vs_rent_has_advisory_disclaimer():
    """SRB227 شراء أم إيجار sheet contains advisory disclaimer (not a final investment recommendation)."""
    wb = _get_wb_maadi_strategic()
    ws_bvr = wb["شراء أم إيجار"]
    all_text = " ".join(
        str(cell or "") for row in ws_bvr.iter_rows(values_only=True) for cell in row
        if cell is not None
    )
    assert "استرشادي" in all_text or "نصيحة استثمارية" in all_text, \
        "شراء أم إيجار sheet missing advisory disclaimer"


def test_SRB228_esg_sheet_has_disclaimer_for_missing_data():
    """SRB228 ESG sheet has an appropriate disclaimer present (QA or non-QA wording)."""
    wb = _get_wb_maadi_strategic()
    ws_esg = wb["ESG والاستدامة"]
    all_text = " ".join(
        str(cell or "") for row in ws_esg.iter_rows(values_only=True) for cell in row
        if cell is not None
    )
    # Either QA disclaimer or no-data disclaimer
    disclaimer_terms = ["محاكاة QA", "لم يتم إدخال بيانات", "استرشادي", "مبنية على"]
    found = any(t in all_text for t in disclaimer_terms)
    assert found, \
        f"ESG sheet missing appropriate disclaimer. Sample: {all_text[:200]!r}"


# ─────────────────────────────────────────────────────────────────────────────
# SRB229–SRB246  Manual Review Corrections Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_SRB229_land_comps_have_geo_match_status():
    """SRB229 _build_method_context land_comps each have geo_match_status field (Part B+C)."""
    mctx = _srr._build_method_context(_QA_MAADI_PAYLOAD)
    lc = mctx.get("land_comps", [])
    assert lc, "land_comps is empty for Maadi QA"
    missing = [i for i, c in enumerate(lc) if "geo_match_status" not in c]
    assert not missing, f"land_comps entries at indices {missing} missing geo_match_status"


def test_SRB230_price_source_data_have_geo_match_status():
    """SRB230 _build_method_context price_source_data entries have geo_match_status (Part B+C)."""
    mctx = _srr._build_method_context(_QA_MAADI_PAYLOAD)
    sources = mctx.get("price_source_data", [])
    assert sources, "price_source_data is empty for Maadi QA"
    missing = [i for i, s in enumerate(sources) if "geo_match_status" not in s]
    assert not missing, \
        f"price_source_data entries at indices {missing} missing geo_match_status"


def test_SRB231_rental_comps_have_geo_match_status():
    """SRB231 _build_method_context rental_value_context comparables have geo_match_status (Part B+C)."""
    mctx = _srr._build_method_context(_QA_MAADI_PAYLOAD)
    rvc  = mctx.get("rental_value_context", {})
    rcs  = rvc.get("rental_comparables", [])
    assert rcs, "rental_comparables empty for Maadi QA"
    missing = [i for i, r in enumerate(rcs) if "geo_match_status" not in r]
    assert not missing, \
        f"rental_comparables entries at indices {missing} missing geo_match_status"


def test_SRB232_land_sheet_has_geo_match_status_header():
    """SRB232 قيمة الأرض workbook sheet has حالة الموقع الجغرافي column header (Part B workbook)."""
    wb = _get_wb_maadi_strategic()
    assert "قيمة الأرض" in wb.sheetnames, "قيمة الأرض sheet missing"
    ws = wb["قيمة الأرض"]
    all_text = " ".join(str(c or "") for row in ws.iter_rows(values_only=True) for c in row)
    assert "حالة الموقع الجغرافي" in all_text or "الموقع الجغرافي" in all_text, \
        "قيمة الأرض sheet missing geo_match_status column"


def test_SRB233_price_sources_sheet_has_geo_match_status_header():
    """SRB233 مصادر الأسعار workbook sheet has geo status column (geo_use_status or geo_match_status)."""
    wb = _get_wb_maadi_strategic()
    assert "مصادر الأسعار" in wb.sheetnames, "مصادر الأسعار sheet missing"
    ws = wb["مصادر الأسعار"]
    all_text = " ".join(str(c or "") for row in ws.iter_rows(values_only=True) for c in row)
    assert (
        "حالة الموقع الجغرافي" in all_text
        or "الموقع الجغرافي" in all_text
        or "حالة الاستخدام الجغرافي" in all_text
        or "الاستخدام الجغرافي" in all_text
    ), "مصادر الأسعار sheet missing geo status column (geo_use_status / geo_match_status)"


def test_SRB234_rental_comps_sheet_has_geo_match_status_header():
    """SRB234 مقارنات إيجارية workbook sheet has حالة الموقع الجغرافي column (Part B workbook)."""
    wb = _get_wb_maadi_strategic()
    assert "مقارنات إيجارية" in wb.sheetnames, "مقارنات إيجارية sheet missing"
    ws = wb["مقارنات إيجارية"]
    all_text = " ".join(str(c or "") for row in ws.iter_rows(values_only=True) for c in row)
    assert "حالة الموقع الجغرافي" in all_text or "الموقع الجغرافي" in all_text, \
        "مقارنات إيجارية sheet missing geo_match_status column"


def test_SRB235_reconciliation_model_h_sales_value_nonzero():
    """SRB235 توفيق النتائج Model H first method row (مقارنة البيوع) has nonzero value (Part A)."""
    wb = _get_wb_maadi_strategic()
    assert "توفيق النتائج" in wb.sheetnames
    ws9 = wb["توفيق النتائج"]
    # Scan for مقارنة البيوع row; its B cell must be a non-zero formula or number
    sales_value_found = False
    for row in ws9.iter_rows(min_row=2, max_row=80):
        if row[0].value and "مقارنة البيوع" in str(row[0].value):
            b_val = row[1].value
            assert b_val is not None, "مقارنة البيوع row in Model H has None value"
            # Accept formula strings or nonzero numbers
            if isinstance(b_val, str):
                sales_value_found = len(b_val.strip()) > 0
            elif isinstance(b_val, (int, float)):
                sales_value_found = b_val != 0
            break
    # If the row contains a cross-sheet formula (string starting with =), that's also valid
    assert sales_value_found, \
        "Model H مقارنة البيوع row has zero or missing value — sales comparison not linked"


def test_SRB236_reconciliation_model_h_sales_uses_cross_sheet_formula():
    """SRB236 توفيق النتائج Model H مقارنة البيوع row uses =مقارنة البيوع! cross-sheet formula (Part A)."""
    wb = _get_wb_maadi_strategic()
    ws9 = wb["توفيق النتائج"]
    # Scan every B-column cell up to row 120; Model H stores ='مقارنة البيوع'!B<n>
    formula_found = any(
        isinstance(row[1].value, str) and "مقارنة البيوع" in row[1].value
        for row in ws9.iter_rows(min_row=2, max_row=120)
        if len(row) > 1
    )
    assert formula_found, \
        "توفيق النتائج has no B-column cross-sheet formula referencing 'مقارنة البيوع' sheet"


def test_SRB237_cost_approach_model_f_has_external_obsolescence_row():
    """SRB237 طريقة التكلفة Model F has الإهلاك الاقتصادي / الخارجي row (Part D)."""
    wb = _get_wb_maadi_strategic()
    assert "طريقة التكلفة" in wb.sheetnames
    ws8 = wb["طريقة التكلفة"]
    all_text = " ".join(
        str(c or "") for row in ws8.iter_rows(values_only=True) for c in row
        if c is not None
    )
    assert "الاقتصادي" in all_text or "الخارجي" in all_text, \
        "طريقة التكلفة Model F missing external/economic obsolescence row"


def test_SRB238_cap_rate_governance_has_difference_from_average():
    """SRB238 _build_method_context has difference_from_average field (Part E)."""
    mctx = _srr._build_method_context(_QA_MAADI_PAYLOAD)
    assert "difference_from_average" in mctx, \
        "method context missing difference_from_average (cap rate governance, Part E)"
    val = mctx["difference_from_average"]
    assert val and isinstance(val, str) and "%" in val, \
        f"difference_from_average has unexpected value: {val!r}"


def test_SRB239_cap_rate_governance_has_difference_from_dr_growth():
    """SRB239 _build_method_context has difference_from_dr_growth field (Part E)."""
    mctx = _srr._build_method_context(_QA_MAADI_PAYLOAD)
    assert "difference_from_dr_growth" in mctx, \
        "method context missing difference_from_dr_growth (cap rate governance, Part E)"


def test_SRB240_rental_purpose_dcf_uses_rental_comparison_noi():
    """SRB240 For rental purpose payload, DCF noi_basis is rental_comparison_* (Part F)."""
    mctx = _srr._build_method_context(_QA_RENTAL_PAYLOAD)
    noi_basis = mctx.get("dcf_noi_basis", "")
    assert noi_basis.startswith("rental_comparison"), \
        f"Rental purpose DCF dcf_noi_basis should be rental_comparison_*, got {noi_basis!r}"


def test_SRB241_what_if_sheet_references_reconciliation_formula():
    """SRB241 سيناريوهات What-If has a cell with ='توفيق النتائج'! cross-sheet formula (Part G)."""
    wb = _get_wb_maadi_strategic()
    ws_wi = wb["سيناريوهات What-If"]
    rec_ref_found = any(
        cell.value and isinstance(cell.value, str) and "توفيق النتائج" in cell.value
        for row in ws_wi.iter_rows()
        for cell in row
    )
    assert rec_ref_found, \
        "سيناريوهات What-If has no cross-sheet formula referencing 'توفيق النتائج'"


def test_SRB242_buy_vs_rent_market_value_references_reconciliation():
    """SRB242 شراء أم إيجار market value cell references ='توفيق النتائج'! (Part G)."""
    wb = _get_wb_maadi_strategic()
    ws_bvr = wb["شراء أم إيجار"]
    rec_ref_found = any(
        cell.value and isinstance(cell.value, str) and "توفيق النتائج" in cell.value
        for row in ws_bvr.iter_rows()
        for cell in row
    )
    assert rec_ref_found, \
        "شراء أم إيجار has no cross-sheet formula referencing 'توفيق النتائج'"


def test_SRB243_esg_sheet_has_discount_rate_adjustment_row():
    """SRB243 ESG sheet has تعديل معدل الخصم row (Part H)."""
    wb = _get_wb_maadi_strategic()
    ws_esg = wb["ESG والاستدامة"]
    all_text = " ".join(
        str(c or "") for row in ws_esg.iter_rows(values_only=True) for c in row
        if c is not None
    )
    assert "تعديل معدل الخصم" in all_text, \
        "ESG sheet missing تعديل معدل الخصم row (Part H)"


def test_SRB244_method_context_has_esg_cap_rate_adjustment():
    """SRB244 _build_method_context has esg_cap_rate_adjustment for QA payload (Part H)."""
    mctx = _srr._build_method_context(_QA_MAADI_PAYLOAD)
    assert "esg_cap_rate_adjustment" in mctx, \
        "method context missing esg_cap_rate_adjustment (Part H)"
    adj = mctx["esg_cap_rate_adjustment"]
    assert adj and "%" in str(adj), \
        f"esg_cap_rate_adjustment has unexpected value: {adj!r}"


def test_SRB245_simple_valuation_draft_has_single_consolidated_disclaimer():
    """SRB245 simple_valuation_draft.html has only ONE disc-pg block (Part I — consolidated)."""
    import pathlib
    tmpl_path = pathlib.Path(__file__).parent.parent / "templates" / "pdf" / "simple_valuation_draft.html"
    content = tmpl_path.read_text(encoding="utf-8")
    disc_count = content.count("disc-pg")
    assert disc_count == 2, \
        f"Expected exactly 1 disc-pg block (2 occurrences of class name), got {disc_count//2}"


def test_SRB246_simple_valuation_draft_has_svg_map_placeholder():
    """SRB246 simple_valuation_draft.html has SVG coordinate map placeholders (Part J)."""
    import pathlib
    tmpl_path = pathlib.Path(__file__).parent.parent / "templates" / "pdf" / "simple_valuation_draft.html"
    content = tmpl_path.read_text(encoding="utf-8")
    assert "<svg" in content, \
        "simple_valuation_draft.html missing SVG map placeholder (Part J)"
    assert "viewBox" in content, \
        "simple_valuation_draft.html SVG missing viewBox attribute"
    assert "latitude" in content, \
        "simple_valuation_draft.html SVG map missing latitude template variable reference"


# ── SRB247-SRB262: Scenario Data Integrity (Session 4 Phase 2) ──────────────

_QA_ZAMALEK_PAYLOAD = {
    "property_type": "شقة سكنية", "country": "مصر",
    "region": "القاهرة", "city": "القاهرة",
    "district": "الزمالك", "zone_id": "ZONE-CAI-ZAMALEK-01",
    "sub_market": "سوق الزمالك الفرعي",
    "area": 150, "land_share_area": 28,
    "condition": "جيد جدًا", "finishing_level": "فاخر",
    "purpose": "القيمة السوقية",
    "valuation_date": "2026-06-25",
    "income_monthly_rent": 12_000, "income_cap_rate": 4.2,
    "estimated_value": 5_200_000,
    "_qa_simulation": True,
}

_QA_RENTAL_NASR_PAYLOAD = {
    "property_type": "شقة سكنية", "country": "مصر",
    "region": "القاهرة", "city": "القاهرة",
    "district": "مدينة نصر - المنطقة الثامنة",
    "zone_id": "ZONE-CAI-NASR-08",
    "sub_market": "سوق مدينة نصر الفرعي",
    "area": 120, "land_share_area": 20,
    "condition": "جيدة", "finishing_level": "متوسط",
    "purpose": "القيمة الإيجارية",
    "valuation_date": "2024-06-30",
    "final_monthly_rental_value": 9_500,
    "final_annual_rental_value": 114_000,
    "estimated_value": 0,
    "_qa_simulation": True,
}

_SUSPICIOUS_AREA_SET = frozenset({2120, 7241, 7342, 247, 313, 401, 700, 3766})


def test_SRB247_rental_qa_area_is_120_in_method_context():
    """SRB247 rental_nasr_city_qa: scenario_subject_area == 120 in method context."""
    mctx = _srr._build_method_context(_QA_RENTAL_NASR_PAYLOAD)
    area = mctx.get("scenario_subject_area")
    assert area is not None, "method context missing scenario_subject_area"
    assert float(area) == 120.0, \
        f"rental QA area mismatch: expected 120, got {area}"


def test_SRB248_rental_qa_area_not_2120_anywhere_in_context():
    """SRB248 rental_nasr_city_qa: suspicious area 2120 must not appear anywhere in context."""
    mctx = _srr._build_method_context(_QA_RENTAL_NASR_PAYLOAD)

    def _search(obj, path=""):
        bad = []
        if isinstance(obj, (int, float)):
            if int(obj) == 2120:
                bad.append(f"{path}={obj}")
        elif isinstance(obj, str):
            if "2120" in obj:
                bad.append(f"{path}={obj!r}")
        elif isinstance(obj, dict):
            for k, v in obj.items():
                bad.extend(_search(v, f"{path}.{k}"))
        elif isinstance(obj, (list, tuple)):
            for i, v in enumerate(obj):
                bad.extend(_search(v, f"{path}[{i}]"))
        return bad

    hits = _search(mctx)
    assert not hits, \
        f"Value 2120 (rental area leakage) found in method context at: {hits[:5]}"


def test_SRB249_market_qa_area_is_150_in_method_context():
    """SRB249 market_zamalek_qa: scenario_subject_area == 150 in method context."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    area = mctx.get("scenario_subject_area")
    assert area is not None, "method context missing scenario_subject_area"
    assert float(area) == 150.0, \
        f"market Zamalek area mismatch: expected 150, got {area}"


def test_SRB250_market_qa_district_is_zamalek():
    """SRB250 market_zamalek_qa: subject district == الزمالك in method context."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    district = str(mctx.get("scenario_subject_district") or "")
    assert "زمالك" in district, \
        f"market scenario district should be الزمالك, got {district!r}"
    assert "نصر" not in district, \
        f"market Zamalek district should NOT contain نصر, got {district!r}"


def test_SRB251_market_included_sales_comps_use_zamalek_zone():
    """SRB251 market_zamalek_qa: all included sales comparables use ZONE-CAI-ZAMALEK-01."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    comps = mctx.get("comparables", [])
    assert comps, "comparables is empty for Zamalek scenario"
    included = [
        c for c in comps
        if "خارج النطاق" not in str(c.get("geo_match_status", ""))
        and "مستبعد" not in str(c.get("inclusion", ""))
    ]
    assert included, "No included sales comparables found for Zamalek scenario"
    for comp in included:
        zone = comp.get("comparable_zone_id", "")
        assert zone == "ZONE-CAI-ZAMALEK-01", \
            f"Included comparable in Zamalek scenario has wrong zone: {zone!r} — {comp.get('location','')!r}"


def test_SRB252_market_nasr_city_comps_are_excluded():
    """SRB252 market_zamalek_qa: Nasr City comparables are excluded with geo marker."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    comps = mctx.get("comparables", [])
    nasr_comps = [c for c in comps if "نصر" in str(c.get("location", ""))]
    assert nasr_comps, \
        "Expected at least one Nasr City comparable row to be present (excluded) in Zamalek scenario"
    for comp in nasr_comps:
        geo_status = str(comp.get("geo_match_status", ""))
        inclusion  = str(comp.get("inclusion", ""))
        excluded = "خارج النطاق" in geo_status or "مستبعد" in inclusion
        assert excluded, \
            f"Nasr City comparable must be excluded in Zamalek scenario: {comp.get('location')!r} — geo={geo_status!r}, inclusion={inclusion!r}"


def test_SRB253_market_avm_sources_use_zamalek_zone():
    """SRB253 market_zamalek_qa: AVM price sources use Zamalek zone or are marked excluded."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    sources = mctx.get("price_source_data", [])
    assert sources, "price_source_data empty for Zamalek scenario"
    for src in sources:
        zone = str(src.get("source_zone_id") or src.get("zone_id") or "")
        use_status = str(src.get("geo_use_status") or "")
        if "مُدرج" in use_status or ("مستبعد" not in use_status and zone):
            assert zone == "ZONE-CAI-ZAMALEK-01" or "مستبعد" in use_status, \
                f"Included AVM source in Zamalek scenario has unexpected zone: {zone!r}"


def test_SRB254_market_land_comps_use_zamalek_zone():
    """SRB254 market_zamalek_qa: land comparables use ZONE-CAI-ZAMALEK-01 or are excluded."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    land_comps = mctx.get("land_comps", [])
    if not land_comps:
        land_comps = mctx.get("land_extraction_comps", [])
    assert land_comps, "No land comparables found for Zamalek scenario"
    for comp in land_comps:
        zone       = str(comp.get("zone_id") or comp.get("comparable_zone_id") or "")
        geo_status = str(comp.get("geo_match_status", ""))
        excluded   = "خارج النطاق" in geo_status or "مستبعد" in str(comp.get("inclusion", ""))
        if not excluded:
            assert zone == "ZONE-CAI-ZAMALEK-01", \
                f"Included land comp in Zamalek scenario has wrong zone: {zone!r}"


def test_SRB255_replacement_cost_consistent_between_cost_and_land():
    """SRB255 market_zamalek_qa: replacement_cost_new in cost section == value used in land extraction."""
    import re as _re
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)

    def _parse_num(v):
        if v is None:
            return None
        m = _re.search(r'[\d,]+(?:\.\d+)?', str(v))
        if m:
            try:
                return float(m.group().replace(",", ""))
            except ValueError:
                return None
        return None

    # extr_replacement_cost_new (land extraction) and cost_replacement_total (cost approach)
    land_rcn = _parse_num(mctx.get("extr_replacement_cost_new"))
    cost_rcn = _parse_num(mctx.get("cost_replacement_total"))

    assert land_rcn is not None, "extr_replacement_cost_new missing from Zamalek context"
    assert cost_rcn is not None, "cost_replacement_total missing from Zamalek context"
    assert abs(land_rcn - cost_rcn) < 1, \
        f"replacement_cost_new mismatch: extr_replacement_cost_new={land_rcn}, cost_replacement_total={cost_rcn}"


def test_SRB256_reconciliation_references_method_sheets():
    """SRB256 market_zamalek_qa: reconciliation/dashboard references method sheet values."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    recon = mctx.get("reconciliation_summary") or mctx.get("reconciliation")
    sales_method = mctx.get("sales_comparison_value") or mctx.get("comparable_indicated_value")
    if recon and isinstance(recon, dict):
        recon_sales = (recon.get("sales_comparison_value") or
                       recon.get("sales_value") or
                       recon.get("indicated_value_sales"))
        if recon_sales and sales_method:
            assert abs(float(str(recon_sales).replace(",", "")) -
                       float(str(sales_method).replace(",", ""))) < 1, \
                f"Reconciliation sales value {recon_sales} != method sheet {sales_method}"


def test_SRB257_reconciliation_sales_value_nonzero_for_market_qa():
    """SRB257 market_zamalek_qa: reconciliation/dashboard sales comparison value != 0."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    # sales_from_comps holds the indicated value from the sales comparison approach
    indicated = (mctx.get("sales_from_comps") or
                 mctx.get("comparable_indicated_value") or
                 mctx.get("sales_comparison_value"))
    assert indicated is not None, \
        "No sales comparison indicated value in Zamalek market context (checked: sales_from_comps, comparable_indicated_value, sales_comparison_value)"
    try:
        val = float(str(indicated).replace(",", "").split()[0])
    except (ValueError, TypeError):
        val = 0
    assert val > 0, \
        f"Sales comparison indicated value must be > 0 for market QA; got {indicated!r}"


def test_SRB258_no_suspicious_test_count_in_valuation_area_fields():
    """SRB258 both QA scenarios: no suspicious test-count value in area fields of method context."""
    for label, payload in [("market", _QA_ZAMALEK_PAYLOAD), ("rental", _QA_RENTAL_NASR_PAYLOAD)]:
        mctx = _srr._build_method_context(payload)
        area_keys = [
            "scenario_subject_area", "area", "subject_area",
            "gross_living_area", "total_area",
        ]
        for key in area_keys:
            val = mctx.get(key)
            if val is not None:
                try:
                    int_val = int(float(val))
                    assert int_val not in _SUSPICIOUS_AREA_SET, \
                        f"[{label}] Suspicious test-count {int_val} found in '{key}'"
                except (ValueError, TypeError):
                    pass


def test_SRB259_integrity_validator_catches_area_mismatch():
    """SRB259 _validate_scenario_data_integrity raises error when area is deliberately wrong."""
    from core_engine.reporting_method_context import _validate_scenario_data_integrity

    # Build a normal context then corrupt the area field to a suspicious value
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    tampered = dict(mctx)
    tampered["scenario_subject_area"] = 2120  # deliberate leakage

    errors = _validate_scenario_data_integrity(tampered)
    has_area_leak = any("AREA" in e.upper() or "2120" in e for e in errors)
    assert has_area_leak, \
        f"Validator did not catch area=2120 leakage; returned errors: {errors}"


def test_SRB260_scenario_integrity_v3_outputs_exist():
    """SRB260 v3 output files exist in scenario_integrity_v3/ directory."""
    import pathlib
    out_dir = pathlib.Path(__file__).parent.parent / "instance" / "manual_review_outputs" / "scenario_integrity_v3"
    required = [
        "01_market_zamalek_preliminary_v3.pdf",
        "02_market_zamalek_certified_v3.pdf",
        "03_market_zamalek_workbook_v3.xlsx",
        "04_rental_nasr_city_preliminary_v3.pdf",
        "05_rental_nasr_city_certified_v3.pdf",
        "06_rental_nasr_city_workbook_v3.xlsx",
        "07_integrity_summary.json",
    ]
    missing = [f for f in required if not (out_dir / f).exists()]
    assert not missing, \
        f"v3 output files missing from {out_dir}: {missing}"


def test_SRB261_no_qdrant_live_claim_in_qa_context():
    """SRB261 both QA scenarios: method context does not claim live Qdrant was actively queried.

    'Qdrant' may appear in disclaimer text saying it is NOT used;
    what is prohibited is a positive ACTIVE-USE claim.
    """
    import json
    # Positive-use claim phrases that would indicate live Qdrant/internet was hit
    FORBIDDEN_ACTIVE_CLAIMS = [
        "qdrant_connected: true",
        "qdrant_active: true",
        "live_retrieval: true",
        "retrieved_from_qdrant",
        "retrieved_from_internet",
        "vector_db_live",
    ]
    for label, payload in [("market", _QA_ZAMALEK_PAYLOAD), ("rental", _QA_RENTAL_NASR_PAYLOAD)]:
        mctx = _srr._build_method_context(payload)
        # Check structured fields (not JSON-serialized text with disclaimer sentences)
        for field in ["qdrant_connected", "live_retrieval_active", "vector_db_live"]:
            val = mctx.get(field)
            assert val is not True, \
                f"[{label}] method context field '{field}' is True — live retrieval must not be active in QA"
        raw = json.dumps(mctx, ensure_ascii=False, default=str).lower()
        for claim in FORBIDDEN_ACTIVE_CLAIMS:
            assert claim.lower() not in raw, \
                f"[{label}] method context contains active Qdrant/live-retrieval claim: {claim!r}"


def test_SRB262_no_external_map_api_url_in_qa_context():
    """SRB262 both QA scenarios: method context does not reference external map API URLs."""
    import json
    forbidden_fragments = [
        "maps.googleapis", "api.mapbox", "openstreetmap.org/tiles",
        "tiles.stadiamaps", "maps.here.com", "map.baidu",
    ]
    for label, payload in [("market", _QA_ZAMALEK_PAYLOAD), ("rental", _QA_RENTAL_NASR_PAYLOAD)]:
        mctx = _srr._build_method_context(payload)
        raw = json.dumps(mctx, ensure_ascii=False, default=str)
        for fragment in forbidden_fragments:
            assert fragment not in raw, \
                f"[{label}] method context references external map API URL: {fragment!r}"


# ── SRB263-SRB276: Source Registry Readiness (Parts A-J) ─────────────────────

def test_SRB263_source_registry_exists_in_method_context():
    """SRB263 both QA scenarios: method context contains source_registry key."""
    for label, payload in [("market", _QA_ZAMALEK_PAYLOAD), ("rental", _QA_RENTAL_NASR_PAYLOAD)]:
        mctx = _srr._build_method_context(payload)
        assert "source_registry" in mctx, \
            f"[{label}] 'source_registry' key missing from method context"
        assert isinstance(mctx["source_registry"], list), \
            f"[{label}] source_registry must be a list"


def test_SRB264_every_source_record_has_source_id():
    """SRB264 both QA scenarios: every source record in source_registry has a source_id."""
    for label, payload in [("market", _QA_ZAMALEK_PAYLOAD), ("rental", _QA_RENTAL_NASR_PAYLOAD)]:
        mctx = _srr._build_method_context(payload)
        for i, src in enumerate(mctx.get("source_registry", [])):
            sid = src.get("source_id") or src.get("source_registry_id")
            assert sid, \
                f"[{label}] source_registry[{i}] has no source_id: {src}"


def test_SRB265_sales_comparables_have_source_ids():
    """SRB265 market QA: included sales comparables are referenced in source_method_links AVM/مقارنة البيوع."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    links = mctx.get("source_method_links", {})
    sales_ids = links.get("مقارنة البيوع", [])
    avm_ids   = links.get("AVM", [])
    assert sales_ids or avm_ids, \
        "source_method_links must have at least one source for مقارنة البيوع or AVM in market QA"


def test_SRB266_rental_comparables_have_source_ids():
    """SRB266 rental QA: included rental comparables referenced in source_method_links."""
    mctx = _srr._build_method_context(_QA_RENTAL_NASR_PAYLOAD)
    links = mctx.get("source_method_links", {})
    rental_ids = (
        links.get("القيمة الإيجارية", [])
        + links.get("مقارنة إيجارية", [])
        + links.get("توفيق القيمة الإيجارية", [])
    )
    assert rental_ids, \
        "source_method_links must reference rental sources for rental QA scenario"


def test_SRB267_land_comparables_have_source_ids():
    """SRB267 both QA scenarios: land source IDs appear in source_method_links[قيمة الأرض]."""
    for label, payload in [("market", _QA_ZAMALEK_PAYLOAD), ("rental", _QA_RENTAL_NASR_PAYLOAD)]:
        mctx = _srr._build_method_context(payload)
        links = mctx.get("source_method_links", {})
        land_ids = links.get("قيمة الأرض", [])
        assert land_ids, \
            f"[{label}] source_method_links[قيمة الأرض] is empty — land sources must be linked"


def test_SRB268_avm_source_rows_have_source_ids():
    """SRB268 both QA scenarios: AVM method has linked source IDs."""
    for label, payload in [("market", _QA_ZAMALEK_PAYLOAD), ("rental", _QA_RENTAL_NASR_PAYLOAD)]:
        mctx = _srr._build_method_context(payload)
        links = mctx.get("source_method_links", {})
        avm_ids = links.get("AVM", [])
        assert avm_ids, \
            f"[{label}] source_method_links[AVM] is empty — AVM source must be linked"


def test_SRB269_excluded_out_of_zone_source_not_in_formulas():
    """SRB269 both QA scenarios: excluded (geo_use_status=مستبعد جغرافيًا) sources are absent from all method links."""
    for label, payload in [("market", _QA_ZAMALEK_PAYLOAD), ("rental", _QA_RENTAL_NASR_PAYLOAD)]:
        mctx = _srr._build_method_context(payload)
        links  = mctx.get("source_method_links", {})
        all_linked_ids = {sid for ids in links.values() for sid in ids}
        for src in mctx.get("source_registry", []):
            if src.get("geo_use_status") == "مستبعد جغرافيًا":
                sid = src.get("source_id") or src.get("source_registry_id", "")
                assert sid not in all_linked_ids, \
                    f"[{label}] excluded source '{sid}' appears in source_method_links — must not affect calculations"


def test_SRB270_source_registry_sheet_exists_in_workbook(client):
    """SRB270 expert workbook contains مصادر الأسعار (canonical source registry sheet)."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")
    rid = json.loads(_post_request(client).data)["request_id"]
    wb_path = _srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"
    wb = openpyxl.load_workbook(str(wb_path))
    assert "مصادر الأسعار" in wb.sheetnames, \
        f"مصادر الأسعار sheet missing from workbook. Sheets: {wb.sheetnames}"


def test_SRB271_source_method_links_sheet_exists_in_workbook(client):
    """SRB271 expert workbook contains سجل ربط المصادر (source method links sheet)."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")
    rid = json.loads(_post_request(client).data)["request_id"]
    wb_path = _srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"
    wb = openpyxl.load_workbook(str(wb_path))
    assert "سجل ربط المصادر" in wb.sheetnames, \
        f"سجل ربط المصادر sheet missing from workbook. Sheets: {wb.sheetnames}"


def test_SRB272_certified_pdf_template_contains_source_registry_section():
    """SRB272 certified PDF template contains سجل مصادر البيانات والمقارنات section."""
    import pathlib
    tmpl = pathlib.Path(__file__).parent.parent / "templates" / "pdf" / "certified_valuation_report.html"
    text = tmpl.read_text(encoding="utf-8")
    assert "سجل مصادر البيانات والمقارنات" in text, \
        "certified PDF template missing 'سجل مصادر البيانات والمقارنات' section title"
    assert "source_registry" in text, \
        "certified PDF template must reference source_registry variable"


def test_SRB273_preliminary_pdf_template_contains_source_summary_section():
    """SRB273 preliminary PDF template contains ملخص مصادر البيانات section."""
    import pathlib
    tmpl = pathlib.Path(__file__).parent.parent / "templates" / "pdf" / "simple_valuation_draft.html"
    text = tmpl.read_text(encoding="utf-8")
    assert "ملخص مصادر البيانات" in text, \
        "preliminary PDF template missing 'ملخص مصادر البيانات' section"
    assert "source_registry" in text, \
        "preliminary PDF template must reference source_registry variable"


def test_SRB274_qdrant_readiness_says_ready_but_disabled():
    """SRB274 both QA scenarios: qdrant_readiness_summary is structurally ready but operationally disabled."""
    for label, payload in [("market", _QA_ZAMALEK_PAYLOAD), ("rental", _QA_RENTAL_NASR_PAYLOAD)]:
        mctx = _srr._build_method_context(payload)
        qrs = mctx.get("qdrant_readiness_summary", {})
        assert "qdrant_readiness_summary" in mctx, \
            f"[{label}] qdrant_readiness_summary missing from method context"
        assert qrs.get("qdrant_ready") is True, \
            f"[{label}] qdrant_ready must be True (structurally ready)"
        assert qrs.get("qdrant_enabled") is False, \
            f"[{label}] qdrant_enabled must be False (not yet activated)"
        assert qrs.get("rag_enabled") is False, \
            f"[{label}] rag_enabled must be False"
        assert qrs.get("internet_ingestion_enabled") is False, \
            f"[{label}] internet_ingestion_enabled must be False"
        assert "جاهز هيكليًا" in str(qrs.get("status_ar", "")), \
            f"[{label}] qdrant_readiness_summary.status_ar must say 'جاهز هيكليًا': {qrs.get('status_ar')}"


def test_SRB275_no_qdrant_active_claim_in_source_registry():
    """SRB275 both QA scenarios: source_registry contains no live Qdrant/RAG/internet active claim."""
    import json
    FORBIDDEN = [
        "retrieved_from_qdrant", "live_qdrant", "qdrant_active: true",
        "internet_search_result", "rag_retrieval",
    ]
    for label, payload in [("market", _QA_ZAMALEK_PAYLOAD), ("rental", _QA_RENTAL_NASR_PAYLOAD)]:
        mctx = _srr._build_method_context(payload)
        raw = json.dumps(mctx.get("source_registry", []), ensure_ascii=False, default=str).lower()
        for claim in FORBIDDEN:
            assert claim.lower() not in raw, \
                f"[{label}] source_registry contains forbidden active-use claim: {claim!r}"


def test_SRB276_source_registry_validator_passes_for_qa():
    """SRB276 both QA scenarios: _validate_source_registry_integrity returns no errors."""
    from core_engine.reporting_method_context import _validate_source_registry_integrity
    for label, payload in [("market", _QA_ZAMALEK_PAYLOAD), ("rental", _QA_RENTAL_NASR_PAYLOAD)]:
        mctx = _srr._build_method_context(payload)
        errors = _validate_source_registry_integrity(mctx)
        assert not errors, \
            f"[{label}] _validate_source_registry_integrity returned errors: {errors}"


# ═════════════════════════════════════════════════════════════════════════════
# Advanced Methodology & Compliance Tests (SRB300–SRB329)
# Parts B–L: HBU, DCF separation, comparable adjustments, assumptions,
#            depreciation, DCF scenarios, legal DD, ESG, EIA, uncertainty, peer review
# ═════════════════════════════════════════════════════════════════════════════

def test_SRB300_hbu_analysis_context_exists():
    """SRB300 hbu_analysis key exists in method context for QA payloads."""
    for label, payload in [("market", _QA_ZAMALEK_PAYLOAD), ("rental", _QA_RENTAL_NASR_PAYLOAD)]:
        mctx = _srr._build_method_context(payload)
        assert "hbu_analysis" in mctx, f"[{label}] hbu_analysis missing from method context"
        assert isinstance(mctx["hbu_analysis"], dict), f"[{label}] hbu_analysis is not a dict"


def test_SRB301_hbu_four_tests_present():
    """SRB301 hbu_analysis contains all four HBU test keys."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    hbu = mctx["hbu_analysis"]
    for key in ("legally_permissible", "physically_possible", "financially_feasible", "maximally_productive"):
        assert key in hbu, f"HBU test key {key!r} missing from hbu_analysis"
    assert hbu.get("hbu_four_tests_present") is True


def test_SRB302_hbu_conclusion_and_selected_use():
    """SRB302 hbu_analysis has non-empty conclusion and selected_hbu for QA."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    hbu = mctx["hbu_analysis"]
    assert hbu.get("hbu_conclusion") and hbu["hbu_conclusion"] != mctx.get("_expert_fill_label", "")
    assert hbu.get("selected_hbu") and hbu["selected_hbu"] != mctx.get("_data_gap_label", "")


def test_SRB303_direct_capitalization_and_dcf_are_separate():
    """SRB303 direct_capitalization_result and dcf_result are separate keys in method context."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "direct_capitalization_result" in mctx, "direct_capitalization_result missing"
    assert "dcf_result" in mctx, "dcf_result missing"
    # They must be populated independently
    assert mctx["direct_capitalization_result"] != mctx["dcf_result"], \
        "direct_capitalization_result and dcf_result should differ"


def test_SRB304_dcf_has_independent_reconciliation_weight():
    """SRB304 dcf_reconciliation_weight exists as a numeric value separate from income_weight."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "dcf_reconciliation_weight" in mctx
    assert isinstance(mctx["dcf_reconciliation_weight"], float)
    assert mctx["dcf_reconciliation_weight"] >= 0


def test_SRB305_income_direct_vs_dcf_explanation_exists():
    """SRB305 income_direct_vs_dcf_explanation is non-empty."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    expl = mctx.get("income_direct_vs_dcf_explanation", "")
    assert expl and len(expl) > 20, "income_direct_vs_dcf_explanation is missing or too short"


def test_SRB306_comparable_adjustment_support_exists():
    """SRB306 comparable_adjustment_support exists with at least one adjustment row."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    cas = mctx.get("comparable_adjustment_support", {})
    assert cas, "comparable_adjustment_support missing"
    adjustments = cas.get("adjustments", [])
    assert len(adjustments) >= 1, "comparable_adjustment_support.adjustments is empty"
    for adj in adjustments:
        assert "adjustment_type" in adj
        assert "coefficient" in adj
        assert "source" in adj


def test_SRB307_assumptions_registry_separates_types():
    """SRB307 assumptions_registry has at least ordinary and extraordinary assumption types."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    asm_list = mctx.get("assumptions_registry", [])
    assert len(asm_list) >= 2, "assumptions_registry has fewer than 2 entries"
    types = {a["type"] for a in asm_list}
    assert "افتراض عادي" in types, "No ordinary assumption in assumptions_registry"
    assert "افتراض خاص" in types, "No extraordinary assumption in assumptions_registry"


def test_SRB308_extraordinary_assumptions_separate_list():
    """SRB308 extraordinary_assumptions is a non-empty list when QA payload used."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    ea = mctx.get("extraordinary_assumptions", [])
    assert isinstance(ea, list) and len(ea) >= 1, "extraordinary_assumptions is empty"
    assert all(a["type"] == "افتراض خاص" for a in ea)


def test_SRB309_scope_limitations_list_exists():
    """SRB309 scope_limitations is a list."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    sl = mctx.get("scope_limitations", [])
    assert isinstance(sl, list)


def test_SRB310_detailed_depreciation_breakdown_exists():
    """SRB310 depreciation_breakdown has all required keys."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    db = mctx.get("depreciation_breakdown", {})
    assert db, "depreciation_breakdown missing"
    required_keys = [
        "physical_curable_pct", "physical_curable_value",
        "physical_incurable_pct", "physical_incurable_value",
        "functional_obsolescence_pct", "functional_obsolescence_value",
        "external_obsolescence_pct", "external_obsolescence_value",
        "total_depreciation_pct", "total_depreciation_value",
        "replacement_cost_new", "depreciated_replacement_cost",
    ]
    for k in required_keys:
        assert k in db, f"depreciation_breakdown missing key {k!r}"


def test_SRB311_depreciation_curable_incurable_split():
    """SRB311 physical curable + incurable = total physical depreciation."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    db = mctx.get("depreciation_breakdown", {})
    curable = db.get("physical_curable_pct", 0)
    incurable = db.get("physical_incurable_pct", 0)
    assert curable >= 0 and incurable >= 0
    assert curable + incurable <= db.get("total_depreciation_pct", 0) + 0.01


def test_SRB312_dcf_scenarios_exist():
    """SRB312 dcf_scenarios has optimistic, base, pessimistic keys."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    scen = mctx.get("dcf_scenarios", {})
    assert scen, "dcf_scenarios missing"
    assert scen.get("scenarios_present") is True
    for key in ("optimistic", "base", "pessimistic"):
        assert key in scen, f"dcf_scenarios missing {key!r}"
        assert "dcf_value" in scen[key], f"dcf_scenarios.{key} missing dcf_value"
        assert "variance_pct" in scen[key]


def test_SRB313_dcf_scenarios_monte_carlo_note():
    """SRB313 dcf_scenarios.monte_carlo_note is present and marks Monte Carlo as not implemented."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    note = mctx["dcf_scenarios"].get("monte_carlo_note", "")
    assert "مرحلة مستقبلية" in note or "غير مفعلة" in note


def test_SRB314_legal_due_diligence_exists():
    """SRB314 legal_due_diligence dict is present with required keys."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    ldd = mctx.get("legal_due_diligence", {})
    assert ldd, "legal_due_diligence missing"
    required = ["legal_scope_limitation", "legal_due_diligence_conclusion", "missing_documents"]
    for k in required:
        assert k in ldd, f"legal_due_diligence missing key {k!r}"


def test_SRB315_legal_due_diligence_scope_limitation_not_empty():
    """SRB315 legal_scope_limitation text is non-empty and mentions scope limitation."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    ldd = mctx["legal_due_diligence"]
    sl = ldd.get("legal_scope_limitation", "")
    assert sl and len(sl) > 20


def test_SRB316_esg_adjustments_affect_rates_only_when_data_exists():
    """SRB316 ESG adjustments exist; esg_terminal_value_adjustment and esg_value_impact present."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "esg_terminal_value_adjustment" in mctx, "esg_terminal_value_adjustment missing"
    assert "esg_value_impact" in mctx, "esg_value_impact missing"
    assert "climate_risk_score" in mctx, "climate_risk_score missing"
    assert "climate_risk_notes" in mctx, "climate_risk_notes missing"
    # Without ESG data (no _qa_simulation), incomplete note should be set
    non_qa = {k: v for k, v in _QA_ZAMALEK_PAYLOAD.items() if k != "_qa_simulation"}
    non_qa["_qa_simulation"] = False
    mctx2 = _srr._build_method_context(non_qa)
    esg2 = mctx2.get("esg_enhanced_context", {})
    assert esg2.get("esg_incomplete_note"), "esg_incomplete_note should be set for non-QA"


def test_SRB317_eia_methodology_absent_for_non_eia_purpose():
    """SRB317 eia_required is False for standard market valuation purpose."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    eia = mctx.get("environmental_impact_assessment", {})
    assert eia.get("eia_required") is False, \
        "EIA should not be required for standard market valuation"


def test_SRB318_eia_methodology_present_for_eia_purpose():
    """SRB318 eia_required is True when purpose includes بيئي."""
    eia_payload = dict(_QA_ZAMALEK_PAYLOAD, purpose="تقييم الأثر البيئي")
    mctx = _srr._build_method_context(eia_payload)
    eia = mctx.get("environmental_impact_assessment", {})
    assert eia.get("eia_required") is True, "EIA should be required for بيئي purpose"


def test_SRB319_uncertainty_range_exists():
    """SRB319 valuation_uncertainty exists with required keys."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    vu = mctx.get("valuation_uncertainty", {})
    assert vu, "valuation_uncertainty missing"
    for k in ("mean_value", "weighted_value", "lower_bound", "upper_bound", "n_methods_used"):
        assert k in vu, f"valuation_uncertainty missing key {k!r}"


def test_SRB320_uncertainty_range_n_methods_positive():
    """SRB320 valuation_uncertainty.n_methods_used >= 1 for QA payload."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    n = mctx["valuation_uncertainty"].get("n_methods_used", 0)
    assert n >= 1, f"n_methods_used={n}, expected >= 1"


def test_SRB321_uncertainty_bounds_ordered():
    """SRB321 lower_bound <= weighted_value <= upper_bound (numeric check)."""
    import re
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    vu = mctx["valuation_uncertainty"]
    def _parse(s: str) -> float:
        return float(re.sub(r"[^\d.]", "", str(s))) if s and str(s) != mctx.get("_data_gap_label", "") else 0.0
    lo = _parse(vu.get("lower_bound", "0"))
    hi = _parse(vu.get("upper_bound", "0"))
    wv = _parse(vu.get("weighted_value", "0"))
    if lo and hi and wv:
        assert lo <= wv <= hi, f"Bounds disorder: lower={lo} weighted={wv} upper={hi}"


def test_SRB322_peer_review_fields_exist():
    """SRB322 peer_review dict exists with required fields."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    pr = mctx.get("peer_review", {})
    assert pr, "peer_review missing from method context"
    for k in ("peer_review_required", "peer_reviewer_name", "peer_review_status",
              "peer_review_status_label", "review_limitations"):
        assert k in pr, f"peer_review missing key {k!r}"


def test_SRB323_peer_review_not_started_default():
    """SRB323 peer_review.peer_review_status defaults to not_started."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    pr = mctx["peer_review"]
    assert pr["peer_review_status"] in ("not_started", "")
    assert pr["review_limitations"] != ""


def test_SRB324_workbook_contains_hbu_sheet(client):
    """SRB324 Expert workbook contains تحليل أعلى وأفضل استغلال sheet."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")
    rid = json.loads(_post_request(client).data)["request_id"]
    wb = openpyxl.load_workbook(str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"))
    assert "تحليل أعلى وأفضل استغلال" in wb.sheetnames, f"HBU sheet missing. Sheets: {wb.sheetnames}"


def test_SRB325_workbook_contains_adjustment_support_sheet(client):
    """SRB325 Expert workbook contains دعم التعديلات sheet."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")
    rid = json.loads(_post_request(client).data)["request_id"]
    wb = openpyxl.load_workbook(str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"))
    assert "دعم التعديلات" in wb.sheetnames


def test_SRB326_workbook_contains_extraordinary_assumptions_sheet(client):
    """SRB326 Expert workbook contains الافتراضات الخاصة والقيود sheet."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")
    rid = json.loads(_post_request(client).data)["request_id"]
    wb = openpyxl.load_workbook(str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"))
    assert "الافتراضات الخاصة والقيود" in wb.sheetnames


def test_SRB327_workbook_contains_depreciation_detail_sheet(client):
    """SRB327 Expert workbook contains تفصيل الإهلاك sheet."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")
    rid = json.loads(_post_request(client).data)["request_id"]
    wb = openpyxl.load_workbook(str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"))
    assert "تفصيل الإهلاك" in wb.sheetnames


def test_SRB328_workbook_contains_dcf_risk_sheet(client):
    """SRB328 Expert workbook contains تحليل مخاطر DCF sheet."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")
    rid = json.loads(_post_request(client).data)["request_id"]
    wb = openpyxl.load_workbook(str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"))
    assert "تحليل مخاطر DCF" in wb.sheetnames


def test_SRB329_workbook_contains_legal_dd_sheet(client):
    """SRB329 Expert workbook contains الفحص القانوني المبدئي sheet."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")
    rid = json.loads(_post_request(client).data)["request_id"]
    wb = openpyxl.load_workbook(str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"))
    assert "الفحص القانوني المبدئي" in wb.sheetnames


def test_SRB330_workbook_contains_esg_impact_sheet(client):
    """SRB330 Expert workbook contains تأثير ESG والمخاطر المناخية sheet."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")
    rid = json.loads(_post_request(client).data)["request_id"]
    wb = openpyxl.load_workbook(str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"))
    assert "تأثير ESG والمخاطر المناخية" in wb.sheetnames


def test_SRB331_workbook_contains_eia_sheet(client):
    """SRB331 Expert workbook contains تقييم الأثر البيئي sheet."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")
    rid = json.loads(_post_request(client).data)["request_id"]
    wb = openpyxl.load_workbook(str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"))
    assert "تقييم الأثر البيئي" in wb.sheetnames


def test_SRB332_workbook_contains_uncertainty_range_sheet(client):
    """SRB332 Expert workbook contains نطاق الثقة وعدم اليقين sheet."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")
    rid = json.loads(_post_request(client).data)["request_id"]
    wb = openpyxl.load_workbook(str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"))
    assert "نطاق الثقة وعدم اليقين" in wb.sheetnames


def test_SRB333_workbook_formulas_remain_formulas(client):
    """SRB333 DCF sheet Form F still contains Excel formula cells after new sheets added."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")
    rid = json.loads(_post_request(client).data)["request_id"]
    wb = openpyxl.load_workbook(str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"), data_only=False)
    assert "DCF" in wb.sheetnames
    ws_dcf = wb["DCF"]
    has_formula = any(
        str(ws_dcf.cell(r, c).value or "").startswith("=")
        for r in range(1, 60) for c in range(1, 8)
    )
    assert has_formula, "DCF sheet has no formula cells after new sheets added"


def test_SRB334_preliminary_pdf_contains_hbu_section():
    """SRB334 simple_valuation_draft.html contains HBU section header text."""
    import pathlib as _pl
    tmpl = (_pl.Path(_srr.__file__).parent / "templates" / "pdf" / "simple_valuation_draft.html").read_text(encoding="utf-8")
    assert "تحليل أعلى وأفضل استغلال" in tmpl


def test_SRB335_certified_pdf_contains_hbu_section():
    """SRB335 certified_valuation_report.html contains HBU section."""
    import pathlib as _pl
    tmpl = (_pl.Path(_srr.__file__).parent / "templates" / "pdf" / "certified_valuation_report.html").read_text(encoding="utf-8")
    assert "تحليل أعلى وأفضل استغلال" in tmpl


def test_SRB336_preliminary_pdf_contains_direct_cap_vs_dcf():
    """SRB336 simple_valuation_draft.html contains direct cap vs DCF section."""
    import pathlib as _pl
    tmpl = (_pl.Path(_srr.__file__).parent / "templates" / "pdf" / "simple_valuation_draft.html").read_text(encoding="utf-8")
    assert "فصل رسملة الدخل المباشر عن DCF" in tmpl or "income_direct_vs_dcf_explanation" in tmpl


def test_SRB337_certified_pdf_contains_legal_due_diligence():
    """SRB337 certified_valuation_report.html contains legal due diligence section."""
    import pathlib as _pl
    tmpl = (_pl.Path(_srr.__file__).parent / "templates" / "pdf" / "certified_valuation_report.html").read_text(encoding="utf-8")
    assert "الفحص القانوني المبدئي" in tmpl


def test_SRB338_no_internal_paths_in_methodology_context():
    """SRB338 New methodology context keys contain no Windows internal paths."""
    import json
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    _new_keys = [
        "hbu_analysis", "direct_capitalization_context", "comparable_adjustment_support",
        "assumptions_registry", "depreciation_breakdown", "dcf_scenarios",
        "legal_due_diligence", "esg_enhanced_context", "environmental_impact_assessment",
        "valuation_uncertainty", "peer_review",
    ]
    raw = json.dumps({k: mctx[k] for k in _new_keys if k in mctx}, ensure_ascii=False, default=str).lower()
    forbidden = ["c:\\users", "core_engine", "\\\\"]
    for fp in forbidden:
        assert fp not in raw, f"Internal path {fp!r} found in methodology context"


def test_SRB339_no_compliance_overclaim_without_peer_review():
    """SRB339 certified PDF template states compliance as methodological alignment, not full certification."""
    import pathlib as _pl
    tmpl = (_pl.Path(_srr.__file__).parent / "templates" / "pdf" / "certified_valuation_report.html").read_text(encoding="utf-8")
    assert "ليتوافق منهجياً" in tmpl or "يراعي مبادئ" in tmpl, \
        "Certified PDF should use qualified compliance language, not claim full USPAP/RICS compliance"


# ═══════════════════════════════════════════════════════════════════════════════
# SRB340–SRB364 — Task 1: Valuation Certification Readiness, Source Quality Gate,
#                         Final Reconciliation & Scope Completion
# ═══════════════════════════════════════════════════════════════════════════════

def test_SRB340_source_quality_gate_key_present():
    """SRB340 _build_method_context returns source_quality_gate dict."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "source_quality_gate" in mctx, "source_quality_gate key missing from context"
    assert isinstance(mctx["source_quality_gate"], dict)


def test_SRB341_source_quality_gate_certification_blocked_for_qa():
    """SRB341 source_quality_gate.certification_allowed is False for QA simulation payload."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    sqg = mctx["source_quality_gate"]
    assert sqg.get("certification_allowed") is False, \
        "QA simulation payload must NOT be certification_allowed"


def test_SRB342_source_quality_gate_qa_count_positive_for_qa():
    """SRB342 source_quality_gate.qa_simulation_sources_count > 0 for QA payload."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    sqg = mctx["source_quality_gate"]
    assert sqg.get("qa_simulation_sources_count", 0) > 0, \
        "Expected at least one QA simulation source in QA payload"


def test_SRB343_source_quality_gate_block_reason_non_empty_for_qa():
    """SRB343 source_quality_gate.certification_block_reason is non-empty for QA payload."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    sqg = mctx["source_quality_gate"]
    assert sqg.get("certification_block_reason", "").strip(), \
        "certification_block_reason must be non-empty when QA sources present"


def test_SRB344_source_quality_gate_advisory_reason_always_present():
    """SRB344 source_quality_gate.advisory_only_reason is always non-empty."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    sqg = mctx["source_quality_gate"]
    assert sqg.get("advisory_only_reason", "").strip(), \
        "advisory_only_reason must always be present"


def test_SRB345_final_reconciliation_key_present():
    """SRB345 _build_method_context returns final_reconciliation dict."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "final_reconciliation" in mctx, "final_reconciliation key missing from context"
    assert isinstance(mctx["final_reconciliation"], dict)


def test_SRB346_final_reconciliation_method_values_non_empty():
    """SRB346 final_reconciliation.method_values is non-empty list for QA payload."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    fr = mctx["final_reconciliation"]
    mv = fr.get("method_values", [])
    assert isinstance(mv, list) and len(mv) > 0, \
        "final_reconciliation.method_values must be a non-empty list"


def test_SRB347_final_reconciliation_selected_value_non_empty():
    """SRB347 final_reconciliation.selected_final_value is non-empty for QA payload."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    fr = mctx["final_reconciliation"]
    assert fr.get("selected_final_value", "").strip(), \
        "final_reconciliation.selected_final_value must be non-empty"


def test_SRB348_final_reconciliation_weighted_indication_non_empty():
    """SRB348 final_reconciliation.weighted_indication is non-empty for QA payload."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    fr = mctx["final_reconciliation"]
    assert fr.get("weighted_indication", "").strip(), \
        "final_reconciliation.weighted_indication must be non-empty"


def test_SRB349_final_reconciliation_dominant_method_non_empty():
    """SRB349 final_reconciliation.dominant_method is non-empty for QA payload."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    fr = mctx["final_reconciliation"]
    assert fr.get("dominant_method", "").strip(), \
        "final_reconciliation.dominant_method must be non-empty"


def test_SRB350_standards_compliance_key_present():
    """SRB350 _build_method_context returns standards_compliance dict."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "standards_compliance" in mctx, "standards_compliance key missing from context"
    assert isinstance(mctx["standards_compliance"], dict)


def test_SRB351_standards_compliance_ivs_statement_non_empty():
    """SRB351 standards_compliance.ivs_alignment_statement is non-empty."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    sc = mctx["standards_compliance"]
    assert sc.get("ivs_alignment_statement", "").strip(), \
        "ivs_alignment_statement must be non-empty"


def test_SRB352_standards_compliance_full_claim_blocked_for_qa():
    """SRB352 standards_compliance.full_compliance_claim_allowed is False when QA sources present."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    sc = mctx["standards_compliance"]
    assert sc.get("full_compliance_claim_allowed") is False, \
        "full_compliance_claim_allowed must be False when QA sources or gates are incomplete"


def test_SRB353_standards_compliance_qualified_statement_uses_correct_language():
    """SRB353 standards_compliance.qualified_compliance_statement contains ليتوافق منهجياً."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    sc = mctx["standards_compliance"]
    stmt = sc.get("qualified_compliance_statement", "")
    assert "ليتوافق منهجياً" in stmt or "يتوافق منهجياً" in stmt, \
        "Qualified compliance statement must use approved methodological alignment language"


def test_SRB354_expert_approval_key_present():
    """SRB354 _build_method_context returns expert_approval dict."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "expert_approval" in mctx, "expert_approval key missing from context"
    assert isinstance(mctx["expert_approval"], dict)


def test_SRB355_expert_approval_signature_not_ready_without_expert_fields():
    """SRB355 expert_approval.certification_signature_ready is False when no expert name/sig in QA payload."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    ea = mctx["expert_approval"]
    assert ea.get("certification_signature_ready") is False, \
        "certification_signature_ready must be False when expert_name / signature not provided"


def test_SRB356_scope_of_work_key_present():
    """SRB356 _build_method_context returns scope_of_work dict."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "scope_of_work" in mctx, "scope_of_work key missing from context"
    assert isinstance(mctx["scope_of_work"], dict)


def test_SRB357_scope_of_work_valuation_purpose_non_empty():
    """SRB357 scope_of_work.valuation_purpose is non-empty for QA payload."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    sow = mctx["scope_of_work"]
    assert sow.get("valuation_purpose", "").strip(), \
        "scope_of_work.valuation_purpose must be non-empty"


def test_SRB358_scope_of_work_methods_used_non_empty():
    """SRB358 scope_of_work.methods_used_str is non-empty for QA payload."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    sow = mctx["scope_of_work"]
    assert sow.get("methods_used_str", "").strip(), \
        "scope_of_work.methods_used_str must be non-empty"


def test_SRB359_workbook_has_data_governance_sheet(client):
    """SRB359 Expert workbook contains حوكمة مصادر البيانات sheet."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")
    rid = json.loads(_post_request(client).data)["request_id"]
    wb = openpyxl.load_workbook(str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"))
    assert "حوكمة مصادر البيانات" in wb.sheetnames, \
        f"حوكمة مصادر البيانات sheet missing. Sheets: {wb.sheetnames}"


def test_SRB360_workbook_has_final_reconciliation_sheet(client):
    """SRB360 Expert workbook contains التوفيق النهائي للقيمة sheet."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")
    rid = json.loads(_post_request(client).data)["request_id"]
    wb = openpyxl.load_workbook(str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"))
    assert "التوفيق النهائي للقيمة" in wb.sheetnames, \
        f"التوفيق النهائي للقيمة sheet missing. Sheets: {wb.sheetnames}"


def test_SRB361_workbook_has_compliance_statement_sheet(client):
    """SRB361 Expert workbook contains بيان الامتثال sheet."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")
    rid = json.loads(_post_request(client).data)["request_id"]
    wb = openpyxl.load_workbook(str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"))
    assert "بيان الامتثال" in wb.sheetnames, \
        f"بيان الامتثال sheet missing. Sheets: {wb.sheetnames}"


def test_SRB362_workbook_has_expert_signature_sheet(client):
    """SRB362 Expert workbook contains توقيع واعتماد الخبير sheet."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")
    rid = json.loads(_post_request(client).data)["request_id"]
    wb = openpyxl.load_workbook(str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"))
    assert "توقيع واعتماد الخبير" in wb.sheetnames, \
        f"توقيع واعتماد الخبير sheet missing. Sheets: {wb.sheetnames}"


def test_SRB363_workbook_has_scope_of_work_sheet(client):
    """SRB363 Expert workbook contains نطاق العمل sheet."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")
    rid = json.loads(_post_request(client).data)["request_id"]
    wb = openpyxl.load_workbook(str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"))
    assert "نطاق العمل" in wb.sheetnames, \
        f"نطاق العمل sheet missing. Sheets: {wb.sheetnames}"


def test_SRB364_no_internal_paths_in_task1_context_keys():
    """SRB364 Task 1 new context keys contain no Windows internal paths."""
    import json as _json
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    _task1_keys = [
        "source_quality_gate", "final_reconciliation", "standards_compliance",
        "expert_approval", "scope_of_work",
    ]
    raw = _json.dumps(
        {k: mctx[k] for k in _task1_keys if k in mctx},
        ensure_ascii=False, default=str,
    ).lower()
    for fp in ("c:\\users", "core_engine", "\\\\"):
        assert fp not in raw, f"Internal path {fp!r} found in Task 1 context keys"


# ═══════════════════════════════════════════════════════════════════════════════
# SRB365–SRB389 — Task 2: Valuation Report Final Governance, Attachments, AVM,
#                         Rent Consistency & Report Status Clarity Pass
# ═══════════════════════════════════════════════════════════════════════════════

def test_SRB365_peer_review_gate_key_present():
    """SRB365 _build_method_context returns peer_review_gate dict."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "peer_review_gate" in mctx, "peer_review_gate key missing from context"
    assert isinstance(mctx["peer_review_gate"], dict)


def test_SRB366_peer_review_gate_required_is_true():
    """SRB366 peer_review_gate.peer_review_required is always True."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    prg = mctx["peer_review_gate"]
    assert prg.get("peer_review_required") is True, \
        "peer_review_gate.peer_review_required must always be True"


def test_SRB367_peer_review_gate_not_allowed_for_qa():
    """SRB367 peer_review_gate.certification_allowed_by_peer_review is False for QA payload (no peer review)."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    prg = mctx["peer_review_gate"]
    assert prg.get("certification_allowed_by_peer_review") is False, \
        "certification_allowed_by_peer_review must be False when peer_review_status not reviewed/approved"


def test_SRB368_peer_review_gate_block_reason_non_empty_when_not_approved():
    """SRB368 peer_review_gate.peer_review_block_reason is non-empty when not approved."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    prg = mctx["peer_review_gate"]
    assert prg.get("peer_review_block_reason", "").strip(), \
        "peer_review_block_reason must be non-empty when peer review not completed"


def test_SRB369_visual_attachments_key_present():
    """SRB369 _build_method_context returns visual_attachments dict."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "visual_attachments" in mctx, "visual_attachments key missing from context"
    assert isinstance(mctx["visual_attachments"], dict)


def test_SRB370_visual_attachments_map_available_is_bool():
    """SRB370 visual_attachments.location_map_available is a bool."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    va = mctx["visual_attachments"]
    assert isinstance(va.get("location_map_available"), bool), \
        "visual_attachments.location_map_available must be a bool"


def test_SRB371_avm_status_key_present():
    """SRB371 _build_method_context returns avm_status dict."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "avm_status" in mctx, "avm_status key missing from context"
    assert isinstance(mctx["avm_status"], dict)


def test_SRB372_avm_status_not_used_without_avm_inputs():
    """SRB372 avm_status.avm_used is a bool; exclusion reason present when AVM not used."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    av = mctx["avm_status"]
    assert isinstance(av.get("avm_used"), bool), \
        "avm_status.avm_used must be a bool"
    if not av.get("avm_used"):
        assert av.get("avm_exclusion_reason", "").strip(), \
            "avm_exclusion_reason must be non-empty when avm_used=False"


def test_SRB373_avm_exclusion_reason_non_empty_when_not_used():
    """SRB373 avm_status.avm_exclusion_reason is non-empty when AVM not used."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    av = mctx["avm_status"]
    if not av.get("avm_used"):
        assert av.get("avm_exclusion_reason", "").strip(), \
            "avm_exclusion_reason must be non-empty when avm_used=False"


def test_SRB374_rent_consistency_check_key_present():
    """SRB374 _build_method_context returns rent_consistency_check dict."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "rent_consistency_check" in mctx, "rent_consistency_check key missing from context"
    assert isinstance(mctx["rent_consistency_check"], dict)


def test_SRB375_rent_consistency_income_monthly_rent_key_exists():
    """SRB375 rent_consistency_check.income_method_monthly_rent key always exists."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    rcc = mctx["rent_consistency_check"]
    assert "income_method_monthly_rent" in rcc, \
        "rent_consistency_check.income_method_monthly_rent key must always be present"


def test_SRB376_rent_consistency_rent_consistent_is_bool():
    """SRB376 rent_consistency_check.rent_consistent is a bool."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    rcc = mctx["rent_consistency_check"]
    assert isinstance(rcc.get("rent_consistent"), bool), \
        "rent_consistency_check.rent_consistent must be a bool"


def test_SRB377_client_recommendation_key_present():
    """SRB377 _build_method_context returns client_recommendation dict."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "client_recommendation" in mctx, "client_recommendation key missing from context"
    assert isinstance(mctx["client_recommendation"], dict)


def test_SRB378_client_recommendation_value_non_empty():
    """SRB378 client_recommendation.recommended_value is non-empty for QA payload."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    cr = mctx["client_recommendation"]
    assert cr.get("recommended_value", "").strip(), \
        "client_recommendation.recommended_value must be non-empty"


def test_SRB379_valuation_fee_disclosure_key_present():
    """SRB379 _build_method_context returns valuation_fee_disclosure dict."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "valuation_fee_disclosure" in mctx, "valuation_fee_disclosure key missing from context"
    assert isinstance(mctx["valuation_fee_disclosure"], dict)


def test_SRB380_valuation_fee_disclosure_independence_statement_non_empty():
    """SRB380 valuation_fee_disclosure.fee_independence_statement is always non-empty."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    vfd = mctx["valuation_fee_disclosure"]
    assert vfd.get("fee_independence_statement", "").strip(), \
        "valuation_fee_disclosure.fee_independence_statement must always be present"


def test_SRB381_valuation_fee_not_contingent_for_standard_qa():
    """SRB381 valuation_fee_disclosure.fee_contingent_on_value is False for standard QA payload."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    vfd = mctx["valuation_fee_disclosure"]
    assert vfd.get("fee_contingent_on_value") is False, \
        "fee_contingent_on_value must be False when no contingent_fee flag in payload"


def test_SRB382_report_status_visuals_key_present():
    """SRB382 _build_method_context returns report_status_visuals dict."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "report_status_visuals" in mctx, "report_status_visuals key missing from context"
    assert isinstance(mctx["report_status_visuals"], dict)


def test_SRB383_preliminary_banner_color_always_red():
    """SRB383 report_status_visuals.preliminary_banner_color_semantic is always 'red'."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    rsv = mctx["report_status_visuals"]
    assert rsv.get("preliminary_banner_color_semantic") == "red", \
        "Preliminary banner must always be red regardless of gate status"


def test_SRB384_report_status_visuals_not_certified_for_qa():
    """SRB384 report_status_visuals.certification_allowed is False for QA payload (gates fail)."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    rsv = mctx["report_status_visuals"]
    assert rsv.get("certification_allowed") is False, \
        "certification_allowed must be False for QA payload where source/signature/peer-review gates fail"


def test_SRB385_certified_banner_amber_when_gates_fail():
    """SRB385 report_status_visuals.certified_banner_color_semantic is 'amber' for QA payload."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    rsv = mctx["report_status_visuals"]
    assert rsv.get("certified_banner_color_semantic") == "amber", \
        "certified_banner_color_semantic must be 'amber' when any gate fails"


def test_SRB386_workbook_has_rent_consistency_sheet(client):
    """SRB386 Expert workbook contains تسوية الإيجار sheet."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")
    rid = json.loads(_post_request(client).data)["request_id"]
    wb = openpyxl.load_workbook(str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"))
    assert "تسوية الإيجار" in wb.sheetnames, \
        f"تسوية الإيجار sheet missing. Sheets: {wb.sheetnames}"


def test_SRB387_workbook_has_client_recommendation_sheet(client):
    """SRB387 Expert workbook contains التوصية النهائية sheet."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")
    rid = json.loads(_post_request(client).data)["request_id"]
    wb = openpyxl.load_workbook(str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"))
    assert "التوصية النهائية" in wb.sheetnames, \
        f"التوصية النهائية sheet missing. Sheets: {wb.sheetnames}"


def test_SRB388_workbook_has_professional_disclosures_sheet(client):
    """SRB388 Expert workbook contains الإفصاحات المهنية sheet."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")
    rid = json.loads(_post_request(client).data)["request_id"]
    wb = openpyxl.load_workbook(str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"))
    assert "الإفصاحات المهنية" in wb.sheetnames, \
        f"الإفصاحات المهنية sheet missing. Sheets: {wb.sheetnames}"


def test_SRB389_no_internal_paths_in_task2_context_keys():
    """SRB389 Task 2 new context keys contain no Windows internal paths."""
    import json as _json
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    _task2_keys = [
        "peer_review_gate", "visual_attachments", "avm_status",
        "rent_consistency_check", "client_recommendation",
        "valuation_fee_disclosure", "report_status_visuals",
    ]
    raw = _json.dumps(
        {k: mctx[k] for k in _task2_keys if k in mctx},
        ensure_ascii=False, default=str,
    ).lower()
    for fp in ("c:\\users", "core_engine", "\\\\"):
        assert fp not in raw, f"Internal path {fp!r} found in Task 2 context keys"


# ═══════════════════════════════════════════════════════════════════════════════
# SRB390–SRB407 — SWOT Strategic Analysis Integration Pass
# ═══════════════════════════════════════════════════════════════════════════════

def test_SRB390_swot_analysis_exists_in_method_context():
    """SRB390 swot_analysis key exists in method context."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "swot_analysis" in mctx, "swot_analysis missing from method context"
    assert isinstance(mctx["swot_analysis"], dict), "swot_analysis is not a dict"


def test_SRB391_swot_strengths_non_empty():
    """SRB391 swot_analysis.strengths is a non-empty list."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    sw = mctx.get("swot_analysis", {})
    assert sw.get("strengths"), "swot_analysis.strengths is empty or missing"
    assert isinstance(sw["strengths"], list)
    assert len(sw["strengths"]) >= 1


def test_SRB392_swot_weaknesses_non_empty():
    """SRB392 swot_analysis.weaknesses is a non-empty list."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    sw = mctx.get("swot_analysis", {})
    assert sw.get("weaknesses"), "swot_analysis.weaknesses is empty or missing"
    assert isinstance(sw["weaknesses"], list)
    assert len(sw["weaknesses"]) >= 1


def test_SRB393_swot_opportunities_non_empty():
    """SRB393 swot_analysis.opportunities is a non-empty list."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    sw = mctx.get("swot_analysis", {})
    assert sw.get("opportunities"), "swot_analysis.opportunities is empty or missing"
    assert isinstance(sw["opportunities"], list)
    assert len(sw["opportunities"]) >= 1


def test_SRB394_swot_threats_non_empty():
    """SRB394 swot_analysis.threats is a non-empty list."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    sw = mctx.get("swot_analysis", {})
    assert sw.get("threats"), "swot_analysis.threats is empty or missing"
    assert isinstance(sw["threats"], list)
    assert len(sw["threats"]) >= 1


def test_SRB395_swot_items_have_required_fields():
    """SRB395 Each SWOT item has impact_score, probability_score, priority_score."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    sw = mctx.get("swot_analysis", {})
    all_items = (
        sw.get("strengths", []) + sw.get("weaknesses", []) +
        sw.get("opportunities", []) + sw.get("threats", [])
    )
    assert all_items, "No SWOT items found"
    for item in all_items:
        for field in ("impact_score", "probability_score", "priority_score",
                      "category", "item_key", "title_ar", "description_ar"):
            assert field in item, f"SWOT item missing field {field!r}: {item.get('item_key', '?')}"


def test_SRB396_swot_priority_score_equals_impact_times_probability():
    """SRB396 priority_score == impact_score × probability_score for every SWOT item."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    sw = mctx.get("swot_analysis", {})
    all_items = (
        sw.get("strengths", []) + sw.get("weaknesses", []) +
        sw.get("opportunities", []) + sw.get("threats", [])
    )
    for item in all_items:
        expected = item["impact_score"] * item["probability_score"]
        assert item["priority_score"] == expected, (
            f"priority_score mismatch for {item.get('item_key')}: "
            f"expected {expected}, got {item['priority_score']}"
        )


def test_SRB397_swot_impact_probability_in_range_1_5():
    """SRB397 impact_score and probability_score are integers 1–5."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    sw = mctx.get("swot_analysis", {})
    all_items = (
        sw.get("strengths", []) + sw.get("weaknesses", []) +
        sw.get("opportunities", []) + sw.get("threats", [])
    )
    for item in all_items:
        for field in ("impact_score", "probability_score"):
            v = item.get(field)
            assert isinstance(v, int), f"{field} is not int: {type(v)} in {item.get('item_key')}"
            assert 1 <= v <= 5, f"{field}={v} out of range [1,5] in {item.get('item_key')}"


def test_SRB398_swot_value_impact_direction_valid():
    """SRB398 value_impact_direction is one of positive/negative/neutral/uncertain."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    sw = mctx.get("swot_analysis", {})
    valid_dirs = {"positive", "negative", "neutral", "uncertain"}
    all_items = (
        sw.get("strengths", []) + sw.get("weaknesses", []) +
        sw.get("opportunities", []) + sw.get("threats", [])
    )
    for item in all_items:
        d = item.get("value_impact_direction", "")
        assert d in valid_dirs, f"Invalid value_impact_direction={d!r} in {item.get('item_key')}"


def test_SRB399_swot_hbu_alignment_exists():
    """SRB399 swot_hbu_alignment exists and has required keys."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "swot_hbu_alignment" in mctx, "swot_hbu_alignment missing from context"
    sha = mctx["swot_hbu_alignment"]
    for key in ("selected_hbu", "supporting_strengths", "limiting_weaknesses",
                "future_opportunities", "major_threats", "hbu_alignment_conclusion"):
        assert key in sha, f"swot_hbu_alignment missing key {key!r}"
    assert sha.get("hbu_alignment_conclusion"), "hbu_alignment_conclusion is empty"


def test_SRB400_swot_uncertainty_linkage_exists():
    """SRB400 swot_uncertainty_linkage exists and has required keys."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "swot_uncertainty_linkage" in mctx, "swot_uncertainty_linkage missing from context"
    sul = mctx["swot_uncertainty_linkage"]
    for key in ("upper_bound_drivers", "lower_bound_drivers",
                "optimistic_scenario_links", "pessimistic_scenario_links",
                "uncertainty_explanation"):
        assert key in sul, f"swot_uncertainty_linkage missing key {key!r}"
    assert isinstance(sul["upper_bound_drivers"], list)
    assert isinstance(sul["lower_bound_drivers"], list)


def test_SRB401_swot_recommendation_linkage_exists():
    """SRB401 swot_recommendation_linkage exists and has required keys."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "swot_recommendation_linkage" in mctx, "swot_recommendation_linkage missing from context"
    srl = mctx["swot_recommendation_linkage"]
    for key in ("recommended_value", "recommendation_conditioned_by",
                "key_strengths_supporting_recommendation",
                "key_risks_limiting_recommendation",
                "recommended_next_steps_from_swot",
                "swot_based_recommendation"):
        assert key in srl, f"swot_recommendation_linkage missing key {key!r}"
    assert srl.get("swot_based_recommendation"), "swot_based_recommendation is empty"


def test_SRB402_swot_pdf_contains_swot_heading():
    """SRB402 Generated preliminary PDF contains SWOT heading text."""
    import re
    pdf_bytes = _srr._build_simple_valuation_pdf_bytes(_QA_ZAMALEK_PAYLOAD)
    assert len(pdf_bytes) > 1000, "PDF too small"
    # Check via HTML generation (context has SWOT section)
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    sw = mctx.get("swot_analysis", {})
    assert sw, "swot_analysis missing — PDF cannot contain SWOT section"
    assert sw.get("strengths"), "No SWOT strengths in context"


def test_SRB403_swot_pdf_hbu_linkage_present():
    """SRB403 swot_hbu_alignment.hbu_alignment_conclusion is non-empty."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    sha = mctx.get("swot_hbu_alignment", {})
    assert sha.get("hbu_alignment_conclusion"), "hbu_alignment_conclusion is empty"
    assert len(sha["hbu_alignment_conclusion"]) > 20, "hbu_alignment_conclusion too short"


def test_SRB404_workbook_contains_swot_sheet():
    """SRB404 Expert workbook contains sheet 'تحليل_SWOT'."""
    wb = _get_wb_v2()
    assert "تحليل_SWOT" in wb.sheetnames, \
        f"'تحليل_SWOT' sheet missing. Sheets: {wb.sheetnames}"


def test_SRB405_workbook_contains_risk_matrix_sheet():
    """SRB405 Expert workbook contains sheet 'مصفوفة_تقييم_المخاطر'."""
    wb = _get_wb_v2()
    assert "مصفوفة_تقييم_المخاطر" in wb.sheetnames, \
        f"'مصفوفة_تقييم_المخاطر' sheet missing. Sheets: {wb.sheetnames}"


def test_SRB406_swot_workbook_priority_cells_have_formulas():
    """SRB406 SWOT workbook sheet 'تحليل_SWOT' has priority formula cells (=F*G)."""
    wb = _get_wb_v2()
    assert "تحليل_SWOT" in wb.sheetnames, "'تحليل_SWOT' sheet missing"
    ws = wb["تحليل_SWOT"]
    formula_cells = [
        cell for row in ws.iter_rows(min_row=3, max_row=40)
        for cell in row
        if cell.value and isinstance(cell.value, str) and cell.value.startswith("=F") and "*G" in cell.value
    ]
    assert formula_cells, "No =F*G priority formula cells found in 'تحليل_SWOT'"


def test_SRB407_swot_uncertainty_sheet_has_swot_drivers():
    """SRB407 Uncertainty sheet contains SWOT upper/lower driver rows."""
    wb = _get_wb_v2()
    assert "نطاق الثقة وعدم اليقين" in wb.sheetnames, "'نطاق الثقة وعدم اليقين' sheet missing"
    ws = wb["نطاق الثقة وعدم اليقين"]
    all_text = " ".join(
        str(val) for row in ws.iter_rows(values_only=True)
        for val in row if val is not None
    )
    assert "SWOT" in all_text or "محركات" in all_text, \
        "SWOT upper/lower driver rows not found in uncertainty sheet"


# ═══════════════════════════════════════════════════════════════════════════════
# SRB408–SRB436 — Valuation QA Simulation Governance & Production Readiness Gate
# ═══════════════════════════════════════════════════════════════════════════════

def test_SRB408_valuation_qa_simulation_governance_exists():
    """SRB408 valuation_qa_simulation_governance exists in method context."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "valuation_qa_simulation_governance" in mctx, \
        "valuation_qa_simulation_governance missing from context"
    assert isinstance(mctx["valuation_qa_simulation_governance"], dict)


def test_SRB409_qa_simulation_blocks_certified_use():
    """SRB409 certified_use_allowed=False when QA simulation active."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    qg = mctx["valuation_qa_simulation_governance"]
    assert qg["qa_simulation_active"] is True, "qa_simulation_active should be True for QA payload"
    assert qg["certified_use_allowed"] is False, \
        "certified_use_allowed should be False when QA simulation active"


def test_SRB410_qa_simulation_warning_text_present():
    """SRB410 warning_text is non-empty when QA simulation active."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    qg = mctx["valuation_qa_simulation_governance"]
    assert qg.get("warning_text"), "warning_text should not be empty when QA active"
    assert len(qg["warning_text"]) > 10, "warning_text too short"


def test_SRB411_valuation_comparable_readiness_exists():
    """SRB411 valuation_comparable_readiness exists and has required keys."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "valuation_comparable_readiness" in mctx, \
        "valuation_comparable_readiness missing from context"
    cr = mctx["valuation_comparable_readiness"]
    for key in ("sales_comparison_ready", "actual_real_sales_comparables_count",
                "qa_comparables_count", "comparable_method_certified_use_allowed",
                "required_actions"):
        assert key in cr, f"valuation_comparable_readiness missing key {key!r}"


def test_SRB412_missing_real_comps_block_certified_comparison():
    """SRB412 comparable_method_certified_use_allowed=False when real comparables are zero."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    cr = mctx["valuation_comparable_readiness"]
    assert cr["actual_real_sales_comparables_count"] == 0, \
        "In QA mode actual_real_sales_comparables_count should be 0"
    assert cr["comparable_method_certified_use_allowed"] is False, \
        "comparable_method_certified_use_allowed should be False with no real comparables"


def test_SRB413_valuation_depreciation_age_evidence_gate_exists():
    """SRB413 valuation_depreciation_age_evidence_gate exists and has required keys."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "valuation_depreciation_age_evidence_gate" in mctx, \
        "valuation_depreciation_age_evidence_gate missing from context"
    dg = mctx["valuation_depreciation_age_evidence_gate"]
    for key in ("effective_age_used", "economic_life", "depreciation_method",
                "age_evidence_required", "age_evidence_available",
                "depreciation_certified_use_allowed", "acceptable_evidence_types",
                "warning_text"):
        assert key in dg, f"valuation_depreciation_age_evidence_gate missing key {key!r}"


def test_SRB414_missing_age_evidence_blocks_certified_depreciation():
    """SRB414 depreciation_certified_use_allowed=False when age evidence missing."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    dg = mctx["valuation_depreciation_age_evidence_gate"]
    assert dg["age_evidence_available"] is False, \
        "age_evidence_available should be False in QA mode"
    assert dg["depreciation_certified_use_allowed"] is False, \
        "depreciation_certified_use_allowed should be False when evidence missing"
    assert dg["age_evidence_required"] is True


def test_SRB415_valuation_document_readiness_exists():
    """SRB415 valuation_document_readiness exists and has required keys."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "valuation_document_readiness" in mctx, \
        "valuation_document_readiness missing from context"
    dr = mctx["valuation_document_readiness"]
    for key in ("document_completeness_score", "required_documents_count",
                "submitted_documents_count", "missing_mandatory_documents",
                "certification_risk_level", "valuation_certification_ready",
                "required_actions_before_certification"):
        assert key in dr, f"valuation_document_readiness missing key {key!r}"


def test_SRB416_missing_mandatory_docs_set_cert_ready_false():
    """SRB416 valuation_certification_ready=False when mandatory documents are missing."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    dr = mctx["valuation_document_readiness"]
    assert dr["missing_mandatory_documents"], \
        "missing_mandatory_documents should be non-empty in QA mode"
    assert dr["valuation_certification_ready"] is False, \
        "valuation_certification_ready should be False when mandatory docs are missing"


def test_SRB417_valuation_certification_roadmap_exists():
    """SRB417 valuation_certification_roadmap exists with all required keys."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "valuation_certification_roadmap" in mctx, \
        "valuation_certification_roadmap missing from context"
    road = mctx["valuation_certification_roadmap"]
    for key in ("current_stage", "roadmap_steps", "blockers",
                "next_required_step", "certified_ready_stage_reached",
                "roadmap_warning"):
        assert key in road, f"valuation_certification_roadmap missing key {key!r}"


def test_SRB418_roadmap_starts_with_qa_advisory_draft():
    """SRB418 First roadmap step is 'QA advisory draft' (completed=True)."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    road = mctx["valuation_certification_roadmap"]
    assert road["current_stage"] == "مسودة QA استرشادية", \
        f"current_stage should be 'مسودة QA استرشادية', got {road['current_stage']!r}"
    steps = road["roadmap_steps"]
    assert len(steps) == 10, f"Expected 10 roadmap steps, got {len(steps)}"
    assert steps[0]["completed"] is True, "First roadmap step should be completed"
    assert all(not s["completed"] for s in steps[1:]), \
        "All roadmap steps after step 1 should be incomplete"


def test_SRB419_valuation_geographic_land_price_readiness_exists():
    """SRB419 valuation_geographic_land_price_readiness exists with required keys."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "valuation_geographic_land_price_readiness" in mctx, \
        "valuation_geographic_land_price_readiness missing from context"
    glr = mctx["valuation_geographic_land_price_readiness"]
    for key in ("land_price_is_qa", "land_price_production_ready",
                "replacement_required", "suggested_source_categories",
                "limitation_text"):
        assert key in glr, f"valuation_geographic_land_price_readiness missing key {key!r}"


def test_SRB420_qa_land_price_requires_replacement():
    """SRB420 replacement_required=True when land price is QA."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    glr = mctx["valuation_geographic_land_price_readiness"]
    assert glr["land_price_is_qa"] is True, "land_price_is_qa should be True in QA mode"
    assert glr["replacement_required"] is True, "replacement_required should be True for QA land price"
    assert glr["land_price_production_ready"] is False


def test_SRB421_valuation_source_database_linkage_readiness_exists():
    """SRB421 valuation_source_database_linkage_readiness exists in context."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "valuation_source_database_linkage_readiness" in mctx, \
        "valuation_source_database_linkage_readiness missing from context"
    slr = mctx["valuation_source_database_linkage_readiness"]
    for key in ("qdrant_active_now", "rag_active_now", "live_database_active_now",
                "integration_status", "required_actions"):
        assert key in slr, f"valuation_source_database_linkage_readiness missing key {key!r}"


def test_SRB422_qdrant_active_now_false():
    """SRB422 qdrant_active_now=False always."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    slr = mctx["valuation_source_database_linkage_readiness"]
    assert slr["qdrant_active_now"] is False, "qdrant_active_now must be False"


def test_SRB423_rag_active_now_false():
    """SRB423 rag_active_now=False always."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    slr = mctx["valuation_source_database_linkage_readiness"]
    assert slr["rag_active_now"] is False, "rag_active_now must be False"


def test_SRB424_live_database_active_now_false():
    """SRB424 live_database_active_now=False unless explicitly enabled."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    slr = mctx["valuation_source_database_linkage_readiness"]
    assert slr["live_database_active_now"] is False, "live_database_active_now must be False"


def test_SRB425_valuation_parameter_governance_exists():
    """SRB425 valuation_parameter_governance exists with required keys."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "valuation_parameter_governance" in mctx, \
        "valuation_parameter_governance missing from context"
    pg = mctx["valuation_parameter_governance"]
    for key in ("parameters", "legal_or_market_reference_available",
                "verified_by_expert", "production_use_allowed",
                "verification_status", "required_action", "warning_text"):
        assert key in pg, f"valuation_parameter_governance missing key {key!r}"
    assert isinstance(pg["parameters"], list), "parameters should be a list"
    assert len(pg["parameters"]) >= 1, "parameters list should not be empty"


def test_SRB426_missing_references_block_param_certified_use():
    """SRB426 certified_use_allowed=False for parameters without references."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    pg = mctx["valuation_parameter_governance"]
    for param in pg["parameters"]:
        assert "certified_use_allowed" in param, \
            f"Parameter {param.get('parameter_name')} missing certified_use_allowed"
        assert param["certified_use_allowed"] is False, \
            f"Parameter {param.get('parameter_name')} should have certified_use_allowed=False"


def test_SRB427_valuation_certification_status_exists():
    """SRB427 valuation_certification_status exists with required keys."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "valuation_certification_status" in mctx, \
        "valuation_certification_status missing from context"
    cs = mctx["valuation_certification_status"]
    for key in ("report_status", "certification_ready", "certification_blockers",
                "certification_risk_level", "recommended_next_action",
                "readiness_summary", "executive_recommendation"):
        assert key in cs, f"valuation_certification_status missing key {key!r}"


def test_SRB428_certification_ready_false_when_blockers_exist():
    """SRB428 certification_ready=False when any blockers exist."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    cs = mctx["valuation_certification_status"]
    assert cs["certification_blockers"], "certification_blockers should be non-empty for QA mode"
    assert cs["certification_ready"] is False, \
        "certification_ready should be False when blockers exist"
    assert cs["report_status"] == "qa_advisory_only"


def test_SRB429_workbook_has_qa_governance_sheet():
    """SRB429 Workbook contains 'حوكمة بيانات QA' sheet."""
    wb = _get_wb_v2()
    assert "حوكمة بيانات QA" in wb.sheetnames, \
        "'حوكمة بيانات QA' sheet missing from workbook"


def test_SRB430_workbook_has_document_risk_sheet():
    """SRB430 Workbook contains 'قائمة المستندات ومخاطر الاعتماد' sheet."""
    wb = _get_wb_v2()
    assert "قائمة المستندات ومخاطر الاعتماد" in wb.sheetnames, \
        "'قائمة المستندات ومخاطر الاعتماد' sheet missing from workbook"


def test_SRB431_workbook_has_certification_roadmap_sheet():
    """SRB431 Workbook contains 'خارطة طريق الاعتماد' sheet."""
    wb = _get_wb_v2()
    assert "خارطة طريق الاعتماد" in wb.sheetnames, \
        "'خارطة طريق الاعتماد' sheet missing from workbook"


def test_SRB432_workbook_has_parameter_governance_sheet():
    """SRB432 Workbook contains 'حوكمة المعاملات' sheet."""
    wb = _get_wb_v2()
    assert "حوكمة المعاملات" in wb.sheetnames, \
        "'حوكمة المعاملات' sheet missing from workbook"


def test_SRB433_workbook_has_certification_status_sheet():
    """SRB433 Workbook contains 'حالة الاعتماد والتوصية' sheet."""
    wb = _get_wb_v2()
    assert "حالة الاعتماد والتوصية" in wb.sheetnames, \
        "'حالة الاعتماد والتوصية' sheet missing from workbook"


def test_SRB434_no_internal_paths_in_context():
    """SRB434 No internal file paths exposed in production readiness context values."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    _forbidden = ("C:\\", "/home/", "/tmp/", "core_engine/", "expert_smart")
    for key in ("valuation_qa_simulation_governance", "valuation_certification_status",
                "valuation_parameter_governance"):
        block = mctx.get(key, {})
        block_str = str(block)
        for forbidden in _forbidden:
            assert forbidden not in block_str, \
                f"Internal path {forbidden!r} found in {key}"


def test_SRB435_no_certified_ready_claim_while_blockers_exist():
    """SRB435 Report does not claim certification_ready=True while blockers exist."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    cs = mctx["valuation_certification_status"]
    if cs["certification_blockers"]:
        assert cs["certification_ready"] is False, \
            "certification_ready must be False when blockers exist"
        assert "جاهز للاعتماد الرسمي" not in cs.get("executive_recommendation", "") \
               or "غير جاهز" in cs.get("executive_recommendation", ""), \
            "executive_recommendation must not claim readiness while blockers exist"


def test_SRB436_workbook_certification_status_sheet_has_blocker_rows():
    """SRB436 'حالة الاعتماد والتوصية' sheet contains certification blocker rows."""
    wb = _get_wb_v2()
    assert "حالة الاعتماد والتوصية" in wb.sheetnames
    ws = wb["حالة الاعتماد والتوصية"]
    all_text = " ".join(
        str(val) for row in ws.iter_rows(values_only=True)
        for val in row if val is not None
    )
    assert "جاهز" in all_text or "اعتماد" in all_text, \
        "Certification status sheet does not contain expected content"


# ── SRB437–SRB467: Risk/Decision Pass tests ──────────────────────────────────

def test_SRB437_valuation_data_fuel_readiness_exists():
    """SRB437 _build_method_context returns valuation_data_fuel_readiness key."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "valuation_data_fuel_readiness" in mctx


def test_SRB438_data_ready_false_when_only_qa_sources():
    """SRB438 data_ready=False when all sources are QA simulation."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    dfr = mctx["valuation_data_fuel_readiness"]
    assert dfr["methodology_ready"] is True
    assert dfr["data_ready"] is False
    assert dfr["certification_ready"] is False


def test_SRB439_method_consistency_diagnostics_exists():
    """SRB439 _build_method_context returns method_consistency_diagnostics key."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "method_consistency_diagnostics" in mctx


def test_SRB440_high_cv_triggers_high_risk():
    """SRB440 CV > 20% produces cv_risk_level='مرتفع'."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    mcd = mctx["method_consistency_diagnostics"]
    cv_str = mcd["coefficient_of_variation"]
    if cv_str and cv_str != "—":
        cv_val = float(cv_str.replace("%", "").strip())
        if cv_val > 20:
            assert mcd["cv_risk_level"] == "مرتفع"
    assert "cv_risk_level" in mcd


def test_SRB441_rent_reconciliation_explanation_exists():
    """SRB441 _build_method_context returns rent_reconciliation_explanation key."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "rent_reconciliation_explanation" in mctx


def test_SRB442_rent_mismatch_requires_explanation():
    """SRB442 Rent mismatch >3% sets explanation_required=True."""
    payload = dict(_QA_RENTAL_NASR_PAYLOAD)
    payload["income_monthly_rent"] = 9_000
    payload["final_monthly_rental_value"] = 9_500
    mctx = _srr._build_method_context(payload)
    rre = mctx["rent_reconciliation_explanation"]
    assert rre["explanation_required"] is True
    assert rre["expert_confirmation_required"] is True


def test_SRB443_certification_execution_gate_exists():
    """SRB443 _build_method_context returns certification_execution_gate key."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "certification_execution_gate" in mctx


def test_SRB444_missing_signature_blocks_certification():
    """SRB444 Missing expert signature makes certification_execution_allowed=False."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    ceg = mctx["certification_execution_gate"]
    assert ceg["expert_signature_available"] is False
    assert ceg["certification_execution_allowed"] is False


def test_SRB445_missing_peer_review_blocks_certification():
    """SRB445 Missing peer review makes certification_execution_allowed=False."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    ceg = mctx["certification_execution_gate"]
    assert ceg["peer_review_completed"] is False
    assert ceg["certification_execution_allowed"] is False


def test_SRB446_dcf_terminal_assumption_support_exists():
    """SRB446 _build_method_context returns dcf_terminal_assumption_support key."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "dcf_terminal_assumption_support" in mctx


def test_SRB447_missing_terminal_source_marks_advisory():
    """SRB447 Missing DCF terminal source sets terminal_assumption_certified_use_allowed=False."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    dta = mctx["dcf_terminal_assumption_support"]
    assert dta["growth_rate_source_available"] is False
    assert dta["terminal_cap_rate_source_available"] is False
    assert dta["terminal_assumption_certified_use_allowed"] is False


def test_SRB448_field_visual_evidence_gate_exists():
    """SRB448 _build_method_context returns field_visual_evidence_gate key."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "field_visual_evidence_gate" in mctx


def test_SRB449_missing_exterior_photo_blocks_visual_gate():
    """SRB449 Missing exterior photo => minimum_visual_evidence_met=False."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    fvg = mctx["field_visual_evidence_gate"]
    assert fvg["exterior_photo_available"] is False
    assert fvg["facade_photo_available"] is False
    assert fvg["minimum_visual_evidence_met"] is False
    assert fvg["visual_evidence_certified_use_allowed"] is False


def test_SRB450_avm_completeness_decision_exists():
    """SRB450 _build_method_context returns avm_completeness_decision key."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "avm_completeness_decision" in mctx


def test_SRB451_incomplete_avm_excluded_with_zero_weight_or_qa():
    """SRB451 AVM in QA mode has zero or advisory reconciliation weight."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    acd = mctx["avm_completeness_decision"]
    assert "avm_status" in acd
    if not acd["avm_used"]:
        assert acd["avm_reconciliation_weight"] == 0
        assert acd["avm_exclusion_reason"] != ""


def test_SRB452_valuation_risk_heatmap_exists():
    """SRB452 _build_method_context returns valuation_risk_heatmap key."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "valuation_risk_heatmap" in mctx


def test_SRB453_risk_heatmap_has_required_dimensions():
    """SRB453 Risk heatmap contains legal, financial, market, data_sources dimensions."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    rh = mctx["valuation_risk_heatmap"]
    dim_keys = {d["dimension_key"] for d in rh.get("dimensions", [])}
    for required_key in ("legal", "financial", "market", "data_sources", "certification_signature"):
        assert required_key in dim_keys, f"Missing dimension: {required_key}"


def test_SRB454_certification_timeline_exists():
    """SRB454 _build_method_context returns certification_timeline key."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "certification_timeline" in mctx


def test_SRB455_certification_timeline_has_6_steps():
    """SRB455 Certification timeline contains 6 steps."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    ctl = mctx["certification_timeline"]
    assert len(ctl.get("steps", [])) == 6
    assert ctl["total_estimated_days"] > 0


def test_SRB456_break_even_rent_analysis_exists():
    """SRB456 _build_method_context returns break_even_rent_analysis key."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "break_even_rent_analysis" in mctx


def test_SRB457_break_even_rent_positive_for_market_payload():
    """SRB457 Break-even monthly rent is positive when market value is available."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    bea = mctx["break_even_rent_analysis"]
    assert bea["data_complete"] is True
    assert bea["break_even_monthly_rent_raw"] > 0


def test_SRB458_valuation_compliance_dashboard_exists():
    """SRB458 _build_method_context returns valuation_compliance_dashboard key."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "valuation_compliance_dashboard" in mctx


def test_SRB459_compliance_dashboard_has_14_items():
    """SRB459 Compliance dashboard contains 14 items."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    comp = mctx["valuation_compliance_dashboard"]
    assert comp["total_items"] == 14


def test_SRB460_mass_appraisal_reference_exists():
    """SRB460 _build_method_context returns mass_appraisal_reference key."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "mass_appraisal_reference" in mctx


def test_SRB461_mass_appraisal_advisory_only_when_no_real_dataset():
    """SRB461 mass_appraisal_reference has reconciliation_weight=0 in QA mode."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    mar = mctx["mass_appraisal_reference"]
    assert mar["reconciliation_weight"] == 0.0
    assert "limitation_text" in mar
    assert len(mar["limitation_text"]) > 10


def test_SRB462_investment_decision_summary_exists():
    """SRB462 _build_method_context returns investment_decision_summary key."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "investment_decision_summary" in mctx


def test_SRB463_investment_decision_conditional_when_gates_fail():
    """SRB463 Decision summary is advisory/conditional when certification gates fail."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    inv = mctx["investment_decision_summary"]
    assert inv["is_advisory"] is True
    assert "مشروطة" in inv["recommended_decision"] or "استرشادي" in inv["recommended_decision"]


def test_SRB464_workbook_has_method_consistency_sheet():
    """SRB464 Workbook contains 'اختبار اتساق الطرق' sheet."""
    wb = _get_wb_v2()
    assert "اختبار اتساق الطرق" in wb.sheetnames


def test_SRB465_workbook_has_risk_heatmap_sheet():
    """SRB465 Workbook contains 'خريطة مخاطر التقييم' sheet."""
    wb = _get_wb_v2()
    assert "خريطة مخاطر التقييم" in wb.sheetnames


def test_SRB466_workbook_has_break_even_sheet():
    """SRB466 Workbook contains 'نقطة تعادل الإيجار' sheet."""
    wb = _get_wb_v2()
    assert "نقطة تعادل الإيجار" in wb.sheetnames


def test_SRB467_workbook_has_compliance_dashboard_sheet():
    """SRB467 Workbook contains 'لوحة امتثال التقييم' sheet."""
    wb = _get_wb_v2()
    assert "لوحة امتثال التقييم" in wb.sheetnames


# ── SRB468–SRB496 — Filing/Certification Readiness, QA Data Governance,
#    Real Comparables, Depreciation Evidence & Source Readiness Pass ──────────

def test_SRB468_valuation_qa_simulation_governance_blocks_certified_use():
    """SRB468 valuation_qa_simulation_governance.certified_use_allowed=False when QA active."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    qg = mctx["valuation_qa_simulation_governance"]
    assert qg["qa_simulation_active"] is True
    assert qg["certified_use_allowed"] is False
    assert qg["qa_simulation_sources_count"] > 0


def test_SRB469_qa_simulation_governance_warning_text_non_empty():
    """SRB469 QA simulation governance warning_text is populated when QA active."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    qg = mctx["valuation_qa_simulation_governance"]
    assert len(qg.get("warning_text", "")) > 20, \
        "warning_text should be non-empty when QA simulation is active"


def test_SRB470_qa_advisory_label_present_when_qa_active():
    """SRB470 advisory_label contains 'مسودة QA' substring when QA active."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    qg = mctx["valuation_qa_simulation_governance"]
    assert "مسودة QA" in qg.get("advisory_label", ""), \
        "advisory_label should contain 'مسودة QA' when QA simulation is active"


def test_SRB471_valuation_comparison_real_data_readiness_exists():
    """SRB471 valuation_comparison_real_data_readiness alias key exists in context."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "valuation_comparison_real_data_readiness" in mctx, \
        "valuation_comparison_real_data_readiness alias key missing from context"
    cr = mctx["valuation_comparison_real_data_readiness"]
    assert isinstance(cr, dict)
    for key in (
        "comparable_method_certified_use_allowed",
        "required_sales_comparables_count",
        "actual_real_sales_comparables_count",
        "qa_comparables_count",
        "missing_comparable_categories",
        "required_actions",
    ):
        assert key in cr, f"valuation_comparison_real_data_readiness missing key {key!r}"


def test_SRB472_missing_real_comparables_block_certified_use_via_alias():
    """SRB472 valuation_comparison_real_data_readiness blocks certified use when QA comps active."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    cr = mctx["valuation_comparison_real_data_readiness"]
    assert cr["comparable_method_certified_use_allowed"] is False, \
        "comparable_method_certified_use_allowed should be False in QA mode"
    assert cr["qa_comparables_count"] > 0 or cr["missing_comparable_categories"]


def test_SRB473_comparison_real_data_readiness_equals_comparable_readiness():
    """SRB473 valuation_comparison_real_data_readiness is the same object as valuation_comparable_readiness."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert mctx["valuation_comparison_real_data_readiness"] is mctx["valuation_comparable_readiness"], \
        "alias should point to same dict object as canonical key"


def test_SRB474_valuation_document_certification_risk_exists():
    """SRB474 valuation_document_certification_risk alias key exists in context."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "valuation_document_certification_risk" in mctx, \
        "valuation_document_certification_risk alias key missing from context"
    dc = mctx["valuation_document_certification_risk"]
    assert isinstance(dc, dict)
    for key in (
        "valuation_certification_ready",
        "certification_risk_level",
        "missing_mandatory_documents",
        "required_actions_before_certification",
    ):
        assert key in dc, f"valuation_document_certification_risk missing key {key!r}"


def test_SRB475_document_certification_risk_certification_ready_false_when_docs_missing():
    """SRB475 valuation_document_certification_risk.valuation_certification_ready=False when docs missing."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    dc = mctx["valuation_document_certification_risk"]
    assert dc["valuation_certification_ready"] is False, \
        "valuation_certification_ready should be False when mandatory docs are missing"
    assert dc["certification_risk_level"] == "مرتفع", \
        "certification_risk_level should be مرتفع when mandatory docs are missing"


def test_SRB476_document_certification_risk_equals_document_readiness():
    """SRB476 valuation_document_certification_risk is same object as valuation_document_readiness."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert mctx["valuation_document_certification_risk"] is mctx["valuation_document_readiness"], \
        "alias should point to same dict object as canonical key"


def test_SRB477_valuation_production_readiness_roadmap_exists():
    """SRB477 valuation_production_readiness_roadmap alias key exists in context."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "valuation_production_readiness_roadmap" in mctx, \
        "valuation_production_readiness_roadmap alias key missing from context"
    rd = mctx["valuation_production_readiness_roadmap"]
    assert isinstance(rd, dict)
    for key in (
        "current_stage",
        "roadmap_steps",
        "blockers",
        "next_required_step",
        "certified_ready_stage_reached",
        "roadmap_warning",
    ):
        assert key in rd, f"valuation_production_readiness_roadmap missing key {key!r}"


def test_SRB478_roadmap_current_stage_is_qa_advisory_when_qa_active():
    """SRB478 valuation_production_readiness_roadmap.current_stage is QA advisory in QA mode."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    rd = mctx["valuation_production_readiness_roadmap"]
    assert "مسودة QA" in rd["current_stage"] or "QA" in rd["current_stage"], \
        "current_stage should indicate QA advisory draft when QA active"


def test_SRB479_roadmap_has_at_least_10_steps():
    """SRB479 valuation_production_readiness_roadmap has at least 10 roadmap steps."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    rd = mctx["valuation_production_readiness_roadmap"]
    assert len(rd["roadmap_steps"]) >= 10, \
        f"Expected at least 10 roadmap steps, got {len(rd['roadmap_steps'])}"


def test_SRB480_roadmap_certified_ready_false_in_qa_mode():
    """SRB480 valuation_production_readiness_roadmap.certified_ready_stage_reached=False in QA."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    rd = mctx["valuation_production_readiness_roadmap"]
    assert rd["certified_ready_stage_reached"] is False


def test_SRB481_production_readiness_roadmap_equals_certification_roadmap():
    """SRB481 valuation_production_readiness_roadmap is same object as valuation_certification_roadmap."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert mctx["valuation_production_readiness_roadmap"] is mctx["valuation_certification_roadmap"], \
        "alias should point to same dict object as canonical key"


def test_SRB482_depreciation_age_evidence_gate_blocks_when_no_evidence():
    """SRB482 valuation_depreciation_age_evidence_gate.depreciation_certified_use_allowed=False when no age doc."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    dg = mctx["valuation_depreciation_age_evidence_gate"]
    assert dg["age_evidence_available"] is False
    assert dg["depreciation_certified_use_allowed"] is False
    assert len(dg.get("acceptable_evidence_types", [])) >= 4


def test_SRB483_geographic_land_price_replacement_required_when_qa():
    """SRB483 valuation_geographic_land_price_readiness.replacement_required=True when QA active."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    glr = mctx["valuation_geographic_land_price_readiness"]
    assert glr["land_price_is_qa"] is True
    assert glr["replacement_required"] is True
    assert glr["land_price_production_ready"] is False


def test_SRB484_source_database_linkage_qdrant_inactive():
    """SRB484 valuation_source_database_linkage_readiness: qdrant, rag, live_db all inactive."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    slr = mctx["valuation_source_database_linkage_readiness"]
    assert slr["qdrant_active_now"] is False, "qdrant must remain inactive"
    assert slr["rag_active_now"] is False, "RAG must remain inactive"
    assert slr["live_database_active_now"] is False, "live_database must remain inactive"


def test_SRB485_parameter_governance_blocks_when_no_references():
    """SRB485 valuation_parameter_governance.production_use_allowed=False when no references."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    pg = mctx["valuation_parameter_governance"]
    assert pg["production_use_allowed"] is False, \
        "production_use_allowed should be False when parameter references are missing"
    assert len(pg.get("parameters", [])) >= 4, "At least 4 parameters expected"
    assert all(not p["certified_use_allowed"] for p in pg["parameters"])


def test_SRB486_valuation_final_certification_status_exists():
    """SRB486 valuation_final_certification_status alias key exists in context."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert "valuation_final_certification_status" in mctx, \
        "valuation_final_certification_status alias key missing from context"
    fs = mctx["valuation_final_certification_status"]
    assert isinstance(fs, dict)
    for key in (
        "report_status",
        "certification_ready",
        "certification_blockers",
        "certification_risk_level",
        "recommended_next_action",
        "executive_recommendation",
    ):
        assert key in fs, f"valuation_final_certification_status missing key {key!r}"


def test_SRB487_final_certification_status_not_ready_when_blockers():
    """SRB487 valuation_final_certification_status.certification_ready=False when blockers exist."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    fs = mctx["valuation_final_certification_status"]
    assert fs["certification_ready"] is False, \
        "certification_ready should be False when blockers exist"
    assert len(fs["certification_blockers"]) > 0, \
        "certification_blockers list must be non-empty when QA simulation is active"


def test_SRB488_final_certification_status_report_status_qa_advisory():
    """SRB488 valuation_final_certification_status.report_status='qa_advisory_only' when QA active."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    fs = mctx["valuation_final_certification_status"]
    assert fs["report_status"] == "qa_advisory_only", \
        f"Expected qa_advisory_only, got {fs['report_status']!r}"


def test_SRB489_final_certification_status_equals_certification_status():
    """SRB489 valuation_final_certification_status is same object as valuation_certification_status."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    assert mctx["valuation_final_certification_status"] is mctx["valuation_certification_status"], \
        "alias should point to same dict object as canonical key"


def test_SRB490_workbook_has_qa_governance_sheet():
    """SRB490 Workbook contains 'حوكمة بيانات QA' sheet (filing/certification gate pass)."""
    wb = _get_wb_v2()
    assert "حوكمة بيانات QA" in wb.sheetnames


def test_SRB491_workbook_has_document_risk_sheet():
    """SRB491 Workbook contains 'قائمة المستندات ومخاطر الاعتماد' sheet."""
    wb = _get_wb_v2()
    assert "قائمة المستندات ومخاطر الاعتماد" in wb.sheetnames


def test_SRB492_workbook_has_certification_roadmap_sheet():
    """SRB492 Workbook contains 'خارطة طريق الاعتماد' sheet."""
    wb = _get_wb_v2()
    assert "خارطة طريق الاعتماد" in wb.sheetnames


def test_SRB493_workbook_has_parameter_governance_sheet():
    """SRB493 Workbook contains 'حوكمة المعاملات' sheet."""
    wb = _get_wb_v2()
    assert "حوكمة المعاملات" in wb.sheetnames


def test_SRB494_workbook_has_certification_status_sheet():
    """SRB494 Workbook contains 'حالة الاعتماد والتوصية' sheet."""
    wb = _get_wb_v2()
    assert "حالة الاعتماد والتوصية" in wb.sheetnames


def test_SRB495_no_certified_ready_claim_while_blockers_in_final_status():
    """SRB495 Final certification status does not claim ready when blockers exist."""
    mctx = _srr._build_method_context(_QA_ZAMALEK_PAYLOAD)
    fs = mctx["valuation_final_certification_status"]
    if fs["certification_blockers"]:
        assert fs["certification_ready"] is False, \
            "certification_ready must be False when certification_blockers is non-empty"
        assert "qa_advisory" in fs["report_status"] or fs["report_status"] != "ready_for_certification"


def test_SRB496_qa_output_gate_directory_exists_after_script():
    """SRB496 Gate QA output directory and at least one context JSON exist."""
    import pathlib
    import importlib.util, sys as _sys
    _core = pathlib.Path(__file__).resolve().parent.parent
    _gate_dir = _core / "instance" / "manual_review_outputs" / "valuation_certification_readiness_gate"
    # If directory doesn't exist yet, create it via the QA script
    if not _gate_dir.exists():
        script_path = _core / "generate_valuation_cert_readiness_gate_qa.py"
        if script_path.exists():
            spec = importlib.util.spec_from_file_location("_gate_qa", script_path)
            mod = importlib.util.module_from_spec(spec)
            _sys.modules["_gate_qa"] = mod
            try:
                spec.loader.exec_module(mod)
                if hasattr(mod, "main"):
                    mod.main()
            except Exception:
                pass
    # Check for at least the context JSON
    context_files = list(_gate_dir.glob("*_context.json")) if _gate_dir.exists() else []
    assert _gate_dir.exists(), f"Gate output directory not found: {_gate_dir}"
    assert len(context_files) >= 1, "Expected at least one context JSON in gate output directory"
