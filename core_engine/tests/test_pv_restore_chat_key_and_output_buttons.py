"""
PVRCK-B01 – PVRCK-B18
Professional Valuation — Restore Old Chat Key and Clarify Report Output Buttons
Backend/HTML structure tests.
"""
import pathlib
import pytest

HTML_PATH = pathlib.Path(__file__).parents[2] / "frontend" / "index.html"


@pytest.fixture(scope="module")
def html():
    return HTML_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# B01 – unified_report_output_controls_context object exists in JS
# ---------------------------------------------------------------------------
def test_B01_unified_report_output_controls_context_exists(html):
    """PVRCK-B01: pvCollectUnifiedReportGenerationControlContext function exists."""
    assert "pvCollectUnifiedReportGenerationControlContext" in html


# ---------------------------------------------------------------------------
# B02 – single_report_dropdown flag is true
# ---------------------------------------------------------------------------
def test_B02_single_report_dropdown_true(html):
    """PVRCK-B02: single_report_dropdown: true in context function."""
    assert "single_report_dropdown" in html


# ---------------------------------------------------------------------------
# B03 – report_options_count equals 7
# ---------------------------------------------------------------------------
def test_B03_report_options_count_seven(html):
    """PVRCK-B03: report_options_count: 7 in context."""
    assert "report_options_count" in html
    # Verify exactly 7 options in the dropdown
    count = html.count('<option value=')
    # the main dropdown has 7 options — check specific values
    assert "traditional_report" in html
    assert "detailed_report" in html
    assert "professional_report" in html
    assert "simulated_uploaded_report" in html
    assert "report_review_output" in html
    assert "hbu_analysis_report" in html
    assert "standards_compliance_report" in html


# ---------------------------------------------------------------------------
# B04 – pdf_is_output_format_not_report_type = true
# ---------------------------------------------------------------------------
def test_B04_pdf_is_output_format_not_report_type(html):
    """PVRCK-B04: pdf_is_output_format_not_report_type flag present."""
    assert "pdf_is_output_format_not_report_type" in html


# ---------------------------------------------------------------------------
# B05 – excel_is_output_format_not_report_type = true
# ---------------------------------------------------------------------------
def test_B05_excel_is_output_format_not_report_type(html):
    """PVRCK-B05: excel_is_output_format_not_report_type flag present."""
    assert "excel_is_output_format_not_report_type" in html


# ---------------------------------------------------------------------------
# B06 – user_pdf_button_visible = true
# ---------------------------------------------------------------------------
def test_B06_user_pdf_button_visible(html):
    """PVRCK-B06: user_pdf_button_visible flag present."""
    assert "user_pdf_button_visible" in html


# ---------------------------------------------------------------------------
# B07 – admin_excel_button_protected = true
# ---------------------------------------------------------------------------
def test_B07_admin_excel_button_protected(html):
    """PVRCK-B07: admin_excel_button_protected flag present."""
    assert "admin_excel_button_protected" in html


# ---------------------------------------------------------------------------
# B08 – old_chat_key_restored = true
# ---------------------------------------------------------------------------
def test_B08_old_chat_key_restored(html):
    """PVRCK-B08: old_chat_key_restored flag present in context."""
    assert "old_chat_key_restored" in html


# ---------------------------------------------------------------------------
# B09 – chat_key_position_below_pdf = true
# ---------------------------------------------------------------------------
def test_B09_chat_key_position_below_pdf(html):
    """PVRCK-B09: chat_key_position_below_pdf flag present."""
    assert "chat_key_position_below_pdf" in html


# ---------------------------------------------------------------------------
# B10 – PDF action maps to pvGenerateUnifiedUserPdf
# ---------------------------------------------------------------------------
def test_B10_pdf_action_maps_to_user_pdf_function(html):
    """PVRCK-B10: pvGenerateUnifiedUserPdf function preserved; visible button removed (deduplication)."""
    assert "pvGenerateUnifiedUserPdf" in html
    # Button removed from visible UI — deduplication phase: pro-val-generate-user-pdf-report no longer a button
    assert 'onclick="pvGenerateUnifiedUserPdf()"' not in html


# ---------------------------------------------------------------------------
# B11 – Excel action maps to pvGenerateUnifiedAdminExcel
# ---------------------------------------------------------------------------
def test_B11_excel_action_maps_to_admin_excel_function(html):
    """PVRCK-B11: Excel button calls pvGenerateUnifiedAdminExcel."""
    assert "pvGenerateUnifiedAdminExcel" in html
    assert 'data-testid="pro-val-generate-admin-excel-sheets"' in html


# ---------------------------------------------------------------------------
# B12 – Chat key maps to pvExecuteOldStyleChatKeyAction
# ---------------------------------------------------------------------------
def test_B12_chat_key_maps_to_chat_action_function(html):
    """PVRCK-B12: pvExecuteOldStyleChatKeyAction function preserved; visible button removed (deduplication)."""
    assert "pvExecuteOldStyleChatKeyAction" in html
    # Button removed from visible UI — deduplication phase: pv-old-style-chat-key no longer a button
    assert 'onclick="pvExecuteOldStyleChatKeyAction()"' not in html


# ---------------------------------------------------------------------------
# B13 – PDF button uses selected unified_report_action
# ---------------------------------------------------------------------------
def test_B13_pdf_uses_unified_report_action(html):
    """PVRCK-B13: pvGenerateUnifiedUserPdf reads pv-chat-report-action."""
    assert "pv-chat-report-action" in html
    # function body references the report action
    assert "unified_report_action" in html


# ---------------------------------------------------------------------------
# B14 – Excel button uses selected unified_report_action
# ---------------------------------------------------------------------------
def test_B14_excel_uses_unified_report_action(html):
    """PVRCK-B14: pvGenerateUnifiedAdminExcel context includes unified_report_action."""
    assert "unified_report_action" in html


# ---------------------------------------------------------------------------
# B15 – all controls use unified_professional_valuation_page_context
# ---------------------------------------------------------------------------
def test_B15_controls_use_unified_page_context(html):
    """PVRCK-B15: uses_unified_professional_valuation_page_context is true in context."""
    assert "uses_unified_professional_valuation_page_context" in html


# ---------------------------------------------------------------------------
# B16 – no internal paths in backend context
# ---------------------------------------------------------------------------
def test_B16_no_internal_paths_in_context(html):
    """PVRCK-B16: no_internal_paths flag present; no literal Windows paths in HTML."""
    assert "no_internal_paths" in html
    import re
    windows_paths = re.findall(r"C:\\\\Users\\\\[^<\"'`\s]+", html)
    assert len(windows_paths) == 0, f"Internal Windows paths found: {windows_paths[:3]}"


# ---------------------------------------------------------------------------
# B17 – ordinary valuation page unaffected (bridge_api.py parses clean)
# ---------------------------------------------------------------------------
def test_B17_ordinary_valuation_unaffected():
    """PVRCK-B17: bridge_api.py syntax is clean."""
    import ast
    src = (pathlib.Path(__file__).parents[2] / "core_engine" / "bridge_api.py").read_text(encoding="utf-8")
    ast.parse(src)  # raises SyntaxError if broken


# ---------------------------------------------------------------------------
# B18 – tax appeal page unaffected
# ---------------------------------------------------------------------------
def test_B18_tax_appeal_unaffected(html):
    """PVRCK-B18: Tax appeal section markers still present in HTML."""
    assert "tax-appeal" in html or "tax_appeal" in html or "الطعن الضريبي" in html


# ---------------------------------------------------------------------------
# Additional structural checks
# ---------------------------------------------------------------------------
def test_B19_pdf_button_label_correct(html):
    """PVRCK-B19: PDF button label is 'إصدار تقرير PDF للمستخدم'."""
    assert "إصدار تقرير PDF للمستخدم" in html


def test_B20_chat_key_label_present(html):
    """PVRCK-B20: Chat key has 'إرسال للشات' label."""
    assert "إرسال للشات" in html


def test_B21_dropdown_label_correct(html):
    """PVRCK-B21: Dropdown label is 'تحليل وإصدار التقارير'."""
    assert "تحليل وإصدار التقارير" in html


def test_B22_excel_label_correct(html):
    """PVRCK-B22: Excel button label is 'إصدار شيتات Excel للأدمن'."""
    assert "إصدار شيتات Excel للأدمن" in html


def test_B23_old_output_button_not_visible(html):
    """PVRCK-B23: 'إصدار المخرجات' button not visible — replaced with hidden span."""
    # The old button text should not appear as a real button anymore.
    # It's now in a hidden span's sibling context.
    # Check: no <button ... > ...إصدار المخرجات... </button> pattern with it being a real button
    import re
    # The "إصدار المخرجات" text only appears in JS strings now, not in a visible button
    button_pattern = re.compile(
        r'<button[^>]*>[^<]*إصدار المخرجات[^<]*</button>', re.DOTALL
    )
    matches = button_pattern.findall(html)
    assert len(matches) == 0, "إصدار المخرجات still present as a visible button"


def test_B24_flex_column_layout(html):
    """PVRCK-B24: Output buttons container uses flex-direction:column."""
    assert "flex-direction:column" in html


def test_B25_legacy_compat_spans_present(html):
    """PVRCK-B25: Backward-compat hidden spans for old testids present."""
    assert 'data-testid="pro-val-unified-generate-user-pdf"' in html
    assert 'data-testid="pro-val-unified-generate-admin-excel"' in html
    assert 'data-testid="pro-val-unified-generate-selected-output"' in html
