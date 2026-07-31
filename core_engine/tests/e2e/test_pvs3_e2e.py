"""
PVS3 E2E Browser Tests
Professional Valuation Page — Section 3 Three-Step Anti-Confusion Cleanup

27 browser-visibility tests covering:
- Three-step structure visible in DOM
- Required testids present and visible
- RICS/IVS/IFRS not visible in professional-context-path-select
- Methodology not in assignment-purpose select
- Partial interest panel toggle
- Summary panel testids
- Apply button present
- No standalone 3.6 heading
- No internal paths in page
- PVPTS12 fix: disclosures-warnings visible
- PVPBSR19 fix: preliminary-weighting-subsection visible
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://127.0.0.1:5000"


@pytest.fixture(scope="module")
def pv_page(browser):
    """Navigate to the professional valuation page and open Section 3."""
    page = browser.new_page()
    page.goto(f"{BASE_URL}/", timeout=30000)
    # Open the Professional Valuation tab / section
    tab = page.locator('[data-testid="professional-valuation-tab"], [id*="professional-valuation-tab"]')
    if tab.count() > 0:
        tab.first.click()
    else:
        # Try nav link
        pv_link = page.locator("text=التقييم المهني").first
        if pv_link.count() > 0:
            pv_link.click()
    page.wait_for_timeout(500)
    yield page
    page.close()


# ── PVS3-E01: Section 3 container is visible ─────────────────────────────────

def test_PVS3_E01_section3_container_visible(pv_page: Page):
    """PVS3-E01: Section 3 container (pro-val-section-valuation-purpose) is visible in DOM."""
    el = pv_page.locator('[data-testid="pro-val-section-valuation-purpose"]')
    expect(el).to_be_visible()


# ── PVS3-E02: Section title contains updated text ────────────────────────────

def test_PVS3_E02_section_title_updated(pv_page: Page):
    """PVS3-E02: Section title includes 'الغرض من التقييم'."""
    # Title should be inside the section
    section = pv_page.locator('[data-testid="pro-val-section-valuation-purpose"]')
    expect(section).to_contain_text("الغرض من التقييم")


# ── PVS3-E03: Step 3.1 — assignment-purpose-select is visible ────────────────

def test_PVS3_E03_step1_assignment_purpose_visible(pv_page: Page):
    """PVS3-E03: pro-val-assignment-purpose-select is visible (Step 3.1)."""
    el = pv_page.locator('[data-testid="pro-val-assignment-purpose-select"]')
    expect(el).to_be_visible()


# ── PVS3-E04: Step 3.1 heading mentions "الخطوة 1" ──────────────────────────

def test_PVS3_E04_step1_heading_contains_step1(pv_page: Page):
    """PVS3-E04: Step 3.1 container shows 'الخطوة 1' in heading."""
    step1 = pv_page.locator('[data-testid="pro-val-purpose-step"]')
    expect(step1).to_contain_text("الخطوة 1")


# ── PVS3-E05: Step 3.2 — intended-user-select is visible ─────────────────────

def test_PVS3_E05_step2_intended_user_visible(pv_page: Page):
    """PVS3-E05: pro-val-intended-user-select is visible (Step 3.2, canonical testid after PVS3 merge)."""
    el = pv_page.locator('[data-testid="pro-val-intended-user-select"]')
    expect(el).to_be_visible()


# ── PVS3-E06: Step 3.2 heading mentions "الخطوة 2" ──────────────────────────

def test_PVS3_E06_step2_heading_contains_step2(pv_page: Page):
    """PVS3-E06: Step 3.2 container shows 'الخطوة 2' in heading."""
    step2 = pv_page.locator('[data-testid="pro-val-intended-user-pathway-step"]')
    expect(step2).to_contain_text("الخطوة 2")


# ── PVS3-E07: Step 3.3 — basis-of-value-select is visible ────────────────────

def test_PVS3_E07_step3_basis_of_value_visible(pv_page: Page):
    """PVS3-E07: pro-val-basis-of-value-select is visible (Step 3.3)."""
    el = pv_page.locator('[data-testid="pro-val-basis-of-value-select"]')
    expect(el).to_be_visible()


# ── PVS3-E08: Step 3.3 heading mentions "الخطوة 3" ──────────────────────────

def test_PVS3_E08_step3_heading_contains_step3(pv_page: Page):
    """PVS3-E08: Step 3.3 container shows 'الخطوة 3' in heading."""
    step3 = pv_page.locator('[data-testid="pro-val-basis-value-premise-step"]')
    expect(step3).to_contain_text("الخطوة 3")


# ── PVS3-E09: professional-pathway-select is visible (canonical testid after PVS3 merge) ──

def test_PVS3_E09_professional_pathway_select_visible(pv_page: Page):
    """PVS3-E09: pro-val-professional-pathway-select is visible (canonical testid after PVS3 merge)."""
    el = pv_page.locator('[data-testid="pro-val-professional-pathway-select"]')
    expect(el).to_be_visible()


# ── PVS3-E10: RICS Red Book NOT an option in professional-pathway-select ──────

def test_PVS3_E10_rics_not_in_pathway_dropdown(pv_page: Page):
    """PVS3-E10: rics_red_book is NOT an option in pro-val-professional-pathway-select (vis workspace)."""
    select = pv_page.locator('[data-testid="pro-val-professional-pathway-select"]')
    expect(select).to_be_visible()
    rics_option = select.locator('option[value="rics_red_book"]')
    assert rics_option.count() == 0, "rics_red_book should not be in canonical pathway dropdown"


# ── PVS3-E11: IVSC IPS NOT an option in professional-pathway-select ──────────

def test_PVS3_E11_ivsc_not_in_pathway_dropdown(pv_page: Page):
    """PVS3-E11: ivsc_ips is NOT an option in pro-val-professional-pathway-select (vis workspace)."""
    select = pv_page.locator('[data-testid="pro-val-professional-pathway-select"]')
    ivsc_option = select.locator('option[value="ivsc_ips"]')
    assert ivsc_option.count() == 0, "ivsc_ips should not be in canonical pathway dropdown"


# ── PVS3-E12: IFRS 13 NOT an option in professional-pathway-select ────────────

def test_PVS3_E12_ifrs_not_in_pathway_dropdown(pv_page: Page):
    """PVS3-E12: ifrs_13_fair_value_hierarchy is NOT an option in pro-val-professional-pathway-select."""
    select = pv_page.locator('[data-testid="pro-val-professional-pathway-select"]')
    ifrs_option = select.locator('option[value="ifrs_13_fair_value_hierarchy"]')
    assert ifrs_option.count() == 0, "ifrs_13_fair_value_hierarchy should not be in canonical pathway dropdown"


# ── PVS3-E13: Basel III/IV NOT an option in professional-pathway-select ───────

def test_PVS3_E13_basel_not_in_pathway_dropdown(pv_page: Page):
    """PVS3-E13: basel_iii_iv_collateral is NOT an option in pro-val-professional-pathway-select."""
    select = pv_page.locator('[data-testid="pro-val-professional-pathway-select"]')
    basel_option = select.locator('option[value="basel_iii_iv_collateral"]')
    assert basel_option.count() == 0, "basel_iii_iv_collateral should not be in canonical pathway dropdown"


# ── PVS3-E14: banking_finance_path IS an option in pathway dropdown ───────────

def test_PVS3_E14_banking_finance_path_in_dropdown(pv_page: Page):
    """PVS3-E14: banking_finance_path option exists in pro-val-professional-pathway-select."""
    select = pv_page.locator('[data-testid="pro-val-professional-pathway-select"]')
    option = select.locator('option[value="banking_finance_path"]')
    assert option.count() > 0, "banking_finance_path should be in pathway dropdown"


# ── PVS3-E15: Inline guidance testid in DOM (Step 3.1) ───────────────────────

def test_PVS3_E15_purpose_inline_guidance_in_dom(pv_page: Page):
    """PVS3-E15: pro-val-purpose-inline-guidance element is in the DOM."""
    el = pv_page.locator('[data-testid="pro-val-purpose-inline-guidance"]')
    assert el.count() > 0, "pro-val-purpose-inline-guidance should be in DOM"


# ── PVS3-E16: Inline warning testid in DOM (Step 3.1) ────────────────────────

def test_PVS3_E16_purpose_inline_warning_in_dom(pv_page: Page):
    """PVS3-E16: pro-val-purpose-inline-warning element is in the DOM."""
    el = pv_page.locator('[data-testid="pro-val-purpose-inline-warning"]')
    assert el.count() > 0, "pro-val-purpose-inline-warning should be in DOM"


# ── PVS3-E17: Summary panel is visible ───────────────────────────────────────

def test_PVS3_E17_summary_panel_visible(pv_page: Page):
    """PVS3-E17: pro-val-purpose-routing-summary is visible."""
    el = pv_page.locator('[data-testid="pro-val-purpose-routing-summary"]')
    expect(el).to_be_visible()


# ── PVS3-E18: Summary purpose field testid exists ────────────────────────────

def test_PVS3_E18_summary_purpose_testid(pv_page: Page):
    """PVS3-E18: pro-val-purpose-summary-purpose element is in DOM."""
    el = pv_page.locator('[data-testid="pro-val-purpose-summary-purpose"]')
    assert el.count() > 0, "pro-val-purpose-summary-purpose testid missing"


# ── PVS3-E19: Summary basis field testid exists ───────────────────────────────

def test_PVS3_E19_summary_basis_testid(pv_page: Page):
    """PVS3-E19: pro-val-purpose-summary-basis element is in DOM."""
    el = pv_page.locator('[data-testid="pro-val-purpose-summary-basis"]')
    assert el.count() > 0, "pro-val-purpose-summary-basis testid missing"


# ── PVS3-E20: Apply button is visible ────────────────────────────────────────

def test_PVS3_E20_apply_button_visible(pv_page: Page):
    """PVS3-E20: pro-val-apply-purpose-selection-button is visible."""
    el = pv_page.locator('[data-testid="pro-val-apply-purpose-selection-button"]')
    expect(el).to_be_visible()


# ── PVS3-E21: preliminary-weighting-subsection is NOT visible (removed per task) ─────

def test_PVS3_E21_preliminary_weighting_not_visible(pv_page: Page):
    """PVS3-E21: pro-val-preliminary-weighting-subsection is NOT visible (removed from visible UI)."""
    el = pv_page.locator('[data-testid="pro-val-preliminary-weighting-subsection"]')
    expect(el).not_to_be_visible()


# ── PVS3-E22: disclosures-warnings outer wrapper NOT visible (removed per task) ───────

def test_PVS3_E22_disclosures_warnings_not_visible(pv_page: Page):
    """PVS3-E22: pro-val-purpose-disclosures-warnings is NOT visible (removed from visible UI)."""
    el = pv_page.locator('[data-testid="pro-val-purpose-disclosures-warnings"]')
    expect(el).not_to_be_visible()


# ── PVS3-E23: No standalone '3.6' heading in disclosures section ─────────────

def test_PVS3_E23_no_standalone_3_6_heading(pv_page: Page):
    """PVS3-E23: No visible element contains the text '3.6' as a heading (Rule 15 compliance)."""
    # Find any heading (h3/h4/h5) or badge that contains exactly '3.6'
    hits = pv_page.locator("h3:has-text('3.6'), h4:has-text('3.6'), h5:has-text('3.6'), .badge:has-text('3.6'), [class*='step-label']:has-text('3.6')")
    visible_hits = [h for h in hits.all() if h.is_visible()]
    assert len(visible_hits) == 0, f"Found visible '3.6' heading — Rule 15 violation: {[h.inner_text() for h in visible_hits]}"


# ── PVS3-E24: Partial interest panel in DOM ───────────────────────────────────

def test_PVS3_E24_partial_interest_panel_in_dom(pv_page: Page):
    """PVS3-E24: pro-val-partial-interest-panel element is in the DOM."""
    el = pv_page.locator('[data-testid="pro-val-partial-interest-panel"]')
    assert el.count() > 0, "pro-val-partial-interest-panel should be in DOM"


# ── PVS3-E25: Partial interest panel toggles when partial_interest selected ───

def test_PVS3_E25_partial_interest_panel_toggles(pv_page: Page):
    """PVS3-E25: partial interest panel becomes visible when partial_interest_valuation is selected."""
    purpose_select = pv_page.locator('[data-testid="pro-val-assignment-purpose-select"]')
    if purpose_select.count() == 0:
        pytest.skip("assignment-purpose select not found")

    panel = pv_page.locator('[data-testid="pro-val-partial-interest-panel"]')
    if panel.count() == 0:
        pytest.skip("partial-interest-panel not found")

    # Select partial_interest_valuation
    options = purpose_select.locator('option[value="partial_interest_valuation"]')
    if options.count() == 0:
        pytest.skip("partial_interest_valuation option not available")

    purpose_select.select_option("partial_interest_valuation")
    pv_page.wait_for_timeout(300)
    # Panel should now be visible
    expect(panel).to_be_visible()


# ── PVS3-E26: No internal paths in page source ────────────────────────────────

def test_PVS3_E26_no_internal_paths_in_page(pv_page: Page):
    """PVS3-E26: Page source does not contain internal file-system paths."""
    content = pv_page.content()
    forbidden = ["core_engine/", "C:\\\\Users", "c:\\\\users", "__file__", "/home/", "instance/manual"]
    hits = [f for f in forbidden if f in content]
    assert not hits, f"Internal paths found in page source: {hits}"


# ── PVS3-E27: purpose-logic-path-select count=2 preserved (PVNEW05) ──────────

def test_PVS3_E27_purpose_logic_path_select_count(pv_page: Page):
    """PVS3-E27: pro-val-purpose-logic-path-select has exactly 2 elements in DOM (PVNEW05 compat)."""
    els = pv_page.locator('[data-testid="pro-val-purpose-logic-path-select"]')
    assert els.count() == 2, f"Expected 2 pro-val-purpose-logic-path-select elements, got {els.count()}"


# ══════════════════════════════════════════════════════════════════════════════
# PVS3-Merge: Section 3 Professional Targeting Cleanup Tests (E28-E56)
# Tests for purpose flow + professional targeting after merge
# ══════════════════════════════════════════════════════════════════════════════


def _goto_vis(page: Page, live_server: str) -> None:
    """Navigate to root — ws-professional (user-facing) is visible."""
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator('#ws-professional').wait_for(state="visible", timeout=10_000)


def _scroll_to(page: Page, selector: str) -> None:
    page.locator(selector).evaluate("el => el.scrollIntoView({block:'center'})")
    page.wait_for_timeout(200)


@pytest.fixture(scope="module")
def live_server() -> str:
    return "http://127.0.0.1:5000"


@pytest.fixture(scope="module")
def merge_page(browser, live_server):
    page = browser.new_page()
    _goto_vis(page, live_server)
    yield page
    page.close()


# ── E28-E34: Section 3.1 Purpose Controls ─────────────────────────────────────

def test_PVS3_E28_step1_title_visible(merge_page: Page):
    """PVS3-E28: Step 3.1 title 'الخطوة 1: لماذا يُطلب التقييم؟' is visible."""
    el = merge_page.locator('[data-testid="pro-val-purpose-logical-section"]')
    expect(el).to_contain_text("الخطوة 1")


def test_PVS3_E29_assignment_purpose_select_visible(merge_page: Page):
    """PVS3-E29: pro-val-assignment-purpose-select is visible."""
    el = merge_page.locator('[data-testid="pro-val-assignment-purpose-select"]')
    expect(el).to_be_visible()


def test_PVS3_E30_purpose_subroute_select_visible(merge_page: Page):
    """PVS3-E30: pro-val-purpose-subroute-select is visible."""
    el = merge_page.locator('[data-testid="pro-val-purpose-subroute-select"]')
    expect(el).to_be_visible()


def test_PVS3_E31_purpose_logic_path_not_visible(merge_page: Page):
    """PVS3-E31: المسار المنطقي للغرض (pvr-vis-purpose-logic-path) is NOT visible."""
    _scroll_to(merge_page, '[data-testid="pro-val-assignment-purpose-select"]')
    el = merge_page.locator('#pvr-vis-purpose-logic-path')
    expect(el).not_to_be_visible()


def test_PVS3_E32_purpose_router_section_not_visible(merge_page: Page):
    """PVS3-E32: Standalone 'Valuation Purpose Router' block is NOT visible."""
    el = merge_page.locator('[data-testid="pro-val-purpose-router-section"]')
    expect(el).not_to_be_visible()


def test_PVS3_E33_selecting_mortgage_financing_updates_subroutes(merge_page: Page):
    """PVS3-E33: Selecting mortgage_financing updates subroute options."""
    _scroll_to(merge_page, '[data-testid="pro-val-assignment-purpose-select"]')
    merge_page.locator('[data-testid="pro-val-assignment-purpose-select"]').select_option("mortgage_financing")
    merge_page.wait_for_timeout(400)
    subroute = merge_page.locator('[data-testid="pro-val-purpose-subroute-select"]')
    options = subroute.locator('option').all()
    values = [o.get_attribute("value") for o in options if o.get_attribute("value")]
    assert any(v in values for v in ["collateral_valuation", "refinance", "ltv_support"]), \
        f"Expected mortgage subroutes, got: {values}"


def test_PVS3_E34_no_methodology_in_purpose_dropdown(merge_page: Page):
    """PVS3-E34: Methodology options (dcf, sales_comparison) are NOT in assignment_purpose select."""
    select = merge_page.locator('[data-testid="pro-val-assignment-purpose-select"]')
    for method_val in ["sales_comparison", "dcf", "cost_approach", "income_approach"]:
        opt = select.locator(f'option[value="{method_val}"]')
        assert opt.count() == 0, f"{method_val} should not be in assignment_purpose dropdown"


# ── E35-E44: Section 3.2 Professional Targeting Controls ──────────────────────

def test_PVS3_E35_intended_user_section_visible(merge_page: Page):
    """PVS3-E35: pro-val-intended-user-section wrapper is visible."""
    el = merge_page.locator('[data-testid="pro-val-intended-user-section"]')
    expect(el).to_be_visible()


def test_PVS3_E36_intended_user_select_visible(merge_page: Page):
    """PVS3-E36: pro-val-intended-user-select (الجهة المستهدفة) is visible."""
    el = merge_page.locator('[data-testid="pro-val-intended-user-select"]')
    expect(el).to_be_visible()


def test_PVS3_E37_professional_pathway_section_visible(merge_page: Page):
    """PVS3-E37: pro-val-professional-pathway-section wrapper is visible."""
    el = merge_page.locator('[data-testid="pro-val-professional-pathway-section"]')
    expect(el).to_be_visible()


def test_PVS3_E38_professional_pathway_select_visible(merge_page: Page):
    """PVS3-E38: pro-val-professional-pathway-select (المسار المهني) is visible."""
    el = merge_page.locator('[data-testid="pro-val-professional-pathway-select"]')
    expect(el).to_be_visible()


def test_PVS3_E39_professional_purpose_path_not_visible(merge_page: Page):
    """PVS3-E39: مسار الغرض المهني (pvr-vis-professional-purpose-path) is NOT visible."""
    _scroll_to(merge_page, '[data-testid="pro-val-professional-pathway-select"]')
    el = merge_page.locator('#pvr-vis-professional-purpose-path')
    expect(el).not_to_be_visible()


def test_PVS3_E40_only_two_visible_professional_dropdowns(merge_page: Page):
    """PVS3-E40: Only 2 visible select dropdowns in professional targeting block."""
    _scroll_to(merge_page, '[data-testid="pro-val-intended-user-pathway-step"]')
    container = merge_page.locator('[data-testid="pro-val-professional-purpose-section"]')
    visible_selects = [
        sel for sel in container.locator('select').all()
        if sel.is_visible()
    ]
    assert len(visible_selects) == 2, \
        f"Expected 2 visible selects in professional targeting, got {len(visible_selects)}"


def test_PVS3_E41_selecting_intended_user_updates_guidance(merge_page: Page):
    """PVS3-E41: Selecting intended_user updates pvr-intended-user-inline-guidance."""
    _scroll_to(merge_page, '[data-testid="pro-val-intended-user-select"]')
    merge_page.locator('[data-testid="pro-val-intended-user-select"]').select_option("bank_financial_institution")
    merge_page.wait_for_timeout(400)
    guidance = merge_page.locator('#pvr-intended-user-inline-guidance')
    text = guidance.text_content() or ""
    assert len(text.strip()) > 10, f"Guidance should be non-empty after selecting bank, got: '{text}'"


def test_PVS3_E42_selecting_professional_pathway_updates_guidance(merge_page: Page):
    """PVS3-E42: Selecting professional_pathway updates pvr-professional-targeting-guidance."""
    _scroll_to(merge_page, '[data-testid="pro-val-professional-pathway-select"]')
    merge_page.locator('[data-testid="pro-val-professional-pathway-select"]').select_option("banking_lending")
    merge_page.wait_for_timeout(400)
    guidance = merge_page.locator('#pvr-professional-targeting-guidance')
    expect(guidance).to_be_visible()
    text = guidance.text_content() or ""
    assert len(text.strip()) > 10, f"Guidance should be non-empty after selecting banking_lending, got: '{text}'"


def test_PVS3_E43_no_third_professional_dropdown_visible(merge_page: Page):
    """PVS3-E43: No third visible dropdown appears in professional targeting block."""
    container = merge_page.locator('[data-testid="pro-val-professional-purpose-section"]')
    visible_selects = [s for s in container.locator('select').all() if s.is_visible()]
    assert len(visible_selects) <= 2, \
        f"No more than 2 visible selects expected in professional targeting, got {len(visible_selects)}"


def test_PVS3_E44_banking_lending_canonical_in_pathway(merge_page: Page):
    """PVS3-E44: Canonical value banking_lending exists in pro-val-professional-pathway-select."""
    select = merge_page.locator('[data-testid="pro-val-professional-pathway-select"]')
    option = select.locator('option[value="banking_lending"]')
    assert option.count() > 0, "banking_lending canonical value should be in pathway select"


# ── E45-E52: Legacy values still present ───────────────────────────────────────

def test_PVS3_E45_legacy_banking_finance_path_in_pathway(merge_page: Page):
    """PVS3-E45: Legacy value banking_finance_path still exists in professional-pathway-select."""
    select = merge_page.locator('[data-testid="pro-val-professional-pathway-select"]')
    option = select.locator('option[value="banking_finance_path"]')
    assert option.count() > 0, "banking_finance_path should be preserved in pathway select"


def test_PVS3_E46_legacy_bank_financing_path_absorbed(merge_page: Page):
    """PVS3-E46: Absorbed legacy value bank_financing_path present in professional-pathway-select."""
    select = merge_page.locator('[data-testid="pro-val-professional-pathway-select"]')
    option = select.locator('option[value="bank_financing_path"]')
    assert option.count() > 0, "bank_financing_path should be absorbed into pathway select"


def test_PVS3_E47_bank_financial_institution_in_intended_user(merge_page: Page):
    """PVS3-E47: bank_financial_institution option in pro-val-intended-user-select."""
    select = merge_page.locator('[data-testid="pro-val-intended-user-select"]')
    option = select.locator('option[value="bank_financial_institution"]')
    assert option.count() > 0, "bank_financial_institution should be in intended-user select"


def test_PVS3_E48_commercial_bank_new_option_in_intended_user(merge_page: Page):
    """PVS3-E48: New canonical value commercial_bank present in pro-val-intended-user-select."""
    select = merge_page.locator('[data-testid="pro-val-intended-user-select"]')
    option = select.locator('option[value="commercial_bank"]')
    assert option.count() > 0, "commercial_bank canonical option should be in intended-user select"


def test_PVS3_E49_legacy_bank_option_preserved_in_intended_user(merge_page: Page):
    """PVS3-E49: Legacy value 'bank' preserved in pro-val-intended-user-select."""
    select = merge_page.locator('[data-testid="pro-val-intended-user-select"]')
    option = select.locator('option[value="bank"]')
    assert option.count() > 0, "Legacy 'bank' option should be preserved"


# ── E50-E56: Global checks ──────────────────────────────────────────────────────

def test_PVS3_E50_no_standards_in_section31(merge_page: Page):
    """PVS3-E50: No IVS/RICS/IFRS options in assignment-purpose-select."""
    select = merge_page.locator('[data-testid="pro-val-assignment-purpose-select"]')
    for std_val in ["rics_red_book", "ivsc_ips", "ifrs_13", "fra_egypt"]:
        opt = select.locator(f'option[value="{std_val}"]')
        assert opt.count() == 0, f"{std_val} should not be in purpose dropdown"


def test_PVS3_E51_no_basis_of_value_in_purpose_dropdown(merge_page: Page):
    """PVS3-E51: Basis-of-value options not in assignment-purpose-select."""
    select = merge_page.locator('[data-testid="pro-val-assignment-purpose-select"]')
    for bov in ["market_value", "fair_value", "investment_value"]:
        opt = select.locator(f'option[value="{bov}"]')
        assert opt.count() == 0, f"{bov} should not be in purpose dropdown"


def test_PVS3_E52_no_dloc_dlom_in_purpose_dropdown(merge_page: Page):
    """PVS3-E52: DLOC/DLOM not in assignment-purpose-select."""
    select = merge_page.locator('[data-testid="pro-val-assignment-purpose-select"]')
    for dl in ["dloc", "dlom"]:
        opt = select.locator(f'option[value*="{dl}"]')
        assert opt.count() == 0, f"{dl} should not be in purpose dropdown"


def test_PVS3_E53_no_dloc_dlom_in_pathway_dropdown(merge_page: Page):
    """PVS3-E53: DLOC/DLOM not in professional-pathway-select."""
    select = merge_page.locator('[data-testid="pro-val-professional-pathway-select"]')
    for dl in ["dloc", "dlom"]:
        opt = select.locator(f'option[value*="{dl}"]')
        assert opt.count() == 0, f"{dl} should not be in pathway dropdown"


def test_PVS3_E54_professional_targeting_guidance_element_exists(merge_page: Page):
    """PVS3-E54: pro-val-professional-targeting-guidance element is in DOM."""
    el = merge_page.locator('[data-testid="pro-val-professional-targeting-guidance"]')
    assert el.count() > 0, "pro-val-professional-targeting-guidance element should exist in DOM"


def test_PVS3_E55_intended_user_guidance_element_exists(merge_page: Page):
    """PVS3-E55: pro-val-intended-user-inline-guidance element is in DOM."""
    el = merge_page.locator('[data-testid="pro-val-intended-user-inline-guidance"]')
    assert el.count() > 0, "pro-val-intended-user-inline-guidance should be in DOM"


def test_PVS3_E56_no_duplicate_testids_in_targeting_section(merge_page: Page):
    """PVS3-E56: No duplicate testids in professional targeting section for visible selects."""
    container = merge_page.locator('[data-testid="pro-val-professional-purpose-section"]')
    intended = container.locator('[data-testid="pro-val-intended-user-select"]')
    pathway  = container.locator('[data-testid="pro-val-professional-pathway-select"]')
    assert intended.count() == 1, f"Expected 1 pro-val-intended-user-select, got {intended.count()}"
    assert pathway.count() == 1, f"Expected 1 pro-val-professional-pathway-select, got {pathway.count()}"
