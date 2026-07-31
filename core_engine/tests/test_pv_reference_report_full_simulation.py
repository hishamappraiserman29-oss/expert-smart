"""
test_pv_reference_report_full_simulation.py
17 tests — Full simulation of the 16-page reference PDF.
advisory_only=True | no_fake_cert=True | certification_ready=False
"""
from __future__ import annotations
import json
from pathlib import Path
import pytest

_CORE = Path(__file__).resolve().parent.parent
_GATE = _CORE / "instance" / "manual_review_outputs" / "valuation_certification_readiness_gate"
_OUT  = _CORE / "instance" / "manual_review_outputs" / "professional_valuation_reference_full_simulation"

_PDF_DIR = _OUT / "pdf_outputs"
_XL_DIR  = _OUT / "excel_outputs"
_PAD     = _OUT / "pdf_audits"
_XAD     = _OUT / "excel_audits"
_SAD     = _OUT / "source_reference_audits"
_PVP     = _OUT / "pdf_visual_previews"
_EVP     = _OUT / "excel_visual_previews"
_FRP     = _OUT / "final_report"

_REF_PDF  = _GATE / "01_market_certification_readiness_preliminary.pdf"
_TRAD_PDF = _PDF_DIR / "traditional_report.pdf"
_TRAD_HTML= _PDF_DIR / "traditional_report.html"
_DET_PDF  = _PDF_DIR / "detailed_report.pdf"
_DET_HTML = _PDF_DIR / "detailed_report.html"
_PRO_PDF  = _PDF_DIR / "professional_report.pdf"
_PRO_HTML = _PDF_DIR / "professional_report.html"
_XL       = _XL_DIR / "professional_valuation_merged_master_workbook.xlsx"
_XLM      = _XL_DIR / "professional_valuation_merged_master_workbook.xlsm"
_P2P_IDX  = _PVP / "OPEN_PAGE_BY_PAGE_TRADITIONAL_COMPARISON.html"
_FINAL_IDX= _OUT / "OPEN_FINAL_REPORT_AND_EXCEL_SIMULATION_REVIEW.html"


def _text(p: Path) -> str:
    if p and p.exists():
        return p.read_text(encoding="utf-8", errors="ignore")
    return ""

def _j(folder: Path, fname: str) -> dict:
    p = folder / fname
    assert p.exists(), f"Audit missing: {p}"
    return json.loads(p.read_text(encoding="utf-8"))

def _trad() -> str: return _text(_TRAD_HTML) or _text(_TRAD_PDF)
def _det()  -> str: return _text(_DET_HTML)  or _text(_DET_PDF)
def _pro()  -> str: return _text(_PRO_HTML)  or _text(_PRO_PDF)

def _xl_names() -> list:
    try:
        import openpyxl
        xl = _XL if _XL.exists() else _XLM
        if not xl.exists(): return []
        wb = openpyxl.load_workbook(str(xl), read_only=True)
        names = list(wb.sheetnames); wb.close()
        return names
    except Exception:
        return []


# ── T01: Reference PDF exists ─────────────────────────────────────────────────
def test_T01_reference_pdf_exists():
    assert _REF_PDF.exists(), "Reference PDF missing"
    assert _REF_PDF.stat().st_size > 100_000, "Reference PDF too small"


# ── T02: Reference page count = 16 ───────────────────────────────────────────
def test_T02_reference_page_count_16():
    d = _j(_PAD, "traditional_reference_page_count_audit.json")
    assert d["reference_page_count"] == 16, "Reference page count should be 16"


# ── T03: traditional_report.pdf exists ───────────────────────────────────────
def test_T03_traditional_pdf_exists():
    assert _TRAD_PDF.exists() or _TRAD_HTML.exists(), \
        "traditional_report.pdf / .html not generated"
    if _TRAD_PDF.exists():
        assert _TRAD_PDF.stat().st_size > 50_000, "Traditional PDF too small"


# ── T04: Traditional report page count = 16 ──────────────────────────────────
def test_T04_traditional_page_count_16():
    d = _j(_PAD, "traditional_reference_page_count_audit.json")
    assert d["generated_page_count"] == 16, \
        f"Traditional should be 16 pages, got {d.get('generated_page_count')}"


# ── T05: Traditional page count matches reference ─────────────────────────────
def test_T05_traditional_page_count_matches_reference():
    d = _j(_PAD, "traditional_reference_page_count_audit.json")
    assert d["page_count_matches_reference"] is True
    assert d["status"] in ("PASS", "PARTIAL"), \
        f"Page count status: {d.get('status')}"


# ── T06: Page-by-page comparison index exists ─────────────────────────────────
def test_T06_page_by_page_comparison_index_exists():
    assert _P2P_IDX.exists(), "OPEN_PAGE_BY_PAGE_TRADITIONAL_COMPARISON.html missing"
    content = _P2P_IDX.read_text(encoding="utf-8", errors="ignore")
    assert len(content) > 1_000, "Page-by-page index too short"
    assert "PASS" in content, "No PASS in page-by-page index"


# ── T07: Traditional visual similarity audit exists ───────────────────────────
def test_T07_traditional_visual_similarity_audit_exists():
    d = _j(_PAD, "traditional_visual_style_simulation_audit.json")
    assert d["arabic_rtl_layout"] is True
    assert d["warning_boxes_present"] is True
    assert d["readiness_blocks_present"] is True
    assert d["certification_gate_present"] is True
    assert d["no_internal_paths"] is True
    assert d["visual_style_status"] == "PASS"


# ── T08: detailed_report.pdf exists ──────────────────────────────────────────
def test_T08_detailed_pdf_exists():
    assert _DET_PDF.exists() or _DET_HTML.exists(), \
        "detailed_report.pdf / .html not generated"
    if _DET_PDF.exists():
        assert _DET_PDF.stat().st_size > 50_000, "Detailed PDF too small"


# ── T09: Detailed includes Traditional + scenarios/sensitivity/sale-vs-rent ───
def test_T09_detailed_includes_traditional_plus_extras():
    d = _j(_PAD, "detailed_report_added_layers_audit.json")
    assert d["includes_full_traditional_structure"] is True
    assert d["what_if_scenarios_added"] is True
    assert d["sensitivity_matrix_added"] is True
    assert d["sale_vs_rent_comparison_added"] is True
    assert d["detailed_richer_than_traditional"] is True
    assert d["status"] == "PASS"
    assert d.get("certification_ready") is False

    txt = _det()
    assert "سيناريو" in txt or "What-If" in txt or "Scenario" in txt
    assert "حساسية" in txt or "Sensitivity" in txt
    assert "إيجار" in txt or "Rent" in txt


# ── T10: professional_report.pdf exists ──────────────────────────────────────
def test_T10_professional_pdf_exists():
    assert _PRO_PDF.exists() or _PRO_HTML.exists(), \
        "professional_report.pdf / .html not generated"
    if _PRO_PDF.exists():
        assert _PRO_PDF.stat().st_size > 50_000, "Professional PDF too small"


# ── T11: Professional includes Detailed + compliance/source/risk/SWOT/ESG/spatial/regression/land adj ──
def test_T11_professional_includes_detailed_plus_professional_layers():
    d = _j(_PAD, "professional_report_added_layers_audit.json")
    assert d["includes_full_detailed_structure"] is True
    assert d["ivs_uspap_rics_matrix_added"] is True
    assert d["source_registry_added"] is True
    assert d["risk_register_added"] is True
    assert d["swot_added"] is True
    assert d["risk_assessment_matrix_added"] is True
    assert d["esg_handled"] is True
    assert d["spatial_analysis_added"] is True
    assert d["multiple_regression_added"] is True
    assert d["land_adjustment_matrix_added"] is True
    assert d["status"] == "PASS"
    assert d.get("certification_ready") is False

    txt = _pro()
    assert "IVS" in txt or "USPAP" in txt or "RICS" in txt
    assert "سجل المصادر" in txt or "Source Registry" in txt or "Registry" in txt
    assert "SWOT" in txt
    assert "ESG" in txt or "استدامة" in txt
    assert "انحدار" in txt or "Regression" in txt


# ── T12: Merged Excel workbook exists ─────────────────────────────────────────
def test_T12_merged_excel_workbook_exists():
    found = _XL.exists() or _XLM.exists()
    assert found, "Merged Excel workbook missing"
    xl = _XL if _XL.exists() else _XLM
    assert xl.stat().st_size > 10_000, "Excel too small"


# ── T13: Excel enhancement audit exists ───────────────────────────────────────
def test_T13_excel_enhancement_audit_exists():
    d = _j(_XAD, "excel_enhancement_and_reference_simulation_audit.json")
    assert d["one_merged_workbook_created"] is True
    assert d["source_files_preserved"] is True
    assert d["similar_sheets_consolidated"] is True
    assert d["legacy_sheets_archived"] is True
    assert d["formulas_added_where_possible"] is True
    assert d["source_registry_present"] is True
    assert d["no_fake_certification"] is True
    assert d["excel_status"] == "PASS"
    assert d.get("certification_ready") is False
    names = _xl_names()
    for req in ["Sales Comparison", "Income Capitalization", "Reconciliation",
                "Risk Register", "Source Registry"]:
        assert req in names, f"Required sheet missing: {req}"


# ── T14: Source files preservation audit ──────────────────────────────────────
def test_T14_source_files_preservation_audit():
    d = _j(_SAD, "source_file_preservation_audit.json")
    assert d["reference_pdf_preserved"] is True
    assert d["source_files_deleted"] is False
    assert d["source_files_overwritten"] is False
    assert d["source_files_modified"] is False
    assert d["new_outputs_created_separately"] is True
    assert d["preservation_status"] == "PASS"


# ── T15: No fake certification ────────────────────────────────────────────────
def test_T15_no_fake_certification():
    d = _j(_PAD, "no_fake_certification_audit.json")
    assert d["certification_ready"] is False
    assert d["fake_signature_created"] is False
    assert d["fake_stamp_created"] is False
    assert d["fake_certification_created"] is False
    assert d["status"] == "PASS"

    for html_path in [_TRAD_HTML, _DET_HTML, _PRO_HTML]:
        if html_path.exists():
            content = html_path.read_text(encoding="utf-8", errors="ignore")
            assert "certification_ready=True" not in content, \
                f"Fake cert in {html_path.name}"
            assert "ختم رسمي معتمد" not in content, \
                f"Fake stamp in {html_path.name}"


# ── T16: No internal paths in generated HTML ──────────────────────────────────
def test_T16_no_internal_paths():
    for f in [_TRAD_HTML, _DET_HTML, _PRO_HTML, _P2P_IDX, _FINAL_IDX]:
        if f and f.exists():
            content = f.read_text(encoding="utf-8", errors="ignore")
            for bad in [r"C:\\Users", "/home/"]:
                assert bad not in content, \
                    f"Internal path in {f.name}: {bad}"


# ── T17: Final review index exists ────────────────────────────────────────────
def test_T17_final_review_index_exists():
    assert _FINAL_IDX.exists(), "OPEN_FINAL_REPORT_AND_EXCEL_SIMULATION_REVIEW.html missing"
    content = _FINAL_IDX.read_text(encoding="utf-8", errors="ignore")
    assert len(content) > 1_000, "Final review index too short"
    assert "certification_ready" in content
    assert "traditional" in content.lower() or "تقليدي" in content
