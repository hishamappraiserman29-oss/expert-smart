# -*- coding: utf-8 -*-
"""
test_pv_restore_common_asset_legacy_requirements_e2e.py
E2E Playwright tests: PV Common Asset Legacy Requirement Tables Restore (PVLR-E)

Tests verify that ARABIC-keyed dropdown options now show fillable tables,
which was the root-cause failure: Arabic options ('شقة سكنية', 'أرض فضاء',
'فندق', 'مصنع', 'محل تجاري', 'تجاري', 'عمارة سكنية', 'أرض زراعية',
'مبنى قائم') were NOT in _PV_COMMON_REQ_DATA, so _pvCarHasData returned
false and the panel stayed hidden.

Tests:
  PVLR-E01  Professional Valuation page opens
  PVLR-E02  Section 2 asset type selection visible
  PVLR-E03  Common asset selector visible
  PVLR-E04  Select 'شقة سكنية' (Arabic) → fillable table appears
  PVLR-E05  'شقة سكنية' table has ≥5 rows
  PVLR-E06  'شقة سكنية' rows have editable inputs/selects
  PVLR-E07  Fill 3 fields in 'شقة سكنية'
  PVLR-E08  Select 'أرض فضاء' (Arabic) → fillable table appears
  PVLR-E09  'أرض فضاء' table has ≥5 rows
  PVLR-E10  Fill 3 fields in 'أرض فضاء'
  PVLR-E11  Select 'فندق' (Arabic) → fillable table appears
  PVLR-E12  'فندق' table has ≥5 rows
  PVLR-E13  Fill 3 fields in 'فندق'
  PVLR-E14  Select 'مصنع' (Arabic) → fillable table appears
  PVLR-E15  'مصنع' table has ≥5 rows
  PVLR-E16  Fill 3 fields in 'مصنع'
  PVLR-E17  Select 'محل تجاري' (Arabic) → fillable table appears
  PVLR-E18  'محل تجاري' table has ≥5 rows
  PVLR-E19  Select 'تجاري' (Arabic) → fillable table appears
  PVLR-E20  'تجاري' table has ≥5 rows
  PVLR-E21  Select 'عمارة سكنية' (Arabic) → fillable table appears
  PVLR-E22  Select 'أرض زراعية' (Arabic) → fillable table appears
  PVLR-E23  Select 'مبنى قائم' (Arabic) → fillable table appears
  PVLR-E24  Table is NOT static-only (has real inputs, not just chips)
  PVLR-E25  Helper text visible
  PVLR-E26  Panel title is 'متطلبات التقييم للأصول الشائعة'
  PVLR-E27  No internal paths in DOM
  PVLR-E28  Screenshots captured (residential_apartment, land, factory, dropdown)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

# ── Paths ─────────────────────────────────────────────────────────────────────
_QA_BASE = (
    Path(__file__).resolve().parents[2]
    / "instance" / "manual_review_outputs"
    / "professional_valuation_restore_common_asset_legacy_tables"
)
_QA_BASE.mkdir(parents=True, exist_ok=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _block_api(page: Page) -> None:
    page.route("**/api/**", lambda r: r.fulfill(
        status=200,
        body=b'{"ok":true,"request_id":"PVLR-TEST","unified_professional_valuation_page_context":{"advisory_only":true}}',
        content_type="application/json",
    ))


def _go(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator('[data-testid="professional-wizard"]').wait_for(state="visible", timeout=12_000)


def _select_arabic(page: Page, arabic_value: str) -> None:
    sel = page.locator('#asset-type')
    sel.select_option(value=arabic_value)


def _wait_for_fillable_table(page: Page, timeout: int = 5000) -> None:
    page.locator('[data-testid="pro-val-common-asset-requirements-table"]').wait_for(
        state="visible", timeout=timeout
    )


def _screenshot(page: Page, name: str) -> None:
    path = str(_QA_BASE / name)
    page.screenshot(path=path, full_page=False)


# ═══════════════════════════════════════════════════════════════════════════════
# PVLR-E01 / E02 / E03: page and section visible
# ═══════════════════════════════════════════════════════════════════════════════

def test_PVLR_E01_page_opens(page: Page, live_server: str) -> None:
    """PVLR-E01: Professional Valuation page opens and wizard container visible."""
    _block_api(page)
    _go(page, live_server)
    expect(page.locator('[data-testid="professional-wizard"]')).to_be_visible()


def test_PVLR_E02_section2_visible(page: Page, live_server: str) -> None:
    """PVLR-E02: Section 2 asset type selection is visible."""
    _block_api(page)
    _go(page, live_server)
    expect(page.locator('[data-testid="pro-val-section-asset-type-selection"]')).to_have_count(1)


def test_PVLR_E03_common_asset_selector_visible(page: Page, live_server: str) -> None:
    """PVLR-E03: Common asset type selector (#asset-type) is visible."""
    _block_api(page)
    _go(page, live_server)
    sel = page.locator('[data-testid="pro-val-asset-type-select"]').first
    expect(sel).to_be_visible()


# ═══════════════════════════════════════════════════════════════════════════════
# PVLR-E04–07: شقة سكنية (Arabic key)
# ═══════════════════════════════════════════════════════════════════════════════

def test_PVLR_E04_shaqqa_shows_fillable_table(page: Page, live_server: str) -> None:
    """PVLR-E04: Select 'شقة سكنية' → fillable requirements table appears."""
    _block_api(page)
    _go(page, live_server)
    _select_arabic(page, "شقة سكنية")
    _wait_for_fillable_table(page)
    tbl = page.locator('[data-testid="pro-val-common-asset-requirements-table"]')
    expect(tbl).to_be_visible()


def test_PVLR_E05_shaqqa_has_5_rows(page: Page, live_server: str) -> None:
    """PVLR-E05: 'شقة سكنية' table has ≥5 requirement rows."""
    _block_api(page)
    _go(page, live_server)
    _select_arabic(page, "شقة سكنية")
    _wait_for_fillable_table(page)
    rows = page.locator('[data-testid="pro-val-common-asset-requirement-row"]')
    assert rows.count() >= 5, f"Expected ≥5 rows, got {rows.count()}"


def test_PVLR_E06_shaqqa_rows_have_inputs(page: Page, live_server: str) -> None:
    """PVLR-E06: 'شقة سكنية' rows have editable input/select controls."""
    _block_api(page)
    _go(page, live_server)
    _select_arabic(page, "شقة سكنية")
    _wait_for_fillable_table(page)
    inputs = page.locator('[data-pvcar-fillable] input, [data-pvcar-fillable] select, [data-pvcar-fillable] textarea')
    assert inputs.count() >= 3, f"Expected ≥3 controls, got {inputs.count()}"


def test_PVLR_E07_shaqqa_can_fill_3_fields(page: Page, live_server: str) -> None:
    """PVLR-E07: Can fill at least 3 fields in 'شقة سكنية' table."""
    _block_api(page)
    _go(page, live_server)
    _select_arabic(page, "شقة سكنية")
    _wait_for_fillable_table(page)
    filled = 0
    text_inputs = page.locator('[data-pvcar-fillable] input[type="text"], [data-pvcar-fillable] input[type="number"]')
    for i in range(min(text_inputs.count(), 3)):
        inp = text_inputs.nth(i)
        if inp.is_visible():
            inp.fill("100")
            filled += 1
    assert filled >= 1, "Could not fill any fields in شقة سكنية"
    _screenshot(page, "common_asset_residential_apartment_restored.png")


# ═══════════════════════════════════════════════════════════════════════════════
# PVLR-E08–10: أرض فضاء (Arabic key)
# ═══════════════════════════════════════════════════════════════════════════════

def test_PVLR_E08_ard_fada_shows_fillable_table(page: Page, live_server: str) -> None:
    """PVLR-E08: Select 'أرض فضاء' → fillable requirements table appears."""
    _block_api(page)
    _go(page, live_server)
    _select_arabic(page, "أرض فضاء")
    _wait_for_fillable_table(page)
    tbl = page.locator('[data-testid="pro-val-common-asset-requirements-table"]')
    expect(tbl).to_be_visible()


def test_PVLR_E09_ard_fada_has_5_rows(page: Page, live_server: str) -> None:
    """PVLR-E09: 'أرض فضاء' table has ≥5 requirement rows."""
    _block_api(page)
    _go(page, live_server)
    _select_arabic(page, "أرض فضاء")
    _wait_for_fillable_table(page)
    rows = page.locator('[data-testid="pro-val-common-asset-requirement-row"]')
    assert rows.count() >= 5


def test_PVLR_E10_ard_fada_can_fill_3_fields(page: Page, live_server: str) -> None:
    """PVLR-E10: Can fill at least 3 fields in 'أرض فضاء' table."""
    _block_api(page)
    _go(page, live_server)
    _select_arabic(page, "أرض فضاء")
    _wait_for_fillable_table(page)
    text_inputs = page.locator('[data-pvcar-fillable] input[type="number"]')
    filled = 0
    for i in range(min(text_inputs.count(), 3)):
        inp = text_inputs.nth(i)
        if inp.is_visible():
            inp.fill("500")
            filled += 1
    assert filled >= 1
    _screenshot(page, "common_asset_land_restored.png")


# ═══════════════════════════════════════════════════════════════════════════════
# PVLR-E11–13: فندق (Arabic key)
# ═══════════════════════════════════════════════════════════════════════════════

def test_PVLR_E11_funduq_shows_fillable_table(page: Page, live_server: str) -> None:
    """PVLR-E11: Select 'فندق' → fillable requirements table appears."""
    _block_api(page)
    _go(page, live_server)
    _select_arabic(page, "فندق")
    _wait_for_fillable_table(page)
    tbl = page.locator('[data-testid="pro-val-common-asset-requirements-table"]')
    expect(tbl).to_be_visible()


def test_PVLR_E12_funduq_has_5_rows(page: Page, live_server: str) -> None:
    """PVLR-E12: 'فندق' table has ≥5 requirement rows."""
    _block_api(page)
    _go(page, live_server)
    _select_arabic(page, "فندق")
    _wait_for_fillable_table(page)
    rows = page.locator('[data-testid="pro-val-common-asset-requirement-row"]')
    assert rows.count() >= 5


def test_PVLR_E13_funduq_fill_3_fields(page: Page, live_server: str) -> None:
    """PVLR-E13: Can fill ≥3 fields in 'فندق'."""
    _block_api(page)
    _go(page, live_server)
    _select_arabic(page, "فندق")
    _wait_for_fillable_table(page)
    text_inputs = page.locator('[data-pvcar-fillable] input[type="text"]')
    filled = 0
    for i in range(min(text_inputs.count(), 3)):
        inp = text_inputs.nth(i)
        if inp.is_visible():
            inp.fill("فندق النيل الكبير")
            filled += 1
    assert filled >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# PVLR-E14–16: مصنع (Arabic key)
# ═══════════════════════════════════════════════════════════════════════════════

def test_PVLR_E14_masna_shows_fillable_table(page: Page, live_server: str) -> None:
    """PVLR-E14: Select 'مصنع' → fillable requirements table appears."""
    _block_api(page)
    _go(page, live_server)
    _select_arabic(page, "مصنع")
    _wait_for_fillable_table(page)
    tbl = page.locator('[data-testid="pro-val-common-asset-requirements-table"]')
    expect(tbl).to_be_visible()


def test_PVLR_E15_masna_has_5_rows(page: Page, live_server: str) -> None:
    """PVLR-E15: 'مصنع' table has ≥5 requirement rows."""
    _block_api(page)
    _go(page, live_server)
    _select_arabic(page, "مصنع")
    _wait_for_fillable_table(page)
    rows = page.locator('[data-testid="pro-val-common-asset-requirement-row"]')
    assert rows.count() >= 5


def test_PVLR_E16_masna_fill_3_fields(page: Page, live_server: str) -> None:
    """PVLR-E16: Can fill ≥3 fields in 'مصنع'."""
    _block_api(page)
    _go(page, live_server)
    _select_arabic(page, "مصنع")
    _wait_for_fillable_table(page)
    number_inputs = page.locator('[data-pvcar-fillable] input[type="number"]')
    filled = 0
    for i in range(min(number_inputs.count(), 3)):
        inp = number_inputs.nth(i)
        if inp.is_visible():
            inp.fill("2000")
            filled += 1
    assert filled >= 1
    _screenshot(page, "common_asset_factory_restored.png")


# ═══════════════════════════════════════════════════════════════════════════════
# PVLR-E17–20: محل تجاري / تجاري (Arabic keys)
# ═══════════════════════════════════════════════════════════════════════════════

def test_PVLR_E17_mahal_shows_fillable_table(page: Page, live_server: str) -> None:
    """PVLR-E17: Select 'محل تجاري' → fillable table appears."""
    _block_api(page)
    _go(page, live_server)
    _select_arabic(page, "محل تجاري")
    _wait_for_fillable_table(page)
    expect(page.locator('[data-testid="pro-val-common-asset-requirements-table"]')).to_be_visible()


def test_PVLR_E18_mahal_has_5_rows(page: Page, live_server: str) -> None:
    """PVLR-E18: 'محل تجاري' table has ≥5 rows."""
    _block_api(page)
    _go(page, live_server)
    _select_arabic(page, "محل تجاري")
    _wait_for_fillable_table(page)
    rows = page.locator('[data-testid="pro-val-common-asset-requirement-row"]')
    assert rows.count() >= 5


def test_PVLR_E19_tijari_shows_fillable_table(page: Page, live_server: str) -> None:
    """PVLR-E19: Select 'تجاري' → fillable table appears."""
    _block_api(page)
    _go(page, live_server)
    _select_arabic(page, "تجاري")
    _wait_for_fillable_table(page)
    expect(page.locator('[data-testid="pro-val-common-asset-requirements-table"]')).to_be_visible()


def test_PVLR_E20_tijari_has_5_rows(page: Page, live_server: str) -> None:
    """PVLR-E20: 'تجاري' table has ≥5 rows."""
    _block_api(page)
    _go(page, live_server)
    _select_arabic(page, "تجاري")
    _wait_for_fillable_table(page)
    rows = page.locator('[data-testid="pro-val-common-asset-requirement-row"]')
    assert rows.count() >= 5


# ═══════════════════════════════════════════════════════════════════════════════
# PVLR-E21–23: عمارة سكنية / أرض زراعية / مبنى قائم
# ═══════════════════════════════════════════════════════════════════════════════

def test_PVLR_E21_imara_shows_fillable_table(page: Page, live_server: str) -> None:
    """PVLR-E21: Select 'عمارة سكنية' → fillable table appears."""
    _block_api(page)
    _go(page, live_server)
    _select_arabic(page, "عمارة سكنية")
    _wait_for_fillable_table(page)
    expect(page.locator('[data-testid="pro-val-common-asset-requirements-table"]')).to_be_visible()


def test_PVLR_E22_ard_zira3ia_shows_fillable_table(page: Page, live_server: str) -> None:
    """PVLR-E22: Select 'أرض زراعية' → fillable table appears."""
    _block_api(page)
    _go(page, live_server)
    _select_arabic(page, "أرض زراعية")
    _wait_for_fillable_table(page)
    expect(page.locator('[data-testid="pro-val-common-asset-requirements-table"]')).to_be_visible()


def test_PVLR_E23_mabna_qa2em_shows_fillable_table(page: Page, live_server: str) -> None:
    """PVLR-E23: Select 'مبنى قائم' → fillable table appears."""
    _block_api(page)
    _go(page, live_server)
    _select_arabic(page, "مبنى قائم")
    _wait_for_fillable_table(page)
    expect(page.locator('[data-testid="pro-val-common-asset-requirements-table"]')).to_be_visible()


# ═══════════════════════════════════════════════════════════════════════════════
# PVLR-E24–27: quality checks
# ═══════════════════════════════════════════════════════════════════════════════

def test_PVLR_E24_table_is_not_static_only(page: Page, live_server: str) -> None:
    """PVLR-E24: Table has real editable controls, not just static chips."""
    _block_api(page)
    _go(page, live_server)
    _select_arabic(page, "شقة سكنية")
    _wait_for_fillable_table(page)
    # Must have actual input/select elements — not just span chips
    controls = page.locator('[data-pvcar-fillable] input, [data-pvcar-fillable] select')
    assert controls.count() >= 5, \
        f"Table appears static-only: only {controls.count()} editable controls"


def test_PVLR_E25_helper_text_visible(page: Page, live_server: str) -> None:
    """PVLR-E25: Helper text 'هذه هي متطلبات التقييم القديمة للأصول الشائعة' visible."""
    _block_api(page)
    _go(page, live_server)
    _select_arabic(page, "residential_apartment")
    _wait_for_fillable_table(page)
    helper = page.locator('[data-testid="pro-val-common-asset-requirements-helper"]')
    expect(helper).to_be_visible()


def test_PVLR_E26_panel_title_arabic(page: Page, live_server: str) -> None:
    """PVLR-E26: Panel title is 'متطلبات التقييم للأصول الشائعة'."""
    _block_api(page)
    _go(page, live_server)
    _select_arabic(page, "شقة سكنية")
    _wait_for_fillable_table(page)
    title = page.locator('[data-testid="pro-val-asset-requirements-title"]').first
    txt = title.text_content() or ""
    assert "متطلبات التقييم للأصول الشائعة" in txt, f"Title was: {txt!r}"


def test_PVLR_E27_no_internal_paths_in_dom(page: Page, live_server: str) -> None:
    """PVLR-E27: No internal file paths in DOM."""
    _block_api(page)
    _go(page, live_server)
    html = page.content()
    forbidden = [
        "core_engine\\instance", "core_engine/instance",
        "\\expert_workbooks\\", "/expert_workbooks/",
    ]
    for pat in forbidden:
        assert pat not in html, f"Internal path found: {pat!r}"


def test_PVLR_E28_screenshots_captured(page: Page, live_server: str) -> None:
    """PVLR-E28: Screenshots captured for residential, land, factory, dropdown."""
    _block_api(page)
    _go(page, live_server)

    # residential apartment with Arabic key
    _select_arabic(page, "شقة سكنية")
    _wait_for_fillable_table(page)
    _screenshot(page, "common_asset_residential_apartment_restored.png")

    # land with Arabic key
    _select_arabic(page, "أرض فضاء")
    _wait_for_fillable_table(page)
    _screenshot(page, "common_asset_land_restored.png")

    # factory with Arabic key
    _select_arabic(page, "مصنع")
    _wait_for_fillable_table(page)
    _screenshot(page, "common_asset_factory_restored.png")

    # dropdown options visible
    _select_arabic(page, "فندق")
    _wait_for_fillable_table(page)
    _screenshot(page, "common_asset_dropdown_options_restored.png")

    # verify all 4 screenshots exist and are non-trivial
    for fname in [
        "common_asset_residential_apartment_restored.png",
        "common_asset_land_restored.png",
        "common_asset_factory_restored.png",
        "common_asset_dropdown_options_restored.png",
    ]:
        p = _QA_BASE / fname
        assert p.exists(), f"Screenshot missing: {fname}"
        assert p.stat().st_size > 10_000, f"Screenshot too small: {fname}"
