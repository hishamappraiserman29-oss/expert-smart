"""
market_intelligence.py — Market Intelligence (Phase 36)

Real-time market trend recording, sentiment analysis, and geographic analytics.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MarketSegment(str, Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    AGRICULTURAL = "agricultural"


@dataclass
class MarketTrend:
    trend_id: str
    segment: MarketSegment
    location: str
    metric_name: str
    current_value: float
    previous_value: float
    trend_direction: str
    trend_percentage: float
    measurement_period: str = "monthly"
    last_updated: datetime = field(default_factory=datetime.utcnow)
    volatility: float = 0.0
    market_sentiment: str = "neutral"
    forecast_direction: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trend_id": self.trend_id,
            "segment": self.segment.value,
            "location": self.location,
            "metric_name": self.metric_name,
            "current_value": round(self.current_value, 2),
            "previous_value": round(self.previous_value, 2),
            "trend_direction": self.trend_direction,
            "trend_percentage": round(self.trend_percentage, 4),
            "market_sentiment": self.market_sentiment,
            "volatility": round(self.volatility, 4),
            "measurement_period": self.measurement_period,
            "last_updated": self.last_updated.isoformat(),
        }


class MarketIntelligence:
    """Market intelligence: trend recording, sentiment, and summaries."""

    def __init__(self) -> None:
        self.trends: Dict[str, MarketTrend] = {}
        self._by_segment: Dict[str, List[str]] = {}
        self._by_location: Dict[str, List[str]] = {}
        self._lock = threading.Lock()
        logger.info("Market Intelligence initialized")

    def record_market_trend(
        self,
        trend_id: str,
        segment: MarketSegment,
        location: str,
        metric_name: str,
        current_value: float,
        previous_value: float,
        measurement_period: str = "monthly",
        volatility: float = 0.0,
    ) -> MarketTrend:
        if previous_value > 0:
            pct = (current_value - previous_value) / previous_value * 100
        else:
            pct = 0.0

        if pct > 2:
            direction = "up"
        elif pct < -2:
            direction = "down"
        else:
            direction = "stable"

        if direction == "up" and pct > 5:
            sentiment = "bullish"
        elif direction == "down" and pct < -5:
            sentiment = "bearish"
        else:
            sentiment = "neutral"

        trend = MarketTrend(
            trend_id=trend_id,
            segment=segment,
            location=location,
            metric_name=metric_name,
            current_value=current_value,
            previous_value=previous_value,
            trend_direction=direction,
            trend_percentage=pct,
            measurement_period=measurement_period,
            volatility=volatility,
            market_sentiment=sentiment,
        )
        with self._lock:
            self.trends[trend_id] = trend
            self._by_segment.setdefault(segment.value, []).append(trend_id)
            self._by_location.setdefault(location, []).append(trend_id)

        logger.info("Market trend recorded: %s in %s (%.2f%%)", metric_name, location, pct)
        return trend

    def get_trends_by_segment(self, segment: MarketSegment) -> List[MarketTrend]:
        with self._lock:
            ids = list(self._by_segment.get(segment.value, []))
            return [self.trends[tid] for tid in ids if tid in self.trends]

    def get_trends_by_location(self, location: str) -> List[MarketTrend]:
        with self._lock:
            ids = list(self._by_location.get(location, []))
            return [self.trends[tid] for tid in ids if tid in self.trends]

    def get_market_summary(self) -> Dict[str, Any]:
        with self._lock:
            trends = list(self.trends.values())
        if not trends:
            return {"trends_recorded": 0}
        bullish = sum(1 for t in trends if t.market_sentiment == "bullish")
        neutral = sum(1 for t in trends if t.market_sentiment == "neutral")
        bearish = sum(1 for t in trends if t.market_sentiment == "bearish")
        avg_pct = sum(t.trend_percentage for t in trends) / len(trends)
        latest = max(t.last_updated for t in trends)
        return {
            "total_trends": len(trends),
            "market_sentiment": {
                "bullish": bullish, "neutral": neutral, "bearish": bearish,
            },
            "avg_trend_percentage": round(avg_pct, 4),
            "last_updated": latest.isoformat(),
        }

    def get_top_performers(self, limit: int = 5) -> List[MarketTrend]:
        with self._lock:
            trends = list(self.trends.values())
        trends.sort(key=lambda t: t.trend_percentage, reverse=True)
        return trends[:limit]

    def count(self) -> int:
        with self._lock:
            return len(self.trends)


market_intelligence = MarketIntelligence()
