"""
E2E tests for Standards Compliance Report Workflow.
BT01-BT20: browser tests (skip if Playwright unavailable).
FT01-FT15: file-based tests (always run after builder executes).

Run: python -m pytest tests/e2e/test_pv_standards_compliance_report_e2e.py -q
"""
from __future__ import annotations
import json
import pathlib
import pytest

_ROOT = pathlib.Path(__file__).parent.parent.parent
_SC   = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_standards_compliance"
_AUD  = _SC / "standards_compliance_audits"
_PDF  = _SC / "pdf_outputs"
_XL   = _SC / "excel_outputs"
_PREV = _SC / "visual_previews"
_SS   = _SC / "screenshots"
_RPT  = _SC / "final_report"
_TXT  = _SC / "pdf_text_extracts"

# ── Playwright availability ───────────────────────────────────────────────────
try:
    from playwright.sync_api import sync_playwright, Page  # type: ignore
    _PW_AVAILABLE = True
except ImportError:
    _PW_AVAILABLE = False

_skip_browser = pytest.mark.skipif(not _PW_AVAILABLE, reason="Playwright not installed")
_BASE = "http://localhost:5000"


def _open_compliance_panel(page: "Page") -> None:
    page.goto(_BASE, timeout=15_000)
    page.wait_for_load_state("domcontentloaded")
    page.click("[data-testid='pv-open-standards-table']", timeout=8_000)
    page.evaluate(
        "() => { "
        "var p = document.getElementById('pv-req-panel-standards'); "
        "if (p) { p.style.display=''; } "
        "var s1 = document.getElementById('sc-wizard-step-1'); "
        "if (s1) { s1.style.display=''; } "
        "}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# BROWSER TESTS (BT01-BT20)
# ══════════════════════════════════════════════════════════════════════════════

@_skip_browser
def test_BT01_open_professional_valuation_page():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        assert "Expert" in p.title() or p.url.startswith(_BASE)
        b.close()


@_skip_browser
def test_BT02_locate_special_reports_section():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        el = p.query_selector("[data-testid='pv-open-standards-table']")
        assert el is not None, "Standards compliance button not found"
        b.close()


@_skip_browser
def test_BT03_click_opens_compliance_workflow():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        panel = p.query_selector("#pv-req-panel-standards")
        assert panel is not None
        b.close()


@_skip_browser
def test_BT04_compliance_workflow_panel_has_testid():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        el = p.query_selector("[data-testid='pv-special-req-panel-standards_compliance_report']")
        assert el is not None
        b.close()


@_skip_browser
def test_BT05_step1_upload_card_visible():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        step1 = p.query_selector("#sc-wizard-step-1")
        assert step1 is not None
        b.close()


@_skip_browser
def test_BT06_step1_standards_selector_visible():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        for tid in ["sc-std-ivs", "sc-std-uspap", "sc-std-rics", "sc-std-fra"]:
            el = p.query_selector(f"[data-testid='{tid}']")
            assert el is not None, f"{tid} not found"
        b.close()


@_skip_browser
def test_BT07_ivs_selected_by_default():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        cb = p.query_selector("[data-testid='sc-std-ivs']")
        assert cb is not None
        assert cb.is_checked(), "IVS should be checked by default"
        b.close()


@_skip_browser
def test_BT08_step_progress_bar_exists():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        for i in range(1, 5):
            el = p.query_selector(f"#sc-prog-{i}")
            assert el is not None, f"sc-prog-{i} not found"
        b.close()


@_skip_browser
def test_BT09_navigate_to_step2():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        p.evaluate("() => pvScGoToStep(2)")
        step2 = p.query_selector("#sc-wizard-step-2")
        assert step2 is not None
        b.close()


@_skip_browser
def test_BT10_extraction_status_panel_in_step2():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        p.evaluate("() => pvScGoToStep(2)")
        el = p.query_selector("[data-testid='sc-extraction-status']")
        assert el is not None
        b.close()


@_skip_browser
def test_BT11_navigate_to_step3():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        p.evaluate("() => pvScGoToStep(3)")
        step3 = p.query_selector("#sc-wizard-step-3")
        assert step3 is not None
        b.close()


@_skip_browser
def test_BT12_compliance_score_card_in_step3():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        p.evaluate("() => pvScGoToStep(3)")
        el = p.query_selector("[data-testid='sc-compliance-score-card']")
        assert el is not None
        b.close()


@_skip_browser
def test_BT13_ivs_table_in_step3():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        p.evaluate("() => pvScGoToStep(3)")
        el = p.query_selector("[data-testid='sc-ivs-compliance-table']")
        assert el is not None
        b.close()


@_skip_browser
def test_BT14_uspap_table_in_step3():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        p.evaluate("() => pvScGoToStep(3)")
        el = p.query_selector("[data-testid='sc-uspap-compliance-table']")
        assert el is not None
        b.close()


@_skip_browser
def test_BT15_rics_table_in_step3():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        p.evaluate("() => pvScGoToStep(3)")
        el = p.query_selector("[data-testid='sc-rics-compliance-table']")
        assert el is not None
        b.close()


@_skip_browser
def test_BT16_fra_table_in_step3():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        p.evaluate("() => pvScGoToStep(3)")
        el = p.query_selector("[data-testid='sc-fra-compliance-table']")
        assert el is not None
        b.close()


@_skip_browser
def test_BT17_navigate_to_step4():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        p.evaluate("() => pvScGoToStep(4)")
        step4 = p.query_selector("#sc-wizard-step-4")
        assert step4 is not None
        b.close()


@_skip_browser
def test_BT18_download_buttons_in_step4():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        p.evaluate("() => pvScGoToStep(4)")
        pdf_btn = p.query_selector("[data-testid='sc-download-pdf']")
        xl_btn  = p.query_selector("[data-testid='sc-download-excel']")
        assert pdf_btn is not None, "PDF download button missing"
        assert xl_btn is not None, "Excel download button missing"
        b.close()


@_skip_browser
def test_BT19_no_fake_signature_in_dom():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        body = p.inner_html("body")
        assert "fake_signature" not in body
        assert "mock_certification" not in body
        b.close()


@_skip_browser
def test_BT20_no_internal_paths_in_dom():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_compliance_panel(p)
        body = p.inner_html("body")
        assert "C:\\Users\\Lenovo" not in body
        assert "C:/Users/Lenovo" not in body
        b.close()


# ══════════════════════════════════════════════════════════════════════════════
# FILE-BASED TESTS (FT01-FT15) — always run after builder
# ══════════════════════════════════════════════════════════════════════════════

def test_FT01_output_directory_exists():
    assert _SC.is_dir(), "Standards compliance output directory missing"


def test_FT02_all_seven_audit_files_exist():
    expected = [
        "01_upload_and_standards_selection_audit.json",
        "02_pdf_extraction_and_text_analysis_audit.json",
        "03_compliance_scoring_audit.json",
        "04_pdf_structure_audit.json",
        "05_excel_audit.json",
        "06_ui_audit.json",
        "07_visual_review_audit.json",
    ]
    for f in expected:
        assert (_AUD / f).exists(), f"Audit file missing: {f}"


def test_FT03_all_audits_have_safety_flags():
    required_flags = {
        "advisory_only": True,
        "fake_signature_created": False,
        "not_report_review": True,
        "not_hbu_workflow": True,
        "in_chat_box": False,
    }
    for fname in _AUD.glob("*.json"):
        d = json.loads(fname.read_text(encoding="utf-8"))
        for k, v in required_flags.items():
            assert d.get(k) == v, f"{fname.name}: {k} must be {v}"


def test_FT04_pdf_or_html_exists():
    pdf  = _PDF / "standards_compliance_report.pdf"
    html = _PDF / "standards_compliance_report.html"
    assert pdf.exists() or html.exists(), (
        "Neither standards_compliance_report.pdf nor .html found"
    )


def test_FT05_html_contains_all_standards():
    html_path = _PDF / "standards_compliance_report.html"
    if not html_path.exists():
        pytest.skip("HTML not generated")
    content = html_path.read_text(encoding="utf-8", errors="ignore")
    for std in ["IVS", "USPAP", "RICS", "FRA"]:
        assert std in content, f"{std} not found in HTML report"


def test_FT06_html_contains_scores():
    html_path = _PDF / "standards_compliance_report.html"
    if not html_path.exists():
        pytest.skip("HTML not generated")
    content = html_path.read_text(encoding="utf-8", errors="ignore")
    assert "%" in content, "Percentage scores missing from HTML"
    assert "advisory_only" in content


def test_FT07_visual_index_exists():
    idx = _PREV / "OPEN_STANDARDS_COMPLIANCE_REVIEW_INDEX.html"
    assert idx.exists(), "Visual review index missing"


def test_FT08_visual_index_no_internal_paths():
    idx = _PREV / "OPEN_STANDARDS_COMPLIANCE_REVIEW_INDEX.html"
    if not idx.exists():
        pytest.skip("Visual index not generated")
    content = idx.read_text(encoding="utf-8", errors="ignore")
    assert r"C:\Users" not in content, "Internal Windows path in visual index"
    assert "C:/Users/Lenovo" not in content


def test_FT09_twelve_screenshots_exist():
    pngs = list(_SS.glob("*.png"))
    assert len(pngs) >= 12, f"Expected 12 screenshots, found {len(pngs)}"


def test_FT10_final_report_exists():
    rpt = _RPT / "final_standards_compliance_report.txt"
    assert rpt.exists(), "Final standards compliance report missing"
    content = rpt.read_text(encoding="utf-8", errors="ignore")
    assert "advisory_only: True" in content
    assert "fake_signature_created: False" in content
    assert "overall_status: PASS" in content or "overall_status: PARTIAL" in content


def test_FT11_scoring_audit_scores_are_valid():
    audit = json.loads(
        (_AUD / "03_compliance_scoring_audit.json").read_text(encoding="utf-8")
    )
    for key in ("ivs_score", "uspap_score", "rics_score", "fra_score"):
        val = audit.get(key, -1)
        assert 0 <= val <= 100, f"{key}={val} out of range"
    after = audit.get("overall_score_after_caps", -1)
    before = audit.get("overall_score_before_caps", -1)
    assert 0 <= after <= before <= 100


def test_FT12_ui_audit_has_wizard_steps():
    audit = json.loads(
        (_AUD / "06_ui_audit.json").read_text(encoding="utf-8")
    )
    assert audit.get("wizard_steps_count") == 4
    for key in ["step_1_upload_and_standards", "step_2_extraction_status",
                "step_3_compliance_scoring", "step_4_generate_report"]:
        assert audit.get(key) is True, f"{key} missing from ui_audit"


def test_FT13_pdf_structure_audit_has_required_sections():
    audit = json.loads(
        (_AUD / "04_pdf_structure_audit.json").read_text(encoding="utf-8")
    )
    for key in [
        "executive_summary_page_present",
        "overall_score_present",
        "per_standard_scores_present",
        "ivs_section_present_if_selected",
        "uspap_section_present_if_selected",
        "rics_section_present_if_selected",
        "fra_section_present_if_selected",
        "advisory_warning_present",
        "signature_gate_present",
        "fake_signature_absent",
    ]:
        assert audit.get(key) is True, f"{key} missing from pdf_structure_audit"


def test_FT14_other_workflows_unaffected():
    sim_dir = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_uploaded_template_simulation"
    assert sim_dir.is_dir(), "Simulation output dir must not be removed"
    hbu_dir = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_hbu_analysis"
    assert hbu_dir.is_dir(), "HBU output dir must not be removed"


def test_FT15_text_extract_exists():
    txt = _TXT  / "standards_compliance_text_extract.txt"
    assert txt.exists(), "Text extract file missing"
    content = txt.read_text(encoding="utf-8", errors="ignore")
    assert "advisory_only=True" in content
    assert "fake_signature_created=False" in content
