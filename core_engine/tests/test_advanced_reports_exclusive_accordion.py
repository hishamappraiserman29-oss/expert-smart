# test_advanced_reports_exclusive_accordion.py
# Permanent tests — Advanced Reports Exclusive Accordion
# advisory_only=True | no_commit=True | no_push=True
#
# Mandate: ADVANCED_REPORTS_EXCLUSIVE_REQUIREMENTS_ACCORDION_APPROVED
# Verifies:
#   - Four workflow button labels exactly as mandated (Arabic text)
#   - Old incorrect labels removed from button proximity
#   - All four buttons have aria-expanded="false" in initial HTML
#   - All four buttons have correct aria-controls pointing to panel IDs
#   - Authoritative state variable window.activeAdvancedReportPanel used
#   - Old state variable window._pvOpenSpecialReportPanel absent
#   - _PV_SPECIAL_BTN_IDS map defined with all four keys
#   - pvOpenSpecialReportRequirementsTable resets all aria, sets active one
#   - Exclusive toggle: same panel click collapses it (state = null)
#   - pvCloseSpecialReportPanel resets aria-expanded and state
#   - Simulation panel heading corrected to "محاكاة التقرير"
#   - All four requirement panel IDs present, each exactly once

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

HTML = pathlib.Path("frontend/index.html")


def _html() -> str:
    return HTML.read_text(encoding="utf-8", errors="replace")


# ════════════════════════════════════════════════════════════════════════════
# A — BUTTON LABELS (4 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_A01_button1_label_report_review():
    html = _html()
    assert "فتح متطلبات مراجعة التقارير" in html, (
        "Button 1 must say 'فتح متطلبات مراجعة التقارير'"
    )


def test_A02_button2_label_simulation():
    html = _html()
    assert "فتح متطلبات محاكاة التقرير" in html, (
        "Button 2 must say 'فتح متطلبات محاكاة التقرير'"
    )


def test_A03_button3_label_hbu():
    html = _html()
    assert "فتح متطلبات أعلى وأفضل استخدام" in html, (
        "Button 3 must say 'فتح متطلبات أعلى وأفضل استخدام'"
    )


def test_A04_button4_label_standards():
    html = _html()
    assert "فتح متطلبات امتثال المعايير" in html, (
        "Button 4 must say 'فتح متطلبات امتثال المعايير'"
    )


# ════════════════════════════════════════════════════════════════════════════
# B — OLD INCORRECT LABELS REMOVED (2 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_B01_old_button1_label_absent_near_btn():
    html = _html()
    idx = html.index('data-testid="pv-open-report-review-table"')
    nearby = html[idx: idx + 400]
    assert "مراجعة التقرير المرفوع" not in nearby, (
        "Old button 1 text 'مراجعة التقرير المرفوع' must not appear near pv-open-report-review-table"
    )


def test_B02_old_button2_label_absent_near_btn():
    html = _html()
    idx = html.index('data-testid="pv-open-simulation-table"')
    nearby = html[idx: idx + 400]
    assert "رفع تقرير للمراجعة والتحليل" not in nearby, (
        "Old button 2 text 'رفع تقرير للمراجعة والتحليل' must not appear near pv-open-simulation-table"
    )


# ════════════════════════════════════════════════════════════════════════════
# C — ARIA INITIAL STATE: all buttons aria-expanded="false" (4 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_C01_btn_report_review_aria_expanded_false():
    html = _html()
    idx = html.index('id="pv-btn-report-review"')
    nearby = html[idx: idx + 400]
    assert 'aria-expanded="false"' in nearby, (
        "pv-btn-report-review must have aria-expanded='false' in initial HTML"
    )


def test_C02_btn_simulation_aria_expanded_false():
    html = _html()
    idx = html.index('id="pv-btn-simulation"')
    nearby = html[idx: idx + 400]
    assert 'aria-expanded="false"' in nearby, (
        "pv-btn-simulation must have aria-expanded='false' in initial HTML"
    )


def test_C03_btn_hbu_aria_expanded_false():
    html = _html()
    idx = html.index('id="pv-btn-hbu"')
    nearby = html[idx: idx + 400]
    assert 'aria-expanded="false"' in nearby, (
        "pv-btn-hbu must have aria-expanded='false' in initial HTML"
    )


def test_C04_btn_standards_aria_expanded_false():
    html = _html()
    idx = html.index('id="pv-btn-standards"')
    nearby = html[idx: idx + 400]
    assert 'aria-expanded="false"' in nearby, (
        "pv-btn-standards must have aria-expanded='false' in initial HTML"
    )


# ════════════════════════════════════════════════════════════════════════════
# D — aria-controls CORRECT FOR EACH BUTTON (4 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_D01_btn_report_review_aria_controls():
    html = _html()
    idx = html.index('id="pv-btn-report-review"')
    nearby = html[idx: idx + 500]
    assert 'aria-controls="pv-req-panel-report-review"' in nearby, (
        "pv-btn-report-review must have aria-controls='pv-req-panel-report-review'"
    )


def test_D02_btn_simulation_aria_controls():
    html = _html()
    idx = html.index('id="pv-btn-simulation"')
    nearby = html[idx: idx + 500]
    assert 'aria-controls="pv-req-panel-simulation"' in nearby, (
        "pv-btn-simulation must have aria-controls='pv-req-panel-simulation'"
    )


def test_D03_btn_hbu_aria_controls():
    html = _html()
    idx = html.index('id="pv-btn-hbu"')
    nearby = html[idx: idx + 500]
    assert 'aria-controls="pv-req-panel-hbu"' in nearby, (
        "pv-btn-hbu must have aria-controls='pv-req-panel-hbu'"
    )


def test_D04_btn_standards_aria_controls():
    html = _html()
    idx = html.index('id="pv-btn-standards"')
    nearby = html[idx: idx + 500]
    assert 'aria-controls="pv-req-panel-standards"' in nearby, (
        "pv-btn-standards must have aria-controls='pv-req-panel-standards'"
    )


# ════════════════════════════════════════════════════════════════════════════
# E — AUTHORITATIVE STATE VARIABLE (2 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_E01_active_panel_state_variable_present():
    html = _html()
    assert "window.activeAdvancedReportPanel" in html, (
        "Authoritative state variable window.activeAdvancedReportPanel must be used"
    )


def test_E02_old_state_variable_completely_absent():
    html = _html()
    assert "window._pvOpenSpecialReportPanel" not in html, (
        "Old state variable window._pvOpenSpecialReportPanel must be fully replaced"
    )


# ════════════════════════════════════════════════════════════════════════════
# F — _PV_SPECIAL_BTN_IDS MAP (3 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_F01_btn_ids_map_defined():
    html = _html()
    assert "_PV_SPECIAL_BTN_IDS" in html, (
        "_PV_SPECIAL_BTN_IDS map must be defined for ARIA sync"
    )


def test_F02_btn_ids_map_contains_all_four_btn_ids():
    html = _html()
    idx = html.index("_PV_SPECIAL_BTN_IDS")
    nearby = html[idx: idx + 500]
    for btn_id in ("pv-btn-report-review", "pv-btn-simulation",
                   "pv-btn-hbu", "pv-btn-standards"):
        assert btn_id in nearby, (
            f"_PV_SPECIAL_BTN_IDS must contain button id '{btn_id}'"
        )


def test_F03_btn_ids_map_has_all_four_type_keys():
    html = _html()
    idx = html.index("_PV_SPECIAL_BTN_IDS")
    nearby = html[idx: idx + 500]
    for key in ("report_review_output", "simulated_uploaded_report",
                "hbu_analysis_report", "standards_compliance_report"):
        assert key in nearby, (
            f"_PV_SPECIAL_BTN_IDS must contain key '{key}'"
        )


# ════════════════════════════════════════════════════════════════════════════
# G — EXCLUSIVE ACCORDION LOGIC IN pvOpenSpecialReportRequirementsTable (4 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_G01_open_fn_resets_all_panel_displays():
    html = _html()
    fn_idx = html.index("function pvOpenSpecialReportRequirementsTable(type)")
    fn_body = html[fn_idx: fn_idx + 1400]
    assert "_PV_SPECIAL_PANEL_IDS" in fn_body, (
        "pvOpenSpecialReportRequirementsTable must iterate _PV_SPECIAL_PANEL_IDS to close all panels"
    )


def test_G02_open_fn_resets_all_btn_aria_to_false():
    html = _html()
    fn_idx = html.index("function pvOpenSpecialReportRequirementsTable(type)")
    fn_body = html[fn_idx: fn_idx + 1400]
    assert "_PV_SPECIAL_BTN_IDS" in fn_body, (
        "pvOpenSpecialReportRequirementsTable must iterate _PV_SPECIAL_BTN_IDS to reset aria"
    )
    assert "setAttribute('aria-expanded', 'false')" in fn_body, (
        "pvOpenSpecialReportRequirementsTable must call setAttribute('aria-expanded','false') on all btns"
    )


def test_G03_open_fn_sets_active_btn_aria_to_true():
    html = _html()
    fn_idx = html.index("function pvOpenSpecialReportRequirementsTable(type)")
    fn_body = html[fn_idx: fn_idx + 1400]
    assert "setAttribute('aria-expanded', 'true')" in fn_body, (
        "pvOpenSpecialReportRequirementsTable must set aria-expanded='true' on the active button"
    )


def test_G04_open_fn_exclusive_toggle_collapses_same_panel():
    html = _html()
    fn_idx = html.index("function pvOpenSpecialReportRequirementsTable(type)")
    fn_body = html[fn_idx: fn_idx + 1400]
    assert "window.activeAdvancedReportPanel === type" in fn_body, (
        "Exclusive toggle: open function must check if same panel already open"
    )
    assert "window.activeAdvancedReportPanel = null" in fn_body, (
        "Exclusive toggle: open function must set state to null when toggling closed"
    )


# ════════════════════════════════════════════════════════════════════════════
# H — pvCloseSpecialReportPanel ARIA RESET (2 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_H01_close_fn_resets_btn_aria_expanded():
    html = _html()
    fn_idx = html.index("function pvCloseSpecialReportPanel(type)")
    fn_body = html[fn_idx: fn_idx + 600]
    assert "_PV_SPECIAL_BTN_IDS" in fn_body, (
        "pvCloseSpecialReportPanel must reference _PV_SPECIAL_BTN_IDS to reset button aria"
    )
    assert "setAttribute('aria-expanded', 'false')" in fn_body, (
        "pvCloseSpecialReportPanel must reset aria-expanded to 'false' on the button"
    )


def test_H02_close_fn_nulls_state_variable():
    html = _html()
    fn_idx = html.index("function pvCloseSpecialReportPanel(type)")
    fn_body = html[fn_idx: fn_idx + 600]
    assert "window.activeAdvancedReportPanel = null" in fn_body, (
        "pvCloseSpecialReportPanel must set window.activeAdvancedReportPanel = null"
    )


# ════════════════════════════════════════════════════════════════════════════
# I — SIMULATION PANEL HEADING CORRECTED (2 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_I01_simulation_panel_heading_is_correct():
    html = _html()
    idx = html.index('id="pv-req-panel-simulation"')
    nearby = html[idx: idx + 1500]
    assert "محاكاة التقرير" in nearby, (
        "Simulation panel heading must contain 'محاكاة التقرير'"
    )


def test_I02_simulation_panel_old_heading_removed():
    html = _html()
    idx = html.index('id="pv-req-panel-simulation"')
    nearby = html[idx: idx + 1500]
    assert "محاكاة تقرير مرفوع" not in nearby, (
        "Simulation panel must NOT say 'محاكاة تقرير مرفوع' (old upload/review wording)"
    )


# ════════════════════════════════════════════════════════════════════════════
# J — PANEL IDs PRESENT EXACTLY ONCE (4 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_J01_panel_report_review_id_unique():
    html = _html()
    count = html.count('id="pv-req-panel-report-review"')
    assert count == 1, f"pv-req-panel-report-review must appear exactly once; found {count}"


def test_J02_panel_simulation_id_unique():
    html = _html()
    count = html.count('id="pv-req-panel-simulation"')
    assert count == 1, f"pv-req-panel-simulation must appear exactly once; found {count}"


def test_J03_panel_hbu_id_unique():
    html = _html()
    count = html.count('id="pv-req-panel-hbu"')
    assert count == 1, f"pv-req-panel-hbu must appear exactly once; found {count}"


def test_J04_panel_standards_id_unique():
    html = _html()
    count = html.count('id="pv-req-panel-standards"')
    assert count == 1, f"pv-req-panel-standards must appear exactly once; found {count}"


# ════════════════════════════════════════════════════════════════════════════
# K — AT MOST ONE aria-expanded="true" IN THE WORKFLOW SECTION AT INITIAL LOAD (1 test)
# ════════════════════════════════════════════════════════════════════════════

def test_K01_at_most_one_aria_expanded_true_among_workflow_btns():
    html = _html()
    # Count aria-expanded="true" on the four workflow buttons in the initial HTML
    btn_ids = ("pv-btn-report-review", "pv-btn-simulation",
               "pv-btn-hbu", "pv-btn-standards")
    true_count = 0
    for btn_id in btn_ids:
        idx = html.index(f'id="{btn_id}"')
        nearby = html[idx: idx + 500]
        if 'aria-expanded="true"' in nearby:
            true_count += 1
    assert true_count == 0, (
        f"No workflow button may have aria-expanded='true' at initial load; found {true_count}"
    )
