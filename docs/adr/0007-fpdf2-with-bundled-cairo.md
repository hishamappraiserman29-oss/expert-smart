# ADR-0007: fpdf2 with Bundled Cairo TTF

- **Status:** Accepted
- **Date:** 2026-05-04

## Context

The PDF engine needed to produce professionally styled Arabic+English reports.
The core challenges:
1. **Arabic shaping** — Arabic characters must be reshaped from Unicode code points
   to their presentation forms (initial/medial/final/isolated) and reversed for RTL
   display. Raw Unicode fed to a PDF renderer produces disconnected, left-to-right
   glyphs.
2. **Font** — The visual identity (ADR-0003) requires Cairo typeface. It must
   render consistently across developer machines, CI, and production containers.
3. **Licensing** — The library and font must be open-source and suitable for
   commercial use.
4. **No system dependencies** — The project runs on Windows (dev), Linux (CI/prod).
   A library that calls system-level PDF tools (wkhtmltopdf, LibreOffice) adds
   platform-specific install friction.

## Options Considered

### Option A — ReportLab
Mature, widely used. Native PDF generation in Python.

- Pros: Rich feature set. Excellent documentation.
- Cons: ReportLab's open-source version (LGPL) has limited Arabic support.
  The commercial version (RML) has full RTL but requires a paid license.
  System font loading is non-trivial on Windows.

### Option B — WeasyPrint
HTML/CSS → PDF. Rich styling via CSS.

- Pros: Full Arabic RTL via CSS `direction: rtl`. Familiar HTML rendering model.
- Cons: Requires system-level GTK/Cairo shared libraries on Linux. Installation is
  complex in Docker slim images. Not pure Python — binary dependencies.

### Option C — fpdf2 + arabic-reshaper + python-bidi (chosen)
`fpdf2` is a pure-Python PDF library (LGPL). Arabic support via:
- `arabic-reshaper` — converts Unicode to presentation forms.
- `python-bidi` — applies the Unicode Bidirectional Algorithm.
- Bundled Cairo TTF (OFL-1.1) — guaranteed identical rendering everywhere.

### Option D — Platypus (ReportLab's flowable framework)
Higher-level than raw ReportLab. Supports tables, paragraphs, and flowables.
- Cons: Same licensing concern as Option A.

## Decision

Adopt Option C. The pipeline is:

```python
reshaped = arabic_reshaper.reshape(arabic_text)
bidi_text = get_display(reshaped)   # python-bidi
pdf.set_font("Cairo", size=11)
pdf.cell(w, h, bidi_text)
```

Cairo TTF is bundled in `core_engine/reports/pdf/assets/` (Cairo-Regular.ttf and
Cairo-Bold.ttf). The font is registered at engine startup via `fpdf2`'s
`add_font()`. All Arabic text in the report passes through `prepare_text()` in
`pdf_arabic.py` before being passed to fpdf2.

## Consequences

**Positive:**
- Pure Python — `pip install fpdf2 arabic-reshaper python-bidi` is all that is needed.
  No system libraries, no platform-specific installers.
- Bundled font → byte-identical output across dev/CI/prod (supports ADR-0011).
- OFL-1.1 and LGPL licenses are compatible with commercial use.
- `fpdf2` actively maintained; Arabic TTF subsetting is handled automatically.

**Negative / Tradeoffs:**
- `fpdf2` emits glyph-missing warnings for some legacy presentation-form Arabic
  characters (U+FE8x–U+FEFx range). These are cosmetic — the glyphs render from
  the reshaped form — but they appear in logs and can be alarming.
- The two-step reshape + bidi pipeline must be applied consistently; forgetting
  `prepare_text()` on any Arabic string produces garbled output.
- PDF layout is manual (absolute coordinates, not flowable) — complex layouts
  require careful arithmetic rather than automatic reflow.
- Cairo TTF adds ~400 KB to the repository.
