# -*- coding: utf-8 -*-
"""
Batch 8 — Production Activation tests.
17 tests verifying the production activation execution.
Run with .venv/Scripts/python.exe -m pytest (no skips expected).
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

import pytest

PROJ = pathlib.Path(__file__).resolve().parent.parent.parent
CE   = PROJ / "core_engine"
BASE = CE / "instance" / "manual_review_outputs" / "professional_valuation_template_driven_production_activation"
AUDITS    = BASE / "audits"
FINAL     = BASE / "final_report"
VIS_OUT   = BASE / "visual_previews"
TEST_LOGS = BASE / "test_logs"


def _j(name: str) -> dict:
    return json.loads((AUDITS / name).read_text(encoding="utf-8"))


def _fj(name: str) -> dict:
    return json.loads((FINAL / name).read_text(encoding="utf-8"))


# ── Test 01 — Dependencies install from declared manifest ─────────────────────
def test_01_dependencies_install_from_manifest():
    dep = _j("01_dependency_reproducibility.json")
    assert dep["overall"] == "PASS", (
        f"Dependency reproducibility failed: {dep.get('checks')}"
    )
    assert dep["checks"].get("install") == "PASS", "Clean-env install failed"


# ── Test 02 — Clean environment imports all required packages ─────────────────
def test_02_clean_env_imports_all_packages():
    dep = _j("01_dependency_reproducibility.json")
    for pkg in ("import_openpyxl", "import_PyMuPDF", "import_matplotlib", "import_win32com"):
        assert dep["checks"].get(pkg) == "PASS", (
            f"Clean-env import failed for {pkg}: {dep['checks'].get(pkg)}"
        )


# ── Test 03 — Excel COM 16.0 works ───────────────────────────────────────────
def test_03_excel_com_16_works():
    dep  = _j("01_dependency_reproducibility.json")
    gate = _j("02_preproduction_gate.json")
    assert dep["checks"].get("excel_com_dispatch") == "PASS", (
        "Excel COM dispatch failed in clean env"
    )
    assert gate["checks"].get("excel_com_16") == "PASS", (
        f"Excel COM 16.0 failed in gate: {gate['checks'].get('excel_com_16')}"
    )
    assert gate["checks"].get("excel_version") == "16.0", (
        f"Expected Excel 16.0, got {gate['checks'].get('excel_version')!r}"
    )


# ── Test 04 — Default flag remains disabled in code ──────────────────────────
def test_04_default_flag_disabled_in_code():
    flag_val = os.environ.get("PV_TEMPLATE_DRIVEN_EXCEL_ENABLED", "")
    assert flag_val.lower() not in ("1", "true", "yes", "on"), (
        f"Flag must be disabled by default, got: {flag_val!r}"
    )
    gate = _j("02_preproduction_gate.json")
    assert gate["checks"].get("feature_flag_currently_disabled") == "PASS", (
        "Gate audit says flag was active in normal process"
    )
    # Verify code default: _is_template_driven_excel_enabled with no env var returns False
    pvo_path = CE / "professional_valuation_outputs.py"
    src = pvo_path.read_text(encoding="utf-8")
    assert 'return val in ("1", "true", "yes", "on")' in src, (
        "Default disabled logic missing from pvo code"
    )


# ── Test 05 — Production process flag was explicitly enabled ──────────────────
def test_05_production_process_flag_enabled():
    flag_doc = _j("03_production_flag_activation.json")
    assert flag_doc["flag_value_used"] == "1", (
        "Production flag was not recorded as enabled"
    )
    assert flag_doc["flag_scope"] == "process-local only", (
        "Flag scope must be process-local only"
    )
    assert flag_doc["global_env_not_set"] is True, (
        "Flag was set globally (machine or user level)"
    )


# ── Test 06 — Smoke request used template_driven ──────────────────────────────
def test_06_smoke_uses_template_driven():
    smoke = _j("04_production_smoke_result.json")
    assert smoke["smoke_status"] == "PASS", (
        f"Production smoke failed: {smoke.get('checks')}"
    )
    assert smoke["builder_used"] == "template_driven", (
        f"Expected template_driven, got {smoke['builder_used']!r}"
    )
    assert smoke["checks"]["builder_used_template_driven"] is True
    assert smoke["checks"]["fallback_used"] is False


# ── Test 07 — Smoke output has 55 sheets ─────────────────────────────────────
def test_07_smoke_output_55_sheets():
    smoke = _j("04_production_smoke_result.json")
    assert smoke.get("sheet_count") == 55, (
        f"Expected 55 sheets, got {smoke.get('sheet_count')}"
    )
    assert smoke["checks"]["sheet_count_55"] is True


# ── Test 08 — Fallback health check passes ────────────────────────────────────
def test_08_fallback_health_pass():
    fb = _j("05_production_fallback_health.json")
    assert fb["status"] == "PASS", (
        f"Fallback health failed: {fb.get('checks')}"
    )
    assert fb["checks"]["routes_to_legacy_fallback"] is True, (
        "Fallback did not route to legacy_fallback"
    )
    assert fb["checks"]["legacy_output_published"] is True, (
        "Legacy fallback output not published"
    )


# ── Test 09 — No partial file is published ───────────────────────────────────
def test_09_no_partial_file_published():
    fb = _j("05_production_fallback_health.json")
    assert fb["checks"]["partial_not_published"] is True, (
        "A partial workbook was published during fallback"
    )
    smoke = _j("04_production_smoke_result.json")
    assert smoke["checks"].get("temp_file_cleaned") is True, (
        "Temporary file was not cleaned after smoke"
    )


# ── Test 10 — Source templates remain unchanged ───────────────────────────────
def test_10_source_templates_unchanged():
    summary = _fj("production_activation_summary.json")
    assert summary["source_template_hashes"]["unchanged"] is True, (
        "Source template was mutated during Batch 8"
    )


# ── Test 11 — Production visual samples exist ─────────────────────────────────
def test_11_production_visual_samples_exist():
    visual = _j("07_production_real_visual_sample.json")
    assert visual["renderer_used"] == "Excel COM", (
        f"Expected Excel COM, got {visual['renderer_used']!r}"
    )
    assert visual["total_pngs"] > 0, "No PNGs generated"
    assert len(visual["full_55_sheet_workbooks"]) >= 1, (
        "No full-55-sheet visual samples"
    )
    assert len(visual["priority_8_sheet_workbooks"]) >= 1, (
        "No priority visual samples"
    )


# ── Test 12 — No critical visual defect exists ───────────────────────────────
def test_12_no_critical_visual_defects():
    visual = _j("07_production_real_visual_sample.json")
    assert visual["critical_defects"] == 0, (
        f"{visual['critical_defects']} critical visual defect(s)"
    )
    for section in ("full_55_sheet_workbooks", "priority_8_sheet_workbooks"):
        for wb in visual[section]:
            assert wb.get("fail_count", 0) == 0, (
                f"Failed sheets in {wb.get('request_id')}: {wb.get('fail_count')}"
            )


# ── Test 13 — Rollback returns routing to legacy ──────────────────────────────
def test_13_rollback_returns_legacy():
    rb = _j("08_production_rollback_verification.json")
    assert rb["rollback_status"] == "PASS", (
        f"Rollback test failed: {rb.get('checks')}"
    )
    assert rb["checks"].get("builder_is_legacy") is True, (
        "After rollback, builder was not 'legacy'"
    )
    assert rb["checks"].get("legacy_output_ok") is True, (
        "Legacy output generation failed after rollback"
    )


# ── Test 14 — Reactivation returns routing to template_driven ────────────────
def test_14_reactivation_returns_template():
    rb = _j("08_production_rollback_verification.json")
    assert rb["checks"].get("reactivation_uses_template") is True, (
        "After reactivation, builder was not 'template_driven'"
    )
    assert rb["checks"].get("reactivation_ok") is True, (
        "Template output generation failed after reactivation"
    )


# ── Test 15 — No orphan Excel process remains ─────────────────────────────────
def test_15_no_orphan_excel_processes():
    mon = _j("06_production_monitoring_summary.json")
    assert mon["orphan_excel_processes"] == 0, (
        f"Orphan Excel processes in monitoring: {mon['orphan_excel_processes']}"
    )
    visual = _j("07_production_real_visual_sample.json")
    assert visual["orphan_excel_after_visual"] == 0, (
        f"Orphan Excel processes after visual rendering: {visual['orphan_excel_after_visual']}"
    )


# ── Test 16 — No incomplete temporary files remain ────────────────────────────
def test_16_no_incomplete_temp_files():
    mon = _j("06_production_monitoring_summary.json")
    assert mon["incomplete_temporary_files"] == 0, (
        f"Incomplete temporary files: {mon['incomplete_temporary_files']}"
    )


# ── Test 17 — Logs remain sanitized ──────────────────────────────────────────
def test_17_logs_sanitized():
    mon = _j("06_production_monitoring_summary.json")
    assert mon["sensitive_logging_findings"] == 0, (
        f"Sensitive logging findings: {mon['sensitive_logging_findings']}"
    )
    fb = _j("05_production_fallback_health.json")
    assert fb["checks"].get("error_logged_safely") is True, (
        "Fallback error was not logged safely"
    )
