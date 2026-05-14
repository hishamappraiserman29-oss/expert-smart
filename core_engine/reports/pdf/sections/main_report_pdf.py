"""
Main Report Section — cover page: appraiser/property identity, KPIs, summary.

Profile-aware: KPI cards render only for 'detailed' and 'professional_template';
'legacy' shows the identity block + summary table without KPI cards.

Independent of sheets/main_report_sheet.py — shares only the DTO shape.
"""

from __future__ import annotations

from typing import Any, Mapping

from fpdf import FPDF

from ..pdf_components import (
    draw_banner,
    draw_divider,
    draw_kpi_row,
    draw_label_value_row,
    draw_section_header,
    draw_table,
)
from ..pdf_theme import DEFAULT, PDFTheme

# ── Layout helpers (supplement frozen PDFTheme) ───────────────────────────────

_A4_W: float = 210.0
_PARA_GAP: float = 2.0


def _cw(theme: PDFTheme) -> float:
    return _A4_W - theme.margin_left - theme.margin_right


# ── Valid profile keys ────────────────────────────────────────────────────────

_VALID_PROFILES: frozenset[str] = frozenset({"legacy", "detailed", "professional_template"})
_KPI_PROFILES: frozenset[str] = frozenset({"detailed", "professional_template"})


# ── Public API ────────────────────────────────────────────────────────────────

def render_main_report(
    pdf: FPDF,
    *,
    appraiser: Mapping[str, Any],
    property_info: Mapping[str, Any],
    valuation_results: Mapping[str, Any],
    profile_key: str = "legacy",
    font_family: str = "Cairo",
    theme: PDFTheme = DEFAULT,
) -> None:
    """
    Render the main report cover section onto the current PDF page.

    Args:
        pdf: FPDF instance with at least one page.
        appraiser: {'name', 'title', 'firm', 'license', 'date'}.
        property_info: {'address', 'type', 'area', 'tenure', ...}.
        valuation_results: {'market_value', 'price_per_sqm',
                            'confidence', 'value_words', ...}.
        profile_key: 'legacy' / 'detailed' / 'professional_template'.
                     KPI cards appear only for detailed and professional_template.
        font_family: Registered font family ('Cairo' or 'Helvetica').
        theme: PDFTheme (defaults to DEFAULT).

    Raises:
        ValueError: If profile_key is not one of the three valid values.

    Advances the cursor; does not call output().
    """
    if profile_key not in _VALID_PROFILES:
        raise ValueError(
            f"Unknown profile_key {profile_key!r}. "
            f"Valid: {sorted(_VALID_PROFILES)}"
        )

    th = theme

    # ── Title banner ─────────────────────────────────────────────────
    draw_banner(pdf, "تقرير التقييم العقاري", font_family=font_family, theme=th)

    # ── Appraiser + property identity ─────────────────────────────────
    draw_section_header(pdf, "بيانات التقرير", font_family=font_family, theme=th)
    _row(pdf, "اسم المُقَيِّم",  appraiser.get("name"),       font_family, th)
    _row(pdf, "رقم الترخيص",   appraiser.get("license"),    font_family, th)
    _row(pdf, "تاريخ التقييم", appraiser.get("date"),       font_family, th)
    _row(pdf, "عنوان العقار",  property_info.get("address"), font_family, th)
    _row(pdf, "نوع العقار",    property_info.get("type"),   font_family, th)
    _row(pdf, "المساحة (م²)",  property_info.get("area"),   font_family, th)

    pdf.ln(_PARA_GAP)
    draw_divider(pdf, theme=th)

    # ── KPI cards (detailed / professional_template only) ─────────────
    if profile_key in _KPI_PROFILES:
        draw_section_header(pdf, "المؤشرات الرئيسية", font_family=font_family, theme=th)
        cards = _build_kpi_cards(valuation_results)
        if cards:
            draw_kpi_row(pdf, cards, font_family=font_family, theme=th)

    # ── Valuation summary table ────────────────────────────────────────
    draw_section_header(pdf, "ملخص نتائج التقييم", font_family=font_family, theme=th)
    headers = ["البند", "القيمة"]
    rows = _build_summary_rows(valuation_results)
    draw_table(pdf, headers, rows, font_family=font_family, theme=th)


# ── Internal Helpers ──────────────────────────────────────────────────────────

def _row(
    pdf: FPDF, label: str, value: Any, font_family: str, theme: PDFTheme,
) -> None:
    display = str(value) if value not in (None, "") else "—"
    draw_label_value_row(pdf, label, display, font_family=font_family, theme=theme)


def _fmt(value: Any) -> str:
    """Format a value for display — thousands separator for numbers."""
    if value in (None, ""):
        return "—"
    if isinstance(value, (int, float)):
        return f"{value:,.0f}" if value == int(value) else f"{value:,.2f}"
    return str(value)


def _build_kpi_cards(vr: Mapping[str, Any]) -> list[dict[str, str]]:
    """Build the KPI card list from valuation_results, skipping missing values."""
    candidates = [
        ("القيمة السوقية", vr.get("market_value")),
        ("السعر / م²",     vr.get("price_per_sqm")),
        ("درجة الثقة",    vr.get("confidence")),
    ]
    return [
        {"label": label, "value": _fmt(value)}
        for label, value in candidates
        if value not in (None, "")
    ]


def _build_summary_rows(vr: Mapping[str, Any]) -> list[list[str]]:
    """Build the summary table rows from valuation_results."""
    items = [
        ("القيمة السوقية المقدّرة",   vr.get("market_value")),
        ("القيمة بالحروف",            vr.get("value_words")),
        ("السعر للمتر المربع",        vr.get("price_per_sqm")),
        ("درجة الثقة في التقدير",     vr.get("confidence")),
        ("منهج التقييم الأساسي",      vr.get("primary_approach")),
    ]
    return [[label, _fmt(value)] for label, value in items]
