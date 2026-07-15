"""
professional_valuation_taxonomy_v2.py — Canonical four-axis taxonomy v2 for Professional Valuation.

Four axes:
  Axis 1 – Asset Classification  (asset_family, asset_type, asset_subtype, asset_condition_path)
  Axis 2 – Assignment Purpose    (assignment_purpose, intended_use, intended_user_category, professional_context_path)
  Axis 3 – Basis of Value        (basis_of_value, value_premise, value_output_type)
  Axis 4 – Report Type           (report_type) — handled by professional_valuation_routes.py

Derived – Method Routing         (method_route, enabled_methods, method_steps)

Rules:
  - No external APIs, no OCR, no Qdrant, no RAG.
  - All legacy field values are preserved as raw_legacy_values in the returned context.
  - Unknown values return taxonomy_warnings (soft validation, not rejection).
  - Misplaced values (market_value as asset, comparable_adjustment as purpose) are flagged.
"""
from __future__ import annotations

# ── Axis 1: Asset Classification ──────────────────────────────────────────────

VALID_ASSET_FAMILIES: frozenset[str] = frozenset({
    "residential_housing",
    "land_plots",
    "commercial_retail",
    "office_administrative",
    "industrial_logistics",
    "hospitality_leisure",
    "healthcare_education",
    "special_purpose",
    "agri_environmental",
    "infrastructure",
    "mixed_use",
    # New uncommon/specialized families (Part D + PVACUR additions)
    "heritage_assets",
    "cultural_heritage_assets",
    "special_purpose_assets",
    "infrastructure_assets",
    "healthcare_assets",
    "education_assets",
    "religious_assets",
    "sports_recreation_assets",
    "hospitality_special_assets",
    "energy_utility_assets",
    "transport_assets",
    "marine_assets",
    "agricultural_special_assets",
    "industrial_special_assets",
    "tourism_special_assets",
    "entertainment_assets",
    # Legacy families from existing UI (preserved, not deleted)
    "hospitality_entertainment",
    "sports_event_venues",
    "advanced_industrial_logistics",
    "tech_energy_infrastructure",
    "specialized_medical_science",
    "agri_environmental_assets",
    "underground_special_assets",
    "cemetery_memorial_assets",
    "heritage_cultural_assets",
})

VALID_ASSET_TYPES: frozenset[str] = frozenset({
    # Residential
    "residential_apartment", "residential_villa", "residential_building", "residential_compound",
    # Land
    "urban_land", "agricultural_land", "industrial_land", "coastal_land", "desert_land",
    # Commercial/Retail
    "retail_shop", "shopping_mall", "showroom", "hypermarket",
    # Office/Admin
    "administrative_office", "office_building", "business_park", "serviced_office",
    # Industrial/Logistics
    "industrial_factory", "warehouse", "logistics_facility", "cold_storage", "data_center",
    "prefabricated_factory",
    # Hospitality
    "hotel", "resort", "serviced_apartments", "floating_hotel", "budget_hotel",
    # Healthcare/Education
    "hospital", "clinic", "medical_center", "school", "university", "training_center",
    # Special Purpose
    "religious_facility", "heritage_property", "marina", "airport", "seaport", "cemetery",
    # Agri/Environmental
    "timberland", "agricultural_estate", "fish_farm", "solar_farm",
    # Infrastructure
    "utility_plant", "road_asset", "rail_asset", "bridge",
    # Mixed Use
    "mixed_use_development", "transit_oriented_development",
    # Legacy ordinary valuation asset-type values (Arabic/English, preserved)
    "شقة سكنية", "عمارة سكنية", "أرض فضاء", "أرض زراعية", "تجاري", "مبنى قائم",
    "فندق", "مصنع", "محل تجاري", "retail_shop_detailed", "مستشفى", "مدرسة", "مناجم",
    "water_well", "hotel_resort_detailed", "floating_hotel", "airport", "seaport",
    "marina", "data_center", "cold_storage", "industrial_logistics_facility_detailed",
    "healthcare_facility", "wellness_resort", "educational_asset",
    "heritage_property_detailed", "architectural_cultural_heritage_detailed", "zoo_safari",
    "littoral_rights", "riparian_rights", "waterway_easement",
    "أصول معنوية", "ملكيات جزئية", "استثمارات تحت الإنشاء", "historical", "heritage",
    # Legacy professional subtype values that were used as asset types
    "industrial", "prefabricated_factory", "self_storage", "container_yard",
    "parking_structure", "telecom_tower", "stadium", "indoor_arena",
    "hospital", "school",
})

# Subtypes that are valid given an asset_type (used for warning when duplicated)
_HOTEL_VALID_SUBTYPES: frozenset[str] = frozenset({
    "business_hotel", "boutique_hotel", "resort_hotel", "airport_hotel",
    "extended_stay_hotel", "lifestyle_hotel", "luxury_hotel", "budget_hotel_brand",
    "serviced_apartments_hotel",
})
_FACTORY_VALID_SUBTYPES: frozenset[str] = frozenset({
    "light_factory", "heavy_factory", "processing_plant", "assembly_plant",
    "pharmaceutical_factory", "food_processing", "textile_factory",
    "petrochemical_plant", "prefabricated_structure",
})
_LAND_VALID_SUBTYPES: frozenset[str] = frozenset({
    "raw_land", "serviced_land", "plotted_land", "gazetted_land",
    "development_land", "investment_land", "coastal_plot",
})
_RESIDENTIAL_VALID_SUBTYPES: frozenset[str] = frozenset({
    "studio", "one_bedroom", "two_bedroom", "three_bedroom", "penthouse",
    "duplex", "triplex", "garden_apartment", "rooftop_unit",
    "standalone_villa", "townhouse", "chalet", "palace",
})

# Values from legacy PROF_FAMILY_SUBTYPES that remain valid (preserved, not deleted)
LEGACY_SUBTYPES_PRESERVED: frozenset[str] = frozenset({
    "hotel",  # was subtype under hospitality_entertainment — valid as asset_type, warn if also asset_type=hotel
    "cinema", "theater", "opera_house", "theme_park", "indoor_ski_slope", "casino",
    "stadium", "indoor_arena", "padel_tennis_courts", "squash_courts", "racecourse",
    "motorsport_circuit", "golf_course",
    "industrial", "prefabricated_factory", "self_storage", "container_yard", "parking_structure",
    "telecom_tower", "solar_farm",
    "hospital", "school", "life_sciences_lab", "bio_bank",
    "agtech_hydroponic", "greenhouse", "smart_farm",
    "repurposed_cave", "underground_bunker",
    "cemetery", "memorial_park",
    "heritage_property", "architectural_heritage", "cultural_landmark", "adaptive_reuse_heritage",
})

VALID_ASSET_CONDITION_PATHS: frozenset[str] = frozenset({
    "operating_existing",
    "vacant_existing",
    "under_construction",
    "development_ready",
    "brownfield_redevelopment",
    "heritage_listed",
    "partially_let",
    "owner_occupied",
    "investment_let",
    "shell_and_core",
    # Specific hotel condition paths
    "operating_existing_hotel",
    "vacant_hotel",
    "hotel_under_renovation",
    # Specific land condition paths
    "raw_undeveloped_land",
    "serviced_land",
    "land_under_development",
})

# ── Axis 2: Assignment Purpose / Intended Use ─────────────────────────────────

VALID_ASSIGNMENT_PURPOSES: frozenset[str] = frozenset({
    "financing_mortgage",
    "sale_purchase",
    "court_dispute",
    "investment_decision",
    "internal_advisory",
    "tax_government",
    "insurance",
    "financial_reporting",
    "environmental_risk_review",
    "liquidation_restructuring",
    "inheritance_partition",
    "regulatory_compliance",
    "portfolio_management",
    "asset_disposal",
    "development_feasibility",
    # Aliases from ordinary valuation (preserved)
    "market_value",   # was misplaced as purpose — flagged with warning
    "rental_value",   # was misplaced as purpose — flagged with warning
    # Legacy purpose values from ordinary valuation (preserved)
    "fair_market_value",
    "acquisition",
    "bank_financing",
    "judicial_liquidation",
    "investment_analysis",
    "rental_arbitration",
    "tax_assessment",
    "usufruct",
    "uncertainty_valuation",
    "highest_and_best_use",   # method, not purpose — flagged with warning
    "investment_funds",
    "environmental_impact_assessment",
})

VALID_INTENDED_USER_CATEGORIES: frozenset[str] = frozenset({
    "bank_financial_institution",
    "court_judicial_authority",
    "government_regulator",
    "private_investor",
    "corporate_board",
    "insurance_company",
    "real_estate_fund",
    "internal_management",
    "tax_authority",
    "auditor_accountant",
    "general_public",
})

VALID_PROFESSIONAL_CONTEXT_PATHS: frozenset[str] = frozenset({
    "basel_iii_iv_collateral",
    "ifrs_13_fair_value_hierarchy",
    "rics_red_book",
    "ivsc_ips",
    "court_appointed_expert",
    "government_mass_appraisal",
    "investment_fund_nav",
    "insurance_reinstatement",
    "internal_advisory_only",
    "environmental_due_diligence",
})

# ── Axis 3: Basis of Value ────────────────────────────────────────────────────

VALID_BASIS_OF_VALUE: frozenset[str] = frozenset({
    "market_value",         # القيمة السوقية
    "market_rent",          # القيمة الإيجارية السوقية
    "investment_value",     # القيمة الاستثمارية
    "fair_value",           # القيمة العادلة (IFRS 13)
    "liquidation_value",    # قيمة التصفية
    "insurable_value",      # قيمة التأمين / إعادة الإنشاء
    "going_concern_value",  # قيمة الاستمرارية
    "special_purpose_value", # قيمة الأغراض الخاصة
    # Legacy values from ordinary valuation (preserved, mapped)
    "fair_market_value",    # alias → market_value
    "rental_value",         # alias → market_rent
    "reinstatement_value",  # alias → insurable_value
    "standard_market_value", # alias → market_value (was in prof-purpose-route)
})

VALID_VALUE_PREMISES: frozenset[str] = frozenset({
    "as_is",
    "as_stabilized",
    "as_complete",
    "highest_and_best_use",
    "current_use",
    "alternative_use",
    "forced_sale",
    "going_concern",
})

VALID_VALUE_OUTPUT_TYPES: frozenset[str] = frozenset({
    "point_estimate",
    "range_estimate",
    "weighted_value",
    "probability_weighted",
    "scenario_based",
})

# ── Extended VALID sets for new canonical options (preserved, not deleted) ────
VALID_INTENDED_USER_CATEGORIES = VALID_INTENDED_USER_CATEGORIES | frozenset({
    "bank", "court", "investor", "owner", "company",
    "government_entity", "regulator", "real_estate_tax_authority",
    "insurance_company", "auditor", "internal_management",
})

VALID_PROFESSIONAL_CONTEXT_PATHS = VALID_PROFESSIONAL_CONTEXT_PATHS | frozenset({
    "bank_financing_path", "court_expert_path", "investor_decision_path",
    "internal_management_path", "government_tax_path", "tax_authority_path",
    "insurance_path", "financial_reporting_path", "ifrs_financial_reporting_path",
    "regulatory_path", "ma_transaction_path", "environmental_review_path",
})

VALID_ASSIGNMENT_PURPOSES = VALID_ASSIGNMENT_PURPOSES | frozenset({
    "partial_interest_valuation", "merger_acquisition", "tax_appeal",
    "regulatory_government",
})

VALID_BASIS_OF_VALUE = VALID_BASIS_OF_VALUE | frozenset({
    "value_in_use", "special_value", "synergistic_value",
})

VALID_VALUE_PREMISES = VALID_VALUE_PREMISES | frozenset({
    "as_repaired", "as_completed", "as_stabilized", "liquidation_premise",
    "continued_use", "forced_sale",
})

# ── Section 3 Registries — Purpose, Intended User, Pathway, Basis, Premise ──

_VALUATION_PURPOSE_REGISTRY: list[dict] = [
    {"key":"sale_purchase","label_ar":"بيع / شراء","label_en":"Sale / Purchase","category":"transaction","recommended_methods":["sales_comparison","income_approach"],"required_disclosures":["market_comparables_required"],"warnings":[],"legacy_aliases":[],"active":True,"requires_expert_review":False},
    {"key":"financing_mortgage","label_ar":"تمويل / رهن","label_en":"Financing / Mortgage","category":"lending","recommended_methods":["sales_comparison","income_approach","cost_approach"],"required_disclosures":["lender_requirements","certification_may_be_required"],"warnings":["lender_specific_requirements_may_apply"],"legacy_aliases":["bank_financing"],"active":True,"requires_expert_review":False},
    {"key":"court_dispute","label_ar":"نزاع قضائي / محكمة","label_en":"Court Dispute","category":"legal","recommended_methods":["sales_comparison","cost_approach","income_approach"],"required_disclosures":["scope_of_work_disclosure","litigation_use_disclosure"],"warnings":["explicit_scope_limitations_required"],"legacy_aliases":[],"active":True,"requires_expert_review":True},
    {"key":"tax_appeal","label_ar":"طعن ضريبي","label_en":"Tax Appeal","category":"tax","recommended_methods":["statutory_basis","sales_comparison","income_approach"],"required_disclosures":["local_tax_rules_apply","statutory_basis_required"],"warnings":["local_tax_calculation_rules_apply"],"legacy_aliases":["tax_assessment","tax_government"],"active":True,"requires_expert_review":False},
    {"key":"investment_decision","label_ar":"قرار استثماري","label_en":"Investment Decision","category":"investment","recommended_methods":["dcf","sales_comparison","income_approach"],"required_disclosures":["growth_assumptions_documented"],"warnings":[],"legacy_aliases":["investment_analysis","acquisition"],"active":True,"requires_expert_review":False},
    {"key":"internal_advisory","label_ar":"استخدام داخلي استرشادي","label_en":"Internal Advisory","category":"advisory","recommended_methods":["sales_comparison","income_approach"],"required_disclosures":["advisory_only_not_for_official_use"],"warnings":[],"legacy_aliases":["internal_advisory_only"],"active":True,"requires_expert_review":False},
    {"key":"insurance","label_ar":"تأمين","label_en":"Insurance","category":"insurance","recommended_methods":["cost_approach","insurable_value_calc"],"required_disclosures":["reinstatement_cost_basis","policy_terms_apply"],"warnings":[],"legacy_aliases":["insurance_reinstatement"],"active":True,"requires_expert_review":False},
    {"key":"financial_reporting","label_ar":"تقارير مالية","label_en":"Financial Reporting","category":"financial","recommended_methods":["ifrs_fair_value","dcf","sales_comparison"],"required_disclosures":["ifrs_13_fair_value_hierarchy","accountant_review_required"],"warnings":["ifrs_hierarchy_level_required"],"legacy_aliases":[],"active":True,"requires_expert_review":True},
    {"key":"regulatory_government","label_ar":"تنظيمي / حكومي","label_en":"Regulatory / Government","category":"regulatory","recommended_methods":["sales_comparison","cost_approach"],"required_disclosures":["regulatory_requirements_apply"],"warnings":[],"legacy_aliases":["regulatory_compliance","tax_government"],"active":True,"requires_expert_review":False},
    {"key":"merger_acquisition","label_ar":"اندماج واستحواذ","label_en":"Merger & Acquisition","category":"transaction","recommended_methods":["dcf","sales_comparison","synergistic_value_calc"],"required_disclosures":["synergies_documented"],"warnings":[],"legacy_aliases":[],"active":True,"requires_expert_review":True},
    {"key":"liquidation_restructuring","label_ar":"تصفية وإعادة هيكلة","label_en":"Liquidation / Restructuring","category":"legal","recommended_methods":["forced_sale_approach","cost_approach","income_approach"],"required_disclosures":["liquidation_does_not_reflect_normal_market"],"warnings":["liquidation_not_normal_market"],"legacy_aliases":["judicial_liquidation"],"active":True,"requires_expert_review":True},
    {"key":"partial_interest_valuation","label_ar":"تقييم مصالح جزئية","label_en":"Partial Interest Valuation","category":"special","recommended_methods":["full_ownership_value_first","dloc_dlom_discounts"],"required_disclosures":["full_ownership_required_first","dloc_dlom_justification_required"],"warnings":["expert_justification_required_for_discounts"],"legacy_aliases":[],"active":True,"requires_expert_review":True},
    {"key":"inheritance_partition","label_ar":"تقسيم الميراث","label_en":"Inheritance Partition","category":"legal","recommended_methods":["sales_comparison","cost_approach"],"required_disclosures":[],"warnings":[],"legacy_aliases":[],"active":True,"requires_expert_review":False},
    {"key":"development_feasibility","label_ar":"جدوى التطوير","label_en":"Development Feasibility","category":"investment","recommended_methods":["residual_land_value","dcf","cost_approach"],"required_disclosures":[],"warnings":[],"legacy_aliases":[],"active":True,"requires_expert_review":False},
    {"key":"portfolio_management","label_ar":"إدارة المحفظة","label_en":"Portfolio Management","category":"investment","recommended_methods":["sales_comparison","income_approach","dcf"],"required_disclosures":[],"warnings":[],"legacy_aliases":[],"active":True,"requires_expert_review":False},
    {"key":"environmental_risk_review","label_ar":"مراجعة مخاطر بيئية","label_en":"Environmental Risk Review","category":"special","recommended_methods":["remediation_cost","market_impact_assessment"],"required_disclosures":["environmental_liability_disclosure"],"warnings":[],"legacy_aliases":[],"active":True,"requires_expert_review":False},
]

_PURPOSE_LOGIC_PATH_REGISTRY: list[dict] = [
    {"key":"sales_comparison_market_value","label_ar":"مقارنة المبيعات — قيمة سوقية","applicable_purposes":["sale_purchase","financing_mortgage"],"active":True},
    {"key":"income_dcf_investment_value","label_ar":"دخل DCF — قيمة استثمارية","applicable_purposes":["investment_decision","financial_reporting"],"active":True},
    {"key":"cost_approach_insurable","label_ar":"تكلفة — قيمة تأمين","applicable_purposes":["insurance"],"active":True},
    {"key":"land_residual_development","label_ar":"أرض متبقية — تطوير","applicable_purposes":["development_feasibility"],"active":True},
    {"key":"forced_sale_liquidation","label_ar":"بيع اضطراري / تصفية","applicable_purposes":["liquidation_restructuring"],"active":True},
    {"key":"ifrs_fair_value_hierarchy","label_ar":"IFRS — تسلسل القيمة العادلة","applicable_purposes":["financial_reporting"],"active":True},
    {"key":"mass_appraisal_tax_route","label_ar":"تقييم جماعي — ضريبي","applicable_purposes":["tax_appeal","regulatory_government"],"active":True},
    {"key":"rental_arbitration_route","label_ar":"مسار تحكيم إيجاري","applicable_purposes":["court_dispute","tax_appeal"],"active":True},
    {"key":"acquisition_synergy_value","label_ar":"قيمة التآزر الاستثماري","applicable_purposes":["merger_acquisition","investment_decision"],"active":True},
    {"key":"standard_market_value","label_ar":"القيمة السوقية القياسية","applicable_purposes":["sale_purchase","financing_mortgage"],"active":True},
]

_INTENDED_USER_REGISTRY: list[dict] = [
    {"key":"bank_financial_institution","label_ar":"بنك / مؤسسة مالية","label_en":"Bank / Financial Institution","legacy_aliases":["bank"],"active":True},
    {"key":"court_judicial_authority","label_ar":"محكمة / جهة قضائية","label_en":"Court / Judicial Authority","legacy_aliases":["court"],"active":True},
    {"key":"government_regulator","label_ar":"جهة حكومية / رقابية","label_en":"Government / Regulator","legacy_aliases":["government_entity","regulator"],"active":True},
    {"key":"private_investor","label_ar":"مستثمر خاص","label_en":"Private Investor","legacy_aliases":["investor"],"active":True},
    {"key":"corporate_board","label_ar":"مجلس إدارة / شركة","label_en":"Corporate Board / Company","legacy_aliases":["company"],"active":True},
    {"key":"insurance_company","label_ar":"شركة تأمين","label_en":"Insurance Company","legacy_aliases":[],"active":True},
    {"key":"real_estate_fund","label_ar":"صندوق استثمار عقاري","label_en":"Real Estate Fund","legacy_aliases":[],"active":True},
    {"key":"internal_management","label_ar":"إدارة داخلية","label_en":"Internal Management","legacy_aliases":[],"active":True},
    {"key":"tax_authority","label_ar":"هيئة الضرائب","label_en":"Tax Authority","legacy_aliases":["real_estate_tax_authority"],"active":True},
    {"key":"auditor_accountant","label_ar":"مراجع حسابات / محاسب","label_en":"Auditor / Accountant","legacy_aliases":["auditor"],"active":True},
    {"key":"general_public","label_ar":"عام","label_en":"General Public","legacy_aliases":[],"active":True},
    {"key":"owner","label_ar":"مالك","label_en":"Owner","legacy_aliases":[],"active":True},
]

_PROFESSIONAL_PATHWAY_REGISTRY: list[dict] = [
    {"key":"bank_financing_path","label_ar":"مسار البنوك والتمويل","label_en":"Bank Financing Path","applicable_purposes":["financing_mortgage"],"applicable_user_categories":["bank_financial_institution"],"active":True},
    {"key":"court_expert_path","label_ar":"مسار المحاكم والخبراء","label_en":"Court Expert Path","applicable_purposes":["court_dispute"],"applicable_user_categories":["court_judicial_authority"],"active":True},
    {"key":"tax_authority_path","label_ar":"مسار الجهات الضريبية","label_en":"Tax Authority Path","applicable_purposes":["tax_appeal","regulatory_government"],"applicable_user_categories":["tax_authority"],"legacy_aliases":["government_tax_path"],"active":True},
    {"key":"investor_decision_path","label_ar":"مسار المستثمرين","label_en":"Investor Decision Path","applicable_purposes":["investment_decision","development_feasibility"],"applicable_user_categories":["private_investor","real_estate_fund"],"active":True},
    {"key":"ifrs_financial_reporting_path","label_ar":"مسار التقارير المالية IFRS","label_en":"IFRS Financial Reporting Path","applicable_purposes":["financial_reporting"],"applicable_user_categories":["auditor_accountant","corporate_board"],"legacy_aliases":["financial_reporting_path"],"active":True},
    {"key":"insurance_path","label_ar":"مسار التأمين","label_en":"Insurance Path","applicable_purposes":["insurance"],"applicable_user_categories":["insurance_company"],"active":True},
    {"key":"regulatory_path","label_ar":"مسار الجهات التنظيمية","label_en":"Regulatory Path","applicable_purposes":["regulatory_government"],"applicable_user_categories":["government_regulator"],"active":True},
    {"key":"ma_transaction_path","label_ar":"مسار الاندماج والاستحواذ","label_en":"M&A Transaction Path","applicable_purposes":["merger_acquisition"],"applicable_user_categories":["corporate_board","private_investor"],"active":True},
    {"key":"internal_management_path","label_ar":"مسار الإدارة الداخلية","label_en":"Internal Management Path","applicable_purposes":["internal_advisory","portfolio_management"],"applicable_user_categories":["internal_management"],"active":True},
    {"key":"government_tax_path","label_ar":"مسار الجهات الحكومية / الضريبية","label_en":"Government / Tax Path","applicable_purposes":["tax_appeal","regulatory_government","tax_government"],"applicable_user_categories":["government_regulator","tax_authority"],"legacy_aliases":[],"active":True},
    {"key":"financial_reporting_path","label_ar":"مسار التقارير المالية","label_en":"Financial Reporting Path","applicable_purposes":["financial_reporting"],"applicable_user_categories":["auditor_accountant"],"legacy_aliases":[],"active":True},
    {"key":"environmental_review_path","label_ar":"مسار المراجعة البيئية","label_en":"Environmental Review Path","applicable_purposes":["environmental_risk_review"],"applicable_user_categories":[],"legacy_aliases":[],"active":True},
]

_BASIS_OF_VALUE_REGISTRY: list[dict] = [
    {"key":"market_value","label_ar":"القيمة السوقية","label_en":"Market Value","standard_ref":"IVS 104","legacy_aliases":["fair_market_value","standard_market_value"],"active":True},
    {"key":"market_rent","label_ar":"القيمة الإيجارية السوقية","label_en":"Market Rent","standard_ref":"IVS 104","legacy_aliases":["rental_value","rental_arbitration"],"active":True},
    {"key":"investment_value","label_ar":"القيمة الاستثمارية","label_en":"Investment Value","standard_ref":"IVS 104","legacy_aliases":[],"active":True},
    {"key":"fair_value","label_ar":"القيمة العادلة","label_en":"Fair Value (IFRS 13)","standard_ref":"IFRS 13","legacy_aliases":[],"active":True},
    {"key":"liquidation_value","label_ar":"قيمة التصفية","label_en":"Liquidation Value","standard_ref":"IVS 104","legacy_aliases":[],"active":True,"warnings":["liquidation_does_not_reflect_normal_market"]},
    {"key":"insurable_value","label_ar":"قيمة التأمين / إعادة الإنشاء","label_en":"Insurable Value","standard_ref":"Insurance Standards","legacy_aliases":["reinstatement_value"],"active":True},
    {"key":"going_concern_value","label_ar":"قيمة الاستمرارية","label_en":"Going Concern Value","standard_ref":"IVS 200","legacy_aliases":[],"active":True},
    {"key":"special_purpose_value","label_ar":"قيمة الأغراض الخاصة","label_en":"Special Purpose Value","standard_ref":"IVS 104","legacy_aliases":[],"active":True},
    {"key":"value_in_use","label_ar":"قيمة الاستخدام","label_en":"Value in Use","standard_ref":"IAS 36","legacy_aliases":[],"active":True},
    {"key":"special_value","label_ar":"القيمة الخاصة","label_en":"Special Value","standard_ref":"IVS 104","legacy_aliases":[],"active":True},
    {"key":"synergistic_value","label_ar":"القيمة التآزرية","label_en":"Synergistic Value","standard_ref":"IVS 104","legacy_aliases":[],"active":True},
]

_VALUE_PREMISE_REGISTRY: list[dict] = [
    {"key":"as_is","label_ar":"الحالة الراهنة As Is","label_en":"As Is","active":True,"legacy_aliases":[]},
    {"key":"as_repaired","label_ar":"بعد الإصلاح As Repaired","label_en":"As Repaired","active":True,"legacy_aliases":[]},
    {"key":"as_completed","label_ar":"عند الاكتمال As Completed","label_en":"As Completed","active":True,"legacy_aliases":["as_complete"],"warnings":["financing_mortgage_may_require_guarantees"]},
    {"key":"as_stabilized","label_ar":"بعد الاستقرار التشغيلي As Stabilized","label_en":"As Stabilized","active":True,"legacy_aliases":[]},
    {"key":"going_concern","label_ar":"استمرارية التشغيل Going Concern","label_en":"Going Concern","active":True,"legacy_aliases":[]},
    {"key":"liquidation_premise","label_ar":"فرضية التصفية Liquidation Premise","label_en":"Liquidation Premise","active":True,"legacy_aliases":[]},
    {"key":"forced_sale","label_ar":"بيع جبري Forced Sale","label_en":"Forced Sale","active":True,"legacy_aliases":[]},
    {"key":"continued_use","label_ar":"استمرار الاستخدام Continued Use","label_en":"Continued Use","active":True,"legacy_aliases":[]},
    {"key":"highest_and_best_use","label_ar":"أعلى وأفضل استخدام HBU","label_en":"Highest and Best Use (HBU)","active":True,"legacy_aliases":[]},
    {"key":"current_use","label_ar":"الاستخدام الحالي","label_en":"Current Use","active":True,"legacy_aliases":[]},
    {"key":"alternative_use","label_ar":"استخدام بديل","label_en":"Alternative Use","active":True,"legacy_aliases":[]},
]

_PURPOSE_DISCLOSURE_WARNING_REGISTRY: list[dict] = [
    {"key":"financing_mortgage+as_completed","label_ar":"تمويل وفرضية عند الاكتمال","warning":"قد لا تقبل بعض جهات التمويل التقييم على أساس عند الاكتمال دون ضمانات أو مستندات داعمة.","type":"warning","applies_when":{"purpose":"financing_mortgage","premise":["as_completed","as_complete"]}},
    {"key":"investment_value+financing_mortgage","label_ar":"قيمة استثمارية لغرض رهن","warning":"القيمة الاستثمارية قد لا تكون مناسبة لبعض أغراض الرهن البنكي؛ راجع الجهة الممولة.","type":"incompatibility","applies_when":{"purpose":"financing_mortgage","basis_of_value":"investment_value"}},
    {"key":"liquidation_value_disclosure","label_ar":"إفصاح قيمة التصفية","warning":"قيمة التصفية لا تعكس بالضرورة ظروف السوق الطبيعي.","type":"disclosure","applies_when":{"basis_of_value":"liquidation_value"}},
    {"key":"partial_interest_disclosure","label_ar":"تقييم المصالح الجزئية","warning":"يتطلب تقييم المصالح الجزئية تقدير قيمة الملكية الكاملة أولاً ثم تطبيق خصومات نقص السيطرة ونقص التسويق عند الاقتضاء وبمبررات موثقة.","type":"disclosure","applies_when":{"purpose":"partial_interest_valuation"}},
    {"key":"court_dispute_disclosure","label_ar":"استخدام قضائي","warning":"الاستخدام القضائي يتطلب وضوح نطاق العمل والافتراضات والقيود والمستندات المؤيدة.","type":"warning","applies_when":{"intended_user_category":"court_judicial_authority"}},
    {"key":"fair_value+ifrs_disclosure","label_ar":"قيمة عادلة IFRS","warning":"قياسات القيمة العادلة لأغراض التقارير المالية قد تتطلب مراجعة معايير IFRS ومستوى المدخلات.","type":"disclosure","applies_when":{"basis_of_value":"fair_value","professional_context_path":"ifrs_financial_reporting_path"}},
    {"key":"tax_appeal_disclosure","label_ar":"طعن ضريبي","warning":"الطعن الضريبي يتطلب الالتزام بالقواعد الضريبية المحلية وأساس التقييم المعمول به.","type":"warning","applies_when":{"purpose":"tax_appeal"}},
]

_PURPOSE_ROUTING_MATRIX_REGISTRY: list[dict] = [
    {
        "key": "sale_purchase+market_value+as_is",
        "label_ar": "بيع/شراء — قيمة سوقية — الحالة الراهنة",
        "assignment_purpose": "sale_purchase", "basis_of_value": "market_value", "value_premise": "as_is",
        "recommended_methods": ["sales_comparison","income_approach","cost_approach"],
        "required_disclosures": ["verify_market_comparables"],
        "warnings": [], "review_required": False,
    },
    {
        "key": "financing_mortgage+market_value+as_is",
        "label_ar": "تمويل/رهن — قيمة سوقية — الحالة الراهنة",
        "assignment_purpose": "financing_mortgage", "basis_of_value": "market_value", "value_premise": "as_is",
        "recommended_methods": ["sales_comparison","income_approach","cost_approach"],
        "required_disclosures": ["lender_requirements","certification_may_be_required"],
        "warnings": ["lender_specific_requirements_may_apply"], "review_required": False,
    },
    {
        "key": "financing_mortgage+market_value+as_completed",
        "label_ar": "تمويل/رهن — قيمة سوقية — عند الاكتمال",
        "assignment_purpose": "financing_mortgage", "basis_of_value": "market_value", "value_premise": "as_completed",
        "recommended_methods": ["sales_comparison","dcf","cost_approach"],
        "required_disclosures": ["construction_docs_required","guarantees_disclosure"],
        "warnings": ["lender_may_require_guarantees"], "review_required": True,
    },
    {
        "key": "court_dispute+market_value",
        "label_ar": "نزاع قضائي — قيمة سوقية",
        "assignment_purpose": "court_dispute", "basis_of_value": "market_value", "value_premise": None,
        "recommended_methods": ["sales_comparison","cost_approach","income_approach"],
        "required_disclosures": ["litigation_use_disclosure","scope_limitations_explicit"],
        "warnings": ["scope_limitations_must_be_explicit"], "review_required": True,
    },
    {
        "key": "tax_appeal+market_value",
        "label_ar": "طعن ضريبي — قيمة سوقية",
        "assignment_purpose": "tax_appeal", "basis_of_value": "market_value", "value_premise": None,
        "recommended_methods": ["statutory_basis","sales_comparison","income_approach"],
        "required_disclosures": ["local_tax_rules","statutory_basis_required"],
        "warnings": ["tax_specific_calculation_rules"], "review_required": False,
    },
    {
        "key": "financial_reporting+fair_value",
        "label_ar": "تقارير مالية — قيمة عادلة",
        "assignment_purpose": "financial_reporting", "basis_of_value": "fair_value", "value_premise": None,
        "recommended_methods": ["ifrs_fair_value_level1","ifrs_fair_value_level2","ifrs_fair_value_level3","dcf"],
        "required_disclosures": ["ifrs_13_context_advisory","expert_review_required"],
        "warnings": ["ifrs_hierarchy_level_required"], "review_required": True,
    },
    {
        "key": "partial_interest_valuation+market_value",
        "label_ar": "مصالح جزئية — قيمة سوقية",
        "assignment_purpose": "partial_interest_valuation", "basis_of_value": "market_value", "value_premise": None,
        "recommended_methods": ["full_ownership_value_first","dloc_if_applicable","dlom_if_applicable"],
        "required_disclosures": ["full_ownership_required","dloc_dlom_expert_justification","disclosure_required"],
        "warnings": ["expert_justification_required"], "review_required": True,
    },
]

def get_purpose_registries() -> dict:
    """Return all Section 3 registries for API responses."""
    return {
        "valuation_purpose_registry":           _VALUATION_PURPOSE_REGISTRY,
        "purpose_logic_path_registry":          _PURPOSE_LOGIC_PATH_REGISTRY,
        "intended_user_registry":               _INTENDED_USER_REGISTRY,
        "professional_pathway_registry":        _PROFESSIONAL_PATHWAY_REGISTRY,
        "basis_of_value_registry":              _BASIS_OF_VALUE_REGISTRY,
        "value_premise_registry":               _VALUE_PREMISE_REGISTRY,
        "purpose_disclosure_warning_registry":  _PURPOSE_DISCLOSURE_WARNING_REGISTRY,
        "purpose_routing_matrix_registry":      _PURPOSE_ROUTING_MATRIX_REGISTRY,
    }

# ── Derived Axis: Method Routing ──────────────────────────────────────────────

# These are METHOD STEPS — they must not appear as assignment purposes or purpose subroutes
METHOD_STEPS: frozenset[str] = frozenset({
    "sales_comparison",
    "comparable_adjustment",
    "rental_comparison",
    "cost_approach",
    "depreciation_model",
    "direct_capitalization",
    "dcf",
    "land_comparison",
    "residual_land_value",
    "hbu",
    "legal_review",
    "esg",
    "swot",
    "peer_review",
    "signature_gate",
    "income_approach",
    "occupancy_revenue_analysis",
    "infrastructure_constraints",
    "environmental_risk",
    "mass_appraisal_reference",
    "sensitivity_analysis",
    "scenario_analysis",
    "probability_weighted_value",
    "stress_testing",
})

# Old purpose-route / subroute values that are actually method steps (misplaced)
_MISPLACED_AS_PURPOSE: dict[str, str] = {
    "sales_comparison_market_value": "comparable_adjustment / sales_comparison",
    "dcf_investment_value":          "dcf",
    "comparable_adjustment":         "comparable_adjustment",
    "habu_required":                 "hbu",
    "sensitivity_analysis":          "sensitivity_analysis",
    "scenario_analysis":             "scenario_analysis",
    "probability_weighted_value":    "probability_weighted_value",
    "stress_case":                   "stress_testing",
    "highest_and_best_use":          "hbu",
}

# Old purpose-route values that are actually basis of value (misplaced)
_MISPLACED_AS_ASSET_OR_BASIS: dict[str, str] = {
    "standard_market_value":   "market_value",
    "market_value_with_habu":  "market_value",
    "fair_market_value":       "market_value",
    "rental_arbitration":      "market_rent",
    "rental_value":            "market_rent",
    "market_value":            "market_value",
}

# ── Method Routing Matrix ─────────────────────────────────────────────────────
# Inputs: (asset_type_canonical, assignment_purpose_canonical, basis_of_value_canonical)
# Output: list of enabled_methods

_ROUTING_MATRIX: list[dict] = [
    # Hotel + market_value (any assignment purpose)
    {
        "asset_types":         {"hotel", "فندق", "hotel_resort_detailed", "floating_hotel"},
        "basis_of_value":      {"market_value", "fair_market_value", "standard_market_value"},
        "assignment_purposes": None,  # any
        "enabled_methods": [
            "sales_comparison", "comparable_adjustment", "income_approach",
            "direct_capitalization", "dcf", "hbu", "legal_review", "esg", "swot",
        ],
        "workbook_sheets": ["مقارنة البيوع", "طريقة الدخل", "التدفقات النقدية DCF",
                            "HBU", "الفحص القانوني", "ESG", "SWOT"],
        "pdf_sections":   ["market_value_summary", "hbu_section", "governance"],
    },
    # Hotel + market_rent
    {
        "asset_types":         {"hotel", "فندق", "hotel_resort_detailed", "serviced_apartments"},
        "basis_of_value":      {"market_rent", "rental_value", "rental_arbitration"},
        "assignment_purposes": None,
        "enabled_methods": [
            "rental_comparison", "income_approach",
            "occupancy_revenue_analysis", "direct_capitalization",
        ],
        "workbook_sheets": ["القيمة الإيجارية", "مقارنات إيجارية", "طريقة الدخل"],
        "pdf_sections":   ["rental_value_summary"],
    },
    # Land (any) + market_value
    {
        "asset_types": {
            "urban_land", "agricultural_land", "industrial_land", "coastal_land", "desert_land",
            "أرض فضاء", "أرض زراعية",
        },
        "basis_of_value":      {"market_value", "fair_market_value", "standard_market_value"},
        "assignment_purposes": None,
        "enabled_methods": [
            "land_comparison", "residual_land_value", "hbu", "legal_review",
            "infrastructure_constraints",
        ],
        "workbook_sheets": ["مقارنة البيوع", "قيمة الأرض", "HBU", "الفحص القانوني"],
        "pdf_sections":   ["land_value_summary", "hbu_section"],
    },
    # Factory/Industrial + financing_mortgage
    {
        "asset_types": {
            "industrial_factory", "warehouse", "logistics_facility", "prefabricated_factory",
            "مصنع", "industrial", "industrial_logistics_facility_detailed",
        },
        "basis_of_value":      None,  # any
        "assignment_purposes": {"financing_mortgage", "bank_financing"},
        "enabled_methods": [
            "cost_approach", "depreciation_model", "income_approach", "dcf",
            "environmental_risk", "legal_review", "peer_review", "signature_gate",
        ],
        "workbook_sheets": ["طريقة التكلفة", "تفصيل الإهلاك", "طريقة الدخل",
                            "التدفقات النقدية DCF", "الفحص القانوني"],
        "pdf_sections":   ["cost_approach_section", "legal_section", "governance"],
    },
    # Residential + market_value
    {
        "asset_types": {
            "residential_apartment", "residential_villa", "residential_building",
            "residential_compound", "شقة سكنية", "عمارة سكنية",
        },
        "basis_of_value":      {"market_value", "fair_market_value", "standard_market_value"},
        "assignment_purposes": None,
        "enabled_methods": [
            "sales_comparison", "comparable_adjustment", "cost_approach", "income_approach",
        ],
        "workbook_sheets": ["مقارنة البيوع", "طريقة التكلفة", "طريقة الدخل"],
        "pdf_sections":   ["market_value_summary"],
    },
    # Residential + market_rent
    {
        "asset_types": {
            "residential_apartment", "residential_villa", "residential_building",
            "residential_compound", "شقة سكنية", "عمارة سكنية",
        },
        "basis_of_value":      {"market_rent", "rental_value", "rental_arbitration"},
        "assignment_purposes": None,
        "enabled_methods": [
            "rental_comparison", "comparable_adjustment", "direct_capitalization",
        ],
        "workbook_sheets": ["القيمة الإيجارية", "مقارنات إيجارية"],
        "pdf_sections":   ["rental_value_summary"],
    },
    # Office/Admin + investment_decision
    {
        "asset_types": {
            "administrative_office", "office_building", "business_park", "serviced_office",
        },
        "basis_of_value":      None,
        "assignment_purposes": {"investment_decision", "investment_analysis", "investment_funds"},
        "enabled_methods": [
            "dcf", "direct_capitalization", "income_approach", "hbu",
            "sales_comparison", "esg",
        ],
        "workbook_sheets": ["التدفقات النقدية DCF", "طريقة الدخل", "HBU", "ESG"],
        "pdf_sections":   ["investment_analysis_section", "hbu_section"],
    },
    # Court/Legal — any asset
    {
        "asset_types":         None,  # any asset
        "basis_of_value":      None,
        "assignment_purposes": {"court_dispute", "judicial_liquidation"},
        "enabled_methods": [
            "sales_comparison", "comparable_adjustment", "legal_review",
            "cost_approach", "income_approach",
        ],
        "workbook_sheets": ["مقارنة البيوع", "الفحص القانوني", "طريقة التكلفة"],
        "pdf_sections":   ["legal_section", "governance"],
    },
    # Insurance — any asset
    {
        "asset_types":         None,
        "basis_of_value":      {"insurable_value", "reinstatement_value"},
        "assignment_purposes": {"insurance"},
        "enabled_methods": [
            "cost_approach", "depreciation_model",
        ],
        "workbook_sheets": ["طريقة التكلفة", "تفصيل الإهلاك"],
        "pdf_sections":   ["cost_approach_section"],
    },
    # Financial Reporting (IFRS) — any asset
    {
        "asset_types":         None,
        "basis_of_value":      {"fair_value"},
        "assignment_purposes": {"financial_reporting"},
        "enabled_methods": [
            "sales_comparison", "comparable_adjustment", "income_approach",
            "dcf", "cost_approach",
        ],
        "workbook_sheets": ["مقارنة البيوع", "طريقة الدخل", "التدفقات النقدية DCF"],
        "pdf_sections":   ["fair_value_section", "governance"],
    },
    # Environmental/ESG — any asset
    {
        "asset_types":         None,
        "basis_of_value":      None,
        "assignment_purposes": {"environmental_risk_review", "environmental_impact_assessment"},
        "enabled_methods": [
            "esg", "environmental_risk", "cost_approach",
        ],
        "workbook_sheets": ["ESG والاستدامة", "تقييم الأثر البيئي"],
        "pdf_sections":   ["esg_section"],
    },
]

_DEFAULT_METHODS: list[str] = ["sales_comparison", "comparable_adjustment"]

# ── Alias / Backward Compat Mapping Table ─────────────────────────────────────

ALIAS_MAPPING: list[dict] = [
    # 1. market_value placed as asset type
    {
        "old_option": "market_value", "old_label_ar": "القيمة السوقية",
        "old_section": "asset_type or subtype",
        "problem_type": "misplaced_basis_of_value",
        "canonical_axis": "basis_of_value", "canonical_field": "basis_of_value",
        "canonical_value": "market_value", "canonical_label_ar": "القيمة السوقية",
        "migration_note": "market_value is a basis of value, not an asset type. Move to basis_of_value field.",
    },
    # 2. comparable_adjustment as purpose subroute
    {
        "old_option": "comparable_adjustment", "old_label_ar": "تعديل المقارنات",
        "old_section": "purpose_subpath / prof-purpose-subroute",
        "problem_type": "method_step_misplaced_as_purpose",
        "canonical_axis": "method_routing", "canonical_field": "method_steps",
        "canonical_value": "comparable_adjustment", "canonical_label_ar": "تعديل المقارنات",
        "migration_note": "comparable_adjustment is a valuation method step, not a purpose. Appears automatically in enabled_methods.",
    },
    # 3. hotel duplicated as both asset_type and subtype
    {
        "old_option": "hotel", "old_label_ar": "فندق",
        "old_section": "hospitality_entertainment family subtype (when asset_type is also hotel)",
        "problem_type": "duplicate_asset_value",
        "canonical_axis": "asset_classification", "canonical_field": "asset_subtype",
        "canonical_value": "business_hotel",
        "canonical_label_ar": "فندق أعمال (اختر النوع الفرعي الصحيح)",
        "migration_note": "hotel appears both as asset_type and as subtype under hospitality_entertainment. Preserve raw value. User should refine: business_hotel, boutique_hotel, resort_hotel, airport_hotel, etc.",
    },
    # 4. sales_comparison_market_value as purpose route
    {
        "old_option": "sales_comparison_market_value",
        "old_label_ar": "مقارنة المبيعات",
        "old_section": "prof-purpose-route",
        "problem_type": "method_step_misplaced_as_purpose",
        "canonical_axis": "method_routing", "canonical_field": "enabled_methods",
        "canonical_value": "sales_comparison",
        "canonical_label_ar": "طريقة مقارنة المبيعات",
        "migration_note": "sales_comparison is a method, not a purpose. Derived automatically from (asset_type + basis_of_value + assignment_purpose).",
    },
    # 5. standard_market_value as purpose route
    {
        "old_option": "standard_market_value",
        "old_label_ar": "القيمة السوقية القياسية",
        "old_section": "prof-purpose-route",
        "problem_type": "misplaced_basis_of_value",
        "canonical_axis": "basis_of_value", "canonical_field": "basis_of_value",
        "canonical_value": "market_value",
        "canonical_label_ar": "القيمة السوقية",
        "migration_note": "standard_market_value is a basis of value, not a purpose route. Move to basis_of_value field.",
    },
    # 6. market_value_with_habu as purpose route
    {
        "old_option": "market_value_with_habu",
        "old_label_ar": "القيمة السوقية وفق HABU",
        "old_section": "prof-purpose-route",
        "problem_type": "mixed_basis_and_method",
        "canonical_axis": "basis_of_value + method_routing",
        "canonical_field": "basis_of_value + value_premise",
        "canonical_value": "market_value + highest_and_best_use",
        "canonical_label_ar": "القيمة السوقية + HABU",
        "migration_note": "Split: basis_of_value=market_value, value_premise=highest_and_best_use. HBU appears in enabled_methods automatically.",
    },
    # 7. dcf_investment_value as purpose route
    {
        "old_option": "dcf_investment_value",
        "old_label_ar": "DCF - التدفق النقدي المخصوم",
        "old_section": "prof-purpose-route",
        "problem_type": "method_step_misplaced_as_purpose",
        "canonical_axis": "method_routing", "canonical_field": "enabled_methods",
        "canonical_value": "dcf",
        "canonical_label_ar": "طريقة DCF",
        "migration_note": "DCF is a method, not a purpose. Derived automatically. Purpose should be investment_decision; basis_of_value=investment_value.",
    },
    # 8. fair_market_value as valuation_purpose
    {
        "old_option": "fair_market_value",
        "old_label_ar": "البيع والشراء — القيمة السوقية العادلة",
        "old_section": "val-purpose (ordinary valuation)",
        "problem_type": "mixed_basis_and_purpose",
        "canonical_axis": "basis_of_value + assignment_purpose",
        "canonical_field": "basis_of_value + assignment_purpose",
        "canonical_value": "market_value + sale_purchase",
        "canonical_label_ar": "القيمة السوقية + البيع والشراء",
        "migration_note": "Split: basis_of_value=market_value, assignment_purpose=sale_purchase. Backward compat: store as-is, add canonical fields.",
    },
    # 9. rental_arbitration as valuation_purpose
    {
        "old_option": "rental_arbitration",
        "old_label_ar": "القيمة الإيجارية العادلة",
        "old_section": "val-purpose (ordinary valuation)",
        "problem_type": "misplaced_basis_of_value",
        "canonical_axis": "basis_of_value",
        "canonical_field": "basis_of_value",
        "canonical_value": "market_rent",
        "canonical_label_ar": "القيمة الإيجارية السوقية",
        "migration_note": "rental_arbitration indicates basis_of_value=market_rent. Preserve raw value. Canonical: basis_of_value=market_rent.",
    },
    # 10. highest_and_best_use as purpose
    {
        "old_option": "highest_and_best_use",
        "old_label_ar": "تحليل أعلى وأفضل استغلال",
        "old_section": "val-purpose (ordinary valuation)",
        "problem_type": "method_step_misplaced_as_purpose",
        "canonical_axis": "method_routing",
        "canonical_field": "enabled_methods",
        "canonical_value": "hbu",
        "canonical_label_ar": "HBU — أعلى وأفضل استغلال",
        "migration_note": "HBU is a method/analysis step, not an assignment purpose. Add hbu to enabled_methods automatically. Assignment purpose remains: investment_decision or sale_purchase.",
    },
    # 11. sensitivity_analysis as purpose subroute
    {
        "old_option": "sensitivity_analysis",
        "old_label_ar": "تحليل الحساسية",
        "old_section": "prof-purpose-route (under عدم اليقين)",
        "problem_type": "method_step_misplaced_as_purpose",
        "canonical_axis": "method_routing",
        "canonical_field": "method_steps",
        "canonical_value": "sensitivity_analysis",
        "canonical_label_ar": "تحليل الحساسية",
        "migration_note": "Sensitivity analysis is a method step, not a purpose. Appears in enabled_methods under investment_decision or any purpose when report_type=professional_report.",
    },
]

# ── Validation functions ───────────────────────────────────────────────────────

def validate_asset_family(value: str) -> tuple[bool, str]:
    if not value:
        return True, ""
    if value in VALID_ASSET_FAMILIES:
        return True, ""
    return False, f"asset_family غير معروفة: '{value}'. القيم المتاحة: {', '.join(sorted(VALID_ASSET_FAMILIES)[:10])} ..."


def validate_asset_type(value: str) -> tuple[bool, str]:
    if not value:
        return True, ""
    if value in VALID_ASSET_TYPES:
        return True, ""
    return False, f"asset_type غير معروف: '{value}'. سيُقبَل كقيمة مخصصة مع تحذير."


def validate_assignment_purpose(value: str) -> tuple[bool, str]:
    if not value:
        return True, ""
    if value in VALID_ASSIGNMENT_PURPOSES:
        return True, ""
    return False, f"assignment_purpose غير معروف: '{value}'. سيُقبَل كقيمة مخصصة مع تحذير."


def validate_basis_of_value(value: str) -> tuple[bool, str]:
    if not value:
        return True, ""
    if value in VALID_BASIS_OF_VALUE:
        return True, ""
    return False, f"basis_of_value غير معروف: '{value}'. القيم الصالحة: {', '.join(sorted(VALID_BASIS_OF_VALUE))}."


def validate_value_premise(value: str) -> tuple[bool, str]:
    if not value:
        return True, ""
    if value in VALID_VALUE_PREMISES:
        return True, ""
    return False, f"value_premise غير معروف: '{value}'."


# ── Misplacement detection ────────────────────────────────────────────────────

def detect_misplacements(
    asset_type: str = "",
    asset_subtype: str = "",
    assignment_purpose: str = "",
    valuation_purpose: str = "",
    purpose_subpath: str = "",
    basis_of_value: str = "",
) -> list[dict]:
    """Detect taxonomy misplacements and return list of warning dicts."""
    warnings: list[dict] = []

    # Detect hotel duplicate: asset_type=hotel AND asset_subtype=hotel
    if (asset_type.lower() in {"hotel", "فندق", "hotel_resort_detailed"} and
            asset_subtype.lower() == "hotel"):
        warnings.append({
            "warning_code": "duplicate_asset_value",
            "field": "asset_subtype",
            "value": asset_subtype,
            "message": (
                "النوع الفرعي 'hotel' مكرر مع نوع الأصل 'hotel'. "
                "يُرجى اختيار نوع فرعي أكثر تحديداً: business_hotel, boutique_hotel, resort_hotel, airport_hotel."
            ),
            "canonical_suggestion": "business_hotel",
        })

    # Detect market_value/rental_value placed as valuation_purpose
    _bov_misplaced = {
        "market_value": "market_value",
        "rental_value": "market_rent",
        "fair_market_value": "market_value",
        "standard_market_value": "market_value",
        "rental_arbitration": "market_rent",
    }
    vp_lower = (valuation_purpose or assignment_purpose or "").lower()
    if vp_lower in _bov_misplaced:
        warnings.append({
            "warning_code": "misplaced_basis_of_value",
            "field": "valuation_purpose / assignment_purpose",
            "value": vp_lower,
            "message": (
                f"'{vp_lower}' هو أساس قيمة وليس غرض تكليف. "
                f"الحقل الصحيح: basis_of_value={_bov_misplaced[vp_lower]}."
            ),
            "canonical_suggestion": f"basis_of_value={_bov_misplaced[vp_lower]}",
        })

    # Detect method steps placed as purpose_subpath
    if purpose_subpath and purpose_subpath in _MISPLACED_AS_PURPOSE:
        warnings.append({
            "warning_code": "method_step_misplaced_as_purpose",
            "field": "purpose_subpath",
            "value": purpose_subpath,
            "message": (
                f"'{purpose_subpath}' هو خطوة منهجية وليس غرض تكليف. "
                f"القيمة الصحيحة: method_steps={_MISPLACED_AS_PURPOSE[purpose_subpath]}."
            ),
            "canonical_suggestion": f"method_steps={_MISPLACED_AS_PURPOSE[purpose_subpath]}",
        })

    # Detect HBU used as purpose
    if vp_lower == "highest_and_best_use":
        warnings.append({
            "warning_code": "method_step_misplaced_as_purpose",
            "field": "assignment_purpose",
            "value": "highest_and_best_use",
            "message": (
                "HBU (أعلى وأفضل استخدام) هو خطوة تحليل وليس غرض تكليف. "
                "سيُضاف HBU تلقائياً إلى enabled_methods. "
                "غرض التكليف المقترح: investment_decision."
            ),
            "canonical_suggestion": "assignment_purpose=investment_decision + enabled_methods includes hbu",
        })

    return warnings


# ── Backward compatibility normalization ──────────────────────────────────────

def normalize_legacy_fields(
    property_type: str = "",
    valuation_purpose: str = "",
    property_subtype: str = "",
    basis_of_value: str = "",
    purpose_subpath: str = "",
) -> dict:
    """
    Map legacy fields to canonical four-axis values.
    Returns dict with canonical fields + raw_legacy_values.
    Does NOT reject any value — only normalizes and warns.
    """
    canonical: dict = {
        "asset_type":          property_type or "",
        "asset_subtype":       property_subtype or "",
        "assignment_purpose":  "",
        "basis_of_value":      basis_of_value or "",
        "method_route":        "",
    }
    raw_legacy: dict = {
        "property_type":    property_type,
        "valuation_purpose": valuation_purpose,
        "property_subtype": property_subtype,
        "basis_of_value":   basis_of_value,
        "purpose_subpath":  purpose_subpath,
    }

    # Map valuation_purpose → assignment_purpose or basis_of_value
    _purpose_to_basis = {
        "fair_market_value":   "market_value",
        "rental_arbitration":  "market_rent",
        "rental_value":        "market_rent",
        "market_value":        "market_value",
        "standard_market_value": "market_value",
        "judicial_liquidation": "liquidation_value",
        "insurance":           "insurable_value",
        "financial_reporting": None,  # purpose only, basis determined separately
    }
    _purpose_to_assignment = {
        "fair_market_value":   "sale_purchase",
        "acquisition":         "sale_purchase",
        "bank_financing":      "financing_mortgage",
        "judicial_liquidation": "court_dispute",
        "insurance":           "insurance",
        "investment_analysis": "investment_decision",
        "rental_arbitration":  "investment_decision",
        "rental_value":        "investment_decision",
        "tax_assessment":      "tax_government",
        "financial_reporting": "financial_reporting",
        "usufruct":            "inheritance_partition",
        "highest_and_best_use": "investment_decision",
        "investment_funds":    "investment_decision",
        "environmental_impact_assessment": "environmental_risk_review",
    }

    if valuation_purpose:
        bov = _purpose_to_basis.get(valuation_purpose)
        if bov and not canonical["basis_of_value"]:
            canonical["basis_of_value"] = bov
        asgn = _purpose_to_assignment.get(valuation_purpose)
        if asgn:
            canonical["assignment_purpose"] = asgn
        elif valuation_purpose not in _purpose_to_basis and valuation_purpose not in _purpose_to_assignment:
            # Unknown purpose — pass through as assignment_purpose
            canonical["assignment_purpose"] = valuation_purpose

    # Map purpose_subpath → method_route
    if purpose_subpath and purpose_subpath in _MISPLACED_AS_PURPOSE:
        canonical["method_route"] = _MISPLACED_AS_PURPOSE[purpose_subpath]
    elif purpose_subpath:
        canonical["method_route"] = purpose_subpath

    return {
        "canonical": canonical,
        "raw_legacy_values": raw_legacy,
    }


# ── Method Routing ────────────────────────────────────────────────────────────

def derive_method_route(
    asset_type: str = "",
    asset_family: str = "",
    assignment_purpose: str = "",
    basis_of_value: str = "",
    report_type: str = "professional_report",
) -> dict:
    """
    Derive enabled_methods, workbook_sheets, pdf_sections from the four canonical inputs.
    Returns advisory routing only — does not generate outputs or bypass certification gates.
    """
    at  = (asset_type or "").lower().strip()
    af  = (asset_family or "").lower().strip()
    ap  = (assignment_purpose or "").lower().strip()
    bov = (basis_of_value or "").lower().strip()

    enabled: list[str] = []
    sheets: list[str] = []
    sections: list[str] = []
    routing_warnings: list[str] = []

    for rule in _ROUTING_MATRIX:
        # Check asset_type match
        at_match = (rule["asset_types"] is None) or (at in rule["asset_types"])
        # Check basis_of_value match
        bov_match = (rule["basis_of_value"] is None) or (bov in rule["basis_of_value"])
        # Check assignment_purpose match
        ap_match = (rule["assignment_purposes"] is None) or (ap in rule["assignment_purposes"])

        if at_match and bov_match and ap_match:
            for m in rule["enabled_methods"]:
                if m not in enabled:
                    enabled.append(m)
            for s in rule["workbook_sheets"]:
                if s not in sheets:
                    sheets.append(s)
            for p in rule["pdf_sections"]:
                if p not in sections:
                    sections.append(p)

    if not enabled:
        enabled = list(_DEFAULT_METHODS)
        routing_warnings.append(
            "لم يتم العثور على مسار طرق محدد — تم تفعيل الطرق الافتراضية (مقارنة المبيعات، تعديل المقارنات)."
        )

    # Professional report always adds governance methods
    if report_type == "professional_report":
        for m in ("hbu", "esg", "swot", "peer_review"):
            if m not in enabled:
                enabled.append(m)

    return {
        "enabled_methods":        enabled,
        "required_workbook_sheets": sheets,
        "required_pdf_sections":  sections,
        "routing_warnings":       routing_warnings,
        "method_routing_advisory": (
            "مسار الطرق استشاري فقط — لا يتجاوز بوابات جاهزية البيانات. "
            "يمكن للخبير تعديل الطرق المفعلة."
        ),
    }


# ── Main context builder ───────────────────────────────────────────────────────

def get_taxonomy_v2_context(
    asset_family: str = "",
    asset_type: str = "",
    asset_subtype: str = "",
    asset_condition_path: str = "",
    assignment_purpose: str = "",
    intended_use: str = "",
    intended_user_category: str = "",
    professional_context_path: str = "",
    basis_of_value: str = "",
    value_premise: str = "",
    value_output_type: str = "",
    report_type: str = "professional_report",
    # Legacy fields for backward compat
    property_type: str = "",
    valuation_purpose: str = "",
    property_subtype: str = "",
    purpose_subpath: str = "",
) -> dict:
    """
    Build full canonical taxonomy context including:
    - canonical_taxonomy (four axes)
    - derived_method_route
    - taxonomy_warnings (misplacements + unknown values)
    - raw_legacy_values
    """
    taxonomy_warnings: list[dict] = []

    # Normalize legacy fields if canonical not provided
    if not asset_type and property_type:
        asset_type = property_type
    if not assignment_purpose or not basis_of_value:
        legacy_norm = normalize_legacy_fields(
            property_type=property_type,
            valuation_purpose=valuation_purpose,
            property_subtype=property_subtype,
            basis_of_value=basis_of_value,
            purpose_subpath=purpose_subpath,
        )
        canon = legacy_norm["canonical"]
        if not asset_type:
            asset_type = canon.get("asset_type", "")
        if not asset_subtype:
            asset_subtype = canon.get("asset_subtype", "")
        if not assignment_purpose:
            assignment_purpose = canon.get("assignment_purpose", "")
        if not basis_of_value:
            basis_of_value = canon.get("basis_of_value", "")

    # Validate fields — soft validation only (warn, not reject)
    for fn, val, validator in [
        ("asset_family",        asset_family,        validate_asset_family),
        ("assignment_purpose",  assignment_purpose,  validate_assignment_purpose),
        ("basis_of_value",      basis_of_value,      validate_basis_of_value),
        ("value_premise",       value_premise,        validate_value_premise),
    ]:
        ok, msg = validator(val)
        if not ok:
            taxonomy_warnings.append({"field": fn, "warning": msg})

    # Detect misplacements
    misplacements = detect_misplacements(
        asset_type=asset_type,
        asset_subtype=asset_subtype,
        assignment_purpose=assignment_purpose,
        valuation_purpose=valuation_purpose,
        purpose_subpath=purpose_subpath,
        basis_of_value=basis_of_value,
    )
    taxonomy_warnings.extend(misplacements)

    # Derive method routing
    method_route = derive_method_route(
        asset_type=asset_type,
        asset_family=asset_family,
        assignment_purpose=assignment_purpose,
        basis_of_value=basis_of_value,
        report_type=report_type,
    )

    canonical_taxonomy = {
        "axis_1_asset_classification": {
            "asset_family":          asset_family,
            "asset_type":            asset_type,
            "asset_subtype":         asset_subtype,
            "asset_condition_path":  asset_condition_path,
        },
        "axis_2_assignment_purpose": {
            "assignment_purpose":         assignment_purpose,
            "intended_use":               intended_use,
            "intended_user_category":     intended_user_category,
            "professional_context_path":  professional_context_path,
        },
        "axis_3_basis_of_value": {
            "basis_of_value":   basis_of_value,
            "value_premise":    value_premise,
            "value_output_type": value_output_type,
        },
        "axis_4_report_type": {
            "report_type": report_type,
        },
    }

    return {
        "canonical_taxonomy":   canonical_taxonomy,
        "derived_method_route": method_route,
        "taxonomy_warnings":    taxonomy_warnings,
        "raw_legacy_values": {
            "property_type":    property_type,
            "valuation_purpose": valuation_purpose,
            "property_subtype": property_subtype,
            "purpose_subpath":  purpose_subpath,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Asset-Specific Requirements Catalogue (Addendum — Preservation Layer)
# ═══════════════════════════════════════════════════════════════════════════════

_ASSET_REQUIREMENTS_CATALOGUE: dict[str, dict] = {

    # ── Hotel / Hospitality ──────────────────────────────────────────────────
    "hotel": {
        "requirements_panel_title_ar": "متطلبات تقييم فندق",
        "asset_label_ar": "فندق / فندق بوتيك / فندق تجاري",
        "asset_family":   "hospitality_leisure",
        "requirement_groups": [
            "G1_normalized_asset_data", "G2_operations_kpis", "G3_management_contracts",
            "G4_revenue_expenses", "G5_site_facilities", "G6_technical_capex",
            "G7_licenses_compliance", "G8_market_competition", "G9_documents",
            "G10_methods", "G11_legacy_extras",
        ],
        "required_inputs": [
            "number_of_rooms",
            "adr",
            "occupancy_rate",
            "revpar",
            "room_revenue",
            "food_beverage_revenue",
            "events_banquets_revenue",
            "operating_expenses",
            "management_or_franchise_agreement",
            "hotel_class_rating",
            "operating_status",
            "required_capex",
            "tourism_operational_risk",
            "number_of_keys",
            "gop",
            "noi",
            "ebitda",
            "ffe_reserve",
            "competitor_set",
            "tourism_demand",
        ],
        "required_inputs_labels_ar": {
            "number_of_rooms":                   "عدد الغرف",
            "adr":                               "متوسط سعر الغرفة اليومي ADR",
            "occupancy_rate":                    "معدل الإشغال",
            "revpar":                            "RevPAR",
            "room_revenue":                      "إيرادات الغرف",
            "food_beverage_revenue":             "إيرادات الأغذية والمشروبات",
            "events_banquets_revenue":           "إيرادات القاعات والفعاليات",
            "operating_expenses":                "مصروفات التشغيل",
            "management_or_franchise_agreement": "عقد الإدارة أو الامتياز",
            "hotel_class_rating":                "تصنيف الفندق / النجوم",
            "operating_status":                  "حالة التشغيل",
            "required_capex":                    "CapEx المطلوب",
            "tourism_operational_risk":          "مخاطر التشغيل والسياحة",
        },
        "required_evidence": [
            "hotel_license", "financial_statements_3_years", "management_agreement",
            "star_rating_certificate", "ownership_deed", "building_permit",
        ],
        "recommended_methods": [
            "sales_comparison", "hotel_comparable_analysis", "income_approach",
            "direct_capitalization", "dcf", "hbu", "legal_review", "esg", "swot",
        ],
        "recommended_workbook_sheets": [
            "hotel_operational_data", "adr_revpar_analysis", "income_approach_hotel",
            "dcf_hotel", "comparable_hotel_sales", "hbu_analysis",
        ],
        "recommended_pdf_sections": [
            "hotel_operational_summary", "income_approach_section",
            "dcf_section", "comparable_analysis_section",
        ],
        "warnings": [
            "يجب مراجعة عقد الإدارة أو الامتياز قبل إصدار أي قيمة نهائية.",
            "RevPAR و ADR يُشكّلان ركيزة نهج الدخل — التحقق منهما إلزامي.",
        ],
        "legacy_requirement_keys": [
            "hotel_resort_detailed", "ht_number_of_rooms", "ht_adr",
            "ht_occupancy_rate", "ht_revpar", "ht_room_revenue",
            "ht_food_beverage_revenue", "ht_events_banquets_revenue",
            "ht_operating_expenses", "ht_management_or_franchise_agreement",
            "ht_hotel_class_rating", "ht_operating_status",
            "ht_required_capex", "ht_tourism_operational_risk",
            "ht_number_of_keys", "ht_number_of_suites", "ht_number_of_villas",
            "ht_star_rating", "ht_hotel_type", "ht_brand_positioning",
            "ht_target_segments", "ht_resort_facilities", "ht_tourism_certification",
            "ht_annual_occupancy", "ht_seasonal_occupancy", "ht_alos",
            "ht_seasonality_index", "ht_trevpar", "ht_goppar",
            "ht_mpi", "ht_ari", "ht_rgi",
            "ht_online_review_score", "ht_guest_satisfaction_index",
            "ht_demand_mix", "ht_distribution_channels",
            "ht_operator_name", "ht_management_agreement_type",
            "ht_management_fee_structure", "ht_franchise_flag",
            "ht_franchise_brand", "ht_franchise_fee", "ht_key_money",
            "ht_incentive_fee_structure", "ht_contract_remaining_term",
            "ht_termination_clause", "ht_non_compete_clause",
            "ht_technical_services_agreement", "ht_asset_management_agreement",
            "ht_spa_wellness_revenue", "ht_recreation_revenue",
            "ht_mice_revenue", "ht_retail_revenue", "ht_total_revenue",
            "ht_payroll_expenses", "ht_utilities_expenses", "ht_rm_expenses",
            "ht_management_fees", "ht_franchise_fees",
            "ht_gop", "ht_ebitda", "ht_noi", "ht_ffe_reserve",
            "ht_land_area", "ht_building_area", "ht_pool_count",
            "ht_restaurant_count", "ht_meeting_rooms_area",
            "ht_parking_capacity", "ht_beach_access", "ht_golf_course",
            "ht_spa_area", "ht_site_characteristics",
            "ht_building_age", "ht_last_renovation_date",
            "ht_structural_condition", "ht_energy_system", "ht_hvac_system",
            "ht_building_management_system", "ht_capex_backlog",
            "ht_useful_life_remaining",
            "ht_hotel_license_status", "ht_fire_safety_certificate",
            "ht_health_permit", "ht_tourism_authority_registration",
            "ht_environmental_compliance", "ht_accessibility_compliance",
            "ht_brand_agreement_registrations",
            "ht_competitor_set", "ht_competitive_position",
            "ht_market_demand_forecast", "ht_tourism_demand", "ht_online_reputation",
            "ht_room_mix", "ht_average_room_size",
            "ht_adr_history", "ht_revpar_history", "ht_occupancy_history",
            "ht_banquet_revenue", "ht_other_operating_income",
            "ht_land_building_separation", "ht_terminal_cap_rate",
            "ht_discount_rate", "ht_hbu_constraints", "ht_risk_notes",
            "ht_audited_financials",
        ],
        "preservation_pass": True,
        "missing_from_current_after_restore": [],
        "deleted_requirements": [],
    },

    # ── Resort (shared hotel family) ────────────────────────────────────────
    "resort": {
        "requirements_panel_title_ar": "متطلبات تقييم منتجع",
        "asset_family":   "hospitality_leisure",
        "required_inputs": [
            "number_of_rooms", "adr", "occupancy_rate", "revpar",
            "room_revenue", "operating_expenses", "hotel_class_rating",
            "operating_status", "required_capex",
        ],
        "required_inputs_labels_ar": {
            "number_of_rooms":    "عدد الغرف / الوحدات",
            "adr":                "متوسط سعر الغرفة اليومي ADR",
            "occupancy_rate":     "معدل الإشغال",
            "revpar":             "RevPAR",
            "room_revenue":       "إيرادات الغرف",
            "operating_expenses": "مصروفات التشغيل",
            "hotel_class_rating": "تصنيف المنتجع",
            "operating_status":   "حالة التشغيل",
            "required_capex":     "CapEx المطلوب",
        },
        "required_evidence": [
            "hotel_license", "financial_statements_3_years", "ownership_deed",
        ],
        "recommended_methods": [
            "sales_comparison", "income_approach", "direct_capitalization", "dcf", "hbu",
        ],
        "recommended_workbook_sheets": [
            "hotel_operational_data", "adr_revpar_analysis", "income_approach_hotel", "dcf_hotel",
        ],
        "recommended_pdf_sections": [
            "hotel_operational_summary", "income_approach_section", "dcf_section",
        ],
        "warnings": [
            "RevPAR و ADR يُشكّلان ركيزة نهج الدخل — التحقق منهما إلزامي.",
        ],
        "legacy_requirement_keys": [
            "hotel_resort_detailed", "ht_number_of_rooms", "ht_adr", "ht_occupancy_rate",
            "ht_revpar", "ht_operating_expenses",
        ],
    },

    # ── Industrial Factory ───────────────────────────────────────────────────
    "industrial_factory": {
        "requirements_panel_title_ar": "متطلبات تقييم مصنع / أصل صناعي",
        "asset_label_ar": "مصنع / أصل صناعي / منشأة لوجستية متخصصة",
        "asset_family":   "industrial_logistics",
        "requirement_groups": [
            "G1_asset_definition", "G2_location_land_access", "G3_buildings_structure",
            "G4_utilities_machinery", "G5_financial_operational", "G6_environmental_compliance",
            "G7_documents", "G8_additional", "G9_methods",
        ],
        "required_inputs": [
            "land_area", "building_area", "production_halls",
            "utilities_capacity", "machinery_separation",
            "environmental_risks", "replacement_cost",
            "depreciation_model", "operating_status",
            "special_purpose_limitation",
        ],
        "required_inputs_labels_ar": {
            "land_area":                 "مساحة الأرض",
            "building_area":             "مساحة المبنى / المباني",
            "production_halls":          "قاعات الإنتاج وعددها",
            "utilities_capacity":        "طاقة المرافق (كهرباء / مياه / غاز)",
            "machinery_separation":      "هل يمكن فصل الآلات عن العقار؟",
            "environmental_risks":       "المخاطر البيئية",
            "replacement_cost":          "تكلفة الإحلال",
            "depreciation_model":        "نموذج الإهلاك",
            "operating_status":          "حالة التشغيل",
            "special_purpose_limitation": "قيود الغرض الخاص",
        },
        "required_evidence": [
            "ownership_deed", "building_permit", "environmental_clearance",
            "utilities_contracts", "machinery_inventory",
        ],
        "recommended_methods": [
            "cost_approach", "depreciation_model", "income_approach",
            "dcf", "environmental_risk", "legal_review", "hbu", "special_purpose_warning",
        ],
        "recommended_workbook_sheets": [
            "cost_approach_industrial", "depreciation_schedule", "environmental_risk_assessment",
            "income_approach_industrial", "hbu_industrial",
        ],
        "recommended_pdf_sections": [
            "cost_approach_section", "depreciation_analysis",
            "environmental_risk_section", "hbu_section",
        ],
        "warnings": [
            "الأصول الصناعية ذات الغرض الخاص قد تفرض قيوداً على قيمة السوق.",
            "المخاطر البيئية قد تُخفض القيمة بشكل مادي — يلزم تقييم مستقل.",
        ],
        "legacy_requirement_keys": [
            "industrial_logistics_facility_detailed",
            "industrial_factory_requirements", "factory_land_area",
            "factory_building_area", "factory_production_halls",
            "factory_environmental_risks", "factory_replacement_cost",
            "fac_asset_type_classification", "fac_industrial_sub_type",
            "fac_industrial_usage", "fac_special_purpose_flag",
            "fac_land_area", "fac_land_shape", "fac_frontage",
            "fac_access_road_width", "fac_distance_to_port",
            "fac_distance_to_highway", "fac_logistics_location_score",
            "fac_zoning_permit", "fac_building_area_total",
            "fac_production_hall_area", "fac_office_area",
            "fac_storage_area", "fac_clear_height", "fac_structural_type",
            "fac_building_condition", "fac_age_years",
            "fac_power_capacity_kw", "fac_water_capacity",
            "fac_gas_connection", "fac_drainage_system",
            "fac_machinery_included", "fac_machinery_inventory",
            "fac_machinery_age", "fac_automation_level",
            "fac_current_tenant", "fac_monthly_rent",
            "fac_operating_expenses", "fac_noi",
            "fac_replacement_cost", "fac_depreciation_model",
            "fac_environmental_risk_level", "fac_environmental_clearance",
            "fac_hazardous_materials", "fac_contamination_flag",
        ],
        "preservation_pass": True,
        "missing_from_current_after_restore": [],
        "deleted_requirements": [],
    },

    # ── Land (urban) ─────────────────────────────────────────────────────────
    "urban_land": {
        "requirements_panel_title_ar": "متطلبات تقييم أرض",
        "asset_label_ar": "أرض بيضاء / أرض قابلة للتطوير / أرض تجارية",
        "asset_family":   "land_plots",
        "requirement_groups": [
            "G1_identification_classification", "G2_location_boundaries",
            "G3_utilities_infrastructure", "G4_development_potential",
            "G5_legal_documentation", "G6_market_comparables",
            "G7_additional", "G8_methods",
        ],
        "required_inputs": [
            "zoning", "permitted_use", "frontage", "access_roads",
            "utilities_available", "development_potential",
            "legal_constraints", "infrastructure_constraints",
        ],
        "required_inputs_labels_ar": {
            "zoning":                    "منطقة التخطيط / التصنيف العمراني",
            "permitted_use":             "الاستخدام المسموح به",
            "frontage":                  "الواجهة (م)",
            "access_roads":              "طرق الوصول",
            "utilities_available":       "المرافق المتاحة",
            "development_potential":     "إمكانية التطوير",
            "legal_constraints":         "القيود القانونية",
            "infrastructure_constraints": "قيود البنية التحتية",
        },
        "required_evidence": [
            "ownership_deed", "surveyor_report", "zoning_certificate",
            "utilities_availability_letter",
        ],
        "recommended_methods": [
            "land_comparison", "residual_land_value", "hbu", "legal_review",
            "infrastructure_constraints",
        ],
        "recommended_workbook_sheets": [
            "land_comparison_sheet", "residual_land_value_sheet", "hbu_land",
        ],
        "recommended_pdf_sections": [
            "land_comparison_section", "residual_value_section", "hbu_section",
        ],
        "warnings": [
            "قيود التخطيط والتصنيف العمراني تؤثر مباشرة على إمكانية التطوير.",
            "يُفضل إجراء تحليل HBU لأراضي التطوير.",
        ],
        "legacy_requirement_keys": [
            "land_requirements", "land_zoning", "land_permitted_use",
            "land_frontage", "land_access_roads", "land_utilities",
            "land_area_m2", "land_shape", "land_dimensions",
            "land_topography", "land_gps_coordinates",
            "land_water_connection", "land_electricity_connection",
            "land_sewage_connection", "land_gas_connection",
            "land_road_width", "land_infrastructure_readiness",
            "land_far", "land_bcr", "land_max_floors",
            "land_development_scenario", "land_residual_value",
            "land_hbu_analysis", "land_encumbrances",
            "land_mortgage_flag", "land_court_order_flag",
            "land_market_comparables", "land_price_per_m2",
            "land_recent_sales", "land_comparable_adjustments",
        ],
        "preservation_pass": True,
        "missing_from_current_after_restore": [],
        "deleted_requirements": [],
    },

    # ── Agricultural Land ────────────────────────────────────────────────────
    "agricultural_land": {
        "requirements_panel_title_ar": "متطلبات تقييم أرض زراعية",
        "asset_family":   "agri_environmental",
        "required_inputs": [
            "zoning", "permitted_use", "soil_quality", "water_access",
            "crop_type", "utilities_available", "legal_constraints",
        ],
        "required_inputs_labels_ar": {
            "zoning":             "التصنيف الزراعي",
            "permitted_use":      "الاستخدام المسموح به",
            "soil_quality":       "جودة التربة",
            "water_access":       "مصادر المياه",
            "crop_type":          "نوع المحصول الزراعي",
            "utilities_available": "المرافق المتاحة",
            "legal_constraints":  "القيود القانونية",
        },
        "required_evidence": [
            "ownership_deed", "agricultural_registration", "water_rights_document",
        ],
        "recommended_methods": [
            "land_comparison", "income_approach", "residual_land_value", "legal_review",
        ],
        "recommended_workbook_sheets": [
            "agricultural_land_sheet", "income_approach_agri",
        ],
        "recommended_pdf_sections": [
            "agricultural_land_section", "income_approach_section",
        ],
        "warnings": [
            "الأراضي الزراعية تخضع لقوانين خاصة تحظر تحويلها بدون إذن رسمي.",
        ],
        "legacy_requirement_keys": [
            "agricultural_land_requirements", "agri_soil_quality", "agri_water_access",
        ],
    },

    # ── Retail Shop ──────────────────────────────────────────────────────────
    "retail_shop": {
        "requirements_panel_title_ar": "متطلبات تقييم محل تجاري",
        "asset_label_ar": "محل تجاري / متجر / مساحة تجارية",
        "asset_family":   "commercial_retail",
        "requirement_groups": [
            "G1_asset_basic_data", "G2_location_footfall",
            "G3_lease_income", "G4_market_comparables",
            "G5_documents", "G6_additional", "G7_methods",
        ],
        "required_inputs": [
            "frontage", "footfall", "location_quality", "visibility",
            "lease_terms", "monthly_rent", "sales_comparables", "rental_comparables",
        ],
        "required_inputs_labels_ar": {
            "frontage":           "الواجهة (م)",
            "footfall":           "حركة المرور / الزوار",
            "location_quality":   "جودة الموقع",
            "visibility":         "الظهور / الرؤية",
            "lease_terms":        "شروط الإيجار",
            "monthly_rent":       "الإيجار الشهري الحالي",
            "sales_comparables":  "مقارنات البيع",
            "rental_comparables": "مقارنات الإيجار",
        },
        "required_evidence": [
            "ownership_deed", "lease_agreement", "commercial_license",
            "sales_comparable_evidence",
        ],
        "recommended_methods": [
            "sales_comparison", "rental_comparison", "direct_capitalization",
            "dcf", "comparable_adjustment",
        ],
        "recommended_workbook_sheets": [
            "retail_sales_comparables", "rental_comparison_sheet",
            "direct_cap_sheet", "location_quality_matrix",
        ],
        "recommended_pdf_sections": [
            "retail_market_analysis", "comparable_analysis_section",
            "income_approach_section",
        ],
        "warnings": [
            "حركة المرور وجودة الموقع عوامل حاكمة في تقييم المحلات التجارية.",
        ],
        "legacy_requirement_keys": [
            "retail_shop_detailed", "retail_requirements",
            "retail_frontage", "retail_footfall",
            "retail_lease_terms", "retail_monthly_rent",
            "retail_area_m2", "retail_floor_level",
            "retail_visibility_score", "retail_corner_unit_flag",
            "retail_anchor_proximity", "retail_parking_spaces",
            "retail_access_type", "retail_peak_hours",
            "retail_tenant_name", "retail_lease_start_date",
            "retail_lease_end_date", "retail_rent_free_period",
            "retail_service_charges", "retail_turnover_clause",
            "retail_passing_rent", "retail_market_rent",
            "retail_void_period", "retail_occupancy_rate",
            "retail_cap_rate", "retail_noi",
        ],
        "preservation_pass": True,
        "missing_from_current_after_restore": [],
        "deleted_requirements": [],
    },

    # ── Shopping Mall ────────────────────────────────────────────────────────
    "shopping_mall": {
        "requirements_panel_title_ar": "متطلبات تقييم مركز تجاري / مول",
        "asset_family":   "commercial_retail",
        "required_inputs": [
            "gla", "occupancy_rate", "anchor_tenants", "lease_terms",
            "net_operating_income", "management_expenses", "footfall",
        ],
        "required_inputs_labels_ar": {
            "gla":                  "المساحة الإجمالية للتأجير (GLA)",
            "occupancy_rate":       "معدل الإشغال",
            "anchor_tenants":       "المستأجرون الرئيسيون",
            "lease_terms":          "شروط عقود الإيجار",
            "net_operating_income": "صافي الدخل التشغيلي",
            "management_expenses":  "مصروفات الإدارة",
            "footfall":             "حركة الزوار",
        },
        "required_evidence": [
            "ownership_deed", "lease_register", "management_accounts",
        ],
        "recommended_methods": [
            "income_approach", "direct_capitalization", "dcf",
            "sales_comparison", "comparable_adjustment",
        ],
        "recommended_workbook_sheets": [
            "mall_income_sheet", "lease_analysis", "dcf_retail",
        ],
        "recommended_pdf_sections": [
            "retail_market_analysis", "income_approach_section", "dcf_section",
        ],
        "warnings": [
            "انعدام المستأجرين الرئيسيين يُضعف موقف المفاوضة.",
        ],
        "legacy_requirement_keys": [
            "mall_requirements", "mall_gla", "mall_occupancy_rate", "mall_anchor_tenants",
        ],
    },

    # ── Warehouse / Logistics ────────────────────────────────────────────────
    "warehouse": {
        "requirements_panel_title_ar": "متطلبات تقييم مخزن / لوجستيات",
        "asset_label_ar": "مستودع / مخزن / منشأة لوجستية",
        "asset_family":   "industrial_logistics",
        "requirement_groups": [
            "G1_basic_data", "G2_logistics_location",
            "G3_utilities_equipment", "G4_lease_income",
            "G5_compliance_documents", "G6_additional", "G7_methods",
        ],
        "required_inputs": [
            "storage_area", "clear_height", "loading_bays",
            "access_roads", "logistics_location", "utilities", "rental_comparables",
        ],
        "required_inputs_labels_ar": {
            "storage_area":       "مساحة التخزين (م²)",
            "clear_height":       "الارتفاع الصافي (م)",
            "loading_bays":       "بوابات الشحن والتفريغ",
            "access_roads":       "طرق الوصول للشاحنات",
            "logistics_location": "جودة الموقع اللوجستي",
            "utilities":          "المرافق المتاحة",
            "rental_comparables": "مقارنات الإيجار",
        },
        "required_evidence": [
            "ownership_deed", "building_permit", "fire_safety_certificate",
            "rental_comparable_evidence",
        ],
        "recommended_methods": [
            "rental_comparison", "cost_approach", "income_approach",
            "logistics_location_adjustment",
        ],
        "recommended_workbook_sheets": [
            "warehouse_rental_comparables", "cost_approach_industrial",
            "logistics_location_matrix",
        ],
        "recommended_pdf_sections": [
            "warehouse_market_analysis", "cost_approach_section",
            "rental_comparison_section",
        ],
        "warnings": [
            "موقع المستودع وقربه من الطرق السريعة يُؤثر على القيمة الإيجارية.",
        ],
        "legacy_requirement_keys": [
            "warehouse_requirements", "warehouse_storage_area", "warehouse_clear_height",
            "warehouse_loading_bays", "warehouse_access_roads",
            "wh_total_area_m2", "wh_office_area", "wh_mezzanine_flag",
            "wh_dock_levelers", "wh_loading_bay_count",
            "wh_truck_turning_radius", "wh_distance_to_highway",
            "wh_distance_to_port", "wh_gps_coordinates",
            "wh_power_capacity_kw", "wh_fire_suppression_system",
            "wh_racking_system", "wh_cold_storage_flag",
            "wh_current_tenant", "wh_monthly_rent",
            "wh_lease_terms", "wh_occupancy_rate",
            "wh_noi", "wh_cap_rate",
            "wh_fire_safety_certificate", "wh_building_permit",
            "wh_zoning_permit",
        ],
        "preservation_pass": True,
        "missing_from_current_after_restore": [],
        "deleted_requirements": [],
    },

    # ── Residential Apartment ────────────────────────────────────────────────
    "residential_apartment": {
        "requirements_panel_title_ar": "متطلبات تقييم وحدة سكنية",
        "asset_family":   "residential_housing",
        "required_inputs": [
            "area_m2", "floor_level", "finishing_quality",
            "occupancy_status", "sales_comparables", "rental_comparables",
        ],
        "required_inputs_labels_ar": {
            "area_m2":            "المساحة (م²)",
            "floor_level":        "رقم الطابق",
            "finishing_quality":  "مستوى التشطيب",
            "occupancy_status":   "حالة الإشغال",
            "sales_comparables":  "مقارنات البيع",
            "rental_comparables": "مقارنات الإيجار",
        },
        "required_evidence": [
            "ownership_deed", "building_permit", "sales_comparable_evidence",
        ],
        "recommended_methods": [
            "sales_comparison", "comparable_adjustment", "cost_approach",
        ],
        "recommended_workbook_sheets": [
            "residential_sales_comparables", "comparable_adjustment_sheet",
        ],
        "recommended_pdf_sections": [
            "residential_market_analysis", "comparable_analysis_section",
        ],
        "warnings": [],
        "legacy_requirement_keys": [
            "residential_unit_requirements", "residential_area_m2",
            "residential_floor_level", "residential_finishing",
        ],
    },

    # ── Office / Administrative ──────────────────────────────────────────────
    "administrative_office": {
        "requirements_panel_title_ar": "متطلبات تقييم مكتب إداري",
        "asset_family":   "office_administrative",
        "required_inputs": [
            "area_m2", "floor_level", "occupancy_status",
            "lease_terms", "monthly_rent", "rental_comparables",
        ],
        "required_inputs_labels_ar": {
            "area_m2":            "المساحة (م²)",
            "floor_level":        "رقم الطابق",
            "occupancy_status":   "حالة الإشغال",
            "lease_terms":        "شروط الإيجار",
            "monthly_rent":       "الإيجار الشهري الحالي",
            "rental_comparables": "مقارنات الإيجار",
        },
        "required_evidence": [
            "ownership_deed", "lease_agreement", "building_permit",
        ],
        "recommended_methods": [
            "rental_comparison", "direct_capitalization", "dcf",
            "income_approach", "hbu",
        ],
        "recommended_workbook_sheets": [
            "office_rental_comparables", "direct_cap_sheet", "dcf_office",
        ],
        "recommended_pdf_sections": [
            "office_market_analysis", "income_approach_section",
        ],
        "warnings": [],
        "legacy_requirement_keys": [
            "office_requirements", "office_area_m2", "office_lease_terms",
        ],
    },

    # ── Cinema / Entertainment Venue ────────────────────────────────────────
    "cinema": {
        "requirements_panel_title_ar": "متطلبات تقييم سينما",
        "asset_label_ar": "سينما / دار عرض سينمائي",
        "asset_family":   "entertainment_assets",
        "required_inputs": [
            "location", "land_area_m2", "building_area_m2",
            "number_of_halls", "total_seats", "year_built",
            "operating_status", "average_occupancy_rate",
            "daily_screenings", "average_ticket_price",
            "ticket_revenue", "food_beverage_revenue",
            "advertising_revenue", "annual_revenue",
            "operating_expenses", "management_contract",
        ],
        "required_inputs_labels_ar": {
            "location":                "موقع السينما",
            "land_area_m2":            "مساحة الأرض (م²)",
            "building_area_m2":        "مساحة المبنى (م²)",
            "number_of_halls":         "عدد القاعات",
            "total_seats":             "عدد المقاعد",
            "year_built":              "سنة الإنشاء",
            "operating_status":        "حالة التشغيل",
            "average_occupancy_rate":  "متوسط الإشغال",
            "daily_screenings":        "عدد العروض اليومية",
            "average_ticket_price":    "متوسط سعر التذكرة",
            "ticket_revenue":          "إيرادات التذاكر",
            "food_beverage_revenue":   "إيرادات الأغذية والمشروبات",
            "advertising_revenue":     "إيرادات الإعلانات والرعاية",
            "annual_revenue":          "الإيرادات السنوية",
            "operating_expenses":      "المصروفات التشغيلية",
            "management_contract":     "عقد الإدارة أو التشغيل",
        },
        "required_evidence": [
            "operating_license", "civil_defense_permit",
            "municipal_licenses", "ownership_deed",
            "architectural_plans", "financial_statements",
        ],
        "recommended_methods": [
            "sales_comparison", "income_approach",
            "direct_capitalization", "dcf", "cost_approach", "hbu", "risk_analysis",
        ],
        "recommended_workbook_sheets": [
            "cinema_operational_data", "income_approach_cinema",
            "dcf_cinema", "comparable_entertainment_sales",
        ],
        "recommended_pdf_sections": [
            "cinema_operational_summary", "income_approach_section",
            "dcf_section", "market_analysis_section",
        ],
        "warnings": [
            "مخاطر تغير الطلب على السينما بسبب المنصات الرقمية يجب تقييمها.",
            "رخصة التشغيل والدفاع المدني إلزامية قبل إصدار القيمة النهائية.",
        ],
        "legacy_requirement_keys": [
            "cinema_halls", "seating_capacity", "annual_revenue",
            "occupancy_rate", "operating_status",
            "maintenance_costs", "operating_contract", "building_permit",
        ],
    },

    # ── Padel Tennis Court ───────────────────────────────────────────────────
    "padel_tennis_court": {
        "requirements_panel_title_ar": "متطلبات تقييم ملعب بادل تنس",
        "asset_label_ar": "ملعب بادل تنس / مركز بادل",
        "asset_family":   "sports_recreation_assets",
        "required_inputs": [
            "location", "land_area_m2", "number_of_courts",
            "court_area_m2", "year_built", "operating_status",
            "finish_level", "utilities_condition", "parking_spaces",
            "court_floor_type", "glass_condition", "lighting_system",
            "changing_rooms", "daily_operating_hours", "booking_system",
            "number_of_staff", "monthly_operating_expenses",
            "annual_maintenance_expenses", "management_contracts",
            "average_booking_rate_per_hour", "available_hours_per_day",
            "occupancy_rate", "daily_revenue", "monthly_revenue",
            "annual_revenue", "academy_revenue", "subscription_revenue",
            "food_beverage_revenue", "net_operating_income",
        ],
        "required_inputs_labels_ar": {
            "location":                      "موقع الأصل",
            "land_area_m2":                  "مساحة الأرض (م²)",
            "number_of_courts":              "عدد ملاعب البادل",
            "court_area_m2":                 "مساحة كل ملعب (م²)",
            "year_built":                    "سنة الإنشاء",
            "operating_status":              "حالة التشغيل",
            "finish_level":                  "مستوى التشطيب",
            "utilities_condition":           "حالة المرافق",
            "parking_spaces":                "مواقف السيارات",
            "court_floor_type":              "نوع أرضية الملعب",
            "glass_condition":               "حالة الزجاج الواقي",
            "lighting_system":               "نظام الإضاءة",
            "changing_rooms":                "غرف تغيير الملابس",
            "daily_operating_hours":         "ساعات التشغيل اليومية",
            "booking_system":                "نظام الحجز الإلكتروني",
            "number_of_staff":               "عدد العاملين",
            "monthly_operating_expenses":    "مصروفات التشغيل الشهرية",
            "annual_maintenance_expenses":   "مصروفات الصيانة السنوية",
            "management_contracts":          "عقود الإدارة",
            "average_booking_rate_per_hour": "متوسط سعر الحجز بالساعة",
            "available_hours_per_day":       "ساعات التشغيل المتاحة يومياً",
            "occupancy_rate":                "معدل الإشغال (%)",
            "daily_revenue":                 "الإيرادات اليومية المتوقعة",
            "monthly_revenue":               "الإيرادات الشهرية",
            "annual_revenue":                "الإيرادات السنوية",
            "academy_revenue":               "إيرادات الأكاديمية والتدريب",
            "subscription_revenue":          "إيرادات الاشتراكات",
            "food_beverage_revenue":         "إيرادات الأغذية والمشروبات",
            "net_operating_income":          "صافي الدخل التشغيلي",
        },
        "required_evidence": [
            "ownership_deed", "operating_license",
            "municipal_licenses", "civil_defense_permit",
            "architectural_plans", "court_photos",
            "management_contracts", "financial_statements_3_years",
            "operating_expense_statement", "historical_booking_data",
        ],
        "recommended_methods": [
            "income_approach", "dcf",
            "cost_approach", "sales_comparison", "hbu",
        ],
        "recommended_workbook_sheets": [
            "padel_court_operational_data", "revenue_projections",
            "income_approach_padel", "dcf_padel",
            "comparable_sports_facilities", "hbu_analysis",
        ],
        "recommended_pdf_sections": [
            "padel_court_summary", "income_approach_section",
            "dcf_section", "market_analysis_section", "risk_section",
        ],
        "warnings": [
            "معدل الإشغال الفعلي يجب التحقق منه من بيانات الحجز التاريخية.",
            "مخاطر الموسمية وتقلبات الطلب يجب أخذها في الحسبان في DCF.",
            "رخصة التشغيل ورخصة الدفاع المدني إلزاميتان قبل إصدار القيمة.",
        ],
        "legacy_requirement_keys": [
            "padel_courts_count", "annual_revenue", "occupancy_rate",
            "playing_fees", "maintenance_costs", "facility_location",
        ],
    },

}

# Aliases — map additional asset_types to the same catalogue entry
_REQUIREMENTS_ALIASES: dict[str, str] = {
    "floating_hotel":    "hotel",
    "serviced_apartments": "hotel",
    "budget_hotel":      "hotel",
    "logistics_facility": "warehouse",
    "cold_storage":      "warehouse",
    "industrial_land":   "urban_land",
    "coastal_land":      "urban_land",
    "desert_land":       "urban_land",
    "residential_villa": "residential_apartment",
    "residential_building": "residential_apartment",
    "residential_compound": "residential_apartment",
    "office_building":   "administrative_office",
    "business_park":     "administrative_office",
    "serviced_office":   "administrative_office",
    "prefabricated_factory": "industrial_factory",
    "coworking_space":   "administrative_office",
    "padel_tennis_courts": "padel_tennis_court",
    "padel_courts":      "padel_tennis_court",
}

# Generic fallback requirements for asset_types not in the catalogue
_GENERIC_REQUIREMENTS: dict = {
    "requirements_panel_title_ar": "متطلبات تقييم الأصل",
    "asset_family":   "",
    "required_inputs": [
        "area_m2", "legal_status", "ownership_deed",
        "location_description", "sales_comparables",
    ],
    "required_inputs_labels_ar": {
        "area_m2":              "المساحة (م²)",
        "legal_status":         "الوضع القانوني",
        "ownership_deed":       "سند الملكية",
        "location_description": "وصف الموقع",
        "sales_comparables":    "مقارنات البيع",
    },
    "required_evidence": ["ownership_deed", "building_permit"],
    "recommended_methods": ["sales_comparison", "comparable_adjustment"],
    "recommended_workbook_sheets": ["general_comparables"],
    "recommended_pdf_sections": ["market_analysis_section"],
    "warnings": [],
    "legacy_requirement_keys": [],
}


def get_asset_specific_requirements(
    asset_type: str = "",
    asset_family: str = "",
    asset_subtype: str = "",
) -> dict:
    """Return asset-specific requirement context derived from asset classification.

    The requirements are advisory — they are NOT mandatory blockers in Phase B.
    They inform: required_inputs, required_evidence, recommended_methods,
    recommended_workbook_sheets, recommended_pdf_sections, taxonomy warnings.

    Legacy requirement keys are preserved in legacy_requirement_keys.
    """
    key = (asset_type or "").strip().lower()
    # Resolve alias
    resolved_key = _REQUIREMENTS_ALIASES.get(key, key)
    base = _ASSET_REQUIREMENTS_CATALOGUE.get(resolved_key)

    if base is None:
        # Fall back to family-level lookup
        fam = (asset_family or "").strip().lower()
        if fam in ("hospitality_leisure", "hospitality_entertainment"):
            base = _ASSET_REQUIREMENTS_CATALOGUE.get("hotel")
        elif fam in ("industrial_logistics", "advanced_industrial_logistics"):
            base = _ASSET_REQUIREMENTS_CATALOGUE.get("industrial_factory")
        elif fam in ("land_plots",):
            base = _ASSET_REQUIREMENTS_CATALOGUE.get("urban_land")
        elif fam in ("commercial_retail",):
            base = _ASSET_REQUIREMENTS_CATALOGUE.get("retail_shop")

    if base is None:
        base = _GENERIC_REQUIREMENTS

    result = dict(base)
    result["asset_type_resolved"]  = resolved_key
    result["asset_type_requested"] = key
    result["asset_family_hint"]    = asset_family
    result["asset_subtype_hint"]   = asset_subtype
    result["is_generic_fallback"]  = (base is _GENERIC_REQUIREMENTS)

    # Computed counts and preservation fields
    norm_keys = result.get("required_inputs", [])
    legacy_keys = result.get("legacy_requirement_keys", [])
    result["normalized_requirement_keys"]       = norm_keys
    result["normalized_requirements_count"]     = len(norm_keys)
    result["legacy_requirements_count"]         = len(legacy_keys)
    result["total_requirements_count"]          = len(set(norm_keys) | set(legacy_keys))
    result["preservation_pass"]                 = result.get("preservation_pass", True)
    result["missing_from_current_after_restore"] = result.get("missing_from_current_after_restore", [])
    result["deleted_requirements"]              = result.get("deleted_requirements", [])
    result["requirement_groups"]                = result.get("requirement_groups", [])
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Feature Capabilities Catalogue — Controls Inventory, Classification &
# Activation Roadmap (Parts J–M)
# ═══════════════════════════════════════════════════════════════════════════════

# Classification states (Part J):
#   active          — real context/data exists and is reflected in reports
#   partially_active — context exists but report reflection is incomplete
#   expert_only     — only in expert draft / expert workbook
#   admin_only      — only in admin/backoffice UI
#   output_registry — only in saved reports/output registry and audit trail
#   not_applicable  — only applies to specific asset types
#   disabled        — implemented visually but not usable yet
#   future_stub     — not implemented; must not affect valuation conclusions

# Effectiveness levels (Part M):
#   0 = UI only, no effect
#   1 = visible but no backend
#   2 = backend/context exists but no report reflection
#   3 = partial report reflection
#   4 = active in reports but not certified
#   5 = fully active and certified-gated

_FEATURE_CAPABILITIES_CATALOGUE: list[dict] = [

    # ── 1. Asset-Specific Requirements ─────────────────────────────────────
    {
        "control_key":              "asset_specific_requirements",
        "label_ar":                 "البيانات التقنية للأصل / متطلبات الأصل المختار",
        "data_testid":              "pro-val-asset-requirements-panel",
        "current_location":         "Section 1.5 of new-request form (frontend), pvr_create() response (backend)",
        "current_behavior":         "Shows asset-specific required inputs/evidence/methods when asset_type is selected. Stored in record and returned in GET detail.",
        "frontend_handler_exists":  True,
        "backend_route_exists":     True,
        "context_key_exists":       True,
        "appears_in_preliminary_pdf":   False,
        "appears_in_expert_draft_pdf":  False,
        "appears_in_expert_workbook":   False,
        "appears_in_certified_pdf":     False,
        "appears_in_final_workbook":    False,
        "affects_certification_gate":   False,
        "state":                    "partially_active",
        "recommended_state":        "active",
        "effectiveness_level":      2,
        "report_reflection_status": "context_exists_no_pdf_reflection",
        "activation_requirements":  [
            "Add asset_specific_requirements section to expert_draft.html",
            "Add asset_requirements summary to preliminary_report.html",
            "Add required_inputs checklist to expert workbook builder",
        ],
        "notes": "Context is computed and stored. UI panel shown. PDF/workbook reflection is missing.",
    },

    # ── 2. Preliminary Weighting Engine / محرك الترجيح المبدئي ─────────────
    {
        "control_key":              "method_weighting_engine",
        "label_ar":                 "محرك الترجيح المبدئي",
        "data_testid":              "professional-weighted-engine-panel",
        "current_location":         "Ordinary valuation section (main advisor workspace, not pro-val form)",
        "current_behavior":         "Shows weighting sliders for ordinary valuation reconciliation. Not connected to professional valuation method_summary.",
        "frontend_handler_exists":  True,
        "backend_route_exists":     True,
        "context_key_exists":       True,
        "appears_in_preliminary_pdf":   False,
        "appears_in_expert_draft_pdf":  True,
        "appears_in_expert_workbook":   True,
        "appears_in_certified_pdf":     True,
        "appears_in_final_workbook":    True,
        "affects_certification_gate":   False,
        "state":                    "expert_only",
        "recommended_state":        "active",
        "effectiveness_level":      4,
        "report_reflection_status": "active_in_expert_and_certified_not_in_preliminary",
        "activation_requirements":  [
            "Wire professional valuation method_summary.reconciliation_value to preliminary_report weighting summary",
            "Ensure method weights appear in preliminary_report.html as advisory summary",
        ],
        "notes": "Reconciliation weights reflected in expert_draft.html (ctx.method_summary), final workbook, certified PDF. Missing from preliminary report.",
    },

    # ── 3. Digital Verification / التحقق الرقمي ──────────────────────────
    {
        "control_key":              "digital_verification",
        "label_ar":                 "التحقق الرقمي / المُحقق الرقمي",
        "data_testid":              "fraud-panel",
        "current_location":         "Ordinary valuation section (id=fraud-panel, openFraudPanel())",
        "current_behavior":         "Fraud/digital verification panel for ordinary valuation. Not surfaced in professional valuation context.",
        "frontend_handler_exists":  True,
        "backend_route_exists":     False,
        "context_key_exists":       False,
        "appears_in_preliminary_pdf":   False,
        "appears_in_expert_draft_pdf":  False,
        "appears_in_expert_workbook":   False,
        "appears_in_certified_pdf":     False,
        "appears_in_final_workbook":    False,
        "affects_certification_gate":   False,
        "state":                    "disabled",
        "recommended_state":        "active",
        "effectiveness_level":      1,
        "report_reflection_status": "not_reflected",
        "activation_requirements":  [
            "Add output_hash and file_version fields to professional valuation certified output record",
            "Add digital_verification section to expert_workbook builder (output hash + gate snapshot)",
            "Add audit_trail section to certified_report.html (file hash, version, certification timestamp)",
            "Add digital_verification row to expert_draft.html governance section",
        ],
        "notes": "Output hash exists in certified_outputs output_record (PVOUT record). Not yet surfaced as a named control in pro-val UI or PDF.",
    },

    # ── 4. Geotechnical Risk / المخاطر الجيوتقنية ─────────────────────────
    {
        "control_key":              "geotechnical_risk",
        "label_ar":                 "المخاطر الجيوتقنية",
        "data_testid":              "geo-panel",
        "current_location":         "Ordinary valuation section (id=geo-panel, openGeoPanel())",
        "current_behavior":         "Geotechnical risk panel for ordinary valuation. Not in professional valuation context.",
        "frontend_handler_exists":  True,
        "backend_route_exists":     False,
        "context_key_exists":       False,
        "appears_in_preliminary_pdf":   False,
        "appears_in_expert_draft_pdf":  False,
        "appears_in_expert_workbook":   False,
        "appears_in_certified_pdf":     False,
        "appears_in_final_workbook":    False,
        "affects_certification_gate":   False,
        "state":                    "not_applicable",
        "recommended_state":        "active",
        "effectiveness_level":      1,
        "report_reflection_status": "not_reflected",
        "activation_requirements":  [
            "Only activate for asset_type in (urban_land, agricultural_land, industrial_factory, warehouse, special_purpose_asset)",
            "Add geotechnical_risk_notes field to professional valuation evidence record",
            "Add risk_section to expert_draft.html and expert workbook",
            "Add geotechnical_risk row to certified_report.html only if evidence-backed",
        ],
        "notes": "Not applicable to hotel/residential. Applicable to land, factory, warehouse. Must have evidence source before appearing in certified output.",
    },

    # ── 5. Asset Portfolio / محفظة الأصول ────────────────────────────────
    {
        "control_key":              "asset_portfolio",
        "label_ar":                 "محفظة الأصول",
        "data_testid":              "pro-val-asset-portfolio",
        "current_location":         "Ordinary valuation section (AssetManager.showDashboard())",
        "current_behavior":         "Single-asset portfolio dashboard for ordinary valuation. No multi-asset model for professional valuation.",
        "frontend_handler_exists":  True,
        "backend_route_exists":     False,
        "context_key_exists":       False,
        "appears_in_preliminary_pdf":   False,
        "appears_in_expert_draft_pdf":  False,
        "appears_in_expert_workbook":   False,
        "appears_in_certified_pdf":     False,
        "appears_in_final_workbook":    False,
        "affects_certification_gate":   False,
        "state":                    "future_stub",
        "recommended_state":        "future_stub",
        "effectiveness_level":      0,
        "report_reflection_status": "not_reflected",
        "activation_requirements":  [
            "Implement multi-asset request model (multiple assets per professional valuation request)",
            "Add portfolio summary sheet to expert and final workbooks",
            "Add asset_allocation model and portfolio reconciliation logic",
            "Add portfolio_summary PDF section to professional_report type only",
        ],
        "notes": "No client-facing report effect until activated. Must not appear in preliminary/certified PDFs until data model exists.",
    },

    # ── 6. Migration Radar / رادار الهجرة ────────────────────────────────
    {
        "control_key":              "migration_radar",
        "label_ar":                 "رادار الهجرة العقارية",
        "data_testid":              "demo-panel",
        "current_location":         "Ordinary valuation section (id=demo-panel, openDemoPanel())",
        "current_behavior":         "Demographic migration radar panel for ordinary valuation. No data model or methodology for professional valuation.",
        "frontend_handler_exists":  True,
        "backend_route_exists":     False,
        "context_key_exists":       False,
        "appears_in_preliminary_pdf":   False,
        "appears_in_expert_draft_pdf":  False,
        "appears_in_expert_workbook":   False,
        "appears_in_certified_pdf":     False,
        "appears_in_final_workbook":    False,
        "affects_certification_gate":   False,
        "state":                    "future_stub",
        "recommended_state":        "future_stub",
        "effectiveness_level":      0,
        "report_reflection_status": "not_reflected",
        "activation_requirements":  [
            "Define demographic/migration data source (no external API without explicit approval)",
            "Define methodology and expert review workflow",
            "Add risk_section integration with report limitation text",
            "Add migration_radar_notes field to evidence record",
        ],
        "notes": "No valuation effect until active. Must not affect valuation conclusions without data source and methodology.",
    },

    # ── 7. Reference Library / فتح المكتبة المرجعية ───────────────────────
    {
        "control_key":              "reference_library",
        "label_ar":                 "فتح المكتبة المرجعية",
        "data_testid":              "pro-val-reference-library",
        "current_location":         "Ordinary valuation section (activateDualComparison())",
        "current_behavior":         "Activates dual comparison view for ordinary valuation. Source registry exists in professional valuation backend via evidence_routes.",
        "frontend_handler_exists":  True,
        "backend_route_exists":     True,
        "context_key_exists":       True,
        "appears_in_preliminary_pdf":   True,
        "appears_in_expert_draft_pdf":  True,
        "appears_in_expert_workbook":   True,
        "appears_in_certified_pdf":     True,
        "appears_in_final_workbook":    True,
        "affects_certification_gate":   True,
        "state":                    "partially_active",
        "recommended_state":        "active",
        "effectiveness_level":      4,
        "report_reflection_status": "source_registry_reflected_dual_comparison_not_linked",
        "activation_requirements":  [
            "Link reference library button in pro-val section (currently only in ordinary val)",
            "Add reference_catalogue_route to professional valuation source tab",
            "Add source approval workflow link to source_section",
            "Ensure references are linked to source_registry records",
        ],
        "notes": "Source registry IS reflected in all professional valuation PDFs via ctx.source_summary. Dual-comparison UI link is missing from pro-val section.",
    },

    # ── 8. Output Registry / سجل التقارير المحفوظة ───────────────────────
    {
        "control_key":              "output_registry",
        "label_ar":                 "سجل التقارير المحفوظة",
        "data_testid":              "pro-val-tab-outputs",
        "current_location":         "Detail workspace outputs tab (pro-val-tab-outputs) + output_registry JSONL",
        "current_behavior":         "Output registry records every certified PDF and final workbook with hash, version, status. Accessible via outputs endpoint.",
        "frontend_handler_exists":  True,
        "backend_route_exists":     True,
        "context_key_exists":       True,
        "appears_in_preliminary_pdf":   False,
        "appears_in_expert_draft_pdf":  True,
        "appears_in_expert_workbook":   True,
        "appears_in_certified_pdf":     True,
        "appears_in_final_workbook":    True,
        "affects_certification_gate":   False,
        "state":                    "active",
        "recommended_state":        "active",
        "effectiveness_level":      5,
        "report_reflection_status": "fully_reflected_in_expert_certified_final",
        "activation_requirements":  [],
        "notes": "Fully implemented. PVOUT records stored, hashed, versioned. output_registry sheet in final workbook. output_hash in certified PDF.",
    },

    # ── 9. Super Intelligence / إستخبارات فائقة ──────────────────────────
    {
        "control_key":              "super_intelligence",
        "label_ar":                 "إستخبارات فائقة",
        "data_testid":              "pro-val-super-intelligence",
        "current_location":         "Ordinary valuation section (group label over fraud/geo/demo/portfolio buttons)",
        "current_behavior":         "Label grouping for advanced controls. No dedicated backend module or methodology.",
        "frontend_handler_exists":  False,
        "backend_route_exists":     False,
        "context_key_exists":       False,
        "appears_in_preliminary_pdf":   False,
        "appears_in_expert_draft_pdf":  False,
        "appears_in_expert_workbook":   False,
        "appears_in_certified_pdf":     False,
        "appears_in_final_workbook":    False,
        "affects_certification_gate":   False,
        "state":                    "future_stub",
        "recommended_state":        "future_stub",
        "effectiveness_level":      0,
        "report_reflection_status": "not_reflected",
        "activation_requirements":  [
            "Define explainable analysis module (no external API without explicit approval)",
            "Add auditable output fields",
            "Add expert approval step",
            "Add intelligence_report_section to professional_report type only",
        ],
        "notes": "No effect on valuation conclusions. Must not be described as active or affecting outputs.",
    },

    # ── 10. Admin Dashboard / لوحة التحكم الإدارية ───────────────────────
    {
        "control_key":              "admin_dashboard",
        "label_ar":                 "لوحة التحكم الإدارية",
        "data_testid":              "pro-val-admin-dashboard",
        "current_location":         "Navigation / backoffice admin section",
        "current_behavior":         "Admin-only backoffice panel. Not visible in client-facing PDFs.",
        "frontend_handler_exists":  True,
        "backend_route_exists":     True,
        "context_key_exists":       False,
        "appears_in_preliminary_pdf":   False,
        "appears_in_expert_draft_pdf":  False,
        "appears_in_expert_workbook":   False,
        "appears_in_certified_pdf":     False,
        "appears_in_final_workbook":    False,
        "affects_certification_gate":   False,
        "state":                    "admin_only",
        "recommended_state":        "admin_only",
        "effectiveness_level":      4,
        "report_reflection_status": "admin_only_no_client_effect",
        "activation_requirements":  [],
        "notes": "Admin dashboard is admin_only. No client-facing report effect. Internal audit metadata only.",
    },

    # ── 11. Advanced Reviews (HBU, Legal, ESG, SWOT) ──────────────────────
    {
        "control_key":              "advanced_reviews",
        "label_ar":                 "المراجعات المتقدمة — HBU، الفحص القانوني، ESG، SWOT",
        "data_testid":              "pro-val-tab-hbu",
        "current_location":         "Detail workspace tabs: pro-val-tab-hbu, pro-val-tab-legal, pro-val-tab-esg, pro-val-tab-swot",
        "current_behavior":         "Four advanced review steps. Completion tracked in ctx.advanced_reviews. Gates checked before certification.",
        "frontend_handler_exists":  True,
        "backend_route_exists":     True,
        "context_key_exists":       True,
        "appears_in_preliminary_pdf":   False,
        "appears_in_expert_draft_pdf":  True,
        "appears_in_expert_workbook":   True,
        "appears_in_certified_pdf":     True,
        "appears_in_final_workbook":    True,
        "affects_certification_gate":   True,
        "state":                    "active",
        "recommended_state":        "active",
        "effectiveness_level":      5,
        "report_reflection_status": "fully_reflected_in_expert_certified_final",
        "activation_requirements":  [],
        "notes": "Fully implemented. HBU/legal/ESG/SWOT gated. Shown in expert_draft section 6 and governance section.",
    },

    # ── 12. Certification Gate ─────────────────────────────────────────────
    {
        "control_key":              "certification_gate",
        "label_ar":                 "بوابة الاعتماد النهائي",
        "data_testid":              "pro-val-tab-signature",
        "current_location":         "Phase G: peer-review, signature, final certification gate",
        "current_behavior":         "Multi-gate certification: evidence, comparables, methods, reconciliation, advanced reviews, peer review, signature. certification_ready only becomes True after all gates pass.",
        "frontend_handler_exists":  True,
        "backend_route_exists":     True,
        "context_key_exists":       True,
        "appears_in_preliminary_pdf":   False,
        "appears_in_expert_draft_pdf":  True,
        "appears_in_certified_pdf":     True,
        "appears_in_final_workbook":    True,
        "appears_in_expert_workbook":   True,
        "affects_certification_gate":   True,
        "state":                    "active",
        "recommended_state":        "active",
        "effectiveness_level":      5,
        "report_reflection_status": "fully_reflected_in_expert_certified_final",
        "activation_requirements":  [],
        "notes": "Fully implemented. certification_ready=False until all gates pass. Blockers list in expert_draft section 8.",
    },
]


def get_feature_capabilities_context(
    asset_type: str = "",
    asset_family: str = "",
    report_type: str = "professional_report",
) -> dict:
    """
    Return the full feature capabilities inventory for a professional valuation request.

    Returns:
      controls:              list of all control records with state, effectiveness level,
                             report reflection status, and activation requirements
      active_controls:       list of control_keys that are active
      partially_active_controls: list of partially active control_keys
      disabled_controls:     list of disabled control_keys
      future_stub_controls:  list of future_stub control_keys
      admin_only_controls:   list of admin_only control_keys
      expert_only_controls:  list of expert_only control_keys
      not_applicable_controls: list of not_applicable control_keys for this asset
      report_reflection_matrix: what each control shows in which report type
      control_activation_roadmap: activation_requirements for non-active controls
      advisory_note:         Arabic note about inactive controls
    """
    at = (asset_type or "").lower().strip()

    # Determine not_applicable controls based on asset_type
    _geo_applicable_types = frozenset({
        "urban_land", "agricultural_land", "industrial_land", "coastal_land", "desert_land",
        "industrial_factory", "warehouse", "logistics_facility", "prefabricated_factory",
        "special_purpose_asset", "مصنع", "أرض فضاء", "أرض زراعية",
    })
    geo_applicable = at in _geo_applicable_types

    controls: list[dict] = []
    active: list[str] = []
    partially_active: list[str] = []
    disabled: list[str] = []
    future_stubs: list[str] = []
    admin_only: list[str] = []
    expert_only: list[str] = []
    not_applicable: list[str] = []

    for ctrl in _FEATURE_CAPABILITIES_CATALOGUE:
        ck = ctrl["control_key"]
        state = ctrl["state"]

        # Override geotechnical risk state based on asset type
        if ck == "geotechnical_risk":
            if not geo_applicable:
                state = "not_applicable"
            else:
                state = "partially_active"

        rec = dict(ctrl)
        rec["state"] = state

        if state == "active":
            active.append(ck)
        elif state == "partially_active":
            partially_active.append(ck)
        elif state == "disabled":
            disabled.append(ck)
        elif state == "future_stub":
            future_stubs.append(ck)
        elif state == "admin_only":
            admin_only.append(ck)
        elif state == "expert_only":
            expert_only.append(ck)
        elif state == "not_applicable":
            not_applicable.append(ck)

        controls.append(rec)

    # Build report_reflection_matrix
    report_reflection_matrix: dict = {}
    for ctrl in controls:
        ck = ctrl["control_key"]
        report_reflection_matrix[ck] = {
            "label_ar":                     ctrl["label_ar"],
            "state":                        ctrl["state"],
            "effectiveness_level":          ctrl["effectiveness_level"],
            "appears_in_preliminary_pdf":   ctrl["appears_in_preliminary_pdf"],
            "appears_in_expert_draft_pdf":  ctrl["appears_in_expert_draft_pdf"],
            "appears_in_expert_workbook":   ctrl["appears_in_expert_workbook"],
            "appears_in_certified_pdf":     ctrl["appears_in_certified_pdf"],
            "appears_in_final_workbook":    ctrl["appears_in_final_workbook"],
            "affects_certification_gate":   ctrl["affects_certification_gate"],
            "report_reflection_status":     ctrl["report_reflection_status"],
        }

    # Build control_activation_roadmap for non-active controls
    control_activation_roadmap: list[dict] = []
    for ctrl in controls:
        if ctrl["state"] not in ("active",) and ctrl["activation_requirements"]:
            control_activation_roadmap.append({
                "control_key":              ctrl["control_key"],
                "label_ar":                 ctrl["label_ar"],
                "current_state":            ctrl["state"],
                "current_effectiveness_level": ctrl["effectiveness_level"],
                "why_not_active":           ctrl.get("notes", ""),
                "activation_requirements":  ctrl["activation_requirements"],
                "recommended_state":        ctrl["recommended_state"],
                "expected_report_impact_after_activation": ctrl["report_reflection_status"],
            })

    return {
        "controls":                  controls,
        "active_controls":           active,
        "partially_active_controls": partially_active,
        "disabled_controls":         disabled,
        "future_stub_controls":      future_stubs,
        "admin_only_controls":       admin_only,
        "expert_only_controls":      expert_only,
        "not_applicable_controls":   not_applicable,
        "report_reflection_matrix":  report_reflection_matrix,
        "control_activation_roadmap": control_activation_roadmap,
        "advisory_note": (
            "الضوابط غير المفعّلة لا تؤثر على استنتاجات التقييم. "
            "الضوابط المصنفة future_stub تعني عدم وجود تأثير على التقارير. "
            "الضوابط المصنفة partially_active تعني وجود سياق في الباك إند "
            "لكن الانعكاس على التقارير غير مكتمل بعد."
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PVDSR — Dynamic Special Asset Requirements Registries (Section 2 Five-Group)
# ═══════════════════════════════════════════════════════════════════════════════

_UNCOMMON_ASSET_FAMILY_REGISTRY: dict = {
    "sports_recreation_assets":     {"key": "sports_recreation_assets", "label_ar": "الأصول الرياضية والترفيهية", "label_en": "Sports & Recreation Assets", "advisory_only": True, "active": True},
    "entertainment_assets":         {"key": "entertainment_assets",      "label_ar": "أصول الترفيه",                  "label_en": "Entertainment Assets",      "advisory_only": True, "active": True},
    "healthcare_assets":            {"key": "healthcare_assets",         "label_ar": "الأصول الصحية والطبية",         "label_en": "Healthcare Assets",         "advisory_only": True, "active": True},
    "education_assets":             {"key": "education_assets",          "label_ar": "الأصول التعليمية",              "label_en": "Education Assets",          "advisory_only": True, "active": True},
    "industrial_special_assets":    {"key": "industrial_special_assets", "label_ar": "أصول صناعية متخصصة",           "label_en": "Industrial Special Assets", "advisory_only": True, "active": True},
    "logistics_special_assets":     {"key": "logistics_special_assets",  "label_ar": "أصول لوجستية متخصصة",          "label_en": "Logistics Special Assets",  "advisory_only": True, "active": True},
    "hospitality_special_assets":   {"key": "hospitality_special_assets","label_ar": "أصول سياحية وفندقية متخصصة",   "label_en": "Hospitality Special Assets","advisory_only": True, "active": True},
    "cultural_heritage_assets":     {"key": "cultural_heritage_assets",  "label_ar": "الأصول الثقافية والتراثية",    "label_en": "Cultural Heritage Assets",  "advisory_only": True, "active": True},
    "agricultural_special_assets":  {"key": "agricultural_special_assets","label_ar": "أصول زراعية متخصصة",          "label_en": "Agricultural Special Assets","advisory_only": True, "active": True},
    "mining_extractives_assets":    {"key": "mining_extractives_assets", "label_ar": "الأصول التعدينية والاستخراجية","label_en": "Mining & Extractive Assets","advisory_only": True, "active": True},
    "media_production_assets":      {"key": "media_production_assets",   "label_ar": "الأصول الإعلامية والإنتاجية", "label_en": "Media & Production Assets", "advisory_only": True, "active": True},
    "special_purpose_assets":       {"key": "special_purpose_assets",    "label_ar": "الأصول المتخصصة",              "label_en": "Special Purpose Assets",    "advisory_only": True, "active": True},
}

_UNCOMMON_ASSET_SUBTYPE_REGISTRY: dict = {
    # sports_recreation_assets
    "padel_tennis_court":     {"key": "padel_tennis_court",     "family_key": "sports_recreation_assets", "label_ar": "ملعب بادل تنس",            "label_en": "Padel Tennis Court",        "legacy_aliases": ["padel_tennis_courts", "padel_courts"], "requirements_key": "padel_tennis_court",     "advisory_only": True},
    "football_court":         {"key": "football_court",         "family_key": "sports_recreation_assets", "label_ar": "ملعب كرة قدم",              "label_en": "Football Court",            "legacy_aliases": [],                                      "requirements_key": "football_court",         "advisory_only": True},
    "sports_club":            {"key": "sports_club",            "family_key": "sports_recreation_assets", "label_ar": "نادي رياضي",               "label_en": "Sports Club",               "legacy_aliases": [],                                      "requirements_key": "sports_club",            "advisory_only": True},
    "stadium":                {"key": "stadium",                "family_key": "sports_recreation_assets", "label_ar": "استاد",                     "label_en": "Stadium",                   "legacy_aliases": [],                                      "requirements_key": "stadium",                "advisory_only": True},
    "gym_fitness_center":     {"key": "gym_fitness_center",     "family_key": "sports_recreation_assets", "label_ar": "صالة رياضية / جيم",         "label_en": "Gym / Fitness Center",      "legacy_aliases": [],                                      "requirements_key": "gym_fitness_center",     "advisory_only": True},
    "swimming_pool_facility": {"key": "swimming_pool_facility", "family_key": "sports_recreation_assets", "label_ar": "حمام سباحة / منشأة سباحة", "label_en": "Swimming Pool Facility",    "legacy_aliases": [],                                      "requirements_key": "swimming_pool_facility", "advisory_only": True},
    "amusement_park":         {"key": "amusement_park",         "family_key": "sports_recreation_assets", "label_ar": "مدينة ملاهي",              "label_en": "Amusement Park",            "legacy_aliases": ["theme_park"],                          "requirements_key": "amusement_park",         "advisory_only": True},
    "recreation_center":      {"key": "recreation_center",      "family_key": "sports_recreation_assets", "label_ar": "مركز ترفيهي رياضي",         "label_en": "Recreation Center",         "legacy_aliases": [],                                      "requirements_key": "recreation_center",      "advisory_only": True},
    # entertainment_assets
    "cinema":                 {"key": "cinema",                 "family_key": "entertainment_assets",     "label_ar": "سينما",                     "label_en": "Cinema",                    "legacy_aliases": [],                                      "requirements_key": "cinema",                 "advisory_only": True},
    "theater":                {"key": "theater",                "family_key": "entertainment_assets",     "label_ar": "مسرح",                      "label_en": "Theater",                   "legacy_aliases": [],                                      "requirements_key": "theater",                "advisory_only": True},
    "event_hall":             {"key": "event_hall",             "family_key": "entertainment_assets",     "label_ar": "قاعة فعاليات",              "label_en": "Event Hall",                "legacy_aliases": [],                                      "requirements_key": "event_hall",             "advisory_only": True},
    "amusement_center":       {"key": "amusement_center",       "family_key": "entertainment_assets",     "label_ar": "مركز ترفيهي",              "label_en": "Amusement Center",          "legacy_aliases": [],                                      "requirements_key": "amusement_center",       "advisory_only": True},
    "conference_center":      {"key": "conference_center",      "family_key": "entertainment_assets",     "label_ar": "مركز مؤتمرات",              "label_en": "Conference Center",         "legacy_aliases": [],                                      "requirements_key": "conference_center",      "advisory_only": True},
    # healthcare_assets
    "general_hospital":       {"key": "general_hospital",       "family_key": "healthcare_assets",        "label_ar": "مستشفى عام",               "label_en": "General Hospital",          "legacy_aliases": ["hospital", "مستشفى"],                  "requirements_key": "general_hospital",       "advisory_only": True},
    "clinic_complex":         {"key": "clinic_complex",         "family_key": "healthcare_assets",        "label_ar": "مجمع عيادات",              "label_en": "Clinic Complex",            "legacy_aliases": [],                                      "requirements_key": "clinic_complex",         "advisory_only": True},
    "medical_center":         {"key": "medical_center",         "family_key": "healthcare_assets",        "label_ar": "مركز طبي",                  "label_en": "Medical Center",            "legacy_aliases": [],                                      "requirements_key": "medical_center",         "advisory_only": True},
    "specialized_medical_facility": {"key": "specialized_medical_facility", "family_key": "healthcare_assets", "label_ar": "منشأة طبية متخصصة", "label_en": "Specialized Medical Facility", "legacy_aliases": [], "requirements_key": "specialized_medical_facility", "advisory_only": True},
    # education_assets
    "school_campus":          {"key": "school_campus",          "family_key": "education_assets",         "label_ar": "مدرسة",                     "label_en": "School Campus",             "legacy_aliases": ["school", "مدرسة"],                     "requirements_key": "school_campus",          "advisory_only": True},
    "university_campus":      {"key": "university_campus",      "family_key": "education_assets",         "label_ar": "حرم جامعي",                "label_en": "University Campus",         "legacy_aliases": [],                                      "requirements_key": "university_campus",      "advisory_only": True},
    "training_center_edu":    {"key": "training_center_edu",    "family_key": "education_assets",         "label_ar": "مركز تدريب",                "label_en": "Training Center",           "legacy_aliases": ["training_center"],                     "requirements_key": "training_center_edu",    "advisory_only": True},
    "nursery_education_property": {"key": "nursery_education_property", "family_key": "education_assets", "label_ar": "حضانة / منشأة تعليم مبكر", "label_en": "Nursery / Early Education", "legacy_aliases": [], "requirements_key": "nursery_education_property", "advisory_only": True},
    # cultural_heritage_assets
    "distinguished_architectural_heritage": {"key": "distinguished_architectural_heritage", "family_key": "cultural_heritage_assets", "label_ar": "عقار ذو تراث معماري متميز", "label_en": "Distinguished Architectural Heritage", "legacy_aliases": ["heritage", "heritage_property", "listed_heritage_building"], "requirements_key": "distinguished_architectural_heritage", "advisory_only": True},
    "listed_heritage_building": {"key": "listed_heritage_building", "family_key": "cultural_heritage_assets", "label_ar": "مبنى تراثي مسجل", "label_en": "Listed Heritage Building", "legacy_aliases": ["heritage_listed"], "requirements_key": "distinguished_architectural_heritage", "advisory_only": True},
    # mining_extractives_assets
    "mine_gold":              {"key": "mine_gold",              "family_key": "mining_extractives_assets", "label_ar": "منجم ذهب",                 "label_en": "Gold Mine",                 "legacy_aliases": [],                                      "requirements_key": "mine_gold",              "advisory_only": True},
    "mine_phosphate":         {"key": "mine_phosphate",         "family_key": "mining_extractives_assets", "label_ar": "منجم فوسفات",              "label_en": "Phosphate Mine",            "legacy_aliases": [],                                      "requirements_key": "mine_phosphate",         "advisory_only": True},
    "quarry":                 {"key": "quarry",                 "family_key": "mining_extractives_assets", "label_ar": "محجر",                      "label_en": "Quarry",                    "legacy_aliases": [],                                      "requirements_key": "quarry",                 "advisory_only": True},
    # media_production_assets
    "filming_studio":         {"key": "filming_studio",         "family_key": "media_production_assets",  "label_ar": "استوديو تصوير",            "label_en": "Filming Studio",            "legacy_aliases": [],                                      "requirements_key": "filming_studio",         "advisory_only": True},
    "media_center":           {"key": "media_center",           "family_key": "media_production_assets",  "label_ar": "مركز إعلامي",              "label_en": "Media Center",              "legacy_aliases": [],                                      "requirements_key": "media_center",           "advisory_only": True},
}

_REQUIREMENT_GROUP_REGISTRY: dict = {
    "descriptive": {"key": "descriptive", "label_ar": "البيانات الوصفية والتعريفية", "label_en": "Descriptive & Identification Data", "order": 1},
    "physical":    {"key": "physical",    "label_ar": "البيانات الفيزيائية والإنشائية", "label_en": "Physical & Structural Data",       "order": 2},
    "operational": {"key": "operational", "label_ar": "البيانات التشغيلية والإيرادات", "label_en": "Operational & Revenue Data",        "order": 3},
    "legal":       {"key": "legal",       "label_ar": "البيانات القانونية والمستندات", "label_en": "Legal & Documentation Data",        "order": 4},
    "market":      {"key": "market",      "label_ar": "البيانات السوقية والمنافسة",    "label_en": "Market & Competitive Data",         "order": 5},
}

_FIELD_TYPE_REGISTRY: dict = {
    "text":           {"key": "text",           "label_ar": "نص قصير",                 "label_en": "Text",            "icon": "T"},
    "textarea":       {"key": "textarea",       "label_ar": "نص طويل",                 "label_en": "Textarea",        "icon": "¶"},
    "number":         {"key": "number",         "label_ar": "رقمي",                    "label_en": "Number",          "icon": "#"},
    "currency":       {"key": "currency",       "label_ar": "عملة",                    "label_en": "Currency",        "icon": "EGP"},
    "percent":        {"key": "percent",        "label_ar": "نسبة مئوية",              "label_en": "Percent",         "icon": "%"},
    "date":           {"key": "date",           "label_ar": "تاريخ",                   "label_en": "Date",            "icon": "date"},
    "select":         {"key": "select",         "label_ar": "قائمة اختيار",            "label_en": "Select",          "icon": "v"},
    "multi_select":   {"key": "multi_select",   "label_ar": "اختيار متعدد",            "label_en": "Multi-Select",    "icon": "multi"},
    "checkbox_group": {"key": "checkbox_group", "label_ar": "مجموعة مربعات اختيار",   "label_en": "Checkbox Group",  "icon": "chk"},
    "file":           {"key": "file",           "label_ar": "ملف / مستند",             "label_en": "File Upload",     "icon": "file"},
    "coordinate":     {"key": "coordinate",     "label_ar": "إحداثيات",                "label_en": "Coordinate",      "icon": "coord"},
    "map_placeholder":{"key": "map_placeholder","label_ar": "خريطة (مستقبلي)",         "label_en": "Map Placeholder", "icon": "map"},
    "note":           {"key": "note",           "label_ar": "ملاحظة",                  "label_en": "Note",            "icon": "i"},
}

_METHODOLOGY_GUIDANCE_REGISTRY: dict = {
    "padel_tennis_court": {
        "asset_key": "padel_tennis_court", "advisory_only": True,
        "recommended_methods": ["income_approach", "sales_comparison", "cost_approach"],
        "preliminary_method_weights": {"income_approach_dcf": 60, "sales_comparison": 25, "cost_approach": 15},
        "key_value_drivers": ["معدل الإشغال", "الإيرادات السنوية", "عدد الملاعب", "الموقع", "نوع أرضية الملعب"],
        "required_inputs_for_calculation": ["annual_gross_revenue", "annual_operating_expenses", "padel_courts_count", "average_hourly_booking_price", "utilization_rate_percent"],
    },
    "cinema": {
        "asset_key": "cinema", "advisory_only": True,
        "recommended_methods": ["income_approach", "sales_comparison", "cost_approach"],
        "preliminary_method_weights": {"income_approach_dcf": 55, "sales_comparison": 25, "cost_approach": 20},
        "key_value_drivers": ["معدل الإشغال", "إيرادات التذاكر", "عدد القاعات", "الموقع", "المنافسة"],
        "required_inputs_for_calculation": ["halls_count", "seats_count", "average_occupancy_percent", "average_ticket_price", "annual_gross_revenue"],
    },
    "general_hospital": {
        "asset_key": "general_hospital", "advisory_only": True,
        "recommended_methods": ["cost_approach", "income_approach"],
        "preliminary_method_weights": {"cost_approach": 50, "income_approach": 50},
        "key_value_drivers": ["عدد الأسرة", "معدل الإشغال", "الإيرادات السنوية", "حالة الترخيص", "التجهيزات الطبية"],
        "required_inputs_for_calculation": ["beds_count", "annual_occupancy_percent", "annual_gross_revenue", "annual_operating_expenses"],
    },
    "school_campus": {
        "asset_key": "school_campus", "advisory_only": True,
        "recommended_methods": ["sales_comparison", "income_approach"],
        "preliminary_method_weights": {"sales_comparison": 50, "income_approach": 50},
        "key_value_drivers": ["عدد الطلاب", "نسبة الإشغال", "رسوم الدراسة", "الموقع", "الترخيص التعليمي"],
        "required_inputs_for_calculation": ["enrolled_students_count", "annual_tuition_fee", "occupancy_ratio_percent", "annual_gross_revenue"],
    },
    "distinguished_architectural_heritage": {
        "asset_key": "distinguished_architectural_heritage", "advisory_only": True,
        "recommended_methods": ["cost_approach", "sales_comparison", "income_approach"],
        "preliminary_method_weights": {"cost_approach_restoration": 70, "sales_comparison": 20, "income_approach": 10},
        "key_value_drivers": ["تصنيف التراث", "تكلفة الترميم", "حالة المبنى", "القيود القانونية", "إمكانية إعادة التوظيف"],
        "required_inputs_for_calculation": ["heritage_classification", "restoration_needs", "building_condition", "development_restrictions"],
    },
}

_ASSET_REPORT_WORKBOOK_CONTEXT_REGISTRY: dict = {
    "padel_tennis_court": {
        "asset_key": "padel_tennis_court", "advisory_only": True,
        "required_pdf_sections": ["وصف الأصل", "البيانات الفيزيائية", "البيانات التشغيلية", "الإيرادات", "المستندات", "السوق والمنافسة", "المنهجية المقترحة", "المخاطر"],
        "required_workbook_sheets": ["inputs", "physical_data", "operational_data", "revenue", "expenses", "documents_checklist", "market_competition", "methodology_guidance", "risks"],
        "missing_report_inputs": [],
    },
    "cinema": {
        "asset_key": "cinema", "advisory_only": True,
        "required_pdf_sections": ["وصف الأصل", "البيانات الفيزيائية", "البيانات التشغيلية", "الإيرادات", "المستندات", "السوق والمنافسة", "المنهجية المقترحة"],
        "required_workbook_sheets": ["inputs", "physical_data", "operational_data", "revenue", "expenses", "documents_checklist", "market_competition", "methodology_guidance"],
        "missing_report_inputs": [],
    },
    "general_hospital": {
        "asset_key": "general_hospital", "advisory_only": True,
        "required_pdf_sections": ["وصف الأصل", "البيانات الفيزيائية", "البيانات التشغيلية", "الإيرادات", "المستندات", "السوق والمنافسة", "المنهجية المقترحة", "المخاطر"],
        "required_workbook_sheets": ["inputs", "physical_data", "operational_data", "revenue", "expenses", "documents_checklist", "market_competition", "methodology_guidance", "risks"],
        "missing_report_inputs": [],
    },
    "school_campus": {
        "asset_key": "school_campus", "advisory_only": True,
        "required_pdf_sections": ["وصف الأصل", "البيانات الفيزيائية", "البيانات التشغيلية", "الإيرادات", "المستندات", "السوق والمنافسة", "المنهجية المقترحة"],
        "required_workbook_sheets": ["inputs", "physical_data", "operational_data", "revenue", "expenses", "documents_checklist", "market_competition", "methodology_guidance"],
        "missing_report_inputs": [],
    },
    "distinguished_architectural_heritage": {
        "asset_key": "distinguished_architectural_heritage", "advisory_only": True,
        "required_pdf_sections": ["وصف الأصل", "البيانات الفيزيائية", "البيانات التشغيلية", "المستندات", "السوق", "المنهجية المقترحة"],
        "required_workbook_sheets": ["inputs", "physical_data", "restoration_costs", "documents_checklist", "market_competition", "methodology_guidance"],
        "missing_report_inputs": [],
    },
}

_FUTURE_INTEGRATIONS_REGISTRY: dict = {
    "interactive_map":                  {"key": "interactive_map",                  "state": "future_stub", "active": False, "label_ar": "خريطة تفاعلية",                "reason": "External map integration is not enabled in this phase."},
    "external_market_database":         {"key": "external_market_database",         "state": "future_stub", "active": False, "label_ar": "قاعدة بيانات السوق الخارجية", "reason": "External market database search is not enabled in this phase."},
    "government_api_integration":       {"key": "government_api_integration",       "state": "future_stub", "active": False, "label_ar": "API حكومي",                    "reason": "Government APIs are not enabled in this phase."},
    "auto_completion":                  {"key": "auto_completion",                  "state": "future_stub", "active": False, "label_ar": "إكمال تلقائي",                 "reason": "Auto-completion from external data is not enabled in this phase."},
    "admin_panel_field_builder":        {"key": "admin_panel_field_builder",        "state": "future_stub", "active": False, "label_ar": "لوحة إدارة بناء الحقول",       "reason": "Admin panel field builder is deferred."},
    "retrospective_requirements_versioning": {"key": "retrospective_requirements_versioning", "state": "future_stub", "active": False, "label_ar": "تحكم بإصدار المتطلبات", "reason": "Versioning by valuation date is deferred."},
}

_LEGACY_ASSET_ALIAS_REGISTRY: dict = {
    "padel_tennis_courts":  {"canonical_key": "padel_tennis_court",                 "family_key": "sports_recreation_assets"},
    "padel_courts":         {"canonical_key": "padel_tennis_court",                 "family_key": "sports_recreation_assets"},
    "hospital":             {"canonical_key": "general_hospital",                   "family_key": "healthcare_assets"},
    "مستشفى":              {"canonical_key": "general_hospital",                   "family_key": "healthcare_assets"},
    "school":               {"canonical_key": "school_campus",                      "family_key": "education_assets"},
    "مدرسة":               {"canonical_key": "school_campus",                      "family_key": "education_assets"},
    "heritage":             {"canonical_key": "distinguished_architectural_heritage","family_key": "cultural_heritage_assets"},
    "heritage_property":    {"canonical_key": "distinguished_architectural_heritage","family_key": "cultural_heritage_assets"},
    "listed_heritage_building": {"canonical_key": "distinguished_architectural_heritage", "family_key": "cultural_heritage_assets"},
    "theme_park":           {"canonical_key": "amusement_park",                    "family_key": "sports_recreation_assets"},
}

_DYNAMIC_REQUIREMENT_FIELD_REGISTRY: dict = {
    # Base descriptive fields (shared)
    "facility_trade_name":                {"key": "facility_trade_name",               "group": "descriptive", "field_type": "text",           "label_ar": "الاسم التجاري للمنشأة",             "required": False, "source": "normalized"},
    "geographic_location_description":    {"key": "geographic_location_description",   "group": "descriptive", "field_type": "textarea",       "label_ar": "وصف الموقع الجغرافي",               "required": True,  "source": "normalized"},
    "coordinates_manual":                 {"key": "coordinates_manual",                "group": "descriptive", "field_type": "coordinate",     "label_ar": "الإحداثيات اليدوية",                "required": False, "source": "normalized"},
    "map_placeholder":                    {"key": "map_placeholder",                   "group": "descriptive", "field_type": "map_placeholder","label_ar": "خريطة الموقع",                      "required": False, "source": "normalized"},
    "total_land_area_sqm":                {"key": "total_land_area_sqm",               "group": "descriptive", "field_type": "number",         "label_ar": "المساحة الكلية للأرض (م²)",         "required": True,  "source": "normalized", "unit": "م²"},
    # Base physical fields
    "construction_type":                  {"key": "construction_type",                 "group": "physical",    "field_type": "select",         "label_ar": "نوع الإنشاء",                       "required": False, "source": "normalized"},
    "building_age_years":                 {"key": "building_age_years",                "group": "physical",    "field_type": "number",         "label_ar": "عمر المبنى (سنة)",                  "required": False, "source": "normalized", "unit": "سنة"},
    "structural_condition":               {"key": "structural_condition",              "group": "physical",    "field_type": "select",         "label_ar": "الحالة الإنشائية",                  "required": True,  "source": "normalized"},
    "built_up_area_sqm":                  {"key": "built_up_area_sqm",                 "group": "physical",    "field_type": "number",         "label_ar": "مساحة المباني (م²)",                "required": True,  "source": "normalized", "unit": "م²"},
    # Padel-specific
    "padel_courts_count":                 {"key": "padel_courts_count",                "group": "physical",    "field_type": "number",         "label_ar": "عدد ملاعب البادل",                  "required": True,  "source": "normalized", "asset_key": "padel_tennis_court"},
    "average_hourly_booking_price":       {"key": "average_hourly_booking_price",      "group": "operational", "field_type": "currency",       "label_ar": "متوسط سعر الحجز بالساعة",           "required": True,  "source": "normalized", "asset_key": "padel_tennis_court"},
    "utilization_rate_percent":           {"key": "utilization_rate_percent",          "group": "operational", "field_type": "percent",        "label_ar": "معدل الإشغال (%)",                  "required": True,  "source": "normalized", "asset_key": "padel_tennis_court"},
    # Cinema-specific
    "halls_count":                        {"key": "halls_count",                       "group": "physical",    "field_type": "number",         "label_ar": "عدد القاعات",                       "required": True,  "source": "normalized", "asset_key": "cinema"},
    "seats_count":                        {"key": "seats_count",                       "group": "physical",    "field_type": "number",         "label_ar": "عدد المقاعد",                       "required": True,  "source": "normalized", "asset_key": "cinema"},
    "average_ticket_price":               {"key": "average_ticket_price",              "group": "operational", "field_type": "currency",       "label_ar": "متوسط سعر التذكرة",                 "required": True,  "source": "normalized", "asset_key": "cinema"},
    # Hospital-specific
    "beds_count":                         {"key": "beds_count",                        "group": "physical",    "field_type": "number",         "label_ar": "عدد الأسرة",                        "required": True,  "source": "normalized", "asset_key": "general_hospital"},
    "operating_rooms_count":              {"key": "operating_rooms_count",             "group": "physical",    "field_type": "number",         "label_ar": "عدد غرف العمليات",                  "required": False, "source": "normalized", "asset_key": "general_hospital"},
    # School-specific
    "classrooms_count":                   {"key": "classrooms_count",                  "group": "physical",    "field_type": "number",         "label_ar": "عدد الفصول",                        "required": True,  "source": "normalized", "asset_key": "school_campus"},
    "students_capacity":                  {"key": "students_capacity",                 "group": "physical",    "field_type": "number",         "label_ar": "الطاقة الاستيعابية للطلاب",         "required": False, "source": "normalized", "asset_key": "school_campus"},
    # Heritage-specific
    "heritage_classification":            {"key": "heritage_classification",           "group": "descriptive", "field_type": "select",         "label_ar": "تصنيف التراث المعماري",             "required": True,  "source": "normalized", "asset_key": "distinguished_architectural_heritage"},
    # Common operational
    "annual_gross_revenue":               {"key": "annual_gross_revenue",              "group": "operational", "field_type": "currency",       "label_ar": "الإيرادات السنوية الإجمالية",       "required": True,  "source": "normalized"},
    "annual_occupancy_percent":           {"key": "annual_occupancy_percent",          "group": "operational", "field_type": "percent",        "label_ar": "متوسط الإشغال / الاستخدام السنوي", "required": False, "source": "normalized"},
    # Legal / file
    "title_deed_or_lease_contract":       {"key": "title_deed_or_lease_contract",      "group": "legal",       "field_type": "file",           "label_ar": "سند الملكية / عقد الإيجار",         "required": True,  "source": "normalized"},
    "operating_license_file":             {"key": "operating_license_file",            "group": "legal",       "field_type": "file",           "label_ar": "رخصة التشغيل",                      "required": True,  "source": "normalized"},
    "audited_financials_file":            {"key": "audited_financials_file",           "group": "legal",       "field_type": "file",           "label_ar": "القوائم المالية المدققة",            "required": True,  "source": "normalized"},
}

_ASSET_SPECIFIC_REQUIREMENT_REGISTRY: dict = {
    "padel_tennis_court": {
        "asset_key": "padel_tennis_court", "advisory_only": True, "preservation_pass": True,
        "five_groups": ["descriptive", "physical", "operational", "legal", "market"],
        "total_requirements_count": 40, "legacy_requirements_count": 6, "normalized_requirements_count": 34,
        "missing_legacy_requirements_after_restore": [],
        "field_types_used": ["text", "textarea", "number", "currency", "percent", "select", "checkbox_group", "file", "coordinate", "map_placeholder"],
    },
    "cinema": {
        "asset_key": "cinema", "advisory_only": True, "preservation_pass": True,
        "five_groups": ["descriptive", "physical", "operational", "legal", "market"],
        "total_requirements_count": 31, "legacy_requirements_count": 4, "normalized_requirements_count": 27,
        "missing_legacy_requirements_after_restore": [],
        "field_types_used": ["text", "textarea", "number", "currency", "percent", "select", "checkbox_group", "file", "coordinate"],
    },
    "general_hospital": {
        "asset_key": "general_hospital", "advisory_only": True, "preservation_pass": True,
        "five_groups": ["descriptive", "physical", "operational", "legal", "market"],
        "total_requirements_count": 35, "legacy_requirements_count": 20, "normalized_requirements_count": 15,
        "missing_legacy_requirements_after_restore": [],
        "field_types_used": ["text", "textarea", "number", "currency", "percent", "select", "checkbox_group", "file", "coordinate"],
    },
    "school_campus": {
        "asset_key": "school_campus", "advisory_only": True, "preservation_pass": True,
        "five_groups": ["descriptive", "physical", "operational", "legal", "market"],
        "total_requirements_count": 30, "legacy_requirements_count": 15, "normalized_requirements_count": 15,
        "missing_legacy_requirements_after_restore": [],
        "field_types_used": ["text", "textarea", "number", "currency", "percent", "select", "checkbox_group", "file", "coordinate"],
    },
    "distinguished_architectural_heritage": {
        "asset_key": "distinguished_architectural_heritage", "advisory_only": True, "preservation_pass": True,
        "five_groups": ["descriptive", "physical", "operational", "legal", "market"],
        "total_requirements_count": 24, "legacy_requirements_count": 27, "normalized_requirements_count": 0,
        "missing_legacy_requirements_after_restore": [],
        "field_types_used": ["text", "textarea", "number", "currency", "select", "file", "coordinate"],
    },
}


def get_special_asset_registries() -> dict:
    """Return all 10 PVDSR special asset registries. advisory_only throughout."""
    return {
        "uncommon_asset_family":         _UNCOMMON_ASSET_FAMILY_REGISTRY,
        "uncommon_asset_subtype":        _UNCOMMON_ASSET_SUBTYPE_REGISTRY,
        "requirement_group":             _REQUIREMENT_GROUP_REGISTRY,
        "field_type":                    _FIELD_TYPE_REGISTRY,
        "dynamic_requirement_field":     _DYNAMIC_REQUIREMENT_FIELD_REGISTRY,
        "asset_specific_requirement":    _ASSET_SPECIFIC_REQUIREMENT_REGISTRY,
        "methodology_guidance":          _METHODOLOGY_GUIDANCE_REGISTRY,
        "asset_report_workbook_context": _ASSET_REPORT_WORKBOOK_CONTEXT_REGISTRY,
        "future_integrations":           _FUTURE_INTEGRATIONS_REGISTRY,
        "legacy_asset_alias":            _LEGACY_ASSET_ALIAS_REGISTRY,
    }


# ── PVACR: Chat Output Final Restructure Registries ───────────────────────────

_REPORT_OUTPUT_REGISTRY: dict = {
    "traditional_report": {
        "label_ar":                        "تقرير تقليدي",
        "user_pdf_allowed":                True,
        "admin_excel_allowed":             True,
        "certified_gate_required_for_final": True,
        "advisory_allowed":                True,
        "maps_to_canonical":               "summary_report",
    },
    "detailed_report": {
        "label_ar":                        "تقرير ت��صيلي",
        "user_pdf_allowed":                True,
        "admin_excel_allowed":             True,
        "certified_gate_required_for_final": True,
        "advisory_allowed":                True,
        "maps_to_canonical":               "full_report",
    },
    "professional_report": {
        "label_ar":                        "تقرير احترافي",
        "user_pdf_allowed":                True,
        "admin_excel_allowed":             True,
        "certified_gate_required_for_final": True,
        "advisory_allowed":                True,
        "maps_to_canonical":               "enhanced_professional_report",
    },
    "simulated_uploaded_report": {
        "label_ar":                        "محاكاة تقرير مرفوع",
        "requires_uploaded_report":        True,
        "requires_training_toggle":        True,
        "user_pdf_allowed":                True,
        "admin_excel_allowed":             True,
        "certified_gate_required_for_final": True,
        "advisory_allowed":                True,
        "simulation_only":                 True,
    },
    "report_review_output": {
        "label_ar":                        "مراجعة تقرير",
        "requires_report_review_toggle":   True,
        "user_pdf_allowed":                True,
        "admin_excel_allowed":             True,
        "advisory_allowed":                True,
        "review_only":                     True,
    },
    "hbu_analysis_report": {
        "label_ar":                        "تقرير تحليل أعلى وأفضل استخدام",
        "requires_hbu_report_toggle":      True,
        "user_pdf_allowed":                True,
        "admin_excel_allowed":             True,
        "advisory_allowed":                True,
    },
}

_OUTPUT_FORMAT_VISIBILITY_POLICY: dict = {
    "user_pdf": {
        "visible_to":            ["user", "admin", "expert"],
        "contains_internal_paths": False,
    },
    "admin_excel": {
        "visible_to":            ["admin"],
        "contains_internal_paths": False,
    },
}

_DEPRECATED_VISIBLE_CONTROLS_REGISTRY: dict = {
    "preliminary_weighting_engine": {
        "old_visible_labels":      ["محرك الترجيح المبدئي", "3.5 الترجيح المبدئي للطرق"],
        "visible_in_main_page":    False,
        "backend_alias_preserved": True,
        "new_location":            "method_analysis_context_or_report_context_only",
        "reason":                  "Removed from main page to reduce clutter.",
    },
    "disclosures_warnings_panel": {
        "old_visible_label":       "3.6 الإفصاحات والتحذيرات",
        "visible_in_main_page":    False,
        "backend_context_preserved": True,
        "new_location":            "report_context_or_inline_validation_only",
    },
    "engine_governance_audit_panel": {
        "old_visible_label":       "حوكمة المحرك والتدقيق — متقدم",
        "visible_in_main_page":    False,
        "internal_context_preserved": True,
        "new_location":            "internal_backend_audit_context_only",
        "reason":                  "Advanced internal trace should not clutter the client-facing page.",
    },
    "standalone_report_type_section": {
        "old_visible_label":       "5. نوع التقرير",
        "visible_in_main_page":    False,
        "backend_alias_preserved": True,
        "new_location":            "chat_box_report_action_dropdown",
        "reason":                  "Report type selection rehomed to Chat Box dropdown.",
    },
    "standalone_outputs_drafts_section": {
        "old_visible_label":       "المخرجات والمسودة",
        "visible_in_main_page":    False,
        "backend_alias_preserved": True,
        "new_location":            "chat_box_section",
        "reason":                  "Output generation consolidated into Chat Box.",
    },
}

_OUTPUT_SURFACE_REGISTRY: dict = {
    "primary_visible_surface":           "chat_box",
    "standalone_output_sections_visible": False,
    "admin_excel_visible_to_user":        False,
    "certification_gates_preserved":      True,
}


def get_chat_output_registries() -> dict:
    """Return PVACR chat output registries. advisory_only throughout."""
    return {
        "report_output_registry":          _REPORT_OUTPUT_REGISTRY,
        "output_format_visibility_policy": _OUTPUT_FORMAT_VISIBILITY_POLICY,
        "deprecated_visible_controls":     _DEPRECATED_VISIBLE_CONTROLS_REGISTRY,
        "output_surface_registry":         _OUTPUT_SURFACE_REGISTRY,
    }

