"""
Composite Property Wave 3 — Pre-flight validator.

Validates component dicts and purpose strings BEFORE they reach
CompositeEngine (Wave 1) or PurposeComplianceAdapter (Wave 2).

Design:
- Never raises on validation failure — returns CompositeValidationReport.
- Raises CompositeValidationError only on programmer misuse (wrong arg types,
  length mismatch).
- DRY: imports ASSET_TYPES and PURPOSE_RULES from Waves 1 and 2 directly.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Mapping

from valuation_engines.composite_engine import ASSET_TYPES
from adapters.purpose_adapter import PURPOSE_RULES


# ─────────────────────────────────────────────────────────────────────
# Severity
# ─────────────────────────────────────────────────────────────────────

class Severity(enum.Enum):
    BLOCKING = "BLOCKING"
    ADVISORY = "ADVISORY"


# ─────────────────────────────────────────────────────────────────────
# Result types
# ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ValidationIssue:
    severity: Severity
    code: str
    component_index: int | None
    field: str
    message: str


@dataclass(frozen=True)
class CompositeValidationReport:
    issues: tuple[ValidationIssue, ...]

    @property
    def blocking_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.BLOCKING)

    @property
    def advisory_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.ADVISORY)

    @property
    def is_blocking(self) -> bool:
        return self.blocking_count > 0

    @property
    def is_clean(self) -> bool:
        return len(self.issues) == 0


# ─────────────────────────────────────────────────────────────────────
# Programmer-misuse exception
# ─────────────────────────────────────────────────────────────────────

class CompositeValidationError(Exception):
    """Raised for programmer misuse, NOT for validation failures."""


# ─────────────────────────────────────────────────────────────────────
# Coherence rules
# ─────────────────────────────────────────────────────────────────────

# Concession-based types: land/building value may be encumbered by terms.
_CONCESSION_TYPES: frozenset[str] = frozenset({"المطارات والموانئ"})

_COHERENCE_RISKY_PURPOSES: frozenset[str] = frozenset({
    "التصفية الإجبارية - القيمة التصفوية (Liquidation Value x0.82)",
    "الرهن والتمويل البنكي - القيمة السوقية لأغراض التمويل (0.95x)",
})

_MAX_CONCESSION_YEARS: int = 99


# ─────────────────────────────────────────────────────────────────────
# Validator
# ─────────────────────────────────────────────────────────────────────

class CompositeValidator:
    """Pre-flight validator for composite property inputs (Wave 3)."""

    # ── Component ────────────────────────────────────────────────────

    def validate_component(
        self,
        component: Mapping[str, Any],
        index: int = 0,
    ) -> list[ValidationIssue]:
        """Validate one component dict. Returns issues list (may be empty).

        Raises:
            CompositeValidationError: component is not a Mapping.
        """
        if not isinstance(component, Mapping):
            raise CompositeValidationError(
                f"component must be a Mapping, got {type(component).__name__}"
            )
        issues: list[ValidationIssue] = []

        # asset_type — required; stops further checks if absent or unknown
        asset_type = component.get("asset_type")
        if asset_type is None:
            issues.append(ValidationIssue(
                severity=Severity.BLOCKING,
                code="MISSING_ASSET_TYPE",
                component_index=index,
                field="asset_type",
                message="asset_type is required",
            ))
            return issues

        if asset_type not in ASSET_TYPES:
            issues.append(ValidationIssue(
                severity=Severity.BLOCKING,
                code="UNKNOWN_ASSET_TYPE",
                component_index=index,
                field="asset_type",
                message=f"Unknown asset_type: {asset_type!r}",
            ))
            return issues

        # area_sqm — required, numeric, positive
        area = component.get("area_sqm")
        if area is None:
            issues.append(ValidationIssue(
                severity=Severity.BLOCKING,
                code="NON_POSITIVE_AREA",
                component_index=index,
                field="area_sqm",
                message="area_sqm is required",
            ))
        elif not isinstance(area, (int, float)):
            issues.append(ValidationIssue(
                severity=Severity.BLOCKING,
                code="NON_POSITIVE_AREA",
                component_index=index,
                field="area_sqm",
                message=f"area_sqm must be numeric, got {type(area).__name__}",
            ))
        elif area <= 0:
            issues.append(ValidationIssue(
                severity=Severity.BLOCKING,
                code="NON_POSITIVE_AREA",
                component_index=index,
                field="area_sqm",
                message=f"area_sqm must be > 0, got {area}",
            ))

        # specific_attributes — must be a Mapping
        specific = component.get("specific_attributes", {})
        if not isinstance(specific, Mapping):
            issues.append(ValidationIssue(
                severity=Severity.BLOCKING,
                code="MISSING_REQUIRED_ATTR",
                component_index=index,
                field="specific_attributes",
                message="specific_attributes must be a Mapping",
            ))
            return issues

        # required attrs per schema
        for attr_name, attr_type in ASSET_TYPES[asset_type].items():
            value = specific.get(attr_name)
            if value is None:
                issues.append(ValidationIssue(
                    severity=Severity.BLOCKING,
                    code="MISSING_REQUIRED_ATTR",
                    component_index=index,
                    field=f"specific_attributes.{attr_name}",
                    message=f"Required attribute '{attr_name}' is missing",
                ))
                continue

            type_ok: bool
            if attr_type in (int, float):
                type_ok = isinstance(value, (int, float))
            else:
                type_ok = isinstance(value, attr_type)

            if not type_ok:
                issues.append(ValidationIssue(
                    severity=Severity.BLOCKING,
                    code="WRONG_ATTR_TYPE",
                    component_index=index,
                    field=f"specific_attributes.{attr_name}",
                    message=(
                        f"'{attr_name}' expected {attr_type.__name__}, "
                        f"got {type(value).__name__}"
                    ),
                ))

        # implausible concession_years_remaining
        cy = specific.get("concession_years_remaining")
        if cy is not None and isinstance(cy, (int, float)):
            if cy > _MAX_CONCESSION_YEARS:
                issues.append(ValidationIssue(
                    severity=Severity.ADVISORY,
                    code="IMPLAUSIBLE_RANGE",
                    component_index=index,
                    field="specific_attributes.concession_years_remaining",
                    message=(
                        f"concession_years_remaining={cy} exceeds plausible "
                        f"maximum of {_MAX_CONCESSION_YEARS}"
                    ),
                ))

        return issues

    # ── Purpose ──────────────────────────────────────────────────────

    def validate_purpose(
        self,
        purpose: str,
        component_index: int | None = None,
    ) -> list[ValidationIssue]:
        """Validate one purpose string. Returns issues list (may be empty).

        Raises:
            CompositeValidationError: purpose is not a str.
        """
        if not isinstance(purpose, str):
            raise CompositeValidationError(
                f"purpose must be str, got {type(purpose).__name__}"
            )
        issues: list[ValidationIssue] = []

        if purpose not in PURPOSE_RULES:
            issues.append(ValidationIssue(
                severity=Severity.BLOCKING,
                code="UNKNOWN_PURPOSE",
                component_index=component_index,
                field="purpose",
                message=f"Unknown purpose: {purpose!r}",
            ))
            return issues

        rule = PURPOSE_RULES[purpose]
        if rule.get("deep", False):
            issues.append(ValidationIssue(
                severity=Severity.ADVISORY,
                code="DEFERRED_DEEP_ROUTE",
                component_index=component_index,
                field="purpose",
                message=(
                    f"Purpose '{purpose}' uses deep route '{rule['route']}'"
                    " — full computation deferred to a later wave"
                ),
            ))

        return issues

    # ── Full validation ───────────────────────────────────────────────

    def validate(
        self,
        components: list[Mapping[str, Any]],
        purposes: list[str],
    ) -> CompositeValidationReport:
        """Validate all components + purposes together.

        Raises:
            CompositeValidationError: wrong arg types or length mismatch.
        """
        if not isinstance(components, list):
            raise CompositeValidationError(
                f"components must be a list, got {type(components).__name__}"
            )
        if not isinstance(purposes, list):
            raise CompositeValidationError(
                f"purposes must be a list, got {type(purposes).__name__}"
            )
        if len(components) != len(purposes):
            raise CompositeValidationError(
                f"components ({len(components)}) and purposes "
                f"({len(purposes)}) length mismatch"
            )

        all_issues: list[ValidationIssue] = []

        for idx, (component, purpose) in enumerate(zip(components, purposes)):
            all_issues.extend(self.validate_component(component, idx))
            all_issues.extend(self.validate_purpose(purpose, idx))

            # coherence: concession-based type + risky purpose
            asset_type = (
                component.get("asset_type")
                if isinstance(component, Mapping)
                else None
            )
            if asset_type in _CONCESSION_TYPES and purpose in _COHERENCE_RISKY_PURPOSES:
                all_issues.append(ValidationIssue(
                    severity=Severity.ADVISORY,
                    code="PURPOSE_ASSET_COHERENCE",
                    component_index=idx,
                    field="purpose",
                    message=(
                        f"Asset type '{asset_type}' (concession-based) with "
                        f"purpose '{purpose}' — land/building value may be "
                        "encumbered by concession terms; domain review advised"
                    ),
                ))

        return CompositeValidationReport(issues=tuple(all_issues))
