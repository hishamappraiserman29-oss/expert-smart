"""
dashboard_system.py — Dashboard System (Phase 36)

Interactive dashboard management with widgets and sharing.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DashboardType(str, Enum):
    EXECUTIVE = "executive"
    OPERATIONAL = "operational"
    PORTFOLIO = "portfolio"
    PERFORMANCE = "performance"
    COMPLIANCE = "compliance"
    MARKET = "market"
    CUSTOM = "custom"


class WidgetType(str, Enum):
    METRIC_CARD = "metric_card"
    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    PIE_CHART = "pie_chart"
    TABLE = "table"
    HEATMAP = "heatmap"
    MAP = "map"
    GAUGE = "gauge"
    SCORECARD = "scorecard"
    TIMELINE = "timeline"


@dataclass
class DashboardWidget:
    widget_id: str
    widget_type: WidgetType
    title: str
    metric_ids: List[str]
    position_x: int = 0
    position_y: int = 0
    width: int = 4
    height: int = 3
    refresh_interval: int = 300
    is_interactive: bool = True
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "widget_id": self.widget_id,
            "widget_type": self.widget_type.value,
            "title": self.title,
            "metric_ids": self.metric_ids,
            "position": {"x": self.position_x, "y": self.position_y},
            "size": {"width": self.width, "height": self.height},
            "refresh_interval": self.refresh_interval,
            "is_interactive": self.is_interactive,
        }


@dataclass
class Dashboard:
    dashboard_id: str
    name: str
    dashboard_type: DashboardType
    description: str
    owner_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    widgets: List[DashboardWidget] = field(default_factory=list)
    is_shared: bool = False
    shared_with: List[str] = field(default_factory=list)
    auto_refresh: bool = True
    refresh_interval: int = 300
    is_public: bool = False
    is_pinned: bool = False
    tags: List[str] = field(default_factory=list)
    view_count: int = 0
    last_viewed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dashboard_id": self.dashboard_id,
            "name": self.name,
            "dashboard_type": self.dashboard_type.value,
            "description": self.description,
            "owner_id": self.owner_id,
            "widgets_count": len(self.widgets),
            "is_shared": self.is_shared,
            "is_pinned": self.is_pinned,
            "view_count": self.view_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class DashboardSystem:
    """Manage analytics dashboards with widgets and sharing."""

    def __init__(self) -> None:
        self.dashboards: Dict[str, Dashboard] = {}
        self._by_owner: Dict[str, List[str]] = {}
        self._by_type: Dict[str, List[str]] = {}
        self._lock = threading.Lock()
        logger.info("Dashboard System initialized")

    def create_dashboard(
        self,
        dashboard_id: str,
        name: str,
        dashboard_type: DashboardType,
        description: str,
        owner_id: str,
        tags: Optional[List[str]] = None,
    ) -> Dashboard:
        dashboard = Dashboard(
            dashboard_id=dashboard_id,
            name=name,
            dashboard_type=dashboard_type,
            description=description,
            owner_id=owner_id,
            tags=tags or [],
        )
        with self._lock:
            self.dashboards[dashboard_id] = dashboard
            self._by_owner.setdefault(owner_id, []).append(dashboard_id)
            self._by_type.setdefault(dashboard_type.value, []).append(dashboard_id)
        logger.info("Dashboard created: %s", name)
        return dashboard

    def add_widget(self, dashboard_id: str, widget: DashboardWidget) -> bool:
        with self._lock:
            dashboard = self.dashboards.get(dashboard_id)
        if dashboard is None:
            return False
        dashboard.widgets.append(widget)
        dashboard.updated_at = datetime.utcnow()
        return True

    def remove_widget(self, dashboard_id: str, widget_id: str) -> bool:
        with self._lock:
            dashboard = self.dashboards.get(dashboard_id)
        if dashboard is None:
            return False
        before = len(dashboard.widgets)
        dashboard.widgets = [w for w in dashboard.widgets if w.widget_id != widget_id]
        return len(dashboard.widgets) < before

    def get_user_dashboards(self, user_id: str) -> List[Dashboard]:
        with self._lock:
            ids = list(self._by_owner.get(user_id, []))
            return [self.dashboards[did] for did in ids if did in self.dashboards]

    def get_dashboards_by_type(self, dashboard_type: DashboardType) -> List[Dashboard]:
        with self._lock:
            ids = list(self._by_type.get(dashboard_type.value, []))
            return [self.dashboards[did] for did in ids if did in self.dashboards]

    def record_view(self, dashboard_id: str) -> None:
        with self._lock:
            dashboard = self.dashboards.get(dashboard_id)
        if dashboard:
            dashboard.view_count += 1
            dashboard.last_viewed_at = datetime.utcnow()

    def share_dashboard(self, dashboard_id: str, user_ids: List[str]) -> bool:
        with self._lock:
            dashboard = self.dashboards.get(dashboard_id)
        if dashboard is None:
            return False
        for uid in user_ids:
            if uid not in dashboard.shared_with:
                dashboard.shared_with.append(uid)
        dashboard.is_shared = True
        dashboard.updated_at = datetime.utcnow()
        return True

    def pin_dashboard(self, dashboard_id: str) -> bool:
        with self._lock:
            dashboard = self.dashboards.get(dashboard_id)
        if dashboard is None:
            return False
        dashboard.is_pinned = True
        return True

    def get_statistics(self) -> Dict[str, Any]:
        with self._lock:
            dashboards = list(self.dashboards.values())
        by_type: Dict[str, int] = {}
        for d in dashboards:
            by_type[d.dashboard_type.value] = by_type.get(d.dashboard_type.value, 0) + 1
        return {
            "total_dashboards": len(dashboards),
            "shared_dashboards": sum(1 for d in dashboards if d.is_shared),
            "pinned_dashboards": sum(1 for d in dashboards if d.is_pinned),
            "total_widgets": sum(len(d.widgets) for d in dashboards),
            "by_type": by_type,
        }

    def count(self) -> int:
        with self._lock:
            return len(self.dashboards)


dashboard_system = DashboardSystem()
