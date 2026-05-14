#!/usr/bin/env python3
"""Standalone tests for cost_income_reconciliation_pdf — pytest or direct."""

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
from core_engine.reports.pdf.sections.cost_income_reconciliation_pdf import (
    render_cost_approach,
    render_cost_income_reconciliation,
    render_income_approach,
    render_reconciliation,
)


def _new_pdf():
    doc = FPDF(orientation="P", unit="mm", format="A4")
    doc.set_auto_page_break(auto=True, margin=18)
    fam = register_fonts(doc)
    doc.add_page()
    return doc, fam


_COST = {
    "rcn": 1_800_000, "depreciation_pct": "15%", "depreciation": 270_000,
    "land_value": 900_000, "cost_value_indication": 2_430_000,
    "reproduction_cost": 1_950_000, "age_ratio": "12/60",
}
_INCOME = {
    "gross_income": 240_000, "vacancy_pct": "8%", "opex": 60_000,
    "noi": 160_800, "cap_rate": "6.5%", "income_value_indication": 2_473_846,
    "discount_rate": "9%", "growth_rate": "3%",
}
_RECON = {
    "weights": {"sales": "50%", "cost": "20%", "income": "30%"},
    "indications": {"sales": 2_500_000, "cost": 2_430_000, "income": 2_473_846},
    "final_value": 2_478_153,
    "final_value_words": "مليونان وأربعمائة وثمانية وسبعون ألف جنيه",
    "confidence_interval": "2.40M – 2.55M",
}


def test_cost_approach_advances_cursor():
    doc, fam = _new_pdf()
    y0 = doc.get_y()
    render_cost_approach(doc, _COST, font_family=fam)
    assert doc.get_y() > y0


def test_income_approach_advances_cursor():
    doc, fam = _new_pdf()
    y0 = doc.get_y()
    render_income_approach(doc, _INCOME, font_family=fam)
    assert doc.get_y() > y0


def test_reconciliation_advances_cursor():
    doc, fam = _new_pdf()
    y0 = doc.get_y()
    render_reconciliation(doc, _RECON, font_family=fam)
    assert doc.get_y() > y0


def test_orchestrator_all_three():
    doc, fam = _new_pdf()
    render_cost_income_reconciliation(
        doc, cost_approach=_COST, income_approach=_INCOME, reconciliation=_RECON,
        font_family=fam,
    )
    out = doc.output()
    assert bytes(out[:4]) == b"%PDF" and len(out) > 2000


def test_orchestrator_invalid_profile_raises():
    doc, fam = _new_pdf()
    with pytest.raises(ValueError, match="Unknown profile_key"):
        render_cost_income_reconciliation(doc, cost_approach=_COST,
                                          profile_key="bad", font_family=fam)


def test_orchestrator_none_approaches_noop():
    doc, fam = _new_pdf()
    render_cost_income_reconciliation(doc, font_family=fam)
    assert bytes(doc.output()[:4]) == b"%PDF"


def test_empty_dicts_no_crash():
    doc, fam = _new_pdf()
    render_cost_income_reconciliation(
        doc, cost_approach={}, income_approach={}, reconciliation={}, font_family=fam,
    )
    assert bytes(doc.output()[:4]) == b"%PDF"


def test_all_profiles_render():
    for p in ("legacy", "detailed", "professional_template"):
        doc, fam = _new_pdf()
        render_cost_income_reconciliation(
            doc, cost_approach=_COST, income_approach=_INCOME, reconciliation=_RECON,
            profile_key=p, font_family=fam,
        )
        assert bytes(doc.output()[:4]) == b"%PDF"


if __name__ == "__main__":
    print("Run via: pytest tests/test_pdf_cost_income_reconciliation.py -v")
