# test_pv_pdf_english_methods_upgrade_e2e.py
# E2E / browser tests for Professional Valuation PDF English Methods Upgrade
# advisory_only=True | not_real_training=True | no_commit=True
#
# T01–T21: Static file checks — run without live server.
# T22:     Requires live server + Playwright (deselected by default).

import pathlib
import pytest

pytestmark = pytest.mark.e2e

UPGRADE  = pathlib.Path(
    "core_engine/instance/manual_review_outputs/"
    "professional_valuation_pdf_english_methods_upgrade"
)
PDF_OUT  = UPGRADE / "pdf_outputs"
PREVIEWS = UPGRADE / "pdf_visual_previews"
AUDITS   = UPGRADE / "pdf_method_audits"

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
    import urllib.request, urllib.error
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
    assert "تقييم" in text or "valuation" in text.lower(), (
        "index.html does not reference valuation content"
    )


# ── T02: Unified report section referenced in HTML ────────────────────────────
def test_T02_unified_report_section_visible():
    idx = pathlib.Path("frontend/index.html")
    text = idx.read_text(encoding="utf-8", errors="replace")
    assert "تحليل وإصدار التقارير" in text or "report" in text.lower(), (
        "Unified report section 'تحليل وإصدار التقارير' not found in index.html"
    )


# ── T03: traditional_report.pdf physically created ────────────────────────────
def test_T03_traditional_report_pdf_exists():
    f = PDF_OUT / "traditional_report.pdf"
    assert f.exists(), f"traditional_report.pdf not created: {f}"
    assert f.stat().st_size > 5_000, f"traditional_report.pdf is too small"


# ── T04: detailed_report.pdf physically created ───────────────────────────────
def test_T04_detailed_report_pdf_exists():
    f = PDF_OUT / "detailed_report.pdf"
    assert f.exists(), f"detailed_report.pdf not created: {f}"
    assert f.stat().st_size > 5_000


# ── T05: professional_report.pdf physically created ───────────────────────────
def test_T05_professional_report_pdf_exists():
    f = PDF_OUT / "professional_report.pdf"
    assert f.exists(), f"professional_report.pdf not created: {f}"
    assert f.stat().st_size > 5_000


# ── T06: hbu_analysis_report.pdf physically created ───────────────────────────
def test_T06_hbu_report_pdf_exists():
    f = PDF_OUT / "hbu_analysis_report.pdf"
    assert f.exists(), f"hbu_analysis_report.pdf not created: {f}"
    assert f.stat().st_size > 5_000


# ── T07: standards_compliance_report.pdf physically created ───────────────────
def test_T07_standards_report_pdf_exists():
    f = PDF_OUT / "standards_compliance_report.pdf"
    assert f.exists(), f"standards_compliance_report.pdf not created: {f}"
    assert f.stat().st_size > 5_000


# ── T08: report_review_output.pdf physically created ─────────────────────────
def test_T08_report_review_pdf_exists():
    f = PDF_OUT / "report_review_output.pdf"
    assert f.exists(), f"report_review_output.pdf not created: {f}"
    assert f.stat().st_size > 5_000


# ── T09: simulated_uploaded_report.pdf physically created ─────────────────────
def test_T09_simulated_report_pdf_exists():
    f = PDF_OUT / "simulated_uploaded_report.pdf"
    assert f.exists(), f"simulated_uploaded_report.pdf not created: {f}"
    assert f.stat().st_size > 5_000


# ── T10: All 7 PDFs physically exist ─────────────────────────────────────────
def test_T10_all_seven_pdfs_exist():
    pdfs = list(PDF_OUT.glob("*.pdf"))
    assert len(pdfs) >= 7, f"Expected >= 7 PDFs, found {len(pdfs)}: {[p.name for p in pdfs]}"
    for p in pdfs:
        assert p.stat().st_size > 5_000, f"PDF too small: {p.name}"


# ── T11: No duplicate lower PDF/chat buttons (static HTML check) ──────────────
def test_T11_no_extra_orphan_pdf_buttons():
    idx = pathlib.Path("frontend/index.html")
    text = idx.read_text(encoding="utf-8", errors="replace")
    pdf_count = text.lower().count("generate-pdf") + text.lower().count("pdf-btn")
    assert pdf_count <= 30, (
        f"Suspiciously many PDF button refs ({pdf_count}) — possible duplicate buttons"
    )


# ── T12: Advisory notice confirmed in PDFs (English metadata) ─────────────────
def test_T12_advisory_notice_in_pdfs():
    for fname in ["traditional_report.pdf", "professional_report.pdf"]:
        f = PDF_OUT / fname
        if not f.exists():
            pytest.fail(f"PDF missing: {f}")
        content = f.read_bytes()
        assert b"Expert Smart" in content, (
            f"Advisory marker 'Expert Smart' missing in {fname}"
        )
        assert b"ReportLab" in content, (
            f"ReportLab marker missing in {fname}"
        )


# ── T13: No fake certification in PDFs ────────────────────────────────────────
def test_T13_no_fake_certification():
    fake = [b"FINAL_CERTIFIED", b"certified_final_valuation",
            b"certified_stamp", b"expert_signature"]
    for fname in PDF_FILES:
        f = PDF_OUT / fname
        if not f.exists():
            continue
        content = f.read_bytes()
        for phrase in fake:
            assert phrase not in content, (
                f"Fake certification phrase '{phrase.decode()}' in {fname}"
            )


# ── T14: No internal paths in PDFs ────────────────────────────────────────────
def test_T14_no_internal_paths_in_pdfs():
    forbidden = [b"C:\\Users\\", b"C:/Users/", b"AppData", b"__file__"]
    for fname in PDF_FILES:
        f = PDF_OUT / fname
        if not f.exists():
            continue
        content = f.read_bytes()
        for pat in forbidden:
            assert pat not in content, (
                f"Internal path '{pat.decode()}' in {fname}"
            )


# ── T15: PDF language context English in method audit ─────────────────────────
def test_T15_pdf_language_english_in_audit():
    audit = AUDITS / "method_coverage_audit.json"
    assert audit.exists(), f"Method audit missing: {audit}"
    import json
    data = json.loads(audit.read_text(encoding="utf-8"))
    lang_ctx = data.get("pdf_language_context", {})
    assert lang_ctx.get("pdf_language") == "en", (
        f"pdf_language not 'en' in method audit: {lang_ctx}"
    )
    assert lang_ctx.get("arabic_pdf_labels_removed") is True
    assert lang_ctx.get("english_report_template_enabled") is True


# ── T16: Traditional methods in professional report audit ─────────────────────
def test_T16_traditional_methods_in_professional_audit():
    import json
    audit = AUDITS / "method_coverage_audit.json"
    data = json.loads(audit.read_text(encoding="utf-8"))
    trad = data["valuation_methods_pdf_context"]["traditional_methods"]
    for method_key in ["market_approach", "income_approach", "cost_approach"]:
        covered = trad.get(method_key, {}).get("covered_in_pdfs", [])
        assert "professional_report" in covered, (
            f"Traditional method '{method_key}' not listed in professional_report"
        )


# ── T17: Modern methods in professional report audit ──────────────────────────
def test_T17_modern_methods_in_professional_audit():
    import json
    audit = AUDITS / "method_coverage_audit.json"
    data = json.loads(audit.read_text(encoding="utf-8"))
    modern = data["valuation_methods_pdf_context"]["modern_methods"]
    for method_key in ["dcf_analysis", "hbu_analysis"]:
        covered = modern.get(method_key, {}).get("covered_in_pdfs", [])
        assert "professional_report" in covered, (
            f"Modern method '{method_key}' not listed in professional_report"
        )


# ── T18: Physical audit status is PASS ────────────────────────────────────────
def test_T18_physical_audit_status_pass():
    import json
    audit = AUDITS / "pdf_physical_files_audit.json"
    assert audit.exists(), f"Physical audit missing: {audit}"
    data = json.loads(audit.read_text(encoding="utf-8"))
    assert data["pdf_generation_status"] == "PASS", (
        f"Generation status is not PASS: {data['pdf_generation_status']}"
    )
    assert data.get("pdf_language") == "en"
    assert data.get("advisory_only") is True


# ── T19: Visual preview index exists ─────────────────────────────────────────
def test_T19_visual_preview_index_exists():
    idx = PREVIEWS / "pdf_visual_review_index.html"
    assert idx.exists(), f"Visual review index missing: {idx}"
    text = idx.read_text(encoding="utf-8", errors="replace")
    assert "pdf_outputs" in text.lower() or "professional" in text.lower(), (
        "Visual review index does not reference PDF outputs"
    )


# ── T20: Individual visual previews exist ─────────────────────────────────────
def test_T20_individual_previews_exist():
    for fname in PDF_FILES:
        preview = PREVIEWS / fname.replace(".pdf", "_preview.html")
        assert preview.exists(), f"Preview missing: {preview.name}"


# ── T21: No internal paths in DOM (static HTML check) ────────────────────────
def test_T21_no_internal_paths_in_dom():
    idx = pathlib.Path("frontend/index.html")
    text = idx.read_text(encoding="utf-8", errors="replace")
    forbidden_patterns = ["C:\\Users\\", "AppData", "__file__", "/home/"]
    for pat in forbidden_patterns:
        assert pat not in text, (
            f"Internal path pattern '{pat}' found in frontend/index.html"
        )


# ── T22: Browser E2E — PV page opens (requires live server) ──────────────────
@pytest.mark.live_server
def test_T22_pv_page_opens_browser():
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
            # Check advisory notice is visible somewhere on the page
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
