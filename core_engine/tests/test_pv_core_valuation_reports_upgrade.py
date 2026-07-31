"""
Backend tests for Core Reports Excel Visual QA upgrade.
CR01-CR29.
Run: python -m pytest tests/test_pv_core_valuation_reports_upgrade.py -q
"""
from __future__ import annotations
import json, pathlib
import pytest

_ROOT = pathlib.Path(__file__).parent.parent
_OUT  = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_core_reports_excel_visual_qa"
_PDF  = _OUT / "pdf_outputs"
_XL   = _OUT / "excel_outputs"
_AUD  = _OUT / "report_audits"
_PREV = _OUT / "visual_previews"
_SS   = _OUT / "screenshots"
_RPT  = _OUT / "final_report"

_TRAD = _PDF / "traditional_valuation_report_upgraded.pdf"
_DET  = _PDF / "detailed_valuation_report_upgraded.pdf"
_PROF = _PDF / "professional_valuation_report_upgraded.pdf"
_XLWB = _XL  / "core_reports_qa_workbook.xlsx"
_IDX  = _PREV / "OPEN_CORE_REPORTS_EXCEL_VISUAL_QA_INDEX.html"

def _aud(name):
    p = _AUD / name
    assert p.exists(), f"Audit missing: {name}"
    return json.loads(p.read_text(encoding="utf-8"))

# CR01-CR07: Output folder and files
def test_CR01_output_folder_exists(): assert _OUT.is_dir()
def test_CR02_pdf_folder_exists():    assert _PDF.is_dir()
def test_CR03_traditional_pdf_exists(): assert _TRAD.exists(), str(_TRAD)
def test_CR04_detailed_pdf_exists():    assert _DET.exists(),  str(_DET)
def test_CR05_professional_pdf_exists(): assert _PROF.exists(), str(_PROF)
def test_CR06_pdfs_non_empty():
    for p in [_TRAD, _DET, _PROF]:
        assert p.stat().st_size > 100, f"{p.name} too small"
def test_CR07_excel_workbook_exists(): assert _XLWB.exists(), str(_XLWB)

# CR08-CR10: Audit files
def test_CR08_ref_inventory_audit():    assert (_AUD/"01_reference_reports_inventory.json").exists()
def test_CR09_blank_pages_audit():      assert (_AUD/"02_blank_pages_layout_cleanup.json").exists()
def test_CR10_header_footer_audit():    assert (_AUD/"03_header_footer_page_numbering.json").exists()
def test_CR11_cover_diff_audit():       assert (_AUD/"04_cover_differentiation.json").exists()
def test_CR12_report_struct_audit():    assert (_AUD/"05_report_structure.json").exists()
def test_CR13_smart_page_audit():       assert (_AUD/"06_smart_valuation_page_integration.json").exists()
def test_CR14_visual_readability_audit(): assert (_AUD/"07_visual_readability.json").exists()
def test_CR15_uncertainty_audit():      assert (_AUD/"08_uncertainty_range.json").exists()
def test_CR16_land_adj_audit():         assert (_AUD/"09_land_adjustment_visualization.json").exists()
def test_CR17_avm_warning_audit():      assert (_AUD/"10_avm_warning.json").exists()
def test_CR18_sale_rent_audit():        assert (_AUD/"11_sale_vs_rent_upgrade.json").exists()
def test_CR19_standards_audit():        assert (_AUD/"12_standards_compliance_statement.json").exists()
def test_CR20_risk_matrix_audit():      assert (_AUD/"13_risk_matrix_upgrade.json").exists()
def test_CR21_working_draft_audit():    assert (_AUD/"14_working_draft_disclaimer.json").exists()
def test_CR22_type_enhancements_audit(): assert (_AUD/"15_report_type_specific_enhancements.json").exists()
def test_CR23_visual_index_audit():     assert (_AUD/"16_visual_review_index.json").exists()
def test_CR24_ui_integration_audit():   assert (_AUD/"17_ui_integration.json").exists()

# CR25: No fake signature / valuer / license
def test_CR25_no_fake_signature():
    a = _aud("12_standards_compliance_statement.json")
    assert a.get("fake_signature_created") is False
    assert a.get("fake_valuer_name_created") is False
    assert a.get("fake_license_created") is False

# CR26: No internal paths in visual index
def test_CR26_no_internal_paths():
    if not _IDX.exists(): pytest.skip("Index not created")
    c = _IDX.read_text(encoding="utf-8", errors="ignore")
    assert r"C:\Users\Lenovo" not in c
    assert "C:/Users/Lenovo" not in c

# CR27: All audits have safety flags
def test_CR27_all_audits_have_safety_flags():
    for f in _AUD.glob("*.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        assert d.get("advisory_only") is True,       f"{f.name}: advisory_only"
        assert d.get("fake_sources_created") is False, f"{f.name}: fake_sources"

# CR28: Visual review index exists
def test_CR28_visual_index_exists(): assert _IDX.exists()

# CR29: Final report exists with PASS or PARTIAL
def test_CR29_final_report_status():
    rpt = _RPT / "final_core_reports_excel_visual_qa_report.txt"
    assert rpt.exists()
    c = rpt.read_text(encoding="utf-8", errors="ignore")
    assert '"overall_status"' in c
    import json as _j
    d = _j.loads(c)
    assert d.get("overall_status") in ("PASS","PARTIAL"), f"Status: {d.get('overall_status')}"
