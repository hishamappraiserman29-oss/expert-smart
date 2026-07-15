"""
E2E / Visual tests for Report Review V2.1 UI panels.
Browser tests (BT01-BT17): skipped if Playwright not installed.
File-based tests (FT01-FT08): always run.
Run: python -m pytest tests/e2e/test_pv_report_review_v2_visual.py -q
"""
from __future__ import annotations
import json
import pathlib
import pytest

try:
    from playwright.sync_api import sync_playwright
    _PW_AVAILABLE = True
except ImportError:
    _PW_AVAILABLE = False

_pw_skip = pytest.mark.skipif(not _PW_AVAILABLE, reason="Playwright not installed")
_BASE_URL = "http://127.0.0.1:5000"

_ROOT = pathlib.Path(__file__).parent.parent.parent
_V2   = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_report_review_v2"
_AUD  = _V2 / "report_review_audits"
_PDF  = _V2 / "pdf_outputs"
_SS   = _V2 / "screenshots"


def _open_report_review_wizard(page):
    """Open the panel and show V2 results so elements are accessible."""
    page.goto(f"{_BASE_URL}/", timeout=15000)
    page.wait_for_timeout(800)
    btn = page.query_selector("[data-testid='pv-open-report-review-table']")
    if btn and btn.is_visible():
        btn.click()
        page.wait_for_timeout(600)
    # Show V2 panel via JS (it starts hidden; in prod it shows after generation)
    page.evaluate("var p = document.getElementById('rr-v2-results-panel'); if(p) p.style.display = '';")
    page.wait_for_timeout(300)


# ─────────────────────────────────────────────────────────────────────────────
# Browser tests — BT01 through BT17
# ─────────────────────────────────────────────────────────────────────────────

@_pw_skip
def test_BT01_page_loads():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        title = page.title()
        assert title or page.content()
        browser.close()


@_pw_skip
def test_BT02_report_review_trigger_exists():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        el = page.query_selector("[data-testid='pv-open-report-review-table']")
        assert el is not None, "Report review trigger button not found"
        _SS.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(_SS / "bt02_trigger_button.png"))
        browser.close()


@_pw_skip
def test_BT03_v2_executive_card_in_dom():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_report_review_wizard(page)
        el = page.query_selector("[data-testid='rr-executive-card-v2']")
        assert el is not None, "rr-executive-card-v2 not found in DOM"
        _SS.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(_SS / "review_v2_executive_card.png"))
        browser.close()


@_pw_skip
def test_BT04_v2_traffic_light_in_dom():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_report_review_wizard(page)
        el = page.query_selector("[data-testid='rr-traffic-light-v2']")
        assert el is not None, "rr-traffic-light-v2 not found in DOM"
        browser.close()


@_pw_skip
def test_BT05_v2_human_review_quick_list_in_dom():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_report_review_wizard(page)
        el = page.query_selector("[data-testid='rr-human-review-quick-list-v2']")
        assert el is not None, "rr-human-review-quick-list-v2 not found in DOM"
        page.screenshot(path=str(_SS / "review_v2_human_review_quick_list.png"))
        browser.close()


@_pw_skip
def test_BT06_v2_unified_compliance_table_in_dom():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_report_review_wizard(page)
        el = page.query_selector("[data-testid='rr-unified-compliance-table-v2']")
        assert el is not None, "rr-unified-compliance-table-v2 not found in DOM"
        page.screenshot(path=str(_SS / "review_v2_unified_compliance_table.png"))
        browser.close()


@_pw_skip
def test_BT07_v2_value_comparison_in_dom():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_report_review_wizard(page)
        el = page.query_selector("[data-testid='rr-value-comparison-v2']")
        assert el is not None, "rr-value-comparison-v2 not found in DOM"
        page.screenshot(path=str(_SS / "review_v2_value_comparison.png"))
        browser.close()


@_pw_skip
def test_BT08_v2_agents_heatmap_in_dom():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_report_review_wizard(page)
        el = page.query_selector("[data-testid='rr-agents-heatmap-v2']")
        assert el is not None, "rr-agents-heatmap-v2 not found in DOM"
        page.screenshot(path=str(_SS / "review_v2_agents_heatmap.png"))
        browser.close()


@_pw_skip
def test_BT09_v2_action_items_in_dom():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_report_review_wizard(page)
        el = page.query_selector("[data-testid='rr-action-items-v2']")
        assert el is not None, "rr-action-items-v2 not found in DOM"
        page.screenshot(path=str(_SS / "review_v2_action_items.png"))
        browser.close()


@_pw_skip
def test_BT10_v2_signature_gate_in_dom():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_report_review_wizard(page)
        el = page.query_selector("[data-testid='rr-signature-gate-v2']")
        assert el is not None, "rr-signature-gate-v2 not found in DOM"
        page.screenshot(path=str(_SS / "review_v2_signature_gate.png"))
        browser.close()


@_pw_skip
def test_BT11_v2_download_pdf_button_in_dom():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_report_review_wizard(page)
        el = page.query_selector("[data-testid='rr-download-v2-pdf']")
        assert el is not None, "rr-download-v2-pdf not found in DOM"
        browser.close()


@_pw_skip
def test_BT12_v21_extraction_panel_in_dom():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_report_review_wizard(page)
        el = page.query_selector("[data-testid='rr-extraction-quality-panel-v21']")
        assert el is not None, "rr-extraction-quality-panel-v21 not found in DOM"
        browser.close()


@_pw_skip
def test_BT13_v21_market_research_panel_in_dom():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_report_review_wizard(page)
        el = page.query_selector("[data-testid='rr-external-market-research-panel-v21']")
        assert el is not None, "rr-external-market-research-panel-v21 not found in DOM"
        browser.close()


@_pw_skip
def test_BT14_v21_critical_scoring_panel_in_dom():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_report_review_wizard(page)
        el = page.query_selector("[data-testid='rr-critical-scoring-panel-v21']")
        assert el is not None, "rr-critical-scoring-panel-v21 not found in DOM"
        browser.close()


@_pw_skip
def test_BT15_v21_hbu_gap_panel_in_dom():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_report_review_wizard(page)
        el = page.query_selector("[data-testid='rr-hbu-gap-suggestions-panel-v21']")
        assert el is not None, "rr-hbu-gap-suggestions-panel-v21 not found in DOM"
        browser.close()


@_pw_skip
def test_BT16_v21_uncertainty_range_panel_in_dom():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_report_review_wizard(page)
        el = page.query_selector("[data-testid='rr-uncertainty-range-panel-v21']")
        assert el is not None, "rr-uncertainty-range-panel-v21 not found in DOM"
        browser.close()


@_pw_skip
def test_BT17_no_fake_signature_in_dom():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        dom = page.content()
        for bad in ["fake_reviewer_signature\n", "mock_signature", "placeholder_signature"]:
            assert bad not in dom, f"Forbidden text '{bad}' found in DOM"
        assert "fake_reviewer_signature_created=False" in dom, (
            "Safety flag missing from DOM"
        )
        page.screenshot(path=str(_SS / "review_v2_review_index.png"))
        browser.close()


# ─────────────────────────────────────────────────────────────────────────────
# File-based tests — FT01 through FT08
# ─────────────────────────────────────────────────────────────────────────────

def test_FT01_v2_output_folder_exists():
    assert _V2.exists(), f"V2 output folder missing: {_V2}"


def test_FT02_v2_html_exists():
    html = _PDF / "report_review_output_v2.html"
    assert html.exists(), "report_review_output_v2.html not found"
    assert html.stat().st_size > 5_000, "V2 HTML is too small"


def test_FT03_visual_index_exists():
    idx = _V2 / "visual_previews" / "OPEN_REPORT_REVIEW_V2_REVIEW_INDEX.html"
    assert idx.exists(), "V2 visual index missing"


def test_FT04_all_v20_audits_exist():
    required = [
        "review_v2_traffic_light_audit.json",
        "review_v2_human_review_consolidation_audit.json",
        "review_v2_unified_compliance_table_audit.json",
        "review_v2_value_comparison_audit.json",
        "review_v2_agents_heatmap_audit.json",
        "review_v2_action_items_audit.json",
        "review_v2_signature_gate_audit.json",
        "review_v2_ui_audit.json",
        "review_v2_excel_audit.json",
        "review_v2_pdf_structure_audit.json",
    ]
    missing = [f for f in required if not (_AUD / f).exists()]
    assert not missing, f"Missing V2.0 audits: {missing}"


def test_FT05_all_v21_audits_exist():
    required = [
        "review_v21_external_market_research_audit.json",
        "review_v21_extraction_bottleneck_audit.json",
        "review_v21_critical_scoring_audit.json",
        "review_v21_hbu_gap_suggestions_audit.json",
        "review_v21_uncertainty_range_suggestion_audit.json",
        "review_v21_ui_panels_audit.json",
    ]
    missing = [f for f in required if not (_AUD / f).exists()]
    assert not missing, f"Missing V2.1 audits: {missing}"


def test_FT06_no_fake_signature_in_any_v2_audit():
    for f in _AUD.glob("review_v2*.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        assert d.get("fake_reviewer_signature_created", False) is False, (
            f"{f.name}: fake_reviewer_signature_created must be False"
        )


def test_FT07_final_report_exists():
    rpt = _V2 / "final_report" / "final_report_review_v2_report.txt"
    assert rpt.exists(), "Final report V2 missing"
    assert rpt.stat().st_size > 1_000


def test_FT08_text_extract_exists():
    txt = _V2 / "pdf_text_extracts" / "report_review_output_v2_text.txt"
    assert txt.exists(), "V2 text extract missing"
    content = txt.read_text(encoding="utf-8", errors="ignore")
    assert "executive" in content.lower() or "التقييم السريع" in content
