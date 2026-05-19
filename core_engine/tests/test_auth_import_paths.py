"""
SEC-011 regression tests: auth module import path correctness.

Verifies that auth.tokens is importable from inside core_engine/ (the
same path bridge_api.py uses at startup) and that _AUTH_AVAILABLE is
True after the relative-import fix in auth/__init__.py.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parents[1]   # .../core_engine
_ROOT = _CORE.parent                            # repo root


def _ensure_paths():
    for p in (str(_CORE), str(_ROOT)):
        if p not in sys.path:
            sys.path.insert(0, p)


# ── IP01–IP02: import path correctness ───────────────────────────────────────

class TestAuthImportFromCoreEngine:
    """auth.tokens must be importable with core_engine/ on sys.path."""

    def test_IP01_auth_tokens_importable_core_on_path(self):
        """Simulate bridge_api.py startup: core_engine/ is sys.path[0]."""
        _ensure_paths()
        from auth.tokens import AuthError, generate_token, verify_token
        assert callable(generate_token)
        assert callable(verify_token)
        assert issubclass(AuthError, Exception)

    def test_IP02_auth_package_init_does_not_raise(self):
        """auth/__init__.py must not raise ModuleNotFoundError."""
        _ensure_paths()
        import auth
        assert hasattr(auth, "AuthError")
        assert hasattr(auth, "generate_token")
        assert hasattr(auth, "verify_token")


# ── IP03: _AUTH_AVAILABLE flag ────────────────────────────────────────────────

class TestAuthAvailableFlag:
    """bridge_api._AUTH_AVAILABLE must be True (SEC-011 regression guard)."""

    def test_IP03_auth_available_is_true(self):
        _ensure_paths()
        os.chdir(str(_CORE))
        import bridge_api
        assert bridge_api._AUTH_AVAILABLE is True, (
            "_AUTH_AVAILABLE is False — SEC-011 fix not applied or auth import failed"
        )


# ── IP04–IP07: endpoint auth behaviour ───────────────────────────────────────

@pytest.fixture(autouse=True)
def jwt_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-sec011-paths")
    monkeypatch.delenv("JWT_TTL_SECONDS", raising=False)


@pytest.fixture()
def client():
    _ensure_paths()
    os.chdir(str(_CORE))
    from bridge_api import app
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_IP04_valid_token_accepted(client):
    """Valid JWT must NOT return 401 on a protected endpoint."""
    from auth.tokens import generate_token
    token = generate_token("sec011-user")
    resp = client.get("/api/reports", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code != 401, (
        f"Valid token returned 401 — _AUTH_AVAILABLE may still be False. "
        f"Response: {resp.get_json()}"
    )


def test_IP05_missing_token_returns_401(client):
    resp = client.get("/api/reports")
    assert resp.status_code == 401


def test_IP06_invalid_token_returns_401(client):
    resp = client.get(
        "/api/reports",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert resp.status_code == 401


def test_IP07_middleware_sets_user_id_for_valid_token(client):
    """Middleware must populate g.user_id so owner isolation works."""
    from auth.tokens import generate_token
    from flask import g
    token = generate_token("owner-007")
    with client.application.test_request_context(
        "/api/reports",
        headers={"Authorization": f"Bearer {token}"},
    ):
        from bridge_api import _attach_user_from_token
        _attach_user_from_token()
        assert g.user_id == "owner-007"
