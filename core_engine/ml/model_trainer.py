"""
model_trainer.py — Train Random Forest, Gradient Boosting, and (optionally) XGBoost.
XGBoost is optional; falls back gracefully when not installed.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.model_selection import cross_val_score

try:
    import xgboost as xgb  # type: ignore
    _XGBOOST_OK = True
except ImportError:
    _XGBOOST_OK = False

logger = logging.getLogger(__name__)

_DEFAULT_RF_PARAMS: Dict[str, Any] = {
    "n_estimators": 100,
    "max_depth": 15,
    "min_samples_split": 5,
    "min_samples_leaf": 2,
    "random_state": 42,
    "n_jobs": -1,
}

_DEFAULT_GB_PARAMS: Dict[str, Any] = {
    "n_estimators": 100,
    "learning_rate": 0.1,
    "max_depth": 5,
    "min_samples_split": 5,
    "min_samples_leaf": 2,
    "random_state": 42,
}

_DEFAULT_XGB_PARAMS: Dict[str, Any] = {
    "n_estimators": 100,
    "learning_rate": 0.1,
    "max_depth": 5,
    "min_child_weight": 1,
    "random_state": 42,
    "n_jobs": -1,
}


class ModelTrainer:
    """Train and select the best ML model for AVM."""

    def __init__(self) -> None:
        self.models: Dict[str, Any] = {}
        self.best_model: Optional[Any] = None
        self.best_algorithm: str = ""

    # ------------------------------------------------------------------
    # Individual trainers
    # ------------------------------------------------------------------

    def train_random_forest(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        hyperparams: Optional[Dict[str, Any]] = None,
        cv: int = 5,
    ) -> Dict[str, Any]:
        params = hyperparams or _DEFAULT_RF_PARAMS
        logger.info("Training Random Forest (%d estimators)...", params.get("n_estimators", 100))
        model = RandomForestRegressor(**params)
        model.fit(X_train, y_train)
        cv_scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="r2")
        result = self._make_result("random_forest", model, cv_scores, params)
        self.models["random_forest"] = model
        if self.best_model is None:
            self.best_model = model
            self.best_algorithm = "random_forest"
        logger.info("RF CV R² = %.4f ± %.4f", cv_scores.mean(), cv_scores.std())
        return result

    def train_gradient_boosting(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        hyperparams: Optional[Dict[str, Any]] = None,
        cv: int = 5,
    ) -> Dict[str, Any]:
        params = hyperparams or _DEFAULT_GB_PARAMS
        logger.info("Training Gradient Boosting (%d estimators)...", params.get("n_estimators", 100))
        model = GradientBoostingRegressor(**params)
        model.fit(X_train, y_train)
        cv_scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="r2")
        result = self._make_result("gradient_boosting", model, cv_scores, params)
        self.models["gradient_boosting"] = model
        logger.info("GB CV R² = %.4f ± %.4f", cv_scores.mean(), cv_scores.std())
        return result

    def train_xgboost(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        hyperparams: Optional[Dict[str, Any]] = None,
        cv: int = 5,
    ) -> Dict[str, Any]:
        if not _XGBOOST_OK:
            logger.warning("XGBoost not installed — skipping XGBoost training")
            return {"algorithm": "xgboost", "cv_mean": 0.0, "cv_std": 0.0, "skipped": True}
        params = hyperparams or _DEFAULT_XGB_PARAMS
        logger.info("Training XGBoost (%d estimators)...", params.get("n_estimators", 100))
        model = xgb.XGBRegressor(**params)
        model.fit(X_train, y_train)
        cv_scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="r2")
        result = self._make_result("xgboost", model, cv_scores, params)
        self.models["xgboost"] = model
        logger.info("XGB CV R² = %.4f ± %.4f", cv_scores.mean(), cv_scores.std())
        return result

    # ------------------------------------------------------------------
    # Ensemble
    # ------------------------------------------------------------------

    def train_ensemble(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        cv: int = 5,
    ) -> Dict[str, Dict]:
        results: Dict[str, Dict] = {}
        results["random_forest"] = self.train_random_forest(X_train, y_train, cv=cv)
        results["gradient_boosting"] = self.train_gradient_boosting(X_train, y_train, cv=cv)
        if _XGBOOST_OK:
            results["xgboost"] = self.train_xgboost(X_train, y_train, cv=cv)

        # Pick best by CV mean
        best_algo = max(
            [(k, v) for k, v in results.items() if not v.get("skipped")],
            key=lambda kv: kv[1]["cv_mean"],
        )[0]
        self.best_model = self.models[best_algo]
        self.best_algorithm = best_algo
        logger.info(
            "Best model: %s (R² = %.4f)",
            best_algo,
            results[best_algo]["cv_mean"],
        )
        return results

    # ------------------------------------------------------------------
    # Hyperparameter tuning (lightweight grid — avoids long CI runtimes)
    # ------------------------------------------------------------------

    def hyperparameter_tuning(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        cv: int = 3,
    ) -> Dict[str, Any]:
        from sklearn.model_selection import GridSearchCV  # type: ignore

        param_grid = {
            "n_estimators": [50, 100],
            "max_depth": [5, 10],
            "min_samples_split": [2, 5],
        }
        base = RandomForestRegressor(random_state=42, n_jobs=-1)
        gs = GridSearchCV(base, param_grid, cv=cv, scoring="r2", n_jobs=-1)
        gs.fit(X_train, y_train)
        logger.info("Tuning done: best R² = %.4f, params = %s", gs.best_score_, gs.best_params_)
        return {
            "best_params": gs.best_params_,
            "best_score": float(gs.best_score_),
        }

    # ------------------------------------------------------------------
    # Persist
    # ------------------------------------------------------------------

    def save_model(self, model_path: str) -> bool:
        if self.best_model is None:
            logger.error("No best model to save")
            return False
        try:
            joblib.dump(self.best_model, model_path)
            logger.info("Model saved: %s", model_path)
            return True
        except Exception as exc:
            logger.error("Error saving model: %s", exc)
            return False

    def load_model(self, model_path: str) -> bool:
        try:
            self.best_model = joblib.load(model_path)
            logger.info("Model loaded: %s", model_path)
            return True
        except Exception as exc:
            logger.error("Error loading model: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_result(
        algorithm: str,
        model: Any,
        cv_scores: np.ndarray,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "model": model,
            "algorithm": algorithm,
            "cv_mean": float(cv_scores.mean()),
            "cv_std": float(cv_scores.std()),
            "cv_scores": cv_scores.tolist(),
            "hyperparams": params,
        }
