# Changelog

All notable changes to EXPERT_SMART are documented here.

This project follows [Keep a Changelog](https://keepachangelog.com/) and [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

*(no unreleased changes)*

---

## [1.1.2] — 2026-05-20 — Conditional Release (R3 final closure)

**Type:** CONDITIONAL — PH.3 GCP key rotation still pending.  
**Tag:** `v1.1.2` (not yet created — pending approval).  
**Handoff:** `docs/FINAL_RELEASE_HANDOFF_v1.1.2.md`  
**Base:** builds on `v1.1.1` (Frontend Auth #7b + PH.3 runbook).

### Added

#### database/ subsystem (R3.10 — commit `d94a847`)
- `database/models.py` — SQLAlchemy ORM models: `Comparable`, `Valuation`, `QualityAudit`, `ActivityLog` (renamed from `AuditLog` to avoid collision with enterprise audit log).
- `database/connection.py` — lazy engine factory, `SessionLocal` proxy, `get_db()`, `ping_db()`, `init_db()`.
- `database/audit_log.py` — SQLite enterprise audit log: `AuditAction` enum (8 actions), `AuditEvent` dataclass, `AuditLog` class (record/get/count/filter).
- `database/batch_store.py` — SQLite-backed batch result persistence.
- `database/webhook_log.py` — SQLite webhook delivery log.
- `database/__init__.py` — exports `Base`, `Comparable`, `Valuation`, `QualityAudit`, `ActivityLog`.
- 74 new tests (ORM integration + audit log unit).

#### saas/ subsystem (R3.11 — commit `b99187c`)
- `saas/tenant_manager.py` — in-memory multi-tenant registry with `TenantStatus`, `UserRole`, `SubscriptionTier` enums and `TIER_LIMITS`.
- `saas/billing_engine.py` — usage metering (`UsageMetric`), invoice generation (no live payment).
- `saas/subscription_manager.py` — full lifecycle: trial/paid/upgrade/downgrade/suspend/cancel/expire.
- `saas/tenant_isolation.py` — `TenantIsolationValidator`, `require_tenant_context` decorator.
- `saas/dashboard.py` — `TenantDashboard`: overview, analytics, billing summary, platform stats.
- 11 new enterprise API endpoints (`/api/enterprise/*`) — all `@_require_admin` (SEC-003).
- Enterprise audit trail: tenant creation and user add events auto-recorded.
- 105 new tests (API integration + unit: `test_phase_15_e2e.py`, `test_phase_15_2_e2e.py`, `test_phase39_saas.py`, `test_saas_readiness.py`).

#### E2E test bundle (R3.12 — commit `3ec8de5`)
- `test_phase_8_e2e.py` — SQLite/SQLAlchemy ORM writes + 3 valuation API calls (15 tests).
- `test_phase_10_e2e.py` — DCF model math + 2 DCF API calls (6 tests).
- `test_phase_11_e2e.py` — Portfolio performance scenarios + 2 API calls + sheet builder (17 tests).
- `test_phase_11_complete.py` — Portfolio E2E pipeline + 2 API calls (10 tests).
- `test_phase_12_e2e.py` — BatchProcessor + 8 batch API calls + report builder + registry (21 tests).
- `test_phase_13_e2e.py` — BatchStore SQLite persistence + 3 API calls (11 tests).
- `test_phase_14_e2e.py` — WebhookDispatcher + WebhookLog + 1 async webhook API call (12 tests).

### Fixed
- **CI dependency gap (commit `f20160f`):** `SQLAlchemy>=2.0,<3.0` added to `core_engine/requirements.txt`. `database/models.py` imports SQLAlchemy at module load time; the package was installed ad-hoc on developer machines but absent from requirements, causing `ModuleNotFoundError` during pytest collection in CI.

### Tests
- Full suite: **2,076 tests, all passing** (up from 1,858 at v1.1.0 / 1,971 at v1.1.1).
- GitHub Actions CI: green.

---

## [1.1.0] — 2026-05-19 — Conditional Release

**Type:** CONDITIONAL — see `docs/PH3_KEY_ROTATION_WAIVER.md`.  
**Tag:** `v1.1.0` on commit `8671de5`.  
**Handoff:** `docs/FINAL_RELEASE_HANDOFF_v1.1.0.md`

### Security
- **SEC-011 fixed:** `auth/__init__.py` changed to relative import (`from .tokens import ...`).
  Resolves silent auth-import failure that caused `_AUTH_AVAILABLE = False` in all deployment
  modes (subprocess, waitress, Docker), returning 401 to all users regardless of token.
- **SEC-002e complete:** `@require_auth` enforced on `/api/reports*` and `/api/valuation`.
  Owner isolation via `owner_user_id`. Rate limiting active per user.
- **SEC-001–SEC-009:** All security audit findings remediated.
- **Startup warning:** `CRITICAL` log emitted if auth module fails to import in future.
- **PH.3 waiver:** Google service account key rotation formally waived (pending MFA).
  Repo contains no credential key material. Waiver ID: `PH3-GCP-SA-KEY-ROTATION`.

### CI / Testing
- `nest_asyncio` and `fastmcp` pinned in `requirements-dev.txt` — fixes two CI import failures.
- Docker GHCR push gated to `workflow_dispatch` — prevents permission errors on normal CI pushes.
- E2E test updated to filter expected auth 401 from `POST /api/radar/start`.
- 7 new regression tests: `core_engine/tests/test_auth_import_paths.py` (IP01–IP07).
- Test suite: **1858 tests, all passing**.

### Tooling
- `tools/production_dry_run.py` — versioned dry-run orchestrator (no hardcoded paths).
  Fixes: `AUDIT_DB_PATH` env var + `timeout=30` for valuation probe. Result: **21/21 checks pass**.

### Documentation
- `docs/SECURITY_AUDIT_v1.md` — post-audit status table (SEC-001–SEC-014 + PH.3).
- `docs/PROD_READINESS_CHECKLIST.md` — gate summary updated to CONDITIONAL-GO.
- `docs/PH3_KEY_ROTATION_WAIVER.md` — formal waiver with three closure options.
- `docs/PRODUCTION_DRY_RUN.md` — full dry-run report; verdict GO (21/21).
- `docs/FINAL_RELEASE_HANDOFF_v1.1.0.md` — release handoff (this release).

### Added

#### R3.2 — Government, Banking, Funds Pilot Subsystems
- `government/` — compliance engine, tax calculator, forms generator, audit trail,
  digital signature (HMAC; requires `GOVERNMENT_SIGNATURE_SECRET` env var), government portal.
  Egyptian CBE / EGFSA / Tax Authority / Ministry of Finance. 49 tests.
- `banking/` — collateral valuation, LTV calculator (Basel III weights), collateral registry,
  risk assessment, CBE compliance tracker, loan servicing, market monitoring, bank dashboard.
  64 tests.
- `funds/` — fair value (IFRS 13 Level 1/2/3), NAV calculator, fund valuation engine,
  FRA compliance, portfolio manager, valuation hierarchy, benchmark system, fund dashboard,
  risk analytics (VaR). 70 tests.

#### R3.1 — Security Subsystem
- `security/input_validator.py` — `InputValidator` + `SanitisationResult` (UUID, path, property
  type, area, location, execution mode, purpose, batch, sanitize).
- `security/rate_limiter.py` — sliding-window `RateLimiter` + `RateLimitResult`, thread-safe.
- `security/secrets_scanner.py` — `SecretsScanner` + `SecretFinding`; regex patterns for AWS keys,
  Google API keys, private keys, hardcoded passwords, JWT tokens.
- 28 tests covering all three components.

#### CI / CD
- `.github/workflows/ci-cd.yml` — 4-job pipeline: test → lint → build → deploy.
  Deploy gated to `workflow_dispatch` only (not auto-triggered on push).
- `docs/CI_ACTIVATION_NOTES.md` — activation steps, secrets required, rollback procedure.
- `docs/SECURITY_PLAN_REPORTS_API.md` — auth/authorization/rate-limiting plan for `/api/reports*`.

---

## [1.0.0] — 2026-05-16

First production-ready release. Introduces **Shared Core Architecture** with three isolated
engines, full Bridge API integration, and a frontend history panel.

### Added

#### Core Architecture
- `report_profiles.py` — frozen-dataclass registry for `legacy` / `detailed` / `professional_template`.
- `report_theme.py` — Midnight Gold design system (Navy + Gold palette, Cairo typography).
- `excel_builder.py` — refactored to consume `report_theme` + `sheets/` modules.
- Seven sheet modules under `core_engine/reports/sheets/`:
  inputs / main_report / sales_comparison / cost_approach / income_approach / reconciliation / certification.

#### PDF Engine (`core_engine/reports/pdf/`)
- Public API: `generate_pdf(profile_key, data, output_path)`.
- `fpdf2` + bundled Cairo TTF for Arabic shaping/bidi.
- Deterministic output (byte-identical for identical input).
- 4 profile-aware sections.

#### Validation Engine (`core_engine/reports/validation/`)
- `validate_report(data, profile_key)` returning `ValidationResult`.
- Three severities: `ERROR` / `WARNING` / `INFO`.
- Bilingual messages (Arabic + English) + stable machine-readable codes.

#### DB Engine (`core_engine/reports/db/`)
- SQLite-backed persistence: `save_report` / `get_report` / `list_reports` /
  `update_report` / `delete_report` / `count_reports`.
- Hybrid schema (indexed columns + JSON blob).
- `CHECK(id=1)` single-row schema_version guard.
- Forward-only migrations.
- Round-trip JSON fidelity for Arabic content.

#### Bridge API (`bridge_api.py`)
- Opt-in `"validate": true` — ERROR ⇒ 422, WARNING ⇒ 200 + warnings block.
- Opt-in `"persist": true` — non-fatal auto-save with `report_db_id`.
- Opt-in `"pdf": true` — generates PDF alongside Excel.
- `GET /api/reports`, `GET /api/reports/<id>`, `GET /api/reports/<id>/pdf` (additive).
- `report_pipeline.py` facade.

#### Frontend (`frontend/index.html`)
- Saved reports history panel + profile/status filters.
- Detail overlay + PDF download button.
- No-auto-load policy (page works when backend is down).
- Localisation (`frontend/localization.js`), RTL stylesheet (`frontend/style_rtl.css`),
  agent chat UI (`frontend/agent_chat.html`).

#### Infrastructure
- `docker/` + `kubernetes/` deployment manifests.
- `.github/` CI workflow scaffolding.
- `pyproject.toml` + linters / coverage / security tooling.
- `README.md` with architecture overview linking to closure report.

### Fixed
- `_AuditAction` variable shadowing in `bridge_api.py` that silenced enterprise audit trail.
- `main_report_sheet.py` KPI section now uses canonical `professional_template` profile key.

### Tests
- **482 tests, all green** at v1.0.0 tag, zero regression across the journey.

### Notes
- Frontend relies on a documented manual checklist (no automated tests yet).
- 24 additional subsystems preserved on `wip/r3-subsystems-checkpoint`, pending
  per-subsystem review (R3.1 security + R3.2 government/banking/funds already merged).
- `PHASE_4_README.md` cosmetic edit deferred for manual review.

### Documentation
- `docs/EXPERT_SMART_CLOSURE_REPORT.md` — full architecture reference and project closure.
- `docs/SECURITY_PLAN_REPORTS_API.md` — security design for report endpoints.

---

[Unreleased]: https://github.com/hishamappraiserman29-oss/expert-smart/compare/v1.1.2...HEAD
[1.1.2]: https://github.com/hishamappraiserman29-oss/expert-smart/compare/v1.1.1...v1.1.2
[1.1.0]: https://github.com/hishamappraiserman29-oss/expert-smart/releases/tag/v1.1.0
[1.0.0]: https://github.com/hishamappraiserman29-oss/expert-smart/releases/tag/v1.0.0
