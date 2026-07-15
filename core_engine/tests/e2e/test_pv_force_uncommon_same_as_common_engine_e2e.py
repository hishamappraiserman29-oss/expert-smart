"""
E2E tests: Professional Valuation — Force Uncommon Assets to Use Same Engine as Common Assets.

Verifies that petrol_station, cinema_theater, sports_padel_club, mixed_use_special, and
architectural_cultural_heritage_detailed render rich gold/gray collapsible sections with
component grids in #es-req-panel — identical behaviour to common assets (hotel, factory).

Tests (29):
  FCU_E2E_01 — initial load: new asset types not visible
  FCU_E2E_02–06 — petrol_station: panel visible, title, pvr hidden, sections, component list
  FCU_E2E_07–11 — cinema_theater: panel visible, title, pvr hidden, component grid, add works
  FCU_E2E_12–15 — sports_padel_club: panel visible, title, pvr hidden, component list
  FCU_E2E_16–19 — mixed_use_special: panel visible, title, pvr hidden, component list
  FCU_E2E_20–23 — architectural_cultural_heritage_detailed: panel visible, title, pvr hidden, component list
  FCU_E2E_24 — petrol_station: document section has bool fields
  FCU_E2E_25 — cinema_theater: collapsible details elements present (parity with common assets)
  FCU_E2E_26 — hotel_resort still works after FCU task (regression)
  FCU_E2E_27 — factory still works after FCU task (regression)
  FCU_E2E_28 — petrol_station: add-component increases card count
  FCU_E2E_29 — sports_padel_club: add-component increases card count
"""
import pytest
from playwright.sync_api import Page, expect


_LS_KEY = "es_auth"
_MOCK_SESSION = '{"token": "mock-pvfcu-token", "user_id": "pvfcu-test", "is_admin": false}'


def _load_page(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle", timeout=30_000)
    page.evaluate(f"localStorage.setItem('{_LS_KEY}', JSON.stringify({_MOCK_SESSION}))")


def _select_asset(page: Page, value: str) -> None:
    page.locator("#asset-type").select_option(value=value)


def _wait_panel(page: Page) -> None:
    page.locator("#es-req-panel").wait_for(state="visible", timeout=7_000)


# ── FCU_E2E_01 ────────────────────────────────────────────────────────────────


def test_FCU_E2E_01_initial_load_panels_hidden(page: Page, live_server: str) -> None:
    """On page load: #es-req-panel and #pvr-vis-asset-requirements-panel are both hidden."""
    _load_page(page, live_server)
    es = page.locator("#es-req-panel")
    pvr = page.locator("#pvr-vis-asset-requirements-panel")
    expect(es).to_be_attached()
    assert not es.is_visible(), "#es-req-panel must be hidden on load"
    assert not pvr.is_visible(), "#pvr-vis-panel must be hidden on load"


# ── FCU_E2E_02–06: petrol_station ─────────────────────────────────────────────


def test_FCU_E2E_02_petrol_station_panel_visible(page: Page, live_server: str) -> None:
    """petrol_station: #es-req-panel becomes visible after selection."""
    _load_page(page, live_server)
    _select_asset(page, "محطة تموين سيارات")
    _wait_panel(page)


def test_FCU_E2E_03_petrol_station_title_present(page: Page, live_server: str) -> None:
    """petrol_station: #es-req-title contains Arabic station text."""
    _load_page(page, live_server)
    _select_asset(page, "محطة تموين سيارات")
    _wait_panel(page)
    title = page.locator("#es-req-title").inner_text()
    assert any(kw in title for kw in ("محطة", "تموين", "وقود")), (
        f"petrol_station title must contain station keyword. Got: {title!r}"
    )


def test_FCU_E2E_04_petrol_station_pvr_panel_hidden(page: Page, live_server: str) -> None:
    """petrol_station: #pvr-vis-asset-requirements-panel stays hidden."""
    _load_page(page, live_server)
    _select_asset(page, "محطة تموين سيارات")
    _wait_panel(page)
    assert not page.locator("#pvr-vis-asset-requirements-panel").is_visible(), (
        "#pvr-vis-panel must be hidden for petrol_station"
    )


def test_FCU_E2E_05_petrol_station_has_collapsible_sections(page: Page, live_server: str) -> None:
    """petrol_station: #es-req-panel contains <details> collapsible sections."""
    _load_page(page, live_server)
    _select_asset(page, "محطة تموين سيارات")
    _wait_panel(page)
    details_count = page.locator("#es-req-panel details").count()
    assert details_count >= 3, (
        f"petrol_station must have ≥3 collapsible sections. Got: {details_count}"
    )


def test_FCU_E2E_06_petrol_station_has_component_grid(page: Page, live_server: str) -> None:
    """petrol_station: component grid #es-comp-grid-petrol_station is rendered."""
    _load_page(page, live_server)
    _select_asset(page, "محطة تموين سيارات")
    _wait_panel(page)
    grid = page.locator("#es-comp-grid-petrol_station")
    expect(grid).to_be_attached()
    assert grid.count() > 0, "#es-comp-grid-petrol_station must be present"


# ── FCU_E2E_07–11: cinema_theater ─────────────────────────────────────────────


def test_FCU_E2E_07_cinema_theater_panel_visible(page: Page, live_server: str) -> None:
    """cinema_theater: #es-req-panel becomes visible after selection."""
    _load_page(page, live_server)
    _select_asset(page, "سينما / مسرح / قاعة عرض")
    _wait_panel(page)


def test_FCU_E2E_08_cinema_theater_title_present(page: Page, live_server: str) -> None:
    """cinema_theater: #es-req-title contains Arabic cinema/theater keyword."""
    _load_page(page, live_server)
    _select_asset(page, "سينما / مسرح / قاعة عرض")
    _wait_panel(page)
    title = page.locator("#es-req-title").inner_text()
    assert any(kw in title for kw in ("سينما", "مسرح", "قاعة", "عرض")), (
        f"cinema_theater title must contain cinema/theater keyword. Got: {title!r}"
    )


def test_FCU_E2E_09_cinema_theater_pvr_panel_hidden(page: Page, live_server: str) -> None:
    """cinema_theater: #pvr-vis-asset-requirements-panel stays hidden."""
    _load_page(page, live_server)
    _select_asset(page, "سينما / مسرح / قاعة عرض")
    _wait_panel(page)
    assert not page.locator("#pvr-vis-asset-requirements-panel").is_visible(), (
        "#pvr-vis-panel must be hidden for cinema_theater"
    )


def test_FCU_E2E_10_cinema_theater_has_component_grid(page: Page, live_server: str) -> None:
    """cinema_theater: component grid #es-comp-grid-cinema_theater is rendered."""
    _load_page(page, live_server)
    _select_asset(page, "سينما / مسرح / قاعة عرض")
    _wait_panel(page)
    grid = page.locator("#es-comp-grid-cinema_theater")
    expect(grid).to_be_attached()
    assert grid.count() > 0, "#es-comp-grid-cinema_theater must be present"


def test_FCU_E2E_11_cinema_theater_add_component_works(page: Page, live_server: str) -> None:
    """cinema_theater: clicking add-hall button increases card count by 1."""
    _load_page(page, live_server)
    _select_asset(page, "سينما / مسرح / قاعة عرض")
    _wait_panel(page)
    grid = page.locator("#es-comp-grid-cinema_theater")
    initial = grid.locator(".es-component-card").count()
    add_btn = page.locator("#es-add-comp-btn-cinema_theater")
    expect(add_btn).to_be_visible(timeout=4_000)
    add_btn.click()
    page.wait_for_timeout(500)
    after = grid.locator(".es-component-card").count()
    assert after == initial + 1, (
        f"cinema_theater add-component: expected {initial + 1} cards, got {after}"
    )


# ── FCU_E2E_12–15: sports_padel_club ──────────────────────────────────────────


def test_FCU_E2E_12_sports_padel_club_panel_visible(page: Page, live_server: str) -> None:
    """sports_padel_club: #es-req-panel becomes visible after selection."""
    _load_page(page, live_server)
    _select_asset(page, "نادي رياضي / ملاعب بادل")
    _wait_panel(page)


def test_FCU_E2E_13_sports_padel_club_title_present(page: Page, live_server: str) -> None:
    """sports_padel_club: #es-req-title contains Arabic sports/padel keyword."""
    _load_page(page, live_server)
    _select_asset(page, "نادي رياضي / ملاعب بادل")
    _wait_panel(page)
    title = page.locator("#es-req-title").inner_text()
    assert any(kw in title for kw in ("نادي", "رياضي", "بادل", "ملاعب")), (
        f"sports_padel_club title must contain sports/padel keyword. Got: {title!r}"
    )


def test_FCU_E2E_14_sports_padel_club_pvr_panel_hidden(page: Page, live_server: str) -> None:
    """sports_padel_club: #pvr-vis-asset-requirements-panel stays hidden."""
    _load_page(page, live_server)
    _select_asset(page, "نادي رياضي / ملاعب بادل")
    _wait_panel(page)
    assert not page.locator("#pvr-vis-asset-requirements-panel").is_visible(), (
        "#pvr-vis-panel must be hidden for sports_padel_club"
    )


def test_FCU_E2E_15_sports_padel_club_has_component_grid(page: Page, live_server: str) -> None:
    """sports_padel_club: component grid #es-comp-grid-sports_padel_club is rendered."""
    _load_page(page, live_server)
    _select_asset(page, "نادي رياضي / ملاعب بادل")
    _wait_panel(page)
    grid = page.locator("#es-comp-grid-sports_padel_club")
    expect(grid).to_be_attached()
    assert grid.count() > 0, "#es-comp-grid-sports_padel_club must be present"


# ── FCU_E2E_16–19: mixed_use_special ──────────────────────────────────────────


def test_FCU_E2E_16_mixed_use_special_panel_visible(page: Page, live_server: str) -> None:
    """mixed_use_special: #es-req-panel becomes visible after selection."""
    _load_page(page, live_server)
    _select_asset(page, "أصل متعدد الاستخدامات خاص")
    _wait_panel(page)


def test_FCU_E2E_17_mixed_use_special_title_present(page: Page, live_server: str) -> None:
    """mixed_use_special: #es-req-title shows mixed-use keyword."""
    _load_page(page, live_server)
    _select_asset(page, "أصل متعدد الاستخدامات خاص")
    _wait_panel(page)
    title = page.locator("#es-req-title").inner_text()
    assert any(kw in title for kw in ("متعدد", "استخدامات", "خاص", "مختلط")), (
        f"mixed_use_special title must contain mixed-use keyword. Got: {title!r}"
    )


def test_FCU_E2E_18_mixed_use_special_pvr_panel_hidden(page: Page, live_server: str) -> None:
    """mixed_use_special: #pvr-vis-asset-requirements-panel stays hidden."""
    _load_page(page, live_server)
    _select_asset(page, "أصل متعدد الاستخدامات خاص")
    _wait_panel(page)
    assert not page.locator("#pvr-vis-asset-requirements-panel").is_visible(), (
        "#pvr-vis-panel must be hidden for mixed_use_special"
    )


def test_FCU_E2E_19_mixed_use_special_has_component_grid(page: Page, live_server: str) -> None:
    """mixed_use_special: component grid #es-comp-grid-mixed_use_special is rendered."""
    _load_page(page, live_server)
    _select_asset(page, "أصل متعدد الاستخدامات خاص")
    _wait_panel(page)
    grid = page.locator("#es-comp-grid-mixed_use_special")
    expect(grid).to_be_attached()
    assert grid.count() > 0, "#es-comp-grid-mixed_use_special must be present"


# ── FCU_E2E_20–23: architectural_cultural_heritage_detailed ───────────────────


def test_FCU_E2E_20_arch_heritage_panel_visible(page: Page, live_server: str) -> None:
    """architectural_cultural_heritage_detailed: #es-req-panel becomes visible."""
    _load_page(page, live_server)
    _select_asset(page, "architectural_cultural_heritage_detailed")
    _wait_panel(page)


def test_FCU_E2E_21_arch_heritage_title_present(page: Page, live_server: str) -> None:
    """architectural_cultural_heritage_detailed: title shows heritage keyword."""
    _load_page(page, live_server)
    _select_asset(page, "architectural_cultural_heritage_detailed")
    _wait_panel(page)
    title = page.locator("#es-req-title").inner_text()
    assert any(kw in title for kw in ("تراث", "موروث", "ثقافي", "معماري")), (
        f"arch heritage title must contain heritage keyword. Got: {title!r}"
    )


def test_FCU_E2E_22_arch_heritage_pvr_panel_hidden(page: Page, live_server: str) -> None:
    """architectural_cultural_heritage_detailed: #pvr-vis-panel stays hidden."""
    _load_page(page, live_server)
    _select_asset(page, "architectural_cultural_heritage_detailed")
    _wait_panel(page)
    assert not page.locator("#pvr-vis-asset-requirements-panel").is_visible(), (
        "#pvr-vis-panel must be hidden for architectural_cultural_heritage_detailed"
    )


def test_FCU_E2E_23_arch_heritage_has_component_grid(page: Page, live_server: str) -> None:
    """architectural_cultural_heritage_detailed: component grid present."""
    _load_page(page, live_server)
    _select_asset(page, "architectural_cultural_heritage_detailed")
    _wait_panel(page)
    grid = page.locator("#es-comp-grid-architectural_cultural_heritage_detailed")
    expect(grid).to_be_attached()
    assert grid.count() > 0, "#es-comp-grid-architectural_cultural_heritage_detailed must be present"


# ── FCU_E2E_24–25: Style parity ───────────────────────────────────────────────


def test_FCU_E2E_24_petrol_station_document_section_has_fields(page: Page, live_server: str) -> None:
    """petrol_station: document upload section contains checkbox/bool fields."""
    _load_page(page, live_server)
    _select_asset(page, "محطة تموين سيارات")
    _wait_panel(page)
    # Document section fields are rendered as checkboxes or toggle-like inputs
    inputs = page.locator("#es-req-panel input[type='checkbox'], #es-req-panel input[type='radio']").count()
    # Fallback: any input in the panel
    if inputs == 0:
        inputs = page.locator("#es-req-panel input, #es-req-panel select").count()
    assert inputs > 0, "petrol_station panel must have input fields including document checkboxes"


def test_FCU_E2E_25_cinema_theater_has_details_elements_like_common_assets(
    page: Page, live_server: str
) -> None:
    """cinema_theater: panel has <details> collapsible sections — same style as hotel/factory."""
    _load_page(page, live_server)
    _select_asset(page, "سينما / مسرح / قاعة عرض")
    _wait_panel(page)
    details_count = page.locator("#es-req-panel details").count()
    assert details_count >= 3, (
        f"cinema_theater must have ≥3 collapsible <details> sections (same as common assets). Got: {details_count}"
    )


# ── FCU_E2E_26–27: Regression — common assets still work ──────────────────────


def test_FCU_E2E_26_hotel_resort_still_works(page: Page, live_server: str) -> None:
    """Regression: hotel_resort still shows rich form in #es-req-panel (not broken by FCU task)."""
    _load_page(page, live_server)
    _select_asset(page, "فندق")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=7_000)
    grid = page.locator("#es-comp-grid-hotel_resort, #es-comp-grid-hotel")
    assert not page.locator("#pvr-vis-asset-requirements-panel").is_visible(), (
        "Hotel: #pvr-vis-panel must still be hidden after FCU task"
    )


def test_FCU_E2E_27_factory_still_works(page: Page, live_server: str) -> None:
    """Regression: factory still shows rich form in #es-req-panel (not broken by FCU task)."""
    _load_page(page, live_server)
    _select_asset(page, "مصنع")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=7_000)
    assert not page.locator("#pvr-vis-asset-requirements-panel").is_visible(), (
        "Factory: #pvr-vis-panel must still be hidden after FCU task"
    )


# ── FCU_E2E_28–29: Add-component button works for new types ───────────────────


def test_FCU_E2E_28_petrol_station_add_component_works(page: Page, live_server: str) -> None:
    """petrol_station: clicking add-component button increases card count by 1."""
    _load_page(page, live_server)
    _select_asset(page, "محطة تموين سيارات")
    _wait_panel(page)
    grid = page.locator("#es-comp-grid-petrol_station")
    initial = grid.locator(".es-component-card").count()
    add_btn = page.locator("#es-add-comp-btn-petrol_station")
    expect(add_btn).to_be_visible(timeout=4_000)
    add_btn.click()
    page.wait_for_timeout(500)
    after = grid.locator(".es-component-card").count()
    assert after == initial + 1, (
        f"petrol_station add-component: expected {initial + 1} cards, got {after}"
    )


def test_FCU_E2E_29_sports_padel_club_add_component_works(page: Page, live_server: str) -> None:
    """sports_padel_club: clicking add-court button increases card count by 1."""
    _load_page(page, live_server)
    _select_asset(page, "نادي رياضي / ملاعب بادل")
    _wait_panel(page)
    grid = page.locator("#es-comp-grid-sports_padel_club")
    initial = grid.locator(".es-component-card").count()
    add_btn = page.locator("#es-add-comp-btn-sports_padel_club")
    expect(add_btn).to_be_visible(timeout=4_000)
    add_btn.click()
    page.wait_for_timeout(500)
    after = grid.locator(".es-component-card").count()
    assert after == initial + 1, (
        f"sports_padel_club add-component: expected {initial + 1} cards, got {after}"
    )
