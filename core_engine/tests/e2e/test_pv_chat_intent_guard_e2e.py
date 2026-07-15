# test_pv_chat_intent_guard_e2e.py
# E2E tests — Professional Valuation Chat Intent Guard
# advisory_only=True | not_real_training=True | no_commit=True
#
# T01–T20: Static HTML checks — run without live server.
# T21–T34: Playwright browser tests — require live server + @pytest.mark.live_server.

import pathlib
import re
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


# ── T01: HTML file exists ────────────────────────────────────────────────────
def test_T01_html_exists():
    assert HTML.exists()
    assert "valuation" in _html().lower() or "تقييم" in _html()


# ── T02: Chat Box visible in HTML ────────────────────────────────────────────
def test_T02_chat_box_visible():
    assert "pro-val-chat-command-center" in _html()


# ── T03: Intent guard warning area present in DOM ────────────────────────────
def test_T03_intent_guard_warning_area_present():
    html = _html()
    assert 'data-testid="pv-chat-intent-guard-warning"' in html
    assert 'id="pv-chat-intent-guard-warning"' in html


# ── T04: Warning area hidden by default ─────────────────────────────────────
def test_T04_intent_guard_warning_hidden_by_default():
    html = _html()
    idx = html.find('data-testid="pv-chat-intent-guard-warning"')
    assert idx != -1
    snippet = html[max(0, idx - 20):idx + 200]
    assert "display:none" in snippet, "Intent guard warning must be hidden by default"


# ── T05: Warning text contains required Arabic message ──────────────────────
def test_T05_warning_text_present_in_html():
    html = _html()
    assert "هذا الصندوق مخصص لإعداد ومراجعة تقرير التقييم المهني" in html


# ── T06: Quick actions area present ─────────────────────────────────────────
def test_T06_quick_actions_area_present():
    html = _html()
    assert 'data-testid="pv-chat-intent-guard-quick-actions"' in html


# ── T07: All five quick action buttons present ──────────────────────────────
def test_T07_five_quick_actions_present():
    html = _html()
    assert "إدخال بيانات أصل" in html
    assert "رفع مستند تقييم" in html
    assert "استكمال متطلبات التقرير" in html
    assert "إصدار تقرير تقييم" in html
    assert "فتح التقارير الخاصة" in html


# ── T08: Data quality badge area present ────────────────────────────────────
def test_T08_data_quality_badge_present():
    html = _html()
    assert 'data-testid="pv-chat-data-quality-badge"' in html
    assert 'id="pv-chat-data-quality-badge"' in html


# ── T09: Data quality badge hidden by default ────────────────────────────────
def test_T09_data_quality_badge_hidden_by_default():
    html = _html()
    idx = html.find('data-testid="pv-chat-data-quality-badge"')
    assert idx != -1
    snippet = html[max(0, idx - 20):idx + 200]
    assert "display:none" in snippet, "Data quality badge must be hidden by default"


# ── T10: Ambiguous confirmation area present ─────────────────────────────────
def test_T10_ambiguous_confirmation_area_present():
    html = _html()
    assert 'data-testid="pv-chat-ambiguous-confirmation"' in html


# ── T11: Ambiguous confirmation hidden by default ────────────────────────────
def test_T11_ambiguous_confirmation_hidden_by_default():
    html = _html()
    idx = html.find('data-testid="pv-chat-ambiguous-confirmation"')
    assert idx != -1
    snippet = html[max(0, idx - 20):idx + 200]
    assert "display:none" in snippet


# ── T12: Missing requirements area present ───────────────────────────────────
def test_T12_missing_requirements_area_present():
    assert 'pv-chat-quality-missing-reqs' in _html()


# ── T13: pvClassifyChatMessageIntent JS function defined ─────────────────────
def test_T13_pvClassifyChatMessageIntent_defined():
    assert "function pvClassifyChatMessageIntent" in _html()


# ── T14: pvHandleIrrelevantChatMessage JS function defined ───────────────────
def test_T14_pvHandleIrrelevantChatMessage_defined():
    assert "function pvHandleIrrelevantChatMessage" in _html()


# ── T15: pvHandleAmbiguousChatMessage JS function defined ────────────────────
def test_T15_pvHandleAmbiguousChatMessage_defined():
    assert "function pvHandleAmbiguousChatMessage" in _html()


# ── T16: pvCalculateChatDataQualityScore JS function defined ─────────────────
def test_T16_pvCalculateChatDataQualityScore_defined():
    assert "function pvCalculateChatDataQualityScore" in _html()


# ── T17: processAndGenerate override present ─────────────────────────────────
def test_T17_processAndGenerate_override_present():
    html = _html()
    assert "_pvOrigPAG" in html, "processAndGenerate override wrapper not found"
    assert "pvClassifyChatMessageIntent" in html


# ── T18: trigger_mode referenced in JS context ───────────────────────────────
def test_T18_intent_guard_trigger_mode_in_js():
    html = _html()
    assert "irrelevant_general_chat" in html
    assert "ambiguous_needs_confirmation" in html


# ── T19: Advisory notice preserved ───────────────────────────────────────────
def test_T19_advisory_notice_preserved():
    assert "جميع المخرجات استرشادية غير معتمدة" in _html()


# ── T20: No internal paths in DOM ────────────────────────────────────────────
def test_T20_no_internal_paths_in_dom():
    html = _html()
    for pat in ["C:\\Users\\Lenovo", "AppData\\Local", "__file__", "/home/"]:
        assert pat not in html, f"Internal path in HTML: {pat}"


# ── T21–T34: Playwright browser tests ────────────────────────────────────────

@pytest.mark.live_server
def test_T21_page_opens_in_browser():
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
            assert page.locator('[data-testid="pro-val-chat-command-center"]').count() > 0
        except PWTimeout:
            pytest.fail("Page load timed out")
        finally:
            browser.close()


@pytest.mark.live_server
def test_T22_chat_box_visible_in_browser():
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
            assert page.locator('[data-testid="pro-val-chat-input"]').count() > 0
        except PWTimeout:
            pytest.fail("Page load timed out")
        finally:
            browser.close()


@pytest.mark.live_server
def test_T23_relevant_message_accepted():
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
            textarea = page.locator('[data-testid="pro-val-chat-input"]')
            textarea.fill("العقار فندق على مساحة 5000 متر في الرياض ويحتاج تقرير احترافي")
            # Trigger the core report chip (which now calls processAndGenerate via guard)
            page.locator('[data-testid="pv-core-report-chip-traditional"]').click()
            page.wait_for_timeout(800)
            # Warning should NOT appear for a relevant message
            warn = page.locator('[data-testid="pv-chat-intent-guard-warning"]')
            assert not warn.is_visible(), "Warning should not appear for relevant message"
        except PWTimeout:
            pytest.fail("Page load timed out")
        finally:
            browser.close()


@pytest.mark.live_server
def test_T24_irrelevant_message_triggers_warning():
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
            textarea = page.locator('[data-testid="pro-val-chat-input"]')
            textarea.fill("أنا كنت في النادي وبحكي قصة ليس لها علاقة بالتقييم رحلة سياحية")
            # Click send via JS call
            page.evaluate("document.getElementById('generateBtn').style.display='block'")
            page.locator('[data-testid="pro-val-chat-send-button"]').click()
            page.wait_for_timeout(600)
            warn = page.locator('[data-testid="pv-chat-intent-guard-warning"]')
            assert warn.is_visible(), "Warning should appear for irrelevant message"
        except PWTimeout:
            pytest.fail("Page load timed out")
        finally:
            browser.close()


@pytest.mark.live_server
def test_T25_quick_actions_visible_after_block():
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
            # Trigger warning via JS
            page.evaluate("""
                pvRenderChatIntentGuardWarning(
                    'هذا الصندوق مخصص لإعداد ومراجعة تقرير التقييم المهني.'
                );
                pvRenderChatQuickActions();
            """)
            page.wait_for_timeout(400)
            qa = page.locator('[data-testid="pv-chat-intent-guard-quick-actions"]')
            assert qa.is_visible(), "Quick actions should be visible"
        except PWTimeout:
            pytest.fail("Page load timed out")
        finally:
            browser.close()


@pytest.mark.live_server
def test_T26_ambiguous_message_shows_confirmation():
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
            # Trigger ambiguous handler via JS
            page.evaluate("""
                pvHandleAmbiguousChatMessage('محتاج رأيك', {category:'ambiguous_needs_confirmation'});
            """)
            page.wait_for_timeout(400)
            amb = page.locator('[data-testid="pv-chat-ambiguous-confirmation"]')
            assert amb.is_visible(), "Ambiguous confirmation should be visible"
        except PWTimeout:
            pytest.fail("Page load timed out")
        finally:
            browser.close()


@pytest.mark.live_server
def test_T27_irrelevant_message_not_in_unified_context():
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
            # Trigger irrelevant message handler
            page.evaluate("""
                pvHandleIrrelevantChatMessage('كورة مباراة',
                    {category: 'irrelevant_general_chat'});
            """)
            page.wait_for_timeout(400)
            # Verify the context records it as NOT saved to report context
            saved = page.evaluate("""
                window._pvUnifiedPageContext &&
                window._pvUnifiedPageContext.chat_context &&
                window._pvUnifiedPageContext.chat_context.last_message_saved_to_report_context
            """)
            assert saved is False, "Irrelevant message must not be saved to report context"
        except PWTimeout:
            pytest.fail("Page load timed out")
        finally:
            browser.close()


@pytest.mark.live_server
def test_T28_no_internal_paths_in_browser():
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
            content = page.content()
            assert "C:\\Users\\Lenovo" not in content
            assert "AppData\\Local" not in content
        except PWTimeout:
            pytest.fail("Page load timed out")
        finally:
            browser.close()
