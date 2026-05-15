"""
model_validator.py — Metrics and validation utilities for the AVM.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

import numpy as np
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    r2_score,
)

logger = logging.getLogger(__name__)


class ModelValidator:
    """Static evaluation helpers — no state required."""

    @staticmethod
    def evaluate(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Any]:
        """Compute comprehensive regression metrics."""
        y_true = np.asarray(y_true, dtype=float)
        y_pred = np.asarray(y_pred, dtype=float)

        mse = mean_squared_error(y_true, y_pred)
        rmse = float(np.sqrt(mse))
        mae = float(mean_absolute_error(y_true, y_pred))
        mape = float(mean_absolute_percentage_error(y_true, y_pred))
        r2 = float(r2_score(y_true, y_pred))

        errors = y_true - y_pred
        error_pct = np.abs(errors / np.where(y_true == 0, 1, y_true) * 100)

        return {
            "mse": float(mse),
            "rmse": rmse,
            "mae": mae,
            "mape": mape,
            "r2": r2,
            "error_distribution": {
                "mean": float(errors.mean()),
                "std": float(errors.std()),
                "min": float(errors.min()),
                "max": float(errors.max()),
                "p5":  float(np.percentile(error_pct, 5)),
                "p25": float(np.percentile(error_pct, 25)),
                "p50": float(np.percentile(error_pct, 50)),
                "p75": float(np.percentile(error_pct, 75)),
                "p95": float(np.percentile(error_pct, 95)),
            },
            "accuracy_within_ranges": {
                "5_percent":  float((error_pct <= 5).sum()  / len(error_pct) * 100),
                "10_percent": float((error_pct <= 10).sum() / len(error_pct) * 100),
                "15_percent": float((error_pct <= 15).sum() / len(error_pct) * 100),
                "20_percent": float((error_pct <= 20).sum() / len(error_pct) * 100),
            },
        }

    @staticmethod
    def validate_by_subgroup(
        df: "pd.DataFrame",  # noqa: F821
        y_true: np.ndarray,
        y_pred: np.ndarray,
        group_column: str,
    ) -> Dict[str, Dict]:
        """Compute metrics separately for each unique value of *group_column*."""
        import pandas as pd  # local import keeps dependency optional at module level

        results: Dict[str, Dict] = {}
        y_true_arr = np.asarray(y_true, dtype=float)
        y_pred_arr = np.asarray(y_pred, dtype=float)
        df = df.reset_index(drop=True)

        for group in df[group_column].unique():
            mask = (df[group_column] == group).values
            if mask.sum() == 0:
                continue
            results[str(group)] = ModelValidator.evaluate(
                y_true_arr[mask], y_pred_arr[mask]
            )
        return results

    @staticmethod
    def check_overfitting(train_score: float, test_score: float, threshold: float = 0.1) -> bool:
        """Return True (and warn) when train/test gap exceeds *threshold*."""
        gap = train_score - test_score
        if gap > threshold:
            logger.warning(
                "Possible overfitting: train R²=%.4f, test R²=%.4f, gap=%.4f",
                train_score,
                test_score,
                gap,
            )
            return True
        return False

    @staticmethod
    def generate_report(metrics: Dict[str, Any]) -> str:
        """Return a human-readable evaluation report string."""
        ed = metrics["error_distribution"]
        ar = metrics["accuracy_within_ranges"]
        return (
            "\n"
            "OVERALL METRICS:\n"
            f"  R² Score:                 {metrics['r2']:.4f}\n"
            f"  Root Mean Squared Error:  EGP {metrics['rmse']:,.0f}\n"
            f"  Mean Absolute Error:      EGP {metrics['mae']:,.0f}\n"
            f"  Mean Absolute % Error:    {metrics['mape']:.2f}%\n"
            "\n"
            "ERROR DISTRIBUTION:\n"
            f"  Mean Error:               EGP {ed['mean']:,.0f}\n"
            f"  Std Deviation:            EGP {ed['std']:,.0f}\n"
            f"  p5 / p50 / p95:           {ed['p5']:.1f}% / {ed['p50']:.1f}% / {ed['p95']:.1f}%\n"
            "\n"
            "PREDICTION ACCURACY:\n"
            f"  Within  5%:              {ar['5_percent']:.1f}%\n"
            f"  Within 10%:              {ar['10_percent']:.1f}%\n"
            f"  Within 15%:              {ar['15_percent']:.1f}%\n"
            f"  Within 20%:              {ar['20_percent']:.1f}%\n"
        )
