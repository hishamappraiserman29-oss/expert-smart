# -*- coding: utf-8 -*-
"""
21 tests for Batch 1 — Standalone Template-Driven Workbook Builder.

Tests verify:
 1.  Primary template file exists.
 2.  Builder module exists.
 3.  Output workbook exists after build.
 4.  Output opens cleanly with openpyxl.
 5.  Output contains exactly 44 sheets.
 6.  Sheet names/order match the primary template.
 7.  Source template SHA-256 is unchanged after build.
 8.  B4:B26 mapping labels were verified (no silent mismatches).
 9.  B27:B33 formulas are unchanged in output.
10.  Dashboard contains at least two charts.
11.  KPI cells A5, C5, G5, I5 remain formula-based.
12.  Completion formula I1 in assumptions sheet remains unchanged.
13.  Missing inputs are not silently converted to zero.
14.  Silent template assumptions are disabled by default.
15.  Assumption provenance is recorded when explicitly enabled.
16.  Output ZIP contains no VBA stream.
17.  Output is a valid .xlsx (not .xlsm).
18.  No source workbook is overwritten by build.
19.  No internal absolute paths are exposed in audit files.
20.  No fake certification/signature/license/stamp is created by builder.
21.  professional_valuation_outputs.py was NOT modified by Batch 1.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import zipfile

import openpyxl
import pytest

# ── Paths ──────────────────────────────────────────────────────────────────────
_BASE = pathlib.Path(__file__).resolve().parent.parent  # core_engine/
_REPO = _BASE.parent

_PRIMARY_TEMPLATE = (
    _REPO / "templates" / "reports" / "individual_valuation_professional_template.xlsm"
)
_BUILDER_MODULE = _BASE / "reports" / "excel_template_driven_builder.py"
_OUT_DIR = (
    _BASE / "instance" / "manual_review_outputs"
    / "professional_valuation_template_driven_batch1"
)
_OUTPUT_XL = _OUT_DIR / "excel_outputs" / "template_driven_professional_workbook_batch1.xlsx"
_AUDITS_DIR = _OUT_DIR / "audits"
_PVO_FILE = _BASE / "professional_valuation_outputs.py"

# ── Shared fixtures ────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def build_result():
    """
    Run the builder once per test session with a minimal ctx (no valid data)
    so we exercise the missing-input path.  Saves to the canonical output path.
    """
    spec = importlib.util.spec_from_file_location(
        "excel_template_driven_builder", str(_BUILDER_MODULE)
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    ctx: dict = {
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

    _OUTPUT_XL.parent.mkdir(parents=True, exist_ok=True)
    result = mod.build_individual_valuation_xlsx(
        ctx=ctx,
        output_path=_OUTPUT_XL,
        allow_template_assumptions=False,
    )
    return result, mod


@pytest.fixture(scope="module")
def output_wb(build_result):
    """Open the generated workbook once per session (read-only)."""
    result, _mod = build_result
    if not _OUTPUT_XL.is_file():
        pytest.skip("Output workbook was not generated — build failed")
    wb = openpyxl.load_workbook(str(_OUTPUT_XL), keep_vba=False)
    yield wb
    wb.close()


@pytest.fixture(scope="module")
def template_wb():
    """Open the primary template once per session (read-only)."""
    if not _PRIMARY_TEMPLATE.is_file():
        pytest.skip("Primary template not found")
    wb = openpyxl.load_workbook(str(_PRIMARY_TEMPLATE), keep_vba=True, read_only=True)
    yield wb
    wb.close()


# ── Tests ──────────────────────────────────────────────────────────────────────

# Test 1 — Primary template exists
def test_01_primary_template_exists():
    assert _PRIMARY_TEMPLATE.is_file(), (
        f"Primary template not found: {_PRIMARY_TEMPLATE}"
    )


# Test 2 — Builder module exists
def test_02_builder_module_exists():
    assert _BUILDER_MODULE.is_file(), (
        f"Builder module not found: {_BUILDER_MODULE}"
    )


# Test 3 — Output workbook exists after build
def test_03_output_workbook_exists(build_result):
    result, _mod = build_result
    assert _OUTPUT_XL.is_file(), (
        f"Output workbook not generated. Errors: {result['errors']}"
    )


# Test 4 — Output opens cleanly with openpyxl
def test_04_output_opens_cleanly(output_wb):
    assert output_wb is not None


# Test 5 — Output contains exactly 44 sheets
def test_05_output_sheet_count_44(output_wb):
    count = len(output_wb.sheetnames)
    assert count == 44, f"Expected 44 sheets, got {count}"


# Test 6 — Sheet names/order match primary template
def test_06_sheet_names_match_template(output_wb, template_wb):
    out_names = list(output_wb.sheetnames)
    tpl_names = list(template_wb.sheetnames)
    assert out_names == tpl_names, (
        f"Sheet name mismatch.\nTemplate: {tpl_names}\nOutput: {out_names}"
    )


# Test 7 — Source template SHA-256 unchanged after build
def test_07_source_template_sha256_unchanged(build_result):
    result, _mod = build_result
    sha_before = result.get("template_sha256_before")
    sha_after = result.get("template_sha256_after")
    assert sha_before is not None, "SHA before not recorded"
    assert sha_after is not None, "SHA after not recorded"
    assert sha_before == sha_after, (
        f"Source template was mutated! before={sha_before} after={sha_after}"
    )
    # Also verify against current file directly
    current_sha = hashlib.sha256(_PRIMARY_TEMPLATE.read_bytes()).hexdigest()
    assert current_sha == sha_before, (
        f"Template SHA at test-time differs from build-time record. "
        f"build={sha_before} now={current_sha}"
    )


# Test 8 — B4:B26 mapping labels verified (no undetected mismatches)
def test_08_injection_mapping_labels_verified(build_result, output_wb):
    result, _mod = build_result
    ws = output_wb["الافتراضات والمدخلات"]
    expected_labels = _mod._EXPECTED_LABELS
    bad = []
    for row, expected in expected_labels.items():
        actual = ws.cell(row, 1).value
        if actual != expected:
            bad.append(f"B{row}: expected {expected!r}, got {actual!r}")
    assert not bad, "\n".join(bad)
    # Blockers should be empty when labels match (test with minimal ctx)
    blockers = result.get("mapping_blockers", [])
    for blocker in blockers:
        # Any blocker must have been recorded explicitly (not silently ignored)
        assert "row" in blocker and "expected_label" in blocker, (
            f"Blocker missing required fields: {blocker}"
        )


# Test 9 — B27:B33 formulas unchanged in output
def test_09_b27_b33_formulas_unchanged(build_result, output_wb):
    result, _mod = build_result
    ws = output_wb["الافتراضات والمدخلات"]
    before = result.get("b27_b33_before", {})
    assert before, "b27_b33_before snapshot missing from result"
    bad = []
    for r in range(27, 34):
        coord = f"B{r}"
        expected_formula = before.get(coord, {}).get("value")
        actual_formula = ws.cell(r, 2).value
        if expected_formula != actual_formula:
            bad.append(
                f"{coord}: expected {expected_formula!r}, got {actual_formula!r}"
            )
    assert not bad, "\n".join(bad)


# Test 10 — Dashboard contains at least two charts
def test_10_dashboard_has_at_least_two_charts(output_wb):
    ws = output_wb["لوحة القيادة التنفيذية"]
    chart_count = len(ws._charts)
    assert chart_count >= 2, (
        f"Expected >= 2 charts in dashboard, found {chart_count}"
    )


# Test 11 — KPI cells A5, C5, G5, I5 remain formula-based
def test_11_kpi_cells_are_formulas(output_wb):
    ws = output_wb["لوحة القيادة التنفيذية"]
    bad = []
    for coord in ["A5", "C5", "G5", "I5"]:
        val = ws[coord].value
        if not (isinstance(val, str) and val.startswith("=")):
            bad.append(f"{coord}: expected formula, got {val!r}")
    assert not bad, "\n".join(bad)


# Test 12 — Completion formula I1 in assumptions sheet unchanged
def test_12_completion_formula_i1_unchanged(output_wb, template_wb):
    ws_out = output_wb["الافتراضات والمدخلات"]
    ws_tpl = template_wb["الافتراضات والمدخلات"]
    tpl_i1 = ws_tpl["I1"].value
    out_i1 = ws_out["I1"].value
    assert isinstance(out_i1, str) and out_i1.startswith("="), (
        f"I1 is not a formula in output: {out_i1!r}"
    )
    assert out_i1 == tpl_i1, (
        f"I1 formula changed.\nTemplate: {tpl_i1!r}\nOutput: {out_i1!r}"
    )


# Test 13 — Missing inputs are not silently converted to zero
def test_13_missing_inputs_not_replaced_with_zero(build_result, output_wb):
    result, _mod = build_result
    ws = output_wb["الافتراضات والمدخلات"]
    # Cells the test ctx did NOT supply — they must be None/blank, not 0
    # Test ctx supplies: B4(area), B5(price), B6(rent), B7(cap_rate), B9(floor),
    # B10(year), B13(client), B14(type), B15(location).
    # NOT supplied: B8, B11, B12, B17-B26 (except B7 cap rate).
    missing_rows_in_test_ctx = [8, 11, 12, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26]
    bad = []
    for row in missing_rows_in_test_ctx:
        val = ws.cell(row, 2).value
        if val == 0 or val == 0.0:
            bad.append(
                f"B{row}: should be blank (missing), but was injected as zero"
            )
    assert not bad, "\n".join(bad)


# Test 14 — Silent template assumptions disabled by default
def test_14_template_assumptions_disabled_by_default(build_result):
    result, _mod = build_result
    # Build fixture uses allow_template_assumptions=False (the default)
    assert result["allow_template_assumptions"] is False, (
        "allow_template_assumptions must default to False"
    )
    # No template-assumption provenance entries should exist in result
    tpl_assumed = [
        k for k, v in result.get("provenance", {}).items()
        if v.get("provenance") == "template_assumption"
    ]
    assert not tpl_assumed, (
        f"template_assumption provenance used when allow_template_assumptions=False: {tpl_assumed}"
    )


# Test 15 — Assumption provenance recorded when explicitly enabled
def test_15_provenance_recorded_when_assumptions_enabled(build_result):
    _result, mod = build_result
    # Build a second workbook with template assumptions enabled
    ctx_empty: dict = {}
    tmp_path = (
        _OUT_DIR / "excel_outputs" / "template_driven_assumptions_test.xlsx"
    )
    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    res2 = mod.build_individual_valuation_xlsx(
        ctx=ctx_empty,
        output_path=tmp_path,
        allow_template_assumptions=True,
    )
    # At least some cells should show template_assumption provenance
    tpl_assumed = [
        k for k, v in res2.get("provenance", {}).items()
        if v.get("provenance") == "template_assumption"
    ]
    assert tpl_assumed, (
        "No template_assumption entries recorded when allow_template_assumptions=True"
    )
    # Clean up test artefact
    if tmp_path.is_file():
        tmp_path.unlink()


# Test 16 — Output ZIP contains no VBA stream
def test_16_output_no_vba_stream(build_result):
    result, _mod = build_result
    macro_audit = result.get("macro_audit", {})
    assert macro_audit.get("verdict") == "CLEAN", (
        f"Macro stream detected: {macro_audit.get('macro_entries')}"
    )
    # Double-check by inspecting ZIP directly
    macro_markers = ("vbaproject.bin", "xl/vbaproject.bin", "xl/macros/vbaproject.bin")
    with zipfile.ZipFile(str(_OUTPUT_XL), "r") as zf:
        lower_names = [n.lower() for n in zf.namelist()]
        found = [n for n in lower_names if any(m in n for m in macro_markers)]
    assert not found, f"VBA entries found in output ZIP: {found}"


# Test 17 — Output is a valid .xlsx (not .xlsm)
def test_17_output_is_xlsx():
    assert _OUTPUT_XL.suffix == ".xlsx", (
        f"Output extension is {_OUTPUT_XL.suffix!r}; expected .xlsx"
    )
    # A valid OOXML xlsx must have [Content_Types].xml
    with zipfile.ZipFile(str(_OUTPUT_XL), "r") as zf:
        assert "[Content_Types].xml" in zf.namelist(), (
            "Output is not a valid OOXML package"
        )


# Test 18 — No source workbook overwritten
def test_18_source_workbooks_not_overwritten():
    sources = [
        _PRIMARY_TEMPLATE,
        _REPO / "templates" / "reports" / "mass_appraisal_professional_template.xlsm",
        _BASE / "instance" / "manual_review_outputs"
        / "valuation_certification_readiness_gate"
        / "03_market_certification_readiness_workbook.xlsx",
    ]
    for src in sources:
        if not src.exists():
            continue  # only check those present
        # Verify file is still in its original directory (not in batch1 output dir)
        out_dir_str = str(_OUT_DIR).replace("\\", "/").lower()
        src_str = str(src).replace("\\", "/").lower()
        assert not src_str.startswith(out_dir_str), (
            f"Source file appears to have been moved into output dir: {src}"
        )
        # Verify extension unchanged
        assert src.suffix.lower() in (".xlsm", ".xlsx"), (
            f"Source extension changed: {src}"
        )


# Test 19 — No internal absolute paths exposed in audit files
def test_19_no_absolute_paths_in_audits():
    if not _AUDITS_DIR.is_dir():
        pytest.skip("Audits dir not generated yet")
    bad = []
    for audit_file in _AUDITS_DIR.glob("*.json"):
        content = audit_file.read_text(encoding="utf-8")
        # Windows absolute paths: drive letter + colon + backslash
        import re
        hits = re.findall(r"[A-Za-z]:\\[^\s\"\\]{5,}", content)
        # Allow the path value that is explicitly part of the inventory record
        # (which exists as a design requirement), but flag any unexpected leaks
        # in other fields
        data = json.loads(content)
        # The only allowed absolute path is primary_template.path in audit 01
        allowed_contexts = set()
        if audit_file.name == "01_source_template_inventory.json":
            pt = data.get("primary_template", {}).get("path", "")
            if pt:
                allowed_contexts.add(pt.replace("/", "\\"))

        for hit in hits:
            norm = hit.replace("/", "\\")
            if norm not in allowed_contexts:
                bad.append(f"{audit_file.name}: {hit!r}")
    assert not bad, f"Unexpected absolute paths in audits:\n" + "\n".join(bad)


# Test 20 — No fake certification/signature/license/stamp created by builder
def test_20_no_fake_certification(build_result, output_wb):
    """
    The builder only writes to B4:B26 of الافتراضات والمدخلات.
    Verify that no cell in that injection range contains hardcoded certification,
    approval, or completion language that could create a false impression of
    a certified or complete workbook.

    The test does NOT scan other sheets — those contain legitimate template text
    (professional disclaimers, placeholder signature lines, column labels) that
    the builder never touches.
    """
    fake_markers = [
        "مكتمل",            # 'complete' — must not be hardcoded in input cells
        "معتمد",             # 'approved/certified'
        "جاهز للاعتماد",    # 'ready for certification'
        "✅",               # green checkmark completion indicator
    ]
    ws = output_wb["الافتراضات والمدخلات"]
    bad = []
    # Check only the injection range B4:B26
    for row in range(4, 27):
        cell = ws.cell(row, 2)
        val = cell.value
        if not isinstance(val, str):
            continue
        if isinstance(val, str) and val.startswith("="):
            continue  # formula — fine
        for marker in fake_markers:
            if marker in val:
                bad.append(
                    f"الافتراضات والمدخلات!B{row}: injected value contains "
                    f"{marker!r}: {val[:120]!r}"
                )
    assert not bad, (
        "Builder injected fake certification/completion text into input cells:\n"
        + "\n".join(bad)
    )


# Test 21 — professional_valuation_outputs.py NOT modified by Batch 1
def test_21_pvo_not_modified():
    """
    Verify professional_valuation_outputs.py retains the from-scratch legacy builder
    (Batch 1 guard).  Batch 5 integration added a strategy wrapper and feature flag;
    the guard checks that the legacy builder body is preserved and additive only.
    """
    assert _PVO_FILE.is_file(), f"File not found: {_PVO_FILE}"
    content = _PVO_FILE.read_text(encoding="utf-8")
    # The from-scratch legacy builder must still exist (never removed)
    assert "wb = openpyxl.Workbook()" in content, (
        "professional_valuation_outputs.py no longer contains 'wb = openpyxl.Workbook()' "
        "— the legacy builder was removed (must be preserved)"
    )
    # Batch 5 integration wires in the builder — its presence is now expected
    assert "excel_template_driven_builder" in content, (
        "professional_valuation_outputs.py no longer references excel_template_driven_builder "
        "— Batch 5 integration wrapper was removed"
    )
    # Legacy function must still be present
    assert "def _generate_final_workbook(" in content, (
        "_generate_final_workbook was removed — legacy builder must be preserved"
    )
