# Backup and Export Tools

CLI utilities for safe SQLite backup and JSON export of saved reports.

## Backup (`tools/backup_reports.py`)

Online SQLite backup — safe to run while the app is serving requests.
Captures the entire DB file: `reports`, `schema_version`, `report_access_log`,
and all indexes.

```bash
python tools/backup_reports.py \
    --source core_engine/reports/db/data/reports.db \
    --dest-dir backups/ \
    --retention-days 30
```

### Cron schedule (recommended)

Daily at 03:00 UTC:

```cron
0 3 * * * cd /path/to/expert_smart && python tools/backup_reports.py --source core_engine/reports/db/data/reports.db --dest-dir /var/backups/expert-smart --retention-days 30
```

### Restore

Backups are full SQLite files — restore by replacing the live DB:

```bash
# 1. Stop the app
# 2. cp /var/backups/expert-smart/reports_20260516T030000Z.db core_engine/reports/db/data/reports.db
# 3. Start the app
```

## JSON Export (`tools/export_reports_json.py`)

For archival, migration, analysis, or admin reports.

```bash
# Export all reports
python tools/export_reports_json.py \
    --db core_engine/reports/db/data/reports.db \
    --out reports_export.json \
    --pretty

# Filter by owner
python tools/export_reports_json.py \
    --db core_engine/reports/db/data/reports.db \
    --out alice_reports.json \
    --owner-user-id alice

# Metadata only (no full DTO)
python tools/export_reports_json.py \
    --db core_engine/reports/db/data/reports.db \
    --out summary.json \
    --exclude-data
```

Arabic content survives unchanged (UTF-8, `ensure_ascii=False`).

## Security note

The export tool does NOT enforce auth — it has direct DB access. Restrict to
operators with DB-level read access. For user-facing exports, build a
dedicated authenticated endpoint (Followup #7c+).

## Production checklist

- [ ] Cron backup scheduled
- [ ] Restore drill performed and verified
- [ ] Backup destination on different disk/host than primary DB
- [ ] Retention policy documented and enforced
- [ ] Export script access restricted to admins
