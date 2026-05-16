# Audit Log

Records every access to protected `/api/reports*` endpoints for forensics
and compliance (added in auth wave S5).

## Schema (DB v3)

```sql
CREATE TABLE report_access_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT,           -- NULL for unauthenticated requests
    endpoint    TEXT NOT NULL,
    method      TEXT NOT NULL,
    status      INTEGER NOT NULL,
    report_id   TEXT,           -- extracted from URL when applicable
    ip          TEXT,
    created_at  TEXT NOT NULL   -- UTC ISO 8601
);
```

Indexes: `(user_id, created_at)` for per-user forensics, `(created_at)` for
time-range queries.

## Configuration

| Env Var | Default | Purpose |
|---------|---------|---------|
| `AUDIT_ENABLED` | `true` | Set `false` to disable all logging |
| `AUDIT_DB_PATH` | *(see below)* | Override DB path (tests only) |

DB path resolution order:
1. Explicit `db_path` kwarg on `log_access` / `fetch_audit_logs`
2. `AUDIT_DB_PATH` env var
3. `DEFAULT_DB_PATH` from `reports.db.db_engine` (production default)

## Best-Effort Guarantee

Write failures are swallowed silently — audit logging must **never** break
the response. Monitor disk space and DB availability via external tooling.

## Querying

```python
from audit_log import fetch_audit_logs

# All accesses by alice
rows = fetch_audit_logs(user_id="alice")

# All 401s in a time window
rows = fetch_audit_logs(since="2026-05-15T00:00:00+00:00",
                        until="2026-05-16T00:00:00+00:00")
```

## Retention Policy (recommended)

- Keep online: 90 days
- Archive (export to JSON — tooling in future S5.1): 1 year
- Then purge

## Disabling for Tests

Tests run with `AUDIT_ENABLED=false` by default (set in `conftest.py`
autouse fixture). Tests that verify audit behavior opt in:

```python
@pytest.fixture
def audit_client(monkeypatch, tmp_path):
    monkeypatch.setenv("AUDIT_ENABLED", "true")
    monkeypatch.setenv("AUDIT_DB_PATH", str(tmp_path / "audit.db"))
    ...
```

## Production Checklist

- [ ] `AUDIT_ENABLED=true` (default — confirm not overridden)
- [ ] DB disk space monitoring (table grows linearly with traffic)
- [ ] Retention/archival cron job configured
- [ ] Admin endpoint to query audit log requires admin role (future S5.1)
