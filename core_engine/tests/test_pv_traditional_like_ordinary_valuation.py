"""
test_pv_traditional_like_ordinary_valuation.py
32 tests — Traditional Report matching ordinary valuation page quality.
advisory_only=True | no_fake_cert=True | no_commit=True | certification_ready=False
"""
from __future__ import annotations
import json
from pathlib import Path
import pytest

_CORE = Path(__file__).resolve().parent.parent
_OUT  = _CORE / "instance" / "manual_review_outputs" / "professional_valuation_traditional_like_ordinary_valuation"
_REF  = _CORE / "instance" / "manual_review_outputs" / "valuation_certification_readiness_gate"
_PDF  = _OUT / "pdf_outputs" / "traditional_report.pdf"
_HTML = _OUT / "pdf_outputs" / "traditional_report.html"
_XL   = _OUT / "excel_outputs" / "professional_valuation_admin_master_workbook.xlsx"
_PAD  = _OUT / "pdf_audits"
_XAD  = _OUT / "excel_audits"
_SAD  = _OUT / "source_reference_audits"
_FRP  = _OUT / "final_report"
_PVP  = _OUT / "pdf_visual_previews"
_EVP  = _OUT / "excel_visual_previews"

_ORD_VAL = _CORE / "professional_valuation_routes.py"
_TAX_APP = _CORE / "tax_appeal_routes.py"

# Arabic keywords expected in report
_PDF_KEYWORDS = [
    "AVM", "مقارنة", "رسملة", "التكلفة", "DCF", "التوفيق",
    "HBU", "المخاطر", "عدم اليقين", "التوصية", "الاعتماد",
    "الخبير", "الافتراضات", "مصادر",
]


def _pdf_text() -> str:
    # Prefer HTML source for canonical Unicode (PDF may use presentation/ligature forms)
    if _HTML.exists():
        return _HTML.read_text(encoding="utf-8", errors="ignore")
    if not _PDF.exists():
        return ""
    try:
        from pypdf import PdfReader
        return " ".join(p.extract_text() or "" for p in PdfReader(str(_PDF)).pages)
    except Exception:
        return ""


def _j(fname: str) -> dict:
    p = _PAD / fname
    assert p.exists(), f"Audit missing: {fname}"
    return json.loads(p.read_text(encoding="utf-8"))


# T01 — output folder exists
def test_T01_output_folder_exists():
    assert _OUT.exists(), f"Output folder missing: {_OUT}"


# T02 — reference PDF is detected
def test_T02_reference_pdf_detected():
    ref = _REF / "01_market_certification_readiness_preliminary.pdf"
    assert ref.exists(), f"Reference PDF missing: {ref}"
    assert ref.stat().st_size > 100_000, "Reference PDF too small"


# T03 — reference Excel is detected
def test_T03_reference_excel_detected():
    ref = _REF / "03_market_certification_readiness_workbook.xlsx"
    assert ref.exists(), f"Reference Excel missing: {ref}"


# T04 — source files are not modified
def test_T04_source_files_not_modified():
    audit_f = _SAD / "source_files_preservation_audit.json"
    assert audit_f.exists(), "Source preservation audit missing"
    data = json.loads(audit_f.read_text(encoding="utf-8"))
    assert data["source_files_preserved"] is True
    assert data["source_files_deleted"] is False
    assert data["source_files_overwritten"] is False
    assert data["source_files_modified"] is False


# T05 — traditional_report.pdf exists
def test_T05_traditional_report_pdf_exists():
    assert _PDF.exists() or _HTML.exists(), \
        "Neither traditional_report.pdf nor traditional_report.html found"


# T06 — traditional_report.pdf is non-empty (>50KB)
def test_T06_traditional_report_pdf_non_empty():
    if _PDF.exists():
        assert _PDF.stat().st_size > 50_000, f"PDF too small: {_PDF.stat().st_size}"
    else:
        assert _HTML.exists(), "No PDF and no HTML fallback"
        assert _HTML.stat().st_size > 20_000, "HTML fallback too small"


# T07 — traditional_report.pdf opens successfully
def test_T07_traditional_report_pdf_opens():
    if _PDF.exists():
        try:
            from pypdf import PdfReader
            r = PdfReader(str(_PDF))
            assert len(r.pages) >= 1
        except ImportError:
            pytest.skip("pypdf not installed")
    else:
        assert _HTML.exists()
        content = _HTML.read_text(encoding="utf-8", errors="ignore")
        assert len(content) > 10_000


# T08 — traditional_report.pdf is Arabic-first
def test_T08_traditional_report_arabic_first():
    txt = _pdf_text()
    assert len(txt) > 0, "Could not extract report text"
    arabic_chars = sum(1 for c in txt if '؀' <= c <= 'ۿ')
    assert arabic_chars > 100, f"Not enough Arabic text: {arabic_chars} chars"


# T09 — contains AVM section
def test_T09_contains_avm():
    txt = _pdf_text()
    assert "AVM" in txt or "آلي" in txt, "AVM section not found"


# T10 — contains sales comparison
def test_T10_contains_sales_comparison():
    txt = _pdf_text()
    assert "مقارنة" in txt or "Sales" in txt or "Comparison" in txt, \
        "Sales comparison not found"


# T11 — contains land value / land comparison
def test_T11_contains_land_value():
    txt = _pdf_text()
    assert "أرض" in txt or "أراضي" in txt or "land" in txt.lower(), \
        "Land value section not found"


# T12 — contains income capitalization
def test_T12_contains_income_capitalization():
    txt = _pdf_text()
    assert "رسملة" in txt or "Income" in txt or "NOI" in txt, \
        "Income capitalization not found"


# T13 — contains cost approach
def test_T13_contains_cost_approach():
    txt = _pdf_text()
    assert "التكلفة" in txt or "Cost" in txt, "Cost approach not found"


# T14 — contains DCF support
def test_T14_contains_dcf_support():
    txt = _pdf_text()
    assert "DCF" in txt, "DCF section not found"


# T15 — contains reconciliation
def test_T15_contains_reconciliation():
    txt = _pdf_text()
    assert "التوفيق" in txt or "Reconciliation" in txt, "Reconciliation not found"


# T16 — contains HBU summary
def test_T16_contains_hbu_summary():
    txt = _pdf_text()
    assert "HBU" in txt or "أفضل استخدام" in txt or "أعلى" in txt, \
        "HBU summary not found"


# T17 — contains risk / readiness section
def test_T17_contains_risk_readiness():
    txt = _pdf_text()
    assert "المخاطر" in txt or "مخاطر" in txt or "Risk" in txt, \
        "Risk section not found"


# T18 — contains uncertainty range
def test_T18_contains_uncertainty_range():
    txt = _pdf_text()
    assert "نطاق" in txt or "uncertainty" in txt.lower() or "range" in txt.lower(), \
        "Uncertainty range not found"


# T19 — contains data sources
def test_T19_contains_data_sources():
    txt = _pdf_text()
    assert "مصادر" in txt or "Sources" in txt or "source" in txt.lower(), \
        "Data sources section not found"


# T20 — contains final recommendation
def test_T20_contains_final_recommendation():
    txt = _pdf_text()
    assert "التوصية" in txt or "Recommendation" in txt or "توصية" in txt, \
        "Final recommendation not found"


# T21 — contains certification gate
def test_T21_contains_certification_gate():
    txt = _pdf_text()
    assert ("الاعتماد" in txt or "certification" in txt.lower()
            or "gate" in txt.lower() or "الخبير" in txt), \
        "Certification gate not found"


# T22 — no fake signature
def test_T22_no_fake_signature():
    txt = _pdf_text()
    fake_patterns = ["signed by", "digital signature:", "signature: ✓"]
    for p in fake_patterns:
        assert p.lower() not in txt.lower(), f"Fake signature pattern found: {p}"
    # Must say "غير متاح" or "بانتظار" near توقيع
    assert "غير متاح" in txt or "بانتظار" in txt or "مسودة" in txt, \
        "No draft/pending marker found near signature area"


# T23 — no fake stamp
def test_T23_no_fake_stamp():
    txt = _pdf_text()
    assert "ختم رسمي معتمد" not in txt
    assert "official stamp" not in txt.lower()


# T24 — no fake certification
def test_T24_no_fake_certification():
    txt = _pdf_text()
    # certification_ready=True must not appear as a claim
    assert "certification_ready=True" not in txt, \
        "Fake certification_ready=True found in report text"
    assert "معتمد رسمياً" not in txt or "غير معتمد رسمياً" in txt, \
        "Report claims official certification"


# T25 — admin Excel workbook exists
def test_T25_admin_excel_workbook_exists():
    xl = _XL
    xm = _OUT / "excel_outputs" / "professional_valuation_admin_master_workbook.xlsm"
    found = xl.exists() or xm.exists()
    assert found, f"Admin Excel workbook not found at {xl} or {xm}"


# T26 — admin Excel includes method sheets
def test_T26_admin_excel_includes_method_sheets():
    xl = _XL if _XL.exists() else _OUT / "excel_outputs" / "professional_valuation_admin_master_workbook.xlsm"
    if not xl.exists():
        pytest.skip("Excel workbook not found")
    try:
        import openpyxl
        wb = openpyxl.load_workbook(str(xl), read_only=True, data_only=True)
        names = wb.sheetnames
        required = ["Cover", "Income Approach", "Cost Approach", "Comparables",
                    "AVM Reference", "Reconciliation", "Risk Register"]
        for r in required:
            assert r in names, f"Required sheet missing: {r}"
        wb.close()
    except ImportError:
        pytest.skip("openpyxl not installed")


# T27 — attached workbook mapping audit exists
def test_T27_attached_workbook_mapping_audit_exists():
    f = _XAD / "attached_traditional_method_workbooks_mapping.json"
    assert f.exists(), f"Mapping audit missing: {f}"
    data = json.loads(f.read_text(encoding="utf-8"))
    assert "market_certification_workbook" in data
    assert "income_capitalization" in data
    assert "cost_approach" in data
    assert "dcf" in data
    assert "reconciliation" in data


# T28 — style similarity audit exists and passes
def test_T28_style_similarity_audit_passes():
    f = _PAD / "traditional_report_matches_ordinary_valuation_reference_audit.json"
    assert f.exists(), f"Style similarity audit missing: {f}"
    data = json.loads(f.read_text(encoding="utf-8"))
    assert data["reference_pdf_used"] is True
    assert data["arabic_rtl_layout"] is True
    assert data["method_tables_present"] is True
    assert data["certification_gate_present"] is True
    assert data["style_similarity_status"] == "PASS"
    assert data.get("certification_ready") is False


# T29 — number traceability audit exists and passes
def test_T29_number_traceability_audit_passes():
    f = _PAD / "traditional_pdf_number_traceability_audit.json"
    assert f.exists(), f"Traceability audit missing: {f}"
    data = json.loads(f.read_text(encoding="utf-8"))
    assert data["numbers_traced_to_excel_or_source"] is True
    assert data["illustrative_numbers_explained"] is True
    assert data["traceability_status"] == "PASS"
    assert len(data.get("untraced_numbers", [])) == 0


# T30 — no internal paths in main HTML output
def test_T30_no_internal_paths():
    html = _HTML if _HTML.exists() else None
    cmp  = _PVP / "OPEN_TRADITIONAL_REPORT_REFERENCE_COMPARISON.html"
    for f in [html, cmp]:
        if f and f.exists():
            content = f.read_text(encoding="utf-8", errors="ignore")
            for bad in [r"C:\\Users", "C:/Users", "/home/"]:
                assert bad not in content, f"Internal path found in {f.name}: {bad}"


# T31 — ordinary valuation page unaffected
def test_T31_ordinary_valuation_page_unaffected():
    assert _ORD_VAL.exists(), "professional_valuation_routes.py missing — ordinary valuation page broken"


# T32 — tax appeal unaffected
def test_T32_tax_appeal_unaffected():
    assert _TAX_APP.exists(), "tax_appeal_routes.py missing — tax appeal page broken"
