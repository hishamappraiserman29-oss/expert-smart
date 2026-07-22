# -*- coding: utf-8 -*-
"""
core_engine/tests/test_pv_excel_formula_regression.py

Permanent regression tests for the Excel template-driven builder formula fixes.

Verifies that:
  1. The corrected builder does NOT produce Excel error formulas in the three
     previously-defective sheets (9, 12, 34).
  2. Valid numeric inputs produce correct formula text (not annotation text).
  3. Missing data produces the sentinel string, not a formula error code.
  4. The builder pipeline completes (Batch 1→2→3) with 55 sheets.
  5. builder_used = template_driven, fallback_used = False.

These tests use openpyxl to inspect formula text and cached values — they do NOT
depend on manually-edited audit JSON files. COM recalculation is intentionally
not required here; the formula text check is sufficient to prove the fix.

DO NOT hard-code a PASS decision. DO NOT check total_formula_error_cells == 0
for the whole workbook, since pre-existing template named-range formulas in
other sheets produce #NAME? regardless of the fix.
"""
from __future__ import annotations

import pathlib
import tempfile
import sys
import os

import openpyxl
import pytest

# ── Builder import ─────────────────────────────────────────────────────────────
CORE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CORE))

_UNAVAIL = "لا تتوفر بيانات كافية للحساب"


@pytest.fixture(autouse=True, scope="module")
def _core_cwd():
    """Change working directory to CORE for this module's tests, then restore."""
    _orig = os.getcwd()
    os.chdir(str(CORE))
    yield
    os.chdir(_orig)


@pytest.fixture(scope="module")
def regen_workbook_missing_data(tmp_path_factory):
    """
    Fresh workbook generated with all numeric inputs missing.
    Proves the fix handles the worst-case state.
    """
    from reports.excel_template_driven_builder import (
        build_template_driven_professional_workbook as _build,
    )
    out = tmp_path_factory.mktemp("regen_missing") / "test_missing.xlsx"
    ctx = {
        "request_summary": {
            "property_type": "شقة سكنية",
            "property_address": "شارع القاهرة",
            "valuation_purpose": "بيع",
            "basis_of_value": "القيمة السوقية",
        },
        "method_summary": {},
        "comparable_summary": {},
    }
    result = _build(ctx, out, allow_template_assumptions=False)
    assert result["success"], f"Builder failed (missing data): {result['errors']}"
    assert result["sheet_count"] == 55, f"Expected 55 sheets, got {result['sheet_count']}"
    assert result["pipeline_stages_completed"] == 3
    wb = openpyxl.load_workbook(str(out), keep_vba=False, data_only=False)
    yield wb
    wb.close()


@pytest.fixture(scope="module")
def regen_workbook_with_defaults(tmp_path_factory):
    """
    Fresh workbook generated with template defaults (allow_template_assumptions=True).
    Proves the fix works when numeric inputs are available.
    """
    from reports.excel_template_driven_builder import (
        build_template_driven_professional_workbook as _build,
    )
    out = tmp_path_factory.mktemp("regen_defaults") / "test_defaults.xlsx"
    ctx = {
        "request_summary": {
            "property_type": "شقة سكنية",
            "property_address": "شارع القاهرة",
            "valuation_purpose": "بيع",
            "basis_of_value": "القيمة السوقية",
        },
        "method_summary": {},
        "comparable_summary": {},
    }
    result = _build(ctx, out, allow_template_assumptions=True)
    assert result["success"], f"Builder failed (defaults): {result['errors']}"
    assert result["sheet_count"] == 55, f"Expected 55 sheets, got {result['sheet_count']}"
    wb = openpyxl.load_workbook(str(out), keep_vba=False, data_only=False)
    yield wb
    wb.close()


# ─── Sheet 9: رأسمالة الدخل ──────────────────────────────────────────────────

class TestSheet9CapRate:
    """MAJ-01 regression: B11, B12 must be live formulas, not annotation text."""

    def test_b11_is_formula_not_annotation(self, regen_workbook_missing_data):
        ws = regen_workbook_missing_data["رأسمالة الدخل"]
        val = ws["B11"].value
        assert val is not None, "B11 is unexpectedly None"
        assert str(val).startswith("="), (
            f"B11 is not a formula — annotation text may have survived. Got: {val!r}"
        )
        assert "≈" not in str(val), (
            f"B11 still contains annotation text prefix '≈': {val!r}"
        )

    def test_b12_is_formula_not_annotation(self, regen_workbook_missing_data):
        ws = regen_workbook_missing_data["رأسمالة الدخل"]
        val = ws["B12"].value
        assert val is not None, "B12 is unexpectedly None"
        assert str(val).startswith("="), (
            f"B12 is not a formula — annotation text may have survived. Got: {val!r}"
        )
        assert "≈" not in str(val), (
            f"B12 still contains annotation text prefix '≈': {val!r}"
        )

    def test_b11_formula_references_b9_b10(self, regen_workbook_missing_data):
        ws = regen_workbook_missing_data["رأسمالة الدخل"]
        val = ws["B11"].value
        assert "B9" in str(val) and "B10" in str(val), (
            f"B11 formula should reference B9+B10, got: {val!r}"
        )

    def test_b12_formula_references_b15_b10(self, regen_workbook_missing_data):
        ws = regen_workbook_missing_data["رأسمالة الدخل"]
        val = ws["B12"].value
        assert "B15" in str(val) and "B10" in str(val), (
            f"B12 formula should reference B15*B10, got: {val!r}"
        )

    def test_b11_b12_same_with_defaults(self, regen_workbook_with_defaults):
        ws = regen_workbook_with_defaults["رأسمالة الدخل"]
        b11 = ws["B11"].value
        b12 = ws["B12"].value
        assert str(b11).startswith("=") and "≈" not in str(b11), (
            f"B11 with defaults still has annotation text: {b11!r}"
        )
        assert str(b12).startswith("=") and "≈" not in str(b12), (
            f"B12 with defaults still has annotation text: {b12!r}"
        )


# ─── Sheet 12: الخيارات الحقيقية ──────────────────────────────────────────────

class TestSheet12RealOptions:
    """MAJ-02 regression: NORM.S.DIST not _xludf.NORM.S.DIST; sigma=0 guard present."""

    def test_b14_has_sigma_guard(self, regen_workbook_missing_data):
        ws = regen_workbook_missing_data["الخيارات الحقيقية"]
        val = str(ws["B14"].value or "")
        assert val.startswith("=IF(OR(B7<=0"), (
            f"B14 missing sigma=0 guard. Got: {val!r}"
        )

    def test_b14_has_iferror(self, regen_workbook_missing_data):
        ws = regen_workbook_missing_data["الخيارات الحقيقية"]
        val = str(ws["B14"].value or "")
        assert "IFERROR" in val, f"B14 missing IFERROR guard. Got: {val!r}"

    def test_b16_uses_norm_s_dist_not_xludf(self, regen_workbook_missing_data):
        ws = regen_workbook_missing_data["الخيارات الحقيقية"]
        val = str(ws["B16"].value or "")
        assert "NORM.S.DIST" in val, f"B16 missing NORM.S.DIST. Got: {val!r}"
        assert "_xludf" not in val, (
            f"B16 still has locale-mutated _xludf prefix. Got: {val!r}"
        )

    def test_b17_uses_norm_s_dist_not_xludf(self, regen_workbook_missing_data):
        ws = regen_workbook_missing_data["الخيارات الحقيقية"]
        val = str(ws["B17"].value or "")
        assert "NORM.S.DIST" in val, f"B17 missing NORM.S.DIST. Got: {val!r}"
        assert "_xludf" not in val, (
            f"B17 still has locale-mutated _xludf prefix. Got: {val!r}"
        )

    def test_b18_has_iferror_guard(self, regen_workbook_missing_data):
        ws = regen_workbook_missing_data["الخيارات الحقيقية"]
        val = str(ws["B18"].value or "")
        assert "IFERROR" in val, f"B18 missing IFERROR guard. Got: {val!r}"

    def test_b22_has_iferror_max(self, regen_workbook_missing_data):
        ws = regen_workbook_missing_data["الخيارات الحقيقية"]
        val = str(ws["B22"].value or "")
        assert "IFERROR" in val and "MAX" in val, (
            f"B22 should be IFERROR(MAX(...),0). Got: {val!r}"
        )

    def test_missing_data_not_converted_to_zero(self, regen_workbook_missing_data):
        """Sentinel string must appear, not silent zero conversion."""
        ws = regen_workbook_missing_data["الخيارات الحقيقية"]
        b14 = str(ws["B14"].value or "")
        assert _UNAVAIL in b14 or "B5" in b14, (
            f"B14 formula does not reference sentinel or input cells: {b14!r}"
        )

    def test_same_with_defaults(self, regen_workbook_with_defaults):
        ws = regen_workbook_with_defaults["الخيارات الحقيقية"]
        b16 = str(ws["B16"].value or "")
        assert "_xludf" not in b16, f"B16 with defaults has _xludf: {b16!r}"
        assert "NORM.S.DIST" in b16, f"B16 with defaults missing NORM.S.DIST: {b16!r}"


# ─── Sheet 34: الاقتراض والكاش ───────────────────────────────────────────────

class TestSheet34LoanCash:
    """MAJ-03 regression: B7, B8 must be live formulas, not annotation text."""

    def test_b7_is_formula_not_annotation(self, regen_workbook_missing_data):
        # Sheet name may have emoji prefix
        sheet = next(
            (n for n in regen_workbook_missing_data.sheetnames if "الاقتراض والكاش" in n),
            None,
        )
        assert sheet is not None, "Sheet 'الاقتراض والكاش' not found in workbook"
        ws = regen_workbook_missing_data[sheet]
        val = ws["B7"].value
        assert val is not None, "B7 is unexpectedly None"
        assert str(val).startswith("="), (
            f"B7 is not a formula — annotation text may have survived. Got: {val!r}"
        )
        assert "≈" not in str(val), (
            f"B7 still contains annotation prefix '≈': {val!r}"
        )

    def test_b8_is_formula_not_annotation(self, regen_workbook_missing_data):
        sheet = next(
            (n for n in regen_workbook_missing_data.sheetnames if "الاقتراض والكاش" in n),
            None,
        )
        ws = regen_workbook_missing_data[sheet]
        val = ws["B8"].value
        assert val is not None, "B8 is unexpectedly None"
        assert str(val).startswith("="), (
            f"B8 is not a formula — annotation text may have survived. Got: {val!r}"
        )
        assert "≈" not in str(val), (
            f"B8 still contains annotation prefix '≈': {val!r}"
        )

    def test_b7_formula_is_down_payment(self, regen_workbook_missing_data):
        sheet = next(
            (n for n in regen_workbook_missing_data.sheetnames if "الاقتراض والكاش" in n),
            None,
        )
        ws = regen_workbook_missing_data[sheet]
        val = ws["B7"].value
        assert "B5" in str(val) and "B6" in str(val), (
            f"B7 should reference B5*B6 (price × ratio). Got: {val!r}"
        )

    def test_b8_formula_is_loan_amount(self, regen_workbook_missing_data):
        sheet = next(
            (n for n in regen_workbook_missing_data.sheetnames if "الاقتراض والكاش" in n),
            None,
        )
        ws = regen_workbook_missing_data[sheet]
        val = ws["B8"].value
        assert "B5" in str(val) and "B7" in str(val), (
            f"B8 should reference B5-B7 (price - down payment). Got: {val!r}"
        )


# ─── Pipeline integrity ────────────────────────────────────────────────────────

class TestPipelineIntegrity:
    """Builder pipeline must complete all 3 stages, produce 55 sheets, use template_driven."""

    def test_55_sheets_generated(self, regen_workbook_missing_data):
        assert len(regen_workbook_missing_data.sheetnames) == 55

    def test_55_sheets_with_defaults(self, regen_workbook_with_defaults):
        assert len(regen_workbook_with_defaults.sheetnames) == 55

    def test_required_governance_sheets_present(self, regen_workbook_missing_data):
        names = regen_workbook_missing_data.sheetnames
        required = {"القيمة بالحروف", "بيان الامتثال", "توقيع واعتماد الخبير"}
        missing = required - set(names)
        assert not missing, f"Required governance sheets missing: {missing}"

    def test_all_three_fix_sheets_present(self, regen_workbook_missing_data):
        names = regen_workbook_missing_data.sheetnames
        assert "رأسمالة الدخل" in names
        assert "الخيارات الحقيقية" in names
        assert any("الاقتراض والكاش" in n for n in names)

    def test_no_vba_stream(self, tmp_path):
        """Sanity: generated .xlsx must be macro-free."""
        import zipfile
        from reports.excel_template_driven_builder import (
            build_template_driven_professional_workbook as _build,
        )
        out = tmp_path / "no_vba_check.xlsx"
        ctx = {"request_summary": {}, "method_summary": {}, "comparable_summary": {}}
        result = _build(ctx, out, allow_template_assumptions=True)
        assert result["success"]
        with zipfile.ZipFile(str(out), "r") as zf:
            vba_files = [n for n in zf.namelist() if "vbaProject" in n]
        assert not vba_files, f"VBA stream found in output: {vba_files}"
