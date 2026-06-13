"""
Asset Families Registry — Phase 6 (METADATA ONLY).

Organises specialised real-estate asset types into nine logical families,
each with subtypes and a valuation profile specification.

⚠️  METADATA ONLY — no valuation engines are built here.
    ValuationProfileSpec.profile_fields lists the data-point *names* that
    a future engine would need; no FieldSpec objects, no required/optional
    flags, and no validation logic exist in this module.

Relationship to valuation_requirements.py
-----------------------------------------
The three *core legacy* asset types — residential · commercial · land —
are handled exclusively by valuation_requirements.py and the Requirements
Matrix.  They deliberately do NOT appear in this registry.

Frontend / E2E code alignment (Phase 6 notes)
---------------------------------------------
Subtype IDs that match existing frontend option values exactly:
  heritage_property      ← `#asset-type option[value="heritage_property"]`
  architectural_heritage ← `#asset-type option[value="architectural_heritage"]`
  prefabricated_factory  ← `#asset-type option[value="prefabricated_factory"]`

Frontend-only codes NOT yet represented in the 9 families:
  data_center   → nearest family: tech_energy_infrastructure (alias candidate Ph-7)
  cold_storage  → nearest family: advanced_industrial_logistics (alias candidate Ph-7)

No renaming of existing frontend codes is performed here.

Usage
-----
    from adapters.asset_families import (
        list_asset_families,
        get_asset_family,
        list_asset_subtypes,
        get_asset_subtype_profile,
        resolve_asset_family_for_subtype,
        is_supported_asset_family,
        is_supported_asset_subtype,
    )
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ValuationProfileSpec:
    """Metadata-only valuation profile for an asset subtype.

    profile_fields
        Ordered tuple of data-point names that a future valuation engine
        would collect for this subtype.  Names only — no types, no
        validation, no engine logic.
    """
    profile_fields: tuple[str, ...]


@dataclass(frozen=True)
class AssetSubtype:
    """A single asset subtype within a family.

    subtype_id  Unique snake_case identifier (globally unique across all families).
    display_ar  Arabic display name.
    family_id   Parent family identifier.
    profile     Metadata-only valuation profile for this subtype.
    """
    subtype_id: str
    display_ar: str
    family_id:  str
    profile:    ValuationProfileSpec


@dataclass(frozen=True)
class AssetFamily:
    """A logical grouping of related asset subtypes.

    family_id   Unique snake_case identifier.
    display_ar  Arabic display name for the family.
    subtypes    Tuple of AssetSubtype instances belonging to this family.
    """
    family_id:  str
    display_ar: str
    subtypes:   tuple[AssetSubtype, ...]


# ── Shared profile field sets (reused across subtypes) ───────────────────────

_HOSPITALITY_PROFILE = ValuationProfileSpec((
    "annual_footfall",
    "ticket_revenue",
    "occupancy_rate",
    "average_spend_per_head",
    "operating_days_per_year",
    "safety_certifications",
    "maintenance_contracts",
))

_SPORTS_PROFILE = ValuationProfileSpec((
    "licensed_capacity",
    "event_days_per_year",
    "peak_utilization_rate",
    "membership_or_booking_revenue",
    "sponsorship_revenue",
    "maintenance_cost",
    "lighting_standard",
    "safety_license",
))

_INDUSTRIAL_LOGISTICS_PROFILE = ValuationProfileSpec((
    "gross_area",
    "operational_capacity",
    "occupancy_rate",
    "access_quality",
    "structural_capacity",
    "operating_cost",
    "licensing_status",
))

_TECH_ENERGY_PROFILE = ValuationProfileSpec((
    "long_term_lease_duration",
    "annual_escalation",
    "grid_or_network_connection",
    "tenant_quality",
    "remaining_contract_term",
))

_MEDICAL_SCIENCE_PROFILE = ValuationProfileSpec((
    "technical_fitout_cost",
    "specialized_hvac",
    "backup_power_system",
    "compliance_certifications",
    "biohazard_management",
    "operational_risk_score",
))

_AGRI_ENV_PROFILE = ValuationProfileSpec((
    "production_capacity",
    "water_consumption",
    "energy_consumption",
    "offtake_contracts",
    "climate_control_system",
    "yield_per_cycle",
))

_UNDERGROUND_PROFILE = ValuationProfileSpec((
    "geotechnical_stability",
    "emergency_exits_count",
    "forced_ventilation_system",
    "civil_defense_approval",
    "adaptive_reuse_potential",
    "security_level",
))

_CEMETERY_PROFILE = ValuationProfileSpec((
    "remaining_plot_capacity",
    "plot_sales_rate",
    "perpetual_care_fund",
    "maintenance_obligation",
    "religious_or_municipal_license",
))

_HERITAGE_PROFILE = ValuationProfileSpec((
    "heritage_grade",
    "alteration_restrictions",
    "reproduction_cost",
    "historical_value_coefficient",
    "functional_obsolescence_heritage",
    "restoration_opex",
    "trade_off_coefficient",
    "restricted_cash_flow_duration",
    "surrounding_cultural_flow",
    "social_utility_index",
))


# ── Family 1 — Hospitality & Entertainment ────────────────────────────────────

_FAMILY_HOSPITALITY = AssetFamily(
    family_id  = "hospitality_entertainment",
    display_ar = "الضيافة والترفيه والسياحة",
    subtypes   = (
        AssetSubtype("hotel",          "فندق",          "hospitality_entertainment", _HOSPITALITY_PROFILE),
        AssetSubtype("cinema",         "سينما",         "hospitality_entertainment", _HOSPITALITY_PROFILE),
        AssetSubtype("theater",        "مسرح",          "hospitality_entertainment", _HOSPITALITY_PROFILE),
        AssetSubtype("opera_house",    "دار أوبرا",     "hospitality_entertainment", _HOSPITALITY_PROFILE),
        AssetSubtype("theme_park",     "مدينة ألعاب",   "hospitality_entertainment", _HOSPITALITY_PROFILE),
        AssetSubtype("indoor_ski_slope","منحدر تزلج مغطى","hospitality_entertainment", _HOSPITALITY_PROFILE),
        AssetSubtype("casino",         "كازينو",        "hospitality_entertainment", _HOSPITALITY_PROFILE),
    ),
)


# ── Family 2 — Sports & Event Venues ─────────────────────────────────────────

_FAMILY_SPORTS = AssetFamily(
    family_id  = "sports_event_venues",
    display_ar = "الملاعب وقاعات الفعاليات الرياضية",
    subtypes   = (
        AssetSubtype("stadium",             "ملعب رياضي",       "sports_event_venues", _SPORTS_PROFILE),
        AssetSubtype("indoor_arena",        "قاعة مغلقة",       "sports_event_venues", _SPORTS_PROFILE),
        AssetSubtype("padel_tennis_courts", "ملاعب بادل تنس",   "sports_event_venues", _SPORTS_PROFILE),
        AssetSubtype("squash_courts",       "ملاعب إسكواش",     "sports_event_venues", _SPORTS_PROFILE),
        AssetSubtype("racecourse",          "ميدان سباق خيل",   "sports_event_venues", _SPORTS_PROFILE),
        AssetSubtype("motorsport_circuit",  "حلبة سباق سيارات", "sports_event_venues", _SPORTS_PROFILE),
        AssetSubtype("golf_course",         "ملعب جولف",        "sports_event_venues", _SPORTS_PROFILE),
    ),
)


# ── Family 3 — Advanced Industrial & Logistics ───────────────────────────────

_FAMILY_INDUSTRIAL = AssetFamily(
    family_id  = "advanced_industrial_logistics",
    display_ar = "الصناعي والخدمات اللوجستية",
    subtypes   = (
        AssetSubtype("industrial",           "صناعي",              "advanced_industrial_logistics", _INDUSTRIAL_LOGISTICS_PROFILE),
        AssetSubtype("prefabricated_factory","مصنع جاهز",          "advanced_industrial_logistics", _INDUSTRIAL_LOGISTICS_PROFILE),
        AssetSubtype("self_storage",         "مخازن التخزين الذاتي","advanced_industrial_logistics", _INDUSTRIAL_LOGISTICS_PROFILE),
        AssetSubtype("container_yard",       "ساحة حاويات",         "advanced_industrial_logistics", _INDUSTRIAL_LOGISTICS_PROFILE),
        AssetSubtype("parking_structure",    "مبنى مواقف سيارات",   "advanced_industrial_logistics", _INDUSTRIAL_LOGISTICS_PROFILE),
    ),
)


# ── Family 4 — Tech & Energy Infrastructure ──────────────────────────────────

_FAMILY_TECH_ENERGY = AssetFamily(
    family_id  = "tech_energy_infrastructure",
    display_ar = "البنية التحتية التقنية والطاقة",
    subtypes   = (
        AssetSubtype("telecom_tower", "برج اتصالات", "tech_energy_infrastructure", _TECH_ENERGY_PROFILE),
        AssetSubtype("solar_farm",    "مزرعة طاقة شمسية", "tech_energy_infrastructure", _TECH_ENERGY_PROFILE),
    ),
)


# ── Family 5 — Specialized Medical & Science ─────────────────────────────────

_FAMILY_MEDICAL = AssetFamily(
    family_id  = "specialized_medical_science",
    display_ar = "الطبي والعلمي المتخصص",
    subtypes   = (
        AssetSubtype("hospital",          "مستشفى",            "specialized_medical_science", _MEDICAL_SCIENCE_PROFILE),
        AssetSubtype("school",            "مدرسة",             "specialized_medical_science", _MEDICAL_SCIENCE_PROFILE),
        AssetSubtype("life_sciences_lab", "مختبر علوم الحياة", "specialized_medical_science", _MEDICAL_SCIENCE_PROFILE),
        AssetSubtype("bio_bank",          "بنك بيولوجي",       "specialized_medical_science", _MEDICAL_SCIENCE_PROFILE),
    ),
)


# ── Family 6 — Agri & Environmental Assets ───────────────────────────────────

_FAMILY_AGRI = AssetFamily(
    family_id  = "agri_environmental_assets",
    display_ar = "الأصول الزراعية والبيئية",
    subtypes   = (
        AssetSubtype("agtech_hydroponic", "زراعة هيدروبونيك تقنية", "agri_environmental_assets", _AGRI_ENV_PROFILE),
        AssetSubtype("greenhouse",        "بيت زجاجي",               "agri_environmental_assets", _AGRI_ENV_PROFILE),
        AssetSubtype("smart_farm",        "مزرعة ذكية",              "agri_environmental_assets", _AGRI_ENV_PROFILE),
    ),
)


# ── Family 7 — Underground & Special Assets ──────────────────────────────────

_FAMILY_UNDERGROUND = AssetFamily(
    family_id  = "underground_special_assets",
    display_ar = "الأصول تحت الأرض والخاصة",
    subtypes   = (
        AssetSubtype("repurposed_cave",   "كهف معاد توظيفه", "underground_special_assets", _UNDERGROUND_PROFILE),
        AssetSubtype("underground_bunker","ملجأ تحت الأرض",   "underground_special_assets", _UNDERGROUND_PROFILE),
    ),
)


# ── Family 8 — Cemetery & Memorial Assets ────────────────────────────────────

_FAMILY_CEMETERY = AssetFamily(
    family_id  = "cemetery_memorial_assets",
    display_ar = "المقابر والنصب التذكارية",
    subtypes   = (
        AssetSubtype("cemetery",      "مقبرة",         "cemetery_memorial_assets", _CEMETERY_PROFILE),
        AssetSubtype("memorial_park", "حديقة تذكارية", "cemetery_memorial_assets", _CEMETERY_PROFILE),
    ),
)


# ── Family 9 — Heritage & Cultural Assets ────────────────────────────────────

_FAMILY_HERITAGE = AssetFamily(
    family_id  = "heritage_cultural_assets",
    display_ar = "الأصول التراثية والثقافية",
    subtypes   = (
        AssetSubtype("heritage_property",        "عقار تراثي",               "heritage_cultural_assets", _HERITAGE_PROFILE),
        AssetSubtype("architectural_heritage",   "تراث معماري",              "heritage_cultural_assets", _HERITAGE_PROFILE),
        AssetSubtype("cultural_landmark",        "معلم ثقافي",               "heritage_cultural_assets", _HERITAGE_PROFILE),
        AssetSubtype("adaptive_reuse_heritage",  "إعادة توظيف تراثي",        "heritage_cultural_assets", _HERITAGE_PROFILE),
    ),
)


# ── Registry ──────────────────────────────────────────────────────────────────

_ALL_FAMILIES: tuple[AssetFamily, ...] = (
    _FAMILY_HOSPITALITY,
    _FAMILY_SPORTS,
    _FAMILY_INDUSTRIAL,
    _FAMILY_TECH_ENERGY,
    _FAMILY_MEDICAL,
    _FAMILY_AGRI,
    _FAMILY_UNDERGROUND,
    _FAMILY_CEMETERY,
    _FAMILY_HERITAGE,
)

# O(1) lookup indices built at import time
ASSET_FAMILIES_REGISTRY: dict[str, AssetFamily] = {
    f.family_id: f for f in _ALL_FAMILIES
}

ASSET_SUBTYPES_INDEX: dict[str, AssetSubtype] = {
    st.subtype_id: st
    for fam in _ALL_FAMILIES
    for st in fam.subtypes
}

# Core legacy types managed by valuation_requirements.py — NOT in this registry
LEGACY_CORE_ASSET_TYPES: frozenset[str] = frozenset({
    "residential",
    "commercial",
    "land",
})

# Future alias candidates (frontend-only codes not yet mapped to a family)
# data_center   → nearest: tech_energy_infrastructure  (Phase 7 candidate)
# cold_storage  → nearest: advanced_industrial_logistics (Phase 7 candidate)
_FRONTEND_ALIAS_CANDIDATES: dict[str, str] = {
    "data_center":  "tech_energy_infrastructure",
    "cold_storage": "advanced_industrial_logistics",
}


# ── Public API ────────────────────────────────────────────────────────────────

def list_asset_families() -> list[AssetFamily]:
    """Return all asset families sorted by family_id."""
    return sorted(ASSET_FAMILIES_REGISTRY.values(), key=lambda f: f.family_id)


def get_asset_family(family_id: str) -> AssetFamily:
    """Return the AssetFamily for *family_id*.

    Raises
    ------
    ValueError
        If family_id is not in the registry.
    """
    entry = ASSET_FAMILIES_REGISTRY.get(family_id)
    if entry is None:
        raise ValueError(
            f"Unknown asset family {family_id!r}. "
            f"Valid families: {sorted(ASSET_FAMILIES_REGISTRY)}"
        )
    return entry


def list_asset_subtypes(family_id: str) -> list[AssetSubtype]:
    """Return subtypes for *family_id* sorted by subtype_id.

    Raises
    ------
    ValueError
        If family_id is not in the registry.
    """
    return sorted(get_asset_family(family_id).subtypes, key=lambda s: s.subtype_id)


def get_asset_subtype_profile(subtype_id: str) -> ValuationProfileSpec:
    """Return the ValuationProfileSpec for *subtype_id*.

    Raises
    ------
    ValueError
        If subtype_id is not in the index.
    """
    entry = ASSET_SUBTYPES_INDEX.get(subtype_id)
    if entry is None:
        raise ValueError(
            f"Unknown asset subtype {subtype_id!r}. "
            f"Valid subtypes: {sorted(ASSET_SUBTYPES_INDEX)}"
        )
    return entry.profile


def resolve_asset_family_for_subtype(subtype_id: str) -> str:
    """Return the family_id that owns *subtype_id*.

    Raises
    ------
    ValueError
        If subtype_id is not in the index.
    """
    entry = ASSET_SUBTYPES_INDEX.get(subtype_id)
    if entry is None:
        raise ValueError(
            f"Unknown asset subtype {subtype_id!r}. "
            f"Valid subtypes: {sorted(ASSET_SUBTYPES_INDEX)}"
        )
    return entry.family_id


def is_supported_asset_family(family_id: str) -> bool:
    """Return True if *family_id* is a recognised specialised family."""
    return family_id in ASSET_FAMILIES_REGISTRY


def is_supported_asset_subtype(subtype_id: str) -> bool:
    """Return True if *subtype_id* is a recognised asset subtype."""
    return subtype_id in ASSET_SUBTYPES_INDEX
