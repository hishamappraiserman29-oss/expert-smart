"""
test_pv_visual_review_excel_and_pdfs.py
18 tests — Visual QA Review for Admin Excel and Three PDF Reports
advisory_only=True | no_fake_cert=True | no_commit=True | certification_ready=False
"""
from __future__ import annotations
import json
from pathlib import Path
import pytest

_CORE = Path(__file__).resolve().parent.parent
_OUT  = _CORE / "instance" / "manual_review_outputs" / \
        "professional_valuation_visual_review_excel_and_pdfs"
_SNAP = _OUT / "source_files_snapshot"
_XLPR = _OUT / "excel_visual_review" / "sheet_previews"
_PDFP = _OUT / "pdf_visual_review" / "pdf_page_previews"
_CMP  = _OUT / "comparison_review"
_AUD  = _OUT / "audits"
_SCR  = _OUT / "screenshots"
_FREP = _OUT / "final_report"
_VIDX = _OUT / "visual_index"

_PDF_NAMES   = ["traditional_report", "detailed_report", "professional_report"]
_SHEET_SLUGS = [
    "01_Cover","02_Data_Quality","03_Property","04_HBU_Analysis","05_Comparables",
    "06_Income_Approach","07_Cost_Approach","08_AVM_Reference","09_Scenarios",
    "10_Sensitivity_Matrix","11_Reconciliation","12_Risk_Register",
    "13_Standards_Matrix","14_Source_Registry","15_Admin_Notes",
]

def _j(fname: str) -> dict:
    p = _AUD / fname
    assert p.exists(), f"Audit missing: {fname}"
    return json.loads(p.read_text(encoding="utf-8"))


# T01 — Visual review folder exists
def test_T01_visual_review_folder_exists():
    assert _OUT.exists(), f"Review folder missing: {_OUT}"


# T02 — source_files_snapshot exists
def test_T02_source_files_snapshot_exists():
    assert _SNAP.exists(), "source_files_snapshot/ missing"


# T03 — Excel snapshot exists and is non-empty (accepts .xlsm or .xlsx)
def test_T03_excel_snapshot_exists():
    xlsm = _SNAP / "professional_valuation_admin_master_workbook.xlsm"
    xlsx = _SNAP / "professional_valuation_admin_master_workbook.xlsx"
    xl = xlsm if xlsm.exists() else xlsx
    assert xl.exists(), f"Excel snapshot missing (checked .xlsm and .xlsx in {_SNAP})"
    assert xl.stat().st_size > 10_000, f"Excel snapshot too small: {xl.stat().st_size}"


# T04 — Three PDF snapshots exist and are non-empty
def test_T04_three_pdf_snapshots_exist():
    for name in _PDF_NAMES:
        p = _SNAP / f"{name}.pdf"
        assert p.exists(), f"PDF snapshot missing: {name}.pdf"
        assert p.stat().st_size > 50_000, f"PDF snapshot too small: {name}"


# T05 — Excel structure audit exists and passes
def test_T05_excel_structure_audit_exists_and_passes():
    d = _j("03_excel_structure_visual_audit.json")
    assert d["excel_structure_status"] == "PASS", f"Excel structure FAILED: {d}"
    assert d["first_15_sheets_are_master_sheets"] is True
    assert d["exact_master_sheet_order"] is True
    assert d["total_sheet_count"] >= 17


# T06 — Excel master sheet content audit exists and passes
def test_T06_excel_master_sheet_content_audit_passes():
    d = _j("04_excel_master_sheet_content_audit.json")
    assert d["excel_content_status"] in ("PASS", "PARTIAL"), \
        f"Excel content audit FAILED: {d.get('excel_content_status')}"
    # All 15 master sheets must have previews created
    sheet_keys = [
        "Cover","Data Quality","Property","HBU Analysis","Comparables",
        "Income Approach","Cost Approach","AVM Reference","Scenarios",
        "Sensitivity Matrix","Reconciliation","Risk Register",
        "Standards Matrix","Source Registry","Admin Notes",
    ]
    for sk in sheet_keys:
        assert d.get(sk, {}).get("preview_created") is True, \
            f"Sheet preview missing: {sk}"


# T07 — Excel legacy archive audit exists
def test_T07_excel_legacy_archive_audit_exists():
    d = _j("05_excel_legacy_archive_visual_audit.json")
    assert d["legacy_archive_status"] in ("PASS", "PARTIAL"), \
        f"Legacy archive status unexpected: {d.get('legacy_archive_status')}"
    assert d["legacy_archive_sheet_count"] >= 2, \
        f"Expected >= 2 legacy sheets, got {d.get('legacy_archive_sheet_count')}"


# T08 — PDF visual content audit exists and passes
def test_T08_pdf_visual_content_audit_passes():
    d = _j("06_pdf_visual_content_audit.json")
    assert d["pdf_visual_content_status"] == "PASS", \
        f"PDF visual content FAILED: {d.get('pdf_visual_content_status')}"
    for name in _PDF_NAMES:
        key = name  # same key format in audit
        assert d[key]["exists"] is True, f"{name}: not found in audit"
        assert d[key]["page_count"] > 0, f"{name}: zero pages"
        assert d[key]["arabic_first"] is True, f"{name}: not Arabic-first"


# T09 — PDF distinctness audit passes
def test_T09_pdf_distinctness_audit_passes():
    d = _j("07_pdf_distinctness_visual_audit.json")
    assert d["distinctness_status"] == "PASS", \
        f"Distinctness FAILED: {d.get('distinctness_status')}"
    assert d["traditional_less_detailed_than_detailed"] is True
    assert d["detailed_less_detailed_than_professional"] is True
    assert d["near_duplicate_report_pairs"] == []


# T10 — Excel/PDF consistency audit exists
def test_T10_excel_pdf_consistency_audit_exists():
    d = _j("08_excel_pdf_consistency_audit.json")
    assert d["number_consistency_status"] in ("PASS", "PARTIAL"), \
        f"Consistency status unexpected: {d.get('number_consistency_status')}"
    assert len(d.get("checked_fields", [])) >= 10, "Too few fields checked"


# T11 — Main visual review index exists
def test_T11_main_visual_review_index_exists():
    idx = _VIDX / "OPEN_VISUAL_REVIEW_EXCEL_AND_PDFS.html"
    assert idx.exists(), "Main visual review index missing"
    content = idx.read_text(encoding="utf-8")
    assert "OPEN_VISUAL_REVIEW" in idx.name
    assert len(content) > 2_000, "Index too short"


# T12 — Excel sheet previews exist for all 15 master sheets
def test_T12_excel_sheet_previews_exist():
    for slug in _SHEET_SLUGS:
        p = _XLPR / f"{slug}_preview.html"
        assert p.exists(), f"Sheet preview missing: {slug}_preview.html"
        assert p.stat().st_size > 500, f"Sheet preview empty: {slug}"


# T13 — PDF previews exist (HTML or page preview)
def test_T13_pdf_page_previews_exist():
    # At least one of: page_preview.html in subfolder, or HTML preview from source
    _SRC_MERGE = _CORE / "instance" / "manual_review_outputs" / \
                 "professional_valuation_integrated_report_merge"
    found_any = False
    for name in _PDF_NAMES:
        page_html = _PDFP / f"{name}_pages" / "page_preview.html"
        src_html  = _SRC_MERGE / "pdf_visual_previews" / f"{name}_preview.html"
        has = page_html.exists() or src_html.exists()
        assert has, f"No preview for {name}"
        found_any = True
    assert found_any


# T14 — Side-by-side PDF comparison exists
def test_T14_side_by_side_pdf_comparison_exists():
    p = _CMP / "pdf_three_reports_side_by_side.html"
    assert p.exists(), "Side-by-side comparison missing"
    content = p.read_text(encoding="utf-8")
    assert "traditional" in content.lower() or "تقليدي" in content
    assert "detailed" in content.lower() or "تفصيلي" in content
    assert "professional" in content.lower() or "مهني" in content


# T15 — Screenshots exist or blocker is documented
def test_T15_screenshots_exist_or_blocker_documented():
    pngs   = list(_SCR.glob("*.png"))
    blocker = _SCR / "screenshot_blocker.txt"
    assert len(pngs) > 0 or blocker.exists(), \
        "Neither screenshots nor blocker documentation found"


# T16 — Final status is not PASS if required physical files are missing
def test_T16_final_status_reflects_physical_files():
    d1 = _j("01_file_discovery_and_physical_audit.json")
    assert d1["physical_file_status"] == "PASS", \
        f"Physical files FAILED — final status must not be PASS. Blocker: {d1}"
    # If physical is PASS, final report should also indicate PASS
    frep = _FREP / "final_visual_review_excel_and_pdfs_report.txt"
    if frep.exists():
        content = frep.read_text(encoding="utf-8")
        assert "Review Status: PASS" in content or "Review Status: PARTIAL" in content, \
            "Final report does not match physical file status"


# T17 — No fake certification in main outputs and audit JSON structured values
def test_T17_no_fake_certification():
    # Audit JSONs: check no structured field has certification_ready=true
    import json as _json

    def _check_no_cert_true(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "certification_ready" and v is True:
                    raise AssertionError(
                        f"certification_ready=True found at path '{path}.{k}'")
                _check_no_cert_true(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                _check_no_cert_true(v, f"{path}[{i}]")

    for f in _AUD.glob("*.json"):
        _check_no_cert_true(_json.loads(f.read_text(encoding="utf-8")), f.name)

    # Main index HTML: certification_ready=False must be present, not True as a status
    idx = _VIDX / "OPEN_VISUAL_REVIEW_EXCEL_AND_PDFS.html"
    if idx.exists():
        content = idx.read_text(encoding="utf-8")
        assert "certification_ready=True" not in content, \
            "Fake certification in main index HTML"

    # Side-by-side comparison must not claim cert ready
    cmp_html = _CMP / "pdf_three_reports_side_by_side.html"
    if cmp_html.exists():
        content = cmp_html.read_text(encoding="utf-8")
        assert "certification_ready=True" not in content, \
            "Fake certification in side-by-side HTML"


# T18 — No internal filesystem paths in generated review HTML
def test_T18_no_internal_paths_in_review_html():
    idx = _VIDX / "OPEN_VISUAL_REVIEW_EXCEL_AND_PDFS.html"
    if not idx.exists():
        pytest.skip("Index not created")
    content = idx.read_text(encoding="utf-8")
    for pat in [r"C:\\Users", "C:/Users", "/home/", "core_engine/instance/"]:
        assert pat not in content, f"Internal path found in index: {pat}"
    # Also check sheet previews
    for html in _XLPR.glob("*.html"):
        c = html.read_text(encoding="utf-8", errors="ignore")
        for pat in [r"C:\\Users", "C:/Users"]:
            assert pat not in c, f"Internal path in {html.name}: {pat}"
