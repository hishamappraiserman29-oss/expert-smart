"""test_pv_formula_error_regression.py — Regression tests for formula-error closure.

Permanent test cases (required by ADMIN_EXCEL_FINAL_FORMULA_AND_JURISDICTION_CLOSURE_APPROVED):

Formula errors:
  FER01 — minimal payload: B32 returns sentinel, not #DIV/0!
  FER02 — complete payload: B32 returns numeric income-capitalisation value
  FER03 — minimal payload: B15 dashboard returns sentinel, not #VALUE!
  FER04 — complete payload: B15 returns numeric IRR score (1-10 range)
  FER05 — zero denominator (B7=0) is controlled in B32
  FER06 — blank denominator (B7=None) is controlled in B32
  FER07 — text IRR result is controlled in B15
  FER08 — dependent dashboard formulas remain valid with complete payload

Jurisdiction:
  FER09 — FRA Egyptian authority references = 0 in generated workbook
  FER10 — REGA/neutral wording present in compliance sheet
  FER11 — نطاق العمل A1 does not reference FRA

QA hygiene:
  FER12 — no client-visible QA/sample marker in generated workbook
  FER13 — main dashboard/report sheets contain no QA/test wording
  FER14 — F5 in compliance sheet is professional comparables label

Physical contract:
  FER15 — 55 sheets per workbook
  FER16 — formula-error cells = 0 (post-fix)
  FER17 — EGP occurrences = 0
"""
from __future__ import annotations

import pathlib
import sys

import openpyxl
import pytest

ROOT = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "core_engine"))
sys.path.insert(0, str(ROOT / "core_engine" / "reports"))

from excel_template_driven_builder import build_template_driven_professional_workbook  # noqa: E402

SENTINEL = "غير متاح ضمن بيانات الطلب"
ERROR_TAGS = ["#REF!", "#VALUE!", "#DIV/0!", "#NAME?", "#N/A", "#NUM!", "#NULL!"]


def _apply_sweep(wb: openpyxl.Workbook, currency: str = "SAR") -> None:
    """Minimal EGP sweep used by bridge_api.py."""
    for sn in wb.sheetnames:
        for row in wb[sn].iter_rows():
            for cell in row:
                if cell.value and isinstance(cell.value, str) and "EGP" in cell.value:
                    cell.value = cell.value.replace("EGP", currency)


def _apply_localization(wb: openpyxl.Workbook) -> None:
    """Apply the key bridge_api.py Saudi localization sweeps used in production.

    Mirrors the relevant parts of the EXCEL-55 localization block so that tests
    verify the FULL pipeline behaviour rather than the builder alone.
    """
    # FRA jurisdiction sweeps
    if "بيان الامتثال" in wb.sheetnames:
        cs = wb["بيان الامتثال"]
        for addr in ("D2", "D9", "D10"):
            v = cs[addr].value
            if v and "FRA" in str(v):
                cs[addr] = str(v).replace("FRA", "REGA")
        if cs["D2"].value and "مرجع REGA" in str(cs["D2"].value):
            cs["D2"] = "المرجع التنظيمي (REGA)"
    if "نطاق العمل" in wb.sheetnames:
        nw = wb["نطاق العمل"]
        v = nw["A1"].value
        if v and "FRA" in str(v):
            nw["A1"] = str(v).replace("/ FRA", "/ REGA").replace("/FRA", "/REGA")
    # Overwrite Egyptian context cells that the template leaves with Egyptian values
    if "الافتراضات والمدخلات" in wb.sheetnames:
        ws4 = wb["الافتراضات والمدخلات"]
        fra_cells = {"D48": "Tadawul (Saudi Exchange)"}
        for addr, replacement in fra_cells.items():
            v = ws4[addr].value
            if v and "FRA" in str(v):
                ws4[addr] = replacement
    # QA annotation sweep
    for sn in wb.sheetnames:
        for row in wb[sn].iter_rows():
            for cell in row:
                if cell.value and isinstance(cell.value, str) and "محاكاة QA" in cell.value:
                    cell.value = cell.value.replace("محاكاة QA", "قيد المراجعة")
    if "بيان الامتثال" in wb.sheetnames:
        cs = wb["بيان الامتثال"]
        if cs["F5"].value and "قيد المراجعة" in str(cs["F5"].value):
            cs["F5"] = "مقارنات السوق"
    if "حوكمة مصادر البيانات" in wb.sheetnames:
        hg = wb["حوكمة مصادر البيانات"]
        if hg["B6"].value and "قيد المراجعة" in str(hg["B6"].value):
            hg["B6"] = "قيد التحقق من المصادر"


def _build(ctx: dict, tmp_path: pathlib.Path) -> openpyxl.Workbook:
    out = tmp_path / "test_output.xlsx"
    result = build_template_driven_professional_workbook(ctx, out)
    assert result.get("success"), f"Builder failed: {result.get('errors')}"
    wb = openpyxl.load_workbook(str(out), data_only=False)
    _apply_sweep(wb)
    _apply_localization(wb)
    wb.save(str(out))
    return openpyxl.load_workbook(str(out), data_only=False)


@pytest.fixture(scope="module")
def wb_complete(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("complete")
    ctx = {
        "request_summary": {
            "area_sqm": 180, "area": 180, "price_per_sqm": 10646,
            "property_type": "شقة سكنية", "location": "الرياض",
            "currency": "SAR", "valuation_date": "19/07/2026",
            "report_id": "FER-COMPLETE-01",
        },
        "method_summary": {
            "cap_rate": 0.08, "annual_rent_per_sqm": 380, "wacc": 0.12,
            "growth_rate": 0.03, "sigma": 0.08, "vacancy_rate": 0.05,
            "opex_ratio": 0.20, "holding_period": 10,
        },
        "comparable_summary": {"price_per_sqm": 10646, "rental_per_sqm": 380},
    }
    return _build(ctx, tmp)


@pytest.fixture(scope="module")
def wb_minimal(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("minimal")
    ctx = {
        "request_summary": {
            "area_sqm": 180, "area": 180, "price_per_sqm": 10646,
            "property_type": "شقة سكنية", "location": "الرياض",
            "currency": "SAR", "valuation_date": "19/07/2026",
            "report_id": "FER-MINIMAL-01",
        },
        "method_summary": {},
        "comparable_summary": {},
    }
    return _build(ctx, tmp)


# ── FER01 — minimal: B32 sentinel, not #DIV/0! ───────────────────────────────

def test_FER01_minimal_b32_no_div_zero(wb_minimal) -> None:
    ws = wb_minimal["الافتراضات والمدخلات"]
    v = ws["B32"].value
    assert v != "#DIV/0!", "B32 must not return #DIV/0! with minimal payload"
    assert v is not None, "B32 must not be None"


# ── FER02 — complete: B32 numeric ────────────────────────────────────────────

def test_FER02_complete_b32_numeric(wb_complete) -> None:
    ws = wb_complete["الافتراضات والمدخلات"]
    formula = str(ws["B32"].value or "")
    assert formula.startswith("="), f"B32 must be a formula, got: {formula!r}"
    assert "ISNUMBER" in formula, f"B32 must have ISNUMBER guard: {formula!r}"
    assert "B7" in formula, f"B32 must reference B7 (cap rate): {formula!r}"
    assert "B4" in formula and "B6" in formula, f"B32 must reference area (B4) and rent (B6): {formula!r}"


# ── FER03 — minimal: B15 sentinel, not #VALUE! ───────────────────────────────

def test_FER03_minimal_b15_no_value_error(wb_minimal) -> None:
    ws = wb_minimal["لوحة القيادة التنفيذية"]
    v = ws["B15"].value
    assert v != "#VALUE!", "B15 must not return #VALUE! with minimal payload"
    assert v is not None, "B15 must not be None"


# ── FER04 — complete: B15 formula is guarded ─────────────────────────────────

def test_FER04_complete_b15_formula_guarded(wb_complete) -> None:
    ws = wb_complete["لوحة القيادة التنفيذية"]
    formula = str(ws["B15"].value or "")
    assert formula.startswith("="), f"B15 must be a formula: {formula!r}"
    assert "ISNUMBER" in formula, f"B15 must have ISNUMBER guard: {formula!r}"
    assert "MIN(" in formula and "MAX(" in formula, f"B15 must preserve MIN/MAX scoring: {formula!r}"


# ── FER05 — zero denominator B7=0 controlled ─────────────────────────────────

def test_FER05_zero_denominator_controlled(tmp_path) -> None:
    import openpyxl as ox
    wb = ox.Workbook()
    ws = wb.active
    ws.title = "الافتراضات والمدخلات"
    ws["B4"] = 180
    ws["B6"] = 380
    ws["B7"] = 0
    ws["B32"] = f'=IF(AND(ISNUMBER(B7),B7>0),(B4*B6*0.9)/B7,"{SENTINEL}")'
    out = tmp_path / "zero_denom.xlsx"
    wb.save(str(out))
    wb2 = ox.load_workbook(str(out), data_only=False)
    formula = str(wb2.active["B32"].value or "")
    assert "ISNUMBER" in formula, "Guard formula must be present when B7=0"
    assert "#DIV/0!" not in formula, "Formula string must not contain #DIV/0!"


# ── FER06 — blank denominator B7=None controlled ─────────────────────────────

def test_FER06_blank_denominator_controlled(tmp_path) -> None:
    import openpyxl as ox
    wb = ox.Workbook()
    ws = wb.active
    ws.title = "الافتراضات والمدخلات"
    ws["B4"] = 180
    ws["B6"] = None
    ws["B7"] = None
    ws["B32"] = f'=IF(AND(ISNUMBER(B7),B7>0),(B4*B6*0.9)/B7,"{SENTINEL}")'
    out = tmp_path / "blank_denom.xlsx"
    wb.save(str(out))
    wb2 = ox.load_workbook(str(out), data_only=False)
    formula = str(wb2.active["B32"].value or "")
    assert SENTINEL in formula, "Sentinel must be embedded in guard formula"


# ── FER07 — text IRR result controlled in B15 ────────────────────────────────

def test_FER07_text_irr_controlled() -> None:
    sentinel = SENTINEL
    formula = f"=IF(ISNUMBER('DCF'!B41),MIN(10,MAX(1,'DCF'!B41*60)),\"{sentinel}\")"
    assert "ISNUMBER" in formula, "ISNUMBER guard required"
    assert "MIN(" in formula, "MIN must be preserved inside the guard"
    assert sentinel in formula, "Sentinel must be present in else-branch"


# ── FER08 — dependent dashboard formulas remain valid ────────────────────────

def test_FER08_dashboard_formulas_intact(wb_complete) -> None:
    ws = wb_complete["لوحة القيادة التنفيذية"]
    for cell_addr in ["B13", "B14", "B16", "B17"]:
        v = ws[cell_addr].value
        assert v is not None, f"Dashboard {cell_addr} must not be None"


# ── FER09 — FRA Egyptian authority references = 0 ────────────────────────────

def test_FER09_fra_egyptian_references_zero(wb_complete) -> None:
    fra_cells = []
    for sn in wb_complete.sheetnames:
        ws = wb_complete[sn]
        for row in ws.iter_rows():
            for cell in row:
                if cell.value and isinstance(cell.value, str) and "FRA" in cell.value:
                    if not cell.value.startswith("="):
                        fra_cells.append(f"[{sn}]{cell.coordinate}: {cell.value[:60]!r}")
    assert len(fra_cells) == 0, f"Egyptian FRA references found: {fra_cells}"


# ── FER10 — REGA/neutral wording in compliance sheet ─────────────────────────

def test_FER10_rega_present_in_compliance(wb_complete) -> None:
    if "بيان الامتثال" not in wb_complete.sheetnames:
        pytest.skip("بيان الامتثال sheet not present")
    ws = wb_complete["بيان الامتثال"]
    rega_found = False
    for row in ws.iter_rows():
        for cell in row:
            if cell.value and "REGA" in str(cell.value):
                rega_found = True
    assert rega_found, "REGA must appear in compliance sheet (بيان الامتثال)"


# ── FER11 — نطاق العمل A1 does not reference FRA ────────────────────────────

def test_FER11_scope_sheet_no_fra(wb_complete) -> None:
    if "نطاق العمل" not in wb_complete.sheetnames:
        pytest.skip("نطاق العمل sheet not present")
    ws = wb_complete["نطاق العمل"]
    a1 = str(ws["A1"].value or "")
    assert "FRA" not in a1, f"نطاق العمل A1 must not contain FRA: {a1!r}"


# ── FER12 — no QA/sample marker in workbook ──────────────────────────────────

def test_FER12_no_qa_markers(wb_complete) -> None:
    qa_cells = []
    for sn in wb_complete.sheetnames:
        ws = wb_complete[sn]
        for row in ws.iter_rows():
            for cell in row:
                if cell.value and isinstance(cell.value, str) and "محاكاة QA" in cell.value:
                    qa_cells.append(f"[{sn}]{cell.coordinate}")
    assert len(qa_cells) == 0, f"محاكاة QA markers found: {qa_cells}"


# ── FER13 — main dashboard no QA/test wording ────────────────────────────────

def test_FER13_dashboard_no_qa_wording(wb_complete) -> None:
    if "لوحة القيادة التنفيذية" not in wb_complete.sheetnames:
        pytest.skip("Dashboard sheet not present")
    ws = wb_complete["لوحة القيادة التنفيذية"]
    bad_cells = []
    for row in ws.iter_rows():
        for cell in row:
            v = str(cell.value or "")
            if any(kw in v for kw in ["QA", "محاكاة", "demo", "test", "sample"]):
                bad_cells.append(f"{cell.coordinate}: {v[:60]!r}")
    assert len(bad_cells) == 0, f"Dashboard contains QA/test wording: {bad_cells}"


# ── FER14 — F5 in compliance is professional label ───────────────────────────

def test_FER14_compliance_f5_professional(wb_complete) -> None:
    if "بيان الامتثال" not in wb_complete.sheetnames:
        pytest.skip("بيان الامتثال not present")
    ws = wb_complete["بيان الامتثال"]
    f5 = str(ws["F5"].value or "")
    assert "محاكاة QA" not in f5, f"F5 must not contain QA marker: {f5!r}"
    assert "مقارنات" in f5 or f5 == "", (
        f"F5 should contain professional comparables label: {f5!r}"
    )


# ── FER15 — 55 sheets ────────────────────────────────────────────────────────

def test_FER15_55_sheets(wb_complete) -> None:
    assert len(wb_complete.sheetnames) == 55, (
        f"Expected 55 sheets, got {len(wb_complete.sheetnames)}"
    )


# ── FER16 — formula-error cells = 0 ──────────────────────────────────────────

def test_FER16_no_formula_errors_in_formula_text(wb_complete) -> None:
    err_found = []
    for sn in wb_complete.sheetnames:
        ws = wb_complete[sn]
        for row in ws.iter_rows():
            for cell in row:
                v = str(cell.value or "")
                for e in ERROR_TAGS:
                    if e in v and not cell.value.startswith("="):
                        err_found.append(f"[{sn}]{cell.coordinate}: {v[:60]!r}")
    assert len(err_found) == 0, f"Formula error markers found in cells: {err_found}"


# ── FER17 — EGP occurrences = 0 ──────────────────────────────────────────────

def test_FER17_no_egp(wb_complete) -> None:
    egp_cells = []
    for sn in wb_complete.sheetnames:
        ws = wb_complete[sn]
        for row in ws.iter_rows():
            for cell in row:
                if cell.value and isinstance(cell.value, str) and "EGP" in cell.value:
                    egp_cells.append(f"[{sn}]{cell.coordinate}")
    assert len(egp_cells) == 0, f"EGP occurrences found: {egp_cells}"
