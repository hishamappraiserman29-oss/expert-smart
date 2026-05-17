# Security Endpoint Auth Classification Matrix
**SEC-002 — Broad Auth Endpoint Audit**
**Date:** 2026-05-18
**Status:** Classification complete. No code changes applied. Remediation waves pending approval.

---

## Legend

| Classification | Meaning |
|----------------|---------|
| `PUBLIC_OK` | No auth required. Safe for unauthenticated access. Health checks, static info, public market data. |
| `AUTH_REQUIRED` | Must have valid JWT (`@require_auth`). User report data, generated files, personal/user-owned outputs, regulated computations. |
| `ADMIN_REQUIRED` | Must be an admin user (`@_require_admin`). Tenant management, audit viewer, platform config, destructive ops. |
| `INTERNAL_ONLY` | Should not be publicly routable. Auth-system maintenance, debug/dev ops. |
| `DEFER_REVIEW` | Product policy decision needed. Ambiguous whether public-demo or auth-gated. |

---

## Summary

| Metric | Count |
|--------|-------|
| Total Flask routes audited | 167 |
| Currently `@require_auth` | 5 |
| Currently `@_require_admin` | 19 |
| Currently no auth decorator | 143 |
| **Auth-protected total** | **24 (14%)** |
| **Unprotected total** | **143 (86%)** |

| Recommended Classification | Count |
|---------------------------|-------|
| Already compliant (correct auth applied) | 24 |
| PUBLIC_OK (correctly unprotected) | 43 |
| **AUTH_REQUIRED gap** | **62** |
| **ADMIN_REQUIRED gap** | **20** |
| **INTERNAL_ONLY gap** | **1** |
| **DEFER_REVIEW** | **17** |

**Confirmed gaps requiring remediation: 83 endpoints** (62 + 20 + 1)

---

## Section 1 — Already Compliant (24 routes)

No action needed. These were fixed in prior security waves (SEC-001, SEC-003, SEC-005, SEC-007, Wave BA).

| Route | Method | Decorator | Classification |
|-------|--------|-----------|----------------|
| `/api/download/<filename>` | GET | `@require_auth` + rate limit | AUTH_REQUIRED ✅ |
| `/api/valuation/report/download/<filename>` | GET | `@require_auth` + rate limit | AUTH_REQUIRED ✅ |
| `/api/reports` | GET | `@require_auth` + rate limit | AUTH_REQUIRED ✅ |
| `/api/reports/<id>` | GET | `@require_auth` + rate limit | AUTH_REQUIRED ✅ |
| `/api/reports/<id>/pdf` | GET | `@require_auth` + rate limit | AUTH_REQUIRED ✅ |
| `/api/market-feed` | POST | `@_require_admin` | ADMIN_REQUIRED ✅ |
| `/api/market-feed/<id>` | DELETE | `@_require_admin` | ADMIN_REQUIRED ✅ |
| `/api/enterprise/tenant` | POST | `@_require_admin` | ADMIN_REQUIRED ✅ |
| `/api/enterprise/tenant/<id>` | GET | `@_require_admin` | ADMIN_REQUIRED ✅ |
| `/api/enterprise/tenant/<id>/user` | POST | `@_require_admin` | ADMIN_REQUIRED ✅ |
| `/api/enterprise/tenant/<id>/license` | GET | `@_require_admin` | ADMIN_REQUIRED ✅ |
| `/api/enterprise/tenant/<id>/audit` | GET | `@_require_admin` | ADMIN_REQUIRED ✅ |
| `/api/saas/tenants` | POST | `@_require_admin` | ADMIN_REQUIRED ✅ |
| `/api/saas/tenants` | GET | `@_require_admin` | ADMIN_REQUIRED ✅ |
| `/api/saas/tenants/<id>` | GET | `@_require_admin` | ADMIN_REQUIRED ✅ |
| `/api/saas/tenants/<id>/users` | POST | `@_require_admin` | ADMIN_REQUIRED ✅ |
| `/api/saas/tenants/<id>/subscription` | PUT | `@_require_admin` | ADMIN_REQUIRED ✅ |
| `/api/saas/tenants/<id>/suspend` | POST | `@_require_admin` | ADMIN_REQUIRED ✅ |
| `/api/saas/tenants/<id>/reactivate` | POST | `@_require_admin` | ADMIN_REQUIRED ✅ |
| `/api/saas/tenants/<id>/billing/usage` | POST | `@_require_admin` | ADMIN_REQUIRED ✅ |
| `/api/saas/tenants/<id>/billing/invoice` | POST | `@_require_admin` | ADMIN_REQUIRED ✅ |
| `/api/saas/tenants/<id>/dashboard` | GET | `@_require_admin` | ADMIN_REQUIRED ✅ |
| `/api/saas/stats` | GET | `@_require_admin` | ADMIN_REQUIRED ✅ |
| `/api/admin/audit` | GET | `@_require_admin` + rate limit | ADMIN_REQUIRED ✅ |

---

## Section 2 — PUBLIC_OK (43 routes)

Correctly unprotected. No change needed.

| Route | Method | Function | Rationale |
|-------|--------|----------|-----------|
| `/api/<path:p>` | OPTIONS | `_pre` | CORS preflight catchall |
| `/` | GET | `serve_index` | Frontend HTML |
| `/<path>` | GET | `serve_static` | Static assets |
| `/agent` | GET | `agent_chat_ui` | Chat UI HTML page |
| `/api/advisor/health` | GET | `advisor_health` | Health check |
| `/api/iaao/health` | GET | `iaao_health` | Health check |
| `/api/health` | GET | `api_health_hardened` | Health check |
| `/api/market-feed` | GET | `market_feed_get` | Public market data read |
| `/api/avm/info` | GET | `api_avm_info` | Module metadata |
| `/api/marketplace/plugins` | GET | `api_marketplace_list_plugins` | Public browsing |
| `/api/marketplace/plugins/<id>` | GET | `api_marketplace_plugin_detail` | Public browsing |
| `/api/marketplace/trending` | GET | `api_marketplace_trending` | Public browsing |
| `/api/marketplace/info` | GET | `api_marketplace_info` | Module metadata |
| `/api/standards/frameworks` | GET | `api_standards_list_frameworks` | Reference data |
| `/api/government/info` | GET | `api_government_info` | Module metadata |
| `/api/banking/info` | GET | `api_banking_info` | Module metadata |
| `/api/funds/info` | GET | `api_funds_info` | Module metadata |
| `/api/knowledge/info` | GET | `api_knowledge_info` | Module metadata |
| `/api/knowledge/search` | GET | `api_knowledge_search` | Public knowledge read |
| `/api/knowledge/standards` | GET | `api_knowledge_standards_list` | Reference data |
| `/api/knowledge/standards/compatible` | POST | `api_knowledge_standards_compatible` | Reference check |
| `/api/knowledge/courses` | GET | `api_knowledge_courses_list` | Public catalog |
| `/api/knowledge/regulatory/updates` | GET | `api_knowledge_regulatory_updates` | Public reference |
| `/api/knowledge/regulatory/deadlines` | GET | `api_knowledge_regulatory_deadlines` | Public reference |
| `/api/knowledge/statistics` | GET | `api_knowledge_statistics` | Public stats |
| `/api/knowledge/search` | POST | `knowledge_search` | Public search |
| `/api/knowledge/stats` | GET | `knowledge_stats` | Public stats |
| `/api/analytics/info` | GET | `analytics_info` | Module metadata |
| `/api/analytics/market/trends` | GET | `analytics_market_trends` | Public market data |
| `/api/search/info` | GET | `search_info` | Module metadata |
| `/api/hardening/info` | GET | `api38_info` | Module metadata |
| `/api/integrations/info` | GET | `integ40_info` | Module metadata |
| `/api/market-indicators/latest` | GET | `mi41_latest` | Public market data |
| `/api/market-indicators/history` | GET | `mi41_history` | Public market data |
| `/api/market-indicators/statistics` | GET | `mi41_statistics` | Public market data |
| `/api/market-indicators/info` | GET | `mi41_info` | Module metadata |
| `/api/language/strings` | GET | `get_language_strings` | Static UI config |
| `/api/language/detect` | POST | `detect_language` | Public utility |
| `/api/price/trend` | GET | `price_trend` | Public market data |
| `/api/mass-appraisal/template-xlsx` | GET | `handle_mass_appraisal_template_xlsx` | Blank template, no data |
| `/api/integrations/oauth/<svc>/callback` | GET | `api_oauth_callback` | Must be public for OAuth redirect |
| `/api/docs/openapi.json` | GET | `api38_openapi_spec` | Public API discovery |
| `/api/price-index` | GET/POST | `handle_price_index` | ⚠ Tentative PUBLIC_OK — see DEFER note |

---

## Section 3 — AUTH_REQUIRED Gaps (62 routes)

All of these are currently unprotected. Each should receive `@require_auth` (and optionally a rate limit).

### 3A — Mass Appraisal: Government/Tax operations (10 endpoints)

| Route | Method | Function | Sensitivity |
|-------|--------|----------|-------------|
| `/api/mass-appraisal/run` | POST | `handle_mass_appraisal_run` | **CRITICAL** — bulk govt/tax computation |
| `/api/mass-appraisal/export-xlsx` | POST | `handle_mass_appraisal_export_xlsx` | HIGH — downloadable govt data |
| `/api/mass-appraisal/import-xlsx` | POST | `handle_mass_appraisal_import_xlsx` | HIGH — bulk property data ingest |
| `/api/mass-appraisal/preview` | POST | `handle_mass_appraisal_preview` | MEDIUM |
| `/api/mass-appraisal/sales/verify` | POST | `handle_mass_sales_verify` | MEDIUM |
| `/api/mass-appraisal/sales/time-adjust` | POST | `handle_mass_sales_time_adjust` | MEDIUM |
| `/api/mass-appraisal/sales/adjust` | POST | `handle_mass_sales_adjust` | MEDIUM |
| `/api/mass-appraisal/ratio-study/run` | POST | `handle_mass_ratio_study` | MEDIUM |
| `/api/mass-appraisal/calibration/preview` | POST | `handle_mass_calibration_preview` | MEDIUM |
| `/api/mass-appraisal/calibration/sandbox` | POST | `handle_mass_calibration_sandbox` | MEDIUM |

### 3B — Valuation pipeline (11 endpoints)

| Route | Method | Function | Sensitivity |
|-------|--------|----------|-------------|
| `/api/valuation/full` | POST | `api_valuation_full` | HIGH — full report + PDF |
| `/api/valuation/report` | POST | `api_valuation_report` | HIGH — can persist to DB |
| `/api/valuation/batch` | POST | `api_valuation_batch` | HIGH — bulk, generates files |
| `/api/valuation/batch` | GET | `api_valuation_batch_list` | MEDIUM — user data list |
| `/api/valuation/batch/<id>` | GET | `api_valuation_batch_status` | MEDIUM — user data |
| `/api/valuation/audit` | POST | `api_valuation_audit` | HIGH — CBE regulatory |
| `/api/valuation/land` | POST | `api_valuation_land` | MEDIUM |
| `/api/valuation/portfolio` | POST | `api_valuation_portfolio` | HIGH — financial |
| `/api/valuation/portfolio/performance` | POST | `api_valuation_portfolio_performance` | HIGH — financial |
| `/api/valuation/avm` | POST | `api_avm_valuation` | MEDIUM |
| `/api/valuation/avm/batch` | POST | `api_avm_batch_valuation` | MEDIUM |

### 3C — Assets (user-owned data) (6 endpoints)

| Route | Method | Function | Sensitivity |
|-------|--------|----------|-------------|
| `/api/assets` | GET | `assets_list` | HIGH — user data |
| `/api/assets/register` | POST | `assets_register` | HIGH — writes user data |
| `/api/assets/<id>` | GET | `assets_get` | HIGH — user data |
| `/api/assets/<id>/update` | PUT/POST | `assets_update` | HIGH — mutates user data |
| `/api/assets/dashboard` | GET | `assets_dashboard` | MEDIUM — user data |
| `/api/assets/<id>` | DELETE | `assets_delete` | **CRITICAL** — destructive, no auth |

### 3D — File operations (2 endpoints)

| Route | Method | Function | Sensitivity |
|-------|--------|----------|-------------|
| `/api/upload` | POST | `upload_image` | **CRITICAL** — unauthenticated file write |
| `/api/ingest` | POST | `ingest_file` | **CRITICAL** — unauthenticated bulk import |

### 3E — Banking / CBE (4 endpoints)

| Route | Method | Function | Sensitivity |
|-------|--------|----------|-------------|
| `/api/banking/collateral/value` | POST | `api_banking_collateral_value` | HIGH — Basel III regulated |
| `/api/banking/ltv/calculate` | POST | `api_banking_ltv_calculate` | HIGH — Basel III risk |
| `/api/banking/collateral/register` | POST | `api_banking_collateral_register` | HIGH — writes collateral record |
| `/api/banking/compliance/check` | POST | `api_banking_compliance_check` | HIGH — CBE regulatory |

### 3F — Funds / FRA (5 endpoints)

| Route | Method | Function | Sensitivity |
|-------|--------|----------|-------------|
| `/api/funds/fair-value/assess` | POST | `api_funds_fair_value_assess` | HIGH — IFRS 13 |
| `/api/funds/nav/calculate` | POST | `api_funds_nav_calculate` | HIGH — financial |
| `/api/funds/value` | POST | `api_funds_value` | HIGH — financial |
| `/api/funds/compliance/check` | POST | `api_funds_compliance_check` | HIGH — FRA regulatory |
| `/api/funds/dashboard/<manager_id>` | GET | `api_funds_dashboard` | HIGH — user-scoped financial |

### 3G — Government operations (3 endpoints)

| Route | Method | Function | Sensitivity |
|-------|--------|----------|-------------|
| `/api/government/compliance/check` | POST | `api_government_compliance_check` | HIGH — regulatory |
| `/api/government/tax/calculate` | POST | `api_government_tax_calculate` | HIGH — tax calculation |
| `/api/government/forms/generate` | POST | `api_government_forms_generate` | HIGH — official document |

### 3H — Analytics (user-scoped) (6 endpoints)

| Route | Method | Function | Sensitivity |
|-------|--------|----------|-------------|
| `/api/analytics/metrics/<id>/record` | POST | `analytics_record_metric` | MEDIUM — writes data |
| `/api/analytics/metrics/<id>/statistics` | GET | `analytics_metric_statistics` | MEDIUM |
| `/api/analytics/metrics/<id>/timeseries` | GET | `analytics_metric_timeseries` | MEDIUM |
| `/api/analytics/dashboards` | GET | `analytics_list_dashboards` | MEDIUM — user data |
| `/api/analytics/dashboards/<id>` | GET | `analytics_get_dashboard` | MEDIUM — user data |
| `/api/analytics/risk/portfolio/<id>` | POST | `analytics_portfolio_risk` | HIGH — financial risk |

### 3I — Integrations / Webhooks / OAuth (6 endpoints)

| Route | Method | Function | Sensitivity |
|-------|--------|----------|-------------|
| `/api/integrations/plugins` | GET | `api_integrations_list_plugins` | MEDIUM — per-user |
| `/api/integrations/webhooks` | GET | `api_integrations_list_webhooks` | MEDIUM — user data |
| `/api/integrations/webhooks` | POST | `api_integrations_create_webhook` | HIGH — creates persistent resource |
| `/api/integrations/webhooks/<id>` | DELETE | `api_integrations_delete_webhook` | HIGH — destructive |
| `/api/integrations/oauth/<svc>/authorize` | GET | `api_oauth_authorize` | HIGH — user OAuth flow |
| `/api/marketplace/plugins/<id>/reviews` | POST | `api_marketplace_add_review` | MEDIUM — UGC abuse risk |

### 3J — Other (9 endpoints)

| Route | Method | Function | Sensitivity |
|-------|--------|----------|-------------|
| `/api/fraud/detect` | POST | `fraud_detect` | HIGH — fraud data |
| `/api/reit/nav` | POST | `handle_reit_nav` | HIGH — financial |
| `/api/standards/uspap/generate` | POST | `api_uspap_generate` | HIGH — official appraisal doc |
| `/api/price/excel-table` | POST | `price_excel_table` | MEDIUM — file generation |
| `/api/agent/chat` | POST | `agent_chat` | MEDIUM — resource, user session |
| `/api/knowledge/courses/<id>/enroll` | POST | `api_knowledge_enroll` | MEDIUM — user action |
| `/api/library/scan` | POST | `library_scan` | MEDIUM — data write |
| `/api/library/add` | POST | `library_add_manual` | MEDIUM — data write |
| `/api/search/properties/register` | POST | `search_register_property` | MEDIUM — data write |

---

## Section 4 — ADMIN_REQUIRED Gaps (20 routes)

All currently unprotected. Each should receive `@_require_admin`.

| Route | Method | Function | Risk |
|-------|--------|----------|------|
| `/api/tune/profiles` | GET | `tune_list_profiles` | System config read |
| `/api/tune/profiles/<id>` | GET | `tune_get_profile` | System config read |
| `/api/tune/profiles/<id>` | DELETE | `tune_delete_profile` | **DESTRUCTIVE** — deletes AI system profile |
| `/api/tune/apply` | POST | `tune_apply_prompt` | **CRITICAL** — writes to AI system prompts |
| `/api/tune/analyze` | POST | `tune_analyze` | AI system analysis |
| `/api/library/<id>` | DELETE | `library_delete` | **DESTRUCTIVE** — deletes library record |
| `/api/radar/start` | POST | `radar_start` | Starts background scraping process |
| `/api/radar/stop` | POST | `radar_stop` | Stops background process |
| `/api/price/cache/clear` | POST | `price_cache_clear` | **Cache flush** — service impact / DoS vector |
| `/api/training/register` | POST | `training_register` | System config write |
| `/api/banking/dashboard/<bank_id>` | GET | `api_banking_dashboard` | Bank-scoped sensitive data |
| `/api/government/portal/create` | POST | `api_government_portal_create` | System config write |
| `/api/hardening/api-keys/generate` | POST | `api38_generate_key` | **Creates platform credentials** |
| `/api/hardening/integrations/register` | POST | `api38_register_integration` | System config write |
| `/api/hardening/integrations/stats` | GET | `api38_integration_stats` | Operational telemetry |
| `/api/integrations/plugins/<id>/install` | POST | `api_integrations_install_plugin` | **Code execution** — installs plugin |
| `/api/integrations/sync` | POST | `integ40_sync` | Triggers system sync |
| `/api/integrations/partners` | POST | `integ40_create_partner` | Creates partner account |
| `/api/integrations/partners/<id>/dashboard` | GET | `integ40_partner_dashboard` | Partner-scoped data |
| `/api/integrations/connector-webhooks` | POST | `integ40_register_webhook` | System config write |

---

## Section 5 — INTERNAL_ONLY Gap (1 route)

Should be removed from public routing or restricted to localhost/internal network only.

| Route | Method | Function | Risk |
|-------|--------|----------|------|
| `/api/hardening/api-keys/validate` | POST | `api38_validate_key` | Auth-system maintenance. No business user should call this. Exposing it publicly creates an oracle for credential probing. |

---

## Section 6 — DEFER_REVIEW (17 routes)

These require an explicit product/stakeholder decision before auth can be assigned. Default recommendation: apply `@require_auth` and remove when a deliberate public-access decision is made.

| Route | Method | Function | Question |
|-------|--------|----------|----------|
| `/api/valuation` | POST | `handle_valuation` | **Most impactful.** Core product API — public demo tier or auth-required? |
| `/api/advisor` | POST | `advisor_endpoint` | Public AI assistant or auth-tracked? |
| `/api/valuation/dcf` | POST | `api_valuation_dcf` | Pure stateless calc — public tool or auth? |
| `/api/scenarios/run` | POST | `scenarios_run` | Pure stateless calc |
| `/api/scenarios/monte_carlo` | POST | `scenarios_monte_carlo` | Pure stateless calc |
| `/api/scenarios/sensitivity` | POST | `scenarios_sensitivity` | Pure stateless calc |
| `/api/scenarios/stress_test` | POST | `scenarios_stress_test` | Pure stateless calc |
| `/api/comparables/search` | POST | `api_comparable_search` | Public data search or auth? |
| `/api/engines/comparative` | POST | `api_engine_comparative` | Raw engine — public or internal? |
| `/api/engines/cost` | POST | `api_engine_cost` | Raw engine |
| `/api/engines/income` | POST | `api_engine_income` | Raw engine |
| `/api/standards/validate` | POST | `api_standards_validate` | Standards check tool — public? |
| `/api/iaao` | POST | `iaao_compute` | IAAO ratio tool — public regulatory tool? |
| `/api/price-map` | POST/GET | `price_map` | Public heatmap or auth? |
| `/api/knowledge/enhance` | POST | `knowledge_enhance` | RAG augmentation — public or rate-limited? |
| `/api/language/set/<code>` | POST | `set_language` | Session preference — stateless, public OK? |
| `/api/price/intelligence` | POST | `price_intelligence_search` | Search tool — public or auth? |

---

## Section 7 — Top 10 Highest-Risk Gaps

| Priority | Route | Risk Level | Reason |
|----------|-------|------------|--------|
| 1 | `POST /api/mass-appraisal/run` | CRITICAL | Unauthenticated trigger of bulk govt/tax computation |
| 2 | `POST /api/valuation/batch` | CRITICAL | Bulk operation, persists user results, no auth |
| 3 | `POST /api/upload` | CRITICAL | Unauthenticated file write to server filesystem |
| 4 | `POST /api/ingest` | CRITICAL | Unauthenticated bulk data import |
| 5 | `DELETE /api/tune/profiles/<id>` | CRITICAL | Unauthenticated deletion of AI system config |
| 6 | `POST /api/tune/apply` | CRITICAL | Unauthenticated write to AI system prompts |
| 7 | `POST /api/price/cache/clear` | HIGH | Unauthenticated cache flush — DoS vector |
| 8 | `POST /api/hardening/api-keys/generate` | HIGH | Creates platform credentials without auth |
| 9 | `POST /api/integrations/plugins/<id>/install` | HIGH | Unauthenticated plugin installation (code execution) |
| 10 | `POST /api/government/forms/generate` | HIGH | Unauthenticated official government document generation |

---

## Section 8 — Proposed Remediation Waves

### SEC-002a — Destructive operations + file writes (10 endpoints)
*No product-policy ambiguity. All are clearly destructive or file-system-level. Highest blast radius.*

Targets:
- `DELETE /api/tune/profiles/<id>` → `@_require_admin`
- `POST /api/tune/apply` → `@_require_admin`
- `POST /api/price/cache/clear` → `@_require_admin`
- `POST /api/hardening/api-keys/generate` → `@_require_admin`
- `POST /api/integrations/plugins/<id>/install` → `@_require_admin`
- `DELETE /api/library/<id>` → `@_require_admin`
- `POST /api/upload` → `@require_auth`
- `POST /api/ingest` → `@require_auth`
- `DELETE /api/assets/<id>` → `@require_auth`
- `POST /api/hardening/api-keys/validate` → INTERNAL_ONLY

### SEC-002b — Mass appraisal + valuation pipeline (21 endpoints)
*Government/tax/banking sensitive; large operations; user-result persistence.*

Targets: all 10 `/api/mass-appraisal/*` write endpoints + all 11 `/api/valuation/(full|report|audit|land|portfolio|portfolio/performance|batch*|avm*)` endpoints → `@require_auth`

### SEC-002c — Financial regulated + assets + admin ops (18 endpoints)
*CBE/FRA/government regulated operations; user-owned asset CRUD.*

Targets:
- All 4 `/api/banking/collateral|ltv|compliance` endpoints + `api_banking_dashboard` (→ `@_require_admin`) → `@require_auth` / `@_require_admin`
- All 5 `/api/funds/*` endpoints → `@require_auth`
- 3 `/api/government/*` operation endpoints → `@require_auth`
- All 6 `/api/assets/*` endpoints → `@require_auth`
- `/api/radar/start`, `/api/radar/stop` → `@_require_admin`
- `/api/training/register` → `@_require_admin`
- `/api/government/portal/create` → `@_require_admin`

### SEC-002d — Integrations, analytics, remaining admin ops (16 endpoints)
*Lower urgency; user-scoped integrations and analytics.*

Targets:
- 5 `/api/integrations/webhooks*` + `oauth/authorize` + `plugins` list → `@require_auth`
- 6 `/api/analytics/*` user-scoped → `@require_auth`
- `integ40_sync`, `integ40_create_partner`, `integ40_partner_dashboard`, `integ40_register_webhook` → `@_require_admin`
- `api38_register_integration`, `api38_integration_stats` → `@_require_admin`

### SEC-002e — Product policy decisions required (17 endpoints)
*Requires stakeholder input before implementation.*

Recommendation if no decision is reached: default to `@require_auth`, document as temporary pending explicit public-access approval.

---

## Section 9 — Production Gate Status

| Item | Status |
|------|--------|
| SEC-001 Path traversal `/api/download` | ✅ Fixed |
| SEC-002 Broad auth classification | ⚠ **CLASSIFIED — remediation pending** |
| SEC-003 Enterprise/SaaS unprotected | ✅ Fixed |
| SEC-004 `str(e)` leaks | ✅ Fixed |
| SEC-005 Valuation report download | ✅ Fixed |
| SEC-006 CORS wildcard | ✅ Fixed |
| SEC-007 Market feed write auth | ✅ Fixed |
| SEC-008 Audit prefix gaps | ✅ Fixed |
| SEC-009 `.env.example` missing | ✅ Fixed |
| `service_account.json` key rotation | ⚠ Open (tracked separately, PH.3) |

**Production Gate: NO-GO** — 83 auth gaps confirmed open across SEC-002a–d. Gate will upgrade to CONDITIONAL-GO after SEC-002a+b are complete (highest-risk 31 endpoints resolved).

---

*Generated by SEC-002 classification audit. No code was modified during this audit.*
*Next step: approve SEC-002a wave implementation.*
