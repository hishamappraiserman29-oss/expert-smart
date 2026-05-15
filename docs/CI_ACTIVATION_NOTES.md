# CI Activation Notes

## State as of مايو 2026

### Workflows Present

| File | Jobs | Trigger |
|---|---|---|
| `.github/workflows/ci-cd.yml` | test → lint → build → deploy | push to `main`/`develop`; PR to `main` |

**Job dependency chain:**
```
test ──┐
       ├──► build (main only) ──► deploy (main only, env: production)
lint ──┘
```

---

### Validation Results

| Check | Result |
|---|---|
| YAML syntax | ✅ valid |
| Local equivalent run (`pytest tests/` from `core_engine/`) | ✅ 482/482 passed |
| Python version — local | Python 3.13.13 |
| Python version — workflow (after fix) | `3.13` ✅ aligned |
| `requirements.txt` present | ✅ `core_engine/requirements.txt` |
| `fpdf2` in requirements (after fix) | ✅ added |
| `arabic-reshaper`, `python-bidi` in requirements (after fix) | ✅ added |
| `pytest-timeout`, `pytest-xdist`, `anyio` in CI install step (after fix) | ✅ added |

---

### Changes Made

#### 1. `.github/workflows/ci-cd.yml`

**Python version:** `3.11` → `3.13`
- Reason: local runtime is 3.13; misalignment could hide 3.13-specific behaviour.

**Test dependencies:** added `pytest-timeout pytest-xdist anyio` to the `pip install` line.
- Reason: `pyproject.toml` addopts and some tests use these plugins; missing them causes collection warnings or failures on a clean CI environment.

#### 2. `core_engine/requirements.txt`

Added section:
```
# PDF generation (reports engine)
fpdf2
arabic-reshaper
python-bidi
```
- Reason: PDF engine tests (`test_pdf_*.py`) import `fpdf2`. Without it, all 85 PDF tests would fail on CI with `ModuleNotFoundError`.

---

### Known Limitations

| Item | Status |
|---|---|
| Frontend — no automated tests | Manual checklist only. CI does not cover `frontend/`. |
| `database/` subsystem (PostgreSQL) | Deferred — requires `psycopg2` + live PG. Not in requirements.txt intentionally. |
| Docker `build` job | Requires `GITHUB_TOKEN` (auto-provided by GitHub Actions). No extra secret needed. |
| `deploy` job | Requires `KUBECONFIG` secret (base64-encoded). Must be added in GitHub repo settings before deploying. |
| Codecov upload | `continue-on-error: true` — failure does not block CI. Safe to leave until Codecov account is configured. |
| Lint (`ruff`) | `|| true` — non-blocking. Lint warnings appear in logs but do not fail the job. |

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

### 2. Push `main` and the version tag

```bash
git push -u origin main
git push origin v1.0.0
```

After push, GitHub Actions will trigger automatically on the `main` push.

### 3. Verify on GitHub

1. Go to `https://github.com/<user>/<repo>/actions`
2. You should see **CI/CD Pipeline** running
3. Expected result: **test ✅ green (482 tests)**, **lint ✅ green**
4. **build** job runs only on `main` — will push image to `ghcr.io/<repo>:latest`
5. **deploy** job requires `KUBECONFIG` secret — will fail until configured (acceptable)

### 4. (Optional) Protect `main` branch

In GitHub: **Settings → Branches → Add branch protection rule**

- Branch: `main`
- ✅ Require status checks to pass before merging
  - Required checks: `Test Suite`, `Lint & Type Check`
- ✅ Require branches to be up to date before merging

This ensures no PR can land on `main` without passing CI.

### 5. (Optional) Push the security-only feature branch for review

```bash
git push origin feature/r3-1-security-only
```

Then open a PR: `feature/r3-1-security-only → main` — CI will run on the PR automatically.

---

## Rollback

If CI causes unexpected failures after push:

```bash
# Option A: revert the workflow change via a new commit (preferred)
git revert HEAD --no-edit
git push origin main

# Option B: disable the workflow temporarily
# Rename .github/workflows/ci-cd.yml → ci-cd.yml.disabled
# Commit and push
```

---

**EXPERT_SMART | CI Activation Notes | مايو 2026**
