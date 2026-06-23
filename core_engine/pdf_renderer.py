"""
pdf_renderer.py — Centralised HTML-to-PDF renderer using Playwright/Chromium.

Public API
----------
render_pdf_from_html(html: str) -> bytes
    Render an HTML string to PDF bytes.  Chromium handles Arabic shaping,
    RTL layout, and bidi — no fpdf, no arabic_reshaper, no python-bidi.

cairo_font_css() -> str
    Return a ready-to-embed CSS @font-face block that loads the bundled
    Cairo TTF from a base64 data URI (no network request required).
"""
from __future__ import annotations

import base64
from pathlib import Path

_FONTS_DIR = Path(__file__).parent / "reports" / "pdf" / "assets" / "fonts"


def cairo_font_css() -> str:
    """Return @font-face CSS for Cairo Regular + Bold from bundled TTF files.

    Falls back to an empty string when the font files are missing so callers
    can still render (Chromium will use system Tahoma/Arial for Arabic).
    """
    def _b64(name: str) -> str:
        p = _FONTS_DIR / name
        return "data:font/truetype;base64," + base64.b64encode(p.read_bytes()).decode("ascii")

    try:
        r_uri = _b64("Cairo-Regular.ttf")
        b_uri = _b64("Cairo-Bold.ttf")
    except Exception:
        return ""

    return (
        "@font-face {"
        "font-family:'Cairo';font-weight:400;font-style:normal;"
        f"src:url('{r_uri}') format('truetype');}}\n"
        "@font-face {"
        "font-family:'Cairo';font-weight:700;font-style:normal;"
        f"src:url('{b_uri}') format('truetype');}}\n"
    )


def render_pdf_from_html(html: str) -> bytes:
    """Render *html* to A4 PDF bytes using Playwright/Chromium headless.

    Raises RuntimeError if Playwright or Chromium is unavailable.
    Never falls back to FPDF — FPDF cannot shape Arabic correctly.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is required for Arabic PDF generation but is not installed. "
            "Run: pip install playwright && playwright install chromium"
        ) from exc

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(locale="ar-EG")
            page.set_content(html, wait_until="networkidle")
            return page.pdf(
                format="A4",
                print_background=True,
                margin={
                    "top":    "16mm",
                    "right":  "14mm",
                    "bottom": "16mm",
                    "left":   "14mm",
                },
            )
        finally:
            browser.close()
