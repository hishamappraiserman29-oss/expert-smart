"""
E2E smoke tests for Phase 8B/8C/8C.1/8D/8E/8G/8H.1/8H.2B/8H.2D/8H.2E/8I — Frontend Requirements Checklist Panel.

Requires a running bridge_api server (managed by conftest.py) and Playwright.

    pytest core_engine/tests/e2e/test_requirements_checklist_smoke.py -v

  CS01 — panel hidden on initial page load
  CS02 — panel title is Arabic; sections A and B have descriptive paragraphs
  CS03 — Arabic section headings present; method codes and heading absent from entire panel
  CS04 — unsupported purpose → improved soft message shown
  CS05 — core valuation UI elements still intact
  CS06 — "تجاري" (API-driven building_mixed) calls API; title contains "تجاري", not composite
  CS07 — land single mode: no method names appear anywhere in panel
  CS08 — null-mapped asset type (أصول معنوية) shows soft message with continuation guidance
  CS09 — section D is empty; no Arabic or raw method labels in single-mode panel
  CS10 — determinism: two reloads with same selection produce identical text
  CS11 — (8H.1) always-visible #cv-nav-link header link is absent; composite access is contextual only
  CS12 — sections A/B/C each have their descriptive paragraph
  CS13 — section D is empty after Phase 8E methods removal
  CS14 — residential single mode: composite link absent; title does not say "مركّب"
  CS15 — land single mode: composite link absent; title does not say "مركّب"
  CS16 — "عمارة سكنية" shows static building_full panel; title is "متطلبات تقييم عمارة سكنية"
  CS17 — building_full panel has redirect link to composite_valuation.html
  CS18 — building_full panel shows grouped checklist sections (land/building/income)
  CS19 — no raw registry codes in building_full panel
  CS20 — "عمارة سكنية" does not call GET /api/valuation/requirements
  CS21 — residential single panel: section D empty, no methods section
  CS22 — residential single panel text: "مناهج التقييم المناسبة" absent
  CS23 — building_full panel text: "مناهج التقييم المناسبة" absent
  CS24 — "تجاري" calls GET /api/valuation/requirements (API-driven building_mixed profile)
  CS25 — "مصنع" is placeholder profile; must NOT call GET /api/valuation/requirements
  CS26 — "شقة سكنية" calls GET /api/valuation/requirements (residential_unit API profile)
  CS27 — "أرض فضاء" calls GET /api/valuation/requirements (land API profile)
  CS28 — "عمارة سكنية" (Phase 8G framing): ZERO API calls, static path confirmed
  CS29 — "عمارة سكنية" building_full panel contains floor-use rows (الدور الأرضي, الأدوار المتكررة)
  CS30 — "فندق" → placeholder panel; ZERO API calls; title contains "فندق"; deferred notice shown
  CS31 — "مصنع" → placeholder panel; ZERO API calls; deferred notice shown
  CS32 — "مستشفى" → placeholder panel; ZERO API calls; deferred notice shown
  CS33 — all placeholder asset types contain "قيد التطوير" notice
  CS34 — placeholder panels contain NO ✦ bullet and NO "(مطلوب)" tag
  CS35 — no raw English profile codes appear in placeholder panel text
  CS36 — two consecutive renders of "عمارة سكنية" produce identical innerText
  CS37 — (8H.1) placeholder panel (فندق) has contextual composite CTA pointing to composite_valuation.html
  CS38 — (8H.1) building_full panel s4 is empty; no method label text present
  CS39 — (8H.1) all placeholder types show contextual composite CTA; residential/land do not

  CS40 — (8H.2B) residential panel renders real form controls
  CS41 — (8H.2B) area_sqm renders as number input
  CS42 — (8H.2B) floor_number renders as number input
  CS43 — (8H.2B) finishing_level renders as select with ≥4 options
  CS44 — (8H.2B) legal_status renders as select
  CS45 — (8H.2B) document fields render as checkboxes with Arabic labels
  CS46 — (8H.2B) land panel renders real form controls
  CS47 — (8H.2B) land_area_sqm renders as number input
  CS48 — (8H.2B) frontage_m renders as number input
  CS49 — (8H.2B) zoning_type renders as select with ≥6 options
  CS50 — (8H.2B) utilities_available renders as checkbox group
  CS51 — (8H.2B) buildability_status renders as select
  CS52 — (8H.2B) land document fields render as checkboxes
  CS53 — (8H.2B) engine fields not rendered as form controls
  CS54 — (8H.2B) field label comes from label_ar (DRY)
  CS55 — (8H.2B) no JS console errors on render

  CS56 — (8H.2D) select first option is 'اختر ...' placeholder
  CS57 — (8H.2D) default option text derived from label_ar
  CS58 — (8H.2D) yes/no fields show نعم/لا
  CS59 — (8H.2D) number inputs carry non-empty placeholder
  CS60 — (8H.2D) all 3 section headings visible in residential panel
  CS61 — (8H.2D) utilities_available shows Arabic chip labels
  CS62 — (8H.2D) utilities_available shows no raw backend codes

  CS63 — (8H.2E) finishing_level options display Arabic translations
  CS64 — (8H.2E) legal_status options display Arabic translations
  CS65 — (8H.2E) parking_available select shows نعم/لا
  CS66 — (8H.2E) zoning_type options display Arabic translations
  CS67 — (8H.2E) buildability_status options display Arabic translations
  CS68 — (8H.2E) hbu select options display Arabic translations
  CS69 — (8H.2E) no raw enum codes in residential panel visible text
  CS70 — (8H.2E) no raw enum codes in land panel visible text

  CS71 — (8I) #es-profile-explainer hidden on initial page load
  CS72 — (8I) selecting residential → explainer visible, badge contains مدعوم
  CS73 — (8I) selecting عمارة سكنية (building_full) → badge contains نموذج مركّب
  CS74 — (8I) selecting فندق (placeholder) → badge contains قيد التطوير
  CS75 — (8I) selecting unsupported type → badge contains غير مدعوم
  CS76 — (8I) selection change فندق → شقة سكنية updates explainer from قيد التطوير to مدعوم
  CS77 — (8I) <optgroup> elements present inside #asset-type
  CS78 — (8I) all 16 original option values still present in #asset-type unchanged
"""
from __future__ import annotations

import json

from playwright.sync_api import Page, Route, expect

_LS_KEY       = "es_auth"
_MOCK_SESSION = json.dumps({"token": "mock-token-cs", "user_id": "smoke-user", "is_admin": False})

# Phase 8H.2C enriched mock responses — carry role/label_ar/group/ui_required
# so the Phase 8H.2B renderer can classify and build real controls.
# Engine fields use role="engine_value" and must NOT be rendered.

def _ei(name, ft, desc, vv=None, *, role="engine_value", label_ar="", group="", ui_req=False):
    """Shorthand: engine / non-user field factory."""
    return {"name": name, "required": True, "field_type": ft, "description": desc,
            "valid_values": vv or [], "role": role, "label_ar": label_ar,
            "group": group, "ui_required": ui_req}

def _ui(name, ft, desc, vv=None, *, label_ar, group="", ui_req=False):
    """Shorthand: user_input field factory."""
    return {"name": name, "required": False, "field_type": ft, "description": desc,
            "valid_values": vv or [], "role": "user_input", "label_ar": label_ar,
            "group": group, "ui_required": ui_req}

def _doc(name, label_ar):
    """Shorthand: document (bool) field factory."""
    return {"name": name, "required": False, "field_type": "bool", "description": label_ar,
            "valid_values": [], "role": "user_input", "label_ar": label_ar,
            "group": "document", "ui_required": False}


_RESIDENTIAL_RESPONSE = {
    "status": "ok", "asset_type": "residential", "purpose": "market_value",
    "checklist_items": [
        # engine_value — must NOT render
        _ei("comparable", "float", "Comparable-sales approach value (EGP)"),
        _ei("cost",       "float", "Cost-approach value (EGP)"),
        _ei("income",     "float", "Income-capitalization approach value (EGP)"),
        _ei("comparables","list",  "List of comparable sales dicts"),
        # Section A — ui_required=True
        _ui("area_sqm",       "float", "Floor area (sqm)",                  label_ar="المساحة (م²)",        ui_req=True),
        _ui("floor_number",   "int",   "Floor number within the building",   label_ar="رقم الطابق",           ui_req=True),
        _ui("rooms_count",    "int",   "Number of rooms",                    label_ar="عدد الغرف",            ui_req=True),
        _ui("finishing_level","str",   "Finishing level of the unit",
            ["shell", "semi_finished", "standard_finished", "luxury_finished"],
            label_ar="مستوى التشطيب", ui_req=True),
        _ui("legal_status",   "str",   "Legal / title status",
            ["registered_title", "preliminary_contract", "allocation", "unknown"],
            label_ar="الحالة القانونية", ui_req=True),
        # Section B — ui_required=False, non-document
        _ui("client_name",    "str",   "Client or borrower name",            label_ar="اسم العميل"),
        _ui("location",       "str",   "Property address or location",       label_ar="الموقع"),
        _ui("elevator_available","str","Elevator available",
            ["yes", "no"],                                                    label_ar="يوجد مصعد"),
        _ui("parking_available","str", "Parking available",
            ["yes", "no"],                                                    label_ar="يوجد موقف سيارة"),
        # Section C — documents
        _doc("ownership_document",            "سند الملكية"),
        _doc("recent_photos",                 "صور حديثة للعقار"),
        _doc("site_croquis_or_location",      "كروكي الموقع"),
        _doc("nearby_sale_comparables_if_available", "مقارنات بيع قريبة (إن وجدت)"),
    ],
    "dynamic_fields": [],
    "recommended_methods": ["comparable", "cost", "income"],
    "notes": "",
}

_COMMERCIAL_RESPONSE = {
    "status": "ok", "asset_type": "commercial", "purpose": "market_value",
    "checklist_items": [
        _ei("comparable", "float", "Comparable value"),
        _ei("cost",       "float", "Cost value"),
        _ei("income",     "float", "Income value"),
        _ui("client_name",  "str",   "Client name",        label_ar="اسم العميل"),
        _ui("annual_rent",  "float", "Annual rental income", label_ar="الإيجار السنوي (ج.م.)"),
        _ui("cap_rate",     "float", "Capitalization rate",  label_ar="معدل الرسملة"),
    ],
    "dynamic_fields": [],
    "recommended_methods": ["comparable", "cost", "income"],
    "notes": "",
}

_LAND_RESPONSE = {
    "status": "ok", "asset_type": "land", "purpose": "market_value",
    "checklist_items": [
        # engine_value — must NOT render
        _ei("comparable",  "float", "Comparable-sales approach value (EGP)"),
        _ei("income",      "float", "Income-capitalization approach value (EGP)"),
        _ei("comparables", "list",  "List of comparable sales dicts"),
        # Section A — ui_required=True
        _ui("land_area_sqm",    "float", "Land area (sqm)",           label_ar="مساحة الأرض (م²)",        ui_req=True),
        _ui("frontage_m",       "float", "Street frontage width (m)", label_ar="واجهة الأرض (م)",          ui_req=True),
        _ui("street_width_m",   "float", "Adjacent street width (m)", label_ar="عرض الشارع (م)",           ui_req=True),
        _ui("zoning_type",      "str",   "Zoning classification",
            ["residential", "commercial", "administrative", "mixed_use", "agricultural", "unknown"],
            label_ar="نوع التخطيط العمراني", ui_req=True),
        _ui("buildability_status","str", "Buildability and planning constraints",
            ["buildable", "needs_verification", "planning_restrictions", "unknown"],
            label_ar="حالة قابلية البناء", ui_req=True),
        _ui("legal_status",     "str",   "Legal / title status",
            ["registered_title", "preliminary_contract", "allocation", "unknown"],
            label_ar="الحالة القانونية", ui_req=True),
        # Section B — ui_required=False, non-document
        _ui("client_name",      "str",   "Client name",                label_ar="اسم العميل"),
        _ui("hbu",              "str",   "Highest-and-best-use",
            ["residential", "commercial", "mixed_use", "industrial", "agricultural", "speculative"],
            label_ar="أفضل استخدام (HBU)"),
        _ui("utilities_available","list","Available utilities on the plot",
            ["electricity", "water", "sewage", "gas", "paved_road"],
            label_ar="الخدمات المتاحة"),
        # Section C — documents
        _doc("ownership_document",         "سند الملكية"),
        _doc("site_plan_or_croquis",       "كروكي المخطط"),
        _doc("site_photos",                "صور الموقع"),
    ],
    "dynamic_fields": [
        {"name": "zoning_type", "field_type": "str",
         "valid_values": ["residential", "commercial", "administrative", "mixed_use", "agricultural", "unknown"],
         "role": "user_input", "label_ar": "نوع التخطيط العمراني", "group": "", "ui_required": True},
    ],
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
    # Section B description (Phase 8H.2B: optional data fields, ui_required=False)
    s2_text = page.locator("#es-req-s2").inner_text()
    assert "ترفع جودة التقرير" in s2_text, (
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
    """Null-mapped asset type (أصول معنوية) shows soft message with continuation guidance."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="أصول معنوية")
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

def test_CS11_always_visible_composite_nav_link_removed(page: Page, live_server: str) -> None:
    """Phase 8H.1: always-visible #cv-nav-link header link removed; composite access is contextual only."""
    page.goto(live_server, wait_until="networkidle")

    link = page.locator("#cv-nav-link")
    assert link.count() == 0 or not link.is_visible(), (
        "Header #cv-nav-link must NOT be present/visible after Phase 8H.1 nav de-duplication"
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
    # Phase 8H.2B: s2 is now "بيانات إضافية" (optional data), s3 is documents
    assert "ترفع جودة التقرير" in s2_text, (
        f"Section B description missing. Got: {s2_text!r}"
    )
    assert "المستندات المتوفّرة" in s3_text, (
        f"Section C (documents) description missing. Got: {s3_text!r}"
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
    """'عمارة سكنية' (building_full static panel): title is 'متطلبات تقييم عمارة سكنية'."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    title_text = page.locator("#es-req-title").inner_text()
    assert "متطلبات تقييم عمارة سكنية" in title_text, (
        f"Title must be 'متطلبات تقييم عمارة سكنية' for building_full static panel. Got: {title_text!r}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "سيتم التعامل معه" in panel_text or "يتكوّن" in panel_text, (
        f"Building_full system-decision explanation must appear in panel. Got: {panel_text!r}"
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

def test_CS25_masna_is_placeholder_no_api_call(page: Page, live_server: str) -> None:
    """'مصنع' maps to factory placeholder profile — must NOT call GET /api/valuation/requirements."""
    api_calls: list[str] = []

    def intercept(route: Route) -> None:
        api_calls.append(route.request.url)
        route.continue_()

    page.route("**/api/valuation/requirements**", intercept)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="مصنع")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    assert len(api_calls) == 0, (
        f"GET /api/valuation/requirements must NOT be called for 'مصنع' (placeholder profile). "
        f"Got {len(api_calls)} call(s): {api_calls}"
    )


# ── CS26 ──────────────────────────────────────────────────────────────────────

def test_CS26_shaqqa_calls_requirements_api(page: Page, live_server: str) -> None:
    """'شقة سكنية' is residential_unit API profile — must call GET /api/valuation/requirements."""
    api_calls: list[str] = []

    def intercept(route: Route) -> None:
        api_calls.append(route.request.url)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps(_RESIDENTIAL_RESPONSE))

    page.route("**/api/valuation/requirements**", intercept)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    assert len(api_calls) >= 1, (
        f"GET /api/valuation/requirements MUST be called for 'شقة سكنية' (residential_unit). "
        f"Got {len(api_calls)} call(s)."
    )
    assert "asset_type=residential" in api_calls[0], (
        f"API call must use registry code 'residential'. URL: {api_calls[0]!r}"
    )


# ── CS27 ──────────────────────────────────────────────────────────────────────

def test_CS27_land_calls_requirements_api(page: Page, live_server: str) -> None:
    """'أرض فضاء' is land API profile — must call GET /api/valuation/requirements."""
    api_calls: list[str] = []

    def intercept(route: Route) -> None:
        api_calls.append(route.request.url)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps(_LAND_RESPONSE))

    page.route("**/api/valuation/requirements**", intercept)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="أرض فضاء")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    assert len(api_calls) >= 1, (
        f"GET /api/valuation/requirements MUST be called for 'أرض فضاء' (land profile). "
        f"Got {len(api_calls)} call(s)."
    )
    assert "asset_type=land" in api_calls[0], (
        f"API call must use registry code 'land'. URL: {api_calls[0]!r}"
    )


# ── CS28 ──────────────────────────────────────────────────────────────────────

def test_CS28_emara_static_path_zero_api_calls(page: Page, live_server: str) -> None:
    """'عمارة سكنية' takes building_full static path (Phase 8G) — ZERO API calls."""
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
        f"GET /api/valuation/requirements must NOT be called for 'عمارة سكنية' (static path). "
        f"Got {len(api_calls)} call(s): {api_calls}"
    )


# ── CS29 ──────────────────────────────────────────────────────────────────────

def test_CS29_emara_floor_use_section_present(page: Page, live_server: str) -> None:
    """'عمارة سكنية' building_full panel shows floor-use informational rows."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    panel_text = page.locator("#es-req-panel").inner_text()
    assert "الدور الأرضي" in panel_text, (
        f"Floor-use row 'الدور الأرضي' must appear in building_full panel. Got: {panel_text!r}"
    )
    assert "الأدوار المتكررة" in panel_text, (
        f"Floor-use row 'الأدوار المتكررة' must appear in building_full panel. Got: {panel_text!r}"
    )


# ── CS30 ──────────────────────────────────────────────────────────────────────

def test_CS30_hotel_is_placeholder_zero_api_deferred_notice(page: Page, live_server: str) -> None:
    """'فندق' maps to hotel placeholder: ZERO API calls, title contains 'فندق', deferred notice."""
    api_calls: list[str] = []

    def intercept(route: Route) -> None:
        api_calls.append(route.request.url)
        route.continue_()

    page.route("**/api/valuation/requirements**", intercept)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="فندق")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    assert len(api_calls) == 0, (
        f"GET /api/valuation/requirements must NOT be called for 'فندق' (placeholder). "
        f"Got {len(api_calls)} call(s): {api_calls}"
    )
    title_text = page.locator("#es-req-title").inner_text()
    assert "فندق" in title_text, (
        f"Title must contain 'فندق'. Got: {title_text!r}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "قيد التطوير" in panel_text, (
        f"Deferred notice 'قيد التطوير' must appear in hotel placeholder panel. Got: {panel_text!r}"
    )


# ── CS31 ──────────────────────────────────────────────────────────────────────

def test_CS31_factory_is_placeholder_zero_api_deferred_notice(page: Page, live_server: str) -> None:
    """'مصنع' maps to factory placeholder: ZERO API calls, deferred notice shown."""
    api_calls: list[str] = []

    def intercept(route: Route) -> None:
        api_calls.append(route.request.url)
        route.continue_()

    page.route("**/api/valuation/requirements**", intercept)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="مصنع")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    assert len(api_calls) == 0, (
        f"GET /api/valuation/requirements must NOT be called for 'مصنع' (placeholder). "
        f"Got {len(api_calls)} call(s): {api_calls}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "قيد التطوير" in panel_text, (
        f"Deferred notice 'قيد التطوير' must appear in factory placeholder panel. Got: {panel_text!r}"
    )


# ── CS32 ──────────────────────────────────────────────────────────────────────

def test_CS32_hospital_is_placeholder_zero_api_deferred_notice(page: Page, live_server: str) -> None:
    """'مستشفى' maps to hospital placeholder: ZERO API calls, deferred notice shown."""
    api_calls: list[str] = []

    def intercept(route: Route) -> None:
        api_calls.append(route.request.url)
        route.continue_()

    page.route("**/api/valuation/requirements**", intercept)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="مستشفى")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    assert len(api_calls) == 0, (
        f"GET /api/valuation/requirements must NOT be called for 'مستشفى' (placeholder). "
        f"Got {len(api_calls)} call(s): {api_calls}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "قيد التطوير" in panel_text, (
        f"Deferred notice 'قيد التطوير' must appear in hospital placeholder panel. Got: {panel_text!r}"
    )


# ── CS33 ──────────────────────────────────────────────────────────────────────

def test_CS33_all_placeholder_types_have_deferred_notice(page: Page, live_server: str) -> None:
    """All six placeholder asset types render a 'قيد التطوير' notice in the panel."""
    placeholder_types = ["فندق", "مصنع", "محل تجاري", "مستشفى", "مدرسة", "مناجم"]

    for asset_type in placeholder_types:
        page.goto(live_server, wait_until="networkidle")
        _inject_session(page)

        page.select_option("#asset-type", value=asset_type)
        page.select_option("#val-purpose", value="fair_market_value")
        page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

        panel_text = page.locator("#es-req-panel").inner_text()
        assert "قيد التطوير" in panel_text, (
            f"Placeholder asset '{asset_type}' must show 'قيد التطوير'. Got: {panel_text!r}"
        )


# ── CS34 ──────────────────────────────────────────────────────────────────────

def test_CS34_placeholder_panels_no_required_bullets(page: Page, live_server: str) -> None:
    """Placeholder panels contain no ✦ bullet and no '(مطلوب)' required tag."""
    placeholder_types = ["فندق", "مصنع", "مستشفى"]

    for asset_type in placeholder_types:
        page.goto(live_server, wait_until="networkidle")
        _inject_session(page)

        page.select_option("#asset-type", value=asset_type)
        page.select_option("#val-purpose", value="fair_market_value")
        page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

        panel_text = page.locator("#es-req-panel").inner_text()
        assert "✦" not in panel_text, (
            f"Placeholder panel '{asset_type}' must not contain ✦ bullet. Got: {panel_text!r}"
        )
        assert "(مطلوب)" not in panel_text, (
            f"Placeholder panel '{asset_type}' must not contain '(مطلوب)'. Got: {panel_text!r}"
        )


# ── CS35 ──────────────────────────────────────────────────────────────────────

def test_CS35_no_raw_profile_codes_in_placeholder_panels(page: Page, live_server: str) -> None:
    """No raw English profile codes appear in placeholder panel text."""
    raw_codes = ("hotel", "factory", "retail", "hospital", "school", "mine",
                 "building_full", "building_mixed", "residential_unit")

    placeholder_types = ["فندق", "مصنع", "مستشفى"]

    for asset_type in placeholder_types:
        page.goto(live_server, wait_until="networkidle")
        _inject_session(page)

        page.select_option("#asset-type", value=asset_type)
        page.select_option("#val-purpose", value="fair_market_value")
        page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

        panel_text = page.locator("#es-req-panel").inner_text()
        for code in raw_codes:
            assert code not in panel_text, (
                f"Raw profile code '{code}' must not appear in placeholder panel '{asset_type}'. "
                f"Got: {panel_text!r}"
            )


# ── CS36 ──────────────────────────────────────────────────────────────────────

def test_CS36_emara_two_renders_identical(page: Page, live_server: str) -> None:
    """Two consecutive renders of 'عمارة سكنية' produce identical panel innerText."""
    def _render_and_get_text() -> str:
        page.goto(live_server, wait_until="networkidle")
        _inject_session(page)
        page.select_option("#asset-type", value="عمارة سكنية")
        page.select_option("#val-purpose", value="fair_market_value")
        page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
        return page.locator("#es-req-panel").inner_text()

    text1 = _render_and_get_text()
    text2 = _render_and_get_text()

    assert text1 == text2, (
        "Two consecutive renders of 'عمارة سكنية' produced different panel text.\n"
        f"Run 1: {text1!r}\nRun 2: {text2!r}"
    )


# ── CS37 ──────────────────────────────────────────────────────────────────────

def test_CS37_placeholder_has_composite_cta(page: Page, live_server: str) -> None:
    """Phase 8H.1: placeholder panel (فندق) shows contextual composite CTA pointing to composite_valuation.html."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="فندق")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    link = page.locator("#es-req-composite-link")
    expect(link).to_be_visible()
    href = link.get_attribute("href") or ""
    assert "composite_valuation.html" in href, (
        f"Placeholder CTA must point to composite_valuation.html. Got: {href!r}"
    )
    link_text = link.inner_text().strip()
    assert "فتح نموذج التقييم المركب" in link_text, (
        f"Placeholder CTA label must say 'فتح نموذج التقييم المركب'. Got: {link_text!r}"
    )


# ── CS38 ──────────────────────────────────────────────────────────────────────

def test_CS38_building_full_s4_empty_no_method_labels(page: Page, live_server: str) -> None:
    """Phase 8H.1: building_full panel s4 is empty; method label text is absent."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    s4_text = page.locator("#es-req-s4").inner_text().strip()
    assert s4_text == "", (
        f"Section D must be empty for building_full after Phase 8H.1. Got: {s4_text!r}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "نهج المقارنة" not in panel_text, (
        f"Method label 'نهج المقارنة' must not appear in building_full panel. Got: {panel_text!r}"
    )
    assert "نهج الدخل" not in panel_text, (
        f"Method label 'نهج الدخل' must not appear in building_full panel. Got: {panel_text!r}"
    )
    assert "المناهج المقترحة" not in panel_text, (
        f"Methods heading 'المناهج المقترحة' must not appear in building_full panel. Got: {panel_text!r}"
    )


# ── CS39 ──────────────────────────────────────────────────────────────────────

def test_CS39_all_placeholder_types_have_composite_cta_residential_land_do_not(page: Page, live_server: str) -> None:
    """Phase 8H.1: all placeholder types show composite CTA; residential_unit and land do not."""
    placeholder_types = ["فندق", "مصنع", "محل تجاري", "مستشفى", "مدرسة", "مناجم"]

    for asset_type in placeholder_types:
        page.goto(live_server, wait_until="networkidle")
        _inject_session(page)

        page.select_option("#asset-type", value=asset_type)
        page.select_option("#val-purpose", value="fair_market_value")
        page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

        link = page.locator("#es-req-composite-link")
        assert link.count() >= 1 and link.is_visible(), (
            f"Composite CTA must be visible in placeholder panel '{asset_type}'"
        )
        href = link.get_attribute("href") or ""
        assert "composite_valuation.html" in href, (
            f"Composite CTA must point to composite_valuation.html for '{asset_type}'. Got: {href!r}"
        )

    # Residential and land must NOT show composite CTA
    for asset_type, mock_data in [("شقة سكنية", _RESIDENTIAL_RESPONSE), ("أرض فضاء", _LAND_RESPONSE)]:
        _mock_req(page, mock_data)
        page.goto(live_server, wait_until="networkidle")
        _inject_session(page)

        page.select_option("#asset-type", value=asset_type)
        page.select_option("#val-purpose", value="fair_market_value")
        page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

        link = page.locator("#es-req-composite-link")
        assert link.count() == 0 or not link.is_visible(), (
            f"Composite CTA must NOT appear for '{asset_type}' (API-driven, not composite)"
        )


# ══ Phase 8H.2B — structured form controls (CS40 – CS55) ════════════════════


def _load_residential(page: Page, live_server: str) -> None:
    """Helper: navigate to live_server, inject session, select residential + market value."""
    _mock_req(page, _RESIDENTIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)


def _load_land(page: Page, live_server: str) -> None:
    """Helper: navigate to live_server, inject session, select land + market value."""
    _mock_req(page, _LAND_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="أرض فضاء")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)


# ── CS40 ──────────────────────────────────────────────────────────────────────

def test_CS40_residential_renders_form_controls(page: Page, live_server: str) -> None:
    """Phase 8H.2B: residential panel renders real input/select/checkbox elements, not text-only."""
    _load_residential(page, live_server)
    panel = page.locator("#es-req-panel")
    # At least one input or select must exist inside the panel
    inputs  = panel.locator("input, select")
    assert inputs.count() > 0, (
        "Residential panel must contain real form controls after Phase 8H.2B"
    )


# ── CS41 ──────────────────────────────────────────────────────────────────────

def test_CS41_residential_area_sqm_number_input(page: Page, live_server: str) -> None:
    """Phase 8H.2B: area_sqm renders as <input type='number'> in residential panel."""
    _load_residential(page, live_server)
    field = page.locator("#es-req-field-area_sqm")
    assert field.count() > 0, "area_sqm input must be present in residential panel"
    assert field.get_attribute("type") == "number", (
        f"area_sqm must be type='number'. Got: {field.get_attribute('type')!r}"
    )


# ── CS42 ──────────────────────────────────────────────────────────────────────

def test_CS42_residential_floor_number_number_input(page: Page, live_server: str) -> None:
    """Phase 8H.2B: floor_number (int) renders as <input type='number'> in residential panel."""
    _load_residential(page, live_server)
    field = page.locator("#es-req-field-floor_number")
    assert field.count() > 0, "floor_number input must be present in residential panel"
    assert field.get_attribute("type") == "number", (
        f"floor_number must be type='number'. Got: {field.get_attribute('type')!r}"
    )


# ── CS43 ──────────────────────────────────────────────────────────────────────

def test_CS43_residential_finishing_level_select_with_options(page: Page, live_server: str) -> None:
    """Phase 8H.2B: finishing_level renders as <select> with at least 4 options."""
    _load_residential(page, live_server)
    sel = page.locator("#es-req-field-finishing_level")
    assert sel.count() > 0, "finishing_level select must be present"
    tag = sel.evaluate("el => el.tagName.toLowerCase()")
    assert tag == "select", f"finishing_level must be a <select>. Got: {tag!r}"
    opts = page.locator("#es-req-field-finishing_level option")
    assert opts.count() >= 4, (
        f"finishing_level must have ≥4 options. Got: {opts.count()}"
    )


# ── CS44 ──────────────────────────────────────────────────────────────────────

def test_CS44_residential_legal_status_select(page: Page, live_server: str) -> None:
    """Phase 8H.2B: legal_status renders as <select> in residential panel."""
    _load_residential(page, live_server)
    sel = page.locator("#es-req-field-legal_status")
    assert sel.count() > 0, "legal_status select must be present in residential panel"
    tag = sel.evaluate("el => el.tagName.toLowerCase()")
    assert tag == "select", f"legal_status must be a <select>. Got: {tag!r}"
    opts = page.locator("#es-req-field-legal_status option")
    assert opts.count() >= 4, (
        f"legal_status must have ≥4 options. Got: {opts.count()}"
    )


# ── CS45 ──────────────────────────────────────────────────────────────────────

def test_CS45_residential_document_checkboxes(page: Page, live_server: str) -> None:
    """Phase 8H.2B: document fields render as checkboxes with Arabic labels in section C."""
    _load_residential(page, live_server)
    # ownership_document is a document checkbox
    cb = page.locator("#es-req-field-ownership_document")
    assert cb.count() > 0, "ownership_document checkbox must be present"
    assert cb.get_attribute("type") == "checkbox", (
        f"ownership_document must be type='checkbox'. Got: {cb.get_attribute('type')!r}"
    )
    # Its label must contain the Arabic label_ar value
    label = page.locator("label[for='es-req-field-ownership_document']")
    assert label.count() > 0, "Label for ownership_document must be present"
    label_text = label.inner_text()
    assert "سند الملكية" in label_text, (
        f"ownership_document label must contain 'سند الملكية'. Got: {label_text!r}"
    )
    # recent_photos must also be a checkbox
    cb2 = page.locator("#es-req-field-recent_photos")
    assert cb2.count() > 0, "recent_photos checkbox must be present"
    assert cb2.get_attribute("type") == "checkbox"


# ── CS46 ──────────────────────────────────────────────────────────────────────

def test_CS46_land_renders_form_controls(page: Page, live_server: str) -> None:
    """Phase 8H.2B: land panel renders real input/select/checkbox elements, not text-only."""
    _load_land(page, live_server)
    panel = page.locator("#es-req-panel")
    inputs = panel.locator("input, select")
    assert inputs.count() > 0, (
        "Land panel must contain real form controls after Phase 8H.2B"
    )


# ── CS47 ──────────────────────────────────────────────────────────────────────

def test_CS47_land_land_area_sqm_number_input(page: Page, live_server: str) -> None:
    """Phase 8H.2B: land_area_sqm renders as <input type='number'> in land panel."""
    _load_land(page, live_server)
    field = page.locator("#es-req-field-land_area_sqm")
    assert field.count() > 0, "land_area_sqm input must be present in land panel"
    assert field.get_attribute("type") == "number", (
        f"land_area_sqm must be type='number'. Got: {field.get_attribute('type')!r}"
    )


# ── CS48 ──────────────────────────────────────────────────────────────────────

def test_CS48_land_frontage_m_number_input(page: Page, live_server: str) -> None:
    """Phase 8H.2B: frontage_m renders as <input type='number'> in land panel."""
    _load_land(page, live_server)
    field = page.locator("#es-req-field-frontage_m")
    assert field.count() > 0, "frontage_m input must be present in land panel"
    assert field.get_attribute("type") == "number", (
        f"frontage_m must be type='number'. Got: {field.get_attribute('type')!r}"
    )


# ── CS49 ──────────────────────────────────────────────────────────────────────

def test_CS49_land_zoning_type_select_with_options(page: Page, live_server: str) -> None:
    """Phase 8H.2B: zoning_type renders as <select> with at least 6 options in land panel."""
    _load_land(page, live_server)
    sel = page.locator("#es-req-field-zoning_type")
    assert sel.count() > 0, "zoning_type select must be present in land panel"
    tag = sel.evaluate("el => el.tagName.toLowerCase()")
    assert tag == "select", f"zoning_type must be a <select>. Got: {tag!r}"
    opts = page.locator("#es-req-field-zoning_type option")
    assert opts.count() >= 6, (
        f"zoning_type must have ≥6 options. Got: {opts.count()}"
    )


# ── CS50 ──────────────────────────────────────────────────────────────────────

def test_CS50_land_utilities_available_checkbox_group(page: Page, live_server: str) -> None:
    """Phase 8H.2B: utilities_available (list+valid_values) renders as a checkbox group."""
    _load_land(page, live_server)
    checkboxes = page.locator("[name='utilities_available']")
    assert checkboxes.count() >= 5, (
        f"utilities_available must have ≥5 checkboxes (one per valid value). "
        f"Got: {checkboxes.count()}"
    )
    # Every element in the group must be a checkbox
    for i in range(checkboxes.count()):
        cb = checkboxes.nth(i)
        assert cb.get_attribute("type") == "checkbox", (
            f"utilities_available item {i} must be type='checkbox'"
        )


# ── CS51 ──────────────────────────────────────────────────────────────────────

def test_CS51_land_buildability_status_select(page: Page, live_server: str) -> None:
    """Phase 8H.2B: buildability_status renders as <select> in land panel."""
    _load_land(page, live_server)
    sel = page.locator("#es-req-field-buildability_status")
    assert sel.count() > 0, "buildability_status select must be present in land panel"
    tag = sel.evaluate("el => el.tagName.toLowerCase()")
    assert tag == "select", f"buildability_status must be a <select>. Got: {tag!r}"


# ── CS52 ──────────────────────────────────────────────────────────────────────

def test_CS52_land_document_checkboxes(page: Page, live_server: str) -> None:
    """Phase 8H.2B: document fields render as checkboxes with Arabic labels in land section C."""
    _load_land(page, live_server)
    cb = page.locator("#es-req-field-ownership_document")
    assert cb.count() > 0, "ownership_document checkbox must be present in land panel"
    assert cb.get_attribute("type") == "checkbox"
    label = page.locator("label[for='es-req-field-ownership_document']")
    assert label.count() > 0, "Label for land ownership_document must be present"
    label_text = label.inner_text()
    assert "سند الملكية" in label_text, (
        f"Land ownership_document label must contain 'سند الملكية'. Got: {label_text!r}"
    )
    cb2 = page.locator("#es-req-field-site_photos")
    assert cb2.count() > 0, "site_photos checkbox must be present in land panel"
    assert cb2.get_attribute("type") == "checkbox"


# ── CS53 ──────────────────────────────────────────────────────────────────────

def test_CS53_engine_fields_not_rendered(page: Page, live_server: str) -> None:
    """Phase 8H.2B: engine_value fields (comparable/cost/income/comparables) must NOT render."""
    _load_residential(page, live_server)
    for engine_field in ("comparable", "cost", "income", "comparables"):
        el = page.locator(f"[data-es-req-field='{engine_field}']")
        assert el.count() == 0, (
            f"Engine field '{engine_field}' must NOT be rendered as a form control. "
            f"Found {el.count()} element(s)."
        )


# ── CS54 ──────────────────────────────────────────────────────────────────────

def test_CS54_field_label_comes_from_label_ar(page: Page, live_server: str) -> None:
    """Phase 8H.2B: the visible label for area_sqm comes from label_ar ('المساحة (م²)'), not hardcoded."""
    _load_residential(page, live_server)
    label = page.locator("label[for='es-req-field-area_sqm']")
    assert label.count() > 0, "Label for area_sqm must be present"
    label_text = label.inner_text()
    assert "المساحة" in label_text, (
        f"area_sqm label must contain Arabic text from label_ar 'المساحة (م²)'. "
        f"Got: {label_text!r}"
    )
    # Confirm the same DRY property for a land field
    _load_land(page, live_server)
    label2 = page.locator("label[for='es-req-field-land_area_sqm']")
    assert label2.count() > 0, "Label for land_area_sqm must be present"
    label2_text = label2.inner_text()
    assert "مساحة" in label2_text, (
        f"land_area_sqm label must contain Arabic text from label_ar. Got: {label2_text!r}"
    )


# ── CS55 ──────────────────────────────────────────────────────────────────────

def test_CS55_no_console_errors_on_render(page: Page, live_server: str) -> None:
    """Phase 8H.2B: rendering residential and land panels produces zero JS console errors.

    Network-level 401s that occur before session injection are pre-existing expected
    behaviour and are excluded from this assertion.
    """
    def _is_js_error(msg) -> bool:
        """True only for real JavaScript errors; ignore network/auth noise."""
        return (
            msg.type == "error"
            and "401" not in msg.text
            and "UNAUTHORIZED" not in msg.text
            and "Failed to load resource" not in msg.text
        )

    console_errors: list[str] = []
    page.on("console", lambda msg: console_errors.append(msg.text) if _is_js_error(msg) else None)

    _load_residential(page, live_server)
    assert not console_errors, (
        f"JavaScript console errors during residential render: {console_errors}"
    )

    console_errors.clear()
    _load_land(page, live_server)
    assert not console_errors, (
        f"JavaScript console errors during land render: {console_errors}"
    )


# ══ Phase 8H.2D — UX polish (CS56 – CS60) ════════════════════════════════════


# ── CS56 ──────────────────────────────────────────────────────────────────────

def test_CS56_select_first_option_is_ikhtaar_placeholder(page: Page, live_server: str) -> None:
    """Phase 8H.2D: select dropdowns render 'اختر ...' as the first (disabled) placeholder option."""
    _load_residential(page, live_server)
    first_text = page.locator("#es-req-field-finishing_level option").nth(0).inner_text()
    assert "اختر" in first_text, (
        f"First option of finishing_level must contain 'اختر'. Got: {first_text!r}"
    )


# ── CS57 ──────────────────────────────────────────────────────────────────────

def test_CS57_select_default_option_derived_from_label_ar(page: Page, live_server: str) -> None:
    """Phase 8H.2D: default select option text is DERIVED from label_ar — DRY compliance."""
    _load_residential(page, live_server)
    # finishing_level label_ar in mock = "مستوى التشطيب"
    first_text = page.locator("#es-req-field-finishing_level option").nth(0).inner_text()
    assert "مستوى التشطيب" in first_text, (
        f"Default option must contain label_ar 'مستوى التشطيب' (derived, not hardcoded). "
        f"Got: {first_text!r}"
    )
    # land: zoning_type label_ar = "نوع التخطيط العمراني"
    _load_land(page, live_server)
    first_text2 = page.locator("#es-req-field-zoning_type option").nth(0).inner_text()
    assert "نوع التخطيط" in first_text2, (
        f"Default option for zoning_type must contain label_ar fragment. Got: {first_text2!r}"
    )


# ── CS58 ──────────────────────────────────────────────────────────────────────

def test_CS58_yesno_field_renders_arabic_options(page: Page, live_server: str) -> None:
    """Phase 8H.2D: fields with yes/no valid_values display نعم / لا (not raw 'yes'/'no')."""
    _load_residential(page, live_server)
    sel = page.locator("#es-req-field-elevator_available")
    assert sel.count() > 0, "elevator_available select must be present in residential panel"
    opts_text = page.locator("#es-req-field-elevator_available option").all_inner_texts()
    assert any("نعم" in t for t in opts_text), (
        f"elevator_available must have a 'نعم' option. Got: {opts_text}"
    )
    assert any("لا" in t for t in opts_text), (
        f"elevator_available must have a 'لا' option. Got: {opts_text}"
    )


# ── CS59 ──────────────────────────────────────────────────────────────────────

def test_CS59_number_inputs_have_placeholder(page: Page, live_server: str) -> None:
    """Phase 8H.2D: number inputs carry a non-empty placeholder attribute."""
    _load_residential(page, live_server)
    ph = page.locator("#es-req-field-area_sqm").get_attribute("placeholder")
    assert ph and len(ph) > 0, (
        f"area_sqm must have a non-empty placeholder. Got: {ph!r}"
    )
    _load_land(page, live_server)
    ph2 = page.locator("#es-req-field-frontage_m").get_attribute("placeholder")
    assert ph2 and len(ph2) > 0, (
        f"frontage_m must have a non-empty placeholder. Got: {ph2!r}"
    )


# ── CS60 ──────────────────────────────────────────────────────────────────────

def test_CS60_three_section_headings_visible_in_residential_panel(page: Page, live_server: str) -> None:
    """Phase 8H.2D: all 3 section card headings are rendered inside the requirements panel."""
    _load_residential(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "البيانات الأساسية المطلوبة" in panel_text, (
        f"Section A heading missing from panel. Got: {panel_text!r}"
    )
    assert "بيانات إضافية لتحسين الدقّة" in panel_text, (
        f"Section B heading missing from panel. Got: {panel_text!r}"
    )
    assert "المستندات المطلوبة" in panel_text, (
        f"Section C heading missing from panel. Got: {panel_text!r}"
    )


# ── CS61 ──────────────────────────────────────────────────────────────────────

def test_CS61_utilities_available_shows_arabic_labels(page: Page, live_server: str) -> None:
    """Phase 8H.2D: utilities_available chip group shows Arabic labels, not raw backend codes."""
    _load_land(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    for arabic in ("كهرباء", "مياه", "صرف صحي", "غاز", "طريق ممهد"):
        assert arabic in panel_text, (
            f"utilities_available must show Arabic label '{arabic}'. Got: {panel_text!r}"
        )


# ── CS62 ──────────────────────────────────────────────────────────────────────

def test_CS62_utilities_available_no_raw_backend_codes(page: Page, live_server: str) -> None:
    """Phase 8H.2D: utilities_available chip group must NOT display raw backend codes."""
    _load_land(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    for raw in ("electricity", "water", "sewage", "gas", "paved_road"):
        assert raw not in panel_text, (
            f"Raw backend code '{raw}' must not appear in rendered panel. Got: {panel_text!r}"
        )


# ══ Phase 8H.2E — dropdown options content fix (CS63 – CS70) ═════════════════


# ── CS63 ──────────────────────────────────────────────────────────────────────

def test_CS63_finishing_level_options_arabic(page: Page, live_server: str) -> None:
    """Phase 8H.2E: finishing_level select options display Arabic translations, not raw codes."""
    _load_residential(page, live_server)
    opts = page.locator("#es-req-field-finishing_level option").all_inner_texts()
    for arabic in ("بدون تشطيب", "نصف تشطيب", "تشطيب عادي", "تشطيب فاخر"):
        assert any(arabic in t for t in opts), (
            f"finishing_level must have Arabic option '{arabic}'. Got opts: {opts}"
        )
    for raw in ("shell", "semi_finished", "standard_finished", "luxury_finished"):
        assert not any(raw == t.strip() for t in opts), (
            f"Raw code '{raw}' must not be the displayed text in finishing_level options. Got: {opts}"
        )


# ── CS64 ──────────────────────────────────────────────────────────────────────

def test_CS64_legal_status_options_arabic(page: Page, live_server: str) -> None:
    """Phase 8H.2E: legal_status select options display Arabic translations, not raw codes."""
    _load_residential(page, live_server)
    opts = page.locator("#es-req-field-legal_status option").all_inner_texts()
    for arabic in ("ملكية مسجلة", "عقد ابتدائي", "تخصيص", "غير محدد"):
        assert any(arabic in t for t in opts), (
            f"legal_status must have Arabic option '{arabic}'. Got opts: {opts}"
        )
    for raw in ("registered_title", "preliminary_contract", "allocation", "unknown"):
        assert not any(raw == t.strip() for t in opts), (
            f"Raw code '{raw}' must not be the displayed text in legal_status options. Got: {opts}"
        )


# ── CS65 ──────────────────────────────────────────────────────────────────────

def test_CS65_parking_available_shows_arabic(page: Page, live_server: str) -> None:
    """Phase 8H.2E: parking_available select displays نعم/لا, not raw yes/no."""
    _load_residential(page, live_server)
    opts = page.locator("#es-req-field-parking_available option").all_inner_texts()
    assert any("نعم" in t for t in opts), (
        f"parking_available must have a 'نعم' option. Got: {opts}"
    )
    assert any("لا" in t for t in opts), (
        f"parking_available must have a 'لا' option. Got: {opts}"
    )
    assert not any("yes" == t.strip() for t in opts), (
        f"Raw 'yes' must not be the displayed text in parking_available. Got: {opts}"
    )


# ── CS66 ──────────────────────────────────────────────────────────────────────

def test_CS66_zoning_type_options_arabic(page: Page, live_server: str) -> None:
    """Phase 8H.2E: zoning_type select options display Arabic translations, not raw codes."""
    _load_land(page, live_server)
    opts = page.locator("#es-req-field-zoning_type option").all_inner_texts()
    for arabic in ("سكني", "تجاري", "إداري", "استخدام مختلط", "زراعي", "غير محدد"):
        assert any(arabic in t for t in opts), (
            f"zoning_type must have Arabic option '{arabic}'. Got opts: {opts}"
        )
    for raw in ("residential", "commercial", "administrative", "mixed_use", "agricultural"):
        assert not any(raw == t.strip() for t in opts), (
            f"Raw code '{raw}' must not be the displayed text in zoning_type options. Got: {opts}"
        )


# ── CS67 ──────────────────────────────────────────────────────────────────────

def test_CS67_buildability_status_options_arabic(page: Page, live_server: str) -> None:
    """Phase 8H.2E: buildability_status select options display Arabic translations."""
    _load_land(page, live_server)
    opts = page.locator("#es-req-field-buildability_status option").all_inner_texts()
    for arabic in ("قابل للبناء", "يحتاج تحقق", "قيود تخطيطية", "غير محدد"):
        assert any(arabic in t for t in opts), (
            f"buildability_status must have Arabic option '{arabic}'. Got opts: {opts}"
        )
    for raw in ("buildable", "needs_verification", "planning_restrictions"):
        assert not any(raw == t.strip() for t in opts), (
            f"Raw code '{raw}' must not be displayed text in buildability_status. Got: {opts}"
        )


# ── CS68 ──────────────────────────────────────────────────────────────────────

def test_CS68_hbu_options_arabic(page: Page, live_server: str) -> None:
    """Phase 8H.2E: hbu select options display Arabic translations, not raw codes."""
    _load_land(page, live_server)
    opts = page.locator("#es-req-field-hbu option").all_inner_texts()
    for arabic in ("سكني", "تجاري", "استخدام مختلط", "صناعي", "زراعي", "مضاربي"):
        assert any(arabic in t for t in opts), (
            f"hbu must have Arabic option '{arabic}'. Got opts: {opts}"
        )
    for raw in ("industrial", "speculative"):
        assert not any(raw == t.strip() for t in opts), (
            f"Raw code '{raw}' must not be the displayed text in hbu options. Got: {opts}"
        )


# ── CS69 ──────────────────────────────────────────────────────────────────────

def test_CS69_residential_panel_no_raw_enum_codes(page: Page, live_server: str) -> None:
    """Phase 8H.2E: residential panel visible text contains no raw enum value codes."""
    _load_residential(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    raw_codes = (
        "shell", "semi_finished", "standard_finished", "luxury_finished",
        "registered_title", "preliminary_contract", "allocation",
        "owner_occupied", "rental",
        "luxury", "economy", "heritage",
        "ordinary", "premium",
    )
    for code in raw_codes:
        assert code not in panel_text, (
            f"Raw code '{code}' must not appear in residential panel visible text. "
            f"Got: {panel_text!r}"
        )


# ── CS70 ──────────────────────────────────────────────────────────────────────

def test_CS70_land_panel_no_raw_enum_codes(page: Page, live_server: str) -> None:
    """Phase 8H.2E: land panel visible text contains no raw enum value codes."""
    _load_land(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    raw_codes = (
        "registered_title", "preliminary_contract", "allocation",
        "buildable", "needs_verification", "planning_restrictions",
        "mixed_use", "agricultural", "administrative",
        "industrial", "speculative",
        "prime", "secondary", "remote",
        "unrestricted", "general_commercial", "residential_only", "restricted",
        "ready_to_build", "feasible", "challenging", "very_difficult",
    )
    for code in raw_codes:
        assert code not in panel_text, (
            f"Raw code '{code}' must not appear in land panel visible text. "
            f"Got: {panel_text!r}"
        )


# ══ Phase 8I — Asset Selector UX (CS71 – CS78) ═══════════════════════════════


# ── CS71 ──────────────────────────────────────────────────────────────────────

def test_CS71_profile_explainer_hidden_on_load(page: Page, live_server: str) -> None:
    """Phase 8I: #es-profile-explainer is hidden on initial page load (no selection yet)."""
    page.goto(live_server, wait_until="networkidle")
    explainer = page.locator("#es-profile-explainer")
    assert explainer.count() > 0, "#es-profile-explainer must exist in DOM"
    assert not explainer.is_visible(), (
        "#es-profile-explainer must be hidden before any asset-type selection"
    )


# ── CS72 ──────────────────────────────────────────────────────────────────────

def test_CS72_residential_selection_shows_supported_badge(page: Page, live_server: str) -> None:
    """Phase 8I: selecting شقة سكنية shows explainer with 'مدعوم' badge."""
    _mock_req(page, _RESIDENTIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    explainer = page.locator("#es-profile-explainer")
    assert explainer.is_visible(), "#es-profile-explainer must be visible after selecting شقة سكنية"
    badge_text = page.locator("#es-profile-badge").inner_text()
    assert "مدعوم" in badge_text, (
        f"Badge must contain 'مدعوم' for residential selection. Got: {badge_text!r}"
    )


# ── CS73 ──────────────────────────────────────────────────────────────────────

def test_CS73_building_full_selection_shows_composite_badge(page: Page, live_server: str) -> None:
    """Phase 8I: selecting عمارة سكنية (building_full) shows 'نموذج مركّب' badge."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    explainer = page.locator("#es-profile-explainer")
    assert explainer.is_visible(), "#es-profile-explainer must be visible after selecting عمارة سكنية"
    badge_text = page.locator("#es-profile-badge").inner_text()
    assert "نموذج مركّب" in badge_text, (
        f"Badge must contain 'نموذج مركّب' for building_full. Got: {badge_text!r}"
    )


# ── CS74 ──────────────────────────────────────────────────────────────────────

def test_CS74_placeholder_selection_shows_in_development_badge(page: Page, live_server: str) -> None:
    """Phase 8I: selecting فندق (placeholder profile) shows 'قيد التطوير' badge."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="فندق")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    explainer = page.locator("#es-profile-explainer")
    assert explainer.is_visible(), "#es-profile-explainer must be visible after selecting فندق"
    badge_text = page.locator("#es-profile-badge").inner_text()
    assert "قيد التطوير" in badge_text, (
        f"Badge must contain 'قيد التطوير' for placeholder profile. Got: {badge_text!r}"
    )


# ── CS75 ──────────────────────────────────────────────────────────────────────

def test_CS75_unsupported_selection_shows_unsupported_badge(page: Page, live_server: str) -> None:
    """Phase 8I: selecting أصول معنوية (null-mapped, unsupported) shows 'غير مدعوم' badge."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="أصول معنوية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    explainer = page.locator("#es-profile-explainer")
    assert explainer.is_visible(), "#es-profile-explainer must be visible after selecting unsupported type"
    badge_text = page.locator("#es-profile-badge").inner_text()
    assert "غير مدعوم" in badge_text, (
        f"Badge must contain 'غير مدعوم' for unsupported type. Got: {badge_text!r}"
    )


# ── CS76 ──────────────────────────────────────────────────────────────────────

def test_CS76_explainer_updates_on_selection_change(page: Page, live_server: str) -> None:
    """Phase 8I: changing selection فندق → شقة سكنية updates badge from قيد التطوير to مدعوم."""
    _mock_req(page, _RESIDENTIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    # First selection: فندق → قيد التطوير
    page.select_option("#asset-type", value="فندق")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    badge_text_1 = page.locator("#es-profile-badge").inner_text()
    assert "قيد التطوير" in badge_text_1, (
        f"First selection (فندق) must show 'قيد التطوير'. Got: {badge_text_1!r}"
    )

    # Second selection: شقة سكنية → مدعوم
    page.select_option("#asset-type", value="شقة سكنية")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
    badge_text_2 = page.locator("#es-profile-badge").inner_text()
    assert "مدعوم" in badge_text_2, (
        f"After changing to شقة سكنية, badge must show 'مدعوم'. Got: {badge_text_2!r}"
    )
    assert "قيد التطوير" not in badge_text_2, (
        f"'قيد التطوير' must NOT appear in badge after switching to residential. Got: {badge_text_2!r}"
    )


# ── CS77 ──────────────────────────────────────────────────────────────────────

def test_CS77_optgroups_present_in_asset_type_select(page: Page, live_server: str) -> None:
    """Phase 8I: #asset-type select contains <optgroup> elements for category grouping."""
    page.goto(live_server, wait_until="networkidle")
    optgroups = page.locator("#asset-type optgroup")
    assert optgroups.count() >= 4, (
        f"#asset-type must have ≥4 optgroup elements. Got: {optgroups.count()}"
    )
    labels = [optgroups.nth(i).get_attribute("label") for i in range(optgroups.count())]
    assert any("سكن" in (lbl or "") for lbl in labels), (
        f"Expected an optgroup with 'سكن' in label. Got labels: {labels}"
    )
    assert any("أراضٍ" in (lbl or "") or "أراض" in (lbl or "") for lbl in labels), (
        f"Expected an optgroup for أراضٍ. Got labels: {labels}"
    )


# ── CS78 ──────────────────────────────────────────────────────────────────────

def test_CS78_all_original_option_values_unchanged(page: Page, live_server: str) -> None:
    """Phase 8I: all 16 original option values still present in #asset-type (values unchanged)."""
    page.goto(live_server, wait_until="networkidle")
    original_values = [
        "شقة سكنية", "عمارة سكنية", "تجاري", "أرض فضاء", "مصنع",
        "أرض زراعية", "فندق", "محل تجاري", "مستشفى", "مدرسة",
        "أصول معنوية", "ملكيات جزئية", "مناجم", "استثمارات تحت الإنشاء",
        "historical", "heritage",
    ]
    actual_values = page.locator("#asset-type option").evaluate_all(
        "opts => opts.map(o => o.value)"
    )
    for v in original_values:
        assert v in actual_values, (
            f"Original option value '{v}' must still be present in #asset-type. "
            f"Got values: {actual_values}"
        )
