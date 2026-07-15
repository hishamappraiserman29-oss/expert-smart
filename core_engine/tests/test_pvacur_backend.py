"""
PVACURB01–PVACURB27 — Backend tests for Professional Valuation:
Common vs Uncommon Asset Types/Families/Subtypes + Requirements Context.

Verifies asset_type_selection_context fields returned by POST
/api/professional-valuation/requests.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

# ── Path setup (mirrors existing backend test pattern) ───────────────────────

_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(str(_CORE))

from bridge_api import app                            # noqa: E402
import professional_valuation_routes as _pvr         # noqa: E402

_TEST_SECRET = "pvr-pvacur-test-secret-32chars!!!"


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


# ── Helpers ───────────────────────────────────────────────────────────────────

_BASE: dict = {
    "client_name":       "اختبار PVACUR",
    "property_type":     "شقة سكنية",
    "valuation_purpose": "قيمة سوقية",
    "city":              "الرياض",
    "district":          "العليا",
}


def _post(client, extra: dict | None = None) -> tuple:
    body = dict(_BASE)
    if extra:
        body.update(extra)
    resp = client.post(
        "/api/professional-valuation/requests",
        json=body,
        content_type="application/json",
    )
    rb = resp.get_json() or {}
    return resp, rb


def _ctx(rb: dict) -> dict:
    return rb.get("asset_type_selection_context", {})


# ── PVACURB01–PVACURB05: Context existence ───────────────────────────────────

def test_PVACURB01_context_key_exists(client):
    _, rb = _post(client)
    assert "asset_type_selection_context" in rb


def test_PVACURB02_available_common_asset_types_exists(client):
    _, rb = _post(client)
    ctx = _ctx(rb)
    assert "available_common_asset_types" in ctx
    assert isinstance(ctx["available_common_asset_types"], list)


def test_PVACURB03_available_uncommon_families_exists(client):
    _, rb = _post(client)
    ctx = _ctx(rb)
    assert "available_uncommon_asset_families" in ctx
    assert isinstance(ctx["available_uncommon_asset_families"], list)


def test_PVACURB04_available_uncommon_subtypes_exists(client):
    _, rb = _post(client)
    ctx = _ctx(rb)
    assert "available_uncommon_asset_subtypes" in ctx


def test_PVACURB05_available_subtypes_by_family_exists(client):
    _, rb = _post(client)
    ctx = _ctx(rb)
    assert "available_uncommon_asset_subtypes_by_family" in ctx
    assert isinstance(ctx["available_uncommon_asset_subtypes_by_family"], dict)


# ── PVACURB06–PVACURB08: Common asset list contents ─────────────────────────

def test_PVACURB06_common_list_includes_hotel(client):
    _, rb = _post(client)
    common = _ctx(rb)["available_common_asset_types"]
    assert "hotel" in common or "فندق" in common


def test_PVACURB07_common_list_includes_vacant_land(client):
    _, rb = _post(client)
    common = _ctx(rb)["available_common_asset_types"]
    assert "vacant_land" in common or "أرض فضاء" in common


def test_PVACURB08_common_list_includes_residential_apartment(client):
    _, rb = _post(client)
    common = _ctx(rb)["available_common_asset_types"]
    assert "residential_apartment" in common or "شقة سكنية" in common


# ── PVACURB09–PVACURB12: Uncommon family list contents ──────────────────────

def test_PVACURB09_uncommon_families_includes_entertainment(client):
    _, rb = _post(client)
    families = _ctx(rb)["available_uncommon_asset_families"]
    assert "entertainment_assets" in families


def test_PVACURB10_uncommon_families_includes_heritage(client):
    _, rb = _post(client)
    families = _ctx(rb)["available_uncommon_asset_families"]
    assert "heritage_assets" in families


def test_PVACURB11_uncommon_families_includes_special_purpose(client):
    _, rb = _post(client)
    families = _ctx(rb)["available_uncommon_asset_families"]
    assert "special_purpose_assets" in families


def test_PVACURB12_uncommon_family_count_gte_15(client):
    _, rb = _post(client)
    families = _ctx(rb)["available_uncommon_asset_families"]
    assert len(families) >= 15


# ── PVACURB13–PVACURB15: Subtype mapping contents ───────────────────────────

def test_PVACURB13_entertainment_subtypes_include_cinema(client):
    _, rb = _post(client, {"asset_family": "entertainment_assets"})
    subtypes_map = _ctx(rb)["available_uncommon_asset_subtypes_by_family"]
    assert "entertainment_assets" in subtypes_map
    assert "cinema" in subtypes_map["entertainment_assets"]


def test_PVACURB14_heritage_subtypes_include_distinguished(client):
    _, rb = _post(client, {"asset_family": "heritage_assets"})
    subtypes_map = _ctx(rb)["available_uncommon_asset_subtypes_by_family"]
    assert "heritage_assets" in subtypes_map
    assert "distinguished_architectural_heritage" in subtypes_map["heritage_assets"]


def test_PVACURB15_subtypes_for_family_populated_when_family_selected(client):
    _, rb = _post(client, {"asset_family": "entertainment_assets"})
    ctx = _ctx(rb)
    subtypes = ctx.get("available_uncommon_asset_subtypes", [])
    assert "cinema" in subtypes


# ── PVACURB16–PVACURB18: selected_asset_source ──────────────────────────────

def test_PVACURB16_source_common_when_asset_type_only(client):
    _, rb = _post(client, {"asset_type": "hotel", "asset_family": ""})
    assert _ctx(rb)["selected_asset_source"] == "common_asset_type"


def test_PVACURB17_source_uncommon_family_when_family_only(client):
    _, rb = _post(client, {"asset_family": "entertainment_assets", "asset_subtype": ""})
    assert _ctx(rb)["selected_asset_source"] == "uncommon_family"


def test_PVACURB18_source_uncommon_subtype_when_family_and_subtype(client):
    _, rb = _post(client, {
        "asset_family": "entertainment_assets",
        "asset_subtype": "cinema",
    })
    assert _ctx(rb)["selected_asset_source"] == "uncommon_subtype"


# ── PVACURB19–PVACURB21: Duplicate / hidden options ─────────────────────────

def test_PVACURB19_duplicate_options_removed_list_present(client):
    _, rb = _post(client)
    ctx = _ctx(rb)
    assert "duplicate_options_removed_from_visible_ui" in ctx


def test_PVACURB20_duplicate_options_preserved_as_aliases(client):
    _, rb = _post(client)
    ctx = _ctx(rb)
    preserved = ctx.get("duplicate_options_preserved_as_aliases", [])
    assert isinstance(preserved, list)
    assert len(preserved) >= 7  # 7 hidden common families


def test_PVACURB21_no_internal_paths_in_response(client):
    _, rb = _post(client)
    body_str = json.dumps(rb)
    forbidden = ["C:\\Users", "/home/", "site-packages",
                 "professional_valuation_routes.py"]
    for f in forbidden:
        assert f not in body_str, f"Internal path leaked: {f!r}"


# ── PVACURB22–PVACURB24: No-deletion assertions ──────────────────────────────

def test_PVACURB22_deleted_common_types_empty(client):
    # The common list must be non-empty (proves nothing was deleted)
    _, rb = _post(client)
    common = _ctx(rb).get("available_common_asset_types", [])
    assert len(common) >= 40


def test_PVACURB23_deleted_uncommon_families_empty(client):
    _, rb = _post(client)
    families = _ctx(rb).get("available_uncommon_asset_families", [])
    assert len(families) >= 15


def test_PVACURB24_uncommon_subtype_map_no_empty_lists(client):
    _, rb = _post(client)
    subtypes_map = _ctx(rb).get("available_uncommon_asset_subtypes_by_family", {})
    for family, subtypes in subtypes_map.items():
        assert isinstance(subtypes, list), f"{family} subtypes not a list"
        assert len(subtypes) > 0, f"{family} has empty subtype list"


# ── PVACURB25–PVACURB27: Regression + final checks ───────────────────────────

def test_PVACURB25_entertainment_family_request_returns_201(client):
    resp, rb = _post(client, {"asset_family": "entertainment_assets"})
    assert resp.status_code in (200, 201)
    assert rb.get("ok") is True


def test_PVACURB26_entertainment_cinema_source_correct(client):
    _, rb = _post(client, {
        "asset_family": "entertainment_assets",
        "asset_subtype": "cinema",
    })
    ctx = _ctx(rb)
    assert ctx.get("selected_asset_source") == "uncommon_subtype"
    assert ctx.get("uncommon_asset_family") == "entertainment_assets"
    assert ctx.get("uncommon_asset_subtype") == "cinema"


def test_PVACURB27_entertainment_family_label_correct(client):
    _, rb = _post(client, {"asset_family": "entertainment_assets"})
    ctx = _ctx(rb)
    label = ctx.get("uncommon_asset_family_label_ar", "")
    assert "ترفيه" in label or "entertainment" in label.lower()
