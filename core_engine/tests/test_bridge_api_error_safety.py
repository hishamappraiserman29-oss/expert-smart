"""
SEC-004 tests — safe error responses in bridge_api.py.

All internal 500 errors must return a generic message and must NOT
leak exception text, file paths, tracebacks, or module names.
Tests use monkeypatch to force an exception inside a live handler.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(str(_CORE))

from bridge_api import app, _safe_err  # noqa: E402
from auth.tokens import generate_token  # noqa: E402

_TEST_SECRET = "test-secret-for-error-safety-tests"
_ADMIN_USER  = "admin-error-test"


def _auth(user: str = "test-user") -> dict:
    return {"Authorization": f"Bearer {generate_token(user)}"}


def _admin_auth() -> dict:
    return _auth(_ADMIN_USER)


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


# ── _safe_err unit tests ──────────────────────────────────────────────────────

class TestSafeErrHelper:
    """Direct unit tests for the _safe_err helper."""

    def test_returns_500_status(self):
        with app.app_context():
            _, status = _safe_err(RuntimeError("boom"))
        assert status == 500

    def test_body_has_generic_message(self):
        with app.app_context():
            resp, _ = _safe_err(RuntimeError("secret internal detail"))
        body = json.loads(resp.get_data(as_text=True))
        assert body["message"] == "Internal server error"
        assert "secret internal detail" not in body["message"]

    def test_body_has_status_error(self):
        with app.app_context():
            resp, _ = _safe_err(ValueError("some value error"))
        body = json.loads(resp.get_data(as_text=True))
        assert body["status"] == "error"

    def test_body_has_code(self):
        with app.app_context():
            resp, _ = _safe_err(Exception("x"))
        body = json.loads(resp.get_data(as_text=True))
        assert body["code"] == "internal_error"

    def test_exception_text_not_in_response(self):
        secret_path = r"C:\Users\admin\secret_config.py"
        with app.app_context():
            resp, _ = _safe_err(FileNotFoundError(secret_path))
        body = json.loads(resp.get_data(as_text=True))
        assert secret_path not in str(body)
        assert "Users" not in str(body)

    def test_sql_text_not_in_response(self):
        sql_exc = Exception("SELECT * FROM users WHERE id='1' OR '1'='1'")
        with app.app_context():
            resp, _ = _safe_err(sql_exc)
        body = json.loads(resp.get_data(as_text=True))
        assert "SELECT" not in str(body)
        assert "FROM users" not in str(body)


# ── Integration: handler forced to raise returns safe response ────────────────

class TestHandlerForcedInternalError:
    """Force an internal error in live handlers and assert safe response."""

    def test_market_data_endpoint_hides_exception(self, client):
        # Regardless of how the pipeline handles an internal error,
        # the sensitive exception message must never reach the response body.
        with patch("bridge_api.get_search_engine",
                   side_effect=RuntimeError("DB path: /var/db/secret.db")):
            resp = client.post(
                "/api/valuation",
                json={
                    "location": "Cairo",
                    "area": 100,
                    "property_type": "apartment",
                    "price_per_meter": 10000,
                },
            )
        # Pipeline may return 200 (fallback) or 4xx/5xx — either is acceptable.
        # What is NOT acceptable: leaking the internal exception string.
        body = resp.get_json() or {}
        assert "/var/db/secret.db" not in str(body)
        assert "DB path" not in str(body)

    def test_500_response_body_has_no_traceback(self, client):
        """A forced 500 body must not contain traceback markers."""
        with patch("bridge_api.get_search_engine",
                   side_effect=Exception("Traceback (most recent call last)")):
            resp = client.post(
                "/api/valuation",
                json={"location": "x", "area": 1, "property_type": "y", "price_per_meter": 1},
            )
        body_str = str(resp.get_json() or {})
        assert "Traceback" not in body_str
        assert "most recent call last" not in body_str

    def test_safe_err_response_shape(self, client):
        """When _safe_err is triggered, response shape is canonical."""
        with patch("bridge_api.get_search_engine",
                   side_effect=RuntimeError("internal failure")):
            resp = client.post(
                "/api/valuation",
                json={"location": "x", "area": 1, "property_type": "y", "price_per_meter": 1},
            )
        if resp.status_code == 500:
            body = resp.get_json()
            assert body["status"] == "error"
            assert body["message"] == "Internal server error"
            assert body["code"] == "internal_error"
            assert "internal failure" not in str(body)

    def test_no_module_path_in_500(self, client):
        """Exception with module path must not reach response body."""
        with patch("bridge_api.get_search_engine",
                   side_effect=ImportError("No module named 'core_engine.secret'")):
            resp = client.post(
                "/api/valuation",
                json={"location": "x", "area": 1, "property_type": "y", "price_per_meter": 1},
            )
        body_str = str(resp.get_json() or {})
        assert "core_engine.secret" not in body_str
        assert "No module named" not in body_str


# ── No leaks on existing public endpoints ─────────────────────────────────────

class TestPublicEndpointsNoLeak:
    """Public endpoints must not expose exception text on bad input."""

    def test_health_never_leaks(self, client):
        resp = client.get("/api/advisor/health")
        assert resp.status_code == 200
        body_str = str(resp.get_json())
        assert "Traceback" not in body_str
        assert "Exception" not in body_str

    def test_valuation_bad_input_no_traceback(self, client):
        resp = client.post("/api/valuation", json={})
        body_str = str(resp.get_json() or {})
        assert "Traceback" not in body_str
        assert "traceback" not in body_str.lower()

    def test_download_missing_file_no_exception_text(self, client, tmp_path, monkeypatch):
        monkeypatch.setenv("JWT_SECRET", _TEST_SECRET)
        monkeypatch.setattr("bridge_api.OUTPUTS", str(tmp_path))
        resp = client.get(
            "/api/download/missing.xlsx",
            headers=_auth(),
        )
        body_str = str(resp.get_json() or {})
        assert "Traceback" not in body_str
        assert "FileNotFoundError" not in body_str


# ── Regression: previous security fixes still pass ───────────────────────────

class TestSecurityRegressions:
    """SEC-001, SEC-003 core assertions must remain intact."""

    def test_sec001_no_token_still_401(self, client):
        resp = client.get("/api/download/report.xlsx")
        assert resp.status_code == 401

    def test_sec003_enterprise_no_token_still_401(self, client):
        resp = client.post("/api/enterprise/tenant", json={})
        assert resp.status_code == 401

    def test_sec003_saas_no_token_still_401(self, client):
        resp = client.post("/api/saas/tenants", json={})
        assert resp.status_code == 401

    def test_sec003_non_admin_still_403(self, client):
        resp = client.post(
            "/api/enterprise/tenant",
            json={},
            headers=_auth("non-admin-user"),
        )
        assert resp.status_code == 403
