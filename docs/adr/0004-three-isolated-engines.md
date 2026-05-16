# ADR-0004: Three Isolated Engines (PDF / Validation / DB)

- **Status:** Accepted
- **Date:** 2026-04-25

## Context

Once the Excel builder was stable, three additional capabilities were needed:
1. **PDF generation** — produce a styled Arabic PDF alongside the Excel.
2. **Validation** — catch bad DTO data before generation, not after.
3. **Persistence** — save reports for later retrieval via the history panel.

The question was how to structure these: as a single pipeline object that owns all
three, or as isolated engines that a thin facade orchestrates.

An early prototype put validation logic inside `excel_builder.py` and called
`generate_pdf()` from within the Excel pipeline. This made unit testing impossible
without triggering the full generation stack, and caused font initialization to run
even in validation-only paths.

## Options Considered

### Option A — Monolithic pipeline
One object/module handles validate → build → persist → pdf.
- Pros: Single entry point, no wiring code.
- Cons: All-or-nothing imports. Cannot test validation without PDF dependencies.
  Cannot use DB without the Excel stack. Impossible to adopt engines independently.

### Option B — Three isolated engines + thin facade (chosen)
Each engine has:
- A single public entry point (`validate_report`, `generate_pdf`, `save_report`).
- No imports from the other two engines.
- Its own test suite that runs independently.

`report_pipeline.py` is the only module that imports all three — it is the wiring
layer, not business logic.

### Option C — Plugin architecture
Engines are registered plugins discovered at import time.
- Cons: Adds a registry/discovery mechanism for three fixed components. Over-engineered
  for a known closed set.

## Decision

Adopt Option B. Enforcement rules (not just conventions):
- `reports/validation/` has no import from `reports/pdf/` or `reports/db/`.
- `reports/pdf/` has no import from `reports/validation/` or `reports/db/`.
- `reports/db/` has no import from either other engine.
- Only `report_pipeline.py` and `bridge_api.py` may import from multiple engines.

Each engine is independently startable: `python -c "from reports.validation import validate_report"` succeeds without installing PDF deps.

## Consequences

**Positive:**
- Validation tests run in milliseconds — no font loading, no file I/O.
- PDF engine can be swapped (e.g., replace fpdf2 with WeasyPrint) without touching
  validation or DB.
- DB engine works in environments with no PDF support (e.g., a read-only reporting
  service).
- CI can run all engine tests in parallel without shared state.
- Each engine can be versioned and released independently.

**Negative / Tradeoffs:**
- The shared `report_theme.py` and `report_profiles.py` are imported by all three —
  they must remain side-effect-free at import time.
- `report_pipeline.py` is the load-bearing wiring module; changes there affect all
  paths simultaneously.
- Shared DTOs (the report data dict) are not typed end-to-end — a shape mismatch
  between engines is caught at runtime, not at import time.
