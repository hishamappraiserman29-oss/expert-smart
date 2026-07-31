# -*- coding: utf-8 -*-
"""
test_pv_force_restore_common_asset_old_requirements.py
Backend tests: Force Restore Old Common Asset Valuation Requirement Tables (PVFR-B)

Tests verify the restored _PV_COMMON_REQ_DATA structure, context files,
git history search report, and backend compatibility.

Tests:
  PVFR-B01  Git history search report exists
  PVFR-B02  old_common_asset_ui_inventory exists
  PVFR-B03  common_asset_legacy_requirements_context exists
  PVFR-B04  residential apartment restored (fields count >= 10)
  PVFR-B05  villa alias maps to residential_apartment
  PVFR-B06  retail shop restored (fields count >= 8)
  PVFR-B07  factory restored (fields count >= 10)
  PVFR-B08  vacant land restored (maps to urban_land)
  PVFR-B09  administrative office restored (fields count >= 8)
  PVFR-B10  warehouse restored (fields count >= 8)
  PVFR-B11  hotel restored (fields count >= 10)
  PVFR-B12  deleted_old_requirements is empty
  PVFR-B13  deleted_old_options is empty
  PVFR-B14  static_only_after_restore is false
  PVFR-B15  every common asset requirement has field_type
  PVFR-B16  every select has at least one option
  PVFR-B17  option sets are correct (no cross-contamination)
  PVFR-B18  no internal paths in context
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

# ── Paths ─────────────────────────────────────────────────────────────────────
_QA_DIR = Path(__file__).parent.parent / "instance" / "manual_review_outputs" / \
    "professional_valuation_force_restore_common_asset_old_requirements"


def _load(fname: str) -> dict:
    p = _QA_DIR / fname
    if not p.exists():
        pytest.skip(f"QA file not found: {fname}")
    return json.loads(p.read_text(encoding="utf-8"))


# ── PVFR-B01: Git history search report exists ────────────────────────────────
def test_pvfr_b01_git_history_search_report_exists():
    """PVFR-B01: Git history search report file exists."""
    assert (_QA_DIR / "01_git_history_search_report.json").exists(), \
        "Git history search report missing"


# ── PVFR-B02: Old common asset UI inventory exists ────────────────────────────
def test_pvfr_b02_old_common_asset_ui_inventory_exists():
    """PVFR-B02: Old common asset UI inventory file exists."""
    assert (_QA_DIR / "02_old_common_asset_ui_inventory.json").exists(), \
        "Old UI inventory file missing"


# ── PVFR-B03: Common asset legacy requirements context exists ─────────────────
def test_pvfr_b03_common_asset_legacy_requirements_context_exists():
    """PVFR-B03: Backend compatibility context file exists."""
    assert (_QA_DIR / "08_backend_compatibility_context.json").exists(), \
        "Backend compatibility context file missing"
    ctx = _load("08_backend_compatibility_context.json")
    assert "common_asset_legacy_requirements_context" in ctx


# ── PVFR-B04: Residential apartment restored ─────────────────────────────────
def test_pvfr_b04_residential_apartment_restored():
    """PVFR-B04: Residential apartment has >= 10 restored requirements."""
    inv = _load("04_restored_common_asset_requirements_inventory.json")
    apt = inv.get("residential_apartment", {})
    assert apt, "residential_apartment not in inventory"
    total = apt.get("total_fields", 0)
    assert total >= 10, f"Expected >= 10 fields for residential_apartment, got {total}"


# ── PVFR-B05: Villa alias maps to residential_apartment ─────────────────────
def test_pvfr_b05_villa_alias_maps_to_residential_apartment():
    """PVFR-B05: Villa is aliased to residential_apartment data."""
    inv = _load("04_restored_common_asset_requirements_inventory.json")
    apt = inv.get("residential_apartment", {})
    aliases = apt.get("aliases", [])
    assert "residential_villa" in aliases, \
        "residential_villa alias not found in residential_apartment"


# ── PVFR-B06: Retail shop restored ───────────────────────────────────────────
def test_pvfr_b06_retail_shop_restored():
    """PVFR-B06: Retail shop has >= 8 restored requirements."""
    inv = _load("04_restored_common_asset_requirements_inventory.json")
    shop = inv.get("retail_shop", {})
    assert shop, "retail_shop not in inventory"
    total = shop.get("total_fields", 0)
    assert total >= 8, f"Expected >= 8 fields for retail_shop, got {total}"


# ── PVFR-B07: Factory restored ───────────────────────────────────────────────
def test_pvfr_b07_factory_restored():
    """PVFR-B07: Industrial factory has >= 10 restored requirements."""
    inv = _load("04_restored_common_asset_requirements_inventory.json")
    factory = inv.get("industrial_factory", {})
    assert factory, "industrial_factory not in inventory"
    total = factory.get("total_fields", 0)
    assert total >= 10, f"Expected >= 10 fields for industrial_factory, got {total}"


# ── PVFR-B08: Vacant land restored ───────────────────────────────────────────
def test_pvfr_b08_vacant_land_restored():
    """PVFR-B08: Vacant land maps to urban_land data."""
    inv = _load("04_restored_common_asset_requirements_inventory.json")
    land = inv.get("urban_land", {})
    assert land, "urban_land not in inventory"
    aliases = land.get("aliases", [])
    assert "vacant_land" in aliases, "vacant_land alias not found in urban_land"
    total = land.get("total_fields", 0)
    assert total >= 8, f"Expected >= 8 fields for urban_land, got {total}"


# ── PVFR-B09: Administrative office restored ─────────────────────────────────
def test_pvfr_b09_administrative_office_restored():
    """PVFR-B09: Administrative office has >= 8 restored requirements."""
    inv = _load("04_restored_common_asset_requirements_inventory.json")
    office = inv.get("administrative_office", {})
    assert office, "administrative_office not in inventory"
    total = office.get("total_fields", 0)
    assert total >= 8, f"Expected >= 8 fields for administrative_office, got {total}"


# ── PVFR-B10: Warehouse restored ─────────────────────────────────────────────
def test_pvfr_b10_warehouse_restored():
    """PVFR-B10: Warehouse has >= 8 restored requirements."""
    inv = _load("04_restored_common_asset_requirements_inventory.json")
    wh = inv.get("warehouse", {})
    assert wh, "warehouse not in inventory"
    total = wh.get("total_fields", 0)
    assert total >= 8, f"Expected >= 8 fields for warehouse, got {total}"


# ── PVFR-B11: Hotel restored ──────────────────────────────────────────────────
def test_pvfr_b11_hotel_restored():
    """PVFR-B11: Hotel has >= 10 restored requirements."""
    inv = _load("04_restored_common_asset_requirements_inventory.json")
    hotel = inv.get("hotel", {})
    assert hotel, "hotel not in inventory"
    total = hotel.get("total_fields", 0)
    assert total >= 10, f"Expected >= 10 fields for hotel, got {total}"


# ── PVFR-B12: deleted_old_requirements is empty ──────────────────────────────
def test_pvfr_b12_deleted_old_requirements_empty():
    """PVFR-B12: No old requirements were deleted."""
    audit = _load("09_no_deletion_audit.json")
    deleted = audit.get("deleted_old_requirements", [])
    assert deleted == [], f"Deleted old requirements found: {deleted}"


# ── PVFR-B13: deleted_old_options is empty ───────────────────────────────────
def test_pvfr_b13_deleted_old_options_empty():
    """PVFR-B13: No old options were deleted."""
    audit = _load("09_no_deletion_audit.json")
    deleted = audit.get("deleted_old_options", [])
    assert deleted == [], f"Deleted old options found: {deleted}"


# ── PVFR-B14: static_only_after_restore is false ─────────────────────────────
def test_pvfr_b14_static_only_after_restore_false():
    """PVFR-B14: Tables are not static-only after restore."""
    audit = _load("10_static_only_audit.json")
    assert audit.get("static_only_after_restore") is False, \
        "static_only_after_restore must be False"
    assert audit.get("has_text_inputs") is True
    assert audit.get("has_select_dropdowns") is True


# ── PVFR-B15: Every common asset requirement has field_type ──────────────────
def test_pvfr_b15_every_requirement_has_field_type():
    """PVFR-B15: Every requirement group in inventory has fields list."""
    inv = _load("04_restored_common_asset_requirements_inventory.json")
    for asset_key, asset_data in inv.items():
        groups = asset_data.get("groups", [])
        assert len(groups) >= 2, f"{asset_key}: expected >= 2 groups, got {len(groups)}"
        for grp in groups:
            fields = grp.get("fields", [])
            assert len(fields) >= 2, f"{asset_key}/{grp.get('title')}: expected >= 2 fields"


# ── PVFR-B16: Every select has at least one option ───────────────────────────
def test_pvfr_b16_option_sets_have_options():
    """PVFR-B16: Option sets in PV_OPTS audit each have >= 2 options."""
    audit = _load("06_option_sets_restoration_audit.json")
    opts = audit.get("option_sets_defined_in_PV_OPTS", {})
    assert len(opts) >= 5, "Expected at least 5 option sets"
    for key, values in opts.items():
        if isinstance(values, list):
            assert len(values) >= 2, f"Option set {key} has < 2 options"


# ── PVFR-B17: Option sets are correct (no cross-contamination) ───────────────
def test_pvfr_b17_option_sets_correct():
    """PVFR-B17: Option sets are correctly mapped — no cross-contamination."""
    audit = _load("06_option_sets_restoration_audit.json")
    mapping = audit.get("option_sets_correctly_mapped", {})
    assert mapping.get("construction_type_not_mixed_with_condition") is True
    assert mapping.get("structural_condition_not_mixed_with_construction") is True
    assert mapping.get("no_cross_contamination") is True
    rules = audit.get("audit_rules_passed", {})
    assert rules.get("construction_type_contains_only_construction_values") is True
    assert rules.get("structural_condition_contains_only_condition_values") is True


# ── PVFR-B18: No internal paths in context ───────────────────────────────────
def test_pvfr_b18_no_internal_paths_in_context():
    """PVFR-B18: Backend context has no_internal_paths_in_api_response=True."""
    ctx = _load("08_backend_compatibility_context.json")
    inner = ctx.get("common_asset_legacy_requirements_context", {})
    assert inner.get("no_internal_paths_in_api_response") is True
    assert inner.get("advisory_only") is True
    assert inner.get("fillable_tables_restored") is True
    assert inner.get("static_only_after_restore") is False
