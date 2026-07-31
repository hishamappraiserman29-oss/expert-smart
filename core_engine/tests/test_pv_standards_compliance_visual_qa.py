"""
Backend tests for Standards Compliance Visual QA.
26 tests (VQA01-VQA26).
Run: python -m pytest tests/test_pv_standards_compliance_visual_qa.py -q
"""
from __future__ import annotations
import json
import pathlib
import pytest

_ROOT = pathlib.Path(__file__).parent.parent
_QA   = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_standards_compliance_visual_qa"
_AUD  = _QA / "standards_compliance_audits"
_PDF  = _QA / "pdf_outputs"
_XL   = _QA / "excel_outputs"
_SS   = _QA / "screenshots"
_PREV = _QA / "visual_previews"
_TXT  = _QA / "pdf_text_extracts"
_RPT  = _QA / "final_report"


def _aud(name: str) -> dict:
    p = _AUD / name
    assert p.exists(), "Visual QA audit missing: " + name
    return json.loads(p.read_text(encoding="utf-8"))


# ── VQA01: visual QA root folder exists ──────────────────────────────────────
def test_VQA01_visual_qa_folder_exists():
    assert _QA.is_dir(), "Visual QA root folder missing"


# ── VQA02: screenshots folder exists ──────────────────────────────────────────
def test_VQA02_screenshots_folder_exists():
    assert _SS.is_dir(), "Screenshots folder missing"


# ── VQA03: visual QA index exists ─────────────────────────────────────────────
def test_VQA03_visual_qa_index_exists():
    idx = _PREV / "OPEN_STANDARDS_COMPLIANCE_VISUAL_QA_INDEX.html"
    assert idx.exists(), "Visual QA index HTML missing"
    content = idx.read_text(encoding="utf-8", errors="ignore")
    assert "advisory_only" in content
    assert r"C:\Users" not in content
    assert "C:/Users/Lenovo" not in content


# ── VQA04: browser entry audit exists ────────────────────────────────────────
def test_VQA04_browser_entry_audit_exists():
    audit = _aud("01_browser_entry_visual_audit.json")
    assert audit.get("special_reports_section_visible") is True
    assert audit.get("standards_compliance_button_visible") is True
    assert audit.get("standards_compliance_workflow_opened") is True
    assert audit.get("not_inside_chat_box") is True
    assert audit.get("not_report_review") is True
    assert audit.get("not_hbu_workflow") is True


# ── VQA05: wizard audit exists ───────────────────────────────────────────────
def test_VQA05_wizard_audit_exists():
    audit = _aud("02_wizard_visual_audit.json")
    assert audit.get("wizard_steps_count") == 4
    assert audit.get("step_1_upload_and_standards_visible") is True
    assert audit.get("step_2_extraction_visible") is True
    assert audit.get("step_3_compliance_scoring_visible") is True
    assert audit.get("step_4_generation_visible") is True


# ── VQA06: upload/standards audit exists ─────────────────────────────────────
def test_VQA06_upload_standards_audit_exists():
    audit = _aud("03_upload_standards_visual_audit.json")
    assert audit.get("pdf_upload_card_visible") is True
    assert audit.get("ivs_selected") is True
    assert audit.get("uspap_selected") is True
    assert audit.get("rics_selected") is True
    assert audit.get("fra_selected") is True
    assert audit.get("not_inside_chat_box") is True


# ── VQA07: extraction audit exists ───────────────────────────────────────────
def test_VQA07_extraction_audit_exists():
    audit = _aud("04_extraction_visual_audit.json")
    assert audit.get("text_extraction_status_visible") is True
    assert audit.get("internal_paths_hidden") is True
    status = audit.get("extraction_visual_status", "")
    assert status in ("PASS", "PARTIAL", "FAILED")


# ── VQA08: score card audit exists ───────────────────────────────────────────
def test_VQA08_score_card_audit_exists():
    audit = _aud("05_score_card_visual_audit.json")
    assert audit.get("compliance_score_card_visible") is True
    assert audit.get("ivs_score_visible") is True
    assert audit.get("uspap_score_visible") is True
    assert audit.get("rics_score_visible") is True
    assert audit.get("fra_score_visible") is True
    assert audit.get("traffic_light_visible") is True


# ── VQA09: IVS audit exists ──────────────────────────────────────────────────
def test_VQA09_ivs_audit_exists():
    audit = _aud("06_ivs_visual_audit.json")
    assert audit.get("ivs_table_visible") is True
    assert audit.get("ivs_103_1_present") is True
    assert audit.get("ivs_103_2_present") is True
    assert audit.get("ivs_uncertainty_row_present") is True
    assert audit.get("ivs_visual_status") in ("PASS", "PARTIAL")


# ── VQA10: USPAP audit exists ────────────────────────────────────────────────
def test_VQA10_uspap_audit_exists():
    audit = _aud("07_uspap_visual_audit.json")
    assert audit.get("uspap_table_visible") is True
    assert audit.get("sr_2_1_present") is True
    assert audit.get("sr_2_3_present") is True
    assert audit.get("uspap_visual_status") in ("PASS", "PARTIAL")


# ── VQA11: RICS audit exists ─────────────────────────────────────────────────
def test_VQA11_rics_audit_exists():
    audit = _aud("08_rics_visual_audit.json")
    assert audit.get("rics_table_visible") is True
    assert audit.get("vps_6_clear_not_misleading_present") is True
    assert audit.get("rics_visual_status") in ("PASS", "PARTIAL")


# ── VQA12: FRA audit exists ──────────────────────────────────────────────────
def test_VQA12_fra_audit_exists():
    audit = _aud("09_fra_visual_audit.json")
    assert audit.get("fra_table_visible") is True
    assert audit.get("fra_1_present") is True
    assert audit.get("fra_5_present") is True
    assert audit.get("fra_visual_status") in ("PASS", "PARTIAL")


# ── VQA13: blockers/recommendations audit exists ─────────────────────────────
def test_VQA13_blockers_recommendations_audit_exists():
    audit = _aud("10_blockers_recommendations_visual_audit.json")
    assert audit.get("critical_non_compliance_panel_visible") is True
    assert audit.get("recommendations_panel_visible") is True
    assert audit.get("signature_gate_clean") is True
    assert audit.get("fake_signature_created") is False


# ── VQA14: output generation audit exists ────────────────────────────────────
def test_VQA14_output_generation_audit_exists():
    audit = _aud("11_output_generation_visual_audit.json")
    assert audit.get("generate_pdf_button_visible") is True
    assert audit.get("download_pdf_button_visible") is True
    assert audit.get("download_excel_button_visible") is True
    assert audit.get("fake_signature_created") is False
    assert audit.get("fake_certification_created") is False
    assert audit.get("internal_paths_hidden") is True


# ── VQA15: PDF visual audit exists ───────────────────────────────────────────
def test_VQA15_pdf_visual_audit_exists():
    audit = _aud("12_pdf_visual_audit.json")
    assert audit.get("standards_compliance_pdf_exists") is True
    assert audit.get("advisory_warning_present") is True
    assert audit.get("fake_signature_absent") is True
    assert audit.get("fake_certification_absent") is True
    assert audit.get("internal_paths_found") is False
    status = audit.get("pdf_visual_status", "")
    assert status in ("PASS", "PARTIAL")


# ── VQA16: Excel visual audit exists ─────────────────────────────────────────
def test_VQA16_excel_visual_audit_exists():
    audit = _aud("13_excel_visual_audit.json")
    assert audit.get("standards_compliance_excel_exists") is True
    assert audit.get("excel_visual_status") in ("PASS", "PARTIAL")


# ── VQA17: standards_compliance_report.pdf exists ────────────────────────────
def test_VQA17_compliance_pdf_exists():
    pdf  = _PDF / "standards_compliance_report.pdf"
    html = _PDF / "standards_compliance_report.html"
    assert pdf.exists() or html.exists(), (
        "Neither PDF nor HTML report found in visual_qa/pdf_outputs/"
    )


# ── VQA18: PDF is non-empty ───────────────────────────────────────────────────
def test_VQA18_pdf_is_non_empty():
    pdf  = _PDF / "standards_compliance_report.pdf"
    html = _PDF / "standards_compliance_report.html"
    if pdf.exists():
        assert pdf.stat().st_size > 500, "PDF is suspiciously small"
    elif html.exists():
        assert html.stat().st_size > 1000, "HTML report is suspiciously small"
    else:
        pytest.fail("No PDF or HTML report found")


# ── VQA19: Excel workbook exists ─────────────────────────────────────────────
def test_VQA19_excel_workbook_exists():
    xl = _XL / "standards_compliance_workbook.xlsx"
    assert xl.exists(), "Excel workbook missing from visual_qa/excel_outputs/"
    assert xl.stat().st_size > 2_000, "Excel workbook too small"


# ── VQA20: text extract exists ───────────────────────────────────────────────
def test_VQA20_text_extract_exists():
    txt = _TXT / "standards_compliance_report_text.txt"
    assert txt.exists(), "PDF text extract missing"
    content = txt.read_text(encoding="utf-8", errors="ignore")
    assert "advisory_only=True" in content
    assert "fake_signature_created=False" in content


# ── VQA21: no fake signature ─────────────────────────────────────────────────
def test_VQA21_no_fake_signature():
    for fname in _AUD.glob("*.json"):
        d = json.loads(fname.read_text(encoding="utf-8"))
        assert d.get("fake_signature_created", False) is False, (
            fname.name + ": fake_signature_created must be False"
        )


# ── VQA22: no fake certification ─────────────────────────────────────────────
def test_VQA22_no_fake_certification():
    for fname in _AUD.glob("*.json"):
        d = json.loads(fname.read_text(encoding="utf-8"))
        assert d.get("fake_certification_created", False) is False, (
            fname.name + ": fake_certification_created must be False"
        )


# ── VQA23: no internal paths in visual index ─────────────────────────────────
def test_VQA23_no_internal_paths_in_visual_index():
    idx = _PREV / "OPEN_STANDARDS_COMPLIANCE_VISUAL_QA_INDEX.html"
    if not idx.exists():
        pytest.skip("Visual index not created")
    content = idx.read_text(encoding="utf-8", errors="ignore")
    assert r"C:\Users" not in content, "Internal Windows path found in visual index"
    assert "C:/Users/Lenovo" not in content, "Internal path found in visual index"


# ── VQA24: final report status not PASS if PDF missing ───────────────────────
def test_VQA24_final_status_not_pass_if_pdf_missing():
    pdf_exists = (
        (_PDF / "standards_compliance_report.pdf").exists()
        or (_PDF / "standards_compliance_report.html").exists()
    )
    rpt = _RPT / "final_standards_compliance_visual_qa_report.txt"
    if not rpt.exists():
        pytest.skip("Final report not created")
    content = rpt.read_text(encoding="utf-8", errors="ignore")
    if not pdf_exists:
        assert "visual_qa_status: PASS" not in content, (
            "Final report claims PASS but PDF is missing"
        )


# ── VQA25: final report status not PASS if Excel missing ─────────────────────
def test_VQA25_final_status_not_pass_if_excel_missing():
    xl_exists = (_XL / "standards_compliance_workbook.xlsx").exists()
    rpt = _RPT / "final_standards_compliance_visual_qa_report.txt"
    if not rpt.exists():
        pytest.skip("Final report not created")
    content = rpt.read_text(encoding="utf-8", errors="ignore")
    if not xl_exists:
        assert "visual_qa_status: PASS" not in content, (
            "Final report claims PASS but Excel is missing"
        )


# ── VQA26: final report status not PASS if tables missing ────────────────────
def test_VQA26_final_status_not_pass_if_tables_missing():
    audit_06 = _AUD / "06_ivs_visual_audit.json"
    if not audit_06.exists():
        pytest.skip("IVS audit not created")
    d = json.loads(audit_06.read_text(encoding="utf-8"))
    ivs_ok = d.get("ivs_table_visible", False)
    rpt = _RPT / "final_standards_compliance_visual_qa_report.txt"
    if not rpt.exists():
        pytest.skip("Final report not created")
    content = rpt.read_text(encoding="utf-8", errors="ignore")
    if not ivs_ok:
        assert "visual_qa_status: PASS" not in content, (
            "Final report claims PASS but IVS table is missing"
        )
