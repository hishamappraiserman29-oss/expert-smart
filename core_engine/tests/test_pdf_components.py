"""
test_pdf_components.py — Wave 7a.2 reusable PDF drawing components (16 tests)

Tests:
  register_fonts (2): returns Cairo, idempotent second call
  draw_banner (4): cursor advances, section header advances,
                   divider advances, Latin text works
  draw_kpi_card (3): absolute positioning doesn't move global cursor,
                     kpi_row advances cursor, empty kpi_row is noop
  draw_table (4): table advances cursor, empty rows ok,
                  custom col_widths ok, label_value_row advances
  draw_footer (2): no exception with text, no exception empty
  integration (1): full page → valid %PDF bytes > 1KB
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_CORE))
os.chdir(str(_CORE))

import pytest
from fpdf import FPDF

from reports.pdf import pdf_components as C
from reports.pdf.pdf_theme import DEFAULT


# ── Shared fixture ────────────────────────────────────────────────────────────

@pytest.fixture
def pdf():
    """Fresh FPDF instance with Cairo registered and first page open."""
    doc = FPDF(orientation="P", unit="mm", format="A4")
    doc.set_auto_page_break(auto=False)
    family = C.register_fonts(doc)
    doc.add_page()
    doc._test_family = family  # stash for tests
    return doc


# ── register_fonts ────────────────────────────────────────────────────────────

class TestRegisterFonts:
    def test_returns_cairo_when_bundled(self):
        doc = FPDF()
        family = C.register_fonts(doc)
        assert family == "Cairo"

    def test_idempotent_second_call(self):
        doc = FPDF()
        f1 = C.register_fonts(doc)
        f2 = C.register_fonts(doc)
        assert f1 == f2 == "Cairo"


# ── Banners & Headers ─────────────────────────────────────────────────────────

class TestBanners:
    def test_draw_banner_advances_cursor(self, pdf):
        y_before = pdf.get_y()
        C.draw_banner(pdf, "تقرير التقييم العقاري", font_family=pdf._test_family)
        y_after = pdf.get_y()
        assert y_after > y_before
        assert y_after >= y_before + DEFAULT.banner_h

    def test_draw_section_header_advances_cursor(self, pdf):
        y_before = pdf.get_y()
        C.draw_section_header(pdf, "بيانات العقار", font_family=pdf._test_family)
        assert pdf.get_y() > y_before

    def test_draw_divider_advances_cursor(self, pdf):
        y_before = pdf.get_y()
        C.draw_divider(pdf)
        assert pdf.get_y() > y_before

    def test_banner_with_latin_text_does_not_raise(self, pdf):
        C.draw_banner(pdf, "Valuation Report", font_family=pdf._test_family)
        assert pdf.get_y() > DEFAULT.margin_top


# ── KPI Cards ─────────────────────────────────────────────────────────────────

class TestKpiCards:
    def test_draw_kpi_card_does_not_advance_global_cursor(self, pdf):
        y_before = pdf.get_y()
        C.draw_kpi_card(
            pdf, label="القيمة السوقية", value="2,500,000",
            x=20, y=50, width=50, font_family=pdf._test_family,
        )
        assert pdf.get_y() == y_before

    def test_draw_kpi_row_advances_cursor(self, pdf):
        y_before = pdf.get_y()
        C.draw_kpi_row(
            pdf,
            [
                {"label": "القيمة", "value": "2.5M"},
                {"label": "المساحة", "value": "320 م²"},
                {"label": "السعر/م²", "value": "7,800"},
            ],
            font_family=pdf._test_family,
        )
        assert pdf.get_y() > y_before

    def test_draw_kpi_row_empty_is_noop(self, pdf):
        y_before = pdf.get_y()
        C.draw_kpi_row(pdf, [], font_family=pdf._test_family)
        assert pdf.get_y() == y_before


# ── Tables ────────────────────────────────────────────────────────────────────

class TestTables:
    def test_draw_table_advances_cursor(self, pdf):
        y_before = pdf.get_y()
        C.draw_table(
            pdf,
            ["البند", "القيمة"],
            [["المساحة", "320"], ["السعر", "2,500,000"]],
            font_family=pdf._test_family,
        )
        assert pdf.get_y() > y_before

    def test_draw_table_empty_rows_does_not_raise(self, pdf):
        C.draw_table(pdf, ["A", "B"], [], font_family=pdf._test_family)
        assert pdf.get_y() > DEFAULT.margin_top

    def test_draw_table_custom_col_widths(self, pdf):
        C.draw_table(
            pdf, ["البند", "القيمة"], [["x", "y"]],
            col_widths=[60.0, 114.0], font_family=pdf._test_family,
        )
        assert pdf.get_y() > DEFAULT.margin_top

    def test_draw_label_value_row_advances_cursor(self, pdf):
        y_before = pdf.get_y()
        C.draw_label_value_row(
            pdf, "اسم المُقَيِّم", "د. عبد الرؤوف محمد",
            font_family=pdf._test_family,
        )
        assert pdf.get_y() > y_before


# ── Footer ────────────────────────────────────────────────────────────────────

class TestFooter:
    def test_draw_footer_with_text_does_not_raise(self, pdf):
        C.draw_footer(pdf, "EXPERT_SMART", font_family=pdf._test_family)

    def test_draw_footer_empty_text_does_not_raise(self, pdf):
        C.draw_footer(pdf, font_family=pdf._test_family)


# ── Integration ───────────────────────────────────────────────────────────────

class TestIntegration:
    def test_full_page_composition_outputs_valid_pdf(self, pdf):
        """Compose all components → valid %PDF bytes > 1 KB."""
        fam = pdf._test_family
        C.draw_banner(pdf, "تقرير التقييم العقاري", font_family=fam)
        C.draw_section_header(pdf, "المؤشرات الرئيسية", font_family=fam)
        C.draw_kpi_row(pdf, [
            {"label": "القيمة السوقية", "value": "2,500,000"},
            {"label": "المساحة", "value": "320 م²"},
        ], font_family=fam)
        C.draw_section_header(pdf, "بيانات العقار", font_family=fam)
        C.draw_label_value_row(pdf, "العنوان", "القاهرة الجديدة", font_family=fam)
        C.draw_divider(pdf)
        C.draw_table(
            pdf, ["البند", "القيمة"],
            [["نهج المقارنة", "2,400,000"], ["نهج التكلفة", "2,600,000"]],
            font_family=fam,
        )
        C.draw_footer(pdf, "EXPERT_SMART", font_family=fam)

        out = pdf.output()
        assert isinstance(out, (bytes, bytearray))
        assert len(out) > 1000
        assert bytes(out[:4]) == b"%PDF"
