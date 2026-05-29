"""
Unit tests for GET /api/valuation/requirements — Phase 8B.

  REQ01 — both params missing → 400
  REQ02 — purpose param missing → 400
  REQ03 — unknown asset_type → 400
  REQ04 — purpose not supported for asset_type → 400
  REQ05 — unauthenticated → 401
  REQ06 — residential + market_value → 200, correct structure
  REQ07 — land + market_value → 200, cost NOT in recommended_methods
  REQ08 — commercial + investment_analysis → 200, correct structure
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

from bridge_api import app        # noqa: E402
from auth.tokens import generate_token  # noqa: E402

_USER        = "reqs-test-user"
_TEST_SECRET = "test-secret-for-baseline"


def _auth() -> dict:
    return {"Authorization": f"Bearer {generate_token(_USER)}"}


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", _TEST_SECRET)
    monkeypatch.delenv("JWT_TTL_SECONDS", raising=False)


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── REQ01 ─────────────────────────────────────────────────────────────────────

def test_REQ01_missing_both_params(client):
    """No query params → 400 with explanatory message."""
    resp = client.get("/api/valuation/requirements", headers=_auth())
    assert resp.status_code == 400
    data = resp.get_json()
    assert "asset_type" in data["message"]
    assert "purpose" in data["message"]


# ── REQ02 ─────────────────────────────────────────────────────────────────────

def test_REQ02_missing_purpose(client):
    """asset_type supplied but purpose absent → 400."""
    resp = client.get(
        "/api/valuation/requirements?asset_type=residential",
        headers=_auth(),
    )
    assert resp.status_code == 400
    assert "purpose" in resp.get_json()["message"]


# ── REQ03 ─────────────────────────────────────────────────────────────────────

def test_REQ03_unknown_asset_type(client):
    """Unrecognised asset_type → 400."""
    resp = client.get(
        "/api/valuation/requirements?asset_type=industrial&purpose=market_value",
        headers=_auth(),
    )
    assert resp.status_code == 400
    assert "industrial" in resp.get_json()["message"]


# ── REQ04 ─────────────────────────────────────────────────────────────────────

def test_REQ04_purpose_not_supported_for_asset_type(client):
    """residential + investment_analysis is not in the registry → 400."""
    resp = client.get(
        "/api/valuation/requirements?asset_type=residential&purpose=investment_analysis",
        headers=_auth(),
    )
    assert resp.status_code == 400
    assert "investment_analysis" in resp.get_json()["message"]


# ── REQ05 ─────────────────────────────────────────────────────────────────────

def test_REQ05_unauthenticated(client):
    """No Authorization header → 401."""
    resp = client.get(
        "/api/valuation/requirements?asset_type=residential&purpose=market_value"
    )
    assert resp.status_code == 401


# ── REQ06 ─────────────────────────────────────────────────────────────────────

def test_REQ06_residential_market_value(client):
    """residential + market_value → 200 with correct structure; enriched dynamic_fields."""
    resp = client.get(
        "/api/valuation/requirements?asset_type=residential&purpose=market_value",
        headers=_auth(),
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["asset_type"] == "residential"
    assert data["purpose"] == "market_value"
    assert isinstance(data["checklist_items"], list)
    assert len(data["checklist_items"]) > 0
    assert isinstance(data["dynamic_fields"], list)
    assert isinstance(data["recommended_methods"], list)
    required_names = [i["name"] for i in data["checklist_items"] if i["required"]]
    assert "cost" in required_names
    assert "comparable" in required_names
    # Phase 8H.2A: new enum fields must appear in dynamic_fields
    dynamic_names = [f["name"] for f in data["dynamic_fields"]]
    assert "finishing_level" in dynamic_names, (
        f"finishing_level missing from residential dynamic_fields. Got: {dynamic_names}"
    )
    assert "legal_status" in dynamic_names, (
        f"legal_status missing from residential dynamic_fields. Got: {dynamic_names}"
    )


# ── REQ07 ─────────────────────────────────────────────────────────────────────

def test_REQ07_land_market_value_no_cost_method(client):
    """land + market_value → 200; cost NOT in recommended_methods; enriched dynamic_fields."""
    resp = client.get(
        "/api/valuation/requirements?asset_type=land&purpose=market_value",
        headers=_auth(),
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert "cost" not in data["recommended_methods"]
    assert "comparable" in data["recommended_methods"]
    assert "income" in data["recommended_methods"]
    assert "cost" in data["notes"].lower()
    # Phase 8H.2A: new enum fields must appear in dynamic_fields
    dynamic_names = [f["name"] for f in data["dynamic_fields"]]
    assert "zoning_type" in dynamic_names, (
        f"zoning_type missing from land dynamic_fields. Got: {dynamic_names}"
    )
    assert "buildability_status" in dynamic_names, (
        f"buildability_status missing from land dynamic_fields. Got: {dynamic_names}"
    )
    assert "legal_status" in dynamic_names, (
        f"legal_status missing from land dynamic_fields. Got: {dynamic_names}"
    )


# ── REQ08 ─────────────────────────────────────────────────────────────────────

def test_REQ08_commercial_investment_analysis(client):
    """commercial + investment_analysis → 200 with correct structure."""
    resp = client.get(
        "/api/valuation/requirements?asset_type=commercial&purpose=investment_analysis",
        headers=_auth(),
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["asset_type"] == "commercial"
    assert data["purpose"] == "investment_analysis"
    assert isinstance(data["checklist_items"], list)
    assert "cost" in data["recommended_methods"]
