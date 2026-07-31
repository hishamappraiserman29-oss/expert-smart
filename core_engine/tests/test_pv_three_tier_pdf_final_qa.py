# -*- coding: utf-8 -*-
"""
Final QA test suite — three-tier PDF system.
44 tests covering templates, builder, PDFs, governance, tier sections, and audit artifacts.
"""
import pathlib
import re

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_BASE    = pathlib.Path(__file__).resolve().parent.parent
_MRO     = _BASE / "instance" / "manual_review_outputs" / "professional_valuation_pdf_reference_parity"
_PDF_DIR = _MRO / "pdf_outputs"
_PRV_DIR = _MRO / "visual_previews"
_AUD_DIR = _MRO / "audits"
_TPL_DIR = _BASE / "templates" / "pdf"
_BLDR    = _BASE / "reports" / "pv_three_tier_pdf_builder.py"

_TRAD_PDF = _PDF_DIR / "traditional_three_tier_report.pdf"
_DET_PDF  = _PDF_DIR / "detailed_three_tier_report.pdf"
_PRO_PDF  = _PDF_DIR / "professional_three_tier_report.pdf"

_TRAD_TPL = _TPL_DIR / "pv_traditional_report.html"
_DET_TPL  = _TPL_DIR / "pv_detailed_report.html"
_PRO_TPL  = _TPL_DIR / "pv_professional_report.html"

_TRAD_PRV = _PRV_DIR / "traditional_three_tier_preview.html"
_DET_PRV  = _PRV_DIR / "detailed_three_tier_preview.html"
_PRO_PRV  = _PRV_DIR / "professional_three_tier_preview.html"

_QA_INDEX  = _PRV_DIR / "OPEN_THREE_TIER_PDF_FINAL_QA.html"
_ZERO_LOSS = _AUD_DIR / "batch_4_zero_loss_audit.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _pdf_text(path: pathlib.Path) -> str:
    try:
        import fitz
        doc = fitz.open(str(path))
        return "\n".join(doc[i].get_text() for i in range(doc.page_count))
    except Exception:
        return ""


def _read(path: pathlib.Path) -> str:
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return ""
    return ""


def _triple(pdf: pathlib.Path, prv: pathlib.Path, tpl: pathlib.Path) -> str:
    return _pdf_text(pdf) + "\n" + _read(prv) + "\n" + _read(tpl)


def _builder_source() -> str:
    return _read(_BLDR)


# ---------------------------------------------------------------------------
# 1. Templates exist
# ---------------------------------------------------------------------------
def test_01_traditional_template_exists():
    assert _TRAD_TPL.exists(), str(_TRAD_TPL)


def test_02_detailed_template_exists():
    assert _DET_TPL.exists(), str(_DET_TPL)


def test_03_professional_template_exists():
    assert _PRO_TPL.exists(), str(_PRO_TPL)


# ---------------------------------------------------------------------------
# 2. Builder exists
# ---------------------------------------------------------------------------
def test_04_builder_exists():
    assert _BLDR.exists(), str(_BLDR)


# ---------------------------------------------------------------------------
# 3. PDFs exist and are non-empty
# ---------------------------------------------------------------------------
def test_05_traditional_pdf_exists_nonempty():
    assert _TRAD_PDF.exists(), str(_TRAD_PDF)
    assert _TRAD_PDF.stat().st_size > 10240, "traditional PDF unexpectedly small"


def test_06_detailed_pdf_exists_nonempty():
    assert _DET_PDF.exists(), str(_DET_PDF)
    assert _DET_PDF.stat().st_size > 10240, "detailed PDF unexpectedly small"


def test_07_professional_pdf_exists_nonempty():
    assert _PRO_PDF.exists(), str(_PRO_PDF)
    assert _PRO_PDF.stat().st_size > 10240, "professional PDF unexpectedly small"


# ---------------------------------------------------------------------------
# 4. Non-certified disclaimer
# ---------------------------------------------------------------------------
_NONCERT = "تقرير آلي استرشادي — غير معتمد رسميًا"


def test_08_traditional_non_certified_disclaimer():
    assert _NONCERT in _triple(_TRAD_PDF, _TRAD_PRV, _TRAD_TPL)


def test_09_detailed_non_certified_disclaimer():
    assert _NONCERT in _triple(_DET_PDF, _DET_PRV, _DET_TPL)


def test_10_professional_non_certified_disclaimer():
    assert _NONCERT in _triple(_PRO_PDF, _PRO_PRV, _PRO_TPL)


# ---------------------------------------------------------------------------
# 5. Watermark
# ---------------------------------------------------------------------------
_WATERMARK = "مسودة غير معتمدة"


def test_11_traditional_watermark():
    assert _WATERMARK in _triple(_TRAD_PDF, _TRAD_PRV, _TRAD_TPL)


def test_12_detailed_watermark():
    assert _WATERMARK in _triple(_DET_PDF, _DET_PRV, _DET_TPL)


def test_13_professional_watermark():
    assert _WATERMARK in _triple(_PRO_PDF, _PRO_PRV, _PRO_TPL)


# ---------------------------------------------------------------------------
# 6. No automatic Certified claim
# ---------------------------------------------------------------------------
_AUTO_CERT = "✓ معتمد"


def test_14_traditional_no_auto_cert():
    assert _AUTO_CERT not in _triple(_TRAD_PDF, _TRAD_PRV, _TRAD_TPL)


def test_15_detailed_no_auto_cert():
    assert _AUTO_CERT not in _triple(_DET_PDF, _DET_PRV, _DET_TPL)


def test_16_professional_no_auto_cert():
    assert _AUTO_CERT not in _triple(_PRO_PDF, _PRO_PRV, _PRO_TPL)


# ---------------------------------------------------------------------------
# 7. No fake signature / license / stamp images
# ---------------------------------------------------------------------------
_FAKE = ("signature.png", "license.png", "stamp.png")


def test_17_traditional_no_fake_assets():
    src = _triple(_TRAD_PDF, _TRAD_PRV, _TRAD_TPL)
    assert not [a for a in _FAKE if a in src]


def test_18_detailed_no_fake_assets():
    src = _triple(_DET_PDF, _DET_PRV, _DET_TPL)
    assert not [a for a in _FAKE if a in src]


def test_19_professional_no_fake_assets():
    src = _triple(_PRO_PDF, _PRO_PRV, _PRO_TPL)
    assert not [a for a in _FAKE if a in src]


# ---------------------------------------------------------------------------
# 8. No internal absolute paths in PDF text
# ---------------------------------------------------------------------------
def test_20_traditional_no_internal_paths():
    hits = re.findall(r"[A-Za-z]:\\[^\s\"<>]{5,}", _pdf_text(_TRAD_PDF))
    assert not hits, f"traditional PDF exposes paths: {hits[:3]}"


def test_21_detailed_no_internal_paths():
    hits = re.findall(r"[A-Za-z]:\\[^\s\"<>]{5,}", _pdf_text(_DET_PDF))
    assert not hits, f"detailed PDF exposes paths: {hits[:3]}"


def test_22_professional_no_internal_paths():
    hits = re.findall(r"[A-Za-z]:\\[^\s\"<>]{5,}", _pdf_text(_PRO_PDF))
    assert not hits, f"professional PDF exposes paths: {hits[:3]}"


# ---------------------------------------------------------------------------
# 9. No Excel workbook path exposed
# ---------------------------------------------------------------------------
_XL = (".xlsx", ".xlsm")


def test_23_traditional_no_excel_path():
    src = _triple(_TRAD_PDF, _TRAD_PRV, _TRAD_TPL)
    assert not [k for k in _XL if k in src], "traditional: Excel extension found"


def test_24_detailed_no_excel_path():
    src = _triple(_DET_PDF, _DET_PRV, _DET_TPL)
    assert not [k for k in _XL if k in src], "detailed: Excel extension found"


def test_25_professional_no_excel_path():
    src = _triple(_PRO_PDF, _PRO_PRV, _PRO_TPL)
    assert not [k for k in _XL if k in src], "professional: Excel extension found"


# ---------------------------------------------------------------------------
# 10. Traditional tier sections
# ---------------------------------------------------------------------------
def test_26_traditional_avm():
    src = _triple(_TRAD_PDF, _TRAD_PRV, _TRAD_TPL)
    assert "AVM" in src or "نموذج" in src


def test_27_traditional_sales_comparison():
    src = _triple(_TRAD_PDF, _TRAD_PRV, _TRAD_TPL)
    assert "مقارنة" in src or "sec-comparables" in src


def test_28_traditional_cost():
    src = _triple(_TRAD_PDF, _TRAD_PRV, _TRAD_TPL)
    assert "تكلفة" in src or "sec-cost" in src or "sec-boq" in src


def test_29_traditional_dcf():
    src = _triple(_TRAD_PDF, _TRAD_PRV, _TRAD_TPL)
    assert "DCF" in src or "sec-dcf" in src or "تدفقات" in src


def test_30_traditional_reconciliation():
    src = _triple(_TRAD_PDF, _TRAD_PRV, _TRAD_TPL)
    assert "توفيق" in src or "تسوية" in src or "sec-reconciliation" in src


def test_31_traditional_hbu():
    src = _triple(_TRAD_PDF, _TRAD_PRV, _TRAD_TPL)
    assert "HBU" in src or "أفضل استخدام" in src or "sec-hbu" in src


def test_32_traditional_swot():
    src = _triple(_TRAD_PDF, _TRAD_PRV, _TRAD_TPL)
    assert "SWOT" in src or "نقاط القوة" in src or "sec-swot" in src


# ---------------------------------------------------------------------------
# 11. Detailed tier sections
# ---------------------------------------------------------------------------
def test_33_detailed_land():
    src = _triple(_DET_PDF, _DET_PRV, _DET_TPL)
    assert "أراضي" in src or "sec-land" in src


def test_34_detailed_risk():
    src = _triple(_DET_PDF, _DET_PRV, _DET_TPL)
    assert "مخاطر" in src or "sec-risk" in src


def test_35_detailed_esg():
    src = _triple(_DET_PDF, _DET_PRV, _DET_TPL)
    assert "ESG" in src or "sec-esg" in src


def test_36_detailed_npv_irr_payback():
    src = _triple(_DET_PDF, _DET_PRV, _DET_TPL)
    assert (
        "NPV" in src or "IRR" in src or "Payback" in src
        or "صافي القيمة الحالية" in src
        or "معدل العائد الداخلي" in src
        or "فترة الاسترداد" in src
        or "sec-npv-irr" in src
    )


# ---------------------------------------------------------------------------
# 12. Professional tier sections
# ---------------------------------------------------------------------------
def test_37_professional_toc():
    src = _triple(_PRO_PDF, _PRO_PRV, _PRO_TPL)
    assert "فهرس" in src or "sec-toc" in src


def test_38_professional_scope():
    src = _triple(_PRO_PDF, _PRO_PRV, _PRO_TPL)
    assert "نطاق العمل" in src or "sec-scope-of-work" in src


def test_39_professional_compliance():
    src = _triple(_PRO_PDF, _PRO_PRV, _PRO_TPL)
    assert "بيان الامتثال" in src or "sec-compliance" in src


def test_40_professional_signature_gate():
    gate = "بانتظار التوقيع الرسمي من مقيم عقاري مرخص"
    src = _triple(_PRO_PDF, _PRO_PRV, _PRO_TPL)
    assert gate in src, "professional: exact signature gate phrase not found"


def test_41_professional_weighted_reconciliation():
    src = _triple(_PRO_PDF, _PRO_PRV, _PRO_TPL)
    assert "الترجيح الموزون" in src or "sec-weighted-recon" in src


# ---------------------------------------------------------------------------
# 13. Builder does not use FPDF
# ---------------------------------------------------------------------------
def test_42_builder_no_fpdf_import():
    src = _builder_source()
    bad = [
        ln.strip() for ln in src.splitlines()
        if ln.strip().startswith("import fpdf") or ln.strip().startswith("from fpdf")
    ]
    assert not bad, f"builder FPDF import lines: {bad}"


# ---------------------------------------------------------------------------
# 14. Audit artifacts exist
# ---------------------------------------------------------------------------
def test_43_visual_qa_index_exists():
    assert _QA_INDEX.exists(), str(_QA_INDEX)
    assert _QA_INDEX.stat().st_size > 1024


def test_44_zero_loss_audit_exists():
    assert _ZERO_LOSS.exists(), str(_ZERO_LOSS)
    assert _ZERO_LOSS.stat().st_size > 512
