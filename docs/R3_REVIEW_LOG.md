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

## R3.6+ — Pending

WIP subsystems not yet reviewed:
- `adapters/` (market_value, mortgage, insurance, ifrs_13, residential, commercial, land, enterprise, asset)
- `banking_expert/`
- `scripts/` — deferred, candidate for R3.6
- `database/` deferred (see R3.1 deferral above; prerequisite for saas/)
- `saas/` deferred (see R3.5 deferral above)
- (others as identified on WIP)

Previously merged:
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
