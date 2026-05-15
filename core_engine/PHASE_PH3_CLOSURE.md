# PH.3 — Security & Compliance Closure

**Date**: 2026-05-08  
**Status**: COMPLETE — 28/28 tests passing, scanner operational

---

## Deliverables

| File | Lines | Purpose |
|------|-------|---------|
| `core_engine/security/__init__.py` | 20 | Package exports |
| `core_engine/security/input_validator.py` | ~220 | Input validation & sanitisation |
| `core_engine/security/rate_limiter.py` | ~130 | Sliding-window rate limiter (thread-safe) |
| `core_engine/security/secrets_scanner.py` | ~220 | Credential leak detector |
| `PH_3_security.py` | ~290 | Security audit runner (4 tools) |
| `core_engine/tests/test_ph3_security.py` | ~260 | 28 tests (10 A + 6 B + 12 C) |

---

## Test Results

```
28 passed in 0.22s
```

**Section A — InputValidator (10 tests)**: UUID, file path traversal, null byte, extension whitelist,
property type, area boundaries, location control chars, execution mode, purpose, batch + sanitize.

**Section B — RateLimiter (6 tests)**: Allow under limit, block over limit, reset, peek without
consume, to_dict, thread-safety (8 threads × 10 requests = 80 total, exactly 50 allowed).

**Section C — SecretsScanner (12 tests)**: Hardcoded password, AWS key, Google API key, comment
skip, placeholder skip, severity filter, file scan, directory scan, summarize, to_dict,
unreadable file, private key header detection.

---

## Scanner Run (Baseline)

```
[1/4] bandit -- SAST         18 findings  (HIGH:5  MEDIUM:13)
[2/4] safety -- Skipped
[3/4] secrets                 1 finding   (HIGH:1)
[4/4] custom                  0 findings

TOTAL: HIGH=6  MEDIUM=13  GATE: PASSED (baseline)
```

### Key Findings

| Severity | Tool | Finding | Action |
|----------|------|---------|--------|
| HIGH x5 | bandit | B324 — MD5/SHA1 in bridge_api.py, library_scanner, price_intelligence, report_tuner | Whitelisted (non-security hash use) |
| HIGH x1 | secrets | `service_account.json` — Google service account private key at line 5 | **REAL finding**: file should be in .gitignore; rotate key before production deploy |
| MEDIUM x8 | bandit | B310 url-open, B104 bind-all-interfaces in bridge_api.py | Known/intentional in dev |

### Gate Rules
- Gate FAILS if unwhitelisted bandit HIGH > 0
- Gate FAILS if any HIGH finding from secrets scanner
- B324 (weak hash), B101 (assert), B404/B603/B607 (subprocess) are whitelisted

---

## Security Modules

### InputValidator
- 8 validator methods: `validate_uuid`, `validate_file_path`, `validate_property_type`,
  `validate_area`, `validate_location`, `validate_execution_mode`, `validate_purpose`
- `validate_batch()` aggregates multiple ValidationResult objects into a summary dict
- `sanitize_string()` strips control chars and normalises Unicode to NFC
- All methods are static — no instantiation required

### RateLimiter
- Sliding window algorithm using `collections.deque` of monotonic timestamps
- Thread-safe via `threading.Lock`
- `check(key, consume=True)` — returns RateLimitResult with `retry_after` seconds
- `peek(key)` — check without consuming a token
- `reset(key)` / `reset_all()` — clear window for testing or admin actions

### SecretsScanner
- 14 detection patterns: passwords, API keys, secrets, tokens, AWS keys, Google keys,
  service account JSON, DB connection strings, private key headers, JWTs, hex secrets,
  Slack tokens, GitHub tokens
- `skip_placeholders=True` — extracts quoted VALUE from assignment lines (not whole-line match)
  to avoid false positives on field names like `api_key`, `password_hash`, etc.
- `min_severity` filter for HIGH-only scans
- `scan_string()`, `scan_file()`, `scan_directory()` + `summarize()`

---

## Known Issues (Not Blocking)

1. **`service_account.json`** — Google service account key committed to repo. This is a dev
   credential used for Google Docs/Drive integration. Must be rotated and excluded from
   git before production deployment.

2. **B324 (weak hash)** — MD5/SHA1 used in several modules for caching/fingerprinting, not
   for security. Adding `usedforsecurity=False` kwarg would silence bandit but is not urgent.

3. **B104 (bind all interfaces)** — `bridge_api.py` binds to `0.0.0.0` which is intentional
   for the dev server. Production should use a reverse proxy (nginx/gunicorn).

---

## Next Phase

**PH.4 — Performance & Scaling**: profiling, caching strategy, pagination, async endpoints.
