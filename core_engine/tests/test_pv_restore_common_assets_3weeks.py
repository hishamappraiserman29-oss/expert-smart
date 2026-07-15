"""
PVRCА: Professional Valuation — Restore Common Asset Requirement Tables (3+ Weeks)
Backend tests — verify data completeness and structural integrity of _PV_COMMON_REQ_DATA
as represented in frontend/index.html (working tree).

Tests: PVRCA-B01 through PVRCA-B25
Run: python -m pytest core_engine/tests/test_pv_restore_common_assets_3weeks.py -q
"""
import pathlib, re, json, pytest

HTML = pathlib.Path("frontend/index.html").read_text(encoding="utf-8")

# ─── helpers ───────────────────────────────────────────────────────────────────

def _bk_in_html(backend_key: str) -> bool:
    return f"bk:'{backend_key}'" in HTML or f'bk:"{backend_key}"' in HTML

def _opt_in_html(opt_key: str) -> bool:
    return f"_PV_OPTS.{opt_key}" in HTML

def _key_has_entry(data_key: str) -> bool:
    return (
        f"        {data_key}: [" in HTML or
        f"        {data_key}:[" in HTML
    )

def _title_in_html(title_ar: str) -> bool:
    return f"title:'{title_ar}'" in HTML or f'title:"{title_ar}"' in HTML

def _count_groups_for_key(key: str) -> int:
    pattern = re.compile(
        rf"        {key}: \[(.+?)\n        \],",
        re.DOTALL
    )
    m = pattern.search(HTML)
    if not m:
        return 0
    block = m.group(1)
    return len(re.findall(r"title:'[^']+'", block))

# ─── Part A: Git history search confirmed ──────────────────────────────────────

def test_PVRCA_B01_git_history_report_exists():
    """01_deep_git_history_recovery_report.json must exist."""
    p = pathlib.Path(
        "core_engine/instance/manual_review_outputs/"
        "professional_valuation_restore_common_assets_3weeks/"
        "01_deep_git_history_recovery_report.json"
    )
    assert p.exists()

def test_PVRCA_B02_git_search_parameters():
    """Git history report must confirm searched_days_back >= 45 and all branches."""
    p = pathlib.Path(
        "core_engine/instance/manual_review_outputs/"
        "professional_valuation_restore_common_assets_3weeks/"
        "01_deep_git_history_recovery_report.json"
    )
    data = json.loads(p.read_text(encoding="utf-8"))
    params = data["search_parameters"]
    assert params["searched_days_back"] >= 45
    assert params["searched_all_branches"] is True
    assert params["searched_reflog"] is True
    assert params["searched_stashes"] is True

def test_PVRCA_B03_old_tables_found():
    """Git history report must confirm old_common_asset_tables_found = true."""
    p = pathlib.Path(
        "core_engine/instance/manual_review_outputs/"
        "professional_valuation_restore_common_assets_3weeks/"
        "01_deep_git_history_recovery_report.json"
    )
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["old_implementation_found"] is True
    vals = data.get("required_values", {})
    assert vals.get("old_common_asset_tables_found") is True
    assert vals.get("restoration_method") == "git_history_restore"

# ─── Part B: _PV_COMMON_REQ_DATA primary entries ──────────────────────────────

def test_PVRCA_B04_all_primary_entries_exist():
    """_PV_COMMON_REQ_DATA must have all 10 primary entries as distinct entries."""
    keys = [
        "hotel", "industrial_factory", "urban_land", "retail_shop",
        "warehouse", "residential_apartment", "administrative_office",
        "residential_villa", "agricultural_land", "mixed_use_asset"
    ]
    for k in keys:
        assert _key_has_entry(k), f"Missing primary entry: {k}"

def test_PVRCA_B05_residential_apartment_group_count():
    """residential_apartment must have >=8 groups (enriched from old schema)."""
    n = _count_groups_for_key("residential_apartment")
    assert n >= 8, f"Expected >=8 groups, got {n}"

def test_PVRCA_B06_residential_apartment_old_backend_keys_preserved():
    """All 23 original backend keys must still be present in HTML."""
    old_keys = [
        "gross_area_sqm", "net_area_sqm", "bedroom_count", "bathroom_count",
        "floor_level", "building_floors_count", "construction_year",
        "construction_type", "structural_condition", "finishing_level",
        "parking_spots", "has_elevator", "has_storage", "has_garden_pool",
        "has_security", "ownership_type", "land_registry_ref",
        "encumbrances_notes", "title_deed_doc", "market_demand_level",
        "market_comparable_price_sqm", "market_comparable_rent_sqm", "rental_yield_pct"
    ]
    for k in old_keys:
        assert _bk_in_html(k), f"Old backend key missing: {k}"

def test_PVRCA_B07_residential_apartment_new_groups_present():
    """New groups from old schema must be in HTML for residential_apartment."""
    new_titles = [
        "خصائص الوحدة",
        "خصائص الموقع والمبنى",
        "التشطيب والحالة الفنية",
        "الوضع التشغيلي والدخل",
        "مستندات الوحدة",
        "الخصائص المادية التفصيلية",
        "الخصائص القانونية والملكية",
    ]
    for t in new_titles:
        assert _title_in_html(t), f"Missing group title: {t}"

def test_PVRCA_B08_residential_apartment_new_backend_keys():
    """New backend keys from old b3d3c34 schema must be present."""
    new_keys = [
        "unit_subtype", "reception_count", "balcony_count",
        "building_type", "orientation", "view_quality", "noise_exposure_level",
        "finishing_age_years", "maintenance_level", "finishing_quality_detail",
        "occupancy_status", "rental_income_monthly", "service_charges_monthly",
        "ru_building_permit", "ru_receipt_alloc", "ru_unit_plan",
        "land_share_sqm", "building_age_years", "terrace_area_sqm",
        "title_deed_type", "mortgage_or_lien_status", "building_permit_status",
        "registration_status", "common_area_share_pct", "legal_restrictions_summary"
    ]
    for k in new_keys:
        assert _bk_in_html(k), f"New backend key missing: {k}"

# ─── Part C: New distinct entries ─────────────────────────────────────────────

def test_PVRCA_B09_residential_villa_distinct():
    """residential_villa must be a distinct entry (not just alias)."""
    assert _key_has_entry("residential_villa"), "residential_villa has no distinct entry"

def test_PVRCA_B10_residential_villa_villa_specific_fields():
    """residential_villa must include villa-specific fields."""
    villa_keys = ["land_area_sqm", "built_area_sqm", "has_private_pool", "has_private_roof"]
    for k in villa_keys:
        assert _bk_in_html(k), f"Villa-specific key missing: {k}"

def test_PVRCA_B11_agricultural_land_distinct():
    """agricultural_land must be a distinct entry (not just alias to urban_land)."""
    assert _key_has_entry("agricultural_land"), "agricultural_land has no distinct entry"
    assert "agricultural_land    = _PV_COMMON_REQ_DATA.urban_land" not in HTML, \
        "agricultural_land is still aliased to urban_land — must be distinct"

def test_PVRCA_B12_agricultural_land_specific_fields():
    """agricultural_land must include agricultural-specific fields."""
    agri_keys = [
        "soil_type", "irrigation_type", "current_crops_or_use",
        "water_sources", "farm_buildings_available", "cultivated_area_sqm"
    ]
    for k in agri_keys:
        assert _bk_in_html(k), f"Agricultural key missing: {k}"

def test_PVRCA_B13_mixed_use_asset_distinct():
    """mixed_use_asset must be a distinct entry (not just alias to retail_shop)."""
    assert _key_has_entry("mixed_use_asset"), "mixed_use_asset has no distinct entry"
    assert "mixed_use_asset      = _PV_COMMON_REQ_DATA.retail_shop" not in HTML, \
        "mixed_use_asset is still aliased to retail_shop — must be distinct"

def test_PVRCA_B14_mixed_use_asset_specific_fields():
    """mixed_use_asset must include mixed-use-specific fields."""
    mixed_keys = [
        "residential_area_sqm", "commercial_area_sqm",
        "total_annual_rental_income", "overall_occupancy_rate"
    ]
    for k in mixed_keys:
        assert _bk_in_html(k), f"Mixed-use key missing: {k}"

# ─── Part D: New _PV_OPTS entries ─────────────────────────────────────────────

def test_PVRCA_B15_new_pv_opts_unit_subtype():
    assert _opt_in_html("unit_subtype"), "_PV_OPTS.unit_subtype missing"

def test_PVRCA_B16_new_pv_opts_building_type_res():
    assert _opt_in_html("building_type_res"), "_PV_OPTS.building_type_res missing"

def test_PVRCA_B17_new_pv_opts_orientation():
    assert _opt_in_html("orientation"), "_PV_OPTS.orientation missing"

def test_PVRCA_B18_new_pv_opts_maintenance_level():
    assert _opt_in_html("maintenance_level"), "_PV_OPTS.maintenance_level missing"

def test_PVRCA_B19_new_pv_opts_occupancy_status():
    assert _opt_in_html("occupancy_status"), "_PV_OPTS.occupancy_status missing"

def test_PVRCA_B20_new_pv_opts_view_quality():
    assert _opt_in_html("view_quality"), "_PV_OPTS.view_quality missing"

def test_PVRCA_B21_new_pv_opts_title_deed_type():
    assert _opt_in_html("title_deed_type"), "_PV_OPTS.title_deed_type missing"

def test_PVRCA_B22_new_pv_opts_soil_irrigation():
    assert _opt_in_html("soil_type"), "_PV_OPTS.soil_type missing"
    assert _opt_in_html("irrigation_type"), "_PV_OPTS.irrigation_type missing"

# ─── Part E: Aliases and Arabic mappings ──────────────────────────────────────

def test_PVRCA_B23_arabic_villa_alias():
    """Arabic 'فيلا' must alias to residential_villa."""
    assert "'فيلا'" in HTML and "residential_villa" in HTML
    pattern = re.compile(r"\['فيلا'\]\s*=\s*_PV_COMMON_REQ_DATA\.residential_villa")
    assert pattern.search(HTML), "Arabic 'فيلا' alias must point to residential_villa"

def test_PVRCA_B24_arabic_agricultural_land_alias():
    """Arabic 'أرض زراعية' must alias to agricultural_land (not urban_land)."""
    pattern = re.compile(r"\['أرض زراعية'\]\s*=\s*_PV_COMMON_REQ_DATA\.agricultural_land")
    assert pattern.search(HTML), "Arabic 'أرض زراعية' must point to agricultural_land"
    bad = re.compile(r"\['أرض زراعية'\]\s*=\s*_PV_COMMON_REQ_DATA\.urban_land")
    assert not bad.search(HTML), "Arabic 'أرض زراعية' must NOT point to urban_land"

def test_PVRCA_B25_renderer_and_visibility_function_present():
    """pvRenderCommonAssetFillable and showProfAssetRequirements must be in HTML."""
    assert "pvRenderCommonAssetFillable" in HTML, "pvRenderCommonAssetFillable missing"
    assert "showProfAssetRequirements" in HTML, "showProfAssetRequirements missing"
    assert "pvr-vis-asset-requirements-panel" in HTML, "requirements panel div missing"
    assert "pvr-vis-car-body" in HTML, "pvr-vis-car-body div missing"
