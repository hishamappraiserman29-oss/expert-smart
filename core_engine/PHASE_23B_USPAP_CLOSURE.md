# Phase 23B — USPAP Compliance Framework — Closure Document

## Key Invariant
USPAP (and all standards) are **reporting / disclosure frameworks ONLY**.
They do **not** change, recalculate, or override any valuation engine result.

## Files Created

| File | Purpose |
|------|---------|
| `standards/__init__.py` | Package exports |
| `standards/uspap.py` | USPAP disclosure framework: property ID, assumptions, competency, certification, workfile, compliance checker, addendum generator |
| `standards/standards_manager.py` | Multi-framework manager: EGVS, IVSC, USPAP, IFRS13, CBE; compatibility validation |
| `tests/test_phase23b_uspap.py` | 40 tests (A01–H08) |

## bridge_api.py Endpoints Added

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/standards/frameworks` | GET | List all 5 supported frameworks |
| `/api/standards/validate` | POST | Validate framework combination (returns warnings) |
| `/api/standards/uspap/generate` | POST | Generate USPAP disclosure addendum for a property |

All endpoints guarded by `_USPAP_OK` flag. Valuation engines untouched.

## USPAP Classes

- **`USPAPPropertyIdentification`** — address, parcel ID, legal description
- **`USPAPAssumptions`** — extraordinary assumptions + hypothetical conditions (deduplication, flag tracking)
- **`USPAPCompetencyStatement`** — auto-generated or custom competency text
- **`USPAPCertification`** — standard USPAP certification language with USPAP-Oriented notice
- **`USPAPWorkfileNote`** — workfile reference documentation
- **`USPAPReport`** — composite report dataclass; `is_avm_valuation`/`is_mass_appraisal` flags
- **`USPAPComplianceChecker`** — field validation → (warnings, errors); blocks `APPRAISER_CERTIFIED` claim for AVM/mass appraisal
- **`USPAPComplianceAddenum`** — formatted multi-section addendum text

## Key Design Rules Enforced

1. `calculation_impact: False` on every `StandardsManager` framework config
2. AVM + `APPRAISER_CERTIFIED` → **error** (cannot claim certified for automated systems)
3. Mass appraisal + `APPRAISER_CERTIFIED` → **error**
4. AVM/mass with `USPAP_ORIENTED` → **warning only** (advisory)
5. Every addendum includes disclaimer: "Does NOT constitute professional appraisal services"

## Test Results
- **40/40 tests pass** (A01–H08)
- **695/695 full suite** — zero regressions
- Valuation engines (`comparative.py`, `cost.py`, `income.py`, `avm_predictor.py`) untouched (verified by grep)
