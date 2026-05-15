# Phase 6 — Asset Adapters + Excel Report Generation

## Overview

Phase 4 delivered 3 core valuation engines (generic — work for any property type).  
Phase 5 delivered 5 purpose adapters (generic — mortgage, insurance, market value, IFRS 13).  
Phase 6 adds the **Asset Layer** — property-type-specific logic that sits above both.

### What Phase 6 delivers

1. **AssetAdapter base class** — abstract interface for property-type specialisation
2. **ResidentialAdapter** — apartments, villas, townhouses (owner-occupied + rental)
3. **CommercialAdapter** — offices, retail units, mixed-use (yield-driven)
4. **Custom weight presets** — 80/15/5 residential owner-occupied; 30/20/50 commercial
5. **Excel report generation** — audit trail → formatted `.xlsx` (court-grade valuation report)
6. **Walking skeleton** — single request produces a downloadable valuation report
7. **EgVS full compliance** — all 11 EGVS sections populated in the report

### Architecture shift from Phase 5

**Phase 5 (Purpose Layer — generic):**

```
POST /api/valuation/full
        │
        ├─→ ComparativeEngine  ─┐
        ├─→ CostEngine           ├─→ three_values dict
        └─→ IncomeEngine        ─┘
                    │
             PurposeAdapter (selected by valuation_purpose)
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
 MarketValue   Mortgage     Insurance
 Adapter       Adapter      Adapter
                    │
              PurposeResult (final value + audit)
```

**Phase 6 (Asset Layer — sits above Purpose Layer):**

```
POST /api/valuation/report
        │
        ├─→ ComparableSearchEngine  →  ranked comparables
        ├─→ ComparativeEngine       ─┐
        ├─→ CostEngine               ├─→ three_values dict
        └─→ IncomeEngine            ─┘
                    │
           AssetAdapter (selected by property_type)
           ┌──────────────────────────────────────┐
           │  ResidentialAdapter / CommercialAdapter│
           │  • property-type weights              │
           │  • applicable purpose list            │
           │  • type-specific validation rules     │
           └─────────────────┬────────────────────┘
                             │ calls selected PurposeAdapters
                    ┌────────┴────────┐
                    ▼                 ▼
             MarketValueAdapter  MortgageAdapter ...
                    │
           AssetValuationResult
           (all purpose values + full audit trail)
                    │
           ExcelReportBuilder
                    │
           valuation_report.xlsx   ←  downloadable
```

The caller sends **one request** — property data + type + purpose — and receives both
a JSON response (same as Phase 5) **and** a formatted Excel report with the full audit
trail, all EGVS section disclosures, and a signature block for the appraiser.

---

## Directory layout (new files only)

```
core_engine/
├── asset_adapters/              ← NEW package (Phase 6)
│   ├── __init__.py              ← exports base + concrete adapters
│   ├── base.py                  ← AssetAdapter ABC + AssetValuationResult
│   ├── residential.py           ← ResidentialAdapter (Task 6.1)
│   └── commercial.py            ← CommercialAdapter  (Task 6.2)
│
├── reports/                     ← NEW package (Phase 6)
│   ├── __init__.py
│   ├── excel_builder.py         ← ExcelReportBuilder (Task 6.3)
│   ├── templates/
│   │   ├── valuation_report.xlsx  ← master template (styled headers, logos)
│   │   └── egvs_sections.json     ← EGVS section text for auto-population
│   └── output/                  ← generated reports (gitignored)
│
└── bridge_api.py                ← add 1 new route: POST /api/valuation/report
```

No existing files in `adapters/`, `engines/`, or existing routes are modified.

---

## Task 6.0 — AssetAdapter Base Class

**File:** `core_engine/asset_adapters/base.py`

### Purpose

Defines the abstract contract that every asset-type adapter must satisfy.
An AssetAdapter knows:
- Which `PurposeAdapter`s are applicable for this property type
- What weight presets to use per purpose
- What property-type-specific validation to perform
- How to enrich the final result with asset-specific metadata

### Abstract interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from adapters.base import PurposeResult, ValidationIssue


@dataclass
class AssetValuationResult:
    asset_type:         str                        # "residential" | "commercial" | ...
    property_subtype:   str                        # "apartment" | "villa" | "office" | ...
    three_values: dict[str, Decimal]               # raw Phase 4 engine values
    purpose_results: dict[str, PurposeResult]      # keyed by purpose name
    primary_value:      Decimal                    # recommended value (asset-specific)
    primary_purpose:    str                        # which purpose drove primary value
    confidence:         str                        # aggregated across all purposes
    egvs_sections: dict[str, str]                  # section code → narrative text
    report_metadata: dict                          # appraiser, date, property address...
    issues: list[ValidationIssue] = field(default_factory=list)


class AssetAdapter(ABC):
    """
    Abstract base for property-type-specific valuation logic.
    Sits above PurposeAdapters — selects which purposes apply and
    with what weights, then delegates to the Phase 5 layer.
    """

    asset_type:    str = "base"
    version:       str = "0.0.0"

    # Subclasses declare which purposes apply and their weight presets
    applicable_purposes: list[str] = []
    weight_presets: dict[str, dict] = {}   # purpose → weights dict

    @abstractmethod
    def validate_property(self, property_data: dict) -> list[ValidationIssue]:
        """Type-specific validation (area ranges, age limits, etc.)"""
        ...

    @abstractmethod
    def select_primary_value(
        self,
        purpose_results: dict[str, PurposeResult],
        property_data: dict,
    ) -> tuple[Decimal, str]:
        """Return (primary_value, primary_purpose_name) for this asset type."""
        ...

    @abstractmethod
    def build_egvs_sections(
        self,
        result: AssetValuationResult,
        property_data: dict,
    ) -> dict[str, str]:
        """Return dict mapping EGVS section code → populated narrative text."""
        ...

    def value(
        self,
        three_values: dict,
        property_data: dict,
        requested_purposes: list[str] | None = None,
    ) -> AssetValuationResult:
        """
        Orchestrates purpose adapters, builds result, populates EGVS sections.
        Concrete subclasses normally do NOT override this method.
        """
        ...
```

### `AssetValuationResult` fields

| Field | Type | Description |
|---|---|---|
| `asset_type` | str | "residential", "commercial" |
| `property_subtype` | str | "apartment", "villa", "office", "retail" |
| `three_values` | dict | raw Phase 4 values (comp, cost, income) |
| `purpose_results` | dict | PurposeResult per adapter |
| `primary_value` | Decimal | recommended value for this asset type |
| `primary_purpose` | str | which purpose drove the primary value |
| `confidence` | str | lowest confidence across all purposes (conservative) |
| `egvs_sections` | dict | section code → populated narrative |
| `report_metadata` | dict | appraiser, date, address, reference number |
| `issues` | list | aggregated warnings from all adapters |

---

## Task 6.1 — ResidentialAdapter

**File:** `core_engine/asset_adapters/residential.py`

### Rationale

Residential is the dominant transaction type in the Egyptian market. Owner-occupiers
pay market price and do not capitalise income, so the **Comparative Approach** is
heavily weighted. Cost provides a floor (replacement cost signals over/under-building);
Income is rarely the primary signal for owner-occupied units.

For **rental residential**, income becomes more significant (investor perspective) and
weights shift toward the income approach.

### Property subtypes

| Subtype | Arabic | Notes |
|---|---|---|
| `apartment` | شقة سكنية | Most common — weight preset A |
| `villa` | فيلا | Standalone; land component significant |
| `townhouse` | تاون هاوس | Compound; comp approach dominant |
| `duplex` | دوبلكس | Like villa but less land |
| `studio` | ستوديو | Micro-unit; comp dominant |
| `penthouse` | بنتهاوس | Premium tier; fewer comparables |

### Weight presets

| Use case | Comparative | Cost | Income | Trigger |
|---|---|---|---|---|
| Owner-occupied (default) | **80%** | 15% | 5% | `occupancy == "owner"` |
| Rental residential | **50%** | 20% | 30% | `occupancy == "rental"` |
| Low-comp (< 3 comps) | **40%** | 40% | 20% | `comparable_count < 3` |

### Applicable purposes

- `market_value` (primary — always run)
- `mortgage` (run when `borrower_profile` is provided)
- `insurance` (run when `building_age_years` is provided)
- `ifrs_13` (run when `cap_rate_source` is provided or explicitly requested)

### Primary value selection rule

```
primary_value = market_value.adjusted_value
primary_purpose = "market_value"
```

Residential primary value is always Market Value (EGVS 2.0 definition).
All other purposes are supplementary disclosures.

### Validation rules

| Rule | Severity | Condition |
|---|---|---|
| Area must be > 0 | error | `area_sqm <= 0` |
| Area sanity ceiling | warning | `area_sqm > 1000` (unusually large apartment) |
| Age must be >= 0 | error | `age_years < 0` |
| Age ceiling | warning | `age_years > 80` (structural risk) |
| Subtype must be known | warning | subtype not in list above |
| Comparable floor | warning | `comparable_count < 3` |

### Property-specific EGVS narratives

The adapter auto-populates these EGVS sections with property-specific text:

| Section | Content |
|---|---|
| EGVS 1 — Scope | Property type, subject details, inspection date |
| EGVS 2 — Assumptions | Owner-occupied / rental assumption, area measurement basis |
| EGVS 3 — Market Analysis | Comparable count, price-per-sqm range, location premium |
| EGVS 4 — Valuation Approach | Why comparative is primary; cost as cross-check |
| EGVS 5 — Reconciliation | Weight rationale; final value derivation |
| EGVS 6 — Conclusion | Final value, confidence, effective date |

### Key metadata output

```python
metadata = {
    "subtype":              "apartment",
    "occupancy":            "owner",
    "weight_preset":        "owner_occupied",
    "area_sqm":             120,
    "age_years":            5,
    "price_per_sqm":        33_000,        # final value / area
    "comparable_count":     5,
    "location_tier":        "prime",       # prime / secondary / peripheral
    "egvs_compliance":      True,
    "ifrs13_hierarchy":     "Level 2",
}
```

---

## Task 6.2 — CommercialAdapter

**File:** `core_engine/asset_adapters/commercial.py`

### Rationale

Commercial real estate in Egypt is yield-driven. Investors acquire offices, retail
units, and mixed-use properties primarily based on Net Operating Income and
capitalisation rates. The **Income Approach** dominates; Comparative provides
market evidence; Cost is used as a sanity check or when market evidence is thin.

### Property subtypes

| Subtype | Notes |
|---|---|
| `office` | Grade A/B; NOI-driven |
| `retail` | Street retail or mall unit; footfall-linked |
| `showroom` | Car or furniture showroom; large area |
| `warehouse` | Industrial-adjacent; cost approach strong |
| `mixed_use` | Residential + commercial floors |

### Weight presets

| Use case | Comparative | Cost | Income | Trigger |
|---|---|---|---|---|
| Standard commercial (default) | 30% | 20% | **50%** | default |
| Thin market (< 3 comps) | 20% | 30% | **50%** | `comparable_count < 3` |
| New construction | 20% | **50%** | 30% | `age_years <= 2` |
| Industrial / warehouse | 20% | **55%** | 25% | `subtype == "warehouse"` |

### Applicable purposes

- `market_value` (always run)
- `mortgage` (run when `borrower_profile` provided; CBE rules apply)
- `insurance` (always run — replacement cost for buildings)
- `ifrs_13` (run when explicitly requested or `cap_rate_source` provided)

### Primary value selection rule

```
IF income engine confidence == "high" AND comparable_count >= 3:
    primary_value  = market_value.adjusted_value   # reconciled, income-weighted
    primary_purpose = "market_value"
ELSE:
    primary_value  = market_value.adjusted_value   # fall back to reconciled
    primary_purpose = "market_value"
    issues.append(WARNING — "thin market: income approach confidence low")
```

Market Value (reconciled with income-heavy weights) is always the primary value.
The income weight is embedded in the reconciliation, not a separate override.

### Validation rules

| Rule | Severity | Condition |
|---|---|---|
| Area must be > 0 | error | `area_sqm <= 0` |
| Cap rate required | warning | `cap_rate` not provided (income engine will use default) |
| Annual income required | warning | `gross_income_annual_egp` not provided |
| Age ceiling | warning | `age_years > 50` |
| Subtype must be known | warning | subtype not in list above |

---

## Task 6.3 — ExcelReportBuilder

**File:** `core_engine/reports/excel_builder.py`

### Purpose

Transforms an `AssetValuationResult` into a formatted Excel workbook that satisfies
Egyptian court requirements and client-facing valuation report standards.
Uses `openpyxl` (already in requirements).

### Report structure (sheets)

| Sheet | Contents |
|---|---|
| **Cover** | Property photo placeholder, appraiser details, effective date, reference number |
| **Summary** | One-page executive: all purpose values, primary recommendation, confidence |
| **Three Approaches** | Phase 4 engine values with mini audit trail per approach |
| **Purpose Valuations** | One section per purpose adapter (market, mortgage, insurance, IFRS 13) |
| **Comparable Evidence** | All ranked comparables, similarity scores, adjustments applied |
| **Audit Trail** | Complete step-by-step log (Phase 4 + Phase 5 + Phase 6 entries) |
| **EGVS Compliance** | All 11 EGVS sections populated with property-specific text |
| **Appraiser Sign-off** | Certification text, signature line, stamp placeholder |

### Styling conventions

| Element | Style |
|---|---|
| Header rows | Dark navy fill (#1F3864), white bold text, 12pt |
| Sub-headers | Light blue fill (#D6E4F7), dark text, 11pt |
| Value cells | Right-aligned, number format `#,##0.00 "EGP"` |
| Percentage cells | Format `0.00%` |
| Confidence: high | Green fill (#C6EFCE) |
| Confidence: medium | Yellow fill (#FFEB9C) |
| Confidence: low | Orange fill (#FFCC99) |
| Confidence: insufficient | Red fill (#FFC7CE) |
| Arabic text cells | Right-to-left alignment, Simplified Arabic font |

### Auto-generated cells

Every cell marked `{{placeholder}}` in the template is replaced at runtime:

```
{{property_address}}    → property_data["address"]
{{effective_date}}      → valuation_date (ISO 8601)
{{appraiser_name}}      → report_metadata["appraiser_name"]
{{primary_value}}       → formatted number, e.g. "12,245,759 EGP"
{{confidence_label}}    → "عالية" / "متوسطة" / "منخفضة"
{{egvs_section_1}}      → populated EGVS 1 narrative
... (all 11 EGVS sections)
```

### ExcelReportBuilder interface

```python
class ExcelReportBuilder:
    def __init__(self, template_path: str | None = None): ...

    def build(
        self,
        result: AssetValuationResult,
        property_data: dict,
        output_path: str,
    ) -> str:
        """
        Write the report to output_path.
        Returns the absolute path to the written file.
        """

    def _write_cover(self, ws, result, property_data): ...
    def _write_summary(self, ws, result): ...
    def _write_three_approaches(self, ws, result): ...
    def _write_purpose_valuations(self, ws, result): ...
    def _write_comparables(self, ws, result): ...
    def _write_audit_trail(self, ws, result): ...
    def _write_egvs_sections(self, ws, result): ...
    def _write_signoff(self, ws, result, property_data): ...
```

### Output file naming

```
reports/output/{reference_number}_{effective_date}.xlsx
# e.g. VAL-2026-001_2026-05-07.xlsx
```

---

## Task 6.4 — Flask Route Integration

**File:** `core_engine/bridge_api.py` — add **2 new routes** only.

### Route A — `POST /api/valuation/report`

Extends `POST /api/valuation/full` with asset-layer logic and report generation.

**Additional input fields** (beyond Phase 5 `/api/valuation/full`):

```json
{
  "property_type":    "residential",
  "property_subtype": "apartment",
  "occupancy":        "owner",
  "address":          "15 Nile Corniche, Maadi, Cairo",
  "reference_number": "VAL-2026-001",
  "appraiser_name":   "Eng. Hisham Elmahdy",
  "valuation_date":   "2026-05-07",
  "generate_report":  true
}
```

**Response (generate_report=false):**

```json
{
  "status":       "success",
  "asset_type":   "residential",
  "primary_value": 10815256.19,
  "primary_purpose": "market_value",
  "confidence":   "high",
  "phase_4_values": { ... },
  "purpose_valuations": { ... },
  "egvs_sections": { ... },
  "issues": []
}
```

**Response (generate_report=true):**

```json
{
  "status":        "success",
  "primary_value": 10815256.19,
  "confidence":    "high",
  "report_url":    "/api/valuation/report/download/VAL-2026-001_2026-05-07.xlsx",
  "purpose_valuations": { ... },
  "issues": []
}
```

### Route B — `GET /api/valuation/report/download/<filename>`

Serves the generated `.xlsx` file as a download.

```python
@app.route("/api/valuation/report/download/<filename>")
def download_report(filename):
    return send_file(
        os.path.join(REPORTS_OUTPUT_DIR, filename),
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
```

---

## Task 6.5 — Unit Tests

Test scripts follow the same `_test_p6_*.py` pattern as Phase 5.

### `_test_p6_residential.py` — 15 tests

| # | Test |
|---|---|
| 1 | Instantiation (name, version, applicable_purposes, weight_presets) |
| 2 | Validation — good inputs (0 errors) |
| 3 | Owner-occupied preset (80/15/5 weights) |
| 4 | Rental preset (50/20/30 weights) |
| 5 | Low-comp fallback (< 3 comps → 40/40/20) |
| 6 | Primary value = market_value.adjusted_value |
| 7 | All 4 purposes returned when all requested |
| 8 | Mortgage only when borrower_profile provided |
| 9 | Confidence aggregation (lowest across purposes) |
| 10 | EGVS sections populated (all 6 sections non-empty) |
| 11 | Metadata completeness (subtype, area, price_per_sqm, etc.) |
| 12 | Area > 1000 → warning |
| 13 | Age < 0 → error |
| 14 | Unknown subtype → warning |
| 15 | Result is AssetValuationResult with all required fields |

### `_test_p6_commercial.py` — 15 tests

| # | Test |
|---|---|
| 1 | Instantiation |
| 2 | Standard preset (30/20/50 weights) |
| 3 | Thin market (<3 comps → 20/30/50) |
| 4 | New construction (age ≤ 2 → 20/50/30) |
| 5 | Warehouse preset (20/55/25) |
| 6 | Primary value always = market_value |
| 7 | Missing cap_rate → warning |
| 8 | Missing gross_income → warning |
| 9 | All purposes returned |
| 10 | EGVS sections populated |
| 11 | Metadata completeness |
| 12 | Age > 50 → warning |
| 13 | Invalid area → error |
| 14 | price_per_sqm calculated correctly |
| 15 | AssetValuationResult fields complete |

### `_test_p6_excel.py` — 10 tests

| # | Test |
|---|---|
| 1 | ExcelReportBuilder instantiation |
| 2 | build() returns a file path |
| 3 | Output file exists and is non-empty |
| 4 | Workbook has all 8 expected sheets |
| 5 | Cover sheet has property address and date |
| 6 | Summary sheet has primary_value |
| 7 | Audit trail sheet has correct row count |
| 8 | EGVS sheet has all 11 sections populated |
| 9 | Confidence cell has correct fill colour |
| 10 | File is valid .xlsx (openpyxl can re-open it) |

---

## Task 6.6 — End-to-End Test

### `_test_p6_e2e.py`

Single script that exercises the full Phase 6 pipeline:

1. Build a realistic `AssetValuationResult` using real Phase 4 + Phase 5 values
2. Run `ResidentialAdapter.value()` with all 4 purposes
3. Run `ExcelReportBuilder.build()` → write to temp file
4. Re-open the workbook and assert sheet count, primary value cell, EGVS section presence
5. POST to `/api/valuation/report` with `generate_report=true`
6. Assert HTTP 200, assert `report_url` in response
7. GET the download URL, assert content-type is `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

---

## EGVS Compliance Matrix — Phase 6 Coverage

Phase 5 produced disclosures (list of section codes).  
Phase 6 produces **populated narratives** — actual text for each section.

| EGVS Section | Phase 5 | Phase 6 |
|---|---|---|
| 1 — Definitions and Scope | disclosure code only | full narrative auto-generated |
| 2 — Bases of Value | disclosure code only | full narrative auto-generated |
| 3 — Valuation Approaches | disclosure code only | three-approach rationale |
| 4 — Valuation of Property Types | disclosure code only | property-type-specific text |
| 5 — Reconciliation | partial (weights) | full reconciliation narrative |
| 6 — Reporting | ✗ | appraiser declaration, date, caveats |
| 7 — Residential Valuation | ✗ | ResidentialAdapter specific |
| 8 — Commercial Valuation | ✗ | CommercialAdapter specific |
| 9 — Mass Appraisal | ✗ | out of scope for Phase 6 |
| 10 — Special Purpose | ✗ | planned Phase 7 |
| 11 — Review Valuations | ✗ | planned Phase 7 |

---

## Implementation Sequence

| Task | File | Est. effort | Depends on |
|---|---|---|---|
| **6.0** | `asset_adapters/base.py` | ~1 hour | Phase 5 adapters |
| **6.1** | `asset_adapters/residential.py` | ~2 hours | Task 6.0 |
| **6.2** | `asset_adapters/commercial.py` | ~1.5 hours | Task 6.0 |
| **6.3** | `reports/excel_builder.py` | ~3 hours | Task 6.0 |
| **6.4** | `bridge_api.py` (2 routes) | ~1 hour | Tasks 6.1–6.3 |
| **6.5** | `_test_p6_residential.py` + `_test_p6_commercial.py` + `_test_p6_excel.py` | ~1.5 hours | Tasks 6.1–6.3 |
| **6.6** | `_test_p6_e2e.py` | ~1 hour | Task 6.4 |
| | **Total** | **~11 hours** | |

---

## Dependencies

### New Python packages

| Package | Version | Purpose |
|---|---|---|
| `openpyxl` | ≥ 3.1 | Excel report generation (likely already installed) |

No new packages beyond `openpyxl`. All other dependencies come from Phase 4 / 5.

### Verify before starting

```powershell
python -c "import openpyxl; print(openpyxl.__version__)"
```

If missing: `pip install openpyxl`

---

## Key Design Decisions

### 1. Asset adapter does NOT replace purpose adapter

The two layers are independent. An `AssetAdapter` calls `PurposeAdapter.adjust()`
internally, passing the appropriate weights. The Phase 5 adapters are not modified.
This keeps Phase 5 generic (any property type calls them) while Phase 6 handles
property-type-specific weight selection and EGVS narrative generation.

### 2. Primary value is always Market Value

All asset types return `market_value.adjusted_value` as the primary recommendation.
Other purpose values (mortgage, insurance, IFRS 13) are supplementary disclosures.
This is consistent with EGVS 2.0 — Market Value is the standard basis unless
the client specifies otherwise.

### 3. Weight presets are in the asset adapter, not the purpose adapter

Phase 5 `MarketValueAdapter` accepts any `comparable_count`-based weight.  
Phase 6 `ResidentialAdapter` *selects* the weight preset (80/15/5 vs 50/20/30)
based on `occupancy` and `comparable_count`, then passes it to the Phase 5 adapter.

### 4. Excel report is optional (generate_report flag)

`POST /api/valuation/report` works with `generate_report=false` (default) for API
clients that only want JSON. Report generation adds ~0.5s overhead and is only
triggered when explicitly requested. This keeps the route fast for programmatic use.

### 5. Reports stored on disk, not in database

Generated reports are written to `core_engine/reports/output/` and served via a
download route. No database required. Files are named by reference number + date
and are accessible as long as the server is running.

---

## What Phase 6 does NOT do

- Does **not** modify Phase 4 engines or Phase 5 adapters
- Does **not** add Word/PDF report formats (deferred to Phase 7)
- Does **not** implement mass appraisal asset adapter (Phase 7)
- Does **not** add industrial, land, or special-purpose adapters (Phase 7)
- Does **not** add a frontend UI for report download (Phase 7)
- Does **not** persist reports to a database (out of scope)

---

## Phase 6 Completion Criteria

| Criterion | Verification |
|---|---|
| `ResidentialAdapter` passes 15 unit tests | `python _test_p6_residential.py` → ALL PASS |
| `CommercialAdapter` passes 15 unit tests | `python _test_p6_commercial.py` → ALL PASS |
| `ExcelReportBuilder` passes 10 unit tests | `python _test_p6_excel.py` → ALL PASS |
| `POST /api/valuation/report` returns 200 | curl or Postman test |
| Report download route returns `.xlsx` | GET `/api/valuation/report/download/...` |
| All Phase 4 + Phase 5 routes unchanged | regression test → all pass |
| Phase 6 e2e test passes | `python _test_p6_e2e.py` → ALL PASS |

---

*Document created: 2026-05-07*  
*Author: Hisham Elmahdy / Claude Code*  
*Status: APPROVED — ready for implementation*
