"""
schema_validator.py — P0 structural schema validation for mass valuation data.

Validates records against data_contract.json specifications.
NO valuation logic, NO estimated values, NO statistical computation.
Reuses SanitisationResult pattern from core_engine/security/input_validator.py.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_CONTRACT_PATH = Path(__file__).parent / "data_contract.json"
_MAPPING_PATH  = Path(__file__).parent / "column_mapping.json"

_UUID_OR_ALNUM_RE = re.compile(r'^[A-Za-z0-9_\-]{1,100}$')

# Saudi Arabia bounding box (WGS84)
_SA_LAT_MIN, _SA_LAT_MAX = 16.3, 32.2
_SA_LON_MIN, _SA_LON_MAX = 34.5, 55.7


# ---------------------------------------------------------------------------
# ValidationResult — aligned with SanitisationResult pattern
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """Outcome of a structural schema check on a single property record."""

    property_id: str
    is_valid: bool
    errors: List[str]   = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    flags: List[str]    = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.is_valid

    def to_dict(self) -> Dict[str, Any]:
        return {
            "property_id": self.property_id,
            "valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "flags": self.flags,
        }


@dataclass
class BatchValidationResult:
    """Summary of schema validation for an import batch."""

    total:    int
    rejected: int
    flagged:  int
    passed:   int
    records:  List[ValidationResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "rejected": self.rejected,
            "flagged": self.flagged,
            "passed": self.passed,
            "records": [r.to_dict() for r in self.records],
        }


# ---------------------------------------------------------------------------
# Allowed enumerations (from data_contract.json)
# ---------------------------------------------------------------------------

_VALID_PROPERTY_TYPES = frozenset({
    "residential", "commercial", "industrial", "land",
    "mixed_use", "hotel", "retail", "office", "warehouse",
    "villa", "apartment", "compound",
})

_VALID_CONDITIONS = frozenset({"new", "excellent", "good", "fair", "poor", "unknown"})

_VALID_USES = frozenset({
    "owner_occupied", "investment_rental", "vacant", "mixed",
    "under_construction", "government", "waqf", "unknown",
})

_VALID_EVIDENCE_TYPES = frozenset({
    "registered_sale", "offer_listing", "rental_contract",
    "valuation_report", "government_assessment", "manual_entry", "unknown",
})

_VALID_QUALITY_FINISHES = frozenset({"luxury", "high", "standard", "economy", "shell", "unknown"})

# Date pattern YYYY-MM-DD
_DATE_RE = re.compile(r'^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])$')


# ---------------------------------------------------------------------------
# SchemaValidator
# ---------------------------------------------------------------------------

class SchemaValidator:
    """
    Structural schema validator for mass valuation property records.

    Validates: types, required fields, enum membership, numeric bounds,
    coordinate ranges, date format.

    Does NOT perform: statistical outlier detection, value imputation,
    price estimation, or any valuation logic.
    """

    def validate_record(self, record: Dict[str, Any]) -> ValidationResult:
        """Validate a single property record against the data contract."""
        pid = str(record.get("property_id", "UNKNOWN"))
        errors:   List[str] = []
        warnings: List[str] = []
        flags:    List[str] = []

        # ── Required fields ──────────────────────────────────────────────
        required = ["property_id", "property_type", "transaction_date",
                    "transaction_price", "land_area_m2"]
        for f in required:
            v = record.get(f)
            if v is None or v == "":
                errors.append(f"QR-001: required field '{f}' is missing or empty")

        if errors:
            return ValidationResult(pid, False, errors, warnings, flags)

        # ── property_id ──────────────────────────────────────────────────
        pid_val = str(record["property_id"]).strip()
        if not pid_val or len(pid_val) > 100:
            errors.append("property_id must be 1–100 characters")

        # ── property_type ────────────────────────────────────────────────
        pt = str(record.get("property_type", "")).strip().lower()
        if pt not in _VALID_PROPERTY_TYPES:
            errors.append(f"property_type '{pt}' not in allowed enum: {sorted(_VALID_PROPERTY_TYPES)}")

        # ── transaction_date ─────────────────────────────────────────────
        td = str(record.get("transaction_date", "")).strip()
        if not _DATE_RE.match(td):
            errors.append(f"transaction_date '{td}' must be ISO8601 YYYY-MM-DD")

        # ── transaction_price ────────────────────────────────────────────
        price = record.get("transaction_price")
        if price is not None:
            try:
                price_f = float(price)
                if price_f <= 0:
                    errors.append("QR-004: transaction_price must be strictly positive (> 0)")
                elif price_f < 1000:
                    errors.append("QR-004: transaction_price < 1,000 SAR — likely invalid or wrong currency")
            except (TypeError, ValueError):
                errors.append("transaction_price must be a number")

        # ── land_area_m2 ─────────────────────────────────────────────────
        area = record.get("land_area_m2")
        if area is not None:
            try:
                area_f = float(area)
                if area_f <= 0:
                    errors.append("QR-005: land_area_m2 must be > 0")
                elif area_f < 0.1:
                    errors.append("land_area_m2 < 0.1 m² — below minimum threshold")
                elif area_f > 10_000_000:
                    warnings.append("land_area_m2 > 10,000,000 m² — please verify")
            except (TypeError, ValueError):
                errors.append("land_area_m2 must be a number")

        # ── built_up_area_m2 (optional) ──────────────────────────────────
        bua = record.get("built_up_area_m2")
        if bua is not None:
            try:
                bua_f = float(bua)
                if bua_f <= 0:
                    errors.append("QR-005: built_up_area_m2 must be > 0 if present")
            except (TypeError, ValueError):
                errors.append("built_up_area_m2 must be a number if present")

        # ── coordinates (optional but paired) ────────────────────────────
        lat = record.get("latitude") or (record.get("coordinates") or {}).get("latitude")
        lon = record.get("longitude") or (record.get("coordinates") or {}).get("longitude")
        lat_present = lat is not None
        lon_present = lon is not None

        if lat_present != lon_present:
            errors.append("QR-009: latitude and longitude must both be present or both null")
        elif lat_present and lon_present:
            try:
                lat_f = float(lat)
                lon_f = float(lon)
                if not (_SA_LAT_MIN <= lat_f <= _SA_LAT_MAX):
                    errors.append(f"QR-008: latitude {lat_f} outside Saudi bounds [{_SA_LAT_MIN}, {_SA_LAT_MAX}]")
                if not (_SA_LON_MIN <= lon_f <= _SA_LON_MAX):
                    errors.append(f"QR-008: longitude {lon_f} outside Saudi bounds [{_SA_LON_MIN}, {_SA_LON_MAX}]")
            except (TypeError, ValueError):
                errors.append("latitude/longitude must be numbers")

        # ── Optional enum fields ──────────────────────────────────────────
        condition = record.get("condition")
        if condition is not None and str(condition).lower() not in _VALID_CONDITIONS:
            warnings.append(f"condition '{condition}' not in enum — will default to 'unknown'")
            flags.append("condition_normalised_to_unknown")

        use = record.get("use")
        if use is not None and str(use).lower() not in _VALID_USES:
            warnings.append(f"use '{use}' not in enum — will default to 'unknown'")
            flags.append("use_normalised_to_unknown")

        evidence = record.get("evidence_type")
        if evidence is not None and str(evidence).lower() not in _VALID_EVIDENCE_TYPES:
            warnings.append(f"evidence_type '{evidence}' not in enum — will default to 'unknown'")
            flags.append("evidence_type_normalised_to_unknown")

        quality = record.get("quality_finish")
        if quality is not None and str(quality).lower() not in _VALID_QUALITY_FINISHES:
            warnings.append(f"quality_finish '{quality}' not in enum — will default to 'unknown'")
            flags.append("quality_finish_normalised_to_unknown")

        # ── Occupancy range ───────────────────────────────────────────────
        occ = record.get("occupancy")
        if occ is not None:
            try:
                occ_f = float(occ)
                if not (0.0 <= occ_f <= 100.0):
                    errors.append(f"occupancy {occ_f} outside range [0, 100]")
            except (TypeError, ValueError):
                errors.append("occupancy must be a number between 0 and 100")

        # ── Age ────────────────────────────────────────────────────────────
        age = record.get("age")
        if age is not None:
            try:
                age_i = int(float(age))
                if age_i < 0:
                    errors.append("age must be non-negative")
                elif age_i > 200:
                    warnings.append(f"age {age_i} years exceeds 200 — please verify")
            except (TypeError, ValueError):
                errors.append("age must be an integer")

        # ── Location warning ───────────────────────────────────────────────
        city = record.get("city")
        if not city and not lat_present:
            flags.append("QR-015: both city and coordinates absent — flag_for_review")
            warnings.append("QR-015: no location information (city or coordinates) — flagged for manual review")

        is_valid = len(errors) == 0
        return ValidationResult(pid, is_valid, errors, warnings, flags)

    def validate_batch(
        self,
        records: List[Dict[str, Any]],
    ) -> BatchValidationResult:
        """Validate a list of property records and return a batch summary."""
        results: List[ValidationResult] = []
        for rec in records:
            results.append(self.validate_record(rec))

        rejected = sum(1 for r in results if not r.is_valid)
        flagged  = sum(1 for r in results if r.is_valid and r.flags)
        passed   = sum(1 for r in results if r.is_valid and not r.flags)

        return BatchValidationResult(
            total=len(records),
            rejected=rejected,
            flagged=flagged,
            passed=passed,
            records=results,
        )

    def validate_audit_trail_required_fields(
        self,
        audit_record: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """
        Check that an audit trail record contains all mandatory fields
        from audit_trail.schema.json.
        No value logic — structural check only.
        """
        required_fields = [
            "audit_id", "run_id", "dataset_id", "model_id",
            "run_hash", "dataset_hash", "model_hash",
            "code_commit", "feature_schema_hash",
            "hyperparameters", "random_seed",
            "training_period", "validation_strategy",
            "standard_version_id", "created_at",
        ]
        missing = [f for f in required_fields if f not in audit_record or audit_record[f] is None]
        if missing:
            return False, [f"audit_trail missing required field: '{f}'" for f in missing]

        # Check advisory_only flag
        if audit_record.get("advisory_only") is not True:
            return False, ["audit_trail.advisory_only must be True"]
        if audit_record.get("certification_ready") is not False:
            return False, ["audit_trail.certification_ready must be False"]

        return True, []

    def validate_run_state_transition(
        self,
        from_state: str,
        to_state: str,
    ) -> Tuple[bool, str]:
        """
        Validate that a run state transition is permitted per states.json.
        No valuation logic — governance check only.
        """
        allowed: Dict[str, List[str]] = {
            "draft":                    ["training", "rejected"],
            "training":                 ["validated", "rejected"],
            "validated":                ["approved_for_internal_use", "rejected"],
            "approved_for_internal_use": ["active", "deprecated", "rejected"],
            "active":                   ["challenger", "deprecated"],
            "challenger":               ["active", "deprecated", "rejected"],
            "deprecated":               ["archived"],
            "rejected":                 ["archived"],
            "archived":                 [],
        }
        permitted = allowed.get(from_state, [])
        if to_state in permitted:
            return True, "ok"
        return False, (
            f"Transition '{from_state}' → '{to_state}' is not permitted. "
            f"Allowed next states: {permitted}"
        )
