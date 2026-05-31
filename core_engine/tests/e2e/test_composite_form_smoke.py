"""
Playwright smoke tests for frontend/composite_valuation.html (Wave 5b).

These tests require a running bridge_api server (managed by conftest.py)
and a Playwright browser (chromium).  Run with:

    pytest core_engine/tests/e2e/ -v

or just this file:

    pytest core_engine/tests/e2e/test_composite_form_smoke.py -v
"""
from __future__ import annotations

import json

import pytest
from playwright.sync_api import Page, expect

_PAGE_PATH = "/composite_valuation.html"

# ─────────────────────────────────────────────────────────────────────────────
# Minimal mock schema — isolates tests from real JWT / server state.
# 2 asset types (one with attrs, one without) and 2 purposes.
# ─────────────────────────────────────────────────────────────────────────────
_MOCK_SCHEMA = {
    "composite_api_version": 1,
    "asset_types": [
        {
            "name": "وحدة سكنية (شقة / فيلا)",
            "attributes": [
                {"name": "bedrooms_count", "type": "int"},
                {"name": "floor_number",   "type": "int"},
            ],
        },
        {
            "name": "أرض سكنية",
            "attributes": [],
        },
    ],
    "purposes": [
        {
            "name": "البيع والشراء - القيمة السوقية العادلة (Market Value)",
            "multiplier": 1.0,
            "deep": False,
        },
        {
            "name": "الرهن والتمويل البنكي - القيمة السوقية لأغراض التمويل (0.95x)",
            "multiplier": 0.95,
            "deep": False,
        },
    ],
}

_MOCK_SESSION_OBJ = {
    "token":    "mock-wave5b-smoke-token",
    "user_id":  "cv-smoke-user",
    "is_admin": False,
}


def _setup_session_and_schema(page: Page, live_server: str) -> None:
    """Navigate to the page, inject a mock session, intercept the schema
    endpoint, then reload so DOMContentLoaded sees the session.

    Same pattern as test_frontend_smoke.py: goto → evaluate → reload.
    The route interceptor persists across the reload.
    """
    page.route(
        "**/api/valuation/composite/schema",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(_MOCK_SCHEMA),
        ),
    )
    page.goto(live_server + _PAGE_PATH, wait_until="networkidle")
    page.evaluate(
        "localStorage.setItem('es_auth', JSON.stringify("
        + json.dumps(_MOCK_SESSION_OBJ)
        + "));"
    )
    page.reload(wait_until="networkidle")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Page load — no session, no console errors
# ─────────────────────────────────────────────────────────────────────────────

def test_page_loads_no_console_errors(page: Page, live_server: str) -> None:
    """composite_valuation.html loads (no session) without unexpected JS errors."""
    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.goto(live_server + _PAGE_PATH, wait_until="networkidle")
    # Only filter resource-load 401s from the schema endpoint (same tolerance
    # as test_frontend_smoke.py for background auth-guarded calls).
    real_errors = [
        e for e in errors
        if not ("Failed to load resource" in e and "401" in e)
    ]
    assert real_errors == [], f"Unexpected JS console errors: {real_errors}"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Auth guard — no session shows prompt, hides form
# ─────────────────────────────────────────────────────────────────────────────

def test_no_token_shows_auth_prompt(page: Page, live_server: str) -> None:
    """Without a stored session, #cv-no-auth is visible and the form is hidden."""
    page.goto(live_server + _PAGE_PATH, wait_until="networkidle")
    # localStorage is empty in a fresh browser context — no explicit removeItem needed.
    expect(page.locator("#cv-no-auth")).to_be_visible()
    expect(page.locator("#cv-main")).not_to_be_visible()


# ─────────────────────────────────────────────────────────────────────────────
# 3. Schema loading — asset-type select populated
# ─────────────────────────────────────────────────────────────────────────────

def test_schema_loads_populates_asset_type_select(page: Page, live_server: str) -> None:
    """After schema loads the first component's asset-type select has options."""
    _setup_session_and_schema(page, live_server)

    expect(page.locator("#cv-form")).to_be_visible(timeout=8_000)

    # cvLoadSchema auto-adds one component (index 0)
    asset_sel = page.locator("#cv-asset-type-0")
    expect(asset_sel).to_be_visible()
    # One blank option + mock schema types
    option_count = asset_sel.locator("option[value]:not([value=''])").count()
    assert option_count == len(_MOCK_SCHEMA["asset_types"]), (
        f"Expected {len(_MOCK_SCHEMA['asset_types'])} asset-type options, got {option_count}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Schema loading — global purpose dropdown populated
# ─────────────────────────────────────────────────────────────────────────────

def test_global_purpose_select_populated(page: Page, live_server: str) -> None:
    """Global purpose dropdown has one option per schema.purposes entry."""
    _setup_session_and_schema(page, live_server)
    expect(page.locator("#cv-form")).to_be_visible(timeout=8_000)

    sel = page.locator("#cv-global-purpose")
    expect(sel).to_be_visible()
    count = sel.locator("option").count()
    assert count == len(_MOCK_SCHEMA["purposes"]), (
        f"Expected {len(_MOCK_SCHEMA['purposes'])} purpose options, got {count}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Dynamic attribute rendering on asset-type change
# ─────────────────────────────────────────────────────────────────────────────

def test_asset_type_change_renders_specific_attributes(page: Page, live_server: str) -> None:
    """Selecting an asset type with attributes reveals the attribute input fields."""
    _setup_session_and_schema(page, live_server)
    expect(page.locator("#cv-form")).to_be_visible(timeout=8_000)

    page.locator("#cv-asset-type-0").select_option("وحدة سكنية (شقة / فيلا)")

    attrs_div = page.locator("#cv-attrs-0")
    expect(attrs_div).to_be_visible()
    assert page.locator("#cv-attr-0-bedrooms_count").count() == 1, (
        "#cv-attr-0-bedrooms_count input not found after asset-type change"
    )
    assert page.locator("#cv-attr-0-floor_number").count() == 1, (
        "#cv-attr-0-floor_number input not found after asset-type change"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6. Purpose override toggle
# ─────────────────────────────────────────────────────────────────────────────

def test_override_toggle_shows_per_component_purpose(page: Page, live_server: str) -> None:
    """Override checkbox hidden by default; checking it reveals per-component purpose select."""
    _setup_session_and_schema(page, live_server)
    expect(page.locator("#cv-form")).to_be_visible(timeout=8_000)

    override_wrap = page.locator("#cv-override-purpose-0")
    assert not override_wrap.is_visible(), "Override purpose should be hidden before checkbox is checked"

    page.locator("#cv-override-chk-0").check()
    expect(override_wrap).to_be_visible()

    # Per-component purpose select must have same count as global
    per_comp_count = page.locator("#cv-purpose-0 option").count()
    assert per_comp_count == len(_MOCK_SCHEMA["purposes"]), (
        f"Per-component purpose select has {per_comp_count} options, "
        f"expected {len(_MOCK_SCHEMA['purposes'])}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 7. Submit sends POST with Authorization header and correct body shape
# ─────────────────────────────────────────────────────────────────────────────

def test_submit_sends_post_with_auth_header(page: Page, live_server: str) -> None:
    """Submitting the form fires POST /api/valuation/composite with
    Authorization: Bearer <token> and a body containing components + purposes arrays."""
    _setup_session_and_schema(page, live_server)
    expect(page.locator("#cv-form")).to_be_visible(timeout=8_000)

    captured: dict = {}

    def _intercept_post(route):
        req = route.request
        if req.method == "POST":
            captured["auth"] = req.headers.get("authorization", "")
            captured["body"] = req.post_data
        route.abort()

    page.route("**/api/valuation/composite", _intercept_post)

    # Fill required fields for the auto-added component
    page.locator("#cv-asset-type-0").select_option("أرض سكنية")  # no specific attrs
    page.locator("#cv-area-0").fill("200")
    page.locator("#cv-rate-0").fill("3000")
    page.locator("#cv-submit-btn").click()
    page.wait_for_timeout(2_000)

    assert "auth" in captured, "POST to /api/valuation/composite was not intercepted"
    assert captured["auth"] == "Bearer mock-wave5b-smoke-token", (
        f"Unexpected Authorization header: {captured['auth']!r}"
    )
    body = json.loads(captured["body"])
    assert "components" in body, "POST body missing 'components' key"
    assert "purposes" in body, "POST body missing 'purposes' key"
    assert isinstance(body["purposes"], list), "'purposes' must be a list"
    assert len(body["purposes"]) == len(body["components"]), (
        "purposes list length must equal components list length"
    )
    # Every component must carry an explicit purpose field (Gate B requirement).
    assert all("purpose" in c for c in body["components"]), (
        "Every component object must have an explicit 'purpose' field"
    )
    # component[i].purpose must equal purposes[i] for every position.
    for i, (comp, purp) in enumerate(zip(body["components"], body["purposes"])):
        assert comp["purpose"] == purp, (
            f"components[{i}].purpose {comp['purpose']!r} != purposes[{i}] {purp!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 8. Navigation link present in index.html
# ─────────────────────────────────────────────────────────────────────────────

def test_navigation_link_present_in_index(page: Page, live_server: str) -> None:
    """Phase 8H.1/8J: composite CTA link is contextual; appears in placeholder panels (فندق).

    Phase 8J removed the link from building_full (عمارة سكنية); placeholder profiles retain it.
    """
    page.goto(live_server, wait_until="networkidle")
    # Placeholder profiles render without auth and retain the composite CTA link
    page.select_option("#asset-type", value="فندق")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    link = page.locator("a[href='/composite_valuation.html']")
    assert link.count() >= 1, "Contextual composite CTA link not found after selecting فندق (placeholder)"
    expect(link.first).to_be_visible()
