"""Backend tests for PDF Reference Parity — 26 tests"""
import pathlib, re
import pytest

try:
    import fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

BASE = (pathlib.Path(__file__).parent.parent
        / "instance" / "manual_review_outputs"
        / "professional_valuation_pdf_reference_parity")
PDF_DIR    = BASE / "pdf_outputs"
TRAD       = PDF_DIR / "traditional_reference_parity_report.pdf"
DET        = PDF_DIR / "detailed_reference_parity_report.pdf"
PROF       = PDF_DIR / "professional_reference_parity_report.pdf"
BLUEPRINT  = BASE / "audits" / "01_reference_pdf_inventory.json"
GAP_MATRIX = BASE / "audits" / "02_pdf_design_system_audit.json"
VIS_INDEX  = BASE / "visual_previews" / "OPEN_PDF_REFERENCE_PARITY_REVIEW.html"
SIG_FRAG   = "بانتظار"


def _text(path):
    if not HAS_FITZ or not path.exists():
        return ""
    doc = fitz.open(str(path))
    t = " ".join(p.get_text() for p in doc)
    doc.close()
    return t


def _has_sec(text, n):
    return f"§{n}" in text


# ── 1-3: PDF existence ─────────────────────────────────────────────────────
def test_01_traditional_pdf_exists():
    assert TRAD.exists()

def test_02_detailed_pdf_exists():
    assert DET.exists()

def test_03_professional_pdf_exists():
    assert PROF.exists()

# ── 4-5: non-empty ─────────────────────────────────────────────────────────
def test_04_traditional_pdf_non_empty():
    assert TRAD.exists() and TRAD.stat().st_size > 10_000

def test_05_detailed_pdf_non_empty():
    assert DET.exists() and DET.stat().st_size > 10_000

# ── 6-7: reference files ───────────────────────────────────────────────────
def test_06_reference_blueprint_exists():
    assert BLUEPRINT.exists()

def test_07_pdf_gap_matrix_exists():
    assert GAP_MATRIX.exists()

# ── 8: traditional ─────────────────────────────────────────────────────────
def test_08_traditional_contains_summary_valuation_sections():
    t = _text(TRAD)
    assert any(k in t for k in ["تكلف", "القيمة", "أرض"])

# ── 9-10: detailed ─────────────────────────────────────────────────────────
def test_09_detailed_contains_cost_approach():
    t = _text(DET)
    assert "تكلف" in t

def test_10_detailed_contains_land_reconciliation():
    t = _text(DET)
    assert any(k in t for k in ["توفيق", "مطابقة", "أرض"])

# ── 11-23: professional (§N markers) ───────────────────────────────────────
def test_11_professional_contains_toc():
    t = _text(PROF)
    assert _has_sec(t, 3) and "جدول" in t

def test_12_professional_contains_executive_dashboard():
    t = _text(PROF)
    assert _has_sec(t, 4)

def test_13_professional_contains_cost_approach():
    t = _text(PROF)
    assert _has_sec(t, 17)

def test_14_professional_contains_building_cost_breakdown():
    t = _text(PROF)
    assert _has_sec(t, 18)

def test_15_professional_contains_depreciation_analysis():
    t = _text(PROF)
    assert _has_sec(t, 22)

def test_16_professional_contains_land_sales_comparison():
    t = _text(PROF)
    assert _has_sec(t, 11)

def test_17_professional_contains_land_extraction_method():
    t = _text(PROF)
    assert _has_sec(t, 13)

def test_18_professional_contains_land_reconciliation():
    t = _text(PROF)
    assert _has_sec(t, 15)

def test_19_professional_contains_dcf_or_blocker():
    t = _text(PROF)
    assert any(k in t for k in ["DCF", "NPV", _has_sec(t, 30).__class__.__name__]) or _has_sec(t, 30)

def test_20_professional_contains_spatial_analysis():
    t = _text(PROF)
    assert _has_sec(t, 7)

def test_21_professional_contains_ann_section():
    t = _text(PROF)
    assert _has_sec(t, 34) and "ANN" in t

def test_22_professional_contains_risk_matrix():
    t = _text(PROF)
    assert _has_sec(t, 38)

def test_23_professional_contains_signature_gate():
    t = _text(PROF)
    assert _has_sec(t, 48) and SIG_FRAG in t

# ── 24: visual index ───────────────────────────────────────────────────────
def test_24_visual_index_exists():
    assert VIS_INDEX.exists()

# ── 25-26: no fake data / no internal paths ────────────────────────────────
def test_25_no_fake_signature():
    t = _text(PROF)
    assert "fake_signature_created=True" not in t

def test_26_no_internal_paths():
    t = _text(PROF)
    assert "C:\\Users\\Lenovo" not in t and "C:/Users/Lenovo" not in t
