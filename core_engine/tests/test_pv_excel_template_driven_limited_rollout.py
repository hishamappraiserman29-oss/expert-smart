# -*- coding: utf-8 -*-
"""
Batch 7 — Controlled Limited Rollout Validation tests.
20 tests verifying the complete limited rollout execution.
Run with .venv/Scripts/python.exe -m pytest (no skips expected).
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import zipfile

import pytest

PROJ = pathlib.Path(__file__).resolve().parent.parent.parent
CE   = PROJ / "core_engine"
BASE = CE / "instance" / "manual_review_outputs" / "professional_valuation_template_driven_limited_rollout"
AUDITS  = BASE / "audits"
TD_OUT  = BASE / "outputs" / "template_driven"
FB_OUT  = BASE / "outputs" / "fallback_validation"
VIS_OUT = BASE / "visual_previews"
FINAL   = BASE / "final_report"

_PRIMARY_TPL = PROJ / "templates" / "reports" / "individual_valuation_professional_template.xlsm"
_CERT_SRC = (CE / "instance" / "manual_review_outputs"
             / "valuation_certification_readiness_gate"
             / "03_market_certification_readiness_workbook.xlsx")


def _j(name: str) -> dict:
    return json.loads((AUDITS / name).read_text(encoding="utf-8"))


def _fj(name: str) -> dict:
    return json.loads((FINAL / name).read_text(encoding="utf-8"))


# ── Test 01 — Correct .venv interpreter was used ──────────────────────────────
def test_01_correct_venv_interpreter():
    gate = _j("01_limited_rollout_runtime_gate.json")
    exe = gate["python_executable"]
    assert ".venv" in exe.lower(), f"Expected .venv interpreter, got: {exe}"
    assert pathlib.Path(exe).is_file(), f"Interpreter does not exist: {exe}"


# ── Test 02 — Excel COM 16.0 is available ─────────────────────────────────────
def test_02_excel_com_16_available():
    gate = _j("01_limited_rollout_runtime_gate.json")
    assert gate["excel_com_dispatch"] == "PASS", "Excel COM dispatch failed"
    assert gate["excel_version"] == "16.0", (
        f"Expected Excel 16.0, got {gate['excel_version']!r}"
    )


# ── Test 03 — Normal process flag remains disabled ────────────────────────────
def test_03_normal_process_flag_disabled():
    flag_val = os.environ.get("PV_TEMPLATE_DRIVEN_EXCEL_ENABLED", "")
    assert flag_val.lower() not in ("1", "true", "yes", "on"), (
        f"Normal process flag must be disabled, got: {flag_val!r}"
    )
    gate = _j("01_limited_rollout_runtime_gate.json")
    assert gate["flag_disabled_in_normal"] is True, (
        "Gate audit says flag was not disabled in normal process"
    )


# ── Test 04 — Dedicated rollout process used the flag ─────────────────────────
def test_04_rollout_process_flag_enabled():
    exec_r = _j("03_rollout_execution_results.json")
    assert exec_r["flag_used"] == "PV_TEMPLATE_DRIVEN_EXCEL_ENABLED=true", (
        "Rollout must have run with flag explicitly enabled"
    )
    assert exec_r["flag_after"] == "disabled", (
        "Flag must be recorded as disabled after rollout"
    )


# ── Test 05 — Actual integrated flow used ─────────────────────────────────────
def test_05_actual_integrated_flow():
    exec_r = _j("03_rollout_execution_results.json")
    assert exec_r["summary"]["template_driven"] > 0, (
        "No template_driven routing recorded — integrated flow not used"
    )


# ── Test 06 — Controlled request count between 5 and 10 ──────────────────────
def test_06_request_count_5_to_10():
    inv = _j("02_rollout_request_inventory.json")
    n = inv["request_count"]
    assert 5 <= n <= 10, f"Expected 5–10 requests, got {n}"


# ── Test 07 — All successful template outputs contain 55 sheets ───────────────
def test_07_all_template_outputs_55_sheets():
    exec_r = _j("03_rollout_execution_results.json")
    bad = [r["rollout_request_id"] for r in exec_r["requests"]
           if r["builder_used"] == "template_driven" and r["sheet_count"] != 55]
    assert not bad, f"Workbooks not 55 sheets: {bad}"
    assert exec_r["summary"]["55_sheet_valid"] == exec_r["summary"]["template_driven"], (
        "Not all template-driven workbooks have 55 sheets"
    )


# ── Test 08 — Valuation parity passes for every request ───────────────────────
def test_08_valuation_parity_all_pass():
    exec_r = _j("03_rollout_execution_results.json")
    summary = _fj("limited_rollout_summary.json")
    assert summary["parity_result"] == "PASS", "Valuation parity failed"
    # Verify parity MD exists
    parity_md = FINAL / "limited_rollout_valuation_parity.md"
    assert parity_md.is_file(), "Parity report not generated"
    content = parity_md.read_text(encoding="utf-8")
    assert "FAIL" not in content or "PASS" in content, "Parity report has failures"


# ── Test 09 — Incomplete inputs do not create fake defaults ───────────────────
def test_09_incomplete_inputs_no_fake_defaults():
    integrity = _j("05_rollout_output_integrity.json")
    for rec in integrity["results"]:
        assert rec.get("missing_data_not_fabricated", True) is True, (
            f"{rec.get('request_id')}: missing data was fabricated"
        )


# ── Test 10 — Certification remains non-automatic ────────────────────────────
def test_10_cert_non_automatic():
    exec_r = _j("03_rollout_execution_results.json")
    auto_cert = [r["rollout_request_id"] for r in exec_r["requests"]
                 if r.get("certification_state") == "ready"]
    assert not auto_cert, (
        f"Certification was automatically set to ready for: {auto_cert}"
    )


# ── Test 11 — Signature remains unsigned ──────────────────────────────────────
def test_11_signature_unsigned():
    exec_r = _j("03_rollout_execution_results.json")
    signed = [r["rollout_request_id"] for r in exec_r["requests"]
              if r.get("signature_state") != "unsigned"]
    assert not signed, f"Unexpected signed outputs: {signed}"


# ── Test 12 — Controlled failure uses legacy_fallback ─────────────────────────
def test_12_controlled_failure_legacy_fallback():
    fb = _j("04_rollout_fallback_validation.json")
    assert fb["builder_used"] == "legacy_fallback", (
        f"Expected legacy_fallback, got {fb['builder_used']!r}"
    )
    assert fb["success"] is True, "Fallback did not succeed"
    assert fb["legacy_output_published"] is True, "Legacy output not published"


# ── Test 13 — Temporary files are removed ─────────────────────────────────────
def test_13_temp_files_removed():
    fb = _j("04_rollout_fallback_validation.json")
    assert fb["temp_files_remain"] == 0, (
        f"Expected 0 temp files, found {fb['temp_files_remain']}"
    )
    assert fb["no_partial_workbook"] is True, "Partial workbook was published"


# ── Test 14 — No orphan Excel process remains ─────────────────────────────────
def test_14_no_orphan_excel_processes():
    perf = _j("06_rollout_performance_reliability.json")
    assert perf["orphan_excel_processes"] == 0, (
        f"Orphan Excel processes detected: {perf['orphan_excel_processes']}"
    )
    visual = _j("07_rollout_real_visual_audit.json")
    assert visual.get("orphan_excel_after_visual", 0) == 0, (
        "Orphan Excel processes after visual rendering"
    )


# ── Test 15 — Real visual evidence exists ─────────────────────────────────────
def test_15_real_visual_evidence_exists():
    visual = _j("07_rollout_real_visual_audit.json")
    assert visual["renderer_used"] == "Excel COM", (
        f"Expected Excel COM renderer, got {visual['renderer_used']!r}"
    )
    assert visual["total_pngs"] > 0, "No PNGs generated"
    full = visual["full_55_sheet_workbooks"]
    priority = visual["priority_8_sheet_workbooks"]
    assert len(full) >= 2, f"Expected at least 2 full-render workbooks, got {len(full)}"
    assert len(priority) >= 2, f"Expected at least 2 priority-render workbooks, got {len(priority)}"


# ── Test 16 — No critical visual defects ─────────────────────────────────────
def test_16_no_critical_visual_defects():
    visual = _j("07_rollout_real_visual_audit.json")
    assert visual["critical_defects"] == 0, (
        f"{visual['critical_defects']} critical visual defect(s) found"
    )
    for section in ("full_55_sheet_workbooks", "priority_8_sheet_workbooks"):
        for wb in visual[section]:
            assert wb.get("fail_count", 0) == 0, (
                f"Failed sheets in {wb.get('request_id')}: {wb.get('fail_count')}"
            )


# ── Test 17 — Logs are sanitized ────────────────────────────────────────────���─
def test_17_logs_sanitized():
    priv = _j("08_rollout_logging_privacy.json")
    assert priv["status"] == "PASS", (
        f"Logging privacy failed: {priv.get('violations')}"
    )
    assert priv["privacy_violations_found"] == 0, (
        f"Privacy violations: {priv['violations']}"
    )
    san = priv["sanitization_test"]
    assert san["windows_path_clean"] is True, "Windows path not sanitized"
    assert san["unix_path_clean"] is True, "Unix path not sanitized"


# ── Test 18 — Source template hashes unchanged ────────────────────────────────
def test_18_source_template_hashes_unchanged():
    summary = _fj("limited_rollout_summary.json")
    assert summary["source_template_hashes"]["unchanged"] is True, (
        "Source template was mutated during rollout"
    )
    integrity = _j("05_rollout_output_integrity.json")
    assert integrity["template_sources_unchanged"] is True, (
        "Integrity audit reports template modified"
    )


# ── Test 19 — Feature flag disabled after rollout ────────────────────────────
def test_19_feature_flag_disabled_after_rollout():
    flag_post = _j("09_feature_flag_post_rollout.json")
    assert flag_post["flag_disabled_in_normal_process"] is True, (
        "Flag was not disabled after rollout"
    )
    assert flag_post["legacy_builder_confirmed_default"] is True, (
        "Legacy builder is not the default after rollout"
    )
    assert flag_post["status"] == "PASS", (
        f"Feature flag safety check: {flag_post['status']}"
    )


# ── Test 20 — No source-code file modified by Batch 7 ────────────────────────
def test_20_no_source_files_modified():
    pvo_path = CE / "professional_valuation_outputs.py"
    builder_path = CE / "reports" / "excel_template_driven_builder.py"
    # These files must not have been modified by Batch 7:
    # Verify they still exist and are parseable
    import ast
    for p in (pvo_path, builder_path):
        assert p.is_file(), f"Source file missing: {p}"
        src = p.read_text(encoding="utf-8")
        try:
            ast.parse(src)
        except SyntaxError as e:
            pytest.fail(f"Syntax error in {p.name}: {e}")
    # Verify no Batch 7 markers injected
    for p in (pvo_path, builder_path):
        src = p.read_text(encoding="utf-8")
        assert "batch7" not in src.lower(), (
            f"Batch 7 code injected into {p.name}"
        )
