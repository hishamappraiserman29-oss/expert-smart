"""
PVCAR E2E Browser Tests — Professional Valuation Common Asset Requirements
Tests PVCAR-E01 through PVCAR-E30 using Playwright.
Validates fillable tables, correct select options, testids, and renderer behaviour.
"""
import pytest
from playwright.sync_api import Page, expect


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _goto_pv(page: Page, live_server: str) -> None:
    """Navigate to the Professional Valuation workspace via hash."""
    page.goto(f"{live_server}#professional-valuation", wait_until="domcontentloaded")
    page.locator('[data-testid="pro-val-workspace"]').wait_for(state="visible", timeout=10_000)


def _open_new_request(page: Page) -> None:
    """Click the new-request button to reveal the request form."""
    btn = page.locator('[data-testid="pro-val-new-request-button"]')
    if btn.is_visible(timeout=3000):
        btn.click()
        page.wait_for_timeout(400)


def _select_asset(page: Page, asset_type: str) -> None:
    """Select an asset type from #pvr-asset-type."""
    sel = page.locator('#pvr-asset-type')
    sel.wait_for(state="visible", timeout=6000)
    sel.select_option(asset_type)
    page.wait_for_timeout(600)


# ─────────────────────────────────────────────────────────────────────────────
# A. Page loads and workspace visible
# ─────────────────────────────────────────────────────────────────────────────

def test_PVCAR_E01_page_loads(page: Page, live_server: str) -> None:
    """Professional Valuation workspace loads without JS errors."""
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    _goto_pv(page, live_server)
    assert len(errors) == 0, f"JS errors on PV workspace load: {errors}"


def test_PVCAR_E02_new_request_button_visible(page: Page, live_server: str) -> None:
    """New request button is visible in the PV workspace."""
    _goto_pv(page, live_server)
    btn = page.locator('[data-testid="pro-val-new-request-button"]')
    expect(btn).to_be_visible()


def test_PVCAR_E03_asset_type_select_exists(page: Page, live_server: str) -> None:
    """Asset type select (#pvr-asset-type) is present and has options."""
    _goto_pv(page, live_server)
    _open_new_request(page)
    sel = page.locator('#pvr-asset-type')
    expect(sel).to_be_visible()
    count = sel.evaluate("el => el.options.length")
    assert count > 5, "Asset type select has too few options"


# ─────────────────────────────────────────────────────────────────────────────
# B. Common asset: Hotel — fillable table renders
# ─────────────────────────────────────────────────────────────────────────────

def test_PVCAR_E04_hotel_panel_appears(page: Page, live_server: str) -> None:
    """Selecting hotel shows the hotel requirements panel."""
    _goto_pv(page, live_server)
    _open_new_request(page)
    _select_asset(page, "hotel")
    panel = page.locator('[data-testid="pro-val-hotel-requirements-panel"]')
    expect(panel).to_be_visible()


def test_PVCAR_E05_hotel_fillable_panel_rendered(page: Page, live_server: str) -> None:
    """Selecting hotel renders pro-val-common-asset-requirements-panel."""
    _goto_pv(page, live_server)
    _open_new_request(page)
    _select_asset(page, "hotel")
    fp = page.locator('[data-testid="pro-val-common-asset-requirements-panel"]')
    expect(fp).to_be_visible()


def test_PVCAR_E06_hotel_requirements_table_rendered(page: Page, live_server: str) -> None:
    """Hotel fillable table testid pro-val-common-asset-requirements-table is present."""
    _goto_pv(page, live_server)
    _open_new_request(page)
    _select_asset(page, "hotel")
    table = page.locator('[data-testid="pro-val-common-asset-requirements-table"]')
    expect(table).to_be_visible()


def test_PVCAR_E07_hotel_requirement_rows_present(page: Page, live_server: str) -> None:
    """Hotel fillable table has at least 10 requirement rows."""
    _goto_pv(page, live_server)
    _open_new_request(page)
    _select_asset(page, "hotel")
    rows = page.locator('[data-testid="pro-val-common-asset-requirement-row"]')
    count = rows.count()
    assert count >= 10, f"Expected >=10 hotel requirement rows, got {count}"


def test_PVCAR_E08_hotel_requirement_labels_present(page: Page, live_server: str) -> None:
    """Hotel requirement rows have label cells."""
    _goto_pv(page, live_server)
    _open_new_request(page)
    _select_asset(page, "hotel")
    labels = page.locator('[data-testid="pro-val-common-asset-requirement-label"]')
    assert labels.count() >= 10


def test_PVCAR_E09_hotel_construction_type_select_correct_options(page: Page, live_server: str) -> None:
    """Hotel construction_type select has concrete/steel/wood options — NOT ممتا��/جيد."""
    _goto_pv(page, live_server)
    _open_new_request(page)
    _select_asset(page, "hotel")
    sel = page.locator('select[data-backend-key="construction_type"]').first
    expect(sel).to_be_visible()
    opts = sel.evaluate("el => Array.from(el.options).map(o => o.value)")
    assert "concrete" in opts, f"concrete missing from construction_type: {opts}"
    assert "steel" in opts, f"steel missing from construction_type: {opts}"
    assert "wood" in opts, f"wood missing from construction_type: {opts}"
    assert "excellent" not in opts, f"excellent must NOT be in construction_type: {opts}"


def test_PVCAR_E10_hotel_structural_condition_select_correct(page: Page, live_server: str) -> None:
    """Hotel structural_condition select has excellent/needs_maintenance — NOT concrete."""
    _goto_pv(page, live_server)
    _open_new_request(page)
    _select_asset(page, "hotel")
    sel = page.locator('select[data-backend-key="structural_condition"]').first
    expect(sel).to_be_visible()
    opts = sel.evaluate("el => Array.from(el.options).map(o => o.value)")
    assert "excellent" in opts
    assert "needs_maintenance" in opts
    assert "concrete" not in opts, "concrete should NOT be in structural_condition"


def test_PVCAR_E11_hotel_ownership_type_select_correct(page: Page, live_server: str) -> None:
    """Hotel ownership_type select has freehold, usufruct options."""
    _goto_pv(page, live_server)
    _open_new_request(page)
    _select_asset(page, "hotel")
    sel = page.locator('select[data-backend-key="ownership_type"]').first
    expect(sel).to_be_visible()
    opts = sel.evaluate("el => Array.from(el.options).map(o => o.value)")
    assert "freehold" in opts
    assert "usufruct" in opts


def test_PVCAR_E12_hotel_market_demand_select_correct(page: Page, live_server: str) -> None:
    """Hotel market_demand_level select has high/medium/low."""
    _goto_pv(page, live_server)
    _open_new_request(page)
    _select_asset(page, "hotel")
    sel = page.locator('select[data-backend-key="market_demand_level"]').first
    expect(sel).to_be_visible()
    opts = sel.evaluate("el => Array.from(el.options).map(o => o.value)")
    assert "high" in opts
    assert "medium" in opts
    assert "low" in opts


def test_PVCAR_E13_hotel_save_button_present(page: Page, live_server: str) -> None:
    """Hotel requirements panel has pro-val-common-asset-requirements-save-button."""
    _goto_pv(page, live_server)
    _open_new_request(page)
    _select_asset(page, "hotel")
    btn = page.locator('[data-testid="pro-val-common-asset-requirements-save-button"]')
    expect(btn).to_be_visible()


def test_PVCAR_E14_hotel_input_status_updates(page: Page, live_server: str) -> None:
    """Filling property_name input updates status to ✅."""
    _goto_pv(page, live_server)
    _open_new_request(page)
    _select_asset(page, "hotel")
    inp = page.locator('input[data-backend-key="property_name"]').first
    expect(inp).to_be_visible()
    inp.fill("فندق النيل الكبير")
    page.wait_for_timeout(300)
    status = page.locator('[data-testid="pro-val-common-asset-requirement-status"] span').first
    text = status.text_content()
    assert "✅" in text or "مكتمل" in text, f"Status not updated after fill: {text}"


# ─────────────────────────────────────────────────────────────────────────────
# C. Industrial factory panel
# ─────────────────────────────────────────────────────────────────────────────

def test_PVCAR_E15_factory_panel_appears(page: Page, live_server: str) -> None:
    """Selecting industrial_factory shows fillable requirements panel."""
    _goto_pv(page, live_server)
    _open_new_request(page)
    _select_asset(page, "industrial_factory")
    fp = page.locator('[data-testid="pro-val-common-asset-requirements-panel"]')
    expect(fp).to_be_visible()


def test_PVCAR_E16_factory_rows_present(page: Page, live_server: str) -> None:
    """Factory panel has at least 8 requirement rows."""
    _goto_pv(page, live_server)
    _open_new_request(page)
    _select_asset(page, "industrial_factory")
    rows = page.locator('[data-testid="pro-val-common-asset-requirement-row"]')
    assert rows.count() >= 8


# ─────────────────────────────────────────────────────────────────────────────
# D. Land panel
# ─────────────────────────────────────────────────────────────────────────────

def test_PVCAR_E17_land_panel_appears(page: Page, live_server: str) -> None:
    """Selecting urban_land shows fillable requirements panel."""
    _goto_pv(page, live_server)
    _open_new_request(page)
    _select_asset(page, "urban_land")
    fp = page.locator('[data-testid="pro-val-common-asset-requirements-panel"]')
    expect(fp).to_be_visible()


def test_PVCAR_E18_land_rows_present(page: Page, live_server: str) -> None:
    """Land panel has at least 8 requirement rows."""
    _goto_pv(page, live_server)
    _open_new_request(page)
    _select_asset(page, "urban_land")
    rows = page.locator('[data-testid="pro-val-common-asset-requirement-row"]')
    assert rows.count() >= 8


# ─────────────────────────────────────────────────────────────────────────────
# E. Retail / Warehouse / Residential
# ─────────────────────────────────────────────────────────────────────────────

def test_PVCAR_E19_retail_panel_appears(page: Page, live_server: str) -> None:
    """Selecting retail_shop shows fillable requirements panel."""
    _goto_pv(page, live_server)
    _open_new_request(page)
    _select_asset(page, "retail_shop")
    fp = page.locator('[data-testid="pro-val-common-asset-requirements-panel"]')
    expect(fp).to_be_visible()


def test_PVCAR_E20_warehouse_panel_appears(page: Page, live_server: str) -> None:
    """Selecting warehouse shows fillable requirements panel."""
    _goto_pv(page, live_server)
    _open_new_request(page)
    _select_asset(page, "warehouse")
    fp = page.locator('[data-testid="pro-val-common-asset-requirements-panel"]')
    expect(fp).to_be_visible()


def test_PVCAR_E21_residential_panel_appears(page: Page, live_server: str) -> None:
    """Selecting residential_apartment shows fillable requirements panel."""
    _goto_pv(page, live_server)
    _open_new_request(page)
    _select_asset(page, "residential_apartment")
    fp = page.locator('[data-testid="pro-val-common-asset-requirements-panel"]')
    expect(fp).to_be_visible()


def test_PVCAR_E22_residential_construction_type_select(page: Page, live_server: str) -> None:
    """Residential construction_type select shows concrete — NOT excellent."""
    _goto_pv(page, live_server)
    _open_new_request(page)
    _select_asset(page, "residential_apartment")
    sel = page.locator('select[data-backend-key="construction_type"]').first
    expect(sel).to_be_visible()
    opts = sel.evaluate("el => Array.from(el.options).map(o => o.value)")
    assert "concrete" in opts
    assert "excellent" not in opts


# ─────────────────────────────────────────────────────────────────────────────
# F. Administrative Office panel
# ─────────────────────────────────────────────────────────────────────────────

def test_PVCAR_E23_office_panel_appears(page: Page, live_server: str) -> None:
    """Selecting administrative_office shows fillable requirements panel."""
    _goto_pv(page, live_server)
    _open_new_request(page)
    _select_asset(page, "administrative_office")
    fp = page.locator('[data-testid="pro-val-common-asset-requirements-panel"]')
    expect(fp).to_be_visible()


def test_PVCAR_E24_office_rows_present(page: Page, live_server: str) -> None:
    """Office panel has at least 8 requirement rows."""
    _goto_pv(page, live_server)
    _open_new_request(page)
    _select_asset(page, "administrative_office")
    rows = page.locator('[data-testid="pro-val-common-asset-requirement-row"]')
    assert rows.count() >= 8


# ─────────────────────────────────────────────────────────────────────────────
# G. Select testid validation
# ─────────────────────────────────────────────────────────────────────────────

def test_PVCAR_E25_common_asset_select_testid(page: Page, live_server: str) -> None:
    """Select elements in common asset table use pro-val-common-asset-requirement-select testid."""
    _goto_pv(page, live_server)
    _open_new_request(page)
    _select_asset(page, "hotel")
    selects = page.locator('[data-testid="pro-val-common-asset-requirement-select"]')
    count = selects.count()
    assert count >= 3, f"Expected >=3 pro-val-common-asset-requirement-select elements, got {count}"


def test_PVCAR_E26_common_asset_input_testid(page: Page, live_server: str) -> None:
    """Non-select inputs in common asset table use pro-val-common-asset-requirement-input testid."""
    _goto_pv(page, live_server)
    _open_new_request(page)
    _select_asset(page, "hotel")
    inputs = page.locator('[data-testid="pro-val-common-asset-requirement-input"]')
    count = inputs.count()
    assert count >= 5, f"Expected >=5 pro-val-common-asset-requirement-input elements, got {count}"


# ─────────────────────────────────────────────────────────────────────────────
# H. Alias asset types work
# ─────────────────────────────────────────────────────────────────────────────

def test_PVCAR_E27_resort_uses_hotel_data(page: Page, live_server: str) -> None:
    """Selecting resort renders fillable requirements panel (hotel alias)."""
    _goto_pv(page, live_server)
    _open_new_request(page)
    _select_asset(page, "resort")
    fp = page.locator('[data-testid="pro-val-common-asset-requirements-panel"]')
    expect(fp).to_be_visible()


def test_PVCAR_E28_agricultural_land_uses_land_data(page: Page, live_server: str) -> None:
    """Selecting agricultural_land renders fillable requirements panel."""
    _goto_pv(page, live_server)
    _open_new_request(page)
    _select_asset(page, "agricultural_land")
    fp = page.locator('[data-testid="pro-val-common-asset-requirements-panel"]')
    expect(fp).to_be_visible()


# ─────────────────────────────────────────────────────────────────────────────
# I. No regressions
# ─────────────────────────────────────────────────────────────────────────────

def test_PVCAR_E29_static_legacy_still_present(page: Page, live_server: str) -> None:
    """Legacy static content (number_of_rooms / عدد المفاتيح) is still inside hotel panel."""
    _goto_pv(page, live_server)
    _open_new_request(page)
    _select_asset(page, "hotel")
    panel = page.locator('[data-testid="pro-val-hotel-requirements-panel"]')
    expect(panel).to_be_visible()
    html = panel.inner_html()
    assert ("number_of_rooms" in html or "عدد الغرف" in html or "عدد المفاتيح" in html), \
        "Legacy static content removed from hotel panel — regression"


def test_PVCAR_E30_no_js_errors_on_asset_selection(page: Page, live_server: str) -> None:
    """No JS errors occur when selecting hotel, factory, land, retail, warehouse, residential."""
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    _goto_pv(page, live_server)
    _open_new_request(page)
    for asset_type in ["hotel", "industrial_factory", "urban_land",
                       "retail_shop", "warehouse", "residential_apartment"]:
        _select_asset(page, asset_type)
    assert len(errors) == 0, f"JS errors during asset selection: {errors}"
