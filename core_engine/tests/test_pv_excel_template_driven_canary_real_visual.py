# -*- coding: utf-8 -*-
"""
Batch 6R — Canary Real Excel COM Visual Smoke tests.
10 tests verifying the Excel COM rendering of the Batch 6 canary workbook.
All renderer tests must pass; no skips accepted.
"""
from __future__ import annotations
import json
import os
import pathlib
import sys

import pytest

PROJ = pathlib.Path(__file__).resolve().parent.parent.parent
BASE = PROJ / "core_engine/instance/manual_review_outputs/professional_valuation_template_driven_canary_real_visual"
AUDITS = BASE / "audits"
PNG_DIR = BASE / "visual_previews"

CANARY_WB = (
    PROJ
    / "core_engine/instance/manual_review_outputs"
    / "professional_valuation_template_driven_canary"
    / "outputs/template_driven_canary_workbook.xlsx"
)

PRIORITY_SHEETS = [
    "الافتراضات والمدخلات",
    "لوحة القيادة التنفيذية",
    "القيمة بالحروف",
    "بيان الامتثال",
    "توقيع واعتماد الخبير",
    "حالة الاعتماد والتوصية",
    "نطاق الثقة وعدم اليقين",
    "التوصية النهائية",
]


def _j(name: str) -> dict:
    return json.loads((AUDITS / name).read_text(encoding="utf-8"))


# ── Test 01 — Selected Python executable is recorded ─────────────────────────
def test_01_selected_python_recorded():
    env = _j("01_runtime_environment_comparison.json")
    selected = env["selected_executable"]
    assert selected, "selected_executable must be recorded"
    assert pathlib.Path(selected).is_file(), (
        f"Selected Python does not exist: {selected}"
    )


# ── Test 02 — win32com imports in selected executable ─────────────────────────
def test_02_win32com_in_selected_executable():
    env = _j("01_runtime_environment_comparison.json")
    project_env = next(
        e for e in env["environments"] if e["label"] == "project_venv"
    )
    assert project_env["win32com_import"] == "PASS", (
        f"win32com import failed in selected runtime: {project_env.get('win32com_location')}"
    )


# ── Test 03 — Excel COM 16.0 starts successfully ──────────────────────────────
def test_03_excel_com_16_dispatched():
    env = _j("01_runtime_environment_comparison.json")
    project_env = next(
        e for e in env["environments"] if e["label"] == "project_venv"
    )
    assert project_env["excel_com_dispatch"] == "PASS", "Excel COM dispatch failed"
    assert project_env["excel_version"] == "16.0", (
        f"Expected Excel 16.0, got {project_env['excel_version']!r}"
    )


# ── Test 04 — Actual canary workbook was used ─────────────────────────────────
def test_04_actual_canary_workbook_used():
    smoke = _j("03_real_canary_visual_smoke.json")
    wb_path = pathlib.Path(smoke["canary_workbook"])
    assert wb_path == CANARY_WB.resolve() or wb_path == CANARY_WB, (
        f"Wrong workbook used: {wb_path}"
    )
    assert CANARY_WB.is_file(), "Canary workbook file does not exist"


# ── Test 05 — All 8 priority sheets rendered through Excel COM ────────────────
def test_05_all_8_priority_sheets_rendered():
    smoke = _j("03_real_canary_visual_smoke.json")
    assert smoke["renderer_used"] == "Excel COM", (
        f"Expected 'Excel COM', got {smoke['renderer_used']!r}"
    )
    assert smoke["priority_sheets_exported"] == 8, (
        f"Expected 8 sheets exported, got {smoke['priority_sheets_exported']}"
    )
    failed = [s["sheet"] for s in smoke["sheets"] if s["status"] == "FAILED"]
    assert not failed, f"Sheets failed to render: {failed}"


# ── Test 06 — At least 8 real PNG files exist ─────────────────────────────────
def test_06_at_least_8_real_pngs():
    pngs = list(PNG_DIR.glob("*.png"))
    assert len(pngs) >= 8, (
        f"Expected at least 8 PNGs, found {len(pngs)}"
    )


# ── Test 07 — No fallback renderer was used ───────────────────────────────────
def test_07_no_fallback_renderer():
    smoke = _j("03_real_canary_visual_smoke.json")
    assert smoke["renderer_used"] == "Excel COM", "Fallback renderer was used"
    assert smoke.get("renderer_fallback") is None or smoke["renderer_fallback"] is None, (
        "A fallback renderer was recorded"
    )
    smoke_str = json.dumps(smoke)
    assert "matplotlib" not in smoke_str.lower(), "matplotlib fallback referenced in audit"
    assert "openpyxl preview" not in smoke_str.lower(), "openpyxl preview referenced"


# ── Test 08 — No critical visual defect exists ────────────────────────────────
def test_08_no_critical_visual_defects():
    defects = _j("04_real_canary_visual_defects.json")
    assert defects["critical_defects"] == 0, (
        f"{defects['critical_defects']} critical visual defect(s): "
        f"{[d['sheet'] for d in defects['defects'] if d['severity'] == 'CRITICAL']}"
    )


# ── Test 09 — Workbook hash is unchanged ──────────────────────────────────────
def test_09_workbook_hash_unchanged():
    smoke = _j("03_real_canary_visual_smoke.json")
    assert smoke["workbook_unchanged"] is True, (
        f"Canary workbook was mutated: "
        f"{smoke['workbook_hash_before'][:16]} → {smoke['workbook_hash_after'][:16]}"
    )


# ── Test 10 — Feature flag remains disabled after test ───────────────────────
def test_10_feature_flag_disabled():
    flag_val = os.environ.get("PV_TEMPLATE_DRIVEN_EXCEL_ENABLED", "")
    assert flag_val.lower() not in ("1", "true", "yes", "on"), (
        f"Feature flag must remain disabled after test, got: {flag_val!r}"
    )
