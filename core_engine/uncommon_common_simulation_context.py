"""
Phase UCS — Uncommon Common Simulation Context
advisory_only=True — not_real_training
"""

uncommon_common_simulation_context = {
    "direct_common_simulation_enabled":          True,
    "working_common_renderer_reused":            True,
    "separate_uncommon_renderer_disabled":       True,
    "uncommon_assets_simulate_common_requirements": True,

    "common_renderer_function":  "renderStaticPanel (Phase-8B IIFE) called via fetchChecklist → _STATIC_PROFILES",
    "common_container_selector": "#es-req-panel",
    "common_css_classes":        ["es-form-section", "es-component-card", "es-component-grid", "es-field", "es-doc-row", "es-chip"],
    "common_group_renderer":     "_sectionControlsHTML(heading, color, desc, fields)",
    "common_field_renderer":     "_fieldControlHTML(field)",
    "common_repeatable_renderer":"_renderComponentSection(cfg, containerEl)",
    "common_upload_clip_renderer": "_fieldControlHTML with field_type='bool', group='document', desc=_UPLOAD_HINT",
    "common_priority_badge_renderer": "ui_required=true fields rendered with * marker via _fieldControlHTML",
    "common_completion_renderer":   "esRequirementDraft draft collector via _attachDraftCollector",
    "common_context_collector":     "window.esRequirementDraft + pvCollectUncommonSimulatedRequirementValues()",

    "uncommon_asset_mapping": {
        "petrol_station":                           "industrial_factory_or_mixed_use_template",
        "hospital":                                 "building_or_hotel_component_template",
        "school":                                   "building_or_mixed_use_template",
        "cinema_theater":                           "commercial_or_building_template",
        "sports_padel_club":                        "land_service_component_template",
        "architectural_cultural_heritage_detailed": "building_legal_document_template",
        "mixed_use_special":                        "mixed_use_asset_template",
        "hotel":                                    "hotel_resort_golden_reference_template",
    },

    "uncommon_asset_keys_still_using_weak_renderer": [],
    "style_parity_with_common_assets":               True,
    "common_asset_tables_preserved":                 True,
    "deleted_old_requirements":                      [],
    "deleted_old_options":                           [],
    "preservation_pass":                             True,

    "uncommon_asset_keys_detected": [
        "petrol_station",
        "hospital",
        "school",
        "cinema_theater",
        "sports_padel_club",
        "architectural_cultural_heritage_detailed",
        "mixed_use_special",
        "hotel",
    ],
    "uncommon_asset_keys_mapped_to_common_simulation": [
        "petrol_station",
        "hospital",
        "school",
        "cinema_theater",
        "sports_padel_club",
        "architectural_cultural_heritage_detailed",
        "mixed_use_special",
        "hotel",
    ],

    "upload_clips_enabled":           True,
    "priority_badges_enabled":        True,
    "completion_validation_enabled":  True,
    "repeatable_groups_enabled":      True,
    "unified_context_sync_enabled":   True,

    "data_attribute_engine":            "old-style-common-simulation",
    "data_uncommon_simulates_common":   "true",
    "runtime_renderer_debug_enabled":   True,
    "debug_uncommon_simulates_common":  True,

    "wrapper_functions": [
        "pvRenderUncommonAsCommonStyleRequirements",
        "pvBuildUncommonCommonStyleRequirementConfig",
        "pvMapUncommonAssetToCommonTemplate",
        "pvGetUncommonSimulatedRequirementGroups",
        "pvDisableWeakUncommonRenderer",
        "pvAssertUncommonUsesCommonSimulation",
        "pvCollectUncommonSimulatedRequirementValues",
        "pvSyncUncommonSimulatedValuesToUnifiedContext",
    ],

    "no_internal_paths":  True,
    "no_commit_made":     True,
    "advisory_only":      True,
    "not_real_training":  True,
}
