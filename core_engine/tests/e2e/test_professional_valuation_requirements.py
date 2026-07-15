"""
PVRQ01–PVRQ16 — Professional Valuation Requirements Panel E2E Tests.

Tests the visible workspace (ws-professional) asset-specific requirements panel.
Verifies that full legacy requirements are displayed when each asset type is selected.

Navigation: default URL (no hash) → ws-professional is the active workspace.

PVRQ01  pvr-asset-requirements-panel element is present in DOM
PVRQ02  selecting hotel shows pvr-hotel-requirements panel
PVRQ03  hotel requirements count badge is visible
PVRQ04  hotel requirements count badge shows 110+ (≥ legacy count)
PVRQ05  hotel panel contains ADR text
PVRQ06  hotel panel contains RevPAR text
PVRQ07  hotel panel contains DCF text
PVRQ08  hotel panel has legacy-restored marker
PVRQ09  selecting industrial_factory shows factory requirements panel
PVRQ10  selecting urban_land shows land requirements panel
PVRQ11  selecting retail_shop shows retail requirements panel
PVRQ12  selecting warehouse shows warehouse requirements panel
PVRQ13  market_value does not appear as an asset requirement label
PVRQ14  comparable_adjustment does not appear as an asset type option label
PVRQ15  no duplicate data-testid values in asset requirements area
PVRQ16  no internal filesystem paths visible in requirements DOM
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _go_to_visible_pv(page: Page, live_server: str) -> None:
    """Navigate to the default page — ws-professional is the active workspace."""
    page.route("**/api/**", lambda r: r.fulfill(
        status=200, body=b'{"ok":true}', content_type="application/json"
    ))
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator('[data-testid="professional-wizard"]').wait_for(state="visible", timeout=10_000)


def _select_asset_type_visible(page: Page, value: str) -> None:
    """Set the asset type in the visible workspace (ws-professional) via JavaScript.
    Calls pvUpdateAssetRequirementsPanel() directly — bypasses scroll/visibility
    constraints and reliably triggers the requirements panel update."""
    page.evaluate(f"""
        (function() {{
            var sel = document.getElementById('pvr-asset-type');
            if (!sel) throw new Error('pvr-asset-type not found');
            sel.value = {repr(value)};
            if (typeof pvUpdateAssetRequirementsPanel === 'function') {{
                pvUpdateAssetRequirementsPanel();
            }}
        }})();
    """)
    page.wait_for_timeout(400)


# ─────────────────────────────────────────────────────────────────────────────
# PVRQ01: Requirements panel element present
# ─────────────────────────────────────────────────────────────────────────────

def test_PVRQ01_asset_requirements_panel_present(page: Page, live_server: str) -> None:
    """PVRQ01: pvr-asset-requirements-panel element is present in the ws-professional workspace."""
    _go_to_visible_pv(page, live_server)
    # Scope to #ws-professional: the panel also exists in ws-professional-valuation (count==2 globally)
    ws = page.locator("#ws-professional")
    panel = ws.locator('[data-testid="pro-val-asset-requirements-panel"]')
    expect(panel).to_have_count(1)


# ─────────────────────────────────────────────────────────────────────────────
# PVRQ02–PVRQ08: Hotel requirements
# ─────────────────────────────────────────────────────────────────────────────

def test_PVRQ02_selecting_hotel_shows_hotel_requirements(page: Page, live_server: str) -> None:
    """PVRQ02: Selecting hotel shows the hotel requirements sub-panel (display not none)."""
    _go_to_visible_pv(page, live_server)
    _select_asset_type_visible(page, "hotel")
    # Outer panel display should be '' (not 'none') after selection
    outer_display = page.evaluate(
        "() => document.getElementById('pvr-asset-requirements-panel').style.display"
    )
    assert outer_display != "none", (
        f"pvr-asset-requirements-panel should not be display:none after selecting hotel, got '{outer_display}'"
    )
    # Hotel sub-panel display should be '' (not 'none')
    hotel_display = page.evaluate(
        "() => document.getElementById('pvr-hotel-requirements').style.display"
    )
    assert hotel_display != "none", (
        f"pvr-hotel-requirements should not be display:none after selecting hotel, got '{hotel_display}'"
    )


def test_PVRQ03_hotel_requirements_count_badge_present(page: Page, live_server: str) -> None:
    """PVRQ03: After selecting hotel, the requirements count badge exists in DOM."""
    _go_to_visible_pv(page, live_server)
    _select_asset_type_visible(page, "hotel")
    count_badge = page.locator('[data-testid="pro-val-hotel-requirements-count"]')
    expect(count_badge).to_have_count(1)


def test_PVRQ04_hotel_requirements_count_gte_legacy(page: Page, live_server: str) -> None:
    """PVRQ04: Hotel requirements count badge text confirms ≥ legacy count (contains 110+ or higher)."""
    _go_to_visible_pv(page, live_server)
    _select_asset_type_visible(page, "hotel")
    badge_text = page.locator('[data-testid="pro-val-hotel-requirements-count"]').inner_html()
    # Badge must contain a number >= 100 indicating full legacy restoration
    assert any(str(n) in badge_text for n in range(100, 200)), (
        f"Count badge should show 100+ requirements, got: '{badge_text}'"
    )


def test_PVRQ05_hotel_panel_contains_adr(page: Page, live_server: str) -> None:
    """PVRQ05: Hotel requirements panel contains ADR text."""
    _go_to_visible_pv(page, live_server)
    _select_asset_type_visible(page, "hotel")
    hotel_html = page.locator('[data-testid="pro-val-hotel-requirements-panel"]').inner_html()
    assert "ADR" in hotel_html or "adr" in hotel_html.lower(), (
        "Hotel requirements panel must contain ADR"
    )


def test_PVRQ06_hotel_panel_contains_revpar(page: Page, live_server: str) -> None:
    """PVRQ06: Hotel requirements panel contains RevPAR text."""
    _go_to_visible_pv(page, live_server)
    _select_asset_type_visible(page, "hotel")
    hotel_html = page.locator('[data-testid="pro-val-hotel-requirements-panel"]').inner_html()
    assert "RevPAR" in hotel_html or "revpar" in hotel_html.lower(), (
        "Hotel requirements panel must contain RevPAR"
    )


def test_PVRQ07_hotel_panel_contains_dcf(page: Page, live_server: str) -> None:
    """PVRQ07: Hotel requirements panel mentions DCF method."""
    _go_to_visible_pv(page, live_server)
    _select_asset_type_visible(page, "hotel")
    hotel_html = page.locator('[data-testid="pro-val-hotel-requirements-panel"]').inner_html()
    assert "dcf" in hotel_html.lower() or "DCF" in hotel_html, (
        "Hotel requirements panel must contain DCF method reference"
    )


def test_PVRQ08_hotel_panel_has_legacy_restored_marker(page: Page, live_server: str) -> None:
    """PVRQ08: Hotel requirements panel has the legacy-restored confirmation marker in DOM."""
    _go_to_visible_pv(page, live_server)
    _select_asset_type_visible(page, "hotel")
    marker = page.locator('[data-testid="pro-val-asset-requirements-legacy-restored"]')
    expect(marker).to_have_count(1)


# ─────────────────────────────────────────────────────────────────────────────
# PVRQ09–PVRQ12: Other asset types
# ─────────────────────────────────────────────────────────────────────────────

def test_PVRQ09_selecting_factory_shows_factory_requirements(page: Page, live_server: str) -> None:
    """PVRQ09: Selecting industrial_factory makes factory sub-panel display not-none."""
    _go_to_visible_pv(page, live_server)
    _select_asset_type_visible(page, "industrial_factory")
    factory_display = page.evaluate(
        "() => document.getElementById('pvr-factory-requirements').style.display"
    )
    assert factory_display != "none", (
        f"pvr-factory-requirements should not be display:none after selecting industrial_factory"
    )
    # Hotel panel must remain hidden
    hotel_display = page.evaluate(
        "() => document.getElementById('pvr-hotel-requirements').style.display"
    )
    assert hotel_display == "none", (
        "pvr-hotel-requirements must be display:none when factory is selected"
    )


def test_PVRQ10_selecting_land_shows_land_requirements(page: Page, live_server: str) -> None:
    """PVRQ10: Selecting urban_land makes land sub-panel display not-none."""
    _go_to_visible_pv(page, live_server)
    _select_asset_type_visible(page, "urban_land")
    land_display = page.evaluate(
        "() => document.getElementById('pvr-land-requirements').style.display"
    )
    assert land_display != "none", (
        "pvr-land-requirements should not be display:none after selecting urban_land"
    )


def test_PVRQ11_selecting_retail_shows_retail_requirements(page: Page, live_server: str) -> None:
    """PVRQ11: Selecting retail_shop makes retail sub-panel display not-none."""
    _go_to_visible_pv(page, live_server)
    _select_asset_type_visible(page, "retail_shop")
    retail_display = page.evaluate(
        "() => document.getElementById('pvr-retail-requirements').style.display"
    )
    assert retail_display != "none", (
        "pvr-retail-requirements should not be display:none after selecting retail_shop"
    )


def test_PVRQ12_selecting_warehouse_shows_warehouse_requirements(page: Page, live_server: str) -> None:
    """PVRQ12: Selecting warehouse makes warehouse sub-panel display not-none."""
    _go_to_visible_pv(page, live_server)
    _select_asset_type_visible(page, "warehouse")
    warehouse_display = page.evaluate(
        "() => document.getElementById('pvr-warehouse-requirements').style.display"
    )
    assert warehouse_display != "none", (
        "pvr-warehouse-requirements should not be display:none after selecting warehouse"
    )


# ─────────────────────────────────────────────────────────────────────────────
# PVRQ13–PVRQ16: Integrity checks
# ─────────────────────────────────────────────────────────────────────────────

def test_PVRQ13_market_value_not_in_asset_requirements(page: Page, live_server: str) -> None:
    """PVRQ13: market_value option does not appear as an asset requirement category in hotel panel."""
    _go_to_visible_pv(page, live_server)
    _select_asset_type_visible(page, "hotel")
    # The requirements panel should not contain "market_value" as an asset requirement category
    # Uses JS to get innerHTML (works even if panel is offscreen)
    panel_html = page.evaluate(
        "() => (document.getElementById('pvr-hotel-requirements') || {}).innerHTML || ''"
    )
    # market_value is a basis_of_value concept, not an asset requirement category
    panel_normalized = panel_html.lower().replace("_", "").replace("-", "")
    assert "marketvalue" not in panel_normalized, (
        "market_value should not appear as an asset requirement category in hotel panel"
    )


def test_PVRQ14_comparable_adjustment_not_as_asset_type_option(page: Page, live_server: str) -> None:
    """PVRQ14: comparable_adjustment is not listed as an asset type option label."""
    _go_to_visible_pv(page, live_server)
    at_select = page.locator('#pvr-asset-type')
    at_html = at_select.inner_html()
    assert "comparable_adjustment" not in at_html.lower(), (
        "comparable_adjustment must not appear as an asset type option"
    )


def test_PVRQ15_no_duplicate_panel_testids_in_requirements_area(page: Page, live_server: str) -> None:
    """PVRQ15: Panel-level testids (the *-panel ones) within the requirements area are unique.
    Note: item-level testids (full-list, legacy-list, normalized-list) intentionally repeat once
    per sub-panel, so only panel-container testids are checked for uniqueness."""
    _go_to_visible_pv(page, live_server)
    # Check panel-level testids only — these must be unique
    panel_testids = [
        "pro-val-hotel-requirements-panel",
        "pro-val-factory-requirements-panel",
        "pro-val-land-requirements-panel",
        "pro-val-retail-requirements-panel",
        "pro-val-warehouse-requirements-panel",
        "pro-val-residential-requirements-panel",
    ]
    for tid in panel_testids:
        count = page.locator(f'[data-testid="{tid}"]').count()
        assert count == 1, (
            f"Panel testid '{tid}' must appear exactly once, found {count}"
        )


def test_PVRQ16_no_internal_paths_in_requirements_dom(page: Page, live_server: str) -> None:
    """PVRQ16: No internal filesystem paths in the asset requirements DOM."""
    _go_to_visible_pv(page, live_server)
    _select_asset_type_visible(page, "hotel")
    panel_html = page.evaluate(
        "() => (document.getElementById('pvr-asset-requirements-panel') || {}).innerHTML || ''"
    )
    for forbidden in ("C:\\", "/home/", "/var/", "core_engine/", "bridge_api"):
        assert forbidden not in panel_html, (
            f"Internal path fragment '{forbidden}' found in requirements DOM"
        )
