"""
Backend visual QA tests for Uploaded Template Simulation workflow.
20 tests covering all QA audit files and physical outputs.
Run: python -m pytest tests/test_pv_uploaded_template_simulation_visual_qa.py -q
"""
from __future__ import annotations
import json
import pathlib
import pytest

_ROOT = pathlib.Path(__file__).parent.parent
_QA   = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_uploaded_template_simulation_visual_qa"
_AUD  = _QA / "uploaded_report_simulation_audits"
_PDF  = _QA / "pdf_outputs"
_XL   = _QA / "excel_outputs"
_SS   = _QA / "screenshots"
_PREV = _QA / "visual_previews"
_PROF = _QA / "template_profiles"
_TXT  = _QA / "pdf_text_extracts"
_RPT  = _QA / "final_report"


def _aud(name: str) -> dict:
    p = _AUD / name
    assert p.exists(), f"QA audit missing: {name}"
    return json.loads(p.read_text(encoding="utf-8"))


# ── VQ01: visual QA folder exists ────────────────────────────────────────────
def test_VQ01_visual_qa_folder_exists():
    assert _QA.exists(), f"Visual QA folder missing: {_QA}"
    assert _QA.is_dir()


# ── VQ02: screenshots folder exists and has at least 20 files ────────────────
def test_VQ02_screenshots_folder_exists():
    assert _SS.exists(), "Screenshots folder missing"
    pngs = list(_SS.glob("*.png"))
    assert len(pngs) >= 20, f"Expected >= 20 screenshots, found {len(pngs)}"


# ── VQ03: visual QA index exists ─────────────────────────────────────────────
def test_VQ03_visual_qa_index_exists():
    idx = _PREV / "OPEN_UPLOADED_TEMPLATE_SIMULATION_VISUAL_QA_INDEX.html"
    assert idx.exists(), "Visual QA index missing"
    content = idx.read_text(encoding="utf-8", errors="ignore")
    assert "محاكاة" in content, "Visual QA index must mention محاكاة"
    assert "advisory_only" in content
    assert "visual_qa_status" in content


# ── VQ04: browser entry audit exists ─────────────────────────────────────────
def test_VQ04_browser_entry_audit_exists():
    audit = _aud("01_browser_entry_visual_audit.json")
    assert audit.get("professional_valuation_page_opened") is True
    assert audit.get("special_reports_section_visible") is True
    assert audit.get("uploaded_template_simulation_button_visible") is True
    assert audit.get("wizard_opened") is True
    assert audit.get("wizard_steps_count") == 4
    assert audit.get("not_report_review") is True
    assert audit.get("not_inside_chat_box") is True
    assert audit.get("browser_entry_status") in ("PASS", "PARTIAL")


# ── VQ05: template upload parsing audit exists ────────────────────────────────
def test_VQ05_template_upload_parsing_audit_exists():
    audit = _aud("02_template_upload_parsing_visual_audit.json")
    assert audit.get("template_pdf_upload_control_visible") is True
    assert audit.get("template_pdf_uploaded") is True
    assert audit.get("uploaded_file_name_visible") is True
    assert audit.get("uploaded_file_size_visible") is True
    assert audit.get("page_count_visible_or_blocker_documented") is True
    assert audit.get("template_parsing_status_visible") is True
    assert audit.get("text_extraction_status_visible") is True
    assert audit.get("internal_paths_hidden") is True


# ── VQ06: placeholder mapping audit exists ────────────────────────────────────
def test_VQ06_placeholder_mapping_audit_exists():
    audit = _aud("03_template_preview_placeholder_visual_audit.json")
    assert audit.get("template_preview_visible") is True
    assert audit.get("placeholder_mapping_table_visible") is True
    assert audit.get("manual_mapping_enabled") is True
    cols = audit.get("placeholder_table_columns", [])
    assert len(cols) >= 6, f"Expected >= 6 columns, got {len(cols)}"
    assert audit.get("final_market_value_mapping_present_or_manually_added") is True
    assert audit.get("template_profile_created") is True


# ── VQ07: new property input audit exists ────────────────────────────────────
def test_VQ07_new_property_input_audit_exists():
    audit = _aud("04_new_property_input_visual_audit.json")
    assert audit.get("basic_property_fields_visible") is True
    assert audit.get("sales_comparison_inputs_visible") is True
    assert audit.get("at_least_4_comparables_entered") is True
    assert audit.get("income_inputs_visible") is True
    assert audit.get("cost_inputs_visible") is True
    assert audit.get("reconciliation_inputs_visible") is True
    assert audit.get("arabic_input_supported") is True
    assert audit.get("weights_sum_validation_visible") is True
    assert audit.get("weights_sum_valid") is True
    assert audit.get("new_property_input_status") == "PASS"


# ── VQ08: valuation engine audit exists ──────────────────────────────────────
def test_VQ08_valuation_engine_audit_exists():
    audit = _aud("05_valuation_engine_visual_audit.json")
    assert audit.get("sales_comparison_calculated") is True
    assert audit.get("income_approach_calculated") is True
    assert audit.get("cost_approach_calculated") is True
    assert audit.get("reconciliation_calculated") is True
    assert audit.get("final_market_value_calculated") is True
    assert audit.get("calculation_trace_visible") is True
    assert audit.get("final_value_from_new_inputs") is True
    assert audit.get("old_template_values_not_used") is True
    assert audit.get("valuation_engine_visual_status") == "PASS"


# ── VQ09: generated report audit exists ───────────────────────────────────────
def test_VQ09_generated_report_audit_exists():
    audit = _aud("06_generated_report_visual_audit.json")
    assert audit.get("generate_report_button_visible") is True
    assert audit.get("download_button_visible") is True
    assert audit.get("new_property_data_used") is True
    assert audit.get("final_value_from_engine_used") is True
    assert audit.get("old_values_leaked") is False
    assert audit.get("fake_signature_created") is False
    assert audit.get("professional_advisory_note_present") is True
    assert audit.get("no_internal_paths") is True


# ── VQ10: generated PDF content audit exists ──────────────────────────────────
def test_VQ10_generated_pdf_content_audit_exists():
    audit = _aud("07_generated_pdf_content_audit.json")
    assert audit.get("generated_pdf_opens_successfully") is True
    assert audit.get("new_client_name_present") is True
    assert audit.get("new_property_location_present") is True
    assert audit.get("new_area_present") is True
    assert audit.get("professional_advisory_note_present") is True
    assert audit.get("signature_gate_clean") is True
    assert audit.get("old_template_values_absent") is True
    assert audit.get("fake_signature_absent") is True
    assert audit.get("fake_stamp_absent") is True
    assert audit.get("internal_paths_found") is False


# ── VQ11: Excel visual audit exists ───────────────────────────────────────────
def test_VQ11_excel_visual_audit_exists():
    audit = _aud("08_excel_visual_audit.json")
    assert audit.get("excel_workbook_exists") is True
    assert audit.get("sales_comparison_sheet_present") is True
    assert audit.get("income_approach_sheet_present") is True
    assert audit.get("reconciliation_sheet_present") is True
    assert audit.get("final_value_sheet_present") is True
    assert audit.get("final_value_traceability_present") is True
    assert audit.get("old_values_not_used_as_new_values") is True
    assert audit.get("excel_preview_created") is True


# ── VQ12: generated simulated PDF exists ──────────────────────────────────────
def test_VQ12_generated_simulated_pdf_exists():
    pdf  = _PDF / "simulated_uploaded_template_report.pdf"
    html = _PDF / "simulated_uploaded_template_report.html"
    assert pdf.exists() or html.exists(), (
        "Neither simulated PDF nor HTML found in QA pdf_outputs"
    )


# ── VQ13: generated simulated PDF is non-empty ────────────────────────────────
def test_VQ13_generated_simulated_pdf_non_empty():
    pdf  = _PDF / "simulated_uploaded_template_report.pdf"
    html = _PDF / "simulated_uploaded_template_report.html"
    if pdf.exists():
        assert pdf.stat().st_size > 1_000, f"PDF too small: {pdf.stat().st_size}"
    if html.exists():
        assert html.stat().st_size > 5_000, f"HTML too small: {html.stat().st_size}"


# ── VQ14: generated PDF text extract exists ───────────────────────────────────
def test_VQ14_generated_pdf_text_extract_exists():
    txt = _TXT / "simulated_uploaded_template_report_text.txt"
    assert txt.exists(), "PDF text extract missing"
    content = txt.read_text(encoding="utf-8", errors="ignore")
    assert len(content) > 100, "PDF text extract is too short"
    assert "advisory_only" in content


# ── VQ15: template_profile.json exists ───────────────────────────────────────
def test_VQ15_template_profile_exists():
    profile = _PROF / "template_profile.json"
    assert profile.exists(), "template_profile.json missing"
    p = json.loads(profile.read_text(encoding="utf-8"))
    assert "variable_fields" in p
    assert isinstance(p["variable_fields"], list)
    assert len(p["variable_fields"]) >= 10
    assert "template_profile_status" in p
    assert p.get("advisory_only") is True
    assert p.get("internal_paths_exposed") is False


# ── VQ16: Excel workbook exists ───────────────────────────────────────────────
def test_VQ16_excel_workbook_exists():
    xl = _XL / "simulated_uploaded_template_report_workbook.xlsx"
    assert xl.exists(), "Excel workbook missing from QA excel_outputs"
    assert xl.stat().st_size > 2_000, "Excel workbook is too small"


# ── VQ17: no fake signature in any QA audit ───────────────────────────────────
def test_VQ17_no_fake_signature():
    for fname in _AUD.glob("*.json"):
        d = json.loads(fname.read_text(encoding="utf-8"))
        assert d.get("fake_signature_created", False) is False, (
            f"{fname.name}: fake_signature_created must be False"
        )
    html = _PDF / "simulated_uploaded_template_report.html"
    if html.exists():
        content = html.read_text(encoding="utf-8", errors="ignore")
        assert "fake_signature\n" not in content
        assert "mock_signature" not in content


# ── VQ18: no fake certification in any QA audit ───────────────────────────────
def test_VQ18_no_fake_certification():
    for fname in _AUD.glob("*.json"):
        d = json.loads(fname.read_text(encoding="utf-8"))
        assert d.get("certification_ready", False) is False, (
            f"{fname.name}: certification_ready must be False"
        )
        assert d.get("fake_expert_approval_created", False) is False, (
            f"{fname.name}: fake_expert_approval_created must be False"
        )


# ── VQ19: no internal paths in visual QA index ────────────────────────────────
def test_VQ19_no_internal_paths_in_visual_index():
    idx = _PREV / "OPEN_UPLOADED_TEMPLATE_SIMULATION_VISUAL_QA_INDEX.html"
    if not idx.exists():
        pytest.skip("Visual QA index not found")
    content = idx.read_text(encoding="utf-8", errors="ignore")
    assert r"C:\Users" not in content, "Internal Windows path in QA visual index"
    assert "C:/Users/Lenovo" not in content
    for fname in _AUD.glob("*.json"):
        text = fname.read_text(encoding="utf-8", errors="ignore")
        assert r"C:\Users" not in text, f"Internal path in {fname.name}"
        assert "C:/Users/Lenovo" not in text


# ── VQ20: final visual status not PASS if PDF missing ────────────────────────
def test_VQ20_final_status_consistent_with_pdf():
    pdf  = _PDF / "simulated_uploaded_template_report.pdf"
    html = _PDF / "simulated_uploaded_template_report.html"
    pdf_exists = pdf.exists() or html.exists()
    rpt = _RPT / "final_uploaded_template_simulation_visual_qa_report.txt"
    if rpt.exists():
        text = rpt.read_text(encoding="utf-8", errors="ignore")
        if not pdf_exists:
            assert "PASS" not in text or "PARTIAL" in text or "FAILED" in text, (
                "Final report claims PASS but no PDF/HTML found"
            )
    # If PDF exists, audit 06 must not say FAILED
    if pdf_exists:
        audit = _aud("06_generated_report_visual_audit.json")
        assert audit.get("generated_report_status") in ("PASS", "PARTIAL"), (
            "PDF exists but generated_report_status says FAILED"
        )
