"""
test_pv_final_pdf_excel_review_pack.py
15 tests — مراجعة حزمة PDF + Excel النهائية
advisory_only=True | no_fake_cert=True | no_commit=True
"""
from __future__ import annotations
import json
from pathlib import Path

import openpyxl
import pytest

_CORE = Path(__file__).resolve().parent.parent
_SRC  = _CORE / "instance" / "manual_review_outputs" / \
        "professional_valuation_single_excel_15_master_plus_legacy_archive_three_pdfs"
_PDF_SRC = _SRC / "pdf_outputs"
_XL_SRC  = _SRC / "excel_outputs"

_REV  = _CORE / "instance" / "manual_review_outputs" / \
        "professional_valuation_final_pdf_excel_review_pack"
_SNAP = _REV / "source_files_snapshot"
_PREV = _REV / "pdf_review" / "previews"
_AUD  = _REV / "audits"
_VIS  = _REV / "visual_index"
_XREV = _REV / "excel_review"
_FRP  = _REV / "final_report"

_XL_NAME = "professional_valuation_admin_master_workbook.xlsm"
_MASTER_SHEETS = [
    "Cover", "Data Quality", "Property", "HBU Analysis", "Comparables",
    "Income Approach", "Cost Approach", "AVM Reference", "Scenarios",
    "Sensitivity Matrix", "Reconciliation", "Risk Register",
    "Standards Matrix", "Source Registry", "Admin Notes",
]


def _j(p: Path) -> dict:
    assert p.exists(), f"Audit missing: {p}"
    return json.loads(p.read_text(encoding="utf-8"))


# T01
def test_T01_review_pack_folder_exists():
    assert _REV.exists(), f"Review pack folder missing: {_REV}"


# T02
def test_T02_three_pdf_source_files_exist():
    for name in ["traditional_report.pdf", "detailed_report.pdf", "professional_report.pdf"]:
        p = _PDF_SRC / name
        assert p.exists(), f"Missing PDF source: {p}"
        assert p.stat().st_size > 10_000, f"PDF too small: {name}"


# T03
def test_T03_one_excel_source_file_exists():
    xl = _XL_SRC / _XL_NAME
    assert xl.exists(), f"Missing Excel: {xl}"
    assert xl.stat().st_size > 50_000, "Excel too small"
    xl_files = list(_XL_SRC.glob("*.xlsm")) + list(_XL_SRC.glob("*.xlsx"))
    assert len(xl_files) == 1, f"Expected 1 Excel, found {len(xl_files)}"


# T04
def test_T04_files_copied_to_source_snapshot():
    for name in ["traditional_report.pdf", "detailed_report.pdf", "professional_report.pdf",
                 _XL_NAME]:
        p = _SNAP / name
        assert p.exists(), f"Not copied to snapshot: {name}"


# T05
def test_T05_pdf_content_audit_exists_and_passes():
    data = _j(_AUD / "03_pdf_content_audit.json")
    assert data["pdf_content_status"] == "PASS", (
        f"PDF content audit failed: {data['pdf_content_status']}")


# T06
def test_T06_pdf_visual_previews_exist():
    for name in ["traditional_report_preview_index.html",
                 "detailed_report_preview_index.html",
                 "professional_report_preview_index.html",
                 "three_pdf_side_by_side_review.html"]:
        assert (_PREV / name).exists(), f"Preview missing: {name}"


# T07
def test_T07_pdf_distinctness_audit_exists_and_passes():
    data = _j(_AUD / "05_pdf_distinctness_audit.json")
    assert data["distinctness_status"] == "PASS"
    assert data["traditional_less_detailed_than_detailed"] is True
    assert data["detailed_less_detailed_than_professional"] is True
    assert data["professional_is_highest_depth"] is True


# T08
def test_T08_excel_structure_audit_exists_and_passes():
    data = _j(_AUD / "06_excel_structure_audit.json")
    assert data["excel_structure_status"] == "PASS"
    assert data["first_15_sheets_are_master_sheets"] is True
    assert data["legacy_archive_sheets_included_after_master_sheets"] is True
    assert data["total_sheet_count"] >= 17  # 15 master + at least 2 LEGACY archive sheets


# T09
def test_T09_excel_master_sheet_content_audit_passes():
    data = _j(_AUD / "07_excel_master_sheet_content_audit.json")
    assert data["excel_master_sheet_content_status"] == "PASS"


# T10
def test_T10_excel_legacy_archive_audit_passes():
    data = _j(_AUD / "08_excel_legacy_archive_audit.json")
    assert data["legacy_archive_status"] == "PASS"
    assert data["grand_final_legacy_sheets_included"] is True
    assert data["ultra_legacy_sheets_included"] is True
    assert data["legacy_source_files_modified"] is False


# T11
def test_T11_excel_visual_review_index_exists():
    assert (_XREV / "admin_master_workbook_review_index.html").exists()


# T12
def test_T12_final_open_review_index_exists():
    assert (_VIS / "OPEN_FINAL_PDF_EXCEL_REVIEW_INDEX.html").exists()


# T13
def test_T13_no_fake_certification():
    data = _j(_AUD / "03_pdf_content_audit.json")
    for report_key in ["traditional_report", "detailed_report", "professional_report"]:
        assert data[report_key]["contains_fake_certification"] is False, (
            f"Fake certification found in {report_key}")


# T14
def test_T14_no_internal_paths_in_audits():
    for fname in [
        "01_physical_files_audit.json",
        "03_pdf_content_audit.json",
        "06_excel_structure_audit.json",
        "07_excel_master_sheet_content_audit.json",
    ]:
        f = _AUD / fname
        if f.exists():
            content = f.read_text(encoding="utf-8")
            for pat in [r"C:\\Users", "C:/Users", "/home/"]:
                assert pat not in content, f"Internal path in {fname}: {pat}"


# T15
def test_T15_final_report_exists_and_status_not_failed_if_files_present():
    rep = _FRP / "final_pdf_excel_review_pack_report.txt"
    assert rep.exists(), "Final report missing"
    content = rep.read_text(encoding="utf-8")
    # If all required source files exist, status must not be FAILED
    pdfs_exist = all((_PDF_SRC / f).exists()
                     for f in ["traditional_report.pdf", "detailed_report.pdf",
                                "professional_report.pdf"])
    xl_exists  = (_XL_SRC / _XL_NAME).exists()
    if pdfs_exist and xl_exists:
        assert "OVERALL REVIEW STATUS: FAILED" not in content, (
            "Final report claims FAILED but all source files exist")
    assert "no_commit" in content
    assert "advisory_only" in content
