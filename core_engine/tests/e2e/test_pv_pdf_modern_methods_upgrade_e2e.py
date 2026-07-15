"""
test_pv_pdf_modern_methods_upgrade_e2e.py
اختبارات E2E — تحسين تقارير PDF لتعكس الأساليب الحديثة من Excel القديم

تشغيل الاختبارات الساكنة:
  python -m pytest core_engine/tests/e2e/test_pv_pdf_modern_methods_upgrade_e2e.py -q -m "not live_server"

arabic_primary=True | legacy_excel_methods=True | advisory_only=True
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_CORE     = Path(__file__).resolve().parent.parent.parent
_QA       = _CORE / "instance" / "manual_review_outputs" / "professional_valuation_pdf_modern_methods_upgrade"
_PDF      = _QA / "pdf_outputs"
_PREV     = _QA / "pdf_visual_previews"
_LEG      = _QA / "legacy_excel_audits"
_METH     = _QA / "method_coverage_audits"
_DIST     = _QA / "report_distinctness_audits"
_STRC     = _QA / "report_structure_audits"
_BASE_URL = "http://127.0.0.1:5000"

sys.path.insert(0, str(_CORE))

try:
    from playwright.sync_api import Page, expect
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Page = object  # type: ignore[misc]

_LIVE     = pytest.mark.live_server
_SKIP_NO_PW = pytest.mark.skipif(
    not PLAYWRIGHT_AVAILABLE,
    reason="playwright not installed — run: pip install playwright && playwright install chromium",
)


def _load(path: Path) -> dict:
    assert path.exists(), f"Audit file missing: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def _html(key: str) -> str:
    p = _PREV / f"{key}_preview.html"
    assert p.exists(), f"Missing preview: {p}"
    return p.read_text(encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════════
# STATIC TESTS — no live server required
# ═══════════════════════════════════════════════════════════════════════════════

def test_E01_qa_folder_exists():
    """E01: QA output folder exists."""
    assert _QA.exists()


def test_E02_pdf_outputs_exist():
    """E02: all three upgraded PDF outputs exist."""
    for name in ["traditional_report.pdf", "detailed_report.pdf", "professional_report.pdf"]:
        assert (_PDF / name).exists(), f"Missing PDF: {name}"


def test_E03_preview_htmls_exist():
    """E03: all three HTML preview files exist."""
    for key in ["traditional_report", "detailed_report", "professional_report"]:
        assert (_PREV / f"{key}_preview.html").exists(), f"Missing preview: {key}"


def test_E04_traditional_pdf_size():
    """E04: traditional_report.pdf is non-empty (>10KB)."""
    assert (_PDF / "traditional_report.pdf").stat().st_size > 10_000


def test_E05_detailed_pdf_significantly_larger_than_traditional():
    """E05: detailed PDF is significantly larger than traditional (upgrade check)."""
    trad_size = (_PDF / "traditional_report.pdf").stat().st_size
    det_size  = (_PDF / "detailed_report.pdf").stat().st_size
    assert det_size > trad_size * 1.5, \
        f"detailed ({det_size:,}) not significantly larger than traditional ({trad_size:,})"


def test_E06_professional_pdf_significantly_larger_than_detailed():
    """E06: professional PDF is significantly larger than detailed (upgrade check)."""
    det_size = (_PDF / "detailed_report.pdf").stat().st_size
    pro_size = (_PDF / "professional_report.pdf").stat().st_size
    assert pro_size > det_size * 1.3, \
        f"professional ({pro_size:,}) not significantly larger than detailed ({det_size:,})"


def test_E07_pdf_sizes_are_distinct():
    """E07: three PDFs have distinct sizes — not identical content."""
    sizes = [(_PDF / f"{k}.pdf").stat().st_size
             for k in ["traditional_report", "detailed_report", "professional_report"]]
    assert len(set(sizes)) == 3, f"Non-distinct PDF sizes: {sizes}"


def test_E08_detailed_has_dcf_content():
    """E08: detailed report preview contains DCF content."""
    content = _html("detailed_report")
    assert "DCF" in content or "التدفقات النقدية" in content


def test_E09_detailed_has_sensitivity_content():
    """E09: detailed report preview contains sensitivity content."""
    content = _html("detailed_report")
    assert "الحساسية" in content or "Sensitivity" in content


def test_E10_detailed_has_hbu_content():
    """E10: detailed report contains HBU summary."""
    content = _html("detailed_report")
    assert "HBU" in content or "أعلى وأفضل استخدام" in content


def test_E11_professional_has_dual_dcf():
    """E11: professional report references both 5-year and 10-year DCF."""
    content = _html("professional_report")
    assert "5 سنوات" in content or "5-year" in content.lower()
    assert "10 سنوات" in content or "10-year" in content.lower()


def test_E12_professional_has_scenario_analysis():
    """E12: professional report contains scenario analysis."""
    content = _html("professional_report")
    assert "السيناريو" in content or "Scenario" in content


def test_E13_professional_has_dashboard():
    """E13: professional report contains dashboard section."""
    content = _html("professional_report")
    assert "Dashboard" in content or "لوحة" in content


def test_E14_no_internal_paths_in_previews():
    """E14: no internal filesystem paths exposed in output previews."""
    for key in ["traditional_report", "detailed_report", "professional_report"]:
        content = _html(key)
        for pat in (r"C:\\Users", r"C:/Users", "/home/", "core_engine/instance"):
            assert pat not in content, f"Internal path in {key}: {pat}"


def test_E15_visual_review_index_exists():
    """E15: pdf_modern_methods_visual_review_index.html exists."""
    assert (_PREV / "pdf_modern_methods_visual_review_index.html").exists()


def test_E16_method_coverage_audit_confirms_modern_methods():
    """E16: method coverage audit confirms modern methods added."""
    data = _load(_METH / "pdf_methods_added_from_legacy_excel_audit.json")
    assert data["coverage_status"] == "PASS"
    det = data["detailed_report"]
    assert det["dcf_summary"] is True
    assert det["sensitivity_snapshot"] is True
    pro = data["professional_report"]
    assert pro["dcf_analysis"] is True
    assert pro["scenario_analysis"] is True
    assert pro["reflects_legacy_excel_methods"] is True


def test_E17_distinctness_audit_passes():
    """E17: distinctness audit confirms reports are not near-duplicates."""
    data = _load(_DIST / "pdf_depth_distinctness_after_modern_methods_upgrade.json")
    assert data["distinctness_status"] == "PASS"
    assert data["near_duplicate_report_pairs"] == []
    sc = data["section_counts"]
    assert sc["traditional_report"] < sc["detailed_report"] < sc["professional_report"]


def test_E18_legacy_method_inventory_confirmed():
    """E18: legacy method inventory confirms detection of key Excel methods."""
    data = _load(_LEG / "legacy_excel_method_inventory.json")
    dm = data["detected_methods"]
    for method in ["market_approach", "income_approach", "cost_approach",
                   "dcf_analysis", "sensitivity_analysis", "weighted_reconciliation",
                   "hbu_analysis", "direct_capitalization", "scenario_analysis"]:
        assert dm.get(method) is True, f"Missing method: {method}"


# ═══════════════════════════════════════════════════════════════════════════════
# LIVE SERVER + PLAYWRIGHT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

@_LIVE
@_SKIP_NO_PW
def test_E19_page_opens_without_js_errors(page: Page):
    """E19: Professional Valuation page opens without JS errors."""
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{_BASE_URL}/", timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=20_000)
    assert len(errors) == 0 or all("favicon" in e.lower() for e in errors)


@_LIVE
@_SKIP_NO_PW
def test_E20_core_report_section_visible(page: Page):
    """E20: core report section is visible."""
    page.goto(f"{_BASE_URL}/", timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=20_000)
    section = page.locator('[data-testid="pro-val-expert-review-request-section"]')
    expect(section).to_be_visible(timeout=10_000)


@_LIVE
@_SKIP_NO_PW
def test_E21_traditional_pdf_exists_after_generation(page: Page):
    """E21: traditional_report.pdf physically exists."""
    assert (_PDF / "traditional_report.pdf").exists()
    assert (_PDF / "traditional_report.pdf").stat().st_size > 10_000


@_LIVE
@_SKIP_NO_PW
def test_E22_detailed_pdf_exists_and_is_larger(page: Page):
    """E22: detailed_report.pdf physically exists and is larger than traditional."""
    assert (_PDF / "detailed_report.pdf").exists()
    det = (_PDF / "detailed_report.pdf").stat().st_size
    trad = (_PDF / "traditional_report.pdf").stat().st_size
    assert det > trad


@_LIVE
@_SKIP_NO_PW
def test_E23_professional_pdf_exists_and_is_largest(page: Page):
    """E23: professional_report.pdf is the largest PDF."""
    sizes = {
        k: (_PDF / f"{k}.pdf").stat().st_size
        for k in ["traditional_report", "detailed_report", "professional_report"]
    }
    assert sizes["professional_report"] == max(sizes.values())


@_LIVE
@_SKIP_NO_PW
def test_E24_visual_review_index_renders(page: Page):
    """E24: visual review index HTML renders with correct title."""
    preview = _PREV / "pdf_modern_methods_visual_review_index.html"
    assert preview.exists()
    page.goto(preview.as_uri(), timeout=15_000)
    assert "فهرس" in page.content()


@_LIVE
@_SKIP_NO_PW
def test_E25_no_internal_paths_in_dom(page: Page):
    """E25: No internal filesystem paths appear in page DOM."""
    page.goto(f"{_BASE_URL}/", timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=20_000)
    content = page.content()
    for pat in [r"C:\\Users", r"C:/Users", "/home/"]:
        assert pat not in content, f"Internal path in DOM: {pat}"


@_LIVE
@_SKIP_NO_PW
def test_E26_method_coverage_confirmed_via_static(page: Page):
    """E26: method coverage audit confirms advanced methods present."""
    data = _load(_METH / "pdf_methods_added_from_legacy_excel_audit.json")
    pro = data["professional_report"]
    assert pro["dcf_analysis"] is True
    assert pro["hbu_summary"] is True
    assert pro["scenario_analysis"] is True
    assert pro["reflects_legacy_excel_methods"] is True
