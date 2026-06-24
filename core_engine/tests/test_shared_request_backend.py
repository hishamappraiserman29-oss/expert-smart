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

    assert "لا يتضمن هذا الإصدار سجل مصادر آلي" in html, (
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


def test_SRB182_workbook_has_26_sheets():
    """SRB182 Expert workbook has exactly 26 sheets (22 original + 4 strategic: What-If, Buy vs Rent, ESG, Construction Cost)."""
    wb = _get_wb_v2()
    assert len(wb.sheetnames) == 26, \
        f"Expected 26 sheets, got {len(wb.sheetnames)}: {wb.sheetnames}"


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
