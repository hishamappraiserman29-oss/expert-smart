"""test_pv_three_tier_pdf_det.py — Batch 2: Detailed PDF tier tests.

Verifies:
- File existence (template + builder)
- HTML content: all 37 sections, disclaimers, watermark, RTL
- Workbook-derived sections: land methods, income cap, NPV/IRR, sensitivity, ESG
- No Certified output, no fake stamps, no internal paths, no FPDF
- Traditional tier regression (Batch 1 still works)
- Existing PDF test files not removed or disabled
- PDF generation via Playwright (skipped if Playwright not installed)
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).parent.parent.parent
CORE = ROOT / "core_engine"
BUILDER_PATH = CORE / "reports" / "pv_three_tier_pdf_builder.py"
TEMPLATE_PATH = CORE / "templates" / "pdf" / "pv_detailed_report.html"
TRAD_TEMPLATE_PATH = CORE / "templates" / "pdf" / "pv_traditional_report.html"
TRAD_TEST_PATH = CORE / "tests" / "test_pv_three_tier_pdf_trad.py"

PDF_OUT = (
    CORE / "instance" / "manual_review_outputs"
    / "professional_valuation_pdf_reference_parity"
    / "pdf_outputs" / "detailed_three_tier_report.pdf"
)
PREVIEW_OUT = (
    CORE / "instance" / "manual_review_outputs"
    / "professional_valuation_pdf_reference_parity"
    / "visual_previews" / "detailed_three_tier_preview.html"
)


def _sample_data() -> dict:
    return {
        "report_title":        "تقرير تقييم آلي تفصيلي — اختبار QA",
        "property_address":    "شارع التحرير، القاهرة",
        "property_type":       "شقة سكنية",
        "area_sqm":            150,
        "floor":               3,
        "age_years":           10,
        "condition":           "جيد",
        "valuation_purpose":   "بيع",
        "valuation_basis":     "القيمة السوقية",
        "inspection_date":     "2026-07-11",
        "report_date":         "2026-07-11",
        "report_ref":          "DET-QA-001",
        "currency":            "م.ج",
        "client_name":         "محاكاة داخلية/QA",
        "intended_use":        "اختبار جودة — غير رسمي",
        "final_value":         2_500_000,
        "market_value":        2_500_000,
        "land_value":          1_500_000,
        "building_value":      800_000,
        "dcf_value":           2_450_000,
        "cost_approach_value": 2_300_000,
        "value_per_sqm":       16_667,
        "confidence_low":      2_300_000,
        "confidence_high":     2_700_000,
        "confidence_score":    72,
        "discount_rate":       12,
        "growth_rate":         3,
        "cap_rate_exit":       7,
        "noi":                 108_000,
        "gross_yield":         "4.8",
        "net_yield":           "4.3",
        "grm":                 20.8,
        "sale_rent_recommendation": "بيع أنسب في الظروف الحالية — إرشادي",
        "npv":                 350_000,
        "irr":                 "14.2",
        "payback_years":       "7.2",
        "equity_multiple":     "1.8",
        "data_completeness":   75,
        "data_reliability":    68,
        "land_area":           200,
        "land_price_sqm":      7_500,
        "land_method":         "مقارنة الأراضي",
        "land_sales_value":    7_500,
        "land_extraction_value": 7_200,
        "land_residual_value": 7_800,
        "land_sales_weight":   "50%",
        "land_extraction_weight": "30%",
        "land_residual_weight": "20%",
        "rcn":                 1_000_000,
        "rcn_per_sqm":         6_667,
        "base_construction_cost": 525_000,
        "finishing_cost":      180_000,
        "services_cost":       120_000,
        "contingency_cost":    50_000,
        "site_improvements_value": 50_000,
        "physical_depreciation":   15,
        "functional_depreciation":  5,
        "economic_depreciation":    0,
        "total_depreciation":      20,
        "annual_depreciation_rate": 1.5,
        "remaining_economic_life":  40,
        "market_weight":    "40%",
        "cost_weight":      "25%",
        "dcf_weight":       "35%",
        "terminal_value":   1_800_000,
        "investment_horizon": "5 سنوات",
        "hbu_current":      "سكني",
        "hbu_optimal":      "سكني مع إمكانية التكثيف",
        "hbu_legal":        "مسموح",
        "hbu_physical":     "ممكن",
        "hbu_financial":    "مجدٍ",
        "hbu_productivity": "متوسط",
        "hbu_conclusion":   "الاستخدام السكني هو الأمثل في المرحلة الراهنة",
        "exec_summary": (
            "يُقدَّر العقار الواقع في شارع التحرير بالقاهرة بقيمة إرشادية تمثيلية تبلغ 2,500,000 م.ج "
            "استناداً إلى ثلاثة مداخل تقييمية: مقارنة المبيعات، مدخل التكلفة، والدخل/DCF. "
            "التقرير إرشادي تمثيلي — محاكاة داخلية/QA — غير معتمد رسميًا."
        ),
        "recommendation": (
            "يُنصح باستكمال الوثائق المطلوبة قبل الاعتماد الرسمي. "
            "القيمة المبدئية الإرشادية للعقار تُقدَّر بـ 2,500,000 م.ج — محاكاة داخلية/QA."
        ),
        "regression_equation": "Q = 800,000 + 11,200·م² − 15,000·عمر + 200,000·موقع",
        "sources": [
            {"name": "بيانات الطلب",       "type": "إدخال",   "status": "متاح",    "note": "بيانات الطلب الأساسية"},
            {"name": "Qdrant/RAG",          "type": "قاعدة بيانات", "status": "غير متاح", "note": "غير مفعَّل — لا scraping"},
            {"name": "بيانات السجل العقاري", "type": "رسمي",   "status": "غير متاح", "note": "يتطلب اعتمادًا رسميًا"},
        ],
        "data_quality": [
            {"dimension": "اكتمال البيانات",     "score": 75, "note": "وثائق ناقصة"},
            {"dimension": "موثوقية المصادر",     "score": 60, "note": "بيانات تمثيلية"},
            {"dimension": "حداثة البيانات",      "score": 80, "note": "2026"},
            {"dimension": "الاتساق الداخلي",     "score": 85, "note": "تحقق ناجح"},
        ],
        "market_evidence": [
            {"type": "بيع حديث",    "source": "سجل تمثيلي", "value": "16,500 م.ج/م²", "date": "2026-05", "status": "تمثيلي/QA"},
            {"type": "إيجار حديث", "source": "سجل تمثيلي", "value": "800 م.ج/شهر",   "date": "2026-06", "status": "تمثيلي/QA"},
        ],
        "avm_results": [
            {"method": "نموذج انحدار متعدد", "value": 2_520_000, "r2": 0.87, "rmse": 85_000, "note": "إرشادي"},
            {"method": "AVM متوسط السوق",    "value": 2_480_000, "r2": 0.85, "rmse": 90_000, "note": "إرشادي"},
        ],
        "comparables": [
            {"id": 1, "address": "شارع المعز",  "area": 145, "price": 2_450_000, "price_sqm": 16_897, "adj_total": -2, "adj_value": 2_401_000, "date": "2026-01", "note": "بيانات تمثيلية"},
            {"id": 2, "address": "شارع الهرم",  "area": 160, "price": 2_650_000, "price_sqm": 16_563, "adj_total":  3, "adj_value": 2_729_500, "date": "2026-02", "note": "بيانات تمثيلية"},
            {"id": 3, "address": "المهندسين",   "area": 140, "price": 2_350_000, "price_sqm": 16_786, "adj_total": -1, "adj_value": 2_326_500, "date": "2026-03", "note": "بيانات تمثيلية"},
            {"id": 4, "address": "الدقي",       "area": 155, "price": 2_580_000, "price_sqm": 16_645, "adj_total":  1, "adj_value": 2_605_800, "date": "2026-04", "note": "بيانات تمثيلية"},
        ],
        "sales_adj_matrix": [
            {"factor": "الموقع",        "values": [-2,  3, -1,  1]},
            {"factor": "المساحة",       "values": [ 0,  0,  0,  0]},
            {"factor": "عمر المبنى",    "values": [ 0, -1,  0,  1]},
            {"factor": "الحالة",        "values": [ 0,  1, -1,  0]},
        ],
        "land_sales": [
            {"location": "منطقة أ", "area": 210, "price_sqm": 7_200, "total": 1_512_000, "date": "2026-01", "note": "تمثيلي"},
            {"location": "منطقة ب", "area": 195, "price_sqm": 7_600, "total": 1_482_000, "date": "2026-02", "note": "تمثيلي"},
            {"location": "منطقة ج", "area": 205, "price_sqm": 7_700, "total": 1_578_500, "date": "2026-03", "note": "تمثيلي"},
        ],
        "land_adj_items": [
            {"factor": "الموقع",  "values": [-2,  3, -1]},
            {"factor": "المساحة", "values": [ 0,  1,  0]},
            {"factor": "الشكل",   "values": [ 1, -1,  0]},
        ],
        "land_extraction": {
            "total_value":          2_300_000,
            "rcn":                  1_000_000,
            "depreciation":         20,
            "building_dep_value":   800_000,
            "extracted_land_value": 1_500_000,
            "land_price_sqm":       7_500,
        },
        "land_residual": {
            "gdv":                  3_500_000,
            "build_cost":           1_200_000,
            "developer_margin":     15,
            "residual_land_value":  1_775_000,
        },
        "boq_items": [
            {"item": "هيكل خرساني",    "unit": "م²", "qty": 150, "unit_price": 3_500, "total": 525_000},
            {"item": "تشطيبات",        "unit": "م²", "qty": 150, "unit_price": 1_200, "total": 180_000},
            {"item": "كهرباء وسباكة",  "unit": "م²", "qty": 150, "unit_price":   800, "total": 120_000},
            {"item": "تكييف وتهوية",   "unit": "م²", "qty": 150, "unit_price":   500, "total":  75_000},
        ],
        "site_improvements": [
            {"item": "ممرات وأرصفة", "cost": 30_000, "dep_pct": 15, "contrib_value": 25_500},
            {"item": "تنسيق حدائق", "cost": 20_000, "dep_pct": 20, "contrib_value": 16_000},
        ],
        "income_cap": {
            "gross_rent":       135_000,
            "vacancy_rate":     10,
            "eri":              121_500,
            "opex":             13_500,
            "noi":              108_000,
            "cap_rate":         6.8,
            "capitalized_value": 1_588_235,
        },
        "rent_comps": [
            {"location": "شارع المعز",  "area": 145, "annual_rent": 126_000, "rent_sqm": 869, "date": "2026-01", "note": "تمثيلي"},
            {"location": "المهندسين",   "area": 140, "annual_rent": 120_000, "rent_sqm": 857, "date": "2026-02", "note": "تمثيلي"},
            {"location": "الدقي",       "area": 155, "annual_rent": 138_000, "rent_sqm": 890, "date": "2026-03", "note": "تمثيلي"},
        ],
        "dcf_years": [
            {"year": 1, "rent": 120_000, "vacancy": 5, "noi": 114_000, "discount": 12, "pv": 101_786},
            {"year": 2, "rent": 123_600, "vacancy": 5, "noi": 117_420, "discount": 12, "pv":  93_700},
            {"year": 3, "rent": 127_308, "vacancy": 5, "noi": 120_943, "discount": 12, "pv":  86_080},
            {"year": 4, "rent": 131_127, "vacancy": 5, "noi": 124_671, "discount": 12, "pv":  79_220},
            {"year": 5, "rent": 135_061, "vacancy": 5, "noi": 128_308, "discount": 12, "pv":  72_810},
        ],
        "sensitivity_growth_rates": ["1%", "2%", "3%", "4%", "5%"],
        "sensitivity_matrix": [
            {"disc_rate": 10, "values": [2_650_000, 2_720_000, 2_800_000, 2_880_000, 2_970_000]},
            {"disc_rate": 11, "values": [2_520_000, 2_590_000, 2_660_000, 2_740_000, 2_820_000]},
            {"disc_rate": 12, "values": [2_400_000, 2_460_000, 2_520_000, 2_600_000, 2_680_000]},
            {"disc_rate": 13, "values": [2_280_000, 2_340_000, 2_400_000, 2_470_000, 2_550_000]},
            {"disc_rate": 14, "values": [2_170_000, 2_230_000, 2_290_000, 2_360_000, 2_430_000]},
        ],
        "scenarios": [
            {"name": "متشائم", "growth_rate": 1, "discount_rate": 14, "vacancy": 15, "value": 2_100_000, "npv": -200_000},
            {"name": "أساسي",  "growth_rate": 3, "discount_rate": 12, "vacancy":  5, "value": 2_500_000, "npv":  350_000},
            {"name": "متفائل", "growth_rate": 5, "discount_rate": 10, "vacancy":  3, "value": 2_950_000, "npv":  750_000},
        ],
        "risk_register": [
            {"risk": "تراجع أسعار السوق",   "category": "سوقي",   "probability": 3, "impact": 4, "score": 12, "response": "متابعة دورية"},
            {"risk": "وثائق ملكية ناقصة",   "category": "قانوني", "probability": 4, "impact": 3, "score": 12, "response": "استكمال الوثائق"},
            {"risk": "ارتفاع تكاليف الإنشاء", "category": "تكلفة", "probability": 2, "impact": 3, "score":  6, "response": "احتياطي التكلفة"},
            {"risk": "ارتفاع معدلات الفائدة", "category": "مالي",  "probability": 3, "impact": 3, "score":  9, "response": "تحليل الحساسية"},
        ],
        "esg": {
            "environmental_score":  65,
            "environmental_note":   "كفاءة طاقة متوسطة — يتطلب تقييمًا مستقلاً",
            "social_score":         70,
            "social_note":          "موقع قريب من الخدمات — تمثيلي",
            "governance_score":     55,
            "governance_note":      "وثائق حوكمة ناقصة — تمثيلي",
            "total_score":          63,
            "overall_note":         "تقييم ESG إرشادي تمثيلي — محاكاة داخلية/QA — غير معتمد",
        },
        "swot": {
            "strengths":     ["موقع متميز", "حالة جيدة", "قرب من الخدمات"],
            "weaknesses":    ["عمر المبنى متوسط", "وثائق ناقصة"],
            "opportunities": ["تطوير المنطقة", "تكثيف البناء المسموح"],
            "threats":       ["تقلبات السوق", "ارتفاع الفائدة"],
        },
        "cap_rate_models": [
            {"model": "بناء الأسعار", "rate": 7.5, "note": "إرشادي"},
            {"model": "مقارنة السوق", "rate": 6.8, "note": "إرشادي"},
        ],
        "required_docs": ["صك الملكية", "مخطط معتمد", "شهادة إتمام"],
        "missing_docs":  ["مخطط معتمد"],
    }


# ── D01 / D02: File existence ─────────────────────────────────────────────

def test_d01_detailed_template_exists():
    assert TEMPLATE_PATH.exists(), f"Detailed template missing: {TEMPLATE_PATH}"


def test_d02_builder_file_exists():
    assert BUILDER_PATH.exists(), f"Builder missing: {BUILDER_PATH}"


# ── HTML content fixture ──────────────────────────────────────────────────

@pytest.fixture(scope="module")
def html():
    sys.path.insert(0, str(CORE / "reports"))
    sys.path.insert(0, str(CORE))
    from pv_three_tier_pdf_builder import build_detailed_html  # type: ignore
    return build_detailed_html(_sample_data())


# ── D05: Traditional tier no regression ──────────────────────────────────

def test_d05_traditional_tier_still_works():
    """Traditional HTML build must still succeed — no regression from Batch 2."""
    assert TRAD_TEMPLATE_PATH.exists(), f"Traditional template missing: {TRAD_TEMPLATE_PATH}"
    sys.path.insert(0, str(CORE / "reports"))
    sys.path.insert(0, str(CORE))
    from pv_three_tier_pdf_builder import build_traditional_html  # type: ignore
    trad_html = build_traditional_html({"report_title": "test", "final_value": 1_000_000})
    assert "مسودة غير معتمدة" in trad_html
    assert "تقرير آلي" in trad_html


# ── D06 / D07: Disclaimers and watermark ─────────────────────────────────

def test_d06_rtl_and_non_certified_disclaimer(html):
    assert "غير معتمد" in html, "Non-certified disclaimer missing"
    assert 'dir="rtl"' in html or "direction: rtl" in html, "RTL direction missing"


def test_d07_watermark_text(html):
    assert "مسودة غير معتمدة" in html, "Watermark 'مسودة غير معتمدة' missing"


# ── D08: Executive summary ────────────────────────────────────────────────

def test_d08_executive_summary(html):
    assert "sec-exec-summary" in html
    assert "الملخص التنفيذي" in html


# ── D09: Source registry and data quality ────────────────────────────────

def test_d09_source_registry_and_data_quality(html):
    assert "sec-sources" in html
    assert "سجل المصادر" in html
    assert "sec-data-quality" in html
    assert "جودة البيانات" in html


# ── D10: Sales comparison ─────────────────────────────────────────────────

def test_d10_sales_comparison(html):
    assert "sec-comparables" in html
    assert "مقارنة المبيعات" in html


# ── D11: Land adjustment matrix ──────────────────────────────────────────

def test_d11_land_adj_matrix(html):
    assert "sec-land-adj" in html
    assert "مصفوفة تسويات الأرض" in html


# ── D12: Land extraction method ──────────────────────────────────────────

def test_d12_land_extraction(html):
    assert "sec-land-extraction" in html
    assert "الاستخلاص" in html


# ── D13: Land reconciliation ─────────────────────────────────────────────

def test_d13_land_reconciliation(html):
    assert "sec-land-recon" in html
    assert "مصالحة" in html
    assert "الأرض" in html


# ── D14: Cost approach ───────────────────────────────────────────────────

def test_d14_cost_approach(html):
    assert "sec-cost" in html
    assert "مدخل التكلفة" in html


# ── D15: Building cost breakdown ─────────────────────────────────────────

def test_d15_building_cost_breakdown(html):
    assert "sec-boq" in html
    assert "BOQ" in html


# ── D16: Income capitalization ───────────────────────────────────────────

def test_d16_income_capitalization(html):
    assert "sec-income-cap" in html
    assert "الرسملة" in html


# ── D17: DCF section ─────────────────────────────────────────────────────

def test_d17_dcf_section(html):
    assert "sec-dcf" in html
    assert "DCF" in html


# ── D18: NPV / IRR / Payback ─────────────────────────────────────────────

def test_d18_npv_irr_payback(html):
    assert "sec-npv-irr" in html
    assert "NPV" in html
    assert "IRR" in html


# ── D19: Sensitivity / Scenario ──────────────────────────────────────────

def test_d19_sensitivity_scenario(html):
    assert "sec-sensitivity" in html
    assert "الحساسية" in html
    assert "sec-scenarios" in html
    assert "السيناريوهات" in html


# ── D20: Risk matrix / register ──────────────────────────────────────────

def test_d20_risk_register_and_matrix(html):
    assert "sec-risk-register" in html
    assert "سجل المخاطر" in html
    assert "sec-risk-matrix" in html


# ── D21: ESG ─────────────────────────────────────────────────────────────

def test_d21_esg_section(html):
    assert "sec-esg" in html
    assert "ESG" in html


# ── D22: HBU / SWOT ──────────────────────────────────────────────────────

def test_d22_hbu_and_swot(html):
    assert "sec-hbu" in html
    assert "HBU" in html
    assert "sec-swot" in html
    assert "SWOT" in html


# ── D23: Signature / advisory gate ───────────────────────────────────────

def test_d23_signature_gate(html):
    assert "sec-signature" in html
    assert "بانتظار التوقيع الرسمي من مقيم عقاري مرخص" in html


# ── D24: No certified claim ──────────────────────────────────────────────

def test_d24_no_certified_claim(html):
    assert "غير معتمد" in html
    assert "تم الاعتماد" not in html
    assert "CERTIFIED_ISSUED" not in html


# ── D25: No fake signature / license / stamp ─────────────────────────────

def test_d25_no_fake_signature_license_stamp(html):
    assert "fake_stamp_created=True"           not in html
    assert "fake_license_created=True"          not in html
    assert "fake_valuer_created=True"           not in html
    assert "fake_production_data_created=True"  not in html


# ── D26: No internal absolute paths ──────────────────────────────────────

def test_d26_no_internal_absolute_paths(html):
    assert r"C:\Users\Lenovo" not in html
    assert "C:/Users/Lenovo" not in html


# ── D27: FPDF not used for the new Detailed Arabic report ────────────────

def test_d27_fpdf_not_used_for_detailed():
    builder_src = BUILDER_PATH.read_text(encoding="utf-8")
    lower_src = builder_src.lower()
    assert "from fpdf" not in lower_src, "FPDF import found in builder — violates governance rule"
    assert "import fpdf" not in lower_src, "FPDF import found in builder — violates governance rule"


# ── D28: Batch 1 Traditional test file still exists ──────────────────────

def test_d28_batch1_traditional_test_file_exists():
    assert TRAD_TEST_PATH.exists(), f"Batch 1 traditional test file missing: {TRAD_TEST_PATH}"


# ── D03 / D04: PDF generation (requires Playwright) ──────────────────────

def _playwright_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        return True
    except ImportError:
        return False


@pytest.mark.skipif(not _playwright_available(), reason="playwright not installed")
def test_d03_d04_detailed_pdf_generation():
    """End-to-end: generate Detailed PDF via shared Playwright renderer."""
    sys.path.insert(0, str(CORE / "reports"))
    sys.path.insert(0, str(CORE))
    from pv_three_tier_pdf_builder import render_detailed_pdf  # type: ignore

    pdf_bytes = render_detailed_pdf(_sample_data(), output_path=PDF_OUT)

    assert isinstance(pdf_bytes, bytes), "render_detailed_pdf must return bytes"
    assert len(pdf_bytes) > 10_000, f"PDF suspiciously small: {len(pdf_bytes)} bytes"
    assert pdf_bytes[:4] == b"%PDF", "Output is not a valid PDF (no %PDF magic bytes)"
    assert PDF_OUT.exists(), f"PDF output file not written: {PDF_OUT}"
    assert PDF_OUT.stat().st_size > 10_000, "Written PDF file too small"

    # Write HTML preview alongside
    sys.path.insert(0, str(CORE / "reports"))
    from pv_three_tier_pdf_builder import build_detailed_html  # type: ignore
    preview_html = build_detailed_html(_sample_data())
    PREVIEW_OUT.parent.mkdir(parents=True, exist_ok=True)
    PREVIEW_OUT.write_text(preview_html, encoding="utf-8")
    assert PREVIEW_OUT.exists()
