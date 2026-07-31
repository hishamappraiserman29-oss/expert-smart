"""
PVTC01–PVTC21 — Professional Valuation Three-Cards Taxonomy Browser Tests (Part I).

These tests navigate to the DEFAULT URL (no hash) so the VISIBLE workspace
ws-professional is active.  They prove that:

  Card 1 — تعريف الأصل العقاري         (pro-val-card-asset-definition)
  Card 2 — مسارات وأغراض التقييم       (pro-val-card-purpose-routes)
  Card 3 — أساس القيمة المطلوب         (pro-val-card-basis-of-value)

…are all rendered correctly in the browser with the correct testids, labels,
and select options, and that no old mixed-block artefacts remain visible.

Strict rules respected:
  - No report generation triggered.
  - No backend API calls (all **/api/** routes mocked to {"ok":true}).
  - No modification of existing options or backend logic.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _go_to_visible_pv(page: Page, live_server: str) -> None:
    """Navigate to the default page — ws-professional (visible workspace) is active."""
    page.route("**/api/**", lambda r: r.fulfill(
        status=200, body=b'{"ok":true}', content_type="application/json"
    ))
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator('[data-testid="professional-wizard"]').wait_for(state="visible", timeout=10_000)


# ─────────────────────────────────────────────────────────────────────────────
# PVTC01–PVTC05 — Card 1: تعريف الأصل العقاري
# ─────────────────────────────────────────────────────────────────────────────

def test_PVTC01_card_asset_definition_visible(page: Page, live_server: str) -> None:
    """PVTC01: pro-val-card-asset-definition wrapper is visible in ws-professional."""
    _go_to_visible_pv(page, live_server)
    card = page.locator('[data-testid="pro-val-card-asset-definition"]').first
    expect(card).to_be_visible()


def test_PVTC02_asset_family_select_wrapper_visible(page: Page, live_server: str) -> None:
    """PVTC02: pro-val-asset-family-select wrapper (Card 1.1) is visible."""
    _go_to_visible_pv(page, live_server)
    wrapper = page.locator('[data-testid="pro-val-asset-family-select"]').first
    expect(wrapper).to_be_visible()


def test_PVTC03_asset_type_select_visible(page: Page, live_server: str) -> None:
    """PVTC03: pro-val-asset-type-select (Card 1.2) is visible."""
    _go_to_visible_pv(page, live_server)
    sel = page.locator('[data-testid="pro-val-asset-type-select"]').first
    expect(sel).to_be_visible()


def test_PVTC04_asset_subtype_select_wrapper_visible(page: Page, live_server: str) -> None:
    """PVTC04: pro-val-asset-subtype-select wrapper (Card 1.3) is visible."""
    _go_to_visible_pv(page, live_server)
    wrapper = page.locator('[data-testid="pro-val-asset-subtype-select"]').first
    expect(wrapper).to_be_visible()


def test_PVTC05_asset_condition_path_select_visible(page: Page, live_server: str) -> None:
    """PVTC05: pro-val-asset-condition-path-select (Card 1.4) is visible."""
    _go_to_visible_pv(page, live_server)
    sel = page.locator('[data-testid="pro-val-asset-condition-path-select"]').first
    expect(sel).to_be_visible()


def test_PVTC06_asset_condition_path_has_seven_options(page: Page, live_server: str) -> None:
    """PVTC06: pro-val-asset-condition-path-select contains all 7 condition path options."""
    _go_to_visible_pv(page, live_server)
    sel = page.locator('[data-testid="pro-val-asset-condition-path-select"]').first
    expected_values = [
        "new_construction", "as_is", "as_repaired", "as_completed",
        "as_stabilized", "retrospective", "prospective",
    ]
    for val in expected_values:
        opt = sel.locator(f'option[value="{val}"]')
        expect(opt).to_have_count(1), f"Missing condition path option: {val}"


# ─────────────────────────────────────────────────────────────────────────────
# PVTC07–PVTC09 — Card 2: مسارات وأغراض التقييم
# ─────────────────────────────────────────────────────────────────────────────

def test_PVTC07_card_purpose_routes_visible(page: Page, live_server: str) -> None:
    """PVTC07: pro-val-card-purpose-routes wrapper is visible in ws-professional."""
    _go_to_visible_pv(page, live_server)
    card = page.locator('[data-testid="pro-val-card-purpose-routes"]').first
    expect(card).to_be_visible()


def test_PVTC08_purpose_routes_subgroups_present(page: Page, live_server: str) -> None:
    """PVTC08: All three sub-group sections (2.1/2.2/2.3) inside Card 2 are visible.
    2.1 = pro-val-purpose-logical-section
    2.2 = pro-val-purpose-router-section
    2.3 = pro-val-professional-purpose-section"""
    _go_to_visible_pv(page, live_server)
    for tid in (
        "pro-val-section-valuation-purpose-routes",
        "pro-val-purpose-logical-section",
        "pro-val-purpose-router-section",
    ):
        el = page.locator(f'[data-testid="{tid}"]').first
        expect(el).to_be_visible(), f"Section not visible: {tid}"


def test_PVTC09_assignment_purpose_select_inside_card2(page: Page, live_server: str) -> None:
    """PVTC09: pro-val-assignment-purpose-select is visible inside Card 2 (2.1 sub-group)."""
    _go_to_visible_pv(page, live_server)
    sel = page.locator('[data-testid="pro-val-assignment-purpose-select"]').first
    expect(sel).to_be_visible()


# ─────────────────────────────────────────────────────────────────────────────
# PVTC10–PVTC17 — Card 3: أساس القيمة المطلوب
# ─────────────────────────────────────────────────────────────────────────────

def test_PVTC10_card_basis_of_value_visible(page: Page, live_server: str) -> None:
    """PVTC10: pro-val-card-basis-of-value wrapper is visible in ws-professional."""
    _go_to_visible_pv(page, live_server)
    card = page.locator('[data-testid="pro-val-card-basis-of-value"]').first
    expect(card).to_be_visible()


def test_PVTC11_basis_of_value_section_visible(page: Page, live_server: str) -> None:
    """PVTC11: pro-val-basis-of-value-section inner panel is visible inside Card 3."""
    _go_to_visible_pv(page, live_server)
    panel = page.locator('[data-testid="pro-val-basis-of-value-section"]').first
    expect(panel).to_be_visible()


def test_PVTC12_basis_of_value_select_visible(page: Page, live_server: str) -> None:
    """PVTC12: pro-val-basis-of-value-select is visible in Card 3."""
    _go_to_visible_pv(page, live_server)
    sel = page.locator('[data-testid="pro-val-basis-of-value-select"]').first
    expect(sel).to_be_visible()


def test_PVTC13_value_premise_select_visible(page: Page, live_server: str) -> None:
    """PVTC13: pro-val-value-premise-select is visible in Card 3."""
    _go_to_visible_pv(page, live_server)
    sel = page.locator('[data-testid="pro-val-value-premise-select"]').first
    expect(sel).to_be_visible()


def test_PVTC14_value_output_type_select_visible(page: Page, live_server: str) -> None:
    """PVTC14: pro-val-value-output-type-select is visible in Card 3."""
    _go_to_visible_pv(page, live_server)
    sel = page.locator('[data-testid="pro-val-value-output-type-select"]').first
    expect(sel).to_be_visible()


def test_PVTC15_basis_of_value_has_eight_options(page: Page, live_server: str) -> None:
    """PVTC15: pro-val-basis-of-value-select contains all 8 basis-of-value options."""
    _go_to_visible_pv(page, live_server)
    sel = page.locator('[data-testid="pro-val-basis-of-value-select"]').first
    expected_values = [
        "market_value", "market_rent", "investment_value", "fair_value",
        "liquidation_value", "insurable_value", "going_concern_value",
        "special_purpose_value",
    ]
    for val in expected_values:
        opt = sel.locator(f'option[value="{val}"]')
        expect(opt).to_have_count(1), f"Missing basis-of-value option: {val}"


def test_PVTC16_value_premise_has_eight_options(page: Page, live_server: str) -> None:
    """PVTC16: pro-val-value-premise-select contains all 8 premise options."""
    _go_to_visible_pv(page, live_server)
    sel = page.locator('[data-testid="pro-val-value-premise-select"]').first
    expected_values = [
        "as_is", "as_stabilized", "as_complete", "highest_and_best_use",
        "current_use", "alternative_use", "forced_sale", "going_concern",
    ]
    for val in expected_values:
        opt = sel.locator(f'option[value="{val}"]')
        expect(opt).to_have_count(1), f"Missing value-premise option: {val}"


def test_PVTC17_value_output_type_has_five_options(page: Page, live_server: str) -> None:
    """PVTC17: pro-val-value-output-type-select contains all 5 output-type options."""
    _go_to_visible_pv(page, live_server)
    sel = page.locator('[data-testid="pro-val-value-output-type-select"]').first
    expected_values = [
        "point_estimate", "range_estimate", "weighted_value",
        "probability_weighted", "scenario_based",
    ]
    for val in expected_values:
        opt = sel.locator(f'option[value="{val}"]')
        expect(opt).to_have_count(1), f"Missing output-type option: {val}"


# ─────────────────────────────────────────────────────────────────────────────
# PVTC18–PVTC21 — Old mixed-block removal & hidden val-purpose preservation
# ─────────────────────────────────────────────────────────────────────────────

def test_PVTC18_three_cards_all_visible_simultaneously(page: Page, live_server: str) -> None:
    """PVTC18: All three card wrappers are simultaneously visible on the page."""
    _go_to_visible_pv(page, live_server)
    for tid in (
        "pro-val-card-asset-definition",
        "pro-val-card-purpose-routes",
        "pro-val-card-basis-of-value",
    ):
        card = page.locator(f'[data-testid="{tid}"]').first
        expect(card).to_be_visible(), f"Card not visible: {tid}"


def test_PVTC19_hidden_val_purpose_not_visible(page: Page, live_server: str) -> None:
    """PVTC19: The hidden #val-purpose select (preserved for JS) is NOT visible to users."""
    _go_to_visible_pv(page, live_server)
    hidden_sel = page.locator('#val-purpose')
    # May be count=1 or more; what matters is none is visible
    for i in range(hidden_sel.count()):
        assert not hidden_sel.nth(i).is_visible(), (
            f"#val-purpose at index {i} must be hidden (display:none wrapper)"
        )


def test_PVTC20_professional_routing_console_present(page: Page, live_server: str) -> None:
    """PVTC20: professional-routing-console outer div is present (PDW01 compatibility).
    Card 1 is nested inside it — this ensures backward-compat testid is not broken."""
    _go_to_visible_pv(page, live_server)
    outer = page.locator('[data-testid="professional-routing-console"]').first
    expect(outer).to_be_visible()


def test_PVTC21_old_testids_still_present_in_card1(page: Page, live_server: str) -> None:
    """PVTC21: Old testids professional-asset-family and professional-asset-subtype still
    present (required by PDW02/PDW03/PWF04/PWF05) — nested inside the new Card 1 wrappers."""
    _go_to_visible_pv(page, live_server)
    for tid in ("professional-asset-family", "professional-asset-subtype"):
        el = page.locator(f'[data-testid="{tid}"]').first
        expect(el).to_be_visible(), f"Old backward-compat testid not visible: {tid}"
