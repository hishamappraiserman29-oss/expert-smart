"""Forward-only migration runner for the reports SQLite schema."""

from __future__ import annotations

import sqlite3

from .schema import CREATE_TABLES_SQL, SCHEMA_VERSION


def current_version(conn: sqlite3.Connection) -> int:
    """Return the schema version recorded in the DB, or 0 if unversioned."""
    try:
        row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
        return int(row[0]) if row else 0
    except sqlite3.OperationalError:
        # Table does not yet exist.
        return 0


def _apply_v1(conn: sqlite3.Connection) -> None:
    """Create all v1 tables/indexes and record version=1."""
    conn.executescript(CREATE_TABLES_SQL)
    # Seed version row only when table is empty.
    if not conn.execute("SELECT 1 FROM schema_version LIMIT 1").fetchone():
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (1,))
    conn.commit()


_MIGRATIONS: dict[int, object] = {
    1: _apply_v1,
}


def migrate(
    conn: sqlite3.Connection,
    *,
    target_version: int | None = None,
) -> int:
    """Run all pending migrations up to *target_version* (default: latest).

    Idempotent — calling twice with the same target is safe.
    Returns the version the database is at after the call.
    """
    target = target_version if target_version is not None else SCHEMA_VERSION
    version = current_version(conn)

    for v in sorted(_MIGRATIONS):
        if v <= version:
            continue
        if v > target:
            break
        fn = _MIGRATIONS[v]
        fn(conn)  # type: ignore[operator]
        version = v

    return version
