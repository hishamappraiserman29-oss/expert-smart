"""
Integration tests for the Bridge API PDF export endpoint (Wave BA.4b).

Endpoint under test:
  GET /api/reports/<report_id>/pdf

Behavior:
  - Fetches the stored report DTO from the DB via export_report_pdf().
  - Returns 404 when the report_id is not found.
  - Returns application/pdf bytes when found; Content-Disposition names the file.
  - DB / PDF-engine exceptions → controlled 500 response.
  - No application-level auth gate (infrastructure auth assumed — same policy as
    /api/valuation and the other /api/reports endpoints).
  - No production DB file is created in tests — all calls mock export_report_pdf.

Tests: PX01–PX14
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(str(_CORE))

from bridge_api import app  # noqa: E402

# ── Shared stubs ──────────────────────────────────────────────────────────────

_REPORT_ID  = "ES-20260515-ABCD"
_FAKE_PDF   = b"%PDF-1.4 fake-pdf-content-for-testing"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture()
def auth_header(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-s3-pdf")
    from auth.tokens import generate_token
    return lambda user_id="test-user": {"Authorization": f"Bearer {generate_token(user_id)}"}


# ── PX01–PX03: Successful PDF export ─────────────────────────────────────────

class TestPdfExportSuccess:
    def test_PX01_returns_200(self, client, auth_header):
        with patch("reports.report_pipeline.export_report_pdf",
                   return_value=_FAKE_PDF):
            r = client.get(f"/api/reports/{_REPORT_ID}/pdf", headers=auth_header())
        assert r.status_code == 200

    def test_PX02_mimetype_is_application_pdf(self, client, auth_header):
        with patch("reports.report_pipeline.export_report_pdf",
                   return_value=_FAKE_PDF):
            r = client.get(f"/api/reports/{_REPORT_ID}/pdf", headers=auth_header())
        assert r.mimetype == "application/pdf"

    def test_PX03_response_bytes_start_with_pdf_header(self, client, auth_header):
        with patch("reports.report_pipeline.export_report_pdf",
                   return_value=_FAKE_PDF):
            r = client.get(f"/api/reports/{_REPORT_ID}/pdf", headers=auth_header())
        assert r.data.startswith(b"%PDF")

    def test_PX04_content_disposition_is_attachment(self, client, auth_header):
        with patch("reports.report_pipeline.export_report_pdf",
                   return_value=_FAKE_PDF):
            r = client.get(f"/api/reports/{_REPORT_ID}/pdf", headers=auth_header())
        cd = r.headers.get("Content-Disposition", "")
        assert "attachment" in cd

    def test_PX05_content_disposition_includes_filename(self, client, auth_header):
        with patch("reports.report_pipeline.export_report_pdf",
                   return_value=_FAKE_PDF):
            r = client.get(f"/api/reports/{_REPORT_ID}/pdf", headers=auth_header())
        cd = r.headers.get("Content-Disposition", "")
        assert ".pdf" in cd

    def test_PX06_returned_bytes_match_engine_output(self, client, auth_header):
        with patch("reports.report_pipeline.export_report_pdf",
                   return_value=_FAKE_PDF):
            r = client.get(f"/api/reports/{_REPORT_ID}/pdf", headers=auth_header())
        assert r.data == _FAKE_PDF


# ── PX07–PX09: Not-found behaviour ───────────────────────────────────────────

class TestPdfExportNotFound:
    def test_PX07_missing_report_returns_404(self, client, auth_header):
        with patch("reports.report_pipeline.export_report_pdf",
                   return_value=None):
            r = client.get("/api/reports/NONEXISTENT-ID/pdf", headers=auth_header())
        assert r.status_code == 404

    def test_PX08_missing_report_status_is_not_found(self, client, auth_header):
        with patch("reports.report_pipeline.export_report_pdf",
                   return_value=None):
            data = client.get("/api/reports/NONEXISTENT-ID/pdf", headers=auth_header()).get_json()
        assert data["status"] == "not_found"

    def test_PX09_missing_report_message_contains_id(self, client, auth_header):
        with patch("reports.report_pipeline.export_report_pdf",
                   return_value=None):
            data = client.get("/api/reports/NONEXISTENT-ID/pdf", headers=auth_header()).get_json()
        assert "NONEXISTENT-ID" in data["message"]


# ── PX10–PX11: Exception handling ────────────────────────────────────────────

class TestPdfExportExceptions:
    def test_PX10_db_exception_returns_500(self, client, auth_header):
        with patch("reports.report_pipeline.export_report_pdf",
                   side_effect=RuntimeError("disk full")):
            r = client.get(f"/api/reports/{_REPORT_ID}/pdf", headers=auth_header())
        assert r.status_code == 500

    def test_PX11_db_exception_status_is_error(self, client, auth_header):
        with patch("reports.report_pipeline.export_report_pdf",
                   side_effect=RuntimeError("disk full")):
            data = client.get(f"/api/reports/{_REPORT_ID}/pdf", headers=auth_header()).get_json()
        assert data["status"] == "error"
        assert data["message"]


# ── PX12: professional_template profile ──────────────────────────────────────

class TestPdfExportProfiles:
    def test_PX12_professional_template_returns_200(self, client, auth_header):
        """export_report_pdf handles professional_template profile internally;
        the route is profile-agnostic — it delegates to the pipeline."""
        with patch("reports.report_pipeline.export_report_pdf",
                   return_value=_FAKE_PDF):
            r = client.get(f"/api/reports/{_REPORT_ID}/pdf", headers=auth_header())
        assert r.status_code == 200
        assert r.mimetype == "application/pdf"


# ── PX13–PX14: No production DB file created ─────────────────────────────────

class TestNoProdDB:
    def test_PX13_no_db_created_on_success(self, client, auth_header):
        """Mocking export_report_pdf ensures the real DB is never opened."""
        prod_db = Path(_CORE) / "reports" / "db" / "data" / "reports.db"
        existed_before = prod_db.exists()
        with patch("reports.report_pipeline.export_report_pdf",
                   return_value=_FAKE_PDF):
            client.get(f"/api/reports/{_REPORT_ID}/pdf", headers=auth_header())
        if not existed_before:
            assert not prod_db.exists()

    def test_PX14_no_db_created_on_not_found(self, client, auth_header):
        prod_db = Path(_CORE) / "reports" / "db" / "data" / "reports.db"
        existed_before = prod_db.exists()
        with patch("reports.report_pipeline.export_report_pdf",
                   return_value=None):
            client.get("/api/reports/MISSING/pdf", headers=auth_header())
        if not existed_before:
            assert not prod_db.exists()
