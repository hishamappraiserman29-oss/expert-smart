"""reports.db — SQLite persistence layer for valuation reports.

Public surface (Wave 7c.1):
    ReportRecord  — frozen dataclass representing a stored report
    SCHEMA_VERSION — current schema integer
    migrate()     — run pending DB migrations

Wave 7c.2 will add ReportRepository.
Wave 7c.3 will add the top-level save_report / get_report / … helpers.
"""

from .migrations import migrate
from .models import ReportRecord
from .schema import SCHEMA_VERSION

__all__ = [
    "ReportRecord",
    "SCHEMA_VERSION",
    "migrate",
]
