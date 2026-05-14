"""
pdf_arabic.py — Arabic text preparation utilities for fpdf2.

Pipeline:
  raw text → reshape_arabic() → get_display() → ready for PDF cell()

Font resolution order for find_font():
  1. Custom fonts_dir override (keyword arg)
  2. Bundled assets/fonts/ directory (Cairo-Regular/Bold)
  3. Windows system fonts (Arial)
  4. FileNotFoundError if none found

Usage:
    from core_engine.reports.pdf.pdf_arabic import prepare_text, find_font
    pdf.cell(w, h, prepare_text("مرحباً"))
    font_path = find_font("cairo-regular")
"""

from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Optional

# ── Optional dependency guards ────────────────────────────────────────────────

try:
    import arabic_reshaper as _reshaper
    _HAS_RESHAPER = True
except ImportError:  # pragma: no cover
    _HAS_RESHAPER = False

try:
    from bidi.algorithm import get_display as _get_display
    _HAS_BIDI = True
except ImportError:  # pragma: no cover
    _HAS_BIDI = False

# ── Constants ─────────────────────────────────────────────────────────────────

_ASSETS_FONTS = Path(__file__).parent / "assets" / "fonts"

_BUNDLED: dict[str, str] = {
    "cairo-regular": "Cairo-Regular.ttf",
    "cairo-bold":    "Cairo-Bold.ttf",
}

_SYSTEM_WINDOWS: dict[str, str] = {
    "arial":         "arial.ttf",
    "arial-bold":    "arialbd.ttf",
    "times":         "times.ttf",
}

_WINDOWS_FONTS_DIR = Path("C:/Windows/Fonts")

# Arabic Unicode ranges (basic + extended + presentation forms)
_ARABIC_RANGES = (
    (0x0600, 0x06FF),   # Arabic
    (0x0750, 0x077F),   # Arabic Supplement
    (0x08A0, 0x08FF),   # Arabic Extended-A
    (0xFB50, 0xFDFF),   # Arabic Presentation Forms-A
    (0xFE70, 0xFEFF),   # Arabic Presentation Forms-B
    (0x10E60, 0x10E7F), # Rumi Numeral Symbols
)

_HEBREW_RANGES = (
    (0x0590, 0x05FF),
    (0xFB1D, 0xFB4F),
)


# ── Public API ────────────────────────────────────────────────────────────────

def is_rtl(text: str) -> bool:
    """Return True if *text* contains any Arabic or Hebrew codepoints."""
    for ch in text:
        cp = ord(ch)
        for lo, hi in _ARABIC_RANGES:
            if lo <= cp <= hi:
                return True
        for lo, hi in _HEBREW_RANGES:
            if lo <= cp <= hi:
                return True
    return False


def reshape_arabic(text: str) -> str:
    """
    Connect isolated Arabic letters into their contextual presentation forms.

    Requires arabic_reshaper.  Falls back to the original text unchanged when
    the library is unavailable (e.g., in minimal test environments).
    """
    if not _HAS_RESHAPER:
        return text
    return _reshaper.reshape(text)


def prepare_text(text: str) -> str:
    """
    Full Arabic rendering pipeline: reshape → bidi → ready for fpdf2 cell().

    For non-Arabic text the string is returned unchanged.
    """
    if not is_rtl(text):
        return text
    reshaped = reshape_arabic(text)
    if _HAS_BIDI:
        return _get_display(reshaped)
    return reshaped


def find_font(
    name: str = "cairo-regular",
    fonts_dir: Optional[Path] = None,
) -> Path:
    """
    Resolve a font by logical name to an absolute .ttf path.

    Search order:
      1. *fonts_dir* override (if given)
      2. Bundled assets/fonts/ (Cairo-Regular, Cairo-Bold)
      3. Windows system fonts (Arial family)

    Raises FileNotFoundError when no match is found.
    """
    key = name.lower().strip()

    # 1. Custom override directory
    if fonts_dir is not None:
        fonts_dir = Path(fonts_dir)
        filename = _BUNDLED.get(key) or _SYSTEM_WINDOWS.get(key)
        if filename:
            candidate = fonts_dir / filename
            if candidate.exists():
                return candidate.resolve()

    # 2. Bundled assets/fonts/
    if key in _BUNDLED:
        candidate = _ASSETS_FONTS / _BUNDLED[key]
        if candidate.exists():
            return candidate.resolve()

    # 3. Windows system fonts
    if key in _SYSTEM_WINDOWS:
        candidate = _WINDOWS_FONTS_DIR / _SYSTEM_WINDOWS[key]
        if candidate.exists():
            return candidate.resolve()

    # Also accept bare "arial" → try system
    for sys_key, sys_file in _SYSTEM_WINDOWS.items():
        if key in sys_key or sys_key in key:
            candidate = _WINDOWS_FONTS_DIR / sys_file
            if candidate.exists():
                return candidate.resolve()

    raise FileNotFoundError(
        f"Font '{name}' not found in bundled assets or Windows system fonts. "
        f"Searched: {_ASSETS_FONTS}, {_WINDOWS_FONTS_DIR}"
    )


def fonts_available(fonts_dir: Optional[Path] = None) -> dict[str, bool]:
    """
    Return a status dict indicating which fonts are resolvable.

    Keys:
      cairo_regular_bundled  — Cairo-Regular.ttf present in assets/fonts/
      cairo_bold_bundled     — Cairo-Bold.ttf present in assets/fonts/
      arial_system           — arial.ttf present in Windows system fonts
      reshaper_available     — arabic_reshaper importable
      bidi_available         — python-bidi importable
    """
    base = fonts_dir or _ASSETS_FONTS

    def _exists(path: Path) -> bool:
        return path.exists()

    return {
        "cairo_regular_bundled": _exists(_ASSETS_FONTS / "Cairo-Regular.ttf"),
        "cairo_bold_bundled":    _exists(_ASSETS_FONTS / "Cairo-Bold.ttf"),
        "arial_system":          _exists(_WINDOWS_FONTS_DIR / "arial.ttf"),
        "reshaper_available":    _HAS_RESHAPER,
        "bidi_available":        _HAS_BIDI,
    }
