"""
language_detector.py — Phase 23 Automatic Language Detection
Detect language from text content, HTTP headers, browser locale, or user preference.
"""

from __future__ import annotations

from .localization import Language


class LanguageDetector:
    """Detect language from various input sources."""

    @staticmethod
    def detect_from_text(text: str) -> Language:
        """Detect language by character distribution (Arabic vs Latin)."""
        arabic_count = 0
        english_count = 0
        for char in text:
            code = ord(char)
            if 0x0600 <= code <= 0x06FF:
                arabic_count += 1
            elif char.isalpha() and code < 256:
                english_count += 1
        return Language.ARABIC if arabic_count > english_count else Language.ENGLISH

    @staticmethod
    def detect_from_headers(headers: dict) -> Language:
        """Detect language from HTTP Accept-Language header."""
        accept = headers.get("Accept-Language", "en-US").lower()
        if "ar" in accept:
            return Language.ARABIC
        if "fr" in accept:
            return Language.FRENCH
        return Language.ENGLISH

    @staticmethod
    def detect_from_browser_locale(locale_string: str) -> Language:
        """Detect language from a browser locale string (e.g. 'ar-EG')."""
        lower = locale_string.lower()
        if lower.startswith("ar"):
            return Language.ARABIC
        if lower.startswith("fr"):
            return Language.FRENCH
        return Language.ENGLISH

    @staticmethod
    def detect_from_user_preference(user_language: str) -> Language:
        """Detect language from an explicit user preference string."""
        lower = user_language.lower()
        if lower in ("ar", "arabic", "ar_eg", "ar-eg"):
            return Language.ARABIC
        if lower in ("fr", "french", "fr_fr", "fr-fr"):
            return Language.FRENCH
        return Language.ENGLISH
