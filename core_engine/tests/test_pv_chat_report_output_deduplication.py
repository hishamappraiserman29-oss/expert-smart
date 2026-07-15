"""
DUPL-B01 – DUPL-B13
Professional Valuation — Remove Duplicate Lower Chat Output Buttons
Backend/HTML structure tests.
advisory_only=True | not_real_training=True | no_commit=True
"""
import ast
import pathlib
import re
import pytest

HTML_PATH = pathlib.Path(__file__).parents[2] / "frontend" / "index.html"
CTX_PATH  = pathlib.Path(__file__).parents[1] / "chat_report_output_deduplication_context.py"


@pytest.fixture(scope="module")
def html():
    return HTML_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def ctx():
    from core_engine.chat_report_output_deduplication_context import (
        chat_report_output_deduplication_context,
    )
    return chat_report_output_deduplication_context


# ---------------------------------------------------------------------------
# DUPL-B01 — context module importable
# ---------------------------------------------------------------------------
def test_B01_context_module_importable(ctx):
    """DUPL-B01: chat_report_output_deduplication_context is importable."""
    assert ctx is not None
    assert isinstance(ctx, dict)


# ---------------------------------------------------------------------------
# DUPL-B02 — main_unified_report_section_preserved = True
# ---------------------------------------------------------------------------
def test_B02_main_unified_report_section_preserved(ctx):
    """DUPL-B02: main_unified_report_section_preserved is True."""
    assert ctx["main_unified_report_section_preserved"] is True


# ---------------------------------------------------------------------------
# DUPL-B03 — main_unified_report_label correct
# ---------------------------------------------------------------------------
def test_B03_main_unified_report_label(ctx):
    """DUPL-B03: main_unified_report_label is 'تحليل وإصدار التقارير'."""
    assert ctx["main_unified_report_label"] == "تحليل وإصدار التقارير"


# ---------------------------------------------------------------------------
# DUPL-B04 — visible_report_types_count = 7
# ---------------------------------------------------------------------------
def test_B04_visible_report_types_count_seven(ctx):
    """DUPL-B04: visible_report_types_count is 7."""
    assert ctx["visible_report_types_count"] == 7


# ---------------------------------------------------------------------------
# DUPL-B05 — duplicate_lower_pdf_button_removed = True
# ---------------------------------------------------------------------------
def test_B05_duplicate_lower_pdf_button_removed(ctx):
    """DUPL-B05: duplicate_lower_pdf_button_removed is True."""
    assert ctx["duplicate_lower_pdf_button_removed"] is True


# ---------------------------------------------------------------------------
# DUPL-B06 — duplicate_lower_send_to_chat_button_removed = True
# ---------------------------------------------------------------------------
def test_B06_duplicate_lower_send_to_chat_button_removed(ctx):
    """DUPL-B06: duplicate_lower_send_to_chat_button_removed is True."""
    assert ctx["duplicate_lower_send_to_chat_button_removed"] is True


# ---------------------------------------------------------------------------
# DUPL-B07 — pdf_generation_capability_preserved = True
# ---------------------------------------------------------------------------
def test_B07_pdf_generation_capability_preserved(ctx):
    """DUPL-B07: pdf_generation_capability_preserved is True."""
    assert ctx["pdf_generation_capability_preserved"] is True


# ---------------------------------------------------------------------------
# DUPL-B08 — admin_excel_generation_capability_preserved = True
# ---------------------------------------------------------------------------
def test_B08_admin_excel_generation_capability_preserved(ctx):
    """DUPL-B08: admin_excel_generation_capability_preserved is True."""
    assert ctx["admin_excel_generation_capability_preserved"] is True


# ---------------------------------------------------------------------------
# DUPL-B09 — feature_toggles_preserved = True
# ---------------------------------------------------------------------------
def test_B09_feature_toggles_preserved(ctx):
    """DUPL-B09: feature_toggles_preserved is True."""
    assert ctx["feature_toggles_preserved"] is True


# ---------------------------------------------------------------------------
# DUPL-B10 — advisory_notice_preserved = True
# ---------------------------------------------------------------------------
def test_B10_advisory_notice_preserved(ctx):
    """DUPL-B10: advisory_notice_preserved is True."""
    assert ctx["advisory_notice_preserved"] is True


# ---------------------------------------------------------------------------
# DUPL-B11 — deleted_backend_capabilities = []
# ---------------------------------------------------------------------------
def test_B11_deleted_backend_capabilities_empty(ctx):
    """DUPL-B11: deleted_backend_capabilities is empty list."""
    assert ctx["deleted_backend_capabilities"] == []


# ---------------------------------------------------------------------------
# DUPL-B12 — HTML: visible button elements not present; functions preserved
# ---------------------------------------------------------------------------
def test_B12_html_buttons_removed_functions_preserved(html):
    """DUPL-B12: PDF/ChatKey button elements removed from HTML; backend JS functions intact."""
    # Visible buttons gone
    assert 'onclick="pvGenerateUnifiedUserPdf()"' not in html, (
        "PDF button with onclick still present in HTML"
    )
    assert 'onclick="pvExecuteOldStyleChatKeyAction()"' not in html, (
        "Chat key button with onclick still present in HTML"
    )
    # Backend functions still defined
    assert "function pvGenerateUnifiedUserPdf()" in html
    assert "function pvExecuteOldStyleChatKeyAction()" in html
    # Unified report section intact
    assert "تحليل وإصدار التقارير" in html
    assert 'data-testid="pro-val-unified-analyze-generate-reports-select"' in html
    # Seven report options intact
    for val in [
        "traditional_report", "detailed_report", "professional_report",
        "simulated_uploaded_report", "report_review_output",
        "hbu_analysis_report", "standards_compliance_report",
    ]:
        assert f'value="{val}"' in html, f"Report option '{val}' missing"


# ---------------------------------------------------------------------------
# DUPL-B13 — no internal paths; bridge_api.py parses; tax appeal unaffected
# ---------------------------------------------------------------------------
def test_B13_no_internal_paths_and_unaffected_pages(html):
    """DUPL-B13: No Windows paths in HTML; bridge_api parses; tax appeal intact."""
    # No internal paths
    assert "no_internal_paths" in html
    windows_paths = re.findall(r"C:\\\\Users\\\\[^<\"'`\s]+", html)
    assert len(windows_paths) == 0, f"Internal paths found: {windows_paths[:3]}"
    # bridge_api.py syntax clean
    bridge = (
        pathlib.Path(__file__).parents[2] / "core_engine" / "bridge_api.py"
    ).read_text(encoding="utf-8")
    ast.parse(bridge)
    # Tax appeal marker present
    assert "tax-appeal" in html or "tax_appeal" in html or "الطعن الضريبي" in html
