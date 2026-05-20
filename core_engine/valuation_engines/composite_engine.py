"""
Composite Property Engine — per-component baseline valuation.

Wave 1 of the Composite Property Architecture. Processes a list of
asset components, validates each against its asset-type schema, and
computes a BASELINE mechanical value per component.

This engine does NOT apply valuation-purpose adjustments (that is the
PurposeComplianceAdapter — Wave 2) and does NOT aggregate or apply
synergy (Wave 7). Each component is valued in isolation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


# ─────────────────────────────────────────────────────────────────────
# Asset type registry — 15 types (14 original + المطارات والموانئ)
# ─────────────────────────────────────────────────────────────────────

ASSET_TYPES: dict[str, dict[str, type]] = {
    "وحدة سكنية (شقة / فيلا)": {
        "bedrooms_count": int,
        "floor_number": int,
    },
    "عقار كامل (عمارة / مجمع سكني)": {
        "building_age": int,
        "total_floors": int,
    },
    "سكني / تجاري / إداري (مباني قائمة)": {
        "office_count": int,
        "elevator_count": int,
    },
    "أرض فضاء (مطورة / خام)": {
        "zoning_type": str,
        "frontage_meters": float,
    },
    "صناعي / مستودع / لوجستي": {
        "clear_height_meters": float,
        "floor_load_capacity_ton_sqm": float,
        "power_capacity_kva": float,
    },
    "أرض زراعية": {
        "water_source": str,
        "crop_type": str,
    },
    "فنادق ومنتجعات سياحية": {
        "room_count": int,
        "average_daily_rate_adr": float,
        "occupancy_rate_percent": float,
        "revpar": float,
    },
    "تجزئة (محلات / مولات)": {
        "shop_count": int,
        "frontage_meters": float,
    },
    "أصول متخصصة: مستشفيات ومراكز طبية": {
        "bed_count": int,
        "operating_rooms_count": int,
        "medical_classification": str,
    },
    "أصول متخصصة: مدارس ومرافق تعليمية": {
        "classroom_count": int,
        "student_capacity": int,
    },
    "أصول عقارية مرتبطة بأصول معنوية": {
        "goodwill_value": float,
    },
    "المصالح والملكيات الجزئية (Partial Interests)": {
        "ownership_share_percent": float,
    },
    "مناجم وآبار (بترول / غاز/ مياه / ذهب)": {
        "proven_reserves_volume": float,
        "daily_production_rate": float,
        "extraction_cost_per_unit": float,
    },
    "استثمارات تحت الإنشاء (Investments Under Construction)": {
        "completion_percent": float,
        "estimated_cost_to_complete": float,
    },
    # ═══ NEW (Wave 1) ═══
    "المطارات والموانئ": {
        "facility_subtype": str,              # "مطار" | "ميناء"
        "annual_throughput": float,           # ركاب/سنة (مطار) أو TEU/سنة (ميناء)
        "berth_or_runway_count": int,         # عدد الأرصفة (ميناء) أو المدارج (مطار)
        "concession_years_remaining": float,  # سنوات الامتياز المتبقّية
    },
}


@dataclass(frozen=True)
class ComponentValuation:
    """Result of valuing a single component (baseline only)."""

    component_id: Any
    name: str
    asset_type: str
    area_sqm: float
    baseline_value: float
    method: str
    notes: tuple[str, ...] = field(default_factory=tuple)


class CompositeEngineError(Exception):
    """Raised for invalid component structure or unknown asset type."""


class CompositeEngine:
    """Processes asset components into baseline valuations."""

    def __init__(self, *, default_rate_per_sqm: float = 1.0) -> None:
        self._default_rate = default_rate_per_sqm

    # ── Validation ───────────────────────────────────────────────────

    def _validate_component(self, component: Mapping[str, Any]) -> None:
        asset_type = component.get("asset_type")
        if asset_type not in ASSET_TYPES:
            raise CompositeEngineError(
                f"Unknown asset_type {asset_type!r}. "
                f"Valid types: {sorted(ASSET_TYPES.keys())}"
            )
        if not isinstance(component.get("area_sqm"), (int, float)):
            raise CompositeEngineError(
                f"component {component.get('id')!r}: area_sqm must be numeric"
            )
        spec = component.get("specific_attributes") or {}
        for attr_name, attr_type in ASSET_TYPES[asset_type].items():
            if attr_name not in spec:
                raise CompositeEngineError(
                    f"component {component.get('id')!r} ({asset_type}): "
                    f"missing required attribute '{attr_name}'"
                )
            val = spec[attr_name]
            if attr_type in (int, float) and not isinstance(val, (int, float)):
                raise CompositeEngineError(
                    f"component {component.get('id')!r}: "
                    f"'{attr_name}' must be {attr_type.__name__}, got {type(val).__name__}"
                )
            if attr_type is str and not isinstance(val, str):
                raise CompositeEngineError(
                    f"component {component.get('id')!r}: "
                    f"'{attr_name}' must be str"
                )

    # ── Baseline calculation ─────────────────────────────────────────

    def _baseline(
        self, component: Mapping[str, Any]
    ) -> tuple[float, str, list[str]]:
        """Return (baseline_value, method, notes).

        Wave 1 baseline is mechanical. Deep domain math (DCF, concession
        modelling, reserve depletion) is intentionally deferred and flagged.
        """
        asset_type = component["asset_type"]
        area = float(component["area_sqm"])
        spec = component.get("specific_attributes") or {}
        rate = float(component.get("base_rate_per_sqm", self._default_rate))
        notes: list[str] = []

        value = area * rate
        method = "area_rate"

        if asset_type == "فنادق ومنتجعات سياحية":
            revpar = float(spec.get("revpar", 0))
            rooms = float(spec.get("room_count", 0))
            if revpar > 0 and rooms > 0:
                value = revpar * rooms * 365.0
                method = "income_revpar_baseline"
                notes.append(
                    "NOTE: RevPAR baseline only — full income-approach "
                    "(cap rate / DCF) deferred to domain review"
                )

        elif asset_type == "المطارات والموانئ":
            method = "infrastructure_baseline"
            notes.append(
                "NOTE: Airport/seaport valuation is concession-based DCF — "
                "Wave 1 returns area×rate placeholder only. Full concession "
                "cashflow model + domain expert (د. عبد الرؤوف) review required "
                "before any client-facing use."
            )

        elif asset_type == "مناجم وآبار (بترول / غاز/ مياه / ذهب)":
            notes.append(
                "NOTE: Reserve-depletion / extraction-cost model deferred — "
                "baseline area×rate is a placeholder only"
            )

        elif asset_type == "أصول عقارية مرتبطة بأصول معنوية":
            goodwill = float(spec.get("goodwill_value", 0))
            value = value + goodwill
            method = "area_rate_plus_goodwill"

        elif asset_type == "المصالح والملكيات الجزئية (Partial Interests)":
            share = float(spec.get("ownership_share_percent", 100)) / 100.0
            value = value * share
            method = "area_rate_partial_share"

        elif asset_type == "استثمارات تحت الإنشاء (Investments Under Construction)":
            completion = float(spec.get("completion_percent", 0)) / 100.0
            value = value * completion
            method = "area_rate_completion_weighted"
            notes.append(
                "NOTE: Under-construction value weighted by completion% — "
                "cost-to-complete not deducted in baseline"
            )

        return value, method, notes

    # ── Public API ───────────────────────────────────────────────────

    def value_component(self, component: Mapping[str, Any]) -> ComponentValuation:
        """Validate + compute baseline for one component."""
        self._validate_component(component)
        value, method, notes = self._baseline(component)
        return ComponentValuation(
            component_id=component.get("id"),
            name=str(component.get("name", "")),
            asset_type=component["asset_type"],
            area_sqm=float(component["area_sqm"]),
            baseline_value=round(value, 2),
            method=method,
            notes=tuple(notes),
        )

    def value_all(
        self, components: list[Mapping[str, Any]]
    ) -> list[ComponentValuation]:
        """Value every component. Order preserved. Empty list → []."""
        return [self.value_component(c) for c in components]
