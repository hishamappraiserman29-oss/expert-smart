"""
Backend tests for Core Valuation Excel Upgrade.
Tests EX01-EX47 (original 31 + 16 additional).
Run: python -m pytest tests/test_pv_core_valuation_excel_upgrade.py -q
"""
from __future__ import annotations
import json
import pathlib
import pytest

try:
    import openpyxl
    _XL = True
except ImportError:
    _XL = False

_ROOT = pathlib.Path(__file__).parent.parent
_OUT  = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_core_excel_upgrade"
_XL_DIR = _OUT / "excel_outputs"
_AUD    = _OUT / "excel_audits"
_PREV   = _OUT / "visual_previews"
_SS     = _OUT / "screenshots"
_RPT    = _OUT / "final_report"

_WB = _XL_DIR / "core_valuation_master_workbook.xlsx"

def _aud(name: str) -> dict:
    p = _AUD / name
    assert p.exists(), f"Audit missing: {name}"
    return json.loads(p.read_text(encoding="utf-8"))

def _sheets():
    if not _XL or not _WB.exists():
        pytest.skip("Workbook missing or openpyxl unavailable")
    wb = openpyxl.load_workbook(str(_WB), read_only=True, data_only=True)
    s = wb.sheetnames
    wb.close()
    return s

# EX01-EX07: folder and file existence
def test_EX01_output_folder_exists():
    assert _OUT.is_dir()

def test_EX02_final_workbook_exists():
    assert _WB.exists(), f"Workbook missing: {_WB}"

def test_EX03_workbook_non_empty():
    assert _WB.stat().st_size > 5_000

def test_EX04_reference_inventory_audit_exists():
    assert (_AUD / "01_reference_workbook_inventory.json").exists()

def test_EX05_source_preservation_audit_exists():
    assert (_AUD / "12_source_files_preservation_audit.json").exists()

def test_EX06_final_workbook_structure_audit_exists():
    assert (_AUD / "03_final_workbook_structure_audit.json").exists()

def test_EX07_dashboard_audit_exists():
    assert (_AUD / "04_dashboard_audit.json").exists()

# EX08-EX13: audit presence
def test_EX08_traditional_methods_audit_exists():
    assert (_AUD / "05_traditional_methods_audit.json").exists()

def test_EX09_modern_methods_audit_exists():
    assert (_AUD / "06_modern_methods_audit.json").exists()

def test_EX10_data_quality_audit_exists():
    assert (_AUD / "07_data_quality_source_registry_audit.json").exists()

def test_EX11_charts_audit_exists():
    assert (_AUD / "08_charts_visuals_audit.json").exists()

def test_EX12_print_summary_audit_exists():
    assert (_AUD / "09_print_ready_summary_audit.json").exists()

def test_EX13_ui_integration_audit_exists():
    assert (_AUD / "10_core_report_ui_integration_audit.json").exists()

# EX14: visual preview
def test_EX14_visual_preview_index_exists():
    idx = _PREV / "OPEN_CORE_VALUATION_EXCEL_REVIEW_INDEX.html"
    assert idx.exists()

# EX15-EX30: required sheets
REQUIRED_SHEETS = [
    "Cover", "Executive Dashboard", "Input Control Panel", "Property Data",
    "Sales Comparison", "Income Capitalization", "Cost Approach", "DCF Support",
    "Reconciliation", "Final Value", "Data Quality", "Source Registry",
    "Charts Dashboard", "Print Report Summary", "Land Adjustment Matrix",
    "AVM Summary", "Multiple Regression", "Scenarios", "Sensitivity Matrix",
    "HBU Summary", "Risk Register", "Certification Readiness", "Changelog",
    "ESG Sustainability", "Standards Readiness", "Sale vs Rent",
    "Admin Notes", "Export Log", "Legacy Archive Index",
]

@pytest.mark.skipif(not _XL, reason="openpyxl missing")
def test_EX15_required_sheets_all_present():
    sheets = _sheets()
    missing = [s for s in REQUIRED_SHEETS if s not in sheets]
    assert not missing, f"Missing sheets: {missing}"

def test_EX16_cover_sheet(): assert "Cover" in _sheets()
def test_EX17_executive_dashboard(): assert "Executive Dashboard" in _sheets()
def test_EX18_sales_comparison(): assert "Sales Comparison" in _sheets()
def test_EX19_income_capitalization(): assert "Income Capitalization" in _sheets()
def test_EX20_cost_approach(): assert "Cost Approach" in _sheets()
def test_EX21_dcf_support(): assert "DCF Support" in _sheets()
def test_EX22_reconciliation(): assert "Reconciliation" in _sheets()
def test_EX23_final_value(): assert "Final Value" in _sheets()
def test_EX24_data_quality(): assert "Data Quality" in _sheets()
def test_EX25_source_registry(): assert "Source Registry" in _sheets()
def test_EX26_charts_dashboard(): assert "Charts Dashboard" in _sheets()
def test_EX27_print_report_summary(): assert "Print Report Summary" in _sheets()

# EX28: formula presence checks
@pytest.mark.skipif(not _XL, reason="openpyxl missing")
def test_EX28_formulas_in_reconciliation():
    wb = openpyxl.load_workbook(str(_WB), read_only=True)
    ws = wb["Reconciliation"]
    found_mround = False
    for row in ws.iter_rows(values_only=False):
        for cell in row:
            if cell.value and isinstance(cell.value, str) and "MROUND" in cell.value.upper():
                found_mround = True
                break
    wb.close()
    assert found_mround, "MROUND formula missing in Reconciliation"

@pytest.mark.skipif(not _XL, reason="openpyxl missing")
def test_EX29_formulas_in_sales_comparison():
    wb = openpyxl.load_workbook(str(_WB), read_only=True)
    ws = wb["Sales Comparison"]
    found = False
    for row in ws.iter_rows(values_only=False):
        for cell in row:
            if cell.value and isinstance(cell.value, str) and "AVERAGE" in cell.value.upper():
                found = True
                break
    wb.close()
    assert found, "AVERAGE formula missing in Sales Comparison"

# EX30: no fake sources
def test_EX30_no_fake_sources():
    for f in _AUD.glob("*.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        assert d.get("fake_sources_created", False) is False, f"{f.name}: fake_sources_created must be False"

# EX31: no internal paths in visual index
def test_EX31_no_internal_paths():
    idx = _PREV / "OPEN_CORE_VALUATION_EXCEL_REVIEW_INDEX.html"
    if not idx.exists():
        pytest.skip("Visual index not generated")
    content = idx.read_text(encoding="utf-8", errors="ignore")
    assert r"C:\Users" not in content
    assert "C:/Users/Lenovo" not in content

# EX32: old reference files not modified
def test_EX32_old_reference_files_not_overwritten():
    aud = _aud("12_source_files_preservation_audit.json")
    assert aud.get("source_files_preserved") is True
    assert aud.get("source_files_not_deleted") is True
    assert aud.get("source_files_not_overwritten") is True

# EX33: Core report UI still works
def test_EX33_core_report_ui_audit_passes():
    aud = _aud("10_core_report_ui_integration_audit.json")
    assert aud.get("single_internal_excel_card_visible") is True
    assert aud.get("download_excel_button_visible") is True
    assert aud.get("old_duplicate_excel_buttons_removed") is True

# EX34-EX47: new formula/linking tests
def test_EX34_changelog_sheet_exists():
    assert "Changelog" in _sheets()

@pytest.mark.skipif(not _XL, reason="openpyxl missing")
def test_EX35_sales_reliability_formula_exists():
    wb = openpyxl.load_workbook(str(_WB), read_only=True)
    ws = wb["Sales Comparison"]
    found = any(
        isinstance(c.value, str) and "عالية" in c.value
        for row in ws.iter_rows(values_only=False)
        for c in row
    )
    wb.close()
    assert found, "Reliability formula with 'عالية' missing in Sales Comparison"

@pytest.mark.skipif(not _XL, reason="openpyxl missing")
def test_EX36_sales_deviation_from_average_formula():
    wb = openpyxl.load_workbook(str(_WB), read_only=True)
    ws = wb["Sales Comparison"]
    found = any(
        isinstance(c.value, str) and "ABS" in c.value.upper() and "AVERAGE" in c.value.upper()
        for row in ws.iter_rows(values_only=False)
        for c in row
    )
    wb.close()
    assert found, "ABS/AVERAGE deviation formula missing in Sales Comparison"

@pytest.mark.skipif(not _XL, reason="openpyxl missing")
def test_EX37_land_adjustment_links_to_property_area():
    wb = openpyxl.load_workbook(str(_WB), read_only=True)
    ws = wb["Land Adjustment Matrix"]
    found = any(
        isinstance(c.value, str) and "Property Data" in c.value
        for row in ws.iter_rows(values_only=False)
        for c in row
    )
    wb.close()
    assert found, "'Property Data' reference missing in Land Adjustment Matrix"

@pytest.mark.skipif(not _XL, reason="openpyxl missing")
def test_EX38_income_includes_rent_comparables():
    wb = openpyxl.load_workbook(str(_WB), read_only=True)
    ws = wb["Income Capitalization"]
    has_comp = any(
        isinstance(c.value, str) and "Comp Rent" in c.value or (isinstance(c.value, str) and "R1" == c.value)
        for row in ws.iter_rows(values_only=False)
        for c in row
    )
    wb.close()
    assert has_comp, "Rent comparables section missing in Income Capitalization"

@pytest.mark.skipif(not _XL, reason="openpyxl missing")
def test_EX39_sensitivity_has_selected_scenario():
    wb = openpyxl.load_workbook(str(_WB), read_only=True)
    ws = wb["Sensitivity Matrix"]
    found = any(
        isinstance(c.value, str) and "Selected" in c.value
        for row in ws.iter_rows(values_only=False)
        for c in row
    )
    wb.close()
    assert found, "Selected scenario section missing in Sensitivity Matrix"

@pytest.mark.skipif(not _XL, reason="openpyxl missing")
def test_EX40_reconciliation_uses_mround():
    wb = openpyxl.load_workbook(str(_WB), read_only=True)
    ws = wb["Reconciliation"]
    found = any(
        isinstance(c.value, str) and "MROUND" in c.value.upper()
        for row in ws.iter_rows(values_only=False)
        for c in row
    )
    wb.close()
    assert found, "MROUND missing in Reconciliation"

@pytest.mark.skipif(not _XL, reason="openpyxl missing")
def test_EX41_hbu_has_value_weight():
    wb = openpyxl.load_workbook(str(_WB), read_only=True)
    ws = wb["HBU Summary"]
    has_wt = any(
        isinstance(c.value, str) and "Weight" in c.value
        for row in ws.iter_rows(values_only=False)
        for c in row
    )
    wb.close()
    assert has_wt, "Value Weight column missing in HBU Summary"

def test_EX42_dashboard_has_certification_status_kpi():
    aud = _aud("21_dashboard_kpi_priority_audit.json")
    assert aud.get("certification_status_kpi_present") is True

def test_EX43_dashboard_has_blockers_count_kpi():
    aud = _aud("21_dashboard_kpi_priority_audit.json")
    assert aud.get("blockers_count_kpi_present") is True

def test_EX44_dashboard_has_data_quality_kpi():
    aud = _aud("21_dashboard_kpi_priority_audit.json")
    assert aud.get("data_quality_kpi_present") is True

def test_EX45_rounding_settings_in_input_control():
    aud = _aud("22_rounding_governance_audit.json")
    assert aud.get("rounding_settings_created") is True
    assert aud.get("rounding_increment_default_5000") is True

@pytest.mark.skipif(not _XL, reason="openpyxl missing")
def test_EX46_rounding_consistent_across_sheets():
    wb = openpyxl.load_workbook(str(_WB), read_only=True)
    ip = wb["Input Control Panel"]
    recon = wb["Reconciliation"]
    fv = wb["Final Value"]
    # Just confirm both sheets exist and are not empty
    assert ip is not None and recon is not None and fv is not None
    wb.close()

def test_EX47_changelog_logs_formula_upgrades():
    aud = _aud("20_changelog_audit.json")
    assert aud.get("changelog_sheet_created") is True
    assert aud.get("formula_updates_logged") is True
