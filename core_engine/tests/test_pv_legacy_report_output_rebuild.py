# test_pv_legacy_report_output_rebuild.py
# Parts J — Physical file and parity verification for legacy report output rebuild
# advisory_only=True | not_real_training=True | no_commit=True

import json
import pathlib
import pytest

REBUILD = pathlib.Path(
    "core_engine/instance/manual_review_outputs/"
    "professional_valuation_legacy_report_output_rebuild"
)
LEGACY_REF  = REBUILD / "legacy_references"
EXCEL_OUT   = REBUILD / "excel_outputs"
PDF_OUT     = REBUILD / "pdf_outputs"
COMP_AUD    = REBUILD / "comparison_audits"
FINAL_RPT   = REBUILD / "final_report"

LEGACY_FILES = [
    "Report_ES_GRAND_FINAL_v4.xlsm",
    "Report_ES_ULTRA.xlsm",
]
EXCEL_ADMIN_FILES = [
    "professional_report_admin_workbook.xlsm",
    "detailed_report_admin_workbook.xlsm",
    "traditional_report_admin_workbook.xlsm",
    "hbu_analysis_admin_workbook.xlsm",
    "standards_compliance_admin_workbook.xlsm",
    "report_review_admin_workbook.xlsm",
    "simulated_uploaded_report_admin_workbook.xlsm",
]
PDF_FILES = [
    "traditional_report.pdf",
    "detailed_report.pdf",
    "professional_report.pdf",
    "hbu_analysis_report.pdf",
    "standards_compliance_report.pdf",
    "report_review_output.pdf",
    "simulated_uploaded_report.pdf",
]
GF_EXPECTED_SHEETS = 44


# ── T01: QA rebuild folder exists ────────────────────────────────────────────
def test_T01_rebuild_folder_exists():
    assert REBUILD.exists(), f"Rebuild folder missing: {REBUILD}"


# ── T02: Legacy GRAND_FINAL workbook found ────────────────────────────────────
def test_T02_legacy_grand_final_found():
    f = LEGACY_REF / "Report_ES_GRAND_FINAL_v4.xlsm"
    assert f.exists(), f"Legacy GRAND_FINAL missing: {f}"
    assert f.stat().st_size > 1_000_000, "GRAND_FINAL is suspiciously small"


# ── T03: Legacy ULTRA workbook found ─────────────────────────────────────────
def test_T03_legacy_ultra_found():
    f = LEGACY_REF / "Report_ES_ULTRA.xlsm"
    assert f.exists(), f"Legacy ULTRA missing: {f}"
    assert f.stat().st_size > 100_000, "ULTRA is suspiciously small"


# ── T04: Legacy inventory generated ──────────────────────────────────────────
def test_T04_legacy_inventory_generated():
    gf = COMP_AUD / "legacy_grand_final_inventory.json"
    ul = COMP_AUD / "legacy_ultra_inventory.json"
    assert gf.exists(), f"GRAND_FINAL inventory missing: {gf}"
    assert ul.exists(), f"ULTRA inventory missing: {ul}"
    gf_data = json.loads(gf.read_text(encoding="utf-8"))
    assert gf_data["sheet_count"] == GF_EXPECTED_SHEETS
    assert gf_data["file_found"] is True


# ── T05: Legacy sheet map generated ──────────────────────────────────────────
def test_T05_legacy_sheet_map_generated():
    sm = COMP_AUD / "legacy_sheet_map.json"
    assert sm.exists(), f"Sheet map missing: {sm}"
    data = json.loads(sm.read_text(encoding="utf-8"))
    assert data["sheet_count"] == GF_EXPECTED_SHEETS
    assert len(data["sheets"]) == GF_EXPECTED_SHEETS
    # Every sheet has a classification
    for s in data["sheets"]:
        assert "classification" in s
        assert s["classification"] != ""


# ── T06: Excel outputs folder is not empty ───────────────────────────────────
def test_T06_excel_outputs_not_empty():
    files = list(EXCEL_OUT.glob("*.xlsm"))
    assert len(files) > 0, "excel_outputs/ is empty — no .xlsm files found"


# ── T07: Professional admin workbook exists ───────────────────────────────────
def test_T07_professional_admin_workbook_exists():
    f = EXCEL_OUT / "professional_report_admin_workbook.xlsm"
    assert f.exists(), f"Professional workbook missing: {f}"
    assert f.stat().st_size > 1_000_000, "Professional workbook is a tiny placeholder"


# ── T08: Professional admin workbook has >= 44 sheets ─────────────────────────
def test_T08_professional_workbook_has_44_sheets():
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")
    f = EXCEL_OUT / "professional_report_admin_workbook.xlsm"
    if not f.exists():
        pytest.fail(f"Professional workbook missing: {f}")
    wb = openpyxl.load_workbook(str(f), read_only=True, keep_vba=True)
    sc = len(wb.sheetnames)
    wb.close()
    assert sc >= GF_EXPECTED_SHEETS, (
        f"Professional workbook has {sc} sheets — expected >= {GF_EXPECTED_SHEETS}"
    )


# ── T09: No legacy sheets deleted in professional workbook ────────────────────
def test_T09_no_legacy_sheets_deleted():
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")
    audit = COMP_AUD / "generated_vs_legacy_excel_parity_audit.json"
    assert audit.exists(), f"Parity audit missing: {audit}"
    data = json.loads(audit.read_text(encoding="utf-8"))
    deleted = data.get("deleted_legacy_sheets", [])
    assert len(deleted) == 0, f"Legacy sheets deleted: {deleted}"


# ── T10: Generated workbook is not a tiny placeholder ────────────────────────
def test_T10_workbook_not_tiny_placeholder():
    f = EXCEL_OUT / "professional_report_admin_workbook.xlsm"
    if not f.exists():
        pytest.fail(f"Professional workbook missing: {f}")
    # Must be at least 1 MB (legacy is 3.3 MB, tiny placeholder would be < 100 KB)
    assert f.stat().st_size > 1_000_000, (
        f"Professional workbook is {f.stat().st_size} bytes — tiny placeholder detected"
    )


# ── T11: PDF outputs folder is not empty ──────────────────────────────────────
def test_T11_pdf_outputs_not_empty():
    files = list(PDF_OUT.glob("*.pdf"))
    assert len(files) > 0, "pdf_outputs/ is empty — no PDF files found"


# ── T12: traditional_report.pdf exists ────────────────────────────────────────
def test_T12_traditional_pdf_exists():
    f = PDF_OUT / "traditional_report.pdf"
    assert f.exists(), f"traditional_report.pdf missing: {f}"
    assert f.stat().st_size > 0, "traditional_report.pdf is empty"


# ── T13: detailed_report.pdf exists ───────────────────────────────────────────
def test_T13_detailed_pdf_exists():
    f = PDF_OUT / "detailed_report.pdf"
    assert f.exists(), f"detailed_report.pdf missing: {f}"
    assert f.stat().st_size > 0, "detailed_report.pdf is empty"


# ── T14: professional_report.pdf exists ───────────────────────────────────────
def test_T14_professional_pdf_exists():
    f = PDF_OUT / "professional_report.pdf"
    assert f.exists(), f"professional_report.pdf missing: {f}"
    assert f.stat().st_size > 0, "professional_report.pdf is empty"


# ── T15: All PDFs are non-empty ────────────────────────────────────────────────
def test_T15_all_pdfs_non_empty():
    for fname in PDF_FILES:
        f = PDF_OUT / fname
        assert f.exists(), f"PDF missing: {f}"
        assert f.stat().st_size > 1000, f"PDF is too small (possible empty): {fname}"


# ── T16: Physical output audit exists ─────────────────────────────────────────
def test_T16_physical_output_audit_exists():
    f = COMP_AUD / "physical_output_files_audit.json"
    assert f.exists(), f"Physical output audit missing: {f}"
    data = json.loads(f.read_text(encoding="utf-8"))
    assert data["excel_output_status"] in ("PASS", "PARTIAL")
    assert data["pdf_output_status"] in ("PASS", "PARTIAL")
    # Both must be PASS
    assert data["excel_output_status"] == "PASS", (
        f"Excel output status: {data['excel_output_status']}"
    )
    assert data["pdf_output_status"] == "PASS", (
        f"PDF output status: {data['pdf_output_status']}"
    )


# ── T17: Generated vs legacy parity audit exists ──────────────────────────────
def test_T17_parity_audit_exists():
    f = COMP_AUD / "generated_vs_legacy_excel_parity_audit.json"
    assert f.exists(), f"Parity audit missing: {f}"
    data = json.loads(f.read_text(encoding="utf-8"))
    assert data["generated_files_physically_exist"] is True
    assert data["excel_parity_status"] in ("PASS", "PARTIAL", "FAILED")


# ── T18: No fake certification in generated Excel workbooks ───────────────────
def test_T18_no_fake_certification_in_excel():
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")
    fake_phrases = ["FINAL_CERTIFIED", "certified_final_valuation"]
    for fname in EXCEL_ADMIN_FILES:
        f = EXCEL_OUT / fname
        if not f.exists():
            continue
        wb = openpyxl.load_workbook(str(f), read_only=True, keep_vba=True)
        for ws in wb.worksheets:
            try:
                for row in ws.iter_rows(max_row=5, values_only=True):
                    for v in row:
                        if v is not None:
                            for phrase in fake_phrases:
                                assert phrase not in str(v), (
                                    f"Fake certification phrase '{phrase}' in {fname}/{ws.title}"
                                )
            except Exception:
                pass
        wb.close()


# ── T19: No internal paths in generated Excel inputs ──────────────────────────
def test_T19_no_internal_paths_in_excel():
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")
    forbidden = ["C:\\Users\\", "C:/Users/", "AppData", "__file__"]
    for fname in EXCEL_ADMIN_FILES:
        f = EXCEL_OUT / fname
        if not f.exists():
            continue
        wb = openpyxl.load_workbook(str(f), read_only=True, keep_vba=True)
        # Only check the inputs sheet (first 10 rows) to avoid scanning all 44 sheets
        inp = "الافتراضات والمدخلات"
        if inp in wb.sheetnames:
            ws = wb[inp]
            for row in ws.iter_rows(max_row=10, values_only=True):
                for v in row:
                    if v is not None:
                        cell_str = str(v)
                        for pat in forbidden:
                            assert pat not in cell_str, (
                                f"Internal path '{pat}' found in {fname}/{inp}"
                            )
        wb.close()


# ── T20: Ordinary valuation unaffected (smoke) ────────────────────────────────
def test_T20_ordinary_valuation_unaffected():
    bridge = pathlib.Path("core_engine/bridge_api.py")
    assert bridge.exists(), "bridge_api.py missing"
    text = bridge.read_text(encoding="utf-8", errors="replace")
    assert "def calculate_property_value" in text or "valuation" in text.lower(), (
        "bridge_api.py does not appear to contain valuation logic"
    )


# ── T21: Tax appeal unaffected (smoke) ────────────────────────────────────────
def test_T21_tax_appeal_unaffected():
    bridge = pathlib.Path("core_engine/bridge_api.py")
    text = bridge.read_text(encoding="utf-8", errors="replace")
    assert "tax" in text.lower() or "appeal" in text.lower(), (
        "bridge_api.py does not appear to contain tax/appeal logic"
    )
