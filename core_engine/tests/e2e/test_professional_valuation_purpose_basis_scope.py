"""
PVPBSR E2E Browser Tests
Professional Valuation Page — Purpose, Basis of Value, Intended User,
Scope, Standards, Weighting & Registry Integration

28 tests covering all new sub-sections visibility, dropdown options,
dynamic behavior (partial-interest panel toggle), weighting input.

All tests navigate to the live server root URL (ws-professional is
the default active workspace), exactly like the existing PVVIS/PVACUR
test pattern.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


# ── Helpers ───────────────────────────────────────────────────────────────────

def _goto(page: Page, live_server: str) -> None:
    """Navigate to the default page where ws-professional is active."""
    page.route("**/api/**", lambda r: r.fulfill(
        status=200, body=b'{"ok":true}', content_type="application/json"
    ))
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator('[data-testid="professional-wizard"]').wait_for(
        state="visible", timeout=12_000
    )


def _section3(page: Page):
    """Scoped locator for Section 3 inside the active professional workspace."""
    return page.locator('#ws-professional [data-testid="pro-val-section-valuation-purpose"]')


# ── PVPBSR01 — Section 3 is visible on the professional valuation page ────────
def test_PVPBSR01_section3_visible(page: Page, live_server: str) -> None:
    _goto(page, live_server)
    expect(_section3(page)).to_be_visible()


# ── PVPBSR02 — 3.1 purpose main subsection is visible ────────────────────────
def test_PVPBSR02_purpose_main_subsection_visible(page: Page, live_server: str) -> None:
    _goto(page, live_server)
    panel = _section3(page).locator('[data-testid="pro-val-purpose-main-subsection"]')
    expect(panel).to_be_visible()


# ── PVPBSR03 — assignment_purpose select is visible ──────────────────────────
def test_PVPBSR03_assignment_purpose_select_visible(page: Page, live_server: str) -> None:
    _goto(page, live_server)
    sel = _section3(page).locator('[data-testid="pro-val-assignment-purpose-select"]')
    expect(sel).to_be_visible()


# ── PVPBSR04 — purpose select contains tax_appeal option ─────────────────────
def test_PVPBSR04_tax_appeal_option_exists(page: Page, live_server: str) -> None:
    _goto(page, live_server)
    sel = _section3(page).locator('[data-testid="pro-val-assignment-purpose-select"]')
    opt = sel.locator('option[value="tax_appeal"]')
    expect(opt).to_have_count(1)


# ── PVPBSR05 — purpose select contains partial_interest_valuation option ──────
def test_PVPBSR05_partial_interest_option_exists(page: Page, live_server: str) -> None:
    _goto(page, live_server)
    sel = _section3(page).locator('[data-testid="pro-val-assignment-purpose-select"]')
    opt = sel.locator('option[value="partial_interest_valuation"]')
    expect(opt).to_have_count(1)


# ── PVPBSR06 — purpose select contains merger_acquisition option ──────────────
def test_PVPBSR06_merger_acquisition_option_exists(page: Page, live_server: str) -> None:
    _goto(page, live_server)
    sel = _section3(page).locator('[data-testid="pro-val-assignment-purpose-select"]')
    opt = sel.locator('option[value="merger_acquisition"]')
    expect(opt).to_have_count(1)


# ── PVPBSR07 — 3.2 intended user subsection is visible ───────────────────────
def test_PVPBSR07_intended_user_subsection_visible(page: Page, live_server: str) -> None:
    _goto(page, live_server)
    panel = _section3(page).locator('[data-testid="pro-val-intended-user-subsection"]')
    expect(panel).to_be_visible()


# ── PVPBSR08 — intended_user_name input is visible ───────────────────────────
def test_PVPBSR08_intended_user_name_input_visible(page: Page, live_server: str) -> None:
    _goto(page, live_server)
    inp = _section3(page).locator('[data-testid="pro-val-intended-user-name-input"]')
    expect(inp).to_be_visible()


# ── PVPBSR09 — 3.3 basis of value subsection is visible ──────────────────────
def test_PVPBSR09_basis_of_value_subsection_visible(page: Page, live_server: str) -> None:
    _goto(page, live_server)
    panel = _section3(page).locator('[data-testid="pro-val-basis-of-value-subsection"]')
    expect(panel).to_be_visible()


# ── PVPBSR10 — basis_of_value select is visible ──────────────────────────────
def test_PVPBSR10_basis_of_value_select_visible(page: Page, live_server: str) -> None:
    _goto(page, live_server)
    sel = _section3(page).locator('[data-testid="pro-val-basis-of-value-select"]')
    expect(sel).to_be_visible()


# ── PVPBSR11 — basis_of_value select has value_in_use option ─────────────────
def test_PVPBSR11_value_in_use_option(page: Page, live_server: str) -> None:
    _goto(page, live_server)
    sel = _section3(page).locator('[data-testid="pro-val-basis-of-value-select"]')
    opt = sel.locator('option[value="value_in_use"]')
    expect(opt).to_have_count(1)


# ── PVPBSR12 — basis_of_value select has special_value option ────────────────
def test_PVPBSR12_special_value_option(page: Page, live_server: str) -> None:
    _goto(page, live_server)
    sel = _section3(page).locator('[data-testid="pro-val-basis-of-value-select"]')
    opt = sel.locator('option[value="special_value"]')
    expect(opt).to_have_count(1)


# ── PVPBSR13 — value_premise select has as_repaired option ───────────────────
def test_PVPBSR13_value_premise_as_repaired(page: Page, live_server: str) -> None:
    _goto(page, live_server)
    sel = _section3(page).locator('[data-testid="pro-val-value-premise-select"]')
    expect(sel).to_be_visible()
    opt = sel.locator('option[value="as_repaired"]')
    expect(opt).to_have_count(1)


# ── PVPBSR14 — value_scope select is visible ─────────────────────────────────
def test_PVPBSR14_value_scope_select_visible(page: Page, live_server: str) -> None:
    _goto(page, live_server)
    sel = _section3(page).locator('[data-testid="pro-val-value-scope-select"]')
    expect(sel).to_be_visible()


# ── PVPBSR15 — 3.4 scope of work subsection is visible ───────────────────────
def test_PVPBSR15_scope_subsection_visible(page: Page, live_server: str) -> None:
    _goto(page, live_server)
    panel = _section3(page).locator('[data-testid="pro-val-scope-of-work-subsection"]')
    expect(panel).to_be_visible()


# ── PVPBSR16 — scope_of_work select is visible ───────────────────────────────
def test_PVPBSR16_scope_of_work_select_visible(page: Page, live_server: str) -> None:
    _goto(page, live_server)
    sel = _section3(page).locator('[data-testid="pro-val-scope-of-work-select"]')
    expect(sel).to_be_visible()


# ── PVPBSR17 — inspection_scope select is visible ────────────────────────────
def test_PVPBSR17_inspection_scope_select_visible(page: Page, live_server: str) -> None:
    _goto(page, live_server)
    sel = _section3(page).locator('[data-testid="pro-val-inspection-scope-select"]')
    expect(sel).to_be_visible()


# ── PVPBSR18 — limiting_conditions input is visible ──────────────────────────
def test_PVPBSR18_limiting_conditions_input_visible(page: Page, live_server: str) -> None:
    _goto(page, live_server)
    inp = _section3(page).locator('[data-testid="pro-val-limiting-conditions-input"]')
    expect(inp).to_be_visible()


# ── PVPBSR19 — 3.5 preliminary weighting subsection is NOT visible (removed) ──
def test_PVPBSR19_weighting_subsection_not_visible(page: Page, live_server: str) -> None:
    _goto(page, live_server)
    panel = _section3(page).locator('[data-testid="pro-val-preliminary-weighting-subsection"]')
    expect(panel).not_to_be_visible()


# ── PVPBSR20 — sales_comparison_weight input is NOT visible (removed) ─────────
def test_PVPBSR20_sales_comparison_weight_not_visible(page: Page, live_server: str) -> None:
    _goto(page, live_server)
    inp = _section3(page).locator('[data-testid="pro-val-sales-comparison-weight-input"]')
    expect(inp).not_to_be_visible()


# ── PVPBSR21 — income_approach_weight input is NOT visible (removed) ──────────
def test_PVPBSR21_income_approach_weight_not_visible(page: Page, live_server: str) -> None:
    _goto(page, live_server)
    inp = _section3(page).locator('[data-testid="pro-val-income-approach-weight-input"]')
    expect(inp).not_to_be_visible()


# ── PVPBSR22 — cost_approach_weight input is NOT visible (removed) ────────────
def test_PVPBSR22_cost_approach_weight_not_visible(page: Page, live_server: str) -> None:
    _goto(page, live_server)
    inp = _section3(page).locator('[data-testid="pro-val-cost-approach-weight-input"]')
    expect(inp).not_to_be_visible()


# ── PVPBSR23 — weighting_total_display is NOT visible (removed) ──────────────
def test_PVPBSR23_weighting_total_display_not_visible(page: Page, live_server: str) -> None:
    _goto(page, live_server)
    disp = _section3(page).locator('[data-testid="pro-val-weighting-total-display"]')
    expect(disp).not_to_be_visible()


# ── PVPBSR24 — 3.6 disclosures/warnings subsection is NOT visible (removed) ───
def test_PVPBSR24_disclosures_subsection_not_visible(page: Page, live_server: str) -> None:
    _goto(page, live_server)
    panel = _section3(page).locator('[data-testid="pro-val-disclosures-warnings-subsection"]')
    expect(panel).not_to_be_visible()


# ── PVPBSR25 — partial interest panel hidden by default ──────────────────────
def test_PVPBSR25_partial_interest_panel_hidden_by_default(page: Page, live_server: str) -> None:
    _goto(page, live_server)
    # Panel exists in DOM but is hidden (display:none) by default
    panel = page.locator('#ws-professional [data-testid="pro-val-partial-interest-panel"]')
    expect(panel).to_have_count(1)
    expect(panel).to_be_hidden()


# ── PVPBSR26 — partial interest panel shown when purpose selected ─────────────
def test_PVPBSR26_partial_interest_panel_shown_on_purpose_select(page: Page, live_server: str) -> None:
    _goto(page, live_server)
    sel = _section3(page).locator('[data-testid="pro-val-assignment-purpose-select"]')
    sel.select_option("partial_interest_valuation")
    panel = page.locator('#ws-professional [data-testid="pro-val-partial-interest-panel"]')
    expect(panel).to_be_visible()


# ── PVPBSR27 — DLOC input visible inside partial interest panel ───────────────
def test_PVPBSR27_dloc_input_visible_in_panel(page: Page, live_server: str) -> None:
    _goto(page, live_server)
    sel = _section3(page).locator('[data-testid="pro-val-assignment-purpose-select"]')
    sel.select_option("partial_interest_valuation")
    panel = page.locator('#ws-professional [data-testid="pro-val-partial-interest-panel"]')
    expect(panel).to_be_visible()
    dloc = panel.locator('[data-testid="pro-val-dloc-percent-input"]')
    expect(dloc).to_be_visible()


# ── PVPBSR28 — partial interest panel hides again when purpose changed back ───
def test_PVPBSR28_partial_interest_panel_hides_on_purpose_change(page: Page, live_server: str) -> None:
    _goto(page, live_server)
    sel = _section3(page).locator('[data-testid="pro-val-assignment-purpose-select"]')
    # Show it
    sel.select_option("partial_interest_valuation")
    panel = page.locator('#ws-professional [data-testid="pro-val-partial-interest-panel"]')
    expect(panel).to_be_visible()
    # Hide it again by switching to a different purpose
    sel.select_option("sale_purchase")
    expect(panel).to_be_hidden()
