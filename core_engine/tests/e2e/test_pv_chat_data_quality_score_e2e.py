# test_pv_chat_data_quality_score_e2e.py
# E2E tests — Chat Data Quality Score for Professional Valuation
# advisory_only=True | not_real_training=True | no_commit=True
#
# T01–T12: Static HTML/Python checks — run without live server.
# T13–T19: Playwright browser tests — require live server + @pytest.mark.live_server.

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


# ── T01: HTML exists with valuation content ──────────────────────────────────
def test_T01_html_exists():
    assert HTML.exists()
    assert "تقييم" in _html()


# ── T02: Data quality score JS functions defined ─────────────────────────────
def test_T02_data_quality_js_functions_defined():
    html = _html()
    assert "function pvCalculateChatDataQualityScore" in html
    assert "function pvExtractMinimumRequirementCoverageFromChat" in html
    assert "function pvRenderChatDataQualityBadge" in html
    assert "function pvRenderMissingMinimumRequirementsFromChat" in html


# ── T03: pvSyncChatDataQualityToUnifiedContext defined ───────────────────────
def test_T03_pvSyncChatDataQualityToUnifiedContext_defined():
    assert "function pvSyncChatDataQualityToUnifiedContext" in _html()


# ── T04: pvUpdateReportReadinessFromChatQuality defined ──────────────────────
def test_T04_pvUpdateReportReadinessFromChatQuality_defined():
    assert "function pvUpdateReportReadinessFromChatQuality" in _html()


# ── T05: pvCompareChatInputsAgainstMinimumRequirements defined ───────────────
def test_T05_pvCompareChatInputsAgainstMinimumRequirements_defined():
    assert "function pvCompareChatInputsAgainstMinimumRequirements" in _html()


# ── T06: Quality level labels (Arabic) present in JS ────────────────────────
def test_T06_quality_level_labels_in_js():
    html = _html()
    assert "ضعيفة جداً" in html
    assert "ضعيفة" in html
    assert "مقبولة" in html
    assert "جيدة" in html
    assert "قوية" in html


# ── T07: Missing requirements area has correct testid ───────────────────────
def test_T07_missing_requirements_area_testid():
    assert 'data-testid="pv-chat-quality-missing-reqs"' in _html()


# ── T08: pvSyncChatDataQualityToUnifiedContext uses correct keys ──────────────
def test_T08_quality_context_keys_in_js():
    html = _html()
    assert "last_relevant_message_quality_level" in html
    assert "last_relevant_message_quality_score" in html
    assert "minimum_requirements_completed" in html
    assert "minimum_requirements_missing" in html
    assert "report_readiness_status" in html


# ── T09: Readiness statuses present in JS ────────────────────────────────────
def test_T09_readiness_statuses_in_js():
    html = _html()
    assert "not_ready" in html
    assert "partial" in html
    assert "reviewable_draft" in html
    assert "ready_for_expert_review" in html


# ── T10: Scoring weights present in JS ───────────────────────────────────────
def test_T10_scoring_weights_in_js():
    html = _html()
    assert "0.60" in html or "* 60" in html
    assert "0.20" in html or "* 20" in html


# ── T11: expert_review_required referenced in JS ─────────────────────────────
def test_T11_expert_review_required_in_js():
    assert "expert_review_required" in _html()


# ── T12: Python scorer gives correct result for comprehensive message ─────────
def test_T12_python_scorer_comprehensive_message():
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    from core_engine.professional_valuation_chat_intent_guard_context import (
        extract_minimum_requirement_coverage, calculate_chat_data_quality_score
    )
    msg = (
        "فندق تجاري على مساحة 5000 متر في منطقة الرياض، "
        "يحتاج تقرير احترافي لأغراض الرهن التمويلي. "
        "حالة المبنى جيدة، مؤجر بالكامل. سند ملكية صك. معايير IVS."
    )
    coverage = extract_minimum_requirement_coverage(msg)
    result = calculate_chat_data_quality_score(coverage)
    assert result["score"] >= 40, f"Score too low: {result['score']}"
    assert result["level"] in ("weak", "acceptable", "good", "strong")
    assert isinstance(result["missing"], list)
    assert result["expert_review_required"] is True


# ── T13–T19: Playwright browser tests ────────────────────────────────────────

@pytest.mark.live_server
def test_T13_page_opens():
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
            assert page.locator('[data-testid="pv-chat-data-quality-badge"]').count() > 0
        except PWTimeout:
            pytest.fail("Page load timed out")
        finally:
            browser.close()


@pytest.mark.live_server
def test_T14_weak_quality_badge_visible_for_weak_message():
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
            # Render a weak badge via JS
            page.evaluate("""
                pvRenderChatDataQualityBadge(12, 'very_weak',
                    ['موقع الأصل', 'مساحة الأصل', 'سند الملكية'],
                    'تم ذكر نوع الأصل فقط');
            """)
            page.wait_for_timeout(400)
            badge = page.locator('[data-testid="pv-chat-data-quality-badge"]')
            assert badge.is_visible(), "Quality badge should be visible"
        except PWTimeout:
            pytest.fail("Page load timed out")
        finally:
            browser.close()


@pytest.mark.live_server
def test_T15_missing_requirements_visible():
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
            page.evaluate("""
                pvRenderMissingMinimumRequirementsFromChat(
                    ['موقع الأصل', 'مساحة الأصل', 'سند الملكية', 'الغرض من التقييم']
                );
                document.getElementById('pv-chat-data-quality-badge').style.display = 'block';
            """)
            page.wait_for_timeout(400)
            missing_el = page.locator('[data-testid="pv-chat-quality-missing-reqs"]')
            assert missing_el.is_visible()
        except PWTimeout:
            pytest.fail("Page load timed out")
        finally:
            browser.close()


@pytest.mark.live_server
def test_T16_quality_context_synced_to_unified():
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
            page.evaluate("""
                pvSyncChatDataQualityToUnifiedContext({
                    level: 'weak', score: 30,
                    found: ['نوع الأصل'], missing: ['موقع الأصل'],
                    optional_found: [], readiness: 'partial',
                    reason: 'test', expert_review_required: true
                });
            """)
            level = page.evaluate("""
                window._pvUnifiedPageContext &&
                window._pvUnifiedPageContext.chat_data_quality_context &&
                window._pvUnifiedPageContext.chat_data_quality_context.last_relevant_message_quality_level
            """)
            assert level == "weak", f"Expected 'weak', got {level}"
        except PWTimeout:
            pytest.fail("Page load timed out")
        finally:
            browser.close()


@pytest.mark.live_server
def test_T17_report_readiness_updates():
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
            page.evaluate("pvUpdateReportReadinessFromChatQuality(75)")
            readiness = page.evaluate("""
                window._pvUnifiedPageContext &&
                window._pvUnifiedPageContext.chat_data_quality_context &&
                window._pvUnifiedPageContext.chat_data_quality_context.report_readiness_status
            """)
            assert readiness in ("reviewable_draft", "ready_for_expert_review"), \
                f"Unexpected readiness: {readiness}"
        except PWTimeout:
            pytest.fail("Page load timed out")
        finally:
            browser.close()
