"""
Cost / Income / Reconciliation Section — three interrelated approaches.

Bundled in one module because reconciliation aggregates the cost and
income approach results. Each approach has its own render_* function;
render_cost_income_reconciliation orchestrates all three.

Display-only — all valuations are pre-computed by valuation_engines
(frozen). This module never performs valuation math; it only formats
and lays out pre-computed values.

Independent of sheets/cost_approach_sheet.py, sheets/income_approach_sheet.py,
and sheets/reconciliation_sheet.py — shares only the DTO shape.
"""

from __future__ import annotations

from typing import Any, Mapping

from fpdf import FPDF

from ..pdf_components import (
    draw_banner,
    draw_divider,
    draw_label_value_row,
    draw_section_header,
    draw_table,
)
from ..pdf_theme import DEFAULT, PDFTheme

# ── Layout helpers ────────────────────────────────────────────────────────────

_SECTION_GAP: float = 4.0

# ── Valid profile keys ────────────────────────────────────────────────────────

_VALID_PROFILES: frozenset[str] = frozenset({"legacy", "detailed", "professional_template"})


# ── Orchestrator ──────────────────────────────────────────────────────────────

def render_cost_income_reconciliation(
    pdf: FPDF,
    *,
    cost_approach: Mapping[str, Any] | None = None,
    income_approach: Mapping[str, Any] | None = None,
    reconciliation: Mapping[str, Any] | None = None,
    profile_key: str = "legacy",
    font_family: str = "Cairo",
    theme: PDFTheme = DEFAULT,
) -> None:
    """
    Render cost approach + income approach + reconciliation sections.

    Args:
        pdf: FPDF instance with at least one page.
        cost_approach: {'rcn', 'depreciation', 'depreciation_pct',
                        'land_value', 'cost_value_indication',
                        'reproduction_cost', 'age_ratio'}.
        income_approach: {'gross_income', 'vacancy_pct', 'opex', 'noi',
                          'cap_rate', 'income_value_indication',
                          'discount_rate', 'growth_rate'}.
        reconciliation: {'weights': {'sales', 'cost', 'income'},
                         'indications': {'sales', 'cost', 'income'},
                         'final_value', 'final_value_words',
                         'confidence_interval'}.
        profile_key: 'legacy' / 'detailed' / 'professional_template'.
                     'professional_template' adds extra rows to cost/income.
        font_family: Registered family ('Cairo' or 'Helvetica').
        theme: PDFTheme.

    Raises:
        ValueError: If profile_key is not one of the three valid values.

    Any approach passed as None is silently skipped.
    Advances cursor; does not call output().
    """
    if profile_key not in _VALID_PROFILES:
        raise ValueError(
            f"Unknown profile_key {profile_key!r}. "
            f"Valid: {sorted(_VALID_PROFILES)}"
        )

    if cost_approach is not None:
        render_cost_approach(
            pdf, cost_approach,
            profile_key=profile_key, font_family=font_family, theme=theme,
        )
    if income_approach is not None:
        render_income_approach(
            pdf, income_approach,
            profile_key=profile_key, font_family=font_family, theme=theme,
        )
    if reconciliation is not None:
        render_reconciliation(
            pdf, reconciliation,
            profile_key=profile_key, font_family=font_family, theme=theme,
        )


# ── Cost Approach ─────────────────────────────────────────────────────────────

def render_cost_approach(
    pdf: FPDF,
    data: Mapping[str, Any],
    *,
    profile_key: str = "legacy",
    font_family: str = "Cairo",
    theme: PDFTheme = DEFAULT,
) -> None:
    """Render the cost approach block (RCN → depreciation → land → value)."""
    th = theme
    draw_banner(pdf, "أسلوب التكلفة", font_family=font_family, theme=th)

    draw_section_header(pdf, "مكوّنات التكلفة", font_family=font_family, theme=th)
    headers = ["البند", "القيمة"]
    rows: list[list[str]] = [
        ["تكلفة الإحلال الجديدة (RCN)", _fmt(data.get("rcn"))],
        ["نسبة الإهلاك",               _fmt(data.get("depreciation_pct"))],
        ["قيمة الإهلاك",               _fmt(data.get("depreciation"))],
        ["قيمة الأرض",                 _fmt(data.get("land_value"))],
    ]
    if profile_key == "professional_template":
        rows.insert(1, ["تكلفة الاستبدال (Reproduction)",
                        _fmt(data.get("reproduction_cost"))])
        rows.append(["العمر الفعلي / الاقتصادي",
                     _fmt(data.get("age_ratio"))])
    draw_table(pdf, headers, rows, font_family=font_family, theme=th)

    draw_label_value_row(
        pdf, "مؤشر القيمة بأسلوب التكلفة",
        _fmt(data.get("cost_value_indication")),
        font_family=font_family, theme=th,
    )
    pdf.ln(_SECTION_GAP)
    draw_divider(pdf, theme=th)


# ── Income Approach ───────────────────────────────────────────────────────────

def render_income_approach(
    pdf: FPDF,
    data: Mapping[str, Any],
    *,
    profile_key: str = "legacy",
    font_family: str = "Cairo",
    theme: PDFTheme = DEFAULT,
) -> None:
    """Render the income approach block (gross → NOI → cap rate → value)."""
    th = theme
    draw_banner(pdf, "أسلوب الدخل", font_family=font_family, theme=th)

    draw_section_header(pdf, "تحليل الدخل", font_family=font_family, theme=th)
    headers = ["البند", "القيمة"]
    rows: list[list[str]] = [
        ["الدخل الإجمالي السنوي",        _fmt(data.get("gross_income"))],
        ["نسبة الإشغال الشاغر",           _fmt(data.get("vacancy_pct"))],
        ["المصروفات التشغيلية",           _fmt(data.get("opex"))],
        ["صافي الدخل التشغيلي (NOI)",    _fmt(data.get("noi"))],
        ["معدل الرسملة (Cap Rate)",       _fmt(data.get("cap_rate"))],
    ]
    if profile_key == "professional_template":
        rows.append(["معدل الخصم (DCF)",    _fmt(data.get("discount_rate"))])
        rows.append(["معدل النمو (Gordon)", _fmt(data.get("growth_rate"))])
    draw_table(pdf, headers, rows, font_family=font_family, theme=th)

    draw_label_value_row(
        pdf, "مؤشر القيمة بأسلوب الدخل",
        _fmt(data.get("income_value_indication")),
        font_family=font_family, theme=th,
    )
    pdf.ln(_SECTION_GAP)
    draw_divider(pdf, theme=th)


# ── Reconciliation ────────────────────────────────────────────────────────────

def render_reconciliation(
    pdf: FPDF,
    data: Mapping[str, Any],
    *,
    profile_key: str = "legacy",
    font_family: str = "Cairo",
    theme: PDFTheme = DEFAULT,
) -> None:
    """Render the reconciliation block (weights table → final value)."""
    th = theme
    draw_banner(pdf, "التوفيق بين المناهج", font_family=font_family, theme=th)

    draw_section_header(pdf, "أوزان المناهج", font_family=font_family, theme=th)
    weights = data.get("weights") or {}
    indications = data.get("indications") or {}
    headers = ["المنهج", "مؤشر القيمة", "الوزن"]
    rows = [
        ["مقارنة البيوع", _fmt(indications.get("sales")),  _fmt(weights.get("sales"))],
        ["التكلفة",       _fmt(indications.get("cost")),   _fmt(weights.get("cost"))],
        ["الدخل",         _fmt(indications.get("income")), _fmt(weights.get("income"))],
    ]
    draw_table(pdf, headers, rows, font_family=font_family, theme=th)

    draw_section_header(pdf, "القيمة النهائية", font_family=font_family, theme=th)
    draw_label_value_row(
        pdf, "القيمة السوقية النهائية المقدّرة",
        _fmt(data.get("final_value")),
        font_family=font_family, theme=th,
    )
    if data.get("final_value_words"):
        draw_label_value_row(
            pdf, "القيمة بالحروف",
            str(data["final_value_words"]),
            font_family=font_family, theme=th,
        )
    if profile_key == "professional_template" and data.get("confidence_interval"):
        draw_label_value_row(
            pdf, "نطاق الثقة",
            str(data["confidence_interval"]),
            font_family=font_family, theme=th,
        )


# ── Internal Helpers ──────────────────────────────────────────────────────────

def _fmt(value: Any) -> str:
    """Format a value for display — thousands separator for numbers."""
    if value in (None, ""):
        return "—"
    if isinstance(value, (int, float)):
        return f"{value:,.0f}" if value == int(value) else f"{value:,.2f}"
    return str(value)
