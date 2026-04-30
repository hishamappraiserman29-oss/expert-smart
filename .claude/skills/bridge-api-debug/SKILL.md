# Skill: Bridge API Debugging

## Purpose
Safely debug and fix issues within `core_engine/bridge_api.py` without breaking existing endpoints or altering robust routing mechanisms.

## Context
- **Target File**: `core_engine/bridge_api.py`
- **Port**: `http://localhost:5000`
- **Environment**: Windows + PowerShell
- **Logs**: Search `core_engine/*.log` for tracebacks before editing.

## Safety Constraints
- **Zero Breakage**: Focus ONLY on the requested endpoint/bug. Do not refactor imports or unrelated endpoints.
- **Minimal Code Touches**: If adding a new feature, append it safely or propose modular extraction rather than gutting existing functions.
- **Validation**: Ensure that JSON payload reading (using `request.get_json()`) is wrapped in try-except blocks to catch formatting errors.
- **Reporting**: Always communicate exactly which lines were modified and why.

## Troubleshooting

### CORS / connectivity
- Symptom: browser console shows `Failed to fetch` or `blocked by CORS policy`.
- Resolution checklist:
  1. Confirm the Flask server is up on `http://127.0.0.1:5000` (not stopped).
  2. Open the UI from same-origin only: `http://127.0.0.1:5000/`. Never use `file://`.
  3. If the response is `404` for a known route, the server is running an older build — restart it.

### Localhost testing (PowerShell)
- Health check:
  ```powershell
  Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/advisor/health" -Method Get
  ```
- Inspect a route's existence without invoking heavy logic:
  ```powershell
  curl.exe -I http://127.0.0.1:5000/api/<route>
  ```

### Restart workflow (waitress)
- Waitress in `bridge_api.py` is not a dev-reloader. After any edit:
  1. Stop the running server with Ctrl+C.
  2. Run `python core_engine/bridge_api.py` again.
  3. Re-issue the failing request to confirm the fix.

### Large-file editing caution
- `core_engine/bridge_api.py` exceeds 5,000 lines. When editing:
  - Make one small change at a time.
  - After each edit, run a syntax check:
    ```powershell
    python -c "import ast, pathlib; ast.parse(pathlib.Path('core_engine/bridge_api.py').read_text(encoding='utf-8'))"
    ```
  - If the check fails, revert immediately rather than chaining further edits.

### Payload schema validation (`/api/valuation`)
- Validate inputs only against fields actually observed in the existing handler — do not invent new keys.
- Wrap `request.get_json()` in try-except (already specified above) and return a clear `400` with the offending field name when invalid.
- When in doubt, log the received payload structure (keys only, never values) and ask the user before adding new required fields.
