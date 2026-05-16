# E2E Testing Guide

End-to-end (E2E) tests for Expert Smart use [Playwright](https://playwright.dev/) via
`pytest-playwright`.  They launch a real browser (Chromium) against the running
`bridge_api` server and verify the UI behaves correctly.

---

## Prerequisites

Install dev dependencies (if not already present):

```powershell
pip install -r requirements-dev.txt
python -m playwright install chromium
```

These packages are **not** in `requirements.txt` — they are never deployed to production.

---

## Running the Tests

### Option A — Let the fixture start the server

From the project root:

```powershell
pytest core_engine/tests/e2e/ -v
```

The `conftest.py` fixture detects whether port 5000 is already listening:
- **Port free** → starts `python core_engine/bridge_api.py` as a subprocess, waits up
  to 20 s for the health endpoint (`/api/advisor/health`) to return 200, then runs the
  tests, and terminates the server on teardown.
- **Port occupied** → reuses the existing server (e.g. a developer-running instance) and
  does **not** terminate it after the tests finish.

### Option B — Start the server yourself first

```powershell
# Terminal 1
python core_engine/bridge_api.py

# Terminal 2
pytest core_engine/tests/e2e/ -v
```

This is the recommended workflow during active development — startup is instant and
you can inspect server logs while tests run.

---

## Test Inventory

| Test | What it verifies |
|------|-----------------|
| `test_page_loads_without_console_errors` | Home page loads via `networkidle`; no JS `console.error` messages emitted |
| `test_reports_panel_visible` | `#es-reports-panel`, `#es-reports-filter-profile`, `#es-reports-filter-status`, and the `تحديث السجل` refresh button are all visible |
| `test_refresh_renders_table_or_empty_state` | Clicking refresh causes either `#es-reports-table-wrap` to appear (has saved reports) or `#es-reports-state` to show a non-empty message (no reports yet) |
| `test_existing_features_still_work` | `#generateBtn` is present and not disabled — the core valuation entry point is intact |

---

## Configuration

Viewport is fixed at **1280 × 800** for all tests (set in `conftest.py`
`browser_context_args`).  To run with a different browser:

```powershell
pytest core_engine/tests/e2e/ --browser firefox
```

Supported browsers: `chromium` (default), `firefox`, `webkit`.

---

## CI Integration

The workflow `.github/workflows/e2e.yml` runs these tests automatically on every push
to `main` and on pull requests.  Key steps:

1. Install Python deps + `pip install -r requirements-dev.txt`
2. `python -m playwright install --with-deps chromium`
3. `pytest core_engine/tests/e2e/ -v --tb=short`

If the server fails to become ready within 20 s, the fixture calls `pytest.fail()`
with a descriptive message and the job is marked failed.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `bridge_api.py did not become ready within 20 s` | Port conflict or server crash | Run `python core_engine/bridge_api.py` manually and check stderr |
| `Console errors detected on page load` | JS exception in `frontend/index.html` | Open browser DevTools and reproduce manually |
| `TimeoutError` on `wait_for_function` | Slow network / DB I/O | Increase `timeout` in `test_refresh_renders_table_or_empty_state` |
| `playwright._impl._errors.Error: Executable doesn't exist` | Chromium not installed | Run `python -m playwright install chromium` |
| Tests skipped with `no tests ran` | pytest can't find e2e dir | Run from project root, not from `core_engine/` |
