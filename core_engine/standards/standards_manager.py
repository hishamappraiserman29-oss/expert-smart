"""
standards_manager.py — Multi-framework standards support.

Supported frameworks: EGVS, IVSC, USPAP, IFRS13, CBE.
All are REPORTING / DISCLOSURE frameworks — none change valuation calculations.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class StandardsFramework(str, Enum):
    EGVS = "egvs"       # Egyptian General Valuation Standards
    IVSC = "ivsc"       # International Valuation Standards
    USPAP = "uspap"     # US Uniform Standards of Professional Appraisal Practice
    IFRS13 = "ifrs13"   # IFRS 13 Fair Value Measurement
    CBE = "cbe"         # Central Bank of Egypt guidelines


class StandardsManager:
    """Manage standards framework selection and compatibility."""

    def __init__(self) -> None:
        self.supported_frameworks: Dict[StandardsFramework, Dict[str, Any]] = {
            StandardsFramework.EGVS: {
                "name": "Egyptian General Valuation Standards",
                "description": "Standards for property valuation in Egypt",
                "applies_to": ["all"],
                "calculation_impact": False,
                "report_sections": ["valuation_approach", "market_analysis"],
            },
            StandardsFramework.IVSC: {
                "name": "International Valuation Standards",
                "description": "International standards for property valuation",
                "applies_to": ["all"],
                "calculation_impact": False,
                "report_sections": ["valuation_approach", "market_analysis", "basis_of_value"],
            },
            StandardsFramework.USPAP: {
                "name": "Uniform Standards of Professional Appraisal Practice",
                "description": (
                    "US professional appraisal standards "
                    "(optional disclosure framework)"
                ),
                "applies_to": ["individual_appraisals"],
                "calculation_impact": False,
                "report_sections": [
                    "intended_use",
                    "intended_user",
                    "scope_of_work",
                    "property_identification",
                    "assumptions",
                    "competency",
                    "certification",
                ],
                "note": (
                    "USPAP is a reporting/disclosure framework only. "
                    "Does not change valuations."
                ),
            },
            StandardsFramework.IFRS13: {
                "name": "IFRS 13 Fair Value Measurement",
                "description": "Fair value accounting standards",
                "applies_to": ["portfolio", "financial_reporting"],
                "calculation_impact": False,
                "report_sections": ["fair_value_hierarchy", "valuation_techniques"],
            },
            StandardsFramework.CBE: {
                "name": "Central Bank of Egypt Guidelines",
                "description": "CBE requirements for financial institution valuations",
                "applies_to": ["bank_lending", "financial_institutions"],
                "calculation_impact": False,
                "report_sections": ["loan_to_value", "lending_policy_compliance"],
            },
        }

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def get_applicable_frameworks(self, valuation_type: str) -> List[StandardsFramework]:
        """Return frameworks applicable to *valuation_type*."""
        return [
            fw for fw, cfg in self.supported_frameworks.items()
            if "all" in cfg["applies_to"] or valuation_type in cfg["applies_to"]
        ]

    def get_framework_requirements(self, framework: StandardsFramework) -> Dict[str, Any]:
        """Return the configuration dict for *framework*."""
        return self.supported_frameworks.get(framework, {})

    def list_frameworks(self) -> Dict[str, Dict[str, Any]]:
        """Return all frameworks as a plain dict (string keys for JSON serialisation)."""
        return {fw.value: cfg for fw, cfg in self.supported_frameworks.items()}

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_framework_combination(
        self, frameworks: List[StandardsFramework]
    ) -> Tuple[bool, List[str]]:
        """
        Check that the selected set of frameworks is compatible.

        Returns:
            (is_valid, warnings)
        """
        warnings: List[str] = []

        if StandardsFramework.USPAP in frameworks:
            warnings.append(
                "USPAP is a reporting framework. Does not change valuations."
            )

        if (
            StandardsFramework.IFRS13 in frameworks
            and StandardsFramework.EGVS in frameworks
        ):
            warnings.append(
                "IFRS13 and EGVS have different valuation approaches. "
                "Ensure consistency."
            )

        return True, warnings


standards_manager = StandardsManager()
