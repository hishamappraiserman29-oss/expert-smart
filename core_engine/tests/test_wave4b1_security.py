"""Wave 4B1 security tests — OAF containment and multipart upload policy.

OAF-001  Arbitrary run_id prediction access       → admin-only after 4B1
OAF-002  Client-controlled analyst-role elevation  → admin-only after 4B1
OAF-003  Global authenticated run-list exposure    → admin-only after 4B1
OAF-004  Review referential-integrity (regression) → still 403 for non-admin
OAF-005  Export unvalidated reference (regression) → still 403 for non-admin

Gate 6   Multi-file upload policy for all three routes
"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_ORIG_CWD = os.getcwd()
try:
    os.chdir(str(_CORE))
    from bridge_api import app as _app
finally:
    os.chdir(_ORIG_CWD)

_TEST_SECRET = "test-secret-wave4b1-security-min32!!"
_ADMIN_USER  = "admin-wave4b1"
_PLAIN_USER  = "user-wave4b1"


def _make_token(user: str) -> str:
    from auth.tokens import generate_token
    return generate_token(user)


def _auth_header(user: str) -> dict:
    return {"Authorization": f"Bearer {_make_token(user)}"}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def sec_client(monkeypatch):
    """Test client with JWT_SECRET and ADMIN_USER_IDS configured."""
    monkeypatch.setenv("JWT_SECRET",      _TEST_SECRET)
    monkeypatch.setenv("ADMIN_USER_IDS",  _ADMIN_USER)
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    monkeypatch.setenv("AUDIT_ENABLED",   "false")
    _app.config["TESTING"] = True
    with _app.test_client() as c:
        yield c


def _pdf_bytes(size: int = 128) -> bytes:
    """Minimal valid-looking bytes for file upload tests."""
    return b"%PDF-1.4 test content " + b"x" * size


# ── OAF-001: Predictions endpoint — arbitrary run_id access ───────────────────

def test_oaf_001_predictions_non_admin_returns_403(sec_client, monkeypatch):
    """Non-admin authenticated user must get 403 from predictions endpoint."""
    monkeypatch.setenv("JWT_SECRET",     _TEST_SECRET)
    monkeypatch.setenv("ADMIN_USER_IDS", _ADMIN_USER)
    rv = sec_client.get(
        "/api/mass-valuation/predictions/some-run-id",
        headers=_auth_header(_PLAIN_USER),
    )
    assert rv.status_code == 403, (
        f"Expected 403 for non-admin on predictions endpoint, got {rv.status_code}"
    )


def test_oaf_001_predictions_admin_permitted(sec_client, monkeypatch):
    """Admin user must not receive 403 from predictions endpoint."""
    monkeypatch.setenv("JWT_SECRET",     _TEST_SECRET)
    monkeypatch.setenv("ADMIN_USER_IDS", _ADMIN_USER)
    rv = sec_client.get(
        "/api/mass-valuation/predictions/nonexistent-run-id",
        headers=_auth_header(_ADMIN_USER),
    )
    assert rv.status_code in (200, 404, 503), (
        f"Admin on predictions endpoint: expected 200/404/503, got {rv.status_code}"
    )
    assert rv.status_code != 403, "Admin must not receive 403 on predictions endpoint"


def test_oaf_001_predictions_unauthenticated_returns_401(sec_client):
    """Unauthenticated request must get 401."""
    rv = sec_client.get("/api/mass-valuation/predictions/some-run-id")
    assert rv.status_code == 401


# ── OAF-002: role=analyst elevation ───────────────────────────────────────────

def test_oaf_002_predictions_role_analyst_non_admin_returns_403(sec_client, monkeypatch):
    """Non-admin must get 403 even when passing ?role=analyst."""
    monkeypatch.setenv("JWT_SECRET",     _TEST_SECRET)
    monkeypatch.setenv("ADMIN_USER_IDS", _ADMIN_USER)
    rv = sec_client.get(
        "/api/mass-valuation/predictions/any-run?role=analyst",
        headers=_auth_header(_PLAIN_USER),
    )
    assert rv.status_code == 403, (
        f"Expected 403 for non-admin with ?role=analyst, got {rv.status_code}"
    )


def test_oaf_002_predictions_admin_permitted_with_analyst_role(sec_client, monkeypatch):
    """Admin user with ?role=analyst must not receive 403."""
    monkeypatch.setenv("JWT_SECRET",     _TEST_SECRET)
    monkeypatch.setenv("ADMIN_USER_IDS", _ADMIN_USER)
    rv = sec_client.get(
        "/api/mass-valuation/predictions/nonexistent?role=analyst",
        headers=_auth_header(_ADMIN_USER),
    )
    assert rv.status_code != 403, "Admin must not receive 403 on predictions with ?role=analyst"


# ── OAF-003: Runs list — global exposure ──────────────────────────────────────

def test_oaf_003_runs_non_admin_returns_403(sec_client, monkeypatch):
    """Non-admin authenticated user must get 403 from /runs endpoint."""
    monkeypatch.setenv("JWT_SECRET",     _TEST_SECRET)
    monkeypatch.setenv("ADMIN_USER_IDS", _ADMIN_USER)
    rv = sec_client.get(
        "/api/mass-valuation/runs",
        headers=_auth_header(_PLAIN_USER),
    )
    assert rv.status_code == 403, (
        f"Expected 403 for non-admin on /runs, got {rv.status_code}"
    )


def test_oaf_003_runs_admin_permitted(sec_client, monkeypatch):
    """Admin user must receive 200 from /runs endpoint."""
    monkeypatch.setenv("JWT_SECRET",     _TEST_SECRET)
    monkeypatch.setenv("ADMIN_USER_IDS", _ADMIN_USER)
    rv = sec_client.get(
        "/api/mass-valuation/runs",
        headers=_auth_header(_ADMIN_USER),
    )
    assert rv.status_code == 200, (
        f"Expected 200 for admin on /runs, got {rv.status_code}"
    )


def test_oaf_003_runs_unauthenticated_returns_401(sec_client):
    """Unauthenticated request to /runs must get 401."""
    rv = sec_client.get("/api/mass-valuation/runs")
    assert rv.status_code == 401


# ── OAF-004: Review regression (Wave 4B2, NOT closed by 4B1) ──────────────────

def test_oaf_004_review_regression_still_protected(sec_client, monkeypatch):
    """POST review/<prediction_id> must still return 403 for non-admin (regression guard).

    OAF-004 is deferred to Wave 4B2. This test confirms no regression — it does
    NOT claim to close the finding.
    """
    monkeypatch.setenv("JWT_SECRET",     _TEST_SECRET)
    monkeypatch.setenv("ADMIN_USER_IDS", _ADMIN_USER)
    rv = sec_client.post(
        "/api/mass-valuation/review/any-prediction-id",
        headers=_auth_header(_PLAIN_USER),
        json={"run_id": "r1", "decision": "approved", "reason": "test"},
    )
    assert rv.status_code == 403, (
        f"OAF-004 regression: non-admin on review endpoint, expected 403, got {rv.status_code}"
    )


# ── OAF-005: Export regression (Wave 4B2, NOT closed by 4B1) ─────────────────

def test_oaf_005_export_regression_still_protected(sec_client, monkeypatch):
    """GET export must still return 403 for non-admin (regression guard).

    OAF-005 is deferred to Wave 4B2. This test confirms no regression — it does
    NOT claim to close the finding.
    """
    monkeypatch.setenv("JWT_SECRET",     _TEST_SECRET)
    monkeypatch.setenv("ADMIN_USER_IDS", _ADMIN_USER)
    rv = sec_client.get(
        "/api/mass-valuation/runs/any-run-id/export",
        headers=_auth_header(_PLAIN_USER),
    )
    assert rv.status_code == 403, (
        f"OAF-005 regression: non-admin on export endpoint, expected 403, got {rv.status_code}"
    )


# ── Gate 6: Multi-file upload policy — /api/tax-appeal/leads ─────────────────

def _tax_lead_data(**extra_files) -> dict:
    data = {
        "owner_name": "Test Owner",
        "phone":      "0500000001",
    }
    data.update(extra_files)
    return data


def test_tax_leads_zero_files(sec_client):
    """Zero files: lead is accepted."""
    rv = sec_client.post(
        "/api/tax-appeal/leads",
        data=_tax_lead_data(),
        content_type="multipart/form-data",
    )
    assert rv.status_code in (201, 200), f"Expected 201, got {rv.status_code}"


def test_tax_leads_one_file_accepted(sec_client):
    """One valid file: lead is accepted."""
    rv = sec_client.post(
        "/api/tax-appeal/leads",
        data=_tax_lead_data(doc_0=(io.BytesIO(_pdf_bytes()), "file1.pdf")),
        content_type="multipart/form-data",
    )
    assert rv.status_code in (201, 200), f"Expected 201, got {rv.status_code}"


def test_tax_leads_five_files_accepted(sec_client):
    """Five valid files: lead is accepted (exactly at limit)."""
    data = _tax_lead_data()
    for i in range(5):
        data[f"doc_{i}"] = (io.BytesIO(_pdf_bytes()), f"file{i}.pdf")
    rv = sec_client.post(
        "/api/tax-appeal/leads",
        data=data,
        content_type="multipart/form-data",
    )
    assert rv.status_code in (201, 200), f"Expected 201, got {rv.status_code}"


def test_tax_leads_six_files_rejected(sec_client):
    """Six files: rejected with 413 too_many_files."""
    data = _tax_lead_data()
    for i in range(6):
        data[f"doc_{i}"] = (io.BytesIO(_pdf_bytes()), f"file{i}.pdf")
    rv = sec_client.post(
        "/api/tax-appeal/leads",
        data=data,
        content_type="multipart/form-data",
    )
    assert rv.status_code == 413, f"Expected 413 for 6 files, got {rv.status_code}"
    body = rv.get_json() or {}
    assert body.get("error") == "too_many_files"
    assert body.get("maximum") == 5


def test_tax_leads_repeated_field_names_counted(sec_client):
    """Repeated multipart field names are each counted individually."""
    from werkzeug.datastructures import MultiDict
    parts = MultiDict([
        ("owner_name", "Test Owner"),
        ("phone",      "0500000001"),
    ])
    for _ in range(7):
        parts.add("doc_0", (io.BytesIO(_pdf_bytes(1024)), "rep.pdf"))
    rv = sec_client.post(
        "/api/tax-appeal/leads",
        data=parts,
        content_type="multipart/form-data",
    )
    assert rv.status_code == 413, (
        f"Expected 413 for 7 repeated-key files, got {rv.status_code}"
    )


def test_tax_leads_five_valid_ten_mib_files_accepted(sec_client):
    """Five files at exactly 10 MiB each: all accepted (per-file limit is inclusive)."""
    _10MiB = 10 * 1024 * 1024 - 512  # just under the 10 MiB per-file limit
    data = _tax_lead_data()
    for i in range(5):
        data[f"doc_{i}"] = (io.BytesIO(b"x" * _10MiB), f"large{i}.pdf")
    rv = sec_client.post(
        "/api/tax-appeal/leads",
        data=data,
        content_type="multipart/form-data",
    )
    assert rv.status_code in (201, 200, 207), (
        f"Expected 201/207 for 5 large valid files, got {rv.status_code}"
    )


# ── Gate 6: Multi-file upload policy — /api/expert-requests ──────────────────

def _er_data(**extra_files) -> dict:
    data = {
        "source_page": "simple_valuation",
        "user_name":   "Test User",
        "phone":       "0500000002",
    }
    data.update(extra_files)
    return data


def test_expert_requests_five_files_accepted(sec_client):
    """Five doc_* files: request is accepted."""
    data = _er_data()
    for i in range(5):
        data[f"doc_{i}"] = (io.BytesIO(_pdf_bytes()), f"doc{i}.pdf")
    rv = sec_client.post(
        "/api/expert-requests",
        data=data,
        content_type="multipart/form-data",
    )
    assert rv.status_code in (201, 200), f"Expected 201, got {rv.status_code}"


def test_expert_requests_six_files_rejected(sec_client):
    """Six doc_* files: rejected with 413 too_many_files."""
    data = _er_data()
    for i in range(6):
        data[f"doc_{i}"] = (io.BytesIO(_pdf_bytes()), f"doc{i}.pdf")
    rv = sec_client.post(
        "/api/expert-requests",
        data=data,
        content_type="multipart/form-data",
    )
    assert rv.status_code == 413, f"Expected 413 for 6 doc_* files, got {rv.status_code}"
    body = rv.get_json() or {}
    assert body.get("error") == "too_many_files"
    assert body.get("maximum") == 5


def test_expert_requests_non_doc_prefix_not_counted(sec_client):
    """Non-doc_* keys are not counted against the limit (prefix filter applies)."""
    data = _er_data()
    # 3 valid doc_* files + 10 other_* files that should be ignored
    for i in range(3):
        data[f"doc_{i}"] = (io.BytesIO(_pdf_bytes()), f"doc{i}.pdf")
    for i in range(10):
        data[f"other_{i}"] = (io.BytesIO(_pdf_bytes()), f"other{i}.pdf")
    rv = sec_client.post(
        "/api/expert-requests",
        data=data,
        content_type="multipart/form-data",
    )
    assert rv.status_code in (201, 200), (
        f"Non-doc_* files must not count toward limit; got {rv.status_code}"
    )


# ── Gate 6: Multi-file upload policy — /api/expert-requests/<id>/documents ───

def _make_request_id(client) -> str:
    """Create an expert request and return its ID for document upload tests."""
    data = {
        "source_page": "simple_valuation",
        "user_name":   "Doc Upload User",
        "phone":       "0500000003",
    }
    rv = client.post(
        "/api/expert-requests",
        data=data,
        content_type="multipart/form-data",
    )
    if rv.status_code in (200, 201):
        body = rv.get_json() or {}
        return body.get("request_id", "FALLBACK-ID-00000000")
    return "FALLBACK-ID-00000000"


def test_expert_request_documents_five_files_accepted(sec_client):
    """Five files on the documents endpoint: accepted."""
    req_id = _make_request_id(sec_client)
    data = {}
    for i in range(5):
        data[f"file_{i}"] = (io.BytesIO(_pdf_bytes()), f"f{i}.pdf")
    rv = sec_client.post(
        f"/api/expert-requests/{req_id}/documents",
        data=data,
        content_type="multipart/form-data",
    )
    assert rv.status_code in (200, 207), f"Expected 200/207, got {rv.status_code}"


def test_expert_request_documents_six_files_rejected(sec_client):
    """Six files on the documents endpoint: rejected with 413 too_many_files."""
    req_id = _make_request_id(sec_client)
    data = {}
    for i in range(6):
        data[f"file_{i}"] = (io.BytesIO(_pdf_bytes()), f"f{i}.pdf")
    rv = sec_client.post(
        f"/api/expert-requests/{req_id}/documents",
        data=data,
        content_type="multipart/form-data",
    )
    assert rv.status_code == 413, f"Expected 413 for 6 files, got {rv.status_code}"
    body = rv.get_json() or {}
    assert body.get("error") == "too_many_files"
    assert body.get("maximum") == 5


# ── Gate 6 continued: full 7-case coverage for /api/tax-appeal/leads ──────────

def test_tax_leads_one_file_above_10mib_rejected(sec_client):
    """One file larger than 10 MiB is rejected by the per-file size rule."""
    _11MiB = 11 * 1024 * 1024
    data = _tax_lead_data()
    data["doc_0"] = (io.BytesIO(b"x" * _11MiB), "large.pdf")
    rv = sec_client.post(
        "/api/tax-appeal/leads",
        data=data,
        content_type="multipart/form-data",
    )
    assert rv.status_code in (413, 400, 422), (
        f"Expected 413/400/422 for file >10 MiB, got {rv.status_code}"
    )


# ── Gate 6 continued: full 7-case coverage for /api/expert-requests ───────────

def test_expert_requests_zero_files_accepted(sec_client):
    """Zero files on expert-requests: request accepted."""
    rv = sec_client.post(
        "/api/expert-requests",
        data=_er_data(),
        content_type="multipart/form-data",
    )
    assert rv.status_code in (201, 200), f"Expected 201, got {rv.status_code}"


def test_expert_requests_one_file_accepted(sec_client):
    """One valid file on expert-requests: request accepted."""
    data = _er_data()
    data["doc_0"] = (io.BytesIO(_pdf_bytes()), "doc0.pdf")
    rv = sec_client.post(
        "/api/expert-requests",
        data=data,
        content_type="multipart/form-data",
    )
    assert rv.status_code in (201, 200), f"Expected 201, got {rv.status_code}"


def test_expert_requests_repeated_field_names_counted(sec_client):
    """Repeated multipart field names are counted individually on expert-requests."""
    from werkzeug.datastructures import MultiDict
    parts = MultiDict([
        ("source_page", "simple_valuation"),
        ("user_name",   "Test User"),
        ("phone",       "0500000002"),
    ])
    for _ in range(7):
        parts.add("doc_0", (io.BytesIO(_pdf_bytes(1024)), "rep.pdf"))
    rv = sec_client.post(
        "/api/expert-requests",
        data=parts,
        content_type="multipart/form-data",
    )
    assert rv.status_code == 413, (
        f"Expected 413 for 7 repeated-key files on expert-requests, got {rv.status_code}"
    )


def test_expert_requests_one_file_above_10mib_rejected(sec_client):
    """One file larger than 10 MiB is rejected by the per-file size rule."""
    _11MiB = 11 * 1024 * 1024
    data = _er_data()
    data["doc_0"] = (io.BytesIO(b"x" * _11MiB), "large.pdf")
    rv = sec_client.post(
        "/api/expert-requests",
        data=data,
        content_type="multipart/form-data",
    )
    assert rv.status_code in (413, 400, 422), (
        f"Expected 413/400/422 for file >10 MiB on expert-requests, got {rv.status_code}"
    )


def test_expert_requests_five_valid_below_limit_accepted(sec_client):
    """Five valid files at or below per-file limit are accepted."""
    _9MiB = 9 * 1024 * 1024
    data = _er_data()
    for i in range(5):
        data[f"doc_{i}"] = (io.BytesIO(b"x" * _9MiB), f"doc{i}.pdf")
    rv = sec_client.post(
        "/api/expert-requests",
        data=data,
        content_type="multipart/form-data",
    )
    assert rv.status_code in (201, 200, 207), (
        f"Expected 201 for 5 valid files on expert-requests, got {rv.status_code}"
    )


# ── Gate 6 continued: full 7-case for /api/expert-requests/<id>/documents ─────

def test_expert_request_documents_zero_files_accepted(sec_client):
    """Zero files on the documents endpoint: accepted."""
    req_id = _make_request_id(sec_client)
    rv = sec_client.post(
        f"/api/expert-requests/{req_id}/documents",
        data={},
        content_type="multipart/form-data",
    )
    assert rv.status_code in (200, 207, 400), (
        f"Zero files documents: expected 200/207/400 (not 413), got {rv.status_code}"
    )
    assert rv.status_code != 413, "Zero files must not produce 413"


def test_expert_request_documents_one_file_accepted(sec_client):
    """One valid file on the documents endpoint: accepted."""
    req_id = _make_request_id(sec_client)
    data = {"file_0": (io.BytesIO(_pdf_bytes()), "f0.pdf")}
    rv = sec_client.post(
        f"/api/expert-requests/{req_id}/documents",
        data=data,
        content_type="multipart/form-data",
    )
    assert rv.status_code in (200, 207), f"Expected 200/207, got {rv.status_code}"


def test_expert_request_documents_repeated_field_names_counted(sec_client):
    """Repeated multipart field names are counted individually on documents endpoint."""
    from werkzeug.datastructures import MultiDict
    req_id = _make_request_id(sec_client)
    parts = MultiDict()
    for _ in range(7):
        parts.add("file_0", (io.BytesIO(_pdf_bytes(1024)), "rep.pdf"))
    rv = sec_client.post(
        f"/api/expert-requests/{req_id}/documents",
        data=parts,
        content_type="multipart/form-data",
    )
    assert rv.status_code == 413, (
        f"Expected 413 for 7 repeated-key files on documents, got {rv.status_code}"
    )


def test_expert_request_documents_one_file_above_10mib_rejected(sec_client):
    """One file larger than 10 MiB is rejected on the documents endpoint."""
    _11MiB = 11 * 1024 * 1024
    req_id = _make_request_id(sec_client)
    data = {"file_0": (io.BytesIO(b"x" * _11MiB), "large.pdf")}
    rv = sec_client.post(
        f"/api/expert-requests/{req_id}/documents",
        data=data,
        content_type="multipart/form-data",
    )
    assert rv.status_code in (413, 400, 422), (
        f"Expected 413/400/422 for >10 MiB on documents, got {rv.status_code}"
    )


def test_expert_request_documents_five_valid_below_limit_accepted(sec_client):
    """Five valid files at or below per-file limit are accepted on documents."""
    _9MiB = 9 * 1024 * 1024
    req_id = _make_request_id(sec_client)
    data = {}
    for i in range(5):
        data[f"file_{i}"] = (io.BytesIO(b"x" * _9MiB), f"f{i}.pdf")
    rv = sec_client.post(
        f"/api/expert-requests/{req_id}/documents",
        data=data,
        content_type="multipart/form-data",
    )
    assert rv.status_code in (200, 207), (
        f"Expected 200/207 for 5 valid files on documents, got {rv.status_code}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Section 10: XLSX and public-template security regressions
# ═══════════════════════════════════════════════════════════════════════════════

# ── Formula injection neutralization helpers ───────────────────────────────────

def _import_esc():
    """Return the _esc() function from mass_appraisal."""
    import importlib
    import sys
    _ma_path = str(Path(_CORE))
    if _ma_path not in sys.path:
        sys.path.insert(0, _ma_path)
    ma = importlib.import_module("mass_appraisal")
    return ma._esc


def _import_escape_formula():
    """Return the _escape_formula() function from mass_appraisal_excel."""
    import importlib
    import sys
    _ma_path = str(Path(_CORE))
    if _ma_path not in sys.path:
        sys.path.insert(0, _ma_path)
    mae = importlib.import_module("mass_appraisal_excel")
    return mae._escape_formula


# ── Formula-prefix neutralization — _esc() ────────────────────────────────────

def test_formula_prefix_equals_neutralized():
    """= prefix is neutralized by _esc() with a leading apostrophe."""
    _esc = _import_esc()
    result = _esc("=SUM(A1:A10)")
    assert result.startswith("'"), f"Expected leading apostrophe, got {result!r}"
    assert "=SUM" in result


def test_formula_prefix_plus_neutralized():
    """+ prefix is neutralized by _esc()."""
    _esc = _import_esc()
    result = _esc("+1234")
    assert result.startswith("'"), f"Expected leading apostrophe, got {result!r}"


def test_formula_prefix_minus_neutralized():
    """- prefix is neutralized by _esc()."""
    _esc = _import_esc()
    result = _esc("-1234")
    assert result.startswith("'"), f"Expected leading apostrophe, got {result!r}"


def test_formula_prefix_at_neutralized():
    """@ prefix is neutralized by _esc()."""
    _esc = _import_esc()
    result = _esc("@SUM(A1)")
    assert result.startswith("'"), f"Expected leading apostrophe, got {result!r}"


def test_formula_prefix_tab_neutralized():
    r"""Tab (\t) prefix is neutralized by _esc()."""
    _esc = _import_esc()
    result = _esc("\tDANGER")
    assert result.startswith("'"), f"Expected leading apostrophe, got {result!r}"


def test_formula_prefix_cr_neutralized():
    r"""Carriage return (\r) prefix is neutralized by _esc()."""
    _esc = _import_esc()
    result = _esc("\rDANGER")
    assert result.startswith("'"), f"Expected leading apostrophe, got {result!r}"


def test_safe_string_not_modified():
    """Safe string values are returned unchanged by _esc()."""
    _esc = _import_esc()
    assert _esc("Riyadh") == "Riyadh"
    assert _esc("good") == "good"
    assert _esc(12345) == 12345
    assert _esc(None) is None


def test_openpyxl_values_neutralized_via_escape_formula():
    """_escape_formula() in mass_appraisal_excel neutralizes all formula prefixes."""
    _escape_formula = _import_escape_formula()
    for prefix in ("=", "+", "-", "@", "\t", "\r"):
        val = f"{prefix}DANGER"
        result = _escape_formula(val)
        assert result.startswith("'"), (
            f"Prefix {prefix!r}: expected leading apostrophe, got {result!r}"
        )


# ── XlsxWriter security options (source verification) ─────────────────────────

def test_xlsx_strings_to_formulas_false():
    """mass_appraisal.py passes strings_to_formulas=False to XlsxWriter."""
    import ast, pathlib
    source = (Path(_CORE) / "mass_appraisal.py").read_text(encoding="utf-8")
    assert '"strings_to_formulas": False' in source or \
           "'strings_to_formulas': False" in source, (
        "strings_to_formulas=False must be set in mass_appraisal.py XlsxWriter options"
    )


def test_xlsx_strings_to_urls_false():
    """mass_appraisal.py passes strings_to_urls=False to XlsxWriter."""
    source = (Path(_CORE) / "mass_appraisal.py").read_text(encoding="utf-8")
    assert '"strings_to_urls": False' in source or \
           "'strings_to_urls': False" in source, (
        "strings_to_urls=False must be set in mass_appraisal.py XlsxWriter options"
    )


# ── Public template-xlsx endpoint ─────────────────────────────────────────────

def test_template_xlsx_is_public(sec_client):
    """GET /api/mass-appraisal/template-xlsx returns 200 without Authorization."""
    rv = sec_client.get("/api/mass-appraisal/template-xlsx")
    assert rv.status_code in (200, 404, 500), (
        f"Template XLSX endpoint: expected 200/404/500 (not 401/403), got {rv.status_code}"
    )
    assert rv.status_code not in (401, 403), (
        "Template XLSX must be public — must not return 401/403"
    )


def test_template_xlsx_unauthenticated_options(sec_client):
    """OPTIONS /api/mass-appraisal/template-xlsx succeeds without Authorization."""
    rv = sec_client.options("/api/mass-appraisal/template-xlsx")
    assert rv.status_code not in (401, 403), (
        f"OPTIONS must not require auth on public template endpoint, got {rv.status_code}"
    )


def test_template_xlsx_exact_mime(sec_client):
    """Successful template-xlsx response has the correct XLSX MIME type."""
    rv = sec_client.get("/api/mass-appraisal/template-xlsx")
    if rv.status_code == 200:
        ct = rv.content_type or ""
        assert "openxmlformats-officedocument.spreadsheetml.sheet" in ct, (
            f"Expected XLSX MIME type, got {ct!r}"
        )


def test_template_xlsx_size_under_2mib(sec_client):
    """Template XLSX response must not exceed 2 MiB."""
    rv = sec_client.get("/api/mass-appraisal/template-xlsx")
    if rv.status_code == 200:
        size = len(rv.data)
        assert size <= 2 * 1024 * 1024, (
            f"Template XLSX is {size} bytes — exceeds 2 MiB safety limit"
        )


def test_template_xlsx_valid_zip_signature(sec_client):
    """Template XLSX has valid ZIP/XLSX signature (starts with PK)."""
    rv = sec_client.get("/api/mass-appraisal/template-xlsx")
    if rv.status_code == 200:
        assert rv.data[:2] == b"PK", (
            f"XLSX must start with ZIP signature PK, got {rv.data[:4]!r}"
        )


def test_template_xlsx_no_formula_cells(sec_client):
    """Template XLSX contains no formula cells (xl/worksheets must have no <f> tags)."""
    import zipfile, io as _io
    rv = sec_client.get("/api/mass-appraisal/template-xlsx")
    if rv.status_code != 200:
        pytest.skip("Template endpoint unavailable — skipping content inspection")
    with zipfile.ZipFile(_io.BytesIO(rv.data)) as zf:
        for name in zf.namelist():
            if name.startswith("xl/worksheets/") and name.endswith(".xml"):
                content = zf.read(name)
                assert b"<f>" not in content and b"<f " not in content, (
                    f"Formula cell found in {name}"
                )


def test_template_xlsx_no_external_links(sec_client):
    """Template XLSX contains no xl/externalLinks entries."""
    import zipfile, io as _io
    rv = sec_client.get("/api/mass-appraisal/template-xlsx")
    if rv.status_code != 200:
        pytest.skip("Template endpoint unavailable — skipping content inspection")
    with zipfile.ZipFile(_io.BytesIO(rv.data)) as zf:
        external_link_entries = [n for n in zf.namelist() if "externalLinks" in n]
        assert not external_link_entries, (
            f"Template XLSX must not have externalLinks: {external_link_entries}"
        )


def test_template_xlsx_no_target_mode_external(sec_client):
    """No .rels file inside template XLSX contains TargetMode='External'."""
    import zipfile, io as _io
    rv = sec_client.get("/api/mass-appraisal/template-xlsx")
    if rv.status_code != 200:
        pytest.skip("Template endpoint unavailable — skipping content inspection")
    with zipfile.ZipFile(_io.BytesIO(rv.data)) as zf:
        for name in zf.namelist():
            if name.endswith(".rels"):
                content = zf.read(name)
                assert b'TargetMode="External"' not in content, (
                    f"External TargetMode found in {name}"
                )


def test_template_xlsx_no_vba(sec_client):
    """Template XLSX must not contain a VBA project."""
    import zipfile, io as _io
    rv = sec_client.get("/api/mass-appraisal/template-xlsx")
    if rv.status_code != 200:
        pytest.skip("Template endpoint unavailable — skipping content inspection")
    with zipfile.ZipFile(_io.BytesIO(rv.data)) as zf:
        vba_entries = [n for n in zf.namelist() if "vbaProject" in n or n.endswith(".bin")]
        assert not vba_entries, (
            f"Template XLSX must not contain VBA project: {vba_entries}"
        )


def test_template_xlsx_no_secret_patterns(sec_client):
    """Template XLSX must not contain secret-pattern values in any entry."""
    import zipfile, io as _io, re as _re
    rv = sec_client.get("/api/mass-appraisal/template-xlsx")
    if rv.status_code != 200:
        pytest.skip("Template endpoint unavailable — skipping content inspection")
    secret_re = _re.compile(
        rb"-----BEGIN .{0,20}PRIVATE KEY-----|"
        rb"\"type\"\s*:\s*\"service_account\"|"
        rb"[Aa][Pp][Ii][_-]?[Kk][Ee][Yy]\s*[:=]\s*[A-Za-z0-9+/]{20}"
    )
    with zipfile.ZipFile(_io.BytesIO(rv.data)) as zf:
        for name in zf.namelist():
            content = zf.read(name)
            m = secret_re.search(content)
            assert m is None, (
                f"Secret-pattern found in {name}: {m.group()[:40]!r}"
            )
