"""
pdf_theme.py — PDF visual identity (Midnight Gold) for EXPERT_SMART.

Mirrors the hex values from report_theme.Palette / Typography but as
pure-Python dataclass constants so fpdf2 can consume them without
importing openpyxl styles.

Usage:
    from core_engine.reports.pdf.pdf_theme import DEFAULT as theme
    banner_color = theme.ink          # (11, 20, 55) RGB tuple
    font_size    = theme.size_title   # 22
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple


RGBColor = Tuple[int, int, int]


def _hex(h: str) -> RGBColor:
    """Convert 6-char hex string (no #) to (R, G, B) tuple."""
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


@dataclass(frozen=True)
class PDFTheme:
    """Immutable PDF design token bag — Midnight Gold palette."""

    # ── Navy spectrum ──────────────────────────────────────────────────
    ink: RGBColor       = field(default_factory=lambda: _hex("0B1437"))
    navy_deep: RGBColor = field(default_factory=lambda: _hex("12224F"))
    navy: RGBColor      = field(default_factory=lambda: _hex("1B3263"))
    navy_light: RGBColor = field(default_factory=lambda: _hex("294479"))
    indigo: RGBColor    = field(default_factory=lambda: _hex("3A5491"))

    # ── Gold spectrum ───────────────────────────────────────────────────
    gold: RGBColor       = field(default_factory=lambda: _hex("C9A961"))
    gold_light: RGBColor = field(default_factory=lambda: _hex("EBD79A"))
    gold_pale: RGBColor  = field(default_factory=lambda: _hex("F8EFC9"))

    # ── Status colors ───────────────────────────────────────────────────
    emerald: RGBColor = field(default_factory=lambda: _hex("0E8B6E"))
    coral: RGBColor   = field(default_factory=lambda: _hex("D85842"))
    purple: RGBColor  = field(default_factory=lambda: _hex("6B4FA1"))
    teal: RGBColor    = field(default_factory=lambda: _hex("3A9CA1"))

    # ── Neutrals ────────────────────────────────────────────────────────
    paper: RGBColor    = field(default_factory=lambda: _hex("FAF7F0"))
    grey_100: RGBColor = field(default_factory=lambda: _hex("EEF1F7"))
    grey_300: RGBColor = field(default_factory=lambda: _hex("C8CDDB"))
    grey_500: RGBColor = field(default_factory=lambda: _hex("8C93A8"))
    grey_700: RGBColor = field(default_factory=lambda: _hex("586079"))
    white: RGBColor    = field(default_factory=lambda: _hex("FFFFFF"))
    black: RGBColor    = field(default_factory=lambda: _hex("000000"))

    # ── Typography ──────────────────────────────────────────────────────
    font_primary: str  = "Cairo"
    font_fallback: str = "Arial"

    size_title: float          = 22.0
    size_section_header: float = 13.0
    size_label: float          = 10.5
    size_body: float           = 10.5
    size_kpi: float            = 18.0
    size_footer: float         = 9.0

    # ── Layout (mm) ─────────────────────────────────────────────────────
    margin_top: float    = 20.0
    margin_bottom: float = 20.0
    margin_left: float   = 18.0
    margin_right: float  = 18.0
    banner_h: float      = 28.0
    section_h: float     = 10.0
    row_h: float         = 8.0
    footer_h: float      = 12.0


# Module-level singleton — import and use directly.
DEFAULT: PDFTheme = PDFTheme()
