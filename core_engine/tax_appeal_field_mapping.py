"""
tax_appeal_field_mapping.py — Manual field-mapping workflow for tax appeal evidence.

Workflow:
  Expert uploads evidence → approves as source/for-report → creates manual
  field mappings linking evidence to specific report fields → confirms mappings
  → applies confirmed mappings as source-linked context overlay.

Rules:
  - No OCR, no Qdrant, no RAG, no automatic value extraction.
  - All mapped values must be manually entered or confirmed by the expert.
  - Mappings start as draft/needs_review.
  - Only confirmed mappings can be used in report context.
  - production_ready=True only if evidence is approved_as_source + expert confirmed.
  - Conflicts detected when mapped value differs from existing payload value.
  - Unresolved conflicts block apply-to-context.
  - No internal file paths in API responses.

Storage:
  instance/tax_appeal_field_mappings/<request_id>/mappings.jsonl
  instance/tax_appeal_field_mappings/<request_id>/conflicts.jsonl
  instance/tax_appeal_field_mappings/<request_id>/context_overlay.json
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── Storage ───────────────────────────────────────────────────────────────────

_FM_BASE = Path(__file__).parent / "instance" / "tax_appeal_field_mappings"
_FM_BASE.mkdir(parents=True, exist_ok=True)

# ── Regex validators ──────────────────────────────────────────────────────────

_ER_ID_RE = re.compile(r"^TAXER-[0-9A-F]{8}$")
_FM_ID_RE = re.compile(r"^FM-[0-9A-F]{8}$")
_CF_ID_RE = re.compile(r"^FC-[0-9A-F]{8}$")

# ── Valid statuses ────────────────────────────────────────────────────────────

_FM_STATUSES = {"draft", "needs_review", "confirmed", "rejected", "superseded"}
_CF_STATUSES = {
    "no_conflict", "needs_expert_decision", "accepted_mapped_value",
    "kept_existing_value", "rejected_mapping", "superseded",
}
_EV_ACTIVE_STATUSES = {"uploaded", "needs_review", "approved_for_report", "approved_as_source"}

# ── Value types ───────────────────────────────────────────────────────────────

VALUE_TYPES = {"text", "number", "money", "percentage", "date", "boolean", "enum", "long_text"}

# ── Value origins ─────────────────────────────────────────────────────────────

VALUE_ORIGINS = {
    "expert_manual_entry",
    "user_payload_existing",
    "approved_source_manual_mapping",
    "qa_simulation",
    "future_ocr_placeholder",     # inactive — placeholder only
    "future_qdrant_placeholder",  # inactive — placeholder only
}

# ── Field catalogue ───────────────────────────────────────────────────────────

FIELD_CATALOGUE: list[dict] = [
    # ── Group 1: Tax notice / Form 3 ──────────────────────────────────────────
    {
        "field_key": "tax_notice_number",
        "label_ar": "رقم الإشعار الضريبي",
        "group": "tax_notice",
        "value_type": "text",
        "allowed_evidence_types": ["tax_notice_form3"],
        "required_for_tax_modes": ["annual_real_estate_tax", "transfer_tax"],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": False,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "رقم مرجعي فريد من إشعار نموذج 3",
    },
    {
        "field_key": "notice_issue_date",
        "label_ar": "تاريخ إصدار الإشعار",
        "group": "tax_notice",
        "value_type": "date",
        "allowed_evidence_types": ["tax_notice_form3"],
        "required_for_tax_modes": ["annual_real_estate_tax"],
        "required_for_property_classes": [],
        "affects_deadline": True,
        "affects_calculation": False,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "تاريخ صدور الإشعار من مصلحة الضرائب",
    },
    {
        "field_key": "notice_received_date",
        "label_ar": "تاريخ استلام الإشعار",
        "group": "tax_notice",
        "value_type": "date",
        "allowed_evidence_types": ["tax_notice_form3"],
        "required_for_tax_modes": ["annual_real_estate_tax"],
        "required_for_property_classes": [],
        "affects_deadline": True,
        "affects_calculation": False,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "تاريخ استلام العميل للإشعار — يبدأ منه ميعاد الطعن 60 يومًا",
    },
    {
        "field_key": "tax_assessment_basis_date",
        "label_ar": "تاريخ أساس التقدير الضريبي",
        "group": "tax_notice",
        "value_type": "date",
        "allowed_evidence_types": ["tax_notice_form3"],
        "required_for_tax_modes": ["annual_real_estate_tax"],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "تاريخ آخر حصر ضريبي — يحدد القيمة الإيجارية الحكومية",
    },
    {
        "field_key": "tax_cycle_year",
        "label_ar": "سنة الدورة الضريبية",
        "group": "tax_notice",
        "value_type": "number",
        "allowed_evidence_types": ["tax_notice_form3"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "السنة الضريبية محل الطعن",
    },
    {
        "field_key": "government_tax_amount",
        "label_ar": "مبلغ الضريبة الحكومي",
        "group": "tax_notice",
        "value_type": "money",
        "allowed_evidence_types": ["tax_notice_form3"],
        "required_for_tax_modes": ["annual_real_estate_tax"],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "المبلغ الضريبي المُقدَّر من الحكومة قبل الطعن",
    },
    {
        "field_key": "government_annual_rental_value",
        "label_ar": "القيمة الإيجارية السنوية الحكومية",
        "group": "tax_notice",
        "value_type": "money",
        "allowed_evidence_types": ["tax_notice_form3"],
        "required_for_tax_modes": ["annual_real_estate_tax"],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "القيمة الإيجارية السنوية وفق التقدير الحكومي",
    },
    {
        "field_key": "government_assessed_value",
        "label_ar": "القيمة المُقدَّرة حكوميًا",
        "group": "tax_notice",
        "value_type": "money",
        "allowed_evidence_types": ["tax_notice_form3"],
        "required_for_tax_modes": ["annual_real_estate_tax"],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "القيمة السوقية أو الإيجارية وفق التقدير الحكومي",
    },
    {
        "field_key": "property_tax_account_number",
        "label_ar": "رقم الحساب الضريبي للعقار",
        "group": "tax_notice",
        "value_type": "text",
        "allowed_evidence_types": ["tax_notice_form3"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": False,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "رقم الملف الضريبي لدى مصلحة الضرائب العقارية",
    },
    {
        "field_key": "tax_authority_office",
        "label_ar": "مكتب مصلحة الضرائب",
        "group": "tax_notice",
        "value_type": "text",
        "allowed_evidence_types": ["tax_notice_form3"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": False,
        "affects_report": True,
        "requires_expert_confirmation": False,
        "ordinary_user_visible": False,
        "notes": "اسم المكتب الصادر منه الإشعار",
    },
    {
        "field_key": "objection_deadline_date",
        "label_ar": "تاريخ انتهاء ميعاد الطعن",
        "group": "tax_notice",
        "value_type": "date",
        "allowed_evidence_types": ["tax_notice_form3"],
        "required_for_tax_modes": ["annual_real_estate_tax"],
        "required_for_property_classes": [],
        "affects_deadline": True,
        "affects_calculation": False,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "60 يومًا من تاريخ الاستلام — تاريخ انقضاء حق الطعن",
    },
    # ── Group 2: Property identification ──────────────────────────────────────
    {
        "field_key": "taxpayer_name",
        "label_ar": "اسم الممول",
        "group": "property_identification",
        "value_type": "text",
        "allowed_evidence_types": ["tax_notice_form3", "ownership_document"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": False,
        "affects_report": True,
        "requires_expert_confirmation": False,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "owner_name",
        "label_ar": "اسم المالك",
        "group": "property_identification",
        "value_type": "text",
        "allowed_evidence_types": ["ownership_document", "tax_notice_form3"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": False,
        "affects_report": True,
        "requires_expert_confirmation": False,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "property_address",
        "label_ar": "عنوان العقار",
        "group": "property_identification",
        "value_type": "text",
        "allowed_evidence_types": ["tax_notice_form3", "ownership_document", "area_statement", "floor_plan"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": False,
        "affects_report": True,
        "requires_expert_confirmation": False,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "district",
        "label_ar": "الحي",
        "group": "property_identification",
        "value_type": "text",
        "allowed_evidence_types": ["tax_notice_form3", "ownership_document", "map_or_aerial_image"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": False,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "city",
        "label_ar": "المدينة",
        "group": "property_identification",
        "value_type": "text",
        "allowed_evidence_types": ["tax_notice_form3", "ownership_document"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": False,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "zone_id",
        "label_ar": "منطقة التقييم",
        "group": "property_identification",
        "value_type": "text",
        "allowed_evidence_types": ["tax_notice_form3", "map_or_aerial_image"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "property_type",
        "label_ar": "نوع العقار",
        "group": "property_identification",
        "value_type": "enum",
        "allowed_evidence_types": ["tax_notice_form3", "ownership_document", "building_permit"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "property_subtype",
        "label_ar": "النوع الفرعي للعقار",
        "group": "property_identification",
        "value_type": "enum",
        "allowed_evidence_types": ["tax_notice_form3", "ownership_document", "building_permit"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "property_area",
        "label_ar": "مساحة الوحدة/العقار (م²)",
        "group": "property_identification",
        "value_type": "number",
        "allowed_evidence_types": ["ownership_document", "area_statement", "floor_plan", "tax_notice_form3"],
        "required_for_tax_modes": ["annual_real_estate_tax"],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "المساحة المستخدمة في حساب القيمة الإيجارية",
    },
    {
        "field_key": "floor",
        "label_ar": "الطابق",
        "group": "property_identification",
        "value_type": "text",
        "allowed_evidence_types": ["ownership_document", "area_statement", "floor_plan"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": False,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "unit_number",
        "label_ar": "رقم الوحدة",
        "group": "property_identification",
        "value_type": "text",
        "allowed_evidence_types": ["ownership_document", "area_statement"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": False,
        "affects_report": True,
        "requires_expert_confirmation": False,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "building_number",
        "label_ar": "رقم المبنى",
        "group": "property_identification",
        "value_type": "text",
        "allowed_evidence_types": ["ownership_document", "area_statement", "tax_notice_form3"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": False,
        "affects_report": True,
        "requires_expert_confirmation": False,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "land_area",
        "label_ar": "مساحة الأرض (م²)",
        "group": "property_identification",
        "value_type": "number",
        "allowed_evidence_types": ["ownership_document", "land_allocation_document", "area_statement"],
        "required_for_tax_modes": [],
        "required_for_property_classes": ["land", "villa"],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "building_area",
        "label_ar": "مساحة البناء (م²)",
        "group": "property_identification",
        "value_type": "number",
        "allowed_evidence_types": ["ownership_document", "building_permit", "area_statement", "floor_plan"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "",
    },
    # ── Group 3: Ownership / legal ────────────────────────────────────────────
    {
        "field_key": "ownership_document_number",
        "label_ar": "رقم وثيقة الملكية",
        "group": "ownership_legal",
        "value_type": "text",
        "allowed_evidence_types": ["ownership_document"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": False,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "ownership_type",
        "label_ar": "نوع الملكية",
        "group": "ownership_legal",
        "value_type": "enum",
        "allowed_evidence_types": ["ownership_document"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "ownership_date",
        "label_ar": "تاريخ الملكية",
        "group": "ownership_legal",
        "value_type": "date",
        "allowed_evidence_types": ["ownership_document"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": False,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "legal_dispute_status",
        "label_ar": "حالة النزاع القانوني",
        "group": "ownership_legal",
        "value_type": "enum",
        "allowed_evidence_types": ["ownership_document", "legal_note"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": False,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "mortgage_or_lien_status",
        "label_ar": "حالة الرهن أو الحجز",
        "group": "ownership_legal",
        "value_type": "enum",
        "allowed_evidence_types": ["ownership_document", "legal_note"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": False,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "ownership_notes",
        "label_ar": "ملاحظات الملكية",
        "group": "ownership_legal",
        "value_type": "long_text",
        "allowed_evidence_types": ["ownership_document", "legal_note", "expert_note"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": False,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "",
    },
    # ── Group 4: License / use ────────────────────────────────────────────────
    {
        "field_key": "licensed_use",
        "label_ar": "الاستخدام المرخَّص",
        "group": "license_use",
        "value_type": "text",
        "allowed_evidence_types": ["activity_license", "building_permit", "industrial_license"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "actual_use",
        "label_ar": "الاستخدام الفعلي",
        "group": "license_use",
        "value_type": "text",
        "allowed_evidence_types": ["activity_license", "property_photos", "expert_note"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "activity_license_number",
        "label_ar": "رقم ترخيص النشاط",
        "group": "license_use",
        "value_type": "text",
        "allowed_evidence_types": ["activity_license"],
        "required_for_tax_modes": [],
        "required_for_property_classes": ["commercial", "industrial"],
        "affects_deadline": False,
        "affects_calculation": False,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "activity_license_date",
        "label_ar": "تاريخ ترخيص النشاط",
        "group": "license_use",
        "value_type": "date",
        "allowed_evidence_types": ["activity_license"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": False,
        "affects_report": True,
        "requires_expert_confirmation": False,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "activity_type",
        "label_ar": "نوع النشاط",
        "group": "license_use",
        "value_type": "text",
        "allowed_evidence_types": ["activity_license", "commercial_register", "industrial_license"],
        "required_for_tax_modes": [],
        "required_for_property_classes": ["commercial", "industrial"],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "industrial_license_number",
        "label_ar": "رقم الترخيص الصناعي",
        "group": "license_use",
        "value_type": "text",
        "allowed_evidence_types": ["industrial_license"],
        "required_for_tax_modes": [],
        "required_for_property_classes": ["industrial"],
        "affects_deadline": False,
        "affects_calculation": False,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "commercial_register_number",
        "label_ar": "رقم السجل التجاري",
        "group": "license_use",
        "value_type": "text",
        "allowed_evidence_types": ["commercial_register"],
        "required_for_tax_modes": [],
        "required_for_property_classes": ["commercial"],
        "affects_deadline": False,
        "affects_calculation": False,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "",
    },
    # ── Group 5: Valuation support ─────────────────────────────────────────────
    {
        "field_key": "market_comparable_value",
        "label_ar": "القيمة السوقية المقارِنة",
        "group": "valuation_support",
        "value_type": "money",
        "allowed_evidence_types": ["market_comparables_excel"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "القيمة المرجعية من ملف مقارنات السوق — يجب تأكيد الخبير",
    },
    {
        "field_key": "rental_comparable_value",
        "label_ar": "القيمة الإيجارية المقارِنة",
        "group": "valuation_support",
        "value_type": "money",
        "allowed_evidence_types": ["rental_comparables_excel"],
        "required_for_tax_modes": ["annual_real_estate_tax"],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "الإيجار المرجعي من ملف مقارنات الإيجار",
    },
    {
        "field_key": "tax_comparable_value",
        "label_ar": "القيمة الضريبية المقارِنة",
        "group": "valuation_support",
        "value_type": "money",
        "allowed_evidence_types": ["tax_comparables_excel"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "land_price_reference",
        "label_ar": "سعر الأرض المرجعي (ج.م/م²)",
        "group": "valuation_support",
        "value_type": "money",
        "allowed_evidence_types": ["nuca_land_price_reference", "market_comparables_excel", "expert_note"],
        "required_for_tax_modes": [],
        "required_for_property_classes": ["land", "villa"],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "building_cost_reference",
        "label_ar": "تكلفة البناء المرجعية (ج.م/م²)",
        "group": "valuation_support",
        "value_type": "money",
        "allowed_evidence_types": ["factory_cost_guidance", "expert_note"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "depreciation_rate_reference",
        "label_ar": "معدل الإهلاك المرجعي (%)",
        "group": "valuation_support",
        "value_type": "percentage",
        "allowed_evidence_types": ["expert_note", "factory_cost_guidance"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "factory_cost_guidance_reference",
        "label_ar": "مرجع تكلفة المصنع",
        "group": "valuation_support",
        "value_type": "text",
        "allowed_evidence_types": ["factory_cost_guidance", "ain_shams_factory_cost_reference"],
        "required_for_tax_modes": [],
        "required_for_property_classes": ["industrial"],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "ain_shams_factory_cost_reference",
        "label_ar": "مرجع تكلفة مصانع عين شمس",
        "group": "valuation_support",
        "value_type": "money",
        "allowed_evidence_types": ["ain_shams_factory_cost_reference"],
        "required_for_tax_modes": [],
        "required_for_property_classes": ["industrial"],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "مرجع تكلفة البناء الصناعي من منطقة عين شمس",
    },
    {
        "field_key": "nuca_land_price_reference",
        "label_ar": "مرجع أسعار أراضي هيئة التعمير",
        "group": "valuation_support",
        "value_type": "money",
        "allowed_evidence_types": ["nuca_land_price_reference"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "سعر الأرض المرجعي من هيئة التعمير",
    },
    # ── Group 6: Deadline ─────────────────────────────────────────────────────
    {
        "field_key": "deadline_date",
        "label_ar": "تاريخ الموعد النهائي للطعن",
        "group": "deadline",
        "value_type": "date",
        "allowed_evidence_types": ["tax_notice_form3"],
        "required_for_tax_modes": ["annual_real_estate_tax"],
        "required_for_property_classes": [],
        "affects_deadline": True,
        "affects_calculation": False,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "يُحسب من تاريخ استلام الإشعار + 60 يومًا",
    },
    {
        "field_key": "days_remaining",
        "label_ar": "الأيام المتبقية على موعد الطعن",
        "group": "deadline",
        "value_type": "number",
        "allowed_evidence_types": ["tax_notice_form3"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": True,
        "affects_calculation": False,
        "affects_report": True,
        "requires_expert_confirmation": False,
        "ordinary_user_visible": False,
        "notes": "محسوب آليًا من تاريخ الاستلام وتاريخ التقرير",
    },
    {
        "field_key": "deadline_status",
        "label_ar": "حالة الموعد النهائي",
        "group": "deadline",
        "value_type": "enum",
        "allowed_evidence_types": ["tax_notice_form3"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": True,
        "affects_calculation": False,
        "affects_report": True,
        "requires_expert_confirmation": False,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "deadline_risk_note",
        "label_ar": "ملاحظة مخاطرة الموعد",
        "group": "deadline",
        "value_type": "long_text",
        "allowed_evidence_types": ["tax_notice_form3", "expert_note"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": True,
        "affects_calculation": False,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "",
    },
    # ── Group 7: Report recommendation ────────────────────────────────────────
    {
        "field_key": "proposed_corrected_tax",
        "label_ar": "الضريبة المقترحة بعد التصحيح",
        "group": "report_recommendation",
        "value_type": "money",
        "allowed_evidence_types": ["tax_notice_form3", "market_comparables_excel", "rental_comparables_excel", "expert_note"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "الضريبة العقارية السنوية المقترحة وفق تقييم الخبير",
    },
    {
        "field_key": "expected_saving",
        "label_ar": "الوفر الضريبي المتوقع",
        "group": "report_recommendation",
        "value_type": "money",
        "allowed_evidence_types": ["expert_note"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "الفرق بين الضريبة الحالية والمقترحة",
    },
    {
        "field_key": "overcharge_percentage",
        "label_ar": "نسبة الزيادة في التقدير (%)",
        "group": "report_recommendation",
        "value_type": "percentage",
        "allowed_evidence_types": ["expert_note"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": True,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "recommended_action",
        "label_ar": "الإجراء الموصى به",
        "group": "report_recommendation",
        "value_type": "long_text",
        "allowed_evidence_types": ["expert_note"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": False,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "",
    },
    {
        "field_key": "legal_review_required",
        "label_ar": "يتطلب مراجعة قانونية",
        "group": "report_recommendation",
        "value_type": "boolean",
        "allowed_evidence_types": ["legal_note", "expert_note"],
        "required_for_tax_modes": [],
        "required_for_property_classes": [],
        "affects_deadline": False,
        "affects_calculation": False,
        "affects_report": True,
        "requires_expert_confirmation": True,
        "ordinary_user_visible": False,
        "notes": "",
    },
]

# Quick lookup by key
_CATALOGUE_BY_KEY: dict[str, dict] = {f["field_key"]: f for f in FIELD_CATALOGUE}

# ── Storage helpers ───────────────────────────────────────────────────────────

def _fm_dir(request_id: str) -> Path:
    d = _FM_BASE / request_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _fm_file(request_id: str) -> Path:
    return _fm_dir(request_id) / "mappings.jsonl"


def _cf_file(request_id: str) -> Path:
    return _fm_dir(request_id) / "conflicts.jsonl"


def _overlay_file(request_id: str) -> Path:
    return _fm_dir(request_id) / "context_overlay.json"


def _new_fm_id() -> str:
    return "FM-" + uuid.uuid4().hex[:8].upper()


def _new_cf_id() -> str:
    return "FC-" + uuid.uuid4().hex[:8].upper()


def _persist_fm(request_id: str, rec: dict) -> None:
    f = _fm_file(request_id)
    with open(f, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _update_fm(request_id: str, mapping_id: str, updates: dict) -> None:
    f = _fm_file(request_id)
    if not f.exists():
        return
    lines: list[str] = []
    with open(f, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
                if rec.get("mapping_id") == mapping_id:
                    rec.update(updates)
                    audit = rec.get("audit_log", [])
                    audit.append({
                        "action": "updated",
                        "fields": list(updates.keys()),
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                    rec["audit_log"] = audit
                lines.append(json.dumps(rec, ensure_ascii=False))
            except json.JSONDecodeError:
                lines.append(raw)
    with open(f, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def _read_fm(request_id: str, mapping_id: str) -> Optional[dict]:
    f = _fm_file(request_id)
    if not f.exists():
        return None
    with open(f, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
                if rec.get("mapping_id") == mapping_id:
                    return rec
            except json.JSONDecodeError:
                continue
    return None


def load_mapping_records(request_id: str) -> list[dict]:
    """Load all mapping records for a request. Public — used by context/workbook builders."""
    f = _fm_file(request_id)
    if not f.exists():
        return []
    rows: list[dict] = []
    with open(f, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rows.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    return rows


def _persist_cf(request_id: str, rec: dict) -> None:
    f = _cf_file(request_id)
    with open(f, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _update_cf(request_id: str, conflict_id: str, updates: dict) -> None:
    f = _cf_file(request_id)
    if not f.exists():
        return
    lines: list[str] = []
    with open(f, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
                if rec.get("conflict_id") == conflict_id:
                    rec.update(updates)
                lines.append(json.dumps(rec, ensure_ascii=False))
            except json.JSONDecodeError:
                lines.append(raw)
    with open(f, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def load_conflict_records(request_id: str) -> list[dict]:
    """Load all conflict records for a request."""
    f = _cf_file(request_id)
    if not f.exists():
        return []
    rows: list[dict] = []
    with open(f, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rows.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    return rows


# ── Safe response builders ────────────────────────────────────────────────────

def _fm_safe(rec: dict) -> dict:
    """Return public-safe mapping metadata — never includes internal paths."""
    return {
        "mapping_id":              rec.get("mapping_id"),
        "request_id":              rec.get("request_id"),
        "evidence_id":             rec.get("evidence_id"),
        "source_registry_id":      rec.get("source_registry_id"),
        "evidence_type":           rec.get("evidence_type"),
        "mapped_field_key":        rec.get("mapped_field_key"),
        "mapped_field_label_ar":   rec.get("mapped_field_label_ar"),
        "mapped_field_group":      rec.get("mapped_field_group"),
        "mapped_value":            rec.get("mapped_value"),
        "mapped_value_type":       rec.get("mapped_value_type"),
        "mapped_value_display":    rec.get("mapped_value_display"),
        "source_status":           rec.get("source_status"),
        "evidence_status":         rec.get("evidence_status"),
        "mapping_status":          rec.get("mapping_status"),
        "production_ready":        rec.get("production_ready", False),
        "expert_confirmed":        rec.get("expert_confirmed", False),
        "expert_reviewed_by":      rec.get("expert_reviewed_by"),
        "expert_reviewed_at":      rec.get("expert_reviewed_at"),
        "confidence_level":        rec.get("confidence_level"),
        "value_origin":            rec.get("value_origin"),
        "conflict_status":         rec.get("conflict_status"),
        "previous_value":          rec.get("previous_value"),
        "existing_payload_value":  rec.get("existing_payload_value"),
        "override_applied":        rec.get("override_applied", False),
        "override_reason":         rec.get("override_reason"),
        "report_usage_allowed":    rec.get("report_usage_allowed", False),
        "used_in_pdf":             rec.get("used_in_pdf", False),
        "used_in_workbook":        rec.get("used_in_workbook", False),
        "used_in_calculation":     rec.get("used_in_calculation", False),
        "ordinary_user_visible":   rec.get("ordinary_user_visible", False),
        "created_at":              rec.get("created_at"),
        "updated_at":              rec.get("updated_at"),
        "no_automatic_value_extraction": True,
    }


def _cf_safe(rec: dict) -> dict:
    """Return public-safe conflict metadata."""
    return {
        "conflict_id":             rec.get("conflict_id"),
        "mapping_id":              rec.get("mapping_id"),
        "field_key":               rec.get("field_key"),
        "existing_payload_value":  rec.get("existing_payload_value"),
        "mapped_value":            rec.get("mapped_value"),
        "evidence_id":             rec.get("evidence_id"),
        "source_registry_id":      rec.get("source_registry_id"),
        "severity":                rec.get("severity"),
        "conflict_status":         rec.get("conflict_status"),
        "expert_decision_required": rec.get("expert_decision_required", True),
        "resolution":              rec.get("resolution"),
        "override_reason":         rec.get("override_reason"),
        "created_at":              rec.get("created_at"),
        "updated_at":              rec.get("updated_at"),
    }


# ── Conflict detection ────────────────────────────────────────────────────────

def _detect_conflict(
    request_id: str,
    mapping_id: str,
    field_key: str,
    mapped_value: str,
    evidence_id: str,
    source_registry_id: Optional[str],
    payload: dict,
) -> Optional[dict]:
    """Detect if mapped value conflicts with existing payload value. Returns conflict record or None."""
    existing = payload.get(field_key)
    if existing is None:
        return None

    existing_str = str(existing).strip()
    mapped_str   = str(mapped_value).strip()

    if not existing_str or not mapped_str:
        return None

    if existing_str == mapped_str:
        return None

    # Severity heuristics
    field_info = _CATALOGUE_BY_KEY.get(field_key, {})
    affects_calculation = field_info.get("affects_calculation", False)
    severity = "high" if affects_calculation else "medium"

    cf_id = _new_cf_id()
    now   = datetime.utcnow().isoformat()

    rec = {
        "conflict_id":              cf_id,
        "mapping_id":               mapping_id,
        "field_key":                field_key,
        "existing_payload_value":   existing_str,
        "mapped_value":             mapped_str,
        "evidence_id":              evidence_id,
        "source_registry_id":       source_registry_id,
        "severity":                 severity,
        "conflict_status":          "needs_expert_decision",
        "expert_decision_required": True,
        "resolution":               None,
        "override_reason":          None,
        "created_at":               now,
        "updated_at":               now,
    }
    _persist_cf(request_id, rec)
    return rec


# ── Source-linked summary builder ─────────────────────────────────────────────

def build_field_mapping_summary(
    mapping_records: list[dict],
    conflict_records: list[dict],
) -> dict:
    """Build field_mapping_summary for context / API responses."""
    total     = len(mapping_records)
    confirmed = sum(1 for m in mapping_records if m.get("mapping_status") == "confirmed")
    pending   = sum(1 for m in mapping_records if m.get("mapping_status") in ("draft", "needs_review"))
    rejected  = sum(1 for m in mapping_records if m.get("mapping_status") == "rejected")
    prod_ready= sum(1 for m in mapping_records if m.get("production_ready"))

    by_group: dict[str, list[str]] = {}
    for m in mapping_records:
        grp = m.get("mapped_field_group", "other")
        by_group.setdefault(grp, [])
        if m.get("mapped_field_key") not in by_group[grp]:
            by_group[grp].append(m.get("mapped_field_key", ""))

    unresolved_conflicts = [
        c for c in conflict_records
        if c.get("conflict_status") == "needs_expert_decision"
    ]

    applied = [
        m.get("mapped_field_key")
        for m in mapping_records
        if m.get("mapping_status") == "confirmed"
        and m.get("report_usage_allowed")
        and not m.get("conflict_status") in ("needs_expert_decision",)
    ]

    expert_actions = []
    if pending:
        expert_actions.append(f"{pending} ربط/روابط تحتاج مراجعة أو تأكيد")
    if unresolved_conflicts:
        expert_actions.append(f"{len(unresolved_conflicts)} تعارض/تعارضات تحتاج قرار خبير")

    return {
        "total_mappings":              total,
        "confirmed_mappings":          confirmed,
        "pending_mappings":            pending,
        "rejected_mappings":           rejected,
        "production_ready_mappings":   prod_ready,
        "mapped_fields_by_group":      by_group,
        "conflicts_count":             len(conflict_records),
        "unresolved_conflicts":        len(unresolved_conflicts),
        "applied_source_linked_fields": applied,
        "expert_actions_required":     expert_actions,
        "no_automatic_value_extraction": True,
    }


def build_source_linked_inputs(
    mapping_records: list[dict],
    conflict_records: list[dict],
) -> dict:
    """Build source_linked_inputs dict for context overlay."""
    conflict_by_mapping: dict[str, dict] = {}
    for c in conflict_records:
        mid = c.get("mapping_id")
        if mid:
            conflict_by_mapping[mid] = c

    result: dict[str, dict] = {}
    for m in mapping_records:
        if m.get("mapping_status") != "confirmed":
            continue
        if not m.get("report_usage_allowed"):
            continue

        mid   = m.get("mapping_id", "")
        fkey  = m.get("mapped_field_key", "")
        cf    = conflict_by_mapping.get(mid, {})
        cf_st = cf.get("conflict_status", "no_conflict") if cf else "no_conflict"

        if cf_st == "needs_expert_decision":
            continue   # unresolved conflict — do not apply

        result[fkey] = {
            "value":             m.get("mapped_value"),
            "display_value":     m.get("mapped_value_display") or m.get("mapped_value"),
            "evidence_id":       m.get("evidence_id"),
            "source_registry_id": m.get("source_registry_id"),
            "evidence_type":     m.get("evidence_type"),
            "source_status":     m.get("source_status"),
            "production_ready":  m.get("production_ready", False),
            "expert_confirmed":  m.get("expert_confirmed", False),
            "used_in_report":    m.get("report_usage_allowed", False),
            "conflict_status":   cf_st,
            "notes":             None,   # expert notes excluded from ordinary context
        }

    return result


# ── Route registration ────────────────────────────────────────────────────────

def register_field_mapping_routes(app, require_auth) -> None:
    """Register all /api/tax-appeal/expert-requests/<id>/field-mappings/* routes."""
    from flask import jsonify, request as flask_request

    # ── GET .../field-mappings/catalogue ─────────────────────────────────────
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/field-mappings/catalogue",
        methods=["GET"],
    )
    @require_auth
    def tax_appeal_fm_catalogue(request_id: str):
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400

        from tax_appeal_routes import _read_er
        if not _read_er(request_id):
            return jsonify({"status": "error", "message": "طلب الطعن غير موجود"}), 404

        groups: dict[str, list] = {}
        for f in FIELD_CATALOGUE:
            grp = f["group"]
            groups.setdefault(grp, [])
            groups[grp].append({
                "field_key":                   f["field_key"],
                "label_ar":                    f["label_ar"],
                "group":                       grp,
                "value_type":                  f["value_type"],
                "allowed_evidence_types":      f["allowed_evidence_types"],
                "affects_deadline":            f["affects_deadline"],
                "affects_calculation":         f["affects_calculation"],
                "affects_report":              f["affects_report"],
                "requires_expert_confirmation": f["requires_expert_confirmation"],
                "ordinary_user_visible":       f["ordinary_user_visible"],
                "notes":                       f["notes"],
            })

        return jsonify({
            "status":    "ok",
            "request_id": request_id,
            "total_fields": len(FIELD_CATALOGUE),
            "catalogue_by_group": groups,
            "no_automatic_value_extraction": True,
        })

    # ── GET .../field-mappings ────────────────────────────────────────────────
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/field-mappings",
        methods=["GET"],
    )
    @require_auth
    def tax_appeal_fm_list(request_id: str):
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400

        from tax_appeal_routes import _read_er
        if not _read_er(request_id):
            return jsonify({"status": "error", "message": "طلب الطعن غير موجود"}), 404

        mappings  = load_mapping_records(request_id)
        conflicts = load_conflict_records(request_id)
        summary   = build_field_mapping_summary(mappings, conflicts)

        return jsonify({
            "status":     "ok",
            "request_id": request_id,
            "count":      len(mappings),
            "mappings":   [_fm_safe(m) for m in mappings],
            "conflicts":  [_cf_safe(c) for c in conflicts],
            "field_mapping_summary": summary,
            "no_automatic_value_extraction": True,
        })

    # ── POST .../field-mappings ───────────────────────────────────────────────
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/field-mappings",
        methods=["POST"],
    )
    @require_auth
    def tax_appeal_fm_create(request_id: str):
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400

        from tax_appeal_routes import _read_er
        er = _read_er(request_id)
        if not er:
            return jsonify({"status": "error", "message": "طلب الطعن غير موجود"}), 404

        body = flask_request.get_json(force=True, silent=True) or {}

        evidence_id     = (body.get("evidence_id") or "").strip()
        field_key       = (body.get("mapped_field_key") or "").strip()
        mapped_value    = body.get("mapped_value")
        mapped_vtype    = (body.get("mapped_value_type") or "text").strip()
        expert_notes    = body.get("expert_notes")
        override_reason = body.get("override_reason")

        # Validate evidence_id
        if not evidence_id:
            return jsonify({"status": "error", "message": "evidence_id مطلوب"}), 400

        from tax_appeal_evidence_routes import _read_ev, EVIDENCE_TYPES as _EV_TYPES
        ev = _read_ev(request_id, evidence_id)
        if not ev:
            return jsonify({"status": "error", "message": "المستند غير موجود أو لا ينتمي لهذا الطلب"}), 404

        ev_status = ev.get("status", "")
        if ev_status in ("rejected", "superseded"):
            return jsonify({
                "status": "error",
                "message": f"لا يمكن ربط حقل بمستند بحالة '{ev_status}'",
            }), 422

        # Validate field key
        if not field_key:
            return jsonify({"status": "error", "message": "mapped_field_key مطلوب"}), 400
        field_info = _CATALOGUE_BY_KEY.get(field_key)
        if not field_info:
            return jsonify({"status": "error", "message": f"مفتاح الحقل غير موجود في الكتالوج: {field_key}"}), 400

        # Validate mapped_value
        if mapped_value is None:
            return jsonify({"status": "error", "message": "mapped_value مطلوب"}), 400

        # Evidence type compatibility check
        ev_type           = ev.get("evidence_type", "other")
        allowed_ev_types  = field_info.get("allowed_evidence_types", [])
        type_compatible   = not allowed_ev_types or ev_type in allowed_ev_types

        if not type_compatible and not override_reason:
            return jsonify({
                "status": "error",
                "message": (
                    f"نوع المستند '{ev_type}' غير متوافق مع الحقل '{field_key}'. "
                    f"المصادر المسموحة: {allowed_ev_types}. "
                    "أضف override_reason لتجاوز هذا التحقق."
                ),
                "allowed_evidence_types": allowed_ev_types,
                "evidence_type": ev_type,
            }), 422

        if mapped_vtype not in VALUE_TYPES:
            mapped_vtype = "text"

        # Production ready: only if evidence approved_as_source
        is_source = ev_status == "approved_as_source"
        production_ready = False  # starts false; set to True only on confirm if source

        now = datetime.utcnow().isoformat()
        fm_id = _new_fm_id()

        rec: dict = {
            "mapping_id":            fm_id,
            "request_id":            request_id,
            "evidence_id":           evidence_id,
            "source_registry_id":    ev.get("source_registry_id"),
            "evidence_type":         ev_type,
            "mapped_field_key":      field_key,
            "mapped_field_label_ar": field_info["label_ar"],
            "mapped_field_group":    field_info["group"],
            "mapped_value":          str(mapped_value),
            "mapped_value_type":     mapped_vtype,
            "mapped_value_display":  str(mapped_value),
            "source_status":         ev.get("source_status", ""),
            "evidence_status":       ev_status,
            "mapping_status":        "needs_review",
            "production_ready":      production_ready,
            "expert_confirmed":      False,
            "expert_reviewed_by":    None,
            "expert_reviewed_at":    None,
            "confidence_level":      "low",
            "value_origin":          (
                "approved_source_manual_mapping" if is_source
                else "expert_manual_entry"
            ),
            "conflict_status":       "no_conflict",
            "previous_value":        None,
            "existing_payload_value": None,
            "override_applied":      bool(override_reason and not type_compatible),
            "override_reason":       override_reason,
            "report_usage_allowed":  False,
            "used_in_pdf":           False,
            "used_in_workbook":      False,
            "used_in_calculation":   field_info.get("affects_calculation", False),
            "ordinary_user_visible": False,
            "expert_notes":          expert_notes,
            "created_at":            now,
            "updated_at":            now,
            "audit_log": [{
                "action":    "created",
                "timestamp": now,
                "evidence_id": evidence_id,
                "field_key": field_key,
            }],
        }

        # Conflict detection against existing payload
        _pj = er.get("payload_json")
        payload = (json.loads(_pj) if _pj else None) or er
        cf = _detect_conflict(
            request_id, fm_id, field_key, str(mapped_value),
            evidence_id, ev.get("source_registry_id"), payload,
        )
        if cf:
            rec["conflict_status"]       = "needs_expert_decision"
            rec["existing_payload_value"] = cf.get("existing_payload_value")

        _persist_fm(request_id, rec)

        resp = {
            "status":     "ok",
            "no_automatic_value_extraction": True,
            **_fm_safe(rec),
        }
        if cf:
            resp["conflict_detected"] = True
            resp["conflict"] = _cf_safe(cf)

        return jsonify(resp), 201

    # ── POST .../field-mappings/<mapping_id>/confirm ──────────────────────────
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/field-mappings/<mapping_id>/confirm",
        methods=["POST"],
    )
    @require_auth
    def tax_appeal_fm_confirm(request_id: str, mapping_id: str):
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400

        rec = _read_fm(request_id, mapping_id)
        if not rec:
            return jsonify({"status": "error", "message": "سجل الربط غير موجود"}), 404

        if rec.get("mapping_status") in ("rejected", "superseded"):
            return jsonify({
                "status": "error",
                "message": "لا يمكن تأكيد ربط بحالة rejected أو superseded",
            }), 422

        body = flask_request.get_json(force=True, silent=True) or {}
        now  = datetime.utcnow().isoformat()

        # production_ready: only if evidence is approved_as_source
        ev_status    = rec.get("evidence_status", "")
        is_source    = ev_status == "approved_as_source"
        prod_ready   = is_source   # explicit expert confirmation of source mapping

        updates: dict = {
            "mapping_status":     "confirmed",
            "expert_confirmed":   True,
            "expert_reviewed_at": now,
            "expert_reviewed_by": body.get("reviewed_by", "expert"),
            "report_usage_allowed": True,
            "production_ready":   prod_ready,
            "confidence_level":   "high" if is_source else "medium",
            "updated_at":         now,
        }
        if body.get("expert_notes"):
            updates["expert_notes"] = body["expert_notes"]

        _update_fm(request_id, mapping_id, updates)
        updated = _read_fm(request_id, mapping_id)

        return jsonify({
            "status":           "ok",
            **(_fm_safe(updated) if updated else {}),
        })

    # ── POST .../field-mappings/<mapping_id>/reject ───────────────────────────
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/field-mappings/<mapping_id>/reject",
        methods=["POST"],
    )
    @require_auth
    def tax_appeal_fm_reject(request_id: str, mapping_id: str):
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400

        rec = _read_fm(request_id, mapping_id)
        if not rec:
            return jsonify({"status": "error", "message": "سجل الربط غير موجود"}), 404

        body = flask_request.get_json(force=True, silent=True) or {}
        rejection_reason = (body.get("expert_notes") or body.get("rejection_reason") or "").strip()
        if not rejection_reason:
            return jsonify({"status": "error", "message": "rejection_reason أو expert_notes مطلوب لرفض الربط"}), 400

        now = datetime.utcnow().isoformat()
        _update_fm(request_id, mapping_id, {
            "mapping_status":     "rejected",
            "expert_confirmed":   False,
            "report_usage_allowed": False,
            "production_ready":   False,
            "expert_reviewed_at": now,
            "expert_notes":       rejection_reason,
            "updated_at":         now,
        })
        updated = _read_fm(request_id, mapping_id)

        return jsonify({
            "status": "ok",
            **(_fm_safe(updated) if updated else {}),
        })

    # ── POST .../field-mappings/<mapping_id>/supersede ────────────────────────
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/field-mappings/<mapping_id>/supersede",
        methods=["POST"],
    )
    @require_auth
    def tax_appeal_fm_supersede(request_id: str, mapping_id: str):
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400

        rec = _read_fm(request_id, mapping_id)
        if not rec:
            return jsonify({"status": "error", "message": "سجل الربط غير موجود"}), 404

        body = flask_request.get_json(force=True, silent=True) or {}
        now  = datetime.utcnow().isoformat()

        _update_fm(request_id, mapping_id, {
            "mapping_status":     "superseded",
            "expert_confirmed":   False,
            "report_usage_allowed": False,
            "production_ready":   False,
            "superseded_by_mapping_id": body.get("replacement_mapping_id"),
            "updated_at":         now,
        })
        updated = _read_fm(request_id, mapping_id)

        return jsonify({
            "status": "ok",
            **(_fm_safe(updated) if updated else {}),
        })

    # ── POST .../field-mappings/apply-to-context ──────────────────────────────
    @app.route(
        "/api/tax-appeal/expert-requests/<request_id>/field-mappings/apply-to-context",
        methods=["POST"],
    )
    @require_auth
    def tax_appeal_fm_apply_context(request_id: str):
        if not _ER_ID_RE.fullmatch(request_id):
            return jsonify({"status": "error", "message": "معرّف الطلب غير صالح"}), 400

        from tax_appeal_routes import _read_er
        er = _read_er(request_id)
        if not er:
            return jsonify({"status": "error", "message": "طلب الطعن غير موجود"}), 404

        mappings  = load_mapping_records(request_id)
        conflicts = load_conflict_records(request_id)

        # Block if unresolved conflicts
        unresolved = [
            c for c in conflicts
            if c.get("conflict_status") == "needs_expert_decision"
        ]
        if unresolved:
            return jsonify({
                "status":  "error",
                "message": f"يوجد {len(unresolved)} تعارض/تعارضات غير محسومة — يجب حسمها قبل التطبيق",
                "unresolved_conflicts": [_cf_safe(c) for c in unresolved],
            }), 422

        # Build confirmed mappings
        confirmed = [
            m for m in mappings
            if m.get("mapping_status") == "confirmed"
            and m.get("report_usage_allowed")
        ]

        _pj2 = er.get("payload_json")
        payload = (json.loads(_pj2) if _pj2 else None) or er
        applied_fields:   list[str] = []
        skipped_fields:   list[str] = []
        conflict_details: list[dict] = []

        source_linked = build_source_linked_inputs(mappings, conflicts)

        for m in confirmed:
            fkey = m.get("mapped_field_key", "")
            if fkey in source_linked:
                applied_fields.append(fkey)
            else:
                skipped_fields.append(fkey)

        # Persist context overlay snapshot (does NOT overwrite original payload)
        overlay = {
            "request_id":       request_id,
            "applied_at":       datetime.utcnow().isoformat(),
            "applied_fields":   applied_fields,
            "skipped_fields":   skipped_fields,
            "source_linked_inputs": source_linked,
        }
        _overlay_file(request_id).write_text(
            json.dumps(overlay, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # Mark used_in_pdf/workbook
        for m in confirmed:
            fkey = m.get("mapped_field_key", "")
            if fkey in applied_fields:
                _update_fm(request_id, m["mapping_id"], {
                    "used_in_pdf":      True,
                    "used_in_workbook": True,
                    "updated_at":       datetime.utcnow().isoformat(),
                })

        return jsonify({
            "status":              "ok",
            "applied_fields_count": len(applied_fields),
            "skipped_fields_count": len(skipped_fields),
            "conflicts_count":     0,
            "conflict_details":    conflict_details,
            "source_linked_context_summary": {
                "total_applied":  len(applied_fields),
                "applied_fields": applied_fields,
                "skipped_fields": skipped_fields,
            },
            "no_automatic_value_extraction": True,
        })
