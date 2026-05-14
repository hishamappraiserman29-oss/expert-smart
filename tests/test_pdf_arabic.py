#!/usr/bin/env python3
"""Tests for core_engine/reports/pdf/pdf_arabic.py — Wave 7a.1."""

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

from core_engine.reports.pdf.pdf_arabic import (
    is_rtl,
    reshape_arabic,
    prepare_text,
    find_font,
    fonts_available,
)


# ── is_rtl ────────────────────────────────────────────────────────────────────

def test_is_rtl_arabic_returns_true():
    assert is_rtl("مرحباً") is True
    print("✓ test_is_rtl_arabic_returns_true")


def test_is_rtl_english_returns_false():
    assert is_rtl("Hello World") is False
    print("✓ test_is_rtl_english_returns_false")


def test_is_rtl_digits_returns_false():
    assert is_rtl("123,456") is False
    print("✓ test_is_rtl_digits_returns_false")


def test_is_rtl_mixed_returns_true():
    assert is_rtl("Value: قيمة") is True
    print("✓ test_is_rtl_mixed_returns_true")


def test_is_rtl_empty_returns_false():
    assert is_rtl("") is False
    print("✓ test_is_rtl_empty_returns_false")


# ── reshape_arabic ────────────────────────────────────────────────────────────

def test_reshape_arabic_returns_string():
    result = reshape_arabic("هشام محمد المهدى")
    assert isinstance(result, str)
    assert len(result) > 0
    print("✓ test_reshape_arabic_returns_string")


def test_reshape_arabic_non_arabic_passthrough():
    result = reshape_arabic("Hello")
    assert result == "Hello"
    print("✓ test_reshape_arabic_non_arabic_passthrough")


# ── prepare_text ──────────────────────────────────────────────────────────────

def test_prepare_text_arabic_returns_nonempty():
    result = prepare_text("تقرير تقييم عقاري")
    assert isinstance(result, str)
    assert len(result) > 0
    print("✓ test_prepare_text_arabic_returns_nonempty")


def test_prepare_text_english_unchanged():
    result = prepare_text("Expert Smart")
    assert result == "Expert Smart"
    print("✓ test_prepare_text_english_unchanged")


def test_prepare_text_number_unchanged():
    result = prepare_text("1,250,000")
    assert result == "1,250,000"
    print("✓ test_prepare_text_number_unchanged")


# ── find_font ─────────────────────────────────────────────────────────────────

def test_cairo_regular_is_bundled():
    """Cairo-Regular.ttf must resolve from assets/fonts/."""
    path = find_font("cairo-regular")
    assert path.exists(), f"Cairo-Regular.ttf not found at {path}"
    assert path.suffix.lower() == ".ttf"
    assert "Cairo-Regular" in path.name
    print(f"✓ test_cairo_regular_is_bundled ({path})")


def test_cairo_bold_is_bundled():
    """Cairo-Bold.ttf must resolve from assets/fonts/."""
    path = find_font("cairo-bold")
    assert path.exists(), f"Cairo-Bold.ttf not found at {path}"
    assert "Cairo-Bold" in path.name
    print(f"✓ test_cairo_bold_is_bundled ({path})")


def test_find_font_unknown_raises():
    import pytest
    with pytest.raises(FileNotFoundError):
        find_font("nonexistent-font-xyz")
    print("✓ test_find_font_unknown_raises")


def test_find_font_returns_absolute_path():
    path = find_font("cairo-regular")
    assert path.is_absolute()
    print("✓ test_find_font_returns_absolute_path")


# ── fonts_available ───────────────────────────────────────────────────────────

def test_fonts_available_returns_dict():
    result = fonts_available()
    assert isinstance(result, dict)
    assert len(result) >= 5
    print(f"✓ test_fonts_available_returns_dict ({list(result.keys())})")


def test_fonts_available_cairo_regular_bundled_true():
    result = fonts_available()
    assert result["cairo_regular_bundled"] is True, (
        "Cairo-Regular.ttf must be present in assets/fonts/. "
        "Run: download Cairo font to core_engine/reports/pdf/assets/fonts/"
    )
    print("✓ test_fonts_available_cairo_regular_bundled_true")


def test_fonts_available_cairo_bold_bundled_true():
    result = fonts_available()
    assert result["cairo_bold_bundled"] is True
    print("✓ test_fonts_available_cairo_bold_bundled_true")


def test_fonts_available_has_reshaper_key():
    result = fonts_available()
    assert "reshaper_available" in result
    assert isinstance(result["reshaper_available"], bool)
    print(f"✓ test_fonts_available_has_reshaper_key (value={result['reshaper_available']})")


def test_fonts_available_has_bidi_key():
    result = fonts_available()
    assert "bidi_available" in result
    assert isinstance(result["bidi_available"], bool)
    print(f"✓ test_fonts_available_has_bidi_key (value={result['bidi_available']})")


if __name__ == "__main__":
    test_is_rtl_arabic_returns_true()
    test_is_rtl_english_returns_false()
    test_is_rtl_digits_returns_false()
    test_is_rtl_mixed_returns_true()
    test_is_rtl_empty_returns_false()
    test_reshape_arabic_returns_string()
    test_reshape_arabic_non_arabic_passthrough()
    test_prepare_text_arabic_returns_nonempty()
    test_prepare_text_english_unchanged()
    test_prepare_text_number_unchanged()
    test_cairo_regular_is_bundled()
    test_cairo_bold_is_bundled()
    test_find_font_unknown_raises()
    test_find_font_returns_absolute_path()
    test_fonts_available_returns_dict()
    test_fonts_available_cairo_regular_bundled_true()
    test_fonts_available_cairo_bold_bundled_true()
    test_fonts_available_has_reshaper_key()
    test_fonts_available_has_bidi_key()
    print("\n✅ كل اختبارات pdf_arabic (19) نجحت")
