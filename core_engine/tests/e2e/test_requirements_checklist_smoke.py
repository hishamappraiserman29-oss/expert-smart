"""
E2E smoke tests for Phase 8B/8C/8C.1 — Frontend Requirements Checklist Panel.

Requires a running bridge_api server (managed by conftest.py) and Playwright.

    pytest core_engine/tests/e2e/test_requirements_checklist_smoke.py -v

  CS01 — panel hidden on initial page load (unchanged)
  CS02 — panel title is Arabic; section descriptive paragraphs present
  CS03 — Arabic section headings present; method codes absent from A and B
  CS04 — unsupported purpose → improved soft message shown
  CS05 — core valuation UI elements still intact (unchanged)
  CS06 — "عمارة سكنية" maps to commercial; title contains "تجاري" not "سكني"
  CS07 — land selection: "نهج التكلفة" NOT in section D methods or section A
  CS08 — unsupported asset type → improved soft message shown
  CS09 — recommended_methods rendered as Arabic labels in section D only
  CS10 — determinism: two reloads with same selection produce identical text
  CS11 — header nav link reads "تقييم أصل مركّب" with tooltip attribute
  CS12 — each of the four sections (A/B/C/D) has its descriptive paragraph
  CS13 — section D carries data-es-section='methods' and background style
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

_SOFT_MSG_FRAGMENT = "يمكنك متابعة التقييم"


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

def test_CS02_panel_title_arabic_and_section_descriptions_present(page: Page, live_server: str) -> None:
    """Panel title shows human-readable Arabic; sections A, B, D have descriptive paragraphs."""
    _mock_req(page, _RESIDENTIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
    title_text = page.locator("#es-req-title").inner_text()

    assert "(residential" not in title_text, (
        f"Title must not contain raw key '(residential'. Got: {title_text!r}"
    )
    assert "market_value" not in title_text, (
        f"Title must not contain raw key 'market_value'. Got: {title_text!r}"
    )
    assert "متطلبات تقييم" in title_text, (
        f"Title should contain 'متطلبات تقييم'. Got: {title_text!r}"
    )
    assert "وحدة سكنية" in title_text, (
        f"Title should contain 'وحدة سكنية'. Got: {title_text!r}"
    )

    # Section A description
    s1_text = page.locator("#es-req-s1").inner_text()
    assert "ضرورية لبناء التقرير" in s1_text, (
        f"Section A description missing. Got: {s1_text!r}"
    )
    # Section B description (client_name/location go to B via FIELD_GROUP='report')
    s2_text = page.locator("#es-req-s2").inner_text()
    assert "التحقّق من الملكية" in s2_text, (
        f"Section B description missing. Got: {s2_text!r}"
    )
    # Section D description
    s4_text = page.locator("#es-req-s4").inner_text()
    assert "ليست بيانات يطلبها النظام" in s4_text, (
        f"Section D description missing. Got: {s4_text!r}"
    )


# ── CS03 ──────────────────────────────────────────────────────────────────────

def test_CS03_section_headings_present_method_codes_absent_from_A_B(page: Page, live_server: str) -> None:
    """Arabic section headings present; raw method codes absent from sections A and B."""
    _mock_req(page, _RESIDENTIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    panel_text = page.locator("#es-req-panel").inner_text()
    assert "البيانات الأساسية" in panel_text or "المتطلبات الأساسية" in panel_text, (
        f"Section A heading missing. Panel text: {panel_text!r}"
    )
    assert "المستندات" in panel_text, (
        f"Section B heading missing. Panel text: {panel_text!r}"
    )
    assert "مناهج التقييم" in panel_text, (
        f"Section D heading missing. Panel text: {panel_text!r}"
    )

    # Raw English method codes must NOT appear in section A or B
    s1_text = page.locator("#es-req-s1").inner_text()
    s2_text = page.locator("#es-req-s2").inner_text()
    for raw_code in ("comparable", "cost", "income", "residual_land_value", "investment_analysis"):
        assert raw_code not in s1_text, (
            f"Raw method code '{raw_code}' must not appear in section A. Got: {s1_text!r}"
        )
        assert raw_code not in s2_text, (
            f"Raw method code '{raw_code}' must not appear in section B. Got: {s2_text!r}"
        )


# ── CS04 ──────────────────────────────────────────────────────────────────────

def test_CS04_unsupported_purpose_shows_improved_soft_message(page: Page, live_server: str) -> None:
    """Selecting an unmapped purpose shows the improved soft message with continuation guidance."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="rental_arbitration")   # not in PURPOSE_MAP

    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    soft_msg = page.locator("#es-req-soft-msg")
    expect(soft_msg).to_be_visible()
    msg_text = soft_msg.inner_text()
    assert "لا توجد" in msg_text, (
        f"Soft message should contain 'لا توجد'. Got: {msg_text!r}"
    )
    assert _SOFT_MSG_FRAGMENT in msg_text, (
        f"Soft message should contain continuation guidance '{_SOFT_MSG_FRAGMENT}'. Got: {msg_text!r}"
    )


# ── CS05 ──────────────────────────────────────────────────────────────────────

def test_CS05_existing_valuation_ui_intact(page: Page, live_server: str) -> None:
    """Core valuation UI elements are still present after Phase 8B/8C/8C.1 HTML injection."""
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

def test_CS07_land_panel_renders_no_cost_anywhere(page: Page, live_server: str) -> None:
    """Land: 'نهج التكلفة' absent from section D methods and from section A."""
    _mock_req(page, _LAND_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="أرض فضاء")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    s1_text = page.locator("#es-req-s1").inner_text()
    s4_text = page.locator("#es-req-s4").inner_text()

    assert "نهج التكلفة" not in s4_text, (
        f"'نهج التكلفة' must NOT appear in section D for land. Got: {s4_text!r}"
    )
    assert "نهج التكلفة" not in s1_text, (
        f"'نهج التكلفة' must NOT appear in section A for land. Got: {s1_text!r}"
    )
    assert "نهج المقارنة" in s4_text or "نهج الدخل" in s4_text, (
        f"Land methods (comparable/income) should appear in section D. Got: {s4_text!r}"
    )


# ── CS08 ──────────────────────────────────────────────────────────────────────

def test_CS08_unsupported_asset_type_shows_improved_soft_message(page: Page, live_server: str) -> None:
    """Asset type not in ASSET_TYPE_MAP shows improved soft message with continuation guidance."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="مستشفى")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    soft_msg = page.locator("#es-req-soft-msg")
    expect(soft_msg).to_be_visible()
    msg_text = soft_msg.inner_text()
    assert "لا توجد" in msg_text, (
        f"Soft message should contain 'لا توجد'. Got: {msg_text!r}"
    )
    assert _SOFT_MSG_FRAGMENT in msg_text, (
        f"Soft message should contain continuation guidance '{_SOFT_MSG_FRAGMENT}'. Got: {msg_text!r}"
    )


# ── CS09 ──────────────────────────────────────────────────────────────────────

def test_CS09_methods_rendered_as_arabic_labels_in_section_D(page: Page, live_server: str) -> None:
    """recommended_methods display as Arabic labels in section D; no raw English codes in D."""
    _mock_req(page, _RESIDENTIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    s4_text = page.locator("#es-req-s4").inner_text()
    assert "نهج المقارنة السوقية" in s4_text, (
        f"Arabic label for 'comparable' missing in section D. Got: {s4_text!r}"
    )
    assert "نهج التكلفة" in s4_text, (
        f"Arabic label for 'cost' missing in section D. Got: {s4_text!r}"
    )
    assert "نهج الدخل" in s4_text, (
        f"Arabic label for 'income' missing in section D. Got: {s4_text!r}"
    )
    for raw_code in ("comparable", "cost", "income"):
        assert raw_code not in s4_text, (
            f"Raw code '{raw_code}' must not appear in section D. Got: {s4_text!r}"
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


# ── CS11 ──────────────────────────────────────────────────────────────────────

def test_CS11_nav_link_renamed_with_tooltip(page: Page, live_server: str) -> None:
    """Header nav link reads 'تقييم أصل مركّب'; title attribute contains tooltip."""
    page.goto(live_server, wait_until="networkidle")

    link = page.locator("#cv-nav-link")
    expect(link).to_be_visible()

    link_text = link.inner_text().strip()
    assert link_text == "تقييم أصل مركّب", (
        f"Nav link text must be 'تقييم أصل مركّب'. Got: {link_text!r}"
    )
    title_attr = link.get_attribute("title") or ""
    assert "استخدمه عند تقييم" in title_attr, (
        f"Nav title must contain 'استخدمه عند تقييم'. Got: {title_attr!r}"
    )
    assert "أرض + مبنى" in title_attr, (
        f"Nav title must mention component example 'أرض + مبنى'. Got: {title_attr!r}"
    )


# ── CS12 ──────────────────────────────────────────────────────────────────────

def test_CS12_four_sections_have_descriptions(page: Page, live_server: str) -> None:
    """Each of the four sections (A/B/C/D) renders with its explanatory Arabic description."""
    _mock_req(page, _LAND_RESPONSE)   # land gives content in all 4 sections
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="أرض فضاء")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    s1_text = page.locator("#es-req-s1").inner_text()
    s2_text = page.locator("#es-req-s2").inner_text()
    s3_text = page.locator("#es-req-s3").inner_text()
    s4_text = page.locator("#es-req-s4").inner_text()

    assert "ضرورية لبناء التقرير" in s1_text, (
        f"Section A description missing. Got: {s1_text!r}"
    )
    assert "التحقّق من الملكية" in s2_text, (
        f"Section B description missing. Got: {s2_text!r}"
    )
    assert "ترفع جودة التقرير" in s3_text, (
        f"Section C description missing. Got: {s3_text!r}"
    )
    assert "ليست بيانات يطلبها النظام" in s4_text, (
        f"Section D description missing. Got: {s4_text!r}"
    )


# ── CS13 ──────────────────────────────────────────────────────────────────────

def test_CS13_section_D_visually_distinct(page: Page, live_server: str) -> None:
    """Section D has data-es-section='methods' marker and background style applied."""
    _mock_req(page, _RESIDENTIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-s4").wait_for(state="visible", timeout=6_000)

    s4 = page.locator("#es-req-s4")
    assert s4.get_attribute("data-es-section") == "methods", (
        "Section D must carry data-es-section='methods' for visual-distinction verification"
    )
    style = s4.get_attribute("style") or ""
    assert "background" in style, (
        f"Section D must have a background style to be visually distinct from A/B. Style: {style!r}"
    )
