"""Tests for core_engine.valuation_engines.composite_engine."""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import pytest

# ── sys.path setup ────────────────────────────────────────────────────────────
_CORE = Path(__file__).resolve().parents[1]   # …/core_engine/
_ROOT = _CORE.parent                          # project root
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from valuation_engines.composite_engine import (  # noqa: E402
    ASSET_TYPES,
    CompositeEngine,
    CompositeEngineError,
    ComponentValuation,
)


@pytest.fixture
def engine():
    return CompositeEngine(default_rate_per_sqm=1000.0)


def _component(asset_type, spec, *, cid=1, area=100.0, name="test"):
    return {
        "id": cid,
        "name": name,
        "asset_type": asset_type,
        "area_sqm": area,
        "specific_attributes": spec,
    }


# ── Registry ─────────────────────────────────────────────────────────

class TestAssetTypeRegistry:
    def test_has_15_types(self):
        assert len(ASSET_TYPES) == 15

    def test_new_airport_seaport_type_present(self):
        assert "المطارات والموانئ" in ASSET_TYPES

    def test_airport_seaport_attributes(self):
        attrs = ASSET_TYPES["المطارات والموانئ"]
        assert "facility_subtype" in attrs
        assert "annual_throughput" in attrs
        assert "berth_or_runway_count" in attrs
        assert "concession_years_remaining" in attrs

    def test_all_14_original_types_preserved(self):
        for t in [
            "وحدة سكنية (شقة / فيلا)",
            "عقار كامل (عمارة / مجمع سكني)",
            "سكني / تجاري / إداري (مباني قائمة)",
            "أرض فضاء (مطورة / خام)",
            "صناعي / مستودع / لوجستي",
            "أرض زراعية",
            "فنادق ومنتجعات سياحية",
            "تجزئة (محلات / مولات)",
            "أصول متخصصة: مستشفيات ومراكز طبية",
            "أصول متخصصة: مدارس ومرافق تعليمية",
            "أصول عقارية مرتبطة بأصول معنوية",
            "المصالح والملكيات الجزئية (Partial Interests)",
            "مناجم وآبار (بترول / غاز/ مياه / ذهب)",
            "استثمارات تحت الإنشاء (Investments Under Construction)",
        ]:
            assert t in ASSET_TYPES, f"original type missing: {t}"


# ── Validation ───────────────────────────────────────────────────────

class TestValidation:
    def test_unknown_asset_type_raises(self, engine):
        with pytest.raises(CompositeEngineError, match="Unknown asset_type"):
            engine.value_component(_component("نوع غير موجود", {}))

    def test_missing_attribute_raises(self, engine):
        with pytest.raises(CompositeEngineError, match="missing required attribute"):
            engine.value_component(_component(
                "وحدة سكنية (شقة / فيلا)", {"bedrooms_count": 3},  # floor_number missing
            ))

    def test_wrong_attribute_type_raises(self, engine):
        with pytest.raises(CompositeEngineError, match="must be"):
            engine.value_component(_component(
                "وحدة سكنية (شقة / فيلا)",
                {"bedrooms_count": "three", "floor_number": 2},
            ))

    def test_non_numeric_area_raises(self, engine):
        c = _component("أرض زراعية", {"water_source": "نيل", "crop_type": "قمح"})
        c["area_sqm"] = "big"
        with pytest.raises(CompositeEngineError, match="area_sqm"):
            engine.value_component(c)

    def test_int_accepted_where_float_expected(self, engine):
        # frontage_meters expects float; passing int should be accepted (lenient)
        r = engine.value_component(_component(
            "أرض فضاء (مطورة / خام)",
            {"zoning_type": "سكني", "frontage_meters": 20},  # int, not float
        ))
        assert isinstance(r, ComponentValuation)


# ── Baseline calculation ─────────────────────────────────────────────

class TestBaseline:
    def test_area_rate_default(self, engine):
        r = engine.value_component(_component(
            "وحدة سكنية (شقة / فيلا)",
            {"bedrooms_count": 3, "floor_number": 2},
            area=100.0,
        ))
        assert r.baseline_value == 100000.0
        assert r.method == "area_rate"

    def test_per_component_rate_override(self, engine):
        c = _component(
            "وحدة سكنية (شقة / فيلا)",
            {"bedrooms_count": 3, "floor_number": 2},
            area=100.0,
        )
        c["base_rate_per_sqm"] = 5000.0
        r = engine.value_component(c)
        assert r.baseline_value == 500000.0

    def test_hotel_revpar_method(self, engine):
        r = engine.value_component(_component(
            "فنادق ومنتجعات سياحية",
            {
                "room_count": 150,
                "average_daily_rate_adr": 450.0,
                "occupancy_rate_percent": 75.0,
                "revpar": 337.5,
            },
        ))
        assert r.baseline_value == round(337.5 * 150 * 365, 2)
        assert r.method == "income_revpar_baseline"
        assert any("RevPAR baseline" in n for n in r.notes)

    def test_airport_seaport_has_deferral_note(self, engine):
        r = engine.value_component(_component(
            "المطارات والموانئ",
            {
                "facility_subtype": "ميناء",
                "annual_throughput": 1_000_000.0,
                "berth_or_runway_count": 8,
                "concession_years_remaining": 25.0,
            },
        ))
        assert r.method == "infrastructure_baseline"
        assert any("concession" in n.lower() for n in r.notes)
        assert any("د. عبد الرؤوف" in n for n in r.notes)

    def test_goodwill_added(self, engine):
        r = engine.value_component(_component(
            "أصول عقارية مرتبطة بأصول معنوية",
            {"goodwill_value": 50000.0},
            area=100.0,
        ))
        assert r.baseline_value == 150000.0
        assert r.method == "area_rate_plus_goodwill"

    def test_partial_interest_share(self, engine):
        r = engine.value_component(_component(
            "المصالح والملكيات الجزئية (Partial Interests)",
            {"ownership_share_percent": 40.0},
            area=100.0,
        ))
        assert r.baseline_value == 40000.0
        assert r.method == "area_rate_partial_share"

    def test_under_construction_completion_weighted(self, engine):
        r = engine.value_component(_component(
            "استثمارات تحت الإنشاء (Investments Under Construction)",
            {"completion_percent": 60.0, "estimated_cost_to_complete": 200000.0},
            area=100.0,
        ))
        assert r.baseline_value == 60000.0
        assert r.method == "area_rate_completion_weighted"

    def test_mine_has_deferral_note(self, engine):
        r = engine.value_component(_component(
            "مناجم وآبار (بترول / غاز/ مياه / ذهب)",
            {
                "proven_reserves_volume": 1e6,
                "daily_production_rate": 500.0,
                "extraction_cost_per_unit": 12.0,
            },
        ))
        assert any("Reserve-depletion" in n or "placeholder" in n for n in r.notes)


# ── value_all ────────────────────────────────────────────────────────

class TestValueAll:
    def test_empty_list(self, engine):
        assert engine.value_all([]) == []

    def test_order_preserved(self, engine):
        comps = [
            _component(
                "وحدة سكنية (شقة / فيلا)",
                {"bedrooms_count": 2, "floor_number": 1},
                cid="a",
            ),
            _component(
                "أرض زراعية",
                {"water_source": "بئر", "crop_type": "نخيل"},
                cid="b",
            ),
        ]
        results = engine.value_all(comps)
        assert [r.component_id for r in results] == ["a", "b"]

    def test_mixed_types_all_valued(self, engine):
        comps = [
            _component(
                "وحدة سكنية (شقة / فيلا)",
                {"bedrooms_count": 2, "floor_number": 1},
                cid=1,
            ),
            _component(
                "المطارات والموانئ",
                {
                    "facility_subtype": "مطار",
                    "annual_throughput": 5e6,
                    "berth_or_runway_count": 2,
                    "concession_years_remaining": 30.0,
                },
                cid=2,
            ),
            _component(
                "فنادق ومنتجعات سياحية",
                {
                    "room_count": 100,
                    "average_daily_rate_adr": 300.0,
                    "occupancy_rate_percent": 70.0,
                    "revpar": 210.0,
                },
                cid=3,
            ),
        ]
        results = engine.value_all(comps)
        assert len(results) == 3
        assert all(r.baseline_value > 0 for r in results)

    def test_one_bad_component_raises(self, engine):
        comps = [
            _component(
                "وحدة سكنية (شقة / فيلا)",
                {"bedrooms_count": 2, "floor_number": 1},
                cid=1,
            ),
            _component("نوع خاطئ", {}, cid=2),
        ]
        with pytest.raises(CompositeEngineError):
            engine.value_all(comps)


# ── Result dataclass ─────────────────────────────────────────────────

class TestComponentValuation:
    def test_is_frozen(self, engine):
        r = engine.value_component(_component(
            "وحدة سكنية (شقة / فيلا)",
            {"bedrooms_count": 3, "floor_number": 2},
        ))
        with pytest.raises(dataclasses.FrozenInstanceError):
            r.baseline_value = 999  # type: ignore[misc]

    def test_notes_is_tuple(self, engine):
        r = engine.value_component(_component(
            "المطارات والموانئ",
            {
                "facility_subtype": "ميناء",
                "annual_throughput": 1e6,
                "berth_or_runway_count": 5,
                "concession_years_remaining": 20.0,
            },
        ))
        assert isinstance(r.notes, tuple)
