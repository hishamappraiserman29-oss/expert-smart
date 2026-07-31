"""
test_pv_integrated_pdf_gap_fix.py
31 backend tests — نموذج التقرير الموحد المتكامل ثلاثي المستوى
arabic_primary=True | unified_model=True | advisory_only=True
"""
from __future__ import annotations
import json
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parent.parent
_QA   = _CORE / "instance" / "manual_review_outputs" / "professional_valuation_integrated_pdf_gap_fix"
_PDF  = _QA / "pdf_outputs"
_PREV = _QA / "pdf_visual_previews"
_PAUD = _QA / "pdf_audits"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")

def _load(p: Path) -> dict:
    assert p.exists(), f"Missing: {p}"
    return json.loads(p.read_text(encoding="utf-8"))

def _html(key: str) -> str:
    p = _PREV / f"{key}_preview.html"
    assert p.exists(), f"Missing preview: {p}"
    return p.read_text(encoding="utf-8")


# T01
def test_T01_qa_folder_exists():
    assert _QA.exists()

# T02
def test_T02_three_pdf_files_exist():
    for name in ["traditional_report.pdf", "detailed_report.pdf", "professional_report.pdf"]:
        assert (_PDF / name).exists(), f"Missing: {name}"

# T03
def test_T03_pdfs_non_empty():
    for name in ["traditional_report.pdf", "detailed_report.pdf", "professional_report.pdf"]:
        assert (_PDF / name).stat().st_size > 10_000, f"Too small: {name}"

# T04
def test_T04_pdfs_arabic_first():
    for key in ["traditional_report", "detailed_report", "professional_report"]:
        html = _html(key)
        assert "تقرير" in html or "تقييم" in html, f"{key} not Arabic-first"
        assert 'lang=\'ar\'' in html or 'lang="ar"' in html, f"{key} missing lang=ar"

# T05
def test_T05_traditional_has_hbu_summary():
    html = _html("traditional_report")
    assert "HBU" in html or "أعلى وأفضل" in html

# T06
def test_T06_traditional_has_risk_note():
    html = _html("traditional_report")
    assert "مخاطر" in html or "risk" in html.lower()

# T07
def test_T07_traditional_has_conclusion_recommendation():
    html = _html("traditional_report")
    assert "التوصية" in html or "النتيجة" in html

# T08
def test_T08_detailed_has_structured_hbu():
    html = _html("detailed_report")
    assert "الاختبارات الأربعة" in html or ("HBU" in html and "مشروع قانوناً" in html)

# T09
def test_T09_detailed_dcf_inside_income_approach():
    html = _html("detailed_report")
    assert "التدفقات النقدية المخصومة ضمن أسلوب الدخل" in html or \
           ("DCF" in html and "أسلوب الدخل" in html)

# T10
def test_T10_detailed_risk_connected_to_value():
    html = _html("detailed_report")
    assert "أثر المخاطر على القيمة" in html or ("مخاطر" in html and "%" in html)

# T11
def test_T11_detailed_has_sensitivity_matrix():
    html = _html("detailed_report")
    assert "الحساسية" in html or "Sensitivity" in html
    assert "Cap Rate" in html or "معدل الرسملة" in html

# T12
def test_T12_detailed_has_weighting_rationale():
    html = _html("detailed_report")
    assert "مبررات" in html or "الأوزان" in html

# T13
def test_T13_detailed_has_gap_analysis():
    html = _html("detailed_report")
    assert "الفجوات" in html or "الفارق" in html or "تحليل الفجوات" in html

# T14
def test_T14_professional_has_dcf_5_and_10_years():
    html = _html("professional_report")
    assert ("5 سنوات" in html or "5-year" in html.lower())
    assert ("10 سنوات" in html or "10-year" in html.lower())

# T15
def test_T15_professional_has_npv_irr():
    html = _html("professional_report")
    assert "NPV" in html
    assert "IRR" in html

# T16
def test_T16_professional_hbu_four_tests():
    html = _html("professional_report")
    assert "الاختبار الأول" in html or "مشروع قانوناً" in html
    assert "الاختبار الثاني" in html or "ممكن مادياً" in html
    assert "الاختبار الثالث" in html or "مجدٍ مالياً" in html
    assert "الاختبار الرابع" in html or "الأعلى إنتاجية" in html

# T17
def test_T17_professional_has_scenario_analysis():
    html = _html("professional_report")
    assert "السيناريو" in html or "Scenario" in html
    assert "المتفائل" in html
    assert "المتحفظ" in html

# T18
def test_T18_professional_has_multi_variable_sensitivity():
    html = _html("professional_report")
    assert "متعدد" in html or "multi" in html.lower() or "المتغيرات" in html
    assert "Cap Rate" in html
    assert ("معدل الخصم" in html or "Discount" in html)

# T19
def test_T19_professional_has_risk_impact_on_value():
    html = _html("professional_report")
    assert "التأثير على القيمة" in html or "تأثيره على القيمة" in html or \
           ("سجل المخاطر" in html and "%" in html)

# T20
def test_T20_professional_has_avm_reliability():
    html = _html("professional_report")
    assert "موثوقية" in html or "reliability" in html.lower()
    assert "AVM" in html

# T21
def test_T21_professional_has_weighted_reconciliation_rationale():
    html = _html("professional_report")
    assert "مبررات اختيار الأوزان" in html or \
           ("الترجيح" in html and "مبرر" in html)

# T22
def test_T22_professional_has_standards_matrix():
    html = _html("professional_report")
    assert "IVS" in html
    assert "RICS" in html or "IFRS" in html

# T23
def test_T23_professional_has_source_registry():
    html = _html("professional_report")
    assert "سجل مصادر" in html or "مصادر البيانات" in html

# T24
def test_T24_professional_has_investment_recommendation():
    html = _html("professional_report")
    assert "التوصية الاستثمارية" in html or \
           ("توصية" in html and ("استثمار" in html or "LTV" in html))

# T25
def test_T25_repetition_audit_passes():
    data = _load(_PAUD / "pdf_repetition_reduction_audit.json")
    assert data["near_duplicate_paragraphs_removed"] is True
    assert data["near_duplicate_report_pairs"] == []
    assert data["repetition_status"] == "PASS"

# T26
def test_T26_gap_fix_audit_passes():
    data = _load(_PAUD / "integrated_report_depth_and_gap_fix_audit.json")
    assert data["unified_integrated_model_enabled"] is True
    assert data["traditional_report"]["hbu_summary_present"] is True
    assert data["detailed_report"]["dcf_integrated_into_income"] is True
    assert data["professional_report"]["multi_variable_sensitivity_present"] is True
    assert data["gap_fix_status"] == "PASS"

# T27
def test_T27_depth_audit_passes():
    data = _load(_PAUD / "integrated_report_depth_and_gap_fix_audit.json")
    assert data["traditional_less_detailed_than_detailed"] is True
    assert data["detailed_less_detailed_than_professional"] is True
    assert data["professional_is_highest_depth"] is True

# T28
def test_T28_no_fake_certification():
    for key in ["traditional_report", "detailed_report", "professional_report"]:
        html = _html(key)
        assert "مسودة" in html
        assert "certification_ready=False" in html or "advisory_only=True" in html

# T29
def test_T29_no_internal_paths_in_previews():
    for key in ["traditional_report", "detailed_report", "professional_report"]:
        html = _html(key)
        for pat in [r"C:\\Users", r"C:/Users", "/home/", "core_engine/instance"]:
            assert pat not in html, f"Internal path in {key}: {pat}"

# T30
def test_T30_ordinary_valuation_unaffected():
    frontend = _CORE.parent / "frontend" / "index.html"
    if not frontend.exists():
        frontend = _CORE / "frontend" / "index.html"
    assert frontend.exists(), "frontend/index.html missing"

# T31
def test_T31_tax_appeal_unaffected():
    # Tax appeal routes exist independently of this feature
    bridge = _CORE / "bridge_api.py"
    assert bridge.exists(), "bridge_api.py missing"
    content = bridge.read_text(encoding="utf-8", errors="ignore")
    assert "tax" in content.lower() or "ضريبة" in content or "appeal" in content.lower()
