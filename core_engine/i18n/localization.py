"""
localization.py — Phase 23 i18n Framework
Supports Arabic, English, French with RTL/LTR, date/currency formatting.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional
from datetime import datetime


class Language(str, Enum):
    ARABIC  = "ar"
    ENGLISH = "en"
    FRENCH  = "fr"


class TextDirection(str, Enum):
    LTR = "ltr"
    RTL = "rtl"


class Localization:
    """Localization engine — translate, format dates/currency/numbers."""

    def __init__(self, default_language: Language = Language.ENGLISH) -> None:
        self.default_language = default_language
        self.current_language = default_language
        self.translations: Dict[Language, Dict[str, str]] = {}
        self.loaded_languages: List[Language] = []

        self.language_config: Dict[Language, Dict] = {
            Language.ARABIC: {
                "name": "Arabic",
                "native_name": "العربية",
                "direction": TextDirection.RTL,
                "locale": "ar_EG",
                "currency": "EGP",
                "date_format": "%d/%m/%Y",
                "time_format": "%H:%M:%S",
            },
            Language.ENGLISH: {
                "name": "English",
                "native_name": "English",
                "direction": TextDirection.LTR,
                "locale": "en_US",
                "currency": "EGP",
                "date_format": "%Y-%m-%d",
                "time_format": "%H:%M:%S",
            },
            Language.FRENCH: {
                "name": "Français",
                "native_name": "Français",
                "direction": TextDirection.LTR,
                "locale": "fr_FR",
                "currency": "EGP",
                "date_format": "%d/%m/%Y",
                "time_format": "%H:%M:%S",
            },
        }

    def set_language(self, language: Language) -> bool:
        if language not in self.translations:
            return False
        self.current_language = language
        return True

    def load_translations(self, language: Language, translations_dict: Dict[str, str]) -> bool:
        self.translations[language] = translations_dict
        if language not in self.loaded_languages:
            self.loaded_languages.append(language)
        return True

    def t(self, key: str, language: Optional[Language] = None, **kwargs) -> str:
        lang = language or self.current_language
        if lang not in self.translations:
            return key
        text = self.translations[lang].get(key, key)
        for var_name, var_value in kwargs.items():
            text = text.replace(f"{{{var_name}}}", str(var_value))
        return text

    def get_language_name(self, language: Optional[Language] = None, native: bool = True) -> str:
        lang = language or self.current_language
        config = self.language_config.get(lang, {})
        return config.get("native_name" if native else "name", lang.value)

    def get_text_direction(self, language: Optional[Language] = None) -> TextDirection:
        lang = language or self.current_language
        config = self.language_config.get(lang, {})
        direction = config.get("direction", TextDirection.LTR)
        if isinstance(direction, str):
            return TextDirection(direction)
        return direction

    def get_locale(self, language: Optional[Language] = None) -> str:
        lang = language or self.current_language
        return self.language_config.get(lang, {}).get("locale", "en_US")

    def format_date(self, date: datetime, language: Optional[Language] = None) -> str:
        lang = language or self.current_language
        fmt = self.language_config.get(lang, {}).get("date_format", "%Y-%m-%d")
        return date.strftime(fmt)

    def format_currency(self, amount: float, language: Optional[Language] = None) -> str:
        lang = language or self.current_language
        currency = self.language_config.get(lang, {}).get("currency", "EGP")
        formatted = f"{amount:,.2f}"
        if lang == Language.ARABIC:
            return f"{formatted} {currency}"
        return f"{currency} {formatted}"

    def format_number(self, number: float, decimal_places: int = 2,
                      language: Optional[Language] = None) -> str:
        lang = language or self.current_language
        formatted = f"{number:,.{decimal_places}f}"
        if lang == Language.ARABIC:
            formatted = formatted.replace(".", "،")
        return formatted

    def get_available_languages(self) -> List[Language]:
        return list(self.translations.keys())

    def get_current_language(self) -> Language:
        return self.current_language

    def get_ui_direction(self) -> str:
        return "rtl" if self.get_text_direction() == TextDirection.RTL else "ltr"


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_localization: Optional[Localization] = None


def get_localization() -> Localization:
    global _localization
    if _localization is None:
        _localization = Localization()
    return _localization


def init_localization(default_language: Language = Language.ENGLISH) -> Localization:
    global _localization
    _localization = Localization(default_language)
    return _localization
