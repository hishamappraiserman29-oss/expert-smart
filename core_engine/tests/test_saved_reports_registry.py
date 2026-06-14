"""
Tests for Phase 15 — Saved Reports Registry.

SR01  — module is importable
SR02  — SavedReportRecord is a dataclass with required fields
SR03  — create_saved_report_record: generates report_id when not supplied
SR04  — create_saved_report_record: uses supplied report_id
SR05  — create_saved_report_record: external_user + pdf → external_pdf_path stored, excel_internal_only=False
SR06  — create_saved_report_record: internal_admin + xlsx → excel_internal_only=True
SR07  — create_saved_report_record: internal_admin + xlsx → internal_excel_path stored
SR08  — create_saved_report_record: external_user pdf → pdf_external_user_available=True
SR09  — create_saved_report_record: internal_admin xlsx → excel_internal_admin_available=True
SR10  — create_saved_report_record: external_user xlsx → excel_internal_only=False (not internal)
SR11  — create_saved_report_record: approval_status stored
SR12  — create_saved_report_record: generated_at stored
SR13  — create_saved_report_record: appraiser_name stored
SR14  — create_saved_report_record: asset_type stored
SR15  — create_saved_report_record: valuation_purpose stored
SR16  — create_saved_report_record: unknown audience raises ValueError
SR17  — create_saved_report_record: unknown format raises ValueError
SR18  — create_saved_report_record: unknown approval_status raises ValueError
SR19  — create_saved_report_record: unknown report_status raises ValueError
SR20  — save_report_registry_entry: persists record to JSON file
SR21  — load_saved_report_registry: returns empty list when file absent
SR22  — load_saved_report_registry: round-trips saved records correctly
SR23  — list_saved_reports: returns all records when no filters
SR24  — list_saved_reports: filters by output_audience
SR25  — list_saved_reports: filters by asset_type
SR26  — list_saved_reports: filters by report_status
SR27  — list_saved_reports: pagination (limit/offset)
SR28  — get_saved_report: returns record by report_id
SR29  — get_saved_report: returns None for unknown report_id
SR30  — get_saved_report: filters by file_format
SR31  — save_report_registry_entry: updating existing record replaces it (no duplicate)
SR32  — classify_report_output: .pdf → "pdf"
SR33  — classify_report_output: .xlsx → "xlsx"
SR34  — classify_report_output: unknown → "unknown"
SR35  — is_internal_excel_output: True for internal_admin xlsx
SR36  — is_internal_excel_output: False for external_user pdf
SR37  — is_external_pdf_output: True for external_user pdf
SR38  — is_external_pdf_output: False for internal_admin xlsx
SR39  — internal Excel path not set when audience is external_user
SR40  — external PDF path not set when audience is internal_admin
SR41  — source_log_available stored and retrievable
SR42  — approval_log_available stored and retrievable
SR43  — registry creates parent directory if absent
SR44  — existing report/excel/pdf tests still compatible (import check)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

# ── Path setup ────────────────────────────────────────────────────────────────
_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(str(_CORE))

from reports.saved_reports_registry import (  # noqa: E402
    SavedReportRecord,
    classify_report_output,
    create_saved_report_record,
    get_saved_report,
    is_external_pdf_output,
    is_internal_excel_output,
    list_saved_reports,
    load_saved_report_registry,
    save_report_registry_entry,
)


# ── Common fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def reg_path(tmp_path) -> Path:
    return tmp_path / "registry.json"


def _pdf_record(**kwargs) -> SavedReportRecord:
    defaults = dict(
        output_audience="external_user",
        file_format="pdf",
        generated_at="2026-06-15T10:00:00",
        report_status="final_ready",
        appraiser_name="خبير التقييم هشام المهدي",
        asset_type="residential",
        valuation_purpose="market_value",
        external_pdf_path="/reports/R001.pdf",
    )
    defaults.update(kwargs)
    return create_saved_report_record(**defaults)


def _excel_record(**kwargs) -> SavedReportRecord:
    defaults = dict(
        output_audience="internal_admin",
        file_format="xlsx",
        generated_at="2026-06-15T10:00:00",
        report_status="draft",
        appraiser_name="خبير التقييم هشام المهدي",
        asset_type="commercial",
        valuation_purpose="mortgage_lending",
        internal_excel_path="/reports/R001_internal.xlsx",
    )
    defaults.update(kwargs)
    return create_saved_report_record(**defaults)


# ── SR01–SR02: import & dataclass ────────────────────────────────────────────

def test_SR01_module_importable():
    import reports.saved_reports_registry as m
    assert hasattr(m, "SavedReportRecord")
    assert hasattr(m, "create_saved_report_record")
    assert hasattr(m, "save_report_registry_entry")
    assert hasattr(m, "load_saved_report_registry")
    assert hasattr(m, "list_saved_reports")
    assert hasattr(m, "get_saved_report")


def test_SR02_dataclass_has_required_fields():
    fields = {f.name for f in SavedReportRecord.__dataclass_fields__.values()}
    required = {
        "report_id", "output_audience", "file_format", "report_status",
        "generated_at", "appraiser_name", "asset_type", "asset_family",
        "valuation_purpose", "purpose_route", "approval_status", "issued_at",
        "external_pdf_path", "internal_excel_path", "report_data_path",
        "pdf_external_user_available", "excel_internal_admin_available",
        "excel_internal_only", "source_log_available", "approval_log_available",
    }
    assert required.issubset(fields)


# ── SR03–SR15: create_saved_report_record ────────────────────────────────────

def test_SR03_generates_report_id_when_not_supplied():
    r = _pdf_record()
    assert r.report_id and len(r.report_id) > 8


def test_SR04_uses_supplied_report_id():
    r = _pdf_record(report_id="CUSTOM-001")
    assert r.report_id == "CUSTOM-001"


def test_SR05_external_user_pdf_sets_external_path_not_internal():
    r = _pdf_record(report_id="R-PDF-01", external_pdf_path="/out/r.pdf")
    assert r.external_pdf_path == "/out/r.pdf"
    assert r.internal_excel_path == ""
    assert r.excel_internal_only is False


def test_SR06_internal_admin_xlsx_sets_excel_internal_only():
    r = _excel_record()
    assert r.excel_internal_only is True


def test_SR07_internal_admin_xlsx_sets_internal_excel_path():
    r = _excel_record(internal_excel_path="/vault/r.xlsx")
    assert r.internal_excel_path == "/vault/r.xlsx"


def test_SR08_external_pdf_user_available_true():
    r = _pdf_record(external_pdf_path="/out/r.pdf")
    assert r.pdf_external_user_available is True


def test_SR09_internal_admin_excel_available_true():
    r = _excel_record(internal_excel_path="/vault/r.xlsx")
    assert r.excel_internal_admin_available is True


def test_SR10_external_user_xlsx_not_internal_only():
    r = create_saved_report_record(
        output_audience="external_user", file_format="xlsx",
        generated_at="2026-06-15", report_status="draft",
    )
    assert r.excel_internal_only is False


def test_SR11_approval_status_stored():
    r = _pdf_record(approval_status="pending_human_review")
    assert r.approval_status == "pending_human_review"


def test_SR12_generated_at_stored():
    r = _pdf_record(generated_at="2026-06-15T12:00:00")
    assert r.generated_at == "2026-06-15T12:00:00"


def test_SR13_appraiser_name_stored():
    r = _pdf_record(appraiser_name="هشام المهدي")
    assert r.appraiser_name == "هشام المهدي"


def test_SR14_asset_type_stored():
    r = _pdf_record(asset_type="hotel")
    assert r.asset_type == "hotel"


def test_SR15_valuation_purpose_stored():
    r = _pdf_record(valuation_purpose="mortgage_lending")
    assert r.valuation_purpose == "mortgage_lending"


# ── SR16–SR19: validation ─────────────────────────────────────────────────────

def test_SR16_unknown_audience_raises():
    with pytest.raises(ValueError, match="Unknown output_audience"):
        create_saved_report_record(
            output_audience="public", file_format="pdf",
            generated_at="2026-06-15", report_status="draft",
        )


def test_SR17_unknown_format_raises():
    with pytest.raises(ValueError, match="Unknown file_format"):
        create_saved_report_record(
            output_audience="external_user", file_format="rtf",
            generated_at="2026-06-15", report_status="draft",
        )


def test_SR18_unknown_approval_status_raises():
    with pytest.raises(ValueError, match="Unknown approval_status"):
        create_saved_report_record(
            output_audience="external_user", file_format="pdf",
            generated_at="2026-06-15", report_status="draft",
            approval_status="auto_approved",
        )


def test_SR19_unknown_report_status_raises():
    with pytest.raises(ValueError, match="Unknown report_status"):
        create_saved_report_record(
            output_audience="external_user", file_format="pdf",
            generated_at="2026-06-15", report_status="in_progress",
        )


# ── SR20–SR22: save / load ────────────────────────────────────────────────────

def test_SR20_save_persists_to_json(reg_path):
    r = _pdf_record(report_id="R-SAVE-01")
    save_report_registry_entry(r, registry_path=reg_path)
    assert reg_path.exists()
    data = json.loads(reg_path.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["report_id"] == "R-SAVE-01"


def test_SR21_load_returns_empty_when_no_file(reg_path):
    assert load_saved_report_registry(reg_path) == []


def test_SR22_load_roundtrips_correctly(reg_path):
    r = _excel_record(report_id="R-LOAD-01")
    save_report_registry_entry(r, registry_path=reg_path)
    loaded = load_saved_report_registry(reg_path)
    assert len(loaded) == 1
    assert loaded[0].report_id == "R-LOAD-01"
    assert loaded[0].excel_internal_only is True
    assert loaded[0].output_audience == "internal_admin"


# ── SR23–SR27: list_saved_reports ────────────────────────────────────────────

def test_SR23_list_returns_all_records(reg_path):
    for i in range(3):
        save_report_registry_entry(
            _pdf_record(report_id=f"R-LIST-{i:02d}"),
            registry_path=reg_path,
        )
    assert len(list_saved_reports(registry_path=reg_path)) == 3


def test_SR24_list_filters_by_output_audience(reg_path):
    save_report_registry_entry(_pdf_record(report_id="R-EXT"), registry_path=reg_path)
    save_report_registry_entry(_excel_record(report_id="R-INT"), registry_path=reg_path)
    ext = list_saved_reports(registry_path=reg_path, output_audience="external_user")
    inn = list_saved_reports(registry_path=reg_path, output_audience="internal_admin")
    assert len(ext) == 1 and ext[0].report_id == "R-EXT"
    assert len(inn) == 1 and inn[0].report_id == "R-INT"


def test_SR25_list_filters_by_asset_type(reg_path):
    save_report_registry_entry(_pdf_record(report_id="R-RES", asset_type="residential"), registry_path=reg_path)
    save_report_registry_entry(_pdf_record(report_id="R-COM", asset_type="commercial"), registry_path=reg_path)
    res = list_saved_reports(registry_path=reg_path, asset_type="residential")
    assert len(res) == 1 and res[0].report_id == "R-RES"


def test_SR26_list_filters_by_report_status(reg_path):
    save_report_registry_entry(_pdf_record(report_id="R-FINAL", report_status="final_ready"), registry_path=reg_path)
    save_report_registry_entry(_excel_record(report_id="R-DRAFT", report_status="draft"), registry_path=reg_path)
    finals = list_saved_reports(registry_path=reg_path, report_status="final_ready")
    assert len(finals) == 1 and finals[0].report_id == "R-FINAL"


def test_SR27_list_pagination(reg_path):
    for i in range(5):
        save_report_registry_entry(
            _pdf_record(report_id=f"R-PAG-{i:02d}"),
            registry_path=reg_path,
        )
    page1 = list_saved_reports(registry_path=reg_path, limit=2, offset=0)
    page2 = list_saved_reports(registry_path=reg_path, limit=2, offset=2)
    assert len(page1) == 2
    assert len(page2) == 2
    assert {r.report_id for r in page1}.isdisjoint({r.report_id for r in page2})


# ── SR28–SR30: get_saved_report ──────────────────────────────────────────────

def test_SR28_get_by_report_id(reg_path):
    save_report_registry_entry(_pdf_record(report_id="R-GET-01"), registry_path=reg_path)
    r = get_saved_report("R-GET-01", registry_path=reg_path)
    assert r is not None
    assert r.report_id == "R-GET-01"


def test_SR29_get_returns_none_for_unknown(reg_path):
    assert get_saved_report("UNKNOWN-XYZ", registry_path=reg_path) is None


def test_SR30_get_filters_by_file_format(reg_path):
    save_report_registry_entry(_pdf_record(report_id="R-FMT-01", file_format="pdf"), registry_path=reg_path)
    save_report_registry_entry(_excel_record(report_id="R-FMT-01"), registry_path=reg_path)
    pdf_r  = get_saved_report("R-FMT-01", registry_path=reg_path, file_format="pdf")
    xlsx_r = get_saved_report("R-FMT-01", registry_path=reg_path, file_format="xlsx")
    assert pdf_r  is not None and pdf_r.file_format  == "pdf"
    assert xlsx_r is not None and xlsx_r.file_format == "xlsx"


# ── SR31: upsert ─────────────────────────────────────────────────────────────

def test_SR31_update_replaces_existing_record(reg_path):
    r1 = _pdf_record(report_id="R-UPD-01", report_status="draft")
    save_report_registry_entry(r1, registry_path=reg_path)
    r2 = _pdf_record(report_id="R-UPD-01", report_status="final_ready")
    save_report_registry_entry(r2, registry_path=reg_path)
    records = load_saved_report_registry(reg_path)
    assert len(records) == 1
    assert records[0].report_status == "final_ready"


# ── SR32–SR34: classify_report_output ────────────────────────────────────────

@pytest.mark.parametrize("path,expected", [
    ("/reports/r.pdf",  "pdf"),
    ("/reports/r.xlsx", "xlsx"),
    ("/reports/r.xlsm", "xlsm"),
    ("/reports/r.json", "json"),
    ("/reports/r.docx", "docx"),
    ("pdf",             "pdf"),
    ("xlsx",            "xlsx"),
    ("/reports/r.txt",  "unknown"),
])
def test_SR32_to_SR34_classify_report_output(path: str, expected: str):
    assert classify_report_output(path) == expected


# ── SR35–SR38: classification helpers ────────────────────────────────────────

def test_SR35_is_internal_excel_true_for_internal_xlsx():
    r = _excel_record()
    assert is_internal_excel_output(r) is True


def test_SR36_is_internal_excel_false_for_external_pdf():
    r = _pdf_record()
    assert is_internal_excel_output(r) is False


def test_SR37_is_external_pdf_true_for_external_pdf():
    r = _pdf_record()
    assert is_external_pdf_output(r) is True


def test_SR38_is_external_pdf_false_for_internal_xlsx():
    r = _excel_record()
    assert is_external_pdf_output(r) is False


# ── SR39–SR40: path isolation ─────────────────────────────────────────────────

def test_SR39_internal_excel_path_empty_for_external_user():
    r = create_saved_report_record(
        output_audience="external_user", file_format="xlsx",
        generated_at="2026-06-15", report_status="draft",
        internal_excel_path="/vault/r.xlsx",  # should be ignored
    )
    assert r.internal_excel_path == ""


def test_SR40_external_pdf_path_empty_for_internal_admin():
    r = create_saved_report_record(
        output_audience="internal_admin", file_format="pdf",
        generated_at="2026-06-15", report_status="draft",
        external_pdf_path="/out/r.pdf",  # should be ignored
    )
    assert r.external_pdf_path == ""


# ── SR41–SR42: source/approval log flags ─────────────────────────────────────

def test_SR41_source_log_available_stored(reg_path):
    r = _pdf_record(report_id="R-SRC-01", source_log_available=True)
    save_report_registry_entry(r, registry_path=reg_path)
    loaded = get_saved_report("R-SRC-01", registry_path=reg_path)
    assert loaded is not None and loaded.source_log_available is True


def test_SR42_approval_log_available_stored(reg_path):
    r = _excel_record(report_id="R-APL-01", approval_log_available=True)
    save_report_registry_entry(r, registry_path=reg_path)
    loaded = get_saved_report("R-APL-01", registry_path=reg_path)
    assert loaded is not None and loaded.approval_log_available is True


# ── SR43: directory creation ──────────────────────────────────────────────────

def test_SR43_creates_parent_directory(tmp_path):
    deep = tmp_path / "a" / "b" / "c" / "registry.json"
    r = _pdf_record(report_id="R-DIR-01")
    save_report_registry_entry(r, registry_path=deep)
    assert deep.exists()


# ── SR44: existing modules still importable ───────────────────────────────────

def test_SR44_existing_modules_still_importable():
    from reports.report_pipeline import run_report_pipeline, PipelineResult  # noqa: F401
    from reports.report_identity import build_report_metadata  # noqa: F401
    from reports.report_profiles import get_report_profile  # noqa: F401
    from reports.excel_builder import ExcelReportBuilder  # noqa: F401
    assert True


# ── SR45: default registry path is core_engine/outputsreports/ ───────────────

def test_SR45_default_registry_path_is_outputsreports():
    """
    Asserts the registry lands in core_engine/outputsreports/ — the project's
    existing convention for concatenated output-category folder names
    (same pattern as outputscalculations/, outputslogs/).
    Not a typo; the directory already exists in the repo.
    """
    from reports.saved_reports_registry import DEFAULT_REGISTRY_PATH
    path = DEFAULT_REGISTRY_PATH
    assert path.parent.name == "outputsreports", (
        f"Expected parent 'outputsreports', got {path.parent.name!r}"
    )
    assert path.name == "saved_reports_registry.json"
    assert path.parent.parent.name == "core_engine"
