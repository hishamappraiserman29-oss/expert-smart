"""
Unit tests for valuation_engines/composite_reporter.py (Wave 7B).

All tests are pure — no Flask, no DB, no HTTP.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# ── sys.path ──────────────────────────────────────────────────────────
_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent

for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_ORIG_CWD = os.getcwd()
try:
    os.chdir(str(_CORE))

    from adapters.purpose_adapter import AdjustedValuation
    from valuation_engines.composite_reporter import (
        _IAAO_NOTE,
        _USPAP_NOTE,
        build_reporting_blocks,
    )
finally:
    os.chdir(_ORIG_CWD)


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def _av(
    *,
    uspap_standards: tuple = ("Standard 1", "Standard 2"),
    iaao_block_triggered: bool = False,
    deep_route_deferred: bool = False,
    idx: int = 0,
) -> AdjustedValuation:
    return AdjustedValuation(
        component_id=f"c{idx}",
        name=f"unit-{idx}",
        asset_type="وحدة سكنية (شقة / فيلا)",
        purpose="البيع والشراء - القيمة السوقية العادلة (Market Value)",
        baseline_value=1_000_000.0,
        multiplier_applied=1.0,
        adjusted_value=1_000_000.0,
        route="market_baseline",
        deep_route_deferred=deep_route_deferred,
        iaao_block_triggered=iaao_block_triggered,
        uspap_standards=uspap_standards,
        notes=(),
    )


_NON_TAX = _av()
_MASS_AV = _av(
    uspap_standards=("Standard 1", "Standard 2", "Standard 5", "Standard 6"),
    iaao_block_triggered=True,
)


# ─────────────────────────────────────────────────────────────────────
# 1. uspap_reporting structure
# ─────────────────────────────────────────────────────────────────────

class TestUspapBlock:
    def test_returns_uspap_reporting_key(self):
        result = build_reporting_blocks([_NON_TAX])
        assert "uspap_reporting" in result

    def test_standards_applied_non_tax(self):
        r = build_reporting_blocks([_NON_TAX])
        assert r["uspap_reporting"]["standards_applied"] == ["Standard 1", "Standard 2"]

    def test_mass_appraisal_standards_absent_non_tax(self):
        r = build_reporting_blocks([_NON_TAX])
        assert r["uspap_reporting"]["mass_appraisal_standards_present"] is False

    def test_components_count(self):
        r = build_reporting_blocks([_NON_TAX, _NON_TAX])
        assert r["uspap_reporting"]["components_count"] == 2

    def test_note_present(self):
        r = build_reporting_blocks([_NON_TAX])
        assert r["uspap_reporting"]["note"] == _USPAP_NOTE

    def test_note_does_not_claim_uspap_certified(self):
        r = build_reporting_blocks([_NON_TAX])
        note = r["uspap_reporting"]["note"].lower()
        assert "uspap certified" not in note
        assert "iaao certified" not in note

    def test_mass_appraisal_standards_present_with_std5_6(self):
        r = build_reporting_blocks([_MASS_AV])
        assert r["uspap_reporting"]["mass_appraisal_standards_present"] is True

    def test_standards_applied_includes_5_6_when_present(self):
        r = build_reporting_blocks([_MASS_AV])
        stds = r["uspap_reporting"]["standards_applied"]
        assert "Standard 5" in stds
        assert "Standard 6" in stds

    def test_standards_applied_sorted(self):
        r = build_reporting_blocks([_MASS_AV])
        stds = r["uspap_reporting"]["standards_applied"]
        assert stds == sorted(stds)

    def test_empty_valuations_empty_standards(self):
        r = build_reporting_blocks([])
        assert r["uspap_reporting"]["standards_applied"] == []
        assert r["uspap_reporting"]["components_count"] == 0

    def test_standards_union_across_components(self):
        av1 = _av(uspap_standards=("Standard 1", "Standard 2"), idx=0)
        av2 = _av(uspap_standards=("Standard 1", "Standard 2", "Standard 5", "Standard 6"), idx=1)
        r = build_reporting_blocks([av1, av2])
        stds = r["uspap_reporting"]["standards_applied"]
        assert set(stds) == {"Standard 1", "Standard 2", "Standard 5", "Standard 6"}
        assert r["uspap_reporting"]["mass_appraisal_standards_present"] is True


# ─────────────────────────────────────────────────────────────────────
# 2. iaao_reporting structure
# ─────────────────────────────────────────────────────────────────────

class TestIaaoBlock:
    def test_returns_iaao_reporting_key(self):
        result = build_reporting_blocks([_NON_TAX])
        assert "iaao_reporting" in result

    def test_cod_is_none(self):
        r = build_reporting_blocks([_NON_TAX])
        assert r["iaao_reporting"]["cod"] is None

    def test_prd_is_none(self):
        r = build_reporting_blocks([_NON_TAX])
        assert r["iaao_reporting"]["prd"] is None

    def test_ratio_study_status_not_computed(self):
        r = build_reporting_blocks([_NON_TAX])
        assert r["iaao_reporting"]["ratio_study_status"] == "not_computed"

    def test_note_present(self):
        r = build_reporting_blocks([_NON_TAX])
        assert r["iaao_reporting"]["note"] == _IAAO_NOTE

    def test_note_mentions_ratio_study(self):
        r = build_reporting_blocks([_NON_TAX])
        assert "ratio-study" in r["iaao_reporting"]["note"] or "sales-ratio" in r["iaao_reporting"]["note"]

    def test_note_does_not_claim_iaao_certified(self):
        r = build_reporting_blocks([_NON_TAX])
        note = r["iaao_reporting"]["note"].lower()
        assert "uspap certified" not in note
        assert "iaao certified" not in note

    def test_iaao_triggered_count_zero_default(self):
        r = build_reporting_blocks([_NON_TAX])
        assert r["iaao_reporting"]["iaao_triggered_count"] == 0

    def test_iaao_triggered_count_nonzero(self):
        r = build_reporting_blocks([_MASS_AV])
        assert r["iaao_reporting"]["iaao_triggered_count"] == 1

    def test_iaao_triggered_count_mixed(self):
        r = build_reporting_blocks([_NON_TAX, _MASS_AV, _MASS_AV])
        assert r["iaao_reporting"]["iaao_triggered_count"] == 2

    def test_deep_routes_deferred_count_zero(self):
        r = build_reporting_blocks([_NON_TAX])
        assert r["iaao_reporting"]["deep_routes_deferred_count"] == 0

    def test_deep_routes_deferred_count_nonzero(self):
        deep_av = _av(deep_route_deferred=True, idx=1)
        r = build_reporting_blocks([_NON_TAX, deep_av])
        assert r["iaao_reporting"]["deep_routes_deferred_count"] == 1

    def test_empty_valuations_zero_counts(self):
        r = build_reporting_blocks([])
        assert r["iaao_reporting"]["iaao_triggered_count"] == 0
        assert r["iaao_reporting"]["deep_routes_deferred_count"] == 0


# ─────────────────────────────────────────────────────────────────────
# 3. Determinism
# ─────────────────────────────────────────────────────────────────────

class TestDeterminism:
    def test_same_input_identical_output(self):
        avs = [_av(idx=0), _av(idx=1)]
        r1 = build_reporting_blocks(avs)
        r2 = build_reporting_blocks(avs)
        assert r1 == r2

    def test_same_input_with_mass_appraisal_identical(self):
        avs = [_MASS_AV, _NON_TAX]
        r1 = build_reporting_blocks(avs)
        r2 = build_reporting_blocks(avs)
        assert r1 == r2


# ─────────────────────────────────────────────────────────────────────
# 4. DRY — reporter reads existing AdjustedValuation fields
# ─────────────────────────────────────────────────────────────────────

class TestDRY:
    def test_reads_uspap_standards_from_field(self):
        """Reporter reflects whatever uspap_standards the adapter placed on AV."""
        custom_av = _av(uspap_standards=("Standard 1",), idx=0)
        r = build_reporting_blocks([custom_av])
        assert r["uspap_reporting"]["standards_applied"] == ["Standard 1"]

    def test_reads_iaao_block_triggered_from_field(self):
        triggered_av = _av(iaao_block_triggered=True, idx=0)
        r = build_reporting_blocks([triggered_av])
        assert r["iaao_reporting"]["iaao_triggered_count"] == 1

    def test_reads_deep_route_deferred_from_field(self):
        deep_av = _av(deep_route_deferred=True, idx=0)
        r = build_reporting_blocks([deep_av])
        assert r["iaao_reporting"]["deep_routes_deferred_count"] == 1

    def test_non_triggered_av_contributes_zero_iaao(self):
        r = build_reporting_blocks([_NON_TAX])
        assert r["iaao_reporting"]["iaao_triggered_count"] == 0

    def test_non_deep_av_contributes_zero_deep(self):
        r = build_reporting_blocks([_NON_TAX])
        assert r["iaao_reporting"]["deep_routes_deferred_count"] == 0
