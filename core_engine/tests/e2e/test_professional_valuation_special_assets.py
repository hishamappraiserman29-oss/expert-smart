"""
PVSA E2E Browser Tests — Professional Valuation Special Assets
Tests PVSA01 through PVSA47

Covers Section 2 "اختيار نوع الأصل العقاري" UI interactions:
- Section and control visibility (PVSA01–07)
- Common asset presence (PVSA08–10)
- Uncommon family presence (PVSA11–15)
- Sports family subtype interactions (PVSA16–23)
- Cinema (entertainment) interactions (PVSA24–33)
- Requirements panel shared elements (PVSA34–35)
- Hotel requirements from common select (PVSA36–38)
- Heritage requirements (PVSA39–42)
- Structural integrity checks (PVSA43–47)
"""

import pytest
from playwright.sync_api import expect, Page


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _nav_to_prof_val(page: Page, live_server: str) -> None:
    """Navigate to the Professional Valuation page and wait for the wizard."""
    page.route("**/api/**", lambda r: r.fulfill(
        status=200, body=b'{"ok":true}', content_type="application/json"
    ))
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator('[data-testid="professional-wizard"]').wait_for(
        state="visible", timeout=15_000
    )


def _sec2(page: Page):
    """Return a locator scoped to the Section 2 asset-type-selection container."""
    return page.locator('[data-testid="pro-val-section-asset-type-selection"]')


def _select_uncommon_family(page: Page, family_value: str) -> None:
    """Select an uncommon asset family from the family dropdown."""
    family_sel = page.locator('[data-testid="professional-asset-family"]')
    family_sel.select_option(value=family_value)


def _select_uncommon_subtype(page: Page, subtype_value: str) -> None:
    """Select a subtype from the subtype dropdown."""
    subtype_sel = page.locator('[data-testid="professional-asset-subtype"]')
    subtype_sel.select_option(value=subtype_value)


def _requirements_panel(page: Page):
    """Return the Section-2-scoped requirements panel locator."""
    return _sec2(page).locator('[data-testid="pro-val-asset-requirements-panel"]')


def _requirements_title(page: Page):
    return _sec2(page).locator('[data-testid="pro-val-asset-requirements-title"]')


def _requirements_body(page: Page):
    return _sec2(page).locator('[data-testid="pro-val-asset-requirements-body"]')


def _common_asset_select(page: Page):
    """Return the Section-2-scoped common asset type select element."""
    return _sec2(page).locator('[data-testid="pro-val-asset-type-select"]')


# ──────────────────────────────────────────────────────────────────────────────
# PVSA01–07: Section and control visibility
# ──────────────────────────────────────────────────────────────────────────────

class TestSectionVisibility:

    def test_PVSA01_section2_visible(self, page: Page, live_server: str):
        """Section 2 container is visible on page load."""
        _nav_to_prof_val(page, live_server)
        expect(page.locator('[data-testid="pro-val-section-asset-type-selection"]')).to_be_visible()

    def test_PVSA02_common_asset_type_select_visible(self, page: Page, live_server: str):
        """Common asset type select wrapper is visible."""
        _nav_to_prof_val(page, live_server)
        expect(page.locator('[data-testid="pro-val-common-asset-type-select"]')).to_be_visible()

    def test_PVSA03_asset_type_select_has_options(self, page: Page, live_server: str):
        """Main common asset type select is visible and has options."""
        _nav_to_prof_val(page, live_server)
        sel = _common_asset_select(page)
        expect(sel).to_be_visible()
        count = sel.locator("option").count()
        assert count > 5, f"Expected >5 common asset options, got {count}"

    def test_PVSA04_uncommon_family_select_visible(self, page: Page, live_server: str):
        """Uncommon asset family wrapper is visible."""
        _nav_to_prof_val(page, live_server)
        expect(_sec2(page).locator('[data-testid="pro-val-asset-family-select"]').first).to_be_visible()

    def test_PVSA05_family_dropdown_visible(self, page: Page, live_server: str):
        """Family dropdown element is visible."""
        _nav_to_prof_val(page, live_server)
        expect(page.locator('[data-testid="professional-asset-family"]')).to_be_visible()

    def test_PVSA06_subtype_wrapper_exists(self, page: Page, live_server: str):
        """Subtype wrapper exists in DOM."""
        _nav_to_prof_val(page, live_server)
        expect(_sec2(page).locator('[data-testid="pro-val-asset-subtype-select"]').first).to_be_attached()

    def test_PVSA07_requirements_panel_exists(self, page: Page, live_server: str):
        """Requirements panel exists in DOM (may be hidden initially)."""
        _nav_to_prof_val(page, live_server)
        expect(_requirements_panel(page)).to_be_attached()


# ──────────────────────────────────────────────────────────────────────────────
# PVSA08–10: Common asset presence in main select
# ──────────────────────────────────────────────────────────────────────────────

class TestCommonAssetPresence:

    def test_PVSA08_hotel_in_common_asset_list(self, page: Page, live_server: str):
        """Hotel option exists in common asset type select."""
        _nav_to_prof_val(page, live_server)
        sel = _common_asset_select(page)
        option = sel.locator('option[value="hotel"]')
        expect(option).to_be_attached()

    def test_PVSA09_vacant_land_in_common_list(self, page: Page, live_server: str):
        """Vacant land option exists in common asset type select."""
        _nav_to_prof_val(page, live_server)
        sel = _common_asset_select(page)
        count = sel.locator("option").count()
        texts = [sel.locator("option").nth(i).inner_text() for i in range(count)]
        combined = " ".join(texts)
        assert "أرض" in combined or "فضاء" in combined, f"No land option found. Options: {texts[:10]}"

    def test_PVSA10_residential_unit_in_common_list(self, page: Page, live_server: str):
        """Residential unit option exists in common asset type select."""
        _nav_to_prof_val(page, live_server)
        sel = _common_asset_select(page)
        count = sel.locator("option").count()
        texts = [sel.locator("option").nth(i).inner_text() for i in range(count)]
        combined = " ".join(texts)
        assert "سكني" in combined or "شقة" in combined, f"No residential option found. Options: {texts[:10]}"


# ──────────────────────────────────────────────────────────────────────────────
# PVSA11–15: Uncommon family presence in family dropdown
# ──────────────────────────────────────────────────────────────────────────────

class TestUncommonFamilyPresence:

    def test_PVSA11_sports_recreation_family_present(self, page: Page, live_server: str):
        """sports_recreation_assets option exists in family dropdown."""
        _nav_to_prof_val(page, live_server)
        family_sel = page.locator('[data-testid="professional-asset-family"]')
        option = family_sel.locator('option[value="sports_recreation_assets"]')
        expect(option).to_be_attached()

    def test_PVSA12_entertainment_family_present(self, page: Page, live_server: str):
        """entertainment_assets option exists in family dropdown."""
        _nav_to_prof_val(page, live_server)
        family_sel = page.locator('[data-testid="professional-asset-family"]')
        option = family_sel.locator('option[value="entertainment_assets"]')
        expect(option).to_be_attached()

    def test_PVSA13_heritage_family_present(self, page: Page, live_server: str):
        """heritage_assets option exists in family dropdown."""
        _nav_to_prof_val(page, live_server)
        family_sel = page.locator('[data-testid="professional-asset-family"]')
        option = family_sel.locator('option[value="heritage_assets"]')
        expect(option).to_be_attached()

    def test_PVSA14_special_purpose_family_present(self, page: Page, live_server: str):
        """special_purpose_assets or special_purpose option exists in family dropdown."""
        _nav_to_prof_val(page, live_server)
        family_sel = page.locator('[data-testid="professional-asset-family"]')
        count = family_sel.locator("option").count()
        values = [family_sel.locator("option").nth(i).get_attribute("value") for i in range(count)]
        has_sp = any("special_purpose" in (v or "") for v in values)
        assert has_sp, f"No special_purpose family found. Values: {values}"

    def test_PVSA15_family_dropdown_has_multiple_families(self, page: Page, live_server: str):
        """Family dropdown must have at least 10 options."""
        _nav_to_prof_val(page, live_server)
        family_sel = page.locator('[data-testid="professional-asset-family"]')
        count = family_sel.locator("option").count()
        assert count >= 10, f"Expected ≥10 family options, got {count}"


# ──────────────────────────────────────────────────────────────────────────────
# PVSA16–23: Sports family → padel tennis court interactions
# ──────────────────────────────────────────────────────────────────────────────

class TestSportsFamilyPadelInteractions:

    def test_PVSA16_selecting_sports_family_populates_subtypes(self, page: Page, live_server: str):
        """Selecting sports_recreation_assets populates the subtype dropdown."""
        _nav_to_prof_val(page, live_server)
        _select_uncommon_family(page, "sports_recreation_assets")
        subtype_sel = page.locator('[data-testid="professional-asset-subtype"]')
        count = subtype_sel.locator("option").count()
        assert count >= 2, f"Expected ≥2 subtype options after sports family selection, got {count}"

    def test_PVSA17_padel_tennis_court_in_sports_subtypes(self, page: Page, live_server: str):
        """padel_tennis_court (singular) option is in sports subtype list."""
        _nav_to_prof_val(page, live_server)
        _select_uncommon_family(page, "sports_recreation_assets")
        subtype_sel = page.locator('[data-testid="professional-asset-subtype"]')
        option = subtype_sel.locator('option[value="padel_tennis_court"]')
        expect(option).to_be_attached()

    def test_PVSA18_selecting_padel_opens_requirements_panel(self, page: Page, live_server: str):
        """Selecting padel_tennis_court makes the requirements panel visible."""
        _nav_to_prof_val(page, live_server)
        _select_uncommon_family(page, "sports_recreation_assets")
        _select_uncommon_subtype(page, "padel_tennis_court")
        expect(_requirements_panel(page)).to_be_visible(timeout=5_000)

    def test_PVSA19_padel_requirements_title_contains_padel(self, page: Page, live_server: str):
        """Requirements panel title must contain 'ملعب بادل' or 'بادل تنس'."""
        _nav_to_prof_val(page, live_server)
        _select_uncommon_family(page, "sports_recreation_assets")
        _select_uncommon_subtype(page, "padel_tennis_court")
        title = _requirements_title(page)
        expect(title).to_be_visible()
        title_text = title.inner_text()
        assert "بادل" in title_text, f"Title should contain 'بادل', got: '{title_text}'"

    def test_PVSA20_padel_requirements_include_number_of_courts(self, page: Page, live_server: str):
        """Requirements body must contain 'ملاعب البادل' or 'عدد ملاعب'."""
        _nav_to_prof_val(page, live_server)
        _select_uncommon_family(page, "sports_recreation_assets")
        _select_uncommon_subtype(page, "padel_tennis_court")
        body = _requirements_body(page)
        expect(body).to_be_visible()
        body_text = body.inner_text()
        assert "ملاعب البادل" in body_text or "عدد ملاعب" in body_text, (
            f"'عدد ملاعب البادل' not found in requirements body. Body: {body_text[:300]}"
        )

    def test_PVSA21_padel_requirements_include_booking_rate(self, page: Page, live_server: str):
        """Requirements body must contain 'سعر الحجز' or 'متوسط سعر الحجز'."""
        _nav_to_prof_val(page, live_server)
        _select_uncommon_family(page, "sports_recreation_assets")
        _select_uncommon_subtype(page, "padel_tennis_court")
        body_text = _requirements_body(page).inner_text()
        assert "الحجز" in body_text, (
            f"'سعر الحجز' not found in requirements body. Body: {body_text[:300]}"
        )

    def test_PVSA22_padel_requirements_include_occupancy_rate(self, page: Page, live_server: str):
        """Requirements body must contain 'معدل الإشغال'."""
        _nav_to_prof_val(page, live_server)
        _select_uncommon_family(page, "sports_recreation_assets")
        _select_uncommon_subtype(page, "padel_tennis_court")
        body_text = _requirements_body(page).inner_text()
        assert "الإشغال" in body_text, (
            f"'معدل الإشغال' not found. Body: {body_text[:300]}"
        )

    def test_PVSA23_padel_requirements_include_dcf(self, page: Page, live_server: str):
        """Requirements body must contain 'DCF' in methods group."""
        _nav_to_prof_val(page, live_server)
        _select_uncommon_family(page, "sports_recreation_assets")
        _select_uncommon_subtype(page, "padel_tennis_court")
        body_text = _requirements_body(page).inner_text()
        assert "DCF" in body_text, (
            f"'DCF' not found in padel requirements. Body: {body_text[:300]}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# PVSA24–33: Cinema (entertainment) interactions
# ──────────────────────────────────────────────────────────────────────────────

class TestCinemaInteractions:

    def test_PVSA24_selecting_entertainment_populates_subtypes(self, page: Page, live_server: str):
        """Selecting entertainment_assets family populates subtype dropdown."""
        _nav_to_prof_val(page, live_server)
        _select_uncommon_family(page, "entertainment_assets")
        subtype_sel = page.locator('[data-testid="professional-asset-subtype"]')
        count = subtype_sel.locator("option").count()
        assert count >= 2, f"Expected ≥2 subtypes for entertainment_assets, got {count}"

    def test_PVSA25_cinema_in_entertainment_subtypes(self, page: Page, live_server: str):
        """cinema option exists in entertainment subtypes."""
        _nav_to_prof_val(page, live_server)
        _select_uncommon_family(page, "entertainment_assets")
        subtype_sel = page.locator('[data-testid="professional-asset-subtype"]')
        option = subtype_sel.locator('option[value="cinema"]')
        expect(option).to_be_attached()

    def test_PVSA26_selecting_cinema_opens_requirements_panel(self, page: Page, live_server: str):
        """Selecting cinema makes the requirements panel visible."""
        _nav_to_prof_val(page, live_server)
        _select_uncommon_family(page, "entertainment_assets")
        _select_uncommon_subtype(page, "cinema")
        expect(_requirements_panel(page)).to_be_visible(timeout=5_000)

    def test_PVSA27_cinema_requirements_title_contains_cinema(self, page: Page, live_server: str):
        """Cinema requirements title must contain 'سينما'."""
        _nav_to_prof_val(page, live_server)
        _select_uncommon_family(page, "entertainment_assets")
        _select_uncommon_subtype(page, "cinema")
        title = _requirements_title(page)
        expect(title).to_be_visible()
        title_text = title.inner_text()
        assert "سينما" in title_text, f"Title should contain 'سينما', got: '{title_text}'"

    def test_PVSA28_cinema_requirements_include_number_of_halls(self, page: Page, live_server: str):
        """Cinema requirements must contain 'القاعات' or 'عدد القاعات'."""
        _nav_to_prof_val(page, live_server)
        _select_uncommon_family(page, "entertainment_assets")
        _select_uncommon_subtype(page, "cinema")
        body_text = _requirements_body(page).inner_text()
        assert "القاعات" in body_text, (
            f"'عدد القاعات' not found in cinema requirements. Body: {body_text[:300]}"
        )

    def test_PVSA29_cinema_requirements_include_seats(self, page: Page, live_server: str):
        """Cinema requirements must contain 'المقاعد'."""
        _nav_to_prof_val(page, live_server)
        _select_uncommon_family(page, "entertainment_assets")
        _select_uncommon_subtype(page, "cinema")
        body_text = _requirements_body(page).inner_text()
        assert "المقاعد" in body_text, f"'المقاعد' not found. Body: {body_text[:300]}"

    def test_PVSA30_cinema_requirements_include_ticket_price(self, page: Page, live_server: str):
        """Cinema requirements must contain 'سعر التذكرة'."""
        _nav_to_prof_val(page, live_server)
        _select_uncommon_family(page, "entertainment_assets")
        _select_uncommon_subtype(page, "cinema")
        body_text = _requirements_body(page).inner_text()
        assert "التذكرة" in body_text, f"'سعر التذكرة' not found. Body: {body_text[:300]}"

    def test_PVSA31_cinema_requirements_include_operating_license(self, page: Page, live_server: str):
        """Cinema requirements must contain 'رخصة التشغيل'."""
        _nav_to_prof_val(page, live_server)
        _select_uncommon_family(page, "entertainment_assets")
        _select_uncommon_subtype(page, "cinema")
        body_text = _requirements_body(page).inner_text()
        assert "التشغيل" in body_text, f"'رخصة التشغيل' not found. Body: {body_text[:300]}"

    def test_PVSA32_cinema_requirements_include_dcf(self, page: Page, live_server: str):
        """Cinema requirements must contain 'DCF'."""
        _nav_to_prof_val(page, live_server)
        _select_uncommon_family(page, "entertainment_assets")
        _select_uncommon_subtype(page, "cinema")
        body_text = _requirements_body(page).inner_text()
        assert "DCF" in body_text, f"'DCF' not found in cinema requirements. Body: {body_text[:300]}"

    def test_PVSA33_cinema_requirements_include_risks(self, page: Page, live_server: str):
        """Cinema requirements must contain 'مخاطر' (risks section)."""
        _nav_to_prof_val(page, live_server)
        _select_uncommon_family(page, "entertainment_assets")
        _select_uncommon_subtype(page, "cinema")
        body_text = _requirements_body(page).inner_text()
        assert "مخاطر" in body_text, f"'مخاطر' not found. Body: {body_text[:300]}"


# ──────────────────────────────────────────────────────────────────────────────
# PVSA34–35: Requirements panel shared elements
# ──────────────────────────────────────────────────────────────────────────────

class TestRequirementsPanelSharedElements:

    def test_PVSA34_requirements_count_badge_visible_for_padel(self, page: Page, live_server: str):
        """Requirements count badge is visible after padel selection."""
        _nav_to_prof_val(page, live_server)
        _select_uncommon_family(page, "sports_recreation_assets")
        _select_uncommon_subtype(page, "padel_tennis_court")
        count_el = _sec2(page).locator('[data-testid="pro-val-asset-requirements-count"]')
        expect(count_el).to_be_visible()
        count_text = count_el.inner_text()
        assert "المتطلبات" in count_text or any(c.isdigit() for c in count_text), (
            f"Count badge text unexpected: '{count_text}'"
        )

    def test_PVSA35_legacy_preservation_marker_visible_for_padel(self, page: Page, live_server: str):
        """Legacy preservation marker is visible after padel selection."""
        _nav_to_prof_val(page, live_server)
        _select_uncommon_family(page, "sports_recreation_assets")
        _select_uncommon_subtype(page, "padel_tennis_court")
        marker = _sec2(page).locator('[data-testid="pro-val-asset-requirements-preservation-marker"]')
        expect(marker).to_be_visible()


# ──────────────────────────────────────────────────────────────────────────────
# PVSA36–38: Hotel requirements from common select
# ──────────────────────────────────────────────────────────────────────────────

class TestHotelRequirements:

    def test_PVSA36_selecting_hotel_opens_requirements_panel(self, page: Page, live_server: str):
        """Selecting hotel from common asset type list shows requirements panel."""
        _nav_to_prof_val(page, live_server)
        _common_asset_select(page).select_option(value="hotel")
        expect(_requirements_panel(page)).to_be_visible(timeout=5_000)

    def test_PVSA37_hotel_requirements_include_adr(self, page: Page, live_server: str):
        """Hotel requirements panel must contain 'ADR'."""
        _nav_to_prof_val(page, live_server)
        _common_asset_select(page).select_option(value="hotel")
        body = _requirements_body(page)
        expect(body).to_be_visible()
        body_text = body.inner_text()
        assert "ADR" in body_text, f"'ADR' not found in hotel requirements. Body: {body_text[:300]}"

    def test_PVSA38_hotel_requirements_include_revpar(self, page: Page, live_server: str):
        """Hotel requirements panel must contain 'RevPAR'."""
        _nav_to_prof_val(page, live_server)
        _common_asset_select(page).select_option(value="hotel")
        body_text = _requirements_body(page).inner_text()
        assert "RevPAR" in body_text, f"'RevPAR' not found in hotel requirements. Body: {body_text[:300]}"


# ──────────────────────────────────────────────────────────────────────────────
# PVSA39–42: Heritage requirements
# ──────────────────────────────────────────────────────────────────────────────

class TestHeritageRequirements:

    def test_PVSA39_selecting_heritage_family_populates_subtypes(self, page: Page, live_server: str):
        """Selecting heritage_assets family populates subtype dropdown."""
        _nav_to_prof_val(page, live_server)
        _select_uncommon_family(page, "heritage_assets")
        subtype_sel = page.locator('[data-testid="professional-asset-subtype"]')
        count = subtype_sel.locator("option").count()
        assert count >= 2, f"Expected ≥2 heritage subtypes, got {count}"

    def test_PVSA40_distinguished_heritage_in_subtypes(self, page: Page, live_server: str):
        """distinguished_architectural_heritage is available as a heritage subtype."""
        _nav_to_prof_val(page, live_server)
        _select_uncommon_family(page, "heritage_assets")
        subtype_sel = page.locator('[data-testid="professional-asset-subtype"]')
        option = subtype_sel.locator('option[value="distinguished_architectural_heritage"]')
        expect(option).to_be_attached()

    def test_PVSA41_selecting_distinguished_heritage_opens_panel(self, page: Page, live_server: str):
        """Selecting distinguished_architectural_heritage shows requirements panel."""
        _nav_to_prof_val(page, live_server)
        _select_uncommon_family(page, "heritage_assets")
        _select_uncommon_subtype(page, "distinguished_architectural_heritage")
        expect(_requirements_panel(page)).to_be_visible(timeout=5_000)

    def test_PVSA42_heritage_requirements_include_official_decision(self, page: Page, live_server: str):
        """Heritage requirements must contain 'التراث' in body text."""
        _nav_to_prof_val(page, live_server)
        _select_uncommon_family(page, "heritage_assets")
        _select_uncommon_subtype(page, "distinguished_architectural_heritage")
        body = _requirements_body(page)
        expect(body).to_be_visible()
        body_text = body.inner_text()
        assert "التراث" in body_text or "تراث" in body_text, (
            f"Heritage context missing from body. Body: {body_text[:300]}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# PVSA43–47: Structural integrity and no-injection checks
# ──────────────────────────────────────────────────────────────────────────────

class TestStructuralIntegrity:

    def test_PVSA43_no_external_api_calls_in_dom(self, page: Page, live_server: str):
        """DOM must not contain references to external API URLs in asset requirement panels."""
        _nav_to_prof_val(page, live_server)
        _select_uncommon_family(page, "sports_recreation_assets")
        _select_uncommon_subtype(page, "padel_tennis_court")
        body_text = _requirements_body(page).inner_text()
        forbidden = ["http://", "https://", "qdrant", "openai", "external_api"]
        for f in forbidden:
            assert f not in body_text.lower(), (
                f"Forbidden external reference '{f}' found in requirements panel"
            )

    def test_PVSA44_no_internal_paths_in_requirements_panel(self, page: Page, live_server: str):
        """Requirements panel must not expose internal file paths."""
        _nav_to_prof_val(page, live_server)
        _select_uncommon_family(page, "entertainment_assets")
        _select_uncommon_subtype(page, "cinema")
        body_text = _requirements_body(page).inner_text()
        forbidden_paths = ["core_engine/", "C:\\", "/home/", "site-packages"]
        for fp in forbidden_paths:
            assert fp not in body_text, (
                f"Internal path '{fp}' exposed in requirements panel"
            )

    def test_PVSA45_requirements_panel_title_testid_exists(self, page: Page, live_server: str):
        """pro-val-asset-requirements-title testid exists and is attached."""
        _nav_to_prof_val(page, live_server)
        expect(_requirements_title(page)).to_be_attached()

    def test_PVSA46_requirements_panel_body_testid_exists(self, page: Page, live_server: str):
        """pro-val-asset-requirements-body testid exists and is attached."""
        _nav_to_prof_val(page, live_server)
        expect(_requirements_body(page)).to_be_attached()

    def test_PVSA47_padel_tennis_courts_plural_still_in_subtypes(self, page: Page, live_server: str):
        """Legacy padel_tennis_courts (plural) must still be in sports subtypes — no deletion."""
        _nav_to_prof_val(page, live_server)
        _select_uncommon_family(page, "sports_recreation_assets")
        subtype_sel = page.locator('[data-testid="professional-asset-subtype"]')
        option = subtype_sel.locator('option[value="padel_tennis_courts"]')
        expect(option).to_be_attached()
