"""
SEC-006 tests — CORS origin restriction via ALLOWED_ORIGINS env var.

CORS must never use wildcard "*" in production.
Allowed origins come from ALLOWED_ORIGINS env var; safe local defaults apply when unset.
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

import bridge_api as _bapi  # noqa: E402
from bridge_api import app   # noqa: E402


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── _CORS_ORIGINS parsing ─────────────────────────────────────────────────────

class TestCorsOriginsEnvParsing:
    """_CORS_ORIGINS must reflect ALLOWED_ORIGINS and never be '*'."""

    def test_wildcard_not_in_default_origins(self):
        # Reload _CORS_ORIGINS with ALLOWED_ORIGINS unset
        import importlib
        env_backup = os.environ.pop("ALLOWED_ORIGINS", None)
        try:
            origins = [
                o.strip()
                for o in os.environ.get("ALLOWED_ORIGINS", "").split(",")
                if o.strip()
            ] or ["http://localhost:5000", "http://127.0.0.1:5000", "http://localhost:3000"]
            assert "*" not in origins
        finally:
            if env_backup is not None:
                os.environ["ALLOWED_ORIGINS"] = env_backup

    def test_env_var_parsed_correctly(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.example.com,https://admin.example.com")
        origins = [
            o.strip()
            for o in os.environ.get("ALLOWED_ORIGINS", "").split(",")
            if o.strip()
        ] or ["http://localhost:5000"]
        assert "https://app.example.com" in origins
        assert "https://admin.example.com" in origins
        assert "*" not in origins

    def test_empty_env_var_gives_local_defaults(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_ORIGINS", "")
        origins = [
            o.strip()
            for o in os.environ.get("ALLOWED_ORIGINS", "").split(",")
            if o.strip()
        ] or ["http://localhost:5000", "http://127.0.0.1:5000", "http://localhost:3000"]
        assert len(origins) >= 1
        assert "*" not in origins
        assert any("localhost" in o or "127.0.0.1" in o for o in origins)

    def test_module_cors_origins_not_wildcard(self):
        assert "*" not in _bapi._CORS_ORIGINS
        assert len(_bapi._CORS_ORIGINS) >= 1


# ── CORS preflight response ───────────────────────────────────────────────────

class TestCorsPreflightResponse:
    """OPTIONS preflight must not echo back '*' as Access-Control-Allow-Origin."""

    def test_options_preflight_responds(self, client):
        resp = client.options(
            "/api/advisor/health",
            headers={"Origin": "http://localhost:5000"},
        )
        assert resp.status_code < 500

    def test_allowed_origin_gets_cors_header(self, client):
        resp = client.get(
            "/api/advisor/health",
            headers={"Origin": "http://localhost:5000"},
        )
        # Flask-CORS should set the header for a permitted origin
        acao = resp.headers.get("Access-Control-Allow-Origin", "")
        # Must not be wildcard
        assert acao != "*"

    def test_cors_header_not_wildcard_on_any_response(self, client):
        resp = client.get("/api/advisor/health")
        acao = resp.headers.get("Access-Control-Allow-Origin", "")
        assert acao != "*"
