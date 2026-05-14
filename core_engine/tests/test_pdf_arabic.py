"""
test_pdf_arabic.py — Wave 7a.1 PDF Arabic utilities (19 tests)

Tests:
  RTL detection (5): Arabic, English, digits, mixed, empty
  reshape_arabic (2): returns string, non-Arabic passthrough
  prepare_text (3): Arabic pipeline, English unchanged, number unchanged
  find_font (4): cairo-regular bundled, cairo-bold bundled, unknown raises, absolute path
  fonts_available (5): returns dict, cairo_regular=True, cairo_bold=True,
                       reshaper key, bidi key
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_CORE))
os.chdir(str(_CORE))

import pytest

from reports.pdf.pdf_arabic import (
    is_rtl,
    reshape_arabic,
    prepare_text,
    find_font,
    fonts_available,
)


# ── is_rtl ────────────────────────────────────────────────────────────────────

class TestIsRtl:
    def test_arabic_returns_true(self):
        assert is_rtl("مرحباً") is True

    def test_english_returns_false(self):
        assert is_rtl("Hello World") is False

    def test_digits_return_false(self):
        assert is_rtl("123,456") is False

    def test_mixed_arabic_english_returns_true(self):
        assert is_rtl("Value: قيمة") is True

    def test_empty_string_returns_false(self):
        assert is_rtl("") is False


# ── reshape_arabic ────────────────────────────────────────────────────────────

class TestReshapeArabic:
    def test_returns_nonempty_string_for_arabic(self):
        result = reshape_arabic("هشام محمد المهدى")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_non_arabic_returned_unchanged(self):
        assert reshape_arabic("Hello") == "Hello"


# ── prepare_text ──────────────────────────────────────────────────────────────

class TestPrepareText:
    def test_arabic_pipeline_returns_nonempty(self):
        result = prepare_text("تقرير تقييم عقاري")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_english_returned_unchanged(self):
        assert prepare_text("Expert Smart") == "Expert Smart"

    def test_number_returned_unchanged(self):
        assert prepare_text("1,250,000") == "1,250,000"


# ── find_font ─────────────────────────────────────────────────────────────────

class TestFindFont:
    def test_cairo_regular_bundled_resolves(self):
        path = find_font("cairo-regular")
        assert path.exists(), f"Cairo-Regular.ttf not found at {path}"
        assert "Cairo-Regular" in path.name

    def test_cairo_bold_bundled_resolves(self):
        path = find_font("cairo-bold")
        assert path.exists(), f"Cairo-Bold.ttf not found at {path}"
        assert "Cairo-Bold" in path.name

    def test_unknown_font_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            find_font("nonexistent-font-xyz-abc")

    def test_returns_absolute_path(self):
        path = find_font("cairo-regular")
        assert path.is_absolute()


# ── fonts_available ───────────────────────────────────────────────────────────

class TestFontsAvailable:
    def test_returns_dict_with_expected_keys(self):
        result = fonts_available()
        expected_keys = {
            "cairo_regular_bundled",
            "cairo_bold_bundled",
            "arial_system",
            "reshaper_available",
            "bidi_available",
        }
        assert expected_keys.issubset(result.keys())

    def test_cairo_regular_bundled_is_true(self):
        result = fonts_available()
        assert result["cairo_regular_bundled"] is True, (
            "Cairo-Regular.ttf must be present in assets/fonts/"
        )

    def test_cairo_bold_bundled_is_true(self):
        result = fonts_available()
        assert result["cairo_bold_bundled"] is True

    def test_reshaper_available_is_bool(self):
        result = fonts_available()
        assert isinstance(result["reshaper_available"], bool)

    def test_bidi_available_is_bool(self):
        result = fonts_available()
        assert isinstance(result["bidi_available"], bool)
