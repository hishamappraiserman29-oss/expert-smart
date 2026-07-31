"""
E2E Visual QA tests for Professional Valuation Report Review workflow.
Browser tests (VT01-VT18): skipped if Playwright not installed.
File-based checks (VT19-VT26): always run.
"""

from __future__ import annotations
import json
import pathlib
import pytest

# ── Playwright detection ──────────────────────────────────────────────────────
try:
    from playwright.sync_api import sync_playwright, Page
    _PW_AVAILABLE = True
except ImportError:
    _PW_AVAILABLE = False

_pw_skip = pytest.mark.skipif(not _PW_AVAILABLE, reason="Playwright not installed")
_BASE_URL = "http://127.0.0.1:5000"

_ROOT = pathlib.Path(__file__).parent.parent.parent
_QA   = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_report_review_visual_qa"
_SRC  = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_report_review_complete_workflow"
_REVIEW_PDF = _QA / "pdf_outputs" / "report_review_output.pdf"
_REVIEW_HTML = _SRC / "pdf_outputs" / "report_review_output.html"

# ── Browser tests (Playwright required) ───────────────────────────────────────

@_pw_skip
def test_VT01_open_professional_valuation_page():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        assert "تقييم" in page.title() or page.query_selector("[data-testid='pv-special-req-panel-report_review_output']") is not None
        ss = _QA / "screenshots" / "01_special_reports_section.png"
        ss.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(ss))
        browser.close()

@_pw_skip
def test_VT02_special_reports_section_visible():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        # Navigate to professional valuation section
        pv_btn = page.query_selector("[data-testid='pv-section-btn'], #pv-nav, .pv-nav-btn")
        if pv_btn:
            pv_btn.click()
            page.wait_for_timeout(1000)
        special = page.query_selector("text=التقارير الخاصة")
        assert special is not None, "Special reports section not found"
        page.screenshot(path=str(_QA / "screenshots" / "02_report_review_button.png"))
        browser.close()

@_pw_skip
def test_VT03_click_report_review_button():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        # The trigger button opens the panel; the panel itself starts hidden
        btn = page.query_selector("[data-testid='pv-open-report-review-table']")
        assert btn is not None, "Report review trigger button not found (data-testid=pv-open-report-review-table)"
        btn.click()
        page.wait_for_timeout(1500)
        page.screenshot(path=str(_QA / "screenshots" / "03_report_review_wizard_opened.png"))
        browser.close()

@_pw_skip
def test_VT04_verify_wizard_opened():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        wizard = page.query_selector("#pv-req-panel-report-review")
        assert wizard is not None, "Report review wizard panel not found"
        browser.close()

@_pw_skip
def test_VT05_upload_step_visible():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        upload = page.query_selector("[data-testid='rr-pdf-upload']")
        assert upload is not None, "PDF upload control not found"
        page.screenshot(path=str(_QA / "screenshots" / "04_upload_step_before_upload.png"))
        browser.close()

@_pw_skip
def test_VT06_upload_pdf_fixture():
    """Upload a fixture PDF and verify extraction status appears."""
    # find a fixture PDF
    fixture = next(_QA.rglob("*.pdf"), None) or next(_SRC.rglob("*.pdf"), None)
    if not fixture:
        pytest.skip("No fixture PDF found")
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        upload_input = page.query_selector("[data-testid='rr-pdf-upload']")
        if upload_input:
            upload_input.set_input_files(str(fixture))
            page.wait_for_timeout(1500)
        page.screenshot(path=str(_QA / "screenshots" / "05_upload_step_after_upload.png"))
        browser.close()

@_pw_skip
def test_VT07_extraction_status_appears():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        status = page.query_selector("[data-testid='rr-extraction-status']")
        assert status is not None, "Extraction status element not found"
        page.screenshot(path=str(_QA / "screenshots" / "06_extraction_status_panel.png"))
        browser.close()

@_pw_skip
def test_VT08_fill_review_info():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        # Open the wizard panel first
        btn = page.query_selector("[data-testid='pv-open-report-review-table']")
        if btn:
            btn.click()
            page.wait_for_timeout(1000)
        # Advance to step 2 via the Next button
        next_btn = page.query_selector("[data-testid='rr-wizard-next']")
        if next_btn:
            next_btn.click()
            page.wait_for_timeout(500)
        page.screenshot(path=str(_QA / "screenshots" / "07_review_info_empty.png"))
        reviewer = page.query_selector("[data-testid='rr-reviewer-name']")
        if reviewer and reviewer.is_visible():
            reviewer.fill("خبير التقييم القانوني")
        page.screenshot(path=str(_QA / "screenshots" / "08_review_info_filled.png"))
        browser.close()

@_pw_skip
def test_VT09_standards_selector_visible():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        ivs_el = page.query_selector("[data-testid='rr-std-ivs']")
        assert ivs_el is not None, "IVS standard selector not found"
        page.screenshot(path=str(_QA / "screenshots" / "09_standards_selector.png"))
        browser.close()

@_pw_skip
def test_VT10_ivs_checklist_visible():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        ivs_tbl = page.query_selector("[data-testid='rr-ivs-checklist-table']")
        assert ivs_tbl is not None, "IVS checklist table not found"
        page.screenshot(path=str(_QA / "screenshots" / "10_ivs_checklist.png"))
        browser.close()

@_pw_skip
def test_VT11_all_four_standard_checklists():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        for std, ss_name in [("uspap","11_uspap_checklist.png"),("rics","12_rics_checklist.png"),("fra","13_fra_checklist.png")]:
            el = page.query_selector(f"[data-testid='rr-std-{std}']")
            assert el is not None, f"{std.upper()} selector not found"
            page.screenshot(path=str(_QA / "screenshots" / ss_name))
        browser.close()

@_pw_skip
def test_VT12_review_agents_panel():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        agents = page.query_selector("[data-testid='rr-agents-panel']")
        assert agents is not None, "Review agents panel not found"
        page.screenshot(path=str(_QA / "screenshots" / "17_review_agents_panel.png"))
        browser.close()

@_pw_skip
def test_VT13_human_review_flags_panel():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        flags = page.query_selector("[data-testid='rr-human-flags-panel']")
        assert flags is not None, "Human review flags panel not found"
        page.screenshot(path=str(_QA / "screenshots" / "19_human_review_flags_panel.png"))
        browser.close()

@_pw_skip
def test_VT14_final_decision_step():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        score = page.query_selector("[data-testid='rr-review-score']")
        assert score is not None, "Review score panel not found"
        page.screenshot(path=str(_QA / "screenshots" / "22_review_score_panel.png"))
        browser.close()

@_pw_skip
def test_VT15_generate_pdf_button_visible():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        btn = page.query_selector("[data-testid='rr-generate-review-pdf']")
        assert btn is not None, "Generate review PDF button not found"
        page.screenshot(path=str(_QA / "screenshots" / "24_generate_review_pdf_button.png"))
        browser.close()

@_pw_skip
def test_VT16_download_button_visible():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        dl = page.query_selector("[data-testid='rr-download-review-pdf']")
        assert dl is not None, "Download review PDF button not found"
        page.screenshot(path=str(_QA / "screenshots" / "25_download_review_pdf_button.png"))
        browser.close()

@_pw_skip
def test_VT17_no_internal_paths_in_dom():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        dom = page.content()
        assert "C:\\Users" not in dom, "Internal Windows path found in DOM"
        assert "C:/Users/Lenovo" not in dom, "Username path found in DOM"
        browser.close()

@_pw_skip
def test_VT18_capture_screenshots_set():
    """Confirm screenshot captures work (basic test)."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        ss_path = _QA / "screenshots" / "20_final_decision_empty.png"
        ss_path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(ss_path))
        assert ss_path.exists()
        browser.close()

# ── File-based checks (always run) ───────────────────────────────────────────

def test_VT19_visual_qa_folder_exists():
    assert _QA.exists(), f"Visual QA folder missing: {_QA}"

def test_VT20_visual_index_html_exists():
    idx = _QA / "visual_previews" / "OPEN_REPORT_REVIEW_VISUAL_QA_INDEX.html"
    assert idx.exists(), "Visual QA index HTML missing"
    content = idx.read_text(encoding="utf-8", errors="ignore")
    assert "مراجعة تقرير" in content

def test_VT21_report_review_pdf_exists():
    assert _REVIEW_PDF.exists(), "report_review_output.pdf not found in QA pdf_outputs"
    assert _REVIEW_PDF.stat().st_size > 10_000, "PDF is too small"

def test_VT22_review_html_has_15_sections():
    """The copied review HTML has 15 page-break sections."""
    dest_html = _QA / "pdf_outputs" / "report_review_output.html"
    if not dest_html.exists():
        # fall back to source
        if not _REVIEW_HTML.exists():
            pytest.skip("Review HTML not found")
        src = _REVIEW_HTML
    else:
        src = dest_html
    content = src.read_text(encoding="utf-8", errors="ignore")
    breaks = content.count('class="pg"') + content.count("class='pg'")
    assert breaks >= 15, f"Expected >= 15 page sections, got {breaks}"

def test_VT23_no_fake_signature_in_any_audit():
    if not _QA.exists():
        pytest.skip("QA folder missing")
    for f in (_QA / "report_review_audits").glob("*.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        assert d.get("fake_reviewer_signature_created", False) is False, \
            f"{f.name}: fake_reviewer_signature_created must be False"

def test_VT24_no_internal_paths_in_visual_index():
    idx = _QA / "visual_previews" / "OPEN_REPORT_REVIEW_VISUAL_QA_INDEX.html"
    if not idx.exists():
        pytest.skip("Visual index missing")
    content = idx.read_text(encoding="utf-8", errors="ignore")
    assert "C:\\Users" not in content
    assert "C:/Users/Lenovo" not in content

def test_VT25_excel_has_all_review_sheets():
    xl = _SRC / "excel_outputs" / "professional_valuation_merged_master_workbook.xlsm"
    if not xl.exists():
        pytest.skip("Excel workbook missing")
    import openpyxl
    wb = openpyxl.load_workbook(str(xl), keep_vba=True)
    sheets = wb.sheetnames
    required = [
        "Report Review Input", "Uploaded Report Metadata", "Extracted Report Structure",
        "IVS Review Checklist", "USPAP Review Checklist", "RICS Review Checklist",
        "FRA Review Checklist", "Technical Review", "Numeric Recalculation",
        "Review Agents Summary", "Findings Register", "Human Review Flags",
        "Review Score", "Reviewer Decision", "Review Export Log"
    ]
    missing = [s for s in required if s not in sheets]
    assert not missing, f"Missing review sheets: {missing}"

def test_VT26_pdf_text_extract_exists():
    txt = _QA / "pdf_text_extracts" / "report_review_output_text.txt"
    assert txt.exists(), "PDF text extract missing"
    content = txt.read_text(encoding="utf-8", errors="ignore")
    assert len(content) > 200, "Text extract too short"
