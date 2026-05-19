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

**SEC-002 complete** (SEC-002a through SEC-002e, all test-aligned). No further SEC-002 rollout is pending.

**Post-#7b frontend/auth follow-ups (deferred — not a blocker for v1.1.0):**
- ~~Frontend auth integration (Followup #7b)~~ — **IMPLEMENTED** (commits `d8c9d5d`, `0db6f4b`): JWT login modal + esFetch wrapper; protected calls now send `Authorization: Bearer <token>`. See `docs/AUTH_FLOW.md`.
- Background calls (`/api/radar/start`, `/api/price-index`) are currently unauthenticated; should later be gated behind token/admin state.
- Optional migration from token-paste `localStorage` flow to a real login provider or `HttpOnly` cookie session.

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

> **Note (2026-05-20):** `database/` and `saas/` have since been merged in v1.1.2.
> See `docs/FINAL_RELEASE_HANDOFF_v1.1.2.md` for the updated status.

### `database/` subsystem
- **Status at v1.1.0:** DEFERRED *(merged in v1.1.2 — commit `d94a847`)*
- ~~Contains a naming collision: `AuditLog` in both `database/models.py` and `database/audit_log.py`~~
- **Resolution:** `database/models.py` class renamed `ActivityLog`; collision eliminated (R3.10)

### `saas/` subsystem
- **Status at v1.1.0:** DEFERRED *(merged in v1.1.2 — commit `b99187c`)*
- **Resolution:** B1 (scripts/) and B2 (database.audit_log) blockers resolved; merged R3.11

### `mobile/`
- **Status:** On WIP branch (`wip/r3-subsystems-checkpoint`), not merged to `main`
- Not part of v1.1.0 or v1.1.2 scope
- **Next step:** Review and merge when mobile sprint is complete

### Frontend Auth — Followup #7b
- **Status:** IMPLEMENTED (commits `d8c9d5d` backend · `0db6f4b` frontend)
- JWT login modal added to `frontend/index.html`. User pastes a pre-existing JWT (no username/password, no user store). Modal calls `GET /api/auth/verify` to validate, then stores `{token, user_id, is_admin}` in `localStorage` under key `es_auth`.
- `esFetch` wrapper attaches `Authorization: Bearer <token>` on 4 protected calls: valuation form, `esReportsLoad`, `esReportsViewDetail`, `esReportsDownloadPdf`.
- 401 → session cleared + login modal re-prompt. 403 → inline admin-required message.
- Logged-in bar (top-right) shows `user_id [مسؤول]` badge when authenticated.
- E2E coverage added: 7 `TestAuthUI` tests in `test_frontend_smoke.py`.
- 401 filter in E2E narrowed to only `/api/radar/start` and `/api/price-index` (surgical, with URL-absent fallback).
- **Remaining follow-ups (deferred to next sprint):**
  - Replace token-paste flow with a real login provider / user store when needed
  - Migrate from `localStorage` to `HttpOnly` cookie session (eliminates XSS exposure)
  - Gate `/api/radar/start` and `/api/price-index` behind auth/admin state in a future wave
  - See `docs/AUTH_FLOW.md §8` for full hardening path

### E2E bundle
- **Status:** RESOLVED — green as of commit `234dc6a`
- The blocked state was caused by an expected 401 from `POST /api/radar/start` being captured as a console error. Fixed by filtering known-expected auth 401s in `test_frontend_smoke.py`.

---

## 11. Recommended Next Work

| Priority | Item | Rationale |
|---|---|---|
| P0 | **PH.3 closure** — complete GCP key rotation or confirm key deleted/unused | Main blocker for Full Production GO; waiver expires 2026-06-19 |
| P1 | **Frontend/auth follow-ups after SEC-002** — gate background calls (`/api/radar/start`, `/api/price-index`) behind token/admin state; optionally migrate from token-paste `localStorage` to real login provider or `HttpOnly` cookie | SEC-002 itself is complete; these are post-#7b hardening steps |
| ~~P2~~ | ~~**`database/` resolution**~~ | ✅ DONE in v1.1.2 (R3.10 + R3.11) |
| P3 | **Full Production GO review** — re-run gate after P0 is closed | Produces unconditional production release |
| P4 | **Performance baseline** (Followup #12) | Required for regression alerts; currently deferred |

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
| Frontend auth (#7b) — MVP login modal + esFetch | ✅ IMPLEMENTED (post-tag) |
| `database/` / `saas/` subsystems | ✅ MERGED in v1.1.2 |
| `mobile/` | ⚠️ WIP BRANCH |
| **v1.1.0 CONDITIONAL release** | ✅ **ALLOWED** |
| **Full unconditional production GO** | ❌ **PENDING** — PH.3 closure (main blocker) |

---

**EXPERT_SMART | v1.1.0 Conditional Release Handoff | 2026-05-19**
