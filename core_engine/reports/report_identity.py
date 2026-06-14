"""
Report Identity & Output Audience — Phase 14.

Central constants for visible report branding and output audience separation.

Branding is VISUAL/DISPLAY ONLY:
  - No module renames, no path renames, no repository renames.
  - These strings appear only in rendered PDF/Excel output.

Output audiences:
  external_user  — PDF summary only (no Excel exposed)
  internal_admin — PDF + detailed Excel workbook (stored internally)
"""
from __future__ import annotations

from dataclasses import dataclass

# ── Visible branding (display in reports only) ────────────────────────────────

FIRM_NAME:       str = "ALHADY FOR REAL PROPERTY"
APPRAISER_NAME:  str = "خبير التقييم هشام المهدي"
APPRAISER_TEL:   str = "01222230128"
APPRAISER_EMAIL: str = "APPRAISERMAN29@GMAIL.COM"

# ── Output audience constants ─────────────────────────────────────────────────

OUTPUT_AUDIENCES: frozenset[str] = frozenset({"external_user", "internal_admin"})
FILE_FORMATS:     frozenset[str] = frozenset({"pdf", "xlsx", "xlsm"})

_DEFAULT_AUDIENCE: str = "external_user"


# ── Report output metadata dataclass ─────────────────────────────────────────

@dataclass
class ReportOutputMetadata:
    """Metadata describing a single report output artifact.

    approval_status and source_log_available link to Phase 13 approval_rules
    constants — no re-definition here.
    """
    report_id:            str
    report_type:          str            # "valuation" | "composite" | "portfolio"
    output_audience:      str            # "external_user" | "internal_admin"
    file_format:          str            # "pdf" | "xlsx" | "xlsm"
    generated_at:         str            # ISO 8601 string
    appraiser_name:       str  = APPRAISER_NAME
    valuation_purpose:    str  = ""
    asset_type:           str  = ""
    asset_family:         str  = ""
    approval_status:      str  = "not_required"   # Phase 13 APPROVAL_STATUSES
    source_log_available: bool = False
    excel_internal_only:  bool = False             # True when xlsx targeted at internal_admin


# ── Factory ───────────────────────────────────────────────────────────────────

def build_report_metadata(
    *,
    report_id:            str,
    report_type:          str,
    output_audience:      str,
    file_format:          str,
    generated_at:         str,
    appraiser_name:       str  = APPRAISER_NAME,
    valuation_purpose:    str  = "",
    asset_type:           str  = "",
    asset_family:         str  = "",
    approval_status:      str  = "not_required",
    source_log_available: bool = False,
) -> ReportOutputMetadata:
    """Validated factory for ReportOutputMetadata.

    Raises
    ------
    ValueError
        If output_audience or file_format is not a recognised value.
    """
    if output_audience not in OUTPUT_AUDIENCES:
        raise ValueError(
            f"Unknown output_audience {output_audience!r}. "
            f"Allowed: {sorted(OUTPUT_AUDIENCES)}"
        )
    if file_format not in FILE_FORMATS:
        raise ValueError(
            f"Unknown file_format {file_format!r}. "
            f"Allowed: {sorted(FILE_FORMATS)}"
        )
    excel_internal_only = (
        file_format in {"xlsx", "xlsm"} and output_audience == "internal_admin"
    )
    return ReportOutputMetadata(
        report_id=report_id,
        report_type=report_type,
        output_audience=output_audience,
        file_format=file_format,
        generated_at=generated_at,
        appraiser_name=appraiser_name,
        valuation_purpose=valuation_purpose,
        asset_type=asset_type,
        asset_family=asset_family,
        approval_status=approval_status,
        source_log_available=source_log_available,
        excel_internal_only=excel_internal_only,
    )


# ── Audience helpers ──────────────────────────────────────────────────────────

def is_excel_allowed_for_audience(audience: str) -> bool:
    """Return True only for internal_admin — external_user receives PDF only."""
    return audience == "internal_admin"


def normalize_audience(audience: str | None) -> str:
    """Return a valid audience key; unknown/None defaults to 'external_user'."""
    if audience in OUTPUT_AUDIENCES:
        return str(audience)
    return _DEFAULT_AUDIENCE
