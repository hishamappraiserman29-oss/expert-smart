# ADR-0011: Deterministic PDF Output (Fixed Creation Date)

- **Status:** Accepted
- **Date:** 2026-05-04

## Context

By default, `fpdf2` embeds the current timestamp into the PDF metadata
(`/CreationDate` and `/ModDate` fields). This means two calls to `generate_pdf()`
with identical input data produce binary-different files — the only difference being
the embedded timestamp.

This non-determinism caused several problems:
1. **Test brittleness** — a byte-comparison test on the PDF output would fail every
   second, not because the content changed but because the timestamp changed.
2. **Cache invalidation** — any caching layer keyed on the output hash (file storage,
   CDN, deduplication) would treat every generation as a unique file.
3. **Auditability** — in a regulated domain (real estate valuation for CBE), it is
   desirable that the same report data always produces the same byte sequence. This
   makes tamper detection trivial: hash the output and compare to the stored reference.

## Options Considered

### Option A — Accept non-determinism
Do not fix the timestamp. Accept that tests cannot compare bytes.

- Pros: Zero implementation effort.
- Cons: Breaks byte-comparison tests. Prevents caching. Complicates audit trails.

### Option B — Fixed creation date in `generate_pdf()` (chosen)
Pass a fixed `creation_date` to fpdf2 at the start of every generation call.
Use a project-epoch constant (`datetime(2026, 1, 1, tzinfo=timezone.utc)`) rather
than `datetime.now()`. This makes the output byte-identical for identical input
across any invocation time.

The actual valuation date (when the report was created by the appraiser) is embedded
in the DTO and rendered in the report body — the PDF metadata date is irrelevant to
the report's legal content.

### Option C — Strip metadata after generation
Generate with a live timestamp, then strip or normalize the PDF metadata fields
using a post-processing library (e.g., `pikepdf`).

- Pros: Works for any PDF library, not just fpdf2.
- Cons: Adds a dependency (`pikepdf`) and a post-processing step. More moving parts
  for a problem that fpdf2 can solve natively.

### Option D — Use content hash as the determinism guarantee
Do not fix the timestamp; instead, define "same report" as "same content hash of
the report body, ignoring metadata." Implement a stripped-hash comparison in tests.

- Cons: Requires a custom comparison utility. Caching is still broken. Audit trail
  is harder to reason about.

## Decision

Adopt Option B. `generate_pdf()` passes `creation_date=datetime(2026, 1, 1, tzinfo=timezone.utc)`
to fpdf2. This is documented as intentional in a code comment. The valuation date
that matters legally is the one rendered in the report body, not the PDF metadata.

## Consequences

**Positive:**
- Byte-identical output for identical input, regardless of when `generate_pdf()` is called.
- Tests can compare PDF hashes or byte sequences directly.
- File deduplication and CDN caching work correctly.
- Tamper detection is straightforward: generate from the stored DTO, compare hashes.

**Negative / Tradeoffs:**
- The PDF `/CreationDate` metadata is misleading — it reads `2026-01-01` regardless
  of when the report was actually generated. Any tool that reads PDF metadata to
  determine report age will be wrong.
- If fpdf2 changes how it handles `creation_date`, the determinism guarantee could
  break silently — must be checked on fpdf2 version upgrades.
- The fixed date is a project-epoch constant, not the valuation date. Future maintainers
  must understand this is intentional, not a bug.
