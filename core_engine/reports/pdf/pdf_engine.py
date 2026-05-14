"""
pdf_engine.py — EXPERT_SMART PDF Report Generator (Wave 7a.6).

Single public entry point:
    generate_pdf(*, profile_key, data, output_path, ...) -> Path

Composes all four sections (main_report, sales_comparison,
cost_income_reconciliation, certification) into one paginated document
and writes it to *output_path*.

Determinism: every call with the same inputs produces a byte-identical
file because creation_date, creator, and producer are all fixed
constants rather than live timestamps.

Display-only — no valuation math is performed here.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Optional

from fpdf import FPDF

from .pdf_arabic import find_font
from .pdf_components import draw_footer, register_fonts
from .pdf_theme import DEFAULT, PDFTheme
from .sections.certification_pdf import render_certification
from .sections.cost_income_reconciliation_pdf import render_cost_income_reconciliation
from .sections.main_report_pdf import render_main_report
from .sections.sales_comparison_pdf import render_sales_comparison

# ── Determinism constants ─────────────────────────────────────────────────────

_FIXED_CREATION_DATE: datetime = datetime(2000, 1, 1, 0, 0, 0)
_FIXED_PRODUCER: str = "EXPERT_SMART PDF Engine"
_FIXED_CREATOR: str = "core_engine.reports.pdf"
_FOOTER_TEXT: str = "EXPERT_SMART — تقرير التقييم العقاري"

# ── Valid profile keys ────────────────────────────────────────────────────────

_VALID_PROFILES: frozenset[str] = frozenset({"legacy", "detailed", "professional_template"})


# ── Font registration with optional directory override ────────────────────────

def _register_fonts(pdf: FPDF, fonts_dir: Optional[str | os.PathLike[str]] = None) -> str:
    """Register Cairo fonts, optionally sourcing from *fonts_dir*."""
    if fonts_dir is None:
        return register_fonts(pdf)

    fdir = Path(fonts_dir)
    try:
        regular = str(find_font("cairo-regular", fonts_dir=fdir))
    except FileNotFoundError:
        # Custom dir doesn't have Cairo — fall back to bundled
        return register_fonts(pdf)

    try:
        pdf.add_font("Cairo", style="", fname=regular)
    except Exception:
        pass  # already registered

    try:
        bold = str(find_font("cairo-bold", fonts_dir=fdir))
    except FileNotFoundError:
        bold = regular
    try:
        pdf.add_font("Cairo", style="B", fname=bold)
    except Exception:
        pass
    return "Cairo"


# ── FPDF subclass with auto-footer ────────────────────────────────────────────

class _ReportPDF(FPDF):
    """FPDF subclass that draws the branded footer on every page."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._font_family: str = "Helvetica"
        self._theme: PDFTheme = DEFAULT

    def footer(self) -> None:
        draw_footer(self, _FOOTER_TEXT, font_family=self._font_family, theme=self._theme)


# ── Public API ────────────────────────────────────────────────────────────────

def generate_pdf(
    *,
    profile_key: str = "legacy",
    data: Mapping[str, Any],
    output_path: str | os.PathLike[str],
    fonts_dir: Optional[str | os.PathLike[str]] = None,
    theme: PDFTheme = DEFAULT,
) -> Path:
    """
    Generate a complete PDF valuation report and write it to *output_path*.

    Args:
        profile_key: 'legacy' / 'detailed' / 'professional_template'.
        data: Report payload with the following optional top-level keys:
            - 'appraiser'        dict  → main_report identity block
            - 'property_info'    dict  → main_report property block
            - 'valuation_results' dict → main_report KPI/summary block
            - 'subject'          dict  → sales_comparison subject
            - 'comparables'      list  → sales_comparison comps
            - 'cost_approach'    dict  → cost section
            - 'income_approach'  dict  → income section
            - 'reconciliation'   dict  → reconciliation section
            - 'certification'    dict  → certification appraiser block
        output_path: Destination file path (created with parents as needed).
        fonts_dir: Override Cairo font directory (None → built-in assets/).
        theme: PDFTheme instance (defaults to DEFAULT Midnight Gold).

    Returns:
        Path to the written PDF file.

    Raises:
        ValueError: If *profile_key* is not a valid value.
        OSError:    If the parent directory cannot be created or the file
                    cannot be written.
    """
    if profile_key not in _VALID_PROFILES:
        raise ValueError(
            f"Unknown profile_key {profile_key!r}. "
            f"Valid: {sorted(_VALID_PROFILES)}"
        )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    pdf = _ReportPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=theme.margin_bottom)

    # Determinism — fixed metadata so output is byte-stable
    pdf.set_creation_date(_FIXED_CREATION_DATE)
    pdf.set_creator(_FIXED_CREATOR)
    pdf.producer = _FIXED_PRODUCER

    # Font registration (with optional custom directory override)
    fam = _register_fonts(pdf, fonts_dir=fonts_dir)
    pdf._font_family = fam
    pdf._theme = theme

    # ── Section composition ────────────────────────────────────────────────────
    pdf.add_page()

    # 1. Main report (always — even with empty dicts)
    render_main_report(
        pdf,
        appraiser=data.get("appraiser") or {},
        property_info=data.get("property_info") or {},
        valuation_results=data.get("valuation_results") or {},
        profile_key=profile_key,
        font_family=fam,
        theme=theme,
    )

    # 2. Sales comparison (only if subject or comparables present)
    subject = data.get("subject")
    comparables = data.get("comparables")
    if subject is not None or comparables is not None:
        render_sales_comparison(
            pdf,
            subject=subject or {},
            comparables=comparables or [],
            profile_key=profile_key,
            font_family=fam,
            theme=theme,
        )

    # 3. Cost / Income / Reconciliation (each independently skipped if absent)
    render_cost_income_reconciliation(
        pdf,
        cost_approach=data.get("cost_approach"),
        income_approach=data.get("income_approach"),
        reconciliation=data.get("reconciliation"),
        profile_key=profile_key,
        font_family=fam,
        theme=theme,
    )

    # 4. Certification (always — even with empty dict)
    render_certification(
        pdf,
        appraiser=data.get("certification") or {},
        profile_key=profile_key,
        font_family=fam,
        theme=theme,
    )

    pdf.output(str(out))
    return out
