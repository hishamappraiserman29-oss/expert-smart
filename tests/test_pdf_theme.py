#!/usr/bin/env python3
"""Tests for core_engine/reports/pdf/pdf_theme.py — Wave 7a.1."""

import sys
import io
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_ROOT = Path(__file__).resolve().parent.parent
_CORE = _ROOT / "core_engine"
for _p in (str(_ROOT), str(_CORE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from core_engine.reports.pdf.pdf_theme import PDFTheme, DEFAULT


# ── Module-level singleton ────────────────────────────────────────────────────

def test_default_singleton_is_pdfttheme():
    assert isinstance(DEFAULT, PDFTheme)
    print("✓ test_default_singleton_is_pdfttheme")


def test_pdfttheme_is_frozen():
    """PDFTheme must be immutable (frozen dataclass)."""
    import pytest
    with pytest.raises((TypeError, AttributeError)):
        DEFAULT.ink = (0, 0, 0)  # type: ignore[misc]
    print("✓ test_pdfttheme_is_frozen")


# ── Palette correctness (matches report_theme.Palette) ───────────────────────

def test_ink_color_matches_midnight_gold():
    """INK = #0B1437 → (11, 20, 55)."""
    assert DEFAULT.ink == (0x0B, 0x14, 0x37)
    print(f"✓ test_ink_color_matches_midnight_gold {DEFAULT.ink}")


def test_gold_color_matches_midnight_gold():
    """GOLD = #C9A961 → (201, 169, 97)."""
    assert DEFAULT.gold == (0xC9, 0xA9, 0x61)
    print(f"✓ test_gold_color_matches_midnight_gold {DEFAULT.gold}")


def test_navy_color_is_correct():
    """NAVY = #1B3263 → (27, 50, 99)."""
    assert DEFAULT.navy == (0x1B, 0x32, 0x63)
    print(f"✓ test_navy_color_is_correct {DEFAULT.navy}")


def test_white_is_255_255_255():
    assert DEFAULT.white == (255, 255, 255)
    print("✓ test_white_is_255_255_255")


def test_emerald_color_is_correct():
    """EMERALD = #0E8B6E → (14, 139, 110)."""
    assert DEFAULT.emerald == (0x0E, 0x8B, 0x6E)
    print(f"✓ test_emerald_color_is_correct {DEFAULT.emerald}")


def test_coral_color_is_correct():
    """CORAL = #D85842 → (216, 88, 66)."""
    assert DEFAULT.coral == (0xD8, 0x58, 0x42)
    print(f"✓ test_coral_color_is_correct {DEFAULT.coral}")


# ── Typography ────────────────────────────────────────────────────────────────

def test_font_primary_is_cairo():
    assert DEFAULT.font_primary == "Cairo"
    print("✓ test_font_primary_is_cairo")


def test_size_title_is_22():
    assert DEFAULT.size_title == 22.0
    print("✓ test_size_title_is_22")


def test_size_section_header_is_13():
    assert DEFAULT.size_section_header == 13.0
    print("✓ test_size_section_header_is_13")


def test_size_body_is_10_5():
    assert DEFAULT.size_body == 10.5
    print("✓ test_size_body_is_10_5")


# ── Layout dimensions ─────────────────────────────────────────────────────────

def test_margins_are_positive():
    assert DEFAULT.margin_top > 0
    assert DEFAULT.margin_bottom > 0
    assert DEFAULT.margin_left > 0
    assert DEFAULT.margin_right > 0
    print("✓ test_margins_are_positive")


def test_banner_height_is_positive():
    assert DEFAULT.banner_h > 0
    print(f"✓ test_banner_height_is_positive ({DEFAULT.banner_h}mm)")


# ── Custom instance ───────────────────────────────────────────────────────────

def test_custom_theme_overrides_size_title():
    custom = PDFTheme(size_title=28.0)
    assert custom.size_title == 28.0
    assert DEFAULT.size_title == 22.0  # singleton unchanged
    print("✓ test_custom_theme_overrides_size_title")


def test_all_color_fields_are_rgb_tuples():
    """Every color field must be a 3-tuple of ints in [0, 255]."""
    color_fields = [
        "ink", "navy_deep", "navy", "navy_light", "indigo",
        "gold", "gold_light", "gold_pale",
        "emerald", "coral", "purple", "teal",
        "paper", "grey_100", "grey_300", "grey_500", "grey_700",
        "white", "black",
    ]
    for name in color_fields:
        val = getattr(DEFAULT, name)
        assert isinstance(val, tuple) and len(val) == 3, f"{name} not a 3-tuple"
        for component in val:
            assert 0 <= component <= 255, f"{name}[{component}] out of range"
    print(f"✓ test_all_color_fields_are_rgb_tuples ({len(color_fields)} colors)")


if __name__ == "__main__":
    test_default_singleton_is_pdfttheme()
    test_pdfttheme_is_frozen()
    test_ink_color_matches_midnight_gold()
    test_gold_color_matches_midnight_gold()
    test_navy_color_is_correct()
    test_white_is_255_255_255()
    test_emerald_color_is_correct()
    test_coral_color_is_correct()
    test_font_primary_is_cairo()
    test_size_title_is_22()
    test_size_section_header_is_13()
    test_size_body_is_10_5()
    test_margins_are_positive()
    test_banner_height_is_positive()
    test_custom_theme_overrides_size_title()
    test_all_color_fields_are_rgb_tuples()
    print("\n✅ كل اختبارات pdf_theme (16) نجحت")
