"""
PVS31-E01–E19 — Professional Valuation Section 3.1 Purpose Route Merge: E2E Browser Tests
Validates:
  - New visible layout (الغرض الرئيسي + المسار الفرعي)
  - Removed elements are NOT visible (المسار المنطقي, Valuation Purpose Router)
  - Dynamic subroute population works (mortgage_financing → subroutes appear)
  - No methodology options in purpose dropdown
  - Backend compat elements still in DOM (PVNEW05/06 not broken)

Navigation notes:
  - pvr-vis-* elements live inside ws-professional (the default active tab, lines ~4809-7699).
  - pvr-assignment-purpose (no vis) lives inside ws-professional-valuation (backoffice).
  - _goto_vis(): navigate to root — ws-professional is active (es-ws-active in HTML).
  - _goto_pv():  navigate to #professional-valuation — ws-professional-valuation is active.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _block(page: Page) -> None:
    page.route("**/api/**", lambda r: r.fulfill(
        status=200, body=b'{"ok":true,"requests":[]}', content_type="application/json"
    ))


def _goto_vis(page: Page, live_server: str) -> None:
    """Navigate to root page so ws-professional (user-facing) is visible."""
    _block(page)
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator('#ws-professional').wait_for(state="visible", timeout=10_000)


def _goto_pv(page: Page, live_server: str) -> None:
    """Navigate to backoffice workspace (for DOM-count tests like PVNEW05)."""
    _block(page)
    page.goto(f"{live_server}#professional-valuation", wait_until="domcontentloaded")
    page.locator('[data-testid="pro-val-workspace"]').wait_for(state="visible", timeout=10_000)


def _scroll_to(page: Page, selector: str) -> None:
    """Scroll element into view so Playwright can interact with it."""
    page.locator(selector).evaluate("el => el.scrollIntoView({block:'center'})")
    page.wait_for_timeout(200)


# ─── Tests ────────────────────────────────────────────────────────────────────

def test_PVS31_E01_section31_wrapper_visible(page: Page, live_server: str) -> None:
    """E01: pro-val-purpose-logical-section is present in DOM."""
    _goto_vis(page, live_server)
    el = page.locator('[data-testid="pro-val-purpose-logical-section"]')
    assert el.count() >= 1, "pro-val-purpose-logical-section not found"


def test_PVS31_E02_step1_title_in_dom(page: Page, live_server: str) -> None:
    """E02: Section heading 'الخطوة 1: لماذا يُطلب التقييم؟' is present in DOM text."""
    _goto_vis(page, live_server)
    section = page.locator('[data-testid="pro-val-purpose-logical-section"]')
    text = section.inner_text()
    assert "الخطوة 1" in text, f"'الخطوة 1' not found in section. Got: {text[:200]}"


def test_PVS31_E03_assignment_purpose_select_in_dom(page: Page, live_server: str) -> None:
    """E03: pvr-vis-assignment-purpose select exists in ws-professional."""
    _goto_vis(page, live_server)
    el = page.locator('#pvr-vis-assignment-purpose')
    assert el.count() >= 1, "pvr-vis-assignment-purpose not found"


def test_PVS31_E04_purpose_subroute_select_in_ws_professional(page: Page, live_server: str) -> None:
    """E04: pvr-vis-purpose-subroute select exists in ws-professional."""
    _goto_vis(page, live_server)
    el = page.locator('#pvr-vis-purpose-subroute')
    assert el.count() >= 1, "pvr-vis-purpose-subroute not found"


def test_PVS31_E05_purpose_subroute_placeholder(page: Page, live_server: str) -> None:
    """E05: Subroute dropdown shows 'اختر الغرض الرئيسي أولاً' before purpose selected."""
    _goto_vis(page, live_server)
    sel = page.locator('#pvr-vis-purpose-subroute')
    text = sel.inner_text()
    assert "اختر الغرض الرئيسي أولاً" in text, \
        f"Placeholder text missing. Got: {text}"


def test_PVS31_E06_logic_path_not_visible(page: Page, live_server: str) -> None:
    """E06: pvr-vis-purpose-logic-path select is NOT visible (wrapped in display:none)."""
    _goto_vis(page, live_server)
    el = page.locator('#pvr-vis-purpose-logic-path')
    assert el.count() >= 1, "pvr-vis-purpose-logic-path not in DOM"
    assert not el.first.is_visible(), "pvr-vis-purpose-logic-path should NOT be visible"


def test_PVS31_E07_valuation_purpose_router_not_visible(page: Page, live_server: str) -> None:
    """E07: pro-val-purpose-router-section (Valuation Purpose Router block) is NOT visible."""
    _goto_vis(page, live_server)
    el = page.locator('[data-testid="pro-val-purpose-router-section"]')
    assert el.count() >= 1, "pro-val-purpose-router-section removed from DOM — must be preserved"
    assert not el.first.is_visible(), "Valuation Purpose Router block should NOT be visible"


def test_PVS31_E08_purpose_route_select_not_visible(page: Page, live_server: str) -> None:
    """E08: prof-purpose-route (مسار الغرض) select is NOT visible (inside hidden block)."""
    _goto_vis(page, live_server)
    el = page.locator('#prof-purpose-route')
    if el.count() > 0:
        assert not el.first.is_visible(), "prof-purpose-route should NOT be visible"


def test_PVS31_E09_purpose_router_summary_not_visible(page: Page, live_server: str) -> None:
    """E09: pro-val-purpose-router-summary panel is NOT visible."""
    _goto_vis(page, live_server)
    el = page.locator('[data-testid="pro-val-purpose-router-summary"]')
    if el.count() > 0:
        assert not el.first.is_visible(), "Purpose router summary should NOT be visible"


def test_PVS31_E10_select_mortgage_financing_updates_subroutes(page: Page, live_server: str) -> None:
    """E10: Selecting mortgage_financing populates subroute options."""
    _goto_vis(page, live_server)
    _scroll_to(page, '#pvr-vis-assignment-purpose')
    page.locator('#pvr-vis-assignment-purpose').select_option("mortgage_financing")
    page.wait_for_timeout(400)
    options = page.locator('#pvr-vis-purpose-subroute option').all_text_contents()
    assert len(options) > 1, f"No subroutes for mortgage_financing. Got: {options}"
    all_text = " ".join(options)
    assert "ضمانات" in all_text or "تمويل" in all_text or "LTV" in all_text, \
        f"Expected mortgage subroutes. Got: {options}"


def test_PVS31_E11_collateral_valuation_subroute_present(page: Page, live_server: str) -> None:
    """E11: mortgage_financing subroutes include تقييم ضمانات التمويل."""
    _goto_vis(page, live_server)
    _scroll_to(page, '#pvr-vis-assignment-purpose')
    page.locator('#pvr-vis-assignment-purpose').select_option("mortgage_financing")
    page.wait_for_timeout(400)
    options = page.locator('#pvr-vis-purpose-subroute option').all_text_contents()
    assert any("ضمانات" in o for o in options), \
        f"تقييم ضمانات التمويل not found. Got: {options}"


def test_PVS31_E12_select_sale_purchase_updates_subroutes(page: Page, live_server: str) -> None:
    """E12: Selecting sale_purchase populates subroute options."""
    _goto_vis(page, live_server)
    _scroll_to(page, '#pvr-vis-assignment-purpose')
    page.locator('#pvr-vis-assignment-purpose').select_option("sale_purchase")
    page.wait_for_timeout(400)
    options = page.locator('#pvr-vis-purpose-subroute option').all_text_contents()
    assert len(options) > 1, f"No subroutes for sale_purchase. Got: {options}"


def test_PVS31_E13_seller_buyer_subroutes_present(page: Page, live_server: str) -> None:
    """E13: sale_purchase subroutes include seller and buyer options."""
    _goto_vis(page, live_server)
    _scroll_to(page, '#pvr-vis-assignment-purpose')
    page.locator('#pvr-vis-assignment-purpose').select_option("sale_purchase")
    page.wait_for_timeout(400)
    options = page.locator('#pvr-vis-purpose-subroute option').all_text_contents()
    all_text = " ".join(options)
    assert "بائع" in all_text or "مشتري" in all_text, \
        f"Seller/buyer options not found. Got: {options}"


def test_PVS31_E14_no_methodology_in_purpose_dropdown(page: Page, live_server: str) -> None:
    """E14: Assignment purpose dropdown does not contain DCF or sales_comparison."""
    _goto_vis(page, live_server)
    options = page.locator('#pvr-vis-assignment-purpose option').all_text_contents()
    all_text = " ".join(options).lower()
    assert "dcf" not in all_text, "DCF found in purpose dropdown — must not appear"
    assert "مقارنة المبيعات" not in all_text, "مقارنة المبيعات in purpose dropdown"


def test_PVS31_E15_no_basis_of_value_in_assignment_purpose(page: Page, live_server: str) -> None:
    """E15: market_value and fair_value are not option values in pvr-vis-assignment-purpose."""
    _goto_vis(page, live_server)
    opts = page.locator('#pvr-vis-assignment-purpose option').all()
    values = [o.get_attribute("value") or "" for o in opts]
    assert "market_value" not in values, "market_value in assignment_purpose options"
    assert "fair_value" not in values, "fair_value in assignment_purpose options"


def test_PVS31_E16_tax_appeal_subroutes_visible(page: Page, live_server: str) -> None:
    """E16: tax_appeal purpose populates subroutes with طعن ضريبة عقارية."""
    _goto_vis(page, live_server)
    _scroll_to(page, '#pvr-vis-assignment-purpose')
    page.locator('#pvr-vis-assignment-purpose').select_option("tax_appeal")
    page.wait_for_timeout(400)
    options = page.locator('#pvr-vis-purpose-subroute option').all_text_contents()
    assert any("طعن" in o or "ضريبة" in o for o in options), \
        f"Tax appeal subroutes missing. Got: {options}"


def test_PVS31_E17_partial_interest_subroutes_visible(page: Page, live_server: str) -> None:
    """E17: partial_interest_valuation populates subroutes with حصة أقلية etc."""
    _goto_vis(page, live_server)
    _scroll_to(page, '#pvr-vis-assignment-purpose')
    page.locator('#pvr-vis-assignment-purpose').select_option("partial_interest_valuation")
    page.wait_for_timeout(400)
    options = page.locator('#pvr-vis-purpose-subroute option').all_text_contents()
    assert any("أقلية" in o or "شائعة" in o or "انتفاع" in o for o in options), \
        f"Partial interest subroutes missing. Got: {options}"


def test_PVS31_E18_purpose_logic_path_in_dom_for_pvnew05(page: Page, live_server: str) -> None:
    """E18: pro-val-purpose-logic-path-select has count>=2 in DOM (PVNEW05 compat)."""
    _goto_pv(page, live_server)
    count = page.locator('[data-testid="pro-val-purpose-logic-path-select"]').count()
    assert count >= 2, \
        f"Expected >=2 instances of pro-val-purpose-logic-path-select, got {count}"


def test_PVS31_E19_purpose_subroute_select_option_works(page: Page, live_server: str) -> None:
    """E19: Can select a subroute value after picking financial_reporting purpose."""
    _goto_vis(page, live_server)
    _scroll_to(page, '#pvr-vis-assignment-purpose')
    page.locator('#pvr-vis-assignment-purpose').select_option("financial_reporting")
    page.wait_for_timeout(400)
    subroute_sel = page.locator('#pvr-vis-purpose-subroute')
    options = subroute_sel.locator('option').all()
    assert len(options) > 1, "No subroutes for financial_reporting"
    non_blank = [o for o in options if o.get_attribute("value")]
    if non_blank:
        subroute_sel.select_option(non_blank[0].get_attribute("value"))
        page.wait_for_timeout(200)
        val = subroute_sel.evaluate("el => el.value")
        assert val != "", f"Subroute selection did not register. Value: '{val}'"
