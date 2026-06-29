"""
PVP01–PVP18 — Professional Valuation Backoffice Page E2E Tests (Phase A + Phase B).

Phase A tests (PVP01–PVP09):
  Scaffold rendering — tab visibility, hash navigation, governance warnings,
  placeholder table, detail tabs, no API calls without auth.

Phase B tests (PVP10–PVP18):
  Phase B UI elements — phase-b-placeholder, new-request-form, certified-disabled,
  empty-state, detail-panel, transition controls, gate summary, regression on
  simple-valuation and tax-appeal tabs.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _go_to_pro_val(page: Page, live_server: str) -> None:
    """Navigate to the professional valuation backoffice via hash."""
    page.goto(f"{live_server}#professional-valuation", wait_until="domcontentloaded")
    page.locator('[data-testid="pro-val-workspace"]').wait_for(state="visible", timeout=10_000)


def _block_api(page: Page) -> None:
    """Block all API calls so tests are purely frontend."""
    page.route("**/api/**", lambda r: r.fulfill(
        status=200, body=b'{"ok":true}', content_type="application/json"
    ))


# ─────────────────────────────────────────────────────────────────────────────
# Phase A Tests — PVP01–PVP09 (scaffold rendering)
# ─────────────────────────────────────────────────────────────────────────────

def test_PVP01_professional_valuation_tab_hidden_by_default(page: Page, live_server: str) -> None:
    """PVP01: The professional-valuation-tab button is hidden by default on page load."""
    _block_api(page)
    page.goto(live_server, wait_until="domcontentloaded")
    tab_btn = page.locator('[data-testid="professional-valuation-tab"]')
    expect(tab_btn).to_have_count(1)
    assert tab_btn.evaluate("el => window.getComputedStyle(el).display") == "none", (
        "Professional valuation tab should be hidden by default"
    )


def test_PVP02_hash_shows_professional_valuation_workspace(page: Page, live_server: str) -> None:
    """PVP02: Navigating to #professional-valuation shows the ws-professional-valuation workspace."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    ws = page.locator('[data-testid="pro-val-workspace"]')
    expect(ws).to_be_visible()


def test_PVP03_dashboard_placeholder_visible(page: Page, live_server: str) -> None:
    """PVP03: The pro-val-dashboard section is visible in the scaffold."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    dashboard = page.locator('[data-testid="pro-val-dashboard"]')
    expect(dashboard).to_be_visible()


def test_PVP04_request_table_placeholder_visible(page: Page, live_server: str) -> None:
    """PVP04: The pro-val-request-table is visible and contains a placeholder row."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    table = page.locator('[data-testid="pro-val-request-table"]')
    expect(table).to_be_visible()
    placeholder_row = page.locator('[data-testid="pro-val-request-row"]')
    expect(placeholder_row).to_have_count(1)


def test_PVP05_certification_blocked_warning_visible(page: Page, live_server: str) -> None:
    """PVP05: The certification-blocked warning is visible and contains Arabic advisory text."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    warning = page.locator('[data-testid="pro-val-certification-blocked-warning"]')
    expect(warning).to_be_visible()
    expect(warning).to_contain_text("الاعتماد")


def test_PVP06_all_detail_tabs_visible(page: Page, live_server: str) -> None:
    """PVP06: All 15 detail workspace tab buttons are present in the scaffold."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    required_tabs = [
        "pro-val-tab-summary",
        "pro-val-tab-property",
        "pro-val-tab-scope",
        "pro-val-tab-evidence",
        "pro-val-tab-sources",
        "pro-val-tab-methods",
        "pro-val-tab-hbu",
        "pro-val-tab-dcf",
        "pro-val-tab-swot",
        "pro-val-tab-esg",
        "pro-val-tab-legal",
        "pro-val-tab-governance",
        "pro-val-tab-peer-review",
        "pro-val-tab-signature",
        "pro-val-tab-outputs",
    ]
    for testid in required_tabs:
        el = page.locator(f'[data-testid="{testid}"]')
        expect(el).to_have_count(1), f"Tab {testid} not found"


def test_PVP07_scaffold_visible_without_pro_val_api_calls(page: Page, live_server: str) -> None:
    """PVP07: Dashboard is visible even if professional-valuation API returns 503.
    Without a stored auth token, no API calls are made on scaffold load.
    """
    api_calls: list[str] = []
    page.route("**/api/professional-valuation/**", lambda r: (
        api_calls.append(r.request.url), r.fulfill(status=503, body=b'{"error":"not implemented"}')
    ))
    _go_to_pro_val(page, live_server)
    expect(page.locator('[data-testid="pro-val-dashboard"]')).to_be_visible()
    # Phase B: without a stored token, no API calls are made on load
    assert api_calls == [], f"Scaffold made unexpected API calls: {api_calls}"


def test_PVP08_existing_simple_valuation_tab_still_works(page: Page, live_server: str) -> None:
    """PVP08: The simple valuation tab still renders correctly after Phase B changes."""
    _block_api(page)
    page.goto(live_server, wait_until="domcontentloaded")
    val_btn = page.locator('#es-tab-valuation')
    expect(val_btn).to_have_count(1)
    val_btn.click()
    page.locator('[data-testid="simple-valuation-tab"]').wait_for(state="visible", timeout=10_000)
    expect(page.locator('[data-testid="simple-valuation-tab"]')).to_be_visible()


def test_PVP09_tax_appeal_tab_still_works(page: Page, live_server: str) -> None:
    """PVP09: The tax appeal tab still renders correctly after Phase B changes."""
    _block_api(page)
    page.goto(live_server, wait_until="domcontentloaded")
    tax_btn = page.locator('[data-testid="tax-tab"]')
    expect(tax_btn).to_have_count(1)
    tax_btn.click()
    page.locator('[data-testid="tax-page"]').wait_for(state="visible", timeout=10_000)
    expect(page.locator('[data-testid="tax-page"]')).to_be_visible()


# ─────────────────────────────────────────────────────────────────────────────
# Phase B Tests — PVP10–PVP18 (new UI elements)
# ─────────────────────────────────────────────────────────────────────────────

def test_PVP10_phase_b_placeholder_visible(page: Page, live_server: str) -> None:
    """PVP10: The Phase B placeholder/notice banner is visible."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    ph = page.locator('[data-testid="pro-val-phase-b-placeholder"]')
    expect(ph).to_be_visible()
    expect(ph).to_contain_text("Phase B")


def test_PVP11_new_request_form_present(page: Page, live_server: str) -> None:
    """PVP11: The new-request-form element is present in the DOM (may be hidden initially)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    form = page.locator('[data-testid="pro-val-new-request-form"]')
    expect(form).to_have_count(1)


def test_PVP12_create_request_button_present(page: Page, live_server: str) -> None:
    """PVP12: The create-request-button is present inside the new-request-form."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    btn = page.locator('[data-testid="pro-val-create-request-button"]')
    expect(btn).to_have_count(1)


def test_PVP13_certified_disabled_element_present(page: Page, live_server: str) -> None:
    """PVP13: The pro-val-certified-disabled indicator is present (certified report blocked)."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-certified-disabled"]')
    expect(el).to_have_count(1)


def test_PVP14_request_empty_state_present(page: Page, live_server: str) -> None:
    """PVP14: The request-empty-state element is present in the DOM."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-request-empty-state"]')
    expect(el).to_have_count(1)


def test_PVP15_detail_panel_present(page: Page, live_server: str) -> None:
    """PVP15: The pro-val-detail-panel element is present in the workspace."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-detail-panel"]')
    expect(el).to_have_count(1)


def test_PVP16_transition_controls_present(page: Page, live_server: str) -> None:
    """PVP16: Transition select and button are present in the detail panel."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    sel = page.locator('[data-testid="pro-val-transition-select"]')
    btn = page.locator('[data-testid="pro-val-transition-button"]')
    expect(sel).to_have_count(1)
    expect(btn).to_have_count(1)


def test_PVP17_certification_gate_summary_present(page: Page, live_server: str) -> None:
    """PVP17: The certification-gate-summary placeholder is visible in the workspace."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    el = page.locator('[data-testid="pro-val-certification-gate-summary"]')
    expect(el).to_have_count(1)
    expect(el).to_be_visible()


def test_PVP18_generate_certified_button_disabled(page: Page, live_server: str) -> None:
    """PVP18: The generate-certified button is disabled — certification blocked in Phase B."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    btn = page.locator('[data-testid="pro-val-generate-certified"]')
    expect(btn).to_have_count(1)
    assert btn.is_disabled(), "Certified report button should be disabled in Phase B"
