"""
PVACUR01–PVACUR37 — E2E browser tests for Professional Valuation Section 2:
Common Asset Types vs Uncommon Asset Families/Subtypes + Full Requirements.

Uses Playwright (pytest-playwright). All tests run against the live server via
the `live_server` fixture in conftest.py.

Rules:
- No commits, no new pages, no new workspaces.
- All assertions use to_be_visible(), select_option(), inner_text(), not.to_contain().
- Heritage-alias subtypes are routed to the full 7-group heritage panel.
- Cinema requirements must include all 7 specific items listed in Part G.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


# ── Helpers ──────────────────────────────────────────────────────────────────

def _go_to_pv(page: Page, live_server: str) -> None:
    """Navigate to the Professional Valuation page and stub API calls."""
    page.route("**/api/**", lambda r: r.fulfill(
        status=200, body=b'{"ok":true}', content_type="application/json"
    ))
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator('[data-testid="professional-wizard"]').wait_for(
        state="visible", timeout=12_000
    )


def _select_family(page: Page, value: str) -> None:
    page.locator("#prof-asset-family").select_option(value)
    page.wait_for_timeout(300)


def _select_subtype(page: Page, value: str) -> None:
    page.locator("#prof-asset-subtype").select_option(value)
    page.wait_for_timeout(300)


def _select_asset_type(page: Page, value: str) -> None:
    page.locator("#asset-type").select_option(value)
    page.wait_for_timeout(300)


def _section(page: Page):
    return page.locator('[data-testid="pro-val-section-asset-type-selection"]')


def _requirements_body(page: Page) -> str:
    panel = _section(page).locator('[data-testid="pro-val-asset-requirements-panel"]')
    panel.wait_for(state="visible", timeout=5_000)
    return panel.inner_text()


# ── Section 2 Visibility ─────────────────────────────────────────────────────

def test_PVACUR01_section2_container_visible(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    expect(
        page.locator('[data-testid="pro-val-section-asset-type-selection"]')
    ).to_be_visible()


def test_PVACUR02_label_common_asset_type_visible(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    card = page.locator('[data-testid="pro-val-card-asset-definition"]')
    assert "نوع الأصل العقاري الشائع" in card.inner_text()


def test_PVACUR03_label_uncommon_family_visible(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    card = page.locator('[data-testid="pro-val-card-asset-definition"]')
    assert "عائلة الأصل غير الشائعة" in card.inner_text()


def test_PVACUR04_label_uncommon_subtype_visible(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    card = page.locator('[data-testid="pro-val-card-asset-definition"]')
    assert "النوع الفرعي للأصل غير الشائع" in card.inner_text()


def test_PVACUR05_common_asset_type_select_visible(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    card = page.locator('[data-testid="pro-val-card-asset-definition"]')
    expect(card.locator('[data-testid="pro-val-asset-type-select"]')).to_be_visible()


def test_PVACUR06_common_asset_type_outer_testid(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    card = page.locator('[data-testid="pro-val-card-asset-definition"]')
    expect(card.locator('[data-testid="pro-val-common-asset-type-select"]')).to_be_visible()


def test_PVACUR07_uncommon_family_select_visible(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    expect(
        page.locator('[data-testid="professional-asset-family"]')
    ).to_be_visible()


def test_PVACUR08_uncommon_subtype_select_visible(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    expect(
        page.locator('[data-testid="professional-asset-subtype"]')
    ).to_be_visible()


# ── Common Asset List Contents ────────────────────────────────────────────────

def test_PVACUR09_common_list_includes_hotel(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    sel = page.locator("#asset-type")
    html = sel.inner_html()
    assert "hotel" in html or "فندق" in html


def test_PVACUR10_common_list_includes_vacant_land(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    sel = page.locator("#asset-type")
    html = sel.inner_html()
    assert "vacant_land" in html or "أرض فضاء" in html


def test_PVACUR11_common_list_includes_residential_unit(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    sel = page.locator("#asset-type")
    html = sel.inner_html()
    assert "residential_apartment" in html or "شقة سكنية" in html


# ── Uncommon Family List Contents ────────────────────────────────────────────

def test_PVACUR12_uncommon_family_includes_entertainment(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    sel = page.locator("#prof-asset-family")
    html = sel.inner_html()
    assert "entertainment_assets" in html


def test_PVACUR13_uncommon_family_includes_heritage(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    sel = page.locator("#prof-asset-family")
    html = sel.inner_html()
    assert "heritage_assets" in html


def test_PVACUR14_uncommon_family_includes_special_purpose(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    sel = page.locator("#prof-asset-family")
    html = sel.inner_html()
    assert "special_purpose_assets" in html


def test_PVACUR15_uncommon_family_does_not_repeat_hotel(page: Page, live_server: str) -> None:
    """hotel is a common asset type — must not appear as a VISIBLE uncommon family."""
    _go_to_pv(page, live_server)
    # Only visible (non-hidden) options in the family select
    visible_opts = page.locator(
        "#prof-asset-family option:not([hidden])"
    ).all_text_contents()
    # None of the visible uncommon family labels should be exactly "فندق" or "hotel"
    lower = [o.strip().lower() for o in visible_opts]
    assert "فندق" not in lower
    # "hotel" can exist as a subtype text but not as a standalone family option text
    for opt in visible_opts:
        assert opt.strip() not in ("hotel", "فندق"), f"hotel found in visible uncommon family: {opt!r}"


# ── Entertainment Family → Subtype Chain ────────────────────────────────────

def test_PVACUR16_selecting_entertainment_populates_subtypes(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    _select_family(page, "entertainment_assets")
    # Should have more than the placeholder option
    opts = page.locator("#prof-asset-subtype option").all()
    assert len(opts) > 1


def test_PVACUR17_entertainment_subtypes_include_cinema(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    _select_family(page, "entertainment_assets")
    html = page.locator("#prof-asset-subtype").inner_html()
    assert "cinema" in html


def test_PVACUR18_selecting_cinema_opens_requirements_panel(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    _select_family(page, "entertainment_assets")
    _select_subtype(page, "cinema")
    panel = _section(page).locator('[data-testid="pro-val-asset-requirements-panel"]')
    expect(panel).to_be_visible()
    title = _section(page).locator('[data-testid="pro-val-asset-requirements-title"]').inner_text()
    assert "سينما" in title


# ── Cinema Requirement Items ──────────────────────────────────────────────────

def test_PVACUR19_cinema_requires_number_of_screens(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    _select_family(page, "entertainment_assets")
    _select_subtype(page, "cinema")
    body = _requirements_body(page)
    assert "عدد القاعات" in body


def test_PVACUR20_cinema_requires_seat_count(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    _select_family(page, "entertainment_assets")
    _select_subtype(page, "cinema")
    body = _requirements_body(page)
    assert "عدد المقاعد" in body


def test_PVACUR21_cinema_requires_avg_ticket_price(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    _select_family(page, "entertainment_assets")
    _select_subtype(page, "cinema")
    body = _requirements_body(page)
    assert "متوسط سعر التذكرة" in body


def test_PVACUR22_cinema_requires_ticket_revenue(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    _select_family(page, "entertainment_assets")
    _select_subtype(page, "cinema")
    body = _requirements_body(page)
    assert "إيرادات التذاكر" in body


def test_PVACUR23_cinema_requires_operating_license(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    _select_family(page, "entertainment_assets")
    _select_subtype(page, "cinema")
    body = _requirements_body(page)
    assert "رخصة التشغيل" in body


def test_PVACUR24_cinema_requires_DCF_method(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    _select_family(page, "entertainment_assets")
    _select_subtype(page, "cinema")
    body = _requirements_body(page)
    assert "DCF" in body


def test_PVACUR25_cinema_requires_license_risk(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    _select_family(page, "entertainment_assets")
    _select_subtype(page, "cinema")
    body = _requirements_body(page)
    assert "مخاطر التراخيص" in body


# ── Requirements Count + Legacy Preservation ─────────────────────────────────

def test_PVACUR26_requirements_count_visible_after_cinema(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    _select_family(page, "entertainment_assets")
    _select_subtype(page, "cinema")
    expect(
        page.locator('[data-testid="pro-val-asset-requirements-count"]')
    ).to_be_visible()


def test_PVACUR27_legacy_preservation_marker_visible_after_cinema(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    _select_family(page, "entertainment_assets")
    _select_subtype(page, "cinema")
    expect(
        page.locator('[data-testid="pro-val-asset-requirements-preservation-marker"]')
    ).to_be_visible()


# ── Hotel Common Asset Requirements ──────────────────────────────────────────

def test_PVACUR28_selecting_hotel_opens_requirements(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    _select_asset_type(page, "hotel")
    panel = _section(page).locator('[data-testid="pro-val-asset-requirements-panel"]')
    expect(panel).to_be_visible()


def test_PVACUR29_hotel_requirements_include_ADR(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    _select_asset_type(page, "hotel")
    body = _requirements_body(page)
    assert "ADR" in body


def test_PVACUR30_hotel_requirements_include_RevPAR(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    _select_asset_type(page, "hotel")
    body = _requirements_body(page)
    assert "RevPAR" in body


# ── Heritage Family → Subtype Chain ──────────────────────────────────────────

def test_PVACUR31_selecting_heritage_family_populates_subtypes(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    _select_family(page, "heritage_assets")
    opts = page.locator("#prof-asset-subtype option").all()
    assert len(opts) > 1


def test_PVACUR32_selecting_distinguished_heritage_opens_panel(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    _select_family(page, "heritage_assets")
    _select_subtype(page, "distinguished_architectural_heritage")
    panel = _section(page).locator('[data-testid="pro-val-asset-requirements-panel"]')
    expect(panel).to_be_visible()


def test_PVACUR33_heritage_requirements_include_classification(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    _select_family(page, "heritage_assets")
    _select_subtype(page, "distinguished_architectural_heritage")
    body = _requirements_body(page)
    assert "تصنيف التراث المعماري" in body


def test_PVACUR34_heritage_requirements_include_official_decision(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    _select_family(page, "heritage_assets")
    _select_subtype(page, "distinguished_architectural_heritage")
    body = _requirements_body(page)
    assert "قرار التراث الرسمي" in body


# ── Duplicate + Content Exclusion Checks ─────────────────────────────────────

def test_PVACUR35_no_market_value_in_common_asset_list(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    html = page.locator("#asset-type").inner_html()
    assert "market_value" not in html
    assert "قيمة سوقية" not in html


def test_PVACUR36_no_comparable_adjustment_in_asset_lists(page: Page, live_server: str) -> None:
    _go_to_pv(page, live_server)
    asset_html = page.locator("#asset-type").inner_html()
    family_html = page.locator("#prof-asset-family").inner_html()
    assert "comparable_adjustment" not in asset_html
    assert "comparable_adjustment" not in family_html


def test_PVACUR37_no_internal_paths_in_dom(page: Page, live_server: str) -> None:
    """Backend file paths must not leak into DOM."""
    _go_to_pv(page, live_server)
    content = page.content()
    forbidden = [
        "C:\\Users", "c:\\users",
        "/home/", "site-packages",
        "professional_valuation_routes.py",
        "professional_valuation_taxonomy_v2.py",
    ]
    for pat in forbidden:
        assert pat not in content, f"Internal path leaked: {pat!r}"
