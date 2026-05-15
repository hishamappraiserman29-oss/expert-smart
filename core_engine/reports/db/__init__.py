"""
reports.db — SQLite persistence layer for valuation reports (Phase 7c).

Built across Waves 7c.1 → 7c.3:
  - 7c.1 + Amendment: schema, models, migrations  (foundation)
  - 7c.2: repository                              (CRUD)
  - 7c.3: db_engine                               (public API)

Independent of the legacy project `database/` package.

Public API:
    from core_engine.reports.db import (
        save_report, get_report, list_reports,
        update_report, delete_report, count_reports,
        ReportRecord,
    )
"""

from .db_engine import (
    DEFAULT_DB_PATH,
    count_reports,
    delete_report,
    get_report,
    list_reports,
    save_report,
    update_report,
)
from .migrations import migrate
from .models import ReportRecord
from .schema import SCHEMA_VERSION

__all__ = [
    "save_report",
    "get_report",
    "list_reports",
    "update_report",
    "delete_report",
    "count_reports",
    "ReportRecord",
    "DEFAULT_DB_PATH",
    "SCHEMA_VERSION",
    "migrate",
]
