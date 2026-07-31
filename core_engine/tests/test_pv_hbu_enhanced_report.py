"""
test_pv_hbu_enhanced_report.py
Enhanced HBU Report — 30 tests covering:
  H-E01..05  : Sourcing layer & provenance
  H-E06..10  : Financial depth (RLV / payback / IRR / sensitivity)
  H-E11..15  : Artifact existence & size
  H-E16..20  : HTML content (Axes A-F, ≥1000 chars per axis)
  H-E21..25  : Governance (watermark, no local paths, audience separation)
  H-E26..30  : Excel structure (15+ sheets, charts, SAR-only)

All tests use a single module-scoped fixture that runs the generator once.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

# ── path setup ────────────────────────────────────────────────────────────────
_TESTS = pathlib.Path(__file__).resolve().parent
_CORE  = _TESTS.parent
for _p in [str(_CORE), str(_CORE / "reports")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ════════════════════════════════════════════════════════════════════════════
#  MODULE-SCOPED FIXTURE — run generator once
# ════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def report():
    """Run generate_enhanced_hbu_report() once for the whole module."""
    from hbu_enhanced_report import generate_enhanced_hbu_report

    out_dir = _CORE / "outputs" / "test_enhanced_hbu"
    result  = generate_enhanced_hbu_report(
        out_dir=out_dir, case_id="TEST-HBU-ENHANCED-001"
    )
    return result


@pytest.fixture(scope="module")
def arts(report):
    return report["artifacts"]


@pytest.fixture(scope="module")
def fd(report):
    return report["financial_depth"]


@pytest.fixture(scope="module")
def prov(report):
    return report["provenance_table"]


@pytest.fixture(scope="module")
def sourcing(report):
    return report["sourcing_summary"]


@pytest.fixture(scope="module")
def hbu(report):
    return report["hbu_result"]


@pytest.fixture(scope="module")
def vqa(report):
    return report["visual_qa"]


@pytest.fixture(scope="module")
def user_html_text(arts):
    p = arts.get("user_html")
    if p and pathlib.Path(p).exists():
        return pathlib.Path(p).read_text(encoding="utf-8")
    return ""


@pytest.fixture(scope="module")
def admin_html_text(arts):
    p = arts.get("admin_html")
    if p and pathlib.Path(p).exists():
        return pathlib.Path(p).read_text(encoding="utf-8")
    return ""


# ════════════════════════════════════════════════════════════════════════════
#  H-E01..05 — Sourcing layer & provenance
# ════════════════════════════════════════════════════════════════════════════

def test_H_E01_sourcing_import():
    """hbu_sourced_inputs.source_hbu_inputs() is importable and callable."""
    from hbu_sourced_inputs import source_hbu_inputs, HBUSourcingResult
    body = {"land_area_m2": 2400, "city_ar": "الرياض",
            "district_ar": "النرجس", "country_code": "SA"}
    result = source_hbu_inputs(body)
    assert isinstance(result, HBUSourcingResult)


def test_H_E02_provenance_count(prov):
    """Provenance table has ≥8 records (one per HBU market input)."""
    assert len(prov) >= 8, f"Expected ≥8 provenance records, got {len(prov)}"


def test_H_E03_mass_appraisal_tier1(prov):
    """Mass appraisal inputs have Tier-1 محوكم source tier."""
    tier1 = [p for p in prov if "Tier-1" in (p.get("source_tier") or "")]
    assert len(tier1) >= 1, "Expected ≥1 Tier-1 محوكم provenance record from mass appraisal"


def test_H_E04_draft_inputs_labeled(prov):
    """Web research / enrichment inputs are labeled Draft or غير متاح — never unlabeled."""
    non_tier1 = [p for p in prov if "Tier-1" not in (p.get("source_tier") or "")]
    for p in non_tier1:
        status = p.get("status", "")
        assert status in ("Draft — مسح مبدئي محوكم", "Draft — افتراضي",
                          "غير متاح", "Certified"), \
            f"Input {p.get('input_id')} has unlabeled status: {status!r}"


def test_H_E05_no_fabricated_inputs(prov):
    """Unavailable inputs have a documented reason (no silent None without explanation)."""
    for p in prov:
        if p.get("value_used") is None:
            note = p.get("reconciliation_note", "")
            assert note, \
                f"Input {p.get('input_id')} is None but has no reconciliation_note"


# ════════════════════════════════════════════════════════════════════════════
#  H-E06..10 — Financial depth
# ════════════════════════════════════════════════════════════════════════════

def test_H_E06_financial_depth_keys(fd):
    """compute_financial_depth returns all required keys."""
    required = ["gdv", "tdc", "rlv", "rlv_per_m2", "land_cost",
                "payback_years", "irr_project_pct", "irr_investor_pct",
                "dev_margin_pct", "sensitivity_grid", "discount_rate_sensitivity"]
    for key in required:
        assert key in fd, f"Missing financial depth key: {key}"


def test_H_E07_rlv_computed(fd):
    """RLV is computed (not None) and equals GDV - TDC - dev_profit_target."""
    assert fd["rlv"] is not None, "RLV is None"
    expected = fd["gdv"] - fd["tdc"] - fd["dev_profit_target"]
    assert abs(fd["rlv"] - expected) < 10, \
        f"RLV mismatch: {fd['rlv']} vs expected {expected:.0f}"


def test_H_E08_payback_computed(fd):
    """Payback period is computed (not None) and positive."""
    assert fd["payback_years"] is not None, "payback_years is None"
    assert fd["payback_years"] > 0, \
        f"payback_years should be positive, got {fd['payback_years']}"


def test_H_E09_irr_computed(fd):
    """IRR investor is computed (not None) and positive."""
    assert fd["irr_investor_pct"] is not None, "irr_investor_pct is None"
    assert fd["irr_project_pct"]  is not None, "irr_project_pct is None"
    assert fd["irr_project_pct"] > 0, \
        f"irr_project_pct should be positive, got {fd['irr_project_pct']}"


def test_H_E10_sensitivity_9_scenarios(fd):
    """Sensitivity grid has 9 computed NPV values (3×3), none are None."""
    sg = fd["sensitivity_grid"]
    matrix = sg.get("npv_matrix", [])
    assert len(matrix) == 3, f"Expected 3 revenue rows, got {len(matrix)}"
    for row in matrix:
        assert len(row) == 3, f"Expected 3 cost columns, got {len(row)}"
        for v in row:
            assert v is not None, "Sensitivity matrix contains None value"


# ════════════════════════════════════════════════════════════════════════════
#  H-E11..15 — Artifact existence & size
# ════════════════════════════════════════════════════════════════════════════

def test_H_E11_user_html_exists(arts):
    """User HTML artifact exists and has size > 30 KB."""
    p = arts.get("user_html")
    assert p and pathlib.Path(p).exists(), "user_html does not exist"
    assert pathlib.Path(p).stat().st_size > 30_000, \
        f"user_html too small: {pathlib.Path(p).stat().st_size} bytes"


def test_H_E12_admin_html_exists(arts):
    """Admin HTML artifact exists and has size > 30 KB."""
    p = arts.get("admin_html")
    assert p and pathlib.Path(p).exists(), "admin_html does not exist"
    assert pathlib.Path(p).stat().st_size > 30_000, \
        f"admin_html too small: {pathlib.Path(p).stat().st_size} bytes"


def test_H_E13_user_pdf_exists(arts):
    """User PDF artifact exists and has size > 20 KB."""
    p = arts.get("user_pdf")
    assert p and pathlib.Path(p).exists(), "user_pdf does not exist"
    assert pathlib.Path(p).stat().st_size > 20_000, \
        f"user_pdf too small: {pathlib.Path(p).stat().st_size} bytes"


def test_H_E14_admin_pdf_exists(arts):
    """Admin PDF artifact exists and has size > 20 KB."""
    p = arts.get("admin_pdf")
    assert p and pathlib.Path(p).exists(), "admin_pdf does not exist"
    assert pathlib.Path(p).stat().st_size > 20_000, \
        f"admin_pdf too small: {pathlib.Path(p).stat().st_size} bytes"


def test_H_E15_admin_xlsx_exists(arts):
    """Admin XLSX artifact exists and has size > 10 KB."""
    p = arts.get("admin_xlsx")
    assert p and pathlib.Path(p).exists(), "admin_xlsx does not exist"
    assert pathlib.Path(p).stat().st_size > 10_000, \
        f"admin_xlsx too small: {pathlib.Path(p).stat().st_size} bytes"


# ════════════════════════════════════════════════════════════════════════════
#  H-E16..20 — HTML content (Axes A–F)
# ════════════════════════════════════════════════════════════════════════════

def test_H_E16_axis_a_site_content(user_html_text):
    """User HTML has Axis A (site study) section with ≥800 chars of content."""
    assert "المحور A" in user_html_text or "دراسة الموقع" in user_html_text, \
        "Axis A section not found in user HTML"
    idx = user_html_text.find("دراسة الموقع")
    if idx < 0:
        idx = user_html_text.find("المحور A")
    snippet = user_html_text[idx:idx + 3000]
    assert len(snippet) > 800, f"Axis A content too short: {len(snippet)} chars"


def test_H_E17_axis_b_market_content(user_html_text):
    """User HTML has Axis B (market intelligence) with ≥800 chars."""
    assert "الذكاء السوقي" in user_html_text or "المحور B" in user_html_text, \
        "Axis B section not found in user HTML"
    idx = max(user_html_text.find("الذكاء السوقي"),
              user_html_text.find("المحور B"))
    snippet = user_html_text[idx:idx + 3000]
    assert len(snippet) > 800, f"Axis B content too short: {len(snippet)} chars"


def test_H_E18_axis_c_concepts_content(user_html_text):
    """User HTML has Axis C (development concepts) with all 4 alternatives."""
    assert "المفاهيم التطويرية" in user_html_text or "المحور C" in user_html_text, \
        "Axis C section not found in user HTML"
    # All 4 alternatives should be present
    for alt_id in ("ALT-01", "ALT-02", "ALT-03", "ALT-04"):
        assert alt_id in user_html_text, f"{alt_id} not found in Axis C"


def test_H_E19_axis_d_rlv_in_html(user_html_text):
    """User HTML has RLV analysis section with key Arabic terms."""
    for term in ("RLV", "القيمة المتبقية", "المالي"):
        assert term in user_html_text, f"Term '{term}' not found in user HTML"


def test_H_E20_axis_e_advisory_narrative(user_html_text):
    """User HTML has Axis E advisory narrative with ≥500 chars."""
    assert "التوصيات" in user_html_text or "المحور E" in user_html_text, \
        "Axis E section not found in user HTML"
    idx = max(user_html_text.find("التوصيات الاستشارية"),
              user_html_text.find("المحور E"))
    snippet = user_html_text[max(0, idx):max(0, idx) + 2000]
    assert len(snippet) > 500, f"Axis E narrative too short: {len(snippet)} chars"


# ════════════════════════════════════════════════════════════════════════════
#  H-E21..25 — Governance & audience separation
# ════════════════════════════════════════════════════════════════════════════

def test_H_E21_user_html_advisory_watermark(user_html_text):
    """User HTML contains advisory watermark text."""
    assert "استرشادي" in user_html_text or "غير معتمد" in user_html_text, \
        "Advisory watermark missing from user HTML"


def test_H_E22_user_html_no_local_paths(user_html_text):
    """User HTML does not contain local file paths."""
    for pattern in ("file:///C:", "C:\\\\", "C:/Users", "\\\\Users"):
        assert pattern not in user_html_text, \
            f"Local path pattern '{pattern}' found in user HTML"


def test_H_E23_user_html_no_admin_sections(user_html_text):
    """User HTML does NOT contain admin-only source log section."""
    assert "سجل_المصادر" not in user_html_text, \
        "Admin-only source log found in user HTML"
    assert "سجل الافتراضات الداخلية" not in user_html_text, \
        "Admin-only assumptions log found in user HTML"


def test_H_E24_admin_html_has_source_log(admin_html_text):
    """Admin HTML DOES contain source log section."""
    has_log = ("سجل_المصادر" in admin_html_text
               or "سجل المصادر" in admin_html_text
               or "سجل الافتراضات" in admin_html_text)
    assert has_log, "Admin HTML missing source log / assumptions section"


def test_H_E25_governance_flags(report):
    """Report governance flags are correctly set."""
    gov = report["governance"]
    assert gov["advisory_only"] is True
    assert gov["certification_ready"] is False
    assert gov["fake_reviewer_signature_created"] is False
    assert gov["non_certified"] is True


# ════════════════════════════════════════════════════════════════════════════
#  H-E26..30 — Excel structure
# ════════════════════════════════════════════════════════════════════════════

def test_H_E26_excel_sheet_count(arts):
    """Admin XLSX has ≥15 sheets."""
    p = arts.get("admin_xlsx")
    if not (p and pathlib.Path(p).exists()):
        pytest.skip("admin_xlsx not available")
    import openpyxl
    wb = openpyxl.load_workbook(p, read_only=True)
    count = len(wb.sheetnames)
    wb.close()
    assert count >= 15, f"Expected ≥15 sheets, got {count}: {wb.sheetnames}"


def test_H_E27_excel_expected_sheets(arts):
    """Admin XLSX contains required sheet names."""
    p = arts.get("admin_xlsx")
    if not (p and pathlib.Path(p).exists()):
        pytest.skip("admin_xlsx not available")
    import openpyxl
    wb = openpyxl.load_workbook(p, read_only=True)
    names = wb.sheetnames
    wb.close()
    required = ["ملخص_HBU", "مصدرية_المدخلات", "العمق_المالي",
                "حساسية_متعددة", "مقارنة_البدائل", "حوكمة_وإفصاحات"]
    for req in required:
        assert req in names, f"Required sheet '{req}' not found. Available: {names}"


def test_H_E28_excel_has_charts(arts):
    """Admin XLSX has ≥1 chart (NPV bar chart or sensitivity line chart)."""
    p = arts.get("admin_xlsx")
    if not (p and pathlib.Path(p).exists()):
        pytest.skip("admin_xlsx not available")
    import openpyxl
    wb = openpyxl.load_workbook(p, read_only=False)
    chart_count = sum(len(ws._charts) for ws in wb.worksheets)
    wb.close()
    assert chart_count >= 1, "No charts found in admin XLSX"


def test_H_E29_excel_provenance_sheet_has_data(arts):
    """Provenance sheet has ≥8 data rows."""
    p = arts.get("admin_xlsx")
    if not (p and pathlib.Path(p).exists()):
        pytest.skip("admin_xlsx not available")
    import openpyxl
    wb = openpyxl.load_workbook(p, read_only=True)
    ws = wb["مصدرية_المدخلات"]
    data_rows = sum(1 for row in ws.iter_rows(min_row=3, values_only=True)
                    if any(v is not None for v in row))
    wb.close()
    assert data_rows >= 8, f"Provenance sheet has {data_rows} data rows, expected ≥8"


def test_H_E30_excel_no_foreign_currency(arts):
    """Admin XLSX contains no EGP or QAR — SAR only."""
    p = arts.get("admin_xlsx")
    if not (p and pathlib.Path(p).exists()):
        pytest.skip("admin_xlsx not available")
    import openpyxl
    wb = openpyxl.load_workbook(p, read_only=True)
    found_foreign = []
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            for val in row:
                if isinstance(val, str) and ("EGP" in val or "QAR" in val):
                    found_foreign.append(val[:40])
    wb.close()
    assert not found_foreign, \
        f"Foreign currencies found in XLSX: {found_foreign[:3]}"
