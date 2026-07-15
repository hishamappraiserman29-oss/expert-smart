"""
test_pv_pdf_modern_methods_upgrade.py
اختبارات الواجهة الخلفية — تحسين تقارير PDF لتعكس الأساليب الحديثة من Excel القديم

تشغيل:
  python -m pytest core_engine/tests/test_pv_pdf_modern_methods_upgrade.py -q

arabic_primary=True | uses_legacy_excel_methods=True | advisory_only=True
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_CORE))

_QA   = _CORE / "instance" / "manual_review_outputs" / "professional_valuation_pdf_modern_methods_upgrade"
_PDF  = _QA / "pdf_outputs"
_PREV = _QA / "pdf_visual_previews"
_LEG  = _QA / "legacy_excel_audits"
_METH = _QA / "method_coverage_audits"
_DIST = _QA / "report_distinctness_audits"
_STRC = _QA / "report_structure_audits"


def _load(path: Path) -> dict:
    assert path.exists(), f"Missing: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def _html(key: str) -> str:
    p = _PREV / f"{key}_preview.html"
    assert p.exists(), f"Missing preview HTML: {p}"
    return p.read_text(encoding="utf-8")


# ── T01: QA folder exists ─────────────────────────────────────────────────────

def test_T01_qa_folder_exists():
    """T01: QA output folder and subfolders exist."""
    assert _QA.exists()
    assert _PDF.exists()
    assert _PREV.exists()


# ── T02: Legacy Excel method inventory exists ─────────────────────────────────

def test_T02_legacy_method_inventory_exists():
    """T02: legacy_excel_method_inventory.json exists."""
    p = _LEG / "legacy_excel_method_inventory.json"
    assert p.exists(), "legacy_excel_method_inventory.json missing"
    data = _load(p)
    assert data.get("legacy_reference_used") == "Report_ES_GRAND_FINAL_v4.xlsm"


# ── T03: traditional_report.pdf exists ───────────────────────────────────────

def test_T03_traditional_pdf_exists():
    """T03: traditional_report.pdf exists and is non-empty."""
    p = _PDF / "traditional_report.pdf"
    assert p.exists()
    assert p.stat().st_size > 1_000


# ── T04: detailed_report.pdf exists ──────────────────────────────────────────

def test_T04_detailed_pdf_exists():
    """T04: detailed_report.pdf exists and is non-empty."""
    p = _PDF / "detailed_report.pdf"
    assert p.exists()
    assert p.stat().st_size > 1_000


# ── T05: professional_report.pdf exists ──────────────────────────────────────

def test_T05_professional_pdf_exists():
    """T05: professional_report.pdf exists and is non-empty."""
    p = _PDF / "professional_report.pdf"
    assert p.exists()
    assert p.stat().st_size > 1_000


# ── T06: All PDFs are non-empty ───────────────────────────────────────────────

def test_T06_all_pdfs_non_empty():
    """T06: all three PDFs are larger than 10KB."""
    for name in ["traditional_report.pdf", "detailed_report.pdf", "professional_report.pdf"]:
        p = _PDF / name
        assert p.exists()
        assert p.stat().st_size > 10_000, f"{name} is too small"


# ── T07: PDFs have Arabic primary headings ────────────────────────────────────

def test_T07_pdfs_have_arabic_headings():
    """T07: HTML previews have lang='ar' and dir='rtl'."""
    for key in ["traditional_report", "detailed_report", "professional_report"]:
        content = _html(key)
        assert "lang='ar'" in content or 'lang="ar"' in content, f"{key} missing lang=ar"
        assert "dir='rtl'" in content or 'dir="rtl"' in content, f"{key} missing dir=rtl"


# ── T08: Traditional includes Market/Income/Cost/AVM ─────────────────────────

def test_T08_traditional_includes_core_methods():
    """T08: traditional report includes Market, Income, Cost, AVM."""
    content = _html("traditional_report")
    for term in ["أسلوب السوق", "أسلوب الدخل", "أسلوب التكلفة", "AVM"]:
        assert term in content, f"Traditional missing: {term}"


# ── T09: Detailed includes DCF summary ───────────────────────────────────────

def test_T09_detailed_includes_dcf():
    """T09: detailed report includes DCF summary."""
    content = _html("detailed_report")
    assert "DCF" in content or "التدفقات النقدية" in content, \
        "detailed report missing DCF"


# ── T10: Detailed includes sensitivity snapshot ───────────────────────────────

def test_T10_detailed_includes_sensitivity():
    """T10: detailed report includes sensitivity snapshot."""
    content = _html("detailed_report")
    assert "الحساسية" in content or "Sensitivity" in content, \
        "detailed report missing sensitivity"


# ── T11: Detailed includes risk notes ────────────────────────────────────────

def test_T11_detailed_includes_risk_notes():
    """T11: detailed report includes risk notes."""
    content = _html("detailed_report")
    assert "المخاطر" in content or "Risk" in content, \
        "detailed report missing risk notes"


# ── T12: Detailed is richer than traditional ──────────────────────────────────

def test_T12_detailed_richer_than_traditional():
    """T12: detailed report has more sections than traditional."""
    trad = _html("traditional_report")
    det  = _html("detailed_report")
    trad_h2 = trad.count("<h2>")
    det_h2  = det.count("<h2>")
    assert det_h2 > trad_h2, \
        f"detailed_h2={det_h2} not > traditional_h2={trad_h2}"


# ── T13: Professional includes DCF ───────────────────────────────────────────

def test_T13_professional_includes_dcf():
    """T13: professional report includes DCF full analysis."""
    content = _html("professional_report")
    assert "DCF" in content or "التدفقات النقدية" in content, \
        "professional report missing DCF"


# ── T14: Professional includes HBU summary ───────────────────────────────────

def test_T14_professional_includes_hbu():
    """T14: professional report includes HBU analysis."""
    content = _html("professional_report")
    assert "HBU" in content or "أعلى وأفضل استخدام" in content, \
        "professional report missing HBU"


# ── T15: Professional includes scenario analysis ─────────────────────────────

def test_T15_professional_includes_scenarios():
    """T15: professional report includes scenario analysis."""
    content = _html("professional_report")
    assert "السيناريو" in content or "Scenario" in content, \
        "professional report missing scenario analysis"


# ── T16: Professional includes sensitivity analysis ──────────────────────────

def test_T16_professional_includes_sensitivity():
    """T16: professional report includes full sensitivity analysis."""
    content = _html("professional_report")
    assert "الحساسية" in content or "Sensitivity" in content, \
        "professional report missing sensitivity"


# ── T17: Professional includes risk-adjusted valuation ───────────────────────

def test_T17_professional_includes_risk_adjusted():
    """T17: professional report includes risk-adjusted valuation discussion."""
    content = _html("professional_report")
    assert "المخاطر" in content or "Risk" in content, \
        "professional report missing risk discussion"


# ── T18: Professional includes AVM reliability discussion ─────────────────────

def test_T18_professional_includes_avm_reliability():
    """T18: professional report includes AVM reliability discussion."""
    content = _html("professional_report")
    assert "AVM" in content, "professional report missing AVM"
    assert "موثوقية" in content or "reliability" in content.lower(), \
        "professional report missing AVM reliability discussion"


# ── T19: Professional includes weighted reconciliation ───────────────────────

def test_T19_professional_includes_reconciliation():
    """T19: professional report includes weighted reconciliation."""
    content = _html("professional_report")
    assert "التوفيق" in content or "الترجيح" in content, \
        "professional report missing reconciliation"


# ── T20: Professional includes standards matrix ───────────────────────────────

def test_T20_professional_includes_standards_matrix():
    """T20: professional report includes standards compliance matrix."""
    content = _html("professional_report")
    assert "IVS" in content or "المعايير" in content, \
        "professional report missing standards matrix"


# ── T21: Professional reflects legacy Excel methods ───────────────────────────

def test_T21_professional_reflects_excel_methods():
    """T21: professional report HTML references Excel-derived methods."""
    content = _html("professional_report")
    for term in ["DCF", "الحساسية", "HBU", "السيناريو", "المخاطر", "AVM", "التوفيق", "IVS"]:
        assert term in content, f"Professional missing legacy Excel method term: {term}"


# ── T22: Professional is richer than detailed ────────────────────────────────

def test_T22_professional_richer_than_detailed():
    """T22: professional report has more sections than detailed."""
    det = _html("detailed_report")
    pro = _html("professional_report")
    det_h2 = det.count("<h2>")
    pro_h2 = pro.count("<h2>")
    assert pro_h2 > det_h2, \
        f"professional_h2={pro_h2} not > detailed_h2={det_h2}"


# ── T23: Method coverage audit passes ────────────────────────────────────────

def test_T23_method_coverage_audit_passes():
    """T23: method coverage audit = PASS and all required methods covered."""
    data = _load(_METH / "pdf_methods_added_from_legacy_excel_audit.json")
    assert data.get("coverage_status") == "PASS"
    assert data.get("critical_gaps_remaining") == []
    trad = data.get("traditional_report", {})
    assert trad.get("market_approach") is True
    assert trad.get("income_approach") is True
    det = data.get("detailed_report", {})
    assert det.get("dcf_summary") is True
    assert det.get("sensitivity_snapshot") is True
    pro = data.get("professional_report", {})
    assert pro.get("dcf_analysis") is True
    assert pro.get("hbu_summary") is True
    assert pro.get("scenario_analysis") is True
    assert pro.get("sensitivity_analysis") is True
    assert pro.get("risk_adjusted_valuation") is True
    assert pro.get("avm_reliability_discussion") is True
    assert pro.get("weighted_reconciliation") is True
    assert pro.get("reflects_legacy_excel_methods") is True


# ── T24: Distinctness audit passes ───────────────────────────────────────────

def test_T24_distinctness_audit_passes():
    """T24: distinctness audit confirms three reports are distinct."""
    data = _load(_DIST / "pdf_depth_distinctness_after_modern_methods_upgrade.json")
    assert data.get("distinctness_status") == "PASS"
    assert data.get("traditional_less_detailed_than_detailed") is True
    assert data.get("detailed_less_detailed_than_professional") is True
    assert data.get("professional_is_highest_depth") is True
    assert data.get("near_duplicate_report_pairs") == []


# ── T25: Physical files audit passes ─────────────────────────────────────────

def test_T25_physical_files_audit_passes():
    """T25: physical files audit = PASS."""
    data = _load(_STRC / "pdf_physical_files_after_modern_methods_upgrade.json")
    assert data.get("physical_files_status") == "PASS"
    for f in data.get("pdf_files", []):
        assert f["exists"] is True, f'{f["file_name"]} exists=False'
        assert f["contains_internal_paths"] is False
        assert f["contains_fake_certification"] is False


# ── T26: Visual preview index exists ─────────────────────────────────────────

def test_T26_visual_preview_index_exists():
    """T26: pdf_modern_methods_visual_review_index.html exists."""
    p = _PREV / "pdf_modern_methods_visual_review_index.html"
    assert p.exists(), "Visual review index missing"


# ── T27: No fake certification ───────────────────────────────────────────────

def test_T27_no_fake_certification():
    """T27: no fake certification or stamp in any preview."""
    for key in ["traditional_report", "detailed_report", "professional_report"]:
        content = _html(key)
        assert "مسودة" in content, f"{key} missing draft notice"
        if "certification_ready" in content.lower():
            assert "False" in content, f"{key} shows certification_ready=True — fake cert!"


# ── T28: No internal paths ────────────────────────────────────────────────────

def test_T28_no_internal_paths():
    """T28: no Windows filesystem paths appear in any HTML preview."""
    for key in ["traditional_report", "detailed_report", "professional_report"]:
        content = _html(key)
        for pat in (r"C:\\Users", r"C:/Users", "/home/", "expert_smart1",
                    "core_engine/instance"):
            assert pat not in content, f"Internal path leaked in {key}: {pat}"


# ── T29: Ordinary valuation unaffected ───────────────────────────────────────

def test_T29_ordinary_valuation_unaffected():
    """T29: ordinary valuation page still present in frontend."""
    frontend = _CORE.parent / "frontend" / "index.html"
    assert frontend.exists()
    content = frontend.read_text(encoding="utf-8")
    assert 'id="simple-certified-report-cta-box"' in content


# ── T30: Tax appeal unaffected ───────────────────────────────────────────────

def test_T30_tax_appeal_unaffected():
    """T30: tax appeal content still present in frontend."""
    frontend = _CORE.parent / "frontend" / "index.html"
    content = frontend.read_text(encoding="utf-8")
    assert "ضريبي" in content or "ضريبة" in content or "tax" in content.lower()
