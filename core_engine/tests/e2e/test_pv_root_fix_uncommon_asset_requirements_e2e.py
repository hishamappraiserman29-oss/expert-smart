"""
E2E tests: Phase RFU — Root-Fix Uncommon Asset Requirements.

Verifies that selecting uncommon asset types in Chromium shows the old-style rich
requirement engine with correct data attributes and runtime debug state.

Tests (26):
  RFU_E2E_01 — initial load: panels hidden
  RFU_E2E_02 — common asset (مصنع): data-requirement-engine=old-style-common-simulation
  RFU_E2E_03 — common asset (مصنع): data-asset-category=common
  RFU_E2E_04 — common asset (مصنع): debug object usedWeakRenderer=false
  RFU_E2E_05 — petrol_station: data-requirement-engine=old-style-common-simulation
  RFU_E2E_06 — petrol_station: data-asset-category=uncommon
  RFU_E2E_07 — petrol_station: debug.usedWeakRenderer=false, oldStyleEngineUsed=true
  RFU_E2E_08 — petrol_station: title contains station text
  RFU_E2E_09 — petrol_station: add-component button works
  RFU_E2E_10 — hospital: data-asset-category=uncommon
  RFU_E2E_11 — hospital: debug.usedWeakRenderer=false
  RFU_E2E_12 — school: data-asset-category=uncommon
  RFU_E2E_13 — school: debug.usedWeakRenderer=false
  RFU_E2E_14 — cinema_theater: data-asset-category=uncommon
  RFU_E2E_15 — cinema_theater: add-hall button works
  RFU_E2E_16 — sports_padel_club: data-asset-category=uncommon
  RFU_E2E_17 — sports_padel_club: add-court button works
  RFU_E2E_18 — architectural_cultural_heritage_detailed: data-asset-category=uncommon
  RFU_E2E_19 — architectural_cultural_heritage_detailed: add-element button works
  RFU_E2E_20 — mixed_use_special: data-asset-category=uncommon
  RFU_E2E_21 — mixed_use_special: debug.usedWeakRenderer=false
  RFU_E2E_22 — hotel: data-asset-category=uncommon (regression — existing asset)
  RFU_E2E_23 — no visible panel has data-requirement-engine=weak
  RFU_E2E_24 — no visible panel has data-requirement-engine=flat
  RFU_E2E_25 — after all uncommon, common asset (عمارة سكنية) still shows old-style-common-simulation
  RFU_E2E_26 — pvRenderOldStyleRichRequirementEngine and pvSetRequirementRenderDebug exist in window
"""
import pytest
from playwright.sync_api import Page, expect


_LS_KEY = "es_auth"
_MOCK_SESSION = '{"token": "mock-rfu-token", "user_id": "rfu-test", "is_admin": false}'


def _load_page(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle", timeout=30_000)
    page.evaluate(
        f"localStorage.setItem('{_LS_KEY}', JSON.stringify({_MOCK_SESSION}))"
    )


def _select_asset(page: Page, value: str) -> None:
    page.locator("#asset-type").select_option(value=value)


def _wait_panel(page: Page) -> None:
    page.locator("#es-req-panel").wait_for(state="visible", timeout=7_000)


def _get_debug(page: Page) -> dict:
    return page.evaluate("() => window.__pvRequirementRenderDebug || null")


# ── RFU_E2E_01 ────────────────────────────────────────────────────────────────


def test_RFU_E2E_01_initial_load_panels_hidden(page: Page, live_server: str) -> None:
    """On load: both #es-req-panel and #pvr-vis-asset-requirements-panel are hidden."""
    _load_page(page, live_server)
    es = page.locator("#es-req-panel")
    pvr = page.locator("#pvr-vis-asset-requirements-panel")
    expect(es).to_be_attached()
    assert not es.is_visible(), "#es-req-panel must be hidden on load"
    assert not pvr.is_visible(), "#pvr-vis-panel must be hidden on load"


# ── RFU_E2E_02–04: Common asset ───────────────────────────────────────────────


def test_RFU_E2E_02_common_asset_engine_attr(page: Page, live_server: str) -> None:
    """Common asset (مصنع): #es-req-panel has data-requirement-engine=old-style-common-simulation."""
    _load_page(page, live_server)
    _select_asset(page, "مصنع")
    _wait_panel(page)
    engine = page.locator("#es-req-panel").get_attribute("data-requirement-engine")
    assert engine == "old-style-common-simulation", (
        f"Common asset must show data-requirement-engine='old-style-common-simulation'. Got: {engine!r}"
    )


def test_RFU_E2E_03_common_asset_category_attr(page: Page, live_server: str) -> None:
    """Common asset (مصنع): #es-req-panel has data-asset-category=common."""
    _load_page(page, live_server)
    _select_asset(page, "مصنع")
    _wait_panel(page)
    cat = page.locator("#es-req-panel").get_attribute("data-asset-category")
    assert cat == "common", (
        f"Factory (مصنع) must have data-asset-category='common'. Got: {cat!r}"
    )


def test_RFU_E2E_04_common_asset_debug_object(page: Page, live_server: str) -> None:
    """Common asset (مصنع): debug object shows usedWeakRenderer=false."""
    _load_page(page, live_server)
    _select_asset(page, "مصنع")
    _wait_panel(page)
    debug = _get_debug(page)
    assert debug is not None, "window.__pvRequirementRenderDebug must be set"
    assert debug["usedWeakRenderer"] is False
    assert debug["oldStyleEngineUsed"] is True
    assert debug["lastRenderer"] == "pvRenderOldStyleRichRequirementEngine"


# ── RFU_E2E_05–09: petrol_station ─────────────────────────────────────────────


def test_RFU_E2E_05_petrol_station_engine_attr(page: Page, live_server: str) -> None:
    """petrol_station: data-requirement-engine=old-style-common-simulation."""
    _load_page(page, live_server)
    _select_asset(page, "محطة تموين سيارات")
    _wait_panel(page)
    engine = page.locator("#es-req-panel").get_attribute("data-requirement-engine")
    assert engine == "old-style-common-simulation", (
        f"petrol_station must use old-style-common-simulation engine. Got: {engine!r}"
    )


def test_RFU_E2E_06_petrol_station_category_attr(page: Page, live_server: str) -> None:
    """petrol_station: data-asset-category=uncommon."""
    _load_page(page, live_server)
    _select_asset(page, "محطة تموين سيارات")
    _wait_panel(page)
    cat = page.locator("#es-req-panel").get_attribute("data-asset-category")
    assert cat == "uncommon", (
        f"petrol_station must have data-asset-category='uncommon'. Got: {cat!r}"
    )


def test_RFU_E2E_07_petrol_station_debug_object(page: Page, live_server: str) -> None:
    """petrol_station: debug object usedWeakRenderer=false, oldStyleEngineUsed=true."""
    _load_page(page, live_server)
    _select_asset(page, "محطة تموين سيارات")
    _wait_panel(page)
    debug = _get_debug(page)
    assert debug is not None, "window.__pvRequirementRenderDebug must be set"
    assert debug["usedWeakRenderer"] is False, (
        f"petrol_station: usedWeakRenderer must be false. Got: {debug['usedWeakRenderer']}"
    )
    assert debug["oldStyleEngineUsed"] is True
    assert debug["lastRenderer"] == "pvRenderOldStyleRichRequirementEngine"
    assert debug["lastAssetCategory"] == "uncommon"


def test_RFU_E2E_08_petrol_station_title_visible(page: Page, live_server: str) -> None:
    """petrol_station: #es-req-title contains station-related Arabic text."""
    _load_page(page, live_server)
    _select_asset(page, "محطة تموين سيارات")
    _wait_panel(page)
    title = page.locator("#es-req-title").inner_text()
    assert any(kw in title for kw in ("محطة", "تموين", "وقود")), (
        f"petrol_station title must contain station keyword. Got: {title!r}"
    )


def test_RFU_E2E_09_petrol_station_add_component(page: Page, live_server: str) -> None:
    """petrol_station: add-component button increases card count."""
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
        f"petrol_station: expected {initial+1} cards after add, got {after}"
    )


# ── RFU_E2E_10–11: hospital ───────────────────────────────────────────────────


def test_RFU_E2E_10_hospital_category_attr(page: Page, live_server: str) -> None:
    """hospital: data-asset-category=uncommon."""
    _load_page(page, live_server)
    _select_asset(page, "مستشفى")
    _wait_panel(page)
    cat = page.locator("#es-req-panel").get_attribute("data-asset-category")
    assert cat == "uncommon", (
        f"hospital must have data-asset-category='uncommon'. Got: {cat!r}"
    )


def test_RFU_E2E_11_hospital_debug_no_weak(page: Page, live_server: str) -> None:
    """hospital: debug.usedWeakRenderer=false."""
    _load_page(page, live_server)
    _select_asset(page, "مستشفى")
    _wait_panel(page)
    debug = _get_debug(page)
    assert debug is not None
    assert debug["usedWeakRenderer"] is False


# ── RFU_E2E_12–13: school ─────────────────────────────────────────────────────


def test_RFU_E2E_12_school_category_attr(page: Page, live_server: str) -> None:
    """school: data-asset-category=uncommon."""
    _load_page(page, live_server)
    _select_asset(page, "مدرسة")
    _wait_panel(page)
    cat = page.locator("#es-req-panel").get_attribute("data-asset-category")
    assert cat == "uncommon", (
        f"school must have data-asset-category='uncommon'. Got: {cat!r}"
    )


def test_RFU_E2E_13_school_debug_no_weak(page: Page, live_server: str) -> None:
    """school: debug.usedWeakRenderer=false."""
    _load_page(page, live_server)
    _select_asset(page, "مدرسة")
    _wait_panel(page)
    debug = _get_debug(page)
    assert debug is not None
    assert debug["usedWeakRenderer"] is False


# ── RFU_E2E_14–15: cinema_theater ─────────────────────────────────────────────


def test_RFU_E2E_14_cinema_theater_category_attr(page: Page, live_server: str) -> None:
    """cinema_theater: data-asset-category=uncommon."""
    _load_page(page, live_server)
    _select_asset(page, "سينما / مسرح / قاعة عرض")
    _wait_panel(page)
    cat = page.locator("#es-req-panel").get_attribute("data-asset-category")
    assert cat == "uncommon", (
        f"cinema_theater must have data-asset-category='uncommon'. Got: {cat!r}"
    )


def test_RFU_E2E_15_cinema_theater_add_hall(page: Page, live_server: str) -> None:
    """cinema_theater: add-component button increases card count."""
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
        f"cinema_theater: expected {initial+1} cards after add, got {after}"
    )


# ── RFU_E2E_16–17: sports_padel_club ─────────────────────────────────────────


def test_RFU_E2E_16_sports_padel_club_category_attr(page: Page, live_server: str) -> None:
    """sports_padel_club: data-asset-category=uncommon."""
    _load_page(page, live_server)
    _select_asset(page, "نادي رياضي / ملاعب بادل")
    _wait_panel(page)
    cat = page.locator("#es-req-panel").get_attribute("data-asset-category")
    assert cat == "uncommon", (
        f"sports_padel_club must have data-asset-category='uncommon'. Got: {cat!r}"
    )


def test_RFU_E2E_17_sports_padel_club_add_court(page: Page, live_server: str) -> None:
    """sports_padel_club: add-component button increases card count."""
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
        f"sports_padel_club: expected {initial+1} cards after add, got {after}"
    )


# ── RFU_E2E_18–19: architectural_cultural_heritage_detailed ───────────────────


def test_RFU_E2E_18_arch_heritage_category_attr(page: Page, live_server: str) -> None:
    """architectural_cultural_heritage_detailed: data-asset-category=uncommon."""
    _load_page(page, live_server)
    _select_asset(page, "architectural_cultural_heritage_detailed")
    _wait_panel(page)
    cat = page.locator("#es-req-panel").get_attribute("data-asset-category")
    assert cat == "uncommon", (
        f"architectural_cultural_heritage_detailed must be 'uncommon'. Got: {cat!r}"
    )


def test_RFU_E2E_19_arch_heritage_add_element(page: Page, live_server: str) -> None:
    """architectural_cultural_heritage_detailed: add-element button increases card count."""
    _load_page(page, live_server)
    _select_asset(page, "architectural_cultural_heritage_detailed")
    _wait_panel(page)
    grid = page.locator("#es-comp-grid-architectural_cultural_heritage_detailed")
    initial = grid.locator(".es-component-card").count()
    add_btn = page.locator(
        "#es-add-comp-btn-architectural_cultural_heritage_detailed"
    )
    expect(add_btn).to_be_visible(timeout=4_000)
    add_btn.click()
    page.wait_for_timeout(500)
    after = grid.locator(".es-component-card").count()
    assert after == initial + 1, (
        f"arch_heritage: expected {initial+1} cards after add, got {after}"
    )


# ── RFU_E2E_20–21: mixed_use_special ─────────────────────────────────────────


def test_RFU_E2E_20_mixed_use_special_category_attr(page: Page, live_server: str) -> None:
    """mixed_use_special: data-asset-category=uncommon."""
    _load_page(page, live_server)
    _select_asset(page, "أصل متعدد الاستخدامات خاص")
    _wait_panel(page)
    cat = page.locator("#es-req-panel").get_attribute("data-asset-category")
    assert cat == "uncommon", (
        f"mixed_use_special must have data-asset-category='uncommon'. Got: {cat!r}"
    )


def test_RFU_E2E_21_mixed_use_special_debug_no_weak(page: Page, live_server: str) -> None:
    """mixed_use_special: debug.usedWeakRenderer=false."""
    _load_page(page, live_server)
    _select_asset(page, "أصل متعدد الاستخدامات خاص")
    _wait_panel(page)
    debug = _get_debug(page)
    assert debug is not None
    assert debug["usedWeakRenderer"] is False
    assert debug["lastAssetCategory"] == "uncommon"


# ── RFU_E2E_22: hotel regression ─────────────────────────────────────────────


def test_RFU_E2E_22_hotel_still_uncommon(page: Page, live_server: str) -> None:
    """hotel (فندق): data-asset-category=uncommon — regression check."""
    _load_page(page, live_server)
    _select_asset(page, "فندق")
    _wait_panel(page)
    cat = page.locator("#es-req-panel").get_attribute("data-asset-category")
    assert cat == "uncommon", (
        f"hotel must have data-asset-category='uncommon'. Got: {cat!r}"
    )


# ── RFU_E2E_23–24: No weak/flat panels visible ────────────────────────────────


def test_RFU_E2E_23_no_weak_engine_panel(page: Page, live_server: str) -> None:
    """After selecting petrol_station, no visible panel has data-requirement-engine=weak."""
    _load_page(page, live_server)
    _select_asset(page, "محطة تموين سيارات")
    _wait_panel(page)
    weak_panels = page.locator("[data-requirement-engine='weak']:visible")
    assert weak_panels.count() == 0, "No visible panel must have data-requirement-engine='weak'"


def test_RFU_E2E_24_no_flat_engine_panel(page: Page, live_server: str) -> None:
    """After selecting hospital, no visible panel has data-requirement-engine=flat."""
    _load_page(page, live_server)
    _select_asset(page, "مستشفى")
    _wait_panel(page)
    flat_panels = page.locator("[data-requirement-engine='flat']:visible")
    assert flat_panels.count() == 0, "No visible panel must have data-requirement-engine='flat'"


# ── RFU_E2E_25: Common asset preserved after uncommon selections ──────────────


def test_RFU_E2E_25_common_asset_preserved_after_uncommon(
    page: Page, live_server: str
) -> None:
    """After all uncommon selections, common asset (عمارة سكنية) still shows old-style-common-simulation."""
    _load_page(page, live_server)
    for val in ["محطة تموين سيارات", "مستشفى", "سينما / مسرح / قاعة عرض"]:
        _select_asset(page, val)
        _wait_panel(page)
    _select_asset(page, "عمارة سكنية")
    _wait_panel(page)
    engine = page.locator("#es-req-panel").get_attribute("data-requirement-engine")
    assert engine == "old-style-common-simulation", (
        f"Common asset (عمارة سكنية) must still use old-style-common-simulation engine. Got: {engine!r}"
    )
    cat = page.locator("#es-req-panel").get_attribute("data-asset-category")
    assert cat == "common", (
        f"عمارة سكنية must have data-asset-category='common'. Got: {cat!r}"
    )


# ── RFU_E2E_26: Canonical functions exist in window ───────────────────────────


def test_RFU_E2E_26_canonical_functions_in_window(page: Page, live_server: str) -> None:
    """pvRenderOldStyleRichRequirementEngine and pvSetRequirementRenderDebug exist in window."""
    _load_page(page, live_server)
    has_renderer = page.evaluate(
        "() => typeof window.pvRenderOldStyleRichRequirementEngine === 'function'"
    )
    has_debug_setter = page.evaluate(
        "() => typeof window.pvSetRequirementRenderDebug === 'function'"
    )
    has_config_getter = page.evaluate(
        "() => typeof window.pvGetRequirementConfigForAsset === 'function'"
    )
    assert has_renderer, "window.pvRenderOldStyleRichRequirementEngine must be a function"
    assert has_debug_setter, "window.pvSetRequirementRenderDebug must be a function"
    assert has_config_getter, "window.pvGetRequirementConfigForAsset must be a function"
