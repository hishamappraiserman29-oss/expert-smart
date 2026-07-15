"""
Backend Visual QA tests for Core Valuation Report Issuance.
VQ01-VQ25.
Run: python -m pytest tests/test_pv_core_reports_excel_visual_qa.py -q
"""
from __future__ import annotations
import json, pathlib
import pytest

_ROOT = pathlib.Path(__file__).parent.parent
_OUT  = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_core_reports_excel_visual_qa"
_PDF  = _OUT / "pdf_outputs"
_XL   = _OUT / "excel_outputs"
_AUD  = _OUT / "qa_audits"
_PREV = _OUT / "visual_previews"
_SS   = _OUT / "screenshots"
_RPT  = _OUT / "final_report"
_TXT  = _OUT / "pdf_text_extracts"
_EXLP = _OUT / "excel_previews"

_TRAD = _PDF / "traditional_valuation_report_upgraded.pdf"
_DET  = _PDF / "detailed_valuation_report_upgraded.pdf"
_PROF = _PDF / "professional_valuation_report_upgraded.pdf"
_XLWB = _XL  / "core_valuation_master_workbook.xlsx"
_IDX  = _PREV / "OPEN_CORE_REPORTS_EXCEL_VISUAL_QA_INDEX.html"

def _aud(name: str) -> dict:
    p = _AUD / name
    assert p.exists(), f"Audit missing: {name}"
    return json.loads(p.read_text(encoding="utf-8"))

# VQ01: output folder
def test_VQ01_output_folder_exists(): assert _OUT.is_dir()

# VQ02-VQ04: PDFs exist
def test_VQ02_traditional_pdf_exists(): assert _TRAD.exists()
def test_VQ03_detailed_pdf_exists():    assert _DET.exists()
def test_VQ04_professional_pdf_exists(): assert _PROF.exists()

# VQ05: PDFs non-empty
def test_VQ05_pdfs_non_empty():
    for p in [_TRAD, _DET, _PROF]:
        assert p.stat().st_size > 100, f"{p.name} empty"

# VQ06: Excel master workbook exists
def test_VQ06_excel_master_workbook_exists(): assert _XLWB.exists()

# VQ07: Excel non-empty
def test_VQ07_excel_workbook_non_empty():
    assert _XLWB.stat().st_size > 1000

# VQ08: Visual index exists
def test_VQ08_visual_index_exists(): assert _IDX.exists()

# VQ09: Browser entry audit
def test_VQ09_browser_entry_audit_exists():
    a = _aud("01_browser_entry_ui_audit.json")
    assert a.get("core_report_section_visible") is True
    assert a.get("internal_paths_exposed") is False

# VQ10: PDF generation audit
def test_VQ10_pdf_generation_audit_exists():
    a = _aud("02_pdf_generation_audit.json")
    assert a.get("traditional_pdf_exists") is True
    assert a.get("fake_signature_created") is False

# VQ11: PDF rendering audit
def test_VQ11_pdf_rendering_audit_exists():
    a = _aud("03_pdf_rendering_text_audit.json")
    assert a.get("traditional_pages_rendered") is True

# VQ12: Traditional visual audit
def test_VQ12_traditional_visual_audit():
    a = _aud("04_traditional_report_visual_audit.json")
    assert a.get("blue_cover_present") is True
    assert a.get("fake_signature_absent") is True
    assert a.get("working_draft_disclaimer_present") is True

# VQ13: Detailed visual audit
def test_VQ13_detailed_visual_audit():
    a = _aud("05_detailed_report_visual_audit.json")
    assert a.get("green_bronze_cover_present") is True
    assert a.get("executive_summary_page_2_present") is True
    assert a.get("fake_signature_absent") is True

# VQ14: Professional visual audit
def test_VQ14_professional_visual_audit():
    a = _aud("06_professional_report_visual_audit.json")
    assert a.get("red_gold_cover_present") is True
    assert a.get("toc_present") is True
    assert a.get("risk_matrix_5x5_early") is True
    assert a.get("fake_signature_absent") is True
    assert a.get("fake_license_absent") is True

# VQ15: Shared engine audit
def test_VQ15_shared_engine_audit():
    a = _aud("07_shared_engine_smart_page_audit.json")
    assert a.get("reports_share_same_engine") is True
    assert a.get("fake_market_evidence_created") is False

# VQ16: Excel generation audit
def test_VQ16_excel_generation_audit():
    a = _aud("08_excel_generation_audit.json")
    assert a.get("core_master_workbook_exists") is True
    assert a.get("old_excels_preserved") is True

# VQ17: Excel structure audit
def test_VQ17_excel_structure_audit():
    a = _aud("09_excel_structure_audit.json")
    assert a.get("cover_present") is True
    assert a.get("executive_dashboard_present") is True
    assert a.get("reconciliation_present") is True
    assert a.get("changelog_present") is True

# VQ18: Excel dashboard audit
def test_VQ18_excel_dashboard_audit():
    a = _aud("10_excel_dashboard_visuals_audit.json")
    assert a.get("kpi_cards_present") is True
    assert a.get("final_value_kpi_present") is True

# VQ19: Excel formula audit
def test_VQ19_excel_formula_audit():
    a = _aud("11_excel_formula_linking_audit.json")
    assert a.get("land_value_linked_to_subject_area") is True
    assert a.get("reconciliation_rounding_automated") is True
    assert a.get("noi_formula_present") is True

# VQ20: Print/Changelog audit
def test_VQ20_excel_print_changelog_audit():
    a = _aud("12_excel_print_changelog_audit.json")
    assert a.get("print_report_summary_present") is True
    assert a.get("changelog_present") is True
    assert a.get("version_tracking_present") is True

# VQ21: No fake signature
def test_VQ21_no_fake_signature():
    a = _aud("02_pdf_generation_audit.json")
    assert a.get("fake_signature_created") is False
    assert a.get("fake_valuer_created") is False
    assert a.get("fake_license_created") is False
    assert a.get("fake_stamp_created") is False

# VQ22: No fake valuer in professional audit
def test_VQ22_no_fake_valuer_professional():
    a = _aud("06_professional_report_visual_audit.json")
    assert a.get("fake_valuer_absent") is True
    assert a.get("fake_signature_absent") is True

# VQ23: No internal paths in visual index
def test_VQ23_no_internal_paths_in_index():
    c = _IDX.read_text(encoding="utf-8", errors="ignore")
    assert r"C:\Users\Lenovo" not in c
    assert "C:/Users/Lenovo" not in c

# VQ24: Final status not PASS if PDF missing
def test_VQ24_final_report_status():
    rpt = _RPT / "final_core_reports_excel_visual_qa_report.txt"
    assert rpt.exists()
    d = json.loads(rpt.read_text(encoding="utf-8"))
    if not (d.get("traditional_pdf_exists") and d.get("detailed_pdf_exists") and d.get("professional_pdf_exists")):
        assert d.get("overall_status") != "PASS"
    else:
        assert d.get("overall_status") in ("PASS", "PARTIAL")

# VQ25: Final status not PASS if Excel missing
def test_VQ25_final_status_not_pass_if_excel_missing():
    rpt = _RPT / "final_core_reports_excel_visual_qa_report.txt"
    d = json.loads(rpt.read_text(encoding="utf-8"))
    if not d.get("excel_workbook_exists"):
        assert d.get("overall_status") != "PASS"
    else:
        assert d.get("overall_status") in ("PASS", "PARTIAL")
