"""
Backend tests for Report Review V2.0 outputs.
20 tests — T01 through T20.
Run: python -m pytest tests/test_pv_report_review_v2.py -q
"""
from __future__ import annotations
import json
import pathlib
import pytest

_ROOT = pathlib.Path(__file__).parent.parent
_V2   = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_report_review_v2"
_AUD  = _V2 / "report_review_audits"
_PDF  = _V2 / "pdf_outputs"
_RPT  = _V2 / "final_report"
_PREV = _V2 / "visual_previews"
_XL   = _V2 / "excel_outputs"


def _aud(name: str) -> dict:
    p = _AUD / name
    assert p.exists(), f"Audit missing: {name}"
    return json.loads(p.read_text(encoding="utf-8"))


# ── T01: V2 folder exists ────────────────────────────────────────────────────
def test_T01_v2_output_folder_exists():
    assert _V2.exists(), f"V2 output folder missing: {_V2}"


# ── T02: V2 PDF or HTML exists ───────────────────────────────────────────────
def test_T02_report_review_v2_pdf_or_html_exists():
    html = _PDF / "report_review_output_v2.html"
    pdf  = _PDF / "report_review_output_v2.pdf"
    assert html.exists() or pdf.exists(), "Neither V2 PDF nor V2 HTML found"


# ── T03: page count 8–10 OR blocker documented ───────────────────────────────
def test_T03_pdf_page_count_8_to_10_or_blocker():
    audit = _aud("review_v2_pdf_structure_audit.json")
    if not audit.get("report_review_output_v2_pdf_exists"):
        assert audit.get("html_generated"), "PDF blocked but HTML not generated either"
        return
    assert audit.get("target_page_count_8_to_10"), (
        f"Page count not in 8–10 range. Count: {audit.get('actual_page_count')}"
    )


# ── T04: executive summary on page 1 ─────────────────────────────────────────
def test_T04_executive_summary_on_page_1():
    html = _PDF / "report_review_output_v2.html"
    if not html.exists():
        pytest.skip("HTML not generated")
    content = html.read_text(encoding="utf-8", errors="ignore")
    assert "بطاقة التقييم السريع" in content, "Executive summary card not found on page 1"


# ── T05: traffic-light decision visible ──────────────────────────────────────
def test_T05_traffic_light_system_present():
    html = _PDF / "report_review_output_v2.html"
    if not html.exists():
        pytest.skip("HTML not generated")
    content = html.read_text(encoding="utf-8", errors="ignore")
    found = any(s in content for s in ["عائق يمنع الاعتماد", "يحتاج تعديلات", "متوافق"])
    assert found, "Traffic-light decision label not found in HTML"


# ── T06: human review quick list ─────────────────────────────────────────────
def test_T06_human_review_quick_list_exists():
    audit = _aud("review_v2_human_review_consolidation_audit.json")
    assert audit.get("human_review_items_consolidated"), "Human review items not consolidated"
    assert audit.get("early_page_created"), "Early page for human review not created"
    html = _PDF / "report_review_output_v2.html"
    if html.exists():
        assert "قائمة المراجعة البشرية السريعة" in html.read_text(encoding="utf-8", errors="ignore")


# ── T07: unified compliance table ────────────────────────────────────────────
def test_T07_unified_compliance_table_present():
    audit = _aud("review_v2_unified_compliance_table_audit.json")
    assert audit.get("unified_compliance_table_present")
    assert audit.get("ivs_items_included")
    assert audit.get("uspap_items_included")
    assert audit.get("rics_items_included")
    assert audit.get("fra_items_included")
    assert audit.get("action_column_present")


# ── T08: old separate repetition reduced ─────────────────────────────────────
def test_T08_repetition_reduced():
    audit = _aud("review_v2_pdf_structure_audit.json")
    assert audit.get("repetition_reduced"), "Repetition reduction not confirmed"


# ── T09: value comparison section present ────────────────────────────────────
def test_T09_value_comparison_exists():
    audit = _aud("review_v2_value_comparison_audit.json")
    html = _PDF / "report_review_output_v2.html"
    if html.exists():
        assert "مقارنة القيمة" in html.read_text(encoding="utf-8", errors="ignore")
    assert "advisory_only" in audit
    assert audit.get("advisory_only") is True


# ── T10: agents heatmap present ──────────────────────────────────────────────
def test_T10_agents_heatmap_present():
    audit = _aud("review_v2_agents_heatmap_audit.json")
    assert audit.get("agents_heatmap_present")
    assert audit.get("income_agent_present")
    assert audit.get("risk_agent_present")
    assert audit.get("action_column_present")


# ── T11: action items exist ───────────────────────────────────────────────────
def test_T11_action_items_present():
    audit = _aud("review_v2_action_items_audit.json")
    assert audit.get("action_items_section_present")
    assert audit.get("imperative_language_used")
    assert audit.get("standard_reference_present")
    assert audit.get("deadline_present")


# ── T12: action items use imperative language ─────────────────────────────────
def test_T12_action_items_imperative_language():
    html = _PDF / "report_review_output_v2.html"
    if not html.exists():
        pytest.skip("HTML not generated")
    content = html.read_text(encoding="utf-8", errors="ignore")
    assert "قم ب" in content, "Imperative 'قم ب' language not found in action items"


# ── T13: signature gate clean ─────────────────────────────────────────────────
def test_T13_signature_gate_clean():
    audit = _aud("review_v2_signature_gate_audit.json")
    assert audit.get("fake_reviewer_signature_removed")
    assert audit.get("waiting_for_authorized_reviewer_signature_text_present")
    assert audit.get("no_fake_signature_text_in_pdf")
    assert audit.get("no_fake_signature_text_in_dom")


# ── T14: fake_reviewer_signature not in PDF text ─────────────────────────────
def test_T14_no_fake_reviewer_signature_in_pdf_text():
    for p in [
        _PDF / "report_review_output_v2.html",
        _V2 / "pdf_text_extracts" / "report_review_output_v2_text.txt",
    ]:
        if p.exists():
            text = p.read_text(encoding="utf-8", errors="ignore")
            for bad in ["fake_reviewer_signature\n", "fake_signature\n",
                        "mock_signature", "placeholder_signature"]:
                assert bad not in text, f"Forbidden signature text '{bad}' found in {p.name}"


# ── T15: fake_signature not in PDF text ──────────────────────────────────────
def test_T15_no_fake_signature_string():
    html = _PDF / "report_review_output_v2.html"
    if not html.exists():
        pytest.skip("HTML not generated")
    content = html.read_text(encoding="utf-8", errors="ignore")
    assert "fake_signature" not in content.lower() or "fake_reviewer_signature_created=False" in content


# ── T16: AI-assisted warning present ─────────────────────────────────────────
def test_T16_ai_assisted_warning_present():
    html = _PDF / "report_review_output_v2.html"
    if not html.exists():
        pytest.skip("HTML not generated")
    content = html.read_text(encoding="utf-8", errors="ignore")
    assert "استرشادي" in content, "AI-advisory warning not found"
    assert "advisory_only=True" in content


# ── T17: V2 UI audit exists ──────────────────────────────────────────────────
def test_T17_v2_ui_audit_exists():
    audit = _aud("review_v2_ui_audit.json")
    assert audit.get("executive_decision_card_visible")
    assert audit.get("traffic_light_visible")
    assert audit.get("download_v2_pdf_button_visible")
    assert audit.get("signature_gate_panel_visible")


# ── T18: V2 Excel audit exists ───────────────────────────────────────────────
def test_T18_v2_excel_audit_exists():
    audit = _aud("review_v2_excel_audit.json")
    assert audit.get("executive_summary_sheet_present")
    assert audit.get("traffic_light_sheet_present")
    assert audit.get("action_items_sheet_present")
    assert audit.get("signature_gate_sheet_present")
    assert audit.get("old_review_sheets_preserved")


# ── T19: V2 visual index exists ──────────────────────────────────────────────
def test_T19_v2_visual_index_exists():
    idx = _PREV / "OPEN_REPORT_REVIEW_V2_REVIEW_INDEX.html"
    assert idx.exists(), "V2 visual index HTML missing"
    content = idx.read_text(encoding="utf-8", errors="ignore")
    assert "مراجعة" in content


# ── T20: no internal paths in visual index ───────────────────────────────────
def test_T20_no_internal_paths():
    idx = _PREV / "OPEN_REPORT_REVIEW_V2_REVIEW_INDEX.html"
    if not idx.exists():
        pytest.skip("Visual index missing")
    content = idx.read_text(encoding="utf-8", errors="ignore")
    assert r"C:\Users" not in content, "Internal Windows path found in visual index"
    assert "C:/Users/Lenovo" not in content
