"""
market_monitoring.py — Market Monitoring & Mark-to-Market

Real-time collateral value tracking, market index updates, and portfolio
alert generation for proactive risk management.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MarketUpdate:
    """A market price index update for a property segment."""

    update_id: str
    segment: str                 # e.g. "cairo_residential", "giza_commercial"
    index_value: float           # current index value (base = 100)
    change_pct: float            # % change from previous period
    source: str
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "update_id": self.update_id,
            "segment": self.segment,
            "index_value": self.index_value,
            "change_pct": round(self.change_pct, 2),
            "source": self.source,
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class PortfolioAlert:
    """An alert raised for a collateral entry based on market movement."""

    alert_id: str
    collateral_id: str
    loan_id: str
    alert_type: str       # "ltv_breach" | "value_decline" | "revaluation_due"
    severity: str         # "low" | "medium" | "high" | "critical"
    message: str
    current_ltv: float
    threshold_ltv: float
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "collateral_id": self.collateral_id,
            "loan_id": self.loan_id,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "message": self.message,
            "current_ltv": round(self.current_ltv, 2),
            "threshold_ltv": self.threshold_ltv,
            "created_at": self.created_at.isoformat(),
            "resolved": self.resolved,
        }


class MarketMonitor:
    """Track market indices and generate portfolio alerts on value movements."""

    # LTV thresholds that trigger alerts (per collateral type)
    _LTV_THRESHOLDS: Dict[str, Dict[str, float]] = {
        "residential_property": {"medium": 75.0, "high": 85.0, "critical": 95.0},
        "commercial_property":  {"medium": 65.0, "high": 75.0, "critical": 85.0},
        "industrial_property":  {"medium": 60.0, "high": 70.0, "critical": 80.0},
        "default":              {"medium": 70.0, "high": 80.0, "critical": 90.0},
    }

    def __init__(self) -> None:
        self._indices: Dict[str, MarketUpdate] = {}
        self._alerts: List[PortfolioAlert] = []
        self._lock = threading.Lock()
        self._alert_counter = 0

    def publish_update(self, update: MarketUpdate) -> None:
        """Store the latest market index update for a segment."""
        with self._lock:
            self._indices[update.segment] = update
        logger.info(
            "Market update [%s]: %.2f (%.2f%%)",
            update.segment, update.index_value, update.change_pct,
        )

    def get_index(self, segment: str) -> Optional[MarketUpdate]:
        with self._lock:
            return self._indices.get(segment)

    def check_collateral(
        self,
        collateral_id: str,
        loan_id: str,
        current_collateral_value: float,
        outstanding_balance: float,
        collateral_type: str = "residential_property",
    ) -> List[PortfolioAlert]:
        """Evaluate a collateral position and raise alerts if LTV thresholds breached."""
        if current_collateral_value <= 0:
            return []

        current_ltv = (outstanding_balance / current_collateral_value) * 100
        thresholds = self._LTV_THRESHOLDS.get(collateral_type, self._LTV_THRESHOLDS["default"])
        new_alerts: List[PortfolioAlert] = []

        if current_ltv >= thresholds["critical"]:
            severity = "critical"
        elif current_ltv >= thresholds["high"]:
            severity = "high"
        elif current_ltv >= thresholds["medium"]:
            severity = "medium"
        else:
            return []

        with self._lock:
            self._alert_counter += 1
            aid = f"ALT-{self._alert_counter:06d}"
        threshold_used = thresholds[severity]
        alert = PortfolioAlert(
            alert_id=aid,
            collateral_id=collateral_id,
            loan_id=loan_id,
            alert_type="ltv_breach",
            severity=severity,
            message=(
                f"LTV {current_ltv:.1f}% breaches {severity} threshold "
                f"{threshold_used:.0f}% for {collateral_type}"
            ),
            current_ltv=current_ltv,
            threshold_ltv=threshold_used,
        )
        with self._lock:
            self._alerts.append(alert)
        new_alerts.append(alert)
        logger.warning(
            "LTV alert [%s] %s: %.1f%% > %.0f%% threshold",
            severity.upper(), collateral_id, current_ltv, threshold_used,
        )
        return new_alerts

    def get_active_alerts(self) -> List[PortfolioAlert]:
        with self._lock:
            return [a for a in self._alerts if not a.resolved]

    def resolve_alert(self, alert_id: str) -> bool:
        with self._lock:
            for a in self._alerts:
                if a.alert_id == alert_id:
                    a.resolved = True
                    return True
        return False

    def alert_count(self) -> int:
        with self._lock:
            return len(self._alerts)


market_monitor = MarketMonitor()
