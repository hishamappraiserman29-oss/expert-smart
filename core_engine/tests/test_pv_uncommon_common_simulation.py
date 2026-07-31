"""
Phase UCS — Uncommon Common Simulation: Backend Tests (25 tests)
advisory_only=True — not_real_training
"""
import re
import sys
import pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core_engine.uncommon_common_simulation_context import (
    uncommon_common_simulation_context as CTX,
)

HTML = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

UNCOMMON_KEYS = [
    "petrol_station",
    "hospital",
    "school",
    "cinema_theater",
    "sports_padel_club",
    "architectural_cultural_heritage_detailed",
    "mixed_use_special",
    "hotel",
]

MAPPED_KEYS = [
    "petrol_station",
    "hospital_medical_center",
    "school_university",
    "cinema_theater",
    "sports_padel_club",
    "heritage_cultural_asset",
    "mixed_use_special_asset",
]


# ── Core simulation flags ──────────────────────────────────────────────────────

def test_UCS001_context_exists():
    assert isinstance(CTX, dict)


def test_UCS002_direct_common_simulation_enabled():
    assert CTX["direct_common_simulation_enabled"] is True


def test_UCS003_working_common_renderer_reused():
    assert CTX["working_common_renderer_reused"] is True


def test_UCS004_separate_uncommon_renderer_disabled():
    assert CTX["separate_uncommon_renderer_disabled"] is True


def test_UCS005_uncommon_assets_simulate_common_requirements():
    assert CTX["uncommon_assets_simulate_common_requirements"] is True


def test_UCS006_no_keys_still_using_weak_renderer():
    assert CTX["uncommon_asset_keys_still_using_weak_renderer"] == []


# ── Asset template mapping ─────────────────────────────────────────────────────

def test_UCS007_petrol_station_mapped():
    mapping = CTX["uncommon_asset_mapping"]
    assert "petrol_station" in mapping
    assert mapping["petrol_station"]


def test_UCS008_hospital_mapped():
    assert "hospital" in CTX["uncommon_asset_mapping"]


def test_UCS009_school_mapped():
    assert "school" in CTX["uncommon_asset_mapping"]


def test_UCS010_cinema_theater_mapped():
    assert "cinema_theater" in CTX["uncommon_asset_mapping"]


def test_UCS011_sports_padel_club_mapped():
    assert "sports_padel_club" in CTX["uncommon_asset_mapping"]


def test_UCS012_heritage_mapped():
    assert "architectural_cultural_heritage_detailed" in CTX["uncommon_asset_mapping"]


def test_UCS013_mixed_use_special_mapped():
    assert "mixed_use_special" in CTX["uncommon_asset_mapping"]


def test_UCS014_hotel_mapped():
    assert "hotel" in CTX["uncommon_asset_mapping"]


# ── Style and preservation flags ──────────────────────────────────────────────

def test_UCS015_style_parity_with_common_assets():
    assert CTX["style_parity_with_common_assets"] is True


def test_UCS016_common_asset_tables_preserved():
    assert CTX["common_asset_tables_preserved"] is True


# ── Feature flags ──────────────────────────────────────────────────────────────

def test_UCS017_upload_clips_enabled():
    assert CTX["upload_clips_enabled"] is True


def test_UCS018_priority_badges_enabled():
    assert CTX["priority_badges_enabled"] is True


def test_UCS019_repeatable_groups_enabled():
    assert CTX["repeatable_groups_enabled"] is True


def test_UCS020_completion_validation_enabled():
    assert CTX["completion_validation_enabled"] is True


def test_UCS021_unified_context_sync_enabled():
    assert CTX["unified_context_sync_enabled"] is True


# ── Preservation audit ───��────────────────────────────────────────────────────

def test_UCS022_no_deleted_requirements():
    assert CTX["deleted_old_requirements"] == []


def test_UCS023_no_deleted_options():
    assert CTX["deleted_old_options"] == []


# ── HTML verification ─────────────────────────────────────────────────────────

def test_UCS024_no_internal_paths_in_html():
    assert not re.compile(r"[A-Z]:\\\\Users\\\\", re.IGNORECASE).search(HTML), \
        "Windows drive path found in frontend/index.html"


def test_UCS025_simulation_attrs_in_html():
    """index.html must contain the new UCS attributes and wrapper functions."""
    assert "old-style-common-simulation" in HTML, \
        "data-requirement-engine='old-style-common-simulation' missing from renderStaticPanel"
    assert "data-uncommon-simulates-common" in HTML, \
        "data-uncommon-simulates-common attribute missing from renderStaticPanel"
    assert "uncommonSimulatesCommon" in HTML, \
        "uncommonSimulatesCommon field missing from __pvRequirementRenderDebug"
    assert "pvRenderUncommonAsCommonStyleRequirements" in HTML, \
        "pvRenderUncommonAsCommonStyleRequirements wrapper not found in HTML"
    assert "pvBuildUncommonCommonStyleRequirementConfig" in HTML, \
        "pvBuildUncommonCommonStyleRequirementConfig not found in HTML"
    assert "pvMapUncommonAssetToCommonTemplate" in HTML, \
        "pvMapUncommonAssetToCommonTemplate not found in HTML"
    assert "pvDisableWeakUncommonRenderer" in HTML, \
        "pvDisableWeakUncommonRenderer not found in HTML"
    assert "pvSyncUncommonSimulatedValuesToUnifiedContext" in HTML, \
        "pvSyncUncommonSimulatedValuesToUnifiedContext not found in HTML"
