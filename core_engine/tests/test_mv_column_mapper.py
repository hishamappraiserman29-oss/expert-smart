"""
test_mv_column_mapper.py — P12 tests: Column Mapping (D-02).
Tests: CM-01 → CM-17
"""
import pytest

from core_engine.mass_valuation.column_mapper import (
    MappingResult,
    map_record,
    resolve_canonical_name,
    canonical_fields,
)


# ---------------------------------------------------------------------------
# CM-01  Canonical fields pass through unchanged
# ---------------------------------------------------------------------------

def test_cm_01_canonical_passthrough():
    """D-02: canonical field names resolve to themselves."""
    result = map_record({
        "property_id":       "P-001",
        "property_type":     "residential",
        "city":              "Riyadh",
        "land_area_m2":      "300",
        "transaction_price": "2000000",
    })
    assert result.canonical["property_id"] == "P-001"
    assert result.canonical["property_type"] == "residential"


# ---------------------------------------------------------------------------
# CM-02  CSV alias resolution
# ---------------------------------------------------------------------------

def test_cm_02_csv_alias_property_no():
    """D-02: 'Property_No' alias resolves to canonical 'property_id'."""
    result = map_record({"Property_No": "P-CSV-001"})
    assert "property_id" in result.canonical
    assert result.canonical["property_id"] == "P-CSV-001"


def test_cm_03_csv_alias_sale_value():
    """D-02: 'Sale_Value' alias resolves to canonical 'transaction_price'."""
    result = map_record({"Sale_Value": "1500000"})
    assert "transaction_price" in result.canonical


def test_cm_04_csv_alias_sale_date():
    """D-02: 'Sale_Date' alias resolves to canonical 'transaction_date'."""
    result = map_record({"Sale_Date": "2024-03-15"})
    assert "transaction_date" in result.canonical
    assert result.canonical["transaction_date"] == "2024-03-15"


# ---------------------------------------------------------------------------
# CM-05  XLSX / alternative alias forms
# ---------------------------------------------------------------------------

def test_cm_05_xlsx_alias_land_area():
    """D-02: 'Plot_Area' alias resolves to canonical 'land_area_m2'."""
    result = map_record({"Plot_Area": "500"})
    assert "land_area_m2" in result.canonical


def test_cm_06_xlsx_alias_built_up():
    """D-02: 'BUA' alias resolves to canonical 'built_up_area_m2'."""
    result = map_record({"BUA": "300"})
    assert "built_up_area_m2" in result.canonical


# ---------------------------------------------------------------------------
# CM-07  Case-insensitive alias matching
# ---------------------------------------------------------------------------

def test_cm_07_case_insensitive_upper():
    """D-02: alias lookup is case-insensitive (CITY → city)."""
    result = map_record({"CITY": "Jeddah"})
    assert "city" in result.canonical


def test_cm_08_case_insensitive_mixed():
    """D-02: mixed-case alias 'PropertyID' resolves to 'property_id'."""
    result = map_record({"PropertyID": "P-002"})
    assert "property_id" in result.canonical
    assert result.canonical["property_id"] == "P-002"


# ---------------------------------------------------------------------------
# CM-09  Arabic alias resolution
# ---------------------------------------------------------------------------

def test_cm_09_arabic_alias_property_id():
    """D-02: Arabic alias رقم_العقار resolves to 'property_id'."""
    result = map_record({"رقم_العقار": "P-AR-001"})
    assert "property_id" in result.canonical
    assert result.canonical["property_id"] == "P-AR-001"


def test_cm_10_arabic_alias_city():
    """D-02: Arabic alias المدينة resolves to 'city'."""
    result = map_record({"المدينة": "الرياض"})
    assert "city" in result.canonical


def test_cm_11_arabic_alias_transaction_price():
    """D-02: Arabic alias قيمة_الصفقة resolves to 'transaction_price'."""
    result = map_record({"قيمة_الصفقة": "2500000"})
    assert "transaction_price" in result.canonical


# ---------------------------------------------------------------------------
# CM-12  Arabic value maps
# ---------------------------------------------------------------------------

def test_cm_12_arabic_value_map_property_type_residential():
    """D-02: Arabic value 'سكني' maps to canonical 'residential'."""
    result = map_record({"property_type": "سكني"})
    assert result.canonical["property_type"] == "residential"


def test_cm_13_arabic_value_map_property_type_commercial():
    """D-02: Arabic value 'تجاري' maps to canonical 'commercial'."""
    result = map_record({"property_type": "تجاري"})
    assert result.canonical["property_type"] == "commercial"


def test_cm_14_arabic_value_map_condition_good():
    """D-02: Arabic condition 'جيد' maps to canonical 'good'."""
    result = map_record({"condition": "جيد"})
    assert result.canonical["condition"] == "good"


def test_cm_15_arabic_value_map_condition_excellent():
    """D-02: Arabic condition 'ممتاز' maps to canonical 'excellent'."""
    result = map_record({"condition": "ممتاز"})
    assert result.canonical["condition"] == "excellent"


def test_cm_16_arabic_value_map_use_owner_occupied():
    """D-02: Arabic use 'مالك' maps to canonical 'owner_occupied'."""
    result = map_record({"use": "مالك"})
    assert result.canonical["use"] == "owner_occupied"


def test_cm_17_arabic_value_map_quality_finish_luxury():
    """D-02: Arabic quality_finish 'فاخر' maps to canonical 'luxury'."""
    result = map_record({"quality_finish": "فاخر"})
    assert result.canonical["quality_finish"] == "luxury"


def test_cm_18_arabic_value_map_evidence_type_registered_sale():
    """D-02: Arabic evidence_type 'صك_مسجّل' maps to canonical 'registered_sale'."""
    result = map_record({"evidence_type": "صك_مسجّل"})
    assert result.canonical["evidence_type"] == "registered_sale"


# ---------------------------------------------------------------------------
# CM-19  Unmapped keys are tracked
# ---------------------------------------------------------------------------

def test_cm_19_unmapped_keys_tracked():
    """D-02: keys with no alias match are collected in unmapped_keys."""
    result = map_record({
        "property_id":    "P-003",
        "unknown_column": "some_value",
        "another_junk":   "x",
    })
    assert "unknown_column" in result.unmapped_keys
    assert "another_junk" in result.unmapped_keys
    assert "property_id" not in result.unmapped_keys


# ---------------------------------------------------------------------------
# CM-20  to_float transform
# ---------------------------------------------------------------------------

def test_cm_20_to_float_land_area():
    """D-02: land_area_m2 string value is converted to float."""
    result = map_record({"land_area_m2": "350.5"})
    assert result.canonical["land_area_m2"] == 350.5
    assert isinstance(result.canonical["land_area_m2"], float)


# ---------------------------------------------------------------------------
# CM-21  title_case transform on city
# ---------------------------------------------------------------------------

def test_cm_21_title_case_city():
    """D-02: city field receives title_case transform."""
    result = map_record({"city": "riyadh"})
    assert result.canonical["city"] == "Riyadh"


# ---------------------------------------------------------------------------
# CM-22  Coordinates → nested dict
# ---------------------------------------------------------------------------

def test_cm_22_coordinates_nested():
    """D-02: latitude/longitude aliases produce nested coordinates dict."""
    result = map_record({"Latitude": "24.7136", "Longitude": "46.6753"})
    assert "coordinates" in result.canonical
    assert "latitude" in result.canonical["coordinates"]
    assert "longitude" in result.canonical["coordinates"]
    assert result.canonical["coordinates"]["latitude"] == 24.7136
    assert result.canonical["coordinates"]["longitude"] == 46.6753


# ---------------------------------------------------------------------------
# CM-23  resolve_canonical_name API
# ---------------------------------------------------------------------------

def test_cm_23_resolve_canonical_name_known():
    """D-02: resolve_canonical_name returns canonical field for known alias."""
    assert resolve_canonical_name("Sale_Value") == "transaction_price"
    assert resolve_canonical_name("PropertyNo") == "property_id"


def test_cm_24_resolve_canonical_name_unknown():
    """D-02: resolve_canonical_name returns None for unrecognised alias."""
    assert resolve_canonical_name("no_such_column") is None


# ---------------------------------------------------------------------------
# CM-25  canonical_fields API
# ---------------------------------------------------------------------------

def test_cm_25_canonical_fields_includes_required():
    """D-02: canonical_fields() includes all fields required by QR-001."""
    fields = canonical_fields()
    required = [
        "property_id", "property_type", "transaction_date",
        "transaction_price", "land_area_m2",
    ]
    for f in required:
        assert f in fields, f"canonical_fields() missing required field: {f}"


# ---------------------------------------------------------------------------
# CM-26  MappingResult is the correct type
# ---------------------------------------------------------------------------

def test_cm_26_map_record_returns_mapping_result():
    """D-02: map_record always returns a MappingResult instance."""
    result = map_record({})
    assert isinstance(result, MappingResult)
    assert isinstance(result.canonical, dict)
    assert isinstance(result.unmapped_keys, list)
    assert isinstance(result.warnings, list)
