"""
Composite Aggregator — Wave 7A of the Composite Property Architecture.

Receives the list of AdjustedValuation objects (Wave 2 output) and an
optional synergy_adjustment_percent, returns an AggregationResult
containing all five portfolio-level totals.

Formula:
  total_baseline              = sum(av.baseline_value)
  total_adjusted_before_synergy = sum(av.adjusted_value)
  synergy_adjustment_amount   = total_adjusted_before_synergy * pct / 100
  total_adjusted_after_synergy = total_adjusted_before_synergy + synergy_adjustment_amount

Pure module: no Flask, no DB, no side effects.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from adapters.purpose_adapter import AdjustedValuation


class CompositeAggregatorError(ValueError):
    """Raised for invalid aggregation input."""


@dataclass(frozen=True)
class AggregationResult:
    """Immutable portfolio-level aggregation output."""

    total_baseline: float
    total_adjusted_before_synergy: float
    synergy_adjustment_percent: float
    synergy_adjustment_amount: float
    total_adjusted_after_synergy: float


def aggregate(
    adjusted: Sequence[AdjustedValuation],
    *,
    synergy_adjustment_percent: float = 0.0,
) -> AggregationResult:
    """Aggregate per-component AdjustedValuation objects into portfolio totals.

    Args:
        adjusted: Wave 2 output list (PurposeComplianceAdapter.adapt_all()).
        synergy_adjustment_percent: Portfolio synergy as a percentage
            (e.g. 5.0 = +5%, -10.0 = -10%).  Defaults to 0.0 (no synergy).

    Raises:
        CompositeAggregatorError: synergy_adjustment_percent is not a finite
            real number (wrong type, NaN, or Inf).
    """
    if isinstance(synergy_adjustment_percent, bool) or not isinstance(
        synergy_adjustment_percent, (int, float)
    ):
        raise CompositeAggregatorError(
            f"synergy_adjustment_percent must be a real number, "
            f"got {type(synergy_adjustment_percent).__name__}: "
            f"{synergy_adjustment_percent!r}"
        )
    pct = float(synergy_adjustment_percent)
    if not math.isfinite(pct):
        raise CompositeAggregatorError(
            f"synergy_adjustment_percent must be finite, got {pct!r}"
        )

    total_baseline = round(sum(av.baseline_value for av in adjusted), 2)
    total_before   = round(sum(av.adjusted_value  for av in adjusted), 2)
    amount         = round(total_before * pct / 100.0, 2)
    total_after    = round(total_before + amount, 2)

    return AggregationResult(
        total_baseline=total_baseline,
        total_adjusted_before_synergy=total_before,
        synergy_adjustment_percent=pct,
        synergy_adjustment_amount=amount,
        total_adjusted_after_synergy=total_after,
    )
