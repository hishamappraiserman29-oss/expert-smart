# Retention Policy

Periodic maintenance for the reports DB. Run via `tools/apply_retention.py`.

## Default Rules

| Data | Default action | Default threshold |
|---|---|---|
| Reports in `draft` status | → `archived` | > 30 days since last update |
| Reports in `archived` status | DELETE | **Disabled by default** (`--archived-to-delete >= 0` to enable) |
| `report_access_log` rows | DELETE | > 90 days |

## CLI

```bash
# 1. Dry-run (default — shows what would happen, NO changes)
python tools/apply_retention.py --db core_engine/reports/db/data/reports.db

# 2. Apply with default rules
python tools/apply_retention.py --db core_engine/reports/db/data/reports.db --apply

# 3. Custom thresholds
python tools/apply_retention.py --db reports.db --apply \
    --drafts-to-archive 60 \
    --archived-to-delete 365 \
    --audit-to-delete 90

# 4. Disable a rule by passing -1
python tools/apply_retention.py --db reports.db --apply \
    --drafts-to-archive -1
```

## Cron Schedule (recommended)

Weekly on Sundays at 02:00 UTC:

```cron
0 2 * * 0 cd /path/to/expert_smart && python tools/apply_retention.py --db core_engine/reports/db/data/reports.db --apply
```

## Safety

- **Dry-run by default.** Always run without `--apply` first to inspect the plan.
- Archived deletion is **opt-in** (default `-1`). Only enable after you have
  backups and JSON exports for the relevant horizon.
- Each rule is independent: pass `-1` to disable any rule without affecting others.

## Recommended order in production cron

```
1. tools/backup_reports.py                             # safety snapshot first
2. tools/export_reports_json.py --status archived ...  # export to JSON before deletion
3. tools/apply_retention.py --apply                    # then apply retention
```

## What this does NOT cover

- **Compliance-driven minimum retention** — encode in your specific deployment config.
- **Per-user/per-tenant rules** — current implementation is global.
- **Soft-delete / revival** — current `DELETE` is permanent; backups are the only recovery path.
