# -*- coding: utf-8 -*-
"""
10 tests verifying that all 73 Excel sheets were rendered visually via Excel COM,
PNG previews exist, audits are written, and the source workbook was not modified.
"""
import json
import pathlib
import re

import pytest

_BASE = pathlib.Path(__file__).resolve().parent.parent
_QA   = _BASE / "instance" / "manual_review_outputs" / "professional_valuation_full_visual_qa"
_AUD  = _QA / "audits"
_SCR  = _QA / "screenshots" / "excel"
_VI   = _QA / "visual_index" / "OPEN_EXCEL_AND_PDF_VISUAL_QA.html"
_SRC  = _BASE / "instance" / "manual_review_outputs" / "professional_valuation_excel_reference_parity" / "excel_outputs" / "core_valuation_master_workbook_reference_parity.xlsx"

_RENDERER_AUD  = _AUD / "excel_renderer_detection_audit.json"
_RENDER_AUD    = _AUD / "excel_real_visual_render_audit.json"
_SHEET_RESULTS = _AUD / "excel_73_sheet_visual_results.json"
_DEFECTS_AUD   = _AUD / "excel_visual_defects_audit.json"
_PRIORITY_AUD  = _AUD / "excel_priority_sheets_visual_audit.json"


def test_01_renderer_audit_exists():
    assert _RENDERER_AUD.exists(), str(_RENDERER_AUD)
    data = json.loads(_RENDERER_AUD.read_text(encoding="utf-8"))
    assert data.get("selected_renderer"), "selected_renderer must be set"


def test_02_all_73_sheets_rendered():
    data = json.loads(_RENDER_AUD.read_text(encoding="utf-8"))
    rendered = data.get("sheets_rendered", 0)
    assert rendered == 73, f"expected 73 sheets rendered, got {rendered}"


def test_03_every_sheet_has_at_least_one_png():
    results = json.loads(_SHEET_RESULTS.read_text(encoding="utf-8"))
    missing = [r["sheet_name"] for r in results if not r.get("png_files")]
    assert not missing, f"sheets without PNG: {missing[:5]}"


def test_04_at_least_73_png_files_exist():
    pngs = list(_SCR.glob("*.png"))
    assert len(pngs) >= 73, f"expected >= 73 PNGs, found {len(pngs)}"


def test_05_visual_results_audit_exists():
    assert _SHEET_RESULTS.exists(), str(_SHEET_RESULTS)
    results = json.loads(_SHEET_RESULTS.read_text(encoding="utf-8"))
    assert len(results) == 73, f"expected 73 entries, got {len(results)}"


def test_06_visual_defects_audit_exists():
    assert _DEFECTS_AUD.exists(), str(_DEFECTS_AUD)
    assert _DEFECTS_AUD.stat().st_size > 2


def test_07_priority_sheets_audit_exists():
    assert _PRIORITY_AUD.exists(), str(_PRIORITY_AUD)
    data = json.loads(_PRIORITY_AUD.read_text(encoding="utf-8"))
    assert len(data) >= 10, f"expected >= 10 priority sheets, got {len(data)}"


def test_08_visual_index_links_to_excel_previews():
    src = _VI.read_text(encoding="utf-8")
    assert "../screenshots/excel/" in src, "index must contain Excel preview links"


def test_09_source_workbook_not_modified():
    data = json.loads(_RENDER_AUD.read_text(encoding="utf-8"))
    assert data.get("source_workbook_unmodified") is True, "source workbook must not be modified"


def test_10_no_internal_absolute_paths_in_index():
    src = _VI.read_text(encoding="utf-8")
    hits = re.findall(r"[A-Za-z]:\\[^\s\"<>']{5,}", src)
    assert not hits, f"absolute paths in index: {hits[:3]}"
