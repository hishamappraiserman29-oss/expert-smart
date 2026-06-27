# -*- coding: utf-8 -*-
"""
tax_appeal_reference_registry.py — Internal Reference Registry for Tax Appeal Calculations.

Public API:
    _build_tax_reference_registry(payload: dict) -> dict

Provides structured internal reference data for:
    - Rental value references
    - Market transaction references
    - Land price references
    - Adjustment factor references
    - Prior valuation report links
    - Reference versioning / confidence metadata

Strict rules:
    - No live Qdrant, no RAG, no internet search, no external APIs.
    - QA simulation (_qa_simulation=True) uses synthetic data only.
    - Production mode shows explicit gap markers when verified data is absent.
    - Do not claim official data from NUCA, IDA, Tax Authority, or universities
      unless a document was explicitly uploaded by the user.
    - Do not claim Qdrant/internet/OCR are active.
"""
from __future__ import annotations

# ── Gap / status markers ───────────────────────────────────────────────────────

_SRC_QA        = "محاكاة QA — لا تصلح كدليل رسمي"
_SRC_EXPERT    = "إدخال الخبير — يحتاج توثيق"
_SRC_DOC       = "وثيقة مطلوبة غير مرفقة"
_SRC_HIST      = "تقرير داخلي تاريخي"
_SRC_FUTURE    = "مصدر مستقبلي — سيُفعَّل لاحقًا"
_SRC_QDRANT    = "Qdrant مرحلة مستقبلية — غير مفعل"
_SRC_OFFICIAL  = "وثيقة رسمية مطلوبة — غير مُقدَّمة"
_GAP           = "غير متاح ضمن بيانات الطلب"
_NOT_PROD      = False
_QA_NOTE       = "بيانات تجريبية لأغراض QA فقط — لا تصلح للتقديم أمام الجهات الرسمية"

# ── Property-class resolution ─────────────────────────────────────────────────

_CLASS_MAP: dict[str, str] = {
    "villa": "residential", "apartment": "residential", "residential_unit": "residential",
    "residential": "residential", "سكني": "residential",
    "shop": "non_residential", "admin_unit": "non_residential", "admin": "non_residential",
    "basement_storage": "non_residential", "basement": "non_residential",
    "office": "non_residential", "garage": "non_residential", "mall_unit": "non_residential",
    "factory": "special_purpose", "industrial_facility": "special_purpose",
    "industrial": "special_purpose", "production_facility": "special_purpose",
}

def _resolve_class(payload: dict) -> tuple[str, str]:
    raw = str(payload.get("property_type") or "").lower().strip()
    class_key = _CLASS_MAP.get(raw, "residential")
    return class_key, raw


# ── Reference row factory ─────────────────────────────────────────────────────

def _ref(
    ref_id: str, ref_type: str, source_label: str, source_status: str,
    city: str, district: str, prop_class: str, subtype: str,
    *,
    area: float | None = None,
    value: float | None = None,
    price_per_m2: float | None = None,
    monthly_rent: float | None = None,
    annual_rent: float | None = None,
    rent_per_m2_month: float | None = None,
    land_price_per_m2: float | None = None,
    adj_type: str | None = None,
    adj_value: float | None = None,
    evidence_quality: str = "متوسط",
    confidence: float = 0.5,
    prod_ready: bool = False,
    is_qa: bool = True,
    methods: list[str] | None = None,
    source_date: str = "2024-06-01",
    zone_id: str = "QA-ZONE-01",
    notes: str = "",
) -> dict:
    return {
        "reference_id":            ref_id,
        "reference_type":          ref_type,
        "source_label":            source_label,
        "source_status":           source_status,
        "source_origin":           "QA simulation" if is_qa else "internal",
        "source_date":             source_date,
        "city":                    city,
        "district":                district,
        "zone_id":                 zone_id,
        "property_class":          prop_class,
        "property_subtype":        subtype,
        "area":                    area,
        "value":                   value,
        "price_per_m2":            price_per_m2,
        "monthly_rent":            monthly_rent,
        "annual_rent":             annual_rent,
        "rent_per_m2_month":       rent_per_m2_month,
        "land_price_per_m2":       land_price_per_m2,
        "adjustment_factor_type":  adj_type,
        "adjustment_factor_value": adj_value,
        "evidence_quality":        evidence_quality,
        "confidence_score":        confidence,
        "production_ready":        prod_ready,
        "qa_simulation":           is_qa,
        "used_in_methods":         methods or [],
        "notes":                   notes or (_QA_NOTE if is_qa else _GAP),
    }


# ── Rental references ─────────────────────────────────────────────────────────

def _build_rental_references(
    payload: dict, class_key: str, subtype: str, district: str, city: str, is_qa: bool
) -> list[dict]:
    if not is_qa:
        return [_ref(
            "RENT-PROD-PLACEHOLDER", "rental_reference",
            "مرجع إيجاري — مطلوب توثيق", _SRC_DOC,
            city, district, class_key, subtype,
            evidence_quality="غير متاح", confidence=0.0, prod_ready=False, is_qa=False,
            methods=["income_capitalization"],
            notes="يحتاج استكمال مراجع إيجارية موثقة — تقارير سوقية أو تقدير خبير",
        )]

    annual_rent = float(payload.get("estimated_market_rental_value") or 0) or None
    area = float(payload.get("area") or 0) or None

    if class_key == "residential":
        monthly = round((annual_rent / 12) if annual_rent else 8_750.0, 2)
        area_ref = area or 320.0
        rents = [
            ("RENT-RES-QA-01", monthly,       area_ref,       "إيجار فيلا مقارنة أ"),
            ("RENT-RES-QA-02", monthly * 1.08, area_ref * 1.1, "إيجار فيلا مقارنة ب"),
            ("RENT-RES-QA-03", monthly * 0.91, area_ref * 0.9, "إيجار فيلا مقارنة ج"),
        ]
        return [
            _ref(rid, "rental_reference", label + " — محاكاة QA", _SRC_QA,
                 city, district, class_key, subtype,
                 area=a, monthly_rent=round(m, 2), annual_rent=round(m * 12, 2),
                 rent_per_m2_month=round(m / a, 2),
                 evidence_quality="QA محاكاة", confidence=0.30, prod_ready=False, is_qa=True,
                 methods=["income_capitalization"], source_date=f"2024-0{i+1}-01",
                 notes=_QA_NOTE)
            for i, (rid, m, a, label) in enumerate(rents)
        ]

    if class_key == "non_residential":
        if subtype in ("shop", "mall_unit"):
            rents = [
                ("RENT-NR-SHOP-QA-01", 2_400.0, 80.0,  "إيجار محل مقارنة أ"),
                ("RENT-NR-SHOP-QA-02", 2_600.0, 90.0,  "إيجار محل مقارنة ب"),
                ("RENT-NR-SHOP-QA-03", 2_100.0, 70.0,  "إيجار محل مقارنة ج"),
            ]
        elif subtype in ("admin_unit", "office"):
            rents = [
                ("RENT-NR-ADM-QA-01", 3_000.0, 120.0, "إيجار وحدة إدارية مقارنة أ"),
                ("RENT-NR-ADM-QA-02", 3_200.0, 130.0, "إيجار وحدة إدارية مقارنة ب"),
                ("RENT-NR-ADM-QA-03", 2_800.0, 110.0, "إيجار وحدة إدارية مقارنة ج"),
                ("RENT-NR-ADM-QA-04", 3_100.0, 125.0, "إيجار وحدة إدارية مقارنة د"),
            ]
        elif subtype in ("basement_storage", "basement", "garage"):
            rents = [
                ("RENT-NR-BSM-QA-01", 950.0,  95.0,  "إيجار مخزن بدروم مقارنة أ"),
                ("RENT-NR-BSM-QA-02", 1_100.0, 110.0, "إيجار مخزن بدروم مقارنة ب"),
                ("RENT-NR-BSM-QA-03", 800.0,   80.0,  "إيجار مخزن بدروم مقارنة ج"),
            ]
        else:
            rents = [
                ("RENT-NR-GEN-QA-01", 2_000.0, 100.0, "إيجار عقار غير سكني مقارنة أ"),
                ("RENT-NR-GEN-QA-02", 2_200.0, 110.0, "إيجار عقار غير سكني مقارنة ب"),
            ]
        return [
            _ref(rid, "rental_reference", label + " — محاكاة QA", _SRC_QA,
                 city, district, class_key, subtype,
                 area=a, monthly_rent=round(m, 2), annual_rent=round(m * 12, 2),
                 rent_per_m2_month=round(m / a, 2),
                 evidence_quality="QA محاكاة", confidence=0.30, prod_ready=False, is_qa=True,
                 methods=["income_capitalization"], source_date=f"2024-0{i+1}-01",
                 notes=_QA_NOTE)
            for i, (rid, m, a, label) in enumerate(rents)
        ]

    # special_purpose (factory/industrial)
    return [
        _ref("RENT-SP-QA-01", "rental_reference",
             "إيجار منشأة صناعية مقارنة أ — محاكاة QA", _SRC_QA,
             city, district, class_key, subtype,
             area=2_000.0, monthly_rent=5_000.0, annual_rent=60_000.0,
             rent_per_m2_month=2.5,
             evidence_quality="QA محاكاة", confidence=0.25, prod_ready=False, is_qa=True,
             methods=["income_capitalization"],
             notes="المنشآت الصناعية نادرًا ما تُقيَّم بطريقة الرسملة — " + _QA_NOTE),
    ]


# ── Market transaction references ─────────────────────────────────────────────

def _build_transaction_references(
    payload: dict, class_key: str, subtype: str, district: str, city: str, is_qa: bool
) -> list[dict]:
    if not is_qa:
        return [_ref(
            "TRANS-PROD-PLACEHOLDER", "market_transaction_reference",
            "معاملة سوقية — مطلوب توثيق", _SRC_DOC,
            city, district, class_key, subtype,
            evidence_quality="غير متاح", confidence=0.0, prod_ready=False, is_qa=False,
            methods=["sales_comparison"],
            notes="يحتاج استكمال بيانات معاملات سوقية موثقة",
        )]

    area = float(payload.get("area") or 0) or None

    if class_key == "residential":
        a_ref = area or 350.0
        txns = [
            ("TXN-RES-QA-01", a_ref,       1_500_000.0, "2024-01", "سعر طلب"),
            ("TXN-RES-QA-02", a_ref * 1.1, 1_750_000.0, "2023-11", "بيع فعلي"),
            ("TXN-RES-QA-03", a_ref * 0.9, 1_200_000.0, "2023-09", "بيع فعلي"),
        ]
        return [
            _ref(rid, "market_transaction_reference",
                 f"معاملة فيلا {dt} — محاكاة QA", _SRC_QA,
                 city, district, class_key, subtype,
                 area=a, value=v, price_per_m2=round(v / a, 2),
                 evidence_quality="QA محاكاة", confidence=0.30, prod_ready=False, is_qa=True,
                 methods=["sales_comparison"],
                 source_date=dt + "-01",
                 notes=f"نوع المعاملة: {ttype} — " + _QA_NOTE)
            for i, (rid, a, v, dt, ttype) in enumerate(txns)
        ]

    if class_key == "non_residential":
        if subtype in ("shop", "mall_unit"):
            txns = [
                ("TXN-NR-SHOP-QA-01", 80.0,  320_000.0, "2024-02", "بيع فعلي"),
                ("TXN-NR-SHOP-QA-02", 90.0,  378_000.0, "2023-12", "بيع فعلي"),
                ("TXN-NR-SHOP-QA-03", 70.0,  266_000.0, "2023-10", "سعر طلب"),
            ]
        elif subtype in ("admin_unit", "office"):
            txns = [
                ("TXN-NR-ADM-QA-01", 120.0, 360_000.0, "2024-01", "بيع فعلي"),
                ("TXN-NR-ADM-QA-02", 130.0, 403_000.0, "2023-12", "بيع فعلي"),
                ("TXN-NR-ADM-QA-03", 110.0, 319_000.0, "2023-10", "سعر طلب"),
                ("TXN-NR-ADM-QA-04", 125.0, 375_000.0, "2023-08", "بيع فعلي"),
            ]
        elif subtype in ("basement_storage", "basement"):
            txns = [
                ("TXN-NR-BSM-QA-01", 95.0,  114_000.0, "2024-01", "بيع فعلي"),
                ("TXN-NR-BSM-QA-02", 110.0, 132_000.0, "2023-11", "بيع فعلي"),
                ("TXN-NR-BSM-QA-03", 80.0,   88_000.0, "2023-08", "سعر طلب"),
            ]
        else:
            txns = [
                ("TXN-NR-GEN-QA-01", 100.0, 300_000.0, "2024-01", "بيع فعلي"),
                ("TXN-NR-GEN-QA-02", 110.0, 341_000.0, "2023-10", "بيع فعلي"),
            ]
        return [
            _ref(rid, "market_transaction_reference",
                 f"معاملة {dt} — محاكاة QA", _SRC_QA,
                 city, district, class_key, subtype,
                 area=a, value=v, price_per_m2=round(v / a, 2),
                 evidence_quality="QA محاكاة", confidence=0.30, prod_ready=False, is_qa=True,
                 methods=["sales_comparison"],
                 source_date=dt + "-01",
                 notes=f"نوع المعاملة: {ttype} — " + _QA_NOTE)
            for i, (rid, a, v, dt, ttype) in enumerate(txns)
        ]

    # special_purpose
    a_ref = area or 2_500.0
    return [
        _ref("TXN-SP-QA-01", "market_transaction_reference",
             "معاملة منشأة صناعية أ — محاكاة QA", _SRC_QA,
             city, district, class_key, subtype,
             area=a_ref, value=a_ref * 800.0, price_per_m2=800.0,
             evidence_quality="QA محاكاة", confidence=0.25, prod_ready=False, is_qa=True,
             methods=["sales_comparison"],
             notes="المنشآت الصناعية نادرة في السوق — " + _QA_NOTE),
        _ref("TXN-SP-QA-02", "market_transaction_reference",
             "معاملة منشأة صناعية ب — محاكاة QA", _SRC_QA,
             city, district, class_key, subtype,
             area=a_ref * 0.8, value=a_ref * 0.8 * 750.0, price_per_m2=750.0,
             evidence_quality="QA محاكاة", confidence=0.25, prod_ready=False, is_qa=True,
             methods=["sales_comparison"],
             notes=_QA_NOTE),
    ]


# ── Land price references ─────────────────────────────────────────────────────

def _build_land_price_references(
    payload: dict, class_key: str, subtype: str, district: str, city: str, is_qa: bool
) -> list[dict]:
    if not is_qa:
        return [_ref(
            "LAND-PROD-PLACEHOLDER", "land_price_reference",
            "سعر الأرض — وثيقة رسمية مطلوبة", _SRC_OFFICIAL,
            city, district, class_key, subtype,
            evidence_quality="غير متاح", confidence=0.0, prod_ready=False, is_qa=False,
            methods=["cost"],
            notes="يحتاج بيانات رسمية لسعر الأرض — من الجهات المختصة أو خبير مرخص",
        )]

    payload_land = float(payload.get("cost_per_sqm_land") or 0)

    if class_key == "residential":
        land_prices = [
            ("LAND-RES-QA-01", payload_land or 3_000.0, "سعر أرض سكنية منطقة مقارنة أ"),
            ("LAND-RES-QA-02", (payload_land or 3_000.0) * 1.05, "سعر أرض سكنية منطقة مقارنة ب"),
            ("LAND-RES-QA-03", (payload_land or 3_000.0) * 0.95, "سعر أرض سكنية منطقة مقارنة ج"),
        ]
    elif class_key == "non_residential":
        if subtype in ("shop", "mall_unit"):
            base = payload_land or 5_000.0
        elif subtype in ("basement_storage", "basement"):
            base = 0.0  # accessory — land share = 0
        else:
            base = payload_land or 4_000.0
        if base == 0.0:
            return [_ref(
                "LAND-BSM-QA-01", "land_price_reference",
                "حصة بدروم من الأرض — صفر (ملحق)", _SRC_QA,
                city, district, class_key, subtype,
                land_price_per_m2=0.0,
                evidence_quality="QA محاكاة", confidence=0.50, prod_ready=False, is_qa=True,
                methods=["cost"],
                notes="المخزن البدروم ملحق — لا حصة منفصلة في الأرض — " + _QA_NOTE,
            )]
        land_prices = [
            ("LAND-NR-QA-01", base,          "سعر أرض غير سكنية أ"),
            ("LAND-NR-QA-02", base * 1.08,   "سعر أرض غير سكنية ب"),
            ("LAND-NR-QA-03", base * 0.93,   "سعر أرض غير سكنية ج"),
        ]
    else:  # special_purpose
        base = payload_land or 300.0
        land_prices = [
            ("LAND-SP-QA-01", base,        "سعر أرض صناعية أ — منطقة صناعية"),
            ("LAND-SP-QA-02", base * 1.10, "سعر أرض صناعية ب — منطقة صناعية"),
        ]

    return [
        _ref(rid, "land_price_reference", label + " — محاكاة QA", _SRC_QA,
             city, district, class_key, subtype,
             land_price_per_m2=price,
             evidence_quality="QA محاكاة", confidence=0.30, prod_ready=False, is_qa=True,
             methods=["cost"],
             notes=_QA_NOTE)
        for rid, price, label in land_prices
    ]


# ── Adjustment factor references ──────────────────────────────────────────────

def _build_adjustment_factor_references(
    payload: dict, class_key: str, subtype: str, is_qa: bool
) -> list[dict]:
    city = payload.get("city") or payload.get("governorate") or "غير محدد"
    district = payload.get("district") or city
    prod_ready = False

    base = [
        _ref("ADJ-TIME-QA-01", "adjustment_factor_reference",
             "تعديل الزمن (سنوي)", _SRC_QA if is_qa else _SRC_EXPERT,
             city, district, class_key, subtype,
             adj_type="time_adjustment", adj_value=1.05,
             evidence_quality="QA محاكاة" if is_qa else "يحتاج خبير",
             confidence=0.35 if is_qa else 0.4, prod_ready=prod_ready, is_qa=is_qa,
             methods=["sales_comparison"],
             notes="تعديل +5% سنويًا — افتراض QA" if is_qa else "يحتاج تأكيد الخبير"),
        _ref("ADJ-LOC-QA-01", "location_factor_reference",
             "معامل الموقع", _SRC_QA if is_qa else _SRC_EXPERT,
             city, district, class_key, subtype,
             adj_type="location_adjustment", adj_value=1.00,
             evidence_quality="QA محاكاة" if is_qa else "يحتاج خبير",
             confidence=0.35 if is_qa else 0.4, prod_ready=prod_ready, is_qa=is_qa,
             methods=["sales_comparison"],
             notes="معامل موقع = 1.00 (نفس المنطقة)" if is_qa else "يحتاج تقييم الموقع"),
    ]

    if class_key == "non_residential":
        base.append(_ref(
            "ADJ-FLOOR-QA-01", "floor_factor_reference",
            "معامل الدور", _SRC_QA if is_qa else _SRC_EXPERT,
            city, district, class_key, subtype,
            adj_type="floor_factor",
            adj_value=float(payload.get("floor_adjustment_factor") or 0.85),
            evidence_quality="QA محاكاة" if is_qa else "يحتاج خبير",
            confidence=0.40 if is_qa else 0.5, prod_ready=prod_ready, is_qa=is_qa,
            methods=["cost", "sales_comparison", "income_capitalization"],
            notes="معامل الدور حسب الجدول المرجعي — " + _QA_NOTE if is_qa else _SRC_EXPERT,
        ))

    if subtype in ("shop", "mall_unit"):
        base.append(_ref(
            "ADJ-FRONT-QA-01", "frontage_factor_reference",
            "معامل الواجهة", _SRC_QA if is_qa else _SRC_EXPERT,
            city, district, class_key, subtype,
            adj_type="frontage_factor", adj_value=1.00,
            evidence_quality="QA محاكاة" if is_qa else "يحتاج خبير",
            confidence=0.40 if is_qa else 0.5, prod_ready=prod_ready, is_qa=is_qa,
            methods=["cost", "sales_comparison"],
            notes="واجهة غير مُحددة — معامل = 1.00 افتراضي QA" if is_qa else _SRC_EXPERT,
        ))

    return base


# ── Prior valuation report links ──────────────────────────────────────────────

def _build_prior_report_links_registry(
    payload: dict, class_key: str, subtype: str, is_qa: bool
) -> list[dict]:
    district = payload.get("district") or payload.get("governorate") or "غير محدد"

    # QA simulation: show 1-2 synthetic prior reports
    if is_qa:
        links: list[dict] = []
        if class_key in ("residential", "non_residential"):
            links.append({
                "linked_report_id":       "PRIOR-MKT-QA-01",
                "report_type":            "market_valuation_report",
                "report_date":            "2023-09-01",
                "valuation_date":         "2023-08-01",
                "district":               district,
                "zone_id":                "QA-ZONE-01",
                "property_class":         class_key,
                "indicated_market_value": float(payload.get("expert_indicated_value") or 0) or 500_000.0,
                "indicated_rental_value": float(payload.get("estimated_market_rental_value") or 0) or 90_000.0,
                "rent_per_m2":            round((float(payload.get("estimated_market_rental_value") or 0) or 90_000.0) / max(float(payload.get("area") or 1), 1) / 12, 2),
                "value_per_m2":           float(payload.get("cost_per_sqm_building") or 2_000.0),
                "source_status":          "محاكاة QA — تقرير داخلي تاريخي",
                "usable_for_tax_appeal":  True,
                "limitations":            "التقرير بتاريخ 2023 — يحتاج تعديل زمني",
                "expert_review_required": True,
            })
        if class_key == "non_residential":
            links.append({
                "linked_report_id":       "PRIOR-RENT-QA-01",
                "report_type":            "rental_valuation_report",
                "report_date":            "2023-06-01",
                "valuation_date":         "2023-05-01",
                "district":               district,
                "zone_id":                "QA-ZONE-01",
                "property_class":         class_key,
                "indicated_market_value": None,
                "indicated_rental_value": float(payload.get("estimated_market_rental_value") or 0) or 36_000.0,
                "rent_per_m2":            round((float(payload.get("estimated_market_rental_value") or 0) or 36_000.0) / max(float(payload.get("area") or 1), 1) / 12, 2),
                "value_per_m2":           None,
                "source_status":          "محاكاة QA — تقرير إيجاري تاريخي",
                "usable_for_tax_appeal":  True,
                "limitations":            "يُستخدم كمرجع داعم فقط — ليس كبديل لتقييم ضريبي رسمي",
                "expert_review_required": True,
            })
        return links

    # Production: placeholder
    return [{
        "linked_report_id":       "PRIOR-PROD-PLACEHOLDER",
        "report_type":            "prior_valuation_report_reference",
        "report_date":            _GAP,
        "valuation_date":         _GAP,
        "district":               district,
        "zone_id":                _GAP,
        "property_class":         class_key,
        "indicated_market_value": None,
        "indicated_rental_value": None,
        "rent_per_m2":            None,
        "value_per_m2":           None,
        "source_status":          "لا يوجد تقرير سابق مُرتبط — يمكن إضافته عند الاستكمال",
        "usable_for_tax_appeal":  False,
        "limitations":            "لا بيانات سابقة — يحتاج رفع تقارير تقييم سابقة",
        "expert_review_required": True,
    }]


# ── Reference versioning ──────────────────────────────────────────────────────

def _build_reference_versioning(is_qa: bool) -> dict:
    return {
        "reference_version_id":  "REF-V1-QA-2024" if is_qa else "REF-V1-PENDING",
        "created_at":            "2024-01-01",
        "updated_at":            "2024-06-01",
        "source_snapshot_date":  "2024-06-01",
        "applicable_period":     "2024",
        "reference_version":     "1.0",
        "confidence_score":      0.30 if is_qa else 0.0,
        "evidence_quality":      "QA محاكاة" if is_qa else "غير متاح",
        "review_status":         "محاكاة QA — لم تتم مراجعة رسمية" if is_qa else "يحتاج استكمال",
        "notes": (
            "هذا الإصدار يحتوي على بيانات محاكاة QA فقط — "
            "يحتاج استبدالها بمراجع موثقة قبل الاستخدام الإنتاجي"
            if is_qa else
            "لا توجد بيانات مرجعية مُحمَّلة — يحتاج استكمال"
        ),
    }


# ── Depreciation references ───────────────────────────────────────────────────

_DEP_MODELS: dict[str, dict] = {
    "residential": {
        "economic_life_years": 60,
        "annual_depreciation_rate": round(1 / 60, 6),
        "depreciation_method": "straight_line",
        "max_allowed_rate": 0.80,
    },
    "non_residential": {
        "economic_life_years": 50,
        "annual_depreciation_rate": 0.02,
        "depreciation_method": "straight_line",
        "max_allowed_rate": 0.80,
    },
    "special_purpose": {
        "economic_life_years": 30,
        "annual_depreciation_rate": round(1 / 30, 6),
        "depreciation_method": "straight_line",
        "max_allowed_rate": 0.85,
    },
    "basement_storage": {
        "economic_life_years": 50,
        "annual_depreciation_rate": 0.02,
        "depreciation_method": "straight_line",
        "max_allowed_rate": 0.80,
    },
}

_DEP_CLASS_MAP: dict[str, str] = {
    "residential":     "residential",
    "non_residential": "non_residential",
    "special_purpose": "special_purpose",
}

_DEP_SUBTYPE_OVERRIDE: dict[str, str] = {
    "basement_storage": "basement_storage",
    "basement":         "basement_storage",
}


def _build_depreciation_reference_entry(
    class_key: str, subtype: str, payload: dict, is_qa: bool
) -> dict:
    dep_key = _DEP_SUBTYPE_OVERRIDE.get(subtype) or _DEP_CLASS_MAP.get(class_key, "non_residential")
    model = _DEP_MODELS.get(dep_key, _DEP_MODELS["non_residential"])

    effective_age = None
    age_raw = payload.get("age_years") or payload.get("effective_age")
    if age_raw is not None:
        try:
            effective_age = float(age_raw)
        except (ValueError, TypeError):
            effective_age = None

    eco_life = model["economic_life_years"]
    ann_rate = model["annual_depreciation_rate"]
    max_rate = model["max_allowed_rate"]

    if effective_age is not None and effective_age > 0:
        acc_rate = min(effective_age * ann_rate, max_rate)
        age_gap = False
    else:
        acc_rate = None
        age_gap = True

    # Ain Shams override for factory
    ain_shams_applied = False
    ain_shams_note = ""
    if class_key == "special_purpose" and subtype in ("factory", "industrial_facility", "industrial"):
        ain_shams_applied = True
        ain_shams_note = (
            "إرشادات تكلفة مصانع جامعة عين شمس (مبدئية) — لا تتضمن عمرًا إنتاجيًا صريحًا. "
            "المعدل المستخدم (1/30) مبني على ممارسة مهنية لا على الدراسة المبدئية. "
            "يحتاج مراجعة الخبير."
        )

    return {
        "reference_id":              f"DEP-{dep_key.upper()}-QA-01" if is_qa else f"DEP-{dep_key.upper()}-PROD",
        "reference_type":            "depreciation_reference",
        "property_class":            class_key,
        "property_subtype":          subtype,
        "depreciation_key":          dep_key,
        "economic_life_years":       eco_life,
        "annual_depreciation_rate":  ann_rate,
        "depreciation_method":       model["depreciation_method"],
        "max_allowed_accumulated":   max_rate,
        "effective_age_years":       effective_age,
        "accumulated_depreciation":  round(acc_rate, 4) if acc_rate is not None else None,
        "effective_age_missing":     age_gap,
        "effective_age_gap_note":    "العمر الفعلي غير مُقدَّم — لا يمكن حساب الإهلاك المتراكم" if age_gap else "",
        "source_status":             _SRC_QA if is_qa else _SRC_EXPERT,
        "expert_override_allowed":   True,
        "ain_shams_guidance_applied": ain_shams_applied,
        "ain_shams_note":            ain_shams_note,
        "production_ready":          False,
        "qa_simulation":             is_qa,
        "notes": (
            f"نموذج الإهلاك: {dep_key} — {eco_life} سنة عمر اقتصادي — معدل سنوي {ann_rate:.4f}"
            + (" — " + _QA_NOTE if is_qa else " — يحتاج توثيق من خبير")
        ),
    }


# ── Official price placeholder ────────────────────────────────────────────────

def _build_official_price_placeholder(class_key: str, subtype: str, city: str, district: str) -> dict:
    return _ref(
        "OFFICIAL-PRICE-PLACEHOLDER", "official_price_placeholder",
        "سعر رسمي — مطلوب من جهة رسمية", _SRC_OFFICIAL,
        city, district, class_key, subtype,
        evidence_quality="غير متاح", confidence=0.0, prod_ready=False, is_qa=False,
        methods=["cost", "tax_comparison"],
        notes="يحتاج قيمة رسمية من الجهات المختصة (مصلحة الضرائب العقارية / جهاز التعمير)",
    )


# ── Future Qdrant placeholder ─────────────────────────────────────────────────

def _build_qdrant_placeholder(class_key: str, subtype: str, city: str, district: str) -> dict:
    return _ref(
        "QDRANT-FUTURE-PLACEHOLDER", "future_qdrant_reference_placeholder",
        "Qdrant — مرجع مستقبلي", _SRC_QDRANT,
        city, district, class_key, subtype,
        evidence_quality="غير متاح — مرحلة مستقبلية", confidence=0.0,
        prod_ready=False, is_qa=False,
        methods=[],
        notes="سيُفعَّل بعد بناء قاعدة بيانات Qdrant وإدخال البيانات وتحديد نطاق البحث",
    )


# ── Main registry builder ─────────────────────────────────────────────────────

def _build_tax_reference_registry(payload: dict) -> dict:
    """Build the internal reference registry for tax appeal calculations.

    Returns:
        dict with rental_references, transaction_references, land_price_references,
        adjustment_factor_references, prior_report_links, source_confidence_summary,
        registry_status, reference_versioning, depreciation_reference
    """
    is_qa = bool(payload.get("_qa_simulation"))
    class_key, subtype = _resolve_class(payload)
    city     = payload.get("city") or payload.get("governorate") or "غير محدد"
    district = payload.get("district") or city

    rental_refs       = _build_rental_references(payload, class_key, subtype, district, city, is_qa)
    transaction_refs  = _build_transaction_references(payload, class_key, subtype, district, city, is_qa)
    land_price_refs   = _build_land_price_references(payload, class_key, subtype, district, city, is_qa)
    adj_factor_refs   = _build_adjustment_factor_references(payload, class_key, subtype, is_qa)
    prior_links       = _build_prior_report_links_registry(payload, class_key, subtype, is_qa)
    dep_ref           = _build_depreciation_reference_entry(class_key, subtype, payload, is_qa)
    versioning        = _build_reference_versioning(is_qa)

    all_data_refs = rental_refs + transaction_refs + land_price_refs + adj_factor_refs
    qa_count      = sum(1 for r in all_data_refs if "QA" in str(r.get("source_status", "")))
    prod_count    = sum(1 for r in all_data_refs if r.get("production_ready"))
    missing_count = sum(1 for r in all_data_refs if "مطلوب" in str(r.get("source_status", "")))

    source_confidence = {
        "total_references":       len(all_data_refs),
        "qa_simulation_count":    qa_count,
        "production_ready_count": prod_count,
        "missing_count":          missing_count,
        "overall_confidence":     "محاكاة QA — غير جاهز للإنتاج" if is_qa else "يحتاج استكمال مراجع موثقة",
        "production_ready":       not is_qa and prod_count > 0,
        "qdrant_active":          False,
        "internet_active":        False,
        "ocr_active":             False,
    }

    return {
        "rental_references":          rental_refs,
        "transaction_references":     transaction_refs,
        "land_price_references":      land_price_refs,
        "adjustment_factor_references": adj_factor_refs,
        "prior_report_links":         prior_links,
        "depreciation_reference":     dep_ref,
        "source_confidence_summary":  source_confidence,
        "reference_versioning":       versioning,
        "registry_status": {
            "qdrant_ready":   True,
            "qdrant_active":  False,
            "internet_active": False,
            "ocr_active":     False,
            "status_ar":      "سجل داخلي — Qdrant/الإنترنت/OCR غير مفعل",
            "version":        "v1.0",
        },
    }
