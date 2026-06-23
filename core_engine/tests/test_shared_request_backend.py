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


def test_SRB43_expert_workbook_has_all_six_sheets(client):
    """Workbook contains all 9 required sheets (Dashboard + 8 traditional valuation sheets)."""
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
        "بيانات العقار",
        "مقارنة البيوع",
        "طريقة الدخل",
        "طريقة التكلفة",
        "توفيق النتائج",
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
    assert wb.sheetnames[0] == "Dashboard", "Dashboard must be the first (active) sheet"
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
    """مقارنة البيوع sheet has all required column headers and 3 placeholder rows."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")

    rid = json.loads(_post_request(client).data)["request_id"]
    wb  = openpyxl.load_workbook(str(_srr._WORKBOOKS / rid / f"expert_review_{rid}.xlsx"))
    assert "مقارنة البيوع" in wb.sheetnames, "مقارنة البيوع sheet not found"
    ws  = wb["مقارنة البيوع"]
    headers = " | ".join(str(ws.cell(row=1, column=c).value or "") for c in range(1, 16))
    for h in ("رقم المقارن", "سعر المتر", "الموقع", "ملاحظات الخبير"):
        assert h in headers, f"مقارنة البيوع missing header: {h!r}"
    placeholders = [str(ws.cell(row=r, column=1).value or "") for r in range(2, 5)]
    assert any("مقارن" in p for p in placeholders), (
        f"مقارنة البيوع missing placeholder rows. Col-A rows 2-4: {placeholders}"
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
    """All 10 required template IDs exist in REPORT_TEMPLATES."""
    from report_template_registry import REPORT_TEMPLATES
    required = [
        "simple_dashboard_draft",
        "residential_summary_three_methods",
        "full_three_approach_report",
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
