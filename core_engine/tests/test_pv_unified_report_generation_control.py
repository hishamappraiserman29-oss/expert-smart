"""
Backend tests: Unified Report Generation Control
=================================================
PVURGC-B01 through PVURGC-B22

Verifies that the unified "تحليل وإصدار التقارير" control module
exposes the correct structure, alias mapping, and output permissions.
"""
from __future__ import annotations
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import importlib
import pytest


@pytest.fixture(scope="module")
def ctrl():
    """Import the unified report control module."""
    import importlib.util, pathlib
    spec_path = pathlib.Path(__file__).parent.parent / "professional_valuation_unified_report_control.py"
    spec = importlib.util.spec_from_file_location("pvurc", spec_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── PVURGC-B01 ────────────────────────────────────────────────────────────

def test_PVURGC_B01_control_context_exists(ctrl):
    """PVURGC-B01: UNIFIED_REPORT_GENERATION_CONTROL_CONTEXT dict exists."""
    assert hasattr(ctrl, "UNIFIED_REPORT_GENERATION_CONTROL_CONTEXT")
    assert isinstance(ctrl.UNIFIED_REPORT_GENERATION_CONTROL_CONTEXT, dict)


# ── PVURGC-B02 ────────────────────────────────────────────────────────────

def test_PVURGC_B02_canonical_key_is_unified_report_action(ctrl):
    """PVURGC-B02: canonical_key = 'unified_report_action'."""
    ctx = ctrl.UNIFIED_REPORT_GENERATION_CONTROL_CONTEXT
    assert ctx["canonical_key"] == "unified_report_action"


# ── PVURGC-B03 ────────────────────────────────────────────────────────────

def test_PVURGC_B03_canonical_label_ar(ctrl):
    """PVURGC-B03: canonical_label_ar = 'تحليل وإصدار التقارير'."""
    ctx = ctrl.UNIFIED_REPORT_GENERATION_CONTROL_CONTEXT
    assert ctx["canonical_label_ar"] == "تحليل وإصدار التقارير"


# ── PVURGC-B04 ────────────────────────────────────────────────────────────

def test_PVURGC_B04_visible_options_count_is_7(ctrl):
    """PVURGC-B04: visible_options_count = 7."""
    ctx = ctrl.UNIFIED_REPORT_GENERATION_CONTROL_CONTEXT
    assert ctx["visible_options_count"] == 7


# ── PVURGC-B05 ────────────────────────────────────────────────────────────

def test_PVURGC_B05_alias_mapping_preserves_report_type(ctrl):
    """PVURGC-B05: REPORT_ACTION_ALIAS_MAPPING includes 'report_type' key."""
    mapping = ctrl.REPORT_ACTION_ALIAS_MAPPING
    assert "report_type" in mapping
    assert mapping["report_type"] == "unified_report_action"


# ── PVURGC-B06 ────────────────────────────────────────────────────────────

def test_PVURGC_B06_alias_mapping_preserves_report_action(ctrl):
    """PVURGC-B06: REPORT_ACTION_ALIAS_MAPPING includes 'report_action' key."""
    mapping = ctrl.REPORT_ACTION_ALIAS_MAPPING
    assert "report_action" in mapping
    assert mapping["report_action"] == "unified_report_action"


# ── PVURGC-B07 ────────────────────────────────────────────────────────────

def test_PVURGC_B07_all_seven_actions_present(ctrl):
    """PVURGC-B07: UNIFIED_REPORT_ACTION_OPTIONS contains exactly 7 entries."""
    options = ctrl.UNIFIED_REPORT_ACTION_OPTIONS
    assert len(options) == 7
    keys = [o["key"] for o in options]
    assert len(keys) == len(set(keys)), "Duplicate keys found"


# ── PVURGC-B08 ────────────────────────────────────────────────────────────

def test_PVURGC_B08_traditional_report_exists(ctrl):
    """PVURGC-B08: traditional_report is a valid option."""
    keys = [o["key"] for o in ctrl.UNIFIED_REPORT_ACTION_OPTIONS]
    assert "traditional_report" in keys


# ── PVURGC-B09 ────────────────────────────────────────────────────────────

def test_PVURGC_B09_detailed_report_exists(ctrl):
    """PVURGC-B09: detailed_report is a valid option."""
    keys = [o["key"] for o in ctrl.UNIFIED_REPORT_ACTION_OPTIONS]
    assert "detailed_report" in keys


# ── PVURGC-B10 ────────────────────────────────────────────────────────────

def test_PVURGC_B10_professional_report_exists(ctrl):
    """PVURGC-B10: professional_report is a valid option."""
    keys = [o["key"] for o in ctrl.UNIFIED_REPORT_ACTION_OPTIONS]
    assert "professional_report" in keys


# ── PVURGC-B11 ────────────────────────────────────────────────────────────

def test_PVURGC_B11_simulated_uploaded_report_exists(ctrl):
    """PVURGC-B11: simulated_uploaded_report is a valid option."""
    keys = [o["key"] for o in ctrl.UNIFIED_REPORT_ACTION_OPTIONS]
    assert "simulated_uploaded_report" in keys


# ── PVURGC-B12 ────────────────────────────────────────────────────────────

def test_PVURGC_B12_report_review_output_exists(ctrl):
    """PVURGC-B12: report_review_output is a valid option."""
    keys = [o["key"] for o in ctrl.UNIFIED_REPORT_ACTION_OPTIONS]
    assert "report_review_output" in keys


# ── PVURGC-B13 ────────────────────────────────────────────────────────────

def test_PVURGC_B13_hbu_analysis_report_exists(ctrl):
    """PVURGC-B13: hbu_analysis_report is a valid option."""
    keys = [o["key"] for o in ctrl.UNIFIED_REPORT_ACTION_OPTIONS]
    assert "hbu_analysis_report" in keys


# ── PVURGC-B14 ────────────────────────────────────────────────────────────

def test_PVURGC_B14_standards_compliance_report_exists(ctrl):
    """PVURGC-B14: standards_compliance_report is a valid option."""
    keys = [o["key"] for o in ctrl.UNIFIED_REPORT_ACTION_OPTIONS]
    assert "standards_compliance_report" in keys


# ── PVURGC-B15 ────────────────────────────────────────────────────────────

def test_PVURGC_B15_excel_pattern_not_main_report_selector(ctrl):
    """PVURGC-B15: excel_pattern_is_not_main_report_selector = True."""
    ctx = ctrl.UNIFIED_REPORT_GENERATION_CONTROL_CONTEXT
    assert ctx["excel_pattern_is_not_main_report_selector"] is True


# ── PVURGC-B16 ────────────────────────────────────────────────────────────

def test_PVURGC_B16_unified_action_in_page_context(ctrl):
    """PVURGC-B16: build_unified_report_generation_control_context includes selected_unified_report_action."""
    ctx = ctrl.build_unified_report_generation_control_context(
        selected_unified_report_action="detailed_report"
    )
    assert ctx["selected_unified_report_action"] == "detailed_report"


# ── PVURGC-B17 ────────────────────────────────────────────────────────────

def test_PVURGC_B17_output_permissions_use_unified_report_action(ctrl):
    """PVURGC-B17: output_permissions block exists and is driven by unified_report_action."""
    ctx = ctrl.build_unified_report_generation_control_context()
    assert "output_permissions" in ctx
    perms = ctx["output_permissions"]
    assert "can_generate_user_pdf" in perms


# ── PVURGC-B18 ────────────────────────────────────────────────────────────

def test_PVURGC_B18_pdf_generation_context_uses_unified_action(ctrl):
    """PVURGC-B18: pdf_generation_uses_unified_report_action = True."""
    ctx = ctrl.build_unified_report_generation_control_context()
    assert ctx.get("pdf_generation_uses_unified_report_action") is True


# ── PVURGC-B19 ────────────────────────────────────────────────────────────

def test_PVURGC_B19_excel_generation_context_uses_unified_action(ctrl):
    """PVURGC-B19: excel_generation_uses_unified_report_action = True."""
    ctx = ctrl.build_unified_report_generation_control_context()
    assert ctx.get("excel_generation_uses_unified_report_action") is True


# ── PVURGC-B20 ────────────────────────────────────────────────────────────

def test_PVURGC_B20_no_internal_paths_in_context(ctrl):
    """PVURGC-B20: No internal file paths exposed in context."""
    ctx = ctrl.build_unified_report_generation_control_context()
    import json
    ctx_str = json.dumps(ctx, ensure_ascii=False)
    bad = ["C:\\", "c:\\", "/Users/", "/home/", "core_engine/"]
    for b in bad:
        assert b not in ctx_str, f"Internal path fragment found: {b!r}"


# ── PVURGC-B21 ────────────────────────────────────────────────────────────

def test_PVURGC_B21_resolve_from_payload_legacy_report_type(ctrl):
    """PVURGC-B21: resolve_unified_report_action_from_payload reads report_type fallback."""
    result = ctrl.resolve_unified_report_action_from_payload({"report_type": "detailed_report"})
    assert result == "detailed_report"


# ── PVURGC-B22 ────────────────────────────────────────────────────────────

def test_PVURGC_B22_resolve_from_payload_prefers_unified_key(ctrl):
    """PVURGC-B22: unified_report_action takes precedence over report_type in payload."""
    result = ctrl.resolve_unified_report_action_from_payload({
        "report_type":          "traditional_report",
        "unified_report_action": "hbu_analysis_report",
    })
    assert result == "hbu_analysis_report"
