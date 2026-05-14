#!/usr/bin/env python3
"""Standalone tests for pdf_engine.generate_pdf — pytest or direct."""

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

from core_engine.reports.pdf.pdf_engine import generate_pdf

_DATA = {
    "appraiser": {"name": "د. محمد الخبير", "license": "EG-2026-00471", "date": "2026-05-14"},
    "property_info": {"address": "القاهرة الجديدة", "type": "سكني", "area": 320},
    "valuation_results": {
        "market_value": 2_500_000, "price_per_sqm": 7_812, "confidence": "عالية",
        "value_words": "مليونان وخمسمائة ألف جنيه", "primary_approach": "مقارنة البيوع",
    },
    "certification": {"name": "د. محمد الخبير", "license": "EG-2026-00471", "date": "2026-05-14"},
}


def test_creates_valid_pdf(tmp_path):
    out = tmp_path / "report.pdf"
    result = generate_pdf(profile_key="legacy", data=_DATA, output_path=out)
    assert result == out
    assert out.read_bytes()[:4] == b"%PDF"


def test_invalid_profile_raises(tmp_path):
    with pytest.raises(ValueError, match="Unknown profile_key"):
        generate_pdf(profile_key="bad", data=_DATA, output_path=tmp_path / "x.pdf")


def test_all_profiles(tmp_path):
    for p in ("legacy", "detailed", "professional_template"):
        out = tmp_path / f"{p}.pdf"
        generate_pdf(profile_key=p, data=_DATA, output_path=out)
        assert out.read_bytes()[:4] == b"%PDF"


def test_minimal_data_no_crash(tmp_path):
    out = tmp_path / "minimal.pdf"
    generate_pdf(profile_key="legacy", data={}, output_path=out)
    assert out.read_bytes()[:4] == b"%PDF"


if __name__ == "__main__":
    print("Run via: pytest tests/test_pdf_engine.py -v")
