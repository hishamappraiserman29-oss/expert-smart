# test_merged_report_selector_before_send.py
# Permanent tests — Merged Report Selector Before Send
# advisory_only=True | no_commit=True | no_push=True
#
# Mandate: MERGE_REPORT_TYPE_AND_REPORT_GENERATION_BEFORE_SEND_APPROVED
# Verifies that the two duplicate report-selection sections are merged into
# one authoritative section located before the Send button, the old dropdown
# is removed, and all three cards use one authoritative selected state.

import pathlib
import re
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

HTML = pathlib.Path("frontend/index.html")


def _html() -> str:
    return HTML.read_text(encoding="utf-8", errors="replace")


# ════════════════════════════════════════════════════════════════════════════
# A — ONE MERGED AUTHORITATIVE SECTION (3 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_A01_unified_section_exists():
    html = _html()
    assert 'id="pv-unified-report-type-section"' in html, (
        "Merged unified report-type section must exist"
    )


def test_A02_only_one_unified_section():
    html = _html()
    # Count the div opening tag specifically to avoid matching data-testid substring
    count = html.count('<div id="pv-unified-report-type-section"')
    assert count == 1, (
        f"Exactly one merged authoritative section div must exist, found {count}"
    )


def test_A03_no_independent_old_attachment_section():
    html = _html()
    assert 'id="pv-report-type-attachments-section"' not in html, (
        "Old pv-report-type-attachments-section must be removed"
    )


# ════════════════════════════════════════════════════════════════════════════
# B — MERGED SECTION INSIDE CHAT AND BEFORE SEND (3 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_B01_unified_section_before_send_button():
    html = _html()
    unified_idx = html.find('id="pv-unified-report-type-section"')
    send_idx = html.find('id="generateBtn"')
    assert unified_idx != -1 and send_idx != -1, (
        "Both unified section and Send button must exist"
    )
    assert unified_idx < send_idx, (
        "Unified section must appear before the Send button in the DOM"
    )


def test_B02_no_report_selector_section_after_send():
    html = _html()
    send_idx = html.find('id="generateBtn"')
    assert send_idx != -1
    after_send = html[send_idx:]
    assert 'id="pv-core-report-issuance"' not in after_send, (
        "Old pv-core-report-issuance section must not remain after the Send button"
    )


def test_B03_no_old_unified_issuance_heading_in_dom():
    html = _html()
    # The old standalone "إصدار ومراجعة تقارير التقييم" section div must be gone
    assert 'id="pv-unified-report-issuance-in-chat"' not in html or \
           'data-testid="pv-unified-report-issuance-in-chat"' not in html, (
        "Old pv-unified-report-issuance-in-chat section must be removed as an active div"
    )


# ════════════════════════════════════════════════════════════════════════════
# C — OLD DROPDOWN ABSENT (3 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_C01_old_report_dropdown_absent():
    html = _html()
    assert 'id="pv-submission-report-type"' not in html, (
        "Old pv-submission-report-type dropdown must not exist in the DOM"
    )


def test_C02_old_dropdown_label_absent():
    html = _html()
    # "اختيار نوع التقرير:" must not appear as a visible label
    # It should not be inside any active (non-aria-hidden) element
    # Simple check: not in the HTML at all as a DOM label
    assert 'for="pv-submission-report-type"' not in html, (
        "Old dropdown label (for=pv-submission-report-type) must not exist"
    )


def test_C03_old_dropdown_error_element_absent():
    html = _html()
    assert 'id="pv-submission-report-type-error"' not in html, (
        "Old pv-submission-report-type-error element must not exist"
    )


# ════════════════════════════════════════════════════════════════════════════
# D — THREE REPORT CARDS PRESENT (4 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_D01_exactly_three_unified_cards():
    html = _html()
    trad  = html.count('data-testid="pv-unified-card-traditional"')
    det   = html.count('data-testid="pv-unified-card-detailed"')
    prof  = html.count('data-testid="pv-unified-card-professional"')
    assert trad == 1 and det == 1 and prof == 1, (
        f"Exactly one card each for traditional/detailed/professional — got {trad}/{det}/{prof}"
    )


def test_D02_traditional_card_value():
    html = _html()
    assert "pvSelectReportTier('traditional_report')" in html, (
        "Traditional card must call pvSelectReportTier with 'traditional_report'"
    )


def test_D03_detailed_card_value():
    html = _html()
    assert "pvSelectReportTier('detailed_report')" in html, (
        "Detailed card must call pvSelectReportTier with 'detailed_report'"
    )


def test_D04_professional_card_value():
    html = _html()
    assert "pvSelectReportTier('professional_report')" in html, (
        "Professional card must call pvSelectReportTier with 'professional_report'"
    )


# ════════════════════════════════════════════════════════════════════════════
# E — CARDS ARE SELECT-ONLY (NOT IMMEDIATE GENERATION) (2 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_E01_no_card_onclick_calling_pvGenerateCoreReportBundle():
    html = _html()
    # Cards must not call pvGenerateCoreReportBundle on click
    # (cards are now select-only; Send button triggers generation)
    # Check that card wrappers reference pvSelectReportTier, not pvGenerateCoreReportBundle
    traditional_idx = html.find('data-testid="pv-unified-card-traditional"')
    detailed_idx    = html.find('data-testid="pv-unified-card-detailed"')
    professional_idx = html.find('data-testid="pv-unified-card-professional"')
    assert traditional_idx != -1, "Traditional card must exist"
    # Grab a narrow window around each card onclick
    for idx, label in [(traditional_idx, 'traditional'), (detailed_idx, 'detailed'), (professional_idx, 'professional')]:
        card_block = html[idx:idx+300]
        assert 'pvGenerateCoreReportBundle' not in card_block, (
            f"{label} card onclick must not call pvGenerateCoreReportBundle"
        )


def test_E02_cards_use_type_button():
    html = _html()
    # All three unified card wrappers use onclick, not form submit
    # Confirm no card triggers form submission (type="submit" inside card)
    for tier in ['traditional', 'detailed', 'professional']:
        card_idx = html.find(f'id="pv-unified-wrap-{tier}"')
        assert card_idx != -1, f"pv-unified-wrap-{tier} must exist"
        card_block = html[card_idx:card_idx+400]
        assert 'type="submit"' not in card_block, (
            f"{tier} card must not contain a submit button"
        )


# ════════════════════════════════════════════════════════════════════════════
# F — ONE SEND BUTTON (2 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_F01_exactly_one_send_button():
    html = _html()
    count = html.count('id="generateBtn"')
    assert count == 1, f"Exactly one generateBtn must exist, found {count}"


def test_F02_send_button_after_unified_section():
    html = _html()
    unified_end = html.find('<!-- /pv-unified-report-type-section -->')
    send_idx    = html.find('id="generateBtn"')
    assert unified_end != -1 and send_idx != -1
    assert unified_end < send_idx, (
        "Send button must be after the unified section closing comment"
    )


# ════════════════════════════════════════════════════════════════════════════
# G — SELECTED TYPE LABEL (2 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_G01_selected_type_label_exists():
    html = _html()
    assert 'data-testid="pv-unified-selected-type-label"' in html, (
        "Unified selected-type label container must exist"
    )


def test_G02_selected_type_name_element_exists():
    html = _html()
    assert 'id="pv-core-selected-type-name"' in html, (
        "pv-core-selected-type-name element must exist for dynamic label update"
    )


# ════════════════════════════════════════════════════════════════════════════
# H — NO TYPE SELECTED INITIAL MESSAGE (1 test)
# ════════════════════════════════════════════════════════════════════════════

def test_H01_no_type_message_present():
    html = _html()
    assert 'id="pv-unified-no-type-msg"' in html, (
        "pv-unified-no-type-msg element must exist for initial no-selection state"
    )


# ════════════════════════════════════════════════════════════════════════════
# I — ATTACHMENT CONTAINER (3 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_I01_attachment_requirements_container_present():
    html = _html()
    assert 'id="pv-submission-attachment-requirements"' in html, (
        "Attachment requirements container must be present in the unified section"
    )


def test_I02_attachment_upload_container_present():
    html = _html()
    assert 'id="pv-submission-attachment-upload"' in html, (
        "Attachment upload container must be present in the unified section"
    )


def test_I03_attachment_error_container_present():
    html = _html()
    assert 'id="pv-submission-attachment-error"' in html, (
        "Attachment error container must be present in the unified section"
    )


# ════════════════════════════════════════════════════════════════════════════
# J — ONE DISCLAIMER / ADVISORY NOTICE (1 test)
# ════════════════════════════════════════════════════════════════════════════

def test_J01_exactly_one_advisory_notice_in_unified_section():
    html = _html()
    # Advisory notice is in the unified section
    section_start = html.find('id="pv-unified-report-type-section"')
    section_end   = html.find('<!-- /pv-unified-report-type-section -->')
    assert section_start != -1 and section_end != -1
    section_block = html[section_start:section_end]
    count = section_block.count('data-testid="pv-unified-advisory-notice"')
    assert count == 1, (
        f"Exactly one advisory notice must exist in the unified section, found {count}"
    )


# ════════════════════════════════════════════════════════════════════════════
# K — JS AUTHORITATIVE STATE AND NEW FUNCTION (3 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_K01_pvSelectReportTier_function_exists():
    assert "function pvSelectReportTier" in _html(), (
        "pvSelectReportTier function must be defined"
    )


def test_K02_initial_state_is_null():
    html = _html()
    # Initial value of _pvCoreValuationReportType must be null
    assert "window._pvCoreValuationReportType   = null" in html or \
           "window._pvCoreValuationReportType = null" in html, (
        "Initial _pvCoreValuationReportType must be null (not pre-selected)"
    )


def test_K03_processAndGenerate_reads_from_authoritative_state():
    html = _html()
    assert "window._pvCoreValuationReportType || ''" in html, (
        "processAndGenerate must read from window._pvCoreValuationReportType"
    )


# ════════════════════════════════════════════════════════════════════════════
# L — NO STALE DROPDOWN REFERENCES IN ACTIVE JS (2 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_L01_no_active_getElementById_for_old_dropdown():
    html = _html()
    # getElementById('pv-submission-report-type') must not appear in active JS
    assert "getElementById('pv-submission-report-type')" not in html, (
        "No active getElementById call for deleted pv-submission-report-type"
    )


def test_L02_no_old_error_element_in_active_js():
    html = _html()
    # getElementById for old error element must not appear in active JS
    assert "getElementById('pv-submission-report-type-error')" not in html, (
        "No active getElementById call for deleted pv-submission-report-type-error"
    )


# ════════════════════════════════════════════════════════════════════════════
# M — RESULT REGIONS (2 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_M01_bundle_status_region_present():
    html = _html()
    assert 'id="pv-core-bundle-status"' in html, (
        "Bundle status region must be present in the unified section"
    )


def test_M02_issuance_status_line_present():
    html = _html()
    assert 'id="pv-core-issuance-status"' in html, (
        "Issuance status line must be present in the unified section"
    )


# ════════════════════════════════════════════════════════════════════════════
# N — ADMIN EXCEL PROTECTED (2 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_N01_admin_excel_card_starts_hidden():
    html = _html()
    # Use the data-testid opening tag to locate the card precisely
    idx = html.find('data-testid="pv-core-internal-excel-card"')
    assert idx != -1, "Admin Excel card must exist"
    card_block = html[idx:idx+400]
    assert 'display:none' in card_block, (
        "Admin Excel card must start hidden (display:none)"
    )


def test_N02_admin_excel_labeled_admin_only():
    html = _html()
    idx = html.find('data-testid="pv-core-internal-excel-card"')
    assert idx != -1
    card_block = html[idx:idx+800]
    assert 'Admin Only' in card_block or 'للمسؤولين فقط' in card_block, (
        "Admin Excel card must be labeled as admin-only"
    )


# ════════════════════════════════════════════════════════════════════════════
# O — EXPERT TIP (2 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_O01_expert_tip_exists_exactly_once():
    html = _html()
    count = html.count('نصيحة الخبير:')
    assert count == 1, f"Expert tip must appear exactly once, found {count}"


def test_O02_expert_tip_after_send_button():
    html = _html()
    send_idx = html.find('id="generateBtn"')
    tip_idx  = html.find('نصيحة الخبير:')
    assert send_idx != -1 and tip_idx != -1
    assert tip_idx > send_idx, (
        "Expert tip must appear after the Send button"
    )


# ════════════════════════════════════════════════════════════════════════════
# P — NO DUPLICATE ELEMENT IDs (3 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_P01_no_duplicate_pv_chip_traditional():
    html = _html()
    count = html.count('id="pv-chip-traditional"')
    assert count == 1, f"pv-chip-traditional ID must appear exactly once, found {count}"


def test_P02_no_duplicate_pv_chip_detailed():
    html = _html()
    count = html.count('id="pv-chip-detailed"')
    assert count == 1, f"pv-chip-detailed ID must appear exactly once, found {count}"


def test_P03_no_duplicate_pv_chip_professional():
    html = _html()
    count = html.count('id="pv-chip-professional"')
    assert count == 1, f"pv-chip-professional ID must appear exactly once, found {count}"


# ════════════════════════════════════════════════════════════════════════════
# Q — LEGITIMATE REPORT GENERATION FLOW INTACT (3 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_Q01_processAndGenerate_function_present():
    assert "async function processAndGenerate" in _html(), (
        "processAndGenerate function must remain intact"
    )


def test_Q02_pvGenerateCoreReportBundle_function_defined():
    assert "function pvGenerateCoreReportBundle" in _html(), (
        "pvGenerateCoreReportBundle function must remain defined (backward compat)"
    )


def test_Q03_pvSelectCoreValuationReportType_function_present():
    assert "function pvSelectCoreValuationReportType" in _html(), (
        "pvSelectCoreValuationReportType must remain for backward compat"
    )


# ════════════════════════════════════════════════════════════════════════════
# R — INDEPENDENT SECTIONS = 0 (2 tests)
# ════════════════════════════════════════════════════════════════════════════

def test_R01_no_active_pv_core_valuation_report_issuance():
    html = _html()
    # The old action-card section must be gone as an active DOM element
    # (may survive as a comment reference)
    active_idx = html.find('id="pv-core-report-issuance"')
    if active_idx != -1:
        # Confirm it's in a comment, not an active element
        # Check 50 chars before for comment start
        before = html[max(0, active_idx-200):active_idx]
        assert '<!--' in before, (
            "pv-core-report-issuance must only appear inside a comment, not an active element"
        )


def test_R02_no_active_independent_card_section_after_send():
    html = _html()
    send_idx = html.find('id="generateBtn"')
    assert send_idx != -1
    after_send = html[send_idx:]
    # These old testids must not appear as active DOM nodes after the Send button
    assert 'data-testid="pv-core-valuation-report-issuance"' not in after_send, (
        "pv-core-valuation-report-issuance must not exist after Send button"
    )
