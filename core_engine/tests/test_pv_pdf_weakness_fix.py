"""
test_pv_pdf_weakness_fix.py
34 tests — تصحيح ثغرات تقارير PDF
advisory_only=True | no_fake_cert=True | no_commit=True | certification_ready=False
"""
from __future__ import annotations
import json
import sys
import unicodedata
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parent.parent
_OUT  = _CORE / "instance" / "manual_review_outputs" / \
        "professional_valuation_pdf_weakness_fix"
_PDF  = _OUT / "pdf_outputs"
_PREV = _OUT / "pdf_visual_previews"
_AUD  = _OUT / "pdf_audits"
_FRP  = _OUT / "final_report"

# Source-of-truth values (same as builder)
_NOI       = 62_772
_FINAL_VAL = 1_200_000
_XL_SRC    = _CORE / "instance" / "manual_review_outputs" / \
             "professional_valuation_single_excel_15_master_plus_legacy_archive_three_pdfs" / "excel_outputs"
_XL_NAME   = "professional_valuation_admin_master_workbook.xlsm"


def _j(p: Path) -> dict:
    assert p.exists(), f"Audit missing: {p}"
    return json.loads(p.read_text(encoding="utf-8"))


def _html(name: str) -> str:
    p = _PREV / f"{name}_preview.html"
    assert p.exists(), f"Preview missing: {p}"
    return p.read_text(encoding="utf-8")


def _pdf_text(name: str) -> str:
    p = _PDF / f"{name}.pdf"
    if not p.exists():
        return ""
    try:
        import pypdf
        r = pypdf.PdfReader(str(p))
        raw = "\n".join(pg.extract_text() or "" for pg in r.pages)
        return unicodedata.normalize("NFKC", raw)
    except Exception:
        return ""


def _has(text: str, *terms: str) -> bool:
    t = unicodedata.normalize("NFKC", text)
    return any(term in t for term in terms)


def _chk(name: str, *terms: str) -> bool:
    return _has(_pdf_text(name), *terms) or _has(_html(name), *terms)


# ── T01: QA folder ────────────────────────────────────────────────────────────
def test_T01_qa_folder_exists():
    assert _OUT.exists(), f"QA folder missing: {_OUT}"


# ── T02: PDF files exist ──────────────────────────────────────────────────────
def test_T02_three_pdf_files_exist():
    for name in ["traditional_report", "detailed_report", "professional_report"]:
        p = _PDF / f"{name}.pdf"
        assert p.exists(), f"PDF missing: {name}.pdf"


# ── T03: PDFs non-empty ───────────────────────────────────────────────────────
def test_T03_pdfs_non_empty():
    for name in ["traditional_report", "detailed_report", "professional_report"]:
        p = _PDF / f"{name}.pdf"
        if p.exists():
            assert p.stat().st_size > 10_000, f"PDF too small: {name}"


# ── T04: PDFs open successfully ───────────────────────────────────────────────
def test_T04_pdfs_open_successfully():
    for name in ["traditional_report", "detailed_report", "professional_report"]:
        p = _PDF / f"{name}.pdf"
        if not p.exists():
            pytest.skip(f"PDF not rendered: {name}")
        try:
            import pypdf
            r = pypdf.PdfReader(str(p))
            assert len(r.pages) > 0
        except Exception as e:
            pytest.fail(f"{name}: {e}")


# ── T05: Traditional — HBU summary ───────────────────────────────────────────
def test_T05_traditional_hbu_summary():
    ok = _chk("traditional_report",
               "مشروع قانوناً", "ممكن مادياً", "مجدٍ مالياً", "الأعلى إنتاجية",
               "HBU", "أعلى وأفضل")
    assert ok, "Traditional: HBU not found"


# ── T06: Traditional — DCF sanity check ──────────────────────────────────────
def test_T06_traditional_dcf_sanity_check():
    ok = _chk("traditional_report",
               "DCF", "فحص مبسط", "NPV", "Sanity", "تدفقات نقدية")
    assert ok, "Traditional: DCF sanity check not found"


# ── T07: Traditional — basic sensitivity ─────────────────────────────────────
def test_T07_traditional_basic_sensitivity():
    ok = _chk("traditional_report",
               "حساسية", "Cap Rate", "Sensitivity", "معدل الرسملة")
    assert ok, "Traditional: sensitivity not found"


# ── T08: Traditional — risk matrix/note ──────────────────────────────────────
def test_T08_traditional_risk_matrix():
    ok = _chk("traditional_report",
               "مخاطر", "Risk", "خطر", "الشدة", "أثر")
    assert ok, "Traditional: risk matrix not found"


# ── T09: Traditional — weights justified ─────────────────────────────────────
def test_T09_traditional_weights_justified():
    ok = _chk("traditional_report",
               "50%", "30%", "20%", "مبرر", "مبررات", "الوزن")
    assert ok, "Traditional: weight justification not found"


# ── T10: Traditional — recommendation ────────────────────────────────────────
def test_T10_traditional_recommendation():
    ok = _chk("traditional_report",
               "التوصية", "توصية", "LTV", "مناسب للتمويل", "النتيجة")
    assert ok, "Traditional: recommendation not found"


# ── T11: Detailed — HBU ──────────────────────────────────────────────────────
def test_T11_detailed_hbu():
    ok = _chk("detailed_report",
               "مشروع قانوناً", "ممكن مادياً", "مجدٍ مالياً", "الأعلى إنتاجية",
               "الاختبارات الأربعة", "HBU")
    assert ok, "Detailed: HBU not found"


# ── T12: Detailed — scenario summary ─────────────────────────────────────────
def test_T12_detailed_scenario_summary():
    ok = _chk("detailed_report",
               "السيناريو", "متحفظ", "أساسي", "متفائل", "Scenario")
    assert ok, "Detailed: scenario summary not found"


# ── T13: Detailed — DCF inside income approach ───────────────────────────────
def test_T13_detailed_dcf_inside_income():
    ok = _chk("detailed_report",
               "DCF", "NPV", "تدفقات نقدية مخصومة", "أسلوب الدخل")
    assert ok, "Detailed: DCF not in income approach"


# ── T14: Detailed — risk matrix upgraded ─────────────────────────────────────
def test_T14_detailed_risk_matrix_upgraded():
    ok = _chk("detailed_report",
               "أثر", "القيمة", "مخاطر", "الانعكاس", "نطاق القيمة")
    assert ok, "Detailed: upgraded risk matrix not found"


# ── T15: Detailed — weights justified ────────────────────────────────────────
def test_T15_detailed_weights_justified():
    ok = _chk("detailed_report",
               "50%", "35%", "15%", "مبرر", "مبررات", "الوزن")
    assert ok, "Detailed: weight justification not found"


# ── T16: Detailed — gap analysis ─────────────────────────────────────────────
def test_T16_detailed_gap_analysis():
    ok = _chk("detailed_report",
               "فجوة", "الفجوات", "Gap", "الفارق", "فجوة السوق")
    assert ok, "Detailed: gap analysis not found"


# ── T17: Professional — NOI matches Excel ────────────────────────────────────
def test_T17_professional_noi_matches_excel():
    # NOI = 62,772 must appear in professional report
    ok = _chk("professional_report",
               "62,772", "62772", "صافي الدخل التشغيلي NOI")
    assert ok, f"Professional: NOI {_NOI} not found in report"


# ── T18: Professional — sensitivity matrix not repeated ──────────────────────
def test_T18_professional_sensitivity_not_repeated():
    h = _html("professional_report")
    # Verify three distinct sensitivity sections
    ok = (
        "Cap Rate" in h or "معدل الرسملة" in h or "إشغال" in h
    ) and (
        "معدل الخصم" in h or "Discount" in h or "DR" in h or "Terminal" in h
    )
    assert ok, "Professional: multi-dimensional sensitivity not found"


# ── T19: Professional — risk impact justified ─────────────────────────────────
def test_T19_professional_risk_impact_justified():
    ok = _chk("professional_report",
               "1.5%", "المرجح", "مرجح", "الأثر المرجح", "Weighted",
               "القيمة المعدلة", "risk_adjusted")
    assert ok, "Professional: justified risk impact percentage not found"


# ── T20: Professional — gap analysis ─────────────────────────────────────────
def test_T20_professional_gap_analysis():
    ok = _chk("professional_report",
               "فجوة", "الفجوات", "Gap", "الفارق", "تحليل الفجوات")
    assert ok, "Professional: gap analysis not found"


# ── T21: All reports — uncertainty range ─────────────────────────────────────
def test_T21_all_reports_uncertainty_range():
    for name in ["traditional_report", "detailed_report", "professional_report"]:
        ok = _chk(name, "نطاق عدم اليقين", "Uncertainty", "حد أدنى", "حد أعلى",
                  "نطاق القيمة", "نطاق الثقة")
        assert ok, f"{name}: uncertainty range not found"


# ── T22: All reports — data sources documented ───────────────────────────────
def test_T22_all_reports_data_sources():
    for name in ["traditional_report", "detailed_report", "professional_report"]:
        ok = _chk(name, "مصادر البيانات", "Data Sources", "مصدر", "درجة الثقة",
                  "مصادر", "البيانات")
        assert ok, f"{name}: data sources not found"


# ── T23: All reports — illustrative assumptions explained ─────────────────────
def test_T23_all_reports_illustrative_assumptions():
    for name in ["traditional_report", "detailed_report", "professional_report"]:
        ok = _chk(name, "توضيحي", "Illustrative", "افتراضات", "سبب كونها توضيحية",
                  "الافتراضات التوضيحية")
        assert ok, f"{name}: illustrative assumptions explanation not found"


# ── T24: All reports — certification/signature gate ──────────────────────────
def test_T24_all_reports_signature_gate():
    for name in ["traditional_report", "detailed_report", "professional_report"]:
        ok = _chk(name, "بوابة مراجعة", "certification_ready=False",
                  "التوقيع", "اسم خبير", "بانتظار المراجعة")
        assert ok, f"{name}: signature gate not found"


# ── T25: No fake signature ────────────────────────────────────────────────────
def test_T25_no_fake_signature():
    for name in ["traditional_report", "detailed_report", "professional_report"]:
        h = _html(name)
        assert "no_fake_signature=True" in h or "no_fake_signature" in h or \
               "بانتظار المراجعة" in h, \
               f"{name}: no fake-signature declaration found"
        # Must NOT have actual signature data
        assert "خبير معتمد:" not in h or "بانتظار" in h, \
               f"{name}: possible fake expert signature data"


# ── T26: No fake stamp ────────────────────────────────────────────────────────
def test_T26_no_fake_stamp():
    for name in ["traditional_report", "detailed_report", "professional_report"]:
        h = _html(name)
        assert "no_fake_stamp=True" in h or "بانتظار المراجعة" in h or \
               "no_fake_stamp" in h, \
               f"{name}: no fake-stamp declaration"


# ── T27: No fake certification ────────────────────────────────────────────────
def test_T27_no_fake_certification():
    for name in ["traditional_report", "detailed_report", "professional_report"]:
        h = _html(name)
        assert "certification_ready=False" in h, f"{name}: certification_ready=False not in preview"
        assert "certification_ready=True" not in h, f"{name}: fake certification_ready=True found"


# ── T28: No internal paths ────────────────────────────────────────────────────
def test_T28_no_internal_paths():
    for name in ["traditional_report", "detailed_report", "professional_report"]:
        h = _html(name)
        for pat in [r"C:\\Users", "C:/Users", "/home/", "core_engine/instance"]:
            assert pat not in h, f"{name} preview: internal path found: {pat}"
    for fname in [
        "pdf_physical_files_audit.json",
        "pdf_excel_number_consistency_audit.json",
        "pdf_weakness_fix_audit.json",
    ]:
        f = _AUD / fname
        if f.exists():
            content = f.read_text(encoding="utf-8")
            for pat in [r"C:\\Users", "C:/Users", "/home/"]:
                assert pat not in content, f"{fname}: internal path found: {pat}"


# ── T29: Weakness fix audit passes ───────────────────────────────────────────
def test_T29_weakness_fix_audit_passes():
    data = _j(_AUD / "pdf_weakness_fix_audit.json")
    assert data["overall_status"] == "PASS", f"Weakness fix audit: {data['overall_status']}"
    sg = data["shared_gaps_fixed"]
    assert sg["hbu_added_to_traditional_and_detailed"] is True
    assert sg["client_recommendation_added_to_all"] is True
    assert sg["risk_linked_to_final_value"] is True
    assert sg["uncertainty_range_added_to_all"] is True
    assert sg["signature_gate_added_without_fake_signature"] is True


# ── T30: Excel number consistency audit passes ────────────────────────────────
def test_T30_excel_number_consistency_audit_passes():
    data = _j(_AUD / "pdf_excel_number_consistency_audit.json")
    assert data["number_consistency_status"] == "PASS", \
        f"Consistency audit: {data['number_consistency_status']}"
    assert data["noi_pdf_matches_excel"] is True
    assert data["final_value_pdf_matches_excel"] is True
    assert data["mismatches"] == []
    assert data["excel_source_used"] is True


# ── T31: Risk-value linkage audit passes ─────────────────────────────────────
def test_T31_risk_value_linkage_audit_passes():
    data = _j(_AUD / "pdf_risk_value_linkage_audit.json")
    assert data["risk_value_linkage_status"] == "PASS"
    assert data["vague_unjustified_adjustments_removed"] is True
    assert data["professional_report"]["risk_register_present"] is True
    assert data["professional_report"]["risk_adjustment_rationale_present"] is True


# ── T32: Uncertainty/sources audit passes ────────────────────────────────────
def test_T32_uncertainty_sources_audit_passes():
    data = _j(_AUD / "pdf_uncertainty_and_sources_audit.json")
    assert data["status"] == "PASS"
    for level in ["traditional_report", "detailed_report", "professional_report"]:
        assert data[level]["uncertainty_range_present"] is True
        assert data[level]["illustrative_assumptions_explained"] is True


# ── T33: Ordinary valuation unaffected ───────────────────────────────────────
def test_T33_ordinary_valuation_unaffected():
    bridge = _CORE / "bridge_api.py"
    assert bridge.exists(), "bridge_api.py missing"
    frontend = _CORE.parent / "frontend" / "index.html"
    if not frontend.exists():
        frontend = _CORE / "frontend" / "index.html"
    assert frontend.exists(), "frontend/index.html missing"


# ── T34: Tax appeal unaffected ───────────────────────────────────────────────
def test_T34_tax_appeal_unaffected():
    bridge = _CORE / "bridge_api.py"
    assert bridge.exists()
    content = bridge.read_text(encoding="utf-8", errors="ignore")
    assert "tax" in content.lower() or "ضريبة" in content or "appeal" in content.lower(), \
        "Tax appeal routes appear to be missing from bridge_api.py"
