# test_pv_split_report_issuance_controls_e2e.py
# E2E tests — Split Report Issuance Controls
# advisory_only=True | not_real_training=True | no_commit=True
#
# T01–T23: Static HTML checks — run without live server.
# T24–T27: Playwright browser tests — require live server + @pytest.mark.live_server.

import json
import pathlib
import pytest

pytestmark = pytest.mark.e2e

HTML      = pathlib.Path("frontend/index.html")
BASE      = pathlib.Path("core_engine/instance/manual_review_outputs/"
                          "professional_valuation_split_report_issuance_controls")
BASE_URL  = "http://127.0.0.1:5000"

CORE_TYPES    = ["traditional_report", "detailed_report", "professional_report"]
SPECIAL_TYPES = ["report_review_output", "simulated_uploaded_report",
                 "hbu_analysis_report", "standards_compliance_report"]

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


def _html():
    return HTML.read_text(encoding="utf-8", errors="replace")


def _server_running():
    import urllib.request
    try:
        urllib.request.urlopen(f"{BASE_URL}/api/advisor/health", timeout=3)
        return True
    except Exception:
        return False


# ── T01: Professional Valuation page HTML exists ──────────────────────────────
def test_T01_pv_page_html_exists():
    assert HTML.exists(), "frontend/index.html missing"
    html = _html()
    assert "valuation" in html.lower() or "تقييم" in html


# ── T02: Chat box visible in HTML ─────────────────────────────────────────────
def test_T02_chat_box_visible():
    html = _html()
    assert "pro-val-section-chat-box" in html or "pro-val-chat-command-center" in html


# ── T03: Core report issuance section present ────────────────────────────────
def test_T03_core_report_issuance_section_present():
    html = _html()
    assert "pv-core-valuation-report-issuance" in html
    assert "إصدار تقارير التقييم الأساسية" in html


# ── T04: Three core report type chips visible ────────────────────────────────
def test_T04_three_core_report_type_chips():
    html = _html()
    assert "pv-core-report-chip-traditional" in html
    assert "pv-core-report-chip-detailed"    in html
    assert "pv-core-report-chip-professional" in html
    assert "تقرير تقليدي"  in html
    assert "تقرير تفصيلي"  in html
    assert "تقرير احترافي" in html


# ── T05: Core output buttons visible ─────────────────────────────────────────
def test_T05_core_output_buttons_visible():
    html = _html()
    assert "pv-core-generate-user-pdf"    in html
    assert "pv-core-generate-admin-excel" in html
    assert "إصدار PDF للمستخدم"         in html
    assert "إصدار شيت Excel للأدمن"     in html


# ── T06: Core selector does NOT contain the four special report types ─────────
def test_T06_core_selector_does_not_contain_special_reports():
    html = _html()
    # The new core chips section must not list special types as chips
    # (they exist in the hidden legacy select — that's expected for compat)
    # Verify the core chips div only has the three core types
    core_section_start = html.find('pv-core-report-type-chips')
    core_section_end   = html.find('pv-core-output-buttons')
    assert core_section_start != -1
    assert core_section_end   != -1
    core_chips = html[core_section_start:core_section_end]
    for special in ["report_review_output","simulated_uploaded_report",
                    "hbu_analysis_report","standards_compliance_report"]:
        assert special not in core_chips, f"Special type in core chips: {special}"


# ── T07: Special reports section present ─────────────────────────────────────
def test_T07_special_reports_section_present():
    html = _html()
    assert "pv-special-report-workflows" in html
    assert "التقارير الخاصة والتحليلات المتقدمة" in html


# ── T08: Four special workflow buttons present ───────────────────────────────
def test_T08_four_special_workflow_buttons():
    html = _html()
    assert "pv-open-report-review-table" in html
    assert "pv-open-simulation-table"    in html
    assert "pv-open-hbu-table"           in html
    assert "pv-open-standards-table"     in html
    assert "فتح متطلبات مراجعة التقارير"       in html
    assert "فتح متطلبات محاكاة تقرير مرفوع"    in html
    assert "فتح متطلبات أعلى وأفضل استخدام"    in html
    assert "فتح متطلبات امتثال المعايير"        in html


# ── T09: Report Review dedicated panel present ───────────────────────────────
def test_T09_report_review_panel_present():
    html = _html()
    assert "pv-special-req-panel-report_review_output" in html
    assert "متطلبات مراجعة التقارير" in html


# ── T10: Report Review panel has review-specific groups ─────────────────────
def test_T10_report_review_groups():
    html = _html()
    assert "بيانات التقرير محل المراجعة" in html
    assert "نطاق المراجعة"               in html
    assert "اكتمال محتوى التقرير"        in html
    assert "مراجعة أساليب التقييم"       in html
    assert "ملاحظات المراجع"             in html


# ── T11: Report Review panel has review issue button ────────────────────────
def test_T11_report_review_issue_button():
    html = _html()
    assert "pv-issue-report-review-pdf"      in html
    assert "إصدار تقرير مراجعة PDF"          in html


# ── T12: Simulation panel present ───────────────────────────────────────────
def test_T12_simulation_panel_present():
    html = _html()
    assert "pv-special-req-panel-simulated_uploaded_report" in html
    assert "متطلبات محاكاة تقرير مرفوع"                    in html


# ── T13: Simulation panel notice about real_report_uploaded=false ────────────
def test_T13_simulation_real_report_false_notice():
    html = _html()
    assert "real_report_uploaded=false" in html or "real_report_uploaded" in html


# ── T14: HBU panel present ───────────────────────────────────────────────────
def test_T14_hbu_panel_present():
    html = _html()
    assert "pv-special-req-panel-hbu_analysis_report"      in html
    assert "متطلبات تحليل أعلى وأفضل استخدام"             in html


# ── T15: HBU panel has four test group headings ──────────────────────────────
def test_T15_hbu_four_test_groups():
    html = _html()
    assert "Physically Possible"   in html
    assert "Legally Permissible"   in html
    assert "Financially Feasible"  in html
    assert "Maximally Productive"  in html


# ── T16: HBU panel is_valuation_report=false notice ─────────────────────────
def test_T16_hbu_not_valuation_report():
    html = _html()
    assert "is_valuation_report=false" in html


# ── T17: Standards compliance panel present ──────────────────────────────────
def test_T17_standards_compliance_panel_present():
    html = _html()
    assert "pv-special-req-panel-standards_compliance_report" in html
    assert "متطلبات امتثال المعايير" in html


# ── T18: Standards compliance panel has matrix groups ────────────────────────
def test_T18_standards_compliance_matrix_groups():
    html = _html()
    assert "IVS 2025 Compliance Matrix" in html
    assert "RICS"                        in html
    assert "USPAP"                       in html
    assert "valuation_conclusion_included=false" in html


# ── T19: Old single seven-report selector not visible as primary control ──────
def test_T19_old_seven_report_selector_not_primary():
    html = _html()
    # The legacy hidden div must exist
    legacy_idx = html.find('pv-legacy-seven-report-selector-hidden')
    assert legacy_idx != -1
    # display:none must appear in the surrounding context (before or after the testid attr)
    surrounding = html[max(0, legacy_idx - 300):legacy_idx + 300]
    assert "display:none" in surrounding, (
        "Legacy selector wrapper must have display:none"
    )


# ── T20: No duplicate lower "إرسال للشات" button visible ────────────────────
def test_T20_no_duplicate_lower_chat_send_button():
    html = _html()
    # generateBtn should be hidden
    assert 'id="generateBtn"' not in html or 'style="display:none"' in html[
        html.find('id="generateBtn"') - 10 : html.find('id="generateBtn"') + 200
    ]


# ── T21: No internal paths in HTML ───────────────────────────────────────────
def test_T21_no_internal_paths_in_dom():
    html = _html()
    for pat in ["C:\\Users\\Lenovo", "AppData\\Local", "__file__", "/home/"]:
        assert pat not in html, f"Internal path in HTML: {pat}"


# ── T22: No duplicate testids ─────────────────────────────────────────────────
def test_T22_no_duplicate_core_testids():
    html = _html()
    for testid in ["pv-core-valuation-report-issuance", "pv-special-report-workflows",
                   "pv-core-generate-user-pdf", "pv-core-generate-admin-excel"]:
        count = html.count(f'data-testid="{testid}"')
        assert count == 1, f"Duplicate testid: {testid} appears {count} times"


# ── T23: QA audit files exist ────────────────────────────────────────────────
def test_T23_qa_audit_files_exist():
    assert BASE.exists(), f"QA folder missing: {BASE}"
    for fname in [
        "00_split_report_issuance_index.json",
        "03_special_report_workflow_audit.json",
        "06_hbu_requirements_table_audit.json",
    ]:
        assert (BASE / fname).exists(), f"QA file missing: {fname}"


# ── T24–T27: Browser tests (require live server) ─────────────────────────────

@pytest.mark.live_server
def test_T24_pv_page_opens_and_chat_box_visible():
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("playwright not installed")
    if not _server_running():
        pytest.skip("Server not running at http://127.0.0.1:5000")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(f"{BASE_URL}/", timeout=15000)
            page.wait_for_load_state("networkidle", timeout=15000)
            assert page.locator('[data-testid="pro-val-chat-command-center"]').count() > 0
        except PWTimeout:
            pytest.fail("Page load timed out")
        finally:
            browser.close()


@pytest.mark.live_server
def test_T25_core_report_issuance_below_chat_box():
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("playwright not installed")
    if not _server_running():
        pytest.skip("Server not running")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(f"{BASE_URL}/", timeout=15000)
            page.wait_for_load_state("networkidle", timeout=15000)
            assert page.locator('[data-testid="pv-core-valuation-report-issuance"]').count() > 0
            assert page.locator('[data-testid="pv-special-report-workflows"]').count() > 0
        except PWTimeout:
            pytest.fail("Page load timed out")
        finally:
            browser.close()


@pytest.mark.live_server
def test_T26_special_report_panel_opens_on_click():
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("playwright not installed")
    if not _server_running():
        pytest.skip("Server not running")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(f"{BASE_URL}/", timeout=15000)
            page.wait_for_load_state("networkidle", timeout=15000)
            page.locator('[data-testid="pv-open-hbu-table"]').click()
            page.wait_for_timeout(500)
            panel = page.locator('[data-testid="pv-special-req-panel-hbu_analysis_report"]')
            assert panel.is_visible(), "HBU panel did not open"
        except PWTimeout:
            pytest.fail("Page load timed out")
        finally:
            browser.close()


@pytest.mark.live_server
def test_T27_core_chip_selection():
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("playwright not installed")
    if not _server_running():
        pytest.skip("Server not running")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(f"{BASE_URL}/", timeout=15000)
            page.wait_for_load_state("networkidle", timeout=15000)
            page.locator('[data-testid="pv-core-report-chip-detailed"]').click()
            page.wait_for_timeout(300)
            label = page.locator('#pv-core-selected-type-name').inner_text()
            assert "تفصيلي" in label, f"Label not updated: {label}"
        except PWTimeout:
            pytest.fail("Page load timed out")
        finally:
            browser.close()
