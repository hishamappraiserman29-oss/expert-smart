"""
feature_engineer.py — Extract and transform features for the AVM.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_TIME_COLS = ["days_old", "month", "quarter", "year", "is_recent"]
_BASE_NUMERIC = [
    "area_sqm", "price_per_sqm",
    "is_small", "is_medium", "is_large",
    "location_avg_price", "location_price_std",
    "type_avg_price",
]


class FeatureEngineer:
    """Engineer features for ML training and inference."""

    def __init__(self) -> None:
        self.feature_names: List[str] = []
        self.categorical_features: List[str] = []
        self.numeric_features: List[str] = []
        self._location_price_map: Dict[str, float] = {}
        self._location_std_map: Dict[str, float] = {}
        self._type_price_map: Dict[str, float] = {}
        self._global_mean_price: float = 0.0

    # ------------------------------------------------------------------
    # Core extraction
    # ------------------------------------------------------------------

    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return a copy of *df* with all engineered columns added.

        First call (training): computes group statistics and learns category set.
        Subsequent calls (test/inference): uses stored statistics and aligns
        one-hot columns to the training category set so feature counts match.
        """
        features = df.copy()
        is_fitted = bool(self.categorical_features)

        # ── Numeric ──────────────────────────────────────────────────
        features["area_sqm"] = pd.to_numeric(features["area_sqm"], errors="coerce")
        features["area_sqm"] = features["area_sqm"].fillna(features["area_sqm"].median())

        features["price_per_sqm"] = features["primary_value"] / features["area_sqm"]
        features["price_per_sqm"] = features["price_per_sqm"].fillna(
            features["price_per_sqm"].median()
        )

        features["is_small"] = (features["area_sqm"] < 100).astype(int)
        features["is_medium"] = (
            (features["area_sqm"] >= 100) & (features["area_sqm"] < 300)
        ).astype(int)
        features["is_large"] = (features["area_sqm"] >= 300).astype(int)

        # ── Location ─────────────────────────────────────────────────
        if not is_fitted:
            self._global_mean_price = float(features["primary_value"].mean())
            self._location_price_map = (
                features.groupby("location")["primary_value"].mean().to_dict()
            )
            self._location_std_map = (
                features.groupby("location")["primary_value"].std().fillna(0).to_dict()
            )
            self._type_price_map = (
                features.groupby("property_type")["primary_value"].mean().to_dict()
            )

        features["location_avg_price"] = (
            features["location"].map(self._location_price_map).fillna(self._global_mean_price)
        )
        features["location_price_std"] = (
            features["location"].map(self._location_std_map).fillna(0.0)
        )

        # ── Property type ─────────────────────────────────────────────
        features["type_avg_price"] = (
            features["property_type"].map(self._type_price_map).fillna(self._global_mean_price)
        )

        # ── Time ──────────────────────────────────────────────────────
        has_time = False
        if "created_at" in features.columns:
            features["created_at"] = pd.to_datetime(features["created_at"], errors="coerce")
            if features["created_at"].notna().any():
                ref = features["created_at"].max()
                features["days_old"] = (ref - features["created_at"]).dt.days.fillna(0)
                features["month"] = features["created_at"].dt.month.fillna(1)
                features["quarter"] = features["created_at"].dt.quarter.fillna(1)
                features["year"] = features["created_at"].dt.year.fillna(2024)
                features["is_recent"] = (features["days_old"] <= 180).astype(int)
                has_time = True

        if not has_time:
            for col in _TIME_COLS:
                features[col] = 0

        # ── One-hot encode property type ──────────────────────────────
        dummies = pd.get_dummies(features["property_type"], prefix="property_type")
        features = pd.concat([features, dummies], axis=1)

        if not is_fitted:
            # Training: learn the full category set
            self.categorical_features = list(dummies.columns)
        else:
            # Inference/test: align to training categories (fill missing with 0)
            for col in self.categorical_features:
                if col not in features.columns:
                    features[col] = 0

        # ── Assemble feature list ─────────────────────────────────────
        numeric_cols = _BASE_NUMERIC + _TIME_COLS
        for col in numeric_cols:
            if col in features.columns:
                features[col] = features[col].fillna(features[col].median())

        self.numeric_features = [c for c in numeric_cols if c in features.columns]
        self.feature_names = self.numeric_features + self.categorical_features

        logger.info(
            "Engineered %d features (%d numeric, %d categorical)",
            len(self.feature_names),
            len(self.numeric_features),
            len(self.categorical_features),
        )
        return features

    # ------------------------------------------------------------------
    # Feature importance helpers
    # ------------------------------------------------------------------

    def get_feature_importance(
        self, feature_importance: Dict[str, float]
    ) -> List[Tuple[str, float]]:
        """Sort feature importance dict descending."""
        return sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)

    def get_top_features(
        self, feature_importance: Dict[str, float], top_n: int = 20
    ) -> List[str]:
        """Return names of top *top_n* important features."""
        return [f for f, _ in self.get_feature_importance(feature_importance)[:top_n]]
