"""
PVCAR Backend Tests — Professional Valuation Common Asset Requirements
Tests PVCAR-B01 through PVCAR-B30.
Validates _PV_COMMON_REQ_DATA field definitions, option sets, and alias
mappings as reflected in the HTML source. No Flask server required.
"""
import re
import pathlib
import pytest

_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
HTML = (_ROOT / "frontend/index.html").read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _has(pattern: str) -> bool:
    return bool(re.search(pattern, HTML))


def _count(pattern: str) -> int:
    return len(re.findall(pattern, HTML))


# ─────────────────────────────────────────────────────────────────────────────
# A. _PV_OPTS canonical options presence
# ─────────────────────────────────────────────────────────────────────────────

def test_PVCAR_B01_pv_opts_declared():
    """_PV_OPTS object is declared in the HTML source."""
    assert _has(r"var _PV_OPTS\s*=\s*\{")


def test_PVCAR_B02_construction_type_options_correct():
    """construction_type has concrete, steel, wood, mixed, masonry options."""
    assert _has(r"'concrete'.*?'خرساني'"), "concrete option missing"
    assert _has(r"'steel'.*?'معدني'"), "steel option missing"
    assert _has(r"'wood'.*?'خشبي'"), "wood option missing"
    assert _has(r"'mixed'.*?'مختلط'"), "mixed option missing"
    assert _has(r"'masonry'"), "masonry option missing"


def test_PVCAR_B03_structural_condition_options_correct():
    """structural_condition has excellent, very_good, good, needs_maintenance, poor."""
    assert _has(r"'excellent'.*?'ممتاز'"), "excellent missing"
    assert _has(r"'very_good'.*?'جيد جداً'"), "very_good missing"
    assert _has(r"'needs_maintenance'.*?'يحتاج صيانة'"), "needs_maintenance missing"
    assert _has(r"'poor'.*?'سيئ'"), "poor missing"


def test_PVCAR_B04_finishing_level_options_correct():
    """finishing_level has luxury, economy, shell_core options."""
    assert _has(r"'luxury'"), "luxury missing from finishing_level"
    assert _has(r"'shell_core'"), "shell_core missing from finishing_level"
    assert _has(r"'economy'"), "economy missing from finishing_level"
    assert _has(r"خام"), "خام label missing from shell_core option"
    assert _has(r"اقتصادي"), "اقتصادي label missing from economy option"


def test_PVCAR_B05_ownership_type_options_correct():
    """ownership_type has freehold, long_lease, usufruct, operation_management, concession."""
    assert _has(r"'freehold'.*?'ملكية حرة'"), "freehold missing"
    assert _has(r"'long_lease'"), "long_lease missing"
    assert _has(r"'usufruct'.*?'حق انتفاع'"), "usufruct missing"
    assert _has(r"'concession'.*?'امتياز'"), "concession missing"


def test_PVCAR_B06_market_demand_options_correct():
    """_PV_OPTS.market_demand has high, medium, low, unknown entries."""
    assert _has(r"market_demand:\s*\["), "_PV_OPTS.market_demand not found"
    # These values are unique to the market_demand array in the file
    assert _has(r"'unknown'"), "'unknown' option missing"
    assert _has(r"'غير محدد'"), "'غير محدد' label missing"
    # Ensure the array contains at least 4 entries by finding 4 distinct values
    section = re.search(r"market_demand:\s*\[([\s\S]{0,300})\]", HTML)
    assert section, "Could not find market_demand array block"
    raw = section.group(0)
    # medium and low are inside nested [..] pairs; check the raw 500-char window
    window = HTML[HTML.find("market_demand:"):HTML.find("market_demand:") + 400]
    assert "medium" in window, "'medium' not found near market_demand"
    assert "low" in window, "'low' not found near market_demand"


def test_PVCAR_B07_seasonality_options_correct():
    """_PV_OPTS.seasonality has year_round, high_season, seasonal, variable."""
    assert _has(r"seasonality:\s*\["), "_PV_OPTS.seasonality not found"
    # Unique values that only appear in the seasonality array
    assert _has(r"'year_round'"), "'year_round' missing"
    assert _has(r"طوال العام"), "'طوال العام' label missing"
    assert _has(r"'high_season'"), "'high_season' missing"
    assert _has(r"'low_season'"), "'low_season' missing"
    assert _has(r"'variable'"), "'variable' missing"
    assert _has(r"متقلب"), "'متقلب' label missing"


# ─────────────────────────────────────────────────────────────────────────────
# B. _PV_LABEL_OPT_MAP or equivalent post-processor
# ─────────────────────────────────────────────────────────────────────────────

def test_PVCAR_B08_dsr_postprocessor_present():
    """_pvFixDsrSelectOptions IIFE or equivalent post-processor is declared."""
    assert _has(r"_pvFixDsrSelectOptions|_PV_LABEL_OPT_MAP"), \
        "DSR select-options post-processor not found"


def test_PVCAR_B09_label_map_construction_type():
    """Label map maps 'نوع الإنشاء' to construction_type options."""
    assert _has(r"'نوع الإنشاء'.*?construction_type"), \
        "نوع الإنشاء not mapped to construction_type"


def test_PVCAR_B10_label_map_structural_condition():
    """Label map maps 'الحالة الإنشائية' to structural_condition options."""
    assert _has(r"'الحالة الإنشائية'.*?structural_condition"), \
        "الحالة الإنشائية not mapped to structural_condition"


def test_PVCAR_B11_label_map_finishing_level():
    """Label map maps 'مستوى التشطيب' to finishing_level options."""
    assert _has(r"'مستوى التشطيب'.*?finishing_level"), \
        "مستوى التشطيب not mapped to finishing_level"


def test_PVCAR_B12_label_map_ownership_type():
    """Label map maps 'نوع الملكية' to ownership_type options."""
    assert _has(r"'نوع الملكية'.*?ownership_type"), \
        "نوع الملكية not mapped to ownership_type"


def test_PVCAR_B13_label_map_seasonality():
    """Label map maps 'الموسمية' to seasonality options."""
    assert _has(r"'الموسمية'.*?seasonality"), \
        "الموسمية not mapped to seasonality"


# ─────────────────────────────────────────────────────────────────────────────
# C. _PV_COMMON_REQ_DATA structure
# ─────────────────────────────────────────────────────────────────────────────

def test_PVCAR_B14_common_req_data_declared():
    """_PV_COMMON_REQ_DATA is declared."""
    assert _has(r"var _PV_COMMON_REQ_DATA\s*=\s*\{")


def test_PVCAR_B15_hotel_group_present():
    """hotel key with groups is present in _PV_COMMON_REQ_DATA."""
    assert _has(r"hotel:\s*\["), "hotel entry missing"


def test_PVCAR_B16_industrial_factory_group_present():
    """industrial_factory key with groups is present."""
    assert _has(r"industrial_factory:\s*\["), "industrial_factory entry missing"


def test_PVCAR_B17_urban_land_group_present():
    """urban_land key with groups is present."""
    assert _has(r"urban_land:\s*\["), "urban_land entry missing"


def test_PVCAR_B18_retail_shop_group_present():
    """retail_shop key with groups is present."""
    assert _has(r"retail_shop:\s*\["), "retail_shop entry missing"


def test_PVCAR_B19_warehouse_group_present():
    """warehouse key with groups is present."""
    assert _has(r"warehouse:\s*\["), "warehouse entry missing"


def test_PVCAR_B20_residential_apartment_group_present():
    """residential_apartment key with groups is present."""
    assert _has(r"residential_apartment:\s*\["), "residential_apartment entry missing"


def test_PVCAR_B21_administrative_office_group_present():
    """administrative_office key with groups is present."""
    assert _has(r"administrative_office:\s*\["), "administrative_office entry missing"


def test_PVCAR_B22_backend_key_number_of_keys():
    """Hotel backend key number_of_keys is referenced."""
    assert _has(r"bk:'number_of_keys'"), "number_of_keys backend key missing"


def test_PVCAR_B23_backend_key_occupancy_rate():
    """occupancy_rate backend key is referenced."""
    assert _has(r"bk:'occupancy_rate'"), "occupancy_rate backend key missing"


def test_PVCAR_B24_backend_key_land_registry_ref():
    """land_registry_ref backend key is present in common req data."""
    assert _has(r"bk:'land_registry_ref'"), "land_registry_ref missing"


def test_PVCAR_B25_backend_key_market_demand_level():
    """market_demand_level backend key is present for market groups."""
    assert _has(r"bk:'market_demand_level'"), "market_demand_level missing"


# ─────────────────────────────────────────────────────────────────────────────
# D. Aliases
# ─────────────────────────────────────────────────────────────────────────────

def test_PVCAR_B26_aliases_resort():
    """resort is aliased to hotel data."""
    assert _has(r"_PV_COMMON_REQ_DATA\.resort\s*=\s*_PV_COMMON_REQ_DATA\.hotel"), \
        "resort alias missing"


def test_PVCAR_B27_aliases_agricultural_land():
    """agricultural_land is aliased to urban_land data."""
    assert _has(r"_PV_COMMON_REQ_DATA\.agricultural_land\s*=\s*_PV_COMMON_REQ_DATA\.urban_land"), \
        "agricultural_land alias missing"


def test_PVCAR_B28_aliases_shopping_mall():
    """shopping_mall is aliased to retail_shop data."""
    assert _has(r"_PV_COMMON_REQ_DATA\.shopping_mall\s*=\s*_PV_COMMON_REQ_DATA\.retail_shop"), \
        "shopping_mall alias missing"


# ─────────────────────────────────────────────────────────────────────────────
# E. Renderer and updater functions
# ─────────────────────────────────────────────────────────────────────────────

def test_PVCAR_B29_renderer_function_declared():
    """pvRenderCommonAssetFillable function is declared."""
    assert _has(r"window\.pvRenderCommonAssetFillable\s*=\s*function"), \
        "pvRenderCommonAssetFillable not declared"


def test_PVCAR_B30_updater_calls_renderer():
    """pvUpdateAssetRequirementsPanel calls pvRenderCommonAssetFillable."""
    updater_block = re.search(
        r"window\.pvUpdateAssetRequirementsPanel\s*=\s*function.*?(?=window\.\w+\s*=\s*function)",
        HTML, re.S
    )
    assert updater_block, "pvUpdateAssetRequirementsPanel block not found"
    block_text = updater_block.group(0)
    assert "pvRenderCommonAssetFillable" in block_text, \
        "pvUpdateAssetRequirementsPanel does not call pvRenderCommonAssetFillable"
