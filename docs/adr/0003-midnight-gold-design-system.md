# ADR-0003: Midnight Gold + Cairo as Visual Identity

- **Status:** Accepted
- **Date:** 2026-04-20

## Context

Before Shared Core Architecture, colors and fonts were scattered as string literals
throughout the builder — `"000080"`, `"C9A961"`, `"Arial"` appearing dozens of times
with no central definition. Any brand-refresh required a grep-and-replace across
multiple files, with high risk of missing an instance.

Additionally, the domain is Egyptian real estate valuation. Reports are consumed by
banks (Central Bank of Egypt), government agencies, and professional appraisers.
The visual language needed to convey authority and formality while supporting
full Arabic RTL rendering.

## Options Considered

### Option A — Continue with scattered literals
No design system. Each sheet module defines its own colors.
- Cons: Guaranteed drift. No brand consistency across profiles or engines.

### Option B — Midnight Gold design system (chosen)
Centralize all visual constants in `report_theme.py`:
- **Palette:** Deep Navy (`#0B1437`) anchored by Gold (`#C9A961`) as the accent.
  Navy signals authority and formality; Gold signals premium quality.
- **Typography:** Cairo (Google Fonts, OFL-1.1 license) as the primary typeface —
  native Arabic/Latin bilingual support, professional look, open license.
- **Fallback:** Arial for environments where Cairo is unavailable.
- **Aliases:** `BuilderPalette` for Excel (openpyxl hex strings) + `PDFTheme` for
  PDF (RGB tuples) — same semantic names, different wire formats.

### Option C — Generic corporate palette
Use a neutral blue/grey scheme with no Arabic-specific font consideration.
- Cons: Generic. No Arabic rendering advantage. Loses the domain-specific identity.

## Decision

Adopt Option B (Midnight Gold). `report_theme.py` defines:
- `BuilderPalette` — named hex color constants for Excel
- `NumFormat` — canonical Excel number-format strings
- `PDFTheme` — frozen dataclass of RGB tuples + typography + spacing constants

All sheet modules import from `report_theme` and use symbolic names
(`palette.NAVY`, `theme.gold`, `NumFormat.EGP_MILLIONS`) — never raw literals.

Cairo TTF is bundled in `core_engine/reports/pdf/assets/` to guarantee identical
rendering across environments regardless of system font installation.

## Consequences

**Positive:**
- Brand change = one file edit (`report_theme.py`). All profiles + both renderers
  (Excel and PDF) update automatically.
- Symbolic names are self-documenting (`palette.GOLD_LIGHT` vs `"EBD79A"`).
- Cairo provides correct Arabic glyph shaping out of the box via `arabic-reshaper`
  + `python-bidi`, which is essential for the RTL field labels in the report.
- No system font dependency — bundled TTF means reproducible output on CI and
  production containers.

**Negative / Tradeoffs:**
- Bundled Cairo TTF adds ~400 KB to the repository.
- fpdf2 emits glyph-missing warnings for some legacy presentation-form Arabic
  characters; these are cosmetic (shapes render correctly) but noisy in logs.
- The dual `BuilderPalette` / `PDFTheme` split means a semantic color has two
  representations — must be kept in sync manually when the palette evolves.
