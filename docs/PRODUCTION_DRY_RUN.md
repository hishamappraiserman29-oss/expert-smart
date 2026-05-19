# Production Dry-Run Report — EXPERT_SMART

**Date:** 2026-05-19  
**Conducted by:** Hisham Elmahdy + Claude CLI  
**Dry-run rules:** zero code changes · temp secrets/DB/outputs · mandatory server cleanup · findings = recommendations only  
**Waiver on file:** `PH3-GCP-SA-KEY-ROTATION` (see `docs/PH3_KEY_ROTATION_WAIVER.md`)

---

## Verdict

> **NO-GO**
>
> SEC-011 (auth module import failure) is a **critical production blocker**.  
> All protected endpoints return 401 to all users regardless of token validity.  
> The application is non-functional for authenticated users in the current state.  
> Fix SEC-011 and re-run dry-run before any production or staging deployment.

---

## Phase Results Summary

| Phase | Description | Result | Score |
|---|---|---|---|
| 2 | Environment setup | PASS | 6/6 |
| 3 | Server boot | PASS | boot in 3.0 s |
| 4 | HTTP probes | FAIL | 3/10 |
| 5 | Operational tooling | PASS | 3/3 |
| 6 | Docker build validation | SKIP | daemon offline |
| 7 | Cleanup | PASS | process + files |
| **Overall** | | **FAIL** | **13/20** |

---

## Phase 2 — Environment

All six environment checks passed. Dry-run secrets are session-only constants (not from `.env`).

| Check | Result |
|---|---|
| JWT_SECRET set (>= 32 chars) — 48 chars | OK |
| GOVT_SIGNING_KEY set (>= 32 chars) — 46 chars | OK |
| AUDIT_ENABLED = true | OK |
| RATE_LIMIT_ENABLED = true | OK |
| ADMIN_USER_IDS set | OK |
| REPORTS_DB_PATH in temp dir | OK |

**Note:** `core_engine/.env` was NOT read. `valuation_logic.py` loads it with `override=False`, so injected dry-run secrets are unaffected. Confirmed safe.

---

## Phase 3 — Boot

| Metric | Value | Threshold | Result |
|---|---|---|---|
| Port 5000 open | Yes | within 25 s | PASS |
| Boot time | 3.0 s | — | PASS |
| Server exit code (post-cleanup) | 1 | — | Expected (SIGTERM) |

Server started successfully as subprocess from `core_engine/` with dry-run env vars injected via `subprocess.Popen(env=...)`.

---

## Phase 4 — HTTP Probes

**3 of 10 probes passed.**  
Root cause for all failures: **SEC-011** — auth module import fails at startup; `_AUTH_AVAILABLE = False`; middleware silently returns without setting `g.user_id`; `require_auth` returns 401 for every request including valid-token requests.

| # | Probe | Expected | Got | Result |
|---|---|---|---|---|
| 1 | GET / (index) | 200 | 200 | **PASS** |
| 2 | GET /api/reports (no token) | 401 | 401 | **PASS** |
| 3 | GET /api/reports (valid token) | 200 | 401 | **FAIL** — SEC-011 |
| 4 | GET /api/reports (bad token) | 401 | 401 | **PASS** |
| 5 | GET /api/reports/<bad-id> + token | 404 | 401 | **FAIL** — SEC-011 |
| 6 | GET /api/admin/audit (non-admin token) | 403 | 401 | **FAIL** — SEC-011 |
| 7 | GET /api/admin/audit (admin token) | 200 | 401 | **FAIL** — SEC-011 |
| 8 | Rate limit: 31× /api/reports | 429 (last) | 401 | **FAIL** — SEC-011 |
| 9 | Audit rows in DB (> 0) | > 0 | 0 | **FAIL** — no successful requests |
| 10 | POST /api/valuation (auth token) | 200/422/400 | 401 | **FAIL** — SEC-011 |

**Probes 2 and 4** pass for the right observable reason (401) but for the wrong internal reason: with `_AUTH_AVAILABLE = False`, the middleware never inspects the token at all — it silently bypasses and leaves `g.user_id = None`. The 401 is correct output but represents a broken code path.

---

## Phase 5 — Operational Tooling

All three operational tools passed against a temp SQLite database.

| Tool | Command | Result |
|---|---|---|
| `backup_reports.py` | `--source <db> --dest-dir <tmp> --retention-days 30` | PASS |
| `export_reports_json.py` | `--db <db> --out <tmp>/export.json --pretty` | PASS |
| `apply_retention.py` | `--db <db>` | PASS |

---

## Phase 6 — Docker Build Validation

**SKIP — Docker Desktop daemon was not running during dry-run.**

Docker 28.4.0 is installed. Static Dockerfile analysis performed:

| Check | Finding |
|---|---|
| Multi-stage build (builder + production) | Present — reduces image size |
| Non-root user (`appuser:appgroup`) | Present — good practice |
| HEALTHCHECK URL (`/api/health`) | Valid — endpoint exists at `bridge_api.py:9287` |
| CMD invocation | `python -m waitress ... bridge_api:app` from `/app` (= `core_engine/`) |
| SEC-011 impact on container | Same failure: container runs from `/app`; `core_engine` not on path; `_AUTH_AVAILABLE = False` |

**Action required:** Fix SEC-011 before Docker build is validated. Even if the image builds, the running container will have broken auth.

---

## Phase 7 — Cleanup

| Item | Result |
|---|---|
| Server process terminated (SIGTERM) | PASS |
| Temp database removed | PASS |
| Temp export file removed | PASS |
| Temp backup directory removed | PASS |

Zero persistent side effects from the dry-run.

---

## Findings

### FINDING-01 — CRITICAL (Production Blocker)

**ID:** SEC-011 (confirmed + extended)  
**Title:** Auth module import failure — `_AUTH_AVAILABLE = False` in all deployment modes

**Root cause:**

`core_engine/auth/__init__.py:12` contains:
```python
from core_engine.auth.tokens import AuthError, generate_token, verify_token
```
This is an absolute import that requires `core_engine`'s *parent directory* on `sys.path`.

When `bridge_api.py` runs (whether via `python bridge_api.py` from `core_engine/`, via waitress, or inside the Docker container at `/app`), the working directory IS `core_engine/` — so `sys.path[0]` is `core_engine/`. The module `core_engine` is not findable from inside itself.

**Failure chain:**
```
bridge_api.py:53  try:
bridge_api.py:54      from auth.tokens import AuthError, verify_token
                      └── Python imports auth package
                          └── auth/__init__.py:12  from core_engine.auth.tokens import ...
                              └── ModuleNotFoundError: No module named 'core_engine'
bridge_api.py:56  except ImportError:
bridge_api.py:57      _AUTH_AVAILABLE = False        ← silently set
```

**Effect:**
- Middleware `_attach_user_from_token` returns immediately, never reads `Authorization` header
- `g.user_id` is always `None`
- `require_auth` always returns 401 HTTP response
- ALL protected endpoints unreachable by all users

**Confirmed:** Import fails when tested directly from `core_engine/` directory — `ModuleNotFoundError: No module named 'core_engine'`.

**Fix (1-line change — do NOT apply during dry-run):**

In `core_engine/auth/__init__.py` line 12, change absolute import to relative:
```python
# Before (broken):
from core_engine.auth.tokens import AuthError, generate_token, verify_token

# After (fix):
from .tokens import AuthError, generate_token, verify_token
```

`auth/tokens.py` itself is correct — it only imports stdlib and `jwt` (PyJWT). The bug is exclusively in `__init__.py`.

---

### FINDING-02 — WARNING

**Title:** Silent auth failure — no operational warning on startup

When `_AUTH_AVAILABLE = False`, the application starts normally, logs nothing, and returns 401 silently. Operators have no indication that auth is disabled short of inspecting every API response. This makes production diagnosis extremely difficult.

**Recommendation:** In `bridge_api.py:56-57`, add a critical log:
```python
except ImportError:
    _AUTH_AVAILABLE = False
    import logging as _logging
    _logging.critical(
        "AUTH DISABLED: failed to import auth.tokens — "
        "all protected endpoints will return 401. Check sys.path."
    )
```

---

### FINDING-03 — INFO

**Title:** Docker build validation inconclusive — daemon offline

Docker Desktop was not running during the dry-run. The Dockerfile is structurally sound, but SEC-011 applies equally to the container runtime (container runs from `/app` = `core_engine/`). Docker build validation should be repeated after SEC-011 is fixed.

---

### FINDING-04 — INFO

**Title:** Probes 2 and 4 pass for wrong internal reason

GET /api/reports with no token or bad token correctly returns 401 — but because `_AUTH_AVAILABLE = False` causes the middleware to skip all token processing, not because the tokens were validated and rejected. After SEC-011 is fixed, these probes must be re-run to confirm that bad/absent tokens are properly rejected by the token-validation path.

---

## Remediation Plan

| Priority | Finding | Action | Owner |
|---|---|---|---|
| P0 — fix before any deploy | FINDING-01 | Change `auth/__init__.py:12` to relative import `from .tokens import ...` | Engineering |
| P1 — fix in same PR | FINDING-02 | Add `logging.critical(...)` in auth import except block | Engineering |
| P2 — validate after fix | FINDING-03 | Re-run Docker build with daemon running after SEC-011 fixed | Engineering |
| P3 — re-run dry-run | All | Run full dry-run again; expect 10/10 probes to pass | Engineering |

---

## Gate Impact

| Gate | Status | Condition |
|---|---|---|
| Repo credential hygiene | GO | No credentials tracked; CI guard active |
| CI pipeline (1851 tests) | GO | All green |
| Operational tooling (backup/export/retention) | GO | 3/3 PASS |
| Server boot | GO | 3.0 s |
| Authentication + authorization | **BLOCKED** | SEC-011 — all auth endpoints 401 |
| Rate limiting | **BLOCKED** | Unreachable until auth fixed |
| Audit logging | **BLOCKED** | Zero entries (no successful auth requests) |
| Docker build | PENDING | Daemon offline; blocked by SEC-011 anyway |
| **Production dry-run overall** | **NO-GO** | SEC-011 is a hard blocker |
| `v1.1.0` release tag | CONDITIONAL-HOLD | Previously CONDITIONAL; now requires SEC-011 fix before re-assessment |
| Full unconditional production release | BLOCKED | PH.3 waiver + SEC-011 both unresolved |

---

## Recommended Next Steps

1. **Fix SEC-011 now** — change `auth/__init__.py:12` to `from .tokens import ...`
2. Add startup warning log (FINDING-02) in the same commit
3. Run `python -c "from auth.tokens import AuthError, verify_token; print('OK')"` from `core_engine/` to confirm fix
4. Re-run dry-run orchestrator — expect 10/10 probes to pass
5. Re-run Docker build with Docker Desktop running
6. After clean dry-run: re-assess `v1.1.0` conditional release gate

---

**EXPERT_SMART | Production Dry-Run | 2026-05-19**
