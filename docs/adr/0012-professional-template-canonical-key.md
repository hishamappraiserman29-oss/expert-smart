# ADR-0012: `professional_template` is the Canonical Profile Key

- **Status:** Accepted
- **Date:** 2026-05-09

## Context

The highest-tier report profile existed under at least two spellings in the codebase
at different points in the project history:
- `"professional"` — used in early profile registry drafts.
- `"professional_template"` — the actual key in `REGISTRY` from Phase 1 onwards.

Because the key is a plain string passed through the API payload, the mismatch was
invisible at import time. It only manifested at runtime when `profile_key` was looked
up in `REGISTRY` — returning `PROFILE_UNKNOWN` error or falling back to `legacy`
silently, depending on the fallback implementation at that moment.

The specific incident: `main_report_sheet.py` was discovered using `"professional"`
in its KPI section guard (`if profile_key == "professional":`), causing the
professional-grade KPI rendering to be silently skipped for the `professional_template`
profile. This was caught in commit `12ad8be` and fixed.

## Options Considered

### Option A — Accept both spellings
Normalize at the API boundary: if `profile_key == "professional"`, treat it as
`"professional_template"`.

- Pros: Tolerant of callers using either spelling.
- Cons: The normalization logic must live somewhere and be applied consistently.
  Two spellings in the codebase means two spellings in tests, logs, and documentation —
  the drift problem resurfaces over time.

### Option B — Rename to `"professional"` (shorter)
Use the shorter spelling everywhere. Update `REGISTRY`.

- Cons: All existing callers (frontend, tests, documentation, external integrations)
  that already use `"professional_template"` must be updated. The rename would be
  a breaking change for any deployed client.

### Option C — `"professional_template"` is canonical, zero aliases (chosen)
Declare `"professional_template"` as the single, permanent, canonical key.
Any occurrence of `"professional"` (without `_template`) in code, tests, or
documentation is a bug and must be corrected.

The convention is documented in:
- This ADR.
- `docs/DEVELOPER_HANDOFF.md` (Section 5, convention #4).
- The profile registry itself (`report_profiles.py` — the key is the docstring).

## Decision

Adopt Option C. The key `"professional_template"` is canonical. No alias, no
normalization, no fallback. Callers that pass `"professional"` receive a
`PROFILE_UNKNOWN` validation error — this is intentional, not a bug.

The rule is enforced by the validation engine: an unknown `profile_key` is an
`ERROR`-severity issue that blocks generation (when `validate=true`) and logs a
warning (always).

## Consequences

**Positive:**
- Single source of truth for the key string. Grep is authoritative: any file
  containing `"professional"` without `_template` is a defect.
- The validation engine catches caller mistakes early (422 with clear error code
  `PROFILE_UNKNOWN`) rather than silently producing the wrong report.
- New developers are protected: the handoff documentation makes this explicit as a
  named convention.

**Negative / Tradeoffs:**
- The key is longer than necessary — `"professional_template"` vs `"professional"`.
  Minor UX friction for API consumers.
- Any existing client hardcoded to `"professional"` must be updated before upgrading
  to v1.0.0.
- The suffix `_template` has no semantic meaning beyond distinguishing the key from
  the shorter variant — future readers may wonder why it is there.
