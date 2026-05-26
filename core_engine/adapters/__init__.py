# Phase 5 Purpose Adapters
from .base import PurposeAdapter, PurposeResult, Adjustment, ValidationIssue
from .reconciliation import ReconciliationEngine
from .market_value import MarketValueAdapter
from .mortgage import MortgageValueAdapter
from .insurance import InsuranceValueAdapter
from .ifrs_13 import IFRS13FairValueAdapter

# Phase 6 Asset Adapters
from .asset import AssetAdapter, AssetValuationResult
from .residential import ResidentialAdapter
from .commercial import CommercialAdapter
from .land import LandAdapter

__all__ = [
    # Phase 5
    "PurposeAdapter",
    "PurposeResult",
    "Adjustment",
    "ValidationIssue",
    "ReconciliationEngine",
    "MarketValueAdapter",
    "MortgageValueAdapter",
    "InsuranceValueAdapter",
    "IFRS13FairValueAdapter",
    # Phase 6 / 7
    "AssetAdapter",
    "AssetValuationResult",
    "ResidentialAdapter",
    "CommercialAdapter",
    "LandAdapter",
    # Wave 2 — Composite Purpose Adapter
    "PURPOSE_RULES",
    "PurposeComplianceAdapter",
    "PurposeAdapterError",
    "AdjustedValuation",
    # Phase 8A — Single-Property Requirements Matrix
    "SUPPORTED_ASSET_TYPES",
    "SUPPORTED_PURPOSES",
    "SUPPORTED_PURPOSES_BY_ASSET_TYPE",
    "REQUIREMENTS_MATRIX",
    "FieldSpec",
    "ValuationRequirements",
    "RequirementsViolation",
    "get_requirements",
    "list_supported_asset_types",
    "list_supported_purposes",
    "validate_result",
]

# Wave 2 — Composite Property Architecture
from .purpose_adapter import (  # noqa: E402
    PURPOSE_RULES,
    PurposeComplianceAdapter,
    PurposeAdapterError,
    AdjustedValuation,
)

# Phase 8A — Single-Property Requirements Matrix
from .valuation_requirements import (  # noqa: E402
    SUPPORTED_ASSET_TYPES,
    SUPPORTED_PURPOSES,
    SUPPORTED_PURPOSES_BY_ASSET_TYPE,
    REQUIREMENTS_MATRIX,
    FieldSpec,
    ValuationRequirements,
    RequirementsViolation,
    get_requirements,
    list_supported_asset_types,
    list_supported_purposes,
    validate_result,
)
