"""Tests for core_engine.validation.composite_rules (Wave 3)."""
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

from valuation_engines.composite_engine import ASSET_TYPES as _ENGINE_ASSET_TYPES  # noqa: E402
from adapters.purpose_adapter import PURPOSE_RULES as _ADAPTER_PURPOSE_RULES       # noqa: E402
from validation.composite_rules import (  # noqa: E402
    ASSET_TYPES,
    PURPOSE_RULES,
    Severity,
    ValidationIssue,
    CompositeValidationReport,
    CompositeValidationError,
    CompositeValidator,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def validator():
    return CompositeValidator()


def _residential(area=100.0):
    return {
        "asset_type": "وحدة سكنية (شقة / فيلا)",
        "area_sqm": area,
        "specific_attributes": {"bedrooms_count": 3, "floor_number": 2},
    }


def _airport(concession=20.0):
    return {
        "asset_type": "المطارات والموانئ",
        "area_sqm": 50000.0,
        "specific_attributes": {
            "facility_subtype": "مطار",
            "annual_throughput": 5000000.0,
            "berth_or_runway_count": 2,
            "concession_years_remaining": concession,
        },
    }


_MARKET_VALUE = "البيع والشراء - القيمة السوقية العادلة (Market Value)"
_FINANCING = "الرهن والتمويل البنكي - القيمة السوقية لأغراض التمويل (0.95x)"
_LIQUIDATION = "التصفية الإجبارية - القيمة التصفوية (Liquidation Value x0.82)"
_DCF = "التحليل الاستثماري - IRR / NPV / DCF"


# ── DRY identity ──────────────────────────────────────────────────────────────

class TestDRYIdentity:
    def test_asset_types_same_object(self):
        assert ASSET_TYPES is _ENGINE_ASSET_TYPES

    def test_purpose_rules_same_object(self):
        assert PURPOSE_RULES is _ADAPTER_PURPOSE_RULES


# ── Severity enum ─────────────────────────────────────────────────────────────

class TestSeverityEnum:
    def test_blocking_member(self):
        assert Severity.BLOCKING.value == "BLOCKING"

    def test_advisory_member(self):
        assert Severity.ADVISORY.value == "ADVISORY"

    def test_is_enum(self):
        import enum
        assert issubclass(Severity, enum.Enum)


# ── ValidationIssue frozen ────────────────────────────────────────────────────

class TestValidationIssueFrozen:
    def test_is_frozen(self):
        issue = ValidationIssue(
            severity=Severity.BLOCKING,
            code="X",
            component_index=0,
            field="f",
            message="m",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            issue.code = "Y"  # type: ignore[misc]


# ── CompositeValidationReport properties ─────────────────────────────────────

class TestCompositeValidationReport:
    def _make(self, severities: list[Severity]) -> CompositeValidationReport:
        issues = tuple(
            ValidationIssue(s, "X", 0, "f", "m") for s in severities
        )
        return CompositeValidationReport(issues=issues)

    def test_blocking_count(self):
        r = self._make([Severity.BLOCKING, Severity.ADVISORY, Severity.BLOCKING])
        assert r.blocking_count == 2

    def test_advisory_count(self):
        r = self._make([Severity.BLOCKING, Severity.ADVISORY])
        assert r.advisory_count == 1

    def test_is_blocking_true(self):
        assert self._make([Severity.BLOCKING]).is_blocking is True

    def test_is_blocking_false_when_advisory_only(self):
        assert self._make([Severity.ADVISORY]).is_blocking is False

    def test_is_clean_true(self):
        assert CompositeValidationReport(issues=()).is_clean is True

    def test_is_clean_false(self):
        assert self._make([Severity.ADVISORY]).is_clean is False

    def test_is_frozen(self):
        r = CompositeValidationReport(issues=())
        with pytest.raises(dataclasses.FrozenInstanceError):
            r.issues = ()  # type: ignore[misc]

    def test_issues_is_tuple(self):
        r = CompositeValidationReport(issues=())
        assert isinstance(r.issues, tuple)


# ── validate_component ────────────────────────────────────────────────────────

class TestValidateComponent:
    def test_clean_residential(self, validator):
        issues = validator.validate_component(_residential(), 0)
        assert issues == []

    def test_clean_airport(self, validator):
        issues = validator.validate_component(_airport(), 0)
        assert issues == []

    @pytest.mark.parametrize("asset_type", list(ASSET_TYPES.keys()))
    def test_all_15_types_accept_minimal_valid_component(self, validator, asset_type):
        """Every type should return no issues with valid minimal inputs."""
        spec: dict = {}
        for attr_name, attr_type in ASSET_TYPES[asset_type].items():
            if attr_type == int:
                spec[attr_name] = 1
            elif attr_type == float:
                spec[attr_name] = 1.0
            elif attr_type == str:
                spec[attr_name] = "test"
            elif attr_type == bool:
                spec[attr_name] = True
        component = {
            "asset_type": asset_type,
            "area_sqm": 100.0,
            "specific_attributes": spec,
        }
        issues = validator.validate_component(component, 0)
        assert issues == [], f"Unexpected issues for {asset_type}: {issues}"

    def test_missing_asset_type_blocking(self, validator):
        comp = {"area_sqm": 100.0, "specific_attributes": {}}
        issues = validator.validate_component(comp, 0)
        codes = [i.code for i in issues]
        assert "MISSING_ASSET_TYPE" in codes
        assert all(i.severity == Severity.BLOCKING for i in issues)

    def test_unknown_asset_type_blocking(self, validator):
        comp = {"asset_type": "نوع غير معروف", "area_sqm": 100.0, "specific_attributes": {}}
        issues = validator.validate_component(comp, 0)
        codes = [i.code for i in issues]
        assert "UNKNOWN_ASSET_TYPE" in codes

    def test_missing_area_sqm_blocking(self, validator):
        comp = {
            "asset_type": "وحدة سكنية (شقة / فيلا)",
            "specific_attributes": {"bedrooms_count": 3, "floor_number": 1},
        }
        issues = validator.validate_component(comp, 0)
        codes = [i.code for i in issues]
        assert "NON_POSITIVE_AREA" in codes
        assert all(i.severity != Severity.ADVISORY for i in issues if i.code == "NON_POSITIVE_AREA")

    def test_zero_area_sqm_blocking(self, validator):
        issues = validator.validate_component(_residential(area=0.0), 0)
        assert any(i.code == "NON_POSITIVE_AREA" for i in issues)

    def test_negative_area_sqm_blocking(self, validator):
        issues = validator.validate_component(_residential(area=-50.0), 0)
        assert any(i.code == "NON_POSITIVE_AREA" for i in issues)

    def test_missing_required_attr_blocking(self, validator):
        comp = {
            "asset_type": "وحدة سكنية (شقة / فيلا)",
            "area_sqm": 100.0,
            "specific_attributes": {"bedrooms_count": 3},  # floor_number missing
        }
        issues = validator.validate_component(comp, 0)
        codes = [i.code for i in issues]
        assert "MISSING_REQUIRED_ATTR" in codes
        blocking = [i for i in issues if i.code == "MISSING_REQUIRED_ATTR"]
        assert all(i.severity == Severity.BLOCKING for i in blocking)
        assert any("floor_number" in i.field for i in blocking)

    def test_wrong_attr_type_blocking(self, validator):
        comp = {
            "asset_type": "وحدة سكنية (شقة / فيلا)",
            "area_sqm": 100.0,
            "specific_attributes": {"bedrooms_count": "three", "floor_number": 1},
        }
        issues = validator.validate_component(comp, 0)
        assert any(i.code == "WRONG_ATTR_TYPE" for i in issues)
        wrong = [i for i in issues if i.code == "WRONG_ATTR_TYPE"]
        assert all(i.severity == Severity.BLOCKING for i in wrong)

    def test_implausible_concession_years_advisory(self, validator):
        issues = validator.validate_component(_airport(concession=100.0), 0)
        assert any(i.code == "IMPLAUSIBLE_RANGE" for i in issues)
        implausible = [i for i in issues if i.code == "IMPLAUSIBLE_RANGE"]
        assert all(i.severity == Severity.ADVISORY for i in implausible)

    def test_concession_99_is_not_implausible(self, validator):
        issues = validator.validate_component(_airport(concession=99.0), 0)
        assert not any(i.code == "IMPLAUSIBLE_RANGE" for i in issues)

    def test_non_mapping_raises(self, validator):
        with pytest.raises(CompositeValidationError):
            validator.validate_component(["not", "a", "mapping"], 0)  # type: ignore


# ── validate_purpose ──────────────────────────────────────────────────────────

class TestValidatePurpose:
    def test_clean_market_value(self, validator):
        issues = validator.validate_purpose(_MARKET_VALUE)
        assert issues == []

    def test_unknown_purpose_blocking(self, validator):
        issues = validator.validate_purpose("غرض غير معروف")
        assert any(i.code == "UNKNOWN_PURPOSE" for i in issues)
        assert all(i.severity == Severity.BLOCKING for i in issues)

    def test_deep_route_purpose_advisory(self, validator):
        issues = validator.validate_purpose(_DCF)
        assert any(i.code == "DEFERRED_DEEP_ROUTE" for i in issues)
        deferred = [i for i in issues if i.code == "DEFERRED_DEEP_ROUTE"]
        assert all(i.severity == Severity.ADVISORY for i in deferred)

    def test_explicit_multiplier_purpose_no_deferred(self, validator):
        issues = validator.validate_purpose(_LIQUIDATION)
        assert not any(i.code == "DEFERRED_DEEP_ROUTE" for i in issues)

    def test_non_string_raises(self, validator):
        with pytest.raises(CompositeValidationError):
            validator.validate_purpose(42)  # type: ignore

    def test_component_index_propagated(self, validator):
        issues = validator.validate_purpose("غرض خطأ", component_index=7)
        assert issues[0].component_index == 7


# ── validate (full) ───────────────────────────────────────────────────────────

class TestValidate:
    def test_all_clean(self, validator):
        report = validator.validate(
            [_residential(), _airport()],
            [_MARKET_VALUE, _MARKET_VALUE],
        )
        assert report.is_clean

    def test_length_mismatch_raises(self, validator):
        with pytest.raises(CompositeValidationError, match="length mismatch"):
            validator.validate([_residential()], [_MARKET_VALUE, _LIQUIDATION])

    def test_wrong_components_type_raises(self, validator):
        with pytest.raises(CompositeValidationError):
            validator.validate((_residential(),), [_MARKET_VALUE])  # type: ignore

    def test_wrong_purposes_type_raises(self, validator):
        with pytest.raises(CompositeValidationError):
            validator.validate([_residential()], (_MARKET_VALUE,))  # type: ignore

    def test_empty_lists_clean(self, validator):
        report = validator.validate([], [])
        assert report.is_clean

    def test_blocking_propagates_to_report(self, validator):
        bad = {"asset_type": "نوع مجهول", "area_sqm": 100.0, "specific_attributes": {}}
        report = validator.validate([bad], [_MARKET_VALUE])
        assert report.is_blocking

    def test_advisory_only_not_blocking(self, validator):
        report = validator.validate([_airport()], [_DCF])
        assert not report.is_blocking
        assert report.advisory_count >= 1

    def test_coherence_airport_liquidation_advisory(self, validator):
        report = validator.validate([_airport()], [_LIQUIDATION])
        coherence = [i for i in report.issues if i.code == "PURPOSE_ASSET_COHERENCE"]
        assert len(coherence) == 1
        assert coherence[0].severity == Severity.ADVISORY

    def test_coherence_airport_financing_advisory(self, validator):
        report = validator.validate([_airport()], [_FINANCING])
        coherence = [i for i in report.issues if i.code == "PURPOSE_ASSET_COHERENCE"]
        assert len(coherence) == 1
        assert coherence[0].severity == Severity.ADVISORY

    def test_coherence_airport_market_value_no_issue(self, validator):
        report = validator.validate([_airport()], [_MARKET_VALUE])
        coherence = [i for i in report.issues if i.code == "PURPOSE_ASSET_COHERENCE"]
        assert len(coherence) == 0

    def test_coherence_residential_liquidation_no_issue(self, validator):
        report = validator.validate([_residential()], [_LIQUIDATION])
        coherence = [i for i in report.issues if i.code == "PURPOSE_ASSET_COHERENCE"]
        assert len(coherence) == 0

    def test_multiple_components_index_correct(self, validator):
        bad_purpose = "غرض مجهول"
        report = validator.validate(
            [_residential(), _residential()],
            [_MARKET_VALUE, bad_purpose],
        )
        unknown = [i for i in report.issues if i.code == "UNKNOWN_PURPOSE"]
        assert len(unknown) == 1
        assert unknown[0].component_index == 1

    def test_no_raise_on_validation_failure(self, validator):
        bad = {"asset_type": "مجهول", "area_sqm": -1.0, "specific_attributes": {}}
        report = validator.validate([bad], ["غرض مجهول"])
        assert report.is_blocking  # returns report, never raises


# ── Report immutability ───────────────────────────────────────────────────────

class TestReportImmutability:
    def test_report_frozen(self, validator):
        report = validator.validate([_residential()], [_MARKET_VALUE])
        with pytest.raises(dataclasses.FrozenInstanceError):
            report.issues = ()  # type: ignore[misc]
