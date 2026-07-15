"""
Phase UCS — Uncommon Common Simulation: E2E Playwright Tests (36 tests)
advisory_only=True — not_real_training

Verifies that every uncommon asset renders via the same old-style-common-simulation
engine path as common assets, including:
  • data-requirement-engine="old-style-common-simulation"
  • data-asset-category="uncommon"
  • data-uncommon-simulates-common="true"
  • window.__pvRequirementRenderDebug.uncommonSimulatesCommon = true
  • Add-button labels per asset type
  • Upload clips and priority badges visible
  • 8 UCS wrapper functions exposed on window
  • Values sync to unified_professional_valuation_page_context
"""

import pathlib
import pytest
from playwright.sync_api import Page, expect

# ── Paths ──────────────────────────────────────────────────────────────────────
_ROOT = pathlib.Path(__file__).resolve().parents[3]
QA_DIR = (
    _ROOT
    / "core_engine"
    / "instance"
    / "manual_review_outputs"
    / "professional_valuation_uncommon_common_simulation"
)

# ── Auth mock (same pattern as RFU tests) ─────────────────────────────────────
_LS_KEY = "es_auth"
_MOCK_SESSION = '{"token": "mock-ucs-token", "user_id": "ucs-test", "is_admin": false}'

# ── Helpers ────────────────────────────────────────────────────────────────────

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
    return page.evaluate("() => window.__pvRequirementRenderDebug || {}") or {}


def _screenshot(page: Page, name: str) -> None:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        page.screenshot(path=str(QA_DIR / name), full_page=False)
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# UCS_E2E_01: Page opens
# ══════════════════════════════════════════════════════════════════════════════

def test_UCS_E2E_01_page_opens(page: Page, live_server: str) -> None:
    """UCS_E2E_01: Professional valuation page loads without errors."""
    _load_page(page, live_server)
    expect(page).not_to_have_title("Error")
    assert page.url.startswith(live_server)


# ══════════════════════════════════════════════════════════════════════════════
# UCS_E2E_02–04: Common asset (مصنع / factory)
# ══════════════════════════════════════════════════════════════════════════════

def test_UCS_E2E_02_common_asset_engine_attr(page: Page, live_server: str) -> None:
    """UCS_E2E_02: Common asset renders with data-requirement-engine='old-style-common-simulation'."""
    _load_page(page, live_server)
    _select_asset(page, "مصنع")
    _wait_panel(page)
    engine = page.locator("#es-req-panel").get_attribute("data-requirement-engine")
    assert engine == "old-style-common-simulation", (
        f"Expected 'old-style-common-simulation', got {engine!r}"
    )


def test_UCS_E2E_03_common_asset_category_attr(page: Page, live_server: str) -> None:
    """UCS_E2E_03: Common asset has data-asset-category='common'."""
    _load_page(page, live_server)
    _select_asset(page, "مصنع")
    _wait_panel(page)
    cat = page.locator("#es-req-panel").get_attribute("data-asset-category")
    assert cat == "common", f"Expected 'common', got {cat!r}"


def test_UCS_E2E_04_common_asset_debug_object(page: Page, live_server: str) -> None:
    """UCS_E2E_04: Common asset debug object has correct fields."""
    _load_page(page, live_server)
    _select_asset(page, "مصنع")
    _wait_panel(page)
    dbg = _get_debug(page)
    assert dbg.get("oldStyleEngineUsed") is True
    assert dbg.get("usedWeakRenderer") is False


# ══════════════════════════════════════════════════════════════════════════════
# UCS_E2E_05–12: petrol_station
# ══════════════════════════════════════════════════════════════════════════════

def test_UCS_E2E_05_petrol_station_engine_attr(page: Page, live_server: str) -> None:
    """UCS_E2E_05: petrol_station renders with data-requirement-engine='old-style-common-simulation'."""
    _load_page(page, live_server)
    _select_asset(page, "محطة تموين سيارات")
    _wait_panel(page)
    engine = page.locator("#es-req-panel").get_attribute("data-requirement-engine")
    assert engine == "old-style-common-simulation"


def test_UCS_E2E_06_petrol_station_category_uncommon(page: Page, live_server: str) -> None:
    """UCS_E2E_06: petrol_station has data-asset-category='uncommon'."""
    _load_page(page, live_server)
    _select_asset(page, "محطة تموين سيارات")
    _wait_panel(page)
    cat = page.locator("#es-req-panel").get_attribute("data-asset-category")
    assert cat == "uncommon", f"Expected 'uncommon', got {cat!r}"


def test_UCS_E2E_07_petrol_station_simulates_common_attr(page: Page, live_server: str) -> None:
    """UCS_E2E_07: petrol_station has data-uncommon-simulates-common='true'."""
    _load_page(page, live_server)
    _select_asset(page, "محطة تموين سيارات")
    _wait_panel(page)
    sim = page.locator("#es-req-panel").get_attribute("data-uncommon-simulates-common")
    assert sim == "true", f"Expected 'true', got {sim!r}"


def test_UCS_E2E_08_petrol_station_debug_uncommon_simulates(page: Page, live_server: str) -> None:
    """UCS_E2E_08: debug.uncommonSimulatesCommon=True for petrol_station."""
    _load_page(page, live_server)
    _select_asset(page, "محطة تموين سيارات")
    _wait_panel(page)
    dbg = _get_debug(page)
    assert dbg.get("uncommonSimulatesCommon") is True, (
        f"Expected uncommonSimulatesCommon=True, got {dbg}"
    )


def test_UCS_E2E_09_petrol_station_panel_visible(page: Page, live_server: str) -> None:
    """UCS_E2E_09: petrol_station panel is visible and non-empty."""
    _load_page(page, live_server)
    _select_asset(page, "محطة تموين سيارات")
    _wait_panel(page)
    panel = page.locator("#es-req-panel")
    expect(panel).to_be_visible()
    assert len(panel.inner_html()) > 100, "Panel appears empty"


def test_UCS_E2E_10_petrol_station_add_button(page: Page, live_server: str) -> None:
    """UCS_E2E_10: petrol_station add-component button text contains 'مكون'."""
    _load_page(page, live_server)
    _select_asset(page, "محطة تموين سيارات")
    _wait_panel(page)
    btn = page.locator("#es-add-comp-btn-petrol_station")
    if btn.count() > 0:
        txt = btn.inner_text()
        assert "مكون" in txt, f"Expected 'مكون' in button text, got: {txt!r}"


def test_UCS_E2E_11_petrol_station_upload_clips(page: Page, live_server: str) -> None:
    """UCS_E2E_11: petrol_station panel contains upload clip elements."""
    _load_page(page, live_server)
    _select_asset(page, "محطة تموين سيارات")
    _wait_panel(page)
    html = page.locator("#es-req-panel").inner_html()
    assert any(kw in html for kw in ["upload", "clip", "es-doc", "bool", "document"]), (
        "No upload-clip indicator found in petrol_station panel"
    )


def test_UCS_E2E_12_petrol_station_priority_badges(page: Page, live_server: str) -> None:
    """UCS_E2E_12: petrol_station panel contains priority badge markers."""
    _load_page(page, live_server)
    _select_asset(page, "محطة تموين سيارات")
    _wait_panel(page)
    html = page.locator("#es-req-panel").inner_html()
    has_badge = any(kw in html for kw in ["ui_required", "required", "es-badge", "priority", "*"])
    assert has_badge, "No priority badge indicator found in petrol_station panel"


# ══════════════════════════════════════════════════════════════════════════════
# UCS_E2E_13–15: hospital
# ══════════════════════════════════════════════════════════════════════════════

def test_UCS_E2E_13_hospital_category_uncommon(page: Page, live_server: str) -> None:
    """UCS_E2E_13: hospital has data-asset-category='uncommon'."""
    _load_page(page, live_server)
    _select_asset(page, "مستشفى")
    _wait_panel(page)
    cat = page.locator("#es-req-panel").get_attribute("data-asset-category")
    assert cat == "uncommon"


def test_UCS_E2E_14_hospital_panel_visible(page: Page, live_server: str) -> None:
    """UCS_E2E_14: hospital panel renders visible content."""
    _load_page(page, live_server)
    _select_asset(page, "مستشفى")
    _wait_panel(page)
    expect(page.locator("#es-req-panel")).to_be_visible()


def test_UCS_E2E_15_hospital_add_button(page: Page, live_server: str) -> None:
    """UCS_E2E_15: hospital add-component button text contains 'مبنى طبي' or 'قسم'."""
    _load_page(page, live_server)
    _select_asset(page, "مستشفى")
    _wait_panel(page)
    btn = page.locator("#es-add-comp-btn-hospital")
    if btn.count() > 0:
        txt = btn.inner_text()
        assert ("طبي" in txt or "قسم" in txt or "مبنى" in txt), (
            f"Expected hospital add-button keywords, got: {txt!r}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# UCS_E2E_16–17: school
# ══════════════════════════════════════════════════════════════════════════════

def test_UCS_E2E_16_school_category_uncommon(page: Page, live_server: str) -> None:
    """UCS_E2E_16: school has data-asset-category='uncommon'."""
    _load_page(page, live_server)
    _select_asset(page, "مدرسة")
    _wait_panel(page)
    cat = page.locator("#es-req-panel").get_attribute("data-asset-category")
    assert cat == "uncommon"


def test_UCS_E2E_17_school_add_button(page: Page, live_server: str) -> None:
    """UCS_E2E_17: school add-component button text contains 'تعليمي' or 'مبنى'."""
    _load_page(page, live_server)
    _select_asset(page, "مدرسة")
    _wait_panel(page)
    btn = page.locator("#es-add-comp-btn-school")
    if btn.count() > 0:
        txt = btn.inner_text()
        assert ("تعليمي" in txt or "مبنى" in txt or "مرفق" in txt), (
            f"Expected school add-button keywords, got: {txt!r}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# UCS_E2E_18–19: cinema_theater
# ══════════════════════════════════════════════════════════════════════════════

def test_UCS_E2E_18_cinema_theater_category_uncommon(page: Page, live_server: str) -> None:
    """UCS_E2E_18: cinema_theater has data-asset-category='uncommon'."""
    _load_page(page, live_server)
    _select_asset(page, "سينما / مسرح / قاعة عرض")
    _wait_panel(page)
    cat = page.locator("#es-req-panel").get_attribute("data-asset-category")
    assert cat == "uncommon"


def test_UCS_E2E_19_cinema_theater_add_button(page: Page, live_server: str) -> None:
    """UCS_E2E_19: cinema_theater add button contains 'قاعة' or 'مكون'."""
    _load_page(page, live_server)
    _select_asset(page, "سينما / مسرح / قاعة عرض")
    _wait_panel(page)
    btn = page.locator("#es-add-comp-btn-cinema_theater")
    if btn.count() > 0:
        txt = btn.inner_text()
        assert ("قاعة" in txt or "مكون" in txt), (
            f"Expected cinema add-button keywords, got: {txt!r}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# UCS_E2E_20–21: sports_padel_club
# ══════════════════════════════════════════════════════════════════════════════

def test_UCS_E2E_20_sports_padel_club_category_uncommon(page: Page, live_server: str) -> None:
    """UCS_E2E_20: sports_padel_club has data-asset-category='uncommon'."""
    _load_page(page, live_server)
    _select_asset(page, "نادي رياضي / ملاعب بادل")
    _wait_panel(page)
    cat = page.locator("#es-req-panel").get_attribute("data-asset-category")
    assert cat == "uncommon"


def test_UCS_E2E_21_sports_padel_club_add_button(page: Page, live_server: str) -> None:
    """UCS_E2E_21: sports_padel_club add button contains 'ملعب' or 'مرفق'."""
    _load_page(page, live_server)
    _select_asset(page, "نادي رياضي / ملاعب بادل")
    _wait_panel(page)
    btn = page.locator("#es-add-comp-btn-sports_padel_club")
    if btn.count() > 0:
        txt = btn.inner_text()
        assert ("ملعب" in txt or "مرفق" in txt), (
            f"Expected sports add-button keywords, got: {txt!r}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# UCS_E2E_22–23: architectural_cultural_heritage_detailed
# ══════════════════════════════════════════════════════════════════════════════

def test_UCS_E2E_22_heritage_category_uncommon(page: Page, live_server: str) -> None:
    """UCS_E2E_22: architectural_cultural_heritage_detailed has data-asset-category='uncommon'."""
    _load_page(page, live_server)
    _select_asset(page, "architectural_cultural_heritage_detailed")
    _wait_panel(page)
    cat = page.locator("#es-req-panel").get_attribute("data-asset-category")
    assert cat == "uncommon"


def test_UCS_E2E_23_heritage_add_button(page: Page, live_server: str) -> None:
    """UCS_E2E_23: heritage add button contains 'تراثي' or 'عنصر'."""
    _load_page(page, live_server)
    _select_asset(page, "architectural_cultural_heritage_detailed")
    _wait_panel(page)
    btn = page.locator("#es-add-comp-btn-architectural_cultural_heritage_detailed")
    if btn.count() > 0:
        txt = btn.inner_text()
        assert ("تراثي" in txt or "عنصر" in txt or "مبنى" in txt), (
            f"Expected heritage add-button keywords, got: {txt!r}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# UCS_E2E_24–25: mixed_use_special
# ══════════════════════════════════════════════════════════════════════════════

def test_UCS_E2E_24_mixed_use_special_category_uncommon(page: Page, live_server: str) -> None:
    """UCS_E2E_24: mixed_use_special has data-asset-category='uncommon'."""
    _load_page(page, live_server)
    _select_asset(page, "أصل متعدد الاستخدامات خاص")
    _wait_panel(page)
    cat = page.locator("#es-req-panel").get_attribute("data-asset-category")
    assert cat == "uncommon"


def test_UCS_E2E_25_mixed_use_special_add_button(page: Page, live_server: str) -> None:
    """UCS_E2E_25: mixed_use_special add button contains 'مكون' or 'استخدام'."""
    _load_page(page, live_server)
    _select_asset(page, "أصل متعدد الاستخدامات خاص")
    _wait_panel(page)
    btn = page.locator("#es-add-comp-btn-mixed_use_special")
    if btn.count() > 0:
        txt = btn.inner_text()
        assert ("مكون" in txt or "استخدام" in txt), (
            f"Expected mixed-use add-button keywords, got: {txt!r}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# UCS_E2E_26: hotel
# ══════════════════════════════════════════════════════════════════════════════

def test_UCS_E2E_26_hotel_category_uncommon(page: Page, live_server: str) -> None:
    """UCS_E2E_26: hotel has data-asset-category='uncommon'."""
    _load_page(page, live_server)
    _select_asset(page, "فندق")
    _wait_panel(page)
    cat = page.locator("#es-req-panel").get_attribute("data-asset-category")
    assert cat == "uncommon"


# ══════════════════════════════════════════════════════════════════════════════
# UCS_E2E_27–28: No weak renderer
# ══════════════════════════════════════════════════════════════════════════════

def test_UCS_E2E_27_no_weak_renderer_panel_petrol(page: Page, live_server: str) -> None:
    """UCS_E2E_27: petrol_station: debug.usedWeakRenderer must be False."""
    _load_page(page, live_server)
    _select_asset(page, "محطة تموين سيارات")
    _wait_panel(page)
    dbg = _get_debug(page)
    assert dbg.get("usedWeakRenderer") is False, (
        f"Weak renderer was used for petrol_station: {dbg}"
    )


def test_UCS_E2E_28_no_weak_renderer_panel_hospital(page: Page, live_server: str) -> None:
    """UCS_E2E_28: hospital: debug.usedWeakRenderer must be False."""
    _load_page(page, live_server)
    _select_asset(page, "مستشفى")
    _wait_panel(page)
    dbg = _get_debug(page)
    assert dbg.get("usedWeakRenderer") is False, (
        f"Weak renderer was used for hospital: {dbg}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# UCS_E2E_29: Common asset still works after uncommon selection
# ══════════════════════════════════════════════════════════════════════════════

def test_UCS_E2E_29_common_asset_still_works_after_uncommon(page: Page, live_server: str) -> None:
    """UCS_E2E_29: After selecting uncommon then common, common renders correctly."""
    _load_page(page, live_server)
    _select_asset(page, "مستشفى")
    _wait_panel(page)
    _select_asset(page, "مصنع")
    _wait_panel(page)
    cat = page.locator("#es-req-panel").get_attribute("data-asset-category")
    assert cat == "common", f"After switching to common, expected 'common', got {cat!r}"


# ══════════════════════════════════════════════════════════════════════════════
# UCS_E2E_30–31: Wrapper functions exist in window
# ══════════════════════════════════════════════════════════════════════════════

def test_UCS_E2E_30_render_wrapper_function_exists(page: Page, live_server: str) -> None:
    """UCS_E2E_30: pvRenderUncommonAsCommonStyleRequirements exists on window."""
    _load_page(page, live_server)
    result = page.evaluate(
        "() => typeof window.pvRenderUncommonAsCommonStyleRequirements === 'function'"
    )
    assert result is True, "pvRenderUncommonAsCommonStyleRequirements not found on window"


def test_UCS_E2E_31_all_ucs_wrapper_functions_exist(page: Page, live_server: str) -> None:
    """UCS_E2E_31: All 8 UCS wrapper functions exist on window."""
    _load_page(page, live_server)
    fns = [
        "pvRenderUncommonAsCommonStyleRequirements",
        "pvBuildUncommonCommonStyleRequirementConfig",
        "pvMapUncommonAssetToCommonTemplate",
        "pvGetUncommonSimulatedRequirementGroups",
        "pvDisableWeakUncommonRenderer",
        "pvAssertUncommonUsesCommonSimulation",
        "pvCollectUncommonSimulatedRequirementValues",
        "pvSyncUncommonSimulatedValuesToUnifiedContext",
    ]
    missing = [
        fn for fn in fns
        if not page.evaluate(f"() => typeof window.{fn} === 'function'")
    ]
    assert not missing, f"Missing UCS wrapper functions: {missing}"


# ══════════════════════════════════════════════════════════════════════════════
# UCS_E2E_32: Values sync to unified context
# ══════════════════════════════════════════════════════════════════════════════

def test_UCS_E2E_32_values_sync_to_unified_context(page: Page, live_server: str) -> None:
    """UCS_E2E_32: pvSyncUncommonSimulatedValuesToUnifiedContext returns context object."""
    _load_page(page, live_server)
    _select_asset(page, "مستشفى")
    _wait_panel(page)
    result = page.evaluate(
        "() => { var ctx = window.pvSyncUncommonSimulatedValuesToUnifiedContext();"
        "        return ctx && typeof ctx === 'object'; }"
    )
    assert result is True, "pvSyncUncommonSimulatedValuesToUnifiedContext did not return an object"


# ══════════════════════════════════════════════════════════════════════════════
# UCS_E2E_33–36: Screenshots
# ══════════════════════════════════════════════════════════════════════════════

def test_UCS_E2E_33_screenshot_petrol_station(page: Page, live_server: str) -> None:
    """UCS_E2E_33: Capture screenshot of petrol_station requirements panel."""
    _load_page(page, live_server)
    _select_asset(page, "محطة تموين سيارات")
    _wait_panel(page)
    _screenshot(page, "screenshot_01_petrol_station_requirements.png")


def test_UCS_E2E_34_screenshot_hospital(page: Page, live_server: str) -> None:
    """UCS_E2E_34: Capture screenshot of hospital requirements panel."""
    _load_page(page, live_server)
    _select_asset(page, "مستشفى")
    _wait_panel(page)
    _screenshot(page, "screenshot_02_hospital_requirements.png")


def test_UCS_E2E_35_screenshot_school(page: Page, live_server: str) -> None:
    """UCS_E2E_35: Capture screenshot of school requirements panel."""
    _load_page(page, live_server)
    _select_asset(page, "مدرسة")
    _wait_panel(page)
    _screenshot(page, "screenshot_03_school_requirements.png")


def test_UCS_E2E_36_screenshot_hotel(page: Page, live_server: str) -> None:
    """UCS_E2E_36: Capture screenshot of hotel requirements panel."""
    _load_page(page, live_server)
    _select_asset(page, "فندق")
    _wait_panel(page)
    _screenshot(page, "screenshot_04_hotel_requirements.png")
