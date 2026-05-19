# Frontend Auth Flow — EXPERT SMART (Auth Wave #7b)

**Date:** 2026-05-19  
**Commits:** `d8c9d5d` (backend) · `0db6f4b` (frontend)  
**Status:** MVP — admin-only, pre-existing JWT, `localStorage`

---

## 1. Overview

EXPERT SMART uses **JWT Bearer tokens** for all protected API calls. The frontend
does **not** implement username/password authentication. Tokens are generated
out-of-band by an administrator using `generate_token()` or the CLI, then pasted
into the login modal by the user.

```
Admin CLI                    Browser                         Bridge API
──────────                   ───────                         ──────────
generate_token("alice")  →   paste JWT into modal        →  GET /api/auth/verify
                         ←   {user_id, is_admin}         ←  200 OK
                             store in localStorage
                             esFetch attaches Bearer      →  GET /api/reports
                                                          ←  200 + data
```

---

## 2. Token Generation (Admin Side)

```python
# From core_engine/ directory:
from auth.tokens import generate_token

token = generate_token("alice", ttl_seconds=86400)   # 24 h
print(token)
```

Or via CLI:
```bash
python -c "from auth.tokens import generate_token; print(generate_token('alice'))"
```

Required env vars when running the server:
```
JWT_SECRET=<strong-random-secret>
ADMIN_USER_IDS=alice,bob          # comma-separated admin user IDs
JWT_TTL_SECONDS=86400             # optional; default 3600
```

---

## 3. Login Flow (Browser)

1. User opens the app. `esFetch` transparently attaches `Authorization: Bearer <token>`
   if a session exists in `localStorage`.
2. On first visit (or after expiry/logout), a protected API call returns **401**.
3. `esFetch` catches the 401, clears `localStorage`, and shows the **login modal**.
4. User pastes a JWT into the textarea and clicks **دخول** (Enter).
5. Frontend calls `GET /api/auth/verify` with the pasted token — **no password sent**.
6. On success (`200`): token + `user_id` + `is_admin` saved to `localStorage` as
   `es_auth`. Modal closes. Top-right bar shows `user_id [مسؤول]` (admin badge
   shown only if `is_admin === true`).
7. On failure (`401`): inline error shown; nothing stored.

---

## 4. Token Storage

| Key | Value |
|---|---|
| `localStorage` key | `es_auth` |
| Stored fields | `token` (JWT string), `user_id` (string), `is_admin` (boolean) |
| Cleared on | logout button · 401 response from any `esFetch` call |

**XSS Warning:** `localStorage` is accessible to any JavaScript running on the same
origin. In the current MVP this is acceptable because the app is served from a
single trusted origin. For hardened production deployment, consider:
- `HttpOnly` cookies (requires server-side session endpoint)
- Strict CSP headers (`Content-Security-Policy`)
- Short token TTLs (e.g. `JWT_TTL_SECONDS=3600`)

---

## 5. esFetch Wrapper

`window.esFetch(url, opts)` — drop-in replacement for `fetch()` on protected routes.

| Scenario | Behaviour |
|---|---|
| Token exists | Adds `Authorization: Bearer <token>` header |
| No token | Sends request without header (server returns 401) |
| Response 401 | Clears session · shows login modal · throws `ES_AUTH_401` |
| Response 403 | Shows inline "admin-required" message · throws `ES_AUTH_403` |
| Other codes | Returns `Response` as-is (caller handles) |

**Callers (as of #7b):**

| Call site | Endpoint |
|---|---|
| Valuation form submit | `POST /api/valuation` |
| Reports history load | `GET /api/reports` |
| Report detail overlay | `GET /api/reports/<id>` |
| PDF download | `GET /api/reports/<id>/pdf` |

**Excluded from esFetch (intentional):**

| Call site | Reason |
|---|---|
| `GET /api/price-index` | Background auto-call on page load; must not trigger modal |
| `POST /api/radar/start` | Background auto-call on page load; must not trigger modal |

---

## 6. Backend Endpoint

`GET /api/auth/verify` — added in commit `d8c9d5d`.

- Requires valid `Authorization: Bearer <token>` header.
- Protected by `@require_auth` (returns `401` if missing/invalid/expired).
- Returns:
  ```json
  { "status": "ok", "user_id": "alice", "is_admin": true }
  ```
- Audited via `_AUDITED_PREFIXES` — every verify call is logged to the audit DB.
- Test coverage: `core_engine/tests/test_bridge_api_login.py` (AV01–AV10).

---

## 7. Logout

Clicking **خروج** in the top-right bar:
1. Calls `window.esHandleLogout()`.
2. Clears `es_auth` from `localStorage`.
3. Hides the logged-in bar.

The server-side JWT is not invalidated (stateless JWT — no server-side revocation
in this MVP). The token remains valid until its `exp` claim expires. For hardened
production, implement a token revocation list (e.g. Redis blocklist).

---

## 8. Production Hardening Path

| Item | Priority | Notes |
|---|---|---|
| Short JWT TTL | P0 | Set `JWT_TTL_SECONDS=3600` or lower in production |
| HTTPS only | P0 | Never send Bearer tokens over plain HTTP |
| Strict CSP | P1 | Prevents XSS exfiltration of `localStorage` token |
| Token revocation list | P1 | Redis/DB blocklist for logout-before-expiry |
| HttpOnly cookie session | P2 | Eliminates XSS token exposure entirely |
| Full SEC-002 rollout | P2 | Extend `@require_auth` to remaining unprotected endpoints |
| Refresh tokens | P3 | Long-lived refresh + short-lived access token pair |

---

**EXPERT_SMART | Auth Flow #7b | 2026-05-19**
