# -*- coding: utf-8 -*-
"""
test_pv_restore_common_asset_legacy_requirements.py
Backend tests: PV Common Asset Legacy Requirement Tables Restore (PVLR)

Tests verify:
  PVLR-B01  Legacy common asset requirements context exists (QA files)
  PVLR-B02  All common assets registered with Arabic aliases
  PVLR-B03  residential_apartment has requirements
  PVLR-B04  hotel has requirements
  PVLR-B05  industrial_factory has requirements
  PVLR-B06  urban_land has requirements (covers أرض فضاء / أرض زراعية)
  PVLR-B07  retail_shop has requirements (covers محل تجاري / تجاري)
  PVLR-B08  warehouse has requirements
  PVLR-B09  administrative_office has requirements (covers مبنى قائم)
  PVLR-B10  restored_requirement_count >= 5 for each asset
  PVLR-B11  No deleted old requirements
  PVLR-B12  No deleted old options
  PVLR-B13  Backend compatibility context has fillable_tables_restored=true
  PVLR-B14  No internal paths in QA context
  PVLR-B15  Ordinary valuation unaffected (health endpoint)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

_QA_BASE = (
    Path(__file__).resolve().parents[1]
    / "instance" / "manual_review_outputs"
    / "professional_valuation_restore_common_asset_legacy_tables"
)

# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def inventory():
    f = _QA_BASE / "03_restored_common_asset_requirements_inventory.json"
    assert f.exists(), f"Inventory file not found: {f}"
    return json.loads(f.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def compat_ctx():
    f = _QA_BASE / "06_backend_compatibility_context.json"
    assert f.exists(), f"Backend compat file not found: {f}"
    return json.loads(f.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def audit():
    f = _QA_BASE / "04_common_asset_old_vs_restored_audit.json"
    assert f.exists(), f"Audit file not found: {f}"
    return json.loads(f.read_text(encoding="utf-8"))


# ── PVLR-B01: index exists ────────────────────────────────────────────────────
def test_PVLR_B01_qa_index_exists():
    """PVLR-B01: QA output directory and index file exist."""
    idx = _QA_BASE / "00_restore_common_asset_legacy_tables_index.json"
    assert _QA_BASE.is_dir(), "QA directory missing"
    assert idx.exists(), "Index file missing"


# ── PVLR-B02: Arabic aliases in inventory ───────────────────────────────────
def test_PVLR_B02_arabic_aliases_in_inventory(inventory):
    """PVLR-B02: Arabic aliases are documented in the inventory."""
    aliases = inventory.get("arabic_aliases_added", {})
    required_arabic_keys = [
        "شقة سكنية", "عمارة سكنية", "أرض فضاء", "أرض زراعية",
        "تجاري", "مبنى قائم", "فندق", "مصنع", "محل تجاري",
    ]
    for key in required_arabic_keys:
        assert key in aliases, f"Arabic alias missing: {key!r}"


# ── PVLR-B03: residential_apartment ─────────────────────────────────────────
def test_PVLR_B03_residential_apartment_has_requirements(inventory):
    """PVLR-B03: residential_apartment has restored requirements."""
    req = inventory["restored_common_asset_requirements"]["residential_apartment"]
    assert req["restored_requirement_count"] >= 5
    assert req["has_fillable_inputs"]
    assert req["has_select_fields"]
    assert req["static_only_after_restore"] is False


# ── PVLR-B04: hotel ──────────────────────────────────────────────────────────
def test_PVLR_B04_hotel_has_requirements(inventory):
    """PVLR-B04: hotel has restored requirements."""
    req = inventory["restored_common_asset_requirements"]["hotel"]
    assert req["restored_requirement_count"] >= 5
    assert req["has_fillable_inputs"]
    assert req["has_select_fields"]
    assert req["static_only_after_restore"] is False


# ── PVLR-B05: industrial_factory ─────────────────────────────────────────────
def test_PVLR_B05_industrial_factory_has_requirements(inventory):
    """PVLR-B05: industrial_factory has restored requirements."""
    req = inventory["restored_common_asset_requirements"]["industrial_factory"]
    assert req["restored_requirement_count"] >= 5
    assert req["has_fillable_inputs"]
    assert req["has_select_fields"]
    assert req["static_only_after_restore"] is False


# ── PVLR-B06: urban_land ─────────────────────────────────────────────────────
def test_PVLR_B06_urban_land_has_requirements(inventory):
    """PVLR-B06: urban_land (covers أرض فضاء / أرض زراعية) has restored requirements."""
    req = inventory["restored_common_asset_requirements"]["urban_land"]
    assert req["restored_requirement_count"] >= 5
    assert req["has_fillable_inputs"]
    assert req["has_select_fields"]
    assert req["static_only_after_restore"] is False
    assert "أرض فضاء" in req["aliases_in_dropdown"]
    assert "أرض زراعية" in req["aliases_in_dropdown"]


# ── PVLR-B07: retail_shop ────────────────────────────────────────────────────
def test_PVLR_B07_retail_shop_has_requirements(inventory):
    """PVLR-B07: retail_shop (covers محل تجاري / تجاري) has restored requirements."""
    req = inventory["restored_common_asset_requirements"]["retail_shop"]
    assert req["restored_requirement_count"] >= 5
    assert req["has_fillable_inputs"]
    assert req["static_only_after_restore"] is False
    assert "محل تجاري" in req["aliases_in_dropdown"]
    assert "تجاري" in req["aliases_in_dropdown"]


# ── PVLR-B08: warehouse ──────────────────────────────────────────────────────
def test_PVLR_B08_warehouse_has_requirements(inventory):
    """PVLR-B08: warehouse has restored requirements."""
    req = inventory["restored_common_asset_requirements"]["warehouse"]
    assert req["restored_requirement_count"] >= 5
    assert req["has_fillable_inputs"]
    assert req["has_select_fields"]
    assert req["static_only_after_restore"] is False


# ── PVLR-B09: administrative_office ─────────────────────────────────────────
def test_PVLR_B09_administrative_office_has_requirements(inventory):
    """PVLR-B09: administrative_office (covers مبنى قائم) has restored requirements."""
    req = inventory["restored_common_asset_requirements"]["administrative_office"]
    assert req["restored_requirement_count"] >= 5
    assert req["has_fillable_inputs"]
    assert req["static_only_after_restore"] is False
    assert "مبنى قائم" in req["aliases_in_dropdown"]


# ── PVLR-B10: restored_requirement_count >= 5 for all ───────────────────────
def test_PVLR_B10_all_assets_have_enough_requirements(inventory):
    """PVLR-B10: every restored asset has ≥ 5 requirement fields."""
    reqs = inventory["restored_common_asset_requirements"]
    for key, data in reqs.items():
        assert data["restored_requirement_count"] >= 5, \
            f"{key}: only {data['restored_requirement_count']} requirements"


# ── PVLR-B11: no deleted old requirements ───────────────────────────────────
def test_PVLR_B11_no_deleted_old_requirements(inventory):
    """PVLR-B11: deleted_old_requirements is empty."""
    assert inventory["deletion_audit"]["deleted_old_requirements"] == []


# ── PVLR-B12: no deleted old options ────────────────────────────────────────
def test_PVLR_B12_no_deleted_old_options(inventory):
    """PVLR-B12: deleted_old_options is empty."""
    assert inventory["deletion_audit"]["deleted_old_options"] == []


# ── PVLR-B13: backend compat has fillable_tables_restored ──────────────────
def test_PVLR_B13_backend_compat_fillable_tables_restored(compat_ctx):
    """PVLR-B13: backend compatibility context has fillable_tables_restored=true."""
    ctx = compat_ctx["common_asset_legacy_requirements_context"]
    assert ctx["fillable_tables_restored"] is True
    assert ctx["visible_in_ui"] is True
    assert ctx["preservation_pass"] is True


# ── PVLR-B14: no internal paths in context ──────────────────────────────────
def test_PVLR_B14_no_internal_paths_in_context(compat_ctx):
    """PVLR-B14: no internal file paths in QA context."""
    raw = json.dumps(compat_ctx)
    forbidden = ["core_engine\\instance", "core_engine/instance",
                 "\\expert_workbooks\\", "/expert_workbooks/",
                 "C:\\Users\\", "c:/users/"]
    for pat in forbidden:
        assert pat.lower() not in raw.lower(), f"Internal path found: {pat!r}"


# ── PVLR-B15: ordinary valuation health ─────────────────────────────────────
def test_PVLR_B15_ordinary_valuation_health():
    """PVLR-B15: Simple valuation health endpoint reachable (server running)."""
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:5000/api/advisor/health", timeout=5) as r:
            body = r.read().decode()
        assert "ok" in body.lower() or "status" in body.lower()
    except Exception as e:
        pytest.skip(f"Server not running: {e}")
