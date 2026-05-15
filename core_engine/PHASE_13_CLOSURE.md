# Phase 13 — Persistent Storage — FINAL CLOSURE

**Status:** COMPLETE (100%)
**Date:** 2026-05-08
**Final Test Count:** 10 tests (all passing)

---

## Executive Summary

Phase 13 replaced the in-memory `BatchRegistry` (Phase 12.3) with a durable
SQLite store. Completed batch reports now survive server restarts. The public
API shapes (`GET /api/valuation/batch/<id>`, `GET /api/valuation/batch`) are
unchanged — callers cannot tell the difference.

---

## Task Ledger

| Task | Deliverable | Tests | Status |
|------|-------------|-------|--------|
| 13.0 | `batch_store.py` — SQLite BatchStore (save/get/list_recent/count/delete) | — | DONE |
| 13.1 | bridge_api.py — 3 targeted edits replacing BatchRegistry with BatchStore | — | DONE |
| 13.2 | `test_phase_13_e2e.py` (10 tests) + this closure doc | 10 | DONE |

---

## What Was Delivered

### Tasks 13.0 + 13.1 — BatchStore + bridge_api Wiring

**File:** `core_engine/database/batch_store.py`

**Schema (`batch_jobs` table):**

```sql
CREATE TABLE IF NOT EXISTS batch_jobs (
    batch_id              TEXT PRIMARY KEY,
    batch_name            TEXT NOT NULL DEFAULT '',
    status                TEXT NOT NULL DEFAULT 'completed',
    total_submitted       INTEGER NOT NULL DEFAULT 0,
    completed             INTEGER NOT NULL DEFAULT 0,
    failed                INTEGER NOT NULL DEFAULT 0,
    skipped               INTEGER NOT NULL DEFAULT 0,
    total_valuation_value REAL    NOT NULL DEFAULT 0.0,
    average_valuation     REAL    NOT NULL DEFAULT 0.0,
    summary_json          TEXT    NOT NULL DEFAULT '{}',
    report_json           TEXT    NOT NULL DEFAULT '{}',
    completed_at          TEXT,
    registered_at         TEXT    NOT NULL
);
```

`summary_json` stores the flat `summary` dict. `report_json` stores the full
`completion_report` dict (including `completed_properties`, `failed_properties`,
`skipped_properties`) so `get()` reconstructs the same shape every time.

**DB path resolution (priority order):**
1. `db_path` constructor argument
2. `EXPERT_SMART_BATCH_DB` environment variable
3. Default: `tempfile.gettempdir()/expert_smart_batches.db`

**Public API:**

| Method | Description |
|--------|-------------|
| `save(completion_report)` | INSERT OR REPLACE by `batch_id`; stamps `registered_at` |
| `get(batch_id)` | Returns reconstructed dict or `None` |
| `list_recent(limit=20)` | SELECT ORDER BY `registered_at` DESC LIMIT n |
| `count()` | SELECT COUNT(*) |
| `delete(batch_id)` | Removes one record (admin/test) |
| `clear_all()` | Removes all records (test isolation) |

**Design decisions:**
- One new `sqlite3.connect()` per public method — avoids cross-thread connection
  sharing (sqlite3 default restriction). Connections are cheap to open.
- `CREATE TABLE IF NOT EXISTS` on every `__init__` — idempotent, no migration
  needed for new installs, sub-millisecond when table already exists.
- `INSERT OR REPLACE` — re-saving the same `batch_id` is safe; the row is
  replaced atomically.
- `row_factory = sqlite3.Row` — allows dict-like column access in `_row_to_dict`.

**bridge_api.py changes (3 edits, all inside route functions):**

| Route | Before | After |
|-------|--------|-------|
| `POST /api/valuation/batch` | `registry.register(...)` | `BatchStore().save(...)` |
| `GET /api/valuation/batch/<id>` | `registry.get(batch_id)` | `BatchStore().get(batch_id)` |
| `GET /api/valuation/batch` | `registry.list_recent(limit)` | `BatchStore().list_recent(limit)` |

`BatchRegistry` in `adapters/batch_registry.py` is retained (not deleted) —
it is still covered by Phase 12 tests and may serve as a cache layer in a
future phase.

---

## Test Coverage

| Test | What it verifies |
|------|-----------------|
| `test_store_creates_db_file` | SQLite file created on disk after `BatchStore()` init |
| `test_save_get_roundtrip` | Exact field values (batch_id, status, counts, property lists, registered_at) preserved across save/get |
| `test_get_unknown_returns_none` | Missing batch_id returns `None`, not KeyError |
| `test_list_recent_newest_first` | INSERT order preserved; list order is newest-first |
| `test_count_reflects_saves` | `count()` starts at 0, increments correctly |
| `test_persistence_across_instances` | Record saved in instance A is retrievable in instance B (same db file, different connection) — the core durability proof |
| `test_list_recent_limit` | `limit=3` returns exactly 3 from a 10-record store |
| `test_api_post_then_get_from_sqlite` | Full round-trip through the live Flask routes: POST creates, GET retrieves from SQLite |
| `test_api_list_includes_posted_batch` | `GET /api/valuation/batch?limit=50` includes the just-posted batch |
| `test_delete_and_clear` | `delete()` removes one; `clear_all()` empties the table |

---

## Architecture After Phase 13

```
POST /api/valuation/batch
        │
        ▼
BatchProcessor → get_completion_report()
        │
        ▼
BatchStore.save()  ──────────────────────────► expert_smart_batches.db
        │                                              │
        │                                              │
        └──► HTTP response (immediate)        GET /api/valuation/batch/<id>
                                              GET /api/valuation/batch
                                                       │
                                              BatchStore.get() / .list_recent()
                                                       │
                                              ◄────────┘
                                              HTTP response (from SQLite)
```

---

## Files Created / Modified

| File | Change |
|------|--------|
| `core_engine/database/batch_store.py` | Created — Task 13.0 |
| `core_engine/bridge_api.py` | Modified — 3 targeted edits (Task 13.1) |
| `core_engine/tests/test_phase_13_e2e.py` | Created — 10 tests (Task 13.2) |
| `core_engine/PHASE_13_CLOSURE.md` | Created — this file |

---

## No-Touch Zones (respected throughout)

- `core_engine/engines/` — not opened
- `core_engine/adapters/` Phases 5–12 files — not modified
- `core_engine/database/` Phase 8 files (models, connection, queries, migrations) — not modified
- All existing API response shapes — unchanged
- All Phase 4–12 valuation logic — unchanged

---

## Critical Notes for Next Phase

- Default DB path is `%TEMP%/expert_smart_batches.db`. Set
  `EXPERT_SMART_BATCH_DB` env var to point to a stable location for production.
- `BatchStore()` is instantiated inside each route call (no module-level
  singleton). This is intentional: the db_path is resolved once at import time
  via `_DEFAULT_DB`, so all instances share the same file unless overridden.
- `bridge_api.py` is now ~8,430+ lines. Always syntax-check after editing:
  ```powershell
  python -c "import ast, pathlib; ast.parse(pathlib.Path('core_engine/bridge_api.py').read_text(encoding='utf-8'))"
  ```
- All Phase 5–13 work remains **uncommitted**. Git only has Phase 4 commits on `main`.

---

## Cumulative Test Count

| Phase | Tests |
|-------|-------|
| 1–7   | ~302  |
| 8     | 55    |
| 9     | 28    |
| 10    | 5     |
| 11    | 25    |
| 12    | 20    |
| 13    | 10    |
| **Total** | **~445+** |

---

## Suggested Next Phase

**Phase 14 — Webhook Notifications**
- `POST /api/valuation/batch` accepts optional `webhook_url`
- On completion, POST the report to the webhook URL in a background thread
- `WebhookDelivery`: url, payload, attempt, last_status, delivered_at
- Retry logic: up to 3 attempts with exponential back-off (2s, 4s, 8s)
- `WebhookLog` SQLite table — persists delivery history alongside batch_jobs
- Tests: mock HTTP server receives payload; retry on failure; max-attempt cap
