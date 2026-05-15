"""
government — Government / Tax Pilot Package

Compliance, tax valuation, official forms, audit trail, and digital signatures
for Egyptian government agencies (CBE, EGFSA, Tax Authority, Ministry of Finance).
"""

from .compliance_engine import (
    GovernmentComplianceEngine,
    GovernmentStandard,
    ComplianceLevel,
    ComplianceRule,
    ComplianceCheckResult,
)
from .tax_calculator import TaxCalculator, TaxClassification, TaxValuationResult
from .forms_generator import FormsGenerator, GovernmentForm
from .audit_trail import GovernmentAuditTrail, AuditAction, AuditEntry
from .digital_signature import DigitalSignatureManager, SignedDocument, SignatureAlgorithm
from .government_portal import GovernmentPortalManager, GovernmentAgencyPortal

__all__ = [
    "GovernmentComplianceEngine",
    "GovernmentStandard",
    "ComplianceLevel",
    "ComplianceRule",
    "ComplianceCheckResult",
    "TaxCalculator",
    "TaxClassification",
    "TaxValuationResult",
    "FormsGenerator",
    "GovernmentForm",
    "GovernmentAuditTrail",
    "AuditAction",
    "AuditEntry",
    "DigitalSignatureManager",
    "SignedDocument",
    "SignatureAlgorithm",
    "GovernmentPortalManager",
    "GovernmentAgencyPortal",
]
