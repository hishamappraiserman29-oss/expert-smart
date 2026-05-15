"""
test_phase23_i18n.py — Phase 23 Localization Tests

Covers:
  A. Localization  — set_language, translate, variables, direction, format
  B. ArabicSupport — numerals, date, currency, RTL detection
  C. LanguageDetector — text, headers, browser locale, user preference
  D. Translations  — key consistency, counts, non-English values
"""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from i18n.localization import Localization, Language, TextDirection
from i18n.arabic_support import ArabicSupport
from i18n.language_detector import LanguageDetector
from i18n.translations import get_translations, ENGLISH_TRANSLATIONS, ARABIC_TRANSLATIONS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_loc() -> Localization:
    """Localization instance with EN and AR loaded."""
    loc = Localization()
    loc.load_translations(Language.ENGLISH, get_translations("en"))
    loc.load_translations(Language.ARABIC, get_translations("ar"))
    loc.set_language(Language.ENGLISH)
    return loc


# ===========================================================================
# A. Localization
# ===========================================================================

class TestLocalization:

    def test_A01_set_language_returns_true(self):
        loc = _make_loc()
        assert loc.set_language(Language.ARABIC) is True

    def test_A02_set_language_updates_current(self):
        loc = _make_loc()
        loc.set_language(Language.ARABIC)
        assert loc.get_current_language() == Language.ARABIC

    def test_A03_set_unknown_language_returns_false(self):
        loc = Localization()
        assert loc.set_language(Language.FRENCH) is False

    def test_A04_translate_english(self):
        loc = _make_loc()
        loc.set_language(Language.ENGLISH)
        assert loc.t("button.submit") == "Submit"

    def test_A05_translate_arabic(self):
        loc = _make_loc()
        loc.set_language(Language.ARABIC)
        assert loc.t("button.submit") == "إرسال"

    def test_A06_translate_missing_key_returns_key(self):
        loc = _make_loc()
        assert loc.t("nonexistent.key") == "nonexistent.key"

    def test_A07_translate_with_variable_substitution(self):
        loc = Localization()
        loc.load_translations(Language.ENGLISH, {"msg": "Found {count} items"})
        loc.set_language(Language.ENGLISH)
        result = loc.t("msg", count=42)
        assert "42" in result

    def test_A08_text_direction_arabic_is_rtl(self):
        loc = Localization()
        assert loc.get_text_direction(Language.ARABIC) == TextDirection.RTL

    def test_A09_text_direction_english_is_ltr(self):
        loc = Localization()
        assert loc.get_text_direction(Language.ENGLISH) == TextDirection.LTR

    def test_A10_text_direction_french_is_ltr(self):
        loc = Localization()
        assert loc.get_text_direction(Language.FRENCH) == TextDirection.LTR

    def test_A11_format_currency_english_has_egp_left(self):
        loc = Localization()
        result = loc.format_currency(1000.50, Language.ENGLISH)
        assert result.startswith("EGP")
        assert "1,000.50" in result

    def test_A12_format_currency_arabic_has_egp_right(self):
        loc = Localization()
        result = loc.format_currency(1000.50, Language.ARABIC)
        assert result.endswith("EGP")
        assert "1,000.50" in result

    def test_A13_format_date_english_contains_year(self):
        loc = Localization()
        result = loc.format_date(datetime(2024, 1, 15), Language.ENGLISH)
        assert "2024" in result

    def test_A14_format_date_arabic_contains_year(self):
        loc = Localization()
        result = loc.format_date(datetime(2024, 1, 15), Language.ARABIC)
        assert "2024" in result

    def test_A15_get_ui_direction_rtl_for_arabic(self):
        loc = _make_loc()
        loc.set_language(Language.ARABIC)
        assert loc.get_ui_direction() == "rtl"

    def test_A16_get_ui_direction_ltr_for_english(self):
        loc = _make_loc()
        loc.set_language(Language.ENGLISH)
        assert loc.get_ui_direction() == "ltr"

    def test_A17_load_translations_returns_true(self):
        loc = Localization()
        ok = loc.load_translations(Language.ENGLISH, {"k": "v"})
        assert ok is True

    def test_A18_get_available_languages(self):
        loc = _make_loc()
        langs = loc.get_available_languages()
        assert Language.ENGLISH in langs
        assert Language.ARABIC in langs

    def test_A19_language_name_arabic_native(self):
        loc = Localization()
        name = loc.get_language_name(Language.ARABIC, native=True)
        assert "ع" in name  # Arabic letter

    def test_A20_language_name_english_native(self):
        loc = Localization()
        assert loc.get_language_name(Language.ENGLISH, native=True) == "English"


# ===========================================================================
# B. ArabicSupport
# ===========================================================================

class TestArabicSupport:

    def test_B01_convert_to_arabic_numerals(self):
        result = ArabicSupport.convert_to_arabic_numerals("12345")
        assert "١" in result
        assert "٢" in result
        assert "٥" in result

    def test_B02_convert_to_western_numerals(self):
        result = ArabicSupport.convert_to_western_numerals("١٢٣٤٥")
        assert "1" in result
        assert "5" in result

    def test_B03_roundtrip_numerals(self):
        original = "9876543210"
        arabic = ArabicSupport.convert_to_arabic_numerals(original)
        back = ArabicSupport.convert_to_western_numerals(arabic)
        assert back == original

    def test_B04_format_date_arabic_contains_arabic_month(self):
        date = datetime(2024, 1, 15)
        result = ArabicSupport.format_date_arabic(date, with_day=True)
        assert "يناير" in result

    def test_B05_format_date_arabic_without_day(self):
        date = datetime(2024, 6, 10)
        result = ArabicSupport.format_date_arabic(date, with_day=False)
        assert "يونيو" in result
        assert str(date.year) in result

    def test_B06_format_currency_arabic_contains_currency(self):
        result = ArabicSupport.format_currency_arabic(1000.50)
        assert "جنيه" in result

    def test_B07_format_currency_arabic_contains_arabic_numeral(self):
        result = ArabicSupport.format_currency_arabic(1000.50)
        assert "١" in result

    def test_B08_format_number_arabic_uses_arabic_decimal(self):
        result = ArabicSupport.format_number_arabic(3.14)
        assert "،" in result  # Arabic decimal comma

    def test_B09_is_rtl_text_arabic(self):
        assert ArabicSupport.is_rtl_text("مرحبا") is True

    def test_B10_is_rtl_text_english(self):
        assert ArabicSupport.is_rtl_text("Hello") is False

    def test_B11_is_rtl_text_mixed(self):
        assert ArabicSupport.is_rtl_text("مرحبا Hello") is True

    def test_B12_alignment_methods_return_strings(self):
        assert isinstance(ArabicSupport.get_header_alignment(), str)
        assert isinstance(ArabicSupport.get_body_alignment(), str)
        assert isinstance(ArabicSupport.get_float_alignment(), str)


# ===========================================================================
# C. LanguageDetector
# ===========================================================================

class TestLanguageDetector:

    def test_C01_detect_arabic_from_text(self):
        assert LanguageDetector.detect_from_text("مرحبا بك في النظام") == Language.ARABIC

    def test_C02_detect_english_from_text(self):
        assert LanguageDetector.detect_from_text("Hello welcome to the system") == Language.ENGLISH

    def test_C03_detect_arabic_from_accept_language_header(self):
        headers = {"Accept-Language": "ar-EG,ar;q=0.9"}
        assert LanguageDetector.detect_from_headers(headers) == Language.ARABIC

    def test_C04_detect_french_from_accept_language_header(self):
        headers = {"Accept-Language": "fr-FR,fr;q=0.9"}
        assert LanguageDetector.detect_from_headers(headers) == Language.FRENCH

    def test_C05_detect_english_default_header(self):
        headers = {"Accept-Language": "en-US,en;q=0.9"}
        assert LanguageDetector.detect_from_headers(headers) == Language.ENGLISH

    def test_C06_detect_from_browser_locale_arabic(self):
        assert LanguageDetector.detect_from_browser_locale("ar-EG") == Language.ARABIC

    def test_C07_detect_from_browser_locale_french(self):
        assert LanguageDetector.detect_from_browser_locale("fr-FR") == Language.FRENCH

    def test_C08_detect_from_browser_locale_english(self):
        assert LanguageDetector.detect_from_browser_locale("en-US") == Language.ENGLISH

    def test_C09_user_preference_ar(self):
        assert LanguageDetector.detect_from_user_preference("ar") == Language.ARABIC

    def test_C10_user_preference_ar_eg(self):
        assert LanguageDetector.detect_from_user_preference("ar_EG") == Language.ARABIC

    def test_C11_user_preference_fr(self):
        assert LanguageDetector.detect_from_user_preference("fr") == Language.FRENCH

    def test_C12_user_preference_en(self):
        assert LanguageDetector.detect_from_user_preference("en") == Language.ENGLISH


# ===========================================================================
# D. Translations
# ===========================================================================

class TestTranslations:

    def test_D01_english_translations_non_empty(self):
        trans = get_translations("en")
        assert len(trans) > 0

    def test_D02_english_has_button_submit(self):
        assert "button.submit" in get_translations("en")

    def test_D03_arabic_translations_non_empty(self):
        assert len(get_translations("ar")) > 0

    def test_D04_arabic_has_button_submit(self):
        assert "button.submit" in get_translations("ar")

    def test_D05_arabic_submit_is_not_english(self):
        assert get_translations("ar")["button.submit"] != "Submit"

    def test_D06_french_translations_non_empty(self):
        assert len(get_translations("fr")) > 0

    def test_D07_all_english_keys_in_arabic(self):
        en = get_translations("en")
        ar = get_translations("ar")
        for key in en:
            assert key in ar, f"Missing Arabic translation for key: {key}"

    def test_D08_translations_have_nav_keys(self):
        en = get_translations("en")
        for key in ("nav.home", "nav.valuations", "nav.reports"):
            assert key in en

    def test_D09_translations_have_error_keys(self):
        ar = get_translations("ar")
        assert "error.valuation_failed" in ar

    def test_D10_confidence_keys_exist_all_languages(self):
        for lang in ("en", "ar", "fr"):
            trans = get_translations(lang)
            for key in ("confidence.high", "confidence.medium", "confidence.low"):
                assert key in trans, f"{key} missing from {lang}"

    def test_D11_info_version_has_placeholder(self):
        en = get_translations("en")
        assert "{version}" in en["info.version"]

    def test_D12_arabic_info_version_has_placeholder(self):
        ar = get_translations("ar")
        assert "{version}" in ar["info.version"]
