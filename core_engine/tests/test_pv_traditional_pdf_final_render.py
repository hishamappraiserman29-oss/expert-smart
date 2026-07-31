"""test_pv_traditional_pdf_final_render.py — Traditional PDF Final Render Gate.

Verifies that the Traditional tier PDF was generated via Playwright/Chromium,
contains all 36 logical sections, passes all governance checks, and that no
Playwright-related test is skipped.

Run:
    .venv/Scripts/python.exe -m pytest core_engine/tests/test_pv_traditional_pdf_final_render.py -q
"""
from __future__ import annotations

import importlib.metadata
import json
import pathlib
import sys

import pytest

ROOT  = pathlib.Path(__file__).parent.parent.parent
CORE  = ROOT / "core_engine"
GATE  = CORE / "instance" / "manual_review_outputs" / \
        "professional_valuation_traditional_final_render_gate"
PDF   = GATE / "actual_file" / "FINAL_TRADITIONAL_REPORT.pdf"
AUDITS = GATE / "audits"
VISUAL_INDEX = GATE / "visual_index" / "OPEN_FINAL_TRADITIONAL_REPORT_REVIEW.html"

BATCH_START = "2026-07-13T14:19:26Z"  # ISO-8601 UTC

# 36 required logical parent-level section IDs
REQUIRED_SECTION_IDS = [
    "sec-cover", "sec-avm", "sec-comparables", "sec-land",
    "sec-boq", "sec-depreciation", "sec-cost-value", "sec-dcf",
    "sec-assumptions", "sec-kpi", "sec-reconciliation", "sec-caprate",
    "sec-advisory", "sec-nextdocs", "sec-datasources", "sec-hbu",
    "sec-swot", "sec-depr-doc", "sec-certrisk", "sec-roadmap",
    "sec-landsources", "sec-qdrant", "sec-governance", "sec-cv",
    "sec-sig-review", "sec-riskmap", "sec-avm-status", "sec-breakeven",
    "sec-compliance", "sec-income-cap-dcf", "sec-adj-support",
    "sec-assumptions-table", "sec-legal", "sec-esg", "sec-confidence",
    "sec-final-recon", "sec-rent-recon", "sec-fee", "sec-recommendation",
    "sec-general-conditions", "sec-signature",
]

REQUIRED_PHRASES = [
    "تقرير آلي استرشادي — غير معتمد رسميًا",
    "مسودة غير معتمدة",
    "غير معتمد",
    "لا يصدر تقرير معتمد إلا بعد مراجعة وتوقيع خبير تقييم مرخص",
    "بانتظار التوقيع الرسمي من مقيم عقاري مرخص",
]

FORBIDDEN = [
    "fake_stamp_created=True",
    "fake_license_created=True",
    "fake_valuer_created=True",
    "fake_production_data_created=True",
    "CERTIFIED_ISSUED",
    "تم الاعتماد",
]

SIM = "محاكاة داخلية/QA — غير معتمدة"

SAMPLE_DATA = {
    "report_title": "تقرير تقييم عقاري آلي — مبسط (Traditional)",
    "property_address": "شارع الجمهورية، القاهرة الجديدة، مصر",
    "property_type": "شقة سكنية", "area_sqm": 180, "floor": 5,
    "age_years": 8, "condition": "جيد جداً",
    "valuation_purpose": "بيع وشراء", "valuation_basis": "القيمة السوقية العادلة",
    "inspection_date": "2026-07-13", "report_date": "2026-07-13",
    "report_ref": "FINAL-TRAD-2026-001", "currency": "م.ج",
    "final_value": 3_200_000, "market_value": 3_200_000, "land_value": 1_800_000,
    "building_value": 1_100_000, "dcf_value": 3_100_000, "cost_approach_value": 2_900_000,
    "value_per_sqm": 17_778, "confidence_low": 2_950_000, "confidence_high": 3_450_000,
    "confidence_score": 74, "discount_rate": 12.5, "growth_rate": 3.5, "cap_rate_exit": 7.2,
    "land_area": 240, "land_price_sqm": 7_500, "land_method": SIM,
    "physical_depreciation": 12, "functional_depreciation": 3, "total_depreciation": 15,
    "hbu_current": "سكني", "hbu_optimal": "سكني مع إمكانية التكثيف",
    "hbu_legal": "مسموح", "hbu_physical": "ممكن", "hbu_financial": "مجدٍ", "hbu_productivity": "متوسط",
    "recommendation": "يُنصح باستكمال الوثائق. القيمة التأشيرية 3,200,000 م.ج. — غير معتمدة.",
    "avm_results": [{"method": SIM, "value": 3_220_000, "r2": 0.88, "note": SIM}],
    "comparables": [{"id": 1, "address": "شارع المعز", "area": 175, "price": 3_150_000,
                     "price_sqm": 18_000, "adj_total": -2, "adj_value": 3_087_000,
                     "date": "2026-04", "note": SIM}],
    "boq_items": [{"item": "هيكل خرساني", "unit": "م²", "qty": 180,
                   "unit_price": 3_800, "total": 684_000}],
    "dcf_years": [{"year": 1, "rent": 144_000, "vacancy": 5, "noi": 136_800,
                   "discount": 12.5, "pv": 121_600}],
    "terminal_value": 2_200_000,
    "cap_rate_models": [{"model": "بناء الأسعار", "rate": 7.8, "note": SIM}],
    "swot": {"strengths": ["موقع متميز"], "weaknesses": ["عمر متوسط"],
             "opportunities": ["تطوير المنطقة"], "threats": ["تقلبات السوق"]},
    "required_docs": ["صك الملكية", "رخصة البناء"],
    "missing_docs": ["رخصة البناء"],
    "cert_risks": ["وثائق مفقودة"],
    "roadmap_steps": [{"step": "استكمال الوثائق", "status": "معلق"}],
    "annual_noi": 136_800, "cap_rate_used": 7.2,
    "market_weight": "40%", "cost_weight": "25%", "dcf_weight": "35%",
}


# ── Environment ───────────────────────────────────────────────────────────

def test_R01_correct_venv_used():
    """Project .venv Python is used (not a global install)."""
    assert "expert_smart1" in sys.executable.lower() or \
           ".venv" in sys.executable.lower(), \
        f"Expected project .venv, got: {sys.executable}"


def test_R02_playwright_imports():
    """playwright.sync_api is importable."""
    from playwright.sync_api import sync_playwright  # noqa: F401


def test_R03_chromium_available():
    """Chromium executable exists on disk."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = pathlib.Path(p.chromium.executable_path)
        assert br.exists(), f"Chromium binary not found: {br}"


def test_R04_jinja2_imports():
    """Jinja2 is importable and version >= 3.1."""
    import jinja2
    major, minor = [int(x) for x in jinja2.__version__.split(".")[:2]]
    assert (major, minor) >= (3, 1), f"Jinja2 too old: {jinja2.__version__}"


# ── PDF file existence & freshness ───────────────────────────────────────

def test_R05_final_pdf_exists():
    """FINAL_TRADITIONAL_REPORT.pdf exists in actual_file/."""
    assert PDF.exists(), f"Final PDF missing: {PDF}"


def test_R06_pdf_generated_after_batch_start():
    """PDF modification time is after the batch start timestamp."""
    import datetime
    mtime = datetime.datetime.utcfromtimestamp(PDF.stat().st_mtime)
    batch_start = datetime.datetime.fromisoformat(BATCH_START.rstrip("Z"))
    assert mtime > batch_start, f"PDF mtime {mtime} not after batch start {batch_start}"


# ── Renderer verification ─────────────────────────────────────────────────

def test_R07_playwright_renderer_used():
    """Generation audit confirms Playwright/Chromium renderer."""
    audit = json.loads((AUDITS / "04_fresh_traditional_pdf_generation.json").read_text(encoding="utf-8"))
    assert audit.get("playwright_used") is True
    assert audit.get("fpdf_used") is False


def test_R08_fpdf_not_used():
    """fpdf2 is never imported in the PDF builder module (comment 'No FPDF' is allowed)."""
    builder = (CORE / "reports" / "pv_three_tier_pdf_builder.py").read_text(encoding="utf-8")
    # Only flag actual import statements, not the 'No FPDF' disclaimer comment
    assert "import fpdf" not in builder.lower(), "fpdf imported in builder — forbidden"
    assert "from fpdf" not in builder.lower(), "fpdf imported in builder — forbidden"


# ── PDF validity ──────────────────────────────────────────────────────────

def test_R09_pdf_opens_successfully():
    """PyMuPDF can open the PDF without errors."""
    import fitz
    doc = fitz.open(str(PDF))
    assert doc.page_count > 0
    doc.close()


def test_R10_actual_page_count_from_pdf():
    """PDF has at least 15 pages (target ≥ 16)."""
    import fitz
    doc = fitz.open(str(PDF))
    count = doc.page_count
    doc.close()
    assert count >= 15, f"Too few pages: {count}"


# ── PNG rendering ─────────────────────────────────────────────────────────

def test_R11_every_pdf_page_has_png():
    """Every PDF page has a corresponding PNG in page_pngs/."""
    import fitz
    doc = fitz.open(str(PDF))
    page_count = doc.page_count
    doc.close()
    png_dir = GATE / "page_pngs"
    for i in range(1, page_count + 1):
        png = png_dir / f"traditional_page_{i:03d}.png"
        assert png.exists(), f"Missing PNG for page {i}: {png}"


# ── Section inventory ─────────────────────────────────────────────────────

def test_R12_all_36_logical_sections_traceable():
    """All 36 required section IDs are present in the rendered HTML."""
    sys.path.insert(0, str(CORE / "reports"))
    sys.path.insert(0, str(CORE))
    from pv_three_tier_pdf_builder import build_traditional_html  # type: ignore
    html = build_traditional_html(SAMPLE_DATA)
    missing = [sid for sid in REQUIRED_SECTION_IDS if sid not in html]
    assert not missing, f"Missing section IDs in HTML: {missing}"


def test_R13_no_section_missing_id():
    """Section inventory audit reports missing_id_count = 0."""
    audit = json.loads((AUDITS / "05_traditional_36_section_inventory.json").read_text(encoding="utf-8"))
    assert audit["missing_id_count"] == 0, f"missing_id_count = {audit['missing_id_count']}"


# ── Visual defects ────────────────────────────────────────────────────────

def test_R14_no_critical_visual_defects():
    """Visual defects audit reports zero critical defects."""
    audit = json.loads((AUDITS / "08_traditional_visual_defects.json").read_text(encoding="utf-8"))
    assert audit["critical_count"] == 0, f"Critical defects: {audit['defects']}"


# ── Required disclaimers ──────────────────────────────────────────────────

def test_R15_required_disclaimers_in_html():
    """All 5 required governance phrases are present in the rendered HTML."""
    sys.path.insert(0, str(CORE / "reports"))
    sys.path.insert(0, str(CORE))
    from pv_three_tier_pdf_builder import build_traditional_html  # type: ignore
    html = build_traditional_html(SAMPLE_DATA)
    missing = [ph for ph in REQUIRED_PHRASES if ph not in html]
    assert not missing, f"Missing required phrases: {missing}"


# ── Signature & certification safety ─────────────────────────────────────

def test_R16_signature_gate_unsigned():
    """Signature gate is present and explicitly marked as pending/unsigned."""
    sys.path.insert(0, str(CORE / "reports"))
    sys.path.insert(0, str(CORE))
    from pv_three_tier_pdf_builder import build_traditional_html  # type: ignore
    html = build_traditional_html(SAMPLE_DATA)
    assert "sec-signature" in html, "sec-signature missing"
    assert "بانتظار التوقيع" in html, "Signature pending phrase missing"


def test_R17_no_automatic_certification():
    """No automatic certification claims in the HTML."""
    sys.path.insert(0, str(CORE / "reports"))
    sys.path.insert(0, str(CORE))
    from pv_three_tier_pdf_builder import build_traditional_html  # type: ignore
    html = build_traditional_html(SAMPLE_DATA)
    assert "تم الاعتماد" not in html
    assert "CERTIFIED_ISSUED" not in html


# ── Fake data forbidden ───────────────────────────────────────────────────

def test_R18_no_fake_licence_stamp_signature():
    """No fake stamps, licences, or valuer flags in the HTML."""
    sys.path.insert(0, str(CORE / "reports"))
    sys.path.insert(0, str(CORE))
    from pv_three_tier_pdf_builder import build_traditional_html  # type: ignore
    html = build_traditional_html(SAMPLE_DATA)
    for f in FORBIDDEN:
        assert f not in html, f"Forbidden string found: {f}"


# ── Internal paths ────────────────────────────────────────────────────────

def test_R19_no_internal_absolute_path():
    """No Windows absolute paths exposed in the HTML."""
    sys.path.insert(0, str(CORE / "reports"))
    sys.path.insert(0, str(CORE))
    from pv_three_tier_pdf_builder import build_traditional_html  # type: ignore
    html = build_traditional_html(SAMPLE_DATA)
    assert r"C:\Users\Lenovo" not in html
    assert "C:/Users/Lenovo" not in html


# ── No recalculation ─────────────────────────────────────────────────────

def test_R20_no_valuation_recalculation_in_template():
    """Template does not import valuation engine modules."""
    template_text = (CORE / "templates" / "pdf" / "pv_traditional_report.html").read_text(encoding="utf-8")
    forbidden_imports = ["from valuation", "import valuation", "bridge_api", "calculate_value"]
    for fi in forbidden_imports:
        assert fi not in template_text, f"Template imports valuation logic: {fi}"


# ── Visual index ──────────────────────────────────────────────────────────

def test_R21_visual_index_exists():
    """Visual index HTML exists and contains expected structure."""
    assert VISUAL_INDEX.exists(), f"Visual index missing: {VISUAL_INDEX}"
    content = VISUAL_INDEX.read_text(encoding="utf-8")
    assert "FINAL_TRADITIONAL_REPORT.pdf" in content
    assert "traditional_page_001.png" in content
