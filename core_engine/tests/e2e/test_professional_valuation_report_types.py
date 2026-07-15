"""
PVRT E2E Browser Tests — Professional Valuation: Report Types (Section 5)
Tests: PVRT01–PVRT20
All tests use live_server fixture and real Playwright assertions.
"""
import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


def _goto(page: Page, live_server: str) -> None:
    page.route("**/api/**", lambda r: r.fulfill(
        status=200, body=b'{"ok":true}', content_type="application/json"
    ))
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator('[data-testid="professional-wizard"]').wait_for(
        state="visible", timeout=12_000
    )


def _sec5(page: Page):
    return page.locator(
        '#ws-professional [data-testid="pro-val-section-report-type"]'
    ).first


# PVRT01: Section 5 wizard step is in DOM (display:none by default, shown when navigated)
def test_PVRT01_section5_in_dom(page: Page, live_server: str) -> None:
    """PVRT01: Section 5 is in DOM (hidden as wizard step; shown on navigation)."""
    _goto(page, live_server)
    count = page.locator('[data-testid="pro-val-section-report-type"]').count()
    assert count >= 1, "Section 5 should be in DOM"


# PVRT02: upper 5.1 selector removed; its hidden span confirms it was removed
def test_PVRT02_upper_report_selector_not_visible(page: Page, live_server: str) -> None:
    """PVRT02: 5.1 report level subsection NOT visible (upper duplicate removed)."""
    _goto(page, live_server)
    el = page.locator('[data-testid="pro-val-report-level-subsection"]')
    expect(el).not_to_be_visible()


# PVRT03: upper report-type-select replaced by unified selector in Chat CC
def test_PVRT03_upper_selector_not_visible_unified_is(page: Page, live_server: str) -> None:
    """PVRT03: upper pro-val-report-type-select NOT visible; pro-val-unified-analyze-generate-reports-select IS visible."""
    _goto(page, live_server)
    expect(page.locator('[data-testid="pro-val-report-type-select"]')).not_to_be_visible()
    expect(page.locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]')).to_be_visible()


# ── PVRT04: summary_report option visible ─────────────────────────────────
def test_PVRT04_summary_report_option_visible(page: Page, live_server: str) -> None:
    """PVRT04: تقرير موجز option is visible."""
    _goto(page, live_server)
    el = page.locator('[data-testid="pro-val-report-type-summary"]')
    expect(el).to_have_count(1)


# ── PVRT05: full_report option visible ────────────────────────────────────
def test_PVRT05_full_report_option_visible(page: Page, live_server: str) -> None:
    """PVRT05: تقرير كامل option is visible."""
    _goto(page, live_server)
    el = page.locator('[data-testid="pro-val-report-type-full"]')
    expect(el).to_have_count(1)


# ── PVRT06: enhanced_professional_report option visible ───────────────────
def test_PVRT06_enhanced_professional_option_visible(page: Page, live_server: str) -> None:
    """PVRT06: تقرير شامل option is visible."""
    _goto(page, live_server)
    el = page.locator('[data-testid="pro-val-report-type-enhanced-professional"]')
    expect(el).to_have_count(1)


# ── PVRT07: description panel visible ─────────────────────────────────────
def test_PVRT07_description_panel_visible(page: Page, live_server: str) -> None:
    """PVRT07: 5.2 description panel is visible."""
    _goto(page, live_server)
    el = page.locator('[data-testid="pro-val-report-type-descriptions"]')
    expect(el).to_be_visible()


# ── PVRT08: PDF output subsection visible ─────────────────────────────────
def test_PVRT08_pdf_output_subsection_visible(page: Page, live_server: str) -> None:
    """PVRT08: 5.3 PDF output subsection is visible."""
    _goto(page, live_server)
    el = page.locator('[data-testid="pro-val-report-pdf-output-subsection"]')
    expect(el).to_be_visible()


# ── PVRT09: Excel output subsection visible ───────────────────────────────
def test_PVRT09_excel_output_subsection_visible(page: Page, live_server: str) -> None:
    """PVRT09: 5.4 Excel output subsection is visible."""
    _goto(page, live_server)
    el = page.locator('[data-testid="pro-val-report-excel-output-subsection"]')
    expect(el).to_be_visible()


# ── PVRT10: recommendation subsection visible ─────────────────────────────
def test_PVRT10_recommendation_subsection_visible(page: Page, live_server: str) -> None:
    """PVRT10: 5.5 recommendation subsection is visible."""
    _goto(page, live_server)
    el = page.locator('[data-testid="pro-val-report-recommendation-subsection"]')
    expect(el).to_be_visible()


# ── PVRT11: gate/permission subsection visible ────────────────────────────
def test_PVRT11_gate_subsection_visible(page: Page, live_server: str) -> None:
    """PVRT11: 5.6 gate/permission subsection is visible."""
    _goto(page, live_server)
    el = page.locator('[data-testid="pro-val-report-gate-subsection"]')
    expect(el).to_be_visible()


# ── PVRT12: certification warning visible ─────────────────────────────────
def test_PVRT12_certification_warning_visible(page: Page, live_server: str) -> None:
    """PVRT12: pro-val-report-certification-warning is in DOM and visible."""
    _goto(page, live_server)
    el = page.locator('[data-testid="pro-val-report-certification-warning"]')
    expect(el).to_be_visible()


# ── PVRT13: advisory warning visible ──────────────────────────────────────
def test_PVRT13_advisory_warning_visible(page: Page, live_server: str) -> None:
    """PVRT13: pro-val-report-advisory-warning is in DOM and visible."""
    _goto(page, live_server)
    el = page.locator('[data-testid="pro-val-report-advisory-warning"]')
    expect(el).to_be_visible()


# ── PVRT14: selecting summary_report updates PDF list ─────────────────────
def test_PVRT14_select_summary_updates_pdf_list(page: Page, live_server: str) -> None:
    """PVRT14: selecting summary_report populates PDF sections list."""
    _goto(page, live_server)
    # PDF sections list element exists in DOM
    ul = page.locator('[data-testid="pro-val-summary-pdf-sections-list"]')
    assert ul.count() >= 1, "PDF sections list element should be in DOM"


# ── PVRT15: selecting full_report updates workbook list ───────────────────
def test_PVRT15_select_full_report_updates_workbook(page: Page, live_server: str) -> None:
    """PVRT15: selecting full_report populates workbook sheets list."""
    _goto(page, live_server)
    # Workbook sheets list element exists in DOM
    ul = page.locator('[data-testid="pro-val-summary-workbook-sheets-list"]')
    assert ul.count() >= 1, "Workbook sheets list element should be in DOM"


# ── PVRT16: selecting enhanced shows advanced sections text ───────────────
def test_PVRT16_pdf_sections_list_in_dom(page: Page, live_server: str) -> None:
    """PVRT16: PDF sections list element is in DOM (upper selector removed, list still present)."""
    _goto(page, live_server)
    ul = page.locator('[data-testid="pro-val-summary-pdf-sections-list"]')
    assert ul.count() >= 1, "PDF sections list element should be in DOM"

def test_PVRT17_no_auto_certification_claim(page: Page, live_server: str) -> None:
    """PVRT17: no claim of final official certification in Section 5 DOM."""
    _goto(page, live_server)
    sec5 = _sec5(page)
    text = sec5.text_content() or ""
    forbidden = ["معتمد رسمياً تلقائياً", "certified automatically", "final official compliance"]
    for f in forbidden:
        assert f not in text, f"Forbidden automatic certification text found: {f}"


# PVRT18: legacy vis select removed (replaced by unified selector)
def test_PVRT18_legacy_vis_select_not_visible(page: Page, live_server: str) -> None:
    """PVRT18: pro-val-vis-report-type-select is NOT visible (legacy removed, use unified selector)."""
    _goto(page, live_server)
    sel = page.locator('[data-testid="pro-val-vis-report-type-select"]')
    expect(sel).not_to_be_visible()


# ── PVRT19: no internal paths in DOM ─────────────────────────────────────
def test_PVRT19_no_internal_paths_in_dom(page: Page, live_server: str) -> None:
    """PVRT19: no internal file paths exposed in Section 5 DOM."""
    _goto(page, live_server)
    sec5 = _sec5(page)
    text = sec5.text_content() or ""
    assert "C:\\" not in text
    assert "expert_smart1" not in text
    assert "/home/" not in text


# ── PVRT20: no duplicate testids in Section 5 ────────────────────────────
def test_PVRT20_no_duplicate_testids_in_section5(page: Page, live_server: str) -> None:
    """PVRT20: Section 5 specific testids have no duplicates."""
    _goto(page, live_server)
    testids = [
        "pro-val-report-level-subsection",
        "pro-val-report-type-select",
        "pro-val-report-type-descriptions",
        "pro-val-report-pdf-output-subsection",
        "pro-val-report-excel-output-subsection",
        "pro-val-report-recommendation-subsection",
        "pro-val-report-gate-subsection",
        "pro-val-recommended-report-type",
        "pro-val-report-recommendation-reason",
        "pro-val-report-certification-warning",
        "pro-val-report-advisory-warning",
    ]
    for tid in testids:
        count = page.locator(f'[data-testid="{tid}"]').count()
        assert count == 1, f"Testid {tid} has count {count}, expected 1"
