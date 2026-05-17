"""
SEC-002a tests — destructive operations + file writes auth hardening.

Covers the 10 endpoints protected in the SEC-002a wave:
  - DELETE /api/tune/profiles/<id>    → @_require_admin
  - POST   /api/tune/apply            → @_require_admin
  - POST   /api/price/cache/clear     → @_require_admin
  - DELETE /api/library/<id>          → @_require_admin
  - POST   /api/integrations/plugins/<id>/install → @_require_admin
  - POST   /api/hardening/api-keys/generate       → @_require_admin
  - POST   /api/hardening/api-keys/validate       → @_require_admin (INTERNAL_ONLY)
  - POST   /api/ingest                → @require_auth
  - POST   /api/upload                → @require_auth
  - DELETE /api/assets/<id>           → @require_auth
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

os.chdir(str(_CORE))

from bridge_api import app  # noqa: E402
from auth.tokens import generate_token  # noqa: E402

_ADMIN_USER = "admin-sec002a-test"
_NON_ADMIN  = "regular-sec002a-user"
_TEST_SECRET = "test-secret-for-sec002a"


def _admin_headers() -> dict:
    return {"Authorization": f"Bearer {generate_token(_ADMIN_USER)}"}


def _user_headers() -> dict:
    return {"Authorization": f"Bearer {generate_token(_NON_ADMIN)}"}


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", _TEST_SECRET)
    monkeypatch.setenv("ADMIN_USER_IDS", _ADMIN_USER)
    monkeypatch.delenv("JWT_TTL_SECONDS", raising=False)


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── DELETE /api/tune/profiles/<id> ───────────────────────────────────────────

class TestTuneProfileDelete:
    def test_no_token_returns_401(self, client):
        resp = client.delete("/api/tune/profiles/some-profile")
        assert resp.status_code == 401

    def test_non_admin_returns_403(self, client):
        resp = client.delete("/api/tune/profiles/some-profile", headers=_user_headers())
        assert resp.status_code == 403

    def test_admin_reaches_handler(self, client):
        resp = client.delete("/api/tune/profiles/nonexistent-profile", headers=_admin_headers())
        assert resp.status_code not in (401, 403)

    def test_options_preflight_allowed(self, client):
        resp = client.options("/api/tune/profiles/some-profile")
        assert resp.status_code == 200


# ── POST /api/tune/apply ─────────────────────────────────────────────────────

class TestTuneApply:
    def test_no_token_returns_401(self, client):
        resp = client.post("/api/tune/apply", json={"prompt": "test"})
        assert resp.status_code == 401

    def test_non_admin_returns_403(self, client):
        resp = client.post("/api/tune/apply", json={"prompt": "test"}, headers=_user_headers())
        assert resp.status_code == 403

    def test_admin_reaches_handler(self, client):
        resp = client.post("/api/tune/apply", json={"prompt": "test", "profile_id": "x"}, headers=_admin_headers())
        assert resp.status_code not in (401, 403)

    def test_options_preflight_allowed(self, client):
        resp = client.options("/api/tune/apply")
        assert resp.status_code == 200


# ── POST /api/price/cache/clear ──────────────────────────────────────────────

class TestPriceCacheClear:
    def test_no_token_returns_401(self, client):
        resp = client.post("/api/price/cache/clear")
        assert resp.status_code == 401

    def test_non_admin_returns_403(self, client):
        resp = client.post("/api/price/cache/clear", headers=_user_headers())
        assert resp.status_code == 403

    def test_admin_reaches_handler(self, client):
        resp = client.post("/api/price/cache/clear", headers=_admin_headers())
        assert resp.status_code not in (401, 403)


# ── DELETE /api/library/<id> ─────────────────────────────────────────────────

class TestLibraryDelete:
    def test_no_token_returns_401(self, client):
        resp = client.delete("/api/library/some-record-id")
        assert resp.status_code == 401

    def test_non_admin_returns_403(self, client):
        resp = client.delete("/api/library/some-record-id", headers=_user_headers())
        assert resp.status_code == 403

    def test_admin_reaches_handler(self, client):
        resp = client.delete("/api/library/nonexistent-id", headers=_admin_headers())
        assert resp.status_code not in (401, 403)


# ── POST /api/ingest ─────────────────────────────────────────────────────────

class TestIngest:
    def test_no_token_returns_401(self, client):
        data = {"file": (io.BytesIO(b"data"), "test.xlsx")}
        resp = client.post("/api/ingest", data=data, content_type="multipart/form-data")
        assert resp.status_code == 401

    def test_non_admin_user_allowed(self, client):
        # @require_auth — any authenticated user is allowed
        data = {"file": (io.BytesIO(b"data"), "test.xlsx")}
        resp = client.post("/api/ingest", data=data,
                           content_type="multipart/form-data",
                           headers=_user_headers())
        assert resp.status_code not in (401, 403)

    def test_options_preflight_allowed(self, client):
        resp = client.options("/api/ingest")
        assert resp.status_code == 200


# ── POST /api/upload ─────────────────────────────────────────────────────────

class TestUpload:
    def test_no_token_returns_401(self, client):
        data = {"file": (io.BytesIO(b"img"), "photo.jpg")}
        resp = client.post("/api/upload", data=data, content_type="multipart/form-data")
        assert resp.status_code == 401

    def test_non_admin_user_allowed(self, client):
        data = {"file": (io.BytesIO(b"img"), "photo.jpg")}
        resp = client.post("/api/upload", data=data,
                           content_type="multipart/form-data",
                           headers=_user_headers())
        assert resp.status_code not in (401, 403)

    def test_options_preflight_allowed(self, client):
        resp = client.options("/api/upload")
        assert resp.status_code == 200


# ── DELETE /api/assets/<id> ──────────────────────────────────────────────────

class TestAssetsDelete:
    def test_no_token_returns_401(self, client):
        resp = client.delete("/api/assets/some-asset-id")
        assert resp.status_code == 401

    def test_non_admin_user_allowed(self, client):
        # @require_auth — any authenticated user
        resp = client.delete("/api/assets/nonexistent-id", headers=_user_headers())
        assert resp.status_code not in (401, 403)


# ── POST /api/integrations/plugins/<id>/install ──────────────────────────────

class TestPluginInstall:
    def test_no_token_returns_401(self, client):
        resp = client.post("/api/integrations/plugins/some-plugin/install", json={})
        assert resp.status_code == 401

    def test_non_admin_returns_403(self, client):
        resp = client.post("/api/integrations/plugins/some-plugin/install",
                           json={}, headers=_user_headers())
        assert resp.status_code == 403

    def test_admin_reaches_handler(self, client):
        resp = client.post("/api/integrations/plugins/some-plugin/install",
                           json={}, headers=_admin_headers())
        assert resp.status_code not in (401, 403)


# ── POST /api/hardening/api-keys/generate ────────────────────────────────────

class TestApiKeyGenerate:
    def test_no_token_returns_401(self, client):
        resp = client.post("/api/hardening/api-keys/generate", json={})
        assert resp.status_code == 401

    def test_non_admin_returns_403(self, client):
        resp = client.post("/api/hardening/api-keys/generate",
                           json={}, headers=_user_headers())
        assert resp.status_code == 403

    def test_admin_reaches_handler(self, client):
        resp = client.post("/api/hardening/api-keys/generate",
                           json={"partner_id": "p1", "partner_name": "P1"},
                           headers=_admin_headers())
        assert resp.status_code not in (401, 403)


# ── POST /api/hardening/api-keys/validate (INTERNAL_ONLY) ────────────────────

class TestApiKeyValidate:
    """INTERNAL_ONLY: restricted to admin — no public or regular-user access."""

    def test_no_token_returns_401(self, client):
        resp = client.post("/api/hardening/api-keys/validate", json={})
        assert resp.status_code == 401

    def test_non_admin_returns_403(self, client):
        resp = client.post("/api/hardening/api-keys/validate",
                           json={}, headers=_user_headers())
        assert resp.status_code == 403

    def test_admin_reaches_handler(self, client):
        # Handler returns its own 401 for an unknown key_id — that is not
        # from the auth decorator (which would return 403 for non-admin).
        # We only assert that the admin JWT was not rejected by the decorator.
        resp = client.post("/api/hardening/api-keys/validate",
                           json={"key_id": "x", "key_secret": "y"},
                           headers=_admin_headers())
        assert resp.status_code != 403
