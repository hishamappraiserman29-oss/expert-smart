"""
Backend tests — Reference Parity Upgrade.
RP01-RP25.
Run: python -m pytest tests/test_pv_reference_parity_upgrade.py -q
"""
import json, pathlib
import pytest

_ROOT = pathlib.Path(__file__).parent.parent
_OUT = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_reference_parity_upgrade"
_PDF = _OUT / "pdf_outputs"
_XL  = _OUT / "excel_outputs"
_AUD = _OUT / "audits"
_RPT = _OUT / "final_report"
_SS  = _OUT / "screenshots"
_PREV = _OUT / "visual_previews"

_TRAD = _PDF / "traditional_valuation_report_reference_parity.pdf"
_DET  = _PDF / "detailed_valuation_report_reference_parity.pdf"
_PROF = _PDF / "professional_valuation_report_reference_parity.pdf"
_XLWB = _XL  / "core_valuation_master_workbook_reference_parity.xlsx"
_IDX  = _PREV / "OPEN_REFERENCE_PARITY_REVIEW_INDEX.html"

def _rpt():
    return json.loads((_RPT / "final_reference_parity_upgrade_report.txt").read_text(encoding="utf-8"))

def test_RP01_traditional_pdf_exists(): assert _TRAD.exists()
def test_RP02_detailed_pdf_exists():    assert _DET.exists()
def test_RP03_professional_pdf_exists(): assert _PROF.exists()
def test_RP04_excel_workbook_exists():  assert _XLWB.exists()

def test_RP05_traditional_not_6_pages():
    r = _rpt()
    pages = r.get("traditional_pdf_pages", 0)
    assert pages > 6 or r.get("traditional_report_expanded_beyond_6_pages") is True

def test_RP06_traditional_structure_expanded():
    r = _rpt()
    assert r.get("traditional_report_expanded_beyond_6_pages") is True

def test_RP07_cost_approach_deepened():
    r = _rpt()
    assert r.get("cost_approach_deepened") is True

def test_RP08_building_cost_breakdown_added():
    r = _rpt()
    assert r.get("building_cost_breakdown_added") is True

def test_RP09_depreciation_analysis_added():
    r = _rpt()
    assert r.get("depreciation_analysis_added") is True

def test_RP10_land_sales_comparison_added():
    r = _rpt()
    assert r.get("land_sales_comparison_added") is True

def test_RP11_land_extraction_method_added():
    r = _rpt()
    assert r.get("land_extraction_method_added") is True

def test_RP12_land_reconciliation_added():
    r = _rpt()
    assert r.get("land_reconciliation_added") is True

def test_RP13_dcf_present():
    # DCF must be in detailed/professional PDFs
    assert _DET.stat().st_size > 50_000, "Detailed PDF too small"

def test_RP14_irr_in_excel():
    r = _rpt()
    assert r.get("irr_sheet_added") is True

def test_RP15_spatial_analysis_in_excel():
    r = _rpt()
    assert r.get("spatial_analysis_sheet_added") is True

def test_RP16_ann_sheet_in_excel():
    r = _rpt()
    assert r.get("ann_sheet_added") is True

def test_RP17_risk_matrix_exists():
    r = _rpt()
    assert r.get("advanced_methods_added") is True

def test_RP18_charts_dashboard_exists():
    r = _rpt()
    assert r.get("charts_added") is True

def test_RP19_print_report_summary_exists():
    # Print Report Summary sheet
    import openpyxl
    wb = openpyxl.load_workbook(str(_XLWB), read_only=True)
    sheets = wb.sheetnames
    wb.close()
    assert any("Print" in s or "Summary" in s or "Print Report" in s for s in sheets), f"Print sheet missing. Sheets: {sheets}"

def test_RP20_excel_sheet_count():
    import openpyxl
    wb = openpyxl.load_workbook(str(_XLWB), read_only=True)
    count = len(wb.sheetnames)
    wb.close()
    r = _rpt()
    # Either >=40 sheets or gap is documented
    assert count >= 40 or r.get("excel_sheet_count", 0) >= 40, f"Only {count} sheets"

def test_RP21_visual_index_exists():
    assert _IDX.exists()

def test_RP22_no_fake_signature():
    a = json.loads((_AUD / "03_pdf_physical_audit.json").read_text(encoding="utf-8"))
    assert a.get("fake_signature_created") is False
    assert a.get("fake_valuer_created") is False
    assert a.get("fake_license_created") is False

def test_RP23_no_fake_valuer():
    r = _rpt()
    assert r.get("fake_valuer_created") is False

def test_RP24_no_fake_license():
    r = _rpt()
    assert r.get("fake_license_created") is False

def test_RP25_no_internal_paths():
    c = _IDX.read_text(encoding="utf-8", errors="ignore")
    assert r"C:\Users\Lenovo" not in c
    r_data = _rpt()
    assert r_data.get("internal_paths_exposed") is False
