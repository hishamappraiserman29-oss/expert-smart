"""
forecasting.py — Forecasting Engine (Phase 36)

Rule-based and trend-based market and portfolio forecasting.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean, stdev
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ForecastModel:
    model_id: str
    name: str
    model_type: str
    metric_id: str
    forecast_horizon: int = 30
    confidence_level: float = 0.95
    historical_data_points: int = 0
    last_trained: Optional[datetime] = None
    accuracy_score: float = 0.0
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "name": self.name,
            "model_type": self.model_type,
            "metric_id": self.metric_id,
            "forecast_horizon": self.forecast_horizon,
            "confidence_level": self.confidence_level,
            "historical_data_points": self.historical_data_points,
            "accuracy_score": round(self.accuracy_score, 4),
            "last_trained": self.last_trained.isoformat() if self.last_trained else None,
            "is_active": self.is_active,
        }


@dataclass
class Forecast:
    forecast_id: str
    model_id: str
    metric_id: str
    forecast_date: datetime
    forecasted_values: List[float]
    confidence_intervals: List[Tuple[float, float]]
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "forecast_id": self.forecast_id,
            "model_id": self.model_id,
            "metric_id": self.metric_id,
            "forecast_date": self.forecast_date.isoformat(),
            "forecasted_values": [round(v, 4) for v in self.forecasted_values],
            "confidence_intervals": [
                {"low": round(lo, 4), "high": round(hi, 4)}
                for lo, hi in self.confidence_intervals
            ],
            "horizon_days": len(self.forecasted_values),
            "created_at": self.created_at.isoformat(),
        }


class ForecastingEngine:
    """Forecasting engine with trend-based and linear models."""

    _VALID_MODEL_TYPES = {"linear_regression", "arima", "prophet", "lstm", "ensemble"}

    def __init__(self) -> None:
        self.models: Dict[str, ForecastModel] = {}
        self.forecasts: Dict[str, Forecast] = {}
        self._lock = threading.Lock()
        logger.info("Forecasting Engine initialized")

    def create_forecast_model(
        self,
        model_id: str,
        name: str,
        model_type: str,
        metric_id: str,
        forecast_horizon: int = 30,
        confidence_level: float = 0.95,
    ) -> ForecastModel:
        if model_type not in self._VALID_MODEL_TYPES:
            raise ValueError(f"Unknown model_type: {model_type!r}. "
                             f"Valid: {sorted(self._VALID_MODEL_TYPES)}")
        model = ForecastModel(
            model_id=model_id,
            name=name,
            model_type=model_type,
            metric_id=metric_id,
            forecast_horizon=forecast_horizon,
            confidence_level=confidence_level,
        )
        with self._lock:
            self.models[model_id] = model
        logger.info("Forecast model created: %s (%s)", name, model_type)
        return model

    def train_model(
        self,
        model_id: str,
        historical_data: List[float],
    ) -> bool:
        with self._lock:
            model = self.models.get(model_id)
        if model is None:
            return False
        if len(historical_data) < 2:
            return False

        model.historical_data_points = len(historical_data)
        model.last_trained = datetime.utcnow()

        # Accuracy estimate based on data size and variance
        try:
            cv = stdev(historical_data) / mean(historical_data) if mean(historical_data) != 0 else 1.0
            model.accuracy_score = max(0.5, min(0.99, 1.0 - cv * 0.3))
        except Exception:
            model.accuracy_score = 0.75

        logger.info("Model trained: %s (%.4f accuracy)", model.name, model.accuracy_score)
        return True

    def generate_forecast(
        self,
        model_id: str,
        forecast_id: str,
        seed_value: Optional[float] = None,
    ) -> Optional[Forecast]:
        with self._lock:
            model = self.models.get(model_id)
        if model is None:
            return None

        base = seed_value if seed_value is not None else 100.0
        # Simple linear trend with small random-like drift
        forecasted_values = [round(base * (1 + 0.005 * i), 4) for i in range(model.forecast_horizon)]
        # Confidence band widens with horizon
        confidence_intervals = [
            (round(v * (1 - 0.05 * (i + 1) / model.forecast_horizon), 4),
             round(v * (1 + 0.05 * (i + 1) / model.forecast_horizon), 4))
            for i, v in enumerate(forecasted_values)
        ]

        forecast = Forecast(
            forecast_id=forecast_id,
            model_id=model_id,
            metric_id=model.metric_id,
            forecast_date=datetime.utcnow(),
            forecasted_values=forecasted_values,
            confidence_intervals=confidence_intervals,
        )
        with self._lock:
            self.forecasts[forecast_id] = forecast
        logger.info("Forecast generated: %s (%d days)", forecast_id, model.forecast_horizon)
        return forecast

    def get_forecast_accuracy(self, model_id: str) -> float:
        with self._lock:
            model = self.models.get(model_id)
        return model.accuracy_score if model else 0.0

    def list_active_models(self) -> List[ForecastModel]:
        with self._lock:
            return [m for m in self.models.values() if m.is_active]

    def deactivate_model(self, model_id: str) -> bool:
        with self._lock:
            model = self.models.get(model_id)
        if model is None:
            return False
        model.is_active = False
        return True

    def count_models(self) -> int:
        with self._lock:
            return len(self.models)

    def count_forecasts(self) -> int:
        with self._lock:
            return len(self.forecasts)


forecasting_engine = ForecastingEngine()
