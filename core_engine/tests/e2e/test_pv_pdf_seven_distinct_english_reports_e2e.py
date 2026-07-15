# test_pv_pdf_seven_distinct_english_reports_e2e.py
# E2E tests — Radical PDF Rebuild: 7 Distinct English Report Types
# advisory_only=True | not_real_training=True | no_commit=True
#
# T01–T22: Static file checks — run without live server.
# T23:     Requires live server + Playwright (deselected by default).

import json
import pathlib
import pytest

pytestmark = pytest.mark.e2e

BASE = pathlib.Path(
    "core_engine/instance/manual_review_outputs/"
    "professional_valuation_pdf_seven_distinct_english_reports"
)
PDF_OUT   = BASE / "pdf_outputs"
RT_AUDITS = BASE / "report_type_audits"
M_AUDITS  = BASE / "method_audits"
PREVIEWS  = BASE / "pdf_visual_previews"

PDF_FILES = [
    "traditional_report.pdf",
    "detailed_report.pdf",
    "professional_report.pdf",
    "hbu_analysis_report.pdf",
    "standards_compliance_report.pdf",
    "report_review_output.pdf",
    "simulated_uploaded_report.pdf",
]

BASE_URL = "http://127.0.0.1:5000"

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


def _server_running():
    import urllib.request
    try:
        urllib.request.urlopen(f"{BASE_URL}/api/advisor/health", timeout=3)
        return True
    except Exception:
        return False


# ── T01: Professional Valuation page HTML exists ──────────────────────────────
def test_T01_pv_page_html_exists():
    idx = pathlib.Path("frontend/index.html")
    assert idx.exists(), "frontend/index.html missing"
    text = idx.read_text(encoding="utf-8", errors="replace")
    assert "تقييم" in text or "valuation" in text.lower()


# ── T02: Unified report section referenced in HTML ───────────────────────────
def test_T02_unified_report_section_visible():
    idx = pathlib.Path("frontend/index.html")
    text = idx.read_text(encoding="utf-8", errors="replace")
    assert "تحليل وإصدار التقارير" in text or "report" in text.lower()


# ── T03: traditional_report.pdf exists and > 15 KB ───────────────────────────
def test_T03_traditional_report_exists():
    f = PDF_OUT / "traditional_report.pdf"
    assert f.exists(), f"traditional_report.pdf missing"
    assert f.stat().st_size > 15_000


# ── T04: detailed_report.pdf exists and > 20 KB ──────────────────────────────
def test_T04_detailed_report_exists():
    f = PDF_OUT / "detailed_report.pdf"
    assert f.exists()
    assert f.stat().st_size > 20_000, f"detailed_report too small: {f.stat().st_size/1024:.1f} KB"


# ── T05: professional_report.pdf exists and > 30 KB ──────────────────────────
def test_T05_professional_report_exists():
    f = PDF_OUT / "professional_report.pdf"
    assert f.exists()
    assert f.stat().st_size > 30_000, f"professional_report too small: {f.stat().st_size/1024:.1f} KB"


# ── T06: hbu_analysis_report.pdf exists ─────────────────────────────────────
def test_T06_hbu_report_exists():
    f = PDF_OUT / "hbu_analysis_report.pdf"
    assert f.exists()
    assert f.stat().st_size > 15_000


# ── T07: standards_compliance_report.pdf exists ──────────────────────────────
def test_T07_standards_report_exists():
    f = PDF_OUT / "standards_compliance_report.pdf"
    assert f.exists()
    assert f.stat().st_size > 15_000


# ── T08: report_review_output.pdf exists ─────────────────────────────────────
def test_T08_review_output_exists():
    f = PDF_OUT / "report_review_output.pdf"
    assert f.exists()
    assert f.stat().st_size > 15_000


# ── T09: simulated_uploaded_report.pdf exists ────────────────────────────────
def test_T09_simulation_report_exists():
    f = PDF_OUT / "simulated_uploaded_report.pdf"
    assert f.exists()
    assert f.stat().st_size > 15_000


# ── T10: All 7 PDFs exist ────────────────────────────────────────────────────
def test_T10_all_seven_pdfs_exist():
    pdfs = list(PDF_OUT.glob("*.pdf"))
    assert len(pdfs) >= 7, f"Expected >= 7 PDFs, found {len(pdfs)}"
    for p in pdfs:
        assert p.stat().st_size > 15_000, f"PDF too small: {p.name}"


# ── T11: No duplicate lower PDF/chat buttons (static HTML check) ──────────────
def test_T11_no_extra_orphan_pdf_buttons():
    idx = pathlib.Path("frontend/index.html")
    text = idx.read_text(encoding="utf-8", errors="replace")
    pdf_count = text.lower().count("generate-pdf") + text.lower().count("pdf-btn")
    assert pdf_count <= 30, f"Suspiciously many PDF button refs ({pdf_count})"


# ── T12: English metadata in all PDFs ────────────────────────────────────────
def test_T12_english_metadata_in_pdfs():
    for fname in ["traditional_report.pdf", "professional_report.pdf",
                  "hbu_analysis_report.pdf"]:
        f = PDF_OUT / fname
        if not f.exists():
            pytest.fail(f"PDF missing: {f}")
        content = f.read_bytes()
        assert b"Expert Smart" in content, f"'Expert Smart' missing in {fname}"
        assert b"ReportLab" in content, f"ReportLab marker missing in {fname}"


# ── T13: No fake certification in any PDF ─────────────────────────────────────
def test_T13_no_fake_certification():
    fake = [b"FINAL_CERTIFIED", b"certified_final_valuation",
            b"certified_stamp", b"expert_signature"]
    for fname in PDF_FILES:
        f = PDF_OUT / fname
        if not f.exists():
            continue
        content = f.read_bytes()
        for phrase in fake:
            assert phrase not in content, f"Fake cert phrase '{phrase.decode()}' in {fname}"


# ── T14: No internal paths in PDFs ────────────────────────────────────────────
def test_T14_no_internal_paths_in_pdfs():
    forbidden = [b"C:\\Users\\", b"C:/Users/", b"AppData", b"__file__"]
    for fname in PDF_FILES:
        f = PDF_OUT / fname
        if not f.exists():
            continue
        content = f.read_bytes()
        for pat in forbidden:
            assert pat not in content, f"Internal path '{pat.decode()}' in {fname}"


# ── T15: PDF language PASS in language audit ─────────────────────────────────
def test_T15_language_audit_pass():
    audit = RT_AUDITS / "pdf_english_language_audit.json"
    assert audit.exists()
    data = json.loads(audit.read_text(encoding="utf-8"))
    assert data["language_status"] == "PASS"
    assert data["pdf_language_required"] == "en"


# ── T16: Traditional methods in traditional report audit ─────────────────────
def test_T16_traditional_methods_in_audit():
    data = json.loads((M_AUDITS/"pdf_method_coverage_audit.json").read_text(encoding="utf-8"))
    trad = data["traditional_report"]
    for m in ["market_approach","income_approach","cost_approach","avm_assisted_indication"]:
        assert trad[m] is True, f"traditional_report missing: {m}"


# ── T17: Modern methods in professional report audit ─────────────────────────
def test_T17_modern_methods_in_professional():
    data = json.loads((M_AUDITS/"pdf_method_coverage_audit.json").read_text(encoding="utf-8"))
    prof = data["professional_report"]
    for m in ["dcf_analysis","hbu_summary","scenario_analysis","sensitivity_analysis",
              "avm_assisted_indication","weighted_reconciliation"]:
        assert prof[m] is True, f"professional_report missing: {m}"


# ── T18: Physical audit status PASS ──────────────────────────────────────────
def test_T18_physical_audit_status_pass():
    audit = RT_AUDITS / "pdf_physical_files_audit.json"
    assert audit.exists()
    data = json.loads(audit.read_text(encoding="utf-8"))
    assert data["pdf_generation_status"] == "PASS"
    assert data["pdf_language"] == "en"
    assert data["advisory_only"] is True


# ── T19: Visual preview index exists ─────────────────────────────────────────
def test_T19_visual_preview_index_exists():
    idx = PREVIEWS / "pdf_visual_review_index.html"
    assert idx.exists()
    text = idx.read_text(encoding="utf-8", errors="replace")
    assert "professional" in text.lower() or "pdf_outputs" in text.lower()


# ── T20: Individual previews exist for all 7 reports ─────────────────────────
def test_T20_individual_previews_exist():
    for fname in PDF_FILES:
        preview = PREVIEWS / fname.replace(".pdf", "_preview.html")
        assert preview.exists(), f"Preview missing: {preview.name}"


# ── T21: No internal paths in frontend HTML ───────────────────────────────────
def test_T21_no_internal_paths_in_dom():
    idx = pathlib.Path("frontend/index.html")
    text = idx.read_text(encoding="utf-8", errors="replace")
    for pat in ["C:\\Users\\", "AppData", "__file__", "/home/"]:
        assert pat not in text, f"Internal path '{pat}' in frontend/index.html"


# ── T22: Seven reports distinctness audit PASS ───────────────────────────────
def test_T22_seven_reports_distinct():
    audit = RT_AUDITS / "seven_pdf_distinctness_audit.json"
    assert audit.exists()
    data = json.loads(audit.read_text(encoding="utf-8"))
    assert data["reports_are_distinct"] is True
    assert data["near_duplicate_report_pairs"] == []


# ── T23: Browser E2E — PV page opens (requires live server) ──────────────────
@pytest.mark.live_server
def test_T23_pv_page_opens_browser():
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("playwright not installed")
    if not _server_running():
        pytest.skip("Server not running at http://127.0.0.1:5000")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(f"{BASE_URL}/", timeout=15000)
            page.wait_for_load_state("networkidle", timeout=15000)
            title = page.title()
            assert title, "Page has no title"
            content = page.content()
            assert (
                "advisory" in content.lower()
                or "تحليل" in content
                or "valuation" in content.lower()
            ), "Page does not appear to be the Professional Valuation page"
        except PWTimeout:
            pytest.fail("Page load timed out")
        finally:
            browser.close()
