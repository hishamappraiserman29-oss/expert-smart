# ADR-0001: Adopt Shared Core Architecture

- **Status:** Accepted
- **Date:** 2026-04-15

## Context

The project originally had three near-duplicate Excel-generation paths — one per
report profile (legacy / detailed / professional_template). Every visual change
(color, font, wording, number format) had to be applied in three places. This led
to drift between profiles and was the largest single source of regressions throughout
the early phases.

Symptoms that triggered the decision:
- A color palette fix applied to `legacy` silently failed to apply to `detailed`.
- KPI section in `professional_template` used a different font size than the others.
- Adding a new section required copy-pasting ~300 lines across three modules.

## Options Considered

### Option A — Continue duplicating
Keep three separate builders. Each profile owns its entire rendering stack.

- Pros: Zero migration risk. No abstraction overhead.
- Cons: O(n×profiles) maintenance. Drift compounds over time. Impossible to
  guarantee visual consistency at scale.

### Option B — Shared Core Architecture (chosen)
Extract a single source of truth:
- `report_profiles.py` — profile registry + feature flags
- `report_theme.py` — visual constants (colors, fonts, margins, number formats)
- `sheets/` — one module per report section, each profile-aware
- `excel_builder.py` — thin orchestrator that calls sheet modules

### Option C — Declarative DSL
Describe reports in YAML/JSON, generate code from the spec. Profiles are config,
not code.

- Pros: Maximum flexibility. Renderer-agnostic.
- Cons: Requires building a DSL parser + renderer. Far outside the project timeline.
  Overkill for a known fixed set of sections.

## Decision

Adopt Option B. The refactoring was executed across 7 phases (Excel waves 1–5,
sheet extraction, profile normalization). `excel_builder.py` became a thin
orchestrator; each of the seven sheet modules holds a single `apply_*` function
that accepts `(ws, data, *, profile_key)`.

The `ReportFeatures` frozen dataclass in `report_profiles.py` controls which sections
are rendered for each profile — a simple boolean gate that any new sheet respects.

## Consequences

**Positive:**
- Single change point for visual identity — one color constant edit propagates to
  all profiles automatically.
- Sheet modules are independently testable without initializing the full builder.
- New profiles take hours instead of days (add an entry to `REGISTRY`, done).
- The three engines (PDF / Validation / DB) can consume the same DTOs and theme
  constants without coupling to each other.

**Negative / Tradeoffs:**
- Initial refactoring effort spanned 7 phases and ~12 commits.
- Every sheet module must inspect `profile_key` — adds a parameter to all `apply_*`
  signatures.
- The profile feature matrix (`ReportFeatures`) must stay in sync with sheet logic;
  stale flags cause silent no-ops.
