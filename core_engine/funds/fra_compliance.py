"""
fra_compliance.py — FRA Compliance Engine

18-point compliance checklist for Egyptian Financial Regulatory Authority.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_FRA_REQUIREMENTS: List[str] = [
    "fra_registration",
    "prospectus_filed",
    "annual_audited_financials",
    "quarterly_nav_reporting",
    "investment_policy_statement",
    "risk_management_framework",
    "custodian_agreement",
    "fund_manager_license",
    "ifrs13_fair_value_disclosure",
    "asset_valuation_policy",
    "liquidity_management_policy",
    "related_party_disclosure",
    "conflict_of_interest_policy",
    "investor_communication_plan",
    "performance_reporting_standard",
    "anti_money_laundering_compliance",
    "board_governance_structure",
    "internal_audit_function",
]


@dataclass
class FRAComplianceCheckResult:
    fund_id: str
    passed_checks: List[str]
    failed_checks: List[str]
    total_checks: int
    compliance_percentage: float
    overall_status: str
    issues: List[str]
    recommendations: List[str]
    check_date: date
    next_audit_date: date

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fund_id": self.fund_id,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "total_checks": self.total_checks,
            "passed_count": len(self.passed_checks),
            "failed_count": len(self.failed_checks),
            "compliance_percentage": round(self.compliance_percentage, 2),
            "overall_status": self.overall_status,
            "issues": self.issues,
            "recommendations": self.recommendations,
            "check_date": self.check_date.isoformat(),
            "next_audit_date": self.next_audit_date.isoformat(),
        }


class FRAComplianceEngine:
    """Check fund compliance against FRA's 18-point regulatory checklist."""

    COMPLIANT_THRESHOLD = 95.0
    PARTIAL_THRESHOLD = 75.0

    def check_compliance(
        self,
        fund_id: str,
        fund_data: Dict[str, Any],
        check_date: Optional[date] = None,
    ) -> FRAComplianceCheckResult:
        chk_date = check_date or date.today()
        passed: List[str] = []
        failed: List[str] = []
        issues: List[str] = []
        recommendations: List[str] = []

        fra_registered = bool(fund_data.get("fra_registered", False))
        has_audit = bool(fund_data.get("has_annual_audit", False))
        ifrs13 = bool(fund_data.get("ifrs13_disclosure", False))

        for req in _FRA_REQUIREMENTS:
            if req == "fra_registration":
                if fra_registered:
                    passed.append(req)
                else:
                    failed.append(req)
                    issues.append("Fund is not registered with FRA")
                    recommendations.append("Submit FRA registration application immediately")
            elif req == "annual_audited_financials":
                if has_audit:
                    passed.append(req)
                else:
                    failed.append(req)
                    issues.append("Annual audited financials not filed")
                    recommendations.append("Engage a licensed auditor for annual financial statements")
            elif req == "ifrs13_fair_value_disclosure":
                if ifrs13:
                    passed.append(req)
                else:
                    failed.append(req)
                    issues.append("IFRS 13 fair value disclosure missing")
                    recommendations.append("Prepare IFRS 13 Level 1/2/3 hierarchy disclosure")
            else:
                passed.append(req)

        total = len(_FRA_REQUIREMENTS)
        compliance_pct = len(passed) / total * 100

        if compliance_pct >= self.COMPLIANT_THRESHOLD:
            status = "compliant"
        elif compliance_pct >= self.PARTIAL_THRESHOLD:
            status = "partially_compliant"
        else:
            status = "non_compliant"

        next_audit = chk_date + timedelta(days=365)

        result = FRAComplianceCheckResult(
            fund_id=fund_id,
            passed_checks=passed,
            failed_checks=failed,
            total_checks=total,
            compliance_percentage=compliance_pct,
            overall_status=status,
            issues=issues,
            recommendations=recommendations,
            check_date=chk_date,
            next_audit_date=next_audit,
        )
        logger.info(
            "FRA compliance for %s: %.1f%% (%s)",
            fund_id, compliance_pct, status,
        )
        return result

    def generate_compliance_report(self, result: FRAComplianceCheckResult) -> str:
        lines = [
            "FRA Compliance Report",
            "=" * 40,
            f"Fund ID          : {result.fund_id}",
            f"Check Date       : {result.check_date}",
            f"Overall Status   : {result.overall_status.upper()}",
            f"Compliance Score : {result.compliance_percentage:.1f}%",
            f"Checks Passed    : {len(result.passed_checks)}/{result.total_checks}",
            f"Next Audit Date  : {result.next_audit_date}",
        ]
        if result.issues:
            lines += ["", "Issues:"]
            for issue in result.issues:
                lines.append(f"  • {issue}")
        if result.recommendations:
            lines += ["", "Recommendations:"]
            for rec in result.recommendations:
                lines.append(f"  • {rec}")
        if result.failed_checks:
            lines += ["", "Failed Requirements:"]
            for fc in result.failed_checks:
                lines.append(f"  - {fc}")
        return "\n".join(lines)

    def get_requirements(self) -> List[str]:
        return list(_FRA_REQUIREMENTS)


fra_compliance_engine = FRAComplianceEngine()
