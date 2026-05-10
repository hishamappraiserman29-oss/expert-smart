"""
Focused integration test: Mass Appraisal export — template vs fallback path.

Scenarios:
  1. Template exists → build_mass_appraisal_workbook() returns .xlsm bytes
     (non-empty, starts with PK magic for ZIP/OOXML).
  2. Template temporarily renamed/absent →
     build_mass_appraisal_workbook() falls back to openpyxl builder (.xlsx bytes).
  3. Missing optional fields (ratio_study, calibration_preview, governance, etc.)
     → no crash; returns bytes in both template and fallback paths.

Run:
    python _test_mass_appraisal_export_integration.py
"""
from __future__ import annotations

import os
import sys
import shutil
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "core_engine"))

from core_engine.mass_appraisal_excel import build_mass_appraisal_workbook
from core_engine.reports.excel_template_renderer import MASS_APPRAISAL_TEMPLATE

_PK_MAGIC = b"PK\x03\x04"   # ZIP/OOXML file magic bytes

# ── Minimal result dict (new schema) ──────────────────────────────────────────
_MINIMAL_RESULT: dict = {
    "n_units":              2,
    "total_portfolio_value": 8_200_000.0,
    "avg_ppm":              18_500.0,
    "method":               "avm",
    "purpose":              "fair_market",
    "location":             "Cairo",
    "units": [
        {
            "id":        "P001",
            "area":      120.0,
            "floor":     3,
            "year_built": 2010,
            "condition": "good",
            "avm_ppm":   18_000.0,
            "adj_ppm":   18_200.0,
            "final_ppm": 18_200.0,
            "unit_value": 2_184_000.0,
            "sale_price": 2_100_000.0,
        },
        {
            "id":        "P002",
            "area":      200.0,
            "floor":     1,
            "year_built": 2015,
            "condition": "excellent",
            "avm_ppm":   19_000.0,
            "adj_ppm":   19_200.0,
            "final_ppm": 19_200.0,
            "unit_value": 3_840_000.0,
        },
    ],
    "ratio_study": {
        "n_sales":      1,
        "median_ratio": 0.984,
        "mean_ratio":   0.984,
        "cod":          3.8,
        "prd":          1.01,
        "cod_pass":     True,
        "prd_pass":     True,
    },
    "portfolio_summary": {
        "min_value":  2_184_000.0,
        "max_value":  3_840_000.0,
        "median_val": 3_012_000.0,
    },
}


def _check(label: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {label}" + (f" — {detail}" if detail else ""))
    return ok


def _is_ooxml(data: bytes) -> bool:
    return data[:4] == _PK_MAGIC


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 1: Template present
# ─────────────────────────────────────────────────────────────────────────────
def test_template_path() -> bool:
    print("\n[Scenario 1] Template present => expect .xlsm bytes from template")
    if not MASS_APPRAISAL_TEMPLATE.is_file():
        print("  [SKIP] Template file not found on disk — skipping scenario 1")
        return True

    data = build_mass_appraisal_workbook(_MINIMAL_RESULT)
    all_ok = True
    all_ok &= _check("Returns bytes",      isinstance(data, bytes))
    all_ok &= _check("Non-empty",          len(data) > 0, f"{len(data):,} bytes")
    all_ok &= _check("Valid OOXML (PK magic)", _is_ooxml(data))
    return all_ok


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 2: Template absent → fallback to openpyxl builder
# ─────────────────────────────────────────────────────────────────────────────
def test_fallback_path() -> bool:
    print("\n[Scenario 2] Template absent => expect openpyxl fallback bytes")
    if not MASS_APPRAISAL_TEMPLATE.is_file():
        print("  [SKIP] Template not found — fallback is already the only path")
        data = build_mass_appraisal_workbook(_MINIMAL_RESULT)
        all_ok = True
        all_ok &= _check("Returns bytes (fallback)", isinstance(data, bytes))
        all_ok &= _check("Non-empty",                len(data) > 0)
        all_ok &= _check("Valid OOXML (PK magic)",   _is_ooxml(data))
        return all_ok

    # Temporarily move the template out of the way
    backup = str(MASS_APPRAISAL_TEMPLATE) + ".bak_test"
    shutil.move(str(MASS_APPRAISAL_TEMPLATE), backup)
    try:
        data = build_mass_appraisal_workbook(_MINIMAL_RESULT)
        all_ok = True
        all_ok &= _check("Returns bytes (fallback)", isinstance(data, bytes))
        all_ok &= _check("Non-empty",                len(data) > 0, f"{len(data):,} bytes")
        all_ok &= _check("Valid OOXML (PK magic)",   _is_ooxml(data))
    finally:
        shutil.move(backup, str(MASS_APPRAISAL_TEMPLATE))
        _check("Template restored after test", MASS_APPRAISAL_TEMPLATE.is_file())
    return all_ok


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 3: Missing optional fields — no crash
# ─────────────────────────────────────────────────────────────────────────────
def test_missing_optional_fields() -> bool:
    print("\n[Scenario 3] Missing optional fields => no crash, returns bytes")
    all_ok = True

    # Minimal result with only mandatory key
    bare = {"n_units": 0, "units": []}
    try:
        data = build_mass_appraisal_workbook(bare)
        all_ok &= _check("No crash with bare result",    True)
        all_ok &= _check("Returns bytes",                isinstance(data, bytes))
        all_ok &= _check("Non-empty",                    len(data) > 0)
    except Exception as exc:
        all_ok &= _check("No crash with bare result", False, str(exc))

    # Full result but all optional args are None
    try:
        data2 = build_mass_appraisal_workbook(
            _MINIMAL_RESULT,
            ratio_study=None,
            calibration_preview=None,
            governance=None,
            model_cycle=None,
            sales_verification=None,
        )
        all_ok &= _check("No crash with all optionals=None", True)
        all_ok &= _check("Returns bytes",                    isinstance(data2, bytes))
    except Exception as exc:
        all_ok &= _check("No crash with all optionals=None", False, str(exc))

    # Optional dicts present but partially populated
    partial_ratio = {
        "status": "success",
        "summary": {
            "portfolio_metrics": {
                "median_ratio": 0.98,
                "cod": 5.1,
                "prd": 1.02,
            }
        },
    }
    partial_calib = {
        "status": "success",
        "portfolio_calibration": {
            "calibration_factor": 1.02,
            "sample_size": 50,
        },
    }
    partial_gov = {
        "governance_id": "GOV-001",
        "status": "approved",
    }
    try:
        data3 = build_mass_appraisal_workbook(
            _MINIMAL_RESULT,
            ratio_study=partial_ratio,
            calibration_preview=partial_calib,
            governance=partial_gov,
        )
        all_ok &= _check("No crash with partial optional dicts", True)
        all_ok &= _check("Returns bytes",                         isinstance(data3, bytes))
        all_ok &= _check("Non-empty",                             len(data3) > 0)
    except Exception as exc:
        all_ok &= _check("No crash with partial optional dicts", False, str(exc))

    return all_ok


# ─────────────────────────────────────────────────────────────────────────────
def main() -> int:
    print("\n=== Mass Appraisal Export Integration Test ===")
    results = [
        test_template_path(),
        test_fallback_path(),
        test_missing_optional_fields(),
    ]
    all_pass = all(results)
    print(f"\n{'ALL SCENARIOS PASSED' if all_pass else 'SOME SCENARIOS FAILED'}\n")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
