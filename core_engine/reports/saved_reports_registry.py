"""
saved_reports_registry.py — Saved Reports Registry (Phase 15).

Lightweight JSON-file registry that tracks generated report artifacts
(external PDF + internal Excel) with full metadata for each saved report.

Design principles
-----------------
- JSON-file based — no DB migration required.
- Default registry file: core_engine/outputsreports/saved_reports_registry.json
- All functions accept a ``registry_path`` override (used by tests via tmp_path).
- Aligns with Phase 13 (approval_rules) and Phase 14 (report_identity) constants.
- No valuation math, no engine changes, no API contract changes.

External vs. Internal separation
---------------------------------
  external_user  → external_pdf_path (PDF summary, client-deliverable)
  internal_admin → internal_excel_path (detailed xlsx, internal-only)
  excel_internal_only=True  → Excel artifact is NEVER exposed as a public download.

Usage
-----
    from reports.saved_reports_registry import (
        SavedReportRecord,
        create_saved_report_record,
        save_report_registry_entry,
        load_saved_report_registry,
        list_saved_reports,
        get_saved_report,
        classify_report_output,
        is_internal_excel_output,
        is_external_pdf_output,
    )
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# ── Constants re-used from Phase 13 / 14 (no re-definition of frozensets) ────

_VALID_APPROVAL_STATUSES: frozenset[str] = frozenset({
    "not_required", "pending_human_review", "approved", "rejected",
})

_VALID_REPORT_STATUSES: frozenset[str] = frozenset({
    "draft", "draft_pending_human_review", "final_ready", "issued", "archived",
})

_VALID_AUDIENCES: frozenset[str] = frozenset({"external_user", "internal_admin"})
_VALID_FORMATS:   frozenset[str] = frozenset({"pdf", "xlsx", "xlsm", "json", "docx"})

# ── Default registry path ─────────────────────────────────────────────────────

DEFAULT_REGISTRY_PATH: Path = (
    Path(__file__).resolve().parent.parent / "outputsreports" / "saved_reports_registry.json"
)


# ── SavedReportRecord dataclass ───────────────────────────────────────────────

@dataclass
class SavedReportRecord:
    """Metadata record for a single saved report artifact.

    Stored in the JSON registry; one record per generated artifact.
    Multiple records may share the same report_id (one for PDF, one for Excel).
    """
    report_id:                    str
    output_audience:              str            # "external_user" | "internal_admin"
    file_format:                  str            # "pdf" | "xlsx" | "xlsm" | "json"
    report_status:                str            # draft / draft_pending_human_review / final_ready / issued / archived
    generated_at:                 str            # ISO 8601
    appraiser_name:               str  = ""
    asset_type:                   str  = ""
    asset_family:                 str  = ""
    valuation_purpose:            str  = ""
    purpose_route:                str  = ""
    approval_status:              str  = "not_required"
    issued_at:                    str  = ""
    external_pdf_path:            str  = ""      # path or "" when not applicable
    internal_excel_path:          str  = ""      # path or "" when not applicable
    report_data_path:             str  = ""      # path to JSON metadata/data sidecar
    pdf_external_user_available:  bool = False
    excel_internal_admin_available: bool = False
    excel_internal_only:          bool = False   # True → never expose as public download
    source_log_available:         bool = False
    approval_log_available:       bool = False


# ── Factory ───────────────────────────────────────────────────────────────────

def create_saved_report_record(
    *,
    report_id:                    str | None = None,
    output_audience:              str,
    file_format:                  str,
    report_status:                str = "draft",
    generated_at:                 str,
    appraiser_name:               str  = "",
    asset_type:                   str  = "",
    asset_family:                 str  = "",
    valuation_purpose:            str  = "",
    purpose_route:                str  = "",
    approval_status:              str  = "not_required",
    issued_at:                    str  = "",
    external_pdf_path:            str  = "",
    internal_excel_path:          str  = "",
    report_data_path:             str  = "",
    source_log_available:         bool = False,
    approval_log_available:       bool = False,
) -> SavedReportRecord:
    """Create and validate a SavedReportRecord.

    Raises
    ------
    ValueError
        If output_audience, file_format, approval_status, or report_status
        is not a recognised value.
    """
    if output_audience not in _VALID_AUDIENCES:
        raise ValueError(
            f"Unknown output_audience {output_audience!r}. "
            f"Allowed: {sorted(_VALID_AUDIENCES)}"
        )
    if file_format not in _VALID_FORMATS:
        raise ValueError(
            f"Unknown file_format {file_format!r}. "
            f"Allowed: {sorted(_VALID_FORMATS)}"
        )
    if approval_status not in _VALID_APPROVAL_STATUSES:
        raise ValueError(
            f"Unknown approval_status {approval_status!r}. "
            f"Allowed: {sorted(_VALID_APPROVAL_STATUSES)}"
        )
    if report_status not in _VALID_REPORT_STATUSES:
        raise ValueError(
            f"Unknown report_status {report_status!r}. "
            f"Allowed: {sorted(_VALID_REPORT_STATUSES)}"
        )

    is_excel = file_format in {"xlsx", "xlsm"}
    excel_internal_only = is_excel and output_audience == "internal_admin"

    return SavedReportRecord(
        report_id=report_id or str(uuid.uuid4()),
        output_audience=output_audience,
        file_format=file_format,
        report_status=report_status,
        generated_at=generated_at,
        appraiser_name=appraiser_name,
        asset_type=asset_type,
        asset_family=asset_family,
        valuation_purpose=valuation_purpose,
        purpose_route=purpose_route,
        approval_status=approval_status,
        issued_at=issued_at,
        external_pdf_path=external_pdf_path if output_audience == "external_user" else "",
        internal_excel_path=internal_excel_path if is_excel and output_audience == "internal_admin" else "",
        report_data_path=report_data_path,
        pdf_external_user_available=bool(external_pdf_path) and output_audience == "external_user",
        excel_internal_admin_available=bool(internal_excel_path) and output_audience == "internal_admin",
        excel_internal_only=excel_internal_only,
        source_log_available=source_log_available,
        approval_log_available=approval_log_available,
    )


# ── Registry persistence ──────────────────────────────────────────────────────

def save_report_registry_entry(
    record: SavedReportRecord,
    *,
    registry_path: Path | str = DEFAULT_REGISTRY_PATH,
) -> None:
    """Append or update a SavedReportRecord in the JSON registry file.

    If a record with the same ``report_id`` and ``file_format`` already
    exists it is replaced; otherwise the new record is appended.
    The parent directory is created if it does not exist.

    Args:
        record:        The record to persist.
        registry_path: Path to the JSON registry file.
    """
    path = Path(registry_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    existing = _read_raw(path)
    key = (record.report_id, record.file_format)
    updated = [
        r for r in existing
        if (r.get("report_id"), r.get("file_format")) != key
    ]
    updated.append(asdict(record))
    path.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")


def load_saved_report_registry(
    registry_path: Path | str = DEFAULT_REGISTRY_PATH,
) -> list[SavedReportRecord]:
    """Load all records from the JSON registry file.

    Returns an empty list when the file does not exist.
    """
    path = Path(registry_path)
    return [SavedReportRecord(**r) for r in _read_raw(path)]


def list_saved_reports(
    *,
    registry_path:   Path | str = DEFAULT_REGISTRY_PATH,
    output_audience: str | None = None,
    asset_type:      str | None = None,
    valuation_purpose: str | None = None,
    report_status:   str | None = None,
    approval_status: str | None = None,
    limit:           int = 100,
    offset:          int = 0,
) -> list[SavedReportRecord]:
    """Return a filtered, paginated list of saved report records.

    All filter args are optional; omit to return all records.
    """
    records = load_saved_report_registry(registry_path)
    if output_audience is not None:
        records = [r for r in records if r.output_audience == output_audience]
    if asset_type is not None:
        records = [r for r in records if r.asset_type == asset_type]
    if valuation_purpose is not None:
        records = [r for r in records if r.valuation_purpose == valuation_purpose]
    if report_status is not None:
        records = [r for r in records if r.report_status == report_status]
    if approval_status is not None:
        records = [r for r in records if r.approval_status == approval_status]
    return records[offset: offset + limit]


def get_saved_report(
    report_id: str,
    *,
    registry_path: Path | str = DEFAULT_REGISTRY_PATH,
    file_format:   str | None = None,
) -> SavedReportRecord | None:
    """Retrieve a single record by report_id (and optionally file_format).

    Returns None if not found.
    """
    records = load_saved_report_registry(registry_path)
    matches = [r for r in records if r.report_id == report_id]
    if file_format is not None:
        matches = [r for r in matches if r.file_format == file_format]
    return matches[0] if matches else None


# ── Classification helpers ────────────────────────────────────────────────────

def classify_report_output(file_path_or_type: str) -> str:
    """Return the file format category for a path or extension string.

    Returns one of: "pdf" | "xlsx" | "xlsm" | "json" | "docx" | "unknown".
    """
    s = str(file_path_or_type).lower().strip()
    if s.endswith(".pdf")  or s == "pdf":  return "pdf"
    if s.endswith(".xlsx") or s == "xlsx": return "xlsx"
    if s.endswith(".xlsm") or s == "xlsm": return "xlsm"
    if s.endswith(".json") or s == "json": return "json"
    if s.endswith(".docx") or s == "docx": return "docx"
    return "unknown"


def is_internal_excel_output(record: SavedReportRecord) -> bool:
    """Return True when the record represents an internal-only Excel artifact."""
    return record.excel_internal_only


def is_external_pdf_output(record: SavedReportRecord) -> bool:
    """Return True when the record is an external-user PDF artifact."""
    return record.output_audience == "external_user" and record.file_format == "pdf"


# ── Internal helpers ──────────────────────────────────────────────────────────

def _read_raw(path: Path) -> list[dict[str, Any]]:
    """Read the JSON registry file; return empty list if absent or malformed."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []
