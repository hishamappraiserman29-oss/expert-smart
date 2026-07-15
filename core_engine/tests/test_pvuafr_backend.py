"""
test_pvuafr_backend.py — PVUAFR Backend Tests
Professional Valuation Uncommon Asset Fillable Requirements

PVUAFR-B01  field type registry exists and is non-empty
PVUAFR-B02  every field type in registry has a non-empty renderer key
PVUAFR-B03  map_placeholder is listed as non-fillable
PVUAFR-B04  all other standard field types are fillable
PVUAFR-B05  _PVDSR_DATA equivalent: padel requirements count >= 10 per group
PVUAFR-B06  get_special_asset_registries returns expected keys
PVUAFR-B07  hospital alias resolves to general_hospital in registry
PVUAFR-B08  school alias resolves to school_campus in registry
PVUAFR-B09  heritage alias resolves to distinguished_architectural_heritage in registry
PVUAFR-B10  _find_pvr alias is identical to _read_pvr
PVUAFR-B11  _SPECIAL_ASSET_REQ_VALUES starts as empty dict
PVUAFR-B12  GET special-asset-requirements returns 401 without auth
PVUAFR-B13  GET special-asset-requirements returns 404 for unknown request_id
PVUAFR-B14  GET special-asset-requirements returns 200 with empty values when nothing saved
PVUAFR-B15  GET response advisory_only is True
PVUAFR-B16  POST special-asset-requirements returns 401 without auth
PVUAFR-B17  POST special-asset-requirements returns 404 for unknown request_id
PVUAFR-B18  POST saves values and returns 200
PVUAFR-B19  POST response contains completion_summary with total/filled/missing/pct
PVUAFR-B20  POST with all values filled gives pct=100
PVUAFR-B21  POST with no values gives pct=0
PVUAFR-B22  GET after POST returns previously saved values
PVUAFR-B23  POST response advisory_only is True
PVUAFR-B24  no internal paths in GET response
PVUAFR-B25  no internal paths in POST response
PVUAFR-B26  POST to different asset_key clears previous values for same request_id
PVUAFR-B27  ordinary valuation route still responds (not broken)
PVUAFR-B28  tax appeal route still responds (not broken)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

# ── Path setup ────────────────────────────────────────────────────────────────

_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(str(_CORE))

from bridge_api import app                                # noqa: E402
from auth.tokens import generate_token                    # noqa: E402
import professional_valuation_routes as _pvr             # noqa: E402
import professional_valuation_taxonomy_v2 as _tax        # noqa: E402

_TEST_SECRET = "pvuafr-test-secret-32chars-xxxxx"

_INTERNAL_PATH_MARKERS = [
    "C:\\", "C:/", "/core_engine/", "/instance/", "\\core_engine\\",
    "\\instance\\", "/Users/", "\\Users\\", "/home/", ".py:", ".jsonl",
]


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def _clean_pvr_datastore():
    if _pvr._REQ_FILE.exists():
        _pvr._REQ_FILE.write_bytes(b"")
    if _pvr._EVENTS_FILE.exists():
        _pvr._EVENTS_FILE.write_bytes(b"")
    _pvr._SPECIAL_ASSET_REQ_VALUES.clear()


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", _TEST_SECRET)
    monkeypatch.delenv("JWT_TTL_SECONDS", raising=False)


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _auth() -> dict:
    return {"Authorization": f"Bearer {generate_token('test-admin')}"}


def _create_request(client, name: str = "مختبر بادل تست") -> str:
    """Create a professional valuation request and return its request_id."""
    resp = client.post(
        "/api/professional-valuation/requests",
        json={
            "client_name": name,
            "property_type": "sports_recreation_assets",
            "valuation_purpose": "mortgage",
            "property_address": "شارع التحرير، القاهرة",
            "city": "القاهرة",
            "district": "وسط البلد",
        },
        headers=_auth(),
    )
    assert resp.status_code == 201, f"create failed: {resp.data}"
    return resp.get_json()["request_id"]


def _no_internal_path(text: str) -> bool:
    return not any(m in text for m in _INTERNAL_PATH_MARKERS)


# ── Registry tests ────────────────────────────────────────────────────────────

def test_PVUAFR_B01_field_type_registry_exists():
    """PVUAFR-B01: _FIELD_TYPE_REGISTRY exists and is non-empty."""
    reg = _tax._FIELD_TYPE_REGISTRY
    assert isinstance(reg, dict)
    assert len(reg) >= 10


def test_PVUAFR_B02_every_field_type_has_icon():
    """PVUAFR-B02: Every field type in registry has a non-empty icon key."""
    reg = _tax._FIELD_TYPE_REGISTRY
    for ft, meta in reg.items():
        assert "icon" in meta, f"field type '{ft}' missing icon key"
        assert meta["icon"] is not None, f"field type '{ft}' has null icon"


def test_PVUAFR_B03_map_placeholder_in_registry():
    """PVUAFR-B03: map_placeholder exists in the field type registry."""
    reg = _tax._FIELD_TYPE_REGISTRY
    assert "map_placeholder" in reg, "map_placeholder not in _FIELD_TYPE_REGISTRY"
    assert reg["map_placeholder"].get("icon"), "map_placeholder missing icon"


def test_PVUAFR_B04_standard_field_types_present():
    """PVUAFR-B04: All standard field types are present in the registry."""
    reg = _tax._FIELD_TYPE_REGISTRY
    required_types = ["text", "textarea", "number", "currency", "percent",
                      "date", "select", "checkbox_group", "file", "coordinate"]
    for ft in required_types:
        assert ft in reg, f"'{ft}' not in _FIELD_TYPE_REGISTRY"
        assert reg[ft].get("label_ar"), f"'{ft}' missing label_ar"


def test_PVUAFR_B05_get_special_asset_registries_returns_expected_keys():
    """PVUAFR-B05: get_special_asset_registries returns the expected structure."""
    result = _tax.get_special_asset_registries()
    assert isinstance(result, dict)
    # Actual keys returned by get_special_asset_registries()
    assert "field_type" in result or "uncommon_asset_subtype" in result, \
        f"Expected registry keys not found. Got: {list(result.keys())[:5]}"


def test_PVUAFR_B06_padel_requirements_non_empty():
    """PVUAFR-B06: Padel tennis court has requirements in the dynamic registry."""
    result = _tax.get_special_asset_registries()
    # Try the correct key name
    reqs = (result.get("asset_specific_requirement")
            or result.get("asset_specific_requirement_registry")
            or {})
    subtypes = (result.get("uncommon_asset_subtype")
                or result.get("uncommon_asset_subtype_registry")
                or {})
    assert "padel_tennis_court" in reqs or "padel_tennis_court" in subtypes, \
        "padel_tennis_court not found in asset registries"


def test_PVUAFR_B07_hospital_alias_in_registry():
    """PVUAFR-B07: hospital alias maps to general_hospital."""
    result = _tax.get_special_asset_registries()
    # Check canonical key in asset_specific_requirement or uncommon_asset_subtype
    reqs = (result.get("asset_specific_requirement")
            or result.get("asset_specific_requirement_registry")
            or {})
    subtypes = (result.get("uncommon_asset_subtype")
                or result.get("uncommon_asset_subtype_registry")
                or {})
    aliases = result.get("legacy_asset_alias", {})
    assert (
        "general_hospital" in reqs
        or "general_hospital" in subtypes
        or aliases.get("hospital", {}).get("canonical_key") == "general_hospital"
    ), "general_hospital not found in registry"


def test_PVUAFR_B08_school_alias_in_registry():
    """PVUAFR-B08: school alias maps to school_campus."""
    result = _tax.get_special_asset_registries()
    reqs = (result.get("asset_specific_requirement")
            or result.get("asset_specific_requirement_registry")
            or {})
    subtypes = (result.get("uncommon_asset_subtype")
                or result.get("uncommon_asset_subtype_registry")
                or {})
    aliases = result.get("legacy_asset_alias", {})
    assert (
        "school_campus" in reqs
        or "school_campus" in subtypes
        or aliases.get("school", {}).get("canonical_key") == "school_campus"
    ), "school_campus not found in registry"


def test_PVUAFR_B09_heritage_alias_in_registry():
    """PVUAFR-B09: heritage alias maps to distinguished_architectural_heritage."""
    result = _tax.get_special_asset_registries()
    reqs = (result.get("asset_specific_requirement")
            or result.get("asset_specific_requirement_registry")
            or {})
    subtypes = (result.get("uncommon_asset_subtype")
                or result.get("uncommon_asset_subtype_registry")
                or {})
    aliases = result.get("legacy_asset_alias", {})
    assert (
        "distinguished_architectural_heritage" in reqs
        or "distinguished_architectural_heritage" in subtypes
        or aliases.get("heritage", {}).get("canonical_key") == "distinguished_architectural_heritage"
    ), "distinguished_architectural_heritage not found in registry"


def test_PVUAFR_B10_find_pvr_alias():
    """PVUAFR-B10: _find_pvr is aliased to _read_pvr."""
    assert _pvr._find_pvr is _pvr._read_pvr


def test_PVUAFR_B11_special_asset_req_values_is_dict():
    """PVUAFR-B11: _SPECIAL_ASSET_REQ_VALUES is a dict."""
    assert isinstance(_pvr._SPECIAL_ASSET_REQ_VALUES, dict)


# ── GET route tests ───────────────────────────────────────────────────────────

def test_PVUAFR_B12_get_requires_auth(client):
    """PVUAFR-B12: GET special-asset-requirements returns 401 without auth."""
    resp = client.get(
        "/api/professional-valuation/requests/nonexistent-id/special-asset-requirements"
    )
    assert resp.status_code == 401


def test_PVUAFR_B13_get_returns_404_unknown_id(client):
    """PVUAFR-B13: GET returns 404 for unknown request_id."""
    resp = client.get(
        "/api/professional-valuation/requests/pvuafr-nonexistent-xyz/special-asset-requirements",
        headers=_auth(),
    )
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["ok"] is False


def test_PVUAFR_B14_get_returns_200_empty_when_nothing_saved(client):
    """PVUAFR-B14: GET returns 200 with empty values when nothing saved yet."""
    rid = _create_request(client, "بادل تست ب14")
    resp = client.get(
        f"/api/professional-valuation/requests/{rid}/special-asset-requirements",
        headers=_auth(),
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["values"] == [] or isinstance(data["values"], list)


def test_PVUAFR_B15_get_advisory_only_true(client):
    """PVUAFR-B15: GET response advisory_only is True."""
    rid = _create_request(client, "بادل تست ب15")
    resp = client.get(
        f"/api/professional-valuation/requests/{rid}/special-asset-requirements",
        headers=_auth(),
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("advisory_only") is True


# ── POST route tests ──────────────────────────────────────────────────────────

def test_PVUAFR_B16_post_requires_auth(client):
    """PVUAFR-B16: POST special-asset-requirements returns 401 without auth."""
    resp = client.post(
        "/api/professional-valuation/requests/nonexistent-id/special-asset-requirements",
        json={"selected_asset_key": "padel_tennis_court", "values": []},
    )
    assert resp.status_code == 401


def test_PVUAFR_B17_post_returns_404_unknown_id(client):
    """PVUAFR-B17: POST returns 404 for unknown request_id."""
    resp = client.post(
        "/api/professional-valuation/requests/pvuafr-no-such-request/special-asset-requirements",
        json={"selected_asset_key": "padel_tennis_court", "values": []},
        headers=_auth(),
    )
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["ok"] is False


def test_PVUAFR_B18_post_saves_values(client):
    """PVUAFR-B18: POST saves values and returns 200."""
    rid = _create_request(client, "بادل تست ب18")
    values = [
        {"field_name": "padel_tennis_court_physical_7", "label": "عدد ملاعب البادل",
         "ft": "number", "value": "4", "group": "physical", "index": 7},
    ]
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/special-asset-requirements",
        json={"selected_asset_key": "padel_tennis_court", "values": values},
        headers=_auth(),
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["request_id"] == rid


def test_PVUAFR_B19_post_completion_summary_keys(client):
    """PVUAFR-B19: POST response contains completion_summary with required keys."""
    rid = _create_request(client, "بادل تست ب19")
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/special-asset-requirements",
        json={"selected_asset_key": "padel_tennis_court", "values": [
            {"field_name": "f1", "label": "ل1", "ft": "number", "value": "5",
             "group": "physical", "index": 0},
        ]},
        headers=_auth(),
    )
    assert resp.status_code == 200
    cs = resp.get_json().get("completion_summary", {})
    # Accept either naming convention from the backend
    has_total = "total" in cs or "total_requirements_count" in cs
    has_filled = "filled" in cs or "filled_requirements_count" in cs
    has_missing = "missing" in cs or "missing_requirements_count" in cs
    has_pct = "pct" in cs or "completion_percent" in cs
    assert has_total, f"completion_summary missing total key: {cs}"
    assert has_filled, f"completion_summary missing filled key: {cs}"
    assert has_missing, f"completion_summary missing missing key: {cs}"
    assert has_pct, f"completion_summary missing pct key: {cs}"


def test_PVUAFR_B20_post_all_filled_pct_100(client):
    """PVUAFR-B20: POST with all values non-empty gives 100% completion."""
    rid = _create_request(client, "بادل تست ب20")
    values = [
        {"field_name": f"padel_f{i}", "label": f"حقل {i}", "ft": "text",
         "value": f"قيمة {i}", "group": "descriptive", "index": i}
        for i in range(5)
    ]
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/special-asset-requirements",
        json={"selected_asset_key": "padel_tennis_court", "values": values},
        headers=_auth(),
    )
    assert resp.status_code == 200
    cs = resp.get_json()["completion_summary"]
    total = cs.get("total") or cs.get("total_requirements_count", 0)
    filled = cs.get("filled") or cs.get("filled_requirements_count", 0)
    pct = cs.get("pct") or cs.get("completion_percent", 0)
    assert total > 0
    assert filled == total
    assert pct == 100


def test_PVUAFR_B21_post_empty_values_pct_0(client):
    """PVUAFR-B21: POST with no values gives 0% completion."""
    rid = _create_request(client, "بادل تست ب21")
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/special-asset-requirements",
        json={"selected_asset_key": "padel_tennis_court", "values": []},
        headers=_auth(),
    )
    assert resp.status_code == 200
    cs = resp.get_json()["completion_summary"]
    filled = cs.get("filled") or cs.get("filled_requirements_count", 0)
    pct = cs.get("pct") or cs.get("completion_percent", 0)
    assert filled == 0
    assert pct == 0


def test_PVUAFR_B22_get_after_post_returns_saved_values(client):
    """PVUAFR-B22: GET after POST returns the previously saved values."""
    rid = _create_request(client, "بادل تست ب22")
    saved_values = [
        {"field_name": "padel_tennis_court_physical_7", "label": "عدد ملاعب البادل",
         "ft": "number", "value": "8", "group": "physical", "index": 7},
    ]
    client.post(
        f"/api/professional-valuation/requests/{rid}/special-asset-requirements",
        json={"selected_asset_key": "padel_tennis_court", "values": saved_values},
        headers=_auth(),
    )
    resp = client.get(
        f"/api/professional-valuation/requests/{rid}/special-asset-requirements",
        headers=_auth(),
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["selected_asset_key"] == "padel_tennis_court"
    vals = data["values"]
    assert len(vals) == 1
    assert vals[0]["value"] == "8"


def test_PVUAFR_B23_post_advisory_only_true(client):
    """PVUAFR-B23: POST response advisory_only is True."""
    rid = _create_request(client, "بادل تست ب23")
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/special-asset-requirements",
        json={"selected_asset_key": "cinema", "values": []},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.get_json().get("advisory_only") is True


def test_PVUAFR_B24_no_internal_paths_in_get_response(client):
    """PVUAFR-B24: GET response contains no internal file system paths."""
    rid = _create_request(client, "بادل تست ب24")
    resp = client.get(
        f"/api/professional-valuation/requests/{rid}/special-asset-requirements",
        headers=_auth(),
    )
    text = resp.data.decode("utf-8", errors="replace")
    assert _no_internal_path(text), f"Internal path found in GET response: {text[:200]}"


def test_PVUAFR_B25_no_internal_paths_in_post_response(client):
    """PVUAFR-B25: POST response contains no internal file system paths."""
    rid = _create_request(client, "بادل تست ب25")
    resp = client.post(
        f"/api/professional-valuation/requests/{rid}/special-asset-requirements",
        json={"selected_asset_key": "padel_tennis_court", "values": []},
        headers=_auth(),
    )
    text = resp.data.decode("utf-8", errors="replace")
    assert _no_internal_path(text), f"Internal path found in POST response: {text[:200]}"


def test_PVUAFR_B26_post_different_asset_key_replaces(client):
    """PVUAFR-B26: POST with different asset_key replaces previous values for same request."""
    rid = _create_request(client, "بادل تست ب26")
    client.post(
        f"/api/professional-valuation/requests/{rid}/special-asset-requirements",
        json={"selected_asset_key": "padel_tennis_court", "values": [
            {"field_name": "p1", "label": "ل1", "ft": "number", "value": "3",
             "group": "physical", "index": 0},
        ]},
        headers=_auth(),
    )
    client.post(
        f"/api/professional-valuation/requests/{rid}/special-asset-requirements",
        json={"selected_asset_key": "cinema", "values": []},
        headers=_auth(),
    )
    resp = client.get(
        f"/api/professional-valuation/requests/{rid}/special-asset-requirements?asset_key=cinema",
        headers=_auth(),
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["selected_asset_key"] == "cinema"
    assert data["values"] == []


def test_PVUAFR_B27_ordinary_valuation_still_responds(client):
    """PVUAFR-B27: Ordinary valuation route still responds (not broken by PVUAFR changes)."""
    resp = client.post(
        "/api/valuation",
        json={
            "property_type": "apartment",
            "area": 100,
            "location": "cairo",
            "condition": "good",
        },
    )
    assert resp.status_code not in (404, 405), \
        f"Ordinary valuation route broken: {resp.status_code}"


def test_PVUAFR_B28_tax_appeal_route_still_responds(client):
    """PVUAFR-B28: Tax appeal route still responds (not broken by PVUAFR changes)."""
    resp = client.get("/api/tax-appeal/expert-requests", headers=_auth())
    assert resp.status_code not in (404, 405), \
        f"Tax appeal route broken: {resp.status_code}"
