"""
Tests for the Asset Families Registry — Phase 6.

Registry safety tests:
  AF01  — exactly 9 required families present with correct IDs
  AF02  — family IDs are globally unique
  AF03  — subtype IDs are globally unique (across all families)
  AF04  — every subtype references an existing family (family_id ∈ registry)
  AF05  — every subtype belongs to exactly one family
  AF06  — every family has at least one subtype
  AF07  — every subtype has a non-empty valuation profile
  AF08  — LEGACY_CORE_ASSET_TYPES contains residential / commercial / land
  AF09  — core legacy types do NOT appear in the families registry
  AF10  — core legacy types do NOT appear as subtypes
  AF11  — get_asset_family raises ValueError for unknown family_id
  AF12  — get_asset_subtype_profile raises ValueError for unknown subtype_id
  AF13  — resolve_asset_family_for_subtype raises ValueError for unknown subtype_id
  AF14  — list_asset_families returns all 9 families sorted
  AF15  — list_asset_subtypes returns correct subtypes sorted for a family
  AF16  — is_supported_asset_family: True for known, False for unknown
  AF17  — is_supported_asset_subtype: True for known, False for unknown
  AF18  — frontend alignment: heritage_property / architectural_heritage / prefabricated_factory present
  AF19  — resolve_asset_family_for_subtype returns correct family_id
  AF20  — registry is importable with no backend engines or bridge_api required
  AF21  — profile field names are non-empty strings (no blank entries)
  AF22  — each family's subtypes all reference that same family_id
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pytest

# ── Path setup (mirrors other test modules) ──────────────────────────────────
_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(str(_CORE))

from adapters.asset_families import (  # noqa: E402
    ASSET_FAMILIES_REGISTRY,
    ASSET_SUBTYPES_INDEX,
    LEGACY_CORE_ASSET_TYPES,
    AssetFamily,
    AssetSubtype,
    ValuationProfileSpec,
    get_asset_family,
    get_asset_subtype_profile,
    is_supported_asset_family,
    is_supported_asset_subtype,
    list_asset_families,
    list_asset_subtypes,
    resolve_asset_family_for_subtype,
)

_REQUIRED_FAMILY_IDS: frozenset[str] = frozenset({
    "hospitality_entertainment",
    "sports_event_venues",
    "advanced_industrial_logistics",
    "tech_energy_infrastructure",
    "specialized_medical_science",
    "agri_environmental_assets",
    "underground_special_assets",
    "cemetery_memorial_assets",
    "heritage_cultural_assets",
})


# ── AF01 — All 9 required families present with correct IDs ──────────────────

def test_AF01_all_nine_required_families_present():
    """Exactly the 9 Phase 6 family IDs must exist in the registry."""
    for fid in _REQUIRED_FAMILY_IDS:
        assert fid in ASSET_FAMILIES_REGISTRY, (
            f"Required asset family '{fid}' is missing from ASSET_FAMILIES_REGISTRY"
        )
    assert len(ASSET_FAMILIES_REGISTRY) == 9, (
        f"Expected exactly 9 families, got {len(ASSET_FAMILIES_REGISTRY)}: "
        f"{sorted(ASSET_FAMILIES_REGISTRY)}"
    )


# ── AF02 — Family IDs are globally unique ────────────────────────────────────

def test_AF02_family_ids_are_unique():
    """No two families share the same family_id."""
    ids = [f.family_id for f in ASSET_FAMILIES_REGISTRY.values()]
    assert len(ids) == len(set(ids)), (
        f"Duplicate family_ids detected: {[x for x in ids if ids.count(x) > 1]}"
    )


# ── AF03 — Subtype IDs are globally unique ───────────────────────────────────

def test_AF03_subtype_ids_are_globally_unique():
    """No two subtypes across all families share the same subtype_id."""
    all_ids: list[str] = []
    for fam in ASSET_FAMILIES_REGISTRY.values():
        for st in fam.subtypes:
            all_ids.append(st.subtype_id)
    duplicates = [x for x in all_ids if all_ids.count(x) > 1]
    assert not duplicates, (
        f"Duplicate subtype_ids detected: {sorted(set(duplicates))}"
    )


# ── AF04 — Every subtype references an existing family ───────────────────────

def test_AF04_every_subtype_references_existing_family():
    """Every AssetSubtype.family_id must exist as a key in ASSET_FAMILIES_REGISTRY."""
    for subtype_id, st in ASSET_SUBTYPES_INDEX.items():
        assert st.family_id in ASSET_FAMILIES_REGISTRY, (
            f"Subtype '{subtype_id}' references unknown family_id '{st.family_id}'"
        )


# ── AF05 — Every subtype belongs to exactly one family ───────────────────────

def test_AF05_every_subtype_belongs_to_exactly_one_family():
    """No subtype_id appears in more than one family's subtypes tuple."""
    subtype_to_families: dict[str, list[str]] = {}
    for fam in ASSET_FAMILIES_REGISTRY.values():
        for st in fam.subtypes:
            subtype_to_families.setdefault(st.subtype_id, []).append(fam.family_id)
    multi = {k: v for k, v in subtype_to_families.items() if len(v) > 1}
    assert not multi, (
        f"Subtypes appearing in multiple families: {multi}"
    )


# ── AF06 — Every family has at least one subtype ─────────────────────────────

def test_AF06_every_family_has_at_least_one_subtype():
    """Every AssetFamily must contain at least one AssetSubtype."""
    for fam in ASSET_FAMILIES_REGISTRY.values():
        assert len(fam.subtypes) >= 1, (
            f"Family '{fam.family_id}' has no subtypes"
        )


# ── AF07 — Every subtype has a non-empty valuation profile ───────────────────

def test_AF07_every_subtype_has_nonempty_profile():
    """Every AssetSubtype.profile must contain at least one profile field."""
    for subtype_id, st in ASSET_SUBTYPES_INDEX.items():
        assert isinstance(st.profile, ValuationProfileSpec), (
            f"Subtype '{subtype_id}' profile is not a ValuationProfileSpec"
        )
        assert len(st.profile.profile_fields) >= 1, (
            f"Subtype '{subtype_id}' has an empty profile (no profile fields)"
        )


# ── AF08 — LEGACY_CORE_ASSET_TYPES contains the three core types ─────────────

def test_AF08_legacy_core_asset_types_complete():
    """LEGACY_CORE_ASSET_TYPES must contain residential, commercial, land."""
    for name in ("residential", "commercial", "land"):
        assert name in LEGACY_CORE_ASSET_TYPES, (
            f"'{name}' is missing from LEGACY_CORE_ASSET_TYPES"
        )
    assert len(LEGACY_CORE_ASSET_TYPES) == 3, (
        f"Expected exactly 3 legacy types, got {len(LEGACY_CORE_ASSET_TYPES)}"
    )


# ── AF09 — Core legacy types NOT in families registry ────────────────────────

def test_AF09_core_legacy_types_not_in_families_registry():
    """residential / commercial / land must NOT appear as family_ids."""
    for name in LEGACY_CORE_ASSET_TYPES:
        assert name not in ASSET_FAMILIES_REGISTRY, (
            f"Core legacy type '{name}' must not appear as a family_id "
            f"(it is handled by valuation_requirements.py)"
        )


# ── AF10 — Core legacy types NOT in subtypes index ───────────────────────────

def test_AF10_core_legacy_types_not_as_subtypes():
    """residential / commercial / land must NOT appear as subtype_ids."""
    for name in LEGACY_CORE_ASSET_TYPES:
        assert name not in ASSET_SUBTYPES_INDEX, (
            f"Core legacy type '{name}' must not appear as a subtype_id"
        )


# ── AF11 — get_asset_family raises ValueError for unknown family ──────────────

def test_AF11_get_asset_family_unknown_raises():
    """get_asset_family must raise ValueError for an unrecognised family_id."""
    with pytest.raises(ValueError, match="Unknown asset family"):
        get_asset_family("nonexistent_family_xyz")


# ── AF12 — get_asset_subtype_profile raises ValueError for unknown subtype ───

def test_AF12_get_asset_subtype_profile_unknown_raises():
    """get_asset_subtype_profile must raise ValueError for an unrecognised subtype_id."""
    with pytest.raises(ValueError, match="Unknown asset subtype"):
        get_asset_subtype_profile("nonexistent_subtype_xyz")


# ── AF13 — resolve_asset_family_for_subtype raises ValueError for unknown ────

def test_AF13_resolve_asset_family_unknown_subtype_raises():
    """resolve_asset_family_for_subtype must raise ValueError for unrecognised subtype."""
    with pytest.raises(ValueError, match="Unknown asset subtype"):
        resolve_asset_family_for_subtype("nonexistent_subtype_xyz")


# ── AF14 — list_asset_families returns all 9, sorted ─────────────────────────

def test_AF14_list_asset_families_sorted_and_complete():
    """list_asset_families returns all 9 families sorted by family_id."""
    families = list_asset_families()
    assert len(families) == 9, f"Expected 9 families, got {len(families)}"
    ids = [f.family_id for f in families]
    assert ids == sorted(ids), f"Families not sorted: {ids}"
    for fid in _REQUIRED_FAMILY_IDS:
        assert any(f.family_id == fid for f in families), (
            f"Required family '{fid}' missing from list_asset_families()"
        )


# ── AF15 — list_asset_subtypes returns correct subtypes sorted ───────────────

def test_AF15_list_asset_subtypes_sorted_and_correct():
    """list_asset_subtypes returns subtypes for a family, sorted by subtype_id."""
    subtypes = list_asset_subtypes("hospitality_entertainment")
    ids = [st.subtype_id for st in subtypes]
    assert ids == sorted(ids), f"Subtypes not sorted: {ids}"
    expected = {"hotel", "cinema", "theater", "opera_house",
                "theme_park", "indoor_ski_slope", "casino"}
    assert set(ids) == expected, (
        f"hospitality_entertainment subtypes mismatch. "
        f"Expected: {sorted(expected)}. Got: {sorted(ids)}"
    )
    # All must reference the correct family
    for st in subtypes:
        assert st.family_id == "hospitality_entertainment"


def test_AF15b_list_asset_subtypes_unknown_family_raises():
    """list_asset_subtypes must raise ValueError for unrecognised family_id."""
    with pytest.raises(ValueError, match="Unknown asset family"):
        list_asset_subtypes("nonexistent_family_xyz")


# ── AF16 — is_supported_asset_family ─────────────────────────────────────────

def test_AF16_is_supported_asset_family():
    """is_supported_asset_family returns True for known, False for unknown."""
    assert is_supported_asset_family("hospitality_entertainment") is True
    assert is_supported_asset_family("heritage_cultural_assets") is True
    assert is_supported_asset_family("residential") is False
    assert is_supported_asset_family("unknown_family") is False


# ── AF17 — is_supported_asset_subtype ────────────────────────────────────────

def test_AF17_is_supported_asset_subtype():
    """is_supported_asset_subtype returns True for known, False for unknown."""
    assert is_supported_asset_subtype("hotel") is True
    assert is_supported_asset_subtype("heritage_property") is True
    assert is_supported_asset_subtype("architectural_heritage") is True
    assert is_supported_asset_subtype("residential") is False
    assert is_supported_asset_subtype("unknown_subtype") is False


# ── AF18 — Frontend alignment: key subtype IDs exist ─────────────────────────

def test_AF18_frontend_aligned_subtypes_exist():
    """Subtype IDs matching existing frontend option values must be present."""
    # These match `#asset-type option[value="..."]` in the E2E smoke tests
    frontend_aligned = {
        "heritage_property",
        "architectural_heritage",
        "prefabricated_factory",
        "hotel",
        "hospital",
        "industrial",
    }
    for subtype_id in frontend_aligned:
        assert subtype_id in ASSET_SUBTYPES_INDEX, (
            f"Frontend-aligned subtype '{subtype_id}' is missing from ASSET_SUBTYPES_INDEX"
        )


# ── AF19 — resolve_asset_family_for_subtype correct mappings ────────────────

@pytest.mark.parametrize("subtype_id,expected_family", [
    ("hotel",                  "hospitality_entertainment"),
    ("cinema",                 "hospitality_entertainment"),
    ("stadium",                "sports_event_venues"),
    ("padel_tennis_courts",    "sports_event_venues"),
    ("industrial",             "advanced_industrial_logistics"),
    ("prefabricated_factory",  "advanced_industrial_logistics"),
    ("self_storage",           "advanced_industrial_logistics"),
    ("telecom_tower",          "tech_energy_infrastructure"),
    ("solar_farm",             "tech_energy_infrastructure"),
    ("hospital",               "specialized_medical_science"),
    ("bio_bank",               "specialized_medical_science"),
    ("agtech_hydroponic",      "agri_environmental_assets"),
    ("greenhouse",             "agri_environmental_assets"),
    ("underground_bunker",     "underground_special_assets"),
    ("repurposed_cave",        "underground_special_assets"),
    ("cemetery",               "cemetery_memorial_assets"),
    ("memorial_park",          "cemetery_memorial_assets"),
    ("heritage_property",      "heritage_cultural_assets"),
    ("architectural_heritage", "heritage_cultural_assets"),
    ("cultural_landmark",      "heritage_cultural_assets"),
    ("adaptive_reuse_heritage","heritage_cultural_assets"),
])
def test_AF19_resolve_asset_family_for_subtype(subtype_id, expected_family):
    """resolve_asset_family_for_subtype returns the correct family_id."""
    assert resolve_asset_family_for_subtype(subtype_id) == expected_family, (
        f"resolve_asset_family_for_subtype('{subtype_id}') should return "
        f"'{expected_family}', got '{resolve_asset_family_for_subtype(subtype_id)}'"
    )


# ── AF20 — Registry importable without backend engines ───────────────────────

def test_AF20_registry_importable_without_engines():
    """Importing asset_families must not require any valuation engine or bridge_api."""
    # The import at the top of this file already succeeded without those modules,
    # which proves they are not required.  This test makes the guarantee explicit.
    assert ASSET_FAMILIES_REGISTRY is not None
    assert ASSET_SUBTYPES_INDEX is not None
    assert len(ASSET_FAMILIES_REGISTRY) == 9


# ── AF21 — Profile field names are non-empty strings ─────────────────────────

def test_AF21_profile_field_names_are_nonempty_strings():
    """Every profile field name must be a non-empty, non-whitespace string."""
    for subtype_id, st in ASSET_SUBTYPES_INDEX.items():
        for fname in st.profile.profile_fields:
            assert isinstance(fname, str), (
                f"Subtype '{subtype_id}': profile field {fname!r} is not a string"
            )
            assert fname.strip(), (
                f"Subtype '{subtype_id}': profile field is empty or whitespace: {fname!r}"
            )


# ── AF22 — Each family's subtypes all reference that family ──────────────────

def test_AF22_family_subtypes_reference_parent_family():
    """Every subtype in a family's subtypes tuple must have family_id == that family."""
    for fam in ASSET_FAMILIES_REGISTRY.values():
        for st in fam.subtypes:
            assert st.family_id == fam.family_id, (
                f"Subtype '{st.subtype_id}' in family '{fam.family_id}' "
                f"has mismatched family_id='{st.family_id}'"
            )
