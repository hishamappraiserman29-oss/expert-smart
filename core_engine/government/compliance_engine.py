"""
compliance_engine.py — Government Compliance Engine

Standards, regulations, and compliance tracking for Egyptian authorities.
All checks are reporting/disclosure only; valuation calculations are untouched.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class GovernmentStandard(str, Enum):
    EGVS = "egvs"          # Egyptian General Valuation Standards
    CBE = "cbe"            # Central Bank of Egypt
    EGFSA = "egfsa"        # Egyptian Financial Supervisory Authority
    TAX_AUTHORITY = "tax"  # Egyptian Tax Authority
    IFRS13 = "ifrs13"      # International Financial Reporting Standard 13
    IFRS16 = "ifrs16"      # IFRS 16 Lease Accounting


class ComplianceLevel(str, Enum):
    FULL_COMPLIANT = "full_compliant"
    PARTIAL_COMPLIANT = "partial_compliant"
    NON_COMPLIANT = "non_compliant"
    EXEMPT = "exempt"


@dataclass
class ComplianceRule:
    """A single compliance rule."""

    rule_id: str
    standard: GovernmentStandard
    requirement: str
    description: str
    severity: str  # "critical" | "high" | "medium" | "low"
    required_fields: List[str] = field(default_factory=list)
    effective_date: datetime = field(default_factory=datetime.utcnow)

    def check(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Return (is_compliant, error_message)."""
        for field_name in self.required_fields:
            if field_name not in data or data[field_name] is None or data[field_name] == "":
                return False, f"Missing required field: {field_name}"
        return True, None


@dataclass
class ComplianceCheckResult:
    """Result of a compliance check against one standard."""

    property_id: str
    standard: GovernmentStandard
    compliance_level: ComplianceLevel
    passed_rules: int
    failed_rules: int
    total_rules: int
    issues: List[Dict[str, str]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    checked_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "property_id": self.property_id,
            "standard": self.standard.value,
            "compliance_level": self.compliance_level.value,
            "passed_rules": self.passed_rules,
            "failed_rules": self.failed_rules,
            "total_rules": self.total_rules,
            "compliance_percentage": (
                round(self.passed_rules / self.total_rules * 100, 1)
                if self.total_rules > 0 else 0.0
            ),
            "issues": self.issues,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "checked_at": self.checked_at.isoformat(),
        }


class GovernmentComplianceEngine:
    """Rule-based compliance checker for Egyptian government standards."""

    def __init__(self) -> None:
        self.rules: Dict[str, List[ComplianceRule]] = {}
        self._initialize_rules()

    # ------------------------------------------------------------------
    # Rule initialisation
    # ------------------------------------------------------------------

    def _initialize_rules(self) -> None:
        self.rules[GovernmentStandard.EGVS.value] = [
            ComplianceRule(
                "egvs_001", GovernmentStandard.EGVS,
                "Property identification",
                "Property must be clearly identified with address, area, and type",
                "critical",
                required_fields=["street_address", "city", "area_sqm", "property_type"],
            ),
            ComplianceRule(
                "egvs_002", GovernmentStandard.EGVS,
                "Valuation date",
                "Valuation must have effective date and report date",
                "critical",
                required_fields=["effective_date", "report_date"],
            ),
            ComplianceRule(
                "egvs_003", GovernmentStandard.EGVS,
                "Comparable analysis",
                "Minimum 3 comparable properties required",
                "high",
                required_fields=["comparables"],
            ),
            ComplianceRule(
                "egvs_004", GovernmentStandard.EGVS,
                "Market analysis",
                "Market conditions and trends must be analyzed",
                "high",
                required_fields=["market_analysis"],
            ),
            ComplianceRule(
                "egvs_005", GovernmentStandard.EGVS,
                "Scope of work",
                "Scope of valuation must be documented",
                "medium",
                required_fields=["scope_of_work"],
            ),
        ]

        self.rules[GovernmentStandard.CBE.value] = [
            ComplianceRule(
                "cbe_001", GovernmentStandard.CBE,
                "Loan-to-value calculation",
                "LTV must be calculated and documented",
                "critical",
                required_fields=["property_value", "loan_amount"],
            ),
            ComplianceRule(
                "cbe_002", GovernmentStandard.CBE,
                "Collateral valuation",
                "Collateral value must be assessed separately",
                "high",
                required_fields=["collateral_value"],
            ),
            ComplianceRule(
                "cbe_003", GovernmentStandard.CBE,
                "Risk assessment",
                "Risk rating must be assigned",
                "high",
                required_fields=["risk_rating"],
            ),
            ComplianceRule(
                "cbe_004", GovernmentStandard.CBE,
                "Appraiser credentials",
                "Appraiser must have CBE approval",
                "critical",
                required_fields=["appraiser_cbe_approval"],
            ),
            ComplianceRule(
                "cbe_005", GovernmentStandard.CBE,
                "Documentation retention",
                "All supporting documents must be retained for 5 years",
                "high",
                required_fields=["documentation_archive"],
            ),
        ]

        self.rules[GovernmentStandard.TAX_AUTHORITY.value] = [
            ComplianceRule(
                "tax_001", GovernmentStandard.TAX_AUTHORITY,
                "Tax valuation basis",
                "Valuation must comply with tax authority standards",
                "critical",
                required_fields=["tax_valuation_basis"],
            ),
            ComplianceRule(
                "tax_002", GovernmentStandard.TAX_AUTHORITY,
                "Property classification",
                "Property must be classified per tax code",
                "critical",
                required_fields=["tax_classification"],
            ),
            ComplianceRule(
                "tax_003", GovernmentStandard.TAX_AUTHORITY,
                "Value documentation",
                "All value assumptions must be documented",
                "high",
                required_fields=["value_assumptions"],
            ),
            ComplianceRule(
                "tax_004", GovernmentStandard.TAX_AUTHORITY,
                "Audit trail",
                "Complete audit trail required",
                "high",
                required_fields=["audit_trail"],
            ),
        ]

        self.rules[GovernmentStandard.EGFSA.value] = [
            ComplianceRule(
                "egfsa_001", GovernmentStandard.EGFSA,
                "Fair value assessment",
                "Fair value per IFRS 13 standards",
                "critical",
                required_fields=["fair_value", "valuation_approach"],
            ),
            ComplianceRule(
                "egfsa_002", GovernmentStandard.EGFSA,
                "Level of valuation",
                "Valuation level (1, 2, or 3) must be assigned",
                "high",
                required_fields=["valuation_level"],
            ),
            ComplianceRule(
                "egfsa_003", GovernmentStandard.EGFSA,
                "Disclosure requirements",
                "Full disclosure of valuation methodology",
                "high",
                required_fields=["methodology_disclosure"],
            ),
            ComplianceRule(
                "egfsa_004", GovernmentStandard.EGFSA,
                "Expert certification",
                "Expert must be certified by EGFSA",
                "critical",
                required_fields=["expert_egfsa_certification"],
            ),
        ]

        total = sum(len(v) for v in self.rules.values())
        logger.info("Initialized %d government compliance rules", total)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_compliance(
        self,
        property_data: Dict[str, Any],
        standard: GovernmentStandard,
    ) -> ComplianceCheckResult:
        """Check property data against a single government standard."""

        property_id = property_data.get("property_id", "unknown")

        if standard.value not in self.rules:
            return ComplianceCheckResult(
                property_id=property_id,
                standard=standard,
                compliance_level=ComplianceLevel.EXEMPT,
                passed_rules=0,
                failed_rules=0,
                total_rules=0,
                warnings=["No rules defined for this standard"],
            )

        rules = self.rules[standard.value]
        passed = 0
        failed = 0
        issues: List[Dict[str, str]] = []
        warnings: List[str] = []
        recommendations: List[str] = []

        for rule in rules:
            ok, msg = rule.check(property_data)
            if ok:
                passed += 1
            else:
                failed += 1
                issues.append({
                    "rule_id": rule.rule_id,
                    "requirement": rule.requirement,
                    "severity": rule.severity,
                    "message": msg or "",
                })
                if rule.severity == "critical":
                    recommendations.append(f"Critical: {rule.requirement}")
                else:
                    warnings.append(f"{rule.severity.title()}: {rule.requirement}")

        pct = passed / len(rules) * 100 if rules else 0.0
        if failed == 0:
            level = ComplianceLevel.FULL_COMPLIANT
        elif pct >= 75:
            level = ComplianceLevel.PARTIAL_COMPLIANT
        else:
            level = ComplianceLevel.NON_COMPLIANT

        return ComplianceCheckResult(
            property_id=property_id,
            standard=standard,
            compliance_level=level,
            passed_rules=passed,
            failed_rules=failed,
            total_rules=len(rules),
            issues=issues,
            warnings=warnings,
            recommendations=recommendations,
        )

    def check_all_standards(
        self, property_data: Dict[str, Any]
    ) -> Dict[str, ComplianceCheckResult]:
        """Check compliance against all defined standards."""
        return {
            std.value: self.check_compliance(property_data, std)
            for std in GovernmentStandard
        }

    def get_compliance_certificate(
        self,
        property_id: str,
        standard: GovernmentStandard,
        result: ComplianceCheckResult,
    ) -> str:
        """Return a plain-text compliance certificate."""
        pct = result.to_dict()["compliance_percentage"]
        cert = (
            f"COMPLIANCE CERTIFICATE — {standard.value.upper()}\n"
            f"{'=' * 64}\n"
            f"Property ID:      {property_id}\n"
            f"Standard:         {standard.value.upper()}\n"
            f"Checked:          {result.checked_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Level:            {result.compliance_level.value.upper()}\n"
            f"Rules Passed:     {result.passed_rules}/{result.total_rules} ({pct:.1f}%)\n"
        )
        if result.issues:
            cert += "\nISSUES:\n"
            for issue in result.issues:
                cert += f"  [{issue['severity'].upper()}] {issue['requirement']}: {issue['message']}\n"
        if result.recommendations:
            cert += "\nRECOMMENDATIONS:\n"
            for rec in result.recommendations:
                cert += f"  * {rec}\n"
        cert += (
            f"\nGenerated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"{'=' * 64}\n"
        )
        return cert


government_compliance = GovernmentComplianceEngine()
