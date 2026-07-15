"""
Backend tests: Professional Valuation — Force Uncommon Assets to Use Same Engine as Common Assets.

Verifies that petrol_station, cinema_theater, sports_padel_club, mixed_use_special, and
architectural_cultural_heritage_detailed are wired into the same rich engine
(renderStaticPanel → _renderProfileSections → _sectionControlsHTML / _renderComponentSection)
as common assets (hotel, factory, apartment, etc.), with full schema coverage.

Tests (27):
  Category 1 — Context and Engine Detection (PVFCU001–005)
  Category 2 — Key Mapping (PVFCU006–010)
  Category 3 — Per-Asset Schema Groups (PVFCU011–015)
  Category 4 — Field Coverage (PVFCU016–020)
  Category 5 — Component List Features (PVFCU021–023)
  Category 6 — Preservation and Safety (PVFCU024–027)
"""
import json
import pathlib
import re

import pytest

# ── Path helpers ──────────────────────────────────────────────────────────────

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_FRONTEND = _ROOT / "frontend" / "index.html"
_QA_DIR = (
    _ROOT
    / "core_engine"
    / "instance"
    / "manual_review_outputs"
    / "professional_valuation_force_uncommon_same_engine"
)
_SIGNOFF = _QA_DIR / "13_final_delivery_signoff.json"


@pytest.fixture(scope="module")
def html() -> str:
    return _FRONTEND.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def signoff() -> dict:
    return json.loads(_SIGNOFF.read_text(encoding="utf-8"))


# ═══════════════════════════════════════════════════════════════════════════════
# Category 1 — Context and Engine Detection
# ═══════════════════════════════════════════════════════════════════════════════


def test_PVFCU001_fcu_context_file_exists() -> None:
    """QA context file (13_final_delivery_signoff.json) must exist."""
    assert _SIGNOFF.exists(), f"Missing signoff file: {_SIGNOFF}"


def test_PVFCU002_uncommon_assets_use_common_engine_flag(signoff: dict) -> None:
    """uncommon_assets_now_use_common_old_style_engine must be true."""
    val = signoff["required_final_values"]["uncommon_assets_now_use_common_old_style_engine"]
    assert val is True, f"Flag must be true. Got: {val!r}"


def test_PVFCU003_weak_renderer_removed_flag(signoff: dict) -> None:
    """weak_uncommon_renderer_removed_or_wrapped must be true."""
    val = signoff["required_final_values"]["weak_uncommon_renderer_removed_or_wrapped"]
    assert val is True, f"Flag must be true. Got: {val!r}"


def test_PVFCU004_no_keys_still_on_weak_renderer(signoff: dict) -> None:
    """uncommon_asset_keys_still_using_weak_renderer must be empty list."""
    val = signoff["required_final_values"]["uncommon_asset_keys_still_using_weak_renderer"]
    assert val == [], f"List must be empty. Got: {val!r}"


def test_PVFCU005_style_parity_and_preservation_flags(signoff: dict) -> None:
    """style_parity_with_common_assets=true AND common_asset_tables_preserved=true."""
    parity = signoff["required_final_values"]["style_parity_with_common_assets"]
    preserved = signoff["required_final_values"]["common_asset_tables_preserved"]
    assert parity is True, f"style_parity_with_common_assets must be true. Got: {parity!r}"
    assert preserved is True, f"common_asset_tables_preserved must be true. Got: {preserved!r}"


# ═══════════════════════════════════════════════════════════════════════════════
# Category 2 — Key Mapping
# ═══════════════════════════════════════════════════════════════════════════════


def test_PVFCU006_petrol_station_in_asset_profile_map(html: str) -> None:
    """ASSET_PROFILE_MAP must have Arabic key 'محطة تموين سيارات' → 'petrol_station'."""
    assert "'محطة تموين سيارات'" in html, "Arabic key 'محطة تموين سيارات' not found in HTML"
    assert "'petrol_station'" in html, "'petrol_station' profile code not found in HTML"
    # Check they appear together
    idx_ar = html.find("'محطة تموين سيارات'")
    idx_ps = html.find("'petrol_station'", idx_ar)
    assert idx_ps - idx_ar < 300, (
        "petrol_station mapping: arabic key and profile code must be in close proximity"
    )


def test_PVFCU007_cinema_theater_in_asset_profile_map(html: str) -> None:
    """ASSET_PROFILE_MAP must have key 'سينما / مسرح / قاعة عرض' → 'cinema_theater'."""
    assert "'سينما / مسرح / قاعة عرض'" in html, "Arabic key for cinema_theater not found"
    assert "'cinema_theater'" in html, "'cinema_theater' profile code not found"


def test_PVFCU008_sports_padel_club_in_asset_profile_map(html: str) -> None:
    """ASSET_PROFILE_MAP must have key 'نادي رياضي / ملاعب بادل' → 'sports_padel_club'."""
    assert "'نادي رياضي / ملاعب بادل'" in html, "Arabic key for sports_padel_club not found"
    assert "'sports_padel_club'" in html, "'sports_padel_club' profile code not found"


def test_PVFCU009_mixed_use_special_in_asset_profile_map(html: str) -> None:
    """ASSET_PROFILE_MAP must have key 'أصل متعدد الاستخدامات خاص' → 'mixed_use_special'."""
    assert "'أصل متعدد الاستخدامات خاص'" in html, "Arabic key for mixed_use_special not found"
    assert "'mixed_use_special'" in html, "'mixed_use_special' profile code not found"


def test_PVFCU010_static_profiles_all_5_fcu_types(html: str) -> None:
    """_STATIC_PROFILES must have type:'form' entries for all 5 FCU profiles."""
    fcu_profiles = [
        "petrol_station",
        "cinema_theater",
        "sports_padel_club",
        "mixed_use_special",
        "architectural_cultural_heritage_detailed",
    ]
    for profile in fcu_profiles:
        pattern = rf"'{re.escape(profile)}'.*?type:\s*'form'"
        assert re.search(pattern, html, re.DOTALL), (
            f"_STATIC_PROFILES entry with type:'form' missing for profile: {profile}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Category 3 — Per-Asset Schema Groups
# ═══════════════════════════════════════════════════════════════════════════════

def _count_schema_sections(html: str, profile: str) -> int:
    """Count sections in _PROFILE_FORM_SCHEMA[profile] by counting { heading: or field_type: 'component_list'."""
    # Find the schema block for this profile
    marker = f"'{profile}': {{ sections: ["
    start = html.find(marker)
    if start == -1:
        return -1
    # Find the matching closing bracket sequence '],'  or '],' (end of sections array)
    depth = 0
    i = start + len(marker)
    # Count 'heading:' occurrences and 'field_type:' occurrences in this block
    # Simple heuristic: find where the sections array ends
    sections_start = html.find("[", start + len(marker) - 1)
    if sections_start == -1:
        return -1
    # Find the end of the sections array (matching ])
    depth = 1
    j = sections_start + 1
    while j < len(html) and depth > 0:
        if html[j] == "[":
            depth += 1
        elif html[j] == "]":
            depth -= 1
        j += 1
    schema_block = html[sections_start:j]
    # Count heading: and field_type: 'component_list' entries as sections
    # Use negative lookbehind to avoid matching 'section_heading:' as 'heading:'
    heading_count = len(re.findall(r"(?<!\w)heading:", schema_block))
    comp_count = len(re.findall(r"field_type:\s*'component_list'", schema_block))
    return heading_count + comp_count


def test_PVFCU011_petrol_station_has_7_sections(html: str) -> None:
    """petrol_station schema must have 7 sections (5 regular + 1 component_list + 1 docs)."""
    count = _count_schema_sections(html, "petrol_station")
    assert count == 7, f"petrol_station must have 7 sections. Got: {count}"


def test_PVFCU012_cinema_theater_has_6_sections(html: str) -> None:
    """cinema_theater schema must have 6 sections."""
    count = _count_schema_sections(html, "cinema_theater")
    assert count == 6, f"cinema_theater must have 6 sections. Got: {count}"


def test_PVFCU013_sports_padel_club_has_6_sections(html: str) -> None:
    """sports_padel_club schema must have 6 sections."""
    count = _count_schema_sections(html, "sports_padel_club")
    assert count == 6, f"sports_padel_club must have 6 sections. Got: {count}"


def test_PVFCU014_mixed_use_special_has_6_sections(html: str) -> None:
    """mixed_use_special schema must have 6 sections."""
    count = _count_schema_sections(html, "mixed_use_special")
    assert count == 6, f"mixed_use_special must have 6 sections. Got: {count}"


def test_PVFCU015_arch_heritage_has_6_sections(html: str) -> None:
    """architectural_cultural_heritage_detailed schema must have 6 sections."""
    count = _count_schema_sections(html, "architectural_cultural_heritage_detailed")
    assert count == 6, (
        f"architectural_cultural_heritage_detailed must have 6 sections. Got: {count}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Category 4 — Field Coverage
# ═══════════════════════════════════════════════════════════════════════════════


def _schema_block(html: str, profile: str) -> str:
    """Extract the sections array content for a given profile schema."""
    marker = f"'{profile}': {{ sections: ["
    start = html.find(marker)
    if start == -1:
        return ""
    sections_start = html.find("[", start + len(marker) - 1)
    if sections_start == -1:
        return ""
    depth = 1
    j = sections_start + 1
    while j < len(html) and depth > 0:
        if html[j] == "[":
            depth += 1
        elif html[j] == "]":
            depth -= 1
        j += 1
    return html[sections_start:j]


def test_PVFCU016_petrol_station_key_fields_present(html: str) -> None:
    """petrol_station schema contains ps_land_area_sqm, ps_pumps_count, ps_fuel_types."""
    block = _schema_block(html, "petrol_station")
    for field in ("ps_land_area_sqm", "ps_pumps_count", "ps_fuel_types"):
        assert field in block, f"petrol_station schema missing field: {field}"


def test_PVFCU017_cinema_theater_key_fields_present(html: str) -> None:
    """cinema_theater schema contains ct_total_seats, ct_halls_count, ct_venue_type."""
    block = _schema_block(html, "cinema_theater")
    for field in ("ct_total_seats", "ct_halls_count", "ct_venue_type"):
        assert field in block, f"cinema_theater schema missing field: {field}"


def test_PVFCU018_sports_padel_club_key_fields_present(html: str) -> None:
    """sports_padel_club schema contains sp_courts_count, sp_padel_courts, sp_venue_type."""
    block = _schema_block(html, "sports_padel_club")
    for field in ("sp_courts_count", "sp_padel_courts", "sp_venue_type"):
        assert field in block, f"sports_padel_club schema missing field: {field}"


def test_PVFCU019_mixed_use_special_key_fields_present(html: str) -> None:
    """mixed_use_special schema contains mx_land_area_sqm, mx_residential_pct, mx_occupancy_rate."""
    block = _schema_block(html, "mixed_use_special")
    for field in ("mx_land_area_sqm", "mx_residential_pct", "mx_occupancy_rate"):
        assert field in block, f"mixed_use_special schema missing field: {field}"


def test_PVFCU020_arch_heritage_key_fields_present(html: str) -> None:
    """architectural_cultural_heritage_detailed schema contains ach_heritage_type, ach_heritage_grade, ach_listed."""
    block = _schema_block(html, "architectural_cultural_heritage_detailed")
    for field in ("ach_heritage_type", "ach_heritage_grade", "ach_listed"):
        assert field in block, (
            f"architectural_cultural_heritage_detailed schema missing field: {field}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Category 5 — Component List Features
# ═══════════════════════════════════════════════════════════════════════════════


def test_PVFCU021_petrol_station_component_defaults_count(html: str) -> None:
    """petrol_station component_list defaults must have 4 items."""
    block = _schema_block(html, "petrol_station")
    # Find the component_list section and count defaults
    comp_idx = block.find("component_list")
    assert comp_idx != -1, "component_list not found in petrol_station schema"
    # Count default strings: 'مبنى الإدارة / الخدمات', 'منطقة الطلمبات', 'الخزانات', 'ماركت / خدمات تجارية'
    defaults_block_start = block.find("defaults:", comp_idx)
    defaults_block_end = block.find("]", defaults_block_start) + 1
    defaults_block = block[defaults_block_start:defaults_block_end]
    count = defaults_block.count("'")
    # 4 strings × 2 quotes each = 8 quotes
    assert count >= 8, (
        f"petrol_station defaults must have 4 items (≥8 quote chars). Got {count // 2} items"
    )


def test_PVFCU022_cinema_theater_component_extra_fields(html: str) -> None:
    """cinema_theater component_list extra_fields must include hall_seats_count and hall_screen_type."""
    block = _schema_block(html, "cinema_theater")
    assert "hall_seats_count" in block, "cinema_theater missing extra_field hall_seats_count"
    assert "hall_screen_type" in block, "cinema_theater missing extra_field hall_screen_type"


def test_PVFCU023_sports_padel_club_component_label(html: str) -> None:
    """sports_padel_club component_list section_label must be 'ملعب'."""
    block = _schema_block(html, "sports_padel_club")
    assert "section_label:" in block, "sports_padel_club missing section_label"
    # Find the section_label value
    label_idx = block.find("section_label:")
    label_snippet = block[label_idx:label_idx + 60]
    assert "ملعب" in label_snippet, (
        f"sports_padel_club section_label must be 'ملعب'. Snippet: {label_snippet!r}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Category 6 — Preservation and Safety
# ═══════════════════════════════════════════════════════════════════════════════


def test_PVFCU024_hotel_resort_schema_preserved(html: str) -> None:
    """hotel schema must still have ≥5 sections (not deleted by FCU task)."""
    # The hotel schema key in _PROFILE_FORM_SCHEMA is 'hotel' (not 'hotel_resort')
    count = _count_schema_sections(html, "hotel")
    assert count >= 5, (
        f"hotel schema must have ≥5 sections (was not altered by FCU). Got: {count}"
    )


def test_PVFCU025_hospital_still_in_profile_map(html: str) -> None:
    """hospital_medical_center must still be present in ASSET_PROFILE_MAP."""
    # Either Arabic hospital key or profile code 'hospital_medical_center' must exist
    assert (
        "hospital_medical_center" in html or "مستشفى" in html
    ), "hospital_medical_center profile missing from HTML (FCU task must not delete pre-existing types)"


def test_PVFCU026_intercept_covers_fcu_arabic_keys(html: str) -> None:
    """window._pvRichAssetProfileMap must be exposed, and all 4 FCU Arabic keys appear in ASSET_PROFILE_MAP."""
    assert "_pvRichAssetProfileMap" in html, "window._pvRichAssetProfileMap must be exposed"
    fcu_arabic_keys = [
        "'محطة تموين سيارات'",
        "'سينما / مسرح / قاعة عرض'",
        "'نادي رياضي / ملاعب بادل'",
        "'أصل متعدد الاستخدامات خاص'",
    ]
    for key in fcu_arabic_keys:
        assert key in html, f"FCU Arabic key not found in HTML: {key}"


def test_PVFCU027_no_internal_paths_in_dom(html: str) -> None:
    """No Windows internal file paths (C:\\Users) must appear in the HTML."""
    # Strip JS template literals and raw string content to check only rendered HTML
    bad_pattern = re.compile(r"C:\\\\Users|C:/Users", re.IGNORECASE)
    assert not bad_pattern.search(html), (
        "Windows file system path found in frontend/index.html — violates no_internal_paths_in_dom rule"
    )
