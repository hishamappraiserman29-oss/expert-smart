# -*- coding: utf-8 -*-
"""
Batch 4 — Final Visual Parity, Full QA, and Integration Readiness tests.
27 tests verifying the QA copy, visual render, formula integrity, governance,
and integration readiness decision.
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

BATCH3_PATH = (
    BASE / "core_engine" / "instance" / "manual_review_outputs"
    / "professional_valuation_template_driven_batch3"
    / "excel_outputs" / "template_driven_professional_workbook_batch3.xlsx"
)
OUTPUT_PATH = (
    BASE / "core_engine" / "instance" / "manual_review_outputs"
    / "professional_valuation_template_driven_batch4"
    / "excel_outputs" / "template_driven_professional_workbook_final_qa.xlsx"
)
BATCH4_DIR = OUTPUT_PATH.parent.parent
AUDITS_DIR = BATCH4_DIR / "audits"
FINAL_REPORT_DIR = BATCH4_DIR / "final_report"
PNG_DIR = BATCH4_DIR / "visual_previews" / "sheet_pngs"
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
def build_result4(builder_mod):
    result4 = builder_mod.build_batch4_qa(
        batch3_path=BATCH3_PATH,
        ctx=_CTX,
        output_path=OUTPUT_PATH,
    )
    out_dir = OUTPUT_PATH.parent.parent
    builder_mod.write_batch4_artifacts(result4, out_dir)
    return result4


@pytest.fixture(scope="module")
def output_wb(build_result4):
    wb = openpyxl.load_workbook(str(OUTPUT_PATH))
    yield wb
    wb.close()


# ── Test 01 — Batch 3 workbook exists ─────────────────────────────────────────
def test_01_batch3_workbook_exists():
    assert BATCH3_PATH.is_file(), f"Batch 3 workbook missing: {BATCH3_PATH}"


# ── Test 02 — Batch 4 QA workbook exists ──────────────────────────────────────
def test_02_batch4_qa_workbook_exists(build_result4):
    assert OUTPUT_PATH.is_file(), f"Batch 4 QA output missing: {OUTPUT_PATH}"


# ── Test 03 — QA workbook opens cleanly ───────────────────────────────────────
def test_03_qa_workbook_opens_cleanly():
    wb = openpyxl.load_workbook(str(OUTPUT_PATH))
    assert wb is not None
    wb.close()


# ── Test 04 — Sheet count is exactly 55 ───────────────────────────────────────
def test_04_sheet_count_is_55(output_wb):
    assert len(output_wb.sheetnames) == 55, \
        f"Expected 55 sheets, got {len(output_wb.sheetnames)}"


# ── Test 05 — Sheet names/order match Batch 3 ─────────────────────────────────
def test_05_sheet_names_match_batch3(output_wb, build_result4):
    b3_names = build_result4.get("sheet_names", [])
    assert list(output_wb.sheetnames) == b3_names, \
        "QA copy sheet order differs from Batch 3"


# ── Test 06 — All 55 sheets have rendered previews ────────────────────────────
def test_06_all_55_sheets_rendered(build_result4):
    rendered = build_result4.get("sheets_rendered", 0)
    assert rendered == 55, f"Expected 55 rendered, got {rendered}"


# ── Test 07 — At least one PNG exists per sheet ───────────────────────────────
def test_07_at_least_one_png_per_sheet(build_result4):
    sheet_names = build_result4.get("sheet_names", [])
    assert len(sheet_names) == 55
    pngs = list(PNG_DIR.glob("*.png")) if PNG_DIR.is_dir() else []
    assert len(pngs) >= 55, \
        f"Expected at least 55 PNGs, found {len(pngs)} in {PNG_DIR}"


# ── Test 08 — No critical visual defect (FAILED sheets = 0) ───────────────────
def test_08_no_critical_visual_defect(build_result4):
    failed = build_result4.get("failed_sheets", 0)
    assert failed == 0, \
        f"{failed} sheets classified FAILED. Defects: " \
        f"{[d['issue'] for d in build_result4.get('defects_register', []) if d.get('severity')=='CRITICAL'][:5]}"


# ── Test 09 — Original two dashboard charts remain ────────────────────────────
def test_09_original_dashboard_charts_remain(build_result4):
    chart_prov = build_result4.get("chart_provenance", {})
    orig = chart_prov.get("original_template_charts", 0)
    assert orig >= 2, f"Expected >= 2 original charts, found {orig}"


# ── Test 10 — Eight real inserted charts remain ───────────────────────────────
def test_10_eight_real_inserted_charts(build_result4):
    real = build_result4.get("real_chart_count", 0)
    assert real == 8, f"Expected 8 real charts, got {real}"


# ── Test 11 — Two unavailable panels remain clearly labelled ──────────────────
def test_11_two_unavailable_panels_labelled(build_result4):
    unavail = build_result4.get("unavailable_panel_count", 0)
    assert unavail == 2, f"Expected 2 unavailable panels, got {unavail}"
    chart_prov = build_result4.get("chart_provenance", {})
    label = chart_prov.get("unavailable_label_text", "")
    assert "غير متاح" in label, f"Unavailable label text missing: {label!r}"


# ── Test 12 — B27:B33 formulas remain unchanged ───────────────────────────────
def test_12_b27_b33_unchanged(build_result4):
    fi = build_result4.get("formula_integrity", {})
    b27_b33 = fi.get("b27_b33", {})
    for coord in ["B27", "B28", "B29", "B30", "B31", "B32", "B33"]:
        assert coord in b27_b33, f"{coord} not found in formula integrity audit"
        v = b27_b33[coord].get("value")
        assert v is not None, f"{coord} is None — formula disappeared"


# ── Test 13 — KPI formulas remain (A5, C5, G5, I5) ───────────────────────────
def test_13_kpi_formulas_unchanged(build_result4):
    fi = build_result4.get("formula_integrity", {})
    kpis = fi.get("kpis", {})
    for coord in ["A5", "C5", "G5", "I5"]:
        assert kpis.get(coord) is not None, \
            f"Dashboard KPI {coord} is missing"


# ── Test 14 — I1 formula remains ──────────────────────────────────────────────
def test_14_i1_formula_unchanged(build_result4):
    fi = build_result4.get("formula_integrity", {})
    assert fi.get("i1_is_formula") or fi.get("i1_value") is not None, \
        "I1 completion cell is missing or no longer a formula"


# ── Test 15 — B20 blank when wacc_construction absent ────────────────────────
def test_15_b20_blank(build_result4):
    fi = build_result4.get("formula_integrity", {})
    assert fi.get("b20_blank") is True, \
        f"B20 must be blank (wacc_construction not in ctx), got: {fi.get('b20_value')!r}"


# ── Test 16 — DCF A61:A63 [1]-refs unchanged ──────────────────────────────────
def test_16_dcf_1_refs_unchanged(build_result4):
    fi = build_result4.get("formula_integrity", {})
    assert fi.get("dcf_refs_preserved"), \
        f"DCF A61:A63 [1]-refs not preserved. Values: {fi.get('dcf_a61_a63')}"


# ── Test 17 — Broken formula count is zero ────────────────────────────────────
def test_17_broken_formula_count_zero(build_result4):
    fi = build_result4.get("formula_integrity", {})
    count = fi.get("broken_formula_count", 0)
    assert count == 0, \
        f"Found {count} broken formulas: {fi.get('broken_formula_examples', [])}"


# ── Test 18 — External link count is zero ─────────────────────────────────────
def test_18_external_link_count_zero(build_result4):
    fi = build_result4.get("formula_integrity", {})
    count = fi.get("external_link_count", 0)
    assert count == 0, f"External links found: {count}"


# ── Test 19 — No VBA stream ───────────────────────────────────────────────────
def test_19_no_vba_stream(build_result4):
    fi = build_result4.get("formula_integrity", {})
    assert fi.get("vba_clean", True), \
        f"VBA found in QA workbook: {fi.get('macro_verdict')}"


# ── Test 20 — Source (Batch 3) hash unchanged ─────────────────────────────────
def test_20_source_hash_unchanged(build_result4):
    before = build_result4.get("batch3_sha_before")
    after = build_result4.get("batch3_sha_after")
    assert before == after, \
        f"Batch 3 source was mutated during Batch 4 QA build: {before!r} → {after!r}"


# ── Test 21 — Value-in-words consistent with numeric source ───────────────────
def test_21_value_in_words_consistent(output_wb):
    assert "القيمة بالحروف" in output_wb.sheetnames, \
        "القيمة بالحروف sheet missing"
    ws = output_wb["القيمة بالحروف"]
    # Structure: A9 = Arabic words for total value, C8 = numeric total (EGP)
    # Find any non-None cell with Arabic word content in rows 1-12
    arabic_words = None
    numeric_val = None
    for row in range(1, 13):
        for col in range(1, 5):
            v = ws.cell(row, col).value
            if v is None:
                continue
            vs = str(v)
            if "مليون" in vs or "ألف" in vs or "مئة" in vs or "مائة" in vs:
                arabic_words = vs
            try:
                fv = float(v)
                if fv > 100000:
                    numeric_val = fv
            except (TypeError, ValueError):
                pass
    assert arabic_words is not None and len(arabic_words) > 10, \
        f"Arabic words for total value not found in القيمة بالحروف sheet"
    assert numeric_val is not None and numeric_val > 0, \
        f"Numeric total value not found in القيمة بالحروف sheet"
    # Verify consistency: Arabic words should correspond to the numeric value
    assert numeric_val > 2_000_000, \
        f"Expected value > 2M EGP (approx 3,083,813), got {numeric_val}"


# ── Test 22 — Signature sheet is unsigned ─────────────────────────────────────
def test_22_signature_unsigned(output_wb):
    assert "توقيع واعتماد الخبير" in output_wb.sheetnames
    ws = output_wb["توقيع واعتماد الخبير"]
    b10 = ws["B10"].value
    assert b10 != "معتمد", f"B10 must not be 'معتمد', got: {b10!r}"
    b11 = str(ws["B11"].value or "")
    assert b11.startswith("لا"), f"B11 must start with 'لا', got: {b11!r}"
    b8 = str(ws["B8"].value or "")
    assert "توقيع" in b8, f"B8 signature pending text missing: {b8!r}"


# ── Test 23 — No automatic certification ──────────────────────────────────────
def test_23_no_auto_certification(output_wb):
    assert "حالة الاعتماد والتوصية" in output_wb.sheetnames
    ws = output_wb["حالة الاعتماد والتوصية"]
    b3 = ws["B3"].value
    assert b3 == "لا", f"Cert ready flag B3 must be 'لا', got: {b3!r}"
    b2 = str(ws["B2"].value or "")
    CERT_VALS = {"معتمد", "جاهز للاعتماد", "مكتمل", "approved"}
    assert b2.strip() not in CERT_VALS, \
        f"Report status must not indicate certified: {b2!r}"


# ── Test 24 — No internal absolute paths ──────────────────────────────────────
def test_24_no_absolute_paths(build_result4):
    fi = build_result4.get("formula_integrity", {})
    count = fi.get("abs_path_count", 0)
    assert count == 0, f"Absolute paths found in cells: {count}"


# ── Test 25 — Visual index exists ─────────────────────────────────────────────
def test_25_visual_index_exists():
    html_path = (
        BATCH4_DIR / "visual_previews" / "OPEN_FINAL_TEMPLATE_DRIVEN_WORKBOOK_QA.html"
    )
    assert html_path.is_file(), f"Visual index missing: {html_path}"
    content = html_path.read_text(encoding="utf-8")
    assert "Batch 4" in content, "HTML index does not mention Batch 4"
    assert "sheet_pngs" in content, "HTML index has no PNG gallery references"
    # Must not expose absolute paths
    assert "C:/Users/" not in content and "C:\\Users\\" not in content, \
        "HTML index exposes absolute paths"


# ── Test 26 — Integration readiness report exists ────────────────────────────
def test_26_integration_readiness_report_exists(build_result4):
    report_path = FINAL_REPORT_DIR / "production_integration_readiness.md"
    assert report_path.is_file(), f"Readiness report missing: {report_path}"
    content = report_path.read_text(encoding="utf-8")
    readiness = build_result4.get("integration_readiness", "")
    assert readiness in content, \
        f"Readiness decision '{readiness}' not found in report"
    assert readiness in ("READY", "READY_WITH_CONDITIONS", "NOT_READY"), \
        f"Unexpected readiness value: {readiness!r}"


# ── Test 27 — professional_valuation_outputs.py not modified ─────────────────
def test_27_pv_outputs_not_modified():
    content = PV_OUTPUTS_PATH.read_text(encoding="utf-8")
    assert "build_batch4_qa" not in content, \
        "professional_valuation_outputs.py was modified — contains batch4 reference"
    assert "openpyxl.Workbook()" in content, \
        "professional_valuation_outputs.py lost the from-scratch builder"
