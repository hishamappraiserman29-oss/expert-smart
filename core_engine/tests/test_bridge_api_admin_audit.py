"""Integration tests for GET /api/admin/audit (Followup S5.1).

Uses AUDIT_DB_PATH env var (same pattern as test_bridge_api_audit.py) to
isolate the audit DB in tmp_path so production data is never touched.
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
from audit_log import log_access  # noqa: E402


# ── Helpers ───────────────────────────────────────────────────────────────────

def _auth(user: str) -> dict:
    from auth.tokens import generate_token
    return {"Authorization": f"Bearer {generate_token(user)}"}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def env(monkeypatch, tmp_path):
    """Set env vars for an isolated admin-audit test run."""
    db = tmp_path / "admin_audit_test.db"
    monkeypatch.setenv("JWT_SECRET", "test-secret-admin-s51")
    monkeypatch.setenv("ADMIN_USER_IDS", "alice,operations")
    # Override conftest autouse AUDIT_ENABLED=false
    monkeypatch.setenv("AUDIT_ENABLED", "true")
    monkeypatch.setenv("AUDIT_DB_PATH", str(db))
    return db


@pytest.fixture()
def client(env):
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── AA01–AA04: Auth / access control ─────────────────────────────────────────

class TestAdminAuditAccess:
    def test_AA01_no_token_returns_401(self, client):
        resp = client.get("/api/admin/audit")
        assert resp.status_code == 401
        assert resp.get_json()["status"] == "unauthorized"

    def test_AA02_non_admin_returns_403(self, client):
        resp = client.get("/api/admin/audit", headers=_auth("bob"))
        assert resp.status_code == 403
        assert resp.get_json()["status"] == "forbidden"

    def test_AA03_admin_returns_200(self, client):
        resp = client.get("/api/admin/audit", headers=_auth("alice"))
        assert resp.status_code == 200
        body = resp.get_json()
        assert "count" in body
        assert "records" in body
        assert "filters" in body

    def test_AA04_operations_admin_returns_200(self, client):
        resp = client.get("/api/admin/audit", headers=_auth("operations"))
        assert resp.status_code == 200


# ── AA05–AA08: Data retrieval ─────────────────────────────────────────────────

class TestAdminAuditData:
    def test_AA05_records_returned(self, client, env):
        log_access(user_id="bob", endpoint="/api/reports",
                   method="GET", status=200, db_path=env)
        resp = client.get("/api/admin/audit", headers=_auth("alice"))
        body = resp.get_json()
        assert body["count"] >= 1
        assert any(r["user_id"] == "bob" for r in body["records"])

    def test_AA06_filter_by_user_id(self, client, env):
        log_access(user_id="bob", endpoint="/x",
                   method="GET", status=200, db_path=env)
        log_access(user_id="carol", endpoint="/y",
                   method="GET", status=200, db_path=env)
        resp = client.get("/api/admin/audit?user_id=bob",
                          headers=_auth("alice"))
        body = resp.get_json()
        assert body["count"] >= 1
        for r in body["records"]:
            assert r["user_id"] == "bob"

    def test_AA07_pagination_limit(self, client, env):
        for i in range(15):
            log_access(user_id=f"u{i}", endpoint="/x",
                       method="GET", status=200, db_path=env)
        resp = client.get("/api/admin/audit?limit=5&offset=0",
                          headers=_auth("alice"))
        body = resp.get_json()
        assert len(body["records"]) == 5

    def test_AA08_limit_capped_at_500(self, client):
        resp = client.get("/api/admin/audit?limit=999999",
                          headers=_auth("alice"))
        body = resp.get_json()
        assert body["filters"]["limit"] == 500


# ── AA09–AA11: Error handling ─────────────────────────────────────────────────

class TestAdminAuditErrors:
    def test_AA09_invalid_limit_returns_400(self, client):
        resp = client.get("/api/admin/audit?limit=abc",
                          headers=_auth("alice"))
        assert resp.status_code == 400
        assert resp.get_json()["status"] == "bad_request"

    def test_AA10_invalid_offset_returns_400(self, client):
        resp = client.get("/api/admin/audit?offset=xyz",
                          headers=_auth("alice"))
        assert resp.status_code == 400

    def test_AA11_unset_admin_env_locks_everyone_out(self, client, monkeypatch):
        monkeypatch.delenv("ADMIN_USER_IDS", raising=False)
        resp = client.get("/api/admin/audit", headers=_auth("alice"))
        assert resp.status_code == 403


# ── AA12: Meta-audit ──────────────────────────────────────────────────────────

class TestAdminAuditMetaAudit:
    def test_AA12_admin_access_is_itself_audited(self, client, env):
        """Accessing /api/admin/audit must be logged (meta-audit)."""
        # First access — this gets written to the DB by the after_request hook
        client.get("/api/admin/audit", headers=_auth("alice"))
        # Second access — reads the log, which includes the first access
        resp = client.get("/api/admin/audit", headers=_auth("alice"))
        body = resp.get_json()
        assert any(
            r["endpoint"] == "/api/admin/audit" and r["user_id"] == "alice"
            for r in body["records"]
        )
