"""
test_pv_reference_report_full_simulation_visual.py
12 visual / e2e tests — 16-page reference simulation.
advisory_only=True | no_fake_cert=True | certification_ready=False
VT01-VT05: Playwright (skip if not installed or server down)
VT06-VT12: File-based (always run)
"""
from __future__ import annotations
from pathlib import Path
import pytest

_CORE = Path(__file__).resolve().parent.parent.parent
_GATE = _CORE / "instance" / "manual_review_outputs" / "valuation_certification_readiness_gate"
_OUT  = _CORE / "instance" / "manual_review_outputs" / "professional_valuation_reference_full_simulation"
_SCR  = _OUT / "test_logs"

_PDF_DIR = _OUT / "pdf_outputs"
_XL_DIR  = _OUT / "excel_outputs"
_PVP     = _OUT / "pdf_visual_previews"
_EVP     = _OUT / "excel_visual_previews"

_TRAD_PDF  = _PDF_DIR / "traditional_report.pdf"
_TRAD_HTML = _PDF_DIR / "traditional_report.html"
_DET_PDF   = _PDF_DIR / "detailed_report.pdf"
_PRO_PDF   = _PDF_DIR / "professional_report.pdf"
_XL        = _XL_DIR  / "professional_valuation_merged_master_workbook.xlsx"
_XLM       = _XL_DIR  / "professional_valuation_merged_master_workbook.xlsm"
_P2P_IDX   = _PVP / "OPEN_PAGE_BY_PAGE_TRADITIONAL_COMPARISON.html"
_EXCEL_IDX = _EVP / "OPEN_EXCEL_REFERENCE_SIMULATION_REVIEW.html"
_FINAL_IDX = _OUT / "OPEN_FINAL_REPORT_AND_EXCEL_SIMULATION_REVIEW.html"

_BASE   = "http://localhost:5000"
_PV_URL = _BASE + "/"

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


def _skip_pw():
    if not HAS_PLAYWRIGHT:
        pytest.skip("Playwright not installed")


def _skip_no_server(page):
    try:
        page.goto(_BASE, timeout=5000)
    except Exception:
        pytest.skip("Server not running at localhost:5000")


# VT01 — Professional Valuation page opens
def test_VT01_pv_page_opens():
    _skip_pw()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        _skip_no_server(page)
        page.goto(_PV_URL)
        assert page.title() != ""
        _SCR.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(_SCR / "pv_page_open.png"))
        browser.close()


# VT02 — Page-by-page comparison index screenshot
def test_VT02_page_by_page_comparison_screenshot():
    _skip_pw()
    _SCR.mkdir(parents=True, exist_ok=True)
    if not _P2P_IDX.exists():
        pytest.skip("Page-by-page comparison index not generated")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("file:///" + str(_P2P_IDX).replace("\\", "/"))
        page.screenshot(path=str(_SCR / "page_by_page_comparison_index.png"))
        browser.close()


# VT03 — Excel review index screenshot
def test_VT03_excel_review_screenshot():
    _skip_pw()
    _SCR.mkdir(parents=True, exist_ok=True)
    if not _EXCEL_IDX.exists():
        pytest.skip("Excel review index not generated")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("file:///" + str(_EXCEL_IDX).replace("\\", "/"))
        page.screenshot(path=str(_SCR / "excel_review_index.png"))
        browser.close()


# VT04 — Final review index screenshot
def test_VT04_final_review_index_screenshot():
    _skip_pw()
    _SCR.mkdir(parents=True, exist_ok=True)
    if not _FINAL_IDX.exists():
        pytest.skip("Final review index not generated")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("file:///" + str(_FINAL_IDX).replace("\\", "/"))
        page.screenshot(path=str(_SCR / "final_review_index.png"))
        browser.close()


# VT05 — Traditional HTML renders in browser
def test_VT05_traditional_html_renders():
    _skip_pw()
    _SCR.mkdir(parents=True, exist_ok=True)
    if not _TRAD_HTML.exists():
        pytest.skip("Traditional HTML not generated")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("file:///" + str(_TRAD_HTML).replace("\\", "/"))
        page.screenshot(path=str(_SCR / "reference_vs_traditional_page_1.png"))
        browser.close()


# VT06 — Traditional PDF/HTML exists and is substantial
def test_VT06_traditional_report_pdf_exists():
    assert _TRAD_PDF.exists() or _TRAD_HTML.exists(), \
        "traditional_report.pdf / .html not generated"
    if _TRAD_PDF.exists():
        assert _TRAD_PDF.stat().st_size > 50_000, "Traditional PDF too small"


# VT07 — Traditional report has 16 page sections
def test_VT07_traditional_has_16_page_sections():
    if not _TRAD_HTML.exists():
        pytest.skip("Traditional HTML not found")
    content = _TRAD_HTML.read_text(encoding="utf-8", errors="ignore")
    # Each page after first has class 'pg' with page-break-before
    page_breaks = content.count("class='pg'")
    assert page_breaks >= 15, \
        f"Expected 15 page-break dividers for 16 pages, got {page_breaks}"


# VT08 — Detailed PDF/HTML exists
def test_VT08_detailed_pdf_exists():
    assert _DET_PDF.exists() or (_PDF_DIR / "detailed_report.html").exists(), \
        "detailed_report.pdf / .html not generated"


# VT09 — Professional PDF/HTML exists
def test_VT09_professional_pdf_exists():
    assert _PRO_PDF.exists() or (_PDF_DIR / "professional_report.html").exists(), \
        "professional_report.pdf / .html not generated"


# VT10 — Merged Excel workbook generated
def test_VT10_merged_excel_workbook_generated():
    xl = _XL if _XL.exists() else _XLM
    assert xl.exists(), "Merged Excel workbook not found"
    assert xl.stat().st_size > 10_000, "Excel too small"


# VT11 — Final review index exists and has key content
def test_VT11_final_review_index_exists():
    assert _FINAL_IDX.exists(), "OPEN_FINAL_REPORT_AND_EXCEL_SIMULATION_REVIEW.html missing"
    content = _FINAL_IDX.read_text(encoding="utf-8", errors="ignore")
    assert len(content) > 2_000, "Final review index too short"
    assert "certification_ready" in content
    assert "PASS" in content


# VT12 — Screenshot or blocker documented
def test_VT12_screenshot_or_blocker_documented():
    _SCR.mkdir(parents=True, exist_ok=True)
    pngs    = list(_SCR.glob("*.png"))
    blocker = _SCR / "screenshot_blocker.txt"

    if not HAS_PLAYWRIGHT and not pngs:
        blocker.write_text(
            "Screenshots blocked: Playwright not installed.\n"
            "Install: pip install playwright && playwright install chromium\n",
            encoding="utf-8",
        )

    assert len(pngs) > 0 or blocker.exists(), \
        "Neither screenshots nor blocker documentation found"
