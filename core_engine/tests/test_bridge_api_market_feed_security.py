"""
SEC-007 tests — market feed write endpoint protection.

POST /api/market-feed and DELETE /api/market-feed/<id> require admin auth.
GET /api/market-feed remains public.
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
from auth.tokens import generate_token  # noqa: E402

_ADMIN_USER  = "admin-market-test"
_NON_ADMIN   = "regular-market-user"
_TEST_SECRET = "test-secret-for-market-feed-security"


def _auth(user: str) -> dict:
    return {"Authorization": f"Bearer {generate_token(user)}"}


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


# ── POST /api/market-feed ─────────────────────────────────────────────────────

class TestMarketFeedPostAuth:
    """POST must require admin; OPTIONS preflight always allowed."""

    def test_no_token_returns_401(self, client):
        resp = client.post("/api/market-feed", json={"price_per_meter": 10000})
        assert resp.status_code == 401
        assert resp.get_json()["status"] == "unauthorized"

    def test_non_admin_returns_403(self, client):
        resp = client.post(
            "/api/market-feed",
            json={"price_per_meter": 10000},
            headers=_auth(_NON_ADMIN),
        )
        assert resp.status_code == 403
        assert resp.get_json()["status"] == "forbidden"

    def test_admin_reaches_handler(self, client):
        # Admin with invalid payload reaches handler validation (not auth rejection)
        resp = client.post(
            "/api/market-feed",
            json={},  # missing price — handler returns 400
            headers=_auth(_ADMIN_USER),
        )
        assert resp.status_code not in (401, 403)

    def test_options_preflight_returns_200(self, client):
        # OPTIONS is handled by the global _pre catchall, not the auth-gated POST route
        resp = client.options("/api/market-feed")
        assert resp.status_code == 200, (
            f"OPTIONS preflight must always return 200 (got {resp.status_code})"
        )


# ── DELETE /api/market-feed/<record_id> ──────────────────────────────────────

class TestMarketFeedDeleteAuth:
    """DELETE must require admin."""

    def test_no_token_returns_401(self, client):
        resp = client.delete("/api/market-feed/some-record-id")
        assert resp.status_code == 401

    def test_non_admin_returns_403(self, client):
        resp = client.delete(
            "/api/market-feed/some-record-id",
            headers=_auth(_NON_ADMIN),
        )
        assert resp.status_code == 403

    def test_admin_reaches_handler(self, client):
        resp = client.delete(
            "/api/market-feed/nonexistent-id",
            headers=_auth(_ADMIN_USER),
        )
        # Handler returns success even if id not found (deletes 0 records)
        assert resp.status_code not in (401, 403)


# ── GET /api/market-feed — intentionally public ───────────────────────────────

class TestMarketFeedGetPublic:
    """GET is read-only and remains public — no auth required."""

    def test_no_token_still_accessible(self, client):
        resp = client.get("/api/market-feed")
        assert resp.status_code not in (401, 403)

    def test_returns_valid_response(self, client):
        resp = client.get("/api/market-feed")
        assert resp.status_code < 500
