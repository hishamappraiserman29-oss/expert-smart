"""
Composite reporting — Wave 7B. Builds USPAP/IAAO-aware reporting blocks
by aggregating the per-component markers that PurposeAdapter already
produces. Renders/aggregates; never re-derives standards logic and
never computes COD/PRD.

Pure module: no Flask, no DB, no side effects.
"""
from __future__ import annotations

from typing import Sequence

from adapters.purpose_adapter import AdjustedValuation

_USPAP_NOTE = (
    "USPAP-aware reporting markers, aggregated from per-component standards "
    "produced by PurposeAdapter. Not a certified compliance statement."
)
_IAAO_NOTE = (
    "COD/PRD are mass-appraisal population statistics requiring a "
    "sales-ratio dataset; the composite endpoint accepts none, so they are "
    "not computed. IAAO-style statistical support markers only — "
    "not a certified compliance statement."
)
_MASS_APPRAISAL_STANDARDS = frozenset(("Standard 5", "Standard 6"))


def build_reporting_blocks(valuations: Sequence[AdjustedValuation]) -> dict:
    """Return {"uspap_reporting": {...}, "iaao_reporting": {...}}.

    Aggregates per-component AdjustedValuation markers:
      - uspap_standards (tuple)  -> sorted union
      - iaao_block_triggered     -> count
      - deep_route_deferred      -> count

    Deterministic: same input → identical output.
    """
    components_count = len(valuations)
    all_standards: set[str] = set()
    iaao_count = 0
    deep_count = 0

    for av in valuations:
        all_standards.update(av.uspap_standards)
        if av.iaao_block_triggered:
            iaao_count += 1
        if av.deep_route_deferred:
            deep_count += 1

    standards_sorted = sorted(all_standards)
    mass_present = bool(all_standards & _MASS_APPRAISAL_STANDARDS)

    return {
        "uspap_reporting": {
            "standards_applied": standards_sorted,
            "mass_appraisal_standards_present": mass_present,
            "components_count": components_count,
            "note": _USPAP_NOTE,
        },
        "iaao_reporting": {
            "iaao_triggered_count": iaao_count,
            "deep_routes_deferred_count": deep_count,
            "cod": None,
            "prd": None,
            "ratio_study_status": "not_computed",
            "note": _IAAO_NOTE,
        },
    }
