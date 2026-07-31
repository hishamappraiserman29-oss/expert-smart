# -*- coding: utf-8 -*-
"""
test_pv_unified_report_generation_control_e2e.py
E2E Playwright tests: Unified Report Generation Control (PVURGC-E)

Verifies that:
- Exactly ONE visible report-action dropdown exists (named "تحليل وإصدار التقارير")
- Old duplicate labels are NOT visible
- The dropdown contains exactly 7 options
- Selecting each option updates the page state
- PDF button preserved; Admin Excel protected
- Section 2 / Chat input remain functional
- No duplicate testids, no internal paths in DOM

Tests:
  PVURGC-E01  Professional Valuation page opens
  PVURGC-E02  Chat box / output area visible
  PVURGC-E03  Exactly one visible report action dropdown
  PVURGC-E04  Visible dropdown label is "تحليل وإصدار التقارير"
  PVURGC-E05  Old label "نوع التقرير أو الإجراء" NOT visible as separate control
  PVURGC-E06  Old label "تحليل وإصدار التقرير" NOT visible as separate control
  PVURGC-E07  "نمط التقرير Excel" is NOT the main report selector
  PVURGC-E08  Dropdown contains "تقرير تقليدي"
  PVURGC-E09  Dropdown contains "تقرير تفصيلي"
  PVURGC-E10  Dropdown contains "تقرير احترافي"
  PVURGC-E11  Dropdown contains "محاكاة تقرير مرفوع"
  PVURGC-E12  Dropdown contains "مراجعة تقرير"
  PVURGC-E13  Dropdown contains "تقرير تحليل أعلى وأفضل استخدام"
  PVURGC-E14  Dropdown contains "تقرير امتثال المعايير"
  PVURGC-E15  Dropdown option count is exactly 7
  PVURGC-E16  Select traditional_report
  PVURGC-E17  Verify unified_report_action = traditional_report
  PVURGC-E18  Select detailed_report
  PVURGC-E19  Verify unified_report_action = detailed_report
  PVURGC-E20  Select professional_report
  PVURGC-E21  Verify unified_report_action = professional_report
  PVURGC-E22  PDF button visible
  PVURGC-E23  Admin Excel button hidden/protected for non-admin
  PVURGC-E24  Generate selected output button visible
  PVURGC-E25  Section 2 asset type selector visible and unaffected
  PVURGC-E26  Chat input visible and unaffected
  PVURGC-E27  No duplicate testids in ws-professional
  PVURGC-E28  No internal paths in DOM
  PVURGC-E29  Screenshots captured
"""
from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

# ── QA output directory ───────────────────────────────────────────────────────

_QA_BASE = (
    Path(__file__).resolve().parents[2]
    / "instance" / "manual_review_outputs"
    / "professional_valuation_merge_report_controls"
)
_QA_BASE.mkdir(parents=True, exist_ok=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _block_api(page: Page) -> None:
    page.route("**/api/**", lambda r: r.fulfill(
        status=200,
        body=b'{"ok":true,"request_id":"PVURGC-TEST","unified_professional_valuation_page_context":{"advisory_only":true}}',
        content_type="application/json",
    ))


def _go(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator('[data-testid="professional-wizard"]').wait_for(state="visible", timeout=12_000)


def _ws(page: Page):
    return page.locator("#ws-professional")


def _get_report_select(page: Page):
    return _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]').first


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_PVURGC_E01_page_opens(page: Page, live_server: str) -> None:
    """PVURGC-E01: Professional Valuation page opens and wizard container visible."""
    _block_api(page)
    _go(page, live_server)
    expect(page.locator('[data-testid="professional-wizard"]')).to_be_visible()


def test_PVURGC_E02_chat_box_visible(page: Page, live_server: str) -> None:
    """PVURGC-E02: Chat box output area is visible."""
    _block_api(page)
    _go(page, live_server)
    expect(_ws(page).locator('[data-testid="pro-val-chat-output-permissions"]')).to_be_visible()


def test_PVURGC_E03_exactly_one_visible_report_dropdown(page: Page, live_server: str) -> None:
    """PVURGC-E03: Exactly one visible report action dropdown in ws-professional."""
    _block_api(page)
    _go(page, live_server)
    sel = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]')
    assert sel.count() == 1, f"Expected 1 unified dropdown, found {sel.count()}"
    expect(sel).to_be_visible()


def test_PVURGC_E04_visible_label_is_canonical(page: Page, live_server: str) -> None:
    """PVURGC-E04: The visible label is exactly 'تحليل وإصدار التقارير'."""
    _block_api(page)
    _go(page, live_server)
    label = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-label"]')
    expect(label).to_be_visible()
    txt = label.text_content() or ""
    assert "تحليل وإصدار التقارير" in txt, f"Label text was: {txt!r}"


def test_PVURGC_E05_old_label_naw3_not_visible(page: Page, live_server: str) -> None:
    """PVURGC-E05: 'نوع التقرير أو الإجراء' is NOT visible as a separate control label."""
    _block_api(page)
    _go(page, live_server)
    # The old label text should not appear as a visible standalone element
    ws = _ws(page)
    labels = ws.locator("label, legend, span, div")
    count = labels.count()
    found_visible = False
    for i in range(min(count, 200)):
        try:
            el = labels.nth(i)
            if el.is_visible():
                txt = el.text_content() or ""
                if "نوع التقرير أو الإجراء" == txt.strip():
                    found_visible = True
                    break
        except Exception:
            pass
    assert not found_visible, "Old label 'نوع التقرير أو الإجراء' is still visible"


def test_PVURGC_E06_old_label_tahleel_not_visible(page: Page, live_server: str) -> None:
    """PVURGC-E06: 'تحليل وإصدار التقرير' (singular) NOT visible as a standalone label."""
    _block_api(page)
    _go(page, live_server)
    # The button with that text should be hidden (display:none)
    btn = page.locator('#generateBtn')
    if btn.count() > 0:
        # If element exists, it must be hidden
        assert not btn.is_visible(), "generateBtn with old label is still visible"


def test_PVURGC_E07_excel_pattern_not_main_selector(page: Page, live_server: str) -> None:
    """PVURGC-E07: 'نمط التقرير Excel' is not the main report type selector."""
    _block_api(page)
    _go(page, live_server)
    # The canonical unified select must NOT have Excel pattern options as its values
    sel = _get_report_select(page)
    option_values = page.evaluate(
        """() => {
            const el = document.getElementById('pv-chat-report-action');
            if (!el) return [];
            return Array.from(el.options).map(o => o.value);
        }"""
    )
    assert "legacy" not in option_values, "Excel 'legacy' style is in the main report selector"
    assert "detailed" not in option_values, "Excel 'detailed' style is in the main report selector"
    assert "professional_template" not in option_values, "Excel template in main selector"


def test_PVURGC_E08_option_traditional_report(page: Page, live_server: str) -> None:
    """PVURGC-E08: Dropdown contains 'تقرير تقليدي'."""
    _block_api(page)
    _go(page, live_server)
    opt = _ws(page).locator(
        '[data-testid="pro-val-unified-analyze-generate-reports-select"] '
        'option[value="traditional_report"]'
    )
    assert opt.count() >= 1
    assert "تقرير تقليدي" in (opt.first.text_content() or "")


def test_PVURGC_E09_option_detailed_report(page: Page, live_server: str) -> None:
    """PVURGC-E09: Dropdown contains 'تقرير تفصيلي'."""
    _block_api(page)
    _go(page, live_server)
    opt = _ws(page).locator(
        '[data-testid="pro-val-unified-analyze-generate-reports-select"] '
        'option[value="detailed_report"]'
    )
    assert opt.count() >= 1
    assert "تقرير تفصيلي" in (opt.first.text_content() or "")


def test_PVURGC_E10_option_professional_report(page: Page, live_server: str) -> None:
    """PVURGC-E10: Dropdown contains 'تقرير احترافي'."""
    _block_api(page)
    _go(page, live_server)
    opt = _ws(page).locator(
        '[data-testid="pro-val-unified-analyze-generate-reports-select"] '
        'option[value="professional_report"]'
    )
    assert opt.count() >= 1
    assert "تقرير احترافي" in (opt.first.text_content() or "")


def test_PVURGC_E11_option_simulated_uploaded(page: Page, live_server: str) -> None:
    """PVURGC-E11: Dropdown contains 'محاكاة تقرير مرفوع'."""
    _block_api(page)
    _go(page, live_server)
    opt = _ws(page).locator(
        '[data-testid="pro-val-unified-analyze-generate-reports-select"] '
        'option[value="simulated_uploaded_report"]'
    )
    assert opt.count() >= 1
    assert "محاكاة تقرير مرفوع" in (opt.first.text_content() or "")


def test_PVURGC_E12_option_report_review(page: Page, live_server: str) -> None:
    """PVURGC-E12: Dropdown contains 'مراجعة تقرير'."""
    _block_api(page)
    _go(page, live_server)
    opt = _ws(page).locator(
        '[data-testid="pro-val-unified-analyze-generate-reports-select"] '
        'option[value="report_review_output"]'
    )
    assert opt.count() >= 1
    assert "مراجعة تقرير" in (opt.first.text_content() or "")


def test_PVURGC_E13_option_hbu(page: Page, live_server: str) -> None:
    """PVURGC-E13: Dropdown contains 'تقرير تحليل أعلى وأفضل استخدام'."""
    _block_api(page)
    _go(page, live_server)
    opt = _ws(page).locator(
        '[data-testid="pro-val-unified-analyze-generate-reports-select"] '
        'option[value="hbu_analysis_report"]'
    )
    assert opt.count() >= 1
    assert "أعلى وأفضل" in (opt.first.text_content() or "")


def test_PVURGC_E14_option_standards_compliance(page: Page, live_server: str) -> None:
    """PVURGC-E14: Dropdown contains 'تقرير امتثال المعايير'."""
    _block_api(page)
    _go(page, live_server)
    opt = _ws(page).locator(
        '[data-testid="pro-val-unified-analyze-generate-reports-select"] '
        'option[value="standards_compliance_report"]'
    )
    assert opt.count() >= 1
    assert "امتثال المعايير" in (opt.first.text_content() or "")


def test_PVURGC_E15_dropdown_has_exactly_7_options(page: Page, live_server: str) -> None:
    """PVURGC-E15: Dropdown has exactly 7 options."""
    _block_api(page)
    _go(page, live_server)
    count = page.evaluate(
        """() => {
            const el = document.getElementById('pv-chat-report-action');
            return el ? el.options.length : 0;
        }"""
    )
    assert count == 7, f"Expected 7 options, got {count}"


def test_PVURGC_E16_select_traditional_report(page: Page, live_server: str) -> None:
    """PVURGC-E16: Can select traditional_report in the unified dropdown."""
    _block_api(page)
    _go(page, live_server)
    sel = _get_report_select(page)
    sel.select_option("traditional_report")
    val = page.evaluate("() => document.getElementById('pv-chat-report-action')?.value")
    assert val == "traditional_report"


def test_PVURGC_E17_unified_report_action_traditional(page: Page, live_server: str) -> None:
    """PVURGC-E17: After selecting traditional_report, page state reflects it."""
    _block_api(page)
    _go(page, live_server)
    sel = _get_report_select(page)
    sel.select_option("traditional_report")
    val = page.evaluate(
        "() => document.getElementById('pv-chat-report-action')?.value || ''"
    )
    assert val == "traditional_report", f"Expected traditional_report, got {val!r}"


def test_PVURGC_E18_select_detailed_report(page: Page, live_server: str) -> None:
    """PVURGC-E18: Can select detailed_report in the unified dropdown."""
    _block_api(page)
    _go(page, live_server)
    sel = _get_report_select(page)
    sel.select_option("detailed_report")
    val = page.evaluate("() => document.getElementById('pv-chat-report-action')?.value")
    assert val == "detailed_report"


def test_PVURGC_E19_unified_report_action_detailed(page: Page, live_server: str) -> None:
    """PVURGC-E19: After selecting detailed_report, page state reflects it."""
    _block_api(page)
    _go(page, live_server)
    sel = _get_report_select(page)
    sel.select_option("detailed_report")
    val = page.evaluate(
        "() => document.getElementById('pv-chat-report-action')?.value || ''"
    )
    assert val == "detailed_report", f"Expected detailed_report, got {val!r}"


def test_PVURGC_E20_select_professional_report(page: Page, live_server: str) -> None:
    """PVURGC-E20: Can select professional_report in the unified dropdown."""
    _block_api(page)
    _go(page, live_server)
    sel = _get_report_select(page)
    sel.select_option("professional_report")
    val = page.evaluate("() => document.getElementById('pv-chat-report-action')?.value")
    assert val == "professional_report"


def test_PVURGC_E21_unified_report_action_professional(page: Page, live_server: str) -> None:
    """PVURGC-E21: After selecting professional_report, page state reflects it."""
    _block_api(page)
    _go(page, live_server)
    sel = _get_report_select(page)
    sel.select_option("professional_report")
    val = page.evaluate(
        "() => document.getElementById('pv-chat-report-action')?.value || ''"
    )
    assert val == "professional_report", f"Expected professional_report, got {val!r}"


def test_PVURGC_E22_pdf_button_visible(page: Page, live_server: str) -> None:
    """PVURGC-E22: PDF button 'إصدار PDF للمستخدم' is visible."""
    _block_api(page)
    _go(page, live_server)
    btn = _ws(page).locator('[data-testid="pro-val-unified-generate-user-pdf"]')
    expect(btn).to_be_visible()


def test_PVURGC_E23_admin_excel_hidden_for_non_admin(page: Page, live_server: str) -> None:
    """PVURGC-E23: Admin Excel button is hidden/protected for non-admin users."""
    _block_api(page)
    _go(page, live_server)
    btn = page.locator('[data-testid="pro-val-unified-generate-admin-excel"]')
    if btn.count() > 0:
        assert not btn.is_visible(), "Admin Excel button should be hidden for non-admin"


def test_PVURGC_E24_generate_output_button_visible(page: Page, live_server: str) -> None:
    """PVURGC-E24: 'إصدار المخرجات' button is visible."""
    _block_api(page)
    _go(page, live_server)
    btn = _ws(page).locator('[data-testid="pro-val-unified-generate-selected-output"]')
    expect(btn).to_be_visible()


def test_PVURGC_E25_section2_asset_type_unaffected(page: Page, live_server: str) -> None:
    """PVURGC-E25: Section 2 asset type selector is visible and unaffected."""
    _block_api(page)
    _go(page, live_server)
    sec2 = _ws(page).locator('[data-testid="pro-val-section-asset-type-selection"]')
    expect(sec2).to_be_visible()


def test_PVURGC_E26_chat_input_unaffected(page: Page, live_server: str) -> None:
    """PVURGC-E26: Chat input area is visible and unaffected."""
    _block_api(page)
    _go(page, live_server)
    inp = _ws(page).locator('[data-testid="pro-val-chat-input"]')
    expect(inp).to_be_visible()


def test_PVURGC_E27_no_duplicate_report_action_testids(page: Page, live_server: str) -> None:
    """PVURGC-E27: The unified dropdown testid appears exactly once."""
    _block_api(page)
    _go(page, live_server)
    sel = _ws(page).locator('[data-testid="pro-val-unified-analyze-generate-reports-select"]')
    assert sel.count() == 1, f"Expected exactly 1 unified dropdown, found {sel.count()}"


def test_PVURGC_E28_no_internal_paths_in_dom(page: Page, live_server: str) -> None:
    """PVURGC-E28: DOM body does not contain internal file path fragments."""
    _block_api(page)
    _go(page, live_server)
    body_html = page.locator("body").inner_html()
    bad_patterns = ["C:\\Users\\", "c:\\Users\\", "/home/", "core_engine/tests/"]
    for pat in bad_patterns:
        assert pat not in body_html, f"Internal path found in DOM: {pat!r}"


def test_PVURGC_E29_screenshots_captured(page: Page, live_server: str) -> None:
    """PVURGC-E29: Capture three required screenshots."""
    _block_api(page)
    _go(page, live_server)

    # Screenshot 1: unified dropdown visible
    page.screenshot(
        path=str(_QA_BASE / "unified_analyze_generate_reports_dropdown.png"),
        full_page=False,
    )

    # Screenshot 2: verify old label not present, new label visible
    page.screenshot(
        path=str(_QA_BASE / "duplicate_report_controls_removed.png"),
        full_page=False,
    )

    # Screenshot 3: show all 7 options by clicking the dropdown
    sel = _get_report_select(page)
    sel.click()
    page.screenshot(
        path=str(_QA_BASE / "seven_report_actions_visible.png"),
        full_page=False,
    )

    # Verify screenshots were actually written
    for fname in [
        "unified_analyze_generate_reports_dropdown.png",
        "duplicate_report_controls_removed.png",
        "seven_report_actions_visible.png",
    ]:
        path = _QA_BASE / fname
        assert path.exists(), f"Screenshot missing: {fname}"
        assert path.stat().st_size > 5_000, f"Screenshot suspiciously small: {fname}"
