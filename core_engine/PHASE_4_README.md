# Phase 4 — Methodological Engines + EgVS Skeleton

## Overview

Phase 4 delivered the foundational methodological layer of the Expert Smart valuation system:

- **3 core calculation engines** (Comparative, Cost, Income Approach)
- **Comparable search + ranking** (1,731 records from `market_feed.json`, 6-factor similarity scoring)
- **EgVS compliance skeleton** (court-grade audit trail on every calculation step)
- **4 new Flask API endpoints** (expose all engines to the web, no existing routes modified)

**Status:** ✅ Complete, tested, committed — `7b1e1f2`

---

## What Was Built

### 1. Core Foundation — Task 4.0
**File:** `core_engine/engines/base.py`

Abstract base classes and dataclasses shared by every engine:

| Class | Purpose |
|---|---|
| `AuditEntry` | One calculation step: step_name, inputs, outputs, formula, references |
| `ValidationIssue` | Problem flag: severity (error/warning/info), code, message |
| `EngineResult` | Complete output: value, confidence, audit_trail, issues, metadata |
| `ValuationEngine` | ABC — enforces `validate()` + `calculate()` on every subclass |

`ValuationEngine` is abstract — instantiating it directly raises `TypeError`. Every engine inherits from it and must implement both methods.

---

### 2. Comparable Search — Tasks 4.1 + 4.2
**File:** `core_engine/engines/comparable_search.py`

**Class:** `ComparableSearchEngine`

Loads `market_feed.json` once at startup and exposes a filter + ranking API.

#### Real data characteristics (as of Phase 4)
- 1,731 records, flat JSON array (not `{"comparables": [...]}`)
- Fields: `area`, `price`, `price_per_meter`, `timestamp`, `location` (string), `year_built`, `credibility`
- Location is a district string in Arabic — no lat/lng coordinates yet
- `property_type` values are Arabic strings: `شقة سكنية`, `فيلا`, `تجاري`, `عمارة سكنية`, `أرض فضاء`, `فندق`, `محل تجاري`

#### Methods

**`search(filters)`** — filter comparables by criteria

| Filter | Type | Notes |
|---|---|---|
| `latitude`, `longitude` | float | Required — returns empty if absent |
| `radius_meters` | float | Default 5,000 |
| `property_type` | str | Exact match, case-insensitive |
| `area_sqm_min` / `area_sqm_max` | float | Auto-swaps if reversed |
| `max_age_months` | int | Based on `timestamp` |
| `finishing_levels` | list | Multi-select on `finishing_level` |
| `location_text` | str | Substring match on Arabic location string |

Each result gets two computed fields added:
- `distance_meters` — computed from lat/lng (0.0 if comp has no coordinates)
- `price_per_sqm` — `price / area`

**`similarity_score(subject, comparable)`** — score one comparable 0–100

| Factor | Weight | Scoring |
|---|---|---|
| Distance | 40% | `100 × max(0, 1 − dist / radius)` |
| Area | 20% | `100 × max(0, 1 − area_pct_diff / tolerance)` |
| Compound match | 15% | 100 if same `compound_id`, else 0 |
| Age | 10% | `100 × max(0, 1 − age_diff / 30)`, 50 if data absent |
| Finishing | 10% | 100 if same `finishing_level`, else 0 |
| Recency | 5% | `100 × max(0, 1 − days_ago / horizon_days)` |

Returns `{"similarity_score": float, "breakdown": {6 factors}}`.

**`search_and_rank(subject, filters, limit)`** — combines all three steps

1. `search(filters)` → filtered list
2. `similarity_score()` for each result
3. Sort descending by score, return top `limit` results

#### Live test result
- 1,320 `شقة سكنية` pass typical filters
- Top comparable score: **74.5** (distance 100, area 97.5, age 100, recency 100)
- `search_and_rank(limit=5)` returns exactly 5, sorted correctly

---

### 3. Comparative Engine — Task 4.3
**File:** `core_engine/engines/comparative.py`

**Class:** `ComparativeEngine` (inherits `ValuationEngine`)

Sales Comparison Approach — the dominant method in Egyptian residential valuation.

#### Inputs

```json
{
  "subject_area_sqm": 120,
  "subject_age_years": 2,
  "subject_floor": null,
  "subject_finishing_level": null,
  "comparables": [
    {
      "id": "comp_1",
      "area_sqm": 110,
      "price_egp": 4950000,
      "age_years": 3,
      "floor": 2,
      "finishing_level": "finished"
    }
  ]
}
```

#### Validation rules

| Code | Severity | Condition |
|---|---|---|
| `INVALID_SUBJECT_AREA` | error | `subject_area_sqm ≤ 0` |
| `INSUFFICIENT_COMPARABLES` | error | `len(comparables) < 3` |
| `BELOW_RECOMMENDED` | warning | `len(comparables) < 5` |
| `INVALID_COMPARABLE_AREA` | warning | Any comparable `area ≤ 0` |
| `MISSING_PRICE` | error | Comparable has no `price_egp` or `price_per_sqm` |
| `INVALID_PRICE` | warning | Price ≤ 0 |

#### Calculation flow (per comparable)

1. Extract `price_per_sqm = price_egp / area`
2. Apply **area adjustment**: `factor = (subject_area / comp_area) ^ 0.85`
3. Apply **age adjustment**: `factor = max(0, 1 − |subject_age − comp_age| × 0.01)`
4. Apply **floor adjustment**: lookup `floor_adjustments[str(floor_diff)]` (configurable dict)
5. Apply **finishing adjustment**: lookup `finishing_adjustments[comp_finishing]` (configurable dict)

Aggregate: `final_value = mean(adjusted_prices_per_sqm) × subject_area`

#### Configurable parameters

| Attribute | Default | Meaning |
|---|---|---|
| `area_elasticity` | 0.85 | Economy-of-scale exponent |
| `age_depreciation_per_year` | 0.01 | 1% per year age gap |
| `floor_adjustments` | `{}` | Dict: floor_diff → % adjustment |
| `finishing_adjustments` | `{}` | Dict: finishing_level → % adjustment |
| `config_min_comparables` | 3 | Error threshold |
| `config_recommended_comparables` | 5 | Warning threshold |

#### Confidence

| Condition | Confidence |
|---|---|
| ≥ 5 comparables | `high` |
| 3–4 comparables | `medium` |
| < 3 comparables | `insufficient` |

#### Metadata returned

```json
{
  "per_sqm": 41829.97,
  "comparable_count": 5,
  "price_range_min": 38241.5,
  "price_range_max": 44800.2,
  "coefficient_of_variation": 0.048
}
```

**Live test result:** 5,019,596 EGP · high · 22 audit entries

---

### 4. Cost Engine — Task 4.4
**File:** `core_engine/engines/cost.py`  
**Data:** `core_engine/engines/cost_tables.json`

**Class:** `CostEngine` (inherits `ValuationEngine`)

Cost Approach / Replacement Cost Method — used as a sanity check against the comparative value.

**Formula:**
```
RCN = cost_per_sqm × building_area
Depreciation% = min(age_years / economic_life, 1.0)
Depreciated_cost = RCN × (1 − Depreciation%)
Value = Depreciated_cost + Land_Value
```

#### Cost tables (`cost_tables.json`)

| Governorate | Economy (EGP/m²) | Standard (EGP/m²) | Luxury (EGP/m²) |
|---|---|---|---|
| Cairo | 8,000 | 14,000 | 25,000 |
| Giza | 7,500 | 13,000 | 23,000 |
| Alexandria | 7,000 | 12,000 | 20,000 |
| Ismailia | 6,500 | 11,000 | 18,000 |
| Suez | 6,500 | 11,000 | 18,000 |
| Port_Said | 6,500 | 11,000 | 18,000 |
| `_default` | 6,500 | 11,000 | 18,000 |

Unknown governorate → `UNKNOWN_GOVERNORATE` warning, falls back to `_default`.

#### Economic lives by quality

| Quality | Economic Life |
|---|---|
| Economy | 40 years |
| Standard | 60 years |
| Luxury | 80 years |

#### Validation rules

| Code | Severity | Condition |
|---|---|---|
| `INVALID_BUILDING_AREA` | error | `building_area_sqm ≤ 0` |
| `INVALID_AGE` | error | `building_age_years < 0` |
| `INVALID_QUALITY` | error | Not in `{economy, standard, luxury}` |
| `INVALID_LAND_VALUE` | error | `land_value_egp < 0` |
| `FULLY_DEPRECIATED` | warning | `age ≥ economic_life` |
| `UNKNOWN_GOVERNORATE` | warning | Not in cost tables |

#### Confidence

| Condition | Confidence |
|---|---|
| Age < 80% of life + land value > 0 | `high` |
| Age ≥ 80% of life | `medium` |
| Age ≥ economic life OR land value = 0 | `low` |

#### Spec example (exact match)

```
Cairo, standard, 120 m², 5 years old, land = 1,000,000 EGP
RCN = 14,000 × 120 = 1,680,000 EGP
Depreciation = 5/60 = 8.33%
Depreciated = 1,680,000 × 0.9167 = 1,540,000 EGP
Value = 1,540,000 + 1,000,000 = 2,540,000 EGP ✓
```

**Live test result:** 2,540,000 EGP · high · 6 audit entries

---

### 5. Income Engine — Task 4.5
**File:** `core_engine/engines/income.py`

**Class:** `IncomeEngine` (inherits `ValuationEngine`)

Income Approach / Direct Capitalization — for rental and income-producing properties.

**Formula:**
```
EGI = Gross_Income × (1 − Vacancy_Rate)
NOI = EGI × (1 − OpEx_Ratio)
Value = NOI / Cap_Rate
```

#### Inputs

```json
{
  "gross_income_annual_egp": 240000,
  "vacancy_rate": 0.10,
  "operating_expenses_ratio": 0.35,
  "cap_rate": 0.10,
  "cap_rate_source": "market",
  "cap_rate_source_reference": "Market analysis Cairo 2025"
}
```

#### Validation rules

| Code | Severity | Condition |
|---|---|---|
| `INVALID_GROSS_INCOME` | error | `gross_income ≤ 0` |
| `INVALID_VACANCY_RATE` | error | `vacancy < 0` or `vacancy > 0.5` |
| `INVALID_OPEX_RATIO` | error | `opex < 0` or `opex ≥ 1.0` |
| `HIGH_OPEX_RATIO` | warning | `opex > 0.7` |
| `INVALID_CAP_RATE` | error | `cap_rate ≤ 0` |
| `CAP_RATE_OUT_OF_RANGE` | warning | Outside \[4%, 20%\] Egyptian range |
| `EXPERT_CAP_RATE_NO_SOURCE` | warning | Source is "expert" but no reference given |
| `NON_POSITIVE_NOI` | error | Calculated NOI ≤ 0 (property unprofitable) |

#### Confidence

| Condition | Confidence |
|---|---|
| NOI ≤ 0 | `insufficient` |
| Vacancy > 30% | `low` |
| Cap rate in \[4%, 20%\] | `high` |
| Cap rate outside range, source = "expert" | `medium` |
| Cap rate outside range, source = "market"/"published" | `high` |

#### Spec example (exact match)

```
Gross income: 240,000 EGP/year
Vacancy 10%:  EGI = 216,000 EGP
OpEx 35%:     OpEx = 75,600 EGP → NOI = 140,400 EGP
Cap rate 10%: Value = 140,400 / 0.10 = 1,404,000 EGP ✓
```

**Live test result:** 1,404,000 EGP · high · 5 audit entries

---

### 6. Flask Integration — Task 4.6
**File:** `core_engine/bridge_api.py` (4 routes added, nothing else changed)

All 4 engines are exposed via lazy-loaded singletons (`get_*_engine()` functions). The engines are initialized on the first request and reused thereafter.

Every route returns the same JSON envelope:

```json
{
  "status": "success" | "error",
  "engine_name": "comparative" | "cost" | "income",
  "value": 5019596.00,
  "confidence": "high" | "medium" | "low" | "insufficient",
  "metadata": { ... },
  "audit_trail": [
    {
      "step_name": "Load inputs",
      "inputs": { ... },
      "outputs": { ... },
      "formula": "...",
      "references": ["EGVS_3.1: Sales Comparison Approach"]
    }
  ],
  "issues": [
    {
      "severity": "warning",
      "code": "BELOW_RECOMMENDED",
      "message": "Less than 5 comparables; confidence will be lower"
    }
  ]
}
```

---

## Architecture

```
core_engine/
│
├── bridge_api.py          ← Flask monolith — routes wired here
│
├── engines/               ← Phase 4 package (NEW)
│   ├── __init__.py        ← exports all 4 public classes
│   ├── base.py            ← AuditEntry, ValidationIssue, EngineResult, ValuationEngine
│   ├── comparable_search.py  ← ComparableSearchEngine (loads market_feed.json)
│   ├── comparative.py     ← ComparativeEngine (Sales Comparison)
│   ├── cost.py            ← CostEngine (Replacement Cost)
│   ├── income.py          ← IncomeEngine (Direct Capitalization)
│   └── cost_tables.json   ← EGP/m² by governorate + quality
│
└── data/
    └── market_feed.json   ← 1,731 comparable transactions (read-only)
```

**Key design decisions:**
- Engines are **pure Python** — no Flask, no file I/O, no side effects
- All engines use **relative imports** (`from .base import ...`) for compatibility with the `core_engine/` runtime context
- `bridge_api.py` uses `from engines.xxx import ...` (no `core_engine.` prefix)
- Paths to JSON files are resolved via `_BASE` (absolute path to `core_engine/`) to avoid working-directory issues
- Each engine is a **singleton** (lazy-loaded global) — `market_feed.json` is read once at startup

---

## API Reference

### POST /api/comparables/search

```bash
curl -X POST http://localhost:5000/api/comparables/search \
  -H "Content-Type: application/json" \
  -d '{
    "subject_property": {"area_sqm": 120, "age_years": 2},
    "filters": {
      "property_type": "شقة سكنية",
      "latitude": 30.0276,
      "longitude": 31.4913,
      "radius_meters": 5000
    },
    "limit": 10
  }'
```

### POST /api/engines/comparative

```bash
curl -X POST http://localhost:5000/api/engines/comparative \
  -H "Content-Type: application/json" \
  -d '{
    "subject_area_sqm": 120,
    "subject_age_years": 2,
    "comparables": [
      {"id": "c1", "area_sqm": 110, "price_egp": 4950000, "age_years": 3},
      {"id": "c2", "area_sqm": 125, "price_egp": 5100000, "age_years": 1},
      {"id": "c3", "area_sqm": 115, "price_egp": 4800000, "age_years": 4},
      {"id": "c4", "area_sqm": 130, "price_egp": 5300000, "age_years": 2},
      {"id": "c5", "area_sqm": 120, "price_egp": 5000000, "age_years": 2}
    ]
  }'
```

### POST /api/engines/cost

```bash
curl -X POST http://localhost:5000/api/engines/cost \
  -H "Content-Type: application/json" \
  -d '{
    "building_area_sqm": 120,
    "building_age_years": 5,
    "construction_quality": "standard",
    "governorate": "Cairo",
    "land_value_egp": 1000000
  }'
```

### POST /api/engines/income

```bash
curl -X POST http://localhost:5000/api/engines/income \
  -H "Content-Type: application/json" \
  -d '{
    "gross_income_annual_egp": 240000,
    "vacancy_rate": 0.10,
    "operating_expenses_ratio": 0.35,
    "cap_rate": 0.10,
    "cap_rate_source": "market",
    "cap_rate_source_reference": "Market analysis Cairo 2025"
  }'
```

---

## EgVS Compliance Notes

Every calculation step is logged as an `AuditEntry` with:
- `step_name` — human-readable label
- `inputs` — exact values that went into the step
- `outputs` — exact values that came out
- `formula` — the mathematical expression (not Python code)
- `references` — EGVS section references (e.g. `"EGVS_3.2: Area Adjustment"`)

This trail is preserved in every API response and is intended to satisfy court-grade traceability requirements. The `audit_trail` array is never omitted — it is always returned even when `value` is `null` (so the appraiser can see exactly which step failed).

EGVS references used:
| Reference | Engine | Step |
|---|---|---|
| EGVS_3.1 | Comparative | Sales Comparison Approach |
| EGVS_3.2 | Comparative | Area Adjustment |
| EGVS_3.3 | Comparative | Age / Condition Adjustment |
| EGVS_3.4 | Comparative | Value Reconciliation |
| EGVS_4.1 | Cost | Cost Approach |
| EGVS_4.2 | Cost | Replacement Cost New |
| EGVS_4.3 | Cost | Economic Life Table |
| EGVS_4.4 | Cost | Straight-Line Depreciation |
| EGVS_4.5 | Cost | Accrued Depreciation |
| EGVS_4.6 | Cost | Land + Building Reconciliation |
| EGVS_5.1 | Income | Income Approach |
| EGVS_5.2 | Income | Effective Gross Income |
| EGVS_5.3 | Income | Operating Expenses |
| EGVS_5.4 | Income | Net Operating Income |
| EGVS_5.5 | Income | Direct Capitalization |

---

## Known Limitations (Phase 4)

| Limitation | Impact | Phase 5 fix |
|---|---|---|
| No lat/lng in `market_feed.json` | Distance filter skipped; all records pass distance check | Geocode `location` strings → add `lat`/`lng` fields |
| Property types in Arabic only | English type strings return 0 comparables | Normalise property type vocabulary |
| Cost tables are estimates | Construction costs change quarterly | Pull from BIM/MOH published indices |
| Income approach: Direct Cap only | No multi-year DCF | Phase 10: DCF engine |
| No compound/finishing data in feed | Compound (15%) and finishing (10%) scores always 0 | Enrich feed records |
| Single-threaded engine singletons | Thread-safety not guaranteed under high concurrency | Add per-request engine instances or locks |

---

## Testing

All engines were tested in isolation before integration:

```
# Run from project root (C:\Users\...\expert_smart1 - Copy\)
python -m pytest core_engine/engines/  # (no pytest — manual shell tests only)

# Manual shell test pattern used throughout:
python -c "from core_engine.engines.cost import CostEngine; ..."
```

Live integration tests run against the running server:
```
# Start server
cd core_engine && python bridge_api.py

# Test all 4 routes
python -c "import urllib.request, json; ..."
```

All 6 live tests pass: comparable search, comparative, cost, income, error handling, existing route regression.

---

## What's Next (Phase 5 candidates)

1. **Geocode `market_feed.json`** — add `lat`/`lng` to each record so the distance filter works
2. **Enrich comparable data** — add `compound_id`, `finishing_level` to unlock the 25% of similarity score currently scored 0
3. **Three-method reconciliation** — take all three engine results, apply weights, produce final recommended value
4. **Frontend UI** — expose the 4 routes in the web interface (search + run all 3 engines + show audit trail)
5. **Cost table refresh** — update `cost_tables.json` with current Egyptian market construction costs
6. **Report generation** — embed audit trail into Word/PDF valuation reports
7. **Unit tests** — replace manual shell tests with a proper test suite (`pytest`)

---

*Phase 4 committed: `7b1e1f2` — feat: Phase 4A — methodological valuation engines + Flask routes*
