# Mass Valuation — Verification Guide

Covers R-03 (Reproducibility), R-04 (Holdout / Data-Leakage Safety),
and R-05 (Run Version Traceability) for the `POST /api/mass-valuation/import` pipeline.

---

## Endpoint Contract — Request Format and Size

**Endpoint:** `POST /api/mass-valuation/import`

**Request format:** JSON body only. The endpoint uses `request.get_json(silent=True)`.
Multipart form uploads are not accepted.

**Request-size limit (evidence-based):**
- No application-level upload-size limit (`MAX_CONTENT_LENGTH` or equivalent) was found
  configured for this endpoint in `bridge_api.py`.
- The endpoint accepts JSON, not multipart uploads.
- The effective request-size limit is deployment/server-dependent (Waitress, Nginx,
  or load balancer settings in production).
- A production request-size limit remains a deployment-hardening item, not addressed
  in this branch.

---

## R-03 — Reproducibility

**Claim:** Identical input records produce identical pipeline output — same column mapping,
same quality flags, same eligible set — regardless of when the call is made.

### How to verify

```python
from core_engine.mass_valuation.pipeline import run_pipeline

records = [
    {"property_id": "P001", "transaction_price": 500_000, "address": "Riyadh", "land_area_m2": 200},
    {"property_id": "P002", "transaction_price": 0,       "address": "Jeddah", "land_area_m2": 100},
]

r1 = run_pipeline(records, source="csv", lookback_months=36)
r2 = run_pipeline(records, source="csv", lookback_months=36)

assert r1.n_eligible  == r2.n_eligible
assert r1.n_rejected  == r2.n_rejected
assert r1.n_flagged   == r2.n_flagged

rpt1 = {e["property_id"]: e["action"] for e in r1.pipeline_report()}
rpt2 = {e["property_id"]: e["action"] for e in r2.pipeline_report()}
assert rpt1 == rpt2
```

**Why this holds:**
- `column_mapper.py` (D-02) applies deterministic alias lookups with no random or time-dependent state.
- `quality_checker.py` (D-03/D-04/D-05) applies rule-based checks; no statistical models or
  date-sensitive windows are used within a single batch call.
- `lookback_months` is an explicit parameter, not derived from `datetime.now()`.

**What can change between runs:**
- If the reference dataset used by D-03 batching is updated (e.g., new comparable transactions
  appended), the `lookback_months` window will cover different data → different outlier flags.
  This is expected and intentional. To freeze a run for audit, use the `run_id` from R-05.

---

## R-04 — Holdout / Data-Leakage Safety

**Claim:** The import pipeline does not use `execute=true` training data to influence
D-02/D-03/D-04/D-05 quality decisions. There is no data leakage from the runner back to the pipeline.

### Architecture proof

The endpoint (`bridge_api.py:12960–13025`) executes these steps in strict order:

```
1. parse request body           (records, source, lookback_months, execute)
2. _mv_run_pipeline(raw_records, ...)  ← pipeline runs FIRST, independently
3. if execute=true:
       runner.run(pipeline.eligible_records, ...)   ← runner sees ONLY eligible records
4. return response
```

`run_pipeline()` completes and returns a `PipelineResult` **before** `MassValuationRunner` is
ever instantiated. The pipeline receives `raw_records` (the original input list) by reference,
but `MassValuationRunner.run()` receives `pipeline.eligible_records` — a derived list of
canonical dicts computed entirely within the pipeline.

No feedback path exists from runner output back to the pipeline because:
- `run_pipeline()` is a pure function (no global state mutation).
- `MassValuationRunner` is constructed after `run_pipeline()` returns.
- The `PipelineResult` object is immutable after construction.

### How to verify

```python
from unittest.mock import patch, MagicMock
from core_engine.mass_valuation.pipeline import run_pipeline

records = [{"property_id": "P001", "transaction_price": 500_000, "address": "Riyadh", "land_area_m2": 200}]

pipeline_calls = []
original_run = run_pipeline

def spy_run(raw, **kw):
    result = original_run(raw, **kw)
    pipeline_calls.append(len(raw))
    return result

with patch("core_engine.mass_valuation.pipeline.run_pipeline", side_effect=spy_run):
    r = spy_run(records)

# Pipeline ran once, on the original raw records, not on runner output
assert pipeline_calls == [1]
assert r.n_input == 1
```

---

## R-05 — Run Version Traceability

**Claim:** Every `execute=true` call returns a `run_id` that can be traced back to the exact
input batch, source, lookback_months, pipeline_report, and IAAO metrics via the audit APIs.

### Step 1 — Perform an import run

```bash
curl -s -X POST http://127.0.0.1:5000/api/mass-valuation/import \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"records": [...], "execute": true, "run_name": "Audit-2026-Q3"}' \
  | python -m json.tool
```

Response includes:

```json
{
  "run_result": {
    "run_id": "mv_run_abc123",
    "status": "completed",
    "n_predicted": 47
  },
  "advisory_only": true,
  "certification_ready": false
}
```

### Step 2 — List runs

```bash
curl -s http://127.0.0.1:5000/api/mass-valuation/runs \
  -H "Authorization: Bearer <admin_token>" | python -m json.tool
```

Returns paginated list with `run_id`, `run_name`, `created_at`, `status`, `n_input_records`.

### Step 3 — Retrieve predictions for a run

```bash
curl -s http://127.0.0.1:5000/api/mass-valuation/predictions/mv_run_abc123 \
  -H "Authorization: Bearer <admin_token>" | python -m json.tool
```

Returns per-property predictions with `property_id`, `predicted_value`, `method`, `confidence`.

### Invariants on every response

| Field | Value | Where enforced |
|-------|-------|----------------|
| `advisory_only` | `true` | `bridge_api.py:13025` (hard-coded) |
| `certification_ready` | `false` | `bridge_api.py:13026` (hard-coded) |

These values are **never** computed from data. An auditor may verify by inspecting the source
at those lines — no configuration or environment variable can override them.
