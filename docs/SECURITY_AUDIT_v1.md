# Security Audit v1 — EXPERT_SMART

**Date:** 2026-05-17
**Scope:** All code on `main` branch HEAD (commit `c6a1c40`)
**Auditor:** Claude CLI (automated read-only audit)
**Methodology:** 7-category static analysis + git history sweep

---

## Post-Audit Status (as of 2026-05-18)

| Finding | Severity | Status | Notes |
|---|---|---|---|
| SEC-001 Path traversal `/api/download` | Critical | ✅ Fixed | `@require_auth` + `basename` + containment check added |
| SEC-002 ~75 unauthenticated endpoints | High | 🔄 In Progress | `/api/valuation` + `/api/reports*` hardened; remaining endpoints tracked |
| SEC-003 Unauthenticated enterprise mgmt | High | ✅ Fixed | `@require_admin` applied to all `/api/enterprise/*` routes |
| SEC-004 `str(e)` exception disclosure | High | 🔄 Deferred | Tracked; not yet replaced |
| SEC-005 Unauthenticated report download | High | ✅ Fixed | `@require_auth` added |
| SEC-006 CORS wildcard | Medium | 🔄 Deferred | Tracked; not yet restricted |
| SEC-007 Unauthenticated market-feed write | Medium | 🔄 Deferred | Tracked |
| SEC-008 Audit coverage gap | Medium | 🔄 Deferred | Tracked |
| SEC-009 `.env.example` missing | Medium | ✅ Fixed | `.env.example` created with all required vars |
| SEC-010 Disconnected `security_layer.py` | Low | 🔄 Deferred | Tracked |
| SEC-011 Silent auth-import failure | Low | 🔄 Deferred | Tracked |
| SEC-012 Decorator order `@require_auth`/`@limiter` | Low | 🔄 Deferred | Tracked |
| SEC-013 TODO in production response | Informational | 🔄 Deferred | Tracked |
| SEC-014 `datetime.utcnow()` deprecated | Informational | 🔄 Deferred | Tracked |

### PH.3 — Google Credentials (Post-Audit Finding)

| Item | Status |
|---|---|
| `service_account.json` / `credentials.json` tracked in Git | ✅ Not tracked — `.gitignore` hardened |
| Private key content in any tracked file | ✅ Not present — CI secret guard active |
| Repo-side remediation | ✅ DONE |
| Manual key rotation on GCP | ⚠️ **WAIVED TEMPORARILY** — Waiver ID: `PH3-GCP-SA-KEY-ROTATION` |

**Waiver reason:** MFA / 2-Step Verification setup could not be completed; current account lacks
`iam.serviceAccounts.list` and `resourcemanager.projects.get` on project `gleaming-terra-487414-f4`.

**Gate impact (updated 2026-05-19):**
- Production dry-run: ⚠️ CONDITIONAL — allowed with project owner's explicit acknowledgement of waiver.
- `v1.1.0` release tag: ⚠️ CONDITIONAL — **allowed as conditional release**; waiver decision recorded 2026-05-19 by project owner (Hisham Elmahdy). See waiver document for recommended tag annotation.
- Full unconditional production release: ❌ PENDING — requires PH.3 waiver closure (key rotated/deleted/confirmed unused).

**Waiver document:** `docs/PH3_KEY_ROTATION_WAIVER.md` — contains closure conditions, compensating controls, and owner sign-off fields.

---

## Executive Summary

| Severity      | Count |
|---------------|-------|
| Critical      | 1     |
| High          | 4     |
| Medium        | 4     |
| Low           | 3     |
| Informational | 2     |
| **Total**     | **14**|

### Top Critical + High Issues

1. **[SEC-001]** Path traversal risk + unauthenticated access on `/api/download/<filename>`
2. **[SEC-002]** ~75 of ~80 endpoints have zero application-level authentication
3. **[SEC-003]** Unauthenticated enterprise tenant creation and user management
4. **[SEC-004]** `str(e)` in 97+ error responses — internal exception message disclosure
5. **[SEC-005]** Unauthenticated `/api/valuation/report/download/<filename>` exposes generated Excel reports

### Production Gate Assessment

- [x] JWT secret: properly requires `JWT_SECRET` env var — no default ✅
- [x] HMAC signing key: requires `GOVT_SIGNING_KEY` env var — no default ✅
- [x] Reports DB: `owner_user_id` enforced on all fetch/delete paths ✅
- [ ] Zero Critical findings: **FAIL** — SEC-001 open
- [ ] All High findings tracked with owner + deadline: **FAIL** — 4 open
- [ ] `.env.example` documents all required env vars: **FAIL** — file missing

**Verdict: NO-GO for public production launch**

Minimum gate-clearance conditions:
1. Fix SEC-001 (path traversal) — immediate
2. Confirm SEC-002 infrastructure-auth coverage or apply application-level auth — before launch
3. Fix SEC-003 (unauthenticated tenant management) — immediate
4. Fix SEC-004 (error disclosure) — before launch

---

## 1. Critical Findings (1)

### SEC-001 — Path Traversal + Unauthenticated Access on `/api/download/<filename>`

- **Severity:** Critical
- **Category:** Endpoint Surface / Static Pattern
- **Affected:** `core_engine/bridge_api.py:5591–5593`
- **Description:**
  The `/api/download/<filename>` endpoint calls `send_file(os.path.join(OUTPUTS, filename))` with no authentication decorator, no `os.path.basename()` normalization, and no path-containment check. On Windows (the current deployment platform), backslash (`\`) is a path separator but is NOT a URL `/`, so Flask's `<filename>` string converter passes it through. An attacker can request `..%5Cbridge_api.py` (URL-encoded `\`), which Python resolves as `OUTPUTS\..\bridge_api.py`, traversing one directory upward. Deeper traversal is possible with chained `%5C..%5C` segments. Additionally, Python's `os.path.join` discards all previous components when given an absolute path; if Waitress/WSGI normalises a path segment into an absolute string before handing it to Flask, the full file system is exposed.

  The newer download endpoint at line 8168 (`/api/valuation/report/download/<filename>`) demonstrates the correct pattern: `safe_name = os.path.basename(filename)` + `.xlsx` extension enforcement. The `/api/download/` endpoint has none of these guards.

- **Evidence:**
  ```python
  # bridge_api.py:5591–5593 — NO auth, NO basename, NO containment check
  @app.route("/api/download/<filename>")
  def download(filename):
      return send_file(os.path.join(OUTPUTS, filename), as_attachment=True)

  # OUTPUTS = core_engine/outputs/  (bridge_api.py:343)
  OUTPUTS = os.path.join(_BASE, "outputs")

  # Contrast: safe pattern used at line 8176–8179
  safe_name = os.path.basename(filename)
  if not safe_name.endswith(".xlsx") or safe_name != filename:
      return jsonify({"status": "error", "message": "Invalid filename"}), 400
  ```

- **Recommended Fix:**
  1. Apply `@require_auth` decorator.
  2. Sanitise filename: `safe = os.path.basename(filename)`.
  3. Verify the resolved path starts with `OUTPUTS`: `if not os.path.abspath(filepath).startswith(os.path.abspath(OUTPUTS) + os.sep): abort(400)`.
  4. Restrict to known extensions (`.docx`, `.pdf`, `.xlsx`).

- **Effort:** Small (< 30 min)
- **Related:** SEC-002 (no auth pattern), SEC-005 (similar unauth download endpoint)

---

## 2. High Findings (4)

### SEC-002 — ~75 of ~80 Endpoints Have Zero Application-Level Authentication

- **Severity:** High
- **Category:** Endpoint Surface / Auth Integration
- **Affected:** `core_engine/bridge_api.py` (all routes except `/api/reports*`, `/api/admin/audit`)
- **Description:**
  The application exposes approximately 80 HTTP routes. Only 3 carry `@require_auth` (the `/api/reports` family) and only 1 carries `@require_admin` (`/api/admin/audit`). All remaining ~75 endpoints — including financial valuation, fraud detection, geo-risk scoring, mass appraisal, enterprise management, market intelligence, batch processing, and REIT NAV calculation — have no authentication gate at the application layer.

  The comment at line 11656–11658 states *"No application-level auth gate — infrastructure auth is assumed"*. If that infrastructure auth (API gateway, mTLS, VPN) is absent or misconfigured, every financial calculation and all user data is publicly accessible. There is no auditable confirmation in the code that this assumption holds in deployment.

- **Evidence:**
  ```python
  # bridge_api.py:542 — audit only covers 2 prefixes
  _AUDITED_PREFIXES = ("/api/reports", "/api/admin")

  # Representative unauthenticated endpoints:
  @app.route("/api/valuation", methods=["POST","OPTIONS"])          # line 5319
  @app.route("/api/fraud/detect", methods=["POST", "OPTIONS"])      # line 6650
  @app.route("/api/geo/risk", methods=["POST", "OPTIONS"])          # line 6690
  @app.route("/api/mass-appraisal/run", methods=["POST", "OPTIONS"])# line 7258
  @app.route("/api/enterprise/tenant", methods=["POST"])            # line 8921
  @app.route("/api/reit/nav", methods=["POST", "OPTIONS"])          # line 7120
  # ... 70+ more
  ```

- **Recommended Fix:**
  Document the infrastructure auth layer and verify it is enforced before requests reach the Flask application in all deployment environments. Add a startup assertion or health-check that confirms the auth layer is active. For any endpoint that is not behind guaranteed infrastructure auth, apply `@require_auth`.

- **Effort:** Large (1+ day for full coverage); Medium for documentation + startup assertion
- **Related:** SEC-003, SEC-005, SEC-006, SEC-008

---

### SEC-003 — Unauthenticated Enterprise Tenant Creation and User Management

- **Severity:** High
- **Category:** Endpoint Surface / Cross-Cutting
- **Affected:** `core_engine/bridge_api.py:8921–9000+`
- **Description:**
  The enterprise management endpoints (`/api/enterprise/tenant` POST, `/api/enterprise/tenant/<id>` GET, `/api/enterprise/tenant/<id>/user` POST) have no authentication. Any anonymous caller on the network can create tenant organisations, enumerate existing tenants by ID, and add users with arbitrary roles. This is the highest-privilege data mutation in the system with no access control.

- **Evidence:**
  ```python
  # bridge_api.py:8921 — create tenant, no auth
  @app.route("/api/enterprise/tenant", methods=["POST"])
  def api_enterprise_create_tenant():
      data = request.get_json(force=True) or {}
      org_name = (data.get("organization_name") or "").strip()
      ...
      tenant = _tenant_manager.create_tenant(org_name, country, tier)

  # bridge_api.py:8965 — add user to tenant, no auth
  @app.route("/api/enterprise/tenant/<tenant_id>/user", methods=["POST"])
  def api_enterprise_add_user(tenant_id: str):
      ...
      role = (data.get("role") or "").strip()
  ```

- **Recommended Fix:**
  Apply `@require_admin` (or at minimum `@require_auth`) to all `/api/enterprise/*` routes. Tenant creation should require admin role.

- **Effort:** Small (< 30 min — adding decorators)
- **Related:** SEC-002

---

### SEC-004 — `str(e)` in 97+ Error Responses — Internal Exception Message Disclosure

- **Severity:** High
- **Category:** Cross-Cutting Threats
- **Affected:** `core_engine/bridge_api.py` (97 occurrences)
- **Description:**
  Across 97 `except` blocks in `bridge_api.py`, exception messages are returned verbatim to API callers via `jsonify({"status": "error", "message": str(e)})`. Exception messages from Python internals, SQLite, file system errors, and third-party libraries routinely include internal file paths, table names, column names, library versions, and configuration details. An attacker can trigger deliberate errors (malformed inputs, non-existent IDs, oversized payloads) to extract architectural information.

  Additionally, `traceback.format_exc()` is `print()`-ed to stdout at ~12 locations. In production this goes to server logs, which may be accessible if logging is misconfigured.

- **Evidence:**
  ```python
  # Typical pattern — bridge_api.py:5589
  except Exception as e:
      print(traceback.format_exc())             # full traceback to stdout
      return jsonify({"status":"error","message":str(e)}), 500

  # Examples of what str(e) can leak:
  # sqlite3.OperationalError: no such table: market_records
  # FileNotFoundError: [Errno 2] No such file or directory: '/app/outputs/...'
  # json.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
  # KeyError: 'property_type'  (reveals expected schema)
  ```

- **Recommended Fix:**
  Replace `str(e)` in all production error responses with a generic message. Log the full exception server-side (using `logger.exception()` rather than `print(traceback.format_exc())`). Return only `{"status": "error", "message": "Internal server error"}` to callers. Reserve detail messages for known, safe validation errors.

- **Effort:** Medium (1–3 hours — systematic replacement across bridge_api.py)
- **Related:** SEC-001 (path info leakage in download error), SEC-002

---

### SEC-005 — Unauthenticated `/api/valuation/report/download/<filename>`

- **Severity:** High
- **Category:** Endpoint Surface
- **Affected:** `core_engine/bridge_api.py:8168–8190`
- **Description:**
  The endpoint `/api/valuation/report/download/<filename>` correctly prevents path traversal (uses `os.path.basename()` + `.xlsx` extension check), but carries no `@require_auth` decorator. Valuation Excel reports contain property addresses, assessed values, income projections, and client/appraiser details — sensitive financial PII. Any anonymous caller who discovers or guesses a report UUID (or iterates filenames from the temp directory naming pattern) can download any report generated by any user.

  The report UUID is returned in the JSON response of `/api/valuation/report` (also unauthenticated per SEC-002), compounding the exposure.

- **Evidence:**
  ```python
  # bridge_api.py:8168 — NO @require_auth
  @app.route("/api/valuation/report/download/<filename>", methods=["GET"])
  def api_valuation_report_download(filename: str):
      safe_name = os.path.basename(filename)
      if not safe_name.endswith(".xlsx") or safe_name != filename:
          return jsonify({"status": "error", "message": "Invalid filename"}), 400
      filepath = os.path.join(_REPORT_DIR, safe_name)
      ...
      return send_file(filepath, ...)

  # _REPORT_DIR = tempfile.gettempdir() / "expert_smart_reports"
  # bridge_api.py:7951
  ```

- **Recommended Fix:**
  Add `@require_auth`. Store reports with `owner_user_id` as prefix/metadata and verify on download. Consider using signed short-lived download tokens instead of stable filenames.

- **Effort:** Small (< 30 min for auth gate; Medium for owner binding)
- **Related:** SEC-001, SEC-002

---

## 3. Medium Findings (4)

### SEC-006 — CORS Wildcard `Access-Control-Allow-Origin: *` on All `/api/*` Routes

- **Severity:** Medium
- **Category:** Configuration Hygiene / Cross-Cutting
- **Affected:** `core_engine/bridge_api.py:360` + `bridge_api.py:532–537`
- **Description:**
  CORS is configured in two places: `flask_cors.CORS(app, resources={r"/api/*": {"origins": "*"}})` at line 360, and a manual `Access-Control-Allow-Origin: *` header in the `@after_request` hook at line 534. Both set wildcard origin. Combined with the ~75 unauthenticated POST endpoints (SEC-002), any website can make cross-origin requests that read or write financial data, market feed records, and mass appraisal inputs. While browsers block credentialed requests to wildcard origins, all unauthenticated endpoints are reachable from any origin.

- **Evidence:**
  ```python
  # bridge_api.py:360
  CORS(app, resources={r"/api/*": {"origins": "*"}})

  # bridge_api.py:532–537
  @app.after_request
  def _cors(r):
      r.headers["Access-Control-Allow-Origin"]  = "*"
      r.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
      r.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
      return r
  ```

- **Recommended Fix:**
  Restrict CORS to known frontend origins (e.g., `ALLOWED_ORIGINS` env var). In the manual `_cors` hook, validate `request.origin` against a whitelist. Remove duplicate CORS configuration (keep only flask-cors or the manual hook, not both).

- **Effort:** Small (< 30 min)
- **Related:** SEC-002

---

### SEC-007 — Unauthenticated Market Feed Write Endpoint Allows Anonymous Data Injection

- **Severity:** Medium
- **Category:** Endpoint Surface / Cross-Cutting
- **Affected:** `core_engine/bridge_api.py:5598–5668`
- **Description:**
  `POST /api/market-feed` accepts market intelligence records from any anonymous caller. The endpoint writes to the `market_records` SQLite table used to power comparative analysis, heatmaps, and price intelligence. An attacker can systematically inject fabricated market data (false prices, false locations, false property types) to skew valuation outputs. There is no source authentication, no anomaly detection, and no rate limit on this endpoint.

- **Evidence:**
  ```python
  # bridge_api.py:5598 — no auth, no rate limit
  @app.route("/api/market-feed", methods=["POST", "OPTIONS"])
  def market_feed_post():
      """يُضيف سجل بيانات سوقية جديد من أي مصدر خارجي."""
      ...
      # Writes directly to market_records table via MarketRadar
  ```

- **Recommended Fix:**
  Require authentication for write operations (`@require_auth`). Add rate limiting (`@limiter.limit`). Consider requiring a data source token for external integrations.

- **Effort:** Small (< 30 min)
- **Related:** SEC-002

---

### SEC-008 — Audit Coverage Covers Only 2 of ~80 Endpoint Prefixes

- **Severity:** Medium
- **Category:** Auth Integration / Cross-Cutting
- **Affected:** `core_engine/bridge_api.py:542`
- **Description:**
  The `_AUDITED_PREFIXES` constant limits audit logging to `/api/reports` and `/api/admin`. All other endpoints — including `/api/valuation`, `/api/fraud/detect`, `/api/enterprise/*`, `/api/mass-appraisal/*`, `/api/market-feed` — generate no audit trail. In a regulated financial system (CBE, FRA, EGFSA), the absence of audit records for financial calculations and administrative mutations is a compliance gap and an incident-response blocker.

- **Evidence:**
  ```python
  # bridge_api.py:542
  _AUDITED_PREFIXES = ("/api/reports", "/api/admin")

  @app.after_request
  def _audit_protected_endpoints(response):
      """Log every access to /api/reports* endpoints."""
      path = request.path
      if not any(path.startswith(p) for p in _AUDITED_PREFIXES):
          return response   # ← all other endpoints exit silently
  ```

- **Recommended Fix:**
  Expand `_AUDITED_PREFIXES` to include at minimum: `/api/valuation`, `/api/enterprise`, `/api/mass-appraisal`, `/api/fraud`, `/api/market-feed`. Consider audit-logging all POST/PUT/DELETE requests by default and whitelisting read-only health endpoints for exclusion.

- **Effort:** Small (< 30 min to expand prefixes; Medium for full audit coverage with user attribution)
- **Related:** SEC-002, SEC-003

---

### SEC-009 — `.env.example` Missing — Required Production Env Vars Undocumented

- **Severity:** Medium
- **Category:** Configuration Hygiene
- **Affected:** Repository root (file does not exist)
- **Description:**
  There is no `.env.example` file. The application requires at least the following env vars for correct and secure operation, none of which are documented in a single reference location:

  | Variable | Purpose | Consequence if missing |
  |---|---|---|
  | `JWT_SECRET` | JWT signing key | All auth operations raise `AuthError` |
  | `JWT_TTL_SECONDS` | Token lifetime | Defaults silently to 3600 s |
  | `GOVT_SIGNING_KEY` | HMAC document signing | Raises `ValueError` on instantiation |
  | `ADMIN_USER_IDS` | Admin allowlist | Defaults to empty (no admins) |
  | `AUDIT_ENABLED` | Enable audit logging | Defaults to `"true"` |
  | `RATE_LIMIT_ENABLED` | Enable rate limiting | Defaults to `"true"` |
  | `REPORTS_DB_PATH` | SQLite DB path | Uses default relative path |

  A new deployment operator has no documented list of what to set. A mis-deployment may leave `JWT_SECRET` unset (all auth fails) or `ADMIN_USER_IDS` empty (no admin access).

- **Evidence:**
  ```bash
  # No .env.example in repo root
  # Variables scattered across:
  # core_engine/auth/tokens.py:25 — JWT_SECRET
  # core_engine/bridge_api.py:378  — RATE_LIMIT_ENABLED
  # core_engine/audit_log.py:23    — AUDIT_ENABLED
  # core_engine/admin.py:20        — ADMIN_USER_IDS
  # core_engine/government/digital_signature.py:56 — GOVT_SIGNING_KEY
  ```

- **Recommended Fix:**
  Create `.env.example` at repo root with all required variables, safe placeholder values, and brief inline comments. Add a startup check that logs warnings for any variable that has no default and is unset.

- **Effort:** Small (< 30 min)
- **Related:** SEC-001, SEC-002

---

## 4. Low Findings (3)

### SEC-010 — `api/security_layer.py` API Key Manager Is In-Memory Only and Not Wired to Auth

- **Severity:** Low
- **Category:** Module Review
- **Affected:** `core_engine/api/security_layer.py`
- **Description:**
  `security_layer.py` implements a full API key generation, rotation, and rate-limit-tier system (`APIKeyManager`, `RateLimitConfig`). All state is held in a dict in memory: keys are lost on every server restart, there is no persistence layer, and the manager is not imported or consulted anywhere in `bridge_api.py`. The Auth module (`auth/tokens.py`) independently handles JWT auth. Having a parallel, disconnected API key system creates confusion about the intended auth model and the in-memory store is not production-safe.

- **Evidence:**
  ```python
  # api/security_layer.py:29–31 — stored as Enum value strings (not credentials)
  class AuthenticationMethod(str, Enum):
      API_KEY = "api_key"          # String value, not a secret
      BEARER_TOKEN = "bearer_token"

  # bridge_api.py — no import of security_layer found
  ```

- **Recommended Fix:**
  Either integrate `security_layer.py` with bridge_api.py (adding persistence) or remove it to avoid confusion. Document the intended auth model clearly in one place.

- **Effort:** Medium (1–3 hours)

---

### SEC-011 — Auth Failure During Import Silently Disables All Auth

- **Severity:** Low
- **Category:** Auth Integration
- **Affected:** `core_engine/bridge_api.py:53–58`
- **Description:**
  The auth module is loaded inside a `try/except ImportError` block. If the import fails (missing package, broken module), `_AUTH_AVAILABLE` is set to `False` and all `require_auth` calls silently pass through (`g.user_id` remains `None` but `require_auth` checks `getattr(g, "user_id", None)` — which returns `None`, causing 401s). Technically auth enforcement is preserved for the 3 protected endpoints. However the silent failure mode provides no alert and no startup-time validation that auth is operational.

- **Evidence:**
  ```python
  # bridge_api.py:53–58
  try:
      from auth.tokens import AuthError as _AuthError, verify_token as _verify_token
      _AUTH_AVAILABLE = True
  except ImportError:
      _AUTH_AVAILABLE = False   # ← silent; no log, no startup assertion

  # bridge_api.py:579
  def _attach_user_from_token():
      g.user_id = None
      if not _AUTH_AVAILABLE:
          return              # ← auth silently skipped if module missing
  ```

- **Recommended Fix:**
  Replace the `try/except ImportError` with a mandatory import (fail fast at startup if auth module is missing). At minimum, add `logger.critical("Auth module unavailable — authentication disabled!")` in the except block.

- **Effort:** Small (< 30 min)

---

### SEC-012 — `@require_auth` Before `@limiter.limit` — Rate Limit Does Not Apply to Auth Failures

- **Severity:** Low
- **Category:** Auth Integration
- **Affected:** `core_engine/bridge_api.py:11662–11663`, `11705–11706`, `11736–11737`
- **Description:**
  In all three `@require_auth`-protected endpoints, the decorator order is `@require_auth` (outer) → `@limiter.limit` (inner). Flask evaluates outer decorators first, so auth runs before the rate limiter. Unauthenticated requests are rejected at the auth gate without consuming rate-limit quota. This means an attacker can send an unlimited stream of requests with invalid/missing tokens to the auth-protected endpoints without triggering rate limiting. In the current design this is lower risk (JWT validation is fast and tokens cannot be guessed), but for any future endpoints that check username/password or perform heavier auth work, the order should be reversed.

- **Evidence:**
  ```python
  # bridge_api.py:11661–11663
  @app.route("/api/reports", methods=["GET"])
  @require_auth         # outer — runs first; rejects before limiter
  @limiter.limit("30/minute", exempt_when=_rate_limit_disabled)
  def reports_list():
  ```

- **Recommended Fix:**
  Swap decorator order to `@limiter.limit` (outer) → `@require_auth` (inner) for all protected endpoints. This applies the rate limit to all requests, including unauthenticated ones, preventing enumeration and brute-force via this path.

- **Effort:** Small (< 30 min)
- **Related:** SEC-002

---

## 5. Informational (2)

### SEC-013 — Silent `TODO` Comment in Production API Response Payload

- **Severity:** Informational
- **Category:** Cross-Cutting
- **Affected:** `core_engine/bridge_api.py:11650`
- **Description:**
  A production JSON response includes the string `"Data is representative sample values. TODO: live market data collector."` in the `"note"` field. While not a security vulnerability, returning `TODO` notes in production responses reveals that a feature is incomplete and discloses the system's development roadmap to any caller.

- **Evidence:**
  ```python
  # bridge_api.py:11650
  "note": "Data is representative sample values. TODO: live market data collector."
  ```

- **Recommended Fix:**
  Remove the `TODO` from the API response. Use a generic note like `"Data is representative of current market samples."` Track the live data collector work in the project backlog.

- **Effort:** Small

---

### SEC-014 — `datetime.utcnow()` Deprecated in Government Module

- **Severity:** Informational
- **Category:** Module Review
- **Affected:** `core_engine/government/digital_signature.py:114`, `core_engine/government/government_portal.py:36,48`
- **Description:**
  Python 3.12+ marks `datetime.utcnow()` as deprecated. This produces `DeprecationWarning` in test output and will become a runtime error in a future Python version. Not a security issue today, but worth tracking alongside security-relevant module maintenance.

- **Evidence:**
  ```
  DeprecationWarning: datetime.datetime.utcnow() is deprecated ...
  Use timezone-aware objects: datetime.datetime.now(datetime.UTC)
  ```

- **Recommended Fix:**
  Replace all `datetime.utcnow()` with `datetime.now(timezone.utc)` and add `from datetime import timezone` where needed.

- **Effort:** Small

---

## 6. False Positives / Acceptable Risks

### FP-001 — `API_KEY = "api_key"` in `security_layer.py`

- **Why flagged:** Matches `API_KEY\s*=\s*"..."` pattern
- **Why safe:** This is a Python `Enum` value string (`AuthenticationMethod.API_KEY = "api_key"`), not a secret credential. It represents a method name label, not a key value.

### FP-002 — `BEARER_TOKEN = "bearer_token"` in `security_layer.py`

- **Why flagged:** Matches `TOKEN\s*=\s*"..."` pattern
- **Why safe:** Same as FP-001 — Enum label string.

### FP-003 — `market_radar.py:383` f-string in `execute()` call

- **Why flagged:** Matches `execute(f"""...{cond}...)` pattern — apparent SQL injection
- **Why safe:** The `cond` variable is built exclusively from static SQL fragments (`"confidence >= 0.3 AND ppm IS NOT NULL..."`) with `?` placeholders appended. All user-supplied values (`location`, `asset_type`) are added to the `params` list and passed as the second argument to `execute()`. The f-string embeds only the static `cond` string, not user data. This is a safe parameterized query construction pattern.
  ```python
  cond = "confidence >= 0.3 AND ppm IS NOT NULL AND ppm > 0"
  if location:
      cond += " AND location LIKE ?"; params.append(f"%{location}%")  # user input → params
  cur = self._conn().execute(f"SELECT ... WHERE {cond} ...", params)  # cond is static
  ```

### FP-004 — `subprocess.check_call(..., shell=True)` and `eval()`/`exec()` hits

- **Why flagged:** Matches `shell=True` and `eval(` patterns
- **Why safe:** All hits are in `pip/_internal/`, `distlib/`, `pkg_resources/`, and `pygments/` — third-party library internals shipped with the Python packaging toolchain, not `core_engine/` production code. No `shell=True` or `eval/exec` was found in any `core_engine/*.py` file.

### FP-005 — Test file secrets (`test-secret-for-unit-tests-only`, `csecret`, etc.)

- **Why flagged:** Match `SECRET|TOKEN|password` patterns with string values
- **Why safe:** All occurrences are in `core_engine/tests/` files. Values like `"test-secret-for-unit-tests-only"` and `"test-signing-key-for-unit-tests-only"` are intentional test fixtures, clearly named, and never used in production code paths. Git history confirms no production-like secrets (e.g., `sk_live_`, 40+ char random strings) appear in any file.

### FP-006 — Git History — No Production Secrets Found

- **Why flagged:** Scanned last 50 commits for `API_KEY=`, `SECRET=`, `TOKEN=`, `sk_live_`, `pk_live_`, `password=`
- **Why safe:** All matches in git history are additions to test files (`test_marketplace.py`, `test_phase40_integrations.py`, `test_ph3_security.py`). No `.env` files or PEM/key files were ever committed. No production-like secrets appear.

---

## 7. Recommended Fix Order

### Immediate (before any network exposure)
1. **SEC-001** — Add `os.path.basename()` + path containment + `@require_auth` to `/api/download/<filename>`
2. **SEC-003** — Add `@require_admin` to all `/api/enterprise/*` routes
3. **SEC-005** — Add `@require_auth` to `/api/valuation/report/download/<filename>`

### Before Production Launch
4. **SEC-002** — Confirm infrastructure auth coverage in all deployment environments; add startup assertion
5. **SEC-004** — Replace `str(e)` with generic messages in all 97+ error responses
6. **SEC-009** — Create `.env.example` documenting all required env vars

### Next Sprint
7. **SEC-006** — Restrict CORS origins to known frontend domain(s)
8. **SEC-007** — Add `@require_auth` + `@limiter.limit` to `/api/market-feed` POST
9. **SEC-008** — Expand `_AUDITED_PREFIXES` to cover valuation + enterprise + mass-appraisal

### When Convenient
10. **SEC-010** — Integrate or remove disconnected `api/security_layer.py`
11. **SEC-011** — Replace silent auth-import failure with fail-fast or explicit warning
12. **SEC-012** — Swap `@require_auth` / `@limiter.limit` order (limiter outer)
13. **SEC-013** — Remove TODO from production API response
14. **SEC-014** — Replace `datetime.utcnow()` with timezone-aware alternative

---

## 8. Methodology + Tools

### Categories Audited
1. **Endpoint Surface** — all `@app.route` declarations, decorator coverage, `_AUDITED_PREFIXES`
2. **Cross-Cutting Threats** — IDOR patterns, owner-filter enforcement, error message disclosure
3. **Static Pattern Scan** — secrets, SQL injection, unsafe deserialization, code execution, command injection, path traversal
4. **Git History Sweep** — last 50 commits scanned for accidental secrets, `.env` commits, key files
5. **High-Risk Modules Deep Review** — `auth/`, `government/`, `funds/`, `banking/`, `agents/`, `reports/db/`, `api/security_layer.py`
6. **Auth Integration Health** — decorator order, `_AUDITED_PREFIXES`, rate-limit coverage, `_AUTH_AVAILABLE` failure mode
7. **Configuration Hygiene** — `.env.example` existence, `.gitignore` coverage, env var defaults

### Patterns Searched

| Pattern | Total Hits | Actual Issues |
|---|---|---|
| `@app.route(...)` (all routes) | ~80 | SEC-001, SEC-002, SEC-003, SEC-005, SEC-007 |
| `@require_auth` / `@require_admin` | 4 | SEC-002 (coverage gap) |
| `@limiter.limit` | 4 | SEC-012 (decorator order) |
| `_AUDITED_PREFIXES` | 1 | SEC-008 |
| `str(e)` in error responses | 97 | SEC-004 |
| `traceback.format_exc()` | ~12 | SEC-004 |
| `send_file` + `os.path.join` | 2 | SEC-001, SEC-005 |
| `CORS.*origins.*\*` | 2 | SEC-006 |
| `API_KEY\|SECRET\|TOKEN.*=.*"..."` | 13 | FP-001, FP-002, FP-005 (all FP) |
| `execute(f"` or `.format().*execute` | 1 | FP-003 (safe) |
| `pickle.loads\|yaml.load[^_]` | 0 | None |
| `\beval\(\|\bexec\(` (core_engine only) | 0 | None |
| `shell=True` (core_engine only) | 0 | None |
| `os.environ.get(..., "non-empty-default")` | 4 | SEC-009 (defaults OK; .env.example missing) |
| Git history secret patterns | 11 | FP-006 (all test values) |
| `.env` committed | 0 | None |
| `JWT_SECRET` + default | 0 | None (correctly raises) |
| `GOVT_SIGNING_KEY` + default | 0 | None (fixed in R3.9) |
| `RISK_FREE_RATE = 0.08` | 0 | None (fixed in R3.9) |
| `TODO\|FIXME\|HACK` (core_engine production) | 2 | SEC-013 (informational) |

### Files Reviewed

- `core_engine/bridge_api.py` (~11,800 lines)
- `core_engine/auth/tokens.py`
- `core_engine/admin.py`
- `core_engine/audit_log.py`
- `core_engine/market_radar.py`
- `core_engine/reports/db/db_engine.py`
- `core_engine/government/digital_signature.py`
- `core_engine/government/tax_calculator.py`
- `core_engine/funds/fund_engine.py`
- `core_engine/banking/ltv_calculator.py`, `collateral_engine.py`, `risk_assessment.py`
- `core_engine/agents/` (8 files — no LLM key hardcoding found)
- `core_engine/api/security_layer.py`
- `.gitignore` (root)
- Git log last 50 commits

### Out of Scope

- **Frontend** (`frontend/index.html`) — no JS/DOM security analysis; XSS, CSP, SRI out of scope for this audit
- **Mobile** (`mobile/`) — on WIP branch, not on `main`
- **WIP branch** (`wip/r3-subsystems-checkpoint`) — deferred subsystems not yet merged
- **Dependency CVE scan** — requires `pip-audit` or `safety`; separate task
- **Live penetration testing** — static analysis only; runtime race conditions and session fixation not fully observable statically
- **Infrastructure layer** — load balancer, API gateway, TLS termination — not in repository

### Limitations

- Static analysis cannot catch runtime-only issues (race conditions, session state, timing attacks)
- Path traversal risk on Windows (SEC-001) is assessed from code review; actual exploitability depends on WSGI server URL decoding behaviour — verify manually
- "Infrastructure auth" assumption (SEC-002) could not be verified from code alone; deployment documentation should be consulted
- Some findings assume public network exposure; if the application is deployed on a private internal network with no public ingress, several High findings reduce to Medium
