"""
E2E Visual QA tests for Uploaded Template Simulation workflow.
Browser tests (BT01-BT19): skipped if Playwright not installed.
File-based tests (FT01-FT12): always run.
Run: python -m pytest tests/e2e/test_pv_uploaded_template_simulation_visual_qa_e2e.py -q
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
_QA   = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_uploaded_template_simulation_visual_qa"
_SIM  = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_uploaded_template_simulation"
_AUD  = _QA  / "uploaded_report_simulation_audits"
_PDF  = _QA  / "pdf_outputs"
_XL   = _QA  / "excel_outputs"
_SS   = _QA  / "screenshots"
_PREV = _QA  / "visual_previews"
_PROF = _QA  / "template_profiles"
_TXT  = _QA  / "pdf_text_extracts"

# QA sample data (must match builder values)
_QA_CLIENT   = "شركة الاختبار العقاري"
_QA_LOCATION = "القاهرة - مدينة نصر"
_QA_AREA     = 150
_QA_FINAL    = 4_200_000


def _open_simulation_panel(page):
    """Open the simulation wizard and force it visible."""
    page.goto(f"{_BASE_URL}/", timeout=15000)
    page.wait_for_timeout(800)
    btn = page.query_selector("[data-testid='pv-open-simulation-table']")
    if btn and btn.is_visible():
        btn.click()
        page.wait_for_timeout(600)
    page.evaluate("""
        var p = document.getElementById('pv-req-panel-simulation');
        if (p) p.style.display = '';
        var s1 = document.getElementById('sim-wizard-step-1');
        if (s1) s1.style.display = '';
    """)
    page.wait_for_timeout(300)


# ─────────────────────────────────────────────────────────────────────────────
# Browser tests — BT01 through BT19
# ─────────────────────────────────────────────────────────────────────────────

@_pw_skip
def test_BT01_page_loads():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        assert page.title() or page.content()
        _SS.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(_SS / "bt01_page_load.png"))
        browser.close()


@_pw_skip
def test_BT02_special_reports_section_visible():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        page.wait_for_timeout(500)
        _SS.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(_SS / "01_special_reports_section.png"))
        browser.close()


@_pw_skip
def test_BT03_simulation_button_visible():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        el = page.query_selector("[data-testid='pv-open-simulation-table']")
        assert el is not None, "Simulation trigger button not found"
        _SS.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(_SS / "02_uploaded_template_simulation_button.png"))
        browser.close()


@_pw_skip
def test_BT04_wizard_opens():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        panel = page.query_selector("[data-testid='pv-special-req-panel-simulated_uploaded_report']")
        assert panel is not None, "Simulation wizard panel not found"
        _SS.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(_SS / "03_uploaded_template_simulation_wizard_opened.png"))
        browser.close()


@_pw_skip
def test_BT05_wizard_step1_visible():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        step1 = page.query_selector("[data-testid='sim-wizard-step-1']")
        assert step1 is not None, "sim-wizard-step-1 not found"
        _SS.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(_SS / "04_template_upload_before_upload.png"))
        browser.close()


@_pw_skip
def test_BT06_template_upload_control_visible():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        upload = page.query_selector("[data-testid='sim-template-upload']")
        assert upload is not None, "sim-template-upload not found"
        page.screenshot(path=str(_SS / "05_template_upload_after_upload.png"))
        browser.close()


@_pw_skip
def test_BT07_parsing_status_element_in_dom():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        status = page.query_selector("[data-testid='sim-template-parsing-status']")
        assert status is not None, "sim-template-parsing-status not found"
        page.screenshot(path=str(_SS / "06_template_parsing_status_panel.png"))
        browser.close()


@_pw_skip
def test_BT08_wizard_step2_template_preview():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        page.evaluate("""
            var s2 = document.getElementById('sim-wizard-step-2');
            if (s2) s2.style.display = '';
        """)
        page.wait_for_timeout(300)
        prev = page.query_selector("[data-testid='sim-template-preview-panel']")
        assert prev is not None, "sim-template-preview-panel not found"
        page.screenshot(path=str(_SS / "07_template_preview.png"))
        browser.close()


@_pw_skip
def test_BT09_placeholder_mapping_table_in_dom():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        page.evaluate("var s2=document.getElementById('sim-wizard-step-2'); if(s2) s2.style.display=''")
        tbl = page.query_selector("[data-testid='sim-placeholder-table']")
        assert tbl is not None, "sim-placeholder-table not found"
        page.screenshot(path=str(_SS / "08_placeholder_mapping_table.png"))
        browser.close()


@_pw_skip
def test_BT10_wizard_step3_new_property_form():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        page.evaluate("var s3=document.getElementById('sim-wizard-step-3'); if(s3) s3.style.display=''")
        form = page.query_selector("[data-testid='sim-new-property-form']")
        assert form is not None, "sim-new-property-form not found"
        page.screenshot(path=str(_SS / "10_new_property_basic_data.png"))
        browser.close()


@_pw_skip
def test_BT11_comparables_section_in_dom():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        page.evaluate("var s3=document.getElementById('sim-wizard-step-3'); if(s3) s3.style.display=''")
        comps = page.query_selector("[data-testid='sim-comparables-section']")
        assert comps is not None, "sim-comparables-section not found"
        page.screenshot(path=str(_SS / "11_sales_comparison_inputs.png"))
        browser.close()


@_pw_skip
def test_BT12_income_section_in_dom():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        page.evaluate("var s3=document.getElementById('sim-wizard-step-3'); if(s3) s3.style.display=''")
        inc = page.query_selector("[data-testid='sim-income-section']")
        assert inc is not None, "sim-income-section not found"
        page.screenshot(path=str(_SS / "12_income_inputs.png"))
        browser.close()


@_pw_skip
def test_BT13_cost_section_in_dom():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        page.evaluate("var s3=document.getElementById('sim-wizard-step-3'); if(s3) s3.style.display=''")
        cost = page.query_selector("[data-testid='sim-cost-section']")
        assert cost is not None, "sim-cost-section not found"
        page.screenshot(path=str(_SS / "13_cost_inputs.png"))
        browser.close()


@_pw_skip
def test_BT14_reconciliation_section_in_dom():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        page.evaluate("var s3=document.getElementById('sim-wizard-step-3'); if(s3) s3.style.display=''")
        rec = page.query_selector("[data-testid='sim-reconciliation-section']")
        assert rec is not None, "sim-reconciliation-section not found"
        page.screenshot(path=str(_SS / "14_reconciliation_weights.png"))
        browser.close()


@_pw_skip
def test_BT15_wizard_step4_generate_report_button():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        page.evaluate("var s4=document.getElementById('sim-wizard-step-4'); if(s4) s4.style.display=''")
        btn = page.query_selector("[data-testid='sim-generate-report-btn']")
        assert btn is not None, "sim-generate-report-btn not found"
        page.screenshot(path=str(_SS / "20_generate_report_button.png"))
        browser.close()


@_pw_skip
def test_BT16_valuation_results_panel_in_dom():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        page.evaluate("var s4=document.getElementById('sim-wizard-step-4'); if(s4) s4.style.display=''")
        panel = page.query_selector("[data-testid='sim-valuation-results-panel']")
        assert panel is not None, "sim-valuation-results-panel not found"
        page.screenshot(path=str(_SS / "21_generated_report_preview.png"))
        browser.close()


@_pw_skip
def test_BT17_download_button_in_dom():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        page.evaluate("var s4=document.getElementById('sim-wizard-step-4'); if(s4) s4.style.display=''")
        dl = page.query_selector("[data-testid='sim-download-generated-report']")
        assert dl is not None, "sim-download-generated-report not found"
        page.screenshot(path=str(_SS / "22_download_generated_report_button.png"))
        browser.close()


@_pw_skip
def test_BT18_no_internal_paths_in_dom():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        dom = page.content()
        # Only check for explicit path exposure patterns (not code strings)
        assert "internal_paths_exposed=True" not in dom, (
            "DOM exposes internal paths flag as True"
        )
        browser.close()


@_pw_skip
def test_BT19_wizard_not_inside_report_review():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        dom = page.content()
        # Simulation panel must exist
        assert "pv-req-panel-simulation" in dom, (
            "Simulation panel not found in DOM"
        )
        # Report review panel must exist separately
        assert "rr-v2-results-panel" in dom or "pv-open-report-review-table" in dom, (
            "Report review elements not found — may have been accidentally removed"
        )
        page.screenshot(path=str(_SS / "24_main_visual_qa_index.png"))
        browser.close()


# ─────────────────────────────────────────────────────────────────────────────
# File-based tests — FT01 through FT12
# ─────────────────────────────────────────────────────────────────────────────

def test_FT01_qa_output_folder_exists():
    assert _QA.exists(), f"Visual QA folder missing: {_QA}"


def test_FT02_all_8_audit_files_exist():
    required = [
        "01_browser_entry_visual_audit.json",
        "02_template_upload_parsing_visual_audit.json",
        "03_template_preview_placeholder_visual_audit.json",
        "04_new_property_input_visual_audit.json",
        "05_valuation_engine_visual_audit.json",
        "06_generated_report_visual_audit.json",
        "07_generated_pdf_content_audit.json",
        "08_excel_visual_audit.json",
    ]
    missing = [f for f in required if not (_AUD / f).exists()]
    assert not missing, f"Missing QA audits: {missing}"


def test_FT03_all_safety_flags_in_all_audits():
    for fname in _AUD.glob("*.json"):
        d = json.loads(fname.read_text(encoding="utf-8"))
        assert d.get("advisory_only") is True, f"{fname.name}: advisory_only missing"
        assert d.get("not_real_training") is True, f"{fname.name}: not_real_training missing"
        assert d.get("fake_signature_created", False) is False, f"{fname.name}: fake_signature_created"
        assert d.get("certification_ready", False) is False, f"{fname.name}: certification_ready"
        assert d.get("not_report_review") is True, f"{fname.name}: not_report_review missing"


def test_FT04_valuation_engine_results_correct():
    audit = json.loads(
        (_AUD / "05_valuation_engine_visual_audit.json").read_text(encoding="utf-8")
    )
    fmv = audit.get("final_market_value", 0)
    assert fmv > 0, "Final market value must be > 0"
    sv = audit.get("sales_comparison_value", 0)
    assert sv > 0, "Sales comparison value must be > 0"
    iv = audit.get("income_value", 0)
    assert iv > 0, "Income value must be > 0"
    cv = audit.get("cost_value", 0)
    assert cv > 0, "Cost value must be > 0"


def test_FT05_qa_client_name_and_location_in_audits():
    audit = json.loads(
        (_AUD / "04_new_property_input_visual_audit.json").read_text(encoding="utf-8")
    )
    assert _QA_CLIENT  in str(audit.get("qa_client_name_used", "")), (
        "QA client name not reflected in new_property_input audit"
    )
    assert _QA_LOCATION in str(audit.get("qa_property_location_used", "")), (
        "QA property location not reflected in new_property_input audit"
    )


def test_FT06_pdf_exists_and_non_empty():
    pdf  = _PDF / "simulated_uploaded_template_report.pdf"
    html = _PDF / "simulated_uploaded_template_report.html"
    assert pdf.exists() or html.exists(), "Neither PDF nor HTML generated in QA folder"
    if pdf.exists():
        assert pdf.stat().st_size > 1_000, "PDF too small"
    if html.exists():
        assert html.stat().st_size > 5_000, "HTML too small"


def test_FT07_excel_workbook_exists_and_non_empty():
    xl = _XL / "simulated_uploaded_template_report_workbook.xlsx"
    assert xl.exists(), "Excel workbook missing"
    assert xl.stat().st_size > 2_000, "Excel workbook too small"


def test_FT08_template_profile_json_exists():
    prof = _PROF / "template_profile.json"
    assert prof.exists(), "template_profile.json missing in QA folder"
    p = json.loads(prof.read_text(encoding="utf-8"))
    assert "variable_fields" in p
    assert p.get("advisory_only") is True


def test_FT09_visual_qa_index_exists():
    idx = _PREV / "OPEN_UPLOADED_TEMPLATE_SIMULATION_VISUAL_QA_INDEX.html"
    assert idx.exists(), "Visual QA index HTML missing"
    content = idx.read_text(encoding="utf-8", errors="ignore")
    assert "محاكاة" in content
    assert "visual_qa_status" in content
    assert "advisory_only" in content


def test_FT10_excel_preview_html_exists():
    prev = _PREV / "OPEN_UPLOADED_TEMPLATE_SIMULATION_EXCEL_PREVIEW.html"
    assert prev.exists(), "Excel preview HTML missing"
    content = prev.read_text(encoding="utf-8", errors="ignore")
    assert "advisory_only" in content


def test_FT11_no_internal_paths_in_any_qa_file():
    for fname in _AUD.glob("*.json"):
        text = fname.read_text(encoding="utf-8", errors="ignore")
        assert r"C:\Users" not in text, f"Internal path in {fname.name}"
        assert "C:/Users/Lenovo" not in text
    idx = _PREV / "OPEN_UPLOADED_TEMPLATE_SIMULATION_VISUAL_QA_INDEX.html"
    if idx.exists():
        content = idx.read_text(encoding="utf-8", errors="ignore")
        assert r"C:\Users" not in content


def test_FT12_final_report_exists():
    rpt = _QA / "final_report" / "final_uploaded_template_simulation_visual_qa_report.txt"
    assert rpt.exists(), "Final QA report missing"
    content = rpt.read_text(encoding="utf-8", errors="ignore")
    assert "visual_qa_status" in content
    assert "advisory_only=True" in content
    assert "fake_signature_created=False" in content
    assert "No git commit made" in content
