# test_preliminary_weighted_valuation_removal.py
# Permanent tests — Preliminary Weighted Valuation UI Removal
# advisory_only=True | no_commit=True | no_push=True
#
# Mandate: REMOVE_PRELIMINARY_WEIGHTED_VALUATION_UI_APPROVED
# Verifies complete removal of the preliminary weighted valuation section,
# its inputs, JS logic, navigation references, and layout cleanup.

import pathlib
import re
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

HTML = pathlib.Path("frontend/index.html")


def _html() -> str:
    return HTML.read_text(encoding="utf-8", errors="replace")


# ════════════════════════════════════════════════════════════════════════════
# A — SECTION HEADINGS ABSENT (3 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_A01_english_heading_absent():
    assert "Preliminary Weighted Valuation" not in _html(), (
        "'Preliminary Weighted Valuation' must not appear anywhere in the HTML"
    )


def test_A02_arabic_engine_heading_absent():
    assert "محرك الترجيح المبدئي" not in _html(), (
        "'محرك الترجيح المبدئي' must not appear anywhere in the HTML"
    )


def test_A03_arabic_result_heading_absent():
    assert "القيمة المرجحة المبدئية غير معتمدة" not in _html(), (
        "'القيمة المرجحة المبدئية غير معتمدة' must not appear anywhere in the HTML"
    )


# ════════════════════════════════════════════════════════════════════════════
# B — SALES COMPARISON CONTROLS ABSENT (2 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_B01_sales_comparison_weight_input_absent():
    html = _html()
    assert 'id="prof-sales-weight"' not in html, (
        "Sales comparison weight input (id=prof-sales-weight) must not be in the DOM"
    )


def test_B02_sales_comparison_value_input_absent():
    html = _html()
    assert 'id="prof-sales-value"' not in html, (
        "Sales comparison value input (id=prof-sales-value) must not be in the DOM"
    )


# ════════════════════════════════════════════════════════════════════════════
# C — INCOME APPROACH CONTROLS ABSENT (2 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_C01_income_approach_weight_input_absent():
    html = _html()
    assert 'id="prof-income-weight"' not in html, (
        "Income approach weight input (id=prof-income-weight) must not be in the DOM"
    )


def test_C02_income_approach_value_input_absent():
    html = _html()
    assert 'id="prof-income-value"' not in html, (
        "Income approach value input (id=prof-income-value) must not be in the DOM"
    )


# ════════════════════════════════════════════════════════════════════════════
# D — COST APPROACH CONTROLS ABSENT (2 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_D01_cost_approach_weight_input_absent():
    html = _html()
    assert 'id="prof-cost-weight"' not in html, (
        "Cost approach weight input (id=prof-cost-weight) must not be in the DOM"
    )


def test_D02_cost_approach_value_input_absent():
    html = _html()
    assert 'id="prof-cost-value"' not in html, (
        "Cost approach value input (id=prof-cost-value) must not be in the DOM"
    )


# ════════════════════════════════════════════════════════════════════════════
# E — SENSITIVITY AND RESULT CONTROLS ABSENT (2 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_E01_preliminary_sensitivity_control_absent():
    html = _html()
    assert 'id="prof-sensitivity-output"' not in html, (
        "Preliminary sensitivity output (id=prof-sensitivity-output) must not be in the DOM"
    )


def test_E02_preliminary_weighted_result_card_absent():
    html = _html()
    assert 'id="prof-weighted-value"' not in html, (
        "Preliminary weighted value output (id=prof-weighted-value) must not be in the DOM"
    )


# ════════════════════════════════════════════════════════════════════════════
# F — PRELIMINARY WARNING AND PANEL ABSENT (2 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_F01_preliminary_warning_absent():
    assert "غير معتمدة ولا تستند إلى شواهد بيعية حقيقية" not in _html(), (
        "Preliminary engine warning text must not appear anywhere in the HTML"
    )


def test_F02_preliminary_panel_container_absent():
    html = _html()
    assert 'data-testid="professional-weighted-engine-panel"' not in html, (
        "professional-weighted-engine-panel container must not be in the DOM"
    )


# ════════════════════════════════════════════════════════════════════════════
# G — NO HIDDEN DUPLICATES (2 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_G01_no_hidden_preliminary_section_by_display_none():
    html = _html()
    # Look for the panel testid anywhere combined with display:none
    assert "professional-weighted-engine-panel" not in html, (
        "No hidden copy of professional-weighted-engine-panel should remain"
    )


def test_G02_weights_total_warning_absent():
    html = _html()
    assert 'id="prof-weights-warning"' not in html, (
        "Preliminary weights total warning element must not be in the DOM"
    )


# ════════════════════════════════════════════════════════════════════════════
# H — STALE JAVASCRIPT REFERENCES ABSENT (3 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_H01_calcProfWeightedValue_function_absent():
    assert "calcProfWeightedValue" not in _html(), (
        "calcProfWeightedValue function must not exist in JavaScript"
    )


def test_H02_preliminary_panel_dom_probe_absent():
    html = _html()
    # The DOMContentLoaded probe that hid the panel is removed
    assert "keep panel visible" not in html, (
        "Stale DOMContentLoaded panel probe must not exist"
    )


def test_H03_cmpLoadSchema_no_longer_hides_preliminary_panel():
    html = _html()
    # The composite schema loader must not reference the preliminary panel
    idx = html.find("function cmpLoadSchema")
    assert idx != -1, "cmpLoadSchema must still exist"
    func_body = html[idx: idx + 800]
    assert "professional-weighted-engine-panel" not in func_body, (
        "cmpLoadSchema must not reference the deleted preliminary panel"
    )


# ════════════════════════════════════════════════════════════════════════════
# I — NO EMPTY CONTAINER IN PREVIOUS LOCATION (2 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_I01_no_stale_3B_comment():
    html = _html()
    assert "STEP 3B" not in html, (
        "Stale STEP 3B comment block must not remain in the HTML"
    )


def test_I02_3_4_section_follows_naturally_after_removal():
    html = _html()
    # After removal, 3.4 section should appear without the preliminary panel block between
    # the purpose routing summary and 3.4
    idx_routing = html.find("pro-val-purpose-routing-summary")
    idx_34 = html.find("pro-val-scope-of-work-subsection")
    assert idx_routing != -1 and idx_34 != -1, (
        "Both surrounding sections must still exist"
    )
    gap = html[idx_routing: idx_34]
    assert "prof-sales-value" not in gap, (
        "Preliminary inputs must not appear in the gap between surrounding sections"
    )


# ════════════════════════════════════════════════════════════════════════════
# J — NAVIGATION REFERENCE REMOVED (1 test)
# ════════════════════════════════════════════════════════════════════════════

def test_J01_active_controls_list_no_preliminary_engine_entry():
    html = _html()
    idx = html.find("pro-val-active-controls-list")
    assert idx != -1, "Active controls list must still exist"
    list_block = html[idx: idx + 1500]
    assert "محرك الترجيح المبدئي" not in list_block, (
        "Navigation list must not reference محرك الترجيح المبدئي"
    )


# ════════════════════════════════════════════════════════════════════════════
# K — LEGITIMATE VALUATION METHODS UNTOUCHED (4 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_K01_sales_comparison_method_remains_in_legitimate_workflow():
    html = _html()
    # pvCalcWeightingTotal reads pvr-vis-sales-comparison-weight — a different control
    assert "pvr-vis-sales-comparison-weight" in html, (
        "Legitimate pvr-vis-sales-comparison-weight control must remain untouched"
    )


def test_K02_income_approach_remains_in_legitimate_workflow():
    html = _html()
    assert "pvr-vis-income-approach-weight" in html, (
        "Legitimate pvr-vis-income-approach-weight control must remain untouched"
    )


def test_K03_cost_approach_remains_in_legitimate_workflow():
    html = _html()
    assert "pvr-vis-cost-approach-weight" in html, (
        "Legitimate pvr-vis-cost-approach-weight control must remain untouched"
    )


def test_K04_pvCalcWeightingTotal_function_remains():
    assert "pvCalcWeightingTotal" in _html(), (
        "Legitimate pvCalcWeightingTotal function must remain untouched"
    )


# ════════════════════════════════════════════════════════════════════════════
# L — REPORT AND EXPERT-REVIEW WORKFLOWS UNTOUCHED (3 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_L01_report_generation_controls_present():
    html = _html()
    assert "unified_report_action" in html or "generate-report" in html or "pvGenerateReport" in html, (
        "Report generation trigger must remain in the HTML"
    )


def test_L02_hbu_analysis_section_present():
    html = _html()
    assert "hbu" in html.lower() or "أعلى وأفضل استخدام" in html, (
        "HBU analysis section must still be present"
    )


def test_L03_expert_review_workflow_present():
    html = _html()
    assert "openExpertRequestModal" in html or "expert-review" in html or "خبير" in html, (
        "Expert review workflow must remain intact"
    )
