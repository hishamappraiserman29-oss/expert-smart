# R3 Subsystem Review Log

Branch reviewed: `wip/r3-subsystems-checkpoint`
WIP baseline: 1606/1606 tests passing

---

## R3.1 — Gate Decision (2026-05-16)

### `core_engine/security/` — ALREADY ON MAIN

Merged via `feature/r3-1-security-only` → commit `6b35448`.

Applied rename: `ValidationResult` → `SanitisationResult` to avoid collision with
`reports.validation.ValidationResult`.

Files: 4 / ~768 lines
Tests: 28 (A01–A10 InputValidator, B01–B06 RateLimiter, C01–C12 SecretsScanner)
Dependencies: none beyond stdlib

No further action required.

---

### `core_engine/database/` — DEFERRED

Decision: **DEFER**
Date: 2026-05-16

Files: 10 / ~1,904 lines
Tests: 0
Missing from `requirements.txt`: `sqlalchemy`, `psycopg2`

Reasons for deferral:
1. Zero unit or integration tests.
2. `sqlalchemy` and `psycopg2` missing from `requirements.txt` — would break CI.
3. Requires live PostgreSQL instance; dead code on main without it.
4. Dual `AuditLog` naming collision: `database/models.py` (SQLAlchemy ORM) vs
   `database/audit_log.py` (SQLite dataclass) — both export `AuditLog`.
5. All `bridge_api.py` references to `database/` are already guarded with
   `try/except ImportError` on main — no functional regression from deferring.

Prerequisites before re-review:
- Write unit/integration tests for `database/` modules
- Add `sqlalchemy` + `psycopg2-binary` to `requirements.txt`
- Resolve `AuditLog` naming collision between `models.py` and `audit_log.py`

---

## R3.2 — Gate Decision (2026-05-16)

Feature branch: `feature/r3-2-government-banking-funds-review`
Merge commit: `f8c89c3`
Full suite after merge: 665/665 passed

### `core_engine/government/` — MERGED

Files: 7 / ~1,691 lines | Tests: 49 ✅
Fix applied before merge: `digital_signature.py` — removed hardcoded HMAC fallback
`"expert_smart_gov_default_key"`. Now requires `secret_key` arg or
`GOVERNMENT_SIGNATURE_SECRET` env var; raises `ValueError` if neither provided.
Module-level singleton `digital_signature_manager = DigitalSignatureManager()`
removed (bridge_api never used it). Commit: `ae4884d`.

### `core_engine/banking/` — MERGED

Files: 10 / ~2,195 lines | Tests: 64 ✅
No changes required. 5 files use `datetime.utcnow()` (deprecated Python 3.12+)
— warnings only, no failures. To be cleaned up in a follow-up.

### `core_engine/funds/` — MERGED

Files: 11 / ~2,123 lines | Tests: 70 ✅
Cleanup applied before merge: converted absolute `from funds.X import` to
relative `from .X import` in `__init__.py`, `fund_dashboard.py`,
`valuation_hierarchy.py`. Commit: `ae4884d`.

---

## R3.3 — Gate Decision (2026-05-17)

Branch reviewed: `wip/r3-subsystems-checkpoint`
Cherry-picks onto: `main`
Full suite after all three merges: **967 / 967 passed ✅**

### `core_engine/analytics/` — MERGED

Commit cherry-picked: `fa4afe6` → landed as `64657f3`
Files: 7 / ~1,009 lines | Tests: 50 ✅
Dependencies: pure stdlib
Modules: `analytics_engine`, `dashboard_system`, `forecasting`, `market_intelligence`, `portfolio_risk`
Endpoints unlocked: 8 (`/api/analytics/*`) — guard `_ANALYTICS_OK` was already wired in `bridge_api.py`

### `core_engine/search/` — MERGED

Commit cherry-picked: `e5b1d4e` → landed as `b8bc953`
Files: 5 / ~742 lines | Tests: 34 ✅
Dependencies: pure stdlib — no dependency on `analytics/` or `ml/`
Modules: `comparable_search`, `similarity_matcher`, `adjustment_factors`
Endpoints unlocked: 4 (`/api/search/*`) — guard `_SEARCH_OK` was already wired in `bridge_api.py`

### `core_engine/ml/` — MERGED

Commit cherry-picked: `086fdc8` → landed as `0434a9d`
Files: 8 / ~1,550 lines | Tests: 52 ✅
Dependencies: `numpy`, `pandas`, `scikit-learn`, `joblib` (all installed); XGBoost optional (guarded internally)
Modules: `avm_predictor`, `data_processor`, `feature_engineer`, `model_registry`, `model_trainer`, `model_validator`
Endpoints unlocked: 3 (`/api/ml/*`) — guard `_ML_OK` was already wired in `bridge_api.py`
Note: No model binary files in repo (all pure Python, largest commit 121K).

---

## R3.4 — Gate Decision (2026-05-17)

Cherry-picks onto: `main`
Full suite after all merges: **1,227 / 1,227 passed ✅**

### Prerequisite: `mcp_bridge` + `mcp_setup` + `market_indicators` — MERGED

Commit cherry-picked: `7e3ec3b` → landed as `2db154c`
Files: 5 (`mcp_bridge.py`, `mcp_setup.py`, `market_indicators.py`, `test_phase_16_e2e.py`, `test_phase_16_1_e2e.py`)
Required by: agents test files import `from mcp_bridge import APIResponse`
Tests: 20 / 20 ✅

### `core_engine/agents/` — MERGED

Commit cherry-picked: `4f9cc8a` → landed as `6c64b8a`
Files: 14 (7 modules + __init__ + 6 test files), ~2,190 source lines | Tests: 94 ✅
Dependencies: **100% stdlib** — no LLM provider, no network
Modules: `workspace_manager`, `file_scanner`, `file_watcher`, `pipeline_orchestrator`, `supervised_agent`, `command_parser`, `chat_agent`
Endpoints unlocked: chat UI + `/api/agent/chat` — guard `_CHAT_OK` was already wired in `bridge_api.py`

### `core_engine/knowledge/` — MERGED

Commit cherry-picked: `cac0d0d` → landed as `46b5e2f`
Files: 12 (10 modules + __init__ + 2 test files), ~2,350 source lines | Tests: 92 ✅
Dependencies: pure stdlib; Qdrant/Ollama optional (graceful HTTP fallback to empty list)
All tests use `auto_embed=False` — no network calls at test time

### `core_engine/integrations/` — MERGED

Commit cherry-picked: `9d29696` → landed as `d7136c2`
Files: 11 (9 modules + connectors/bank_connector + 1 test file), ~1,273 source lines | Tests: 54 ✅
Dependencies: `requests` (optional guard `_REQUESTS_OK`); OAuth/webhook stdlib HMAC
Tests use `http://localhost:19999` (intentionally unreachable) — all verify graceful offline behavior

### Cross-cutting notes

- Zero inter-subsystem dependencies (agents ↔ knowledge ↔ integrations = independent)
- No LLM provider packages anywhere in the three subsystems
- No hardcoded API keys or secrets
- **Test infrastructure fix**: `nest-asyncio` added to `requirements-dev.txt`; `core_engine/tests/conftest.py` applies `nest_asyncio.apply()` at session start. Root cause: `pytest-playwright` leaves the C-level asyncio TSS running-loop pointer set after its session teardown, causing `asyncio.run()` to raise in later tests. `nest_asyncio` patches the stdlib loop to allow nested calls. The WIP branch's 1,606-test baseline never exhibited this because the `e2e/` Playwright tests were added to `main` AFTER the WIP branch was cut.
- No env vars required for any of the three subsystems

---

## R3.5 — Gate Decision (2026-05-17)

Cherry-picks onto: `main`

### `core_engine/marketplace/` + `core_engine/plugins/` — MERGED

Commit cherry-picked: `9170ebd` → landed as `5e8f44c`
Files: 7 source + 1 test (8 total), ~757 source lines | Tests: 53 ✅
Dependencies: pure stdlib; `stripe` optional (guarded try/except ImportError in example plugin only)
Modules: `marketplace` (catalog, listings, reviews, installations), `plugins` (plugin_system, plugin_registry, StripePlugin example)
Endpoints unlocked: 7 (`/api/marketplace/*` + `/api/integrations/plugins/*`) — guard `_MARKETPLACE_OK` was already wired in `bridge_api.py`

Security notes:
- Zero hardcoded secrets; no `sk_live_*` / `sk_test_*` anywhere
- Plugin mechanism: static registry only — no `exec`/`eval`/`importlib` dynamic loading
- Payment tests (F01–F06) use `PaymentProvider.MOCK` only — no live Stripe calls

### `core_engine/saas/` — DEFERRED

Decision: **DEFER**
Date: 2026-05-17

Files: 6 source + 4 test files | Tests: 103 ✅ (on WIP)
Source modules are clean and ready. Deferral is due to test dependencies.

Reasons for deferral:
1. `test_phase39_saas.py` imports from `scripts/` module (WIP commit `cb4b5d4`, not on main).
2. `test_phase_15_2_e2e.py` imports from `database.audit_log` (AuditAction, AuditEvent, AuditLog)
   — the `database/` module was deferred in R3.1; selective extraction of one file risks
   partial subsystem merge and future naming conflicts.
3. `tenant_id` / `owner_user_id` bridge is undocumented (two parallel identity models).
4. `scripts/` deferred to R3.6 or separate approval.

Prerequisites before re-review:
- `database/audit_log.py` naming/design resolved and standalone extraction approved, OR
  full `database/` deferred blockers closed (tests + sqlalchemy + AuditLog collision)
- `scripts/` reviewed in R3.6 or separately approved
- `tenant_id` / `owner_user_id` bridge documented in security ADR

Security check: clean ✅ — no hardcoded secrets, no payment provider calls, pure in-memory billing

---

## R3.6 — Gate Decision (2026-05-17)

Cherry-picks onto: `main`
Full suite after all three merges: **1,349 / 1,349 passed ✅**

### `core_engine/performance/` — MERGED

Commit cherry-picked: `41c0b16` → landed as `aae8af5`
Files: 4 source + 1 test (5 total), ~692 source lines | Tests: 35 ✅
Dependencies: pure stdlib (no external deps)
Modules: `cache` (TTLCache, @cached decorator), `paginator` (Paginator, PageRequest, PageResult), `profiler` (PerformanceProfiler, @timed decorator)
Full suite after merge: **1,315 / 1,315 passed ✅**

### `core_engine/deployment/` — MERGED

Commit cherry-picked: `8ee22b5` → landed as `34aae58`
Files: 3 source + 1 __init__ + 1 test (5 total), ~794 source lines | Tests: 34 ✅
Dependencies: pure stdlib; `python-dotenv` optional (guarded)
Modules: `config` (AppConfig dataclass, ConfigValidator, load_config()), `health` (HealthChecker, per-check timeout threading), `startup` (StartupValidator, pre-flight checks)
Security notes: `secret_key` redacted in `config.to_dict()` output; no hardcoded secrets; `EXPERT_SMART_*` env-var namespace
Full suite after merge: **1,349 / 1,349 passed ✅**

### `core_engine/scripts/` — MERGED

Commit cherry-picked: `cb4b5d4` → landed as `e731001`
Files: 11 CLI scripts, 0 test files
Dependencies: `boto3` optional (S3 upload guarded); `pg_dump` subprocess (external, not packaged); `requests` optional
Modules: `backup_manager`, `api_health_check`, `health_check`, `loadtest`, `saas_readiness_check`, `saas_operations`, `sync_runner`, `evaluate_avm_model`, `train_avm_model`, `populate_knowledge_base`, `install_plugin`
Security notes: `PGPASSWORD` extracted from `DATABASE_URL` env var via `_extract_password()`; never hardcoded; `cleanup_old_backups()` scoped to backup dir only
Full suite after merge: **1,349 / 1,349 passed ✅** (no new tests — scripts/ contains no test files)

### saas/ blocker update

- **B1** (`test_phase39_saas.py` needs `scripts/` module): ✅ **RESOLVED** — `scripts/` is now on main
- **B2** (`test_phase_15_2_e2e.py` needs `database.audit_log`): ❌ **STILL OPEN** — `database/` deferred (R3.1)
- saas/ remains **DEFERRED** until B2 is resolved

---

## R3.7 — Gate Decision (2026-05-17)

Cherry-picks onto: `main`
Full suite after all three merges: **1,491 / 1,491 passed ✅**

### `core_engine/i18n/` — MERGED

Commit cherry-picked: `d288d0d` → landed as `01f79e2`
Files: 4 source + 1 __init__ + 1 test (6 total), ~539 source lines | Tests: 56 ✅
Dependencies: pure stdlib (no external deps)
Modules: `localization` (Language enum, Localization class, date/currency/number formatters), `translations` (63-key EN/AR/FR dict parity), `arabic_support` (ArabicSupport — Arabic numerals, dates, currency, RTL detection), `language_detector` (LanguageDetector — text/header/browser/preference detection)
Overlap notes:
  - `arabic_support.py` vs `pdf_arabic.py`: complementary layers — `arabic_support` = business data formatting; `pdf_arabic` = PDF glyph rendering (reshape+bidi). No unification needed.
  - `multilingual_builder.py` on main had dangling top-level `from i18n.localization import ...` — merging i18n satisfies it.
  - `frontend/localization.js` on main consumes `/api/language/strings` — now live.
Full suite after merge: **1,405 / 1,405 passed ✅**

Follow-up items:
- [ ] Confirm `pdf_arabic.py` and `arabic_support.py` coexist without confusion — no unification needed unless a future refactor ticket is opened

### `core_engine/standards/` — MERGED

Commit cherry-picked: `c72bafd` → landed as `e4a3f6a`
Files: 2 source + 1 __init__ + 1 test (4 total), ~526 source lines | Tests: 40 ✅
Dependencies: pure stdlib (no external deps)
Modules: `uspap` (USPAPCompliance, USPAPReport, USPAPComplianceChecker, USPAPComplianceAddenum — USPAP-oriented disclosure framework), `standards_manager` (StandardsManager — EGVS/IVSC/USPAP/IFRS13/CBE registry)
Notes:
  - All 5 frameworks: `calculation_impact: False` — valuation engines untouched
  - AVM/mass-appraisal USPAP compliance level guards (blocks APPRAISER_CERTIFIED)
  - `datetime.utcnow()` deprecation warnings in tests — advisory only, no failures
  - USPAP text is English-only; no Egyptian Law 148/2001 coverage
  - USPAP edition year not stated in addendum text
Full suite after merge: **1,445 / 1,445 passed ✅**

Follow-up items (content review required before production use):
- [ ] Domain expert (د. عبد الرؤوف) review: USPAP edition year, Egyptian Law 148/2001 coverage, Arabic compliance text for Egyptian audience
- [ ] Add `USPAP_EDITION = "2024"` constant to `standards_manager.py` before production use

### `core_engine/scenarios/` — MERGED

Commit cherry-picked: `b573098` → landed as `0a9538f`
Files: 4 source + 1 __init__ + 1 test (6 total), ~607 source lines | Tests: 46 ✅
Dependencies: pure stdlib (`random`, `math` only — no ml/, no validation/)
Modules: `scenario_builder` (ScenarioBuilder, Optimistic/Base/Pessimistic/Custom), `monte_carlo` (MonteCarloEngine, 10K iterations default, `seed` config), `sensitivity_matrix` (SensitivityMatrix, 2-variable grid), `stress_test` (StressTestSuite, 5 built-in EG market scenarios + custom extensibility)
Notes:
  - Zero ml/ dependency — pure Python stochastic simulation
  - 5 Egypt-specific stress scenarios: COVID, CBE rate hike, EGP devaluation, market crash, recovery
  - `MonteCarloConfig.seed = None` by default (non-reproducible); `seed=42` in tests for reproducibility
  - 10K iterations runs < 1s — no timeout concern
Full suite after merge: **1,491 / 1,491 passed ✅**

Follow-up items:
- [ ] Document random seed policy: `seed=None` is intentional for non-reproducible API use; callers needing reproducibility must pass explicit seed

---

## R3.8+ — Pending

WIP subsystems not yet reviewed:
- `adapters/` (market_value, mortgage, insurance, ifrs_13, residential, commercial, land, enterprise, asset)
- `banking_expert/`
- `database/` deferred (see R3.1 deferral above; prerequisite for saas/)
- `saas/` deferred (see R3.5 deferral above; B1 resolved, B2 still open)
- (others as identified on WIP)

Previously merged:
- `i18n/` ✅ merged (R3.7)
- `standards/` ✅ merged (R3.7)
- `scenarios/` ✅ merged (R3.7)
- `performance/` ✅ merged (R3.6)
- `deployment/` ✅ merged (R3.6)
- `scripts/` ✅ merged (R3.6)
- `marketplace/` + `plugins/` ✅ merged (R3.5)
- `agents/` ✅ merged (R3.4)
- `knowledge/` ✅ merged (R3.4)
- `integrations/` ✅ merged (R3.4)
- `analytics/` ✅ merged (R3.3)
- `search/` ✅ merged (R3.3)
- `ml/` ✅ merged (R3.3)
- `government/` ✅ merged (R3.2)
- `banking/` ✅ merged (R3.2)
- `funds/` ✅ merged (R3.2)
- `security/` ✅ merged (R3.1)

Review to be scheduled in separate sessions.
