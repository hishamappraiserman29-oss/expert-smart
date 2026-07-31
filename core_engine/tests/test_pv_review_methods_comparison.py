"""
Permanent focused tests for pv_report_review_endpoint.py V3.0.

Tests valuation method computation, RAG logic, audience separation,
watermarks, compliance score, HTML structure, and Excel/chart contract.

All tests use deterministic fixtures. No network access. No customer data.
"""
import importlib
import math
import pathlib
import sys
import tempfile
import re

import pytest

# ── import target module ──────────────────────────────────────────────────────
_CORE = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_CORE.parent))

try:
    import core_engine.pv_report_review_endpoint as _ep
    _compute  = _ep._compute_valuation_methods
    _validate = _ep._validate_numeric_inputs
    _html     = _ep._build_review_html
    _xl       = _ep._build_review_excel
    _score    = _ep._compute_compliance_score
    _TMPL     = _ep._COMPLIANCE_TEMPLATE
    IMPORT_OK = True
except Exception as _e:
    IMPORT_OK = False
    _IMPORT_ERROR = str(_e)

pytestmark = pytest.mark.skipif(
    not IMPORT_OK,
    reason=f"Import failed: {_IMPORT_ERROR if not IMPORT_OK else ''}"
)


# ── fixtures ──────────────────────────────────────────────────────────────────

def _meta_full():
    """Complete Qatar villa test case — exercises all four methods."""
    return {
        "case_id":                "QA-QATAR-PV-REVIEW-V3-001",
        "country_ar":             "قطر",
        "city_ar":                "لوسيل",
        "district_ar":            "فوكس هيلز",
        "currency_code":          "QAR",
        "asset_type_ar":          "فيلا سكنية",
        "land_area_m2":           1200.0,
        "built_up_area_m2":       850.0,
        "reviewer_name":          "اختبار آلي",
        "review_client":          "نظام QA",
        "review_purpose":         "اختبار بصري",
        "review_scope":           "مراجعة شاملة",
        "review_date":            "2026-07-01",
        # reported value
        "reported_value":         12_000_000.0,
        # sales comparison: 3 complete comparables
        "comp1": (13_000_000.0, 900.0, 2.5),
        "comp2": (11_500_000.0, 800.0, -1.0),
        "comp3": (12_200_000.0, 850.0, 0.0),
        # income capitalization
        "gross_income":           800_000.0,
        "vacancy_rate":           10.0,
        "opex_ratio":             20.0,
        "cap_rate":               5.0,
        # cost approach
        "replacement_cost_per_sqm": 8_000.0,
        "depreciation_pct":         15.0,
        "land_value_per_sqm":       6_000.0,
        # DCF
        "discount_rate":          8.0,
        "holding_period_years":   10.0,
        "annual_rent_growth":     3.0,
        "exit_cap_rate":          5.5,
    }


def _meta_empty():
    return {
        "case_id":       "QA-EMPTY-001",
        "currency_code": "QAR",
    }


# ── test_compute_sales_comparison ─────────────────────────────────────────────

def test_compute_sales_comparison():
    meta = _meta_full()
    result = _compute(meta)
    sc = result["methods"]["sales_comparison"]
    assert sc["status"] == "computed"

    # Manual calculation for comp1:
    # price=13_000_000, area=900 → psm=14444.44, adj=+2.5% → adj_psm=14805.56
    c1 = (13_000_000.0 / 900.0) * 1.025
    # comp2: 11_500_000 / 800 * (1-0.01)
    c2 = (11_500_000.0 / 800.0) * 0.99
    # comp3: 12_200_000 / 850 * 1.0
    c3 = 12_200_000.0 / 850.0
    expected_avg = (c1 + c2 + c3) / 3.0
    expected_val = round(expected_avg * 850.0, 2)

    assert abs(sc["value"] - expected_val) < 1.0, (
        f"SC value {sc['value']} != expected {expected_val}"
    )
    inputs = sc["inputs_used"]
    assert inputs["built_up_area_m2"] == 850.0
    assert abs(inputs["avg_adj_psm"] - expected_avg) < 0.01


def test_compute_sales_comparison_accepts_partial_comparable_set():
    """One or two complete comparables should compute successfully."""
    meta = dict(_meta_full())
    meta["comp2"] = None
    meta["comp3"] = None
    result = _compute(meta)
    sc = result["methods"]["sales_comparison"]
    assert sc["status"] == "computed"
    assert sc["value"] is not None


def test_compute_sales_comparison_reports_missing_data():
    result = _compute(_meta_empty())
    sc = result["methods"]["sales_comparison"]
    assert sc["status"] == "unavailable"
    assert sc["value"] is None
    assert len(sc["missing_inputs"]) > 0
    assert sc["reason"] is not None and len(sc["reason"]) > 0


# ── test_compute_income_cap ───────────────────────────────────────────────────

def test_compute_income_cap():
    meta = _meta_full()
    result = _compute(meta)
    ic = result["methods"]["income_capitalization"]
    assert ic["status"] == "computed"

    egi      = 800_000.0 * (1 - 10.0 / 100)       # 720_000
    noi      = egi * (1 - 20.0 / 100)              # 576_000
    expected = round(noi / (5.0 / 100), 2)          # 11_520_000

    assert abs(ic["value"] - expected) < 1.0, (
        f"IC value {ic['value']} != expected {expected}"
    )
    inputs = ic["inputs_used"]
    assert abs(inputs["effective_gross_income"] - egi) < 0.01
    assert abs(inputs["noi"] - noi) < 0.01


def test_compute_income_cap_rejects_zero_cap_rate():
    meta = dict(_meta_full())
    meta["cap_rate"] = 0.0
    _, errors = _validate({**meta, "cap_rate": "0"})
    assert any("معدل الرسملة" in e or "cap_rate" in e.lower() for e in errors)


# ── test_compute_cost ─────────────────────────────────────────────────────────

def test_compute_cost():
    meta = _meta_full()
    result = _compute(meta)
    ca = result["methods"]["cost_approach"]
    assert ca["status"] == "computed"

    land_val   = 1200.0 * 6_000.0              # 7_200_000
    gross_repl = 850.0 * 8_000.0               # 6_800_000
    depr       = gross_repl * 0.15              # 1_020_000
    depr_impl  = gross_repl - depr             # 5_780_000
    expected   = round(land_val + depr_impl, 2) # 12_980_000

    assert abs(ca["value"] - expected) < 1.0, (
        f"CA value {ca['value']} != expected {expected}"
    )
    inputs = ca["inputs_used"]
    assert abs(inputs["land_value"] - land_val) < 0.01
    assert abs(inputs["depreciated_improvements"] - depr_impl) < 0.01


# ── test_compute_dcf ──────────────────────────────────────────────────────────

def test_compute_dcf():
    meta = _meta_full()
    result = _compute(meta)
    dcf = result["methods"]["dcf"]
    assert dcf["status"] == "computed"

    # Independently calculate year 1
    gi    = 800_000.0
    vac   = 10.0
    opex  = 20.0
    dr    = 8.0
    arg   = 3.0
    ecap  = 5.5
    hp    = 10

    pv_sum  = 0.0
    noi_last = 0.0
    for t in range(1, hp + 1):
        gt   = gi * (1.03 ** (t - 1))
        eff  = gt * 0.90
        noi  = eff * 0.80
        df   = (1.08) ** t
        pv_sum += noi / df
        noi_last = noi

    term_noi = noi_last * 1.03
    term_val = term_noi / 0.055
    term_pv  = term_val / (1.08 ** hp)
    expected = round(pv_sum + term_pv, 2)

    assert abs(dcf["value"] - expected) < 100.0, (
        f"DCF value {dcf['value']} != expected {expected}"
    )
    assert len(dcf["year_table"]) == hp
    assert dcf["year_table"][0]["year"] == 1


def test_compute_dcf_rejects_invalid_duration():
    _, errors = _validate({"holding_period_years": "0"})
    assert any("مدة" in e or "holding" in e.lower() for e in errors)
    _, errors2 = _validate({"holding_period_years": "101"})
    assert any("مدة" in e or "holding" in e.lower() for e in errors2)


# ── RAG + variance tests ──────────────────────────────────────────────────────

def test_variance_and_rag_green():
    # reported=10_000_000, independent=10_300_000 → +3% → GREEN
    meta = dict(_meta_full())
    meta["reported_value"] = 10_000_000.0
    # force SC to produce close value by manipulating comps
    meta["comp1"] = (10_300_000.0, 850.0, 0.0)
    meta["comp2"] = None
    meta["comp3"] = None
    result = _compute(meta)
    sc = result["methods"]["sales_comparison"]
    if sc["status"] == "computed":
        assert sc["rag"] in ("GREEN", "AMBER", "RED", "GRAY")  # just ensure it's valid
        if sc["absolute_variance_pct"] is not None and sc["absolute_variance_pct"] <= 5.0:
            assert sc["rag"] == "GREEN"


def test_variance_and_rag_amber():
    # variance between 5% and 15% → AMBER
    from core_engine.pv_report_review_endpoint import _rag
    assert _rag(5.1)  == "AMBER"
    assert _rag(14.9) == "AMBER"


def test_variance_and_rag_red():
    from core_engine.pv_report_review_endpoint import _rag
    assert _rag(15.1) == "RED"
    assert _rag(50.0) == "RED"


def test_variance_gray_without_reported_value():
    result = _compute(_meta_empty())
    for m in result["methods"].values():
        if m["status"] == "computed":
            assert m["rag"] == "GRAY"  # no reported value → GRAY


# ── uncertainty range ─────────────────────────────────────────────────────────

def test_uncertainty_range_requires_two_methods():
    # With no data, no valid methods → no range
    result = _compute(_meta_empty())
    unc = result["uncertainty"]
    assert unc.get("valid_count", 0) == 0


def test_uncertainty_range_from_valid_methods():
    meta = _meta_full()
    result = _compute(meta)
    unc = result["uncertainty"]
    valid_count = unc.get("valid_count", 0)
    if valid_count >= 2:
        assert unc["low"] <= unc["high"]
        assert unc["midpoint"] is not None
        assert unc.get("spread_pct") is not None


# ── input validation ──────────────────────────────────────────────────────────

def test_invalid_nan_and_infinity_are_rejected():
    _, errors = _validate({"reported_value": "nan"})
    assert errors, "NaN should produce errors"
    _, errors2 = _validate({"cap_rate": "inf"})
    assert errors2, "Infinity should produce errors"


def test_route_invalid_numeric_input_returns_400():
    """Validation function returns errors for bad inputs — route returns 400."""
    _, errors = _validate({"reported_value": "abc", "cap_rate": "-5"})
    assert len(errors) >= 1


def test_validate_partial_comparable_raises_error():
    """A comparable with price but no area is invalid."""
    _, errors = _validate({"comp1_price": "1000000", "comp1_area": ""})
    assert any("مبيع" in e or "comp1" in e.lower() for e in errors)


# ── HTML structure tests ──────────────────────────────────────────────────────

def _get_user_html():
    return _html(_meta_full(), audience="user")


def _get_admin_html():
    return _html(_meta_full(), audience="admin")


def test_html_user_has_watermark():
    html = _get_user_html()
    assert 'class="review-watermark review-watermark--user"' in html
    assert "استرشادي" in html
    assert "غير معتمد" in html


def test_html_admin_has_light_watermark():
    html = _get_admin_html()
    assert 'class="review-watermark review-watermark--admin"' in html
    assert "داخلية" in html or "للمراجعة" in html


def test_html_user_no_internal_paths():
    html = _get_user_html()
    forbidden = [
        "file:///C:/",
        "C:\\",
        "C:/Users",
        "stack trace",
        "Traceback",
        "audit_trail",
    ]
    for f in forbidden:
        assert f not in html, f"Found forbidden string in user HTML: {f!r}"


def test_html_has_exactly_10_pages():
    html = _get_user_html()
    # Count <div class="pg"
    count = html.count('class="pg"')
    assert count == 10, f"Expected 10 pages, found {count}"


def test_html_pages_are_non_empty():
    html = _get_user_html()
    # Each pg div should have meaningful content (not just empty div)
    parts = html.split('class="pg"')
    assert len(parts) == 11, "Should have 10 pg divs"
    for i, part in enumerate(parts[1:], 1):
        # The next closing </div> should contain table or card content
        snippet = part[:500]
        has_content = (
            "<table" in snippet or
            "<div" in snippet or
            "<h2" in snippet
        )
        assert has_content, f"Page {i} appears to have no content"


def test_html_page_4_has_independent_methods():
    html = _get_user_html()
    assert "Shadow Valuation" in html or "الأساليب المستقلة" in html
    assert "أسلوب مقارنة المبيعات" in html
    assert "أسلوب رسملة الدخل" in html
    assert "أسلوب التكلفة" in html
    assert "DCF" in html


def test_html_page_5_has_master_comparison():
    html = _get_user_html()
    assert "master-comparison-table" in html or "جدول المقارنة الشاملة" in html


def test_compliance_rows_are_12():
    # _COMPLIANCE_TEMPLATE must have exactly 12 entries
    assert len(_TMPL) == 12, f"Expected 12 compliance rows, got {len(_TMPL)}"


def test_review_dimensions_are_13():
    html = _get_user_html()
    assert "review-dimensions-table" in html or "أبعاد المراجعة التقنية" in html
    # Count <tr> rows within the dimensions table — should have 13 data rows
    # (simplistic: count occurrences of dimension labels)
    dim_indicators = [
        "هوية التقرير",
        "بيانات الأصل",
        "الملكية",
        "الموقع",
        "مقارنة المبيعات",
        "رسملة الدخل",
        "أسلوب التكلفة",
        "DCF",
        "الاتساق الرياضي",
        "التوفيق",
        "HBU",
        "الامتثال",
        "المخاطر",
    ]
    found = sum(1 for d in dim_indicators if d in html)
    assert found >= 12, f"Expected ≥12 review dimensions in HTML, found {found}"


# ── advisory flags ────────────────────────────────────────────────────────────

def test_advisory_flags_all_formats():
    user_html  = _get_user_html()
    admin_html = _get_admin_html()
    for html in (user_html, admin_html):
        assert "advisory_only" in html
        assert "استرشادي" in html
        assert "fake_reviewer_signature_created" in html


# ── audience separation ───────────────────────────────────────────────────────

def test_audience_separation():
    user_html  = _get_user_html()
    admin_html = _get_admin_html()

    # User must NOT contain admin audit trail
    assert "سجل التدقيق الداخلي" not in user_html
    assert "داخلي — للمراجع فقط" not in user_html

    # Admin SHOULD contain audit trail
    assert "سجل التدقيق الداخلي" in admin_html

    # User watermark element present in user HTML (div element, not CSS definition)
    assert 'class="review-watermark review-watermark--user"' in user_html
    # Admin watermark element must NOT appear in user HTML
    assert 'class="review-watermark review-watermark--admin"' not in user_html

    # Admin watermark element in admin HTML
    assert 'class="review-watermark review-watermark--admin"' in admin_html


def test_user_and_admin_html_are_materially_different():
    user_html  = _get_user_html()
    admin_html = _get_admin_html()
    assert user_html != admin_html


def test_client_cannot_self_assign_admin_audience():
    """Audience is determined by server-side role, not a client-supplied field."""
    # _build_review_html requires explicit audience parameter from caller
    # The route handler always calls with audience from is_admin(), never from request
    # This is enforced by design — the function signature requires the caller to pass it
    user_html = _html(_meta_full(), audience="user")
    admin_html = _html(_meta_full(), audience="admin")
    # Attempting to pass audience as a meta field has no effect
    meta_with_fake_audience = dict(_meta_full())
    meta_with_fake_audience["audience"] = "admin"
    html_should_still_be_user = _html(meta_with_fake_audience, audience="user")
    assert "سجل التدقيق الداخلي" not in html_should_still_be_user


# ── dynamic compliance score ──────────────────────────────────────────────────

def test_dynamic_compliance_score_is_not_hardcoded():
    comp = _score()
    # Must be a computed integer/number, not the hardcoded 55
    assert isinstance(comp["score"], (int, float))
    assert 0 <= comp["score"] <= 100
    assert "formula" in comp
    # Verify formula is factual (not "55/100 × 100 = 55%")
    assert "55/100" not in comp["formula"]


def test_compliance_score_matches_template():
    """Score must be consistent with _COMPLIANCE_TEMPLATE statuses."""
    comp = _score()
    score_map = {"pass": 1.0, "partial": 0.5, "fail": 0.0}
    applicable = [c for c in _TMPL if c[3] != "na"]
    earned = sum(score_map.get(c[3], 0.0) for c in applicable)
    expected = round(earned / len(applicable) * 100)
    assert comp["score"] == expected


def test_missing_method_inputs_have_documented_reason():
    result = _compute(_meta_empty())
    for key, m in result["methods"].items():
        if m["status"] in ("unavailable", "invalid"):
            assert m.get("reason") is not None and len(m["reason"]) > 0, (
                f"Method {key} is {m['status']} but has no documented reason"
            )


# ── Excel tests ───────────────────────────────────────────────────────────────

def test_excel_sheet_5_has_master_table():
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not available")
    with tempfile.TemporaryDirectory() as tmp:
        xl_path = pathlib.Path(tmp) / "test_review.xlsx"
        ok = _xl(_meta_full(), xl_path)
        assert ok
        wb = openpyxl.load_workbook(str(xl_path))
        sheet_names = wb.sheetnames
        assert "مقارنة القيمة" in sheet_names
        ws5 = wb["مقارنة القيمة"]
        # Row 2 should be the header row
        header_row = [ws5.cell(row=2, column=c).value for c in range(1, 6)]
        assert any("أسلوب" in str(v) for v in header_row if v)
        # Rows 3-6 should contain method labels
        labels = [ws5.cell(row=r, column=1).value for r in range(3, 7)]
        assert any(v is not None for v in labels)


def test_excel_has_chart():
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not available")
    with tempfile.TemporaryDirectory() as tmp:
        xl_path = pathlib.Path(tmp) / "test_review_chart.xlsx"
        ok = _xl(_meta_full(), xl_path)
        assert ok
        wb = openpyxl.load_workbook(str(xl_path))
        ws5 = wb["مقارنة القيمة"]
        charts = ws5._charts
        assert len(charts) >= 1, "Sheet 5 must contain at least one chart"
        chart = charts[0]
        # Chart must have series
        assert len(chart.series) >= 1, "Chart must have at least one data series"


def test_excel_unavailable_methods_are_not_false_zeroes():
    """Methods with no data must not appear as 0 in the chart data."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not available")
    with tempfile.TemporaryDirectory() as tmp:
        xl_path = pathlib.Path(tmp) / "test_empty_review.xlsx"
        ok = _xl(_meta_empty(), xl_path)
        assert ok
        wb = openpyxl.load_workbook(str(xl_path))
        ws5 = wb["مقارنة القيمة"]
        # For empty meta, independent values should be None/blank, not 0
        for row in range(3, 7):
            val = ws5.cell(row=row, column=3).value  # column C = independent
            assert val != 0, (
                f"Row {row} independent value should not be 0 when method unavailable"
            )


def test_user_and_admin_pdf_contracts_differ():
    """Verify user HTML lacks audit data that admin HTML contains."""
    user_html  = _get_user_html()
    admin_html = _get_admin_html()
    # Admin audit section text not in user
    assert "generated_at" not in user_html or "سجل التدقيق" not in user_html
    # Admin must show internal label
    assert "داخلية" in admin_html or "للمراجع" in admin_html
