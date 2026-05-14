"""
test_pdf_theme.py — Wave 7a.1 PDF Theme foundation (16 tests)

Tests:
  Singleton (2): DEFAULT is PDFTheme, frozen (immutable)
  Palette (6): ink #0B1437, gold #C9A961, navy #1B3263, white, emerald, coral
  Typography (4): font_primary=Cairo, size_title=22, size_section=13, size_body=10.5
  Layout (2): margins positive, banner_h positive
  Custom instance (1): override size_title without mutating DEFAULT
  Type coverage (1): all 19 color fields are valid RGB tuples
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_CORE))
os.chdir(str(_CORE))

import pytest

from reports.pdf.pdf_theme import PDFTheme, DEFAULT


# ── Module-level singleton ────────────────────────────────────────────────────

class TestSingleton:
    def test_default_is_pdfttheme_instance(self):
        assert isinstance(DEFAULT, PDFTheme)

    def test_pdfttheme_is_frozen_immutable(self):
        with pytest.raises((TypeError, AttributeError)):
            DEFAULT.ink = (0, 0, 0)  # type: ignore[misc]


# ── Palette correctness (mirrors report_theme.Palette) ───────────────────────

class TestPalette:
    def test_ink_is_0b1437(self):
        assert DEFAULT.ink == (0x0B, 0x14, 0x37)

    def test_gold_is_c9a961(self):
        assert DEFAULT.gold == (0xC9, 0xA9, 0x61)

    def test_navy_is_1b3263(self):
        assert DEFAULT.navy == (0x1B, 0x32, 0x63)

    def test_white_is_255_255_255(self):
        assert DEFAULT.white == (255, 255, 255)

    def test_emerald_is_0e8b6e(self):
        assert DEFAULT.emerald == (0x0E, 0x8B, 0x6E)

    def test_coral_is_d85842(self):
        assert DEFAULT.coral == (0xD8, 0x58, 0x42)


# ── Typography ────────────────────────────────────────────────────────────────

class TestTypography:
    def test_font_primary_is_cairo(self):
        assert DEFAULT.font_primary == "Cairo"

    def test_size_title_is_22(self):
        assert DEFAULT.size_title == 22.0

    def test_size_section_header_is_13(self):
        assert DEFAULT.size_section_header == 13.0

    def test_size_body_is_10_5(self):
        assert DEFAULT.size_body == 10.5


# ── Layout dimensions ─────────────────────────────────────────────────────────

class TestLayout:
    def test_all_margins_are_positive(self):
        assert DEFAULT.margin_top > 0
        assert DEFAULT.margin_bottom > 0
        assert DEFAULT.margin_left > 0
        assert DEFAULT.margin_right > 0

    def test_banner_height_is_positive(self):
        assert DEFAULT.banner_h > 0


# ── Custom instance ───────────────────────────────────────────────────────────

class TestCustomInstance:
    def test_override_size_title_does_not_mutate_default(self):
        custom = PDFTheme(size_title=28.0)
        assert custom.size_title == 28.0
        assert DEFAULT.size_title == 22.0


# ── Full type coverage ────────────────────────────────────────────────────────

class TestColorFields:
    _COLOR_FIELDS = [
        "ink", "navy_deep", "navy", "navy_light", "indigo",
        "gold", "gold_light", "gold_pale",
        "emerald", "coral", "purple", "teal",
        "paper", "grey_100", "grey_300", "grey_500", "grey_700",
        "white", "black",
    ]

    def test_all_color_fields_are_valid_rgb_tuples(self):
        for name in self._COLOR_FIELDS:
            val = getattr(DEFAULT, name)
            assert isinstance(val, tuple) and len(val) == 3, f"{name}: expected 3-tuple"
            for component in val:
                assert isinstance(component, int), f"{name}[{component}] not int"
                assert 0 <= component <= 255, f"{name}[{component}] out of [0,255]"
