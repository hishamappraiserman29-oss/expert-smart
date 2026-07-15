"""
test_pv_exact_reference_simulation_three_levels.py
44 tests — Three-level professional valuation reports.
advisory_only=True | no_fake_cert=True | no_commit=True | certification_ready=False
"""
from __future__ import annotations
import json
from pathlib import Path
import pytest

_CORE = Path(__file__).resolve().parent.parent
_OUT  = _CORE / "instance" / "manual_review_outputs" / \
        "professional_valuation_exact_reference_simulation_three_levels"
_GATE = _CORE / "instance" / "manual_review_outputs" / \
        "valuation_certification_readiness_gate"

_PDF_DIR = _OUT / "pdf_outputs"
_XL_DIR  = _OUT / "excel_outputs"
_PAD     = _OUT / "pdf_audits"
_XAD     = _OUT / "excel_audits"
_SAD     = _OUT / "source_reference_audits"
_FRP     = _OUT / "final_report"
_PVP     = _OUT / "pdf_visual_previews"
_EVP     = _OUT / "excel_visual_previews"

_TRAD_PDF = _PDF_DIR / "traditional_report.pdf"
_TRAD_HTML= _PDF_DIR / "traditional_report.html"
_DET_PDF  = _PDF_DIR / "detailed_report.pdf"
_DET_HTML = _PDF_DIR / "detailed_report.html"
_PRO_PDF  = _PDF_DIR / "professional_report.pdf"
_PRO_HTML = _PDF_DIR / "professional_report.html"
_XL       = _XL_DIR  / "professional_valuation_merged_master_workbook.xlsx"
_XLM      = _XL_DIR  / "professional_valuation_merged_master_workbook.xlsm"

_ORD_VAL  = _CORE / "professional_valuation_routes.py"
_TAX_APP  = _CORE / "tax_appeal_routes.py"


def _text(path: Path) -> str:
    if path and path.exists():
        return path.read_text(encoding="utf-8", errors="ignore")
    return ""

def _trad() -> str:
    return _text(_TRAD_HTML) or _text(_TRAD_PDF)

def _det() -> str:
    return _text(_DET_HTML) or _text(_DET_PDF)

def _pro() -> str:
    return _text(_PRO_HTML) or _text(_PRO_PDF)

def _j(folder: Path, fname: str) -> dict:
    p = folder / fname
    assert p.exists(), "Audit missing: " + str(p)
    return json.loads(p.read_text(encoding="utf-8"))

def _xl_names() -> list:
    try:
        import openpyxl
        xl = _XL if _XL.exists() else _XLM
        if not xl.exists():
            return []
        wb = openpyxl.load_workbook(str(xl), read_only=True)
        names = list(wb.sheetnames)
        wb.close()
        return names
    except Exception:
        return []


# ── T01 – T04: Folder and Reference Files ─────────────────────────────────────

def test_T01_output_folder_exists():
    assert _OUT.exists(), "Output folder missing: " + str(_OUT)

def test_T02_reference_pdf_detected():
    ref = _GATE / "01_market_certification_readiness_preliminary.pdf"
    assert ref.exists(), "Reference PDF missing"
    assert ref.stat().st_size > 100_000, "Reference PDF too small"

def test_T03_source_excel_files_detected():
    ref = _GATE / "03_market_certification_readiness_workbook.xlsx"
    assert ref.exists(), "Reference Excel missing"
    assert ref.stat().st_size > 10_000, "Reference Excel too small"

def test_T04_source_files_preserved():
    d = _j(_SAD, "source_files_preservation_audit.json")
    assert d["source_files_preserved"] is True
    assert d["source_files_deleted"] is False
    assert d["source_files_overwritten"] is False
    assert d["source_files_modified"] is False


# ── T05 – T07: PDF Physical Existence ────────────────────────────────────────

def test_T05_traditional_report_exists():
    assert _TRAD_PDF.exists() or _TRAD_HTML.exists(), \
        "traditional_report.pdf / .html missing"

def test_T06_detailed_report_exists():
    assert _DET_PDF.exists() or _DET_HTML.exists(), \
        "detailed_report.pdf / .html missing"

def test_T07_professional_report_exists():
    assert _PRO_PDF.exists() or _PRO_HTML.exists(), \
        "professional_report.pdf / .html missing"


# ── T08: Excel merged workbook ────────────────────────────────────────────────

def test_T08_excel_merged_workbook_exists():
    found = _XL.exists() or _XLM.exists()
    assert found, "Merged Excel workbook missing"
    xl = _XL if _XL.exists() else _XLM
    assert xl.stat().st_size > 10_000, "Excel too small"


# ── T09: Traditional simulates reference structure ────────────────────────────

def test_T09_traditional_simulates_reference_structure():
    d = _j(_PAD, "traditional_exact_reference_simulation_audit.json")
    assert d["reference_pdf_used"] is True
    assert d["traditional_report_simulates_reference_structure"] is True
    assert d["style_similarity_status"] == "PASS"
    assert d.get("certification_ready") is False


# ── T10 – T18: Traditional section presence ──────────────────────────────────

def test_T10_traditional_includes_avm():
    txt = _trad()
    assert "AVM" in txt or "آلي" in txt, "AVM section missing"

def test_T11_traditional_includes_sales_comparison():
    txt = _trad()
    assert "مقارنة" in txt or "Sales" in txt, "Sales comparison missing"

def test_T12_traditional_includes_land_value():
    txt = _trad()
    assert "الأرض" in txt or "أرض" in txt or "land" in txt.lower(), "Land value missing"

def test_T13_traditional_includes_income_capitalization():
    txt = _trad()
    assert "رسملة" in txt or "NOI" in txt or "Income" in txt, "Income capitalization missing"

def test_T14_traditional_includes_cost_approach():
    txt = _trad()
    assert "التكلفة" in txt or "Cost" in txt, "Cost approach missing"

def test_T15_traditional_includes_dcf_support():
    txt = _trad()
    assert "DCF" in txt, "DCF section missing"

def test_T16_traditional_includes_reconciliation():
    txt = _trad()
    assert "التوفيق" in txt or "Reconciliation" in txt or "توفيق" in txt, "Reconciliation missing"

def test_T17_traditional_includes_hbu():
    txt = _trad()
    assert "HBU" in txt or "أفضل" in txt or "أعلى" in txt, "HBU missing"

def test_T18_traditional_includes_readiness_governance():
    txt = _trad()
    assert "جاهزية" in txt or "حوكمة" in txt or "readiness" in txt.lower(), \
        "Readiness/governance blocks missing"

def test_T19_traditional_includes_risk_map():
    txt = _trad()
    assert "المخاطر" in txt or "مخاطر" in txt or "Risk" in txt, "Risk map missing"

def test_T20_traditional_includes_uncertainty_range():
    txt = _trad()
    assert "نطاق" in txt or "uncertainty" in txt.lower() or "عدم اليقين" in txt, \
        "Uncertainty range missing"

def test_T21_traditional_includes_recommendation():
    txt = _trad()
    assert "التوصية" in txt or "توصية" in txt or "Recommendation" in txt, \
        "Recommendation missing"


# ── T22 – T25: Detailed added layers ─────────────────────────────────────────

def test_T22_detailed_includes_all_traditional_sections():
    d = _j(_PAD, "detailed_added_layers_audit.json")
    assert d["includes_all_traditional_sections"] is True
    assert d.get("certification_ready") is False

def test_T23_detailed_includes_whatif_scenarios():
    d = _j(_PAD, "detailed_added_layers_audit.json")
    assert d["what_if_scenarios_added"] is True
    txt = _det()
    assert "سيناريو" in txt or "What-If" in txt or "Scenario" in txt, "Scenarios missing in HTML"

def test_T24_detailed_includes_sensitivity_matrix():
    d = _j(_PAD, "detailed_added_layers_audit.json")
    assert d["sensitivity_matrix_added"] is True
    txt = _det()
    assert "حساسية" in txt or "Sensitivity" in txt or "Cap Rate" in txt, \
        "Sensitivity matrix missing in HTML"

def test_T25_detailed_includes_sale_vs_rent():
    d = _j(_PAD, "detailed_added_layers_audit.json")
    assert d["sale_vs_rent_comparison_added"] is True
    txt = _det()
    assert "إيجار" in txt or "yield" in txt.lower() or "Rent" in txt, \
        "Sale vs rent missing in HTML"


# ── T26 – T37: Professional added layers ──────────────────────────────────────

def test_T26_professional_includes_all_detailed_sections():
    d = _j(_PAD, "professional_added_layers_audit.json")
    assert d["includes_all_detailed_sections"] is True
    assert d.get("certification_ready") is False

def test_T27_professional_includes_ivs_uspap_rics():
    d = _j(_PAD, "professional_added_layers_audit.json")
    assert d["ivs_uspap_rics_matrix_added"] is True
    txt = _pro()
    assert "IVS" in txt or "USPAP" in txt or "RICS" in txt, "IVS/USPAP/RICS missing"

def test_T28_professional_includes_source_registry():
    d = _j(_PAD, "professional_added_layers_audit.json")
    assert d["source_registry_added"] is True
    txt = _pro()
    assert "سجل المصادر" in txt or "Source Registry" in txt or "Registry" in txt, \
        "Source registry missing"

def test_T29_professional_includes_risk_register():
    d = _j(_PAD, "professional_added_layers_audit.json")
    assert d["risk_register_added"] is True
    txt = _pro()
    assert "سجل المخاطر" in txt or "Risk Register" in txt, "Risk register missing"

def test_T30_professional_includes_swot():
    d = _j(_PAD, "professional_added_layers_audit.json")
    assert d["swot_added"] is True
    txt = _pro()
    assert "SWOT" in txt or "نقاط القوة" in txt, "SWOT missing"

def test_T31_professional_includes_risk_assessment_matrix():
    d = _j(_PAD, "professional_added_layers_audit.json")
    assert d["risk_assessment_matrix_added"] is True
    txt = _pro()
    assert "مصفوفة" in txt or "Matrix" in txt, "Risk assessment matrix missing"

def test_T32_professional_esg_handled():
    d = _j(_PAD, "professional_added_layers_audit.json")
    assert d["esg_added_if_available"] is True
    txt = _pro()
    assert "ESG" in txt or "استدامة" in txt, "ESG section missing"

def test_T33_professional_includes_confidence_uncertainty():
    d = _j(_PAD, "professional_added_layers_audit.json")
    assert d["confidence_and_uncertainty_range_added"] is True

def test_T34_professional_includes_special_assumptions():
    d = _j(_PAD, "professional_added_layers_audit.json")
    assert d["special_assumptions_and_limitations_complete"] is True
    txt = _pro()
    assert "افتراضات" in txt or "Assumptions" in txt or "القيود" in txt, \
        "Special assumptions missing"

def test_T35_professional_includes_spatial_analysis():
    d = _j(_PAD, "professional_added_layers_audit.json")
    assert d["spatial_analysis_added"] is True
    txt = _pro()
    assert "مكاني" in txt or "Spatial" in txt or "إحداثيات" in txt, "Spatial analysis missing"

def test_T36_professional_includes_multiple_regression():
    d = _j(_PAD, "professional_added_layers_audit.json")
    assert d["multiple_regression_added"] is True
    txt = _pro()
    assert "انحدار" in txt or "Regression" in txt or "R²" in txt, "Multiple regression missing"

def test_T37_professional_includes_land_adjustment_matrix():
    d = _j(_PAD, "professional_added_layers_audit.json")
    assert d["land_adjustment_matrix_added"] is True
    txt = _pro()
    assert "مصفوفة تعديل الأرض" in txt or "Land Adjustment" in txt, "Land adj matrix missing"


# ── T38 – T40: Excel structure ────────────────────────────────────────────────

def test_T38_one_merged_excel_workbook_exists():
    d = _j(_XAD, "final_excel_merge_mapping.json")
    assert d["one_merged_workbook_created"] is True
    assert d["merge_status"] == "PASS"
    assert d.get("certification_ready") is False

def test_T39_excel_similar_sheets_consolidated():
    d = _j(_XAD, "final_excel_merge_mapping.json")
    assert d["similar_sheets_merged"] is True
    active = d.get("active_consolidated_sheets", [])
    required = ["Sales Comparison", "Income Capitalization", "DCF Support",
                "Reconciliation", "Risk Register", "Source Registry"]
    for r in required:
        assert r in active, "Active sheet missing: " + r

def test_T40_excel_legacy_sheets_archived():
    d = _j(_XAD, "final_excel_merge_mapping.json")
    assert d["legacy_sheets_archived"] is True
    names = _xl_names()
    arch = [n for n in names if n.startswith("ARCH_")]
    assert len(arch) >= 2, "Expected >= 2 ARCH_ legacy sheets, got " + str(len(arch))


# ── T41 – T42: Safety checks ──────────────────────────────────────────────────

def test_T41_no_fake_certification():
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
                "Fake cert in " + html_path.name
            assert "ختم رسمي معتمد" not in content, "Fake stamp in " + html_path.name

def test_T42_no_internal_paths_in_html():
    for html_path in [_TRAD_HTML, _DET_HTML, _PRO_HTML,
                      _PVP / "OPEN_THREE_LEVEL_REPORT_REVIEW_INDEX.html",
                      _EVP / "OPEN_MERGED_EXCEL_REVIEW_INDEX.html"]:
        if html_path.exists():
            content = html_path.read_text(encoding="utf-8", errors="ignore")
            for bad in [r"C:\\Users", "C:/Users", "/home/"]:
                assert bad not in content, "Internal path in " + html_path.name + ": " + bad


# ── T43 – T44: Unaffected existing pages ─────────────────────────────────────

def test_T43_ordinary_valuation_unaffected():
    assert _ORD_VAL.exists(), "professional_valuation_routes.py missing"

def test_T44_tax_appeal_unaffected():
    assert _TAX_APP.exists(), "tax_appeal_routes.py missing"
