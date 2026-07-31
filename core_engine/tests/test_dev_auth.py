"""
Tests for GET /api/dev/auth-token  —  dev_auth.py  (DEV ONLY bootstrap).

DA01  EXPERT_SMART_DEV_AUTH unset           → 404
DA02  EXPERT_SMART_DEV_AUTH=0               → 404
DA03  FLASK_ENV=production + flag set        → 404
DA04  flag=1 + localhost Host               → 200, full JSON shape present
DA05  non-localhost Host                    → 403
DA06  ?user_id=reviewer                     → user_id echoed in response
DA06b no ?user_id                           → default "local-admin"
DA07  returned token passes verify_token()  → unit-level roundtrip
DA08  returned token passes /api/auth/verify → 200
DA09  returned token on protected endpoint  → not 401

All tests use Flask test client + monkeypatch; no live server required.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# ── sys.path ──────────────────────────────────────────────────────────────────
_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
_ORIG_CWD = os.getcwd()
try:
    os.chdir(str(_CORE))

    from bridge_api import app          # noqa: E402
    from auth.tokens import verify_token  # noqa: E402
finally:
    os.chdir(_ORIG_CWD)

_SECRET = "test-dev-auth-secret-unit-tests-only"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Known-good JWT_SECRET; dev flag and FLASK_ENV cleared before every test."""
    monkeypatch.setenv("JWT_SECRET", _SECRET)
    monkeypatch.delenv("EXPERT_SMART_DEV_AUTH", raising=False)
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.delenv("ADMIN_USER_IDS", raising=False)


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture()
def dev_client(monkeypatch, client):
    """Test client with EXPERT_SMART_DEV_AUTH=1; localhost Host is passed per-call."""
    monkeypatch.setenv("EXPERT_SMART_DEV_AUTH", "1")
    return client


# ── DA01–DA03: disabled / production ─────────────────────────────────────────

class TestDisabledByDefault:
    def test_DA01_unset_returns_404(self, client):
        r = client.get("/api/dev/auth-token",
                       headers={"Host": "127.0.0.1:5000"})
        assert r.status_code == 404

    def test_DA02_flag_zero_returns_404(self, monkeypatch, client):
        monkeypatch.setenv("EXPERT_SMART_DEV_AUTH", "0")
        r = client.get("/api/dev/auth-token",
                       headers={"Host": "127.0.0.1:5000"})
        assert r.status_code == 404

    def test_DA03_production_env_returns_404(self, monkeypatch, client):
        monkeypatch.setenv("EXPERT_SMART_DEV_AUTH", "1")
        monkeypatch.setenv("FLASK_ENV", "production")
        r = client.get("/api/dev/auth-token",
                       headers={"Host": "127.0.0.1:5000"})
        assert r.status_code == 404


# ── DA04: happy path ──────────────────────────────────────────────────────────

class TestHappyPath:
    def test_DA04_enabled_localhost_returns_200_with_full_shape(self, dev_client):
        r = dev_client.get("/api/dev/auth-token",
                           headers={"Host": "127.0.0.1:5000"})
        assert r.status_code == 200
        data = r.get_json()
        assert data["status"] == "ok"
        assert "user_id" in data
        assert "token" in data
        assert isinstance(data["token"], str)
        # JWT has three dot-separated segments
        assert data["token"].count(".") == 2
        assert "localStorageSnippet" in data
        snippet = data["localStorageSnippet"]
        assert "es_auth" in snippet
        assert "location.reload()" in snippet
        assert data["token"] in snippet


# ── DA05: non-localhost rejected ──────────────────────────────────────────────

class TestLocalOnlyGuard:
    def test_DA05_non_localhost_returns_403(self, dev_client):
        r = dev_client.get("/api/dev/auth-token",
                           headers={"Host": "example.com"})
        assert r.status_code == 403
        data = r.get_json()
        assert data["status"] == "forbidden"
        assert "localhost" in data["reason"].lower()

    def test_DA05b_localhost_hostname_accepted(self, dev_client):
        r = dev_client.get("/api/dev/auth-token",
                           headers={"Host": "localhost:5000"})
        assert r.status_code == 200


# ── DA06: user_id param ───────────────────────────────────────────────────────

class TestUserIdParam:
    def test_DA06_custom_user_id_echoed(self, dev_client):
        r = dev_client.get("/api/dev/auth-token?user_id=reviewer",
                           headers={"Host": "127.0.0.1:5000"})
        assert r.status_code == 200
        data = r.get_json()
        assert data["user_id"] == "reviewer"
        assert "reviewer" in data["localStorageSnippet"]

    def test_DA06b_default_user_id_is_local_admin(self, dev_client):
        r = dev_client.get("/api/dev/auth-token",
                           headers={"Host": "127.0.0.1:5000"})
        assert r.status_code == 200
        assert r.get_json()["user_id"] == "local-admin"


# ── DA07: token unit roundtrip ────────────────────────────────────────────────

class TestTokenRoundtrip:
    def test_DA07_token_verifies_with_verify_token(self, dev_client):
        r = dev_client.get("/api/dev/auth-token",
                           headers={"Host": "127.0.0.1:5000"})
        assert r.status_code == 200
        token = r.get_json()["token"]

        payload = verify_token(token)
        assert payload["sub"] == "local-admin"
        assert "exp" in payload
        assert "iat" in payload
        assert payload["exp"] > payload["iat"]
        # 7-day TTL ±10 s tolerance
        assert abs((payload["exp"] - payload["iat"]) - 604_800) < 10


# ── DA08: token on /api/auth/verify ──────────────────────────────────────────

class TestTokenOnAuthVerify:
    def test_DA08_token_passes_auth_verify_endpoint(self, dev_client):
        # Obtain token
        r1 = dev_client.get("/api/dev/auth-token",
                             headers={"Host": "127.0.0.1:5000"})
        assert r1.status_code == 200
        token = r1.get_json()["token"]

        # Verify via the server's own /api/auth/verify
        r2 = dev_client.get("/api/auth/verify",
                             headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 200
        data2 = r2.get_json()
        assert data2["status"] == "ok"
        assert data2["user_id"] == "local-admin"


# ── DA09: token on protected endpoint ────────────────────────────────────────

class TestTokenOnProtectedEndpoint:
    def test_DA09_token_on_require_auth_endpoint_not_401(self, dev_client):
        # Obtain token
        r1 = dev_client.get("/api/dev/auth-token",
                             headers={"Host": "127.0.0.1:5000"})
        assert r1.status_code == 200
        token = r1.get_json()["token"]

        # Use it on a @require_auth endpoint (/api/reports — GET, no body needed)
        r2 = dev_client.get("/api/reports",
                             headers={"Authorization": f"Bearer {token}"})
        # A valid token must NOT produce 401 — exact status depends on DB state
        assert r2.status_code != 401
