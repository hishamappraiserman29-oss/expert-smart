# Release Notes — Expert Smart v1.x
## Phases 0–23 | Branch: `feature/requirements-checklist-ui`

**Date:** 2026-06-17
**HEAD:** `2d961e9 fix(security): harden JWT secrets and static file handling`
**Python:** 3.13.14
**WSGI:** Waitress (production) / Flask dev fallback
**Entry point:** `core_engine/bridge_api.py`

---

## Overview

This release consolidates 23 implementation phases on branch
`feature/requirements-checklist-ui`. The platform covers:

- **Valuation engine** — 15+ standalone valuation approach engines (DCF, HABU,
  income, cost, sales comparison, residual land, insurance, mortgage, IFRS 13,
  market rental, rights, litigation, ESG)
- **Requirements system** — 70+ asset types × purpose matrix with field-level
  requirement specs (Phase 8 series through Phase 14)
- **Composite valuation** — multi-approach form UI + API + E2E tests
- **Reports & outputs** — 40+ enriched valuation report templates, saved-report
  registry, PDF download, Excel download
- **AI / RAG / advisory** — chat advisor tab, Qdrant knowledge seeder,
  agentic market enrichment layer (draft/pending-review only)
- **Security hardening** — JWT enforcement, static-file path-traversal fix,
  download auth gating, warning-suppression narrowing
- **Frontend cleanup** — legacy and preview HTML archived; active UI preserved

---

## 1. Changes Facing Users / Operators

### UI (frontend)
| Change | Detail |
|---|---|
| Four-tab workspace | `index.html` — Valuation · Mass Appraisal · Reports · AI Advisor tabs |
| Composite valuation form | `/composite_valuation.html` — multi-approach entry |
| Agent chat | `/agent` → `agent_chat.html` |
| Geo selector | Country → Province → City cascade |
| Requirements checklist panel | Dynamic per-asset, per-purpose checklist inline in valuation tab |
| Frontend cleanup | `sovereign.html`, `sovereign_v2.html`, `valuation.html` → `frontend/_legacy/`; 7 preview HTMLs + `styles.css` → `frontend/_archive/` |

### API (new routes since last main merge)
| Route | Method | Status | Phase |
|---|---|---|---|
| `/api/valuation/requirements` | GET | Active | Phase 8 series |
| `/api/valuation/composite` | POST | Active | Phase 8J |
| `/api/valuation/composite/schema` | GET | Active | Phase 8J |
| `/api/image/geo-analyze` | POST | Alias → `/api/image/analyze` | Phase 20 |
| `/api/market-sweep` | POST | 501 stub | Phase 20 |
| `/api/bank-audit` | POST | 501 stub | Phase 20 |
| `/api/fund-valuation` | POST | 501 stub | Phase 20 |
| `/api/tax-pilot` | POST | 501 stub | Phase 20 |
| `/api/master-report` | POST | 501 stub | Phase 20 |
| `/api/report/generate` | POST | 501 stub | Phase 20 |
| `/api/session/update` | POST | 501 stub | Phase 20 |
| `/api/dev/auth-token` | GET | Dev-only (triple-gated) | Pre-existing |

---

## 2. Professional Valuation Changes

### Requirements System (Phases 8–14)
- 70+ asset types supported: residential, commercial, industrial, agricultural,
  hotel, marina, seaport, airport, healthcare, educational, data center, cold
  storage, heritage, zoo/safari, forest, groundwater/mine, floating hotel,
  serviced apartments, wellness resort, REIT components, under-construction,
  fractional ownership, intangible assets, and more
- Per-purpose requirement matrix: `market_value`, `mortgage`, `insurance`,
  `liquidation`, `investment`, `rental`, `tax`, etc.
- Field-level validation: mandatory / optional / conditional per purpose
- Purpose integration matrix and purpose routes registry

### Valuation Engines (Phases 16–17)
21 standalone engines under `core_engine/engines/`:

| Engine | Class | Approach |
|---|---|---|
| `habu_engine.py` | `HABUEngine` | Highest & Best Use Analysis |
| `sales_comparison_engine.py` | `SalesComparisonEngine` | Market/Sales Comparison |
| `cost_approach_engine.py` | `CostApproachEngine` | Depreciated Replacement Cost |
| `income_approach_engine.py` | `IncomeApproachEngine` | Income Capitalisation |
| `residual_land_engine.py` | `ResidualLandEngine` | Residual Land Value |
| `dcf_engine.py` | `DCFEngine` | Discounted Cash Flow |
| `insurance_engine.py` | `InsuranceEngine` | Insurance Reinstatement |
| `mortgage_lending_engine.py` | `MortgageLendingEngine` | Mortgage Lending Value |
| `liquidation_engine.py` | `LiquidationEngine` | Forced/Orderly Liquidation |
| `market_rental_engine.py` | `MarketRentalEngine` | Market Rental Assessment |
| `ifrs13_engine.py` | `IFRS13Engine` | IFRS 13 Fair Value |
| `rights_engine.py` | `RightsEngine` | Rights & Easements |
| `litigation_compensation_engine.py` | `LitigationCompensationEngine` | Litigation/Compensation |
| `esg_remediation_engine.py` | `ESGRemediationEngine` | ESG / Remediation Cost |
| `engine_dispatcher.py` | `EngineDispatcher` | Routing by purpose |

All engines are isolated under `core_engine/engines/` and **not integrated**
into `/api/valuation` — they are standalone callable modules.

### Approval Rules (Phase 13)
`core_engine/adapters/approval_rules.py`:
- `requires_human_approval()`, `can_generate_final_report()`,
  `validate_auto_enrichment_metadata()` — governance enforcement

---

## 3. Reports & Outputs

### Report Templates
40+ enriched asset-specific report requirement sets added via Phase 8 series
commits (retail, industrial, healthcare, educational, airport, seaport, marina,
data center, cold storage, floating hotel, serviced apartments, wellness resort,
zoo/safari, forest, heritage, mine/groundwater, under-construction, fractional
ownership, intangible assets, architectural cultural heritage, waterway easement,
riparian rights, littoral rights).

### Saved Reports Registry (Phase reported in commits)
`core_engine/reports/` — saved-report registry with identity metadata and output
sheet generation. `/api/reports`, `/api/reports/<id>`, `/api/reports/<id>/pdf`
all require `@require_auth`.

### Excel Downloads
`/api/download/<filename>` — auth-required, 3-layer path-traversal protection,
`OUTPUTS` directory-containment via `realpath`.

`/api/valuation/report/download/<filename>` — auth-required, extension allowlist
(`.xlsx`, `.xlsm` only), 3-layer traversal protection.

---

## 4. Security & Production Readiness (Phase 22)

### Changes Made
| Item | File | Detail |
|---|---|---|
| JWT production key enforcement | `auth/tokens.py` | `FLASK_ENV=production` rejects secrets < 32 bytes; `validate_secret_strength()` utility added |
| Static-file path traversal fix | `bridge_api.py` | `serve_static` now delegates entirely to `send_from_directory` (werkzeug `safe_join`) — removes unsafe `os.path.isfile()` pre-probe |
| Warning suppression narrowed | `investment_engine.py`, `master_report_generator.py`, `run_final_valuation.py` | Replaced blanket `filterwarnings("ignore")` with targeted `DeprecationWarning`+`FutureWarning` only — PyJWT `InsecureKeyLengthWarning` now surfaces |
| JWT test-secret quality | `tests/test_auth.py` | Primary test secret extended from 30 → 32 bytes |
| 15 new security tests | `tests/test_phase22_security.py` | SEC22-01 through SEC22-15 |

### Confirmed Security Invariants
- No auth weakened; no `@require_auth` removed
- No CORS behavior changed; no wildcard `*` ever in `_CORS_ORIGINS`
- No rate limits removed
- No audit/logging disabled
- No secrets committed; `.env` is git-ignored
- Download endpoints: auth-gated + path-traversal protected
- Dev auth: triple-gated (env flag + FLASK_ENV≠production + localhost-only)

### Known Gaps (Phase 23 follow-up)
- 15+ routes (including `/api/agent/chat`, `/api/image/analyze`, `/api/library/add`,
  `/api/tune/analyze`) have no `@require_auth` — wide change deferred
- `/api/valuation`, `/api/advisor`, `/api/agent/chat` are not rate-limited
- `/api/valuation`, `/api/advisor` are not in the audit log after-request hook
- 12 other test modules use JWT secrets < 32 bytes (InsecureKeyLengthWarning
  in test output; tests pass; mechanical fix deferred)
- `host="0.0.0.0"` is hardcoded in startup; no `HOST` env-var override

---

## 5. AI / RAG / Enrichment (Phases 18–19)

### Qdrant Knowledge Seeder (Phase 18)
`core_engine/knowledge/qdrant_seeder.py` — standalone seeder for
`egypt_estate` collection. Gracefully degrades if Qdrant unavailable.
Not integrated into `/api/valuation`.

### Agentic Market Enrichment (Phase 19)
`core_engine/enrichment/` — fully isolated layer:
- All outputs: `is_automated_fill=True`, `approval_status="pending_human_review"`
- `can_generate_final_report()` → `False` until explicit expert approval
- No scraping, no internet calls, no model training
- `MockMarketProvider` for deterministic test isolation
- Reuses Phase 13 `approval_rules.py` for governance (ME13 regression test)

---

## 6. Frontend Inventory (Phase 21)

See `docs/frontend_inventory.md` for full 51-file inventory.

**Active files (must not move):**
- `frontend/index.html` — primary UI at `/`
- `frontend/sovereign_brain.html` — fallback at `/`
- `frontend/agent_chat.html` — served at `/agent`
- `frontend/composite_valuation.html` — E2E-tested at `/composite_valuation.html`
- `frontend/image_d86c0c.jpg` — referenced by `index.html`

**Archived:**
- `frontend/_legacy/` — `sovereign.html`, `sovereign_v2.html`, `valuation.html`
- `frontend/_archive/` — 7 preview HTMLs + `styles.css`

**HOLD (Phase 23 i18n deliverables):**
- `frontend/localization.js` — Phase 23 i18n, not yet wired to `index.html`
- `frontend/style_rtl.css` — Phase 23 RTL CSS, not yet wired

---

## 7. Tests Run & Results

### Baseline (Phase 23 Step verification)

| Suite | Tests | Result |
|---|---|---|
| `test_requirements_endpoint.py` | 21 | ✅ passed |
| `test_valuation_requirements.py` | 70 | ✅ passed |
| `test_purpose_adapter.py` | 36 | ✅ passed |
| **Subtotal Step 3** | **127** | **✅ all passed** |
| auth + JWT + Phase 22 security (`test_auth.py`, `test_dev_auth.py`, `test_auth_import_paths.py`, `test_phase22_security.py`) | 54 | ✅ passed |
| download + security (5 test modules) | 111 | ✅ passed |
| Phase 18/19/20 feature tests | 72 | ✅ passed |
| approval / matrix / asset / purpose | 324 | ✅ passed |
| knowledge / enrichment / habu / valuation | 363 | ✅ passed |
| report / excel / pdf / saved (non-E2E) | 443 | ✅ passed |
| E2E composite smoke | 8 | ✅ passed |
| Focused E2E CS3145, CS3150, CS3153, CS3154, CS3170 | 5 | ✅ passed |
| **Full collection** | **6,489** | **✅ no collection errors** |

### Remaining Warnings (all pre-existing)
| Warning | Source | Classification |
|---|---|---|
| `DeprecationWarning: datetime.datetime.utcnow()` | `market_indicators.py`, SQLAlchemy | Legacy — pre-existing, not a release blocker |
| `InsecureKeyLengthWarning` (HMAC < 32 bytes) | PyJWT, from test fixtures with short secrets | Pre-existing — now unmasked by Phase 22 targeted suppression; tests still pass; follow-up to fix all 12 test files |
| `InsecureKeyLengthWarning` (HMAC 22 bytes, `test_phase20_legacy_compat.py`) | PyJWT | Pre-existing — follow-up |

---

## 8. Known Issues & Classification

| Issue | Classification | Detail |
|---|---|---|
| 15+ routes without `@require_auth` | **Follow-up (not release blocker)** | Wide `bridge_api.py` change; deferred per governance |
| 12 test files with short JWT test secrets | **Follow-up** | `InsecureKeyLengthWarning` in test output; all tests pass |
| `/api/valuation`, `/api/advisor` not rate-limited | **Follow-up** | Wide change; deferred |
| `host="0.0.0.0"` hardcoded in startup | **Follow-up** | Operator-level; no `HOST` env var |
| `frontend/localization.js`, `style_rtl.css` not wired to `index.html` | **Follow-up** | Phase 23 i18n/RTL deliverable outstanding |
| `frontend/script.js` orphan (71KB) | **Follow-up** | No HTML references found; pending git-history investigation |
| `/api/generate-report`, `/api/investment-report` missing | **Follow-up** | Called by `frontend/_legacy/valuation.html`; stubs not added |
| Live OpenAI key in `core_engine/.env` | **Operator action required** | Not committed (git-ignored); operator must rotate |

---

## 9. Rollback Plan

All Phase 18–23 commits are reversible individually:

```powershell
# Revert to Phase 17 state (before Phase 18):
git revert <commit>..HEAD   # or reset to desired baseline commit

# Phase 21 moves (if needed):
Move-Item frontend/_legacy/* frontend/
Move-Item frontend/_archive/* frontend/
Remove-Item frontend/_legacy/, frontend/_archive/
```

No DB schema migrations were introduced in Phases 18–23.
No valuation formula or engine logic was changed in Phases 18–23.

---

## 10. Commit History (Recent 23 Phase Commits)

```
2d961e9  fix(security): harden JWT secrets and static file handling         (Phase 22)
b8bb2cf  chore(frontend): archive legacy and preview files                   (Phase 21)
bf52497  feat(api): add legacy compatibility endpoints                        (Phase 20)
df5e8a3  feat(enrichment): add draft market enrichment layer                 (Phase 19)
9fb75fa  feat(knowledge): add Qdrant seed data seeder                        (Phase 18)
5da92c2  feat(engines): add standalone engine dispatcher                      (Phase 17)
0cb9efe  feat(engines): add rights litigation and ESG foundations            (Phase 17)
9bb2a0e  feat(engines): add market rental and IFRS 13 foundations            (Phase 17)
10ef7e4  feat(engines): add insurance mortgage and liquidation foundations   (Phase 17)
e14b0dc  feat(engines): add DCF and residual land foundations                (Phase 17)
66bb776  feat(engines): add cost and income approach foundations             (Phase 17)
c6dfd17  feat(engines): add HABU and sales comparison foundations            (Phase 16)
bb11cd3  test(engines): add OOP valuation engine coverage                    (Phase 16)
56349ef  feat(reports): add saved reports registry                           (Phase 15)
bdcb2f6  feat(reports): add report identity and output metadata sheets       (Phase 15)
eadb2e0  feat(metadata): add approval rules helpers                          (Phase 13)
```

---

## 11. Files Changed Since Branch Diverged From Main

### Core Engine
- `core_engine/bridge_api.py` — routes for composite, requirements, image geo-analyze alias, legacy stubs, dev auth registration, `serve_static` traversal fix
- `core_engine/auth/tokens.py` — production min-key-length check + `validate_secret_strength()`
- `core_engine/dev_auth.py` — pre-existing (triple-gated dev token endpoint)
- `core_engine/investment_engine.py` — targeted warning suppression
- `core_engine/master_report_generator.py` — targeted warning suppression
- `core_engine/run_final_valuation.py` — targeted warning suppression

### New Modules
- `core_engine/enrichment/` — Phase 19 agentic market enrichment (5 files)
- `core_engine/knowledge/qdrant_seeder.py` — Phase 18 Qdrant seeder
- `core_engine/engines/` — 21 standalone valuation engines
- `core_engine/adapters/approval_rules.py` — Phase 13 governance helpers
- `core_engine/composite_routes.py` — Phase 8J composite valuation routes

### Frontend
- `frontend/index.html` — major; 4-tab workspace, requirements checklist, composite form integration
- `frontend/composite_valuation.html` — composite valuation standalone form
- `frontend/agent_chat.html` — agent chat UI
- `frontend/_legacy/` — `sovereign.html`, `sovereign_v2.html`, `valuation.html` (archived)
- `frontend/_archive/` — 7 preview HTMLs + `styles.css` (archived)

### Tests
- `core_engine/tests/test_phase22_security.py` — 15 Phase 22 security tests (new)
- `core_engine/tests/test_auth.py` — test secret updated to 32 bytes
- `core_engine/tests/test_phase20_legacy_compat.py` — 34 Phase 20 tests
- `core_engine/tests/test_phase19_market_enrichment.py` — 18 Phase 19 tests
- `core_engine/tests/test_phase18_qdrant_seed.py` — Phase 18 tests
- Multiple engine, requirements, composite, and security test files

### Docs
- `docs/frontend_inventory.md` — Phase 21 frontend inventory (51 files)
- `docs/LEGACY_COMPATIBILITY.md` — Phase 20 legacy endpoint map
- `docs/release_notes_phase_0_to_23.md` — this file

---

## 12. Recommended Next Steps

1. **Gate this release** — merge `feature/requirements-checklist-ui` → `main` after full E2E confirmation
2. **Add `@require_auth`** to the 15 currently unprotected routes (priority: `/api/agent/chat`, `/api/image/analyze`, `/api/library/add`, `/api/tune/analyze`, `/api/standards/uspap/generate`)
3. **Add rate limits** to `/api/valuation`, `/api/advisor`, `/api/agent/chat`
4. **Wire `localization.js` and `style_rtl.css`** into `index.html` (Phase 23 i18n deliverable)
5. **Fix short JWT secrets** in 12 remaining test files
6. **Add stubs** for `/api/generate-report` and `/api/investment-report`
7. **Investigate `script.js`** orphan (71KB, no HTML references)
8. **Rotate OpenAI key** in production `.env` (operator action)
9. **Add `HOST` env-var** override to startup block

---

*Generated by Phase 23 stabilization run — 2026-06-17*
*No files were modified, deleted, or committed during this phase.*
