# Changelog

All notable changes to EXPERT_SMART are documented here.

This project follows [Keep a Changelog](https://keepachangelog.com/) and [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

*(no unreleased changes)*

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

[Unreleased]: https://github.com/hishamappraiserman29-oss/expert-smart/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/hishamappraiserman29-oss/expert-smart/releases/tag/v1.1.0
[1.0.0]: https://github.com/hishamappraiserman29-oss/expert-smart/releases/tag/v1.0.0
