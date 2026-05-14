#!/usr/bin/env python3
"""Standalone tests for sections/sales_comparison_pdf — pytest or direct."""

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

from core_engine.reports.pdf.pdf_components import register_fonts
from core_engine.reports.pdf.sections.sales_comparison_pdf import render_sales_comparison


def _new_pdf():
    doc = FPDF(orientation="P", unit="mm", format="A4")
    doc.set_auto_page_break(auto=True, margin=18)
    fam = register_fonts(doc)
    doc.add_page()
    return doc, fam


_SUBJECT = {"address": "القاهرة الجديدة", "area": 320, "type": "سكني"}
_COMPS = [
    {"ref": "ع1", "address": "التجمع الخامس", "sale_price": 2_400_000,
     "area": 310, "price_per_sqm": 7_741, "adjustment_pct": "+3%", "adjusted_value": 2_472_000},
    {"ref": "ع2", "address": "الرحاب", "sale_price": 2_600_000,
     "area": 330, "price_per_sqm": 7_878, "adjustment_pct": "-2%", "adjusted_value": 2_548_000},
]


def test_advances_cursor():
    doc, fam = _new_pdf()
    y0 = doc.get_y()
    render_sales_comparison(doc, subject=_SUBJECT, comparables=_COMPS, font_family=fam)
    assert doc.get_y() > y0


def test_valid_pdf():
    doc, fam = _new_pdf()
    render_sales_comparison(doc, subject=_SUBJECT, comparables=_COMPS, font_family=fam)
    out = doc.output()
    assert bytes(out[:4]) == b"%PDF" and len(out) > 1500


def test_invalid_profile_raises():
    doc, fam = _new_pdf()
    with pytest.raises(ValueError, match="Unknown profile_key"):
        render_sales_comparison(doc, subject=_SUBJECT, comparables=_COMPS,
                                profile_key="bad", font_family=fam)


def test_empty_comparables_no_crash():
    doc, fam = _new_pdf()
    render_sales_comparison(doc, subject=_SUBJECT, comparables=[], font_family=fam)
    assert bytes(doc.output()[:4]) == b"%PDF"


def test_partial_comp_keys_no_crash():
    doc, fam = _new_pdf()
    render_sales_comparison(doc, subject=_SUBJECT, comparables=[{"ref": "ع1"}], font_family=fam)
    assert bytes(doc.output()[:4]) == b"%PDF"


def test_all_profiles_render():
    for p in ("legacy", "detailed", "professional_template"):
        doc, fam = _new_pdf()
        render_sales_comparison(doc, subject=_SUBJECT, comparables=_COMPS,
                                profile_key=p, font_family=fam)
        assert bytes(doc.output()[:4]) == b"%PDF"


if __name__ == "__main__":
    print("Run via: pytest tests/test_pdf_sales_comparison.py -v")
