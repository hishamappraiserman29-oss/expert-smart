"""
E2E smoke tests for Phase 8B/8C — Frontend Requirements Checklist Panel.

Requires a running bridge_api server (managed by conftest.py) and Playwright.

    pytest core_engine/tests/e2e/test_requirements_checklist_smoke.py -v

  CS01 — panel hidden on initial page load (unchanged)
  CS02 — panel title is Arabic, NOT raw "(residential / ...)"
  CS03 — Arabic section headings present after valid selection
  CS04 — unsupported purpose → soft message shown, panel not blank
  CS05 — core valuation UI elements still intact (unchanged)
  CS06 — "عمارة سكنية" maps to commercial; title contains "تجاري" not "سكني"
  CS07 — land selection: panel renders; "نهج التكلفة" NOT in section 4 methods
  CS08 — unsupported asset type → soft message shown
  CS09 — recommended_methods rendered as Arabic labels (not raw codes)
  CS10 — determinism: two reloads with same selection produce identical text
"""
from __future__ import annotations

import json

from playwright.sync_api import Page, Route, expect

_LS_KEY       = "es_auth"
_MOCK_SESSION = json.dumps({"token": "mock-token-cs", "user_id": "smoke-user", "is_admin": False})

_RESIDENTIAL_RESPONSE = {
    "status": "ok", "asset_type": "residential", "purpose": "market_value",
    "checklist_items": [
        {"name": "comparable",  "required": True,  "field_type": "float", "description": "Comparable value", "valid_values": []},
        {"name": "cost",        "required": True,  "field_type": "float", "description": "Cost value",       "valid_values": []},
        {"name": "income",      "required": True,  "field_type": "float", "description": "Income value",     "valid_values": []},
        {"name": "client_name", "required": False, "field_type": "str",   "description": "Client name",      "valid_values": []},
        {"name": "location",    "required": False, "field_type": "str",   "description": "Location",         "valid_values": []},
    ],
    "dynamic_fields": [],
    "recommended_methods": ["comparable", "cost", "income"],
    "notes": "",
}

_COMMERCIAL_RESPONSE = {
    "status": "ok", "asset_type": "commercial", "purpose": "market_value",
    "checklist_items": [
        {"name": "comparable",    "required": True,  "field_type": "float", "description": "Comparable", "valid_values": []},
        {"name": "cost",          "required": True,  "field_type": "float", "description": "Cost",       "valid_values": []},
        {"name": "income",        "required": True,  "field_type": "float", "description": "Income",     "valid_values": []},
        {"name": "client_name",   "required": False, "field_type": "str",   "description": "Client",     "valid_values": []},
        {"name": "annual_rent",   "required": False, "field_type": "float", "description": "Rent",       "valid_values": []},
        {"name": "cap_rate",      "required": False, "field_type": "float", "description": "Cap rate",   "valid_values": []},
    ],
    "dynamic_fields": [],
    "recommended_methods": ["comparable", "cost", "income"],
    "notes": "",
}

_LAND_RESPONSE = {
    "status": "ok", "asset_type": "land", "purpose": "market_value",
    "checklist_items": [
        {"name": "comparable",  "required": True,  "field_type": "float", "description": "Comparable", "valid_values": []},
        {"name": "income",      "required": True,  "field_type": "float", "description": "Income",     "valid_values": []},
        {"name": "client_name", "required": False, "field_type": "str",   "description": "Client",     "valid_values": []},
        {"name": "hbu",         "required": False, "field_type": "str",   "description": "HBU",
         "valid_values": ["residential", "commercial", "mixed_use"]},
    ],
    "dynamic_fields": [{"name": "hbu", "field_type": "str", "valid_values": ["residential", "commercial"]}],
    "recommended_methods": ["comparable", "income"],
    "notes": "Cost approach weight is 0 for unimproved land.",
}


def _inject_session(page: Page) -> None:
    page.evaluate(f"localStorage.setItem('{_LS_KEY}', {_MOCK_SESSION!r})")


def _mock_req(page: Page, payload: dict) -> None:
    def handle(route: Route) -> None:
        route.fulfill(status=200, content_type="application/json", body=json.dumps(payload))
    page.route("**/api/valuation/requirements**", handle)


# ── CS01 ──────────────────────────────────────────────────────────────────────

def test_CS01_panel_hidden_on_load(page: Page, live_server: str) -> None:
    """Requirements checklist panel is hidden on initial page load."""
    page.goto(live_server, wait_until="networkidle")
    panel = page.locator("#es-req-panel")
    expect(panel).to_be_attached()
    assert not panel.is_visible(), "#es-req-panel should be hidden on initial load"


# ── CS02 ──────────────────────────────────────────────────────────────────────

def test_CS02_panel_title_is_arabic_not_raw_keys(page: Page, live_server: str) -> None:
    """Panel title shows human-readable Arabic, NOT raw '(residential / market_value)'."""
    _mock_req(page, _RESIDENTIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
    title_text = page.locator("#es-req-title").inner_text()

    assert "(residential" not in title_text, (
        f"Title must not contain raw registry key '(residential'. Got: {title_text!r}"
    )
    assert "market_value" not in title_text, (
        f"Title must not contain raw registry key 'market_value'. Got: {title_text!r}"
    )
    assert "متطلبات تقييم" in title_text, (
        f"Title should start with Arabic 'متطلبات تقييم'. Got: {title_text!r}"
    )
    assert "وحدة سكنية" in title_text, (
        f"Title should contain Arabic asset label 'وحدة سكنية'. Got: {title_text!r}"
    )


# ── CS03 ──────────────────────────────────────────────────────────────────────

def test_CS03_arabic_section_headings_present(page: Page, live_server: str) -> None:
    """After a valid selection, Arabic section headings appear in the panel."""
    _mock_req(page, _RESIDENTIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    panel_text = page.locator("#es-req-panel").inner_text()
    assert "المستندات" in panel_text or "المتطلبات الأساسية" in panel_text, (
        f"Section 1 heading should be present. Panel text: {panel_text!r}"
    )
    assert "البيانات" in panel_text or "التقرير" in panel_text, (
        f"Section 2 heading should be present. Panel text: {panel_text!r}"
    )
    assert "المناهج" in panel_text, (
        f"Section 4 heading (المناهج) should be present. Panel text: {panel_text!r}"
    )


# ── CS04 ──────────────────────────────────────────────────────────────────────

def test_CS04_unsupported_purpose_shows_soft_message(page: Page, live_server: str) -> None:
    """Selecting an unmapped purpose shows the soft message; panel is visible not blank."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="rental_arbitration")   # not in PURPOSE_MAP

    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    soft_msg = page.locator("#es-req-soft-msg")
    expect(soft_msg).to_be_visible()
    assert "لا توجد" in soft_msg.inner_text(), (
        f"Soft message should contain 'لا توجد'. Got: {soft_msg.inner_text()!r}"
    )


# ── CS05 ──────────────────────────────────────────────────────────────────────

def test_CS05_existing_valuation_ui_intact(page: Page, live_server: str) -> None:
    """Core valuation UI elements are still present after Phase 8B/8C HTML injection."""
    page.goto(live_server, wait_until="networkidle")
    expect(page.locator("#generateBtn")).to_be_visible()
    expect(page.locator("#asset-type")).to_be_visible()
    expect(page.locator("#val-purpose")).to_be_visible()


# ── CS06 ──────────────────────────────────────────────────────────────────────

def test_CS06_emara_maps_to_commercial(page: Page, live_server: str) -> None:
    """'عمارة سكنية' maps to commercial registry; title contains 'تجاري' not 'سكني'."""
    _mock_req(page, _COMMERCIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
    title_text = page.locator("#es-req-title").inner_text()

    assert "تجاري" in title_text, (
        f"Title should contain 'تجاري' for commercial mapping. Got: {title_text!r}"
    )
    assert "سكني" not in title_text, (
        f"Title must NOT contain 'سكني' when mapped to commercial. Got: {title_text!r}"
    )


# ── CS07 ──────────────────────────────────────────────────────────────────────

def test_CS07_land_panel_renders_no_cost_in_methods(page: Page, live_server: str) -> None:
    """Land selection: panel renders and 'نهج التكلفة' absent from recommended methods."""
    _mock_req(page, _LAND_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="أرض فضاء")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    s4_text = page.locator("#es-req-s4").inner_text()
    assert "نهج التكلفة" not in s4_text, (
        f"'نهج التكلفة' must NOT appear in methods section for land. Section 4 text: {s4_text!r}"
    )
    assert "نهج المقارنة" in s4_text or "نهج الدخل" in s4_text, (
        f"Land methods (comparable/income) should be in section 4. Got: {s4_text!r}"
    )


# ── CS08 ──────────────────────────────────────────────────────────────────────

def test_CS08_unsupported_asset_type_shows_soft_message(page: Page, live_server: str) -> None:
    """Selecting an asset type not in ASSET_TYPE_MAP shows the soft message."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="مستشفى")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    soft_msg = page.locator("#es-req-soft-msg")
    expect(soft_msg).to_be_visible()
    assert "لا توجد" in soft_msg.inner_text(), (
        f"Soft message should contain 'لا توجد'. Got: {soft_msg.inner_text()!r}"
    )


# ── CS09 ──────────────────────────────────────────────────────────────────────

def test_CS09_methods_rendered_as_arabic_labels(page: Page, live_server: str) -> None:
    """recommended_methods are displayed in Arabic, not as raw English codes."""
    _mock_req(page, _RESIDENTIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    s4_text = page.locator("#es-req-s4").inner_text()
    # Arabic labels must be present
    assert "نهج المقارنة السوقية" in s4_text, (
        f"Arabic label for 'comparable' missing in methods section. Got: {s4_text!r}"
    )
    assert "نهج التكلفة" in s4_text, (
        f"Arabic label for 'cost' missing in methods section. Got: {s4_text!r}"
    )
    assert "نهج الدخل" in s4_text, (
        f"Arabic label for 'income' missing in methods section. Got: {s4_text!r}"
    )
    # Raw English codes must NOT appear in methods section
    for raw_code in ("comparable", "cost", "income"):
        assert raw_code not in s4_text, (
            f"Raw code '{raw_code}' must not appear in methods section. Got: {s4_text!r}"
        )


# ── CS10 ──────────────────────────────────────────────────────────────────────

def test_CS10_determinism_two_reloads(page: Page, live_server: str) -> None:
    """Two consecutive page loads with the same selection produce identical panel text."""
    _mock_req(page, _RESIDENTIAL_RESPONSE)

    def _load_and_get_text() -> str:
        page.goto(live_server, wait_until="networkidle")
        _inject_session(page)
        page.select_option("#asset-type", value="شقة سكنية")
        page.select_option("#val-purpose", value="fair_market_value")
        page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
        return page.locator("#es-req-panel").inner_text()

    text1 = _load_and_get_text()
    text2 = _load_and_get_text()

    assert text1 == text2, (
        "Two consecutive reloads with same selection produced different panel text.\n"
        f"Run 1: {text1!r}\nRun 2: {text2!r}"
    )
