"""
analytics_engine.py — Analytics Engine (Phase 36)

Real-time data aggregation, metric tracking, and statistical processing.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from statistics import mean, stdev
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    COUNT = "count"
    SUM = "sum"
    AVERAGE = "average"
    PERCENTAGE = "percentage"
    RATE = "rate"
    RATIO = "ratio"
    TREND = "trend"


class TimeGranularity(str, Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


@dataclass
class MetricDataPoint:
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "metadata": self.metadata,
        }


@dataclass
class Metric:
    metric_id: str
    name: str
    metric_type: MetricType
    description: str
    data_points: List[MetricDataPoint] = field(default_factory=list)
    unit: str = ""
    target_value: Optional[float] = None
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None
    is_active: bool = True
    refresh_interval: int = 300
    last_updated: datetime = field(default_factory=datetime.utcnow)

    def current_value(self) -> Optional[float]:
        return self.data_points[-1].value if self.data_points else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "name": self.name,
            "metric_type": self.metric_type.value,
            "current_value": self.current_value(),
            "unit": self.unit,
            "target_value": self.target_value,
            "data_points_count": len(self.data_points),
            "last_updated": self.last_updated.isoformat(),
        }


class AnalyticsEngine:
    """Central analytics engine for metric tracking and aggregation."""

    _MAX_DATA_POINTS = 10_000

    def __init__(self) -> None:
        self.metrics: Dict[str, Metric] = {}
        self._lock = threading.Lock()
        logger.info("Analytics Engine initialized")

    def register_metric(
        self,
        metric_id: str,
        name: str,
        metric_type: MetricType,
        description: str,
        unit: str = "",
        target_value: Optional[float] = None,
    ) -> Metric:
        metric = Metric(
            metric_id=metric_id,
            name=name,
            metric_type=metric_type,
            description=description,
            unit=unit,
            target_value=target_value,
        )
        with self._lock:
            self.metrics[metric_id] = metric
        logger.info("Metric registered: %s", name)
        return metric

    def record_data_point(
        self,
        metric_id: str,
        value: float,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> bool:
        with self._lock:
            metric = self.metrics.get(metric_id)
        if metric is None:
            return False
        dp = MetricDataPoint(
            timestamp=timestamp or datetime.utcnow(),
            value=value,
            metadata=metadata or {},
        )
        metric.data_points.append(dp)
        metric.last_updated = datetime.utcnow()
        if len(metric.data_points) > self._MAX_DATA_POINTS:
            metric.data_points = metric.data_points[-self._MAX_DATA_POINTS:]
        return True

    def get_metric_statistics(self, metric_id: str) -> Dict[str, Any]:
        with self._lock:
            metric = self.metrics.get(metric_id)
        if metric is None:
            return {}
        values = [dp.value for dp in metric.data_points]
        if not values:
            return {"metric_id": metric_id, "name": metric.name, "data_points": 0}

        stats: Dict[str, Any] = {
            "metric_id": metric_id,
            "name": metric.name,
            "count": len(values),
            "current": values[-1],
            "min": min(values),
            "max": max(values),
            "average": mean(values),
            "unit": metric.unit,
        }
        if len(values) > 1:
            stats["stdev"] = stdev(values)
            recent_avg = mean(values[-10:]) if len(values) >= 10 else mean(values)
            stats["trend"] = "increasing" if recent_avg > mean(values) else "decreasing"
        if metric.target_value:
            stats["percent_to_target"] = values[-1] / metric.target_value * 100
        return stats

    def get_time_series(
        self,
        metric_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        granularity: TimeGranularity = TimeGranularity.DAILY,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            metric = self.metrics.get(metric_id)
        if metric is None:
            return []
        now = datetime.utcnow()
        end_time = end_time or now
        start_time = start_time or (now - timedelta(days=30))
        filtered = [dp for dp in metric.data_points if start_time <= dp.timestamp <= end_time]
        return self._aggregate_by_granularity(filtered, granularity)

    def _aggregate_by_granularity(
        self, data_points: List[MetricDataPoint], granularity: TimeGranularity
    ) -> List[Dict[str, Any]]:
        if not data_points:
            return []
        buckets: Dict[str, List[float]] = {}
        for dp in data_points:
            key = self._bucket_key(dp.timestamp, granularity)
            buckets.setdefault(key, []).append(dp.value)
        result = []
        for key in sorted(buckets):
            vals = buckets[key]
            result.append({
                "time": key,
                "value": mean(vals),
                "min": min(vals),
                "max": max(vals),
                "count": len(vals),
            })
        return result

    def _bucket_key(self, ts: datetime, granularity: TimeGranularity) -> str:
        if granularity == TimeGranularity.HOURLY:
            return ts.strftime("%Y-%m-%d %H:00")
        if granularity == TimeGranularity.DAILY:
            return ts.strftime("%Y-%m-%d")
        if granularity == TimeGranularity.WEEKLY:
            return ts.strftime("%Y-W%W")
        if granularity == TimeGranularity.MONTHLY:
            return ts.strftime("%Y-%m")
        if granularity == TimeGranularity.QUARTERLY:
            q = (ts.month - 1) // 3 + 1
            return f"{ts.year}-Q{q}"
        return ts.strftime("%Y")

    def get_all_metrics(self) -> List[Metric]:
        with self._lock:
            return [m for m in self.metrics.values() if m.is_active]

    def get_engine_statistics(self) -> Dict[str, Any]:
        with self._lock:
            metrics = list(self.metrics.values())
        total_dp = sum(len(m.data_points) for m in metrics)
        by_type: Dict[str, int] = {}
        for m in metrics:
            by_type[m.metric_type.value] = by_type.get(m.metric_type.value, 0) + 1
        return {
            "total_metrics": len(metrics),
            "active_metrics": sum(1 for m in metrics if m.is_active),
            "total_data_points": total_dp,
            "metrics_by_type": by_type,
        }

    def count(self) -> int:
        with self._lock:
            return len(self.metrics)


analytics_engine = AnalyticsEngine()
