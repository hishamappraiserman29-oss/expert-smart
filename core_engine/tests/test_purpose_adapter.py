"""Tests for core_engine.adapters.purpose_adapter."""
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

from valuation_engines.composite_engine import ComponentValuation  # noqa: E402
from adapters.purpose_adapter import (  # noqa: E402
    PURPOSE_RULES,
    PurposeComplianceAdapter,
    PurposeAdapterError,
    AdjustedValuation,
)


@pytest.fixture
def adapter():
    return PurposeComplianceAdapter()


def _baseline(value=100000.0, asset_type="وحدة سكنية (شقة / فيلا)"):
    return ComponentValuation(
        component_id=1,
        name="test",
        asset_type=asset_type,
        area_sqm=100.0,
        baseline_value=value,
        method="area_rate",
        notes=(),
    )


# ── Catalog ───────────────────────────────────────────────────────────────────

class TestPurposeCatalog:
    def test_has_14_purposes(self):
        assert len(PURPOSE_RULES) == 14

    def test_market_value_present(self):
        assert "البيع والشراء - القيمة السوقية العادلة (Market Value)" in PURPOSE_RULES

    def test_all_rules_have_multiplier_and_route(self):
        for name, rule in PURPOSE_RULES.items():
            assert "multiplier" in rule, name
            assert "route" in rule, name

    def test_exactly_4_explicit_multiplier_purposes(self):
        explicit = [k for k, v in PURPOSE_RULES.items() if not v.get("deep", False)]
        assert len(explicit) == 4

    def test_exactly_10_deep_route_purposes(self):
        deep = [k for k, v in PURPOSE_RULES.items() if v.get("deep", False)]
        assert len(deep) == 10


# ── Explicit-multiplier purposes ──────────────────────────────────────────────

class TestExplicitMultipliers:
    def test_market_value_1x(self, adapter):
        r = adapter.adapt(
            _baseline(100000.0),
            "البيع والشراء - القيمة السوقية العادلة (Market Value)",
        )
        assert r.multiplier_applied == 1.00
        assert r.adjusted_value == 100000.0
        assert r.deep_route_deferred is False

    def test_financing_0_95x(self, adapter):
        r = adapter.adapt(
            _baseline(100000.0),
            "الرهن والتمويل البنكي - القيمة السوقية لأغراض التمويل (0.95x)",
        )
        assert r.multiplier_applied == 0.95
        assert r.adjusted_value == 95000.0
        assert r.deep_route_deferred is False

    def test_liquidation_0_82x(self, adapter):
        r = adapter.adapt(
            _baseline(100000.0),
            "التصفية الإجبارية - القيمة التصفوية (Liquidation Value x0.82)",
        )
        assert r.multiplier_applied == 0.82
        assert r.adjusted_value == 82000.0
        assert r.deep_route_deferred is False

    def test_insurance_1_08x(self, adapter):
        r = adapter.adapt(
            _baseline(100000.0),
            "التأمين - قيمة إعادة الإنشاء (Reinstatement Value x1.08)",
        )
        assert r.multiplier_applied == 1.08
        assert r.adjusted_value == 108000.0
        assert r.deep_route_deferred is False
        assert any("structure-only" in n for n in r.notes)

    def test_rounding_two_decimal_places(self, adapter):
        r = adapter.adapt(
            _baseline(100001.0),
            "الرهن والتمويل البنكي - القيمة السوقية لأغراض التمويل (0.95x)",
        )
        # 100001 × 0.95 = 95000.95
        assert r.adjusted_value == 95000.95


# ── Complex-route purposes ────────────────────────────────────────────────────

class TestComplexRoutes:
    @pytest.mark.parametrize("purpose", [
        "الاستحواذ والاندماج - القيمة الاستثمارية (Investment Value)",
        "التحليل الاستثماري - IRR / NPV / DCF",
        "تحديد الأجرة - القيمة الإيجارية العادلة (Rental Value)",
        "التقارير المالية والمحاسبية - القيمة العادلة (13 Fair Value - IFRS)",
        "حق الانتفاع - تقييم حقوق المنفعة العقارية (Usufruct Right)",
        "التقييم في حالة عدم اليقين (Valuation Under Uncertainty)",
        "تحليل أعلى وأفضل استغلال (Highest and Best Use Analysis)",
        "التقييم لأغراض الصناديق الاستثمارية (Valuation for Investment Funds / REITs)",
        "تقييم الأثر البيئي (Environmental Impact Assessment - EIA)",
    ])
    def test_complex_route_keeps_baseline_and_flags_deferred(self, adapter, purpose):
        r = adapter.adapt(_baseline(100000.0), purpose)
        assert r.multiplier_applied == 1.00
        assert r.adjusted_value == 100000.0
        assert r.deep_route_deferred is True
        assert any("deferred" in n.lower() for n in r.notes)

    def test_complex_route_label_set(self, adapter):
        r = adapter.adapt(
            _baseline(),
            "التحليل الاستثماري - IRR / NPV / DCF",
        )
        assert r.route == "financial_metrics_trigger"


# ── IAAO trigger ──────────────────────────────────────────────────────────────

class TestIAAOTrigger:
    def test_tax_purpose_triggers_iaao_when_mode_enabled(self, adapter):
        r = adapter.adapt(
            _baseline(),
            "الضرائب - القيمة للأغراض الضريبية / الضريبة العقارية",
            iaao_mass_appraisal_mode=True,
        )
        assert r.iaao_block_triggered is True
        assert "Standard 5" in r.uspap_standards
        assert "Standard 6" in r.uspap_standards

    def test_tax_purpose_no_iaao_when_mode_disabled(self, adapter):
        r = adapter.adapt(
            _baseline(),
            "الضرائب - القيمة للأغراض الضريبية / الضريبة العقارية",
            iaao_mass_appraisal_mode=False,
        )
        assert r.iaao_block_triggered is False
        assert any("disabled" in n for n in r.notes)

    def test_non_tax_purpose_never_triggers_iaao(self, adapter):
        r = adapter.adapt(
            _baseline(),
            "البيع والشراء - القيمة السوقية العادلة (Market Value)",
            iaao_mass_appraisal_mode=True,
        )
        assert r.iaao_block_triggered is False


# ── USPAP standards ───────────────────────────────────────────────────────────

class TestUSPAP:
    def test_component_level_standards_always_present(self, adapter):
        r = adapter.adapt(
            _baseline(),
            "البيع والشراء - القيمة السوقية العادلة (Market Value)",
        )
        assert "Standard 1" in r.uspap_standards
        assert "Standard 2" in r.uspap_standards

    def test_mass_appraisal_standards_only_for_tax(self, adapter):
        r = adapter.adapt(
            _baseline(),
            "البيع والشراء - القيمة السوقية العادلة (Market Value)",
        )
        assert "Standard 5" not in r.uspap_standards
        assert "Standard 6" not in r.uspap_standards


# ── Errors ────────────────────────────────────────────────────────────────────

class TestErrors:
    def test_unknown_purpose_raises(self, adapter):
        with pytest.raises(PurposeAdapterError, match="Unknown purpose"):
            adapter.adapt(_baseline(), "غرض غير موجود")

    def test_error_message_includes_valid_purposes(self, adapter):
        with pytest.raises(PurposeAdapterError, match="Valid"):
            adapter.adapt(_baseline(), "unknown")


# ── Notes carry-forward ───────────────────────────────────────────────────────

class TestNotesCarryForward:
    def test_engine_notes_preserved(self, adapter):
        base = ComponentValuation(
            component_id=1,
            name="hotel",
            asset_type="فنادق ومنتجعات سياحية",
            area_sqm=5000.0,
            baseline_value=500000.0,
            method="income_revpar_baseline",
            notes=("NOTE: RevPAR baseline only — full income-approach deferred",),
        )
        r = adapter.adapt(
            base,
            "البيع والشراء - القيمة السوقية العادلة (Market Value)",
        )
        assert any("RevPAR" in n for n in r.notes)

    def test_rule_note_appended(self, adapter):
        r = adapter.adapt(
            _baseline(),
            "التأمين - قيمة إعادة الإنشاء (Reinstatement Value x1.08)",
        )
        assert any("structure-only" in n for n in r.notes)


# ── adapt_all ─────────────────────────────────────────────────────────────────

class TestAdaptAll:
    def test_aligned_lists(self, adapter):
        vals = [_baseline(100000.0), _baseline(200000.0)]
        purposes = [
            "البيع والشراء - القيمة السوقية العادلة (Market Value)",
            "الرهن والتمويل البنكي - القيمة السوقية لأغراض التمويل (0.95x)",
        ]
        results = adapter.adapt_all(vals, purposes)
        assert len(results) == 2
        assert results[0].adjusted_value == 100000.0
        assert results[1].adjusted_value == 190000.0

    def test_length_mismatch_raises(self, adapter):
        with pytest.raises(ValueError, match="length mismatch"):
            adapter.adapt_all([_baseline()], ["p1", "p2"])

    def test_empty_lists(self, adapter):
        assert adapter.adapt_all([], []) == []

    def test_order_preserved(self, adapter):
        vals = [_baseline(v) for v in [50000.0, 80000.0, 120000.0]]
        purposes = [
            "التصفية الإجبارية - القيمة التصفوية (Liquidation Value x0.82)",
            "البيع والشراء - القيمة السوقية العادلة (Market Value)",
            "التأمين - قيمة إعادة الإنشاء (Reinstatement Value x1.08)",
        ]
        results = adapter.adapt_all(vals, purposes)
        assert results[0].adjusted_value == round(50000.0 * 0.82, 2)
        assert results[1].adjusted_value == 80000.0
        assert results[2].adjusted_value == round(120000.0 * 1.08, 2)


# ── Result dataclass ──────────────────────────────────────────────────────────

class TestAdjustedValuation:
    def test_is_frozen(self, adapter):
        r = adapter.adapt(
            _baseline(),
            "البيع والشراء - القيمة السوقية العادلة (Market Value)",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            r.adjusted_value = 999  # type: ignore[misc]

    def test_notes_and_uspap_are_tuples(self, adapter):
        r = adapter.adapt(
            _baseline(),
            "الضرائب - القيمة للأغراض الضريبية / الضريبة العقارية",
        )
        assert isinstance(r.notes, tuple)
        assert isinstance(r.uspap_standards, tuple)

    def test_baseline_value_preserved_in_result(self, adapter):
        r = adapter.adapt(
            _baseline(123456.78),
            "الرهن والتمويل البنكي - القيمة السوقية لأغراض التمويل (0.95x)",
        )
        assert r.baseline_value == 123456.78
        assert r.adjusted_value == round(123456.78 * 0.95, 2)
