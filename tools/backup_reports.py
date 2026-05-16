"""
tools/backup_reports.py — Safe SQLite backup for reports.db.

Uses sqlite3.backup() API (online — works while DB is in use).
Captures the entire file: reports + schema_version + report_access_log + indexes.
Includes retention policy.

Usage:
    python tools/backup_reports.py \\
        --source core_engine/reports/db/data/reports.db \\
        --dest-dir backups/ \\
        --retention-days 30
"""
from __future__ import annotations

import argparse
import datetime
import sqlite3
from pathlib import Path


def backup(source: Path, dest_dir: Path) -> Path:
    """Online SQLite backup. Returns path of created backup."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    dest = dest_dir / f"reports_{timestamp}.db"

    src_conn = sqlite3.connect(str(source))
    try:
        dst_conn = sqlite3.connect(str(dest))
        try:
            src_conn.backup(dst_conn)   # online backup API
        finally:
            dst_conn.close()
    finally:
        src_conn.close()
    return dest


def prune(dest_dir: Path, retention_days: int) -> list[Path]:
    """Delete backups older than retention_days. Returns deleted paths."""
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=retention_days)
    deleted = []
    for f in dest_dir.glob("reports_*.db"):
        mtime = datetime.datetime.utcfromtimestamp(f.stat().st_mtime)
        if mtime < cutoff:
            f.unlink()
            deleted.append(f)
    return deleted


def main() -> int:
    p = argparse.ArgumentParser(description="Backup reports.db safely (online).")
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--dest-dir", type=Path, required=True)
    p.add_argument("--retention-days", type=int, default=30)
    args = p.parse_args()

    if not args.source.exists():
        print(f"ERROR: source not found: {args.source}")
        return 1

    created = backup(args.source, args.dest_dir)
    deleted = prune(args.dest_dir, args.retention_days)
    print(f"OK backup: {created}")
    print(f"OK pruned: {len(deleted)} files older than {args.retention_days}d")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
