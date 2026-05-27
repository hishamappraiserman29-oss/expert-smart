# Final Release Handoff — EXPERT_SMART v1.1.4

**Date:** 2026-05-22  
**Released by:** Hisham Elmahdy  
**Release type:** CONDITIONAL (not unconditional Full Production GO)  
**Tag:** `v1.1.4` — pending creation  
**Base:** `v1.1.3` (mobile/ CI gate)  
**PR:** #1 — merge commit `cb13c7a`

---

## 1. Release Summary

v1.1.4 introduces the **Composite Property Architecture** — a nine-wave composable
valuation engine for multi-component mixed-use properties. It adds
`POST /api/valuation/composite`, `GET /api/valuation/composite/schema`, a schema-driven
RTL frontend form, an additive Excel sheet, portfolio aggregation with synergy formula,
and USPAP/IAAO-aware reporting blocks.

The release remains **CONDITIONAL** because PH.3 (GCP service account key rotation) is
still pending. Full Production GO is blocked on PH.3 closure, not on code quality.

---

## 2. Commits Since v1.1.3

| Commit | Wave | Description |
|---|---|---|
| `cb13c7a` | — | Merge PR #1 from `feature/composite-frontend-wave5` |
| `effa7b9` | 7B | `composite_reporter.py` — USPAP/IAAO-aware reporting blocks (DRY) |
| `42908ba` | 7A | `composite_aggregator.py` — portfolio sum + synergy formula |
| `b0b8e76` | 6 | `composite_sheet.py` — "التقييم المركب" additive Excel tab |
| `c29bd57` | 5b | `composite_valuation.html` — schema-driven RTL frontend form |
| `85d12ac` | 5a | `GET /api/valuation/composite/schema` — backend-driven schema endpoint |
| `bc8e2f5` | 4 | `POST /api/valuation/composite` — stateless endpoint wiring Waves 1–3 |
| `8f333d4` | 3 | `CompositeValidator` — pre-flight BLOCKING/ADVISORY validation gate |
| `7f0adb1` | 2 | `PurposeComplianceAdapter` — 14 purpose multipliers → frozen `AdjustedValuation` |
| `ee86311` | 1 | `CompositeEngine` — per-component baseline: `area_sqm × base_rate_per_sqm` |

---

## 3. CI/CD Status

| Workflow | Status |
|---|---|
| CI/CD Pipeline | ✅ green |
| E2E Tests | ✅ green |

Full test suite: **2,364 / 2,364 passing** (up from 2,076 at v1.1.2/v1.1.3, +288 new composite tests).  
No failures, no skips.

---

## 4. New Subsystems in This Release

### Wave 1 — CompositeEngine (`valuation_engines/composite_engine.py`)

Stateless per-component baseline valuation engine. 15 asset types with distinct attribute
schemas (residential unit, villa, apartment, land, commercial space, office, warehouse,
hotel room, retail shop, clinic, school, factory, mixed-use, parking lot, storage).
Formula: `area_sqm × base_rate_per_sqm`. Raises `CompositeEngineError` for unknown asset
types or invalid attribute types.

**Tests:** `test_composite_engine.py`

### Wave 2 — PurposeComplianceAdapter (`adapters/purpose_adapter.py`)

14 valuation purposes mapped to multipliers (0.6–1.5×). Produces frozen `AdjustedValuation`
dataclasses carrying `uspap_standards`, `iaao_block_triggered`, and `deep_route_deferred`
markers. USPAP Standards 1+2 are assigned for all purposes; Standards 5+6 additionally for
tax purposes (`triggers_iaao=True`).

**Tests:** `test_purpose_adapter.py`

### Wave 3 — CompositeValidator (`validation/composite_rules.py`)

Pre-flight validation gate. Issues BLOCKING (HTTP 422) or ADVISORY issues. Validates:
asset type existence, required attributes, attribute type correctness, area > 0, purpose
validity, component list not empty. All messages bilingual (Arabic + English).

**Tests:** `test_composite_rules.py`

### Wave 4 — POST /api/valuation/composite (`composite_routes.py`)

Stateless endpoint wiring Waves 1–3. Accepts `components[]` + `purposes` (string broadcast
or per-component list). Returns: validation block, per-component `AdjustedValuation`, summary
totals, aggregation (Wave 7A), USPAP/IAAO reporting blocks (Wave 7B). Behind `@require_auth`.

**Tests:** `test_composite_endpoint.py` (incl. `TestGoldenSnapshot` deep-equal guard)

### Wave 5a — GET /api/valuation/composite/schema

Backend-driven schema endpoint. Returns live `ASSET_TYPES` catalog (15 types with attribute
specs) and `PURPOSE_RULES` catalog (14 purposes with multipliers). Frontend consumes this to
build the form dynamically — no hardcoded type/purpose lists in HTML. Behind `@require_auth`.

**Tests:** `test_composite_schema_endpoint.py`

### Wave 5b — composite_valuation.html (`frontend/composite_valuation.html`)

Schema-driven RTL form. Fetches schema on load, renders dynamic asset-type/attribute fields,
supports global + per-component purpose override. Bearer-token auth via `localStorage['es_auth']`.
Linked from `frontend/index.html` navigation. Playwright E2E smoke test in
`tests/e2e/test_composite_form_smoke.py`.

### Wave 6 — composite_sheet.py (`reports/sheets/composite_sheet.py`)

Additive Excel tab "التقييم المركب". 9 columns, RTL, Midnight Gold theme. Guard:
only added when `composite_valuations` is passed to `excel_builder.build()` with a clean
validation report. Zero change to existing sheets.

**Tests:** `test_composite_sheet.py`

### Wave 7A — composite_aggregator.py (`valuation_engines/composite_aggregator.py`)

Portfolio aggregation. `AggregationResult` frozen dataclass (5 fields:
`total_baseline`, `total_adjusted_before_synergy`, `synergy_adjustment_percent`,
`synergy_adjustment_amount`, `total_adjusted_after_synergy`). Formula:
`total_after = total_before + (total_before × synergy_pct / 100)`. Validates against
bool, non-numeric, NaN, Inf inputs. Raises `CompositeAggregatorError`.

**Tests:** `test_composite_aggregator.py`

### Wave 7B — composite_reporter.py (`valuation_engines/composite_reporter.py`)

USPAP/IAAO-aware reporting blocks. DRY: reads `uspap_standards`, `iaao_block_triggered`,
`deep_route_deferred` directly from existing `AdjustedValuation` fields — never re-derives
standards logic. `COD`/`PRD` are always `null` (see §5 for rationale).

**Tests:** `test_composite_reporter.py` (31 unit tests across 4 classes)

---

## 5. Design Constraints (not bugs)

### COD/PRD always null

`iaao_reporting.cod` and `iaao_reporting.prd` are always `null`.  
`ratio_study_status` is always `"not_computed"`.

**Why:** COD and PRD are mass-appraisal population statistics requiring a sales-ratio dataset
(many assessed values vs. sale prices). A single composite property's components are not a
ratio-study population. Computing pseudo-COD/PRD from component adjusted values would be
statistically meaningless and professionally misleading.

### iaao_mass_appraisal_mode never activated

`composite_routes.py` calls `_adapter.adapt_all(valuations, purposes)` without
`iaao_mass_appraisal_mode=True`. Therefore `iaao_block_triggered` is always `False` in
live endpoint responses, even for tax purposes.

**Why:** The `iaao_mass_appraisal_mode` parameter was designed for a future mass-appraisal
batch context. Single-property composite valuation is not a mass-appraisal context.
Tax purposes still receive USPAP Standards 5+6 via the `triggers_iaao` flag in `PURPOSE_RULES`.

---

## 6. Security Audit Status

No new security findings. All findings from v1.1.0 remain in their prior state.

| Finding | Status |
|---|---|
| SEC-001–SEC-009 | Remediated (prior releases) |
| SEC-002 auth hardening (full rollout) | ✅ COMPLETE |
| SEC-003 enterprise endpoints `@_require_admin` | ✅ Active |
| Composite endpoints auth | ✅ Both `POST /api/valuation/composite` and `GET /api/valuation/composite/schema` behind `@require_auth` |
| PH.3 GCP key rotation | ⚠️ WAIVED TEMPORARILY — unchanged from v1.1.0 |

---

## 7. What Remains Deferred

### PH.3 — GCP Service Account Key Rotation
- Still pending (waiver ID: `PH3-GCP-SA-KEY-ROTATION`)
- Waiver expires: 2026-06-19
- Closure runbook: `docs/PH3_CLOSURE_RUNBOOK.md`
- Verifier: `tools/verify_ph3_closure.py`
- **This is the only remaining blocker for Full Production GO**

### B3 bridge — Multi-tenant report isolation
- `tenant_id` ↔ `owner_user_id` link for composite valuations not yet implemented.
- Deferred from R3.11 (saas/ subsystem). P2.

### Frontend auth follow-ups
- `/api/radar/start` and `/api/price-index` not yet behind auth.
- Composite endpoints are already behind `@require_auth` — no action needed.

### Composite Waves 8–9
- Not yet specified. No Gate A, no implementation.
- Do not begin without an approved spec. See `docs/DEFERRED_ITEMS.md → D7`.

---

## 8. Release Gate Summary

| Gate | Status |
|---|---|
| Repo credential hygiene | ✅ GO |
| CI/CD Pipeline (2,364 tests) | ✅ GO |
| E2E smoke tests | ✅ GO |
| Production dry-run | ✅ GO (21/21 — from v1.1.0; no runtime changes in v1.1.4 composite layer) |
| SEC-002 auth hardening (complete) | ✅ GO |
| SEC-003 enterprise admin gate | ✅ GO |
| Composite endpoints behind `@require_auth` | ✅ GO |
| Wave 1 `CompositeEngine` | ✅ MERGED |
| Wave 2 `PurposeComplianceAdapter` | ✅ MERGED |
| Wave 3 `CompositeValidator` | ✅ MERGED |
| Wave 4 `POST /api/valuation/composite` | ✅ MERGED |
| Wave 5a schema endpoint | ✅ MERGED |
| Wave 5b composite frontend form | ✅ MERGED |
| Wave 6 composite Excel sheet | ✅ MERGED |
| Wave 7A portfolio aggregation | ✅ MERGED |
| Wave 7B USPAP/IAAO reporting blocks | ✅ MERGED |
| Composite golden-snapshot test | ✅ PASSING |
| mobile/ subsystem + CI workflow | ✅ MERGED (v1.1.3 + `9a8b844`) |
| PH.3 GCP key rotation | ⚠️ WAIVED TEMPORARILY |
| **v1.1.4 CONDITIONAL release** | ✅ **ALLOWED** |
| **Full unconditional production GO** | ❌ **PENDING** — PH.3 closure only |

---

## 9. Recommended Next Steps

| Priority | Item |
|---|---|
| **P0** | **PH.3 closure** — complete GCP key rotation or confirm key deleted/unused. Waiver expires 2026-06-19. Runbook: `docs/PH3_CLOSURE_RUNBOOK.md`. |
| **P1** | **Full Production GO review** — re-run production gate after PH.3 is closed. Issues an unconditional release. |
| **P2** | **B3 bridge** — `tenant_id` ↔ `owner_user_id` link for multi-tenant composite report isolation (saas/ non-blocking deferral). |
| **P2** | **Frontend auth follow-ups** — gate `/api/radar/start` and `/api/price-index` behind auth/admin state. |
| **P3** | **Composite Waves 8–9** — open Gate A survey only after an approved spec exists. |

---

**EXPERT_SMART | v1.1.4 Conditional Release Handoff | 2026-05-22**
