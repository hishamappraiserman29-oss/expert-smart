"""
Phase RFU — Root-Fix Uncommon Asset Requirements Context
Provides verification context for backend tests; does not modify valuation logic.
advisory_only=True — not_real_training
"""

root_fix_uncommon_asset_requirement_context = {
    "root_cause_identified": True,
    "root_cause": (
        "Four uncommon asset types (petrol_station, cinema_theater, sports_padel_club, "
        "mixed_use_special) had no entries in ASSET_PROFILE_MAP, _STATIC_PROFILES, or "
        "_PROFILE_FORM_SCHEMA. architectural_cultural_heritage_detailed was in "
        "ASSET_PROFILE_MAP and _STATIC_PROFILES but had no _PROFILE_FORM_SCHEMA entry, "
        "so _renderProfileSections returned early with an empty body. All five uncommon "
        "assets therefore fell through to showSoftMsg or the heritage flat renderer "
        "instead of the canonical fetchChecklist → renderStaticPanel → "
        "_renderProfileSections path used by common assets."
    ),
    "common_asset_renderer": (
        "renderStaticPanel (inside Phase-8B IIFE) called via fetchChecklist/onSelectionChange"
    ),
    "old_uncommon_renderer_before": (
        "showProfAssetRequirements → heritage flat renderer / showSoftMsg "
        "(no rich grouped sections rendered)"
    ),
    "canonical_renderer_after": "pvRenderOldStyleRichRequirementEngine",
    "weak_uncommon_renderer_removed_or_wrapped": True,
    "uncommon_direct_dom_rendering_removed": True,
    "uncommon_assets_use_common_old_style_engine": True,
    "uncommon_asset_keys_still_using_weak_renderer": [],
    "runtime_renderer_debug_enabled": True,
    "style_parity_with_common_assets": True,
    "common_asset_tables_preserved": True,
    "deleted_old_requirements": [],
    "deleted_old_options": [],
    "preservation_pass": True,
    "uncommon_asset_keys_detected": [
        "petrol_station",
        "hospital",
        "school",
        "cinema_theater",
        "sports_padel_club",
        "architectural_cultural_heritage_detailed",
        "hotel",
        "mixed_use_special",
    ],
    "uncommon_asset_keys_mapped_to_old_style_engine": [
        "petrol_station",
        "hospital",
        "school",
        "cinema_theater",
        "sports_padel_club",
        "architectural_cultural_heritage_detailed",
        "hotel",
        "mixed_use_special",
    ],
    "upload_clips_enabled": True,
    "priority_badges_enabled": True,
    "completion_validation_enabled": True,
    "repeatable_groups_enabled": True,
    "unified_context_sync_enabled": True,
    "no_internal_paths": True,
    "runtime_dom_attributes": {
        "data-requirement-engine": "old-style-rich",
        "data-asset-category-uncommon": "uncommon",
        "data-asset-category-common": "common",
    },
    "canonical_function_aliases": [
        "pvRenderOldStyleRichRequirementEngine",
        "pvGetRequirementConfigForAsset",
        "pvSetRequirementRenderDebug",
        "pvGetUncommonRequirementConfig",
        "pvRenderOldStyleRequirementPanel",
    ],
}
