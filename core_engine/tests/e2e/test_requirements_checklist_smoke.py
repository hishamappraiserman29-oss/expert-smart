"""
E2E smoke tests for Phase 8B/8C/8C.1/8D/8E — Frontend Requirements Checklist Panel.

Requires a running bridge_api server (managed by conftest.py) and Playwright.

    pytest core_engine/tests/e2e/test_requirements_checklist_smoke.py -v

  CS01 — panel hidden on initial page load
  CS02 — panel title is Arabic; sections A and B have descriptive paragraphs
  CS03 — Arabic section headings present; method codes and heading absent from entire panel
  CS04 — unsupported purpose → improved soft message shown
  CS05 — core valuation UI elements still intact
  CS06 — "تجاري" (single commercial) calls API; title contains "تجاري", not composite
  CS07 — land single mode: no method names appear anywhere in panel
  CS08 — unsupported asset type → improved soft message shown
  CS09 — section D is empty; no Arabic or raw method labels in single-mode panel
  CS10 — determinism: two reloads with same selection produce identical text
  CS11 — header nav link reads "تقييم أصل مركّب" with tooltip attribute
  CS12 — sections A/B/C each have their descriptive paragraph
  CS13 — section D is empty after Phase 8E methods removal
  CS14 — residential single mode: composite link absent; title does not say "مركّب"
  CS15 — land single mode: composite link absent; title does not say "مركّب"
  CS16 — "عمارة سكنية" shows composite guidance panel; title contains "أصل مركّب"
  CS17 — composite panel has redirect link to composite_valuation.html
  CS18 — composite panel shows grouped checklist sections (land/building/income)
  CS19 — no raw registry codes in composite panel
  CS20 — "عمارة سكنية" does not call GET /api/valuation/requirements
  CS21 — residential single panel: section D empty, no methods section
  CS22 — residential single panel text: "مناهج التقييم المناسبة" absent
  CS23 — composite panel text: "مناهج التقييم المناسبة" absent
  CS24 — "تجاري" calls GET /api/valuation/requirements (not treated as composite)
  CS25 — "مصنع" calls GET /api/valuation/requirements (not treated as composite)
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
    """Panel title shows human-readable Arabic; sections A and B have descriptive paragraphs."""
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


# ── CS03 ──────────────────────────────────────────────────────────────────────

def test_CS03_section_headings_present_method_codes_absent_from_panel(page: Page, live_server: str) -> None:
    """Sections A/B headings present; raw method codes and methods heading absent from entire panel."""
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
    # Phase 8E: methods section removed from user-facing panel
    assert "مناهج التقييم" not in panel_text, (
        f"'مناهج التقييم' must NOT appear in single-mode panel after Phase 8E. Panel text: {panel_text!r}"
    )

    # Raw English method codes must NOT appear anywhere in the panel
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

def test_CS06_tijari_maps_to_commercial_single_mode(page: Page, live_server: str) -> None:
    """'تجاري' (commercial building) uses single-property mode; title contains 'تجاري'."""
    _mock_req(page, _COMMERCIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    # 'تجاري' maps to registry code 'commercial' but is NOT in _COMPOSITE_CODES,
    # so it must use the single-property API path, not the composite panel.
    page.select_option("#asset-type", value="تجاري")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
    title_text = page.locator("#es-req-title").inner_text()

    assert "تجاري" in title_text, (
        f"Title should contain 'تجاري' for commercial single-mode mapping. Got: {title_text!r}"
    )
    # Must NOT show composite panel for a single commercial building
    assert "أصل مركّب" not in title_text and "أصل مركب" not in title_text, (
        f"Title must NOT contain 'أصل مركّب' for single-mode 'تجاري'. Got: {title_text!r}"
    )


# ── CS07 ──────────────────────────────────────────────────────────────────────

def test_CS07_land_panel_renders_no_methods_anywhere(page: Page, live_server: str) -> None:
    """Land (single mode): no method names anywhere in panel after Phase 8E methods removal."""
    _mock_req(page, _LAND_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="أرض فضاء")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    panel_text = page.locator("#es-req-panel").inner_text()
    s4_text = page.locator("#es-req-s4").inner_text()

    # Section D must be empty — methods are internal
    assert s4_text.strip() == "", (
        f"Section D must be empty for land (single mode). Got: {s4_text!r}"
    )
    # The methods section heading must not appear (field labels in s1 may contain 'نهج' as part of the field name)
    assert "مناهج التقييم المناسبة" not in panel_text, (
        f"'مناهج التقييم المناسبة' heading must NOT appear in single-mode panel. Got: {panel_text!r}"
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

def test_CS09_section_D_empty_no_method_labels(page: Page, live_server: str) -> None:
    """Section D is empty — methods removed from user-facing panel; no Arabic or raw method labels."""
    _mock_req(page, _RESIDENTIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    s4_text = page.locator("#es-req-s4").inner_text().strip()
    assert s4_text == "", (
        f"Section D must be empty after Phase 8E methods removal. Got: {s4_text!r}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    # 'مناهج التقييم المناسبة' is the section heading — must be absent
    # (field labels in s1 may include 'نهج' as part of their Arabic name)
    assert "مناهج التقييم المناسبة" not in panel_text, (
        f"'مناهج التقييم المناسبة' heading must NOT appear in single-mode panel. Got: {panel_text!r}"
    )
    # Raw English method codes must not appear anywhere
    for raw_code in ("comparable", "cost", "income"):
        assert raw_code not in panel_text, (
            f"Raw method code '{raw_code}' must not appear in single-mode panel. Got: {panel_text!r}"
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

def test_CS12_three_sections_have_descriptions(page: Page, live_server: str) -> None:
    """Sections A/B/C each render with their explanatory Arabic description paragraph."""
    _mock_req(page, _LAND_RESPONSE)   # land gives content in all 3 data sections
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="أرض فضاء")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    s1_text = page.locator("#es-req-s1").inner_text()
    s2_text = page.locator("#es-req-s2").inner_text()
    s3_text = page.locator("#es-req-s3").inner_text()

    assert "ضرورية لبناء التقرير" in s1_text, (
        f"Section A description missing. Got: {s1_text!r}"
    )
    assert "التحقّق من الملكية" in s2_text, (
        f"Section B description missing. Got: {s2_text!r}"
    )
    assert "ترفع جودة التقرير" in s3_text, (
        f"Section C description missing. Got: {s3_text!r}"
    )


# ── CS13 ──────────────────────────────────────────────────────────────────────

def test_CS13_section_D_empty_after_methods_removal(page: Page, live_server: str) -> None:
    """Section D is empty after Phase 8E — methods are internal to engine, not user-facing."""
    _mock_req(page, _RESIDENTIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    s4 = page.locator("#es-req-s4")
    assert s4.get_attribute("data-es-section") != "methods", (
        "Section D must NOT carry data-es-section='methods' — methods removed from user panel"
    )
    s4_text = s4.inner_text().strip()
    assert s4_text == "", (
        f"Section D must be empty after methods removal. Got: {s4_text!r}"
    )


# ── CS14 ──────────────────────────────────────────────────────────────────────

def test_CS14_residential_single_mode_no_composite_banner(page: Page, live_server: str) -> None:
    """Residential unit (single mode): composite link absent; title does not say 'مركّب'."""
    _mock_req(page, _RESIDENTIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    title_text = page.locator("#es-req-title").inner_text()
    assert "مركّب" not in title_text and "مركب" not in title_text, (
        f"Title must not contain 'مركّب' for single mode. Got: {title_text!r}"
    )
    composite_link = page.locator("#es-req-composite-link")
    assert composite_link.count() == 0 or not composite_link.is_visible(), (
        "Composite link must not appear for residential (single mode)"
    )


# ── CS15 ──────────────────────────────────────────────────────────────────────

def test_CS15_land_single_mode_no_composite_banner(page: Page, live_server: str) -> None:
    """Land (single mode): composite link absent; title does not say 'مركّب'."""
    _mock_req(page, _LAND_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="أرض فضاء")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    title_text = page.locator("#es-req-title").inner_text()
    assert "مركّب" not in title_text and "مركب" not in title_text, (
        f"Title must not contain 'مركّب' for land (single mode). Got: {title_text!r}"
    )
    composite_link = page.locator("#es-req-composite-link")
    assert composite_link.count() == 0 or not composite_link.is_visible(), (
        "Composite link must not appear for land (single mode)"
    )


# ── CS16 ──────────────────────────────────────────────────────────────────────

def test_CS16_building_shows_composite_guidance_panel(page: Page, live_server: str) -> None:
    """'عمارة سكنية' (composite mode): guidance panel shown; title contains 'أصل مركّب'."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    title_text = page.locator("#es-req-title").inner_text()
    assert "أصل مركّب" in title_text or "أصل مركب" in title_text, (
        f"Title must contain 'أصل مركّب' for composite mode. Got: {title_text!r}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "سيتم التعامل معه" in panel_text or "يتكوّن" in panel_text, (
        f"Composite system-decision explanation must appear in panel. Got: {panel_text!r}"
    )


# ── CS17 ──────────────────────────────────────────────────────────────────────

def test_CS17_composite_panel_has_redirect_link(page: Page, live_server: str) -> None:
    """Composite guidance panel contains a visible link to /composite_valuation.html."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    link = page.locator("#es-req-composite-link")
    expect(link).to_be_visible()
    href = link.get_attribute("href") or ""
    assert "composite_valuation.html" in href, (
        f"Composite link must point to composite_valuation.html. Got: {href!r}"
    )
    link_text = link.inner_text().strip()
    assert "فتح نموذج التقييم المركب" in link_text, (
        f"Composite link label must say 'فتح نموذج التقييم المركب'. Got: {link_text!r}"
    )


# ── CS18 ──────────────────────────────────────────────────────────────────────

def test_CS18_composite_panel_shows_grouped_checklist_sections(page: Page, live_server: str) -> None:
    """Composite panel shows building-specific grouped sections for all required data types."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    panel_text = page.locator("#es-req-panel").inner_text()
    assert "بيانات الأرض" in panel_text, (
        f"Composite panel must contain 'بيانات الأرض'. Got: {panel_text!r}"
    )
    assert "بيانات المبنى" in panel_text, (
        f"Composite panel must contain 'بيانات المبنى'. Got: {panel_text!r}"
    )
    assert "بيانات الدخل" in panel_text, (
        f"Composite panel must contain 'بيانات الدخل'. Got: {panel_text!r}"
    )


# ── CS19 ──────────────────────────────────────────────────────────────────────

def test_CS19_no_raw_registry_codes_in_composite_panel(page: Page, live_server: str) -> None:
    """No raw English registry codes appear anywhere in the composite guidance panel."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    panel_text = page.locator("#es-req-panel").inner_text()
    for raw_code in ("commercial", "residential", "land", "market_value",
                     "comparable", "cost", "income"):
        assert raw_code not in panel_text, (
            f"Raw code '{raw_code}' must not appear in composite panel. Got: {panel_text!r}"
        )


# ── CS20 ──────────────────────────────────────────────────────────────────────

def test_CS20_composite_does_not_call_requirements_api(page: Page, live_server: str) -> None:
    """Composite selection does not trigger GET /api/valuation/requirements."""
    api_calls: list[str] = []

    def intercept(route: Route) -> None:
        api_calls.append(route.request.url)
        route.continue_()

    page.route("**/api/valuation/requirements**", intercept)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    assert len(api_calls) == 0, (
        f"GET /api/valuation/requirements must NOT be called for composite assets. "
        f"Called {len(api_calls)} time(s): {api_calls}"
    )


# ── CS21 ──────────────────────────────────────────────────────────────────────

def test_CS21_residential_single_panel_no_methods_section(page: Page, live_server: str) -> None:
    """Residential single panel: section D empty, data-es-section='methods' absent."""
    _mock_req(page, _RESIDENTIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    s4 = page.locator("#es-req-s4")
    assert s4.get_attribute("data-es-section") != "methods", (
        "Section D must NOT carry data-es-section='methods' after Phase 8E"
    )
    assert s4.inner_text().strip() == "", (
        f"Section D must be empty for residential single mode. Got: {s4.inner_text()!r}"
    )


# ── CS22 ──────────────────────────────────────────────────────────────────────

def test_CS22_residential_single_panel_no_methods_heading(page: Page, live_server: str) -> None:
    """Residential single panel text does not contain 'مناهج التقييم المناسبة'."""
    _mock_req(page, _RESIDENTIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    panel_text = page.locator("#es-req-panel").inner_text()
    assert "مناهج التقييم المناسبة" not in panel_text, (
        f"'مناهج التقييم المناسبة' must NOT appear in residential single panel. "
        f"Got: {panel_text!r}"
    )


# ── CS23 ──────────────────────────────────────────────────────────────────────

def test_CS23_composite_panel_no_methods_heading(page: Page, live_server: str) -> None:
    """Composite panel text does not contain 'مناهج التقييم المناسبة'."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    panel_text = page.locator("#es-req-panel").inner_text()
    assert "مناهج التقييم المناسبة" not in panel_text, (
        f"'مناهج التقييم المناسبة' must NOT appear in composite panel. "
        f"Got: {panel_text!r}"
    )


# ── CS24 ──────────────────────────────────────────────────────────────────────

def test_CS24_tijari_not_composite_calls_api(page: Page, live_server: str) -> None:
    """'تجاري' is NOT in _COMPOSITE_CODES; must call GET /api/valuation/requirements."""
    api_calls: list[str] = []

    def intercept(route: Route) -> None:
        api_calls.append(route.request.url)
        route.fulfill(status=200, content_type="application/json",
                      body=__import__("json").dumps(_COMMERCIAL_RESPONSE))

    page.route("**/api/valuation/requirements**", intercept)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="تجاري")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    assert len(api_calls) >= 1, (
        f"GET /api/valuation/requirements MUST be called for 'تجاري' (single commercial). "
        f"Got {len(api_calls)} call(s)."
    )


# ── CS25 ──────────────────────────────────────────────────────────────────────

def test_CS25_masna_not_composite_calls_api(page: Page, live_server: str) -> None:
    """'مصنع' is NOT in _COMPOSITE_CODES; must call GET /api/valuation/requirements."""
    api_calls: list[str] = []

    def intercept(route: Route) -> None:
        api_calls.append(route.request.url)
        route.fulfill(status=200, content_type="application/json",
                      body=__import__("json").dumps(_COMMERCIAL_RESPONSE))

    page.route("**/api/valuation/requirements**", intercept)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="مصنع")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    assert len(api_calls) >= 1, (
        f"GET /api/valuation/requirements MUST be called for 'مصنع' (single industrial). "
        f"Got {len(api_calls)} call(s)."
    )
