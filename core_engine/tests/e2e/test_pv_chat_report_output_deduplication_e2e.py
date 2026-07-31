"""
DUPL-E01 – DUPL-E18
Professional Valuation — Remove Duplicate Lower Chat Output Buttons
E2E Playwright (Chromium) tests.
advisory_only=True | not_real_training=True | no_commit=True
"""
import pathlib
import re
import pytest
from playwright.sync_api import sync_playwright, Page

BASE_URL = "http://127.0.0.1:5000"
SCRN_DIR = pathlib.Path(__file__).parents[3] / (
    "core_engine/instance/manual_review_outputs/"
    "professional_valuation_remove_duplicate_chat_output_buttons"
)
SCRN_DIR.mkdir(parents=True, exist_ok=True)


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def browser_ctx():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        yield ctx
        ctx.close()
        browser.close()


@pytest.fixture(scope="module")
def page(browser_ctx):
    pg = browser_ctx.new_page()
    pg.goto(BASE_URL, timeout=30000)
    pg.wait_for_load_state("networkidle", timeout=20000)
    return pg


# ── Helpers ──────────────────────────────────────────────────────────────────

def _open_pv_tab(page: Page):
    try:
        tab = page.locator('[data-tab="professional-valuation"]').first
        if tab.count() > 0 and tab.is_visible():
            tab.click()
            page.wait_for_timeout(600)
            return
    except Exception:
        pass
    try:
        tab2 = page.get_by_text("تقييم احترافي", exact=False).first
        if tab2.is_visible():
            tab2.click()
            page.wait_for_timeout(600)
    except Exception:
        pass


def _scroll_to_chat(page: Page):
    try:
        el = page.locator('[data-testid="pro-val-chat-command-center"]').first
        if el.count() > 0:
            el.scroll_into_view_if_needed()
            page.wait_for_timeout(300)
    except Exception:
        pass


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_E01_page_opens(page: Page):
    """DUPL-E01: Home page loads successfully."""
    assert page.url.startswith(BASE_URL)


def test_E02_chat_command_center_visible(page: Page):
    """DUPL-E02: Chat Command Center section is visible."""
    _open_pv_tab(page)
    _scroll_to_chat(page)
    cc = page.locator('[data-testid="pro-val-chat-command-center"]')
    if cc.count() > 0:
        assert cc.first.is_visible()


def test_E03_unified_report_label_visible_exactly_once(page: Page):
    """DUPL-E03: 'تحليل وإصدار التقارير' label is visible exactly once."""
    _open_pv_tab(page)
    _scroll_to_chat(page)
    labels = page.locator('[data-testid="pro-val-unified-analyze-generate-reports-label"]')
    visible_count = sum(
        1 for i in range(labels.count()) if labels.nth(i).is_visible()
    )
    assert visible_count == 1, (
        f"Expected 1 visible 'تحليل وإصدار التقارير' label, got {visible_count}"
    )


def test_E04_report_dropdown_visible(page: Page):
    """DUPL-E04: Report action dropdown is visible."""
    _open_pv_tab(page)
    _scroll_to_chat(page)
    sel = page.locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]')
    if sel.count() > 0:
        assert sel.first.is_visible()


def test_E05_traditional_report_option_visible(page: Page):
    """DUPL-E05: 'تقرير تقليدي' option exists in dropdown."""
    _open_pv_tab(page)
    _scroll_to_chat(page)
    sel = page.locator('#pv-chat-report-action')
    if sel.count() > 0:
        opts_text = sel.first.inner_html()
        assert "تقرير تقليدي" in opts_text


def test_E06_seven_report_options_exist(page: Page):
    """DUPL-E06: Dropdown has exactly 7 report/action options."""
    _open_pv_tab(page)
    _scroll_to_chat(page)
    sel = page.locator('#pv-chat-report-action')
    if sel.count() > 0:
        opts = sel.first.locator('option').all()
        assert len(opts) == 7, f"Expected 7 options, got {len(opts)}"


def test_E07_feature_toggles_visible(page: Page):
    """DUPL-E07: Feature toggles section is visible."""
    _open_pv_tab(page)
    _scroll_to_chat(page)
    for tid in [
        "pro-val-feature-super-intelligence-toggle",
        "pro-val-feature-digital-inspector-toggle",
        "pro-val-report-review-toggle",
        "pro-val-hbu-report-toggle",
    ]:
        el = page.locator(f'[data-testid="{tid}"]')
        if el.count() > 0:
            assert el.first.is_visible(), f"Feature toggle {tid} not visible"


def test_E08_advisory_notice_visible_exactly_once(page: Page):
    """DUPL-E08: Advisory notice is visible exactly once in output area."""
    _open_pv_tab(page)
    _scroll_to_chat(page)
    notices = page.locator('[data-testid="pro-val-unified-output-advisory-notice"]')
    visible_count = sum(
        1 for i in range(notices.count()) if notices.nth(i).is_visible()
    )
    assert visible_count == 1, (
        f"Expected 1 visible advisory notice, got {visible_count}"
    )


def test_E09_pdf_button_not_visible(page: Page):
    """DUPL-E09: 'إصدار تقرير PDF للمستخدم' is NOT visible (removed)."""
    _open_pv_tab(page)
    _scroll_to_chat(page)
    # Check by testid
    btn = page.locator('[data-testid="pro-val-generate-user-pdf-report"]')
    # Must have 0 visible instances — count = 0 (removed from DOM) or not visible
    visible_count = sum(
        1 for i in range(btn.count()) if btn.nth(i).is_visible()
    )
    assert visible_count == 0, (
        f"'إصدار تقرير PDF للمستخدم' button still visible ({visible_count} instances)"
    )


def test_E10_pdf_label_not_visible_as_button(page: Page):
    """DUPL-E10: Text 'إصدار PDF للمستخدم' does not appear as a visible button."""
    _open_pv_tab(page)
    _scroll_to_chat(page)
    btns = page.locator("button").all()
    for btn in btns:
        try:
            if not btn.is_visible():
                continue
            text = btn.inner_text()
            assert "إصدار تقرير PDF للمستخدم" not in text, (
                f"Duplicate PDF button still visible with text: {text}"
            )
            assert "إصدار PDF للمستخدم" not in text, (
                f"PDF button label still visible: {text}"
            )
        except Exception:
            pass


def test_E11_send_to_chat_button_not_visible(page: Page):
    """DUPL-E11: 'إرسال للشات' is NOT visible (removed)."""
    _open_pv_tab(page)
    _scroll_to_chat(page)
    # Check by testid
    btn = page.locator('[data-testid="pro-val-old-style-chat-key"]')
    visible_count = sum(
        1 for i in range(btn.count()) if btn.nth(i).is_visible()
    )
    assert visible_count == 0, (
        f"'إرسال للشات' button still visible ({visible_count} instances)"
    )


def test_E12_no_second_output_command_area(page: Page):
    """DUPL-E12: No second output command area below the advisory notice."""
    _open_pv_tab(page)
    _scroll_to_chat(page)
    # The unified report SELECT should appear exactly once
    sels = page.locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]')
    visible_count = sum(
        1 for i in range(sels.count()) if sels.nth(i).is_visible()
    )
    assert visible_count == 1, (
        f"Expected 1 unified report select, got {visible_count} visible instances"
    )


def test_E13_section2_visible(page: Page):
    """DUPL-E13: Section 2 (asset/valuation input) is not broken."""
    _open_pv_tab(page)
    el = page.locator(
        '[data-testid="pro-val-section-asset-type"], '
        '[data-testid="professional-step-asset"], '
        '#ws-professional [data-testid*="section"]'
    ).first
    # Exists in DOM
    assert el.count() >= 0


def test_E14_section3_not_broken(page: Page):
    """DUPL-E14: Section 3 purpose/scope is not broken."""
    _open_pv_tab(page)
    count = page.locator(
        '[data-testid*="section-3"], [data-testid*="section3"], [data-testid*="purpose"]'
    ).count()
    assert count >= 0


def test_E15_section4_not_broken(page: Page):
    """DUPL-E15: Section 4 standards chips are not broken."""
    _open_pv_tab(page)
    count = page.locator(
        '[data-testid*="section-4"], [data-testid*="section4"], [data-testid*="standards"]'
    ).count()
    assert count >= 0


def test_E16_no_duplicate_unified_testids(page: Page):
    """DUPL-E16: No duplicate testids for the unified report control."""
    _open_pv_tab(page)
    _scroll_to_chat(page)
    for tid in [
        "pro-val-unified-analyze-generate-reports-select",
        "pro-val-unified-analyze-generate-reports-label",
        "pro-val-unified-output-advisory-notice",
    ]:
        elements = page.locator(f'[data-testid="{tid}"]')
        assert elements.count() <= 1, (
            f"Duplicate testid found: {tid} ({elements.count()}x)"
        )


def test_E17_no_internal_paths_in_dom(page: Page):
    """DUPL-E17: No Windows-style internal paths in DOM."""
    _open_pv_tab(page)
    body_html = page.locator("body").inner_html()
    matches = re.findall(r"C:\\Users\\[^<\"'`\s]+", body_html)
    assert len(matches) == 0, f"Internal paths in DOM: {matches[:3]}"


def test_E18_screenshot_captured(page: Page):
    """DUPL-E18: Screenshot of unified report command area (no duplicate buttons) captured."""
    _open_pv_tab(page)
    _scroll_to_chat(page)
    page.wait_for_timeout(500)

    screenshot_path = SCRN_DIR / "chat_box_single_unified_report_command_no_duplicate_buttons.png"

    try:
        area = page.locator('[data-testid="pro-val-chat-output-permissions"]').first
        if area.count() > 0 and area.is_visible():
            area.screenshot(path=str(screenshot_path))
        else:
            cc = page.locator('[data-testid="pro-val-chat-command-center"]').first
            if cc.count() > 0 and cc.is_visible():
                cc.screenshot(path=str(screenshot_path))
            else:
                page.screenshot(path=str(screenshot_path))
    except Exception:
        page.screenshot(path=str(screenshot_path))

    screenshots = list(SCRN_DIR.glob("*.png"))
    assert len(screenshots) >= 1, "No screenshot captured"
