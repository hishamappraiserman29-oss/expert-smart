"""
report_pipeline.py — Bridge between the bridge_api flat dict and the three
report engines (validation / pdf / db).

Public surface:
    PipelineResult        — frozen dataclass, one per pipeline call
    validate_report_data  — bridge_api integration point (validation only, BA.2)
    persist_report_data   — bridge_api integration point (persistence only, BA.3)
    fetch_reports         — bridge_api integration point (history list, BA.4a)
    fetch_report          — bridge_api integration point (history single, BA.4a)
    run_report_pipeline   — full orchestrator; every step is opt-in
    _build_engine_dto     — maps bridge_api full-dict → nested engine DTO

All steps are additive and independent: skipping one does not affect others.
"""
from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from reports.db import DEFAULT_DB_PATH
from reports.db import count_reports as _db_count
from reports.db import get_report as _db_get
from reports.db import list_reports as _db_list
from reports.db import save_report as _db_save
from reports.pdf import generate_pdf as _pdf_generate
from reports.validation import validate_report as _val_report


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PipelineResult:
    """Immutable outcome of a single run_report_pipeline call.

    Fields:
        is_valid          True when no validation ERRORs (or validate=False).
        errors            Tuple of ValidationIssue objects with severity ERROR.
        warnings          Tuple of ValidationIssue objects with severity WARNING.
        report_db_id      report_id returned by save_report; None if persist=False.
        pdf_path          Path to generated PDF; None if generate_pdf=False.
        validation_result Raw ValidationResult object; None if validate=False.
    """
    is_valid:          bool
    errors:            tuple
    warnings:          tuple
    report_db_id:      str | None = None
    pdf_path:          Path | None = None
    validation_result: object | None = None


# ── DTO mapper ────────────────────────────────────────────────────────────────

def _build_engine_dto(full: dict[str, Any]) -> dict[str, Any]:
    """Map a bridge_api ``full`` flat dict to the nested DTO the engines expect.

    The mapper is lenient: missing keys yield empty strings / None / empty dicts
    so validation can report what is absent rather than crashing here.
    """
    _area = full.get("area")
    area: float | None = float(_area) if _area is not None else None

    _mv = full.get("market_value")
    market_value: float | None = float(_mv) if _mv is not None else None

    _ppm = full.get("price_per_meter") or full.get("price_per_sqm")
    price_per_sqm: float | None = float(_ppm) if _ppm else None

    return {
        "appraiser": {
            "name":    full.get("expert", ""),
            "title":   full.get("appraiser_title", ""),
            "firm":    full.get("appraiser_firm", ""),
            "license": full.get("appraiser_license", full.get("license", "")),
            "date":    full.get("valuation_date", full.get("report_date", "")),
        },
        "property_info": {
            "address": full.get("location", ""),
            "type":    full.get("property_type", ""),
            "area":    area,
        },
        "valuation_results": {
            "market_value":     market_value,
            "price_per_sqm":    price_per_sqm,
            "confidence":       full.get("confidence", ""),
            "value_words":      full.get("value_words", ""),
            "primary_approach": full.get("primary_approach", ""),
        },
        "subject": {
            "address": full.get("location", ""),
            "area":    area,
            "type":    full.get("property_type", ""),
        },
        # comp_sales from advanced_valuation kw; fall back to comparables key
        "comparables":    full.get("comp_sales") or full.get("comparables") or [],
        "cost_approach":  full.get("cost_approach") or {},
        "income_approach": full.get("income_approach") or {},
        "reconciliation": full.get("reconciliation") or {},
    }


# ── Pipeline orchestrator ─────────────────────────────────────────────────────

def run_report_pipeline(
    full: dict[str, Any],
    *,
    profile_key: str = "legacy",
    validate: bool = False,
    generate_pdf: bool = False,
    pdf_output_path: Path | str | None = None,
    persist: bool = False,
    db_path: Path | str = DEFAULT_DB_PATH,
    status: str = "draft",
) -> PipelineResult:
    """Run the report pipeline for a single valuation result.

    Args:
        full:            The ``full`` dict assembled in ``handle_valuation``.
        profile_key:     Report profile ("legacy" / "detailed" / "professional_template").
        validate:        Run the validation engine; result in PipelineResult.errors.
        generate_pdf:    Render a PDF to ``pdf_output_path``.
        pdf_output_path: Where to write the PDF (required when generate_pdf=True).
        persist:         Save the DTO to the SQLite report database.
        db_path:         Override the default DB path (useful in tests).
        status:          Initial status for the saved record ("draft" / "final").

    Returns:
        PipelineResult — is_valid=True when validate=False or no ERRORs found.
    """
    dto = _build_engine_dto(full)

    # ── Step 1: Validation (opt-in) ───────────────────────────────────────────
    validation_result = None
    is_valid = True
    errors: tuple = ()
    warnings: tuple = ()

    if validate:
        validation_result = _val_report(dto, profile_key=profile_key)
        is_valid = validation_result.is_valid
        errors   = tuple(validation_result.errors)
        warnings = tuple(validation_result.warnings)

    # ── Step 2: PDF generation (opt-in) ──────────────────────────────────────
    pdf_path: Path | None = None
    if generate_pdf and pdf_output_path is not None:
        pdf_path = _pdf_generate(
            profile_key=profile_key,
            data=dto,
            output_path=Path(pdf_output_path),
        )

    # ── Step 3: Persistence (opt-in) ─────────────────────────────────────────
    report_db_id: str | None = None
    if persist:
        report_db_id = _db_save(
            dto,
            profile_key=profile_key,
            status=status,
            report_id=full.get("report_id"),
            db_path=db_path,
        )

    return PipelineResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        report_db_id=report_db_id,
        pdf_path=pdf_path,
        validation_result=validation_result,
    )


# ── bridge_api integration point ─────────────────────────────────────────────

def validate_report_data(
    full: dict[str, Any],
    *,
    profile_key: str = "legacy",
) -> PipelineResult:
    """Validation-only facade used by the bridge_api validation gate (Wave BA.2).

    Thin wrapper over run_report_pipeline with validate=True and all other
    steps (generate_pdf, persist) off. Future waves extend this module without
    changing this public symbol — bridge_api imports only this name.

    Args:
        full:        The ``full`` dict assembled in ``handle_valuation``.
        profile_key: Report profile ("legacy"/"detailed"/"professional_template").

    Returns:
        PipelineResult with is_valid, errors, warnings populated.
        is_valid=False means ERRORs were found; generation should be blocked.
    """
    return run_report_pipeline(full, profile_key=profile_key, validate=True)


def persist_report_data(
    full: dict[str, Any],
    *,
    profile_key: str = "legacy",
    status: str = "draft",
    db_path: "Path | str" = DEFAULT_DB_PATH,
) -> str:
    """Bridge API integration point — persistence only (Wave BA.3).

    Thin wrapper over run_report_pipeline with persist=True and all other
    steps (validate, generate_pdf) off. Future waves extend this module
    without changing this public symbol.

    Args:
        full:        The ``full`` dict assembled in ``handle_valuation``.
        profile_key: Report profile ("legacy"/"detailed"/"professional_template").
        status:      Initial record status ("draft"/"final"/"archived").
        db_path:     DB path (tests pass tmp_path; prod uses DEFAULT_DB_PATH).

    Returns:
        report_id string as stored in the DB.
    """
    result = run_report_pipeline(
        full,
        profile_key=profile_key,
        persist=True,
        status=status,
        db_path=db_path,
    )
    return result.report_db_id


# ── BA.4a: History facades ────────────────────────────────────────────────────

def fetch_reports(
    *,
    profile_key: str | None = None,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
    owner_user_id: str | None = None,
    db_path: "Path | str" = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Bridge API integration point — history list (Wave BA.4a / S3).

    Returns a summary list of persisted reports plus the total count
    matching the applied filters. Pagination is caller-controlled.

    Args:
        profile_key:   Filter to one profile ('legacy'/'detailed'/'professional_template').
        status:        Filter to one status ('draft'/'final'/'archived').
        limit:         Max records returned (default 20).
        offset:        Skip first N records (default 0).
        owner_user_id: When provided, only returns reports owned by this user (S3).
        db_path:       DB path (tests pass tmp_path; prod uses DEFAULT_DB_PATH).

    Returns:
        {"count": <int>, "reports": [<summary>, ...]}
        where each summary has: report_db_id, property_type, location,
        market_value, report_date, status, profile_key.
    """
    records = _db_list(
        profile_key=profile_key,
        status=status,
        limit=limit,
        offset=offset,
        owner_user_id=owner_user_id,
        db_path=db_path,
    )
    total = _db_count(
        profile_key=profile_key,
        status=status,
        owner_user_id=owner_user_id,
        db_path=db_path,
    )
    summaries = [
        {
            "report_db_id":  r.report_id,
            "property_type": r.data.get("property_info", {}).get("type", ""),
            "location":      r.data.get("property_info", {}).get("address", ""),
            "market_value":  r.market_value,
            "report_date":   r.data.get("appraiser", {}).get("date", ""),
            "status":        r.status,
            "profile_key":   r.profile_key,
        }
        for r in records
    ]
    return {"count": total, "reports": summaries}


def fetch_report(
    report_id: str,
    *,
    owner_user_id: str | None = None,
    db_path: "Path | str" = DEFAULT_DB_PATH,
) -> dict[str, Any] | None:
    """Bridge API integration point — history single (Wave BA.4a / S3).

    Returns the full stored DTO for one report, or None when the ID
    is not in the database or owner does not match.

    Args:
        report_id:     The report_db_id assigned at persist time.
        owner_user_id: When provided, only returns if owner matches (S3 IDOR guard).
        db_path:       DB path (tests pass tmp_path; prod uses DEFAULT_DB_PATH).

    Returns:
        Full record dict, or None if not found / owner mismatch.
    """
    record = _db_get(report_id, owner_user_id=owner_user_id, db_path=db_path)
    if record is None:
        return None
    return {
        "report_db_id": record.report_id,
        "profile_key":  record.profile_key,
        "status":       record.status,
        "created_at":   record.created_at,
        "updated_at":   record.updated_at,
        "data":         record.data,
    }


# ── BA.4b: PDF export facade ──────────────────────────────────────────────────

def export_report_pdf(
    report_id: str,
    *,
    owner_user_id: str | None = None,
    db_path: "Path | str" = DEFAULT_DB_PATH,
) -> bytes | None:
    """Bridge API integration point — PDF export for a stored report (Wave BA.4b / S3).

    Fetches the stored DTO from the DB (owner-filtered), renders a PDF via the
    PDF engine into a temp file, reads the bytes, cleans up, and returns raw PDF
    bytes. Returns None when the report_id is not found or owner does not match.

    Args:
        report_id:     The report_db_id as stored at persist time.
        owner_user_id: When provided, only proceeds if owner matches (S3 IDOR guard).
        db_path:       DB path (tests pass tmp_path; prod uses DEFAULT_DB_PATH).

    Returns:
        PDF bytes (begins with b'%PDF'), or None if report_id not found / owner mismatch.

    Raises:
        Any exception from _pdf_generate (e.g. ValueError for bad profile_key,
        OSError for I/O failure) propagates to the caller so the route can
        return a controlled 500 response.
    """
    record = _db_get(report_id, owner_user_id=owner_user_id, db_path=db_path)
    if record is None:
        return None

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as _tmp:
        tmp_path = Path(_tmp.name)

    try:
        _pdf_generate(
            profile_key=record.profile_key,
            data=record.data,
            output_path=tmp_path,
        )
        return tmp_path.read_bytes()
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
