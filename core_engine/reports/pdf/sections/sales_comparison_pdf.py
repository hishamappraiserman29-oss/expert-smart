"""
Sales Comparison Section — adjustment grid + indicated value.

Renders the comparable properties as an adjustment grid table.
Does NOT compute valuations — it reads pre-computed values from the
DTO (computation belongs to valuation_engines, which are frozen).

Independent of sheets/sales_comparison_sheet.py — shares only the DTO shape.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from fpdf import FPDF

from ..pdf_arabic import prepare_text
from ..pdf_components import (
    draw_banner,
    draw_label_value_row,
    draw_section_header,
    draw_table,
)
from ..pdf_theme import DEFAULT, PDFTheme

# ── Layout helpers (supplement frozen PDFTheme) ───────────────────────────────

_A4_W: float = 210.0
_PARA_GAP: float = 2.0


def _cw(theme: PDFTheme) -> float:
    return _A4_W - theme.margin_left - theme.margin_right


# ── Valid profile keys ────────────────────────────────────────────────────────

_VALID_PROFILES: frozenset[str] = frozenset({"legacy", "detailed", "professional_template"})


# ── Public API ────────────────────────────────────────────────────────────────

def render_sales_comparison(
    pdf: FPDF,
    *,
    subject: Mapping[str, Any],
    comparables: Sequence[Mapping[str, Any]],
    profile_key: str = "legacy",
    font_family: str = "Cairo",
    theme: PDFTheme = DEFAULT,
) -> None:
    """
    Render the sales comparison section onto the current PDF page.

    Args:
        pdf: FPDF instance with at least one page.
        subject: The property being valued — {'address', 'area', 'type', ...}.
        comparables: Sequence of comp dicts, each with keys like
            {'ref', 'address', 'sale_price', 'area', 'price_per_sqm',
             'adjustment_pct', 'adjusted_value'}.
        profile_key: 'legacy' / 'detailed' / 'professional_template'.
        font_family: Registered font family ('Cairo' or 'Helvetica').
        theme: PDFTheme.

    Raises:
        ValueError: If profile_key is not one of the three valid values.

    Advances the cursor; does not call output().
    """
    if profile_key not in _VALID_PROFILES:
        raise ValueError(
            f"Unknown profile_key {profile_key!r}. "
            f"Valid: {sorted(_VALID_PROFILES)}"
        )

    th = theme

    # ── Title banner ─────────────────────────────────────────────────
    draw_banner(pdf, "أسلوب مقارنة البيوع", font_family=font_family, theme=th)

    # ── Subject property block ────────────────────────────────────────
    draw_section_header(pdf, "العقار محل التقييم", font_family=font_family, theme=th)
    _row(pdf, "العنوان",      subject.get("address"), font_family, th)
    _row(pdf, "المساحة (م²)", subject.get("area"),   font_family, th)
    _row(pdf, "نوع العقار",   subject.get("type"),   font_family, th)

    pdf.ln(_PARA_GAP)

    # ── Adjustment grid ───────────────────────────────────────────────
    draw_section_header(pdf, "شبكة التسويات", font_family=font_family, theme=th)

    if not comparables:
        _empty_note(pdf, "لا توجد عقارات مقارنة متاحة.", font_family, th)
        return

    headers = [
        "المرجع", "العنوان", "سعر البيع",
        "المساحة", "السعر/م²", "نسبة التسوية", "القيمة المعدّلة",
    ]
    rows = [_comp_row(c) for c in comparables]

    # Proportional column widths — address gets extra space
    cw = _cw(th)
    col_widths = [
        cw * 0.10,  # المرجع
        cw * 0.24,  # العنوان
        cw * 0.14,  # سعر البيع
        cw * 0.11,  # المساحة
        cw * 0.13,  # السعر/م²
        cw * 0.13,  # نسبة التسوية
        cw * 0.15,  # القيمة المعدّلة
    ]
    draw_table(
        pdf, headers, rows,
        col_widths=col_widths, font_family=font_family, theme=th,
        row_height=6.5,
    )

    # ── Indicated value ───────────────────────────────────────────────
    indicated = _indicated_value(comparables)
    if indicated is not None:
        draw_label_value_row(
            pdf,
            "القيمة المُشار إليها بأسلوب المقارنة",
            _fmt(indicated),
            font_family=font_family,
            theme=th,
        )


# ── Internal Helpers ──────────────────────────────────────────────────────────

def _row(
    pdf: FPDF, label: str, value: Any, font_family: str, theme: PDFTheme,
) -> None:
    display = str(value) if value not in (None, "") else "—"
    draw_label_value_row(pdf, label, display, font_family=font_family, theme=theme)


def _fmt(value: Any) -> str:
    if value in (None, ""):
        return "—"
    if isinstance(value, (int, float)):
        return f"{value:,.0f}" if value == int(value) else f"{value:,.2f}"
    return str(value)


def _comp_row(c: Mapping[str, Any]) -> list[str]:
    """Convert one comparable dict into a table row of strings."""
    return [
        _fmt(c.get("ref")),
        _fmt(c.get("address")),
        _fmt(c.get("sale_price")),
        _fmt(c.get("area")),
        _fmt(c.get("price_per_sqm")),
        _fmt(c.get("adjustment_pct")),
        _fmt(c.get("adjusted_value")),
    ]


def _indicated_value(comparables: Sequence[Mapping[str, Any]]) -> float | None:
    """
    Average of available 'adjusted_value' fields across comparables.

    NOTE: Display-only convenience — authoritative valuation is produced
    by valuation_engines (frozen). Returns None when no numeric
    adjusted_value is present.
    """
    vals = [
        c["adjusted_value"]
        for c in comparables
        if isinstance(c.get("adjusted_value"), (int, float))
    ]
    return sum(vals) / len(vals) if vals else None


def _empty_note(
    pdf: FPDF, text: str, font_family: str, theme: PDFTheme,
) -> None:
    """Render a centered coral-colored note when comparables list is empty."""
    th = theme
    pdf.set_font(font_family, "", th.size_body)
    pdf.set_text_color(*th.coral)
    pdf.set_x(th.margin_left)
    pdf.cell(_cw(th), th.row_h + 2, prepare_text(text), align="C")
    pdf.ln(th.row_h + 2)
    pdf.set_text_color(*th.ink)
