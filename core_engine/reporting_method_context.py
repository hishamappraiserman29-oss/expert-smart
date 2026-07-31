# -*- coding: utf-8 -*-
"""
reporting_method_context.py — Valuation method/context helpers.

Extracted from shared_request_routes.py (refactor Step 1).
Contains deterministic, pure-Python helpers for valuation purpose detection,
date-basis classification, and full method context assembly.

No Flask, no storage I/O, no PDF rendering.
No external API calls. No live data retrieval.
"""
from __future__ import annotations

# ── Valuation purpose + date-basis helpers ───────────────────────────────────

_RENTAL_PURPOSE_LABELS = {
    "القيمة الإيجارية", "قيمة إيجارية", "تقدير الإيجار",
    "القيمة الإيجارية السوقية", "market rent", "rental value",
}


def _detect_valuation_purpose(payload: dict) -> dict:
    """Detect valuation purpose from payload; return structured purpose info dict."""
    purpose_raw   = str(payload.get("purpose") or "").strip()
    purpose_lower = purpose_raw.lower()

    if purpose_lower in {s.lower() for s in _RENTAL_PURPOSE_LABELS}:
        return {
            "purpose_key":                "rental_value",
            "purpose_label_ar":           "القيمة الإيجارية",
            "requires_rental_pages":      True,
            "requires_capital_value_pages": False,
            "requires_income_pages":      True,
        }
    if purpose_lower in {"القيمة السوقية", "قيمة سوقية", "market value"}:
        return {
            "purpose_key":                "market_value",
            "purpose_label_ar":           "القيمة السوقية",
            "requires_rental_pages":      False,
            "requires_capital_value_pages": True,
            "requires_income_pages":      False,
        }
    if purpose_lower in {"قيمة استثمارية", "investment value"}:
        return {
            "purpose_key":                "investment_value",
            "purpose_label_ar":           "القيمة الاستثمارية",
            "requires_rental_pages":      False,
            "requires_capital_value_pages": True,
            "requires_income_pages":      True,
        }
    if purpose_lower in {"تمويل", "رهن", "financing", "mortgage"}:
        return {
            "purpose_key":                "financing",
            "purpose_label_ar":           "غرض التمويل / الرهن",
            "requires_rental_pages":      False,
            "requires_capital_value_pages": True,
            "requires_income_pages":      False,
        }
    if purpose_lower in {"تقاضي", "قضائي", "litigation", "court"}:
        return {
            "purpose_key":                "litigation",
            "purpose_label_ar":           "غرض التقاضي / القضاء",
            "requires_rental_pages":      False,
            "requires_capital_value_pages": True,
            "requires_income_pages":      False,
        }
    if purpose_lower in {"ضريبي", "طعن ضريبي", "tax", "appeal", "tax appeal"}:
        return {
            "purpose_key":                "tax",
            "purpose_label_ar":           "الغرض الضريبي / الطعن",
            "requires_rental_pages":      False,
            "requires_capital_value_pages": True,
            "requires_income_pages":      False,
        }
    if purpose_lower in {"أفضل استخدام", "hbu", "highest and best use"}:
        return {
            "purpose_key":                "hbu",
            "purpose_label_ar":           "أفضل وأعلى استخدام (HBU)",
            "requires_rental_pages":      False,
            "requires_capital_value_pages": True,
            "requires_income_pages":      True,
        }
    if purpose_lower in {"قيمة عادلة", "ifrs", "fair value"}:
        return {
            "purpose_key":                "ifrs",
            "purpose_label_ar":           "القيمة العادلة (IFRS)",
            "requires_rental_pages":      False,
            "requires_capital_value_pages": True,
            "requires_income_pages":      True,
        }
    # Default: market value (also covers blank / unknown)
    return {
        "purpose_key":                "market_value",
        "purpose_label_ar":           purpose_raw or "القيمة السوقية",
        "requires_rental_pages":      False,
        "requires_capital_value_pages": True,
        "requires_income_pages":      False,
    }


def _detect_valuation_date_basis(valuation_date: str, report_date: str) -> dict:
    """Classify valuation date relative to report date.

    Returns dict with date_basis_key, date_basis_label_ar, date_basis_notes.
    Threshold: >60 days before report → retrospective; >30 days after → prospective.
    """
    _RETRO = (
        "تم إعداد التقييم على أساس تاريخ تقييم سابق، ويجب أن تعكس البيانات والتحليلات "
        "الظروف السوقية المتاحة أو المفترضة في ذلك التاريخ."
    )
    _CURRENT = (
        "تم إعداد التقييم على أساس تاريخ تقييم حالي قريب من تاريخ التقرير."
    )
    _PROSP = (
        "تم إعداد التقييم على أساس تاريخ مستقبلي، وتعتمد النتيجة على افتراضات "
        "مستقبلية قابلة للتغير."
    )
    try:
        from datetime import date as _date
        vd = _date.fromisoformat(str(valuation_date).strip()[:10])
        rd = _date.fromisoformat(str(report_date).strip()[:10])
        delta = (rd - vd).days          # positive = valuation is in the past
        if delta > 60:
            return {"date_basis_key": "retrospective",
                    "date_basis_label_ar": "تقييم بأثر سابق",
                    "date_basis_notes":    _RETRO}
        if delta < -30:
            return {"date_basis_key": "prospective",
                    "date_basis_label_ar": "تقييم مستقبلي",
                    "date_basis_notes":    _PROSP}
        return {"date_basis_key": "current",
                "date_basis_label_ar": "تقييم حالي",
                "date_basis_notes":    _CURRENT}
    except Exception:
        return {"date_basis_key": "unknown",
                "date_basis_label_ar": "غير محدد",
                "date_basis_notes":    "لم يتم تحديد أساس تاريخ التقييم."}


# ── Valuation method context builder (comparables, income, DCF, cost) ────────

def _build_method_context(payload: dict) -> dict:
    """Build comparable matrix, income, DCF, cost, land, AVM regression context from payload.

    If payload["_qa_simulation"] is True, synthetic QA numbers are used
    for manual review output generation only. All synthetic data is labelled
    as such — not claimed as real market evidence.
    """
    is_qa = bool(payload.get("_qa_simulation"))
    area = float(payload.get("area") or 120)
    land_share_area = float(payload.get("land_share_area") or 35)

    # Standard data-gap labels (used across all non-QA paths)
    _DATA_GAP     = "غير متاح ضمن بيانات الطلب"
    _EXPERT_FILL  = "يحتاج استكمال بواسطة الخبير"
    _NA_PURPOSE   = "غير مطبق لهذا الغرض"

    # Purpose and date-basis detection (deterministic, no live calls)
    purpose_info    = _detect_valuation_purpose(payload)
    _val_date_raw   = str(payload.get("valuation_date") or "").strip()[:10]
    _rep_date_raw   = str(payload.get("report_date")    or "2026-06-24")[:10]
    date_basis_info = _detect_valuation_date_basis(_val_date_raw, _rep_date_raw)
    _is_rental      = (purpose_info["purpose_key"] == "rental_value")

    # ── Subject geographic identification (from payload or QA defaults) ──────
    # QA fallback uses location field to distinguish Nasr City vs Maadi vs Zamalek vs generic
    _qa_loc_hint      = str(payload.get("district") or payload.get("location") or "")
    _qa_is_nasr       = is_qa and "نصر"   in _qa_loc_hint
    _qa_is_maadi      = is_qa and "معادي" in _qa_loc_hint
    _qa_is_zamalek    = is_qa and "زمالك" in _qa_loc_hint
    subject_zone_id    = (
        payload.get("zone_id") or (
            "ZONE-CAI-NASR-08"    if _qa_is_nasr
            else "ZONE-CAI-MAADI-01"   if _qa_is_maadi
            else "ZONE-CAI-ZAMALEK-01" if _qa_is_zamalek
            else "ZONE-CAI-NASR-08"    if is_qa   # generic QA default → Nasr City
            else "غير محدد"
        )
    )
    subject_district   = (
        payload.get("district") or (
            "مدينة نصر"  if _qa_is_nasr
            else "المعادي"  if _qa_is_maadi
            else "الزمالك"  if _qa_is_zamalek
            else "مدينة نصر" if is_qa   # generic QA default
            else _DATA_GAP
        )
    )
    subject_city       = payload.get("city")        or ("القاهرة" if is_qa else _DATA_GAP)
    subject_sub_market = payload.get("sub_market") or (
        "سوق المعادي الفرعي"        if _qa_is_maadi
        else "سوق الزمالك الفرعي"   if _qa_is_zamalek
        else "سوق مدينة نصر الفرعي" if is_qa
        else _DATA_GAP
    )
    subject_location_label = f"{subject_district}، {subject_city}"
    _GEO_DISCLAIMER = (
        "تمت مطابقة المقارنات مع نطاق العقار محل التقييم وفق كود المنطقة / السوق الفرعي. "
        "أي مقارن خارج النطاق يظهر للمراجعة فقط ولا يدخل في الاستنتاج."
    )

    def _fmt_int(v, suffix=" ج.م"):
        try:
            return f"{int(float(str(v))):,}{suffix}" if v else ""
        except (TypeError, ValueError):
            return str(v) if v else ""

    def _fmt_pct(v):
        try:
            return f"{float(str(v)):.1f}%"
        except (TypeError, ValueError):
            return str(v) if v else ""

    # Defaults for non-QA paths
    avg_land_price_str = ""
    land_value_by_sales_str = ""
    land_value_by_sales = 0
    land_comps: list = []
    land_extraction_ctx: dict = {}
    land_value_reconciled = ""
    land_value_expert_selected = ""
    cost_breakdown: list = []
    cost_breakdown_total = ""
    cost_breakdown_grand_total = 0.0
    discount_rate_methods: list = []
    dr_average = ""
    dr_expert_selected = ""
    dr_notes = ""
    terminal_cap_methods: list = []
    tc_average = ""
    tc_expert_selected = ""
    tc_notes = ""
    avm_regression: list = []
    avm_reg_base_value = ""
    avm_reg_coeff_total = ""
    avm_reg_predicted = ""
    avm_reg_residual = ""
    avm_reg_final = ""
    avm_reg_confidence_band = ""
    avm_reg_limitations = ""

    # ── New data-binding structures (defaults for non-QA) ─────────────────
    price_source_data: list = []
    mass_appraisal_bridge: dict = {
        "mass_run_id":               _DATA_GAP,
        "mass_zone_id":              _DATA_GAP,
        "mass_average_price_per_m2": _DATA_GAP,
        "mass_model_value":          _DATA_GAP,
        "mass_confidence_range":     _DATA_GAP,
        "mass_data_quality_score":   _DATA_GAP,
        "mass_source_coverage":      _DATA_GAP,
        "mass_appraisal_status": (
            "لم يتم ربط هذا التقرير بنتيجة تقييم جماعي فعلية في هذه المرحلة. "
            "تم استخدام محاكاة داخلية لأغراض QA."
        ),
        "linked_to_report_methods":  _DATA_GAP,
    }
    cap_rate_derivation: dict = {}
    rental_value_context: dict = {}

    # ── Map/aerial image placeholders (no external API calls) ────────────────
    _coords_raw = str(payload.get("coordinates") or "")
    _lat_val, _lon_val = None, None
    if _coords_raw and "," in _coords_raw:
        try:
            _cparts = _coords_raw.split(",", 1)
            _lat_val = float(_cparts[0].strip())
            _lon_val = float(_cparts[1].strip())
        except (ValueError, TypeError):
            pass
    _has_coords = (_lat_val is not None and _lon_val is not None)

    map_ctx = {
        "subject_map_image_available":     False,
        "subject_aerial_image_available":  False,
        "comparables_map_image_available": False,
        "has_coordinates":                 _has_coords,
        "latitude":                        round(_lat_val, 6) if _has_coords else _DATA_GAP,
        "longitude":                       round(_lon_val, 6) if _has_coords else _DATA_GAP,
        "coordinate_source":               payload.get("coordinate_source") or (
            "مدخل يدوي" if _has_coords else _DATA_GAP
        ),
        "coordinate_confidence":           "متوسط" if _has_coords else _DATA_GAP,
        "map_placeholder_text": (
            f"خريطة موقع العقار — إحداثيات: {_lat_val:.4f}°N، {_lon_val:.4f}°E ({subject_location_label})"
            if _has_coords
            else "لم يتم إدخال إحداثيات العقار. يلزم استكمالها لإظهار خريطة دقيقة."
        ),
        "aerial_placeholder_text": (
            f"صورة جوية للعقار — الموقع: {subject_location_label}"
            if subject_location_label and _DATA_GAP not in subject_location_label
            else "صورة جوية للعقار — الموقع غير محدد. يُضيف الخبير يدوياً."
        ),
        "comps_map_placeholder_text": (
            "خريطة توزيع المقارنات الجغرافية — تُعرض المقارنات المُدرجة والمستبعدة جغرافياً"
        ),
        "map_image_types": [
            {"type": "خريطة موقع العقار",     "available": False, "notes": "يُضيف الخبير يدوياً"},
            {"type": "صورة جوية للعقار",       "available": False, "notes": "يُضيف الخبير يدوياً"},
            {"type": "خريطة توزيع المقارنات", "available": False, "notes": "يُضيف الخبير يدوياً"},
            {"type": "صور المقارنات",          "available": False, "notes": "يُضيف الخبير يدوياً"},
        ],
        "map_disclaimer": (
            "لا تتضمن هذه النسخة جلب خرائط أو صور جوية من الإنترنت أو Google Maps أو OSM أو Mapbox. "
            "يُضيف الخبير الصور والخرائط يدوياً عند الحاجة."
        ),
    }

    # ── Pre-compute replacement cost (for land extraction + cost approach consistency) ──
    # Both sections must reference the same base cost; computed once here.
    if is_qa:
        _pcr_area     = area
        _pcr_indirect = round(_pcr_area * 1_000)
        _pcr_direct   = (
            _pcr_area * (1_500 + 450 + 300 + 400 + 200 + 400 + 300 + 300)
            + _pcr_indirect
        )  # = area * 3_850 + area * 1_000 = area * 4_850 simplified
        _pcr_contingency   = int(_pcr_direct * 0.10)
        _qa_repl_cost_new  = _pcr_direct + _pcr_contingency
    else:
        _qa_repl_cost_new  = 0

    # ── Comparable matrix ─────────────────────────────────────────────────
    comparables_raw = payload.get("comparables")
    if comparables_raw and isinstance(comparables_raw, list) and len(comparables_raw) >= 2:
        comparables = comparables_raw
        avg_adj = ""
    else:
        # ── Zone-aware QA comparables: derive from subject district ────────
        _is_maadi_subject   = is_qa and ("معادي" in subject_district)
        _is_zamalek_subject = is_qa and ("زمالك" in subject_district)
        _is_nasr_subject    = is_qa and ("نصر"   in subject_district)
        if _is_maadi_subject:
            _SYNTH_COMPS = [
                {"num": 1, "location": f"{subject_district} - شارع النيل",
                 "area": 160, "sale_price": 4_000_000, "price_per_m2": 25_000,
                 "location_factor": 1.00, "area_factor": 1.01,
                 "condition_factor": 1.00, "finishing_factor": 1.02, "time_factor": 1.00,
                 "status": "مباع", "notes": "مقارن مباشر — نفس المنطقة",
                 "reliability_score": "عالية", "inclusion": "مُدرَج",
                 "comparable_zone_id": subject_zone_id, "comparable_district": subject_district,
                 "geo_match_status": "مطابق",
                 "geo_match_notes": "نفس المنطقة والسوق الفرعي — مُدرَج في الحسابات"},
                {"num": 2, "location": f"{subject_district} - شارع 9",
                 "area": 175, "sale_price": 4_200_000, "price_per_m2": 24_000,
                 "location_factor": 1.01, "area_factor": 0.99,
                 "condition_factor": 1.00, "finishing_factor": 1.01, "time_factor": 1.00,
                 "status": "مباع", "notes": "نفس المنطقة — تسوية موقع +1%",
                 "reliability_score": "عالية", "inclusion": "مُدرَج",
                 "comparable_zone_id": subject_zone_id, "comparable_district": subject_district,
                 "geo_match_status": "مطابق",
                 "geo_match_notes": "نفس المنطقة — مُدرَج في الحسابات"},
                {"num": 3, "location": f"{subject_district} - سعد زغلول",
                 "area": 195, "sale_price": 4_680_000, "price_per_m2": 24_000,
                 "location_factor": 1.02, "area_factor": 0.99,
                 "condition_factor": 1.00, "finishing_factor": 1.00, "time_factor": 1.00,
                 "status": "مباع", "notes": "شارع رئيسي — تسوية موقع +2%",
                 "reliability_score": "متوسطة", "inclusion": "مُدرَج",
                 "comparable_zone_id": subject_zone_id, "comparable_district": subject_district,
                 "geo_match_status": "مطابق",
                 "geo_match_notes": "نفس المنطقة — مُدرَج في الحسابات"},
                {"num": 4, "location": "مدينة نصر - المنطقة الثامنة",
                 "area": 150, "sale_price": 3_450_000, "price_per_m2": 23_000,
                 "location_factor": 1.00, "area_factor": 1.00,
                 "condition_factor": 1.00, "finishing_factor": 1.00, "time_factor": 1.00,
                 "status": "مباع", "notes": "مقارن مرجعي خارج النطاق — غير مستخدم في الاستنتاج",
                 "reliability_score": "منخفضة", "inclusion": "مستبعد جغرافيًا",
                 "comparable_zone_id": "ZONE-CAI-NASR-08", "comparable_district": "مدينة نصر",
                 "geo_match_status": "خارج النطاق",
                 "geo_match_notes": "مستبعد جغرافيًا — يُعرض للمراجعة فقط ولا يدخل في الاستنتاج"},
            ]
        elif _is_zamalek_subject:
            # ── Zamalek luxury market: 4 in-zone + 1 excluded audit row ──
            _SYNTH_COMPS = [
                {"num": 1, "location": "الزمالك - شارع أبو الفدا",
                 "area": 140, "sale_price": 4_900_000, "price_per_m2": 35_000,
                 "location_factor": 1.00, "area_factor": 1.01,
                 "condition_factor": 1.02, "finishing_factor": 1.03, "time_factor": 1.00,
                 "status": "مباع", "notes": "مقارن مباشر — شقة فاخرة على شارع النيل",
                 "reliability_score": "عالية", "inclusion": "مُدرَج",
                 "comparable_zone_id": "ZONE-CAI-ZAMALEK-01", "comparable_district": "الزمالك",
                 "geo_match_status": "مطابق",
                 "geo_match_notes": "نفس المنطقة والسوق الفرعي — مُدرَج في الحسابات"},
                {"num": 2, "location": "الزمالك - شارع البرازيل",
                 "area": 165, "sale_price": 5_610_000, "price_per_m2": 34_000,
                 "location_factor": 1.01, "area_factor": 0.99,
                 "condition_factor": 1.00, "finishing_factor": 1.02, "time_factor": 1.00,
                 "status": "مباع", "notes": "منطقة الزمالك الشمالية — تسوية موقع +1%",
                 "reliability_score": "عالية", "inclusion": "مُدرَج",
                 "comparable_zone_id": "ZONE-CAI-ZAMALEK-01", "comparable_district": "الزمالك",
                 "geo_match_status": "مطابق",
                 "geo_match_notes": "نفس المنطقة — مُدرَج في الحسابات"},
                {"num": 3, "location": "الزمالك - شارع محمد مظهر",
                 "area": 155, "sale_price": 5_580_000, "price_per_m2": 36_000,
                 "location_factor": 1.02, "area_factor": 1.00,
                 "condition_factor": 0.99, "finishing_factor": 1.01, "time_factor": 1.00,
                 "status": "مباع", "notes": "موقع متميز — تسوية حالة −1%",
                 "reliability_score": "عالية", "inclusion": "مُدرَج",
                 "comparable_zone_id": "ZONE-CAI-ZAMALEK-01", "comparable_district": "الزمالك",
                 "geo_match_status": "مطابق",
                 "geo_match_notes": "نفس المنطقة — مُدرَج في الحسابات"},
                {"num": 4, "location": "الزمالك - شارع طه حسين",
                 "area": 145, "sale_price": 5_365_000, "price_per_m2": 37_000,
                 "location_factor": 1.03, "area_factor": 1.01,
                 "condition_factor": 1.01, "finishing_factor": 1.00, "time_factor": 1.00,
                 "status": "مباع", "notes": "شارع هادئ — تسوية موقع +3%",
                 "reliability_score": "متوسطة", "inclusion": "مُدرَج",
                 "comparable_zone_id": "ZONE-CAI-ZAMALEK-01", "comparable_district": "الزمالك",
                 "geo_match_status": "مطابق",
                 "geo_match_notes": "نفس المنطقة — مُدرَج في الحسابات"},
                {"num": 5, "location": "مدينة نصر - المنطقة الثامنة",
                 "area": 150, "sale_price": 3_450_000, "price_per_m2": 23_000,
                 "location_factor": 1.00, "area_factor": 1.00,
                 "condition_factor": 1.00, "finishing_factor": 1.00, "time_factor": 1.00,
                 "status": "مباع",
                 "notes": "مستبعد جغرافيًا — غير مستخدم في الحساب",
                 "reliability_score": "منخفضة",
                 "inclusion": "مستبعد جغرافيًا — غير مستخدم في الحساب",
                 "comparable_zone_id": "ZONE-CAI-NASR-08", "comparable_district": "مدينة نصر",
                 "geo_match_status": "خارج النطاق",
                 "geo_match_notes": "مستبعد جغرافيًا — يُعرض للمراجعة فقط ولا يدخل في الاستنتاج"},
            ]
        elif is_qa:
            _SYNTH_COMPS = [
                {"num": 1, "location": "مدينة نصر - المنطقة الثامنة", "area": 115,
                 "sale_price": 2_875_000, "price_per_m2": 25_000,
                 "location_factor": 1.00, "area_factor": 1.01,
                 "condition_factor": 0.98, "finishing_factor": 1.03, "time_factor": 1.00,
                 "status": "مباع", "notes": "مقارن مباشر — نفس المنطقة",
                 "reliability_score": "عالية", "inclusion": "مُدرَج",
                 "comparable_zone_id": subject_zone_id, "comparable_district": subject_district,
                 "geo_match_status": "مطابق",
                 "geo_match_notes": "نفس المنطقة — مُدرَج في الحسابات"},
                {"num": 2, "location": "مدينة نصر - المنطقة السابعة", "area": 130,
                 "sale_price": 3_120_000, "price_per_m2": 24_000,
                 "location_factor": 1.02, "area_factor": 0.99,
                 "condition_factor": 1.00, "finishing_factor": 1.02, "time_factor": 1.01,
                 "status": "مباع", "notes": "منطقة مجاورة — تسوية موقع +2%",
                 "reliability_score": "متوسطة", "inclusion": "مُدرَج",
                 "comparable_zone_id": subject_zone_id, "comparable_district": subject_district,
                 "geo_match_status": "مطابق",
                 "geo_match_notes": "منطقة مجاورة — مُدرَج في الحسابات"},
                {"num": 3, "location": "مدينة نصر - المنطقة التاسعة", "area": 110,
                 "sale_price": 2_530_000, "price_per_m2": 23_000,
                 "location_factor": 1.03, "area_factor": 1.02,
                 "condition_factor": 1.01, "finishing_factor": 1.04, "time_factor": 1.00,
                 "status": "مباع", "notes": "منطقة مجاورة — تسوية موقع +3%",
                 "reliability_score": "متوسطة", "inclusion": "مُدرَج",
                 "comparable_zone_id": subject_zone_id, "comparable_district": subject_district,
                 "geo_match_status": "مطابق",
                 "geo_match_notes": "منطقة مجاورة — مُدرَج في الحسابات"},
                {"num": 4, "location": "مدينة نصر - شارع جانبي", "area": 125,
                 "sale_price": 2_875_000, "price_per_m2": 23_000,
                 "location_factor": 1.05, "area_factor": 1.00,
                 "condition_factor": 1.00, "finishing_factor": 1.03, "time_factor": 1.01,
                 "status": "معروض", "notes": "شارع جانبي — تسوية موقع +5%",
                 "reliability_score": "منخفضة", "inclusion": "مُدرَج للإرشاد",
                 "comparable_zone_id": subject_zone_id, "comparable_district": subject_district,
                 "geo_match_status": "مطابق",
                 "geo_match_notes": "نطاق فرعي — مُدرَج للإرشاد"},
            ]
        else:
            _SYNTH_COMPS = [
                {"num": i, "location": "—", "area": "—", "sale_price": "—",
                 "price_per_m2": "—", "location_factor": "—", "area_factor": "—",
                 "condition_factor": "—", "finishing_factor": "—", "time_factor": "—",
                 "adjusted_price_per_m2": "—", "adjusted_value": "—",
                 "status": "يحتاج استكمال", "notes": "يُعبأ بواسطة الخبير",
                 "reliability_score": "—", "inclusion": "—",
                 "comparable_zone_id": "—", "geo_match_status": "—",
                 "geo_match_notes": "—"}
                for i in range(1, 5)
            ]
        comparables = _SYNTH_COMPS

    adj_prices = []           # only geo-matched (or untagged) comparables
    adj_prices_excluded = []  # out-of-zone — shown but not in calculation
    for comp in comparables:
        _geo_ok = comp.get("geo_match_status", "مطابق") not in ("خارج النطاق",)
        try:
            ppm2 = float(comp["price_per_m2"])
            adj = (ppm2
                   * float(comp.get("location_factor", 1))
                   * float(comp.get("area_factor", 1))
                   * float(comp.get("condition_factor", 1))
                   * float(comp.get("finishing_factor", 1))
                   * float(comp.get("time_factor", 1)))
            adj_val = adj * area
            gross_adj_pct = (
                abs(float(comp.get("location_factor", 1)) - 1) +
                abs(float(comp.get("area_factor", 1)) - 1) +
                abs(float(comp.get("condition_factor", 1)) - 1) +
                abs(float(comp.get("finishing_factor", 1)) - 1) +
                abs(float(comp.get("time_factor", 1)) - 1)
            ) * 100
            net_adj_pct = (adj / ppm2 - 1) * 100 if ppm2 else 0
            comp["adjusted_price_per_m2"] = (
                f"{adj:,.0f} ج.م/م²" if _geo_ok else "مستبعد جغرافيًا"
            )
            comp["adjusted_value"] = (
                f"{adj_val:,.0f} ج.م" if _geo_ok else "مستبعد جغرافيًا"
            )
            comp["sale_price"] = (
                f"{int(comp['sale_price']):,} ج.م"
                if isinstance(comp["sale_price"], (int, float))
                else comp["sale_price"]
            )
            comp["price_per_m2"]  = f"{int(ppm2):,} ج.م/م²"
            comp["gross_adj_pct"] = f"{gross_adj_pct:.1f}%" if _geo_ok else "—"
            comp["net_adj_pct"]   = f"{net_adj_pct:+.1f}%"  if _geo_ok else "—"
            if _geo_ok:
                adj_prices.append(adj)
            else:
                adj_prices_excluded.append(adj)
        except (TypeError, ValueError):
            pass

    if adj_prices:
        avg_adj_val = sum(adj_prices) / len(adj_prices)
        avg_adj = f"{avg_adj_val:,.0f} ج.م/م²"
        sales_from_comps = int(avg_adj_val * area)
        sales_from_comps_str = f"{sales_from_comps:,} ج.م"
    else:
        avg_adj = ""
        sales_from_comps_str = ""

    # ── Land sales comparison — zone-aware (2 in-zone + 1 out-of-zone for audit) ──
    if is_qa:
        if _qa_is_maadi:
            _LAND_COMPS_ALL = [
                {"num": 1, "location": "المعادي - شارع 9", "zone_id": "ZONE-CAI-MAADI-01",
                 "area_m2": 40, "offer_date": "03/2026", "total_price": 600_000,
                 "price_per_m2": 15_000, "location_factor": 1.00, "area_factor": 1.00,
                 "time_factor": 1.00, "notes": "أرض بيضاء في المعادي — في نطاق العقار"},
                {"num": 2, "location": "المعادي - شارع 5", "zone_id": "ZONE-CAI-MAADI-01",
                 "area_m2": 35, "offer_date": "01/2026", "total_price": 508_200,
                 "price_per_m2": 14_520, "location_factor": 1.02, "area_factor": 1.01,
                 "time_factor": 1.00,
                 "notes": "منطقة مجاورة داخل المعادي — تسوية موقع +2%"},
                {"num": 3, "location": "مدينة نصر - المنطقة الثامنة",
                 "zone_id": "ZONE-CAI-NASR-08", "area_m2": 38,
                 "offer_date": "03/2026", "total_price": 380_000, "price_per_m2": 10_000,
                 "location_factor": 1.00, "area_factor": 1.01, "time_factor": 1.00,
                 "notes": "خارج النطاق — يظهر للمراجعة فقط"},
            ]
        elif _qa_is_zamalek:
            # Zamalek has premium land prices
            _LAND_COMPS_ALL = [
                {"num": 1, "location": "الزمالك - شارع النيل", "zone_id": "ZONE-CAI-ZAMALEK-01",
                 "area_m2": 30, "offer_date": "03/2026", "total_price": 2_250_000,
                 "price_per_m2": 75_000, "location_factor": 1.00, "area_factor": 1.00,
                 "time_factor": 1.00,
                 "notes": "نصيب أرض شقة فاخرة على النيل — نفس النطاق"},
                {"num": 2, "location": "الزمالك - شارع الجيزة", "zone_id": "ZONE-CAI-ZAMALEK-01",
                 "area_m2": 25, "offer_date": "01/2026", "total_price": 1_800_000,
                 "price_per_m2": 72_000, "location_factor": 1.02, "area_factor": 1.01,
                 "time_factor": 1.00,
                 "notes": "نطاق الزمالك الجنوبي — تسوية موقع +2%"},
                {"num": 3, "location": "مدينة نصر - المنطقة الثامنة",
                 "zone_id": "ZONE-CAI-NASR-08", "area_m2": 38,
                 "offer_date": "03/2026", "total_price": 380_000, "price_per_m2": 10_000,
                 "location_factor": 1.00, "area_factor": 1.01, "time_factor": 1.00,
                 "notes": "خارج النطاق — مستبعد جغرافيًا"},
            ]
        else:
            # Generic QA (Nasr City / rental scenario)
            _LAND_COMPS_ALL = [
                {"num": 1, "location": "مدينة نصر - المنطقة الثامنة",
                 "zone_id": "ZONE-CAI-NASR-08", "area_m2": 38,
                 "offer_date": "03/2026", "total_price": 380_000, "price_per_m2": 10_000,
                 "location_factor": 1.00, "area_factor": 1.01, "time_factor": 1.00,
                 "notes": "أرض بيضاء نفس المنطقة"},
                {"num": 2, "location": "مدينة نصر - المنطقة التاسعة",
                 "zone_id": "ZONE-CAI-NASR-08", "area_m2": 42,
                 "offer_date": "01/2026", "total_price": 390_600, "price_per_m2": 9_300,
                 "location_factor": 1.03, "area_factor": 0.99, "time_factor": 1.01,
                 "notes": "منطقة مجاورة — تسوية موقع +3%"},
                {"num": 3, "location": "مدينة نصر - شارع مدبولي",
                 "zone_id": "ZONE-CAI-NASR-08", "area_m2": 32,
                 "offer_date": "02/2026", "total_price": 307_200, "price_per_m2": 9_600,
                 "location_factor": 1.02, "area_factor": 1.02, "time_factor": 1.00,
                 "notes": "قطعة أرض داخل المبنى — نصيب من المشاع"},
            ]

        # Tag each comp with geo_match_status; only in-zone comps enter the average
        adj_land_prices = []
        for lc in _LAND_COMPS_ALL:
            _lc_in_zone = lc.get("zone_id", "") == subject_zone_id
            lc["geo_match_status"]    = "مطابق" if _lc_in_zone else "خارج النطاق"
            lc["geo_exclusion_reason"] = (
                "" if _lc_in_zone
                else f"نطاق {lc.get('zone_id', '')} يختلف عن نطاق العقار {subject_zone_id}"
            )
            lc["total_price_disp"]  = f"{int(lc['total_price']):,} ج.م"
            lc["price_per_m2_disp"] = f"{int(lc['price_per_m2']):,} ج.م/م²"
            if _lc_in_zone:
                adj_l = (lc["price_per_m2"]
                         * lc["location_factor"]
                         * lc["area_factor"]
                         * lc["time_factor"])
                lc["adj_price_per_m2"] = f"{adj_l:,.0f} ج.م/م²"
                lc["land_share_value"] = f"{int(adj_l * land_share_area):,} ج.م"
                adj_land_prices.append(adj_l)
            else:
                lc["adj_price_per_m2"] = "مستبعد جغرافيًا"
                lc["land_share_value"] = "مستبعد جغرافيًا"

        land_comps = _LAND_COMPS_ALL
        avg_land_price = sum(adj_land_prices) / len(adj_land_prices) if adj_land_prices else 0
        land_value_by_sales = int(avg_land_price * land_share_area)
        avg_land_price_str = f"{avg_land_price:,.0f} ج.م/م²"
        land_value_by_sales_str = f"{land_value_by_sales:,} ج.م"

        # Land extraction method — calibrated to subject zone.
        # replacement_cost_new is taken from the pre-computed cost breakdown total
        # (_qa_repl_cost_new) to ensure طريقة التكلفة and قيمة الأرض use the same basis.
        replacement_cost_new = _qa_repl_cost_new if _qa_repl_cost_new else (
            810_000 if _qa_is_maadi else 720_000
        )
        if _qa_is_maadi:
            improved_indication = 3_600_000
        elif _qa_is_zamalek:
            improved_indication = 5_300_000
        else:
            improved_indication = 3_055_500
        depreciation_pct     = 25.0
        depr_amount          = replacement_cost_new * depreciation_pct / 100
        depr_imprv_value     = replacement_cost_new - depr_amount
        extracted_land_val   = improved_indication - depr_imprv_value
        extracted_land_per_m2 = extracted_land_val / land_share_area if land_share_area else 0
        land_extraction_ctx = {
            "extr_improved_indication":  f"{improved_indication:,} ج.م",
            "extr_replacement_cost_new": f"{replacement_cost_new:,} ج.م",
            "extr_depreciation_pct":     f"{depreciation_pct:.1f}%",
            "extr_depr_amount":          f"{depr_amount:,.0f} ج.م",
            "extr_depr_imprv_value":     f"{depr_imprv_value:,.0f} ج.م",
            "extr_land_value":           f"{extracted_land_val:,.0f} ج.م",
            "extr_land_per_m2":          f"{extracted_land_per_m2:,.0f} ج.م/م²",
            "extr_land_share_value":     f"{int(extracted_land_per_m2 * land_share_area):,} ج.م",
        }
        extr_val = int(extracted_land_per_m2 * land_share_area)
        land_value_avg_n = (land_value_by_sales + extr_val) / 2
        land_value_reconciled = f"{int(land_value_avg_n):,} ج.م"
        land_value_expert_selected = land_value_reconciled

    # ── Shared land value — subject's proportional share (Part C) ────────
    _tbsa = float(payload.get("total_building_sellable_area") or 0)
    if _tbsa > 0:
        _land_share_ratio = round(area / _tbsa, 4)
    else:
        _land_share_ratio = float(payload.get("land_share_ratio") or (
            round(area / 1_000, 4) if is_qa else 0
        ))
    _land_share_ratio_pct = f"{_land_share_ratio:.2%}" if _land_share_ratio else _EXPERT_FILL
    # Subject's share of land area (m²)
    _land_area_total = float(payload.get("land_area") or (land_share_area if is_qa else 0))
    _subj_land_share_area = round(_land_share_ratio * _land_area_total, 2) if (
        _land_share_ratio and _land_area_total
    ) else 0
    _subj_land_share_area_str = (
        f"{_subj_land_share_area:.2f} م²" if _subj_land_share_area else _EXPERT_FILL
    )
    # Reconciled land value for subject's share
    try:
        _land_val_num = float(
            str(land_value_expert_selected).replace(",", "").replace(" ج.م", "").strip()
        )
    except (ValueError, TypeError):
        _land_val_num = 0
    _rec_subj_land_share_val = (
        round(_land_val_num * _land_share_ratio) if (_land_val_num and _land_share_ratio) else 0
    )
    _rec_subj_land_share_val_str = (
        f"{_rec_subj_land_share_val:,} ج.م" if _rec_subj_land_share_val else _EXPERT_FILL
    )
    shared_land_ctx = {
        "total_building_sellable_area":    f"{_tbsa:,.0f} م²" if _tbsa else _EXPERT_FILL,
        "land_share_ratio":                _land_share_ratio_pct,
        "subject_land_share_area":         _subj_land_share_area_str,
        "reconciled_subject_land_share_value": _rec_subj_land_share_val_str,
        "expert_selected_subject_land_value":  _EXPERT_FILL,
        "shared_land_basis_notes": (
            "نصيب العقار المُقيَّم من قيمة الأرض يُحتسب بنسبة مساحته إلى إجمالي "
            "المساحات القابلة للبيع في المبنى (land_share_ratio × land_value_reconciled)."
        ),
    }

    # ── Building cost breakdown ───────────────────────────────────────────
    if is_qa:
        _cost_area = area  # bound to payload area — never hardcode
        _indirect  = round(_cost_area * 1_000)  # indirect costs scale with area
        _COST_ITEMS_RAW = [
            ("أعمال الهيكل الخرساني",   "م²",     _cost_area, 1_500, "هيكل خرساني مسلح"),
            ("أعمال المباني والطوب",     "م²",     _cost_area,   450, "حوائط وفواصل"),
            ("أعمال البياض والتلبيس",    "م²",     _cost_area,   300, "بياض داخلي وخارجي"),
            ("أعمال الأرضيات",          "م²",     _cost_area,   400, "سيراميك متوسط"),
            ("أعمال الدهانات",          "م²",     _cost_area,   200, "دهانات داخلية"),
            ("أعمال الكهرباء",          "م²",     _cost_area,   400, "تمديدات كهربائية كاملة"),
            ("أعمال السباكة والصرف",    "م²",     _cost_area,   300, "تمديدات ميه وصرف"),
            ("أعمال النجارة/الألوميتال", "م²",     _cost_area,   300, "أبواب وشبابيك"),
            ("مصاريف غير مباشرة",       "إجمالي", 1,      _indirect, "إشراف وإدارة وترخيص"),
        ]
        total_direct = sum(item[2] * item[3] for item in _COST_ITEMS_RAW)
        contingency = int(total_direct * 0.10)
        grand_total = total_direct + contingency
        for item_name, unit, qty, unit_cost, note in _COST_ITEMS_RAW:
            row_total = qty * unit_cost
            cost_breakdown.append({
                "item":       item_name,
                "unit":       unit,
                "qty":        str(qty),
                "unit_cost":  f"{unit_cost:,}",
                "total_cost": f"{row_total:,}",
                "pct":        f"{row_total / grand_total * 100:.1f}%",
                "notes":      note,
            })
        cost_breakdown.append({
            "item":       "هامش واحتياطي (10%)",
            "unit":       "—",
            "qty":        "—",
            "unit_cost":  "—",
            "total_cost": f"{contingency:,}",
            "pct":        f"{contingency / grand_total * 100:.1f}%",
            "notes":      "احتياطي طوارئ",
        })
        cost_breakdown_grand_total = grand_total
        cost_breakdown_total = f"{grand_total:,} ج.م"

    # ── Income approach ───────────────────────────────────────────────────
    monthly_rent      = float(payload.get("income_monthly_rent") or (9_000 if is_qa else 0))
    annual_gross      = monthly_rent * 12 if monthly_rent else 0
    vac_rate          = float(payload.get("income_vacancy_rate") or (5.0 if is_qa else 0))
    vac_amt           = annual_gross * vac_rate / 100 if annual_gross else 0
    coll_loss_pct     = float(payload.get("income_collection_loss_rate") or (2.0 if is_qa else 0))
    coll_loss         = annual_gross * coll_loss_pct / 100 if annual_gross else 0
    egi               = annual_gross - vac_amt - coll_loss
    exp_rate          = float(payload.get("income_expense_rate") or (10.0 if is_qa else 0))
    expenses          = egi * exp_rate / 100 if egi else 0
    reserve_pct       = float(payload.get("income_reserve_rate") or (3.0 if is_qa else 0))
    reserve           = egi * reserve_pct / 100 if egi else 0
    noi               = egi - expenses - reserve
    cap_rate_pct      = float(payload.get("income_cap_rate") or (3.8 if is_qa else 0))
    income_value_calc = (noi / (cap_rate_pct / 100)) if cap_rate_pct and noi else 0

    income_ctx: dict = {}
    if monthly_rent or is_qa:
        income_ctx = {
            "income_monthly_rent":        _fmt_int(monthly_rent),
            "income_annual_gross":        _fmt_int(annual_gross),
            "income_vacancy_rate":        _fmt_pct(vac_rate),
            "income_vacancy_amt":         _fmt_int(vac_amt),
            "income_collection_loss_pct": _fmt_pct(coll_loss_pct),
            "income_collection_loss":     _fmt_int(coll_loss),
            "income_egi":                 _fmt_int(egi),
            "income_expense_rate":        _fmt_pct(exp_rate),
            "income_expenses":            _fmt_int(expenses),
            "income_reserve_pct":         _fmt_pct(reserve_pct),
            "income_reserve":             _fmt_int(reserve),
            "income_noi":                 _fmt_int(noi),
            "income_cap_rate_pct":        _fmt_pct(cap_rate_pct),
            "income_value_calc":          _fmt_int(income_value_calc),
        }

    # ── Part F: Pre-compute rental comparison NOI for DCF alignment ──────────
    # For rental-purpose reports the DCF base NOI must come from the market
    # rental comparables (computed later in rental_value_context), not from the
    # capital-yield income approach.  We pre-compute it here from the same QA
    # comp data so the DCF cash-flow rows are internally consistent.
    _rental_comp_noi_for_dcf: float = 0.0
    _dcf_noi_basis: str = "income_approach"
    if _is_rental:
        _r_mo_payload = float(payload.get("final_monthly_rental_value") or 0)
        if _r_mo_payload:
            _rental_comp_noi_for_dcf = _r_mo_payload * 12 * 0.93
            _dcf_noi_basis = "rental_comparison_payload"
        elif is_qa:
            _r_area_pre = float(payload.get("area") or 150)
            if _qa_is_maadi:
                _r_rents_pre = [
                    (9_500  / 170) * (1.00 * 1.01 * 1.00 * 1.00 * 1.00),
                    (10_200 / 185) * (1.02 * 0.99 * 1.00 * 1.01 * 1.00),
                    (8_800  / 160) * (1.01 * 1.02 * 0.99 * 1.00 * 1.00),
                ]
            else:
                _r_rents_pre = [
                    (9_200  / 115) * (1.00 * 1.01 * 0.98 * 1.03 * 1.00),
                    (10_400 / 130) * (1.02 * 0.99 * 1.00 * 1.00 * 1.00),
                    (7_560  / 108) * (1.03 * 1.02 * 1.01 * 1.03 * 1.00),
                    (10_000 / 125) * (1.05 * 0.99 * 1.00 * 1.02 * 1.01),
                ]
            _r_avg_rpsm_pre             = sum(_r_rents_pre) / len(_r_rents_pre)
            _rental_comp_noi_for_dcf    = _r_avg_rpsm_pre * _r_area_pre * 12 * 0.93
            _dcf_noi_basis              = "rental_comparison_qa"

    # ── DCF (5-year expanded) ─────────────────────────────────────────────
    dcf_rows: list = []
    dcf_ctx: dict  = {}
    if is_qa or payload.get("dcf_discount_rate"):
        if _is_rental and _rental_comp_noi_for_dcf:
            base_noi = _rental_comp_noi_for_dcf
        else:
            base_noi = noi if noi else (float(payload.get("income_noi") or 0))
        growth_rate   = float(payload.get("dcf_growth_rate") or 5.0) / 100
        discount_rate = float(payload.get("dcf_discount_rate") or 13.0) / 100
        term_cap_rate = float(payload.get("dcf_terminal_cap_rate") or 4.5) / 100
        capex_pct     = float(payload.get("dcf_capex_pct") or 2.0) / 100
        if not base_noi:
            base_noi = 92_340 if is_qa else 0
        current_noi = base_noi
        pv_cf_total = 0.0
        for yr in range(1, 6):
            df_yr = (1 + discount_rate) ** yr
            denom = 1 - exp_rate / 100 - vac_rate / 100 - coll_loss_pct / 100
            gross_income_yr = current_noi / denom if denom > 0 else current_noi * 1.15
            vac_coll_yr     = gross_income_yr * (vac_rate + coll_loss_pct) / 100
            egi_yr          = gross_income_yr - vac_coll_yr
            exp_yr          = egi_yr * exp_rate / 100
            capex_yr        = gross_income_yr * capex_pct
            net_cf_yr       = current_noi - capex_yr
            pv_yr           = net_cf_yr / df_yr
            pv_cf_total    += pv_yr
            dcf_rows.append({
                "year":            f"السنة {yr}",
                "gross_income":    f"{gross_income_yr:,.0f} ج.م",
                "vac_collection":  f"{vac_coll_yr:,.0f} ج.م",
                "egi":             f"{egi_yr:,.0f} ج.م",
                "expenses":        f"{exp_yr:,.0f} ج.م",
                "noi":             f"{current_noi:,.0f} ج.م",
                "capex":           f"{capex_yr:,.0f} ج.م",
                "net_cashflow":    f"{net_cf_yr:,.0f} ج.م",
                "discount_factor": f"{1/df_yr:.4f}",
                "pv":              f"{pv_yr:,.0f} ج.م",
            })
            current_noi *= (1 + growth_rate)

        term_noi         = current_noi
        terminal_value   = term_noi / term_cap_rate if term_cap_rate else 0
        df5              = (1 + discount_rate) ** 5
        sell_cost_pct    = float(payload.get("dcf_selling_costs_pct") or 2.0) / 100
        net_terminal     = terminal_value * (1 - sell_cost_pct)
        pv_terminal      = net_terminal / df5
        dcf_total        = pv_cf_total + pv_terminal
        dcf_ctx = {
            "dcf_rows":              dcf_rows,
            "dcf_base_noi":          f"{base_noi:,.0f} ج.م",
            "dcf_noi_basis":         _dcf_noi_basis,
            "dcf_pv_cashflows":      f"{pv_cf_total:,.0f} ج.م",
            "dcf_terminal_noi":      f"{term_noi:,.0f} ج.م",
            "dcf_terminal_value":    f"{terminal_value:,.0f} ج.م",
            "dcf_selling_costs_pct": _fmt_pct(sell_cost_pct * 100),
            "dcf_net_terminal":      f"{net_terminal:,.0f} ج.م",
            "dcf_pv_terminal":       f"{pv_terminal:,.0f} ج.م",
            "dcf_value_calc":        f"{dcf_total:,.0f} ج.م",
            "dcf_discount_rate_pct": _fmt_pct(discount_rate * 100),
            "dcf_growth_rate_pct":   _fmt_pct(growth_rate * 100),
            "dcf_terminal_cap_pct":  _fmt_pct(term_cap_rate * 100),
        }

        # Discount rate derivation (4 methods) — QA synthetic assumptions
        if is_qa:
            discount_rate_methods = [
                {
                    "method": "أ. طريقة البناء التراكمي (Build-up)",
                    "components": [
                        ("معدل الخلو من المخاطر",        "6.0%"),
                        ("علاوة التضخم والمخاطر العامة", "3.0%"),
                        ("علاوة مخاطر العقار",           "2.0%"),
                        ("علاوة السيولة",                "1.5%"),
                        ("علاوة الإدارة/السوق",          "0.5%"),
                    ],
                    "indicated_rate": "13.0%",
                },
                {
                    "method": "ب. نموذج CAPM المبسط",
                    "components": [
                        ("معدل الخلو من المخاطر (Rf)",   "6.0%"),
                        ("بيتا العقار (β proxy)",        "0.85"),
                        ("علاوة مخاطر السوق (Rm−Rf)",   "7.0%"),
                        ("علاوة المخاطر المحددة",         "1.05%"),
                    ],
                    "indicated_rate": "13.0%",
                },
                {
                    "method": "ج. استخلاص عائد السوق",
                    "components": [
                        ("معدل الرسملة السوقي",          "3.8%"),
                        ("تسوية معدل النمو المتوقع",     "+5.0%"),
                        ("تسوية مخاطر خاصة",             "+4.2%"),
                    ],
                    "indicated_rate": "13.0%",
                },
                {
                    "method": "د. نموذج حزمة الاستثمار (Band-of-Investment)",
                    "components": [
                        ("نسبة الدين (60%)",             "60%"),
                        ("ثابت الرهن (MC)",              "9.0%"),
                        ("نسبة حقوق الملكية (40%)",      "40%"),
                        ("عائد حقوق الملكية (Ye)",       "19.0%"),
                    ],
                    "indicated_rate": "13.0%",
                },
            ]
            dr_average         = "13.0%"
            dr_expert_selected = "13.0%"
            dr_notes           = "محاكاة QA — لا تستند إلى مصادر سوقية حقيقية."
            terminal_cap_methods = [
                {"method": "أ. معدل رسملة السوق المباشر",          "description": "مشتق من مبيعات مقارنة مماثلة",             "indicated_rate": "4.0%"},
                {"method": "ب. معدل الخصم ناقص معدل النمو",        "description": "13.0% − 5.0% (مبسط)",                     "indicated_rate": "4.5%"},
                {"method": "ج. عائد الدخل من عقارات مقارنة",       "description": "افتراضات سوقية داخلية للمنطقة",             "indicated_rate": "4.3%"},
                {"method": "د. معدل الرسملة المستقر (Expert)",      "description": "تقدير الخبير بناءً على ظروف السوق",         "indicated_rate": "4.7%"},
            ]
            tc_average         = "4.4%"
            tc_expert_selected = "4.5%"
            tc_notes           = "محاكاة QA — جميع المعدلات افتراضية."

    # ── Cost approach ─────────────────────────────────────────────────────
    cost_ctx: dict = {}
    if is_qa or payload.get("land_share_value") or payload.get("replacement_cost_per_m2"):
        if is_qa and land_value_reconciled:
            try:
                land_val = int(str(land_value_reconciled).replace(",", "").replace(" ج.م", "").strip())
            except Exception:
                land_val = 910_000
        else:
            land_val = float(payload.get("land_share_value") or (910_000 if is_qa else 0))

        if is_qa and cost_breakdown_grand_total:
            repl_total = cost_breakdown_grand_total
            repl_m2    = repl_total / area if area else 6_000
        else:
            repl_m2    = float(payload.get("replacement_cost_per_m2") or (6_000 if is_qa else 0))
            repl_total = repl_m2 * area

        phys_depr  = float(payload.get("physical_depreciation_rate") or (20.0 if is_qa else 0))
        func_depr  = float(payload.get("functional_depreciation_rate") or (5.0 if is_qa else 0))
        ext_depr   = float(payload.get("external_depreciation_rate") or 0.0)
        total_depr_pct = phys_depr + func_depr + ext_depr
        total_depr_amt = repl_total * total_depr_pct / 100
        depr_imprv     = repl_total - total_depr_amt
        cost_val       = land_val + depr_imprv
        cost_ctx = {
            "cost_land_value":           _fmt_int(land_val),
            "cost_replacement_per_m2":   _fmt_int(repl_m2, " ج.م/م²"),
            "cost_replacement_total":    _fmt_int(repl_total),
            "cost_physical_depr_pct":    _fmt_pct(phys_depr),
            "cost_functional_depr_pct":  _fmt_pct(func_depr),
            "cost_external_depr_pct":    _fmt_pct(ext_depr),
            "cost_total_depr_pct":       _fmt_pct(total_depr_pct),
            "cost_total_depr_amt":       _fmt_int(total_depr_amt),
            "cost_depreciated_imprv":    _fmt_int(depr_imprv),
            "cost_value_calc":           _fmt_int(cost_val),
        }

    # ── AVM regression-style analysis (QA simulation) ─────────────────────
    if is_qa:
        # Base price per m² and district label depend on scenario
        if _qa_is_zamalek:
            _avm_base_ppm2   = 35_000
            _avm_loc_label   = "الزمالك — سوق الشقق الفاخرة"
            _avm_cond_factor = 1.02
            _avm_cond_note   = "جيد جداً — تشطيب فاخر"
            _avm_fin_factor  = 1.05
            _avm_fin_note    = "تشطيب فاخر"
        elif _qa_is_maadi:
            _avm_base_ppm2   = 25_000
            _avm_loc_label   = "المعادي — سوق الشقق السكنية"
            _avm_cond_factor = 1.00
            _avm_cond_note   = "جيد جداً"
            _avm_fin_factor  = 1.03
            _avm_fin_note    = "تشطيب فاخر"
        else:
            _avm_base_ppm2   = 25_000
            _avm_loc_label   = "مدينة نصر — المنطقة الثامنة"
            _avm_cond_factor = 0.97
            _avm_cond_note   = "جيد بدلاً من ممتاز"
            _avm_fin_factor  = 1.05
            _avm_fin_note    = "تشطيب متوسط+"
        _avm_base_val    = _avm_base_ppm2 * area
        _avm_cond_effect = _avm_base_val * (_avm_cond_factor - 1)
        _avm_fin_effect  = _avm_base_val * _avm_cond_factor * (_avm_fin_factor - 1)
        _avm_predicted   = int(_avm_base_val * _avm_cond_factor * _avm_fin_factor * 0.98 * 1.005)
        _avm_residual    = int(_avm_base_val * 0.013)
        _avm_final       = _avm_predicted + _avm_residual
        _avm_band_low    = int(_avm_final * 0.90)
        _avm_band_high   = int(_avm_final * 1.10)
        avm_regression = [
            {"feature": "المساحة (م²)",               "value": str(int(area)),
             "coeff": f"{_avm_base_ppm2:,} ج.م/م²",
             "effect": f"{_avm_base_val:,.0f} ج.م",
             "notes": "القيمة الأساسية × المساحة"},
            {"feature": "معامل الموقع",                "value": "1.00",   "coeff": "+0.00%",
             "effect": "+0 ج.م",   "notes": _avm_loc_label},
            {"feature": "معامل الحالة",                "value": str(_avm_cond_factor),
             "coeff": f"{(_avm_cond_factor-1)*100:+.2f}%",
             "effect": f"{_avm_cond_effect:+,.0f} ج.م", "notes": _avm_cond_note},
            {"feature": "معامل التشطيب",               "value": str(_avm_fin_factor),
             "coeff": f"{(_avm_fin_factor-1)*100:+.2f}%",
             "effect": f"{_avm_fin_effect:+,.0f} ج.م", "notes": _avm_fin_note},
            {"feature": "معامل الدور/الإطلالة",         "value": "1.00",   "coeff": "+0.00%",
             "effect": "+0 ج.م",   "notes": "دور متوسط"},
            {"feature": "معامل العمر/الإهلاك",          "value": "0.98",   "coeff": "−2.00%",
             "effect": f"{int(_avm_base_val * _avm_cond_factor * _avm_fin_factor * -0.02):+,} ج.م",
             "notes": "عمر فعلي 8 سنوات"},
            {"feature": "معامل عرض الشارع/الواجهة",     "value": "1.005",  "coeff": "+0.50%",
             "effect": f"{int(_avm_base_val * _avm_cond_factor * _avm_fin_factor * 0.98 * 0.005):+,} ج.م",
             "notes": "شارع 12م — واجهة 8م"},
        ]
        avm_reg_base_value      = f"{_avm_base_val:,.0f} ج.م"
        avm_reg_coeff_total     = "+0.50%"
        avm_reg_predicted       = f"{_avm_predicted:,} ج.م"
        avm_reg_residual        = f"+{_avm_residual:,} ج.م (تعديل خبير)"
        avm_reg_final           = f"{_avm_final:,} ج.م"
        avm_reg_confidence_band = f"{_avm_band_low:,} — {_avm_band_high:,} ج.م"
        avm_reg_limitations     = (
            "تحليل AVM في هذه النسخة يستخدم محاكاة داخلية/مدخلات النظام لأغراض المراجعة "
            "ولا يمثل نموذجًا مدربًا على بيانات سوقية حقيقية ما لم يتم تفعيل Source Registry/Qdrant لاحقًا. "
            "لا يتضمن استرجاعًا من الإنترنت أو Qdrant."
        )

    # ── Price Source Spine (QA simulation) — scenario-specific ──────────────
    if is_qa:
        # Select price source parameters per scenario
        if _qa_is_zamalek:
            _psd_zone1       = "ZONE-CAI-ZAMALEK-01"
            _psd_dist1       = "الزمالك، القاهرة"
            _psd_ppm2_1      = "35,000 ج.م/م²"
            _psd_val1        = "5,250,000 ج.م"
            _psd_label1      = "تقييم جماعي — حي الزمالك Q1/2026"
            _psd_zone2       = "ZONE-CAI-ZAMALEK-01"
            _psd_dist2       = "الزمالك، القاهرة"
            _psd_ppm2_2      = "36,000 ج.م/م²"
            _psd_val2        = "5,040,000 ج.م"
            _psd_label2      = "مقارن يدوي — الزمالك شارع أبو الفدا"
            _psd_zone3       = "ZONE-CAI-ZAMALEK-01"
            _psd_dist3       = "الزمالك، القاهرة"
            _psd_ppm2_3      = "35,500 ج.م/م²"
            _psd_val3        = "5,325,000 ج.م"
            _psd_label3      = "سعر خبير — تقدير الزمالك الفاخر"
            _psd_land_zone   = "ZONE-CAI-ZAMALEK-01"
            _psd_land_dist   = "الزمالك، القاهرة"
            _psd_land_ppm2   = "75,000 ج.م/م²"
            _psd_land_val    = "2,250,000 ج.م"
            _psd_land_label  = "مقارن أرض — الزمالك شارع النيل"
            _psd_rent_zone   = "ZONE-CAI-ZAMALEK-01"
            _psd_rent_dist   = "الزمالك، القاهرة"
            _psd_rent_val    = "12,000 ج.م/شهر"
            _psd_rent_label  = "مؤشر إيجاري — شقة فاخرة الزمالك"
        elif _qa_is_maadi:
            _psd_zone1       = "ZONE-CAI-MAADI-01"
            _psd_dist1       = "المعادي، القاهرة"
            _psd_ppm2_1      = "25,000 ج.م/م²"
            _psd_val1        = "4,500,000 ج.م"
            _psd_label1      = "تقييم جماعي — حي المعادي Q1/2026"
            _psd_zone2       = "ZONE-CAI-NASR-08"
            _psd_dist2       = "مدينة نصر، القاهرة"
            _psd_ppm2_2      = "25,000 ج.م/م²"
            _psd_val2        = "2,875,000 ج.م"
            _psd_label2      = "مقارن يدوي — مدينة نصر المنطقة الثامنة"
            _psd_zone3       = "ZONE-CAI-MAADI-01"
            _psd_dist3       = "المعادي، القاهرة"
            _psd_ppm2_3      = "25,000 ج.م/م²"
            _psd_val3        = "4,500,000 ج.م"
            _psd_label3      = "سعر خبير — تقدير محلل المعادي"
            _psd_land_zone   = "ZONE-CAI-NASR-08"
            _psd_land_dist   = "مدينة نصر، القاهرة"
            _psd_land_ppm2   = "10,000 ج.م/م²"
            _psd_land_val    = "380,000 ج.م"
            _psd_land_label  = "مقارن أرض — مدينة نصر المنطقة الثامنة"
            _psd_rent_zone   = "ZONE-CAI-MAADI-01"
            _psd_rent_dist   = "المعادي، القاهرة"
            _psd_rent_val    = "9,000 ج.م/شهر"
            _psd_rent_label  = "مؤشر إيجاري — المعادي/مدينة نصر"
        else:
            # Nasr City / generic rental QA
            _psd_zone1       = "ZONE-CAI-NASR-08"
            _psd_dist1       = "مدينة نصر، القاهرة"
            _psd_ppm2_1      = "25,000 ج.م/م²"
            _psd_val1        = "3,000,000 ج.م"
            _psd_label1      = "تقييم جماعي — حي مدينة نصر Q1/2026"
            _psd_zone2       = "ZONE-CAI-NASR-08"
            _psd_dist2       = "مدينة نصر، القاهرة"
            _psd_ppm2_2      = "25,000 ج.م/م²"
            _psd_val2        = "2,875,000 ج.م"
            _psd_label2      = "مقارن يدوي — مدينة نصر المنطقة الثامنة"
            _psd_zone3       = "ZONE-CAI-NASR-08"
            _psd_dist3       = "مدينة نصر، القاهرة"
            _psd_ppm2_3      = "25,000 ج.م/م²"
            _psd_val3        = "3,000,000 ج.م"
            _psd_label3      = "سعر خبير — مدينة نصر"
            _psd_land_zone   = "ZONE-CAI-NASR-08"
            _psd_land_dist   = "مدينة نصر، القاهرة"
            _psd_land_ppm2   = "10,000 ج.م/م²"
            _psd_land_val    = "380,000 ج.م"
            _psd_land_label  = "مقارن أرض — مدينة نصر المنطقة الثامنة"
            _psd_rent_zone   = "ZONE-CAI-NASR-08"
            _psd_rent_dist   = "مدينة نصر، القاهرة"
            _psd_rent_val    = "9,000 ج.م/شهر"
            _psd_rent_label  = "مؤشر إيجاري — مدينة نصر"

        price_source_data = [
            {
                "source_registry_id": "SRC-QA-001",
                "source_type":        "mass_appraisal_zone",
                "source_label":       _psd_label1,
                "source_method":      "AVM / تقييم جماعي",
                "zone_id":            _psd_zone1,
                "district":           _psd_dist1,
                "property_class":     "شقة سكنية",
                "price_per_m2":       _psd_ppm2_1,
                "source_value":       _psd_val1,
                "source_date":        "01/2026",
                "source_confidence":  "متوسطة",
                "source_status":      "محاكاة QA",
                "source_notes":       "محاكاة داخلية — لا يوجد ربط فعلي بـ Source Registry",
                "used_in_methods":    "AVM، مقارنة البيوع، توفيق النتائج",
            },
            {
                "source_registry_id": "SRC-QA-002",
                "source_type":        "manual_comparable",
                "source_label":       _psd_label2,
                "source_method":      "مقارنة البيوع",
                "zone_id":            _psd_zone2,
                "district":           _psd_dist2,
                "property_class":     "شقة سكنية",
                "price_per_m2":       _psd_ppm2_2,
                "source_value":       _psd_val2,
                "source_date":        "03/2026",
                "source_confidence":  "عالية",
                "source_status":      "محاكاة QA",
                "source_notes":       "مقارن مباشر — يُستخدم في جدول مقارنة البيوع",
                "used_in_methods":    "مقارنة البيوع",
            },
            {
                "source_registry_id": "SRC-QA-003",
                "source_type":        "expert_entered_price",
                "source_label":       _psd_label3,
                "source_method":      "تقدير الخبير",
                "zone_id":            _psd_zone3,
                "district":           _psd_dist3,
                "property_class":     "شقة سكنية",
                "price_per_m2":       _psd_ppm2_3,
                "source_value":       _psd_val3,
                "source_date":        "06/2026",
                "source_confidence":  "عالية",
                "source_status":      "محاكاة QA",
                "source_notes":       "تقدير خبير — يُستخدم في التوفيق",
                "used_in_methods":    "توفيق النتائج",
            },
            {
                "source_registry_id": "SRC-QA-004",
                "source_type":        "land_comparable",
                "source_label":       _psd_land_label,
                "source_method":      "قيمة الأرض",
                "zone_id":            _psd_land_zone,
                "district":           _psd_land_dist,
                "property_class":     "أرض سكنية",
                "price_per_m2":       _psd_land_ppm2,
                "source_value":       _psd_land_val,
                "source_date":        "03/2026",
                "source_confidence":  "عالية",
                "source_status":      "محاكاة QA",
                "source_notes":       "مقارن أرض — يُستخدم في جدول قيمة الأرض وطريقة التكلفة",
                "used_in_methods":    "قيمة الأرض، طريقة التكلفة",
            },
            {
                "source_registry_id": "SRC-QA-005",
                "source_type":        "rental_income_indication",
                "source_label":       _psd_rent_label,
                "source_method":      "طريقة الدخل",
                "zone_id":            _psd_rent_zone,
                "district":           _psd_rent_dist,
                "property_class":     "شقة سكنية",
                "price_per_m2":       "—",
                "source_value":       _psd_rent_val,
                "source_date":        "06/2026",
                "source_confidence":  "متوسطة",
                "source_status":      "محاكاة QA",
                "source_notes":       "إيجار سوقي افتراضي — يُستخدم في طريقة الدخل و DCF",
                "used_in_methods":    "طريقة الدخل، DCF",
            },
        ]

        # Tag each price source with geo_match_status relative to subject zone
        for _src in price_source_data:
            _src_zone = _src.get("zone_id", "")
            _src_in_zone = bool(_src_zone and _src_zone == subject_zone_id)
            _src["geo_match_status"]    = "مطابق" if _src_in_zone else "خارج النطاق"
            _src["geo_use_status"]      = "مُدرج" if _src_in_zone else "مستبعد جغرافيًا"
            _src["geo_exclusion_reason"] = (
                "" if _src_in_zone
                else f"نطاق {_src_zone} يختلف عن نطاق العقار {subject_zone_id}"
            )

        # Mass appraisal bridge — zone and price calibrated to scenario
        if _qa_is_zamalek:
            _mass_zone   = "ZONE-CAI-ZAMALEK-01"
            _mass_ppm2   = "35,000 ج.م/م²"
            _mass_val    = f"{int(35_000 * area):,} ج.م"
            _mass_band   = f"{int(35_000*0.90):,} — {int(35_000*1.10):,} ج.م/م²"
            _mass_cover  = "28 عقار في نطاق 1 كم — منطقة الزمالك"
        elif _qa_is_maadi:
            _mass_zone   = "ZONE-CAI-MAADI-01"
            _mass_ppm2   = "25,000 ج.م/م²"
            _mass_val    = f"{int(25_000 * area):,} ج.م"
            _mass_band   = "22,500 — 27,500 ج.م/م²"
            _mass_cover  = "35 عقار في نطاق 1 كم"
        else:
            _mass_zone   = "ZONE-CAI-NASR-08"
            _mass_ppm2   = "25,000 ج.م/م²"
            _mass_val    = f"{int(25_000 * area):,} ج.م"
            _mass_band   = "22,500 — 27,500 ج.م/م²"
            _mass_cover  = "42 عقار في نطاق 1 كم — مدينة نصر"
        mass_appraisal_bridge = {
            "mass_run_id":               f"MASS-RUN-QA-2026-{_mass_zone[-3:]}",
            "mass_zone_id":              _mass_zone,
            "mass_average_price_per_m2": _mass_ppm2,
            "mass_model_value":          _mass_val,
            "mass_confidence_range":     _mass_band,
            "mass_data_quality_score":   "72%",
            "mass_source_coverage":      _mass_cover,
            "mass_appraisal_status": (
                "محاكاة QA — لم يتم ربط Source Registry/Qdrant فعلياً في هذه المرحلة."
            ),
            "linked_to_report_methods":  "AVM، مقارنة البيوع، توفيق النتائج، لوحة التحكم",
        }

        # Extend price_source_data with 4 rental source rows (rental QA only)
        if _is_rental:
            price_source_data.extend([
            {
                "source_registry_id": "SRC-QA-R01",
                "source_type":        "rental_comparable",
                "source_label":       "إيجار مقارن — مدينة نصر الثامنة — منفذ",
                "source_method":      "مقارنة إيجارية",
                "zone_id":            "ZONE-CAI-NASR-08",
                "district":           "مدينة نصر، القاهرة",
                "property_class":     "شقة سكنية",
                "price_per_m2":       "80 ج.م/م²/شهر",
                "source_value":       "9,200 ج.م/شهر",
                "source_date":        "03/2026",
                "source_confidence":  "عالية",
                "source_status":      "محاكاة QA",
                "source_notes":       "عقد إيجار منفذ — مقارن مباشر",
                "used_in_methods":    "مقارنة إيجارية، القيمة الإيجارية",
            },
            {
                "source_registry_id": "SRC-QA-R02",
                "source_type":        "lease_offer",
                "source_label":       "عرض إيجار — مدينة نصر، المنطقة الثامنة — معلن",
                "source_method":      "مقارنة إيجارية",
                "zone_id":            "ZONE-CAI-NASR-08",
                "district":           "مدينة نصر، القاهرة",
                "property_class":     "شقة سكنية",
                "price_per_m2":       "80 ج.م/م²/شهر",
                "source_value":       "10,400 ج.م/شهر",
                "source_date":        "04/2026",
                "source_confidence":  "متوسطة",
                "source_status":      "محاكاة QA",
                "source_notes":       "عرض إيجار معلن — تسوية موقع +2%",
                "used_in_methods":    "مقارنة إيجارية، القيمة الإيجارية",
            },
            {
                "source_registry_id": "SRC-QA-R03",
                "source_type":        "lease_contract",
                "source_label":       "عقد إيجار — مدينة نصر، المنطقة الثامنة — منفذ",
                "source_method":      "مقارنة إيجارية",
                "zone_id":            "ZONE-CAI-NASR-08",
                "district":           "مدينة نصر، القاهرة",
                "property_class":     "شقة سكنية",
                "price_per_m2":       "70 ج.م/م²/شهر",
                "source_value":       "7,560 ج.م/شهر",
                "source_date":        "02/2026",
                "source_confidence":  "عالية",
                "source_status":      "محاكاة QA",
                "source_notes":       "عقد إيجار منفذ — شقة مشابهة منطقة مجاورة",
                "used_in_methods":    "مقارنة إيجارية، القيمة الإيجارية",
            },
            {
                "source_registry_id": "SRC-QA-R04",
                "source_type":        "expert_rent_input",
                "source_label":       "تقدير خبير — إيجار سوقي — مدينة نصر",
                "source_method":      "تقدير الخبير",
                "zone_id":            "ZONE-CAI-NASR-08",
                "district":           "مدينة نصر، القاهرة",
                "property_class":     "شقة سكنية",
                "price_per_m2":       "79 ج.م/م²/شهر",
                "source_value":       "9,500 ج.م/شهر",
                "source_date":        "06/2026",
                "source_confidence":  "عالية",
                "source_status":      "محاكاة QA",
                "source_notes":       "تقدير خبير داخلي — القيمة المختارة للقيمة الإيجارية",
                "used_in_methods":    "القيمة الإيجارية، توفيق القيمة الإيجارية",
            },
        ])

    # ── Rental value context (QA or actual rental-purpose payload) ────────────
    if _is_rental or is_qa:
        _subj_area = area
        # Zone-aware rental comparables (3 in-zone + 1 out-of-zone for audit)
        if _qa_is_maadi:
            _RENT_COMPS = [
                {"num": 1, "location": "المعادي - شارع 9",
                 "zone_id": "ZONE-CAI-MAADI-01",
                 "property_type": "شقة سكنية", "area": 170, "monthly_rent": 9_500,
                 "location_factor": 1.00, "area_factor": 1.01,
                 "condition_factor": 1.00, "finishing_factor": 1.00, "time_factor": 1.00,
                 "status": "عقد إيجار منفذ", "notes": "مقارن مباشر — المعادي"},
                {"num": 2, "location": "المعادي - شارع 5",
                 "zone_id": "ZONE-CAI-MAADI-01",
                 "property_type": "شقة سكنية", "area": 185, "monthly_rent": 10_200,
                 "location_factor": 1.02, "area_factor": 0.99,
                 "condition_factor": 1.00, "finishing_factor": 1.01, "time_factor": 1.00,
                 "status": "عرض إيجار معلن",
                 "notes": "منطقة مجاورة داخل المعادي — تسوية موقع +2%"},
                {"num": 3, "location": "المعادي - شارع رئيسي",
                 "zone_id": "ZONE-CAI-MAADI-01",
                 "property_type": "شقة سكنية", "area": 160, "monthly_rent": 8_800,
                 "location_factor": 1.01, "area_factor": 1.02,
                 "condition_factor": 0.99, "finishing_factor": 1.00, "time_factor": 1.00,
                 "status": "عقد إيجار منفذ",
                 "notes": "شارع رئيسي المعادي — تسوية موقع +1%"},
                {"num": 4, "location": "مدينة نصر - المنطقة الثامنة",
                 "zone_id": "ZONE-CAI-NASR-08",
                 "property_type": "شقة سكنية", "area": 115, "monthly_rent": 9_200,
                 "location_factor": 1.00, "area_factor": 1.01,
                 "condition_factor": 0.98, "finishing_factor": 1.03, "time_factor": 1.00,
                 "status": "عقد إيجار منفذ", "notes": "خارج النطاق — يظهر للمراجعة فقط"},
            ]
        else:
            _RENT_COMPS = [
                {"num": 1, "location": "مدينة نصر - المنطقة الثامنة",
                 "zone_id": "ZONE-CAI-NASR-08",
                 "property_type": "شقة سكنية", "area": 115, "monthly_rent": 9_200,
                 "location_factor": 1.00, "area_factor": 1.01,
                 "condition_factor": 0.98, "finishing_factor": 1.03, "time_factor": 1.00,
                 "status": "عقد إيجار منفذ", "notes": "مقارن مباشر — نفس المنطقة"},
                {"num": 2, "location": "مدينة نصر - المنطقة السابعة",
                 "zone_id": "ZONE-CAI-NASR-08",
                 "property_type": "شقة سكنية", "area": 130, "monthly_rent": 10_400,
                 "location_factor": 1.02, "area_factor": 0.99,
                 "condition_factor": 1.00, "finishing_factor": 1.00, "time_factor": 1.00,
                 "status": "عرض إيجار معلن", "notes": "منطقة مجاورة — تسوية موقع +2%"},
                {"num": 3, "location": "مدينة نصر - المنطقة التاسعة",
                 "zone_id": "ZONE-CAI-NASR-08",
                 "property_type": "شقة سكنية", "area": 108, "monthly_rent": 7_560,
                 "location_factor": 1.03, "area_factor": 1.02,
                 "condition_factor": 1.01, "finishing_factor": 1.03, "time_factor": 1.00,
                 "status": "عقد إيجار منفذ", "notes": "منطقة مجاورة — تسوية موقع +3%"},
                {"num": 4, "location": "مدينة نصر - شارع جانبي",
                 "zone_id": "ZONE-CAI-NASR-08",
                 "property_type": "شقة سكنية", "area": 125, "monthly_rent": 10_000,
                 "location_factor": 1.05, "area_factor": 0.99,
                 "condition_factor": 1.00, "finishing_factor": 1.02, "time_factor": 1.01,
                 "status": "عرض إيجار معلن", "notes": "شارع جانبي — تسوية موقع +5%"},
            ]

        # Tag each rental comp with geo_match_status
        for _rc_pre in _RENT_COMPS:
            _rc_zone = _rc_pre.get("zone_id", "")
            _rc_in_zone = bool(_rc_zone and _rc_zone == subject_zone_id)
            _rc_pre["geo_match_status"]    = "مطابق" if _rc_in_zone else "خارج النطاق"
            _rc_pre["geo_exclusion_reason"] = (
                "" if _rc_in_zone
                else f"نطاق {_rc_zone} يختلف عن نطاق العقار {subject_zone_id}"
            )
        _adj_rents_list = []
        for _rc in _RENT_COMPS:
            _rc_area    = float(_rc["area"])
            _rc_monthly = float(_rc["monthly_rent"])
            _rpsm       = _rc_monthly / _rc_area
            _tot_adj    = (float(_rc["location_factor"]) * float(_rc["area_factor"]) *
                           float(_rc["condition_factor"]) * float(_rc["finishing_factor"]) *
                           float(_rc["time_factor"]))
            _adj_rpsm   = _rpsm * _tot_adj
            _subj_mo    = _adj_rpsm * _subj_area
            _rc["annual_rent"]            = int(_rc_monthly * 12)
            _rc["rent_per_m2_monthly"]    = round(_rpsm, 2)
            _rc["total_adj_factor"]       = round(_tot_adj, 4)
            _rc["adj_rent_per_m2"]        = round(_adj_rpsm, 2)
            _rc["subj_monthly_adj"]       = round(_subj_mo, 0)
            _rc["monthly_rent_disp"]      = f"{int(_rc_monthly):,} ج.م/شهر"
            _rc["annual_rent_disp"]       = f"{int(_rc_monthly * 12):,} ج.م/سنة"
            _rc["rent_per_m2_disp"]       = f"{_rpsm:.2f} ج.م/م²/شهر"
            _rc["total_adj_factor_disp"]  = f"{_tot_adj:.4f}"
            _rc["adj_rent_per_m2_disp"]   = f"{_adj_rpsm:.2f} ج.م/م²/شهر"
            _rc["subj_monthly_disp"]      = f"{int(_subj_mo):,} ج.م/شهر"
            # Only include in-zone comps in the average
            if _rc.get("geo_match_status", "مطابق") == "مطابق":
                _adj_rents_list.append(_adj_rpsm)

        _avg_adj_rent    = sum(_adj_rents_list) / len(_adj_rents_list) if _adj_rents_list else 0
        _sorted_adj      = sorted(_adj_rents_list)
        _med_adj_rent    = _sorted_adj[len(_sorted_adj) // 2] if _sorted_adj else 0
        _ind_monthly     = _avg_adj_rent * _subj_area
        _ind_annual      = _ind_monthly * 12
        _rvac_pct        = 5.0
        _rcoll_pct       = 2.0
        _rvac_amt        = _ind_annual * _rvac_pct / 100
        _rcoll_amt       = _ind_annual * _rcoll_pct / 100
        _net_rental_inc  = _ind_annual - _rvac_amt - _rcoll_amt

        _final_mo   = float(payload.get("final_monthly_rental_value") or
                            (9_500 if is_qa else _ind_monthly))
        _final_ann  = float(payload.get("final_annual_rental_value") or _final_mo * 12)
        _cap_est    = float(payload.get("estimated_value") or 0)
        _impl_yield = (
            f"{_net_rental_inc / _cap_est * 100:.2f}%" if _cap_est else _DATA_GAP
        )

        rental_value_context = {
            "rental_comparables":              _RENT_COMPS,
            "avg_adj_rent_per_m2_monthly":     f"{_avg_adj_rent:.2f}",
            "median_adj_rent_per_m2_monthly":  f"{_med_adj_rent:.2f}",
            "indicated_monthly_rent":          f"{int(_ind_monthly):,} ج.م",
            "indicated_annual_rent":           f"{int(_ind_annual):,} ج.م",
            "vacancy_rate":                    f"{_rvac_pct:.1f}%",
            "vacancy_amount":                  f"{int(_rvac_amt):,} ج.م",
            "collection_loss_rate":            f"{_rcoll_pct:.1f}%",
            "collection_loss_amount":          f"{int(_rcoll_amt):,} ج.م",
            "net_rental_income":               f"{int(_net_rental_inc):,} ج.م",
            "implied_yield":                   _impl_yield,
            "final_monthly_rental_value":      f"{int(_final_mo):,} ج.م",
            "final_annual_rental_value":       f"{int(_final_ann):,} ج.م",
            "rental_value_low_range":          f"{int(_final_mo * 0.92):,} ج.م",
            "rental_value_high_range":         f"{int(_final_mo * 1.08):,} ج.م",
            "rental_value_notes": (
                f"الإيجار الشهري المختار {int(_final_mo):,} ج.م يستند إلى متوسط "
                f"المقارنات المعدلة ({_avg_adj_rent:.2f} ج.م/م²/شهر × {int(_subj_area)} م²). "
                "محاكاة QA — لا تمثل عقوداً حقيقية."
            ),
            "rental_disclaimer": (
                "جميع البيانات الإيجارية محاكاة داخلية لأغراض QA. "
                "لا تمثل عقوداً أو مصادر إيجارية فعلية. "
                "لا يتضمن هذا التحليل استرجاعاً من الإنترنت أو Qdrant."
            ),
        }
    else:
        rental_value_context = {
            "rental_comparables":              [],
            "avg_adj_rent_per_m2_monthly":     _DATA_GAP,
            "median_adj_rent_per_m2_monthly":  _DATA_GAP,
            "indicated_monthly_rent":          _DATA_GAP,
            "indicated_annual_rent":           _DATA_GAP,
            "vacancy_rate":                    _DATA_GAP,
            "vacancy_amount":                  _DATA_GAP,
            "collection_loss_rate":            _DATA_GAP,
            "collection_loss_amount":          _DATA_GAP,
            "net_rental_income":               _DATA_GAP,
            "implied_yield":                   _DATA_GAP,
            "final_monthly_rental_value":      _DATA_GAP,
            "final_annual_rental_value":       _DATA_GAP,
            "rental_value_low_range":          _DATA_GAP,
            "rental_value_high_range":         _DATA_GAP,
            "rental_value_notes":              _EXPERT_FILL,
            "rental_disclaimer":               "",
        }

    # ── Final Capitalization Rate — 4 methods (distinct from discount rate) ──
    if is_qa:
        _cr_m1_comps = [
            {"num": 1, "location": "مدينة نصر — المنطقة الثامنة",
             "noi": "315,000 ج.م", "value": "8,289,474 ج.م", "cap_rate": "3.80%"},
            {"num": 2, "location": "مدينة نصر — المنطقة السابعة",
             "noi": "290,000 ج.م", "value": "7,631,579 ج.م", "cap_rate": "3.80%"},
            {"num": 3, "location": "مدينة نصر — المنطقة التاسعة",
             "noi": "340,000 ج.م", "value": "8,947,368 ج.م", "cap_rate": "3.80%"},
        ]
        _cr_m1 = 3.80

        _cr_debt  = 0.60; _cr_mc    = 0.055; _cr_eq = 0.40; _cr_eqdiv = 0.040
        _cr_m2    = round((_cr_debt * _cr_mc + _cr_eq * _cr_eqdiv) * 100, 2)  # 4.90%

        # DR-minus-growth uses actual DCF inputs (discount_rate=13%, growth=5%)
        _cr_yield = float(payload.get("dcf_discount_rate") or 13.0)
        _cr_glt   = float(payload.get("dcf_growth_rate") or 5.0)
        _cr_m3    = round(_cr_yield - _cr_glt, 2)  # 8.00% for QA

        _cr_rf = 6.0; _cr_prisk = 1.5; _cr_liq = 1.0; _cr_mgmt = 0.5; _cr_gded = 4.0
        _cr_m4 = round(_cr_rf + _cr_prisk + _cr_liq + _cr_mgmt - _cr_gded, 2)  # 5.00%

        _cr_avg = round((_cr_m1 + _cr_m2 + _cr_m3 + _cr_m4) / 4, 2)
        # Expert selects DR-minus-growth result as the most theoretically consistent
        _cr_expert_selected = _cr_m3  # DR - growth (using actual DCF inputs)

        cap_rate_derivation = {
            "methods": [
                {
                    "method_key":  "direct_extraction",
                    "method_name": "أ. الاستخلاص المباشر من السوق",
                    "comparables": _cr_m1_comps,
                    "indicated_cap_rate": f"{_cr_m1:.2f}%",
                    "notes": "متوسط معدلات الرسملة المستخلصة من 3 مبيعات مقارنة",
                },
                {
                    "method_key":  "band_of_investment",
                    "method_name": "ب. نموذج حزمة الاستثمار (Band of Investment)",
                    "inputs": {
                        "debt_ratio":           f"{_cr_debt*100:.0f}%",
                        "mortgage_constant":    f"{_cr_mc*100:.1f}%",
                        "equity_ratio":         f"{_cr_eq*100:.0f}%",
                        "equity_dividend_rate": f"{_cr_eqdiv*100:.1f}%",
                    },
                    "formula": (
                        f"{_cr_debt*100:.0f}% × {_cr_mc*100:.1f}% + "
                        f"{_cr_eq*100:.0f}% × {_cr_eqdiv*100:.1f}% = {_cr_m2:.2f}%"
                    ),
                    "indicated_cap_rate": f"{_cr_m2:.2f}%",
                    "notes": "محاكاة QA — ثابت الرهن ومعدل حقوق الملكية افتراضيان",
                },
                {
                    "method_key":  "dr_minus_growth",
                    "method_name": "ج. معدل الخصم ناقص معدل النمو (DR − g / Gordon Model)",
                    "inputs": {
                        "discount_rate": f"{_cr_yield:.1f}%",
                        "growth_rate":   f"{_cr_glt:.1f}%",
                    },
                    "formula": f"{_cr_yield:.1f}% − {_cr_glt:.1f}% = {_cr_m3:.2f}%",
                    "indicated_cap_rate": f"{_cr_m3:.2f}%",
                    "notes": (
                        f"معدل الخصم {_cr_yield:.1f}% (من DCF) ناقص معدل النمو {_cr_glt:.1f}% "
                        "— يعكس انسجام معدل الرسملة مع افتراضات DCF"
                    ),
                },
                {
                    "method_key":  "buildup",
                    "method_name": "د. طريقة البناء التراكمي المعدَّلة (Built-up Adjusted)",
                    "inputs": {
                        "risk_free_rate":    f"{_cr_rf:.1f}%",
                        "property_risk":     f"{_cr_prisk:.1f}%",
                        "liquidity_premium": f"{_cr_liq:.1f}%",
                        "management_risk":   f"{_cr_mgmt:.1f}%",
                        "growth_deduction":  f"-{_cr_gded:.1f}%",
                    },
                    "formula": (
                        f"{_cr_rf:.1f}% + {_cr_prisk:.1f}% + "
                        f"{_cr_liq:.1f}% + {_cr_mgmt:.1f}% − {_cr_gded:.1f}% = {_cr_m4:.2f}%"
                    ),
                    "indicated_cap_rate": f"{_cr_m4:.2f}%",
                    "notes": "محاكاة QA — جميع المعدلات الأساسية افتراضية",
                },
            ],
            "average_cap_rate":         f"{_cr_avg:.2f}%",
            "expert_selected_cap_rate": f"{_cr_expert_selected:.2f}%",
            "dr_minus_growth_rate":     f"{_cr_m3:.2f}%",
            "final_cap_rate_notes": (
                f"معدل الرسملة النهائي المختار = {_cr_expert_selected:.2f}% استناداً إلى "
                f"طريقة معدل الخصم ناقص النمو (DR − g = {_cr_yield:.1f}% − {_cr_glt:.1f}%) "
                "لضمان الانسجام مع افتراضات DCF. "
                "جميع الطرق محاكاة QA ولا تستند إلى مصادر سوقية حقيقية."
            ),
            "disclaimer": (
                "جميع معدلات الرسملة المحسوبة هنا محاكاة داخلية لأغراض QA. "
                "لا يتضمن هذا التحليل استرجاعاً من الإنترنت أو Qdrant أو أي مصدر بيانات خارجي."
            ),
        }
    else:
        cap_rate_derivation = {
            "methods": [],
            "average_cap_rate":        _DATA_GAP,
            "expert_selected_cap_rate": _DATA_GAP,
            "final_cap_rate_notes":    _EXPERT_FILL,
            "disclaimer":              "",
        }

    # ── Cap rate governance check (Part E) ───────────────────────────────
    _cr_gov_warning           = False
    _cr_gov_text              = ""
    _cr_diff_from_avg         = 0.0
    _cr_diff_from_dr_growth   = 0.0
    if is_qa:
        try:
            _cr_selected_num      = _cr_expert_selected   # type: ignore[name-defined]
            _cr_average_num       = _cr_avg               # type: ignore[name-defined]
            _cr_dr_growth_num     = _cr_m3                # type: ignore[name-defined]
            _cr_diff_from_avg     = round(_cr_selected_num - _cr_average_num, 2)
            _cr_diff_from_dr_growth = round(_cr_selected_num - _cr_dr_growth_num, 2)
            _cr_deviation         = abs(_cr_diff_from_avg)
            if _cr_deviation > 0.5:
                _cr_gov_warning = True
                _cr_gov_text = (
                    f"تحذير: معدل الرسملة المختار ({_cr_selected_num:.2f}%) "
                    f"يتجاوز متوسط الطرق الأربع ({_cr_average_num:.2f}%) "
                    f"بفارق {_cr_diff_from_avg:+.2f}% — يتجاوز عتبة 0.50%. "
                    "يلزم الخبير تبرير الاختيار."
                )
        except NameError:
            pass
    cap_rate_governance = {
        "cap_rate_warning_flag":        _cr_gov_warning,
        "cap_rate_warning_text":        _cr_gov_text,
        "difference_from_average":      f"{_cr_diff_from_avg:+.2f}%",
        "difference_from_dr_growth":    f"{_cr_diff_from_dr_growth:+.2f}%",
        "cap_rate_source_basis": (
            "معدل الخصم ناقص النمو (DR − g) — ضمان الانسجام مع افتراضات DCF"
            if is_qa else _EXPERT_FILL
        ),
        "risk_free_rate_source_label": (
            "عائد أذون الخزانة المصرية (364 يوماً)" if is_qa else _EXPERT_FILL
        ),
        "risk_free_rate":             f"{_cr_rf:.1f}%" if is_qa else _EXPERT_FILL,  # type: ignore
        "risk_free_rate_date":        "2026-06-01" if is_qa else _EXPERT_FILL,
        "risk_free_rate_notes": (
            "معدل الخالي من المخاطر مأخوذ من أذون الخزانة المصرية — محاكاة QA"
            if is_qa else _EXPERT_FILL
        ),
    }

    # ── Preliminary vs Certified value difference (Part D) ───────────────
    _prelim_val_num   = float(
        str(payload.get("preliminary_value") or "").replace(",", "").replace(" ج.م", "").strip()
        or (3_200_000 if is_qa else 0)
    )
    _certified_val_num = float(
        str(payload.get("certified_final_value") or "").replace(",", "").replace(" ج.م", "").strip()
        or 0
    )
    if _certified_val_num and _prelim_val_num:
        _pvc_diff    = _certified_val_num - _prelim_val_num
        _pvc_diff_pct = (_pvc_diff / _prelim_val_num * 100) if _prelim_val_num else 0
        _pvc_diff_str = f"{_pvc_diff:+,.0f} ج.م"
        _pvc_pct_str  = f"{_pvc_diff_pct:+.2f}%"
    else:
        _pvc_diff_str = _EXPERT_FILL
        _pvc_pct_str  = _EXPERT_FILL
    prelim_vs_certified = {
        "preliminary_value":      (
            f"{int(_prelim_val_num):,} ج.م" if _prelim_val_num else _EXPERT_FILL
        ),
        "certified_final_value":  (
            f"{int(_certified_val_num):,} ج.م" if _certified_val_num else _EXPERT_FILL
        ),
        "difference_amount":      _pvc_diff_str,
        "difference_percentage":  _pvc_pct_str,
        "reason_summary": payload.get("prelim_certified_reason") or (
            "لم يصدر بعد تقرير معتمد — القيمة الأولية هي المرجع الراهن." if not _certified_val_num
            else _EXPERT_FILL
        ),
        "expert_adjustment_notes": payload.get("expert_adjustment_notes") or _EXPERT_FILL,
        "disclaimer": (
            "الفارق بين القيمة الأولية والقيمة المعتمدة يُوثَّق هنا لأغراض الشفافية "
            "والمراجعة وفق متطلبات IVSC ومعايير التقييم المصرية."
        ),
    }

    # ── Part H: ESG financial linkage ─────────────────────────────────────
    # Compute ESG adjustment values that propagate to cap rate and discount rate.
    # QA synthetic scores from the same 8-criteria set used in the workbook ESG sheet.
    _esg_qa_scores = [3, 2, 3, 3, 3, 3, 3, 4]  # must match workbook _esg_items QA values
    _esg_total: int = sum(_esg_qa_scores) if is_qa else int(payload.get("esg_total_score") or 0)
    # Formula: -0.025% per point above 20, floored at -0.50%
    _esg_raw_adj: float = -(_esg_total - 20) * 0.025 if _esg_total > 20 else 0.0
    _esg_cap_adj: float = max(-0.50, _esg_raw_adj)   # cap rate reduction in % points
    # Discount rate gets the same directional adjustment scaled by risk premium weight
    _esg_dr_adj:  float = _esg_cap_adj               # symmetric for simplicity
    esg_context = {
        "esg_total_score":              _esg_total,
        "esg_total_score_max":          40,
        "esg_raw_adjustment_pct":       f"{_esg_raw_adj:+.3f}%",
        "esg_cap_rate_adjustment":      f"{_esg_cap_adj:+.3f}%",
        "esg_discount_rate_adjustment": f"{_esg_dr_adj:+.3f}%",
        "esg_risk_premium_adjustment":  f"{_esg_cap_adj:+.3f}%",
        "esg_adjustment_basis": (
            f"تعديل -0.025% لكل نقطة فوق 20 — درجة QA {_esg_total} من 40"
            if is_qa else "يتطلب إدخال درجة ESG من المُقيِّم"
        ),
        "esg_adjusted_cap_rate": (
            f"{round(_cr_expert_selected + _esg_cap_adj, 2):.2f}%"  # type: ignore[name-defined]
            if is_qa else _EXPERT_FILL
        ),
        "esg_adjusted_discount_rate": (
            f"{round(float(payload.get('dcf_discount_rate') or 13.0) + _esg_dr_adj, 2):.2f}%"
            if is_qa else _EXPERT_FILL
        ),
    }

    # ── Source Registry enrichment (readiness layer — no live Qdrant) ─────────
    # Adds full Source Registry schema fields to every price source record.
    # qdrant_status is always "مرحلة مستقبلية — غير مفعل" — Qdrant not activated.
    _QDRANT_STATUS    = "مرحلة مستقبلية — غير مفعل"
    _CONFIDENCE_MAP   = {"عالية": 85, "متوسطة": 70, "منخفضة": 50}
    for _sr in price_source_data:
        _sr_type = _sr.get("source_type", "")
        _sr_label = _sr.get("source_label", "")
        _sr_in_zone = _sr.get("zone_id", "") == subject_zone_id
        _is_rental_src = (
            "rental" in _sr_type or "lease" in _sr_type or "rent" in _sr_type
            or "إيجار" in _sr_label
        )
        _is_land_src   = "land" in _sr_type or "أرض" in _sr_label
        _sr.setdefault("source_id",               _sr.get("source_registry_id", ""))
        _sr.setdefault("source_origin",            "محاكاة QA داخلية" if is_qa else _DATA_GAP)
        _sr.setdefault("source_currency",          "ج.م")
        _sr.setdefault("country",                  "مصر")
        _sr.setdefault("city",                     subject_city)
        _sr.setdefault("sub_market",               subject_sub_market if _sr_in_zone else _DATA_GAP)
        _sr.setdefault("asset_type",               _sr.get("property_class", "شقة سكنية"))
        _sr.setdefault("area",                     area)
        _sr.setdefault("value",                    _sr.get("source_value", ""))
        _sr.setdefault("monthly_rent",             _sr.get("source_value", "") if _is_rental_src else "")
        _sr.setdefault("rent_per_m2_monthly",      _sr.get("price_per_m2", "") if _is_rental_src else "")
        _sr.setdefault("land_price_per_m2",        _sr.get("price_per_m2", "") if _is_land_src else "")
        _sr.setdefault("construction_cost_per_m2", "")
        _sr.setdefault("confidence_score",         _CONFIDENCE_MAP.get(str(_sr.get("source_confidence", "")), 65))
        _sr.setdefault("reliability_tier",         _sr.get("source_confidence", _DATA_GAP))
        _sr.setdefault("exclusion_reason",         _sr.get("geo_exclusion_reason", ""))
        _sr.setdefault("audit_notes",              "")
        _sr.setdefault("qdrant_ready",             True)
        _sr.setdefault("qdrant_collection",        "expert_valuations")
        _sr.setdefault("qdrant_vector_id",         "")
        _sr.setdefault("qdrant_status",            _QDRANT_STATUS)
    source_registry = price_source_data  # canonical alias with full schema

    # source_method_links: every method → list of source IDs it uses
    _KNOWN_METHODS = [
        "AVM", "مقارنة البيوع", "القيمة الإيجارية", "قيمة الأرض",
        "طريقة التكلفة", "طريقة الدخل", "DCF",
        "مقارنة إيجارية", "توفيق النتائج", "توفيق القيمة الإيجارية",
    ]
    source_method_links: dict = {m: [] for m in _KNOWN_METHODS}
    for _sr in price_source_data:
        _sr_methods_str = _sr.get("used_in_methods", "")
        for _m in _KNOWN_METHODS:
            if _m in _sr_methods_str:
                _sid = _sr.get("source_id") or _sr.get("source_registry_id", "")
                if _sid and _sid not in source_method_links[_m]:
                    source_method_links[_m].append(_sid)

    # source_registry_summary
    _inc_srcs = [s for s in price_source_data if s.get("geo_use_status", "مُدرج") != "مستبعد جغرافيًا"]
    _exc_srcs = [s for s in price_source_data if s.get("geo_use_status", "مُدرج") == "مستبعد جغرافيًا"]
    _src_by_type: dict = {}
    for _sr in price_source_data:
        _t = _sr.get("source_type", "unknown")
        _src_by_type[_t] = _src_by_type.get(_t, 0) + 1
    source_registry_summary = {
        "total_sources":       len(price_source_data),
        "included_sources":    len(_inc_srcs),
        "excluded_sources":    len(_exc_srcs),
        "by_type":             _src_by_type,
        "subject_zone_id":     subject_zone_id,
        "has_out_of_zone":     len(_exc_srcs) > 0,
        "all_have_source_id":  all(
            bool(s.get("source_id") or s.get("source_registry_id"))
            for s in price_source_data
        ) if price_source_data else True,
        "qdrant_status":       _QDRANT_STATUS,
        "disclaimer_ar": (
            "لا يتضمن هذا الإصدار استرجاعًا آليًا من الإنترنت أو Qdrant. "
            "تم تجهيز هيكل مصادر البيانات فقط لاستقبال الربط الآلي في مرحلة لاحقة."
        ),
    }

    # qdrant_readiness_summary — structural readiness only, operational flags all False
    qdrant_readiness_summary = {
        "qdrant_ready":               True,
        "qdrant_enabled":             False,
        "rag_enabled":                False,
        "internet_ingestion_enabled": False,
        "status_ar":                  "جاهز هيكليًا — غير مفعل تشغيليًا",
        "qdrant_collection":          "expert_valuations",
        "qdrant_status":              _QDRANT_STATUS,
        "source_count_ready":         len(price_source_data),
    }

    # ── Advanced Methodology & Compliance Context (Parts B–L) ─────────────────

    # Part B — Highest and Best Use Analysis
    _hbu_current_use = payload.get("current_use") or (
        "سكني فاخر" if is_qa and "زمالك" in subject_district else
        "سكني متوسط" if is_qa else _DATA_GAP
    )
    hbu_analysis = {
        "current_use":             _hbu_current_use,
        "candidate_uses":          ["سكني", "إداري جزئي", "تجاري أرضي"] if is_qa else [_DATA_GAP],
        "legally_permissible":     (
            "الاستخدام السكني مسموح ومرخص — التحويل الإداري يستلزم تراخيص بلدية إضافية"
            if is_qa else _EXPERT_FILL
        ),
        "physically_possible":     (
            "يمكن فيزيائياً تحويل جزئي للإدارة في الطابق الأرضي إذا أتاحه التصميم"
            if is_qa else _EXPERT_FILL
        ),
        "financially_feasible":    (
            "التحويل الإداري الجزئي قد يكون مجدياً عند دخل إضافي يتجاوز تكلفة التحويل"
            if is_qa else _EXPERT_FILL
        ),
        "maximally_productive":    (
            "الاستخدام السكني الحالي هو الأعلى ربحية في ضوء البيانات المتاحة"
            if is_qa else _EXPERT_FILL
        ),
        "selected_hbu":            "سكني فاخر — الاستخدام الحالي" if is_qa else _EXPERT_FILL,
        "conversion_cost":         "150,000 ج.م (تقدير QA — يلزم فحص ميداني)" if is_qa else _DATA_GAP,
        "incremental_income":      "30,000 ج.م/سنة (تقدير QA)" if is_qa else _DATA_GAP,
        "incremental_value":       "تحسن هامشي مقارنة بتكلفة التحويل" if is_qa else _DATA_GAP,
        "hbu_conclusion":          (
            "الاستخدام الحالي (سكني) هو أعلى وأفضل استخدام. "
            "لا يوجد مبرر اقتصادي كافٍ للتحويل في ضوء البيانات الحالية."
            if is_qa else _EXPERT_FILL
        ),
        "limitations":             "التحليل مستند إلى محاكاة QA فقط. يلزم فحص قانوني ورخص بناء فعلية.",
        "hbu_four_tests_present":  True,
    }

    # Part C — Direct Capitalization vs DCF explicit separation
    _direct_cap_value = income_value_calc if income_value_calc else 0
    _dcf_value_raw    = dcf_total if (is_qa or payload.get("dcf_discount_rate")) else 0
    _sales_val_raw    = (
        int(str(sales_from_comps_str).replace(",", "").replace(" ج.م", "").strip())
        if sales_from_comps_str and sales_from_comps_str.replace(",", "").replace(" ج.م", "").strip().isdigit()
        else (sales_from_comps if "sales_from_comps" in dir() and sales_from_comps else 0)
    )
    _cost_val_raw = (cost_val if cost_val else 0) if cost_ctx else float(payload.get("cost_value") or 0)

    direct_capitalization_context = {
        "direct_capitalization_result":      f"{_direct_cap_value:,.0f} ج.م" if _direct_cap_value else _DATA_GAP,
        "direct_capitalization_formula":     "القيمة = صافي الدخل التشغيلي ÷ معدل الرسملة",
        "dcf_result":                        f"{_dcf_value_raw:,.0f} ج.م" if _dcf_value_raw else _DATA_GAP,
        "dcf_reconciliation_weight":         float(payload.get("dcf_weight") or (0.15 if is_qa else 0.0)),
        "direct_cap_reconciliation_weight":  float(payload.get("income_weight") or (0.20 if is_qa else 0.0)),
        "income_direct_vs_dcf_explanation":  (
            "تم فصل طريقة رسملة الدخل المباشر عن طريقة التدفقات النقدية المخصومة "
            "لأن كل منهما يعالج نمطاً مختلفاً من المخاطر والنمو. "
            "رسملة الدخل المباشر تفترض استقراراً في الدخل، "
            "بينما تعالج DCF النمو المتوقع ومتغيرات المخاطر عبر الزمن."
        ),
        "dcf_vs_sales_divergence_note":      (
            "في حال تباين كبير بين DCF وطريقة المقارنة، قد يعكس ذلك: "
            "إيجارات أدنى من السوق، أو افتراضات معدل خصم محافظة، "
            "أو ضعف بيانات الدخل مقارنةً بقوة بيانات المعاملات."
        ),
    }

    # Part D — Comparable Adjustment Support
    comparable_adjustment_support = {
        "adjustments": [
            {
                "adjustment_type": "موقع", "coefficient": 1.05, "pct": "+5%",
                "source": "تحليل الأزواج البيعية (محاكاة QA)" if is_qa else _EXPERT_FILL,
                "basis": "فارق سعر المتر بين المناطق المتجاورة",
                "n_observations": 4 if is_qa else 0,
                "confidence": "متوسط — بيانات QA" if is_qa else _DATA_GAP,
                "notes": "محاكاة QA — غير مفعلة بمصدر سوق حي",
            },
            {
                "adjustment_type": "مساحة", "coefficient": 0.98, "pct": "-2%",
                "source": "انحدار إحصائي (محاكاة QA)" if is_qa else _EXPERT_FILL,
                "basis": "كل زيادة 50 م² — تعديل سالب بسيط",
                "n_observations": 6 if is_qa else 0,
                "confidence": "منخفض — QA فقط" if is_qa else _DATA_GAP,
                "notes": "محاكاة QA — غير مفعلة بمصدر سوق حي",
            },
            {
                "adjustment_type": "الطابق والإطلالة", "coefficient": 1.02, "pct": "+2%",
                "source": "خبرة السوق (محاكاة QA)" if is_qa else _EXPERT_FILL,
                "basis": "طوابق عليا وإطلالة مفتوحة",
                "n_observations": 3 if is_qa else 0,
                "confidence": "منخفض — رأي خبير استرشادي" if is_qa else _DATA_GAP,
                "notes": "محاكاة QA — غير مفعلة بمصدر سوق حي",
            },
            {
                "adjustment_type": "تشطيب", "coefficient": 1.03, "pct": "+3%",
                "source": "تكلفة التشطيب المقدرة" if is_qa else _EXPERT_FILL,
                "basis": "تكلفة فرق التشطيب / سعر متر العقار",
                "n_observations": 0,
                "confidence": "منخفض — تقدير تكلفة فقط",
                "notes": "يلزم مقارنات بيعية معاملات فعلية",
            },
        ],
        "paired_sales_disclaimer": (
            "تحليل الأزواج البيعية مستند إلى محاكاة QA فقط. "
            "لا توجد معاملات سوقية حقيقية مُدخلة. "
            "يجب مراجعة أي معاملات مستندة إلى محاكاة QA قبل الاعتماد النهائي."
            if is_qa else _DATA_GAP
        ),
        "regression_support": (
            "معادلة انحدار QA تقريبية — لا تستند إلى عينة إحصائية حقيقية"
            if is_qa else _DATA_GAP
        ),
    }

    # Part E — Assumptions Registry
    assumptions_registry = [
        {
            "type": "افتراض عادي",
            "description": "صحة بيانات المساحة والعمر المقدمة من العميل",
            "reason": "لم يُجرَ فحص ميداني مستقل",
            "value_impact_if_wrong": "±5% على القيمة المقدرة",
            "needs_supporting_doc": True,
            "expert_notes": _EXPERT_FILL,
        },
        {
            "type": "افتراض خاص",
            "description": "خلو العقار من النزاعات القانونية أو الأعباء الخفية",
            "reason": "لم تُقدَّم مستندات ملكية مكتملة",
            "value_impact_if_wrong": "قد يؤثر تأثيراً جوهرياً — حتى 50%",
            "needs_supporting_doc": True,
            "expert_notes": _EXPERT_FILL,
        },
        {
            "type": "افتراض خاص",
            "description": "الإيجارات المستخدمة تعكس السوق في تاريخ التقييم",
            "reason": "لا يتوفر عقد إيجار مُقدَّم للمراجعة",
            "value_impact_if_wrong": "تأثير جوهري على مؤشر الدخل وDCF",
            "needs_supporting_doc": True,
            "expert_notes": _EXPERT_FILL,
        },
        {
            "type": "قيد على نطاق العمل",
            "description": "عدم إتاحة شهادة تصرفات عقارية أو بيانات التسجيل الرسمي",
            "reason": "قيد متعلق بتوفر المستندات",
            "value_impact_if_wrong": "—",
            "needs_supporting_doc": False,
            "expert_notes": _EXPERT_FILL,
        },
    ]
    extraordinary_assumptions = [a for a in assumptions_registry if a["type"] == "افتراض خاص"]
    hypothetical_conditions: list = []
    scope_limitations = [a for a in assumptions_registry if a["type"] == "قيد على نطاق العمل"]

    # Part F — Detailed depreciation breakdown (physical curable / incurable split)
    _phys_depr_pct = float(payload.get("physical_depreciation_rate") or (20.0 if is_qa else 0))
    _func_depr_pct = float(payload.get("functional_depreciation_rate") or (5.0 if is_qa else 0))
    _ext_depr_pct  = float(payload.get("external_depreciation_rate") or 0.0)
    _land_for_depr = float(payload.get("land_share_value") or (910_000 if is_qa else 0))
    _repl_for_depr = (
        _cost_val_raw - _land_for_depr if _cost_val_raw > _land_for_depr
        else float(payload.get("replacement_cost_per_m2") or (6_000 if is_qa else 0)) * area
    )
    _phys_curable_pct   = min(5.0, _phys_depr_pct * 0.20)
    _phys_incurable_pct = _phys_depr_pct - _phys_curable_pct
    _eff_age   = float(payload.get("effective_age") or (8 if is_qa else 0))
    _econ_life = float(payload.get("economic_life") or 50.0)
    _phys_incur_age_pct = (_eff_age / _econ_life * 100) if _econ_life else _phys_incurable_pct
    depreciation_breakdown = {
        "physical_curable_pct":           round(_phys_curable_pct, 2),
        "physical_curable_value":         f"{_repl_for_depr * _phys_curable_pct / 100:,.0f} ج.م" if _repl_for_depr else _DATA_GAP,
        "physical_incurable_pct":         round(_phys_incurable_pct, 2),
        "physical_incurable_value":       f"{_repl_for_depr * _phys_incurable_pct / 100:,.0f} ج.م" if _repl_for_depr else _DATA_GAP,
        "physical_incurable_age_formula": f"العمر الفعلي {_eff_age:.0f} ÷ العمر الاقتصادي {_econ_life:.0f} = {_phys_incur_age_pct:.1f}%",
        "functional_obsolescence_pct":   round(_func_depr_pct, 2),
        "functional_obsolescence_value":  f"{_repl_for_depr * _func_depr_pct / 100:,.0f} ج.م" if _repl_for_depr else _DATA_GAP,
        "external_obsolescence_pct":     round(_ext_depr_pct, 2),
        "external_obsolescence_value":    f"{_repl_for_depr * _ext_depr_pct / 100:,.0f} ج.م" if _repl_for_depr else _DATA_GAP,
        "total_depreciation_pct":        round(_phys_depr_pct + _func_depr_pct + _ext_depr_pct, 2),
        "total_depreciation_value":       (
            f"{_repl_for_depr * (_phys_depr_pct + _func_depr_pct + _ext_depr_pct) / 100:,.0f} ج.م"
            if _repl_for_depr else _DATA_GAP
        ),
        "replacement_cost_new":           f"{_repl_for_depr:,.0f} ج.م" if _repl_for_depr else _DATA_GAP,
        "depreciated_replacement_cost":   (
            f"{_repl_for_depr * (1 - (_phys_depr_pct + _func_depr_pct + _ext_depr_pct) / 100):,.0f} ج.م"
            if _repl_for_depr else _DATA_GAP
        ),
        "effective_age":                  _eff_age,
        "economic_life":                  _econ_life,
        "evidence_basis":                 "محاكاة QA — يلزم تحقق ميداني وتكلفة إصلاح فعلية" if is_qa else _EXPERT_FILL,
    }

    # Part G — DCF Scenario / Risk Analysis
    _base_noi_for_scen: float = (
        float(str(dcf_ctx.get("dcf_base_noi", "0")).replace(",", "").replace(" ج.م", "").strip())
        if dcf_ctx.get("dcf_base_noi") else float(noi if noi else (180_000 if is_qa else 0))
    )
    _base_discount = float(payload.get("dcf_discount_rate") or 13.0) / 100
    _base_tc       = float(payload.get("dcf_terminal_cap_rate") or 4.5) / 100
    _selling_c     = float(payload.get("dcf_selling_costs_pct") or 2.0) / 100

    def _calc_dcf_scen(noi_b: float, gr: float, dr: float, tc: float, sc: float) -> int:
        if not noi_b or not dr or not tc:
            return 0
        pv = sum(noi_b * (1 + gr) ** t / (1 + dr) ** (t + 1) for t in range(5))
        tv = noi_b * (1 + gr) ** 5 / tc
        pv += tv * (1 - sc) / (1 + dr) ** 5
        return int(round(pv))

    _sv_base = _calc_dcf_scen(_base_noi_for_scen, 0.05, _base_discount, _base_tc, _selling_c)
    _sv_opt  = _calc_dcf_scen(_base_noi_for_scen, 0.06, _base_discount, 0.040, _selling_c)
    _sv_pes  = _calc_dcf_scen(_base_noi_for_scen, 0.03, _base_discount, 0.055, _selling_c)

    dcf_scenarios = {
        "optimistic": {
            "label": "متفائل",
            "rent_growth_pct": 6.0, "terminal_cap_rate_pct": 4.0,
            "dcf_value": f"{_sv_opt:,.0f} ج.م" if _sv_opt else _DATA_GAP,
            "variance_from_base": f"{(_sv_opt - _sv_base):+,.0f} ج.م" if _sv_base else _DATA_GAP,
            "variance_pct": f"{(_sv_opt - _sv_base) / _sv_base * 100:+.1f}%" if _sv_base else _DATA_GAP,
        },
        "base": {
            "label": "أساسي",
            "rent_growth_pct": 5.0, "terminal_cap_rate_pct": 4.5,
            "dcf_value": f"{_sv_base:,.0f} ج.م" if _sv_base else _DATA_GAP,
            "variance_from_base": "— (الأساس)", "variance_pct": "0.0%",
        },
        "pessimistic": {
            "label": "متشائم",
            "rent_growth_pct": 3.0, "terminal_cap_rate_pct": 5.5,
            "dcf_value": f"{_sv_pes:,.0f} ج.م" if _sv_pes else _DATA_GAP,
            "variance_from_base": f"{(_sv_pes - _sv_base):+,.0f} ج.م" if _sv_base else _DATA_GAP,
            "variance_pct": f"{(_sv_pes - _sv_base) / _sv_base * 100:+.1f}%" if _sv_base else _DATA_GAP,
        },
        "scenario_spread": f"{(_sv_opt - _sv_pes):,.0f} ج.م" if (_sv_opt and _sv_pes) else _DATA_GAP,
        "monte_carlo_note": (
            "محاكاة مونت كارلو — مرحلة مستقبلية غير مفعلة. "
            "التحليل الحالي يعتمد ثلاثة سيناريوهات حتمية فقط."
        ),
        "dcf_risk_disclaimer": (
            "نطاق السيناريوهات استرشادي. يلزم مراجعة معدل النمو ومعدل الرسملة الطرفي "
            "بواسطة الخبير بناءً على بيانات السوق الفعلية."
        ),
        "scenarios_present": True,
    }

    # Part H — Legal Due Diligence
    legal_due_diligence = {
        "ownership_type":               payload.get("ownership_type") or _DATA_GAP,
        "ownership_document_reviewed":  (
            "نعم — بناءً على مدخلات العميل" if payload.get("ownership_type")
            else "لا — لم تُقدَّم مستندات ملكية"
        ),
        "mortgage_or_lien_status":       payload.get("mortgage_status") or "غير محدد — يلزم الفحص",
        "legal_dispute_status":          payload.get("dispute_status") or "غير محدد — يلزم الفحص",
        "last_transfer_date":            payload.get("last_transfer_date") or _DATA_GAP,
        "expropriation_or_pending":      payload.get("expropriation_status") or "غير محدد",
        "reviewed_documents":            payload.get("reviewed_legal_docs") or _DATA_GAP,
        "missing_documents":             payload.get("missing_legal_docs") or "شهادة تصرفات — رخصة بناء",
        "legal_scope_limitation": (
            "لم يتم إجراء فحص قانوني كامل، ويعد ذلك قيداً على نطاق العمل، "
            "ولا يمثل التقرير رأياً قانونياً في صحة الملكية."
        ),
        "legal_due_diligence_conclusion": (
            "الفحص القانوني المبدئي محدود ببيانات الطلب. "
            "يُوصى بمراجعة قانونية مستقلة قبل استخدام التقرير لأغراض قانونية أو تمويلية."
        ),
    }

    # Part I — Enhanced ESG context (climate risk, terminal value adjustment, value impact)
    _esg_score_num = _esg_total
    _esg_tv_adj_pct = 7.0 if (is_qa and _esg_score_num >= 30) else (3.0 if (is_qa and _esg_score_num >= 20) else 0.0)
    esg_enhanced_context = {
        "esg_score":                      _esg_score_num,
        "esg_category":                   (
            "A — ممتاز" if _esg_score_num >= 32 else
            "B — جيد"   if _esg_score_num >= 24 else
            "C — متوسط" if _esg_score_num >= 16 else "D — ضعيف"
        ),
        "esg_terminal_value_adjustment":  f"+{_esg_tv_adj_pct:.1f}%",
        "esg_value_impact": (
            f"تعديل إيجابي +{_esg_tv_adj_pct:.1f}% على القيمة الطرفية"
            if _esg_tv_adj_pct > 0 else
            "لا يُطبَّق أثر إنتاجي — بيانات ESG غير مكتملة أو درجة منخفضة"
        ),
        "climate_risk_score":             (
            "منخفض — لا يوجد تاريخ فيضانات أو زلازل ظاهر في المنطقة"
            if is_qa else _DATA_GAP
        ),
        "climate_risk_notes":             (
            "لا يتضمن هذا الإصدار تقييماً مناخياً رسمياً. "
            "يُوصى بتقييم مناخي مستقل للعقارات في مناطق معرضة للفيضانات أو التصحر."
        ),
        "esg_incomplete_note":            (
            "" if is_qa else
            "غير مكتمل — لا يُطبَّق أثر إنتاجي. يلزم تقديم بيانات الاستدامة من المقيِّم."
        ),
    }

    # Part J — Environmental Impact Assessment (purpose-conditional)
    _purpose_key_raw = (purpose_info or {}).get("purpose_key", "") if purpose_info else ""
    _eia_required = (
        "eia" in _purpose_key_raw or
        "environmental" in _purpose_key_raw or
        "بيئي" in str(payload.get("purpose", "")) or
        "أثر بيئي" in str(payload.get("purpose", ""))
    )
    environmental_impact_assessment = {
        "eia_required":                _eia_required,
        "contamination_risk":          (
            payload.get("contamination_risk") or
            ("منخفض — محاكاة QA" if is_qa and _eia_required else _NA_PURPOSE)
        ),
        "groundwater_risk":            payload.get("groundwater_risk") or ("غير محدد" if _eia_required else _NA_PURPOSE),
        "air_quality_noise_risk":      (
            payload.get("air_noise_risk") or
            ("متوسط — قرب طريق رئيسي" if is_qa and _eia_required else _NA_PURPOSE)
        ),
        "proximity_to_sensitive":      payload.get("proximity_sensitive") or _NA_PURPOSE,
        "remediation_cost_estimate":   payload.get("remediation_cost") or _NA_PURPOSE,
        "environmental_discount_pct":  (
            0.0 if not _eia_required
            else float(payload.get("environmental_discount_pct") or 0.0)
        ),
        "land_value_impact":           (
            _NA_PURPOSE if not _eia_required else
            "لا يُطبَّق خصم بدون بيانات تلوث مؤكدة"
        ),
        "eia_conclusion":              (
            _NA_PURPOSE if not _eia_required else
            "لا توجد بيانات بيئية كافية لإجراء تقييم أثر بيئي في هذه المرحلة. "
            "يُعد هذا قيداً على نطاق العمل."
        ),
        "eia_scope_limitation":        (
            _NA_PURPOSE if not _eia_required else
            "لم تُقدَّم بيانات بيئية كافية. لا يُطبَّق خصم دون بيانات تلوث أو معالجة مؤكدة."
        ),
    }

    # Part K — Confidence / Uncertainty Range
    _method_vals_list: list = []
    _method_weights_list: list = []
    for _mv_val, _mw_val, _ml in [
        (_sales_val_raw,    float(payload.get("sales_weight")  or (0.50 if is_qa else 0)), "مقارنة البيوع"),
        (_direct_cap_value, float(payload.get("income_weight") or (0.20 if is_qa else 0)), "رسملة الدخل المباشر"),
        (_dcf_value_raw,    float(payload.get("dcf_weight")    or (0.15 if is_qa else 0)), "DCF"),
        (_cost_val_raw,     float(payload.get("cost_weight")   or (0.15 if is_qa else 0)), "طريقة التكلفة"),
    ]:
        if _mv_val > 0:
            _method_vals_list.append({"method": _ml, "value": _mv_val})
            _method_weights_list.append(_mw_val)

    _n_meth = len(_method_vals_list)
    _mean_v = sum(m["value"] for m in _method_vals_list) / _n_meth if _n_meth else 0
    _wt_s   = sum(_method_weights_list) if _method_weights_list else 0
    _wt_val = (
        sum(m["value"] * w for m, w in zip(_method_vals_list, _method_weights_list)) / _wt_s
        if _wt_s > 0 else _mean_v
    )
    import math as _math_mod
    _std_v  = _math_mod.sqrt(sum((m["value"] - _mean_v) ** 2 for m in _method_vals_list) / _n_meth) if _n_meth > 1 else 0.0
    _cv_v   = (_std_v / _mean_v * 100) if _mean_v else 0.0
    _margin = _std_v * 1.645 if _n_meth > 1 else (_wt_val * 0.10)

    valuation_uncertainty = {
        "method_values":            _method_vals_list,
        "mean_value":               f"{_mean_v:,.0f} ج.م" if _mean_v else _DATA_GAP,
        "weighted_value":           f"{_wt_val:,.0f} ج.م" if _wt_val else _DATA_GAP,
        "standard_deviation":       f"{_std_v:,.0f} ج.م" if _std_v else _DATA_GAP,
        "coefficient_of_variation": f"{_cv_v:.1f}%" if _cv_v else _DATA_GAP,
        "confidence_level":         "90% — نطاق استرشادي (غير إحصائي صارم)",
        "lower_bound":              f"{max(0, _wt_val - _margin):,.0f} ج.م" if _wt_val else _DATA_GAP,
        "upper_bound":              f"{_wt_val + _margin:,.0f} ج.م" if _wt_val else _DATA_GAP,
        "uncertainty_comment": (
            "نطاق عدم اليقين مشتق من تشتت قيم الطرق المستخدمة. "
            "يلزم الحذر عند الاستناد إليه دون مراجعة خبير — العينة محدودة."
            if _n_meth > 1 else
            "بيانات غير كافية لاحتساب نطاق عدم يقين موثوق."
        ),
        "n_methods_used":           _n_meth,
        "uncertainty_label":        "نطاق عدم يقين تقديري",
    }

    # Part L — Peer Review
    _pr_status = payload.get("peer_review_status") or "not_started"
    peer_review = {
        "peer_review_required":    bool(payload.get("peer_review_required") or False),
        "peer_reviewer_name":      payload.get("peer_reviewer_name") or _DATA_GAP,
        "peer_reviewer_role":      payload.get("peer_reviewer_role") or _DATA_GAP,
        "peer_review_date":        payload.get("peer_review_date") or _DATA_GAP,
        "peer_review_status":      _pr_status,
        "peer_review_status_label": {
            "not_started":       "لم تبدأ",
            "in_review":         "قيد المراجعة",
            "changes_requested": "يستلزم تعديلات",
            "reviewed":          "مراجعة مكتملة",
            "approved":          "معتمدة",
        }.get(_pr_status, "غير محدد"),
        "peer_review_notes":       payload.get("peer_review_notes") or _DATA_GAP,
        "review_limitations": (
            "لم يتم إجراء مراجعة نظراء مستقلة في هذه النسخة."
            if _pr_status in ("not_started", "") else ""
        ),
    }

    # ── Task 1 Part B — Source Quality Gate ─────────────────────────────────
    _qa_src_list = [
        s for s in source_registry
        if "QA" in str(s.get("source_status", "")) or "محاكاة" in str(s.get("source_status", ""))
    ]
    _prod_src_list = [
        s for s in source_registry
        if "QA" not in str(s.get("source_status", "")) and "محاكاة" not in str(s.get("source_status", ""))
        and str(s.get("source_status", "")).strip()
    ]
    _cert_allowed = len(_qa_src_list) == 0 and len(source_registry) > 0
    _cert_block_reason = (
        f"يوجد {len(_qa_src_list)} مصدر محاكاة QA — يجب استبدالها ببيانات سوقية حقيقية قبل الاعتماد"
        if _qa_src_list else ""
    )
    source_quality_gate = {
        "all_required_sources_production_ready": _cert_allowed,
        "qa_simulation_sources_count":           len(_qa_src_list),
        "production_ready_sources_count":        len(_prod_src_list),
        "missing_required_sources":              (
            [] if source_registry else ["مصادر بيانات السوق الفعلية"]
        ),
        "certification_allowed":                 _cert_allowed,
        "certification_block_reason":            _cert_block_reason,
        "advisory_only_reason": (
            "يحتوي التقرير على بيانات محاكاة QA غير صالحة للاستخدام الرسمي أو الاعتماد النهائي. "
            "يجب إدخال بيانات سوقية حقيقية ومراجعتها قبل الاعتماد."
            if _qa_src_list else ""
        ),
        "source_quality_summary": (
            f"مصادر جاهزة للإنتاج: {len(_prod_src_list)} | "
            f"مصادر QA (تحتاج استبدال): {len(_qa_src_list)} | "
            f"إجمالي: {len(source_registry)}"
        ),
        "required_actions": (
            [
                "استبدال مصادر محاكاة QA ببيانات سوق فعلية موثقة",
                "مراجعة وتحقق الخبير من المصادر",
                "اعتماد جودة المصادر قبل إصدار التقرير النهائي",
            ]
            if _qa_src_list else []
        ),
        "certification_warning_text": (
            "يحتوي التقرير على بيانات محاكاة QA غير صالحة للاستخدام الرسمي. "
            "يرجى إدخال بيانات سوقية حقيقية ومراجعتها قبل الاعتماد."
            if _qa_src_list else ""
        ),
    }

    # ── Task 1 Part C — Final Reconciliation & Expert-Selected Value ─────────
    if _method_vals_list and _method_weights_list:
        _dom_idx = max(range(len(_method_weights_list)), key=lambda i: _method_weights_list[i])
        _dominant_method = _method_vals_list[_dom_idx]["method"]
        _dominant_weight = _method_weights_list[_dom_idx]
    else:
        _dominant_method = _DATA_GAP
        _dominant_weight = 0.0

    _recon_methods = []
    for _rmv, _rmw in zip(_method_vals_list, _method_weights_list):
        _contribution = _rmv["value"] * _rmw / _wt_s if _wt_s else 0
        _recon_methods.append({
            "method":               _rmv["method"],
            "value":                _rmv["value"],
            "value_str":            f"{_rmv['value']:,.0f} ج.م",
            "weight":               _rmw,
            "weight_pct":           f"{_rmw * 100:.0f}%",
            "weighted_contribution": f"{_contribution:,.0f} ج.م",
            "data_reliability":     "محاكاة QA" if is_qa else _EXPERT_FILL,
        })

    _sel_val_num = _wt_val if _wt_val else 0
    _sel_val_rounded_num = int(round(_sel_val_num / 1000)) * 1000 if _sel_val_num else 0
    _cv_num_recon = (_std_v / _mean_v * 100) if _mean_v else 0
    _divergence_expl = (
        f"تتراوح قيم الطرق بين "
        f"{min(m['value'] for m in _method_vals_list):,.0f} "
        f"و{max(m['value'] for m in _method_vals_list):,.0f} ج.م "
        f"(معامل اختلاف {_cv_num_recon:.1f}%). "
        "يعكس التفاوت اختلاف المنهجيات واعتماداتها على البيانات."
        if len(_method_vals_list) > 1 else _DATA_GAP
    )

    final_reconciliation = {
        "method_values":                _recon_methods,
        "method_weights":               {
            _rmv["method"]: _rmw
            for _rmv, _rmw in zip(_method_vals_list, _method_weights_list)
        },
        "weighted_indication":          f"{_wt_val:,.0f} ج.م" if _wt_val else _DATA_GAP,
        "selected_final_value":         f"{_sel_val_num:,.0f} ج.م" if _sel_val_num else _DATA_GAP,
        "selected_final_value_raw":     _sel_val_num,
        "selected_final_value_rounded": f"{_sel_val_rounded_num:,} ج.م" if _sel_val_rounded_num else _DATA_GAP,
        "lower_value_bound":            valuation_uncertainty.get("lower_bound", _DATA_GAP),
        "upper_value_bound":            valuation_uncertainty.get("upper_bound", _DATA_GAP),
        "value_range_basis":            "نطاق 90% مشتق من تشتت قيم الطرق المستخدمة",
        "dominant_method":              _dominant_method,
        "dominant_method_reason": (
            f"حصلت طريقة {_dominant_method} على أعلى وزن ({_dominant_weight * 100:.0f}%) "
            "نظراً لتوفر بيانات مقارنة سوقية حديثة وموثوقة"
            if _dominant_method != _DATA_GAP else _DATA_GAP
        ),
        "reconciliation_rationale": (
            f"القيمة الموصى بها هي المتوسط الموزون لـ {len(_method_vals_list)} طريقة تقييم. "
            "تعكس الأوزان مدى توفر البيانات وملاءمة كل طريقة للغرض والعقار. "
            "القيمة النهائية استرشادية وتتطلب تأكيداً من الخبير."
            if _method_vals_list else "لا تتوفر قيم طرق كافية للتوفيق"
        ),
        "divergence_explanation":       _divergence_expl,
        "expert_selection_status":      "system_recommended_pending_expert_confirmation",
        "certification_status":         "advisory_only" if not _cert_allowed else "pending_expert_review",
        "reconciliation_basis":         "محاكاة QA" if is_qa else _EXPERT_FILL,
    }

    # ── Task 1 Part D — Standards Compliance Statement ────────────────────────
    _all_gates_ok = _cert_allowed
    _compliance_status = "limited_advisory" if not _all_gates_ok else "methodological_alignment"
    _qual_stmt = (
        "تم تصميم التقرير ليتوافق منهجياً مع مبادئ IVS وUSPAP والمعايير المصرية للتقييم، "
        "إلا أن الاعتماد النهائي يتطلب استكمال مصادر بيانات إنتاجية، "
        "نطاق العمل، وتوقيع الخبير المرخص ومراجعة النظراء."
    )
    standards_compliance = {
        "ivs_alignment_statement": (
            "يراعي التقرير مبادئ IVS الخاصة بالعقارات — IVS 105، IVS 400، IVS 410. "
            "لا يُدّعى الامتثال الكامل لـ IVS في غياب مصادر إنتاجية وتوقيع معتمد."
        ),
        "uspap_alignment_statement": (
            "تم تصميم التقرير وفق منهجية تتوافق مع متطلبات USPAP SR 1-3 — "
            "نطاق العمل، الافتراضات الخاصة، مبدأ عدم الإفصاح الزائف. "
            "لا يُدّعى الامتثال الكامل قبل استكمال نطاق العمل والتوقيع المعتمد."
        ),
        "egyptian_fra_alignment_statement": (
            "يستند التقرير إلى المعايير المصرية للتقييم الصادرة عن هيئة الرقابة المالية (FRA). "
            "الاعتماد النهائي يتطلب تسجيل الخبير ومراجعة المصادر وفق متطلبات FRA."
        ),
        "full_compliance_claim_allowed": _all_gates_ok,
        "compliance_limitations": (
            [
                "مصادر البيانات محاكاة QA — يلزم استبدالها ببيانات سوق حقيقية",
                "توقيع الخبير المرخص مطلوب",
                "نطاق العمل يحتاج استكمالاً",
                "مراجعة النظراء المستقلة مطلوبة",
            ]
            if not _all_gates_ok else []
        ),
        "standards_mapping_table": [
            {
                "methodology_section": "تحليل أعلى وأفضل استخدام (HBU)",
                "ivs_reference": "IVS 104.6، IVS 400.22-26",
                "uspap_reference": "USPAP SR 1-3(b)",
                "fra_reference": "المعيار المصري للتقييم — مبادئ HBU",
                "report_section": "قسم HBU",
                "alignment_status": "مُطبَّق — استرشادي",
                "limitation": "يتطلب بيانات سوق حقيقية",
            },
            {
                "methodology_section": "طريقة التكلفة",
                "ivs_reference": "IVS 410",
                "uspap_reference": "USPAP SR 1-3(a)",
                "fra_reference": "المعيار المصري 410",
                "report_section": "قسم طريقة التكلفة",
                "alignment_status": "مُطبَّق — استرشادي",
                "limitation": "يتطلب تكاليف استبدال فعلية",
            },
            {
                "methodology_section": "مقارنة البيوع",
                "ivs_reference": "IVS 105.4، IVS 400.15",
                "uspap_reference": "USPAP SR 1-3(a)",
                "fra_reference": "المعيار المصري للتقييم — طريقة السوق",
                "report_section": "قسم مقارنة البيوع",
                "alignment_status": "مُطبَّق — استرشادي",
                "limitation": "مقارنات محاكاة QA",
            },
            {
                "methodology_section": "طريقة الدخل / رسملة مباشرة",
                "ivs_reference": "IVS 105.6، IVS 400.19",
                "uspap_reference": "USPAP SR 1-3(a)",
                "fra_reference": "المعيار المصري للتقييم — طريقة الدخل",
                "report_section": "قسم طريقة الدخل",
                "alignment_status": "مُطبَّق — استرشادي",
                "limitation": "إيجار محاكاة",
            },
            {
                "methodology_section": "التدفقات النقدية المخصومة (DCF)",
                "ivs_reference": "IVS 105.6، IVS 400.19",
                "uspap_reference": "USPAP SR 1-4(f)",
                "fra_reference": "المعيار المصري 105 — DCF",
                "report_section": "قسم DCF",
                "alignment_status": "مُطبَّق — استرشادي",
                "limitation": "بيانات افتراضية",
            },
            {
                "methodology_section": "الافتراضات والافتراضات الخاصة",
                "ivs_reference": "IVS 101.4-6",
                "uspap_reference": "USPAP SR 2-2(b)(ix)",
                "fra_reference": "المعيار المصري للتقييم — الإفصاح",
                "report_section": "قسم الافتراضات",
                "alignment_status": "مُطبَّق",
                "limitation": "",
            },
            {
                "methodology_section": "نطاق العمل",
                "ivs_reference": "IVS 101.8",
                "uspap_reference": "USPAP SR 2-2(a)",
                "fra_reference": "FRA — متطلبات التقرير",
                "report_section": "قسم نطاق العمل",
                "alignment_status": "مُطبَّق جزئياً — يحتاج استكمالاً",
                "limitation": "يتطلب إدخال نطاق كامل من الخبير",
            },
            {
                "methodology_section": "توقيع واعتماد الخبير",
                "ivs_reference": "IVS 103.2",
                "uspap_reference": "USPAP SR 2-3",
                "fra_reference": "FRA — ترخيص المقيِّم",
                "report_section": "قسم الاعتماد والتوقيع",
                "alignment_status": "غير مكتمل — يتطلب توقيع معتمد",
                "limitation": "لا يصلح للاعتماد النهائي بدون توقيع",
            },
        ],
        "missing_compliance_requirements": (
            [
                "بيانات سوقية إنتاجية موثقة",
                "توقيع الخبير المرخص",
                "نطاق عمل مكتمل",
                "مراجعة النظراء المستقلة",
            ]
            if not _all_gates_ok else []
        ),
        "compliance_status":              _compliance_status,
        "qualified_compliance_statement": _qual_stmt,
    }

    # ── Task 1 Part E — Expert Signature & Approval Block ────────────────────
    _exp_name    = payload.get("expert_name") or _DATA_GAP
    _exp_license = payload.get("expert_license_number") or payload.get("expert_reg_number") or _DATA_GAP
    _exp_role    = payload.get("expert_role") or (
        "خبير تقييم عقاري" if _exp_name != _DATA_GAP else _DATA_GAP
    )
    _exp_firm    = payload.get("firm_name") or _DATA_GAP
    _exp_date    = payload.get("approval_date") or _DATA_GAP
    _exp_sig     = bool(payload.get("signature_available") or False)
    _exp_stamp   = bool(payload.get("stamp_available") or False)
    _cert_sig_ready = (
        _exp_name != _DATA_GAP and
        _exp_license != _DATA_GAP and
        _exp_date != _DATA_GAP and
        _exp_sig
    )
    expert_approval = {
        "expert_name":                  _exp_name,
        "expert_license_number":        _exp_license,
        "expert_role":                  _exp_role,
        "firm_name":                    _exp_firm,
        "approval_date":                _exp_date,
        "signature_available":          _exp_sig,
        "stamp_available":              _exp_stamp,
        "peer_review_status":           peer_review.get("peer_review_status", "not_started"),
        "approval_status":              "ready_for_approval" if _cert_sig_ready else "pending",
        "approval_limitations": (
            "توقيع الخبير المرخص غير مرفق في هذه النسخة"
            if not _exp_sig else ""
        ),
        "certification_signature_ready": _cert_sig_ready,
        "signature_placeholder_text": (
            "توقيع الخبير غير مرفق في هذه النسخة"
            if not _exp_sig else ""
        ),
        "unsigned_notice": (
            "نسخة مبدئية غير موقعة" if not _exp_sig else ""
        ),
    }

    # ── Task 1 Part F — Scope of Work ────────────────────────────────────────
    _sow_purpose   = purpose_info.get("purpose_label_ar", _DATA_GAP) if purpose_info else _DATA_GAP
    _sow_val_date  = _val_date_raw or _DATA_GAP
    _sow_rep_date  = _rep_date_raw or _DATA_GAP
    _sow_insp_date = payload.get("inspection_date") or _EXPERT_FILL
    _sow_int_users = payload.get("intended_users") or _EXPERT_FILL
    _sow_int_use   = payload.get("intended_use") or _EXPERT_FILL
    _sow_interest  = (
        payload.get("property_interest_valued") or
        ("ملكية حرة (فريهولد)" if is_qa else _EXPERT_FILL)
    )
    _ALL_METHODS_LIST = [
        "مقارنة البيوع", "رسملة الدخل المباشر", "DCF", "طريقة التكلفة", "AVM",
    ]
    _methods_used_list_sow  = [m["method"] for m in _method_vals_list] if _method_vals_list else []
    _methods_excl_list_sow  = [m for m in _ALL_METHODS_LIST if m not in _methods_used_list_sow]
    _sow_data_sources = [
        s.get("source_label", "") for s in source_registry
        if s.get("geo_use_status", "مُدرج") != "مستبعد جغرافيًا"
    ] if source_registry else [_DATA_GAP]

    scope_of_work = {
        "valuation_purpose":         _sow_purpose,
        "intended_users":            _sow_int_users,
        "intended_use":              _sow_int_use,
        "basis_of_value":            _sow_purpose,
        "property_interest_valued":  _sow_interest,
        "valuation_date":            _sow_val_date,
        "inspection_date":           _sow_insp_date,
        "report_date":               _sow_rep_date,
        "methods_used":              _methods_used_list_sow,
        "methods_used_str":          "، ".join(_methods_used_list_sow) if _methods_used_list_sow else _DATA_GAP,
        "methods_excluded":          _methods_excl_list_sow,
        "methods_excluded_str":      "، ".join(_methods_excl_list_sow) if _methods_excl_list_sow else "لا يوجد",
        "method_selection_rationale": (
            "تم اختيار الطرق بناءً على توفر البيانات وملاءمة الطريقة لغرض التقييم ونوع العقار. "
            "الطرق المستبعدة تحتاج بيانات إضافية غير متاحة حالياً."
        ),
        "data_sources_used":         _sow_data_sources,
        "unavailable_data": (
            "شهادة تصرفات عقارية، رخصة البناء، بيانات تكلفة الإنشاء الفعلية، "
            "صور ميدانية، تقييم بيئي مستقل"
        ),
        "scope_limitations":         [lim.get("description", "") for lim in scope_limitations] if scope_limitations else [_DATA_GAP],
        "reliance_restrictions": (
            "لا يجوز الاعتماد على هذا التقرير لأغراض رسمية أو قانونية أو تمويلية "
            "قبل استكمال مصادر البيانات وتوقيع الخبير المرخص ومراجعة النظراء."
        ),
    }

    # ── Task 2 Part B — Peer Review Gate ────────────────────────────────────
    _prg_name    = payload.get("peer_reviewer_name") or _DATA_GAP
    _prg_lic     = (
        payload.get("peer_reviewer_license") or
        payload.get("peer_reviewer_role") or _DATA_GAP
    )
    _prg_date    = payload.get("peer_review_date") or _DATA_GAP
    _prg_sig     = bool(payload.get("peer_review_signature_available") or False)
    _prg_status  = payload.get("peer_review_status") or "not_started"
    _prg_completed = _prg_status in ("reviewed", "approved")
    _prg_cert_allowed = (
        _prg_completed and
        _prg_name != _DATA_GAP and
        _prg_date != _DATA_GAP
    )
    peer_review_gate = {
        "peer_review_required":              True,
        "peer_review_completed":             _prg_completed,
        "peer_reviewer_name":                _prg_name,
        "peer_reviewer_license_or_role":     _prg_lic,
        "peer_review_date":                  _prg_date,
        "peer_review_signature_available":   _prg_sig,
        "peer_review_notes":                 payload.get("peer_review_notes") or _DATA_GAP,
        "peer_review_status":                _prg_status,
        "peer_review_block_reason": (
            "لم يتم إجراء مراجعة نظراء مستقلة في هذه النسخة، ولا تصلح للاعتماد النهائي."
            if not _prg_cert_allowed else ""
        ),
        "certification_allowed_by_peer_review": _prg_cert_allowed,
        "peer_review_limitation_text": (
            "لم يتم إجراء مراجعة نظراء مستقلة في هذه النسخة، ولا تصلح للاعتماد النهائي."
            if not _prg_completed else ""
        ),
    }

    # ── Task 2 Part C — Visual Attachments Readiness ────────────────────────
    _va_missing: list = []
    if not _has_coords:
        _va_missing.append("إحداثيات GPS")
    if not map_ctx.get("subject_map_image_available"):
        _va_missing.append("خريطة موقع العقار")
    if not map_ctx.get("subject_aerial_image_available"):
        _va_missing.append("صورة جوية للعقار")
    if not map_ctx.get("comparables_map_image_available"):
        _va_missing.append("خريطة توزيع المقارنات الجغرافية")
    _va_missing.extend([
        "صور الواجهة الخارجية",
        "صور داخلية",
        "صور المداخل والبيئة المحيطة",
    ])
    _ext_photos  = bool(payload.get("exterior_photos_attached") or False)
    _int_photos  = bool(payload.get("interior_photos_attached") or False)
    _fac_photos  = bool(payload.get("facade_photos_attached") or False)
    visual_attachments = {
        "gps_coordinates_available":        _has_coords,
        "latitude":                         map_ctx.get("latitude", _DATA_GAP),
        "longitude":                        map_ctx.get("longitude", _DATA_GAP),
        "location_map_available":           map_ctx.get("subject_map_image_available", False),
        "aerial_image_available":           map_ctx.get("subject_aerial_image_available", False),
        "comparables_map_available":        map_ctx.get("comparables_map_image_available", False),
        "exterior_photos_available":        _ext_photos,
        "interior_photos_available":        _int_photos,
        "facade_photos_available":          _fac_photos,
        "attachments_ready_for_certification": False,
        "missing_visual_attachments":       _va_missing,
        "attachment_limitations": (
            f"المرفقات البصرية التالية غير متوفرة: {' | '.join(_va_missing[:3])} وغيرها. "
            "يُضيف الخبير هذه المرفقات يدوياً قبل الاعتماد النهائي."
        ),
        "map_disclaimer": (
            "لم تُقدَّم خرائط أو صور ميدانية فعلية في هذه النسخة. "
            "البيانات الموضحة هي بيانات نصية/تعريفية فقط. "
            "يجب إرفاق خرائط وصور فعلية قبل الاعتماد."
        ),
        "required_attachments": [
            {"type": "خريطة موقع العقار",              "available": map_ctx.get("subject_map_image_available", False), "notes": "يُضيف الخبير يدوياً"},
            {"type": "إحداثيات GPS",                   "available": _has_coords,  "notes": (f"{_lat_val:.4f}N, {_lon_val:.4f}E" if _has_coords else "غير متوفرة")},
            {"type": "صورة جوية للعقار",               "available": False, "notes": "يُضيف الخبير يدوياً"},
            {"type": "خريطة توزيع المقارنات الجغرافية", "available": False, "notes": "تُنشأ عند توفر إحداثيات المقارنات"},
            {"type": "صور الواجهة الخارجية",           "available": _ext_photos,  "notes": "يُرفقها الخبير"},
            {"type": "صور داخلية",                      "available": _int_photos,  "notes": "يُرفقها الخبير"},
            {"type": "صور المداخل / الشارع / البيئة المحيطة", "available": _fac_photos, "notes": "يُرفقها الخبير"},
        ],
    }

    # ── Task 2 Part D — AVM Completeness / Explicit Exclusion ───────────────
    _avm_val_raw  = payload.get("avm_value") or 0
    _avm_has_val  = bool(_avm_val_raw and isinstance(_avm_val_raw, (int, float)) and _avm_val_raw > 0)
    _avm_used     = bool(_avm_has_val or (avm_regression and avm_reg_predicted))
    _avm_wt_raw   = float(payload.get("avm_weight") or 0)
    avm_status = {
        "avm_used":                  _avm_used,
        "avm_available":             _avm_used,
        "avm_input_completeness": (
            "مكتمل" if _avm_has_val else (
                f"{len(avm_regression)} عوامل انحدار متوفرة" if avm_regression else "غير مكتمل — لا توجد مدخلات AVM"
            )
        ),
        "avm_value":                 f"{int(_avm_val_raw):,} ج.م" if _avm_has_val else (avm_reg_predicted or _DATA_GAP),
        "avm_confidence_score":      (
            payload.get("avm_confidence_score") or ("72%" if is_qa and _avm_used else _DATA_GAP)
        ),
        "avm_methodology_summary": (
            "نموذج الانحدار الخطي المتعدد — AVM داخلي. لا يعتمد على Qdrant أو إنترنت."
            if _avm_used else _DATA_GAP
        ),
        "avm_data_sources": (
            "بيانات محاكاة QA — مصادر داخلية للتحقق المنهجي فقط"
            if (is_qa and _avm_used) else _DATA_GAP
        ),
        "avm_limitations": (
            "AVM محاكاة داخلية — لا يُعتمد عليه كمؤشر سوقي مستقل. يتطلب مصادر بيانات حقيقية."
            if (is_qa and _avm_used) else (
                "لم يتم استخدام AVM لعدم اكتمال المدخلات ومصادر البيانات."
                if not _avm_used else ""
            )
        ),
        "avm_exclusion_reason": (
            "" if _avm_used else
            "لم يتم استخدام AVM لعدم اكتمال المدخلات ومصادر البيانات."
        ),
        "avm_reconciliation_weight":     _avm_wt_raw if _avm_used else 0,
        "avm_reconciliation_weight_pct": (
            f"{_avm_wt_raw * 100:.0f}%" if _avm_used else "0%"
        ),
    }

    # ── Task 2 Part E — Rent Consistency Check ───────────────────────────────
    _rent_income_raw = monthly_rent  # income approach monthly rent (float)
    _rent_final_raw  = float(payload.get("final_monthly_rental_value") or 0)
    _rent_diff_abs   = abs(_rent_income_raw - _rent_final_raw) if (_rent_income_raw and _rent_final_raw) else 0
    _rent_diff_pct_v = (_rent_diff_abs / _rent_final_raw * 100) if _rent_final_raw else 0
    _rent_consistent = _rent_diff_pct_v <= 5.0
    _rent_material   = _rent_diff_pct_v > 5.0 and bool(_rent_income_raw and _rent_final_raw)
    rent_consistency_check = {
        "income_method_monthly_rent":       f"{_rent_income_raw:,.0f} ج.م/شهر" if _rent_income_raw else _DATA_GAP,
        "income_method_monthly_rent_raw":   _rent_income_raw,
        "final_selected_monthly_rent":      f"{_rent_final_raw:,.0f} ج.م/شهر" if _rent_final_raw else _DATA_GAP,
        "final_selected_monthly_rent_raw":  _rent_final_raw,
        "rental_comparison_indication": (
            f"{_rent_final_raw:,.0f} ج.م/شهر (من مقارنات إيجارية)" if _rent_final_raw else _DATA_GAP
        ),
        "rent_difference_value":     f"{_rent_diff_abs:,.0f} ج.م/شهر" if _rent_diff_abs else _DATA_GAP,
        "rent_difference_percent":   f"{_rent_diff_pct_v:.1f}%" if (_rent_income_raw and _rent_final_raw) else _DATA_GAP,
        "rent_consistent":           _rent_consistent,
        "rent_difference_explanation": (
            "" if not _rent_material else
            f"تم استخدام إيجار {_rent_income_raw:,.0f} ج.م/شهر في طريقة الدخل "
            f"لأنه يعكس إيجاراً سوقياً تقديرياً للعقار، بينما القيمة الإيجارية النهائية "
            f"{_rent_final_raw:,.0f} ج.م/شهر تستند إلى مقارنات إيجارية فعلية أو أكثر تحفظاً. "
            "لذلك تم توثيق الفرق ضمن التوفيق النهائي."
        ),
        "rent_consistency_required_action": (
            "يجب على الخبير توثيق سبب اختلاف الإيجار المستخدم في طريقة الدخل "
            "عن القيمة الإيجارية النهائية."
            if _rent_material else ""
        ),
    }

    # ── Task 2 Part F — Final Client Recommendation ──────────────────────────
    _rec_val_str = (
        f"{_rent_final_raw:,.0f} ج.م/شهر"
        if (_is_rental and _rent_final_raw) else (
            f"{_sel_val_rounded_num:,} ج.م" if _sel_val_rounded_num else _DATA_GAP
        )
    )
    _unc_lower = valuation_uncertainty.get("lower_bound", "")
    _unc_upper = valuation_uncertainty.get("upper_bound", "")
    _rec_val_range = (
        f"{_unc_lower} — {_unc_upper}"
        if (_unc_lower and _unc_upper and _DATA_GAP not in str(_unc_lower)) else _DATA_GAP
    )
    _key_risks: list = []
    if _cv_num_recon > 25:
        _key_risks.append(f"تفاوت مادي بين الطرق (CV={_cv_num_recon:.1f}%) — ينصح بمراجعة الأوزان")
    if not _cert_allowed:
        _key_risks.append("بيانات محاكاة QA — يلزم استبدالها بمصادر سوق حقيقية")
    if not _prg_cert_allowed:
        _key_risks.append("مراجعة النظراء المستقلة غير مكتملة")
    if not _exp_sig:
        _key_risks.append("توقيع الخبير المرخص غير مرفق")
    if _va_missing:
        _key_risks.append("خرائط وصور ميدانية غير مرفقة")
    _next_steps: list = []
    if not _cert_allowed:
        _next_steps.append("توفير بيانات سوق حقيقية وموثقة بدلاً من محاكاة QA")
    _next_steps.append("استكمال الوثائق القانونية للعقار")
    _next_steps.append("إرفاق خرائط وصور ميدانية")
    if not _exp_sig:
        _next_steps.append("الحصول على توقيع الخبير المرخص")
    if not _prg_cert_allowed:
        _next_steps.append("إجراء مراجعة نظراء مستقلة")
    client_recommendation = {
        "recommended_value":       _rec_val_str,
        "recommended_value_range": _rec_val_range,
        "recommended_use": (
            "استرشادي / مراجعة داخلية فقط — غير صالح للاعتماد الرسمي"
            if not _cert_allowed else
            "قرار استثماري / مراجعة داخلية"
        ),
        "next_steps":              _next_steps,
        "key_risks":               _key_risks if _key_risks else ["لا مخاطر جوهرية في هذه المرحلة"],
        "required_documents_before_certification": [
            "مصادر بيانات سوق إنتاجية",
            "شهادة تصرفات عقارية",
            "رخصة البناء",
            "خرائط وصور ميدانية",
            "توقيع الخبير المرخص",
            "تقرير مراجعة النظراء",
        ],
        "recommended_action": (
            "هذا التقرير استرشادي ولا يصلح للاعتماد الرسمي. "
            "يُوصى باستكمال متطلبات الاعتماد المذكورة قبل استخدام التقرير رسمياً."
            if not _cert_allowed else
            "التقرير جاهز للمراجعة النهائية من الخبير قبل الاعتماد."
        ),
        "report_use_limitations": (
            "لا يصلح هذا التقرير للتقديم الرسمي أو الاعتماد النهائي قبل "
            "استكمال مصادر البيانات وتوقيع الخبير ومراجعة النظراء."
        ),
    }

    # ── Task 2 Part G — Valuation Fee Disclosure ─────────────────────────────
    _fee_amount    = payload.get("valuation_fee_amount") or _DATA_GAP
    _fee_basis     = payload.get("valuation_fee_basis") or "مقطوع / غير مشروط بالنتيجة"
    _fee_contingent = bool(payload.get("fee_contingent_on_value") or False)
    valuation_fee_disclosure = {
        "fee_disclosed":    True,
        "fee_amount":       _fee_amount,
        "fee_basis":        _fee_basis,
        "fee_contingent_on_value": _fee_contingent,
        "fee_independence_statement": (
            "أتعاب التقييم لا تعتمد على نتيجة القيمة أو على الوصول إلى رقم محدد. "
            "المقيِّم مستقل ولا توجد مصلحة شخصية مرتبطة بنتيجة التقييم."
        ),
        "ethics_disclosure_status": (
            "تحذير أخلاقي: الأتعاب المشروطة بالقيمة تُعد مخالفة لمعايير USPAP وIVS وأخلاقيات المهنة."
            if _fee_contingent else
            "لا توجد مخاوف أخلاقية — الأتعاب مستقلة عن نتيجة التقييم"
        ),
        "independence_declaration": (
            "يُقرّ المقيِّم باستقلاليته التامة وعدم وجود مصلحة مالية أو شخصية "
            "في العقار محل التقييم أو في نتيجة التقرير."
        ),
    }

    # ── Task 2 Part H — Report Status Visuals ────────────────────────────────
    _all_gates_passed = _cert_allowed and _cert_sig_ready and _prg_cert_allowed
    report_status_visuals = {
        "preliminary_banner_text":       "مسودة غير معتمدة — للاستخدام الداخلي فقط",
        "preliminary_watermark_text":    "PRELIMINARY / غير معتمد",
        "preliminary_banner_color_semantic": "red",
        "preliminary_advisory_note": (
            "لا يصلح هذا التقرير للتقديم الرسمي أو الاعتماد النهائي قبل "
            "استكمال مصادر البيانات وتوقيع الخبير ومراجعة النظراء."
        ),
        "certified_banner_text": (
            "تقرير معتمد — صالح للاستخدام الرسمي"
            if _all_gates_passed else
            "نسخة خبراء غير مكتملة الاعتماد — Advisory Only"
        ),
        "certified_banner_color_semantic": "green" if _all_gates_passed else "amber",
        "certification_allowed":         _all_gates_passed,
        "certification_blockers": [
            b for b in [
                _cert_block_reason        if not _cert_allowed     else "",
                "توقيع الخبير المرخص غير متوفر"   if not _cert_sig_ready  else "",
                "مراجعة النظراء المستقلة غير مكتملة" if not _prg_cert_allowed else "",
            ]
            if b
        ],
        "report_version":          payload.get("report_version") or "1.0-draft",
        "approval_date":           _exp_date,
        "approval_status":         expert_approval.get("approval_status", "pending"),
        "expert_signature_status": "متوفر" if _exp_sig else "غير مرفق",
        "peer_review_status_label": peer_review.get("peer_review_status_label", "لم تبدأ"),
        "source_quality_status": (
            f"محاكاة QA ({len(_qa_src_list)} مصدر)" if _qa_src_list else "جاهز للإنتاج"
        ),
    }

    # ── SWOT Strategic Analysis ───────────────────────────────────────────────
    _swot_qa_note  = "QA simulation / advisory" if _qa_src_list else "بيانات إنتاجية"
    _swot_hbu_sel  = hbu_analysis.get("selected_hbu", "")
    _swot_esg_score = int(esg_enhanced_context.get("esg_score", 0) or 0)
    _swot_esg_cat   = esg_enhanced_context.get("esg_category", "")
    _swot_esg_adj   = esg_enhanced_context.get("esg_terminal_value_adjustment", "")
    _swot_dcf_opt   = dcf_scenarios.get("optimistic", {}) if isinstance(dcf_scenarios, dict) else {}
    _swot_dcf_pess  = dcf_scenarios.get("pessimistic", {}) if isinstance(dcf_scenarios, dict) else {}
    _swot_dcf_spread = str(dcf_scenarios.get("scenario_spread", "") if isinstance(dcf_scenarios, dict) else "")
    _swot_legal_missing = legal_due_diligence.get("missing_documents", "") if isinstance(legal_due_diligence, dict) else ""
    _swot_condition  = str(payload.get("condition", "") or "")
    _swot_finishing  = str(payload.get("finishing_level", "") or "")
    _swot_map_avail  = visual_attachments.get("location_map_available", False)
    _swot_cv_str     = valuation_uncertainty.get("coefficient_of_variation", "") if isinstance(valuation_uncertainty, dict) else ""

    def _mk_swot(cat, key, title, desc, evidence, section, imp, prob, direction, val_note, action, src_status):
        return {
            "category": cat, "item_key": key, "title_ar": title, "description_ar": desc,
            "evidence_basis": evidence, "related_report_section": section,
            "impact_score": int(imp), "probability_score": int(prob),
            "priority_score": int(imp) * int(prob),
            "value_impact_direction": direction, "value_impact_note": val_note,
            "expert_action": action, "source_quality_status": src_status,
        }

    # --- STRENGTHS ---
    swot_strengths: list = []
    swot_strengths.append(_mk_swot(
        "strength", "location_quality",
        "الموقع الاستراتيجي",
        f"يقع العقار في {subject_district}، {subject_city} ضمن النطاق {subject_zone_id}، مما يمنحه موقعاً مؤهلاً في السوق الفرعي.",
        f"البيانات الجغرافية: {subject_location_label} — نطاق {subject_zone_id}",
        "تحليل السوق / المقارنات",
        4, 5, "positive",
        "الموقع يدعم القيمة السوقية ويعزز إمكانية التأجير والبيع.",
        "توثيق الموقع بخرائط فعلية وإحداثيات GPS.",
        _swot_qa_note,
    ))
    if _swot_condition or _swot_finishing:
        _cond_desc = f"الحالة: {_swot_condition}" + (f" | التشطيب: {_swot_finishing}" if _swot_finishing else "")
        swot_strengths.append(_mk_swot(
            "strength", "property_condition",
            "الحالة الإنشائية والتشطيب",
            f"{_cond_desc} — يقلل من نسبة الاستهلاك ويرفع القيمة.",
            f"بيانات العقار المدخلة: الحالة={_swot_condition}، التشطيب={_swot_finishing}",
            "الاستهلاك وطريقة التكلفة",
            3, 4, "positive",
            "الحالة الجيدة تعزز القيمة وتخفض نسبة الاستهلاك في نهج التكلفة.",
            "إرفاق صور ميدانية لتوثيق الحالة الفعلية.",
            _swot_qa_note,
        ))
    if _swot_hbu_sel:
        swot_strengths.append(_mk_swot(
            "strength", "hbu_current_use",
            "دعم تحليل HBU للاستخدام الحالي",
            f"يؤكد تحليل أعلى وأفضل استغلال أن الاستخدام الحالي ({_swot_hbu_sel}) هو الأمثل وفق المعطيات.",
            f"خلاصة HBU: {hbu_analysis.get('maximally_productive', '') if isinstance(hbu_analysis, dict) else ''}",
            "تحليل أعلى وأفضل استغلال",
            3, 4, "positive",
            "تأكيد HBU يعزز ثقة المستخدم في القيمة المقدرة ويدعم الاستخدام الحالي.",
            "التحقق من الترخيص الفعلي قبل اعتماد نتيجة HBU.",
            _swot_qa_note,
        ))
    if _swot_esg_score >= 20:
        swot_strengths.append(_mk_swot(
            "strength", "esg_positive",
            "درجة ESG إيجابية",
            f"حصل العقار على درجة ESG {_swot_esg_score}/40 (الفئة: {_swot_esg_cat})، "
            f"مما يعني تعديلاً إيجابياً {_swot_esg_adj} على القيمة الطرفية.",
            f"نموذج ESG الداخلي — درجة {_swot_esg_score}/40",
            "ESG والمخاطر المناخية",
            2, 3, "positive",
            f"تعديل ESG إيجابي يحسن القيمة الطرفية في DCF. الدرجة الحالية: {_swot_esg_score}/40.",
            "تحسين عوامل ESG لرفع الدرجة وزيادة التأثير الإيجابي على القيمة.",
            _swot_qa_note,
        ))
    if monthly_rent > 0:
        swot_strengths.append(_mk_swot(
            "strength", "income_generation",
            "قدرة توليد الدخل",
            f"يولد العقار إيجاراً شهرياً يقدر بـ {monthly_rent:,.0f} ج.م، مما يجعل نهج الدخل أداة تقييمية فعالة.",
            f"بيانات الإيجار المدخلة: {monthly_rent:,.0f} ج.م/شهر",
            "طريقة الدخل / رسملة الدخل المباشر",
            3, 4, "positive",
            "الدخل الإيجاري يدعم قيمة العقار ويعزز الجدوى المالية.",
            "توثيق عقود الإيجار الفعلية لدعم طريقة الدخل.",
            _swot_qa_note,
        ))

    # --- WEAKNESSES ---
    swot_weaknesses: list = []
    if _qa_src_list:
        _qa_c = len(_qa_src_list)
        swot_weaknesses.append(_mk_swot(
            "weakness", "qa_data_reliance",
            "الاعتماد على بيانات محاكاة QA",
            f"يعتمد التقرير على {_qa_c} مصادر بيانات محاكاة QA لا تعكس بيانات سوق حقيقية، "
            "مما يقيد صلاحية التقرير للاعتماد الرسمي.",
            f"بوابة جودة المصادر: {_qa_c} مصادر QA / 0 إنتاجية",
            "بوابة جودة المصادر",
            4, 5, "negative",
            "بيانات QA تضعف موثوقية القيمة المقدرة وتمنع الاعتماد الرسمي.",
            "استبدال مصادر QA ببيانات سوقية موثقة وحقيقية.",
            _swot_qa_note,
        ))
    if _swot_legal_missing:
        swot_weaknesses.append(_mk_swot(
            "weakness", "missing_legal_documents",
            "وثائق قانونية غير مكتملة",
            f"لم تقدم الوثائق القانونية: {_swot_legal_missing}. هذا الغياب يقيد التحقق من الملكية.",
            f"الفحص القانوني المبدئي: مستندات مفقودة = {_swot_legal_missing}",
            "الفحص القانوني المبدئي",
            4, 5, "negative",
            "غياب الوثائق القانونية يرفع مخاطر النزاعات ويعيق الاعتماد النهائي.",
            "طلب استكمال شهادة التصرفات ورخصة البناء والمستندات المفقودة.",
            _swot_qa_note,
        ))
    if not _swot_map_avail:
        swot_weaknesses.append(_mk_swot(
            "weakness", "missing_visual_attachments",
            "مرفقات بصرية غير مكتملة",
            "لا تتوفر خرائط موقع أو صور جوية للعقار، مما يضعف الدعم البصري للتقرير.",
            "حالة المرفقات البصرية: لا توجد إحداثيات GPS أو خرائط أو صور",
            "المرفقات البصرية",
            2, 5, "neutral",
            "غياب المرفقات البصرية لا يؤثر مباشرة على القيمة لكنه يقلل من جودة التقرير.",
            "إدخال إحداثيات GPS وإرفاق صور ميدانية وخريطة موقع قبل الاعتماد.",
            _swot_qa_note,
        ))
    if not _prg_cert_allowed:
        swot_weaknesses.append(_mk_swot(
            "weakness", "incomplete_peer_review",
            "مراجعة النظراء غير مكتملة",
            "لم تجر مراجعة نظراء مستقلة، وهو شرط ضروري للاعتماد النهائي وفق معايير IVS وUSPAP.",
            f"بوابة مراجعة النظراء: {peer_review_gate.get('peer_review_block_reason', '') if isinstance(peer_review_gate, dict) else ''}",
            "بوابة مراجعة النظراء",
            4, 5, "negative",
            "غياب مراجعة النظراء يعيق الاعتماد الرسمي ويقلل من مصداقية التقرير.",
            "إجراء مراجعة نظراء مستقلة وتوثيقها قبل الاعتماد النهائي.",
            _swot_qa_note,
        ))
    if not _cert_sig_ready:
        swot_weaknesses.append(_mk_swot(
            "weakness", "missing_expert_signature",
            "توقيع الخبير غير مرفق",
            "لا يتضمن التقرير توقيعاً من خبير مرخص، مما يجعله وثيقة استرشادية غير معتمدة.",
            "حالة اعتماد الخبير: توقيع غير مرفق",
            "توقيع واعتماد الخبير",
            5, 5, "negative",
            "غياب التوقيع يلغي الصلاحية القانونية للتقرير ويمنع استخدامه رسمياً.",
            "الحصول على توقيع الخبير المرخص مع رقم السجل والتاريخ والختم.",
            _swot_qa_note,
        ))

    # --- OPPORTUNITIES ---
    swot_opportunities: list = []
    if _swot_dcf_opt:
        _opt_val = str(_swot_dcf_opt.get("dcf_value", ""))
        _opt_rg  = _swot_dcf_opt.get("rent_growth_pct", "")
        _opt_tcr = _swot_dcf_opt.get("terminal_cap_rate_pct", "")
        swot_opportunities.append(_mk_swot(
            "opportunity", "dcf_optimistic",
            "السيناريو المتفائل في DCF",
            f"في السيناريو المتفائل، يرتفع نمو الإيجار إلى {_opt_rg}% ومعدل الرسملة الطرفي ينخفض إلى {_opt_tcr}%، "
            f"ما قد يرفع قيمة DCF إلى {_opt_val}.",
            f"تحليل سيناريو DCF: نمو إيجار {_opt_rg}%، رسملة طرفية {_opt_tcr}%",
            "سيناريوهات DCF",
            4, 3, "positive",
            "السيناريو المتفائل يظهر إمكانية تحسن ملموس في القيمة إذا تحسنت ظروف السوق.",
            "مراقبة معدلات الإيجار ومعدلات الرسملة السوقية لتقييم تحقق هذا السيناريو.",
            _swot_qa_note,
        ))
    if _qa_src_list:
        swot_opportunities.append(_mk_swot(
            "opportunity", "source_upgrade",
            "استبدال بيانات QA ببيانات إنتاجية",
            "يفتح استبدال مصادر محاكاة QA ببيانات سوق حقيقية الباب أمام الاعتماد الرسمي وإصدار تقرير معتمد.",
            "بوابة جودة المصادر: استبدال المصادر يفعل خيار الاعتماد الرسمي",
            "بوابة جودة المصادر",
            5, 4, "positive",
            "استكمال مصادر الإنتاج يحول التقرير من استرشادي إلى معتمد للاستخدام الرسمي.",
            "جمع بيانات سوق حقيقية موثقة وتحديث مصادر الجدول.",
            _swot_qa_note,
        ))
    if _swot_esg_score:
        _esg_remaining = 40 - _swot_esg_score
        swot_opportunities.append(_mk_swot(
            "opportunity", "esg_improvement",
            "تحسين درجة ESG",
            f"الدرجة الحالية {_swot_esg_score}/40 — يمكن تحقيق {_esg_remaining} نقطة إضافية بتحسين كفاءة الطاقة "
            "وإدارة النفايات وتقليل البصمة الكربونية.",
            f"نموذج ESG: درجة حالية {_swot_esg_score}/40، أقصى درجة 40",
            "ESG والمخاطر المناخية",
            3, 3, "positive",
            "رفع درجة ESG يحسن معدلات الرسملة والقيمة الطرفية ويرفع جاذبية العقار.",
            "تقييم تحسينات الكفاءة الطاقوية والبيئية وإدراجها في خطة الصيانة.",
            _swot_qa_note,
        ))
    if monthly_rent > 0:
        swot_opportunities.append(_mk_swot(
            "opportunity", "rent_growth",
            "إمكانية نمو الإيجار",
            "يشير السيناريو المتفائل في DCF إلى إمكانية تحقيق معدل نمو أعلى في الإيجار، "
            "مما سيرفع صافي دخل التشغيل والقيمة الطرفية.",
            f"الإيجار الحالي: {monthly_rent:,.0f} ج.م/شهر — معدل النمو المتفائل: {_swot_dcf_opt.get('rent_growth_pct', '') if _swot_dcf_opt else ''}%",
            "سيناريوهات DCF / طريقة الدخل",
            4, 3, "positive",
            "نمو الإيجار الإضافي يحسن العائد ويرفع القيمة الطرفية في تقييم DCF.",
            "مراقبة اتجاهات إيجارات المنطقة ومراجعة معدل النمو عند تجديد التقرير.",
            _swot_qa_note,
        ))

    # --- THREATS ---
    swot_threats: list = []
    if _swot_dcf_pess:
        _pess_val = str(_swot_dcf_pess.get("dcf_value", ""))
        _pess_rg  = _swot_dcf_pess.get("rent_growth_pct", "")
        _pess_tcr = _swot_dcf_pess.get("terminal_cap_rate_pct", "")
        swot_threats.append(_mk_swot(
            "threat", "dcf_pessimistic",
            "السيناريو المتشائم في DCF",
            f"في السيناريو المتشائم، ينخفض نمو الإيجار إلى {_pess_rg}% ويرتفع معدل الرسملة الطرفي إلى {_pess_tcr}%، "
            f"ما قد يخفض قيمة DCF إلى {_pess_val}.",
            f"تحليل سيناريو DCF: نمو إيجار {_pess_rg}%، رسملة طرفية {_pess_tcr}%",
            "سيناريوهات DCF / تحليل المخاطر",
            4, 3, "negative",
            "السيناريو المتشائم يظهر مخاطر تراجع القيمة في حالات تباطؤ السوق.",
            "تقييم احتمالية تحقق السيناريو المتشائم ومراجعة الأوزان التقديرية.",
            _swot_qa_note,
        ))
    swot_threats.append(_mk_swot(
        "threat", "legal_uncertainty",
        "المخاطر القانونية وعدم اكتمال الوثائق",
        f"غياب الوثائق القانونية ({_swot_legal_missing if _swot_legal_missing else 'لم يتم إجراء فحص كامل'}) "
        "يشكل مخاطرة قانونية تؤثر على صلاحية الاستخدام والبيع والرهن.",
        "الفحص القانوني المبدئي",
        "الفحص القانوني المبدئي",
        4, 4, "negative",
        "المخاطر القانونية تؤثر مباشرة على قابلية البيع والتمويل والاعتماد.",
        "إجراء فحص قانوني شامل من مستشار قانوني مرخص واستكمال الوثائق.",
        _swot_qa_note,
    ))
    if _cv_num_recon > 20:
        swot_threats.append(_mk_swot(
            "threat", "method_divergence",
            "تشتت بين طرق التقييم",
            f"معامل الاختلاف بين الطرق {_swot_cv_str} يشير إلى تشتت مادي، "
            "مما يثير تساؤلات حول دقة الأوزان النسبية والتوافق بين الطرق.",
            f"نطاق عدم اليقين: CV={_swot_cv_str}، نطاق القيم: {_unc_lower} — {_unc_upper}",
            "نطاق الثقة وعدم اليقين",
            3, 4, "uncertain",
            "تشتت الطرق يشير إلى احتمال إعادة تقييم الأوزان أو الافتراضات.",
            "مراجعة أوزان الطرق والافتراضات لتضييق نطاق التشتت.",
            _swot_qa_note,
        ))
    if not _all_gates_passed:
        _blockers_swot = [b for b in [
            "بوابة جودة المصادر مغلقة" if not _cert_allowed else "",
            "توقيع الخبير غير متوفر"    if not _cert_sig_ready else "",
            "مراجعة النظراء غير مكتملة" if not _prg_cert_allowed else "",
        ] if b]
        swot_threats.append(_mk_swot(
            "threat", "certification_blockage",
            "عوائق بوابة الاعتماد",
            "لا يمكن إصدار تقرير معتمد في الوضع الحالي بسبب: " + " | ".join(_blockers_swot),
            "بوابة الجودة الشاملة: بوابة المصادر + التوقيع + مراجعة النظراء",
            "بوابة جودة المصادر / توقيع الخبير / مراجعة النظراء",
            5, 5, "negative",
            "عوائق الاعتماد تمنع استخدام التقرير رسمياً وتقلل من قيمته للأطراف الخارجية.",
            "استكمال متطلبات الاعتماد (مصادر + توقيع + مراجعة نظراء) بشكل تسلسلي.",
            _swot_qa_note,
        ))
    swot_threats.append(_mk_swot(
        "threat", "market_volatility",
        "تقلبات السوق وتغير معدلات الرسملة",
        "تقلب معدلات الرسملة ومعدلات الخصم في السوق يؤثر مباشرة على القيمة؛ "
        "ارتفاع المعدل بنسبة 1% قد يخفض القيمة بشكل ملحوظ.",
        f"نطاق السيناريوهات: {_swot_dcf_spread}",
        "معدل الرسملة / سيناريوهات DCF",
        3, 3, "negative",
        "تقلب المعدلات يحدث تغيرات جوهرية في القيمة تستوجب اختبارات حساسية دورية.",
        "مراجعة معدلات الرسملة والخصم بصفة منتظمة وتحديث التقرير عند التغيير.",
        _swot_qa_note,
    ))

    _all_swot_items = swot_strengths + swot_weaknesses + swot_opportunities + swot_threats
    _all_swot_sorted = sorted(_all_swot_items, key=lambda x: x["priority_score"], reverse=True)
    _top_threat      = next((x for x in _all_swot_sorted if x["category"] == "threat"), {})
    _top_opportunity = next((x for x in _all_swot_sorted if x["category"] == "opportunity"), {})
    _swot_conclusion = (
        "يكشف التحليل الاستراتيجي SWOT أن العقار يتمتع بنقاط قوة تتعلق بالموقع والاستخدام، "
        "لكن الضعف الأبرز يتمثل في اعتماد التقرير على بيانات محاكاة QA وغياب الاعتماد الرسمي. "
        "الفرص الرئيسية تتمحور حول استبدال المصادر واستثمار السيناريو المتفائل، "
        "بينما التهديدات الأهم هي العوائق القانونية وتقلبات السوق. "
        "الحالة الراهنة: " + (
            "يستوفي التقرير جميع شروط الاعتماد" if _all_gates_passed
            else "التقرير استرشادي — يستلزم استكمال متطلبات الاعتماد"
        ) + "."
    )

    swot_analysis = {
        "strengths":               swot_strengths,
        "weaknesses":              swot_weaknesses,
        "opportunities":           swot_opportunities,
        "threats":                 swot_threats,
        "all_items_count":         len(_all_swot_items),
        "weighted_priority_matrix": _all_swot_sorted[:min(5, len(_all_swot_sorted))],
        "top_threat":              _top_threat,
        "top_opportunity":         _top_opportunity,
        "swot_conclusion":         _swot_conclusion,
        "hbu_linkage":             _swot_hbu_sel,
        "dcf_linkage":             (
            f"متفائل: {_swot_dcf_opt.get('dcf_value', '')} | "
            f"متشائم: {_swot_dcf_pess.get('dcf_value', '')} | "
            f"فارق: {_swot_dcf_spread}"
        ),
        "esg_linkage":             f"درجة ESG: {_swot_esg_score}/40 — {_swot_esg_cat}",
        "legal_risk_linkage":      (legal_due_diligence.get("legal_due_diligence_conclusion", "") if isinstance(legal_due_diligence, dict) else ""),
        "uncertainty_linkage":     f"نطاق القيمة: {_unc_lower} — {_unc_upper} | CV={_swot_cv_str}",
        "final_recommendation_linkage": (client_recommendation.get("recommended_action", "") if isinstance(client_recommendation, dict) else ""),
        "limitations": (
            "التحليل الاستراتيجي مستند إلى بيانات محاكاة QA وليس إلى بيانات سوق حقيقية. "
            "نتائج SWOT استرشادية ويجب تحديثها عند توفر بيانات إنتاجية."
            if _qa_src_list else
            "التحليل الاستراتيجي مستند إلى بيانات التقرير المتوفرة. يلزم مراجعة الخبير."
        ),
        "source_quality_advisory": bool(_qa_src_list),
    }

    # ── SWOT HBU Alignment ───────────────────────────────────────────────────
    swot_hbu_alignment = {
        "selected_hbu": _swot_hbu_sel,
        "supporting_strengths": [s["title_ar"] for s in swot_strengths if s.get("value_impact_direction") == "positive"],
        "limiting_weaknesses":  [w["title_ar"] for w in swot_weaknesses],
        "future_opportunities": [o["title_ar"] for o in swot_opportunities],
        "major_threats":        [t["title_ar"] for t in swot_threats if t["priority_score"] >= 12],
        "hbu_alignment_conclusion": (
            f"يتوافق تحليل SWOT مع اختيار HBU الحالي ({_swot_hbu_sel})، "
            "حيث تدعم نقاط القوة المرتبطة بالموقع والتشطيب استمرار الاستخدام الحالي. "
            "ومع ذلك، تبقى التوصية مشروطة باستكمال المستندات القانونية ومصادر البيانات الحقيقية."
        ),
    }

    # ── SWOT Uncertainty Linkage ─────────────────────────────────────────────
    swot_uncertainty_linkage = {
        "upper_bound": _unc_upper,
        "lower_bound": _unc_lower,
        "cv": _swot_cv_str,
        "upper_bound_drivers": [o["title_ar"] for o in swot_opportunities if o.get("value_impact_direction") == "positive"],
        "lower_bound_drivers": [t["title_ar"] for t in swot_threats if t.get("value_impact_direction") in ("negative", "uncertain")],
        "optimistic_scenario_links": [
            str(_swot_dcf_opt.get("label", "متفائل")),
            f"نمو إيجار: {_swot_dcf_opt.get('rent_growth_pct', '')}%",
        ] if _swot_dcf_opt else [],
        "pessimistic_scenario_links": [
            str(_swot_dcf_pess.get("label", "متشائم")),
            f"معدل رسملة طرفي: {_swot_dcf_pess.get('terminal_cap_rate_pct', '')}%",
        ] if _swot_dcf_pess else [],
        "uncertainty_explanation": (
            f"يعكس نطاق عدم اليقين في القيمة ({_unc_lower} — {_unc_upper}) أثر الفرص والتهديدات "
            "المحددة في SWOT؛ فالحد الأعلى يرتبط بفرص نمو الإيجار وتحسن ESG، "
            "بينما يرتبط الحد الأدنى بمخاطر الشواغر والمخاطر القانونية وتقلبات معدلات الرسملة."
        ),
    }

    # ── SWOT Recommendation Linkage ──────────────────────────────────────────
    _swot_rec_conds: list = []
    if not _cert_allowed:
        _swot_rec_conds.append("استكمال مصادر البيانات الإنتاجية")
    if not _cert_sig_ready:
        _swot_rec_conds.append("الحصول على توقيع الخبير المرخص")
    if not _prg_cert_allowed:
        _swot_rec_conds.append("إجراء مراجعة نظراء مستقلة")
    if _swot_legal_missing:
        _swot_rec_conds.append("استكمال الوثائق القانونية")

    swot_recommendation_linkage = {
        "recommended_value": (client_recommendation.get("recommended_value", "") if isinstance(client_recommendation, dict) else ""),
        "recommendation_conditioned_by": _swot_rec_conds,
        "key_strengths_supporting_recommendation": [s["title_ar"] for s in swot_strengths[:3]],
        "key_risks_limiting_recommendation": [t["title_ar"] for t in swot_threats if t["priority_score"] >= 12],
        "recommended_next_steps_from_swot": (client_recommendation.get("next_steps", []) if isinstance(client_recommendation, dict) else []),
        "swot_based_recommendation": (
            "بناء على نقاط القوة المرتبطة بالموقع والتشطيب، والفرص المرتبطة بتحسين العائد "
            "وكفاءة التشغيل، ومع مراعاة نقاط الضعف المتعلقة بجودة مصادر البيانات والمخاطر القانونية، "
            "يوصى بالقيمة المقترحة باعتبارها قيمة إرشادية مشروطة باستكمال المستندات والمراجعة النهائية."
        ),
    }

    # ── Production Readiness & Governance Blocks ──────────────────────────────

    # Part B — QA Simulation Governance Warning
    _qa_active = bool(_qa_src_list)
    _qa_value_categories = [
        "مصادر بيانات السوق", "مقارنات المبيعات",
        "أسعار الأراضي", "معاملات السوق",
    ] if _qa_active else []
    valuation_qa_simulation_governance = {
        "qa_simulation_active":           _qa_active,
        "qa_simulation_sources_count":    len(_qa_src_list),
        "qa_values_used":                 _qa_active,
        "qa_value_categories":            _qa_value_categories,
        "production_ready_sources_count": len(_prod_src_list),
        "certified_use_allowed":          not _qa_active,
        "certified_use_block_reason": (
            f"التقرير يستخدم {len(_qa_src_list)} مصدر(مصادر) محاكاة QA غير معتمدة للاستخدام الرسمي."
            if _qa_active else ""
        ),
        "advisory_label": (
            "مسودة QA استرشادية — غير صالحة للاعتماد الرسمي"
            if _qa_active else "جاهز للإنتاج"
        ),
        "required_replacement_actions": [
            "استبدال بيانات محاكاة QA ببيانات سوقية حقيقية موثقة",
            "إدخال مقارنات مبيعات حقيقية من نفس المنطقة",
            "التحقق من أسعار الأراضي من مصادر رسمية",
            "مراجعة الخبير وتوقيعه على البيانات المستبدلة",
        ] if _qa_active else [],
        "warning_text": (
            "يحتوي التقرير على بيانات محاكاة QA غير صالحة للاستخدام الرسمي أو الاعتماد النهائي. "
            "يجب استبدالها ببيانات سوقية حقيقية موثقة قبل التوقيع أو الاعتماد."
        ) if _qa_active else "",
    }

    # Part C — Sales / Rental Comparable Readiness
    _req_sales_comps  = 3
    _req_rental_comps = 3
    _actual_real_sales   = 0 if _qa_active else len(comparables or [])
    _actual_real_rental  = 0
    _qa_comps_count      = len(comparables or []) if _qa_active else 0
    _missing_comp_cats: list = []
    if _actual_real_sales < _req_sales_comps:
        _missing_comp_cats.append("مقارنات بيع حقيقية")
    if _is_rental and _actual_real_rental < _req_rental_comps:
        _missing_comp_cats.append("مقارنات إيجارية حقيقية")
    _comp_cert_allowed = (
        _actual_real_sales >= _req_sales_comps
        and (not _is_rental or _actual_real_rental >= _req_rental_comps)
        and not _qa_active
    )
    valuation_comparable_readiness = {
        "sales_comparison_ready":               _actual_real_sales >= _req_sales_comps,
        "rental_comparison_ready":              _actual_real_rental >= _req_rental_comps if _is_rental else True,
        "required_sales_comparables_count":     _req_sales_comps,
        "actual_real_sales_comparables_count":  _actual_real_sales,
        "required_rental_comparables_count":    _req_rental_comps,
        "actual_real_rental_comparables_count": _actual_real_rental,
        "qa_comparables_count":                 _qa_comps_count,
        "missing_comparable_categories":        _missing_comp_cats,
        "comparable_method_certified_use_allowed": _comp_cert_allowed,
        "comparison_block_reason": (
            "محاكاة QA — غير صالحة للاعتماد الرسمي. يجب إدخال مقارنات حقيقية موثقة."
            if (_qa_active or _missing_comp_cats) else ""
        ),
        "required_actions": [
            "إدخال صفقات بيع أو عروض إيجارية حقيقية وموثقة من نفس المنطقة "
            "مثل الزمالك، المعادي، مدينة نصر، التجمع، أو منطقة العقار محل التقييم.",
            "توثيق كل مقارنة بـ: الموقع، المساحة، قيمة الصفقة/الإيجار، التاريخ، "
            "المصدر، أساس التعديل، ومراجعة الخبير.",
        ] if (_missing_comp_cats or _qa_active) else [],
    }

    # Part D — Depreciation & Effective Age Evidence Gate
    _eff_age_used = float(
        depreciation_breakdown.get("effective_age", 0) or 0
    ) if isinstance(depreciation_breakdown, dict) else 0.0
    _eco_life = float(
        depreciation_breakdown.get("economic_life", 50) or 50
    ) if isinstance(depreciation_breakdown, dict) else 50.0
    _depr_pct_used = round(_eff_age_used / _eco_life * 100, 1) if _eco_life else 0.0
    _age_evidence_available = False
    _acceptable_evidence_types = [
        "شهادة إتمام البناء",
        "خطاب تسليم الوحدة",
        "رخصة البناء",
        "شهادة صلاحية/إشغال",
        "تقرير معاينة خبير مؤرخ ومرفق بالصور",
        "مستند رسمي من المطور أو الجهة الإدارية",
    ]
    valuation_depreciation_age_evidence_gate = {
        "property_class":      str(payload.get("property_type") or ""),
        "effective_age_used":  _eff_age_used,
        "economic_life":       _eco_life,
        "depreciation_method": "خط مستقيم",
        "depreciation_method_label": (
            "خط مستقيم (إرشادي — بانتظار توثيق العمر الفعلي)"
            if not _age_evidence_available else "خط مستقيم (موثق)"
        ),
        "age_evidence_required":             True,
        "age_evidence_available":            _age_evidence_available,
        "age_evidence_type":                 None,
        "age_evidence_id":                   None,
        "acceptable_evidence_types":         _acceptable_evidence_types,
        "depreciation_certified_use_allowed": _age_evidence_available,
        "block_reason": (
            "العمر الفعلي المستخدم في نموذج الإهلاك يحتاج إلى مستند داعم."
            if not _age_evidence_available else ""
        ),
        "required_actions": [
            "إرفاق شهادة إتمام البناء أو رخصة البناء أو ما يعادلها",
            "أو إرفاق تقرير معاينة خبير مؤرخ ومرفق بالصور يوثق العمر الفعلي",
            "مراجعة الخبير وتأكيد العمر الفعلي المستخدم",
        ],
        "warning_text": (
            "العمر الفعلي المستخدم في نموذج الإهلاك يحتاج إلى مستند داعم مثل شهادة إتمام البناء "
            "أو خطاب تسليم الوحدة أو تقرير معاينة خبير؛ وإلا قد يتم الطعن في صحة احتساب الإهلاك."
        ),
    }

    # Part E — Document Completeness & Certification Risk
    _mandatory_docs = [
        "سند الملكية / عقد الملكية / مستند الحيازة",
        "بيان مساحة أو مستند مؤيد للمساحة",
        "رخصة البناء أو شهادة إتمام البناء",
        "صور المعاينة الخارجية والداخلية",
        "خريطة الموقع أو الإحداثيات",
    ]
    _supp_docs = [
        "مستندات المقارنات أو مصادر السوق",
        "بيانات الإيجار أو عقد الإيجار" if _is_rental else None,
        "مستندات تؤيد الحالة الفنية والعمر الفعلي",
        "أي مستندات قانونية أو تنظيمية لازمة",
    ]
    _supp_docs = [d for d in _supp_docs if d]
    _submitted_docs_count = 0
    _missing_mandatory    = _mandatory_docs[:]
    _doc_completeness_score = 0.0
    valuation_document_readiness = {
        "document_completeness_score":  _doc_completeness_score,
        "required_documents_count":     len(_mandatory_docs),
        "submitted_documents_count":    _submitted_docs_count,
        "missing_mandatory_documents":  _missing_mandatory,
        "missing_supporting_documents": _supp_docs,
        "certification_risk_level":     "مرتفع" if _missing_mandatory else "منخفض",
        "certification_risk_reason": (
            "مخاطر اعتماد مرتفعة بسبب نقص المستندات الإلزامية."
            if _missing_mandatory else ""
        ),
        "valuation_certification_ready": not bool(_missing_mandatory),
        "required_actions_before_certification": [
            f"إرفاق: {doc}" for doc in _missing_mandatory
        ],
        "risk_warning_text": (
            "مخاطر اعتماد مرتفعة بسبب نقص المستندات الإلزامية. "
            "لا يُوصى بالاعتماد الرسمي قبل استكمال هذه المستندات."
        ) if _missing_mandatory else "",
    }

    # Part F — Certification Roadmap
    _roadmap_steps = [
        {"step": 1,  "title": "مسودة QA استرشادية",
         "status": "مكتمل (حالي)", "completed": True},
        {"step": 2,  "title": "معاينة ميدانية وتوثيق العمر والحالة",
         "status": "مطلوب", "completed": False},
        {"step": 3,  "title": "إدخال مقارنات سوقية/إيجارية حقيقية",
         "status": "مطلوب", "completed": False},
        {"step": 4,  "title": "إرفاق سند الملكية وبيانات المساحة والخرائط والصور",
         "status": "مطلوب", "completed": False},
        {"step": 5,  "title": "استبدال أسعار الأراضي الافتراضية بمصادر حقيقية",
         "status": "مطلوب", "completed": False},
        {"step": 6,  "title": "التحقق من المعاملات القانونية/السوقية المستخدمة",
         "status": "مطلوب", "completed": False},
        {"step": 7,  "title": "مراجعة الخبير واعتماد المصادر",
         "status": "مطلوب", "completed": False},
        {"step": 8,  "title": "ربط قاعدة بيانات المقارنات / Qdrant (مستقبلي)",
         "status": "غير مفعل — مخطط مستقبلياً", "completed": False},
        {"step": 9,  "title": "مراجعة نظراء وتوقيع الخبير",
         "status": "مطلوب", "completed": False},
        {"step": 10, "title": "تقرير تقييم صالح للاعتماد الرسمي",
         "status": "غير مكتمل — بانتظار استكمال الخطوات السابقة", "completed": False},
    ]
    _roadmap_blockers = [s["title"] for s in _roadmap_steps if not s["completed"]]
    valuation_certification_roadmap = {
        "current_stage": "مسودة QA استرشادية" if _qa_active else "جاهز للمراجعة",
        "roadmap_steps":  _roadmap_steps,
        "blockers":       _roadmap_blockers,
        "next_required_step": _roadmap_steps[1]["title"] if len(_roadmap_steps) > 1 else "",
        "estimated_readiness_status": "غير جاهز للاعتماد — يتطلب استكمال الخطوات المطلوبة",
        "certified_ready_stage_reached": False,
        "roadmap_warning": (
            "لا يُوصى بالاعتماد الرسمي قبل استكمال البنود التالية: "
            "المعاينة الميدانية، المقارنات الحقيقية، المستندات الإلزامية، "
            "مراجعة الخبير، والتوقيع النهائي."
        ),
    }

    # Part G — Geographic / Land Price Source Readiness
    _land_price_is_qa = _qa_active
    _suggested_land_sources = [
        "هيئة المجتمعات العمرانية الجديدة",
        "مستند تخصيص أرض رسمي",
        "صفقات أراضي فعلية في نفس المنطقة",
        "مقارنات سوقية معتمدة",
        "مصدر معتمد من الخبير داخل Source Registry",
    ]
    valuation_geographic_land_price_readiness = {
        "location":                    subject_location_label,
        "district":                    subject_district,
        "land_price_used":             avg_land_price_str or "غير متاح",
        "land_price_source_type":      "محاكاة QA" if _land_price_is_qa else "مصدر إنتاج",
        "land_price_source_name":      "افتراضي — QA" if _land_price_is_qa else "مصدر رسمي",
        "land_price_source_date":      None,
        "land_price_is_qa":            _land_price_is_qa,
        "land_price_production_ready": not _land_price_is_qa,
        "official_source_required":    True,
        "replacement_required":        _land_price_is_qa,
        "suggested_source_categories": _suggested_land_sources,
        "limitation_text": (
            "استبدال سعر الأرض الافتراضي بمتوسط موثق من جهة رسمية أو صفقات سوق فعلية."
        ) if _land_price_is_qa else "",
    }

    # Part H — Source Database / Qdrant Linkage Readiness
    valuation_source_database_linkage_readiness = {
        "qdrant_ready_architecture":          True,
        "qdrant_active_now":                  False,
        "rag_active_now":                     False,
        "live_database_active_now":           False,
        "previous_valuations_database_ready": False,
        "comparable_database_ready":          False,
        "integration_status": (
            "النظام مهيأ للربط، لكن لم يتم تفعيل قاعدة بيانات مصادر إنتاجية في هذه النسخة."
        ),
        "required_actions": [
            "ملء قاعدة بيانات المقارنات بصفقات حقيقية موثقة",
            "تفعيل Qdrant وربطه بسجل المصادر",
            "اختبار واسترداد المقارنات ذات الصلة للعقار محل التقييم",
        ],
        "warning_text": (
            "النظام مهيأ للربط، لكن لم يتم تفعيل قاعدة بيانات مصادر إنتاجية في هذه النسخة."
        ),
    }

    # Part I — Parameter Governance
    _cap_r_val  = float(payload.get("income_cap_rate") or 0)
    _disc_r_str = str(dr_expert_selected or "").replace("%", "").strip()
    _disc_r_val = float(_disc_r_str) if _disc_r_str else 0.0
    _gov_params = [
        {
            "parameter_name":        "معدل الرسملة",
            "value_used":            f"{_cap_r_val:.2f}%" if _cap_r_val else "غير متاح",
            "parameter_type":        "معامل سوقي",
            "reference_available":   False,
            "reference_name":        None,
            "reference_date":        None,
            "verified_by_expert":    False,
            "certified_use_allowed": False,
            "required_action":       "التحقق من معدل الرسملة من مصادر سوقية معتمدة",
        },
        {
            "parameter_name":        "معدل الخصم",
            "value_used":            f"{_disc_r_val:.2f}%" if _disc_r_val else "غير متاح",
            "parameter_type":        "معامل مالي",
            "reference_available":   False,
            "reference_name":        None,
            "reference_date":        None,
            "verified_by_expert":    False,
            "certified_use_allowed": False,
            "required_action": (
                "ربط معدل الخصم بمرجع مالي معتمد "
                "(مثل سعر فائدة البنك المركزي + علاوة المخاطر)"
            ),
        },
        {
            "parameter_name":        "سعر الأرض لكل متر مربع",
            "value_used":            avg_land_price_str or "غير متاح",
            "parameter_type":        "معامل جغرافي/سوقي",
            "reference_available":   False,
            "reference_name":        None,
            "reference_date":        None,
            "verified_by_expert":    False,
            "certified_use_allowed": False,
            "required_action":       "استبدال سعر الأرض بمصدر رسمي موثق",
        },
        {
            "parameter_name":        "العمر الاقتصادي",
            "value_used":            f"{int(_eco_life)} سنة",
            "parameter_type":        "افتراض فني",
            "reference_available":   False,
            "reference_name":        None,
            "reference_date":        None,
            "verified_by_expert":    False,
            "certified_use_allowed": False,
            "required_action":       "توثيق العمر الاقتصادي من مرجع فني أو مستند تسليم",
        },
        {
            "parameter_name":        "نسبة الإهلاك",
            "value_used":            f"{_depr_pct_used}%",
            "parameter_type":        "افتراض فني",
            "reference_available":   False,
            "reference_name":        None,
            "reference_date":        None,
            "verified_by_expert":    False,
            "certified_use_allowed": False,
            "required_action": (
                "مراجعة نسبة الإهلاك وتوثيقها بشهادة فنية أو تقرير معاينة"
            ),
        },
    ]
    _params_any_blocked = any(not p["certified_use_allowed"] for p in _gov_params)
    valuation_parameter_governance = {
        "parameters":                          _gov_params,
        "legal_or_market_reference_available": False,
        "verified_by_expert":                  False,
        "production_use_allowed":              not _params_any_blocked,
        "verification_status":                 "غير محقق — يتطلب مراجعة مرجعية",
        "required_action": (
            "المعاملات المستخدمة تحتاج إلى تحقق مرجعي ومراجعة خبير قبل الاعتماد الرسمي."
        ),
        "warning_text": (
            "المعاملات المستخدمة تحتاج إلى تحقق مرجعي ومراجعة خبير قبل الاعتماد الرسمي."
        ),
    }

    # Part J — Final Certification Status & Executive Recommendation
    _final_cert_blockers: list = []
    if valuation_qa_simulation_governance["qa_simulation_active"]:
        _final_cert_blockers.append("بيانات محاكاة QA نشطة")
    if not valuation_comparable_readiness["comparable_method_certified_use_allowed"]:
        _final_cert_blockers.append("مقارنات حقيقية غير متوفرة")
    if not valuation_depreciation_age_evidence_gate["depreciation_certified_use_allowed"]:
        _final_cert_blockers.append("دليل العمر الفعلي للإهلاك مفقود")
    if valuation_document_readiness["missing_mandatory_documents"]:
        _final_cert_blockers.append("مستندات إلزامية مفقودة")
    if valuation_geographic_land_price_readiness["replacement_required"]:
        _final_cert_blockers.append("سعر الأرض يحتاج مصدراً رسمياً")
    if _params_any_blocked:
        _final_cert_blockers.append("معاملات رئيسية غير موثقة")
    _final_cert_risk = (
        "مرتفع" if len(_final_cert_blockers) >= 4
        else ("متوسط" if len(_final_cert_blockers) >= 2 else "منخفض")
    )
    valuation_certification_status = {
        "report_status":            "qa_advisory_only" if _final_cert_blockers else "ready_for_certification",
        "certification_ready":      not bool(_final_cert_blockers),
        "certification_blockers":   _final_cert_blockers,
        "certification_risk_level": _final_cert_risk,
        "recommended_next_action": (
            "لا يُوصى بالاعتماد الرسمي قبل استكمال البنود التالية: "
            + "، ".join(_final_cert_blockers)
        ) if _final_cert_blockers else "التقرير جاهز للاعتماد الرسمي.",
        "readiness_summary": (
            f"يوجد {len(_final_cert_blockers)} عائق(عوائق) تمنع الاعتماد الرسمي."
            if _final_cert_blockers else "لا توجد عوائق — التقرير جاهز."
        ),
        "executive_recommendation": (
            "يُوصى بمعالجة العوائق المذكورة قبل تقديم التقرير للاعتماد. "
            "يجب استبدال بيانات QA ببيانات سوقية حقيقية، وإرفاق المستندات الإلزامية، "
            "ومراجعة الخبير والتوقيع قبل الاعتماد النهائي."
        ) if _final_cert_blockers else "التقرير جاهز للاعتماد الرسمي.",
    }

    # ── Risk/Decision Pass — Part B: Data Fuel Readiness ─────────────────────
    _prod_src_count = len(_prod_src_list)
    _missing_real_cats = [
        "أسعار المبيعات الحقيقية", "مقارنات الإيجار",
        "أسعار الأراضي الموثقة", "معاملات السوق المحلية",
        "معدلات الرسملة المرجعية",
    ] if _qa_active else []
    valuation_data_fuel_readiness = {
        "methodology_ready":              True,
        "data_ready":                     not _qa_active,
        "certification_ready":            not _qa_active,
        "qa_simulation_sources_count":    len(_qa_src_list),
        "real_market_sources_count":      _prod_src_count,
        "production_ready_sources_count": _prod_src_count,
        "missing_real_data_categories":   _missing_real_cats,
        "data_readiness_blockers": (
            [f"{len(_qa_src_list)} مصدر(مصادر) محاكاة QA نشطة — يجب استبدالها ببيانات سوق حقيقية"]
            if _qa_active else []
        ),
        "real_data_entry_options": [
            "إدخال يدوي للخبير لبيانات السوق المحققة",
            "رفع ملف Excel يحتوي على المقارنات",
            "إدخال مقارنات موافق عليها في سجل المصادر",
            "ربط قاعدة بيانات Qdrant مستقبلياً (غير مفعل الآن)",
        ],
        "source_replacement_required":    _qa_active,
        "data_readiness_summary": (
            "النظام مكتمل منهجياً من حيث البنية والتحليل، إلا أن التقرير لا يزال غير صالح "
            "للاعتماد الرسمي طالما أن مصادر الأسعار والمقارنات والإيجارات موسومة كمحاكاة QA."
            if _qa_active else "النظام جاهز منهجياً وبيانياً للاعتماد الرسمي."
        ),
        "required_actions": [
            "استبدال مصادر QA ببيانات سوق حقيقية موثقة",
            "توفير مقارنات مبيعات حقيقية من نفس المنطقة",
            "تحديث أسعار الأرض من مصادر رسمية معتمدة",
            "توثيق معدلات الرسملة والخصم بمصادر سوق حقيقية",
        ] if _qa_active else [],
    }

    # ── Risk/Decision Pass — Part C: Real Data Entry Path ────────────────────
    real_data_entry_readiness = {
        "manual_entry_supported":             True,
        "upload_excel_supported":             True,
        "source_registry_approval_supported": True,
        "qdrant_future_ready":                True,
        "qdrant_active_now":                  False,
        "external_api_active_now":            False,
        "required_real_data_fields": [
            "مقارنات المبيعات (3 على الأقل)",
            "مقارنات الإيجار (3 على الأقل — لتقرير الإيجار)",
            "مراجع أسعار الأرض",
            "مراجع معدل الرسملة",
            "مراجع معدل الخصم",
            "دعم تعديلات المقارنات",
            "وثائق قانونية / ملكية",
            "صور ميدانية / خرائط",
            "توقيع الخبير",
            "مراجعة النظراء",
        ],
        "expert_data_entry_checklist": [
            {"field": "مقارنات المبيعات",   "available": not _qa_active, "source": "محاكاة QA" if _qa_active else "منتج"},
            {"field": "مقارنات الإيجار",    "available": not _qa_active, "source": "محاكاة QA" if _qa_active else "منتج"},
            {"field": "مراجع أسعار الأرض", "available": not _qa_active, "source": "محاكاة QA" if _qa_active else "منتج"},
            {"field": "مراجع معدل الرسملة","available": not _qa_active, "source": "محاكاة QA" if _qa_active else "منتج"},
            {"field": "مراجع معدل الخصم",  "available": not _qa_active, "source": "محاكاة QA" if _qa_active else "منتج"},
        ],
    }

    # ── Risk/Decision Pass — Part D: Method Consistency Diagnostics ──────────
    _cv_risk = (
        "مرتفع" if _cv_v > 20
        else ("متوسط" if _cv_v > 10 else "منخفض")
    )
    _cv_color = "red" if _cv_v > 20 else ("amber" if _cv_v > 10 else "green")
    _mcd_rows = [
        {
            "method":              m["method"],
            "value":               m["value"],
            "value_formatted":     f"{m['value']:,.0f} ج.م",
            "dev_from_mean":       f"{(m['value'] - _mean_v):+,.0f} ج.م" if _mean_v else "—",
            "dev_from_mean_pct":   f"{((m['value'] - _mean_v) / _mean_v * 100):+.1f}%" if _mean_v else "—",
            "dev_from_weighted":   f"{(m['value'] - _wt_val):+,.0f} ج.م" if _wt_val else "—",
            "divergent":           abs(m["value"] - _mean_v) / _mean_v * 100 > 20 if _mean_v else False,
            "suspected_cause":     (
                "تباين مرتفع — قد يعكس مخاطر بيانات QA"
                if (abs(m["value"] - _mean_v) / _mean_v * 100 > 20 if _mean_v else False)
                else "ضمن نطاق مقبول"
            ),
        }
        for m in _method_vals_list
    ]
    _divergent_methods = [r["method"] for r in _mcd_rows if r["divergent"]]
    _suspected_causes: list = []
    if _qa_active:
        _suspected_causes.append("بيانات محاكاة QA — لا تعكس تسعير السوق الفعلي")
    if _cv_v > 20:
        _suspected_causes.append("تباين منهجي عالٍ — طريقة الدخل أو DCF تنخفض بشكل ملحوظ عن المقارنة")
    method_consistency_diagnostics = {
        "method_values":             _mcd_rows,
        "mean_value":                f"{_mean_v:,.0f} ج.م" if _mean_v else "—",
        "mean_value_raw":            _mean_v,
        "weighted_value":            f"{_wt_val:,.0f} ج.م" if _wt_val else "—",
        "weighted_value_raw":        _wt_val,
        "standard_deviation":        f"{_std_v:,.0f} ج.م" if _std_v else "—",
        "coefficient_of_variation":  f"{_cv_v:.1f}%" if _cv_v else "—",
        "cv_risk_level":             _cv_risk,
        "cv_color_semantic":         _cv_color,
        "divergence_threshold_pct":  20,
        "divergent_methods":         _divergent_methods,
        "suspected_causes":          _suspected_causes,
        "n_methods":                 len(_method_vals_list),
        "recommended_expert_review_actions": (
            ["مراجعة طريقة الدخل مقارنةً بطريقة المقارنة وتوثيق أسباب التباين"]
            if _cv_v > 20 else []
        ),
        "consistency_warning": (
            f"يوصى بمراجعة طريقة الدخل/المقارنة بسبب التباين الكبير بين المنهجيات (CV = {_cv_v:.1f}%)."
            if _cv_v > 20 else ""
        ),
    }

    # ── Risk/Decision Pass — Part E: Rent Reconciliation Explanation ─────────
    _rre_diff_pct = _rent_diff_pct_v
    _rre_explanation_required = _rre_diff_pct > 3 and bool(_rent_income_raw and _rent_final_raw)
    _rre_expert_confirm_required = _rre_explanation_required
    _rre_explanation = (
        f"تم استخدام إيجار {_rent_income_raw:,.0f} ج.م/شهر في طريقة الدخل لأنه يمثل الإيجار "
        f"الفعلي/التقديري للعقار، بينما القيمة الإيجارية النهائية {_rent_final_raw:,.0f} ج.م/شهر "
        "تم استخلاصها من متوسط المقارنات الإيجارية. ويعكس الفرق تحفظاً في التدفقات النقدية المستقبلية."
        if _rre_explanation_required else (
            "الإيجار المستخدم في طريقة الدخل يتوافق مع القيمة الإيجارية النهائية."
            if (_rent_income_raw and _rent_final_raw) else
            "تم استخدام إيجار مختلف في طريقة الدخل مقارنة بالقيمة الإيجارية النهائية، "
            "ويجب على الخبير توثيق ما إذا كان الفرق ناتجاً عن اختلاف بين الإيجار الفعلي، "
            "الإيجار السوقي، أو متوسط المقارنات."
        )
    )
    rent_reconciliation_explanation = {
        "income_method_monthly_rent":       f"{_rent_income_raw:,.0f} ج.م/شهر" if _rent_income_raw else "—",
        "income_method_monthly_rent_raw":   _rent_income_raw,
        "final_selected_monthly_rent":      f"{_rent_final_raw:,.0f} ج.م/شهر" if _rent_final_raw else "—",
        "final_selected_monthly_rent_raw":  _rent_final_raw,
        "rental_comparable_average":        f"{_rent_final_raw:,.0f} ج.م/شهر (متوسط المقارنات)" if _rent_final_raw else "—",
        "rent_difference_value":            f"{_rent_diff_abs:,.0f} ج.م/شهر" if _rent_diff_abs else "0 ج.م",
        "rent_difference_percent":          f"{_rre_diff_pct:.1f}%" if (_rent_income_raw and _rent_final_raw) else "—",
        "rent_difference_material":         _rent_material,
        "explanation_required":             _rre_explanation_required,
        "explanation_text":                 _rre_explanation,
        "expert_confirmation_required":     _rre_expert_confirm_required,
        "recommended_action": (
            "يجب على الخبير توثيق سبب الفرق بين الإيجار المستخدم والقيمة الإيجارية النهائية."
            if _rre_explanation_required else ""
        ),
    }

    # ── Risk/Decision Pass — Part F: Certification Execution Gate ────────────
    _peer_status_f = peer_review.get("peer_review_status", "not_started")
    _peer_completed = _peer_status_f in ("completed", "approved")
    _peer_reviewer_sig = bool(payload.get("peer_reviewer_signature_available") or False)
    _approval_date_avail = bool(payload.get("approval_date") or payload.get("review_updated_at"))
    _missing_execution: list = []
    _exp_name_gap = "غير متاح ضمن بيانات الطلب"
    if not (_exp_name and _exp_name != _exp_name_gap):
        _missing_execution.append("اسم الخبير غير متاح")
    if not (_exp_license and _exp_license != _exp_name_gap):
        _missing_execution.append("رقم ترخيص الخبير غير متاح")
    if not _exp_sig:
        _missing_execution.append("توقيع الخبير غير مرفق")
    if not _exp_stamp:
        _missing_execution.append("ختم الشركة غير مرفق")
    if not _peer_completed:
        _missing_execution.append("مراجعة النظراء لم تكتمل")
    if not _peer_reviewer_sig:
        _missing_execution.append("توقيع مراجع النظراء غير مرفق")
    _cert_exec_allowed = not bool(_missing_execution)
    certification_execution_gate = {
        "expert_name_available":             bool(_exp_name and _exp_name != _exp_name_gap),
        "expert_license_available":          bool(_exp_license and _exp_license != _exp_name_gap),
        "expert_signature_available":        _exp_sig,
        "company_stamp_available":           _exp_stamp,
        "approval_date_available":           _approval_date_avail,
        "peer_review_completed":             _peer_completed,
        "peer_reviewer_signature_available": _peer_reviewer_sig,
        "certification_execution_allowed":   _cert_exec_allowed,
        "missing_execution_items":           _missing_execution,
        "execution_block_reason": (
            "، ".join(_missing_execution) if _missing_execution else ""
        ),
        "advisory_only_reason": (
            "التقرير استرشادي فقط — لم يكتمل التوقيع والمراجعة قبل الاعتماد."
            if _missing_execution else ""
        ),
        "certification_banner": (
            "تقرير معتمد — صالح للاستخدام الرسمي"
            if _cert_exec_allowed else
            "مسودة استرشادية — غير صالحة للاعتماد الرسمي"
        ),
    }

    # ── Risk/Decision Pass — Part G: DCF Terminal Value Assumption Support ────
    _dcf_growth_raw = float(payload.get("dcf_growth_rate") or 5.0)
    _dcf_term_cap_raw = float(payload.get("dcf_terminal_cap_rate") or 4.5)
    _dcf_term_val_str = str(dcf_ctx.get("dcf_terminal_value", "0") or "0") if dcf_ctx else "0"
    _dcf_term_val_clean = _dcf_term_val_str.replace(",", "").replace(" ج.م", "").strip()
    try:
        _term_val_raw = float(_dcf_term_val_clean) if _dcf_term_val_clean else 0.0
    except ValueError:
        _term_val_raw = 0.0
    _growth_src_avail = bool(payload.get("dcf_growth_rate_source"))
    _term_cap_src_avail = bool(payload.get("dcf_terminal_cap_rate_source"))
    _term_src_quality = (
        "QA محاكاة" if (_qa_active and not _growth_src_avail and not _term_cap_src_avail)
        else ("جزئي" if (_growth_src_avail or _term_cap_src_avail) else "منتج")
    )
    dcf_terminal_assumption_support = {
        "long_term_growth_rate":                    f"{_dcf_growth_raw:.1f}%",
        "terminal_cap_rate":                        f"{_dcf_term_cap_raw:.1f}%",
        "terminal_value":                           f"{int(_term_val_raw):,} ج.م" if _term_val_raw else "—",
        "growth_rate_source_available":             _growth_src_avail,
        "terminal_cap_rate_source_available":       _term_cap_src_avail,
        "source_basis": (
            payload.get("dcf_growth_rate_source") or
            ("محاكاة QA — متوسط سوقي افتراضي" if _qa_active else "يتطلب مصدراً رسمياً")
        ),
        "source_quality_status":                    _term_src_quality,
        "terminal_assumption_certified_use_allowed": (
            not _qa_active and _growth_src_avail and _term_cap_src_avail
        ),
        "explanation_text": (
            "معدل النمو طويل الأمد ومعدل الرسملة النهائي مستخدمان كافتراضات تحليلية في هذه النسخة، "
            "ويحتاجان إلى توثيق بمصادر سوقية قبل الاعتماد."
        ),
        "required_actions": [
            "توثيق معدل النمو طويل الأمد بمصدر سوق رسمي (توقعات هيئة حكومية / تقرير مصرفي)",
            "توثيق معدل الرسملة النهائي من معاملات مبيعات إيجارية فعلية",
        ] if not (_growth_src_avail and _term_cap_src_avail) else [],
    }

    # ── Risk/Decision Pass — Part H: Field Visual Evidence Gate ──────────────
    _va = visual_attachments
    _ext_photo   = _va.get("exterior_photos_available", False)
    _facade_photo = _va.get("facade_photos_available", False)
    _loc_map     = _va.get("location_map_available", False)
    _gps_avail   = _va.get("gps_coordinates_available", False)
    _aerial      = _va.get("aerial_image_available", False)
    _comps_map   = _va.get("comparables_map_available", False)
    _int_photos  = _va.get("interior_photos_available", False)
    _min_vis_met = bool((_ext_photo or _facade_photo) and (_loc_map or _gps_avail))
    _missing_visual: list = []
    if not (_ext_photo or _facade_photo):
        _missing_visual.append("صورة الواجهة/الخارجية")
    if not (_loc_map or _gps_avail):
        _missing_visual.append("خريطة الموقع / الإحداثيات")
    if not _aerial:
        _missing_visual.append("صورة جوية (مستحسن)")
    if not _comps_map:
        _missing_visual.append("خريطة المقارنات (مستحسن)")
    field_visual_evidence_gate = {
        "location_map_available":             _loc_map,
        "gps_coordinates_available":          _gps_avail,
        "aerial_image_available":             _aerial,
        "comparables_map_available":          _comps_map,
        "exterior_photo_available":           _ext_photo,
        "interior_photos_available":          _int_photos,
        "facade_photo_available":             _facade_photo,
        "minimum_visual_evidence_met":        _min_vis_met,
        "visual_evidence_certified_use_allowed": _min_vis_met,
        "missing_visual_evidence":            _missing_visual,
        "warning_text": (
            "يلزم إرفاق صورة واجهة واحدة على الأقل وخريطة/إحداثيات الموقع قبل الاعتماد."
            if not _min_vis_met else ""
        ),
        "required_actions": (
            ["إرفاق صورة الواجهة الخارجية", "إرفاق خريطة الموقع أو الإحداثيات GPS"]
            if not _min_vis_met else []
        ),
    }

    # ── Risk/Decision Pass — Part I: AVM Completeness / Exclusion Decision ───
    _avm_st = avm_status
    _avm_used_flag = _avm_st.get("avm_used", False)
    _avm_inp_compl_str = str(_avm_st.get("avm_input_completeness", "0"))
    _avm_inp_pct: float = 0.0
    if "%" in _avm_inp_compl_str:
        try:
            _avm_inp_pct = float(_avm_inp_compl_str.replace("%", "").strip())
        except ValueError:
            _avm_inp_pct = 0.0
    elif "عوامل" in _avm_inp_compl_str or "عامل" in _avm_inp_compl_str:
        _avm_inp_pct = 70.0 if _avm_used_flag else 0.0
    _avm_inputs_missing: list = (
        [] if _avm_used_flag else [
            "بيانات مبيعات حقيقية للانحدار",
            "معاملات معايرة موثقة",
            "مصادر بيانات للنموذج",
        ]
    )
    _avm_reconciliation_wt = float(_avm_st.get("avm_reconciliation_weight", 0)) if _avm_used_flag else 0.0
    _avm_status_val = (
        "مُستخدم — محاكاة QA" if (_avm_used_flag and _qa_active)
        else ("مُستخدم — منتج" if _avm_used_flag else "excluded_due_to_incomplete_inputs")
    )
    avm_completeness_decision = {
        "avm_used":                       _avm_used_flag,
        "avm_input_completeness_percent": _avm_inp_pct,
        "avm_required_inputs_missing":    _avm_inputs_missing,
        "avm_value":                      _avm_st.get("avm_value", "—"),
        "avm_confidence_score":           _avm_st.get("avm_confidence_score", "—"),
        "avm_methodology_available":      _avm_used_flag,
        "avm_data_sources_available":     not _qa_active and _avm_used_flag,
        "avm_reconciliation_weight":      _avm_reconciliation_wt,
        "avm_exclusion_reason": (
            "" if _avm_used_flag else
            "لم يتم استخدام AVM لعدم اكتمال المدخلات ومصادر البيانات."
        ),
        "avm_status":                     _avm_status_val,
        "display_note": (
            "لم يتم استخدام AVM لعدم اكتمال المدخلات ومصادر البيانات."
            if not _avm_used_flag else
            "AVM مستخدم كمرجع استرشادي — محاكاة QA — لا يُعتمد في التوفيق الرسمي."
        ),
    }

    # ── Risk/Decision Pass — Part J: Risk Heatmap ────────────────────────────
    _hm_dims = [
        {
            "dimension_key": "legal",
            "label_ar":      "قانوني",
            "risk_score":    4 if not valuation_document_readiness.get("valuation_certification_ready", False) else 2,
            "key_driver":    (
                "مستندات ملكية / رخص بناء مفقودة"
                if not valuation_document_readiness.get("valuation_certification_ready", False)
                else "مستندات متوفرة"
            ),
            "mitigation_action": "توفير سند الملكية ورخصة البناء",
        },
        {
            "dimension_key": "financial",
            "label_ar":      "مالي",
            "risk_score":    4 if _cv_v > 20 else (3 if _cv_v > 10 else 2),
            "key_driver":    f"تباين عالٍ بين الطرق (CV={_cv_v:.1f}%)" if _cv_v > 20 else "تباين ضمن حدود مقبولة",
            "mitigation_action": "مراجعة طريقة الدخل وتوثيق مصادر الإيجار",
        },
        {
            "dimension_key": "physical",
            "label_ar":      "فيزيائي/فني",
            "risk_score":    3 if not _min_vis_met else 2,
            "key_driver":    "صور ميدانية وخرائط مفقودة" if not _min_vis_met else "أدلة بصرية متوفرة",
            "mitigation_action": "إرفاق صور الواجهة وخريطة الموقع",
        },
        {
            "dimension_key": "market",
            "label_ar":      "سوقي",
            "risk_score":    5 if _qa_active else 2,
            "key_driver":    "جميع بيانات السوق محاكاة QA" if _qa_active else "بيانات سوق حقيقية",
            "mitigation_action": "استبدال مصادر QA ببيانات سوق حقيقية موثقة",
        },
        {
            "dimension_key": "data_sources",
            "label_ar":      "بيانات ومصادر",
            "risk_score":    5 if _qa_active else 1,
            "key_driver":    f"{len(_qa_src_list)} مصدر QA نشط" if _qa_active else "مصادر منتجة",
            "mitigation_action": "تفعيل سجل المصادر الإنتاجية أو ربط Qdrant مستقبلاً",
        },
        {
            "dimension_key": "certification_signature",
            "label_ar":      "اعتماد وتوقيع",
            "risk_score":    5 if not _cert_exec_allowed else 1,
            "key_driver":    (
                "توقيع / ترخيص / مراجعة نظراء مفقودة"
                if not _cert_exec_allowed else "متكامل"
            ),
            "mitigation_action": "توفير توقيع الخبير المرخص ومراجعة النظراء",
        },
        {
            "dimension_key": "esg_climate",
            "label_ar":      "ESG/مناخ",
            "risk_score":    2,
            "key_driver":    "تقييم ESG أولي متاح — مناخ متوسط",
            "mitigation_action": "تعزيز بيانات الكفاءة الطاقوية والانبعاثات",
        },
    ]
    for _hd in _hm_dims:
        _s = _hd["risk_score"]
        _hd["risk_level"]    = "مرتفع" if _s >= 4 else ("متوسط" if _s >= 3 else "منخفض")
        _hd["color_semantic"] = "red"   if _s >= 4 else ("amber"  if _s >= 3 else "green")
    _overall_risk_score = round(sum(d["risk_score"] for d in _hm_dims) / len(_hm_dims), 1)
    _overall_risk_lvl = "مرتفع" if _overall_risk_score >= 4 else ("متوسط" if _overall_risk_score >= 3 else "منخفض")
    _highest_dim = max(_hm_dims, key=lambda d: d["risk_score"])
    valuation_risk_heatmap = {
        "dimensions":             _hm_dims,
        "overall_risk_score":     _overall_risk_score,
        "overall_risk_level":     _overall_risk_lvl,
        "highest_risk_dimension": _highest_dim["label_ar"],
        "heatmap_summary": (
            f"المخاطر الكلية {_overall_risk_lvl} — البُعد الأعلى خطورة: "
            f"{_highest_dim['label_ar']} (درجة {_highest_dim['risk_score']}/5)."
        ),
        "mitigation_actions": [d["mitigation_action"] for d in _hm_dims if d["risk_score"] >= 3],
    }

    # ── Risk/Decision Pass — Part K: Certification Timeline ──────────────────
    _tl_steps = [
        {"step": 1, "title": "فحص ميداني وتوثيق الموقع",                 "estimated_days": 1, "status": "pending"},
        {"step": 2, "title": "جمع مقارنات المبيعات والإيجار الحقيقية",    "estimated_days": 3, "status": "pending"},
        {"step": 3, "title": "جمع الوثائق القانونية وسند الملكية",        "estimated_days": 4, "status": "pending"},
        {"step": 4, "title": "التحقق من مصادر الأرض / الرسملة / الخصم",  "estimated_days": 2, "status": "pending"},
        {"step": 5, "title": "مراجعة النظراء",                           "estimated_days": 2, "status": "pending"},
        {"step": 6, "title": "التوقيع النهائي والختم",                   "estimated_days": 1, "status": "pending"},
    ]
    _tl_total = sum(s_["estimated_days"] for s_ in _tl_steps)
    certification_timeline = {
        "total_estimated_days": _tl_total,
        "steps":                _tl_steps,
        "timeline_notes": (
            "الجدول الزمني تقديري استرشادي — ليس ضماناً أو التزاماً قانونياً. "
            "قد تتغير المدد بحسب تعقيد الملف وتوافر البيانات والمراجعة."
        ),
        "advisory_label": "جدول زمني استرشادي",
    }

    # ── Risk/Decision Pass — Part L: Break-Even Rent Analysis ────────────────
    _mkt_val_raw = float(_sel_val_num) if _sel_val_num else float(payload.get("estimated_value") or 0)
    _cost_of_capital_pct = float(payload.get("cost_of_capital") or 8.0)
    _annual_maint_raw = float(
        payload.get("annual_maintenance_cost") or
        (_mkt_val_raw * 0.01 if _mkt_val_raw else 0)
    )
    _be_available = bool(_mkt_val_raw)
    _be_monthly: float = 0.0
    if _be_available:
        _be_monthly = round(
            (_mkt_val_raw * _cost_of_capital_pct / 100 + _annual_maint_raw) / 12, 0
        )
    _current_rent_be = _rent_income_raw or _rent_final_raw
    _rent_gap_val = (_current_rent_be - _be_monthly) if (_current_rent_be and _be_monthly) else 0.0
    _rent_gap_pct_be = (_rent_gap_val / _be_monthly * 100) if _be_monthly else 0.0
    _be_interpretation = (
        f"الإيجار الحالي/المتوقع ({_current_rent_be:,.0f} ج.م/شهر) "
        + ("يتجاوز" if _rent_gap_val > 0 else "يقل عن")
        + f" نقطة التعادل ({_be_monthly:,.0f} ج.م/شهر)"
        + f" بفارق {abs(_rent_gap_pct_be):.1f}%."
        if (_current_rent_be and _be_monthly) else
        "بيانات غير كافية لتحليل نقطة التعادل."
    )
    break_even_rent_analysis = {
        "market_value":                    f"{_mkt_val_raw:,.0f} ج.م" if _mkt_val_raw else "—",
        "market_value_raw":                _mkt_val_raw,
        "cost_of_capital_pct": (
            f"{_cost_of_capital_pct:.1f}% (افتراضي استرشادي)"
            if not payload.get("cost_of_capital") else f"{_cost_of_capital_pct:.1f}%"
        ),
        "annual_maintenance_cost":         f"{_annual_maint_raw:,.0f} ج.م/سنة",
        "break_even_monthly_rent":         f"{_be_monthly:,.0f} ج.م/شهر" if _be_monthly else "—",
        "break_even_monthly_rent_raw":     _be_monthly,
        "current_or_expected_monthly_rent": f"{_current_rent_be:,.0f} ج.م/شهر" if _current_rent_be else "—",
        "rent_gap_value":                  f"{abs(_rent_gap_val):,.0f} ج.م/شهر" if _rent_gap_val else "—",
        "rent_gap_percent":                f"{abs(_rent_gap_pct_be):.1f}%" if _rent_gap_pct_be else "—",
        "rent_above_break_even":           (_rent_gap_val > 0) if (_current_rent_be and _be_monthly) else None,
        "interpretation":                  _be_interpretation,
        "investor_decision_note": (
            "هذا المؤشر استرشادي فقط لدعم قرار المستثمر — لا يُعدّ نصيحة استثمارية. "
            "يُنصح بمراجعة الخبير قبل اتخاذ أي قرار استثماري."
        ),
        "data_complete":                   _be_available,
        "cost_of_capital_is_advisory":     not bool(payload.get("cost_of_capital")),
    }

    # ── Risk/Decision Pass — Part M: Compliance Dashboard ────────────────────
    _hbu_ok        = bool(hbu_analysis.get("hbu_four_tests_present"))
    _assumptions_ok = bool(assumptions_registry)
    _sow_ok         = bool(scope_of_work)
    _src_gov_ok     = bool(source_registry_summary)
    _real_data_ok   = not _qa_active
    _legal_ok       = bool(legal_due_diligence.get("title_deed_available"))
    _photos_ok      = _min_vis_met
    _dcf_assump_ok  = bool(_growth_src_avail and _term_cap_src_avail)
    _peer_rev_ok    = _peer_completed
    _sig_ok_comp    = _exp_sig
    _uncertainty_ok = bool(_std_v > 0)
    _esg_ok         = bool(esg_enhanced_context.get("esg_score", 0))
    _fee_ok         = bool(valuation_fee_disclosure)

    def _ci(label: str, status: str, is_blocker: bool = False) -> dict:
        return {"item": label, "status": status, "is_blocker": is_blocker}

    _comp_items = [
        _ci("HBU مطبق",                          "complete" if _hbu_ok else "missing",        True),
        _ci("الافتراضات موثقة",                   "complete" if _assumptions_ok else "missing", True),
        _ci("تأثير الافتراضات الاستثنائية مبين",  "complete" if extraordinary_assumptions else "advisory_only"),
        _ci("نطاق العمل مكتمل",                   "complete" if _sow_ok else "missing",        True),
        _ci("حوكمة المصادر مكتملة",              "complete" if _src_gov_ok else "missing",     True),
        _ci("بيانات سوق حقيقية متوفرة",           "complete" if _real_data_ok else "blocker",  True),
        _ci("العناية القانونية موثقة",            "complete" if _legal_ok else "missing",       True),
        _ci("صور وخرائط مرفقة",                  "complete" if _photos_ok else "missing",      True),
        _ci("افتراضات DCF موثقة",                 "complete" if _dcf_assump_ok else "advisory_only"),
        _ci("مراجعة النظراء مكتملة",             "complete" if _peer_rev_ok else "blocker",    True),
        _ci("توقيع الخبير مرفق",                 "complete" if _sig_ok_comp else "blocker",    True),
        _ci("نطاق عدم اليقين مبين",              "complete" if _uncertainty_ok else "missing"),
        _ci("مخاطر ESG/مناخ مبينة",              "complete" if _esg_ok else "advisory_only"),
        _ci("الإفصاح عن الرسوم مبين",            "complete" if _fee_ok else "advisory_only"),
    ]
    _comp_completed = sum(1 for i in _comp_items if i["status"] == "complete")
    _comp_missing   = sum(1 for i in _comp_items if i["status"] in ("missing", "blocker"))
    _comp_blockers  = [
        i["item"] for i in _comp_items
        if i["status"] == "blocker" or (i["is_blocker"] and i["status"] == "missing")
    ]
    _comp_overall = (
        "غير جاهز — عوائق حرجة" if _comp_blockers
        else ("جزئي — عناصر ناقصة" if _comp_missing > 0 else "مكتمل")
    )
    valuation_compliance_dashboard = {
        "compliance_items":  _comp_items,
        "completed_count":   _comp_completed,
        "missing_count":     _comp_missing,
        "overall_status":    _comp_overall,
        "blocking_items":    _comp_blockers,
        "total_items":       len(_comp_items),
        "completion_pct":    round(_comp_completed / len(_comp_items) * 100, 0) if _comp_items else 0,
    }

    # ── Risk/Decision Pass — Part N: Mass Appraisal Reference ────────────────
    _ma = mass_appraisal_bridge
    _ma_avg_price_str = str(_ma.get("mass_average_price_per_m2", "") or "") if _ma else ""
    _ma_est_val_str   = str(_ma.get("mass_model_value", "") or "") if _ma else ""
    _ma_conf          = _ma.get("mass_data_quality_score", "—") if _ma else "—"
    _ma_used          = bool(_ma and _ma_est_val_str and _qa_active)
    mass_appraisal_reference = {
        "mass_appraisal_used":       _ma_used,
        "average_area_price":        _ma_avg_price_str if _ma_avg_price_str else "—",
        "estimated_reference_value": _ma_est_val_str if _ma_est_val_str else "—",
        "source_available":          not _qa_active,
        "source_quality_status":     "QA محاكاة" if _qa_active else "منتج",
        "confidence_level":          _ma_conf,
        "reconciliation_weight":     0.0,
        "limitation_text": (
            "مرجع تقييم جماعي استرشادي — غير مستخدم في التوفيق النهائي "
            "لعدم توافر قاعدة بيانات إنتاجية."
        ),
        "display_note": (
            "AVM / التقييم الجماعي — محاكاة QA — مرجع استرشادي فقط."
            if _qa_active else
            "مرجع تقييم جماعي منتج — غير مستخدم في التوفيق النهائي."
        ),
    }

    # ── Risk/Decision Pass — Part O: Investment Decision Summary ─────────────
    _rec_val_disp = (
        f"{int(_rent_final_raw):,} ج.م/شهر"
        if (_is_rental and _rent_final_raw) else (
            f"{int(_sel_val_num):,} ج.م" if _sel_val_num else "—"
        )
    )
    _neg_margin = 5.0
    _neg_low  = int(_sel_val_num * (1 - _neg_margin / 100)) if _sel_val_num else 0
    _neg_high = int(_sel_val_num * (1 + _neg_margin / 100)) if _sel_val_num else 0
    _inv_conditions: list = []
    if _qa_active:
        _inv_conditions.append("استبدال بيانات QA ببيانات سوق حقيقية")
    if valuation_document_readiness.get("missing_mandatory_documents"):
        _inv_conditions.append("استكمال الوثائق القانونية الإلزامية")
    if not _exp_sig:
        _inv_conditions.append("الحصول على توقيع الخبير المرخص")
    if not _peer_completed:
        _inv_conditions.append("إتمام مراجعة النظراء")
    if not _min_vis_met:
        _inv_conditions.append("إرفاق صور الواجهة وخريطة الموقع")
    _is_advisory_dec = bool(_final_cert_blockers)
    _rec_decision = (
        "توصية مشروطة — استرشادية" if _is_advisory_dec else "توصية نهائية — جاهز للاعتماد"
    )
    _decision_text = (
        (
            f"يُنصح باستخدام القيمة الإرشادية البالغة {_rec_val_disp} مع هامش تفاوض ±{_neg_margin:.0f}%"
            + (f"، بشرط: {' ، '.join(_inv_conditions)}." if _inv_conditions else ".")
            + " هذه التوصية استرشادية وتتطلب تأكيداً من الخبير قبل أي استخدام رسمي."
        ) if _is_advisory_dec else
        f"التقرير جاهز للاعتماد. القيمة الموصى بها: {_rec_val_disp}. هامش التفاوض: ±{_neg_margin:.0f}%."
    )
    investment_decision_summary = {
        "recommended_decision":    _rec_decision,
        "recommended_value":       _rec_val_disp,
        "negotiation_margin_percent": _neg_margin,
        "negotiation_range_low":   f"{_neg_low:,} ج.م" if _neg_low else "—",
        "negotiation_range_high":  f"{_neg_high:,} ج.م" if _neg_high else "—",
        "key_conditions":          _inv_conditions,
        "must_resolve_before_financing_or_sale": _inv_conditions,
        "decision_summary_text":   _decision_text,
        "is_advisory":             _is_advisory_dec,
        "advisory_label": (
            "قرار استثماري مشروط — استرشادي"
            if _is_advisory_dec else "قرار استثماري نهائي"
        ),
        "investor_note": (
            "هذا الملخص مخصص لدعم القرار — لا يُغني عن نصيحة مالية أو قانونية متخصصة."
        ),
    }

    result = {
        "comparables":              comparables,
        "avg_adjusted_price":       avg_adj,
        "sales_from_comps":         sales_from_comps_str,
        "has_comparables":          bool(comparables and adj_prices),
        **map_ctx,
        "land_comps":               land_comps,
        "avg_land_price":           avg_land_price_str,
        "land_value_by_sales":      land_value_by_sales_str,
        **land_extraction_ctx,
        "land_value_reconciled":        land_value_reconciled,
        "land_value_expert_selected":   land_value_expert_selected,
        "cost_breakdown":           cost_breakdown,
        "cost_breakdown_total":     cost_breakdown_total,
        **income_ctx,
        **dcf_ctx,
        "discount_rate_methods":    discount_rate_methods,
        "dr_average":               dr_average,
        "dr_expert_selected":       dr_expert_selected,
        "dr_notes":                 dr_notes,
        "terminal_cap_methods":     terminal_cap_methods,
        "tc_average":               tc_average,
        "tc_expert_selected":       tc_expert_selected,
        "tc_notes":                 tc_notes,
        **cost_ctx,
        "avm_regression":           avm_regression,
        "avm_reg_base_value":       avm_reg_base_value,
        "avm_reg_coeff_total":      avm_reg_coeff_total,
        "avm_reg_predicted":        avm_reg_predicted,
        "avm_reg_residual":         avm_reg_residual,
        "avm_reg_final":            avm_reg_final,
        "avm_reg_confidence_band":  avm_reg_confidence_band,
        "avm_reg_limitations":      avm_reg_limitations,
        # ── New data-binding structures ────────────────────────────────────
        "price_source_data":        price_source_data,
        "mass_appraisal_bridge":    mass_appraisal_bridge,
        "cap_rate_derivation":      cap_rate_derivation,
        "_data_gap_label":          _DATA_GAP,
        "_expert_fill_label":       _EXPERT_FILL,
        "_na_purpose_label":        _NA_PURPOSE,
        # ── Purpose / date-basis / rental ─────────────────────────────────
        "purpose_info":             purpose_info,
        "date_basis_info":          date_basis_info,
        "is_rental_purpose":        _is_rental,
        "rental_value_context":     rental_value_context,
        # ── Geographic context (Part A) ────────────────────────────────────
        "subject_zone_id":          subject_zone_id,
        "subject_district":         subject_district,
        "subject_city":             subject_city,
        "subject_sub_market":       subject_sub_market,
        "subject_location_label":   subject_location_label,
        "geo_disclaimer":           _GEO_DISCLAIMER,
        "adj_prices_excluded_count": len(adj_prices_excluded),
        # ── Shared land value (Part C) ─────────────────────────────────────
        **shared_land_ctx,
        # ── Cap rate governance (Part E) ───────────────────────────────────
        **cap_rate_governance,
        # ── Preliminary vs Certified diff (Part D) ─────────────────────────
        "prelim_vs_certified":      prelim_vs_certified,
        # ── Cost basis label (Part B) ──────────────────────────────────────
        "cost_area_basis":          f"{area:.0f} م² (مساحة العقار من المدخلات)",
        # ── ESG financial linkage (Part H) ────────────────────────────────
        **esg_context,
        # ── Scenario integrity metadata ────────────────────────────────────
        "scenario_subject_area":    area,
        "scenario_subject_zone_id": subject_zone_id,
        "scenario_subject_district": subject_district,
        # ── Source Registry (readiness layer — Parts A–D+G) ────────────────
        "source_registry":           source_registry,
        "source_method_links":       source_method_links,
        "source_registry_summary":   source_registry_summary,
        "qdrant_readiness_summary":  qdrant_readiness_summary,
        # ── Advanced Methodology & Compliance (Parts B–L) ──────────────────
        "hbu_analysis":                  hbu_analysis,
        "direct_capitalization_context": direct_capitalization_context,
        "direct_capitalization_result":  direct_capitalization_context["direct_capitalization_result"],
        "dcf_result":                    direct_capitalization_context["dcf_result"],
        "dcf_reconciliation_weight":     direct_capitalization_context["dcf_reconciliation_weight"],
        "income_direct_vs_dcf_explanation": direct_capitalization_context["income_direct_vs_dcf_explanation"],
        "comparable_adjustment_support": comparable_adjustment_support,
        "assumptions_registry":          assumptions_registry,
        "extraordinary_assumptions":     extraordinary_assumptions,
        "hypothetical_conditions":       hypothetical_conditions,
        "scope_limitations":             scope_limitations,
        "depreciation_breakdown":        depreciation_breakdown,
        "dcf_scenarios":                 dcf_scenarios,
        "legal_due_diligence":           legal_due_diligence,
        "esg_enhanced_context":          esg_enhanced_context,
        "esg_score":                     esg_enhanced_context["esg_score"],
        "esg_category":                  esg_enhanced_context["esg_category"],
        "esg_terminal_value_adjustment": esg_enhanced_context["esg_terminal_value_adjustment"],
        "esg_value_impact":              esg_enhanced_context["esg_value_impact"],
        "climate_risk_score":            esg_enhanced_context["climate_risk_score"],
        "climate_risk_notes":            esg_enhanced_context["climate_risk_notes"],
        "environmental_impact_assessment": environmental_impact_assessment,
        "valuation_uncertainty":         valuation_uncertainty,
        "peer_review":                   peer_review,
        # ── Task 1 new keys ───────────────────────────────────────────────
        "source_quality_gate":           source_quality_gate,
        "final_reconciliation":          final_reconciliation,
        "standards_compliance":          standards_compliance,
        "expert_approval":               expert_approval,
        "scope_of_work":                 scope_of_work,
        # ── Task 2 new keys ───────────────────────────────────────────────
        "peer_review_gate":              peer_review_gate,
        "visual_attachments":            visual_attachments,
        "avm_status":                    avm_status,
        "rent_consistency_check":        rent_consistency_check,
        "client_recommendation":         client_recommendation,
        "valuation_fee_disclosure":      valuation_fee_disclosure,
        "report_status_visuals":         report_status_visuals,
        # ── SWOT Strategic Analysis keys ──────────────────────────────────────
        "swot_analysis":               swot_analysis,
        "swot_hbu_alignment":          swot_hbu_alignment,
        "swot_uncertainty_linkage":    swot_uncertainty_linkage,
        "swot_recommendation_linkage": swot_recommendation_linkage,
        # ── Production Readiness & Governance keys ────────────────────────────
        "valuation_qa_simulation_governance":          valuation_qa_simulation_governance,
        "valuation_comparable_readiness":              valuation_comparable_readiness,
        "valuation_depreciation_age_evidence_gate":    valuation_depreciation_age_evidence_gate,
        "valuation_document_readiness":                valuation_document_readiness,
        "valuation_certification_roadmap":             valuation_certification_roadmap,
        "valuation_geographic_land_price_readiness":   valuation_geographic_land_price_readiness,
        "valuation_source_database_linkage_readiness": valuation_source_database_linkage_readiness,
        "valuation_parameter_governance":              valuation_parameter_governance,
        "valuation_certification_status":              valuation_certification_status,
        # ── Filing/Certification Readiness Gate — canonical alias keys ───────
        "valuation_comparison_real_data_readiness":    valuation_comparable_readiness,
        "valuation_document_certification_risk":       valuation_document_readiness,
        "valuation_production_readiness_roadmap":      valuation_certification_roadmap,
        "valuation_final_certification_status":        valuation_certification_status,
        # ── Risk/Decision Pass context keys ────────────────────────────────
        "valuation_data_fuel_readiness":          valuation_data_fuel_readiness,
        "real_data_entry_readiness":              real_data_entry_readiness,
        "method_consistency_diagnostics":         method_consistency_diagnostics,
        "rent_reconciliation_explanation":        rent_reconciliation_explanation,
        "certification_execution_gate":           certification_execution_gate,
        "dcf_terminal_assumption_support":        dcf_terminal_assumption_support,
        "field_visual_evidence_gate":             field_visual_evidence_gate,
        "avm_completeness_decision":              avm_completeness_decision,
        "valuation_risk_heatmap":                 valuation_risk_heatmap,
        "certification_timeline":                 certification_timeline,
        "break_even_rent_analysis":               break_even_rent_analysis,
        "valuation_compliance_dashboard":         valuation_compliance_dashboard,
        "mass_appraisal_reference":               mass_appraisal_reference,
        "investment_decision_summary":            investment_decision_summary,
    }
    return result


# ── Suspicious area values (leaked from test counts or unrelated numbers) ────
_SUSPICIOUS_AREA_VALUES: frozenset = frozenset({
    2120, 7241, 7342, 247, 313, 401, 700, 3766,
})


def _is_suspicious_area(v: float) -> bool:
    """Return True if the area value looks like a leaked test-count or suite number."""
    return int(v) in _SUSPICIOUS_AREA_VALUES


def _validate_scenario_data_integrity(method_context: dict) -> list[str]:
    """
    Validate that a built method_context has internally consistent scenario data.

    Returns a list of error strings. Empty list means all checks pass.

    Checks:
    1. Subject area is not a suspicious test-count value.
    2. Included sales comparables share the subject zone_id.
    3. Included land comparables share the subject zone_id.
    4. Included AVM/price sources share the subject zone_id.
    5. Mass appraisal bridge zone matches subject zone.
    6. Sales comparison value is non-zero for market QA.
    7. Rental comparables (if present) share the subject zone_id for included rows.
    8. AVM regression area value matches scenario area.
    """
    errors: list[str] = []

    subject_area     = float(method_context.get("scenario_subject_area") or 0)
    subject_zone_id  = str(method_context.get("scenario_subject_zone_id") or "")
    subject_district = str(method_context.get("scenario_subject_district") or "")
    is_rental        = bool(method_context.get("is_rental_purpose"))

    # 1. Area guard
    if subject_area and _is_suspicious_area(subject_area):
        errors.append(
            f"AREA_LEAK: subject_area={int(subject_area)} matches a known test-count value "
            f"({sorted(_SUSPICIOUS_AREA_VALUES)}). Verify the payload area field."
        )

    # 2. Included sales comparables geography
    for comp in method_context.get("comparables", []):
        geo = comp.get("geo_match_status", "مطابق")
        comp_zone = comp.get("comparable_zone_id", "")
        if geo not in ("خارج النطاق",) and comp_zone and subject_zone_id:
            if comp_zone != subject_zone_id:
                errors.append(
                    f"COMP_GEO_MISMATCH: included comparable '{comp.get('location')}' "
                    f"zone={comp_zone} != subject zone={subject_zone_id}"
                )

    # 3. Included land comparables geography
    for lc in method_context.get("land_comps", []):
        geo = lc.get("geo_match_status", "مطابق")
        lc_zone = lc.get("zone_id", "")
        if geo not in ("خارج النطاق",) and lc_zone and subject_zone_id:
            if lc_zone != subject_zone_id:
                errors.append(
                    f"LAND_COMP_GEO_MISMATCH: included land comp '{lc.get('location')}' "
                    f"zone={lc_zone} != subject zone={subject_zone_id}"
                )

    # 4. Included price sources geography
    for src in method_context.get("price_source_data", []):
        geo_use = src.get("geo_use_status", "مُدرج")
        src_zone = src.get("zone_id", "")
        if geo_use not in ("مستبعد جغرافيًا",) and src_zone and subject_zone_id:
            if src_zone != subject_zone_id:
                errors.append(
                    f"PRICE_SOURCE_GEO_MISMATCH: included source '{src.get('source_registry_id')}' "
                    f"zone={src_zone} != subject zone={subject_zone_id}"
                )

    # 5. Mass appraisal bridge zone
    mass_zone = method_context.get("mass_appraisal_bridge", {}).get("mass_zone_id", "")
    if mass_zone and subject_zone_id and mass_zone != subject_zone_id:
        errors.append(
            f"MASS_APPRAISAL_ZONE_MISMATCH: mass_zone_id={mass_zone} "
            f"!= subject_zone_id={subject_zone_id}"
        )

    # 6. Sales comparison value non-zero for non-rental market QA
    if not is_rental:
        sales_str = str(method_context.get("sales_from_comps") or "")
        sales_num = 0.0
        try:
            sales_num = float(
                sales_str.replace(",", "").replace(" ج.م", "").strip()
            ) if sales_str else 0.0
        except (ValueError, TypeError):
            pass
        if sales_num == 0:
            errors.append(
                "SALES_COMP_ZERO: sales_from_comps is 0 or empty for a non-rental market scenario. "
                "Check that sales comparables have valid price_per_m2 values."
            )

    # 7. Included rental comparables geography
    rental_ctx = method_context.get("rental_value_context", {})
    for rc in rental_ctx.get("rental_comparables", []):
        geo = rc.get("geo_match_status", "مطابق")
        rc_zone = rc.get("zone_id", "")
        if geo not in ("خارج النطاق",) and rc_zone and subject_zone_id:
            if rc_zone != subject_zone_id:
                errors.append(
                    f"RENTAL_COMP_GEO_MISMATCH: included rental comp '{rc.get('location')}' "
                    f"zone={rc_zone} != subject zone={subject_zone_id}"
                )

    # 8. AVM regression area consistency
    avm_rows = method_context.get("avm_regression", [])
    for row in avm_rows:
        if "مساحة" in str(row.get("feature", "")):
            try:
                avm_area = float(str(row.get("value", "0")).replace(",", ""))
                if subject_area and abs(avm_area - subject_area) > 0.01:
                    errors.append(
                        f"AVM_AREA_MISMATCH: AVM regression area={avm_area} "
                        f"!= scenario area={subject_area}"
                    )
            except (ValueError, TypeError):
                pass

    return errors


def _validate_source_registry_integrity(method_context: dict) -> list[str]:
    """
    Validate Source Registry readiness layer in a built method_context.

    Returns a list of error strings. Empty list means all checks pass.

    Checks:
    1. Every included comparable has a source_id.
    2. Every source used in formulas exists in source_registry.
    3. No excluded/out-of-zone source is used in calculations.
    4. Every method has source_method_links.
    5. Qdrant flags remain disabled.
    6. No source claims live retrieval.
    7. No source has missing zone_id if it affects valuation.
    8. No duplicate source_id.
    """
    errors: list[str] = []

    source_registry   = method_context.get("source_registry", [])
    source_links      = method_context.get("source_method_links", {})
    qdrant_readiness  = method_context.get("qdrant_readiness_summary", {})
    registry_summary  = method_context.get("source_registry_summary", {})

    # 1. Every included source in source_registry has a source_id
    for src in source_registry:
        if src.get("geo_use_status", "مُدرج") != "مستبعد جغرافيًا":
            sid = src.get("source_id") or src.get("source_registry_id")
            if not sid:
                errors.append(
                    f"SRC_REG_MISSING_ID: included source record "
                    f"'{src.get('source_label', src.get('source_type', '?'))}' has no source_id"
                )

    # 2. Every source used in formulas exists in source_registry
    _reg_ids = {
        s.get("source_id") or s.get("source_registry_id", "")
        for s in source_registry
        if s.get("source_id") or s.get("source_registry_id")
    }
    for method, ids in source_links.items():
        for sid in ids:
            if sid and sid not in _reg_ids:
                errors.append(
                    f"SRC_REG_ORPHAN_LINK: source_method_links['{method}'] references "
                    f"'{sid}' which is not in source_registry"
                )

    # 3. No excluded/out-of-zone source is used in calculations
    for src in source_registry:
        geo_use = src.get("geo_use_status", "مُدرج")
        if geo_use == "مستبعد جغرافيًا":
            sid = src.get("source_id") or src.get("source_registry_id", "")
            for method, ids in source_links.items():
                if sid and sid in ids:
                    errors.append(
                        f"SRC_REG_EXCLUDED_IN_FORMULA: excluded source '{sid}' "
                        f"appears in source_method_links['{method}']"
                    )

    # 4. Every method has source_method_links (key must exist; empty list is OK)
    _REQUIRED_METHODS = ["AVM", "مقارنة البيوع", "قيمة الأرض", "طريقة الدخل", "DCF"]
    for m in _REQUIRED_METHODS:
        if m not in source_links:
            errors.append(
                f"SRC_REG_NO_METHOD_LINK: method '{m}' missing from source_method_links"
            )

    # 5. Qdrant flags remain disabled
    if qdrant_readiness.get("qdrant_enabled") is True:
        errors.append("SRC_REG_QDRANT_ENABLED: qdrant_enabled=True — must remain False")
    if qdrant_readiness.get("rag_enabled") is True:
        errors.append("SRC_REG_RAG_ENABLED: rag_enabled=True — must remain False")
    if qdrant_readiness.get("internet_ingestion_enabled") is True:
        errors.append("SRC_REG_INTERNET_ENABLED: internet_ingestion_enabled=True — must remain False")

    # 6. No source claims live retrieval
    _FORBIDDEN_CLAIMS = ("retrieved_from_qdrant", "live_qdrant", "qdrant_active: true", "internet_search_result")
    import json as _json_mod
    _raw_registry = _json_mod.dumps(source_registry, ensure_ascii=False, default=str).lower()
    for _claim in _FORBIDDEN_CLAIMS:
        if _claim.lower() in _raw_registry:
            errors.append(f"SRC_REG_LIVE_CLAIM: source registry contains forbidden claim '{_claim}'")

    # 7. No source missing zone_id if it affects valuation (included in formulas)
    for src in source_registry:
        geo_use = src.get("geo_use_status", "مُدرج")
        if geo_use != "مستبعد جغرافيًا":
            if not src.get("zone_id"):
                sid = src.get("source_id") or src.get("source_registry_id", "?")
                errors.append(
                    f"SRC_REG_MISSING_ZONE: included source '{sid}' has no zone_id"
                )

    # 8. No duplicate source_id
    _seen_ids: list = []
    for src in source_registry:
        sid = src.get("source_id") or src.get("source_registry_id", "")
        if sid:
            if sid in _seen_ids:
                errors.append(f"SRC_REG_DUPLICATE_ID: source_id '{sid}' appears more than once")
            else:
                _seen_ids.append(sid)

    return errors

