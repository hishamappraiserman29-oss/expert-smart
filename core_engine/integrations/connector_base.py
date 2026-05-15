"""
connector_base.py — Base Connector Framework (Phase 40)

Foundation for all third-party integrations.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests
    from requests.auth import HTTPBasicAuth
    _REQUESTS_OK = True
except ImportError:
    requests = None  # type: ignore[assignment]
    HTTPBasicAuth = None  # type: ignore[assignment,misc]
    _REQUESTS_OK = False

logger = logging.getLogger(__name__)


class ConnectorType(str, Enum):
    BANKING = "banking"
    ACCOUNTING = "accounting"
    CRM = "crm"
    MLS = "mls"
    ERP = "erp"
    PAYMENT = "payment"
    MARKETPLACE = "marketplace"
    GOVERNMENT = "government"
    ANALYTICS = "analytics"
    COMMUNICATION = "communication"


class SyncDirection(str, Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"
    BIDIRECTIONAL = "bidirectional"


class ConnectorStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class ConnectorConfig:
    connector_id: str
    connector_type: ConnectorType
    name: str
    endpoint_url: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    sync_direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    sync_interval: int = 3600
    enabled: bool = True
    custom_params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connector_id": self.connector_id,
            "connector_type": self.connector_type.value,
            "name": self.name,
            "endpoint_url": self.endpoint_url,
            "sync_direction": self.sync_direction.value,
            "sync_interval": self.sync_interval,
            "enabled": self.enabled,
        }


@dataclass
class SyncResult:
    connector_id: str
    sync_time: datetime
    direction: SyncDirection
    records_synced: int = 0
    records_failed: int = 0
    records_skipped: int = 0
    is_success: bool = True
    error_message: Optional[str] = None
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connector_id": self.connector_id,
            "sync_time": self.sync_time.isoformat(),
            "records_synced": self.records_synced,
            "records_failed": self.records_failed,
            "is_success": self.is_success,
            "duration_seconds": self.duration_seconds,
        }


class BaseConnector(ABC):
    """Abstract base for all external system connectors."""

    def __init__(self, config: ConnectorConfig) -> None:
        self.config = config
        self.session = requests.Session() if _REQUESTS_OK else None
        self.last_sync: Optional[SyncResult] = None
        self.sync_history: List[SyncResult] = []
        self._setup_auth()
        logger.info("Connector initialized: %s", config.name)

    def _setup_auth(self) -> None:
        if self.session is None:
            return
        if self.config.api_key:
            self.session.headers.update({"Authorization": f"Bearer {self.config.api_key}"})
        if self.config.username and self.config.password and HTTPBasicAuth is not None:
            self.session.auth = HTTPBasicAuth(self.config.username, self.config.password)

    @abstractmethod
    def validate_connection(self) -> bool:
        """Return True if the external endpoint is reachable and healthy."""

    @abstractmethod
    def pull_data(self) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Pull records from external system. Returns (records, error_or_None)."""

    @abstractmethod
    def push_data(self, data: List[Dict[str, Any]]) -> Tuple[int, int]:
        """Push records to external system. Returns (synced, failed)."""

    @abstractmethod
    def transform_incoming(self, external_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map external record to internal format."""

    @abstractmethod
    def transform_outgoing(self, internal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map internal record to external format."""

    def sync(self) -> SyncResult:
        start = time.perf_counter()
        result = SyncResult(
            connector_id=self.config.connector_id,
            sync_time=datetime.utcnow(),
            direction=self.config.sync_direction,
        )
        try:
            if not self.validate_connection():
                raise RuntimeError("Connection validation failed")

            if self.config.sync_direction in (SyncDirection.INCOMING, SyncDirection.BIDIRECTIONAL):
                records, error = self.pull_data()
                if error:
                    result.error_message = error
                    result.is_success = False
                else:
                    for rec in records:
                        try:
                            self._save_synced_data(self.transform_incoming(rec))
                            result.records_synced += 1
                        except Exception as exc:
                            logger.error("Transform error: %s", exc)
                            result.records_failed += 1

            if self.config.sync_direction in (SyncDirection.OUTGOING, SyncDirection.BIDIRECTIONAL):
                synced, failed = self.push_data(self._get_unsynced_data())
                result.records_synced += synced
                result.records_failed += failed

        except Exception as exc:
            logger.error("Sync error: %s", exc)
            result.is_success = False
            result.error_message = str(exc)
        finally:
            result.duration_seconds = time.perf_counter() - start
            self.last_sync = result
            self.sync_history.append(result)

        logger.info("Sync finished: %s success=%s", self.config.connector_id, result.is_success)
        return result

    def _save_synced_data(self, data: Dict[str, Any]) -> None:
        pass

    def _get_unsynced_data(self) -> List[Dict[str, Any]]:
        return []

    def get_sync_status(self) -> Dict[str, Any]:
        if not self.last_sync:
            return {"status": "never_synced"}
        return {
            "last_sync": self.last_sync.sync_time.isoformat(),
            "records_synced": self.last_sync.records_synced,
            "records_failed": self.last_sync.records_failed,
            "is_success": self.last_sync.is_success,
            "duration_seconds": self.last_sync.duration_seconds,
        }

    def close(self) -> None:
        if self.session is not None:
            self.session.close()
