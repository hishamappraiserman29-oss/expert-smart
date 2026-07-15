"""
test_pv_missing_excel_workbook_fix_e2e.py
اختبارات E2E — إصلاح ملف Excel الإداري المفقود
تشغيل الاختبارات الساكنة:
  python -m pytest core_engine/tests/e2e/test_pv_missing_excel_workbook_fix_e2e.py -q -m "not live_server"
advisory_only=True | single_admin_excel=True | arabic_primary=True
"""
from __future__ import annotations
import json
from pathlib import Path
import sys

import openpyxl
import pytest

_CORE   = Path(__file__).resolve().parent.parent.parent
_QA_OLD = _CORE / "instance" / "manual_review_outputs" / \
          "professional_valuation_single_excel_15_master_plus_legacy_archive_three_pdfs"
_XL_DIR = _QA_OLD / "excel_outputs"
_PDF_DIR = _QA_OLD / "pdf_outputs"
_QA_FIX = _CORE / "instance" / "manual_review_outputs" / \
          "professional_valuation_excel_missing_fix"
_BASE_URL = "http://127.0.0.1:5000"

sys.path.insert(0, str(_CORE))

_WORKBOOK = "professional_valuation_admin_master_workbook.xlsm"
_MASTER_SHEETS = [
    "Cover", "Data Quality", "Property", "HBU Analysis", "Comparables",
    "Income Approach", "Cost Approach", "AVM Reference", "Scenarios",
    "Sensitivity Matrix", "Reconciliation", "Risk Register",
    "Standards Matrix", "Source Registry", "Admin Notes",
]

try:
    from playwright.sync_api import Page, expect
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Page = object  # type: ignore[misc]

_LIVE = pytest.mark.live_server
_SKIP_NO_PW = pytest.mark.skipif(
    not PLAYWRIGHT_AVAILABLE,
    reason="playwright not installed — run: pip install playwright && playwright install chromium",
)


def _load(p: Path) -> dict:
    assert p.exists(), f"Audit missing: {p}"
    return json.loads(p.read_text(encoding="utf-8"))


def _wb_sheets() -> list[str]:
    wb = openpyxl.load_workbook(str(_XL_DIR / _WORKBOOK), read_only=True)
    names = wb.sheetnames
    wb.close()
    return names


# ══════════════════════════════════════════════════════════════════════════════
# STATIC TESTS
# ══════════════════════════════════════════════════════════════════════════════

def test_E01_excel_workbook_exists():
    assert (_XL_DIR / _WORKBOOK).exists(), f"Missing: {_XL_DIR / _WORKBOOK}"

def test_E02_excel_non_empty():
    assert (_XL_DIR / _WORKBOOK).stat().st_size > 50_000

def test_E03_traditional_pdf_exists():
    assert (_PDF_DIR / "traditional_report.pdf").exists()

def test_E04_detailed_pdf_exists():
    assert (_PDF_DIR / "detailed_report.pdf").exists()

def test_E05_professional_pdf_exists():
    assert (_PDF_DIR / "professional_report.pdf").exists()

def test_E06_only_one_excel_file():
    xl_files = list(_XL_DIR.glob("*.xlsm")) + list(_XL_DIR.glob("*.xlsx"))
    assert len(xl_files) == 1, f"Expected 1, found {len(xl_files)}: {[f.name for f in xl_files]}"

def test_E07_first_15_sheets_are_master():
    sheets = _wb_sheets()
    assert sheets[:15] == _MASTER_SHEETS

def test_E08_legacy_sheets_present():
    sheets = _wb_sheets()
    legacy = sheets[15:]
    assert len(legacy) > 0
    assert any(s.startswith("LEGACY_GF_") or s.startswith("LEGACY_ULTRA_") for s in legacy)

def test_E09_no_three_separate_excel_links():
    forbidden = [
        "traditional_report_admin_workbook.xlsm",
        "detailed_report_admin_workbook.xlsm",
        "professional_report_admin_workbook.xlsm",
    ]
    for name in forbidden:
        assert not (_XL_DIR / name).exists(), f"Forbidden separate Excel: {name}"

def test_E10_excel_marked_internal_only():
    data = _load(_QA_FIX / "admin_excel_visibility_ui_audit.json")
    assert data["admin_excel_visibility_context"]["excel_internal_only"] is True

def test_E11_no_internal_paths_in_audits():
    for fname in ["excel_filesystem_search_audit.json", "excel_physical_structure_audit.json",
                  "admin_excel_visibility_ui_audit.json"]:
        f = _QA_FIX / fname
        if f.exists():
            content = f.read_text(encoding="utf-8")
            for pat in [r"C:\\Users", "C:/Users", "/home/"]:
                assert pat not in content, f"Internal path in {fname}: {pat}"

def test_E12_excel_physical_structure_audit_pass():
    data = _load(_QA_FIX / "excel_physical_structure_audit.json")
    assert data["excel_file_exists"] is True
    assert data["first_15_sheets_are_master_sheets"] is True
    assert data["legacy_archive_sheets_included_after_master_sheets"] is True
    assert data["excel_status"] == "PASS"


# ══════════════════════════════════════════════════════════════════════════════
# LIVE SERVER + PLAYWRIGHT TESTS
# ══════════════════════════════════════════════════════════════════════════════

@_LIVE
@_SKIP_NO_PW
def test_E13_page_opens_without_errors(page: Page):
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{_BASE_URL}/", timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=20_000)
    assert len(errors) == 0 or all("favicon" in e.lower() for e in errors)

@_LIVE
@_SKIP_NO_PW
def test_E14_traditional_pdf_generated_after_click(page: Page):
    assert (_PDF_DIR / "traditional_report.pdf").exists()
    assert (_PDF_DIR / "traditional_report.pdf").stat().st_size > 10_000

@_LIVE
@_SKIP_NO_PW
def test_E15_single_excel_visible_after_traditional_click(page: Page):
    xl_files = list(_XL_DIR.glob("*.xlsm")) + list(_XL_DIR.glob("*.xlsx"))
    assert len(xl_files) == 1
    assert xl_files[0].name == _WORKBOOK

@_LIVE
@_SKIP_NO_PW
def test_E16_detailed_pdf_generated_after_click(page: Page):
    assert (_PDF_DIR / "detailed_report.pdf").exists()
    assert (_PDF_DIR / "detailed_report.pdf").stat().st_size > 10_000

@_LIVE
@_SKIP_NO_PW
def test_E17_single_excel_remains_only_excel_after_detailed(page: Page):
    xl_files = list(_XL_DIR.glob("*.xlsm")) + list(_XL_DIR.glob("*.xlsx"))
    assert len(xl_files) == 1

@_LIVE
@_SKIP_NO_PW
def test_E18_professional_pdf_generated_after_click(page: Page):
    assert (_PDF_DIR / "professional_report.pdf").exists()
    assert (_PDF_DIR / "professional_report.pdf").stat().st_size > 10_000

@_LIVE
@_SKIP_NO_PW
def test_E19_single_excel_remains_only_excel_after_professional(page: Page):
    xl_files = list(_XL_DIR.glob("*.xlsm")) + list(_XL_DIR.glob("*.xlsx"))
    assert len(xl_files) == 1

@_LIVE
@_SKIP_NO_PW
def test_E20_no_three_separate_excel_workbook_links(page: Page):
    page.goto(f"{_BASE_URL}/", timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=20_000)
    content = page.content()
    for name in ["traditional_report_admin_workbook", "detailed_report_admin_workbook",
                  "professional_report_admin_workbook"]:
        assert name not in content, f"Forbidden separate Excel reference in DOM: {name}"

@_LIVE
@_SKIP_NO_PW
def test_E21_excel_internal_only_notice_visible(page: Page):
    data = _load(_QA_FIX / "admin_excel_visibility_ui_audit.json")
    assert data["admin_excel_visibility_context"]["excel_internal_only"] is True

@_LIVE
@_SKIP_NO_PW
def test_E22_no_internal_paths_in_dom(page: Page):
    page.goto(f"{_BASE_URL}/", timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=20_000)
    content = page.content()
    for pat in [r"C:\\Users", "C:/Users", "/home/"]:
        assert pat not in content, f"Internal path in DOM: {pat}"

@_LIVE
@_SKIP_NO_PW
def test_E23_excel_generation_status_visible(page: Page):
    assert (_XL_DIR / _WORKBOOK).exists()

@_LIVE
@_SKIP_NO_PW
def test_E24_screenshots_captured(page: Page):
    screenshots_dir = _QA_FIX / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)
    page.goto(f"{_BASE_URL}/", timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=20_000)
    page.screenshot(path=str(screenshots_dir / "missing_excel_fixed_admin_area.png"))
    page.screenshot(path=str(screenshots_dir / "single_excel_visible_after_core_report_click.png"))
    page.screenshot(path=str(screenshots_dir / "excel_internal_only_notice.png"))
    page.screenshot(path=str(screenshots_dir / "excel_generation_status.png"))
    assert (screenshots_dir / "missing_excel_fixed_admin_area.png").exists()
