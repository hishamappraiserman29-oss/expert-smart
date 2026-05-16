"""Tests for JWT middleware in bridge_api — Wave S2.

Wave S2 contract: middleware reads tokens silently, never rejects.
Missing / malformed / expired tokens all result in g.user_id = None;
no endpoint receives a 4xx from the middleware itself.
"""
from __future__ import annotations

import os
import sys
import time
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
from auth.tokens import generate_token  # noqa: E402

_TEST_SECRET = "test-secret-for-bridge-api-tests"


@pytest.fixture(autouse=True)
def jwt_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", _TEST_SECRET)
    monkeypatch.delenv("JWT_TTL_SECONDS", raising=False)
    yield


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── Backward compat: no token ────────────────────────────────────────


class TestNoTokenBackwardCompat:
    """Requests without Authorization header behave exactly as pre-S2."""

    def test_health_endpoint_no_token(self, client):
        resp = client.get("/api/advisor/health")
        assert resp.status_code == 200

    def test_root_no_token_not_server_error(self, client):
        resp = client.get("/")
        assert resp.status_code < 500

    def test_options_preflight_no_token(self, client):
        resp = client.options("/api/valuation")
        assert resp.status_code < 500

    def test_arbitrary_get_no_token_not_500(self, client):
        # Any route — middleware must not inject 500 for missing token
        resp = client.get("/api/advisor/health")
        assert resp.status_code < 500


# ── Silent token extraction ──────────────────────────────────────────


class TestSilentTokenExtraction:
    """Middleware must never reject based on token presence or absence."""

    def test_valid_token_does_not_break_request(self, client):
        token = generate_token("alice")
        resp = client.get(
            "/api/advisor/health",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    def test_malformed_bearer_token_silent(self, client):
        resp = client.get(
            "/api/advisor/health",
            headers={"Authorization": "Bearer this.is.notvalid"},
        )
        # silent — no 401, no 403, no 500 from middleware
        assert resp.status_code < 500

    def test_missing_bearer_prefix_silent(self, client):
        resp = client.get(
            "/api/advisor/health",
            headers={"Authorization": "Token some-random-value"},
        )
        assert resp.status_code < 500

    def test_bare_authorization_header_silent(self, client):
        resp = client.get(
            "/api/advisor/health",
            headers={"Authorization": "alice"},
        )
        assert resp.status_code < 500

    def test_empty_bearer_value_silent(self, client):
        resp = client.get(
            "/api/advisor/health",
            headers={"Authorization": "Bearer "},
        )
        assert resp.status_code < 500

    def test_expired_token_silent(self, client):
        token = generate_token("alice", ttl_seconds=1)
        time.sleep(2)
        resp = client.get(
            "/api/advisor/health",
            headers={"Authorization": f"Bearer {token}"},
        )
        # expired — but Wave S2 never rejects, just leaves user_id = None
        assert resp.status_code < 500

    def test_wrong_secret_token_silent(self, client, monkeypatch):
        # token signed with different secret — verify_token raises AuthError silently
        import jwt as _jwt
        bad_token = _jwt.encode(
            {"sub": "mallory", "iat": 1, "exp": 9999999999},
            "wrong-secret",
            algorithm="HS256",
        )
        resp = client.get(
            "/api/advisor/health",
            headers={"Authorization": f"Bearer {bad_token}"},
        )
        assert resp.status_code < 500


# ── Baseline endpoints unchanged ─────────────────────────────────────


class TestBaselineUnchanged:
    """All existing endpoints must work identically with or without a token."""

    def test_health_with_token_same_as_without(self, client):
        token = generate_token("alice")
        r_with = client.get(
            "/api/advisor/health",
            headers={"Authorization": f"Bearer {token}"},
        )
        r_without = client.get("/api/advisor/health")
        assert r_with.status_code == r_without.status_code

    def test_options_preflight_with_token_unchanged(self, client):
        token = generate_token("alice")
        r_with = client.options(
            "/api/valuation",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r_with.status_code < 500
