"""
PDF Components — reusable Midnight Gold drawing blocks for fpdf2.

Each function receives an FPDF instance and draws a styled block,
advancing the cursor. Functions never create FPDF or call output();
they are pure drawing primitives composed by section builders.

All Arabic text is processed through pdf_arabic.prepare_text().
All styling comes from pdf_theme.DEFAULT.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from fpdf import FPDF

from .pdf_arabic import find_font, prepare_text
from .pdf_theme import DEFAULT, PDFTheme

# ── Layout constants (A4 210 × 297 mm) ───────────────────────────────────────

_A4_W: float = 210.0   # mm — A4 width
_SECTION_GAP: float = 4.0   # mm gap after banners / section headers
_PARA_GAP: float = 2.0   # mm gap after dividers and thin elements
_KPI_H: float = 22.0   # default KPI card height


def _cw(theme: PDFTheme) -> float:
    """Usable content width = page width − left margin − right margin."""
    return _A4_W - theme.margin_left - theme.margin_right


# ── Font Registration ─────────────────────────────────────────────────────────

def _safe_add_font(pdf: FPDF, family: str, style: str, fname: str) -> None:
    """Add a TTF font, ignoring 'already registered' errors (idempotent)."""
    try:
        pdf.add_font(family, style=style, fname=fname)
    except Exception:
        pass  # duplicate registration — already usable


def register_fonts(pdf: FPDF, theme: PDFTheme = DEFAULT) -> str:
    """
    Register Cairo (regular + bold) on the FPDF instance.

    Returns the font family name to use ('Cairo' if found, 'Helvetica'
    as last-resort fallback).  Safe to call multiple times on the same
    FPDF instance.
    """
    try:
        regular = str(find_font("cairo-regular"))
    except FileNotFoundError:
        return "Helvetica"

    _safe_add_font(pdf, "Cairo", "", regular)

    bold = regular  # fallback: regular doubles as bold
    try:
        bold = str(find_font("cairo-bold"))
    except FileNotFoundError:
        pass
    _safe_add_font(pdf, "Cairo", "B", bold)

    return "Cairo"


# ── Internal Helper ───────────────────────────────────────────────────────────

def _reset_text(pdf: FPDF, theme: PDFTheme) -> None:
    """Restore text color to default ink."""
    pdf.set_text_color(*theme.ink)


# ── Banners & Headers ─────────────────────────────────────────────────────────

def draw_banner(
    pdf: FPDF,
    text: str,
    *,
    theme: PDFTheme = DEFAULT,
    font_family: str = "Cairo",
) -> None:
    """
    Draw a full-width title banner — Navy background, Gold text.

    Used once at the top of each major report section.
    Advances cursor below the banner + section gap.
    """
    th = theme
    pdf.set_fill_color(*th.navy)
    pdf.set_text_color(*th.gold)
    pdf.set_font(font_family, "B", th.size_title)

    y_start = pdf.get_y()
    pdf.set_xy(th.margin_left, y_start)
    pdf.cell(
        _cw(th),
        th.banner_h,
        prepare_text(text),
        border=0,
        align="C",
        fill=True,
    )
    pdf.set_y(y_start + th.banner_h + _SECTION_GAP)
    _reset_text(pdf, theme)


def draw_section_header(
    pdf: FPDF,
    text: str,
    *,
    theme: PDFTheme = DEFAULT,
    font_family: str = "Cairo",
) -> None:
    """
    Draw a section sub-header — Indigo background, White text.

    Smaller than draw_banner; used for sub-sections.
    Advances cursor below the header + paragraph gap.
    """
    th = theme
    pdf.set_fill_color(*th.indigo)
    pdf.set_text_color(*th.white)
    pdf.set_font(font_family, "B", th.size_section_header)

    y_start = pdf.get_y()
    pdf.set_xy(th.margin_left, y_start)
    pdf.cell(
        _cw(th),
        th.section_h,
        prepare_text(text),
        border=0,
        align="R",
        fill=True,
    )
    pdf.set_y(y_start + th.section_h + _PARA_GAP)
    _reset_text(pdf, theme)


def draw_divider(pdf: FPDF, *, theme: PDFTheme = DEFAULT) -> None:
    """Draw a thin horizontal gold divider line, then advance cursor."""
    th = theme
    pdf.set_draw_color(*th.gold)
    pdf.set_line_width(0.4)
    y = pdf.get_y()
    pdf.line(th.margin_left, y, _A4_W - th.margin_right, y)
    pdf.set_y(y + _PARA_GAP)


# ── KPI Cards ─────────────────────────────────────────────────────────────────

def draw_kpi_card(
    pdf: FPDF,
    *,
    label: str,
    value: str,
    x: float,
    y: float,
    width: float,
    height: float = _KPI_H,
    theme: PDFTheme = DEFAULT,
    font_family: str = "Cairo",
    accent: tuple[int, int, int] | None = None,
) -> None:
    """
    Draw a single KPI card at absolute (x, y).

    Gold-light fill, Navy border, large value above small label.
    The global cursor is saved and restored — caller controls the
    flow cursor independently of card placement.
    """
    th = theme
    accent_color = accent or th.navy

    # Save cursor so absolute card drawing doesn't disturb flow
    saved_x, saved_y = pdf.get_x(), pdf.get_y()

    # Card background + border
    pdf.set_fill_color(*th.gold_light)
    pdf.set_draw_color(*th.navy)
    pdf.set_line_width(0.3)
    pdf.rect(x, y, width, height, style="DF")

    # Value (large, upper half)
    pdf.set_text_color(*accent_color)
    pdf.set_font(font_family, "B", th.size_kpi)
    pdf.set_xy(x, y + 3)
    pdf.cell(width, height / 2 - 3, prepare_text(str(value)), align="C")

    # Label (small, lower half)
    pdf.set_text_color(*th.ink)
    pdf.set_font(font_family, "", th.size_label)
    pdf.set_xy(x, y + height / 2)
    pdf.cell(width, height / 2 - 2, prepare_text(str(label)), align="C")

    # Restore cursor to pre-call position
    pdf.set_xy(saved_x, saved_y)
    _reset_text(pdf, theme)


def draw_kpi_row(
    pdf: FPDF,
    cards: Sequence[Mapping[str, str]],
    *,
    theme: PDFTheme = DEFAULT,
    font_family: str = "Cairo",
    gap: float = 4.0,
) -> None:
    """
    Draw a row of evenly-spaced KPI cards then advance the cursor.

    Each card dict must have 'label' and 'value' keys.
    Empty card list is a no-op.
    """
    if not cards:
        return
    th = theme
    n = len(cards)
    total_gap = gap * (n - 1)
    card_w = (_cw(th) - total_gap) / n
    y = pdf.get_y()

    for i, card in enumerate(cards):
        x = th.margin_left + i * (card_w + gap)
        draw_kpi_card(
            pdf,
            label=card["label"],
            value=card["value"],
            x=x,
            y=y,
            width=card_w,
            theme=theme,
            font_family=font_family,
        )

    pdf.set_y(y + _KPI_H + _SECTION_GAP)


# ── Tables ────────────────────────────────────────────────────────────────────

def draw_table(
    pdf: FPDF,
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    *,
    theme: PDFTheme = DEFAULT,
    font_family: str = "Cairo",
    col_widths: Sequence[float] | None = None,
    row_height: float = 7.0,
) -> None:
    """
    Draw a generic table — Navy header row, alternating gold-light fills.

    Advances cursor below the table + section gap.
    """
    th = theme
    n_cols = len(headers)
    if col_widths is None:
        col_widths = [_cw(th) / n_cols] * n_cols

    # Header row
    pdf.set_fill_color(*th.navy)
    pdf.set_text_color(*th.white)
    pdf.set_font(font_family, "B", th.size_label)
    pdf.set_x(th.margin_left)
    for w, h in zip(col_widths, headers):
        pdf.cell(w, row_height, prepare_text(str(h)), border=1, align="C", fill=True)
    pdf.ln(row_height)

    # Data rows with alternating fill
    pdf.set_font(font_family, "", th.size_body)
    for r_idx, row in enumerate(rows):
        fill = r_idx % 2 == 1
        pdf.set_fill_color(*(th.gold_light if fill else th.white))
        pdf.set_text_color(*th.ink)
        pdf.set_x(th.margin_left)
        for w, cell in zip(col_widths, row):
            pdf.cell(
                w, row_height, prepare_text(str(cell)),
                border=1, align="C", fill=fill,
            )
        pdf.ln(row_height)

    pdf.set_y(pdf.get_y() + _SECTION_GAP)
    _reset_text(pdf, theme)


def draw_label_value_row(
    pdf: FPDF,
    label: str,
    value: str,
    *,
    theme: PDFTheme = DEFAULT,
    font_family: str = "Cairo",
    label_width: float | None = None,
) -> None:
    """
    Draw a single 'label : value' row (RTL — label on right side).

    Label cell: bold, gold-light fill.  Value cell: normal, white fill.
    Advances cursor by one row.
    """
    th = theme
    lw = label_width if label_width is not None else _cw(th) * 0.35
    vw = _cw(th) - lw
    h = th.row_h + 1.5

    pdf.set_x(th.margin_left)

    # Value cell (left column in RTL reading order)
    pdf.set_font(font_family, "", th.size_body)
    pdf.set_text_color(*th.ink)
    pdf.set_fill_color(*th.white)
    pdf.cell(vw, h, prepare_text(str(value)), border=1, align="R", fill=True)

    # Label cell (right column in RTL reading order)
    pdf.set_font(font_family, "B", th.size_label)
    pdf.set_fill_color(*th.gold_light)
    pdf.cell(lw, h, prepare_text(str(label)), border=1, align="R", fill=True)

    pdf.ln(h)
    _reset_text(pdf, theme)


# ── Footer ────────────────────────────────────────────────────────────────────

def draw_footer(
    pdf: FPDF,
    text: str = "",
    *,
    theme: PDFTheme = DEFAULT,
    font_family: str = "Cairo",
) -> None:
    """
    Draw a page footer — gold divider + page number (left) + text (right).

    Uses absolute negative-Y positioning so it sits at the page bottom.
    Call from an FPDF.footer() override or manually.
    """
    th = theme
    y_line = -(th.margin_bottom - 2)
    pdf.set_y(y_line)
    pdf.set_draw_color(*th.gold)
    pdf.set_line_width(0.3)
    pdf.line(th.margin_left, pdf.get_y(), _A4_W - th.margin_right, pdf.get_y())

    pdf.set_y(y_line + 2)
    pdf.set_font(font_family, "", th.size_footer)
    pdf.set_text_color(*th.ink)

    half = _cw(th) / 2
    pdf.set_x(th.margin_left)
    pdf.cell(half, 5, str(pdf.page_no()), align="L")
    pdf.cell(half, 5, prepare_text(text) if text else "", align="R")

    _reset_text(pdf, theme)
