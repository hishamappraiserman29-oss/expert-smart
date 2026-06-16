"""
Engine Dispatcher — Phase 16.7.

Central registry and runner for all Phase 16 specialist valuation engines.

Design contract:
  • STANDALONE — never imported by bridge_api.py, valuation_logic.py,
    avm_dispatcher.py, or any /api/* route.
  • ADDITIVE    — zero modification to existing behaviour; old flow is default.
  • COMPATIBILITY MODE — all existing /api/valuation endpoints continue to
    use their current code path untouched. This dispatcher is an opt-in layer.
  • NO SIDE EFFECTS — does not mutate caller inputs; returns new objects only.
  • SAFE FALLBACK — unsupported method key returns a structured warning dict,
    never raises KeyError or AttributeError.

Public API:
    list_engines()                    -> list[str]
    is_supported(key)                 -> bool
    resolve_engine(key)               -> ValuationEngine | None
    run_engine(key, inputs)           -> EngineResult | dict
    get_engine_metadata(key)          -> dict

Supported method keys (14):
    habu · sales_comparison · cost_approach · income_approach ·
    dcf · residual_land · insurance · mortgage_lending · liquidation ·
    market_rental · ifrs13 · rights · litigation_compensation · esg_remediation
"""

from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .base import EngineResult, ValuationEngine

# ---------------------------------------------------------------------------
# Lazy registry — classes imported on first use to keep startup cost low
# ---------------------------------------------------------------------------

_REGISTRY_FACTORIES: Dict[str, str] = {
    # key                       :  "module.ClassName"
    "habu":                       "core_engine.engines.habu_engine.HABUEngine",
    "sales_comparison":           "core_engine.engines.sales_comparison_engine.SalesComparisonEngine",
    "cost_approach":              "core_engine.engines.cost_approach_engine.CostApproachEngine",
    "income_approach":            "core_engine.engines.income_approach_engine.IncomeApproachEngine",
    "dcf":                        "core_engine.engines.dcf_engine.DCFEngine",
    "residual_land":              "core_engine.engines.residual_land_engine.ResidualLandEngine",
    "insurance":                  "core_engine.engines.insurance_engine.InsuranceEngine",
    "mortgage_lending":           "core_engine.engines.mortgage_lending_engine.MortgageLendingEngine",
    "liquidation":                "core_engine.engines.liquidation_engine.LiquidationEngine",
    "market_rental":              "core_engine.engines.market_rental_engine.MarketRentalEngine",
    "ifrs13":                     "core_engine.engines.ifrs13_engine.IFRS13Engine",
    "rights":                     "core_engine.engines.rights_engine.RightsEngine",
    "litigation_compensation":    "core_engine.engines.litigation_compensation_engine.LitigationCompensationEngine",
    "esg_remediation":            "core_engine.engines.esg_remediation_engine.ESGRemediationEngine",
}

# Cache of instantiated engines (one singleton per key — engines are stateless)
_INSTANCE_CACHE: Dict[str, "ValuationEngine"] = {}


def _import_engine(dotted: str) -> type:
    """Import a class given 'package.module.ClassName'."""
    module_path, _, class_name = dotted.rpartition(".")
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_engines() -> list[str]:
    """Return sorted list of all registered method keys."""
    return sorted(_REGISTRY_FACTORIES.keys())


def is_supported(key: str) -> bool:
    """Return True if *key* maps to a registered engine."""
    return (key or "").strip() in _REGISTRY_FACTORIES


def resolve_engine(key: str) -> Optional["ValuationEngine"]:
    """
    Return the singleton engine instance for *key*, or None if unsupported.

    Engines are instantiated once and cached; subsequent calls are O(1) dict
    lookups. Returns None (never raises) for unknown keys.
    """
    k = (key or "").strip()
    if k not in _REGISTRY_FACTORIES:
        return None
    if k not in _INSTANCE_CACHE:
        cls = _import_engine(_REGISTRY_FACTORIES[k])
        _INSTANCE_CACHE[k] = cls()
    return _INSTANCE_CACHE[k]


def run_engine(key: str, inputs: Dict[str, Any]) -> Any:
    """
    Run the engine registered under *key* with *inputs*.

    Returns:
        EngineResult  — if the key is supported (delegates to engine.calculate)
        dict          — structured warning dict if the key is unsupported:
            {
                "supported": False,
                "engine_key": <key>,
                "warning":    "<human-readable explanation>",
                "available_engines": [<sorted list>],
            }

    Never raises for unknown keys — caller should inspect result type or
    check result.get("supported") == False.
    """
    engine = resolve_engine(key)
    if engine is None:
        return {
            "supported":         False,
            "engine_key":        key,
            "warning": (
                f"No engine registered for method key '{key}'. "
                "The existing /api/valuation flow is unaffected. "
                "Use list_engines() to see available keys."
            ),
            "available_engines": list_engines(),
        }
    return engine.calculate(inputs)


def get_engine_metadata(key: str) -> Dict[str, Any]:
    """
    Return metadata dict for a registered engine, or a not-found dict.

    Metadata: engine_key, engine_name, version, class, supported.
    """
    engine = resolve_engine(key)
    if engine is None:
        return {
            "supported":   False,
            "engine_key":  key,
        }
    return {
        "supported":   True,
        "engine_key":  key,
        "engine_name": engine.name,
        "version":     engine.version,
        "class":       type(engine).__name__,
    }
