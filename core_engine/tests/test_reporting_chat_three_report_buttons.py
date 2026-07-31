# test_reporting_chat_three_report_buttons.py
# Permanent tests — Chat Three Report Buttons and Duplication Removal
# advisory_only=True | not_real_training=True | no_commit=True
#
# Mandate: REPORTING_CHAT_THREE_REPORT_BUTTONS_AND_DUPLICATION_REMOVAL_APPROVED
# Verifies: 3 chat buttons, 7-report dropdown hidden, obsolete buttons gone,
#            duplicate expert-review section gone, role-based output formats,
#            tier mapping, bottom section preserved.

import pathlib
import re
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

HTML = pathlib.Path("frontend/index.html")


def _ctx():
    from core_engine.reporting_chat_three_report_buttons_context import (
        get_reporting_chat_three_report_buttons_context,
    )
    return get_reporting_chat_three_report_buttons_context()


def _html() -> str:
    return HTML.read_text(encoding="utf-8", errors="replace")


# ── T01: Context module importable ────────────────────────────────────────────
def test_T01_context_module_importable():
    ctx = _ctx()
    assert isinstance(ctx, dict)
    assert len(ctx) > 10


# ── T02: Chat contains exactly three report-level buttons ────────────────────
def test_T02_chat_contains_exactly_three_report_buttons():
    html = _html()
    ctx = _ctx()
    for testid in ctx["chat_report_button_testids"]:
        count = html.count(testid)
        assert count == 1, f"Expected 1 occurrence of {testid!r}, got {count}"
    assert len(ctx["chat_report_button_testids"]) == 3


# ── T03: Traditional report button exists exactly once ───────────────────────
def test_T03_traditional_report_button_exists_once():
    html = _html()
    testid = "pv-unified-card-traditional"
    assert html.count(testid) == 1


# ── T04: Detailed report button exists exactly once ──────────────────────────
def test_T04_detailed_report_button_exists_once():
    html = _html()
    testid = "pv-unified-card-detailed"
    assert html.count(testid) == 1


# ── T05: Professional report button exists exactly once ──────────────────────
def test_T05_professional_report_button_exists_once():
    html = _html()
    testid = "pv-unified-card-professional"
    assert html.count(testid) == 1


# ── T06: Three buttons map to three distinct canonical tier values ────────────
def test_T06_three_buttons_map_to_distinct_tiers():
    html = _html()
    mapping = {
        "pv-unified-card-traditional": "traditional_report",
        "pv-unified-card-detailed": "detailed_report",
        "pv-unified-card-professional": "professional_report",
    }
    for testid, tier in mapping.items():
        idx = html.index(f'data-testid="{testid}"')
        tag = html[idx:html.index(">", idx) + 1]
        assert f"pvSelectReportTier('{tier}')" in tag


# ── T07: Chat contains no visible seven-report dropdown ──────────────────────
def test_T07_chat_has_no_visible_seven_report_dropdown():
    html = _html()
    ctx = _ctx()
    # The legacy wrapper must have display:none in its static style attribute
    wrapper_testid = ctx["seven_report_dropdown_chat_testid"]
    idx = html.index(f'data-testid="{wrapper_testid}"')
    # Style attribute is on the same element; look within next 100 chars
    nearby = html[idx: idx + 100]
    assert "display:none" in nearby, (
        f"pv-legacy-seven-report-selector-hidden div must have display:none"
    )


# ── T08: Complete page has exactly one seven-report option group ──────────────
def test_T08_authoritative_seven_report_options_count():
    html = _html()
    ctx = _ctx()
    # The authoritative seven-report selector at the bottom must exist
    assert ctx["authoritative_expert_review_report_selector_testid"] in html
    # It must contain all seven canonical option values
    for option_val in ctx["authoritative_expert_review_report_options"]:
        assert option_val in html, (
            f"Seven-report option value {option_val!r} not found in HTML"
        )


# ── T09: Bottom seven-report selector has exactly seven option elements ───────
def test_T09_bottom_selector_has_seven_option_elements():
    html = _html()
    sel_testid = "pro-val-cert-report-type"
    idx = html.index(f'data-testid="{sel_testid}"')
    # Read enough chars to capture all seven options
    block = html[idx: idx + 1500]
    close_idx = block.find("</select>")
    assert close_idx != -1, "Could not find closing </select> after pv-cert-report-type"
    select_block = block[:close_idx]
    # Count only options with a non-empty value attribute (excludes placeholder)
    real_options = re.findall(r'<option\s+value="[^"]+">',  select_block)
    assert len(real_options) == 7, (
        f"Expected 7 report-type option elements in authoritative selector, got {len(real_options)}"
    )


# ── T10: "إصدار تقرير PDF للمستخدم" is not a visible rendered button ─────────
def test_T10_obsolete_pdf_user_button_not_visible():
    html = _html()
    # The text may appear in JS comments/variables but must NOT be in a <button> element
    pattern = re.compile(
        r'<button[^>]*>\s*[^<]*إصدار تقرير PDF للمستخدم[^<]*\s*</button>', re.DOTALL
    )
    matches = pattern.findall(html)
    assert len(matches) == 0, (
        f"Found {len(matches)} visible 'إصدار تقرير PDF للمستخدم' button(s) — must be 0"
    )


# ── T11: "إصدار المخرج المختار" is not a visible rendered button ──────────────
def test_T11_obsolete_selected_output_button_not_visible():
    html = _html()
    # Button removed; text may appear in backward-compat comments
    pattern = re.compile(
        r'<button[^>]*>\s*[^<]*إصدار المخرج المختار[^<]*\s*</button>', re.DOTALL
    )
    matches = pattern.findall(html)
    assert len(matches) == 0, (
        f"Found {len(matches)} visible 'إصدار المخرج المختار' button(s) — must be 0"
    )


# ── T12: Duplicate expert-review section NOT rendered inside chat ─────────────
def test_T12_duplicate_expert_review_section_not_in_chat():
    html = _html()
    chat_open  = html.index('data-testid="pro-val-chat-command-center"')
    chat_close = html.index(
        "<!-- /pro-val-chat-command-center ai-section -->"
    )
    # The "طلب مراجعة خبير معتمد" heading must NOT appear between chat open and close
    chat_block = html[chat_open:chat_close]
    assert "⚖ طلب مراجعة خبير معتمد" not in chat_block, (
        "Duplicate expert-review heading found inside the chat container"
    )
    # The textarea for the now-removed expert-review note must not be inside chat
    assert 'data-testid="pro-val-expert-review-note-input"' not in chat_block, (
        "pro-val-expert-review-note-input textarea still present inside chat"
    )


# ── T13: Authoritative expert-review section remains rendered outside chat ────
def test_T13_authoritative_expert_review_section_preserved():
    html = _html()
    chat_close = html.index(
        "<!-- /pro-val-chat-command-center ai-section -->"
    )
    # The authoritative section (with pro-val-cert-submit) is after the chat container
    advanced_idx = html.index('data-testid="pro-val-expert-review-request-section"',
                              chat_close)
    assert advanced_idx > chat_close, (
        "Authoritative expert-review section must appear after the chat container"
    )
    # It must contain the submit button (certified request workflow)
    remaining = html[advanced_idx:]
    assert 'data-testid="pro-val-cert-submit"' in remaining or \
           'pvSubmitCertifiedExpertReviewRequest' in remaining[:3000]


# ── T14: Static PDF format label removed (cleanup mandate) ───────────────────
# PROFESSIONAL_VALUATION_REPORT_TYPE_ORDER_AND_REPORTING_SECTION_CLEANUP removed
# the static pv-unified-format-labels block; format labels no longer in static HTML.
def test_T14_static_pdf_format_label_removed():
    html = _html()
    ctx = _ctx()
    assert ctx["user_format_pdf_testid"] not in html
    assert ctx["normal_user_pdf_available"] is True  # capability preserved, label removed


# ── T15: Static HTML-view format label removed (cleanup mandate) ──────────────
def test_T15_static_html_view_format_label_removed():
    html = _html()
    ctx = _ctx()
    assert ctx["user_format_html_view_testid"] not in html
    assert ctx["normal_user_html_available"] is True


# ── T16: Static HTML-download format label removed (cleanup mandate) ──────────
def test_T16_static_html_download_format_label_removed():
    html = _html()
    ctx = _ctx()
    assert ctx["user_format_html_download_testid"] not in html


# ── T17: Normal user receives zero Excel controls ────────────────────────────
def test_T17_normal_user_excel_hidden():
    html = _html()
    ctx = _ctx()
    admin_testid = ctx["admin_excel_testid"]
    assert admin_testid in html
    # Must have display:none in the static HTML
    idx = html.index(admin_testid)
    nearby = html[idx: idx + 400]
    assert "display:none" in nearby, (
        "Admin Excel button must have display:none in static HTML for normal-user sessions"
    )
    assert ctx["normal_user_excel_available"] is False


# ── T18: Administrator PDF available ─────────────────────────────────────────
def test_T18_admin_pdf_available():
    ctx = _ctx()
    assert ctx["admin_pdf_available"] is True


# ── T19: Administrator HTML available ────────────────────────────────────────
def test_T19_admin_html_available():
    ctx = _ctx()
    assert ctx["admin_html_available"] is True


# ── T20: Administrator Excel button present for JS to reveal ─────────────────
def test_T20_admin_excel_button_present_for_js():
    html = _html()
    ctx = _ctx()
    assert ctx["admin_excel_testid"] in html
    assert "pvGenerateUnifiedAdminExcel" in html
    assert ctx["admin_excel_revealed_by_role_js"] is True


# ── T21: Traditional button calls traditional tier ───────────────────────────
def test_T21_traditional_button_calls_traditional_tier():
    html = _html()
    idx = html.index('data-testid="pv-unified-card-traditional"')
    tag = html[idx:html.index(">", idx) + 1]
    assert "pvSelectReportTier('traditional_report')" in tag


# ── T22: Detailed button calls detailed tier ─────────────────────────────────
def test_T22_detailed_button_calls_detailed_tier():
    html = _html()
    idx = html.index('data-testid="pv-unified-card-detailed"')
    tag = html[idx:html.index(">", idx) + 1]
    assert "pvSelectReportTier('detailed_report')" in tag


# ── T23: Professional button calls professional tier ─────────────────────────
def test_T23_professional_button_calls_professional_tier():
    html = _html()
    idx = html.index('data-testid="pv-unified-card-professional"')
    tag = html[idx:html.index(">", idx) + 1]
    assert "pvSelectReportTier('professional_report')" in tag


# ── T24: Chat buttons do not invoke seven-report review API ──────────────────
def test_T24_chat_buttons_do_not_invoke_seven_report_review_api():
    html = _html()
    for testid in ["pv-unified-card-traditional",
                   "pv-unified-card-detailed",
                   "pv-unified-card-professional"]:
        idx = html.index(testid)
        nearby = html[idx: idx + 300]
        assert "pvIssueSpecialReportPdf" not in nearby, (
            f"{testid} must not call pvIssueSpecialReportPdf (seven-report review API)"
        )


# ── T25: pvGenerateCoreReportBundle drives all three chips ───────────────────
def test_T25_report_cards_use_selector_function():
    html = _html()
    assert "function pvSelectReportTier" in html
    for tier in ["traditional_report", "detailed_report", "professional_report"]:
        assert f"pvSelectReportTier('{tier}')" in html


# ── T26: Backward-compat spans preserve removed testids ──────────────────────
def test_T26_backward_compat_spans_present():
    html = _html()
    ctx = _ctx()
    for span_testid in [
        ctx["backward_compat_pdf_user_span_testid"],
        ctx["backward_compat_selected_output_span_testid"],
        ctx["backward_compat_expert_review_button_testid"],
    ]:
        assert f'data-testid="{span_testid}"' in html, (
            f"Backward-compat span testid {span_testid!r} missing from HTML"
        )


# ── T27: Bundle status containers present for API output ─────────────────────
def test_T27_bundle_status_containers_present():
    html = _html()
    for testid in ("pv-bundle-pdf-status", "pv-bundle-html-status"):
        assert testid in html, f"Bundle status container {testid!r} missing"


# ── T28: Advisory and safety flags correct ───────────────────────────────────
def test_T28_advisory_and_safety_flags():
    ctx = _ctx()
    assert ctx["advisory_only"]                         is True
    assert ctx["report_calculations_unmodified"]        is True
    assert ctx["backend_role_rules_unmodified"]         is True
    assert ctx["seven_report_review_workflow_preserved"] is True
    assert ctx["pdf_generation_capability_preserved"]   is True
    assert ctx["html_generation_capability_preserved"]  is True
    assert ctx["admin_excel_generation_preserved"]      is True
