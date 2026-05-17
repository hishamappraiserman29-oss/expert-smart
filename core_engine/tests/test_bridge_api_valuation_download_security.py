"""
SEC-005 security tests for /api/valuation/report/download/<filename>.

Covers: authentication enforcement, path traversal defense (3 layers),
extension allow-list, and valid-file serving.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(str(_CORE))

from bridge_api import app  # noqa: E402
from auth.tokens import generate_token  # noqa: E402

_TEST_SECRET = "test-secret-for-valuation-download-security-tests"


@pytest.fixture(autouse=True)
def jwt_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", _TEST_SECRET)
    monkeypatch.delenv("JWT_TTL_SECONDS", raising=False)


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture()
def auth_headers():
    token = generate_token("test-user")
    return {"Authorization": f"Bearer {token}"}


# ── Authentication enforcement ────────────────────────────────────────────────

class TestValuationDownloadAuth:
    """@require_auth must gate every request before file logic runs."""

    def test_no_token_returns_401(self, client):
        resp = client.get("/api/valuation/report/download/report.xlsx")
        assert resp.status_code == 401

    def test_no_token_uuid_filename_returns_401(self, client):
        resp = client.get(
            "/api/valuation/report/download/550e8400-e29b-41d4-a716-446655440000.xlsx"
        )
        assert resp.status_code == 401

    def test_missing_report_returns_404(self, client, auth_headers, tmp_path, monkeypatch):
        monkeypatch.setattr("bridge_api._REPORT_DIR", str(tmp_path))
        resp = client.get(
            "/api/valuation/report/download/nonexistent.xlsx", headers=auth_headers
        )
        assert resp.status_code == 404

    def test_existing_xlsx_returns_200(self, client, auth_headers, tmp_path, monkeypatch):
        monkeypatch.setattr("bridge_api._REPORT_DIR", str(tmp_path))
        (tmp_path / "testreport.xlsx").write_bytes(b"PK\x03\x04fake xlsx")
        resp = client.get(
            "/api/valuation/report/download/testreport.xlsx", headers=auth_headers
        )
        assert resp.status_code == 200

    def test_existing_xlsm_returns_200(self, client, auth_headers, tmp_path, monkeypatch):
        monkeypatch.setattr("bridge_api._REPORT_DIR", str(tmp_path))
        (tmp_path / "testreport.xlsm").write_bytes(b"PK\x03\x04fake xlsm")
        resp = client.get(
            "/api/valuation/report/download/testreport.xlsm", headers=auth_headers
        )
        assert resp.status_code == 200


# ── Path traversal defense ────────────────────────────────────────────────────

class TestValuationDownloadTraversal:
    """All traversal vectors must be rejected with non-200."""

    def test_backslash_single_segment(self, client, auth_headers):
        # %5C → backslash; Layer 1 rejects "\\" in filename
        resp = client.get(
            "/api/valuation/report/download/..%5Cpasswd", headers=auth_headers
        )
        assert resp.status_code == 400

    def test_backslash_double_segment(self, client, auth_headers):
        resp = client.get(
            "/api/valuation/report/download/..%5C..%5Csecret.xlsx",
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_backslash_escape_to_parent(self, client, auth_headers, tmp_path, monkeypatch):
        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()
        monkeypatch.setattr("bridge_api._REPORT_DIR", str(reports_dir))
        (tmp_path / "secret.xlsx").write_text("sensitive")
        resp = client.get(
            "/api/valuation/report/download/..%5Csecret.xlsx", headers=auth_headers
        )
        assert resp.status_code == 400

    def test_dotdot_alone_blocked(self, client, auth_headers, tmp_path, monkeypatch):
        # ".." passes basename check but Layer 3 realpath containment rejects it
        monkeypatch.setattr("bridge_api._REPORT_DIR", str(tmp_path))
        resp = client.get("/api/valuation/report/download/..", headers=auth_headers)
        assert resp.status_code not in (200,)

    def test_forward_slash_traversal_not_served(self, client, auth_headers):
        # Flask <string> converter rejects "/" — routed to 404/405
        resp = client.get(
            "/api/valuation/report/download/../secret.xlsx", headers=auth_headers
        )
        assert resp.status_code != 200

    def test_url_encoded_forward_slash_not_served(self, client, auth_headers):
        # %2F decoded by Werkzeug before routing — Flask never matches <filename>
        resp = client.get(
            "/api/valuation/report/download/..%2Fsecret.xlsx", headers=auth_headers
        )
        assert resp.status_code != 200


# ── Extension allow-list ──────────────────────────────────────────────────────

class TestValuationDownloadExtension:
    """Only .xlsx and .xlsm are permitted."""

    def test_txt_extension_blocked(self, client, auth_headers):
        resp = client.get(
            "/api/valuation/report/download/report.txt", headers=auth_headers
        )
        assert resp.status_code == 400

    def test_py_extension_blocked(self, client, auth_headers):
        resp = client.get(
            "/api/valuation/report/download/bridge_api.py", headers=auth_headers
        )
        assert resp.status_code == 400

    def test_no_extension_blocked(self, client, auth_headers):
        resp = client.get(
            "/api/valuation/report/download/reportfile", headers=auth_headers
        )
        assert resp.status_code == 400
