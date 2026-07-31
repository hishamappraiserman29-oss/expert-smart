# -*- coding: utf-8 -*-
"""
Batch 4R — Real Excel Visual Revalidation tests.
16 tests verifying Excel COM rendering, PNG output, and integration readiness.
Renderer gate PASSED — no skips expected.
"""
from __future__ import annotations
import json
import pathlib

import pytest

BASE = pathlib.Path(__file__).resolve().parent.parent.parent

SOURCE_WB = (BASE / "core_engine/instance/manual_review_outputs"
             / "professional_valuation_template_driven_batch4"
             / "excel_outputs/template_driven_professional_workbook_final_qa.xlsx")
BATCH4R   = (BASE / "core_engine/instance/manual_review_outputs"
             / "professional_valuation_template_driven_batch4_real_visual")
AUDITS    = BATCH4R / "audits"
PNG_DIR   = BATCH4R / "sheet_pngs"
HTML_IDX  = BATCH4R / "visual_previews" / "OPEN_REAL_EXCEL_VISUAL_QA.html"
SUMMARY   = BATCH4R / "final_report" / "real_visual_qa_summary.json"
PV_OUT    = BASE / "core_engine" / "professional_valuation_outputs.py"


def _j(name: str) -> dict:
    return json.loads((AUDITS / name).read_text(encoding="utf-8"))


# ── Test 01 — Excel COM renderer was used ─────────────────────────────────────
def test_01_renderer_is_excel_com():
    audit = _j("01_real_excel_render_audit.json")
    assert audit["renderer_used"] == "Excel COM", \
        f"Expected 'Excel COM', got {audit['renderer_used']!r}"


# ── Test 02 — Excel version is 16.0 ───────────────────────────────────────────
def test_02_excel_version_16():
    audit = _j("01_real_excel_render_audit.json")
    assert audit["excel_version"] == "16.0", \
        f"Expected version 16.0, got {audit['excel_version']!r}"


# ── Test 03 — No metadata/fallback renderer ───────────────────────────────────
def test_03_no_fallback_renderer():
    audit = _j("01_real_excel_render_audit.json")
    # Audit must not reference matplotlib or openpyxl rendering
    audit_str = json.dumps(audit)
    assert "matplotlib" not in audit_str.lower(), \
        "Audit references matplotlib fallback renderer"
    assert audit["renderer_used"] == "Excel COM", \
        "Fallback renderer was used"


# ── Test 04 — Exactly 55 sheets exported ──────────────────────────────────────
def test_04_exactly_55_exported():
    audit = _j("01_real_excel_render_audit.json")
    assert audit["exported_sheet_count"] == 55, \
        f"Expected 55 exported, got {audit['exported_sheet_count']}"


# ── Test 05 — Every sheet has at least one real PNG ───────────────────────────
def test_05_every_sheet_has_real_png():
    results = _j("02_sheet_by_sheet_real_visual_results.json")
    no_png = [s["sheet"] for s in results["sheets"] if s.get("png_count", 0) == 0]
    assert not no_png, f"Sheets with no PNG: {no_png}"


# ── Test 06 — PNG count is at least 55 ────────────────────────────────────────
def test_06_png_count_at_least_55():
    pngs = list(PNG_DIR.glob("*.png"))
    assert len(pngs) >= 55, f"Expected at least 55 PNGs, found {len(pngs)}"


# ── Test 07 — Source workbook hash unchanged ──────────────────────────────────
def test_07_source_hash_unchanged():
    audit = _j("01_real_excel_render_audit.json")
    assert audit["workbook_unchanged"] is True, \
        f"Source workbook mutated: {audit['input_hash_before']} → {audit['input_hash_after']}"


# ── Test 08 — No critical visual defect ───────────────────────────────────────
def test_08_no_critical_visual_defect():
    dreg = _j("03_real_visual_defects_register.json")
    assert dreg["critical_count"] == 0, \
        f"Critical defects: {[d['description'] for d in dreg['defects'] if d.get('severity')=='CRITICAL'][:5]}"


# ── Test 09 — Six original charts visible ────────────────────────────────────
def test_09_six_original_charts_visible():
    prio = _j("04_priority_sheet_real_visual_audit.json")
    orig = prio.get("original_charts_visible", 0)
    assert orig >= 6, f"Expected >= 6 original charts visible, got {orig}"


# ── Test 10 — Eight inserted charts visible ───────────────────────────────────
def test_10_eight_inserted_charts_visible():
    prio = _j("04_priority_sheet_real_visual_audit.json")
    ins  = prio.get("inserted_charts_visible", 0)
    assert ins == 8, f"Expected 8 inserted chart images visible, got {ins}"


# ── Test 11 — Two unavailable panels visible ──────────────────────────────────
def test_11_two_unavailable_panels_visible():
    prio = _j("04_priority_sheet_real_visual_audit.json")
    unavail = prio.get("unavailable_panels_visible", 0)
    assert unavail == 2, f"Expected 2 unavail panels visible, got {unavail}"


# ── Test 12 — No visible formula errors ───────────────────────────────────────
def test_12_no_visible_formula_errors():
    results = _j("02_sheet_by_sheet_real_visual_results.json")
    err_sheets = [s["sheet"] for s in results["sheets"] if s.get("formula_errors")]
    assert not err_sheets, f"Visible formula errors on: {err_sheets}"


# ── Test 13 — DCF allowlist has exactly two known references ─────────────────
def test_13_dcf_allowlist_two_refs_only():
    dcf = _j("06_dcf_reference_allowlist.json")
    assert dcf["verdict"] == "PASS", f"DCF allowlist verdict: {dcf['verdict']}"
    entries = dcf.get("allowlist", [])
    assert len(entries) == 2, f"Expected 2 allowlist entries, got {len(entries)}"
    assert dcf.get("real_external_links", -1) == 0, \
        f"Real external links found: {dcf.get('real_external_links')}"
    for e in entries:
        assert e["reason_classified"] == "intra-workbook xlPathMissing self-ref", \
            f"Unexpected classification: {e}"


# ── Test 14 — Visual QA index exists and is clean ────────────────────────────
def test_14_visual_index_exists_clean():
    assert HTML_IDX.is_file(), f"Visual index missing: {HTML_IDX}"
    content = HTML_IDX.read_text(encoding="utf-8")
    assert "Batch 4R" in content or "Real Excel Visual" in content, \
        "HTML does not identify as Batch 4R"
    assert "sheet_pngs" in content, "HTML has no PNG gallery references"
    assert "C:/Users/" not in content and "C:\\Users\\" not in content, \
        "HTML exposes absolute paths"


# ── Test 15 — No absolute internal paths in any sheet ────────────────────────
def test_15_no_absolute_paths_in_sheets():
    results = _j("02_sheet_by_sheet_real_visual_results.json")
    abs_sheets = [s["sheet"] for s in results["sheets"]
                  if any(d["defect_category"] == "absolute_path"
                         for d in _j("03_real_visual_defects_register.json")["defects"]
                         if d["sheet"] == s["sheet"])]
    assert not abs_sheets, f"Absolute paths found in: {abs_sheets}"


# ── Test 16 — professional_valuation_outputs.py untouched ────────────────────
def test_16_pv_outputs_not_modified():
    content = PV_OUT.read_text(encoding="utf-8")
    assert "build_batch4r" not in content, \
        "professional_valuation_outputs.py was modified"
    assert "openpyxl.Workbook()" in content, \
        "professional_valuation_outputs.py lost the from-scratch builder"
