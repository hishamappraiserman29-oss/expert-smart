# -*- coding: utf-8 -*-
"""test_pv_professional_pdf_final_render.py — Professional PDF Final Render Gate.

Verifies that the Professional tier PDF was generated via Playwright/Chromium,
contains all 51 logical sections, passes all governance checks, cross-tier
inheritance passes, and no test is skipped.

Run:
    .venv/Scripts/python.exe -m pytest core_engine/tests/test_pv_professional_pdf_final_render.py -q
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT   = pathlib.Path(__file__).parent.parent.parent
CORE   = ROOT / "core_engine"
GATE   = CORE / "instance" / "manual_review_outputs" / \
         "professional_valuation_professional_final_render_gate"
PDF    = GATE / "actual_file" / "FINAL_PROFESSIONAL_REPORT.pdf"
AUDITS = GATE / "audits"
VISUAL_INDEX = GATE / "visual_index" / "OPEN_FINAL_PROFESSIONAL_REPORT_REVIEW.html"

BATCH_START = "2026-07-13T00:00:00Z"

REQUIRED_SECTION_IDS = [
    "sec-cover", "sec-advisory", "sec-toc", "sec-exec-dashboard", "sec-scope-of-work",
    "sec-facts", "sec-location", "sec-sources", "sec-data-quality", "sec-market-evidence",
    "sec-avm", "sec-multiple-regression", "sec-comparables", "sec-sales-adj",
    "sec-land-sales", "sec-land-adj", "sec-land-extraction", "sec-land-residual",
    "sec-land-recon", "sec-cost", "sec-boq", "sec-rcn", "sec-direct-costs",
    "sec-indirect-costs", "sec-depreciation", "sec-site-improvements",
    "sec-income-cap", "sec-rent-comps", "sec-sale-rent", "sec-dcf", "sec-npv-irr",
    "sec-sensitivity", "sec-scenarios", "sec-risk-register", "sec-risk-matrix",
    "sec-esg", "sec-hbu", "sec-swot", "sec-standards-readiness", "sec-compliance",
    "sec-disclosures", "sec-cert-readiness", "sec-cert-traffic", "sec-weighted-recon",
    "sec-reconciliation", "sec-conclusion", "sec-recommendation", "sec-nextdocs",
    "sec-appendices", "sec-qdrant", "sec-signature",
]

REQUIRED_PHRASES = [
    "تقرير تقييم آلي احترافي — غير معتمد رسميًا",
    "تقرير آلي استرشادي — غير معتمد رسميًا",
    "مسودة غير معتمدة",
    "لا يصدر تقرير معتمد إلا بعد مراجعة وتوقيع خبير تقييم مرخص",
    "بانتظار التوقيع الرسمي من مقيم عقاري مرخص",
]

FORBIDDEN = [
    "fake_stamp_created=True",
    "fake_license_created=True",
    "fake_valuer_created=True",
    "CERTIFIED_ISSUED",
    "تم الاعتماد",
]

SIM = "محاكاة داخلية/QA — غير معتمدة"

SAMPLE_DATA = {
    "report_title":      "تقرير تقييم عقاري آلي — احترافي (Professional)",
    "firm_name":         "Expert Smart | PropTech Platform",
    "property_address":  "شارع الجمهورية، القاهرة الجديدة، مصر",
    "property_type":     "شقة سكنية",
    "area_sqm":          180,
    "floor":             5,
    "age_years":         8,
    "condition":         "جيد جداً",
    "valuation_purpose": "تمويل عقاري",
    "valuation_basis":   "القيمة السوقية العادلة",
    "inspection_date":   "2026-07-13",
    "report_date":       "2026-07-13",
    "report_ref":        "FINAL-PRO-2026-001",
    "currency":          "م.ج",
    "final_value":       3_200_000,
    "market_value":      3_200_000,
    "land_value":        1_800_000,
    "building_value":    1_100_000,
    "dcf_value":         3_100_000,
    "cost_approach_value": 2_900_000,
    "value_per_sqm":     17_778,
    "confidence_low":    2_950_000,
    "confidence_high":   3_450_000,
    "confidence_score":  74,
    "discount_rate":     12.5,
    "growth_rate":       3.5,
    "cap_rate_exit":     7.2,
    "land_area":         240,
    "land_price_sqm":    7_500,
    "physical_depreciation":   12,
    "functional_depreciation":  3,
    "total_depreciation":      15,
    "hbu_current":    "سكني",
    "hbu_optimal":    "سكني مع إمكانية التكثيف",
    "hbu_legal":      "مسموح",
    "hbu_physical":   "ممكن",
    "hbu_financial":  "مجدٍ",
    "hbu_productivity": "متوسط",
    "recommendation": "يُنصح باستكمال الوثائق. القيمة التأشيرية 3,200,000 م.ج. — غير معتمدة.",
    "annual_noi":     136_800,
    "cap_rate_used":  7.2,
    "market_weight":  "40%",
    "cost_weight":    "25%",
    "dcf_weight":     "35%",
    "npv":            285_000,
    "irr":            "14.8",
    "payback_years":  "7.2",
    "terminal_value": 2_200_000,
    "avm_results": [{"method": SIM, "value": 3_220_000, "r2": 0.88, "note": SIM}],
    "comparables": [
        {"id": 1, "address": "شارع المعز", "area": 175, "price": 3_150_000,
         "price_sqm": 18_000, "adj_total": -2, "adj_value": 3_087_000,
         "date": "2026-04", "note": SIM},
    ],
    "boq_items": [
        {"item": "هيكل خرساني", "unit": "م²", "qty": 180,
         "unit_price": 3_800, "total": 684_000},
    ],
    "dcf_years": [
        {"year": 1, "rent": 144_000, "vacancy": 5, "noi": 136_800,
         "discount": 12.5, "pv": 121_600},
    ],
    "required_docs": ["صك الملكية", "رخصة البناء"],
    "missing_docs":  ["رخصة البناء"],
    "cert_risks":    ["وثائق مفقودة"],
    "swot": {
        "strengths":     ["موقع متميز"],
        "weaknesses":    ["عمر متوسط"],
        "opportunities": ["تطوير المنطقة"],
        "threats":       ["تقلبات السوق"],
    },
    "direct_costs": {
        "structural": 684_000, "concrete": 200_000,
        "windows": 80_000,    "doors": 60_000,
        "subtotal": 1_024_000,
    },
    "indirect_costs": {
        "design_fees": 45_000, "permits": 25_000,
        "financing": 60_000,   "developer_profit": 80_000,
        "subtotal": 210_000,
    },
    "land_extraction": {
        "total_value": 3_200_000, "rcn": 1_280_000,
        "depreciation": 15,       "building_dep_value": 1_088_000,
        "extracted_land_value": 2_112_000, "land_price_sqm": 8_800,
    },
    "land_residual": {
        "gdv": 4_500_000,        "build_cost": 2_100_000,
        "developer_margin": 15,  "residual_land_value": 1_725_000,
    },
    "compliance_statement": {
        "standards":    "IVS / RICS / TAQEEM — استرشادي — " + SIM,
        "limitations":  "تقرير آلي غير معتمد",
        "independence": "مستقل مؤسسياً — لا تعارض مصالح — " + SIM,
    },
    "disclosures": {
        "independence": "لا يوجد تعارض مصالح — إرشادي",
        "conflicts":    "لا تعارض — " + SIM,
        "data_sources": "بيانات تمثيلية — محاكاة داخلية",
        "caveats":      "غير مُوقَّع — غير معتمد — لا Certified آلي",
    },
}


# ── Environment ────────────────────────────────────────────────────────────────

def test_P01_correct_venv_used():
    """Project .venv Python is used (not a global install)."""
    assert "expert_smart1" in sys.executable.lower() or \
           ".venv" in sys.executable.lower(), \
        f"Expected project .venv, got: {sys.executable}"


def test_P02_playwright_imports():
    """playwright.sync_api is importable."""
    from playwright.sync_api import sync_playwright  # noqa: F401


def test_P03_chromium_available():
    """Chromium executable exists on disk."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = pathlib.Path(p.chromium.executable_path)
        assert br.exists(), f"Chromium binary not found: {br}"


def test_P04_jinja2_imports():
    """Jinja2 is importable and version >= 3.1."""
    import jinja2
    major, minor = [int(x) for x in jinja2.__version__.split(".")[:2]]
    assert (major, minor) >= (3, 1), f"Jinja2 too old: {jinja2.__version__}"


# ── PDF existence & freshness ──────────────────────────────────────────────────

def test_P05_final_pdf_exists():
    """FINAL_PROFESSIONAL_REPORT.pdf exists in actual_file/."""
    assert PDF.exists(), f"Final PDF missing: {PDF}"


def test_P06_pdf_generated_after_batch_start():
    """PDF modification time is after the batch start timestamp."""
    import datetime
    mtime = datetime.datetime.utcfromtimestamp(PDF.stat().st_mtime)
    batch_start = datetime.datetime.fromisoformat(BATCH_START.rstrip("Z"))
    assert mtime > batch_start, f"PDF mtime {mtime} not after batch start {batch_start}"


# ── Renderer verification ──────────────────────────────────────────────────────

def test_P07_playwright_renderer_used():
    """Generation audit confirms Playwright/Chromium renderer."""
    audit = json.loads((AUDITS / "04_fresh_professional_pdf_generation.json").read_text(encoding="utf-8"))
    assert audit.get("playwright_used") is True
    assert audit.get("fpdf_used") is False


def test_P08_fpdf_not_imported_in_builder():
    """fpdf2 is never imported in the PDF builder."""
    builder = (CORE / "reports" / "pv_three_tier_pdf_builder.py").read_text(encoding="utf-8")
    assert "import fpdf" not in builder.lower(), "fpdf imported in builder — forbidden"
    assert "from fpdf" not in builder.lower(), "fpdf imported in builder — forbidden"


# ── PDF validity ───────────────────────────────────────────────────────────────

def test_P09_pdf_opens_successfully():
    """PyMuPDF can open the PDF without errors."""
    import fitz
    doc = fitz.open(str(PDF))
    assert doc.page_count > 0
    doc.close()


def test_P10_actual_page_count_from_pdf():
    """PDF has at least 18 pages (Professional is richest tier)."""
    import fitz
    doc = fitz.open(str(PDF))
    count = doc.page_count
    doc.close()
    assert count >= 18, f"Too few pages: {count}"


# ── PNG rendering ──────────────────────────────────────────────────────────────

def test_P11_every_pdf_page_has_png():
    """Every PDF page has a corresponding PNG in page_pngs/."""
    import fitz
    doc = fitz.open(str(PDF))
    page_count = doc.page_count
    doc.close()
    png_dir = GATE / "page_pngs"
    for i in range(1, page_count + 1):
        png = png_dir / f"professional_page_{i:03d}.png"
        assert png.exists(), f"Missing PNG for page {i}: {png}"


# ── Section inventory ──────────────────────────────────────────────────────────

def test_P12_all_51_sections_traceable():
    """All 51 required section IDs are present in the rendered HTML."""
    sys.path.insert(0, str(CORE / "reports"))
    sys.path.insert(0, str(CORE))
    from pv_three_tier_pdf_builder import build_professional_html  # type: ignore
    html = build_professional_html(SAMPLE_DATA)
    missing = [sid for sid in REQUIRED_SECTION_IDS if sid not in html]
    assert not missing, f"Missing section IDs in HTML: {missing}"


def test_P13_no_section_missing_id():
    """Section inventory audit reports missing_id_count = 0."""
    audit = json.loads((AUDITS / "05_professional_section_inventory.json").read_text(encoding="utf-8"))
    assert audit["missing_id_count"] == 0, \
        f"missing_id_count = {audit['missing_id_count']}"


# ── Cross-tier inheritance ─────────────────────────────────────────────────────

def test_P14_cross_tier_inheritance_passes():
    """Cross-tier inheritance audit: all required features present."""
    audit = json.loads((AUDITS / "06_professional_cross_tier_inheritance.json").read_text(encoding="utf-8"))
    assert audit["all_pass"] is True, \
        f"Inheritance failures: {[m for m in audit['matrix'] if m['status'] != 'PASS']}"


# ── Professional-specific sections ────────────────────────────────────────────

def test_P15_premium_cover_exists():
    """Professional cover page is distinct (contains Professional Tier badge)."""
    sys.path.insert(0, str(CORE / "reports"))
    sys.path.insert(0, str(CORE))
    from pv_three_tier_pdf_builder import build_professional_html  # type: ignore
    html = build_professional_html(SAMPLE_DATA)
    assert "sec-cover" in html, "sec-cover missing"
    assert "Professional Tier" in html, "Professional Tier badge missing"


def test_P16_table_of_contents_exists():
    """Table of contents section is present and contains section references."""
    sys.path.insert(0, str(CORE / "reports"))
    sys.path.insert(0, str(CORE))
    from pv_three_tier_pdf_builder import build_professional_html  # type: ignore
    html = build_professional_html(SAMPLE_DATA)
    assert "sec-toc" in html, "sec-toc missing"
    assert "فهرس المحتويات" in html, "TOC title missing"


def test_P17_executive_dashboard_exists():
    """Executive dashboard section is present with value display."""
    sys.path.insert(0, str(CORE / "reports"))
    sys.path.insert(0, str(CORE))
    from pv_three_tier_pdf_builder import build_professional_html  # type: ignore
    html = build_professional_html(SAMPLE_DATA)
    assert "sec-exec-dashboard" in html, "sec-exec-dashboard missing"
    assert "لوحة التحكم التنفيذية" in html, "Executive dashboard title missing"


def test_P18_scope_of_work_exists():
    """Scope of work section is present."""
    sys.path.insert(0, str(CORE / "reports"))
    sys.path.insert(0, str(CORE))
    from pv_three_tier_pdf_builder import build_professional_html  # type: ignore
    html = build_professional_html(SAMPLE_DATA)
    assert "sec-scope-of-work" in html, "sec-scope-of-work missing"
    assert "نطاق العمل" in html, "Scope title missing"


def test_P19_standards_compliance_layer_exists():
    """Standards readiness and compliance sections are present."""
    sys.path.insert(0, str(CORE / "reports"))
    sys.path.insert(0, str(CORE))
    from pv_three_tier_pdf_builder import build_professional_html  # type: ignore
    html = build_professional_html(SAMPLE_DATA)
    assert "sec-standards-readiness" in html, "sec-standards-readiness missing"
    assert "sec-compliance" in html, "sec-compliance missing"


def test_P20_critical_blocker_layer_exists():
    """Certification readiness and traffic-light sections are present."""
    sys.path.insert(0, str(CORE / "reports"))
    sys.path.insert(0, str(CORE))
    from pv_three_tier_pdf_builder import build_professional_html  # type: ignore
    html = build_professional_html(SAMPLE_DATA)
    assert "sec-cert-readiness" in html, "sec-cert-readiness missing"
    assert "sec-cert-traffic" in html, "sec-cert-traffic missing"


def test_P21_action_item_layer_exists():
    """Required documents / next-steps action section is present."""
    sys.path.insert(0, str(CORE / "reports"))
    sys.path.insert(0, str(CORE))
    from pv_three_tier_pdf_builder import build_professional_html  # type: ignore
    html = build_professional_html(SAMPLE_DATA)
    assert "sec-nextdocs" in html, "sec-nextdocs missing"


def test_P22_weighted_reconciliation_exists():
    """Weighted reconciliation matrix section is present."""
    sys.path.insert(0, str(CORE / "reports"))
    sys.path.insert(0, str(CORE))
    from pv_three_tier_pdf_builder import build_professional_html  # type: ignore
    html = build_professional_html(SAMPLE_DATA)
    assert "sec-weighted-recon" in html, "sec-weighted-recon missing"
    assert "مصفوفة المصالحة الموزونة" in html, "Weighted recon title missing"


def test_P23_certification_readiness_exists():
    """Certification readiness checklist is populated in the HTML."""
    sys.path.insert(0, str(CORE / "reports"))
    sys.path.insert(0, str(CORE))
    from pv_three_tier_pdf_builder import build_professional_html  # type: ignore
    html = build_professional_html(SAMPLE_DATA)
    assert "sec-cert-readiness" in html
    assert "جاهزية الاعتماد" in html


# ── Signature gate ─────────────────────────────────────────────────────────────

def test_P24_signature_gate_unsigned():
    """Signature gate is present and marked as pending/unsigned."""
    sys.path.insert(0, str(CORE / "reports"))
    sys.path.insert(0, str(CORE))
    from pv_three_tier_pdf_builder import build_professional_html  # type: ignore
    html = build_professional_html(SAMPLE_DATA)
    assert "sec-signature" in html, "sec-signature missing"
    assert "بانتظار التوقيع" in html, "Signature pending phrase missing"


# ── Required disclaimers ───────────────────────────────────────────────────────

def test_P25_required_disclaimers_present():
    """All 5 required governance phrases are present in the rendered HTML."""
    sys.path.insert(0, str(CORE / "reports"))
    sys.path.insert(0, str(CORE))
    from pv_three_tier_pdf_builder import build_professional_html  # type: ignore
    html = build_professional_html(SAMPLE_DATA)
    missing = [ph for ph in REQUIRED_PHRASES if ph not in html]
    assert not missing, f"Missing required phrases: {missing}"


# ── No automatic certification ─────────────────────────────────────────────────

def test_P26_no_automatic_certification():
    """No automatic certification claims in the HTML."""
    sys.path.insert(0, str(CORE / "reports"))
    sys.path.insert(0, str(CORE))
    from pv_three_tier_pdf_builder import build_professional_html  # type: ignore
    html = build_professional_html(SAMPLE_DATA)
    assert "تم الاعتماد" not in html
    assert "CERTIFIED_ISSUED" not in html


# ── Fake data forbidden ────────────────────────────────────────────────────────

def test_P27_no_fake_licence_stamp_signature():
    """No fake stamps, licences, or valuer flags in the HTML."""
    sys.path.insert(0, str(CORE / "reports"))
    sys.path.insert(0, str(CORE))
    from pv_three_tier_pdf_builder import build_professional_html  # type: ignore
    html = build_professional_html(SAMPLE_DATA)
    for f in FORBIDDEN:
        assert f not in html, f"Forbidden string found: {f}"


# ── Internal paths forbidden ───────────────────────────────────────────────────

def test_P28_no_internal_absolute_path():
    """No Windows absolute paths exposed in the HTML."""
    sys.path.insert(0, str(CORE / "reports"))
    sys.path.insert(0, str(CORE))
    from pv_three_tier_pdf_builder import build_professional_html  # type: ignore
    html = build_professional_html(SAMPLE_DATA)
    assert r"C:\Users\Lenovo" not in html
    assert "C:/Users/Lenovo" not in html


# ── No critical visual defects ────────────────────────────────────────────────

def test_P29_no_critical_visual_defects():
    """Visual defects audit reports zero critical defects."""
    audit = json.loads((AUDITS / "09_professional_visual_defects.json").read_text(encoding="utf-8"))
    assert audit["critical_count"] == 0, f"Critical defects: {audit.get('defects', [])}"


# ── Visual index ───────────────────────────────────────────────────────────────

def test_P30_visual_index_exists():
    """Visual index HTML exists and contains expected structure."""
    assert VISUAL_INDEX.exists(), f"Visual index missing: {VISUAL_INDEX}"
    content = VISUAL_INDEX.read_text(encoding="utf-8")
    assert "FINAL_PROFESSIONAL_REPORT.pdf" in content
    assert "professional_page_001.png" in content
