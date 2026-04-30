# Expert_Smart — Tool Manifest

Documentation-only manifest of currently stable HTTP endpoints that could
later be wrapped by an orchestration layer (LangGraph, MCP, or other).
This file is purely descriptive — no executable code, no runtime artifact.

Snapshot date: April 26, 2026.
Server: Flask + Waitress on `http://127.0.0.1:5000` (dev) /
        gunicorn in production (per `deploy/`).

## How to read

- **name**: short stable identifier (snake_case, intended as future `tool_id`).
- **route**: HTTP path served by `core_engine/bridge_api.py`.
- **method**: HTTP verb.
- **input shape**: human-readable summary of expected request payload.
  Not a formal JSON Schema yet — see "Future use" below.
- **output shape**: human-readable summary of the response top-level fields.
- **idempotent**: `yes` if same input always yields the same logical result;
  `no` if each call mutates persistent state (e.g., assigns a unique report ID
  or writes a uniquely-named file).
- **writes_file**: whether the call writes to `outputs/` (Excel/Word/image)
  as part of the normal success path.
- **ready**: whether the endpoint is suitable, as-is, for an orchestration
  wrapper. ✅ = ready, ⚠️ = partial (caveats below), ❌ = not ready.

## Manifest table

| name | route | method | input shape | output shape | idempotent | writes_file | ready |
|------|-------|--------|-------------|--------------|------------|-------------|-------|
| advisor_health | /api/advisor/health | GET | none | `{status, rag_ready, message}` | yes | no | ✅ yes |
| price_index | /api/price-index | GET | optional query (region_filter, property_type_filter, base_period) | `{status, summary{n_records, n_regions, avg_yoy_pct, highest_region, lowest_region}, regions[]}` | yes (deterministic given current `market_feed.json`) | no | ✅ yes |
| valuation | /api/valuation | POST | `{location, property_type, valuation_purpose, area, price_per_meter?, ...}` (see notes) | `{status, market_value, avm{applied, confidence, n_records, avm_ppm, ...}, excel_url, purpose_report_url}` | no — generates a unique report ID (`ES-<...>`) per call | yes (.xlsm + .docx in `outputs/`) | ✅ yes |
| hbu_analyze | /api/hbu/analyze | POST | `{plot_area_sqm, discount_rate_pct, horizon_years, alternative_uses[]}` | `{status, recommended_use, recommended_npv, recommendation_note, scenarios_evaluated[], comparison_table[]}` | yes (deterministic financial calculation) | no by default; word report optional | ✅ yes |
| reit_nav | /api/reit/nav | POST | `{fund_name, units_outstanding, assets[], liabilities{...}, export_excel?}` | `{status, result{gross_asset_value, total_liabilities, nav, nav_per_unit, weighted_cap_rate_pct, ltv_pct, gearing_ratio_pct, health_label}, excel_url?}` | yes (deterministic — values match within ±0.01% on identical inputs) | only if `export_excel=true` | ✅ yes |
| eia_assess | /api/eia/assess | POST | `{project_name, location, project_type, impacts[], market_value, ...}` | `{status, category, result{classification{category_label, composite_score}, impact_assessment{n_critical, avg_impact_score}, investment_linkage{erf, market_value, adjusted_market_value, value_at_risk}}, word_url, excel_url}` | yes (deterministic given inputs) | yes (.docx + .xlsx in `outputs/`) | ✅ yes |
| image_analyze | /api/image/analyze | POST | multipart/form-data with `file=@…` (image) | `{status, tag, has_gps, gps_lat?, gps_lng?, saved_as}` | partial — same image yields same `tag`/`has_gps`, but each upload saves to a uniquely-named file | yes (saves uploaded image to `outputs/`) | ⚠️ partial — GPS extraction unverified, see `DEFERRED_ITEMS.md` → D1 |

## Notes per endpoint

### advisor_health
- Read-only probe. First call may take 30–90 s (embedding model lazy-load).
  Subsequent calls < 200 ms.
- Reflects vector-DB readiness; returns `rag_ready=true` even with an empty
  collection (clients should not assume non-empty corpus from this signal alone).

### price_index
- Reads from `core_engine/data/market_feed.json` (currently 1,731 records
  post-densification).
- Pure read; no pagination cursor; safe to call repeatedly.

### valuation
- Side-effect generator: writes one `.xlsm` and one `.docx` per call,
  identified by `excel_url` and `purpose_report_url` in the response.
- AVM auto-injection: when `price_per_meter` is omitted and the purpose is in
  `{fair_market_value, bank_financing, tax_assessment, acquisition}`,
  the engine injects an AVM-derived ppm (see `TESTED_BASELINES.md → Baseline 3b`).
- "Idempotent: no" reflects the unique report-ID side effect; the **numeric
  result** for the same input is deterministic (within rounding).

### hbu_analyze
- Pure financial-engine call: 4-test sequential framework
  (legal / physical / financial / maximally productive) + NPV per scenario.
- Standard call returns the analysis dict only; an optional Word report can
  be requested but is not the default.

### reit_nav
- Portfolio-level NAV aggregator (IFRS 13 + IOSCO conventions).
- The Excel export is opt-in via `export_excel=true`; default response has
  no file side effect.

### eia_assess
- 10-section EIA workflow with classification A/B/C and an Environmental
  Risk Factor (ERF: A=1.00, B=0.95, C=0.85).
- Always writes a Word report and an Excel summary on success.

### image_analyze
- Saves the uploaded file under a uniquely-named path in `outputs/`.
- Returns `has_gps=false` cleanly when EXIF is absent (smoke-tested).
- GPS extraction code path **has not** been exercised on a real GPS-tagged
  photo — see `DEFERRED_ITEMS.md` → D1. An orchestration wrapper should
  treat `gps_lat` / `gps_lng` as best-effort until D1 is verified.

## Excluded from this manifest

| route | reason |
|---|---|
| `/api/image/geo-analyze` | Not implemented (`DEFERRED_ITEMS.md` → D2). 9 of 14 expected response fields have no traceable contract. Cannot be wrapped until restored or redesigned. |
| ~44 other routes under `/api/…` | Internal/admin/profile/download endpoints. Out of scope for this manifest until each is individually validated against `TESTED_BASELINES.md`. They will be added row-by-row, never in bulk. |

## Future use of this manifest

This document is intended as the **single source of truth** for any future
`tool_registry.json`. When (and only when) the project is ready for an
orchestration runtime — per the readiness assessment — each row here would
map 1:1 to a registry entry with formal JSON Schema for input and output.

Until then, this file is purely descriptive. **Adding a row here is not the
same as committing to wrap an endpoint.**

## Constraints

This file is documentation-only. Creating it does not:

- import or modify any Python module
- modify `bridge_api.py` or any route
- create a `tool_registry.json`
- create a `langgraph_orchestrator.py`
- introduce an MCP or LangGraph runtime
- alter request/response contracts of any listed endpoint
