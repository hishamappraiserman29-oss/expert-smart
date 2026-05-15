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

## R3.3+ — Pending

WIP subsystems not yet reviewed:
- `adapters/` (market_value, mortgage, insurance, ifrs_13, residential, commercial, land, enterprise, asset)
- `agents/`
- `analytics/`
- `banking_expert/`
- `ml/`
- `government/` ✅ merged
- `banking/` ✅ merged
- `funds/` ✅ merged
- `database/` deferred
- `security/` ✅ merged (R3.1)
- (others as identified on WIP)

Review to be scheduled in separate sessions.
