"""SQLite DDL and schema version for the reports persistence layer."""

from __future__ import annotations

SCHEMA_VERSION: int = 2

CREATE_TABLES_SQL: str = """
CREATE TABLE IF NOT EXISTS schema_version (
    id       INTEGER PRIMARY KEY CHECK (id = 1),   -- single-row guarantee
    version  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
    report_id      TEXT PRIMARY KEY,
    profile_key    TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'draft',
    appraiser_name TEXT,
    market_value   REAL,
    owner_user_id  TEXT NOT NULL DEFAULT '__system__',
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL,
    data_json      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reports_profile   ON reports(profile_key);
CREATE INDEX IF NOT EXISTS idx_reports_status    ON reports(status);
CREATE INDEX IF NOT EXISTS idx_reports_appraiser ON reports(appraiser_name);
CREATE INDEX IF NOT EXISTS idx_reports_created   ON reports(created_at);
CREATE INDEX IF NOT EXISTS idx_reports_owner     ON reports(owner_user_id);
"""

VALID_STATUSES: frozenset[str] = frozenset({"draft", "final", "archived"})
