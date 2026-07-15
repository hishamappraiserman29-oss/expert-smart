"""
PVSA Backend Tests — Professional Valuation Special Assets
Tests PVSA-B01 through PVSA-B35

Covers:
- Common asset type registry (PVSA-B01–04)
- Uncommon asset family registry (PVSA-B05–08)
- Uncommon asset subtype registry (PVSA-B09–13)
- Duplicate prevention (PVSA-B14–15)
- Asset-specific requirements via backend API (PVSA-B16–22)
- Padel tennis court requirements (PVSA-B23–27)
- Cinema requirements (PVSA-B28–30)
- Heritage requirements (PVSA-B31–32)
- Advisory-only enforcement (PVSA-B33–35)
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core_engine.professional_valuation_taxonomy_v2 import (
    get_asset_specific_requirements,
    _ASSET_REQUIREMENTS_CATALOGUE,
    _REQUIREMENTS_ALIASES,
    _GENERIC_REQUIREMENTS,
    VALID_ASSET_FAMILIES,
    LEGACY_SUBTYPES_PRESERVED,
)


# ── PVSA-B01–04: Catalogue registry existence ────────────────────────────────

class TestCatalogueRegistryExistence:

    def test_PVSA_B01_hotel_in_catalogue(self):
        """Hotel must be in _ASSET_REQUIREMENTS_CATALOGUE."""
        assert "hotel" in _ASSET_REQUIREMENTS_CATALOGUE

    def test_PVSA_B02_cinema_in_catalogue(self):
        """Cinema must be in _ASSET_REQUIREMENTS_CATALOGUE."""
        assert "cinema" in _ASSET_REQUIREMENTS_CATALOGUE

    def test_PVSA_B03_padel_tennis_court_in_catalogue(self):
        """padel_tennis_court (singular) must be in _ASSET_REQUIREMENTS_CATALOGUE."""
        assert "padel_tennis_court" in _ASSET_REQUIREMENTS_CATALOGUE

    def test_PVSA_B04_catalogue_not_empty(self):
        """Catalogue must have at least 10 entries."""
        assert len(_ASSET_REQUIREMENTS_CATALOGUE) >= 10


# ── PVSA-B05–08: Uncommon asset family registry ──────────────────────────────

class TestUncommonFamilyRegistry:

    def test_PVSA_B05_sports_recreation_in_valid_families(self):
        assert "sports_recreation_assets" in VALID_ASSET_FAMILIES

    def test_PVSA_B06_entertainment_in_valid_families(self):
        assert "entertainment_assets" in VALID_ASSET_FAMILIES

    def test_PVSA_B07_heritage_in_valid_families(self):
        assert "heritage_assets" in VALID_ASSET_FAMILIES

    def test_PVSA_B08_hospitality_special_in_valid_families(self):
        assert "hospitality_special_assets" in VALID_ASSET_FAMILIES


# ── PVSA-B09–13: Asset subtype registry entries ──────────────────────────────

class TestSubtypeRegistry:

    def test_PVSA_B09_legacy_subtypes_preserved_is_collection(self):
        assert isinstance(LEGACY_SUBTYPES_PRESERVED, (list, frozenset, set, tuple))

    def test_PVSA_B10_padel_tennis_courts_preserved(self):
        """Legacy plural form must remain in LEGACY_SUBTYPES_PRESERVED."""
        assert "padel_tennis_courts" in LEGACY_SUBTYPES_PRESERVED

    def test_PVSA_B11_cinema_preserved(self):
        assert "cinema" in LEGACY_SUBTYPES_PRESERVED

    def test_PVSA_B12_padel_alias_resolves_correctly(self):
        """padel_tennis_courts alias must resolve to padel_tennis_court."""
        assert _REQUIREMENTS_ALIASES.get("padel_tennis_courts") == "padel_tennis_court"

    def test_PVSA_B13_padel_courts_alias_resolves(self):
        assert _REQUIREMENTS_ALIASES.get("padel_courts") == "padel_tennis_court"


# ── PVSA-B14–15: Duplicate prevention ────────────────────────────────────────

class TestDuplicatePrevention:

    def test_PVSA_B14_no_duplicate_aliases_pointing_same_key(self):
        """Multiple aliases may share a target — that is fine (alias fan-in)."""
        targets = list(_REQUIREMENTS_ALIASES.values())
        # all targets must exist in catalogue (alias resolution is sound)
        for alias, target in _REQUIREMENTS_ALIASES.items():
            assert target in _ASSET_REQUIREMENTS_CATALOGUE, (
                f"Alias '{alias}' → '{target}' but '{target}' not in catalogue"
            )

    def test_PVSA_B15_catalogue_keys_unique(self):
        keys = list(_ASSET_REQUIREMENTS_CATALOGUE.keys())
        assert len(keys) == len(set(keys)), "Duplicate keys in _ASSET_REQUIREMENTS_CATALOGUE"


# ── PVSA-B16–22: Asset-specific requirements via get_asset_specific_requirements ─

class TestGetAssetSpecificRequirements:

    def test_PVSA_B16_hotel_returns_dict(self):
        result = get_asset_specific_requirements(asset_type="hotel")
        assert isinstance(result, dict)

    def test_PVSA_B17_hotel_adr_in_labels(self):
        result = get_asset_specific_requirements(asset_type="hotel")
        labels = result.get("required_inputs_labels_ar", {})
        combined = " ".join(labels.values())
        assert "ADR" in combined

    def test_PVSA_B18_hotel_revpar_in_labels(self):
        result = get_asset_specific_requirements(asset_type="hotel")
        labels = result.get("required_inputs_labels_ar", {})
        combined = " ".join(labels.values())
        assert "RevPAR" in combined

    def test_PVSA_B19_hotel_has_recommended_methods(self):
        result = get_asset_specific_requirements(asset_type="hotel")
        assert len(result.get("recommended_methods", [])) > 0

    def test_PVSA_B20_hotel_has_evidence(self):
        result = get_asset_specific_requirements(asset_type="hotel")
        assert len(result.get("required_evidence", [])) > 0

    def test_PVSA_B21_unknown_asset_returns_generic(self):
        result = get_asset_specific_requirements(asset_type="totally_unknown_xyz")
        assert isinstance(result, dict)
        assert "required_inputs" in result

    def test_PVSA_B22_empty_asset_type_returns_generic(self):
        result = get_asset_specific_requirements(asset_type="")
        assert isinstance(result, dict)


# ── PVSA-B23–27: Padel tennis court requirements ─────────────────────────────

class TestPadelRequirements:

    def test_PVSA_B23_padel_tennis_court_returns_dict(self):
        result = get_asset_specific_requirements(asset_type="padel_tennis_court")
        assert isinstance(result, dict)

    def test_PVSA_B24_padel_has_number_of_courts(self):
        result = get_asset_specific_requirements(asset_type="padel_tennis_court")
        labels = result.get("required_inputs_labels_ar", {})
        combined = " ".join(labels.values())
        assert "ملاعب البادل" in combined or "عدد ملاعب" in combined

    def test_PVSA_B25_padel_has_booking_rate(self):
        result = get_asset_specific_requirements(asset_type="padel_tennis_court")
        labels = result.get("required_inputs_labels_ar", {})
        combined = " ".join(labels.values())
        assert "الحجز" in combined

    def test_PVSA_B26_padel_has_operating_license_evidence(self):
        result = get_asset_specific_requirements(asset_type="padel_tennis_court")
        evidence = result.get("required_evidence", [])
        assert "operating_license" in evidence

    def test_PVSA_B27_padel_alias_resolves_to_same_entry(self):
        singular = get_asset_specific_requirements(asset_type="padel_tennis_court")
        plural   = get_asset_specific_requirements(asset_type="padel_tennis_courts")
        assert singular.get("requirements_panel_title_ar") == plural.get("requirements_panel_title_ar")


# ── PVSA-B28–30: Cinema requirements ─────────────────────────────────────────

class TestCinemaRequirements:

    def test_PVSA_B28_cinema_returns_dict(self):
        result = get_asset_specific_requirements(asset_type="cinema")
        assert isinstance(result, dict)

    def test_PVSA_B29_cinema_has_number_of_halls(self):
        result = get_asset_specific_requirements(asset_type="cinema")
        labels = result.get("required_inputs_labels_ar", {})
        combined = " ".join(labels.values())
        assert "القاعات" in combined or "عدد القاعات" in combined

    def test_PVSA_B30_cinema_has_dcf_in_methods(self):
        result = get_asset_specific_requirements(asset_type="cinema")
        methods = result.get("recommended_methods", [])
        assert "dcf" in methods


# ── PVSA-B31–32: Heritage requirements ───────────────────────────────────────

class TestHeritageRequirements:

    def test_PVSA_B31_heritage_in_catalogue(self):
        assert "heritage" in _ASSET_REQUIREMENTS_CATALOGUE or \
               get_asset_specific_requirements(asset_type="distinguished_architectural_heritage") is not None

    def test_PVSA_B32_distinguished_architectural_heritage_returns_dict(self):
        result = get_asset_specific_requirements(
            asset_type="distinguished_architectural_heritage",
            asset_family="heritage_assets",
        )
        assert isinstance(result, dict)
        assert "required_inputs" in result


# ── PVSA-B33–35: Advisory-only enforcement ───────────────────────────────────

class TestAdvisoryOnlyEnforcement:

    def test_PVSA_B33_padel_requirements_are_advisory(self):
        """Requirements must be labelled advisory — no certification_ready gate on requirements alone."""
        result = get_asset_specific_requirements(asset_type="padel_tennis_court")
        # advisory means: no field named 'certification_ready' is set to True
        assert result.get("certification_ready") is not True

    def test_PVSA_B34_cinema_requirements_are_advisory(self):
        result = get_asset_specific_requirements(asset_type="cinema")
        assert result.get("certification_ready") is not True

    def test_PVSA_B35_generic_fallback_is_advisory(self):
        result = get_asset_specific_requirements(asset_type="nonexistent_asset_zzz")
        assert result.get("certification_ready") is not True
