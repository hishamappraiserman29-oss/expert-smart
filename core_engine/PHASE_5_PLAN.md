# Phase 5 — Purpose Adapters Framework + IFRS 13 Compliance

## Overview

Phase 4 delivered three independent valuations for any property (Comparative, Cost, Income).
Phase 5 adds the **Purpose Layer** — transforms generic three-value estimates into
**purpose-specific valuations** (Mortgage Value, Insurance Value, Market Value, Fair Value per
IFRS 13, etc.).

### What Phase 5 delivers

1. **Purpose Adapter Framework** — abstract interface + purpose-specific logic
2. **IFRS 13 Fair Value Adapter** — Fair Value Hierarchy (Level 1, 2, 3) + risk adjustments
3. **Mortgage Value Adapter** — lender adjustments (LTV, risk premium, forced-sale haircut)
4. **Insurance Value Adapter** — replacement cost focus + underwriting rules (no land)
5. **Market Value Adapter** — standard definition per EGVS (most common use case)
6. **Weighted Reconciliation Engine** — appraiser-controlled weights (60/25/15 or custom)
7. **EgVS Full Integration** — complete EGVS section disclosure mapping + report skeleton

---

## Architecture shift from Phase 4

**Phase 4 — Engines Layer:**

```
POST /api/engines/comparative  →  ComparativeEngine.calculate()  →  EngineResult
POST /api/engines/cost         →  CostEngine.calculate()         →  EngineResult
POST /api/engines/income       →  IncomeEngine.calculate()        →  EngineResult
POST /api/comparables/search   →  ComparableSearchEngine.search() →  ranked list
```

Each engine produces a raw value + audit trail. No cross-engine logic. No purpose.

**Phase 5 — Purpose Layer (sits above engines):**

```
POST /api/valuation/full   ─┬─→ ComparativeEngine   ─┐
                             ├─→ CostEngine            ├─→ ReconciliationEngine
                             └─→ IncomeEngine          ─┘
                                         │
                                  PurposeAdapter (selected by valuation_purpose)
                                         │
                          ┌──────────────┼──────────────┐
                          ▼              ▼              ▼
                    MarketValue    MortgageValue   InsuranceValue
                    Adapter        Adapter         Adapter
                          │              │              │
                          └──────────────┼──────────────┘
                                         ▼
                                   FinalValuation
                                   (purpose-adjusted value +
                                    IFRS 13 level + full audit)
```

The caller sends **one request** with property data + purpose, and receives **one final value**
plus the complete three-engine breakdown, reconciliation weights, and purpose-specific
adjustments — all in the audit trail.

---

## Directory layout (new files only)

```
core_engine/
└── engines/
    ├── base.py                   ← existing (Phase 4)
    ├── comparable_search.py      ← existing (Phase 4)
    ├── comparative.py            ← existing (Phase 4)
    ├── cost.py                   ← existing (Phase 4)
    ├── income.py                 ← existing (Phase 4)
    │
    ├── reconciliation.py         ← NEW Task 5.1 — weighted average engine
    ├── purpose/                  ← NEW Task 5.2 — purpose adapter package
    │   ├── __init__.py
    │   ├── base.py               ← PurposeAdapter ABC
    │   ├── market_value.py       ← MarketValueAdapter
    │   ├── mortgage_value.py     ← MortgageValueAdapter
    │   ├── insurance_value.py    ← InsuranceValueAdapter
    │   └── ifrs13.py             ← IFRS13FairValueAdapter
    └── egvs_report.py            ← NEW Task 5.3 — EgVS report skeleton builder
```

`bridge_api.py` receives **one** new composite route: `POST /api/valuation/full`.
No existing Phase 4 routes are modified.

---

## Task 5.0 — Reconciliation Engine

**File:** `core_engine/engines/reconciliation.py`

### Purpose

Takes the three raw `EngineResult` objects from Phase 4 and produces a single
reconciled value, using explicit appraiser-controlled weights.

### Inputs

```python
{
    "comparative_result": EngineResult,   # from ComparativeEngine
    "cost_result":        EngineResult,   # from CostEngine
    "income_result":      EngineResult,   # from IncomeEngine
    "weights": {
        "comparative": 0.60,   # default for residential owner-occupied
        "cost":        0.25,
        "income":      0.15,
    },
    "weight_rationale": "Residential owner-occupied: market evidence is primary indicator"
}
```

Default weight sets by property category:

| Category | Comparative | Cost | Income | Rationale |
|----------|------------|------|--------|-----------|
| Residential owner-occupied | 60% | 25% | 15% | Buyer pays market price, not yield |
| Residential rental | 30% | 20% | 50% | Investor values income stream |
| Commercial / retail | 25% | 15% | 60% | Yield-driven market |
| Industrial | 20% | 50% | 30% | Replacement cost dominates; thin market |
| Land | 70% | 30% | 0% | No building to cost; income rarely applicable |
| Special purpose | 10% | 70% | 20% | Cost approach is usually most reliable |

### Validation rules

- Weights must sum to 1.0 (±0.001 tolerance)
- Only non-None engine values contribute; weights are re-normalised if an engine returned `None`
- If all three values are `None` → `confidence="insufficient"`
- If only one value is non-None → `confidence="low"` regardless of that engine's confidence

### Output: `ReconciliationResult`

```python
@dataclass
class ReconciliationResult:
    reconciled_value:    Decimal         # weighted average of non-None values
    confidence:          str             # high / medium / low / insufficient
    weights_used:        dict            # actual weights after re-normalisation
    weight_rationale:    str
    engine_values: dict[str, float|None] # {comparative: ..., cost: ..., income: ...}
    audit_trail:         list[AuditEntry]
    issues:              list[ValidationIssue]
```

### Audit trail entries

1. `"Extract engine values"` — all three raw values
2. `"Re-normalise weights"` — adjusted weights if any engine returned None
3. `"Apply weights"` — per-engine weighted contribution
4. `"Calculate reconciled value"` — sum of contributions
5. `"Determine confidence"` — rules applied

---

## Task 5.1 — Purpose Adapter Base

**File:** `core_engine/engines/purpose/base.py`

### Abstract interface

```python
class PurposeAdapter(ABC):
    name: str              # e.g. "market_value", "mortgage_value"
    ifrs13_level: str      # "level_1", "level_2", "level_3"
    egvs_section: str      # e.g. "EGVS_2.1"

    @abstractmethod
    def adjust(
        self,
        reconciled: ReconciliationResult,
        engine_results: dict[str, EngineResult],
        property_context: dict,
    ) -> "PurposeResult":
        ...

    @abstractmethod
    def validate_context(self, property_context: dict) -> list[ValidationIssue]:
        ...
```

### `PurposeResult` dataclass

```python
@dataclass
class PurposeResult:
    purpose:           str       # adapter name
    final_value:       Decimal   # purpose-adjusted value
    pre_purpose_value: Decimal   # reconciled value before purpose adjustment
    adjustment_pct:    float     # % change applied by this adapter
    adjustment_reason: str       # narrative explanation
    confidence:        str
    ifrs13_level:      str       # Level 1 / 2 / 3
    ifrs13_rationale:  str
    egvs_section:      str
    audit_trail:       list[AuditEntry]
    issues:            list[ValidationIssue]
    metadata:          dict
```

---

## Task 5.2a — Market Value Adapter

**File:** `core_engine/engines/purpose/market_value.py`

### Definition (EGVS 1.1)

> The estimated amount for which an asset or liability should exchange on the valuation date
> between a willing buyer and a willing seller in an arm's length transaction, after proper
> marketing, where the parties had each acted knowledgeably, prudently, and without compulsion.

### Behaviour

- **No adjustment** — the reconciled value IS the market value by definition
- `adjustment_pct = 0.0`
- `ifrs13_level = "level_2"` — uses observable comparable transactions (not Level 1 exchange quotes)
- Adds EGVS 1.1 disclosure to audit trail
- Applicable to: all property types

### Validation

- No special context required
- Warning if `comparable_count < 5` (thin market evidence)
- Warning if `coefficient_of_variation > 0.30` (heterogeneous comparables)

---

## Task 5.2b — Mortgage Value Adapter

**File:** `core_engine/engines/purpose/mortgage_value.py`

### Definition (Basel III / Egyptian Central Bank circular 1/2024)

Mortgage value is a **conservative, long-term sustainable value** for collateral purposes.
It must be lower than market value to account for forced-sale risk and market cyclicality.

### Adjustments applied (in sequence)

| Step | Adjustment | Default | Configurable |
|------|-----------|---------|-------------|
| 1 | Forced-sale haircut | −15% | Yes — 5–30% range |
| 2 | Market cycle discount | −5% | Yes — 0–15% range |
| 3 | LTV cap check | Warn if value implies LTV > 80% | No |
| 4 | Liquidity premium | −3% for illiquid assets | Yes |

Default total haircut: ~22% below market value.

### Inputs required in `property_context`

```json
{
    "loan_amount_egp":      3000000,
    "ltv_limit_pct":        0.80,
    "forced_sale_pct":      0.15,
    "market_cycle_pct":     0.05,
    "asset_liquidity":      "normal"
}
```

### Validation

- Error: `loan_amount_egp` missing or ≤ 0
- Error: `forced_sale_pct` outside [0.05, 0.30]
- Warning: `EXCEEDS_LTV_LIMIT` — if `loan / mortgage_value > ltv_limit_pct`
- Warning: `HIGH_HAIRCUT` — total adjustment > 30%

### `ifrs13_level`

- Level 2 if comparable transactions exist
- Level 3 if income only (no market comparables)

### Regulatory reference

- Basel III Article 210 (Collateral Valuation)
- Egyptian Central Bank Circular No. 1/2024 (Real Estate Collateral)
- EGVS Section 6.3 (Collateral Valuation)

---

## Task 5.2c — Insurance Value Adapter

**File:** `core_engine/engines/purpose/insurance_value.py`

### Definition

Insurance value = **reinstatement cost** of the building only (excludes land).
It represents the cost to rebuild the structure to the same specification after total loss.

### Behaviour

- Ignores comparative and income values entirely
- Uses `CostEngine.metadata.rcn` (Replacement Cost New) as base
- Applies an inflation escalation for the expected rebuild delay
- **Excludes land value** (`land_value_egp = 0` for insurance purposes)

### Formula

```
Insurance_Value = RCN × (1 + inflation_escalation)
                − land_value
                + professional_fees_pct × RCN
                + demolition_cost_pct × RCN
```

Default rates:
- `inflation_escalation = 0.15` (15% — one-year rebuild delay in Egyptian market)
- `professional_fees_pct = 0.08` (architect + engineer fees)
- `demolition_cost_pct = 0.05` (clearance before rebuild)

Total uplift above RCN: ~28%

### Inputs required

```json
{
    "inflation_escalation_pct": 0.15,
    "professional_fees_pct":    0.08,
    "demolition_cost_pct":      0.05
}
```

### Validation

- Error if `CostEngine` returned `None` (cannot derive RCN)
- Warning: `HIGH_ESCALATION` if `inflation_escalation_pct > 0.30`
- Warning: `NO_COST_ENGINE` if cost engine was not run (insurance approach unavailable)

### `ifrs13_level` → `"level_3"` (unobservable inputs — rebuild cost estimate)

---

## Task 5.2d — IFRS 13 Fair Value Adapter

**File:** `core_engine/engines/purpose/ifrs13.py`

### Definition (IFRS 13, paragraph 9)

> The price that would be received to sell an asset or paid to transfer a liability in an
> **orderly transaction** between market participants at the measurement date.

### Fair Value Hierarchy

| Level | Observable inputs | Applied when |
|-------|------------------|-------------|
| Level 1 | Quoted prices in active markets | Exchange-listed REITS, securitised real estate |
| Level 2 | Observable inputs other than Level 1 | Comparable sales transactions, yield curves |
| Level 3 | Unobservable inputs | Specialised assets, no comparable transactions |

### Level classification logic

```python
def classify_level(engine_results, property_context) -> str:
    comp = engine_results.get("comparative")
    if comp and comp.metadata.get("comparable_count", 0) >= 5:
        return "level_2"   # sufficient observable comparable evidence
    elif comp and comp.metadata.get("comparable_count", 0) >= 1:
        return "level_2"   # some observable evidence
    elif engine_results.get("income") and engine_results["income"].value:
        return "level_3"   # income only — internally developed cap rate
    else:
        return "level_3"   # cost only or insufficient data
```

Level 1 is reserved for publicly traded real estate instruments — not in scope for this platform.

### Risk adjustments

IFRS 13 paragraph 88 requires that **risk inherent in unobservable inputs** be reflected.
For Level 3 valuations, the adapter applies a **risk adjustment factor**:

| Risk factor | Default adjustment |
|------------|-------------------|
| Illiquid market (CV > 0.30) | −3% |
| Thin comparables (n < 3) | −5% |
| High vacancy (>30%) | −4% |
| Distressed property flag | −8% |

Risk adjustments are cumulative (not capped by default) but each is individually audited.

### Disclosure fields added to metadata

```json
{
    "ifrs13_level":            "level_2",
    "ifrs13_level_rationale":  "5 observable comparable transactions used",
    "ifrs13_risk_adjustments": [
        {"factor": "CV > 0.30", "adjustment_pct": -3.0, "applied": true}
    ],
    "measurement_date":        "2026-05-07",
    "market_participant_basis": true,
    "orderly_transaction":      true
}
```

### `egvs_section` → `"EGVS_7.1: IFRS 13 Fair Value Disclosure"`

---

## Task 5.3 — Weighted Reconciliation Engine (composite route)

**File:** `core_engine/engines/reconciliation.py`

This engine is called **before** the purpose adapter. It:

1. Runs all three Phase 4 engines (or accepts pre-run results)
2. Applies appraiser weights
3. Validates that weights sum to 1.0
4. Re-normalises if any engine returned `None`
5. Returns `ReconciliationResult` for the purpose adapter to consume

### Weight presets (used when `weights` is omitted from the request)

```python
WEIGHT_PRESETS = {
    "residential_owner_occupied": {"comparative": 0.60, "cost": 0.25, "income": 0.15},
    "residential_rental":          {"comparative": 0.30, "cost": 0.20, "income": 0.50},
    "commercial":                  {"comparative": 0.25, "cost": 0.15, "income": 0.60},
    "industrial":                  {"comparative": 0.20, "cost": 0.50, "income": 0.30},
    "land":                        {"comparative": 0.70, "cost": 0.30, "income": 0.00},
    "special_purpose":             {"comparative": 0.10, "cost": 0.70, "income": 0.20},
}
```

Preset is selected via `property_context.property_category`.

---

## Task 5.4 — Flask Integration (one new composite route)

**File:** `core_engine/bridge_api.py` (minimal addition)

### New route: `POST /api/valuation/full`

This is the Phase 5 "one-stop" endpoint. It orchestrates:

1. Run comparable search (optional — if `run_search: true`)
2. Run all three engines
3. Reconcile with weights
4. Apply purpose adapter
5. Return unified response

### Request schema

```json
{
    "valuation_purpose": "market_value",
    "property_category": "residential_owner_occupied",

    "subject_property": {
        "area_sqm":        120,
        "age_years":       2,
        "finishing_level": "finished",
        "governorate":     "Cairo"
    },

    "comparables": [
        {"id": "BS-00-1480", "area_sqm": 120.9, "price_egp": 2190144.0, "age_years": 2},
        {"id": "BS-03-1231", "area_sqm": 121.4, "price_egp": 5857468.0, "age_years": 2},
        {"id": "BS-07-0825", "area_sqm": 120.0, "price_egp": 2798977.0, "age_years": 2},
        {"id": "BS-00-0943", "area_sqm": 118.2, "price_egp": 5867856.0, "age_years": 5},
        {"id": "BS-03-1155", "area_sqm": 119.4, "price_egp": 3643309.0, "age_years": 5}
    ],

    "cost_inputs": {
        "building_area_sqm":    120,
        "building_age_years":   2,
        "construction_quality": "standard",
        "land_value_egp":       1000000
    },

    "income_inputs": {
        "gross_income_annual_egp":  240000,
        "vacancy_rate":             0.10,
        "operating_expenses_ratio": 0.35,
        "cap_rate":                 0.10,
        "cap_rate_source":          "market"
    },

    "weights": {
        "comparative": 0.60,
        "cost":        0.25,
        "income":      0.15
    },

    "purpose_context": {
        "loan_amount_egp": 3000000,
        "ltv_limit_pct":   0.80
    }
}
```

`valuation_purpose` accepted values:
- `"market_value"` (default)
- `"mortgage_value"`
- `"insurance_value"`
- `"ifrs13_fair_value"`

### Response schema

```json
{
    "status": "success",
    "valuation_purpose": "market_value",
    "final_value": 3280078.00,
    "confidence": "high",
    "ifrs13_level": "level_2",
    "ifrs13_rationale": "5 observable comparable transactions used",

    "engine_results": {
        "comparative": { "value": 4022462.78, "confidence": "high" },
        "cost":        { "value": 2624000.00, "confidence": "high" },
        "income":      { "value": 1404000.00, "confidence": "high" }
    },

    "reconciliation": {
        "weights_used":      {"comparative": 0.60, "cost": 0.25, "income": 0.15},
        "weight_rationale":  "Residential owner-occupied preset",
        "reconciled_value":  3280078.00,
        "pre_purpose_value": 3280078.00,
        "adjustment_pct":    0.0,
        "adjustment_reason": "Market value: no purpose adjustment applied"
    },

    "audit_trail": [
        { "step_name": "Run ComparativeEngine",    ... },
        { "step_name": "Run CostEngine",           ... },
        { "step_name": "Run IncomeEngine",         ... },
        { "step_name": "Reconcile (weighted mean)", ... },
        { "step_name": "Apply MarketValueAdapter", ... },
        { "step_name": "IFRS 13 level classification", ... }
    ],

    "issues": [],
    "metadata": {
        "egvs_section":      "EGVS_1.1",
        "measurement_date":  "2026-05-07",
        "comparable_count":  5,
        "per_sqm":           33520.52,
        "indicative_range":  [2952070, 3608085]
    }
}
```

---

## Task 5.5 — EgVS Report Skeleton

**File:** `core_engine/engines/egvs_report.py`

Builds a structured report dictionary from a `PurposeResult`, ready for PDF or Word rendering.

### Report sections

| Section | EGVS Ref | Content |
|---------|---------|---------|
| Cover page | — | Property address, valuation date, purpose, appraiser |
| Property description | EGVS 2.1 | Area, age, quality, location |
| Market overview | EGVS 2.2 | Comparable count, price range, CV |
| Comparable analysis | EGVS 3.x | Adjustment grid (all 22 audit entries) |
| Cost approach | EGVS 4.x | RCN, depreciation table |
| Income approach | EGVS 5.x | EGI waterfall, cap rate justification |
| Reconciliation | EGVS 6.1 | Weights, rationale, reconciled value |
| Purpose adjustment | EGVS 6.2 | Adapter-specific section |
| IFRS 13 disclosure | EGVS 7.1 | Level, rationale, risk adjustments |
| Final value | EGVS 8.1 | Final value, confidence band, limitations |
| Appraiser declaration | EGVS 9.1 | Independence, qualifications, date |

### Output format

Returns a Python `dict` that can be serialised to JSON (for API consumers) or passed to a
Jinja2/WeasyPrint template for PDF generation in a future phase.

---

## API surface summary (Phase 5 additions)

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/valuation/full` | Composite: all 3 engines + reconciliation + purpose adapter |

Existing Phase 4 routes (`/api/engines/comparative`, `/api/engines/cost`,
`/api/engines/income`, `/api/comparables/search`) are **unchanged** — available for
standalone engine calls.

---

## IFRS 13 Compliance Matrix

| IFRS 13 Requirement | Where implemented |
|--------------------|------------------|
| Fair value definition (para. 9) | `ifrs13.py` — docstring + metadata |
| Market participant basis (para. 22) | `ifrs13.py` — `market_participant_basis: true` |
| Orderly transaction (para. 15) | `ifrs13.py` — `orderly_transaction: true` |
| Highest and best use (para. 27) | `purpose/base.py` — `hbu_assumed: true` field |
| Fair Value Hierarchy classification (para. 72–90) | `ifrs13.py` — `classify_level()` |
| Level 3 risk adjustment (para. 88) | `ifrs13.py` — `_apply_risk_adjustments()` |
| Disclosure requirements (para. 91–99) | `egvs_report.py` — IFRS 13 disclosure section |
| Measurement date | All adapters — `measurement_date` in metadata |

---

## EgVS Compliance Matrix (Phase 5 additions)

| EGVS Section | Coverage | Implemented in |
|-------------|---------|---------------|
| EGVS 1.1 | Market Value definition | `market_value.py` |
| EGVS 2.1–2.2 | Property description + market overview | `egvs_report.py` |
| EGVS 3.x | Sales Comparison (full grid) | Phase 4 `comparative.py` + report |
| EGVS 4.x | Cost Approach | Phase 4 `cost.py` + report |
| EGVS 5.x | Income Approach | Phase 4 `income.py` + report |
| EGVS 6.1 | Reconciliation | `reconciliation.py` |
| EGVS 6.2 | Purpose adjustment | Purpose adapters |
| EGVS 6.3 | Collateral / Mortgage value | `mortgage_value.py` |
| EGVS 7.1 | IFRS 13 Fair Value | `ifrs13.py` |
| EGVS 8.1 | Final value + confidence band | Composite route response |
| EGVS 9.1 | Appraiser declaration | `egvs_report.py` (static fields) |

---

## Implementation task sequence

```
Task 5.0 — ReconciliationEngine           (reconciliation.py)
    └── depends on: Phase 4 EngineResult

Task 5.1 — PurposeAdapter ABC             (purpose/base.py)
    └── depends on: Task 5.0 ReconciliationResult

Task 5.2a — MarketValueAdapter            (purpose/market_value.py)
Task 5.2b — MortgageValueAdapter          (purpose/mortgage_value.py)
Task 5.2c — InsuranceValueAdapter         (purpose/insurance_value.py)
Task 5.2d — IFRS13FairValueAdapter        (purpose/ifrs13.py)
    └── all depend on: Task 5.1 PurposeAdapter ABC
    └── Tasks 5.2a–d can be built in parallel

Task 5.3 — Flask route /api/valuation/full (bridge_api.py)
    └── depends on: Tasks 5.0, 5.1, 5.2a–d

Task 5.4 — EgVS Report Skeleton           (egvs_report.py)
    └── depends on: Task 5.3 (uses PurposeResult shape)

Task 5.5 — End-to-end testing             (tests)
    └── depends on: all above
```

---

## Lessons from Phase 4 (applied to Phase 5 design)

| Phase 4 lesson | Phase 5 design decision |
|---------------|------------------------|
| Audit trail is CRITICAL — every step must be logged | `ReconciliationEngine` and all adapters produce `AuditEntry` objects; no silent calculations |
| Weight reconciliation must be explicit, not implicit | `weights_used` and `weight_rationale` are first-class fields in the response |
| Three engines need explicit weighting | `WEIGHT_PRESETS` by property category; re-normalisation logged when engine returns `None` |
| Import paths must be package-relative for server CWD | New `engines/purpose/` package uses `from ..base import ...` |
| JSON file paths must use `os.path.join(_BASE, ...)` | No hardcoded relative paths in any Phase 5 file |
| Singleton getter pattern for expensive initialisation | `get_reconciliation_engine()`, `get_purpose_adapter(purpose)` in `bridge_api.py` |
| Graceful errors — HTTP 200 with structured `issues` | All adapters: validation errors → `PurposeResult` with `value=None`, no 500s |

---

## Known constraints and open questions

| # | Item | Decision needed |
|---|------|----------------|
| C1 | LTV limit source | Hardcode CBE 80%? Or accept per-request? Recommend: accept per-request with 80% default |
| C2 | IFRS 13 Level 1 | No real estate is Level 1 in the Egyptian market — exclude from classification logic |
| C3 | Insurance inflation rate | 15% default chosen; must be revisited annually — recommend config file |
| C4 | PDF generation | Out of scope for Phase 5 — `egvs_report.py` returns `dict` only; PDF is Phase 6 |
| C5 | Multi-currency | All values in EGP; FX conversion is out of scope |
| C6 | Depreciation methods | Phase 4 uses straight-line only; observed market uses age/life for residential — acceptable |
| C7 | `D2 — /api/image/geo-analyze`| Still deferred from DEFERRED_ITEMS.md; Phase 5 does not touch image routes |

---

## Phase 6 candidates (out of scope for Phase 5)

1. **PDF / Word report generation** — Jinja2 + WeasyPrint rendering of `egvs_report.py` output
2. **DCF engine** — Discounted Cash Flow for multi-period income projections
3. **Sensitivity analysis** — tornado charts showing value impact of ±10% on each assumption
4. **Basel III LTV dashboard** — portfolio-level mortgage value monitoring
5. **Mass appraisal integration** — pipe Phase 5 `final_value` into existing mass appraisal module
6. **Automated cap rate derivation** — extract implied cap rate from `market_feed.json` transactions
7. **GPS enrichment** — resolve D1 from DEFERRED_ITEMS.md; enable true distance scoring

---

## Baseline values for Phase 5 testing

From Phase 4 end-to-end tests (2026-05-07, commit 7b1e1f2):

| Approach | Value (EGP) | Confidence |
|----------|------------|-----------|
| Comparative | 4,022,462.78 | high |
| Cost | 2,624,000.00 | high |
| Income | 1,404,000.00 | high |
| Weighted (60/25/15) | 3,280,078.00 | high |
| Indicative range (±10%) | 2,952,070 – 3,608,085 | — |

These values must be reproduced by `POST /api/valuation/full` with the same inputs as
Phase 4 tests, before Phase 5 is considered passing.

---

**Status:** Draft — awaiting Phase 4 closure sign-off before Phase 5 implementation begins.  
**Author:** Hisham Elmahdy  
**Date:** 2026-05-07
