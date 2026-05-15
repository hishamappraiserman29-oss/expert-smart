"""
Report profiles registry for Expert Smart.

Central registry for report styles, metadata, and sheet-exclusion logic.
Mirrors the _LEGACY_EXCLUDED_SHEETS constant that excel_builder.py now sources
from here instead of defining inline.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ── Advanced-analytics sheets excluded from the legacy export ─────────────────
# Match is performed on sheet_name.strip().lower() so both Arabic variants
# (ي / ى endings, hamza variants) and English names are covered.
_LEGACY_EXCLUDED_SHEETS: frozenset[str] = frozenset({
    # Arabic names (both spelling variants)
    "التحليل المكاني",  "التحليل المكانى",
    "الإنحدار المتعدد", "الانحدار المتعدد",
    "الخيارات الحقيقية",
    "لوحة القيادة التنفيذية",
    "الشبكات العصبية",
    "السلاسل الزمنية",
    "إستخبارات السوق",  "استخبارات السوق",
    # English names
    "spatial analysis",
    "multiple regression",
    "real options",
    "executive dashboard",
    "neural networks",
    "time series",
    "market intelligence",
})


# ── Profile dataclass ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ReportProfile:
    style: str
    label_ar: str
    label_en: str
    include_advanced_analytics: bool = False
    exclude_advanced_sheets: bool = False
    include_sales_adjustment_matrix: bool = False
    uses_template: bool = False
    template_path: Optional[str] = None
    default_output_ext: str = ".xlsx"


# ── Registry ───────────────────────────────────────────────────────────────────

_PROFILES: dict[str, ReportProfile] = {
    "legacy": ReportProfile(
        style="legacy",
        label_ar="التقرير التقليدي",
        label_en="Legacy Report",
        include_advanced_analytics=False,
        exclude_advanced_sheets=True,
        include_sales_adjustment_matrix=True,
        default_output_ext=".xlsx",
    ),
    "detailed": ReportProfile(
        style="detailed",
        label_ar="التقرير التفصيلي",
        label_en="Detailed Report",
        include_advanced_analytics=True,
        exclude_advanced_sheets=False,
        include_sales_adjustment_matrix=True,
        default_output_ext=".xlsx",
    ),
    "professional_template": ReportProfile(
        style="professional_template",
        label_ar="التقرير الاحترافي بالقالب",
        label_en="Professional Template Report",
        uses_template=True,
        template_path="templates/reports/individual_valuation_professional_template.xlsm",
        exclude_advanced_sheets=False,
        default_output_ext=".xlsm",
    ),
}

_DEFAULT_STYLE = "legacy"


# ── Helper functions ───────────────────────────────────────────────────────────

def normalize_report_style(style: Optional[str]) -> str:
    """Return a valid style key; unknown/missing values default to 'legacy'."""
    if style and style.strip() in _PROFILES:
        return style.strip()
    return _DEFAULT_STYLE


def get_report_profile(style: Optional[str]) -> ReportProfile:
    """Return the ReportProfile for style, defaulting to legacy."""
    return _PROFILES[normalize_report_style(style)]


def is_legacy(style: Optional[str]) -> bool:
    return normalize_report_style(style) == "legacy"


def is_detailed(style: Optional[str]) -> bool:
    return normalize_report_style(style) == "detailed"


def is_professional_template(style: Optional[str]) -> bool:
    return normalize_report_style(style) == "professional_template"


def should_exclude_advanced_sheets(style: Optional[str]) -> bool:
    return get_report_profile(style).exclude_advanced_sheets


def get_legacy_excluded_sheets() -> frozenset[str]:
    """Return the canonical set of advanced-sheet names excluded from legacy."""
    return _LEGACY_EXCLUDED_SHEETS


def normalize_sheet_name(name: str) -> str:
    """Lowercase + strip; used before membership tests."""
    return name.strip().lower()


def is_legacy_excluded_sheet(sheet_name: str) -> bool:
    """Return True if sheet_name (or any keyword it contains) is excluded from legacy.

    Handles prefixed real names like 'ANN — الشبكات العصبية' via substring match.
    """
    normalized = normalize_sheet_name(sheet_name)
    if normalized in _LEGACY_EXCLUDED_SHEETS:
        return True
    return any(keyword in normalized for keyword in _LEGACY_EXCLUDED_SHEETS)
