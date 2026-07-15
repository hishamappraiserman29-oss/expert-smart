"""
E2E Visual QA tests — Post-Update Core Valuation Reports.
BT01-BT12: Browser tests (skip if Playwright unavailable).
FT01-FT15: File-based tests (always run).
Run: python -m pytest tests/e2e/test_pv_post_update_visual_qa_e2e.py -q
"""
from __future__ import annotations
import json, pathlib
import pytest

_ROOT = pathlib.Path(__file__).parent.parent.parent
_OUT  = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_post_update_visual_qa"
_PDF  = _OUT / "pdf_outputs"
_XL   = _OUT / "excel_outputs"
_AUD  = _OUT / "qa_audits"
_PREV = _OUT / "visual_previews"
_SS   = _OUT / "screenshots"
_RPT  = _OUT / "final_report"
_EXLP = _OUT / "excel_previews"

_TRAD = _PDF / "traditional_valuation_report_post_update.pdf"
_DET  = _PDF / "detailed_valuation_report_post_update.pdf"
_PROF = _PDF / "professional_valuation_report_post_update.pdf"
_XLWB = _XL  / "core_valuation_master_workbook_post_update.xlsx"
_IDX  = _PREV / "OPEN_POST_UPDATE_VISUAL_QA_INDEX.html"

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
def test_BT06_excel_internal_card_exists():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        el = p.query_selector("[data-testid='pv-core-internal-excel-card']")
        assert el is not None; b.close()

@_skip
def test_BT07_page_count_badges():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        body = p.inner_html("[data-testid='pv-core-valuation-report-issuance']")
        assert "16" in body and "22" in body and "33" in body; b.close()

@_skip
def test_BT08_no_internal_paths_in_dom():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        body = p.inner_html("body")
        assert r"C:\Users\Lenovo" not in body; b.close()

@_skip
def test_BT09_traditional_description():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        body = p.inner_html("[data-testid='pv-core-valuation-report-issuance']")
        assert "مختصر" in body or "سريعة" in body; b.close()

@_skip
def test_BT10_detailed_description():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        body = p.inner_html("[data-testid='pv-core-valuation-report-issuance']")
        assert "تحليلي" in body or "ملخصاً" in body or "سيناريوهات" in body; b.close()

@_skip
def test_BT11_professional_description():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        body = p.inner_html("[data-testid='pv-core-valuation-report-issuance']")
        assert "امتثال" in body or "احترافي" in body; b.close()

@_skip
def test_BT12_excel_download_button():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        el = p.query_selector("[data-testid='pv-core-download-internal-excel']")
        assert el is not None; b.close()

# ── File-based tests ──────────────────────────────────────────────────────────
def test_FT01_output_folder_exists():   assert _OUT.is_dir()
def test_FT02_traditional_pdf_exists(): assert _TRAD.exists()
def test_FT03_detailed_pdf_exists():    assert _DET.exists()
def test_FT04_professional_pdf_exists(): assert _PROF.exists()
def test_FT05_pdfs_non_empty():
    for p in [_TRAD, _DET, _PROF]:
        assert p.stat().st_size > 10_000, f"{p.name} too small"

def test_FT06_excel_workbook_exists():  assert _XLWB.exists()
def test_FT07_excel_non_empty():        assert _XLWB.stat().st_size > 5_000

def test_FT08_visual_index_exists():    assert _IDX.exists()

def test_FT09_no_internal_paths_in_index():
    c = _IDX.read_text(encoding="utf-8", errors="ignore")
    assert r"C:\Users\Lenovo" not in c
    assert "C:/Users/Lenovo" not in c

def test_FT10_all_12_audits_exist():
    for i in range(1, 13):
        prefix = f"{i:02d}_"
        assert list(_AUD.glob(prefix + "*.json")), f"Audit {prefix}* missing"

def test_FT11_all_audits_safety_flags():
    for f in _AUD.glob("*.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        assert d.get("advisory_only") is True, f.name
        assert d.get("fake_sources_created") is False, f.name

def test_FT12_no_fake_credentials():
    a = json.loads((_AUD / "03_pdf_physical_audit.json").read_text(encoding="utf-8"))
    assert a.get("fake_signature_created") is False
    assert a.get("fake_valuer_created") is False
    assert a.get("fake_license_created") is False

def test_FT13_excel_previews_exist():
    for fname in ["OPEN_EXCEL_DASHBOARD_PREVIEW.html",
                  "OPEN_EXCEL_FORMULAS_PREVIEW.html",
                  "OPEN_EXCEL_PRINT_SUMMARY_PREVIEW.html"]:
        assert (_EXLP / fname).exists(), f"{fname} missing"

def test_FT14_screenshots_exist():
    ss = list(_SS.glob("*.png"))
    assert len(ss) >= 35, f"Only {len(ss)} screenshots"

def test_FT15_final_report_status():
    rpt = _RPT / "final_post_update_visual_qa_report.txt"
    assert rpt.exists()
    d = json.loads(rpt.read_text(encoding="utf-8"))
    assert d.get("overall_status") in ("PASS", "PARTIAL")
    assert d.get("fake_signature_created") is False
    assert d.get("internal_paths_exposed") is False
