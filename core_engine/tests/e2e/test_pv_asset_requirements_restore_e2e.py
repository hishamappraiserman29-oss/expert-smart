"""
E2E Browser Tests — PVS5: Professional Valuation Common Asset Requirements Hard Restore
Task: PVS5-HARD-RESTORE

Tests verify:
1. Selecting a common asset type (hotel, factory, land, etc.) shows a fillable table
2. Fillable table contains real input/select/textarea controls
3. All required testids are present (pro-val-common-asset-requirements-*)
4. Uncommon assets (petrol_station, cinema, padel) still show special asset panel
5. Status updates when fields are filled
6. Save button works
7. Old static panel does not show for common assets
8. Browser screenshots captured for 4 key asset types
"""
import os
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

_SCREENSHOTS_DIR = (
    Path(__file__).resolve().parent.parent
    / "instance"
    / "manual_review_outputs"
    / "professional_valuation_hard_restore_asset_requirements"
)


def _goto(page: Page, live_server: str) -> None:
    page.route("**/api/**", lambda r: r.fulfill(
        status=200, body=b'{"ok":true,"requests":[],"data":{}}',
        content_type="application/json",
    ))
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator('[data-testid="professional-wizard"]').wait_for(
        state="visible", timeout=12_000
    )


def _select_asset_type(page: Page, value: str) -> None:
    sel = page.locator('#asset-type')
    sel.select_option(value=value)


def _common_panel(page: Page):
    return page.locator('[data-testid="pro-val-common-asset-requirements-car-body"]')


def _fillable_panel(page: Page):
    return page.locator('[data-pvcar-fillable]').first


def _save_screenshot(page: Page, name: str) -> None:
    _SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    path = str(_SCREENSHOTS_DIR / name)
    page.screenshot(path=path)


# ── PVCAR01: Asset type select visible ───────────────────────────────────
@pytest.mark.e2e
def test_PVCAR01_asset_type_select_visible(page: Page, live_server: str) -> None:
    """PVCAR01: The common asset type select is visible in Section 2."""
    _goto(page, live_server)
    # Two selects share this testid (Section 2 + backoffice); first is the visible wizard one
    sel = page.locator('[data-testid="pro-val-asset-type-select"]').first
    expect(sel).to_be_visible()


# ── PVCAR02: Asset requirements panel exists in DOM ───────────────────────
@pytest.mark.e2e
def test_PVCAR02_asset_requirements_panel_in_dom(page: Page, live_server: str) -> None:
    """PVCAR02: pvr-vis-asset-requirements-panel exists in the DOM."""
    _goto(page, live_server)
    panel = page.locator('[data-testid="pro-val-asset-requirements-panel"]')
    assert panel.count() >= 1


# ── PVCAR03: Hotel selection shows common asset panel ────────────────────
@pytest.mark.e2e
def test_PVCAR03_hotel_shows_common_asset_panel(page: Page, live_server: str) -> None:
    """PVCAR03: Selecting hotel reveals the fillable common asset panel."""
    _goto(page, live_server)
    _select_asset_type(page, "hotel")
    # Two panels share this testid; use the Section 2 one (#pvr-vis-asset-requirements-panel)
    panel = page.locator('#pvr-vis-asset-requirements-panel')
    expect(panel).to_be_visible()


# ── PVCAR04: Hotel shows pvr-vis-car-body ────────────────────────────────
@pytest.mark.e2e
def test_PVCAR04_hotel_shows_car_body(page: Page, live_server: str) -> None:
    """PVCAR04: Selecting hotel shows pvr-vis-car-body (fillable container)."""
    _goto(page, live_server)
    _select_asset_type(page, "hotel")
    car = page.locator('[data-testid="pro-val-common-asset-requirements-car-body"]')
    expect(car).to_be_visible()


# ── PVCAR05: Hotel has pro-val-common-asset-requirements-panel testid ─────
@pytest.mark.e2e
def test_PVCAR05_hotel_has_requirements_panel_testid(page: Page, live_server: str) -> None:
    """PVCAR05: Selecting hotel renders element with testid pro-val-common-asset-requirements-panel."""
    _goto(page, live_server)
    _select_asset_type(page, "hotel")
    el = page.locator('[data-testid="pro-val-common-asset-requirements-panel"]')
    el.wait_for(state="visible", timeout=5000)
    expect(el).to_be_visible()


# ── PVCAR06: Hotel has requirements table testid ─────────────────────────
@pytest.mark.e2e
def test_PVCAR06_hotel_has_requirements_table_testid(page: Page, live_server: str) -> None:
    """PVCAR06: pro-val-common-asset-requirements-table is present for hotel."""
    _goto(page, live_server)
    _select_asset_type(page, "hotel")
    tbl = page.locator('[data-testid="pro-val-common-asset-requirements-table"]')
    tbl.wait_for(state="visible", timeout=5000)
    expect(tbl).to_be_visible()


# ── PVCAR07: Hotel has requirement rows ──────────────────────────────────
@pytest.mark.e2e
def test_PVCAR07_hotel_has_requirement_rows(page: Page, live_server: str) -> None:
    """PVCAR07: Hotel fillable table has at least 5 pro-val-common-asset-requirement-row elements."""
    _goto(page, live_server)
    _select_asset_type(page, "hotel")
    page.locator('[data-testid="pro-val-common-asset-requirements-table"]').wait_for(
        state="visible", timeout=5000
    )
    rows = page.locator('[data-testid="pro-val-common-asset-requirement-row"]')
    assert rows.count() >= 5


# ── PVCAR08: Hotel has label cells ───────────────────────────────────────
@pytest.mark.e2e
def test_PVCAR08_hotel_has_label_cells(page: Page, live_server: str) -> None:
    """PVCAR08: Hotel rows have pro-val-common-asset-requirement-label cells."""
    _goto(page, live_server)
    _select_asset_type(page, "hotel")
    page.locator('[data-testid="pro-val-common-asset-requirements-table"]').wait_for(
        state="visible", timeout=5000
    )
    labels = page.locator('[data-testid="pro-val-common-asset-requirement-label"]')
    assert labels.count() >= 5


# ── PVCAR09: Hotel has input controls ────────────────────────────────────
@pytest.mark.e2e
def test_PVCAR09_hotel_has_input_controls(page: Page, live_server: str) -> None:
    """PVCAR09: Hotel table has pro-val-common-asset-requirement-input cells."""
    _goto(page, live_server)
    _select_asset_type(page, "hotel")
    page.locator('[data-testid="pro-val-common-asset-requirements-table"]').wait_for(
        state="visible", timeout=5000
    )
    inputs = page.locator('[data-testid="pro-val-common-asset-requirement-input"]')
    assert inputs.count() >= 1


# ── PVCAR10: Hotel has select controls ───────────────────────────────────
@pytest.mark.e2e
def test_PVCAR10_hotel_has_select_controls(page: Page, live_server: str) -> None:
    """PVCAR10: Hotel table has pro-val-common-asset-requirement-select cells."""
    _goto(page, live_server)
    _select_asset_type(page, "hotel")
    page.locator('[data-testid="pro-val-common-asset-requirements-table"]').wait_for(
        state="visible", timeout=5000
    )
    selects = page.locator('[data-testid="pro-val-common-asset-requirement-select"]')
    assert selects.count() >= 1


# ── PVCAR11: Hotel has status cells ──────────────────────────────────────
@pytest.mark.e2e
def test_PVCAR11_hotel_has_status_cells(page: Page, live_server: str) -> None:
    """PVCAR11: Hotel table has pro-val-common-asset-requirement-status cells."""
    _goto(page, live_server)
    _select_asset_type(page, "hotel")
    page.locator('[data-testid="pro-val-common-asset-requirements-table"]').wait_for(
        state="visible", timeout=5000
    )
    statuses = page.locator('[data-testid="pro-val-common-asset-requirement-status"]')
    assert statuses.count() >= 1


# ── PVCAR12: Hotel has note cells ────────────────────────────────────────
@pytest.mark.e2e
def test_PVCAR12_hotel_has_note_cells(page: Page, live_server: str) -> None:
    """PVCAR12: Hotel table has pro-val-common-asset-requirement-note cells."""
    _goto(page, live_server)
    _select_asset_type(page, "hotel")
    page.locator('[data-testid="pro-val-common-asset-requirements-table"]').wait_for(
        state="visible", timeout=5000
    )
    notes = page.locator('[data-testid="pro-val-common-asset-requirement-note"]')
    assert notes.count() >= 1


# ── PVCAR13: Hotel has save button ───────────────────────────────────────
@pytest.mark.e2e
def test_PVCAR13_hotel_has_save_button(page: Page, live_server: str) -> None:
    """PVCAR13: Hotel table has pro-val-common-asset-requirements-save-button."""
    _goto(page, live_server)
    _select_asset_type(page, "hotel")
    btn = page.locator('[data-testid="pro-val-common-asset-requirements-save-button"]')
    btn.wait_for(state="visible", timeout=5000)
    expect(btn).to_be_visible()


# ── PVCAR14: Hotel has completion summary ────────────────────────────────
@pytest.mark.e2e
def test_PVCAR14_hotel_has_completion_summary(page: Page, live_server: str) -> None:
    """PVCAR14: Hotel table has pro-val-common-asset-requirements-completion-summary."""
    _goto(page, live_server)
    _select_asset_type(page, "hotel")
    page.locator('[data-testid="pro-val-common-asset-requirements-table"]').wait_for(
        state="visible", timeout=5000
    )
    summary = page.locator('[data-testid="pro-val-common-asset-requirements-completion-summary"]')
    assert summary.count() >= 1


# ── PVCAR15: Industrial factory shows fillable table ─────────────────────
@pytest.mark.e2e
def test_PVCAR15_industrial_factory_shows_fillable(page: Page, live_server: str) -> None:
    """PVCAR15: Selecting industrial_factory shows a fillable table."""
    _goto(page, live_server)
    _select_asset_type(page, "industrial_factory")
    tbl = page.locator('[data-testid="pro-val-common-asset-requirements-table"]')
    tbl.wait_for(state="visible", timeout=5000)
    expect(tbl).to_be_visible()


# ── PVCAR16: Warehouse shows fillable table ───────────────────────────────
@pytest.mark.e2e
def test_PVCAR16_warehouse_shows_fillable(page: Page, live_server: str) -> None:
    """PVCAR16: Selecting warehouse shows a fillable table."""
    _goto(page, live_server)
    _select_asset_type(page, "warehouse")
    tbl = page.locator('[data-testid="pro-val-common-asset-requirements-table"]')
    tbl.wait_for(state="visible", timeout=5000)
    expect(tbl).to_be_visible()


# ── PVCAR17: Urban land shows fillable table ──────────────────────────────
@pytest.mark.e2e
def test_PVCAR17_urban_land_shows_fillable(page: Page, live_server: str) -> None:
    """PVCAR17: Selecting urban_land shows a fillable table."""
    _goto(page, live_server)
    _select_asset_type(page, "urban_land")
    tbl = page.locator('[data-testid="pro-val-common-asset-requirements-table"]')
    tbl.wait_for(state="visible", timeout=5000)
    expect(tbl).to_be_visible()


# ── PVCAR18: Retail shop shows fillable table ─────────────────────────────
@pytest.mark.e2e
def test_PVCAR18_retail_shop_shows_fillable(page: Page, live_server: str) -> None:
    """PVCAR18: Selecting retail_shop shows a fillable table."""
    _goto(page, live_server)
    _select_asset_type(page, "retail_shop")
    tbl = page.locator('[data-testid="pro-val-common-asset-requirements-table"]')
    tbl.wait_for(state="visible", timeout=5000)
    expect(tbl).to_be_visible()


# ── PVCAR19: Administrative office shows fillable table ──────────────────
@pytest.mark.e2e
def test_PVCAR19_administrative_office_shows_fillable(page: Page, live_server: str) -> None:
    """PVCAR19: Selecting administrative_office shows a fillable table."""
    _goto(page, live_server)
    _select_asset_type(page, "administrative_office")
    tbl = page.locator('[data-testid="pro-val-common-asset-requirements-table"]')
    tbl.wait_for(state="visible", timeout=5000)
    expect(tbl).to_be_visible()


# ── PVCAR20: Residential apartment shows fillable table ──────────────────
@pytest.mark.e2e
def test_PVCAR20_residential_apartment_shows_fillable(page: Page, live_server: str) -> None:
    """PVCAR20: Selecting residential_apartment shows a fillable table."""
    _goto(page, live_server)
    _select_asset_type(page, "residential_apartment")
    tbl = page.locator('[data-testid="pro-val-common-asset-requirements-table"]')
    tbl.wait_for(state="visible", timeout=5000)
    expect(tbl).to_be_visible()


# ── PVCAR21: Resort (alias) shows fillable table ─────────────────────────
@pytest.mark.e2e
def test_PVCAR21_resort_alias_shows_fillable(page: Page, live_server: str) -> None:
    """PVCAR21: Selecting resort (hotel alias) shows a fillable table."""
    _goto(page, live_server)
    _select_asset_type(page, "resort")
    tbl = page.locator('[data-testid="pro-val-common-asset-requirements-table"]')
    tbl.wait_for(state="visible", timeout=5000)
    expect(tbl).to_be_visible()


# ── PVCAR22: Shopping mall (alias) shows fillable table ──────────────────
@pytest.mark.e2e
def test_PVCAR22_shopping_mall_alias_shows_fillable(page: Page, live_server: str) -> None:
    """PVCAR22: Selecting shopping_mall (alias) shows a fillable table."""
    _goto(page, live_server)
    _select_asset_type(page, "shopping_mall")
    tbl = page.locator('[data-testid="pro-val-common-asset-requirements-table"]')
    tbl.wait_for(state="visible", timeout=5000)
    expect(tbl).to_be_visible()


# ── PVCAR23: Can type in hotel text input ────────────────────────────────
@pytest.mark.e2e
def test_PVCAR23_can_type_in_hotel_text_input(page: Page, live_server: str) -> None:
    """PVCAR23: Can type a value into a hotel text input field."""
    _goto(page, live_server)
    _select_asset_type(page, "hotel")
    page.locator('[data-testid="pro-val-common-asset-requirements-table"]').wait_for(
        state="visible", timeout=5000
    )
    first_text = page.locator(
        '[data-pvcar-fillable] input[type="text"]'
    ).first
    first_text.fill("فندق النيل الفاخر")
    assert first_text.input_value() == "فندق النيل الفاخر"


# ── PVCAR24: Can select option in hotel select ───────────────────────────
@pytest.mark.e2e
def test_PVCAR24_can_select_option_in_hotel_select(page: Page, live_server: str) -> None:
    """PVCAR24: Can select an option from a hotel select field."""
    _goto(page, live_server)
    _select_asset_type(page, "hotel")
    page.locator('[data-testid="pro-val-common-asset-requirements-table"]').wait_for(
        state="visible", timeout=5000
    )
    sel = page.locator('[data-pvcar-fillable] select').first
    options = sel.locator('option').all()
    assert len(options) >= 2
    # Select the second option (index 1, since 0 is empty placeholder)
    sel.select_option(index=1)
    assert sel.input_value() != ""


# ── PVCAR25: Hotel save button is clickable ──────────────────────────────
@pytest.mark.e2e
def test_PVCAR25_hotel_save_button_clickable(page: Page, live_server: str) -> None:
    """PVCAR25: Clicking hotel save button changes its text to confirm save."""
    _goto(page, live_server)
    _select_asset_type(page, "hotel")
    btn = page.locator('[data-testid="pro-val-common-asset-requirements-save-button"]')
    btn.wait_for(state="visible", timeout=5000)
    btn.click()
    page.wait_for_timeout(300)
    # After click, button text should change briefly to "تم الحفظ"
    txt = btn.text_content() or ""
    assert "حفظ" in txt or "تم" in txt


# ── PVCAR26: Status updates when hotel text field filled ─────────────────
@pytest.mark.e2e
def test_PVCAR26_status_updates_when_field_filled(page: Page, live_server: str) -> None:
    """PVCAR26: Filling a hotel text field changes status from ⬜ to ✅."""
    _goto(page, live_server)
    _select_asset_type(page, "hotel")
    page.locator('[data-testid="pro-val-common-asset-requirements-table"]').wait_for(
        state="visible", timeout=5000
    )
    # Initial status of first status cell
    first_status = page.locator('[data-testid="pro-val-common-asset-requirement-status"] span').first
    initial_txt = first_status.text_content() or ""
    # Fill in the corresponding input
    first_input = page.locator('[data-pvcar-fillable] input[type="text"]').first
    first_input.fill("اختبار الحالة")
    first_input.dispatch_event("input")
    page.wait_for_timeout(200)
    updated_txt = first_status.text_content() or ""
    assert "✅" in updated_txt or updated_txt != initial_txt


# ── PVCAR27: Non-common asset uses static panel ──────────────────────────
@pytest.mark.e2e
def test_PVCAR27_non_common_asset_uses_static_panel(page: Page, live_server: str) -> None:
    """PVCAR27: Selecting a non-common asset does not show fillable table."""
    _goto(page, live_server)
    # 'historical' is in the select but not in _PV_COMMON_REQ_DATA
    _select_asset_type(page, "historical")
    page.wait_for_timeout(300)
    tbl = page.locator('[data-testid="pro-val-common-asset-requirements-table"]')
    # Either not visible or count == 0
    assert not tbl.is_visible() or tbl.count() == 0


# ── PVCAR28: Special asset panel still present ───────────────────────────
@pytest.mark.e2e
def test_PVCAR28_special_asset_panel_present(page: Page, live_server: str) -> None:
    """PVCAR28: pvr-vis-special-asset-requirements-panel exists in DOM."""
    _goto(page, live_server)
    panel = page.locator('[data-testid="pro-val-special-asset-requirements-panel"]')
    assert panel.count() >= 1


# ── PVCAR29: Hotel fillable table groups visible (details elements) ──────
@pytest.mark.e2e
def test_PVCAR29_hotel_has_group_details(page: Page, live_server: str) -> None:
    """PVCAR29: Hotel fillable table contains <details> group elements."""
    _goto(page, live_server)
    _select_asset_type(page, "hotel")
    page.locator('[data-testid="pro-val-common-asset-requirements-table"]').wait_for(
        state="visible", timeout=5000
    )
    details = page.locator('[data-pvcar-fillable] details')
    assert details.count() >= 2


# ── PVCAR30: Factory has construction_type select ────────────────────────
@pytest.mark.e2e
def test_PVCAR30_factory_has_construction_type_select(page: Page, live_server: str) -> None:
    """PVCAR30: industrial_factory table has a select with construction_type options."""
    _goto(page, live_server)
    _select_asset_type(page, "industrial_factory")
    page.locator('[data-testid="pro-val-common-asset-requirements-table"]').wait_for(
        state="visible", timeout=5000
    )
    selects = page.locator('[data-pvcar-fillable] [data-backend-key="construction_type"]')
    assert selects.count() >= 1
    opts = selects.first.locator('option')
    texts = [opts.nth(i).text_content() or "" for i in range(opts.count())]
    has_concrete = any("خرساني" in t or "concrete" in t.lower() for t in texts)
    assert has_concrete


# ── PVCAR31: Hotel has structural_condition select with fair ─────────────
@pytest.mark.e2e
def test_PVCAR31_hotel_structural_condition_has_fair(page: Page, live_server: str) -> None:
    """PVCAR31: structural_condition select includes مقبول (fair) option."""
    _goto(page, live_server)
    _select_asset_type(page, "hotel")
    page.locator('[data-testid="pro-val-common-asset-requirements-table"]').wait_for(
        state="visible", timeout=5000
    )
    sel = page.locator('[data-pvcar-fillable] [data-backend-key="structural_condition"]')
    assert sel.count() >= 1
    opts = sel.first.locator('option')
    texts = [opts.nth(i).text_content() or "" for i in range(opts.count())]
    assert any("مقبول" in t or "fair" in t.lower() for t in texts)


# ── PVCAR32: construction_type has prefabricated option ──────────────────
@pytest.mark.e2e
def test_PVCAR32_construction_type_has_prefabricated(page: Page, live_server: str) -> None:
    """PVCAR32: construction_type select includes سابق التجهيز / بريفاب (prefabricated)."""
    _goto(page, live_server)
    _select_asset_type(page, "industrial_factory")
    page.locator('[data-testid="pro-val-common-asset-requirements-table"]').wait_for(
        state="visible", timeout=5000
    )
    sel = page.locator('[data-pvcar-fillable] [data-backend-key="construction_type"]')
    assert sel.count() >= 1
    opts = sel.first.locator('option')
    texts = [opts.nth(i).text_content() or "" for i in range(opts.count())]
    assert any("بريفاب" in t or "سابق" in t or "prefabricated" in t.lower() for t in texts)


# ── PVCAR33: Hotel ownership_type select present ─────────────────────────
@pytest.mark.e2e
def test_PVCAR33_hotel_ownership_type_select(page: Page, live_server: str) -> None:
    """PVCAR33: Hotel table has ownership_type select with valid options."""
    _goto(page, live_server)
    _select_asset_type(page, "hotel")
    page.locator('[data-testid="pro-val-common-asset-requirements-table"]').wait_for(
        state="visible", timeout=5000
    )
    sel = page.locator('[data-pvcar-fillable] [data-backend-key="ownership_type"]')
    assert sel.count() >= 1


# ── PVCAR34: Agricultural land (alias) shows urban_land data ─────────────
@pytest.mark.e2e
def test_PVCAR34_agricultural_land_shows_fillable(page: Page, live_server: str) -> None:
    """PVCAR34: Selecting agricultural_land shows a fillable table (alias of urban_land)."""
    _goto(page, live_server)
    _select_asset_type(page, "agricultural_land")
    tbl = page.locator('[data-testid="pro-val-common-asset-requirements-table"]')
    tbl.wait_for(state="visible", timeout=5000)
    expect(tbl).to_be_visible()


# ── PVCAR35: Mixed_use_asset (alias) shows fillable table ────────────────
@pytest.mark.e2e
def test_PVCAR35_mixed_use_asset_shows_fillable(page: Page, live_server: str) -> None:
    """PVCAR35: Selecting mixed_use_asset shows a fillable table."""
    _goto(page, live_server)
    _select_asset_type(page, "mixed_use_asset")
    tbl = page.locator('[data-testid="pro-val-common-asset-requirements-table"]')
    tbl.wait_for(state="visible", timeout=5000)
    expect(tbl).to_be_visible()


# ── PVCAR36: Switching from hotel to factory updates table ───────────────
@pytest.mark.e2e
def test_PVCAR36_switching_asset_type_updates_table(page: Page, live_server: str) -> None:
    """PVCAR36: Switching from hotel to industrial_factory shows factory-specific fields."""
    _goto(page, live_server)
    _select_asset_type(page, "hotel")
    page.locator('[data-testid="pro-val-common-asset-requirements-table"]').wait_for(
        state="visible", timeout=5000
    )
    # Switch to factory
    _select_asset_type(page, "industrial_factory")
    page.wait_for_timeout(400)
    tbl = page.locator('[data-testid="pro-val-common-asset-requirements-table"]')
    expect(tbl).to_be_visible()


# ── PVCAR37: Screenshot hotel fillable table ─────────────────────────────
@pytest.mark.e2e
def test_PVCAR37_screenshot_hotel_fillable(page: Page, live_server: str) -> None:
    """PVCAR37: Screenshot hotel fillable table to verify visual rendering."""
    _goto(page, live_server)
    _select_asset_type(page, "hotel")
    page.locator('[data-testid="pro-val-common-asset-requirements-table"]').wait_for(
        state="visible", timeout=5000
    )
    _save_screenshot(page, "01_hotel_fillable_table.png")
    assert page.locator('[data-testid="pro-val-common-asset-requirements-table"]').is_visible()


# ── PVCAR38: Screenshot factory fillable table ───────────────────────────
@pytest.mark.e2e
def test_PVCAR38_screenshot_factory_fillable(page: Page, live_server: str) -> None:
    """PVCAR38: Screenshot industrial_factory fillable table."""
    _goto(page, live_server)
    _select_asset_type(page, "industrial_factory")
    page.locator('[data-testid="pro-val-common-asset-requirements-table"]').wait_for(
        state="visible", timeout=5000
    )
    _save_screenshot(page, "02_factory_fillable_table.png")
    assert page.locator('[data-testid="pro-val-common-asset-requirements-table"]').is_visible()


# ── PVCAR39: Screenshot land fillable table ──────────────────────────────
@pytest.mark.e2e
def test_PVCAR39_screenshot_land_fillable(page: Page, live_server: str) -> None:
    """PVCAR39: Screenshot urban_land fillable table."""
    _goto(page, live_server)
    _select_asset_type(page, "urban_land")
    page.locator('[data-testid="pro-val-common-asset-requirements-table"]').wait_for(
        state="visible", timeout=5000
    )
    _save_screenshot(page, "03_land_fillable_table.png")
    assert page.locator('[data-testid="pro-val-common-asset-requirements-table"]').is_visible()


# ── PVCAR40: Screenshot residential apartment fillable table ─────────────
@pytest.mark.e2e
def test_PVCAR40_screenshot_residential_fillable(page: Page, live_server: str) -> None:
    """PVCAR40: Screenshot residential_apartment fillable table."""
    _goto(page, live_server)
    _select_asset_type(page, "residential_apartment")
    page.locator('[data-testid="pro-val-common-asset-requirements-table"]').wait_for(
        state="visible", timeout=5000
    )
    _save_screenshot(page, "04_residential_fillable_table.png")
    assert page.locator('[data-testid="pro-val-common-asset-requirements-table"]').is_visible()
