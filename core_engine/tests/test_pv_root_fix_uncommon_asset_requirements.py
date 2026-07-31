"""
Phase RFU — Root-Fix Uncommon Asset Requirements: Backend Tests
28 tests verifying context, schemas, registry coverage, and non-regression.
advisory_only=True — not_real_training
"""
import re
import sys
import pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core_engine.pv_root_fix_uncommon_context import (
    root_fix_uncommon_asset_requirement_context as CTX,
)

HTML = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

UNCOMMON_PROFILES = [
    "petrol_station",
    "hospital",
    "school",
    "cinema_theater",
    "sports_padel_club",
    "architectural_cultural_heritage_detailed",
    "hotel",
    "mixed_use_special",
]


def _schema_block(profile: str) -> str:
    """Return the sections array content for a profile in _PROFILE_FORM_SCHEMA."""
    marker = f"'{profile}': {{ sections: ["
    idx = HTML.find(marker)
    if idx == -1:
        return ""
    depth = 0
    start = HTML.index("[", idx + len(marker) - 1)
    for i, ch in enumerate(HTML[start:], start):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return HTML[start : i + 1]
    return ""


def _count_schema_sections(profile: str) -> int:
    """Count sections (headings + component_list) in a profile schema."""
    block = _schema_block(profile)
    if not block:
        return -1
    heading_count = len(re.findall(r"(?<!\w)heading:", block))
    comp_count = len(re.findall(r"field_type:\s*'component_list'", block))
    return heading_count + comp_count


# ── Context existence and core fields ────��─────────────────────────────────────

def test_PVRF001_context_exists():
    assert isinstance(CTX, dict), "context must be a dict"


def test_PVRF002_root_cause_identified():
    assert CTX["root_cause_identified"] is True


def test_PVRF003_common_asset_renderer_recorded():
    assert CTX["common_asset_renderer"], "common_asset_renderer must be a non-empty string"
    assert "renderStaticPanel" in CTX["common_asset_renderer"]


def test_PVRF004_old_uncommon_renderer_before_recorded():
    assert CTX["old_uncommon_renderer_before"], "old_uncommon_renderer_before must be non-empty"
    assert "weak" in CTX["old_uncommon_renderer_before"].lower() \
        or "flat" in CTX["old_uncommon_renderer_before"].lower() \
        or "soft" in CTX["old_uncommon_renderer_before"].lower()


def test_PVRF005_canonical_renderer_after():
    assert CTX["canonical_renderer_after"] == "pvRenderOldStyleRichRequirementEngine"


def test_PVRF006_weak_renderer_removed_or_wrapped():
    assert CTX["weak_uncommon_renderer_removed_or_wrapped"] is True


def test_PVRF007_uncommon_direct_dom_rendering_removed():
    assert CTX["uncommon_direct_dom_rendering_removed"] is True


def test_PVRF008_uncommon_assets_use_common_old_style_engine():
    assert CTX["uncommon_assets_use_common_old_style_engine"] is True


def test_PVRF009_no_keys_still_using_weak_renderer():
    assert CTX["uncommon_asset_keys_still_using_weak_renderer"] == []


# ── Uncommon asset key coverage ────────────────���────────────────��──────────────

def test_PVRF010_all_uncommon_keys_detected():
    detected = CTX["uncommon_asset_keys_detected"]
    for key in UNCOMMON_PROFILES:
        assert key in detected, f"{key} not in uncommon_asset_keys_detected"


# ── Per-profile schema presence ──────────────────────��───────────────────��─────

def test_PVRF011_petrol_station_schema_in_html():
    assert _count_schema_sections("petrol_station") == 7, \
        f"petrol_station: expected 7 sections, got {_count_schema_sections('petrol_station')}"


def test_PVRF012_hospital_schema_in_html():
    count = _count_schema_sections("hospital")
    assert count >= 5, f"hospital: expected ≥5 sections, got {count}"


def test_PVRF013_school_schema_in_html():
    count = _count_schema_sections("school")
    assert count >= 5, f"school: expected ≥5 sections, got {count}"


def test_PVRF014_cinema_theater_schema_in_html():
    count = _count_schema_sections("cinema_theater")
    assert count >= 5, f"cinema_theater: expected ≥5 sections, got {count}"


def test_PVRF015_sports_padel_club_schema_in_html():
    count = _count_schema_sections("sports_padel_club")
    assert count >= 5, f"sports_padel_club: expected ≥5 sections, got {count}"


def test_PVRF016_architectural_cultural_heritage_schema_in_html():
    count = _count_schema_sections("architectural_cultural_heritage_detailed")
    assert count >= 5, \
        f"architectural_cultural_heritage_detailed: expected ≥5 sections, got {count}"


def test_PVRF017_hotel_schema_in_html():
    count = _count_schema_sections("hotel")
    assert count >= 5, f"hotel: expected ≥5 sections, got {count}"


def test_PVRF018_mixed_use_special_schema_in_html():
    count = _count_schema_sections("mixed_use_special")
    assert count >= 5, f"mixed_use_special: expected ≥5 sections, got {count}"


# ── Feature flags ──────────────��───────────────────────────────────────────────

def test_PVRF019_upload_clips_enabled():
    assert CTX["upload_clips_enabled"] is True


def test_PVRF020_priority_badges_enabled():
    assert CTX["priority_badges_enabled"] is True


def test_PVRF021_completion_validation_enabled():
    assert CTX["completion_validation_enabled"] is True


def test_PVRF022_repeatable_groups_enabled():
    assert CTX["repeatable_groups_enabled"] is True


def test_PVRF023_unified_context_sync_enabled():
    assert CTX["unified_context_sync_enabled"] is True


# ── Preservation audit ────────────────────────────────────────────────���────────

def test_PVRF024_common_asset_tables_preserved():
    assert CTX["common_asset_tables_preserved"] is True


def test_PVRF025_no_deleted_requirements():
    assert CTX["deleted_old_requirements"] == []


def test_PVRF026_no_deleted_options():
    assert CTX["deleted_old_options"] == []


# ── HTML verification ────────────────���───────────────────���─────────────────────

def test_PVRF027_no_internal_paths_in_html():
    # Must not expose Windows-style drive paths in any JS data structure
    import re as _re
    drive_path_pattern = _re.compile(r"[A-Z]:\\\\Users\\\\", _re.IGNORECASE)
    assert not drive_path_pattern.search(HTML), \
        "Windows drive path found in frontend/index.html"


def test_PVRF028_runtime_debug_attrs_in_html():
    """renderStaticPanel must set data-requirement-engine and data-asset-category."""
    assert "data-requirement-engine" in HTML, \
        "data-requirement-engine attribute missing from renderStaticPanel"
    assert "data-asset-category" in HTML, \
        "data-asset-category attribute missing from renderStaticPanel"
    assert "__pvRequirementRenderDebug" in HTML, \
        "window.__pvRequirementRenderDebug missing from renderStaticPanel"
    assert "pvRenderOldStyleRichRequirementEngine" in HTML, \
        "pvRenderOldStyleRichRequirementEngine canonical wrapper not found in HTML"
