# Legacy Compatibility Map — Phase 20

Generated during Phase 20 (Legacy Endpoints & Legacy Frontend Review).

---

## 1. Active Frontend

| File | Status | Served at | Notes |
|---|---|---|---|
| `frontend/index.html` | **ACTIVE** | `/` (primary) | 28 132 lines, v26, four-tab UI |
| `frontend/sovereign_brain.html` | **ACTIVE (fallback)** | `/` (if index.html absent) | 4 086 lines, institutional platform |

`bridge_api.py:677` serves `index.html` first, then `sovereign_brain.html` as fallback.

---

## 2. Legacy / Backup Frontend Files

| File | Lines | Purpose | Endpoints | Status | Recommendation |
|---|---|---|---|---|---|
| `frontend/valuation.html` | 1 678 | Early standalone valuation UI + Gemini | `/api/valuation`, `/api/generate-report` ❌, `/api/investment-report` ❌ | **Legacy** | Archive later — not served at `/` |
| `frontend/sovereign.html` | 2 116 | Sovereign unified interface v1 | `/api/market-sweep` ✅¹, `/api/bank-audit` ✅¹, `/api/fund-valuation` ✅¹, `/api/tax-pilot` ✅¹, `/api/master-report` ✅¹, `/api/report/generate` ✅¹, `/api/valuation`, `/api/ingest`, `/api/price-map`, `/api/upload`, `/api/fraud/detect`, `/api/demographic/flow` | **Legacy** | Keep; stubs added for missing endpoints |
| `frontend/sovereign_brain.html` | 4 086 | Institutional platform v2 | `/api/advisor`, `/api/advisor/health`, `/api/ingest`, `/api/fraud/detect`, `/api/demographic/flow`, `/api/image/analyze`, `/api/image/geo-analyze` ✅² | **Active (fallback)** | Keep |
| `frontend/sovereign_v2.html` | ~2 000 | Sovereign v2 | `/api/session/update` ✅¹ | **Legacy** | Keep; stub added |
| `frontend/sovereign_ui_phase1.html` | — | UI design phase 1 mockup | None | **Legacy / Preview** | Archive later |
| `frontend/sovereign_ui_phase2.html` | — | UI design phase 2 mockup | None | **Legacy / Preview** | Archive later |
| `frontend/composite_valuation.html` | 817 | Composite valuation standalone | `/api/valuation/composite` ✅, `/api/valuation/composite/schema` ✅ | **Legacy (standalone)** | Keep — endpoints are live |
| `frontend/agent_chat.html` | ~100 | Agent chat UI | `/api/agent/chat` ✅ | **Legacy** | Keep — endpoint is live |
| `frontend/test_pipeline.html` | — | Data pipeline test harness | None (uses data-engine/*.js) | **Dev/Test only** | Keep — dev tooling |
| `frontend/badge_preview.html` | — | Badge design preview | None | **Preview / Static** | Archive later |
| `frontend/business_valuation_preview.html` | — | Business valuation preview | None | **Preview / Static** | Archive later |
| `frontend/expert_dashboard_preview.html` | — | Dashboard preview | None | **Preview / Static** | Archive later |
| `frontend/financing_request_preview.html` | — | Financing preview | None | **Preview / Static** | Archive later |
| `frontend/home_pillars_preview.html` | — | Home pillars design | None | **Preview / Static** | Archive later |
| `frontend/index.before-*.html` (×24) | varies | Rolling backup snapshots | — | **Backup snapshots** | Do NOT delete; keep as history |
| `frontend/index.broken.phase311.rollback-snapshot.html` | — | Rollback snapshot | — | **Backup snapshot** | Do NOT delete |

✅¹ = Phase 20 stub added (returns 501 + migration guidance)
✅² = Phase 20 alias added (`/api/image/geo-analyze` → `/api/image/analyze`)
❌ = Missing endpoint, no suitable modern equivalent to trivially alias

---

## 3. Standalone JS/CSS Files

| File | Referenced by | Status |
|---|---|---|
| `frontend/script.js` | Not referenced by `index.html` | **Orphan** — investigate |
| `frontend/localization.js` | Not referenced by `index.html` | **Orphan** — investigate |
| `frontend/styles.css` | Not referenced by `index.html` (uses inline styles) | **Orphan** — investigate |
| `frontend/style_rtl.css` | Not referenced by `index.html` | **Orphan** — investigate |
| `frontend/data-engine/*.js` | `test_pipeline.html` only | **Dev/Test only** |

---

## 4. Endpoint Map (Phase 20)

### Active endpoints referenced by `index.html`

| Endpoint | Method | Status | Notes |
|---|---|---|---|
| `/api/valuation` | POST | ✅ Active | Core valuation |
| `/api/valuation/requirements` | GET | ✅ Active | Requirements checklist |
| `/api/valuation/composite` | POST | ✅ Active | via composite_routes.py |
| `/api/valuation/composite/schema` | GET | ✅ Active | via composite_routes.py |
| `/api/price-index` | GET/POST | ✅ Active | |
| `/api/radar/start` | POST | ✅ Active | |
| `/api/mass-appraisal/*` | various | ✅ Active | Full suite |
| `/api/reports` | GET | ✅ Active | |
| `/api/reports/<id>` | GET | ✅ Active | |
| `/api/reports/<id>/pdf` | GET | ✅ Active | |
| `/api/auth/verify` | GET | ✅ Active | |
| `/api/ingest` | POST | ✅ Active | |
| `/api/upload` | POST | ✅ Active | |
| `/api/fraud/detect` | POST | ✅ Active | |
| `/api/geo/risk` | POST | ✅ Active | |
| `/api/demographic/flow` | POST | ✅ Active | |
| `/api/image/geo-analyze` | POST | ✅ **Alias added** (Phase 20) | → `/api/image/analyze` |

### Sovereign legacy endpoints (sovereign.html — not served at /)

| Endpoint | Method | Status | Phase 20 Action | Modern Equivalent |
|---|---|---|---|---|
| `/api/market-sweep` | POST | ⚠️ **Stub (501)** | Stub added | `/api/radar/*` |
| `/api/bank-audit` | POST | ⚠️ **Stub (501)** | Stub added | `/api/banking/collateral/value` |
| `/api/fund-valuation` | POST | ⚠️ **Stub (501)** | Stub added | `/api/funds/fair-value/assess` |
| `/api/tax-pilot` | POST | ⚠️ **Stub (501)** | Stub added | `/api/government/tax/calculate` |
| `/api/master-report` | POST | ⚠️ **Stub (501)** | Stub added | `/api/valuation/report` |
| `/api/report/generate` | POST | ⚠️ **Stub (501)** | Stub added | `/api/valuation/report` |
| `/api/session/update` | POST | ⚠️ **Stub (501)** | Stub added | TBD |

### Endpoints in valuation.html not in bridge_api

| Endpoint | Status | Notes |
|---|---|---|
| `/api/generate-report` | ❌ Missing | No modern equivalent trivially aliasable; Phase 21 |
| `/api/investment-report` | ❌ Missing | No modern equivalent trivially aliasable; Phase 21 |

---

## 5. Compatibility Issues Found

| Issue | Severity | Location | Phase 20 Action |
|---|---|---|---|
| `/api/image/geo-analyze` missing | Medium | `index.html:4384`, `sovereign_brain.html:2560` | ✅ Alias added |
| `/api/market-sweep` missing | Low (legacy page only) | `sovereign.html:1598` | ✅ 501 stub added |
| `/api/bank-audit` missing | Low (legacy page only) | `sovereign.html:1838` | ✅ 501 stub added |
| `/api/fund-valuation` missing | Low (legacy page only) | `sovereign.html:1855` | ✅ 501 stub added |
| `/api/tax-pilot` missing | Low (legacy page only) | `sovereign.html:1868` | ✅ 501 stub added |
| `/api/master-report` missing | Low (legacy page only) | `sovereign.html:2006` | ✅ 501 stub added |
| `/api/report/generate` missing | Low (legacy page only) | `sovereign.html:2027` | ✅ 501 stub added |
| `/api/session/update` missing | Low (legacy page only) | `sovereign_v2.html:1583` | ✅ 501 stub added |
| `/api/generate-report` missing | Low (legacy page only) | `valuation.html:1619` | Phase 21 — full alias |
| `/api/investment-report` missing | Low (legacy page only) | `valuation.html:1644` | Phase 21 — full alias |
| `script.js`, `localization.js`, `styles.css`, `style_rtl.css` orphaned | Info | `frontend/` | Investigate in Phase 21 |
| 24 index.before-*.html backup files | Info | `frontend/` | Keep as is — do not delete |

---

## 6. Phase 21 Follow-up

1. Wire `/api/generate-report` and `/api/investment-report` (valuation.html legacy calls) — requires understanding their expected payload/response shape before aliasing.
2. Wire `/api/market-sweep` → market_sweeper engine properly (beyond 501 stub).
3. Wire `/api/bank-audit` → bank_audit_engine properly.
4. Wire `/api/fund-valuation` → fund_valuation_engine properly.
5. Wire `/api/tax-pilot` → tax_pilot_engine properly.
6. Wire `/api/master-report` and `/api/report/generate` → master_report_generator properly.
7. Investigate orphan JS/CSS files (`script.js`, `localization.js`, `styles.css`, `style_rtl.css`) — determine if still used by any served page.
8. Archive static preview files (`badge_preview.html`, `business_valuation_preview.html`, etc.) once confirmed unused.
9. Consider adding a `/legacy` redirect page listing all legacy UIs with links.
