"""
Phase 16.6 engine tests — Rights, Litigation Compensation, ESG Remediation.

RT01–RT20  RightsEngine
LC01–LC20  LitigationCompensationEngine
ES01–ES20  ESGRemediationEngine
"""

import pytest
from decimal import Decimal

from core_engine.engines.rights_engine import RightsEngine
from core_engine.engines.litigation_compensation_engine import LitigationCompensationEngine
from core_engine.engines.esg_remediation_engine import ESGRemediationEngine


# ────────────────────────────────────────────────────────────────────────────
# Shared fixtures
# ────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def rights_base():
    """FPV=10M, 25% ownership, DLOC=20%, DLOM=15%."""
    return {
        "full_property_value":  10_000_000,
        "ownership_percentage": 0.25,
        "dloc": 0.20,
        "dlom": 0.15,
    }


@pytest.fixture
def litigation_base():
    """Before=5M, After=3M, CTC=1.5M, Severance=200k."""
    return {
        "before_damage_value": 5_000_000,
        "after_damage_value":  3_000_000,
        "cost_to_cure":        1_500_000,
        "severance_damage":    200_000,
    }


@pytest.fixture
def esg_base():
    """All 5 components supplied."""
    return {
        "remediation_cost":    500_000,
        "environmental_fines": 100_000,
        "energy_savings":      300_000,
        "carbon_credit_value": 200_000,
        "green_premium":       400_000,
    }


# ────────────────────────────────────────────────────────────────────────────
# RightsEngine — RT01–RT20
# ────────────────────────────────────────────────────────────────────────────

engine_r = RightsEngine()


def test_RT01_high_confidence_both_discounts(rights_base):
    """RT01: dloc + dlom supplied → high confidence."""
    r = engine_r.calculate(rights_base)
    assert r.confidence == "high"
    assert r.value is not None


def test_RT02_medium_confidence_dloc_only(rights_base):
    """RT02: dloc only → medium confidence."""
    inp = dict(rights_base)
    del inp["dlom"]
    r = engine_r.calculate(inp)
    assert r.confidence == "medium"


def test_RT03_medium_confidence_dlom_only(rights_base):
    """RT03: dlom only → medium confidence."""
    inp = dict(rights_base)
    del inp["dloc"]
    r = engine_r.calculate(inp)
    assert r.confidence == "medium"


def test_RT04_low_confidence_no_discounts():
    """RT04: no dloc/dlom → low confidence."""
    r = engine_r.calculate({
        "full_property_value":  8_000_000,
        "ownership_percentage": 0.50,
    })
    assert r.confidence == "low"
    assert r.value == Decimal("4000000.00")


def test_RT05_usufruct_pv_computed(rights_base):
    """RT05: usufruct PV computed when all three usufruct inputs present."""
    inp = dict(rights_base)
    inp["remaining_term_years"] = 10.0
    inp["annual_noi"]           = 200_000
    inp["discount_rate"]        = 0.08
    r = engine_r.calculate(inp)
    assert r.metadata["usufruct_value"] is not None
    assert r.metadata["usufruct_value"] > 0


def test_RT06_full_ownership():
    """RT06: ownership_percentage=1.0 (100%) — minority_interest_undiscounted = FPV."""
    r = engine_r.calculate({
        "full_property_value":  6_000_000,
        "ownership_percentage": 1.0,
    })
    assert r.metadata["minority_interest_undiscounted"] == 6_000_000.0


def test_RT07_sequential_application_value(rights_base):
    """RT07: minority_interest_value = FPV × op × (1-DLOC) × (1-DLOM)."""
    r = engine_r.calculate(rights_base)
    expected = 10_000_000 * 0.25 * (1 - 0.20) * (1 - 0.15)
    assert r.value == Decimal(str(round(expected, 2)))


def test_RT08_sequential_not_additive(rights_base):
    """RT08: sequential > additive (additive overcounts discount)."""
    r = engine_r.calculate(rights_base)
    sequential  = float(r.value)
    # additive (wrong) approach
    additive_wrong = 10_000_000 * 0.25 * (1 - (0.20 + 0.15))
    assert sequential > additive_wrong


def test_RT09_high_dloc_warning():
    """RT09: dloc > 80% triggers HIGH_DLOC warning."""
    r = engine_r.calculate({
        "full_property_value":  5_000_000,
        "ownership_percentage": 0.10,
        "dloc": 0.85,
    })
    codes = [i.code for i in r.issues]
    assert "HIGH_DLOC" in codes


def test_RT10_high_dlom_warning():
    """RT10: dlom > 50% triggers HIGH_DLOM warning."""
    r = engine_r.calculate({
        "full_property_value":  5_000_000,
        "ownership_percentage": 0.10,
        "dlom": 0.60,
    })
    codes = [i.code for i in r.issues]
    assert "HIGH_DLOM" in codes


def test_RT11_missing_full_property_value():
    """RT11: missing full_property_value → insufficient."""
    r = engine_r.calculate({"ownership_percentage": 0.25})
    assert r.confidence == "insufficient"
    assert r.value is None


def test_RT12_ownership_zero_error():
    """RT12: ownership_percentage=0 → error."""
    r = engine_r.calculate({
        "full_property_value":  5_000_000,
        "ownership_percentage": 0.0,
    })
    assert r.confidence == "insufficient"


def test_RT13_ownership_over_one_error():
    """RT13: ownership_percentage=1.5 → error."""
    r = engine_r.calculate({
        "full_property_value":  5_000_000,
        "ownership_percentage": 1.5,
    })
    assert r.confidence == "insufficient"


def test_RT14_dloc_ge_one_error():
    """RT14: dloc=1.0 → error (must be < 1)."""
    r = engine_r.calculate({
        "full_property_value":  5_000_000,
        "ownership_percentage": 0.25,
        "dloc": 1.0,
    })
    assert r.confidence == "insufficient"


def test_RT15_dlom_negative_error():
    """RT15: dlom=-0.05 → error."""
    r = engine_r.calculate({
        "full_property_value":  5_000_000,
        "ownership_percentage": 0.25,
        "dlom": -0.05,
    })
    assert r.confidence == "insufficient"


def test_RT16_invalid_remaining_term():
    """RT16: remaining_term_years=0 → error."""
    r = engine_r.calculate({
        "full_property_value":  5_000_000,
        "ownership_percentage": 0.25,
        "remaining_term_years": 0,
        "annual_noi": 100_000,
        "discount_rate": 0.08,
    })
    assert r.confidence == "insufficient"


def test_RT17_invalid_annual_noi():
    """RT17: annual_noi=-1 → error."""
    r = engine_r.calculate({
        "full_property_value":  5_000_000,
        "ownership_percentage": 0.25,
        "remaining_term_years": 10,
        "annual_noi": -1,
        "discount_rate": 0.08,
    })
    assert r.confidence == "insufficient"


def test_RT18_incomplete_usufruct_warning():
    """RT18: two of three usufruct inputs → INCOMPLETE_USUFRUCT_INPUTS warning."""
    r = engine_r.calculate({
        "full_property_value":  5_000_000,
        "ownership_percentage": 0.25,
        "annual_noi": 100_000,
        "discount_rate": 0.08,
        # remaining_term_years missing
    })
    codes = [i.code for i in r.issues]
    assert "INCOMPLETE_USUFRUCT_INPUTS" in codes
    assert r.metadata.get("usufruct_value") is None


def test_RT19_value_decimal_type(rights_base):
    """RT19: result.value is Decimal."""
    r = engine_r.calculate(rights_base)
    assert isinstance(r.value, Decimal)


def test_RT20_usufruct_pv_formula():
    """RT20: usufruct_value = NOI × [1-(1+r)^(-n)] / r."""
    noi = 120_000
    r_rate = 0.10
    n = 5
    r = engine_r.calculate({
        "full_property_value":  5_000_000,
        "ownership_percentage": 1.0,
        "remaining_term_years": n,
        "annual_noi":           noi,
        "discount_rate":        r_rate,
    })
    expected_pv = noi * (1 - (1 + r_rate) ** (-n)) / r_rate
    assert abs(r.metadata["usufruct_value"] - round(expected_pv, 2)) < 0.01


# ────────────────────────────────────────────────────────────────────────────
# LitigationCompensationEngine — LC01–LC20
# ────────────────────────────────────────────────────────────────────────────

engine_l = LitigationCompensationEngine()


def test_LC01_high_confidence_both_optional(litigation_base):
    """LC01: ctc + severance → high confidence."""
    r = engine_l.calculate(litigation_base)
    assert r.confidence == "high"
    assert r.value is not None


def test_LC02_medium_confidence_ctc_only():
    """LC02: cost_to_cure only → medium."""
    r = engine_l.calculate({
        "before_damage_value": 5_000_000,
        "after_damage_value":  3_000_000,
        "cost_to_cure":        1_500_000,
    })
    assert r.confidence == "medium"


def test_LC03_medium_confidence_severance_only():
    """LC03: severance_damage only → medium."""
    r = engine_l.calculate({
        "before_damage_value": 5_000_000,
        "after_damage_value":  3_000_000,
        "severance_damage":    200_000,
    })
    assert r.confidence == "medium"


def test_LC04_low_confidence_neither():
    """LC04: no ctc, no sev → low confidence + warning."""
    r = engine_l.calculate({
        "before_damage_value": 5_000_000,
        "after_damage_value":  3_000_000,
    })
    assert r.confidence == "low"
    codes = [i.code for i in r.issues]
    assert "MISSING_OPTIONAL_COMPONENTS" in codes


def test_LC05_diminution_calculation(litigation_base):
    """LC05: diminution = before − after = 2,000,000."""
    r = engine_l.calculate(litigation_base)
    assert r.metadata["diminution_in_value"] == 2_000_000.0


def test_LC06_cure_viable_when_less_than_diminution():
    """LC06: cost_to_cure < diminution → cost_to_cure_viable=True."""
    r = engine_l.calculate({
        "before_damage_value": 5_000_000,
        "after_damage_value":  3_000_000,
        "cost_to_cure":        1_500_000,
    })
    assert r.metadata["cost_to_cure_viable"] is True


def test_LC07_cure_not_viable_when_exceeds_diminution():
    """LC07: cost_to_cure > diminution → cost_to_cure_viable=False."""
    r = engine_l.calculate({
        "before_damage_value": 5_000_000,
        "after_damage_value":  3_000_000,
        "cost_to_cure":        2_500_000,
    })
    assert r.metadata["cost_to_cure_viable"] is False


def test_LC08_high_cure_ratio_warning():
    """LC08: cost_to_cure > 90% of diminution → HIGH_CURE_COST_RATIO warning."""
    r = engine_l.calculate({
        "before_damage_value": 5_000_000,
        "after_damage_value":  3_000_000,
        "cost_to_cure":        1_900_000,   # 95% of 2M diminution
    })
    codes = [i.code for i in r.issues]
    assert "HIGH_CURE_COST_RATIO" in codes


def test_LC09_zero_diminution_warning():
    """LC09: before == after → ZERO_DIMINUTION warning."""
    r = engine_l.calculate({
        "before_damage_value": 5_000_000,
        "after_damage_value":  5_000_000,
    })
    codes = [i.code for i in r.issues]
    assert "ZERO_DIMINUTION" in codes


def test_LC10_total_compensation_with_severance(litigation_base):
    """LC10: total_compensation = diminution + severance = 2,200,000."""
    r = engine_l.calculate(litigation_base)
    assert r.metadata["total_compensation"] == 2_200_000.0
    assert r.value == Decimal("2200000.00")


def test_LC11_missing_before_value():
    """LC11: missing before_damage_value → insufficient."""
    r = engine_l.calculate({"after_damage_value": 3_000_000})
    assert r.confidence == "insufficient"


def test_LC12_missing_after_value():
    """LC12: missing after_damage_value → insufficient."""
    r = engine_l.calculate({"before_damage_value": 5_000_000})
    assert r.confidence == "insufficient"


def test_LC13_after_exceeds_before():
    """LC13: after > before → error."""
    r = engine_l.calculate({
        "before_damage_value": 3_000_000,
        "after_damage_value":  5_000_000,
    })
    assert r.confidence == "insufficient"
    codes = [i.code for i in r.issues]
    assert "AFTER_EXCEEDS_BEFORE" in codes


def test_LC14_negative_cost_to_cure():
    """LC14: cost_to_cure < 0 → error."""
    r = engine_l.calculate({
        "before_damage_value": 5_000_000,
        "after_damage_value":  3_000_000,
        "cost_to_cure":        -100_000,
    })
    assert r.confidence == "insufficient"


def test_LC15_negative_severance():
    """LC15: severance_damage < 0 → error."""
    r = engine_l.calculate({
        "before_damage_value": 5_000_000,
        "after_damage_value":  3_000_000,
        "severance_damage":    -50_000,
    })
    assert r.confidence == "insufficient"


def test_LC16_total_loss_after_zero():
    """LC16: after_damage_value=0 → diminution = before_damage_value."""
    r = engine_l.calculate({
        "before_damage_value": 4_000_000,
        "after_damage_value":  0,
    })
    assert r.metadata["diminution_in_value"] == 4_000_000.0
    assert r.value == Decimal("4000000.00")


def test_LC17_value_decimal_type(litigation_base):
    """LC17: result.value is Decimal."""
    r = engine_l.calculate(litigation_base)
    assert isinstance(r.value, Decimal)


def test_LC18_audit_trail_steps(litigation_base):
    """LC18: audit trail includes all expected step names."""
    r = engine_l.calculate(litigation_base)
    steps = [a.step_name for a in r.audit_trail]
    assert any("diminution" in s.lower() for s in steps)
    assert any("cost-to-cure" in s.lower() or "cure" in s.lower() for s in steps)
    assert any("severance" in s.lower() for s in steps)
    assert any("total compensation" in s.lower() for s in steps)


def test_LC19_warning_when_neither_optional():
    """LC19: MISSING_OPTIONAL_COMPONENTS warning when no ctc or sev."""
    r = engine_l.calculate({
        "before_damage_value": 5_000_000,
        "after_damage_value":  2_000_000,
    })
    codes = [i.code for i in r.issues]
    assert "MISSING_OPTIONAL_COMPONENTS" in codes


def test_LC20_insufficient_on_invalid_before():
    """LC20: before_damage_value=0 → insufficient confidence."""
    r = engine_l.calculate({
        "before_damage_value": 0,
        "after_damage_value":  0,
    })
    assert r.confidence == "insufficient"


# ────────────────────────────────────────────────────────────────────────────
# ESGRemediationEngine — ES01–ES20
# ────────────────────────────────────────────────────────────────────────────

engine_e = ESGRemediationEngine()


def test_ES01_all_five_components_high_confidence(esg_base):
    """ES01: all 5 inputs → high confidence (≥3 components)."""
    r = engine_e.calculate(esg_base)
    assert r.confidence == "high"
    assert r.value is not None


def test_ES02_three_components_high():
    """ES02: 3 components → high confidence."""
    r = engine_e.calculate({
        "remediation_cost":  300_000,
        "energy_savings":    200_000,
        "green_premium":     150_000,
    })
    assert r.confidence == "high"


def test_ES03_two_components_medium():
    """ES03: 2 components → medium confidence."""
    r = engine_e.calculate({
        "remediation_cost": 300_000,
        "energy_savings":   200_000,
    })
    assert r.confidence == "medium"


def test_ES04_one_component_low():
    """ES04: 1 component → low confidence."""
    r = engine_e.calculate({"green_premium": 100_000})
    assert r.confidence == "low"


def test_ES05_net_positive_result(esg_base):
    """ES05: benefits (900k) > costs (600k) → net_esg_adjustment = 300k."""
    r = engine_e.calculate(esg_base)
    # total_costs=600k, total_benefits=900k → net=300k
    assert r.metadata["net_esg_adjustment"] == 300_000.0
    assert r.value == Decimal("300000.00")


def test_ES06_net_negative_result():
    """ES06: costs > benefits → net_esg_adjustment < 0."""
    r = engine_e.calculate({
        "remediation_cost":    1_000_000,
        "environmental_fines": 500_000,
        "energy_savings":      200_000,
    })
    assert r.metadata["net_esg_adjustment"] < 0
    assert float(r.value) < 0


def test_ES07_no_inputs_error():
    """ES07: no inputs at all → insufficient."""
    r = engine_e.calculate({})
    assert r.confidence == "insufficient"
    codes = [i.code for i in r.issues]
    assert "NO_ESG_INPUTS" in codes


def test_ES08_negative_remediation_cost_error():
    """ES08: remediation_cost < 0 → error."""
    r = engine_e.calculate({"remediation_cost": -100_000})
    assert r.confidence == "insufficient"


def test_ES09_high_cost_ratio_warning():
    """ES09: total_costs > 50% of total_benefits → HIGH_REMEDIATION_COST_RATIO."""
    r = engine_e.calculate({
        "remediation_cost":  600_000,
        "energy_savings":    200_000,
        "green_premium":     100_000,   # benefits=300k, costs=600k → ratio=200%
    })
    codes = [i.code for i in r.issues]
    assert "HIGH_REMEDIATION_COST_RATIO" in codes


def test_ES10_no_cost_components_info():
    """ES10: only benefits → NO_COST_COMPONENTS info."""
    r = engine_e.calculate({
        "energy_savings":    200_000,
        "carbon_credit_value": 100_000,
    })
    codes = [i.code for i in r.issues]
    assert "NO_COST_COMPONENTS" in codes


def test_ES11_no_benefit_components_info():
    """ES11: only costs → NO_BENEFIT_COMPONENTS info."""
    r = engine_e.calculate({
        "remediation_cost":    500_000,
        "environmental_fines": 100_000,
    })
    codes = [i.code for i in r.issues]
    assert "NO_BENEFIT_COMPONENTS" in codes


def test_ES12_value_can_be_negative():
    """ES12: value is Decimal and can be negative."""
    r = engine_e.calculate({
        "remediation_cost":    800_000,
        "environmental_fines": 200_000,
        "green_premium":       100_000,
    })
    assert isinstance(r.value, Decimal)
    assert float(r.value) < 0


def test_ES13_remediation_only():
    """ES13: only remediation_cost → total_benefits=0, net=−remediation."""
    r = engine_e.calculate({"remediation_cost": 400_000})
    assert r.metadata["net_esg_adjustment"] == -400_000.0


def test_ES14_green_premium_only():
    """ES14: only green_premium → net=+green_premium."""
    r = engine_e.calculate({"green_premium": 250_000})
    assert r.metadata["net_esg_adjustment"] == 250_000.0
    assert r.value == Decimal("250000.00")


def test_ES15_all_costs_no_benefits():
    """ES15: both cost inputs, no benefits → negative net."""
    r = engine_e.calculate({
        "remediation_cost":    700_000,
        "environmental_fines": 300_000,
    })
    assert r.metadata["total_costs"]    == 1_000_000.0
    assert r.metadata["total_benefits"] == 0.0
    assert r.metadata["net_esg_adjustment"] == -1_000_000.0


def test_ES16_all_benefits_no_costs():
    """ES16: all three benefit inputs, no costs → positive net."""
    r = engine_e.calculate({
        "energy_savings":      200_000,
        "carbon_credit_value": 150_000,
        "green_premium":       250_000,
    })
    assert r.metadata["total_costs"]    == 0.0
    assert r.metadata["total_benefits"] == 600_000.0
    assert r.metadata["net_esg_adjustment"] == 600_000.0


def test_ES17_audit_trail_three_steps(esg_base):
    """ES17: audit trail has exactly 3 steps for full input set."""
    r = engine_e.calculate(esg_base)
    assert len(r.audit_trail) == 3


def test_ES18_metadata_components_supplied(esg_base):
    """ES18: metadata['components_supplied'] counts correctly."""
    r = engine_e.calculate(esg_base)
    assert r.metadata["components_supplied"] == 5


def test_ES19_engine_name():
    """ES19: engine_name is 'esg_remediation'."""
    r = engine_e.calculate({"green_premium": 100_000})
    assert r.engine_name == "esg_remediation"


def test_ES20_carbon_credit_only_low_confidence():
    """ES20: single component (carbon_credit_value) → low confidence."""
    r = engine_e.calculate({"carbon_credit_value": 300_000})
    assert r.confidence == "low"
    assert r.metadata["components_supplied"] == 1
