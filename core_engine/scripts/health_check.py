"""
health_check.py — Platform Health Check Monitor (Phase 39)

Comprehensive health monitoring: API, database, Redis, disk.
All checks return structured dicts and never raise — services may be offline.
"""

from __future__ import annotations

import json
import logging
import shutil
import time
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class HealthCheckMonitor:
    """Monitor health of all SaaS platform components."""

    _VALID_STATUSES = {"healthy", "warning", "critical", "degraded", "error", "unhealthy"}

    def __init__(self, api_url: str = "http://localhost:5000", check_interval: int = 60) -> None:
        self.api_url = api_url
        self.check_interval = check_interval
        self.health_history: List[Dict[str, Any]] = []
        logger.info("Health Check Monitor initialized (interval=%ds)", check_interval)

    # ── individual checks ──────────────────────────────────────────────────────

    def check_api_health(self) -> Dict[str, Any]:
        try:
            import requests
            response = requests.get(f"{self.api_url}/api/health", timeout=5)
            if response.status_code == 200:
                return {
                    "service": "api",
                    "status": "healthy",
                    "response_time": response.elapsed.total_seconds(),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            return {
                "service": "api",
                "status": "unhealthy",
                "status_code": response.status_code,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as exc:
            return {
                "service": "api",
                "status": "error",
                "error": str(exc),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def check_database_health(self) -> Dict[str, Any]:
        try:
            from database.connection import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            conn.close()
            return {"service": "database", "status": "healthy", "timestamp": datetime.utcnow().isoformat()}
        except Exception as exc:
            return {
                "service": "database",
                "status": "error",
                "error": str(exc),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def check_redis_health(self) -> Dict[str, Any]:
        try:
            import redis
            r = redis.Redis(host="localhost", port=6379, db=0, socket_connect_timeout=2)
            r.ping()
            return {"service": "redis", "status": "healthy", "timestamp": datetime.utcnow().isoformat()}
        except Exception as exc:
            return {
                "service": "redis",
                "status": "error",
                "error": str(exc),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def check_disk_space(self) -> Dict[str, Any]:
        try:
            usage = shutil.disk_usage(".")
            used_pct = usage.used / usage.total * 100
            if used_pct < 80:
                status = "healthy"
            elif used_pct < 90:
                status = "warning"
            else:
                status = "critical"
            return {
                "service": "disk",
                "status": status,
                "used_percent": round(used_pct, 2),
                "total_gb": round(usage.total / 1e9, 2),
                "used_gb": round(usage.used / 1e9, 2),
                "free_gb": round(usage.free / 1e9, 2),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as exc:
            return {
                "service": "disk",
                "status": "error",
                "error": str(exc),
                "timestamp": datetime.utcnow().isoformat(),
            }

    # ── composite check ────────────────────────────────────────────────────────

    def run_health_check(self) -> Dict[str, Any]:
        checks = {
            "api": self.check_api_health(),
            "database": self.check_database_health(),
            "redis": self.check_redis_health(),
            "disk": self.check_disk_space(),
        }
        overall = (
            "healthy"
            if all(c["status"] == "healthy" for c in checks.values())
            else "degraded"
        )
        result: Dict[str, Any] = {
            "overall_status": overall,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks,
        }
        self.health_history.append(result)
        return result

    def monitor_continuously(self) -> None:  # pragma: no cover
        logger.info("Starting continuous health monitoring (interval=%ds) …", self.check_interval)
        while True:
            try:
                result = self.run_health_check()
                if result["overall_status"] != "healthy":
                    logger.warning("Health degraded: %s", json.dumps(result))
                else:
                    logger.info("Health check passed")
                time.sleep(self.check_interval)
            except Exception as exc:
                logger.error("Health check error: %s", exc)
                time.sleep(self.check_interval)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    monitor = HealthCheckMonitor()
    print(json.dumps(monitor.run_health_check(), indent=2))
