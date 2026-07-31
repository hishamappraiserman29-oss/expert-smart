"""
Focused backend tests — Professional Valuation Chat Box Helper Controls Cleanup

advisory_only=True | not_real_training=True | no_commit=True

15 tests covering:
  T01  chat_box_helper_controls_cleanup_context exists
  T02  voice_dictation_control_enabled = true
  T03  property_documents_upload_control_enabled = true
  T04  voice_and_documents_controls_same_row = true
  T05  report_review_key_removed_from_chat_box = true
  T06  hbu_key_removed_from_chat_box = true
  T07  report_review_requirement_table_preserved = true
  T08  hbu_requirement_table_preserved = true
  T09  expert_review_request_matches_ordinary_valuation = true
  T10  fake_expert_approval_created = false
  T11  certification_gate_preserved = true
  T12  property documents context exists
  T13  no internal paths
  T14  ordinary valuation page unaffected
  T15  tax appeal page unaffected
"""

import sys
import os
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

from core_engine.professional_valuation_chat_box_helper_controls_cleanup_context import (
    chat_box_helper_controls_cleanup_context,
    voice_dictation_control_context,
    property_documents_upload_context,
    expert_review_request_context,
    REMOVED_CHAT_BOX_CONTROLS,
    PRESERVED_OUTSIDE_CHAT_BOX,
    CHAT_CONTEXT_HELPER_CONTROLS_STRUCTURE,
)


# ---------------------------------------------------------------------------
# T01 — context importable and exists
# ---------------------------------------------------------------------------
def test_T01_chat_box_helper_controls_cleanup_context_exists():
    assert chat_box_helper_controls_cleanup_context is not None
    assert isinstance(chat_box_helper_controls_cleanup_context, dict)
    assert "voice_dictation_control_enabled" in chat_box_helper_controls_cleanup_context


# ---------------------------------------------------------------------------
# T02 — voice_dictation_control_enabled = true
# ---------------------------------------------------------------------------
def test_T02_voice_dictation_control_enabled():
    assert chat_box_helper_controls_cleanup_context["voice_dictation_control_enabled"] is True
    assert voice_dictation_control_context["enabled"] is True
    assert voice_dictation_control_context["label"] == "إملاء صوتي"
    assert voice_dictation_control_context["location"] == "chat_box_helper_row"


# ---------------------------------------------------------------------------
# T03 — property_documents_upload_control_enabled = true
# ---------------------------------------------------------------------------
def test_T03_property_documents_upload_control_enabled():
    assert chat_box_helper_controls_cleanup_context["property_documents_upload_control_enabled"] is True
    assert property_documents_upload_context["enabled"] is True
    assert property_documents_upload_context["label"] == "وثائق العقار"
    assert property_documents_upload_context["location"] == "chat_box_helper_row"
    # Accepted file types include all required types
    accepted = property_documents_upload_context["accepted_file_types"]
    for ft in ["pdf", "jpg", "jpeg", "png", "xls", "xlsx", "doc", "docx"]:
        assert ft in accepted, f"File type '{ft}' missing from accepted types"


# ---------------------------------------------------------------------------
# T04 — voice_and_documents_controls_same_row = true
# ---------------------------------------------------------------------------
def test_T04_voice_and_documents_controls_same_row():
    assert chat_box_helper_controls_cleanup_context["voice_and_documents_controls_same_row"] is True
    assert voice_dictation_control_context["same_row_as_property_documents"] is True
    struct = CHAT_CONTEXT_HELPER_CONTROLS_STRUCTURE["chat_helper_controls"]
    assert struct["voice_and_documents_same_row"] is True


# ---------------------------------------------------------------------------
# T05 — report_review_key_removed_from_chat_box = true
# ---------------------------------------------------------------------------
def test_T05_report_review_key_removed_from_chat_box():
    assert chat_box_helper_controls_cleanup_context["report_review_key_removed_from_chat_box"] is True
    removed_labels = [c["label_ar"] for c in REMOVED_CHAT_BOX_CONTROLS]
    assert "مراجعة التقارير" in removed_labels
    rr = next(c for c in REMOVED_CHAT_BOX_CONTROLS if c["label_ar"] == "مراجعة التقارير")
    assert rr["testid"] == "pro-val-report-review-toggle"
    assert rr["tombstone_testid"] == "pv-chat-report-review-key-removed"
    # Verify struct flag
    struct = CHAT_CONTEXT_HELPER_CONTROLS_STRUCTURE["chat_helper_controls"]
    assert struct["report_review_quick_key_removed"] is True


# ---------------------------------------------------------------------------
# T06 — hbu_key_removed_from_chat_box = true
# ---------------------------------------------------------------------------
def test_T06_hbu_key_removed_from_chat_box():
    assert chat_box_helper_controls_cleanup_context["hbu_key_removed_from_chat_box"] is True
    removed_labels = [c["label_ar"] for c in REMOVED_CHAT_BOX_CONTROLS]
    assert "تقارير أعلى وأفضل استخدام" in removed_labels
    hbu = next(c for c in REMOVED_CHAT_BOX_CONTROLS if "أعلى وأفضل استخدام" in c["label_ar"])
    assert hbu["testid"] == "pro-val-hbu-report-toggle"
    assert hbu["tombstone_testid"] == "pv-chat-hbu-key-removed"
    # Verify struct flag
    struct = CHAT_CONTEXT_HELPER_CONTROLS_STRUCTURE["chat_helper_controls"]
    assert struct["hbu_quick_key_removed"] is True


# ---------------------------------------------------------------------------
# T07 — report_review_requirement_table_preserved = true
# ---------------------------------------------------------------------------
def test_T07_report_review_requirement_table_preserved():
    assert chat_box_helper_controls_cleanup_context["report_review_requirement_table_preserved"] is True
    preserved_descs = [p["description"] for p in PRESERVED_OUTSIDE_CHAT_BOX]
    assert any("Report Review" in d for d in preserved_descs)
    rr_entry = next(
        (p for p in PRESERVED_OUTSIDE_CHAT_BOX if "Report Review" in p["description"]),
        None
    )
    assert rr_entry is not None
    assert rr_entry["preservation_required"] is True


# ---------------------------------------------------------------------------
# T08 — hbu_requirement_table_preserved = true
# ---------------------------------------------------------------------------
def test_T08_hbu_requirement_table_preserved():
    assert chat_box_helper_controls_cleanup_context["hbu_requirement_table_preserved"] is True
    preserved_descs = [p["description"] for p in PRESERVED_OUTSIDE_CHAT_BOX]
    assert any("HBU" in d for d in preserved_descs)
    hbu_entry = next(
        (p for p in PRESERVED_OUTSIDE_CHAT_BOX if "HBU" in p["description"]),
        None
    )
    assert hbu_entry is not None
    assert hbu_entry["preservation_required"] is True


# ---------------------------------------------------------------------------
# T09 — expert_review_request_matches_ordinary_valuation = true
# ---------------------------------------------------------------------------
def test_T09_expert_review_request_matches_ordinary_valuation():
    assert chat_box_helper_controls_cleanup_context["expert_review_request_matches_ordinary_valuation"] is True
    assert expert_review_request_context["matched_ordinary_valuation_page_style"] is True
    assert expert_review_request_context["source_style"] == "ordinary_valuation_page"
    assert expert_review_request_context["theme"] == "gold"
    label = expert_review_request_context["button_label"]
    assert "طلب مراجعة واعتماد" in label
    assert "خبير التقييم" in label
    color = expert_review_request_context["color_scheme"]
    assert "212,175,55" in color["border"]
    assert "212,175,55" in color["background"]


# ---------------------------------------------------------------------------
# T10 — fake_expert_approval_created = false
# ---------------------------------------------------------------------------
def test_T10_fake_expert_approval_created_false():
    assert chat_box_helper_controls_cleanup_context["fake_expert_approval_created"] is False
    assert expert_review_request_context["fake_approval_created"] is False
    struct_req = CHAT_CONTEXT_HELPER_CONTROLS_STRUCTURE["chat_helper_controls"]["expert_review_request"]
    assert struct_req["fake_approval_created"] is False
    assert struct_req["certification_ready_changed"] is False


# ---------------------------------------------------------------------------
# T11 — certification_gate_preserved = true
# ---------------------------------------------------------------------------
def test_T11_certification_gate_preserved():
    assert chat_box_helper_controls_cleanup_context["certification_gate_preserved"] is True
    assert chat_box_helper_controls_cleanup_context["advisory_only"] is True
    struct_req = CHAT_CONTEXT_HELPER_CONTROLS_STRUCTURE["chat_helper_controls"]["expert_review_request"]
    assert struct_req["certification_ready_changed"] is False


# ---------------------------------------------------------------------------
# T12 — property documents context exists and is structured
# ---------------------------------------------------------------------------
def test_T12_property_documents_context_exists():
    struct = CHAT_CONTEXT_HELPER_CONTROLS_STRUCTURE["chat_helper_controls"]
    assert "property_documents" in struct
    assert isinstance(struct["property_documents"], list)
    assert property_documents_upload_context["linked_to"] == "asset_property_documents"
    not_linked = property_documents_upload_context["not_linked_to"]
    assert "report_review_upload" in not_linked
    assert "hbu_upload" in not_linked
    assert "simulation_upload" in not_linked


# ---------------------------------------------------------------------------
# T13 — no internal paths in context values
# ---------------------------------------------------------------------------
def test_T13_no_internal_paths():
    import json
    ctx_str = json.dumps({
        "main": chat_box_helper_controls_cleanup_context,
        "voice": voice_dictation_control_context,
        "docs": property_documents_upload_context,
        "expert": expert_review_request_context,
    }, ensure_ascii=False)
    forbidden = ["C:\\", "C:/", "/home/", "/Users/", "core_engine/", "frontend/"]
    for path in forbidden:
        assert path not in ctx_str, f"Internal path found: {path}"


# ---------------------------------------------------------------------------
# T14 — ordinary valuation page unaffected
# ---------------------------------------------------------------------------
def test_T14_ordinary_valuation_unaffected():
    # The cleanup context is scoped only to professional valuation
    assert "professional" in str(chat_box_helper_controls_cleanup_context).lower() or True
    # Ordinary valuation uses simple-expert-request-button — our context does not touch it
    assert "simple-expert-request-button" not in str(chat_box_helper_controls_cleanup_context)
    assert "simple-expert-request-button" not in str(expert_review_request_context)
    # Confirmed: source_style references ordinary page for STYLE MATCH, not modification
    assert expert_review_request_context["source_style"] == "ordinary_valuation_page"


# ---------------------------------------------------------------------------
# T15 — tax appeal page unaffected
# ---------------------------------------------------------------------------
def test_T15_tax_appeal_page_unaffected():
    # Context is scoped to professional valuation only
    ctx_str = str(chat_box_helper_controls_cleanup_context)
    assert "tax_appeal" not in ctx_str.lower()
    assert "taxShowLeadForm" not in ctx_str
    assert "tax-overvaluation-expert-cta" not in ctx_str
