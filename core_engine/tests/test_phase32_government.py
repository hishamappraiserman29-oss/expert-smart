"""
test_phase32_government.py — Phase 32 Government / Tax Pilot Tests

Covers:
  A. GovernmentComplianceEngine  (A01–A10)
  B. TaxCalculator               (B01–B10)
  C. FormsGenerator              (C01–C08)
  D. GovernmentAuditTrail        (D01–D06)
  E. DigitalSignatureManager     (E01–E06)
  F. GovernmentPortalManager     (F01–F06)

KEY INVARIANT: Government module is reporting/disclosure only.
No compliance check or tax calculation alters valuation engine output.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from government.compliance_engine import (
    ComplianceLevel,
    GovernmentComplianceEngine,
    GovernmentStandard,
)
from government.tax_calculator import TaxCalculator, TaxClassification
from government.forms_generator import FormsGenerator, GovernmentForm
from government.audit_trail import AuditAction, GovernmentAuditTrail
from government.digital_signature import DigitalSignatureManager, SignatureAlgorithm
from government.government_portal import GovernmentPortalManager


# ===========================================================================
# Helpers
# ===========================================================================

def _full_egvs_data(property_id: str = "prop_001") -> dict:
    return {
        "property_id": property_id,
        "street_address": "10 Tahrir Square",
        "city": "Cairo",
        "area_sqm": 200,
        "property_type": "residential",
        "effective_date": datetime.utcnow(),
        "report_date": datetime.utcnow(),
        "comparables": ["comp_1", "comp_2", "comp_3"],
        "market_analysis": "Active market with steady demand",
        "scope_of_work": "Full desktop appraisal",
    }


def _full_cbe_data(property_id: str = "prop_cbe") -> dict:
    return {
        "property_id": property_id,
        "property_value": 2_000_000,
        "loan_amount": 1_400_000,
        "collateral_value": 2_000_000,
        "risk_rating": "Low",
        "appraiser_cbe_approval": "CBE-2024-001",
        "documentation_archive": "DOC-2024-001",
    }


def _full_tax_data(property_id: str = "prop_tax") -> dict:
    return {
        "property_id": property_id,
        "tax_valuation_basis": "Market Value",
        "tax_classification": "residential",
        "value_assumptions": "No extraordinary conditions",
        "audit_trail": "AUDIT-2024-001",
    }


def _full_egfsa_data(property_id: str = "prop_egfsa") -> dict:
    return {
        "property_id": property_id,
        "fair_value": 3_000_000,
        "valuation_approach": "Market Approach",
        "valuation_level": "Level 2",
        "methodology_disclosure": "Full IFRS 13 disclosure",
        "expert_egfsa_certification": "EGFSA-CERT-2024",
    }


# ===========================================================================
# A. GovernmentComplianceEngine
# ===========================================================================

class TestGovernmentComplianceEngine:

    def setup_method(self):
        self.engine = GovernmentComplianceEngine()

    def test_A01_egvs_full_compliance(self):
        result = self.engine.check_compliance(_full_egvs_data(), GovernmentStandard.EGVS)
        assert result.compliance_level == ComplianceLevel.FULL_COMPLIANT
        assert result.failed_rules == 0

    def test_A02_cbe_full_compliance(self):
        result = self.engine.check_compliance(_full_cbe_data(), GovernmentStandard.CBE)
        assert result.compliance_level == ComplianceLevel.FULL_COMPLIANT
        assert result.failed_rules == 0

    def test_A03_tax_authority_full_compliance(self):
        result = self.engine.check_compliance(_full_tax_data(), GovernmentStandard.TAX_AUTHORITY)
        assert result.compliance_level == ComplianceLevel.FULL_COMPLIANT

    def test_A04_egfsa_full_compliance(self):
        result = self.engine.check_compliance(_full_egfsa_data(), GovernmentStandard.EGFSA)
        assert result.compliance_level == ComplianceLevel.FULL_COMPLIANT

    def test_A05_missing_fields_produce_non_compliant(self):
        result = self.engine.check_compliance(
            {"property_id": "empty"}, GovernmentStandard.EGVS
        )
        assert result.compliance_level == ComplianceLevel.NON_COMPLIANT
        assert result.failed_rules > 0

    def test_A06_issues_list_populated_on_failure(self):
        result = self.engine.check_compliance(
            {"property_id": "x"}, GovernmentStandard.CBE
        )
        assert len(result.issues) > 0
        assert all("rule_id" in i for i in result.issues)
        assert all("severity" in i for i in result.issues)

    def test_A07_partial_compliance_level(self):
        # Provide 4/5 CBE fields → 80% → PARTIAL_COMPLIANT
        data = {
            "property_id": "partial",
            "property_value": 1_000_000,
            "loan_amount": 700_000,
            "collateral_value": 1_000_000,
            "risk_rating": "Medium",
            "appraiser_cbe_approval": "CBE-TEMP",
            # missing documentation_archive only → 4/5 = 80%
        }
        result = self.engine.check_compliance(data, GovernmentStandard.CBE)
        assert result.compliance_level == ComplianceLevel.PARTIAL_COMPLIANT

    def test_A08_to_dict_has_all_required_keys(self):
        result = self.engine.check_compliance(_full_egvs_data(), GovernmentStandard.EGVS)
        d = result.to_dict()
        for key in (
            "property_id", "standard", "compliance_level",
            "passed_rules", "failed_rules", "total_rules",
            "compliance_percentage", "issues", "warnings",
            "recommendations", "checked_at",
        ):
            assert key in d, f"Missing key: {key}"

    def test_A09_compliance_percentage_calculation(self):
        result = self.engine.check_compliance(_full_egvs_data(), GovernmentStandard.EGVS)
        d = result.to_dict()
        assert d["compliance_percentage"] == 100.0

    def test_A10_compliance_certificate_generated(self):
        result = self.engine.check_compliance(_full_egvs_data(), GovernmentStandard.EGVS)
        cert = self.engine.get_compliance_certificate("prop_001", GovernmentStandard.EGVS, result)
        assert "COMPLIANCE CERTIFICATE" in cert
        assert "EGVS" in cert
        assert "prop_001" in cert

    def test_A11_check_all_standards_returns_all(self):
        results = self.engine.check_all_standards({"property_id": "multi"})
        for std in GovernmentStandard:
            assert std.value in results

    def test_A12_unknown_standard_returns_exempt(self):
        # IFRS16 has no rules → EXEMPT
        result = self.engine.check_compliance({"property_id": "x"}, GovernmentStandard.IFRS16)
        assert result.compliance_level == ComplianceLevel.EXEMPT


# ===========================================================================
# B. TaxCalculator
# ===========================================================================

class TestTaxCalculator:

    def setup_method(self):
        self.calc = TaxCalculator()

    def test_B01_residential_property_tax_rate(self):
        result = self.calc.calculate_tax_valuation(
            "res_001", 1_000_000, TaxClassification.RESIDENTIAL
        )
        assert result.annual_tax == pytest.approx(1_000_000 * 0.005)

    def test_B02_commercial_property_tax_rate(self):
        result = self.calc.calculate_tax_valuation(
            "com_001", 2_000_000, TaxClassification.COMMERCIAL
        )
        assert result.annual_tax == pytest.approx(2_000_000 * 0.015)

    def test_B03_industrial_property_tax_rate(self):
        result = self.calc.calculate_tax_valuation(
            "ind_001", 500_000, TaxClassification.INDUSTRIAL
        )
        assert result.annual_tax == pytest.approx(500_000 * 0.010)

    def test_B04_agricultural_property_tax_rate(self):
        result = self.calc.calculate_tax_valuation(
            "agr_001", 300_000, TaxClassification.AGRICULTURAL
        )
        assert result.annual_tax == pytest.approx(300_000 * 0.003)

    def test_B05_vacant_land_tax_rate(self):
        result = self.calc.calculate_tax_valuation(
            "land_001", 800_000, TaxClassification.VACANT_LAND
        )
        assert result.annual_tax == pytest.approx(800_000 * 0.008)

    def test_B06_capital_gains_tax_applies_under_5_years(self):
        result = self.calc.calculate_tax_valuation(
            "cgt_001", 1_500_000, TaxClassification.COMMERCIAL,
            purchase_price=1_000_000, years_held=3
        )
        assert result.capital_gains_tax_applicable is True
        expected_cgt = (1_500_000 - 1_000_000) * 0.25
        assert result.estimated_capital_gains_tax == pytest.approx(expected_cgt)

    def test_B07_capital_gains_tax_exempt_at_5_years(self):
        result = self.calc.calculate_tax_valuation(
            "cgt_002", 1_500_000, TaxClassification.COMMERCIAL,
            purchase_price=1_000_000, years_held=5
        )
        assert result.capital_gains_tax_applicable is False
        assert result.estimated_capital_gains_tax == 0.0

    def test_B08_no_capital_gains_without_purchase_price(self):
        result = self.calc.calculate_tax_valuation(
            "cgt_003", 1_000_000, TaxClassification.RESIDENTIAL
        )
        assert result.capital_gains_tax_applicable is False
        assert result.estimated_capital_gains_tax == 0.0

    def test_B09_no_cgt_when_no_gain(self):
        result = self.calc.calculate_tax_valuation(
            "cgt_004", 800_000, TaxClassification.COMMERCIAL,
            purchase_price=1_000_000, years_held=2
        )
        assert result.capital_gains_tax_applicable is True
        assert result.estimated_capital_gains_tax == 0.0  # no gain, no tax

    def test_B10_to_dict_has_all_keys(self):
        result = self.calc.calculate_tax_valuation(
            "dict_001", 500_000, TaxClassification.MIXED_USE
        )
        d = result.to_dict()
        for key in (
            "property_id", "tax_classification", "assessed_value",
            "tax_rate", "annual_tax", "capital_gains_tax_applicable",
            "estimated_capital_gains_tax", "property_tax_rate",
            "total_estimated_tax", "calculated_at",
        ):
            assert key in d, f"Missing key: {key}"

    def test_B11_tax_report_contains_required_sections(self):
        result = self.calc.calculate_tax_valuation(
            "rep_001", 1_000_000, TaxClassification.COMMERCIAL
        )
        report = self.calc.get_tax_report(result)
        assert "TAX VALUATION REPORT" in report
        assert "COMMERCIAL" in report
        assert "annual_tax" in report.lower() or "Annual Property Tax" in report


# ===========================================================================
# C. FormsGenerator
# ===========================================================================

class TestFormsGenerator:

    def setup_method(self):
        self.gen = FormsGenerator()
        self.property_data = {
            "property_id": "PROP-001",
            "address": "5 Garden City, Cairo",
            "city": "Cairo",
            "area_sqm": 250,
            "property_type": "residential",
            "loan_amount": 1_200_000,
        }
        self.valuation_result = {
            "primary_value": 1_800_000,
            "method": "Comparative",
            "confidence": "High",
            "valuation_date": "2026-05-09",
        }
        self.appraiser_info = {
            "name": "Mohamed Hassan",
            "license": "EGY-LIC-001",
            "cbe_approved": "Yes",
        }

    def test_C01_cbe_form_101_contains_header(self):
        form = self.gen.generate_cbe_form_101(
            self.property_data, self.valuation_result, self.appraiser_info
        )
        assert "CBE 101" in form

    def test_C02_cbe_form_101_contains_property_address(self):
        form = self.gen.generate_cbe_form_101(
            self.property_data, self.valuation_result, self.appraiser_info
        )
        assert "Garden City" in form

    def test_C03_cbe_form_101_contains_valuation_value(self):
        form = self.gen.generate_cbe_form_101(
            self.property_data, self.valuation_result, self.appraiser_info
        )
        assert "1,800,000" in form

    def test_C04_cbe_form_101_contains_ltv_ratio(self):
        form = self.gen.generate_cbe_form_101(
            self.property_data, self.valuation_result, self.appraiser_info
        )
        assert "LTV" in form
        assert "66.7%" in form  # 1.2M / 1.8M

    def test_C05_tax_form_50_contains_header(self):
        tax_result = {
            "tax_classification": "residential",
            "assessed_value": 1_800_000,
            "annual_tax": 9_000,
            "estimated_capital_gains_tax": 0,
            "total_estimated_tax": 9_000,
            "calculated_at": "2026-05-09",
        }
        form = self.gen.generate_tax_form_50(
            self.property_data, tax_result, {"name": "Ali Kamal", "id_number": "1234"}
        )
        assert "Form 50" in form or "FORM 50" in form

    def test_C06_tax_form_50_contains_taxpayer_name(self):
        tax_result = {
            "tax_classification": "residential",
            "assessed_value": 1_800_000,
            "annual_tax": 9_000,
            "estimated_capital_gains_tax": 0,
            "total_estimated_tax": 9_000,
            "calculated_at": "2026-05-09",
        }
        form = self.gen.generate_tax_form_50(
            self.property_data, tax_result, {"name": "Ali Kamal", "id_number": "1234"}
        )
        assert "Ali Kamal" in form

    def test_C07_egfsa_form_30_contains_header(self):
        vr = {
            "fair_value": 3_000_000,
            "valuation_level": "Level 2",
            "approach": "Market",
            "confidence": "High",
            "hierarchy": "2",
        }
        form = self.gen.generate_egfsa_form_30(
            self.property_data, vr,
            {"name": "Sara Expert", "egfsa_cert": "Yes", "cert_number": "EG-100"}
        )
        assert "EGFSA" in form

    def test_C08_egfsa_form_30_contains_fair_value(self):
        vr = {
            "fair_value": 3_000_000,
            "valuation_level": "Level 2",
            "approach": "Market",
        }
        form = self.gen.generate_egfsa_form_30(
            self.property_data, vr,
            {"name": "Sara Expert", "egfsa_cert": "Yes", "cert_number": "EG-100"}
        )
        assert "3,000,000" in form


# ===========================================================================
# D. GovernmentAuditTrail
# ===========================================================================

class TestGovernmentAuditTrail:

    def setup_method(self):
        self.trail = GovernmentAuditTrail()

    def test_D01_record_entry_returns_audit_entry(self):
        entry = self.trail.record(
            AuditAction.COMPLIANCE_CHECK, "prop_001", "property", actor="user_x"
        )
        assert entry.action == AuditAction.COMPLIANCE_CHECK
        assert entry.entity_id == "prop_001"
        assert entry.actor == "user_x"
        assert entry.success is True

    def test_D02_get_by_entity_returns_relevant_entries(self):
        self.trail.record(AuditAction.COMPLIANCE_CHECK, "prop_A", "property")
        self.trail.record(AuditAction.TAX_CALCULATION, "prop_A", "property")
        self.trail.record(AuditAction.FORM_GENERATED, "prop_B", "property")
        entries = self.trail.get_by_entity("prop_A")
        assert len(entries) == 2
        assert all(e.entity_id == "prop_A" for e in entries)

    def test_D03_get_by_action_filters_correctly(self):
        self.trail.record(AuditAction.TAX_CALCULATION, "x", "property")
        self.trail.record(AuditAction.TAX_CALCULATION, "y", "property")
        self.trail.record(AuditAction.FORM_GENERATED, "z", "property")
        results = self.trail.get_by_action(AuditAction.TAX_CALCULATION)
        assert all(e.action == AuditAction.TAX_CALCULATION for e in results)
        assert len(results) == 2

    def test_D04_to_dict_has_required_keys(self):
        entry = self.trail.record(AuditAction.FORM_GENERATED, "form_001", "form")
        d = entry.to_dict()
        for key in ("entry_id", "action", "entity_id", "entity_type", "actor",
                    "details", "timestamp", "success", "error_message"):
            assert key in d

    def test_D05_failed_entry_recorded(self):
        entry = self.trail.record(
            AuditAction.SIGNATURE_APPLIED, "doc_x", "document",
            success=False, error_message="Key not found"
        )
        assert entry.success is False
        assert entry.error_message == "Key not found"

    def test_D06_count_tracks_entries(self):
        trail = GovernmentAuditTrail()
        assert trail.count() == 0
        trail.record(AuditAction.COMPLIANCE_CHECK, "p1", "property")
        trail.record(AuditAction.TAX_CALCULATION, "p2", "property")
        assert trail.count() == 2


# ===========================================================================
# E. DigitalSignatureManager
# ===========================================================================

class TestDigitalSignatureManager:

    @pytest.fixture(autouse=True)
    def set_signing_key(self, monkeypatch):
        monkeypatch.setenv("GOVT_SIGNING_KEY", "test-signing-key-for-unit-tests-only")
        self.mgr = DigitalSignatureManager()

    def test_E01_sign_document_returns_signed_document(self):
        doc = self.mgr.sign_document("Hello Government", document_type="cbe_101")
        assert doc.content_hash != ""
        assert doc.signature != ""
        assert doc.document_type == "cbe_101"

    def test_E02_verify_valid_document_passes(self):
        content = "Official valuation: EGP 1,500,000"
        doc = self.mgr.sign_document(content, document_type="tax_50")
        assert self.mgr.verify_document(content, doc) is True

    def test_E03_verify_tampered_document_fails(self):
        content = "Value: EGP 1,500,000"
        doc = self.mgr.sign_document(content, document_type="tax_50")
        tampered = "Value: EGP 1,000,000"  # amount changed
        assert self.mgr.verify_document(tampered, doc) is False

    def test_E04_to_dict_has_all_keys(self):
        doc = self.mgr.sign_document("content", document_type="egfsa_30")
        d = doc.to_dict()
        for key in (
            "document_id", "document_type", "content_hash",
            "signature", "algorithm", "signer_id", "signed_at", "metadata"
        ):
            assert key in d

    def test_E05_sha256_hash_algorithm(self):
        content = "hash only test"
        doc = self.mgr.sign_document(
            content, document_type="registration",
            algorithm=SignatureAlgorithm.SHA256_HASH
        )
        assert doc.algorithm == SignatureAlgorithm.SHA256_HASH
        assert self.mgr.verify_document(content, doc) is True

    def test_E06_sign_valuation_report_dict(self):
        report = {"property_id": "PROP-X", "value": 2_000_000, "date": "2026-05-09"}
        doc = self.mgr.sign_valuation_report(report, signer_id="cbe_system")
        assert doc.document_type == "valuation_report"
        assert doc.metadata.get("property_id") == "PROP-X"
        assert doc.signer_id == "cbe_system"

    def test_E07_missing_signing_key_raises(self, monkeypatch):
        monkeypatch.delenv("GOVT_SIGNING_KEY")
        with pytest.raises(ValueError, match="GOVT_SIGNING_KEY"):
            DigitalSignatureManager()


# ===========================================================================
# F. GovernmentPortalManager
# ===========================================================================

class TestGovernmentPortalManager:

    def setup_method(self):
        self.mgr = GovernmentPortalManager()

    def test_F01_create_portal_returns_portal(self):
        portal = self.mgr.create_portal("CBE", "Ahmed Ali", "ahmed@cbe.gov.eg")
        assert portal.agency_name == "CBE"
        assert portal.contact_person == "Ahmed Ali"
        assert portal.agency_id != ""

    def test_F02_get_portal_statistics_returns_summary(self):
        portal = self.mgr.create_portal("Tax Auth", "Sara", "sara@tax.gov.eg")
        stats = self.mgr.get_portal_statistics(portal.agency_id)
        assert stats["agency"] == "Tax Auth"
        assert "statistics" in stats

    def test_F03_dashboard_summary_has_required_keys(self):
        portal = self.mgr.create_portal("EGFSA", "Khaled", "k@egfsa.gov.eg")
        summary = portal.get_dashboard_summary()
        for key in ("agency", "agency_id", "contact", "email", "statistics", "features_available"):
            assert key in summary

    def test_F04_non_existent_portal_returns_empty_dict(self):
        result = self.mgr.get_portal_statistics("nonexistent-id-000")
        assert result == {}

    def test_F05_activity_recording_updates_counters(self):
        portal = self.mgr.create_portal("Ministry", "Hassan", "h@mof.gov.eg")
        self.mgr.record_activity(portal.agency_id, "compliance")
        self.mgr.record_activity(portal.agency_id, "tax")
        self.mgr.record_activity(portal.agency_id, "form")
        stats = self.mgr.get_portal_statistics(portal.agency_id)
        assert stats["statistics"]["compliance_checks"] == 1
        assert stats["statistics"]["tax_calculations"] == 1
        assert stats["statistics"]["forms_generated"] == 1

    def test_F06_count_reflects_registered_portals(self):
        mgr = GovernmentPortalManager()
        assert mgr.count() == 0
        mgr.create_portal("Agency1", "P1", "p1@gov.eg")
        mgr.create_portal("Agency2", "P2", "p2@gov.eg")
        assert mgr.count() == 2
