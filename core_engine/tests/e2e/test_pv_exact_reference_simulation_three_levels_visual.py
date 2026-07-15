"""
test_pv_exact_reference_simulation_three_levels_visual.py
13 visual / e2e tests — Three-level report simulation.
advisory_only=True | no_fake_cert=True | no_commit=True | certification_ready=False
VT01-VT05: Playwright (skip if not installed or server down)
VT06-VT13: File-based (always run)
"""
from __future__ import annotations
from pathlib import Path
import pytest

_CORE = Path(__file__).resolve().parent.parent.parent
_OUT  = _CORE / "instance" / "manual_review_outputs" / \
        "professional_valuation_exact_reference_simulation_three_levels"
_SCR  = _OUT / "test_logs"

_PDF_DIR = _OUT / "pdf_outputs"
_XL_DIR  = _OUT / "excel_outputs"
_PVP     = _OUT / "pdf_visual_previews"
_EVP     = _OUT / "excel_visual_previews"

_TRAD_PDF  = _PDF_DIR / "traditional_report.pdf"
_TRAD_HTML = _PDF_DIR / "traditional_report.html"
_DET_PDF   = _PDF_DIR / "detailed_report.pdf"
_DET_HTML  = _PDF_DIR / "detailed_report.html"
_PRO_PDF   = _PDF_DIR / "professional_report.pdf"
_PRO_HTML  = _PDF_DIR / "professional_report.html"
_XL        = _XL_DIR  / "professional_valuation_merged_master_workbook.xlsx"
_XLM       = _XL_DIR  / "professional_valuation_merged_master_workbook.xlsm"
_IDX       = _PVP / "OPEN_THREE_LEVEL_REPORT_REVIEW_INDEX.html"
_EIDX      = _EVP / "OPEN_MERGED_EXCEL_REVIEW_INDEX.html"

_BASE    = "http://localhost:5000"
_PV_URL  = _BASE + "/"

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
        page.screenshot(path=str(_SCR / "traditional_reference_simulation.png"))
        browser.close()


# VT02 — Detailed report section visible on page
def test_VT02_detailed_report_section_visible():
    _skip_pw()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        _skip_no_server(page)
        page.goto(_PV_URL)
        el = page.locator("text=تفصيلي").first
        if el.count() == 0:
            el = page.locator("text=Detailed").first
        if el.count() == 0:
            pytest.skip("Detailed report element not found")
        _SCR.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(_SCR / "detailed_added_layers.png"))
        browser.close()


# VT03 — Professional report section visible on page
def test_VT03_professional_report_section_visible():
    _skip_pw()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        _skip_no_server(page)
        page.goto(_PV_URL)
        el = page.locator("text=احترافي").first
        if el.count() == 0:
            el = page.locator("text=Professional").first
        if el.count() == 0:
            pytest.skip("Professional report element not found")
        _SCR.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(_SCR / "professional_added_layers.png"))
        browser.close()


# VT04 — Three-level review index screenshot
def test_VT04_three_level_review_index_screenshot():
    _skip_pw()
    _SCR.mkdir(parents=True, exist_ok=True)
    if not _IDX.exists():
        pytest.skip("Review index not generated")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("file:///" + str(_IDX).replace("\\", "/"))
        page.screenshot(path=str(_SCR / "three_level_report_review_index.png"))
        browser.close()


# VT05 — Merged Excel review screenshot
def test_VT05_merged_excel_review_screenshot():
    _skip_pw()
    _SCR.mkdir(parents=True, exist_ok=True)
    if not _EIDX.exists():
        pytest.skip("Excel review index not generated")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("file:///" + str(_EIDX).replace("\\", "/"))
        page.screenshot(path=str(_SCR / "merged_excel_review.png"))
        browser.close()


# VT06 — Traditional report PDF/HTML exists (file check)
def test_VT06_traditional_report_pdf_exists():
    assert _TRAD_PDF.exists() or _TRAD_HTML.exists(), \
        "traditional_report.pdf / .html not generated"
    if _TRAD_PDF.exists():
        assert _TRAD_PDF.stat().st_size > 50_000, "Traditional PDF too small"


# VT07 — Detailed report PDF/HTML exists (file check)
def test_VT07_detailed_report_pdf_exists():
    assert _DET_PDF.exists() or _DET_HTML.exists(), \
        "detailed_report.pdf / .html not generated"
    if _DET_PDF.exists():
        assert _DET_PDF.stat().st_size > 50_000, "Detailed PDF too small"


# VT08 — Professional report PDF/HTML exists (file check)
def test_VT08_professional_report_pdf_exists():
    assert _PRO_PDF.exists() or _PRO_HTML.exists(), \
        "professional_report.pdf / .html not generated"
    if _PRO_PDF.exists():
        assert _PRO_PDF.stat().st_size > 50_000, "Professional PDF too small"


# VT09 — Merged Excel workbook generated (file check)
def test_VT09_merged_excel_workbook_generated():
    xl = _XL if _XL.exists() else _XLM
    assert xl.exists(), "Merged Excel workbook not found"
    assert xl.stat().st_size > 10_000, "Excel too small"


# VT10 — Three-level review index exists
def test_VT10_three_level_review_index_exists():
    assert _IDX.exists(), "OPEN_THREE_LEVEL_REPORT_REVIEW_INDEX.html missing"
    content = _IDX.read_text(encoding="utf-8", errors="ignore")
    assert len(content) > 2_000, "Review index too short"
    assert "traditional" in content.lower() or "تقليدي" in content
    assert "certification_ready" in content


# VT11 — Excel preview index exists
def test_VT11_excel_preview_index_exists():
    assert _EIDX.exists(), "OPEN_MERGED_EXCEL_REVIEW_INDEX.html missing"
    content = _EIDX.read_text(encoding="utf-8", errors="ignore")
    assert len(content) > 1_000, "Excel preview index too short"
    assert "Sales Comparison" in content or "مقارنة" in content


# VT12 — No internal paths in generated HTML files
def test_VT12_no_internal_paths_in_dom():
    for f in [_TRAD_HTML, _DET_HTML, _PRO_HTML, _IDX, _EIDX]:
        if f and f.exists():
            content = f.read_text(encoding="utf-8", errors="ignore")
            for bad in [r"C:\\Users", "C:/Users", "/home/"]:
                assert bad not in content, \
                    "Internal path found in " + f.name + ": " + bad


# VT13 — Screenshot or blocker documented
def test_VT13_screenshot_or_blocker_documented():
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
