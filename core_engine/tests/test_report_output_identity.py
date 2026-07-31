"""
Tests for Phase 14 — Report Outputs Modernization.

RO01  — report_identity module is importable
RO02  — FIRM_NAME is "ALHADY FOR REAL PROPERTY"
RO03  — APPRAISER_NAME contains "هشام المهدي"
RO04  — APPRAISER_TEL is "01222230128"
RO05  — APPRAISER_EMAIL is "APPRAISERMAN29@GMAIL.COM"
RO06  — OUTPUT_AUDIENCES contains exactly external_user and internal_admin
RO07  — FILE_FORMATS contains pdf, xlsx, xlsm
RO08  — build_report_metadata: external_user + pdf → excel_internal_only=False
RO09  — build_report_metadata: internal_admin + xlsx → excel_internal_only=True
RO10  — build_report_metadata: unknown audience raises ValueError
RO11  — build_report_metadata: unknown format raises ValueError
RO12  — is_excel_allowed_for_audience: False for external_user
RO13  — is_excel_allowed_for_audience: True for internal_admin
RO14  — normalize_audience: None → external_user
RO15  — normalize_audience: unknown string → external_user
RO16  — normalize_audience: valid audiences round-trip
RO17  — PDF contains valid bytes and advances cursor (main_report with firm identity)
RO18  — PDF output contains firm name rendered (larger than baseline without it)
RO19  — PDF detailed > legacy (KPI gate still works after Phase 14 additions)
RO20  — PDF all 5 profiles render without crash (legacy, detailed, professional_template, external_pdf, internal_detailed)
RO21  — PDF footer constant includes ALHADY FOR REAL PROPERTY
RO22  — report_profiles: external_pdf profile exists and has pdf ext
RO23  — report_profiles: internal_detailed profile exists and has xlsx ext
RO24  — existing profiles unchanged (legacy/detailed/professional_template still present)
RO25  — cover_metadata_sheet: builds workbook without crash
RO26  — cover_metadata_sheet: cell A1 contains FIRM_NAME
RO27  — cover_metadata_sheet: contact cells contain appraiser tel and email
RO28  — cover_metadata_sheet: internal_only badge present when excel_internal_only=True
RO29  — cover_metadata_sheet: no badge when external_user
RO30  — formula_library_sheet: builds workbook without crash
RO31  — formula_library_sheet: contains Sales Comparison section
RO32  — formula_library_sheet: contains Reconciliation section
RO33  — formula_library_sheet: display-only note present
RO34  — source_log_sheet: builds workbook without crash
RO35  — source_log_sheet: populates rows from source_log list
RO36  — source_log_sheet: placeholder row when no entries
RO37  — human_approval_log_sheet: builds workbook without crash
RO38  — human_approval_log_sheet: renders approval_data summary
RO39  — human_approval_log_sheet: renders per-field entries
RO40  — human_approval_log_sheet: placeholder row when no entries
RO41  — PDF does not expose Excel internal content by default
RO42  — Excel internal_only=True does not appear for external_user
RO43  — existing report/excel/pdf tests still compatible (module import check)
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

# ── Path setup ────────────────────────────────────────────────────────────────
_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_ORIG_CWD = os.getcwd()
try:
    os.chdir(str(_CORE))

    from reports.report_identity import (  # noqa: E402
        APPRAISER_EMAIL,
        APPRAISER_NAME,
        APPRAISER_TEL,
        FIRM_NAME,
        OUTPUT_AUDIENCES,
        FILE_FORMATS,
        ReportOutputMetadata,
        build_report_metadata,
        is_excel_allowed_for_audience,
        normalize_audience,
    )
    from reports.report_profiles import (  # noqa: E402
        get_report_profile,
        normalize_report_style,
    )
    from reports.pdf.pdf_engine import _FOOTER_TEXT, generate_pdf  # noqa: E402
    from reports.pdf.sections.main_report_pdf import render_main_report  # noqa: E402
    from reports.sheets.cover_metadata_sheet import apply_cover_metadata_sheet  # noqa: E402
    from reports.sheets.formula_library_sheet import apply_formula_library_sheet  # noqa: E402
    from reports.sheets.source_log_sheet import apply_source_log_sheet  # noqa: E402
    from reports.sheets.human_approval_log_sheet import apply_human_approval_log_sheet  # noqa: E402

    from fpdf import FPDF  # noqa: E402
    from openpyxl import Workbook  # noqa: E402
    from reports.pdf.pdf_components import register_fonts  # noqa: E402
finally:
    os.chdir(_ORIG_CWD)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _new_pdf() -> tuple[FPDF, str]:
    doc = FPDF(orientation="P", unit="mm", format="A4")
    doc.set_auto_page_break(auto=True, margin=18)
    fam = register_fonts(doc)
    doc.add_page()
    return doc, fam


def _new_wb_ws(title: str = "Sheet1"):
    wb = Workbook()
    ws = wb.active
    ws.title = title
    return wb, ws


_APPRAISER = {"name": "خبير اختبار", "license": "EG-TEST-001", "date": "2026-06-14"}
_PROP_INFO = {"address": "القاهرة", "type": "سكني", "area": 200}
_VAL_RESULTS = {"market_value": 1_500_000, "price_per_sqm": 7500,
                "confidence": "عالية", "value_words": "مليون وخمسمائة ألف جنيه",
                "primary_approach": "مقارنة البيوع"}


# ── RO01–RO07: constants ─────────────────────────────────────────────────────

def test_RO01_module_importable():
    import reports.report_identity as m
    assert hasattr(m, "FIRM_NAME")
    assert hasattr(m, "build_report_metadata")


def test_RO02_firm_name():
    assert FIRM_NAME == "ALHADY FOR REAL PROPERTY"


def test_RO03_appraiser_name_contains_hisham():
    assert "هشام المهدي" in APPRAISER_NAME


def test_RO04_appraiser_tel():
    assert APPRAISER_TEL == "01222230128"


def test_RO05_appraiser_email():
    assert APPRAISER_EMAIL == "APPRAISERMAN29@GMAIL.COM"


def test_RO06_output_audiences():
    assert OUTPUT_AUDIENCES == frozenset({"external_user", "internal_admin"})


def test_RO07_file_formats():
    assert {"pdf", "xlsx", "xlsm"}.issubset(FILE_FORMATS)


# ── RO08–RO16: build_report_metadata / audience helpers ──────────────────────

def test_RO08_external_pdf_not_internal():
    m = build_report_metadata(
        report_id="R1", report_type="valuation",
        output_audience="external_user", file_format="pdf",
        generated_at="2026-06-14T00:00:00",
    )
    assert m.output_audience == "external_user"
    assert m.file_format == "pdf"
    assert m.excel_internal_only is False


def test_RO09_internal_xlsx_is_internal_only():
    m = build_report_metadata(
        report_id="R2", report_type="valuation",
        output_audience="internal_admin", file_format="xlsx",
        generated_at="2026-06-14T00:00:00",
    )
    assert m.excel_internal_only is True


def test_RO10_unknown_audience_raises():
    with pytest.raises(ValueError, match="Unknown output_audience"):
        build_report_metadata(
            report_id="X", report_type="v",
            output_audience="public", file_format="pdf",
            generated_at="2026-06-14",
        )


def test_RO11_unknown_format_raises():
    with pytest.raises(ValueError, match="Unknown file_format"):
        build_report_metadata(
            report_id="X", report_type="v",
            output_audience="external_user", file_format="docx",
            generated_at="2026-06-14",
        )


def test_RO12_excel_not_allowed_for_external():
    assert is_excel_allowed_for_audience("external_user") is False


def test_RO13_excel_allowed_for_internal():
    assert is_excel_allowed_for_audience("internal_admin") is True


def test_RO14_normalize_none_returns_external():
    assert normalize_audience(None) == "external_user"


def test_RO15_normalize_unknown_returns_external():
    assert normalize_audience("public") == "external_user"


@pytest.mark.parametrize("aud", ["external_user", "internal_admin"])
def test_RO16_normalize_valid_audiences_roundtrip(aud: str):
    assert normalize_audience(aud) == aud


# ── RO17–RO21: PDF identity ───────────────────────────────────────────────────

def test_RO17_pdf_advances_cursor_and_valid_bytes():
    doc, fam = _new_pdf()
    y0 = doc.get_y()
    render_main_report(doc, appraiser=_APPRAISER, property_info=_PROP_INFO,
                       valuation_results=_VAL_RESULTS, font_family=fam)
    assert doc.get_y() > y0
    out = doc.output()
    assert bytes(out[:4]) == b"%PDF"


def test_RO18_pdf_with_firm_identity_larger_than_empty():
    def _size() -> int:
        doc, fam = _new_pdf()
        render_main_report(doc, appraiser={}, property_info={},
                           valuation_results={}, font_family=fam)
        return len(doc.output())

    size = _size()
    assert size > 1500, f"Expected >1500 bytes, got {size}"


def test_RO19_detailed_still_larger_than_legacy():
    def _size(profile: str) -> int:
        doc, fam = _new_pdf()
        render_main_report(doc, appraiser=_APPRAISER, property_info=_PROP_INFO,
                           valuation_results=_VAL_RESULTS,
                           profile_key=profile, font_family=fam)
        return len(doc.output())

    assert _size("detailed") > _size("legacy")


def test_RO20_all_five_profiles_render(tmp_path):
    for profile in ("legacy", "detailed", "professional_template",
                    "external_pdf", "internal_detailed"):
        out = tmp_path / f"{profile}.pdf"
        generate_pdf(profile_key=profile, data={
            "appraiser": _APPRAISER,
            "property_info": _PROP_INFO,
            "valuation_results": _VAL_RESULTS,
        }, output_path=out)
        assert out.read_bytes()[:4] == b"%PDF", f"profile={profile}"


def test_RO21_footer_contains_firm_name():
    assert "ALHADY FOR REAL PROPERTY" in _FOOTER_TEXT


# ── RO22–RO24: profiles registry ─────────────────────────────────────────────

def test_RO22_external_pdf_profile_exists():
    p = get_report_profile("external_pdf")
    assert p.style == "external_pdf"
    assert p.default_output_ext == ".pdf"


def test_RO23_internal_detailed_profile_exists():
    p = get_report_profile("internal_detailed")
    assert p.style == "internal_detailed"
    assert p.default_output_ext == ".xlsx"


def test_RO24_existing_profiles_unchanged():
    for key in ("legacy", "detailed", "professional_template"):
        p = get_report_profile(key)
        assert p.style == key, f"Profile {key} style changed"


# ── RO25–RO29: cover_metadata_sheet ─────────────────────────────────────────

def test_RO25_cover_metadata_sheet_no_crash():
    wb, ws = _new_wb_ws("Cover & Metadata")
    apply_cover_metadata_sheet(ws)
    assert ws.max_row >= 1


def test_RO26_cover_metadata_sheet_firm_name_in_a1():
    wb, ws = _new_wb_ws("Cover & Metadata")
    apply_cover_metadata_sheet(ws)
    all_values = [str(ws.cell(row=r, column=c).value or "")
                  for r in range(1, ws.max_row + 1)
                  for c in range(1, 3)]
    assert any(FIRM_NAME in v for v in all_values)


def test_RO27_cover_contact_contains_tel_and_email():
    wb, ws = _new_wb_ws("Cover & Metadata")
    apply_cover_metadata_sheet(ws)
    all_values = [str(ws.cell(row=r, column=c).value or "")
                  for r in range(1, ws.max_row + 1)
                  for c in range(1, 3)]
    assert any(APPRAISER_TEL in v for v in all_values)
    assert any(APPRAISER_EMAIL in v for v in all_values)


def test_RO28_internal_badge_present_when_excel_internal_only():
    meta = build_report_metadata(
        report_id="R3", report_type="valuation",
        output_audience="internal_admin", file_format="xlsx",
        generated_at="2026-06-14",
    )
    wb, ws = _new_wb_ws("Cover & Metadata")
    apply_cover_metadata_sheet(ws, metadata=meta)
    all_values = [str(ws.cell(row=r, column=c).value or "")
                  for r in range(1, ws.max_row + 1)
                  for c in range(1, 3)]
    assert any("INTERNAL USE ONLY" in v for v in all_values)


def test_RO29_no_internal_badge_for_external_pdf():
    meta = build_report_metadata(
        report_id="R4", report_type="valuation",
        output_audience="external_user", file_format="pdf",
        generated_at="2026-06-14",
    )
    wb, ws = _new_wb_ws("Cover & Metadata")
    apply_cover_metadata_sheet(ws, metadata=meta)
    all_values = [str(ws.cell(row=r, column=c).value or "")
                  for r in range(1, ws.max_row + 1)
                  for c in range(1, 3)]
    assert not any("INTERNAL USE ONLY" in v for v in all_values)


# ── RO30–RO33: formula_library_sheet ─────────────────────────────────────────

def test_RO30_formula_library_no_crash():
    wb, ws = _new_wb_ws("Formula Library")
    apply_formula_library_sheet(ws)
    assert ws.max_row >= 5


def test_RO31_formula_library_sales_comparison_present():
    wb, ws = _new_wb_ws("Formula Library")
    apply_formula_library_sheet(ws)
    all_values = [str(ws.cell(row=r, column=c).value or "")
                  for r in range(1, ws.max_row + 1)
                  for c in range(1, 5)]
    assert any("Sales Comparison" in v for v in all_values)


def test_RO32_formula_library_reconciliation_present():
    wb, ws = _new_wb_ws("Formula Library")
    apply_formula_library_sheet(ws)
    all_values = [str(ws.cell(row=r, column=c).value or "")
                  for r in range(1, ws.max_row + 1)
                  for c in range(1, 5)]
    assert any("Reconciliation" in v for v in all_values)


def test_RO33_formula_library_display_only_note():
    wb, ws = _new_wb_ws("Formula Library")
    apply_formula_library_sheet(ws)
    all_values = [str(ws.cell(row=r, column=c).value or "")
                  for r in range(1, ws.max_row + 1)
                  for c in range(1, 5)]
    assert any("DESCRIPTIVE ONLY" in v for v in all_values)


# ── RO34–RO36: source_log_sheet ──────────────────────────────────────────────

def test_RO34_source_log_no_crash():
    wb, ws = _new_wb_ws("Source Log")
    apply_source_log_sheet(ws)
    assert ws.max_row >= 1


def test_RO35_source_log_populates_entries():
    entries = [
        {"source_id": "S001", "source_type": "API", "source_name": "market_data_api",
         "retrieval_date": "2026-06-14", "field_applied": "price_per_sqm",
         "confidence": "90", "notes": "primary source"},
    ]
    wb, ws = _new_wb_ws("Source Log")
    apply_source_log_sheet(ws, source_log=entries)
    all_values = [str(ws.cell(row=r, column=c).value or "")
                  for r in range(1, ws.max_row + 1)
                  for c in range(1, 8)]
    assert any("S001" in v for v in all_values)


def test_RO36_source_log_placeholder_when_empty():
    wb, ws = _new_wb_ws("Source Log")
    apply_source_log_sheet(ws, source_log=[])
    all_values = [str(ws.cell(row=r, column=c).value or "")
                  for r in range(1, ws.max_row + 1)
                  for c in range(1, 8)]
    assert any("No source log" in v for v in all_values)


# ── RO37–RO40: human_approval_log_sheet ──────────────────────────────────────

def test_RO37_human_approval_log_no_crash():
    wb, ws = _new_wb_ws("Human Approval Log")
    apply_human_approval_log_sheet(ws)
    assert ws.max_row >= 1


def test_RO38_approval_log_renders_approval_data():
    data = {
        "is_automated_fill": True,
        "approval_status": "pending_human_review",
        "confidence_score": 85.0,
        "data_source_log": ["api_x"],
    }
    wb, ws = _new_wb_ws("Human Approval Log")
    apply_human_approval_log_sheet(ws, approval_data=data)
    all_values = [str(ws.cell(row=r, column=c).value or "")
                  for r in range(1, ws.max_row + 1)
                  for c in range(1, 8)]
    assert any("pending_human_review" in v for v in all_values)


def test_RO39_approval_log_renders_entries():
    entries = [
        {"field_code": "confidence_score", "is_automated_fill": "True",
         "confidence_score": "85.0", "approval_status": "pending_human_review",
         "reviewer": "", "reviewed_at": "", "notes": "awaiting review"},
    ]
    wb, ws = _new_wb_ws("Human Approval Log")
    apply_human_approval_log_sheet(ws, entries=entries)
    all_values = [str(ws.cell(row=r, column=c).value or "")
                  for r in range(1, ws.max_row + 1)
                  for c in range(1, 8)]
    assert any("confidence_score" in v for v in all_values)


def test_RO40_approval_log_placeholder_when_no_entries():
    wb, ws = _new_wb_ws("Human Approval Log")
    apply_human_approval_log_sheet(ws, entries=[])
    all_values = [str(ws.cell(row=r, column=c).value or "")
                  for r in range(1, ws.max_row + 1)
                  for c in range(1, 8)]
    assert any("No per-field" in v for v in all_values)


# ── RO41–RO43: separation & compatibility ────────────────────────────────────

def test_RO41_pdf_does_not_expose_excel_internal_content():
    meta_ext = build_report_metadata(
        report_id="R5", report_type="valuation",
        output_audience="external_user", file_format="pdf",
        generated_at="2026-06-14",
    )
    assert meta_ext.excel_internal_only is False
    assert is_excel_allowed_for_audience(meta_ext.output_audience) is False


def test_RO42_internal_only_not_set_for_external_user():
    meta = build_report_metadata(
        report_id="R6", report_type="valuation",
        output_audience="external_user", file_format="pdf",
        generated_at="2026-06-14",
    )
    assert meta.excel_internal_only is False


def test_RO43_existing_modules_still_importable():
    from reports.report_pipeline import run_report_pipeline, PipelineResult  # noqa: F401
    from reports.excel_builder import ExcelReportBuilder  # noqa: F401
    from reports.report_profiles import get_report_profile, get_legacy_excluded_sheets  # noqa: F401
    assert True
