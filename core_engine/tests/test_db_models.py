"""Tests for core_engine/reports/db/models.py — Wave 7c.1."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_CORE))
os.chdir(str(_CORE))

from reports.db.models import ReportRecord  # noqa: E402


_SAMPLE = dict(
    report_id="rpt-001",
    profile_key="legacy",
    status="draft",
    appraiser_name="د. عبد الرؤوف",
    market_value=2_478_153.0,
    created_at="2026-05-15T10:00:00",
    updated_at="2026-05-15T10:00:00",
    data={"valuation_results": {"market_value": 2_478_153.0}},
)


def _make(**overrides) -> ReportRecord:
    return ReportRecord(**{**_SAMPLE, **overrides})


class TestReportRecordStructure:
    def test_M01_can_instantiate(self):
        rec = _make()
        assert rec.report_id == "rpt-001"

    def test_M02_is_frozen(self):
        rec = _make()
        with pytest.raises((AttributeError, TypeError)):
            rec.status = "final"  # type: ignore[misc]

    def test_M03_equality_same_values(self):
        assert _make() == _make()

    def test_M04_inequality_different_id(self):
        assert _make(report_id="a") != _make(report_id="b")

    def test_M05_profile_key_stored(self):
        rec = _make(profile_key="professional")
        assert rec.profile_key == "professional"

    def test_M06_status_stored(self):
        rec = _make(status="final")
        assert rec.status == "final"

    def test_M07_appraiser_name_can_be_none(self):
        rec = _make(appraiser_name=None)
        assert rec.appraiser_name is None

    def test_M08_market_value_can_be_none(self):
        rec = _make(market_value=None)
        assert rec.market_value is None

    def test_M09_data_dict_stored(self):
        payload = {"key": "value", "nested": {"x": 1}}
        rec = _make(data=payload)
        assert rec.data == payload

    def test_M10_created_at_stored(self):
        rec = _make(created_at="2026-01-01T00:00:00")
        assert rec.created_at == "2026-01-01T00:00:00"

    def test_M11_updated_at_stored(self):
        rec = _make(updated_at="2026-06-01T12:00:00")
        assert rec.updated_at == "2026-06-01T12:00:00"

    def test_M12_data_is_not_shared_between_instances(self):
        rec1 = _make(data={"v": 1})
        rec2 = _make(data={"v": 2})
        assert rec1.data != rec2.data

    def test_M13_arabic_strings_preserved(self):
        rec = _make(appraiser_name="محمد أحمد")
        assert rec.appraiser_name == "محمد أحمد"

    def test_M14_market_value_float_precision(self):
        rec = _make(market_value=1_234_567.89)
        assert rec.market_value == pytest.approx(1_234_567.89)

    def test_M15_data_supports_complex_nested_structure(self):
        complex_data = {
            "appraiser": {"name": "Test", "license": "EG-001"},
            "comparables": [{"price": 1000}, {"price": 2000}],
            "valuation_results": {"market_value": 1_500_000, "confidence": "عالية"},
            "flags": None,
        }
        rec = _make(data=complex_data)
        assert rec.data["comparables"][1]["price"] == 2000
        assert rec.data["flags"] is None
