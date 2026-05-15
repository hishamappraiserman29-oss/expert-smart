"""
sensitivity_matrix.py — Phase 24 Sensitivity Matrix
Two-variable sensitivity analysis producing a grid of property values
across a range of percentage changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class SensitivityResult:
    """
    Result of a two-variable sensitivity analysis.

    Attributes
    ----------
    var1_name   : label for row axis
    var2_name   : label for column axis
    var1_values : % change values for rows
    var2_values : % change values for columns
    matrix      : values[row_idx][col_idx]
    base_value  : unshocked reference value
    """

    var1_name:   str
    var2_name:   str
    var1_values: List[float]
    var2_values: List[float]
    matrix:      List[List[float]]
    base_value:  float

    def get_value(self, row: int, col: int) -> float:
        """Retrieve a single cell by row and column index."""
        return self.matrix[row][col]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "var1_name":   self.var1_name,
            "var2_name":   self.var2_name,
            "var1_values": self.var1_values,
            "var2_values": self.var2_values,
            "matrix":      [[round(v, 2) for v in row] for row in self.matrix],
            "base_value":  round(self.base_value, 2),
        }


class SensitivityMatrix:
    """
    Two-variable sensitivity analysis.

    Usage::
        sm = SensitivityMatrix(base_value=3_000_000)
        result = sm.analyze(
            var1_name="cap_rate",     var1_changes=[-20, -10, 0, 10, 20],
            var2_name="market_growth", var2_changes=[-15, 0, 15],
        )
    """

    def __init__(self, base_value: float) -> None:
        self.base_value = base_value

    def analyze(
        self,
        var1_name:    str,
        var1_changes: List[float],   # row axis — % changes
        var2_name:    str,
        var2_changes: List[float],   # col axis — % changes
        value_fn:     Optional[Callable[[float, float, float], float]] = None,
    ) -> SensitivityResult:
        """
        Build the sensitivity matrix.

        Parameters
        ----------
        var1_changes : row axis percentage changes (e.g. [-20, -10, 0, 10, 20])
        var2_changes : column axis percentage changes
        value_fn     : optional custom function(base, delta1_pct, delta2_pct) → value.
                       Defaults to multiplicative compound adjustment.
        """
        fn = value_fn or self._default_fn

        matrix: List[List[float]] = []
        for d1 in var1_changes:
            row: List[float] = []
            for d2 in var2_changes:
                row.append(fn(self.base_value, d1, d2))
            matrix.append(row)

        return SensitivityResult(
            var1_name=var1_name,
            var2_name=var2_name,
            var1_values=list(var1_changes),
            var2_values=list(var2_changes),
            matrix=matrix,
            base_value=self.base_value,
        )

    # -- Private --------------------------------------------------------------

    @staticmethod
    def _default_fn(base: float, delta1: float, delta2: float) -> float:
        """Multiplicative compound: base × (1 + d1/100) × (1 + d2/100)."""
        return base * (1.0 + delta1 / 100.0) * (1.0 + delta2 / 100.0)
