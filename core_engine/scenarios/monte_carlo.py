"""
monte_carlo.py — Phase 24 Monte Carlo Simulation Engine
Pure-Python (no numpy/scipy) stochastic simulation for property valuation
uncertainty quantification.
"""

from __future__ import annotations

import random
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _percentile(data: List[float], p: float) -> float:
    """Linear-interpolation percentile (equivalent to numpy.percentile)."""
    n = len(data)
    if n == 0:
        return 0.0
    sorted_data = sorted(data)
    idx = (p / 100.0) * (n - 1)
    lo  = int(idx)
    hi  = min(lo + 1, n - 1)
    frac = idx - lo
    return sorted_data[lo] * (1.0 - frac) + sorted_data[hi] * frac


def _mean(data: List[float]) -> float:
    return sum(data) / len(data) if data else 0.0


def _std(data: List[float]) -> float:
    if len(data) < 2:
        return 0.0
    m = _mean(data)
    variance = sum((x - m) ** 2 for x in data) / (len(data) - 1)
    return math.sqrt(variance)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class MonteCarloConfig:
    """Configuration for a Monte Carlo run."""

    iterations:       int   = 10_000
    seed:             Optional[int] = None
    confidence_level: float = 0.95   # for confidence interval


@dataclass
class MonteCarloResult:
    """Statistical summary of a Monte Carlo simulation."""

    mean:               float
    std:                float
    p5:                 float
    p25:                float
    p50:                float
    p75:                float
    p95:                float
    iterations:         int
    confidence_interval: Tuple[float, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mean":       round(self.mean, 2),
            "std":        round(self.std, 2),
            "p5":         round(self.p5, 2),
            "p25":        round(self.p25, 2),
            "p50":        round(self.p50, 2),
            "p75":        round(self.p75, 2),
            "p95":        round(self.p95, 2),
            "iterations": self.iterations,
            "confidence_interval": [
                round(self.confidence_interval[0], 2),
                round(self.confidence_interval[1], 2),
            ],
        }


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class MonteCarloEngine:
    """
    Stochastic simulation engine for property valuation.

    Parameters are modelled as independent normal shocks applied
    multiplicatively to the base value::

        simulated_value = base_value * N(1, volatility/100)

    Parameters
    ----------
    config : MonteCarloConfig (defaults apply when None)
    """

    def __init__(self, config: Optional[MonteCarloConfig] = None) -> None:
        self.config = config or MonteCarloConfig()

    def run(
        self,
        base_value:  float,
        volatility:  float,         # annual σ as a % of base_value (e.g. 15 = 15%)
        iterations:  Optional[int] = None,
    ) -> MonteCarloResult:
        """
        Run a single-factor Monte Carlo simulation.

        Parameters
        ----------
        base_value : central value estimate
        volatility : standard deviation as % of base_value
        iterations : override config.iterations if supplied
        """
        n   = iterations or self.config.iterations
        rng = random.Random(self.config.seed)

        if volatility == 0.0:
            samples = [base_value] * n
        else:
            sigma = volatility / 100.0
            samples = [base_value * rng.gauss(1.0, sigma) for _ in range(n)]

        return self._summarise(samples, n)

    def run_with_parameters(
        self,
        base_value:  float,
        parameters:  List[Dict[str, Any]],
        iterations:  Optional[int] = None,
    ) -> MonteCarloResult:
        """
        Multi-factor simulation.

        Each parameter dict must contain:
          ``std_pct`` — standard deviation as % of base_value
          ``weight``  — relative weight (weights are normalised internally)
        """
        n   = iterations or self.config.iterations
        rng = random.Random(self.config.seed)

        total_weight = sum(p.get("weight", 1.0) for p in parameters) or 1.0

        samples: List[float] = []
        for _ in range(n):
            multiplier = 1.0
            for p in parameters:
                std   = p.get("std_pct", 0.0) / 100.0
                w     = p.get("weight", 1.0) / total_weight
                shock = rng.gauss(0.0, std) * w if std else 0.0
                multiplier += shock
            samples.append(base_value * multiplier)

        return self._summarise(samples, n)

    # -- Private --------------------------------------------------------------

    def _summarise(self, samples: List[float], n: int) -> MonteCarloResult:
        m   = _mean(samples)
        s   = _std(samples)
        # Confidence interval (normal approximation)
        z   = 1.96 if self.config.confidence_level >= 0.95 else 1.645
        ci  = (m - z * s / math.sqrt(n), m + z * s / math.sqrt(n))

        return MonteCarloResult(
            mean=m,
            std=s,
            p5=_percentile(samples, 5),
            p25=_percentile(samples, 25),
            p50=_percentile(samples, 50),
            p75=_percentile(samples, 75),
            p95=_percentile(samples, 95),
            iterations=n,
            confidence_interval=ci,
        )
