"""
uspap.py — USPAP-Oriented Disclosure & Reporting Framework.

IMPORTANT: This module is a REPORTING / DISCLOSURE framework only.
It does NOT perform valuations. It does NOT change any valuation
engine results. It is OPTIONAL and only applied when explicitly
selected by the user.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class USPAPCompliance(str, Enum):
    """USPAP compliance level labels."""
    NOT_APPLICABLE = "not_applicable"
    APPRAISER_CERTIFIED = "certified"
    APPRAISER_LICENSED = "licensed"
    USPAP_ORIENTED = "uspap_oriented"


class USPAPWarning(str, Enum):
    """USPAP disclosure field warnings."""
    MISSING_INTENDED_USER = "missing_intended_user"
    MISSING_INTENDED_USE = "missing_intended_use"
    MISSING_SCOPE_OF_WORK = "missing_scope_of_work"
    MISSING_PROPERTY_ID = "missing_property_id"
    MISSING_EFFECTIVE_DATE = "missing_effective_date"
    MISSING_EXTRAORDINARY_ASSUMPTIONS = "missing_extraordinary_assumptions"
    MISSING_COMPETENCY = "missing_competency"
    MISSING_CERTIFICATION = "missing_certification"
    MISSING_WORKFILE_NOTE = "missing_workfile_note"


@dataclass
class USPAPPropertyIdentification:
    """Property identification section per USPAP Standards Rule 1-2(e)."""
    street_address: str
    city: str
    state: str
    zip_code: str
    legal_description: Optional[str] = None
    parcel_id: Optional[str] = None
    subdivision: Optional[str] = None
    county: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "street_address": self.street_address,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "legal_description": self.legal_description,
            "parcel_id": self.parcel_id,
            "subdivision": self.subdivision,
            "county": self.county,
        }


@dataclass
class USPAPAssumptions:
    """USPAP extraordinary assumptions and hypothetical conditions."""
    extraordinary_assumptions: List[str] = field(default_factory=list)
    hypothetical_conditions: List[str] = field(default_factory=list)
    has_extraordinary_assumptions: bool = False
    has_hypothetical_conditions: bool = False

    def add_extraordinary_assumption(self, assumption: str) -> None:
        if assumption and assumption not in self.extraordinary_assumptions:
            self.extraordinary_assumptions.append(assumption)
            self.has_extraordinary_assumptions = True

    def add_hypothetical_condition(self, condition: str) -> None:
        if condition and condition not in self.hypothetical_conditions:
            self.hypothetical_conditions.append(condition)
            self.has_hypothetical_conditions = True

    def to_dict(self) -> Dict:
        return {
            "extraordinary_assumptions": self.extraordinary_assumptions,
            "hypothetical_conditions": self.hypothetical_conditions,
            "has_extraordinary_assumptions": self.has_extraordinary_assumptions,
            "has_hypothetical_conditions": self.has_hypothetical_conditions,
        }


@dataclass
class USPAPCompetencyStatement:
    """Appraiser competency statement per USPAP Competency Rule."""
    appraiser_name: str
    appraiser_license: str
    appraiser_designation: Optional[str] = None
    experience_with_property_type: bool = True
    experience_with_market: bool = True
    experience_with_valuation_assignment: bool = True
    statement: str = ""

    def get_competency_statement(self) -> str:
        if self.statement:
            return self.statement
        desc = self.appraiser_designation or "real property"
        stmt = f"I certify that I am competent to perform this appraisal of {desc}"
        if self.experience_with_property_type:
            stmt += " and have adequate experience with this type of property"
        if self.experience_with_market:
            stmt += " in this market"
        stmt += "."
        return stmt

    def to_dict(self) -> Dict:
        return {
            "appraiser_name": self.appraiser_name,
            "appraiser_license": self.appraiser_license,
            "appraiser_designation": self.appraiser_designation,
            "experience_with_property_type": self.experience_with_property_type,
            "experience_with_market": self.experience_with_market,
            "experience_with_valuation_assignment": self.experience_with_valuation_assignment,
            "competency_statement": self.get_competency_statement(),
        }


@dataclass
class USPAPCertification:
    """USPAP certification statement per Standards Rule 2-3."""
    appraiser_name: str
    certification_date: datetime
    appraiser_license: str
    scope_of_work: str = ""
    limitation_of_liability: bool = True

    def get_certification_statement(self) -> str:
        sow = self.scope_of_work or "desktop appraisal"
        return (
            "I certify that, to the best of my knowledge and belief, the statements of fact "
            "contained in this report are true and correct, and the reported analyses, conclusions, "
            "and opinions are limited only by the reported assumptions and limiting conditions and "
            "are my personal, impartial, and unbiased professional analyses, opinions, and conclusions.\n\n"
            "I certify that I have no present or prospective interest in the property that is the "
            "subject of this report and that I have no personal interest or bias with respect to "
            "the parties involved.\n\n"
            "I certify that my professional reputation is not contingent upon the development or "
            "reporting of a predetermined value or direction in value that favors the cause of the client.\n\n"
            f"I certify that this appraisal assignment was developed, and this report has been prepared, "
            f"in conformity with the Uniform Standards of Professional Appraisal Practice (USPAP) "
            f"standards applicable to the development of a {sow} appraisal assignment.\n\n"
            "This appraisal is USPAP-Oriented Disclosure Support, subject to professional review "
            "and verification."
        )

    def to_dict(self) -> Dict:
        return {
            "appraiser_name": self.appraiser_name,
            "certification_date": self.certification_date.isoformat(),
            "appraiser_license": self.appraiser_license,
            "scope_of_work": self.scope_of_work,
            "certification_statement": self.get_certification_statement(),
        }


@dataclass
class USPAPWorkfileNote:
    """USPAP workfile documentation note per Record Keeping Rule."""
    content: str
    date_created: datetime = field(default_factory=datetime.utcnow)
    workfile_reference: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "content": self.content,
            "date_created": self.date_created.isoformat(),
            "workfile_reference": self.workfile_reference,
        }


@dataclass
class USPAPReport:
    """Full USPAP disclosure report framework."""
    report_type: str
    intended_user: str
    intended_use: str
    scope_of_work: str
    effective_date: datetime
    report_date: datetime
    property_identification: USPAPPropertyIdentification
    assumptions: USPAPAssumptions
    competency: USPAPCompetencyStatement
    certification: USPAPCertification
    workfile_note: USPAPWorkfileNote
    compliance_level: USPAPCompliance = USPAPCompliance.USPAP_ORIENTED
    is_mass_appraisal: bool = False
    is_avm_valuation: bool = False

    def to_dict(self) -> Dict:
        return {
            "report_type": self.report_type,
            "intended_user": self.intended_user,
            "intended_use": self.intended_use,
            "scope_of_work": self.scope_of_work,
            "effective_date": self.effective_date.isoformat(),
            "report_date": self.report_date.isoformat(),
            "property_identification": self.property_identification.to_dict(),
            "assumptions": self.assumptions.to_dict(),
            "competency": self.competency.to_dict(),
            "certification": self.certification.to_dict(),
            "workfile_note": self.workfile_note.to_dict(),
            "compliance_level": self.compliance_level.value,
            "is_mass_appraisal": self.is_mass_appraisal,
            "is_avm_valuation": self.is_avm_valuation,
        }


class USPAPComplianceChecker:
    """Validate USPAP disclosure fields and return warnings/errors."""

    @staticmethod
    def check_compliance(report: USPAPReport) -> Tuple[List[str], List[str]]:
        """
        Check disclosure field completeness.

        Returns:
            (warnings, errors)  — warnings are advisory; errors are required fields.
        """
        warnings: List[str] = []
        errors: List[str] = []

        logger.info("Checking USPAP compliance fields...")

        # Advisory fields
        if not report.intended_user:
            warnings.append("Intended user not specified")
        if not report.intended_use:
            warnings.append("Intended use not specified")
        if not report.scope_of_work:
            warnings.append("Scope of work not documented")
        if not report.competency.appraiser_license:
            warnings.append("Appraiser license number should be included")
        if not report.certification.scope_of_work:
            warnings.append("Certification scope of work not specified")
        if not report.workfile_note.content:
            warnings.append("Workfile documentation note is recommended")

        # Required fields
        if not report.property_identification.city:
            errors.append("Property city is required")
        if not report.property_identification.state:
            errors.append("Property state is required")
        if not report.property_identification.zip_code:
            errors.append("Property zip code is required")
        if not report.competency.appraiser_name:
            errors.append("Appraiser name is required")

        # Assumption consistency
        if report.assumptions.has_extraordinary_assumptions and not report.assumptions.extraordinary_assumptions:
            errors.append("Extraordinary assumptions listed but not detailed")
        if report.assumptions.has_hypothetical_conditions and not report.assumptions.hypothetical_conditions:
            errors.append("Hypothetical conditions listed but not detailed")

        # AVM / Mass Appraisal guards
        if report.is_avm_valuation:
            if report.compliance_level == USPAPCompliance.APPRAISER_CERTIFIED:
                errors.append(
                    "AVM valuations cannot claim USPAP certified compliance. "
                    "Use 'USPAP-Oriented' instead"
                )
            warnings.append(
                "This is an Automated Valuation Model (AVM). "
                "USPAP applies to appraisers, not AVM systems"
            )

        if report.is_mass_appraisal:
            if report.compliance_level == USPAPCompliance.APPRAISER_CERTIFIED:
                errors.append(
                    "Mass appraisals cannot claim USPAP certified compliance. "
                    "Use 'USPAP-Oriented' instead"
                )
            warnings.append(
                "This is a mass appraisal analysis. "
                "Subject to professional appraiser review"
            )

        if warnings:
            logger.warning("USPAP warnings (%d): %s", len(warnings), warnings)
        if errors:
            logger.error("USPAP errors (%d): %s", len(errors), errors)
        if not warnings and not errors:
            logger.info("USPAP compliance check passed")

        return warnings, errors


class USPAPComplianceAddenum:
    """Generate USPAP-oriented compliance addendum text for reports."""

    @staticmethod
    def generate_addendum(report: USPAPReport) -> str:
        prop = report.property_identification
        lines: List[str] = [
            "╔════════════════════════════════════════════════════════════════╗",
            "║        USPAP-ORIENTED COMPLIANCE ADDENDUM                      ║",
            "║     Subject to Professional Review and Verification             ║",
            "╚════════════════════════════════════════════════════════════════╝",
            "",
            "COMPLIANCE NOTICE:",
            "This report provides USPAP-oriented disclosure support. It is NOT",
            "a certified appraisal and does not constitute professional appraisal",
            "services. All values and conclusions are subject to verification by",
            "a qualified, licensed appraiser in the applicable jurisdiction.",
            "",
            "REPORT INFORMATION:",
            f"  Report Type:           {report.report_type}",
            f"  Report Date:           {report.report_date.strftime('%B %d, %Y')}",
            f"  Effective Date:        {report.effective_date.strftime('%B %d, %Y')}",
            f"  Compliance Level:      {report.compliance_level.value}",
            "",
            "INTENDED USE AND USER:",
            f"  Intended User:         {report.intended_user}",
            f"  Intended Use:          {report.intended_use}",
            "",
            "SCOPE OF WORK:",
            f"  {report.scope_of_work}",
            "",
            "PROPERTY IDENTIFICATION:",
            f"  Address:               {prop.street_address}",
            f"                         {prop.city}, {prop.state} {prop.zip_code}",
            f"  Parcel ID:             {prop.parcel_id or 'Not provided'}",
            f"  Legal Description:     {prop.legal_description or 'See county records'}",
            "",
            "ASSUMPTIONS AND CONDITIONS:",
        ]

        if report.assumptions.extraordinary_assumptions:
            lines.append("")
            lines.append("  Extraordinary Assumptions:")
            for ea in report.assumptions.extraordinary_assumptions:
                lines.append(f"    • {ea}")

        if report.assumptions.hypothetical_conditions:
            lines.append("")
            lines.append("  Hypothetical Conditions:")
            for hc in report.assumptions.hypothetical_conditions:
                lines.append(f"    • {hc}")

        if report.is_avm_valuation:
            lines += [
                "",
                "AUTOMATED VALUATION MODEL (AVM) NOTICE:",
                "This valuation was generated using an automated valuation model.",
                "AVM systems are not subject to USPAP standards. However, this report",
                "provides USPAP-oriented disclosure support for informational purposes.",
                "This is NOT a professional appraisal and requires verification by a",
                "qualified appraiser for lending, legal, or official purposes.",
            ]

        if report.is_mass_appraisal:
            lines += [
                "",
                "MASS APPRAISAL NOTICE:",
                "This analysis is based on mass appraisal methodology. While this",
                "report provides USPAP-oriented disclosure support, it represents",
                "statistical analysis, not individual professional appraisals.",
                "Each property should be individually appraised for final valuation.",
            ]

        lines += [
            "",
            "APPRAISER COMPETENCY STATEMENT:",
            report.competency.get_competency_statement(),
            "",
            "CERTIFICATION STATEMENT:",
            report.certification.get_certification_statement(),
            "",
            "WORKFILE DOCUMENTATION:",
            report.workfile_note.content,
            "",
            "DISCLAIMER:",
            "This report is provided as-is for informational purposes. The user",
            "assumes all responsibility for verification and compliance with local,",
            "state, and federal regulations. This USPAP-oriented support does not",
            "constitute professional appraisal services and should not be relied",
            "upon for lending, legal, tax, or investment decisions without review",
            "by a qualified professional appraiser.",
            "",
            "══════════════════════════════════════════════════════════════════",
        ]

        return "\n".join(lines)
