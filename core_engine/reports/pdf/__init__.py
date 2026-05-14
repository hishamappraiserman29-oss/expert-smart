"""core_engine/reports/pdf — PDF Report Engine (Wave 7a)."""

from .pdf_engine import generate_pdf
from .pdf_theme import DEFAULT as DEFAULT_THEME, PDFTheme

__all__ = ["generate_pdf", "PDFTheme", "DEFAULT_THEME"]
