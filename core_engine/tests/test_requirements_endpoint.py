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
        "/api/valuation/requirements?asset_type=nonexistent_type&purpose=market_value",
        headers=_auth(),
    )
    assert resp.status_code == 400
    assert "nonexistent_type" in resp.get_json()["message"]


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


# ══ Phase 8H.2C — enriched serialization tests (REQ09 – REQ15) ══════════════


# ── REQ09 ─────────────────────────────────────────────────────────────────────

def test_REQ09_checklist_items_have_enriched_keys(client):
    """Every checklist_item entry carries the Phase 8H.2C metadata keys."""
    resp = client.get(
        "/api/valuation/requirements?asset_type=residential&purpose=market_value",
        headers=_auth(),
    )
    assert resp.status_code == 200
    items = resp.get_json()["checklist_items"]
    assert len(items) > 0
    required_keys = {"name", "required", "field_type", "description",
                     "valid_values", "role", "label_ar", "group", "ui_required"}
    for item in items:
        missing = required_keys - set(item.keys())
        assert not missing, (
            f"checklist_item '{item.get('name')}' missing keys: {missing}"
        )


# ── REQ10 ─────────────────────────────────────────────────────────────────────

def test_REQ10_engine_fields_serialize_as_engine_value(client):
    """comparable / cost / income / comparables carry role='engine_value' in response."""
    resp = client.get(
        "/api/valuation/requirements?asset_type=residential&purpose=market_value",
        headers=_auth(),
    )
    data = resp.get_json()
    field_map = {i["name"]: i for i in data["checklist_items"]}
    for name in ("comparable", "cost", "income", "comparables"):
        assert name in field_map, f"Engine field '{name}' missing from checklist_items"
        assert field_map[name]["role"] == "engine_value", (
            f"Engine field '{name}' must have role='engine_value', "
            f"got {field_map[name]['role']!r}"
        )


# ── REQ11 ─────────────────────────────────────────────────────────────────────

def test_REQ11_user_input_fields_have_nonempty_label_ar(client):
    """All user_input checklist_items must carry a non-empty label_ar."""
    for asset_type in ("residential", "land"):
        resp = client.get(
            f"/api/valuation/requirements?asset_type={asset_type}&purpose=market_value",
            headers=_auth(),
        )
        items = resp.get_json()["checklist_items"]
        for item in items:
            if item["role"] == "user_input":
                assert item["label_ar"], (
                    f"user_input field '{item['name']}' in {asset_type} "
                    f"has empty label_ar in serialized response"
                )


# ── REQ12 ─────────────────────────────────────────────────────────────────────

def test_REQ12_document_fields_serialize_correctly(client):
    """Document fields carry group='document' and field_type='bool'."""
    for asset_type, expected_docs in (
        ("residential", ["ownership_document", "recent_photos",
                         "site_croquis_or_location",
                         "nearby_sale_comparables_if_available"]),
        ("land",        ["ownership_document", "site_photos",
                         "site_plan_or_croquis", "area_statement",
                         "coordinates_or_map_location",
                         "building_regulations_if_available"]),
    ):
        resp = client.get(
            f"/api/valuation/requirements?asset_type={asset_type}&purpose=market_value",
            headers=_auth(),
        )
        field_map = {i["name"]: i for i in resp.get_json()["checklist_items"]}
        for doc_name in expected_docs:
            assert doc_name in field_map, (
                f"Document field '{doc_name}' missing from {asset_type} checklist_items"
            )
            item = field_map[doc_name]
            assert item["group"] == "document", (
                f"'{doc_name}' must have group='document', got {item['group']!r}"
            )
            assert item["field_type"] == "bool", (
                f"'{doc_name}' must have field_type='bool', got {item['field_type']!r}"
            )
            assert item["role"] == "user_input", (
                f"'{doc_name}' must have role='user_input', got {item['role']!r}"
            )


# ── REQ13 ─────────────────────────────────────────────────────────────────────

def test_REQ13_residential_ui_required_fields_in_response(client):
    """Residential ui_required=True fields match the approved set in the response."""
    resp = client.get(
        "/api/valuation/requirements?asset_type=residential&purpose=market_value",
        headers=_auth(),
    )
    field_map = {i["name"]: i for i in resp.get_json()["checklist_items"]}
    expected_ui_required = {
        "area_sqm", "floor_number", "rooms_count", "finishing_level", "legal_status",
    }
    for name in expected_ui_required:
        assert name in field_map, f"Field '{name}' missing from residential checklist_items"
        assert field_map[name]["ui_required"] is True, (
            f"Residential field '{name}' must serialize ui_required=true"
        )
    for name in ("comparable", "cost", "income", "comparables"):
        assert field_map[name]["ui_required"] is False, (
            f"Engine field '{name}' must NOT serialize ui_required=true"
        )


# ── REQ14 ─────────────────────────────────────────────────────────────────────

def test_REQ14_land_checklist_items_enriched(client):
    """Land checklist_items include enriched metadata for Phase 8H.2C fields."""
    resp = client.get(
        "/api/valuation/requirements?asset_type=land&purpose=market_value",
        headers=_auth(),
    )
    assert resp.status_code == 200
    field_map = {i["name"]: i for i in resp.get_json()["checklist_items"]}
    spot_checks = {
        "land_area_sqm":      {"role": "user_input", "ui_required": True},
        "frontage_m":         {"role": "user_input", "ui_required": True},
        "zoning_type":        {"role": "user_input", "ui_required": True},
        "utilities_available":{"role": "user_input", "ui_required": False},
        "buildability_status":{"role": "user_input", "ui_required": True},
    }
    for name, expected in spot_checks.items():
        assert name in field_map, f"Land field '{name}' missing from checklist_items"
        for attr, val in expected.items():
            assert field_map[name][attr] == val, (
                f"Land field '{name}' attr '{attr}': expected {val!r}, "
                f"got {field_map[name][attr]!r}"
            )
    for name in ("comparable", "income", "comparables"):
        assert field_map[name]["role"] == "engine_value"


# ── REQ15 ─────────────────────────────────────────────────────────────────────

def test_REQ15_dynamic_fields_also_enriched(client):
    """dynamic_fields entries also carry role/label_ar/group/ui_required (backward compat)."""
    resp = client.get(
        "/api/valuation/requirements?asset_type=residential&purpose=market_value",
        headers=_auth(),
    )
    dynamic = resp.get_json()["dynamic_fields"]
    assert len(dynamic) > 0
    required_keys = {"name", "field_type", "valid_values",
                     "role", "label_ar", "group", "ui_required"}
    for entry in dynamic:
        missing = required_keys - set(entry.keys())
        assert not missing, (
            f"dynamic_fields entry '{entry.get('name')}' missing keys: {missing}"
        )


# ══ Phase 5 — field_owner serialization tests (REQ16 – REQ17) ════════════════


# ── REQ16 ─────────────────────────────────────────────────────────────────────

def test_REQ16_checklist_items_expose_field_owner(client):
    """Every checklist_item entry carries the field_owner key (Phase 5 metadata)."""
    _ALLOWED_OWNERS = {"engine", "universal", "asset", "enrichment", "purpose"}
    for asset_type in ("residential", "commercial", "land"):
        resp = client.get(
            f"/api/valuation/requirements?asset_type={asset_type}&purpose=market_value",
            headers=_auth(),
        )
        assert resp.status_code == 200
        items = resp.get_json()["checklist_items"]
        assert len(items) > 0, f"No checklist_items returned for {asset_type}"
        for item in items:
            assert "field_owner" in item, (
                f"[{asset_type}] checklist_item '{item.get('name')}' "
                f"missing 'field_owner' key"
            )
            assert item["field_owner"] in _ALLOWED_OWNERS, (
                f"[{asset_type}] '{item['name']}' has invalid "
                f"field_owner={item['field_owner']!r}"
            )


# ── REQ17 ─────────────────────────────────────────────────────────────────────

def test_REQ17_field_owner_values_correct_in_response(client):
    """Engine fields carry field_owner='engine'; enrichment fields carry 'enrichment'."""
    resp = client.get(
        "/api/valuation/requirements?asset_type=residential&purpose=market_value",
        headers=_auth(),
    )
    assert resp.status_code == 200
    field_map = {i["name"]: i for i in resp.get_json()["checklist_items"]}

    # Engine fields
    for name in ("comparable", "cost", "income", "comparables"):
        assert name in field_map, f"Engine field '{name}' missing from residential response"
        assert field_map[name]["field_owner"] == "engine", (
            f"Engine field '{name}' must have field_owner='engine', "
            f"got {field_map[name]['field_owner']!r}"
        )

    # Universal user fields
    for name in ("client_name", "location", "area", "valuation_date", "appraiser_name"):
        assert name in field_map, f"Universal field '{name}' missing from residential response"
        assert field_map[name]["field_owner"] == "universal", (
            f"Universal field '{name}' must have field_owner='universal', "
            f"got {field_map[name]['field_owner']!r}"
        )

    # Asset-specific legacy fields
    for name in ("ownership_type", "quality_tier", "age_years"):
        assert name in field_map, f"Asset field '{name}' missing from residential response"
        assert field_map[name]["field_owner"] == "asset", (
            f"Asset field '{name}' must have field_owner='asset', "
            f"got {field_map[name]['field_owner']!r}"
        )

    # Enrichment fields
    for name in ("area_sqm", "finishing_level", "legal_status", "ownership_document"):
        assert name in field_map, f"Enrichment field '{name}' missing from residential response"
        assert field_map[name]["field_owner"] == "enrichment", (
            f"Enrichment field '{name}' must have field_owner='enrichment', "
            f"got {field_map[name]['field_owner']!r}"
        )


# ── Phase 9.1 — hotel / industrial endpoint tests ────────────────────────────


# ── REQ18 — hotel + market_value → 200, checklist_items non-empty ────────────

def test_REQ18_hotel_market_value_200(client):
    """GET …?asset_type=hotel&purpose=market_value returns 200 with checklist_items."""
    resp = client.get(
        "/api/valuation/requirements?asset_type=hotel&purpose=market_value",
        headers=_auth(),
    )
    assert resp.status_code == 200, (
        f"Expected 200 for hotel/market_value, got {resp.status_code}: {resp.data}"
    )
    data = resp.get_json()
    assert data["asset_type"] == "hotel"
    assert data["purpose"] == "market_value"
    assert "checklist_items" in data, "Response missing 'checklist_items'"
    assert len(data["checklist_items"]) >= 1, "hotel/market_value checklist_items is empty"

    # Spot-check enriched keys are present on each item
    enriched_keys = {"name", "required", "field_type", "description",
                     "valid_values", "role", "label_ar", "group",
                     "ui_required", "field_owner"}
    for item in data["checklist_items"]:
        missing = enriched_keys - set(item.keys())
        assert not missing, (
            f"hotel checklist item missing keys: {sorted(missing)}"
        )


# ── REQ19 — industrial + market_value → 200, checklist_items non-empty ───────

def test_REQ19_industrial_market_value_200(client):
    """GET …?asset_type=industrial&purpose=market_value returns 200 with checklist_items."""
    resp = client.get(
        "/api/valuation/requirements?asset_type=industrial&purpose=market_value",
        headers=_auth(),
    )
    assert resp.status_code == 200, (
        f"Expected 200 for industrial/market_value, got {resp.status_code}: {resp.data}"
    )
    data = resp.get_json()
    assert data["asset_type"] == "industrial"
    assert data["purpose"] == "market_value"
    assert "checklist_items" in data, "Response missing 'checklist_items'"
    assert len(data["checklist_items"]) >= 1, "industrial/market_value checklist_items is empty"

    # Spot-check enriched keys
    enriched_keys = {"name", "required", "field_type", "description",
                     "valid_values", "role", "label_ar", "group",
                     "ui_required", "field_owner"}
    for item in data["checklist_items"]:
        missing = enriched_keys - set(item.keys())
        assert not missing, (
            f"industrial checklist item missing keys: {sorted(missing)}"
        )


# ── REQ20 — hotel asset-specific fields appear in response ───────────────────

def test_REQ20_hotel_asset_specific_fields_in_response(client):
    """hotel/market_value response includes key hotel-specific fields."""
    resp = client.get(
        "/api/valuation/requirements?asset_type=hotel&purpose=market_value",
        headers=_auth(),
    )
    assert resp.status_code == 200
    field_map = {item["name"]: item for item in resp.get_json()["checklist_items"]}
    for code in ("total_rooms", "occupancy_rate", "average_daily_rate",
                 "revpar", "star_rating"):
        assert code in field_map, f"Hotel field '{code}' missing from checklist_items"
        assert field_map[code]["field_owner"] == "asset", (
            f"Hotel field '{code}' must be field_owner='asset', "
            f"got {field_map[code]['field_owner']!r}"
        )


# ── REQ21 — industrial asset-specific fields appear in response ───────────────

def test_REQ21_industrial_asset_specific_fields_in_response(client):
    """industrial/market_value response includes key industrial-specific fields."""
    resp = client.get(
        "/api/valuation/requirements?asset_type=industrial&purpose=market_value",
        headers=_auth(),
    )
    assert resp.status_code == 200
    field_map = {item["name"]: item for item in resp.get_json()["checklist_items"]}
    for code in ("land_area", "building_area", "clear_height_or_clear_span",
                 "loading_bays", "warehouse_or_factory_type"):
        assert code in field_map, f"Industrial field '{code}' missing from checklist_items"
        assert field_map[code]["field_owner"] == "asset", (
            f"Industrial field '{code}' must be field_owner='asset', "
            f"got {field_map[code]['field_owner']!r}"
        )
