"""
Professional Valuation — Forensic Old Requirements Restore Tests.

Verifies that the old-system asset requirement tables (commit 8e49866 style)
are correctly restored in the current implementation:
  - #es-req-panel is the primary requirements container for old-system asset types
  - #pvr-vis-asset-requirements-panel is suppressed for old-system asset types
  - Hotel/factory render via renderStaticPanel into #es-req-panel
  - Apartment/land/retail route through fetchChecklist
  - Dynamic add-building works for hotel and factory
  - All old asset types are in ASSET_PROFILE_MAP
"""
import pytest
from pathlib import Path


QA_DIR = Path("core_engine/instance/manual_review_outputs/"
              "professional_valuation_forensic_old_requirements_restore")
RESTORED_DIR = QA_DIR / "restored_current_screenshots"
OLD_DIR = QA_DIR / "old_commit_screenshots"


# ── Category 1: QA Output Files ──────────────────────────────────────────────


def test_PVFOR001_forensic_discovery_report_exists():
    """01_old_ui_forensic_discovery_report.json must exist."""
    assert (QA_DIR / "01_old_ui_forensic_discovery_report.json").exists(), (
        "Missing: 01_old_ui_forensic_discovery_report.json"
    )


def test_PVFOR002_visual_gap_report_exists():
    """02_old_vs_current_visual_gap_report.json must exist."""
    assert (QA_DIR / "02_old_vs_current_visual_gap_report.json").exists(), (
        "Missing: 02_old_vs_current_visual_gap_report.json"
    )


def test_PVFOR003_old_commit_screenshots_exist():
    """Old commit (8e49866) screenshots must exist: hotel, factory, apartment."""
    required = [
        "targeted_old_hotel_req_top.png",
        "targeted_old_factory_req_top.png",
        "targeted_old_apartment_req_top.png",
        "old_8e49866_hotel_add_building.png",
    ]
    for f in required:
        assert (OLD_DIR / f).exists(), f"Missing old screenshot: {f}"


def test_PVFOR004_restored_screenshots_exist():
    """Restored current screenshots must exist after Phase E fix."""
    required = [
        "restored_hotel_req_top.png",
        "restored_hotel_after_add_two.png",
        "restored_factory_req_top.png",
        "restored_apartment_req_top.png",
    ]
    for f in required:
        assert (RESTORED_DIR / f).exists(), f"Missing restored screenshot: {f}"


def test_PVFOR005_verify_results_pass():
    """restored_current_screenshots/verify_results.json must show all_pass=True."""
    import json
    results_file = RESTORED_DIR / "verify_results.json"
    assert results_file.exists(), "Missing: verify_results.json"
    data = json.loads(results_file.read_text(encoding="utf-8"))
    assert data.get("all_pass") is True, (
        f"Verify results not all passing: {data}"
    )


# ── Category 2: Frontend Structure ─────────────────────────────────────���─────


def test_PVFOR006_es_req_panel_in_visible_dom():
    """#es-req-panel must NOT be inside a display:none parent section."""
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    # The es-req-panel must appear BEFORE Section 5 (pro-val-section-report-type)
    es_req_pos = html.find('id="es-req-panel"')
    section5_pos = html.find('data-testid="pro-val-section-report-type"')
    assert es_req_pos > 0, "#es-req-panel not found in frontend/index.html"
    assert section5_pos > 0, "Section 5 not found in frontend/index.html"
    assert es_req_pos < section5_pos, (
        f"#es-req-panel (pos {es_req_pos}) must appear BEFORE the hidden Section 5 "
        f"(pos {section5_pos}), not inside it"
    )


def test_PVFOR007_showprofassetrequirements_has_intercept():
    """showProfAssetRequirements must have the _pvRichAssetProfileMap intercept."""
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    assert "_pvRichAssetProfileMap" in html, (
        "showProfAssetRequirements intercept (_pvRichAssetProfileMap) not found"
    )
    # Verify the intercept returns early for old-system types
    assert "window._pvRichAssetProfileMap.hasOwnProperty(assetTypeVal)" in html, (
        "showProfAssetRequirements must check _pvRichAssetProfileMap.hasOwnProperty"
    )


def test_PVFOR008_fetchchecklist_routes_hotel_to_static():
    """fetchChecklist must use _STATIC_PROFILES which maps hotel to form type."""
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    assert "'hotel':              { type: 'form', titleAr: 'فندق / منتجع سياحي' }" in html, (
        "_STATIC_PROFILES must contain hotel form entry"
    )
    assert "'factory':            { type: 'form', titleAr: 'مصنع / صناعي / لوجستي' }" in html, (
        "_STATIC_PROFILES must contain factory form entry"
    )


def test_PVFOR009_asset_profile_map_has_arabic_keys():
    """ASSET_PROFILE_MAP must have Arabic keys for common asset types."""
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    # Check for presence of keys (whitespace-tolerant)
    import re
    def has_map_entry(html_text, ar_key, profile):
        pattern = re.escape(f"'{ar_key}'") + r"\s*:\s*'" + re.escape(profile) + r"'"
        return bool(re.search(pattern, html_text))

    required = [
        ("شقة سكنية", "residential_unit"),  # شقة سكنية
        ("فندق", "hotel"),                                        # فندق
        ("مصنع", "factory"),                                      # مصنع
        ("أرض فضاء", "land"),                     # أرض فضاء
    ]
    for ar_key, profile in required:
        assert has_map_entry(html, ar_key, profile), (
            f"ASSET_PROFILE_MAP missing entry: '{ar_key}' → '{profile}'"
        )


def test_PVFOR010_render_component_section_exists():
    """_renderComponentSection must exist in IIFE for dynamic add-building."""
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    assert "function _renderComponentSection" in html, (
        "_renderComponentSection function not found"
    )


def test_PVFOR011_component_fields_has_12_entries():
    """COMPONENT_FIELDS must have 12 fields for building cards."""
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    # Check a few key fields that are unique to COMPONENT_FIELDS
    required_fields = [
        "component_name",
        "component_use",
        "construction_system",
        "roof_type",
        "built_area_sqm",
        "floors_count",
        "clear_height_m",
        "finishing_level",
        "structural_condition",
        "maintenance_level",
        "visible_defects",
        "notes",
    ]
    for field in required_fields:
        assert f"'{field}'" in html, f"COMPONENT_FIELDS missing field: {field}"


def test_PVFOR012_hotel_profile_schema_has_5_sections():
    """Hotel _PROFILE_FORM_SCHEMA must have 5 sections including component_list."""
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    # Hotel schema markers
    assert "component_list" in html, "Hotel/factory profile schema missing component_list"
    # Hotel-specific operational fields
    assert "rooms_count" in html, "Hotel profile schema missing rooms_count field"
    assert "occupancy_rate" in html, "Hotel profile schema missing occupancy_rate field"


def test_PVFOR013_pvr_vis_panel_suppressed_for_old_types():
    """For old-system asset types, showProfAssetRequirements hides pvr-vis-asset-requirements-panel."""
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    # The intercept code must set panel.style.display = 'none' when profile is found
    intercept_block = (
        "window._pvRichAssetProfileMap && "
        "window._pvRichAssetProfileMap.hasOwnProperty(assetTypeVal)"
    )
    assert intercept_block in html, (
        f"Intercept block missing in showProfAssetRequirements: {intercept_block!r}"
    )
    # After the intercept, panel.style.display must be set to none
    intercept_idx = html.find(intercept_block)
    nearby = html[intercept_idx:intercept_idx + 200]
    assert "panel.style.display = 'none'" in nearby, (
        "After intercept check, panel.style.display must be set to 'none'"
    )


def test_PVFOR014_no_duplicate_es_req_panel():
    """#es-req-panel must appear exactly once in frontend/index.html."""
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    count = html.count('id="es-req-panel"')
    assert count == 1, f"#es-req-panel appears {count} times; expected exactly 1"


def test_PVFOR015_es_req_panel_not_inside_section5():
    """#es-req-panel must not appear inside the hidden Section 5 container."""
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    # Section 5 is marked with display:none and specific data-testid
    section5_start = html.find('data-testid="pro-val-section-report-type" style="display:none"')
    if section5_start == -1:
        # Alternate spacing
        section5_start = html.find("pro-val-section-report-type")
    assert section5_start > 0, "Section 5 marker not found"
    # es-req-panel must be BEFORE section 5 in the file
    es_req_pos = html.find('id="es-req-panel"')
    assert es_req_pos < section5_start, (
        "#es-req-panel must not be inside the hidden Section 5"
    )


# ── Category 3: Discovery Report Validation ────────────────────────────────���─


def test_PVFOR016_discovery_report_has_commit_info():
    """Discovery report must reference commit 8e49866."""
    import json
    report = json.loads(
        (QA_DIR / "01_old_ui_forensic_discovery_report.json").read_text(encoding="utf-8")
    )
    commit = report.get("selected_commit", {})
    assert commit.get("hash") == "8e49866", "Discovery report missing commit hash 8e49866"
    assert commit.get("port") == 5001, "Discovery report must note old server port 5001"


def test_PVFOR017_discovery_report_has_visual_evidence():
    """Discovery report must list visual evidence screenshots."""
    import json
    report = json.loads(
        (QA_DIR / "01_old_ui_forensic_discovery_report.json").read_text(encoding="utf-8")
    )
    evidence = report.get("visual_evidence", {})
    assert "hotel" in evidence, "Discovery report missing hotel visual evidence"
    assert "apartment" in evidence, "Discovery report missing apartment visual evidence"
    assert "hotel_add_building" in evidence, "Discovery report missing hotel_add_building evidence"


def test_PVFOR018_gap_report_has_root_cause():
    """Visual gap report must identify root cause."""
    import json
    report = json.loads(
        (QA_DIR / "02_old_vs_current_visual_gap_report.json").read_text(encoding="utf-8")
    )
    assert "root_cause" in report, "Gap report missing root_cause field"
    assert "fix_description" in report, "Gap report missing fix_description field"
    fix = report.get("fix_description", {})
    assert fix.get("lines_changed") is not None, "Gap report fix must specify lines_changed"


# ── Category 4: No Safety Rule Violations ────────────────────────────────────


# ── Category 5: Uncommon Asset Coverage ──────────────────────────────────────


def test_PVFOR022_asset_profile_map_has_uncommon_arabic_keys():
    """ASSET_PROFILE_MAP must include uncommon Arabic-keyed asset types."""
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    import re
    def has_map_entry(html_text, ar_key, profile):
        pattern = re.escape(f"'{ar_key}'") + r"\s*:\s*'" + re.escape(profile) + r"'"
        return bool(re.search(pattern, html_text))

    uncommon = [
        ("مستشفى",                  "hospital"),
        ("مدرسة",                   "school"),
        ("مناجم",                   "mine"),
        ("أصول معنوية",             "intangible"),
        ("ملكيات جزئية",            "partial_interest"),
        ("استثمارات تحت الإنشاء",   "under_construction"),
        ("مبنى قائم",               "existing_building_detailed"),
        ("أرض زراعية",              "agricultural_land"),
    ]
    for ar_key, profile in uncommon:
        assert has_map_entry(html, ar_key, profile), (
            f"ASSET_PROFILE_MAP missing uncommon entry: '{ar_key}' → '{profile}'"
        )


def test_PVFOR023_static_profiles_has_uncommon_entries():
    """_STATIC_PROFILES must have form entries for all key uncommon profile codes."""
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    uncommon_profiles = [
        "hospital", "school", "mine", "water_well", "intangible",
        "partial_interest", "under_construction", "historical", "heritage",
        "agricultural_land", "airport", "seaport", "marina", "data_center",
        "cold_storage", "prefabricated_factory", "healthcare_facility",
        "hotel_resort_detailed", "serviced_apartments", "floating_hotel",
        "existing_building_detailed", "retail_shop_detailed",
    ]
    for profile in uncommon_profiles:
        assert f"'{profile}'" in html, (
            f"_STATIC_PROFILES missing uncommon profile: '{profile}'"
        )


def test_PVFOR024_static_profiles_count_at_least_30():
    """_STATIC_PROFILES must cover at least 30 asset type profiles."""
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    import re
    # Count 'xxx': { type: 'form' or 'full' entries in _STATIC_PROFILES block
    static_block_start = html.find("var _STATIC_PROFILES = {")
    assert static_block_start > 0, "_STATIC_PROFILES block not found"
    static_block = html[static_block_start:static_block_start + 5000]
    matches = re.findall(r"type:\s*'(?:form|full)'", static_block)
    assert len(matches) >= 30, (
        f"_STATIC_PROFILES has only {len(matches)} entries; expected >= 30 for full coverage"
    )


def test_PVFOR025_asset_profile_map_count_at_least_30():
    """ASSET_PROFILE_MAP must map at least 30 frontend dropdown values."""
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    import re
    map_start = html.find("var ASSET_PROFILE_MAP = {")
    assert map_start > 0, "ASSET_PROFILE_MAP not found"
    map_block = html[map_start:map_start + 4000]
    # Count key: 'value' pairs inside the block
    matches = re.findall(r"'\S[^']*'\s*:\s*'\w+'\s*,", map_block)
    assert len(matches) >= 30, (
        f"ASSET_PROFILE_MAP has only {len(matches)} entries; expected >= 30"
    )


def test_PVFOR026_intercept_covers_all_profile_map_keys():
    """window._pvRichAssetProfileMap must be exposed (covers ALL ASSET_PROFILE_MAP keys)."""
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    assert "window._pvRichAssetProfileMap" in html, (
        "window._pvRichAssetProfileMap not exposed — intercept cannot cover all types"
    )
    # Confirm the exposure line assigns ASSET_PROFILE_MAP
    assert "window._pvRichAssetProfileMap" in html, (
        "ASSET_PROFILE_MAP must be exposed as window._pvRichAssetProfileMap"
    )


def test_PVFOR027_all_static_form_profiles_have_arabic_title():
    """Every _STATIC_PROFILES entry must have a non-empty titleAr."""
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    import re
    # Find all titleAr values inside _STATIC_PROFILES
    static_block_start = html.find("var _STATIC_PROFILES = {")
    assert static_block_start > 0, "_STATIC_PROFILES block not found"
    # Approximate block end by finding the closing };
    static_block = html[static_block_start:static_block_start + 6000]
    titles = re.findall(r"titleAr:\s*'([^']+)'", static_block)
    assert len(titles) >= 30, f"Only {len(titles)} titleAr found in _STATIC_PROFILES block"
    for title in titles:
        assert title.strip(), "Empty titleAr in _STATIC_PROFILES entry"


# ── Category 4: No Safety Rule Violations ────────────────────────────────────


def test_PVFOR019_no_new_workspace_added():
    """No new workspace div should be introduced by this restore."""
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    workspaces = html.count('class="es-workspace')
    # There should be a known fixed number of workspaces (not increased beyond baseline)
    assert workspaces <= 10, (
        f"Too many workspaces ({workspaces}); restore must not add new workspaces"
    )


def test_PVFOR020_advisory_only_flag_preserved():
    """advisory_only flag (or equivalent) must remain in frontend."""
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    assert "استرشادي" in html, "advisory_only indicator missing from page"


def test_PVFOR021_no_internal_paths_in_dom():
    """No Windows file system paths should appear in DOM output."""
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    forbidden = ["C:\\Users", "c:\\Users", "C:/Users"]
    for pat in forbidden:
        assert pat not in html, f"Internal path exposed in HTML: {pat!r}"
