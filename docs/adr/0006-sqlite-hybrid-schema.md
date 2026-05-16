# ADR-0006: SQLite with Hybrid Schema (Indexed Cols + JSON Blob)

- **Status:** Accepted
- **Date:** 2026-05-03

## Context

The DB engine needed to persist full report DTOs for later retrieval and display.
Report DTOs are large, nested, heterogeneous dicts (property info, comparables,
adjustments, valuation results, appraiser info, signatures). Their shape varies
between profiles and evolves as new fields are added to the engines.

Two competing requirements:
1. **Filtering and listing** — the history panel needs to filter by `profile_key`,
   `status`, date range, and display `appraiser_name` and `market_value` without
   deserializing the full blob.
2. **Round-trip fidelity** — the full DTO must survive a save/load cycle without
   loss, including Arabic strings, nested dicts, and None values.

## Options Considered

### Option A — Full normalization
Decompose the DTO into relational tables (property_info, comparables, adjustments, ...).

- Pros: SQL filtering on any field. No JSON deserialization.
- Cons: Schema migration required for every DTO shape change. The DTO has ~40+
  fields with profile-dependent optional subtrees. Full normalization would require
  10+ tables and complex JOINs for a simple list view.

### Option B — Pure JSON blob
Store the entire DTO as a single TEXT column.

- Pros: Zero schema migration for DTO changes. Perfect fidelity.
- Cons: Cannot filter by `profile_key` or `status` without deserializing every row.
  Full-table scan for every list request. Unusable at scale.

### Option C — Hybrid: indexed cols + JSON blob (chosen)
A small set of top-level scalar fields are extracted into indexed columns:
`report_id`, `profile_key`, `status`, `appraiser_name`, `market_value`,
`created_at`, `updated_at`.

The full DTO is stored as a `TEXT` column (`data`) in JSON format.

List queries (`GET /api/reports`) filter and paginate using only the indexed columns.
Single-record retrieval (`GET /api/reports/<id>`) fetches the full blob and
deserializes it.

### Option D — PostgreSQL with JSONB
Use PostgreSQL's native JSONB type for indexed JSON querying.

- Pros: Full GIN indexing on arbitrary DTO fields.
- Cons: Requires a running PostgreSQL instance, `psycopg2`, and connection management.
  Overkill for a single-tenant local-first reporting store.

## Decision

Adopt Option C (SQLite hybrid). The schema is in `core_engine/reports/db/schema.py`.
Migrations are forward-only and registered in `_MIGRATIONS: dict[int, Callable]`.
A `schema_version` table with `CHECK(id=1)` enforces single-row semantics.

## Consequences

**Positive:**
- No external database process. SQLite is zero-config.
- List queries are fast: indexed column scans, no JSON deserialization.
- DTO schema changes (new fields) require no migration — the blob absorbs them.
- Arabic string round-trip is guaranteed by Python's `json` module (UTF-8 native).
- Forward-only migrations make rollback explicit: you must know what version you are
  rolling back to.

**Negative / Tradeoffs:**
- The indexed columns are a manually maintained projection of the DTO — if
  `appraiser_name` moves in the DTO, the extraction logic must be updated.
- SQLite does not support concurrent writes well; unsuitable for multi-process
  deployments without a connection serialization layer.
- The JSON blob is opaque to SQL tooling — cannot use `SELECT data->>'field'`
  without SQLite's JSON functions (available from SQLite 3.38+).
