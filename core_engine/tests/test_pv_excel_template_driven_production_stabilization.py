# -*- coding: utf-8 -*-
"""
Batch 9 — Production Stabilization tests.
20 tests verifying dependency lock, MuPDF warning classification,
observation window, integrity sampling, visual QA, and rollback drill.
Run with .venv/Scripts/python.exe -m pytest (no skips expected).
"""
from __future__ import annotations
import json, os, pathlib, re, sys
import pytest

PROJ      = pathlib.Path(__file__).resolve().parent.parent.parent
CE        = PROJ / "core_engine"
BASE      = CE / "instance" / "manual_review_outputs" / \
            "professional_valuation_template_driven_production_stabilization"
AUDITS    = BASE / "audits"
FINAL     = BASE / "final_report"
TEST_LOGS = BASE / "test_logs"
REQ_FILE  = CE / "requirements.txt"


def _j(name: str) -> dict:
    return json.loads((AUDITS / name).read_text(encoding="utf-8"))


def _fj(name: str) -> dict:
    return json.loads((FINAL / name).read_text(encoding="utf-8"))


# ── Test 01 — PyMuPDF is pinned or bounded in requirements.txt ───────────────
def test_01_pymupdf_declaration_pinned_or_bounded():
    req_text = REQ_FILE.read_text(encoding="utf-8")
    # Must not be completely unbounded (>=1.27.2 with no upper bound)
    # Accept: ==X.Y.Z.W  or  >=X,<Y  patterns
    pymupdf_lines = [l for l in req_text.splitlines() if l.startswith("PyMuPDF")]
    assert pymupdf_lines, "PyMuPDF not declared in requirements.txt"
    decl = pymupdf_lines[0]
    is_pinned  = "==" in decl
    is_bounded = ">=" in decl and "<" in decl
    assert is_pinned or is_bounded, (
        f"PyMuPDF declaration is neither pinned nor bounded: {decl!r}"
    )
    dep = _j("01_dependency_version_alignment.json")
    assert dep["overall"] == "PASS", f"Dependency alignment overall failed: {dep.get('checks')}"
    assert dep.get("strategy") in ("pinned", "bounded"), (
        f"Strategy must be pinned or bounded, got {dep.get('strategy')!r}"
    )


# ── Test 02 — Clean environment installs successfully ────────────────────────
def test_02_clean_environment_install_pass():
    dep = _j("01_dependency_version_alignment.json")
    assert dep["checks"].get("install") == "PASS", (
        f"Clean environment install failed: {dep['checks'].get('install')}"
    )
    assert dep["checks"].get("venv_created") == "PASS", "Clean venv creation failed"


# ── Test 03 — Required runtime packages import in clean env ──────────────────
def test_03_required_packages_import():
    dep = _j("01_dependency_version_alignment.json")
    for pkg in ("openpyxl", "PyMuPDF", "matplotlib", "win32com"):
        assert dep["checks"].get(f"import_{pkg}") == "PASS", (
            f"Package {pkg} failed to import in clean env: "
            f"{dep['checks'].get(f'import_{pkg}')}"
        )


# ── Test 04 — Excel COM 16.0 works ───────────────────────────────────────────
def test_04_excel_com_16_works():
    rh = _j("08_runtime_reproducibility.json")
    assert rh["checks"].get("excel_com_16") is True, (
        f"Excel COM 16.0 check failed: {rh.get('excel_com_version')!r}"
    )
    assert rh.get("excel_com_version") == "16.0", (
        f"Expected Excel 16.0, got {rh.get('excel_com_version')!r}"
    )


# ── Test 05 — Full MuPDF warning text is captured ────────────────────────────
def test_05_mupdf_warning_text_captured():
    cap = _j("02_mupdf_warning_full_capture.json")
    warning = cap.get("warning_text", "")
    assert "structure tree" in warning.lower() or "No common ancestor" in warning, (
        f"Expected full MuPDF warning text, got: {warning!r}"
    )
    # Warning must be documented (either live-captured or from prior evidence)
    assert cap.get("warning_observed") is True or "note" in cap, (
        "MuPDF warning not documented"
    )


# ── Test 06 — Warning classification exists and is non-blocking ──────────────
def test_06_warning_classification_exists():
    cls = _j("03_mupdf_warning_classification.json")
    valid = {"HARMLESS_LIBRARY_WARNING", "FONT_RENDERING_WARNING",
             "ANNOTATION_WARNING", "PDF_STRUCTURE_WARNING",
             "OUTPUT_INTEGRITY_WARNING", "UNKNOWN_REQUIRES_ACTION"}
    assert cls.get("classification") in valid, (
        f"Invalid classification: {cls.get('classification')!r}"
    )
    assert cls.get("blocking") is False, (
        f"Warning must be NON_BLOCKING for release; blocking={cls.get('blocking')}"
    )
    assert cls.get("severity") == "NON_BLOCKING", (
        f"Expected NON_BLOCKING, got {cls.get('severity')!r}"
    )
    # Evidence fields must all be True
    ev = cls.get("evidence", {})
    for key, val in ev.items():
        assert val is True, f"Evidence field {key!r} is not True: {val}"


# ── Test 07 — At least 50 requests documented in observation window ───────────
def test_07_observation_requests_50_plus():
    obs = _j("04_production_observation_metrics.json")
    n = obs.get("observation_requests", 0)
    assert n >= 50, f"Expected >= 50 observation requests, got {n}"
    assert obs.get("observation_days", 0) >= 1, "observation_days must be >= 1"


# ── Test 08 — Output success rate passes (no failed requests) ────────────────
def test_08_output_success_rate_pass():
    obs = _j("04_production_observation_metrics.json")
    assert obs.get("failed_requests", -1) == 0, (
        f"Failed requests: {obs.get('failed_requests')}"
    )
    rate = obs.get("output_success_rate_pct", 0)
    assert rate == 100.0, f"Output success rate must be 100%, got {rate}"
    assert obs["slo"].get("output_rate_100pct") is True


# ── Test 09 — Fallback thresholds pass ───────────────────────────────────────
def test_09_fallback_thresholds_pass():
    obs = _j("04_production_observation_metrics.json")
    fb  = obs.get("legacy_fallback_count", 0)
    n   = obs.get("observation_requests", 1)
    fb_pct = fb / n * 100 if n else 0
    assert fb_pct <= 5.0, f"Fallback rate {fb_pct:.1f}% exceeds critical threshold of 5%"
    assert obs["slo"].get("fallback_rate_below_2pct") is True, (
        f"Fallback rate exceeds warning threshold of 2%: {fb_pct:.1f}%"
    )


# ── Test 10 — Failed request count is zero ───────────────────────────────────
def test_10_failed_request_count_zero():
    obs = _j("04_production_observation_metrics.json")
    assert obs.get("failed_requests", -1) == 0, (
        f"Failed requests must be 0, got {obs.get('failed_requests')}"
    )
    assert obs["slo"].get("failed_rate_zero") is True


# ── Test 11 — No corrupted workbooks ─────────────────────────────────────────
def test_11_no_corrupted_workbooks():
    obs = _j("04_production_observation_metrics.json")
    assert obs.get("corrupted_workbooks", -1) == 0, (
        f"Corrupted workbooks: {obs.get('corrupted_workbooks')}"
    )
    assert obs["slo"].get("corrupted_zero") is True
    # Integrity samples pass
    integ = _j("06_production_output_integrity_samples.json")
    assert integ.get("fail_count", -1) == 0, (
        f"Integrity sample failures: {integ.get('fail_count')}"
    )


# ── Test 12 — No orphan Excel processes ──────────────────────────────────────
def test_12_no_orphan_excel_processes():
    obs = _j("04_production_observation_metrics.json")
    assert obs.get("orphan_excel_processes", -1) == 0, (
        f"Orphan Excel in monitoring: {obs.get('orphan_excel_processes')}"
    )
    vis = _j("07_production_visual_stability.json")
    assert vis.get("orphan_excel_after_visual", -1) == 0, (
        f"Orphan Excel after visual: {vis.get('orphan_excel_after_visual')}"
    )


# ── Test 13 — No incomplete temporary files ───────────────────────────────────
def test_13_no_incomplete_tmp_files():
    obs = _j("04_production_observation_metrics.json")
    assert obs.get("incomplete_temporary_files", -1) == 0, (
        f"Incomplete tmp files: {obs.get('incomplete_temporary_files')}"
    )
    assert obs["slo"].get("tmp_zero") is True


# ── Test 14 — Output integrity samples pass ──────────────────────────────────
def test_14_output_integrity_samples_pass():
    integ = _j("06_production_output_integrity_samples.json")
    total = integ.get("total_sampled", 0)
    assert total >= 10, f"Expected >= 10 integrity samples, got {total}"
    # Verify by category
    samples = integ.get("samples", [])
    cats = {s["category"] for s in samples}
    assert "complete_input"        in cats, "Missing complete_input samples"
    assert "incomplete_input"      in cats, "Missing incomplete_input samples"
    assert "certification_blocked" in cats, "Missing certification_blocked samples"
    # All samples must pass
    for s in samples:
        assert s.get("pass") is True, (
            f"Integrity check failed for {s.get('request_id')}: {s.get('checks')}"
        )


# ── Test 15 — Real visual samples pass ───────────────────────────────────────
def test_15_real_visual_samples_pass():
    vis = _j("07_production_visual_stability.json")
    assert vis.get("renderer_used") == "Excel COM", (
        f"Expected Excel COM, got {vis.get('renderer_used')!r}"
    )
    assert vis.get("total_pngs", 0) > 0, "No PNGs generated"
    wbs = vis.get("workbooks_rendered", [])
    assert len(wbs) >= 2, f"Expected >= 2 workbooks rendered, got {len(wbs)}"
    for wb in wbs:
        assert wb.get("fail_count", 1) == 0, (
            f"Visual failures in {wb.get('request_id')}: fail={wb.get('fail_count')}"
        )
    assert vis.get("critical_defects", -1) == 0, (
        f"Critical visual defects: {vis.get('critical_defects')}"
    )


# ── Test 16 — Logging remains sanitized ──────────────────────────────────────
def test_16_logging_sanitized():
    obs = _j("04_production_observation_metrics.json")
    assert obs.get("sensitive_logging_findings", -1) == 0, (
        f"Sensitive logging findings: {obs.get('sensitive_logging_findings')}"
    )
    # Verify _sanitize_log_reason function is present in pvo source
    pvo_src = (CE / "professional_valuation_outputs.py").read_text(encoding="utf-8")
    assert "_sanitize_log_reason" in pvo_src, \
        "_sanitize_log_reason function missing from pvo source"


# ── Test 17 — Runtime uses project .venv ─────────────────────────────────────
def test_17_runtime_uses_project_venv():
    rh = _j("08_runtime_reproducibility.json")
    assert rh.get("uses_project_venv") is True, (
        f"Runtime not using project .venv: prefix={rh.get('venv_prefix')!r}"
    )
    assert rh.get("python_version_match") is True, (
        f"Python version mismatch: {rh.get('python_version')!r}"
    )
    assert rh.get("interpreter_mismatch") is False, "Interpreter mismatch detected"
    assert rh.get("untracked_install_required") is False, \
        "Untracked packages required"
    assert rh.get("clean_env_recreatable") is True, \
        "Clean env not recreatable from manifest"


# ── Test 18 — Rollback drill passes ──────────────────────────────────────────
def test_18_rollback_drill_passes():
    rb = _j("09_rollback_drill.json")
    assert rb.get("rollback_status") == "PASS", (
        f"Rollback drill failed: {rb.get('checks')}"
    )
    assert rb["checks"].get("builder_is_legacy") is True, \
        "After rollback, builder was not 'legacy'"
    assert rb["checks"].get("legacy_output_ok") is True, \
        "Legacy output failed after rollback"
    assert rb["checks"].get("reactivation_uses_template") is True, \
        "After reactivation, builder was not 'template_driven'"
    assert rb["checks"].get("reactivation_ok") is True, \
        "Template output failed after reactivation"
    assert rb["checks"].get("global_default_disabled") is True, \
        "Global default env var was not disabled after drill"


# ── Test 19 — Source template hashes unchanged ───────────────────────────────
def test_19_source_templates_unchanged():
    summary = _fj("production_stabilization_summary.json")
    assert summary["criteria"].get("source_templates_unchanged") is True, \
        "Source templates were mutated during Batch 9"
    integ = _j("06_production_output_integrity_samples.json")
    assert integ.get("source_templates_unchanged") is True, \
        "Integrity audit reports source templates changed"


# ── Test 20 — Global feature-flag default remains disabled ───────────────────
def test_20_global_flag_default_disabled():
    # In the running test process, flag must not be set
    val = os.environ.get("PV_TEMPLATE_DRIVEN_EXCEL_ENABLED", "")
    assert val.lower() not in ("1", "true", "yes", "on"), (
        f"Flag is set globally in test process: {val!r}"
    )
    # Rollback audit must confirm global env not set
    rb = _j("09_rollback_drill.json")
    assert rb["checks"].get("global_default_disabled") is True, \
        "Global env was set (machine or user level)"
    # Summary must record decision
    summary = _fj("production_stabilization_summary.json")
    assert summary["decision"] in (
        "RELEASE_STABILIZED",
        "RELEASE_STABILIZED_WITH_CONDITIONS",
    ), f"Unexpected decision: {summary['decision']!r}"
