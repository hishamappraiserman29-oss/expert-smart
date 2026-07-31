"""
E2E Visual QA tests for Core Valuation Report Issuance.
BT01-BT15: Browser tests (skip if Playwright unavailable).
FT01-FT15: File-based tests (always run).
Run: python -m pytest tests/e2e/test_pv_core_reports_excel_visual_qa_e2e.py -q
"""
from __future__ import annotations
import json, pathlib
import pytest

_ROOT = pathlib.Path(__file__).parent.parent.parent
_OUT  = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_core_reports_excel_visual_qa"
_PDF  = _OUT / "pdf_outputs"
_XL   = _OUT / "excel_outputs"
_AUD  = _OUT / "qa_audits"
_PREV = _OUT / "visual_previews"
_SS   = _OUT / "screenshots"
_RPT  = _OUT / "final_report"
_TXT  = _OUT / "pdf_text_extracts"
_EXLP = _OUT / "excel_previews"

_TRAD = _PDF / "traditional_valuation_report_upgraded.pdf"
_DET  = _PDF / "detailed_valuation_report_upgraded.pdf"
_PROF = _PDF / "professional_valuation_report_upgraded.pdf"
_XLWB = _XL  / "core_valuation_master_workbook.xlsx"
_IDX  = _PREV / "OPEN_CORE_REPORTS_EXCEL_VISUAL_QA_INDEX.html"

try:
    from playwright.sync_api import sync_playwright  # type: ignore
    _PW = True
except ImportError:
    _PW = False

_skip = pytest.mark.skipif(not _PW, reason="Playwright not installed")
_BASE = "http://localhost:5000"

# ── Browser tests ─────────────────────────────────────────────────────────────
@_skip
def test_BT01_page_opens():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        assert p.url.startswith(_BASE); b.close()

@_skip
def test_BT02_core_report_section_exists():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000); p.wait_for_load_state("domcontentloaded")
        el = p.query_selector("[data-testid='pv-core-valuation-report-issuance']")
        assert el is not None; b.close()

@_skip
def test_BT03_traditional_card_exists():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        assert p.query_selector("[data-testid='pv-core-report-chip-traditional']"); b.close()

@_skip
def test_BT04_detailed_card_exists():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        assert p.query_selector("[data-testid='pv-core-report-chip-detailed']"); b.close()

@_skip
def test_BT05_professional_card_exists():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        assert p.query_selector("[data-testid='pv-core-report-chip-professional']"); b.close()

@_skip
def test_BT06_page_count_badges_16_22_33():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        body = p.inner_html("[data-testid='pv-core-valuation-report-issuance']")
        assert "16" in body and "22" in body and "33" in body; b.close()

@_skip
def test_BT07_traditional_download_button():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        p.click("[data-testid='pv-core-report-chip-traditional']")
        p.wait_for_timeout(2000)
        assert p.query_selector("button:has-text('تحميل')") or \
               p.query_selector("[data-testid*='download']") or \
               p.query_selector("a[download]"); b.close()

@_skip
def test_BT08_detailed_download_button():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        p.click("[data-testid='pv-core-report-chip-detailed']")
        p.wait_for_timeout(2000)
        body = p.inner_html("body")
        assert "تحميل" in body or "download" in body.lower(); b.close()

@_skip
def test_BT09_professional_download_button():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        p.click("[data-testid='pv-core-report-chip-professional']")
        p.wait_for_timeout(2000)
        body = p.inner_html("body")
        assert "تحميل" in body or "download" in body.lower(); b.close()

@_skip
def test_BT10_internal_excel_card_exists():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        el = p.query_selector("[data-testid='pv-core-internal-excel-card']")
        assert el is not None; b.close()

@_skip
def test_BT11_excel_download_button():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        el = p.query_selector("[data-testid='pv-core-download-internal-excel']")
        assert el is not None; b.close()

@_skip
def test_BT12_no_duplicate_old_excel_buttons():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        els = p.query_selector_all("[data-testid*='excel']")
        assert len(els) <= 2; b.close()

@_skip
def test_BT13_no_internal_paths_in_dom():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        body = p.inner_html("body")
        assert r"C:\Users\Lenovo" not in body; b.close()

@_skip
def test_BT14_traditional_card_description():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        body = p.inner_html("[data-testid='pv-core-valuation-report-issuance']")
        assert "مختصر" in body or "سريعة" in body; b.close()

@_skip
def test_BT15_professional_card_description():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        body = p.inner_html("[data-testid='pv-core-valuation-report-issuance']")
        assert "امتثال" in body or "احترافي" in body; b.close()

# ── File-based tests ──────────────────────────────────────────────────────────
def test_FT01_output_folder_exists():   assert _OUT.is_dir()
def test_FT02_traditional_pdf_exists(): assert _TRAD.exists()
def test_FT03_detailed_pdf_exists():    assert _DET.exists()
def test_FT04_professional_pdf_exists(): assert _PROF.exists()
def test_FT05_pdfs_non_empty():
    for p in [_TRAD, _DET, _PROF]: assert p.stat().st_size > 100

def test_FT06_excel_master_workbook_exists(): assert _XLWB.exists()
def test_FT07_visual_index_exists():          assert _IDX.exists()

def test_FT08_qa_audits_folder_exists(): assert _AUD.is_dir()

def test_FT09_all_13_audits_exist():
    for i in range(1, 14):
        prefix = f"{i:02d}_"
        matches = list(_AUD.glob(prefix + "*.json"))
        assert matches, f"Audit {prefix}* missing"

def test_FT10_all_audits_safety_flags():
    for f in _AUD.glob("*.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        assert d.get("advisory_only") is True, f"{f.name}: advisory_only"
        assert d.get("fake_sources_created") is False, f"{f.name}: fake_sources"

def test_FT11_all_38_screenshots_exist():
    expected = [f"{i:02d}_" for i in range(1, 39)]
    for prefix in expected:
        assert list(_SS.glob(prefix + "*.png")), f"Screenshot {prefix}* missing"

def test_FT12_no_fake_credentials():
    a = json.loads((_AUD/"02_pdf_generation_audit.json").read_text(encoding="utf-8"))
    assert a.get("fake_signature_created") is False
    assert a.get("fake_valuer_created") is False
    assert a.get("fake_license_created") is False
    assert a.get("fake_stamp_created") is False

def test_FT13_excel_previews_exist():
    for f in ["OPEN_EXCEL_DASHBOARD_PREVIEW.html", "OPEN_EXCEL_METHODS_PREVIEW.html",
              "OPEN_EXCEL_FORMULAS_PREVIEW.html"]:
        assert (_EXLP/f).exists(), f"{f} missing"

def test_FT14_no_internal_paths_in_visual_index():
    c = _IDX.read_text(encoding="utf-8", errors="ignore")
    assert r"C:\Users\Lenovo" not in c
    assert "C:/Users/Lenovo" not in c

def test_FT15_final_report_status():
    rpt = _RPT / "final_core_reports_excel_visual_qa_report.txt"
    assert rpt.exists()
    d = json.loads(rpt.read_text(encoding="utf-8"))
    assert d.get("overall_status") in ("PASS", "PARTIAL")
    assert d.get("fake_signature_created") is False
    assert d.get("internal_paths_exposed") is False
