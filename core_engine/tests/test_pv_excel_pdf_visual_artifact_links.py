# -*- coding: utf-8 -*-
"""
12 tests verifying that Excel workbook and three PDF reports are present
as copied artifacts inside the visual QA folder, and that the visual QA
index contains correct relative links to them.
"""
import json
import pathlib
import re

import pytest
import openpyxl

_BASE = pathlib.Path(__file__).resolve().parent.parent
_QA   = _BASE / "instance" / "manual_review_outputs" / "professional_valuation_full_visual_qa"
_ART  = _QA / "artifacts"
_VI   = _QA / "visual_index" / "OPEN_EXCEL_AND_PDF_VISUAL_QA.html"
_MAN  = _QA / "final_report" / "visible_artifacts_manifest.json"

_EXCEL = _ART / "core_valuation_master_workbook_reference_parity.xlsx"
_TRAD  = _ART / "traditional_three_tier_report.pdf"
_DET   = _ART / "detailed_three_tier_report.pdf"
_PRO   = _ART / "professional_three_tier_report.pdf"


def test_01_visual_qa_index_exists():
    assert _VI.exists(), str(_VI)
    assert _VI.stat().st_size > 1000


def test_02_artifacts_folder_exists():
    assert _ART.exists() and _ART.is_dir(), str(_ART)


def test_03_excel_artifact_exists_nonempty():
    assert _EXCEL.exists(), str(_EXCEL)
    assert _EXCEL.stat().st_size > 0


def test_04_traditional_pdf_artifact_exists_nonempty():
    assert _TRAD.exists(), str(_TRAD)
    assert _TRAD.stat().st_size > 0


def test_05_detailed_pdf_artifact_exists_nonempty():
    assert _DET.exists(), str(_DET)
    assert _DET.stat().st_size > 0


def test_06_professional_pdf_artifact_exists_nonempty():
    assert _PRO.exists(), str(_PRO)
    assert _PRO.stat().st_size > 0


def test_07_index_has_excel_link():
    src = _VI.read_text(encoding="utf-8")
    assert "core_valuation_master_workbook_reference_parity.xlsx" in src


def test_08_index_has_all_pdf_links():
    src = _VI.read_text(encoding="utf-8")
    for name in ["traditional_three_tier_report.pdf",
                 "detailed_three_tier_report.pdf",
                 "professional_three_tier_report.pdf"]:
        assert name in src, f"missing link for {name}"


def test_09_index_uses_relative_links():
    src = _VI.read_text(encoding="utf-8")
    assert "../artifacts/" in src, "expected ../artifacts/ relative prefix"
    assert not re.search(r'href="[A-Za-z]:\\', src), "absolute path found in href"


def test_10_index_no_internal_absolute_paths():
    src = _VI.read_text(encoding="utf-8")
    hits = re.findall(r"[A-Za-z]:\\[^\s\"<>']{5,}", src)
    assert not hits, f"absolute paths found: {hits[:3]}"


def test_11_manifest_exists():
    assert _MAN.exists(), str(_MAN)
    assert _MAN.stat().st_size > 50


def test_12_manifest_overall_status_acceptable():
    data = json.loads(_MAN.read_text(encoding="utf-8"))
    status = data.get("overall_status", "")
    assert status in ("PASS", "PARTIAL"), f"unexpected status: {status!r}"
    if status == "PARTIAL":
        assert data.get("blockers"), "PARTIAL must list blockers"
