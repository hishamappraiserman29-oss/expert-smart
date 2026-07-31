"""
PVFSR Backend Tests — Force Single Report Control
==================================================
Tests PVFSR-B01 through PVFSR-B17.
Verifies that the unified report generation control context is correct,
all aliases are preserved, and outputs use unified_report_action.
"""
import json
import pathlib
import sys
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

from core_engine.professional_valuation_unified_report_control import (
    UNIFIED_REPORT_GENERATION_CONTROL_CONTEXT,
    UNIFIED_REPORT_ACTION_OPTIONS,
    REPORT_ACTION_ALIAS_MAPPING,
    build_unified_report_generation_control_context,
    resolve_unified_report_action_from_payload,
)

_QA_DIR = (
    pathlib.Path(__file__).parent.parent
    / "instance" / "manual_review_outputs"
    / "professional_valuation_force_single_report_control"
)

def _load(fname: str) -> dict:
    p = _QA_DIR / fname
    assert p.exists(), f"QA file missing: {fname}"
    return json.loads(p.read_text(encoding="utf-8"))


# PVFSR-B01: unified_report_generation_control_context exists
def test_pvfsr_b01_control_context_exists():
    ctx = UNIFIED_REPORT_GENERATION_CONTROL_CONTEXT
    assert ctx, "PVFSR-B01: unified_report_generation_control_context must exist and be non-empty"


# PVFSR-B02: single_visible_control = True
def test_pvfsr_b02_single_visible_control():
    assert UNIFIED_REPORT_GENERATION_CONTROL_CONTEXT["single_visible_control"] is True, \
        "PVFSR-B02: single_visible_control must be True"


# PVFSR-B03: canonical_label_ar = "تحليل وإصدار التقارير"
def test_pvfsr_b03_canonical_label():
    assert UNIFIED_REPORT_GENERATION_CONTROL_CONTEXT["canonical_label_ar"] == "تحليل وإصدار التقارير", \
        "PVFSR-B03: canonical_label_ar must be 'تحليل وإصدار التقارير'"


# PVFSR-B04: canonical_key = "unified_report_action"
def test_pvfsr_b04_canonical_key():
    assert UNIFIED_REPORT_GENERATION_CONTROL_CONTEXT["canonical_key"] == "unified_report_action", \
        "PVFSR-B04: canonical_key must be 'unified_report_action'"


# PVFSR-B05: visible_options_count = 7
def test_pvfsr_b05_visible_options_count():
    assert UNIFIED_REPORT_GENERATION_CONTROL_CONTEXT["visible_options_count"] == 7, \
        "PVFSR-B05: visible_options_count must be 7"


# PVFSR-B06: all 7 report action keys present
def test_pvfsr_b06_all_seven_options():
    expected = {
        "traditional_report",
        "detailed_report",
        "professional_report",
        "simulated_uploaded_report",
        "report_review_output",
        "hbu_analysis_report",
        "standards_compliance_report",
    }
    actual = {o["key"] for o in UNIFIED_REPORT_ACTION_OPTIONS}
    assert actual == expected, f"PVFSR-B06: missing options: {expected - actual}"


# PVFSR-B07: report_type alias preserved
def test_pvfsr_b07_alias_report_type():
    assert REPORT_ACTION_ALIAS_MAPPING.get("report_type") == "unified_report_action", \
        "PVFSR-B07: report_type must alias to unified_report_action"


# PVFSR-B08: report_action alias preserved
def test_pvfsr_b08_alias_report_action():
    assert REPORT_ACTION_ALIAS_MAPPING.get("report_action") == "unified_report_action", \
        "PVFSR-B08: report_action must alias to unified_report_action"


# PVFSR-B09: selected_report_type alias preserved
def test_pvfsr_b09_alias_selected_report_type():
    assert REPORT_ACTION_ALIAS_MAPPING.get("selected_report_type") == "unified_report_action", \
        "PVFSR-B09: selected_report_type must alias to unified_report_action"


# PVFSR-B10: chat_report_action / browser_report_action resolve correctly
def test_pvfsr_b10_alias_resolve_from_payload():
    payload_old = {"report_type": "detailed_report"}
    result = resolve_unified_report_action_from_payload(payload_old)
    assert result == "detailed_report", "PVFSR-B10: should resolve from report_type alias"


# PVFSR-B11: Excel pattern is not main report selector
def test_pvfsr_b11_excel_pattern_not_main():
    assert UNIFIED_REPORT_GENERATION_CONTROL_CONTEXT["excel_pattern_is_not_main_report_selector"] is True, \
        "PVFSR-B11: excel_pattern_is_not_main_report_selector must be True"


# PVFSR-B12: PDF generation context uses unified_report_action
def test_pvfsr_b12_pdf_uses_unified_report_action():
    ctx = build_unified_report_generation_control_context("traditional_report")
    assert ctx["pdf_generation_uses_unified_report_action"] is True, \
        "PVFSR-B12: pdf_generation_uses_unified_report_action must be True"


# PVFSR-B13: Excel generation context uses unified_report_action
def test_pvfsr_b13_excel_uses_unified_report_action():
    ctx = build_unified_report_generation_control_context("detailed_report")
    assert ctx["excel_generation_uses_unified_report_action"] is True, \
        "PVFSR-B13: excel_generation_uses_unified_report_action must be True"


# PVFSR-B14: all_outputs_use_unified_professional_valuation_page_context
def test_pvfsr_b14_all_outputs_use_unified_context():
    assert UNIFIED_REPORT_GENERATION_CONTROL_CONTEXT.get(
        "uses_unified_professional_valuation_page_context"
    ) is True, "PVFSR-B14: uses_unified_professional_valuation_page_context must be True"


# PVFSR-B15: no internal paths in backend context
def test_pvfsr_b15_no_internal_paths():
    ctx_str = json.dumps(UNIFIED_REPORT_GENERATION_CONTROL_CONTEXT)
    for bad in ["core_engine/instance", "manual_review_outputs", "C:\\Users", "/home/"]:
        assert bad not in ctx_str, f"PVFSR-B15: internal path '{bad}' found in backend context"


# PVFSR-B16: old visible controls removed (documented in context)
def test_pvfsr_b16_old_controls_removed():
    removed = UNIFIED_REPORT_GENERATION_CONTROL_CONTEXT.get("removed_labels", [])
    assert "نوع التقرير أو الإجراء" in removed, \
        "PVFSR-B16: 'نوع التقرير أو الإجراء' must be in removed_labels"
    assert "تحليل وإصدار التقرير" in removed, \
        "PVFSR-B16: 'تحليل وإصدار التقرير' must be in removed_labels"


# PVFSR-B17: build_unified_report_generation_control_context returns valid structure
def test_pvfsr_b17_build_context_valid():
    ctx = build_unified_report_generation_control_context("professional_report")
    assert ctx["selected_unified_report_action"] == "professional_report"
    assert ctx["canonical_key"] == "unified_report_action"
    assert ctx["visible_options_count"] == 7
    assert ctx["advisory_only"] is True
    assert ctx["output_permissions"]["admin_excel_visible_to_current_user"] is False
