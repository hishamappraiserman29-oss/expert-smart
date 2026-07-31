"""
Tests CP01-CP19: Content Parity Upgrade — PDFs, Excel, Audits, Final Report
"""
import json
import pathlib
import pytest

_ROOT = pathlib.Path(__file__).parent.parent
_OUT  = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_content_parity_upgrade"

PDF_DIR    = _OUT / "pdf_outputs"
EXCEL_DIR  = _OUT / "excel_outputs"
AUDIT_DIR  = _OUT / "audits"
PREVIEW_DIR= _OUT / "visual_previews"
FINAL_DIR  = _OUT / "final_report"

TRAD_PDF   = PDF_DIR  / "traditional_valuation_report_content_upgraded.pdf"
DET_PDF    = PDF_DIR  / "detailed_valuation_report_content_upgraded.pdf"
PROF_PDF   = PDF_DIR  / "professional_valuation_report_content_upgraded.pdf"
EXCEL_FILE = EXCEL_DIR / "core_valuation_master_workbook_content_upgraded.xlsx"
VIS_INDEX  = PREVIEW_DIR / "OPEN_CONTENT_PARITY_REVIEW_INDEX.html"
FINAL_RPT  = FINAL_DIR / "final_content_parity_upgrade_report.txt"

AUDIT_FILES = [
    "01_reference_content_deep_analysis.json",
    "02_cost_approach_audit.json",
    "03_land_valuation_audit.json",
    "04_excel_sheets_audit.json",
    "05_traditional_report_audit.json",
    "06_detailed_report_audit.json",
    "07_professional_report_audit.json",
]

# Internal path fragments that must NOT appear in output files
INTERNAL_PATH_MARKERS = [
    "C:\\Users\\", "C:/Users/",
    "/home/", "/root/",
    "expert_smart1",
    "AppData",
]


def _load_final() -> dict:
    return json.loads(FINAL_RPT.read_text(encoding="utf-8"))


def _load_audit(fname: str) -> dict:
    return json.loads((AUDIT_DIR / fname).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# CP01 - CP09: Folder / File existence and basic constraints
# ---------------------------------------------------------------------------

def test_CP01_output_folder_exists():
    """CP01: Output folder exists."""
    assert _OUT.exists(), f"Output folder missing: {_OUT}"


def test_CP02_traditional_pdf_exists():
    """CP02: Traditional PDF exists."""
    assert TRAD_PDF.exists(), f"Missing: {TRAD_PDF.name}"


def test_CP03_detailed_pdf_exists():
    """CP03: Detailed PDF exists."""
    assert DET_PDF.exists(), f"Missing: {DET_PDF.name}"


def test_CP04_professional_pdf_exists():
    """CP04: Professional PDF exists."""
    assert PROF_PDF.exists(), f"Missing: {PROF_PDF.name}"


def test_CP05_pdfs_non_empty():
    """CP05: All 3 PDFs are non-empty (>10,000 bytes)."""
    for pdf in [TRAD_PDF, DET_PDF, PROF_PDF]:
        assert pdf.exists(), f"Missing: {pdf.name}"
        size = pdf.stat().st_size
        assert size > 10_000, f"{pdf.name} is too small: {size} bytes"


def test_CP06_excel_exists():
    """CP06: Excel workbook exists."""
    assert EXCEL_FILE.exists(), f"Missing: {EXCEL_FILE.name}"


def test_CP07_excel_non_empty():
    """CP07: Excel workbook is non-empty (>5,000 bytes)."""
    assert EXCEL_FILE.exists(), f"Missing: {EXCEL_FILE.name}"
    size = EXCEL_FILE.stat().st_size
    assert size > 5_000, f"Excel too small: {size} bytes"


def test_CP08_visual_index_exists():
    """CP08: Visual preview index HTML exists."""
    assert VIS_INDEX.exists(), f"Missing: {VIS_INDEX.name}"


def test_CP09_no_internal_paths_in_visual_index():
    """CP09: Visual index contains no internal filesystem paths."""
    content = VIS_INDEX.read_text(encoding="utf-8")
    for marker in INTERNAL_PATH_MARKERS:
        assert marker not in content, (
            f"Internal path marker found in visual index: '{marker}'"
        )


# ---------------------------------------------------------------------------
# CP10 - CP12: Audit files
# ---------------------------------------------------------------------------

def test_CP10_all_audits_exist():
    """CP10: All 7 audit JSON files exist."""
    for fname in AUDIT_FILES:
        path = AUDIT_DIR / fname
        assert path.exists(), f"Missing audit file: {fname}"


def test_CP11_audits_advisory_only_and_no_fake_sources():
    """CP11: All audits have advisory_only=True and fake_sources_created=False."""
    for fname in AUDIT_FILES:
        data = _load_audit(fname)
        assert data.get("advisory_only") is True, (
            f"{fname}: advisory_only must be True"
        )
        assert data.get("fake_sources_created") is False, (
            f"{fname}: fake_sources_created must be False"
        )


def test_CP12_no_fake_credentials_in_cost_audit():
    """CP12: Cost approach audit (02) confirms no fake credentials."""
    data = _load_audit("02_cost_approach_audit.json")
    assert data.get("fake_credentials_used") is False, (
        "02_cost_approach_audit.json: fake_credentials_used must be False"
    )


# ---------------------------------------------------------------------------
# CP13 - CP19: Final report JSON
# ---------------------------------------------------------------------------

def test_CP13_final_report_exists():
    """CP13: Final report file exists."""
    assert FINAL_RPT.exists(), f"Missing: {FINAL_RPT.name}"


def test_CP14_final_report_overall_status():
    """CP14: Final report overall_status is PASS or PARTIAL."""
    data = _load_final()
    status = data.get("overall_status", "")
    assert status in ("PASS", "PARTIAL"), (
        f"overall_status must be PASS or PARTIAL, got: '{status}'"
    )


def test_CP15_final_report_cost_approach_detailed():
    """CP15: Final report cost_approach_detailed=True."""
    data = _load_final()
    assert data.get("cost_approach_detailed") is True, (
        "final report: cost_approach_detailed must be True"
    )


def test_CP16_final_report_land_sales_comparison_added():
    """CP16: Final report land_sales_comparison_added=True."""
    data = _load_final()
    assert data.get("land_sales_comparison_added") is True, (
        "final report: land_sales_comparison_added must be True"
    )


def test_CP17_final_report_land_extraction_method_added():
    """CP17: Final report land_extraction_method_added=True."""
    data = _load_final()
    assert data.get("land_extraction_method_added") is True, (
        "final report: land_extraction_method_added must be True"
    )


def test_CP18_final_report_land_reconciliation_added():
    """CP18: Final report land_reconciliation_added=True."""
    data = _load_final()
    assert data.get("land_reconciliation_added") is True, (
        "final report: land_reconciliation_added must be True"
    )


def test_CP19_final_report_excel_formulas_added():
    """CP19: Final report excel_formulas_added=True."""
    data = _load_final()
    assert data.get("excel_formulas_added") is True, (
        "final report: excel_formulas_added must be True"
    )
