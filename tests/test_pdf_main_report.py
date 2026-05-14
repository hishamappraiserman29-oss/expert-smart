#!/usr/bin/env python3
"""Standalone tests for sections/main_report_pdf — pytest or direct."""

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
from core_engine.reports.pdf.sections.main_report_pdf import render_main_report


def _new_pdf():
    doc = FPDF(orientation="P", unit="mm", format="A4")
    doc.set_auto_page_break(auto=True, margin=18)
    fam = register_fonts(doc)
    doc.add_page()
    return doc, fam


_APPRAISER = {"name": "د. عبد الرؤوف محمد", "license": "EG-2026-00471", "date": "2026-05-14"}
_PROPERTY = {"address": "القاهرة الجديدة", "type": "سكني", "area": 320}
_RESULTS = {"market_value": 2_500_000, "price_per_sqm": 7_812, "confidence": "عالية",
            "value_words": "مليونان وخمسمائة ألف جنيه", "primary_approach": "مقارنة البيوع"}


def test_advances_cursor():
    doc, fam = _new_pdf()
    y0 = doc.get_y()
    render_main_report(doc, appraiser=_APPRAISER, property_info=_PROPERTY,
                       valuation_results=_RESULTS, font_family=fam)
    assert doc.get_y() > y0


def test_valid_pdf():
    doc, fam = _new_pdf()
    render_main_report(doc, appraiser=_APPRAISER, property_info=_PROPERTY,
                       valuation_results=_RESULTS, font_family=fam)
    out = doc.output()
    assert bytes(out[:4]) == b"%PDF" and len(out) > 1500


def test_invalid_profile_raises():
    doc, fam = _new_pdf()
    with pytest.raises(ValueError, match="Unknown profile_key"):
        render_main_report(doc, appraiser=_APPRAISER, property_info=_PROPERTY,
                           valuation_results=_RESULTS, profile_key="bad", font_family=fam)


def test_empty_dicts_no_crash():
    doc, fam = _new_pdf()
    render_main_report(doc, appraiser={}, property_info={}, valuation_results={}, font_family=fam)
    assert bytes(doc.output()[:4]) == b"%PDF"


def test_all_profiles_render():
    for p in ("legacy", "detailed", "professional_template"):
        doc, fam = _new_pdf()
        render_main_report(doc, appraiser=_APPRAISER, property_info=_PROPERTY,
                           valuation_results=_RESULTS, profile_key=p, font_family=fam)
        assert bytes(doc.output()[:4]) == b"%PDF"


if __name__ == "__main__":
    print("Run via: pytest tests/test_pdf_main_report.py -v")
