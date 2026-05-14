"""
Certification Section — appraiser certification, assumptions, limiting conditions.

Text-only section composed entirely from pdf_components primitives.
Profile-aware: 'professional_template' renders an extended IVS/USPAP
compliance statement; 'legacy' and 'detailed' render the standard block.

This module is independent of sheets/certification_sheet.py — they share
only the DTO shape (appraiser / property_info mappings).
"""

from __future__ import annotations

from typing import Any, Mapping

from fpdf import FPDF

from ..pdf_arabic import prepare_text
from ..pdf_components import (
    draw_banner,
    draw_divider,
    draw_label_value_row,
    draw_section_header,
)
from ..pdf_theme import DEFAULT, PDFTheme

# ── Layout helpers (supplement frozen PDFTheme) ───────────────────────────────

_A4_W: float = 210.0
_PARA_GAP: float = 2.0
_SECTION_GAP: float = 4.0


def _cw(theme: PDFTheme) -> float:
    return _A4_W - theme.margin_left - theme.margin_right


# ── Valid profile keys ────────────────────────────────────────────────────────

_VALID_PROFILES: frozenset[str] = frozenset({"legacy", "detailed", "professional_template"})

# ── Standard Arabic Text Blocks (original boilerplate) ───────────────────────

_CERT_STATEMENT = (
    "يشهد المُقَيِّم بأن البيانات والوقائع الواردة في هذا التقرير صحيحة "
    "على حد علمه واعتقاده، وأن التحليلات والآراء والنتائج تمت دون تحيّز، "
    "وأنه ليس للمُقَيِّم أي مصلحة حالية أو مستقبلية في العقار محل التقييم."
)

_LIMITING_CONDITIONS = (
    "تم إعداد هذا التقرير بناءً على المعلومات المتاحة وقت المعاينة، "
    "ويُفترض صحة المستندات والبيانات المقدمة من العميل. "
    "لا يتحمل المُقَيِّم مسؤولية أي عيوب خفية غير ظاهرة بالمعاينة، "
    "ولا يُعد هذا التقرير مسحاً قانونياً أو هندسياً للعقار."
)

_ASSUMPTIONS = (
    "يُفترض أن العقار خالٍ من النزاعات القانونية وأن سند الملكية سليم، "
    "وأن العقار مستوفٍ لاشتراطات البناء والتراخيص السارية، "
    "وأن القيمة المقدّرة تعكس ظروف السوق في تاريخ التقييم."
)

_IVS_COMPLIANCE = (
    "أُعد هذا التقرير وفقاً لمعايير التقييم الدولية (IVS) "
    "والمبادئ المهنية المعتمدة لأعمال التقييم العقاري."
)

_USPAP_EXTENDED = (
    "كما يلتزم هذا التقرير بالمعايير الموحدة لممارسات التقييم المهني (USPAP)، "
    "بما يشمل قواعد الإفصاح والموضوعية والكفاءة المهنية، "
    "ويحتفظ المُقَيِّم بملف عمل موثّق يدعم النتائج الواردة فيه."
)


# ── Public API ────────────────────────────────────────────────────────────────

def render_certification(
    pdf: FPDF,
    *,
    appraiser: Mapping[str, Any],
    property_info: Mapping[str, Any] | None = None,
    profile_key: str = "legacy",
    font_family: str = "Cairo",
    theme: PDFTheme = DEFAULT,
) -> None:
    """
    Render the appraiser certification section onto the current PDF page.

    Args:
        pdf: An FPDF instance with at least one page added.
        appraiser: Mapping with keys 'name', 'license', 'date', 'title',
                   'firm'. Missing keys render as '—'.
        property_info: Optional mapping; if provided, the property address
                       is shown in the header block.
        profile_key: 'legacy' / 'detailed' / 'professional_template'.
                     'professional_template' adds the extended USPAP block.
        font_family: Registered font family ('Cairo' or 'Helvetica').
        theme: PDFTheme instance (defaults to DEFAULT).

    Raises:
        ValueError: If profile_key is not one of the three valid values.

    Advances the PDF cursor; never calls pdf.output().
    """
    if profile_key not in _VALID_PROFILES:
        raise ValueError(
            f"Unknown profile_key {profile_key!r}. "
            f"Valid: {sorted(_VALID_PROFILES)}"
        )

    th = theme

    # ── Title banner ─────────────────────────────────────────────────
    draw_banner(
        pdf, "شهادة المُقَيِّم والافتراضات",
        font_family=font_family, theme=th,
    )

    # ── Appraiser identity block ──────────────────────────────────────
    draw_section_header(pdf, "بيانات المُقَيِّم", font_family=font_family, theme=th)
    _row(pdf, "اسم المُقَيِّم",  appraiser.get("name"),    font_family, th)
    _row(pdf, "الصفة / المسمى", appraiser.get("title"),   font_family, th)
    _row(pdf, "جهة العمل",      appraiser.get("firm"),    font_family, th)
    _row(pdf, "رقم الترخيص",   appraiser.get("license"), font_family, th)
    _row(pdf, "تاريخ التقرير", appraiser.get("date"),    font_family, th)

    if property_info:
        _row(pdf, "العقار محل التقييم", property_info.get("address"), font_family, th)

    pdf.ln(_PARA_GAP)
    draw_divider(pdf, theme=th)

    # ── Certification statement ───────────────────────────────────────
    draw_section_header(pdf, "بيان الشهادة", font_family=font_family, theme=th)
    _paragraph(pdf, _CERT_STATEMENT, font_family, th)

    # ── Limiting conditions ───────────────────────────────────────────
    draw_section_header(pdf, "الشروط المُقيِّدة", font_family=font_family, theme=th)
    _paragraph(pdf, _LIMITING_CONDITIONS, font_family, th)

    # ── Assumptions ───────────────────────────────────────────────────
    draw_section_header(pdf, "الافتراضات", font_family=font_family, theme=th)
    _paragraph(pdf, _ASSUMPTIONS, font_family, th)

    # ── Compliance ────────────────────────────────────────────────────
    draw_section_header(pdf, "الالتزام بالمعايير", font_family=font_family, theme=th)
    _paragraph(pdf, _IVS_COMPLIANCE, font_family, th)
    if profile_key == "professional_template":
        _paragraph(pdf, _USPAP_EXTENDED, font_family, th)

    # ── Signature line ────────────────────────────────────────────────
    pdf.ln(_SECTION_GAP)
    draw_divider(pdf, theme=th)
    _signature_block(pdf, appraiser, font_family, th)


# ── Internal Helpers ──────────────────────────────────────────────────────────

def _row(
    pdf: FPDF, label: str, value: Any, font_family: str, theme: PDFTheme,
) -> None:
    """Draw a label/value row, substituting '—' for missing values."""
    display = str(value) if value not in (None, "") else "—"
    draw_label_value_row(pdf, label, display, font_family=font_family, theme=theme)


def _paragraph(
    pdf: FPDF, text: str, font_family: str, theme: PDFTheme,
) -> None:
    """Draw a right-aligned RTL paragraph via multi_cell."""
    th = theme
    pdf.set_font(font_family, "", th.size_body)
    pdf.set_text_color(*th.ink)
    pdf.set_x(th.margin_left)
    pdf.multi_cell(
        _cw(th),
        th.row_h,
        prepare_text(text),
        align="R",
    )
    pdf.ln(_PARA_GAP)


def _signature_block(
    pdf: FPDF, appraiser: Mapping[str, Any], font_family: str, theme: PDFTheme,
) -> None:
    """Draw the signature + name + date footer block."""
    th = theme
    half = _cw(th) / 2

    pdf.set_font(font_family, "B", th.size_label)
    pdf.set_text_color(*th.navy)

    pdf.set_x(th.margin_left)
    pdf.cell(half, th.row_h + 2, prepare_text("التوقيع: ____________________"), align="R")
    pdf.cell(half, th.row_h + 2,
             prepare_text(f"التاريخ: {appraiser.get('date') or '—'}"), align="R")
    pdf.ln(th.row_h + 4)

    pdf.set_x(th.margin_left)
    pdf.cell(
        _cw(th), th.row_h,
        prepare_text(f"المُقَيِّم: {appraiser.get('name') or '—'}"),
        align="R",
    )
    pdf.ln(th.row_h)
    pdf.set_text_color(*th.ink)
