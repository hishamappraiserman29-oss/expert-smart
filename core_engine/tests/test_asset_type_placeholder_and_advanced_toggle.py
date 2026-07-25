# test_asset_type_placeholder_and_advanced_toggle.py
# Permanent tests — Asset Type Placeholder Reset and Advanced Requirements Toggle
# advisory_only=True | no_commit=True
#
# Mandate: ASSET_TYPE_PLACEHOLDER_AND_ADVANCED_REQUIREMENTS_TOGGLE_APPROVED
# Verifies:
#   Part 1: "اختر نوع الأصل" placeholder is selectable (not disabled), has empty value,
#            validation message appears when submitting without a real asset type,
#            and reset behavior clears stale state.
#   Part 2: Advanced requirements panel is initially collapsed, toggle button
#            controls show/hide, aria-expanded updates, unique IDs, no duplicates.

import pathlib
import re
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

HTML = pathlib.Path("frontend/index.html")


def _html() -> str:
    return HTML.read_text(encoding="utf-8", errors="replace")


# ════════════════════════════════════════════════════════════════════════════
# PART 1 — Asset Type Placeholder
# ════════════════════════════════════════════════════════════════════════════

# ── AT01: Placeholder option exists exactly once ─────────────────────────────
def test_AT01_asset_type_placeholder_exists_once():
    html = _html()
    assert html.count('pro-val-asset-type-placeholder') == 1, (
        "data-testid='pro-val-asset-type-placeholder' must appear exactly once"
    )


# ── AT02: Placeholder value is empty ─────────────────────────────────────────
def test_AT02_asset_type_placeholder_value_is_empty():
    html = _html()
    idx = html.index('pro-val-asset-type-placeholder')
    # Walk back to find the opening <option tag
    opt_start = html.rindex('<option', 0, idx)
    opt_snippet = html[opt_start:opt_start+160]
    # value="" must be present and empty
    assert 'value=""' in opt_snippet, (
        f"Placeholder option must have value='' (empty). Snippet: {opt_snippet[:80]}"
    )


# ── AT03: Placeholder is NOT disabled ────────────────────────────────────────
def test_AT03_asset_type_placeholder_not_disabled():
    html = _html()
    idx = html.index('pro-val-asset-type-placeholder')
    opt_start = html.rindex('<option', 0, idx)
    opt_snippet = html[opt_start:opt_start+160]
    assert 'disabled' not in opt_snippet, (
        "Placeholder option must NOT have the 'disabled' attribute"
    )


# ── AT04: The select itself is not disabled or aria-disabled ─────────────────
def test_AT04_asset_type_select_not_disabled():
    html = _html()
    idx = html.index('id="asset-type" data-testid="pro-val-asset-type-select"')
    # The <select> opening starts just before `id="asset-type"`
    sel_tag_start = html.rindex('<select', 0, idx)
    # Find closing > of the opening tag (use 1000 chars to be safe — it has long onchange)
    snippet = html[sel_tag_start:sel_tag_start+1000]
    close_angle = snippet.index('>')
    opening_tag = snippet[:close_angle]
    assert ' disabled' not in opening_tag, (
        "The asset-type <select> must not have the 'disabled' attribute"
    )


# ── AT05: Placeholder can be returned-to after selecting real asset type ──────
#    (Static check: the option has no disabled — Playwright handles the dynamic part)
def test_AT05_asset_type_placeholder_selectable():
    html = _html()
    # Confirmed by AT03 (no disabled). This test captures the intent separately.
    idx = html.index('pro-val-asset-type-placeholder')
    opt_start = html.rindex('<option', 0, idx)
    opt_text = html[opt_start:opt_start+160]
    assert 'disabled' not in opt_text
    assert 'value=""' in opt_text


# ── AT06: No API request with empty asset type (JS validation present) ────────
def test_AT06_empty_asset_type_blocked_by_js_validation():
    html = _html()
    # The JS validation must appear in processAndGenerate before the API call
    assert 'يرجى اختيار نوع الأصل أولًا.' in html, (
        "Arabic validation message must be present in JS"
    )
    # Check that the check happens BEFORE the API call (btn.innerHTML line)
    msg_idx  = html.index('يرجى اختيار نوع الأصل أولًا.')
    btn_idx  = html.index('جاري التحليل... <i class="fas fa-spinner fa-spin"></i>')
    assert msg_idx < btn_idx, (
        "Asset type validation must occur BEFORE setting btn.innerHTML (API call)"
    )


# ── AT07: Empty asset type submission is blocked ──────────────────────────────
def test_AT07_empty_asset_submission_returns_early():
    html = _html()
    # The JS must have a return statement after the validation message
    msg_idx = html.index('يرجى اختيار نوع الأصل أولًا.')
    # Look for 'return;' within 400 chars of the message (scrollIntoView + focus precede return)
    nearby = html[msg_idx:msg_idx+400]
    assert 'return;' in nearby, (
        "A 'return;' statement must follow the asset type validation message"
    )


# ── AT08: Arabic validation message text is correct ──────────────────────────
def test_AT08_arabic_validation_message_correct():
    html = _html()
    assert 'يرجى اختيار نوع الأصل أولًا.' in html


# ── AT09: Validation error div is present with correct testid ────────────────
def test_AT09_validation_error_div_present():
    html = _html()
    assert 'id="pro-val-asset-type-error"' in html
    assert 'data-testid="pro-val-asset-type-error"' in html
    # Must have role=alert for accessibility
    idx = html.index('id="pro-val-asset-type-error"')
    nearby = html[idx:idx+300]
    assert 'role="alert"' in nearby, "Error div must have role='alert'"


# ── AT10: Error div is initially hidden ──────────────────────────────────────
def test_AT10_validation_error_initially_hidden():
    html = _html()
    idx = html.index('id="pro-val-asset-type-error"')
    nearby = html[idx:idx+300]
    assert 'display:none' in nearby, "Error div must be initially hidden (display:none)"


# ════════════════════════════════════════════════════════════════════════════
# PART 2 — Advanced Requirements Toggle
# ════════════════════════════════════════════════════════════════════════════

# ── AT11: Requirements panel exists exactly once ──────────────────────────────
def test_AT11_requirements_panel_exists_once():
    html = _html()
    count = html.count('data-testid="pv-advanced-req-panel"')
    assert count == 1, f"Requirements panel testid must appear exactly once; got {count}"


# ── AT12: Requirements panel is initially collapsed ───────────────────────────
def test_AT12_requirements_panel_initially_collapsed():
    html = _html()
    idx = html.index('data-testid="pv-advanced-req-panel"')
    # Find the div opening — walk back
    div_start = html.rindex('<div', 0, idx)
    div_snippet = html[div_start:div_start+160]
    assert 'display:none' in div_snippet, (
        "Requirements panel must have display:none in static HTML (initially collapsed)"
    )


# ── AT13: Toggle button exists exactly once ───────────────────────────────────
def test_AT13_toggle_button_exists_once():
    html = _html()
    count = html.count('data-testid="pv-advanced-req-toggle"')
    assert count == 1, f"Toggle button testid must appear exactly once; got {count}"


# ── AT14: Toggle button initial label is "عرض المتطلبات" ─────────────────────
def test_AT14_toggle_button_initial_label_is_show():
    html = _html()
    idx = html.index('data-testid="pv-advanced-req-toggle-label"')
    label_snippet = html[idx:idx+100]
    assert 'عرض المتطلبات' in label_snippet, (
        "Toggle button initial label must be 'عرض المتطلبات'"
    )


# ── AT15: Toggle function contains expand logic ───────────────────────────────
def test_AT15_toggle_function_has_expand_logic():
    html = _html()
    fn_idx = html.index('function pvToggleAdvancedRequirements')
    fn_body = html[fn_idx:fn_idx+600]
    assert "panel.style.display = expanded ? 'block' : 'none'" in fn_body or \
           "display = expanded" in fn_body, (
        "Toggle function must set panel display based on expanded state"
    )


# ── AT16: Toggle function sets aria-expanded ──────────────────────────────────
def test_AT16_toggle_function_updates_aria_expanded():
    html = _html()
    fn_idx = html.index('function pvToggleAdvancedRequirements')
    fn_body = html[fn_idx:fn_idx+600]
    assert 'aria-expanded' in fn_body, (
        "Toggle function must update aria-expanded attribute"
    )


# ── AT17: Toggle function updates label ───────────────────────────────────────
def test_AT17_toggle_function_updates_label():
    html = _html()
    fn_idx = html.index('function pvToggleAdvancedRequirements')
    fn_body = html[fn_idx:fn_idx+900]  # 900 chars to capture full function body
    assert 'إخفاء المتطلبات' in fn_body, (
        "Toggle function must set label to 'إخفاء المتطلبات' when expanded"
    )
    assert 'عرض المتطلبات' in fn_body, (
        "Toggle function must set label back to 'عرض المتطلبات' when collapsed"
    )


# ── AT18: Toggle function collapses on second call ────────────────────────────
def test_AT18_toggle_function_is_truly_bidirectional():
    html = _html()
    fn_idx = html.index('function pvToggleAdvancedRequirements')
    fn_body = html[fn_idx:fn_idx+700]
    # Must flip a boolean state variable
    assert '_pvAdvancedRequirementsExpanded' in html, (
        "_pvAdvancedRequirementsExpanded state variable must exist"
    )
    assert '!window._pvAdvancedRequirementsExpanded' in fn_body, (
        "Toggle function must negate the state on each click"
    )


# ── AT19: aria-expanded is false initially on toggle button ───────────────────
def test_AT19_aria_expanded_initially_false():
    html = _html()
    btn_testid_idx = html.index('data-testid="pv-advanced-req-toggle"')
    btn_start = html.rindex('<button', 0, btn_testid_idx)
    btn_snippet = html[btn_start:btn_start+700]
    assert 'aria-expanded="false"' in btn_snippet, (
        "Toggle button must have aria-expanded='false' initially"
    )


# ── AT20: aria-controls links button to panel ─────────────────────────────────
def test_AT20_aria_controls_links_to_panel():
    html = _html()
    btn_testid_idx = html.index('data-testid="pv-advanced-req-toggle"')
    btn_start = html.rindex('<button', 0, btn_testid_idx)
    btn_snippet = html[btn_start:btn_start+700]
    assert 'aria-controls="pv-advanced-req-panel"' in btn_snippet, (
        "Toggle button aria-controls must point to pv-advanced-req-panel"
    )


# ── AT21: Toggle button uses type="button" ───────────────────────────────────
def test_AT21_toggle_button_type_button():
    html = _html()
    btn_testid_idx = html.index('data-testid="pv-advanced-req-toggle"')
    btn_start = html.rindex('<button', 0, btn_testid_idx)
    btn_snippet = html[btn_start:btn_start+200]
    assert 'type="button"' in btn_snippet, (
        "Toggle button must have type='button' to avoid form submission"
    )


# ── AT22: Requirements panel is inside pv-special-report-workflows ────────────
def test_AT22_panel_inside_special_report_workflows():
    html = _html()
    idx_section    = html.index('id="pv-special-report-workflows"')
    idx_section_end = html.index('<!-- /pv-special-report-workflows -->')
    idx_panel = html.index('data-testid="pv-advanced-req-panel"')
    assert idx_section < idx_panel < idx_section_end, (
        "pv-advanced-req-panel must be inside pv-special-report-workflows"
    )


# ── AT23: Toggle button is inside pv-special-report-workflows ─────────────────
def test_AT23_toggle_inside_special_report_workflows():
    html = _html()
    idx_section     = html.index('id="pv-special-report-workflows"')
    idx_section_end = html.index('<!-- /pv-special-report-workflows -->')
    idx_toggle = html.index('data-testid="pv-advanced-req-toggle"')
    assert idx_section < idx_toggle < idx_section_end, (
        "Toggle button must be inside pv-special-report-workflows"
    )


# ── AT24: Workflow buttons remain inside the requirements panel ───────────────
def test_AT24_workflow_buttons_inside_panel():
    html = _html()
    idx_panel_open  = html.index('data-testid="pv-advanced-req-panel"')
    idx_panel_close = html.rindex('/pv-advanced-req-panel')
    idx_workflow_btns = html.index('data-testid="pv-special-workflow-buttons"')
    assert idx_panel_open < idx_workflow_btns < idx_panel_close, (
        "Workflow buttons must be inside pv-advanced-req-panel"
    )


# ── AT25: Section heading remains outside (always visible) ────────────────────
def test_AT25_section_heading_outside_panel():
    html = _html()
    idx_panel_open   = html.index('data-testid="pv-advanced-req-panel"')
    idx_heading      = html.index('data-testid="pv-advanced-reports-heading"')
    # Heading must appear BEFORE the panel (so it's always visible)
    assert idx_heading < idx_panel_open, (
        "Section heading must appear before (outside of) the requirements panel"
    )


# ── AT26: Backward compat — previous session's mandate not broken ─────────────
def test_AT26_previous_mandate_not_broken():
    html = _html()
    # Three chip buttons still present
    for chip in ['pv-core-report-chip-traditional',
                 'pv-core-report-chip-detailed',
                 'pv-core-report-chip-professional']:
        assert html.count(chip) == 1, f"Chip {chip!r} must appear exactly once"
    # Legacy selector still present
    assert 'pv-legacy-seven-report-selector-hidden' in html
    # Backward-compat spans present
    assert 'data-testid="pro-val-request-expert-review-button"' in html
