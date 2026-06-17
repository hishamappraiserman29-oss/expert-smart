"""
Phase 20 — Legacy Endpoints & Frontend Compatibility tests.

LC01  /api/image/geo-analyze alias exists and delegates to image/analyze
LC02  /api/image/geo-analyze OPTIONS returns 200
LC03  /api/market-sweep stub returns 501 + legacy flag
LC04  /api/bank-audit stub returns 501 + legacy flag
LC05  /api/fund-valuation stub returns 501 + legacy flag
LC06  /api/tax-pilot stub returns 501 + legacy flag
LC07  /api/master-report stub returns 501 + legacy flag
LC08  /api/report/generate stub returns 501 + legacy flag
LC09  /api/session/update stub returns 501 + legacy flag
LC10  /api/valuation/composite/schema returns 200 (composite_routes registered)
LC11  /api/image/analyze still responds (original not broken by alias)
LC12  /api/valuation still responds (core not broken)
LC13  /api/valuation/requirements still responds
LC14  Legacy stubs do not claim success (is_automated_fill / approved absent)
LC15  All stub responses include 'legacy': True
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# ── path setup (same pattern as test_approval_rules.py) ──────────────────
_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ---------------------------------------------------------------------------
# Flask test client fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    """Return a Flask test client for bridge_api."""
    import os
    os.environ.setdefault("JWT_SECRET", "test-secret-phase20")
    os.environ.setdefault("GOVT_SIGNING_KEY", "test-signing-key-phase20")
    from bridge_api import app
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _json(resp) -> dict:
    return json.loads(resp.data)


# ---------------------------------------------------------------------------
# LC01  /api/image/geo-analyze alias exists
# ---------------------------------------------------------------------------

def test_LC01_geo_analyze_alias_exists(client):
    """LC01: POST /api/image/geo-analyze responds (alias exists — not 404)."""
    resp = client.post("/api/image/geo-analyze")
    # No file sent → 400 (bad request), but NOT 404 (route exists)
    assert resp.status_code != 404, "Route /api/image/geo-analyze not found — alias missing"
    assert resp.status_code in (200, 400, 415, 401, 403)


# ---------------------------------------------------------------------------
# LC02  /api/image/geo-analyze OPTIONS
# ---------------------------------------------------------------------------

def test_LC02_geo_analyze_options(client):
    """LC02: OPTIONS /api/image/geo-analyze returns 200."""
    resp = client.options("/api/image/geo-analyze")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# LC03–LC09  Legacy sovereign stubs
# ---------------------------------------------------------------------------

_STUB_ROUTES = [
    "/api/market-sweep",
    "/api/bank-audit",
    "/api/fund-valuation",
    "/api/tax-pilot",
    "/api/master-report",
    "/api/report/generate",
    "/api/session/update",
]


@pytest.mark.parametrize("route", _STUB_ROUTES)
def test_LC03_to_LC09_sovereign_stub_returns_501(client, route):
    """LC03–LC09: Sovereign legacy stubs return 501 (not 404)."""
    resp = client.post(route, json={})
    assert resp.status_code == 501, (
        f"{route} returned {resp.status_code} — expected 501 stub"
    )
    body = _json(resp)
    assert body.get("legacy") is True, f"{route} response missing 'legacy: True'"
    assert "message" in body, f"{route} stub response missing 'message' field"
    assert body.get("status") == "not_implemented"


@pytest.mark.parametrize("route", _STUB_ROUTES)
def test_LC14_stubs_no_success_claim(client, route):
    """LC14: Stub responses do not claim success or approval."""
    resp = client.post(route, json={})
    body = _json(resp)
    assert body.get("status") != "success", f"{route} stub falsely claims success"
    assert body.get("approval_status") != "approved"
    assert body.get("is_automated_fill") is not True


@pytest.mark.parametrize("route", _STUB_ROUTES)
def test_LC15_stubs_include_legacy_flag(client, route):
    """LC15: All stub responses include 'legacy': True."""
    resp = client.post(route, json={})
    body = _json(resp)
    assert body.get("legacy") is True


# ---------------------------------------------------------------------------
# LC10  /api/valuation/composite/schema still works
# ---------------------------------------------------------------------------

def test_LC10_composite_schema_route_exists(client):
    """LC10: GET /api/valuation/composite/schema responds (composite_routes registered)."""
    resp = client.get("/api/valuation/composite/schema")
    # May require auth (401) or succeed (200) — must not be 404
    assert resp.status_code != 404, "composite/schema route not found — composite_routes not registered"
    assert resp.status_code in (200, 401, 403)


# ---------------------------------------------------------------------------
# LC11  /api/image/analyze original still works
# ---------------------------------------------------------------------------

def test_LC11_image_analyze_original_intact(client):
    """LC11: POST /api/image/analyze still responds after alias addition."""
    resp = client.post("/api/image/analyze")
    assert resp.status_code != 404, "/api/image/analyze broken after Phase 20 alias addition"
    assert resp.status_code in (200, 400, 415, 401, 403)


# ---------------------------------------------------------------------------
# LC12  /api/valuation core not broken
# ---------------------------------------------------------------------------

def test_LC12_valuation_core_intact(client):
    """LC12: POST /api/valuation still accepts requests (core not broken)."""
    resp = client.post("/api/valuation", json={})
    assert resp.status_code != 404, "/api/valuation disappeared"
    assert resp.status_code in (200, 400, 401, 403, 422, 500)


# ---------------------------------------------------------------------------
# LC13  /api/valuation/requirements still responds
# ---------------------------------------------------------------------------

def test_LC13_requirements_endpoint_intact(client):
    """LC13: GET /api/valuation/requirements still responds."""
    resp = client.get("/api/valuation/requirements")
    assert resp.status_code != 404, "/api/valuation/requirements disappeared"
    assert resp.status_code in (200, 400, 401, 403)


# ---------------------------------------------------------------------------
# OPTIONS for stubs
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("route", _STUB_ROUTES)
def test_LC_stub_options_200(client, route):
    """Legacy stubs return 200 for OPTIONS preflight."""
    resp = client.options(route)
    assert resp.status_code == 200, f"{route} OPTIONS returned {resp.status_code}"
