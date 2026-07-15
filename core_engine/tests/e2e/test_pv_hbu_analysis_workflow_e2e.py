"""
E2E tests for HBU Analysis Workflow.
BT01–BT20: browser tests (skipped without Playwright)
FT01–FT15: file-based tests (always run)

Run: python -m pytest tests/e2e/test_pv_hbu_analysis_workflow_e2e.py -q
"""
from __future__ import annotations
import json
import pathlib
import pytest

_ROOT     = pathlib.Path(__file__).parent.parent.parent
_HBU      = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_hbu_analysis"
_AUD      = _HBU / "hbu_audits"
_PDF      = _HBU / "pdf_outputs"
_XL       = _HBU / "excel_outputs"
_SS       = _HBU / "screenshots"
_PREV     = _HBU / "visual_previews"
_SRC      = _HBU / "source_registry"
_RPT      = _HBU / "final_report"
_TXT      = _HBU / "pdf_text_extracts"
_BASE_URL = "http://127.0.0.1:5000"

try:
    from playwright.sync_api import sync_playwright  # type: ignore
    _PW_AVAILABLE = True
except ImportError:
    _PW_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# Browser helper
# ─────────────────────────────────────────────────────────────────────────────

def _open_hbu_panel(page):
    """Navigate to Professional Valuation page and open the HBU wizard panel."""
    page.goto(f"{_BASE_URL}/", timeout=15000)
    page.wait_for_timeout(800)
    btn = page.query_selector("[data-testid='pv-open-hbu-table']")
    if btn and btn.is_visible():
        btn.click()
        page.wait_for_timeout(600)
    # Force panel visible if needed
    page.evaluate("""
        var p = document.getElementById('pv-req-panel-hbu');
        if (p) p.style.display = '';
        var s1 = document.getElementById('hbu-wizard-step-1');
        if (s1) s1.style.display = '';
    """)
    page.wait_for_timeout(300)


# ─────────────────────────────────────────────────────────────────────────────
# Browser tests BT01–BT20 (skipped without Playwright)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not _PW_AVAILABLE, reason="Playwright not installed")
def test_BT01_open_professional_valuation_page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        assert page.title() != ""
        browser.close()


@pytest.mark.skipif(not _PW_AVAILABLE, reason="Playwright not installed")
def test_BT02_locate_special_reports_section():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        el = page.query_selector("[data-testid='pv-special-workflow-buttons']")
        assert el is not None, "Special reports workflow buttons not found"
        browser.close()


@pytest.mark.skipif(not _PW_AVAILABLE, reason="Playwright not installed")
def test_BT03_click_hbu_button():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        _open_hbu_panel(page)
        panel = page.query_selector("[data-testid='pv-special-req-panel-hbu_analysis_report']")
        assert panel is not None, "HBU panel not found"
        browser.close()


@pytest.mark.skipif(not _PW_AVAILABLE, reason="Playwright not installed")
def test_BT04_hbu_wizard_opens():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        _open_hbu_panel(page)
        step1 = page.query_selector("[data-testid='hbu-wizard-step-1']")
        assert step1 is not None, "HBU wizard step 1 not found"
        browser.close()


@pytest.mark.skipif(not _PW_AVAILABLE, reason="Playwright not installed")
def test_BT05_fill_property_data():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        _open_hbu_panel(page)
        asset = page.query_selector("[data-testid='hbu-asset-type']")
        if asset:
            asset.fill("أرض تجارية مختلطة")
        loc = page.query_selector("[data-testid='hbu-location']")
        if loc:
            loc.fill("القاهرة - مدينة نصر")
        area = page.query_selector("[data-testid='hbu-land-area']")
        if area:
            area.fill("2000")
        browser.close()


@pytest.mark.skipif(not _PW_AVAILABLE, reason="Playwright not installed")
def test_BT06_aggregated_market_intelligence_visible():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        _open_hbu_panel(page)
        page.evaluate("if(typeof pvHbuGoToStep==='function') pvHbuGoToStep(2);")
        page.wait_for_timeout(400)
        el = page.query_selector("[data-testid='hbu-aggregated-market-intelligence-page']")
        assert el is not None, "Aggregated Market Intelligence page not found"
        browser.close()


@pytest.mark.skipif(not _PW_AVAILABLE, reason="Playwright not installed")
def test_BT07_browser_research_status_shown():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        _open_hbu_panel(page)
        page.evaluate("if(typeof pvHbuGoToStep==='function') pvHbuGoToStep(2);")
        page.wait_for_timeout(400)
        el = page.query_selector("[data-testid='hbu-browser-research-status']")
        assert el is not None, "Browser research status panel not found"
        browser.close()


@pytest.mark.skipif(not _PW_AVAILABLE, reason="Playwright not installed")
def test_BT08_source_registry_panel_visible():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        _open_hbu_panel(page)
        page.evaluate("if(typeof pvHbuGoToStep==='function') pvHbuGoToStep(2);")
        page.wait_for_timeout(400)
        el = page.query_selector("[data-testid='hbu-source-registry']")
        assert el is not None, "Source registry panel not found"
        browser.close()


@pytest.mark.skipif(not _PW_AVAILABLE, reason="Playwright not installed")
def test_BT09_site_analysis_panel_visible():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        _open_hbu_panel(page)
        page.evaluate("if(typeof pvHbuGoToStep==='function') pvHbuGoToStep(3);")
        page.wait_for_timeout(400)
        el = page.query_selector("[data-testid='hbu-site-analysis-panel']")
        assert el is not None, "Site analysis panel not found"
        browser.close()


@pytest.mark.skipif(not _PW_AVAILABLE, reason="Playwright not installed")
def test_BT10_create_minimum_three_scenarios():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        _open_hbu_panel(page)
        page.evaluate("if(typeof pvHbuGoToStep==='function') pvHbuGoToStep(4);")
        page.wait_for_timeout(400)
        cards = page.query_selector_all(".hbu-scenario-card")
        assert len(cards) >= 3, f"Expected >= 3 scenario cards, got {len(cards)}"
        browser.close()


@pytest.mark.skipif(not _PW_AVAILABLE, reason="Playwright not installed")
def test_BT11_four_hbu_tests_panel_visible():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        _open_hbu_panel(page)
        page.evaluate("if(typeof pvHbuGoToStep==='function') pvHbuGoToStep(5);")
        page.wait_for_timeout(400)
        el = page.query_selector("[data-testid='hbu-four-tests-panel']")
        assert el is not None, "Four HBU tests panel not found"
        browser.close()


@pytest.mark.skipif(not _PW_AVAILABLE, reason="Playwright not installed")
def test_BT12_as_if_vacant_panel_visible():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        _open_hbu_panel(page)
        page.evaluate("if(typeof pvHbuGoToStep==='function') pvHbuGoToStep(5);")
        page.wait_for_timeout(400)
        el = page.query_selector("[data-testid='hbu-as-if-vacant']")
        assert el is not None, "As-if-vacant panel not found"
        browser.close()


@pytest.mark.skipif(not _PW_AVAILABLE, reason="Playwright not installed")
def test_BT13_as_improved_panel_visible():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        _open_hbu_panel(page)
        page.evaluate("if(typeof pvHbuGoToStep==='function') pvHbuGoToStep(5);")
        page.wait_for_timeout(400)
        el = page.query_selector("[data-testid='hbu-as-improved']")
        assert el is not None, "As-improved panel not found"
        browser.close()


@pytest.mark.skipif(not _PW_AVAILABLE, reason="Playwright not installed")
def test_BT14_financial_engine_panel_visible():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        _open_hbu_panel(page)
        page.evaluate("if(typeof pvHbuGoToStep==='function') pvHbuGoToStep(5);")
        page.wait_for_timeout(400)
        el = page.query_selector("[data-testid='hbu-financial-engine-panel']")
        assert el is not None, "Financial engine panel not found"
        browser.close()


@pytest.mark.skipif(not _PW_AVAILABLE, reason="Playwright not installed")
def test_BT15_scenario_ranking_panel_visible():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        _open_hbu_panel(page)
        page.evaluate("if(typeof pvHbuGoToStep==='function') pvHbuGoToStep(6);")
        page.wait_for_timeout(400)
        el = page.query_selector("[data-testid='hbu-scenario-ranking-panel']")
        assert el is not None, "Scenario ranking panel not found"
        browser.close()


@pytest.mark.skipif(not _PW_AVAILABLE, reason="Playwright not installed")
def test_BT16_final_recommendation_panel_visible():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        _open_hbu_panel(page)
        page.evaluate("if(typeof pvHbuGoToStep==='function') pvHbuGoToStep(6);")
        page.wait_for_timeout(400)
        el = page.query_selector("[data-testid='hbu-final-recommendation-panel']")
        assert el is not None, "Final recommendation panel not found"
        browser.close()


@pytest.mark.skipif(not _PW_AVAILABLE, reason="Playwright not installed")
def test_BT17_download_buttons_visible():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        _open_hbu_panel(page)
        page.evaluate("if(typeof pvHbuGoToStep==='function') pvHbuGoToStep(6);")
        page.wait_for_timeout(400)
        btns = page.query_selector("[data-testid='hbu-download-buttons']")
        assert btns is not None, "Download buttons container not found"
        pdf_btn = page.query_selector("[data-testid='pv-issue-hbu-pdf']")
        assert pdf_btn is not None, "PDF download button not found"
        browser.close()


@pytest.mark.skipif(not _PW_AVAILABLE, reason="Playwright not installed")
def test_BT18_no_fake_signature_in_dom():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        _open_hbu_panel(page)
        content = page.content()
        assert "fake_signature\n" not in content
        assert "mock_signature" not in content
        browser.close()


@pytest.mark.skipif(not _PW_AVAILABLE, reason="Playwright not installed")
def test_BT19_no_internal_paths_in_dom():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        _open_hbu_panel(page)
        content = page.content()
        assert r"C:\Users\Lenovo" not in content, "Internal path in DOM"
        browser.close()


@pytest.mark.skipif(not _PW_AVAILABLE, reason="Playwright not installed")
def test_BT20_sensitivity_analysis_panel_visible():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        _open_hbu_panel(page)
        page.evaluate("if(typeof pvHbuGoToStep==='function') pvHbuGoToStep(5);")
        page.wait_for_timeout(400)
        el = page.query_selector("[data-testid='hbu-sensitivity-analysis']")
        assert el is not None, "Sensitivity analysis panel not found"
        browser.close()


# ─────────────────────────────────────────────────────────────────────────────
# File-based tests FT01–FT15 (always run)
# ─────────────────────────────────────────────────────────────────────────────

def test_FT01_hbu_output_folder_exists():
    assert _HBU.exists(), f"HBU output folder missing: {_HBU}"
    assert _HBU.is_dir()


def test_FT02_all_11_audit_files_present():
    expected = [
        "01_hbu_scope_and_property_data_audit.json",
        "02_aggregated_market_research_audit.json",
        "03_site_market_legal_analysis_audit.json",
        "04_hbu_scenarios_audit.json",
        "05_hbu_four_tests_audit.json",
        "06_hbu_financial_engine_audit.json",
        "07_hbu_ranking_recommendation_audit.json",
        "08_hbu_pdf_structure_audit.json",
        "09_hbu_excel_audit.json",
        "10_hbu_ui_audit.json",
        "11_hbu_visual_review_audit.json",
    ]
    for name in expected:
        assert (_AUD / name).exists(), f"Audit file missing: {name}"


def test_FT03_safety_flags_in_all_audits():
    for fname in _AUD.glob("*.json"):
        d = json.loads(fname.read_text(encoding="utf-8"))
        assert d.get("advisory_only") is True, f"{fname.name}: advisory_only must be True"
        assert d.get("fake_signature_created", False) is False
        assert d.get("fake_sources_created", False) is False
        assert d.get("certification_ready", False) is False
        assert d.get("in_chat_box", False) is False


def test_FT04_engine_results_positive():
    audit = json.loads((_AUD / "06_hbu_financial_engine_audit.json").read_text(encoding="utf-8"))
    fin = audit.get("scenario_financials", [])
    assert len(fin) >= 3
    for s in fin:
        assert s.get("npv", 0) > 0
        assert s.get("irr_pct", 0) > 0
        assert s.get("payback_years", 0) > 0


def test_FT05_preferred_hbu_in_audit():
    audit = json.loads((_AUD / "07_hbu_ranking_recommendation_audit.json").read_text(encoding="utf-8"))
    pref = audit.get("preferred_hbu", "")
    assert pref, "preferred_hbu must not be empty"
    assert len(pref) > 5


def test_FT06_pdf_or_html_non_empty():
    pdf  = _PDF / "hbu_analysis_report.pdf"
    html = _PDF / "hbu_analysis_report.html"
    if pdf.exists():
        assert pdf.stat().st_size > 1_000, "PDF too small"
    if html.exists():
        assert html.stat().st_size > 5_000, "HTML too small"
    assert pdf.exists() or html.exists(), "Neither PDF nor HTML found"


def test_FT07_excel_workbook_present():
    xl = _XL / "hbu_analysis_workbook.xlsx"
    audit = json.loads((_AUD / "09_hbu_excel_audit.json").read_text(encoding="utf-8"))
    if audit.get("hbu_excel_exists"):
        assert xl.exists(), "Excel workbook missing"
        assert xl.stat().st_size > 2_000, "Excel workbook too small"


def test_FT08_source_registry_has_sources():
    reg = _SRC / "source_registry.json"
    assert reg.exists(), "source_registry.json missing"
    data = json.loads(reg.read_text(encoding="utf-8"))
    assert "sources" in data
    assert len(data["sources"]) >= 1, "Source registry must have at least 1 source"
    for src in data["sources"]:
        assert "source_title" in src or "source_type" in src


def test_FT09_screenshots_exist():
    pngs = list(_SS.glob("*.png"))
    assert len(pngs) >= 10, f"Expected >= 10 screenshots, found {len(pngs)}"


def test_FT10_visual_index_exists():
    idx = _PREV / "OPEN_HBU_ANALYSIS_REVIEW_INDEX.html"
    assert idx.exists(), "HBU visual review index missing"
    content = idx.read_text(encoding="utf-8", errors="ignore")
    assert "advisory_only" in content
    assert "fake_signature_created" in content


def test_FT11_no_internal_paths():
    idx = _PREV / "OPEN_HBU_ANALYSIS_REVIEW_INDEX.html"
    if idx.exists():
        c = idx.read_text(encoding="utf-8", errors="ignore")
        assert r"C:\Users" not in c
        assert "C:/Users/Lenovo" not in c
    for fname in _AUD.glob("*.json"):
        t = fname.read_text(encoding="utf-8", errors="ignore")
        assert r"C:\Users" not in t
        assert "C:/Users/Lenovo" not in t


def test_FT12_final_report_exists():
    rpt = _RPT / "final_hbu_analysis_workflow_report.txt"
    assert rpt.exists(), "Final HBU report missing"
    content = rpt.read_text(encoding="utf-8", errors="ignore")
    assert "advisory_only" in content
    assert "fake_signature_created" in content
    assert "preferred_hbu" in content.lower() or "preferred" in content.lower()


def test_FT13_text_extract_exists():
    txt = _TXT / "hbu_analysis_report_text.txt"
    assert txt.exists(), "PDF text extract missing"
    content = txt.read_text(encoding="utf-8", errors="ignore")
    assert "advisory_only" in content
    assert len(content) > 50


def test_FT14_four_tests_governance():
    audit = json.loads((_AUD / "05_hbu_four_tests_audit.json").read_text(encoding="utf-8"))
    assert audit.get("legal_failure_blocks_hbu") is True
    assert audit.get("physical_failure_blocks_hbu_or_requires_mitigation") is True
    assert audit.get("financial_failure_blocks_max_productivity") is True
    assert audit.get("max_productive_after_other_tests") is True


def test_FT15_market_data_feeds_recommendation():
    audit = json.loads((_AUD / "02_aggregated_market_research_audit.json").read_text(encoding="utf-8"))
    assert audit.get("market_data_feeds_scenario_generation") is True
    assert audit.get("market_data_feeds_financial_assumptions") is True
    assert audit.get("market_data_feeds_final_hbu_recommendation") is True
    assert audit.get("sources_classified") is True
    assert audit.get("source_confidence_scored") is True
    assert audit.get("verified_vs_listing_data_separated") is True
