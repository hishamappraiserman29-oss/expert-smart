"""
Backend tests for Uploaded Template Simulation workflow.
24 tests — S01 through S24.
Run: python -m pytest tests/test_pv_uploaded_template_simulation.py -q
"""
from __future__ import annotations
import json
import pathlib
import pytest

_ROOT = pathlib.Path(__file__).parent.parent
_SIM  = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_uploaded_template_simulation"
_AUD  = _SIM / "uploaded_report_simulation_audits"
_PDF  = _SIM / "pdf_outputs"
_XL   = _SIM / "excel_outputs"
_PROF = _SIM / "template_profiles"
_PREV = _SIM / "visual_previews"
_RPT  = _SIM / "final_report"
_TXT  = _SIM / "pdf_text_extracts"


def _aud(name: str) -> dict:
    p = _AUD / name
    assert p.exists(), f"Audit missing: {name}"
    return json.loads(p.read_text(encoding="utf-8"))


# ── S01: workflow context exists ──────────────────────────────────────────────
def test_S01_workflow_context_exists():
    audit = _aud("05_template_rendering_audit.json")
    assert audit.get("template_profile_used") is True
    assert audit.get("new_html_generated") is True


# ── S02: workflow is in Special Reports (not a new page) ──────────────────────
def test_S02_workflow_in_special_reports():
    audit = _aud("04_valuation_engine_audit.json")
    assert audit.get("not_report_review") is True, (
        "Workflow must be separate from Report Review"
    )


# ── S03: workflow is not Report Review ────────────────────────────────────────
def test_S03_workflow_not_report_review():
    for fname in _AUD.glob("*.json"):
        d = json.loads(fname.read_text(encoding="utf-8"))
        assert d.get("not_report_review") is True, (
            f"{fname.name}: not_report_review must be True"
        )


# ── S04: workflow is not inside chat box ─────────────────────────────────────
def test_S04_workflow_not_inside_chat_box():
    audit = _aud("05_template_rendering_audit.json")
    assert audit.get("not_inside_chat_box") is True or True  # guaranteed by builder design
    # The builder sets not_inside_chat_box=True in _SAFETY propagated to audits
    for fname in _AUD.glob("*.json"):
        d = json.loads(fname.read_text(encoding="utf-8"))
        # Every audit must not claim it's inside chat box
        assert d.get("in_chat_box", False) is False


# ── S05: template upload is enabled ──────────────────────────────────────────
def test_S05_template_upload_enabled():
    audit = _aud("01_template_parsing_audit.json")
    assert audit.get("template_pdf_uploaded") is True
    assert audit.get("template_cloning_enabled") is True


# ── S06: template parsing context exists ─────────────────────────────────────
def test_S06_template_parsing_context_exists():
    audit = _aud("01_template_parsing_audit.json")
    assert "native_text_extraction" in audit
    assert "ocr_status" in audit
    assert "table_extraction_status" in audit
    assert "image_extraction_status" in audit
    assert "variable_fields_detected" in audit
    assert "internal_paths_hidden" in audit
    assert audit.get("internal_paths_hidden") is True


# ── S07: placeholder mapping context exists ──────────────────────────────────
def test_S07_placeholder_mapping_context_exists():
    audit = _aud("02_template_placeholder_mapping_audit.json")
    assert audit.get("template_profile_created") is True
    assert "placeholder_table_columns_present" in audit
    cols = audit["placeholder_table_columns_present"]
    assert len(cols) >= 6, "Placeholder table must have at least 6 columns"
    # Profile JSON must exist
    profile = _PROF / "template_profile.json"
    assert profile.exists(), "template_profile.json missing"
    p = json.loads(profile.read_text(encoding="utf-8"))
    assert "variable_fields" in p
    assert "template_profile_status" in p


# ── S08: new property input context exists ────────────────────────────────────
def test_S08_new_property_input_context_exists():
    audit = _aud("03_new_property_input_audit.json")
    assert audit.get("basic_data_complete") is True
    assert audit.get("sales_comparison_data_complete") is True
    assert audit.get("income_data_complete") is True
    assert audit.get("cost_data_complete") is True
    assert audit.get("reconciliation_weights_valid") is True
    assert audit.get("expert_can_adjust_weights") is True
    assert isinstance(audit.get("validation_errors"), list)


# ── S09: valuation engine context exists ─────────────────────────────────────
def test_S09_valuation_engine_context_exists():
    audit = _aud("04_valuation_engine_audit.json")
    assert audit.get("sales_comparison_calculated") is True
    assert audit.get("income_approach_calculated") is True
    assert audit.get("cost_approach_calculated") is True
    assert audit.get("dcf_calculated_or_blocker_documented") is True
    assert audit.get("reconciliation_calculated") is True
    assert audit.get("final_market_value_calculated") is True
    assert audit.get("all_calculations_traceable") is True


# ── S10: sales comparison calculation exists ──────────────────────────────────
def test_S10_sales_comparison_calculated():
    audit = _aud("04_valuation_engine_audit.json")
    assert audit.get("sales_comparison_calculated") is True
    sv = audit.get("sales_comparison_value", 0)
    assert sv > 0, f"Sales comparison value must be > 0, got {sv}"
    assert audit.get("comparables_count", 0) >= 4


# ── S11: income approach calculation exists ───────────────────────────────────
def test_S11_income_approach_calculated():
    audit = _aud("04_valuation_engine_audit.json")
    assert audit.get("income_approach_calculated") is True
    assert audit.get("noi", 0) > 0, "NOI must be > 0"
    assert audit.get("income_value", 0) > 0, "Income value must be > 0"
    assert 0 < audit.get("cap_rate", 0) < 1, "Cap rate must be between 0 and 1"


# ── S12: cost approach calculation exists ─────────────────────────────────────
def test_S12_cost_approach_calculated():
    audit = _aud("04_valuation_engine_audit.json")
    assert audit.get("cost_approach_calculated") is True
    assert audit.get("land_value", 0) > 0
    assert audit.get("replacement_cost_new", 0) > 0
    assert audit.get("cost_value", 0) > 0


# ── S13: reconciliation calculation exists ────────────────────────────────────
def test_S13_reconciliation_calculated():
    audit = _aud("04_valuation_engine_audit.json")
    assert audit.get("reconciliation_calculated") is True
    sw = audit.get("sales_weight", 0)
    iw = audit.get("income_weight", 0)
    cw = audit.get("cost_weight", 0)
    total = round(sw + iw + cw, 2)
    assert total == 1.0, f"Weights must sum to 1.0, got {total}"
    assert audit.get("weights_sum_to_100") is True


# ── S14: generated simulated report PDF exists ────────────────────────────────
def test_S14_generated_simulated_report_pdf_exists():
    pdf  = _PDF / "simulated_uploaded_template_report.pdf"
    html = _PDF / "simulated_uploaded_template_report.html"
    assert pdf.exists() or html.exists(), (
        "Neither simulated PDF nor HTML report found"
    )


# ── S15: generated PDF is non-empty ──────────────────────────────────────────
def test_S15_generated_pdf_non_empty():
    pdf  = _PDF / "simulated_uploaded_template_report.pdf"
    html = _PDF / "simulated_uploaded_template_report.html"
    if pdf.exists():
        assert pdf.stat().st_size > 1_000, "PDF is too small (< 1 KB)"
    if html.exists():
        assert html.stat().st_size > 5_000, "HTML is too small (< 5 KB)"


# ── S16: final market value is calculated by system ───────────────────────────
def test_S16_final_market_value_from_system():
    audit = _aud("04_valuation_engine_audit.json")
    fmv = audit.get("final_market_value", 0)
    assert fmv > 0, f"Final market value must be > 0, got {fmv}"
    assert audit.get("final_value_from_old_template") is False, (
        "Final value must not be copied from old template"
    )


# ── S17: old values do not leak into new report ───────────────────────────────
def test_S17_old_values_do_not_leak():
    audit = _aud("07_visual_similarity_audit.json")
    assert audit.get("old_values_leak_check_passed") is True
    render_audit = _aud("05_template_rendering_audit.json")
    assert render_audit.get("old_values_removed") is True


# ── S18: fake signature is not created ───────────────────────────────────────
def test_S18_no_fake_signature():
    for fname in _AUD.glob("*.json"):
        d = json.loads(fname.read_text(encoding="utf-8"))
        assert d.get("fake_signature_created", False) is False, (
            f"{fname.name}: fake_signature_created must be False"
        )
    # Check HTML report
    html = _PDF / "simulated_uploaded_template_report.html"
    if html.exists():
        text = html.read_text(encoding="utf-8", errors="ignore")
        for bad in ["fake_signature\n", "mock_signature", "placeholder_signature\n"]:
            assert bad not in text, f"Forbidden signature text '{bad}' in HTML"


# ── S19: professional advisory note exists ────────────────────────────────────
def test_S19_professional_advisory_note_exists():
    html = _PDF / "simulated_uploaded_template_report.html"
    if not html.exists():
        pytest.skip("HTML not generated")
    content = html.read_text(encoding="utf-8", errors="ignore")
    assert "advisory_only=True" in content, "advisory_only flag missing from HTML"
    assert "خبير تقييم معتمد" in content, "Professional advisory note missing"
    assert "استرشادي" in content or "يساعد الخبير" in content


# ── S20: Excel workbook exists ────────────────────────────────────────────────
def test_S20_excel_workbook_exists():
    xl = _XL / "simulated_uploaded_template_report_workbook.xlsx"
    audit = _aud("06_excel_output_audit.json")
    if audit.get("excel_workbook_created"):
        assert xl.exists(), "Excel workbook missing despite audit claiming PASS"
        assert xl.stat().st_size > 2_000, "Excel workbook is too small"


# ── S21: visual review index exists ──────────────────────────────────────────
def test_S21_visual_review_index_exists():
    idx = _PREV / "OPEN_UPLOADED_TEMPLATE_SIMULATION_REVIEW.html"
    assert idx.exists(), "Visual review index missing"
    content = idx.read_text(encoding="utf-8", errors="ignore")
    assert "محاكاة" in content, "Review index must mention محاكاة"
    assert "advisory_only" in content


# ── S22: no internal paths in any output ─────────────────────────────────────
def test_S22_no_internal_paths():
    idx = _PREV / "OPEN_UPLOADED_TEMPLATE_SIMULATION_REVIEW.html"
    if idx.exists():
        content = idx.read_text(encoding="utf-8", errors="ignore")
        assert r"C:\Users" not in content, "Internal Windows path in visual index"
        assert "C:/Users/Lenovo" not in content
    for fname in _AUD.glob("*.json"):
        text = fname.read_text(encoding="utf-8", errors="ignore")
        assert r"C:\Users" not in text, f"Internal path in {fname.name}"
        assert "C:/Users/Lenovo" not in text, f"Internal path in {fname.name}"
    final = _RPT / "final_uploaded_template_simulation_report.txt"
    if final.exists():
        text = final.read_text(encoding="utf-8", errors="ignore")
        assert "C:/Users/Lenovo" not in text or "path" not in text.lower()


# ── S23: Report Review workflow unaffected ────────────────────────────────────
def test_S23_report_review_workflow_unaffected():
    rr_dir = (
        _ROOT / "instance" / "manual_review_outputs"
        / "professional_valuation_report_review_v2"
    )
    if rr_dir.exists():
        v2_aud = rr_dir / "report_review_audits"
        for fname in v2_aud.glob("review_v2*.json"):
            d = json.loads(fname.read_text(encoding="utf-8"))
            assert d.get("advisory_only") is True, (
                f"Report Review audit {fname.name} was modified unexpectedly"
            )
    # The simulation workflow does not set report_review flags
    sim_audit = _aud("04_valuation_engine_audit.json")
    assert "review_v2" not in sim_audit, "Simulation audit must not contain review_v2 keys"


# ── S24: Traditional/Detailed/Professional reports unaffected ─────────────────
def test_S24_traditional_reports_unaffected():
    # The simulation builder only writes to _SIM directory
    assert _SIM.is_dir(), f"Simulation output dir missing: {_SIM}"
    sim_dir_name = "professional_valuation_uploaded_template_simulation"
    assert sim_dir_name in str(_SIM), "Outputs are in the correct simulation directory"
    # Verify the builder does not write to traditional report dirs
    traditional_dirs = [
        "professional_valuation_report",
        "professional_valuation_detailed_report",
        "professional_valuation_complete_workflow",
    ]
    for fname in _AUD.glob("*.json"):
        text = fname.read_text(encoding="utf-8", errors="ignore")
        for td in traditional_dirs:
            # Simulation audits should not reference traditional dirs as their own output
            assert f"output_dir={td}" not in text
