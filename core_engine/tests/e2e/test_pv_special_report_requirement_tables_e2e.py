# test_pv_special_report_requirement_tables_e2e.py
# E2E tests — Special Report Requirement Tables (Second Key)
# advisory_only=True | not_real_training=True | no_commit=True
#
# T01–T31: Static HTML checks — run without live server.
# T32–T35: Playwright browser tests — require live server + @pytest.mark.live_server.

import pathlib
import pytest

pytestmark = pytest.mark.e2e

HTML = pathlib.Path("frontend/index.html")
BASE_URL = "http://127.0.0.1:5000"

SPECIAL_TYPES = [
    "report_review_output",
    "simulated_uploaded_report",
    "hbu_analysis_report",
    "standards_compliance_report"
]

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
    assert HTML.exists()
    assert "valuation" in _html().lower() or "تقييم" in _html()


# ── T02: Special reports section visible ─────────────────────────────────────
def test_T02_special_reports_section_visible():
    html = _html()
    assert "pv-special-report-workflows" in html
    assert "التقارير الخاصة والتحليلات المتقدمة" in html


# ── T03: Four special workflow buttons visible ────────────────────────────────
def test_T03_four_special_workflow_buttons():
    html = _html()
    assert "فتح متطلبات مراجعة التقارير" in html
    assert "فتح متطلبات محاكاة تقرير مرفوع" in html
    assert "فتح متطلبات أعلى وأفضل استخدام" in html
    assert "فتح متطلبات امتثال المعايير" in html
    assert "pv-open-report-review-table" in html
    assert "pv-open-simulation-table" in html
    assert "pv-open-hbu-table" in html
    assert "pv-open-standards-table" in html


# ── T04: Report Review panel present ─────────────────────────────────────────
def test_T04_report_review_panel_present():
    html = _html()
    assert "pv-special-req-panel-report_review_output" in html


# ── T05: Report Review panel has correct title ───────────────────────────────
def test_T05_report_review_panel_title():
    assert "متطلبات مراجعة التقارير" in _html()


# ── T06: All eight report review groups visible ───────────────────────────────
def test_T06_report_review_eight_groups():
    html = _html()
    assert "بيانات التقرير محل المراجعة" in html
    assert "نطاق المراجعة" in html
    assert "اكتمال محتوى التقرير" in html
    assert "مراجعة أساليب التقييم" in html
    assert "مراجعة البيانات والمدخلات" in html
    assert "مراجعة الافتراضات والقيود" in html
    assert "مراجعة الامتثال للمعايير" in html
    assert "ملاحظات المراجع ومخاطر التقرير" in html


# ── T07: Report Review action button ─────────────────────────────────────────
def test_T07_report_review_action_button():
    html = _html()
    assert "pv-issue-report-review-pdf" in html
    assert "إصدار تقرير مراجعة PDF" in html


# ── T08: Simulation panel present ────────────────────────────────────────────
def test_T08_simulation_panel_present():
    assert "pv-special-req-panel-simulated_uploaded_report" in _html()


# ── T09: Simulation panel title ──────────────────────────────────────────────
def test_T09_simulation_panel_title():
    assert "متطلبات محاكاة تقرير مرفوع" in _html()


# ── T10: All seven simulation groups visible ──────────────────────────────────
def test_T10_simulation_seven_groups():
    html = _html()
    assert "حالة المادة المصدرية" in html
    assert "نطاق المحاكاة" in html
    assert "أقسام التقرير المفترضة" in html
    assert "بيانات الأصل المفترضة" in html
    assert "أساليب التقييم المفترضة" in html
    assert "الفجوات والمخاطر" in html
    assert "نتائج المحاكاة" in html


# ── T11: Simulation action button ────────────────────────────────────────────
def test_T11_simulation_action_button():
    html = _html()
    assert "pv-issue-simulation-pdf" in html
    assert "إصدار تقرير المحاكاة PDF" in html


# ── T12: HBU panel present ───────────────────────────────────────────────────
def test_T12_hbu_panel_present():
    assert "pv-special-req-panel-hbu_analysis_report" in _html()


# ── T13: HBU panel title ─────────────────────────────────────────────────────
def test_T13_hbu_panel_title():
    assert "متطلبات تحليل أعلى وأفضل استخدام" in _html()


# ── T14: Physically Possible group visible ───────────────────────────────────
def test_T14_hbu_physically_possible_group():
    assert "Physically Possible" in _html()


# ── T15: Legally Permissible group visible ───────────────────────────────────
def test_T15_hbu_legally_permissible_group():
    assert "Legally Permissible" in _html()


# ── T16: Financially Feasible group visible ──────────────────────────────────
def test_T16_hbu_financially_feasible_group():
    assert "Financially Feasible" in _html()


# ── T17: Maximally Productive group visible ──────────────────────────────────
def test_T17_hbu_maximally_productive_group():
    assert "Maximally Productive" in _html()


# ── T18: إضافة استخدام بديل button present ───────────────────────────────────
def test_T18_hbu_add_alternative_use_button():
    html = _html()
    assert "إضافة استخدام بديل" in html
    assert "pv-hbu-add-alternative" in html
    assert "pv-hbu-alternatives-container" in html


# ── T19: إضافة سيناريو button present ───────────────────────────────────────
def test_T19_hbu_add_scenario_button():
    html = _html()
    assert "إضافة سيناريو" in html
    assert "pv-hbu-add-scenario" in html
    assert "pv-hbu-scenarios-container" in html


# ── T20: HBU action button ───────────────────────────────────────────────────
def test_T20_hbu_action_button():
    html = _html()
    assert "pv-issue-hbu-pdf" in html
    assert "إصدار تقرير HBU PDF" in html


# ── T21: Standards compliance panel present ──────────────────────────────────
def test_T21_standards_panel_present():
    assert "pv-special-req-panel-standards_compliance_report" in _html()


# ── T22: Standards compliance panel title ────────────────────────────────────
def test_T22_standards_panel_title():
    assert "متطلبات امتثال المعايير" in _html()


# ── T23: IVS matrix visible ──────────────────────────────────────────────────
def test_T23_standards_ivs_matrix():
    html = _html()
    assert "sc-ivs-matrix" in html
    assert "IVS 2025 Compliance Matrix" in html


# ── T24: USPAP matrix visible ────────────────────────────────────────────────
def test_T24_standards_uspap_matrix():
    html = _html()
    assert "sc-uspap-matrix" in html


# ── T25: RICS matrix visible ─────────────────────────────────────────────────
def test_T25_standards_rics_matrix():
    html = _html()
    assert "sc-rics-matrix" in html


# ── T26: IFRS 13 matrix visible ──────────────────────────────────────────────
def test_T26_standards_ifrs13_matrix():
    html = _html()
    assert "sc-ifrs13-matrix" in html


# ── T27: Advisory result group visible ───────────────────────────────────────
def test_T27_standards_advisory_result_group():
    html = _html()
    assert "نتيجة الامتثال الاسترشادية" in html
    assert "pv-issue-standards-pdf" in html


# ── T28: Standards compliance action button ───────────────────────────────────
def test_T28_standards_action_button():
    html = _html()
    assert "إصدار تقرير امتثال المعايير PDF" in html


# ── T29: Core selector does NOT show special report types ────────────────────
def test_T29_core_selector_excludes_special_reports():
    html = _html()
    # Core chip section must not have special types
    core_start = html.find("pv-core-report-type-chips")
    core_end = html.find("pv-core-output-buttons")
    assert core_start != -1 and core_end != -1
    core_chips = html[core_start:core_end]
    for t in ["report_review_output", "simulated_uploaded_report", "hbu_analysis_report", "standards_compliance_report"]:
        assert t not in core_chips, f"Special type in core chips: {t}"


# ── T30: No generic chat paperclip for special reports ───────────────────────
def test_T30_no_generic_chat_paperclip_for_special_reports():
    html = _html()
    # The legacy select is hidden — special reports not exposed as chat-only actions
    legacy_idx = html.find("pv-legacy-seven-report-selector-hidden")
    assert legacy_idx != -1
    surrounding = html[max(0, legacy_idx - 50):legacy_idx + 100]
    assert "display:none" in surrounding


# ── T31: No internal paths in DOM ────────────────────────────────────────────
def test_T31_no_internal_paths_in_dom():
    html = _html()
    for pat in ["C:\\Users\\Lenovo", "AppData\\Local", "__file__", "/home/"]:
        assert pat not in html, f"Internal path in HTML: {pat}"


# ── T32–T35: Browser tests (require live server) ────────────────────────────

@pytest.mark.live_server
def test_T32_special_reports_section_visible_in_browser():
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
            assert page.locator('[data-testid="pv-special-report-workflows"]').count() > 0
        except PWTimeout:
            pytest.fail("Page load timed out")
        finally:
            browser.close()


@pytest.mark.live_server
def test_T33_hbu_panel_opens_on_click():
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
def test_T34_standards_panel_opens_matrices():
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
            page.locator('[data-testid="pv-open-standards-table"]').click()
            page.wait_for_timeout(500)
            assert page.locator('[data-testid="sc-ivs-matrix"]').count() > 0
            assert page.locator('[data-testid="sc-uspap-matrix"]').count() > 0
            assert page.locator('[data-testid="sc-rics-matrix"]').count() > 0
            assert page.locator('[data-testid="sc-ifrs13-matrix"]').count() > 0
        except PWTimeout:
            pytest.fail("Page load timed out")
        finally:
            browser.close()


@pytest.mark.live_server
def test_T35_report_review_panel_opens():
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
            page.locator('[data-testid="pv-open-report-review-table"]').click()
            page.wait_for_timeout(500)
            panel = page.locator('[data-testid="pv-special-req-panel-report_review_output"]')
            assert panel.is_visible(), "Report Review panel did not open"
        except PWTimeout:
            pytest.fail("Page load timed out")
        finally:
            browser.close()
