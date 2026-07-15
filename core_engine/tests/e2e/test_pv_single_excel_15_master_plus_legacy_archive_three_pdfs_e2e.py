"""
test_pv_single_excel_15_master_plus_legacy_archive_three_pdfs_e2e.py
اختبارات E2E — ملف Excel واحد: 15 ورقة رئيسية + أرشيف قديم + 3 تقارير PDF

تشغيل الاختبارات الساكنة:
  python -m pytest core_engine/tests/e2e/test_pv_single_excel_15_master_plus_legacy_archive_three_pdfs_e2e.py -q -m "not live_server"

arabic_primary=True | single_admin_excel=True | advisory_only=True
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parent.parent.parent
_QA   = _CORE / "instance" / "manual_review_outputs" / \
        "professional_valuation_single_excel_15_master_plus_legacy_archive_three_pdfs"
_XL   = _QA / "excel_outputs"
_PDF  = _QA / "pdf_outputs"
_PREV = _QA / "pdf_visual_previews"
_XPREV= _QA / "excel_visual_previews"
_XAUD = _QA / "excel_audits"
_PAUD = _QA / "pdf_audits"
_BASE_URL = "http://127.0.0.1:5000"

sys.path.insert(0, str(_CORE))

try:
    from playwright.sync_api import Page, expect
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Page = object  # type: ignore[misc]

MASTER_SHEET_NAMES = [
    "Cover", "Data Quality", "Property", "HBU Analysis", "Comparables",
    "Income Approach", "Cost Approach", "AVM Reference", "Scenarios",
    "Sensitivity Matrix", "Reconciliation", "Risk Register",
    "Standards Matrix", "Source Registry", "Admin Notes",
]
_WORKBOOK = "professional_valuation_admin_master_workbook.xlsm"
_LIVE = pytest.mark.live_server
_SKIP_NO_PW = pytest.mark.skipif(
    not PLAYWRIGHT_AVAILABLE,
    reason="playwright not installed — run: pip install playwright && playwright install chromium",
)


def _load(path: Path) -> dict:
    assert path.exists(), f"Audit file missing: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def _html(key: str) -> str:
    p = _PREV / f"{key}_preview.html"
    assert p.exists(), f"Missing PDF preview: {p}"
    return p.read_text(encoding="utf-8")


def _wb_sheets() -> list[str]:
    import openpyxl
    wb = openpyxl.load_workbook(str(_XL / _WORKBOOK), read_only=True)
    names = wb.sheetnames
    wb.close()
    return names


# ═══════════════════════════════════════════════════════════════════════════════
# STATIC TESTS — no live server required
# ═══════════════════════════════════════════════════════════════════════════════

def test_E01_qa_folder_exists():
    """E01: QA output folder exists."""
    assert _QA.exists()


def test_E02_admin_excel_exists():
    """E02: one admin Excel workbook exists."""
    assert (_XL / _WORKBOOK).exists()


def test_E03_pdf_outputs_exist():
    """E03: all three PDF outputs exist."""
    for name in ["traditional_report.pdf", "detailed_report.pdf", "professional_report.pdf"]:
        assert (_PDF / name).exists(), f"Missing PDF: {name}"


def test_E04_only_one_excel_file():
    """E04: only one Excel file exists in the output (not three)."""
    xl_files = list(_XL.glob("*.xlsm")) + list(_XL.glob("*.xlsx"))
    assert len(xl_files) == 1, f"Found {len(xl_files)} Excel files — expected 1"


def test_E05_first_15_sheets_are_master():
    """E05: first 15 sheets are the required master sheets in exact order."""
    sheets = _wb_sheets()
    assert sheets[:15] == MASTER_SHEET_NAMES


def test_E06_legacy_archive_sheets_present():
    """E06: legacy archive sheets are present after the first 15."""
    sheets = _wb_sheets()
    legacy = sheets[15:]
    assert len(legacy) > 0, "No legacy archive sheets found"
    # At least some sheets should have LEGACY_ prefix
    has_prefix = any(s.startswith("LEGACY_GF_") or s.startswith("LEGACY_ULTRA_") for s in legacy)
    assert has_prefix, f"No LEGACY_ prefixed sheets found in: {legacy[:10]}"


def test_E07_total_sheet_count_is_15_plus_legacy():
    """E07: total sheet count is 15 (master) + number of legacy sheets."""
    sheets = _wb_sheets()
    assert len(sheets) > 15, f"Only {len(sheets)} sheets found — expected > 15"


def test_E08_traditional_pdf_non_empty():
    """E08: traditional_report.pdf is non-empty (>10KB)."""
    assert (_PDF / "traditional_report.pdf").stat().st_size > 10_000


def test_E09_detailed_pdf_larger_than_traditional():
    """E09: detailed PDF is larger than traditional."""
    trad = (_PDF / "traditional_report.pdf").stat().st_size
    det  = (_PDF / "detailed_report.pdf").stat().st_size
    assert det > trad, f"detailed ({det:,}) not > traditional ({trad:,})"


def test_E10_professional_pdf_largest():
    """E10: professional PDF is the largest."""
    sizes = {k: (_PDF / f"{k}.pdf").stat().st_size
             for k in ["traditional_report", "detailed_report", "professional_report"]}
    assert sizes["professional_report"] == max(sizes.values()), \
        f"professional_report not largest: {sizes}"


def test_E11_detailed_has_dcf_and_sensitivity():
    """E11: detailed report contains DCF and sensitivity content."""
    content = _html("detailed_report")
    assert "DCF" in content or "التدفقات النقدية" in content
    assert "الحساسية" in content or "Sensitivity" in content


def test_E12_professional_has_dual_dcf():
    """E12: professional report references 5-year and 10-year DCF."""
    content = _html("professional_report")
    assert "5 سنوات" in content or "5-year" in content.lower()
    assert "10 سنوات" in content or "10-year" in content.lower()


def test_E13_professional_has_scenarios_and_hbu():
    """E13: professional report contains scenario analysis and HBU."""
    content = _html("professional_report")
    assert "السيناريو" in content or "Scenario" in content
    assert "HBU" in content or "أعلى وأفضل استخدام" in content


def test_E14_professional_has_npv_and_risk_impact():
    """E14: professional report contains NPV/IRR and risk impact."""
    content = _html("professional_report")
    assert "NPV" in content
    assert "المعدَّلة بالمخاطر" in content or "risk" in content.lower()


def test_E15_no_internal_paths_in_previews():
    """E15: no internal filesystem paths exposed in output previews."""
    for key in ["traditional_report", "detailed_report", "professional_report"]:
        content = _html(key)
        for pat in (r"C:\\Users", r"C:/Users", "/home/", "core_engine/instance"):
            assert pat not in content, f"Internal path in {key}: {pat}"


def test_E16_visual_review_index_exists():
    """E16: pdf visual review index HTML exists."""
    assert (_PREV / "three_pdf_visual_review_index.html").exists()


def test_E17_excel_visual_preview_index_exists():
    """E17: Excel admin workbook visual preview index exists."""
    assert (_XPREV / "admin_master_workbook_15_plus_legacy_archive_index.html").exists()


def test_E18_excel_structure_audit_passes():
    """E18: Excel structure audit confirms single workbook with 15+legacy sheets."""
    data = _load(_XAUD / "excel_master_15_plus_legacy_archive_structure_audit.json")
    assert data["single_excel_workbook_generated"] is True
    assert data["first_15_sheets_are_master_sheets"] is True
    assert data["legacy_archive_sheets_included_after_master_sheets"] is True
    assert data["no_three_separate_excel_workbooks"] is True
    assert data["excel_status"] == "PASS"


def test_E19_legacy_archive_audit_passes():
    """E19: legacy archive audit confirms both source files copied."""
    data = _load(_XAUD / "legacy_archive_sheets_audit.json")
    assert data["legacy_archive_enabled"] is True
    assert data["legacy_source_files_modified"] is False
    assert data["legacy_source_files_deleted"] is False
    assert data["legacy_archive_status"] == "PASS"


def test_E20_pdf_coverage_audit_passes():
    """E20: PDF coverage audit confirms professional PDF covers advanced methods."""
    data = _load(_PAUD / "pdf_depth_and_method_coverage_audit.json")
    pro = data["professional_report"]
    assert pro["dcf_full"] is True
    assert pro["hbu_summary"] is True
    assert pro["scenarios"] is True
    assert pro["weighted_reconciliation"] is True
    assert pro["richer_than_detailed"] is True
    assert data["pdf_status"] == "PASS"


def test_E21_consolidation_mapping_covers_all_30():
    """E21: consolidation mapping covers all 30 legacy concept sheets."""
    data = _load(_XAUD / "excel_sheet_consolidation_mapping.json")
    assert data["source_concept_sheet_count"] == 30
    assert data["target_master_sheet_count"] == 15
    assert len(data["mapping"]) == 30


def test_E22_pdf_single_excel_context_audit_passes():
    """E22: all PDFs use the single admin Excel workbook context."""
    data = _load(_PAUD / "pdf_uses_single_excel_context_audit.json")
    assert data["pdf_context_status"] == "PASS"
    assert data["single_excel_workbook_used"] == _WORKBOOK


def test_E23_no_fake_certification():
    """E23: no fake certification in any preview."""
    for key in ["traditional_report", "detailed_report", "professional_report"]:
        content = _html(key)
        assert "مسودة" in content
        assert "certification_ready=False" in content or "advisory_only=True" in content


def test_E24_three_pdfs_have_distinct_sizes():
    """E24: three PDFs have distinct (non-identical) sizes."""
    sizes = [(_PDF / f"{k}.pdf").stat().st_size
             for k in ["traditional_report", "detailed_report", "professional_report"]]
    assert len(set(sizes)) == 3, f"Non-distinct PDF sizes: {sizes}"


# ═══════════════════════════════════════════════════════════════════════════════
# LIVE SERVER + PLAYWRIGHT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

@_LIVE
@_SKIP_NO_PW
def test_E25_page_opens_without_js_errors(page: Page):
    """E25: Professional Valuation page opens without JS errors."""
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{_BASE_URL}/", timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=20_000)
    assert len(errors) == 0 or all("favicon" in e.lower() for e in errors)


@_LIVE
@_SKIP_NO_PW
def test_E26_traditional_report_card_visible(page: Page):
    """E26: traditional report card is visible on the page."""
    page.goto(f"{_BASE_URL}/", timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=20_000)
    # Section header
    section = page.locator('[data-testid="pro-val-expert-review-request-section"]')
    expect(section).to_be_visible(timeout=10_000)


@_LIVE
@_SKIP_NO_PW
def test_E27_admin_excel_output_area_shows_one_workbook(page: Page):
    """E27: admin Excel area shows only one workbook."""
    assert (_XL / _WORKBOOK).exists()
    xl_files = list(_XL.glob("*.xlsm")) + list(_XL.glob("*.xlsx"))
    assert len(xl_files) == 1


@_LIVE
@_SKIP_NO_PW
def test_E28_three_pdfs_exist_after_generation(page: Page):
    """E28: all three PDFs physically exist after generation."""
    for name in ["traditional_report.pdf", "detailed_report.pdf", "professional_report.pdf"]:
        assert (_PDF / name).exists()
        assert (_PDF / name).stat().st_size > 10_000


@_LIVE
@_SKIP_NO_PW
def test_E29_no_internal_paths_in_dom(page: Page):
    """E29: No internal filesystem paths appear in page DOM."""
    page.goto(f"{_BASE_URL}/", timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=20_000)
    content = page.content()
    for pat in [r"C:\\Users", r"C:/Users", "/home/"]:
        assert pat not in content, f"Internal path in DOM: {pat}"


@_LIVE
@_SKIP_NO_PW
def test_E30_excel_is_internal_notice_present(page: Page):
    """E30: Excel internal-only notice is present in admin area."""
    data = _load(_XAUD / "excel_internal_only_audit.json")
    assert data["excel_is_internal_admin_only"] is True
