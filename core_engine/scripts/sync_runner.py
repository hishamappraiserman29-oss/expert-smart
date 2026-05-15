"""
sync_runner.py — Scheduled Sync Runner (Phase 40)

Runs connector synchronisations and webhook deliveries on a schedule.
schedule library is optional — falls back to a simple sleep loop.
"""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

try:
    import schedule as _schedule
    _SCHEDULE_OK = True
except ImportError:
    _schedule = None  # type: ignore[assignment]
    _SCHEDULE_OK = False
    logger.info("schedule library not available — using simple loop")


class SyncRunner:
    """Orchestrate periodic connector sync and webhook delivery."""

    def __init__(self, check_interval: int = 60) -> None:
        self.check_interval = check_interval
        logger.info("SyncRunner initialized (interval=%ds, schedule=%s)", check_interval, _SCHEDULE_OK)

    def run_sync_job(self) -> None:
        try:
            from integrations.sync_engine import sync_engine
            results = sync_engine.sync_all()
            logger.info("Sync job results: %s", results)
        except Exception as exc:
            logger.error("Sync job error: %s", exc)

    def run_webhook_job(self) -> None:
        try:
            from integrations.webhook_manager import webhook_manager
            wh_count = len(webhook_manager.webhooks)
            logger.info("Webhook job: %d registered webhooks", wh_count)
        except Exception as exc:
            logger.error("Webhook job error: %s", exc)

    def start_scheduler(self) -> None:  # pragma: no cover
        if _SCHEDULE_OK and _schedule is not None:
            _schedule.every(5).minutes.do(self.run_sync_job)
            _schedule.every(1).minutes.do(self.run_webhook_job)
            logger.info("Scheduler started (using schedule library)")
            while True:
                _schedule.run_pending()
                time.sleep(self.check_interval)
        else:
            logger.info("Scheduler started (simple loop)")
            tick = 0
            while True:
                tick += 1
                if tick % 5 == 0:
                    self.run_sync_job()
                self.run_webhook_job()
                time.sleep(60)


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    SyncRunner().start_scheduler()
