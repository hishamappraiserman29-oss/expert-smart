"""
SEC-001 security tests for /api/download/<filename>.

Covers: authentication enforcement, path traversal (3 layers), and
valid-file serving. All traversal vectors must return non-200.
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

_TEST_SECRET = "test-secret-for-download-security-tests"


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

class TestDownloadAuth:
    """@require_auth must gate every request before any file logic runs."""

    def test_no_token_returns_401(self, client):
        resp = client.get("/api/download/report.xlsx")
        assert resp.status_code == 401

    def test_missing_file_returns_404(self, client, auth_headers, tmp_path, monkeypatch):
        monkeypatch.setattr("bridge_api.OUTPUTS", str(tmp_path))
        resp = client.get("/api/download/nonexistent.xlsx", headers=auth_headers)
        assert resp.status_code == 404

    def test_existing_file_returns_200(self, client, auth_headers, tmp_path, monkeypatch):
        monkeypatch.setattr("bridge_api.OUTPUTS", str(tmp_path))
        (tmp_path / "report.xlsx").write_bytes(b"PK\x03\x04fake xlsx")
        resp = client.get("/api/download/report.xlsx", headers=auth_headers)
        assert resp.status_code == 200


# ── Path traversal defense ────────────────────────────────────────────────────

class TestDownloadTraversal:
    """All traversal vectors must be rejected with non-200."""

    def test_backslash_single_segment(self, client, auth_headers):
        # %5C → backslash; Layer 1 rejects "\\" in filename
        resp = client.get("/api/download/..%5Cpasswd", headers=auth_headers)
        assert resp.status_code == 400

    def test_backslash_double_segment(self, client, auth_headers):
        # Double-hop backslash traversal; Layer 1 rejects
        resp = client.get("/api/download/..%5C..%5Csecret", headers=auth_headers)
        assert resp.status_code == 400

    def test_backslash_to_parent_file(self, client, auth_headers, tmp_path, monkeypatch):
        # Backslash escape targeting a file placed outside OUTPUTS
        monkeypatch.setattr("bridge_api.OUTPUTS", str(tmp_path / "outputs"))
        (tmp_path / "outputs").mkdir()
        secret = tmp_path / "secret.txt"
        secret.write_text("secret")
        resp = client.get("/api/download/..%5Csecret.txt", headers=auth_headers)
        assert resp.status_code == 400

    def test_dotdot_alone_blocked(self, client, auth_headers, tmp_path, monkeypatch):
        # ".." passes basename check but Layer 3 realpath containment rejects it
        monkeypatch.setattr("bridge_api.OUTPUTS", str(tmp_path))
        resp = client.get("/api/download/..", headers=auth_headers)
        assert resp.status_code not in (200,)

    def test_forward_slash_traversal_not_served(self, client, auth_headers):
        # Flask <string> converter rejects "/" in segment — routed to 404/405
        resp = client.get("/api/download/../secret", headers=auth_headers)
        assert resp.status_code != 200

    def test_url_encoded_forward_slash_not_served(self, client, auth_headers):
        # Werkzeug decodes %2F before routing, so Flask never matches <filename>
        resp = client.get("/api/download/..%2Fsecret", headers=auth_headers)
        assert resp.status_code != 200

    def test_absolute_path_windows_drive(self, client, auth_headers):
        # Windows absolute path "C:" — basename strips to "C:" but realpath rejects
        resp = client.get("/api/download/C%3Asecret.txt", headers=auth_headers)
        # Either 400 (realpath escape) or 404 (file doesn't exist at OUTPUTS/C:secret.txt)
        assert resp.status_code in (400, 404)
