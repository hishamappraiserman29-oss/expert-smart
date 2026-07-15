# test_pv_chat_box_report_control_simplification_e2e.py
# E2E tests — Chat Box Report Control Simplification
# advisory_only=True | not_real_training=True | no_commit=True
#
# T01–T22: Static HTML checks — run without live server.
# T23–T27: Playwright browser tests — require live server + @pytest.mark.live_server.

import pathlib
import pytest

pytestmark = pytest.mark.e2e

HTML = pathlib.Path("frontend/index.html")
BASE_URL = "http://127.0.0.1:5000"

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


# ── T02: Chat Box visible in HTML ────────────────────────────────────────────
def test_T02_chat_box_visible():
    assert "pro-val-chat-command-center" in _html()


# ── T03: Core report section visible ─────────────────────────────────────────
def test_T03_core_report_section_visible():
    html = _html()
    assert "pv-core-valuation-report-issuance" in html
    assert "إصدار تقارير التقييم الأساسية" in html


# ── T04: Helper text visible ─────────────────────────────────────────────────
def test_T04_helper_text_visible():
    html = _html()
    assert "pv-core-report-helper-text" in html
    assert "اضغط على نوع التقرير لإصدار نسخة PDF للمستخدم وشيت Excel للأدمن تلقائياً." in html


# ── T05: Three core report action chips visible ───────────────────────────────
def test_T05_three_core_report_chips_visible():
    html = _html()
    assert "pv-core-report-chip-traditional" in html
    assert "pv-core-report-chip-detailed" in html
    assert "pv-core-report-chip-professional" in html
    assert "تقرير تقليدي" in html
    assert "تقرير تفصيلي" in html
    assert "تقرير احترافي" in html


# ── T06: Chip onclick calls pvGenerateCoreReportBundle ───────────────────────
def test_T06_chips_call_pvGenerateCoreReportBundle():
    html = _html()
    assert "pvGenerateCoreReportBundle('traditional_report')" in html
    assert "pvGenerateCoreReportBundle('detailed_report')" in html
    assert "pvGenerateCoreReportBundle('professional_report')" in html


# ── T07: Separate PDF button not visible ─────────────────────────────────────
def test_T07_separate_pdf_button_not_visible():
    html = _html()
    # pv-core-output-buttons must be display:none
    idx = html.find('data-testid="pv-core-output-buttons"')
    assert idx != -1
    # grab surrounding context
    snippet = html[max(0, idx - 50):idx + 200]
    assert "display:none" in snippet, "pv-core-output-buttons must be hidden"


# ── T08: Separate Excel button not visible ────────────────────────────────────
def test_T08_separate_excel_button_not_visible():
    html = _html()
    ob_idx = html.find('data-testid="pv-core-output-buttons"')
    assert ob_idx != -1
    # The wrapper div opening tag spans ~150 chars — look for display:none within that range
    ob_tag = html[ob_idx:ob_idx + 200]
    assert "display:none" in ob_tag, "pv-core-output-buttons wrapper must have display:none"
    assert "pv-core-generate-admin-excel" in html


# ── T09: Bundle status area present ──────────────────────────────────────────
def test_T09_bundle_status_area_present():
    html = _html()
    assert "pv-core-bundle-status" in html
    assert "pv-bundle-pdf-status" in html
    assert "pv-bundle-excel-status" in html


# ── T10: Simulation upload clip removed from Chat Box ────────────────────────
def test_T10_simulation_upload_clip_removed():
    html = _html()
    # Sentinel span must be present
    assert "pv-chat-simulation-upload-removed" in html
    # The clip must not appear as an HTML element (data-testid attribute on a div)
    # JS querySelector references to the old testid are acceptable
    assert '<div data-testid="pro-val-simulation-report-clip"' not in html, \
        "simulation clip still rendered as a div element in HTML"


# ── T11: Report review upload clip removed from Chat Box ─────────────────────
def test_T11_report_review_upload_clip_removed():
    html = _html()
    assert "pv-chat-review-upload-removed" in html
    assert '<div data-testid="pro-val-review-report-clip"' not in html, \
        "review clip still rendered as a div element in HTML"


# ── T12: "إرسال للشات" not present as visible button text ───────────────────
def test_T12_send_to_chat_not_visible():
    html = _html()
    # Acceptable occurrences: inside HTML comments, inside JS strings (archived label)
    # Must not appear as rendered button content (between <button> tags)
    import re
    button_texts = re.findall(r'<button[^>]*>(.*?)</button>', html, re.DOTALL)
    for bt in button_texts:
        assert "إرسال للشات" not in bt, "إرسال للشات found as visible button text"


# ── T13: Advisory notice preserved ───────────────────────────────────────────
def test_T13_advisory_notice_preserved():
    assert "جميع المخرجات استرشادية غير معتمدة" in _html()


# ── T14: Special report section still present ────────────────────────────────
def test_T14_special_report_section_present():
    html = _html()
    assert "pv-special-report-workflows" in html
    assert "التقارير الخاصة والتحليلات المتقدمة" in html


# ── T15: All four special report buttons still present ───────────────────────
def test_T15_special_report_buttons_present():
    html = _html()
    assert "فتح متطلبات مراجعة التقارير" in html
    assert "فتح متطلبات محاكاة تقرير مرفوع" in html
    assert "فتح متطلبات أعلى وأفضل استخدام" in html
    assert "فتح متطلبات امتثال المعايير" in html


# ── T16: pvGenerateCoreReportBundle JS function defined ──────────────────────
def test_T16_pvGenerateCoreReportBundle_defined():
    assert "function pvGenerateCoreReportBundle" in _html()


# ── T17: pvSyncCoreReportOutputBundleContext JS function defined ──────────────
def test_T17_pvSyncCoreReportOutputBundleContext_defined():
    assert "function pvSyncCoreReportOutputBundleContext" in _html()


# ── T18: trigger_mode in JS context ──────────────────────────────────────────
def test_T18_trigger_mode_in_js():
    assert "report_type_click_generates_both_outputs" in _html()


# ── T19: removed_buttons list in JS context ──────────────────────────────────
def test_T19_removed_buttons_in_js_context():
    html = _html()
    assert "إصدار PDF للمستخدم" in html          # referenced in removed_buttons array
    assert "إصدار شيت Excel للأدمن" in html      # referenced in removed_buttons array


# ── T20: chat_upload_shortcuts_removed list in JS context ────────────────────
def test_T20_chat_upload_shortcuts_in_js():
    assert "simulation_report_upload" in _html()
    assert "report_review_upload" in _html()


# ── T21: No internal paths in DOM ────────────────────────────────────────────
def test_T21_no_internal_paths_in_dom():
    html = _html()
    for pat in ["C:\\Users\\Lenovo", "AppData\\Local", "__file__", "/home/"]:
        assert pat not in html, f"Internal path in HTML: {pat}"


# ── T22: Legacy hidden select preserved for backward compat ──────────────────
def test_T22_legacy_hidden_select_preserved():
    html = _html()
    assert "pv-legacy-seven-report-selector-hidden" in html
    assert "pv-chat-report-action" in html


# ── T23–T27: Browser tests (require live server) ─────────────────────────────

@pytest.mark.live_server
def test_T23_page_opens_in_browser():
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
        except PWTimeout:
            pytest.fail("Page load timed out")
        finally:
            browser.close()


@pytest.mark.live_server
def test_T24_traditional_chip_shows_bundle_status():
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
            page.locator('[data-testid="pv-core-report-chip-traditional"]').click()
            page.wait_for_timeout(600)
            bundle = page.locator('[data-testid="pv-core-bundle-status"]')
            assert bundle.is_visible(), "Bundle status area not visible after chip click"
        except PWTimeout:
            pytest.fail("Page load timed out")
        finally:
            browser.close()


@pytest.mark.live_server
def test_T25_detailed_chip_shows_bundle_status():
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
            page.wait_for_timeout(600)
            bundle = page.locator('[data-testid="pv-core-bundle-status"]')
            assert bundle.is_visible(), "Bundle status area not visible after detailed chip click"
        except PWTimeout:
            pytest.fail("Page load timed out")
        finally:
            browser.close()


@pytest.mark.live_server
def test_T26_professional_chip_shows_bundle_status():
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
            page.locator('[data-testid="pv-core-report-chip-professional"]').click()
            page.wait_for_timeout(600)
            bundle = page.locator('[data-testid="pv-core-bundle-status"]')
            assert bundle.is_visible(), "Bundle status area not visible after professional chip click"
        except PWTimeout:
            pytest.fail("Page load timed out")
        finally:
            browser.close()


@pytest.mark.live_server
def test_T27_special_report_section_visible_in_browser():
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
