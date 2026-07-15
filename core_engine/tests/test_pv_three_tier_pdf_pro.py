"""test_pv_three_tier_pdf_pro.py — Batch 3C: Professional PDF tier tests.

File-based, offline only. No network calls. No external services. No PDF parsing.
Content assertions read the Professional preview HTML written by Batch 3B smoke.
"""
from __future__ import annotations

import pathlib
import re

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HERE = pathlib.Path(__file__).parent                           # core_engine/tests/
_ROOT = _HERE.parent.parent                                     # project root
_CORE = _ROOT / "core_engine"

_TEMPLATE = _CORE / "templates" / "pdf" / "pv_professional_report.html"
_BUILDER  = _CORE / "reports" / "pv_three_tier_pdf_builder.py"

_MRO      = _CORE / "instance" / "manual_review_outputs" / \
            "professional_valuation_pdf_reference_parity"
_PDF_DIR  = _MRO / "pdf_outputs"
_PRV_DIR  = _MRO / "visual_previews"

_PRO_PDF  = _PDF_DIR / "professional_three_tier_report.pdf"
_PRO_PRV  = _PRV_DIR / "professional_three_tier_preview.html"
_TRAD_PDF = _PDF_DIR / "traditional_three_tier_report.pdf"
_DET_PDF  = _PDF_DIR / "detailed_three_tier_report.pdf"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_preview() -> str:
    assert _PRO_PRV.exists(), f"Professional preview not found: {_PRO_PRV}"
    return _PRO_PRV.read_text(encoding="utf-8")


def _builder_source() -> str:
    assert _BUILDER.exists(), f"Builder not found: {_BUILDER}"
    return _BUILDER.read_text(encoding="utf-8")


def _assert_contains(text: str, expected: str, label: str = "") -> None:
    tag = f" [{label}]" if label else ""
    assert expected in text, f"Expected string not found in preview{tag}: {expected!r}"


def _assert_not_contains(text: str, forbidden: str, label: str = "") -> None:
    tag = f" [{label}]" if label else ""
    assert forbidden not in text, f"Forbidden string found in preview{tag}: {forbidden!r}"


# ---------------------------------------------------------------------------
# 1-4 — File existence
# ---------------------------------------------------------------------------

def test_01_professional_template_exists():
    assert _TEMPLATE.exists(), f"Professional template missing: {_TEMPLATE}"


def test_02_builder_file_exists():
    assert _BUILDER.exists(), f"Builder file missing: {_BUILDER}"


def test_03_professional_pdf_exists_and_nonempty():
    assert _PRO_PDF.exists(), f"Professional PDF missing: {_PRO_PDF}"
    assert _PRO_PDF.stat().st_size > 1024, "Professional PDF is empty or too small"


def test_04_professional_preview_exists():
    assert _PRO_PRV.exists(), f"Professional preview missing: {_PRO_PRV}"


# ---------------------------------------------------------------------------
# 5-6 — Regression: prior tier artifacts still present
# ---------------------------------------------------------------------------

def test_05_traditional_pdf_artifact_exists():
    assert _TRAD_PDF.exists(), (
        f"Traditional PDF artifact missing (regression): {_TRAD_PDF}"
    )


def test_06_detailed_pdf_artifact_exists():
    assert _DET_PDF.exists(), (
        f"Detailed PDF artifact missing (regression): {_DET_PDF}"
    )


# ---------------------------------------------------------------------------
# 7-9 — Mandatory governance texts in preview
# ---------------------------------------------------------------------------

def test_07_preview_contains_noncertified_disclaimer():
    text = _read_preview()
    _assert_contains(text, "غير معتمد رسميًا", "non-certified disclaimer")


def test_08_preview_contains_watermark():
    text = _read_preview()
    _assert_contains(text, "مسودة غير معتمدة", "watermark text")


def test_09_preview_contains_professional_header():
    text = _read_preview()
    _assert_contains(text, "تقرير تقييم آلي احترافي", "professional header")


# ---------------------------------------------------------------------------
# 10-16 — Professional-tier-specific sections
# ---------------------------------------------------------------------------

def test_10_preview_contains_table_of_contents():
    text = _read_preview()
    _assert_contains(text, 'id="sec-toc"', "table of contents section")


def test_11_preview_contains_executive_dashboard():
    text = _read_preview()
    _assert_contains(text, 'id="sec-exec-dashboard"', "executive dashboard section")


def test_12_preview_contains_scope_of_work():
    text = _read_preview()
    _assert_contains(text, "نطاق العمل", "scope of work title")
    _assert_contains(text, 'id="sec-scope-of-work"', "scope of work section ID")


def test_13_preview_contains_compliance_statement():
    text = _read_preview()
    _assert_contains(text, "بيان الامتثال", "compliance statement title")
    _assert_contains(text, 'id="sec-compliance"', "compliance section ID")


def test_14_preview_contains_professional_disclosures():
    text = _read_preview()
    _assert_contains(text, "الإفصاحات المهنية", "professional disclosures title")
    _assert_contains(text, 'id="sec-disclosures"', "disclosures section ID")


def test_15_preview_contains_certification_readiness():
    text = _read_preview()
    _assert_contains(text, 'id="sec-cert-readiness"', "cert readiness section ID")


def test_16_preview_contains_certification_traffic_light():
    text = _read_preview()
    _assert_contains(text, 'id="sec-cert-traffic"', "cert traffic-light section ID")


# ---------------------------------------------------------------------------
# 17-21 — Data quality, land approach, cost approach sections
# ---------------------------------------------------------------------------

def test_17_preview_contains_source_registry_and_data_quality():
    text = _read_preview()
    _assert_contains(text, 'id="sec-sources"', "sources section ID")
    _assert_contains(text, 'id="sec-data-quality"', "data quality section ID")


def test_18_preview_contains_land_adjustment_matrix():
    text = _read_preview()
    _assert_contains(text, 'id="sec-land-adj"', "land adjustment section ID")


def test_19_preview_contains_land_extraction_method():
    text = _read_preview()
    _assert_contains(text, 'id="sec-land-extraction"', "land extraction section ID")


def test_20_preview_contains_land_reconciliation():
    text = _read_preview()
    _assert_contains(text, 'id="sec-land-recon"', "land reconciliation section ID")


def test_21_preview_contains_cost_approach():
    text = _read_preview()
    _assert_contains(text, 'id="sec-cost"', "cost approach section ID")


# ---------------------------------------------------------------------------
# 22-27 — Building costs, income, DCF, NPV, sensitivity
# ---------------------------------------------------------------------------

def test_22_preview_contains_building_cost_breakdown():
    text = _read_preview()
    _assert_contains(text, 'id="sec-boq"', "BOQ section ID")


def test_23_preview_contains_income_capitalization():
    text = _read_preview()
    _assert_contains(text, 'id="sec-income-cap"', "income capitalization section ID")


def test_24_preview_contains_dcf():
    text = _read_preview()
    _assert_contains(text, 'id="sec-dcf"', "DCF section ID")


def test_25_preview_contains_npv_irr_or_missing_data_note():
    text = _read_preview()
    # Section must exist; data may show NA sentinel if not supplied
    assert 'id="sec-npv-irr"' in text or "غير متاح ضمن بيانات الطلب" in text, (
        "sec-npv-irr section missing and no NA sentinel found"
    )
    _assert_contains(text, 'id="sec-npv-irr"', "NPV/IRR section ID")


def test_26_preview_contains_sensitivity_and_scenarios():
    text = _read_preview()
    _assert_contains(text, 'id="sec-sensitivity"', "sensitivity section ID")
    _assert_contains(text, 'id="sec-scenarios"', "scenarios section ID")


def test_27_preview_contains_risk_register_and_matrix():
    text = _read_preview()
    _assert_contains(text, 'id="sec-risk-register"', "risk register section ID")
    _assert_contains(text, 'id="sec-risk-matrix"', "risk matrix section ID")


# ---------------------------------------------------------------------------
# 28-31 — ESG, HBU/SWOT, weighted reconciliation, recommendation
# ---------------------------------------------------------------------------

def test_28_preview_contains_esg_section_or_missing_data_note():
    text = _read_preview()
    assert 'id="sec-esg"' in text or "غير متاح ضمن بيانات الطلب" in text, (
        "sec-esg section missing and no NA sentinel found"
    )
    _assert_contains(text, 'id="sec-esg"', "ESG section ID")


def test_29_preview_contains_hbu_and_swot():
    text = _read_preview()
    _assert_contains(text, 'id="sec-hbu"', "HBU section ID")
    _assert_contains(text, 'id="sec-swot"', "SWOT section ID")


def test_30_preview_contains_weighted_reconciliation_matrix():
    text = _read_preview()
    _assert_contains(text, 'id="sec-weighted-recon"', "weighted reconciliation section ID")


def test_31_preview_contains_final_recommendation():
    text = _read_preview()
    _assert_contains(text, 'id="sec-recommendation"', "recommendation section ID")


# ---------------------------------------------------------------------------
# 32 — Signature / advisory gate
# ---------------------------------------------------------------------------

def test_32_preview_contains_expert_signature_gate():
    text = _read_preview()
    _assert_contains(
        text,
        "بانتظار التوقيع الرسمي من مقيم عقاري مرخص",
        "expert signature gate text",
    )


# ---------------------------------------------------------------------------
# 33-36 — Governance negatives
# ---------------------------------------------------------------------------

def test_33_preview_has_no_automatic_certified_claim():
    text = _read_preview()
    # Advisory string "لا Certified آلي" must be present
    _assert_contains(text, "لا Certified", "no-auto-cert advisory present")
    # Must not contain a standalone auto-approval marker
    _assert_not_contains(text, "✓ معتمد", "auto-cert approval marker")


def test_34_preview_has_no_fake_signature_license_stamp():
    text = _read_preview()
    _assert_not_contains(text, "stamp.png", "fake stamp image")
    _assert_not_contains(text, "signature.png", "fake signature image")
    # Signature slot must remain in pending/placeholder form
    _assert_contains(
        text,
        "بانتظار التوقيع الرسمي",
        "pending signature gate present",
    )


def test_35_preview_has_no_internal_absolute_paths():
    text = _read_preview()
    windows_paths = re.findall(r"[A-Za-z]:\\[^\s\"<>]{5,}", text)
    assert not windows_paths, (
        f"Internal absolute paths found in preview: {windows_paths[:3]}"
    )


def test_36_preview_has_no_excel_workbook_path():
    text = _read_preview()
    for pattern in (".xlsx", ".xlsm", "workbook", "Workbook"):
        _assert_not_contains(text, pattern, f"Excel reference ({pattern!r})")


# ---------------------------------------------------------------------------
# 37-40 — Builder source checks
# ---------------------------------------------------------------------------

def test_37_builder_does_not_import_fpdf_for_professional_path():
    src = _builder_source()
    import_lines = [
        ln.strip() for ln in src.splitlines()
        if ln.strip().startswith("import fpdf") or ln.strip().startswith("from fpdf")
    ]
    assert not import_lines, f"FPDF import found in builder: {import_lines}"


def test_38_builder_still_has_traditional_generation():
    src = _builder_source()
    assert "build_traditional_html" in src, "build_traditional_html missing from builder"
    assert "render_traditional_pdf" in src, "render_traditional_pdf missing from builder"


def test_39_builder_still_has_detailed_generation():
    src = _builder_source()
    assert "build_detailed_html" in src, "build_detailed_html missing from builder"
    assert "render_detailed_pdf" in src, "render_detailed_pdf missing from builder"


def test_40_builder_has_professional_generation():
    src = _builder_source()
    assert "build_professional_html" in src, "build_professional_html missing from builder"
    assert "render_professional_pdf" in src, "render_professional_pdf missing from builder"
