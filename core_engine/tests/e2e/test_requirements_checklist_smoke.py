"""
E2E smoke tests for Phase 8B — Frontend Requirements Checklist Panel.

Requires a running bridge_api server (managed by conftest.py) and Playwright.

    pytest core_engine/tests/e2e/test_requirements_checklist_smoke.py -v

  CS01 — panel hidden on initial page load
  CS02 — panel appears after valid asset_type + purpose selection (mocked API)
  CS03 — required fields are rendered inside the panel (mocked API)
  CS04 — panel stays hidden when API returns 400 (unsupported combo)
  CS05 — core valuation UI elements are still intact after Phase 8B injection
"""
from __future__ import annotations

import json

from playwright.sync_api import Page, Route, expect

_LS_KEY       = "es_auth"
_MOCK_SESSION = json.dumps({"token": "mock-token-cs", "user_id": "smoke-user", "is_admin": False})

_SAMPLE_RESPONSE = {
    "status": "ok",
    "asset_type": "residential",
    "purpose": "market_value",
    "checklist_items": [
        {"name": "comparable",  "required": True,  "field_type": "float", "description": "Comparable value", "valid_values": []},
        {"name": "cost",        "required": True,  "field_type": "float", "description": "Cost value",       "valid_values": []},
        {"name": "income",      "required": True,  "field_type": "float", "description": "Income value",     "valid_values": []},
        {"name": "client_name", "required": False, "field_type": "str",   "description": "Client name",      "valid_values": []},
    ],
    "dynamic_fields": [],
    "recommended_methods": ["comparable", "cost", "income"],
    "notes": "",
}


def _inject_session(page: Page) -> None:
    page.evaluate(f"localStorage.setItem('{_LS_KEY}', {_MOCK_SESSION!r})")


def _mock_req_ok(page: Page) -> None:
    def handle(route: Route) -> None:
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(_SAMPLE_RESPONSE),
        )
    page.route("**/api/valuation/requirements**", handle)


def _mock_req_400(page: Page) -> None:
    def handle(route: Route) -> None:
        route.fulfill(
            status=400,
            content_type="application/json",
            body=json.dumps({"status": "error", "message": "not supported"}),
        )
    page.route("**/api/valuation/requirements**", handle)


# ── CS01 ──────────────────────────────────────────────────────────────────────

def test_CS01_panel_hidden_on_load(page: Page, live_server: str) -> None:
    """Requirements checklist panel is hidden on initial page load."""
    page.goto(live_server, wait_until="networkidle")
    panel = page.locator("#es-req-panel")
    expect(panel).to_be_attached()
    assert not panel.is_visible(), "#es-req-panel should be hidden on initial load"


# ── CS02 ──────────────────────────────────────────────────────────────────────

def test_CS02_panel_shows_on_valid_selection(page: Page, live_server: str) -> None:
    """Selecting a mapped asset_type + purpose triggers the fetch and shows the panel."""
    _mock_req_ok(page)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
    expect(page.locator("#es-req-panel")).to_be_visible()


# ── CS03 ──────────────────────────────────────────────────────────────────────

def test_CS03_required_fields_rendered(page: Page, live_server: str) -> None:
    """Required fields section is non-empty after a successful fetch."""
    _mock_req_ok(page)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
    assert page.locator("#es-req-required").inner_text().strip() != "", (
        "#es-req-required should contain field rows after a successful fetch"
    )


# ── CS04 ──────────────────────────────────────────────────────────────────────

def test_CS04_panel_hides_on_400(page: Page, live_server: str) -> None:
    """Panel stays hidden when the API returns 400 (unsupported combination)."""
    _mock_req_400(page)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="أرض فضاء")
    page.select_option("#val-purpose", value="bank_financing")

    page.wait_for_timeout(1_500)
    assert not page.locator("#es-req-panel").is_visible(), (
        "#es-req-panel should remain hidden when API returns 400"
    )


# ── CS05 ──────────────────────────────────────────────────────────────────────

def test_CS05_existing_valuation_ui_intact(page: Page, live_server: str) -> None:
    """Core valuation UI elements are still present after Phase 8B HTML injection."""
    page.goto(live_server, wait_until="networkidle")
    expect(page.locator("#generateBtn")).to_be_visible()
    expect(page.locator("#asset-type")).to_be_visible()
    expect(page.locator("#val-purpose")).to_be_visible()
