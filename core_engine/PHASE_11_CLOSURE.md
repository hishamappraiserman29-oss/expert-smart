# Phase 11 — Portfolio Analysis — FINAL CLOSURE

**Status:** COMPLETE (100%)
**Date:** 2026-05-08
**Final Test Count:** 25 tests (16 unit/integration + 9 E2E — all passing)

---

## Executive Summary

Phase 11 extended Expert Smart from single-property appraisals (Phases 3–10) to
institutional-grade portfolio analysis. Clients can now submit a collection of
pre-valued properties and receive aggregated metrics, stress-scenario analysis,
and a two-sheet Excel report — all through a single API call.

---

## Task Ledger

| Task | Deliverable | Tests | Status |
|------|-------------|-------|--------|
| 11.0 | Portfolio framework (PortfolioBuilder, AggregateMetrics, PropertyInPortfolio) | 10 | DONE |
| 11.1 | Portfolio Summary Excel sheet + POST /api/valuation/portfolio | 8 | DONE |
| 11.2 | Performance analysis (PortfolioPerformanceAnalyzer, stress scenarios) | 12 | DONE |
| 11.3 | Portfolio Performance Excel sheet + build() integration | 16 | DONE |
| 11.4 | E2E test suite (test_phase_11_complete.py, 9 tests) | 9 | DONE |
| 11.5 | Phase 11 closure documentation | — | DONE |

---

## What Was Delivered

### Task 11.0 — Portfolio Framework

**File:** `core_engine/adapters/portfolio.py` (215 lines)

**Classes:**

`PropertyInPortfolio` — wraps one property in portfolio context:
- `property_id`, `property_name`, `property_type`
- `valuation_value`, `valuation_confidence` (high / medium / low)
- `annual_noi`, `annual_gross_income`
- `portfolio_weight`, `contribution_to_return` (computed on demand)

`AggregateMetrics` — 15-field dataclass:
- Totals: `total_portfolio_value`, `number_of_properties`, `total_annual_noi`, `total_annual_gross_income`
- Income: `portfolio_noi_margin`, `portfolio_cap_rate`
- Diversification: `value_by_type`, `type_percentages`, `concentration_ratio`, `herfindahl_index`
- Confidence: `high/medium/low_confidence_count`, `high_confidence_value`

`PortfolioBuilder` — chainable API:
- `add_property(...)` → returns self
- `calculate_metrics()` → populates AggregateMetrics + propagates weights
- `get_portfolio_summary()` → JSON-serialisable dict
- `get_diversification_score()` → 1 − HHI

**Key metric identities verified by tests:**
- `sum(portfolio_weight) == 1.0` for any property count
- `HHI == 0.5` for equal two-property portfolio
- `concentration_ratio == largest_value / total_value`
- `portfolio_cap_rate == total_noi / total_value`

---

### Task 11.1 — Portfolio Reporting

**Files modified:**
- `core_engine/reports/excel_builder.py` — `sheet_portfolio_summary()` added; `__init__` made `result: Optional = None`; `build()` gains `portfolio_summary=None`
- `core_engine/bridge_api.py` — `POST /api/valuation/portfolio` route

**Excel sheet "Portfolio Summary" (6 sections):**
1. Portfolio Overview (name, total value, property count, cap rate)
2. Value Distribution by Type
3. Income Analysis (gross income, NOI, margin)
4. Risk & Diversification (concentration ratio, HHI, diversification score)
5. Valuation Confidence (high/medium/low counts and values)
6. Property Listing (all properties with weight %)

**API response shape:**
```json
{
  "status": "success",
  "portfolio": { "portfolio_name": "...", "metrics": {...}, "properties": [...] },
  "diversification_score": 0.7652,
  "report_id": "<uuid>",
  "download_url": "/api/valuation/report/download/<uuid>.xlsx",
  "timestamp": "2026-05-08T..."
}
```

---

### Task 11.2 — Performance Analysis

**File:** `core_engine/adapters/portfolio_performance.py` (175 lines)

**Classes:**

`PortfolioScenario` — named shock parameters:
- `noi_shock` (multiplier, e.g. 0.80 = −20%)
- `value_shock` (multiplier, e.g. 0.85 = −15%)
- `cap_rate_shift` (additive, e.g. +0.01 = +100 bps)

Standard presets via `create_standard_scenarios()`:
- pessimistic: noi_shock=0.80, value_shock=0.85, cap_rate_shift=+0.01
- base: no change
- optimistic: noi_shock=1.15, value_shock=1.10, cap_rate_shift=−0.005

`ScenarioResult` — computed per scenario:
- `stressed_portfolio_value`, `stressed_total_noi`, `stressed_cap_rate`, `stressed_noi_margin`
- `value_change_pct`, `noi_change_pct` (relative to base)
- `irr_estimate` (stressed cap rate + 5% assumed growth)
- `diversification_score`

`PortfolioPerformanceAnalyzer` — orchestrator:
- `add_scenario()` / `create_standard_scenarios()` — chainable
- `run_scenarios()` — computes and caches all results
- `get_performance_summary()` — full dict including:
  - `min/max_stressed_value`, `min/max_stressed_noi`
  - `value_at_risk_pct` (base − worst-case) / base

**API endpoint:** `POST /api/valuation/portfolio/performance`
- `use_standard_scenarios: true` — applies pessimistic/base/optimistic
- `scenarios: [...]` — custom scenario list
- Returns `performance_analysis` dict with all scenario results

**Verified invariants:**
- pessimistic value < base value < optimistic value
- All IRR estimates > 0
- `value_at_risk_pct` ∈ (0, 1) when any downside scenario exists
- base scenario: `value_change_pct == 0`, `noi_change_pct == 0`

---

### Task 11.3 — Performance Excel Sheet

**File modified:** `core_engine/reports/excel_builder.py`

**Method:** `sheet_portfolio_performance(self, perf: Dict) -> None`

**Sheet "Portfolio Performance" (3 sections):**
1. Baseline Metrics — portfolio name, base value, NOI, cap rate, diversification score, scenario count
2. Scenario Comparison Table — 8 columns per scenario row: Scenario | Stressed Value | Value Δ% | Stressed NOI | NOI Δ% | Stressed Cap Rate | NOI Margin | IRR Estimate
3. Risk Summary — min/max stressed value, min/max stressed NOI, Scenario-Implied Downside %

**Design decisions:**
- Empty scenarios → "No scenario data available" merged cell (does not crash)
- Missing conditional keys (`value_at_risk_pct`, etc.) render as "—" (does not crash)
- Uses `_FILL_PORTFOLIO` (203864 navy) for section titles matching Portfolio Summary
- Uses `_FILL_PORT_COL` (D9E1F2 light blue) for table column headers
- Label "Scenario-Implied Downside %" used instead of statistical VaR language

`build()` signature after Phase 11:
```python
def build(self, filename: str,
          ivsc_disclosure=None,
          cross_border_disclosure=None,
          portfolio_summary=None,
          portfolio_performance=None) -> str
```
All parameters optional — no existing callers broken.

---

### Tasks 11.4–11.5 — E2E Tests + Closure

**File:** `core_engine/tests/test_phase_11_complete.py` (9 tests)

| Test | What it verifies |
|------|-----------------|
| `test_e2e_portfolio_build_and_analyze` | 5-property build, exact totals, diversification > 0 |
| `test_e2e_api_portfolio_endpoint` | POST 200, exact total value, diversification_score key |
| `test_e2e_api_portfolio_with_report` | report_id and download_url both non-null |
| `test_e2e_portfolio_vs_phase_4_income` | cap rate identity: NOI / value == portfolio_cap_rate |
| `test_e2e_property_weights` | sum of weights == 1.0 |
| `test_e2e_confidence_distribution` | high/medium/low counts + high_confidence_value |
| `test_e2e_diversification_metrics` | HHI == 0.5 for equal-weight two-property portfolio |
| `test_e2e_type_distribution` | value_by_type and type_percentages exact values |
| `test_e2e_concentration_ratio` | 80/20 portfolio → concentration_ratio == 0.80 |

---

## Architecture (Phase 11 Complete)

```
POST /api/valuation/portfolio
POST /api/valuation/portfolio/performance
        │
        ▼
PortfolioBuilder ──► PropertyInPortfolio × N
        │                    │
        │            calculate_metrics()
        │                    │
        ▼                    ▼
AggregateMetrics     portfolio_weight (per property)
(HHI, cap_rate,      contribution_to_return
 concentration, …)
        │
        ▼
PortfolioPerformanceAnalyzer
        │
        ├── PortfolioScenario × N (pessimistic / base / optimistic / custom)
        │
        ▼
ScenarioResult × N
(stressed_value, stressed_noi, stressed_cap_rate,
 value_change_pct, noi_change_pct, irr_estimate,
 diversification_score)
        │
        ▼
ExcelReportBuilder
  ├── sheet_portfolio_summary()    → "Portfolio Summary" sheet
  └── sheet_portfolio_performance() → "Portfolio Performance" sheet
```

---

## Test Count Summary

| File | Tests | Result |
|------|-------|--------|
| `test_phase_11_e2e.py` (Tasks 11.0–11.3) | 16 | 16/16 PASS |
| `test_phase_11_complete.py` (Task 11.4) | 9 | 9/9 PASS |
| **Phase 11 total** | **25** | **25/25** |

Cumulative passing tests across all phases: **~382+**

---

## Files Changed in Phase 11

| File | Change type |
|------|-------------|
| `core_engine/adapters/portfolio.py` | Created (Task 11.0) |
| `core_engine/adapters/portfolio_performance.py` | Created (Task 11.2) |
| `core_engine/reports/excel_builder.py` | Modified — 3 additions: `__init__` optional result, `sheet_portfolio_summary`, `sheet_portfolio_performance`; `build()` extended twice |
| `core_engine/bridge_api.py` | Modified — 2 routes added: `POST /api/valuation/portfolio`, `POST /api/valuation/portfolio/performance` |
| `core_engine/tests/test_phase_11_e2e.py` | Created (Tasks 11.0–11.3 unit tests) |
| `core_engine/tests/test_phase_11_complete.py` | Created (Task 11.4 E2E tests) |
| `core_engine/PHASE_11_CLOSURE.md` | Created (this file) |

---

## No-Touch Zones (respected throughout)

- `core_engine/engines/` — not opened
- `core_engine/adapters/base.py`, `market_value.py`, `mortgage.py`, `insurance.py`, `ifrs_13.py` — not opened
- `core_engine/adapters/residential.py`, `commercial.py`, `land.py` — not opened
- `core_engine/adapters/dcf_model.py`, `dcf_sensitivity.py`, `ivsc.py`, `cross_border.py` — not opened
- `core_engine/database/` — not opened
- All existing API response shapes — unchanged

---

## Critical Notes for Next Phase

- `bridge_api.py` is now ~8,250+ lines — always syntax-check after editing:
  ```powershell
  python -c "import ast, pathlib; ast.parse(pathlib.Path('core_engine/bridge_api.py').read_text(encoding='utf-8'))"
  ```
- All Phase 5–11 work is **uncommitted**. Git only has Phase 4 commits on `main`.
- `ExcelReportBuilder()` can now be called with no arguments (portfolio-only mode).
- `build()` parameter order: `filename, ivsc_disclosure, cross_border_disclosure, portfolio_summary, portfolio_performance` — always use keyword args when calling.
- `get_performance_summary()` conditional keys (`min/max_stressed_value`, `value_at_risk_pct`) are absent when `scenarios == []` — sheet builder handles this gracefully.

---

## Suggested Next Phase

**Phase 12 — Batch Valuation API**
- `POST /api/valuation/batch` — accept an array of individual valuation requests
- Process each through the existing Phase 4–7 engines
- Return an array of results + summary statistics
- Optional: generate one combined Excel workbook with one sheet per property
