"""
valuation_logic.py  (root-level redirect)
==========================================
The real implementation lives in core_engine/valuation_logic.py.
This file re-exports everything from there so any import from the
project root still resolves correctly.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "core_engine"))
from valuation_logic import *          # noqa: F401, F403
from valuation_logic import (          # explicit re-export for type checkers
    advanced_valuation,
    get_estimated_price,
    calculate_property_valuation,
    hbu_analysis,
    market_approach,
    cost_approach,
    income_approach,
)
