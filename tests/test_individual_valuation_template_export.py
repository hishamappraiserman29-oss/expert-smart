"""
Focused test: Individual Valuation Excel export — template vs fallback path.

Scenarios:
  1. Template present => ExcelReportBuilder.build() uses template, output is OOXML.
  2. Template temporarily absent => falls back to openpyxl builder, OOXML bytes.
  3. Missing optional fields in AssetValuationResult => no crash.
  4. build_individual_valuation_report() standalone with minimal context.
  5. build_individual_valuation_report() with missing template => returns None.

Run:
    python _test_individual_valuation_template_export.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

# Allow direct project imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "core_engine"))

from core_engine.reports.excel_template_renderer import (
    INDIVIDUAL_VALUATION_TEMPLATE,
    build_individual_valuation_report,
)
from core_engine.reports.excel_builder import ExcelReportBuilder

# ── Import project dataclasses ────────────────────────────────────────────────
from core_engine.adapters.asset import AssetValuationResult
from core_engine.engines.base import AuditEntry, ValidationIssue

_PK_MAGIC = b"PK\x03\x04"


def _check(label: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {label}" + (f" — {detail}" if detail else ""))
    return ok


def _is_ooxml(path: str) -> bool:
    with open(path, "rb") as f:
        return f.read(4) == _PK_MAGIC


def _make_result(
    with_audit: bool = True,
    with_issues: bool = True,
    with_comparables: bool = True,
) -> AssetValuationResult:
    audit: list[AuditEntry] = []
    if with_audit:
        audit = [
            AuditEntry(
                step_name="Comparable Sales Approach",
                inputs={"comparables": 5},
                outputs={"value": 4_800_000},
                formula="median(comparables) * area",
                references=["EGVS_3.1"],
            ),
            AuditEntry(
                step_name="Cost Approach",
                inputs={"replacement_cost": 3_500_000},
                outputs={"value": 3_400_000},
                formula="replacement_cost - depreciation",
                references=["EGVS_3.2"],
            ),
        ]
    issues: list[ValidationIssue] = []
    if with_issues:
        issues = [
            ValidationIssue(severity="warning", code="LOW_COMP_COUNT", message="Only 3 comparables found"),
        ]
    meta: dict = {
        "location":        "Cairo - Maadi",
        "area":            180.0,
        "floor_area_m2":   180.0,
        "comparable":      4_800_000,
        "cost":            3_400_000,
        "income":          4_200_000,
        "reviewer_name":   "Hisham Elmahdy",
        "report_id":       "RPT-2026-TEST",
        "client_name":     "Cairo Bank",
        "valuation_date":  "2026-05-10",
    }
    if with_comparables:
        meta["comparables"] = [
            {"Address": "Maadi St 1", "Sale Price": 4_700_000, "Area": 175},
            {"Address": "Maadi St 5", "Sale Price": 4_900_000, "Area": 185},
        ]
    return AssetValuationResult(
        asset_type="residential",
        primary_purpose="market_value",
        primary_value=Decimal("4_500_000"),
        confidence="high",
        alternative_values={},
        weights_applied={"comparable": 0.6, "cost": 0.2, "income": 0.2},
        audit_trail=audit,
        issues=issues,
        metadata=meta,
        disclosures=["EGVS_1.0", "EGVS_3.1", "IFRS_13-54"],
    )


# ── Scenario 1: Template present + .xlsx requested => actual output is .xlsm ──
def test_template_path() -> bool:
    print("\n[Scenario 1] Template present + .xlsx requested => output promoted to .xlsm")
    if not INDIVIDUAL_VALUATION_TEMPLATE.is_file():
        print("  [SKIP] Template file not found on disk")
        return True

    result = _make_result()
    with tempfile.TemporaryDirectory() as tmp:
        requested  = os.path.join(tmp, "individual_report.xlsx")
        expected   = os.path.join(tmp, "individual_report.xlsm")
        returned   = ExcelReportBuilder(result).build(requested)

        all_ok = True
        all_ok &= _check(
            "Returned path ends with .xlsm (not .xlsx)",
            returned.endswith(".xlsm"),
            returned,
        )
        all_ok &= _check(
            "Returned path equals expected .xlsm path",
            returned == expected,
            returned,
        )
        all_ok &= _check(".xlsm file exists on disk",  os.path.isfile(expected))
        all_ok &= _check(".xlsx file NOT created",     not os.path.isfile(requested))
        if os.path.isfile(expected):
            size = os.path.getsize(expected)
            all_ok &= _check("Output non-empty", size > 0, f"{size:,} bytes")
            all_ok &= _check("Valid OOXML magic", _is_ooxml(expected))
    return all_ok


# ── Scenario 2: Template absent => fallback writes .xlsx unchanged ─────────────
def test_fallback_path() -> bool:
    print("\n[Scenario 2] Template absent => fallback output remains .xlsx")
    if not INDIVIDUAL_VALUATION_TEMPLATE.is_file():
        print("  [INFO] Template already absent — fallback is the only path")
        result = _make_result()
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "fallback_report.xlsx")
            returned = ExcelReportBuilder(result).build(out)
            all_ok = True
            all_ok &= _check("Returned path ends with .xlsx", returned.endswith(".xlsx"), returned)
            all_ok &= _check("Returned path equals requested", returned == out)
            all_ok &= _check("Output file exists",              os.path.isfile(out))
            all_ok &= _check("Valid OOXML magic",               _is_ooxml(out) if os.path.isfile(out) else False)
        return all_ok

    backup = str(INDIVIDUAL_VALUATION_TEMPLATE) + ".bak_test"
    shutil.move(str(INDIVIDUAL_VALUATION_TEMPLATE), backup)
    all_ok = True
    try:
        result = _make_result()
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "fallback_report.xlsx")
            returned = ExcelReportBuilder(result).build(out)
            all_ok &= _check("No crash with absent template",   True)
            all_ok &= _check("Returned path ends with .xlsx",   returned.endswith(".xlsx"), returned)
            all_ok &= _check("Returned path equals requested",  returned == out)
            all_ok &= _check("Output .xlsx exists",              os.path.isfile(out), out)
            all_ok &= _check(".xlsm NOT created",                not os.path.isfile(out.replace(".xlsx", ".xlsm")))
            if os.path.isfile(out):
                all_ok &= _check("Valid OOXML magic", _is_ooxml(out))
    finally:
        shutil.move(backup, str(INDIVIDUAL_VALUATION_TEMPLATE))
        _check("Template restored", INDIVIDUAL_VALUATION_TEMPLATE.is_file())
    return all_ok


# ── Scenario 3: Missing optional fields => no crash ───────────────────────────
def test_missing_optional_fields() -> bool:
    print("\n[Scenario 3] Missing optional fields => no crash")
    all_ok = True

    # Bare result — no audit, no issues, no comparables, no metadata
    bare = AssetValuationResult(
        asset_type="land",
        primary_purpose="market_value",
        primary_value=None,
        confidence="low",
    )
    try:
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "bare_report.xlsx")
            ExcelReportBuilder(bare).build(out)
        all_ok &= _check("No crash with bare result (no metadata)", True)
    except Exception as exc:
        all_ok &= _check("No crash with bare result (no metadata)", False, str(exc))

    # Result with no audit trail, no issues, no disclosures
    sparse = _make_result(with_audit=False, with_issues=False, with_comparables=False)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "sparse_report.xlsx")
            ret = ExcelReportBuilder(sparse).build(out)
        all_ok &= _check("No crash — no audit/issues/comparables", True)
        all_ok &= _check("Returns filename",                        ret is not None)
    except Exception as exc:
        all_ok &= _check("No crash — no audit/issues/comparables", False, str(exc))

    return all_ok


# ── Scenario 4: standalone build_individual_valuation_report() ────────────────
def test_standalone_renderer() -> bool:
    print("\n[Scenario 4] build_individual_valuation_report() standalone")
    if not INDIVIDUAL_VALUATION_TEMPLATE.is_file():
        print("  [SKIP] Template not found")
        return True

    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "standalone.xlsm")
        result = build_individual_valuation_report(
            output_path=out,
            context={
                "report_date":       "2026-05-10",
                "valuation_date":    "2026-05-01",
                "client_name":       "Cairo Bank",
                "property_type":     "residential",
                "location":          "Cairo - Maadi",
                "area":              180,
                "valuation_purpose": "mortgage_lending",
                "final_value":       4_500_000,
                "confidence":        "high",
                "reviewer_name":     "Hisham Elmahdy",
                "report_id":         "RPT-2026-001",
            },
            tables={
                "comparables": [
                    {"Address": "Maadi St 1", "Sale Price": 4_700_000},
                    {"Address": "Maadi St 5", "Sale Price": 4_900_000},
                ],
                "valuation_methods": [
                    {"Approach": "Comparable Sales", "Value (EGP)": 4_800_000, "Weight": 0.6},
                    {"Approach": "Cost Approach",    "Value (EGP)": 3_400_000, "Weight": 0.2},
                    {"Approach": "Income Approach",  "Value (EGP)": 4_200_000, "Weight": 0.2},
                ],
                "audit_trail": [
                    {"Step": "Comparable Sales", "Formula": "median * area", "References": "EGVS_3.1"},
                ],
                "assumptions": [
                    {"Reference": "EGVS_1.0"},
                    {"Reference": "IFRS_13-54"},
                ],
                "issues": [
                    {"Severity": "warning", "Code": "LOW_COMP_COUNT", "Message": "3 comparables only"},
                ],
            },
        )
        all_ok = True
        all_ok &= _check("Returns Path (not None)", result is not None)
        all_ok &= _check("Output file exists",       os.path.isfile(out), out)
        if os.path.isfile(out):
            size = os.path.getsize(out)
            all_ok &= _check("Non-empty",             size > 0, f"{size:,} bytes")
            all_ok &= _check("Valid OOXML magic",     _is_ooxml(out))
    return all_ok


# ── Scenario 5: missing template => standalone returns None ───────────────────
def test_missing_template_returns_none() -> bool:
    print("\n[Scenario 5] Missing template => build_individual_valuation_report() returns None")
    with tempfile.TemporaryDirectory() as tmp:
        result = build_individual_valuation_report(
            output_path=os.path.join(tmp, "should_not_exist.xlsm"),
            context={},
            template_path="templates/reports/__nonexistent__.xlsm",
        )
        ok = _check("Returns None for missing template", result is None)
    return ok


# ─────────────────────────────────────────────────────────────────────────────
def main() -> int:
    print("\n=== Individual Valuation Template Export Test ===")
    results = [
        test_template_path(),
        test_fallback_path(),
        test_missing_optional_fields(),
        test_standalone_renderer(),
        test_missing_template_returns_none(),
    ]
    all_pass = all(results)
    print(f"\n{'ALL SCENARIOS PASSED' if all_pass else 'SOME SCENARIOS FAILED'}\n")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
