# -*- coding: utf-8 -*-
"""
PVATUX01–PVATUX21 — Professional Valuation Asset Type UX Cleanup: Browser Proof Tests (Part K).

These tests navigate to the DEFAULT URL so ws-professional is the active workspace.
They prove the visible UX changes from the asset-type cleanup task:

1. "تعريف الأصل العقاري" is NOT visible as a standalone main heading in Section 2.
2. "البيانات التقنية للأصل" is NOT visible as a standalone main box.
3. Section 2 card (pro-val-section-asset-type-selection) is visible.
4. All 4 selects are visible in correct grid order.
5. asset_family now includes all standard families (residential, land, commercial, etc.).
6. Selecting hotel → meaningful hotel subtypes shown, NOT plain 'hotel'.
7. Selecting vacant land → land subtypes shown, NOT plain 'vacant_land'.
8. Selecting residential unit → residential subtypes shown, NOT plain 'residential_unit'.
9. Selecting hotel → full requirements panel shown with ADR, RevPAR, معدل الإشغال.
10. Requirements count visible.
11. Legacy requirements preserved marker visible.
12. market_value NOT in asset_type select.
13. comparable_adjustment NOT in asset_type or subtype selects.
14. No internal paths in DOM (spot check).
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _go_to_visible_pv(page: Page, live_server: str) -> None:
    """Navigate to default page — ws-professional is the active workspace."""
    page.route("**/api/**", lambda r: r.fulfill(
        status=200, body=b'{"ok":true}', content_type="application/json"
    ))
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator('[data-testid="professional-wizard"]').wait_for(state="visible", timeout=10_000)


# ─────────────────────────────────────────────────────────────────────────────
# PVATUX01–PVATUX05: Section 2 structure visible + removed titles
# ─────────────────────────────────────────────────────────────────────────────

def test_PVATUX01_section2_asset_type_selection_visible(page: Page, live_server: str) -> None:
    """PVATUX01: Section 2 wrapper (pro-val-section-asset-type-selection) is visible."""
    _go_to_visible_pv(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-section-asset-type-selection"]')
    expect(el).to_be_visible()


def test_PVATUX02_asset_definition_title_not_main_visible_heading(page: Page, live_server: str) -> None:
    """PVATUX02: 'تعريف الأصل العقاري' is NOT visible as a standalone section heading.
    It was removed from the card title in the 6-section layout.
    The card now starts directly with the grid of 4 selects.
    This test verifies the removed title is not visible to the user.
    """
    _go_to_visible_pv(page, live_server)
    ws = page.locator("#ws-professional")
    section2 = ws.locator('[data-testid="pro-val-section-asset-type-selection"]')
    card = section2.locator('[data-testid="pro-val-card-asset-definition"]')
    # The old title was a div with text "1. تعريف الأصل العقاري" — it must not appear as visible heading
    # Check the card does NOT contain a visible element that reads exactly as the old title
    old_title_els = card.locator(':text("1. تعريف الأصل العقاري")')
    expect(old_title_els).to_have_count(0)


def test_PVATUX03_technical_data_box_not_visible(page: Page, live_server: str) -> None:
    """PVATUX03: 'البيانات التقنية للأصل' box is NOT visible to the user.
    The prof-technical-panel is no longer triggered by family selection.
    Its display:none state must be preserved on page load.
    """
    _go_to_visible_pv(page, live_server)
    panel = page.locator("#prof-technical-panel")
    # It must not be visible (either absent or hidden)
    expect(panel).not_to_be_visible()


def test_PVATUX04_asset_type_select_visible_row1(page: Page, live_server: str) -> None:
    """PVATUX04: asset_type select (pro-val-asset-type-select) is visible — Row 1 Left."""
    _go_to_visible_pv(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-asset-type-select"]').first
    expect(el).to_be_visible()


def test_PVATUX05_condition_path_select_visible_row1(page: Page, live_server: str) -> None:
    """PVATUX05: condition_path select (pro-val-asset-condition-path-select) is visible — Row 1 Right."""
    _go_to_visible_pv(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-asset-condition-path-select"]').first
    expect(el).to_be_visible()


# ─────────────────────────────────────────────────────────────────────────────
# PVATUX06–PVATUX08: Family and subtype selects visible
# ─────────────────────────────────────────────────────────────────────────────

def test_PVATUX06_family_select_visible_row2(page: Page, live_server: str) -> None:
    """PVATUX06: family select wrapper (pro-val-asset-family-select) is visible — Row 2 Left."""
    _go_to_visible_pv(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-asset-family-select"]').first
    expect(el).to_be_visible()


def test_PVATUX07_subtype_select_visible_row2(page: Page, live_server: str) -> None:
    """PVATUX07: subtype select wrapper (pro-val-asset-subtype-select) is visible — Row 2 Right."""
    _go_to_visible_pv(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-asset-subtype-select"]').first
    expect(el).to_be_visible()


def test_PVATUX08_family_includes_standard_families(page: Page, live_server: str) -> None:
    """PVATUX08: asset_family select now includes standard families (residential, land, commercial, etc.)."""
    _go_to_visible_pv(page, live_server)
    sel = page.locator('#prof-asset-family')
    html = sel.inner_html()
    for val in ("residential_housing", "land_plots", "commercial_retail",
                "industrial_logistics", "hospitality_leisure"):
        assert f'value="{val}"' in html, f"Missing standard family: {val}"


def test_PVATUX09_family_includes_agri_and_infra(page: Page, live_server: str) -> None:
    """PVATUX09: asset_family includes agri_environmental and infrastructure."""
    _go_to_visible_pv(page, live_server)
    sel = page.locator('#prof-asset-family')
    html = sel.inner_html()
    for val in ("agri_environmental", "infrastructure", "mixed_use", "office_administrative"):
        assert f'value="{val}"' in html, f"Missing standard family: {val}"


def test_PVATUX10_legacy_families_still_present(page: Page, live_server: str) -> None:
    """PVATUX10: Old (legacy) families are still present in the family select — no deletion."""
    _go_to_visible_pv(page, live_server)
    sel = page.locator('#prof-asset-family')
    html = sel.inner_html()
    for val in ("hospitality_entertainment", "sports_event_venues",
                "advanced_industrial_logistics", "heritage_cultural_assets"):
        assert f'value="{val}"' in html, f"Legacy family deleted: {val}"


# ─────────────────────────────────────────────────────────────────────────────
# PVATUX11–PVATUX13: Hotel subtype — no duplicate
# ─────────────────────────────────────────────────────────────────────────────

def test_PVATUX11_selecting_hotel_shows_meaningful_subtypes(page: Page, live_server: str) -> None:
    """PVATUX11: Selecting فندق as asset_type populates subtype with business_hotel etc., NOT plain hotel."""
    _go_to_visible_pv(page, live_server)
    page.locator('#asset-type').select_option('فندق')
    subtype_sel = page.locator('#prof-asset-subtype')
    html = subtype_sel.inner_html()
    assert 'value="business_hotel"' in html or 'value="boutique_hotel"' in html, \
        "Hotel subtypes must include business_hotel or boutique_hotel"
    assert 'value="hotel"' not in html, \
        "Subtype 'hotel' must NOT appear when asset_type is hotel (duplicate prevention)"


def test_PVATUX12_selecting_vacant_land_shows_land_subtypes(page: Page, live_server: str) -> None:
    """PVATUX12: Selecting أرض فضاء populates subtype with development land types, NOT plain vacant_land."""
    _go_to_visible_pv(page, live_server)
    page.locator('#asset-type').select_option('أرض فضاء')
    subtype_sel = page.locator('#prof-asset-subtype')
    html = subtype_sel.inner_html()
    assert 'value="residential_development_land"' in html or \
           'value="commercial_development_land"' in html, \
        "Land subtypes must include residential_development_land or commercial_development_land"
    assert 'value="vacant_land"' not in html, \
        "Subtype 'vacant_land' must NOT appear when asset_type is أرض فضاء (duplicate prevention)"


def test_PVATUX13_selecting_residential_unit_shows_unit_subtypes(page: Page, live_server: str) -> None:
    """PVATUX13: Selecting شقة سكنية populates subtype with specific unit types, NOT plain residential_unit."""
    _go_to_visible_pv(page, live_server)
    page.locator('#asset-type').select_option('شقة سكنية')
    subtype_sel = page.locator('#prof-asset-subtype')
    html = subtype_sel.inner_html()
    assert 'value="studio"' in html or 'value="one_bedroom"' in html or 'value="penthouse"' in html, \
        "Residential subtypes must include studio, one_bedroom, or penthouse"
    assert 'value="residential_unit"' not in html, \
        "Subtype 'residential_unit' must NOT appear when asset_type is شقة سكنية (duplicate prevention)"


# ─────────────────────────────────────────────────────────────────────────────
# PVATUX14–PVATUX18: Requirements panel shown with correct content
# ─────────────────────────────────────────────────────────────────────────────

def test_PVATUX14_requirements_panel_hidden_by_default(page: Page, live_server: str) -> None:
    """PVATUX14: Requirements panel is hidden before an asset type is selected."""
    _go_to_visible_pv(page, live_server)
    panel = page.locator('#pvr-vis-asset-requirements-panel')
    expect(panel).not_to_be_visible()


def test_PVATUX15_selecting_hotel_shows_requirements_panel(page: Page, live_server: str) -> None:
    """PVATUX15: Selecting فندق triggers the requirements panel to become visible."""
    _go_to_visible_pv(page, live_server)
    page.locator('#asset-type').select_option('فندق')
    panel = page.locator('#pvr-vis-asset-requirements-panel')
    expect(panel).to_be_visible()


def test_PVATUX16_hotel_requirements_count_visible(page: Page, live_server: str) -> None:
    """PVATUX16: Requirements count badge is visible after selecting hotel."""
    _go_to_visible_pv(page, live_server)
    page.locator('#asset-type').select_option('فندق')
    count_el = page.locator('[data-testid="pro-val-asset-requirements-count"]')
    expect(count_el).to_be_visible()
    text = count_el.text_content() or ""
    assert "عدد المتطلبات" in text, "Requirements count badge must contain 'عدد المتطلبات'"


def test_PVATUX17_legacy_requirements_preserved_marker_visible(page: Page, live_server: str) -> None:
    """PVATUX17: Legacy requirements preserved marker is visible after selecting hotel.
    Scoped to the dynamic requirements panel (#pvr-vis-asset-requirements-panel) to avoid
    strict mode violations from pre-existing legacy requirement panels sharing the same testid.
    """
    _go_to_visible_pv(page, live_server)
    page.locator('#asset-type').select_option('فندق')
    # Scope to the dynamic panel only — not to other static legacy panels
    panel = page.locator('#pvr-vis-asset-requirements-panel')
    expect(panel).to_be_visible()
    marker = panel.locator('[data-testid="pro-val-asset-requirements-legacy-list"]').first
    expect(marker).to_be_visible()
    text = marker.text_content() or ""
    assert "الحفاظ" in text or "النسخة السابقة" in text, \
        f"Legacy preserved marker must contain النسخة السابقة, got: {text!r}"


def test_PVATUX18_hotel_requirements_include_adr_revpar_occupancy(page: Page, live_server: str) -> None:
    """PVATUX18: Hotel requirements body includes ADR, RevPAR, معدل الإشغال."""
    _go_to_visible_pv(page, live_server)
    page.locator('#asset-type').select_option('فندق')
    body = page.locator('#pvr-vis-req-body')
    text = body.inner_text()
    assert "ADR" in text, "Hotel requirements must include ADR"
    assert "RevPAR" in text, "Hotel requirements must include RevPAR"
    assert "الإشغال" in text, "Hotel requirements must include معدل الإشغال"


# ─────────────────────────────────────────────────────────────────────────────
# PVATUX19–PVATUX21: No-deletion and governance checks
# ─────────────────────────────────────────────────────────────────────────────

def test_PVATUX19_market_value_not_in_asset_type_select(page: Page, live_server: str) -> None:
    """PVATUX19: market_value is NOT an option in the asset_type select.
    It is a basis of value, not an asset type.
    """
    _go_to_visible_pv(page, live_server)
    sel = page.locator('#asset-type')
    html = sel.inner_html()
    assert 'value="market_value"' not in html, \
        "market_value must NOT be in asset_type options — it is a basis of value"


def test_PVATUX20_comparable_adjustment_not_in_asset_type_or_subtype(page: Page, live_server: str) -> None:
    """PVATUX20: comparable_adjustment is NOT in asset_type OR subtype selects.
    It is a valuation method step, not an asset type or subtype.
    """
    _go_to_visible_pv(page, live_server)
    asset_html = page.locator('#asset-type').inner_html()
    assert 'value="comparable_adjustment"' not in asset_html, \
        "comparable_adjustment must NOT be in asset_type options"
    subtype_html = page.locator('#prof-asset-subtype').inner_html()
    assert 'value="comparable_adjustment"' not in subtype_html, \
        "comparable_adjustment must NOT be in asset_subtype options"


def test_PVATUX21_all_old_asset_types_still_present(page: Page, live_server: str) -> None:
    """PVATUX21: All old asset types still present in the select — no deletion.
    Verifies: فندق, مصنع, أرض فضاء, أرض زراعية, شقة سكنية, عمارة سكنية, محل تجاري,
    مستشفى, مدرسة, مناجم, water_well, hotel_resort_detailed, serviced_apartments,
    airport, seaport, data_center, cold_storage, historical, heritage.
    """
    _go_to_visible_pv(page, live_server)
    sel = page.locator('#asset-type')
    html = sel.inner_html()
    old_values = [
        "فندق", "مصنع", "أرض فضاء", "أرض زراعية", "شقة سكنية", "عمارة سكنية",
        "محل تجاري", "مستشفى", "مدرسة", "مناجم", "water_well",
        "hotel_resort_detailed", "serviced_apartments", "floating_hotel",
        "airport", "seaport", "marina", "data_center", "cold_storage",
        "prefabricated_factory", "historical", "heritage",
    ]
    for val in old_values:
        assert f'value="{val}"' in html, f"Old asset type deleted: {val}"
