"""
test_professional_composite_split.py — E2E tests for professional geo refactor
and composite tab structure.

PCS01–PCS10  Professional tab: hierarchical geo selector
PCS11–PCS22  Composite tab: structure and data-testids
PCS23–PCS28  Regression: other tabs unchanged
"""
from __future__ import annotations

import pytest

# ── helpers ──────────────────────────────────────────────────────────────────

def _goto(page, live_server: str, timeout: int = 15_000):
    page.goto(live_server, timeout=timeout)
    page.wait_for_load_state("networkidle", timeout=timeout)


def _switch_to_professional(page):
    page.click("#es-tab-professional")
    page.wait_for_selector("#ws-professional.es-ws-active", timeout=5_000)


def _switch_to_composite(page):
    page.click("#es-tab-composite")
    page.wait_for_selector("#ws-composite.es-ws-active", timeout=5_000)


# ═══════════════════════════════════════════════════════════════════════════════
# PCS01–PCS10  Professional tab geo
# ═══════════════════════════════════════════════════════════════════════════════

def test_PCS01_professional_tab_opens(page, live_server):
    """Professional tab activates and workspace is visible."""
    _goto(page, live_server)
    _switch_to_professional(page)
    assert page.is_visible("#ws-professional")


def test_PCS02_professional_geo_country_selector_present(page, live_server):
    """Country dropdown exists with data-testid."""
    _goto(page, live_server)
    _switch_to_professional(page)
    el = page.query_selector('[data-testid="professional-valuation-country"]')
    assert el is not None, "professional-valuation-country not found"


def test_PCS03_professional_geo_region_selector_present(page, live_server):
    """Region/province dropdown exists with data-testid."""
    _goto(page, live_server)
    _switch_to_professional(page)
    el = page.query_selector('[data-testid="professional-valuation-region"]')
    assert el is not None, "professional-valuation-region not found"


def test_PCS04_professional_geo_city_selector_present(page, live_server):
    """City dropdown exists with data-testid."""
    _goto(page, live_server)
    _switch_to_professional(page)
    el = page.query_selector('[data-testid="professional-valuation-city"]')
    assert el is not None, "professional-valuation-city not found"


def test_PCS05_professional_geo_district_input_present(page, live_server):
    """District free-text input exists with data-testid."""
    _goto(page, live_server)
    _switch_to_professional(page)
    el = page.query_selector('[data-testid="professional-valuation-district"]')
    assert el is not None, "professional-valuation-district not found"


def test_PCS06_professional_geo_egypt_populates_provinces(page, live_server):
    """Selecting Egypt populates the province dropdown with Egyptian provinces."""
    _goto(page, live_server)
    _switch_to_professional(page)
    page.select_option("#prof-geo-country", value="EG")
    page.wait_for_timeout(300)
    prov_el = page.query_selector("#prof-geo-province")
    assert prov_el is not None
    assert prov_el.is_enabled()
    options = prov_el.query_selector_all("option")
    values = [o.get_attribute("value") for o in options if o.get_attribute("value")]
    assert len(values) >= 5, f"Expected ≥5 Egyptian provinces, got {len(values)}"
    assert any("القاهرة" in v for v in values)


def test_PCS07_professional_geo_egypt_cairo_populates_cities(page, live_server):
    """Selecting Egypt → القاهرة fills city dropdown."""
    _goto(page, live_server)
    _switch_to_professional(page)
    page.select_option("#prof-geo-country", value="EG")
    page.wait_for_timeout(300)
    page.select_option("#prof-geo-province", label="القاهرة")
    page.wait_for_timeout(300)
    city_el = page.query_selector("#prof-geo-city")
    assert city_el is not None and city_el.is_enabled()
    options = city_el.query_selector_all("option")
    values = [o.get_attribute("value") for o in options if o.get_attribute("value")]
    assert len(values) >= 3, f"Expected ≥3 Cairo cities, got {len(values)}"


def test_PCS08_professional_geo_saudi_populates_provinces(page, live_server):
    """Selecting Saudi Arabia populates province dropdown."""
    _goto(page, live_server)
    _switch_to_professional(page)
    page.select_option("#prof-geo-country", value="SA")
    page.wait_for_timeout(300)
    prov_el = page.query_selector("#prof-geo-province")
    assert prov_el is not None and prov_el.is_enabled()
    options = prov_el.query_selector_all("option")
    values = [o.get_attribute("value") for o in options if o.get_attribute("value")]
    assert len(values) >= 5, f"Expected ≥5 SA provinces, got {len(values)}"


def test_PCS09_professional_geo_city_other_shows_text_input(page, live_server):
    """Selecting 'مدينة أخرى' reveals the free-text city input."""
    _goto(page, live_server)
    _switch_to_professional(page)
    page.select_option("#prof-geo-country", value="EG")
    page.wait_for_timeout(300)
    page.select_option("#prof-geo-province", label="القاهرة")
    page.wait_for_timeout(300)
    page.select_option("#prof-geo-city", value="مدينة أخرى")
    page.wait_for_timeout(300)
    city_other = page.query_selector('[data-testid="professional-valuation-city-other"]')
    assert city_other is not None
    assert city_other.is_visible(), "city-other text input not visible after selecting مدينة أخرى"


def test_PCS10_professional_geo_no_flat_loc_eg_sa(page, live_server):
    """Old flat loc-eg / loc-sa selects are gone from the professional tab."""
    _goto(page, live_server)
    _switch_to_professional(page)
    assert page.query_selector("#loc-eg") is None, "#loc-eg should not exist"
    assert page.query_selector("#loc-sa") is None, "#loc-sa should not exist"


# ═══════════════════════════════════════════════════════════════════════════════
# PCS11–PCS22  Composite tab structure
# ═══════════════════════════════════════════════════════════════════════════════

def test_PCS11_composite_tab_button_has_testid(page, live_server):
    """Composite tab button has data-testid=composite-valuation-tab."""
    _goto(page, live_server)
    el = page.query_selector('[data-testid="composite-valuation-tab"]')
    assert el is not None, "composite-valuation-tab not found"


def test_PCS12_composite_tab_opens(page, live_server):
    """Composite tab activates and workspace is visible."""
    _goto(page, live_server)
    _switch_to_composite(page)
    assert page.is_visible("#ws-composite")


def test_PCS13_composite_header_present(page, live_server):
    """Composite workspace has a header section with correct data-testid."""
    _goto(page, live_server)
    _switch_to_composite(page)
    el = page.query_selector('[data-testid="composite-valuation-header"]')
    assert el is not None, "composite-valuation-header not found"
    assert el.is_visible()


def test_PCS14_composite_header_has_title_text(page, live_server):
    """Composite header contains the tab title text."""
    _goto(page, live_server)
    _switch_to_composite(page)
    header = page.query_selector('[data-testid="composite-valuation-header"]')
    assert header is not None
    text = header.inner_text()
    assert "التقييم" in text or "مجمّع" in text or "مجمع" in text


def test_PCS15_composite_component_form_present(page, live_server):
    """composite-component-form data-testid exists in composite workspace."""
    _goto(page, live_server)
    _switch_to_composite(page)
    el = page.query_selector('[data-testid="composite-component-form"]')
    assert el is not None, "composite-component-form not found"


def test_PCS16_composite_component_table_present(page, live_server):
    """composite-component-table data-testid exists."""
    _goto(page, live_server)
    _switch_to_composite(page)
    el = page.query_selector('[data-testid="composite-component-table"]')
    assert el is not None, "composite-component-table not found"


def test_PCS17_composite_add_component_button_present(page, live_server):
    """composite-add-component data-testid exists."""
    _goto(page, live_server)
    _switch_to_composite(page)
    el = page.query_selector('[data-testid="composite-add-component"]')
    assert el is not None, "composite-add-component not found"


def test_PCS18_composite_generate_button_present(page, live_server):
    """composite-generate data-testid exists."""
    _goto(page, live_server)
    _switch_to_composite(page)
    el = page.query_selector('[data-testid="composite-generate"]')
    assert el is not None, "composite-generate not found"


def test_PCS19_composite_output_present(page, live_server):
    """composite-output data-testid exists."""
    _goto(page, live_server)
    _switch_to_composite(page)
    el = page.query_selector('[data-testid="composite-output"]')
    assert el is not None, "composite-output not found"


def test_PCS20_composite_draft_warning_present(page, live_server):
    """composite-draft-warning data-testid exists in DOM."""
    _goto(page, live_server)
    _switch_to_composite(page)
    el = page.query_selector('[data-testid="composite-draft-warning"]')
    assert el is not None, "composite-draft-warning not found"


def test_PCS21_composite_expert_cta_present(page, live_server):
    """composite-expert-cta data-testid exists and contains a link."""
    _goto(page, live_server)
    _switch_to_composite(page)
    el = page.query_selector('[data-testid="composite-expert-cta"]')
    assert el is not None, "composite-expert-cta not found"
    link = el.query_selector("a")
    assert link is not None, "composite-expert-cta has no anchor link"


def test_PCS22_composite_content_not_in_professional_tab(page, live_server):
    """cmp-form does NOT appear inside the professional workspace."""
    _goto(page, live_server)
    _switch_to_professional(page)
    ws = page.query_selector("#ws-professional")
    assert ws is not None
    cmp_inside = ws.query_selector("#cmp-form")
    assert cmp_inside is None, "cmp-form should not be inside ws-professional"


# ═══════════════════════════════════════════════════════════════════════════════
# PCS23–PCS28  Regression — other tabs and data-testids unchanged
# ═══════════════════════════════════════════════════════════════════════════════

def test_PCS23_chat_tab_unaffected(page, live_server):
    """Chat tab still opens without errors."""
    _goto(page, live_server)
    page.click("#es-tab-chat")
    page.wait_for_selector("#ws-chat.es-ws-active", timeout=5_000)
    assert page.is_visible("#ws-chat")


def test_PCS24_tax_tab_unaffected(page, live_server):
    """Tax tab still opens without errors."""
    _goto(page, live_server)
    page.click("#es-tab-tax")
    page.wait_for_selector("#ws-tax.es-ws-active", timeout=5_000)
    assert page.is_visible("#ws-tax")


def test_PCS25_simple_valuation_geo_unchanged(page, live_server):
    """Simple valuation geo (geo-country, geo-province, geo-city) still exists."""
    _goto(page, live_server)
    page.click("#es-tab-valuation")
    page.wait_for_selector("#ws-valuation.es-ws-active", timeout=5_000)
    assert page.query_selector("#geo-country") is not None
    assert page.query_selector("#geo-province") is not None
    assert page.query_selector("#geo-city") is not None


def test_PCS26_simple_valuation_geo_still_works(page, live_server):
    """Selecting Egypt in simple valuation geo still populates provinces."""
    _goto(page, live_server)
    page.click("#es-tab-valuation")
    page.wait_for_selector("#ws-valuation.es-ws-active", timeout=5_000)
    page.select_option("#geo-country", value="EG")
    page.wait_for_timeout(300)
    prov = page.query_selector("#geo-province")
    assert prov is not None and prov.is_enabled()
    options = [o.get_attribute("value") for o in prov.query_selector_all("option") if o.get_attribute("value")]
    assert len(options) >= 5


def test_PCS27_professional_asset_family_still_present(page, live_server):
    """prof-asset-family select still exists in the professional tab."""
    _goto(page, live_server)
    _switch_to_professional(page)
    el = page.query_selector("#prof-asset-family")
    assert el is not None, "prof-asset-family missing from professional tab"


def test_PCS28_professional_requirements_checklist_still_present(page, live_server):
    """Requirements checklist panel still exists in the professional tab."""
    _goto(page, live_server)
    _switch_to_professional(page)
    el = page.query_selector("#es-req-panel")
    assert el is not None, "es-req-panel missing from professional tab"
