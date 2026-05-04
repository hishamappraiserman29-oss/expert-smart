# Mass Appraisal Phase 1 — Release Checklist
**Version:** Phase 1.11 (Final Stabilization)
**Date:** 2026-05-02
**Status:** RELEASE FREEZE

---

## A. Backend Endpoint Tests

### POST `/api/mass-appraisal/preview`
- [ ] Returns `200` with `{status:"success", summary:{...}, rows:[...]}`
- [ ] Each row has `valid`, `errors`, `warnings` fields
- [ ] `summary` includes `total_rows`, `valid_rows`, `invalid_rows`, `warning_rows`
- [ ] Returns `400` with `error_code` for empty body
- [ ] Returns `400` for non-array `rows`
- [ ] Returns `400` (or `413`/`422`) if `rows.length > 100`
- [ ] Arabic location and property_type strings round-trip cleanly
- [ ] Negative `area` flagged as invalid

### POST `/api/mass-appraisal/run`
- [ ] Returns `200` with `{status:"success", rows:[...], summary:{...}}`
- [ ] Each success row has `market_value`, `currency`, `status:"success"`
- [ ] Each error row has `status:"error"`, `error` message
- [ ] Each skipped row has `status:"skipped"`, `skip_reason`
- [ ] `summary` contains `total_rows`, `successful_rows`, `failed_rows`, `skipped_rows`, `total_market_value`, `average_market_value`, `median_market_value`
- [ ] Phase 1.4 fields present: `location`, `property_type`, `area`, `price_per_meter_effective`, `calculation_source`
- [ ] Phase 1.5 DQ fields present: `data_quality_score` (0–100), `data_quality_level` (`high`/`medium`/`low`/`critical`), `data_quality_flags`
- [ ] Phase 1.6 outlier fields present: `value_per_m2`, `review_required`, `outlier_score`, `outlier_level`, `review_reasons`
- [ ] Summary has Phase 1.6: `outlier_summary`, `review_required_count`, `top_review_reasons`, `portfolio_medians`
- [ ] HBU / REIT / EIA purposes return `status:"skipped"` with `skip_reason`
- [ ] `elapsed_ms` present in summary
- [ ] Returns `400` for missing/empty `rows`

### POST `/api/mass-appraisal/export-xlsx`
- [ ] Returns `200` with `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- [ ] `Content-Disposition` header contains a `.xlsx` filename
- [ ] Returns `400` (`MISSING_RUN_RESULT`) if no valid run result in body
- [ ] Workbook contains ≥ 14 sheets (Executive Summary through Audit & Governance)
- [ ] Sheet names: Executive Summary, Portfolio Results, Purpose Analysis, Location Analysis, Asset Type Analysis, AVM Analysis, Tax Assessment, Usufruct & Uncertainty, Data Quality, Review Queue, Errors & Skipped Rows, Final Reviewed Portfolio, Final Exclusions, Audit & Governance, Assumptions
- [ ] `reviewed_summary` block appears in Executive Summary when sent
- [ ] `audit` block appears in Executive Summary and Audit & Governance sheet when sent
- [ ] File size > 5 KB

### Smoke test commands
```powershell
# Health check
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/advisor/health" -Method Get

# Preview
$body = '{"rows":[{"row_id":"R-001","location":"التجمع الخامس","property_type":"شقة سكنية","area":200,"valuation_purpose":"fair_market_value"}]}'
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/mass-appraisal/preview" -Method Post -ContentType "application/json" -Body $body

# Run
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/mass-appraisal/run" -Method Post -ContentType "application/json" -Body $body
```

---

## B. Frontend Tests

### Input & Upload
- [ ] **تحميل مثال** — fills textarea with 5-row example, counter shows "5 صف"
- [ ] **JSON input** — manually typed array is parsed without error
- [ ] **JSON upload** — `.json` file with `[{...}]` fills textarea and shows success banner
- [ ] **CSV upload** — `.csv` with required columns fills textarea and shows success banner
- [ ] **Invalid JSON upload** — shows Arabic error in summary bar
- [ ] **مسح** — clears textarea and results area
- [ ] Row counter updates live on textarea input

### Preview / Run
- [ ] **معاينة (Preview)** — calls `/api/mass-appraisal/preview`, shows green/red per-row status table
- [ ] **تشغيل (Run)** — calls `/api/mass-appraisal/run`, shows run-mode table with 7 columns
- [ ] Run table columns: المعرف, الغرض, الحالة, القيمة/السبب, جودة البيانات (DQ pill), مراجعة/شذوذ (outlier pill), قرار المراجعة
- [ ] Loading spinner visible during fetch
- [ ] Preview/Run buttons show disabled state during pending call (Phase 1.11)
- [ ] After Run: CSV and XLSX download buttons become enabled
- [ ] After Run: Batch ID appears in audit summary bar (`MA-YYYYMMDD-HHMMSS-XXXX`)
- [ ] After Run: Reviewed portfolio summary div visible

### Download CSV
- [ ] CSV download produces `mass_appraisal_results_YYYYMMDD_HHMMSS.csv`
- [ ] File opens correctly in Excel (Arabic renders, no garbled text)
- [ ] First rows are `AUDIT_FIELD,AUDIT_VALUE` audit header block
- [ ] Blank separator line between audit block and detail rows
- [ ] Detail rows have all Phase 1.4–1.8 columns (35+ columns)
- [ ] Last rows contain `=== REVIEWED PORTFOLIO SUMMARY ===` block (after Phase 1.8 review)
- [ ] Download button shows correct loading state (Phase 1.11)

### Download XLSX
- [ ] XLSX download produces `mass_appraisal_report_YYYYMMDD_HHMMSS.xlsx`
- [ ] File opens in Excel / LibreOffice without errors
- [ ] Sheet count ≥ 14
- [ ] Executive Summary has portfolio KVs in Arabic
- [ ] Portfolio Results sheet has data for all rows
- [ ] Data Quality sheet colored by level (green/yellow/orange/red)
- [ ] Review Queue sheet present
- [ ] Audit & Governance sheet contains batch_id, analyst, timestamps, notes

### Review Workflow (Phase 1.8)
- [ ] Each run-mode table row has a review `<select>` (معتمد / قيد المراجعة / …)
- [ ] Each row has analyst note input and "استبعاد من الملخص النهائي" checkbox
- [ ] Changing any select updates Reviewed Portfolio Summary in real time
- [ ] `review_timestamp` updates in audit bar when a decision changes
- [ ] Rows with `review_status=approved` appear in Final Reviewed Portfolio XLSX sheet

### Audit Metadata (Phase 1.9)
- [ ] "بيانات التدقيق والحوكمة" section is collapsible
- [ ] `mass-analyst-name`, `mass-batch-label`, methodology/assumptions/limitations fields present
- [ ] After Run, audit summary bar shows `Batch ID: MA-...`
- [ ] Audit fields populated from saved session on import

### Export Session (Phase 1.10)
- [ ] "حفظ جلسة التقييم الجماعي JSON" button downloads `mass_appraisal_session_YYYYMMDD_HHMMSS.json`
- [ ] JSON file contains `session_type:"mass_appraisal_session"`, `input_payload`, `latest_run_result`, `review_decisions`, `audit_state`, `audit`, `reviewed_summary`
- [ ] Export can be done before a run (captures input only) and after a run (captures full state)

### Import Session (Phase 1.10)
- [ ] File picker accepts only `.json`
- [ ] Selecting an invalid file shows: `ملف الجلسة غير صالح.`
- [ ] No file selected shows: `اختر ملف جلسة JSON أولاً.`
- [ ] Valid import restores: textarea, run results, review decisions, audit fields, CSV/XLSX buttons enabled
- [ ] `renderMassResult()` called — results table re-populated
- [ ] `renderReviewedPortfolioSummary()` called — summary re-rendered
- [ ] `renderMassAuditSummary()` called — batch ID bar re-rendered
- [ ] **No** backend request during import (verified in DevTools Network tab)
- [ ] Success message: `تم استعادة جلسة التقييم الجماعي بنجاح.`

### File Protocol Guard (Phase 1.11)
- [ ] Opening from `file:///` shows Arabic warning banner:
  `يجب فتح النظام من http://127.0.0.1:5000 وليس كملف محلي.`
- [ ] Warning does not appear when served from HTTP

---

## C. Regression Tests — Single-Property Valuation

> These tests ensure Mass Appraisal changes did not break the existing `/api/valuation` pipeline.

- [ ] **POST `/api/valuation`** — fair_market_value request returns correct `market_value`
- [ ] **Tax Assessment** — `tax_assessment` block present with `annual_tax`, `taxable_amount`
- [ ] **AVM** — when AVM data available, `avm.applied=true`, `confidence`, `n_records` in response
- [ ] **Usufruct** — `usufruct.pv_factor` calculated correctly for given years and discount rate
- [ ] **Uncertainty** — `uncertainty_range.spread_pct` matches input parameter
- [ ] **HBU** — returns HBU analysis block (not skipped in single-property mode)
- [ ] **REIT** — returns REIT block
- [ ] **EIA** — returns EIA block
- [ ] **Excel report download** — `GET /api/download/<filename>` still works for per-property reports
- [ ] **Word report download** — per-property Word report still downloadable
- [ ] **`/api/advisor/health`** — returns `{status:"ok"}`
- [ ] **No `/api/mass-appraisal/*` endpoint called** by single-property UI buttons

### Smoke test
```powershell
$singleBody = '{"location":"التجمع الخامس","property_type":"شقة سكنية","area":200,"valuation_purpose":"fair_market_value"}'
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/valuation" -Method Post -ContentType "application/json" -Body $singleBody
```

---

## D. Browser Tests

### Chrome / Edge (primary targets)
- [ ] All mass appraisal buttons visible and clickable
- [ ] Textarea accepts Arabic and LTR content simultaneously
- [ ] Blob download works (CSV and JSON session file)
- [ ] FileReader API works for JSON/CSV upload and session import
- [ ] No console errors on page load

### Hard Refresh
- [ ] After `Ctrl+Shift+R`: page loads cleanly, no stale cache issues
- [ ] CSV/XLSX buttons start as disabled after hard refresh
- [ ] `window.latestMassAppraisalRunResult` is `undefined` after hard refresh (no stale state)

### File Protocol Block
- [ ] Opening `frontend/index.html` directly via `file:///` shows the Arabic warning banner
- [ ] Fetch calls to `localhost` from `file://` would be blocked by browser CORS anyway

### DevTools Network — Expected Endpoints on Run
| Action | Endpoint | Method | Expected Status |
|--------|----------|--------|-----------------|
| Preview | `/api/mass-appraisal/preview` | POST | 200 |
| Run | `/api/mass-appraisal/run` | POST | 200 |
| Export XLSX | `/api/mass-appraisal/export-xlsx` | POST | 200 |
| Import session | — | — | No network call |
| Export session | — | — | No network call |
| Download CSV | — | — | No network call |

### Forbidden Endpoints (must NOT be called by Mass Appraisal UI)
- `/api/valuation`
- Any per-row report endpoint

---

## E. Known Limitations (Accepted for Phase 1)

| Limitation | Decision |
|------------|----------|
| No database persistence | Accepted — client-side session export/import provided |
| No background job queue | Accepted — synchronous batch, max 100 rows |
| Max 100 rows per batch | Hard limit enforced by backend |
| HBU / REIT / EIA excluded from batch | Skipped with `skip_reason` — Phase 2 target |
| Specialized assets limited/excluded | Phase 2 target |
| CSV / XLSX are aggregate reports only | By design — per-property reports are the single-property flow |
| No authentication / user management | Out of scope for Phase 1 |
| XLSX generated server-side, no disk write | In-memory only, no `/tmp` files |
| Session JSON not encrypted | Acceptable for local dev; encrypt before production |
| Review decisions not persisted to backend | Client-side only — survive via session export/import |

---

## F. Release Sign-Off

| Check | Result | Notes |
|-------|--------|-------|
| `py_compile core_engine/mass_appraisal.py` | ✅ PASS | |
| `py_compile core_engine/bridge_api.py` | ✅ PASS | |
| `py_compile core_engine/mass_appraisal_excel.py` | ✅ PASS | |
| All required JS functions present in HTML | ✅ PASS | |
| No `fetch(/api/valuation)` in mass section | ✅ PASS | |
| File protocol guard present | ✅ PASS | Phase 1.11 |
| Loading states on Preview/Run/XLSX | ✅ PASS | Phase 1.11 |
| Docker build | Pending manual run | |
| Manual end-to-end flow | Pending | See Section B |

---

## G. Phase 2 Backlog (NOT in Phase 1 scope)

- Batch support for HBU / REIT / EIA
- Batch support for specialized assets (hotel, land, industrial)
- Server-side session persistence (DB or Redis)
- Multi-user / authentication
- Background job queue for batches > 100 rows
- Per-row property report generation at batch scale
- Streaming / progress bar for large batches
- Scheduled/automated batch runs
- Comparison between two batch runs (diff view)
- Regulatory submission export formats (CBE, ETA)
