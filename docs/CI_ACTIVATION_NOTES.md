# CI Activation Notes

## State as of مايو 2026 (CI Hardening sprint)

### Workflows Present

| File | Jobs | Trigger |
|---|---|---|
| `.github/workflows/ci-cd.yml` | test → lint → build → deploy | push to `main`/`develop`; PR to `main`; `workflow_dispatch` |
| `.github/workflows/e2e.yml` | e2e (Playwright) | push to `main`; PR to `main`; `workflow_dispatch` |

**Job dependency chain (ci-cd.yml):**
```
test ──┐
       ├──► build (main push only) ──► deploy (workflow_dispatch only)
lint ──┘
```

**Deploy gate:** `deploy` job has `if: github.event_name == 'workflow_dispatch'`
→ production deploy is **always manual-only**. Build (GHCR push) runs on
  every `main` push automatically; it is NOT a deployment.

---

### Validation Results

| Check | Result |
|---|---|
| YAML syntax | ✅ valid |
| Local equivalent run (`pytest core_engine/tests/ --ignore=core_engine/tests/e2e`) | ✅ 1851 passed (e2e excluded from main run; 4 e2e tests covered by e2e.yml) |
| Python version — local | Python 3.13.13 |
| Python version — workflow | `3.13` ✅ aligned |
| `requirements.txt` present | ✅ `core_engine/requirements.txt` |
| `fpdf2`, `arabic-reshaper`, `python-bidi` in requirements | ✅ |
| `PyJWT[crypto]>=2.10.1,<3.0` in requirements | ✅ |
| `pytest-timeout`, `pytest-xdist`, `anyio` in CI install | ✅ |
| E2E workflow `JWT_SECRET` env | ✅ added (dummy value, auth-safe) |
| Secret guard step | ✅ added to test job |
| E2E excluded from main test run (`--ignore=tests/e2e`) | ✅ prevents playwright import error |

---

### Changes Made

#### Round 1 (initial activation)

**`.github/workflows/ci-cd.yml`**
- Python version: `3.11` → `3.13`
- Test dependencies: added `pytest-timeout pytest-xdist anyio`

**`core_engine/requirements.txt`**
- Added `fpdf2`, `arabic-reshaper`, `python-bidi` (PDF engine)

#### Round 2 (CI Hardening sprint, مايو 2026)

**`.github/workflows/ci-cd.yml`**

1. **`--ignore=tests/e2e`** added to pytest command.
   - Reason: E2E tests require `playwright` and a live server; the main CI test
     job installs neither. Without this flag, pytest collection would fail with
     `ModuleNotFoundError: No module named 'playwright'`.
   - E2E coverage is provided by the dedicated `e2e.yml` workflow instead.

2. **Secret guard step** added before "Run tests" (runs from repo root, `shell: python`).
   - Scans all tracked files for:
     - `service_account.json` / `credentials.json` by file name
     - `.env` files (except `.env.example`) by file name
     - `*.db` files under `data/` directories by path pattern
     - PEM private key blocks (`-----BEGIN ... PRIVATE KEY-----\n`) in text files
     - `"type": "service_account"` JSON field in `.json` files only
   - Uses newline-anchored PEM regex to avoid false positives from
     `secrets_scanner.py` which stores detection regexes as Python source.
   - Exits with code 1 if any violation is found.

**`.github/workflows/e2e.yml`**

- Added `env.JWT_SECRET: ci-test-secret-for-e2e-workflow`.
  - Reason: `conftest.py` starts `bridge_api.py` as a subprocess which inherits
    the CI environment. Without JWT_SECRET, the auth middleware uses an empty
    string key; the server starts but any auth-required endpoint returns 401.
    E2E tests only test the UI (DOM + health check), so they pass either way,
    but setting a dummy secret keeps the server in a known-good state and
    prevents spurious console errors that the smoke tests check for.

---

### Known Limitations

| Item | Status |
|---|---|
| `prophet` on Python 3.13 / Linux | prophet ≥1.1 may require compilation on Python 3.13 if no wheel is available. If the e2e install step fails, pin `prophet` to a version with a 3.13 wheel or remove it from requirements.txt and import it lazily. |
| Frontend — no automated tests | Manual checklist only. CI does not cover `frontend/`. |
| `database/` subsystem (PostgreSQL) | Deferred — requires `psycopg2` + live PG. Not in requirements.txt intentionally. |
| Docker `build` job | Requires `GITHUB_TOKEN` (auto-provided). No extra secret needed. |
| `deploy` job | Requires `KUBECONFIG` secret (base64-encoded). Must be added in GitHub repo settings before first deploy. |
| Codecov upload | `continue-on-error: true` — failure does not block CI. |
| Lint (`ruff`) | `|| true` — non-blocking lint warnings appear in logs. |

---

## Activation Steps (User Action Required)

### 1. Verify remote is configured

```bash
git remote -v
```

If empty:
```bash
git remote add origin https://github.com/<your-username>/<your-repo>.git
```

### 2. Push `main`

```bash
git push -u origin main
```

After push, GitHub Actions triggers automatically. Expected:
- **CI/CD Pipeline — Test Suite**: ✅ green (~1851 tests, e2e excluded)
- **CI/CD Pipeline — Lint & Type Check**: ✅ green
- **E2E Tests**: ✅ green (4 Playwright smoke tests)
- **Build**: runs automatically on `main` push, pushes to GHCR
- **Deploy**: NOT triggered (requires `workflow_dispatch`)

### 3. Protect `main` branch

In GitHub: **Settings → Branches → Add branch protection rule**

- Branch: `main`
- ✅ Require status checks to pass before merging
  - Required checks: `Test Suite`, `Lint & Type Check`
- ✅ Require branches to be up to date before merging

### 4. Configure production secrets (when ready to deploy)

Add in GitHub: **Settings → Secrets → Actions**

| Secret | Value |
|---|---|
| `KUBECONFIG` | base64-encoded kubeconfig for your cluster |
| `JWT_SECRET` | strong random secret (production value) |

---

## Secret Guard Reference

The secret guard step (`ci-cd.yml` → `test` job) scans every tracked file
and fails CI if any of the following are found:

| Check | Pattern |
|---|---|
| Credential file by name | `service_account.json`, `credentials.json` |
| `.env` file tracked | any `.env*` except `.env.example` |
| Database in data dir | `*.db` under a `data/` path |
| PEM private key | `-----BEGIN … PRIVATE KEY-----` + newline |
| Service account JSON | `"type": "service_account"` in `.json` files |

To test the guard locally:

```bash
python - << 'EOF'
import sys, pathlib, re, subprocess
# (copy the guard body from ci-cd.yml)
EOF
```

---

## Rollback

```bash
# Revert the workflow change (preferred)
git revert HEAD --no-edit
git push origin main

# Or disable temporarily
# mv .github/workflows/ci-cd.yml .github/workflows/ci-cd.yml.disabled
```

---

**EXPERT_SMART | CI Activation Notes | مايو 2026**
