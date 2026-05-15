"""
sync_engine.py — Bi-directional Sync Manager (Phase 40)

Schedules and executes connector synchronisations.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .connector_base import BaseConnector

logger = logging.getLogger(__name__)


class SyncEngine:
    """Register connectors and run scheduled synchronisations."""

    def __init__(self) -> None:
        self.connectors: Dict[str, BaseConnector] = {}
        self.sync_schedule: Dict[str, datetime] = {}
        self.sync_results: Dict[str, List[Dict[str, Any]]] = {}
        logger.info("SyncEngine initialized")

    def register_connector(self, connector: BaseConnector) -> None:
        cid = connector.config.connector_id
        self.connectors[cid] = connector
        self.sync_results[cid] = []
        self._schedule_next(cid)
        logger.info("Connector registered: %s", cid)

    def _schedule_next(self, connector_id: str) -> None:
        if connector_id not in self.connectors:
            return
        interval = self.connectors[connector_id].config.sync_interval
        self.sync_schedule[connector_id] = datetime.utcnow() + timedelta(seconds=interval)

    def sync_connector(self, connector_id: str) -> bool:
        if connector_id not in self.connectors:
            logger.error("Connector not found: %s", connector_id)
            return False
        connector = self.connectors[connector_id]
        if not connector.config.enabled:
            logger.info("Connector disabled: %s", connector_id)
            return False
        try:
            result = connector.sync()
            self.sync_results[connector_id].append(result.to_dict())
            if len(self.sync_results[connector_id]) > 100:
                self.sync_results[connector_id] = self.sync_results[connector_id][-100:]
            self._schedule_next(connector_id)
            return result.is_success
        except Exception as exc:
            logger.error("sync_connector error: %s", exc)
            return False

    def sync_all(self) -> Dict[str, bool]:
        now = datetime.utcnow()
        results: Dict[str, bool] = {}
        for cid, next_sync in list(self.sync_schedule.items()):
            if now >= next_sync:
                results[cid] = self.sync_connector(cid)
        return results

    def get_sync_statistics(self) -> Dict[str, Any]:
        total = len(self.connectors)
        active = sum(1 for c in self.connectors.values() if c.config.enabled)
        total_syncs = sum(len(r) for r in self.sync_results.values())
        successful = sum(
            sum(1 for r in rlist if r.get("is_success", False))
            for rlist in self.sync_results.values()
        )
        return {
            "total_connectors": total,
            "active_connectors": active,
            "total_syncs": total_syncs,
            "successful_syncs": successful,
            "success_rate": round(successful / total_syncs * 100, 2) if total_syncs > 0 else 0.0,
        }


sync_engine = SyncEngine()
