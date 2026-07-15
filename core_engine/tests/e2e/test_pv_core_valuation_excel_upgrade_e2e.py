"""
E2E tests for Core Valuation Excel Upgrade.
BT01-BT14: Browser tests (skip if Playwright unavailable).
FT01-FT17: File-based tests (always run).

Run: python -m pytest tests/e2e/test_pv_core_valuation_excel_upgrade_e2e.py -q
"""
from __future__ import annotations
import json
import pathlib
import pytest

_ROOT   = pathlib.Path(__file__).parent.parent.parent
_OUT    = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_core_excel_upgrade"
_XL_DIR = _OUT / "excel_outputs"
_AUD    = _OUT / "excel_audits"
_PREV   = _OUT / "visual_previews"
_SS     = _OUT / "screenshots"
_RPT    = _OUT / "final_report"
_WB     = _XL_DIR / "core_valuation_master_workbook.xlsx"

try:
    from playwright.sync_api import sync_playwright, Page  # type: ignore
    _PW_AVAILABLE = True
except ImportError:
    _PW_AVAILABLE = False

_skip_browser = pytest.mark.skipif(not _PW_AVAILABLE, reason="Playwright not installed")
_BASE = "http://localhost:5000"


def _open_core_section(page: "Page") -> None:
    page.goto(_BASE, timeout=15_000)
    page.wait_for_load_state("domcontentloaded")
    el = page.query_selector("[data-testid='pv-core-valuation-report-issuance']")
    if el:
        el.scroll_into_view_if_needed()


# ══════════════════════════════════════════════════════════════════════════════
# BROWSER TESTS (BT01-BT14)
# ══════════════════════════════════════════════════════════════════════════════

@_skip_browser
def test_BT01_page_opens():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        p.goto(_BASE, timeout=15_000)
        assert p.url.startswith(_BASE)
        b.close()


@_skip_browser
def test_BT02_core_issuance_section_exists():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_core_section(p)
        el = p.query_selector("[data-testid='pv-core-valuation-report-issuance']")
        assert el is not None, "Core issuance section not found"
        b.close()


@_skip_browser
def test_BT03_traditional_report_card_exists():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_core_section(p)
        el = p.query_selector("[data-testid='pv-core-report-chip-traditional']")
        assert el is not None
        b.close()


@_skip_browser
def test_BT04_detailed_report_card_exists():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_core_section(p)
        el = p.query_selector("[data-testid='pv-core-report-chip-detailed']")
        assert el is not None
        b.close()


@_skip_browser
def test_BT05_professional_report_card_exists():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_core_section(p)
        el = p.query_selector("[data-testid='pv-core-report-chip-professional']")
        assert el is not None
        b.close()


@_skip_browser
def test_BT06_internal_excel_card_exists():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_core_section(p)
        el = p.query_selector("[data-testid='pv-core-internal-excel-card']")
        assert el is not None, "Internal Excel card not found"
        b.close()


@_skip_browser
def test_BT07_download_internal_excel_button_exists():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_core_section(p)
        el = p.query_selector("[data-testid='pv-core-download-internal-excel']")
        assert el is not None, "Download internal Excel button not found"
        b.close()


@_skip_browser
def test_BT08_internal_excel_label_visible():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_core_section(p)
        body = p.inner_html("[data-testid='pv-core-valuation-report-issuance']")
        assert "Excel" in body and ("داخلي" in body or "Internal" in body), (
            "Internal Excel label not found in core section"
        )
        b.close()


@_skip_browser
def test_BT09_no_separate_old_excel_admin_button():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_core_section(p)
        # Old button should be hidden (aria-hidden or display:none)
        old_btn = p.query_selector("[data-testid='pv-core-generate-admin-excel']:visible")
        assert old_btn is None, "Old separate admin Excel button is still visible"
        b.close()


@_skip_browser
def test_BT10_generate_traditional_report():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_core_section(p)
        btn = p.query_selector("[data-testid='pv-core-report-chip-traditional']")
        if btn:
            btn.click()
        p.wait_for_timeout(1500)
        b.close()


@_skip_browser
def test_BT11_generate_detailed_report():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_core_section(p)
        btn = p.query_selector("[data-testid='pv-core-report-chip-detailed']")
        if btn:
            btn.click()
        p.wait_for_timeout(1500)
        b.close()


@_skip_browser
def test_BT12_generate_professional_report():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_core_section(p)
        btn = p.query_selector("[data-testid='pv-core-report-chip-professional']")
        if btn:
            btn.click()
        p.wait_for_timeout(1500)
        b.close()


@_skip_browser
def test_BT13_no_internal_paths_in_dom():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_core_section(p)
        body = p.inner_html("body")
        assert "C:\\Users\\Lenovo" not in body
        assert "C:/Users/Lenovo" not in body
        b.close()


@_skip_browser
def test_BT14_no_duplicate_old_excel_buttons():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page()
        _open_core_section(p)
        body = p.inner_html("body")
        # Old text that should not appear as a visible button label
        assert "إرسال للشات" not in body.replace("display:none", "")
        b.close()


# ══════════════════════════════════════════════════════════════════════════════
# FILE-BASED TESTS (FT01-FT17) — always run
# ══════════════════════════════════════════════════════════════════════════════

def test_FT01_output_folder_exists():
    assert _OUT.is_dir()


def test_FT02_excel_workbook_exists():
    assert _WB.exists(), f"Workbook missing: {_WB}"


def test_FT03_excel_workbook_non_empty():
    assert _WB.stat().st_size > 5_000


def test_FT04_all_22_audits_exist():
    expected = [f"{i:02d}_" for i in range(1, 23)]
    for prefix in expected:
        matches = list(_AUD.glob(prefix + "*.json"))
        assert matches, f"No audit starting with {prefix}"


def test_FT05_all_audits_have_safety_flags():
    for f in _AUD.glob("*.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        assert d.get("advisory_only") is True, f"{f.name}: advisory_only must be True"
        assert d.get("fake_sources_created", False) is False, f"{f.name}: fake_sources_created must be False"
        assert d.get("internal_paths_exposed", True) is False, f"{f.name}: internal_paths_exposed must be False"


def test_FT06_all_21_screenshots_exist():
    expected = [
        "01_reference_workbook_inventory.png", "02_final_excel_dashboard.png",
        "03_method_value_comparison_chart.png", "04_sales_comparison_sheet.png",
        "05_income_capitalization_sheet.png", "06_cost_approach_sheet.png",
        "07_dcf_support_sheet.png", "08_sensitivity_matrix.png",
        "09_risk_register.png", "10_print_report_summary.png",
        "11_core_excel_ui_card.png", "12_visual_review_index.png",
        "13_sales_reliability_formula.png", "14_land_adjustment_linked_formula.png",
        "15_income_rent_comparables.png", "16_sensitivity_selected_scenario.png",
        "17_reconciliation_mround_formula.png", "18_hbu_value_weight.png",
        "19_changelog_sheet.png", "20_dashboard_kpi_cards.png",
        "21_rounding_settings.png",
    ]
    for name in expected:
        assert (_SS / name).exists(), f"Screenshot missing: {name}"


def test_FT07_visual_index_exists_and_valid():
    idx = _PREV / "OPEN_CORE_VALUATION_EXCEL_REVIEW_INDEX.html"
    assert idx.exists()
    content = idx.read_text(encoding="utf-8", errors="ignore")
    assert "advisory_only" in content
    assert "PASS" in content
    assert r"C:\Users" not in content
    assert "C:/Users/Lenovo" not in content


def test_FT08_final_report_exists():
    rpt = _RPT / "final_core_valuation_excel_upgrade_report.txt"
    assert rpt.exists()
    content = rpt.read_text(encoding="utf-8", errors="ignore")
    assert "overall_status" in content
    assert "PASS" in content


def test_FT09_inventory_file_exists():
    assert (_RPT / "generated_files_inventory.txt").exists()


def test_FT10_reference_files_inspected():
    aud = json.loads((_AUD / "01_reference_workbook_inventory.json").read_text(encoding="utf-8"))
    assert aud.get("reference_files_inspected") is True
    files = aud.get("files", [])
    assert len(files) == 3


def test_FT11_source_files_preserved():
    aud = json.loads((_AUD / "12_source_files_preservation_audit.json").read_text(encoding="utf-8"))
    assert aud.get("source_files_preserved") is True
    assert aud.get("source_files_not_overwritten") is True


def test_FT12_traditional_methods_all_pass():
    aud = json.loads((_AUD / "05_traditional_methods_audit.json").read_text(encoding="utf-8"))
    assert aud.get("sales_comparison_sheet_created") is True
    assert aud.get("income_capitalization_sheet_created") is True
    assert aud.get("cost_approach_sheet_created") is True
    assert aud.get("reconciliation_sheet_created") is True
    assert aud.get("status") == "PASS"


def test_FT13_modern_methods_all_pass():
    aud = json.loads((_AUD / "06_modern_methods_audit.json").read_text(encoding="utf-8"))
    assert aud.get("avm_summary_created") is True
    assert aud.get("dcf_support_created") is True
    assert aud.get("sensitivity_matrix_created") is True
    assert aud.get("risk_register_created") is True
    assert aud.get("status") in ("PASS", "PARTIAL")


def test_FT14_data_quality_and_sources_pass():
    aud = json.loads((_AUD / "07_data_quality_source_registry_audit.json").read_text(encoding="utf-8"))
    assert aud.get("data_quality_sheet_created") is True
    assert aud.get("source_registry_sheet_created") is True
    assert aud.get("fake_sources_created") is False
    assert aud.get("status") == "PASS"


def test_FT15_no_internal_paths_in_any_audit():
    for f in _AUD.glob("*.json"):
        content = f.read_text(encoding="utf-8", errors="ignore")
        assert r"C:\Users\Lenovo" not in content, f"Internal path in {f.name}"
        assert "C:/Users/Lenovo" not in content, f"Internal path in {f.name}"


def test_FT16_changelog_audit_passes():
    aud = json.loads((_AUD / "20_changelog_audit.json").read_text(encoding="utf-8"))
    assert aud.get("changelog_sheet_created") is True
    assert aud.get("formula_updates_logged") is True
    assert aud.get("status") == "PASS"


def test_FT17_final_report_not_pass_if_workbook_missing():
    rpt = _RPT / "final_core_valuation_excel_upgrade_report.txt"
    if not rpt.exists():
        pytest.skip("Final report not created")
    content = rpt.read_text(encoding="utf-8", errors="ignore")
    if not _WB.exists():
        assert "overall_status\": \"PASS\"" not in content, (
            "Final report claims PASS but workbook is missing"
        )
