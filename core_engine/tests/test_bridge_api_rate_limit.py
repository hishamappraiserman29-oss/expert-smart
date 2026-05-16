"""
Tests for per-user rate limiting on protected endpoints (Auth Wave S4).

Design:
  - conftest.py autouse sets RATE_LIMIT_ENABLED=false for all tests.
  - `rate_limited_client` fixture overrides to true + resets counters.
  - Pipeline is mocked so business logic never touches the DB.

Tests: RL01–RL12
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


# ── Helpers ───────────────────────────────────────────────────────────────────

_EMPTY_LIST = {"count": 0, "reports": []}
_FAKE_PDF   = b"%PDF-1.4 fake"


def _auth(user_id: str = "alice") -> dict:
    from auth.tokens import generate_token
    return {"Authorization": f"Bearer {generate_token(user_id)}"}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def rate_limited_client(monkeypatch):
    """Flask test client with rate limiting enabled + counters reset."""
    # Override the autouse _disable_rate_limit from conftest.py
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("JWT_SECRET", "test-secret-s4-rate-limit")
    from bridge_api import app, limiter
    limiter.reset()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── RL01–RL03: GET /api/reports — 30/min ─────────────────────────────────────

class TestRateLimitListReports:
    def test_RL01_under_limit_passes(self, rate_limited_client):
        """5 requests within 30/min limit — none should be 429."""
        with patch("reports.report_pipeline.fetch_reports",
                   return_value=_EMPTY_LIST):
            for _ in range(5):
                resp = rate_limited_client.get("/api/reports", headers=_auth())
                assert resp.status_code != 429

    def test_RL02_exceeding_limit_returns_429(self, rate_limited_client):
        """31st request past 30/min limit → 429."""
        with patch("reports.report_pipeline.fetch_reports",
                   return_value=_EMPTY_LIST):
            for _ in range(30):
                rate_limited_client.get("/api/reports", headers=_auth())
            resp = rate_limited_client.get("/api/reports", headers=_auth())
        assert resp.status_code == 429

    def test_RL03_429_response_shape(self, rate_limited_client):
        """429 body has expected fields and Retry-After header."""
        with patch("reports.report_pipeline.fetch_reports",
                   return_value=_EMPTY_LIST):
            for _ in range(30):
                rate_limited_client.get("/api/reports", headers=_auth())
            resp = rate_limited_client.get("/api/reports", headers=_auth())
        assert resp.status_code == 429
        body = resp.get_json()
        assert body["status"] == "rate_limited"
        assert "message" in body
        assert "limit" in body
        assert resp.headers.get("Retry-After") is not None


# ── RL04: Per-user isolation ──────────────────────────────────────────────────

class TestRateLimitPerUser:
    def test_RL04_separate_counters_per_user(self, rate_limited_client):
        """Alice's quota exhaustion does not block Bob."""
        with patch("reports.report_pipeline.fetch_reports",
                   return_value=_EMPTY_LIST):
            # Alice fills her quota
            for _ in range(30):
                rate_limited_client.get("/api/reports", headers=_auth("alice"))
            resp_alice = rate_limited_client.get("/api/reports", headers=_auth("alice"))
            assert resp_alice.status_code == 429

            # Bob's first request must succeed
            resp_bob = rate_limited_client.get("/api/reports", headers=_auth("bob"))
            assert resp_bob.status_code != 429


# ── RL05: PDF tighter limit (10/min) ─────────────────────────────────────────

class TestRateLimitPdfTighter:
    def test_RL05_pdf_limit_is_10_per_minute(self, rate_limited_client):
        """11th request to PDF endpoint → 429."""
        with patch("reports.report_pipeline.export_report_pdf",
                   return_value=_FAKE_PDF):
            for _ in range(10):
                rate_limited_client.get("/api/reports/any-id/pdf", headers=_auth())
            resp = rate_limited_client.get("/api/reports/any-id/pdf", headers=_auth())
        assert resp.status_code == 429


# ── RL06: GET /api/reports/<id> — 60/min ─────────────────────────────────────

class TestRateLimitGetReport:
    def test_RL06_get_report_limit_is_60_per_minute(self, rate_limited_client):
        """61st request to single-report endpoint → 429."""
        with patch("reports.report_pipeline.fetch_report",
                   return_value=None):
            for _ in range(60):
                rate_limited_client.get("/api/reports/some-id", headers=_auth())
            resp = rate_limited_client.get("/api/reports/some-id", headers=_auth())
        assert resp.status_code == 429


# ── RL07–RL08: Disabled mode ──────────────────────────────────────────────────

class TestRateLimitDisabled:
    """When RATE_LIMIT_ENABLED=false (conftest.py default), no 429 ever fires."""

    def test_RL07_limit_inactive_when_disabled(self, monkeypatch):
        """100 requests with rate limiting off → no 429."""
        # RATE_LIMIT_ENABLED is already 'false' from conftest.py autouse
        monkeypatch.setenv("JWT_SECRET", "test-secret-s4-rate-limit")
        from bridge_api import app, limiter
        limiter.reset()
        with app.test_client() as c:
            with patch("reports.report_pipeline.fetch_reports",
                       return_value=_EMPTY_LIST):
                for _ in range(100):
                    resp = c.get("/api/reports", headers=_auth())
                    assert resp.status_code != 429

    def test_RL08_pdf_inactive_when_disabled(self, monkeypatch):
        """PDF endpoint: 50 requests with rate limiting off → no 429."""
        monkeypatch.setenv("JWT_SECRET", "test-secret-s4-rate-limit")
        from bridge_api import app, limiter
        limiter.reset()
        with app.test_client() as c:
            with patch("reports.report_pipeline.export_report_pdf",
                       return_value=_FAKE_PDF):
                for _ in range(50):
                    resp = c.get("/api/reports/any-id/pdf", headers=_auth())
                    assert resp.status_code != 429


# ── RL09–RL10: Unprotected endpoints unchanged ────────────────────────────────

class TestUnprotectedEndpointsNoLimit:
    """/api/valuation has no rate limit in S4."""

    def test_RL09_valuation_not_limited_no_token(self, rate_limited_client):
        """POST /api/valuation without token: should not return 429."""
        payload = {
            "location":        "القاهرة الجديدة",
            "area":            200,
            "property_type":   "شقة سكنية",
            "price_per_meter": 10_000,
        }
        for _ in range(5):
            resp = rate_limited_client.post("/api/valuation", json=payload)
            assert resp.status_code != 429

    def test_RL10_advisor_health_not_limited(self, rate_limited_client):
        """GET /api/advisor/health has no rate limit."""
        for _ in range(10):
            resp = rate_limited_client.get("/api/advisor/health")
            assert resp.status_code != 429


# ── RL11–RL12: Response headers ───────────────────────────────────────────────

class TestRateLimitHeaders:
    def test_RL11_ratelimit_headers_present_on_success(self, rate_limited_client):
        """X-RateLimit-Limit header appears on successful responses."""
        with patch("reports.report_pipeline.fetch_reports",
                   return_value=_EMPTY_LIST):
            resp = rate_limited_client.get("/api/reports", headers=_auth())
        assert resp.headers.get("X-RateLimit-Limit") is not None

    def test_RL12_retry_after_present_on_429(self, rate_limited_client):
        """Retry-After header present on 429 response."""
        with patch("reports.report_pipeline.fetch_reports",
                   return_value=_EMPTY_LIST):
            for _ in range(30):
                rate_limited_client.get("/api/reports", headers=_auth())
            resp = rate_limited_client.get("/api/reports", headers=_auth())
        assert resp.status_code == 429
        assert resp.headers.get("Retry-After") is not None
