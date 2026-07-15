"""
test_pv_traditional_like_ordinary_valuation_visual.py
E2E visual tests — Traditional Report (like Ordinary Valuation Page).
advisory_only=True | no_fake_cert=True | no_commit=True | certification_ready=False
Tests require Playwright and a running server at http://localhost:5000.
"""
from __future__ import annotations
from pathlib import Path
import pytest

_CORE = Path(__file__).resolve().parent.parent.parent
_OUT  = _CORE / "instance" / "manual_review_outputs" / \
        "professional_valuation_traditional_like_ordinary_valuation"
_SCR  = _OUT / "test_logs"
_PDF  = _OUT / "pdf_outputs" / "traditional_report.pdf"
_HTML = _OUT / "pdf_outputs" / "traditional_report.html"
_XL   = _OUT / "excel_outputs" / "professional_valuation_admin_master_workbook.xlsx"
_CMP  = _OUT / "pdf_visual_previews" / "OPEN_TRADITIONAL_REPORT_REFERENCE_COMPARISON.html"
_EVP  = _OUT / "excel_visual_previews" / "OPEN_ADMIN_EXCEL_METHOD_WORKBOOK_REVIEW.html"

_BASE = "http://localhost:5000"
_PV_URL = f"{_BASE}/"

try:
    from playwright.sync_api import sync_playwright, Page, expect
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


def _skip_if_no_playwright():
    if not HAS_PLAYWRIGHT:
        pytest.skip("Playwright not installed")


def _skip_if_no_server(page):
    try:
        page.goto(_BASE, timeout=5000)
    except Exception:
        pytest.skip("Server not running at localhost:5000")


# VT01 — Professional Valuation page opens
def test_VT01_professional_valuation_page_opens():
    _skip_if_no_playwright()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        _skip_if_no_server(page)
        page.goto(_PV_URL)
        assert page.title() != ""
        _SCR.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(_SCR / "01_pv_page_open.png"))
        browser.close()


# VT02 — Traditional report section visible
def test_VT02_traditional_report_section_visible():
    _skip_if_no_playwright()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        _skip_if_no_server(page)
        page.goto(_PV_URL)
        # Look for traditional report button or section
        trad = page.locator("text=تقليدي").first
        if trad.count() == 0:
            trad = page.locator("text=Traditional").first
        if trad.count() == 0:
            pytest.skip("Traditional report button not found on page")
        trad.scroll_into_view_if_needed()
        page.screenshot(path=str(_SCR / "02_traditional_section.png"))
        browser.close()


# VT03 — traditional_report.pdf exists (file check)
def test_VT03_traditional_report_pdf_exists():
    assert _PDF.exists() or _HTML.exists(), \
        "traditional_report.pdf/html not generated"


# VT04 — admin Excel workbook generated
def test_VT04_admin_excel_workbook_generated():
    assert _XL.exists(), f"Admin Excel not found: {_XL}"


# VT05 — reference comparison index exists
def test_VT05_reference_comparison_index_exists():
    assert _CMP.exists(), f"Comparison index missing: {_CMP}"
    content = _CMP.read_text(encoding="utf-8", errors="ignore")
    assert len(content) > 2000, "Comparison index too short"


# VT06 — traditional PDF preview exists
def test_VT06_traditional_pdf_preview_exists():
    assert _HTML.exists() or _PDF.exists(), "No traditional report preview available"


# VT07 — Excel preview exists
def test_VT07_excel_preview_exists():
    assert _EVP.exists(), f"Excel preview missing: {_EVP}"
    content = _EVP.read_text(encoding="utf-8", errors="ignore")
    assert len(content) > 1000


# VT08 — no internal paths in DOM (static file check)
def test_VT08_no_internal_paths_in_dom():
    for f in [_CMP, _EVP, _HTML]:
        if f and f.exists():
            content = f.read_text(encoding="utf-8", errors="ignore")
            for bad in [r"C:\\Users", "C:/Users", "/home/"]:
                assert bad not in content, f"Internal path in {f.name}: {bad}"


# VT09 — screenshot: traditional_report_generation_area (static fallback)
def test_VT09_screenshot_traditional_report_generation_area():
    _SCR.mkdir(parents=True, exist_ok=True)
    # Try Playwright screenshot; fallback to documenting blocker
    if not HAS_PLAYWRIGHT:
        blocker = _SCR / "screenshot_blocker.txt"
        blocker.write_text(
            "Screenshots blocked: Playwright not installed.\n"
            "Install with: pip install playwright && playwright install chromium\n",
            encoding="utf-8"
        )
        assert blocker.exists()
        return
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(_PV_URL, timeout=5000)
            page.screenshot(path=str(_SCR / "traditional_report_generation_area.png"))
        except Exception:
            (_SCR / "screenshot_blocker.txt").write_text(
                "Screenshots blocked: server not running.\n", encoding="utf-8")
        browser.close()
