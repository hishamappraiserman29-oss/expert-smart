"""
E2E tests: Professional Valuation — Forensic Old Requirements Restore.

Verifies that the old-style #es-req-panel (gold/gray A/B/C sections + dynamic
add-building) is the primary requirements display for old-system asset types,
and that #pvr-vis-asset-requirements-panel is suppressed for those types.

Tests:
  PVFOR_E2E_01 — initial page load: #es-req-panel hidden, #pvr-vis-panel hidden
  PVFOR_E2E_02 — hotel: #es-req-panel visible, #pvr-vis-panel hidden
  PVFOR_E2E_03 — hotel: title contains 'فندق'
  PVFOR_E2E_04 — hotel: component grid present (#es-comp-grid-hotel)
  PVFOR_E2E_05 — hotel: add-building increases card count
  PVFOR_E2E_06 — factory: #es-req-panel visible, #pvr-vis-panel hidden
  PVFOR_E2E_07 — factory: component grid present (#es-comp-grid-factory)
  PVFOR_E2E_08 — apartment: #es-req-panel shows (soft message or API sections)
  PVFOR_E2E_09 — apartment: #pvr-vis-panel hidden
  PVFOR_E2E_10 — land: #es-req-panel shows, #pvr-vis-panel hidden
  PVFOR_E2E_11 — hotel: add-building creates new card with field inputs
  PVFOR_E2E_12 — hotel: default 5 building cards present
  PVFOR_E2E_13 — factory: default 4 building cards present
"""
import pytest
from playwright.sync_api import Page, expect


_LS_KEY = "es_auth"
_MOCK_SESSION = '{"token": "mock-pvfor-token", "user_id": "pvfor-test", "is_admin": false}'


def _load_page(page: Page, live_server: str) -> None:
    """Load PV page with mocked session (no reload needed — localStorage set before goto)."""
    page.goto(live_server, wait_until="networkidle", timeout=30000)
    page.evaluate(f"localStorage.setItem('{_LS_KEY}', JSON.stringify({_MOCK_SESSION}))")


def _select_asset(page: Page, value: str) -> None:
    """Select asset type from the dropdown."""
    page.locator("#asset-type").select_option(value=value)


# ── PVFOR_E2E_01 ──────────────────────────────────────────────────────────────


def test_PVFOR_E2E_01_initial_panels_hidden(page: Page, live_server: str) -> None:
    """On page load: both #es-req-panel and #pvr-vis-asset-requirements-panel are hidden."""
    _load_page(page, live_server)
    es_panel = page.locator("#es-req-panel")
    pvr_panel = page.locator("#pvr-vis-asset-requirements-panel")
    expect(es_panel).to_be_attached()
    assert not es_panel.is_visible(), "#es-req-panel must be hidden on load"
    assert not pvr_panel.is_visible(), "#pvr-vis-asset-requirements-panel must be hidden on load"


# ── PVFOR_E2E_02 ──────────────────────────────────────────────────────────────


def test_PVFOR_E2E_02_hotel_es_req_panel_visible(page: Page, live_server: str) -> None:
    """Hotel: #es-req-panel becomes visible; #pvr-vis-panel stays hidden."""
    _load_page(page, live_server)
    _select_asset(page, "فندق")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
    pvr_panel = page.locator("#pvr-vis-asset-requirements-panel")
    assert not pvr_panel.is_visible(), (
        "#pvr-vis-asset-requirements-panel must be hidden when hotel is selected"
    )


# ── PVFOR_E2E_03 ──────────────────────────────────────────────────────────────


def test_PVFOR_E2E_03_hotel_title_contains_fandoq(page: Page, live_server: str) -> None:
    """Hotel: #es-req-title contains 'فندق'."""
    _load_page(page, live_server)
    _select_asset(page, "فندق")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
    title = page.locator("#es-req-title").inner_text()
    assert "فندق" in title, f"Hotel title must contain 'فندق'. Got: {title!r}"


# ── PVFOR_E2E_04 ──────────────────────────────────────────────────────────────


def test_PVFOR_E2E_04_hotel_component_grid_present(page: Page, live_server: str) -> None:
    """Hotel: #es-comp-grid-hotel is rendered inside #es-req-panel."""
    _load_page(page, live_server)
    _select_asset(page, "فندق")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
    grid = page.locator("#es-comp-grid-hotel")
    expect(grid).to_be_attached()
    assert grid.count() > 0, "#es-comp-grid-hotel must be present after hotel selection"


# ── PVFOR_E2E_05 ──────────────────────────────────────────────────────────────


def test_PVFOR_E2E_05_hotel_add_building_works(page: Page, live_server: str) -> None:
    """Hotel: clicking إضافة مبنى increases the building card count."""
    _load_page(page, live_server)
    _select_asset(page, "فندق")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
    grid = page.locator("#es-comp-grid-hotel")
    initial_count = grid.locator(".es-comp-card").count()
    add_btn = page.locator("#es-add-comp-btn-hotel")
    expect(add_btn).to_be_visible(timeout=4_000)
    add_btn.click()
    page.wait_for_timeout(500)
    new_count = grid.locator(".es-comp-card").count()
    assert new_count == initial_count + 1, (
        f"After add-building click, card count must increase by 1. "
        f"Before: {initial_count}, After: {new_count}"
    )


# ── PVFOR_E2E_06 ──────────────────────────────────────────────────────────────


def test_PVFOR_E2E_06_factory_es_req_panel_visible(page: Page, live_server: str) -> None:
    """Factory: #es-req-panel becomes visible; #pvr-vis-panel stays hidden."""
    _load_page(page, live_server)
    _select_asset(page, "مصنع")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
    pvr_panel = page.locator("#pvr-vis-asset-requirements-panel")
    assert not pvr_panel.is_visible(), (
        "#pvr-vis-asset-requirements-panel must be hidden when factory is selected"
    )


# ── PVFOR_E2E_07 ──────────────────────────────────────────────────────────────


def test_PVFOR_E2E_07_factory_component_grid_present(page: Page, live_server: str) -> None:
    """Factory: #es-comp-grid-factory is rendered inside #es-req-panel."""
    _load_page(page, live_server)
    _select_asset(page, "مصنع")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
    grid = page.locator("#es-comp-grid-factory")
    expect(grid).to_be_attached()
    assert grid.count() > 0, "#es-comp-grid-factory must be present after factory selection"


# ── PVFOR_E2E_08 ──────────────────────────────────────────────────────────────


def test_PVFOR_E2E_08_apartment_es_req_panel_visible(page: Page, live_server: str) -> None:
    """Apartment: #es-req-panel shows (soft message or API sections)."""
    _load_page(page, live_server)
    _select_asset(page, "شقة سكنية")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)


# ── PVFOR_E2E_09 ──────────────────────────────────────────────────────────────


def test_PVFOR_E2E_09_apartment_pvr_panel_hidden(page: Page, live_server: str) -> None:
    """Apartment: #pvr-vis-asset-requirements-panel is hidden."""
    _load_page(page, live_server)
    _select_asset(page, "شقة سكنية")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
    pvr_panel = page.locator("#pvr-vis-asset-requirements-panel")
    assert not pvr_panel.is_visible(), (
        "#pvr-vis-asset-requirements-panel must be hidden for apartment"
    )


# ── PVFOR_E2E_10 ──────────────────────────────────────────────────────────────


def test_PVFOR_E2E_10_land_es_req_panel_visible(page: Page, live_server: str) -> None:
    """Land: #es-req-panel shows (soft message for API path without purpose)."""
    _load_page(page, live_server)
    _select_asset(page, "أرض فضاء")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
    pvr_panel = page.locator("#pvr-vis-asset-requirements-panel")
    assert not pvr_panel.is_visible(), (
        "#pvr-vis-asset-requirements-panel must be hidden for land"
    )


# ── PVFOR_E2E_11 ──────────────────────────────────────────────────────────────


def test_PVFOR_E2E_11_hotel_added_card_has_inputs(page: Page, live_server: str) -> None:
    """Hotel: newly added building card has field inputs (not empty)."""
    _load_page(page, live_server)
    _select_asset(page, "فندق")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
    add_btn = page.locator("#es-add-comp-btn-hotel")
    add_btn.click()
    page.wait_for_timeout(600)
    # New card should have input/select fields
    new_cards = page.locator("#es-comp-grid-hotel .es-comp-card[data-es-added]")
    if new_cards.count() == 0:
        # fallback: check ALL cards have inputs
        all_cards = page.locator("#es-comp-grid-hotel .es-comp-card")
        assert all_cards.count() > 0, "No building cards found in hotel grid"
        last_card = all_cards.last
        inputs = last_card.locator("input, select").count()
        assert inputs > 0, "Added card must contain input/select fields"
    else:
        inputs = new_cards.last.locator("input, select").count()
        assert inputs > 0, "Added card must contain input/select fields"


# ── PVFOR_E2E_12 ──────────────────────────────────────────────────────────────


def test_PVFOR_E2E_12_hotel_default_5_building_cards(page: Page, live_server: str) -> None:
    """Hotel: default rendering has 5 building component cards."""
    _load_page(page, live_server)
    _select_asset(page, "فندق")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
    grid = page.locator("#es-comp-grid-hotel")
    card_count = grid.locator(".es-comp-card").count()
    assert card_count == 5, (
        f"Hotel must default to 5 building cards. Got: {card_count}"
    )


# ── PVFOR_E2E_13 ──────────────────────────────────────────────────────────────


def test_PVFOR_E2E_13_factory_default_4_building_cards(page: Page, live_server: str) -> None:
    """Factory: default rendering has 4 building component cards."""
    _load_page(page, live_server)
    _select_asset(page, "مصنع")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
    grid = page.locator("#es-comp-grid-factory")
    card_count = grid.locator(".es-comp-card").count()
    assert card_count == 4, (
        f"Factory must default to 4 building cards. Got: {card_count}"
    )


# ── PVFOR_E2E_14 ──────────────────────────────────────────────────────────────


def test_PVFOR_E2E_14_hospital_es_req_panel_visible(page: Page, live_server: str) -> None:
    """Hospital (uncommon): #es-req-panel shows with title 'مستشفى'; #pvr-vis-panel hidden."""
    _load_page(page, live_server)
    _select_asset(page, "مستشفى")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
    title = page.locator("#es-req-title").inner_text()
    assert "مستشفى" in title, f"Hospital title must contain 'مستشفى'. Got: {title!r}"
    pvr_panel = page.locator("#pvr-vis-asset-requirements-panel")
    assert not pvr_panel.is_visible(), (
        "#pvr-vis-asset-requirements-panel must be hidden for hospital"
    )


# ── PVFOR_E2E_15 ──────────────────────────────────────────────────────────────


def test_PVFOR_E2E_15_school_es_req_panel_visible(page: Page, live_server: str) -> None:
    """School (uncommon): #es-req-panel shows with title 'مدرسة'; #pvr-vis-panel hidden."""
    _load_page(page, live_server)
    _select_asset(page, "مدرسة")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
    title = page.locator("#es-req-title").inner_text()
    assert "مدرسة" in title, f"School title must contain 'مدرسة'. Got: {title!r}"
    pvr_panel = page.locator("#pvr-vis-asset-requirements-panel")
    assert not pvr_panel.is_visible(), (
        "#pvr-vis-asset-requirements-panel must be hidden for school"
    )
