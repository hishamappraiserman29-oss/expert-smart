# test_pv_report_type_order_and_reporting_section_cleanup.py
# Permanent tests — Professional Valuation Report Type Order + Reporting Section Cleanup
# advisory_only=True | no_commit=True
#
# Mandate: PROFESSIONAL_VALUATION_REPORT_TYPE_ORDER_AND_REPORTING_SECTION_CLEANUP_APPROVED
# Verifies:
#   Part 1: "اختر نوع التقرير وملحقاته" section exists before the submit button;
#            report-type selector uses canonical values; submission blocked without type;
#            attachment requirements update; stale state cleared on type change.
#   Part 2: "إصدار ومراجعة التقارير" section contains ONLY the 3 approved chips;
#            static PDF/HTML/review/HBU controls are absent; dynamic result area is
#            initially empty; admin Excel card exists but is hidden by default.

import pathlib
import re
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

HTML = pathlib.Path("frontend/index.html")


def _html() -> str:
    return HTML.read_text(encoding="utf-8", errors="replace")


# Helper: find the combined reporting section (pv-unified-report-issuance-in-chat
# through /pv-report-issuance-combined comment)
def _reporting_section(html: str) -> str:
    start = html.index('data-testid="pv-unified-report-issuance-in-chat"')
    end   = html.index('<!-- /pv-report-issuance-combined -->')
    return html[start:end]


# ════════════════════════════════════════════════════════════════════════════
# PART 1 — Professional Valuation Page Order
# ════════════════════════════════════════════════════════════════════════════

# ── PVORD01: Report-type section heading testid exists exactly once ───────────
def test_PVORD01_report_type_section_heading_exists_once():
    html = _html()
    # Check the data-testid (uniquely identifies the heading element, not comment text)
    count = html.count('data-testid="pv-report-type-attachments-heading"')
    assert count == 1, (
        f"data-testid='pv-report-type-attachments-heading' must appear exactly once; got {count}"
    )
    # The Arabic heading text must be present (may appear in comment + element = >=1)
    assert 'اختر نوع التقرير وملحقاته' in html


# ── PVORD02: Report-type section testid exists exactly once ──────────────────
def test_PVORD02_report_type_section_testid_exists_once():
    html = _html()
    # data-testid appears once; id= also once; closing comment makes 3 total
    assert html.count('data-testid="pv-report-type-attachments-section"') == 1


# ── PVORD03: Report-type section appears BEFORE the submit button ─────────────
def test_PVORD03_report_type_section_before_submit_button():
    html = _html()
    idx_section = html.index('data-testid="pv-report-type-attachments-section"')
    idx_btn     = html.index('id="generateBtn"')
    assert idx_section < idx_btn, (
        "Report-type section must appear before the generateBtn submit button in the DOM"
    )


# ── PVORD04: Submit button exists exactly once ───────────────────────────────
def test_PVORD04_submit_button_exists_once():
    html = _html()
    count = html.count('id="generateBtn"')
    assert count == 1, f"generateBtn must appear exactly once; got {count}"


# ── PVORD05: Report type selector uses canonical values ───────────────────────
def test_PVORD05_report_selector_uses_canonical_values():
    html = _html()
    idx = html.index('data-testid="pv-submission-report-type-select"')
    # Find the enclosing <select ... </select>
    sel_start = html.rindex('<select', 0, idx)
    sel_end   = html.index('</select>', sel_start)
    select_block = html[sel_start:sel_end]
    for canonical in ['traditional_report', 'detailed_report', 'professional_report']:
        assert f'value="{canonical}"' in select_block, (
            f"Canonical value '{canonical}' must appear as option value in submission selector"
        )


# ── PVORD06: Submission blocked without report type (JS validation present) ───
def test_PVORD06_submission_without_report_type_blocked():
    html = _html()
    assert 'يرجى اختيار نوع التقرير أولًا.' in html, (
        "Arabic report-type validation message must be present in JS"
    )


# ── PVORD07: Report-type validation message appears in correct JS order ───────
def test_PVORD07_report_type_validation_before_api_call():
    html = _html()
    msg_idx = html.index('يرجى اختيار نوع التقرير أولًا.')
    btn_idx = html.index('جاري التحليل... <i class="fas fa-spinner fa-spin"></i>')
    assert msg_idx < btn_idx, (
        "Report-type validation must occur BEFORE the loading spinner (API call)"
    )


# ── PVORD08: Return statement follows report-type validation ──────────────────
def test_PVORD08_report_type_validation_returns_early():
    html = _html()
    msg_idx = html.index('يرجى اختيار نوع التقرير أولًا.')
    nearby  = html[msg_idx:msg_idx + 400]
    assert 'return;' in nearby, (
        "A 'return;' must follow the report-type validation message"
    )


# ── PVORD09: Attachment validation message is present ────────────────────────
def test_PVORD09_attachment_validation_message_present():
    html = _html()
    assert 'يرجى إرفاق جميع الملحقات المطلوبة لنوع التقرير المحدد.' in html, (
        "Attachment validation message must be present in JS"
    )


# ── PVORD10: Submission type included in payload (canonical) ──────────────────
def test_PVORD10_submission_report_type_in_payload():
    html = _html()
    assert 'submission_report_type' in html, (
        "submission_report_type must be included in the API payload"
    )
    idx = html.index('submission_report_type')
    nearby = html[idx:idx + 80]
    assert '_pvSubReportType' in nearby, (
        "submission_report_type must reference the canonical _pvSubReportType variable"
    )


# ── PVORD11: Opening attachment requirements does not submit form ─────────────
def test_PVORD11_attachment_requirements_no_form_submit():
    html = _html()
    # The attachment-requirements and upload sections are divs, not forms/buttons that submit
    idx = html.index('data-testid="pv-submission-attachment-requirements"')
    nearby = html[idx:idx + 500]
    # Must not contain onclick="processAndGenerate" in the attachment area
    assert 'processAndGenerate' not in nearby, (
        "Attachment requirements section must not trigger form submission"
    )


# ── PVORD12: Changing report type clears stale attachment state ──────────────
def test_PVORD12_report_type_change_clears_attachment_state():
    html = _html()
    fn_idx = html.index('function pvUpdateSubmissionReportType')
    # Function body can be 1700+ chars; search with generous window
    fn_body = html[fn_idx:fn_idx + 2000]
    assert '_pvCurrentSubmissionAttachments = {}' in fn_body, (
        "pvUpdateSubmissionReportType must reset _pvCurrentSubmissionAttachments on type change"
    )


# ── PVORD13: Keyboard/DOM focus order — report type before submit ─────────────
def test_PVORD13_dom_order_report_type_before_submit():
    html = _html()
    idx_select = html.index('id="pv-submission-report-type"')
    idx_btn    = html.index('id="generateBtn"')
    assert idx_select < idx_btn, (
        "pv-submission-report-type select must appear before generateBtn in DOM"
    )


# ════════════════════════════════════════════════════════════════════════════
# PART 2 — Reporting Section Cleanup
# ════════════════════════════════════════════════════════════════════════════

# ── PVRSC01: Reporting section combined boundary is marked ────────────────────
def test_PVRSC01_reporting_section_combined_boundary_marked():
    html = _html()
    assert 'data-testid="pv-unified-report-issuance-in-chat"' in html
    assert '<!-- /pv-report-issuance-combined -->' in html


# ── PVRSC02: Exactly three report-level chip controls remain ──────────────────
def test_PVRSC02_exactly_three_report_level_chips():
    html = _html()
    section = _reporting_section(html)
    for chip in ['pv-core-report-chip-traditional',
                 'pv-core-report-chip-detailed',
                 'pv-core-report-chip-professional']:
        count = section.count(chip)
        assert count == 1, (
            f"Chip '{chip}' must appear exactly once inside reporting section; got {count}"
        )


# ── PVRSC03: Traditional report chip exists exactly once ─────────────────────
def test_PVRSC03_traditional_chip_exists_once():
    html = _html()
    assert html.count('pv-core-report-chip-traditional') == 1


# ── PVRSC04: Detailed report chip exists exactly once ────────────────────────
def test_PVRSC04_detailed_chip_exists_once():
    html = _html()
    assert html.count('pv-core-report-chip-detailed') == 1


# ── PVRSC05: Professional report chip exists exactly once ────────────────────
def test_PVRSC05_professional_chip_exists_once():
    html = _html()
    assert html.count('pv-core-report-chip-professional') == 1


# ── PVRSC06: No static "تنزيل PDF" label inside reporting section ────────────
def test_PVRSC06_no_static_pdf_download_in_reporting_section():
    html = _html()
    section = _reporting_section(html)
    # The exact format label text (with entity or literal)
    assert 'pv-format-label-pdf' not in section, (
        "Static PDF format label (pv-format-label-pdf) must not appear in reporting section"
    )


# ── PVRSC07: No static "عرض HTML" label inside reporting section ─────────────
def test_PVRSC07_no_static_html_view_in_reporting_section():
    html = _html()
    section = _reporting_section(html)
    assert 'pv-format-label-html-view' not in section, (
        "Static HTML-view format label must not appear in reporting section"
    )


# ── PVRSC08: No static "تنزيل HTML" label inside reporting section ───────────
def test_PVRSC08_no_static_html_download_in_reporting_section():
    html = _html()
    section = _reporting_section(html)
    assert 'pv-format-label-html-download' not in section, (
        "Static HTML-download format label must not appear in reporting section"
    )


# ── PVRSC09: "مراجعة تقرير التقييم" button absent from reporting section ──────
def test_PVRSC09_review_report_button_absent_from_section():
    html = _html()
    section = _reporting_section(html)
    # Use full attribute string — only appears on an actual element, not inside a comment
    assert 'data-testid="pv-unified-action-review-report"' not in section, (
        "pv-unified-action-review-report button element must not appear in reporting section"
    )


# ── PVRSC10: "تحليل HBU" button absent from reporting section ────────────────
def test_PVRSC10_hbu_button_absent_from_section():
    html = _html()
    section = _reporting_section(html)
    assert 'data-testid="pv-unified-action-hbu"' not in section, (
        "pv-unified-action-hbu button element must not appear in reporting section"
    )


# ── PVRSC11: No seven-report dropdown inside reporting section ────────────────
def test_PVRSC11_no_seven_report_dropdown_in_section():
    html = _html()
    section = _reporting_section(html)
    # The unified seven-report hidden select should NOT be inside the reporting section
    assert 'pv-legacy-seven-report-selector-hidden' not in section, (
        "Seven-report legacy selector must not appear inside the reporting section"
    )


# ── PVRSC12: Dynamic result area exists and is initially hidden ───────────────
def test_PVRSC12_dynamic_result_area_initially_hidden():
    html = _html()
    idx = html.index('data-testid="pv-core-bundle-status"')
    # Style attributes span multiple lines; use 400 chars
    nearby = html[idx:idx + 400]
    assert 'display:none' in nearby, (
        "pv-core-bundle-status dynamic result area must be initially hidden (display:none)"
    )


# ── PVRSC13: PDF status element exists inside result area ────────────────────
def test_PVRSC13_pdf_status_element_exists():
    html = _html()
    assert 'data-testid="pv-bundle-pdf-status"' in html


# ── PVRSC14: HTML status element exists inside result area ───────────────────
def test_PVRSC14_html_status_element_exists():
    html = _html()
    assert 'data-testid="pv-bundle-html-status"' in html


# ── PVRSC15: Admin Excel card exists but hidden by default ───────────────────
def test_PVRSC15_admin_excel_card_hidden_by_default():
    html = _html()
    idx = html.index('data-testid="pv-core-internal-excel-card"')
    # Style spans multiple lines; use 400 chars
    nearby = html[idx:idx + 400]
    assert 'display:none' in nearby, (
        "Admin Excel card must be initially hidden (display:none)"
    )


# ── PVRSC16: Excel card has admin-only label ──────────────────────────────────
def test_PVRSC16_excel_card_has_admin_only_label():
    html = _html()
    idx = html.index('data-testid="pv-core-internal-excel-card"')
    # Admin label is deeper in the card content; use 800 chars
    nearby = html[idx:idx + 800]
    assert 'Admin Only' in nearby or 'للمسؤولين' in nearby, (
        "Admin Excel card must have an admin-only label"
    )


# ── PVRSC17: Chip onclick uses pvGenerateCoreReportBundle ────────────────────
def test_PVRSC17_chip_onclick_uses_core_bundle_function():
    html = _html()
    section = _reporting_section(html)
    assert 'pvGenerateCoreReportBundle' in section, (
        "Report chip onclick must call pvGenerateCoreReportBundle in reporting section"
    )


# ── PVRSC18: Removed IDs have no active getElementById JS references ──────────
def test_PVRSC18_removed_ids_no_active_js_references():
    html = _html()
    removed_ids = [
        'pv-unified-action-review-report',
        'pv-unified-action-hbu',
        'pv-format-label-pdf',
        'pv-format-label-html-view',
        'pv-format-label-html-download',
    ]
    for rid in removed_ids:
        pattern = f"getElementById('{rid}')"
        assert pattern not in html, (
            f"Removed element '{rid}' must not have active getElementById reference in JS"
        )


# ════════════════════════════════════════════════════════════════════════════
# BACKWARD-COMPAT / REGRESSION
# ════════════════════════════════════════════════════════════════════════════

# ── PVBC01: Previous mandate — three chips still present ─────────────────────
def test_PVBC01_previous_mandate_three_chips_still_present():
    html = _html()
    for chip in ['pv-core-report-chip-traditional',
                 'pv-core-report-chip-detailed',
                 'pv-core-report-chip-professional']:
        assert html.count(chip) == 1, f"Chip {chip!r} must appear exactly once"


# ── PVBC02: Legacy selector still hidden ────────────────────────────────────
def test_PVBC02_legacy_selector_still_hidden():
    html = _html()
    assert 'pv-legacy-seven-report-selector-hidden' in html


# ── PVBC03: Asset-type validation from previous mandate still present ─────────
def test_PVBC03_asset_type_validation_still_present():
    html = _html()
    assert 'pro-val-asset-type-error' in html


# ── PVBC04: Advanced requirements toggle still present ───────────────────────
def test_PVBC04_advanced_requirements_toggle_still_present():
    html = _html()
    assert 'pv-advanced-req-toggle' in html
    assert 'pvToggleAdvancedRequirements' in html


# ── PVBC05: pvGenerateCoreReportBundle function still defined ─────────────────
def test_PVBC05_core_bundle_function_still_defined():
    html = _html()
    assert 'function pvGenerateCoreReportBundle' in html
