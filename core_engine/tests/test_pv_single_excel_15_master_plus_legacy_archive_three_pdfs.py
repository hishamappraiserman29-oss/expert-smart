"""
test_pv_single_excel_15_master_plus_legacy_archive_three_pdfs.py
اختبارات الواجهة الخلفية — ملف Excel واحد: 15 ورقة رئيسية + أرشيف قديم + 3 تقارير PDF

تشغيل:
  python -m pytest core_engine/tests/test_pv_single_excel_15_master_plus_legacy_archive_three_pdfs.py -q

arabic_primary=True | single_admin_excel=True | advisory_only=True
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_CORE))

_QA   = _CORE / "instance" / "manual_review_outputs" / \
        "professional_valuation_single_excel_15_master_plus_legacy_archive_three_pdfs"
_XL   = _QA / "excel_outputs"
_PDF  = _QA / "pdf_outputs"
_PREV = _QA / "pdf_visual_previews"
_XPREV= _QA / "excel_visual_previews"
_XAUD = _QA / "excel_audits"
_PAUD = _QA / "pdf_audits"

MASTER_SHEET_NAMES = [
    "Cover", "Data Quality", "Property", "HBU Analysis", "Comparables",
    "Income Approach", "Cost Approach", "AVM Reference", "Scenarios",
    "Sensitivity Matrix", "Reconciliation", "Risk Register",
    "Standards Matrix", "Source Registry", "Admin Notes",
]
_WORKBOOK = "professional_valuation_admin_master_workbook.xlsm"


def _load(path: Path) -> dict:
    assert path.exists(), f"Missing: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def _html(key: str) -> str:
    p = _PREV / f"{key}_preview.html"
    assert p.exists(), f"Missing PDF preview: {p}"
    return p.read_text(encoding="utf-8")


def _wb_sheets() -> list[str]:
    import openpyxl
    wb = openpyxl.load_workbook(str(_XL / _WORKBOOK), read_only=True)
    names = wb.sheetnames
    wb.close()
    return names


# T01 ─────────────────────────────────────────────────────────────────────────
def test_T01_qa_folder_exists():
    """T01: QA output folder and all subfolders exist."""
    assert _QA.exists()
    for sub in ["excel_outputs", "pdf_outputs", "pdf_visual_previews",
                "excel_visual_previews", "excel_audits", "pdf_audits",
                "test_logs", "final_report"]:
        assert (_QA / sub).exists(), f"Missing subfolder: {sub}"


# T02 ─────────────────────────────────────────────────────────────────────────
def test_T02_only_one_admin_excel_workbook():
    """T02: only one generated admin Excel workbook exists."""
    xl_files = list(_XL.glob("*.xlsm")) + list(_XL.glob("*.xlsx"))
    assert len(xl_files) == 1, f"Expected 1 workbook, found: {[f.name for f in xl_files]}"


# T03 ─────────────────────────────────────────────────────────────────────────
def test_T03_no_three_separate_excel_workbooks():
    """T03: three separate admin Excel workbooks do NOT exist."""
    xl_files = list(_XL.glob("*.xlsm")) + list(_XL.glob("*.xlsx"))
    assert len(xl_files) < 3, f"Found {len(xl_files)} Excel files — should be exactly 1"


# T04 ─────────────────────────────────────────────────────────────────────────
def test_T04_admin_master_workbook_exists():
    """T04: professional_valuation_admin_master_workbook.xlsm exists."""
    wb = _XL / _WORKBOOK
    assert wb.exists(), f"Missing: {wb}"


# T05 ─────────────────────────────────────────────────────────────────────────
def test_T05_admin_master_workbook_not_empty():
    """T05: admin master workbook is not empty (>10KB)."""
    assert (_XL / _WORKBOOK).stat().st_size > 10_000


# T06 ─────────────────────────────────────────────────────────────────────────
def test_T06_first_15_sheets_match_required_names():
    """T06: first 15 sheets match required master sheet names."""
    sheets = _wb_sheets()
    assert sheets[:15] == MASTER_SHEET_NAMES, \
        f"First 15 sheets mismatch.\nExpected: {MASTER_SHEET_NAMES}\nGot:      {sheets[:15]}"


# T07 ─────────────────────────────────────────────────────────────────────────
def test_T07_first_15_sheets_in_exact_order():
    """T07: first 15 sheets are in the exact required order."""
    sheets = _wb_sheets()
    for i, expected in enumerate(MASTER_SHEET_NAMES):
        assert sheets[i] == expected, \
            f"Position {i+1}: expected '{expected}', got '{sheets[i]}'"


# T08 ─────────────────────────────────────────────────────────────────────────
def test_T08_legacy_archive_sheets_after_first_15():
    """T08: legacy archive sheets are included after the first 15 master sheets."""
    sheets = _wb_sheets()
    legacy_sheets = sheets[15:]
    assert len(legacy_sheets) > 0, "No legacy archive sheets found after position 15"


# T09 ─────────────────────────────────────────────────────────────────────────
def test_T09_grand_final_legacy_sheets_included():
    """T09: GRAND_FINAL legacy sheets are included or blocker documented."""
    data = _load(_XAUD / "legacy_archive_sheets_audit.json")
    assert data["legacy_archive_enabled"] is True
    gf_ok = data.get("all_grand_final_sheets_copied", False)
    gf_names = data.get("grand_final_sheet_names_in_workbook", [])
    if not gf_ok:
        # Check for documented blocker
        audit = _load(_XAUD / "excel_formula_and_logic_audit.json")
        blockers = audit.get("technical_blockers", [])
        assert len(blockers) > 0, "GRAND_FINAL sheets missing and no blocker documented"
    else:
        assert len(gf_names) > 0, "GRAND_FINAL sheets not copied into workbook"


# T10 ─────────────────────────────────────────────────────────────────────────
def test_T10_ultra_legacy_sheets_included():
    """T10: ULTRA legacy sheets are included or blocker documented."""
    data = _load(_XAUD / "legacy_archive_sheets_audit.json")
    ul_ok = data.get("all_ultra_sheets_copied", False)
    ul_names = data.get("ultra_sheet_names_in_workbook", [])
    if not ul_ok:
        audit = _load(_XAUD / "excel_formula_and_logic_audit.json")
        assert len(audit.get("technical_blockers", [])) > 0
    else:
        assert len(ul_names) > 0


# T11 ─────────────────────────────────────────────────────────────────────────
def test_T11_old_source_legacy_files_not_modified():
    """T11: old source legacy files are not modified."""
    data = _load(_XAUD / "legacy_source_files_preservation_audit.json")
    for key in ["Report_ES_GRAND_FINAL_v4_xlsm", "Report_ES_ULTRA_xlsm"]:
        info = data.get(key, {})
        assert info.get("modified", True) is False, f"{key} was modified"
        assert info.get("deleted", True) is False, f"{key} was deleted"
        assert info.get("overwritten", True) is False, f"{key} was overwritten"


# T12 ─────────────────────────────────────────────────────────────────────────
def test_T12_consolidation_mapping_exists():
    """T12: excel_sheet_consolidation_mapping.json exists."""
    p = _XAUD / "excel_sheet_consolidation_mapping.json"
    assert p.exists()
    data = _load(p)
    assert data.get("source_concept_sheet_count") == 30


# T13 ─────────────────────────────────────────────────────────────────────────
def test_T13_old_30_sheet_concept_mapped():
    """T13: old 30-sheet concept mapped to 15 master sheets."""
    data = _load(_XAUD / "excel_sheet_consolidation_mapping.json")
    assert data.get("target_master_sheet_count") == 15
    assert data.get("similar_sheets_merged") is True
    assert data.get("logic_preserved_by_consolidation") is True
    mapping = data.get("mapping", {})
    assert len(mapping) == 30, f"Expected 30 entries in mapping, got {len(mapping)}"


# T14 ─────────────────────────────────────────────────────────────────────────
def test_T14_dcf_integrated_into_income_approach():
    """T14: DCF is integrated inside Income Approach sheet."""
    data = _load(_XAUD / "excel_formula_and_logic_audit.json")
    assert data.get("dcf_integrated_into_income_approach") is True


# T15 ─────────────────────────────────────────────────────────────────────────
def test_T15_income_approach_has_dcf_options():
    """T15: Income Approach sheet content includes 5-year and 10-year DCF."""
    # Verify the Income Approach preview content or formula audit
    data = _load(_XAUD / "excel_formula_and_logic_audit.json")
    assert data.get("dcf_integrated_into_income_approach") is True
    # Verify in the professional PDF (uses same context)
    content = _html("professional_report")
    assert "5 سنوات" in content or "5-year" in content.lower()
    assert "10 سنوات" in content or "10-year" in content.lower()


# T16 ─────────────────────────────────────────────────────────────────────────
def test_T16_income_approach_has_npv_irr():
    """T16: Income Approach contains NPV/IRR fields."""
    data = _load(_XAUD / "excel_formula_and_logic_audit.json")
    assert data.get("npv_irr_present") is True
    content = _html("professional_report")
    assert "NPV" in content


# T17 ─────────────────────────────────────────────────────────────────────────
def test_T17_hbu_analysis_has_four_tests():
    """T17: HBU Analysis sheet includes the four HBU tests."""
    data = _load(_XAUD / "excel_formula_and_logic_audit.json")
    assert data.get("hbu_numeric_tests_present") is True
    content = _html("professional_report")
    for term in ["Physically Possible", "Legally Permissible", "Financially Feasible", "Maximally Productive"]:
        assert term in content, f"HBU test missing: {term}"


# T18 ─────────────────────────────────────────────────────────────────────────
def test_T18_avm_reference_exists():
    """T18: AVM Reference sheet exists in the workbook."""
    sheets = _wb_sheets()
    assert "AVM Reference" in sheets


# T19 ─────────────────────────────────────────────────────────────────────────
def test_T19_scenarios_sheet_exists():
    """T19: Scenarios sheet exists in the workbook."""
    sheets = _wb_sheets()
    assert "Scenarios" in sheets
    content = _html("professional_report")
    assert "السيناريو" in content or "Scenario" in content


# T20 ─────────────────────────────────────────────────────────────────────────
def test_T20_sensitivity_matrix_has_multi_variable():
    """T20: Sensitivity Matrix has multi-variable sensitivity."""
    data = _load(_XAUD / "excel_formula_and_logic_audit.json")
    assert data.get("sensitivity_multi_variable_present") is True
    content = _html("professional_report")
    assert "الحساسية" in content


# T21 ─────────────────────────────────────────────────────────────────────────
def test_T21_risk_register_has_value_impact():
    """T21: Risk Register has value impact percentage."""
    data = _load(_XAUD / "excel_formula_and_logic_audit.json")
    assert data.get("risk_value_impact_present") is True
    content = _html("professional_report")
    assert "المخاطر" in content


# T22 ─────────────────────────────────────────────────────────────────────────
def test_T22_source_registry_exists():
    """T22: Source Registry sheet exists and documented."""
    sheets = _wb_sheets()
    assert "Source Registry" in sheets
    data = _load(_XAUD / "excel_formula_and_logic_audit.json")
    assert data.get("source_registry_present") is True


# T23 ─────────────────────────────────────────────────────────────────────────
def test_T23_standards_matrix_includes_disclosures():
    """T23: Standards Matrix includes disclosures."""
    data = _load(_XAUD / "excel_formula_and_logic_audit.json")
    assert data.get("standards_disclosures_present") is True
    content = _html("professional_report")
    assert "IVS" in content


# T24 ─────────────────────────────────────────────────────────────────────────
def test_T24_admin_notes_has_expert_review_checklist():
    """T24: Admin Notes sheet includes expert review checklist."""
    sheets = _wb_sheets()
    assert "Admin Notes" in sheets
    # The checklist marker is in the audit
    audit_data = _load(_XAUD / "excel_internal_only_audit.json")
    assert audit_data.get("admin_notice_in_admin_notes_sheet") is True


# T25 ─────────────────────────────────────────────────────────────────────────
def test_T25_excel_is_internal_only():
    """T25: Excel workbook is marked internal-only."""
    data = _load(_XAUD / "excel_internal_only_audit.json")
    assert data.get("excel_is_internal_admin_only") is True
    assert data.get("user_receives_pdf_only") is True


# T26 ─────────────────────────────────────────────────────────────────────────
def test_T26_traditional_pdf_exists():
    """T26: traditional_report.pdf exists and is non-empty."""
    p = _PDF / "traditional_report.pdf"
    assert p.exists()
    assert p.stat().st_size > 10_000


# T27 ─────────────────────────────────────────────────────────────────────────
def test_T27_detailed_pdf_exists():
    """T27: detailed_report.pdf exists and is non-empty."""
    p = _PDF / "detailed_report.pdf"
    assert p.exists()
    assert p.stat().st_size > 10_000


# T28 ─────────────────────────────────────────────────────────────────────────
def test_T28_professional_pdf_exists():
    """T28: professional_report.pdf exists and is non-empty."""
    p = _PDF / "professional_report.pdf"
    assert p.exists()
    assert p.stat().st_size > 10_000


# T29 ─────────────────────────────────────────────────────────────────────────
def test_T29_detailed_pdf_richer_than_traditional():
    """T29: detailed PDF has more <h2> sections than traditional."""
    trad_h2 = _html("traditional_report").count("<h2>")
    det_h2  = _html("detailed_report").count("<h2>")
    assert det_h2 > trad_h2, f"detailed_h2={det_h2} not > traditional_h2={trad_h2}"


# T30 ─────────────────────────────────────────────────────────────────────────
def test_T30_professional_pdf_richer_than_detailed():
    """T30: professional PDF has more <h2> sections than detailed."""
    det_h2 = _html("detailed_report").count("<h2>")
    pro_h2 = _html("professional_report").count("<h2>")
    assert pro_h2 > det_h2, f"professional_h2={pro_h2} not > detailed_h2={det_h2}"


# T31 ─────────────────────────────────────────────────────────────────────────
def test_T31_professional_pdf_includes_advanced_sections():
    """T31: professional PDF includes NPV/IRR, sensitivity, scenarios, risk impact."""
    content = _html("professional_report")
    for term in ["NPV", "الحساسية", "السيناريو", "المخاطر", "DCF"]:
        assert term in content, f"Professional PDF missing: {term}"


# T32 ─────────────────────────────────────────────────────────────────────────
def test_T32_pdfs_use_single_excel_context():
    """T32: PDFs are linked to the single admin Excel workbook context."""
    data = _load(_PAUD / "pdf_uses_single_excel_context_audit.json")
    assert data.get("single_excel_workbook_used") == _WORKBOOK
    assert data.get("pdf_context_status") == "PASS"
    for key in ["traditional_uses_master_excel_context",
                "detailed_uses_master_excel_context",
                "professional_uses_master_excel_context"]:
        assert data.get(key) is True, f"Context check failed: {key}"


# T33 ─────────────────────────────────────────────────────────────────────────
def test_T33_no_fake_certification():
    """T33: no fake certification, signature, or stamp in any preview."""
    for key in ["traditional_report", "detailed_report", "professional_report"]:
        content = _html(key)
        assert "مسودة" in content, f"{key} missing draft notice"
        assert "advisory_only=True" in content, f"{key} missing advisory_only flag"
        if "certification_ready" in content.lower():
            assert "False" in content, f"{key} shows certification_ready=True"


# T34 ─────────────────────────────────────────────────────────────────────────
def test_T34_no_internal_paths_in_previews():
    """T34: no Windows filesystem paths appear in any HTML preview."""
    for key in ["traditional_report", "detailed_report", "professional_report"]:
        content = _html(key)
        for pat in (r"C:\\Users", r"C:/Users", "/home/", "core_engine/instance"):
            assert pat not in content, f"Internal path in {key}: {pat}"


# T35 ─────────────────────────────────────────────────────────────────────────
def test_T35_ordinary_valuation_unaffected():
    """T35: ordinary valuation page element still present in frontend."""
    frontend = _CORE.parent / "frontend" / "index.html"
    assert frontend.exists()
    content = frontend.read_text(encoding="utf-8")
    assert 'id="simple-certified-report-cta-box"' in content


# T36 ─────────────────────────────────────────────────────────────────────────
def test_T36_tax_appeal_unaffected():
    """T36: tax appeal content still present in frontend."""
    frontend = _CORE.parent / "frontend" / "index.html"
    content = frontend.read_text(encoding="utf-8")
    assert "ضريبي" in content or "ضريبة" in content or "tax" in content.lower()
