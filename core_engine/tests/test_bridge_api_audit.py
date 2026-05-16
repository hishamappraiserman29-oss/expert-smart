"""Integration tests for the after_request audit hook (Auth Wave S5).

The hook runs on every /api/reports* request and writes to report_access_log.
Tests use AUDIT_DB_PATH env var to point the hook at a tmp_path DB so
production data is never touched.

Tests: AH01–AH08
"""
from __future__ import annotations

import sys
import os
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
from audit_log import fetch_audit_logs  # noqa: E402


# ── Helpers ───────────────────────────────────────────────────────────────────

def _auth(user: str = "alice") -> dict:
    from auth.tokens import generate_token
    return {"Authorization": f"Bearer {generate_token(user)}"}


_EMPTY_LIST = {"count": 0, "reports": []}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def audit_client(monkeypatch, tmp_path):
    """Flask test client with audit enabled, writing to an isolated tmp DB."""
    db_path = tmp_path / "audit_integration.db"
    # Override conftest.py autouse defaults
    monkeypatch.setenv("AUDIT_ENABLED", "true")
    monkeypatch.setenv("AUDIT_DB_PATH", str(db_path))
    monkeypatch.setenv("JWT_SECRET", "test-secret-s5-audit")
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c, db_path


# ── AH01–AH05: Audit hook writes ─────────────────────────────────────────────

class TestAuditHook:
    def test_AH01_authenticated_request_logged(self, audit_client):
        """Successful authenticated request → row in audit log."""
        c, db = audit_client
        with patch("reports.report_pipeline.fetch_reports",
                   return_value=_EMPTY_LIST):
            c.get("/api/reports", headers=_auth())
        rows = fetch_audit_logs(db_path=db)
        assert len(rows) >= 1
        assert any(r["endpoint"] == "/api/reports" for r in rows)

    def test_AH02_401_logged(self, audit_client):
        """Unauthenticated request (→ 401) is logged."""
        c, db = audit_client
        c.get("/api/reports")  # no token
        rows = fetch_audit_logs(db_path=db)
        assert any(r["status"] == 401 for r in rows)

    def test_AH03_user_id_recorded(self, audit_client):
        """Authenticated user's ID is captured in the log."""
        c, db = audit_client
        with patch("reports.report_pipeline.fetch_reports",
                   return_value=_EMPTY_LIST):
            c.get("/api/reports", headers=_auth("alice"))
        rows = fetch_audit_logs(db_path=db)
        assert any(r["user_id"] == "alice" for r in rows)

    def test_AH04_anonymous_recorded_as_null(self, audit_client):
        """Unauthenticated request logs user_id=NULL."""
        c, db = audit_client
        c.get("/api/reports")  # 401, no token
        rows = fetch_audit_logs(db_path=db)
        assert any(r["user_id"] is None for r in rows)

    def test_AH05_report_id_extracted_from_path(self, audit_client):
        """report_id is extracted from the URL path param."""
        c, db = audit_client
        with patch("reports.report_pipeline.fetch_report", return_value=None):
            c.get("/api/reports/r-xyz-123", headers=_auth())
        rows = fetch_audit_logs(db_path=db)
        assert any(r["report_id"] == "r-xyz-123" for r in rows)


# ── AH06: Unprotected endpoints not logged ────────────────────────────────────

class TestAuditUnprotected:
    def test_AH06_valuation_not_logged(self, audit_client):
        """POST /api/valuation is not in _AUDITED_PREFIXES — no audit row."""
        c, db = audit_client
        c.post("/api/valuation", json={
            "location": "القاهرة", "area": 100,
            "property_type": "شقة سكنية", "price_per_meter": 10_000,
        })
        rows = fetch_audit_logs(db_path=db)
        assert not any(r["endpoint"].startswith("/api/valuation") for r in rows)


# ── AH07–AH08: Disabled mode ──────────────────────────────────────────────────

class TestAuditDisabled:
    def test_AH07_no_rows_when_disabled(self, monkeypatch, tmp_path):
        """AUDIT_ENABLED=false (conftest default) → zero rows written."""
        # conftest.py autouse already sets AUDIT_ENABLED=false
        db_path = tmp_path / "audit_disabled.db"
        monkeypatch.setenv("AUDIT_DB_PATH", str(db_path))
        monkeypatch.setenv("JWT_SECRET", "test-secret-s5-audit")
        with app.test_client() as c:
            c.get("/api/reports")  # would log if enabled
        rows = fetch_audit_logs(db_path=db_path)
        assert rows == []

    def test_AH08_hook_never_raises_on_bad_db(self, monkeypatch):
        """Even if the DB path is invalid, the response must not fail."""
        monkeypatch.setenv("AUDIT_ENABLED", "true")
        monkeypatch.setenv("AUDIT_DB_PATH", "/nonexistent/dir/audit.db")
        monkeypatch.setenv("JWT_SECRET", "test-secret-s5-audit")
        with app.test_client() as c:
            resp = c.get("/api/reports")
        # Response must be some valid HTTP status (not an unhandled exception)
        assert resp.status_code in (200, 401, 404, 429, 500)
