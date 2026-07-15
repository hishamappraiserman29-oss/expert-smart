"""
E2E tests for Core Reports Excel Visual QA upgrade.
BT01-BT12: Browser tests (skip if Playwright unavailable).
FT01-FT17: File-based tests (always run).
Run: python -m pytest tests/e2e/test_pv_core_valuation_reports_upgrade_e2e.py -q
"""
from __future__ import annotations
import json, pathlib
import pytest

_ROOT = pathlib.Path(__file__).parent.parent.parent
_OUT  = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_core_reports_excel_visual_qa"
_PDF  = _OUT / "pdf_outputs"
_XL   = _OUT / "excel_outputs"
_AUD  = _OUT / "report_audits"
_PREV = _OUT / "visual_previews"
_SS   = _OUT / "screenshots"
_RPT  = _OUT / "final_report"

_TRAD = _PDF / "traditional_valuation_report_upgraded.pdf"
_DET  = _PDF / "detailed_valuation_report_upgraded.pdf"
_PROF = _PDF / "professional_valuation_report_upgraded.pdf"
_XLWB = _XL  / "core_reports_qa_workbook.xlsx"
_IDX  = _PREV / "OPEN_CORE_REPORTS_EXCEL_VISUAL_QA_INDEX.html"

try:
    from playwright.sync_api import sync_playwright, Page  # type: ignore
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
def test_BT02_core_section_exists():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000); p.wait_for_load_state("domcontentloaded")
        el = p.query_selector("[data-testid='pv-core-valuation-report-issuance']")
        assert el is not None; b.close()

@_skip
def test_BT03_traditional_chip_exists():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        assert p.query_selector("[data-testid='pv-core-report-chip-traditional']"); b.close()

@_skip
def test_BT04_detailed_chip_exists():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        assert p.query_selector("[data-testid='pv-core-report-chip-detailed']"); b.close()

@_skip
def test_BT05_professional_chip_exists():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        assert p.query_selector("[data-testid='pv-core-report-chip-professional']"); b.close()

@_skip
def test_BT06_traditional_badge_16_pages():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        body = p.inner_html("[data-testid='pv-core-valuation-report-issuance']")
        assert "16" in body; b.close()

@_skip
def test_BT07_detailed_badge_22_pages():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        body = p.inner_html("[data-testid='pv-core-valuation-report-issuance']")
        assert "22" in body; b.close()

@_skip
def test_BT08_professional_badge_33_pages():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        body = p.inner_html("[data-testid='pv-core-valuation-report-issuance']")
        assert "33" in body; b.close()

@_skip
def test_BT09_traditional_description_visible():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        body = p.inner_html("[data-testid='pv-core-valuation-report-issuance']")
        assert "مختصر" in body or "سريعة" in body; b.close()

@_skip
def test_BT10_no_internal_paths_in_dom():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        body = p.inner_html("body")
        assert r"C:\Users\Lenovo" not in body; b.close()

@_skip
def test_BT11_internal_excel_card_visible():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        el = p.query_selector("[data-testid='pv-core-internal-excel-card']")
        assert el is not None; b.close()

@_skip
def test_BT12_download_internal_excel_button():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        el = p.query_selector("[data-testid='pv-core-download-internal-excel']")
        assert el is not None; b.close()

# ── File-based tests ──────────────────────────────────────────────────────────
def test_FT01_output_folder_exists(): assert _OUT.is_dir()
def test_FT02_traditional_pdf_exists(): assert _TRAD.exists()
def test_FT03_detailed_pdf_exists():    assert _DET.exists()
def test_FT04_professional_pdf_exists(): assert _PROF.exists()
def test_FT05_pdfs_non_empty():
    for p in [_TRAD, _DET, _PROF]:
        assert p.stat().st_size > 100

def test_FT06_excel_workbook_exists():  assert _XLWB.exists()
def test_FT07_visual_index_exists():    assert _IDX.exists()

def test_FT08_visual_index_no_internal_paths():
    c = _IDX.read_text(encoding="utf-8", errors="ignore")
    assert r"C:\Users\Lenovo" not in c
    assert "C:/Users/Lenovo" not in c

def test_FT09_all_17_audits_exist():
    for i in range(1, 18):
        prefix = f"{i:02d}_"
        matches = list(_AUD.glob(prefix + "*.json"))
        assert matches, f"Audit {prefix}* missing"

def test_FT10_all_audits_safety_flags():
    for f in _AUD.glob("*.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        assert d.get("advisory_only") is True, f"{f.name}"
        assert d.get("fake_sources_created") is False, f"{f.name}"

def test_FT11_all_15_screenshots_exist():
    expected = [f"{i:02d}_" for i in range(1, 16)]
    for prefix in expected:
        assert list(_SS.glob(prefix + "*.png")), f"Screenshot {prefix}* missing"

def test_FT12_no_fake_signature():
    f = _AUD / "12_standards_compliance_statement.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    assert d.get("fake_signature_created") is False
    assert d.get("fake_valuer_name_created") is False

def test_FT13_covers_differentiated():
    d = json.loads((_AUD/"04_cover_differentiation.json").read_text(encoding="utf-8"))
    assert d.get("traditional_blue_cover_created") is True
    assert d.get("detailed_green_bronze_cover_created") is True
    assert d.get("professional_red_gold_cover_created") is True

def test_FT14_professional_has_toc():
    d = json.loads((_AUD/"05_report_structure.json").read_text(encoding="utf-8"))
    assert d.get("professional_toc_present") is True

def test_FT15_risk_matrix_early():
    d = json.loads((_AUD/"13_risk_matrix_upgrade.json").read_text(encoding="utf-8"))
    assert d.get("risk_matrix_5x5_created") is True
    assert d.get("risk_matrix_placed_early") is True

def test_FT16_final_report_exists():
    rpt = _RPT / "final_core_reports_excel_visual_qa_report.txt"
    assert rpt.exists()
    d = json.loads(rpt.read_text(encoding="utf-8", errors="ignore"))
    assert d.get("overall_status") in ("PASS","PARTIAL")

def test_FT17_no_internal_paths_in_any_audit():
    for f in _AUD.glob("*.json"):
        c = f.read_text(encoding="utf-8", errors="ignore")
        assert r"C:\Users\Lenovo" not in c, f.name
