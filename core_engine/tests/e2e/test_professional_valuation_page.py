"""
PVP01–PVP09 — Professional Valuation Backoffice Page E2E Tests (Phase A Scaffold).

Verifies that the Phase A frontend scaffold is correctly in place:
- Tab hidden by default, shown via hash
- Dashboard placeholder and request table visible
- All required data-testids present
- Certification gate warnings visible
- Existing simple valuation and tax appeal tabs still work

Phase A: scaffold only — no API calls tested here (backend not implemented).
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
    # Wait for the workspace to become visible
    page.locator('[data-testid="pro-val-workspace"]').wait_for(state="visible", timeout=10_000)


def _block_api(page: Page) -> None:
    """Block all API calls so tests are purely frontend."""
    page.route("**/api/**", lambda r: r.fulfill(
        status=200, body=b'{"ok":true}', content_type="application/json"
    ))


# ─────────────────────────────────────────────────────────────────────────────
# PVP01 — Tab hidden by default
# ─────────────────────────────────────────────────────────────────────────────

def test_PVP01_professional_valuation_tab_hidden_by_default(page: Page, live_server: str) -> None:
    """PVP01: The professional-valuation-tab button is hidden by default on page load."""
    _block_api(page)
    page.goto(live_server, wait_until="domcontentloaded")
    tab_btn = page.locator('[data-testid="professional-valuation-tab"]')
    expect(tab_btn).to_have_count(1)
    # Verify it is not visible (hidden via display:none)
    assert tab_btn.evaluate("el => window.getComputedStyle(el).display") == "none", (
        "Professional valuation tab should be hidden by default"
    )


# ─────────────────────────────────────────────────────────────────────────────
# PVP02 — Hash shows workspace
# ─────────────────────────────────────────────────────────────────────────────

def test_PVP02_hash_shows_professional_valuation_workspace(page: Page, live_server: str) -> None:
    """PVP02: Navigating to #professional-valuation shows the ws-professional-valuation workspace."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    ws = page.locator('[data-testid="pro-val-workspace"]')
    expect(ws).to_be_visible()


# ─────────────────────────────────────────────────────────────────────────────
# PVP03 — Dashboard placeholder visible
# ─────────────────────────────────────────────────────────────────────────────

def test_PVP03_dashboard_placeholder_visible(page: Page, live_server: str) -> None:
    """PVP03: The pro-val-dashboard section is visible in the scaffold."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    dashboard = page.locator('[data-testid="pro-val-dashboard"]')
    expect(dashboard).to_be_visible()


# ─────────────────────────────────────────────────────────────────────────────
# PVP04 — Request table placeholder visible
# ─────────────────────────────────────────────────────────────────────────────

def test_PVP04_request_table_placeholder_visible(page: Page, live_server: str) -> None:
    """PVP04: The pro-val-request-table is visible and contains a placeholder row."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    table = page.locator('[data-testid="pro-val-request-table"]')
    expect(table).to_be_visible()
    placeholder_row = page.locator('[data-testid="pro-val-request-row"]')
    expect(placeholder_row).to_have_count(1)


# ─────────────────────────────────────────────────────────────────────────────
# PVP05 — Certification gate warning visible
# ─────────────────────────────────────────────────────────────────────────────

def test_PVP05_certification_blocked_warning_visible(page: Page, live_server: str) -> None:
    """PVP05: The certification-blocked warning is visible in the scaffold."""
    _block_api(page)
    _go_to_pro_val(page, live_server)
    warning = page.locator('[data-testid="pro-val-certification-blocked-warning"]')
    expect(warning).to_be_visible()
    # Must contain the Arabic advisory text
    expect(warning).to_contain_text("الاعتماد")


# ─────────────────────────────────────────────────────────────────────────────
# PVP06 — All 15 tab buttons visible
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# PVP07 — No API calls required for scaffold
# ─────────────────────────────────────────────────────────────────────────────

def test_PVP07_scaffold_visible_without_api_calls(page: Page, live_server: str) -> None:
    """PVP07: The scaffold is fully visible without any backend API calls succeeding."""
    api_calls: list[str] = []
    page.route("**/api/professional-valuation/**", lambda r: (
        api_calls.append(r.request.url), r.fulfill(status=503, body=b'{"error":"not implemented"}')
    ))
    _go_to_pro_val(page, live_server)
    # Dashboard and workspace should be visible even with 503 from professional API
    expect(page.locator('[data-testid="pro-val-dashboard"]')).to_be_visible()
    # Phase A scaffold makes no API calls on load
    assert api_calls == [], f"Scaffold made unexpected API calls: {api_calls}"


# ─────────────────────────────────────────────────────────────────────────────
# PVP08 — Existing simple valuation tab still works
# ─────────────────────────────────────────────────────────────────────────────

def test_PVP08_existing_simple_valuation_tab_still_works(page: Page, live_server: str) -> None:
    """PVP08: The simple valuation tab still renders correctly after scaffold addition."""
    _block_api(page)
    page.goto(live_server, wait_until="domcontentloaded")
    val_btn = page.locator('#es-tab-valuation')
    expect(val_btn).to_have_count(1)
    val_btn.click()
    page.locator('[data-testid="simple-valuation-tab"]').wait_for(state="visible", timeout=10_000)
    expect(page.locator('[data-testid="simple-valuation-tab"]')).to_be_visible()


# ─────────────────────────────────────────────────────────────────────────────
# PVP09 — Tax appeal tab still works
# ─────────────────────────────────────────────────────────────────────────────

def test_PVP09_tax_appeal_tab_still_works(page: Page, live_server: str) -> None:
    """PVP09: The tax appeal tab still renders correctly after scaffold addition."""
    _block_api(page)
    page.goto(live_server, wait_until="domcontentloaded")
    tax_btn = page.locator('[data-testid="tax-tab"]')
    expect(tax_btn).to_have_count(1)
    tax_btn.click()
    page.locator('[data-testid="tax-page"]').wait_for(state="visible", timeout=10_000)
    expect(page.locator('[data-testid="tax-page"]')).to_be_visible()
