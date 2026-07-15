"""
test_pvuaf_backend.py — PVUAF Backend Tests (Part L).

Tests the backend changes introduced by the PVUAF task:
Professional Valuation Page — Section 2 Refinement:
Common Asset Type vs Uncommon Asset Family/Subtype.

PVUAFB01  asset_type_selection_context field exists in create response
PVUAFB02  available_common_asset_types is a non-empty list
PVUAFB03  available_uncommon_asset_families is a non-empty list
PVUAFB04  heritage_assets is in available_uncommon_asset_families
PVUAFB05  cultural_heritage_assets is in available_uncommon_asset_families
PVUAFB06  sports_recreation_assets is in available_uncommon_asset_families
PVUAFB07  selected_asset_source = common_asset_type when only asset_type provided
PVUAFB08  selected_asset_source = uncommon_family when asset_family is uncommon (no subtype)
PVUAFB09  selected_asset_source = uncommon_subtype when asset_family is uncommon + subtype given
PVUAFB10  uncommon_asset_family alias accepted in POST body (backward compat)
PVUAFB11  uncommon_asset_subtype alias accepted in POST body (backward compat)
PVUAFB12  uncommon_asset_family echoed back in context when family is uncommon
PVUAFB13  uncommon_asset_subtype echoed back in context when subtype given with uncommon family
PVUAFB14  common families NOT in available_uncommon_asset_families (hidden-only)
PVUAFB15  duplicate_options_preserved_as_aliases list is non-empty (backward compat present)
PVUAFB16  visible_ui_changes dict shows correct renamed labels
PVUAFB17  visible_ui_changes shows new testids
PVUAFB18  شقة سكنية is in available_common_asset_types
PVUAFB19  heritage key is in available_common_asset_types (original option not deleted)
PVUAFB20  residential_housing is hidden from visible UI but in available_asset_families (backward compat)
PVUAFB21  no internal paths in asset_type_selection_context response
PVUAFB22  create request with heritage_assets family returns 201
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

from bridge_api import app                            # noqa: E402
import professional_valuation_routes as _pvr         # noqa: E402

_TEST_SECRET = "pvr-pvuaf-test-secret-32chars!!!"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def _clean_pvr_datastore():
    if _pvr._REQ_FILE.exists():
        _pvr._REQ_FILE.write_bytes(b"")
    if _pvr._EVENTS_FILE.exists():
        _pvr._EVENTS_FILE.write_bytes(b"")


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", _TEST_SECRET)
    monkeypatch.delenv("JWT_TTL_SECONDS", raising=False)


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


_BASE_PAYLOAD: dict = {
    "client_name":       "اختبار PVUAF",
    "property_type":     "شقة سكنية",
    "valuation_purpose": "قيمة سوقية",
    "city":              "الرياض",
    "district":          "العليا",
}


def _create(client, extra=None) -> tuple:
    data = dict(_BASE_PAYLOAD)
    if extra:
        data.update(extra)
    resp = client.post(
        "/api/professional-valuation/requests",
        json=data,
        content_type="application/json",
    )
    body = resp.get_json() or {}
    return resp, body


def _ctx(body: dict) -> dict:
    return body.get("asset_type_selection_context", {})


# ── PVUAFB01–PVUAFB03: Context field exists ───────────────────────────────────

def test_PVUAFB01_asset_type_selection_context_in_response(client):
    resp, body = _create(client)
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {body}"
    assert "asset_type_selection_context" in body, (
        "asset_type_selection_context must be in create response"
    )


def test_PVUAFB02_available_common_asset_types_is_non_empty(client):
    _, body = _create(client)
    ctx = _ctx(body)
    common = ctx.get("available_common_asset_types", [])
    assert isinstance(common, list) and len(common) > 0, (
        f"available_common_asset_types must be a non-empty list, got: {common!r}"
    )


def test_PVUAFB03_available_uncommon_families_is_non_empty(client):
    _, body = _create(client)
    ctx = _ctx(body)
    uncommon = ctx.get("available_uncommon_asset_families", [])
    assert isinstance(uncommon, list) and len(uncommon) > 0, (
        f"available_uncommon_asset_families must be a non-empty list, got: {uncommon!r}"
    )


# ── PVUAFB04–PVUAFB06: Specific uncommon families present ────────────────────

def test_PVUAFB04_heritage_assets_in_uncommon_families(client):
    _, body = _create(client)
    ctx = _ctx(body)
    uncommon = ctx.get("available_uncommon_asset_families", [])
    assert "heritage_assets" in uncommon, (
        f"heritage_assets must be in available_uncommon_asset_families, got: {uncommon}"
    )


def test_PVUAFB05_cultural_heritage_assets_in_uncommon_families(client):
    _, body = _create(client)
    ctx = _ctx(body)
    uncommon = ctx.get("available_uncommon_asset_families", [])
    assert "cultural_heritage_assets" in uncommon, (
        f"cultural_heritage_assets must be in available_uncommon_asset_families, got: {uncommon}"
    )


def test_PVUAFB06_sports_recreation_assets_in_uncommon_families(client):
    _, body = _create(client)
    ctx = _ctx(body)
    uncommon = ctx.get("available_uncommon_asset_families", [])
    assert "sports_recreation_assets" in uncommon, (
        f"sports_recreation_assets must be in available_uncommon_asset_families, got: {uncommon}"
    )


# ── PVUAFB07–PVUAFB09: selected_asset_source logic ───────────────────────────

def test_PVUAFB07_source_is_common_when_only_asset_type(client):
    _, body = _create(client, {"asset_type": "شقة سكنية", "asset_family": ""})
    ctx = _ctx(body)
    assert ctx.get("selected_asset_source") == "common_asset_type", (
        f"selected_asset_source must be 'common_asset_type', got: {ctx.get('selected_asset_source')!r}"
    )


def test_PVUAFB08_source_is_uncommon_family_when_no_subtype(client):
    _, body = _create(client, {"asset_family": "heritage_assets", "asset_subtype": ""})
    ctx = _ctx(body)
    assert ctx.get("selected_asset_source") == "uncommon_family", (
        f"selected_asset_source must be 'uncommon_family', got: {ctx.get('selected_asset_source')!r}"
    )


def test_PVUAFB09_source_is_uncommon_subtype_when_family_and_subtype(client):
    _, body = _create(client, {
        "asset_family": "heritage_assets",
        "asset_subtype": "distinguished_architectural_heritage",
    })
    ctx = _ctx(body)
    assert ctx.get("selected_asset_source") == "uncommon_subtype", (
        f"selected_asset_source must be 'uncommon_subtype', got: {ctx.get('selected_asset_source')!r}"
    )


# ── PVUAFB10–PVUAFB11: Alias backward compatibility ──────────────────────────

def test_PVUAFB10_uncommon_asset_family_alias_accepted(client):
    resp, body = _create(client, {"uncommon_asset_family": "sports_recreation_assets"})
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {body}"
    ctx = _ctx(body)
    assert ctx.get("selected_asset_source") in ("uncommon_family", "uncommon_subtype"), (
        f"uncommon_asset_family alias must set selected_asset_source to uncommon_family, got: {ctx.get('selected_asset_source')!r}"
    )


def test_PVUAFB11_uncommon_asset_subtype_alias_accepted(client):
    resp, body = _create(client, {
        "uncommon_asset_family": "healthcare_assets",
        "uncommon_asset_subtype": "general_hospital",
    })
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {body}"
    ctx = _ctx(body)
    assert ctx.get("selected_asset_source") == "uncommon_subtype", (
        f"uncommon_asset_subtype alias must yield 'uncommon_subtype' source, got: {ctx.get('selected_asset_source')!r}"
    )


# ── PVUAFB12–PVUAFB13: Uncommon family/subtype echoed ────────────────────────

def test_PVUAFB12_uncommon_family_echoed_when_uncommon(client):
    _, body = _create(client, {"asset_family": "heritage_assets"})
    ctx = _ctx(body)
    assert ctx.get("uncommon_asset_family") == "heritage_assets", (
        f"uncommon_asset_family must be echoed when family is uncommon, got: {ctx.get('uncommon_asset_family')!r}"
    )


def test_PVUAFB13_uncommon_subtype_echoed_when_set(client):
    _, body = _create(client, {
        "asset_family": "sports_recreation_assets",
        "asset_subtype": "stadium",
    })
    ctx = _ctx(body)
    assert ctx.get("uncommon_asset_subtype") == "stadium", (
        f"uncommon_asset_subtype must be echoed when subtype is given with uncommon family, got: {ctx.get('uncommon_asset_subtype')!r}"
    )


# ── PVUAFB14–PVUAFB15: Duplicate prevention and aliases ──────────────────────

def test_PVUAFB14_common_families_not_in_uncommon_list(client):
    _, body = _create(client)
    ctx = _ctx(body)
    uncommon = ctx.get("available_uncommon_asset_families", [])
    common_families = [
        "residential_housing", "land_plots", "commercial_retail",
        "office_administrative", "industrial_logistics", "hospitality_leisure",
        "healthcare_education",
    ]
    for fam in common_families:
        assert fam not in uncommon, (
            f"Common family '{fam}' must NOT appear in available_uncommon_asset_families"
        )


def test_PVUAFB15_duplicate_options_preserved_as_aliases_non_empty(client):
    _, body = _create(client)
    ctx = _ctx(body)
    aliases = ctx.get("duplicate_options_preserved_as_aliases", [])
    assert isinstance(aliases, list) and len(aliases) > 0, (
        f"duplicate_options_preserved_as_aliases must be a non-empty list, got: {aliases!r}"
    )
    assert "residential_housing" in aliases, (
        "residential_housing must be in duplicate_options_preserved_as_aliases as a preserved alias"
    )


# ── PVUAFB16–PVUAFB17: visible_ui_changes ────────────────────────────────────

def test_PVUAFB16_visible_ui_changes_shows_renamed_labels(client):
    _, body = _create(client)
    ctx = _ctx(body)
    ui = ctx.get("visible_ui_changes", {})
    assert ui.get("family_label_changed_from") == "عائلة الأصل", (
        f"family_label_changed_from must be 'عائلة الأصل', got: {ui.get('family_label_changed_from')!r}"
    )
    assert ui.get("family_label_changed_to") == "عائلة الأصل غير الشائعة", (
        f"family_label_changed_to must be 'عائلة الأصل غير الشائعة', got: {ui.get('family_label_changed_to')!r}"
    )
    assert ui.get("subtype_label_changed_to") == "النوع الفرعي للأصل غير الشائع", (
        f"subtype_label_changed_to mismatch, got: {ui.get('subtype_label_changed_to')!r}"
    )


def test_PVUAFB17_visible_ui_changes_shows_new_testids(client):
    _, body = _create(client)
    ctx = _ctx(body)
    ui = ctx.get("visible_ui_changes", {})
    assert ui.get("new_testid_family") == "pro-val-uncommon-asset-family-select", (
        f"new_testid_family mismatch, got: {ui.get('new_testid_family')!r}"
    )
    assert ui.get("new_testid_subtype") == "pro-val-uncommon-asset-subtype-select", (
        f"new_testid_subtype mismatch, got: {ui.get('new_testid_subtype')!r}"
    )


# ── PVUAFB18–PVUAFB20: Common list content ───────────────────────────────────

def test_PVUAFB18_arabic_apartment_in_common_types(client):
    _, body = _create(client)
    ctx = _ctx(body)
    common = ctx.get("available_common_asset_types", [])
    assert "شقة سكنية" in common, (
        f"'شقة سكنية' must be in available_common_asset_types (original option preserved), got: {common}"
    )


def test_PVUAFB19_heritage_key_in_common_types(client):
    _, body = _create(client)
    ctx = _ctx(body)
    common = ctx.get("available_common_asset_types", [])
    assert "heritage" in common, (
        f"'heritage' original key must be in available_common_asset_types (not deleted), got: {common}"
    )


def test_PVUAFB20_residential_housing_in_all_families_for_backward_compat(client):
    _, body = _create(client)
    ctx = _ctx(body)
    all_families = ctx.get("available_asset_families", [])
    assert "residential_housing" in all_families, (
        "residential_housing must be in available_asset_families for backward compat "
        f"(even if hidden from visible UI), got: {all_families}"
    )


# ── PVUAFB21–PVUAFB22: Safety checks ─────────────────────────────────────────

def test_PVUAFB21_no_internal_paths_in_context(client):
    _, body = _create(client, {"asset_family": "heritage_assets"})
    ctx = _ctx(body)
    ctx_str = json.dumps(ctx, ensure_ascii=False)
    forbidden = ["C:\\", "C:/", "/home/", "/root/", "core_engine\\", "core_engine/"]
    for pattern in forbidden:
        assert pattern not in ctx_str, (
            f"Internal path '{pattern}' must not appear in asset_type_selection_context"
        )


def test_PVUAFB22_create_with_heritage_family_returns_201(client):
    resp, body = _create(client, {
        "asset_family": "heritage_assets",
        "asset_subtype": "listed_heritage_building",
    })
    assert resp.status_code == 201, f"Expected 201 with heritage_assets family, got {resp.status_code}: {body}"
    assert body.get("ok") is True
    assert "request_id" in body
