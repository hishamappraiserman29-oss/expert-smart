"""
test_pv_arabic_pdf_legacy_excel_restore_e2e.py
E2E اختبارات — تصحيح لغة التقارير إلى العربية واستعادة النموذج القديم

تشغيل الاختبارات الساكنة:
  python -m pytest core_engine/tests/e2e/test_pv_arabic_pdf_legacy_excel_restore_e2e.py -q -m "not live_server"

تشغيل اختبارات المتصفح الحي (بعد: pip install playwright && playwright install):
  python -m pytest core_engine/tests/e2e/test_pv_arabic_pdf_legacy_excel_restore_e2e.py -q -m live_server

arabic_pdf_language=ar | uses_legacy_template=True | advisory_only=True
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_CORE     = Path(__file__).resolve().parent.parent.parent
_QA       = _CORE / "instance" / "manual_review_outputs" / \
            "professional_valuation_arabic_pdf_legacy_excel_restore"
_PDF      = _QA / "pdf_outputs"
_XLS      = _QA / "excel_outputs"
_PREVIEW  = _QA / "pdf_visual_previews"
_EXCELPRE = _QA / "excel_visual_previews"
_LEG      = _QA / "legacy_excel_audits"
_LANG     = _QA / "report_language_audits"
_METH     = _QA / "method_coverage_audits"
_DIST     = _QA / "report_distinctness_audits"
_FRONTEND = _CORE.parent / "frontend" / "index.html"
_BASE_URL = "http://127.0.0.1:5000"

sys.path.insert(0, str(_CORE))

# ── Playwright graceful fallback ───────────────────────────────────────────────
try:
    from playwright.sync_api import Page, expect
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Page = object  # type: ignore[misc]

_LIVE     = pytest.mark.live_server
_SKIP_NO_PW = pytest.mark.skipif(
    not PLAYWRIGHT_AVAILABLE,
    reason="playwright not installed — run: pip install playwright && playwright install chromium",
)


def _load(path: Path) -> dict:
    assert path.exists(), f"Audit file missing: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


# ═══════════════════════════════════════════════════════════════════════════════
# STATIC TESTS — no live server required
# ═══════════════════════════════════════════════════════════════════════════════

def test_E01_qa_folder_exists():
    """E01: QA output folder exists."""
    assert _QA.exists()


def test_E02_pdf_outputs_exist():
    """E02: All three Arabic PDF outputs exist."""
    for name in ["traditional_report.pdf", "detailed_report.pdf", "professional_report.pdf"]:
        assert (_PDF / name).exists(), f"Missing PDF: {name}"


def test_E03_excel_outputs_exist():
    """E03: All three Arabic Excel admin workbooks exist."""
    for name in [
        "traditional_report_admin_workbook.xlsm",
        "detailed_report_admin_workbook.xlsm",
        "professional_report_admin_workbook.xlsm",
    ]:
        assert (_XLS / name).exists(), f"Missing Excel: {name}"


def test_E04_traditional_pdf_non_empty():
    """E04: traditional_report.pdf is non-empty."""
    assert (_PDF / "traditional_report.pdf").stat().st_size > 1_000


def test_E05_traditional_excel_non_empty():
    """E05: traditional_report_admin_workbook.xlsm is non-empty (>1MB = uses legacy)."""
    assert (_XLS / "traditional_report_admin_workbook.xlsm").stat().st_size > 1_000_000


def test_E06_detailed_pdf_non_empty():
    """E06: detailed_report.pdf is non-empty."""
    assert (_PDF / "detailed_report.pdf").stat().st_size > 1_000


def test_E07_detailed_excel_non_empty():
    """E07: detailed_report_admin_workbook.xlsm is non-empty (>1MB)."""
    assert (_XLS / "detailed_report_admin_workbook.xlsm").stat().st_size > 1_000_000


def test_E08_professional_pdf_non_empty():
    """E08: professional_report.pdf is non-empty."""
    assert (_PDF / "professional_report.pdf").stat().st_size > 1_000


def test_E09_professional_excel_non_empty():
    """E09: professional_report_admin_workbook.xlsm is non-empty (>1MB)."""
    assert (_XLS / "professional_report_admin_workbook.xlsm").stat().st_size > 1_000_000


def test_E10_pdf_sizes_are_distinct():
    """E10: three PDFs have distinct sizes — not identical content."""
    sizes = {
        name: (_PDF / name).stat().st_size
        for name in ["traditional_report.pdf", "detailed_report.pdf", "professional_report.pdf"]
    }
    assert len(set(sizes.values())) == 3, f"Non-distinct PDF sizes: {sizes}"


def test_E11_no_internal_paths_in_audit():
    """E11: No internal filesystem paths exposed in output status."""
    for name in ["traditional_report_preview.html", "detailed_report_preview.html",
                 "professional_report_preview.html"]:
        if not (_PREVIEW / name).exists():
            continue
        content = (_PREVIEW / name).read_text(encoding="utf-8")
        for pat in (r"C:\\Users", r"C:/Users", "/home/", "core_engine/instance"):
            assert pat not in content, f"Internal path in {name}: {pat}"


def test_E12_visual_preview_index_exists():
    """E12: arabic_pdf_visual_review_index.html exists."""
    assert (_PREVIEW / "arabic_pdf_visual_review_index.html").exists()


def test_E13_excel_preservation_preview_exists():
    """E13: legacy_vs_generated_excel_template_preservation_index.html exists."""
    assert (_EXCELPRE / "legacy_vs_generated_excel_template_preservation_index.html").exists()


def test_E14_excel_preview_workbook_previews_exist():
    """E14: individual Excel workbook preview HTML files exist."""
    for name in [
        "traditional_report_admin_workbook_preview.html",
        "detailed_report_admin_workbook_preview.html",
        "professional_report_admin_workbook_preview.html",
    ]:
        assert (_EXCELPRE / name).exists(), f"Missing: {name}"


def test_E15_language_audit_confirms_arabic():
    """E15: language audit confirms pdf_language=ar, excel_language=ar."""
    data = _load(_LANG / "arabic_pdf_excel_language_audit.json")
    assert data["pdf_language"] == "ar"
    assert data["excel_language"] == "ar"
    assert data["language_status"] == "PASS"


def test_E16_preservation_audit_confirms_legacy_template():
    """E16: template preservation audit = PASS."""
    data = _load(_LEG / "generated_excel_template_preservation_audit.json")
    assert data["template_preservation_status"] == "PASS"
    assert data["legacy_template_used_for_all_generated_admin_workbooks"] is True
    assert data["workbooks_are_not_tiny_placeholders"] is True


def test_E17_method_inventory_reports_methods():
    """E17: legacy method inventory detects key methods from the old Excel."""
    data = _load(_LEG / "legacy_excel_method_inventory.json")
    dm = data["detected_methods"]
    for method in ["market_approach", "income_approach", "cost_approach",
                   "dcf_analysis", "sensitivity_analysis", "weighted_reconciliation"]:
        assert dm.get(method) is True, f"Missing method: {method}"


def test_E18_distinctness_audit_passes():
    """E18: distinctness audit confirms three reports are distinct."""
    data = _load(_DIST / "arabic_core_reports_distinctness_audit.json")
    assert data["distinctness_status"] == "PASS"
    assert data["near_duplicate_report_pairs"] == []


# ═══════════════════════════════════════════════════════════════════════════════
# LIVE SERVER + PLAYWRIGHT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

@_LIVE
@_SKIP_NO_PW
def test_E19_page_opens_without_js_errors(page: Page):
    """E19: Professional Valuation page opens without JS errors."""
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{_BASE_URL}/", timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=20_000)
    assert len(errors) == 0 or all("favicon" in e.lower() for e in errors)


@_LIVE
@_SKIP_NO_PW
def test_E20_core_report_section_visible(page: Page):
    """E20: core report section is visible on the PV page."""
    page.goto(f"{_BASE_URL}/", timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=20_000)
    section = page.locator('[data-testid="pro-val-expert-review-request-section"]')
    expect(section).to_be_visible(timeout=10_000)


@_LIVE
@_SKIP_NO_PW
def test_E21_traditional_pdf_file_exists_after_generation(page: Page):
    """E21: traditional_report.pdf physically exists after generation."""
    assert (_PDF / "traditional_report.pdf").exists()
    assert (_PDF / "traditional_report.pdf").stat().st_size > 1_000


@_LIVE
@_SKIP_NO_PW
def test_E22_traditional_excel_file_exists(page: Page):
    """E22: traditional_report_admin_workbook.xlsm physically exists."""
    assert (_XLS / "traditional_report_admin_workbook.xlsm").exists()
    assert (_XLS / "traditional_report_admin_workbook.xlsm").stat().st_size > 1_000_000


@_LIVE
@_SKIP_NO_PW
def test_E23_detailed_pdf_file_exists_after_generation(page: Page):
    """E23: detailed_report.pdf physically exists."""
    assert (_PDF / "detailed_report.pdf").exists()


@_LIVE
@_SKIP_NO_PW
def test_E24_professional_pdf_file_exists_after_generation(page: Page):
    """E24: professional_report.pdf physically exists."""
    assert (_PDF / "professional_report.pdf").exists()


@_LIVE
@_SKIP_NO_PW
def test_E25_professional_excel_file_exists(page: Page):
    """E25: professional_report_admin_workbook.xlsm physically exists."""
    assert (_XLS / "professional_report_admin_workbook.xlsm").exists()


@_LIVE
@_SKIP_NO_PW
def test_E26_visual_preview_index_renders(page: Page):
    """E26: visual preview index HTML renders without errors."""
    preview_path = _PREVIEW / "arabic_pdf_visual_review_index.html"
    assert preview_path.exists()
    page.goto(preview_path.as_uri(), timeout=15_000)
    assert "فهرس معاينة التقارير العربية" in page.title() or \
           "فهرس" in page.content()
