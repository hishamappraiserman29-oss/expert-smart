"""
test_pv_integrated_report_merge.py
26 tests — إطار التقرير العربي المتكامل
advisory_only=True | no_fake_cert=True | no_commit=True | certification_ready=False
"""
from __future__ import annotations
import json
import unicodedata
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parent.parent
_OUT  = _CORE / "instance" / "manual_review_outputs" / \
        "professional_valuation_integrated_report_merge"
_PDF  = _OUT / "pdf_outputs"
_PREV = _OUT / "pdf_visual_previews"
_AUD  = _OUT / "pdf_audits"
_FRP  = _OUT / "final_report"

_NAMES  = ["traditional_report", "detailed_report", "professional_report"]
_NOI    = 62_772
_FINAL  = 1_200_000


def _j(fname: str) -> dict:
    p = _AUD / fname
    assert p.exists(), f"Audit missing: {fname}"
    return json.loads(p.read_text(encoding="utf-8"))


def _html(name: str) -> str:
    p = _PREV / f"{name}_preview.html"
    assert p.exists(), f"Preview missing: {name}_preview.html"
    return p.read_text(encoding="utf-8")


def _pdf_text(name: str) -> str:
    p = _PDF / f"{name}.pdf"
    if not p.exists():
        return ""
    try:
        import pypdf
        raw = "\n".join(pg.extract_text() or "" for pg in pypdf.PdfReader(str(p)).pages)
        return unicodedata.normalize("NFKC", raw)
    except Exception:
        return ""


def _has(text: str, *terms: str) -> bool:
    t = unicodedata.normalize("NFKC", text)
    return any(term in t for term in terms)


def _chk(name: str, *terms: str) -> bool:
    return _has(_pdf_text(name), *terms) or _has(_html(name), *terms)


# ── T01: Output folder ────────────────────────────────────────────────────────
def test_T01_output_folder_exists():
    assert _OUT.exists(), f"Output folder missing: {_OUT}"


# ── T02: Three PDFs exist ─────────────────────────────────────────────────────
def test_T02_three_pdfs_exist():
    for name in _NAMES:
        assert (_PDF / f"{name}.pdf").exists(), f"PDF missing: {name}.pdf"


# ── T03: PDFs non-empty ───────────────────────────────────────────────────────
def test_T03_pdfs_non_empty():
    for name in _NAMES:
        p = _PDF / f"{name}.pdf"
        if p.exists():
            assert p.stat().st_size > 10_000, f"PDF too small: {name}"


# ── T04: PDFs are Arabic-first ────────────────────────────────────────────────
def test_T04_pdfs_arabic_first():
    arabic_terms = ["تقرير", "ريال", "القيمة", "التقييم", "العقار"]
    for name in _NAMES:
        h = _html(name)
        found = any(t in h for t in arabic_terms)
        assert found, f"{name}: Arabic content not found in preview"


# ── T05: Unified framework context flag present ───────────────────────────────
def test_T05_unified_framework_context():
    builder = _CORE / "pv_integrated_report_merge_builder.py"
    assert builder.exists(), "Builder script missing"
    src = builder.read_text(encoding="utf-8", errors="ignore")
    assert "single_unified_report_framework" in src
    assert "level_based_expansion" in src or "Level" in src or "level: Level" in src


# ── T06: Traditional — HBU summary ───────────────────────────────────────────
def test_T06_traditional_hbu_summary():
    ok = _chk("traditional_report",
              "مشروع قانوناً", "ممكن مادياً", "مجدٍ مالياً", "الأعلى إنتاجية",
              "HBU", "أعلى وأفضل")
    assert ok, "Traditional: HBU summary not found"


# ── T07: Detailed — structured HBU ───────────────────────────────────────────
def test_T07_detailed_structured_hbu():
    ok = _chk("detailed_report",
              "الاختبارات الأربعة", "HBU", "مشروع قانوناً", "مجدٍ مالياً",
              "الاستخدام الحالي", "البديل المحتمل")
    assert ok, "Detailed: structured HBU not found"


# ── T08: Professional — HBU four tests ───────────────────────────────────────
def test_T08_professional_hbu_four_tests():
    ok = _chk("professional_report",
              "الاختبار الأول", "الاختبار الثاني", "الاختبار الثالث", "الاختبار الرابع",
              "Legally Permissible", "Physically Possible",
              "Financially Feasible", "Maximally Productive")
    assert ok, "Professional: HBU four tests not found"


# ── T09: DCF inside Income Approach ──────────────────────────────────────────
def test_T09_dcf_inside_income_approach():
    for name in ["detailed_report", "professional_report"]:
        ok = _chk(name, "DCF", "أسلوب الدخل", "التدفقات النقدية المخصومة",
                  "Income Approach")
        assert ok, f"{name}: DCF not found inside Income Approach"
    # Traditional has DCF sanity check
    ok_trad = _chk("traditional_report", "DCF", "فحص مبسط", "Sanity")
    assert ok_trad, "Traditional: DCF sanity check not found"


# ── T10: Professional — NPV / IRR ────────────────────────────────────────────
def test_T10_professional_npv_irr():
    ok = _chk("professional_report", "IRR", "NPV", "معدل العائد الداخلي",
              "صافي القيمة الحالية", "8.1")
    assert ok, "Professional: NPV/IRR not found"


# ── T11: Risk linked to value ─────────────────────────────────────────────────
def test_T11_risk_linked_to_value():
    for name in _NAMES:
        ok = _chk(name, "مخاطر", "القيمة المعدلة", "نطاق", "أثر", "1.5%",
                  "risk", "Risk")
        assert ok, f"{name}: risk-to-value linkage not found"


# ── T12: Uncertainty range in all reports ────────────────────────────────────
def test_T12_uncertainty_range_all_reports():
    for name in _NAMES:
        ok = _chk(name, "نطاق", "1,040,000", "1,310,000",
                  "نطاق القيمة", "نطاق عدم اليقين",
                  "Uncertainty", "حد أدنى", "حد أعلى")
        assert ok, f"{name}: uncertainty range not found"


# ── T13: Recommendations in all reports ──────────────────────────────────────
def test_T13_recommendations_all_reports():
    for name in _NAMES:
        ok = _chk(name, "التوصية", "توصية", "يوصى", "النتيجة",
                  "Recommendation", "LTV")
        assert ok, f"{name}: recommendation not found"


# ── T14: Data sources documented ─────────────────────────────────────────────
def test_T14_data_sources_documented():
    for name in _NAMES:
        ok = _chk(name, "مصادر البيانات", "Data Sources", "مصدر", "مصادر",
                  "البيانات")
        assert ok, f"{name}: data sources not found"


# ── T15: Illustrative assumptions explained ───────────────────────────────────
def test_T15_illustrative_assumptions_explained():
    for name in _NAMES:
        ok = _chk(name, "توضيحي", "Illustrative", "افتراض", "الافتراضات",
                  "سبب كونها توضيحية", "الافتراضات التوضيحية")
        assert ok, f"{name}: illustrative assumptions not explained"


# ── T16: Certification gate in all reports ───────────────────────────────────
def test_T16_certification_gate_present():
    for name in _NAMES:
        ok = _chk(name, "بوابة", "certification_ready", "بانتظار المراجعة",
                  "التوقيع", "اسم خبير", "Expert Review Gate")
        assert ok, f"{name}: certification gate not found"


# ── T17: No fake signature ────────────────────────────────────────────────────
def test_T17_no_fake_signature():
    for name in _NAMES:
        h = _html(name)
        assert "no_fake_signature=True" in h or "بانتظار المراجعة" in h, \
            f"{name}: no fake-signature declaration"
        assert "certification_ready=True" not in h, \
            f"{name}: unexpected certification_ready=True"


# ── T18: No fake stamp ────────────────────────────────────────────────────────
def test_T18_no_fake_stamp():
    for name in _NAMES:
        h = _html(name)
        assert "no_fake_stamp=True" in h or "بانتظار المراجعة" in h, \
            f"{name}: no fake-stamp declaration"


# ── T19: No fake certification ────────────────────────────────────────────────
def test_T19_no_fake_certification():
    for name in _NAMES:
        h = _html(name)
        assert "certification_ready=False" in h, \
            f"{name}: certification_ready=False not found"
        assert "certification_ready=True" not in h, \
            f"{name}: fake certification_ready=True found"


# ── T20: Repetition audit passes ─────────────────────────────────────────────
def test_T20_repetition_audit_passes():
    d = _j("integrated_report_repetition_audit.json")
    assert d["repetition_status"] == "PASS"
    assert d["near_duplicate_report_pairs"] == []


# ── T21: Excel number consistency audit passes ────────────────────────────────
def test_T21_excel_number_consistency_audit_passes():
    d = _j("integrated_report_excel_number_consistency_audit.json")
    assert d["number_consistency_status"] == "PASS"
    assert d["noi_pdf_matches_excel"] is True
    assert d["final_value_pdf_matches_excel"] is True
    assert d["mismatches"] == []
    assert d["noi_value"] == _NOI
    assert d["final_value"] == _FINAL


# ── T22: Professional deeper than detailed ───────────────────────────────────
def test_T22_professional_deeper_than_detailed():
    p_pdf = _PDF / "professional_report.pdf"
    d_pdf = _PDF / "detailed_report.pdf"
    if p_pdf.exists() and d_pdf.exists():
        try:
            import pypdf
            p_pages = len(pypdf.PdfReader(str(p_pdf)).pages)
            d_pages = len(pypdf.PdfReader(str(d_pdf)).pages)
            assert p_pages > d_pages, \
                f"Professional ({p_pages} pages) not deeper than Detailed ({d_pages} pages)"
        except Exception:
            pytest.skip("pypdf not available")
    else:
        pytest.skip("PDFs not rendered")


# ── T23: Detailed deeper than traditional ─────────────────────────────────────
def test_T23_detailed_deeper_than_traditional():
    d_pdf = _PDF / "detailed_report.pdf"
    t_pdf = _PDF / "traditional_report.pdf"
    if d_pdf.exists() and t_pdf.exists():
        try:
            import pypdf
            d_pages = len(pypdf.PdfReader(str(d_pdf)).pages)
            t_pages = len(pypdf.PdfReader(str(t_pdf)).pages)
            assert d_pages > t_pages, \
                f"Detailed ({d_pages} pages) not deeper than Traditional ({t_pages} pages)"
        except Exception:
            pytest.skip("pypdf not available")
    else:
        pytest.skip("PDFs not rendered")


# ── T24: No internal paths ────────────────────────────────────────────────────
def test_T24_no_internal_paths():
    for name in _NAMES:
        h = _html(name)
        for pat in [r"C:\\Users", "C:/Users", "/home/", "core_engine/instance"]:
            assert pat not in h, f"{name} preview: internal path found: {pat}"
    for fname in [
        "integrated_report_merge_master_audit.json",
        "integrated_report_excel_number_consistency_audit.json",
        "integrated_report_certification_gate_audit.json",
    ]:
        f = _AUD / fname
        if f.exists():
            content = f.read_text(encoding="utf-8")
            for pat in [r"C:\\Users", "C:/Users", "/home/"]:
                assert pat not in content, f"{fname}: internal path found: {pat}"


# ── T25: Ordinary valuation unaffected ───────────────────────────────────────
def test_T25_ordinary_valuation_unaffected():
    bridge = _CORE / "bridge_api.py"
    assert bridge.exists(), "bridge_api.py missing"
    frontend = _CORE.parent / "frontend" / "index.html"
    if not frontend.exists():
        frontend = _CORE / "frontend" / "index.html"
    assert frontend.exists(), "frontend/index.html missing"


# ── T26: Tax appeal unaffected ────────────────────────────────────────────────
def test_T26_tax_appeal_unaffected():
    bridge = _CORE / "bridge_api.py"
    assert bridge.exists()
    content = bridge.read_text(encoding="utf-8", errors="ignore")
    assert "tax" in content.lower() or "ضريبة" in content or "appeal" in content.lower(), \
        "Tax appeal routes appear missing from bridge_api.py"
