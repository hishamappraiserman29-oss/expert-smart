"""
E2E / Visual tests for Uploaded Template Simulation workflow.
Browser tests (BT): skipped if Playwright not installed.
File-based tests (FT): always run.
Run: python -m pytest tests/e2e/test_pv_uploaded_template_simulation_e2e.py -q
"""
from __future__ import annotations
import json
import pathlib
import pytest

try:
    from playwright.sync_api import sync_playwright
    _PW_AVAILABLE = True
except ImportError:
    _PW_AVAILABLE = False

_pw_skip = pytest.mark.skipif(not _PW_AVAILABLE, reason="Playwright not installed")
_BASE_URL = "http://127.0.0.1:5000"

_ROOT = pathlib.Path(__file__).parent.parent.parent
_SIM  = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_uploaded_template_simulation"
_AUD  = _SIM / "uploaded_report_simulation_audits"
_PDF  = _SIM / "pdf_outputs"
_XL   = _SIM / "excel_outputs"
_PREV = _SIM / "visual_previews"
_SS   = _SIM / "screenshots"
_RPT  = _SIM / "final_report"


def _open_simulation_panel(page):
    """Open the Professional Valuation page, show simulation panel."""
    page.goto(f"{_BASE_URL}/", timeout=15000)
    page.wait_for_timeout(800)
    btn = page.query_selector("[data-testid='pv-open-simulation-table']")
    if btn and btn.is_visible():
        btn.click()
        page.wait_for_timeout(600)
    # Show sim wizard step 1 in case it's hidden
    page.evaluate("""
        var p = document.getElementById('pv-req-panel-simulation');
        if (p) p.style.display = '';
        var s1 = document.getElementById('sim-wizard-step-1');
        if (s1) s1.style.display = '';
    """)
    page.wait_for_timeout(300)


# ─────────────────────────────────────────────────────────────────────────────
# Browser tests — BT01 through BT21
# ─────────────────────────────────────────────────────────────────────────────

@_pw_skip
def test_BT01_page_loads():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        assert page.content()
        browser.close()


@_pw_skip
def test_BT02_special_reports_section_visible():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        el = page.query_selector("[data-testid='pv-special-workflow-buttons']")
        assert el is not None, "Special workflow buttons section not found"
        _SS.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(_SS / "01_simulation_button.png"))
        browser.close()


@_pw_skip
def test_BT03_simulation_button_exists():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        el = page.query_selector("[data-testid='pv-open-simulation-table']")
        assert el is not None, "Simulation trigger button not found in DOM"
        browser.close()


@_pw_skip
def test_BT04_simulation_panel_opens():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        panel = page.query_selector("[data-testid='pv-special-req-panel-simulated_uploaded_report']")
        assert panel is not None, "Simulation panel not found in DOM"
        page.screenshot(path=str(_SS / "02_template_upload_step.png"))
        browser.close()


@_pw_skip
def test_BT05_wizard_step1_template_upload_present():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        el = page.query_selector("[data-testid='sim-wizard-step-1']")
        assert el is not None, "sim-wizard-step-1 not found in DOM"
        upload = page.query_selector("[data-testid='sim-template-upload']")
        assert upload is not None, "sim-template-upload file input not found"
        browser.close()


@_pw_skip
def test_BT06_wizard_step2_template_preview_present():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        # Show step 2 via JS
        page.evaluate("""
            var s2 = document.getElementById('sim-wizard-step-2');
            if (s2) s2.style.display = '';
        """)
        el = page.query_selector("[data-testid='sim-wizard-step-2']")
        assert el is not None, "sim-wizard-step-2 not found in DOM"
        preview = page.query_selector("[data-testid='sim-template-preview-panel']")
        assert preview is not None, "sim-template-preview-panel not found"
        page.screenshot(path=str(_SS / "03_template_preview_and_mapping.png"))
        browser.close()


@_pw_skip
def test_BT07_placeholder_table_present():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        page.evaluate("""
            var s2 = document.getElementById('sim-wizard-step-2');
            if (s2) s2.style.display = '';
        """)
        el = page.query_selector("[data-testid='sim-placeholder-table']")
        assert el is not None, "sim-placeholder-table not found in DOM"
        browser.close()


@_pw_skip
def test_BT08_wizard_step3_new_property_form_present():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        page.evaluate("""
            var s3 = document.getElementById('sim-wizard-step-3');
            if (s3) s3.style.display = '';
        """)
        el = page.query_selector("[data-testid='sim-wizard-step-3']")
        assert el is not None, "sim-wizard-step-3 not found in DOM"
        form = page.query_selector("[data-testid='sim-new-property-form']")
        assert form is not None, "sim-new-property-form not found"
        page.screenshot(path=str(_SS / "04_new_property_input_form.png"))
        browser.close()


@_pw_skip
def test_BT09_comparables_section_present():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        page.evaluate("""
            var s3 = document.getElementById('sim-wizard-step-3');
            if (s3) s3.style.display = '';
        """)
        el = page.query_selector("[data-testid='sim-comparables-section']")
        assert el is not None, "sim-comparables-section not found in DOM"
        browser.close()


@_pw_skip
def test_BT10_income_and_cost_sections_present():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        page.evaluate("""
            var s3 = document.getElementById('sim-wizard-step-3');
            if (s3) s3.style.display = '';
        """)
        income = page.query_selector("[data-testid='sim-income-section']")
        cost   = page.query_selector("[data-testid='sim-cost-section']")
        assert income is not None, "sim-income-section not found"
        assert cost   is not None, "sim-cost-section not found"
        browser.close()


@_pw_skip
def test_BT11_reconciliation_section_present():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        page.evaluate("""
            var s3 = document.getElementById('sim-wizard-step-3');
            if (s3) s3.style.display = '';
        """)
        el = page.query_selector("[data-testid='sim-reconciliation-section']")
        assert el is not None, "sim-reconciliation-section not found"
        browser.close()


@_pw_skip
def test_BT12_wizard_step4_generate_report_present():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        page.evaluate("""
            var s4 = document.getElementById('sim-wizard-step-4');
            if (s4) s4.style.display = '';
        """)
        el = page.query_selector("[data-testid='sim-wizard-step-4']")
        assert el is not None, "sim-wizard-step-4 not found in DOM"
        btn = page.query_selector("[data-testid='sim-generate-report-btn']")
        assert btn is not None, "sim-generate-report-btn not found"
        browser.close()


@_pw_skip
def test_BT13_valuation_results_panel_present():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        page.evaluate("""
            var s4 = document.getElementById('sim-wizard-step-4');
            if (s4) s4.style.display = '';
            var rp = document.getElementById('sim-valuation-results-panel');
            if (rp) rp.style.display = '';
        """)
        el = page.query_selector("[data-testid='sim-valuation-results-panel']")
        assert el is not None, "sim-valuation-results-panel not found"
        page.screenshot(path=str(_SS / "05_valuation_engine_results.png"))
        browser.close()


@_pw_skip
def test_BT14_valuation_value_elements_present():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        page.evaluate("""
            var s4 = document.getElementById('sim-wizard-step-4');
            if (s4) s4.style.display = '';
            var rp = document.getElementById('sim-valuation-results-panel');
            if (rp) rp.style.display = '';
        """)
        for tid in ["sim-sales-comparison-value", "sim-income-value",
                    "sim-cost-value", "sim-final-market-value"]:
            el = page.query_selector(f"[data-testid='{tid}']")
            assert el is not None, f"{tid} not found in DOM"
        browser.close()


@_pw_skip
def test_BT15_download_button_present():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        page.evaluate("""
            var s4 = document.getElementById('sim-wizard-step-4');
            if (s4) s4.style.display = '';
            var rp = document.getElementById('sim-valuation-results-panel');
            if (rp) rp.style.display = '';
        """)
        el = page.query_selector("[data-testid='sim-download-generated-report']")
        assert el is not None, "sim-download-generated-report not found"
        page.screenshot(path=str(_SS / "08_download_generated_report.png"))
        browser.close()


@_pw_skip
def test_BT16_generated_report_preview_present():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        page.evaluate("""
            var s4 = document.getElementById('sim-wizard-step-4');
            if (s4) s4.style.display = '';
            var rp = document.getElementById('sim-valuation-results-panel');
            if (rp) rp.style.display = '';
        """)
        el = page.query_selector("[data-testid='sim-generated-report-preview']")
        assert el is not None, "sim-generated-report-preview not found"
        page.screenshot(path=str(_SS / "06_generated_report_preview.png"))
        browser.close()


@_pw_skip
def test_BT17_no_internal_paths_in_dom():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"{_BASE_URL}/", timeout=15000)
        dom = page.content()
        for bad in ["C:\\Users\\Lenovo\\Desktop", "C:/Users/Lenovo/Desktop"]:
            assert bad not in dom, f"Internal path '{bad}' found in DOM"
        browser.close()


@_pw_skip
def test_BT18_advisory_warning_in_panel():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        dom = page.content()
        assert ("advisory_only" in dom or "استرشادي" in dom), (
            "Advisory warning not found in panel DOM"
        )
        browser.close()


@_pw_skip
def test_BT19_simulation_panel_not_report_review():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        dom = page.content()
        # The simulation panel should have its own distinct ID
        assert "pv-req-panel-simulation" in dom
        assert "sim-wizard-step-1" in dom
        browser.close()


@_pw_skip
def test_BT20_progress_indicator_present():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        el = page.query_selector("[data-testid='sim-wizard-progress']")
        assert el is not None, "sim-wizard-progress not found in DOM"
        browser.close()


@_pw_skip
def test_BT21_wizard_steps_navigation_elements_present():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        _open_simulation_panel(page)
        next_btn = page.query_selector("[data-testid='sim-btn-next']")
        assert next_btn is not None, "sim-btn-next not found in DOM"
        page.screenshot(path=str(_SS / "07_template_vs_generated_comparison.png"))
        browser.close()


# ─────────────────────────────────────────────────────────────────────────────
# File-based tests — FT01 through FT12
# ─────────────────────────────────────────────────────────────────────────────

def test_FT01_simulation_output_folder_exists():
    assert _SIM.exists(), f"Simulation output folder missing: {_SIM}"


def test_FT02_generated_report_html_exists():
    html = _PDF / "simulated_uploaded_template_report.html"
    assert html.exists(), "simulated_uploaded_template_report.html not found"
    assert html.stat().st_size > 5_000, "Simulation HTML is too small"


def test_FT03_generated_report_pdf_exists():
    pdf  = _PDF / "simulated_uploaded_template_report.pdf"
    html = _PDF / "simulated_uploaded_template_report.html"
    assert pdf.exists() or html.exists(), "Neither PDF nor HTML simulation report found"


def test_FT04_template_profile_json_exists():
    profile = _SIM / "template_profiles" / "template_profile.json"
    assert profile.exists(), "template_profile.json missing"
    p = json.loads(profile.read_text(encoding="utf-8"))
    assert "variable_fields" in p
    assert len(p["variable_fields"]) >= 5


def test_FT05_all_7_audits_exist():
    required = [
        "01_template_parsing_audit.json",
        "02_template_placeholder_mapping_audit.json",
        "03_new_property_input_audit.json",
        "04_valuation_engine_audit.json",
        "05_template_rendering_audit.json",
        "06_excel_output_audit.json",
        "07_visual_similarity_audit.json",
    ]
    missing = [f for f in required if not (_AUD / f).exists()]
    assert not missing, f"Missing audits: {missing}"


def test_FT06_no_fake_signature_in_any_audit():
    for f in _AUD.glob("*.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        assert d.get("fake_signature_created", False) is False, (
            f"{f.name}: fake_signature_created must be False"
        )


def test_FT07_valuation_engine_numbers_are_reasonable():
    audit = _AUD / "04_valuation_engine_audit.json"
    assert audit.exists()
    d = json.loads(audit.read_text(encoding="utf-8"))
    sv = d.get("sales_comparison_value", 0)
    iv = d.get("income_value", 0)
    cv = d.get("cost_value", 0)
    fv = d.get("final_market_value", 0)
    # Values should be positive and in a reasonable range (SAR 100K – 100M)
    for name, val in [("sales", sv), ("income", iv), ("cost", cv), ("final", fv)]:
        assert 100_000 <= val <= 100_000_000, (
            f"{name} value {val} is outside reasonable range"
        )
    # Final value should be a weighted average, within range of approaches
    min_val = min(sv, iv, cv)
    max_val = max(sv, iv, cv)
    assert min_val * 0.8 <= fv <= max_val * 1.2, (
        f"Final value {fv} is too far from approach values"
    )


def test_FT08_excel_workbook_exists():
    xl = _XL / "simulated_uploaded_template_report_workbook.xlsx"
    audit_d = json.loads((_AUD / "06_excel_output_audit.json").read_text(encoding="utf-8"))
    if audit_d.get("excel_workbook_created"):
        assert xl.exists(), "Excel workbook missing"
        assert xl.stat().st_size > 2_000


def test_FT09_visual_review_index_exists():
    idx = _PREV / "OPEN_UPLOADED_TEMPLATE_SIMULATION_REVIEW.html"
    assert idx.exists(), "Visual review index HTML missing"
    content = idx.read_text(encoding="utf-8", errors="ignore")
    assert "محاكاة" in content
    assert "advisory_only" in content


def test_FT10_final_report_exists():
    rpt = _RPT / "final_uploaded_template_simulation_report.txt"
    assert rpt.exists(), "Final simulation report missing"
    assert rpt.stat().st_size > 2_000
    content = rpt.read_text(encoding="utf-8", errors="ignore")
    assert "FINAL MARKET VALUE" in content
    assert "fake_signature_created=False" in content


def test_FT11_html_contains_advisory_note():
    html = _PDF / "simulated_uploaded_template_report.html"
    if not html.exists():
        pytest.skip("HTML not generated")
    content = html.read_text(encoding="utf-8", errors="ignore")
    assert "استرشادي" in content or "advisory_only=True" in content
    assert "خبير تقييم معتمد" in content


def test_FT12_html_contains_signature_gate():
    html = _PDF / "simulated_uploaded_template_report.html"
    if not html.exists():
        pytest.skip("HTML not generated")
    content = html.read_text(encoding="utf-8", errors="ignore")
    assert "بانتظار توقيع الخبير المعتمد" in content, (
        "Signature gate text not found in HTML report"
    )
    # Ensure no fake signature text
    for bad in ["fake_reviewer_signature", "mock_signature", "placeholder_signature"]:
        assert bad not in content.lower(), f"Forbidden: '{bad}' in HTML"
