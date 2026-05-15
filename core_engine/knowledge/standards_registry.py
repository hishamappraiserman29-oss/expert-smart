"""
standards_registry.py — Standards Registry (Phase 35)

Registry for 20+ international and local valuation standards.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Standard:
    standard_id: str
    name: str
    short_name: str
    organization: str
    country: str
    description: str
    version: str
    effective_date: datetime
    applicable_to: List[str]
    jurisdictions: List[str]
    valuation_approaches: List[str]
    disclosure_requirements: List[str]
    key_principles: List[str]
    implementation_level: str
    compliance_level: int
    documentation_url: str = ""
    reference_guide: str = ""
    examples: List[str] = field(default_factory=list)
    is_active: bool = True
    is_updated: bool = False
    update_notes: str = ""
    next_revision_date: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "standard_id": self.standard_id,
            "name": self.name,
            "short_name": self.short_name,
            "organization": self.organization,
            "country": self.country,
            "version": self.version,
            "applicable_to": self.applicable_to,
            "jurisdictions": self.jurisdictions,
            "valuation_approaches": self.valuation_approaches,
            "implementation_level": self.implementation_level,
            "compliance_level": self.compliance_level,
            "is_active": self.is_active,
        }


_STANDARDS_DATA: List[Dict[str, Any]] = [
    dict(
        standard_id="EGVS", name="Egyptian General Valuation Standards",
        short_name="EGVS", organization="Egyptian Appraisers Association",
        country="Egypt",
        description="Standards for property valuation in Egypt",
        version="1.0", effective_date=datetime(2020, 1, 1),
        applicable_to=["residential", "commercial", "industrial", "agricultural"],
        jurisdictions=["Egypt"],
        valuation_approaches=["Comparative", "Cost", "Income"],
        disclosure_requirements=["Market analysis", "Comparable properties", "Assumptions"],
        key_principles=["Independence", "Objectivity", "Professional competence"],
        implementation_level="mandatory", compliance_level=5,
        documentation_url="https://egyptianstandards.org/egvs",
    ),
    dict(
        standard_id="IVSC", name="International Valuation Standards",
        short_name="IVSC", organization="International Valuation Standards Council",
        country="International",
        description="International standards for professional valuation",
        version="2022", effective_date=datetime(2022, 1, 1),
        applicable_to=["all"],
        jurisdictions=["Global", "Egypt", "Saudi Arabia", "UAE"],
        valuation_approaches=["Market Approach", "Cost Approach", "Income Approach"],
        disclosure_requirements=["Scope", "Methodology", "Assumptions", "Limitations"],
        key_principles=["Independence", "Competence", "Transparency"],
        implementation_level="recommended", compliance_level=4,
        documentation_url="https://www.ivsc.org",
    ),
    dict(
        standard_id="USPAP", name="Uniform Standards of Professional Appraisal Practice",
        short_name="USPAP", organization="Appraisal Standards Board",
        country="United States",
        description="Professional appraisal standards in the United States",
        version="2022", effective_date=datetime(2022, 1, 1),
        applicable_to=["all"],
        jurisdictions=["United States", "Canada"],
        valuation_approaches=["Sales Comparison", "Cost", "Income"],
        disclosure_requirements=["Certification", "Workfile documentation"],
        key_principles=["Ethics", "Competence", "Objectivity"],
        implementation_level="mandatory", compliance_level=5,
        documentation_url="https://www.appraisers.org",
    ),
    dict(
        standard_id="IFRS13", name="IFRS 13 Fair Value Measurement",
        short_name="IFRS 13", organization="International Accounting Standards Board",
        country="International",
        description="Fair value measurement for financial reporting",
        version="2013", effective_date=datetime(2013, 1, 1),
        applicable_to=["financial_assets", "investments", "all"],
        jurisdictions=["Global", "Egypt"],
        valuation_approaches=["Market Approach", "Income Approach", "Cost Approach"],
        disclosure_requirements=["Fair value hierarchy", "Sensitivity analysis"],
        key_principles=["3-level valuation hierarchy"],
        implementation_level="mandatory", compliance_level=5,
    ),
    dict(
        standard_id="IFRS16", name="IFRS 16 Lease Accounting",
        short_name="IFRS 16", organization="International Accounting Standards Board",
        country="International",
        description="Lease accounting and disclosure standard",
        version="2016", effective_date=datetime(2019, 1, 1),
        applicable_to=["leases", "commercial", "industrial"],
        jurisdictions=["Global", "Egypt"],
        valuation_approaches=["Income Approach"],
        disclosure_requirements=["Right-of-use assets", "Lease liabilities"],
        key_principles=["Substance over form"],
        implementation_level="mandatory", compliance_level=5,
    ),
    dict(
        standard_id="CBE", name="Central Bank of Egypt Collateral Valuation Standards",
        short_name="CBE", organization="Central Bank of Egypt",
        country="Egypt",
        description="Standards for collateral valuation in bank lending",
        version="1.0", effective_date=datetime(2018, 1, 1),
        applicable_to=["collateral", "mortgage", "residential", "commercial"],
        jurisdictions=["Egypt"],
        valuation_approaches=["Comparative", "Income"],
        disclosure_requirements=["LTV", "Risk assessment", "Market conditions"],
        key_principles=["Conservative valuation", "Collateral quality"],
        implementation_level="mandatory", compliance_level=5,
    ),
    dict(
        standard_id="EGY_TAX", name="Egyptian Tax Authority Valuation Standards",
        short_name="Tax Standards", organization="Egyptian Tax Authority",
        country="Egypt",
        description="Standards for tax valuation and reporting",
        version="2023", effective_date=datetime(2023, 1, 1),
        applicable_to=["all"],
        jurisdictions=["Egypt"],
        valuation_approaches=["Market Approach", "Income Approach"],
        disclosure_requirements=["Tax basis", "Assumptions"],
        key_principles=["Fair market value"],
        implementation_level="mandatory", compliance_level=5,
    ),
    dict(
        standard_id="FRA", name="Financial Regulatory Authority Standards",
        short_name="FRA", organization="Financial Regulatory Authority",
        country="Egypt",
        description="Standards for funds and securities valuation",
        version="2022", effective_date=datetime(2022, 1, 1),
        applicable_to=["funds", "securities", "reits"],
        jurisdictions=["Egypt"],
        valuation_approaches=["Market Approach", "Income Approach", "Cost Approach"],
        disclosure_requirements=["NAV reporting", "IFRS 13 disclosure", "Audit"],
        key_principles=["Investor protection", "Transparency"],
        implementation_level="mandatory", compliance_level=5,
    ),
    dict(
        standard_id="RICS", name="RICS Valuation – Global Standards",
        short_name="RICS Red Book", organization="Royal Institution of Chartered Surveyors",
        country="United Kingdom",
        description="Global valuation standards from RICS",
        version="2022", effective_date=datetime(2022, 1, 1),
        applicable_to=["all"],
        jurisdictions=["Global", "Egypt", "Saudi Arabia", "UAE"],
        valuation_approaches=["Comparative", "Income", "Cost", "Residual"],
        disclosure_requirements=["Scope of work", "Terms of engagement"],
        key_principles=["Independence", "Objectivity"],
        implementation_level="recommended", compliance_level=4,
    ),
    dict(
        standard_id="BASEL3", name="Basel III Collateral Risk Standards",
        short_name="Basel III", organization="Bank for International Settlements",
        country="International",
        description="Risk-weighted asset and collateral standards for banking",
        version="2017", effective_date=datetime(2017, 1, 1),
        applicable_to=["collateral", "mortgage", "commercial"],
        jurisdictions=["Global", "Egypt"],
        valuation_approaches=["Cost Approach", "Comparative"],
        disclosure_requirements=["Risk weights", "LTV ratios"],
        key_principles=["Capital adequacy", "Risk management"],
        implementation_level="mandatory", compliance_level=5,
    ),
    dict(
        standard_id="REIT_STD", name="REIT Valuation Standards",
        short_name="REIT Std", organization="Egyptian Financial Regulatory Authority",
        country="Egypt",
        description="Specific standards for REIT property valuations",
        version="2021", effective_date=datetime(2021, 1, 1),
        applicable_to=["reits", "funds", "commercial", "residential"],
        jurisdictions=["Egypt"],
        valuation_approaches=["Income Approach", "Comparative"],
        disclosure_requirements=["Semi-annual NAV", "Independent valuation"],
        key_principles=["Regular revaluation", "Independence"],
        implementation_level="mandatory", compliance_level=5,
    ),
    dict(
        standard_id="EGFSA", name="EGFSA Valuation Guidelines",
        short_name="EGFSA", organization="Egyptian Financial Supervisory Authority",
        country="Egypt",
        description="Supervisory guidelines for financial asset valuation",
        version="2020", effective_date=datetime(2020, 1, 1),
        applicable_to=["financial_assets", "all"],
        jurisdictions=["Egypt"],
        valuation_approaches=["Market Approach", "Income Approach"],
        disclosure_requirements=["Market disclosure", "Valuation methodology"],
        key_principles=["Consistency", "Transparency"],
        implementation_level="mandatory", compliance_level=4,
    ),
    dict(
        standard_id="TEGoVA", name="European Valuation Standards",
        short_name="EVS", organization="The European Group of Valuers Associations",
        country="Europe",
        description="European valuation standards for cross-border transactions",
        version="2020", effective_date=datetime(2020, 1, 1),
        applicable_to=["all"],
        jurisdictions=["Europe"],
        valuation_approaches=["Comparative", "Income", "Cost"],
        disclosure_requirements=["Market value basis", "Assumptions"],
        key_principles=["Harmonization", "Transparency"],
        implementation_level="recommended", compliance_level=3,
    ),
    dict(
        standard_id="INSURANCE_VAL", name="Insurance Valuation Standards",
        short_name="Ins. Val.", organization="Egyptian Financial Regulatory Authority",
        country="Egypt",
        description="Standards for property valuation for insurance purposes",
        version="2019", effective_date=datetime(2019, 1, 1),
        applicable_to=["all"],
        jurisdictions=["Egypt"],
        valuation_approaches=["Cost Approach"],
        disclosure_requirements=["Replacement cost", "Depreciation schedule"],
        key_principles=["Indemnity", "Replacement cost"],
        implementation_level="mandatory", compliance_level=4,
    ),
    dict(
        standard_id="MORTGAGE_STD", name="Mortgage Valuation Standards",
        short_name="Mortgage Std", organization="Egyptian Mortgage Authority",
        country="Egypt",
        description="Standards for mortgage-backed property valuations",
        version="2020", effective_date=datetime(2020, 1, 1),
        applicable_to=["residential", "mortgage"],
        jurisdictions=["Egypt"],
        valuation_approaches=["Comparative", "Income"],
        disclosure_requirements=["LTV", "Market trend"],
        key_principles=["Prudent lending value"],
        implementation_level="mandatory", compliance_level=5,
    ),
    dict(
        standard_id="PORTFOLIO_VAL", name="Portfolio Valuation Standards",
        short_name="Portfolio Std", organization="CFA Institute",
        country="International",
        description="Standards for valuing real estate portfolios",
        version="2021", effective_date=datetime(2021, 1, 1),
        applicable_to=["funds", "portfolio"],
        jurisdictions=["Global"],
        valuation_approaches=["All approaches"],
        disclosure_requirements=["Weighted average", "Range analysis"],
        key_principles=["Consistency", "Comparability"],
        implementation_level="recommended", compliance_level=3,
    ),
    dict(
        standard_id="GIPS_RE", name="GIPS Real Estate Standards",
        short_name="GIPS RE", organization="CFA Institute",
        country="International",
        description="Global investment performance standards for real estate",
        version="2020", effective_date=datetime(2020, 1, 1),
        applicable_to=["funds", "investments", "reits"],
        jurisdictions=["Global"],
        valuation_approaches=["Market Approach", "Income Approach"],
        disclosure_requirements=["IRR", "TWRR", "Composite definition"],
        key_principles=["Fair representation", "Full disclosure"],
        implementation_level="recommended", compliance_level=3,
    ),
    dict(
        standard_id="FEASIBILITY_STD", name="Feasibility Study Standards",
        short_name="Feasibility Std", organization="Egyptian Appraisers Association",
        country="Egypt",
        description="Standards for real estate feasibility studies",
        version="2021", effective_date=datetime(2021, 1, 1),
        applicable_to=["development", "commercial", "industrial"],
        jurisdictions=["Egypt"],
        valuation_approaches=["Residual", "Income"],
        disclosure_requirements=["Cash flow projections", "Risk analysis"],
        key_principles=["Economic viability", "Risk assessment"],
        implementation_level="recommended", compliance_level=3,
    ),
    dict(
        standard_id="IAAO", name="International Association of Assessing Officers Standards",
        short_name="IAAO", organization="International Association of Assessing Officers",
        country="International",
        description="Mass appraisal and tax assessment standards",
        version="2022", effective_date=datetime(2022, 1, 1),
        applicable_to=["all"],
        jurisdictions=["Global"],
        valuation_approaches=["Mass Appraisal", "Statistical"],
        disclosure_requirements=["COD", "PRD", "PRB ratios"],
        key_principles=["Equity", "Uniformity"],
        implementation_level="recommended", compliance_level=3,
    ),
    dict(
        standard_id="SECURITIZATION_STD", name="Real Estate Securitization Standards",
        short_name="Sec. Std", organization="Egyptian Financial Regulatory Authority",
        country="Egypt",
        description="Standards for real estate securitization valuations",
        version="2022", effective_date=datetime(2022, 1, 1),
        applicable_to=["securitization", "funds", "commercial"],
        jurisdictions=["Egypt"],
        valuation_approaches=["Income Approach", "Market Approach"],
        disclosure_requirements=["Asset quality", "Cash flow analysis"],
        key_principles=["Transparency", "Investor protection"],
        implementation_level="mandatory", compliance_level=5,
    ),
]


class StandardsRegistry:
    """Registry for all valuation standards."""

    def __init__(self) -> None:
        self.standards: Dict[str, Standard] = {}
        self._by_organization: Dict[str, List[str]] = {}
        self._by_country: Dict[str, List[str]] = {}
        self._by_asset_type: Dict[str, List[str]] = {}
        self._initialize_standards()

    def _initialize_standards(self) -> None:
        for data in _STANDARDS_DATA:
            std = Standard(**data)
            self.register_standard(std)
        logger.info("Standards Registry initialized: %d standards", len(self.standards))

    def register_standard(self, standard: Standard) -> None:
        self.standards[standard.standard_id] = standard
        self._by_organization.setdefault(standard.organization, []).append(standard.standard_id)
        for jurisdiction in standard.jurisdictions:
            self._by_country.setdefault(jurisdiction, []).append(standard.standard_id)
        for asset_type in standard.applicable_to:
            self._by_asset_type.setdefault(asset_type, []).append(standard.standard_id)

    def get_standard(self, standard_id: str) -> Optional[Standard]:
        return self.standards.get(standard_id)

    def get_standards_for_asset(self, asset_type: str) -> List[Standard]:
        ids = set(self._by_asset_type.get(asset_type, []))
        ids |= set(self._by_asset_type.get("all", []))
        return [self.standards[sid] for sid in ids if sid in self.standards and self.standards[sid].is_active]

    def get_standards_for_country(self, country: str) -> List[Standard]:
        ids = set(self._by_country.get(country, []))
        ids |= set(self._by_country.get("Global", []))
        return [self.standards[sid] for sid in ids if sid in self.standards and self.standards[sid].is_active]

    def list_all_standards(self, active_only: bool = True) -> List[Standard]:
        standards = list(self.standards.values())
        if active_only:
            standards = [s for s in standards if s.is_active]
        return standards

    def get_compatibility_matrix(self, asset_type: str, country: str) -> Dict[str, Any]:
        asset_stds = {s.standard_id: s for s in self.get_standards_for_asset(asset_type)}
        country_stds = {s.standard_id: s for s in self.get_standards_for_country(country)}
        # Union — both asset-relevant and country-applicable
        applicable_ids = set(asset_stds) & set(country_stds)
        applicable = [self.standards[sid] for sid in applicable_ids if sid in self.standards]
        mandatory = [s.to_dict() for s in applicable if s.implementation_level == "mandatory"]
        recommended = [s.to_dict() for s in applicable if s.implementation_level == "recommended"]
        return {
            "asset_type": asset_type,
            "country": country,
            "applicable_standards": [s.to_dict() for s in applicable],
            "required_standards": mandatory,
            "recommended_standards": recommended,
        }

    def get_by_organization(self, organization: str) -> List[Standard]:
        ids = self._by_organization.get(organization, [])
        return [self.standards[sid] for sid in ids if sid in self.standards]

    def count(self) -> int:
        return len(self.standards)


standards_registry = StandardsRegistry()
