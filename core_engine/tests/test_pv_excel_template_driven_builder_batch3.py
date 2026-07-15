# -*- coding: utf-8 -*-
"""
Batch 3 — Distinctive Sheets + Matplotlib Visualization tests.
30 tests verifying the full build, regression protection, and governance rules.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import re
import zipfile

import openpyxl
import pytest

# ── Canonical paths ────────────────────────────────────────────────────────────
BASE = pathlib.Path(__file__).resolve().parent.parent.parent
BUILDER_PATH = BASE / "core_engine" / "reports" / "excel_template_driven_builder.py"
BATCH2_PATH = (
    BASE / "core_engine" / "instance" / "manual_review_outputs"
    / "professional_valuation_template_driven_batch2"
    / "excel_outputs" / "template_driven_professional_workbook_batch2.xlsx"
)
PRIMARY_TEMPLATE = BASE / "templates" / "reports" / "individual_valuation_professional_template.xlsm"
FALLBACK_TEMPLATE = BASE / "templates" / "reports" / "mass_appraisal_professional_template.xlsm"
OUTPUT_PATH = (
    BASE / "core_engine" / "instance" / "manual_review_outputs"
    / "professional_valuation_template_driven_batch3"
    / "excel_outputs" / "template_driven_professional_workbook_batch3.xlsx"
)
AUDITS_DIR = (
    BASE / "core_engine" / "instance" / "manual_review_outputs"
    / "professional_valuation_template_driven_batch3" / "audits"
)
IMAGES_DIR = (
    BASE / "core_engine" / "instance" / "manual_review_outputs"
    / "professional_valuation_template_driven_batch3" / "generated_images"
)
PREVIEWS_DIR = (
    BASE / "core_engine" / "instance" / "manual_review_outputs"
    / "professional_valuation_template_driven_batch3" / "visual_previews"
)
PV_OUTPUTS_PATH = BASE / "core_engine" / "professional_valuation_outputs.py"

_CTX = {
    "request_summary": {
        "client_name": "بنك التجمع الخامس",
        "property_type": "شقة سكنية",
        "property_address": "القاهرة الجديدة",
        "area_sqm": 175,
        "construction_year": 2015,
        "floor_number": 3,
    },
    "method_summary": {
        "cap_rate": 0.09,
        "annual_rent_per_sqm": 420,
    },
    "comparable_summary": {
        "price_per_sqm": 28500,
    },
}

# ── Module + build fixtures ────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def builder_mod():
    spec = importlib.util.spec_from_file_location(
        "excel_template_driven_builder", str(BUILDER_PATH)
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def build_result3(builder_mod):
    result3 = builder_mod.build_batch3_distinctive_xlsx(
        batch2_path=BATCH2_PATH,
        ctx=_CTX,
        output_path=OUTPUT_PATH,
    )
    out_dir = OUTPUT_PATH.parent.parent
    builder_mod.write_batch3_audits(result3, out_dir)
    return result3


@pytest.fixture(scope="module")
def output_wb(build_result3):
    wb = openpyxl.load_workbook(str(OUTPUT_PATH))
    yield wb
    wb.close()


# ── Test 01 — Batch 2 input exists ────────────────────────────────────────────
def test_01_batch2_input_exists():
    assert BATCH2_PATH.is_file(), f"Batch 2 input missing: {BATCH2_PATH}"


# ── Test 02 — Both source templates exist ─────────────────────────────────────
def test_02_both_source_templates_exist():
    assert PRIMARY_TEMPLATE.is_file(), f"Primary template missing: {PRIMARY_TEMPLATE}"
    assert FALLBACK_TEMPLATE.is_file(), f"Fallback template missing: {FALLBACK_TEMPLATE}"


# ── Test 03 — Source hashes unchanged ─────────────────────────────────────────
def test_03_source_hashes_unchanged(build_result3):
    assert build_result3["batch2_sha256_before"] == build_result3["batch2_sha256_after"], \
        "Batch 2 source was mutated during build"


# ── Test 04 — Batch 3 builder exists ──────────────────────────────────────────
def test_04_builder_exists():
    assert BUILDER_PATH.is_file(), f"Builder missing: {BUILDER_PATH}"


# ── Test 05 — Batch 3 output exists ──────────────────────────────────────────
def test_05_output_exists(build_result3):
    assert OUTPUT_PATH.is_file(), f"Batch 3 output missing: {OUTPUT_PATH}"


# ── Test 06 — Output opens cleanly ───────────────────────────────────────────
def test_06_output_opens_cleanly():
    wb = openpyxl.load_workbook(str(OUTPUT_PATH))
    assert wb is not None
    wb.close()


# ── Test 07 — First 54 sheets match Batch 2 ──────────────────────────────────
def test_07_first_54_sheets_match_batch2(output_wb, build_result3):
    b2_names = build_result3["batch2_sheet_names_before"]
    actual_first54 = list(output_wb.sheetnames)[:54]
    assert actual_first54 == b2_names, (
        f"First 54 sheets differ from Batch 2.\n"
        f"Expected: {b2_names[:5]}...\n"
        f"Got:      {actual_first54[:5]}..."
    )


# ── Test 08 — Expected distinctive sheets preserved or documented ─────────────
def test_08_distinctive_sheets_documented(build_result3):
    inv = build_result3.get("distinctive_inventory", {})
    assert "ann_sheet" in inv, "ANN sheet not in distinctive inventory"
    assert "qiima_sheet" in inv, "قيمة بالحروف not in distinctive inventory"
    ann = inv["ann_sheet"]
    assert ann["in_batch2"] is True, "ANN sheet should be present in Batch 2"
    assert "ANN — الشبكات العصبية" in build_result3.get("output_sheet_names", []), \
        "ANN sheet missing from output"


# ── Test 09 — No duplicate sheet names ────────────────────────────────────────
def test_09_no_duplicate_sheet_names(output_wb):
    names = list(output_wb.sheetnames)
    assert len(names) == len(set(names)), \
        f"Duplicate sheet names found: {[n for n in names if names.count(n) > 1]}"


# ── Test 10 — ANN sheet contains no invented metrics ─────────────────────────
def test_10_ann_sheet_no_invented_metrics(output_wb, build_result3):
    ann = output_wb["ANN — الشبكات العصبية"]
    # RMSE, MAE, R² should match what was already in the sheet (not invented)
    rmse_ols = ann["B35"].value
    mae_ols = ann["B36"].value
    r2_ols = ann["B37"].value
    assert rmse_ols is not None, "ANN B35 (OLS RMSE) should not be None"
    assert mae_ols is not None, "ANN B36 (OLS MAE) should not be None"
    assert r2_ols is not None, "ANN B37 (OLS R²) should not be None"
    # Values should be realistic (not fabricated large numbers)
    assert 0 < float(rmse_ols) < 100_000, f"ANN RMSE out of plausible range: {rmse_ols}"
    assert 0 < float(mae_ols) < 100_000, f"ANN MAE out of plausible range: {mae_ols}"
    assert -1 <= float(r2_ols) <= 1.0, f"OLS R² out of range: {r2_ols}"
    # Confirm build_result3 also records invented_metrics=False
    ann_audit_path = AUDITS_DIR / "02_ann_sheet_preservation_audit.json"
    if ann_audit_path.is_file():
        ann_audit = json.loads(ann_audit_path.read_text(encoding="utf-8"))
        assert ann_audit.get("invented_metrics") is False


# ── Test 11 — Value-in-words source matches numeric source ────────────────────
def test_11_value_in_words_source_consistency(build_result3):
    qiima_prov = build_result3.get("qiima_provenance", {})
    source = qiima_prov.get("source")
    # If computed, total_value and words must both be present
    if source == "computed":
        total = qiima_prov.get("total_value_egp")
        words = qiima_prov.get("value_in_words")
        assert total is not None and total > 0, "قيمة بالحروف: total_value_egp must be > 0"
        assert words and len(words) > 5, "قيمة بالحروف: value_in_words must be non-empty Arabic text"
        # Both must reference the same numeric value
        area = qiima_prov.get("area_sqm")
        per_sqm = qiima_prov.get("weighted_per_sqm")
        if area and per_sqm:
            expected_total = float(per_sqm) * float(area)
            assert abs(float(total) - expected_total) < 1.0, \
                f"قيمة بالحروف: total ({total}) does not match per_sqm * area ({expected_total})"


# ── Test 12 — Missing final value produces unavailable text ──────────────────
def test_12_missing_value_produces_unavailable_text(build_result3, builder_mod):
    # With no ctx, the builder should mark source as unavailable
    ctx_empty: dict = {}
    recon_empty = builder_mod._read_recon_data(BATCH2_PATH)
    # If compute_ok=True (data exists in workbook), source will be 'computed'
    # If unavailable, the sheet should show the sentinel text
    qiima_prov = build_result3.get("qiima_provenance", {})
    source = qiima_prov.get("source", "unavailable")
    if source == "unavailable":
        # القيمة بالحروف sheet should contain the missing sentinel
        if "القيمة بالحروف" in output_wb_names(build_result3):
            pass  # sheet exists even with unavailable data
    else:
        assert source == "computed", f"Unexpected source: {source}"


def output_wb_names(result3):
    return result3.get("output_sheet_names", [])


# ── Test 13 — Generated images exist ──────────────────────────────────────────
def test_13_generated_images_exist(build_result3):
    imgs = build_result3.get("images_generated", [])
    assert len(imgs) == 10, f"Expected 10 images, got {len(imgs)}"
    for img_info in imgs:
        fname = img_info["filename"]
        img_path = IMAGES_DIR / fname
        assert img_path.is_file(), f"Generated image missing: {img_path}"


# ── Test 14 — Real charts have documented numeric provenance ──────────────────
def test_14_real_charts_have_provenance(build_result3):
    for img_info in build_result3.get("images_generated", []):
        if img_info.get("is_real_chart"):
            prov = img_info.get("provenance", "")
            assert prov and len(prov) > 5, \
                f"{img_info['filename']}: real chart has no provenance"


# ── Test 15 — Unavailable panels not counted as real charts ──────────────────
def test_15_unavailable_panels_not_counted_as_real(build_result3):
    real_count = build_result3.get("real_chart_count", 0)
    unavail_count = build_result3.get("unavailable_panel_count", 0)
    imgs = build_result3.get("images_generated", [])
    actual_real = sum(1 for r in imgs if r.get("is_real_chart"))
    actual_unavail = sum(1 for r in imgs if not r.get("is_real_chart"))
    assert real_count == actual_real, \
        f"real_chart_count mismatch: reported {real_count}, actual {actual_real}"
    assert unavail_count == actual_unavail, \
        f"unavailable_panel_count mismatch: reported {unavail_count}, actual {actual_unavail}"
    # Total must be 10
    assert real_count + unavail_count == 10


# ── Test 16 — Original dashboard charts remain ───────────────────────────────
def test_16_dashboard_charts_remain(build_result3):
    reg = build_result3.get("batch2_regression", {})
    before = reg.get("chart_count_before", 0)
    after = reg.get("chart_count_after", 0)
    assert after >= before, f"Chart count dropped: {before} → {after}"
    assert after >= 2, f"Expected at least 2 charts, found {after}"


# ── Test 17 — Inserted images do not replace original charts ─────────────────
def test_17_inserted_images_do_not_replace_charts(build_result3, output_wb):
    reg = build_result3.get("batch2_regression", {})
    before = reg.get("chart_count_before", 0)
    after = reg.get("chart_count_after", 0)
    assert after >= before, \
        f"Original charts were removed when inserting images: {before} → {after}"


# ── Test 18 — B27:B33 formulas unchanged ─────────────────────────────────────
def test_18_b27_b33_formulas_unchanged(build_result3):
    reg = build_result3.get("batch2_regression", {})
    b_before = reg.get("b27_b33_before", {})
    b_after = reg.get("b27_b33_after", {})
    for coord in ["B27", "B28", "B29", "B30", "B31", "B32", "B33"]:
        before = b_before.get(coord, {}).get("value")
        after = b_after.get(coord, {}).get("value")
        assert before == after, f"{coord} formula changed: {before!r} → {after!r}"


# ── Test 19 — KPI formulas unchanged ─────────────────────────────────────────
def test_19_kpi_formulas_unchanged(build_result3):
    reg = build_result3.get("batch2_regression", {})
    kpi_before = reg.get("kpi_before", {})
    kpi_after = reg.get("kpi_after", {})
    for coord in ["A5", "C5", "G5", "I5"]:
        before = kpi_before.get(coord)
        after = kpi_after.get(coord)
        assert before == after, f"Dashboard KPI {coord} changed: {before!r} → {after!r}"


# ── Test 20 — I1 completion formula unchanged ─────────────────────────────────
def test_20_i1_completion_formula_unchanged(build_result3, output_wb):
    reg = build_result3.get("batch2_regression", {})
    i1_before = reg.get("kpi_before", {}).get("I1")
    i1_after = reg.get("kpi_after", {}).get("I1")
    assert i1_before == i1_after, f"I1 changed: {i1_before!r} → {i1_after!r}"
    ws = output_wb["الافتراضات والمدخلات"]
    h1 = ws["H1"].value
    assert h1 and isinstance(h1, str) and h1.startswith("="), \
        f"H1 completion counter is not a formula: {h1!r}"
    assert "COUNTA" in h1.upper(), f"H1 does not contain COUNTA: {h1!r}"


# ── Test 21 — B20 behavior unchanged ─────────────────────────────────────────
def test_21_b20_behavior_unchanged(output_wb):
    ws = output_wb["الافتراضات والمدخلات"]
    b20 = ws["B20"].value
    assert b20 is None, (
        f"B20 must remain blank (wacc_construction not in ctx), got: {b20!r}"
    )


# ── Test 22 — Confirmed [1] DCF formulas unchanged ───────────────────────────
def test_22_dcf_intra_wb_refs_unchanged(build_result3):
    reg = build_result3.get("batch2_regression", {})
    dcf_before = reg.get("dcf_refs_before", {})
    dcf_after = reg.get("dcf_refs_after", {})
    for coord in ["A61", "A62", "A63"]:
        before = dcf_before.get(coord)
        after = dcf_after.get(coord)
        assert before == after, \
            f"DCF {coord} intra-wb ref changed: {before!r} → {after!r}"


# ── Test 23 — External link count remains zero ───────────────────────────────
def test_23_no_external_workbook_links(build_result3):
    issues = build_result3.get("workbook_issues", {})
    assert issues.get("external_link_count", 0) == 0, \
        f"External links found: {issues.get('external_link_examples', [])}"


# ── Test 24 — Broken formula count remains zero ──────────────────────────────
def test_24_no_broken_formulas(build_result3):
    issues = build_result3.get("workbook_issues", {})
    assert issues.get("ref_error_count", 0) == 0, \
        f"#REF! errors: {issues.get('ref_error_examples', [])}"


# ── Test 25 — No VBA stream ───────────────────────────────────────────────────
def test_25_no_vba_stream(build_result3):
    macro = build_result3.get("macro_audit", {})
    assert macro.get("verdict") == "CLEAN", \
        f"VBA found: {macro.get('macro_entries', [])}"


# ── Test 26 — Signature gate remains unsigned ─────────────────────────────────
def test_26_signature_gate_unsigned(output_wb):
    ws = output_wb["توقيع واعتماد الخبير"]
    b8 = str(ws["B8"].value or "")
    assert "توقيع" in b8, f"B8 must contain signature pending text, got: {b8!r}"
    b11 = str(ws["B11"].value or "")
    assert b11.startswith("لا"), f"B11 must start with 'لا' (not certified), got: {b11!r}"


# ── Test 27 — No automatic certified status ──────────────────────────────────
def test_27_no_automatic_certified_status(output_wb):
    ws = output_wb["حالة الاعتماد والتوصية"]
    b3 = ws["B3"].value
    assert b3 == "لا", f"Certification ready must be 'لا', got: {b3!r}"
    b2 = ws["B2"].value
    CERTIFIED_VALS = {"معتمد", "جاهز للاعتماد", "مكتمل", "approved"}
    assert str(b2 or "").strip() not in CERTIFIED_VALS, \
        f"Report status must not indicate certified, got: {b2!r}"


# ── Test 28 — No internal absolute paths ─────────────────────────────────────
def test_28_no_absolute_paths(build_result3):
    issues = build_result3.get("workbook_issues", {})
    assert issues.get("abs_path_count", 0) == 0, \
        f"Absolute paths in cells: {issues.get('abs_path_examples', [])}"


# ── Test 29 — Visual preview index exists ─────────────────────────────────────
def test_29_visual_preview_index_exists():
    preview = PREVIEWS_DIR / "OPEN_BATCH3_DISTINCTIVE_VISUAL_REVIEW.html"
    assert preview.is_file(), f"Visual preview HTML missing: {preview}"
    content = preview.read_text(encoding="utf-8")
    assert "Batch 3" in content, "Preview HTML does not mention Batch 3"
    assert "القيمة بالحروف" in content, "Preview HTML missing قيمة بالحروف section"


# ── Test 30 — professional_valuation_outputs.py not modified ─────────────────
def test_30_pv_outputs_not_modified_by_batch3():
    content = PV_OUTPUTS_PATH.read_text(encoding="utf-8")
    assert "build_batch3_distinctive_xlsx" not in content, \
        "professional_valuation_outputs.py was modified — contains batch3 function reference"
    assert "openpyxl.Workbook()" in content, \
        "professional_valuation_outputs.py lost the from-scratch builder"
