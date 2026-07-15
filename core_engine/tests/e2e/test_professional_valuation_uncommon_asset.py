# -*- coding: utf-8 -*-
"""
PVUAF01–PVUAF24 — Uncommon Asset Family/Subtype UX: Browser Proof Tests (Part K).

Verifies the UX changes from the PVUAF task (Section 2 Refinement):

PVUAF01  Section 2 asset-type-selection card is visible
PVUAF02  Label "نوع الأصل العقاري الشائع" is visible
PVUAF03  Label "عائلة الأصل غير الشائعة" is visible (renamed)
PVUAF04  Label "النوع الفرعي للأصل غير الشائع" is visible (renamed)
PVUAF05  #asset-type select is visible (common asset type)
PVUAF06  #prof-asset-family select is visible (uncommon family)
PVUAF07  #prof-asset-subtype select is visible (uncommon subtype)
PVUAF08  pro-val-uncommon-asset-family-select testid exists
PVUAF09  pro-val-uncommon-asset-subtype-select testid exists
PVUAF10  heritage_assets family option is present in #prof-asset-family
PVUAF11  Selecting heritage_assets populates #prof-asset-subtype with heritage subtypes
PVUAF12  Selecting distinguished_architectural_heritage triggers full heritage requirements panel
PVUAF13  Full heritage panel has >= 39 requirements
PVUAF14  Legacy preservation marker visible after heritage alias subtype selected
PVUAF15  All 7 heritage groups visible after heritage alias subtype selected
PVUAF16  sports_recreation_assets family populates stadium subtype
PVUAF17  Selecting stadium triggers requirements panel
PVUAF18  healthcare_assets family populates general_hospital subtype
PVUAF19  Common asset type (شقة سكنية) still selectable from #asset-type
PVUAF20  No JS errors when selecting heritage_assets family
PVUAF21  No JS errors when selecting distinguished_architectural_heritage subtype
PVUAF22  Old pro-val-asset-family-select testid still present (backward compat)
PVUAF23  Old pro-val-asset-subtype-select testid still present (backward compat)
PVUAF24  heritage option (value=heritage) still present in #asset-type (not deleted)
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


def _select_uncommon_family(page: Page, family_value: str) -> None:
    """Select a family in #prof-asset-family."""
    page.locator('#prof-asset-family').select_option(family_value)
    page.wait_for_timeout(250)


def _select_uncommon_subtype(page: Page, subtype_value: str) -> None:
    """Select a subtype in #prof-asset-subtype."""
    page.locator('#prof-asset-subtype').select_option(subtype_value)
    page.wait_for_timeout(250)


# ─────────────────────────────────────────────────────────────────────────────
# PVUAF01–PVUAF04: Labels visible
# ─────────────────────────────────────────────────────────────────────────────

def test_PVUAF01_section2_asset_definition_card_visible(page: Page, live_server: str) -> None:
    """PVUAF01: pro-val-card-asset-definition inside pro-val-section-asset-type-selection is visible."""
    _go_to_visible_pv(page, live_server)
    section2 = page.locator('[data-testid="pro-val-section-asset-type-selection"]')
    card = section2.locator('[data-testid="pro-val-card-asset-definition"]')
    expect(card).to_be_visible()


def test_PVUAF02_common_asset_type_label_visible(page: Page, live_server: str) -> None:
    """PVUAF02: Label 'نوع الأصل العقاري الشائع' is visible in Section 2."""
    _go_to_visible_pv(page, live_server)
    card = page.locator('[data-testid="pro-val-card-asset-definition"]')
    expect(card.locator(':text("نوع الأصل العقاري الشائع")').first).to_be_visible()


def test_PVUAF03_uncommon_family_label_visible(page: Page, live_server: str) -> None:
    """PVUAF03: Label 'عائلة الأصل غير الشائعة' is visible in Section 2 (renamed from 'عائلة الأصل')."""
    _go_to_visible_pv(page, live_server)
    card = page.locator('[data-testid="pro-val-card-asset-definition"]')
    expect(card.locator(':text("عائلة الأصل غير الشائعة")').first).to_be_visible()


def test_PVUAF04_uncommon_subtype_label_visible(page: Page, live_server: str) -> None:
    """PVUAF04: Label 'النوع الفرعي للأصل غير الشائع' is visible in Section 2 (renamed)."""
    _go_to_visible_pv(page, live_server)
    card = page.locator('[data-testid="pro-val-card-asset-definition"]')
    expect(card.locator(':text("النوع الفرعي للأصل غير الشائع")').first).to_be_visible()


# ─────────────────────────────────────────────────────────────────────────────
# PVUAF05–PVUAF09: Dropdowns and testids visible
# ─────────────────────────────────────────────────────────────────────────────

def test_PVUAF05_common_asset_type_select_visible(page: Page, live_server: str) -> None:
    """PVUAF05: #asset-type (pro-val-asset-type-select) is visible in Section 2 card."""
    _go_to_visible_pv(page, live_server)
    # Scope to Section 2 card to avoid strict-mode violation (testid also exists in pvr section)
    card = page.locator('[data-testid="pro-val-card-asset-definition"]')
    expect(card.locator('[data-testid="pro-val-asset-type-select"]')).to_be_visible()


def test_PVUAF06_uncommon_family_select_visible(page: Page, live_server: str) -> None:
    """PVUAF06: #prof-asset-family (professional-asset-family) is visible."""
    _go_to_visible_pv(page, live_server)
    expect(page.locator('[data-testid="professional-asset-family"]')).to_be_visible()


def test_PVUAF07_uncommon_subtype_select_visible(page: Page, live_server: str) -> None:
    """PVUAF07: #prof-asset-subtype (professional-asset-subtype) is visible."""
    _go_to_visible_pv(page, live_server)
    expect(page.locator('[data-testid="professional-asset-subtype"]')).to_be_visible()


def test_PVUAF08_new_uncommon_family_testid_exists(page: Page, live_server: str) -> None:
    """PVUAF08: New outer wrapper testid 'pro-val-uncommon-asset-family-select' exists in DOM (count >= 1)."""
    _go_to_visible_pv(page, live_server)
    count = page.locator('[data-testid="pro-val-uncommon-asset-family-select"]').count()
    assert count >= 1, f"pro-val-uncommon-asset-family-select must be in DOM, found: {count}"


def test_PVUAF09_new_uncommon_subtype_testid_exists(page: Page, live_server: str) -> None:
    """PVUAF09: New outer wrapper testid 'pro-val-uncommon-asset-subtype-select' exists in DOM (count >= 1)."""
    _go_to_visible_pv(page, live_server)
    count = page.locator('[data-testid="pro-val-uncommon-asset-subtype-select"]').count()
    assert count >= 1, f"pro-val-uncommon-asset-subtype-select must be in DOM, found: {count}"


# ─────────────────────────────────────────────────────────────────────────────
# PVUAF10–PVUAF15: Heritage family → heritage alias → full 7-group panel
# ─────────────────────────────────────────────────────────────────────────────

def test_PVUAF10_heritage_assets_family_option_present(page: Page, live_server: str) -> None:
    """PVUAF10: 'heritage_assets' option is present in #prof-asset-family."""
    _go_to_visible_pv(page, live_server)
    html = page.locator('#prof-asset-family').inner_html()
    assert 'value="heritage_assets"' in html, "heritage_assets option must be in #prof-asset-family"


def test_PVUAF11_heritage_family_populates_heritage_subtypes(page: Page, live_server: str) -> None:
    """PVUAF11: Selecting 'heritage_assets' family populates #prof-asset-subtype with heritage subtypes."""
    _go_to_visible_pv(page, live_server)
    _select_uncommon_family(page, "heritage_assets")
    subtype_html = page.locator('#prof-asset-subtype').inner_html()
    assert "distinguished_architectural_heritage" in subtype_html, (
        "Selecting heritage_assets must populate #prof-asset-subtype with heritage subtypes"
    )


def test_PVUAF12_heritage_alias_subtype_triggers_heritage_panel(page: Page, live_server: str) -> None:
    """PVUAF12: Selecting 'distinguished_architectural_heritage' opens the full heritage requirements panel."""
    _go_to_visible_pv(page, live_server)
    _select_uncommon_family(page, "heritage_assets")
    _select_uncommon_subtype(page, "distinguished_architectural_heritage")
    panel = page.locator('#pvr-vis-asset-requirements-panel')
    expect(panel).to_be_visible()


def test_PVUAF13_heritage_alias_panel_has_39_requirements(page: Page, live_server: str) -> None:
    """PVUAF13: Full heritage panel after alias subtype selection shows >= 39 requirements."""
    _go_to_visible_pv(page, live_server)
    _select_uncommon_family(page, "heritage_assets")
    _select_uncommon_subtype(page, "distinguished_architectural_heritage")
    panel = page.locator('#pvr-vis-asset-requirements-panel')
    expect(panel).to_be_visible()
    count_el = panel.locator('[data-testid="pro-val-heritage-requirements-count"]')
    expect(count_el).to_be_visible()
    text = count_el.text_content() or ""
    assert "39" in text, f"Heritage requirements count badge must show 39, got: {text!r}"


def test_PVUAF14_legacy_preservation_marker_visible_after_heritage_alias(page: Page, live_server: str) -> None:
    """PVUAF14: Legacy preservation marker visible when heritage alias subtype is selected via uncommon family."""
    _go_to_visible_pv(page, live_server)
    _select_uncommon_family(page, "heritage_assets")
    _select_uncommon_subtype(page, "distinguished_architectural_heritage")
    panel = page.locator('#pvr-vis-asset-requirements-panel')
    marker = panel.locator('[data-testid="pro-val-heritage-legacy-requirements-list"]')
    expect(marker).to_be_visible()


def test_PVUAF15_all_seven_heritage_groups_visible_after_alias(page: Page, live_server: str) -> None:
    """PVUAF15: All 7 heritage groups are visible in the panel after heritage alias subtype selection."""
    _go_to_visible_pv(page, live_server)
    _select_uncommon_family(page, "heritage_assets")
    _select_uncommon_subtype(page, "distinguished_architectural_heritage")
    panel = page.locator('#pvr-vis-asset-requirements-panel')
    body_text = panel.inner_text()
    expected_groups = [
        "البيانات الأساسية للأصل",
        "القيمة المعمارية والتراثية",
        "الوضع القانوني والقيود",
        "الحالة المادية وتكاليف الصيانة",
        "الدخل وإمكانية إعادة التوظيف",
        "المستندات المطلوبة",
        "متطلبات إضافية محفوظة من النسخة السابقة",
    ]
    for grp in expected_groups:
        assert grp in body_text, f"Heritage group '{grp}' must be visible in panel after alias subtype selection"


# ─────────────────────────────────────────────────────────────────────────────
# PVUAF16–PVUAF18: Other uncommon families (sports, healthcare)
# ─────────────────────────────────────────────────────────────────────────────

def test_PVUAF16_sports_family_populates_stadium_subtype(page: Page, live_server: str) -> None:
    """PVUAF16: Selecting 'sports_recreation_assets' family populates #prof-asset-subtype with 'stadium'."""
    _go_to_visible_pv(page, live_server)
    _select_uncommon_family(page, "sports_recreation_assets")
    subtype_html = page.locator('#prof-asset-subtype').inner_html()
    assert "stadium" in subtype_html, (
        "Selecting sports_recreation_assets must populate #prof-asset-subtype with stadium"
    )


def test_PVUAF17_stadium_subtype_triggers_requirements_panel(page: Page, live_server: str) -> None:
    """PVUAF17: Selecting 'stadium' subtype triggers the requirements panel."""
    _go_to_visible_pv(page, live_server)
    _select_uncommon_family(page, "sports_recreation_assets")
    _select_uncommon_subtype(page, "stadium")
    panel = page.locator('#pvr-vis-asset-requirements-panel')
    expect(panel).to_be_visible()


def test_PVUAF18_healthcare_family_populates_general_hospital(page: Page, live_server: str) -> None:
    """PVUAF18: Selecting 'healthcare_assets' family populates #prof-asset-subtype with 'general_hospital'."""
    _go_to_visible_pv(page, live_server)
    _select_uncommon_family(page, "healthcare_assets")
    subtype_html = page.locator('#prof-asset-subtype').inner_html()
    assert "general_hospital" in subtype_html, (
        "Selecting healthcare_assets must populate #prof-asset-subtype with general_hospital"
    )


# ─────────────────────────────────────────────────────────────────────────────
# PVUAF19–PVUAF21: Common asset still works; no JS errors
# ─────────────────────────────────────────────────────────────────────────────

def test_PVUAF19_common_asset_type_still_selectable(page: Page, live_server: str) -> None:
    """PVUAF19: Common asset type 'شقة سكنية' is still selectable from #asset-type."""
    _go_to_visible_pv(page, live_server)
    js_errors: list[str] = []
    page.on("pageerror", lambda e: js_errors.append(str(e)))
    page.locator('#asset-type').select_option('شقة سكنية')
    page.wait_for_timeout(300)
    assert not js_errors, f"JS errors on common asset type selection: {js_errors}"


def test_PVUAF20_no_js_errors_selecting_heritage_family(page: Page, live_server: str) -> None:
    """PVUAF20: No JS errors when selecting 'heritage_assets' family."""
    _go_to_visible_pv(page, live_server)
    js_errors: list[str] = []
    page.on("pageerror", lambda e: js_errors.append(str(e)))
    _select_uncommon_family(page, "heritage_assets")
    assert not js_errors, f"JS errors on heritage_assets family selection: {js_errors}"


def test_PVUAF21_no_js_errors_selecting_heritage_alias_subtype(page: Page, live_server: str) -> None:
    """PVUAF21: No JS errors when selecting 'distinguished_architectural_heritage' subtype."""
    _go_to_visible_pv(page, live_server)
    js_errors: list[str] = []
    page.on("pageerror", lambda e: js_errors.append(str(e)))
    _select_uncommon_family(page, "heritage_assets")
    _select_uncommon_subtype(page, "distinguished_architectural_heritage")
    assert not js_errors, f"JS errors on distinguished_architectural_heritage subtype: {js_errors}"


# ─────────────────────────────────────────────────────────────────────────────
# PVUAF22–PVUAF24: Backward compatibility testids and option preservation
# ─────────────────────────────────────────────────────────────────────────────

def test_PVUAF22_old_family_select_testid_preserved(page: Page, live_server: str) -> None:
    """PVUAF22: Original testid 'pro-val-asset-family-select' still present (backward compat)."""
    _go_to_visible_pv(page, live_server)
    count = page.locator('[data-testid="pro-val-asset-family-select"]').count()
    assert count >= 1, (
        f"pro-val-asset-family-select (original testid) must remain in DOM, found: {count}"
    )


def test_PVUAF23_old_subtype_select_testid_preserved(page: Page, live_server: str) -> None:
    """PVUAF23: Original testid 'pro-val-asset-subtype-select' still present (backward compat)."""
    _go_to_visible_pv(page, live_server)
    count = page.locator('[data-testid="pro-val-asset-subtype-select"]').count()
    assert count >= 1, (
        f"pro-val-asset-subtype-select (original testid) must remain in DOM, found: {count}"
    )


def test_PVUAF24_heritage_direct_option_not_deleted_from_asset_type(page: Page, live_server: str) -> None:
    """PVUAF24: option value='heritage' in #asset-type is NOT deleted (no-deletion rule 4)."""
    _go_to_visible_pv(page, live_server)
    html = page.locator('#asset-type').inner_html()
    assert 'value="heritage"' in html, (
        "option value='heritage' must NOT be deleted from #asset-type; it is a preserved original"
    )
