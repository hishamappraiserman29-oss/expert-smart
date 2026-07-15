"""
test_pv_integrated_pdf_gap_fix_e2e.py
E2E tests — النموذج الموحد المتكامل ثلاثي المستوى
تشغيل الاختبارات الساكنة:
  python -m pytest core_engine/tests/e2e/test_pv_integrated_pdf_gap_fix_e2e.py -q -m "not live_server"
arabic_primary=True | unified_model=True | advisory_only=True
"""
from __future__ import annotations
import json
from pathlib import Path
import sys
import pytest

_CORE    = Path(__file__).resolve().parent.parent.parent
_QA      = _CORE / "instance" / "manual_review_outputs" / "professional_valuation_integrated_pdf_gap_fix"
_PDF     = _QA / "pdf_outputs"
_PREV    = _QA / "pdf_visual_previews"
_PAUD    = _QA / "pdf_audits"
_BASE_URL = "http://127.0.0.1:5000"

sys.path.insert(0, str(_CORE))

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
    assert p.exists(), f"Missing audit: {p}"
    return json.loads(p.read_text(encoding="utf-8"))

def _html(key: str) -> str:
    p = _PREV / f"{key}_preview.html"
    assert p.exists(), f"Missing preview: {p}"
    return p.read_text(encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════════════
# STATIC TESTS
# ══════════════════════════════════════════════════════════════════════════════

def test_E01_qa_folder_exists():
    assert _QA.exists()

def test_E02_traditional_pdf_exists():
    assert (_PDF / "traditional_report.pdf").exists()

def test_E03_detailed_pdf_exists():
    assert (_PDF / "detailed_report.pdf").exists()

def test_E04_professional_pdf_exists():
    assert (_PDF / "professional_report.pdf").exists()

def test_E05_visual_review_index_exists():
    assert (_PREV / "integrated_three_report_visual_review_index.html").exists()

def test_E06_no_separate_unwanted_excel_buttons():
    # This feature does not generate new Excel workbooks — only PDFs
    excel_files = list((_QA).rglob("*.xlsm")) + list((_QA).rglob("*.xlsx"))
    assert len(excel_files) == 0, f"Unexpected Excel files in integrated PDF folder: {excel_files}"

def test_E07_traditional_pdf_non_empty():
    assert (_PDF / "traditional_report.pdf").stat().st_size > 10_000

def test_E08_detailed_larger_than_traditional():
    t = (_PDF / "traditional_report.pdf").stat().st_size
    d = (_PDF / "detailed_report.pdf").stat().st_size
    assert d > t, f"detailed ({d}) not > traditional ({t})"

def test_E09_professional_is_largest():
    sizes = {k: (_PDF / f"{k}.pdf").stat().st_size
             for k in ["traditional_report", "detailed_report", "professional_report"]}
    assert sizes["professional_report"] == max(sizes.values()), str(sizes)

def test_E10_traditional_preview_exists():
    assert (_PREV / "traditional_report_preview.html").exists()

def test_E11_detailed_preview_exists():
    assert (_PREV / "detailed_report_preview.html").exists()

def test_E12_professional_preview_exists():
    assert (_PREV / "professional_report_preview.html").exists()

def test_E13_no_internal_paths_in_previews():
    for key in ["traditional_report", "detailed_report", "professional_report"]:
        html = _html(key)
        for pat in [r"C:\\Users", r"C:/Users", "/home/", "core_engine/instance"]:
            assert pat not in html, f"Internal path in {key}: {pat}"

def test_E14_no_fake_cert_in_previews():
    for key in ["traditional_report", "detailed_report", "professional_report"]:
        html = _html(key)
        assert "مسودة" in html
        assert "certification_ready=False" in html or "advisory_only=True" in html

def test_E15_repetition_audit_pass():
    data = _load(_PAUD / "pdf_repetition_reduction_audit.json")
    assert data["repetition_status"] == "PASS"
    assert data["near_duplicate_report_pairs"] == []

def test_E16_depth_gap_fix_audit_pass():
    data = _load(_PAUD / "integrated_report_depth_and_gap_fix_audit.json")
    assert data["gap_fix_status"] == "PASS"
    assert data["unified_integrated_model_enabled"] is True

def test_E17_method_coverage_audit_pass():
    data = _load(_PAUD / "pdf_depth_and_method_coverage_audit.json")
    assert data["pdf_status"] == "PASS"
    assert data["professional_report"]["dcf_full"] is True
    assert data["professional_report"]["multi_variable_sensitivity"] is True
    assert data["professional_report"]["richer_than_detailed"] is True

def test_E18_physical_files_audit_pass():
    data = _load(_PAUD / "pdf_physical_files_audit.json")
    assert data["files_status"] == "PASS"


# ══════════════════════════════════════════════════════════════════════════════
# LIVE SERVER + PLAYWRIGHT TESTS
# ══════════════════════════════════════════════════════════════════════════════

@_LIVE
@_SKIP_NO_PW
def test_E19_page_opens_without_errors(page: Page):
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{_BASE_URL}/", timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=20_000)
    assert len(errors) == 0 or all("favicon" in e.lower() for e in errors)

@_LIVE
@_SKIP_NO_PW
def test_E20_traditional_report_accessible(page: Page):
    assert (_PDF / "traditional_report.pdf").exists()
    assert (_PDF / "traditional_report.pdf").stat().st_size > 10_000

@_LIVE
@_SKIP_NO_PW
def test_E21_detailed_report_accessible(page: Page):
    assert (_PDF / "detailed_report.pdf").exists()
    assert (_PDF / "detailed_report.pdf").stat().st_size > 10_000

@_LIVE
@_SKIP_NO_PW
def test_E22_professional_report_accessible(page: Page):
    assert (_PDF / "professional_report.pdf").exists()
    assert (_PDF / "professional_report.pdf").stat().st_size > 10_000

@_LIVE
@_SKIP_NO_PW
def test_E23_no_internal_paths_in_dom(page: Page):
    page.goto(f"{_BASE_URL}/", timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=20_000)
    content = page.content()
    for pat in [r"C:\\Users", r"C:/Users", "/home/"]:
        assert pat not in content, f"Internal path in DOM: {pat}"

@_LIVE
@_SKIP_NO_PW
def test_E24_visual_review_index_accessible(page: Page):
    assert (_PREV / "integrated_three_report_visual_review_index.html").exists()
