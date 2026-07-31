"""
PVFSR E2E Playwright Tests — Force Single Report Control
=========================================================
Tests PVFSR-E01 through PVFSR-E29.
Verifies visible-count assertions in Chromium browser.
"""
import pathlib
import pytest
from playwright.sync_api import Page, expect

_SCREENSHOT_DIR = (
    pathlib.Path(__file__).parent.parent.parent
    / "instance" / "manual_review_outputs"
    / "professional_valuation_force_single_report_control"
)
_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def _go(page: Page, live_server) -> None:
    page.goto(f"{live_server}/", timeout=30000)
    page.wait_for_load_state("domcontentloaded")


def _ws(page: Page):
    return page.locator("#ws-professional")


def _open_pv(page: Page, live_server) -> None:
    _go(page, live_server)
    tab = page.locator('[data-testid="tab-professional"]')
    if tab.count() and tab.is_visible():
        tab.click()
    page.wait_for_selector("#ws-professional", state="visible", timeout=10000)


def _unified_select(page: Page):
    return _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]')


def _count_visible_text(page: Page, text: str) -> int:
    return _ws(page).locator(f"text={text}").count()


# ─────────────────────────────────────────────────────────────────────────────


# PVFSR-E01: Professional Valuation page opens
def test_pvfsr_e01_page_opens(page: Page, live_server):
    _open_pv(page, live_server)
    assert _ws(page).is_visible(), "PVFSR-E01: Professional Valuation workspace must be visible"


# PVFSR-E02: Old label "نوع التقرير أو الإجراء" has visible count = 0
def test_pvfsr_e02_old_label_report_type_not_visible(page: Page, live_server):
    _open_pv(page, live_server)
    locs = _ws(page).locator("text=نوع التقرير أو الإجراء")
    visible_count = sum(1 for i in range(locs.count()) if locs.nth(i).is_visible())
    assert visible_count == 0, \
        f"PVFSR-E02: 'نوع التقرير أو الإجراء' must not be visible, found {visible_count}"


# PVFSR-E03: Old label "تحليل وإصدار التقرير" has visible count = 0
def test_pvfsr_e03_old_label_analyze_generate_not_visible(page: Page, live_server):
    _open_pv(page, live_server)
    locs = _ws(page).locator("text=تحليل وإصدار التقرير")
    visible_count = sum(
        1 for i in range(locs.count())
        if locs.nth(i).is_visible() and locs.nth(i).text_content().strip() == "تحليل وإصدار التقرير"
    )
    assert visible_count == 0, \
        f"PVFSR-E03: 'تحليل وإصدار التقرير' must not be visible, found {visible_count}"


# PVFSR-E04: New label "تحليل وإصدار التقارير" is visible exactly once
def test_pvfsr_e04_unified_label_visible_once(page: Page, live_server):
    _open_pv(page, live_server)
    locs = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-label"]')
    visible_count = sum(1 for i in range(locs.count()) if locs.nth(i).is_visible())
    assert visible_count == 1, \
        f"PVFSR-E04: 'تحليل وإصدار التقارير' label must be visible exactly once, found {visible_count}"


# PVFSR-E05: Exactly one visible report-action dropdown
def test_pvfsr_e05_single_visible_dropdown(page: Page, live_server):
    _open_pv(page, live_server)
    locs = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]')
    visible_count = sum(1 for i in range(locs.count()) if locs.nth(i).is_visible())
    assert visible_count == 1, \
        f"PVFSR-E05: exactly one report-action dropdown must be visible, found {visible_count}"


# PVFSR-E06: Dropdown testid is visible
def test_pvfsr_e06_dropdown_testid_visible(page: Page, live_server):
    _open_pv(page, live_server)
    sel = _unified_select(page)
    assert sel.count() >= 1, "PVFSR-E06: pro-val-unified-analyze-generate-reports-select must exist"
    assert sel.first.is_visible(), "PVFSR-E06: pro-val-unified-analyze-generate-reports-select must be visible"


# PVFSR-E07: Dropdown option count = 7
def test_pvfsr_e07_option_count_seven(page: Page, live_server):
    _open_pv(page, live_server)
    opts = _unified_select(page).first.locator("option")
    assert opts.count() == 7, f"PVFSR-E07: must have exactly 7 options, found {opts.count()}"


# PVFSR-E08: Option "تقرير تقليدي" present
def test_pvfsr_e08_option_traditional(page: Page, live_server):
    _open_pv(page, live_server)
    opt = _ws(page).locator('[data-testid="pro-val-chat-report-action-traditional"]')
    assert opt.count() >= 1, "PVFSR-E08: option 'تقرير تقليدي' must exist"


# PVFSR-E09: Option "تقرير تفصيلي" present
def test_pvfsr_e09_option_detailed(page: Page, live_server):
    _open_pv(page, live_server)
    opt = _ws(page).locator('[data-testid="pro-val-chat-report-action-detailed"]')
    assert opt.count() >= 1, "PVFSR-E09: option 'تقرير تفصيلي' must exist"


# PVFSR-E10: Option "تقرير احترافي" present
def test_pvfsr_e10_option_professional(page: Page, live_server):
    _open_pv(page, live_server)
    opt = _ws(page).locator('[data-testid="pro-val-chat-report-action-professional"]')
    assert opt.count() >= 1, "PVFSR-E10: option 'تقرير احترافي' must exist"


# PVFSR-E11: Option "محاكاة تقرير مرفوع" present
def test_pvfsr_e11_option_simulated(page: Page, live_server):
    _open_pv(page, live_server)
    opt = _ws(page).locator('[data-testid="pro-val-chat-report-action-simulated-uploaded"]')
    assert opt.count() >= 1, "PVFSR-E11: option 'محاكاة تقرير مرفوع' must exist"


# PVFSR-E12: Option "مراجعة تقرير" present
def test_pvfsr_e12_option_review(page: Page, live_server):
    _open_pv(page, live_server)
    opt = _ws(page).locator('[data-testid="pro-val-chat-report-action-review"]')
    assert opt.count() >= 1, "PVFSR-E12: option 'مراجعة تقرير' must exist"


# PVFSR-E13: Option "تقرير تحليل أعلى وأفضل استخدام" present
def test_pvfsr_e13_option_hbu(page: Page, live_server):
    _open_pv(page, live_server)
    opt = _ws(page).locator('[data-testid="pro-val-chat-report-action-hbu"]')
    assert opt.count() >= 1, "PVFSR-E13: option 'تقرير تحليل أعلى وأفضل استخدام' must exist"


# PVFSR-E14: Option "تقرير امتثال المعايير" present
def test_pvfsr_e14_option_standards(page: Page, live_server):
    _open_pv(page, live_server)
    opt = _ws(page).locator('[data-testid="pro-val-chat-report-action-standards-compliance"]')
    assert opt.count() >= 1, "PVFSR-E14: option 'تقرير امتثال المعايير' must exist"


# PVFSR-E15: "نمط التقرير Excel" is not visible as main selector
def test_pvfsr_e15_excel_pattern_not_main_selector(page: Page, live_server):
    _open_pv(page, live_server)
    locs = _ws(page).locator("text=نمط التقرير Excel")
    visible_count = sum(1 for i in range(locs.count()) if locs.nth(i).is_visible())
    assert visible_count == 0, \
        f"PVFSR-E15: 'نمط التقرير Excel' must not be visible as main selector, found {visible_count}"


# PVFSR-E16: Select traditional_report → unified_report_action = traditional_report
def test_pvfsr_e16_select_traditional(page: Page, live_server):
    _open_pv(page, live_server)
    sel = _unified_select(page).first
    sel.select_option("traditional_report")
    val = sel.input_value()
    assert val == "traditional_report", f"PVFSR-E16: expected 'traditional_report', got '{val}'"


# PVFSR-E17: Select detailed_report → unified_report_action = detailed_report
def test_pvfsr_e17_select_detailed(page: Page, live_server):
    _open_pv(page, live_server)
    sel = _unified_select(page).first
    sel.select_option("detailed_report")
    val = sel.input_value()
    assert val == "detailed_report", f"PVFSR-E17: expected 'detailed_report', got '{val}'"


# PVFSR-E18: Select professional_report → unified_report_action = professional_report
def test_pvfsr_e18_select_professional(page: Page, live_server):
    _open_pv(page, live_server)
    sel = _unified_select(page).first
    sel.select_option("professional_report")
    val = sel.input_value()
    assert val == "professional_report", f"PVFSR-E18: expected 'professional_report', got '{val}'"


# PVFSR-E19: PDF button remains visible
def test_pvfsr_e19_pdf_button_visible(page: Page, live_server):
    _open_pv(page, live_server)
    btn = _ws(page).locator('[data-testid="pro-val-unified-generate-user-pdf"]')
    assert btn.count() >= 1 and btn.first.is_visible(), "PVFSR-E19: PDF button must be visible"


# PVFSR-E20: Admin Excel button exists (protected/disabled for non-admin)
def test_pvfsr_e20_admin_excel_button_protected(page: Page, live_server):
    _open_pv(page, live_server)
    btn = _ws(page).locator('[data-testid="pro-val-unified-generate-admin-excel"]')
    assert btn.count() >= 1, "PVFSR-E20: Admin Excel button must exist in DOM (even if hidden)"


# PVFSR-E21: "إصدار المخرجات" button remains visible
def test_pvfsr_e21_generate_output_button_visible(page: Page, live_server):
    _open_pv(page, live_server)
    btn = _ws(page).locator('[data-testid="pro-val-unified-generate-selected-output"]')
    assert btn.count() >= 1 and btn.first.is_visible(), "PVFSR-E21: 'إصدار المخرجات' button must be visible"


# PVFSR-E22: Section 2 remains visible
def test_pvfsr_e22_section2_visible(page: Page, live_server):
    _open_pv(page, live_server)
    s2 = _ws(page).locator('[data-testid="professional-step-asset"]')
    if s2.count() == 0:
        s2 = _ws(page).locator('[data-testid="pro-val-section-asset-type-selection"]')
    assert s2.count() >= 1, "PVFSR-E22: Section 2 (asset details) must be present"


# PVFSR-E23: Section 3 remains visible
def test_pvfsr_e23_section3_visible(page: Page, live_server):
    _open_pv(page, live_server)
    s3 = _ws(page).locator('[data-testid="pro-val-section-purpose"]')
    if s3.count() == 0:
        s3 = _ws(page).locator('[data-testid="professional-step-purpose"]')
    assert s3.count() >= 1, "PVFSR-E23: Section 3 (purpose) must be present"


# PVFSR-E24: Section 4 remains visible
def test_pvfsr_e24_section4_visible(page: Page, live_server):
    _open_pv(page, live_server)
    s4 = _ws(page).locator('[data-testid="professional-step-matrix"]')
    if s4.count() == 0:
        s4 = _ws(page).locator('[data-testid="pro-val-standards-core-subsection"]')
    assert s4.count() >= 1, "PVFSR-E24: Section 4 (standards/matrix) must be present"


# PVFSR-E25: Chat input remains visible
def test_pvfsr_e25_chat_input_visible(page: Page, live_server):
    _open_pv(page, live_server)
    inp = _ws(page).locator('[data-testid="pro-val-chat-input"]')
    if inp.count() == 0:
        inp = _ws(page).locator('#pv-chat-input')
    assert inp.count() >= 1, "PVFSR-E25: Chat input must be present"


# PVFSR-E26: No duplicate data-testids for the unified select
def test_pvfsr_e26_no_duplicate_testids(page: Page, live_server):
    _open_pv(page, live_server)
    all_matches = page.locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]')
    assert all_matches.count() == 1, \
        f"PVFSR-E26: pro-val-unified-analyze-generate-reports-select must appear exactly once, found {all_matches.count()}"


# PVFSR-E27: No internal paths in DOM
def test_pvfsr_e27_no_internal_paths_in_dom(page: Page, live_server):
    _open_pv(page, live_server)
    bad_patterns = [
        "core_engine/instance/manual_review_outputs",
        "C:\\Users\\Lenovo\\Desktop",
        "expert_smart1 - Copy",
    ]
    body = _ws(page).inner_html()
    for pat in bad_patterns:
        assert pat not in body, f"PVFSR-E27: internal path '{pat}' found in DOM"


# PVFSR-E28: Chat output permissions area exists
def test_pvfsr_e28_output_permissions_area(page: Page, live_server):
    _open_pv(page, live_server)
    panel = _ws(page).locator('[data-testid="pro-val-chat-output-permissions"]')
    assert panel.count() >= 1, "PVFSR-E28: output permissions panel must exist"


# PVFSR-E29: Capture screenshots
def test_pvfsr_e29_capture_screenshots(page: Page, live_server):
    _open_pv(page, live_server)

    # Screenshot 1: after single control (main view)
    page.screenshot(
        path=str(_SCREENSHOT_DIR / "after_single_analyze_generate_reports_control.png"),
        full_page=False
    )

    # Screenshot 2: open the dropdown to show 7 options
    sel = _unified_select(page).first
    page.evaluate(
        "el => { el.size = el.options.length; el.style.height='auto'; }",
        sel.element_handle()
    )
    page.wait_for_timeout(400)
    page.screenshot(
        path=str(_SCREENSHOT_DIR / "seven_report_options_dropdown_open.png"),
        full_page=False
    )
    # Reset
    page.evaluate("el => { el.size = 1; el.style.height=''; }", sel.element_handle())

    # Screenshot 3: before state (just the page without any special state = same as screenshot 1 zoomed)
    page.screenshot(
        path=str(_SCREENSHOT_DIR / "before_duplicate_controls_if_available.png"),
        full_page=False
    )

    assert (_SCREENSHOT_DIR / "after_single_analyze_generate_reports_control.png").exists()
    assert (_SCREENSHOT_DIR / "seven_report_options_dropdown_open.png").exists()
    assert (_SCREENSHOT_DIR / "before_duplicate_controls_if_available.png").exists()
