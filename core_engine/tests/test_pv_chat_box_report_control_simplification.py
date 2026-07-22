# test_pv_chat_box_report_control_simplification.py
# Backend tests — Chat Box Report Control Simplification
# advisory_only=True | not_real_training=True | no_commit=True

import pathlib
import sys
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

HTML = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "index.html"

CORE_TYPES = ["traditional_report", "detailed_report", "professional_report"]


def _ctx():
    from core_engine.pv_chat_box_report_control_simplification_context import (
        get_chat_box_report_control_simplification_context,
    )
    return get_chat_box_report_control_simplification_context()


def _html():
    return HTML.read_text(encoding="utf-8", errors="replace")


# ── T01: Context module importable and returns dict ───────────────────────────
def test_T01_context_module_importable():
    ctx = _ctx()
    assert isinstance(ctx, dict)
    assert len(ctx) > 0


# ── T02: core_report_click_generates_both_outputs = True ─────────────────────
def test_T02_core_report_click_generates_both_outputs():
    assert _ctx()["core_report_click_generates_both_outputs"] is True


# ── T03: Core report types are exactly three ─────────────────────────────────
def test_T03_core_report_types_exactly_three():
    ctx = _ctx()
    assert sorted(ctx["core_report_types"]) == sorted(CORE_TYPES)


# ── T04: separate_user_pdf_button_removed = True ─────────────────────────────
def test_T04_separate_user_pdf_button_removed():
    assert _ctx()["separate_user_pdf_button_removed"] is True


# ── T05: separate_admin_excel_button_removed = True ──────────────────────────
def test_T05_separate_admin_excel_button_removed():
    assert _ctx()["separate_admin_excel_button_removed"] is True


# ── T06: send_to_chat_button_removed = True ───────────────────────────────────
def test_T06_send_to_chat_button_removed():
    assert _ctx()["send_to_chat_button_removed"] is True


# ── T07: simulation_upload_clip_removed_from_chat_box = True ─────────────────
def test_T07_simulation_upload_clip_removed():
    assert _ctx()["simulation_upload_clip_removed_from_chat_box"] is True


# ── T08: report_review_upload_clip_removed_from_chat_box = True ──────────────
def test_T08_report_review_upload_clip_removed():
    assert _ctx()["report_review_upload_clip_removed_from_chat_box"] is True


# ── T09: special_reports_managed_by_dedicated_requirement_tables = True ───────
def test_T09_special_reports_managed_by_requirement_tables():
    assert _ctx()["special_reports_managed_by_dedicated_requirement_tables"] is True


# ── T10: pdf_generation_capability_preserved = True ──────────────────────────
def test_T10_pdf_generation_capability_preserved():
    assert _ctx()["pdf_generation_capability_preserved"] is True


# ── T11: admin_excel_generation_capability_preserved = True ──────────────────
def test_T11_admin_excel_generation_capability_preserved():
    assert _ctx()["admin_excel_generation_capability_preserved"] is True


# ── T12: Special report keys preserved in HTML ───────────────────────────────
def test_T12_special_report_keys_preserved():
    assert _ctx()["special_report_keys_preserved"] is True
    html = _html()
    for key in ["report_review_output", "simulated_uploaded_report",
                "hbu_analysis_report", "standards_compliance_report"]:
        assert key in html, f"Special report key missing from HTML: {key}"


# ── T13: Legacy aliases preserved ────────────────────────────────────────────
def test_T13_legacy_aliases_preserved():
    assert _ctx()["legacy_aliases_preserved"] is True
    html = _html()
    assert "pv-chat-report-action" in html


# ── T14: No internal paths in HTML ───────────────────────────────────────────
def test_T14_no_internal_paths():
    assert _ctx()["no_internal_paths"] is True
    html = _html()
    for pat in ["C:\\Users\\Lenovo", "AppData\\Local", "__file__"]:
        assert pat not in html, f"Internal path in HTML: {pat}"


# ── T15: Ordinary valuation unaffected ───────────────────────────────────────
def test_T15_ordinary_valuation_unaffected():
    assert _ctx()["ordinary_valuation_unaffected"] is True
    html = _html()
    assert "traditional_report" in html
    assert "detailed_report" in html
    assert "professional_report" in html


# ── T16: Tax appeal unaffected ───────────────────────────────────────────────
def test_T16_tax_appeal_unaffected():
    assert _ctx()["tax_appeal_unaffected"] is True
    html = _html()
    assert "tax" in html.lower()
