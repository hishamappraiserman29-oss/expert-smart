# Expert_Smart
PropTech Platform for Real Estate Valuation, Central Bank Auditing (Basel III/IV), and Tax Mass Appraisal.

## Core Rules
- **Safety First**: Do not modify any existing valuation logic, tax indices, or LTV thresholds without explicit user approval.
- **Environment**: Development runs on Windows + PowerShell.
- **Backend Setup**: The main application logic resides in `core_engine/`. 
- **Main Entry Point**: `core_engine/bridge_api.py`
- **Local Server**: Running on `http://localhost:5000`.

## Coding Standards
- Use Python strict typing where applicable.
- Do not refactor existing files arbitrarily; make minimal, safe changes.
- For AI logic (RAG pipeline), rely on `System Prompt + Tools Policy` separation of concerns.

## Common Tasks
- To debug API responses, check the logs (e.g. `server.log`, `server_v44.log`) within `core_engine/`.
- Ensure changes to endpoints in `bridge_api.py` are properly tested against mock data matching the valuation dictionary schema.

## Frontend & Local Access
- **Frontend file**: `frontend/index.html` is served at the root by `bridge_api.py`. Open the UI from same-origin: `http://127.0.0.1:5000/`.
- **No `file://`**: Do not open `frontend/index.html` directly from the file system; cross-origin fetches to the API will be blocked by the browser.
- **Smoke test (PowerShell)**:
  ```powershell
  Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/advisor/health" -Method Get
  ```

## Editing Safety
- **Large file caution**: `core_engine/bridge_api.py` is large (~6,600+ lines). Prefer small, targeted edits; avoid wide replacements that risk truncation.
- **Post-edit syntax check** (run after every edit to that file):
  ```powershell
  python -c "import ast, pathlib; ast.parse(pathlib.Path('core_engine/bridge_api.py').read_text(encoding='utf-8'))"
  ```
- **Restart after edit**: Waitress does not auto-reload. Stop the server (Ctrl+C) and re-run `python core_engine/bridge_api.py` to pick up changes.
