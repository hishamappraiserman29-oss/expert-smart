"""
avm_predictor.py — Single and batch AVM predictions with confidence intervals.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class AVMPredictor:
    """Produce property valuations from a trained ML model."""

    def __init__(self, model: Any, feature_engineer: Any, scaler: Any = None) -> None:
        self.model = model
        self.feature_engineer = feature_engineer
        self.scaler = scaler
        self.prediction_history: List[Dict] = []

    # ------------------------------------------------------------------
    # Single prediction
    # ------------------------------------------------------------------

    def predict(
        self,
        area_sqm: float,
        location: str,
        property_type: str,
        additional_features: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Return predicted value + 90 % confidence interval."""
        try:
            row: Dict[str, Any] = {
                "area_sqm": area_sqm,
                "location": location,
                "property_type": property_type,
                "primary_value": 0,  # placeholder — needed for feature engineering
                "created_at": pd.Timestamp.now(),
            }
            if additional_features:
                row.update(additional_features)

            df = pd.DataFrame([row])
            engineered = self.feature_engineer.extract_features(df)

            available = [f for f in self.feature_engineer.feature_names if f in engineered.columns]
            X = engineered[available].values.astype(float)

            if self.scaler is not None:
                X = self.scaler.transform(X)

            prediction = float(self.model.predict(X)[0])

            # Per-tree predictions for CI estimation (Random Forest / GB)
            tree_preds: List[float] = []
            if hasattr(self.model, "estimators_"):
                for est in self.model.estimators_:
                    try:
                        tree_preds.append(float(est.predict(X.reshape(1, -1))[0]))
                    except Exception:
                        pass

            if len(tree_preds) >= 2:
                arr = np.array(tree_preds)
                lower_ci = float(np.percentile(arr, 5))
                upper_ci = float(np.percentile(arr, 95))
                std_dev = float(arr.std())
            else:
                # Fallback: ±10 % of prediction
                std_dev = prediction * 0.10
                lower_ci = prediction - 1.645 * std_dev
                upper_ci = prediction + 1.645 * std_dev

            result = {
                "predicted_value": prediction,
                "confidence_interval": {
                    "lower_5": lower_ci,
                    "upper_95": upper_ci,
                    "confidence_level": 0.9,
                },
                "standard_deviation": std_dev,
                "coefficient_of_variation": std_dev / prediction if prediction > 0 else 0.0,
                "method": "avm_ml",
                "timestamp": pd.Timestamp.now().isoformat(),
            }

            self.prediction_history.append(
                {**result, "input": {"area_sqm": area_sqm, "location": location, "property_type": property_type}}
            )
            logger.info("AVM prediction: EGP %.0f ± EGP %.0f", prediction, std_dev)
            return result

        except Exception as exc:
            logger.error("Prediction error: %s", exc)
            return {"error": str(exc), "predicted_value": None}

    # ------------------------------------------------------------------
    # Batch prediction
    # ------------------------------------------------------------------

    def predict_batch(self, properties: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Predict all properties in *properties* list."""
        results = []
        for prop in properties:
            pred = self.predict(
                area_sqm=prop.get("area_sqm", 0),
                location=prop.get("location", ""),
                property_type=prop.get("property_type", ""),
                additional_features=prop.get("additional_features"),
            )
            results.append({"property_id": prop.get("property_id"), "prediction": pred})

        valid = [
            r["prediction"]["predicted_value"]
            for r in results
            if r["prediction"].get("predicted_value") is not None
        ]

        return {
            "predictions": results,
            "batch_statistics": {
                "total_properties": len(properties),
                "successful_predictions": len(valid),
                "failed_predictions": len(properties) - len(valid),
                "average_prediction": float(np.mean(valid)) if valid else 0.0,
                "min_prediction": float(np.min(valid)) if valid else 0.0,
                "max_prediction": float(np.max(valid)) if valid else 0.0,
            },
        }

    # ------------------------------------------------------------------
    # Explainability
    # ------------------------------------------------------------------

    def get_prediction_explanation(
        self,
        area_sqm: float,
        location: str,
        property_type: str,
    ) -> Dict[str, Any]:
        """Return top-10 feature importances for this prediction."""
        if not hasattr(self.model, "feature_importances_"):
            return {"error": "Model does not support feature importance"}

        importance_arr = self.model.feature_importances_
        feature_names = self.feature_engineer.feature_names
        # Align lengths in case feature set differs
        min_len = min(len(feature_names), len(importance_arr))
        fi = dict(zip(feature_names[:min_len], importance_arr[:min_len]))
        sorted_fi = sorted(fi.items(), key=lambda kv: kv[1], reverse=True)

        return {
            "top_features": sorted_fi[:10],
            "feature_count": len(fi),
        }

    def get_history(self) -> List[Dict]:
        """Return list of all predictions made so far."""
        return list(self.prediction_history)
