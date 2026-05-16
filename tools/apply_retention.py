"""
tools/apply_retention.py — Apply retention rules to reports.db.

Dry-run by default. Use --apply to actually execute changes.

Rules:
  - drafts > N days       → status=archived
  - archived > M days     → DELETE  (disabled by default; pass --archived-to-delete >= 0)
  - audit_log rows > P days → DELETE

Usage:
    # Dry run with defaults (shows what would happen — NO changes)
    python tools/apply_retention.py --db core_engine/reports/db/data/reports.db

    # Apply with custom thresholds
    python tools/apply_retention.py --db reports.db --apply \\
        --drafts-to-archive 30 \\
        --archived-to-delete 365 \\
        --audit-to-delete 90

    # Disable a rule by passing -1
    python tools/apply_retention.py --db reports.db --apply \\
        --drafts-to-archive -1
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure core_engine/ is on sys.path when script is run directly.
_CORE = Path(__file__).resolve().parent.parent / "core_engine"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from reports.db import delete_report, list_reports, update_report  # noqa: E402
from audit_log import purge_audit_logs  # noqa: E402


def _cutoff(days: int) -> str:
    """Returns ISO timestamp `days` days before now (UTC)."""
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def archive_old_drafts(db: Path, days: int, *, dry_run: bool) -> list[str]:
    """Drafts with updated_at < cutoff → status='archived'. Returns affected IDs."""
    if days < 0:
        return []
    cutoff = _cutoff(days)
    affected = []
    offset = 0
    while True:
        batch = list_reports(status="draft", limit=200, offset=offset, db_path=db)
        if not batch:
            break
        for r in batch:
            if r.updated_at < cutoff:
                affected.append(r.report_id)
                if not dry_run:
                    update_report(r.report_id, status="archived", db_path=db)
        offset += len(batch)
        if len(batch) < 200:
            break
    return affected


def delete_old_archived(db: Path, days: int, *, dry_run: bool) -> list[str]:
    """Archived with updated_at < cutoff → DELETE. Returns affected IDs."""
    if days < 0:
        return []
    cutoff = _cutoff(days)
    affected = []
    offset = 0
    while True:
        batch = list_reports(status="archived", limit=200, offset=offset, db_path=db)
        if not batch:
            break
        for r in batch:
            if r.updated_at < cutoff:
                affected.append(r.report_id)
                if not dry_run:
                    delete_report(r.report_id, db_path=db)
        offset += len(batch)
        if len(batch) < 200:
            break
    return affected


def count_old_audit(db: Path, cutoff: str) -> int:
    """Count audit rows older than cutoff without deleting."""
    conn = sqlite3.connect(db)
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM report_access_log WHERE created_at < ?",
            (cutoff,),
        ).fetchone()
        return int(row[0])
    finally:
        conn.close()


def purge_old_audit(db: Path, days: int, *, dry_run: bool) -> int:
    """Audit rows older than cutoff → DELETE. Returns count affected."""
    if days < 0:
        return 0
    cutoff = _cutoff(days)
    if dry_run:
        return count_old_audit(db, cutoff)
    return purge_audit_logs(older_than_iso=cutoff, db_path=db)


def main() -> int:
    p = argparse.ArgumentParser(description="Apply retention rules to reports.db.")
    p.add_argument("--db", type=Path, required=True)
    p.add_argument("--apply", action="store_true",
                   help="Actually execute (default: dry-run, no changes)")
    p.add_argument("--drafts-to-archive", type=int, default=30,
                   help="Drafts older than N days → archived (-1 to disable)")
    p.add_argument("--archived-to-delete", type=int, default=-1,
                   help="Archived older than M days → DELETED (-1 disabled by default)")
    p.add_argument("--audit-to-delete", type=int, default=90,
                   help="Audit rows older than P days → DELETED (-1 to disable)")
    args = p.parse_args()

    if not args.db.exists():
        print(f"ERROR: db not found: {args.db}", file=sys.stderr)
        return 1

    dry = not args.apply
    mode = "DRY-RUN" if dry else "APPLY"
    print(f"=== Retention {mode} ===")
    print(f"DB: {args.db}")
    print()

    drafts = archive_old_drafts(args.db, args.drafts_to_archive, dry_run=dry)
    if args.drafts_to_archive < 0:
        print("Drafts archival: DISABLED")
    else:
        print(f"Drafts to archive (> {args.drafts_to_archive}d): {len(drafts)}")
        for rid in drafts[:10]:
            print(f"  - {rid}")
        if len(drafts) > 10:
            print(f"  ... +{len(drafts) - 10} more")
    print()

    archived = delete_old_archived(args.db, args.archived_to_delete, dry_run=dry)
    if args.archived_to_delete < 0:
        print("Archived deletion: DISABLED")
    else:
        print(f"Archived to DELETE (> {args.archived_to_delete}d): {len(archived)}")
        for rid in archived[:10]:
            print(f"  - {rid}")
        if len(archived) > 10:
            print(f"  ... +{len(archived) - 10} more")
    print()

    audit_n = purge_old_audit(args.db, args.audit_to_delete, dry_run=dry)
    if args.audit_to_delete < 0:
        print("Audit purge: DISABLED")
    else:
        print(f"Audit rows to DELETE (> {args.audit_to_delete}d): {audit_n}")
    print()

    if dry:
        print("DRY-RUN — no changes applied. Re-run with --apply to execute.")
    else:
        print("APPLIED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
