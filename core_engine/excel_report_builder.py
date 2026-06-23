"""
excel_report_builder.py — Shared Excel workbook helpers for internal expert reports.

Provides reusable openpyxl helpers for building internal valuation workbooks.
This module is for expert/admin use only.  Generated workbooks must never be
exposed or linked to ordinary users.

Public API
----------
create_workbook() -> openpyxl.Workbook
apply_rtl(ws) -> None
style_header_row(ws, headers, row=1) -> None
apply_borders(ws, cell_range) -> None
set_column_widths(ws, widths) -> None
add_kpi_card(ws, cell_range, title, value, fill_color=C_BLUE_L) -> None
add_key_value_table(ws, start_row, pairs, label_col=1, value_col=2) -> int
save_workbook(wb, path) -> Path

Colour constants (importable):
  C_BLUE_D, C_BLUE_M, C_BLUE_L, C_GOLD, C_GOLD_BG,
  C_GRAY, C_GREEN, C_RED, C_WHITE
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

# ── Colour palette ────────────────────────────────────────────────────────────

C_BLUE_D  = "1F4E78"
C_BLUE_M  = "2D6A9F"
C_BLUE_L  = "EBF3FB"
C_GOLD    = "D4AF37"
C_GOLD_BG = "FFF9E6"
C_GRAY    = "F5F5F5"
C_GREEN   = "F0FFF6"
C_RED     = "FFF5F5"
C_WHITE   = "FFFFFF"


def _require_openpyxl():
    """Ensure openpyxl is available; raise ImportError with install hint if not."""
    try:
        import openpyxl
        return openpyxl
    except ImportError as exc:
        raise ImportError(
            "openpyxl is required for Excel report generation. "
            "Run: pip install openpyxl"
        ) from exc


def _styles():
    """Return (Font, PatternFill, Alignment, Border, Side, get_column_letter)."""
    try:
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
        return Font, PatternFill, Alignment, Border, Side, get_column_letter
    except ImportError as exc:
        raise ImportError(
            "openpyxl.styles is required. Run: pip install openpyxl"
        ) from exc


# ── Public helpers ────────────────────────────────────────────────────────────

def create_workbook():
    """Create and return a new openpyxl Workbook."""
    openpyxl = _require_openpyxl()
    return openpyxl.Workbook()


def apply_rtl(ws) -> None:
    """Enable right-to-left reading order for the sheet view."""
    try:
        ws.sheet_view.rightToLeft = True
    except Exception:
        pass


def style_header_row(ws, headers: list[str], row: int = 1) -> None:
    """Write a bold, white-on-dark-blue column header row and freeze the row below.

    headers: list of column title strings (indexed from column 1).
    row: the worksheet row number for the header (default 1).
    """
    Font, PatternFill, Alignment, _, _, _ = _styles()
    fill  = PatternFill("solid", fgColor=C_BLUE_D)
    font  = Font(bold=True, color=C_WHITE, name="Arial", size=10)
    align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for col, title in enumerate(headers, 1):
        c           = ws.cell(row=row, column=col, value=title)
        c.font      = font
        c.fill      = fill
        c.alignment = align
    ws.freeze_panes = ws.cell(row=row + 1, column=1)
    apply_rtl(ws)


def apply_borders(ws, cell_range: str) -> None:
    """Apply thin grey borders to all cells in *cell_range* (e.g. 'A1:F10')."""
    _, _, _, Border, Side, _ = _styles()
    thin   = Side(style="thin", color="CCCCCC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    for row_cells in ws[cell_range]:
        for cell in row_cells:
            cell.border = border


def set_column_widths(ws, widths: list[float]) -> None:
    """Set column widths; *widths* is indexed from column 1."""
    _, _, _, _, _, get_column_letter = _styles()
    for col, width in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = width


def add_kpi_card(
    ws,
    cell_range: str,
    title: str,
    value: Any,
    fill_color: str = C_BLUE_L,
) -> None:
    """Merge *cell_range* and write a KPI card with title and value.

    The range must span at least 2 rows.  The title occupies the first row;
    the value occupies the second row (formatted prominently).

    cell_range: e.g. 'A3:C4'
    fill_color: hex colour string without '#', e.g. 'EBF3FB'
    """
    Font, PatternFill, Alignment, _, _, _ = _styles()
    from openpyxl.utils.cell import range_boundaries

    ws.merge_cells(cell_range)
    min_col, min_row, max_col, max_row = range_boundaries(cell_range)

    title_cell           = ws.cell(row=min_row, column=min_col)
    title_cell.value     = title
    title_cell.font      = Font(bold=True, color=C_BLUE_D, name="Arial", size=9)
    title_cell.fill      = PatternFill("solid", fgColor=fill_color)
    title_cell.alignment = Alignment(horizontal="center", vertical="top", wrap_text=True)

    if max_row > min_row:
        val_cell           = ws.cell(row=min_row + 1, column=min_col)
        val_cell.value     = str(value) if value is not None else ""
        val_cell.font      = Font(bold=True, color=C_BLUE_D, name="Arial", size=11)
        val_cell.fill      = PatternFill("solid", fgColor=fill_color)
        val_cell.alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=True
        )


def add_key_value_table(
    ws,
    start_row: int,
    pairs: list[tuple[str, Any]],
    label_col: int = 1,
    value_col: int = 2,
) -> int:
    """Write (label, value) pairs as a two-column table starting at *start_row*.

    Returns the row number immediately after the last written row, so
    callers can chain multiple tables.
    """
    Font, PatternFill, Alignment, _, _, _ = _styles()
    lbl_font  = Font(bold=True, color=C_BLUE_D, name="Arial", size=9)
    val_font  = Font(color="1A1A2E",            name="Arial", size=9)
    lbl_fill  = PatternFill("solid", fgColor=C_BLUE_L)
    val_fill  = PatternFill("solid", fgColor=C_WHITE)
    align_rt  = Alignment(horizontal="right", vertical="center", wrap_text=True)

    for offset, (label, raw_value) in enumerate(pairs):
        row = start_row + offset
        lc           = ws.cell(row=row, column=label_col, value=label)
        lc.font      = lbl_font
        lc.fill      = lbl_fill
        lc.alignment = align_rt
        vc           = ws.cell(row=row, column=value_col,
                               value=str(raw_value) if raw_value is not None else "")
        vc.font      = val_font
        vc.fill      = val_fill
        vc.alignment = align_rt

    return start_row + len(pairs)


def save_workbook(wb, path: str | Path) -> Path:
    """Save *wb* to *path*, creating parent directories as needed.

    Returns the resolved Path so callers can chain with further checks.
    """
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(dest))
    return dest
