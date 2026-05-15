"""
test_phase23b_uspap.py — Phase 23B USPAP Compliance Framework Tests

Covers:
  A. USPAPPropertyIdentification (A01–A04)
  B. USPAPAssumptions            (B01–B05)
  C. USPAPCompetencyStatement    (C01–C04)
  D. USPAPCertification          (D01–D03)
  E. USPAPReport                 (E01–E04)
  F. USPAPComplianceChecker      (F01–F08)
  G. USPAPComplianceAddenum      (G01–G04)
  H. StandardsManager            (H01–H08)

KEY INVARIANT: USPAP is a reporting/disclosure framework ONLY.
No standard framework may change valuation calculations.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from standards.uspap import (
    USPAPAssumptions,
    USPAPCertification,
    USPAPCompliance,
    USPAPCompetencyStatement,
    USPAPComplianceAddenum,
    USPAPComplianceChecker,
    USPAPPropertyIdentification,
    USPAPReport,
    USPAPWorkfileNote,
)
from standards.standards_manager import StandardsFramework, StandardsManager


# ===========================================================================
# Helpers
# ===========================================================================

def _full_property() -> USPAPPropertyIdentification:
    return USPAPPropertyIdentification(
        street_address="123 Nile Street",
        city="Cairo",
        state="Cairo Governorate",
        zip_code="11511",
        parcel_id="CAI-0042",
        legal_description="Lot 7, Block 3, Maadi District",
    )


def _full_competency(name: str = "Ahmed Valuer") -> USPAPCompetencyStatement:
    return USPAPCompetencyStatement(
        appraiser_name=name,
        appraiser_license="EGY-LIC-2024",
        appraiser_designation="MAI",
    )


def _full_certification(name: str = "Ahmed Valuer") -> USPAPCertification:
    return USPAPCertification(
        appraiser_name=name,
        certification_date=datetime.utcnow(),
        appraiser_license="EGY-LIC-2024",
        scope_of_work="Desktop Appraisal",
    )


def _full_report(**overrides) -> USPAPReport:
    assumptions = USPAPAssumptions()
    defaults = dict(
        report_type="Desktop",
        intended_user="Mortgage Lender",
        intended_use="Mortgage Lending",
        scope_of_work="Desktop appraisal of subject property",
        effective_date=datetime.utcnow(),
        report_date=datetime.utcnow(),
        property_identification=_full_property(),
        assumptions=assumptions,
        competency=_full_competency(),
        certification=_full_certification(),
        workfile_note=USPAPWorkfileNote(content="Market analysis and comparable sales attached"),
    )
    defaults.update(overrides)
    return USPAPReport(**defaults)


# ===========================================================================
# A. USPAPPropertyIdentification
# ===========================================================================

class TestUSPAPPropertyIdentification:

    def test_A01_to_dict_has_required_keys(self):
        prop = _full_property()
        d = prop.to_dict()
        for key in ("street_address", "city", "state", "zip_code"):
            assert key in d

    def test_A02_optional_fields_default_to_none(self):
        prop = USPAPPropertyIdentification("1 St", "City", "State", "00000")
        assert prop.legal_description is None
        assert prop.parcel_id is None
        assert prop.subdivision is None
        assert prop.county is None

    def test_A03_to_dict_includes_optional_fields(self):
        prop = _full_property()
        d = prop.to_dict()
        assert d["parcel_id"] == "CAI-0042"
        assert d["legal_description"] is not None

    def test_A04_street_address_preserved(self):
        prop = USPAPPropertyIdentification("789 Garden Rd", "Giza", "Giza", "12345")
        assert prop.to_dict()["street_address"] == "789 Garden Rd"


# ===========================================================================
# B. USPAPAssumptions
# ===========================================================================

class TestUSPAPAssumptions:

    def test_B01_defaults_empty(self):
        a = USPAPAssumptions()
        assert a.extraordinary_assumptions == []
        assert a.hypothetical_conditions == []
        assert a.has_extraordinary_assumptions is False
        assert a.has_hypothetical_conditions is False

    def test_B02_add_extraordinary_assumption_sets_flag(self):
        a = USPAPAssumptions()
        a.add_extraordinary_assumption("Zoning change pending")
        assert a.has_extraordinary_assumptions is True
        assert "Zoning change pending" in a.extraordinary_assumptions

    def test_B03_add_hypothetical_condition_sets_flag(self):
        a = USPAPAssumptions()
        a.add_hypothetical_condition("Assume renovation complete")
        assert a.has_hypothetical_conditions is True

    def test_B04_duplicate_assumptions_not_added(self):
        a = USPAPAssumptions()
        a.add_extraordinary_assumption("Same assumption")
        a.add_extraordinary_assumption("Same assumption")
        assert len(a.extraordinary_assumptions) == 1

    def test_B05_to_dict_reflects_state(self):
        a = USPAPAssumptions()
        a.add_extraordinary_assumption("Flood zone")
        d = a.to_dict()
        assert d["has_extraordinary_assumptions"] is True
        assert "Flood zone" in d["extraordinary_assumptions"]


# ===========================================================================
# C. USPAPCompetencyStatement
# ===========================================================================

class TestUSPAPCompetencyStatement:

    def test_C01_get_competency_statement_non_empty(self):
        cs = _full_competency()
        stmt = cs.get_competency_statement()
        assert isinstance(stmt, str) and len(stmt) > 10

    def test_C02_custom_statement_returned_verbatim(self):
        cs = USPAPCompetencyStatement("Name", "LIC", statement="Custom competency text.")
        assert cs.get_competency_statement() == "Custom competency text."

    def test_C03_to_dict_includes_competency_statement(self):
        cs = _full_competency()
        d = cs.to_dict()
        assert "competency_statement" in d
        assert d["appraiser_name"] == "Ahmed Valuer"

    def test_C04_designation_included_in_statement_when_set(self):
        cs = USPAPCompetencyStatement("Name", "LIC", appraiser_designation="MAI")
        stmt = cs.get_competency_statement()
        assert "MAI" in stmt


# ===========================================================================
# D. USPAPCertification
# ===========================================================================

class TestUSPAPCertification:

    def test_D01_get_certification_statement_is_string(self):
        cert = _full_certification()
        stmt = cert.get_certification_statement()
        assert isinstance(stmt, str) and len(stmt) > 50

    def test_D02_certification_includes_uspap_oriented_notice(self):
        cert = _full_certification()
        stmt = cert.get_certification_statement()
        assert "USPAP-Oriented" in stmt

    def test_D03_to_dict_has_required_keys(self):
        cert = _full_certification()
        d = cert.to_dict()
        for key in ("appraiser_name", "certification_date", "appraiser_license", "certification_statement"):
            assert key in d


# ===========================================================================
# E. USPAPReport
# ===========================================================================

class TestUSPAPReport:

    def test_E01_report_creation_succeeds(self):
        report = _full_report()
        assert report.report_type == "Desktop"
        assert report.intended_user == "Mortgage Lender"

    def test_E02_default_compliance_level_is_oriented(self):
        report = _full_report()
        assert report.compliance_level == USPAPCompliance.USPAP_ORIENTED

    def test_E03_to_dict_has_all_sections(self):
        report = _full_report()
        d = report.to_dict()
        for key in (
            "report_type", "intended_user", "intended_use", "scope_of_work",
            "property_identification", "assumptions", "competency",
            "certification", "workfile_note", "compliance_level",
        ):
            assert key in d

    def test_E04_avm_flag_stored_correctly(self):
        report = _full_report(is_avm_valuation=True)
        assert report.is_avm_valuation is True
        assert report.to_dict()["is_avm_valuation"] is True


# ===========================================================================
# F. USPAPComplianceChecker
# ===========================================================================

class TestUSPAPComplianceChecker:

    def test_F01_complete_report_has_no_errors(self):
        report = _full_report()
        warnings, errors = USPAPComplianceChecker.check_compliance(report)
        assert errors == []

    def test_F02_missing_city_is_error(self):
        prop = USPAPPropertyIdentification("123 St", "", "State", "00000")
        report = _full_report(property_identification=prop)
        _, errors = USPAPComplianceChecker.check_compliance(report)
        assert any("city" in e.lower() for e in errors)

    def test_F03_missing_state_is_error(self):
        prop = USPAPPropertyIdentification("123 St", "City", "", "00000")
        report = _full_report(property_identification=prop)
        _, errors = USPAPComplianceChecker.check_compliance(report)
        assert any("state" in e.lower() for e in errors)

    def test_F04_missing_zip_is_error(self):
        prop = USPAPPropertyIdentification("123 St", "City", "State", "")
        report = _full_report(property_identification=prop)
        _, errors = USPAPComplianceChecker.check_compliance(report)
        assert any("zip" in e.lower() for e in errors)

    def test_F05_missing_appraiser_name_is_error(self):
        report = _full_report(
            competency=USPAPCompetencyStatement("", "LIC123"),
        )
        _, errors = USPAPComplianceChecker.check_compliance(report)
        assert any("appraiser name" in e.lower() for e in errors)

    def test_F06_avm_plus_certified_produces_error(self):
        report = _full_report(
            compliance_level=USPAPCompliance.APPRAISER_CERTIFIED,
            is_avm_valuation=True,
        )
        warnings, errors = USPAPComplianceChecker.check_compliance(report)
        assert any("AVM" in e for e in errors)

    def test_F07_mass_appraisal_plus_certified_produces_error(self):
        report = _full_report(
            compliance_level=USPAPCompliance.APPRAISER_CERTIFIED,
            is_mass_appraisal=True,
        )
        _, errors = USPAPComplianceChecker.check_compliance(report)
        assert any("mass" in e.lower() for e in errors)

    def test_F08_avm_oriented_produces_only_warning_not_error(self):
        report = _full_report(
            compliance_level=USPAPCompliance.USPAP_ORIENTED,
            is_avm_valuation=True,
        )
        warnings, errors = USPAPComplianceChecker.check_compliance(report)
        assert not any("AVM" in e for e in errors)
        assert any("AVM" in w for w in warnings)


# ===========================================================================
# G. USPAPComplianceAddenum
# ===========================================================================

class TestUSPAPComplianceAddenum:

    def test_G01_addendum_contains_header(self):
        report = _full_report()
        text = USPAPComplianceAddenum.generate_addendum(report)
        assert "USPAP-ORIENTED COMPLIANCE ADDENDUM" in text

    def test_G02_addendum_contains_property_address(self):
        report = _full_report()
        text = USPAPComplianceAddenum.generate_addendum(report)
        assert "123 Nile Street" in text

    def test_G03_extraordinary_assumptions_appear_in_addendum(self):
        assumptions = USPAPAssumptions()
        assumptions.add_extraordinary_assumption("Zoning change pending approval")
        report = _full_report(assumptions=assumptions)
        text = USPAPComplianceAddenum.generate_addendum(report)
        assert "Zoning change pending approval" in text

    def test_G04_avm_notice_appears_when_flag_set(self):
        report = _full_report(is_avm_valuation=True)
        text = USPAPComplianceAddenum.generate_addendum(report)
        assert "AUTOMATED VALUATION MODEL" in text


# ===========================================================================
# H. StandardsManager
# ===========================================================================

class TestStandardsManager:

    def setup_method(self):
        self.mgr = StandardsManager()

    def test_H01_all_five_frameworks_present(self):
        fw = self.mgr.list_frameworks()
        for key in ("egvs", "ivsc", "uspap", "ifrs13", "cbe"):
            assert key in fw

    def test_H02_no_framework_has_calculation_impact(self):
        for fw, cfg in self.mgr.supported_frameworks.items():
            assert cfg["calculation_impact"] is False, (
                f"{fw.value} must NOT impact calculations"
            )

    def test_H03_uspap_applicable_to_individual_appraisals(self):
        applicable = self.mgr.get_applicable_frameworks("individual_appraisals")
        assert StandardsFramework.USPAP in applicable

    def test_H04_egvs_and_ivsc_applicable_to_all(self):
        applicable = self.mgr.get_applicable_frameworks("any_type")
        assert StandardsFramework.EGVS in applicable
        assert StandardsFramework.IVSC in applicable

    def test_H05_validate_combination_always_valid(self):
        is_valid, _ = self.mgr.validate_framework_combination(
            [StandardsFramework.EGVS, StandardsFramework.IVSC]
        )
        assert is_valid is True

    def test_H06_uspap_in_combo_produces_advisory_warning(self):
        _, warnings = self.mgr.validate_framework_combination(
            [StandardsFramework.USPAP]
        )
        assert any("reporting framework" in w.lower() for w in warnings)

    def test_H07_ifrs13_plus_egvs_produces_consistency_warning(self):
        _, warnings = self.mgr.validate_framework_combination(
            [StandardsFramework.IFRS13, StandardsFramework.EGVS]
        )
        assert any("consistency" in w.lower() for w in warnings)

    def test_H08_get_framework_requirements_returns_config(self):
        cfg = self.mgr.get_framework_requirements(StandardsFramework.USPAP)
        assert cfg["calculation_impact"] is False
        assert "report_sections" in cfg
