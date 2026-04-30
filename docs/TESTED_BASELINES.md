# Expert_Smart — Tested Baselines

Snapshot of the runtime validation that closed the stabilization phase (April 2026).
**These are the *known-good* values you can compare future runs against.** A delta beyond ±5% on any numeric field is worth investigating.

---

## Stabilization summary

| # | Test | HTTP | Outcome | Key value |
|---|---|---|---|---|
| 1 | `GET /api/advisor/health` | 200 | ✅ Pass | `status="ok"`, `rag_ready=true` |
| 2 | `GET /api/price-index` | 200 | ✅ Pass (HTTP-confirmed, post-densification) | **1,731 records, 40 regions, avg YoY 11.74%** |
| 3a | `POST /api/valuation` (user-supplied ppm) | 200 | ✅ Pass | `market_value = 6,781,600` |
| 3b | `POST /api/valuation` (AVM-injected ppm) | 200 | ✅ Pass (HTTP-confirmed, post-densification) | `market_value = 6,358,000`, AVM `applied=true / medium / n=16 / avm_ppm=32,872` |
| 4 | `POST /api/hbu/analyze` | 200 | ✅ Pass | recommended NPV = 49,218,928 |
| 5 | `POST /api/reit/nav` | 200 | ✅ Pass | NAV = 48,400,000 / unit = 484 |
| 6 | `POST /api/eia/assess` | 200 | ✅ Pass | Category C, ERF 0.85, VaR 37,500,000 |
| 7a | `POST /api/image/analyze` (smoke) | 200 | ✅ Pass | tag returned, has_gps=false |
| 7b | `POST /api/image/analyze` (GPS) | — | ⊘ Skipped | no GPS-tagged sample available |
| 7c | `POST /api/image/analyze` (reject) | 415 | ✅ Pass | UnsupportedMediaType raised |

**Overall: 6 / 7 active tests passed; 1 sub-test deferred for later.**

---

## Detailed baselines

### Baseline 1 — Health
```
status     : "ok"
rag_ready  : true
message    : "المستشار الذكي جاهز"
```
First-call latency may be 30–90 s on a cold start because the embedding model loads in the background. Subsequent calls are < 200 ms.

### Baseline 2 — Price Index (after `bootstrap_price_data.py --count 1500`)
**HTTP-confirmed via `GET /api/price-index` on April 25, 2026 (post-densification):**
```
status                   : "success"
summary.n_records        : 1731
summary.n_regions        : 40
summary.avg_yoy_pct      : 11.74
summary.highest_region   : "المعادي - دجلة" (~22.9%)
top 3 (composite YoY): values shift on each regenerate; expect 18–25% range
                       in CMA / AVM consensus for top urban regions.
```
**Acceptance window (densified feed):** `n_records ≥ 1500`, `avg_yoy_pct` between 8% and 16%, `highest_yoy_pct` ≤ 30%.

> Earlier sparse-feed baseline (April 25, 2026, before densification): 254 records, avg YoY 9.5%, highest 26.26%. Kept for traceability but **not** the current acceptance target.

### Baseline 3 — Valuation (200 m² apartment in التجمع الخامس)

This endpoint has **two confirmed runtime paths**, depending on whether the caller supplies a `price_per_meter`. Both are HTTP-confirmed.

#### Baseline 3a — User-supplied `price_per_meter` path (legacy)
```
payload includes a manual price_per_meter
status              : "success"
market_value        : 6,781,600 EGP
excel_url           : /api/download/Report_ES-<id>.xlsm
purpose_report_url  : /api/download/PurposeReport_fair_market_value_<id>.docx
avm.applied         : false        (user value preserved — never overwritten)
avm.user_ppm_kept   : true
avm.verdict         : "AVM يُقارب المُدخَل…" or sanity-check spread
```
**Acceptance window (3a):** `market_value` between 6.5M and 7.5M for the canonical payload.

#### Baseline 3b — AVM-injected `price_per_meter` path (post-densification, HTTP-confirmed)
**HTTP-confirmed via `POST /api/valuation` on April 25, 2026** with payload:
```json
{
  "location":          "التجمع الخامس",
  "property_type":     "شقة سكنية",
  "valuation_purpose": "fair_market_value",
  "area":              200
}
```
(no `price_per_meter` supplied — AVM injects it from `market_feed.json`)

Confirmed response:
```
status              : "success"
market_value        : 6,358,000 EGP
avm.applied         : true
avm.eligible        : true
avm.purpose         : "fair_market_value"
avm.confidence      : "medium"
avm.n_records       : 16
avm.time_span_months: 11
avm.avm_ppm         : 32,872 EGP
avm.matched_region  : "القاهرة الجديدة - التجمع الخامس"
avm.weight_uplift   : 0.50
avm.verdict         : "تم اعتماد سعر المتر من AVM = 32,872 ج.م (confidence=medium, n=16 معاملة)."
avm.notes           : "AVM مفعَّل — confidence=medium، بناءً على 16 معاملة عبر 11 شهر."
```
**AVM is now active for this case with medium confidence.**

**Acceptance window (3b):** `market_value` between 6.0M and 7.0M; `avm.applied = true`; `avm.confidence ∈ {"medium", "high"}`; `avm.n_records ≥ 10`; `avm.time_span_months ≥ 3`. Numeric values may drift ±5% on each `bootstrap_price_data.py` regenerate due to randomized noise in the seed data.

> **Before/After densification (April 25, 2026, HTTP-confirmed):**
> - Total feed records: **254 → 1,731**
> - Records matching `التجمع الخامس` + `شقة سكنية`: **1 → 16**
> - `avm.applied`: **false → true**
> - `avm.confidence`: **none → medium**
> - `avm.avm_ppm`: **0 → 32,872 EGP**
> - `market_value` (no user ppm): **N/A (AVM disabled) → 6,358,000 EGP (AVM-driven)**
> - Path of fix: data-density only (no code/config/route changes). See DEFERRED_ITEMS.md → D4.

### Baseline 4 — HBU (5,000 m² mixed-zone plot, 2 alternatives)
```
status                       : "success"
result.recommended_use       : "مول تجاري"
result.recommended_npv       : 49,218,928 EGP
comparison_table[0]:
  use_name         : "برج سكني"
  npv              : 20,234,464
  irr_pct          : 15.92%
  payback_years    : 7.07
  verdict          : "مرشَّح ولكن ليس الأعلى إنتاجية"
comparison_table[1]:
  use_name             : "مول تجاري"
  npv                  : 49,218,928
  irr_pct              : 18.82%
  payback_years        : 6.23
  maximally_productive : true
  verdict              : "أعلى وأفضل استغلال (HBU) — موصى به"
```
**Acceptance window:** recommended_npv ≥ 45M; IRRs within 14–20% range.

### Baseline 5 — REIT NAV (2-asset fund, 100k units)
```
status                        : "success"
result.gross_asset_value      : 86,200,000 EGP
result.total_liabilities      : 37,800,000 EGP
result.nav                    : 48,400,000 EGP
result.nav_per_unit           : 484 EGP
result.weighted_cap_rate_pct  : 7.375
result.ltv_pct                : 43.75
result.gearing_ratio_pct      : 43.85
result.health_label           : "جيد — مقبول لصناديق REITs"
excel_url                     : empty (export_excel was not requested)
```
**Acceptance window:** all values match within ±0.01% (deterministic given the inputs).

### Baseline 6 — EIA (chemical factory, 3 critical impacts)
```
status                                          : "success"
category                                        : "C"
result.classification.category_label            : "فئة (ج) — مرتفع الأثر"
result.classification.composite_score           : 6.95
erf                                             : 0.85
result.investment_linkage.market_value          : 250,000,000
result.investment_linkage.adjusted_market_value : 212,500,000
result.investment_linkage.value_at_risk         : 37,500,000
result.impact_assessment.avg_impact_score       : 8.0
result.impact_assessment.n_critical             : 3
word_url                                        : /api/download/EIA_Report_<id>.docx
excel_url                                       : /api/download/eia_report_<ts>.xlsx
```
**Acceptance window:** `category="C"`, `erf=0.85`, `adjusted_market_value` exactly = `0.85 × market_value`.

### Baseline 7 — Image Analyze
- **7a smoke:** ordinary photo → `status="success"`, `tag` Arabic, `has_gps=false`, `saved_as` ends in `.jpg`.
- **7c reject:** non-image file → HTTP 415 (`UnsupportedMediaType`).
- **7b GPS:** deferred. See DEFERRED_ITEMS.md.

---

## Future smoke checklist (template)

Copy this template, run the 7 commands from `API_REFERENCE.md`, and fill in:

```
══════════════════════════════════════════════════════
  Expert_Smart Smoke Test — date: ____________
══════════════════════════════════════════════════════

[1] GET  /api/advisor/health           ☐ Pass  ☐ Fail
    status:    _____    rag_ready: _____
    note:      ________________________________________

[2] GET  /api/price-index               ☐ Pass  ☐ Fail
    n_records: _____    n_regions: _____
    avg_yoy:   _____%   highest:   _____ (_____%)
    note:      ________________________________________

[3] POST /api/valuation                 ☐ Pass  ☐ Fail
    market_value:    _____
    excel_url:       _____
    avm.applied:     _____    confidence: _____
    note:            __________________________________

[4] POST /api/hbu/analyze               ☐ Pass  ☐ Fail
    recommended_use: _____
    recommended_npv: _____
    irr_pct (best):  _____%
    note:            __________________________________

[5] POST /api/reit/nav                  ☐ Pass  ☐ Fail
    GAV:           _____
    NAV:           _____
    NAV per unit:  _____
    LTV %:         _____
    note:          ____________________________________

[6] POST /api/eia/assess                ☐ Pass  ☐ Fail
    category:        _____    erf:        _____
    adjusted MV:     _____    value@risk: _____
    n_critical:      _____
    note:            __________________________________

[7a] POST /api/image/analyze (smoke)    ☐ Pass  ☐ Fail
     status:        _____    tag:        _____
     has_gps:       _____    saved_as:   _____

[7c] POST /api/image/analyze (reject)   ☐ Pass  ☐ Fail
     status code:   _____   (expected 415)

[7b] POST /api/image/analyze (GPS)      ☐ Pass  ☐ Fail  ☐ Skipped
     has_gps:   _____    lat:    _____    lng:    _____
     note:      ________________________________________

──────────────────────────────────────────────────────
Total:        Pass _____ / 9
Server uptime confirmed before testing? (Y / N)
Issues to file:
  - __________________________________________________
  - __________________________________________________
──────────────────────────────────────────────────────
```

---

## Validation environment used

- OS: Windows + PowerShell 5.1
- Python: 3.x (per server window banner)
- WSGI: waitress (with Flask `app.run` fallback)
- Port: 5000
- market_feed.json (initial run): 254 records (250 from `bootstrap_price_data.py --count 250` + 4 legacy)
- market_feed.json (after AVM densification, April 25, 2026): **1,731 records** from `bootstrap_price_data.py --count 1500` (preserves prior records via append). Backup of the 254-record feed: `core_engine/data/market_feed.backup_20260425_140144.json`.
- Tests run on: April 25, 2026 (initial validation + AVM densification follow-up)
- **HTTP-level confirmation (April 25, 2026):** `GET /api/price-index` and `POST /api/valuation` were both invoked from PowerShell against the running Waitress server (`http://127.0.0.1:5000`). Numbers in Baseline 2 and Baseline 3b above are the actual response values, not derived from direct Python module calls.

**Notes for replicating:**
- Always restart `python core_engine/bridge_api.py` after any code change. Waitress does not auto-reload.
- For Arabic console output add `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` before running tests.
- Use `curl.exe` (not `Invoke-RestMethod`) for `/api/image/analyze` if PowerShell version < 6.0 (no `-Form` support).
