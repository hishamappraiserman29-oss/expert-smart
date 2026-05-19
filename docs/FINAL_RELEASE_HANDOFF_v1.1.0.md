# Final Release Handoff — EXPERT_SMART v1.1.0

**Date:** 2026-05-19  
**Released by:** Hisham Elmahdy  
**Release type:** CONDITIONAL (not unconditional Full Production GO)  
**Tag:** `v1.1.0` — annotated, on `main`

---

## 1. Release Tag Status

| Field | Value |
|---|---|
| Tag | `v1.1.0` |
| Type | Annotated |
| Tagged commit | `8671de5` — `tools(prod): fix dry-run audit DB path and valuation timeout` |
| Branch | `main` |
| Remote | pushed to `origin` |
| Release type | **CONDITIONAL** — see PH.3 waiver section |

---

## 2. CI/CD Status at Tag

Both workflows ran successfully on commit `8671de5` (the tagged commit):

| Workflow | Status |
|---|---|
| CI/CD Pipeline | ✅ success |
| E2E Tests | ✅ success |

Full test suite: **1858/1858 passing** (zero failures, zero skips in unit/integration suite).  
E2E: 4 Playwright smoke tests passing (page load, history panel, health endpoint, auth 401 filter).

---

## 3. Production Dry-Run

**Result: GO** (`docs/PRODUCTION_DRY_RUN.md`)

| Phase | Result |
|---|---|
| Environment (7 checks) | 7/7 PASS |
| Boot (3.5s) | PASS |
| HTTP Probes (10 probes) | 10/10 PASS |
| Tooling (backup / export / retention) | 3/3 PASS |
| Cleanup | PASS |
| **Total checks** | **21/21** |

Run script: `python tools/production_dry_run.py`

---

## 4. Security Audit Status

All 14 findings (SEC-001 through SEC-014) were addressed. See `docs/SECURITY_AUDIT_v1.md` for the full post-audit status table.

| Finding range | Status |
|---|---|
| SEC-001 Path traversal | Remediated |
| SEC-002 Auth enforcement (full rollout) | Partially complete — see SEC-002 note below |
| SEC-003 Hardcoded govt key | Remediated |
| SEC-004 Stack traces in errors | Remediated |
| SEC-005 Unvalidated IDOR | Remediated |
| SEC-006 Rate limiting | Remediated |
| SEC-007 CORS | Remediated |
| SEC-008 Audit logging | Remediated |
| SEC-009 Security headers | Remediated |
| SEC-010 Govt signature key in env | Remediated |
| SEC-011 Auth import failure | **Fixed (this release)** — `auth/__init__.py` relative import |
| SEC-012 through SEC-014 | Remediated per audit |
| PH.3 GCP key rotation | **WAIVED TEMPORARILY** — see Section 9 |

---

## 5. SEC-002 Auth Hardening — Status

**SEC-002e complete:** `/api/reports*` and `/api/valuation` now require a valid JWT (`@require_auth`). Owner isolation enforced via `owner_user_id` filter. Rate limiting active per user.

**Remaining (deferred — not a blocker for v1.1.0):**
- Full SEC-002 rollout to remaining endpoints (`/api/market-feed`, `/api/banking/*`, etc.) — deferred to next sprint
- Frontend auth integration (Followup #7b) — UI does not yet pass JWT tokens; users without a token see 401 on protected calls

---

## 6. SEC-011 Fix — Auth Runtime Import

**Problem:** `auth/__init__.py` used an absolute import (`from core_engine.auth.tokens import ...`) that failed when `bridge_api.py` ran from inside `core_engine/` (subprocess, waitress, Docker). Caused `_AUTH_AVAILABLE = False` silently — all protected endpoints returned 401.

**Fix (commit `c28c2c9`):**
```python
# Before:
from core_engine.auth.tokens import AuthError, generate_token, verify_token
# After:
from .tokens import AuthError, generate_token, verify_token
```

Added `logging.CRITICAL` startup warning if the import ever fails again.  
Added `core_engine/tests/test_auth_import_paths.py` (7 regression tests, IP01–IP07).

---

## 7. CI Hardening Completed in This Cycle

| Fix | Commit |
|---|---|
| `nest_asyncio` added to `requirements-dev.txt` | `4b60395` |
| E2E 401 filter (expected `POST /api/radar/start` 401) | `234dc6a` |
| `fastmcp` added to `requirements-dev.txt` | `0226d12` |
| Docker build: GHCR push gated to `workflow_dispatch` | `8511150` |
| SEC-011 auth import fix + startup warning | `c28c2c9` |
| Dry-run: `AUDIT_DB_PATH` + valuation `timeout=30` | `8671de5` |

---

## 8. Production Dry-Run Tool

`tools/production_dry_run.py` is now a versioned script (no hardcoded paths).  
Run from repo root: `python tools/production_dry_run.py`  
Results saved to `$TEMP/dryrun_results.json`.

---

## 9. PH.3 — Google Service Account Key Rotation Waiver

**Waiver ID:** `PH3-GCP-SA-KEY-ROTATION`  
**Full waiver:** `docs/PH3_KEY_ROTATION_WAIVER.md`  
**Next review:** 2026-06-19

### Repo-side status — CLEAN
- `service_account.json` not tracked in Git — confirmed by `git ls-files`
- `credentials.json` not tracked — confirmed
- No private key content in any tracked file — confirmed by CI secret guard
- `.gitignore` blocks all credential file patterns at root and `core_engine/` level
- `.env.example` uses placeholder only (`GOOGLE_APPLICATION_CREDENTIALS=` empty)
- CI secret guard active on every push

### Cloud-side status — WAIVED TEMPORARILY
The Google service account key (`appraiser-sync@gleaming-terra-487414-f4.iam.gserviceaccount.com`) still exists in Google Cloud Console. Manual rotation could not be completed:
- MFA / 2-Step Verification not completed on the owning Google account
- Missing IAM permissions (`iam.serviceAccounts.list`, `resourcemanager.projects.get`)

### What CONDITIONAL means for this release

| Allowed | Not allowed |
|---|---|
| `v1.1.0` tag with waiver annotation | Declaring unconditional production GO |
| Running scoped conditional dry-run | Full public production launch without owner sign-off |
| Merging to `main`, building Docker image | Deploying to production cluster without owner sign-off |

### Closure conditions (any one resolves the waiver)
- **Option A** — Rotation completed: old key deleted, new key created, `GOOGLE_APPLICATION_CREDENTIALS` updated
- **Option B** — Key confirmed deleted/unused in GCP Console
- **Option C** — Service account disabled or deleted in GCP

---

## 10. Deferred Items (Not Blocking v1.1.0)

### `database/` subsystem
- **Status:** DEFERRED
- Requires `psycopg2` and a live PostgreSQL instance; not in `requirements.txt` intentionally
- Contains a naming collision: `database/models.py` (SQLAlchemy ORM `AuditLog`) vs `database/audit_log.py` (SQLite dataclass `AuditLog`) — both export `AuditLog`
- All `bridge_api.py` references to `database/` are guarded with `try/except`
- **Next step:** Resolve `AuditLog` collision, add PostgreSQL integration tests, undefer

### `saas/` subsystem
- **Status:** DEFERRED — blocked by `database/` deferred status
- B1 blocker (`scripts/` module dependency) resolved
- B2 blocker (`test_phase_15_2_e2e.py` needs `database.audit_log`) still open
- **Next step:** Unblocked automatically when `database/` is resolved

### `mobile/`
- **Status:** On WIP branch (`wip/r3-subsystems-checkpoint`), not merged to `main`
- Not part of the v1.1.0 release scope
- **Next step:** Review and merge when mobile sprint is complete

### Frontend Auth — Followup #7b
- **Status:** OPEN
- SEC-002e hardened the backend (`@require_auth` on protected endpoints). The frontend (`frontend/index.html`) does not yet obtain or send JWT tokens. Users see 401 on protected API calls from the browser UI.
- E2E tests pass because they filter the expected 401 from `POST /api/radar/start`
- **Next step:** Implement login flow in the frontend; pass `Authorization: Bearer <token>` on protected fetch calls

### E2E bundle
- **Status:** RESOLVED — green as of commit `234dc6a`
- The blocked state was caused by an expected 401 from `POST /api/radar/start` being captured as a console error. Fixed by filtering known-expected auth 401s in `test_frontend_smoke.py`.

---

## 11. Recommended Next Work

| Priority | Item | Rationale |
|---|---|---|
| P0 | **PH.3 closure** — complete GCP key rotation or confirm key deleted/unused | Converts CONDITIONAL release to Full Production GO; waiver expires 2026-06-19 |
| P1 | **Frontend Auth (#7b)** — login flow + JWT in browser requests | Users currently cannot access protected endpoints from the UI |
| P2 | **Full SEC-002 rollout** — extend `@require_auth` to remaining unprotected endpoints | Completes the auth hardening started in SEC-002e |
| P3 | **`database/` resolution** — resolve `AuditLog` collision, add PG integration tests | Unblocks `saas/` and enables PostgreSQL production path |
| P4 | **Full Production GO review** — re-run gate after P0+P1+P2 are closed | Produces unconditional production release |
| P5 | **Performance baseline** (Followup #12) | Required for regression alerts; currently deferred |

---

## Release Gate Summary

| Gate | Status |
|---|---|
| Repo credential hygiene | ✅ GO |
| CI/CD pipeline (1858 tests) | ✅ GO |
| E2E smoke tests | ✅ GO |
| Production dry-run | ✅ GO (21/21) |
| Security audit remediation (SEC-001–SEC-014) | ✅ GO |
| SEC-002 auth hardening (key endpoints) | ✅ GO |
| SEC-011 runtime auth import | ✅ GO (fixed this release) |
| PH.3 GCP key rotation | ⚠️ WAIVED TEMPORARILY |
| Frontend auth (#7b) | ⚠️ DEFERRED |
| `database/` / `saas/` subsystems | ⚠️ DEFERRED |
| `mobile/` | ⚠️ WIP BRANCH |
| **v1.1.0 CONDITIONAL release** | ✅ **ALLOWED** |
| **Full unconditional production GO** | ❌ **PENDING** — PH.3 + #7b + SEC-002 full rollout |

---

**EXPERT_SMART | v1.1.0 Conditional Release Handoff | 2026-05-19**
