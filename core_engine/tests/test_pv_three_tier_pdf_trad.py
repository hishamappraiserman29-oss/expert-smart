"""test_pv_three_tier_pdf_trad.py — Batch 1: Traditional PDF tier tests.

Verifies:
- File existence (template + builder)
- HTML content: sections, disclaimers, watermark, RTL
- No Certified output, no fake stamps, no internal paths
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
TEMPLATE_PATH = CORE / "templates" / "pdf" / "pv_traditional_report.html"

EXISTING_PDF_TESTS = [
    CORE / "tests" / "test_pdf_engine.py",
    CORE / "tests" / "test_pdf_arabic.py",
    CORE / "tests" / "test_pdf_components.py",
    CORE / "tests" / "test_pdf_certification.py",
    CORE / "tests" / "test_pdf_main_report.py",
    CORE / "tests" / "test_report_pipeline.py",
]


def _sample_data() -> dict:
    return {
        "report_title": "تقرير تقييم آلي — اختبار QA",
        "property_address": "شارع التحرير، القاهرة",
        "property_type": "شقة سكنية",
        "area_sqm": 150,
        "floor": 3,
        "age_years": 10,
        "condition": "جيد",
        "valuation_purpose": "بيع",
        "valuation_basis": "القيمة السوقية",
        "inspection_date": "2026-07-11",
        "report_date": "2026-07-11",
        "report_ref": "TRAD-QA-001",
        "currency": "م.ج",
        "final_value": 2_500_000,
        "market_value": 2_500_000,
        "land_value": 1_500_000,
        "building_value": 800_000,
        "dcf_value": 2_450_000,
        "cost_approach_value": 2_300_000,
        "value_per_sqm": 16_667,
        "confidence_low": 2_300_000,
        "confidence_high": 2_700_000,
        "confidence_score": 72,
        "discount_rate": 12,
        "growth_rate": 3,
        "cap_rate_exit": 7,
        "land_area": 200,
        "land_price_sqm": 7_500,
        "land_method": "مقارنة الأراضي",
        "physical_depreciation": 15,
        "functional_depreciation": 5,
        "total_depreciation": 20,
        "hbu_current": "سكني",
        "hbu_optimal": "سكني مع إمكانية التكثيف",
        "hbu_legal": "مسموح",
        "hbu_physical": "ممكن",
        "hbu_financial": "مجدٍ",
        "hbu_productivity": "متوسط",
        "recommendation": (
            "يُنصح باستكمال الوثائق المطلوبة قبل الاعتماد الرسمي. "
            "القيمة المبدئية الإرشادية للعقار تُقدَّر بـ 2,500,000 م.ج."
        ),
        "avm_results": [
            {"method": "نموذج انحدار متعدد", "value": 2_520_000, "r2": 0.87, "note": "إرشادي"},
            {"method": "AVM متوسط السوق",    "value": 2_480_000, "r2": 0.85, "note": "إرشادي"},
        ],
        "comparables": [
            {"id": 1, "address": "شارع المعز",   "area": 145, "price": 2_450_000, "price_sqm": 16_897, "adj_total": -2, "adj_value": 2_401_000, "date": "2026-01", "note": "بيانات تمثيلية"},
            {"id": 2, "address": "شارع الهرم",   "area": 160, "price": 2_650_000, "price_sqm": 16_563, "adj_total":  3, "adj_value": 2_729_500, "date": "2026-02", "note": "بيانات تمثيلية"},
            {"id": 3, "address": "المهندسين",    "area": 140, "price": 2_350_000, "price_sqm": 16_786, "adj_total": -1, "adj_value": 2_326_500, "date": "2026-03", "note": "بيانات تمثيلية"},
            {"id": 4, "address": "الدقي",        "area": 155, "price": 2_580_000, "price_sqm": 16_645, "adj_total":  1, "adj_value": 2_605_800, "date": "2026-04", "note": "بيانات تمثيلية"},
        ],
        "boq_items": [
            {"item": "هيكل خرساني",   "unit": "م²", "qty": 150, "unit_price": 3_500, "total": 525_000},
            {"item": "تشطيبات",       "unit": "م²", "qty": 150, "unit_price": 1_200, "total": 180_000},
            {"item": "كهرباء وسباكة", "unit": "م²", "qty": 150, "unit_price":   800, "total": 120_000},
        ],
        "dcf_years": [
            {"year": 1, "rent": 120_000, "vacancy": 5, "noi": 114_000, "discount": 12, "pv": 101_786},
            {"year": 2, "rent": 123_600, "vacancy": 5, "noi": 117_420, "discount": 12, "pv":  93_700},
            {"year": 3, "rent": 127_308, "vacancy": 5, "noi": 120_943, "discount": 12, "pv":  86_080},
            {"year": 4, "rent": 131_127, "vacancy": 5, "noi": 124_671, "discount": 12, "pv":  79_220},
            {"year": 5, "rent": 135_061, "vacancy": 5, "noi": 128_308, "discount": 12, "pv":  72_810},
        ],
        "terminal_value": 1_800_000,
        "cap_rate_models": [
            {"model": "بناء الأسعار",  "rate": 7.5, "note": "إرشادي"},
            {"model": "مقارنة السوق",  "rate": 6.8, "note": "إرشادي"},
            {"model": "Elwood",        "rate": 7.2, "note": "إرشادي"},
            {"model": "Akerson",       "rate": 7.0, "note": "إرشادي"},
        ],
        "swot": {
            "strengths":     ["موقع متميز", "حالة جيدة"],
            "weaknesses":    ["عمر المبنى متوسط"],
            "opportunities": ["تطوير المنطقة"],
            "threats":       ["تقلبات السوق"],
        },
        "required_docs": ["صك الملكية", "مخطط معتمد", "شهادة إتمام"],
        "missing_docs":  ["مخطط معتمد"],
        "cert_risks":    ["وثائق ناقصة", "تقييم مبدئي فقط"],
        "roadmap_steps": [
            {"step": "استكمال الوثائق", "status": "معلق"},
            {"step": "فحص ميداني",      "status": "منجز"},
            {"step": "مراجعة خبير",     "status": "معلق"},
            {"step": "اعتماد رسمي",     "status": "مستقبلي"},
        ],
    }


# ── T01 / T02: File existence ─────────────────────────────────────────────

def test_t01_traditional_template_exists():
    assert TEMPLATE_PATH.exists(), f"Template missing: {TEMPLATE_PATH}"


def test_t02_builder_file_exists():
    assert BUILDER_PATH.exists(), f"Builder missing: {BUILDER_PATH}"


# ── HTML content fixture ──────────────────────────────────────────────────

@pytest.fixture(scope="module")
def html():
    sys.path.insert(0, str(CORE / "reports"))
    sys.path.insert(0, str(CORE))
    from pv_three_tier_pdf_builder import build_traditional_html  # type: ignore
    return build_traditional_html(_sample_data())


# ── T05–T06: Disclaimers and watermark ────────────────────────────────────

def test_t05_rtl_and_non_certified_disclaimer(html):
    assert "غير معتمد" in html, "Non-certified disclaimer missing"
    assert 'dir="rtl"' in html or "direction: rtl" in html, "RTL direction missing"


def test_t06_watermark_text(html):
    assert "مسودة غير معتمدة" in html, "Watermark 'مسودة غير معتمدة' missing"


# ── T07–T14: Section presence ─────────────────────────────────────────────

def test_t07_avm_section(html):
    assert "sec-avm" in html
    assert "AVM" in html


def test_t08_comparables_section(html):
    assert "sec-comparables" in html
    assert "مقارنة المبيعات" in html


def test_t09_boq_section(html):
    assert "sec-boq" in html
    assert "BOQ" in html


def test_t10_dcf_section(html):
    assert "sec-dcf" in html
    assert "DCF" in html


def test_t11_reconciliation_section(html):
    assert "sec-reconciliation" in html
    assert "مصالحة" in html


def test_t12_hbu_section(html):
    assert "sec-hbu" in html
    assert "HBU" in html


def test_t13_swot_section(html):
    assert "sec-swot" in html
    assert "SWOT" in html


def test_t14_certification_roadmap(html):
    assert "sec-roadmap" in html
    assert "خارطة طريق الاعتماد" in html


# ── T15–T17: Safety checks ────────────────────────────────────────────────

def test_t15_no_certified_claim(html):
    assert "غير معتمد" in html
    assert "تم الاعتماد" not in html
    assert "CERTIFIED_ISSUED" not in html


def test_t16_no_fake_signature_license_stamp(html):
    assert "fake_stamp_created=True"          not in html
    assert "fake_license_created=True"         not in html
    assert "fake_valuer_created=True"          not in html
    assert "fake_production_data_created=True" not in html


def test_t17_no_internal_absolute_paths(html):
    assert r"C:\Users\Lenovo" not in html
    assert "C:/Users/Lenovo" not in html


# ── T18: Existing PDF tests not disabled ─────────────────────────────────

def test_t18_existing_pdf_tests_not_disabled():
    for p in EXISTING_PDF_TESTS:
        assert p.exists(), f"Existing PDF test file missing/removed: {p.name}"


# ── T03 / T04: PDF generation (requires Playwright) ──────────────────────

def _playwright_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        return True
    except ImportError:
        return False


@pytest.mark.skipif(not _playwright_available(), reason="playwright not installed")
def test_t03_t04_traditional_pdf_generation():
    """End-to-end: generate PDF bytes via shared Playwright renderer."""
    sys.path.insert(0, str(CORE / "reports"))
    sys.path.insert(0, str(CORE))
    from pv_three_tier_pdf_builder import render_traditional_pdf  # type: ignore

    out = CORE / "instance" / "manual_review_outputs" / \
          "professional_valuation_pdf_reference_parity" / "pdf_outputs" / \
          "traditional_tier_qa_test.pdf"
    pdf_bytes = render_traditional_pdf(_sample_data(), output_path=out)

    assert isinstance(pdf_bytes, bytes), "render_traditional_pdf must return bytes"
    assert len(pdf_bytes) > 10_000, f"PDF suspiciously small: {len(pdf_bytes)} bytes"
    assert pdf_bytes[:4] == b"%PDF", "Output is not a valid PDF (no %PDF magic bytes)"
    assert out.exists(), f"PDF output file not written: {out}"
    assert out.stat().st_size > 10_000, "Written PDF file too small"
