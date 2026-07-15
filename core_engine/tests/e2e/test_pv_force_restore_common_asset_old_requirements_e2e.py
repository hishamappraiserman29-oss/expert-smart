# -*- coding: utf-8 -*-
"""
test_pv_force_restore_common_asset_old_requirements_e2e.py
Playwright E2E tests: Force Restore Old Common Asset Requirement Tables (PVFR-E)

Tests verify that the restored common asset fillable tables are visible in the
browser and that users can interact with them (fill fields, select options).

Tests:
  PVFR-E01  Professional Valuation page opens
  PVFR-E02  Section 2 asset type selection visible
  PVFR-E03  Common asset selector visible
  PVFR-E04  Select residential_apartment → fillable panel appears
  PVFR-E05  Panel title is 'متطلبات التقييم للأصول الشائعة'
  PVFR-E06  Residential apartment table has >= 8 rows
  PVFR-E07  Rows contain editable inputs/selects
  PVFR-E08  Fill 3 fields in residential_apartment
  PVFR-E09  Select residential_villa → fillable panel appears
  PVFR-E10  Villa table has >= 8 rows
  PVFR-E11  Fill 3 fields in residential_villa
  PVFR-E12  Select retail_shop → fillable panel appears
  PVFR-E13  Retail shop table has >= 5 rows
  PVFR-E14  Fill 3 fields in retail_shop
  PVFR-E15  Select industrial_factory → fillable panel appears
  PVFR-E16  Factory table has >= 8 rows
  PVFR-E17  Fill 3 fields in industrial_factory
  PVFR-E18  Select vacant_land → fillable panel appears
  PVFR-E19  Land table has >= 5 rows
  PVFR-E20  Fill 3 fields in vacant_land
  PVFR-E21  Select administrative_office → fillable panel appears
  PVFR-E22  Office table has >= 5 rows
  PVFR-E23  Verify static-only text is not used
  PVFR-E24  Verify option sets are correct (construction_type dropdown present)
  PVFR-E25  Verify no internal paths in DOM
  PVFR-E26  Capture screenshots (6 required)
"""
from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

# ── Paths ─────────────────────────────────────────────────────────────────────
_QA_DIR = Path(__file__).parent.parent.parent / "instance" / "manual_review_outputs" / \
    "professional_valuation_force_restore_common_asset_old_requirements"
_QA_DIR.mkdir(parents=True, exist_ok=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _go(page: Page, live_server: str) -> None:
    page.goto(live_server)
    page.wait_for_selector('[data-testid="professional-wizard"]', timeout=15000)


def _ws(page: Page):
    return page.locator("#ws-professional")


def _asset_select(page: Page):
    return _ws(page).locator("#asset-type")


def _req_panel(page: Page):
    return _ws(page).locator("#pvr-vis-asset-requirements-panel")


def _car_body(page: Page):
    return _ws(page).locator("#pvr-vis-car-body")


def _select_asset(page: Page, value: str) -> None:
    sel = _asset_select(page)
    sel.select_option(value=value)
    page.wait_for_timeout(600)


def _count_rows(page: Page) -> int:
    return _car_body(page).locator('[data-testid="pro-val-common-asset-requirement-row"]').count()


def _panel_title(page: Page) -> str:
    return _ws(page).locator("#pvr-vis-req-title").text_content() or ""


# ── PVFR-E01: Page opens ──────────────────────────────────────────────────────
def test_pvfr_e01_page_opens(page: Page, live_server: str):
    """PVFR-E01: Professional Valuation page opens."""
    _go(page, live_server)
    expect(_ws(page)).to_be_visible()


# ── PVFR-E02: Section 2 visible ───────────────────────────────────────────────
def test_pvfr_e02_section2_visible(page: Page, live_server: str):
    """PVFR-E02: Section 2 asset type selection is visible."""
    _go(page, live_server)
    sec2 = _ws(page).locator('[data-testid="pro-val-section-asset-type-selection"]')
    expect(sec2).to_be_visible()


# ── PVFR-E03: Asset selector visible ─────────────────────────────────────────
def test_pvfr_e03_asset_selector_visible(page: Page, live_server: str):
    """PVFR-E03: Common asset type selector is visible."""
    _go(page, live_server)
    expect(_asset_select(page)).to_be_visible()


# ── PVFR-E04: Select residential_apartment → panel appears ───────────────────
def test_pvfr_e04_residential_apartment_panel_appears(page: Page, live_server: str):
    """PVFR-E04: Select residential_apartment → fillable panel appears."""
    _go(page, live_server)
    _select_asset(page, "residential_apartment")
    expect(_req_panel(page)).to_be_visible()


# ── PVFR-E05: Panel title is correct ─────────────────────────────────────────
def test_pvfr_e05_panel_title_correct(page: Page, live_server: str):
    """PVFR-E05: Panel title is 'متطلبات التقييم للأصول الشائعة'."""
    _go(page, live_server)
    _select_asset(page, "residential_apartment")
    title = _panel_title(page)
    assert "متطلبات" in title, f"Panel title does not contain 'متطلبات': '{title}'"


# ── PVFR-E06: Residential apartment >= 8 rows ────────────────────────────────
def test_pvfr_e06_residential_apartment_rows(page: Page, live_server: str):
    """PVFR-E06: Residential apartment table has >= 8 rows."""
    _go(page, live_server)
    _select_asset(page, "residential_apartment")
    count = _count_rows(page)
    assert count >= 8, f"Expected >= 8 rows for residential_apartment, got {count}"


# ── PVFR-E07: Rows have editable inputs ──────────────────────────────────────
def test_pvfr_e07_rows_have_editable_inputs(page: Page, live_server: str):
    """PVFR-E07: Rows contain editable inputs/selects (not static-only)."""
    _go(page, live_server)
    _select_asset(page, "residential_apartment")
    inputs = _car_body(page).locator("input, select, textarea").count()
    assert inputs >= 5, f"Expected >= 5 editable inputs, got {inputs}"


# ── PVFR-E08: Fill 3 fields in residential_apartment ─────────────────────────
def test_pvfr_e08_fill_residential_apartment(page: Page, live_server: str):
    """PVFR-E08: Fill 3 fields in residential_apartment."""
    _go(page, live_server)
    _select_asset(page, "residential_apartment")
    nums = _car_body(page).locator('input[type="number"]').all()
    assert len(nums) >= 3, f"Expected >= 3 number inputs, got {len(nums)}"
    nums[0].fill("120")
    nums[1].fill("100")
    nums[2].fill("3")
    assert nums[0].input_value() == "120"
    assert nums[1].input_value() == "100"
    assert nums[2].input_value() == "3"


# ── PVFR-E09: Select residential_villa → panel appears ───────────────────────
def test_pvfr_e09_villa_panel_appears(page: Page, live_server: str):
    """PVFR-E09: Select residential_villa → fillable panel appears."""
    _go(page, live_server)
    _select_asset(page, "residential_villa")
    expect(_req_panel(page)).to_be_visible()


# ── PVFR-E10: Villa >= 8 rows ─────────────────────────────────────────────────
def test_pvfr_e10_villa_rows(page: Page, live_server: str):
    """PVFR-E10: Villa table has >= 8 rows (aliased to residential_apartment)."""
    _go(page, live_server)
    _select_asset(page, "residential_villa")
    count = _count_rows(page)
    assert count >= 8, f"Expected >= 8 rows for residential_villa, got {count}"


# ── PVFR-E11: Fill 3 fields in villa ─────────────────────────────────────────
def test_pvfr_e11_fill_villa(page: Page, live_server: str):
    """PVFR-E11: Fill 3 fields in residential_villa."""
    _go(page, live_server)
    _select_asset(page, "residential_villa")
    nums = _car_body(page).locator('input[type="number"]').all()
    assert len(nums) >= 3
    nums[0].fill("350")
    nums[1].fill("280")
    nums[2].fill("4")
    assert nums[0].input_value() == "350"


# ── PVFR-E12: Retail shop panel appears ──────────────────────────────────────
def test_pvfr_e12_retail_shop_panel_appears(page: Page, live_server: str):
    """PVFR-E12: Select retail_shop → fillable panel appears."""
    _go(page, live_server)
    _select_asset(page, "retail_shop")
    expect(_req_panel(page)).to_be_visible()


# ── PVFR-E13: Retail shop >= 5 rows ──────────────────────────────────────────
def test_pvfr_e13_retail_shop_rows(page: Page, live_server: str):
    """PVFR-E13: Retail shop table has >= 5 rows."""
    _go(page, live_server)
    _select_asset(page, "retail_shop")
    count = _count_rows(page)
    assert count >= 5, f"Expected >= 5 rows for retail_shop, got {count}"


# ── PVFR-E14: Fill 3 fields in retail_shop ───────────────────────────────────
def test_pvfr_e14_fill_retail_shop(page: Page, live_server: str):
    """PVFR-E14: Fill 3 fields in retail_shop."""
    _go(page, live_server)
    _select_asset(page, "retail_shop")
    nums = _car_body(page).locator('input[type="number"]').all()
    texts = _car_body(page).locator('input[type="text"]').all()
    assert len(nums) >= 2
    nums[0].fill("75")
    nums[1].fill("60")
    if len(texts) >= 1:
        texts[0].fill("محل بدائع")
    assert nums[0].input_value() == "75"


# ── PVFR-E15: Factory panel appears ──────────────────────────────────────────
def test_pvfr_e15_factory_panel_appears(page: Page, live_server: str):
    """PVFR-E15: Select industrial_factory → fillable panel appears."""
    _go(page, live_server)
    _select_asset(page, "industrial_factory")
    expect(_req_panel(page)).to_be_visible()


# ── PVFR-E16: Factory >= 8 rows ───────────────────────────────────────────────
def test_pvfr_e16_factory_rows(page: Page, live_server: str):
    """PVFR-E16: Factory table has >= 8 rows."""
    _go(page, live_server)
    _select_asset(page, "industrial_factory")
    count = _count_rows(page)
    assert count >= 8, f"Expected >= 8 rows for industrial_factory, got {count}"


# ── PVFR-E17: Fill 3 fields in factory ───────────────────────────────────────
def test_pvfr_e17_fill_factory(page: Page, live_server: str):
    """PVFR-E17: Fill 3 fields in industrial_factory."""
    _go(page, live_server)
    _select_asset(page, "industrial_factory")
    nums = _car_body(page).locator('input[type="number"]').all()
    assert len(nums) >= 3
    nums[0].fill("5000")
    nums[1].fill("3500")
    nums[2].fill("8")
    assert nums[0].input_value() == "5000"


# ── PVFR-E18: Vacant land panel appears ──────────────────────────────────────
def test_pvfr_e18_vacant_land_panel_appears(page: Page, live_server: str):
    """PVFR-E18: Select vacant_land → fillable panel appears."""
    _go(page, live_server)
    _select_asset(page, "vacant_land")
    expect(_req_panel(page)).to_be_visible()


# ── PVFR-E19: Land >= 5 rows ──────────────────────────────────────────────────
def test_pvfr_e19_vacant_land_rows(page: Page, live_server: str):
    """PVFR-E19: Vacant land table has >= 5 rows."""
    _go(page, live_server)
    _select_asset(page, "vacant_land")
    count = _count_rows(page)
    assert count >= 5, f"Expected >= 5 rows for vacant_land, got {count}"


# ── PVFR-E20: Fill 3 fields in vacant_land ───────────────────────────────────
def test_pvfr_e20_fill_vacant_land(page: Page, live_server: str):
    """PVFR-E20: Fill 3 fields in vacant_land."""
    _go(page, live_server)
    _select_asset(page, "vacant_land")
    nums = _car_body(page).locator('input[type="number"]').all()
    assert len(nums) >= 3
    nums[0].fill("2500")
    nums[1].fill("50")
    nums[2].fill("80")
    assert nums[0].input_value() == "2500"


# ── PVFR-E21: Administrative office panel appears ────────────────────────────
def test_pvfr_e21_office_panel_appears(page: Page, live_server: str):
    """PVFR-E21: Select administrative_office → fillable panel appears."""
    _go(page, live_server)
    _select_asset(page, "administrative_office")
    expect(_req_panel(page)).to_be_visible()


# ── PVFR-E22: Office >= 5 rows ───────────────────────────────────────────────
def test_pvfr_e22_office_rows(page: Page, live_server: str):
    """PVFR-E22: Administrative office table has >= 5 rows."""
    _go(page, live_server)
    _select_asset(page, "administrative_office")
    count = _count_rows(page)
    assert count >= 5, f"Expected >= 5 rows for administrative_office, got {count}"


# ── PVFR-E23: Static-only text not used ──────────────────────────────────────
def test_pvfr_e23_not_static_only(page: Page, live_server: str):
    """PVFR-E23: Tables are NOT static-only — have real editable inputs."""
    _go(page, live_server)
    _select_asset(page, "residential_apartment")
    inputs_count = _car_body(page).locator("input, select, textarea").count()
    assert inputs_count >= 5, \
        f"Expected >= 5 editable controls (not static-only), got {inputs_count}"


# ── PVFR-E24: Option sets correct ────────────────────────────────────────────
def test_pvfr_e24_option_sets_correct(page: Page, live_server: str):
    """PVFR-E24: construction_type dropdown has construction values (not condition values)."""
    _go(page, live_server)
    _select_asset(page, "industrial_factory")
    # Find the construction_type select by data-backend-key
    ct_sel = _car_body(page).locator('[data-backend-key="construction_type"]')
    expect(ct_sel).to_be_visible()
    ct_html = ct_sel.inner_html()
    # Should have concrete/steel/wood as options, not excellent/good/poor
    assert "خرساني" in ct_html or "concrete" in ct_html, \
        "construction_type missing concrete option"
    assert "ممتاز" not in ct_html, \
        "construction_type incorrectly contains structural_condition value 'ممتاز'"


# ── PVFR-E25: No internal paths in DOM ───────────────────────────────────────
def test_pvfr_e25_no_internal_paths_in_dom(page: Page, live_server: str):
    """PVFR-E25: No internal file paths appear in DOM content."""
    _go(page, live_server)
    _select_asset(page, "residential_apartment")
    body_html = page.locator("body").inner_html()
    bad_patterns = [
        r"C:\\Users", r"/home/", r"C:/Users",
        "core_engine/instance/manual_review_outputs",
    ]
    for pattern in bad_patterns:
        assert pattern not in body_html, \
            f"Internal path '{pattern}' found in DOM"


# ── PVFR-E26: Capture screenshots ────────────────────────────────────────────
def test_pvfr_e26_capture_screenshots(page: Page, live_server: str):
    """PVFR-E26: Capture 6 screenshots proving the restored tables are visible."""
    _go(page, live_server)

    # Screenshot 1: residential_apartment
    _select_asset(page, "residential_apartment")
    page.wait_for_timeout(800)
    shot1 = _QA_DIR / "common_asset_residential_apartment_restored.png"
    page.screenshot(path=str(shot1), full_page=False)
    assert shot1.exists() and shot1.stat().st_size > 10000, \
        "residential_apartment screenshot too small"

    # Screenshot 2: villa
    _select_asset(page, "residential_villa")
    page.wait_for_timeout(600)
    shot2 = _QA_DIR / "common_asset_villa_restored.png"
    page.screenshot(path=str(shot2), full_page=False)
    assert shot2.exists() and shot2.stat().st_size > 10000, \
        "villa screenshot too small"

    # Screenshot 3: retail_shop
    _select_asset(page, "retail_shop")
    page.wait_for_timeout(600)
    shot3 = _QA_DIR / "common_asset_retail_shop_restored.png"
    page.screenshot(path=str(shot3), full_page=False)
    assert shot3.exists() and shot3.stat().st_size > 10000, \
        "retail_shop screenshot too small"

    # Screenshot 4: factory
    _select_asset(page, "industrial_factory")
    page.wait_for_timeout(600)
    shot4 = _QA_DIR / "common_asset_factory_restored.png"
    page.screenshot(path=str(shot4), full_page=False)
    assert shot4.exists() and shot4.stat().st_size > 10000, \
        "factory screenshot too small"

    # Screenshot 5: vacant_land
    _select_asset(page, "vacant_land")
    page.wait_for_timeout(600)
    shot5 = _QA_DIR / "common_asset_vacant_land_restored.png"
    page.screenshot(path=str(shot5), full_page=False)
    assert shot5.exists() and shot5.stat().st_size > 10000, \
        "vacant_land screenshot too small"

    # Screenshot 6: option sets (factory construction_type select visible)
    _select_asset(page, "industrial_factory")
    page.wait_for_timeout(600)
    # Scroll to the requirements panel to show option sets
    _req_panel(page).scroll_into_view_if_needed()
    page.wait_for_timeout(400)
    shot6 = _QA_DIR / "common_asset_option_sets_restored.png"
    page.screenshot(path=str(shot6), full_page=False)
    assert shot6.exists() and shot6.stat().st_size > 10000, \
        "option_sets screenshot too small"

    assert shot1.exists()
    assert shot2.exists()
    assert shot3.exists()
    assert shot4.exists()
    assert shot5.exists()
    assert shot6.exists()
