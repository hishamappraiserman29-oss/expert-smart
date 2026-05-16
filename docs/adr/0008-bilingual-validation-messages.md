# ADR-0008: Bilingual Validation Messages with Stable Codes

- **Status:** Accepted
- **Date:** 2026-05-05

## Context

The validation engine (ADR-0004) produces `ValidationIssue` objects whenever a
report DTO fails a rule. These issues are surfaced to end users in the frontend,
to API clients in the JSON response, and potentially to audit trails and CBE
compliance reports.

Three audiences with different needs:
1. **Appraisers** — speak Arabic, read the validation output on-screen.
2. **API clients / backend logic** — need to branch on specific rule failures
   programmatically (e.g., suppress a specific warning for a known edge case).
3. **Compliance / audit trails** — need stable, traceable identifiers that do not
   change when wording is revised.

An early prototype returned English-only messages with no machine-readable codes.
This created two problems: appraisers saw English error text in an otherwise Arabic
UI, and programmatic handling required fragile string-matching on the message body.

## Options Considered

### Option A — English-only messages
Single `message` field in English.

- Pros: Simple. No translation maintenance.
- Cons: Appraiser audience reads Arabic. Mixing English error messages into an
  Arabic UI is a usability failure in the target market.

### Option B — Arabic-only messages
Single `message_ar` field in Arabic.

- Pros: Native experience for appraisers.
- Cons: API clients and developers working in English cannot diagnose issues without
  translation. Logging becomes difficult for non-Arabic-speaking engineers.

### Option C — Bilingual messages + stable codes (chosen)
Each `ValidationIssue` carries:
- `message_ar` — Arabic human-readable text for the appraiser UI.
- `message_en` — English human-readable text for API clients and logs.
- `code` — stable SCREAMING_SNAKE_CASE identifier (e.g., `WEIGHTS_SUM_MISMATCH`).
- `severity` — `ERROR` / `WARNING` / `INFO`.
- `field` — dot-notation path to the failing field.

### Option D — i18n catalog
Messages in a single language, translated at render time via a catalog.
- Cons: Requires a translation pipeline, a catalog file, a locale detection mechanism.
  Significant overhead for a fixed two-language requirement.

## Decision

Adopt Option C. The `code` field is the stable contract — clients should branch on
`code`, never on message text. Message text may be revised; codes are never changed
or reused.

The `severity` determines HTTP behavior when `validate=true`:
- `ERROR` → HTTP 422, generation blocked.
- `WARNING` → HTTP 200, generation proceeds, `validation.warnings` populated.
- `INFO` → HTTP 200, informational only.

## Consequences

**Positive:**
- Appraisers see native Arabic error descriptions in the frontend.
- Developers and API clients read English messages in logs and responses.
- `code` enables programmatic handling that survives wording revisions.
- `field` enables the frontend to highlight the specific form section that failed.
- The three-severity model maps cleanly to HTTP behavior — no ambiguous states.

**Negative / Tradeoffs:**
- Every new validation rule requires two message strings — doubles the authoring
  effort per rule.
- Arabic message quality depends on the author; no automated translation check.
- Codes must be globally unique within the validation engine; a collision would
  silently misdirect programmatic handling.
- `severity` escalation (promoting WARNING to ERROR) is a breaking change for any
  client that currently ignores that warning.
