"""
E2E Visual QA tests for Standards Compliance Report Workflow.
Browser tests skip automatically if Playwright is not installed.
File-based tests (FT) always run.

Run: python -m pytest tests/e2e/test_pv_standards_compliance_visual_qa_e2e.py -q
"""
from __future__ import annotations
import json
import pathlib
import pytest

_ROOT = pathlib.Path(__file__).parent.parent.parent
_QA   = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_standards_compliance_visual_qa"
_AUD  = _QA / "standards_compliance_audits"
_PDF  = _QA / "pdf_outputs"
_XL   = _QA / "excel_outputs"
_SS   = _QA / "screenshots"
_PREV = _QA / "visual_previews"
_TXT  = _QA / "pdf_text_extracts"
_RPT  = _QA / "final_report"

try:
    from playwright.sync_api import sync_playwright, Page  # type: ignore
    _PW_AVAILABLE = True
except ImportError:
    _PW_AVAILABLE = False

_skip_browser = pytest.mark.skipif(not _PW_AVAILABLE, reason="Playwright not installed")
_BASE = "http://localhost:5000"

_EXPECTED_SCREENSHOTS = [
    "01_special_reports_section.png",
    "02_standards_compliance_button_visible.png",
    "03_standards_compliance_workflow_opened.png",
    "04_compliance_wizard_step_1_upload_standards.png",
    "05_compliance_wizard_step_2_extraction.png",
    "06_compliance_wizard_step_3_scoring.png",
    "07_compliance_wizard_step_4_generation.png",
    "08_upload_before_pdf.png",
    "09_upload_after_pdf.png",
    "10_standards_selector_all_selected.png",
    "11_official_use_enabled.png",
    "12_pdf_metadata_panel.png",
    "13_text_extraction_status.png",
    "14_ocr_table_extraction_status.png",
    "15_detected_sections_panel.png",
    "16_signature_hbu_uncertainty_detection.png",
    "17_detected_methods_and_identity_fields.png",
    "18_compliance_score_card.png",
    "19_traffic_light_result.png",
    "20_score_caps_and_critical_rules.png",
    "21_official_use_readiness_score.png",
    "22_ivs_compliance_table.png",
    "23_ivs_103_rows.png",
    "24_ivs_105_uncertainty_hbu_rows.png",
    "25_uspap_compliance_table.png",
    "26_uspap_sr_2_2_rows.png",
    "27_uspap_sr_1_4_rows.png",
    "28_uspap_sr_2_3_certification.png",
    "29_rics_compliance_table.png",
    "30_rics_vps_6_parts.png",
    "31_rics_17_mandatory_items_count.png",
    "32_fra_compliance_table.png",
    "33_fra_signature_official_use_rows.png",
    "34_critical_non_compliance_panel.png",
    "35_recommendations_panel.png",
    "36_official_use_readiness_panel.png",
    "37_signature_gate_panel.png",
    "38_generate_compliance_pdf_button.png",
    "39_download_compliance_pdf_button.png",
    "40_download_compliance_excel_button.png",
    "41_compliance_pdf_generated.png",
    "42_main_standards_compliance_visual_qa_index.png",
]


def _open_compliance_panel(page: "Page") -> None:
    page.goto(_BASE, timeout=15_000)
    page.wait_for_load_state("domcontentloaded")
    page.click("[data-testid='pv-open-standards-table']", timeout=8_000)
    page.evaluate(
        "() => { "
        "var p = document.getElementById('pv-req-panel-standards'); "
        "if (p) { p.style.display=''; } "
        "var s1 = document.getElementById('sc-wizard-step-1'); "
        "if (s1) { s1.style.display=''; } "
        "}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# BROWSER TESTS (BT01-BT22) — skip if Playwright not installed
# ══════════════════════════════════════════════════════════════════════════════

@_skip_browser
def test_BT01_open_professional_valuation_page():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        assert "Expert" in p.title() or p.url.startswith(_BASE)
        b.close()


@_skip_browser
def test_BT02_special_reports_section_visible():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        content = p.content()
        assert "التقارير الخاصة" in content or "pv-open-standards-table" in content
        b.close()


@_skip_browser
def test_BT03_standards_compliance_button_visible():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        el = p.query_selector("[data-testid='pv-open-standards-table']")
        assert el is not None, "Standards compliance button not found"
        b.close()


@_skip_browser
def test_BT04_compliance_workflow_opens():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        panel = p.query_selector("#pv-req-panel-standards")
        assert panel is not None
        b.close()


@_skip_browser
def test_BT05_compliance_panel_has_testid():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        el = p.query_selector("[data-testid='pv-special-req-panel-standards_compliance_report']")
        assert el is not None
        b.close()


@_skip_browser
def test_BT06_four_wizard_steps_exist():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        for i in range(1, 5):
            s = p.query_selector(f"#sc-wizard-step-{i}")
            assert s is not None, f"sc-wizard-step-{i} not found"
        b.close()


@_skip_browser
def test_BT07_pdf_upload_card_visible():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        el = p.query_selector("[data-testid='sc-pdf-upload-card']")
        assert el is not None, "PDF upload card not found"
        b.close()


@_skip_browser
def test_BT08_standards_selector_all_four():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        for tid in ["sc-std-ivs", "sc-std-uspap", "sc-std-rics", "sc-std-fra"]:
            el = p.query_selector(f"[data-testid='{tid}']")
            assert el is not None, f"{tid} not found"
        b.close()


@_skip_browser
def test_BT09_extraction_status_in_step2():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        p.evaluate("() => pvScGoToStep(2)")
        el = p.query_selector("[data-testid='sc-extraction-status']")
        assert el is not None, "Extraction status panel not found"
        b.close()


@_skip_browser
def test_BT10_compliance_score_card_in_step3():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        p.evaluate("() => pvScGoToStep(3)")
        el = p.query_selector("[data-testid='sc-compliance-score-card']")
        assert el is not None, "Compliance score card not found"
        b.close()


@_skip_browser
def test_BT11_ivs_compliance_table_in_step3():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        p.evaluate("() => pvScGoToStep(3)")
        el = p.query_selector("[data-testid='sc-ivs-compliance-table']")
        assert el is not None, "IVS compliance table not found"
        b.close()


@_skip_browser
def test_BT12_uspap_compliance_table_in_step3():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        p.evaluate("() => pvScGoToStep(3)")
        el = p.query_selector("[data-testid='sc-uspap-compliance-table']")
        assert el is not None, "USPAP compliance table not found"
        b.close()


@_skip_browser
def test_BT13_rics_compliance_table_in_step3():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        p.evaluate("() => pvScGoToStep(3)")
        el = p.query_selector("[data-testid='sc-rics-compliance-table']")
        assert el is not None, "RICS compliance table not found"
        b.close()


@_skip_browser
def test_BT14_fra_compliance_table_in_step3():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        p.evaluate("() => pvScGoToStep(3)")
        el = p.query_selector("[data-testid='sc-fra-compliance-table']")
        assert el is not None, "FRA compliance table not found"
        b.close()


@_skip_browser
def test_BT15_critical_non_compliance_panel_in_step3():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        p.evaluate("() => pvScGoToStep(3)")
        el = p.query_selector("[data-testid='sc-critical-non-compliance-panel']")
        assert el is not None, "Critical non-compliance panel not found"
        b.close()


@_skip_browser
def test_BT16_recommendations_panel_in_step3():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        p.evaluate("() => pvScGoToStep(3)")
        el = p.query_selector("[data-testid='sc-recommendations-panel']")
        assert el is not None, "Recommendations panel not found"
        b.close()


@_skip_browser
def test_BT17_official_use_readiness_panel_in_step3():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        p.evaluate("() => pvScGoToStep(3)")
        el = p.query_selector("[data-testid='sc-official-use-readiness-panel']")
        assert el is not None, "Official-use readiness panel not found"
        b.close()


@_skip_browser
def test_BT18_generate_and_download_buttons_in_step4():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        p.evaluate("() => pvScGoToStep(4)")
        gen_btn = p.query_selector("[data-testid='sc-generate-report']")
        pdf_btn = p.query_selector("[data-testid='sc-download-pdf']")
        xl_btn  = p.query_selector("[data-testid='sc-download-excel']")
        assert gen_btn is not None, "Generate report button not found"
        assert pdf_btn is not None, "Download PDF button not found"
        assert xl_btn is not None,  "Download Excel button not found"
        b.close()


@_skip_browser
def test_BT19_no_fake_signature_in_dom():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        body = p.inner_html("body")
        assert "fake_signature=True" not in body
        assert "mock_certification" not in body
        b.close()


@_skip_browser
def test_BT20_no_internal_paths_in_dom():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        body = p.inner_html("body")
        assert "C:\\Users\\Lenovo" not in body
        assert "C:/Users/Lenovo" not in body
        b.close()


@_skip_browser
def test_BT21_workflow_separate_from_report_review():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        panel = p.query_selector("#pv-req-panel-standards")
        assert panel is not None
        report_review = p.query_selector("#pv-req-panel-report_review")
        assert report_review is None or not report_review.is_visible(), (
            "Report Review panel should not be open simultaneously"
        )
        b.close()


@_skip_browser
def test_BT22_arabic_rtl_compliance_panel():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        content = p.content()
        assert "dir=\"rtl\"" in content or "direction:rtl" in content
        b.close()


# ══════════════════════════════════════════════════════════════════════════════
# FILE-BASED TESTS (FT01-FT20) — always run
# ══════════════════════════════════════════════════════════════════════════════

def test_FT01_visual_qa_root_exists():
    assert _QA.is_dir(), "Visual QA root folder missing"


def test_FT02_all_nine_subfolders_exist():
    for sub in ["screenshots", "visual_previews", "uploaded_pdf_snapshots",
                "pdf_text_extracts", "pdf_outputs", "excel_outputs",
                "standards_compliance_audits", "test_logs", "final_report"]:
        assert (_QA / sub).is_dir(), "Missing subfolder: " + sub


def test_FT03_all_42_screenshots_exist():
    for name in _EXPECTED_SCREENSHOTS:
        assert (_SS / name).exists(), "Screenshot missing: " + name


def test_FT04_all_14_audit_files_exist():
    expected = [
        "01_browser_entry_visual_audit.json",
        "02_wizard_visual_audit.json",
        "03_upload_standards_visual_audit.json",
        "04_extraction_visual_audit.json",
        "05_score_card_visual_audit.json",
        "06_ivs_visual_audit.json",
        "07_uspap_visual_audit.json",
        "08_rics_visual_audit.json",
        "09_fra_visual_audit.json",
        "10_blockers_recommendations_visual_audit.json",
        "11_output_generation_visual_audit.json",
        "12_pdf_visual_audit.json",
        "13_excel_visual_audit.json",
        "14_visual_index_audit.json",
    ]
    for f in expected:
        assert (_AUD / f).exists(), "Audit file missing: " + f


def test_FT05_all_audits_have_safety_flags():
    required = {
        "advisory_only": True,
        "fake_signature_created": False,
        "fake_certification_created": False,
        "not_inside_chat_box": True,
        "in_chat_box": False,
    }
    for fname in _AUD.glob("*.json"):
        d = json.loads(fname.read_text(encoding="utf-8"))
        for k, v in required.items():
            assert d.get(k) == v, fname.name + ": " + k + " must be " + str(v)


def test_FT06_pdf_exists_and_non_empty():
    pdf  = _PDF / "standards_compliance_report.pdf"
    html = _PDF / "standards_compliance_report.html"
    assert pdf.exists() or html.exists(), "No PDF or HTML report in visual_qa/pdf_outputs/"
    if pdf.exists():
        assert pdf.stat().st_size > 500
    if html.exists():
        assert html.stat().st_size > 1000


def test_FT07_pdf_html_has_required_content():
    html = _PDF / "standards_compliance_report.html"
    if not html.exists():
        pytest.skip("HTML report not in visual_qa folder")
    content = html.read_text(encoding="utf-8", errors="ignore")
    assert "IVS" in content
    assert "USPAP" in content
    assert "RICS" in content
    assert "FRA" in content
    assert "advisory_only" in content


def test_FT08_excel_exists_and_non_empty():
    xl = _XL / "standards_compliance_workbook.xlsx"
    assert xl.exists(), "Excel workbook missing"
    assert xl.stat().st_size > 2_000


def test_FT09_excel_has_expected_sheets():
    xl = _XL / "standards_compliance_workbook.xlsx"
    if not xl.exists():
        pytest.skip("Excel workbook not found")
    try:
        import openpyxl
        wb = openpyxl.load_workbook(xl, read_only=True)
        sheets = wb.sheetnames
        wb.close()
    except ImportError:
        pytest.skip("openpyxl not installed")
    for expected in ["IVS Compliance", "USPAP Compliance", "RICS Compliance", "FRA Compliance"]:
        assert expected in sheets, "Missing Excel sheet: " + expected


def test_FT10_visual_qa_index_exists_and_valid():
    idx = _PREV / "OPEN_STANDARDS_COMPLIANCE_VISUAL_QA_INDEX.html"
    assert idx.exists(), "Visual QA index HTML missing"
    content = idx.read_text(encoding="utf-8", errors="ignore")
    assert "advisory_only" in content
    assert "OPEN_STANDARDS_COMPLIANCE_VISUAL_QA_INDEX" in content or "Visual QA" in content


def test_FT11_excel_preview_exists():
    ep = _PREV / "OPEN_STANDARDS_COMPLIANCE_EXCEL_PREVIEW.html"
    assert ep.exists(), "Excel preview HTML missing"
    content = ep.read_text(encoding="utf-8", errors="ignore")
    assert "advisory_only" in content or "IVS Compliance" in content


def test_FT12_pdf_page_previews_exist():
    pages_dir = _PREV / "standards_compliance_pdf_pages"
    assert pages_dir.is_dir(), "PDF page previews folder missing"
    pages = list(pages_dir.glob("*.html"))
    assert len(pages) >= 7, "Expected at least 7 PDF page previews, found " + str(len(pages))


def test_FT13_text_extract_exists_and_valid():
    txt = _TXT / "standards_compliance_report_text.txt"
    assert txt.exists(), "Text extract missing"
    content = txt.read_text(encoding="utf-8", errors="ignore")
    assert "advisory_only=True" in content
    assert "fake_signature_created=False" in content


def test_FT14_final_report_exists_and_has_status():
    rpt = _RPT / "final_standards_compliance_visual_qa_report.txt"
    assert rpt.exists(), "Final report missing"
    content = rpt.read_text(encoding="utf-8", errors="ignore")
    assert "advisory_only: True" in content
    assert "fake_signature_created: False" in content
    assert any(s in content for s in ["visual_qa_status: PASS", "visual_qa_status: PARTIAL", "visual_qa_status: FAILED"])


def test_FT15_no_internal_paths_in_any_output():
    for html_file in list(_PREV.glob("*.html")) + list(_PDF.glob("*.html")):
        content = html_file.read_text(encoding="utf-8", errors="ignore")
        assert r"C:\Users" not in content, "Internal path in " + html_file.name
        assert "C:/Users/Lenovo" not in content, "Internal path in " + html_file.name
    for json_file in _AUD.glob("*.json"):
        content = json_file.read_text(encoding="utf-8", errors="ignore")
        assert r"C:\Users" not in content, "Internal path in " + json_file.name


def test_FT16_other_workflows_unaffected():
    sim_dir = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_uploaded_template_simulation"
    hbu_dir = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_hbu_analysis"
    sc_dir  = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_standards_compliance"
    assert sim_dir.is_dir(), "Simulation dir was removed"
    assert hbu_dir.is_dir(), "HBU dir was removed"
    assert sc_dir.is_dir(),  "Main standards compliance dir was removed"


def test_FT17_ivs_table_audit_pass():
    d = json.loads((_AUD / "06_ivs_visual_audit.json").read_text(encoding="utf-8"))
    assert d.get("ivs_table_visible") is True
    assert d.get("ivs_103_1_present") is True
    assert d.get("ivs_uncertainty_row_present") is True


def test_FT18_all_audits_have_advisory_only():
    for fname in _AUD.glob("*.json"):
        d = json.loads(fname.read_text(encoding="utf-8"))
        assert d.get("advisory_only") is True, fname.name + ": advisory_only must be True"


def test_FT19_visual_qa_folder_separate_from_main():
    main = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_standards_compliance"
    qa   = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_standards_compliance_visual_qa"
    assert main != qa, "Visual QA folder must be separate from main workflow folder"
    assert main.is_dir(), "Main standards compliance folder must still exist"
    assert qa.is_dir(), "Visual QA folder must exist"


def test_FT20_final_report_has_all_required_fields():
    rpt = _RPT / "final_standards_compliance_visual_qa_report.txt"
    if not rpt.exists():
        pytest.skip("Final report not created")
    content = rpt.read_text(encoding="utf-8", errors="ignore")
    for field in [
        "visual_qa_status", "advisory_only", "fake_signature_created",
        "ivs_score", "uspap_score", "rics_score", "fra_score",
        "wizard_steps_count", "not_inside_chat_box",
        "standards_compliance_pdf_exists", "standards_compliance_excel_exists",
    ]:
        assert field in content, "Final report missing field: " + field
