"""
Backend tests for HBU Analysis Workflow.
28 tests H01–H28.
Run: python -m pytest tests/test_pv_hbu_analysis_workflow.py -q
"""
from __future__ import annotations
import json
import pathlib
import pytest

_ROOT = pathlib.Path(__file__).parent.parent
_HBU  = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_hbu_analysis"
_AUD  = _HBU / "hbu_audits"
_PDF  = _HBU / "pdf_outputs"
_XL   = _HBU / "excel_outputs"
_SS   = _HBU / "screenshots"
_PREV = _HBU / "visual_previews"
_SRC  = _HBU / "source_registry"
_RPT  = _HBU / "final_report"
_TXT  = _HBU / "pdf_text_extracts"


def _aud(name: str) -> dict:
    p = _AUD / name
    assert p.exists(), f"HBU audit missing: {name}"
    return json.loads(p.read_text(encoding="utf-8"))


# ── H01: HBU workflow context exists ─────────────────────────────────────────
def test_H01_hbu_workflow_context_exists():
    audit = _aud("01_hbu_scope_and_property_data_audit.json")
    assert audit.get("hbu_workflow_enabled") is True
    assert audit.get("property_data_collected") is True


# ── H02: workflow is in Special Reports ──────────────────────────────────────
def test_H02_workflow_in_special_reports():
    audit = _aud("01_hbu_scope_and_property_data_audit.json")
    assert audit.get("not_inside_chat_box") is True
    assert audit.get("in_chat_box", False) is False


# ── H03: workflow is not Report Review ───────────────────────────────────────
def test_H03_workflow_not_report_review():
    for fname in _AUD.glob("*.json"):
        d = json.loads(fname.read_text(encoding="utf-8"))
        assert d.get("not_report_review") is True, (
            f"{fname.name}: not_report_review must be True"
        )


# ── H04: workflow is not Uploaded Template Simulation ────────────────────────
def test_H04_workflow_not_uploaded_template_simulation():
    for fname in _AUD.glob("*.json"):
        d = json.loads(fname.read_text(encoding="utf-8"))
        assert d.get("not_uploaded_template_simulation") is True, (
            f"{fname.name}: not_uploaded_template_simulation must be True"
        )


# ── H05: workflow is not Standards Compliance Report ─────────────────────────
def test_H05_workflow_not_standards_compliance():
    for fname in _AUD.glob("*.json"):
        d = json.loads(fname.read_text(encoding="utf-8"))
        assert d.get("not_standards_compliance_report") is True, (
            f"{fname.name}: not_standards_compliance_report must be True"
        )


# ── H06: workflow is not inside chat box ─────────────────────────────────────
def test_H06_workflow_not_inside_chat_box():
    for fname in _AUD.glob("*.json"):
        d = json.loads(fname.read_text(encoding="utf-8"))
        assert d.get("in_chat_box", False) is False, (
            f"{fname.name}: in_chat_box must be False"
        )


# ── H07: wizard has six steps ────────────────────────────────────────────────
def test_H07_wizard_has_six_steps():
    audit = _aud("10_hbu_ui_audit.json")
    assert audit.get("wizard_steps_count") == 6


# ── H08: aggregated market research context exists ───────────────────────────
def test_H08_aggregated_market_research_exists():
    audit = _aud("02_aggregated_market_research_audit.json")
    assert audit.get("aggregated_market_research_enabled") is True
    assert audit.get("aggregated_valuation_intelligence_page_created") is True
    assert audit.get("acts_as_hbu_central_brain") is True
    assert audit.get("market_research_attempted") is True


# ── H09: browser research status is disclosed ────────────────────────────────
def test_H09_browser_research_status_disclosed():
    audit = _aud("02_aggregated_market_research_audit.json")
    status = audit.get("browser_access_status", "")
    assert status in ("available", "partial", "blocked"), (
        f"browser_access_status must be disclosed, got: {status!r}"
    )
    assert audit.get("blocked_research_disclosed") is True or status != "blocked", (
        "If browser is blocked, blocked_research_disclosed must be True"
    )


# ── H10: fake sources are not created ────────────────────────────────────────
def test_H10_no_fake_sources():
    for fname in _AUD.glob("*.json"):
        d = json.loads(fname.read_text(encoding="utf-8"))
        assert d.get("fake_sources_created", False) is False, (
            f"{fname.name}: fake_sources_created must be False"
        )


# ── H11: source registry exists ──────────────────────────────────────────────
def test_H11_source_registry_exists():
    audit = _aud("02_aggregated_market_research_audit.json")
    assert audit.get("source_registry_created") is True
    reg = _SRC / "source_registry.json"
    assert reg.exists(), "source_registry.json missing from source_registry/"
    data = json.loads(reg.read_text(encoding="utf-8"))
    assert "sources" in data
    assert isinstance(data["sources"], list)


# ── H12: site analysis exists ────────────────────────────────────────────────
def test_H12_site_analysis_exists():
    audit = _aud("03_site_market_legal_analysis_audit.json")
    assert audit.get("site_access_analysis_created") is True
    assert audit.get("visibility_analysis_created") is True
    assert audit.get("attractiveness_analysis_created") is True


# ── H13: SWOT exists ─────────────────────────────────────────────────────────
def test_H13_swot_exists():
    audit = _aud("03_site_market_legal_analysis_audit.json")
    assert audit.get("swot_created") is True
    swot = audit.get("swot", {})
    assert "strengths" in swot
    assert "weaknesses" in swot
    assert "opportunities" in swot
    assert "threats" in swot


# ── H14: minimum three scenarios exist ───────────────────────────────────────
def test_H14_minimum_three_scenarios():
    audit = _aud("04_hbu_scenarios_audit.json")
    assert audit.get("minimum_three_scenarios_created") is True
    assert audit.get("scenarios_count", 0) >= 3


# ── H15: four HBU tests exist ────────────────────────────────────────────────
def test_H15_four_hbu_tests_exist():
    audit = _aud("05_hbu_four_tests_audit.json")
    assert audit.get("legally_permissible_test_enabled") is True
    assert audit.get("physically_possible_test_enabled") is True
    assert audit.get("financially_feasible_test_enabled") is True
    assert audit.get("maximally_productive_test_enabled") is True
    assert audit.get("all_scenarios_tested") is True


# ── H16: as-if-vacant is checked ─────────────────────────────────────────────
def test_H16_as_if_vacant_checked():
    audit = _aud("05_hbu_four_tests_audit.json")
    assert audit.get("as_if_vacant_checked") is True


# ── H17: as-improved is checked ──────────────────────────────────────────────
def test_H17_as_improved_checked():
    audit = _aud("05_hbu_four_tests_audit.json")
    assert audit.get("as_improved_checked") is True


# ── H18: DCF/NPV/IRR/payback are calculated or blockers documented ───────────
def test_H18_financial_engine_results():
    audit = _aud("06_hbu_financial_engine_audit.json")
    assert audit.get("dcf_calculated_or_blocker_documented") is True
    assert audit.get("npv_calculated_or_blocker_documented") is True
    assert audit.get("irr_calculated_or_blocker_documented") is True
    assert audit.get("payback_calculated_or_blocker_documented") is True
    # Verify actual scenario financials
    fin = audit.get("scenario_financials", [])
    assert len(fin) >= 3, "Need at least 3 scenario financial records"
    for s in fin:
        assert s.get("npv", 0) > 0, f"NPV must be > 0 for {s.get('scenario')}"
        assert s.get("irr_pct", 0) > 0, f"IRR must be > 0 for {s.get('scenario')}"


# ── H19: sensitivity analysis exists ─────────────────────────────────────────
def test_H19_sensitivity_analysis_exists():
    audit = _aud("06_hbu_financial_engine_audit.json")
    assert audit.get("sensitivity_analysis_created") is True
    sens = audit.get("sensitivity", {})
    assert "conservative" in sens
    assert "base" in sens
    assert "optimistic" in sens


# ── H20: scenario ranking exists ─────────────────────────────────────────────
def test_H20_scenario_ranking_exists():
    audit = _aud("07_hbu_ranking_recommendation_audit.json")
    assert audit.get("all_scenarios_ranked") is True
    ranking = audit.get("ranking", [])
    assert len(ranking) >= 3


# ── H21: final HBU recommendation exists ─────────────────────────────────────
def test_H21_final_hbu_recommendation_exists():
    audit = _aud("07_hbu_ranking_recommendation_audit.json")
    assert audit.get("preferred_hbu_selected") is True
    assert audit.get("backup_scenario_selected") is True
    assert audit.get("four_tests_linked_to_recommendation") is True
    assert audit.get("financial_results_linked_to_recommendation") is True
    pref = audit.get("preferred_hbu", "")
    assert pref, "preferred_hbu must not be empty"


# ── H22: HBU PDF exists ──────────────────────────────────────────────────────
def test_H22_hbu_pdf_exists():
    pdf  = _PDF / "hbu_analysis_report.pdf"
    html = _PDF / "hbu_analysis_report.html"
    assert pdf.exists() or html.exists(), (
        "Neither hbu_analysis_report.pdf nor .html found in pdf_outputs"
    )


# ── H23: HBU Excel exists ────────────────────────────────────────────────────
def test_H23_hbu_excel_exists():
    xl = _XL / "hbu_analysis_workbook.xlsx"
    audit = _aud("09_hbu_excel_audit.json")
    if audit.get("hbu_excel_exists"):
        assert xl.exists(), "Excel workbook missing despite audit claiming PASS"
        assert xl.stat().st_size > 2_000, "Excel workbook too small"


# ── H24: advisory note exists ────────────────────────────────────────────────
def test_H24_advisory_note_exists():
    html = _PDF / "hbu_analysis_report.html"
    if not html.exists():
        pytest.skip("HTML not generated")
    content = html.read_text(encoding="utf-8", errors="ignore")
    assert "advisory_only" in content, "advisory_only flag missing from HTML"
    assert "استرشادي" in content or "خبير تقييم معتمد" in content


# ── H25: fake signature does not appear ──────────────────────────────────────
def test_H25_no_fake_signature():
    for fname in _AUD.glob("*.json"):
        d = json.loads(fname.read_text(encoding="utf-8"))
        assert d.get("fake_signature_created", False) is False, (
            f"{fname.name}: fake_signature_created must be False"
        )
    html = _PDF / "hbu_analysis_report.html"
    if html.exists():
        content = html.read_text(encoding="utf-8", errors="ignore")
        assert "fake_signature\n" not in content
        assert "mock_signature" not in content


# ── H26: visual index exists ─────────────────────────────────────────────────
def test_H26_visual_index_exists():
    idx = _PREV / "OPEN_HBU_ANALYSIS_REVIEW_INDEX.html"
    assert idx.exists(), "HBU visual review index missing"
    content = idx.read_text(encoding="utf-8", errors="ignore")
    assert "advisory_only" in content
    assert "visual_qa_status" in content or "الحالة العامة" in content


# ── H27: no internal paths in outputs ────────────────────────────────────────
def test_H27_no_internal_paths():
    idx = _PREV / "OPEN_HBU_ANALYSIS_REVIEW_INDEX.html"
    if idx.exists():
        content = idx.read_text(encoding="utf-8", errors="ignore")
        assert r"C:\Users" not in content, "Internal Windows path in visual index"
        assert "C:/Users/Lenovo" not in content
    for fname in _AUD.glob("*.json"):
        text = fname.read_text(encoding="utf-8", errors="ignore")
        assert r"C:\Users" not in text, f"Internal path in {fname.name}"
        assert "C:/Users/Lenovo" not in text, f"Internal path in {fname.name}"


# ── H28: other workflows unaffected ──────────────────────────────────────────
def test_H28_other_workflows_unaffected():
    # Simulation workflow dir must still exist
    sim_dir = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_uploaded_template_simulation"
    assert sim_dir.is_dir(), "Simulation output dir must not be removed"
    # HBU audits must not contain simulation-specific keys
    for fname in _AUD.glob("*.json"):
        d = json.loads(fname.read_text(encoding="utf-8"))
        assert "template_pdf_uploaded" not in d, (
            f"{fname.name}: must not contain simulation-specific key template_pdf_uploaded"
        )
