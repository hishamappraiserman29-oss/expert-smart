from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional

from adapters.asset import AssetValuationResult


# EGVS disclosures that must appear on any court-grade valuation report
_REQUIRED_DISCLOSURES = {"EGVS_1.0", "EGVS_2.0", "EGVS_3.0"}

# Minimum confidence level to pass court-grade threshold
_PASSING_CONFIDENCE = {"high", "medium"}

# Minimum number of audit trail entries (Phase 5 + Phase 6 = at least 2)
_MIN_AUDIT_ENTRIES = 2

# Alternative values an EGVS report should carry when the asset is improved property
_RECOMMENDED_ALTERNATIVES = {"mortgage", "insurance"}

# Minimum primary value (EGP) — guard against placeholder / near-zero outputs
_MIN_VALUE_EGP = Decimal("1000")

# Weight sanity band — each weight must be within [0, 1] and all three must sum to 1
_WEIGHT_SUM_TOLERANCE = 0.01

# Category labels used in AuditFinding
CATEGORY_COMPLETENESS = "completeness"
CATEGORY_COMPLIANCE   = "compliance"
CATEGORY_METHODOLOGY  = "methodology"
CATEGORY_DATA_QUALITY = "data_quality"


@dataclass
class AuditFinding:
    """Single quality-audit finding attached to a report."""
    category:       str               # completeness | compliance | methodology | data_quality
    severity:       str               # "error" | "warning" | "info"
    code:           str               # machine-readable identifier
    message:        str               # human-readable description
    recommendation: str               # what the reviewer should do
    field_path:     Optional[str] = None  # dotted path to the offending field, if applicable
    score_impact:   int = 0           # negative points this finding deducts from quality score


@dataclass
class AuditReport:
    """Complete quality-audit result for one AssetValuationResult."""
    passed:         bool
    quality_score:  int                    # 0–100
    quality_grade:  str                    # "A" | "B" | "C" | "D" | "F"
    findings:       List[AuditFinding]     = field(default_factory=list)
    errors:         List[AuditFinding]     = field(default_factory=list)
    warnings:       List[AuditFinding]     = field(default_factory=list)
    infos:          List[AuditFinding]     = field(default_factory=list)
    summary:        str                    = ""
    metadata:       Dict[str, Any]         = field(default_factory=dict)


class ReportQualityAuditor:
    """
    Court-grade quality-control layer for AssetValuationResult objects.

    Runs four independent check groups:
      1. Completeness  — required fields, audit trail depth, alternative values
      2. Compliance    — EGVS disclosures, confidence level, primary value range
      3. Methodology   — weight sanity, cost/income balance for asset type
      4. Data quality  — metadata keys, issue severity distribution

    Each finding carries a `score_impact` (0 = info, -5 = warning, -20 = error).
    The final quality_score starts at 100 and subtracts all score_impacts.
    Scoring bands:  A ≥ 90 | B ≥ 75 | C ≥ 60 | D ≥ 45 | F < 45

    The report `passed` flag is True only when quality_score ≥ 60 AND there
    are zero error-severity findings.
    """

    # Score impact per severity (penalties)
    _PENALTY = {"error": -20, "warning": -5, "info": 0}

    # Passing threshold
    PASS_SCORE = 60

    def audit(self, result: AssetValuationResult) -> AuditReport:
        """
        Run all quality checks and return a consolidated AuditReport.

        Parameters
        ----------
        result : AssetValuationResult
            The output of any Phase 6/7 asset adapter.

        Returns
        -------
        AuditReport with findings, score, grade, and pass/fail verdict.
        """
        findings: List[AuditFinding] = []

        findings.extend(self._check_completeness(result))
        findings.extend(self._check_compliance(result))
        findings.extend(self._check_methodology(result))
        findings.extend(self._check_data_quality(result))

        errors   = [f for f in findings if f.severity == "error"]
        warnings = [f for f in findings if f.severity == "warning"]
        infos    = [f for f in findings if f.severity == "info"]

        score = 100 + sum(f.score_impact for f in findings)
        score = max(0, min(100, score))

        grade = self._grade(score)
        passed = (score >= self.PASS_SCORE) and (len(errors) == 0)

        error_count   = len(errors)
        warning_count = len(warnings)
        summary = (
            f"Quality score: {score}/100 (grade {grade}) — "
            f"{'PASS' if passed else 'FAIL'} | "
            f"{error_count} error(s), {warning_count} warning(s)"
        )

        return AuditReport(
            passed=passed,
            quality_score=score,
            quality_grade=grade,
            findings=findings,
            errors=errors,
            warnings=warnings,
            infos=infos,
            summary=summary,
            metadata={
                "asset_type":    result.asset_type,
                "primary_value": float(result.primary_value) if result.primary_value else None,
                "confidence":    result.confidence,
                "audit_entries": len(result.audit_trail),
                "disclosures":   list(result.disclosures),
            },
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Check group 1: Completeness
    # ──────────────────────────────────────────────────────────────────────────

    def _check_completeness(self, result: AssetValuationResult) -> List[AuditFinding]:
        findings = []

        # Primary value must be present
        if result.primary_value is None:
            findings.append(AuditFinding(
                category=CATEGORY_COMPLETENESS,
                severity="error",
                code="MISSING_PRIMARY_VALUE",
                message="Primary valuation value is None — calculation did not complete.",
                recommendation="Resolve validation errors in the asset adapter before generating a report.",
                field_path="primary_value",
                score_impact=self._PENALTY["error"],
            ))

        # Audit trail depth
        n = len(result.audit_trail)
        if n == 0:
            findings.append(AuditFinding(
                category=CATEGORY_COMPLETENESS,
                severity="error",
                code="EMPTY_AUDIT_TRAIL",
                message="Audit trail is empty — no calculation steps recorded.",
                recommendation="Ensure the asset adapter's value() method is called (not bypassed).",
                field_path="audit_trail",
                score_impact=self._PENALTY["error"],
            ))
        elif n < _MIN_AUDIT_ENTRIES:
            findings.append(AuditFinding(
                category=CATEGORY_COMPLETENESS,
                severity="warning",
                code="SHALLOW_AUDIT_TRAIL",
                message=f"Audit trail has only {n} entr{'y' if n == 1 else 'ies'} "
                        f"(minimum recommended: {_MIN_AUDIT_ENTRIES}).",
                recommendation="Include Phase 5 purpose-adapter entries in the audit chain.",
                field_path="audit_trail",
                score_impact=self._PENALTY["warning"],
            ))

        # Weights must be present
        if not result.weights_applied:
            findings.append(AuditFinding(
                category=CATEGORY_COMPLETENESS,
                severity="error",
                code="MISSING_WEIGHTS",
                message="weights_applied is empty — approach weighting not recorded.",
                recommendation="Populate weights_applied in AssetValuationResult.",
                field_path="weights_applied",
                score_impact=self._PENALTY["error"],
            ))

        # Disclosures must be present
        if not result.disclosures:
            findings.append(AuditFinding(
                category=CATEGORY_COMPLETENESS,
                severity="error",
                code="MISSING_DISCLOSURES",
                message="No disclosures recorded — EGVS compliance cannot be verified.",
                recommendation="Ensure the adapter appends required EGVS sections to disclosures.",
                field_path="disclosures",
                score_impact=self._PENALTY["error"],
            ))

        # Metadata basic keys
        for key in ("property_type", "area_sqm"):
            if key not in result.metadata:
                findings.append(AuditFinding(
                    category=CATEGORY_COMPLETENESS,
                    severity="warning",
                    code=f"MISSING_METADATA_{key.upper()}",
                    message=f"Metadata key '{key}' is absent from the report.",
                    recommendation=f"Include '{key}' in subject_property so it propagates to metadata.",
                    field_path=f"metadata.{key}",
                    score_impact=self._PENALTY["warning"],
                ))

        # Alternative values recommended for improved property
        if result.asset_type in ("residential", "commercial"):
            for alt in _RECOMMENDED_ALTERNATIVES:
                if alt not in result.alternative_values:
                    findings.append(AuditFinding(
                        category=CATEGORY_COMPLETENESS,
                        severity="info",
                        code=f"MISSING_ALTERNATIVE_{alt.upper()}",
                        message=f"Alternative value '{alt}' not included in report.",
                        recommendation=f"Pass '{alt}' purpose adapter result via alternative_values.",
                        field_path=f"alternative_values.{alt}",
                        score_impact=self._PENALTY["info"],
                    ))

        return findings

    # ──────────────────────────────────────────────────────────────────────────
    # Check group 2: Compliance (EGVS + confidence)
    # ──────────────────────────────────────────────────────────────────────────

    def _check_compliance(self, result: AssetValuationResult) -> List[AuditFinding]:
        findings = []

        # Required EGVS disclosures
        present = set(result.disclosures)
        for disc in sorted(_REQUIRED_DISCLOSURES):
            if disc not in present:
                findings.append(AuditFinding(
                    category=CATEGORY_COMPLIANCE,
                    severity="error",
                    code=f"MISSING_DISCLOSURE_{disc.replace('.', '_')}",
                    message=f"Required EGVS disclosure '{disc}' is absent from the report.",
                    recommendation=f"Add '{disc}' to the adapter's disclosures list.",
                    field_path="disclosures",
                    score_impact=self._PENALTY["error"],
                ))

        # AssetAdapter disclosure (traceability)
        adapter_disc = f"AssetAdapter_{result.asset_type.upper()}"
        if adapter_disc not in present:
            findings.append(AuditFinding(
                category=CATEGORY_COMPLIANCE,
                severity="warning",
                code="MISSING_ADAPTER_DISCLOSURE",
                message=f"Adapter disclosure '{adapter_disc}' not found.",
                recommendation="The asset adapter's value() method should append its own disclosure.",
                field_path="disclosures",
                score_impact=self._PENALTY["warning"],
            ))

        # Confidence level
        if result.confidence == "insufficient":
            findings.append(AuditFinding(
                category=CATEGORY_COMPLIANCE,
                severity="error",
                code="INSUFFICIENT_CONFIDENCE",
                message="Confidence is 'insufficient' — report cannot be submitted to court.",
                recommendation="Resolve all validation errors and ensure Phase 4 engines produced values.",
                field_path="confidence",
                score_impact=self._PENALTY["error"],
            ))
        elif result.confidence == "low":
            findings.append(AuditFinding(
                category=CATEGORY_COMPLIANCE,
                severity="warning",
                code="LOW_CONFIDENCE",
                message="Confidence is 'low' — additional supporting evidence is advisable.",
                recommendation="Increase comparable count or improve data quality.",
                field_path="confidence",
                score_impact=self._PENALTY["warning"],
            ))

        # Primary value range
        if result.primary_value is not None:
            if result.primary_value < _MIN_VALUE_EGP:
                findings.append(AuditFinding(
                    category=CATEGORY_COMPLIANCE,
                    severity="error",
                    code="VALUE_BELOW_MINIMUM",
                    message=f"Primary value {result.primary_value} EGP is below the minimum "
                            f"threshold ({_MIN_VALUE_EGP} EGP) — likely a calculation error.",
                    recommendation="Verify Phase 4 engine inputs (area, cap rate, land value).",
                    field_path="primary_value",
                    score_impact=self._PENALTY["error"],
                ))

        # Asset type must be declared
        if not result.asset_type:
            findings.append(AuditFinding(
                category=CATEGORY_COMPLIANCE,
                severity="error",
                code="MISSING_ASSET_TYPE",
                message="asset_type is empty — report cannot be categorised.",
                recommendation="Set asset_type to 'residential', 'commercial', or 'land'.",
                field_path="asset_type",
                score_impact=self._PENALTY["error"],
            ))

        return findings

    # ──────────────────────────────────────────────────────────────────────────
    # Check group 3: Methodology
    # ──────────────────────────────────────────────────────────────────────────

    def _check_methodology(self, result: AssetValuationResult) -> List[AuditFinding]:
        findings = []
        w = result.weights_applied

        if not w:
            return findings  # already flagged in completeness

        # Weights must sum to 1.0
        total = sum(w.values())
        if abs(total - 1.0) > _WEIGHT_SUM_TOLERANCE:
            findings.append(AuditFinding(
                category=CATEGORY_METHODOLOGY,
                severity="error",
                code="WEIGHTS_DO_NOT_SUM_TO_ONE",
                message=f"Approach weights sum to {total:.4f} (expected 1.0 ±{_WEIGHT_SUM_TOLERANCE}).",
                recommendation="Check calculate_weights() in the asset adapter.",
                field_path="weights_applied",
                score_impact=self._PENALTY["error"],
            ))

        # Each individual weight must be in [0, 1]
        for approach, weight in w.items():
            if not (0.0 <= weight <= 1.0):
                findings.append(AuditFinding(
                    category=CATEGORY_METHODOLOGY,
                    severity="error",
                    code=f"INVALID_WEIGHT_{approach.upper()}",
                    message=f"Weight for '{approach}' is {weight} — must be between 0 and 1.",
                    recommendation=f"Correct the weight for '{approach}' in calculate_weights().",
                    field_path=f"weights_applied.{approach}",
                    score_impact=self._PENALTY["error"],
                ))

        # Land: cost weight must be 0 (no building to replace)
        if result.asset_type == "land":
            cost_w = w.get("cost", None)
            if cost_w is not None and cost_w > 0:
                findings.append(AuditFinding(
                    category=CATEGORY_METHODOLOGY,
                    severity="error",
                    code="LAND_NONZERO_COST_WEIGHT",
                    message=f"Land valuation has non-zero cost weight ({cost_w}). "
                            "The cost approach does not apply to vacant land.",
                    recommendation="Set cost weight to 0.0 in the land adapter's calculate_weights().",
                    field_path="weights_applied.cost",
                    score_impact=self._PENALTY["error"],
                ))

        # Comparable approach should carry meaningful weight (>= 0.30 for non-speculative)
        comp_w = w.get("comparable", 0.0)
        if comp_w > 0 and comp_w < 0.30:
            findings.append(AuditFinding(
                category=CATEGORY_METHODOLOGY,
                severity="warning",
                code="LOW_COMPARABLE_WEIGHT",
                message=f"Comparable sales weight ({comp_w:.0%}) is very low — "
                        "market evidence may be under-represented.",
                recommendation="Review the weight preset; comparable sales should usually ≥ 30%.",
                field_path="weights_applied.comparable",
                score_impact=self._PENALTY["warning"],
            ))

        # Residential: income weight > 50% is unusual (it's owner-occupied, not investment)
        if result.asset_type == "residential":
            income_w = w.get("income", 0.0)
            if income_w > 0.50:
                findings.append(AuditFinding(
                    category=CATEGORY_METHODOLOGY,
                    severity="warning",
                    code="HIGH_INCOME_WEIGHT_RESIDENTIAL",
                    message=f"Income weight ({income_w:.0%}) exceeds 50% for a residential asset. "
                            "Income-heavy weighting is more appropriate for commercial.",
                    recommendation="Verify the ownership_type used — rental may be over-weighted.",
                    field_path="weights_applied.income",
                    score_impact=self._PENALTY["warning"],
                ))

        return findings

    # ──────────────────────────────────────────────────────────────────────────
    # Check group 4: Data quality
    # ──────────────────────────────────────────────────────────────────────────

    def _check_data_quality(self, result: AssetValuationResult) -> List[AuditFinding]:
        findings = []

        # Any pre-existing error-severity issues are critical
        existing_errors = [i for i in result.issues if i.severity == "error"]
        if existing_errors:
            for issue in existing_errors:
                findings.append(AuditFinding(
                    category=CATEGORY_DATA_QUALITY,
                    severity="error",
                    code=f"VALIDATION_ERROR_{issue.code}",
                    message=f"Validation error carried into report: {issue.message}",
                    recommendation="Correct the underlying data before generating the report.",
                    score_impact=self._PENALTY["error"],
                ))

        # Warning-level issues reduce data quality but don't block
        existing_warnings = [i for i in result.issues if i.severity == "warning"]
        if existing_warnings:
            for issue in existing_warnings:
                findings.append(AuditFinding(
                    category=CATEGORY_DATA_QUALITY,
                    severity="warning",
                    code=f"VALIDATION_WARNING_{issue.code}",
                    message=f"Validation warning in report: {issue.message}",
                    recommendation="Review and address where possible.",
                    score_impact=self._PENALTY["warning"],
                ))

        # Area_sqm should be positive (if present in metadata)
        area = result.metadata.get("area_sqm")
        if area is not None and float(area) <= 0:
            findings.append(AuditFinding(
                category=CATEGORY_DATA_QUALITY,
                severity="error",
                code="INVALID_AREA_SQM",
                message=f"area_sqm in metadata is {area} — must be positive.",
                recommendation="Pass a valid area_sqm in subject_property.",
                field_path="metadata.area_sqm",
                score_impact=self._PENALTY["error"],
            ))

        # Alternative values should be less than primary (sanity: mortgage < market value)
        if result.primary_value and "mortgage" in result.alternative_values:
            mort = result.alternative_values["mortgage"]
            if mort > result.primary_value:
                findings.append(AuditFinding(
                    category=CATEGORY_DATA_QUALITY,
                    severity="warning",
                    code="MORTGAGE_EXCEEDS_MARKET",
                    message=f"Mortgage value ({mort}) exceeds primary market value "
                            f"({result.primary_value}) — unusual.",
                    recommendation="Verify mortgage adapter LTV haircut is applied correctly.",
                    field_path="alternative_values.mortgage",
                    score_impact=self._PENALTY["warning"],
                ))

        # Info: report has no issues at all (good data)
        if not result.issues:
            findings.append(AuditFinding(
                category=CATEGORY_DATA_QUALITY,
                severity="info",
                code="CLEAN_VALIDATION",
                message="No validation issues — all inputs passed data quality checks.",
                recommendation="No action required.",
                score_impact=0,
            ))

        return findings

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _grade(score: int) -> str:
        if score >= 90:
            return "A"
        if score >= 75:
            return "B"
        if score >= 60:
            return "C"
        if score >= 45:
            return "D"
        return "F"
