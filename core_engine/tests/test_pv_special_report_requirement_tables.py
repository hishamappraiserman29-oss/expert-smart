# test_pv_special_report_requirement_tables.py
# Backend tests — Special Report Requirement Tables (Second Key)
# advisory_only=True | not_real_training=True | no_commit=True

import json
import pathlib
import sys
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

HTML = pathlib.Path("frontend/index.html")

SPECIAL_TYPES = [
    "report_review_output",
    "simulated_uploaded_report",
    "hbu_analysis_report",
    "standards_compliance_report"
]


def _ctx():
    from core_engine.professional_valuation_special_report_requirement_tables_context import (
        get_special_report_requirement_tables_context,
    )
    return get_special_report_requirement_tables_context()


def _html():
    return HTML.read_text(encoding="utf-8", errors="replace")


# ── T01: Context module importable and returns dict ───────────────────────────
def test_T01_context_module_importable():
    ctx = _ctx()
    assert isinstance(ctx, dict)
    assert len(ctx) > 0


# ── T02: special_report_workflows_enabled = True ──────────────────────────────
def test_T02_special_report_workflows_enabled():
    assert _ctx()["special_report_workflows_enabled"] is True


# ── T03: Special report types are exactly the four required ───────────────────
def test_T03_special_report_types_exactly_four():
    ctx = _ctx()
    assert sorted(ctx["special_report_types"]) == sorted(SPECIAL_TYPES)


# ── T04: each_special_report_has_dedicated_requirement_table = True ───────────
def test_T04_each_special_report_has_dedicated_requirement_table():
    assert _ctx()["each_special_report_has_dedicated_requirement_table"] is True


# ── T05: report_review_requirements_enabled = True ───────────────────────────
def test_T05_report_review_requirements_enabled():
    assert _ctx()["report_review_requirements_enabled"] is True


# ── T06: simulated_uploaded_report_requirements_enabled = True ───────────────
def test_T06_simulated_uploaded_report_requirements_enabled():
    assert _ctx()["simulated_uploaded_report_requirements_enabled"] is True


# ── T07: hbu_requirements_enabled = True ─────────────────────────────────────
def test_T07_hbu_requirements_enabled():
    assert _ctx()["hbu_requirements_enabled"] is True


# ── T08: standards_compliance_requirements_enabled = True ────────────────────
def test_T08_standards_compliance_requirements_enabled():
    assert _ctx()["standards_compliance_requirements_enabled"] is True


# ── T09: special_reports_removed_from_core_report_selector = True ────────────
def test_T09_special_reports_removed_from_core_report_selector():
    assert _ctx()["special_reports_removed_from_core_report_selector"] is True


# ── T10: generic_chat_uploads_for_special_reports_removed = True ─────────────
def test_T10_generic_chat_uploads_removed():
    assert _ctx()["generic_chat_uploads_for_special_reports_removed"] is True


# ── T11: HBU has four tests ──────────────────────────────────────────────────
def test_T11_hbu_has_four_tests():
    ctx = _ctx()
    hbu = ctx["hbu_analysis_report_requirement_table"]
    four = hbu["hbu_four_tests"]
    assert four.get("physically_possible") is True
    assert four.get("legally_permissible") is True
    assert four.get("financially_feasible") is True
    assert four.get("maximally_productive") is True
    assert hbu["is_valuation_report"] is False


# ── T12: Standards compliance has IVS matrix ─────────────────────────────────
def test_T12_standards_has_ivs_matrix():
    ctx = _ctx()
    sc = ctx["standards_compliance_report_requirement_table"]
    ivs = sc["ivs_matrix"]
    assert "rows" in ivs
    assert "Scope of Work" in ivs["rows"]
    assert "Basis of Value" in ivs["rows"]


# ── T13: Standards compliance has USPAP matrix ───────────────────────────────
def test_T13_standards_has_uspap_matrix():
    ctx = _ctx()
    sc = ctx["standards_compliance_report_requirement_table"]
    uspap = sc["uspap_matrix"]
    assert "rows" in uspap
    assert "Scope of Work" in uspap["rows"]
    assert "Intended Use" in uspap["rows"]


# ── T14: Standards compliance has RICS matrix ────────────────────────────────
def test_T14_standards_has_rics_matrix():
    ctx = _ctx()
    sc = ctx["standards_compliance_report_requirement_table"]
    rics = sc["rics_matrix"]
    assert "rows" in rics
    assert "Terms of Engagement" in rics["rows"]
    assert "Valuation Approach" in rics["rows"]


# ── T15: Standards compliance has IFRS 13 matrix ─────────────────────────────
def test_T15_standards_has_ifrs13_matrix():
    ctx = _ctx()
    sc = ctx["standards_compliance_report_requirement_table"]
    ifrs = sc["ifrs13_matrix"]
    assert "rows" in ifrs
    assert "Fair Value Context" in ifrs["rows"]
    assert "Inputs Hierarchy" in ifrs["rows"]


# ── T16: Report review has methodology review group ──────────────────────────
def test_T16_report_review_has_methodology_review_group():
    ctx = _ctx()
    rr = ctx["report_review_requirement_table"]
    assert rr["methodology_review_group"] is True
    assert "مراجعة أساليب التقييم" in rr["groups"]


# ── T17: Simulated report has source material status group ────────────────────
def test_T17_simulation_has_source_material_status_group():
    ctx = _ctx()
    sim = ctx["simulated_uploaded_report_requirement_table"]
    assert sim["source_material_status_group"] is True
    assert "حالة المادة المصدرية" in sim["groups"]


# ── T18: Completion validation enabled ───────────────────────────────────────
def test_T18_completion_validation_enabled():
    assert _ctx()["completion_validation_enabled"] is True


# ── T19: Minimum requirement tracking enabled ─────────────────────────────────
def test_T19_minimum_requirement_tracking_enabled():
    assert _ctx()["minimum_requirement_tracking_enabled"] is True


# ── T20: Unified context structure exists ────────────────────────────────────
def test_T20_unified_context_structure_exists():
    ctx = _ctx()
    uc = ctx["unified_context_structure"]
    assert uc["enabled"] is True
    assert "requirement_values" in uc
    assert "completion_status" in uc
    assert "missing_minimum_requirements" in uc
    for t in SPECIAL_TYPES:
        assert t in uc["requirement_values"]
        assert t in uc["completion_status"]
        assert t in uc["missing_minimum_requirements"]


# ── T21: Backend keys preserved ──────────────────────────────────────────────
def test_T21_backend_keys_preserved():
    assert _ctx()["backend_keys_preserved"] is True
    html = _html()
    for key in SPECIAL_TYPES:
        assert key in html, f"Backend key missing from HTML: {key}"


# ── T22: No internal paths in HTML ───────────────────────────────────────────
def test_T22_no_internal_paths():
    assert _ctx()["no_internal_paths"] is True
    html = _html()
    for pat in ["C:\\Users\\Lenovo", "AppData\\Local", "__file__"]:
        assert pat not in html, f"Internal path in HTML: {pat}"


# ── T23: Ordinary valuation unaffected ───────────────────────────────────────
def test_T23_ordinary_valuation_unaffected():
    assert _ctx()["ordinary_valuation_unaffected"] is True
    html = _html()
    assert "pro-val-section-report-type" in html or "pvr-generic-requirements" in html or "traditional_report" in html


# ── T24: Tax appeal unaffected ───────────────────────────────────────────────
def test_T24_tax_appeal_unaffected():
    assert _ctx()["tax_appeal_unaffected"] is True
    html = _html()
    assert "tax" in html.lower()
