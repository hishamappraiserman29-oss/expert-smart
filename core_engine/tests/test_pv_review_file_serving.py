"""
test_pv_review_file_serving.py
26 focused tests — Report Review file-display chain.

Covers:
  T01–T09  Backend response contract (user/admin URLs, no local paths, no admin leakage)
  T10–T14  Physical file integrity (PDF sig, HTML non-empty, XLSX sig, missing-file guard)
  T15–T16  Authorization guards (no client audience escalation, admin-only Excel)
  T17–T18  Path traversal rejection
  T19–T26  Frontend result-area contract (via HTML source inspection)

advisory_only=True | not_real_training=True | fake_reviewer_signature_created=False
"""
from __future__ import annotations

import importlib
import json
import pathlib
import sys
import unittest.mock as mock

import pytest

# ── Locate core_engine root ───────────────────────────────────────────────────
_CORE = pathlib.Path(__file__).resolve().parent.parent
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

# ── Import the endpoint module directly (no Flask app needed for builder tests) ─
import pv_report_review_endpoint as _ep

_OUTPUTS = _CORE / "outputs"


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def flask_app():
    """Minimal Flask test app with the review endpoint registered."""
    flask_mod = pytest.importorskip("flask", reason="flask not installed in test environment")
    Flask = flask_mod.Flask
    g = flask_mod.g
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"

    # Auth stubs
    _users: dict[str, dict] = {
        "user_normal": {"is_admin": False},
        "user_admin":  {"is_admin": True},
    }

    def _require_auth(fn):
        from functools import wraps
        from flask import request as _req, jsonify as _json
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = (_req.headers.get("Authorization", "") or "").replace("Bearer ", "")
            if token not in _users:
                return _json({"status": "unauthorized"}), 401
            g.user_id = token
            return fn(*args, **kwargs)
        return wrapper

    def _is_admin(user_id):
        return _users.get(user_id or "", {}).get("is_admin", False)

    _ep.register_review_endpoint(app, _require_auth, _is_admin, str(_OUTPUTS))
    return app


@pytest.fixture()
def user_client(flask_app):
    with flask_app.test_client() as c:
        yield c


@pytest.fixture()
def admin_client(flask_app):
    with flask_app.test_client() as c:
        yield c


def _post_review(client, token: str, extra: dict | None = None):
    """POST a minimal valid Qatar review payload."""
    data = {
        "reviewer_name": "مراجع اختبار",
        "review_client": "عميل اختبار",
        "reviewed_report_id": "QA-QATAR-REVIEW-FILES-001",
        "case_id": "QA-QATAR-REVIEW-FILES-001",
        "country_ar": "قطر",
        "city_ar": "لوسيل",
        "district_ar": "فوكس هيلز",
        "currency_code": "QAR",
        "asset_type_ar": "فيلا سكنية",
        "review_date": "2026-07-01",
        "reported_value": "5000000",
        "gross_income": "350000",
        "cap_rate": "7.0",
        "vacancy_rate": "10",
        "built_up_area_m2": "850",
        "land_area_m2": "1200",
        "comp1_price": "4800000", "comp1_area": "800", "comp1_adj": "2",
        "comp2_price": "5200000", "comp2_area": "900", "comp2_adj": "-1",
        "comp3_price": "4900000", "comp3_area": "820", "comp3_adj": "1",
        **(extra or {}),
    }
    return client.post(
        "/api/professional-valuation/generate-report-review",
        data=data,
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# T01–T09  Backend response contract
# ═══════════════════════════════════════════════════════════════════════════════

def test_T01_user_response_returns_pdf_url(user_client):
    r = _post_review(user_client, "user_normal")
    d = json.loads(r.data)
    assert d.get("ok") is True, d.get("error", d)
    assert "pdf_url" in d and d["pdf_url"], "pdf_url missing or empty"


def test_T02_user_response_returns_html_view_url(user_client):
    r = _post_review(user_client, "user_normal")
    d = json.loads(r.data)
    assert "html_url" in d and d["html_url"], "html_url missing or empty"


def test_T03_user_response_returns_html_download_url(user_client):
    r = _post_review(user_client, "user_normal")
    d = json.loads(r.data)
    assert "html_download_url" in d and d["html_download_url"], "html_download_url missing"


def test_T04_user_response_contains_no_excel_url(user_client):
    r = _post_review(user_client, "user_normal")
    d = json.loads(r.data)
    assert "excel_url" not in d or not d.get("excel_url"), "User response must not include excel_url"


def test_T05_user_response_contains_no_admin_filenames(user_client):
    r = _post_review(user_client, "user_normal")
    raw = r.data.decode("utf-8")
    assert "_admin." not in raw, f"Admin filenames leaked to normal user response: {raw[:400]}"


def test_T06_admin_response_returns_pdf_url(admin_client):
    r = _post_review(admin_client, "user_admin")
    d = json.loads(r.data)
    assert d.get("ok") is True, d.get("error", d)
    assert "pdf_url" in d and d["pdf_url"], "Admin pdf_url missing"


def test_T07_admin_response_returns_html_urls(admin_client):
    r = _post_review(admin_client, "user_admin")
    d = json.loads(r.data)
    assert "html_url" in d and d["html_url"], "Admin html_url missing"
    assert "html_download_url" in d and d["html_download_url"], "Admin html_download_url missing"


def test_T08_admin_response_returns_excel_url(admin_client):
    r = _post_review(admin_client, "user_admin")
    d = json.loads(r.data)
    # Excel requires openpyxl; skip if builder returns xl_ok=False
    if not d.get("excel_url"):
        pytest.skip("Excel not generated (openpyxl or xlsxwriter not available)")
    assert d["excel_url"].startswith("/api/professional-valuation/review-admin-download/"), (
        f"Admin excel_url has unexpected prefix: {d['excel_url']}"
    )


def test_T09_returned_urls_are_relative_not_local_paths(user_client, admin_client):
    for client, token in [(user_client, "user_normal"), (admin_client, "user_admin")]:
        d = json.loads(_post_review(client, token).data)
        for key in ("pdf_url", "html_url", "html_download_url", "excel_url"):
            val = d.get(key, "")
            if not val:
                continue
            assert not val.startswith("http"), (
                f"Absolute URL found in {key}: {val!r} — must be relative"
            )
            assert "C:\\" not in val and "C:/" not in val and "/home/" not in val, (
                f"Local filesystem path found in {key}: {val!r}"
            )
            assert "127.0.0.1" not in val and "localhost" not in val, (
                f"Hardcoded host found in {key}: {val!r}"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# T10–T14  Physical file integrity
# ═══════════════════════════════════════════════════════════════════════════════

def _get_fname(d: dict, key: str) -> pathlib.Path | None:
    url = d.get(key, "")
    if not url:
        return None
    fname = url.split("/")[-1].split("?")[0]
    p = _OUTPUTS / fname
    return p if p.exists() else None


def test_T10_returned_pdf_physically_exists(user_client):
    d = json.loads(_post_review(user_client, "user_normal").data)
    assert d.get("ok"), d.get("error")
    p = _get_fname(d, "pdf_url")
    assert p is not None and p.exists(), f"User PDF not on disk: {d.get('pdf_url')}"
    assert p.stat().st_size > 0, "User PDF is zero bytes"


def test_T11_returned_pdf_has_valid_signature(user_client):
    d = json.loads(_post_review(user_client, "user_normal").data)
    assert d.get("ok"), d.get("error")
    p = _get_fname(d, "pdf_url")
    if p is None:
        pytest.skip("PDF not on disk")
    header = p.read_bytes()[:5]
    assert header == b"%PDF-", f"PDF does not start with %PDF-: {header!r}"


def test_T12_returned_html_is_non_empty(user_client):
    d = json.loads(_post_review(user_client, "user_normal").data)
    assert d.get("ok"), d.get("error")
    p = _get_fname(d, "html_download_url")
    if p is None:
        p = _get_fname(d, "html_url")
    assert p is not None and p.exists(), "HTML file not on disk"
    text = p.read_text(encoding="utf-8", errors="replace")
    assert len(text) > 200, f"HTML too short ({len(text)} chars)"
    assert "<html" in text.lower(), "HTML file missing <html> tag"


def test_T13_admin_excel_has_valid_xlsx_signature(admin_client):
    d = json.loads(_post_review(admin_client, "user_admin").data)
    assert d.get("ok"), d.get("error")
    if not d.get("excel_url"):
        pytest.skip("Excel not generated")
    fname = d["excel_url"].split("/")[-1]
    p = _OUTPUTS / fname
    if not p.exists():
        pytest.skip("Excel file not on disk")
    # XLSX files are ZIP archives starting with PK\x03\x04
    sig = p.read_bytes()[:4]
    assert sig == b"PK\x03\x04", f"XLSX has invalid ZIP signature: {sig!r}"


def test_T14_missing_file_does_not_return_fake_success(flask_app):
    """Requesting a non-existent file via the download route must return 404, not 200."""
    with flask_app.test_client() as c:
        r = c.get(
            "/api/professional-valuation/review-admin-download/review_nonexistent_admin.pdf",
            headers={"Authorization": "Bearer user_admin"},
        )
        assert r.status_code == 404, f"Expected 404 for missing file, got {r.status_code}"


# ═══════════════════════════════════════════════════════════════════════════════
# T15–T16  Authorization
# ═══════════════════════════════════════════════════════════════════════════════

def test_T15_client_cannot_select_admin_audience(user_client):
    """Sending audience=admin in the payload must NOT grant admin outputs."""
    r = _post_review(user_client, "user_normal", extra={"audience": "admin"})
    d = json.loads(r.data)
    assert d.get("ok"), d.get("error")
    assert "excel_url" not in d or not d.get("excel_url"), (
        "Client-supplied audience=admin was honoured — server must determine role itself"
    )
    raw = r.data.decode("utf-8")
    assert "_admin." not in raw, "Admin artifact leaked when client sent audience=admin"


def test_T16_normal_user_cannot_access_admin_excel(flask_app):
    """Normal user hitting review-admin-download must receive HTTP 403."""
    # First generate as admin so a real admin file exists
    with flask_app.test_client() as admin_c:
        d = json.loads(_post_review(admin_c, "user_admin").data)
    excel_url = d.get("excel_url", "")
    if not excel_url:
        pytest.skip("Excel not generated; cannot test 403")
    fname = excel_url.split("/")[-1]

    with flask_app.test_client() as user_c:
        r = user_c.get(
            f"/api/professional-valuation/review-admin-download/{fname}",
            headers={"Authorization": "Bearer user_normal"},
        )
    assert r.status_code == 403, (
        f"Normal user got {r.status_code} instead of 403 on admin-download route"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# T17–T18  Path traversal
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("traversal", [
    "../../../etc/passwd",
    "..\\..\\..\\Windows\\System32\\config\\SAM",
    "%2e%2e%2f%2e%2e%2f",
    "review_ok%00.html",
])
def test_T17_admin_download_rejects_path_traversal(flask_app, traversal):
    with flask_app.test_client() as c:
        r = c.get(
            f"/api/professional-valuation/review-admin-download/{traversal}",
            headers={"Authorization": "Bearer user_admin"},
        )
    assert r.status_code in (400, 404), (
        f"Traversal {traversal!r} was not rejected: status={r.status_code}"
    )


@pytest.mark.parametrize("traversal", [
    "../../../etc/passwd",
    "..\\Windows\\System32",
])
def test_T18_admin_view_rejects_path_traversal(flask_app, traversal):
    with flask_app.test_client() as c:
        r = c.get(
            f"/api/professional-valuation/review-admin-view/{traversal}",
            headers={"Authorization": "Bearer user_admin"},
        )
    assert r.status_code in (400, 404), (
        f"Traversal {traversal!r} was not rejected on view route: status={r.status_code}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# T19–T26  Frontend result-area contract (static HTML source inspection)
# ═══════════════════════════════════════════════════════════════════════════════

_FRONTEND = _CORE.parent / "frontend" / "index.html"


def _html() -> str:
    if not _FRONTEND.exists():
        pytest.skip("frontend/index.html not found")
    return _FRONTEND.read_text(encoding="utf-8", errors="ignore")


def test_T19_no_result_links_before_successful_response():
    """Download controls must be inside rr-download-section which starts hidden."""
    h = _html()
    import re
    # Find the rr-download-section div
    m = re.search(r'id="rr-download-section"[^>]*style="([^"]*)"', h)
    assert m, "rr-download-section element not found"
    assert "display:none" in m.group(1) or "display: none" in m.group(1), (
        f"rr-download-section is not initially hidden: style={m.group(1)!r}"
    )


def test_T20_loading_state_message_present():
    h = _html()
    assert "جاري مراجعة التقرير وإعداد" in h, "Loading state Arabic message not found in JS"


def test_T21_new_request_clears_old_links():
    h = _html()
    assert "el.onclick = null" in h, "Stale onclick not cleared before new generation"


def test_T22_admin_excel_section_starts_hidden():
    h = _html()
    import re
    m = re.search(r'id="rr-admin-excel-section"[^>]*style="([^"]*)"', h)
    assert m, "rr-admin-excel-section not found"
    assert "display:none" in m.group(1) or "display: none" in m.group(1), (
        f"rr-admin-excel-section is not initially hidden: {m.group(1)!r}"
    )


def test_T23_esDownloadAuth_function_present():
    h = _html()
    assert "function esDownloadAuth" in h, "esDownloadAuth helper function not found"
    assert "URL.createObjectURL" in h, "Blob URL creation missing from esDownloadAuth"


def test_T24_esViewAuth_function_present():
    h = _html()
    assert "function esViewAuth" in h, "esViewAuth helper function not found"
    assert "window.open" in h, "window.open missing from esViewAuth"


def test_T25_ok_check_present_before_showing_download_section():
    h = _html()
    assert "if (!d.ok)" in h or 'if(!d.ok)' in h, (
        "Missing d.ok check — download section would show on backend errors"
    )


def test_T26_view_html_link_has_noopener():
    h = _html()
    import re
    m = re.search(r'id="rr-view-review-html"[^>]*', h)
    assert m, "rr-view-review-html anchor not found"
    snippet = m.group(0)
    assert "noopener" in snippet, (
        f"rr-view-review-html missing rel=noopener: {snippet!r}"
    )
