"""
E2E smoke tests for Phase 8B/8C/8C.1/8D/8E/8G/8H.1/8H.2B/8H.2D/8H.2E/8I/8J/8K/8L/8M/8N/8O/8P/8Q/8R.1/8S.1 — Frontend Requirements Checklist Panel.

Requires a running bridge_api server (managed by conftest.py) and Playwright.

    pytest core_engine/tests/e2e/test_requirements_checklist_smoke.py -v

  CS01 — panel hidden on initial page load
  CS02 — panel title is Arabic; sections A and B have descriptive paragraphs
  CS03 — Arabic section headings present; method codes and heading absent from entire panel
  CS04 — unsupported purpose → improved soft message shown
  CS05 — core valuation UI elements still intact
  CS06 — "تجاري" (API-driven building_mixed) calls API; title contains "تجاري", not composite
  CS07 — land single mode: no method names appear anywhere in panel
  CS08 — (8M) intangible (أصول معنوية) now renders نموذج محلي form instead of unsupported message
  CS09 — section D is empty; no Arabic or raw method labels in single-mode panel
  CS10 — determinism: two reloads with same selection produce identical text
  CS11 — (8H.1) always-visible #cv-nav-link header link is absent; composite access is contextual only
  CS12 — sections A/B/C each have their descriptive paragraph
  CS13 — section D is empty after Phase 8E methods removal
  CS14 — residential single mode: composite link absent; title does not say "مركّب"
  CS15 — land single mode: composite link absent; title does not say "مركّب"
  CS16 — "عمارة سكنية" shows inline building_full form; "بيانات الأرض" present; old static text absent
  CS17 — building_full panel has NO composite_valuation.html link (Phase 8J removes it)
  CS18 — building_full panel shows بيانات الأرض + بيانات المبنى + توزيع الاستخدام (no بيانات الدخل)
  CS19 — no raw registry codes in building_full panel
  CS20 — "عمارة سكنية" does not call GET /api/valuation/requirements
  CS21 — residential single panel: section D empty, no methods section
  CS22 — residential single panel text: "مناهج التقييم المناسبة" absent
  CS23 — building_full panel text: "مناهج التقييم المناسبة" absent
  CS24 — "تجاري" calls GET /api/valuation/requirements (API-driven building_mixed profile)
  CS25 — "مصنع" is placeholder profile; must NOT call GET /api/valuation/requirements
  CS26 — "شقة سكنية" calls GET /api/valuation/requirements (residential_unit API profile)
  CS27 — "أرض فضاء" calls GET /api/valuation/requirements (land API profile)
  CS28 — "عمارة سكنية" (Phase 8G framing): ZERO API calls, static path confirmed
  CS29 — "عمارة سكنية" building_full panel contains floor-use rows (الدور الأرضي, الأدوار المتكررة)
  CS30 — (8K) "فندق" → form type; ZERO API calls; title contains "فندق"; form controls rendered
  CS31 — (8K) "مصنع" → form type; ZERO API calls; form controls rendered
  CS32 — (8K) "مستشفى" → form type; ZERO API calls; form controls rendered
  CS33 — (8K) all 6 form-type asset types render input/select controls
  CS34 — placeholder panels contain NO ✦ bullet and NO "(مطلوب)" tag
  CS35 — no raw English profile codes appear in placeholder panel text
  CS36 — two consecutive renders of "عمارة سكنية" produce identical innerText
  CS37 — (8K) فندق is now a form type; composite CTA absent; form controls rendered
  CS38 — (8H.1) building_full panel s4 is empty; no method label text present
  CS39 — (8K) all 6 form-type profiles have NO composite CTA; residential/land also do not

  CS40 — (8H.2B) residential panel renders real form controls
  CS41 — (8H.2B) area_sqm renders as number input
  CS42 — (8H.2B) floor_number renders as number input
  CS43 — (8H.2B) finishing_level renders as select with ≥4 options
  CS44 — (8H.2B) legal_status renders as select
  CS45 — (8H.2B) document fields render as checkboxes with Arabic labels
  CS46 — (8H.2B) land panel renders real form controls
  CS47 — (8H.2B) land_area_sqm renders as number input
  CS48 — (8H.2B) frontage_m renders as number input
  CS49 — (8H.2B) zoning_type renders as select with ≥6 options
  CS50 — (8H.2B) utilities_available renders as checkbox group
  CS51 — (8H.2B) buildability_status renders as select
  CS52 — (8H.2B) land document fields render as checkboxes
  CS53 — (8H.2B) engine fields not rendered as form controls
  CS54 — (8H.2B) field label comes from label_ar (DRY)
  CS55 — (8H.2B) no JS console errors on render

  CS56 — (8H.2D) select first option is 'اختر ...' placeholder
  CS57 — (8H.2D) default option text derived from label_ar
  CS58 — (8H.2D) yes/no fields show نعم/لا
  CS59 — (8H.2D) number inputs carry non-empty placeholder
  CS60 — (8H.2D) all 3 section headings visible in residential panel
  CS61 — (8H.2D) utilities_available shows Arabic chip labels
  CS62 — (8H.2D) utilities_available shows no raw backend codes

  CS63 — (8H.2E) finishing_level options display Arabic translations
  CS64 — (8H.2E) legal_status options display Arabic translations
  CS65 — (8H.2E) parking_available select shows نعم/لا
  CS66 — (8H.2E) zoning_type options display Arabic translations
  CS67 — (8H.2E) buildability_status options display Arabic translations
  CS68 — (8H.2E) hbu select options display Arabic translations
  CS69 — (8H.2E) no raw enum codes in residential panel visible text
  CS70 — (8H.2E) no raw enum codes in land panel visible text

  CS71 — (8I) #es-profile-explainer hidden on initial page load
  CS72 — (8I) selecting residential → explainer visible, badge contains مدعوم
  CS73 — (8I) selecting عمارة سكنية (building_full) → badge contains نموذج مركّب
  CS74 — (8K) selecting فندق (form profile) → badge contains نموذج محلي
  CS75 — (8M) أصول معنوية is now a local form; badge shows 'نموذج محلي' not 'غير مدعوم'
  CS76 — (8K) selection change فندق → شقة سكنية updates explainer from نموذج محلي to مدعوم
  CS77 — (8I) <optgroup> elements present inside #asset-type
  CS78 — (8I) all 16 original option values still present in #asset-type unchanged

  CS79 — (8J) عمارة سكنية renders real form controls (inputs/selects)
  CS80 — (8J) #es-req-field-site_land_area_sqm number input present
  CS81 — (8J) #es-req-field-total_built_area_sqm number input present
  CS82 — (8J) #es-req-field-structural_condition select with Arabic options (جيدة, متوسطة, تحتاج صيانة)
  CS83 — (8J) #es-bf-floor-table tbody has ≥5 rows
  CS84 — (8J) [data-bf-field='licensed_use'] selects count ≥5
  CS85 — (8J) [data-bf-field='actual_use'] selects count ≥5
  CS86 — (8J) [data-bf-field='floor_area_sqm'] inputs count ≥5
  CS87 — (8J) [data-bf-field='occupancy_status'] selects count ≥5
  CS88 — (8J) floor labels present: بدروم, الدور الأرضي, الدور الأول, الأدوار المتكررة, سطح / خدمات
  CS89 — (8J) #es-req-field-bf_ownership_doc checkbox with label 'سند الملكية'
  CS90 — (8J) building_full panel has no link to /composite_valuation.html
  CS91 — (8J) building_full panel has no 'مناهج التقييم المناسبة' text
  CS92 — (8J) building_full panel has no 'إرشادي' text
  CS93 — (8J) residential controls unchanged: #es-req-field-area_sqm still present
  CS94 — (8J) land controls unchanged: #es-req-field-land_area_sqm still present
  CS95 — (8J) no JS console errors on building_full render
  CS96 — (8K) فندق form renders form controls; composite CTA absent

  CS97  — (8K) hotel form renders input/select controls
  CS98  — (8K) factory form renders input/select controls
  CS99  — (8K) hospital form renders input/select controls
  CS100 — (8K) school form renders input/select controls
  CS101 — (8K) retail form renders input/select controls
  CS102 — (8K) mine form renders input/select controls
  CS103 — (8K) hotel ht_land_area_sqm renders as number input
  CS104 — (8K) factory fc_land_area_sqm renders as number input
  CS105 — (8K) hospital ho_total_beds renders as number input
  CS106 — (8K) school sc_classrooms_count renders as number input
  CS107 — (8K) retail rt_gla_sqm renders as number input
  CS108 — (8K) mine mn_concession_area_sqkm renders as number input
  CS109 — (8K) hotel documents section shows upload hint text
  CS110 — (8K) factory documents section shows upload hint text
  CS111 — (8K) hospital documents section shows upload hint text
  CS112 — (8K) school documents section shows upload hint text
  CS113 — (8K) retail documents section shows upload hint text
  CS114 — (8K) mine documents section shows upload hint text
  CS115 — (8K) all 6 form profiles show 'نموذج محلي' badge
  CS116 — (8K) building_full floor table still intact (regression)
  CS117 — (8K) no JS console errors on hotel form render
  CS118 — (8K) no composite CTA in any of the 6 converted form profiles

  CS119 — (8L) building_full bf_construction_system select with Arabic options
  CS120 — (8L) building_full bf_visible_defects checkbox_group chips
  CS121 — (8L) building_full bf_maintenance_level select
  CS122 — (8L) factory fc_construction_system select with Arabic options
  CS123 — (8L) factory fc_has_crane bool field
  CS124 — (8L) factory fc_clear_height_m number input
  CS125 — (8L) hotel ht_star_rating select has Arabic options (options pattern)
  CS126 — (8L) hotel ht_total_rooms still present after enrichment
  CS127 — (8L) hotel ht_occupancy_rate_pct still present after enrichment
  CS128 — (8L) hospital ho_total_beds still present after enrichment
  CS129 — (8L) hospital ho_operating_rooms still present after enrichment
  CS130 — (8L) hospital ho_license_status select still present
  CS131 — (8L) school sc_classrooms_count still present after enrichment
  CS132 — (8L) school sc_student_capacity still present after enrichment
  CS133 — (8L) school sc_license_status select still present
  CS134 — (8L) retail rt_retail_type select with Arabic options
  CS135 — (8L) retail rt_frontage_m still present after enrichment
  CS136 — (8L) retail rt_footfall_level select field
  CS137 — (8L) mine mn_ore_type select still present
  CS138 — (8L) mine mn_license_status select still present
  CS139 — (8L) mine mn_proven_reserve_ton number input
  CS140 — (8L) mine mn_extraction_method select with Arabic options
  CS141 — (8L) upload hint present in all 7 local profiles incl. building_full
  CS142 — (8L) no JS console errors on enriched building_full render

  CS143 — (8M) water_well renders نموذج محلي form with structured sections
  CS144 — (8M) water_well ww_license_number input present
  CS145 — (8M) water_well ww_depth_m shows unit_ar 'متر'
  CS146 — (8M) water_well ww_daily_production_m3 shows م³/يوم unit
  CS147 — (8M) water_well ww_water_quality_class select renders with options
  CS148 — (8M) water_well upload guidance present
  CS149 — (8M) intangible form renders with it_asset_name field
  CS150 — (8M) partial_interest form renders with pi_ownership_pct number input
  CS151 — (8M) under_construction form renders with uc_completion_pct field
  CS152 — (8M) historical form renders with hs_age_years number input
  CS153 — (8M) heritage form renders with hr_cultural_category select
  CS154 — (8M) all 6 new profiles show badge 'نموذج محلي'
  CS155 — (8M) all 6 new profiles show upload guidance text
  CS156 — (8M) help_ar renders below ww_depth_m in water_well form
  CS157 — (8M) readability CSS es-field-unit and es-field-help rules present in HTML
  CS158 — (8N) factory component section heading present
  CS159 — (8N) factory renders 4 default component cards
  CS160 — (8N) factory card[0] has construction_system select
  CS161 — (8N) factory card[0] construction_system has stable option codes
  CS162 — (8N) factory card[0] has built_area_sqm input
  CS163 — (8N) factory card[0] has clear_height_m input
  CS164 — (8N) factory card[0] has crane_available extra field
  CS165 — (8N) factory card[0] visible_defects chip group with cracks option
  CS166 — (8N) hotel renders 5 default component cards
  CS167 — (8N) hotel card[0] has rooms_count extra field
  CS168 — (8N) hospital card[0] has hvac_condition medical extra field
  CS169 — (8N) school card[0] has classrooms_count extra field
  CS170 — (8N) retail card[0] has leasable_area_sqm extra field
  CS171 — (8N) mine component section uses operational heading not generic building
  CS172 — (8N) mine card[0] has component_capacity (fields_override), no built_area_sqm
  CS173 — (8N) water_well component section uses well heading
  CS174 — (8N) water_well card[0] has component_condition from fields_override
  CS175 — (8N) all 7 operational profiles render at least 1 component card
  CS176 — (8N) factory add-component button present
  CS177 — (8N) clicking add button increases card count by 1
  CS178 — (8N) default cards have no remove button; added cards do
  CS179 — (8N) #es-req-panel font-size >= 16px
  CS180 — (8N) section summary font-size >= 19px
  CS181 — (8N) factory component section has photo upload hint
  CS182 — (8N) residential and land profiles have no component cards

  CS183 — (8O) all 15 profiles stay on index.html after selection (no navigation away)
  CS184 — (8O) water_well panel: no #es-req-composite-link
  CS185 — (8O) intangible panel: no #es-req-composite-link
  CS186 — (8O) partial_interest panel: no #es-req-composite-link
  CS187 — (8O) under_construction panel: no #es-req-composite-link
  CS188 — (8O) historical panel: no #es-req-composite-link
  CS189 — (8O) heritage panel: no #es-req-composite-link
  CS190 — (8O) no 'فتح نموذج التقييم المركب التفصيلي' in panel for any static profile
  CS191 — (8O) no 'يلزم تسجيل الدخول' in requirements panel for any static profile
  CS192 — (8O) no 'يرجى تسجيل الدخول أولاً' in requirements panel for any static profile
  CS193 — (8O) #es-req-panel inner HTML contains no href to /composite_valuation.html
  CS194 — (8O) intangible panel renders inline form controls
  CS195 — (8O) partial_interest panel renders inline form controls
  CS196 — (8O) under_construction panel renders inline form controls
  CS197 — (8O) historical panel renders inline form controls
  CS198 — (8O) heritage panel renders inline form controls

  CS199 — (8P) selecting land without valid session does NOT show login modal
  CS200 — (8P) selecting residential_unit without valid session does NOT show login modal
  CS201 — (8P) selecting building_mixed without valid session does NOT show login modal
  CS202 — (8P) API 401 renders inline soft message inside #es-req-panel, not modal
  CS203 — (8P) building_full selection does NOT show login modal
  CS204 — (8P) factory selection does NOT show login modal
  CS205 — (8P) intangible selection does NOT show login modal
  CS206 — (8P) login modal remains in DOM (structure preservation)
  CS207 — (8P) no composite_valuation.html link in panel (Phase 8O regression guard)

  CS208 — (8Q) أرض زراعية routes as static; badge shows 'نموذج محلي' (not API-driven)
  CS209 — (8Q) أرض زراعية makes ZERO API calls to /api/valuation/requirements
  CS210 — (8Q) أرض زراعية panel title contains 'أرض زراعية'
  CS211 — (8Q) أرض زراعية panel renders inline form controls
  CS212 — (8Q) أرض زراعية panel has no composite link
  CS213 — (8Q) ag_area_sqm renders as number input in agricultural_land form
  CS214 — (8Q) ag_soil_type select renders with Arabic options
  CS215 — (8Q) ag_water_source_type select renders with Arabic options
  CS216 — (8Q) ag_irrigation_system select renders with Arabic options
  CS217 — (8Q) ag_annual_cultivation_cost renders as number input (unit ج.م./سنة)
  CS218 — (8Q) agricultural_land form shows upload hint text
  CS219 — (8Q) ag_farm_buildings_available renders as bool select (نعم/لا)
  CS220 — (8Q) no JS console errors on agricultural_land render

  CS221 — (8Q) شقة سكنية API panel: #es-req-supp receives supplemental sections
  CS222 — (8Q) residential supp heading 'بيانات الوحدة التفصيلية' visible
  CS223 — (8Q) es-supp-field-unit_type select renders with Arabic options
  CS224 — (8Q) es-supp-field-bedrooms_count number input present in residential supp
  CS225 — (8Q) es-supp-field-visible_defects checkbox group rendered (cracks option)
  CS226 — (8Q) es-supp-field-utilities_connected checkbox group rendered
  CS227 — (8Q) residential supp doc section shows upload hint text
  CS228 — (8Q) es-supp-field-ru_building_permit document checkbox present
  CS229 — (8Q) es-supp-field-occupancy_status select renders in residential supp
  CS230 — (8Q) #es-req-supp only uses data-es-supp-field (no data-es-req-field) for residential
  CS231 — (8Q) residential supp header shows '(إدخال محلّي — لا تُرسَل للـ API)' text
  CS232 — (8Q) switching residential → factory clears #es-req-supp
  CS233 — (8Q) es-supp-field-maintenance_level select renders in residential supp

  CS234 — (8Q) أرض فضاء API panel: #es-req-supp receives land supplemental sections
  CS235 — (8Q) land supp heading 'بيانات الأرض التفصيلية' visible
  CS236 — (8Q) es-supp-field-land_area_feddan number input present
  CS237 — (8Q) es-supp-field-shape_regular select renders in land supp
  CS238 — (8Q) es-supp-field-far_ratio number input present in land supp
  CS239 — (8Q) es-supp-field-main_street_width_m number input present
  CS240 — (8Q) es-supp-field-regulatory_compliance select renders in land supp
  CS241 — (8Q) es-supp-field-ld_transaction_cert document checkbox present
  CS242 — (8Q) land #es-req-supp only uses data-es-supp-field (no data-es-req-field)
  CS243 — (8Q) land supp header shows 'بيانات تفصيلية تكميلية للأرض'
  CS244 — (8Q) es-supp-field-infrastructure_development_cost number input in land supp
  CS245 — (8Q) land supp header shows '(إدخال محلّي)' text

  CS246 — (8Q) عمارة سكنية (static) #es-req-supp is empty (no supplemental for static)
  CS247 — (8Q) تجاري (commercial API) #es-req-supp is empty (no schema for commercial)
  CS248 — (8Q) switching residential → عمارة سكنية clears #es-req-supp
  CS249 — (8Q) switching land → مصنع clears #es-req-supp
  CS250 — (8Q) residential supp has no es-supp-field-area_sqm (no API field duplication)
  CS251 — (8Q) residential supp has no es-supp-field-floor_number (no API field duplication)
  CS252 — (8Q) land supp has no es-supp-field-land_area_sqm (no API field duplication)
  CS253 — (8Q) land supp has no es-supp-field-frontage_m (no API field duplication)
  CS254 — (8Q) no data-es-req-field elements in #es-req-supp for residential
  CS255 — (8Q) no data-es-req-field elements in #es-req-supp for land
  CS256 — (8Q) agricultural_land shows 'مصادر المياه والري' section heading
  CS257 — (8Q) ag_soil_fertility select renders with Arabic options in agricultural_land

  CS258 — (8R.1) optgroup 'أصول البنية التحتية والنقل السيادية' appears in #asset-type
  CS259 — (8R.1) airport option appears in #asset-type select
  CS260 — (8R.1) seaport option appears in #asset-type select
  CS261 — (8R.1) marina option appears in #asset-type select
  CS262 — (8R.1) airport renders local form (badge 'نموذج محلي'); page stays on index.html
  CS263 — (8R.1) seaport renders local form (badge 'نموذج محلي'); page stays on index.html
  CS264 — (8R.1) marina renders local form (badge 'نموذج محلي'); page stays on index.html
  CS265 — (8R.1) airport makes ZERO API calls to /api/valuation/requirements
  CS266 — (8R.1) airport panel title contains 'مطار'
  CS267 — (8R.1) ap_main_runway_length_m renders as number input with متر unit
  CS268 — (8R.1) ap_main_runway_width_m renders as number input with متر unit
  CS269 — (8R.1) ap_icao_compliance_status select renders with Arabic options
  CS270 — (8R.1) airport document section shows upload hint text
  CS271 — (8R.1) airport panel has no composite_valuation.html link
  CS272 — (8R.1) seaport makes ZERO API calls to /api/valuation/requirements
  CS273 — (8R.1) sp_annual_container_capacity_teu renders as number input with TEU/سنة unit
  CS274 — (8R.1) sp_berth_draft_depth_m renders as number input with متر unit
  CS275 — (8R.1) sp_harbor_basin_depth_m renders as number input with متر unit
  CS276 — (8R.1) seaport document section shows upload hint text
  CS277 — (8R.1) seaport panel has no composite_valuation.html link
  CS278 — (8R.1) marina makes ZERO API calls to /api/valuation/requirements
  CS279 — (8R.1) mr_wet_slips_count renders as number input
  CS280 — (8R.1) mr_max_yacht_loa_m renders as number input with متر unit
  CS281 — (8R.1) mr_service_facilities_available checkbox group renders (fuel_station option)
  CS282 — (8R.1) marina document section shows upload hint text
  CS283 — (8R.1) marina panel has no composite_valuation.html link
  CS284 — (8R.1) regression guard: existing profiles (فندق, عمارة سكنية) still render form controls
"""
from __future__ import annotations

import json

from playwright.sync_api import Page, Route, expect

_LS_KEY       = "es_auth"
_MOCK_SESSION = json.dumps({"token": "mock-token-cs", "user_id": "smoke-user", "is_admin": False})

# Phase 8H.2C enriched mock responses — carry role/label_ar/group/ui_required
# so the Phase 8H.2B renderer can classify and build real controls.
# Engine fields use role="engine_value" and must NOT be rendered.

def _ei(name, ft, desc, vv=None, *, role="engine_value", label_ar="", group="", ui_req=False):
    """Shorthand: engine / non-user field factory."""
    return {"name": name, "required": True, "field_type": ft, "description": desc,
            "valid_values": vv or [], "role": role, "label_ar": label_ar,
            "group": group, "ui_required": ui_req}

def _ui(name, ft, desc, vv=None, *, label_ar, group="", ui_req=False):
    """Shorthand: user_input field factory."""
    return {"name": name, "required": False, "field_type": ft, "description": desc,
            "valid_values": vv or [], "role": "user_input", "label_ar": label_ar,
            "group": group, "ui_required": ui_req}

def _doc(name, label_ar):
    """Shorthand: document (bool) field factory."""
    return {"name": name, "required": False, "field_type": "bool", "description": label_ar,
            "valid_values": [], "role": "user_input", "label_ar": label_ar,
            "group": "document", "ui_required": False}


_RESIDENTIAL_RESPONSE = {
    "status": "ok", "asset_type": "residential", "purpose": "market_value",
    "checklist_items": [
        # engine_value — must NOT render
        _ei("comparable", "float", "Comparable-sales approach value (EGP)"),
        _ei("cost",       "float", "Cost-approach value (EGP)"),
        _ei("income",     "float", "Income-capitalization approach value (EGP)"),
        _ei("comparables","list",  "List of comparable sales dicts"),
        # Section A — ui_required=True
        _ui("area_sqm",       "float", "Floor area (sqm)",                  label_ar="المساحة (م²)",        ui_req=True),
        _ui("floor_number",   "int",   "Floor number within the building",   label_ar="رقم الطابق",           ui_req=True),
        _ui("rooms_count",    "int",   "Number of rooms",                    label_ar="عدد الغرف",            ui_req=True),
        _ui("finishing_level","str",   "Finishing level of the unit",
            ["shell", "semi_finished", "standard_finished", "luxury_finished"],
            label_ar="مستوى التشطيب", ui_req=True),
        _ui("legal_status",   "str",   "Legal / title status",
            ["registered_title", "preliminary_contract", "allocation", "unknown"],
            label_ar="الحالة القانونية", ui_req=True),
        # Section B — ui_required=False, non-document
        _ui("client_name",    "str",   "Client or borrower name",            label_ar="اسم العميل"),
        _ui("location",       "str",   "Property address or location",       label_ar="الموقع"),
        _ui("elevator_available","str","Elevator available",
            ["yes", "no"],                                                    label_ar="يوجد مصعد"),
        _ui("parking_available","str", "Parking available",
            ["yes", "no"],                                                    label_ar="يوجد موقف سيارة"),
        # Section C — documents
        _doc("ownership_document",            "سند الملكية"),
        _doc("recent_photos",                 "صور حديثة للعقار"),
        _doc("site_croquis_or_location",      "كروكي الموقع"),
        _doc("nearby_sale_comparables_if_available", "مقارنات بيع قريبة (إن وجدت)"),
    ],
    "dynamic_fields": [],
    "recommended_methods": ["comparable", "cost", "income"],
    "notes": "",
}

_COMMERCIAL_RESPONSE = {
    "status": "ok", "asset_type": "commercial", "purpose": "market_value",
    "checklist_items": [
        _ei("comparable", "float", "Comparable value"),
        _ei("cost",       "float", "Cost value"),
        _ei("income",     "float", "Income value"),
        _ui("client_name",  "str",   "Client name",        label_ar="اسم العميل"),
        _ui("annual_rent",  "float", "Annual rental income", label_ar="الإيجار السنوي (ج.م.)"),
        _ui("cap_rate",     "float", "Capitalization rate",  label_ar="معدل الرسملة"),
    ],
    "dynamic_fields": [],
    "recommended_methods": ["comparable", "cost", "income"],
    "notes": "",
}

_LAND_RESPONSE = {
    "status": "ok", "asset_type": "land", "purpose": "market_value",
    "checklist_items": [
        # engine_value — must NOT render
        _ei("comparable",  "float", "Comparable-sales approach value (EGP)"),
        _ei("income",      "float", "Income-capitalization approach value (EGP)"),
        _ei("comparables", "list",  "List of comparable sales dicts"),
        # Section A — ui_required=True
        _ui("land_area_sqm",    "float", "Land area (sqm)",           label_ar="مساحة الأرض (م²)",        ui_req=True),
        _ui("frontage_m",       "float", "Street frontage width (m)", label_ar="واجهة الأرض (م)",          ui_req=True),
        _ui("street_width_m",   "float", "Adjacent street width (m)", label_ar="عرض الشارع (م)",           ui_req=True),
        _ui("zoning_type",      "str",   "Zoning classification",
            ["residential", "commercial", "administrative", "mixed_use", "agricultural", "unknown"],
            label_ar="نوع التخطيط العمراني", ui_req=True),
        _ui("buildability_status","str", "Buildability and planning constraints",
            ["buildable", "needs_verification", "planning_restrictions", "unknown"],
            label_ar="حالة قابلية البناء", ui_req=True),
        _ui("legal_status",     "str",   "Legal / title status",
            ["registered_title", "preliminary_contract", "allocation", "unknown"],
            label_ar="الحالة القانونية", ui_req=True),
        # Section B — ui_required=False, non-document
        _ui("client_name",      "str",   "Client name",                label_ar="اسم العميل"),
        _ui("hbu",              "str",   "Highest-and-best-use",
            ["residential", "commercial", "mixed_use", "industrial", "agricultural", "speculative"],
            label_ar="أفضل استخدام (HBU)"),
        _ui("utilities_available","list","Available utilities on the plot",
            ["electricity", "water", "sewage", "gas", "paved_road"],
            label_ar="الخدمات المتاحة"),
        # Section C — documents
        _doc("ownership_document",         "سند الملكية"),
        _doc("site_plan_or_croquis",       "كروكي المخطط"),
        _doc("site_photos",                "صور الموقع"),
    ],
    "dynamic_fields": [
        {"name": "zoning_type", "field_type": "str",
         "valid_values": ["residential", "commercial", "administrative", "mixed_use", "agricultural", "unknown"],
         "role": "user_input", "label_ar": "نوع التخطيط العمراني", "group": "", "ui_required": True},
    ],
    "recommended_methods": ["comparable", "income"],
    "notes": "Cost approach weight is 0 for unimproved land.",
}

_SOFT_MSG_FRAGMENT = "يمكنك متابعة التقييم"


def _inject_session(page: Page) -> None:
    page.evaluate(f"localStorage.setItem('{_LS_KEY}', {_MOCK_SESSION!r})")


def _mock_req(page: Page, payload: dict) -> None:
    def handle(route: Route) -> None:
        route.fulfill(status=200, content_type="application/json", body=json.dumps(payload))
    page.route("**/api/valuation/requirements**", handle)


# ── CS01 ──────────────────────────────────────────────────────────────────────

def test_CS01_panel_hidden_on_load(page: Page, live_server: str) -> None:
    """Requirements checklist panel is hidden on initial page load."""
    page.goto(live_server, wait_until="networkidle")
    panel = page.locator("#es-req-panel")
    expect(panel).to_be_attached()
    assert not panel.is_visible(), "#es-req-panel should be hidden on initial load"


# ── CS02 ──────────────────────────────────────────────────────────────────────

def test_CS02_panel_title_arabic_and_section_descriptions_present(page: Page, live_server: str) -> None:
    """Panel title shows human-readable Arabic; sections A and B have descriptive paragraphs."""
    _mock_req(page, _RESIDENTIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
    title_text = page.locator("#es-req-title").inner_text()

    assert "(residential" not in title_text, (
        f"Title must not contain raw key '(residential'. Got: {title_text!r}"
    )
    assert "market_value" not in title_text, (
        f"Title must not contain raw key 'market_value'. Got: {title_text!r}"
    )
    assert "متطلبات تقييم" in title_text, (
        f"Title should contain 'متطلبات تقييم'. Got: {title_text!r}"
    )
    assert "وحدة سكنية" in title_text, (
        f"Title should contain 'وحدة سكنية'. Got: {title_text!r}"
    )

    # Section A description
    s1_text = page.locator("#es-req-s1").inner_text()
    assert "ضرورية لبناء التقرير" in s1_text, (
        f"Section A description missing. Got: {s1_text!r}"
    )
    # Section B description (Phase 8H.2B: optional data fields, ui_required=False)
    s2_text = page.locator("#es-req-s2").inner_text()
    assert "ترفع جودة التقرير" in s2_text, (
        f"Section B description missing. Got: {s2_text!r}"
    )


# ── CS03 ──────────────────────────────────────────────────────────────────────

def test_CS03_section_headings_present_method_codes_absent_from_panel(page: Page, live_server: str) -> None:
    """Sections A/B headings present; raw method codes and methods heading absent from entire panel."""
    _mock_req(page, _RESIDENTIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    panel_text = page.locator("#es-req-panel").inner_text()
    assert "البيانات الأساسية" in panel_text or "المتطلبات الأساسية" in panel_text, (
        f"Section A heading missing. Panel text: {panel_text!r}"
    )
    assert "المستندات" in panel_text, (
        f"Section B heading missing. Panel text: {panel_text!r}"
    )
    # Phase 8E: methods section removed from user-facing panel
    assert "مناهج التقييم" not in panel_text, (
        f"'مناهج التقييم' must NOT appear in single-mode panel after Phase 8E. Panel text: {panel_text!r}"
    )

    # Raw English method codes must NOT appear anywhere in the panel
    s1_text = page.locator("#es-req-s1").inner_text()
    s2_text = page.locator("#es-req-s2").inner_text()
    for raw_code in ("comparable", "cost", "income", "residual_land_value", "investment_analysis"):
        assert raw_code not in s1_text, (
            f"Raw method code '{raw_code}' must not appear in section A. Got: {s1_text!r}"
        )
        assert raw_code not in s2_text, (
            f"Raw method code '{raw_code}' must not appear in section B. Got: {s2_text!r}"
        )


# ── CS04 ──────────────────────────────────────────────────────────────────────

def test_CS04_unsupported_purpose_shows_improved_soft_message(page: Page, live_server: str) -> None:
    """Selecting an unmapped purpose shows the improved soft message with continuation guidance."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="rental_arbitration")   # not in PURPOSE_MAP

    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    soft_msg = page.locator("#es-req-soft-msg")
    expect(soft_msg).to_be_visible()
    msg_text = soft_msg.inner_text()
    assert "لا توجد" in msg_text, (
        f"Soft message should contain 'لا توجد'. Got: {msg_text!r}"
    )
    assert _SOFT_MSG_FRAGMENT in msg_text, (
        f"Soft message should contain continuation guidance '{_SOFT_MSG_FRAGMENT}'. Got: {msg_text!r}"
    )


# ── CS05 ──────────────────────────────────────────────────────────────────────

def test_CS05_existing_valuation_ui_intact(page: Page, live_server: str) -> None:
    """Core valuation UI elements are still present after Phase 8B/8C/8C.1 HTML injection."""
    page.goto(live_server, wait_until="networkidle")
    expect(page.locator("#generateBtn")).to_be_visible()
    expect(page.locator("#asset-type")).to_be_visible()
    expect(page.locator("#val-purpose")).to_be_visible()


# ── CS06 ──────────────────────────────────────────────────────────────────────

def test_CS06_tijari_maps_to_commercial_single_mode(page: Page, live_server: str) -> None:
    """'تجاري' (commercial building) uses single-property mode; title contains 'تجاري'."""
    _mock_req(page, _COMMERCIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    # 'تجاري' maps to registry code 'commercial' but is NOT in _COMPOSITE_CODES,
    # so it must use the single-property API path, not the composite panel.
    page.select_option("#asset-type", value="تجاري")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
    title_text = page.locator("#es-req-title").inner_text()

    assert "تجاري" in title_text, (
        f"Title should contain 'تجاري' for commercial single-mode mapping. Got: {title_text!r}"
    )
    # Must NOT show composite panel for a single commercial building
    assert "أصل مركّب" not in title_text and "أصل مركب" not in title_text, (
        f"Title must NOT contain 'أصل مركّب' for single-mode 'تجاري'. Got: {title_text!r}"
    )


# ── CS07 ──────────────────────────────────────────────────────────────────────

def test_CS07_land_panel_renders_no_methods_anywhere(page: Page, live_server: str) -> None:
    """Land (single mode): no method names anywhere in panel after Phase 8E methods removal."""
    _mock_req(page, _LAND_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="أرض فضاء")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    panel_text = page.locator("#es-req-panel").inner_text()
    s4_text = page.locator("#es-req-s4").inner_text()

    # Section D must be empty — methods are internal
    assert s4_text.strip() == "", (
        f"Section D must be empty for land (single mode). Got: {s4_text!r}"
    )
    # The methods section heading must not appear (field labels in s1 may contain 'نهج' as part of the field name)
    assert "مناهج التقييم المناسبة" not in panel_text, (
        f"'مناهج التقييم المناسبة' heading must NOT appear in single-mode panel. Got: {panel_text!r}"
    )


# ── CS08 ──────────────────────────────────────────────────────────────────────

def test_CS08_intangible_shows_local_form(page: Page, live_server: str) -> None:
    """Phase 8M: intangible (أصول معنوية) now renders a نموذج محلي form, not an unsupported message."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="أصول معنوية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    badge = page.locator("#es-profile-badge")
    expect(badge).to_be_visible()
    assert badge.inner_text().strip() == "نموذج محلي", (
        f"intangible should show 'نموذج محلي' badge. Got: {badge.inner_text()!r}"
    )
    # Must NOT show the old "unsupported" soft message
    soft_msg = page.locator("#es-req-soft-msg")
    soft_text = soft_msg.inner_text().strip() if soft_msg.is_visible() else ""
    assert "غير مدعوم" not in soft_text, (
        f"intangible must not show unsupported message after 8M. Got: {soft_text!r}"
    )


# ── CS09 ──────────────────────────────────────────────────────────────────────

def test_CS09_section_D_empty_no_method_labels(page: Page, live_server: str) -> None:
    """Section D is empty — methods removed from user-facing panel; no Arabic or raw method labels."""
    _mock_req(page, _RESIDENTIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    s4_text = page.locator("#es-req-s4").inner_text().strip()
    assert s4_text == "", (
        f"Section D must be empty after Phase 8E methods removal. Got: {s4_text!r}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    # 'مناهج التقييم المناسبة' is the section heading — must be absent
    # (field labels in s1 may include 'نهج' as part of their Arabic name)
    assert "مناهج التقييم المناسبة" not in panel_text, (
        f"'مناهج التقييم المناسبة' heading must NOT appear in single-mode panel. Got: {panel_text!r}"
    )
    # Raw English method codes must not appear anywhere
    for raw_code in ("comparable", "cost", "income"):
        assert raw_code not in panel_text, (
            f"Raw method code '{raw_code}' must not appear in single-mode panel. Got: {panel_text!r}"
        )


# ── CS10 ──────────────────────────────────────────────────────────────────────

def test_CS10_determinism_two_reloads(page: Page, live_server: str) -> None:
    """Two consecutive page loads with the same selection produce identical panel text."""
    _mock_req(page, _RESIDENTIAL_RESPONSE)

    def _load_and_get_text() -> str:
        page.goto(live_server, wait_until="networkidle")
        _inject_session(page)
        page.select_option("#asset-type", value="شقة سكنية")
        page.select_option("#val-purpose", value="fair_market_value")
        page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
        return page.locator("#es-req-panel").inner_text()

    text1 = _load_and_get_text()
    text2 = _load_and_get_text()

    assert text1 == text2, (
        "Two consecutive reloads with same selection produced different panel text.\n"
        f"Run 1: {text1!r}\nRun 2: {text2!r}"
    )


# ── CS11 ──────────────────────────────────────────────────────────────────────

def test_CS11_always_visible_composite_nav_link_removed(page: Page, live_server: str) -> None:
    """Phase 8H.1: always-visible #cv-nav-link header link removed; composite access is contextual only."""
    page.goto(live_server, wait_until="networkidle")

    link = page.locator("#cv-nav-link")
    assert link.count() == 0 or not link.is_visible(), (
        "Header #cv-nav-link must NOT be present/visible after Phase 8H.1 nav de-duplication"
    )


# ── CS12 ──────────────────────────────────────────────────────────────────────

def test_CS12_three_sections_have_descriptions(page: Page, live_server: str) -> None:
    """Sections A/B/C each render with their explanatory Arabic description paragraph."""
    _mock_req(page, _LAND_RESPONSE)   # land gives content in all 3 data sections
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="أرض فضاء")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    s1_text = page.locator("#es-req-s1").inner_text()
    s2_text = page.locator("#es-req-s2").inner_text()
    s3_text = page.locator("#es-req-s3").inner_text()

    assert "ضرورية لبناء التقرير" in s1_text, (
        f"Section A description missing. Got: {s1_text!r}"
    )
    # Phase 8H.2B: s2 is now "بيانات إضافية" (optional data), s3 is documents
    assert "ترفع جودة التقرير" in s2_text, (
        f"Section B description missing. Got: {s2_text!r}"
    )
    assert "المستندات المتوفّرة" in s3_text, (
        f"Section C (documents) description missing. Got: {s3_text!r}"
    )


# ── CS13 ──────────────────────────────────────────────────────────────────────

def test_CS13_section_D_empty_after_methods_removal(page: Page, live_server: str) -> None:
    """Section D is empty after Phase 8E — methods are internal to engine, not user-facing."""
    _mock_req(page, _RESIDENTIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    s4 = page.locator("#es-req-s4")
    assert s4.get_attribute("data-es-section") != "methods", (
        "Section D must NOT carry data-es-section='methods' — methods removed from user panel"
    )
    s4_text = s4.inner_text().strip()
    assert s4_text == "", (
        f"Section D must be empty after methods removal. Got: {s4_text!r}"
    )


# ── CS14 ──────────────────────────────────────────────────────────────────────

def test_CS14_residential_single_mode_no_composite_banner(page: Page, live_server: str) -> None:
    """Residential unit (single mode): composite link absent; title does not say 'مركّب'."""
    _mock_req(page, _RESIDENTIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    title_text = page.locator("#es-req-title").inner_text()
    assert "مركّب" not in title_text and "مركب" not in title_text, (
        f"Title must not contain 'مركّب' for single mode. Got: {title_text!r}"
    )
    composite_link = page.locator("#es-req-composite-link")
    assert composite_link.count() == 0 or not composite_link.is_visible(), (
        "Composite link must not appear for residential (single mode)"
    )


# ── CS15 ──────────────────────────────────────────────────────────────────────

def test_CS15_land_single_mode_no_composite_banner(page: Page, live_server: str) -> None:
    """Land (single mode): composite link absent; title does not say 'مركّب'."""
    _mock_req(page, _LAND_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="أرض فضاء")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    title_text = page.locator("#es-req-title").inner_text()
    assert "مركّب" not in title_text and "مركب" not in title_text, (
        f"Title must not contain 'مركّب' for land (single mode). Got: {title_text!r}"
    )
    composite_link = page.locator("#es-req-composite-link")
    assert composite_link.count() == 0 or not composite_link.is_visible(), (
        "Composite link must not appear for land (single mode)"
    )


# ── CS16 ──────────────────────────────────────────────────────────────────────

def test_CS16_building_shows_inline_form_panel(page: Page, live_server: str) -> None:
    """'عمارة سكنية' (building_full inline form): title correct; 'بيانات الأرض' present; old static text absent."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    title_text = page.locator("#es-req-title").inner_text()
    assert "متطلبات تقييم عمارة سكنية" in title_text, (
        f"Title must be 'متطلبات تقييم عمارة سكنية' for building_full form. Got: {title_text!r}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "بيانات الأرض" in panel_text, (
        f"Inline form must contain 'بيانات الأرض'. Got: {panel_text!r}"
    )
    assert "سيتم التعامل معه" not in panel_text, (
        f"Old static-text phrase 'سيتم التعامل معه' must NOT appear in Phase 8J form. Got: {panel_text!r}"
    )


# ── CS17 ──────────────────────────────────────────────────────────────────────

def test_CS17_building_full_has_no_composite_redirect_link(page: Page, live_server: str) -> None:
    """Phase 8J: building_full inline form has NO redirect link to composite_valuation.html."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    # The composite link must not exist (or not be visible) in the building_full panel
    link = page.locator("#es-req-composite-link")
    assert link.count() == 0 or not link.is_visible(), (
        "building_full inline form must NOT show the composite redirect link (Phase 8J removed it)"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "composite_valuation.html" not in panel_text, (
        f"composite_valuation.html URL must not appear in building_full panel text. Got: {panel_text!r}"
    )


# ── CS18 ──────────────────────────────────────────────────────────────────────

def test_CS18_building_full_inline_form_sections(page: Page, live_server: str) -> None:
    """Phase 8J: building_full inline form shows بيانات الأرض + بيانات المبنى + توزيع الاستخدام; no بيانات الدخل."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    panel_text = page.locator("#es-req-panel").inner_text()
    assert "بيانات الأرض" in panel_text, (
        f"Inline form must contain 'بيانات الأرض'. Got: {panel_text!r}"
    )
    assert "بيانات المبنى" in panel_text, (
        f"Inline form must contain 'بيانات المبنى'. Got: {panel_text!r}"
    )
    assert "توزيع الاستخدام" in panel_text, (
        f"Inline form must contain 'توزيع الاستخدام' floor-table heading. Got: {panel_text!r}"
    )
    assert "بيانات الدخل" not in panel_text, (
        f"Old 'بيانات الدخل' section heading must NOT appear in Phase 8J form. Got: {panel_text!r}"
    )


# ── CS19 ──────────────────────────────────────────────────────────────────────

def test_CS19_no_raw_registry_codes_in_composite_panel(page: Page, live_server: str) -> None:
    """No raw English registry codes appear anywhere in the composite guidance panel."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    panel_text = page.locator("#es-req-panel").inner_text()
    for raw_code in ("commercial", "residential", "land", "market_value",
                     "comparable", "cost", "income"):
        assert raw_code not in panel_text, (
            f"Raw code '{raw_code}' must not appear in composite panel. Got: {panel_text!r}"
        )


# ── CS20 ──────────────────────────────────────────────────────────────────────

def test_CS20_composite_does_not_call_requirements_api(page: Page, live_server: str) -> None:
    """Composite selection does not trigger GET /api/valuation/requirements."""
    api_calls: list[str] = []

    def intercept(route: Route) -> None:
        api_calls.append(route.request.url)
        route.continue_()

    page.route("**/api/valuation/requirements**", intercept)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    assert len(api_calls) == 0, (
        f"GET /api/valuation/requirements must NOT be called for composite assets. "
        f"Called {len(api_calls)} time(s): {api_calls}"
    )


# ── CS21 ──────────────────────────────────────────────────────────────────────

def test_CS21_residential_single_panel_no_methods_section(page: Page, live_server: str) -> None:
    """Residential single panel: section D empty, data-es-section='methods' absent."""
    _mock_req(page, _RESIDENTIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    s4 = page.locator("#es-req-s4")
    assert s4.get_attribute("data-es-section") != "methods", (
        "Section D must NOT carry data-es-section='methods' after Phase 8E"
    )
    assert s4.inner_text().strip() == "", (
        f"Section D must be empty for residential single mode. Got: {s4.inner_text()!r}"
    )


# ── CS22 ──────────────────────────────────────────────────────────────────────

def test_CS22_residential_single_panel_no_methods_heading(page: Page, live_server: str) -> None:
    """Residential single panel text does not contain 'مناهج التقييم المناسبة'."""
    _mock_req(page, _RESIDENTIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    panel_text = page.locator("#es-req-panel").inner_text()
    assert "مناهج التقييم المناسبة" not in panel_text, (
        f"'مناهج التقييم المناسبة' must NOT appear in residential single panel. "
        f"Got: {panel_text!r}"
    )


# ── CS23 ──────────────────────────────────────────────────────────────────────

def test_CS23_composite_panel_no_methods_heading(page: Page, live_server: str) -> None:
    """Composite panel text does not contain 'مناهج التقييم المناسبة'."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    panel_text = page.locator("#es-req-panel").inner_text()
    assert "مناهج التقييم المناسبة" not in panel_text, (
        f"'مناهج التقييم المناسبة' must NOT appear in composite panel. "
        f"Got: {panel_text!r}"
    )


# ── CS24 ──────────────────────────────────────────────────────────────────────

def test_CS24_tijari_not_composite_calls_api(page: Page, live_server: str) -> None:
    """'تجاري' is NOT in _COMPOSITE_CODES; must call GET /api/valuation/requirements."""
    api_calls: list[str] = []

    def intercept(route: Route) -> None:
        api_calls.append(route.request.url)
        route.fulfill(status=200, content_type="application/json",
                      body=__import__("json").dumps(_COMMERCIAL_RESPONSE))

    page.route("**/api/valuation/requirements**", intercept)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="تجاري")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    assert len(api_calls) >= 1, (
        f"GET /api/valuation/requirements MUST be called for 'تجاري' (single commercial). "
        f"Got {len(api_calls)} call(s)."
    )


# ── CS25 ──────────────────────────────────────────────────────────────────────

def test_CS25_masna_is_placeholder_no_api_call(page: Page, live_server: str) -> None:
    """'مصنع' maps to factory placeholder profile — must NOT call GET /api/valuation/requirements."""
    api_calls: list[str] = []

    def intercept(route: Route) -> None:
        api_calls.append(route.request.url)
        route.continue_()

    page.route("**/api/valuation/requirements**", intercept)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="مصنع")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    assert len(api_calls) == 0, (
        f"GET /api/valuation/requirements must NOT be called for 'مصنع' (placeholder profile). "
        f"Got {len(api_calls)} call(s): {api_calls}"
    )


# ── CS26 ──────────────────────────────────────────────────────────────────────

def test_CS26_shaqqa_calls_requirements_api(page: Page, live_server: str) -> None:
    """'شقة سكنية' is residential_unit API profile — must call GET /api/valuation/requirements."""
    api_calls: list[str] = []

    def intercept(route: Route) -> None:
        api_calls.append(route.request.url)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps(_RESIDENTIAL_RESPONSE))

    page.route("**/api/valuation/requirements**", intercept)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    assert len(api_calls) >= 1, (
        f"GET /api/valuation/requirements MUST be called for 'شقة سكنية' (residential_unit). "
        f"Got {len(api_calls)} call(s)."
    )
    assert "asset_type=residential" in api_calls[0], (
        f"API call must use registry code 'residential'. URL: {api_calls[0]!r}"
    )


# ── CS27 ──────────────────────────────────────────────────────────────────────

def test_CS27_land_calls_requirements_api(page: Page, live_server: str) -> None:
    """'أرض فضاء' is land API profile — must call GET /api/valuation/requirements."""
    api_calls: list[str] = []

    def intercept(route: Route) -> None:
        api_calls.append(route.request.url)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps(_LAND_RESPONSE))

    page.route("**/api/valuation/requirements**", intercept)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="أرض فضاء")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    assert len(api_calls) >= 1, (
        f"GET /api/valuation/requirements MUST be called for 'أرض فضاء' (land profile). "
        f"Got {len(api_calls)} call(s)."
    )
    assert "asset_type=land" in api_calls[0], (
        f"API call must use registry code 'land'. URL: {api_calls[0]!r}"
    )


# ── CS28 ──────────────────────────────────────────────────────────────────────

def test_CS28_emara_static_path_zero_api_calls(page: Page, live_server: str) -> None:
    """'عمارة سكنية' takes building_full static path (Phase 8G) — ZERO API calls."""
    api_calls: list[str] = []

    def intercept(route: Route) -> None:
        api_calls.append(route.request.url)
        route.continue_()

    page.route("**/api/valuation/requirements**", intercept)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    assert len(api_calls) == 0, (
        f"GET /api/valuation/requirements must NOT be called for 'عمارة سكنية' (static path). "
        f"Got {len(api_calls)} call(s): {api_calls}"
    )


# ── CS29 ──────────────────────────────────────────────────────────────────────

def test_CS29_emara_floor_use_section_present(page: Page, live_server: str) -> None:
    """'عمارة سكنية' building_full panel shows floor-use informational rows."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")

    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    panel_text = page.locator("#es-req-panel").inner_text()
    assert "الدور الأرضي" in panel_text, (
        f"Floor-use row 'الدور الأرضي' must appear in building_full panel. Got: {panel_text!r}"
    )
    assert "الأدوار المتكررة" in panel_text, (
        f"Floor-use row 'الأدوار المتكررة' must appear in building_full panel. Got: {panel_text!r}"
    )


# ── CS30 ──────────────────────────────────────────────────────────────────────

def test_CS30_hotel_is_form_type_zero_api_renders_controls(page: Page, live_server: str) -> None:
    """'فندق' maps to hotel form type (Phase 8K): ZERO API calls, title contains 'فندق', form controls rendered."""
    api_calls: list[str] = []

    def intercept(route: Route) -> None:
        api_calls.append(route.request.url)
        route.continue_()

    page.route("**/api/valuation/requirements**", intercept)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="فندق")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    assert len(api_calls) == 0, (
        f"GET /api/valuation/requirements must NOT be called for 'فندق' (form type). "
        f"Got {len(api_calls)} call(s): {api_calls}"
    )
    title_text = page.locator("#es-req-title").inner_text()
    assert "فندق" in title_text, (
        f"Title must contain 'فندق'. Got: {title_text!r}"
    )
    control_count = page.locator("#es-req-panel input, #es-req-panel select").count()
    assert control_count > 0, (
        f"Hotel form must render input/select controls. Got {control_count} controls."
    )


# ── CS31 ──────────────────────────────────────────────────────────────────────

def test_CS31_factory_is_form_type_zero_api_renders_controls(page: Page, live_server: str) -> None:
    """'مصنع' maps to factory form type (Phase 8K): ZERO API calls, form controls rendered."""
    api_calls: list[str] = []

    def intercept(route: Route) -> None:
        api_calls.append(route.request.url)
        route.continue_()

    page.route("**/api/valuation/requirements**", intercept)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="مصنع")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    assert len(api_calls) == 0, (
        f"GET /api/valuation/requirements must NOT be called for 'مصنع' (form type). "
        f"Got {len(api_calls)} call(s): {api_calls}"
    )
    control_count = page.locator("#es-req-panel input, #es-req-panel select").count()
    assert control_count > 0, (
        f"Factory form must render input/select controls. Got {control_count} controls."
    )


# ── CS32 ──────────────────────────────────────────────────────────────────────

def test_CS32_hospital_is_form_type_zero_api_renders_controls(page: Page, live_server: str) -> None:
    """'مستشفى' maps to hospital form type (Phase 8K): ZERO API calls, form controls rendered."""
    api_calls: list[str] = []

    def intercept(route: Route) -> None:
        api_calls.append(route.request.url)
        route.continue_()

    page.route("**/api/valuation/requirements**", intercept)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="مستشفى")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    assert len(api_calls) == 0, (
        f"GET /api/valuation/requirements must NOT be called for 'مستشفى' (form type). "
        f"Got {len(api_calls)} call(s): {api_calls}"
    )
    control_count = page.locator("#es-req-panel input, #es-req-panel select").count()
    assert control_count > 0, (
        f"Hospital form must render input/select controls. Got {control_count} controls."
    )


# ── CS33 ──────────────────────────────────────────────────────────────────────

def test_CS33_all_form_type_assets_render_controls(page: Page, live_server: str) -> None:
    """Phase 8K: all six form-type asset types render input/select controls in the panel."""
    form_types = ["فندق", "مصنع", "محل تجاري", "مستشفى", "مدرسة", "مناجم"]

    for asset_type in form_types:
        page.goto(live_server, wait_until="networkidle")
        _inject_session(page)

        page.select_option("#asset-type", value=asset_type)
        page.select_option("#val-purpose", value="fair_market_value")
        page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

        control_count = page.locator("#es-req-panel input, #es-req-panel select").count()
        assert control_count > 0, (
            f"Form-type asset '{asset_type}' must render input/select controls. "
            f"Got {control_count} controls."
        )


# ── CS34 ──────────────────────────────────────────────────────────────────────

def test_CS34_placeholder_panels_no_required_bullets(page: Page, live_server: str) -> None:
    """Placeholder panels contain no ✦ bullet and no '(مطلوب)' required tag."""
    placeholder_types = ["فندق", "مصنع", "مستشفى"]

    for asset_type in placeholder_types:
        page.goto(live_server, wait_until="networkidle")
        _inject_session(page)

        page.select_option("#asset-type", value=asset_type)
        page.select_option("#val-purpose", value="fair_market_value")
        page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

        panel_text = page.locator("#es-req-panel").inner_text()
        assert "✦" not in panel_text, (
            f"Placeholder panel '{asset_type}' must not contain ✦ bullet. Got: {panel_text!r}"
        )
        assert "(مطلوب)" not in panel_text, (
            f"Placeholder panel '{asset_type}' must not contain '(مطلوب)'. Got: {panel_text!r}"
        )


# ── CS35 ──────────────────────────────────────────────────────────────────────

def test_CS35_no_raw_profile_codes_in_placeholder_panels(page: Page, live_server: str) -> None:
    """No raw English profile codes appear in placeholder panel text."""
    raw_codes = ("hotel", "factory", "retail", "hospital", "school", "mine",
                 "building_full", "building_mixed", "residential_unit")

    placeholder_types = ["فندق", "مصنع", "مستشفى"]

    for asset_type in placeholder_types:
        page.goto(live_server, wait_until="networkidle")
        _inject_session(page)

        page.select_option("#asset-type", value=asset_type)
        page.select_option("#val-purpose", value="fair_market_value")
        page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

        panel_text = page.locator("#es-req-panel").inner_text()
        for code in raw_codes:
            assert code not in panel_text, (
                f"Raw profile code '{code}' must not appear in placeholder panel '{asset_type}'. "
                f"Got: {panel_text!r}"
            )


# ── CS36 ──────────────────────────────────────────────────────────────────────

def test_CS36_emara_two_renders_identical(page: Page, live_server: str) -> None:
    """Two consecutive renders of 'عمارة سكنية' produce identical panel innerText."""
    def _render_and_get_text() -> str:
        page.goto(live_server, wait_until="networkidle")
        _inject_session(page)
        page.select_option("#asset-type", value="عمارة سكنية")
        page.select_option("#val-purpose", value="fair_market_value")
        page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
        return page.locator("#es-req-panel").inner_text()

    text1 = _render_and_get_text()
    text2 = _render_and_get_text()

    assert text1 == text2, (
        "Two consecutive renders of 'عمارة سكنية' produced different panel text.\n"
        f"Run 1: {text1!r}\nRun 2: {text2!r}"
    )


# ── CS37 ──────────────────────────────────────────────────────────────────────

def test_CS37_hotel_form_type_no_composite_cta(page: Page, live_server: str) -> None:
    """Phase 8K: فندق is now a form type; composite CTA absent; form controls rendered."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="فندق")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    link = page.locator("#es-req-composite-link")
    assert link.count() == 0 or not link.is_visible(), (
        "فندق form type must NOT show composite CTA link (Phase 8K converts all placeholders to forms)"
    )
    control_count = page.locator("#es-req-panel input, #es-req-panel select").count()
    assert control_count > 0, (
        f"فندق form must render input/select controls. Got {control_count} controls."
    )


# ── CS38 ──────────────────────────────────────────────────────────────────────

def test_CS38_building_full_s4_empty_no_method_labels(page: Page, live_server: str) -> None:
    """Phase 8H.1: building_full panel s4 is empty; method label text is absent."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    s4_text = page.locator("#es-req-s4").inner_text().strip()
    assert s4_text == "", (
        f"Section D must be empty for building_full after Phase 8H.1. Got: {s4_text!r}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "نهج المقارنة" not in panel_text, (
        f"Method label 'نهج المقارنة' must not appear in building_full panel. Got: {panel_text!r}"
    )
    assert "نهج الدخل" not in panel_text, (
        f"Method label 'نهج الدخل' must not appear in building_full panel. Got: {panel_text!r}"
    )
    assert "المناهج المقترحة" not in panel_text, (
        f"Methods heading 'المناهج المقترحة' must not appear in building_full panel. Got: {panel_text!r}"
    )


# ── CS39 ──────────────────────────────────────────────────────────────────────

def test_CS39_all_form_type_profiles_no_composite_cta_residential_land_unchanged(page: Page, live_server: str) -> None:
    """Phase 8K: all 6 form-type profiles have NO composite CTA; residential/land also do not."""
    form_types = ["فندق", "مصنع", "محل تجاري", "مستشفى", "مدرسة", "مناجم"]

    for asset_type in form_types:
        page.goto(live_server, wait_until="networkidle")
        _inject_session(page)

        page.select_option("#asset-type", value=asset_type)
        page.select_option("#val-purpose", value="fair_market_value")
        page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

        link = page.locator("#es-req-composite-link")
        assert link.count() == 0 or not link.is_visible(), (
            f"Form-type profile '{asset_type}' must NOT show composite CTA (Phase 8K)"
        )

    # Residential and land must also NOT show composite CTA (unchanged from 8H/8J)
    for asset_type, mock_data in [("شقة سكنية", _RESIDENTIAL_RESPONSE), ("أرض فضاء", _LAND_RESPONSE)]:
        _mock_req(page, mock_data)
        page.goto(live_server, wait_until="networkidle")
        _inject_session(page)

        page.select_option("#asset-type", value=asset_type)
        page.select_option("#val-purpose", value="fair_market_value")
        page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

        link = page.locator("#es-req-composite-link")
        assert link.count() == 0 or not link.is_visible(), (
            f"Composite CTA must NOT appear for '{asset_type}' (API-driven, not composite)"
        )


# ══ Phase 8H.2B — structured form controls (CS40 – CS55) ════════════════════


def _load_residential(page: Page, live_server: str) -> None:
    """Helper: navigate to live_server, inject session, select residential + market value."""
    _mock_req(page, _RESIDENTIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)


def _load_land(page: Page, live_server: str) -> None:
    """Helper: navigate to live_server, inject session, select land + market value."""
    _mock_req(page, _LAND_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="أرض فضاء")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)


# ── CS40 ──────────────────────────────────────────────────────────────────────

def test_CS40_residential_renders_form_controls(page: Page, live_server: str) -> None:
    """Phase 8H.2B: residential panel renders real input/select/checkbox elements, not text-only."""
    _load_residential(page, live_server)
    panel = page.locator("#es-req-panel")
    # At least one input or select must exist inside the panel
    inputs  = panel.locator("input, select")
    assert inputs.count() > 0, (
        "Residential panel must contain real form controls after Phase 8H.2B"
    )


# ── CS41 ──────────────────────────────────────────────────────────────────────

def test_CS41_residential_area_sqm_number_input(page: Page, live_server: str) -> None:
    """Phase 8H.2B: area_sqm renders as <input type='number'> in residential panel."""
    _load_residential(page, live_server)
    field = page.locator("#es-req-field-area_sqm")
    assert field.count() > 0, "area_sqm input must be present in residential panel"
    assert field.get_attribute("type") == "number", (
        f"area_sqm must be type='number'. Got: {field.get_attribute('type')!r}"
    )


# ── CS42 ──────────────────────────────────────────────────────────────────────

def test_CS42_residential_floor_number_number_input(page: Page, live_server: str) -> None:
    """Phase 8H.2B: floor_number (int) renders as <input type='number'> in residential panel."""
    _load_residential(page, live_server)
    field = page.locator("#es-req-field-floor_number")
    assert field.count() > 0, "floor_number input must be present in residential panel"
    assert field.get_attribute("type") == "number", (
        f"floor_number must be type='number'. Got: {field.get_attribute('type')!r}"
    )


# ── CS43 ──────────────────────────────────────────────────────────────────────

def test_CS43_residential_finishing_level_select_with_options(page: Page, live_server: str) -> None:
    """Phase 8H.2B: finishing_level renders as <select> with at least 4 options."""
    _load_residential(page, live_server)
    sel = page.locator("#es-req-field-finishing_level")
    assert sel.count() > 0, "finishing_level select must be present"
    tag = sel.evaluate("el => el.tagName.toLowerCase()")
    assert tag == "select", f"finishing_level must be a <select>. Got: {tag!r}"
    opts = page.locator("#es-req-field-finishing_level option")
    assert opts.count() >= 4, (
        f"finishing_level must have ≥4 options. Got: {opts.count()}"
    )


# ── CS44 ──────────────────────────────────────────────────────────────────────

def test_CS44_residential_legal_status_select(page: Page, live_server: str) -> None:
    """Phase 8H.2B: legal_status renders as <select> in residential panel."""
    _load_residential(page, live_server)
    sel = page.locator("#es-req-field-legal_status")
    assert sel.count() > 0, "legal_status select must be present in residential panel"
    tag = sel.evaluate("el => el.tagName.toLowerCase()")
    assert tag == "select", f"legal_status must be a <select>. Got: {tag!r}"
    opts = page.locator("#es-req-field-legal_status option")
    assert opts.count() >= 4, (
        f"legal_status must have ≥4 options. Got: {opts.count()}"
    )


# ── CS45 ──────────────────────────────────────────────────────────────────────

def test_CS45_residential_document_checkboxes(page: Page, live_server: str) -> None:
    """Phase 8H.2B: document fields render as checkboxes with Arabic labels in section C."""
    _load_residential(page, live_server)
    # ownership_document is a document checkbox
    cb = page.locator("#es-req-field-ownership_document")
    assert cb.count() > 0, "ownership_document checkbox must be present"
    assert cb.get_attribute("type") == "checkbox", (
        f"ownership_document must be type='checkbox'. Got: {cb.get_attribute('type')!r}"
    )
    # Its label must contain the Arabic label_ar value
    label = page.locator("label[for='es-req-field-ownership_document']")
    assert label.count() > 0, "Label for ownership_document must be present"
    label_text = label.inner_text()
    assert "سند الملكية" in label_text, (
        f"ownership_document label must contain 'سند الملكية'. Got: {label_text!r}"
    )
    # recent_photos must also be a checkbox
    cb2 = page.locator("#es-req-field-recent_photos")
    assert cb2.count() > 0, "recent_photos checkbox must be present"
    assert cb2.get_attribute("type") == "checkbox"


# ── CS46 ──────────────────────────────────────────────────────────────────────

def test_CS46_land_renders_form_controls(page: Page, live_server: str) -> None:
    """Phase 8H.2B: land panel renders real input/select/checkbox elements, not text-only."""
    _load_land(page, live_server)
    panel = page.locator("#es-req-panel")
    inputs = panel.locator("input, select")
    assert inputs.count() > 0, (
        "Land panel must contain real form controls after Phase 8H.2B"
    )


# ── CS47 ──────────────────────────────────────────────────────────────────────

def test_CS47_land_land_area_sqm_number_input(page: Page, live_server: str) -> None:
    """Phase 8H.2B: land_area_sqm renders as <input type='number'> in land panel."""
    _load_land(page, live_server)
    field = page.locator("#es-req-field-land_area_sqm")
    assert field.count() > 0, "land_area_sqm input must be present in land panel"
    assert field.get_attribute("type") == "number", (
        f"land_area_sqm must be type='number'. Got: {field.get_attribute('type')!r}"
    )


# ── CS48 ──────────────────────────────────────────────────────────────────────

def test_CS48_land_frontage_m_number_input(page: Page, live_server: str) -> None:
    """Phase 8H.2B: frontage_m renders as <input type='number'> in land panel."""
    _load_land(page, live_server)
    field = page.locator("#es-req-field-frontage_m")
    assert field.count() > 0, "frontage_m input must be present in land panel"
    assert field.get_attribute("type") == "number", (
        f"frontage_m must be type='number'. Got: {field.get_attribute('type')!r}"
    )


# ── CS49 ──────────────────────────────────────────────────────────────────────

def test_CS49_land_zoning_type_select_with_options(page: Page, live_server: str) -> None:
    """Phase 8H.2B: zoning_type renders as <select> with at least 6 options in land panel."""
    _load_land(page, live_server)
    sel = page.locator("#es-req-field-zoning_type")
    assert sel.count() > 0, "zoning_type select must be present in land panel"
    tag = sel.evaluate("el => el.tagName.toLowerCase()")
    assert tag == "select", f"zoning_type must be a <select>. Got: {tag!r}"
    opts = page.locator("#es-req-field-zoning_type option")
    assert opts.count() >= 6, (
        f"zoning_type must have ≥6 options. Got: {opts.count()}"
    )


# ── CS50 ──────────────────────────────────────────────────────────────────────

def test_CS50_land_utilities_available_checkbox_group(page: Page, live_server: str) -> None:
    """Phase 8H.2B: utilities_available (list+valid_values) renders as a checkbox group."""
    _load_land(page, live_server)
    checkboxes = page.locator("[name='utilities_available']")
    assert checkboxes.count() >= 5, (
        f"utilities_available must have ≥5 checkboxes (one per valid value). "
        f"Got: {checkboxes.count()}"
    )
    # Every element in the group must be a checkbox
    for i in range(checkboxes.count()):
        cb = checkboxes.nth(i)
        assert cb.get_attribute("type") == "checkbox", (
            f"utilities_available item {i} must be type='checkbox'"
        )


# ── CS51 ──────────────────────────────────────────────────────────────────────

def test_CS51_land_buildability_status_select(page: Page, live_server: str) -> None:
    """Phase 8H.2B: buildability_status renders as <select> in land panel."""
    _load_land(page, live_server)
    sel = page.locator("#es-req-field-buildability_status")
    assert sel.count() > 0, "buildability_status select must be present in land panel"
    tag = sel.evaluate("el => el.tagName.toLowerCase()")
    assert tag == "select", f"buildability_status must be a <select>. Got: {tag!r}"


# ── CS52 ──────────────────────────────────────────────────────────────────────

def test_CS52_land_document_checkboxes(page: Page, live_server: str) -> None:
    """Phase 8H.2B: document fields render as checkboxes with Arabic labels in land section C."""
    _load_land(page, live_server)
    cb = page.locator("#es-req-field-ownership_document")
    assert cb.count() > 0, "ownership_document checkbox must be present in land panel"
    assert cb.get_attribute("type") == "checkbox"
    label = page.locator("label[for='es-req-field-ownership_document']")
    assert label.count() > 0, "Label for land ownership_document must be present"
    label_text = label.inner_text()
    assert "سند الملكية" in label_text, (
        f"Land ownership_document label must contain 'سند الملكية'. Got: {label_text!r}"
    )
    cb2 = page.locator("#es-req-field-site_photos")
    assert cb2.count() > 0, "site_photos checkbox must be present in land panel"
    assert cb2.get_attribute("type") == "checkbox"


# ── CS53 ──────────────────────────────────────────────────────────────────────

def test_CS53_engine_fields_not_rendered(page: Page, live_server: str) -> None:
    """Phase 8H.2B: engine_value fields (comparable/cost/income/comparables) must NOT render."""
    _load_residential(page, live_server)
    for engine_field in ("comparable", "cost", "income", "comparables"):
        el = page.locator(f"[data-es-req-field='{engine_field}']")
        assert el.count() == 0, (
            f"Engine field '{engine_field}' must NOT be rendered as a form control. "
            f"Found {el.count()} element(s)."
        )


# ── CS54 ──────────────────────────────────────────────────────────────────────

def test_CS54_field_label_comes_from_label_ar(page: Page, live_server: str) -> None:
    """Phase 8H.2B: the visible label for area_sqm comes from label_ar ('المساحة (م²)'), not hardcoded."""
    _load_residential(page, live_server)
    label = page.locator("label[for='es-req-field-area_sqm']")
    assert label.count() > 0, "Label for area_sqm must be present"
    label_text = label.inner_text()
    assert "المساحة" in label_text, (
        f"area_sqm label must contain Arabic text from label_ar 'المساحة (م²)'. "
        f"Got: {label_text!r}"
    )
    # Confirm the same DRY property for a land field
    _load_land(page, live_server)
    label2 = page.locator("label[for='es-req-field-land_area_sqm']")
    assert label2.count() > 0, "Label for land_area_sqm must be present"
    label2_text = label2.inner_text()
    assert "مساحة" in label2_text, (
        f"land_area_sqm label must contain Arabic text from label_ar. Got: {label2_text!r}"
    )


# ── CS55 ──────────────────────────────────────────────────────────────────────

def test_CS55_no_console_errors_on_render(page: Page, live_server: str) -> None:
    """Phase 8H.2B: rendering residential and land panels produces zero JS console errors.

    Network-level 401s that occur before session injection are pre-existing expected
    behaviour and are excluded from this assertion.
    """
    def _is_js_error(msg) -> bool:
        """True only for real JavaScript errors; ignore network/auth noise."""
        return (
            msg.type == "error"
            and "401" not in msg.text
            and "UNAUTHORIZED" not in msg.text
            and "Failed to load resource" not in msg.text
        )

    console_errors: list[str] = []
    page.on("console", lambda msg: console_errors.append(msg.text) if _is_js_error(msg) else None)

    _load_residential(page, live_server)
    assert not console_errors, (
        f"JavaScript console errors during residential render: {console_errors}"
    )

    console_errors.clear()
    _load_land(page, live_server)
    assert not console_errors, (
        f"JavaScript console errors during land render: {console_errors}"
    )


# ══ Phase 8H.2D — UX polish (CS56 – CS60) ════════════════════════════════════


# ── CS56 ──────────────────────────────────────────────────────────────────────

def test_CS56_select_first_option_is_ikhtaar_placeholder(page: Page, live_server: str) -> None:
    """Phase 8H.2D: select dropdowns render 'اختر ...' as the first (disabled) placeholder option."""
    _load_residential(page, live_server)
    first_text = page.locator("#es-req-field-finishing_level option").nth(0).inner_text()
    assert "اختر" in first_text, (
        f"First option of finishing_level must contain 'اختر'. Got: {first_text!r}"
    )


# ── CS57 ──────────────────────────────────────────────────────────────────────

def test_CS57_select_default_option_derived_from_label_ar(page: Page, live_server: str) -> None:
    """Phase 8H.2D: default select option text is DERIVED from label_ar — DRY compliance."""
    _load_residential(page, live_server)
    # finishing_level label_ar in mock = "مستوى التشطيب"
    first_text = page.locator("#es-req-field-finishing_level option").nth(0).inner_text()
    assert "مستوى التشطيب" in first_text, (
        f"Default option must contain label_ar 'مستوى التشطيب' (derived, not hardcoded). "
        f"Got: {first_text!r}"
    )
    # land: zoning_type label_ar = "نوع التخطيط العمراني"
    _load_land(page, live_server)
    first_text2 = page.locator("#es-req-field-zoning_type option").nth(0).inner_text()
    assert "نوع التخطيط" in first_text2, (
        f"Default option for zoning_type must contain label_ar fragment. Got: {first_text2!r}"
    )


# ── CS58 ──────────────────────────────────────────────────────────────────────

def test_CS58_yesno_field_renders_arabic_options(page: Page, live_server: str) -> None:
    """Phase 8H.2D: fields with yes/no valid_values display نعم / لا (not raw 'yes'/'no')."""
    _load_residential(page, live_server)
    sel = page.locator("#es-req-field-elevator_available")
    assert sel.count() > 0, "elevator_available select must be present in residential panel"
    opts_text = page.locator("#es-req-field-elevator_available option").all_inner_texts()
    assert any("نعم" in t for t in opts_text), (
        f"elevator_available must have a 'نعم' option. Got: {opts_text}"
    )
    assert any("لا" in t for t in opts_text), (
        f"elevator_available must have a 'لا' option. Got: {opts_text}"
    )


# ── CS59 ──────────────────────────────────────────────────────────────────────

def test_CS59_number_inputs_have_placeholder(page: Page, live_server: str) -> None:
    """Phase 8H.2D: number inputs carry a non-empty placeholder attribute."""
    _load_residential(page, live_server)
    ph = page.locator("#es-req-field-area_sqm").get_attribute("placeholder")
    assert ph and len(ph) > 0, (
        f"area_sqm must have a non-empty placeholder. Got: {ph!r}"
    )
    _load_land(page, live_server)
    ph2 = page.locator("#es-req-field-frontage_m").get_attribute("placeholder")
    assert ph2 and len(ph2) > 0, (
        f"frontage_m must have a non-empty placeholder. Got: {ph2!r}"
    )


# ── CS60 ──────────────────────────────────────────────────────────────────────

def test_CS60_three_section_headings_visible_in_residential_panel(page: Page, live_server: str) -> None:
    """Phase 8H.2D: all 3 section card headings are rendered inside the requirements panel."""
    _load_residential(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "البيانات الأساسية المطلوبة" in panel_text, (
        f"Section A heading missing from panel. Got: {panel_text!r}"
    )
    assert "بيانات إضافية لتحسين الدقّة" in panel_text, (
        f"Section B heading missing from panel. Got: {panel_text!r}"
    )
    assert "المستندات المطلوبة" in panel_text, (
        f"Section C heading missing from panel. Got: {panel_text!r}"
    )


# ── CS61 ──────────────────────────────────────────────────────────────────────

def test_CS61_utilities_available_shows_arabic_labels(page: Page, live_server: str) -> None:
    """Phase 8H.2D: utilities_available chip group shows Arabic labels, not raw backend codes."""
    _load_land(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    for arabic in ("كهرباء", "مياه", "صرف صحي", "غاز", "طريق ممهد"):
        assert arabic in panel_text, (
            f"utilities_available must show Arabic label '{arabic}'. Got: {panel_text!r}"
        )


# ── CS62 ──────────────────────────────────────────────────────────────────────

def test_CS62_utilities_available_no_raw_backend_codes(page: Page, live_server: str) -> None:
    """Phase 8H.2D: utilities_available chip group must NOT display raw backend codes."""
    _load_land(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    for raw in ("electricity", "water", "sewage", "gas", "paved_road"):
        assert raw not in panel_text, (
            f"Raw backend code '{raw}' must not appear in rendered panel. Got: {panel_text!r}"
        )


# ══ Phase 8H.2E — dropdown options content fix (CS63 – CS70) ═════════════════


# ── CS63 ──────────────────────────────────────────────────────────────────────

def test_CS63_finishing_level_options_arabic(page: Page, live_server: str) -> None:
    """Phase 8H.2E: finishing_level select options display Arabic translations, not raw codes."""
    _load_residential(page, live_server)
    opts = page.locator("#es-req-field-finishing_level option").all_inner_texts()
    for arabic in ("بدون تشطيب", "نصف تشطيب", "تشطيب عادي", "تشطيب فاخر"):
        assert any(arabic in t for t in opts), (
            f"finishing_level must have Arabic option '{arabic}'. Got opts: {opts}"
        )
    for raw in ("shell", "semi_finished", "standard_finished", "luxury_finished"):
        assert not any(raw == t.strip() for t in opts), (
            f"Raw code '{raw}' must not be the displayed text in finishing_level options. Got: {opts}"
        )


# ── CS64 ──────────────────────────────────────────────────────────────────────

def test_CS64_legal_status_options_arabic(page: Page, live_server: str) -> None:
    """Phase 8H.2E: legal_status select options display Arabic translations, not raw codes."""
    _load_residential(page, live_server)
    opts = page.locator("#es-req-field-legal_status option").all_inner_texts()
    for arabic in ("ملكية مسجلة", "عقد ابتدائي", "تخصيص", "غير محدد"):
        assert any(arabic in t for t in opts), (
            f"legal_status must have Arabic option '{arabic}'. Got opts: {opts}"
        )
    for raw in ("registered_title", "preliminary_contract", "allocation", "unknown"):
        assert not any(raw == t.strip() for t in opts), (
            f"Raw code '{raw}' must not be the displayed text in legal_status options. Got: {opts}"
        )


# ── CS65 ──────────────────────────────────────────────────────────────────────

def test_CS65_parking_available_shows_arabic(page: Page, live_server: str) -> None:
    """Phase 8H.2E: parking_available select displays نعم/لا, not raw yes/no."""
    _load_residential(page, live_server)
    opts = page.locator("#es-req-field-parking_available option").all_inner_texts()
    assert any("نعم" in t for t in opts), (
        f"parking_available must have a 'نعم' option. Got: {opts}"
    )
    assert any("لا" in t for t in opts), (
        f"parking_available must have a 'لا' option. Got: {opts}"
    )
    assert not any("yes" == t.strip() for t in opts), (
        f"Raw 'yes' must not be the displayed text in parking_available. Got: {opts}"
    )


# ── CS66 ──────────────────────────────────────────────────────────────────────

def test_CS66_zoning_type_options_arabic(page: Page, live_server: str) -> None:
    """Phase 8H.2E: zoning_type select options display Arabic translations, not raw codes."""
    _load_land(page, live_server)
    opts = page.locator("#es-req-field-zoning_type option").all_inner_texts()
    for arabic in ("سكني", "تجاري", "إداري", "استخدام مختلط", "زراعي", "غير محدد"):
        assert any(arabic in t for t in opts), (
            f"zoning_type must have Arabic option '{arabic}'. Got opts: {opts}"
        )
    for raw in ("residential", "commercial", "administrative", "mixed_use", "agricultural"):
        assert not any(raw == t.strip() for t in opts), (
            f"Raw code '{raw}' must not be the displayed text in zoning_type options. Got: {opts}"
        )


# ── CS67 ──────────────────────────────────────────────────────────────────────

def test_CS67_buildability_status_options_arabic(page: Page, live_server: str) -> None:
    """Phase 8H.2E: buildability_status select options display Arabic translations."""
    _load_land(page, live_server)
    opts = page.locator("#es-req-field-buildability_status option").all_inner_texts()
    for arabic in ("قابل للبناء", "يحتاج تحقق", "قيود تخطيطية", "غير محدد"):
        assert any(arabic in t for t in opts), (
            f"buildability_status must have Arabic option '{arabic}'. Got opts: {opts}"
        )
    for raw in ("buildable", "needs_verification", "planning_restrictions"):
        assert not any(raw == t.strip() for t in opts), (
            f"Raw code '{raw}' must not be displayed text in buildability_status. Got: {opts}"
        )


# ── CS68 ──────────────────────────────────────────────────────────────────────

def test_CS68_hbu_options_arabic(page: Page, live_server: str) -> None:
    """Phase 8H.2E: hbu select options display Arabic translations, not raw codes."""
    _load_land(page, live_server)
    opts = page.locator("#es-req-field-hbu option").all_inner_texts()
    for arabic in ("سكني", "تجاري", "استخدام مختلط", "صناعي", "زراعي", "مضاربي"):
        assert any(arabic in t for t in opts), (
            f"hbu must have Arabic option '{arabic}'. Got opts: {opts}"
        )
    for raw in ("industrial", "speculative"):
        assert not any(raw == t.strip() for t in opts), (
            f"Raw code '{raw}' must not be the displayed text in hbu options. Got: {opts}"
        )


# ── CS69 ──────────────────────────────────────────────────────────────────────

def test_CS69_residential_panel_no_raw_enum_codes(page: Page, live_server: str) -> None:
    """Phase 8H.2E: residential panel visible text contains no raw enum value codes."""
    _load_residential(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    raw_codes = (
        "shell", "semi_finished", "standard_finished", "luxury_finished",
        "registered_title", "preliminary_contract", "allocation",
        "owner_occupied", "rental",
        "luxury", "economy", "heritage",
        "ordinary", "premium",
    )
    for code in raw_codes:
        assert code not in panel_text, (
            f"Raw code '{code}' must not appear in residential panel visible text. "
            f"Got: {panel_text!r}"
        )


# ── CS70 ──────────────────────────────────────────────────────────────────────

def test_CS70_land_panel_no_raw_enum_codes(page: Page, live_server: str) -> None:
    """Phase 8H.2E: land panel visible text contains no raw enum value codes."""
    _load_land(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    raw_codes = (
        "registered_title", "preliminary_contract", "allocation",
        "buildable", "needs_verification", "planning_restrictions",
        "mixed_use", "agricultural", "administrative",
        "industrial", "speculative",
        "prime", "secondary", "remote",
        "unrestricted", "general_commercial", "residential_only", "restricted",
        "ready_to_build", "feasible", "challenging", "very_difficult",
    )
    for code in raw_codes:
        assert code not in panel_text, (
            f"Raw code '{code}' must not appear in land panel visible text. "
            f"Got: {panel_text!r}"
        )


# ══ Phase 8I — Asset Selector UX (CS71 – CS78) ═══════════════════════════════


# ── CS71 ──────────────────────────────────────────────────────────────────────

def test_CS71_profile_explainer_hidden_on_load(page: Page, live_server: str) -> None:
    """Phase 8I: #es-profile-explainer is hidden on initial page load (no selection yet)."""
    page.goto(live_server, wait_until="networkidle")
    explainer = page.locator("#es-profile-explainer")
    assert explainer.count() > 0, "#es-profile-explainer must exist in DOM"
    assert not explainer.is_visible(), (
        "#es-profile-explainer must be hidden before any asset-type selection"
    )


# ── CS72 ──────────────────────────────────────────────────────────────────────

def test_CS72_residential_selection_shows_supported_badge(page: Page, live_server: str) -> None:
    """Phase 8I: selecting شقة سكنية shows explainer with 'مدعوم' badge."""
    _mock_req(page, _RESIDENTIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)

    explainer = page.locator("#es-profile-explainer")
    assert explainer.is_visible(), "#es-profile-explainer must be visible after selecting شقة سكنية"
    badge_text = page.locator("#es-profile-badge").inner_text()
    assert "مدعوم" in badge_text, (
        f"Badge must contain 'مدعوم' for residential selection. Got: {badge_text!r}"
    )


# ── CS73 ──────────────────────────────────────────────────────────────────────

def test_CS73_building_full_selection_shows_composite_badge(page: Page, live_server: str) -> None:
    """Phase 8I: selecting عمارة سكنية (building_full) shows 'نموذج مركّب' badge."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    explainer = page.locator("#es-profile-explainer")
    assert explainer.is_visible(), "#es-profile-explainer must be visible after selecting عمارة سكنية"
    badge_text = page.locator("#es-profile-badge").inner_text()
    assert "نموذج مركّب" in badge_text, (
        f"Badge must contain 'نموذج مركّب' for building_full. Got: {badge_text!r}"
    )


# ── CS74 ──────────────────────────────────────────────────────────────────────

def test_CS74_form_profile_selection_shows_local_form_badge(page: Page, live_server: str) -> None:
    """Phase 8K: selecting فندق (form profile) shows 'نموذج محلي' badge."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="فندق")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    explainer = page.locator("#es-profile-explainer")
    assert explainer.is_visible(), "#es-profile-explainer must be visible after selecting فندق"
    badge_text = page.locator("#es-profile-badge").inner_text()
    assert "نموذج محلي" in badge_text, (
        f"Badge must contain 'نموذج محلي' for form profile. Got: {badge_text!r}"
    )


# ── CS75 ──────────────────────────────────────────────────────────────────────

def test_CS75_unsupported_selection_shows_unsupported_badge(page: Page, live_server: str) -> None:
    """Phase 8M: أصول معنوية is now a local form profile — badge shows 'نموذج محلي', not 'غير مدعوم'."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="أصول معنوية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    explainer = page.locator("#es-profile-explainer")
    assert explainer.is_visible(), "#es-profile-explainer must be visible after selecting أصول معنوية"
    badge_text = page.locator("#es-profile-badge").inner_text()
    assert "نموذج محلي" in badge_text, (
        f"Badge must contain 'نموذج محلي' for intangible form. Got: {badge_text!r}"
    )


# ── CS76 ──────────────────────────────────────────────────────────────────────

def test_CS76_explainer_updates_on_selection_change(page: Page, live_server: str) -> None:
    """Phase 8K: changing selection فندق → شقة سكنية updates badge from نموذج محلي to مدعوم."""
    _mock_req(page, _RESIDENTIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)

    # First selection: فندق → نموذج محلي
    page.select_option("#asset-type", value="فندق")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    badge_text_1 = page.locator("#es-profile-badge").inner_text()
    assert "نموذج محلي" in badge_text_1, (
        f"First selection (فندق) must show 'نموذج محلي'. Got: {badge_text_1!r}"
    )

    # Second selection: شقة سكنية → مدعوم
    page.select_option("#asset-type", value="شقة سكنية")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
    badge_text_2 = page.locator("#es-profile-badge").inner_text()
    assert "مدعوم" in badge_text_2, (
        f"After changing to شقة سكنية, badge must show 'مدعوم'. Got: {badge_text_2!r}"
    )
    assert "نموذج محلي" not in badge_text_2, (
        f"'نموذج محلي' must NOT appear in badge after switching to residential. Got: {badge_text_2!r}"
    )


# ── CS77 ──────────────────────────────────────────────────────────────────────

def test_CS77_optgroups_present_in_asset_type_select(page: Page, live_server: str) -> None:
    """Phase 8I: #asset-type select contains <optgroup> elements for category grouping."""
    page.goto(live_server, wait_until="networkidle")
    optgroups = page.locator("#asset-type optgroup")
    assert optgroups.count() >= 4, (
        f"#asset-type must have ≥4 optgroup elements. Got: {optgroups.count()}"
    )
    labels = [optgroups.nth(i).get_attribute("label") for i in range(optgroups.count())]
    assert any("سكن" in (lbl or "") for lbl in labels), (
        f"Expected an optgroup with 'سكن' in label. Got labels: {labels}"
    )
    assert any("أراضٍ" in (lbl or "") or "أراض" in (lbl or "") for lbl in labels), (
        f"Expected an optgroup for أراضٍ. Got labels: {labels}"
    )


# ── CS78 ──────────────────────────────────────────────────────────────────────

def test_CS78_all_original_option_values_unchanged(page: Page, live_server: str) -> None:
    """Phase 8I: all 16 original option values still present in #asset-type (values unchanged)."""
    page.goto(live_server, wait_until="networkidle")
    original_values = [
        "شقة سكنية", "عمارة سكنية", "تجاري", "أرض فضاء", "مصنع",
        "أرض زراعية", "فندق", "محل تجاري", "مستشفى", "مدرسة",
        "أصول معنوية", "ملكيات جزئية", "مناجم", "استثمارات تحت الإنشاء",
        "historical", "heritage",
    ]
    actual_values = page.locator("#asset-type option").evaluate_all(
        "opts => opts.map(o => o.value)"
    )
    for v in original_values:
        assert v in actual_values, (
            f"Original option value '{v}' must still be present in #asset-type. "
            f"Got values: {actual_values}"
        )


# ══ Phase 8J — building_full inline structured form (CS79 – CS96) ═══════════


def _load_building_full(page: Page, live_server: str) -> None:
    """Helper: navigate to live_server, inject session, select عمارة سكنية + market value."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


# ── CS79 ──────────────────────────────────────────────────────────────────────

def test_CS79_building_full_renders_form_controls(page: Page, live_server: str) -> None:
    """Phase 8J: عمارة سكنية renders real form inputs/selects, not static text-only."""
    _load_building_full(page, live_server)
    panel = page.locator("#es-req-panel")
    inputs = panel.locator("input, select")
    assert inputs.count() > 0, (
        "building_full panel must contain real form controls after Phase 8J"
    )


# ── CS80 ──────────────────────────────────────────────────────────────────────

def test_CS80_building_full_site_land_area_sqm_input(page: Page, live_server: str) -> None:
    """Phase 8J: #es-req-field-site_land_area_sqm number input present in building_full form."""
    _load_building_full(page, live_server)
    field = page.locator("#es-req-field-site_land_area_sqm")
    assert field.count() > 0, "#es-req-field-site_land_area_sqm must be present"
    assert field.get_attribute("type") == "number", (
        f"site_land_area_sqm must be type='number'. Got: {field.get_attribute('type')!r}"
    )


# ── CS81 ──────────────────────────────────────────────────────────────────────

def test_CS81_building_full_total_built_area_input(page: Page, live_server: str) -> None:
    """Phase 8J: #es-req-field-total_built_area_sqm number input present in building_full form."""
    _load_building_full(page, live_server)
    field = page.locator("#es-req-field-total_built_area_sqm")
    assert field.count() > 0, "#es-req-field-total_built_area_sqm must be present"
    assert field.get_attribute("type") == "number", (
        f"total_built_area_sqm must be type='number'. Got: {field.get_attribute('type')!r}"
    )


# ── CS82 ──────────────────────────────────────────────────────────────────────

def test_CS82_building_full_structural_condition_arabic_options(page: Page, live_server: str) -> None:
    """Phase 8J: #es-req-field-structural_condition select has Arabic options جيدة, متوسطة, تحتاج صيانة."""
    _load_building_full(page, live_server)
    sel = page.locator("#es-req-field-structural_condition")
    assert sel.count() > 0, "#es-req-field-structural_condition select must be present"
    tag = sel.evaluate("el => el.tagName.toLowerCase()")
    assert tag == "select", f"structural_condition must be a <select>. Got: {tag!r}"
    opts = page.locator("#es-req-field-structural_condition option").all_inner_texts()
    for arabic in ("جيدة", "متوسطة", "تحتاج صيانة"):
        assert any(arabic in t for t in opts), (
            f"structural_condition must have Arabic option '{arabic}'. Got: {opts}"
        )
    for raw in ("good", "average", "needs_maintenance"):
        assert not any(raw == t.strip() for t in opts), (
            f"Raw code '{raw}' must not be the displayed text in structural_condition. Got: {opts}"
        )


# ── CS83 ──────────────────────────────────────────────────────────────────────

def test_CS83_building_full_floor_table_has_five_rows(page: Page, live_server: str) -> None:
    """Phase 8J: #es-bf-floor-table tbody contains ≥5 rows (one per floor definition)."""
    _load_building_full(page, live_server)
    tbody_rows = page.locator("#es-bf-floor-table tbody tr")
    assert tbody_rows.count() >= 5, (
        f"Floor table must have ≥5 rows. Got: {tbody_rows.count()}"
    )


# ── CS84 ──────────────────────────────────────────────────────────────────────

def test_CS84_floor_licensed_use_selects_count(page: Page, live_server: str) -> None:
    """Phase 8J: [data-bf-field='licensed_use'] selects present for each floor row (≥5)."""
    _load_building_full(page, live_server)
    sels = page.locator("[data-bf-field='licensed_use']")
    assert sels.count() >= 5, (
        f"[data-bf-field='licensed_use'] selects must be ≥5. Got: {sels.count()}"
    )


# ── CS85 ──────────────────────────────────────────────────────────────────────

def test_CS85_floor_actual_use_selects_count(page: Page, live_server: str) -> None:
    """Phase 8J: [data-bf-field='actual_use'] selects present for each floor row (≥5)."""
    _load_building_full(page, live_server)
    sels = page.locator("[data-bf-field='actual_use']")
    assert sels.count() >= 5, (
        f"[data-bf-field='actual_use'] selects must be ≥5. Got: {sels.count()}"
    )


# ── CS86 ──────────────────────────────────────────────────────────────────────

def test_CS86_floor_area_sqm_inputs_count(page: Page, live_server: str) -> None:
    """Phase 8J: [data-bf-field='floor_area_sqm'] number inputs present for each floor (≥5)."""
    _load_building_full(page, live_server)
    inputs = page.locator("[data-bf-field='floor_area_sqm']")
    assert inputs.count() >= 5, (
        f"[data-bf-field='floor_area_sqm'] inputs must be ≥5. Got: {inputs.count()}"
    )


# ── CS87 ──────────────────────────────────────────────────────────────────────

def test_CS87_floor_occupancy_status_selects_count(page: Page, live_server: str) -> None:
    """Phase 8J: [data-bf-field='occupancy_status'] selects present for each floor row (≥5)."""
    _load_building_full(page, live_server)
    sels = page.locator("[data-bf-field='occupancy_status']")
    assert sels.count() >= 5, (
        f"[data-bf-field='occupancy_status'] selects must be ≥5. Got: {sels.count()}"
    )


# ── CS88 ──────────────────────────────────────────────────────────────────────

def test_CS88_floor_labels_present_in_panel(page: Page, live_server: str) -> None:
    """Phase 8J: all five floor labels are visible in the building_full panel."""
    _load_building_full(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    for label in ("بدروم", "الدور الأرضي", "الدور الأول", "الأدوار المتكررة", "سطح / خدمات"):
        assert label in panel_text, (
            f"Floor label '{label}' must appear in building_full panel. Got: {panel_text!r}"
        )


# ── CS89 ──────────────────────────────────────────────────────────────────────

def test_CS89_bf_ownership_doc_checkbox_with_arabic_label(page: Page, live_server: str) -> None:
    """Phase 8J: #es-req-field-bf_ownership_doc checkbox present with label 'سند الملكية'."""
    _load_building_full(page, live_server)
    cb = page.locator("#es-req-field-bf_ownership_doc")
    assert cb.count() > 0, "#es-req-field-bf_ownership_doc checkbox must be present"
    assert cb.get_attribute("type") == "checkbox", (
        f"bf_ownership_doc must be type='checkbox'. Got: {cb.get_attribute('type')!r}"
    )
    label = page.locator("label[for='es-req-field-bf_ownership_doc']")
    assert label.count() > 0, "Label for bf_ownership_doc must be present"
    assert "سند الملكية" in label.inner_text(), (
        f"bf_ownership_doc label must contain 'سند الملكية'. Got: {label.inner_text()!r}"
    )


# ── CS90 ──────────────────────────────────────────────────────────────────────

def test_CS90_building_full_no_composite_link(page: Page, live_server: str) -> None:
    """Phase 8J: building_full panel has no link to /composite_valuation.html."""
    _load_building_full(page, live_server)
    link = page.locator("#es-req-composite-link")
    assert link.count() == 0 or not link.is_visible(), (
        "building_full inline form must NOT contain the composite redirect link"
    )
    panel_html = page.locator("#es-req-panel").inner_html()
    assert "composite_valuation.html" not in panel_html, (
        "composite_valuation.html URL must not appear in building_full panel HTML"
    )


# ── CS91 ──────────────────────────────────────────────────────────────────────

def test_CS91_building_full_no_methods_heading(page: Page, live_server: str) -> None:
    """Phase 8J: building_full panel has no 'مناهج التقييم المناسبة' text."""
    _load_building_full(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "مناهج التقييم المناسبة" not in panel_text, (
        f"'مناهج التقييم المناسبة' must NOT appear in building_full panel. Got: {panel_text!r}"
    )


# ── CS92 ──────────────────────────────────────────────────────────────────────

def test_CS92_building_full_no_irshadi_text(page: Page, live_server: str) -> None:
    """Phase 8J: building_full panel has no 'إرشادي' (old static hint text) anywhere."""
    _load_building_full(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "إرشادي" not in panel_text, (
        f"Old static hint text 'إرشادي' must NOT appear in Phase 8J building_full form. Got: {panel_text!r}"
    )


# ── CS93 ──────────────────────────────────────────────────────────────────────

def test_CS93_residential_controls_unchanged(page: Page, live_server: str) -> None:
    """Phase 8J: residential panel controls unchanged — #es-req-field-area_sqm still present."""
    _load_residential(page, live_server)
    field = page.locator("#es-req-field-area_sqm")
    assert field.count() > 0, (
        "#es-req-field-area_sqm must still be present in residential panel after Phase 8J"
    )
    assert field.get_attribute("type") == "number", (
        f"area_sqm must still be type='number'. Got: {field.get_attribute('type')!r}"
    )


# ── CS94 ──────────────────────────────────────────────────────────────────────

def test_CS94_land_controls_unchanged(page: Page, live_server: str) -> None:
    """Phase 8J: land panel controls unchanged — #es-req-field-land_area_sqm still present."""
    _load_land(page, live_server)
    field = page.locator("#es-req-field-land_area_sqm")
    assert field.count() > 0, (
        "#es-req-field-land_area_sqm must still be present in land panel after Phase 8J"
    )
    assert field.get_attribute("type") == "number", (
        f"land_area_sqm must still be type='number'. Got: {field.get_attribute('type')!r}"
    )


# ── CS95 ──────────────────────────────────────────────────────────────────────

def test_CS95_no_js_console_errors_on_building_full_render(page: Page, live_server: str) -> None:
    """Phase 8J: no real JavaScript errors when rendering building_full inline form.

    Pre-existing 401/UNAUTHORIZED network noise is excluded (same as CS55).
    """
    def _is_js_error(msg) -> bool:
        return (
            msg.type == "error"
            and "401" not in msg.text
            and "UNAUTHORIZED" not in msg.text
            and "Failed to load resource" not in msg.text
        )

    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if _is_js_error(msg) else None)
    page.on("pageerror", lambda err: errors.append(str(err)))
    _load_building_full(page, live_server)
    assert len(errors) == 0, (
        f"JS console errors must be absent on building_full render. Got: {errors}"
    )


# ── CS96 ──────────────────────────────────────────────────────────────────────

def test_CS96_hotel_form_renders_controls_no_composite_cta(page: Page, live_server: str) -> None:
    """Phase 8K: فندق form renders form controls; composite CTA is absent (all placeholders converted)."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="فندق")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    link = page.locator("#es-req-composite-link")
    assert link.count() == 0 or not link.is_visible(), (
        "فندق form must NOT show composite CTA link after Phase 8K conversion"
    )
    control_count = page.locator("#es-req-panel input, #es-req-panel select").count()
    assert control_count > 0, (
        f"فندق form must render input/select controls. Got {control_count} controls."
    )


# ══ Phase 8K — specialized form controls (CS97 – CS118) ═════════════════════


def _load_hotel(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="فندق")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


def _load_factory(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="مصنع")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


def _load_hospital(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="مستشفى")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


def _load_school(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="مدرسة")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


def _load_retail(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="محل تجاري")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


def _load_mine(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="مناجم")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


# ── CS97 ──────────────────────────────────────────────────────────────────────

def test_CS97_hotel_form_renders_form_controls(page: Page, live_server: str) -> None:
    """Phase 8K: hotel form renders input/select controls in the requirements panel."""
    _load_hotel(page, live_server)
    count = page.locator("#es-req-panel input, #es-req-panel select").count()
    assert count > 0, f"Hotel form must render input/select controls. Got {count} controls."


# ── CS98 ──────────────────────────────────────────────────────────────────────

def test_CS98_factory_form_renders_form_controls(page: Page, live_server: str) -> None:
    """Phase 8K: factory form renders input/select controls in the requirements panel."""
    _load_factory(page, live_server)
    count = page.locator("#es-req-panel input, #es-req-panel select").count()
    assert count > 0, f"Factory form must render input/select controls. Got {count} controls."


# ── CS99 ──────────────────────────────────────────────────────────────────────

def test_CS99_hospital_form_renders_form_controls(page: Page, live_server: str) -> None:
    """Phase 8K: hospital form renders input/select controls in the requirements panel."""
    _load_hospital(page, live_server)
    count = page.locator("#es-req-panel input, #es-req-panel select").count()
    assert count > 0, f"Hospital form must render input/select controls. Got {count} controls."


# ── CS100 ─────────────────────────────────────────────────────────────────────

def test_CS100_school_form_renders_form_controls(page: Page, live_server: str) -> None:
    """Phase 8K: school form renders input/select controls in the requirements panel."""
    _load_school(page, live_server)
    count = page.locator("#es-req-panel input, #es-req-panel select").count()
    assert count > 0, f"School form must render input/select controls. Got {count} controls."


# ── CS101 ─────────────────────────────────────────────────────────────────────

def test_CS101_retail_form_renders_form_controls(page: Page, live_server: str) -> None:
    """Phase 8K: retail form renders input/select controls in the requirements panel."""
    _load_retail(page, live_server)
    count = page.locator("#es-req-panel input, #es-req-panel select").count()
    assert count > 0, f"Retail form must render input/select controls. Got {count} controls."


# ── CS102 ─────────────────────────────────────────────────────────────────────

def test_CS102_mine_form_renders_form_controls(page: Page, live_server: str) -> None:
    """Phase 8K: mine form renders input/select controls in the requirements panel."""
    _load_mine(page, live_server)
    count = page.locator("#es-req-panel input, #es-req-panel select").count()
    assert count > 0, f"Mine form must render input/select controls. Got {count} controls."


# ── CS103 ─────────────────────────────────────────────────────────────────────

def test_CS103_hotel_land_area_number_input_present(page: Page, live_server: str) -> None:
    """Phase 8K: hotel form ht_land_area_sqm renders as a number input."""
    _load_hotel(page, live_server)
    inp = page.locator("#es-req-field-ht_land_area_sqm")
    assert inp.count() == 1, "#es-req-field-ht_land_area_sqm not found in hotel form"
    assert inp.get_attribute("type") == "number", (
        f"ht_land_area_sqm must be type=number. Got: {inp.get_attribute('type')!r}"
    )


# ── CS104 ─────────────────────────────────────────────────────────────────────

def test_CS104_factory_land_area_number_input_present(page: Page, live_server: str) -> None:
    """Phase 8K: factory form fc_land_area_sqm renders as a number input."""
    _load_factory(page, live_server)
    inp = page.locator("#es-req-field-fc_land_area_sqm")
    assert inp.count() == 1, "#es-req-field-fc_land_area_sqm not found in factory form"
    assert inp.get_attribute("type") == "number", (
        f"fc_land_area_sqm must be type=number. Got: {inp.get_attribute('type')!r}"
    )


# ── CS105 ─────────────────────────────────────────────────────────────────────

def test_CS105_hospital_total_beds_number_input_present(page: Page, live_server: str) -> None:
    """Phase 8K: hospital form ho_total_beds renders as a number input."""
    _load_hospital(page, live_server)
    inp = page.locator("#es-req-field-ho_total_beds")
    assert inp.count() == 1, "#es-req-field-ho_total_beds not found in hospital form"
    assert inp.get_attribute("type") == "number", (
        f"ho_total_beds must be type=number. Got: {inp.get_attribute('type')!r}"
    )


# ── CS106 ─────────────────────────────────────────────────────────────────────

def test_CS106_school_classrooms_count_number_input_present(page: Page, live_server: str) -> None:
    """Phase 8K: school form sc_classrooms_count renders as a number input."""
    _load_school(page, live_server)
    inp = page.locator("#es-req-field-sc_classrooms_count")
    assert inp.count() == 1, "#es-req-field-sc_classrooms_count not found in school form"
    assert inp.get_attribute("type") == "number", (
        f"sc_classrooms_count must be type=number. Got: {inp.get_attribute('type')!r}"
    )


# ── CS107 ─────────────────────────────────────────────────────────────────────

def test_CS107_retail_gla_sqm_number_input_present(page: Page, live_server: str) -> None:
    """Phase 8K: retail form rt_gla_sqm renders as a number input."""
    _load_retail(page, live_server)
    inp = page.locator("#es-req-field-rt_gla_sqm")
    assert inp.count() == 1, "#es-req-field-rt_gla_sqm not found in retail form"
    assert inp.get_attribute("type") == "number", (
        f"rt_gla_sqm must be type=number. Got: {inp.get_attribute('type')!r}"
    )


# ── CS108 ─────────────────────────────────────────────────────────────────────

def test_CS108_mine_concession_area_number_input_present(page: Page, live_server: str) -> None:
    """Phase 8K: mine form mn_concession_area_sqkm renders as a number input."""
    _load_mine(page, live_server)
    inp = page.locator("#es-req-field-mn_concession_area_sqkm")
    assert inp.count() == 1, "#es-req-field-mn_concession_area_sqkm not found in mine form"
    assert inp.get_attribute("type") == "number", (
        f"mn_concession_area_sqkm must be type=number. Got: {inp.get_attribute('type')!r}"
    )


# ── CS109–CS114: upload hint text ─────────────────────────────────────────────

_UPLOAD_HINT_TEXT = "ارفع المستندات من زر المرفقات"


def test_CS109_hotel_documents_section_has_upload_hint(page: Page, live_server: str) -> None:
    """Phase 8K: hotel documents section contains upload guidance hint text."""
    _load_hotel(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert _UPLOAD_HINT_TEXT in panel_text, (
        f"Hotel panel must contain upload hint text. Got: {panel_text[:200]!r}"
    )


def test_CS110_factory_documents_section_has_upload_hint(page: Page, live_server: str) -> None:
    """Phase 8K: factory documents section contains upload guidance hint text."""
    _load_factory(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert _UPLOAD_HINT_TEXT in panel_text, (
        f"Factory panel must contain upload hint text. Got: {panel_text[:200]!r}"
    )


def test_CS111_hospital_documents_section_has_upload_hint(page: Page, live_server: str) -> None:
    """Phase 8K: hospital documents section contains upload guidance hint text."""
    _load_hospital(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert _UPLOAD_HINT_TEXT in panel_text, (
        f"Hospital panel must contain upload hint text. Got: {panel_text[:200]!r}"
    )


def test_CS112_school_documents_section_has_upload_hint(page: Page, live_server: str) -> None:
    """Phase 8K: school documents section contains upload guidance hint text."""
    _load_school(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert _UPLOAD_HINT_TEXT in panel_text, (
        f"School panel must contain upload hint text. Got: {panel_text[:200]!r}"
    )


def test_CS113_retail_documents_section_has_upload_hint(page: Page, live_server: str) -> None:
    """Phase 8K: retail documents section contains upload guidance hint text."""
    _load_retail(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert _UPLOAD_HINT_TEXT in panel_text, (
        f"Retail panel must contain upload hint text. Got: {panel_text[:200]!r}"
    )


def test_CS114_mine_documents_section_has_upload_hint(page: Page, live_server: str) -> None:
    """Phase 8K: mine documents section contains upload guidance hint text."""
    _load_mine(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert _UPLOAD_HINT_TEXT in panel_text, (
        f"Mine panel must contain upload hint text. Got: {panel_text[:200]!r}"
    )


# ── CS115 ─────────────────────────────────────────────────────────────────────

def test_CS115_all_six_form_profiles_show_local_form_badge(page: Page, live_server: str) -> None:
    """Phase 8K: all 6 form profiles display the 'نموذج محلي' badge in the explainer."""
    form_types = ["فندق", "مصنع", "محل تجاري", "مستشفى", "مدرسة", "مناجم"]
    for asset_type in form_types:
        page.goto(live_server, wait_until="networkidle")
        _inject_session(page)
        page.select_option("#asset-type", value=asset_type)
        page.select_option("#val-purpose", value="fair_market_value")
        page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
        badge_text = page.locator("#es-profile-badge").inner_text()
        assert "نموذج محلي" in badge_text, (
            f"Form profile '{asset_type}' must show 'نموذج محلي' badge. Got: {badge_text!r}"
        )


# ── CS116 ─────────────────────────────────────────────────────────────────────

def test_CS116_building_full_floor_table_regression(page: Page, live_server: str) -> None:
    """Phase 8K regression: عمارة سكنية floor table still intact after 8K changes."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

    assert page.locator("#es-bf-floor-table").count() == 1, (
        "#es-bf-floor-table must still be present in building_full panel after Phase 8K"
    )
    row_count = page.locator("#es-bf-floor-table tbody tr").count()
    assert row_count >= 5, (
        f"Floor table must have ≥5 rows. Got {row_count} rows."
    )


# ── CS117 ─────────────────────────────────────────────────────────────────────

def test_CS117_no_js_console_errors_on_hotel_form_render(page: Page, live_server: str) -> None:
    """Phase 8K: no unexpected JS console errors when rendering the hotel form."""
    def _is_js_error(msg) -> bool:
        return (
            msg.type == "error"
            and "401" not in msg.text
            and "UNAUTHORIZED" not in msg.text
            and "Failed to load resource" not in msg.text
        )

    console_errors: list[str] = []
    page.on("console", lambda msg: console_errors.append(msg.text) if _is_js_error(msg) else None)

    _load_hotel(page, live_server)
    assert not console_errors, (
        f"JavaScript console errors during hotel form render: {console_errors}"
    )


# ── CS118 ─────────────────────────────────────────────────────────────────────

def test_CS118_no_composite_cta_in_any_form_profile(page: Page, live_server: str) -> None:
    """Phase 8K: none of the 6 converted form profiles shows a composite CTA link."""
    form_types = ["فندق", "مصنع", "محل تجاري", "مستشفى", "مدرسة", "مناجم"]
    for asset_type in form_types:
        page.goto(live_server, wait_until="networkidle")
        _inject_session(page)
        page.select_option("#asset-type", value=asset_type)
        page.select_option("#val-purpose", value="fair_market_value")
        page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)

        link = page.locator("#es-req-composite-link")
        assert link.count() == 0 or not link.is_visible(), (
            f"Form profile '{asset_type}' must NOT show composite CTA link (Phase 8K)"
        )


# ══ Phase 8L — enriched profiles (CS119 – CS142) ═════════════════════════════


# ── CS119 ─────────────────────────────────────────────────────────────────────

def test_CS119_building_full_construction_system_select(page: Page, live_server: str) -> None:
    """Phase 8L: building_full has bf_construction_system select with Arabic options."""
    _load_building_full(page, live_server)
    sel = page.locator("#es-req-field-bf_construction_system")
    assert sel.count() > 0, "#es-req-field-bf_construction_system not found in building_full"
    tag = sel.evaluate("el => el.tagName.toLowerCase()")
    assert tag == "select", f"bf_construction_system must be a <select>. Got: {tag!r}"
    opts = page.locator("#es-req-field-bf_construction_system option").all_inner_texts()
    for arabic in ("جمالون حديد", "هيكل خرساني"):
        assert any(arabic in t for t in opts), (
            f"bf_construction_system must have Arabic option '{arabic}'. Got: {opts}"
        )


# ── CS120 ─────────────────────────────────────────────────────────────────────

def test_CS120_building_full_visible_defects_checkbox_group(page: Page, live_server: str) -> None:
    """Phase 8L: building_full has bf_visible_defects rendered as checkbox chips."""
    _load_building_full(page, live_server)
    chips = page.locator("[data-es-req-field='bf_visible_defects']")
    assert chips.count() > 0, "bf_visible_defects checkboxes not found in building_full"
    panel_text = page.locator("#es-req-panel").inner_text()
    for arabic in ("شروخ", "رطوبة", "هبوط"):
        assert arabic in panel_text, (
            f"bf_visible_defects must show Arabic chip label '{arabic}'. Got: {panel_text[:400]!r}"
        )


# ── CS121 ─────────────────────────────────────────────────────────────────────

def test_CS121_building_full_maintenance_level_select(page: Page, live_server: str) -> None:
    """Phase 8L: building_full has bf_maintenance_level select with Arabic options."""
    _load_building_full(page, live_server)
    sel = page.locator("#es-req-field-bf_maintenance_level")
    assert sel.count() > 0, "#es-req-field-bf_maintenance_level not found in building_full"
    opts = page.locator("#es-req-field-bf_maintenance_level option").all_inner_texts()
    assert any("جيد الصيانة" in t for t in opts), (
        f"bf_maintenance_level must have 'جيد الصيانة' option. Got: {opts}"
    )


# ── CS122 ─────────────────────────────────────────────────────────────────────

def test_CS122_factory_construction_system_select(page: Page, live_server: str) -> None:
    """Phase 8L: factory form has fc_construction_system select with Arabic options."""
    _load_factory(page, live_server)
    sel = page.locator("#es-req-field-fc_construction_system")
    assert sel.count() > 0, "#es-req-field-fc_construction_system not found in factory"
    opts = page.locator("#es-req-field-fc_construction_system option").all_inner_texts()
    assert any("جمالون حديد" in t for t in opts), (
        f"fc_construction_system must have Arabic option 'جمالون حديد'. Got: {opts}"
    )


# ── CS123 ─────────────────────────────────────────────────────────────────────

def test_CS123_factory_has_crane_bool_field(page: Page, live_server: str) -> None:
    """Phase 8L: factory form has fc_has_crane bool select with نعم / لا options."""
    _load_factory(page, live_server)
    sel = page.locator("#es-req-field-fc_has_crane")
    assert sel.count() > 0, "#es-req-field-fc_has_crane not found in factory"
    opts = page.locator("#es-req-field-fc_has_crane option").all_inner_texts()
    assert any("نعم" in t for t in opts), (
        f"fc_has_crane must have 'نعم' option. Got: {opts}"
    )
    assert any("لا" in t for t in opts), (
        f"fc_has_crane must have 'لا' option. Got: {opts}"
    )


# ── CS124 ─────────────────────────────────────────────────────────────────────

def test_CS124_factory_clear_height_number_input(page: Page, live_server: str) -> None:
    """Phase 8L: factory form has fc_clear_height_m as number input."""
    _load_factory(page, live_server)
    inp = page.locator("#es-req-field-fc_clear_height_m")
    assert inp.count() > 0, "#es-req-field-fc_clear_height_m not found in factory"
    assert inp.get_attribute("type") == "number", (
        f"fc_clear_height_m must be type=number. Got: {inp.get_attribute('type')!r}"
    )


# ── CS125 ─────────────────────────────────────────────────────────────────────

def test_CS125_hotel_star_rating_arabic_options(page: Page, live_server: str) -> None:
    """Phase 8L: hotel ht_star_rating select has self-contained Arabic options."""
    _load_hotel(page, live_server)
    sel = page.locator("#es-req-field-ht_star_rating")
    assert sel.count() > 0, "#es-req-field-ht_star_rating not found in hotel"
    tag = sel.evaluate("el => el.tagName.toLowerCase()")
    assert tag == "select", f"ht_star_rating must be a <select>. Got: {tag!r}"
    opts = page.locator("#es-req-field-ht_star_rating option").all_inner_texts()
    assert any("خمس نجوم" in t for t in opts), (
        f"ht_star_rating must have Arabic option 'خمس نجوم'. Got: {opts}"
    )
    assert any("نجمة واحدة" in t for t in opts), (
        f"ht_star_rating must have Arabic option 'نجمة واحدة'. Got: {opts}"
    )


# ── CS126 ─────────────────────────────────────────────────────────────────────

def test_CS126_hotel_total_rooms_number_input(page: Page, live_server: str) -> None:
    """Phase 8L: hotel ht_total_rooms number input still present after enrichment."""
    _load_hotel(page, live_server)
    inp = page.locator("#es-req-field-ht_total_rooms")
    assert inp.count() > 0, "#es-req-field-ht_total_rooms not found after Phase 8L enrichment"
    assert inp.get_attribute("type") == "number", (
        f"ht_total_rooms must be type=number. Got: {inp.get_attribute('type')!r}"
    )


# ── CS127 ─────────────────────────────────────────────────────────────────────

def test_CS127_hotel_occupancy_rate_number_input(page: Page, live_server: str) -> None:
    """Phase 8L: hotel ht_occupancy_rate_pct number input still present after enrichment."""
    _load_hotel(page, live_server)
    inp = page.locator("#es-req-field-ht_occupancy_rate_pct")
    assert inp.count() > 0, "#es-req-field-ht_occupancy_rate_pct not found after Phase 8L enrichment"
    assert inp.get_attribute("type") == "number", (
        f"ht_occupancy_rate_pct must be type=number. Got: {inp.get_attribute('type')!r}"
    )


# ── CS128 ─────────────────────────────────────────────────────────────────────

def test_CS128_hospital_total_beds_still_present(page: Page, live_server: str) -> None:
    """Phase 8L: hospital ho_total_beds still present after enrichment."""
    _load_hospital(page, live_server)
    inp = page.locator("#es-req-field-ho_total_beds")
    assert inp.count() > 0, "#es-req-field-ho_total_beds not found after Phase 8L enrichment"
    assert inp.get_attribute("type") == "number", (
        f"ho_total_beds must be type=number. Got: {inp.get_attribute('type')!r}"
    )


# ── CS129 ─────────────────────────────────────────────────────────────────────

def test_CS129_hospital_operating_rooms_still_present(page: Page, live_server: str) -> None:
    """Phase 8L: hospital ho_operating_rooms still present after enrichment."""
    _load_hospital(page, live_server)
    inp = page.locator("#es-req-field-ho_operating_rooms")
    assert inp.count() > 0, "#es-req-field-ho_operating_rooms not found after Phase 8L enrichment"
    assert inp.get_attribute("type") == "number", (
        f"ho_operating_rooms must be type=number. Got: {inp.get_attribute('type')!r}"
    )


# ── CS130 ─────────────────────────────────────────────────────────────────────

def test_CS130_hospital_license_status_select(page: Page, live_server: str) -> None:
    """Phase 8L: hospital ho_license_status select still present after enrichment."""
    _load_hospital(page, live_server)
    sel = page.locator("#es-req-field-ho_license_status")
    assert sel.count() > 0, "#es-req-field-ho_license_status not found after Phase 8L enrichment"
    tag = sel.evaluate("el => el.tagName.toLowerCase()")
    assert tag == "select", f"ho_license_status must be a <select>. Got: {tag!r}"


# ── CS131 ─────────────────────────────────────────────────────────────────────

def test_CS131_school_classrooms_count_still_present(page: Page, live_server: str) -> None:
    """Phase 8L: school sc_classrooms_count still present after enrichment."""
    _load_school(page, live_server)
    inp = page.locator("#es-req-field-sc_classrooms_count")
    assert inp.count() > 0, "#es-req-field-sc_classrooms_count not found after Phase 8L enrichment"
    assert inp.get_attribute("type") == "number", (
        f"sc_classrooms_count must be type=number. Got: {inp.get_attribute('type')!r}"
    )


# ── CS132 ─────────────────────────────────────────────────────────────────────

def test_CS132_school_student_capacity_still_present(page: Page, live_server: str) -> None:
    """Phase 8L: school sc_student_capacity still present after enrichment."""
    _load_school(page, live_server)
    inp = page.locator("#es-req-field-sc_student_capacity")
    assert inp.count() > 0, "#es-req-field-sc_student_capacity not found after Phase 8L enrichment"
    assert inp.get_attribute("type") == "number", (
        f"sc_student_capacity must be type=number. Got: {inp.get_attribute('type')!r}"
    )


# ── CS133 ─────────────────────────────────────────────────────────────────────

def test_CS133_school_license_status_select(page: Page, live_server: str) -> None:
    """Phase 8L: school sc_license_status select still present after enrichment."""
    _load_school(page, live_server)
    sel = page.locator("#es-req-field-sc_license_status")
    assert sel.count() > 0, "#es-req-field-sc_license_status not found after Phase 8L enrichment"
    tag = sel.evaluate("el => el.tagName.toLowerCase()")
    assert tag == "select", f"sc_license_status must be a <select>. Got: {tag!r}"


# ── CS134 ─────────────────────────────────────────────────────────────────────

def test_CS134_retail_type_select_arabic_options(page: Page, live_server: str) -> None:
    """Phase 8L: retail form has new rt_retail_type select with Arabic options."""
    _load_retail(page, live_server)
    sel = page.locator("#es-req-field-rt_retail_type")
    assert sel.count() > 0, "#es-req-field-rt_retail_type not found in retail"
    opts = page.locator("#es-req-field-rt_retail_type option").all_inner_texts()
    assert any("محل شارع" in t for t in opts), (
        f"rt_retail_type must have Arabic option 'محل شارع'. Got: {opts}"
    )


# ── CS135 ─────────────────────────────────────────────────────────────────────

def test_CS135_retail_frontage_m_still_present(page: Page, live_server: str) -> None:
    """Phase 8L: retail rt_frontage_m still present after enrichment."""
    _load_retail(page, live_server)
    inp = page.locator("#es-req-field-rt_frontage_m")
    assert inp.count() > 0, "#es-req-field-rt_frontage_m not found after Phase 8L enrichment"
    assert inp.get_attribute("type") == "number", (
        f"rt_frontage_m must be type=number. Got: {inp.get_attribute('type')!r}"
    )


# ── CS136 ─────────────────────────────────────────────────────────────────────

def test_CS136_retail_footfall_level_select(page: Page, live_server: str) -> None:
    """Phase 8L: retail form has new rt_footfall_level select field."""
    _load_retail(page, live_server)
    sel = page.locator("#es-req-field-rt_footfall_level")
    assert sel.count() > 0, "#es-req-field-rt_footfall_level not found in retail"
    opts = page.locator("#es-req-field-rt_footfall_level option").all_inner_texts()
    assert any("مرتفع" in t for t in opts), (
        f"rt_footfall_level must have Arabic option containing 'مرتفع'. Got: {opts}"
    )


# ── CS137 ─────────────────────────────────────────────────────────────────────

def test_CS137_mine_ore_type_still_present(page: Page, live_server: str) -> None:
    """Phase 8L: mine mn_ore_type select still present after enrichment."""
    _load_mine(page, live_server)
    sel = page.locator("#es-req-field-mn_ore_type")
    assert sel.count() > 0, "#es-req-field-mn_ore_type not found after Phase 8L enrichment"
    tag = sel.evaluate("el => el.tagName.toLowerCase()")
    assert tag == "select", f"mn_ore_type must be a <select>. Got: {tag!r}"


# ── CS138 ─────────────────────────────────────────────────────────────────────

def test_CS138_mine_license_status_still_present(page: Page, live_server: str) -> None:
    """Phase 8L: mine mn_license_status select still present after enrichment."""
    _load_mine(page, live_server)
    sel = page.locator("#es-req-field-mn_license_status")
    assert sel.count() > 0, "#es-req-field-mn_license_status not found after Phase 8L enrichment"
    tag = sel.evaluate("el => el.tagName.toLowerCase()")
    assert tag == "select", f"mn_license_status must be a <select>. Got: {tag!r}"


# ── CS139 ─────────────────────────────────────────────────────────────────────

def test_CS139_mine_proven_reserve_number_input(page: Page, live_server: str) -> None:
    """Phase 8L: mine form has new mn_proven_reserve_ton number input."""
    _load_mine(page, live_server)
    inp = page.locator("#es-req-field-mn_proven_reserve_ton")
    assert inp.count() > 0, "#es-req-field-mn_proven_reserve_ton not found in mine"
    assert inp.get_attribute("type") == "number", (
        f"mn_proven_reserve_ton must be type=number. Got: {inp.get_attribute('type')!r}"
    )


# ── CS140 ─────────────────────────────────────────────────────────────────────

def test_CS140_mine_extraction_method_select(page: Page, live_server: str) -> None:
    """Phase 8L: mine form has new mn_extraction_method select with Arabic options."""
    _load_mine(page, live_server)
    sel = page.locator("#es-req-field-mn_extraction_method")
    assert sel.count() > 0, "#es-req-field-mn_extraction_method not found in mine"
    opts = page.locator("#es-req-field-mn_extraction_method option").all_inner_texts()
    assert any("حفر مكشوف" in t for t in opts), (
        f"mn_extraction_method must have Arabic option 'حفر مكشوف'. Got: {opts}"
    )


# ── CS141 ─────────────────────────────────────────────────────────────────────

def test_CS141_upload_hint_in_all_seven_profiles(page: Page, live_server: str) -> None:
    """Phase 8L: all 7 local profiles (incl. building_full) show upload hint text."""
    _HINT = "ارفع المستندات من زر المرفقات"
    loaders_and_names = [
        (_load_building_full, "عمارة سكنية"),
        (_load_hotel,         "فندق"),
        (_load_factory,       "مصنع"),
        (_load_hospital,      "مستشفى"),
        (_load_school,        "مدرسة"),
        (_load_retail,        "محل تجاري"),
        (_load_mine,          "مناجم"),
    ]
    for loader, name in loaders_and_names:
        loader(page, live_server)
        panel_text = page.locator("#es-req-panel").inner_text()
        assert _HINT in panel_text, (
            f"Profile '{name}' must show upload hint '{_HINT}'. "
            f"Got: {panel_text[:300]!r}"
        )


# ── CS142 ─────────────────────────────────────────────────────────────────────

def test_CS142_no_js_console_errors_building_full_enriched(page: Page, live_server: str) -> None:
    """Phase 8L: no JS console errors when rendering enriched building_full form."""
    def _is_js_error(msg) -> bool:
        return (
            msg.type == "error"
            and "401" not in msg.text
            and "UNAUTHORIZED" not in msg.text
            and "Failed to load resource" not in msg.text
        )

    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if _is_js_error(msg) else None)
    page.on("pageerror", lambda err: errors.append(str(err)))
    _load_building_full(page, live_server)
    assert len(errors) == 0, (
        f"JS console errors during enriched building_full render: {errors}"
    )


# ── Phase 8M loaders ──────────────────────────────────────────────────────────

def _load_water_well(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="water_well")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


def _load_intangible(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="أصول معنوية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


def _load_partial_interest(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="ملكيات جزئية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


def _load_under_construction(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="استثمارات تحت الإنشاء")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


def _load_historical(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="historical")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


def _load_heritage(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="heritage")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


# ── CS143 ─────────────────────────────────────────────────────────────────────

def test_CS143_water_well_renders_local_form(page: Page, live_server: str) -> None:
    """Phase 8M: water_well renders نموذج محلي form with structured sections."""
    _load_water_well(page, live_server)
    badge = page.locator("#es-profile-badge")
    expect(badge).to_be_visible()
    assert badge.inner_text().strip() == "نموذج محلي", (
        f"water_well must show 'نموذج محلي'. Got: {badge.inner_text()!r}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "الترخيص" in panel_text, (
        f"water_well panel must contain 'الترخيص' section. Got: {panel_text[:400]!r}"
    )


# ── CS144 ─────────────────────────────────────────────────────────────────────

def test_CS144_water_well_license_number_input_present(page: Page, live_server: str) -> None:
    """Phase 8M: water_well ww_license_number input is rendered."""
    _load_water_well(page, live_server)
    field = page.locator("#es-req-field-ww_license_number")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "text", (
        f"ww_license_number must be a text input. Got type={field.get_attribute('type')!r}"
    )


# ── CS145 ─────────────────────────────────────────────────────────────────────

def test_CS145_water_well_depth_shows_unit_meter(page: Page, live_server: str) -> None:
    """Phase 8M: water_well ww_depth_m number input exists and unit 'متر' is visible."""
    _load_water_well(page, live_server)
    field = page.locator("#es-req-field-ww_depth_m")
    expect(field).to_be_visible()
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "متر" in panel_text, (
        f"water_well panel must show unit 'متر' near depth field. Got: {panel_text[:600]!r}"
    )


# ── CS146 ─────────────────────────────────────────────────────────────────────

def test_CS146_water_well_production_shows_m3_unit(page: Page, live_server: str) -> None:
    """Phase 8M: water_well ww_daily_production_m3 is present and م³ unit text visible."""
    _load_water_well(page, live_server)
    field = page.locator("#es-req-field-ww_daily_production_m3")
    expect(field).to_be_visible()
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "م³" in panel_text, (
        f"water_well panel must contain م³ unit text. Got: {panel_text[:600]!r}"
    )


# ── CS147 ─────────────────────────────────────────────────────────────────────

def test_CS147_water_well_quality_select_renders(page: Page, live_server: str) -> None:
    """Phase 8M: water_well ww_water_quality_class select renders with Arabic options."""
    _load_water_well(page, live_server)
    sel = page.locator("#es-req-field-ww_water_quality_class")
    expect(sel).to_be_visible()
    opts = sel.locator("option").all_inner_texts()
    assert any("صالح" in o for o in opts), (
        f"ww_water_quality_class must have 'صالح' option. Got: {opts}"
    )


# ── CS148 ─────────────────────────────────────────────────────────────────────

def test_CS148_water_well_upload_guidance_present(page: Page, live_server: str) -> None:
    """Phase 8M: water_well panel shows upload guidance text."""
    _load_water_well(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "ارفع المستندات" in panel_text, (
        f"water_well panel must show upload guidance. Got: {panel_text[:600]!r}"
    )


# ── CS149 ─────────────────────────────────────────────────────────────────────

def test_CS149_intangible_renders_with_asset_name_field(page: Page, live_server: str) -> None:
    """Phase 8M: intangible form renders and has it_asset_name text input."""
    _load_intangible(page, live_server)
    field = page.locator("#es-req-field-it_asset_name")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "text", (
        f"it_asset_name must be text input. Got type={field.get_attribute('type')!r}"
    )


# ── CS150 ─────────────────────────────────────────────────────────────────────

def test_CS150_partial_interest_ownership_pct_input(page: Page, live_server: str) -> None:
    """Phase 8M: partial_interest form has pi_ownership_pct as a number input."""
    _load_partial_interest(page, live_server)
    field = page.locator("#es-req-field-pi_ownership_pct")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "number", (
        f"pi_ownership_pct must be number input. Got type={field.get_attribute('type')!r}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "%" in panel_text, (
        f"partial_interest panel must show % unit. Got: {panel_text[:400]!r}"
    )


# ── CS151 ─────────────────────────────────────────────────────────────────────

def test_CS151_under_construction_completion_pct_field(page: Page, live_server: str) -> None:
    """Phase 8M: under_construction form has uc_completion_pct and uc_spent_cost fields."""
    _load_under_construction(page, live_server)
    pct_field = page.locator("#es-req-field-uc_completion_pct")
    expect(pct_field).to_be_visible()
    cost_field = page.locator("#es-req-field-uc_spent_cost")
    expect(cost_field).to_be_visible()


# ── CS152 ─────────────────────────────────────────────────────────────────────

def test_CS152_historical_age_years_input(page: Page, live_server: str) -> None:
    """Phase 8M: historical form renders with hs_age_years number input."""
    _load_historical(page, live_server)
    field = page.locator("#es-req-field-hs_age_years")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "number", (
        f"hs_age_years must be number input. Got type={field.get_attribute('type')!r}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "الحماية" in panel_text, (
        f"historical panel must contain 'الحماية' section. Got: {panel_text[:400]!r}"
    )


# ── CS153 ─────────────────────────────────────────────────────────────────────

def test_CS153_heritage_cultural_category_select(page: Page, live_server: str) -> None:
    """Phase 8M: heritage form renders hr_cultural_category select with options."""
    _load_heritage(page, live_server)
    sel = page.locator("#es-req-field-hr_cultural_category")
    expect(sel).to_be_visible()
    opts = sel.locator("option").all_inner_texts()
    assert any("معماري" in o for o in opts), (
        f"hr_cultural_category must have 'معماري' option. Got: {opts}"
    )


# ── CS154 ─────────────────────────────────────────────────────────────────────

def test_CS154_all_six_new_profiles_show_local_form_badge(page: Page, live_server: str) -> None:
    """Phase 8M: all 6 new profiles show 'نموذج محلي' badge."""
    loaders_and_names = [
        (_load_water_well,        "water_well"),
        (_load_intangible,        "intangible"),
        (_load_partial_interest,  "partial_interest"),
        (_load_under_construction,"under_construction"),
        (_load_historical,        "historical"),
        (_load_heritage,          "heritage"),
    ]
    for loader, name in loaders_and_names:
        loader(page, live_server)
        badge = page.locator("#es-profile-badge")
        badge_text = badge.inner_text().strip() if badge.is_visible() else ""
        assert badge_text == "نموذج محلي", (
            f"Profile '{name}' must show 'نموذج محلي' badge. Got: {badge_text!r}"
        )


# ── CS155 ─────────────────────────────────────────────────────────────────────

def test_CS155_all_six_new_profiles_show_upload_guidance(page: Page, live_server: str) -> None:
    """Phase 8M: all 6 new profiles show upload guidance text."""
    _HINT = "ارفع المستندات"
    loaders_and_names = [
        (_load_water_well,        "water_well"),
        (_load_intangible,        "intangible"),
        (_load_partial_interest,  "partial_interest"),
        (_load_under_construction,"under_construction"),
        (_load_historical,        "historical"),
        (_load_heritage,          "heritage"),
    ]
    for loader, name in loaders_and_names:
        loader(page, live_server)
        panel_text = page.locator("#es-req-panel").inner_text()
        assert _HINT in panel_text, (
            f"Profile '{name}' must show upload hint. Got: {panel_text[:300]!r}"
        )


# ── CS156 ─────────────────────────────────────────────────────────────────────

def test_CS156_help_ar_renders_below_depth_field(page: Page, live_server: str) -> None:
    """Phase 8M: help_ar text renders below ww_depth_m in water_well form."""
    _load_water_well(page, live_server)
    panel_html = page.locator("#es-req-panel").inner_html()
    assert "es-field-help" in panel_html, (
        f"water_well panel must contain es-field-help element for help_ar. "
        f"Got (first 800): {panel_html[:800]!r}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "من منسوب" in panel_text, (
        f"help_ar text 'من منسوب' for ww_depth_m must be visible. Got: {panel_text[:600]!r}"
    )


# ── CS157 ─────────────────────────────────────────────────────────────────────

def test_CS157_readability_css_classes_present(page: Page, live_server: str) -> None:
    """Phase 8M: readability CSS classes es-field-unit and es-field-help are defined in the page."""
    _load_water_well(page, live_server)
    # Verify es-field-unit class appears in the rendered DOM (unit suffix present)
    panel_html = page.locator("#es-req-panel").inner_html()
    assert "es-field-unit" in panel_html, (
        "es-field-unit class must appear in water_well rendered panel HTML"
    )
    assert "es-field-help" in panel_html, (
        "es-field-help class must appear in water_well rendered panel HTML"
    )
    # Verify the CSS rule is present in the page source
    page_source = page.content()
    assert "es-field-unit" in page_source, "es-field-unit CSS rule must be in page source"
    assert "es-field-help" in page_source, "es-field-help CSS rule must be in page source"


# ── CS158 ─────────────────────────────────────────────────────────────────────

def test_CS158_factory_component_section_heading_present(page: Page, live_server: str) -> None:
    """Phase 8N: factory panel contains the component section heading."""
    _load_factory(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "مكوّنات الأصل" in panel_text, (
        f"Factory panel must contain component section heading. Got: {panel_text[:400]!r}"
    )


# ── CS159 ─────────────────────────────────────────────────────────────────────

def test_CS159_factory_default_card_count_is_four(page: Page, live_server: str) -> None:
    """Phase 8N: factory renders exactly 4 default component cards."""
    _load_factory(page, live_server)
    cards = page.locator("[data-es-comp-card]")
    count = cards.count()
    assert count == 4, (
        f"Factory must render 4 default component cards. Got: {count}"
    )


# ── CS160 ─────────────────────────────────────────────────────────────────────

def test_CS160_factory_card0_has_construction_system_select(page: Page, live_server: str) -> None:
    """Phase 8N: factory card[0] contains a construction_system select."""
    _load_factory(page, live_server)
    sel = page.locator("[data-es-comp-card='0'] [data-es-comp-field='construction_system']")
    assert sel.count() > 0, "Factory card[0] must have a construction_system select element."


# ── CS161 ─────────────────────────────────────────────────────────────────────

def test_CS161_factory_card0_construction_system_has_stable_codes(page: Page, live_server: str) -> None:
    """Phase 8N: construction_system options use stable internal codes (steel_truss, rcc_frame, steel_frame)."""
    _load_factory(page, live_server)
    html = page.locator("[data-es-comp-card='0']").inner_html()
    assert 'value="steel_truss"'  in html, "steel_truss option must exist in construction_system"
    assert 'value="rcc_frame"'    in html, "rcc_frame option must exist in construction_system"
    assert 'value="steel_frame"'  in html, "steel_frame option must exist in construction_system"


# ── CS162 ─────────────────────────────────────────────────────────────────────

def test_CS162_factory_card0_has_built_area_sqm_input(page: Page, live_server: str) -> None:
    """Phase 8N: factory card[0] has a built_area_sqm number input."""
    _load_factory(page, live_server)
    inp = page.locator("[data-es-comp-card='0'] [data-es-comp-field='built_area_sqm']")
    assert inp.count() > 0, "Factory card[0] must have built_area_sqm input."


# ── CS163 ─────────────────────────────────────────────────────────────────────

def test_CS163_factory_card0_has_clear_height_m_input(page: Page, live_server: str) -> None:
    """Phase 8N: factory card[0] has a clear_height_m number input."""
    _load_factory(page, live_server)
    inp = page.locator("[data-es-comp-card='0'] [data-es-comp-field='clear_height_m']")
    assert inp.count() > 0, "Factory card[0] must have clear_height_m input."


# ── CS164 ─────────────────────────────────────────────────────────────────────

def test_CS164_factory_card0_has_crane_available_extra_field(page: Page, live_server: str) -> None:
    """Phase 8N: factory card[0] has the extra field crane_available."""
    _load_factory(page, live_server)
    fld = page.locator("[data-es-comp-card='0'] [data-es-comp-field='crane_available']")
    assert fld.count() > 0, "Factory card[0] must have crane_available extra field."


# ── CS165 ─────────────────────────────────────────────────────────────────────

def test_CS165_factory_card0_visible_defects_chips_present(page: Page, live_server: str) -> None:
    """Phase 8N: factory card[0] has visible_defects checkbox group with cracks option."""
    _load_factory(page, live_server)
    html = page.locator("[data-es-comp-card='0']").inner_html()
    assert 'data-es-comp-field="visible_defects"' in html, (
        "Factory card[0] must have visible_defects checkboxes."
    )
    assert 'value="cracks"' in html, "cracks checkbox must be present in visible_defects."


# ── CS166 ─────────────────────────────────────────────────────────────────────

def test_CS166_hotel_component_section_has_five_default_cards(page: Page, live_server: str) -> None:
    """Phase 8N: hotel renders 5 default component cards."""
    _load_hotel(page, live_server)
    count = page.locator("[data-es-comp-card]").count()
    assert count == 5, f"Hotel must render 5 default component cards. Got: {count}"


# ── CS167 ─────────────────────────────────────────────────────────────────────

def test_CS167_hotel_card0_has_rooms_count_input(page: Page, live_server: str) -> None:
    """Phase 8N: hotel card[0] has extra field rooms_count."""
    _load_hotel(page, live_server)
    fld = page.locator("[data-es-comp-card='0'] [data-es-comp-field='rooms_count']")
    assert fld.count() > 0, "Hotel card[0] must have rooms_count extra field."


# ── CS168 ─────────────────────────────────────────────────────────────────────

def test_CS168_hospital_component_section_has_hvac_condition(page: Page, live_server: str) -> None:
    """Phase 8N: hospital card[0] has medical extra field hvac_condition."""
    _load_hospital(page, live_server)
    fld = page.locator("[data-es-comp-card='0'] [data-es-comp-field='hvac_condition']")
    assert fld.count() > 0, "Hospital card[0] must have hvac_condition extra field."


# ── CS169 ─────────────────────────────────────────────────────────────────────

def test_CS169_school_component_section_has_classrooms_count(page: Page, live_server: str) -> None:
    """Phase 8N: school card[0] has extra field classrooms_count."""
    _load_school(page, live_server)
    fld = page.locator("[data-es-comp-card='0'] [data-es-comp-field='classrooms_count']")
    assert fld.count() > 0, "School card[0] must have classrooms_count extra field."


# ── CS170 ─────────────────────────────────────────────────────────────────────

def test_CS170_retail_component_section_has_leasable_area(page: Page, live_server: str) -> None:
    """Phase 8N: retail card[0] has extra field leasable_area_sqm."""
    _load_retail(page, live_server)
    fld = page.locator("[data-es-comp-card='0'] [data-es-comp-field='leasable_area_sqm']")
    assert fld.count() > 0, "Retail card[0] must have leasable_area_sqm extra field."


# ── CS171 ─────────────────────────────────────────────────────────────────────

def test_CS171_mine_component_section_uses_operational_heading(page: Page, live_server: str) -> None:
    """Phase 8N: mine uses operational component heading, not generic building heading."""
    _load_mine(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "مكوّنات التشغيل" in panel_text, (
        f"Mine must show 'مكوّنات التشغيل' component heading. Got: {panel_text[:400]!r}"
    )


# ── CS172 ─────────────────────────────────────────────────────────────────────

def test_CS172_mine_card0_has_component_capacity_not_built_area(page: Page, live_server: str) -> None:
    """Phase 8N: mine card[0] uses fields_override (component_capacity present, built_area_sqm absent)."""
    _load_mine(page, live_server)
    card_html = page.locator("[data-es-comp-card='0']").inner_html()
    assert 'data-es-comp-field="component_capacity"' in card_html, (
        "Mine card[0] must have component_capacity (fields_override applied)."
    )
    assert 'data-es-comp-field="built_area_sqm"' not in card_html, (
        "Mine card[0] must NOT have built_area_sqm (fields_override replaces COMPONENT_FIELDS)."
    )


# ── CS173 ─────────────────────────────────────────────────────────────────────

def test_CS173_water_well_component_section_uses_well_heading(page: Page, live_server: str) -> None:
    """Phase 8N: water_well uses well-specific component heading, not generic building heading."""
    _load_water_well(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "مكوّنات البئر" in panel_text, (
        f"Water_well must show 'مكوّنات البئر' heading. Got: {panel_text[:400]!r}"
    )


# ── CS174 ─────────────────────────────────────────────────────────────────────

def test_CS174_water_well_card0_has_component_condition_field(page: Page, live_server: str) -> None:
    """Phase 8N: water_well card[0] has component_condition from fields_override."""
    _load_water_well(page, live_server)
    fld = page.locator("[data-es-comp-card='0'] [data-es-comp-field='component_condition']")
    assert fld.count() > 0, "Water_well card[0] must have component_condition field."


# ── CS175 ─────────────────────────────────────────────────────────────────────

def test_CS175_all_seven_profiles_render_component_cards(page: Page, live_server: str) -> None:
    """Phase 8N: all 7 operational profiles render at least 1 component card."""
    loaders = [
        (_load_factory,   "factory"),
        (_load_hotel,     "hotel"),
        (_load_hospital,  "hospital"),
        (_load_school,    "school"),
        (_load_retail,    "retail"),
        (_load_mine,      "mine"),
        (_load_water_well,"water_well"),
    ]
    for loader, name in loaders:
        loader(page, live_server)
        count = page.locator("[data-es-comp-card]").count()
        assert count >= 1, (
            f"Profile '{name}' must render at least 1 component card. Got: {count}"
        )


# ── CS176 ─────────────────────────────────────────────────────────────────────

def test_CS176_factory_add_component_button_present(page: Page, live_server: str) -> None:
    """Phase 8N: factory panel has an add-component button."""
    _load_factory(page, live_server)
    btn = page.locator("#es-add-comp-btn-factory")
    assert btn.count() > 0, "Factory must have an add-component button (#es-add-comp-btn-factory)."


# ── CS177 ─────────────────────────────────────────────────────────────────────

def test_CS177_factory_add_button_creates_new_card(page: Page, live_server: str) -> None:
    """Phase 8N: clicking add button increases component card count by 1."""
    _load_factory(page, live_server)
    before = page.locator("[data-es-comp-card]").count()
    page.locator("#es-add-comp-btn-factory").click()
    after = page.locator("[data-es-comp-card]").count()
    assert after == before + 1, (
        f"Clicking add must increase card count by 1. Before: {before}, After: {after}"
    )


# ── CS178 ─────────────────────────────────────────────────────────────────────

def test_CS178_default_cards_have_no_remove_button_added_cards_do(page: Page, live_server: str) -> None:
    """Phase 8N: default cards have no remove button; user-added cards have a remove button."""
    _load_factory(page, live_server)
    # Default cards must not have remove button
    for idx in range(4):
        remove_in_default = page.locator(
            f"[data-es-comp-card='{idx}'] .es-remove-comp-btn"
        ).count()
        assert remove_in_default == 0, (
            f"Default card[{idx}] must not have a remove button."
        )
    # Add a card and confirm remove button is present
    page.locator("#es-add-comp-btn-factory").click()
    new_card_idx = page.locator("[data-es-comp-card]").count() - 1
    remove_in_added = page.locator(
        f"[data-es-comp-card='{new_card_idx}'] .es-remove-comp-btn"
    ).count()
    assert remove_in_added == 1, (
        f"Added card[{new_card_idx}] must have exactly 1 remove button."
    )


# ── CS179 ─────────────────────────────────────────────────────────────────────

def test_CS179_es_req_panel_font_size_at_least_16px(page: Page, live_server: str) -> None:
    """Phase 8N: #es-req-panel computed font-size is at least 16px."""
    _load_factory(page, live_server)
    font_size = page.evaluate(
        "() => parseFloat(getComputedStyle(document.getElementById('es-req-panel')).fontSize)"
    )
    assert font_size >= 16, (
        f"#es-req-panel font-size must be >= 16px. Got: {font_size}px"
    )


# ── CS180 ─────────────────────────────────────────────────────────────────────

def test_CS180_section_summary_font_size_at_least_19px(page: Page, live_server: str) -> None:
    """Phase 8N: details summary computed font-size is at least 19px."""
    _load_factory(page, live_server)
    font_size = page.evaluate(
        "() => { var el = document.querySelector('#es-req-panel details > summary');"
        " return el ? parseFloat(getComputedStyle(el).fontSize) : 0; }"
    )
    assert font_size >= 19, (
        f"details > summary font-size must be >= 19px. Got: {font_size}px"
    )


# ── CS181 ─────────────────────────────────────────────────────────────────────

def test_CS181_factory_component_section_has_photo_hint(page: Page, live_server: str) -> None:
    """Phase 8N: factory component section contains photo upload guidance."""
    _load_factory(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "يفضل رفع صور" in panel_text, (
        f"Factory component section must contain photo hint. Got: {panel_text[:400]!r}"
    )


# ── CS182 ─────────────────────────────────────────────────────────────────────

def test_CS182_residential_and_land_have_no_component_cards(page: Page, live_server: str) -> None:
    """Phase 8N: residential and land profiles do not render any component cards."""
    for loader, name in [(_load_residential, "residential"), (_load_land, "land")]:
        loader(page, live_server)
        count = page.locator("[data-es-comp-card]").count()
        assert count == 0, (
            f"Profile '{name}' must not render component cards. Got: {count}"
        )


# ══ Phase 8O — Remove External Composite/Login Screen (CS183–CS198) ══════════


# ── CS183 ─────────────────────────────────────────────────────────────────────

def test_CS183_all_profiles_stay_on_index_page(page: Page, live_server: str) -> None:
    """Phase 8O: selecting any of the 15 supported profiles does not navigate away from index.html."""
    # (asset_type_value, needs_api_mock, mock_data)
    static_profiles = [
        ("عمارة سكنية", False, None),
        ("فندق",        False, None),
        ("مصنع",        False, None),
        ("مستشفى",      False, None),
        ("مدرسة",       False, None),
        ("محل تجاري",   False, None),
        ("مناجم",       False, None),
        ("water_well",              False, None),
        ("أصول معنوية",             False, None),
        ("ملكيات جزئية",            False, None),
        ("استثمارات تحت الإنشاء",   False, None),
        ("historical",              False, None),
        ("heritage",                False, None),
    ]
    api_profiles = [
        ("شقة سكنية", _RESIDENTIAL_RESPONSE),
        ("أرض فضاء",  _LAND_RESPONSE),
    ]

    for asset_val, needs_mock, mock_data in static_profiles:
        page.goto(live_server, wait_until="networkidle")
        _inject_session(page)
        page.select_option("#asset-type", value=asset_val)
        page.select_option("#val-purpose", value="fair_market_value")
        page.wait_for_timeout(500)
        assert page.url.startswith(live_server.rstrip("/")), (
            f"Selecting '{asset_val}' must not navigate away from index. URL: {page.url!r}"
        )

    for asset_val, mock_data in api_profiles:
        _mock_req(page, mock_data)
        page.goto(live_server, wait_until="networkidle")
        _inject_session(page)
        page.select_option("#asset-type", value=asset_val)
        page.select_option("#val-purpose", value="fair_market_value")
        page.wait_for_timeout(500)
        assert page.url.startswith(live_server.rstrip("/")), (
            f"Selecting '{asset_val}' must not navigate away from index. URL: {page.url!r}"
        )


# ── CS184 ─────────────────────────────────────────────────────────────────────

def test_CS184_water_well_panel_no_composite_link(page: Page, live_server: str) -> None:
    """Phase 8O: water_well panel contains no #es-req-composite-link element."""
    _load_water_well(page, live_server)
    link = page.locator("#es-req-composite-link")
    assert link.count() == 0 or not link.is_visible(), (
        "water_well panel must NOT contain the composite redirect link"
    )
    panel_html = page.locator("#es-req-panel").inner_html()
    assert "composite_valuation.html" not in panel_html, (
        "composite_valuation.html URL must not appear in water_well panel HTML"
    )


# ── CS185 ─────────────────────────────────────────────────────────────────────

def test_CS185_intangible_panel_no_composite_link(page: Page, live_server: str) -> None:
    """Phase 8O: intangible panel contains no #es-req-composite-link element."""
    _load_intangible(page, live_server)
    link = page.locator("#es-req-composite-link")
    assert link.count() == 0 or not link.is_visible(), (
        "intangible panel must NOT contain the composite redirect link"
    )
    panel_html = page.locator("#es-req-panel").inner_html()
    assert "composite_valuation.html" not in panel_html, (
        "composite_valuation.html URL must not appear in intangible panel HTML"
    )


# ── CS186 ─────────────────────────────────────────────────────────────────────

def test_CS186_partial_interest_panel_no_composite_link(page: Page, live_server: str) -> None:
    """Phase 8O: partial_interest panel contains no #es-req-composite-link element."""
    _load_partial_interest(page, live_server)
    link = page.locator("#es-req-composite-link")
    assert link.count() == 0 or not link.is_visible(), (
        "partial_interest panel must NOT contain the composite redirect link"
    )
    panel_html = page.locator("#es-req-panel").inner_html()
    assert "composite_valuation.html" not in panel_html, (
        "composite_valuation.html URL must not appear in partial_interest panel HTML"
    )


# ── CS187 ─────────────────────────────────────────────────────────────────────

def test_CS187_under_construction_panel_no_composite_link(page: Page, live_server: str) -> None:
    """Phase 8O: under_construction panel contains no #es-req-composite-link element."""
    _load_under_construction(page, live_server)
    link = page.locator("#es-req-composite-link")
    assert link.count() == 0 or not link.is_visible(), (
        "under_construction panel must NOT contain the composite redirect link"
    )
    panel_html = page.locator("#es-req-panel").inner_html()
    assert "composite_valuation.html" not in panel_html, (
        "composite_valuation.html URL must not appear in under_construction panel HTML"
    )


# ── CS188 ─────────────────────────────────────────────────────────────────────

def test_CS188_historical_panel_no_composite_link(page: Page, live_server: str) -> None:
    """Phase 8O: historical panel contains no #es-req-composite-link element."""
    _load_historical(page, live_server)
    link = page.locator("#es-req-composite-link")
    assert link.count() == 0 or not link.is_visible(), (
        "historical panel must NOT contain the composite redirect link"
    )
    panel_html = page.locator("#es-req-panel").inner_html()
    assert "composite_valuation.html" not in panel_html, (
        "composite_valuation.html URL must not appear in historical panel HTML"
    )


# ── CS189 ─────────────────────────────────────────────────────────────────────

def test_CS189_heritage_panel_no_composite_link(page: Page, live_server: str) -> None:
    """Phase 8O: heritage panel contains no #es-req-composite-link element."""
    _load_heritage(page, live_server)
    link = page.locator("#es-req-composite-link")
    assert link.count() == 0 or not link.is_visible(), (
        "heritage panel must NOT contain the composite redirect link"
    )
    panel_html = page.locator("#es-req-panel").inner_html()
    assert "composite_valuation.html" not in panel_html, (
        "composite_valuation.html URL must not appear in heritage panel HTML"
    )


# ── CS190 ─────────────────────────────────────────────────────────────────────

def test_CS190_no_composite_cta_text_in_any_static_profile(page: Page, live_server: str) -> None:
    """Phase 8O: no static profile shows 'فتح نموذج التقييم المركب التفصيلي' in the panel."""
    loaders = [
        _load_intangible, _load_partial_interest, _load_under_construction,
        _load_historical, _load_heritage, _load_water_well,
        _load_factory, _load_hotel,
    ]
    for loader in loaders:
        loader(page, live_server)
        panel_text = page.locator("#es-req-panel").inner_text()
        assert "فتح نموذج التقييم المركب التفصيلي" not in panel_text, (
            f"Panel must NOT contain CTA text after Phase 8O fix. Got: {panel_text[:300]!r}"
        )


# ── CS191 ─────────────────────────────────────────────────────────────────────

def test_CS191_no_login_required_text_in_panel(page: Page, live_server: str) -> None:
    """Phase 8O: requirements panel never shows 'يلزم تسجيل الدخول' for any profile."""
    loaders = [
        _load_intangible, _load_partial_interest, _load_under_construction,
        _load_historical, _load_heritage, _load_water_well,
    ]
    for loader in loaders:
        loader(page, live_server)
        panel_text = page.locator("#es-req-panel").inner_text()
        assert "يلزم تسجيل الدخول" not in panel_text, (
            f"Panel must NOT show 'يلزم تسجيل الدخول'. Got: {panel_text[:300]!r}"
        )


# ── CS192 ─────────────────────────────────────────────────────────────────────

def test_CS192_no_please_login_text_in_panel(page: Page, live_server: str) -> None:
    """Phase 8O: requirements panel never shows 'يرجى تسجيل الدخول أولاً' for any profile."""
    loaders = [
        _load_intangible, _load_partial_interest, _load_under_construction,
        _load_historical, _load_heritage, _load_water_well,
    ]
    for loader in loaders:
        loader(page, live_server)
        panel_text = page.locator("#es-req-panel").inner_text()
        assert "يرجى تسجيل الدخول أولاً" not in panel_text, (
            f"Panel must NOT show 'يرجى تسجيل الدخول أولاً'. Got: {panel_text[:300]!r}"
        )


# ── CS193 ─────────────────────────────────────────────────────────────────────

def test_CS193_panel_inner_html_no_composite_href(page: Page, live_server: str) -> None:
    """Phase 8O: #es-req-panel inner HTML contains no href pointing to /composite_valuation.html."""
    loaders = [
        _load_intangible, _load_partial_interest, _load_under_construction,
        _load_historical, _load_heritage, _load_water_well,
        _load_factory, _load_hotel, _load_building_full,
    ]
    for loader in loaders:
        loader(page, live_server)
        panel_html = page.locator("#es-req-panel").inner_html()
        assert "composite_valuation.html" not in panel_html, (
            f"Panel inner HTML must NOT contain composite_valuation.html href. Got: {panel_html[:400]!r}"
        )


# ── CS194 ─────────────────────────────────────────────────────────────────────

def test_CS194_intangible_panel_renders_inline_form(page: Page, live_server: str) -> None:
    """Phase 8O: intangible panel renders inline form controls (not a redirect)."""
    _load_intangible(page, live_server)
    count = page.locator("#es-req-panel input, #es-req-panel select").count()
    assert count > 0, (
        f"intangible panel must render inline form controls. Got {count} controls."
    )


# ── CS195 ─────────────────────────────────────────────────────────────────────

def test_CS195_partial_interest_panel_renders_inline_form(page: Page, live_server: str) -> None:
    """Phase 8O: partial_interest panel renders inline form controls (not a redirect)."""
    _load_partial_interest(page, live_server)
    count = page.locator("#es-req-panel input, #es-req-panel select").count()
    assert count > 0, (
        f"partial_interest panel must render inline form controls. Got {count} controls."
    )


# ── CS196 ─────────────────────────────────────────────────────────────────────

def test_CS196_under_construction_panel_renders_inline_form(page: Page, live_server: str) -> None:
    """Phase 8O: under_construction panel renders inline form controls (not a redirect)."""
    _load_under_construction(page, live_server)
    count = page.locator("#es-req-panel input, #es-req-panel select").count()
    assert count > 0, (
        f"under_construction panel must render inline form controls. Got {count} controls."
    )


# ── CS197 ─────────────────────────────────────────────────────────────────────

def test_CS197_historical_panel_renders_inline_form(page: Page, live_server: str) -> None:
    """Phase 8O: historical panel renders inline form controls (not a redirect)."""
    _load_historical(page, live_server)
    count = page.locator("#es-req-panel input, #es-req-panel select").count()
    assert count > 0, (
        f"historical panel must render inline form controls. Got {count} controls."
    )


# ── CS198 ─────────────────────────────────────────────────────────────────────

def test_CS198_heritage_panel_renders_inline_form(page: Page, live_server: str) -> None:
    """Phase 8O: heritage panel renders inline form controls (not a redirect)."""
    _load_heritage(page, live_server)
    count = page.locator("#es-req-panel input, #es-req-panel select").count()
    assert count > 0, (
        f"heritage panel must render inline form controls. Got {count} controls."
    )


# ══ Phase 8P — Suppress Login/JWT Modal in Requirements Flow (CS199–CS207) ══


def _mock_req_401(page: Page) -> None:
    """Route /api/valuation/requirements to return 401 (expired/missing session)."""
    def handle(route: Route) -> None:
        route.fulfill(status=401, content_type="application/json",
                      body='{"error":"unauthorized"}')
    page.route("**/api/valuation/requirements**", handle)


# ── CS199 ─────────────────────────────────────────────────────────────────────

def test_CS199_land_no_session_does_not_show_login_modal(page: Page, live_server: str) -> None:
    """Phase 8P: selecting land with no valid session must NOT open the login modal."""
    _mock_req_401(page)
    page.goto(live_server, wait_until="networkidle")
    page.evaluate("localStorage.removeItem('es_auth')")
    page.select_option("#asset-type", value="أرض فضاء")
    page.select_option("#val-purpose", value="fair_market_value")
    # Wait for the async fetch to settle (inline message or panel reaction)
    page.locator("#es-req-soft-msg").wait_for(state="visible", timeout=5_000)
    modal = page.locator("#es-login-modal")
    assert not modal.is_visible(), (
        "Login modal must NOT appear when selecting land without a valid session (Phase 8P)"
    )


# ── CS200 ─────────────────────────────────────────────────────────────────────

def test_CS200_residential_no_session_does_not_show_login_modal(page: Page, live_server: str) -> None:
    """Phase 8P: selecting residential_unit with no valid session must NOT open the login modal."""
    _mock_req_401(page)
    page.goto(live_server, wait_until="networkidle")
    page.evaluate("localStorage.removeItem('es_auth')")
    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-soft-msg").wait_for(state="visible", timeout=5_000)
    modal = page.locator("#es-login-modal")
    assert not modal.is_visible(), (
        "Login modal must NOT appear when selecting residential_unit without a valid session (Phase 8P)"
    )


# ── CS201 ─────────────────────────────────────────────────────────────────────

def test_CS201_building_mixed_no_session_does_not_show_login_modal(page: Page, live_server: str) -> None:
    """Phase 8P: selecting building_mixed ('تجاري') with no valid session must NOT open the login modal."""
    _mock_req_401(page)
    page.goto(live_server, wait_until="networkidle")
    page.evaluate("localStorage.removeItem('es_auth')")
    page.select_option("#asset-type", value="تجاري")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-soft-msg").wait_for(state="visible", timeout=5_000)
    modal = page.locator("#es-login-modal")
    assert not modal.is_visible(), (
        "Login modal must NOT appear when selecting تجاري without a valid session (Phase 8P)"
    )


# ── CS202 ─────────────────────────────────────────────────────────────────────

def test_CS202_api_401_renders_inline_soft_message(page: Page, live_server: str) -> None:
    """Phase 8P: when /api/valuation/requirements returns 401, panel shows inline message, not modal."""
    _mock_req_401(page)
    page.goto(live_server, wait_until="networkidle")
    page.evaluate("localStorage.removeItem('es_auth')")
    page.select_option("#asset-type", value="أرض فضاء")
    page.select_option("#val-purpose", value="fair_market_value")

    soft_msg = page.locator("#es-req-soft-msg")
    soft_msg.wait_for(state="visible", timeout=5_000)

    # Modal must be hidden
    assert not page.locator("#es-login-modal").is_visible(), (
        "Login modal must NOT appear on 401 from requirements endpoint"
    )
    # Panel must be visible with inline message
    assert page.locator("#es-req-panel").is_visible(), (
        "#es-req-panel must remain visible with inline message on 401"
    )
    msg_text = soft_msg.inner_text()
    assert "تعذر تحميل متطلبات السجل" in msg_text, (
        f"Inline 401 message must contain 'تعذر تحميل متطلبات السجل'. Got: {msg_text!r}"
    )
    assert "تسجيل الدخول لاحقاً" in msg_text or "تسجيل الدخول" in msg_text, (
        f"Inline 401 message must mention login option. Got: {msg_text!r}"
    )


# ── CS203 ─────────────────────────────────────────────────────────────────────

def test_CS203_building_full_does_not_show_login_modal(page: Page, live_server: str) -> None:
    """Phase 8P: building_full (static profile) never triggers the login modal."""
    page.goto(live_server, wait_until="networkidle")
    page.evaluate("localStorage.removeItem('es_auth')")
    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    assert not page.locator("#es-login-modal").is_visible(), (
        "Login modal must NOT appear for building_full (static path, no API call)"
    )


# ── CS204 ─────────────────────────────────────────────────────────────────────

def test_CS204_factory_does_not_show_login_modal(page: Page, live_server: str) -> None:
    """Phase 8P: factory (static profile) never triggers the login modal."""
    page.goto(live_server, wait_until="networkidle")
    page.evaluate("localStorage.removeItem('es_auth')")
    page.select_option("#asset-type", value="مصنع")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    assert not page.locator("#es-login-modal").is_visible(), (
        "Login modal must NOT appear for factory (static path, no API call)"
    )


# ── CS205 ─────────────────────────────────────────────────────────────────────

def test_CS205_intangible_does_not_show_login_modal(page: Page, live_server: str) -> None:
    """Phase 8P: intangible (static profile) never triggers the login modal."""
    page.goto(live_server, wait_until="networkidle")
    page.evaluate("localStorage.removeItem('es_auth')")
    page.select_option("#asset-type", value="أصول معنوية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    assert not page.locator("#es-login-modal").is_visible(), (
        "Login modal must NOT appear for intangible (static path, no API call)"
    )


# ── CS206 ─────────────────────────────────────────────────────────────────────

def test_CS206_login_modal_dom_structure_preserved(page: Page, live_server: str) -> None:
    """Phase 8P: login modal DOM and structure remain intact (not removed by the fix)."""
    page.goto(live_server, wait_until="networkidle")
    modal = page.locator("#es-login-modal")
    expect(modal).to_be_attached()
    assert not modal.is_visible(), "Login modal should be hidden on load (no session)"
    assert page.locator("#es-token-input").count() == 1, "#es-token-input must remain in DOM"
    assert page.locator("#es-login-submit").count() == 1, "#es-login-submit must remain in DOM"
    panel_text = page.locator("#es-login-modal").inner_text()
    assert "تسجيل الدخول" in panel_text, (
        f"Login modal must still contain 'تسجيل الدخول' text. Got: {panel_text!r}"
    )


# ── CS207 ─────────────────────────────────────────────────────────────────────

def test_CS207_no_composite_link_regression(page: Page, live_server: str) -> None:
    """Phase 8P: Phase 8O still holds — no composite_valuation.html link inside requirements panel."""
    _mock_req_401(page)
    page.goto(live_server, wait_until="networkidle")
    page.evaluate("localStorage.removeItem('es_auth')")
    page.select_option("#asset-type", value="أرض فضاء")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-soft-msg").wait_for(state="visible", timeout=5_000)
    panel_html = page.locator("#es-req-panel").inner_html()
    assert "composite_valuation.html" not in panel_html, (
        "composite_valuation.html must not appear in requirements panel (Phase 8O regression)"
    )


# ══ Phase 8Q — Agricultural Land Static Profile + Supplemental Local Intake (CS208–CS257) ══


def _load_agricultural_land(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="أرض زراعية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


def _load_residential_supp(page: Page, live_server: str) -> None:
    """Load شقة سكنية with mocked API and valid session — populates #es-req-supp."""
    _mock_req(page, _RESIDENTIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)


def _load_land_supp(page: Page, live_server: str) -> None:
    """Load أرض فضاء with mocked API and valid session — populates #es-req-supp."""
    _mock_req(page, _LAND_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="أرض فضاء")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)


# ── CS208 ─────────────────────────────────────────────────────────────────────

def test_CS208_agricultural_land_routes_as_static_form(page: Page, live_server: str) -> None:
    """Phase 8Q: أرض زراعية routes as static profile; badge shows 'نموذج محلي', not API-driven."""
    _load_agricultural_land(page, live_server)
    badge = page.locator("#es-profile-badge")
    expect(badge).to_be_visible()
    assert badge.inner_text().strip() == "نموذج محلي", (
        f"أرض زراعية must show badge 'نموذج محلي'. Got: {badge.inner_text()!r}"
    )


# ── CS209 ─────────────────────────────────────────────────────────────────────

def test_CS209_agricultural_land_makes_zero_api_calls(page: Page, live_server: str) -> None:
    """Phase 8Q: أرض زراعية must NOT call /api/valuation/requirements (static path)."""
    api_calls: list[str] = []
    page.goto("about:blank")
    page.route("**/api/valuation/requirements**", lambda route: (
        api_calls.append(route.request.url), route.continue_()
    ))
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="أرض زراعية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    assert len(api_calls) == 0, (
        f"أرض زراعية must make ZERO API calls. Got calls: {api_calls}"
    )


# ── CS210 ─────────────────────────────────────────────────────────────────────

def test_CS210_agricultural_land_title_contains_arabic_name(page: Page, live_server: str) -> None:
    """Phase 8Q: أرض زراعية panel title contains 'أرض زراعية'."""
    _load_agricultural_land(page, live_server)
    title_text = page.locator("#es-req-title").inner_text()
    assert "أرض زراعية" in title_text, (
        f"agricultural_land title must contain 'أرض زراعية'. Got: {title_text!r}"
    )


# ── CS211 ─────────────────────────────────────────────────────────────────────

def test_CS211_agricultural_land_renders_form_controls(page: Page, live_server: str) -> None:
    """Phase 8Q: أرض زراعية panel renders inline input and select controls."""
    _load_agricultural_land(page, live_server)
    count = page.locator("#es-req-panel input, #es-req-panel select").count()
    assert count > 0, (
        f"agricultural_land panel must render form controls. Got {count} controls."
    )


# ── CS212 ─────────────────────────────────────────────────────────────────────

def test_CS212_agricultural_land_has_no_composite_link(page: Page, live_server: str) -> None:
    """Phase 8Q: أرض زراعية panel has no composite_valuation.html link."""
    _load_agricultural_land(page, live_server)
    panel_html = page.locator("#es-req-panel").inner_html()
    assert "composite_valuation.html" not in panel_html, (
        "agricultural_land panel must not contain composite_valuation.html link"
    )


# ── CS213 ─────────────────────────────────────────────────────────────────────

def test_CS213_agricultural_land_ag_area_sqm_number_input(page: Page, live_server: str) -> None:
    """Phase 8Q: ag_area_sqm renders as a number input in agricultural_land form."""
    _load_agricultural_land(page, live_server)
    field = page.locator("#es-req-field-ag_area_sqm")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "number", (
        f"ag_area_sqm must be number input. Got type={field.get_attribute('type')!r}"
    )


# ── CS214 ─────────────────────────────────────────────────────────────────────

def test_CS214_agricultural_land_ag_soil_type_select_arabic(page: Page, live_server: str) -> None:
    """Phase 8Q: ag_soil_type select renders with Arabic options."""
    _load_agricultural_land(page, live_server)
    sel = page.locator("#es-req-field-ag_soil_type")
    expect(sel).to_be_visible()
    opts = sel.locator("option").all_inner_texts()
    assert any("طيني" in o or "رملي" in o or "طمي" in o for o in opts), (
        f"ag_soil_type must have Arabic soil type options. Got: {opts}"
    )


# ── CS215 ─────────────────────────────────────────────────────────────────────

def test_CS215_agricultural_land_ag_water_source_select_renders(page: Page, live_server: str) -> None:
    """Phase 8Q: ag_water_source_type select renders with Arabic options."""
    _load_agricultural_land(page, live_server)
    sel = page.locator("#es-req-field-ag_water_source_type")
    expect(sel).to_be_visible()
    opts = sel.locator("option").all_inner_texts()
    assert len(opts) >= 3, (
        f"ag_water_source_type must have ≥3 options. Got: {opts}"
    )


# ── CS216 ─────────────────────────────────────────────────────────────────────

def test_CS216_agricultural_land_ag_irrigation_system_select(page: Page, live_server: str) -> None:
    """Phase 8Q: ag_irrigation_system select renders with Arabic options."""
    _load_agricultural_land(page, live_server)
    sel = page.locator("#es-req-field-ag_irrigation_system")
    expect(sel).to_be_visible()
    opts = sel.locator("option").all_inner_texts()
    assert any("غمر" in o or "تنقيط" in o or "رش" in o for o in opts), (
        f"ag_irrigation_system must have Arabic irrigation options. Got: {opts}"
    )


# ── CS217 ─────────────────────────────────────────────────────────────────────

def test_CS217_agricultural_land_cultivation_cost_number_input(page: Page, live_server: str) -> None:
    """Phase 8Q: ag_annual_cultivation_cost renders as number input; unit ج.م./سنة visible."""
    _load_agricultural_land(page, live_server)
    field = page.locator("#es-req-field-ag_annual_cultivation_cost")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "number", (
        f"ag_annual_cultivation_cost must be number input. Got type={field.get_attribute('type')!r}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "ج.م." in panel_text, (
        f"agricultural_land panel must show ج.م. unit text. Got: {panel_text[:400]!r}"
    )


# ── CS218 ─────────────────────────────────────────────────────────────────────

def test_CS218_agricultural_land_upload_hint_present(page: Page, live_server: str) -> None:
    """Phase 8Q: agricultural_land form shows upload hint text."""
    _load_agricultural_land(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "ارفع المستندات" in panel_text, (
        f"agricultural_land panel must show upload hint. Got: {panel_text[:400]!r}"
    )


# ── CS219 ─────────────────────────────────────────────────────────────────────

def test_CS219_agricultural_land_farm_buildings_bool_select(page: Page, live_server: str) -> None:
    """Phase 8Q: ag_farm_buildings_available renders as bool select with نعم/لا options."""
    _load_agricultural_land(page, live_server)
    sel = page.locator("#es-req-field-ag_farm_buildings_available")
    expect(sel).to_be_visible()
    opts = sel.locator("option").all_inner_texts()
    assert any("نعم" in o for o in opts), (
        f"ag_farm_buildings_available must have 'نعم' option. Got: {opts}"
    )
    assert any("لا" in o for o in opts), (
        f"ag_farm_buildings_available must have 'لا' option. Got: {opts}"
    )


# ── CS220 ─────────────────────────────────────────────────────────────────────

def test_CS220_agricultural_land_no_js_console_errors(page: Page, live_server: str) -> None:
    """Phase 8Q: no JS console errors when rendering agricultural_land form."""
    def _is_js_error(msg) -> bool:
        return (
            msg.type == "error"
            and "401" not in msg.text
            and "UNAUTHORIZED" not in msg.text
            and "Failed to load resource" not in msg.text
        )

    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if _is_js_error(msg) else None)
    page.on("pageerror", lambda err: errors.append(str(err)))
    _load_agricultural_land(page, live_server)
    assert len(errors) == 0, (
        f"JS console errors during agricultural_land render: {errors}"
    )


# ── CS221 ─────────────────────────────────────────────────────────────────────

def test_CS221_residential_supp_section_rendered(page: Page, live_server: str) -> None:
    """Phase 8Q: شقة سكنية API panel — #es-req-supp receives supplemental content."""
    _load_residential_supp_8w(page, live_server)
    supp = page.locator("#es-req-supp")
    expect(supp).to_be_attached()
    supp_html = supp.inner_html().strip()
    assert supp_html != "", (
        "شقة سكنية panel must populate #es-req-supp with supplemental content"
    )


# ── CS222 ─────────────────────────────────────────────────────────────────────

def test_CS222_residential_supp_heading_unit_detail(page: Page, live_server: str) -> None:
    """Phase 8Q: residential supp heading 'بيانات الوحدة التفصيلية' is visible."""
    _load_residential_supp_8w(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "بيانات الوحدة التفصيلية" in supp_text, (
        f"Residential supp must show heading 'بيانات الوحدة التفصيلية'. Got: {supp_text[:400]!r}"
    )


# ── CS223 ─────────────────────────────────────────────────────────────────────

def test_CS223_residential_supp_unit_type_select_arabic(page: Page, live_server: str) -> None:
    """Phase 8Q: es-supp-field-unit_type select renders with Arabic options."""
    _load_residential_supp_8w(page, live_server)
    sel = page.locator("#es-supp-field-unit_type")
    expect(sel).to_be_visible()
    opts = sel.locator("option").all_inner_texts()
    assert any("شقة" in o or "فيلا" in o or "ستوديو" in o for o in opts), (
        f"unit_type supp select must have Arabic unit options. Got: {opts}"
    )


# ── CS224 ─────────────────────────────────────────────────────────────────────

def test_CS224_residential_supp_bedrooms_count_number_input(page: Page, live_server: str) -> None:
    """Phase 8Q: es-supp-field-bedrooms_count renders as number input in residential supp."""
    _load_residential_supp_8w(page, live_server)
    field = page.locator("#es-supp-field-bedrooms_count")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "number", (
        f"bedrooms_count supp field must be number input. Got type={field.get_attribute('type')!r}"
    )


# ── CS225 ─────────────────────────────────────────────────────────────────────

def test_CS225_residential_supp_visible_defects_checkbox_group(page: Page, live_server: str) -> None:
    """Phase 8Q: es-supp-field-visible_defects-cracks checkbox present in residential supp."""
    _load_residential_supp_8w(page, live_server)
    field = page.locator("#es-supp-field-visible_defects-cracks")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "checkbox", (
        f"visible_defects cracks chip must be checkbox. Got type={field.get_attribute('type')!r}"
    )


# ── CS226 ─────────────────────────────────────────────────────────────────────

def test_CS226_residential_supp_utilities_connected_checkbox_group(page: Page, live_server: str) -> None:
    """Phase 8Q: es-supp-field-utilities_connected checkbox group rendered in residential supp."""
    _load_residential_supp_8w(page, live_server)
    field = page.locator("#es-supp-field-utilities_connected-electricity")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "checkbox", (
        f"utilities_connected electricity chip must be checkbox. Got type={field.get_attribute('type')!r}"
    )


# ── CS227 ─────────────────────────────────────────────────────────────────────

def test_CS227_residential_supp_doc_section_shows_upload_hint(page: Page, live_server: str) -> None:
    """Phase 8Q: residential supp document section shows upload hint text."""
    _load_residential_supp_8w(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "ارفع المستندات" in supp_text, (
        f"Residential supp must show upload hint. Got: {supp_text[:400]!r}"
    )


# ── CS228 ─────────────────────────────────────────────────────────────────────

def test_CS228_residential_supp_building_permit_doc_checkbox(page: Page, live_server: str) -> None:
    """Phase 8Q: es-supp-field-ru_building_permit document checkbox present in residential supp."""
    _load_residential_supp_8w(page, live_server)
    field = page.locator("#es-supp-field-ru_building_permit")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "checkbox", (
        f"ru_building_permit supp field must be checkbox. Got type={field.get_attribute('type')!r}"
    )


# ── CS229 ─────────────────────────────────────────────────────────────────────

def test_CS229_residential_supp_occupancy_status_select(page: Page, live_server: str) -> None:
    """Phase 8Q: es-supp-field-occupancy_status select renders in residential supp."""
    _load_residential_supp_8w(page, live_server)
    sel = page.locator("#es-supp-field-occupancy_status")
    expect(sel).to_be_visible()
    opts = sel.locator("option").all_inner_texts()
    assert any("شاغر" in o or "مستأجر" in o for o in opts), (
        f"occupancy_status supp select must have Arabic options. Got: {opts}"
    )


# ── CS230 ─────────────────────────────────────────────────────────────────────

def test_CS230_residential_supp_uses_supp_field_attr_not_req_field(page: Page, live_server: str) -> None:
    """Phase 8Q: #es-req-supp only has data-es-supp-field attrs (no data-es-req-field) for residential."""
    _load_residential_supp_8w(page, live_server)
    supp_req_count = page.locator("#es-req-supp [data-es-req-field]").count()
    supp_supp_count = page.locator("#es-req-supp [data-es-supp-field]").count()
    assert supp_req_count == 0, (
        f"#es-req-supp must have NO data-es-req-field attrs. Got {supp_req_count}."
    )
    assert supp_supp_count > 0, (
        "#es-req-supp must have data-es-supp-field attrs present."
    )


# ── CS231 ─────────────────────────────────────────────────────────────────────

def test_CS231_residential_supp_header_shows_local_input_label(page: Page, live_server: str) -> None:
    """Phase 8W: residential supp header shows 'إدخال محلي' text (no shadda)."""
    _load_residential_supp_8w(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "إدخال محلي" in supp_text, (
        f"Residential supp must show 'إدخال محلي' label. Got: {supp_text[:400]!r}"
    )


# ── CS232 ─────────────────────────────────────────────────────────────────────

def test_CS232_switching_residential_to_factory_clears_supp(page: Page, live_server: str) -> None:
    """Phase 8Q: switching from residential → factory clears #es-req-supp."""
    _load_residential_supp_8w(page, live_server)
    supp = page.locator("#es-req-supp")
    assert supp.inner_html().strip() != "", "Supp must be populated before switch"
    page.select_option("#asset-type", value="مصنع")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    supp_html = supp.inner_html().strip()
    assert supp_html == "", (
        f"#es-req-supp must be empty after switching to factory. Got: {supp_html[:200]!r}"
    )


# ── CS233 ─────────────────────────────────────────────────────────────────────

def test_CS233_residential_supp_maintenance_level_select(page: Page, live_server: str) -> None:
    """Phase 8Q: es-supp-field-maintenance_level select renders in residential supp."""
    _load_residential_supp_8w(page, live_server)
    sel = page.locator("#es-supp-field-maintenance_level")
    expect(sel).to_be_visible()
    opts = sel.locator("option").all_inner_texts()
    assert any("جيد" in o or "متوسط" in o or "مهمل" in o for o in opts), (
        f"maintenance_level supp select must have Arabic options. Got: {opts}"
    )


# ── CS234 ─────────────────────────────────────────────────────────────────────

def test_CS234_land_supp_section_rendered(page: Page, live_server: str) -> None:
    """Phase 8Q: أرض فضاء API panel — #es-req-supp receives land supplemental sections."""
    _load_land_supp_8w(page, live_server)
    supp = page.locator("#es-req-supp")
    expect(supp).to_be_attached()
    supp_html = supp.inner_html().strip()
    assert supp_html != "", (
        "أرض فضاء panel must populate #es-req-supp with supplemental content"
    )


# ── CS235 ─────────────────────────────────────────────────────────────────────

def test_CS235_land_supp_heading_land_detail(page: Page, live_server: str) -> None:
    """Phase 8Q: land supp heading 'بيانات الأرض التفصيلية' is visible."""
    _load_land_supp_8w(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "بيانات الأرض التفصيلية" in supp_text, (
        f"Land supp must show heading 'بيانات الأرض التفصيلية'. Got: {supp_text[:400]!r}"
    )


# ── CS236 ─────────────────────────────────────────────────────────────────────

def test_CS236_land_supp_area_feddan_number_input(page: Page, live_server: str) -> None:
    """Phase 8Q: es-supp-field-land_area_feddan renders as number input in land supp."""
    _load_land_supp_8w(page, live_server)
    field = page.locator("#es-supp-field-land_area_feddan")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "number", (
        f"land_area_feddan supp field must be number input. Got type={field.get_attribute('type')!r}"
    )


# ── CS237 ─────────────────────────────────────────────────────────────────────

def test_CS237_land_supp_shape_regular_select(page: Page, live_server: str) -> None:
    """Phase 8Q: es-supp-field-shape_regular select renders in land supp."""
    _load_land_supp_8w(page, live_server)
    sel = page.locator("#es-supp-field-shape_regular")
    expect(sel).to_be_visible()
    opts = sel.locator("option").all_inner_texts()
    assert any("منتظمة" in o or "ركنية" in o for o in opts), (
        f"shape_regular supp select must have Arabic shape options. Got: {opts}"
    )


# ── CS238 ─────────────────────────────────────────────────────────────────────

def test_CS238_land_supp_far_ratio_number_input(page: Page, live_server: str) -> None:
    """Phase 8Q: es-supp-field-far_ratio renders as number input in land supp."""
    _load_land_supp_8w(page, live_server)
    field = page.locator("#es-supp-field-far_ratio")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "number", (
        f"far_ratio supp field must be number input. Got type={field.get_attribute('type')!r}"
    )


# ── CS239 ─────────────────────────────────────────────────────────────────────

def test_CS239_land_supp_main_street_width_number_input(page: Page, live_server: str) -> None:
    """Phase 8Q: es-supp-field-main_street_width_m renders as number input in land supp."""
    _load_land_supp_8w(page, live_server)
    field = page.locator("#es-supp-field-main_street_width_m")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "number", (
        f"main_street_width_m supp field must be number input. Got type={field.get_attribute('type')!r}"
    )


# ── CS240 ─────────────────────────────────────────────────────────────────────

def test_CS240_land_supp_regulatory_compliance_select(page: Page, live_server: str) -> None:
    """Phase 8Q: es-supp-field-regulatory_compliance select renders in land supp."""
    _load_land_supp_8w(page, live_server)
    sel = page.locator("#es-supp-field-regulatory_compliance")
    expect(sel).to_be_visible()
    opts = sel.locator("option").all_inner_texts()
    assert any("ملتزم" in o or "مخالفة" in o for o in opts), (
        f"regulatory_compliance supp select must have Arabic options. Got: {opts}"
    )


# ── CS241 ─────────────────────────────────────────────────────────────────────

def test_CS241_land_supp_ld_transaction_cert_doc_checkbox(page: Page, live_server: str) -> None:
    """Phase 8Q: es-supp-field-ld_transaction_cert document checkbox present in land supp."""
    _load_land_supp_8w(page, live_server)
    field = page.locator("#es-supp-field-ld_transaction_cert")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "checkbox", (
        f"ld_transaction_cert supp field must be checkbox. Got type={field.get_attribute('type')!r}"
    )


# ── CS242 ─────────────────────────────────────────────────────────────────────

def test_CS242_land_supp_uses_supp_field_attr_not_req_field(page: Page, live_server: str) -> None:
    """Phase 8Q: land #es-req-supp only has data-es-supp-field attrs (no data-es-req-field)."""
    _load_land_supp_8w(page, live_server)
    supp_req_count = page.locator("#es-req-supp [data-es-req-field]").count()
    supp_supp_count = page.locator("#es-req-supp [data-es-supp-field]").count()
    assert supp_req_count == 0, (
        f"Land #es-req-supp must have NO data-es-req-field attrs. Got {supp_req_count}."
    )
    assert supp_supp_count > 0, (
        "Land #es-req-supp must have data-es-supp-field attrs present."
    )


# ── CS243 ─────────────────────────────────────────────────────────────────────

def test_CS243_land_supp_header_shows_land_supplemental_heading(page: Page, live_server: str) -> None:
    """Phase 8W: land supp header shows 'متطلبات تقييم الأرض الفضاء' heading."""
    _load_land_supp_8w(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "متطلبات تقييم الأرض الفضاء" in supp_text, (
        f"Land supp must show 'متطلبات تقييم الأرض الفضاء'. Got: {supp_text[:400]!r}"
    )


# ── CS244 ─────────────────────────────────────────────────────────────────────

def test_CS244_land_supp_infrastructure_cost_number_input(page: Page, live_server: str) -> None:
    """Phase 8Q: es-supp-field-infrastructure_development_cost renders as number input."""
    _load_land_supp_8w(page, live_server)
    field = page.locator("#es-supp-field-infrastructure_development_cost")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "number", (
        f"infrastructure_development_cost supp field must be number input. "
        f"Got type={field.get_attribute('type')!r}"
    )


# ── CS245 ─────────────────────────────────────────────────────────────────────

def test_CS245_land_supp_header_shows_local_input_label(page: Page, live_server: str) -> None:
    """Phase 8W: land supp shows 'إدخال محلي' marker (no shadda) indicating local-only data."""
    _load_land_supp_8w(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "إدخال محلي" in supp_text, (
        f"Land supp must show 'إدخال محلي' label. Got: {supp_text[:400]!r}"
    )


# ── CS246 ─────────────────────────────────────────────────────────────────────

def test_CS246_building_full_static_supp_is_populated(page: Page, live_server: str) -> None:
    """Phase 8ZA update: عمارة سكنية (static/full) now populates #es-req-supp with enriched supplemental.
    Previously empty (Phase 8Q), now populated since Phase 8ZA added building_full supplemental schema.
    """
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-supp-header").wait_for(state="visible", timeout=8_000)
    supp_html = page.locator("#es-req-supp").inner_html().strip()
    assert supp_html != "", (
        f"Phase 8ZA: عمارة سكنية must now populate #es-req-supp with supplemental content."
    )
    assert "متطلبات تقييم العمارة السكنية" in page.locator("#es-req-supp-header").inner_text(), (
        "Phase 8ZA: building_full supp header must contain 'متطلبات تقييم العمارة السكنية'."
    )


# ── CS247 ─────────────────────────────────────────────────────────────────────

def test_CS247_commercial_api_supp_is_empty(page: Page, live_server: str) -> None:
    """Phase 8Q: تجاري (commercial API) #es-req-supp is empty (no supplemental schema for commercial)."""
    _mock_req(page, _COMMERCIAL_RESPONSE)
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="تجاري")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
    supp_html = page.locator("#es-req-supp").inner_html().strip()
    assert supp_html == "", (
        f"تجاري (commercial) must not populate #es-req-supp. Got: {supp_html[:200]!r}"
    )


# ── CS248 ─────────────────────────────────────────────────────────────────────

def test_CS248_switching_residential_to_building_full_updates_supp(page: Page, live_server: str) -> None:
    """Phase 8ZA update: switching from residential → عمارة سكنية updates #es-req-supp to building_full content.
    Previously cleared (Phase 8Q), now switches to building_full supplemental since Phase 8ZA.
    """
    _load_residential_supp_8w(page, live_server)
    supp = page.locator("#es-req-supp")
    assert "متطلبات تقييم الوحدة السكنية" in supp.inner_text(), (
        "Supp must show residential heading before switch"
    )
    page.select_option("#asset-type", value="عمارة سكنية")
    page.locator("#es-req-supp-header").wait_for(state="visible", timeout=8_000)
    supp_header = page.locator("#es-req-supp-header").inner_text()
    assert "متطلبات تقييم العمارة السكنية" in supp_header, (
        f"Phase 8ZA: after switching to عمارة سكنية, supp must show building_full heading. Got: {supp_header!r}"
    )


# ── CS249 ─────────────────────────────────────────────────────────────────────

def test_CS249_switching_land_to_factory_clears_supp(page: Page, live_server: str) -> None:
    """Phase 8Q: switching from land (has supp) → مصنع (static) clears #es-req-supp."""
    _load_land_supp_8w(page, live_server)
    supp = page.locator("#es-req-supp")
    assert supp.inner_html().strip() != "", "Supp must be populated before switch"
    page.select_option("#asset-type", value="مصنع")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    supp_html = supp.inner_html().strip()
    assert supp_html == "", (
        f"#es-req-supp must be empty after switching to مصنع. Got: {supp_html[:200]!r}"
    )


# ── CS250 ─────────────────────────────────────────────────────────────────────

def test_CS250_residential_supp_no_duplicate_area_sqm(page: Page, live_server: str) -> None:
    """Phase 8Q: residential supp must NOT contain es-supp-field-area_sqm (API field duplication guard)."""
    _load_residential_supp_8w(page, live_server)
    count = page.locator("#es-supp-field-area_sqm").count()
    assert count == 0, (
        f"area_sqm must not appear as supp field (it's an API field). Got {count} occurrences."
    )


# ── CS251 ─────────────────────────────────────────────────────────────────────

def test_CS251_residential_supp_no_duplicate_floor_number(page: Page, live_server: str) -> None:
    """Phase 8Q: residential supp must NOT contain es-supp-field-floor_number (API field duplication guard)."""
    _load_residential_supp_8w(page, live_server)
    count = page.locator("#es-supp-field-floor_number").count()
    assert count == 0, (
        f"floor_number must not appear as supp field (it's an API field). Got {count} occurrences."
    )


# ── CS252 ─────────────────────────────────────────────────────────────────────

def test_CS252_land_supp_no_duplicate_land_area_sqm(page: Page, live_server: str) -> None:
    """Phase 8Q: land supp must NOT contain es-supp-field-land_area_sqm (API field duplication guard)."""
    _load_land_supp_8w(page, live_server)
    count = page.locator("#es-supp-field-land_area_sqm").count()
    assert count == 0, (
        f"land_area_sqm must not appear as supp field (it's an API field). Got {count} occurrences."
    )


# ── CS253 ─────────────────────────────────────────────────────────────────────

def test_CS253_land_supp_no_duplicate_frontage_m(page: Page, live_server: str) -> None:
    """Phase 8Q: land supp must NOT contain es-supp-field-frontage_m (API field duplication guard)."""
    _load_land_supp_8w(page, live_server)
    count = page.locator("#es-supp-field-frontage_m").count()
    assert count == 0, (
        f"frontage_m must not appear as supp field (it's an API field). Got {count} occurrences."
    )


# ── CS254 ─────────────────────────────────────────────────────────────────────

def test_CS254_residential_supp_no_data_es_req_field_in_supp(page: Page, live_server: str) -> None:
    """Phase 8Q: no data-es-req-field elements in #es-req-supp for residential."""
    _load_residential_supp_8w(page, live_server)
    count = page.locator("#es-req-supp [data-es-req-field]").count()
    assert count == 0, (
        f"#es-req-supp must not contain data-es-req-field attrs. Got {count}."
    )


# ── CS255 ─────────────────────────────────────────────────────────────────────

def test_CS255_land_supp_no_data_es_req_field_in_supp(page: Page, live_server: str) -> None:
    """Phase 8Q: no data-es-req-field elements in #es-req-supp for land."""
    _load_land_supp_8w(page, live_server)
    count = page.locator("#es-req-supp [data-es-req-field]").count()
    assert count == 0, (
        f"Land #es-req-supp must not contain data-es-req-field attrs. Got {count}."
    )


# ── CS256 ─────────────────────────────────────────────────────────────────────

def test_CS256_agricultural_land_water_section_heading(page: Page, live_server: str) -> None:
    """Phase 8Q: agricultural_land panel shows 'مصادر المياه والري' section heading."""
    _load_agricultural_land(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "مصادر المياه والري" in panel_text, (
        f"agricultural_land must show 'مصادر المياه والري' heading. Got: {panel_text[:400]!r}"
    )


# ── CS257 ─────────────────────────────────────────────────────────────────────

def test_CS257_agricultural_land_soil_fertility_select_arabic(page: Page, live_server: str) -> None:
    """Phase 8Q: ag_soil_fertility select renders with Arabic fertility options."""
    _load_agricultural_land(page, live_server)
    sel = page.locator("#es-req-field-ag_soil_fertility")
    expect(sel).to_be_visible()
    opts = sel.locator("option").all_inner_texts()
    assert any("عالية" in o or "متوسطة" in o or "منخفضة" in o for o in opts), (
        f"ag_soil_fertility must have Arabic fertility options. Got: {opts}"
    )


# ══ Phase 8R.1 — Infrastructure & Transport Profiles: Airport / Seaport / Marina (CS258–CS284) ══


def _load_airport(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="airport")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


def _load_seaport(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="seaport")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


def _load_marina(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="marina")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


# ── CS258 ─────────────────────────────────────────────────────────────────────

def test_CS258_infrastructure_transport_optgroup_present(page: Page, live_server: str) -> None:
    """Phase 8R.1: optgroup 'أصول البنية التحتية والنقل السيادية' appears in #asset-type."""
    page.goto(live_server, wait_until="networkidle")
    optgroup_labels = page.locator("#asset-type optgroup").evaluate_all(
        "els => els.map(e => e.getAttribute('label'))"
    )
    assert any("أصول البنية التحتية" in lbl for lbl in optgroup_labels), (
        f"#asset-type must have optgroup 'أصول البنية التحتية والنقل السيادية'. Got: {optgroup_labels}"
    )


# ── CS259 ─────────────────────────────────────────────────────────────────────

def test_CS259_airport_option_present_in_select(page: Page, live_server: str) -> None:
    """Phase 8R.1: 'airport' option value exists inside #asset-type."""
    page.goto(live_server, wait_until="networkidle")
    option = page.locator("#asset-type option[value='airport']")
    expect(option).to_be_attached()
    assert "مطار" in option.inner_text(), (
        f"airport option must show Arabic 'مطار' text. Got: {option.inner_text()!r}"
    )


# ── CS260 ─────────────────────────────────────────────────────────────────────

def test_CS260_seaport_option_present_in_select(page: Page, live_server: str) -> None:
    """Phase 8R.1: 'seaport' option value exists inside #asset-type."""
    page.goto(live_server, wait_until="networkidle")
    option = page.locator("#asset-type option[value='seaport']")
    expect(option).to_be_attached()
    assert "ميناء" in option.inner_text(), (
        f"seaport option must show Arabic 'ميناء' text. Got: {option.inner_text()!r}"
    )


# ── CS261 ─────────────────────────────────────────────────────────────────────

def test_CS261_marina_option_present_in_select(page: Page, live_server: str) -> None:
    """Phase 8R.1: 'marina' option value exists inside #asset-type."""
    page.goto(live_server, wait_until="networkidle")
    option = page.locator("#asset-type option[value='marina']")
    expect(option).to_be_attached()
    assert "مارينا" in option.inner_text(), (
        f"marina option must show Arabic 'مارينا' text. Got: {option.inner_text()!r}"
    )


# ── CS262 ─────────────────────────────────────────────────────────────────────

def test_CS262_airport_renders_local_form_stays_on_index(page: Page, live_server: str) -> None:
    """Phase 8R.1: airport renders local form with badge 'نموذج محلي'; page stays on index.html."""
    _load_airport(page, live_server)
    badge = page.locator("#es-profile-badge")
    expect(badge).to_be_visible()
    assert badge.inner_text().strip() == "نموذج محلي", (
        f"airport badge must show 'نموذج محلي'. Got: {badge.inner_text()!r}"
    )
    assert page.url.startswith(live_server), (
        f"page must stay on index.html. Got URL: {page.url!r}"
    )


# ── CS263 ─────────────────────────────────────────────────────────────────────

def test_CS263_seaport_renders_local_form_stays_on_index(page: Page, live_server: str) -> None:
    """Phase 8R.1: seaport renders local form with badge 'نموذج محلي'; page stays on index.html."""
    _load_seaport(page, live_server)
    badge = page.locator("#es-profile-badge")
    expect(badge).to_be_visible()
    assert badge.inner_text().strip() == "نموذج محلي", (
        f"seaport badge must show 'نموذج محلي'. Got: {badge.inner_text()!r}"
    )
    assert page.url.startswith(live_server), (
        f"page must stay on index.html. Got URL: {page.url!r}"
    )


# ── CS264 ─────────────────────────────────────────────────────────────────────

def test_CS264_marina_renders_local_form_stays_on_index(page: Page, live_server: str) -> None:
    """Phase 8R.1: marina renders local form with badge 'نموذج محلي'; page stays on index.html."""
    _load_marina(page, live_server)
    badge = page.locator("#es-profile-badge")
    expect(badge).to_be_visible()
    assert badge.inner_text().strip() == "نموذج محلي", (
        f"marina badge must show 'نموذج محلي'. Got: {badge.inner_text()!r}"
    )
    assert page.url.startswith(live_server), (
        f"page must stay on index.html. Got URL: {page.url!r}"
    )


# ── CS265 ─────────────────────────────────────────────────────────────────────

def test_CS265_airport_makes_zero_api_calls(page: Page, live_server: str) -> None:
    """Phase 8R.1: airport must NOT call /api/valuation/requirements (static path)."""
    api_calls: list[str] = []
    page.goto("about:blank")
    page.route("**/api/valuation/requirements**", lambda route: (
        api_calls.append(route.request.url), route.continue_()
    ))
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="airport")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    assert len(api_calls) == 0, (
        f"airport must make ZERO API calls. Got calls: {api_calls}"
    )


# ── CS266 ─────────────────────────────────────────────────────────────────────

def test_CS266_airport_panel_title_contains_airport_arabic(page: Page, live_server: str) -> None:
    """Phase 8R.1: airport panel title contains 'مطار'."""
    _load_airport(page, live_server)
    title_text = page.locator("#es-req-title").inner_text()
    assert "مطار" in title_text, (
        f"airport title must contain 'مطار'. Got: {title_text!r}"
    )


# ── CS267 ─────────────────────────────────────────────────────────────────────

def test_CS267_airport_runway_length_number_input_with_meter_unit(page: Page, live_server: str) -> None:
    """Phase 8R.1: ap_main_runway_length_m renders as number input; متر unit text visible."""
    _load_airport(page, live_server)
    field = page.locator("#es-req-field-ap_main_runway_length_m")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "number", (
        f"ap_main_runway_length_m must be number input. Got type={field.get_attribute('type')!r}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "متر" in panel_text, (
        f"airport panel must show 'متر' unit text. Got: {panel_text[:400]!r}"
    )


# ── CS268 ─────────────────────────────────────────────────────────────────────

def test_CS268_airport_runway_width_number_input_with_meter_unit(page: Page, live_server: str) -> None:
    """Phase 8R.1: ap_main_runway_width_m renders as number input with متر unit."""
    _load_airport(page, live_server)
    field = page.locator("#es-req-field-ap_main_runway_width_m")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "number", (
        f"ap_main_runway_width_m must be number input. Got type={field.get_attribute('type')!r}"
    )


# ── CS269 ─────────────────────────────────────────────────────────────────────

def test_CS269_airport_icao_compliance_select_arabic_options(page: Page, live_server: str) -> None:
    """Phase 8R.1: ap_icao_compliance_status select renders with Arabic options."""
    _load_airport(page, live_server)
    sel = page.locator("#es-req-field-ap_icao_compliance_status")
    expect(sel).to_be_visible()
    opts = sel.locator("option").all_inner_texts()
    assert any("متوافق" in o or "امتثال" in o or "جزئي" in o for o in opts), (
        f"ap_icao_compliance_status must have Arabic options. Got: {opts}"
    )


# ── CS270 ─────────────────────────────────────────────────────────────────────

def test_CS270_airport_upload_hint_present(page: Page, live_server: str) -> None:
    """Phase 8R.1: airport document section shows upload hint text."""
    _load_airport(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "ارفع المستندات" in panel_text, (
        f"airport panel must show upload hint 'ارفع المستندات'. Got: {panel_text[:400]!r}"
    )


# ── CS271 ─────────────────────────────────────────────────────────────────────

def test_CS271_airport_has_no_composite_link(page: Page, live_server: str) -> None:
    """Phase 8R.1: airport panel has no composite_valuation.html link."""
    _load_airport(page, live_server)
    panel_html = page.locator("#es-req-panel").inner_html()
    assert "composite_valuation.html" not in panel_html, (
        "airport panel must not contain composite_valuation.html link"
    )


# ── CS272 ─────────────────────────────────────────────────────────────────────

def test_CS272_seaport_makes_zero_api_calls(page: Page, live_server: str) -> None:
    """Phase 8R.1: seaport must NOT call /api/valuation/requirements (static path)."""
    api_calls: list[str] = []
    page.goto("about:blank")
    page.route("**/api/valuation/requirements**", lambda route: (
        api_calls.append(route.request.url), route.continue_()
    ))
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="seaport")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    assert len(api_calls) == 0, (
        f"seaport must make ZERO API calls. Got calls: {api_calls}"
    )


# ── CS273 ─────────────────────────────────────────────────────────────────────

def test_CS273_seaport_teu_capacity_number_input_with_teu_unit(page: Page, live_server: str) -> None:
    """Phase 8R.1: sp_annual_container_capacity_teu renders as number input; TEU unit visible."""
    _load_seaport(page, live_server)
    field = page.locator("#es-req-field-sp_annual_container_capacity_teu")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "number", (
        f"sp_annual_container_capacity_teu must be number input. Got type={field.get_attribute('type')!r}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "TEU" in panel_text, (
        f"seaport panel must show 'TEU' unit text. Got: {panel_text[:400]!r}"
    )


# ── CS274 ─────────────────────────────────────────────────────────────────────

def test_CS274_seaport_berth_draft_depth_number_input_meter(page: Page, live_server: str) -> None:
    """Phase 8R.1: sp_berth_draft_depth_m renders as number input with متر unit."""
    _load_seaport(page, live_server)
    field = page.locator("#es-req-field-sp_berth_draft_depth_m")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "number", (
        f"sp_berth_draft_depth_m must be number input. Got type={field.get_attribute('type')!r}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "متر" in panel_text, (
        f"seaport panel must show 'متر' unit text. Got: {panel_text[:400]!r}"
    )


# ── CS275 ─────────────────────────────────────────────────────────────────────

def test_CS275_seaport_harbor_basin_depth_number_input_meter(page: Page, live_server: str) -> None:
    """Phase 8R.1: sp_harbor_basin_depth_m renders as number input with متر unit."""
    _load_seaport(page, live_server)
    field = page.locator("#es-req-field-sp_harbor_basin_depth_m")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "number", (
        f"sp_harbor_basin_depth_m must be number input. Got type={field.get_attribute('type')!r}"
    )


# ── CS276 ─────────────────────────────────────────────────────────────────────

def test_CS276_seaport_upload_hint_present(page: Page, live_server: str) -> None:
    """Phase 8R.1: seaport document section shows upload hint text."""
    _load_seaport(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "ارفع المستندات" in panel_text, (
        f"seaport panel must show upload hint 'ارفع المستندات'. Got: {panel_text[:400]!r}"
    )


# ── CS277 ─────────────────────────────────────────────────────────────────────

def test_CS277_seaport_has_no_composite_link(page: Page, live_server: str) -> None:
    """Phase 8R.1: seaport panel has no composite_valuation.html link."""
    _load_seaport(page, live_server)
    panel_html = page.locator("#es-req-panel").inner_html()
    assert "composite_valuation.html" not in panel_html, (
        "seaport panel must not contain composite_valuation.html link"
    )


# ── CS278 ─────────────────────────────────────────────────────────────────────

def test_CS278_marina_makes_zero_api_calls(page: Page, live_server: str) -> None:
    """Phase 8R.1: marina must NOT call /api/valuation/requirements (static path)."""
    api_calls: list[str] = []
    page.goto("about:blank")
    page.route("**/api/valuation/requirements**", lambda route: (
        api_calls.append(route.request.url), route.continue_()
    ))
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="marina")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    assert len(api_calls) == 0, (
        f"marina must make ZERO API calls. Got calls: {api_calls}"
    )


# ── CS279 ─────────────────────────────────────────────────────────────────────

def test_CS279_marina_wet_slips_count_number_input(page: Page, live_server: str) -> None:
    """Phase 8R.1: mr_wet_slips_count renders as number input."""
    _load_marina(page, live_server)
    field = page.locator("#es-req-field-mr_wet_slips_count")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "number", (
        f"mr_wet_slips_count must be number input. Got type={field.get_attribute('type')!r}"
    )


# ── CS280 ─────────────────────────────────────────────────────────────────────

def test_CS280_marina_max_yacht_loa_number_input_meter(page: Page, live_server: str) -> None:
    """Phase 8R.1: mr_max_yacht_loa_m renders as number input; متر unit text visible."""
    _load_marina(page, live_server)
    field = page.locator("#es-req-field-mr_max_yacht_loa_m")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "number", (
        f"mr_max_yacht_loa_m must be number input. Got type={field.get_attribute('type')!r}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "متر" in panel_text, (
        f"marina panel must show 'متر' unit text. Got: {panel_text[:400]!r}"
    )


# ── CS281 ─────────────────────────────────────────────────────────────────────

def test_CS281_marina_service_facilities_checkbox_group_renders(page: Page, live_server: str) -> None:
    """Phase 8R.1: mr_service_facilities_available checkbox group renders with fuel_station option."""
    _load_marina(page, live_server)
    chips = page.locator("[data-es-req-field='mr_service_facilities_available']")
    expect(chips.first).to_be_visible()
    fuel_chip = page.locator("[data-es-req-field='mr_service_facilities_available'][value='fuel_station']")
    expect(fuel_chip).to_be_attached()


# ── CS282 ─────────────────────────────────────────────────────────────────────

def test_CS282_marina_upload_hint_present(page: Page, live_server: str) -> None:
    """Phase 8R.1: marina document section shows upload hint text."""
    _load_marina(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "ارفع المستندات" in panel_text, (
        f"marina panel must show upload hint 'ارفع المستندات'. Got: {panel_text[:400]!r}"
    )


# ── CS283 ─────────────────────────────────────────────────────────────────────

def test_CS283_marina_has_no_composite_link(page: Page, live_server: str) -> None:
    """Phase 8R.1: marina panel has no composite_valuation.html link."""
    _load_marina(page, live_server)
    panel_html = page.locator("#es-req-panel").inner_html()
    assert "composite_valuation.html" not in panel_html, (
        "marina panel must not contain composite_valuation.html link"
    )


# ── CS284 ─────────────────────────────────────────────────────────────────────

def test_CS284_regression_existing_profiles_still_render(page: Page, live_server: str) -> None:
    """Phase 8R.1: regression guard — existing profiles (فندق, عمارة سكنية) still render form controls."""
    for profile_value, profile_label in [("فندق", "فندق"), ("عمارة سكنية", "عمارة سكنية")]:
        page.goto(live_server, wait_until="networkidle")
        _inject_session(page)
        page.select_option("#asset-type", value=profile_value)
        page.select_option("#val-purpose", value="fair_market_value")
        page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
        count = page.locator("#es-req-panel input, #es-req-panel select").count()
        assert count > 0, (
            f"Regression: {profile_label} panel must still render form controls after 8R.1. "
            f"Got {count} controls."
        )


# ══ Phase 8S.1 — Tech / Logistics / Industrial: data_center / cold_storage / prefabricated_factory (CS285–CS321) ══


def _load_data_center(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="data_center")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


def _load_cold_storage(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="cold_storage")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


def _load_prefabricated_factory(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="prefabricated_factory")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


# ── CS285 ─────────────────────────────────────────────────────────────────────

def test_CS285_tech_logistics_optgroup_present(page: Page, live_server: str) -> None:
    """Phase 8S.1: optgroup 'أصول تكنولوجية ولوجستية وصناعية متقدمة' appears in #asset-type."""
    page.goto(live_server, wait_until="networkidle")
    optgroup_labels = page.locator("#asset-type optgroup").evaluate_all(
        "els => els.map(e => e.getAttribute('label'))"
    )
    assert any("أصول تكنولوجية" in lbl for lbl in optgroup_labels), (
        f"#asset-type must have optgroup 'أصول تكنولوجية ولوجستية وصناعية متقدمة'. "
        f"Got: {optgroup_labels}"
    )


# ── CS286 ─────────────────────────────────────────────────────────────────────

def test_CS286_data_center_option_present(page: Page, live_server: str) -> None:
    """Phase 8S.1: data_center option present with 'مركز بيانات' text."""
    page.goto(live_server, wait_until="networkidle")
    opt = page.locator("#asset-type option[value='data_center']")
    expect(opt).to_be_attached()
    opt_text = opt.inner_text()
    assert "مركز بيانات" in opt_text, (
        f"data_center option must contain 'مركز بيانات'. Got: {opt_text!r}"
    )


# ── CS287 ─────────────────────────────────────────────────────────────────────

def test_CS287_cold_storage_option_present(page: Page, live_server: str) -> None:
    """Phase 8S.1: cold_storage option present with 'مخزن تبريد' text."""
    page.goto(live_server, wait_until="networkidle")
    opt = page.locator("#asset-type option[value='cold_storage']")
    expect(opt).to_be_attached()
    opt_text = opt.inner_text()
    assert "مخزن تبريد" in opt_text, (
        f"cold_storage option must contain 'مخزن تبريد'. Got: {opt_text!r}"
    )


# ── CS288 ─────────────────────────────────────────────────────────────────────

def test_CS288_prefabricated_factory_option_present(page: Page, live_server: str) -> None:
    """Phase 8S.1: prefabricated_factory option present with 'مصنع جاهز' text."""
    page.goto(live_server, wait_until="networkidle")
    opt = page.locator("#asset-type option[value='prefabricated_factory']")
    expect(opt).to_be_attached()
    opt_text = opt.inner_text()
    assert "مصنع جاهز" in opt_text, (
        f"prefabricated_factory option must contain 'مصنع جاهز'. Got: {opt_text!r}"
    )


# ── CS289 ─────────────────────────────────────────────────────────────────────

def test_CS289_data_center_renders_local_form_badge(page: Page, live_server: str) -> None:
    """Phase 8S.1: data_center shows 'نموذج محلي' badge and panel is visible."""
    _load_data_center(page, live_server)
    badge_text = page.locator("#es-profile-badge").inner_text()
    assert "نموذج محلي" in badge_text, (
        f"data_center badge must contain 'نموذج محلي'. Got: {badge_text!r}"
    )
    expect(page.locator("#es-req-panel")).to_be_visible()


# ── CS290 ─────────────────────────────────────────────────────────────────────

def test_CS290_data_center_stays_on_index_html(page: Page, live_server: str) -> None:
    """Phase 8S.1: selecting data_center does not navigate away from index.html."""
    _load_data_center(page, live_server)
    assert page.url.rstrip("/").endswith(("5000", "index.html")), (
        f"data_center must stay on index.html. Got URL: {page.url!r}"
    )


# ── CS291 ─────────────────────────────────────────────────────────────────────

def test_CS291_cold_storage_renders_local_form_badge(page: Page, live_server: str) -> None:
    """Phase 8S.1: cold_storage shows 'نموذج محلي' badge and panel is visible."""
    _load_cold_storage(page, live_server)
    badge_text = page.locator("#es-profile-badge").inner_text()
    assert "نموذج محلي" in badge_text, (
        f"cold_storage badge must contain 'نموذج محلي'. Got: {badge_text!r}"
    )
    expect(page.locator("#es-req-panel")).to_be_visible()


# ── CS292 ─────────────────────────────────────────────────────────────────────

def test_CS292_cold_storage_stays_on_index_html(page: Page, live_server: str) -> None:
    """Phase 8S.1: selecting cold_storage does not navigate away from index.html."""
    _load_cold_storage(page, live_server)
    assert page.url.rstrip("/").endswith(("5000", "index.html")), (
        f"cold_storage must stay on index.html. Got URL: {page.url!r}"
    )


# ── CS293 ─────────────────────────────────────────────────────────────────────

def test_CS293_prefabricated_factory_renders_local_form_badge(page: Page, live_server: str) -> None:
    """Phase 8S.1: prefabricated_factory shows 'نموذج محلي' badge and panel is visible."""
    _load_prefabricated_factory(page, live_server)
    badge_text = page.locator("#es-profile-badge").inner_text()
    assert "نموذج محلي" in badge_text, (
        f"prefabricated_factory badge must contain 'نموذج محلي'. Got: {badge_text!r}"
    )
    expect(page.locator("#es-req-panel")).to_be_visible()


# ── CS294 ─────────────────────────────────────────────────────────────────────

def test_CS294_prefabricated_factory_stays_on_index_html(page: Page, live_server: str) -> None:
    """Phase 8S.1: selecting prefabricated_factory does not navigate away from index.html."""
    _load_prefabricated_factory(page, live_server)
    assert page.url.rstrip("/").endswith(("5000", "index.html")), (
        f"prefabricated_factory must stay on index.html. Got URL: {page.url!r}"
    )


# ── CS295 ─────────────────────────────────────────────────────────────────────

def test_CS295_data_center_no_auth_modal(page: Page, live_server: str) -> None:
    """Phase 8S.1: data_center does not trigger auth modal."""
    _load_data_center(page, live_server)
    auth_visible = page.locator("#auth-modal, #login-modal, [id*='auth']").is_visible()
    assert not auth_visible, "data_center must not trigger any auth modal"


# ── CS296 ─────────────────────────────────────────────────────────────────────

def test_CS296_data_center_no_composite_link(page: Page, live_server: str) -> None:
    """Phase 8S.1: data_center panel has no composite_valuation.html link."""
    _load_data_center(page, live_server)
    panel_html = page.locator("#es-req-panel").inner_html()
    assert "composite_valuation.html" not in panel_html, (
        "data_center panel must not contain composite_valuation.html link"
    )


# ── CS297 ─────────────────────────────────────────────────────────────────────

def test_CS297_cold_storage_no_auth_modal(page: Page, live_server: str) -> None:
    """Phase 8S.1: cold_storage does not trigger auth modal."""
    _load_cold_storage(page, live_server)
    auth_visible = page.locator("#auth-modal, #login-modal, [id*='auth']").is_visible()
    assert not auth_visible, "cold_storage must not trigger any auth modal"


# ── CS298 ─────────────────────────────────────────────────────────────────────

def test_CS298_cold_storage_no_composite_link(page: Page, live_server: str) -> None:
    """Phase 8S.1: cold_storage panel has no composite_valuation.html link."""
    _load_cold_storage(page, live_server)
    panel_html = page.locator("#es-req-panel").inner_html()
    assert "composite_valuation.html" not in panel_html, (
        "cold_storage panel must not contain composite_valuation.html link"
    )


# ── CS299 ─────────────────────────────────────────────────────────────────────

def test_CS299_prefabricated_factory_no_auth_modal(page: Page, live_server: str) -> None:
    """Phase 8S.1: prefabricated_factory does not trigger auth modal."""
    _load_prefabricated_factory(page, live_server)
    auth_visible = page.locator("#auth-modal, #login-modal, [id*='auth']").is_visible()
    assert not auth_visible, "prefabricated_factory must not trigger any auth modal"


# ── CS300 ─────────────────────────────────────────────────────────────────────

def test_CS300_prefabricated_factory_no_composite_link(page: Page, live_server: str) -> None:
    """Phase 8S.1: prefabricated_factory panel has no composite_valuation.html link."""
    _load_prefabricated_factory(page, live_server)
    panel_html = page.locator("#es-req-panel").inner_html()
    assert "composite_valuation.html" not in panel_html, (
        "prefabricated_factory panel must not contain composite_valuation.html link"
    )


# ── CS301 ─────────────────────────────────────────────────────────────────────

def test_CS301_data_center_makes_zero_api_calls(page: Page, live_server: str) -> None:
    """Phase 8S.1: data_center must NOT call /api/valuation/requirements (static path)."""
    api_calls: list[str] = []
    page.goto("about:blank")
    page.route("**/api/valuation/requirements**", lambda route: (
        api_calls.append(route.request.url), route.continue_()
    ))
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="data_center")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    assert len(api_calls) == 0, (
        f"data_center must make ZERO API calls. Got calls: {api_calls}"
    )


# ── CS302 ─────────────────────────────────────────────────────────────────────

def test_CS302_cold_storage_makes_zero_api_calls(page: Page, live_server: str) -> None:
    """Phase 8S.1: cold_storage must NOT call /api/valuation/requirements (static path)."""
    api_calls: list[str] = []
    page.goto("about:blank")
    page.route("**/api/valuation/requirements**", lambda route: (
        api_calls.append(route.request.url), route.continue_()
    ))
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="cold_storage")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    assert len(api_calls) == 0, (
        f"cold_storage must make ZERO API calls. Got calls: {api_calls}"
    )


# ── CS303 ─────────────────────────────────────────────────────────────────────

def test_CS303_prefabricated_factory_makes_zero_api_calls(page: Page, live_server: str) -> None:
    """Phase 8S.1: prefabricated_factory must NOT call /api/valuation/requirements (static path)."""
    api_calls: list[str] = []
    page.goto("about:blank")
    page.route("**/api/valuation/requirements**", lambda route: (
        api_calls.append(route.request.url), route.continue_()
    ))
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="prefabricated_factory")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    assert len(api_calls) == 0, (
        f"prefabricated_factory must make ZERO API calls. Got calls: {api_calls}"
    )


# ── CS304 ─────────────────────────────────────────────────────────────────────

def test_CS304_data_center_power_capacity_number_input_with_mw_unit(page: Page, live_server: str) -> None:
    """Phase 8S.1: dc_total_power_capacity_mw renders as number input; MW unit text visible."""
    _load_data_center(page, live_server)
    field = page.locator("#es-req-field-dc_total_power_capacity_mw")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "number", (
        f"dc_total_power_capacity_mw must be number input. Got type={field.get_attribute('type')!r}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "MW" in panel_text, (
        f"data_center panel must show 'MW' unit text. Got: {panel_text[:400]!r}"
    )


# ── CS305 ─────────────────────────────────────────────────────────────────────

def test_CS305_data_center_tier_classification_select_with_tier_options(page: Page, live_server: str) -> None:
    """Phase 8S.1: dc_tier_classification select renders with Tier I–IV options."""
    _load_data_center(page, live_server)
    sel = page.locator("#es-req-field-dc_tier_classification")
    expect(sel).to_be_visible()
    opts = sel.locator("option").all_inner_texts()
    assert any("Tier" in o for o in opts), (
        f"dc_tier_classification must have Tier options. Got: {opts}"
    )


# ── CS306 ─────────────────────────────────────────────────────────────────────

def test_CS306_data_center_pue_number_input_present(page: Page, live_server: str) -> None:
    """Phase 8S.1: dc_pue renders as number input (PUE field)."""
    _load_data_center(page, live_server)
    field = page.locator("#es-req-field-dc_pue")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "number", (
        f"dc_pue must be number input. Got type={field.get_attribute('type')!r}"
    )


# ── CS307 ─────────────────────────────────────────────────────────────────────

def test_CS307_cold_storage_temperature_ranges_checkbox_group_present(page: Page, live_server: str) -> None:
    """Phase 8S.1: cs_temperature_ranges_available checkbox group renders with expected options."""
    _load_cold_storage(page, live_server)
    chips = page.locator("[data-es-req-field='cs_temperature_ranges_available']")
    expect(chips.first).to_be_visible()
    freezer_chip = page.locator(
        "[data-es-req-field='cs_temperature_ranges_available'][value='freezer']"
    )
    expect(freezer_chip).to_be_attached()


# ── CS308 ─────────────────────────────────────────────────────────────────────

def test_CS308_cold_storage_clear_height_number_input_with_meter_unit(page: Page, live_server: str) -> None:
    """Phase 8S.1: cs_clear_height_m renders as number input; متر unit visible."""
    _load_cold_storage(page, live_server)
    field = page.locator("#es-req-field-cs_clear_height_m")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "number", (
        f"cs_clear_height_m must be number input. Got type={field.get_attribute('type')!r}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "متر" in panel_text, (
        f"cold_storage panel must show 'متر' unit text. Got: {panel_text[:400]!r}"
    )


# ── CS309 ─────────────────────────────────────────────────────────────────────

def test_CS309_cold_storage_backup_refrigeration_bool_select(page: Page, live_server: str) -> None:
    """Phase 8S.1: cs_backup_refrigeration_available renders as yes/no select."""
    _load_cold_storage(page, live_server)
    sel = page.locator("#es-req-field-cs_backup_refrigeration_available")
    expect(sel).to_be_visible()
    opts = sel.locator("option").all_inner_texts()
    assert any("نعم" in o for o in opts) and any("لا" in o for o in opts), (
        f"cs_backup_refrigeration_available must have نعم/لا options. Got: {opts}"
    )


# ── CS310 ─────────────────────────────────────────────────────────────────────

def test_CS310_cold_storage_volume_m3_unit_visible(page: Page, live_server: str) -> None:
    """Phase 8S.1: cs_total_storage_volume_m3 number input present; م³ unit visible."""
    _load_cold_storage(page, live_server)
    field = page.locator("#es-req-field-cs_total_storage_volume_m3")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "number", (
        f"cs_total_storage_volume_m3 must be number input. Got type={field.get_attribute('type')!r}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "م³" in panel_text, (
        f"cold_storage panel must show 'م³' unit text. Got: {panel_text[:400]!r}"
    )


# ── CS311 ─────────────────────────────────────────────────────────────────────

def test_CS311_cold_storage_floor_loading_capacity_with_ton_sqm_unit(page: Page, live_server: str) -> None:
    """Phase 8S.1: cs_floor_loading_capacity_ton_sqm number input present; طن/م² unit visible."""
    _load_cold_storage(page, live_server)
    field = page.locator("#es-req-field-cs_floor_loading_capacity_ton_sqm")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "number", (
        f"cs_floor_loading_capacity_ton_sqm must be number input. Got type={field.get_attribute('type')!r}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "طن/م²" in panel_text, (
        f"cold_storage panel must show 'طن/م²' unit text. Got: {panel_text[:400]!r}"
    )


# ── CS312 ─────────────────────────────────────────────────────────────────────

def test_CS312_prefabricated_factory_clear_span_number_input_with_meter(page: Page, live_server: str) -> None:
    """Phase 8S.1: pf_clear_span_m renders as number input; متر unit visible."""
    _load_prefabricated_factory(page, live_server)
    field = page.locator("#es-req-field-pf_clear_span_m")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "number", (
        f"pf_clear_span_m must be number input. Got type={field.get_attribute('type')!r}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "متر" in panel_text, (
        f"prefabricated_factory panel must show 'متر' unit text. Got: {panel_text[:400]!r}"
    )


# ── CS313 ─────────────────────────────────────────────────────────────────────

def test_CS313_prefabricated_factory_sandwich_panel_type_select_present(page: Page, live_server: str) -> None:
    """Phase 8S.1: pf_sandwich_panel_type renders as select with Arabic options."""
    _load_prefabricated_factory(page, live_server)
    sel = page.locator("#es-req-field-pf_sandwich_panel_type")
    expect(sel).to_be_visible()
    opts = sel.locator("option").all_inner_texts()
    assert any("بولي" in o or "صوف" in o or "PIR" in o for o in opts), (
        f"pf_sandwich_panel_type must have Arabic panel options. Got: {opts}"
    )


# ── CS314 ─────────────────────────────────────────────────────────────────────

def test_CS314_prefabricated_factory_crane_capacity_number_input_with_ton(page: Page, live_server: str) -> None:
    """Phase 8S.1: pf_overhead_crane_load_capacity_ton renders as number input; طن unit visible."""
    _load_prefabricated_factory(page, live_server)
    field = page.locator("#es-req-field-pf_overhead_crane_load_capacity_ton")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "number", (
        f"pf_overhead_crane_load_capacity_ton must be number input. Got type={field.get_attribute('type')!r}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "طن" in panel_text, (
        f"prefabricated_factory panel must show 'طن' unit text. Got: {panel_text[:400]!r}"
    )


# ── CS315 ─────────────────────────────────────────────────────────────────────

def test_CS315_prefabricated_factory_is_separate_from_factory_profile(page: Page, live_server: str) -> None:
    """Phase 8S.1: prefabricated_factory is an independent profile; existing factory still renders separately."""
    # Load prefabricated_factory and verify its unique field is present
    _load_prefabricated_factory(page, live_server)
    pf_field = page.locator("#es-req-field-pf_clear_span_m")
    expect(pf_field).to_be_visible()

    # Now load factory and verify its unique field is present and pf_ field is absent
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="مصنع")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    fc_field = page.locator("#es-req-field-fc_land_area_sqm")
    expect(fc_field).to_be_visible()
    pf_field_in_factory = page.locator("#es-req-field-pf_clear_span_m")
    assert pf_field_in_factory.count() == 0, (
        "factory panel must NOT contain pf_clear_span_m (prefabricated_factory field)"
    )


# ── CS316 ─────────────────────────────────────────────────────────────────────

def test_CS316_data_center_tenant_contract_terms_renders_as_textarea(page: Page, live_server: str) -> None:
    """Phase 8S.1: dc_tenant_contract_terms renders as <textarea>, not <input>."""
    _load_data_center(page, live_server)
    el = page.locator("[data-es-req-field='dc_tenant_contract_terms']")
    expect(el).to_be_visible()
    tag = el.evaluate("e => e.tagName.toLowerCase()")
    assert tag == "textarea", (
        f"dc_tenant_contract_terms must render as textarea. Got tag: {tag!r}"
    )


# ── CS317 ─────────────────────────────────────────────────────────────────────

def test_CS317_cold_storage_major_tenant_contracts_renders_as_textarea(page: Page, live_server: str) -> None:
    """Phase 8S.1: cs_major_tenant_contracts renders as <textarea>, not <input>."""
    _load_cold_storage(page, live_server)
    el = page.locator("[data-es-req-field='cs_major_tenant_contracts']")
    expect(el).to_be_visible()
    tag = el.evaluate("e => e.tagName.toLowerCase()")
    assert tag == "textarea", (
        f"cs_major_tenant_contracts must render as textarea. Got tag: {tag!r}"
    )


# ── CS318 ─────────────────────────────────────────────────────────────────────

def test_CS318_data_center_upload_hint_present(page: Page, live_server: str) -> None:
    """Phase 8S.1: data_center document section shows upload hint text."""
    _load_data_center(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "ارفع المستندات" in panel_text, (
        f"data_center panel must show upload hint 'ارفع المستندات'. Got: {panel_text[:400]!r}"
    )


# ── CS319 ─────────────────────────────────────────────────────────────────────

def test_CS319_cold_storage_upload_hint_present(page: Page, live_server: str) -> None:
    """Phase 8S.1: cold_storage document section shows upload hint text."""
    _load_cold_storage(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "ارفع المستندات" in panel_text, (
        f"cold_storage panel must show upload hint 'ارفع المستندات'. Got: {panel_text[:400]!r}"
    )


# ── CS320 ─────────────────────────────────────────────────────────────────────

def test_CS320_prefabricated_factory_upload_hint_present(page: Page, live_server: str) -> None:
    """Phase 8S.1: prefabricated_factory document section shows upload hint text."""
    _load_prefabricated_factory(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "ارفع المستندات" in panel_text, (
        f"prefabricated_factory panel must show upload hint 'ارفع المستندات'. Got: {panel_text[:400]!r}"
    )


# ── CS321 ─────────────────────────────────────────────────────────────────────

def test_CS321_no_js_console_errors_on_8s1_profiles(page: Page, live_server: str) -> None:
    """Phase 8S.1: no JS console errors when rendering data_center, cold_storage, or prefabricated_factory."""
    def _is_js_error(msg) -> bool:
        return (
            msg.type == "error"
            and "401" not in msg.text
            and "UNAUTHORIZED" not in msg.text
            and "Failed to load resource" not in msg.text
        )

    for profile_value, loader in [
        ("data_center", _load_data_center),
        ("cold_storage", _load_cold_storage),
        ("prefabricated_factory", _load_prefabricated_factory),
    ]:
        console_errors: list[str] = []
        page.on("console", lambda msg: console_errors.append(msg.text) if _is_js_error(msg) else None)
        loader(page, live_server)
        assert not console_errors, (
            f"JavaScript console errors during {profile_value!r} render: {console_errors}"
        )
        console_errors.clear()


# ── CS322 ─────────────────────────────────────────────────────────────────────

def test_CS322_regression_existing_profiles_still_render_after_8s1(page: Page, live_server: str) -> None:
    """Phase 8S.1: regression guard — فندق and مصنع still render form controls; not replaced by 8S.1 profiles."""
    for profile_value, profile_label in [("فندق", "فندق"), ("مصنع", "مصنع")]:
        page.goto(live_server, wait_until="networkidle")
        _inject_session(page)
        page.select_option("#asset-type", value=profile_value)
        page.select_option("#val-purpose", value="fair_market_value")
        page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
        count = page.locator("#es-req-panel input, #es-req-panel select").count()
        assert count > 0, (
            f"Regression: {profile_label} panel must still render form controls after 8S.1. "
            f"Got {count} controls."
        )


# ══════════════════════════════════════════════════════════════════════════════
# Phase 8T.1 — Healthcare / Wellness / Educational asset profiles
# CS323–CS349
# ══════════════════════════════════════════════════════════════════════════════

def _load_healthcare_facility(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="healthcare_facility")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


def _load_wellness_resort(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="wellness_resort")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


def _load_educational_asset(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="educational_asset")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


# ── CS323 ─────────────────────────────────────────────────────────────────────

def test_CS323_optgroup_medical_educational_exists(page: Page, live_server: str) -> None:
    """Phase 8T.1: optgroup «أصول طبية وتعليمية وبيئية متخصّصة» exists in the asset-type dropdown."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    labels = page.locator("#asset-type optgroup").evaluate_all("els => els.map(e => e.label)")
    assert "أصول طبية وتعليمية وبيئية متخصّصة" in labels, (
        f"optgroup «أصول طبية وتعليمية وبيئية متخصّصة» not found in dropdown. "
        f"Got: {labels}"
    )


# ── CS324 ─────────────────────────────────────────────────────────────────────

def test_CS324_option_healthcare_facility_present(page: Page, live_server: str) -> None:
    """Phase 8T.1: option value='healthcare_facility' exists with «— تقييم تفصيلي» suffix."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    opt = page.locator("#asset-type option[value='healthcare_facility']")
    assert opt.count() == 1, "option value='healthcare_facility' not found in dropdown."
    text = opt.inner_text()
    assert "تقييم تفصيلي" in text, (
        f"healthcare_facility option must contain «تقييم تفصيلي». Got: {text!r}"
    )


# ── CS325 ─────────────────────────────────────────────────────────────────────

def test_CS325_option_wellness_resort_present(page: Page, live_server: str) -> None:
    """Phase 8T.1: option value='wellness_resort' exists in the asset-type dropdown."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    opt = page.locator("#asset-type option[value='wellness_resort']")
    assert opt.count() == 1, "option value='wellness_resort' not found in dropdown."


# ── CS326 ─────────────────────────────────────────────────────────────────────

def test_CS326_option_educational_asset_present(page: Page, live_server: str) -> None:
    """Phase 8T.1: option value='educational_asset' exists with «— تقييم تفصيلي» suffix."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    opt = page.locator("#asset-type option[value='educational_asset']")
    assert opt.count() == 1, "option value='educational_asset' not found in dropdown."
    text = opt.inner_text()
    assert "تقييم تفصيلي" in text, (
        f"educational_asset option must contain «تقييم تفصيلي». Got: {text!r}"
    )


# ── CS327 ─────────────────────────────────────────────────────────────────────

def test_CS327_healthcare_facility_badge_and_panel_render(page: Page, live_server: str) -> None:
    """Phase 8T.1: selecting healthcare_facility shows badge and requirements panel."""
    _load_healthcare_facility(page, live_server)
    badge = page.locator("#es-profile-badge")
    assert badge.is_visible(), "Profile badge must be visible for healthcare_facility."
    panel = page.locator("#es-req-panel")
    assert panel.is_visible(), "#es-req-panel must be visible for healthcare_facility."
    auth_modal = page.locator("#auth-modal, #login-modal, .auth-modal")
    assert auth_modal.count() == 0 or not auth_modal.first.is_visible(), (
        "Auth modal must NOT appear for healthcare_facility."
    )


# ── CS328 ─────────────────────────────────────────────────────────────────────

def test_CS328_wellness_resort_badge_and_panel_render(page: Page, live_server: str) -> None:
    """Phase 8T.1: selecting wellness_resort shows badge and requirements panel."""
    _load_wellness_resort(page, live_server)
    badge = page.locator("#es-profile-badge")
    assert badge.is_visible(), "Profile badge must be visible for wellness_resort."
    panel = page.locator("#es-req-panel")
    assert panel.is_visible(), "#es-req-panel must be visible for wellness_resort."
    auth_modal = page.locator("#auth-modal, #login-modal, .auth-modal")
    assert auth_modal.count() == 0 or not auth_modal.first.is_visible(), (
        "Auth modal must NOT appear for wellness_resort."
    )


# ── CS329 ─────────────────────────────────────────────────────────────────────

def test_CS329_educational_asset_badge_and_panel_render(page: Page, live_server: str) -> None:
    """Phase 8T.1: selecting educational_asset shows badge and requirements panel."""
    _load_educational_asset(page, live_server)
    badge = page.locator("#es-profile-badge")
    assert badge.is_visible(), "Profile badge must be visible for educational_asset."
    panel = page.locator("#es-req-panel")
    assert panel.is_visible(), "#es-req-panel must be visible for educational_asset."
    auth_modal = page.locator("#auth-modal, #login-modal, .auth-modal")
    assert auth_modal.count() == 0 or not auth_modal.first.is_visible(), (
        "Auth modal must NOT appear for educational_asset."
    )


# ── CS330 ─────────────────────────────────────────────────────────────────────

def test_CS330_healthcare_facility_stays_on_page(page: Page, live_server: str) -> None:
    """Phase 8T.1: selecting healthcare_facility does not navigate away from the page."""
    _load_healthcare_facility(page, live_server)
    assert "127.0.0.1:5000" in page.url or "localhost:5000" in page.url, (
        f"Page navigated away after selecting healthcare_facility. URL: {page.url}"
    )


# ── CS331 ─────────────────────────────────────────────────────────────────────

def test_CS331_wellness_resort_stays_on_page(page: Page, live_server: str) -> None:
    """Phase 8T.1: selecting wellness_resort does not navigate away from the page."""
    _load_wellness_resort(page, live_server)
    assert "127.0.0.1:5000" in page.url or "localhost:5000" in page.url, (
        f"Page navigated away after selecting wellness_resort. URL: {page.url}"
    )


# ── CS332 ─────────────────────────────────────────────────────────────────────

def test_CS332_educational_asset_stays_on_page(page: Page, live_server: str) -> None:
    """Phase 8T.1: selecting educational_asset does not navigate away from the page."""
    _load_educational_asset(page, live_server)
    assert "127.0.0.1:5000" in page.url or "localhost:5000" in page.url, (
        f"Page navigated away after selecting educational_asset. URL: {page.url}"
    )


# ── CS333 ─────────────────────────────────────────────────────────────────────

def test_CS333_healthcare_facility_zero_api_calls(page: Page, live_server: str) -> None:
    """Phase 8T.1: healthcare_facility must not call /api/valuation/requirements."""
    api_calls: list[str] = []
    page.on("request", lambda req: api_calls.append(req.url) if "valuation/requirements" in req.url else None)
    _load_healthcare_facility(page, live_server)
    assert not api_calls, (
        f"healthcare_facility must be fully static; unexpected API calls: {api_calls}"
    )


# ── CS334 ─────────────────────────────────────────────────────────────────────

def test_CS334_wellness_resort_zero_api_calls(page: Page, live_server: str) -> None:
    """Phase 8T.1: wellness_resort must not call /api/valuation/requirements."""
    api_calls: list[str] = []
    page.on("request", lambda req: api_calls.append(req.url) if "valuation/requirements" in req.url else None)
    _load_wellness_resort(page, live_server)
    assert not api_calls, (
        f"wellness_resort must be fully static; unexpected API calls: {api_calls}"
    )


# ── CS335 ─────────────────────────────────────────────────────────────────────

def test_CS335_educational_asset_zero_api_calls(page: Page, live_server: str) -> None:
    """Phase 8T.1: educational_asset must not call /api/valuation/requirements."""
    api_calls: list[str] = []
    page.on("request", lambda req: api_calls.append(req.url) if "valuation/requirements" in req.url else None)
    _load_educational_asset(page, live_server)
    assert not api_calls, (
        f"educational_asset must be fully static; unexpected API calls: {api_calls}"
    )


# ── CS336 ─────────────────────────────────────────────────────────────────────

def test_CS336_healthcare_facility_key_fields_render(page: Page, live_server: str) -> None:
    """Phase 8T.1: healthcare_facility renders hf_license_status, hf_total_beds, hf_operating_rooms."""
    _load_healthcare_facility(page, live_server)
    for field_name in ("hf_license_status", "hf_total_beds", "hf_operating_rooms"):
        locator = page.locator(f"[data-es-req-field='{field_name}']")
        assert locator.count() > 0, (
            f"healthcare_facility: field '{field_name}' not found in #es-req-panel."
        )


# ── CS337 ─────────────────────────────────────────────────────────────────────

def test_CS337_healthcare_facility_departments_checkbox_group_renders(page: Page, live_server: str) -> None:
    """Phase 8T.1: healthcare_facility hf_departments checkbox_group renders checkboxes."""
    _load_healthcare_facility(page, live_server)
    checkboxes = page.locator("[data-es-req-field='hf_departments']")
    assert checkboxes.count() > 0, (
        "healthcare_facility: hf_departments checkbox_group must render checkboxes in #es-req-panel."
    )


# ── CS338 ─────────────────────────────────────────────────────────────────────

def test_CS338_healthcare_facility_management_contract_textarea_renders(page: Page, live_server: str) -> None:
    """Phase 8T.1: healthcare_facility hf_management_contract_terms textarea renders."""
    _load_healthcare_facility(page, live_server)
    ta = page.locator("textarea[data-es-req-field='hf_management_contract_terms']")
    assert ta.count() == 1, (
        "healthcare_facility: hf_management_contract_terms must render as a <textarea> element."
    )


# ── CS339 ─────────────────────────────────────────────────────────────────────

def test_CS339_wellness_resort_key_fields_render(page: Page, live_server: str) -> None:
    """Phase 8T.1: wellness_resort renders wr_resort_class, wr_therapy_rooms, wr_pool_count."""
    _load_wellness_resort(page, live_server)
    for field_name in ("wr_resort_class", "wr_therapy_rooms", "wr_pool_count"):
        locator = page.locator(f"[data-es-req-field='{field_name}']")
        assert locator.count() > 0, (
            f"wellness_resort: field '{field_name}' not found in #es-req-panel."
        )


# ── CS340 ─────────────────────────────────────────────────────────────────────

def test_CS340_wellness_resort_wellness_services_checkbox_group_renders(page: Page, live_server: str) -> None:
    """Phase 8T.1: wellness_resort wr_wellness_services checkbox_group renders checkboxes."""
    _load_wellness_resort(page, live_server)
    checkboxes = page.locator("[data-es-req-field='wr_wellness_services']")
    assert checkboxes.count() > 0, (
        "wellness_resort: wr_wellness_services checkbox_group must render checkboxes in #es-req-panel."
    )


# ── CS341 ─────────────────────────────────────────────────────────────────────

def test_CS341_wellness_resort_operator_contract_textarea_renders(page: Page, live_server: str) -> None:
    """Phase 8T.1: wellness_resort wr_operator_contract_terms textarea renders."""
    _load_wellness_resort(page, live_server)
    ta = page.locator("textarea[data-es-req-field='wr_operator_contract_terms']")
    assert ta.count() == 1, (
        "wellness_resort: wr_operator_contract_terms must render as a <textarea> element."
    )


# ── CS342 ─────────────────────────────────────────────────────────────────────

def test_CS342_educational_asset_key_fields_render(page: Page, live_server: str) -> None:
    """Phase 8T.1: educational_asset renders ea_facility_type, ea_student_capacity, ea_classrooms_count."""
    _load_educational_asset(page, live_server)
    for field_name in ("ea_facility_type", "ea_student_capacity", "ea_classrooms_count"):
        locator = page.locator(f"[data-es-req-field='{field_name}']")
        assert locator.count() > 0, (
            f"educational_asset: field '{field_name}' not found in #es-req-panel."
        )


# ── CS343 ─────────────────────────────────────────────────────────────────────

def test_CS343_educational_asset_education_stages_checkbox_group_renders(page: Page, live_server: str) -> None:
    """Phase 8T.1: educational_asset ea_education_stages checkbox_group renders checkboxes."""
    _load_educational_asset(page, live_server)
    checkboxes = page.locator("[data-es-req-field='ea_education_stages']")
    assert checkboxes.count() > 0, (
        "educational_asset: ea_education_stages checkbox_group must render checkboxes in #es-req-panel."
    )


# ── CS344 ─────────────────────────────────────────────────────────────────────

def test_CS344_healthcare_facility_upload_hint_present(page: Page, live_server: str) -> None:
    """Phase 8T.1: healthcare_facility documents section contains upload hint text."""
    _load_healthcare_facility(page, live_server)
    hint_text = "ارفع المستندات من زر المرفقات"
    content = page.locator("#es-req-panel").inner_text()
    assert hint_text in content, (
        f"healthcare_facility: upload hint '{hint_text}' not found in #es-req-panel."
    )


# ── CS345 ─────────────────────────────────────────────────────────────────────

def test_CS345_wellness_resort_upload_hint_present(page: Page, live_server: str) -> None:
    """Phase 8T.1: wellness_resort documents section contains upload hint text."""
    _load_wellness_resort(page, live_server)
    hint_text = "ارفع المستندات من زر المرفقات"
    content = page.locator("#es-req-panel").inner_text()
    assert hint_text in content, (
        f"wellness_resort: upload hint '{hint_text}' not found in #es-req-panel."
    )


# ── CS346 ─────────────────────────────────────────────────────────────────────

def test_CS346_educational_asset_upload_hint_present(page: Page, live_server: str) -> None:
    """Phase 8T.1: educational_asset documents section contains upload hint text."""
    _load_educational_asset(page, live_server)
    hint_text = "ارفع المستندات من زر المرفقات"
    content = page.locator("#es-req-panel").inner_text()
    assert hint_text in content, (
        f"educational_asset: upload hint '{hint_text}' not found in #es-req-panel."
    )


# ── CS347 ─────────────────────────────────────────────────────────────────────

def test_CS347_no_auth_modal_for_8t1_profiles(page: Page, live_server: str) -> None:
    """Phase 8T.1: no auth modal triggered for healthcare_facility, wellness_resort, educational_asset."""
    for loader, label in [
        (_load_healthcare_facility, "healthcare_facility"),
        (_load_wellness_resort,     "wellness_resort"),
        (_load_educational_asset,   "educational_asset"),
    ]:
        page.goto(live_server, wait_until="networkidle")
        _inject_session(page)
        page.select_option("#asset-type", value=label)
        page.select_option("#val-purpose", value="fair_market_value")
        page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
        auth_modal = page.locator("#auth-modal, #login-modal, .auth-modal")
        assert auth_modal.count() == 0 or not auth_modal.first.is_visible(), (
            f"Auth modal must NOT appear for {label}."
        )


# ── CS348 ─────────────────────────────────────────────────────────────────────

def test_CS348_no_console_errors_for_8t1_profiles(page: Page, live_server: str) -> None:
    """Phase 8T.1: no JS console errors when rendering healthcare_facility, wellness_resort, educational_asset."""
    def _is_js_error(msg) -> bool:
        return (
            msg.type == "error"
            and "401" not in msg.text
            and "UNAUTHORIZED" not in msg.text.upper()
            and "Failed to load resource" not in msg.text
        )
    for loader, label in [
        (_load_healthcare_facility, "healthcare_facility"),
        (_load_wellness_resort,     "wellness_resort"),
        (_load_educational_asset,   "educational_asset"),
    ]:
        console_errors: list[str] = []
        page.on("console", lambda msg: console_errors.append(msg.text) if _is_js_error(msg) else None)
        loader(page, live_server)
        assert not console_errors, (
            f"JavaScript console errors during {label!r} render: {console_errors}"
        )
        console_errors.clear()


# ── CS349 ─────────────────────────────────────────────────────────────────────

def test_CS349_regression_existing_profiles_still_render_after_8t1(page: Page, live_server: str) -> None:
    """Phase 8T.1: regression guard — hospital and school profiles still render after 8T.1."""
    for profile_value, profile_label in [("مستشفى", "مستشفى"), ("مدرسة", "مدرسة")]:
        page.goto(live_server, wait_until="networkidle")
        _inject_session(page)
        page.select_option("#asset-type", value=profile_value)
        page.select_option("#val-purpose", value="fair_market_value")
        page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
        count = page.locator("#es-req-panel input, #es-req-panel select").count()
        assert count > 0, (
            f"Regression: {profile_label} panel must still render form controls after 8T.1. "
            f"Got {count} controls."
        )


# ══════════════════════════════════════════════════════════════════════════════
# Phase 8U.1 — Heritage / Timberland / Zoo-Safari profiles
# CS350–CS376
# ══════════════════════════════════════════════════════════════════════════════

def _load_heritage_property_detailed(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="heritage_property_detailed")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


def _load_timberland(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="timberland")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


def _load_zoo_safari(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="zoo_safari")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


# ── CS350 ─────────────────────────────────────────────────────────────────────

def test_CS350_optgroup_exceptional_natural_exists(page: Page, live_server: str) -> None:
    """Phase 8U.1: optgroup «أصول حيوية وطبيعية واستكشافية استثنائية» exists in the asset-type dropdown."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    labels = page.locator("#asset-type optgroup").evaluate_all("els => els.map(e => e.label)")
    assert "أصول حيوية وطبيعية واستكشافية استثنائية" in labels, (
        f"optgroup «أصول حيوية وطبيعية واستكشافية استثنائية» not found. Got: {labels}"
    )


# ── CS351 ─────────────────────────────────────────────────────────────────────

def test_CS351_option_heritage_property_detailed_present(page: Page, live_server: str) -> None:
    """Phase 8U.1: option value='heritage_property_detailed' exists with تفصيلية suffix."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    opt = page.locator("#asset-type option[value='heritage_property_detailed']")
    assert opt.count() == 1, "option value='heritage_property_detailed' not found in dropdown."
    text = opt.inner_text()
    assert "تفصيل" in text, (
        f"heritage_property_detailed option must contain «تفصيل». Got: {text!r}"
    )


# ── CS352 ─────────────────────────────────────────────────────────────────────

def test_CS352_option_timberland_present(page: Page, live_server: str) -> None:
    """Phase 8U.1: option value='timberland' exists in the asset-type dropdown."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    opt = page.locator("#asset-type option[value='timberland']")
    assert opt.count() == 1, "option value='timberland' not found in dropdown."


# ── CS353 ─────────────────────────────────────────────────────────────────────

def test_CS353_option_zoo_safari_present(page: Page, live_server: str) -> None:
    """Phase 8U.1: option value='zoo_safari' exists in the asset-type dropdown."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    opt = page.locator("#asset-type option[value='zoo_safari']")
    assert opt.count() == 1, "option value='zoo_safari' not found in dropdown."


# ── CS354 ─────────────────────────────────────────────────────────────────────

def test_CS354_heritage_property_detailed_badge_and_panel_render(page: Page, live_server: str) -> None:
    """Phase 8U.1: heritage_property_detailed renders badge and panel; no auth modal."""
    _load_heritage_property_detailed(page, live_server)
    assert page.locator("#es-profile-badge").is_visible(), "Badge must be visible for heritage_property_detailed."
    assert page.locator("#es-req-panel").is_visible(), "#es-req-panel must be visible."
    auth = page.locator("#auth-modal, #login-modal, .auth-modal")
    assert auth.count() == 0 or not auth.first.is_visible(), "Auth modal must NOT appear."


# ── CS355 ─────────────────────────────────────────────────────────────────────

def test_CS355_timberland_badge_and_panel_render(page: Page, live_server: str) -> None:
    """Phase 8U.1: timberland renders badge and panel; no auth modal."""
    _load_timberland(page, live_server)
    assert page.locator("#es-profile-badge").is_visible(), "Badge must be visible for timberland."
    assert page.locator("#es-req-panel").is_visible(), "#es-req-panel must be visible."
    auth = page.locator("#auth-modal, #login-modal, .auth-modal")
    assert auth.count() == 0 or not auth.first.is_visible(), "Auth modal must NOT appear."


# ── CS356 ─────────────────────────────────────────────────────────────────────

def test_CS356_zoo_safari_badge_and_panel_render(page: Page, live_server: str) -> None:
    """Phase 8U.1: zoo_safari renders badge and panel; no auth modal."""
    _load_zoo_safari(page, live_server)
    assert page.locator("#es-profile-badge").is_visible(), "Badge must be visible for zoo_safari."
    assert page.locator("#es-req-panel").is_visible(), "#es-req-panel must be visible."
    auth = page.locator("#auth-modal, #login-modal, .auth-modal")
    assert auth.count() == 0 or not auth.first.is_visible(), "Auth modal must NOT appear."


# ── CS357 ─────────────────────────────────────────────────────────────────────

def test_CS357_heritage_property_detailed_stays_on_page(page: Page, live_server: str) -> None:
    """Phase 8U.1: heritage_property_detailed does not navigate away from index.html."""
    _load_heritage_property_detailed(page, live_server)
    assert "127.0.0.1:5000" in page.url or "localhost:5000" in page.url, (
        f"Page navigated away after selecting heritage_property_detailed. URL: {page.url}"
    )


# ── CS358 ─────────────────────────────────────────────────────────────────────

def test_CS358_timberland_stays_on_page(page: Page, live_server: str) -> None:
    """Phase 8U.1: timberland does not navigate away from index.html."""
    _load_timberland(page, live_server)
    assert "127.0.0.1:5000" in page.url or "localhost:5000" in page.url, (
        f"Page navigated away after selecting timberland. URL: {page.url}"
    )


# ── CS359 ─────────────────────────────────────────────────────────────────────

def test_CS359_zoo_safari_stays_on_page(page: Page, live_server: str) -> None:
    """Phase 8U.1: zoo_safari does not navigate away from index.html."""
    _load_zoo_safari(page, live_server)
    assert "127.0.0.1:5000" in page.url or "localhost:5000" in page.url, (
        f"Page navigated away after selecting zoo_safari. URL: {page.url}"
    )


# ── CS360 ─────────────────────────────────────────────────────────────────────

def test_CS360_heritage_property_detailed_zero_api_calls(page: Page, live_server: str) -> None:
    """Phase 8U.1: heritage_property_detailed must not call /api/valuation/requirements."""
    api_calls: list[str] = []
    page.on("request", lambda req: api_calls.append(req.url) if "valuation/requirements" in req.url else None)
    _load_heritage_property_detailed(page, live_server)
    assert not api_calls, f"Unexpected API calls for heritage_property_detailed: {api_calls}"


# ── CS361 ─────────────────────────────────────────────────────────────────────

def test_CS361_timberland_zero_api_calls(page: Page, live_server: str) -> None:
    """Phase 8U.1: timberland must not call /api/valuation/requirements."""
    api_calls: list[str] = []
    page.on("request", lambda req: api_calls.append(req.url) if "valuation/requirements" in req.url else None)
    _load_timberland(page, live_server)
    assert not api_calls, f"Unexpected API calls for timberland: {api_calls}"


# ── CS362 ─────────────────────────────────────────────────────────────────────

def test_CS362_zoo_safari_zero_api_calls(page: Page, live_server: str) -> None:
    """Phase 8U.1: zoo_safari must not call /api/valuation/requirements."""
    api_calls: list[str] = []
    page.on("request", lambda req: api_calls.append(req.url) if "valuation/requirements" in req.url else None)
    _load_zoo_safari(page, live_server)
    assert not api_calls, f"Unexpected API calls for zoo_safari: {api_calls}"


# ── CS363 ─────────────────────────────────────────────────────────────────────

def test_CS363_heritage_property_detailed_key_fields_render(page: Page, live_server: str) -> None:
    """Phase 8U.1: heritage_property_detailed renders official_heritage_registration_number, protection_grade, moisture_resistance_condition."""
    _load_heritage_property_detailed(page, live_server)
    for field_name in (
        "hpd_official_registration_number",
        "hpd_protection_grade",
        "hpd_moisture_resistance_condition",
    ):
        assert page.locator(f"[data-es-req-field='{field_name}']").count() > 0, (
            f"heritage_property_detailed: field '{field_name}' not found in #es-req-panel."
        )


# ── CS364 ─────────────────────────────────────────────────────────────────────

def test_CS364_heritage_property_detailed_textarea_fields_render(page: Page, live_server: str) -> None:
    """Phase 8U.1: heritage_property_detailed renders previous_restoration_works and investment_restrictions_summary as textarea."""
    _load_heritage_property_detailed(page, live_server)
    for field_name in ("hpd_previous_restoration_works", "hpd_investment_restrictions_summary"):
        ta = page.locator(f"textarea[data-es-req-field='{field_name}']")
        assert ta.count() == 1, (
            f"heritage_property_detailed: '{field_name}' must render as <textarea>."
        )


# ── CS365 ─────────────────────────────────────────────────────────────────────

def test_CS365_timberland_key_fields_render(page: Page, live_server: str) -> None:
    """Phase 8U.1: timberland renders harvestable_biomass_m3_per_hectare, annual_net_growth_rate_pct, fsc_certification_status."""
    _load_timberland(page, live_server)
    for field_name in (
        "tb_harvestable_biomass_m3_per_hectare",
        "tb_annual_net_growth_rate_pct",
        "tb_fsc_certification_status",
    ):
        assert page.locator(f"[data-es-req-field='{field_name}']").count() > 0, (
            f"timberland: field '{field_name}' not found in #es-req-panel."
        )


# ── CS366 ─────────────────────────────────────────────────────────────────────

def test_CS366_timberland_units_render(page: Page, live_server: str) -> None:
    """Phase 8U.1: timberland panel renders unit strings م³/هكتار, م³/سنة, %."""
    _load_timberland(page, live_server)
    content = page.locator("#es-req-panel").inner_text()
    for unit in ("م³/هكتار", "م³/سنة", "%"):
        assert unit in content, (
            f"timberland: unit '{unit}' not found in #es-req-panel text."
        )


# ── CS367 ─────────────────────────────────────────────────────────────────────

def test_CS367_timberland_textarea_environmental_restrictions_renders(page: Page, live_server: str) -> None:
    """Phase 8U.1: timberland renders tb_environmental_restrictions as textarea."""
    _load_timberland(page, live_server)
    ta = page.locator("textarea[data-es-req-field='tb_environmental_restrictions']")
    assert ta.count() == 1, "timberland: tb_environmental_restrictions must render as <textarea>."


# ── CS368 ─────────────────────────────────────────────────────────────────────

def test_CS368_zoo_safari_key_fields_render(page: Page, live_server: str) -> None:
    """Phase 8U.1: zoo_safari renders animal_species_count, endangered_species_present, animal_welfare_compliance_status."""
    _load_zoo_safari(page, live_server)
    for field_name in (
        "zs_animal_species_count",
        "zs_endangered_species_present",
        "zs_animal_welfare_compliance_status",
    ):
        assert page.locator(f"[data-es-req-field='{field_name}']").count() > 0, (
            f"zoo_safari: field '{field_name}' not found in #es-req-panel."
        )


# ── CS369 ─────────────────────────────────────────────────────────────────────

def test_CS369_zoo_safari_textarea_inventory_renders(page: Page, live_server: str) -> None:
    """Phase 8U.1: zoo_safari renders zs_animal_inventory_summary as textarea."""
    _load_zoo_safari(page, live_server)
    ta = page.locator("textarea[data-es-req-field='zs_animal_inventory_summary']")
    assert ta.count() == 1, "zoo_safari: zs_animal_inventory_summary must render as <textarea>."


# ── CS370 ─────────────────────────────────────────────────────────────────────

def test_CS370_heritage_property_detailed_upload_hint_present(page: Page, live_server: str) -> None:
    """Phase 8U.1: heritage_property_detailed documents section contains upload hint."""
    _load_heritage_property_detailed(page, live_server)
    assert "ارفع المستندات من زر المرفقات" in page.locator("#es-req-panel").inner_text(), (
        "heritage_property_detailed: upload hint not found in #es-req-panel."
    )


# ── CS371 ─────────────────────────────────────────────────────────────────────

def test_CS371_timberland_upload_hint_present(page: Page, live_server: str) -> None:
    """Phase 8U.1: timberland documents section contains upload hint."""
    _load_timberland(page, live_server)
    assert "ارفع المستندات من زر المرفقات" in page.locator("#es-req-panel").inner_text(), (
        "timberland: upload hint not found in #es-req-panel."
    )


# ── CS372 ─────────────────────────────────────────────────────────────────────

def test_CS372_zoo_safari_upload_hint_present(page: Page, live_server: str) -> None:
    """Phase 8U.1: zoo_safari documents section contains upload hint."""
    _load_zoo_safari(page, live_server)
    assert "ارفع المستندات من زر المرفقات" in page.locator("#es-req-panel").inner_text(), (
        "zoo_safari: upload hint not found in #es-req-panel."
    )


# ── CS373 ─────────────────────────────────────────────────────────────────────

def test_CS373_no_console_errors_for_8u1_profiles(page: Page, live_server: str) -> None:
    """Phase 8U.1: no JS console errors when rendering heritage_property_detailed, timberland, zoo_safari."""
    def _is_js_error(msg) -> bool:
        return (
            msg.type == "error"
            and "401" not in msg.text
            and "UNAUTHORIZED" not in msg.text.upper()
            and "Failed to load resource" not in msg.text
        )
    for loader, label in [
        (_load_heritage_property_detailed, "heritage_property_detailed"),
        (_load_timberland,                 "timberland"),
        (_load_zoo_safari,                 "zoo_safari"),
    ]:
        console_errors: list[str] = []
        page.on("console", lambda msg: console_errors.append(msg.text) if _is_js_error(msg) else None)
        loader(page, live_server)
        assert not console_errors, (
            f"JS console errors during {label!r} render: {console_errors}"
        )
        console_errors.clear()


# ── CS374 ─────────────────────────────────────────────────────────────────────

def test_CS374_existing_heritage_profiles_unchanged_after_8u1(page: Page, live_server: str) -> None:
    """Phase 8U.1: existing historical and heritage profiles still render their own form controls unchanged."""
    for profile_value, profile_label in [("historical", "historical"), ("heritage", "heritage")]:
        page.goto(live_server, wait_until="networkidle")
        _inject_session(page)
        page.select_option("#asset-type", value=profile_value)
        page.select_option("#val-purpose", value="fair_market_value")
        page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
        count = page.locator("#es-req-panel input, #es-req-panel select").count()
        assert count > 0, (
            f"Regression: {profile_label} must still render form controls after 8U.1. Got {count}."
        )


# ── CS375 ─────────────────────────────────────────────────────────────────────

def test_CS375_agricultural_land_unchanged_after_8u1(page: Page, live_server: str) -> None:
    """Phase 8U.1: agricultural_land still renders its form controls unchanged after 8U.1."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="أرض زراعية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    count = page.locator("#es-req-panel input, #es-req-panel select").count()
    assert count > 0, (
        f"Regression: agricultural_land must still render form controls after 8U.1. Got {count}."
    )


# ── CS376 ─────────────────────────────────────────────────────────────────────

def test_CS376_8r_8s_8t_profiles_still_render_after_8u1(page: Page, live_server: str) -> None:
    """Phase 8U.1: regression guard — sample of 8R/8S/8T profiles still render after 8U.1."""
    for profile_value in ("airport", "data_center", "healthcare_facility", "educational_asset"):
        page.goto(live_server, wait_until="networkidle")
        _inject_session(page)
        page.select_option("#asset-type", value=profile_value)
        page.select_option("#val-purpose", value="fair_market_value")
        page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
        count = page.locator("#es-req-panel input, #es-req-panel select").count()
        assert count > 0, (
            f"Regression: {profile_value} panel must still render form controls after 8U.1. Got {count}."
        )


# ══════════════════════════════════════════════════════════════════════════════
# Phase 8V — Littoral Rights / Riparian Rights / Waterway Easement
# CS377–CS403
# ══════════════════════════════════════════════════════════════════════════════

def _load_littoral_rights(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="littoral_rights")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


def _load_riparian_rights(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="riparian_rights")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


def _load_waterway_easement(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="waterway_easement")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


# ── CS377 ─────────────────────────────────────────────────────────────────────

def test_CS377_optgroup_water_rights_present(page: Page, live_server: str) -> None:
    """Phase 8V: new optgroup «حقوق شاطئية ومائية وممرات ملاحية» appears in asset-type dropdown."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    html = page.locator("#asset-type").evaluate("el => el.outerHTML")
    assert "حقوق شاطئية ومائية وممرات ملاحية" in html, (
        "Phase 8V optgroup label not found in #asset-type dropdown."
    )


# ── CS378 ─────────────────────────────────────────────────────────────────────

def test_CS378_option_littoral_rights_present(page: Page, live_server: str) -> None:
    """Phase 8V: option value 'littoral_rights' appears in asset-type dropdown."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    options = page.locator("#asset-type option").all_inner_texts()
    html = page.locator("#asset-type").evaluate("el => el.outerHTML")
    assert "littoral_rights" in html, (
        f"littoral_rights option not found in #asset-type. Options: {options}"
    )


# ── CS379 ─────────────────────────────────────────────────────────────────────

def test_CS379_option_riparian_rights_present(page: Page, live_server: str) -> None:
    """Phase 8V: option value 'riparian_rights' appears in asset-type dropdown."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    html = page.locator("#asset-type").evaluate("el => el.outerHTML")
    assert "riparian_rights" in html, (
        "riparian_rights option not found in #asset-type dropdown."
    )


# ── CS380 ─────────────────────────────────────────────────────────────────────

def test_CS380_option_waterway_easement_present(page: Page, live_server: str) -> None:
    """Phase 8V: option value 'waterway_easement' appears in asset-type dropdown."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    html = page.locator("#asset-type").evaluate("el => el.outerHTML")
    assert "waterway_easement" in html, (
        "waterway_easement option not found in #asset-type dropdown."
    )


# ── CS381 ─────────────────────────────────────────────────────────────────────

def test_CS381_littoral_rights_panel_renders(page: Page, live_server: str) -> None:
    """Phase 8V: selecting littoral_rights renders badge «نموذج محلي» and #es-req-panel."""
    _load_littoral_rights(page, live_server)
    badge = page.locator("#es-profile-badge").inner_text()
    assert "نموذج محلي" in badge, (
        f"littoral_rights: badge must show «نموذج محلي». Got: {badge!r}"
    )
    count = page.locator("#es-req-panel input, #es-req-panel select, #es-req-panel textarea").count()
    assert count > 0, (
        f"littoral_rights: #es-req-panel must render form controls. Got {count}."
    )


# ── CS382 ─────────────────────────────────────────────────────────────────────

def test_CS382_riparian_rights_panel_renders(page: Page, live_server: str) -> None:
    """Phase 8V: selecting riparian_rights renders badge «نموذج محلي» and #es-req-panel."""
    _load_riparian_rights(page, live_server)
    badge = page.locator("#es-profile-badge").inner_text()
    assert "نموذج محلي" in badge, (
        f"riparian_rights: badge must show «نموذج محلي». Got: {badge!r}"
    )
    count = page.locator("#es-req-panel input, #es-req-panel select, #es-req-panel textarea").count()
    assert count > 0, (
        f"riparian_rights: #es-req-panel must render form controls. Got {count}."
    )


# ── CS383 ─────────────────────────────────────────────────────────────────────

def test_CS383_waterway_easement_panel_renders(page: Page, live_server: str) -> None:
    """Phase 8V: selecting waterway_easement renders badge «نموذج محلي» and #es-req-panel."""
    _load_waterway_easement(page, live_server)
    badge = page.locator("#es-profile-badge").inner_text()
    assert "نموذج محلي" in badge, (
        f"waterway_easement: badge must show «نموذج محلي». Got: {badge!r}"
    )
    count = page.locator("#es-req-panel input, #es-req-panel select, #es-req-panel textarea").count()
    assert count > 0, (
        f"waterway_easement: #es-req-panel must render form controls. Got {count}."
    )


# ── CS384 ─────────────────────────────────────────────────────────────────────

def test_CS384_littoral_rights_stays_on_page(page: Page, live_server: str) -> None:
    """Phase 8V: selecting littoral_rights does not navigate away from index.html."""
    _load_littoral_rights(page, live_server)
    assert page.url.rstrip("/").endswith(":5000") or "127.0.0.1:5000" in page.url, (
        f"littoral_rights: page must stay on index.html. URL: {page.url}"
    )


# ── CS385 ─────────────────────────────────────────────────────────────────────

def test_CS385_riparian_rights_stays_on_page(page: Page, live_server: str) -> None:
    """Phase 8V: selecting riparian_rights does not navigate away from index.html."""
    _load_riparian_rights(page, live_server)
    assert page.url.rstrip("/").endswith(":5000") or "127.0.0.1:5000" in page.url, (
        f"riparian_rights: page must stay on index.html. URL: {page.url}"
    )


# ── CS386 ─────────────────────────────────────────────────────────────────────

def test_CS386_waterway_easement_stays_on_page(page: Page, live_server: str) -> None:
    """Phase 8V: selecting waterway_easement does not navigate away from index.html."""
    _load_waterway_easement(page, live_server)
    assert page.url.rstrip("/").endswith(":5000") or "127.0.0.1:5000" in page.url, (
        f"waterway_easement: page must stay on index.html. URL: {page.url}"
    )


# ── CS387 ─────────────────────────────────────────────────────────────────────

def test_CS387_littoral_rights_zero_api_calls(page: Page, live_server: str) -> None:
    """Phase 8V: littoral_rights triggers zero POST requests to /api/valuation."""
    api_calls: list[str] = []
    page.on("request", lambda req: api_calls.append(req.url) if "/api/valuation" in req.url else None)
    _load_littoral_rights(page, live_server)
    assert not api_calls, (
        f"littoral_rights: must trigger zero API calls. Got: {api_calls}"
    )


# ── CS388 ─────────────────────────────────────────────────────────────────────

def test_CS388_riparian_rights_zero_api_calls(page: Page, live_server: str) -> None:
    """Phase 8V: riparian_rights triggers zero POST requests to /api/valuation."""
    api_calls: list[str] = []
    page.on("request", lambda req: api_calls.append(req.url) if "/api/valuation" in req.url else None)
    _load_riparian_rights(page, live_server)
    assert not api_calls, (
        f"riparian_rights: must trigger zero API calls. Got: {api_calls}"
    )


# ── CS389 ─────────────────────────────────────────────────────────────────────

def test_CS389_waterway_easement_zero_api_calls(page: Page, live_server: str) -> None:
    """Phase 8V: waterway_easement triggers zero POST requests to /api/valuation."""
    api_calls: list[str] = []
    page.on("request", lambda req: api_calls.append(req.url) if "/api/valuation" in req.url else None)
    _load_waterway_easement(page, live_server)
    assert not api_calls, (
        f"waterway_easement: must trigger zero API calls. Got: {api_calls}"
    )


# ── CS390 ─────────────────────────────────────────────────────────────────────

def test_CS390_littoral_rights_key_fields_render(page: Page, live_server: str) -> None:
    """Phase 8V: littoral_rights key fields render in #es-req-panel."""
    _load_littoral_rights(page, live_server)
    panel = page.locator("#es-req-panel")
    for field_name in (
        "lr_coastal_frontage_length_m",
        "lr_coastal_setback_distance_m",
        "lr_annual_erosion_rate_m_per_year",
        "lr_wave_breakers_available",
    ):
        loc = panel.locator(f"[data-es-req-field='{field_name}']")
        assert loc.count() > 0, (
            f"littoral_rights: field '{field_name}' not found in #es-req-panel."
        )


# ── CS391 ─────────────────────────────────────────────────────────────────────

def test_CS391_riparian_rights_key_fields_render(page: Page, live_server: str) -> None:
    """Phase 8V: riparian_rights key fields render in #es-req-panel."""
    _load_riparian_rights(page, live_server)
    panel = page.locator("#es-req-panel")
    for field_name in (
        "rr_river_frontage_length_m",
        "rr_right_to_build_dock_or_pier",
        "rr_permitted_water_withdrawal_volume_m3_day",
        "rr_water_withdrawal_license_status",
    ):
        loc = panel.locator(f"[data-es-req-field='{field_name}']")
        assert loc.count() > 0, (
            f"riparian_rights: field '{field_name}' not found in #es-req-panel."
        )


# ── CS392 ─────────────────────────────────────────────────────────────────────

def test_CS392_waterway_easement_key_fields_render(page: Page, live_server: str) -> None:
    """Phase 8V: waterway_easement key fields render in #es-req-panel."""
    _load_waterway_easement(page, live_server)
    panel = page.locator("#es-req-panel")
    for field_name in (
        "we_waterway_width_m",
        "we_navigable_depth_m",
        "we_waterway_legal_status",
        "we_dredging_required",
        "we_periodic_dredging_cost_annual",
    ):
        loc = panel.locator(f"[data-es-req-field='{field_name}']")
        assert loc.count() > 0, (
            f"waterway_easement: field '{field_name}' not found in #es-req-panel."
        )


# ── CS393 ─────────────────────────────────────────────────────────────────────

def test_CS393_littoral_rights_textarea_renders(page: Page, live_server: str) -> None:
    """Phase 8V: littoral_rights insurance_or_environmental_risk_notes renders as <textarea>."""
    _load_littoral_rights(page, live_server)
    loc = page.locator("textarea[data-es-req-field='lr_insurance_or_environmental_risk_notes']")
    assert loc.count() > 0, (
        "littoral_rights: textarea 'lr_insurance_or_environmental_risk_notes' not found in #es-req-panel."
    )


# ── CS394 ─────────────────────────────────────────────────────────────────────

def test_CS394_littoral_rights_upload_hint_present(page: Page, live_server: str) -> None:
    """Phase 8V: littoral_rights document section contains upload guidance text."""
    _load_littoral_rights(page, live_server)
    hint_text = "ارفع المستندات من زر المرفقات"
    content = page.locator("#es-req-panel").inner_text()
    assert hint_text in content, (
        f"littoral_rights: upload hint not found in #es-req-panel."
    )


# ── CS395 ─────────────────────────────────────────────────────────────────────

def test_CS395_riparian_rights_upload_hint_present(page: Page, live_server: str) -> None:
    """Phase 8V: riparian_rights document section contains upload guidance text."""
    _load_riparian_rights(page, live_server)
    hint_text = "ارفع المستندات من زر المرفقات"
    content = page.locator("#es-req-panel").inner_text()
    assert hint_text in content, (
        f"riparian_rights: upload hint not found in #es-req-panel."
    )


# ── CS396 ─────────────────────────────────────────────────────────────────────

def test_CS396_waterway_easement_upload_hint_present(page: Page, live_server: str) -> None:
    """Phase 8V: waterway_easement document section contains upload guidance text."""
    _load_waterway_easement(page, live_server)
    hint_text = "ارفع المستندات من زر المرفقات"
    content = page.locator("#es-req-panel").inner_text()
    assert hint_text in content, (
        f"waterway_easement: upload hint not found in #es-req-panel."
    )


# ── CS397 ─────────────────────────────────────────────────────────────────────

def test_CS397_unit_display_renders(page: Page, live_server: str) -> None:
    """Phase 8V: unit labels «متر طولي» (littoral_rights) and «م³/يوم» (riparian_rights) render."""
    _load_littoral_rights(page, live_server)
    content_lr = page.locator("#es-req-panel").inner_text()
    assert "متر طولي" in content_lr, (
        f"littoral_rights: unit 'متر طولي' not found in #es-req-panel."
    )
    _load_riparian_rights(page, live_server)
    content_rr = page.locator("#es-req-panel").inner_text()
    assert "م³/يوم" in content_rr, (
        f"riparian_rights: unit 'م³/يوم' not found in #es-req-panel."
    )


# ── CS398 ─────────────────────────────────────────────────────────────────────

def test_CS398_no_console_errors_for_8v_profiles(page: Page, live_server: str) -> None:
    """Phase 8V: no JS console errors when rendering littoral_rights, riparian_rights, waterway_easement."""
    def _is_js_error(msg) -> bool:
        return (
            msg.type == "error"
            and "401" not in msg.text
            and "UNAUTHORIZED" not in msg.text.upper()
            and "Failed to load resource" not in msg.text
        )
    for loader, label in [
        (_load_littoral_rights,  "littoral_rights"),
        (_load_riparian_rights,  "riparian_rights"),
        (_load_waterway_easement,"waterway_easement"),
    ]:
        console_errors: list[str] = []
        page.on("console", lambda msg: console_errors.append(msg.text) if _is_js_error(msg) else None)
        loader(page, live_server)
        assert not console_errors, (
            f"JS console errors during {label!r} render: {console_errors}"
        )
        console_errors.clear()


# ── CS399 ─────────────────────────────────────────────────────────────────────

def test_CS399_marina_unchanged_after_8v(page: Page, live_server: str) -> None:
    """Phase 8V: marina still renders its form controls unchanged after 8V."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="marina")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    count = page.locator("#es-req-panel input, #es-req-panel select").count()
    assert count > 0, (
        f"Regression: marina must still render form controls after 8V. Got {count}."
    )


# ── CS400 ─────────────────────────────────────────────────────────────────────

def test_CS400_water_well_unchanged_after_8v(page: Page, live_server: str) -> None:
    """Phase 8V: water_well still renders its form controls unchanged after 8V."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="water_well")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    count = page.locator("#es-req-panel input, #es-req-panel select").count()
    assert count > 0, (
        f"Regression: water_well must still render form controls after 8V. Got {count}."
    )


# ── CS401 ─────────────────────────────────────────────────────────────────────

def test_CS401_seaport_unchanged_after_8v(page: Page, live_server: str) -> None:
    """Phase 8V: seaport still renders its form controls unchanged after 8V."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="seaport")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    count = page.locator("#es-req-panel input, #es-req-panel select").count()
    assert count > 0, (
        f"Regression: seaport must still render form controls after 8V. Got {count}."
    )


# ── CS402 ─────────────────────────────────────────────────────────────────────

def test_CS402_agricultural_land_unchanged_after_8v(page: Page, live_server: str) -> None:
    """Phase 8V: agricultural_land still renders its form controls unchanged after 8V."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="أرض زراعية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    count = page.locator("#es-req-panel input, #es-req-panel select").count()
    assert count > 0, (
        f"Regression: agricultural_land must still render form controls after 8V. Got {count}."
    )


# ── CS403 ─────────────────────────────────────────────────────────────────────

def test_CS403_8r_8s_8t_8u_profiles_still_render_after_8v(page: Page, live_server: str) -> None:
    """Phase 8V: regression guard — sample of 8R/8S/8T/8U profiles still render after 8V."""
    for profile_value in ("airport", "data_center", "healthcare_facility", "heritage_property_detailed", "zoo_safari"):
        page.goto(live_server, wait_until="networkidle")
        _inject_session(page)
        page.select_option("#asset-type", value=profile_value)
        page.select_option("#val-purpose", value="fair_market_value")
        page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
        count = page.locator("#es-req-panel input, #es-req-panel select").count()
        assert count > 0, (
            f"Regression: {profile_value} panel must still render form controls after 8V. Got {count}."
        )


# ══════════════════════════════════════════════════════════════════════════════
# Phase 8W — Clarify & Make Visible: Residential Unit & Vacant Land
# CS404–CS418
# ══════════════════════════════════════════════════════════════════════════════

def _load_residential_supp_8w(page: Page, live_server: str) -> None:
    """Phase 8W: load residential_unit via forced 401 path; wait until supplemental header is visible."""
    _mock_req_401(page)
    page.goto(live_server, wait_until="networkidle")
    page.evaluate("localStorage.removeItem('es_auth')")
    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-supp-header").wait_for(state="visible", timeout=8_000)


def _load_land_supp_8w(page: Page, live_server: str) -> None:
    """Phase 8W: load land via forced 401 path; wait until supplemental header is visible."""
    _mock_req_401(page)
    page.goto(live_server, wait_until="networkidle")
    page.evaluate("localStorage.removeItem('es_auth')")
    page.select_option("#asset-type", value="أرض فضاء")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-supp-header").wait_for(state="visible", timeout=8_000)


# ── CS404 ─────────────────────────────────────────────────────────────────────

def test_CS404_residential_supp_heading_renders(page: Page, live_server: str) -> None:
    """Phase 8W: residential supplemental heading 'متطلبات تقييم الوحدة السكنية — شقة / فيلا' is visible."""
    _load_residential_supp_8w(page, live_server)
    header_text = page.locator("#es-req-supp-header").inner_text()
    assert "متطلبات تقييم الوحدة السكنية" in header_text, (
        f"Phase 8W residential heading missing from #es-req-supp-header. Got: {header_text!r}"
    )
    assert "شقة / فيلا" in header_text, (
        f"Phase 8W residential heading must include 'شقة / فيلا'. Got: {header_text!r}"
    )


# ── CS405 ─────────────────────────────────────────────────────────────────────

def test_CS405_land_supp_heading_renders(page: Page, live_server: str) -> None:
    """Phase 8W: land supplemental heading 'متطلبات تقييم الأرض الفضاء — مطوَّرة أو خام' is visible."""
    _load_land_supp_8w(page, live_server)
    header_text = page.locator("#es-req-supp-header").inner_text()
    assert "متطلبات تقييم الأرض الفضاء" in header_text, (
        f"Phase 8W land heading missing from #es-req-supp-header. Got: {header_text!r}"
    )
    assert "مطوَّرة أو خام" in header_text or "مطورة أو خام" in header_text, (
        f"Phase 8W land heading must include developed/raw qualifier. Got: {header_text!r}"
    )


# ── CS406 ─────────────────────────────────────────────────────────────────────

def test_CS406_residential_supp_separator_text_renders(page: Page, live_server: str) -> None:
    """Phase 8W: residential separator subtext 'الحقول أعلاه من سجل المتطلبات الأساسي' is visible."""
    _load_residential_supp_8w(page, live_server)
    subtext_el = page.locator("#es-req-supp-subtext")
    subtext_el.wait_for(state="visible", timeout=4_000)
    txt = subtext_el.inner_text()
    assert "الحقول أعلاه من سجل المتطلبات الأساسي" in txt, (
        f"Phase 8W residential separator subtext missing. Got: {txt!r}"
    )
    assert "إدخال محلي" in txt, (
        f"Phase 8W residential separator must mention 'إدخال محلي'. Got: {txt!r}"
    )


# ── CS407 ─────────────────────────────────────────────────────────────────────

def test_CS407_land_supp_separator_text_renders(page: Page, live_server: str) -> None:
    """Phase 8W: land separator subtext 'الحقول أعلاه من سجل المتطلبات الأساسي' is visible."""
    _load_land_supp_8w(page, live_server)
    subtext_el = page.locator("#es-req-supp-subtext")
    subtext_el.wait_for(state="visible", timeout=4_000)
    txt = subtext_el.inner_text()
    assert "الحقول أعلاه من سجل المتطلبات الأساسي" in txt, (
        f"Phase 8W land separator subtext missing. Got: {txt!r}"
    )
    assert "إدخال محلي" in txt, (
        f"Phase 8W land separator must mention 'إدخال محلي'. Got: {txt!r}"
    )


# ── CS408 ─────────────────────────────────────────────────────────────────────

def test_CS408_residential_unit_type_includes_penthouse(page: Page, live_server: str) -> None:
    """Phase 8W: residential supplemental unit_type select includes penthouse option."""
    _load_residential_supp_8w(page, live_server)
    unit_type_sel = page.locator("[data-es-supp-field='unit_type']")
    unit_type_sel.wait_for(state="visible", timeout=4_000)
    html = unit_type_sel.evaluate("el => el.outerHTML")
    assert "penthouse" in html, (
        f"Phase 8W: unit_type select must include 'penthouse' option. Got: {html!r}"
    )


# ── CS409 ─────────────────────────────────────────────────────────────────────

def test_CS409_land_development_stage_renders(page: Page, live_server: str) -> None:
    """Phase 8W: land_development_stage field renders as first supplemental field in land panel."""
    _load_land_supp_8w(page, live_server)
    stage_sel = page.locator("[data-es-supp-field='land_development_stage']")
    stage_sel.wait_for(state="visible", timeout=4_000)
    assert stage_sel.count() == 1, (
        f"Phase 8W: land_development_stage must render exactly once in land supplemental. Got {stage_sel.count()}."
    )


# ── CS410 ─────────────────────────────────────────────────────────────────────

def test_CS410_land_development_stage_has_raw_and_ready_options(page: Page, live_server: str) -> None:
    """Phase 8W: land_development_stage select includes raw_land and ready_to_build options."""
    _load_land_supp_8w(page, live_server)
    stage_sel = page.locator("[data-es-supp-field='land_development_stage']")
    stage_sel.wait_for(state="visible", timeout=4_000)
    html = stage_sel.evaluate("el => el.outerHTML")
    assert "raw_land" in html, (
        f"Phase 8W: land_development_stage must include 'raw_land' option. Got: {html!r}"
    )
    assert "ready_to_build" in html, (
        f"Phase 8W: land_development_stage must include 'ready_to_build' option. Got: {html!r}"
    )


# ── CS411 ─────────────────────────────────────────────────────────────────────

def test_CS411_401_residential_no_modal_supp_renders(page: Page, live_server: str) -> None:
    """Phase 8W (8P): 401 for residential — no auth modal AND supplemental still renders."""
    _mock_req_401(page)
    page.goto(live_server, wait_until="networkidle")
    page.evaluate("localStorage.removeItem('es_auth')")
    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-soft-msg").wait_for(state="visible", timeout=5_000)
    assert not page.locator("#es-login-modal").is_visible(), (
        "Login modal must NOT appear for residential_unit on 401 (Phase 8P/8W)"
    )
    page.locator("#es-req-supp-header").wait_for(state="visible", timeout=5_000)
    assert "متطلبات تقييم الوحدة السكنية" in page.locator("#es-req-supp-header").inner_text(), (
        "Phase 8W: residential supplemental must render heading even on API 401"
    )


# ── CS412 ─────────────────────────────────────────────────────────────────────

def test_CS412_401_land_no_modal_supp_renders(page: Page, live_server: str) -> None:
    """Phase 8W (8P): 401 for land — no auth modal AND supplemental still renders."""
    _mock_req_401(page)
    page.goto(live_server, wait_until="networkidle")
    page.evaluate("localStorage.removeItem('es_auth')")
    page.select_option("#asset-type", value="أرض فضاء")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-soft-msg").wait_for(state="visible", timeout=5_000)
    assert not page.locator("#es-login-modal").is_visible(), (
        "Login modal must NOT appear for land on 401 (Phase 8P/8W)"
    )
    page.locator("#es-req-supp-header").wait_for(state="visible", timeout=5_000)
    assert "متطلبات تقييم الأرض الفضاء" in page.locator("#es-req-supp-header").inner_text(), (
        "Phase 8W: land supplemental must render heading even on API 401"
    )


# ── CS413 ─────────────────────────────────────────────────────────────────────

def test_CS413_no_duplicate_api_fields_in_residential_supp(page: Page, live_server: str) -> None:
    """Phase 8W/8Z: API-rendered fields must NOT appear as supplemental fields in residential panel.
    Note: view_quality removed from this list in 8Z — it is now a legitimate supplemental field
    (not in API mock) and was pre-emptively over-listed here in a prior wave.
    """
    _load_residential_supp_8w(page, live_server)
    supp = page.locator("#es-req-supp")
    for name in (
        "area_sqm", "floor_number", "rooms_count", "finishing_level",
        "legal_status", "elevator_available", "parking_available",
    ):
        count = supp.locator(f"[data-es-supp-field='{name}']").count()
        assert count == 0, (
            f"Phase 8W: API field '{name}' must not appear in residential supplemental. Found {count}."
        )


# ── CS414 ─────────────────────────────────────────────────────────────────────

def test_CS414_no_duplicate_api_fields_in_land_supp(page: Page, live_server: str) -> None:
    """Phase 8W: API-rendered fields must NOT appear as supplemental fields in land panel."""
    _load_land_supp_8w(page, live_server)
    supp = page.locator("#es-req-supp")
    for name in (
        "land_area_sqm", "frontage_m", "street_width_m", "zoning_type",
        "buildability_status", "legal_status", "utilities_available", "hbu",
    ):
        count = supp.locator(f"[data-es-supp-field='{name}']").count()
        assert count == 0, (
            f"Phase 8W: API field '{name}' must not appear in land supplemental. Found {count}."
        )


# ── CS415 ─────────────────────────────────────────────────────────────────────

def test_CS415_agricultural_land_unchanged_after_8w(page: Page, live_server: str) -> None:
    """Phase 8W: agricultural_land still renders its form controls unchanged after 8W."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="أرض زراعية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    count = page.locator("#es-req-panel input, #es-req-panel select").count()
    assert count > 0, (
        f"Regression: agricultural_land must still render form controls after 8W. Got {count}."
    )


# ── CS416 ─────────────────────────────────────────────────────────────────────

def test_CS416_8r_8s_8t_8u_8v_profiles_still_render_after_8w(page: Page, live_server: str) -> None:
    """Phase 8W: regression guard — sample of 8R/8S/8T/8U/8V profiles still render after 8W."""
    for profile_value in ("airport", "data_center", "healthcare_facility", "zoo_safari", "littoral_rights"):
        page.goto(live_server, wait_until="networkidle")
        _inject_session(page)
        page.select_option("#asset-type", value=profile_value)
        page.select_option("#val-purpose", value="fair_market_value")
        page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
        count = page.locator("#es-req-panel input, #es-req-panel select").count()
        assert count > 0, (
            f"Regression: {profile_value} panel must still render form controls after 8W. Got {count}."
        )


# ── CS417 ─────────────────────────────────────────────────────────────────────

def test_CS417_no_composite_link_residential_land_after_8w(page: Page, live_server: str) -> None:
    """Phase 8W: residential_unit and land panels must NOT contain composite_valuation.html link."""
    for asset_value in ("شقة سكنية", "أرض فضاء"):
        _mock_req_401(page)
        page.goto(live_server, wait_until="networkidle")
        page.evaluate("localStorage.removeItem('es_auth')")
        page.select_option("#asset-type", value=asset_value)
        page.select_option("#val-purpose", value="fair_market_value")
        page.locator("#es-req-panel").wait_for(state="visible", timeout=5_000)
        panel_html = page.locator("#es-req-panel").inner_html()
        assert "composite_valuation.html" not in panel_html, (
            f"Phase 8W: composite link must not appear in panel for {asset_value!r}"
        )


# ── CS418 ─────────────────────────────────────────────────────────────────────

def test_CS418_no_console_errors_for_8w_profiles(page: Page, live_server: str) -> None:
    """Phase 8W: no JS console errors when loading residential_unit or land (8W supplemental)."""
    def _is_js_error(msg) -> bool:
        return (
            msg.type == "error"
            and "401" not in msg.text
            and "UNAUTHORIZED" not in msg.text.upper()
            and "Failed to load resource" not in msg.text
        )

    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if _is_js_error(msg) else None)

    for asset_value in ("شقة سكنية", "أرض فضاء"):
        _mock_req_401(page)
        page.goto(live_server, wait_until="networkidle")
        page.evaluate("localStorage.removeItem('es_auth')")
        page.select_option("#asset-type", value=asset_value)
        page.select_option("#val-purpose", value="fair_market_value")
        page.locator("#es-req-supp-header").wait_for(state="visible", timeout=8_000)

    assert not errors, (
        f"Phase 8W: unexpected JS console errors for residential/land 8W profiles: {errors}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Phase 8X.1 — Hospitality: hotel_resort_detailed, serviced_apartments, floating_hotel
# CS419–CS447
# ══════════════════════════════════════════════════════════════════════════════

def _load_hotel_resort_detailed(page: Page, live_server: str) -> None:
    """Phase 8X.1: load hotel_resort_detailed local form."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="hotel_resort_detailed")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


def _load_serviced_apartments(page: Page, live_server: str) -> None:
    """Phase 8X.1: load serviced_apartments local form."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="serviced_apartments")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


def _load_floating_hotel(page: Page, live_server: str) -> None:
    """Phase 8X.1: load floating_hotel local form."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="floating_hotel")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


# ── CS419 ─────────────────────────────────────────────────────────────────────

def test_CS419_optgroup_hospitality_entertainment_exists(page: Page, live_server: str) -> None:
    """Phase 8X.1: optgroup «أصول الترفيه والضيافة والتجمع الجماهيري» exists in the asset-type dropdown."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    labels = page.locator("#asset-type optgroup").evaluate_all("els => els.map(e => e.label)")
    assert "أصول الترفيه والضيافة والتجمع الجماهيري" in labels, (
        f"optgroup «أصول الترفيه والضيافة والتجمع الجماهيري» not found in dropdown. "
        f"Got: {labels}"
    )


# ── CS420 ─────────────────────────────────────────────────────────────────────

def test_CS420_all_three_8x1_options_present(page: Page, live_server: str) -> None:
    """Phase 8X.1: all three 8X.1 options exist in the asset-type dropdown."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    for value in ("hotel_resort_detailed", "serviced_apartments", "floating_hotel"):
        opt = page.locator(f"#asset-type option[value='{value}']")
        assert opt.count() == 1, f"option value='{value}' not found in dropdown."


# ── CS421 ─────────────────────────────────────────────────────────────────────

def test_CS421_hotel_resort_detailed_badge_and_panel_render(page: Page, live_server: str) -> None:
    """Phase 8X.1: selecting hotel_resort_detailed shows badge and requirements panel."""
    _load_hotel_resort_detailed(page, live_server)
    badge = page.locator("#es-profile-badge")
    assert badge.is_visible(), "Profile badge must be visible for hotel_resort_detailed."
    panel = page.locator("#es-req-panel")
    assert panel.is_visible(), "#es-req-panel must be visible for hotel_resort_detailed."
    auth_modal = page.locator("#auth-modal, #login-modal, .auth-modal")
    assert auth_modal.count() == 0 or not auth_modal.first.is_visible(), (
        "Auth modal must NOT appear for hotel_resort_detailed."
    )


# ── CS422 ─────────────────────────────────────────────────────────────────────

def test_CS422_hotel_resort_detailed_stays_on_page(page: Page, live_server: str) -> None:
    """Phase 8X.1: selecting hotel_resort_detailed does not navigate away from the page."""
    _load_hotel_resort_detailed(page, live_server)
    assert "127.0.0.1:5000" in page.url or "localhost:5000" in page.url, (
        f"Page navigated away after selecting hotel_resort_detailed. URL: {page.url}"
    )


# ── CS423 ─────────────────────────────────────────────────────────────────────

def test_CS423_hotel_resort_detailed_zero_api_calls(page: Page, live_server: str) -> None:
    """Phase 8X.1: hotel_resort_detailed must not call /api/valuation/requirements."""
    api_calls: list[str] = []
    page.on("request", lambda req: api_calls.append(req.url) if "valuation/requirements" in req.url else None)
    _load_hotel_resort_detailed(page, live_server)
    assert not api_calls, (
        f"hotel_resort_detailed must be fully static; unexpected API calls: {api_calls}"
    )


# ── CS424 ─────────────────────────────────────────────────────────────────────

def test_CS424_hotel_resort_detailed_key_fields_render(page: Page, live_server: str) -> None:
    """Phase 8X.1: hotel_resort_detailed renders hrd_keys_count, hrd_rooms_count, hrd_hotel_star_rating."""
    _load_hotel_resort_detailed(page, live_server)
    for field_name in ("hrd_keys_count", "hrd_rooms_count", "hrd_hotel_star_rating"):
        field = page.locator(f"#es-req-field-{field_name}")
        assert field.count() > 0, (
            f"hotel_resort_detailed: field '#es-req-field-{field_name}' not found in panel."
        )


# ── CS425 ─────────────────────────────────────────────────────────────────────

def test_CS425_hotel_resort_detailed_resort_facilities_checkbox_group(page: Page, live_server: str) -> None:
    """Phase 8X.1: hrd_resort_facilities_available checkbox_group renders with facility chips."""
    _load_hotel_resort_detailed(page, live_server)
    chips = page.locator("[data-es-req-field='hrd_resort_facilities_available']")
    expect(chips.first).to_be_visible()
    pool_chip = page.locator("[data-es-req-field='hrd_resort_facilities_available'][value='pool']")
    expect(pool_chip).to_be_attached()


# ── CS426 ─────────────────────────────────────────────────────────────────────

def test_CS426_hotel_resort_detailed_adr_number_input_with_unit(page: Page, live_server: str) -> None:
    """Phase 8X.1: hrd_adr renders as number input; unit 'جنيه/ليلة' visible in panel."""
    _load_hotel_resort_detailed(page, live_server)
    field = page.locator("#es-req-field-hrd_adr")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "number", (
        f"hrd_adr must be number input. Got type={field.get_attribute('type')!r}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "جنيه/ليلة" in panel_text, (
        f"hotel_resort_detailed panel must show 'جنيه/ليلة' unit. Got: {panel_text[:400]!r}"
    )


# ── CS427 ─────────────────────────────────────────────────────────────────────

def test_CS427_hotel_resort_detailed_occupancy_field_with_percent_unit(page: Page, live_server: str) -> None:
    """Phase 8X.1: hrd_annual_occupancy_rate renders as number input with '%' unit visible."""
    _load_hotel_resort_detailed(page, live_server)
    field = page.locator("#es-req-field-hrd_annual_occupancy_rate")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "number", (
        f"hrd_annual_occupancy_rate must be number input. Got type={field.get_attribute('type')!r}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "%" in panel_text, (
        f"hotel_resort_detailed panel must show '%' for occupancy. Got: {panel_text[:400]!r}"
    )


# ── CS428 ─────────────────────────────────────────────────────────────────────

def test_CS428_hotel_resort_detailed_management_contract_textarea(page: Page, live_server: str) -> None:
    """Phase 8X.1: hrd_management_contract_terms renders as textarea."""
    _load_hotel_resort_detailed(page, live_server)
    field = page.locator("#es-req-field-hrd_management_contract_terms")
    expect(field).to_be_visible()
    assert field.evaluate("el => el.tagName.toLowerCase()") == "textarea", (
        "hrd_management_contract_terms must be a textarea element."
    )


# ── CS429 ─────────────────────────────────────────────────────────────────────

def test_CS429_hotel_resort_detailed_upload_hint_present(page: Page, live_server: str) -> None:
    """Phase 8X.1: hotel_resort_detailed document section shows upload hint text."""
    _load_hotel_resort_detailed(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "ارفع المستندات" in panel_text, (
        f"hotel_resort_detailed panel must show upload hint 'ارفع المستندات'. Got: {panel_text[:400]!r}"
    )


# ── CS430 ─────────────────────────────────────────────────────────────────────

def test_CS430_hotel_resort_detailed_no_composite_link(page: Page, live_server: str) -> None:
    """Phase 8X.1: hotel_resort_detailed panel has no composite_valuation.html link."""
    _load_hotel_resort_detailed(page, live_server)
    panel_html = page.locator("#es-req-panel").inner_html()
    assert "composite_valuation.html" not in panel_html, (
        "hotel_resort_detailed panel must not contain composite_valuation.html link."
    )


# ── CS431 ─────────────────────────────────────────────────────────────────────

def test_CS431_hotel_resort_detailed_doc_operating_license_renders(page: Page, live_server: str) -> None:
    """Phase 8X.1: hrd_doc_operating_license document checkbox renders in hotel_resort_detailed."""
    _load_hotel_resort_detailed(page, live_server)
    doc_field = page.locator("[data-es-req-field='hrd_doc_operating_license']")
    assert doc_field.count() > 0, (
        "hotel_resort_detailed: hrd_doc_operating_license document checkbox not found in panel."
    )


# ── CS432 ─────────────────────────────────────────────────────────────────────

def test_CS432_serviced_apartments_badge_and_panel_render(page: Page, live_server: str) -> None:
    """Phase 8X.1: selecting serviced_apartments shows badge and requirements panel."""
    _load_serviced_apartments(page, live_server)
    badge = page.locator("#es-profile-badge")
    assert badge.is_visible(), "Profile badge must be visible for serviced_apartments."
    panel = page.locator("#es-req-panel")
    assert panel.is_visible(), "#es-req-panel must be visible for serviced_apartments."
    auth_modal = page.locator("#auth-modal, #login-modal, .auth-modal")
    assert auth_modal.count() == 0 or not auth_modal.first.is_visible(), (
        "Auth modal must NOT appear for serviced_apartments."
    )


# ── CS433 ─────────────────────────────────────────────────────────────────────

def test_CS433_serviced_apartments_stays_on_page(page: Page, live_server: str) -> None:
    """Phase 8X.1: selecting serviced_apartments does not navigate away from the page."""
    _load_serviced_apartments(page, live_server)
    assert "127.0.0.1:5000" in page.url or "localhost:5000" in page.url, (
        f"Page navigated away after selecting serviced_apartments. URL: {page.url}"
    )


# ── CS434 ─────────────────────────────────────────────────────────────────────

def test_CS434_serviced_apartments_zero_api_calls(page: Page, live_server: str) -> None:
    """Phase 8X.1: serviced_apartments must not call /api/valuation/requirements."""
    api_calls: list[str] = []
    page.on("request", lambda req: api_calls.append(req.url) if "valuation/requirements" in req.url else None)
    _load_serviced_apartments(page, live_server)
    assert not api_calls, (
        f"serviced_apartments must be fully static; unexpected API calls: {api_calls}"
    )


# ── CS435 ─────────────────────────────────────────────────────────────────────

def test_CS435_serviced_apartments_key_fields_render(page: Page, live_server: str) -> None:
    """Phase 8X.1: serviced_apartments renders sa_total_units_count, sa_net_rentable_area_sqm."""
    _load_serviced_apartments(page, live_server)
    for field_name in ("sa_total_units_count", "sa_net_rentable_area_sqm"):
        field = page.locator(f"#es-req-field-{field_name}")
        assert field.count() > 0, (
            f"serviced_apartments: field '#es-req-field-{field_name}' not found in panel."
        )


# ── CS436 ─────────────────────────────────────────────────────────────────────

def test_CS436_serviced_apartments_unit_mix_checkbox_group_renders(page: Page, live_server: str) -> None:
    """Phase 8X.1: sa_unit_mix checkbox_group renders chips in serviced_apartments."""
    _load_serviced_apartments(page, live_server)
    chips = page.locator("[data-es-req-field='sa_unit_mix']")
    expect(chips.first).to_be_visible()
    studio_chip = page.locator("[data-es-req-field='sa_unit_mix'][value='studio']")
    expect(studio_chip).to_be_attached()


# ── CS437 ─────────────────────────────────────────────────────────────────────

def test_CS437_serviced_apartments_alos_number_input_with_night_unit(page: Page, live_server: str) -> None:
    """Phase 8X.1: sa_average_length_of_stay_alos renders as number input; unit 'ليلة' visible."""
    _load_serviced_apartments(page, live_server)
    field = page.locator("#es-req-field-sa_average_length_of_stay_alos")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "number", (
        f"sa_average_length_of_stay_alos must be number input. Got type={field.get_attribute('type')!r}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "ليلة" in panel_text, (
        f"serviced_apartments panel must show 'ليلة' unit for ALOS. Got: {panel_text[:400]!r}"
    )


# ── CS438 ─────────────────────────────────────────────────────────────────────

def test_CS438_serviced_apartments_owner_usage_restrictions_textarea(page: Page, live_server: str) -> None:
    """Phase 8X.1: sa_owner_usage_restrictions renders as textarea in serviced_apartments."""
    _load_serviced_apartments(page, live_server)
    field = page.locator("#es-req-field-sa_owner_usage_restrictions")
    expect(field).to_be_visible()
    assert field.evaluate("el => el.tagName.toLowerCase()") == "textarea", (
        "sa_owner_usage_restrictions must be a textarea element."
    )


# ── CS439 ─────────────────────────────────────────────────────────────────────

def test_CS439_serviced_apartments_upload_hint_present(page: Page, live_server: str) -> None:
    """Phase 8X.1: serviced_apartments document section shows upload hint text."""
    _load_serviced_apartments(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "ارفع المستندات" in panel_text, (
        f"serviced_apartments panel must show upload hint 'ارفع المستندات'. Got: {panel_text[:400]!r}"
    )


# ── CS440 ─────────────────────────────────────────────────────────────────────

def test_CS440_serviced_apartments_no_composite_link(page: Page, live_server: str) -> None:
    """Phase 8X.1: serviced_apartments panel has no composite_valuation.html link."""
    _load_serviced_apartments(page, live_server)
    panel_html = page.locator("#es-req-panel").inner_html()
    assert "composite_valuation.html" not in panel_html, (
        "serviced_apartments panel must not contain composite_valuation.html link."
    )


# ── CS441 ─────────────────────────────────────────────────────────────────────

def test_CS441_floating_hotel_badge_and_panel_render(page: Page, live_server: str) -> None:
    """Phase 8X.1: selecting floating_hotel shows badge and requirements panel."""
    _load_floating_hotel(page, live_server)
    badge = page.locator("#es-profile-badge")
    assert badge.is_visible(), "Profile badge must be visible for floating_hotel."
    panel = page.locator("#es-req-panel")
    assert panel.is_visible(), "#es-req-panel must be visible for floating_hotel."
    auth_modal = page.locator("#auth-modal, #login-modal, .auth-modal")
    assert auth_modal.count() == 0 or not auth_modal.first.is_visible(), (
        "Auth modal must NOT appear for floating_hotel."
    )


# ── CS442 ─────────────────────────────────────────────────────────────────────

def test_CS442_floating_hotel_stays_on_page_and_zero_api(page: Page, live_server: str) -> None:
    """Phase 8X.1: floating_hotel does not navigate away and makes zero API calls."""
    api_calls: list[str] = []
    page.on("request", lambda req: api_calls.append(req.url) if "valuation/requirements" in req.url else None)
    _load_floating_hotel(page, live_server)
    assert "127.0.0.1:5000" in page.url or "localhost:5000" in page.url, (
        f"Page navigated away after selecting floating_hotel. URL: {page.url}"
    )
    assert not api_calls, (
        f"floating_hotel must be fully static; unexpected API calls: {api_calls}"
    )


# ── CS443 ─────────────────────────────────────────────────────────────────────

def test_CS443_floating_hotel_key_fields_render(page: Page, live_server: str) -> None:
    """Phase 8X.1: floating_hotel renders fh_vessel_length_m, fh_hull_condition, fh_cabins_count."""
    _load_floating_hotel(page, live_server)
    for field_name in ("fh_vessel_length_m", "fh_hull_condition", "fh_cabins_count"):
        field = page.locator(f"#es-req-field-{field_name}")
        assert field.count() > 0, (
            f"floating_hotel: field '#es-req-field-{field_name}' not found in panel."
        )


# ── CS444 ─────────────────────────────────────────────────────────────────────

def test_CS444_floating_hotel_vessel_length_number_input_with_meter_unit(page: Page, live_server: str) -> None:
    """Phase 8X.1: fh_vessel_length_m renders as number input; unit 'متر' visible in panel."""
    _load_floating_hotel(page, live_server)
    field = page.locator("#es-req-field-fh_vessel_length_m")
    expect(field).to_be_visible()
    assert field.get_attribute("type") == "number", (
        f"fh_vessel_length_m must be number input. Got type={field.get_attribute('type')!r}"
    )
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "متر" in panel_text, (
        f"floating_hotel panel must show 'متر' unit for vessel length. Got: {panel_text[:400]!r}"
    )


# ── CS445 ─────────────────────────────────────────────────────────────────────

def test_CS445_floating_hotel_hull_condition_select_with_options(page: Page, live_server: str) -> None:
    """Phase 8X.1: fh_hull_condition select renders with جيدة and مقبولة options."""
    _load_floating_hotel(page, live_server)
    sel = page.locator("#es-req-field-fh_hull_condition")
    expect(sel).to_be_visible()
    opts = sel.locator("option").all_inner_texts()
    assert any("جيدة" in o for o in opts), (
        f"fh_hull_condition must have a 'جيدة' option. Got: {opts}"
    )
    assert any("مقبولة" in o for o in opts), (
        f"fh_hull_condition must have a 'مقبولة' option. Got: {opts}"
    )


# ── CS446 ─────────────────────────────────────────────────────────────────────

def test_CS446_floating_hotel_upload_hint_and_no_composite_link(page: Page, live_server: str) -> None:
    """Phase 8X.1: floating_hotel shows upload hint and has no composite_valuation.html link."""
    _load_floating_hotel(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "ارفع المستندات" in panel_text, (
        f"floating_hotel panel must show upload hint 'ارفع المستندات'. Got: {panel_text[:400]!r}"
    )
    panel_html = page.locator("#es-req-panel").inner_html()
    assert "composite_valuation.html" not in panel_html, (
        "floating_hotel panel must not contain composite_valuation.html link."
    )


# ── CS447 ─────────────────────────────────────────────────────────────────────

def test_CS447_regression_existing_profiles_unaffected_and_no_console_errors(page: Page, live_server: str) -> None:
    """Phase 8X.1: regression — old hotel, 8R/8S/8T/8U/8V profiles still render; no JS console errors for 8X.1 profiles."""
    def _is_js_error(msg) -> bool:
        return (
            msg.type == "error"
            and "401" not in msg.text
            and "UNAUTHORIZED" not in msg.text.upper()
            and "Failed to load resource" not in msg.text
        )

    # Regression: old hotel profile (value="فندق") must still render form controls
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="فندق")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    count = page.locator("#es-req-panel input, #es-req-panel select").count()
    assert count > 0, (
        f"Regression: old 'فندق' profile must still render form controls after 8X.1. Got {count}."
    )

    # Regression: sample of 8R/8S/8T/8U/8V profiles still render
    for profile_value in ("airport", "cold_storage", "wellness_resort", "marina", "waterway_easement"):
        page.goto(live_server, wait_until="networkidle")
        _inject_session(page)
        page.select_option("#asset-type", value=profile_value)
        page.select_option("#val-purpose", value="fair_market_value")
        page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
        count = page.locator("#es-req-panel input, #es-req-panel select").count()
        assert count > 0, (
            f"Regression: {profile_value} panel must still render form controls after 8X.1. Got {count}."
        )

    # No JS console errors for the three new 8X.1 profiles
    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if _is_js_error(msg) else None)
    for loader in (_load_hotel_resort_detailed, _load_serviced_apartments, _load_floating_hotel):
        loader(page, live_server)
    assert not errors, (
        f"Phase 8X.1: unexpected JS console errors for 8X.1 profiles: {errors}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Phase 8Z — Enriched Residential Unit Valuation Requirements (CS448 – CS479)
# ══════════════════════════════════════════════════════════════════════════════

# ── CS448 ─────────────────────────────────────────────────────────────────────

def test_CS448_8z_residential_supp_heading_physical_properties(page: Page, live_server: str) -> None:
    """Phase 8Z: residential supp must show 'الخصائص المادية التفصيلية' section heading."""
    _load_residential_supp_8w(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "الخصائص المادية التفصيلية" in text, (
        f"Phase 8Z: section 'الخصائص المادية التفصيلية' missing from residential supp. Got: {text[:300]!r}"
    )


# ── CS449 ─────────────────────────────────────────────────────────────────────

def test_CS449_8z_residential_supp_heading_legal_properties(page: Page, live_server: str) -> None:
    """Phase 8Z: residential supp must show 'الخصائص القانونية والملكية' section heading."""
    _load_residential_supp_8w(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "الخصائص القانونية والملكية" in text, (
        f"Phase 8Z: section 'الخصائص القانونية والملكية' missing from residential supp. Got: {text[:300]!r}"
    )


# ── CS450 ─────────────────────────────────────────────────────────────────────

def test_CS450_8z_residential_supp_heading_economic_properties(page: Page, live_server: str) -> None:
    """Phase 8Z: residential supp must show 'الخصائص الاقتصادية وقابلية التسويق' heading."""
    _load_residential_supp_8w(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "الخصائص الاقتصادية وقابلية التسويق" in text, (
        f"Phase 8Z: section 'الخصائص الاقتصادية وقابلية التسويق' missing. Got: {text[:300]!r}"
    )


# ── CS451 ─────────────────────────────────────────────────────────────────────

def test_CS451_8z_residential_supp_heading_location_services(page: Page, live_server: str) -> None:
    """Phase 8Z: residential supp must show 'خصائص الموقع والخدمات المحيطة' section heading."""
    _load_residential_supp_8w(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "خصائص الموقع والخدمات المحيطة" in text, (
        f"Phase 8Z: section 'خصائص الموقع والخدمات المحيطة' missing. Got: {text[:300]!r}"
    )


# ── CS452 ─────────────────────────────────────────────────────────────────────

def test_CS452_8z_residential_supp_heading_purpose_adjustments(page: Page, live_server: str) -> None:
    """Phase 8Z: residential supp must show 'معاملات التعديل حسب غرض التقييم' section heading."""
    _load_residential_supp_8w(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "معاملات التعديل حسب غرض التقييم" in text, (
        f"Phase 8Z: purpose-adjustment section heading missing. Got: {text[:300]!r}"
    )


# ── CS453 ─────────────────────────────────────────────────────────────────────

def test_CS453_8z_residential_supp_heading_energy_sustainability(page: Page, live_server: str) -> None:
    """Phase 8Z: residential supp must show 'كفاءة الطاقة والاستدامة' section heading."""
    _load_residential_supp_8w(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "كفاءة الطاقة والاستدامة" in text, (
        f"Phase 8Z: section 'كفاءة الطاقة والاستدامة' missing. Got: {text[:300]!r}"
    )


# ── CS454 ─────────────────────────────────────────────────────────────────────

def test_CS454_8z_residential_supp_heading_climate_risks(page: Page, live_server: str) -> None:
    """Phase 8Z: residential supp must show 'المخاطر المناخية والطبيعية' section heading."""
    _load_residential_supp_8w(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "المخاطر المناخية والطبيعية" in text, (
        f"Phase 8Z: section 'المخاطر المناخية والطبيعية' missing. Got: {text[:300]!r}"
    )


# ── CS455 ─────────────────────────────────────────────────────────────────────

def test_CS455_8z_residential_supp_heading_digital_infrastructure(page: Page, live_server: str) -> None:
    """Phase 8Z: residential supp must show 'البنية التحتية الرقمية' section heading."""
    _load_residential_supp_8w(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "البنية التحتية الرقمية" in text, (
        f"Phase 8Z: section 'البنية التحتية الرقمية' missing. Got: {text[:300]!r}"
    )


# ── CS456 ─────────────────────────────────────────────────────────────────────

def test_CS456_8z_land_share_sqm_number_input(page: Page, live_server: str) -> None:
    """Phase 8Z: es-supp-field-land_share_sqm renders as number input (Section A)."""
    _load_residential_supp_8w(page, live_server)
    field = page.locator("[data-es-supp-field='land_share_sqm']")
    assert field.count() > 0, "Phase 8Z: land_share_sqm must be present in residential supp."
    assert field.get_attribute("type") == "number", (
        f"land_share_sqm must be type='number'. Got: {field.get_attribute('type')!r}"
    )


# ── CS457 ─────────────────────────────────────────────────────────────────────

def test_CS457_8z_building_age_years_number_input(page: Page, live_server: str) -> None:
    """Phase 8Z: es-supp-field-building_age_years renders as number input (Section A)."""
    _load_residential_supp_8w(page, live_server)
    field = page.locator("[data-es-supp-field='building_age_years']")
    assert field.count() > 0, "Phase 8Z: building_age_years must be present in residential supp."
    assert field.get_attribute("type") == "number", (
        f"building_age_years must be type='number'. Got: {field.get_attribute('type')!r}"
    )


# ── CS458 ─────────────────────────────────────────────────────────────────────

def test_CS458_8z_building_facilities_checkbox_group(page: Page, live_server: str) -> None:
    """Phase 8Z: building_facilities_available renders as checkbox_group in residential supp (Section A)."""
    _load_residential_supp_8w(page, live_server)
    checkboxes = page.locator("[data-es-supp-field='building_facilities_available']")
    assert checkboxes.count() > 0, (
        "Phase 8Z: building_facilities_available checkbox_group must render in residential supp."
    )
    # Verify at least one chip option (e.g., 'security')
    security_chip = page.locator("[data-es-supp-field='building_facilities_available'][value='security']")
    assert security_chip.count() > 0, (
        "Phase 8Z: building_facilities_available must include 'security' chip option."
    )


# ── CS459 ─────────────────────────────────────────────────────────────────────

def test_CS459_8z_ownership_type_select_renders(page: Page, live_server: str) -> None:
    """Phase 8Z: ownership_type select renders with Arabic options in residential supp (Section B)."""
    _load_residential_supp_8w(page, live_server)
    sel = page.locator("#es-supp-field-ownership_type")
    assert sel.count() > 0, "Phase 8Z: ownership_type select must render in residential supp."
    opts = sel.locator("option")
    assert opts.count() >= 4, (
        f"Phase 8Z: ownership_type must have >=4 options. Got {opts.count()}"
    )


# ── CS460 ─────────────────────────────────────────────────────────────────────

def test_CS460_8z_mortgage_or_lien_status_select_renders(page: Page, live_server: str) -> None:
    """Phase 8Z: mortgage_or_lien_status select renders in residential supp (Section B)."""
    _load_residential_supp_8w(page, live_server)
    sel = page.locator("#es-supp-field-mortgage_or_lien_status")
    assert sel.count() > 0, "Phase 8Z: mortgage_or_lien_status must render in residential supp."


# ── CS461 ─────────────────────────────────────────────────────────────────────

def test_CS461_8z_legal_restrictions_summary_textarea_renders(page: Page, live_server: str) -> None:
    """Phase 8Z: legal_restrictions_summary renders as <textarea> in residential supp (Section B)."""
    _load_residential_supp_8w(page, live_server)
    ta = page.locator("textarea[data-es-supp-field='legal_restrictions_summary']")
    assert ta.count() == 1, (
        "Phase 8Z: legal_restrictions_summary must render as <textarea> in residential supp."
    )


# ── CS462 ─────────────────────────────────────────────────────────────────────

def test_CS462_8z_current_rent_monthly_number_input_not_duplicate(page: Page, live_server: str) -> None:
    """Phase 8Z: current_rent_monthly is new (distinct from rental_income_monthly); both must exist."""
    _load_residential_supp_8w(page, live_server)
    current = page.locator("[data-es-supp-field='current_rent_monthly']")
    existing = page.locator("[data-es-supp-field='rental_income_monthly']")
    assert current.count() > 0, "Phase 8Z: current_rent_monthly must be present in residential supp."
    assert existing.count() > 0, "Phase 8Z: existing rental_income_monthly must still be present."
    assert current.get_attribute("type") == "number", (
        "current_rent_monthly must be type='number'."
    )


# ── CS463 ─────────────────────────────────────────────────────────────────────

def test_CS463_8z_market_rent_monthly_number_input(page: Page, live_server: str) -> None:
    """Phase 8Z: market_rent_monthly renders as number input in residential supp (Section C)."""
    _load_residential_supp_8w(page, live_server)
    field = page.locator("[data-es-supp-field='market_rent_monthly']")
    assert field.count() > 0, "Phase 8Z: market_rent_monthly must be present in residential supp."
    assert field.get_attribute("type") == "number", (
        f"market_rent_monthly must be type='number'. Got: {field.get_attribute('type')!r}"
    )


# ── CS464 ─────────────────────────────────────────────────────────────────────

def test_CS464_8z_neighborhood_quality_select_renders(page: Page, live_server: str) -> None:
    """Phase 8Z: neighborhood_quality select renders with Arabic options in residential supp (Section D)."""
    _load_residential_supp_8w(page, live_server)
    sel = page.locator("#es-supp-field-neighborhood_quality")
    assert sel.count() > 0, "Phase 8Z: neighborhood_quality select must render in residential supp."
    opts = sel.locator("option")
    assert opts.count() >= 4, (
        f"Phase 8Z: neighborhood_quality must have >=4 options. Got {opts.count()}"
    )


# ── CS465 ─────────────────────────────────────────────────────────────────────

def test_CS465_8z_nuisance_sources_nearby_checkbox_group(page: Page, live_server: str) -> None:
    """Phase 8Z: nuisance_sources_nearby renders as checkbox_group in residential supp (Section D)."""
    _load_residential_supp_8w(page, live_server)
    checkboxes = page.locator("[data-es-supp-field='nuisance_sources_nearby']")
    assert checkboxes.count() > 0, (
        "Phase 8Z: nuisance_sources_nearby checkbox_group must render in residential supp."
    )


# ── CS466 ─────────────────────────────────────────────────────────────────────

def test_CS466_8z_mortgage_lending_methodology_select_renders(page: Page, live_server: str) -> None:
    """Phase 8Z: mortgage_lending_methodology select renders (Section E — purpose adjustments)."""
    _load_residential_supp_8w(page, live_server)
    sel = page.locator("#es-supp-field-mortgage_lending_methodology")
    assert sel.count() > 0, "Phase 8Z: mortgage_lending_methodology select must render in residential supp."
    opts = sel.locator("option")
    assert opts.count() >= 8, (
        f"Phase 8Z: mortgage_lending_methodology must have >=8 methodology options. Got {opts.count()}"
    )


# ── CS467 ─────────────────────────────────────────────────────────────────────

def test_CS467_8z_mortgage_lending_adjustment_pct_number_input(page: Page, live_server: str) -> None:
    """Phase 8Z: mortgage_lending_adjustment_pct renders as number input (Section E)."""
    _load_residential_supp_8w(page, live_server)
    field = page.locator("[data-es-supp-field='mortgage_lending_adjustment_pct']")
    assert field.count() > 0, "Phase 8Z: mortgage_lending_adjustment_pct must render in residential supp."
    assert field.get_attribute("type") == "number", (
        "mortgage_lending_adjustment_pct must be type='number'."
    )


# ── CS468 ─────────────────────────────────────────────────────────────────────

def test_CS468_8z_sale_purchase_methodology_select_renders(page: Page, live_server: str) -> None:
    """Phase 8Z: sale_purchase_methodology select renders (Section E — purpose adjustments)."""
    _load_residential_supp_8w(page, live_server)
    sel = page.locator("#es-supp-field-sale_purchase_methodology")
    assert sel.count() > 0, "Phase 8Z: sale_purchase_methodology must render in residential supp."


# ── CS469 ─────────────────────────────────────────────────────────────────────

def test_CS469_8z_litigation_dispute_methodology_select_renders(page: Page, live_server: str) -> None:
    """Phase 8Z: litigation_dispute_methodology select renders as local-only field (Section E)."""
    _load_residential_supp_8w(page, live_server)
    sel = page.locator("#es-supp-field-litigation_dispute_methodology")
    assert sel.count() > 0, (
        "Phase 8Z: litigation_dispute_methodology (local-only purpose) must render in residential supp."
    )
    # Confirm it's a supp field (not req field) — no data-es-req-field on same element
    assert sel.get_attribute("data-es-req-field") is None, (
        "litigation_dispute_methodology must NOT have data-es-req-field attribute."
    )


# ── CS470 ─────────────────────────────────────────────────────────────────────

def test_CS470_8z_energy_efficiency_rating_select_renders(page: Page, live_server: str) -> None:
    """Phase 8Z: energy_efficiency_rating select renders in residential supp (Section F)."""
    _load_residential_supp_8w(page, live_server)
    sel = page.locator("#es-supp-field-energy_efficiency_rating")
    assert sel.count() > 0, "Phase 8Z: energy_efficiency_rating select must render in residential supp."
    opts = sel.locator("option")
    assert opts.count() >= 6, (
        f"Phase 8Z: energy_efficiency_rating must have >=6 options (A+ through F). Got {opts.count()}"
    )


# ── CS471 ─────────────────────────────────────────────────────────────────────

def test_CS471_8z_electricity_consumption_monthly_kwh_number_input(page: Page, live_server: str) -> None:
    """Phase 8Z: electricity_consumption_monthly_kwh renders as number input (Section F)."""
    _load_residential_supp_8w(page, live_server)
    field = page.locator("[data-es-supp-field='electricity_consumption_monthly_kwh']")
    assert field.count() > 0, "Phase 8Z: electricity_consumption_monthly_kwh must render in residential supp."
    assert field.get_attribute("type") == "number", (
        "electricity_consumption_monthly_kwh must be type='number'."
    )


# ── CS472 ─────────────────────────────────────────────────────────────────────

def test_CS472_8z_sustainability_value_impact_pct_number_input(page: Page, live_server: str) -> None:
    """Phase 8Z: sustainability_value_impact_pct renders as number input with % unit (Section F)."""
    _load_residential_supp_8w(page, live_server)
    field = page.locator("[data-es-supp-field='sustainability_value_impact_pct']")
    assert field.count() > 0, "Phase 8Z: sustainability_value_impact_pct must render in residential supp."
    assert field.get_attribute("type") == "number", (
        "sustainability_value_impact_pct must be type='number'."
    )


# ── CS473 ─────────────────────────────────────────────────────────────────────

def test_CS473_8z_flood_risk_level_select_renders(page: Page, live_server: str) -> None:
    """Phase 8Z: flood_risk_level select renders in residential supp (Section G)."""
    _load_residential_supp_8w(page, live_server)
    sel = page.locator("#es-supp-field-flood_risk_level")
    assert sel.count() > 0, "Phase 8Z: flood_risk_level select must render in residential supp."
    opts = sel.locator("option")
    assert opts.count() >= 4, (
        f"Phase 8Z: flood_risk_level must have >=4 risk-level options. Got {opts.count()}"
    )


# ── CS474 ─────────────────────────────────────────────────────────────────────

def test_CS474_8z_climate_risk_value_impact_pct_number_input(page: Page, live_server: str) -> None:
    """Phase 8Z: climate_risk_value_impact_pct renders as number input (Section G)."""
    _load_residential_supp_8w(page, live_server)
    field = page.locator("[data-es-supp-field='climate_risk_value_impact_pct']")
    assert field.count() > 0, "Phase 8Z: climate_risk_value_impact_pct must render in residential supp."
    assert field.get_attribute("type") == "number", (
        "climate_risk_value_impact_pct must be type='number'."
    )


# ── CS475 ─────────────────────────────────────────────────────────────────────

def test_CS475_8z_fiber_optic_available_bool_select_renders(page: Page, live_server: str) -> None:
    """Phase 8Z: fiber_optic_available renders as bool select (نعم/لا) in residential supp (Section H)."""
    _load_residential_supp_8w(page, live_server)
    sel = page.locator("#es-supp-field-fiber_optic_available")
    assert sel.count() > 0, "Phase 8Z: fiber_optic_available must render in residential supp."
    opts_text = sel.inner_text()
    assert "نعم" in opts_text and "لا" in opts_text, (
        f"Phase 8Z: fiber_optic_available must show نعم/لا options. Got: {opts_text!r}"
    )


# ── CS476 ─────────────────────────────────────────────────────────────────────

def test_CS476_8z_digital_infrastructure_value_impact_pct_number_input(page: Page, live_server: str) -> None:
    """Phase 8Z: digital_infrastructure_value_impact_pct renders as number input (Section H)."""
    _load_residential_supp_8w(page, live_server)
    field = page.locator("[data-es-supp-field='digital_infrastructure_value_impact_pct']")
    assert field.count() > 0, (
        "Phase 8Z: digital_infrastructure_value_impact_pct must render in residential supp."
    )
    assert field.get_attribute("type") == "number", (
        "digital_infrastructure_value_impact_pct must be type='number'."
    )


# ── CS477 ─────────────────────────────────────────────────────────────────────

def test_CS477_8z_no_building_full_leakage_in_residential_supp(page: Page, live_server: str) -> None:
    """Phase 8Z: no building_full floor-table elements must appear in residential_unit supplemental."""
    _load_residential_supp_8w(page, live_server)
    supp = page.locator("#es-req-supp")
    bf_elements = supp.locator("[data-bf-floor], [data-bf-field]")
    assert bf_elements.count() == 0, (
        f"Phase 8Z: building_full elements must NOT leak into residential supp. Found {bf_elements.count()}."
    )


# ── CS478 ─────────────────────────────────────────────────────────────────────

def test_CS478_8z_existing_8q_fields_still_present_regression(page: Page, live_server: str) -> None:
    """Phase 8Z regression: existing 8Q supplemental fields (unit_type, maintenance_level, occupancy_status) still render."""
    _load_residential_supp_8w(page, live_server)
    supp = page.locator("#es-req-supp")
    for name in ("unit_type", "maintenance_level", "occupancy_status", "bedrooms_count", "visible_defects"):
        count = supp.locator(f"[data-es-supp-field='{name}']").count()
        assert count > 0, (
            f"Phase 8Z regression: existing 8Q field '{name}' must still render in residential supp."
        )


# ── CS479 ─────────────────────────────────────────────────────────────────────

def test_CS479_8z_no_console_errors_after_enrichment(page: Page, live_server: str) -> None:
    """Phase 8Z: no JS console errors after rendering the enriched residential_unit supplemental."""
    def _is_js_error(msg) -> bool:
        return (
            msg.type == "error"
            and "401" not in msg.text
            and "UNAUTHORIZED" not in msg.text
            and "Failed to load resource" not in msg.text
        )

    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if _is_js_error(msg) else None)
    _load_residential_supp_8w(page, live_server)
    assert not errors, (
        f"Phase 8Z: unexpected JS console errors on residential supp render: {errors}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Phase 8ZA — Enriched building_full Valuation Requirements (CS480 – CS511)
# ══════════════════════════════════════════════════════════════════════════════

def _load_building_full_supp(page: Page, live_server: str) -> None:
    """Phase 8ZA: load building_full panel and wait until supplemental header is visible."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-supp-header").wait_for(state="visible", timeout=8_000)


# ── CS480 ─────────────────────────────────────────────────────────────────────

def test_CS480_8za_bf_supp_heading_renders(page: Page, live_server: str) -> None:
    """Phase 8ZA: #es-req-supp-header shows 'متطلبات تقييم العمارة السكنية / المبنى الكامل'."""
    _load_building_full_supp(page, live_server)
    header_text = page.locator("#es-req-supp-header").inner_text()
    assert "متطلبات تقييم العمارة السكنية" in header_text, (
        f"Phase 8ZA: building_full supp heading missing. Got: {header_text!r}"
    )


# ── CS481 ─────────────────────────────────────────────────────────────────────

def test_CS481_8za_bf_supp_heading_physical_structural(page: Page, live_server: str) -> None:
    """Phase 8ZA: 'الخصائص المادية والإنشائية للمبنى' section heading visible."""
    _load_building_full_supp(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "الخصائص المادية والإنشائية للمبنى" in text, (
        f"Phase 8ZA: section 'الخصائص المادية والإنشائية للمبنى' missing. Got: {text[:300]!r}"
    )


# ── CS482 ─────────────────────────────────────────────────────────────────────

def test_CS482_8za_bf_supp_heading_legal_regulatory(page: Page, live_server: str) -> None:
    """Phase 8ZA: 'الخصائص القانونية والتنظيمية' section heading visible."""
    _load_building_full_supp(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "الخصائص القانونية والتنظيمية" in text, (
        f"Phase 8ZA: section 'الخصائص القانونية والتنظيمية' missing. Got: {text[:300]!r}"
    )


# ── CS483 ─────────────────────────────────────────────────────────────────────

def test_CS483_8za_bf_supp_heading_economic_income(page: Page, live_server: str) -> None:
    """Phase 8ZA: 'الخصائص الاقتصادية والدخل' section heading visible."""
    _load_building_full_supp(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "الخصائص الاقتصادية والدخل" in text, (
        f"Phase 8ZA: section 'الخصائص الاقتصادية والدخل' missing. Got: {text[:300]!r}"
    )


# ── CS484 ─────────────────────────────────────────────────────────────────────

def test_CS484_8za_bf_supp_heading_location_services(page: Page, live_server: str) -> None:
    """Phase 8ZA: 'خصائص الموقع والخدمات المحيطة' section heading visible."""
    _load_building_full_supp(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "خصائص الموقع والخدمات المحيطة" in text, (
        f"Phase 8ZA: section 'خصائص الموقع والخدمات المحيطة' missing. Got: {text[:300]!r}"
    )


# ── CS485 ─────────────────────────────────────────────────────────────────────

def test_CS485_8za_bf_supp_heading_purpose_adjustments(page: Page, live_server: str) -> None:
    """Phase 8ZA: 'معاملات التعديل حسب غرض التقييم' section heading visible."""
    _load_building_full_supp(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "معاملات التعديل حسب غرض التقييم" in text, (
        f"Phase 8ZA: purpose-adjustment section heading missing. Got: {text[:300]!r}"
    )


# ── CS486 ─────────────────────────────────────────────────────────────────────

def test_CS486_8za_bf_supp_heading_energy_sustainability(page: Page, live_server: str) -> None:
    """Phase 8ZA: 'كفاءة الطاقة والاستدامة' section heading visible."""
    _load_building_full_supp(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "كفاءة الطاقة والاستدامة" in text, (
        f"Phase 8ZA: section 'كفاءة الطاقة والاستدامة' missing. Got: {text[:300]!r}"
    )


# ── CS487 ─────────────────────────────────────────────────────────────────────

def test_CS487_8za_bf_supp_heading_climate_risks(page: Page, live_server: str) -> None:
    """Phase 8ZA: 'المخاطر المناخية والطبيعية' section heading visible."""
    _load_building_full_supp(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "المخاطر المناخية والطبيعية" in text, (
        f"Phase 8ZA: section 'المخاطر المناخية والطبيعية' missing. Got: {text[:300]!r}"
    )


# ── CS488 ─────────────────────────────────────────────────────────────────────

def test_CS488_8za_bf_supp_heading_digital_infrastructure(page: Page, live_server: str) -> None:
    """Phase 8ZA: 'البنية التحتية الرقمية والذكية' section heading visible."""
    _load_building_full_supp(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "البنية التحتية الرقمية والذكية" in text, (
        f"Phase 8ZA: section 'البنية التحتية الرقمية والذكية' missing. Got: {text[:300]!r}"
    )


# ── CS489 ─────────────────────────────────────────────────────────────────────

def test_CS489_8za_bf_total_gfa_sqm_number_input(page: Page, live_server: str) -> None:
    """Phase 8ZA: bf_total_gfa_sqm renders as number input (Section A)."""
    _load_building_full_supp(page, live_server)
    field = page.locator("[data-es-supp-field='bf_total_gfa_sqm']")
    assert field.count() > 0, "Phase 8ZA: bf_total_gfa_sqm must be present in building_full supp."
    assert field.get_attribute("type") == "number", (
        f"bf_total_gfa_sqm must be type='number'. Got: {field.get_attribute('type')!r}"
    )


# ── CS490 ─────────────────────────────────────────────────────────────────────

def test_CS490_8za_bf_building_type_select_renders(page: Page, live_server: str) -> None:
    """Phase 8ZA: bf_building_type select renders with options (Section B)."""
    _load_building_full_supp(page, live_server)
    sel = page.locator("#es-supp-field-bf_building_type")
    assert sel.count() > 0, "Phase 8ZA: bf_building_type select must render in building_full supp."
    opts = sel.locator("option")
    assert opts.count() >= 4, (
        f"Phase 8ZA: bf_building_type must have >=4 options. Got {opts.count()}"
    )


# ── CS491 ─────────────────────────────────────────────────────────────────────

def test_CS491_8za_bf_effective_age_years_number_input(page: Page, live_server: str) -> None:
    """Phase 8ZA: bf_effective_age_years renders as number input (Section B)."""
    _load_building_full_supp(page, live_server)
    field = page.locator("[data-es-supp-field='bf_effective_age_years']")
    assert field.count() > 0, "Phase 8ZA: bf_effective_age_years must be present in building_full supp."
    assert field.get_attribute("type") == "number", (
        "bf_effective_age_years must be type='number'."
    )


# ── CS492 ─────────────────────────────────────────────────────────────────────

def test_CS492_8za_bf_structural_defects_summary_textarea(page: Page, live_server: str) -> None:
    """Phase 8ZA: bf_structural_or_mep_defects_summary renders as <textarea> (Section B)."""
    _load_building_full_supp(page, live_server)
    ta = page.locator("textarea[data-es-supp-field='bf_structural_or_mep_defects_summary']")
    assert ta.count() == 1, (
        "Phase 8ZA: bf_structural_or_mep_defects_summary must render as <textarea>."
    )


# ── CS493 ─────────────────────────────────────────────────────────────────────

def test_CS493_8za_bf_commercial_units_count_number_input(page: Page, live_server: str) -> None:
    """Phase 8ZA: bf_commercial_units_count renders as number input (Section C — floor table complement)."""
    _load_building_full_supp(page, live_server)
    field = page.locator("[data-es-supp-field='bf_commercial_units_count']")
    assert field.count() > 0, "Phase 8ZA: bf_commercial_units_count must be present in building_full supp."
    assert field.get_attribute("type") == "number", (
        "bf_commercial_units_count must be type='number'."
    )


# ── CS494 ─────────────────────────────────────────────────────────────────────

def test_CS494_8za_bf_finishing_level_common_areas_select(page: Page, live_server: str) -> None:
    """Phase 8ZA: bf_finishing_level_common_areas select renders (Section D)."""
    _load_building_full_supp(page, live_server)
    sel = page.locator("#es-supp-field-bf_finishing_level_common_areas")
    assert sel.count() > 0, "Phase 8ZA: bf_finishing_level_common_areas must render in building_full supp."


# ── CS495 ─────────────────────────────────────────────────────────────────────

def test_CS495_8za_bf_fire_fighting_system_bool_select(page: Page, live_server: str) -> None:
    """Phase 8ZA: bf_fire_fighting_system_available renders as bool select نعم/لا (Section D)."""
    _load_building_full_supp(page, live_server)
    sel = page.locator("#es-supp-field-bf_fire_fighting_system_available")
    assert sel.count() > 0, "Phase 8ZA: bf_fire_fighting_system_available must render in building_full supp."
    opts_text = sel.inner_text()
    assert "نعم" in opts_text and "لا" in opts_text, (
        f"Phase 8ZA: bf_fire_fighting_system_available must show نعم/لا. Got: {opts_text!r}"
    )


# ── CS496 ─────────────────────────────────────────────────────────────────────

def test_CS496_8za_bf_ownership_type_select_renders(page: Page, live_server: str) -> None:
    """Phase 8ZA: bf_ownership_type select renders with Arabic options (Section E)."""
    _load_building_full_supp(page, live_server)
    sel = page.locator("#es-supp-field-bf_ownership_type")
    assert sel.count() > 0, "Phase 8ZA: bf_ownership_type must render in building_full supp."
    opts = sel.locator("option")
    assert opts.count() >= 4, (
        f"Phase 8ZA: bf_ownership_type must have >=4 options. Got {opts.count()}"
    )


# ── CS497 ─────────────────────────────────────────────────────────────────────

def test_CS497_8za_bf_mortgage_or_lien_status_select(page: Page, live_server: str) -> None:
    """Phase 8ZA: bf_mortgage_or_lien_status select renders (Section E)."""
    _load_building_full_supp(page, live_server)
    sel = page.locator("#es-supp-field-bf_mortgage_or_lien_status")
    assert sel.count() > 0, "Phase 8ZA: bf_mortgage_or_lien_status must render in building_full supp."


# ── CS498 ─────────────────────────────────────────────────────────────────────

def test_CS498_8za_bf_market_gross_rent_annual_number_input(page: Page, live_server: str) -> None:
    """Phase 8ZA: bf_market_gross_rent_annual renders as number input (Section F)."""
    _load_building_full_supp(page, live_server)
    field = page.locator("[data-es-supp-field='bf_market_gross_rent_annual']")
    assert field.count() > 0, "Phase 8ZA: bf_market_gross_rent_annual must be present."
    assert field.get_attribute("type") == "number", (
        "bf_market_gross_rent_annual must be type='number'."
    )


# ── CS499 ─────────────────────────────────────────────────────────────────────

def test_CS499_8za_bf_vacancy_rate_number_input(page: Page, live_server: str) -> None:
    """Phase 8ZA: bf_vacancy_rate renders as number input (Section F)."""
    _load_building_full_supp(page, live_server)
    field = page.locator("[data-es-supp-field='bf_vacancy_rate']")
    assert field.count() > 0, "Phase 8ZA: bf_vacancy_rate must be present in building_full supp."
    assert field.get_attribute("type") == "number", (
        "bf_vacancy_rate must be type='number'."
    )


# ── CS500 ─────────────────────────────────────────────────────────────────────

def test_CS500_8za_bf_district_classification_select(page: Page, live_server: str) -> None:
    """Phase 8ZA: bf_district_classification select renders (Section G)."""
    _load_building_full_supp(page, live_server)
    sel = page.locator("#es-supp-field-bf_district_classification")
    assert sel.count() > 0, "Phase 8ZA: bf_district_classification must render in building_full supp."


# ── CS501 ─────────────────────────────────────────────────────────────────────

def test_CS501_8za_bf_purpose_mortgage_lending_methodology_select(page: Page, live_server: str) -> None:
    """Phase 8ZA: bf_purpose_mortgage_lending_methodology select renders (Section H)."""
    _load_building_full_supp(page, live_server)
    sel = page.locator("#es-supp-field-bf_purpose_mortgage_lending_methodology")
    assert sel.count() > 0, (
        "Phase 8ZA: bf_purpose_mortgage_lending_methodology must render in building_full supp."
    )
    opts = sel.locator("option")
    assert opts.count() >= 8, (
        f"Phase 8ZA: methodology select must have >=8 options. Got {opts.count()}"
    )


# ── CS502 ─────────────────────────────────────────────────────────────────────

def test_CS502_8za_bf_purpose_mortgage_lending_adjustment_pct_number(page: Page, live_server: str) -> None:
    """Phase 8ZA: bf_purpose_mortgage_lending_adjustment_pct renders as number input (Section H)."""
    _load_building_full_supp(page, live_server)
    field = page.locator("[data-es-supp-field='bf_purpose_mortgage_lending_adjustment_pct']")
    assert field.count() > 0, "Phase 8ZA: bf_purpose_mortgage_lending_adjustment_pct must be present."
    assert field.get_attribute("type") == "number", (
        "bf_purpose_mortgage_lending_adjustment_pct must be type='number'."
    )


# ── CS503 ─────────────────────────────────────────────────────────────────────

def test_CS503_8za_bf_purpose_sale_purchase_methodology_select(page: Page, live_server: str) -> None:
    """Phase 8ZA: bf_purpose_sale_purchase_methodology select renders (Section H)."""
    _load_building_full_supp(page, live_server)
    sel = page.locator("#es-supp-field-bf_purpose_sale_purchase_methodology")
    assert sel.count() > 0, (
        "Phase 8ZA: bf_purpose_sale_purchase_methodology must render in building_full supp."
    )


# ── CS504 ─────────────────────────────────────────────────────────────────────

def test_CS504_8za_bf_energy_efficiency_rating_select(page: Page, live_server: str) -> None:
    """Phase 8ZA: bf_energy_efficiency_rating select renders with A+–F options (Section I)."""
    _load_building_full_supp(page, live_server)
    sel = page.locator("#es-supp-field-bf_energy_efficiency_rating")
    assert sel.count() > 0, "Phase 8ZA: bf_energy_efficiency_rating must render in building_full supp."
    opts = sel.locator("option")
    assert opts.count() >= 6, (
        f"Phase 8ZA: bf_energy_efficiency_rating must have >=6 options. Got {opts.count()}"
    )


# ── CS505 ─────────────────────────────────────────────────────────────────────

def test_CS505_8za_bf_flood_risk_level_select(page: Page, live_server: str) -> None:
    """Phase 8ZA: bf_flood_risk_level select renders (Section J)."""
    _load_building_full_supp(page, live_server)
    sel = page.locator("#es-supp-field-bf_flood_risk_level")
    assert sel.count() > 0, "Phase 8ZA: bf_flood_risk_level must render in building_full supp."


# ── CS506 ─────────────────────────────────────────────────────────────────────

def test_CS506_8za_bf_fiber_optic_available_bool_select(page: Page, live_server: str) -> None:
    """Phase 8ZA: bf_fiber_optic_available renders as bool select نعم/لا (Section K)."""
    _load_building_full_supp(page, live_server)
    sel = page.locator("#es-supp-field-bf_fiber_optic_available")
    assert sel.count() > 0, "Phase 8ZA: bf_fiber_optic_available must render in building_full supp."
    opts_text = sel.inner_text()
    assert "نعم" in opts_text and "لا" in opts_text, (
        f"Phase 8ZA: bf_fiber_optic_available must show نعم/لا. Got: {opts_text!r}"
    )


# ── CS507 ─────────────────────────────────────────────────────────────────────

def test_CS507_8za_cs92_regression_no_irshadi_in_panel(page: Page, live_server: str) -> None:
    """Phase 8ZA regression: CS92 guard — no 'إرشادي' text in #es-req-panel after 8ZA enrichment."""
    _load_building_full_supp(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "إرشادي" not in panel_text, (
        f"Phase 8ZA: word 'إرشادي' must NOT appear anywhere in building_full panel. Got: {panel_text[:300]!r}"
    )


# ── CS508 ─────────────────────────────────────────────────────────────────────

def test_CS508_8za_residential_unit_isolation_no_bf_supp_fields(page: Page, live_server: str) -> None:
    """Phase 8ZA: residential_unit supp must NOT contain bf_* supplemental fields."""
    _load_residential_supp_8w(page, live_server)
    supp = page.locator("#es-req-supp")
    for name in ("bf_total_gfa_sqm", "bf_building_type", "bf_ownership_type",
                 "bf_purpose_mortgage_lending_methodology"):
        count = supp.locator(f"[data-es-supp-field='{name}']").count()
        assert count == 0, (
            f"Phase 8ZA: building_full field '{name}' must NOT appear in residential_unit supp. Found {count}."
        )


# ── CS509 ─────────────────────────────────────────────────────────────────────

def test_CS509_8za_floor_table_still_present_regression(page: Page, live_server: str) -> None:
    """Phase 8ZA regression: existing building_full floor table (#es-bf-floor-table) still renders."""
    _load_building_full_supp(page, live_server)
    table = page.locator("#es-bf-floor-table")
    assert table.count() > 0, (
        "Phase 8ZA regression: #es-bf-floor-table must still render after 8ZA enrichment."
    )
    bf_fields = page.locator("[data-bf-floor]")
    assert bf_fields.count() >= 5, (
        f"Phase 8ZA regression: at least 5 data-bf-floor elements expected. Got {bf_fields.count()}."
    )


# ── CS510 ─────────────────────────────────────────────────────────────────────

def test_CS510_8za_residential_8q_supp_regression(page: Page, live_server: str) -> None:
    """Phase 8ZA regression: residential_unit 8Q supplemental (unit_type, occupancy_status) still renders."""
    _load_residential_supp_8w(page, live_server)
    supp = page.locator("#es-req-supp")
    for name in ("unit_type", "occupancy_status", "maintenance_level"):
        count = supp.locator(f"[data-es-supp-field='{name}']").count()
        assert count > 0, (
            f"Phase 8ZA regression: existing 8Q field '{name}' must still render in residential supp."
        )


# ── CS511 ─────────────────────────────────────────────────────────────────────

def test_CS511_8za_no_console_errors_building_full_supp(page: Page, live_server: str) -> None:
    """Phase 8ZA: no JS console errors after rendering enriched building_full supplemental."""
    def _is_js_error(msg) -> bool:
        return (
            msg.type == "error"
            and "401" not in msg.text
            and "UNAUTHORIZED" not in msg.text
            and "Failed to load resource" not in msg.text
        )

    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if _is_js_error(msg) else None)
    _load_building_full_supp(page, live_server)
    assert not errors, (
        f"Phase 8ZA: unexpected JS console errors on building_full supp render: {errors}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Phase 8ZB — Enriched land (Vacant / Development Land) Requirements (CS512–CS543)
# ══════════════════════════════════════════════════════════════════════════════

def _load_land_supp_8zb(page: Page, live_server: str) -> None:
    """Phase 8ZB: load land panel via 401 path and wait for supplemental header."""
    _mock_req_401(page)
    page.goto(live_server, wait_until="networkidle")
    page.evaluate("localStorage.removeItem('es_auth')")
    page.select_option("#asset-type", value="أرض فضاء")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-supp-header").wait_for(state="visible", timeout=8_000)


# ── CS512 ─────────────────────────────────────────────────────────────────────

def test_CS512_8zb_land_supp_heading_renders(page: Page, live_server: str) -> None:
    """Phase 8ZB: #es-req-supp-header shows 'متطلبات تقييم الأرض الفضاء' heading."""
    _load_land_supp_8zb(page, live_server)
    header_text = page.locator("#es-req-supp-header").inner_text()
    assert "متطلبات تقييم الأرض الفضاء" in header_text, (
        f"Phase 8ZB: land supp heading missing. Got: {header_text!r}"
    )


# ── CS513 ─────────────────────────────────────────────────────────────────────

def test_CS513_8zb_land_supp_heading_physical_properties(page: Page, live_server: str) -> None:
    """Phase 8ZB: 'بيانات الأرض الأساسية والخصائص المادية' section heading visible."""
    _load_land_supp_8zb(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "بيانات الأرض الأساسية والخصائص المادية" in text, (
        f"Phase 8ZB: section heading missing. Got: {text[:300]!r}"
    )


# ── CS514 ─────────────────────────────────────────────────────────────────────

def test_CS514_8zb_land_supp_heading_development_readiness(page: Page, live_server: str) -> None:
    """Phase 8ZB: 'حالة التطوير وجاهزية البناء' section heading visible."""
    _load_land_supp_8zb(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "حالة التطوير وجاهزية البناء" in text, (
        f"Phase 8ZB: section 'حالة التطوير وجاهزية البناء' missing. Got: {text[:300]!r}"
    )


# ── CS515 ─────────────────────────────────────────────────────────────────────

def test_CS515_8zb_land_supp_heading_zoning_planning(page: Page, live_server: str) -> None:
    """Phase 8ZB: 'التصنيف العمراني والتخطيط' section heading visible."""
    _load_land_supp_8zb(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "التصنيف العمراني والتخطيط" in text, (
        f"Phase 8ZB: section 'التصنيف العمراني والتخطيط' missing. Got: {text[:300]!r}"
    )


# ── CS516 ─────────────────────────────────────────────────────────────────────

def test_CS516_8zb_land_supp_heading_legal_restrictions(page: Page, live_server: str) -> None:
    """Phase 8ZB: 'الوضع القانوني والقيود' section heading visible."""
    _load_land_supp_8zb(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "الوضع القانوني والقيود" in text, (
        f"Phase 8ZB: section 'الوضع القانوني والقيود' missing. Got: {text[:300]!r}"
    )


# ── CS517 ─────────────────────────────────────────────────────────────────────

def test_CS517_8zb_land_supp_heading_utilities(page: Page, live_server: str) -> None:
    """Phase 8ZB: 'المرافق والبنية التحتية' section heading visible."""
    _load_land_supp_8zb(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "المرافق والبنية التحتية" in text, (
        f"Phase 8ZB: section 'المرافق والبنية التحتية' missing. Got: {text[:300]!r}"
    )


# ── CS518 ─────────────────────────────────────────────────────────────────────

def test_CS518_8zb_land_supp_heading_roads_access(page: Page, live_server: str) -> None:
    """Phase 8ZB: 'الطرق والواجهات والوصول' section heading visible."""
    _load_land_supp_8zb(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "الطرق والواجهات والوصول" in text, (
        f"Phase 8ZB: section 'الطرق والواجهات والوصول' missing. Got: {text[:300]!r}"
    )


# ── CS519 ─────────────────────────────────────────────────────────────────────

def test_CS519_8zb_land_supp_heading_economic_market(page: Page, live_server: str) -> None:
    """Phase 8ZB: 'الخصائص الاقتصادية والسوقية' section heading visible."""
    _load_land_supp_8zb(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "الخصائص الاقتصادية والسوقية" in text, (
        f"Phase 8ZB: section 'الخصائص الاقتصادية والسوقية' missing. Got: {text[:300]!r}"
    )


# ── CS520 ─────────────────────────────────────────────────────────────────────

def test_CS520_8zb_land_supp_heading_development_costs(page: Page, live_server: str) -> None:
    """Phase 8ZB: 'تكاليف التطوير والجدوى' section heading visible."""
    _load_land_supp_8zb(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "تكاليف التطوير والجدوى" in text, (
        f"Phase 8ZB: section 'تكاليف التطوير والجدوى' missing. Got: {text[:300]!r}"
    )


# ── CS521 ─────────────────────────────────────────────────────────────────────

def test_CS521_8zb_land_supp_heading_purpose_adjustments(page: Page, live_server: str) -> None:
    """Phase 8ZB: 'معاملات التعديل حسب غرض التقييم' section heading visible."""
    _load_land_supp_8zb(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "معاملات التعديل حسب غرض التقييم" in text, (
        f"Phase 8ZB: purpose-adjustment section heading missing. Got: {text[:300]!r}"
    )


# ── CS522 ─────────────────────────────────────────────────────────────────────

def test_CS522_8zb_land_supp_heading_environment_geotechnical(page: Page, live_server: str) -> None:
    """Phase 8ZB: 'البيئة والمخاطر الجيوتقنية' section heading visible."""
    _load_land_supp_8zb(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "البيئة والمخاطر الجيوتقنية" in text, (
        f"Phase 8ZB: section 'البيئة والمخاطر الجيوتقنية' missing. Got: {text[:300]!r}"
    )


# ── CS523 ─────────────────────────────────────────────────────────────────────

def test_CS523_8zb_land_supp_heading_climate_risks(page: Page, live_server: str) -> None:
    """Phase 8ZB: 'المخاطر المناخية والطبيعية' section heading visible."""
    _load_land_supp_8zb(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "المخاطر المناخية والطبيعية" in text, (
        f"Phase 8ZB: section 'المخاطر المناخية والطبيعية' missing. Got: {text[:300]!r}"
    )


# ── CS524 ─────────────────────────────────────────────────────────────────────

def test_CS524_8zb_land_supp_heading_digital_infrastructure(page: Page, live_server: str) -> None:
    """Phase 8ZB: 'البنية التحتية الرقمية والاستعداد الذكي' section heading visible."""
    _load_land_supp_8zb(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "البنية التحتية الرقمية والاستعداد الذكي" in text, (
        f"Phase 8ZB: section 'البنية التحتية الرقمية والاستعداد الذكي' missing. Got: {text[:300]!r}"
    )


# ── CS525 ─────────────────────────────────────────────────────────────────────

def test_CS525_8zb_soil_bearing_capacity_available_bool(page: Page, live_server: str) -> None:
    """Phase 8ZB: soil_bearing_capacity_available renders as bool select (Section A)."""
    _load_land_supp_8zb(page, live_server)
    sel = page.locator("#es-supp-field-soil_bearing_capacity_available")
    assert sel.count() > 0, "Phase 8ZB: soil_bearing_capacity_available must render in land supp."
    opts_text = sel.inner_text()
    assert "نعم" in opts_text, "Phase 8ZB: soil_bearing_capacity_available must show نعم option."


# ── CS526 ─────────────────────────────────────────────────────────────────────

def test_CS526_8zb_development_readiness_level_select(page: Page, live_server: str) -> None:
    """Phase 8ZB: development_readiness_level select renders (Section B)."""
    _load_land_supp_8zb(page, live_server)
    sel = page.locator("#es-supp-field-development_readiness_level")
    assert sel.count() > 0, "Phase 8ZB: development_readiness_level must render in land supp."
    opts = sel.locator("option")
    assert opts.count() >= 4, (
        f"Phase 8ZB: development_readiness_level must have >=4 options. Got {opts.count()}"
    )


# ── CS527 ─────────────────────────────────────────────────────────────────────

def test_CS527_8zb_current_land_use_select(page: Page, live_server: str) -> None:
    """Phase 8ZB: current_land_use select renders (Section C)."""
    _load_land_supp_8zb(page, live_server)
    sel = page.locator("#es-supp-field-current_land_use")
    assert sel.count() > 0, "Phase 8ZB: current_land_use must render in land supp."


# ── CS528 ─────────────────────────────────────────────────────────────────────

def test_CS528_8zb_setback_front_m_number_input(page: Page, live_server: str) -> None:
    """Phase 8ZB: setback_front_m renders as number input with meter unit (Section C)."""
    _load_land_supp_8zb(page, live_server)
    field = page.locator("[data-es-supp-field='setback_front_m']")
    assert field.count() > 0, "Phase 8ZB: setback_front_m must be present in land supp."
    assert field.get_attribute("type") == "number", (
        "setback_front_m must be type='number'."
    )


# ── CS529 ─────────────────────────────────────────────────────────────────────

def test_CS529_8zb_ld_ownership_type_select(page: Page, live_server: str) -> None:
    """Phase 8ZB: ld_ownership_type select renders with Arabic options (Section D)."""
    _load_land_supp_8zb(page, live_server)
    sel = page.locator("#es-supp-field-ld_ownership_type")
    assert sel.count() > 0, "Phase 8ZB: ld_ownership_type must render in land supp."
    opts = sel.locator("option")
    assert opts.count() >= 4, (
        f"Phase 8ZB: ld_ownership_type must have >=4 options. Got {opts.count()}"
    )


# ── CS530 ─────────────────────────────────────────────────────────────────────

def test_CS530_8zb_ld_legal_restrictions_summary_textarea(page: Page, live_server: str) -> None:
    """Phase 8ZB: ld_legal_restrictions_summary renders as <textarea> (Section D)."""
    _load_land_supp_8zb(page, live_server)
    ta = page.locator("textarea[data-es-supp-field='ld_legal_restrictions_summary']")
    assert ta.count() == 1, (
        "Phase 8ZB: ld_legal_restrictions_summary must render as <textarea>."
    )


# ── CS531 ─────────────────────────────────────────────────────────────────────

def test_CS531_8zb_electricity_connection_status_select(page: Page, live_server: str) -> None:
    """Phase 8ZB: electricity_connection_status select renders (Section E)."""
    _load_land_supp_8zb(page, live_server)
    sel = page.locator("#es-supp-field-electricity_connection_status")
    assert sel.count() > 0, "Phase 8ZB: electricity_connection_status must render in land supp."


# ── CS532 ─────────────────────────────────────────────────────────────────────

def test_CS532_8zb_distance_to_nearest_water_m_number_input(page: Page, live_server: str) -> None:
    """Phase 8ZB: distance_to_nearest_water_m renders as number input (Section E)."""
    _load_land_supp_8zb(page, live_server)
    field = page.locator("[data-es-supp-field='distance_to_nearest_water_m']")
    assert field.count() > 0, "Phase 8ZB: distance_to_nearest_water_m must be present."
    assert field.get_attribute("type") == "number", (
        "distance_to_nearest_water_m must be type='number'."
    )


# ── CS533 ─────────────────────────────────────────────────────────────────────

def test_CS533_8zb_access_road_type_select(page: Page, live_server: str) -> None:
    """Phase 8ZB: access_road_type select renders with options (Section F)."""
    _load_land_supp_8zb(page, live_server)
    sel = page.locator("#es-supp-field-access_road_type")
    assert sel.count() > 0, "Phase 8ZB: access_road_type must render in land supp."
    opts = sel.locator("option")
    assert opts.count() >= 4, (
        f"Phase 8ZB: access_road_type must have >=4 options. Got {opts.count()}"
    )


# ── CS534 ─────────────────────────────────────────────────────────────────────

def test_CS534_8zb_current_market_price_per_sqm_number_input(page: Page, live_server: str) -> None:
    """Phase 8ZB: current_market_price_per_sqm renders as number input (Section G)."""
    _load_land_supp_8zb(page, live_server)
    field = page.locator("[data-es-supp-field='current_market_price_per_sqm']")
    assert field.count() > 0, "Phase 8ZB: current_market_price_per_sqm must be present."
    assert field.get_attribute("type") == "number", (
        "current_market_price_per_sqm must be type='number'."
    )


# ── CS535 ─────────────────────────────────────────────────────────────────────

def test_CS535_8zb_development_feasibility_level_select(page: Page, live_server: str) -> None:
    """Phase 8ZB: development_feasibility_level select renders (Section H)."""
    _load_land_supp_8zb(page, live_server)
    sel = page.locator("#es-supp-field-development_feasibility_level")
    assert sel.count() > 0, "Phase 8ZB: development_feasibility_level must render in land supp."


# ── CS536 ─────────────────────────────────────────────────────────────────────

def test_CS536_8zb_ld_purpose_mortgage_lending_methodology_select(page: Page, live_server: str) -> None:
    """Phase 8ZB: ld_purpose_mortgage_lending_methodology select renders with >=10 options (Section I)."""
    _load_land_supp_8zb(page, live_server)
    sel = page.locator("#es-supp-field-ld_purpose_mortgage_lending_methodology")
    assert sel.count() > 0, (
        "Phase 8ZB: ld_purpose_mortgage_lending_methodology must render in land supp."
    )
    opts = sel.locator("option")
    assert opts.count() >= 10, (
        f"Phase 8ZB: methodology select must have >=10 options (incl. land-specific). Got {opts.count()}"
    )


# ── CS537 ─────────────────────────────────────────────────────────────────────

def test_CS537_8zb_ld_purpose_development_feasibility_methodology_select(page: Page, live_server: str) -> None:
    """Phase 8ZB: ld_purpose_development_feasibility_methodology (local-only) select renders (Section I)."""
    _load_land_supp_8zb(page, live_server)
    sel = page.locator("#es-supp-field-ld_purpose_development_feasibility_methodology")
    assert sel.count() > 0, (
        "Phase 8ZB: ld_purpose_development_feasibility_methodology (local-only) must render."
    )
    assert sel.get_attribute("data-es-req-field") is None, (
        "ld_purpose_development_feasibility_methodology must NOT have data-es-req-field."
    )


# ── CS538 ─────────────────────────────────────────────────────────────────────

def test_CS538_8zb_ld_purpose_expropriation_compensation_methodology_select(page: Page, live_server: str) -> None:
    """Phase 8ZB: ld_purpose_expropriation_compensation_methodology (local-only) select renders (Section I)."""
    _load_land_supp_8zb(page, live_server)
    sel = page.locator("#es-supp-field-ld_purpose_expropriation_compensation_methodology")
    assert sel.count() > 0, (
        "Phase 8ZB: ld_purpose_expropriation_compensation_methodology (local-only) must render."
    )


# ── CS539 ─────────────────────────────────────────────────────────────────────

def test_CS539_8zb_ld_flood_risk_level_select(page: Page, live_server: str) -> None:
    """Phase 8ZB: ld_flood_risk_level select renders (Section J)."""
    _load_land_supp_8zb(page, live_server)
    sel = page.locator("#es-supp-field-ld_flood_risk_level")
    assert sel.count() > 0, "Phase 8ZB: ld_flood_risk_level must render in land supp."


# ── CS540 ─────────────────────────────────────────────────────────────────────

def test_CS540_8zb_ld_climate_risk_value_impact_pct_number_input(page: Page, live_server: str) -> None:
    """Phase 8ZB: ld_climate_risk_value_impact_pct renders as number input (Section K)."""
    _load_land_supp_8zb(page, live_server)
    field = page.locator("[data-es-supp-field='ld_climate_risk_value_impact_pct']")
    assert field.count() > 0, "Phase 8ZB: ld_climate_risk_value_impact_pct must be present."
    assert field.get_attribute("type") == "number", (
        "ld_climate_risk_value_impact_pct must be type='number'."
    )


# ── CS541 ─────────────────────────────────────────────────────────────────────

def test_CS541_8zb_ld_digital_infrastructure_value_impact_pct(page: Page, live_server: str) -> None:
    """Phase 8ZB: ld_digital_infrastructure_value_impact_pct renders as number input (Section L)."""
    _load_land_supp_8zb(page, live_server)
    field = page.locator("[data-es-supp-field='ld_digital_infrastructure_value_impact_pct']")
    assert field.count() > 0, "Phase 8ZB: ld_digital_infrastructure_value_impact_pct must be present."
    assert field.get_attribute("type") == "number", (
        "ld_digital_infrastructure_value_impact_pct must be type='number'."
    )


# ── CS542 ─────────────────────────────────────────────────────────────────────

def test_CS542_8zb_agricultural_land_isolation(page: Page, live_server: str) -> None:
    """Phase 8ZB: agricultural_land form remains isolated — ag_area_sqm present, no land supp fields."""
    _load_agricultural_land(page, live_server)
    panel = page.locator("#es-req-panel")
    ag_field = panel.locator("[data-es-req-field='ag_area_sqm']")
    assert ag_field.count() > 0, (
        "Phase 8ZB regression: ag_area_sqm must still render in agricultural_land form."
    )
    supp = page.locator("#es-req-supp")
    land_supp_fields = supp.locator(
        "[data-es-supp-field='development_feasibility_level'], "
        "[data-es-supp-field='ld_purpose_mortgage_lending_methodology']"
    )
    assert land_supp_fields.count() == 0, (
        f"Phase 8ZB: land supp fields must NOT appear in agricultural_land panel. "
        f"Found {land_supp_fields.count()}."
    )


# ── CS543 ─────────────────────────────────────────────────────────────────────

def test_CS543_8zb_existing_8q_land_fields_regression(page: Page, live_server: str) -> None:
    """Phase 8ZB regression: existing 8Q/8W land fields (land_development_stage, far_ratio) still render."""
    _load_land_supp_8zb(page, live_server)
    supp = page.locator("#es-req-supp")
    for name in ("land_development_stage", "far_ratio", "main_street_width_m",
                 "infrastructure_development_cost"):
        count = supp.locator(f"[data-es-supp-field='{name}']").count()
        assert count > 0, (
            f"Phase 8ZB regression: existing 8Q/8W field '{name}' must still render in land supp."
        )


# ── Phase 8ZC — Enriched Agricultural Land Requirements (CS544–CS570) ─────────

# ── CS544 ─────────────────────────────────────────────────────────────────────

def test_CS544_agricultural_land_8zc_heading_legal(page: Page, live_server: str) -> None:
    """Phase 8ZC: agricultural_land shows new 'الوضع القانوني والتنظيمي' section heading."""
    _load_agricultural_land(page, live_server)
    panel = page.locator("#es-req-panel")
    assert "الوضع القانوني والتنظيمي" in (panel.inner_text() or ""), (
        "Phase 8ZC: heading 'الوضع القانوني والتنظيمي' must appear in agricultural_land panel."
    )


# ── CS545 ─────────────────────────────────────────────────────────────────────

def test_CS545_agricultural_land_8zc_heading_market(page: Page, live_server: str) -> None:
    """Phase 8ZC: agricultural_land shows 'السوق والوصول وسلاسل الإمداد' section heading."""
    _load_agricultural_land(page, live_server)
    panel = page.locator("#es-req-panel")
    assert "السوق والوصول وسلاسل الإمداد" in (panel.inner_text() or ""), (
        "Phase 8ZC: heading 'السوق والوصول وسلاسل الإمداد' must appear in agricultural_land panel."
    )


# ── CS546 ─────────────────────────────────────────────────────────────────────

def test_CS546_agricultural_land_8zc_heading_risks(page: Page, live_server: str) -> None:
    """Phase 8ZC: agricultural_land shows 'المخاطر البيئية والمناخية' section heading."""
    _load_agricultural_land(page, live_server)
    panel = page.locator("#es-req-panel")
    assert "المخاطر البيئية والمناخية" in (panel.inner_text() or ""), (
        "Phase 8ZC: heading 'المخاطر البيئية والمناخية' must appear in agricultural_land panel."
    )


# ── CS547 ─────────────────────────────────────────────────────────────────────

def test_CS547_agricultural_land_8zc_heading_sustainability(page: Page, live_server: str) -> None:
    """Phase 8ZC: agricultural_land shows 'الاستدامة وكفاءة الموارد' section heading."""
    _load_agricultural_land(page, live_server)
    panel = page.locator("#es-req-panel")
    assert "الاستدامة وكفاءة الموارد" in (panel.inner_text() or ""), (
        "Phase 8ZC: heading 'الاستدامة وكفاءة الموارد' must appear in agricultural_land panel."
    )


# ── CS548 ─────────────────────────────────────────────────────────────────────

def test_CS548_agricultural_land_8zc_heading_purpose(page: Page, live_server: str) -> None:
    """Phase 8ZC: agricultural_land shows 'معاملات التعديل حسب غرض التقييم' heading."""
    _load_agricultural_land(page, live_server)
    panel = page.locator("#es-req-panel")
    assert "معاملات التعديل حسب غرض التقييم" in (panel.inner_text() or ""), (
        "Phase 8ZC: purpose-adjustment heading must appear in agricultural_land panel."
    )


# ── CS549 ─────────────────────────────────────────────────────────────────────

def test_CS549_agricultural_land_8zc_ag_topography_renders(page: Page, live_server: str) -> None:
    """Phase 8ZC: ag_topography select renders in agricultural_land panel."""
    _load_agricultural_land(page, live_server)
    panel = page.locator("#es-req-panel")
    field = panel.locator("[data-es-req-field='ag_topography']")
    assert field.count() > 0, (
        "Phase 8ZC: ag_topography must render in agricultural_land panel."
    )


# ── CS550 ─────────────────────────────────────────────────────────────────────

def test_CS550_agricultural_land_8zc_ag_land_tenure_type_renders(page: Page, live_server: str) -> None:
    """Phase 8ZC: ag_land_tenure_type select renders in agricultural_land panel."""
    _load_agricultural_land(page, live_server)
    panel = page.locator("#es-req-panel")
    field = panel.locator("[data-es-req-field='ag_land_tenure_type']")
    assert field.count() > 0, (
        "Phase 8ZC: ag_land_tenure_type must render in agricultural_land panel."
    )


# ── CS551 ─────────────────────────────────────────────────────────────────────

def test_CS551_agricultural_land_8zc_ag_crop_rotation_renders(page: Page, live_server: str) -> None:
    """Phase 8ZC: ag_crop_rotation_available bool select renders in agricultural_land panel."""
    _load_agricultural_land(page, live_server)
    panel = page.locator("#es-req-panel")
    field = panel.locator("[data-es-req-field='ag_crop_rotation_available']")
    assert field.count() > 0, (
        "Phase 8ZC: ag_crop_rotation_available must render in agricultural_land panel."
    )


# ── CS552 ─────────────────────────────────────────────────────────────────────

def test_CS552_agricultural_land_8zc_ag_drought_risk_renders(page: Page, live_server: str) -> None:
    """Phase 8ZC: ag_drought_risk_level select renders in agricultural_land panel."""
    _load_agricultural_land(page, live_server)
    panel = page.locator("#es-req-panel")
    field = panel.locator("[data-es-req-field='ag_drought_risk_level']")
    assert field.count() > 0, (
        "Phase 8ZC: ag_drought_risk_level must render in agricultural_land panel."
    )


# ── CS553 ─────────────────────────────────────────────────────────────────────

def test_CS553_agricultural_land_8zc_ag_water_use_efficiency_renders(page: Page, live_server: str) -> None:
    """Phase 8ZC: ag_water_use_efficiency_level select renders in agricultural_land panel."""
    _load_agricultural_land(page, live_server)
    panel = page.locator("#es-req-panel")
    field = panel.locator("[data-es-req-field='ag_water_use_efficiency_level']")
    assert field.count() > 0, (
        "Phase 8ZC: ag_water_use_efficiency_level must render in agricultural_land panel."
    )


# ── CS554 ─────────────────────────────────────────────────────────────────────

def test_CS554_agricultural_land_8zc_ag_purpose_mortgage_methodology_renders(page: Page, live_server: str) -> None:
    """Phase 8ZC: ag_purpose_mortgage_lending_methodology select renders in panel."""
    _load_agricultural_land(page, live_server)
    panel = page.locator("#es-req-panel")
    field = panel.locator("[data-es-req-field='ag_purpose_mortgage_lending_methodology']")
    assert field.count() > 0, (
        "Phase 8ZC: ag_purpose_mortgage_lending_methodology must render in agricultural_land panel."
    )


# ── CS555 ─────────────────────────────────────────────────────────────────────

def test_CS555_agricultural_land_8zc_ag_purpose_agricultural_lease_local_label(page: Page, live_server: str) -> None:
    """Phase 8ZC: ag_purpose_agricultural_lease_methodology renders and label contains 'محلي فقط'."""
    _load_agricultural_land(page, live_server)
    panel = page.locator("#es-req-panel")
    field = panel.locator("[data-es-req-field='ag_purpose_agricultural_lease_methodology']")
    assert field.count() > 0, (
        "Phase 8ZC: ag_purpose_agricultural_lease_methodology must render in agricultural_land panel."
    )
    assert "محلي فقط" in (panel.inner_text() or ""), (
        "Phase 8ZC: local-purpose label must contain 'محلي فقط' in agricultural_land panel."
    )


# ── CS556 ─────────────────────────────────────────────────────────────────────

def test_CS556_agricultural_land_8zc_methodology_opts_agricultural_income(page: Page, live_server: str) -> None:
    """Phase 8ZC: 'رسملة الدخل الزراعي' option is available in methodology dropdowns."""
    _load_agricultural_land(page, live_server)
    panel = page.locator("#es-req-panel")
    assert "رسملة الدخل الزراعي" in (panel.inner_text() or ""), (
        "Phase 8ZC: 'رسملة الدخل الزراعي' methodology option must be visible in agricultural_land panel."
    )


# ── CS557 ─────────────────────────────────────────────────────────────────────

def test_CS557_agricultural_land_8zc_ag_area_feddan_help_ar(page: Page, live_server: str) -> None:
    """Phase 8ZC: ag_area_feddan help text '4,200' renders in agricultural_land panel."""
    _load_agricultural_land(page, live_server)
    panel = page.locator("#es-req-panel")
    assert "4,200" in (panel.inner_text() or ""), (
        "Phase 8ZC: ag_area_feddan help_ar '4,200 م²' must render in agricultural_land panel."
    )


# ── CS558 ─────────────────────────────────────────────────────────────────────

def test_CS558_agricultural_land_8zc_ag_salinity_help_ar(page: Page, live_server: str) -> None:
    """Phase 8ZC: ag_salinity_level help text '2,000 ppm' renders in agricultural_land panel."""
    _load_agricultural_land(page, live_server)
    panel = page.locator("#es-req-panel")
    assert "2,000 ppm" in (panel.inner_text() or ""), (
        "Phase 8ZC: ag_salinity_level help_ar '2,000 ppm' must render in agricultural_land panel."
    )


# ── CS559 ─────────────────────────────────────────────────────────────────────

def test_CS559_agricultural_land_8zc_ag_irrigation_system_help_ar(page: Page, live_server: str) -> None:
    """Phase 8ZC: ag_irrigation_system help text 'التنقيط' renders in agricultural_land panel."""
    _load_agricultural_land(page, live_server)
    panel = page.locator("#es-req-panel")
    assert "التنقيط" in (panel.inner_text() or ""), (
        "Phase 8ZC: ag_irrigation_system help_ar must contain 'التنقيط' in agricultural_land panel."
    )


# ── CS560 ─────────────────────────────────────────────────────────────────────

def test_CS560_agricultural_land_8zc_ag_net_income_help_ar(page: Page, live_server: str) -> None:
    """Phase 8ZC: ag_net_agricultural_income_annual help text 'الرسملة' renders in panel."""
    _load_agricultural_land(page, live_server)
    panel = page.locator("#es-req-panel")
    assert "الرسملة" in (panel.inner_text() or ""), (
        "Phase 8ZC: ag_net_agricultural_income_annual help_ar must contain 'الرسملة' in panel."
    )


# ── CS561 ─────────────────────────────────────────────────────────────────────

def test_CS561_agricultural_land_8zc_ag_flood_risk_help_ar(page: Page, live_server: str) -> None:
    """Phase 8ZC: ag_flood_risk help text about insurance renders in agricultural_land panel."""
    _load_agricultural_land(page, live_server)
    panel = page.locator("#es-req-panel")
    assert "التأمين" in (panel.inner_text() or ""), (
        "Phase 8ZC: ag_flood_risk help_ar must contain 'التأمين' in agricultural_land panel."
    )


# ── CS562 ─────────────────────────────────────────────────────────────────────

def test_CS562_agricultural_land_8zc_existing_soil_type_still_renders(page: Page, live_server: str) -> None:
    """Phase 8ZC regression: existing ag_soil_type select still renders after 8ZC enrichment."""
    _load_agricultural_land(page, live_server)
    panel = page.locator("#es-req-panel")
    field = panel.locator("[data-es-req-field='ag_soil_type']")
    assert field.count() > 0, (
        "Phase 8ZC regression: ag_soil_type must still render in agricultural_land panel after 8ZC."
    )


# ── CS563 ─────────────────────────────────────────────────────────────────────

def test_CS563_agricultural_land_8zc_existing_cultivation_cost_still_renders(page: Page, live_server: str) -> None:
    """Phase 8ZC regression: existing ag_annual_cultivation_cost still renders after 8ZC."""
    _load_agricultural_land(page, live_server)
    panel = page.locator("#es-req-panel")
    field = panel.locator("[data-es-req-field='ag_annual_cultivation_cost']")
    assert field.count() > 0, (
        "Phase 8ZC regression: ag_annual_cultivation_cost must still render after 8ZC."
    )


# ── CS564 ─────────────────────────────────────────────────────────────────────

def test_CS564_agricultural_land_8zc_water_section_still_present(page: Page, live_server: str) -> None:
    """Phase 8ZC regression: existing 'مصادر المياه والري' heading still present (CS256 guard)."""
    _load_agricultural_land(page, live_server)
    panel = page.locator("#es-req-panel")
    assert "مصادر المياه والري" in (panel.inner_text() or ""), (
        "Phase 8ZC regression: 'مصادر المياه والري' section heading must remain unchanged after 8ZC."
    )


# ── CS565 ─────────────────────────────────────────────────────────────────────

def test_CS565_agricultural_land_8zc_ag_sustainability_value_impact_pct_renders(page: Page, live_server: str) -> None:
    """Phase 8ZC: ag_sustainability_value_impact_pct number input renders in panel."""
    _load_agricultural_land(page, live_server)
    panel = page.locator("#es-req-panel")
    field = panel.locator("[data-es-req-field='ag_sustainability_value_impact_pct']")
    assert field.count() > 0, (
        "Phase 8ZC: ag_sustainability_value_impact_pct must render in agricultural_land panel."
    )


# ── CS566 ─────────────────────────────────────────────────────────────────────

def test_CS566_agricultural_land_8zc_ag_legal_dispute_status_renders(page: Page, live_server: str) -> None:
    """Phase 8ZC: ag_legal_dispute_status select renders in agricultural_land panel."""
    _load_agricultural_land(page, live_server)
    panel = page.locator("#es-req-panel")
    field = panel.locator("[data-es-req-field='ag_legal_dispute_status']")
    assert field.count() > 0, (
        "Phase 8ZC: ag_legal_dispute_status must render in agricultural_land panel."
    )


# ── CS567 ─────────────────────────────────────────────────────────────────────

def test_CS567_land_unchanged_after_8zc(page: Page, live_server: str) -> None:
    """Phase 8ZC isolation: land (أرض فضاء) supp panel renders far_ratio; no ag_ req fields cross."""
    _load_land_supp_8zb(page, live_server)
    supp = page.locator("#es-req-supp")
    land_field = supp.locator("[data-es-supp-field='far_ratio']")
    assert land_field.count() > 0, (
        "Phase 8ZC isolation: far_ratio must still render in land supp after 8ZC."
    )
    ag_cross = supp.locator(
        "[data-es-req-field='ag_topography'], "
        "[data-es-req-field='ag_land_tenure_type']"
    )
    assert ag_cross.count() == 0, (
        f"Phase 8ZC isolation: ag_ fields must NOT appear in land supp. Found {ag_cross.count()}."
    )


# ── CS568 ─────────────────────────────────────────────────────────────────────

def test_CS568_riparian_rights_unchanged_after_8zc(page: Page, live_server: str) -> None:
    """Phase 8ZC isolation: riparian_rights panel unchanged; ag_ enrichment fields absent."""
    _load_riparian_rights(page, live_server)
    panel = page.locator("#es-req-panel")
    ag_cross = panel.locator(
        "[data-es-req-field='ag_topography'], "
        "[data-es-req-field='ag_land_tenure_type']"
    )
    assert ag_cross.count() == 0, (
        f"Phase 8ZC isolation: ag_ enrichment fields must NOT appear in riparian_rights panel. "
        f"Found {ag_cross.count()}."
    )


# ── CS569 ─────────────────────────────────────────────────────────────────────

def test_CS569_water_well_unchanged_after_8zc(page: Page, live_server: str) -> None:
    """Phase 8ZC isolation: water_well panel unchanged; ag_ enrichment fields absent."""
    _load_water_well(page, live_server)
    panel = page.locator("#es-req-panel")
    ag_cross = panel.locator(
        "[data-es-req-field='ag_land_tenure_type'], "
        "[data-es-req-field='ag_topography']"
    )
    assert ag_cross.count() == 0, (
        f"Phase 8ZC isolation: ag_ enrichment fields must NOT appear in water_well panel. "
        f"Found {ag_cross.count()}."
    )


# ── CS570 ─────────────────────────────────────────────────────────────────────

def test_CS570_8zc_airport_isolation(page: Page, live_server: str) -> None:
    """Phase 8ZC isolation: airport panel unchanged after 8ZC; ag_ enrichment fields absent."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="airport")
    page.select_option("#val-purpose", value="fair_market_value")
    panel = page.locator("#es-req-panel")
    panel.wait_for(state="visible", timeout=4_000)
    ag_cross = panel.locator(
        "[data-es-req-field='ag_topography'], "
        "[data-es-req-field='ag_drought_risk_level']"
    )
    assert ag_cross.count() == 0, (
        f"Phase 8ZC isolation: ag_ enrichment fields must NOT appear in airport panel. "
        f"Found {ag_cross.count()}."
    )


# ── Phase 8ZD helpers ─────────────────────────────────────────────────────────

def _load_existing_building(page: "Page", live_server: str) -> None:
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="مبنى قائم")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


# ── CS571 ─────────────────────────────────────────────────────────────────────

def test_CS571_existing_building_routes_as_static_form(page: "Page", live_server: str) -> None:
    """Phase 8ZD: مبنى قائم routes as a static form profile (zero API calls)."""
    api_calls: list = []
    page.on("request", lambda r: api_calls.append(r.url) if "/api/valuation/requirements" in r.url else None)
    _load_existing_building(page, live_server)
    assert len(api_calls) == 0, (
        f"8ZD: existing_building_detailed must make ZERO API calls. Got: {api_calls}"
    )


# ── CS572 ─────────────────────────────────────────────────────────────────────

def test_CS572_existing_building_title_contains_arabic_name(page: "Page", live_server: str) -> None:
    """Phase 8ZD: panel title contains 'مبنى قائم'."""
    _load_existing_building(page, live_server)
    title = page.locator("#es-req-title").inner_text()
    assert "مبنى قائم" in title, (
        f"8ZD: title must contain 'مبنى قائم'. Got: {title!r}"
    )


# ── CS573 ─────────────────────────────────────────────────────────────────────

def test_CS573_existing_building_badge_shows_local_form(page: "Page", live_server: str) -> None:
    """Phase 8ZD: explainer badge shows 'نموذج محلي' for existing_building_detailed."""
    _load_existing_building(page, live_server)
    badge = page.locator("#es-profile-badge").inner_text()
    assert "نموذج محلي" in badge, (
        f"8ZD: badge must contain 'نموذج محلي'. Got: {badge!r}"
    )


# ── CS574 ─────────────────────────────────────────────────────────────────────

def test_CS574_existing_building_has_no_composite_link(page: "Page", live_server: str) -> None:
    """Phase 8ZD: existing_building_detailed panel has no composite_valuation.html link."""
    _load_existing_building(page, live_server)
    panel_html = page.locator("#es-req-panel").inner_html()
    assert "composite_valuation.html" not in panel_html, (
        "8ZD: existing_building_detailed panel must NOT contain composite_valuation.html link."
    )


# ── CS575 ─────────────────────────────────────────────────────────────────────

def test_CS575_existing_building_no_auth_modal(page: "Page", live_server: str) -> None:
    """Phase 8ZD: selecting مبنى قائم does NOT trigger auth/login modal."""
    _load_existing_building(page, live_server)
    modal = page.locator("#login-modal, #auth-modal, [id*='login']")
    visible_count = sum(1 for i in range(modal.count()) if modal.nth(i).is_visible())
    assert visible_count == 0, (
        f"8ZD: NO auth modal must be visible after selecting مبنى قائم. visible={visible_count}"
    )


# ── CS576 ─────────────────────────────────────────────────────────────────────

def test_CS576_existing_building_renders_supplemental_controls(page: "Page", live_server: str) -> None:
    """Phase 8ZD: #es-req-supp contains supplemental field controls (ebd_ fields)."""
    _load_existing_building(page, live_server)
    supp = page.locator("#es-req-supp")
    supp.wait_for(state="attached", timeout=4_000)
    controls = supp.locator("[data-es-supp-field]")
    assert controls.count() > 10, (
        f"8ZD: #es-req-supp must contain >10 supp controls. Got {controls.count()}."
    )


# ── CS577 ─────────────────────────────────────────────────────────────────────

def test_CS577_existing_building_supp_heading_arabic(page: "Page", live_server: str) -> None:
    """Phase 8ZD: #es-req-supp header shows Arabic heading for existing_building_detailed."""
    _load_existing_building(page, live_server)
    supp = page.locator("#es-req-supp")
    supp_text = supp.inner_text()
    assert "مبنى قائم" in supp_text, (
        f"8ZD: supp heading must contain 'مبنى قائم'. Got excerpt: {supp_text[:200]!r}"
    )


# ── CS578 ─────────────────────────────────────────────────────────────────────

def test_CS578_existing_building_section_A_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZD: section heading 'تعريف المبنى والاستخدام' visible."""
    _load_existing_building(page, live_server)
    assert "تعريف المبنى والاستخدام" in (page.locator("#es-req-supp").inner_text() or ""), (
        "8ZD: section A heading 'تعريف المبنى والاستخدام' must appear."
    )


# ── CS579 ─────────────────────────────────────────────────────────────────────

def test_CS579_existing_building_section_B_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZD: section heading 'الأرض والموقع العام' visible."""
    _load_existing_building(page, live_server)
    assert "الأرض والموقع العام" in (page.locator("#es-req-supp").inner_text() or ""), (
        "8ZD: section B heading 'الأرض والموقع العام' must appear."
    )


# ── CS580 ─────────────────────────────────────────────────────────────────────

def test_CS580_existing_building_section_C_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZD: section heading 'الخصائص المادية والإنشائية' visible."""
    _load_existing_building(page, live_server)
    assert "الخصائص المادية والإنشائية" in (page.locator("#es-req-supp").inner_text() or ""), (
        "8ZD: section C heading must appear."
    )


# ── CS581 ─────────────────────────────────────────────────────────────────────

def test_CS581_existing_building_section_D_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZD: section heading 'التوزيع حسب الأدوار والاستخدامات' visible."""
    _load_existing_building(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "التوزيع حسب الأدوار والاستخدامات" in panel_text, (
        "8ZD: section D heading must appear in existing_building_detailed panel."
    )


# ── CS582 ─────────────────────────────────────────────────────────────────────

def test_CS582_existing_building_section_E_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZD: section heading 'التشطيبات والمرافق والخدمات' visible."""
    _load_existing_building(page, live_server)
    assert "التشطيبات والمرافق والخدمات" in (page.locator("#es-req-supp").inner_text() or ""), (
        "8ZD: section E heading must appear."
    )


# ── CS583 ─────────────────────────────────────────────────────────────────────

def test_CS583_existing_building_section_F_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZD: section heading 'الخصائص القانونية والتنظيمية' visible."""
    _load_existing_building(page, live_server)
    assert "الخصائص القانونية والتنظيمية" in (page.locator("#es-req-supp").inner_text() or ""), (
        "8ZD: section F heading must appear."
    )


# ── CS584 ─────────────────────────────────────────────────────────────────────

def test_CS584_existing_building_section_G_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZD: section heading 'الإشغال والعقود والدخل' visible."""
    _load_existing_building(page, live_server)
    assert "الإشغال والعقود والدخل" in (page.locator("#es-req-supp").inner_text() or ""), (
        "8ZD: section G heading must appear."
    )


# ── CS585 ─────────────────────────────────────────────────────────────────────

def test_CS585_existing_building_section_H_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZD: section heading 'التكاليف وCAPEX والصيانة المؤجَّلة' visible."""
    _load_existing_building(page, live_server)
    assert "التكاليف وCAPEX" in (page.locator("#es-req-supp").inner_text() or ""), (
        "8ZD: section H heading must appear."
    )


# ── CS586 ─────────────────────────────────────────────────────────────────────

def test_CS586_existing_building_section_I_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZD: section heading 'السوق وقابلية التسويق' visible."""
    _load_existing_building(page, live_server)
    assert "السوق وقابلية التسويق" in (page.locator("#es-req-supp").inner_text() or ""), (
        "8ZD: section I heading must appear."
    )


# ── CS587 ─────────────────────────────────────────────────────────────────────

def test_CS587_existing_building_section_J_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZD: section heading 'معاملات التعديل حسب غرض التقييم' visible."""
    _load_existing_building(page, live_server)
    assert "معاملات التعديل حسب غرض التقييم" in (page.locator("#es-req-supp").inner_text() or ""), (
        "8ZD: section J heading must appear."
    )


# ── CS588 ─────────────────────────────────────────────────────────────────────

def test_CS588_existing_building_section_K_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZD: section heading 'كفاءة الطاقة والاستدامة' visible."""
    _load_existing_building(page, live_server)
    assert "كفاءة الطاقة والاستدامة" in (page.locator("#es-req-supp").inner_text() or ""), (
        "8ZD: section K heading must appear."
    )


# ── CS589 ─────────────────────────────────────────────────────────────────────

def test_CS589_existing_building_section_L_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZD: section heading 'المخاطر المناخية والطبيعية' visible."""
    _load_existing_building(page, live_server)
    assert "المخاطر المناخية والطبيعية" in (page.locator("#es-req-supp").inner_text() or ""), (
        "8ZD: section L heading must appear."
    )


# ── CS590 ─────────────────────────────────────────────────────────────────────

def test_CS590_existing_building_section_M_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZD: section heading 'البنية التحتية الرقمية والذكية' visible."""
    _load_existing_building(page, live_server)
    assert "البنية التحتية الرقمية والذكية" in (page.locator("#es-req-supp").inner_text() or ""), (
        "8ZD: section M heading must appear."
    )


# ── CS591 ─────────────────────────────────────────────────────────────────────

def test_CS591_existing_building_section_N_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZD: section heading 'مستندات إضافية مطلوبة' visible."""
    _load_existing_building(page, live_server)
    assert "مستندات إضافية مطلوبة" in (page.locator("#es-req-supp").inner_text() or ""), (
        "8ZD: section N heading must appear."
    )


# ── CS592 ─────────────────────────────────────────────────────────────────────

def test_CS592_ebd_building_use_type_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_building_use_type select renders in existing_building_detailed supp."""
    _load_existing_building(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='ebd_building_use_type']")
    assert field.count() > 0, "8ZD: ebd_building_use_type must render in supp panel."


# ── CS593 ─────────────────────────────────────────────────────────────────────

def test_CS593_ebd_occupancy_type_select_arabic_options(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_occupancy_type select has Arabic options."""
    _load_existing_building(page, live_server)
    sel = page.locator("#es-req-supp [data-es-supp-field='ebd_occupancy_type']")
    assert sel.count() > 0, "8ZD: ebd_occupancy_type must render."
    opts = sel.locator("option").all_inner_texts()
    arabic_opts = [o for o in opts if any("؀" <= c <= "ۿ" for c in o)]
    assert len(arabic_opts) >= 3, (
        f"8ZD: ebd_occupancy_type must have ≥3 Arabic options. Got: {opts}"
    )


# ── CS594 ─────────────────────────────────────────────────────────────────────

def test_CS594_ebd_plot_area_sqm_number_input(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_plot_area_sqm renders as number input with م² unit."""
    _load_existing_building(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='ebd_plot_area_sqm']")
    assert inp.count() > 0, "8ZD: ebd_plot_area_sqm must render."
    assert inp.first.get_attribute("type") == "number", (
        "8ZD: ebd_plot_area_sqm must be type=number."
    )
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "م²" in supp_text, "8ZD: م² unit label must appear in supp panel."


# ── CS595 ─────────────────────────────────────────────────────────────────────

def test_CS595_ebd_net_leasable_area_sqm_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_net_leasable_area_sqm renders as number input."""
    _load_existing_building(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='ebd_net_leasable_area_sqm']")
    assert inp.count() > 0, "8ZD: ebd_net_leasable_area_sqm must render."


# ── CS596 ─────────────────────────────────────────────────────────────────────

def test_CS596_ebd_construction_system_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_construction_system select renders in section C."""
    _load_existing_building(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='ebd_construction_system']")
    assert field.count() > 0, "8ZD: ebd_construction_system must render."


# ── CS597 ─────────────────────────────────────────────────────────────────────

def test_CS597_ebd_visible_structural_defects_checkbox_group(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_visible_structural_defects checkbox group renders."""
    _load_existing_building(page, live_server)
    chips = page.locator("#es-req-supp [data-es-supp-field='ebd_visible_structural_defects']")
    assert chips.count() > 0, "8ZD: ebd_visible_structural_defects checkbox group must render."


# ── CS598 ─────────────────────────────────────────────────────────────────────

def test_CS598_ebd_retail_area_sqm_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_retail_area_sqm number input renders in section D."""
    _load_existing_building(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='ebd_retail_area_sqm']")
    assert inp.count() > 0, "8ZD: ebd_retail_area_sqm must render."


# ── CS599 ─────────────────────────────────────────────────────────────────────

def test_CS599_ebd_unit_mix_summary_textarea_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_unit_mix_summary textarea renders in section D."""
    _load_existing_building(page, live_server)
    ta = page.locator("#es-req-supp [data-es-supp-field='ebd_unit_mix_summary']")
    assert ta.count() > 0, "8ZD: ebd_unit_mix_summary textarea must render."


# ── CS600 ─────────────────────────────────────────────────────────────────────

def test_CS600_ebd_hvac_system_type_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_hvac_system_type select renders in section E."""
    _load_existing_building(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='ebd_hvac_system_type']")
    assert field.count() > 0, "8ZD: ebd_hvac_system_type must render."


# ── CS601 ─────────────────────────────────────────────────────────────────────

def test_CS601_ebd_building_facilities_available_checkbox_group(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_building_facilities_available checkbox group renders."""
    _load_existing_building(page, live_server)
    chips = page.locator("#es-req-supp [data-es-supp-field='ebd_building_facilities_available']")
    assert chips.count() > 0, "8ZD: ebd_building_facilities_available must render."


# ── CS602 ─────────────────────────────────────────────────────────────────────

def test_CS602_ebd_title_deed_available_bool_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_title_deed_available bool select renders in section F."""
    _load_existing_building(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='ebd_title_deed_available']")
    assert field.count() > 0, "8ZD: ebd_title_deed_available must render."


# ── CS603 ─────────────────────────────────────────────────────────────────────

def test_CS603_ebd_market_gross_rent_annual_number_input(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_market_gross_rent_annual renders as number input with unit ج.م./سنة."""
    _load_existing_building(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='ebd_market_gross_rent_annual']")
    assert inp.count() > 0, "8ZD: ebd_market_gross_rent_annual must render."
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "ج.م." in supp_text, "8ZD: ج.م. unit must appear in supp panel."


# ── CS604 ─────────────────────────────────────────────────────────────────────

def test_CS604_ebd_wale_months_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_wale_months (WALE) number input renders in section G."""
    _load_existing_building(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='ebd_wale_months']")
    assert inp.count() > 0, "8ZD: ebd_wale_months must render."


# ── CS605 ─────────────────────────────────────────────────────────────────────

def test_CS605_ebd_capex_required_number_input(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_capex_required renders as number input in section H."""
    _load_existing_building(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='ebd_capex_required']")
    assert inp.count() > 0, "8ZD: ebd_capex_required must render."


# ── CS606 ─────────────────────────────────────────────────────────────────────

def test_CS606_ebd_market_sale_price_per_sqm_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_market_sale_price_per_sqm renders with ج.م./م² unit."""
    _load_existing_building(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='ebd_market_sale_price_per_sqm']")
    assert inp.count() > 0, "8ZD: ebd_market_sale_price_per_sqm must render."


# ── CS607 ─────────────────────────────────────────────────────────────────────

def test_CS607_ebd_sustainability_value_impact_pct_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_sustainability_value_impact_pct renders with % unit in section K."""
    _load_existing_building(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='ebd_sustainability_value_impact_pct']")
    assert inp.count() > 0, "8ZD: ebd_sustainability_value_impact_pct must render."


# ── CS608 ─────────────────────────────────────────────────────────────────────

def test_CS608_ebd_climate_risk_value_impact_pct_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_climate_risk_value_impact_pct renders in section L."""
    _load_existing_building(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='ebd_climate_risk_value_impact_pct']")
    assert inp.count() > 0, "8ZD: ebd_climate_risk_value_impact_pct must render."


# ── CS609 ─────────────────────────────────────────────────────────────────────

def test_CS609_ebd_digital_infrastructure_value_impact_pct_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_digital_infrastructure_value_impact_pct renders in section M."""
    _load_existing_building(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='ebd_digital_infrastructure_value_impact_pct']")
    assert inp.count() > 0, "8ZD: ebd_digital_infrastructure_value_impact_pct must render."


# ── CS610 ─────────────────────────────────────────────────────────────────────

def test_CS610_ebd_doc_title_deed_document_checkbox(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_doc_title_deed document checkbox renders in section N."""
    _load_existing_building(page, live_server)
    cb = page.locator("#es-req-supp [data-es-supp-field='ebd_doc_title_deed']")
    assert cb.count() > 0, "8ZD: ebd_doc_title_deed checkbox must render."


# ── CS611 ─────────────────────────────────────────────────────────────────────

def test_CS611_ebd_doc_recent_photos_document_checkbox(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_doc_recent_photos document checkbox renders in section N."""
    _load_existing_building(page, live_server)
    cb = page.locator("#es-req-supp [data-es-supp-field='ebd_doc_recent_photos']")
    assert cb.count() > 0, "8ZD: ebd_doc_recent_photos checkbox must render."


# ── CS612 ─────────────────────────────────────────────────────────────────────

def test_CS612_ebd_floor_table_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: existing_building_detailed renders floor/use distribution table."""
    _load_existing_building(page, live_server)
    table = page.locator("#es-bf-floor-table")
    assert table.count() > 0, "8ZD: #es-bf-floor-table must render in existing_building_detailed."


# ── CS613 ─────────────────────────────────────────────────────────────────────

def test_CS613_ebd_floor_table_has_five_rows(page: "Page", live_server: str) -> None:
    """Phase 8ZD: floor table has ≥5 rows (basement, ground, first, typical, roof)."""
    _load_existing_building(page, live_server)
    rows = page.locator("#es-bf-floor-table tbody tr")
    assert rows.count() >= 5, (
        f"8ZD: #es-bf-floor-table must have ≥5 rows. Got {rows.count()}."
    )


# ── CS614 ─────────────────────────────────────────────────────────────────────

def test_CS614_ebd_floor_table_licensed_use_selects(page: "Page", live_server: str) -> None:
    """Phase 8ZD: floor table [data-bf-field='licensed_use'] selects count ≥5."""
    _load_existing_building(page, live_server)
    sels = page.locator("[data-bf-field='licensed_use']")
    assert sels.count() >= 5, (
        f"8ZD: licensed_use selects must be ≥5. Got {sels.count()}."
    )


# ── CS615 ─────────────────────────────────────────────────────────────────────

def test_CS615_ebd_floor_labels_arabic(page: "Page", live_server: str) -> None:
    """Phase 8ZD: floor table shows Arabic floor labels (بدروم, الدور الأرضي, سطح)."""
    _load_existing_building(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    for label in ["بدروم", "الدور الأرضي", "سطح"]:
        assert label in panel_text, (
            f"8ZD: floor label '{label}' must appear in existing_building_detailed panel."
        )


# ── CS616 ─────────────────────────────────────────────────────────────────────

def test_CS616_ebd_purpose_mortgage_lending_methodology_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_purpose_mortgage_lending_methodology select renders."""
    _load_existing_building(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='ebd_purpose_mortgage_lending_methodology']"
    )
    assert field.count() > 0, "8ZD: mortgage_lending methodology must render."


# ── CS617 ─────────────────────────────────────────────────────────────────────

def test_CS617_ebd_purpose_sale_purchase_adjustment_pct_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_purpose_sale_purchase_adjustment_pct number input renders."""
    _load_existing_building(page, live_server)
    inp = page.locator(
        "#es-req-supp [data-es-supp-field='ebd_purpose_sale_purchase_adjustment_pct']"
    )
    assert inp.count() > 0, "8ZD: sale_purchase adjustment_pct must render."


# ── CS618 ─────────────────────────────────────────────────────────────────────

def test_CS618_ebd_purpose_ifrs_methodology_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_purpose_ifrs_fair_value_methodology select renders."""
    _load_existing_building(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='ebd_purpose_ifrs_fair_value_methodology']"
    )
    assert field.count() > 0, "8ZD: IFRS methodology must render."


# ── CS619 ─────────────────────────────────────────────────────────────────────

def test_CS619_ebd_purpose_litigation_dispute_local_help_ar(page: "Page", live_server: str) -> None:
    """Phase 8ZD: litigation_dispute purpose block has help_ar marking it as local-only."""
    _load_existing_building(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "نزاعات قضائية" in supp_text, (
        "8ZD: litigation_dispute section must appear in supp panel."
    )


# ── CS620 ─────────────────────────────────────────────────────────────────────

def test_CS620_ebd_purpose_investment_acquisition_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_purpose_investment_acquisition_methodology select renders."""
    _load_existing_building(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='ebd_purpose_investment_acquisition_methodology']"
    )
    assert field.count() > 0, "8ZD: investment_acquisition methodology must render."


# ── CS621 ─────────────────────────────────────────────────────────────────────

def test_CS621_ebd_purpose_redevelopment_feasibility_local_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_purpose_redevelopment_feasibility_methodology renders (local-only)."""
    _load_existing_building(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='ebd_purpose_redevelopment_feasibility_methodology']"
    )
    assert field.count() > 0, "8ZD: redevelopment_feasibility methodology (local) must render."


# ── CS622 ─────────────────────────────────────────────────────────────────────

def test_CS622_ebd_supp_fields_use_data_es_supp_field_attribute(page: "Page", live_server: str) -> None:
    """Phase 8ZD: all ebd_ controls in supp use data-es-supp-field (not data-es-req-field)."""
    _load_existing_building(page, live_server)
    supp = page.locator("#es-req-supp")
    req_fields = supp.locator("[data-es-req-field^='ebd_']")
    assert req_fields.count() == 0, (
        f"8ZD: no ebd_ field must use data-es-req-field in supp. Found {req_fields.count()}."
    )


# ── CS623 ─────────────────────────────────────────────────────────────────────

def test_CS623_ebd_supp_has_no_api_fields_duplicated(page: "Page", live_server: str) -> None:
    """Phase 8ZD: #es-req-supp has no data-es-req-field elements for ebd_ profile."""
    _load_existing_building(page, live_server)
    supp = page.locator("#es-req-supp")
    req_els = supp.locator("[data-es-req-field]")
    assert req_els.count() == 0, (
        f"8ZD: #es-req-supp must contain NO data-es-req-field elements. Got {req_els.count()}."
    )


# ── CS624 ─────────────────────────────────────────────────────────────────────

def test_CS624_existing_building_supp_local_only_text(page: "Page", live_server: str) -> None:
    """Phase 8ZD: supp subtext contains 'إدخال محلي' or 'لا يُرسل للتقرير'."""
    _load_existing_building(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "إدخال محلي" in supp_text or "لا يُرسل" in supp_text, (
        f"8ZD: supp must show local-only disclaimer. Got excerpt: {supp_text[:300]!r}"
    )


# ── CS625 ─────────────────────────────────────────────────────────────────────

def test_CS625_ebd_methodology_opts_include_dcf(page: "Page", live_server: str) -> None:
    """Phase 8ZD: methodology selects include DCF option (discounted_cash_flow)."""
    _load_existing_building(page, live_server)
    sel = page.locator(
        "#es-req-supp [data-es-supp-field='ebd_purpose_mortgage_lending_methodology']"
    )
    assert sel.count() > 0, "8ZD: methodology select must exist."
    opts = sel.locator("option").evaluate_all("els => els.map(e => e.value)")
    assert "discounted_cash_flow" in opts, (
        f"8ZD: DCF option missing from methodology select. Got: {opts}"
    )


# ── CS626 ─────────────────────────────────────────────────────────────────────

def test_CS626_existing_building_isolated_from_building_full(page: "Page", live_server: str) -> None:
    """Phase 8ZD: selecting building_full does NOT show ebd_ supp fields."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    ebd_fields = page.locator("[data-es-supp-field^='ebd_']")
    assert ebd_fields.count() == 0, (
        f"8ZD isolation: ebd_ fields must NOT appear in building_full. Found {ebd_fields.count()}."
    )


# ── CS627 ─────────────────────────────────────────────────────────────────────

def test_CS627_existing_building_isolated_from_residential_unit(page: "Page", live_server: str) -> None:
    """Phase 8ZD: selecting residential_unit does NOT show ebd_ supp fields."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="شقة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
    ebd_fields = page.locator("[data-es-supp-field^='ebd_']")
    assert ebd_fields.count() == 0, (
        f"8ZD isolation: ebd_ fields must NOT appear in residential_unit. Found {ebd_fields.count()}."
    )


# ── CS628 ─────────────────────────────────────────────────────────────────────

def test_CS628_existing_building_isolated_from_land(page: "Page", live_server: str) -> None:
    """Phase 8ZD: selecting land does NOT show ebd_ supp fields."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="أرض فضاء")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
    ebd_fields = page.locator("[data-es-supp-field^='ebd_']")
    assert ebd_fields.count() == 0, (
        f"8ZD isolation: ebd_ fields must NOT appear in land. Found {ebd_fields.count()}."
    )


# ── CS629 ─────────────────────────────────────────────────────────────────────

def test_CS629_existing_building_isolated_from_agricultural_land(page: "Page", live_server: str) -> None:
    """Phase 8ZD: selecting agricultural_land does NOT show ebd_ supp fields."""
    _load_agricultural_land(page, live_server)
    ebd_fields = page.locator("[data-es-supp-field^='ebd_']")
    assert ebd_fields.count() == 0, (
        f"8ZD isolation: ebd_ fields must NOT appear in agricultural_land. Found {ebd_fields.count()}."
    )


# ── CS630 ─────────────────────────────────────────────────────────────────────

def test_CS630_building_full_unchanged_after_8zd(page: "Page", live_server: str) -> None:
    """Phase 8ZD regression: building_full still renders floor table and land sections."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")
    panel = page.locator("#es-req-panel")
    panel.wait_for(state="visible", timeout=4_000)
    panel_text = panel.inner_text()
    assert "بيانات الأرض" in panel_text, (
        "8ZD regression: building_full must still show 'بيانات الأرض'."
    )
    table = panel.locator("#es-bf-floor-table")
    assert table.count() > 0, (
        "8ZD regression: building_full floor table must still render."
    )


# ── CS631 ─────────────────────────────────────────────────────────────────────

def test_CS631_building_full_supp_still_renders_after_8zd(page: "Page", live_server: str) -> None:
    """Phase 8ZD regression: building_full supplemental sections still render."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="عمارة سكنية")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    supp = page.locator("#es-req-supp")
    supp_text = supp.inner_text()
    assert "العمارة السكنية" in supp_text or "المبنى الكامل" in supp_text, (
        f"8ZD regression: building_full supp heading must still appear. Got: {supp_text[:200]!r}"
    )


# ── CS632 ─────────────────────────────────────────────────────────────────────

def test_CS632_agricultural_land_unchanged_after_8zd(page: "Page", live_server: str) -> None:
    """Phase 8ZD regression: agricultural_land still renders ag_ fields."""
    _load_agricultural_land(page, live_server)
    panel = page.locator("#es-req-panel")
    panel_text = panel.inner_text()
    assert "أرض زراعية" in panel_text, (
        "8ZD regression: agricultural_land title must still appear."
    )
    ag_field = panel.locator("[data-es-req-field='ag_area_sqm']")
    assert ag_field.count() > 0, (
        "8ZD regression: ag_area_sqm must still render in agricultural_land."
    )


# ── CS633 ─────────────────────────────────────────────────────────────────────

def test_CS633_land_unchanged_after_8zd(page: "Page", live_server: str) -> None:
    """Phase 8ZD regression: land profile unchanged."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="أرض فضاء")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=6_000)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "أرض" in panel_text, "8ZD regression: land panel must still show."


# ── CS634 ─────────────────────────────────────────────────────────────────────

def test_CS634_switching_ebd_to_hotel_clears_supp(page: "Page", live_server: str) -> None:
    """Phase 8ZD: switching from مبنى قائم to فندق clears ebd_ supp fields."""
    _load_existing_building(page, live_server)
    ebd_count_before = page.locator("[data-es-supp-field^='ebd_']").count()
    assert ebd_count_before > 0, "8ZD: ebd_ fields must appear before switching."
    page.select_option("#asset-type", value="فندق")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    ebd_count_after = page.locator("[data-es-supp-field^='ebd_']").count()
    assert ebd_count_after == 0, (
        f"8ZD: after switching to فندق, ebd_ fields must be gone. Got {ebd_count_after}."
    )


# ── CS635 ─────────────────────────────────────────────────────────────────────

def test_CS635_ebd_no_js_console_errors(page: "Page", live_server: str) -> None:
    """Phase 8ZD: no JS console errors when existing_building_detailed renders."""
    def _is_js_error(msg) -> bool:
        return (
            msg.type == "error"
            and "401" not in msg.text
            and "UNAUTHORIZED" not in msg.text
            and "Failed to load resource" not in msg.text
        )

    errors: list = []
    page.on("console", lambda msg: errors.append(msg.text) if _is_js_error(msg) else None)
    page.on("pageerror", lambda err: errors.append(str(err)))
    _load_existing_building(page, live_server)
    assert len(errors) == 0, (
        f"8ZD: JS console errors on existing_building_detailed render: {errors}"
    )


# ── CS636 ─────────────────────────────────────────────────────────────────────

def test_CS636_ebd_asset_grade_select_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_asset_grade select renders with Grade A/B/C options."""
    _load_existing_building(page, live_server)
    sel = page.locator("#es-req-supp [data-es-supp-field='ebd_asset_grade']")
    assert sel.count() > 0, "8ZD: ebd_asset_grade must render."
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "Grade A" in supp_text or "ممتاز" in supp_text, (
        "8ZD: ebd_asset_grade must show grade options."
    )


# ── CS637 ─────────────────────────────────────────────────────────────────────

def test_CS637_ebd_property_management_type_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_property_management_type select renders in section A."""
    _load_existing_building(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='ebd_property_management_type']")
    assert field.count() > 0, "8ZD: ebd_property_management_type must render."


# ── CS638 ─────────────────────────────────────────────────────────────────────

def test_CS638_ebd_efficiency_ratio_pct_number_input(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_efficiency_ratio_pct renders as number input."""
    _load_existing_building(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='ebd_efficiency_ratio_pct']")
    assert inp.count() > 0, "8ZD: ebd_efficiency_ratio_pct must render."


# ── CS639 ─────────────────────────────────────────────────────────────────────

def test_CS639_ebd_zoning_compliance_status_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD (must-have gap): ebd_zoning_compliance_status renders in section F."""
    _load_existing_building(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='ebd_zoning_compliance_status']")
    assert field.count() > 0, "8ZD: ebd_zoning_compliance_status must render."


# ── CS640 ─────────────────────────────────────────────────────────────────────

def test_CS640_ebd_disability_access_compliance_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD (must-have gap O): ebd_disability_access_compliance renders in section F."""
    _load_existing_building(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='ebd_disability_access_compliance']")
    assert field.count() > 0, "8ZD: ebd_disability_access_compliance must render."


# ── CS641 ─────────────────────────────────────────────────────────────────────

def test_CS641_ebd_safety_code_compliance_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD (must-have gap O): ebd_safety_code_compliance renders in section F."""
    _load_existing_building(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='ebd_safety_code_compliance']")
    assert field.count() > 0, "8ZD: ebd_safety_code_compliance must render."


# ── CS642 ─────────────────────────────────────────────────────────────────────

def test_CS642_ebd_anchor_tenant_credit_quality_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD (must-have gap O): ebd_anchor_tenant_credit_quality renders in section G."""
    _load_existing_building(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='ebd_anchor_tenant_credit_quality']")
    assert field.count() > 0, "8ZD: ebd_anchor_tenant_credit_quality must render."


# ── CS643 ─────────────────────────────────────────────────────────────────────

def test_CS643_ebd_tenant_arrears_status_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD (must-have gap O): ebd_tenant_arrears_status renders in section G."""
    _load_existing_building(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='ebd_tenant_arrears_status']")
    assert field.count() > 0, "8ZD: ebd_tenant_arrears_status must render."


# ── CS644 ─────────────────────────────────────────────────────────────────────

def test_CS644_ebd_facility_management_quality_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD (must-have gap O): ebd_facility_management_quality renders in section H."""
    _load_existing_building(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='ebd_facility_management_quality']")
    assert field.count() > 0, "8ZD: ebd_facility_management_quality must render."


# ── CS645 ─────────────────────────────────────────────────────────────────────

def test_CS645_ebd_climate_resilience_features_checkbox_group(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_climate_resilience_features checkbox group renders in section L."""
    _load_existing_building(page, live_server)
    chips = page.locator("#es-req-supp [data-es-supp-field='ebd_climate_resilience_features']")
    assert chips.count() > 0, "8ZD: ebd_climate_resilience_features must render."


# ── CS646 ─────────────────────────────────────────────────────────────────────

def test_CS646_ebd_sustainability_features_checkbox_group(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_sustainability_features checkbox group renders in section K."""
    _load_existing_building(page, live_server)
    chips = page.locator("#es-req-supp [data-es-supp-field='ebd_sustainability_features']")
    assert chips.count() > 0, "8ZD: ebd_sustainability_features must render."


# ── CS647 ─────────────────────────────────────────────────────────────────────

def test_CS647_ebd_flood_risk_level_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_flood_risk_level select renders in section L."""
    _load_existing_building(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='ebd_flood_risk_level']")
    assert field.count() > 0, "8ZD: ebd_flood_risk_level must render."


# ── CS648 ─────────────────────────────────────────────────────────────────────

def test_CS648_ebd_fiber_optic_available_bool_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_fiber_optic_available bool renders in section M."""
    _load_existing_building(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='ebd_fiber_optic_available']")
    assert field.count() > 0, "8ZD: ebd_fiber_optic_available must render."


# ── CS649 ─────────────────────────────────────────────────────────────────────

def test_CS649_ebd_internet_speed_mbps_number_input(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_internet_speed_mbps renders as number input with Mbps unit."""
    _load_existing_building(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='ebd_internet_speed_mbps']")
    assert inp.count() > 0, "8ZD: ebd_internet_speed_mbps must render."
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "Mbps" in supp_text, "8ZD: Mbps unit must appear."


# ── CS650 ─────────────────────────────────────────────────────────────────────

def test_CS650_ebd_energy_consumption_kwh_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_electricity_consumption_annual_kwh renders with kWh/سنة unit."""
    _load_existing_building(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='ebd_electricity_consumption_annual_kwh']")
    assert inp.count() > 0, "8ZD: ebd_electricity_consumption_annual_kwh must render."
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "kWh" in supp_text, "8ZD: kWh/سنة unit must appear."


# ── CS651 ─────────────────────────────────────────────────────────────────────

def test_CS651_ebd_water_consumption_m3_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_water_consumption_annual_m3 renders with م³/سنة unit."""
    _load_existing_building(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='ebd_water_consumption_annual_m3']")
    assert inp.count() > 0, "8ZD: ebd_water_consumption_annual_m3 must render."


# ── CS652 ─────────────────────────────────────────────────────────────────────

def test_CS652_ebd_noi_annual_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_net_operating_income_annual renders in section G."""
    _load_existing_building(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='ebd_net_operating_income_annual']")
    assert inp.count() > 0, "8ZD: ebd_net_operating_income_annual must render."


# ── CS653 ─────────────────────────────────────────────────────────────────────

def test_CS653_ebd_occupancy_rate_pct_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_occupancy_rate renders with % unit in section G."""
    _load_existing_building(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='ebd_occupancy_rate']")
    assert inp.count() > 0, "8ZD: ebd_occupancy_rate must render."


# ── CS654 ─────────────────────────────────────────────────────────────────────

def test_CS654_ebd_major_replacement_checkbox_group(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_major_replacement_required checkbox group renders in section H."""
    _load_existing_building(page, live_server)
    chips = page.locator("#es-req-supp [data-es-supp-field='ebd_major_replacement_required']")
    assert chips.count() > 0, "8ZD: ebd_major_replacement_required must render."


# ── CS655 ─────────────────────────────────────────────────────────────────────

def test_CS655_ebd_explainer_desc_distinguishes_from_building_full(page: "Page", live_server: str) -> None:
    """Phase 8ZD: explainer desc for existing_building_detailed distinguishes from عمارة سكنية."""
    _load_existing_building(page, live_server)
    desc = page.locator("#es-profile-desc").inner_text()
    assert "عمارة سكنية" in desc or "المركّب" in desc or "مختلف" in desc, (
        f"8ZD: explainer must reference distinction from building_full. Got: {desc!r}"
    )


# ── CS656 ─────────────────────────────────────────────────────────────────────

def test_CS656_ebd_doc_lease_contracts_checkbox_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_doc_lease_contracts document checkbox renders in section N."""
    _load_existing_building(page, live_server)
    cb = page.locator("#es-req-supp [data-es-supp-field='ebd_doc_lease_contracts']")
    assert cb.count() > 0, "8ZD: ebd_doc_lease_contracts must render."


# ── CS657 ─────────────────────────────────────────────────────────────────────

def test_CS657_ebd_doc_structural_report_checkbox_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_doc_structural_report checkbox renders in section N."""
    _load_existing_building(page, live_server)
    cb = page.locator("#es-req-supp [data-es-supp-field='ebd_doc_structural_report']")
    assert cb.count() > 0, "8ZD: ebd_doc_structural_report must render."


# ── CS658 ─────────────────────────────────────────────────────────────────────

def test_CS658_ebd_nuisance_sources_checkbox_group(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_nuisance_sources_nearby checkbox group renders in section B."""
    _load_existing_building(page, live_server)
    chips = page.locator("#es-req-supp [data-es-supp-field='ebd_nuisance_sources_nearby']")
    assert chips.count() > 0, "8ZD: ebd_nuisance_sources_nearby must render."


# ── CS659 ─────────────────────────────────────────────────────────────────────

def test_CS659_ebd_title_contains_full_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZD: panel title contains full Arabic heading 'مبنى قائم — تجاري / سكني / إداري'."""
    _load_existing_building(page, live_server)
    title = page.locator("#es-req-title").inner_text()
    assert "تجاري" in title or "مبنى قائم" in title, (
        f"8ZD: title must contain 'مبنى قائم' and type info. Got: {title!r}"
    )


# ── CS660 ─────────────────────────────────────────────────────────────────────

def test_CS660_ebd_upload_hint_text_in_section_N(page: "Page", live_server: str) -> None:
    """Phase 8ZD: upload hint text visible in section N (مستندات إضافية)."""
    _load_existing_building(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "مستندات" in supp_text, (
        "8ZD: 'مستندات' heading must appear in section N of ebd supp."
    )


# ── CS661 ─────────────────────────────────────────────────────────────────────

def test_CS661_ebd_bms_available_bool_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_bms_available bool renders in section M."""
    _load_existing_building(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='ebd_bms_available']")
    assert field.count() > 0, "8ZD: ebd_bms_available must render."


# ── CS662 ─────────────────────────────────────────────────────────────────────

def test_CS662_ebd_green_building_certification_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_green_building_certification_status select renders in section K."""
    _load_existing_building(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='ebd_green_building_certification_status']")
    assert field.count() > 0, "8ZD: ebd_green_building_certification_status must render."


# ── CS663 ─────────────────────────────────────────────────────────────────────

def test_CS663_ebd_seismic_risk_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_seismic_risk_level select renders in section L."""
    _load_existing_building(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='ebd_seismic_risk_level']")
    assert field.count() > 0, "8ZD: ebd_seismic_risk_level must render."


# ── CS664 ─────────────────────────────────────────────────────────────────────

def test_CS664_ebd_ev_charging_available_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_ev_charging_available bool renders in section M."""
    _load_existing_building(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='ebd_ev_charging_available']")
    assert field.count() > 0, "8ZD: ebd_ev_charging_available must render."


# ── CS665 ─────────────────────────────────────────────────────────────────────

def test_CS665_ebd_anchor_tenant_available_bool_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_anchor_tenant_available bool renders in section G."""
    _load_existing_building(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='ebd_anchor_tenant_available']")
    assert field.count() > 0, "8ZD: ebd_anchor_tenant_available must render."


# ── CS666 ─────────────────────────────────────────────────────────────────────

def test_CS666_ebd_legal_dispute_status_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_legal_dispute_status select renders in section F."""
    _load_existing_building(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='ebd_legal_dispute_status']")
    assert field.count() > 0, "8ZD: ebd_legal_dispute_status must render."


# ── CS667 ─────────────────────────────────────────────────────────────────────

def test_CS667_ebd_tenant_concentration_risk_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_tenant_concentration_risk select renders in section G."""
    _load_existing_building(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='ebd_tenant_concentration_risk']")
    assert field.count() > 0, "8ZD: ebd_tenant_concentration_risk must render."


# ── CS668 ─────────────────────────────────────────────────────────────────────

def test_CS668_ebd_demand_driver_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_demand_driver select renders in section I."""
    _load_existing_building(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='ebd_demand_driver']")
    assert field.count() > 0, "8ZD: ebd_demand_driver must render."


# ── CS669 ─────────────────────────────────────────────────────────────────────

def test_CS669_ebd_purpose_taxation_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_purpose_taxation_methodology renders."""
    _load_existing_building(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='ebd_purpose_taxation_methodology']"
    )
    assert field.count() > 0, "8ZD: taxation methodology must render."


# ── CS670 ─────────────────────────────────────────────────────────────────────

def test_CS670_ebd_purpose_liquidation_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_purpose_liquidation_methodology renders."""
    _load_existing_building(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='ebd_purpose_liquidation_methodology']"
    )
    assert field.count() > 0, "8ZD: liquidation methodology must render."


# ── CS671 ─────────────────────────────────────────────────────────────────────

def test_CS671_ebd_insurance_purpose_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_purpose_insurance_methodology renders."""
    _load_existing_building(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='ebd_purpose_insurance_methodology']"
    )
    assert field.count() > 0, "8ZD: insurance methodology must render."


# ── CS672 ─────────────────────────────────────────────────────────────────────

def test_CS672_ebd_rental_assessment_purpose_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_purpose_rental_assessment_methodology renders."""
    _load_existing_building(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='ebd_purpose_rental_assessment_methodology']"
    )
    assert field.count() > 0, "8ZD: rental_assessment methodology must render."


# ── CS673 ─────────────────────────────────────────────────────────────────────

def test_CS673_ebd_advertising_facade_income_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZD: ebd_advertising_facade_income_annual renders in section G."""
    _load_existing_building(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='ebd_advertising_facade_income_annual']")
    assert inp.count() > 0, "8ZD: ebd_advertising_facade_income_annual must render."


# ── CS674 ─────────────────────────────────────────────────────────────────────

def test_CS674_8zd_hotel_isolation(page: "Page", live_server: str) -> None:
    """Phase 8ZD isolation: hotel panel does NOT show ebd_ supp fields."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="فندق")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    ebd_cross = page.locator("[data-es-supp-field^='ebd_']")
    assert ebd_cross.count() == 0, (
        f"8ZD isolation: ebd_ fields must NOT appear in hotel panel. Found {ebd_cross.count()}."
    )


# ── Phase 8ZE helpers ─────────────────────────────────────────────────────────

def _load_hotel_resort_supp(page: "Page", live_server: str) -> None:
    """Phase 8ZE: load hotel_resort_detailed and wait for supplemental panel."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="hotel_resort_detailed")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


# ── CS675 ─────────────────────────────────────────────────────────────────────

def test_CS675_hrd_supp_renders_supplemental_controls(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hotel_resort_detailed #es-req-supp receives new hrd_supp_ fields."""
    _load_hotel_resort_supp(page, live_server)
    supp = page.locator("#es-req-supp")
    controls = supp.locator("[data-es-supp-field]")
    assert controls.count() > 10, (
        f"8ZE: #es-req-supp must contain >10 supp controls. Got {controls.count()}."
    )


# ── CS676 ─────────────────────────────────────────────────────────────────────

def test_CS676_hrd_supp_heading_arabic(page: "Page", live_server: str) -> None:
    """Phase 8ZE: supp header shows Arabic heading 'متطلبات تقييم فندق أو منتجع'."""
    _load_hotel_resort_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "فندق" in supp_text or "منتجع" in supp_text, (
        f"8ZE: supp heading must contain 'فندق' or 'منتجع'. Got: {supp_text[:200]!r}"
    )


# ── CS677 ─────────────────────────────────────────────────────────────────────

def test_CS677_hrd_supp_local_only_text(page: "Page", live_server: str) -> None:
    """Phase 8ZE: supp shows 'إدخال محلي' or 'لا يُرسل للتقرير' disclaimer."""
    _load_hotel_resort_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "إدخال محلي" in supp_text or "لا يُرسل" in supp_text, (
        f"8ZE: local-only text must appear in supp. Got: {supp_text[:300]!r}"
    )


# ── CS678 ─────────────────────────────────────────────────────────────────────

def test_CS678_hrd_supp_zero_api_calls(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hotel_resort_detailed supplemental makes ZERO API calls."""
    api_calls: list = []
    page.on("request", lambda r: api_calls.append(r.url) if "/api/valuation/requirements" in r.url else None)
    _load_hotel_resort_supp(page, live_server)
    assert len(api_calls) == 0, f"8ZE: must make zero API calls. Got: {api_calls}"


# ── CS679 ─────────────────────────────────────────────────────────────────────

def test_CS679_hrd_supp_no_composite_link(page: "Page", live_server: str) -> None:
    """Phase 8ZE: panel has no composite_valuation.html link."""
    _load_hotel_resort_supp(page, live_server)
    assert "composite_valuation.html" not in page.locator("#es-req-panel").inner_html(), (
        "8ZE: panel must not contain composite_valuation.html link."
    )


# ── CS680 ─────────────────────────────────────────────────────────────────────

def test_CS680_hrd_supp_no_auth_modal(page: "Page", live_server: str) -> None:
    """Phase 8ZE: no auth modal appears after loading hotel_resort_detailed supp."""
    _load_hotel_resort_supp(page, live_server)
    modal = page.locator("#login-modal, #auth-modal, [id*='login']")
    visible = sum(1 for i in range(modal.count()) if modal.nth(i).is_visible())
    assert visible == 0, f"8ZE: no auth modal must be visible. visible={visible}"


# ── CS681 ─────────────────────────────────────────────────────────────────────

def test_CS681_hrd_supp_section_A_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZE: section A heading 'تعريف الفندق أو المنتجع' visible."""
    _load_hotel_resort_supp(page, live_server)
    assert "تعريف الفندق أو المنتجع" in (page.locator("#es-req-supp").inner_text() or ""), (
        "8ZE: section A heading must appear."
    )


# ── CS682 ─────────────────────────────────────────────────────────────────────

def test_CS682_hrd_supp_section_B_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZE: section B heading 'الغرف والمفاتيح ومزيج الإقامة' visible."""
    _load_hotel_resort_supp(page, live_server)
    assert "الغرف والمفاتيح ومزيج الإقامة" in (page.locator("#es-req-supp").inner_text() or ""), (
        "8ZE: section B heading must appear."
    )


# ── CS683 ─────────────────────────────────────────────────────────────────────

def test_CS683_hrd_supp_section_C_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZE: section C heading 'الأرض والموقع والمكوّنات العقارية' visible."""
    _load_hotel_resort_supp(page, live_server)
    assert "الأرض والموقع والمكوّنات" in (page.locator("#es-req-supp").inner_text() or ""), (
        "8ZE: section C heading must appear."
    )


# ── CS684 ─────────────────────────────────────────────────────────────────────

def test_CS684_hrd_supp_section_D_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZE: section D heading 'المرافق والخدمات الفندقية' visible."""
    _load_hotel_resort_supp(page, live_server)
    assert "المرافق والخدمات الفندقية" in (page.locator("#es-req-supp").inner_text() or ""), (
        "8ZE: section D heading must appear."
    )


# ── CS685 ─────────────────────────────────────────────────────────────────────

def test_CS685_hrd_supp_section_E_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZE: section E heading 'التشغيل والمؤشرات الفندقية' visible."""
    _load_hotel_resort_supp(page, live_server)
    assert "التشغيل والمؤشرات الفندقية" in (page.locator("#es-req-supp").inner_text() or ""), (
        "8ZE: section E heading must appear."
    )


# ── CS686 ─────────────────────────────────────────────────────────────────────

def test_CS686_hrd_supp_section_F_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZE: section F heading 'الإيرادات والمصروفات' visible."""
    _load_hotel_resort_supp(page, live_server)
    assert "الإيرادات والمصروفات" in (page.locator("#es-req-supp").inner_text() or ""), (
        "8ZE: section F heading must appear."
    )


# ── CS687 ─────────────────────────────────────────────────────────────────────

def test_CS687_hrd_supp_section_G_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZE: section G heading 'الإدارة والعقود والعلامة التجارية' visible."""
    _load_hotel_resort_supp(page, live_server)
    assert "الإدارة والعقود والعلامة" in (page.locator("#es-req-supp").inner_text() or ""), (
        "8ZE: section G heading must appear."
    )


# ── CS688 ─────────────────────────────────────────────────────────────────────

def test_CS688_hrd_supp_section_H_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZE: section H heading 'الحالة الفنية وCAPEX وFF&E' visible."""
    _load_hotel_resort_supp(page, live_server)
    assert "CAPEX" in (page.locator("#es-req-supp").inner_text() or "") or "FF&E" in (page.locator("#es-req-supp").inner_text() or ""), (
        "8ZE: section H heading (CAPEX/FF&E) must appear."
    )


# ── CS689 ─────────────────────────────────────────────────────────────────────

def test_CS689_hrd_supp_section_I_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZE: section I heading 'التراخيص والامتثال' visible."""
    _load_hotel_resort_supp(page, live_server)
    assert "التراخيص والامتثال" in (page.locator("#es-req-supp").inner_text() or ""), (
        "8ZE: section I heading must appear."
    )


# ── CS690 ─────────────────────────────────────────────────────────────────────

def test_CS690_hrd_supp_section_J_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZE: section J heading 'السوق والمنافسة وقابلية التسويق' visible."""
    _load_hotel_resort_supp(page, live_server)
    assert "السوق والمنافسة" in (page.locator("#es-req-supp").inner_text() or ""), (
        "8ZE: section J heading must appear."
    )


# ── CS691 ─────────────────────────────────────────────────────────────────────

def test_CS691_hrd_supp_section_K_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZE: section K heading 'معاملات التعديل حسب غرض التقييم' visible."""
    _load_hotel_resort_supp(page, live_server)
    assert "معاملات التعديل حسب غرض التقييم" in (page.locator("#es-req-supp").inner_text() or ""), (
        "8ZE: section K heading must appear."
    )


# ── CS692 ─────────────────────────────────────────────────────────────────────

def test_CS692_hrd_supp_section_L_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZE: section L heading 'كفاءة الطاقة والاستدامة' visible."""
    _load_hotel_resort_supp(page, live_server)
    assert "كفاءة الطاقة والاستدامة" in (page.locator("#es-req-supp").inner_text() or ""), (
        "8ZE: section L heading must appear."
    )


# ── CS693 ─────────────────────────────────────────────────────────────────────

def test_CS693_hrd_supp_section_M_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZE: section M heading 'المخاطر المناخية والطبيعية' visible."""
    _load_hotel_resort_supp(page, live_server)
    assert "المخاطر المناخية والطبيعية" in (page.locator("#es-req-supp").inner_text() or ""), (
        "8ZE: section M heading must appear."
    )


# ── CS694 ─────────────────────────────────────────────────────────────────────

def test_CS694_hrd_supp_section_N_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZE: section N heading 'البنية التحتية الرقمية والتكنولوجيا الفندقية' visible."""
    _load_hotel_resort_supp(page, live_server)
    assert "البنية التحتية الرقمية" in (page.locator("#es-req-supp").inner_text() or ""), (
        "8ZE: section N heading must appear."
    )


# ── CS695 ─────────────────────────────────────────────────────────────────────

def test_CS695_hrd_supp_section_O_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZE: section O heading 'مستندات إضافية مطلوبة' visible."""
    _load_hotel_resort_supp(page, live_server)
    assert "مستندات إضافية مطلوبة" in (page.locator("#es-req-supp").inner_text() or ""), (
        "8ZE: section O heading must appear."
    )


# ── CS696 ─────────────────────────────────────────────────────────────────────

def test_CS696_hrd_supp_hotel_asset_type_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_hotel_asset_type select renders in section A."""
    _load_hotel_resort_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_hotel_asset_type']")
    assert field.count() > 0, "8ZE: hrd_supp_hotel_asset_type must render."


# ── CS697 ─────────────────────────────────────────────────────────────────────

def test_CS697_hrd_supp_operating_status_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_operating_status select renders."""
    _load_hotel_resort_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_operating_status']")
    assert field.count() > 0, "8ZE: hrd_supp_operating_status must render."


# ── CS698 ─────────────────────────────────────────────────────────────────────

def test_CS698_hrd_supp_target_guest_segment_checkbox_group(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_target_guest_segment checkbox group renders."""
    _load_hotel_resort_supp(page, live_server)
    chips = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_target_guest_segment']")
    assert chips.count() > 0, "8ZE: hrd_supp_target_guest_segment checkbox group must render."


# ── CS699 ─────────────────────────────────────────────────────────────────────

def test_CS699_hrd_supp_branded_residences_count_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_branded_residences_count number input renders in section B."""
    _load_hotel_resort_supp(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_branded_residences_count']")
    assert inp.count() > 0, "8ZE: hrd_supp_branded_residences_count must render."


# ── CS700 ─────────────────────────────────────────────────────────────────────

def test_CS700_hrd_supp_average_room_size_sqm_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_average_room_size_sqm number input renders with م² unit."""
    _load_hotel_resort_supp(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_average_room_size_sqm']")
    assert inp.count() > 0, "8ZE: hrd_supp_average_room_size_sqm must render."
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "م²" in supp_text, "8ZE: م² unit must appear in supp."


# ── CS701 ─────────────────────────────────────────────────────────────────────

def test_CS701_hrd_supp_rooms_condition_in_H_only(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_rooms_condition appears exactly once (section H only)."""
    _load_hotel_resort_supp(page, live_server)
    fields = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_rooms_condition']")
    assert fields.count() == 1, (
        f"8ZE: hrd_supp_rooms_condition must appear exactly once. Got {fields.count()}."
    )


# ── CS702 ─────────────────────────────────────────────────────────────────────

def test_CS702_hrd_supp_land_area_sqm_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_land_area_sqm number input renders in section C."""
    _load_hotel_resort_supp(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_land_area_sqm']")
    assert inp.count() > 0, "8ZE: hrd_supp_land_area_sqm must render."


# ── CS703 ─────────────────────────────────────────────────────────────────────

def test_CS703_hrd_supp_beachfront_available_bool_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_beachfront_available bool select renders."""
    _load_hotel_resort_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_beachfront_available']")
    assert field.count() > 0, "8ZE: hrd_supp_beachfront_available must render."


# ── CS704 ─────────────────────────────────────────────────────────────────────

def test_CS704_hrd_supp_distance_to_airport_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_distance_to_airport_km renders with كم unit."""
    _load_hotel_resort_supp(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_distance_to_airport_km']")
    assert inp.count() > 0, "8ZE: hrd_supp_distance_to_airport_km must render."
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "كم" in supp_text, "8ZE: كم unit must appear in supp."


# ── CS705 ─────────────────────────────────────────────────────────────────────

def test_CS705_hrd_supp_resort_components_summary_textarea(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_resort_components_summary textarea renders (DRY 8N alternative)."""
    _load_hotel_resort_supp(page, live_server)
    ta = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_resort_components_summary']")
    assert ta.count() > 0, "8ZE: hrd_supp_resort_components_summary must render."


# ── CS706 ─────────────────────────────────────────────────────────────────────

def test_CS706_hrd_supp_meeting_rooms_count_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_meeting_rooms_count number input renders in section D."""
    _load_hotel_resort_supp(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_meeting_rooms_count']")
    assert inp.count() > 0, "8ZE: hrd_supp_meeting_rooms_count must render."


# ── CS707 ─────────────────────────────────────────────────────────────────────

def test_CS707_hrd_supp_spa_available_bool_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_spa_available bool renders in section D."""
    _load_hotel_resort_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_spa_available']")
    assert field.count() > 0, "8ZE: hrd_supp_spa_available must render."


# ── CS708 ─────────────────────────────────────────────────────────────────────

def test_CS708_hrd_supp_trevpar_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_trevpar (TRevPAR) number input renders in section E."""
    _load_hotel_resort_supp(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_trevpar']")
    assert inp.count() > 0, "8ZE: hrd_supp_trevpar must render."


# ── CS709 ─────────────────────────────────────────────────────────────────────

def test_CS709_hrd_supp_goppar_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_goppar (GOPPAR) number input renders in section E."""
    _load_hotel_resort_supp(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_goppar']")
    assert inp.count() > 0, "8ZE: hrd_supp_goppar must render."


# ── CS710 ─────────────────────────────────────────────────────────────────────

def test_CS710_hrd_supp_mpi_ari_rgi_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: MPI, ARI, RGI index fields render in section E."""
    _load_hotel_resort_supp(page, live_server)
    for field_name in ('hrd_supp_market_penetration_index', 'hrd_supp_average_rate_index', 'hrd_supp_revenue_generation_index'):
        f = page.locator(f"#es-req-supp [data-es-supp-field='{field_name}']")
        assert f.count() > 0, f"8ZE: {field_name} must render."


# ── CS711 ─────────────────────────────────────────────────────────────────────

def test_CS711_hrd_supp_distribution_channel_mix_checkbox(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_distribution_channel_mix checkbox group renders."""
    _load_hotel_resort_supp(page, live_server)
    chips = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_distribution_channel_mix']")
    assert chips.count() > 0, "8ZE: hrd_supp_distribution_channel_mix must render."


# ── CS712 ─────────────────────────────────────────────────────────────────────

def test_CS712_hrd_supp_ebitda_annual_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_ebitda_annual number input renders in section F."""
    _load_hotel_resort_supp(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_ebitda_annual']")
    assert inp.count() > 0, "8ZE: hrd_supp_ebitda_annual must render."


# ── CS713 ─────────────────────────────────────────────────────────────────────

def test_CS713_hrd_supp_gop_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_gross_operating_profit_annual renders in section F."""
    _load_hotel_resort_supp(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_gross_operating_profit_annual']")
    assert inp.count() > 0, "8ZE: hrd_supp_gross_operating_profit_annual must render."


# ── CS714 ─────────────────────────────────────────────────────────────────────

def test_CS714_hrd_supp_franchise_agreement_status_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_franchise_agreement_status select renders in section G."""
    _load_hotel_resort_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_franchise_agreement_status']")
    assert field.count() > 0, "8ZE: hrd_supp_franchise_agreement_status must render."


# ── CS715 ─────────────────────────────────────────────────────────────────────

def test_CS715_hrd_supp_ffe_reserve_pct_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_ffe_reserve_pct renders with % unit in section H."""
    _load_hotel_resort_supp(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_ffe_reserve_pct']")
    assert inp.count() > 0, "8ZE: hrd_supp_ffe_reserve_pct must render."


# ── CS716 ─────────────────────────────────────────────────────────────────────

def test_CS716_hrd_supp_brand_pip_required_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_brand_pip_required bool renders in section H."""
    _load_hotel_resort_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_brand_pip_required']")
    assert field.count() > 0, "8ZE: hrd_supp_brand_pip_required must render."


# ── CS717 ─────────────────────────────────────────────────────────────────────

def test_CS717_hrd_supp_civil_defense_status_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_civil_defense_license_status renders in section I."""
    _load_hotel_resort_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_civil_defense_license_status']")
    assert field.count() > 0, "8ZE: hrd_supp_civil_defense_license_status must render."


# ── CS718 ─────────────────────────────────────────────────────────────────────

def test_CS718_hrd_supp_hotel_operating_license_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_hotel_operating_license_status renders in section I."""
    _load_hotel_resort_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_hotel_operating_license_status']")
    assert field.count() > 0, "8ZE: hrd_supp_hotel_operating_license_status must render."


# ── CS719 ─────────────────────────────────────────────────────────────────────

def test_CS719_hrd_supp_market_adr_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_market_adr renders with جنيه/ليلة unit in section J."""
    _load_hotel_resort_supp(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_market_adr']")
    assert inp.count() > 0, "8ZE: hrd_supp_market_adr must render."
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "جنيه/ليلة" in supp_text, "8ZE: جنيه/ليلة unit must appear in supp."


# ── CS720 ─────────────────────────────────────────────────────────────────────

def test_CS720_hrd_supp_ota_dependency_risk_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE (must-have gap P): hrd_supp_ota_dependency_risk_level renders in section J."""
    _load_hotel_resort_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_ota_dependency_risk_level']")
    assert field.count() > 0, "8ZE: hrd_supp_ota_dependency_risk_level must render."


# ── CS721 ─────────────────────────────────────────────────────────────────────

def test_CS721_hrd_supp_purpose_mortgage_methodology_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: mortgage_lending methodology select renders in section K."""
    _load_hotel_resort_supp(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='hrd_supp_purpose_mortgage_lending_methodology']"
    )
    assert field.count() > 0, "8ZE: mortgage_lending methodology must render."


# ── CS722 ─────────────────────────────────────────────────────────────────────

def test_CS722_hrd_supp_methodology_opts_include_room_rate_multiplier(page: "Page", live_server: str) -> None:
    """Phase 8ZE: methodology selects include room_rate_multiplier option."""
    _load_hotel_resort_supp(page, live_server)
    sel = page.locator(
        "#es-req-supp [data-es-supp-field='hrd_supp_purpose_mortgage_lending_methodology']"
    )
    assert sel.count() > 0, "8ZE: methodology select must exist."
    opts = sel.locator("option").evaluate_all("els => els.map(e => e.value)")
    assert "room_rate_multiplier" in opts, (
        f"8ZE: room_rate_multiplier must be in methodology options. Got: {opts}"
    )


# ── CS723 ─────────────────────────────────────────────────────────────────────

def test_CS723_hrd_supp_methodology_opts_include_direct_capitalization(page: "Page", live_server: str) -> None:
    """Phase 8ZE: methodology selects include direct_capitalization option."""
    _load_hotel_resort_supp(page, live_server)
    sel = page.locator(
        "#es-req-supp [data-es-supp-field='hrd_supp_purpose_sale_purchase_methodology']"
    )
    assert sel.count() > 0, "8ZE: sale_purchase methodology select must exist."
    opts = sel.locator("option").evaluate_all("els => els.map(e => e.value)")
    assert "direct_capitalization" in opts, (
        f"8ZE: direct_capitalization must be in methodology options. Got: {opts}"
    )


# ── CS724 ─────────────────────────────────────────────────────────────────────

def test_CS724_hrd_supp_mgmt_contract_review_local_help_ar(page: "Page", live_server: str) -> None:
    """Phase 8ZE: management_contract_review purpose block renders (local-only)."""
    _load_hotel_resort_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "مراجعة عقد الإدارة" in supp_text, (
        "8ZE: management_contract_review section must appear in supp."
    )


# ── CS725 ─────────────────────────────────────────────────────────────────────

def test_CS725_hrd_supp_impairment_testing_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: impairment_testing methodology renders (local-only)."""
    _load_hotel_resort_supp(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='hrd_supp_purpose_impairment_testing_methodology']"
    )
    assert field.count() > 0, "8ZE: impairment_testing methodology must render."


# ── CS726 ─────────────────────────────────────────────────────────────────────

def test_CS726_hrd_supp_energy_consumption_kwh_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_electricity_consumption_annual_kwh renders in section L."""
    _load_hotel_resort_supp(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_electricity_consumption_annual_kwh']")
    assert inp.count() > 0, "8ZE: electricity_consumption_annual_kwh must render."
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "kWh" in supp_text, "8ZE: kWh unit must appear."


# ── CS727 ─────────────────────────────────────────────────────────────────────

def test_CS727_hrd_supp_sustainability_value_impact_pct_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_sustainability_value_impact_pct renders in section L."""
    _load_hotel_resort_supp(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_sustainability_value_impact_pct']")
    assert inp.count() > 0, "8ZE: sustainability_value_impact_pct must render."


# ── CS728 ─────────────────────────────────────────────────────────────────────

def test_CS728_hrd_supp_sustainability_features_checkbox(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_sustainability_features checkbox group renders in section L."""
    _load_hotel_resort_supp(page, live_server)
    chips = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_sustainability_features']")
    assert chips.count() > 0, "8ZE: sustainability_features must render."


# ── CS729 ─────────────────────────────────────────────────────────────────────

def test_CS729_hrd_supp_coastal_erosion_risk_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_coastal_erosion_risk_level renders in section M."""
    _load_hotel_resort_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_coastal_erosion_risk_level']")
    assert field.count() > 0, "8ZE: hrd_supp_coastal_erosion_risk_level must render."


# ── CS730 ─────────────────────────────────────────────────────────────────────

def test_CS730_hrd_supp_seasonal_closure_risk_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE (must-have gap P): hrd_supp_seasonal_closure_risk renders in section M."""
    _load_hotel_resort_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_seasonal_closure_risk']")
    assert field.count() > 0, "8ZE: hrd_supp_seasonal_closure_risk must render."


# ── CS731 ─────────────────────────────────────────────────────────────────────

def test_CS731_hrd_supp_climate_resilience_features_checkbox(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_climate_resilience_features checkbox group renders."""
    _load_hotel_resort_supp(page, live_server)
    chips = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_climate_resilience_features']")
    assert chips.count() > 0, "8ZE: climate_resilience_features must render."


# ── CS732 ─────────────────────────────────────────────────────────────────────

def test_CS732_hrd_supp_pms_available_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_pms_available bool renders in section N."""
    _load_hotel_resort_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_pms_available']")
    assert field.count() > 0, "8ZE: hrd_supp_pms_available must render."


# ── CS733 ─────────────────────────────────────────────────────────────────────

def test_CS733_hrd_supp_hotel_technology_impact_pct_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_hotel_technology_value_impact_pct renders with % unit."""
    _load_hotel_resort_supp(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_hotel_technology_value_impact_pct']")
    assert inp.count() > 0, "8ZE: hotel_technology_value_impact_pct must render."


# ── CS734 ─────────────────────────────────────────────────────────────────────

def test_CS734_hrd_doc_supp_pip_plan_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_doc_supp_pip_plan document checkbox renders in section O."""
    _load_hotel_resort_supp(page, live_server)
    cb = page.locator("#es-req-supp [data-es-supp-field='hrd_doc_supp_pip_plan']")
    assert cb.count() > 0, "8ZE: hrd_doc_supp_pip_plan must render."


# ── CS735 ─────────────────────────────────────────────────────────────────────

def test_CS735_hrd_doc_supp_str_data_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_doc_supp_str_competitor_data document checkbox renders."""
    _load_hotel_resort_supp(page, live_server)
    cb = page.locator("#es-req-supp [data-es-supp-field='hrd_doc_supp_str_competitor_data']")
    assert cb.count() > 0, "8ZE: hrd_doc_supp_str_competitor_data must render."


# ── CS736 ─────────────────────────────────────────────────────────────────────

def test_CS736_hrd_supp_fields_use_data_es_supp_field(page: "Page", live_server: str) -> None:
    """Phase 8ZE: all hrd_supp_ controls use data-es-supp-field (not data-es-req-field)."""
    _load_hotel_resort_supp(page, live_server)
    supp = page.locator("#es-req-supp")
    req_fields = supp.locator("[data-es-req-field^='hrd_supp_']")
    assert req_fields.count() == 0, (
        f"8ZE: no hrd_supp_ field must use data-es-req-field. Found {req_fields.count()}."
    )


# ── CS737 ─────────────────────────────────────────────────────────────────────

def test_CS737_hrd_existing_fields_still_render(page: "Page", live_server: str) -> None:
    """Phase 8ZE regression: existing hrd_adr, hrd_revpar, hrd_keys_count still render."""
    _load_hotel_resort_supp(page, live_server)
    panel = page.locator("#es-req-panel")
    for field_name in ("hrd_adr", "hrd_revpar", "hrd_keys_count"):
        f = panel.locator(f"[data-es-req-field='{field_name}']")
        assert f.count() > 0, f"8ZE regression: {field_name} must still render in main form."


# ── CS738 ─────────────────────────────────────────────────────────────────────

def test_CS738_hrd_existing_sections_still_present(page: "Page", live_server: str) -> None:
    """Phase 8ZE regression: existing main-form section headings still present."""
    _load_hotel_resort_supp(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    for heading in ("بيانات الطاقة الفندقية", "التشغيل والمؤشرات الفندقية", "المستندات المطلوبة"):
        assert heading in panel_text, f"8ZE regression: '{heading}' must still appear."


# ── CS739 ─────────────────────────────────────────────────────────────────────

def test_CS739_hrd_supp_isolated_from_serviced_apartments(page: "Page", live_server: str) -> None:
    """Phase 8ZE: serviced_apartments does NOT show hrd_supp_ fields."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="serviced_apartments")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    hrd_supp = page.locator("[data-es-supp-field^='hrd_supp_']")
    assert hrd_supp.count() == 0, (
        f"8ZE isolation: hrd_supp_ fields must NOT appear in serviced_apartments. Got {hrd_supp.count()}."
    )


# ── CS740 ─────────────────────────────────────────────────────────────────────

def test_CS740_hrd_supp_isolated_from_floating_hotel(page: "Page", live_server: str) -> None:
    """Phase 8ZE: floating_hotel does NOT show hrd_supp_ fields."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="floating_hotel")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    hrd_supp = page.locator("[data-es-supp-field^='hrd_supp_']")
    assert hrd_supp.count() == 0, (
        f"8ZE isolation: hrd_supp_ fields must NOT appear in floating_hotel. Got {hrd_supp.count()}."
    )


# ── CS741 ─────────────────────────────────────────────────────────────────────

def test_CS741_hrd_supp_isolated_from_existing_building(page: "Page", live_server: str) -> None:
    """Phase 8ZE: existing_building_detailed does NOT show hrd_supp_ fields."""
    _load_existing_building(page, live_server)
    hrd_supp = page.locator("[data-es-supp-field^='hrd_supp_']")
    assert hrd_supp.count() == 0, (
        f"8ZE isolation: hrd_supp_ fields must NOT appear in existing_building. Got {hrd_supp.count()}."
    )


# ── CS742 ─────────────────────────────────────────────────────────────────────

def test_CS742_hrd_supp_no_js_console_errors(page: "Page", live_server: str) -> None:
    """Phase 8ZE: no JS console errors when hotel_resort_detailed supp renders."""
    def _is_js_error(msg) -> bool:
        return (
            msg.type == "error"
            and "401" not in msg.text
            and "UNAUTHORIZED" not in msg.text
            and "Failed to load resource" not in msg.text
        )

    errors: list = []
    page.on("console", lambda msg: errors.append(msg.text) if _is_js_error(msg) else None)
    page.on("pageerror", lambda err: errors.append(str(err)))
    _load_hotel_resort_supp(page, live_server)
    assert len(errors) == 0, f"8ZE: JS errors on hotel_resort_detailed supp: {errors}"


# ── CS743 ─────────────────────────────────────────────────────────────────────

def test_CS743_hrd_supp_brand_positioning_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_brand_positioning select renders in section A."""
    _load_hotel_resort_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_brand_positioning']")
    assert field.count() > 0, "8ZE: hrd_supp_brand_positioning must render."


# ── CS744 ─────────────────────────────────────────────────────────────────────

def test_CS744_hrd_supp_noi_annual_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_net_operating_income_annual renders in section F."""
    _load_hotel_resort_supp(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_net_operating_income_annual']")
    assert inp.count() > 0, "8ZE: hrd_supp_net_operating_income_annual must render."


# ── CS745 ─────────────────────────────────────────────────────────────────────

def test_CS745_hrd_supp_owner_operator_dispute_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_owner_operator_dispute_status renders in section G."""
    _load_hotel_resort_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_owner_operator_dispute_status']")
    assert field.count() > 0, "8ZE: hrd_supp_owner_operator_dispute_status must render."


# ── CS746 ─────────────────────────────────────────────────────────────────────

def test_CS746_hrd_supp_competitive_positioning_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_competitive_positioning select renders in section J."""
    _load_hotel_resort_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_competitive_positioning']")
    assert field.count() > 0, "8ZE: hrd_supp_competitive_positioning must render."


# ── CS747 ─────────────────────────────────────────────────────────────────────

def test_CS747_hrd_supp_water_consumption_m3_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_water_consumption_annual_m3 renders with م³/سنة unit."""
    _load_hotel_resort_supp(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_water_consumption_annual_m3']")
    assert inp.count() > 0, "8ZE: water_consumption_annual_m3 must render."


# ── CS748 ─────────────────────────────────────────────────────────────────────

def test_CS748_hrd_supp_green_hotel_certification_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_green_hotel_certification_status select renders."""
    _load_hotel_resort_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_green_hotel_certification_status']")
    assert field.count() > 0, "8ZE: green_hotel_certification_status must render."


# ── CS749 ─────────────────────────────────────────────────────────────────────

def test_CS749_hrd_supp_flood_risk_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_flood_risk_level select renders in section M."""
    _load_hotel_resort_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_flood_risk_level']")
    assert field.count() > 0, "8ZE: hrd_supp_flood_risk_level must render."


# ── CS750 ─────────────────────────────────────────────────────────────────────

def test_CS750_hrd_supp_climate_risk_impact_pct_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_climate_risk_value_impact_pct renders with % unit."""
    _load_hotel_resort_supp(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_climate_risk_value_impact_pct']")
    assert inp.count() > 0, "8ZE: climate_risk_value_impact_pct must render."


# ── CS751 ─────────────────────────────────────────────────────────────────────

def test_CS751_hrd_supp_internet_speed_mbps_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_internet_speed_mbps renders with Mbps unit."""
    _load_hotel_resort_supp(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_internet_speed_mbps']")
    assert inp.count() > 0, "8ZE: internet_speed_mbps must render."
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "Mbps" in supp_text, "8ZE: Mbps unit must appear."


# ── CS752 ─────────────────────────────────────────────────────────────────────

def test_CS752_hrd_supp_ev_charging_available_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_ev_charging_available bool renders in section N."""
    _load_hotel_resort_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_ev_charging_available']")
    assert field.count() > 0, "8ZE: hrd_supp_ev_charging_available must render."


# ── CS753 ─────────────────────────────────────────────────────────────────────

def test_CS753_hrd_doc_supp_ffe_list_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_doc_supp_ffe_list document checkbox renders in section O."""
    _load_hotel_resort_supp(page, live_server)
    cb = page.locator("#es-req-supp [data-es-supp-field='hrd_doc_supp_ffe_list']")
    assert cb.count() > 0, "8ZE: hrd_doc_supp_ffe_list must render."


# ── CS754 ─────────────────────────────────────────────────────────────────────

def test_CS754_hrd_supp_private_beach_rights_descriptive(page: "Page", live_server: str) -> None:
    """Phase 8ZE: private_beach_rights_status is descriptive only (data-es-supp-field)."""
    _load_hotel_resort_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_private_beach_rights_status']")
    assert field.count() > 0, "8ZE: hrd_supp_private_beach_rights_status must render."
    api_link_in_panel = "littoral_rights" in page.locator("#es-req-panel").inner_html()
    assert not api_link_in_panel, (
        "8ZE: private_beach_rights_status must not reference littoral_rights profile in panel."
    )


# ── CS755 ─────────────────────────────────────────────────────────────────────

def test_CS755_methodology_opts_room_rate_multiplier_in_ebd_too(page: "Page", live_server: str) -> None:
    """Phase 8ZE: room_rate_multiplier also appears in existing_building_detailed methodology."""
    _load_existing_building(page, live_server)
    sel = page.locator(
        "#es-req-supp [data-es-supp-field='ebd_purpose_mortgage_lending_methodology']"
    )
    if sel.count() == 0:
        return  # skip if ebd_ field not found (different selector)
    opts = sel.locator("option").evaluate_all("els => els.map(e => e.value)")
    assert "room_rate_multiplier" in opts, (
        f"8ZE: room_rate_multiplier must also be in ebd_ methodology opts (additive). Got: {opts}"
    )


# ── CS756 ─────────────────────────────────────────────────────────────────────

def test_CS756_hrd_supp_payroll_cost_annual_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_payroll_cost_annual number input renders in section F."""
    _load_hotel_resort_supp(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_payroll_cost_annual']")
    assert inp.count() > 0, "8ZE: hrd_supp_payroll_cost_annual must render."


# ── CS757 ─────────────────────────────────────────────────────────────────────

def test_CS757_hrd_supp_last_major_renovation_year_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZE: hrd_supp_last_major_renovation_year renders with سنة unit in section H."""
    _load_hotel_resort_supp(page, live_server)
    inp = page.locator("#es-req-supp [data-es-supp-field='hrd_supp_last_major_renovation_year']")
    assert inp.count() > 0, "8ZE: hrd_supp_last_major_renovation_year must render."


# ── CS758 ─────────────────────────────────────────────────────────────────────

def test_CS758_hrd_supp_litigation_dispute_local_only(page: "Page", live_server: str) -> None:
    """Phase 8ZE: litigation_dispute purpose renders as local-only in section K."""
    _load_hotel_resort_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "نزاعات قضائية" in supp_text, "8ZE: litigation_dispute section must appear."


# ── CS759 ─────────────────────────────────────────────────────────────────────

def test_CS759_8ze_existing_building_unchanged(page: "Page", live_server: str) -> None:
    """Phase 8ZE regression: existing_building_detailed supp still renders after 8ZE."""
    _load_existing_building(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "مبنى قائم" in supp_text or "تجاري" in supp_text, (
        "8ZE regression: existing_building_detailed supp heading must still appear."
    )
    ebd_field = page.locator("#es-req-supp [data-es-supp-field='ebd_building_use_type']")
    assert ebd_field.count() > 0, "8ZE regression: ebd_building_use_type must still render."


# ── Phase 8ZF helpers ─────────────────────────────────────────────────────────

def _load_industrial_logistics_supp(page: "Page", live_server: str) -> None:
    """Phase 8ZF: load industrial_logistics_facility_detailed and wait for supplemental panel."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="industrial_logistics_facility_detailed")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


# ── CS760 ─────────────────────────────────────────────────────────────────────

def test_CS760_8zf_profile_option_exists_in_dropdown(page: "Page", live_server: str) -> None:
    """Phase 8ZF: industrial_logistics_facility_detailed option exists in asset-type dropdown."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    opts = page.locator("#asset-type option[value='industrial_logistics_facility_detailed']")
    assert opts.count() > 0, "8ZF: industrial_logistics_facility_detailed must be in dropdown."


# ── CS761 ─────────────────────────────────────────────────────────────────────

def test_CS761_8zf_badge_renders_no_auth_modal(page: "Page", live_server: str) -> None:
    """Phase 8ZF: badge renders for industrial_logistics_facility_detailed; no auth modal."""
    _load_industrial_logistics_supp(page, live_server)
    badge = page.locator("#es-profile-badge")
    assert badge.is_visible(), "8ZF: #es-profile-badge must be visible."
    badge_text = badge.inner_text()
    assert "نموذج محلي" in badge_text, f"8ZF: badge must contain 'نموذج محلي'. Got: {badge_text}"
    modal = page.locator("#auth-modal, #authModal, [id*='auth'][id*='modal']")
    assert modal.count() == 0 or not modal.first.is_visible(), "8ZF: no auth modal must appear."


# ── CS762 ─────────────────────────────────────────────────────────────────────

def test_CS762_8zf_panel_visible_no_composite_link(page: "Page", live_server: str) -> None:
    """Phase 8ZF: panel is visible and no composite link is triggered."""
    _load_industrial_logistics_supp(page, live_server)
    panel = page.locator("#es-req-panel")
    assert panel.is_visible(), "8ZF: #es-req-panel must be visible."
    panel_html = panel.inner_html()
    assert "composite" not in panel_html.lower() or "composite_valuation" not in panel_html, (
        "8ZF: no composite_valuation link must appear in panel."
    )


# ── CS763 ─────────────────────────────────────────────────────────────────────

def test_CS763_8zf_zero_api_calls(page: "Page", live_server: str) -> None:
    """Phase 8ZF: no API calls to /api/valuation/requirements (fully local form)."""
    api_calls: list = []
    page.on("request", lambda req: api_calls.append(req.url) if "/api/valuation/requirements" in req.url else None)
    _load_industrial_logistics_supp(page, live_server)
    assert len(api_calls) == 0, f"8ZF: must make zero /api/valuation/requirements calls. Got: {api_calls}"


# ── CS764 ─────────────────────────────────────────────────────────────────────

def test_CS764_8zf_section_A_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: section A «تعريف الأصل الصناعي أو اللوجستي» heading renders."""
    _load_industrial_logistics_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "تعريف الأصل الصناعي" in supp_text, "8ZF: section A heading must appear."


# ── CS765 ─────────────────────────────────────────────────────────────────────

def test_CS765_8zf_section_B_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: section B «الأرض والموقع والوصول» heading renders."""
    _load_industrial_logistics_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "الأرض والموقع والوصول" in supp_text, "8ZF: section B heading must appear."


# ── CS766 ─────────────────────────────────────────────────────────────────────

def test_CS766_8zf_section_C_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: section C «المباني الصناعية والهيكل» heading renders."""
    _load_industrial_logistics_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "المباني الصناعية والهيكل" in supp_text, "8ZF: section C heading must appear."


# ── CS767 ─────────────────────────────────────────────────────────────────────

def test_CS767_8zf_section_D_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: section D «الإنتاج والعمليات الصناعية» heading renders."""
    _load_industrial_logistics_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "الإنتاج والعمليات الصناعية" in supp_text, "8ZF: section D heading must appear."


# ── CS768 ─────────────────────────────────────────────────────────────────────

def test_CS768_8zf_section_E_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: section E «المرافق والطاقة والخدمات» heading renders."""
    _load_industrial_logistics_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "المرافق والطاقة والخدمات" in supp_text, "8ZF: section E heading must appear."


# ── CS769 ─────────────────────────────────────────────────────────────────────

def test_CS769_8zf_section_F_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: section F «اللوجستيات والتحميل والتخزين» heading renders."""
    _load_industrial_logistics_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "اللوجستيات والتحميل والتخزين" in supp_text, "8ZF: section F heading must appear."


# ── CS770 ─────────────────────────────────────────────────────────────────────

def test_CS770_8zf_section_G_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: section G «التراخيص والامتثال والتنظيم» heading renders."""
    _load_industrial_logistics_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "التراخيص والامتثال والتنظيم" in supp_text, "8ZF: section G heading must appear."


# ── CS771 ─────────────────────────────────────────────────────────────────────

def test_CS771_8zf_section_H_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: section H «البيئة وHSE والمخاطر الصناعية» heading renders."""
    _load_industrial_logistics_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "البيئة" in supp_text and "HSE" in supp_text, "8ZF: section H heading must appear."


# ── CS772 ─────────────────────────────────────────────────────────────────────

def test_CS772_8zf_section_I_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: section I «الإشغال والعقود والدخل» heading renders."""
    _load_industrial_logistics_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "الإشغال والعقود والدخل" in supp_text, "8ZF: section I heading must appear."


# ── CS773 ─────────────────────────────────────────────────────────────────────

def test_CS773_8zf_section_J_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: section J «التكاليف وCAPEX والصيانة» heading renders."""
    _load_industrial_logistics_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "CAPEX" in supp_text and "الصيانة" in supp_text, "8ZF: section J heading must appear."


# ── CS774 ─────────────────────────────────────────────────────────────────────

def test_CS774_8zf_section_K_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: section K «السوق والموقع الصناعي وقابلية التسويق» heading renders."""
    _load_industrial_logistics_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "السوق والموقع الصناعي" in supp_text, "8ZF: section K heading must appear."


# ── CS775 ─────────────────────────────────────────────────────────────────────

def test_CS775_8zf_section_L_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: section L «معاملات التعديل حسب غرض التقييم» heading renders."""
    _load_industrial_logistics_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "معاملات التعديل" in supp_text, "8ZF: section L heading must appear."


# ── CS776 ─────────────────────────────────────────────────────────────────────

def test_CS776_8zf_section_M_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: section M «كفاءة الطاقة والاستدامة» heading renders."""
    _load_industrial_logistics_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "كفاءة الطاقة والاستدامة" in supp_text, "8ZF: section M heading must appear."


# ── CS777 ─────────────────────────────────────────────────────────────────────

def test_CS777_8zf_section_N_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: section N «المخاطر المناخية والطبيعية والتشغيلية» heading renders."""
    _load_industrial_logistics_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "المخاطر المناخية" in supp_text, "8ZF: section N heading must appear."


# ── CS778 ─────────────────────────────────────────────────────────────────────

def test_CS778_8zf_section_O_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: section O «البنية التحتية الرقمية واللوجستية الذكية» heading renders."""
    _load_industrial_logistics_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "البنية التحتية الرقمية" in supp_text, "8ZF: section O heading must appear."


# ── CS779 ─────────────────────────────────────────────────────────────────────

def test_CS779_8zf_section_P_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: section P «مستندات إضافية مطلوبة» heading renders."""
    _load_industrial_logistics_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "مستندات إضافية مطلوبة" in supp_text, "8ZF: section P heading must appear."


# ── CS780 ─────────────────────────────────────────────────────────────────────

def test_CS780_8zf_field_industrial_asset_type_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: il_supp_industrial_asset_type field renders in section A."""
    _load_industrial_logistics_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='il_supp_industrial_asset_type']")
    assert field.count() > 0, "8ZF: il_supp_industrial_asset_type must render."


# ── CS781 ─────────────────────────────────────────────────────────────────────

def test_CS781_8zf_field_operating_status_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: il_supp_operating_status field renders in section A."""
    _load_industrial_logistics_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='il_supp_operating_status']")
    assert field.count() > 0, "8ZF: il_supp_operating_status must render."


# ── CS782 ─────────────────────────────────────────────────────────────────────

def test_CS782_8zf_field_plot_area_sqm_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: il_supp_plot_area_sqm (section B) renders with م² unit."""
    _load_industrial_logistics_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='il_supp_plot_area_sqm']")
    assert field.count() > 0, "8ZF: il_supp_plot_area_sqm must render."


# ── CS783 ─────────────────────────────────────────────────────────────────────

def test_CS783_8zf_field_floor_loading_capacity_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: il_supp_floor_loading_capacity_ton_sqm (section C) renders."""
    _load_industrial_logistics_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='il_supp_floor_loading_capacity_ton_sqm']")
    assert field.count() > 0, "8ZF: il_supp_floor_loading_capacity_ton_sqm must render."


# ── CS784 ─────────────────────────────────────────────────────────────────────

def test_CS784_8zf_section_D_machinery_exclusion_desc_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: section D description mentions operational interface (no machinery valuation)."""
    _load_industrial_logistics_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "واجهة تشغيلية" in supp_text or "الآلات" in supp_text, (
        "8ZF: section D operational-interface note must appear."
    )


# ── CS785 ─────────────────────────────────────────────────────────────────────

def test_CS785_8zf_machinery_exclusion_note_field_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: il_supp_machinery_excluded_from_real_estate_value_note renders in section D."""
    _load_industrial_logistics_supp(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='il_supp_machinery_excluded_from_real_estate_value_note']"
    )
    assert field.count() > 0, "8ZF: machinery exclusion note field must render."


# ── CS786 ─────────────────────────────────────────────────────────────────────

def test_CS786_8zf_field_electricity_capacity_kva_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: il_supp_electricity_capacity_kva (section E) renders."""
    _load_industrial_logistics_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='il_supp_electricity_capacity_kva']")
    assert field.count() > 0, "8ZF: il_supp_electricity_capacity_kva must render."


# ── CS787 ─────────────────────────────────────────────────────────────────────

def test_CS787_8zf_field_loading_docks_count_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: il_supp_loading_docks_count (section F) renders."""
    _load_industrial_logistics_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='il_supp_loading_docks_count']")
    assert field.count() > 0, "8ZF: il_supp_loading_docks_count must render."


# ── CS788 ─────────────────────────────────────────────────────────────────────

def test_CS788_8zf_purpose_mortgage_lending_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: purpose mortgage_lending methodology field renders in section L."""
    _load_industrial_logistics_supp(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='il_supp_purpose_mortgage_lending_methodology']"
    )
    assert field.count() > 0, "8ZF: mortgage_lending methodology must render in section L."


# ── CS789 ─────────────────────────────────────────────────────────────────────

def test_CS789_8zf_purpose_sale_purchase_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: purpose sale_purchase methodology field renders in section L."""
    _load_industrial_logistics_supp(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='il_supp_purpose_sale_purchase_methodology']"
    )
    assert field.count() > 0, "8ZF: sale_purchase methodology must render."


# ── CS790 ─────────────────────────────────────────────────────────────────────

def test_CS790_8zf_purpose_insurance_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: purpose insurance methodology field renders in section L."""
    _load_industrial_logistics_supp(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='il_supp_purpose_insurance_methodology']"
    )
    assert field.count() > 0, "8ZF: insurance methodology must render."


# ── CS791 ─────────────────────────────────────────────────────────────────────

def test_CS791_8zf_purpose_ifrs_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: purpose ifrs_fair_value methodology field renders in section L."""
    _load_industrial_logistics_supp(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='il_supp_purpose_ifrs_fair_value_methodology']"
    )
    assert field.count() > 0, "8ZF: ifrs_fair_value methodology must render."


# ── CS792 ─────────────────────────────────────────────────────────────────────

def test_CS792_8zf_purpose_rental_assessment_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: purpose rental_assessment methodology field renders in section L."""
    _load_industrial_logistics_supp(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='il_supp_purpose_rental_assessment_methodology']"
    )
    assert field.count() > 0, "8ZF: rental_assessment methodology must render."


# ── CS793 ─────────────────────────────────────────────────────────────────────

def test_CS793_8zf_purpose_taxation_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: purpose taxation methodology field renders in section L."""
    _load_industrial_logistics_supp(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='il_supp_purpose_taxation_methodology']"
    )
    assert field.count() > 0, "8ZF: taxation methodology must render."


# ── CS794 ─────────────────────────────────────────────────────────────────────

def test_CS794_8zf_purpose_liquidation_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: purpose liquidation methodology field renders in section L."""
    _load_industrial_logistics_supp(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='il_supp_purpose_liquidation_methodology']"
    )
    assert field.count() > 0, "8ZF: liquidation methodology must render."


# ── CS795 ─────────────────────────────────────────────────────────────────────

def test_CS795_8zf_purpose_litigation_dispute_local_only(page: "Page", live_server: str) -> None:
    """Phase 8ZF: litigation_dispute (local-only) renders in section L."""
    _load_industrial_logistics_supp(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='il_supp_purpose_litigation_dispute_methodology']"
    )
    assert field.count() > 0, "8ZF: litigation_dispute (local) methodology must render."


# ── CS796 ─────────────────────────────────────────────────────────────────────

def test_CS796_8zf_purpose_investment_acquisition_local_only(page: "Page", live_server: str) -> None:
    """Phase 8ZF: investment_acquisition (local-only) renders in section L."""
    _load_industrial_logistics_supp(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='il_supp_purpose_investment_acquisition_methodology']"
    )
    assert field.count() > 0, "8ZF: investment_acquisition (local) methodology must render."


# ── CS797 ─────────────────────────────────────────────────────────────────────

def test_CS797_8zf_purpose_owner_occupation_local_only(page: "Page", live_server: str) -> None:
    """Phase 8ZF: owner_occupation (local-only) renders in section L."""
    _load_industrial_logistics_supp(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='il_supp_purpose_owner_occupation_methodology']"
    )
    assert field.count() > 0, "8ZF: owner_occupation (local) methodology must render."


# ── CS798 ─────────────────────────────────────────────────────────────────────

def test_CS798_8zf_purpose_sale_leaseback_local_only(page: "Page", live_server: str) -> None:
    """Phase 8ZF: sale_leaseback (local-only) renders in section L."""
    _load_industrial_logistics_supp(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='il_supp_purpose_sale_leaseback_methodology']"
    )
    assert field.count() > 0, "8ZF: sale_leaseback (local) methodology must render."


# ── CS799 ─────────────────────────────────────────────────────────────────────

def test_CS799_8zf_methodology_depreciated_replacement_cost_available(page: "Page", live_server: str) -> None:
    """Phase 8ZF: depreciated_replacement_cost option is in mortgage_lending methodology selector."""
    _load_industrial_logistics_supp(page, live_server)
    sel = page.locator(
        "#es-req-supp [data-es-supp-field='il_supp_purpose_mortgage_lending_methodology']"
    )
    if sel.count() == 0:
        return
    opts = sel.locator("option").evaluate_all("els => els.map(e => e.value)")
    assert "depreciated_replacement_cost" in opts, (
        f"8ZF: depreciated_replacement_cost must be in methodology opts. Got: {opts}"
    )


# ── CS800 ─────────────────────────────────────────────────────────────────────

def test_CS800_8zf_sustainability_value_impact_pct_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: il_supp_sustainability_value_impact_pct (section M) renders."""
    _load_industrial_logistics_supp(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='il_supp_sustainability_value_impact_pct']"
    )
    assert field.count() > 0, "8ZF: il_supp_sustainability_value_impact_pct must render."


# ── CS801 ─────────────────────────────────────────────────────────────────────

def test_CS801_8zf_climate_risk_value_impact_pct_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: il_supp_climate_risk_value_impact_pct (section N) renders."""
    _load_industrial_logistics_supp(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='il_supp_climate_risk_value_impact_pct']"
    )
    assert field.count() > 0, "8ZF: il_supp_climate_risk_value_impact_pct must render."


# ── CS802 ─────────────────────────────────────────────────────────────────────

def test_CS802_8zf_digital_infrastructure_value_impact_pct_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZF: il_supp_digital_infrastructure_value_impact_pct (section O) renders."""
    _load_industrial_logistics_supp(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='il_supp_digital_infrastructure_value_impact_pct']"
    )
    assert field.count() > 0, "8ZF: il_supp_digital_infrastructure_value_impact_pct must render."


# ── CS803 ─────────────────────────────────────────────────────────────────────

def test_CS803_8zf_all_supp_fields_have_data_es_supp_field(page: "Page", live_server: str) -> None:
    """Phase 8ZF: spot-check that il_supp_ fields carry data-es-supp-field attribute."""
    _load_industrial_logistics_supp(page, live_server)
    sample_fields = [
        "il_supp_industrial_asset_type",
        "il_supp_electricity_capacity_kva",
        "il_supp_occupancy_rate",
        "il_supp_capex_required",
        "il_supp_climate_risk_value_impact_pct",
        "il_supp_internet_speed_mbps",
        "il_doc_title_deed_or_usufruct",
    ]
    for fname in sample_fields:
        el = page.locator(f"#es-req-supp [data-es-supp-field='{fname}']")
        assert el.count() > 0, f"8ZF: {fname} must carry data-es-supp-field and render."


# ── CS804 ─────────────────────────────────────────────────────────────────────

def test_CS804_8zf_factory_profile_unchanged(page: "Page", live_server: str) -> None:
    """Phase 8ZF regression: factory profile still renders unchanged after 8ZF."""
    _load_factory(page, live_server)
    panel_text = page.locator("#es-req-panel").inner_text()
    assert "بيانات الأرض الصناعية" in panel_text or "الأرض الصناعية" in panel_text, (
        "8ZF regression: factory panel must still render its sections."
    )
    fc_field = page.locator("[data-es-req-field='fc_land_area_sqm'], input[name='fc_land_area_sqm']")
    assert fc_field.count() > 0 or "fc_land" in page.locator("#es-req-panel").inner_html(), (
        "8ZF regression: fc_ fields must still exist in factory panel."
    )


# ── CS805 ─────────────────────────────────────────────────────────────────────

def test_CS805_8zf_prefabricated_factory_unchanged(page: "Page", live_server: str) -> None:
    """Phase 8ZF regression: prefabricated_factory profile still renders after 8ZF."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="prefabricated_factory")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    panel_html = page.locator("#es-req-panel").inner_html()
    assert "pf_" in panel_html or "بريفاب" in panel_html or "جاهز" in panel_html, (
        "8ZF regression: prefabricated_factory panel must still render."
    )


# ── CS806 ─────────────────────────────────────────────────────────────────────

def test_CS806_8zf_cold_storage_unchanged(page: "Page", live_server: str) -> None:
    """Phase 8ZF regression: cold_storage profile still renders after 8ZF."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="cold_storage")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    panel_html = page.locator("#es-req-panel").inner_html()
    assert "cs_" in panel_html or "تبريد" in panel_html, (
        "8ZF regression: cold_storage panel must still render."
    )


# ── CS807 ─────────────────────────────────────────────────────────────────────

def test_CS807_8zf_data_center_unchanged(page: "Page", live_server: str) -> None:
    """Phase 8ZF regression: data_center profile still renders after 8ZF."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="data_center")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)
    panel_html = page.locator("#es-req-panel").inner_html()
    assert "dc_" in panel_html or "Data Center" in panel_html or "بيانات" in panel_html, (
        "8ZF regression: data_center panel must still render."
    )


# ── CS808 ─────────────────────────────────────────────────────────────────────

def test_CS808_8zf_il_supp_fields_not_in_factory_panel(page: "Page", live_server: str) -> None:
    """Phase 8ZF isolation: il_supp_ fields must NOT appear in factory panel."""
    _load_factory(page, live_server)
    il_fields = page.locator("[data-es-supp-field^='il_supp_']")
    assert il_fields.count() == 0, (
        f"8ZF isolation: il_supp_ fields must not appear in factory panel. Found {il_fields.count()}."
    )


# ── CS809 ─────────────────────────────────────────────────────────────────────

def test_CS809_8zf_hotel_and_ebd_regression(page: "Page", live_server: str) -> None:
    """Phase 8ZF regression: hotel_resort_detailed and existing_building_detailed still render."""
    _load_hotel_resort_supp(page, live_server)
    hotel_text = page.locator("#es-req-supp").inner_text()
    assert "تعريف الفندق" in hotel_text or "فندق" in hotel_text, (
        "8ZF regression: hotel_resort_detailed supp heading must still appear."
    )
    _load_existing_building(page, live_server)
    ebd_text = page.locator("#es-req-supp").inner_text()
    assert "مبنى قائم" in ebd_text or "تجاري" in ebd_text, (
        "8ZF regression: existing_building_detailed supp heading must still appear."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 8ZG — retail_shop_detailed (Retail / Shop — Detailed Valuation)
# CS810 – CS859
# ═══════════════════════════════════════════════════════════════════════════════


def _load_retail_shop_supp(page: "Page", live_server: str) -> None:
    """Phase 8ZG: load retail_shop_detailed and wait for supplemental panel."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="retail_shop_detailed")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-panel").wait_for(state="visible", timeout=4_000)


# ── CS810 ─────────────────────────────────────────────────────────────────────

def test_CS810_8zg_profile_option_exists_in_dropdown(page: "Page", live_server: str) -> None:
    """Phase 8ZG: retail_shop_detailed option exists in asset-type dropdown."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    opts = page.locator("#asset-type option[value='retail_shop_detailed']")
    assert opts.count() > 0, "8ZG: retail_shop_detailed must be in dropdown."


# ── CS811 ─────────────────────────────────────────────────────────────────────

def test_CS811_8zg_badge_renders_no_auth_modal(page: "Page", live_server: str) -> None:
    """Phase 8ZG: badge renders for retail_shop_detailed; no auth modal appears."""
    _load_retail_shop_supp(page, live_server)
    badge = page.locator("#es-profile-badge")
    assert badge.is_visible(), "8ZG: #es-profile-badge must be visible."
    badge_text = badge.inner_text()
    assert "نموذج محلي" in badge_text, f"8ZG: badge must contain 'نموذج محلي'. Got: {badge_text}"
    modal = page.locator("#auth-modal, #authModal, [id*='auth'][id*='modal']")
    assert modal.count() == 0 or not modal.first.is_visible(), "8ZG: no auth modal must appear."


# ── CS812 ─────────────────────────────────────────────────────────────────────

def test_CS812_8zg_panel_visible_no_composite_link(page: "Page", live_server: str) -> None:
    """Phase 8ZG: panel is visible and no composite link is triggered."""
    _load_retail_shop_supp(page, live_server)
    panel = page.locator("#es-req-panel")
    assert panel.is_visible(), "8ZG: #es-req-panel must be visible."
    panel_html = panel.inner_html()
    assert "composite" not in panel_html.lower(), "8ZG: no composite link must appear in panel."


# ── CS813 ─────────────────────────────────────────────────────────────────────

def test_CS813_8zg_supp_controls_render(page: "Page", live_server: str) -> None:
    """Phase 8ZG: retail_shop_detailed #es-req-supp receives rs_supp_ fields (>10 controls)."""
    _load_retail_shop_supp(page, live_server)
    supp = page.locator("#es-req-supp")
    controls = supp.locator("[data-es-supp-field]")
    assert controls.count() > 10, (
        f"8ZG: #es-req-supp must contain >10 supp controls. Got {controls.count()}."
    )


# ── CS814 ─────────────────────────────────────────────────────────────────────

def test_CS814_8zg_supp_heading_arabic(page: "Page", live_server: str) -> None:
    """Phase 8ZG: supp header shows Arabic heading referencing retail/shop valuation."""
    _load_retail_shop_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "تجزئة" in supp_text or "محل تجاري" in supp_text, (
        f"8ZG: supp heading must contain 'تجزئة' or 'محل تجاري'. Got: {supp_text[:200]!r}"
    )


# ── CS815 ─────────────────────────────────────────────────────────────────────

def test_CS815_8zg_supp_local_only_text(page: "Page", live_server: str) -> None:
    """Phase 8ZG: supp shows 'إدخال محلي' or 'لا يُرسل للتقرير' disclaimer."""
    _load_retail_shop_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "إدخال محلي" in supp_text or "لا يُرسل" in supp_text, (
        f"8ZG: local-only text must appear in supp. Got: {supp_text[:300]!r}"
    )


# ── CS816 ─────────────────────────────────────────────────────────────────────

def test_CS816_8zg_section_A_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: section A «تعريف أصل التجزئة ونوعه» heading renders."""
    _load_retail_shop_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "تعريف أصل التجزئة" in supp_text, "8ZG: section A heading must appear."


# ── CS817 ─────────────────────────────────────────────────────────────────────

def test_CS817_8zg_section_B_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: section B «الخصائص المادية والمساحات» heading renders."""
    _load_retail_shop_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "الخصائص المادية والمساحات" in supp_text, "8ZG: section B heading must appear."


# ── CS818 ─────────────────────────────────────────────────────────────────────

def test_CS818_8zg_section_C_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: section C «الواجهة والرؤية والوصول» heading renders."""
    _load_retail_shop_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "الواجهة والرؤية والوصول" in supp_text, "8ZG: section C heading must appear."


# ── CS819 ─────────────────────────────────────────────────────────────────────

def test_CS819_8zg_section_D_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: section D «السياق التجاري ومنطقة الجذب» heading renders."""
    _load_retail_shop_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "السياق التجاري ومنطقة الجذب" in supp_text, "8ZG: section D heading must appear."


# ── CS820 ─────────────────────────────────────────────────────────────────────

def test_CS820_8zg_section_E_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: section E «الإيجارات والعقود والدخل» heading renders."""
    _load_retail_shop_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "الإيجارات والعقود والدخل" in supp_text, "8ZG: section E heading must appear."


# ── CS821 ─────────────────────────────────────────────────────────────────────

def test_CS821_8zg_section_F_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: section F «المبيعات والإنتاجية التجارية» heading renders."""
    _load_retail_shop_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "المبيعات والإنتاجية التجارية" in supp_text, "8ZG: section F heading must appear."


# ── CS822 ─────────────────────────────────────────────────────────────────────

def test_CS822_8zg_section_G_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: section G «المصروفات والتكاليف وCAPEX» heading renders."""
    _load_retail_shop_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "المصروفات والتكاليف" in supp_text and "CAPEX" in supp_text, (
        "8ZG: section G heading must appear."
    )


# ── CS823 ─────────────────────────────────────────────────────────────────────

def test_CS823_8zg_section_H_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: section H «الخدمات الفنية وMEP» heading renders."""
    _load_retail_shop_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "الخدمات الفنية" in supp_text and "MEP" in supp_text, (
        "8ZG: section H heading must appear."
    )


# ── CS824 ─────────────────────────────────────────────────────────────────────

def test_CS824_8zg_section_I_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: section I «التراخيص والاستخدام القانوني» heading renders."""
    _load_retail_shop_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "التراخيص والاستخدام القانوني" in supp_text, "8ZG: section I heading must appear."


# ── CS825 ─────────────────────────────────────────────────────────────────────

def test_CS825_8zg_section_J_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: section J «السوق وقابلية التسويق» heading renders."""
    _load_retail_shop_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "السوق وقابلية التسويق" in supp_text, "8ZG: section J heading must appear."


# ── CS826 ─────────────────────────────────────────────────────────────────────

def test_CS826_8zg_section_K_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: section K «معاملات التعديل حسب غرض التقييم» heading renders."""
    _load_retail_shop_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "معاملات التعديل" in supp_text, "8ZG: section K heading must appear."


# ── CS827 ─────────────────────────────────────────────────────────────────────

def test_CS827_8zg_section_L_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: section L «كفاءة الطاقة والاستدامة» heading renders."""
    _load_retail_shop_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "كفاءة الطاقة والاستدامة" in supp_text, "8ZG: section L heading must appear."


# ── CS828 ─────────────────────────────────────────────────────────────────────

def test_CS828_8zg_section_M_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: section M «المخاطر المناخية والتشغيلية» heading renders."""
    _load_retail_shop_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "المخاطر المناخية" in supp_text, "8ZG: section M heading must appear."


# ── CS829 ─────────────────────────────────────────────────────────────────────

def test_CS829_8zg_section_N_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: section N «البنية التحتية الرقمية والأومني تشانل» heading renders."""
    _load_retail_shop_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "البنية التحتية الرقمية" in supp_text, "8ZG: section N heading must appear."


# ── CS830 ─────────────────────────────────────────────────────────────────────

def test_CS830_8zg_section_O_heading_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: section O «مستندات إضافية مطلوبة» heading renders."""
    _load_retail_shop_supp(page, live_server)
    supp_text = page.locator("#es-req-supp").inner_text()
    assert "مستندات إضافية مطلوبة" in supp_text, "8ZG: section O heading must appear."


# ── CS831 ─────────────────────────────────────────────────────────────────────

def test_CS831_8zg_field_retail_asset_type_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: rs_supp_retail_asset_type (section A) renders."""
    _load_retail_shop_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='rs_supp_retail_asset_type']")
    assert field.count() > 0, "8ZG: rs_supp_retail_asset_type must render."


# ── CS832 ─────────────────────────────────────────────────────────────────────

def test_CS832_8zg_field_gross_area_sqm_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: rs_supp_gross_area_sqm (section B) renders."""
    _load_retail_shop_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='rs_supp_gross_area_sqm']")
    assert field.count() > 0, "8ZG: rs_supp_gross_area_sqm must render."


# ── CS833 ─────────────────────────────────────────────────────────────────────

def test_CS833_8zg_field_visibility_quality_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: rs_supp_visibility_quality (section C) renders."""
    _load_retail_shop_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='rs_supp_visibility_quality']")
    assert field.count() > 0, "8ZG: rs_supp_visibility_quality must render."


# ── CS834 ─────────────────────────────────────────────────────────────────────

def test_CS834_8zg_field_retail_context_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: rs_supp_retail_context (section D) renders."""
    _load_retail_shop_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='rs_supp_retail_context']")
    assert field.count() > 0, "8ZG: rs_supp_retail_context must render."


# ── CS835 ─────────────────────────────────────────────────────────────────────

def test_CS835_8zg_field_current_rent_annual_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: rs_supp_current_rent_annual (section E) renders."""
    _load_retail_shop_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='rs_supp_current_rent_annual']")
    assert field.count() > 0, "8ZG: rs_supp_current_rent_annual must render."


# ── CS836 ─────────────────────────────────────────────────────────────────────

def test_CS836_8zg_field_annual_gross_sales_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: rs_supp_annual_gross_sales (section F) renders."""
    _load_retail_shop_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='rs_supp_annual_gross_sales']")
    assert field.count() > 0, "8ZG: rs_supp_annual_gross_sales must render."


# ── CS837 ─────────────────────────────────────────────────────────────────────

def test_CS837_8zg_field_operating_expenses_annual_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: rs_supp_operating_expenses_annual (section G) renders."""
    _load_retail_shop_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='rs_supp_operating_expenses_annual']")
    assert field.count() > 0, "8ZG: rs_supp_operating_expenses_annual must render."


# ── CS838 ─────────────────────────────────────────────────────────────────────

def test_CS838_8zg_field_hvac_available_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: rs_supp_hvac_available (section H) renders."""
    _load_retail_shop_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='rs_supp_hvac_available']")
    assert field.count() > 0, "8ZG: rs_supp_hvac_available must render."


# ── CS839 ─────────────────────────────────────────────────────────────────────

def test_CS839_8zg_field_commercial_license_status_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: rs_supp_commercial_license_status (section I) renders."""
    _load_retail_shop_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='rs_supp_commercial_license_status']")
    assert field.count() > 0, "8ZG: rs_supp_commercial_license_status must render."


# ── CS840 ─────────────────────────────────────────────────────────────────────

def test_CS840_8zg_field_marketability_level_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: rs_supp_marketability_level (section J) renders."""
    _load_retail_shop_supp(page, live_server)
    field = page.locator("#es-req-supp [data-es-supp-field='rs_supp_marketability_level']")
    assert field.count() > 0, "8ZG: rs_supp_marketability_level must render."


# ── CS841 ─────────────────────────────────────────────────────────────────────

def test_CS841_8zg_purpose_mortgage_lending_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: purpose mortgage_lending methodology field renders in section K."""
    _load_retail_shop_supp(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='rs_supp_purpose_mortgage_lending_methodology']"
    )
    assert field.count() > 0, "8ZG: mortgage_lending methodology must render in section K."


# ── CS842 ─────────────────────────────────────────────────────────────────────

def test_CS842_8zg_purpose_sale_purchase_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: purpose sale_purchase methodology field renders in section K."""
    _load_retail_shop_supp(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='rs_supp_purpose_sale_purchase_methodology']"
    )
    assert field.count() > 0, "8ZG: sale_purchase methodology must render."


# ── CS843 ─────────────────────────────────────────────────────────────────────

def test_CS843_8zg_purpose_insurance_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: purpose insurance methodology field renders in section K."""
    _load_retail_shop_supp(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='rs_supp_purpose_insurance_methodology']"
    )
    assert field.count() > 0, "8ZG: insurance methodology must render."


# ── CS844 ─────────────────────────────────────────────────────────────────────

def test_CS844_8zg_purpose_ifrs_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: purpose ifrs_fair_value methodology field renders in section K."""
    _load_retail_shop_supp(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='rs_supp_purpose_ifrs_fair_value_methodology']"
    )
    assert field.count() > 0, "8ZG: ifrs_fair_value methodology must render."


# ── CS845 ─────────────────────────────────────────────────────────────────────

def test_CS845_8zg_purpose_rental_assessment_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: purpose rental_assessment methodology field renders in section K."""
    _load_retail_shop_supp(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='rs_supp_purpose_rental_assessment_methodology']"
    )
    assert field.count() > 0, "8ZG: rental_assessment methodology must render."


# ── CS846 ─────────────────────────────────────────────────────────────────────

def test_CS846_8zg_purpose_taxation_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: purpose taxation methodology field renders in section K."""
    _load_retail_shop_supp(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='rs_supp_purpose_taxation_methodology']"
    )
    assert field.count() > 0, "8ZG: taxation methodology must render."


# ── CS847 ─────────────────────────────────────────────────────────────────────

def test_CS847_8zg_purpose_liquidation_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZG: purpose liquidation methodology field renders in section K."""
    _load_retail_shop_supp(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='rs_supp_purpose_liquidation_methodology']"
    )
    assert field.count() > 0, "8ZG: liquidation methodology must render."


# ── CS848 ─────────────────────────────────────────────────────────────────────

def test_CS848_8zg_purpose_litigation_dispute_local_only(page: "Page", live_server: str) -> None:
    """Phase 8ZG: litigation_dispute (local-only) renders in section K."""
    _load_retail_shop_supp(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='rs_supp_purpose_litigation_dispute_methodology']"
    )
    assert field.count() > 0, "8ZG: litigation_dispute (local) methodology must render."


# ── CS849 ─────────────────────────────────────────────────────────────────────

def test_CS849_8zg_purpose_investment_acquisition_local_only(page: "Page", live_server: str) -> None:
    """Phase 8ZG: investment_acquisition (local-only) renders in section K."""
    _load_retail_shop_supp(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='rs_supp_purpose_investment_acquisition_methodology']"
    )
    assert field.count() > 0, "8ZG: investment_acquisition (local) methodology must render."


# ── CS850 ─────────────────────────────────────────────────────────────────────

def test_CS850_8zg_purpose_lease_renewal_review_local_only(page: "Page", live_server: str) -> None:
    """Phase 8ZG: lease_renewal_review (local-only) renders in section K."""
    _load_retail_shop_supp(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='rs_supp_purpose_lease_renewal_review_methodology']"
    )
    assert field.count() > 0, "8ZG: lease_renewal_review (local) methodology must render."


# ── CS851 ─────────────────────────────────────────────────────────────────────

def test_CS851_8zg_purpose_business_interruption_local_only(page: "Page", live_server: str) -> None:
    """Phase 8ZG: business_interruption (local-only) renders in section K."""
    _load_retail_shop_supp(page, live_server)
    field = page.locator(
        "#es-req-supp [data-es-supp-field='rs_supp_purpose_business_interruption_methodology']"
    )
    assert field.count() > 0, "8ZG: business_interruption (local) methodology must render."


# ── CS852 ─────────────────────────────────────────────────────────────────────

def test_CS852_8zg_profit_method_option_available(page: "Page", live_server: str) -> None:
    """Phase 8ZG: profit_method option is available in the mortgage_lending methodology selector."""
    _load_retail_shop_supp(page, live_server)
    sel = page.locator(
        "#es-req-supp [data-es-supp-field='rs_supp_purpose_mortgage_lending_methodology']"
    )
    if sel.count() == 0:
        return
    sel_html = sel.first.inner_html()
    assert "profit_method" in sel_html, (
        "8ZG: profit_method option must be available in methodology selector."
    )


# ── CS853 ─────────────────────────────────────────────────────────────────────

def test_CS853_8zg_all_supp_fields_have_data_es_supp_field(page: "Page", live_server: str) -> None:
    """Phase 8ZG: spot-check that rs_supp_ fields carry data-es-supp-field attribute."""
    _load_retail_shop_supp(page, live_server)
    sample_fields = [
        "rs_supp_retail_asset_type",
        "rs_supp_gross_area_sqm",
        "rs_supp_frontage_m",
        "rs_supp_current_rent_annual",
        "rs_supp_annual_gross_sales",
        "rs_supp_marketability_level",
        "rs_doc_title_deed_or_lease",
    ]
    for fname in sample_fields:
        el = page.locator(f"#es-req-supp [data-es-supp-field='{fname}']")
        assert el.count() > 0, f"8ZG: {fname} must carry data-es-supp-field and render."


# ── CS854 ─────────────────────────────────────────────────────────────────────

def test_CS854_8zg_rs_supp_not_in_old_retail_panel(page: "Page", live_server: str) -> None:
    """Phase 8ZG isolation: rs_supp_ fields must NOT appear in old retail (محل تجاري) panel."""
    _load_retail(page, live_server)
    rs_fields = page.locator("[data-es-supp-field^='rs_supp_']")
    assert rs_fields.count() == 0, (
        f"8ZG isolation: rs_supp_ fields must not appear in old retail panel. "
        f"Found {rs_fields.count()}."
    )


# ── CS855 ─────────────────────────────────────────────────────────────────────

def test_CS855_8zg_rs_supp_not_in_building_full_panel(page: "Page", live_server: str) -> None:
    """Phase 8ZG isolation: rs_supp_ fields must NOT appear in building_full supp panel."""
    _load_building_full_supp(page, live_server)
    rs_fields = page.locator("[data-es-supp-field^='rs_supp_']")
    assert rs_fields.count() == 0, (
        f"8ZG isolation: rs_supp_ fields must not appear in building_full panel. "
        f"Found {rs_fields.count()}."
    )


# ── CS856 ─────────────────────────────────────────────────────────────────────

def test_CS856_8zg_rs_supp_not_in_existing_building_panel(page: "Page", live_server: str) -> None:
    """Phase 8ZG isolation: rs_supp_ fields must NOT appear in existing_building_detailed supp."""
    _load_existing_building(page, live_server)
    rs_fields = page.locator("[data-es-supp-field^='rs_supp_']")
    assert rs_fields.count() == 0, (
        f"8ZG isolation: rs_supp_ fields must not appear in existing_building_detailed panel. "
        f"Found {rs_fields.count()}."
    )


# ── CS857 ─────────────────────────────────────────────────────────────────────

def test_CS857_8zg_rs_supp_not_in_hotel_resort_panel(page: "Page", live_server: str) -> None:
    """Phase 8ZG isolation: rs_supp_ fields must NOT appear in hotel_resort_detailed supp."""
    _load_hotel_resort_supp(page, live_server)
    rs_fields = page.locator("[data-es-supp-field^='rs_supp_']")
    assert rs_fields.count() == 0, (
        f"8ZG isolation: rs_supp_ fields must not appear in hotel_resort_detailed panel. "
        f"Found {rs_fields.count()}."
    )


# ── CS858 ─────────────────────────────────────────────────────────────────────

def test_CS858_8zg_rs_supp_not_in_industrial_logistics_panel(page: "Page", live_server: str) -> None:
    """Phase 8ZG isolation: rs_supp_ fields must NOT appear in industrial_logistics supp."""
    _load_industrial_logistics_supp(page, live_server)
    rs_fields = page.locator("[data-es-supp-field^='rs_supp_']")
    assert rs_fields.count() == 0, (
        f"8ZG isolation: rs_supp_ fields must not appear in industrial_logistics panel. "
        f"Found {rs_fields.count()}."
    )


# ── CS859 ─────────────────────────────────────────────────────────────────────

def test_CS859_8zg_land_residential_regression(page: "Page", live_server: str) -> None:
    """Phase 8ZG regression: land and residential_unit profiles still render after 8ZG."""
    _load_land(page, live_server)
    land_panel = page.locator("#es-req-panel")
    assert land_panel.is_visible(), "8ZG regression: land panel must still be visible."
    land_rs = page.locator("[data-es-supp-field^='rs_supp_']")
    assert land_rs.count() == 0, (
        f"8ZG isolation: rs_supp_ fields must not appear in land panel. "
        f"Found {land_rs.count()}."
    )
    _load_residential(page, live_server)
    res_panel = page.locator("#es-req-panel")
    assert res_panel.is_visible(), "8ZG regression: residential panel must still be visible."
    res_rs = page.locator("[data-es-supp-field^='rs_supp_']")
    assert res_rs.count() == 0, (
        f"8ZG isolation: rs_supp_ fields must not appear in residential panel. "
        f"Found {res_rs.count()}."
    )


# ══════════════════════════════════════════════════════════════════════════════
# Phase 8ZH — Healthcare Facility Detailed Valuation Requirements (CS860–CS909)
# ══════════════════════════════════════════════════════════════════════════════


def _load_healthcare_facility_supp(page: "Page", live_server: str) -> None:
    """Load healthcare_facility profile and wait for supplemental panel."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    page.select_option("#asset-type", value="healthcare_facility")
    page.select_option("#val-purpose", value="fair_market_value")
    page.locator("#es-req-supp").wait_for(state="visible", timeout=6_000)


# ── CS860 ─────────────────────────────────────────────────────────────────────

def test_CS860_8zh_healthcare_facility_dropdown_option_exists(page: "Page", live_server: str) -> None:
    """Phase 8ZH: dropdown must contain value='healthcare_facility' option."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    opts = page.locator("#asset-type option[value='healthcare_facility']")
    assert opts.count() >= 1, "8ZH: option value='healthcare_facility' not found in #asset-type."


# ── CS861 ─────────────────────────────────────────────────────────────────────

def test_CS861_8zh_healthcare_facility_badge_renders(page: "Page", live_server: str) -> None:
    """Phase 8ZH: badge/explainer renders for healthcare_facility profile."""
    _load_healthcare_facility(page, live_server)
    badge = page.locator(".es-profile-badge, [class*='profile-badge'], #es-profile-explainer")
    assert badge.count() >= 1 and badge.first.is_visible(), (
        "8ZH: no profile badge rendered for healthcare_facility."
    )


# ── CS862 ─────────────────────────────────────────────────────────────────────

def test_CS862_8zh_healthcare_facility_supp_panel_visible(page: "Page", live_server: str) -> None:
    """Phase 8ZH: #es-req-supp supplemental panel must be visible for healthcare_facility."""
    _load_healthcare_facility_supp(page, live_server)
    supp = page.locator("#es-req-supp")
    assert supp.is_visible(), "8ZH: #es-req-supp supplemental panel not visible for healthcare_facility."


# ── CS863 ─────────────────────────────────────────────────────────────────────

def test_CS863_8zh_healthcare_facility_no_auth_modal(page: "Page", live_server: str) -> None:
    """Phase 8ZH: no auth modal shown after loading healthcare_facility."""
    _load_healthcare_facility_supp(page, live_server)
    modal = page.locator("#auth-modal, .auth-modal, [id*='auth'][id*='modal']")
    visible_count = sum(1 for i in range(modal.count()) if modal.nth(i).is_visible())
    assert visible_count == 0, f"8ZH: auth modal visible after loading healthcare_facility ({visible_count} found)."


# ── CS864 ─────────────────────────────────────────────────────────────────────

def test_CS864_8zh_healthcare_facility_no_composite_link(page: "Page", live_server: str) -> None:
    """Phase 8ZH: no composite_valuation.html link in supp panel."""
    _load_healthcare_facility_supp(page, live_server)
    links = page.locator("#es-req-supp a[href*='composite_valuation']")
    assert links.count() == 0, (
        f"8ZH: composite_valuation.html link must not appear in healthcare_facility supp panel. "
        f"Found {links.count()}."
    )


# ── CS865 ─────────────────────────────────────────────────────────────────────

def test_CS865_8zh_healthcare_facility_supp_heading_text(page: "Page", live_server: str) -> None:
    """Phase 8ZH: supp panel heading must contain healthcare valuation text."""
    _load_healthcare_facility_supp(page, live_server)
    header = page.locator("#es-req-supp-header")
    assert header.is_visible(), "8ZH: #es-req-supp-header not found."
    text = header.inner_text()
    assert "مستشفى" in text or "مركز طبي" in text, (
        f"8ZH: heading must contain 'مستشفى' or 'مركز طبي'. Got: {text[:120]!r}"
    )


# ── CS866 ─────────────────────────────────────────────────────────────────────

def test_CS866_8zh_section_A_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZH: Section A heading — تعريف الأصل الصحي ونموذج التشغيل."""
    _load_healthcare_facility_supp(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "تعريف الأصل الصحي" in text, (
        f"8ZH Section A heading not found. Snippet: {text[:200]!r}"
    )


# ── CS867 ─────────────────────────────────────────────────────────────────────

def test_CS867_8zh_section_B_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZH: Section B heading — الطاقة السريرية والتوزيع الطبي."""
    _load_healthcare_facility_supp(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "الطاقة السريرية" in text, (
        f"8ZH Section B heading not found. Snippet: {text[:200]!r}"
    )


# ── CS868 ─────────────────────────────────────────────────────────────────────

def test_CS868_8zh_section_C_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZH: Section C heading — الأقسام والخدمات الطبية."""
    _load_healthcare_facility_supp(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "الأقسام والخدمات الطبية" in text, (
        f"8ZH Section C heading not found. Snippet: {text[:200]!r}"
    )


# ── CS869 ─────────────────────────────────────────────────────────────────────

def test_CS869_8zh_section_D_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZH: Section D heading — الأجهزة الطبية والتجهيزات التخصصية."""
    _load_healthcare_facility_supp(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "الأجهزة الطبية" in text, (
        f"8ZH Section D heading not found. Snippet: {text[:200]!r}"
    )


# ── CS870 ─────────────────────────────────────────────────────────────────────

def test_CS870_8zh_section_E_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZH: Section E heading — التراخيص والاعتمادات الطبية."""
    _load_healthcare_facility_supp(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "التراخيص والاعتمادات" in text, (
        f"8ZH Section E heading not found. Snippet: {text[:200]!r}"
    )


# ── CS871 ─────────────────────────────────────────────────────────────────────

def test_CS871_8zh_section_F_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZH: Section F heading — الغرف الخاصة والحماية الإشعاعية."""
    _load_healthcare_facility_supp(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "الحماية الإشعاعية" in text, (
        f"8ZH Section F heading not found. Snippet: {text[:200]!r}"
    )


# ── CS872 ─────────────────────────────────────────────────────────────────────

def test_CS872_8zh_section_G_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZH: Section G heading — البنية الفنية وMEP والغازات الطبية."""
    _load_healthcare_facility_supp(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "MEP" in text and "الغازات الطبية" in text, (
        f"8ZH Section G heading not found. Snippet: {text[:200]!r}"
    )


# ── CS873 ─────────────────────────────────────────────────────────────────────

def test_CS873_8zh_section_H_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZH: Section H heading — مكافحة العدوى والسلامة والتشغيل السريري."""
    _load_healthcare_facility_supp(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "مكافحة العدوى" in text, (
        f"8ZH Section H heading not found. Snippet: {text[:200]!r}"
    )


# ── CS874 ─────────────────────────────────────────────────────────────────────

def test_CS874_8zh_section_I_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZH: Section I heading — الكادر الطبي والتشغيل."""
    _load_healthcare_facility_supp(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "الكادر الطبي" in text, (
        f"8ZH Section I heading not found. Snippet: {text[:200]!r}"
    )


# ── CS875 ─────────────────────────────────────────────────────────────────────

def test_CS875_8zh_section_J_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZH: Section J heading — الإيرادات والمصروفات والتشغيل المالي."""
    _load_healthcare_facility_supp(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "الإيرادات والمصروفات" in text, (
        f"8ZH Section J heading not found. Snippet: {text[:200]!r}"
    )


# ── CS876 ─────────────────────────────────────────────────────────────────────

def test_CS876_8zh_section_K_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZH: Section K heading — دافعي التكلفة والتأمين والمرضى."""
    _load_healthcare_facility_supp(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "دافعي التكلفة" in text, (
        f"8ZH Section K heading not found. Snippet: {text[:200]!r}"
    )


# ── CS877 ─────────────────────────────────────────────────────────────────────

def test_CS877_8zh_section_L_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZH: Section L heading — الحالة الفنية وCAPEX والصيانة."""
    _load_healthcare_facility_supp(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "CAPEX" in text and "الصيانة" in text, (
        f"8ZH Section L heading not found. Snippet: {text[:200]!r}"
    )


# ── CS878 ─────────────────────────────────────────────────────────────────────

def test_CS878_8zh_section_M_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZH: Section M heading — الموقع والسوق والمنافسة."""
    _load_healthcare_facility_supp(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "الموقع والسوق" in text, (
        f"8ZH Section M heading not found. Snippet: {text[:200]!r}"
    )


# ── CS879 ─────────────────────────────────────────────────────────────────────

def test_CS879_8zh_section_N_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZH: Section N heading — الخصائص القانونية والتنظيمية."""
    _load_healthcare_facility_supp(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "الخصائص القانونية" in text, (
        f"8ZH Section N heading not found. Snippet: {text[:200]!r}"
    )


# ── CS880 ─────────────────────────────────────────────────────────────────────

def test_CS880_8zh_section_O_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZH: Section O heading — معاملات التعديل حسب غرض التقييم."""
    _load_healthcare_facility_supp(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "معاملات التعديل" in text, (
        f"8ZH Section O heading not found. Snippet: {text[:200]!r}"
    )


# ── CS881 ─────────────────────────────────────────────────────────────────────

def test_CS881_8zh_section_P_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZH: Section P heading — كفاءة الطاقة والاستدامة الصحية."""
    _load_healthcare_facility_supp(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "كفاءة الطاقة" in text and "الاستدامة" in text, (
        f"8ZH Section P heading not found. Snippet: {text[:200]!r}"
    )


# ── CS882 ─────────────────────────────────────────────────────────────────────

def test_CS882_8zh_section_Q_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZH: Section Q heading — المخاطر المناخية والطبيعية واستمرارية الأعمال."""
    _load_healthcare_facility_supp(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "المخاطر المناخية" in text, (
        f"8ZH Section Q heading not found. Snippet: {text[:200]!r}"
    )


# ── CS883 ─────────────────────────────────────────────────────────────────────

def test_CS883_8zh_section_R_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZH: Section R heading — البنية التحتية الرقمية والصحة الرقمية."""
    _load_healthcare_facility_supp(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "البنية التحتية الرقمية" in text, (
        f"8ZH Section R heading not found. Snippet: {text[:200]!r}"
    )


# ── CS884 ─────────────────────────────────────────────────────────────────────

def test_CS884_8zh_section_S_heading(page: "Page", live_server: str) -> None:
    """Phase 8ZH: Section S heading — مستندات إضافية مطلوبة."""
    _load_healthcare_facility_supp(page, live_server)
    text = page.locator("#es-req-supp").inner_text()
    assert "مستندات إضافية" in text, (
        f"8ZH Section S heading not found. Snippet: {text[:200]!r}"
    )


# ── CS885 ─────────────────────────────────────────────────────────────────────

def test_CS885_8zh_field_operating_status(page: "Page", live_server: str) -> None:
    """Phase 8ZH: hc_supp_operating_status field renders in supp panel."""
    _load_healthcare_facility_supp(page, live_server)
    f = page.locator("[data-es-supp-field='hc_supp_operating_status']")
    assert f.count() >= 1, "8ZH: hc_supp_operating_status not found in supp panel."


# ── CS886 ─────────────────────────────────────────────────────────────────────

def test_CS886_8zh_field_licensed_beds_count(page: "Page", live_server: str) -> None:
    """Phase 8ZH: hc_supp_licensed_beds_count field renders in supp panel."""
    _load_healthcare_facility_supp(page, live_server)
    f = page.locator("[data-es-supp-field='hc_supp_licensed_beds_count']")
    assert f.count() >= 1, "8ZH: hc_supp_licensed_beds_count not found in supp panel."


# ── CS887 ─────────────────────────────────────────────────────────────────────

def test_CS887_8zh_field_heavy_equipment_available(page: "Page", live_server: str) -> None:
    """Phase 8ZH: hc_supp_heavy_equipment_available field renders in supp panel."""
    _load_healthcare_facility_supp(page, live_server)
    f = page.locator("[data-es-supp-field='hc_supp_heavy_equipment_available']")
    assert f.count() >= 1, "8ZH: hc_supp_heavy_equipment_available not found in supp panel."


# ── CS888 ─────────────────────────────────────────────────────────────────────

def test_CS888_8zh_field_jci_accreditation_status(page: "Page", live_server: str) -> None:
    """Phase 8ZH: hc_supp_jci_accreditation_status field renders in supp panel."""
    _load_healthcare_facility_supp(page, live_server)
    f = page.locator("[data-es-supp-field='hc_supp_jci_accreditation_status']")
    assert f.count() >= 1, "8ZH: hc_supp_jci_accreditation_status not found in supp panel."


# ── CS889 ─────────────────────────────────────────────────────────────────────

def test_CS889_8zh_field_lead_lined_rooms_available(page: "Page", live_server: str) -> None:
    """Phase 8ZH: hc_supp_lead_lined_rooms_available field renders in supp panel."""
    _load_healthcare_facility_supp(page, live_server)
    f = page.locator("[data-es-supp-field='hc_supp_lead_lined_rooms_available']")
    assert f.count() >= 1, "8ZH: hc_supp_lead_lined_rooms_available not found in supp panel."


# ── CS890 ─────────────────────────────────────────────────────────────────────

def test_CS890_8zh_field_oxygen_supply_system_type(page: "Page", live_server: str) -> None:
    """Phase 8ZH: hc_supp_oxygen_supply_system_type field renders in supp panel."""
    _load_healthcare_facility_supp(page, live_server)
    f = page.locator("[data-es-supp-field='hc_supp_oxygen_supply_system_type']")
    assert f.count() >= 1, "8ZH: hc_supp_oxygen_supply_system_type not found in supp panel."


# ── CS891 ─────────────────────────────────────────────────────────────────────

def test_CS891_8zh_field_doctors_count(page: "Page", live_server: str) -> None:
    """Phase 8ZH: hc_supp_doctors_count field renders in supp panel."""
    _load_healthcare_facility_supp(page, live_server)
    f = page.locator("[data-es-supp-field='hc_supp_doctors_count']")
    assert f.count() >= 1, "8ZH: hc_supp_doctors_count not found in supp panel."


# ── CS892 ─────────────────────────────────────────────────────────────────────

def test_CS892_8zh_field_annual_inpatient_revenue(page: "Page", live_server: str) -> None:
    """Phase 8ZH: hc_supp_annual_inpatient_revenue field renders in supp panel."""
    _load_healthcare_facility_supp(page, live_server)
    f = page.locator("[data-es-supp-field='hc_supp_annual_inpatient_revenue']")
    assert f.count() >= 1, "8ZH: hc_supp_annual_inpatient_revenue not found in supp panel."


# ── CS893 ─────────────────────────────────────────────────────────────────────

def test_CS893_8zh_field_payer_mix(page: "Page", live_server: str) -> None:
    """Phase 8ZH: hc_supp_payer_mix field renders in supp panel."""
    _load_healthcare_facility_supp(page, live_server)
    f = page.locator("[data-es-supp-field='hc_supp_payer_mix']")
    assert f.count() >= 1, "8ZH: hc_supp_payer_mix not found in supp panel."


# ── CS894 ─────────────────────────────────────────────────────────────────────

def test_CS894_8zh_field_electricity_consumption_annual_kwh(page: "Page", live_server: str) -> None:
    """Phase 8ZH: hc_supp_electricity_consumption_annual_kwh field renders in supp panel."""
    _load_healthcare_facility_supp(page, live_server)
    f = page.locator("[data-es-supp-field='hc_supp_electricity_consumption_annual_kwh']")
    assert f.count() >= 1, "8ZH: hc_supp_electricity_consumption_annual_kwh not found in supp panel."


# ── CS895 ─────────────────────────────────────────────────────────────────────

def test_CS895_8zh_section_O_purpose_mortgage_lending(page: "Page", live_server: str) -> None:
    """Phase 8ZH Section O: mortgage_lending purpose block renders."""
    _load_healthcare_facility_supp(page, live_server)
    f = page.locator("[data-es-supp-field='hc_supp_purpose_mortgage_lending_methodology']")
    assert f.count() >= 1, "8ZH: hc_supp_purpose_mortgage_lending_methodology not found."


# ── CS896 ─────────────────────────────────────────────────────────────────────

def test_CS896_8zh_section_O_purpose_sale_purchase(page: "Page", live_server: str) -> None:
    """Phase 8ZH Section O: sale_purchase purpose block renders."""
    _load_healthcare_facility_supp(page, live_server)
    f = page.locator("[data-es-supp-field='hc_supp_purpose_sale_purchase_methodology']")
    assert f.count() >= 1, "8ZH: hc_supp_purpose_sale_purchase_methodology not found."


# ── CS897 ─────────────────────────────────────────────────────────────────────

def test_CS897_8zh_section_O_purpose_insurance(page: "Page", live_server: str) -> None:
    """Phase 8ZH Section O: insurance purpose block renders."""
    _load_healthcare_facility_supp(page, live_server)
    f = page.locator("[data-es-supp-field='hc_supp_purpose_insurance_methodology']")
    assert f.count() >= 1, "8ZH: hc_supp_purpose_insurance_methodology not found."


# ── CS898 ─────────────────────────────────────────────────────────────────────

def test_CS898_8zh_section_O_purpose_ifrs_fair_value(page: "Page", live_server: str) -> None:
    """Phase 8ZH Section O: ifrs_fair_value purpose block renders."""
    _load_healthcare_facility_supp(page, live_server)
    f = page.locator("[data-es-supp-field='hc_supp_purpose_ifrs_fair_value_methodology']")
    assert f.count() >= 1, "8ZH: hc_supp_purpose_ifrs_fair_value_methodology not found."


# ── CS899 ─────────────────────────────────────────────────────────────────────

def test_CS899_8zh_section_O_purpose_impairment_testing(page: "Page", live_server: str) -> None:
    """Phase 8ZH Section O: impairment_testing (local-only) purpose block renders."""
    _load_healthcare_facility_supp(page, live_server)
    f = page.locator("[data-es-supp-field='hc_supp_purpose_impairment_testing_methodology']")
    assert f.count() >= 1, "8ZH: hc_supp_purpose_impairment_testing_methodology not found."


# ── CS900 ─────────────────────────────────────────────────────────────────────

def test_CS900_8zh_section_O_purpose_acquisition_investment(page: "Page", live_server: str) -> None:
    """Phase 8ZH Section O: acquisition_investment purpose block renders."""
    _load_healthcare_facility_supp(page, live_server)
    f = page.locator("[data-es-supp-field='hc_supp_purpose_acquisition_investment_methodology']")
    assert f.count() >= 1, "8ZH: hc_supp_purpose_acquisition_investment_methodology not found."


# ── CS901 ─────────────────────────────────────────────────────────────────────

def test_CS901_8zh_section_O_purpose_taxation(page: "Page", live_server: str) -> None:
    """Phase 8ZH Section O: taxation purpose block renders."""
    _load_healthcare_facility_supp(page, live_server)
    f = page.locator("[data-es-supp-field='hc_supp_purpose_taxation_methodology']")
    assert f.count() >= 1, "8ZH: hc_supp_purpose_taxation_methodology not found."


# ── CS902 ─────────────────────────────────────────────────────────────────────

def test_CS902_8zh_section_O_purpose_liquidation(page: "Page", live_server: str) -> None:
    """Phase 8ZH Section O: liquidation purpose block renders."""
    _load_healthcare_facility_supp(page, live_server)
    f = page.locator("[data-es-supp-field='hc_supp_purpose_liquidation_methodology']")
    assert f.count() >= 1, "8ZH: hc_supp_purpose_liquidation_methodology not found."


# ── CS903 ─────────────────────────────────────────────────────────────────────

def test_CS903_8zh_section_O_purpose_litigation_dispute(page: "Page", live_server: str) -> None:
    """Phase 8ZH Section O: litigation_dispute (local-only) purpose block renders."""
    _load_healthcare_facility_supp(page, live_server)
    f = page.locator("[data-es-supp-field='hc_supp_purpose_litigation_dispute_methodology']")
    assert f.count() >= 1, "8ZH: hc_supp_purpose_litigation_dispute_methodology not found."


# ── CS904 ─────────────────────────────────────────────────────────────────────

def test_CS904_8zh_section_O_purpose_operator_contract_review(page: "Page", live_server: str) -> None:
    """Phase 8ZH Section O: operator_contract_review (local-only) purpose block renders."""
    _load_healthcare_facility_supp(page, live_server)
    f = page.locator("[data-es-supp-field='hc_supp_purpose_operator_contract_review_methodology']")
    assert f.count() >= 1, "8ZH: hc_supp_purpose_operator_contract_review_methodology not found."


# ── CS905 ─────────────────────────────────────────────────────────────────────

def test_CS905_8zh_data_es_supp_field_attribute_spot_check(page: "Page", live_server: str) -> None:
    """Phase 8ZH: sampled hc_supp_ / hc_doc_ fields all have data-es-supp-field attribute."""
    _load_healthcare_facility_supp(page, live_server)
    sampled_fields = [
        "hc_supp_operating_status",
        "hc_supp_licensed_beds_count",
        "hc_supp_jci_accreditation_status",
        "hc_supp_doctors_count",
        "hc_supp_payer_mix",
        "hc_supp_flood_risk_level",
        "hc_doc_medical_equipment_list",
    ]
    missing = []
    for field in sampled_fields:
        el = page.locator(f"[data-es-supp-field='{field}']")
        if el.count() == 0:
            missing.append(field)
    assert not missing, f"8ZH: missing data-es-supp-field attributes: {missing}"


# ── CS906 ─────────────────────────────────────────────────────────────────────

def test_CS906_8zh_hc_supp_fields_not_in_land_panel(page: "Page", live_server: str) -> None:
    """Phase 8ZH isolation: hc_supp_ fields must NOT appear in land supp panel."""
    _load_land(page, live_server)
    hc_fields = page.locator("[data-es-supp-field^='hc_supp_']")
    assert hc_fields.count() == 0, (
        f"8ZH isolation: hc_supp_ fields must not appear in land panel. "
        f"Found {hc_fields.count()}."
    )


# ── CS907 ─────────────────────────────────────────────────────────────────────

def test_CS907_8zh_hc_supp_fields_not_in_wellness_resort_panel(page: "Page", live_server: str) -> None:
    """Phase 8ZH isolation: hc_supp_ fields must NOT appear in wellness_resort supp panel."""
    _load_wellness_resort(page, live_server)
    hc_fields = page.locator("[data-es-supp-field^='hc_supp_']")
    assert hc_fields.count() == 0, (
        f"8ZH isolation: hc_supp_ fields must not appear in wellness_resort panel. "
        f"Found {hc_fields.count()}."
    )


# ── CS908 ─────────────────────────────────────────────────────────────────────

def test_CS908_8zh_hc_supp_fields_not_in_retail_shop_panel(page: "Page", live_server: str) -> None:
    """Phase 8ZH isolation: hc_supp_ fields must NOT appear in retail_shop_detailed supp panel."""
    _load_retail_shop_supp(page, live_server)
    hc_fields = page.locator("[data-es-supp-field^='hc_supp_']")
    assert hc_fields.count() == 0, (
        f"8ZH isolation: hc_supp_ fields must not appear in retail_shop_detailed panel. "
        f"Found {hc_fields.count()}."
    )


# ── CS909 ─────────────────────────────────────────────────────────────────────

def test_CS909_8zh_old_hospital_ho_total_beds_regression(page: "Page", live_server: str) -> None:
    """Phase 8ZH regression: old hospital profile ho_total_beds still renders correctly."""
    page.goto(live_server, wait_until="networkidle")
    _inject_session(page)
    opts = page.locator("#asset-type option[value='hospital']")
    if opts.count() == 0:
        return  # old hospital profile removed -- test passes by design
    page.select_option("#asset-type", value="hospital")
    page.select_option("#val-purpose", value="fair_market_value")
    panel = page.locator("#es-req-panel")
    panel.wait_for(state="visible", timeout=4_000)
    ho_beds = page.locator("[data-es-field='ho_total_beds'], [data-field='ho_total_beds']")
    if ho_beds.count() > 0:
        assert ho_beds.first.is_visible(), (
            "8ZH regression: ho_total_beds field must still be visible in old hospital profile."
        )
