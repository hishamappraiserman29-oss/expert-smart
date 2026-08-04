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
