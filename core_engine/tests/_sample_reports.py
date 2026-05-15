"""
Shared sample report DTOs for integration smoke testing.

These mirror the real DTO shape expected by the report engines
(validation / pdf / db). Built from inspecting the actual engine
signatures — NOT assumptions.

Key discoveries from Step 2 API inspection:
  - Valid profile keys: "legacy", "detailed", "professional_template"
    (NOT "professional" — this would be a PROFILE_UNKNOWN ERROR)
  - reconciliation.weights must sum to 100.0 (numeric, ±0.5 tolerance)
  - comparables items need "sale_price" and "area" keys
  - income_approach.vacancy_pct: 0–100 (plain numeric, not 0–1)
  - income_approach.cap_rate: 1–20 (plain numeric percentage)
  - reconciliation.final_value: required > 0 when reconciliation present
  - professional_template: also needs income_approach.discount_rate (1–30)

Reusable by future integration tests and the bridge_api wiring phase.
"""

from __future__ import annotations

from typing import Any


def sample_report_data(profile_key: str = "legacy") -> dict[str, Any]:
    """Return a complete, valid sample report DTO for the given profile.

    Args:
        profile_key: "legacy" / "detailed" / "professional_template".

    Returns:
        A dict with all sub-mappings the engines expect; passes validation
        with zero ERRORs across all three profile types.
    """
    base: dict[str, Any] = {
        "appraiser": {
            "name": "د. عبد الرؤوف محمد عبد الباقي",   # required (ERROR)
            "title": "خبير تقييم عقاري معتمد",
            "firm": "EXPERT_SMART للاستشارات",
            "license": "EG-2026-00471",               # required (WARNING)
            "date": "2026-05-14",                      # required (WARNING)
        },
        "property_info": {
            "address": "القاهرة الجديدة، التجمع الخامس، الحي الأول",
            "type": "سكني",                            # recommended (WARNING)
            "area": 320,                               # required, > 0 (ERROR)
        },
        "valuation_results": {
            "market_value": 2_478_153,                 # required, > 0 (ERROR)
            "price_per_sqm": 7_744,                    # optional (WARNING if ≤ 0)
            "confidence": "عالية",
            "value_words": "مليونان وأربعمائة وثمانية وسبعون ألفاً ومئة وثلاثة وخمسون جنيهاً",
            "primary_approach": "مقارنة البيوع",
        },
        "subject": {
            "address": "القاهرة الجديدة، التجمع الخامس",
            "area": 320,
            "type": "سكني",
        },
        "comparables": [
            {
                "ref": "ع1",
                "address": "التجمع الخامس",
                "sale_price": 2_400_000,               # required, > 0 (ERROR)
                "area": 310,                           # required, > 0 (ERROR)
                "price_per_sqm": 7_741,
                "adjustment_pct": "3%",
                "adjusted_value": 2_472_000,
            },
            {
                "ref": "ع2",
                "address": "الرحاب",
                "sale_price": 2_600_000,               # required, > 0 (ERROR)
                "area": 330,                           # required, > 0 (ERROR)
                "price_per_sqm": 7_878,
                "adjustment_pct": "-2%",
                "adjusted_value": 2_548_000,
            },
        ],
        "cost_approach": {
            "rcn": 1_800_000,                          # required, > 0 (ERROR)
            "depreciation": 270_000,                   # must be ≤ rcn (WARNING)
            "land_value": 900_000,                     # required, > 0 (ERROR)
            "cost_value_indication": 2_430_000,        # optional (WARNING if ≤ 0)
        },
        "income_approach": {
            "gross_income": 240_000,                   # required, > 0 (ERROR)
            "vacancy_pct": 8.0,                        # range 0–100 (WARNING)
            "opex": 60_000,                            # must be ≥ 0 (WARNING)
            "noi": 160_800,
            "cap_rate": 6.5,                           # range 1–20 (WARNING)
            "income_value_indication": 2_473_846,      # optional (WARNING if ≤ 0)
        },
        "reconciliation": {
            # Weights must sum to 100.0 ±0.5 — using plain numeric values.
            "weights": {"sales": 50.0, "cost": 20.0, "income": 30.0},
            "indications": {
                "sales": 2_500_000,
                "cost": 2_430_000,
                "income": 2_473_846,
            },
            "final_value": 2_478_153,                  # required, > 0 (ERROR)
            "final_value_words": "مليونان وأربعمائة وثمانية وسبعون ألفاً",
        },
    }

    # professional_template requires discount_rate in income_approach (WARNING 1–30).
    if profile_key == "professional_template":
        base["income_approach"]["discount_rate"] = 10.0

    return base


def all_profiles() -> tuple[str, ...]:
    """Valid profile keys to exercise in smoke tests.

    Exact strings from _VALID_PROFILES in validation_engine / pdf_engine:
      "legacy", "detailed", "professional_template"
    """
    return ("legacy", "detailed", "professional_template")
