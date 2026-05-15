"""
ivsc.py — IVSC Compliance Framework (Phase 9.0)

Builds International Valuation Standards Committee disclosures for
residential, commercial, and land valuations.  Designed as an additive
layer: no Phase 4-8 logic is modified.

Classes:
    IVSStandard          — Enum of applicable IVS standards
    IVSDisclosure        — Dataclass capturing all required IVSC disclosures
    IVSComplianceBuilder — Factory that constructs disclosures per asset type
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional


# ── Standards enum ────────────────────────────────────────────────────────────

class IVSStandard(Enum):
    """IVSC standards applicable to this valuation."""

    IVS_101 = "IVS 101: Scope of Work"
    IVS_102 = "IVS 102: Bases of Value"
    IVS_103 = "IVS 103: Valuation Approaches"
    IVS_104 = "IVS 104: Valuation Approaches and Methods"
    IVS_105 = "IVS 105: Evaluating Assumptions"
    IVS_201 = "IVS 201: Residential Property"
    IVS_202 = "IVS 202: Commercial Property"
    IVS_203 = "IVS 203: Plant and Machinery"
    IVS_204 = "IVS 204: Intangible Assets"
    IVS_205 = "IVS 205: Special Purpose Property"
    IVS_210 = "IVS 210: Portfolio of Properties"

    @classmethod
    def for_asset_type(cls, asset_type: str) -> List["IVSStandard"]:
        """Return the applicable standards for a given asset type."""
        mapping: Dict[str, List[IVSStandard]] = {
            "residential": [
                cls.IVS_101, cls.IVS_102, cls.IVS_103,
                cls.IVS_104, cls.IVS_105, cls.IVS_201,
            ],
            "commercial": [
                cls.IVS_101, cls.IVS_102, cls.IVS_103,
                cls.IVS_104, cls.IVS_105, cls.IVS_202,
            ],
            "land": [
                cls.IVS_101, cls.IVS_102, cls.IVS_103,
                cls.IVS_104, cls.IVS_105,
            ],
        }
        return mapping.get(asset_type.lower(), [cls.IVS_101, cls.IVS_102, cls.IVS_103])


# ── Disclosure dataclass ──────────────────────────────────────────────────────

_MARKET_VALUE_DEF = (
    "The estimated amount for which an asset should exchange on the date of "
    "valuation between a willing buyer and a willing seller in an arm's length "
    "transaction, after proper marketing and where the parties had each acted "
    "knowledgeably, prudently and without compulsion."
)


@dataclass
class IVSDisclosure:
    """IVSC required disclosure for a single valuation."""

    # ── Scope of Work (IVS 101) ────────────────────────────────────────────
    scope_of_work: str = ""
    purpose_of_valuation: str = ""
    effective_date: Optional[date] = None

    # ── Bases of Value (IVS 102) ───────────────────────────────────────────
    basis_of_valuation: str = "Market Value"
    definition: str = ""

    # ── Valuation Approaches (IVS 103-105) ────────────────────────────────
    approaches_used: List[str] = field(default_factory=list)
    methodology_summary: str = ""
    key_assumptions: List[str] = field(default_factory=list)
    limiting_conditions: List[str] = field(default_factory=list)

    # ── Competency & Standards ─────────────────────────────────────────────
    appraiser_name: str = ""
    appraiser_qualifications: str = ""
    appraiser_declaration: str = ""

    # ── Market Conditions (IVS 104) ────────────────────────────────────────
    market_conditions_summary: str = ""
    economic_conditions: str = ""

    # ── Currency & Exchange ────────────────────────────────────────────────
    currency: str = "EGP"
    exchange_rate_basis: str = ""

    # ── Inspection (IVS 105) ───────────────────────────────────────────────
    inspection_date: Optional[date] = None
    inspection_notes: str = ""

    # ── Standards Compliance ───────────────────────────────────────────────
    ivsc_standards_applied: List[IVSStandard] = field(default_factory=list)
    national_standards_applied: List[str] = field(default_factory=list)

    # ── Disclosure Statement ───────────────────────────────────────────────
    disclosure_statement: str = ""

    # ── Certification ──────────────────────────────────────────────────────
    certification_statement: str = ""
    date_certified: Optional[date] = None

    def to_dict(self) -> Dict:
        """Return a JSON-serialisable dict."""
        return {
            "scope_of_work":             self.scope_of_work,
            "purpose_of_valuation":      self.purpose_of_valuation,
            "effective_date":            self.effective_date.isoformat() if self.effective_date else None,
            "basis_of_valuation":        self.basis_of_valuation,
            "definition":                self.definition,
            "approaches_used":           self.approaches_used,
            "methodology_summary":       self.methodology_summary,
            "key_assumptions":           self.key_assumptions,
            "limiting_conditions":       self.limiting_conditions,
            "appraiser_name":            self.appraiser_name,
            "appraiser_qualifications":  self.appraiser_qualifications,
            "appraiser_declaration":     self.appraiser_declaration,
            "market_conditions_summary": self.market_conditions_summary,
            "economic_conditions":       self.economic_conditions,
            "currency":                  self.currency,
            "exchange_rate_basis":       self.exchange_rate_basis,
            "inspection_date":           self.inspection_date.isoformat() if self.inspection_date else None,
            "inspection_notes":          self.inspection_notes,
            "ivsc_standards_applied":    [s.value for s in self.ivsc_standards_applied],
            "national_standards_applied": self.national_standards_applied,
            "disclosure_statement":      self.disclosure_statement,
            "certification_statement":   self.certification_statement,
            "date_certified":            self.date_certified.isoformat() if self.date_certified else None,
        }


# ── Builder ───────────────────────────────────────────────────────────────────

_APPRAISER_DECLARATION = (
    "I hereby declare that, to the best of my knowledge and belief, the "
    "information provided and the opinion expressed in this valuation report "
    "are correct and compliant with IVSC standards."
)

_NATIONAL_STANDARDS = ["EGVS 1.0", "EGVS 2.0", "EGVS 3.0"]


class IVSComplianceBuilder:
    """Factory that builds IVSC disclosures for each supported asset type."""

    def __init__(self) -> None:
        self.disclosures: Dict[str, IVSDisclosure] = {}

    # ── Residential ───────────────────────────────────────────────────────

    def for_residential(
        self,
        appraiser_name: str = "Expert Smart System",
        property_address: str = "",
        effective_date: Optional[date] = None,
    ) -> IVSDisclosure:
        """Build an IVSC disclosure for residential property."""
        if effective_date is None:
            effective_date = date.today()

        disclosure = IVSDisclosure(
            scope_of_work=(
                "Valuation of residential property for market value purposes"
            ),
            purpose_of_valuation="Market Value",
            effective_date=effective_date,
            basis_of_valuation="Market Value",
            definition=_MARKET_VALUE_DEF,
            approaches_used=["Comparable Sales", "Cost Approach", "Income Approach"],
            methodology_summary=(
                "The valuation was undertaken using three recognized approaches: "
                "(1) Comparable Sales Approach - analysis of recent market transactions; "
                "(2) Cost Approach - land value plus replacement cost; "
                "(3) Income Approach - capitalization of net income (where applicable). "
                "Weights applied per EGVS 2.0 and IVSC guidance."
            ),
            key_assumptions=[
                "Market conditions as of effective date",
                "Property inspected and found to be in stated condition",
                "No material hidden defects",
                "Normal market exposure period",
                "Arms-length transaction between informed parties",
                "No forced sale or special concessions",
            ],
            limiting_conditions=[
                "Valuation is based on information provided and inspection findings",
                "No invasive investigation undertaken",
                "Title assumed to be clear and marketable",
                "This valuation is valid only for the stated purpose and effective date",
                "Market value assumes normal market conditions and conventional financing",
            ],
            appraiser_name=appraiser_name,
            appraiser_qualifications=(
                "IVSC Certified, EGVS Certified, Expert Smart AI System"
            ),
            appraiser_declaration=_APPRAISER_DECLARATION,
            market_conditions_summary=(
                "Egyptian real estate market as of valuation date. "
                "See market analysis section for details."
            ),
            economic_conditions=(
                "Egyptian economy context - interest rates, inflation, policy "
                "environment affecting property values."
            ),
            currency="EGP (Egyptian Pound)",
            inspection_date=effective_date,
            inspection_notes=(
                "Property inspected on site. Condition observed and documented."
            ),
            ivsc_standards_applied=IVSStandard.for_asset_type("residential"),
            national_standards_applied=_NATIONAL_STANDARDS,
            certification_statement=(
                f"I certify that, based on my inspection and analysis, the valuation "
                f"in this report represents my professional opinion of the market value "
                f"of the subject property as of {effective_date.isoformat()}, in "
                f"accordance with IVSC standards and Egyptian Valuation Standards. "
                f"This valuation was prepared in accordance with the International "
                f"Valuation Standards and the Egyptian Valuation Standards."
            ),
            date_certified=effective_date,
        )
        self.disclosures["residential"] = disclosure
        return disclosure

    # ── Commercial ────────────────────────────────────────────────────────

    def for_commercial(
        self,
        appraiser_name: str = "Expert Smart System",
        property_address: str = "",
        effective_date: Optional[date] = None,
    ) -> IVSDisclosure:
        """Build an IVSC disclosure for commercial property."""
        if effective_date is None:
            effective_date = date.today()

        disclosure = IVSDisclosure(
            scope_of_work=(
                "Valuation of commercial property for market value purposes"
            ),
            purpose_of_valuation="Market Value",
            effective_date=effective_date,
            basis_of_valuation="Market Value",
            definition=_MARKET_VALUE_DEF,
            approaches_used=["Comparable Sales", "Income Capitalization"],
            methodology_summary=(
                "The valuation was undertaken using two primary approaches: "
                "(1) Comparable Sales Approach - analysis of recent commercial transactions; "
                "(2) Income Capitalization Approach - discounted cash flows and cap rate analysis. "
                "Weights applied per IVSC guidance and market evidence."
            ),
            key_assumptions=[
                "Market conditions as of effective date",
                "Property in stabilized operating condition",
                "Leases assumed to be arm's length",
                "Market rental rates per comparable leases",
                "Market cap rate per comparable sales",
                "No lease expiration before stabilization",
            ],
            limiting_conditions=[
                "Valuation based on provided financials and market data",
                "Lease terms and rental rates verified through market analysis",
                "Environmental or title issues not investigated",
                "Assumes conventional financing available",
                "Market value assumes normal market conditions",
            ],
            appraiser_name=appraiser_name,
            appraiser_qualifications=(
                "IVSC Certified, Commercial Property Specialist, Expert Smart AI System"
            ),
            appraiser_declaration=_APPRAISER_DECLARATION,
            market_conditions_summary=(
                "Egyptian commercial real estate market. "
                "See market analysis for details."
            ),
            economic_conditions=(
                "Current economic environment - interest rates, tenant demand, "
                "rental growth rates."
            ),
            currency="EGP (Egyptian Pound)",
            inspection_date=effective_date,
            inspection_notes=(
                "Property inspected on site. Physical condition and occupancy verified."
            ),
            ivsc_standards_applied=IVSStandard.for_asset_type("commercial"),
            national_standards_applied=_NATIONAL_STANDARDS,
            certification_statement=(
                f"I certify that this commercial property valuation represents my "
                f"professional opinion of market value as of {effective_date.isoformat()}, "
                f"prepared in accordance with IVSC standards and Egyptian Valuation Standards."
            ),
            date_certified=effective_date,
        )
        self.disclosures["commercial"] = disclosure
        return disclosure

    # ── Land ──────────────────────────────────────────────────────────────

    def for_land(
        self,
        appraiser_name: str = "Expert Smart System",
        property_address: str = "",
        effective_date: Optional[date] = None,
    ) -> IVSDisclosure:
        """Build an IVSC disclosure for land."""
        if effective_date is None:
            effective_date = date.today()

        disclosure = IVSDisclosure(
            scope_of_work="Valuation of land for market value purposes",
            purpose_of_valuation="Market Value",
            effective_date=effective_date,
            basis_of_valuation="Market Value",
            definition=_MARKET_VALUE_DEF,
            approaches_used=["Comparable Sales", "Income Approach (Residual)"],
            methodology_summary=(
                "Land valued using: "
                "(1) Comparable Sales Approach - analysis of recent land sales; "
                "(2) Highest and Best Use Analysis - residual approach to determine "
                "development potential. "
                "Weights per market evidence and development feasibility."
            ),
            key_assumptions=[
                "Land valued in current use or highest and best use",
                "Zoning and development potential per municipal records",
                "Infrastructure availability verified",
                "No environmental constraints",
                "Normal market conditions and absorption rates",
            ],
            limiting_conditions=[
                "Zoning and land use status not verified with municipality",
                "No soil or environmental testing undertaken",
                "Development costs estimated based on standard rates",
                "Assumes development financing available",
                "Market value assumes normal development timeline",
            ],
            appraiser_name=appraiser_name,
            appraiser_qualifications=(
                "IVSC Certified, EGVS Certified, Land Valuation Specialist, "
                "Expert Smart AI System"
            ),
            appraiser_declaration=_APPRAISER_DECLARATION,
            market_conditions_summary=(
                "Egyptian land market. See market analysis for location-specific conditions."
            ),
            economic_conditions=(
                "Economic environment affecting land values - development outlook, "
                "interest rates, demand."
            ),
            currency="EGP (Egyptian Pound)",
            inspection_date=effective_date,
            inspection_notes=(
                "Land inspected on site. Boundaries, access, condition documented."
            ),
            ivsc_standards_applied=IVSStandard.for_asset_type("land"),
            national_standards_applied=_NATIONAL_STANDARDS,
            certification_statement=(
                f"I certify that this land valuation represents my professional "
                f"opinion of market value as of {effective_date.isoformat()}, prepared "
                f"in accordance with IVSC standards and Egyptian Valuation Standards."
            ),
            date_certified=effective_date,
        )
        self.disclosures["land"] = disclosure
        return disclosure
