# test_reporting_ui_deduplication_chat_layout.py
# Permanent tests — Reporting UI Deduplication and Chat Layout Merge
# advisory_only=True | not_real_training=True | no_commit=True
#
# Mandate: REPORTING_UI_DUPLICATION_AND_CHAT_LAYOUT_MERGE_APPROVED
# Verifies: merged sections, DOM positions, format labels, role-based Excel,
#            action routing, backward-compat spans, no duplicate buttons.

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

HTML = pathlib.Path("frontend/index.html")


def _ctx():
    from core_engine.reporting_ui_deduplication_chat_layout_context import (
        get_reporting_ui_deduplication_chat_layout_context,
    )
    return get_reporting_ui_deduplication_chat_layout_context()


def _html() -> str:
    return HTML.read_text(encoding="utf-8", errors="replace")


# ── T01: Context module importable and returns dict ────────────────────────────
def test_T01_context_module_importable():
    ctx = _ctx()
    assert isinstance(ctx, dict)
    assert len(ctx) > 10


# ── T02: New unified heading appears exactly once ──────────────────────────────
def test_T02_unified_heading_exactly_once():
    html = _html()
    heading = _ctx()["main_unified_section_heading"]
    assert html.count(heading) == 1, (
        f"Expected 1 occurrence of '{heading}', got {html.count(heading)}"
    )


# ── T03: Old main-section heading removed ─────────────────────────────────────
def test_T03_old_main_heading_absent():
    html = _html()
    old = _ctx()["old_heading_removed"]
    assert old not in html, f"Old heading still present: {old}"


# ── T04: Old duplicate section 'محتوى التقرير' absent ─────────────────────────
def test_T04_old_content_section_absent():
    html = _html()
    assert "محتوى التقرير: تحليل وإصدار التقارير" not in html


# ── T05: Advanced-section heading appears exactly once ────────────────────────
def test_T05_advanced_section_heading_exactly_once():
    html = _html()
    heading = _ctx()["advanced_section_heading"]
    assert html.count(heading) == 1, (
        f"Expected 1 occurrence of '{heading}', got {html.count(heading)}"
    )


# ── T06: No standalone simulation section card in HTML ────────────────────────
def test_T06_no_standalone_simulation_section():
    # Old standalone card had testid "pro-val-simulation-report-section" (removed).
    # The simulation functionality lives inside the advanced section only.
    html = _html()
    assert "pro-val-simulation-report-section" not in html


# ── T07: Static format labels removed (cleanup mandate) ──────────────────────
# PROFESSIONAL_VALUATION_REPORT_TYPE_ORDER_AND_REPORTING_SECTION_CLEANUP removed
# the pv-unified-format-labels block; format label testids no longer in static HTML.
def test_T07_static_format_labels_removed():
    html = _html()
    ctx = _ctx()
    for testid in (
        ctx["user_format_pdf_testid"],
        ctx["user_format_html_view_testid"],
        ctx["user_format_html_download_testid"],
    ):
        assert testid not in html, f"Format label testid must be absent: {testid}"


# ── T08: In-chat review and HBU buttons removed (cleanup mandate) ─────────────
# PROFESSIONAL_VALUATION_REPORT_TYPE_ORDER_AND_REPORTING_SECTION_CLEANUP removed
# pv-unified-action-review-report and pv-unified-action-hbu from the section.
def test_T08_in_chat_action_buttons_removed():
    html = _html()
    ctx = _ctx()
    assert f'data-testid="{ctx["review_action_testid"]}"' not in html
    assert f'data-testid="{ctx["hbu_action_testid"]}"'    not in html


# ── T09: Unified section DOM position inside chat container ──────────────────
def test_T09_unified_section_inside_chat_container():
    html = _html()
    chat_open  = html.index('data-testid="pro-val-chat-command-center"')
    chat_close = html.index(
        "<!-- /pro-val-chat-command-center ai-section — extended to include unified report issuance -->"
    )
    unified    = html.index('data-testid="pv-unified-report-issuance-in-chat"')
    assert chat_open < unified < chat_close, (
        "pv-unified-report-issuance-in-chat must be inside the chat container; "
        f"chat_open={chat_open}, unified={unified}, chat_close={chat_close}"
    )


# ── T10: Advanced section DOM position outside chat container ─────────────────
def test_T10_advanced_section_outside_chat_container():
    html = _html()
    chat_close = html.index(
        "<!-- /pro-val-chat-command-center ai-section — extended to include unified report issuance -->"
    )
    advanced   = html.index('data-testid="pv-special-report-workflows"')
    assert advanced > chat_close, (
        "pv-special-report-workflows must be OUTSIDE the chat container; "
        f"chat_close={chat_close}, advanced={advanced}"
    )


# ── T11: Core report issuance section inside chat container ──────────────────
def test_T11_core_report_issuance_inside_chat_container():
    html = _html()
    chat_open  = html.index('data-testid="pro-val-chat-command-center"')
    chat_close = html.index(
        "<!-- /pro-val-chat-command-center ai-section — extended to include unified report issuance -->"
    )
    area1 = html.index('data-testid="pv-core-valuation-report-issuance"')
    assert chat_open < area1 < chat_close, (
        "pv-core-valuation-report-issuance must be inside the chat container"
    )


# ── T12: Normal user — Excel button initially hidden ─────────────────────────
def test_T12_normal_user_excel_hidden_by_default():
    html = _html()
    # The admin Excel button has display:none in the static HTML.
    # JS reveals it only after confirming is_admin === true.
    admin_testid = _ctx()["admin_excel_testid"]
    assert admin_testid in html, "Admin Excel button missing from HTML"
    # Verify the button element carries display:none at its definition
    idx = html.index(admin_testid)
    # The id attribute is on the very next line after the testid; the style with
    # display:none appears within 300 characters of the testid.
    nearby = html[idx: idx + 400]
    assert "display:none" in nearby, (
        "Admin Excel button must start with display:none (hidden from normal users)"
    )


# ── T13: Admin — Excel button present for JS to reveal ───────────────────────
def test_T13_admin_excel_button_exists_for_js():
    html = _html()
    ctx = _ctx()
    assert ctx["admin_excel_testid"] in html
    assert "pvGenerateUnifiedAdminExcel" in html
    assert "pv-admin-excel-btn"          in html


# ── T14: File upload control appears at most once ────────────────────────────
def test_T14_file_upload_control_at_most_once():
    html = _html()
    testid = _ctx()["file_upload_control_testid"]
    # Count via data-testid= to avoid double-counting id= on the same element
    marker = f'data-testid="{testid}"'
    count = html.count(marker)
    assert count <= _ctx()["file_upload_control_count_max"], (
        f"File upload control '{testid}' appears {count} times — expected ≤ 1"
    )


# ── T15: Review-report button element absent from HTML (cleanup mandate) ──────
# PROFESSIONAL_VALUATION_REPORT_TYPE_ORDER_AND_REPORTING_SECTION_CLEANUP removed
# pv-unified-action-review-report; the routing check is no longer applicable.
def test_T15_review_action_button_element_removed():
    html = _html()
    ctx = _ctx()
    assert f'data-testid="{ctx["review_action_testid"]}"' not in html, (
        "pv-unified-action-review-report element must be absent from HTML"
    )


# ── T16: HBU button element absent from HTML (cleanup mandate) ────────────────
# PROFESSIONAL_VALUATION_REPORT_TYPE_ORDER_AND_REPORTING_SECTION_CLEANUP removed
# pv-unified-action-hbu; the routing check is no longer applicable.
def test_T16_hbu_action_button_element_removed():
    html = _html()
    ctx = _ctx()
    assert f'data-testid="{ctx["hbu_action_testid"]}"' not in html, (
        "pv-unified-action-hbu element must be absent from HTML"
    )


# ── T17: Each core report chip testid appears exactly once ───────────────────
def test_T17_no_duplicate_core_report_chips():
    html = _html()
    for testid in _ctx()["core_report_chips_testids"]:
        count = html.count(testid)
        assert count == 1, (
            f"Core report chip '{testid}' appears {count} times — expected exactly 1"
        )


# ── T18: Backward-compat spans preserved for JS callers ─────────────────────
def test_T18_backward_compat_spans_present():
    html = _html()
    ctx = _ctx()
    for testid in (
        ctx["simulation_clip_span_testid"],
        "pro-val-report-review-toggle",
        "pro-val-hbu-report-toggle",
    ):
        assert testid in html, f"Backward-compat span missing: {testid}"
        idx = html.index(testid)
        nearby = html[idx: idx + 200]
        assert "aria-hidden" in nearby, f"Span {testid} must have aria-hidden"


# ── T19: PDF/HTML status containers present for API-URL output ───────────────
def test_T19_bundle_status_containers_present():
    html = _html()
    for testid in ("pv-bundle-pdf-status", "pv-bundle-html-status"):
        assert testid in html, f"Bundle status container missing: {testid}"


# ── T20: pvGenerateCoreReportBundle function defined in HTML ─────────────────
def test_T20_generate_bundle_function_defined():
    html = _html()
    assert "pvGenerateCoreReportBundle" in html


# ── T21: Advisory and safety flags set correctly ────────────────────────────
def test_T21_advisory_and_safety_flags():
    ctx = _ctx()
    assert ctx["advisory_only"]                          is True
    assert ctx["report_calculations_unmodified"]         is True
    assert ctx["backend_role_rules_unmodified"]          is True
    assert ctx["download_security_unmodified"]           is True
    assert ctx["pdf_generation_capability_preserved"]    is True
    assert ctx["html_generation_capability_preserved"]   is True
    assert ctx["admin_excel_generation_capability_preserved"] is True
    assert ctx["existing_report_actions_preserved"]      is True
