"""
arabic_support.py — Phase 23 Arabic-Specific Support
RTL text, Arabic numerals, Arabic date/currency formatting.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict


class ArabicSupport:
    """Arabic language specific formatting and detection."""

    ARABIC_MONTHS = [
        "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
        "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
    ]

    ARABIC_DAYS = [
        "الاثنين", "الثلاثاء", "الأربعاء", "الخميس",
        "الجمعة", "السبت", "الأحد",
    ]

    ARABIC_NUMERALS: Dict[str, str] = {
        "0": "٠", "1": "١", "2": "٢", "3": "٣", "4": "٤",
        "5": "٥", "6": "٦", "7": "٧", "8": "٨", "9": "٩",
    }

    @staticmethod
    def convert_to_arabic_numerals(text: str) -> str:
        for western, arabic in ArabicSupport.ARABIC_NUMERALS.items():
            text = text.replace(western, arabic)
        return text

    @staticmethod
    def convert_to_western_numerals(text: str) -> str:
        reverse = {v: k for k, v in ArabicSupport.ARABIC_NUMERALS.items()}
        for arabic, western in reverse.items():
            text = text.replace(arabic, western)
        return text

    @staticmethod
    def format_date_arabic(date: datetime, with_day: bool = True) -> str:
        """Format date in full Arabic (e.g. 'الثلاثاء 15 يناير 2024')."""
        day_of_week = ArabicSupport.ARABIC_DAYS[date.weekday()]
        month = ArabicSupport.ARABIC_MONTHS[date.month - 1]
        if with_day:
            return f"{day_of_week} {date.day} {month} {date.year}"
        return f"{date.day} {month} {date.year}"

    @staticmethod
    def format_currency_arabic(amount: float, currency: str = "جنيه") -> str:
        """Format currency with Arabic numerals (e.g. '١،٠٠٠.٥٠ جنيه')."""
        formatted = f"{amount:,.2f}"
        formatted = ArabicSupport.convert_to_arabic_numerals(formatted)
        return f"{formatted} {currency}"

    @staticmethod
    def format_number_arabic(number: float, decimal_places: int = 2) -> str:
        """Format number with Arabic decimal comma and Arabic numerals."""
        formatted = f"{number:,.{decimal_places}f}"
        formatted = formatted.replace(".", "،")
        return ArabicSupport.convert_to_arabic_numerals(formatted)

    @staticmethod
    def is_rtl_text(text: str) -> bool:
        """Return True if text contains Arabic characters (U+0600–U+06FF)."""
        for char in text:
            if 0x0600 <= ord(char) <= 0x06FF:
                return True
        return False

    @staticmethod
    def reverse_text_direction(text: str) -> str:
        return text

    @staticmethod
    def get_header_alignment() -> str:
        return "right"

    @staticmethod
    def get_body_alignment() -> str:
        return "right"

    @staticmethod
    def get_float_alignment() -> str:
        return "left"
