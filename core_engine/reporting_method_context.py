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

