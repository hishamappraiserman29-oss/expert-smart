"""
PVASR E2E Browser Tests — Professional Valuation: Applied Valuation Standards (Section 4)
Tests: PVASR01–PVASR21
All tests use live_server fixture and real Playwright assertions.
"""
import pytest
from playwright.sync_api import Page, expect


def _goto(page: Page, live_server: str) -> None:
    page.route("**/api/**", lambda r: r.fulfill(
        status=200, body=b'{"ok":true}', content_type="application/json"
    ))
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator('[data-testid="professional-wizard"]').wait_for(
        state="visible", timeout=12_000
    )


def _sec4(page: Page):
    return page.locator('#ws-professional [data-testid="pro-val-section-applied-valuation-standards"]')


# ── PVASR01: Section 4 visible ────────────────────────────────────────────
@pytest.mark.e2e
def test_PVASR01_section4_visible(page: Page, live_server: str) -> None:
    """PVASR01: Section 4 (معايير التقييم المطبقة) is visible."""
    _goto(page, live_server)
    expect(_sec4(page)).to_be_visible()


# ── PVASR02: Core standards subsection visible ────────────────────────────
@pytest.mark.e2e
def test_PVASR02_core_standards_subsection_visible(page: Page, live_server: str) -> None:
    """PVASR02: 4.1 core standards subsection is visible."""
    _goto(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-standards-core-subsection"]')
    expect(el).to_be_visible()


# ── PVASR03: IVS 2025 checkbox visible ───────────────────────────────────
@pytest.mark.e2e
def test_PVASR03_ivs_2025_checkbox_visible(page: Page, live_server: str) -> None:
    """PVASR03: IVS 2025 checkbox label is visible."""
    _goto(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-standard-ivs-2025"]')
    expect(el).to_be_visible()


# ── PVASR04: RICS Red Book 2025 checkbox visible ─────────────────────────
@pytest.mark.e2e
def test_PVASR04_rics_checkbox_visible(page: Page, live_server: str) -> None:
    """PVASR04: RICS Red Book 2025 checkbox label is visible."""
    _goto(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-standard-rics-red-book-2025"]')
    expect(el).to_be_visible()


# ── PVASR05: IFRS 13 checkbox visible ────────────────────────────────────
@pytest.mark.e2e
def test_PVASR05_ifrs_13_checkbox_visible(page: Page, live_server: str) -> None:
    """PVASR05: IFRS 13 checkbox label is visible."""
    _goto(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-standard-ifrs-13"]')
    expect(el).to_be_visible()


# ── PVASR06: FRA Egypt checkbox visible ──────────────────────────────────
@pytest.mark.e2e
def test_PVASR06_fra_egypt_checkbox_visible(page: Page, live_server: str) -> None:
    """PVASR06: FRA Egypt checkbox label is visible."""
    _goto(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-standard-fra-egypt"]')
    expect(el).to_be_visible()


# ── PVASR07: Local reference subsection visible ───────────────────────────
@pytest.mark.e2e
def test_PVASR07_local_reference_subsection_visible(page: Page, live_server: str) -> None:
    """PVASR07: 4.2 local reference subsection is visible."""
    _goto(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-local-reference-subsection"]')
    expect(el).to_be_visible()


# ── PVASR08: jurisdiction country select visible ──────────────────────────
@pytest.mark.e2e
def test_PVASR08_jurisdiction_country_select_visible(page: Page, live_server: str) -> None:
    """PVASR08: jurisdiction country select is visible."""
    _goto(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-jurisdiction-country-select"]')
    expect(el).to_be_visible()


# ── PVASR09: IVS reference select visible ────────────────────────────────
@pytest.mark.e2e
def test_PVASR09_ivs_reference_select_visible(page: Page, live_server: str) -> None:
    """PVASR09: IVS reference select (4.3) is visible."""
    _goto(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-ivs-reference-select"]')
    expect(el).to_be_visible()


# ── PVASR10: IFRS fair value level select visible ─────────────────────────
@pytest.mark.e2e
def test_PVASR10_ifrs_fair_value_level_select_visible(page: Page, live_server: str) -> None:
    """PVASR10: IFRS fair value level select (4.3) is visible."""
    _goto(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-ifrs-fair-value-level-select"]')
    expect(el).to_be_visible()


# ── PVASR11: compliance disclosure level select visible ───────────────────
@pytest.mark.e2e
def test_PVASR11_compliance_disclosure_level_visible(page: Page, live_server: str) -> None:
    """PVASR11: compliance disclosure level select (4.4) is visible."""
    _goto(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-compliance-disclosure-level-select"]')
    expect(el).to_be_visible()


# ── PVASR12: compliance status badge visible ──────────────────────────────
@pytest.mark.e2e
def test_PVASR12_compliance_status_badge_visible(page: Page, live_server: str) -> None:
    """PVASR12: compliance status badge (4.5) is visible."""
    _goto(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-compliance-status-badge"]')
    expect(el).to_be_visible()


# ── PVASR13: required disclosures list visible ────────────────────────────
@pytest.mark.e2e
def test_PVASR13_required_disclosures_list_visible(page: Page, live_server: str) -> None:
    """PVASR13: required disclosures list (4.5) is visible."""
    _goto(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-required-disclosures-list"]')
    expect(el).to_be_visible()


# ── PVASR14: standards warnings list visible ──────────────────────────────
@pytest.mark.e2e
def test_PVASR14_standards_warnings_list_visible(page: Page, live_server: str) -> None:
    """PVASR14: standards warnings list (4.5) is visible."""
    _goto(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-standards-warnings-list"]')
    expect(el).to_be_visible()


# ── PVASR15: report guidance subsection visible ───────────────────────────
@pytest.mark.e2e
def test_PVASR15_report_guidance_subsection_visible(page: Page, live_server: str) -> None:
    """PVASR15: 4.6 report guidance subsection is visible."""
    _goto(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-standards-report-guidance-subsection"]')
    expect(el).to_be_visible()


# ── PVASR16: checking IVS 2025 shows IVS guidance panel ──────────────────
@pytest.mark.e2e
def test_PVASR16_ivs_checkbox_shows_guidance(page: Page, live_server: str) -> None:
    """PVASR16: checking IVS 2025 checkbox shows IVS guidance panel."""
    _goto(page, live_server)
    checkbox = page.locator('#ws-professional [data-testid="pro-val-standard-ivs-2025"] input[type="checkbox"]')
    panel = page.locator('#pvr-ivs-guidance-panel')
    expect(panel).to_be_hidden()
    checkbox.check()
    expect(panel).to_be_visible()


# ── PVASR17: checking certified target shows gate warning ─────────────────
@pytest.mark.e2e
def test_PVASR17_certified_target_shows_gate_warning(page: Page, live_server: str) -> None:
    """PVASR17: selecting certified_report_ready target shows certification gate warning."""
    _goto(page, live_server)
    sel = page.locator('#ws-professional [data-testid="pro-val-compliance-target-select"]')
    warning = page.locator('[data-testid="pro-val-certification-gate-warning"]')
    expect(warning).to_be_hidden()
    sel.select_option("certified_report_ready")
    expect(warning).to_be_visible()


# ── PVASR18: selecting limited_disclosure shows advisory warning ──────────
@pytest.mark.e2e
def test_PVASR18_limited_disclosure_shows_warning(page: Page, live_server: str) -> None:
    """PVASR18: selecting limited_disclosure shows advisory warning."""
    _goto(page, live_server)
    sel = page.locator('#ws-professional [data-testid="pro-val-compliance-disclosure-level-select"]')
    warning = page.locator('[data-testid="pro-val-limited-disclosure-warning"]')
    expect(warning).to_be_hidden()
    sel.select_option("limited_disclosure")
    expect(warning).to_be_visible()


# ── PVASR19: no final compliance claim in DOM ─────────────────────────────
@pytest.mark.e2e
def test_PVASR19_no_final_compliance_claim(page: Page, live_server: str) -> None:
    """PVASR19: no claim of final official compliance appears in Section 4."""
    _goto(page, live_server)
    sec4 = _sec4(page)
    text = sec4.text_content() or ""
    forbidden = ["ممتثل رسمياً", "معتمد رسمياً", "final compliance", "officially certified"]
    for f in forbidden:
        assert f not in text, f"Forbidden text found: {f}"


# ── PVASR20: no internal paths in DOM ────────────────────────────────────
@pytest.mark.e2e
def test_PVASR20_no_internal_paths_in_dom(page: Page, live_server: str) -> None:
    """PVASR20: no internal file paths exposed in Section 4 DOM."""
    _goto(page, live_server)
    sec4 = _sec4(page)
    text = sec4.text_content() or ""
    assert "C:\\" not in text
    assert "expert_smart1" not in text
    assert "/home/" not in text


# ── PVASR21: no duplicate testids in Section 4 ───────────────────────────
@pytest.mark.e2e
def test_PVASR21_no_duplicate_testids(page: Page, live_server: str) -> None:
    """PVASR21: all Section 4 testids are unique (no duplicates)."""
    _goto(page, live_server)
    testids = [
        "pro-val-standards-core-subsection",
        "pro-val-selected-standards-control",
        "pro-val-standard-ivs-2025",
        "pro-val-standard-rics-red-book-2025",
        "pro-val-standard-ifrs-13",
        "pro-val-standard-fra-egypt",
        "pro-val-standard-gcc",
        "pro-val-standard-custom-local",
        "pro-val-standard-uspap-checkbox",
        "pro-val-standard-basel-iii-checkbox",
        "pro-val-local-reference-subsection",
        "pro-val-standards-reference-subsection",
        "pro-val-compliance-level-subsection",
        "pro-val-compliance-status-subsection",
        "pro-val-standards-report-guidance-subsection",
    ]
    for tid in testids:
        count = page.locator(f'[data-testid="{tid}"]').count()
        assert count == 1, f"Testid {tid} has count {count}, expected 1"


# ── PVASR22: USPAP checkbox visible ──────────────────────────────────────────
@pytest.mark.e2e
def test_PVASR22_uspap_checkbox_visible(page: Page, live_server: str) -> None:
    """PVASR22: USPAP checkbox is visible in Section 4 professional standards category."""
    _goto(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-standard-uspap-checkbox"]')
    expect(el).to_be_visible()


# ── PVASR23: Basel III checkbox visible ──────────────────────────────────────
@pytest.mark.e2e
def test_PVASR23_basel_iii_checkbox_visible(page: Page, live_server: str) -> None:
    """PVASR23: Basel III checkbox is visible in Section 4 risk/banking category."""
    _goto(page, live_server)
    el = page.locator('#ws-professional [data-testid="pro-val-standard-basel-iii-checkbox"]')
    expect(el).to_be_visible()


# ── PVASR24: USPAP under professional standards category ─────────────────────
@pytest.mark.e2e
def test_PVASR24_uspap_under_professional_category(page: Page, live_server: str) -> None:
    """PVASR24: USPAP checkbox is inside the professional valuation standards category."""
    _goto(page, live_server)
    cat = page.locator('#ws-professional [data-testid="pro-val-standards-professional-category"]')
    expect(cat).to_be_visible()
    uspap = cat.locator('[data-testid="pro-val-standard-uspap-checkbox"]')
    expect(uspap).to_be_visible()


# ── PVASR25: Basel III under risk-banking category ───────────────────────────
@pytest.mark.e2e
def test_PVASR25_basel_under_risk_banking_category(page: Page, live_server: str) -> None:
    """PVASR25: Basel III checkbox is inside the risk/banking/collateral frameworks category."""
    _goto(page, live_server)
    cat = page.locator('#ws-professional [data-testid="pro-val-standards-risk-banking-category"]')
    expect(cat).to_be_visible()
    basel = cat.locator('[data-testid="pro-val-standard-basel-iii-checkbox"]')
    expect(basel).to_be_visible()


# ── PVASR26: Selecting USPAP shows details panel ─────────────────────────────
@pytest.mark.e2e
def test_PVASR26_uspap_checkbox_shows_details_panel(page: Page, live_server: str) -> None:
    """PVASR26: checking USPAP shows the USPAP details panel."""
    _goto(page, live_server)
    checkbox = page.locator('#ws-professional [data-testid="pro-val-standard-uspap-checkbox"] input[type="checkbox"]')
    panel = page.locator('[data-testid="pro-val-uspap-details-panel"]')
    expect(panel).to_be_hidden()
    checkbox.check()
    expect(panel).to_be_visible()


# ── PVASR27: USPAP advisory notice visible when USPAP selected ────────────────
@pytest.mark.e2e
def test_PVASR27_uspap_advisory_notice_visible(page: Page, live_server: str) -> None:
    """PVASR27: USPAP advisory notice is visible after checking USPAP."""
    _goto(page, live_server)
    checkbox = page.locator('#ws-professional [data-testid="pro-val-standard-uspap-checkbox"] input[type="checkbox"]')
    checkbox.check()
    notice = page.locator('[data-testid="pro-val-uspap-advisory-notice"]')
    expect(notice).to_be_visible()


# ── PVASR28: Selecting Basel III shows details panel ─────────────────────────
@pytest.mark.e2e
def test_PVASR28_basel_checkbox_shows_details_panel(page: Page, live_server: str) -> None:
    """PVASR28: checking Basel III shows the Basel III details panel."""
    _goto(page, live_server)
    checkbox = page.locator('#ws-professional [data-testid="pro-val-standard-basel-iii-checkbox"] input[type="checkbox"]')
    panel = page.locator('[data-testid="pro-val-basel-details-panel"]')
    expect(panel).to_be_hidden()
    checkbox.check()
    expect(panel).to_be_visible()


# ── PVASR29: Basel advisory notice visible when Basel III selected ────────────
@pytest.mark.e2e
def test_PVASR29_basel_advisory_notice_visible(page: Page, live_server: str) -> None:
    """PVASR29: Basel III advisory notice is visible after checking Basel III."""
    _goto(page, live_server)
    checkbox = page.locator('#ws-professional [data-testid="pro-val-standard-basel-iii-checkbox"] input[type="checkbox"]')
    checkbox.check()
    notice = page.locator('[data-testid="pro-val-basel-advisory-notice"]')
    expect(notice).to_be_visible()


# ── PVASR30: Basel LTV field visible in details panel ────────────────────────
@pytest.mark.e2e
def test_PVASR30_basel_ltv_field_visible(page: Page, live_server: str) -> None:
    """PVASR30: Basel III LTV input is visible inside details panel after checking Basel III."""
    _goto(page, live_server)
    checkbox = page.locator('#ws-professional [data-testid="pro-val-standard-basel-iii-checkbox"] input[type="checkbox"]')
    checkbox.check()
    ltv = page.locator('[data-testid="pro-val-basel-ltv-input"]')
    expect(ltv).to_be_visible()


# ── PVASR31: Basel collateral value field visible ─────────────────────────────
@pytest.mark.e2e
def test_PVASR31_basel_collateral_value_visible(page: Page, live_server: str) -> None:
    """PVASR31: Basel III collateral value input is visible inside details panel."""
    _goto(page, live_server)
    checkbox = page.locator('#ws-professional [data-testid="pro-val-standard-basel-iii-checkbox"] input[type="checkbox"]')
    checkbox.check()
    cv = page.locator('[data-testid="pro-val-basel-collateral-value-input"]')
    expect(cv).to_be_visible()


# ── PVASR32: Basel credit risk rating select visible ─────────────────────────
@pytest.mark.e2e
def test_PVASR32_basel_credit_risk_rating_visible(page: Page, live_server: str) -> None:
    """PVASR32: Basel III credit risk rating select is visible inside details panel."""
    _goto(page, live_server)
    checkbox = page.locator('#ws-professional [data-testid="pro-val-standard-basel-iii-checkbox"] input[type="checkbox"]')
    checkbox.check()
    cr = page.locator('[data-testid="pro-val-basel-credit-risk-rating-select"]')
    expect(cr).to_be_visible()


# ── PVASR33: Basel III not shown as pure valuation standard (category notice) ─
@pytest.mark.e2e
def test_PVASR33_basel_not_pure_valuation_standard_notice(page: Page, live_server: str) -> None:
    """PVASR33: Basel III details panel shows it is not a pure valuation standard."""
    _goto(page, live_server)
    checkbox = page.locator('#ws-professional [data-testid="pro-val-standard-basel-iii-checkbox"] input[type="checkbox"]')
    checkbox.check()
    panel = page.locator('[data-testid="pro-val-basel-details-panel"]')
    text = panel.text_content() or ""
    assert "معيار تقييم عقاري" in text or "مصرفي" in text or "risk" in text.lower(), \
        "Basel III panel should indicate it is not a pure valuation standard"


# ── PVASR34: USPAP details panel hidden by default ───────────────────────────
@pytest.mark.e2e
def test_PVASR34_uspap_panel_hidden_by_default(page: Page, live_server: str) -> None:
    """PVASR34: USPAP details panel is hidden by default before checkbox is checked."""
    _goto(page, live_server)
    panel = page.locator('[data-testid="pro-val-uspap-details-panel"]')
    expect(panel).to_be_hidden()


# ── PVASR35: Basel details panel hidden by default ───────────────────────────
@pytest.mark.e2e
def test_PVASR35_basel_panel_hidden_by_default(page: Page, live_server: str) -> None:
    """PVASR35: Basel III details panel is hidden by default before checkbox is checked."""
    _goto(page, live_server)
    panel = page.locator('[data-testid="pro-val-basel-details-panel"]')
    expect(panel).to_be_hidden()


# ── PVASR36: Advisory notice always visible (standards advisory) ──────────────
@pytest.mark.e2e
def test_PVASR36_standards_advisory_notice_always_visible(page: Page, live_server: str) -> None:
    """PVASR36: Section 4 advisory notice is always visible."""
    _goto(page, live_server)
    notice = page.locator('#ws-professional [data-testid="pro-val-standards-advisory-notice"]')
    expect(notice).to_be_visible()


# ── PVASR37: Professional standards category visible ─────────────────────────
@pytest.mark.e2e
def test_PVASR37_professional_category_visible(page: Page, live_server: str) -> None:
    """PVASR37: Professional valuation standards category is visible."""
    _goto(page, live_server)
    cat = page.locator('#ws-professional [data-testid="pro-val-standards-professional-category"]')
    expect(cat).to_be_visible()


# ── PVASR38: Financial reporting category visible ────────────────────────────
@pytest.mark.e2e
def test_PVASR38_financial_reporting_category_visible(page: Page, live_server: str) -> None:
    """PVASR38: Financial reporting standards category is visible."""
    _goto(page, live_server)
    cat = page.locator('#ws-professional [data-testid="pro-val-standards-financial-reporting-category"]')
    expect(cat).to_be_visible()


# ── PVASR39: Local regulatory category visible ───────────────────────────────
@pytest.mark.e2e
def test_PVASR39_local_regulatory_category_visible(page: Page, live_server: str) -> None:
    """PVASR39: Local/regulatory references category is visible."""
    _goto(page, live_server)
    cat = page.locator('#ws-professional [data-testid="pro-val-standards-local-regulatory-category"]')
    expect(cat).to_be_visible()


# ── PVASR40: Risk banking category visible ───────────────────────────────────
@pytest.mark.e2e
def test_PVASR40_risk_banking_category_visible(page: Page, live_server: str) -> None:
    """PVASR40: Risk/banking/collateral frameworks category is visible."""
    _goto(page, live_server)
    cat = page.locator('#ws-professional [data-testid="pro-val-standards-risk-banking-category"]')
    expect(cat).to_be_visible()


# ── PVASR41: No standalone Section 3.6 warnings visible (already removed) ────
@pytest.mark.e2e
def test_PVASR41_no_standalone_sec36_warnings(page: Page, live_server: str) -> None:
    """PVASR41: Section 3.6 dynamic disclosures/warnings block is not visible (removed)."""
    _goto(page, live_server)
    el = page.locator('[data-testid="pro-val-purpose-disclosures-warnings"]')
    expect(el).not_to_be_visible()


# ── PVASR42: No internal paths in Section 4 DOM ──────────────────────────────
@pytest.mark.e2e
def test_PVASR42_no_internal_paths_in_section4(page: Page, live_server: str) -> None:
    """PVASR42: No internal file paths exposed in Section 4 DOM text."""
    _goto(page, live_server)
    sec4 = _sec4(page)
    text = sec4.text_content() or ""
    assert "C:\\" not in text
    assert "expert_smart1" not in text


# ── PVASR43: USPAP use case select has valid options ─────────────────────────
@pytest.mark.e2e
def test_PVASR43_uspap_use_case_select_options(page: Page, live_server: str) -> None:
    """PVASR43: USPAP use case select has expected options after panel is shown."""
    _goto(page, live_server)
    checkbox = page.locator('#ws-professional [data-testid="pro-val-standard-uspap-checkbox"] input[type="checkbox"]')
    checkbox.check()
    sel = page.locator('[data-testid="pro-val-uspap-use-case-select"]')
    expect(sel).to_be_visible()
    sel.select_option("appraisal_report")
    assert sel.input_value() == "appraisal_report"


# ── PVASR44: Basel III use case select has valid options ──────────────────────
@pytest.mark.e2e
def test_PVASR44_basel_use_case_select_options(page: Page, live_server: str) -> None:
    """PVASR44: Basel III use case select has expected options after panel is shown."""
    _goto(page, live_server)
    checkbox = page.locator('#ws-professional [data-testid="pro-val-standard-basel-iii-checkbox"] input[type="checkbox"]')
    checkbox.check()
    sel = page.locator('[data-testid="pro-val-basel-use-case-select"]')
    expect(sel).to_be_visible()
    sel.select_option("collateral_valuation")
    assert sel.input_value() == "collateral_valuation"


# ── PVASR45: Compliance summary remains advisory after USPAP/Basel selected ───
@pytest.mark.e2e
def test_PVASR45_compliance_remains_advisory(page: Page, live_server: str) -> None:
    """PVASR45: compliance status badge remains advisory (not final certification) after selecting USPAP+Basel."""
    _goto(page, live_server)
    page.locator('#ws-professional [data-testid="pro-val-standard-uspap-checkbox"] input[type="checkbox"]').check()
    page.locator('#ws-professional [data-testid="pro-val-standard-basel-iii-checkbox"] input[type="checkbox"]').check()
    badge = page.locator('[data-testid="pro-val-compliance-status-badge"]')
    expect(badge).to_be_visible()
    text = badge.text_content() or ""
    forbidden = ["ممتثل رسمياً", "معتمد رسمياً", "final compliance", "officially certified"]
    for f in forbidden:
        assert f not in text, f"Forbidden compliance claim: {f}"


# ── PVASR46: USPAP is NOT shown inside risk-banking category ─────────────────
@pytest.mark.e2e
def test_PVASR46_uspap_not_in_risk_banking_category(page: Page, live_server: str) -> None:
    """PVASR46: USPAP checkbox is NOT inside the risk/banking category."""
    _goto(page, live_server)
    risk_cat = page.locator('#ws-professional [data-testid="pro-val-standards-risk-banking-category"]')
    uspap_in_risk = risk_cat.locator('[data-testid="pro-val-standard-uspap-checkbox"]')
    assert uspap_in_risk.count() == 0, "USPAP must not be inside the risk/banking category"
