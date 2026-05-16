"""
tools/export_reports_json.py — Export saved reports to JSON.

Useful for archival, analysis, or migration. Admin-only by design
(does not enforce auth — operator decides whom to export).

Usage:
    python tools/export_reports_json.py \\
        --db core_engine/reports/db/data/reports.db \\
        --out reports_export.json \\
        [--profile-key legacy] \\
        [--status final] \\
        [--owner-user-id alice] \\
        [--since 2026-01-01] \\
        [--until 2026-12-31] \\
        [--exclude-data] \\
        [--pretty]
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from datetime import datetime
from pathlib import Path

# Ensure core_engine/ is on sys.path when script is run directly.
# reports/__init__.py uses bare `from reports.X import ...` which requires
# core_engine/ to be on sys.path (not the project root).
_CORE = Path(__file__).resolve().parent.parent / "core_engine"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from reports.db import list_reports  # noqa: E402


def serialize(record, *, exclude_data: bool) -> dict:
    d = dataclasses.asdict(record)
    if exclude_data:
        d.pop("data", None)
    return d


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--profile-key", default=None)
    p.add_argument("--status", default=None)
    p.add_argument("--owner-user-id", default=None,
                   help="Admin filter — export reports owned by this user only")
    p.add_argument("--since", default=None, help="ISO date (YYYY-MM-DD)")
    p.add_argument("--until", default=None, help="ISO date (YYYY-MM-DD)")
    p.add_argument("--exclude-data", action="store_true",
                   help="Export metadata only (no full data DTO)")
    p.add_argument("--pretty", action="store_true")
    args = p.parse_args()

    # paginate for large DBs
    all_records = []
    offset, page = 0, 200
    while True:
        batch = list_reports(
            profile_key=args.profile_key,
            status=args.status,
            owner_user_id=args.owner_user_id,
            limit=page,
            offset=offset,
            db_path=args.db,
        )
        if not batch:
            break
        all_records.extend(batch)
        offset += page

    # post-fetch date filter (DB layer doesn't expose since/until natively)
    def in_range(r):
        if args.since and r.created_at < args.since:
            return False
        if args.until and r.created_at > args.until + "T23:59:59Z":
            return False
        return True

    filtered = [r for r in all_records if in_range(r)]
    payload = {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "filters": {
            "profile_key": args.profile_key,
            "status": args.status,
            "owner_user_id": args.owner_user_id,
            "since": args.since,
            "until": args.until,
            "exclude_data": args.exclude_data,
        },
        "count": len(filtered),
        "records": [serialize(r, exclude_data=args.exclude_data) for r in filtered],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    indent = 2 if args.pretty else None
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=indent),
        encoding="utf-8",
    )
    print(f"OK exported {len(filtered)} records to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
