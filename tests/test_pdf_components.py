#!/usr/bin/env python3
"""Standalone smoke tests for pdf_components — run directly or via pytest."""

import sys
import io
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_ROOT = Path(__file__).resolve().parent.parent
_CORE = _ROOT / "core_engine"
for _p in (str(_ROOT), str(_CORE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest
from fpdf import FPDF

from core_engine.reports.pdf import pdf_components as C
from core_engine.reports.pdf.pdf_theme import DEFAULT


@pytest.fixture
def pdf():
    doc = FPDF(orientation="P", unit="mm", format="A4")
    doc.set_auto_page_break(auto=False)
    family = C.register_fonts(doc)
    doc.add_page()
    doc._test_family = family
    return doc


def test_register_fonts_returns_cairo():
    doc = FPDF()
    assert C.register_fonts(doc) == "Cairo"
    print("✓ test_register_fonts_returns_cairo")


def test_register_fonts_idempotent():
    doc = FPDF()
    assert C.register_fonts(doc) == C.register_fonts(doc) == "Cairo"
    print("✓ test_register_fonts_idempotent")


def test_draw_banner_advances_cursor(pdf):
    y0 = pdf.get_y()
    C.draw_banner(pdf, "تقرير التقييم العقاري", font_family=pdf._test_family)
    assert pdf.get_y() > y0
    print("✓ test_draw_banner_advances_cursor")


def test_draw_section_header_advances_cursor(pdf):
    y0 = pdf.get_y()
    C.draw_section_header(pdf, "بيانات العقار", font_family=pdf._test_family)
    assert pdf.get_y() > y0
    print("✓ test_draw_section_header_advances_cursor")


def test_draw_divider_advances_cursor(pdf):
    y0 = pdf.get_y()
    C.draw_divider(pdf)
    assert pdf.get_y() > y0
    print("✓ test_draw_divider_advances_cursor")


def test_draw_kpi_card_does_not_move_cursor(pdf):
    y0 = pdf.get_y()
    C.draw_kpi_card(pdf, label="القيمة", value="2,500,000",
                    x=20, y=50, width=50, font_family=pdf._test_family)
    assert pdf.get_y() == y0
    print("✓ test_draw_kpi_card_does_not_move_cursor")


def test_draw_kpi_row_advances_cursor(pdf):
    y0 = pdf.get_y()
    C.draw_kpi_row(pdf, [{"label": "A", "value": "1"}, {"label": "B", "value": "2"}],
                   font_family=pdf._test_family)
    assert pdf.get_y() > y0
    print("✓ test_draw_kpi_row_advances_cursor")


def test_draw_kpi_row_empty_is_noop(pdf):
    y0 = pdf.get_y()
    C.draw_kpi_row(pdf, [], font_family=pdf._test_family)
    assert pdf.get_y() == y0
    print("✓ test_draw_kpi_row_empty_is_noop")


def test_draw_table_advances_cursor(pdf):
    y0 = pdf.get_y()
    C.draw_table(pdf, ["A", "B"], [["1", "2"]], font_family=pdf._test_family)
    assert pdf.get_y() > y0
    print("✓ test_draw_table_advances_cursor")


def test_draw_label_value_row_advances_cursor(pdf):
    y0 = pdf.get_y()
    C.draw_label_value_row(pdf, "العنوان", "القاهرة", font_family=pdf._test_family)
    assert pdf.get_y() > y0
    print("✓ test_draw_label_value_row_advances_cursor")


def test_draw_footer_does_not_raise(pdf):
    C.draw_footer(pdf, "EXPERT_SMART", font_family=pdf._test_family)
    print("✓ test_draw_footer_does_not_raise")


def test_full_page_outputs_valid_pdf(pdf):
    fam = pdf._test_family
    C.draw_banner(pdf, "تقرير التقييم", font_family=fam)
    C.draw_section_header(pdf, "بيانات", font_family=fam)
    C.draw_kpi_row(pdf, [{"label": "القيمة", "value": "2.5M"}], font_family=fam)
    C.draw_table(pdf, ["أ", "ب"], [["x", "y"]], font_family=fam)
    C.draw_footer(pdf, "EXPERT_SMART", font_family=fam)
    out = pdf.output()
    assert isinstance(out, (bytes, bytearray))
    assert len(out) > 1000
    assert bytes(out[:4]) == b"%PDF"
    print(f"✓ test_full_page_outputs_valid_pdf ({len(out):,} bytes)")


if __name__ == "__main__":
    import sys as _sys
    _doc = FPDF(orientation="P", unit="mm", format="A4")
    _doc.set_auto_page_break(auto=False)
    _fam = C.register_fonts(_doc)
    _doc.add_page()
    _doc._test_family = _fam

    test_register_fonts_returns_cairo()
    test_register_fonts_idempotent()
    test_draw_banner_advances_cursor(_doc)
    print("  (re-init pdf for remaining tests...)")
    print("\n✅ بعض الاختبارات نجحت — لتشغيل الكل: pytest tests/test_pdf_components.py")
