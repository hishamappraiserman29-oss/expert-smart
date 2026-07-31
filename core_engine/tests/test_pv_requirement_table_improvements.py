# core_engine/tests/test_pv_requirement_table_improvements.py
# Phase RTI — Requirement Table Improvements backend tests (21 tests)
# advisory_only=True, not_real_training=True

import sys
import os
import re

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


# ── Import context under test ─────────────────────────────────────────────────
from core_engine.requirement_table_improvements_context import (
    requirement_table_improvements_context as RTI,
)


# ── RTI001 — Context object exists ────────────────────────────────────────────
def test_RTI001_context_exists():
    assert RTI is not None
    assert isinstance(RTI, dict)


# ── RTI002 — document_upload_clips_enabled = True ──────────���──────────────────
def test_RTI002_document_upload_clips_enabled():
    assert RTI["document_upload_clips_enabled"] is True


# ── RTI003 — file_upload_fields_use_paperclip = True ─��───────────────────────
def test_RTI003_file_upload_fields_use_paperclip():
    assert RTI["file_upload_fields_use_paperclip"] is True


# ── RTI004 �� accepted_file_types includes pdf, jpg, png, xls, xlsx ────────────
def test_RTI004_accepted_file_types():
    types = RTI["accepted_file_types"]
    for t in ("pdf", "jpg", "png", "xls", "xlsx"):
        assert t in types, f"Missing file type: {t}"


# ── RTI005 — accepted_file_types includes doc, docx ──────────────────────────
def test_RTI005_accepted_file_types_doc():
    types = RTI["accepted_file_types"]
    assert "doc" in types
    assert "docx" in types


# ── RTI006 — requirement_priority_coloring_enabled = True ────────────────��───
def test_RTI006_requirement_priority_coloring_enabled():
    assert RTI["requirement_priority_coloring_enabled"] is True


# ── RTI007 — four priority levels present ───────────���─────────────────────────
def test_RTI007_four_priority_levels():
    levels = RTI["requirement_priority_levels"]
    assert len(levels) == 4
    for expected in ("minimum_required", "required_if_applicable", "recommended", "optional"):
        assert expected in levels


# ─��� RTI008 — minimum_report_requirements_context_enabled = True ───────────────
def test_RTI008_minimum_report_requirements_context_enabled():
    assert RTI["minimum_report_requirements_context_enabled"] is True


# ���─ RTI009 — draft_report_reviewable_logic structure ─────────────────────────
def test_RTI009_draft_reviewable_logic_structure():
    logic = RTI["draft_report_reviewable_logic"]
    assert "required_completed" in logic
    assert "minimum_required" in logic["required_completed"]
    assert "optional_do_not_block" in logic
    assert "recommended" in logic["optional_do_not_block"]
    assert "optional" in logic["optional_do_not_block"]


# ── RTI010 — optional fields do not block reviewable draft status ─────────────
def test_RTI010_optional_do_not_block_draft():
    logic = RTI["draft_report_reviewable_logic"]
    assert "recommended" in logic["optional_do_not_block"]
    assert "optional" in logic["optional_do_not_block"]
    assert logic["final_certification_claim"] is False
    assert logic["expert_review_required"] is True


# ��─ RTI011 — adjustment_factors_duplicate_purpose_removed = True ────────────��─
def test_RTI011_adjustment_factors_duplicate_purpose_removed():
    assert RTI["adjustment_factors_duplicate_purpose_removed"] is True


# ��─ RTI012 — adjustment_factors_purpose_source = section3.assignment_purpose ──
def test_RTI012_adjustment_factors_purpose_source():
    assert RTI["adjustment_factors_purpose_source"] == "section3.assignment_purpose"


# ── RTI013 — legacy purpose aliases preserved ──────────���──────────────────────
def test_RTI013_legacy_aliases_preserved():
    aliases = RTI["adjustment_factors_purpose_aliases"]
    assert aliases["adjustment_purpose"] == "assignment_purpose"
    assert aliases["adjustment_valuation_purpose"] == "assignment_purpose"
    assert aliases["valuation_purpose_for_adjustments"] == "assignment_purpose"
    assert aliases["purpose_in_adjustment_box"] == "assignment_purpose"


# ── RTI014 — adjustment_factors_context schema ────��───────────────────────────
def test_RTI014_adjustment_factors_context_schema():
    ctx = RTI["adjustment_factors_context"]
    assert ctx["editable_duplicate_removed"] is True
    assert ctx["source_of_truth"] == "section3.assignment_purpose"
    assert ctx["read_only_summary_visible"] is True
    assert ctx["legacy_aliases_preserved"] is True
    assert ctx["duplicate_purpose_selectors_count"] == 0
    assert ctx["adjustment_factors_use_section3_purpose"] is True


# ── RTI015 — common asset tables preserved ────────────────��───────────────────
def test_RTI015_common_asset_tables_preserved():
    assert RTI["common_asset_tables_preserved"] is True


# ── RTI016 — uncommon asset tables preserved ─────────────────────────────────
def test_RTI016_uncommon_asset_tables_preserved():
    assert RTI["uncommon_asset_tables_preserved"] is True


# ── RTI017 — hotel/resort old-style layout preserved ─────────────────────────
def test_RTI017_hotel_resort_preserved():
    assert RTI["hotel_resort_golden_reference_preserved"] is True


# ── RTI018 — repeatable building components preserved ────────────────────────
def test_RTI018_repeatable_building_components_preserved():
    assert RTI["repeatable_building_components_preserved"] is True


# ── RTI019 — deleted_old_requirements = [] ───��────────────────────────────────
def test_RTI019_deleted_old_requirements_empty():
    assert RTI["deleted_old_requirements"] == []


# ── RTI020 — deleted_old_options = [] ─────────────────────────────────────────
def test_RTI020_deleted_old_options_empty():
    assert RTI["deleted_old_options"] == []


# ── RTI021 — no internal paths in context values ──��──────────────────────────
def test_RTI021_no_internal_paths_in_context():
    path_pattern = re.compile(r'[A-Za-z]:\\|/home/|/Users/|C:\\Users')
    def _check(obj, path=''):
        if isinstance(obj, str):
            assert not path_pattern.search(obj), f"Internal path at {path}: {obj!r}"
        elif isinstance(obj, dict):
            for k, v in obj.items():
                _check(v, path + '.' + k)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                _check(v, path + '[' + str(i) + ']')
    _check(RTI)
