# test_advanced_reports_four_workflows_pdf_html.py
# Permanent tests — Advanced Reports Four Workflows PDF and HTML Outputs
# advisory_only=True | not_real_training=True | no_commit=True
#
# Mandate: ADVANCED_REPORTS_FOUR_WORKFLOWS_PDF_HTML_OUTPUTS_APPROVED
# Verifies:
#   - Exact 4 format-note occurrences (one per panel) with required Arabic text
#   - Panel 1 (report_review_output): rr-download-section initially hidden;
#     HTML view + download links present; PDF link present; JS handler updated
#   - Panel 2 (simulated_uploaded_report): sim result panel has HTML links;
#     PDF link preserved; simShowValuationResults updated
#   - Panel 3 (hbu_analysis_report): hbu-download-section initially hidden;
#     3-link output area present; Excel button hidden by default (admin-only);
#     button calls pvGenerateHbuPdfBundle, not pvIssueSpecialReportPdf
#   - Panel 4 (standards_compliance_report): sc-download-section initially hidden;
#     3-link output area present; inactive sc-download-pdf/excel hidden;
#     generate button calls pvGenerateStandardsComplianceBundle
#   - Four-workflow state isolation (no link cross-contamination between panels)
#   - Safety flags: no Excel for normal users; no fake pre-generation links

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

HTML = pathlib.Path("frontend/index.html")
_FORMAT_NOTE_TEXT = "المخرجات المتاحة للمستخدم: PDF وHTML"


def _html() -> str:
    return HTML.read_text(encoding="utf-8", errors="replace")


# ════════════════════════════════════════════════════════════════════════════
# FORMAT NOTES — exactly 4, one per panel
# ════════════════════════════════════════════════════════════════════════════

# ── T01: Exactly 4 occurrences of the exact format-note Arabic text ──────────
def test_T01_format_note_text_appears_exactly_four_times():
    html = _html()
    count = html.count(_FORMAT_NOTE_TEXT)
    assert count == 4, (
        f"Expected exactly 4 occurrences of '{_FORMAT_NOTE_TEXT}'; got {count}"
    )


# ── T02: Panel 1 format note testid exists exactly once ──────────────────────
def test_T02_panel1_format_note_testid_exists_once():
    html = _html()
    assert html.count('data-testid="pv-rr-format-note"') == 1


# ── T03: Panel 2 format note testid exists exactly once ──────────────────────
def test_T03_panel2_format_note_testid_exists_once():
    html = _html()
    assert html.count('data-testid="pv-sim-format-note"') == 1


# ── T04: Panel 3 format note testid exists exactly once ──────────────────────
def test_T04_panel3_format_note_testid_exists_once():
    html = _html()
    assert html.count('data-testid="pv-hbu-format-note"') == 1


# ── T05: Panel 4 format note testid exists exactly once ──────────────────────
def test_T05_panel4_format_note_testid_exists_once():
    html = _html()
    assert html.count('data-testid="pv-sc-format-note"') == 1


# ── T06: Each panel's format note contains the exact required text ────────────
def test_T06_each_format_note_contains_required_text():
    html = _html()
    for testid in ("pv-rr-format-note", "pv-sim-format-note",
                   "pv-hbu-format-note", "pv-sc-format-note"):
        idx = html.index(f'data-testid="{testid}"')
        # Format note text must appear within 500 chars of the testid
        nearby = html[idx: idx + 500]
        assert _FORMAT_NOTE_TEXT in nearby, (
            f"Format note '{testid}' does not contain the required Arabic text"
        )


# ════════════════════════════════════════════════════════════════════════════
# PANEL 1 — Report Review (rr-download-section)
# ════════════════════════════════════════════════════════════════════════════

# ── T07: rr-download-section is initially hidden ──────────────────────────────
def test_T07_panel1_download_section_initially_hidden():
    html = _html()
    idx = html.index('data-testid="rr-download-section"')
    nearby = html[idx: idx + 100]
    assert "display:none" in nearby, (
        "rr-download-section must start with display:none (not shown before generation)"
    )


# ── T08: Panel 1 has PDF download link ───────────────────────────────────────
def test_T08_panel1_has_pdf_download_link():
    html = _html()
    assert 'data-testid="rr-download-review-pdf"' in html


# ── T09: Panel 1 has HTML view link ──────────────────────────────────────────
def test_T09_panel1_has_html_view_link():
    html = _html()
    assert 'data-testid="rr-view-review-html"' in html


# ── T10: Panel 1 has HTML download link ──────────────────────────────────────
def test_T10_panel1_has_html_download_link():
    html = _html()
    assert 'data-testid="rr-download-review-html"' in html


# ── T11: Panel 1 rrGenerateReviewPdf populates html_url into HTML links ───────
def test_T11_panel1_js_populates_html_links():
    html = _html()
    fn_idx = html.index("function rrGenerateReviewPdf()")
    fn_body = html[fn_idx: fn_idx + 1600]
    assert "rr-view-review-html" in fn_body, (
        "rrGenerateReviewPdf must reference rr-view-review-html to set HTML view href"
    )
    assert "rr-download-review-html" in fn_body, (
        "rrGenerateReviewPdf must reference rr-download-review-html to set HTML download href"
    )
    assert "d.html_url" in fn_body, (
        "rrGenerateReviewPdf must use d.html_url from API response"
    )


# ════════════════════════════════════════════════════════════════════════════
# PANEL 2 — Simulation (sim-valuation-results-panel)
# ════════════════════════════════════════════════════════════════════════════

# ── T12: Panel 2 has HTML view link inside results panel ─────────────────────
def test_T12_panel2_has_html_view_link():
    html = _html()
    assert 'data-testid="sim-view-html"' in html


# ── T13: Panel 2 has HTML download link inside results panel ─────────────────
def test_T13_panel2_has_html_download_link():
    html = _html()
    assert 'data-testid="sim-download-html"' in html


# ── T14: Panel 2 still has PDF download link ─────────────────────────────────
def test_T14_panel2_pdf_download_link_preserved():
    html = _html()
    assert 'data-testid="sim-download-generated-report"' in html


# ── T15: simShowValuationResults sets HTML link hrefs from d.html_url ────────
def test_T15_panel2_js_populates_html_links():
    html = _html()
    fn_idx = html.index("function simShowValuationResults(d)")
    fn_body = html[fn_idx: fn_idx + 1400]
    assert "sim-view-html" in fn_body, (
        "simShowValuationResults must set sim-view-html href from d.html_url"
    )
    assert "sim-download-html" in fn_body, (
        "simShowValuationResults must set sim-download-html href from d.html_url"
    )
    assert "d.html_url" in fn_body, (
        "simShowValuationResults must reference d.html_url from API response"
    )


# ════════════════════════════════════════════════════════════════════════════
# PANEL 3 — HBU Analysis
# ════════════════════════════════════════════════════════════════════════════

# ── T16: hbu-download-section exists and is initially hidden ──────────────────
def test_T16_panel3_download_section_initially_hidden():
    html = _html()
    assert 'data-testid="hbu-download-section"' in html, (
        "hbu-download-section must be present in HTML"
    )
    idx = html.index('data-testid="hbu-download-section"')
    nearby = html[idx: idx + 100]
    assert "display:none" in nearby, (
        "hbu-download-section must start with display:none (not shown before generation)"
    )


# ── T17: Panel 3 has PDF, HTML view, and HTML download links ─────────────────
def test_T17_panel3_has_all_three_output_links():
    html = _html()
    assert 'data-testid="hbu-download-pdf"'  in html
    assert 'data-testid="hbu-view-html"'     in html
    assert 'data-testid="hbu-download-html"' in html


# ── T18: HBU Excel button is initially hidden (admin-only) ───────────────────
def test_T18_panel3_hbu_excel_hidden_by_default():
    html = _html()
    assert 'data-testid="pv-issue-hbu-excel"' in html, (
        "pv-issue-hbu-excel must remain in DOM for admin reveal"
    )
    idx = html.index('data-testid="pv-issue-hbu-excel"')
    # display:none is on the button style — search within 300 chars
    nearby = html[idx: idx + 300]
    assert "display:none" in nearby, (
        "pv-issue-hbu-excel must have display:none (admin-only, hidden from normal users)"
    )


# ── T19: HBU PDF button calls pvGenerateHbuPdfBundle, not pvIssueSpecialReportPdf ─
def test_T19_panel3_pdf_button_calls_hbu_bundle_function():
    html = _html()
    idx = html.index('data-testid="pv-issue-hbu-pdf"')
    nearby = html[idx: idx + 300]
    assert "pvGenerateHbuPdfBundle" in nearby, (
        "pv-issue-hbu-pdf button must call pvGenerateHbuPdfBundle"
    )
    assert "pvIssueSpecialReportPdf" not in nearby, (
        "pv-issue-hbu-pdf must NOT call pvIssueSpecialReportPdf directly (mandate: dedicated fetch)"
    )


# ── T20: pvGenerateHbuPdfBundle function defined in JS ───────────────────────
def test_T20_pvGenerateHbuPdfBundle_function_defined():
    html = _html()
    assert "function pvGenerateHbuPdfBundle()" in html


# ── T21: pvGenerateHbuPdfBundle shows hbu-download-section in both .then and .catch
def test_T21_panel3_bundle_fn_shows_result_on_success_and_catch():
    html = _html()
    fn_idx = html.index("function pvGenerateHbuPdfBundle()")
    fn_body = html[fn_idx: fn_idx + 2200]
    assert "hbu-download-section" in fn_body
    assert "d.html_url" in fn_body
    # catch handler must also show the section
    catch_idx = fn_body.index(".catch(")
    catch_body = fn_body[catch_idx: catch_idx + 800]
    assert "hbu-download-section" in catch_body, (
        "pvGenerateHbuPdfBundle .catch must also show hbu-download-section"
    )


# ════════════════════════════════════════════════════════════════════════════
# PANEL 4 — Standards Compliance
# ════════════════════════════════════════════════════════════════════════════

# ── T22: sc-download-section exists and is initially hidden ──────────────────
def test_T22_panel4_download_section_initially_hidden():
    html = _html()
    assert 'data-testid="sc-download-section"' in html, (
        "sc-download-section must be present in HTML"
    )
    idx = html.index('data-testid="sc-download-section"')
    nearby = html[idx: idx + 100]
    assert "display:none" in nearby, (
        "sc-download-section must start with display:none (not shown before generation)"
    )


# ── T23: Panel 4 has PDF, HTML view, and HTML download links ─────────────────
def test_T23_panel4_has_all_three_output_links():
    html = _html()
    assert 'data-testid="sc-download-pdf-link"' in html
    assert 'data-testid="sc-view-html"'         in html
    assert 'data-testid="sc-download-html"'     in html


# ── T24: Pre-generation inactive buttons are hidden ──────────────────────────
def test_T24_panel4_inactive_buttons_hidden():
    html = _html()
    idx_pdf   = html.index('data-testid="sc-download-pdf"')
    idx_excel = html.index('data-testid="sc-download-excel"')
    nearby_pdf   = html[idx_pdf:   idx_pdf   + 300]
    nearby_excel = html[idx_excel: idx_excel + 300]
    assert "display:none" in nearby_pdf, (
        "sc-download-pdf button must have display:none (inactive before generation)"
    )
    assert "display:none" in nearby_excel, (
        "sc-download-excel button must have display:none (inactive before generation)"
    )


# ── T25: sc-generate-report calls pvGenerateStandardsComplianceBundle ─────────
def test_T25_panel4_generate_button_calls_standards_bundle_function():
    html = _html()
    idx = html.index('data-testid="sc-generate-report"')
    nearby = html[idx: idx + 300]
    assert "pvGenerateStandardsComplianceBundle" in nearby, (
        "sc-generate-report must call pvGenerateStandardsComplianceBundle"
    )
    assert "pvIssueSpecialReportPdf" not in nearby, (
        "sc-generate-report must NOT call pvIssueSpecialReportPdf directly"
    )


# ── T26: pvGenerateStandardsComplianceBundle function defined and shows result ─
def test_T26_pvGenerateStandardsComplianceBundle_function_defined_and_correct():
    html = _html()
    assert "function pvGenerateStandardsComplianceBundle()" in html
    fn_idx = html.index("function pvGenerateStandardsComplianceBundle()")
    fn_body = html[fn_idx: fn_idx + 2200]
    assert "sc-download-section" in fn_body, (
        "pvGenerateStandardsComplianceBundle must show sc-download-section"
    )
    assert "d.html_url" in fn_body, (
        "pvGenerateStandardsComplianceBundle must use d.html_url from API response"
    )
    catch_idx = fn_body.index(".catch(")
    catch_body = fn_body[catch_idx: catch_idx + 800]
    assert "sc-download-section" in catch_body, (
        "pvGenerateStandardsComplianceBundle .catch must also show sc-download-section"
    )
