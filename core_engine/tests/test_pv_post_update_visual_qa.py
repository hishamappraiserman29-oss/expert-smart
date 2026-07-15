"""
Backend Visual QA tests — Post-Update Core Valuation Reports.
PU01-PU20.
Run: python -m pytest tests/test_pv_post_update_visual_qa.py -q
"""
from __future__ import annotations
import json, pathlib
import pytest

_ROOT = pathlib.Path(__file__).parent.parent
_OUT  = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_post_update_visual_qa"
_PDF  = _OUT / "pdf_outputs"
_XL   = _OUT / "excel_outputs"
_AUD  = _OUT / "qa_audits"
_PREV = _OUT / "visual_previews"
_SS   = _OUT / "screenshots"
_RPT  = _OUT / "final_report"
_EXLP = _OUT / "excel_previews"

_TRAD = _PDF / "traditional_valuation_report_post_update.pdf"
_DET  = _PDF / "detailed_valuation_report_post_update.pdf"
_PROF = _PDF / "professional_valuation_report_post_update.pdf"
_XLWB = _XL  / "core_valuation_master_workbook_post_update.xlsx"
_IDX  = _PREV / "OPEN_POST_UPDATE_VISUAL_QA_INDEX.html"


def _aud(name: str) -> dict:
    p = _AUD / name
    assert p.exists(), f"Audit missing: {name}"
    return json.loads(p.read_text(encoding="utf-8"))


# PU01: output folder
def test_PU01_output_folder_exists(): assert _OUT.is_dir()

# PU02-PU04: PDFs exist
def test_PU02_traditional_pdf_exists(): assert _TRAD.exists()
def test_PU03_detailed_pdf_exists():    assert _DET.exists()
def test_PU04_professional_pdf_exists(): assert _PROF.exists()

# PU05: PDFs non-empty
def test_PU05_pdfs_non_empty():
    for p in [_TRAD, _DET, _PROF]:
        assert p.stat().st_size > 10_000, f"{p.name} too small"

# PU06: Excel workbook exists
def test_PU06_excel_workbook_exists(): assert _XLWB.exists()

# PU07: Excel non-empty
def test_PU07_excel_workbook_non_empty():
    assert _XLWB.stat().st_size > 5_000

# PU08: Visual index exists
def test_PU08_visual_index_exists(): assert _IDX.exists()

# PU09: Screenshots exist (at least 35)
def test_PU09_screenshots_exist():
    ss = list(_SS.glob("*.png"))
    assert len(ss) >= 35, f"Only {len(ss)} screenshots"

# PU10: All 12 audits exist
def test_PU10_all_12_audits_exist():
    for i in range(1, 13):
        prefix = f"{i:02d}_"
        matches = list(_AUD.glob(prefix + "*.json"))
        assert matches, f"Audit {prefix}* missing"

# PU11: All audits have safety flags
def test_PU11_all_audits_safety_flags():
    for f in _AUD.glob("*.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        assert d.get("advisory_only") is True, f"{f.name}: advisory_only missing"
        assert d.get("fake_sources_created") is False, f"{f.name}: fake_sources"

# PU12: No fake signature
def test_PU12_no_fake_signature():
    a = _aud("03_pdf_physical_audit.json")
    assert a.get("fake_signature_created") is False
    assert a.get("fake_valuer_created") is False
    assert a.get("fake_license_created") is False
    assert a.get("fake_stamp_created") is False

# PU13: No internal paths in visual index
def test_PU13_no_internal_paths_in_index():
    c = _IDX.read_text(encoding="utf-8", errors="ignore")
    assert r"C:\Users\Lenovo" not in c
    assert "C:/Users/Lenovo" not in c

# PU14: Professional report has compliance certificate
def test_PU14_professional_compliance_certificate():
    a = _aud("06_professional_visual_audit.json")
    assert a.get("compliance_certificate_after_cover") is True

# PU15: Professional report has TOC
def test_PU15_professional_toc():
    a = _aud("06_professional_visual_audit.json")
    assert a.get("toc_present") is True

# PU16: Professional report has risk matrix
def test_PU16_professional_risk_matrix():
    a = _aud("06_professional_visual_audit.json")
    assert a.get("risk_matrix_5x5_early") is True

# PU17: Detailed report has executive summary
def test_PU17_detailed_executive_summary():
    a = _aud("05_detailed_visual_audit.json")
    assert a.get("executive_summary_page_2_present") is True

# PU18: Excel dashboard preview exists
def test_PU18_excel_dashboard_preview():
    assert (_EXLP / "OPEN_EXCEL_DASHBOARD_PREVIEW.html").exists()

# PU19: Excel formula preview exists
def test_PU19_excel_formula_preview():
    assert (_EXLP / "OPEN_EXCEL_FORMULAS_PREVIEW.html").exists()

# PU20: Final report exists with valid status
def test_PU20_final_report_status():
    rpt = _RPT / "final_post_update_visual_qa_report.txt"
    assert rpt.exists()
    d = json.loads(rpt.read_text(encoding="utf-8"))
    assert d.get("overall_status") in ("PASS", "PARTIAL"), \
        f"Status: {d.get('overall_status')}"
    assert d.get("fake_signature_created") is False
    assert d.get("internal_paths_exposed") is False
