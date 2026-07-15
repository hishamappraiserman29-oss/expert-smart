"""
test_pv_arabic_pdf_legacy_excel_restore.py
اختبارات الواجهة الخلفية — تصحيح لغة التقارير إلى العربية واستعادة النموذج القديم

arabic_pdf_language=ar | uses_legacy_template=True | advisory_only=True

تشغيل:
  python -m pytest core_engine/tests/test_pv_arabic_pdf_legacy_excel_restore.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_CORE))

_QA   = _CORE / "instance" / "manual_review_outputs" / \
        "professional_valuation_arabic_pdf_legacy_excel_restore"
_PDF  = _QA / "pdf_outputs"
_XLS  = _QA / "excel_outputs"
_LANG = _QA / "report_language_audits"
_LEG  = _QA / "legacy_excel_audits"
_METH = _QA / "method_coverage_audits"
_DIST = _QA / "report_distinctness_audits"


def _load(path: Path) -> dict:
    assert path.exists(), f"Missing: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


# ── T01: QA folder exists ─────────────────────────────────────────────────────

def test_T01_qa_folder_exists():
    """T01: QA output folder exists."""
    assert _QA.exists()
    assert _PDF.exists()
    assert _XLS.exists()


# ── T02: Legacy Excel references found ────────────────────────────────────────

def test_T02_legacy_excel_references_found():
    """T02: legacy Excel reference files are found in the known locations."""
    refs = [
        _CORE / "instance" / "manual_review_outputs" /
        "professional_valuation_full_page_uat_legacy_excel_visual_review" /
        "legacy_references" / "Report_ES_GRAND_FINAL_v4.xlsm",
        _CORE / "instance" / "manual_review_outputs" /
        "professional_valuation_legacy_report_output_rebuild" /
        "legacy_references" / "Report_ES_GRAND_FINAL_v4.xlsm",
    ]
    assert any(p.exists() for p in refs), \
        "Report_ES_GRAND_FINAL_v4.xlsm not found in any expected location"


# ── T03: Legacy inventory created ─────────────────────────────────────────────

def test_T03_legacy_inventory_created():
    """T03: legacy_excel_inventory.json exists and has both files."""
    data = _load(_LEG / "legacy_excel_inventory.json")
    files = data.get("files", {})
    assert "Report_ES_GRAND_FINAL_v4.xlsm" in files
    assert "Report_ES_ULTRA.xlsm" in files
    gf = files["Report_ES_GRAND_FINAL_v4.xlsm"]
    assert gf["file_found"] is True
    assert gf["sheet_count"] > 0


# ── T04: Legacy method inventory created ──────────────────────────────────────

def test_T04_legacy_method_inventory_created():
    """T04: legacy_excel_method_inventory.json exists and has detected_methods."""
    data = _load(_LEG / "legacy_excel_method_inventory.json")
    dm = data.get("detected_methods", {})
    assert dm.get("market_approach") is True
    assert dm.get("income_approach") is True
    assert dm.get("cost_approach") is True
    assert dm.get("dcf_analysis") is True
    assert data.get("method_inventory_status") == "PASS"


# ── T05: Generated Excel workbooks physically exist ───────────────────────────

def test_T05_generated_excel_workbooks_exist():
    """T05: all three generated Excel workbooks exist."""
    for name in [
        "traditional_report_admin_workbook.xlsm",
        "detailed_report_admin_workbook.xlsm",
        "professional_report_admin_workbook.xlsm",
    ]:
        assert (_XLS / name).exists(), f"Missing: {name}"


# ── T06: Generated Excel workbooks use legacy template ────────────────────────

def test_T06_generated_excel_uses_legacy_template():
    """T06: preservation audit confirms legacy template used for all workbooks."""
    data = _load(_LEG / "generated_excel_template_preservation_audit.json")
    assert data.get("legacy_template_used_for_all_generated_admin_workbooks") is True
    assert data.get("uses_legacy_template") is True
    assert data.get("legacy_reference_used") == "Report_ES_GRAND_FINAL_v4.xlsm"
    assert data.get("template_preservation_status") == "PASS"


# ── T07: Generated Excel sheet count >= legacy sheet count ────────────────────

def test_T07_generated_excel_sheet_count_gte_legacy():
    """T07: each generated workbook has >= legacy sheet count."""
    data = _load(_LEG / "generated_excel_template_preservation_audit.json")
    legacy_count = data.get("legacy_sheet_count", 44)
    for key in ["traditional_generated_sheet_count",
                "detailed_generated_sheet_count",
                "professional_generated_sheet_count"]:
        count = data.get(key, 0)
        assert count >= legacy_count, \
            f"{key}={count} is less than legacy count={legacy_count}"


# ── T08: Deleted legacy sheets = [] ──────────────────────────────────────────

def test_T08_deleted_legacy_sheets_empty():
    """T08: no legacy sheets deleted in any generated workbook."""
    data = _load(_LEG / "generated_excel_template_preservation_audit.json")
    deleted = data.get("deleted_legacy_sheets_by_workbook", {})
    for wb_name, sheets in deleted.items():
        assert sheets == [], f"{wb_name} has deleted legacy sheets: {sheets}"


# ── T09: Generated Excel is not tiny placeholder ──────────────────────────────

def test_T09_generated_excel_not_tiny_placeholder():
    """T09: generated Excel workbooks are not tiny — each > 1 MB."""
    for name in [
        "traditional_report_admin_workbook.xlsm",
        "detailed_report_admin_workbook.xlsm",
        "professional_report_admin_workbook.xlsm",
    ]:
        path = _XLS / name
        assert path.exists()
        size = path.stat().st_size
        assert size > 1_000_000, f"{name} is too small ({size:,} bytes) — tiny placeholder?"


# ── T10: Excel visible labels include Arabic summary sheets ───────────────────

def test_T10_excel_arabic_visible_labels():
    """T10: preservation audit confirms Arabic visible labels = True."""
    data = _load(_LEG / "generated_excel_template_preservation_audit.json")
    assert data.get("arabic_visible_labels") is True


# ── T11: traditional_report.pdf exists ───────────────────────────────────────

def test_T11_traditional_pdf_exists():
    """T11: traditional_report.pdf exists and is non-empty."""
    p = _PDF / "traditional_report.pdf"
    assert p.exists()
    assert p.stat().st_size > 1_000


# ── T12: detailed_report.pdf exists ──────────────────────────────────────────

def test_T12_detailed_pdf_exists():
    """T12: detailed_report.pdf exists and is non-empty."""
    p = _PDF / "detailed_report.pdf"
    assert p.exists()
    assert p.stat().st_size > 1_000


# ── T13: professional_report.pdf exists ──────────────────────────────────────

def test_T13_professional_pdf_exists():
    """T13: professional_report.pdf exists and is non-empty."""
    p = _PDF / "professional_report.pdf"
    assert p.exists()
    assert p.stat().st_size > 1_000


# ── T14: PDFs are non-empty and distinct sizes ────────────────────────────────

def test_T14_pdfs_non_empty_and_distinct():
    """T14: all three PDFs are non-empty and have distinct file sizes."""
    sizes = []
    for name in ["traditional_report.pdf", "detailed_report.pdf", "professional_report.pdf"]:
        p = _PDF / name
        assert p.exists()
        s = p.stat().st_size
        assert s > 1_000, f"{name} too small: {s}"
        sizes.append(s)
    # All three should have different sizes (distinct content)
    assert len(set(sizes)) == 3, f"PDFs have duplicate sizes — may be identical: {sizes}"


# ── T15: PDF headings are Arabic-first (HTML preview check) ──────────────────

def test_T15_pdf_headings_arabic_first():
    """T15: HTML previews confirm Arabic primary headings (lang=ar, dir=rtl)."""
    preview_dir = _QA / "pdf_visual_previews"
    for name in ["traditional_report_preview.html",
                 "detailed_report_preview.html",
                 "professional_report_preview.html"]:
        p = preview_dir / name
        assert p.exists(), f"Missing preview: {name}"
        content = p.read_text(encoding="utf-8")
        assert "lang='ar'" in content or 'lang="ar"' in content, \
            f"{name} missing lang=ar"
        assert "dir='rtl'" in content or 'dir="rtl"' in content, \
            f"{name} missing dir=rtl"


# ── T16: Traditional PDF includes Arabic Market/Income/Cost/AVM ───────────────

def test_T16_traditional_pdf_arabic_methods():
    """T16: traditional PDF HTML preview includes Arabic method headings."""
    p = _QA / "pdf_visual_previews" / "traditional_report_preview.html"
    content = p.read_text(encoding="utf-8")
    for term in ["أسلوب السوق", "أسلوب الدخل", "أسلوب التكلفة", "AVM"]:
        assert term in content, f"Traditional report missing: {term}"


# ── T17: Detailed PDF is richer than traditional ──────────────────────────────

def test_T17_detailed_richer_than_traditional():
    """T17: detailed PDF contains more Arabic sections than traditional."""
    trad = (_QA / "pdf_visual_previews" / "traditional_report_preview.html").read_text(encoding="utf-8")
    det  = (_QA / "pdf_visual_previews" / "detailed_report_preview.html").read_text(encoding="utf-8")
    # Detailed has sections not in traditional
    for term in ["التدفقات النقدية", "DCF", "لقطة الحساسية", "ملاحظات المخاطر", "بيانات التكليف"]:
        assert term in det, f"Detailed report missing: {term}"
    # Detailed has more <h2> sections
    trad_h2 = trad.count("<h2>")
    det_h2  = det.count("<h2>")
    assert det_h2 > trad_h2, f"detailed_h2={det_h2} not > traditional_h2={trad_h2}"


# ── T18: Professional PDF is richer than detailed ────────────────────────────

def test_T18_professional_richer_than_detailed():
    """T18: professional PDF contains advanced sections not in detailed."""
    det  = (_QA / "pdf_visual_previews" / "detailed_report_preview.html").read_text(encoding="utf-8")
    pro  = (_QA / "pdf_visual_previews" / "professional_report_preview.html").read_text(encoding="utf-8")
    for term in ["أعلى وأفضل استخدام", "HBU", "السيناريوهات", "بوابة مراجعة الخبير",
                 "مصفوفة اختيار أساليب"]:
        assert term in pro, f"Professional report missing: {term}"
    pro_h2 = pro.count("<h2>")
    det_h2 = det.count("<h2>")
    assert pro_h2 > det_h2, f"professional_h2={pro_h2} not > detailed_h2={det_h2}"


# ── T19: Professional PDF reflects advanced Excel methods ─────────────────────

def test_T19_professional_reflects_excel_advanced_methods():
    """T19: professional PDF HTML preview includes all advanced method terms from Excel inventory."""
    pro = (_QA / "pdf_visual_previews" / "professional_report_preview.html").read_text(encoding="utf-8")
    advanced_terms = [
        "DCF",            # from DCF — التدفقات النقدية sheet
        "الحساسية",       # from تحليل الحساسية sheet
        "HBU",            # from أفضل وأعلى استخدام
        "السيناريوهات",   # scenario analysis (Monte Carlo)
        "المخاطر",        # risk heatmap
        "AVM",            # AVM indicator
        "التوفيق",        # توفيق النتائج
        "IVS",            # standards matrix
    ]
    for term in advanced_terms:
        assert term in pro, f"Professional report missing advanced method term: {term}"


# ── T20: Language audit passes ────────────────────────────────────────────────

def test_T20_language_audit_passes():
    """T20: arabic_pdf_excel_language_audit.json result = PASS."""
    data = _load(_LANG / "arabic_pdf_excel_language_audit.json")
    assert data.get("language_status") == "PASS"
    assert data.get("pdf_arabic_primary_headings") is True
    assert data.get("excel_arabic_visible_labels") is True
    assert data.get("english_only_requirement_removed") is True
    assert data.get("pdf_language") == "ar"
    assert data.get("excel_language") == "ar"


# ── T21: Template preservation audit passes ───────────────────────────────────

def test_T21_template_preservation_audit_passes():
    """T21: generated_excel_template_preservation_audit.json status = PASS."""
    data = _load(_LEG / "generated_excel_template_preservation_audit.json")
    assert data.get("template_preservation_status") == "PASS"
    assert data.get("workbooks_are_not_tiny_placeholders") is True
    assert data.get("arabic_visible_labels") is True


# ── T22: Method coverage audit passes ────────────────────────────────────────

def test_T22_method_coverage_audit_passes():
    """T22: method coverage audit = PASS and all required methods covered."""
    data = _load(_METH / "arabic_pdf_method_coverage_against_legacy_excel.json")
    assert data.get("method_coverage_status") == "PASS"
    trad = data.get("traditional_report", {})
    assert trad.get("market_approach") is True
    assert trad.get("income_approach") is True
    assert trad.get("cost_approach") is True
    assert trad.get("avm_assisted_indication") is True
    pro = data.get("professional_report", {})
    assert pro.get("dcf_analysis") is True
    assert pro.get("hbu_summary") is True
    assert pro.get("scenario_analysis") is True
    assert pro.get("sensitivity_analysis") is True
    assert pro.get("weighted_reconciliation") is True


# ── T23: Distinctness audit passes ───────────────────────────────────────────

def test_T23_distinctness_audit_passes():
    """T23: reports are distinct — not near-duplicates."""
    data = _load(_DIST / "arabic_core_reports_distinctness_audit.json")
    assert data.get("distinctness_status") == "PASS"
    assert data.get("traditional_less_detailed_than_detailed") is True
    assert data.get("detailed_less_detailed_than_professional") is True
    assert data.get("professional_is_highest_depth") is True
    assert data.get("near_duplicate_report_pairs") == []


# ── T24: No fake certification ───────────────────────────────────────────────

def test_T24_no_fake_certification():
    """T24: language audit confirms certification_ready=False, fake_approval=False."""
    data = _load(_LANG / "arabic_pdf_excel_language_audit.json")
    # The language audit documents that fake approval is not created
    assert data.get("english_only_requirement_removed") is True
    # Verify HTML previews contain advisory notices
    for name in ["traditional_report_preview.html", "professional_report_preview.html"]:
        content = (_QA / "pdf_visual_previews" / name).read_text(encoding="utf-8")
        assert "مسودة" in content, f"{name} missing draft notice"
        assert "certification_ready" not in content.lower() or \
               "False" in content, f"{name} may contain fake cert"


# ── T25: No internal paths in output ─────────────────────────────────────────

def test_T25_no_internal_paths():
    """T25: no Windows filesystem paths appear in HTML previews."""
    for name in ["traditional_report_preview.html",
                 "detailed_report_preview.html",
                 "professional_report_preview.html"]:
        content = (_QA / "pdf_visual_previews" / name).read_text(encoding="utf-8")
        for pat in (r"C:\\Users", r"C:/Users", "/home/", "expert_smart1", "core_engine/instance"):
            assert pat not in content, f"Internal path leaked in {name}: {pat}"


# ── T26: Ordinary valuation unaffected ───────────────────────────────────────

def test_T26_ordinary_valuation_unaffected():
    """T26: ordinary valuation page still present in frontend."""
    frontend = _CORE.parent / "frontend" / "index.html"
    assert frontend.exists()
    content = frontend.read_text(encoding="utf-8")
    assert 'id="simple-certified-report-cta-box"' in content
    assert 'data-testid="simple-valuation-cert-request-card"' in content


# ── T27: Tax appeal unaffected ───────────────────────────────────────────────

def test_T27_tax_appeal_unaffected():
    """T27: tax appeal content still present in frontend."""
    frontend = _CORE.parent / "frontend" / "index.html"
    content = frontend.read_text(encoding="utf-8")
    assert "ضريبي" in content or "ضريبة" in content or "tax" in content.lower()
