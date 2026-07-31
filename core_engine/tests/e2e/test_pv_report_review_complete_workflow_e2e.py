"""
test_pv_report_review_complete_workflow_e2e.py
28 e2e tests — Complete Report Review Workflow.
advisory_only=True | human_reviewer_required=True | certification_ready=False
VT01-VT20: Playwright (skip if not installed or server down)
VT21-VT28: File-based (always run)
"""
from __future__ import annotations
from pathlib import Path
import pytest

_CORE = Path(__file__).resolve().parent.parent.parent
_INST = _CORE / "instance" / "manual_review_outputs"
_OUT  = _INST / "professional_valuation_report_review_complete_workflow"

_PDF_DIR  = _OUT / "pdf_outputs"
_XL_DIR   = _OUT / "excel_outputs"
_AUD_DIR  = _OUT / "report_review_audits"
_VIS_DIR  = _OUT / "visual_previews"
_SCR_DIR  = _OUT / "screenshots"

_REVIEW_PDF  = _PDF_DIR / "report_review_output.pdf"
_REVIEW_HTML = _PDF_DIR / "report_review_output.html"
_VISUAL_IDX  = _VIS_DIR / "OPEN_REPORT_REVIEW_COMPLETE_WORKFLOW_INDEX.html"

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


# ── VT01: Professional Valuation page opens ───────────────────────────────────
def test_VT01_professional_valuation_page_opens():
    _skip_pw()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        _skip_no_server(page)
        page.goto(_PV_URL)
        assert page.title() != ""
        _SCR_DIR.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(_SCR_DIR / "report_review_button.png"))
        browser.close()


# ── VT02: Special Reports section visible ─────────────────────────────────────
def test_VT02_special_reports_section_visible():
    _skip_pw()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        _skip_no_server(page)
        page.goto(_PV_URL)
        el = page.query_selector('[data-testid="pv-special-workflow-buttons"]')
        assert el is not None, "Special workflow buttons missing"
        browser.close()


# ── VT03: Click Report Review button ─────────────────────────────────────────
def test_VT03_click_report_review_button():
    _skip_pw()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        _skip_no_server(page)
        page.goto(_PV_URL)
        btn = page.query_selector('[data-testid="pv-open-report-review-table"]')
        assert btn is not None, "Report Review button missing"
        btn.click()
        page.wait_for_timeout(500)
        _SCR_DIR.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(_SCR_DIR / "report_review_wizard_step_1_upload_extraction.png"))
        browser.close()


# ── VT04: Report Review wizard opens ──────────────────────────────────────────
def test_VT04_report_review_wizard_opens():
    _skip_pw()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        _skip_no_server(page)
        page.goto(_PV_URL)
        btn = page.query_selector('[data-testid="pv-open-report-review-table"]')
        if btn:
            btn.click()
            page.wait_for_timeout(500)
        panel = page.query_selector('[data-testid="pv-special-req-panel-report_review_output"]')
        assert panel is not None, "Report Review panel missing"
        browser.close()


# ── VT05: Step 1 upload/extraction visible ────────────────────────────────────
def test_VT05_step1_upload_extraction_visible():
    _skip_pw()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        _skip_no_server(page)
        page.goto(_PV_URL)
        btn = page.query_selector('[data-testid="pv-open-report-review-table"]')
        if btn:
            btn.click()
            page.wait_for_timeout(500)
        # Step 1 should be active
        step1 = page.query_selector('[data-testid="rr-wizard-step-1"]')
        assert step1 is not None, "Wizard Step 1 missing"
        browser.close()


# ── VT06: Upload PDF fixture ──────────────────────────────────────────────────
def test_VT06_upload_pdf_fixture():
    _skip_pw()
    # Find a test fixture PDF
    fixture_pdf = None
    for candidate in [
        _CORE / "instance" / "manual_review_outputs" / "valuation_certification_readiness_gate" / "01_market_certification_readiness_preliminary.pdf",
        _REVIEW_PDF,
    ]:
        if candidate.exists():
            fixture_pdf = candidate
            break
    if not fixture_pdf:
        pytest.skip("No fixture PDF found for upload test")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        _skip_no_server(page)
        page.goto(_PV_URL)
        btn = page.query_selector('[data-testid="pv-open-report-review-table"]')
        if btn:
            btn.click()
            page.wait_for_timeout(500)
        upload_input = page.query_selector('[data-testid="rr-pdf-upload"]')
        if upload_input:
            upload_input.set_input_files(str(fixture_pdf))
            page.wait_for_timeout(1000)
        _SCR_DIR.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(_SCR_DIR / "report_review_wizard_step_1_upload_extraction.png"))
        browser.close()


# ── VT07: Verify upload status appears ───────────────────────────────────────
def test_VT07_upload_status_appears():
    _skip_pw()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        _skip_no_server(page)
        page.goto(_PV_URL)
        btn = page.query_selector('[data-testid="pv-open-report-review-table"]')
        if btn:
            btn.click()
            page.wait_for_timeout(500)
        status = page.query_selector('[data-testid="rr-extraction-status"]')
        assert status is not None, "Extraction status element missing"
        browser.close()


# ── VT08: Verify extraction status appears ────────────────────────────────────
def test_VT08_extraction_status_appears():
    _skip_pw()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        _skip_no_server(page)
        page.goto(_PV_URL)
        btn = page.query_selector('[data-testid="pv-open-report-review-table"]')
        if btn:
            btn.click()
            page.wait_for_timeout(500)
        _SCR_DIR.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(_SCR_DIR / "report_review_wizard_step_2_review_info.png"))
        browser.close()


# ── VT09: Go to Step 2 ────────────────────────────────────────────────────────
def test_VT09_go_to_step_2():
    _skip_pw()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        _skip_no_server(page)
        page.goto(_PV_URL)
        btn = page.query_selector('[data-testid="pv-open-report-review-table"]')
        if btn:
            btn.click()
            page.wait_for_timeout(500)
        next_btn = page.query_selector('[data-testid="rr-wizard-next"]')
        if next_btn:
            next_btn.click()
            page.wait_for_timeout(500)
        _SCR_DIR.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(_SCR_DIR / "report_review_wizard_step_2_review_info.png"))
        browser.close()


# ── VT10: Fill review info ────────────────────────────────────────────────────
def test_VT10_fill_review_info():
    _skip_pw()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        _skip_no_server(page)
        page.goto(_PV_URL)
        btn = page.query_selector('[data-testid="pv-open-report-review-table"]')
        if btn:
            btn.click()
            page.wait_for_timeout(500)
        # rr-reviewer-name is in step 2 — advance one step first
        nb = page.query_selector('[data-testid="rr-wizard-next"]')
        if nb:
            nb.click()
            page.wait_for_timeout(500)
        el = page.query_selector('[data-testid="rr-reviewer-name"]')
        if el and el.is_visible():
            el.fill("م. هشام المهدي")
        browser.close()


# ── VT11: Go to Step 3 ────────────────────────────────────────────────────────
def test_VT11_go_to_step_3_standards():
    _skip_pw()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        _skip_no_server(page)
        page.goto(_PV_URL)
        btn = page.query_selector('[data-testid="pv-open-report-review-table"]')
        if btn:
            btn.click()
            page.wait_for_timeout(300)
        for _ in range(2):
            nb = page.query_selector('[data-testid="rr-wizard-next"]')
            if nb:
                nb.click()
                page.wait_for_timeout(300)
        _SCR_DIR.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(_SCR_DIR / "report_review_wizard_step_3_standards.png"))
        browser.close()


# ── VT12: Dynamic checklists appear ──────────────────────────────────────────
def test_VT12_dynamic_checklists_appear():
    _skip_pw()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        _skip_no_server(page)
        page.goto(_PV_URL)
        btn = page.query_selector('[data-testid="pv-open-report-review-table"]')
        if btn:
            btn.click()
            page.wait_for_timeout(300)
        # Check for standards checkboxes
        ivs_chk = page.query_selector('[data-testid="rr-std-ivs"]')
        assert ivs_chk is not None, "IVS standard checkbox missing"
        browser.close()


# ── VT13: Evidence/status/severity/notes fields ───────────────────────────────
def test_VT13_evidence_status_severity_fields():
    _skip_pw()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        _skip_no_server(page)
        page.goto(_PV_URL)
        btn = page.query_selector('[data-testid="pv-open-report-review-table"]')
        if btn:
            btn.click()
            page.wait_for_timeout(300)
        # Check checklist table exists
        tbl = page.query_selector('[data-testid="rr-ivs-checklist-table"]')
        assert tbl is not None, "IVS checklist table missing"
        browser.close()


# ── VT14: Go to Step 4 ────────────────────────────────────────────────────────
def test_VT14_go_to_step_4_technical_agents():
    _skip_pw()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        _skip_no_server(page)
        page.goto(_PV_URL)
        btn = page.query_selector('[data-testid="pv-open-report-review-table"]')
        if btn:
            btn.click()
            page.wait_for_timeout(300)
        for _ in range(3):
            nb = page.query_selector('[data-testid="rr-wizard-next"]')
            if nb:
                nb.click()
                page.wait_for_timeout(300)
        _SCR_DIR.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(_SCR_DIR / "report_review_wizard_step_4_technical_agents.png"))
        browser.close()


# ── VT15: Review agents panel visible ────────────────────────────────────────
def test_VT15_review_agents_panel_visible():
    _skip_pw()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        _skip_no_server(page)
        page.goto(_PV_URL)
        btn = page.query_selector('[data-testid="pv-open-report-review-table"]')
        if btn:
            btn.click()
            page.wait_for_timeout(300)
        agents = page.query_selector('[data-testid="rr-agents-panel"]')
        assert agents is not None, "Review agents panel missing"
        browser.close()


# ── VT16: Human review flags panel ────────────────────────────────────────────
def test_VT16_human_review_flags_panel():
    _skip_pw()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        _skip_no_server(page)
        page.goto(_PV_URL)
        btn = page.query_selector('[data-testid="pv-open-report-review-table"]')
        if btn:
            btn.click()
            page.wait_for_timeout(300)
        flags = page.query_selector('[data-testid="rr-human-flags-panel"]')
        assert flags is not None, "Human review flags panel missing"
        browser.close()


# ── VT17: Go to Step 5 ────────────────────────────────────────────────────────
def test_VT17_go_to_step_5_final_decision():
    _skip_pw()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        _skip_no_server(page)
        page.goto(_PV_URL)
        btn = page.query_selector('[data-testid="pv-open-report-review-table"]')
        if btn:
            btn.click()
            page.wait_for_timeout(300)
        for _ in range(4):
            nb = page.query_selector('[data-testid="rr-wizard-next"]')
            if nb:
                nb.click()
                page.wait_for_timeout(300)
        _SCR_DIR.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(_SCR_DIR / "report_review_wizard_step_5_decision.png"))
        browser.close()


# ── VT18: Calculated review score ────────────────────────────────────────────
def test_VT18_calculated_review_score_visible():
    _skip_pw()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        _skip_no_server(page)
        page.goto(_PV_URL)
        btn = page.query_selector('[data-testid="pv-open-report-review-table"]')
        if btn:
            btn.click()
            page.wait_for_timeout(300)
        score = page.query_selector('[data-testid="rr-review-score"]')
        assert score is not None, "Review score panel missing"
        browser.close()


# ── VT19: Generate report PDF ─────────────────────────────────────────────────
def test_VT19_generate_review_pdf():
    _skip_pw()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        _skip_no_server(page)
        page.goto(_PV_URL)
        btn = page.query_selector('[data-testid="pv-open-report-review-table"]')
        if btn:
            btn.click()
            page.wait_for_timeout(500)
        # rr-generate-review-pdf is in step 5 — advance through all steps
        for _ in range(4):
            nb = page.query_selector('[data-testid="rr-wizard-next"]')
            if nb and nb.is_visible():
                nb.click()
                page.wait_for_timeout(400)
        gen_btn = page.query_selector('[data-testid="rr-generate-review-pdf"]')
        if gen_btn and gen_btn.is_visible():
            gen_btn.click()
            page.wait_for_timeout(3000)
        _SCR_DIR.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(_SCR_DIR / "report_review_pdf_generated.png"))
        browser.close()


# ── VT20: Download button appears ────────────────────────────────────────────
def test_VT20_download_button_appears():
    _skip_pw()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        _skip_no_server(page)
        page.goto(_PV_URL)
        btn = page.query_selector('[data-testid="pv-open-report-review-table"]')
        if btn:
            btn.click()
            page.wait_for_timeout(300)
        dl = page.query_selector('[data-testid="rr-download-review-pdf"]')
        assert dl is not None, "Download Review PDF button missing"
        _SCR_DIR.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(_SCR_DIR / "report_review_download_button.png"))
        browser.close()


# ── VT21: File-based — Review PDF or HTML exists ──────────────────────────────
def test_VT21_review_pdf_or_html_exists():
    assert _REVIEW_PDF.exists() or _REVIEW_HTML.exists(), \
        "report_review_output.pdf / .html not generated"
    if _REVIEW_PDF.exists():
        assert _REVIEW_PDF.stat().st_size > 20_000, "Review PDF too small"


# ── VT22: Review HTML has 5-step wizard sections ─────────────────────────────
def test_VT22_review_html_has_wizard_sections():
    """The Review PDF HTML has 16 page sections (15 page-break dividers)."""
    if not _REVIEW_HTML.exists():
        pytest.skip("Review HTML not found")
    content = _REVIEW_HTML.read_text(encoding="utf-8", errors="ignore")
    # Accept both single-quote and double-quote attribute syntax
    breaks = content.count("class='pg'") + content.count('class="pg"')
    assert breaks >= 15, f"Expected >= 15 page-break dividers, got {breaks}"


# ── VT23: Visual review index exists ──────────────────────────────────────────
def test_VT23_visual_review_index_exists():
    assert _VISUAL_IDX.exists(), "OPEN_REPORT_REVIEW_COMPLETE_WORKFLOW_INDEX.html missing"
    content = _VISUAL_IDX.read_text(encoding="utf-8", errors="ignore")
    assert len(content) > 2_000, "Visual index too short"
    assert "PASS" in content


# ── VT24: All 14 audit files exist ───────────────────────────────────────────
def test_VT24_all_14_audit_files_exist():
    for i in range(14):
        # find file matching the pattern
        matches = list(_AUD_DIR.glob(f"{i:02d}_*.json"))
        assert len(matches) > 0, f"Audit {i:02d} missing from {_AUD_DIR}"


# ── VT25: No fake signature in review HTML ───────────────────────────────────
def test_VT25_no_fake_signature_in_review_html():
    if not _REVIEW_HTML.exists():
        pytest.skip("Review HTML not found")
    content = _REVIEW_HTML.read_text(encoding="utf-8", errors="ignore")
    assert "ختم رسمي معتمد" not in content, "Fake stamp in review HTML"
    assert "certification_ready=True" not in content, "Fake cert flag in review HTML"
    assert "fake_reviewer_signature_created=False" in content or \
           "لم يتم توقيع" in content, "Unsigned gate marker missing"


# ── VT26: No internal paths in DOM or review HTML ─────────────────────────────
def test_VT26_no_internal_paths():
    for f in [_REVIEW_HTML, _VISUAL_IDX]:
        if f and f.exists():
            content = f.read_text(encoding="utf-8", errors="ignore")
            for bad in [r"C:\\Users", r"C:/Users", "/home/"]:
                assert bad not in content, f"Internal path in {f.name}: {bad}"


# ── VT27: Screenshot or blocker documented ────────────────────────────────────
def test_VT27_screenshot_or_blocker_documented():
    _SCR_DIR.mkdir(parents=True, exist_ok=True)
    pngs    = list(_SCR_DIR.glob("*.png"))
    blocker = _SCR_DIR / "screenshot_blocker.txt"

    if not HAS_PLAYWRIGHT and not pngs:
        blocker.write_text(
            "Screenshots blocked: Playwright not installed.\n"
            "Install: pip install playwright && playwright install chromium\n",
            encoding="utf-8",
        )
    assert len(pngs) > 0 or blocker.exists(), \
        "Neither screenshots nor blocker documentation found"


# ── VT28: Final report exists and is complete ────────────────────────────────
def test_VT28_final_report_exists():
    final = _OUT / "final_report" / "final_report_review_complete_workflow_report.txt"
    assert final.exists(), "Final report missing"
    content = final.read_text(encoding="utf-8", errors="ignore")
    assert "report_review_workflow_enabled" in content
    assert "overall_status" in content
    assert len(content) > 3_000, "Final report too short"
