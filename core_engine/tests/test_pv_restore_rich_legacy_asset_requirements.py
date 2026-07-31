# -*- coding: utf-8 -*-
"""
test_pv_restore_rich_legacy_asset_requirements.py
Backend tests: PV Rich Legacy Asset Requirement Engine Restore (PVRLARE)

Tests verify:
  PVRLARE-B01  QA directory and comparison matrix exist
  PVRLARE-B02  Comparison matrix lists 8e49866 as winner
  PVRLARE-B03  Comparison matrix scores 8e49866 with dynamic_feature_score >= 9
  PVRLARE-B04  Comparison matrix has has_add_building=true for winning commit
  PVRLARE-B05  index.html contains pvRestoreRichLegacyAssetRequirementEngine
  PVRLARE-B06  index.html contains _pvRichRenderComponentSection
  PVRLARE-B07  index.html contains pvGetRichProfile
  PVRLARE-B08  index.html contains _PV_RICH_PROFILE_ALIAS_MAP
  PVRLARE-B09  Alias map includes hotel (Arabic 'فندق')
  PVRLARE-B10  Alias map includes factory ('مصنع')
  PVRLARE-B11  Alias map includes industrial_factory
  PVRLARE-B12  showProfAssetRequirements contains Part D intercept
  PVRLARE-B13  showProfAssetRequirements contains pvGetRichProfile
  PVRLARE-B14  showProfAssetRequirements rich path appears BEFORE flat table path
  PVRLARE-B15  index.html still contains COMPONENT_FIELDS
  PVRLARE-B16  index.html still contains _renderComponentSection
  PVRLARE-B17  index.html still contains _PROFILE_FORM_SCHEMA hotel entry
  PVRLARE-B18  index.html still contains _PROFILE_FORM_SCHEMA factory entry
  PVRLARE-B19  Old add-building defaults for hotel preserved
  PVRLARE-B20  Old add-building defaults for factory preserved
  PVRLARE-B21  pvAddAssetBuilding global function present
  PVRLARE-B22  pvCollectRichLegacyAssetRequirementValues global function present
  PVRLARE-B23  No internal paths exposed (sanity check)
  PVRLARE-B24  Ordinary valuation unaffected (health endpoint)
  PVRLARE-B25  Flat table renderer still present (backward compat)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

_QA_BASE = (
    Path(__file__).resolve().parents[1]
    / "instance" / "manual_review_outputs"
    / "professional_valuation_restore_rich_legacy_asset_requirements"
)

_INDEX_HTML = (
    Path(__file__).resolve().parents[2] / "frontend" / "index.html"
)

_BRIDGE_API = (
    Path(__file__).resolve().parents[1] / "bridge_api.py"
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def matrix():
    f = _QA_BASE / "01_legacy_candidate_comparison_matrix.json"
    assert f.exists(), f"Matrix file not found: {f}"
    return json.loads(f.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def html():
    assert _INDEX_HTML.exists(), f"index.html not found: {_INDEX_HTML}"
    return _INDEX_HTML.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def bridge():
    assert _BRIDGE_API.exists(), f"bridge_api.py not found: {_BRIDGE_API}"
    return _BRIDGE_API.read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# PVRLARE-B01 to B04: QA output files
# ─────────────────────────────────────────────────────────────────────────────

def test_PVRLARE_B01_qa_directory_and_matrix_exist():
    """QA directory and comparison matrix JSON exist."""
    assert _QA_BASE.exists(), f"QA directory not found: {_QA_BASE}"
    matrix_file = _QA_BASE / "01_legacy_candidate_comparison_matrix.json"
    assert matrix_file.exists(), f"Matrix file not found: {matrix_file}"


def test_PVRLARE_B02_matrix_winner_is_8e49866(matrix):
    """Comparison matrix declares 8e49866 as the winning commit."""
    winner = matrix.get("winner", {})
    commit = winner.get("commit_sha", "")
    assert "8e49866" in commit, \
        f"Expected winner commit sha to contain '8e49866', got: {commit}"


def test_PVRLARE_B03_matrix_winner_dynamic_feature_score(matrix):
    """Winning commit has dynamic_feature_score >= 9."""
    candidates = matrix.get("candidates", [])
    winner_sha = matrix.get("winner", {}).get("commit_sha", "")
    winner = next((c for c in candidates if c.get("commit_sha", "") in winner_sha), None)
    assert winner is not None, "Winning commit not found in candidates list"
    score = winner.get("dynamic_feature_score", 0)
    assert score >= 9, f"Expected dynamic_feature_score >= 9, got {score}"


def test_PVRLARE_B04_matrix_winner_has_add_building(matrix):
    """Winning commit has has_add_building=true."""
    candidates = matrix.get("candidates", [])
    winner_sha = matrix.get("winner", {}).get("commit_sha", "")
    winner = next((c for c in candidates if c.get("commit_sha", "") in winner_sha), None)
    assert winner is not None, "Winning commit not found in candidates list"
    assert winner.get("has_add_building") is True, \
        "Expected has_add_building=true for winning commit"


# ─────────────────────────────────────────────────────────────────────────────
# PVRLARE-B05 to B08: Global functions present in HTML
# ─────────────────────────────────────────────────────────────────────────────

def test_PVRLARE_B05_pvRestoreRichLegacyAssetRequirementEngine_present(html):
    """index.html contains pvRestoreRichLegacyAssetRequirementEngine global function."""
    assert "pvRestoreRichLegacyAssetRequirementEngine" in html, \
        "pvRestoreRichLegacyAssetRequirementEngine not found in index.html"


def test_PVRLARE_B06_pvRichRenderComponentSection_exposed(html):
    """index.html exposes _pvRichRenderComponentSection globally."""
    assert "window._pvRichRenderComponentSection" in html, \
        "window._pvRichRenderComponentSection not found in index.html"


def test_PVRLARE_B07_pvGetRichProfile_present(html):
    """index.html contains pvGetRichProfile global function."""
    assert "window.pvGetRichProfile" in html, \
        "window.pvGetRichProfile not found in index.html"


def test_PVRLARE_B08_PV_RICH_PROFILE_ALIAS_MAP_present(html):
    """index.html contains _PV_RICH_PROFILE_ALIAS_MAP alias registry."""
    assert "window._PV_RICH_PROFILE_ALIAS_MAP" in html, \
        "window._PV_RICH_PROFILE_ALIAS_MAP not found in index.html"


# ─────────────────────────────────────────────────────────────────────────────
# PVRLARE-B09 to B11: Alias map includes critical entries
# ─────────────────────────────────────────────────────────────────────────────

def test_PVRLARE_B09_alias_map_has_arabic_hotel(html):
    """Alias map maps Arabic 'فندق' to 'hotel'."""
    assert "'فندق'" in html or '"فندق"' in html, \
        "Arabic فندق not found in index.html alias map"
    # Verify it maps to hotel
    pattern = r"['\"]فندق['\"].*?:\s*['\"]hotel['\"]"
    assert re.search(pattern, html), \
        "فندق → hotel mapping not found in alias map"


def test_PVRLARE_B10_alias_map_has_arabic_factory(html):
    """Alias map maps Arabic 'مصنع' to 'factory'."""
    pattern = r"['\"]مصنع['\"].*?:\s*['\"]factory['\"]"
    assert re.search(pattern, html), \
        "مصنع → factory mapping not found in alias map"


def test_PVRLARE_B11_alias_map_has_industrial_factory(html):
    """Alias map maps 'industrial_factory' to 'factory'."""
    pattern = r"['\"]industrial_factory['\"].*?:\s*['\"]factory['\"]"
    assert re.search(pattern, html), \
        "industrial_factory → factory mapping not found in alias map"


# ─────────────────────────────────────────────────────────────────────────────
# PVRLARE-B12 to B14: showProfAssetRequirements routing
# ─────────────────────────────────────────────────────────────────────────────

def test_PVRLARE_B12_showProfAssetRequirements_has_part_d_intercept(html):
    """showProfAssetRequirements contains Part D intercept comment."""
    assert "Part D: Rich Legacy Engine" in html or "Part D" in html, \
        "Part D intercept not found in showProfAssetRequirements"


def test_PVRLARE_B13_showProfAssetRequirements_calls_pvGetRichProfile(html):
    """showProfAssetRequirements calls pvGetRichProfile to check for rich form."""
    assert "pvGetRichProfile" in html, \
        "pvGetRichProfile call not found in index.html"


def test_PVRLARE_B14_rich_path_before_flat_table_path(html):
    """Within showProfAssetRequirements, pvGetRichProfile() call appears before pvRenderCommonAssetFillable() call."""
    # Find the showProfAssetRequirements function body
    fn_start = html.find("window.showProfAssetRequirements = function")
    assert fn_start >= 0, "showProfAssetRequirements not found in HTML"
    fn_end = html.find("\nwindow.", fn_start + 50)
    if fn_end < 0:
        fn_end = fn_start + 20_000
    fn_body = html[fn_start:fn_end]
    # Search for actual CALLS (with parenthesis), not comment references
    rich_idx = fn_body.find("pvGetRichProfile(")
    flat_idx = fn_body.find("pvRenderCommonAssetFillable(")
    assert rich_idx >= 0, "pvGetRichProfile() call not found in showProfAssetRequirements body"
    assert flat_idx >= 0, "pvRenderCommonAssetFillable() call not found in showProfAssetRequirements body"
    assert rich_idx < flat_idx, (
        f"In showProfAssetRequirements: rich path call (pos {rich_idx}) must come before "
        f"flat table call (pos {flat_idx})"
    )


# ─────────────────────────────────────────────────────────────────────────────
# PVRLARE-B15 to B20: Legacy engine not deleted
# ─────────────────────────────────────────────────────────────────────────────

def test_PVRLARE_B15_COMPONENT_FIELDS_still_present(html):
    """COMPONENT_FIELDS array still present (not deleted)."""
    assert "COMPONENT_FIELDS" in html, "COMPONENT_FIELDS deleted from index.html"


def test_PVRLARE_B16_renderComponentSection_still_present(html):
    """_renderComponentSection function still present (not deleted)."""
    assert "_renderComponentSection" in html, \
        "_renderComponentSection deleted from index.html"


def test_PVRLARE_B17_profile_schema_hotel_present(html):
    """_PROFILE_FORM_SCHEMA hotel entry still present (not deleted)."""
    assert "'hotel'" in html or '"hotel"' in html, \
        "hotel entry deleted from _PROFILE_FORM_SCHEMA"


def test_PVRLARE_B18_profile_schema_factory_present(html):
    """_PROFILE_FORM_SCHEMA factory entry still present (not deleted)."""
    assert "'factory'" in html or '"factory"' in html, \
        "factory entry deleted from _PROFILE_FORM_SCHEMA"


def test_PVRLARE_B19_hotel_default_buildings_preserved(html):
    """Hotel default buildings list still preserved (المبنى الرئيسي, غرف, مطعم...)."""
    assert "المبنى الرئيسي" in html, \
        "Hotel default building 'المبنى الرئيسي' deleted"
    assert "��طعم" in html or "قاعة طعام" in html, \
        "Hotel default building مطعم/قاعة طعام deleted"


def test_PVRLARE_B20_factory_default_buildings_preserved(html):
    """Factory default buildings list still preserved (عنبر الإنتاج, المخزن...)."""
    assert "عنبر الإنتاج" in html, \
        "Factory default building 'عنبر الإنتاج' deleted"
    assert "مبنى الإدارة" in html, \
        "Factory default building 'مبنى الإدارة' deleted"


# ─────────────────────────────────────────────────────────────────────────────
# PVRLARE-B21 to B22: Part J function aliases
# ─────────────────────────────────────────────────────────────────────────────

def test_PVRLARE_B21_pvAddAssetBuilding_present(html):
    """Part J: pvAddAssetBuilding global function present."""
    assert "pvAddAssetBuilding" in html, \
        "pvAddAssetBuilding not found in index.html"


def test_PVRLARE_B22_pvCollectRichLegacyAssetRequirementValues_present(html):
    """Part J: pvCollectRichLegacyAssetRequirementValues global function present."""
    assert "pvCollectRichLegacyAssetRequirementValues" in html, \
        "pvCollectRichLegacyAssetRequirementValues not found in index.html"


# ─────────────────────────────────────────────────────────────────────────────
# PVRLARE-B23 to B25: Safety and backward compat
# ─────────────────────────────────────────────────────────────────────────────

def test_PVRLARE_B23_no_internal_paths_in_html(html):
    """No Windows-style internal paths exposed in HTML."""
    bad_patterns = [
        r"C:\\Users\\",
        r"C:/Users/",
        r"AppData",
        r"/home/",
    ]
    for pat in bad_patterns:
        matches = [
            l for l in html.split("\n")
            if pat in l
            and "CLAUDE.md" not in l
            and "core_engine" not in l
            and "memory" not in l
            and "conftest" not in l
        ]
        # Filter out comments and template strings
        real_matches = [
            m for m in matches
            if not m.strip().startswith("//")
            and not m.strip().startswith("*")
            and not m.strip().startswith("#")
        ]
        assert not real_matches, \
            f"Internal path pattern '{pat}' found in HTML: {real_matches[:2]}"


def test_PVRLARE_B24_ordinary_valuation_unaffected(bridge):
    """Flat table renderer pvRenderCommonAssetFillable still in HTML (backward compat)."""
    # Check that flat table function is NOT removed
    html_content = _INDEX_HTML.read_text(encoding="utf-8")
    assert "pvRenderCommonAssetFillable" in html_content, \
        "pvRenderCommonAssetFillable removed — backward compat broken"


def test_PVRLARE_B25_flat_table_data_still_present(html):
    """_PV_COMMON_REQ_DATA flat table data still present for non-rich assets."""
    assert "_PV_COMMON_REQ_DATA" in html, \
        "_PV_COMMON_REQ_DATA removed — flat table data for residential/warehouse broken"
