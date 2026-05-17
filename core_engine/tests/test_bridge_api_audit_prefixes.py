"""
SEC-008 tests — _AUDITED_PREFIXES coverage.

The audit after_request hook must fire for all sensitive protected endpoints
and must NOT fire for noisy public reads.
"""
from __future__ import annotations

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

import bridge_api as _bapi   # noqa: E402
from bridge_api import app    # noqa: E402
from auth.tokens import generate_token  # noqa: E402

_ADMIN_USER  = "admin-audit-prefix-test"
_TEST_SECRET = "test-secret-for-audit-prefix-tests"


def _auth(user: str = _ADMIN_USER) -> dict:
    return {"Authorization": f"Bearer {generate_token(user)}"}


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", _TEST_SECRET)
    monkeypatch.setenv("ADMIN_USER_IDS", _ADMIN_USER)
    monkeypatch.delenv("JWT_TTL_SECONDS", raising=False)
    monkeypatch.setenv("AUDIT_ENABLED", "true")


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── _AUDITED_PREFIXES content ─────────────────────────────────────────────────

class TestAuditedPrefixesContent:
    """The prefixes tuple must include all protected path families."""

    def test_reports_prefix_present(self):
        assert "/api/reports" in _bapi._AUDITED_PREFIXES

    def test_admin_prefix_present(self):
        assert "/api/admin" in _bapi._AUDITED_PREFIXES

    def test_download_prefix_present(self):
        assert "/api/download" in _bapi._AUDITED_PREFIXES

    def test_valuation_report_download_prefix_present(self):
        assert "/api/valuation/report/download" in _bapi._AUDITED_PREFIXES

    def test_enterprise_prefix_present(self):
        assert "/api/enterprise" in _bapi._AUDITED_PREFIXES

    def test_saas_prefix_present(self):
        assert "/api/saas" in _bapi._AUDITED_PREFIXES

    def test_market_feed_prefix_present(self):
        assert "/api/market-feed" in _bapi._AUDITED_PREFIXES

    def test_no_wildcard_public_reads(self):
        # Noisy public endpoints must not be in audit prefixes
        assert "/api/valuation" not in _bapi._AUDITED_PREFIXES
        assert "/api/advisor" not in _bapi._AUDITED_PREFIXES


# ── Audit hook fires for audited prefixes ────────────────────────────────────

class TestAuditHookFires:
    """After-request audit hook must call log_access for audited paths."""

    def test_download_endpoint_triggers_audit(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr("bridge_api.OUTPUTS", str(tmp_path))
        with patch("audit_log.log_access") as mock_log:
            client.get("/api/download/report.xlsx", headers=_auth())
        mock_log.assert_called()

    def test_enterprise_endpoint_triggers_audit(self, client):
        with patch("audit_log.log_access") as mock_log:
            client.post("/api/enterprise/tenant", json={}, headers=_auth())
        mock_log.assert_called()

    def test_saas_endpoint_triggers_audit(self, client):
        with patch("audit_log.log_access") as mock_log:
            client.get("/api/saas/tenants", headers=_auth())
        mock_log.assert_called()

    def test_market_feed_triggers_audit(self, client):
        with patch("audit_log.log_access") as mock_log:
            client.post("/api/market-feed", json={}, headers=_auth())
        mock_log.assert_called()


# ── Audit hook silent for public reads ───────────────────────────────────────

class TestAuditHookSilentForPublic:
    """Public, noisy endpoints must NOT trigger audit logging."""

    def test_health_does_not_audit(self, client):
        with patch("audit_log.log_access") as mock_log:
            client.get("/api/advisor/health")
        mock_log.assert_not_called()
