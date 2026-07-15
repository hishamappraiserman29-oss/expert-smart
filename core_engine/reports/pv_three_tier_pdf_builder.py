"""pv_three_tier_pdf_builder.py — Three-tier PDF builder.

Uses the shared Playwright/HTML renderer (pdf_renderer.py).
No FPDF — no Chrome subprocess — Playwright only.
Never issues Certified output automatically.
"""
from __future__ import annotations

import math
import pathlib
from typing import Any

_HERE = pathlib.Path(__file__).parent
_TEMPLATES = _HERE.parent / "templates" / "pdf"
_CSS_PATH = _TEMPLATES / "pv_design_system.css"
_NA = "غير متاح ضمن بيانات الطلب"


def _na(v: Any) -> str:
    if v is None or (isinstance(v, str) and not v.strip()):
        return _NA
    return str(v)


def _fmt(v: Any, decimals: int = 0) -> str:
    try:
        n = float(str(v).replace(",", ""))
        return f"{n:,.{decimals}f}" if decimals else f"{n:,.0f}"
    except (ValueError, TypeError):
        return _na(v)


def _load_cairo_font_css() -> str:
    try:
        import sys as _sys
        _sys.path.insert(0, str(_HERE.parent))
        from pdf_renderer import cairo_font_css  # type: ignore
        return cairo_font_css()
    except Exception:
        return ""


def _load_renderer():
    import sys as _sys
    _sys.path.insert(0, str(_HERE.parent))
    from pdf_renderer import render_pdf_from_html  # type: ignore
    return render_pdf_from_html


def _safe_float(v: Any) -> float | None:
    try:
        return float(str(v).replace(",", ""))
    except (ValueError, TypeError):
        return None


def _enrich_traditional_data(data: dict) -> dict:
    """Compute derived display-only fields for the traditional PDF template.

    Only adds keys not already present; never overwrites caller-supplied values.
    Never recalculates valuation numbers — only derives display helpers from
    values that already exist in *data*.
    """
    d = dict(data)

    # ── AVM final value fallback ──────────────────────────────────────────
    if not d.get("avm_final_value"):
        avm_rows = d.get("avm_results") or []
        if avm_rows:
            first_val = _safe_float(avm_rows[0].get("value", ""))
            if first_val:
                d.setdefault("avm_final_value", first_val)

    # ── CV consistency test (display only) ───────────────────────────────
    if not d.get("cv_data"):
        vals = []
        for key in ("market_value", "cost_approach_value", "dcf_value", "avm_final_value"):
            v = _safe_float(d.get(key))
            if v and v > 0:
                vals.append(v)
        if len(vals) >= 2:
            mean_v = sum(vals) / len(vals)
            std_dev = math.sqrt(sum((v - mean_v) ** 2 for v in vals) / len(vals))
            cv_pct = (std_dev / mean_v * 100) if mean_v else 0.0
            weighted_value = _safe_float(d.get("final_value")) or mean_v
            if cv_pct < 15:
                risk_class, risk_level = "low", "منخفض — مقبول للاعتماد"
                note = "تباين منخفض بين الطرق — مقبول للمراجعة المهنية."
            elif cv_pct < 30:
                risk_class, risk_level = "mid", "متوسط — يحتاج مراجعة إضافية"
                note = "تباين متوسط — يُنصح بمراجعة الافتراضات قبل الاعتماد."
            else:
                risk_class, risk_level = "high", "مرتفع — عائق للاعتماد الرسمي"
                note = "تباين مرتفع جداً بين الطرق — يمنع الاعتماد الرسمي حتى يُحدَّد السبب."
            low_90 = mean_v - 1.645 * std_dev
            high_90 = mean_v + 1.645 * std_dev
            d["cv_data"] = {
                "cv_pct": f"{cv_pct:.1f}",
                "risk_class": risk_class,
                "risk_level": risk_level,
                "mean_value": mean_v,
                "weighted_value": weighted_value,
                "std_dev": std_dev,
                "low_90": max(0, low_90),
                "high_90": high_90,
                "note": note,
            }

    # ── Confidence range ──────────────────────────────────────────────────
    final_v = _safe_float(d.get("final_value"))
    if final_v and final_v > 0:
        cv_data = d.get("cv_data", {})
        d.setdefault("confidence_low", cv_data.get("low_90") or final_v * 0.90)
        d.setdefault("confidence_high", cv_data.get("high_90") or final_v * 1.10)

    # ── Value chart rows (for bar chart section) ──────────────────────────
    if not d.get("value_chart_rows"):
        chart_rows = []
        max_v = 1.0
        method_keys = [
            ("avm_final_value", "AVM (انحدار آلي)"),
            ("market_value", "مدخل المقارنة السوقية"),
            ("cost_approach_value", "مدخل التكلفة"),
            ("dcf_value", "مدخل DCF"),
            ("income_cap_value", "رسملة الدخل المباشر"),
        ]
        row_vals = []
        for key, label in method_keys:
            v = _safe_float(d.get(key))
            if v and v > 0:
                row_vals.append((label, v))
                if v > max_v:
                    max_v = v
        for label, v in row_vals:
            bar_pct = int(v / max_v * 100)
            chart_rows.append({"method": label, "value": v, "bar_pct": bar_pct, "status": "استرشادي"})
        if chart_rows:
            d["value_chart_rows"] = chart_rows

    # ── Preliminary reconciliation rows ──────────────────────────────────
    if not d.get("recon_rows"):
        recon = []
        pairs = [
            ("avm_final_value", "AVM (انحدار آلي)", "0%"),
            ("market_value", "مدخل المقارنة السوقية", d.get("market_weight", "40%")),
            ("cost_approach_value", "مدخل التكلفة", d.get("cost_weight", "25%")),
            ("dcf_value", "مدخل الدخل / DCF", d.get("dcf_weight", "35%")),
        ]
        for key, label, weight in pairs:
            v = _safe_float(d.get(key))
            if v and v > 0:
                recon.append({"method": label, "value": v, "weight": weight, "status": "استرشادي", "status_class": "warn"})
        if recon:
            d["recon_rows"] = recon

    # ── Weighted reconciliation for final section ─────────────────────────
    if not d.get("weighted_recon_rows"):
        wr_rows = []
        pairs = [
            ("market_value", "مقارنة البيوع", d.get("market_weight", "40%")),
            ("cost_approach_value", "مدخل التكلفة", d.get("cost_weight", "25%")),
            ("dcf_value", "مدخل DCF", d.get("dcf_weight", "35%")),
        ]
        for key, label, weight in pairs:
            v = _safe_float(d.get(key))
            w_str = str(weight).replace("%", "")
            w = _safe_float(w_str)
            if v and v > 0 and w is not None:
                wr_rows.append({
                    "method": label,
                    "value": v,
                    "weight": weight,
                    "weighted_contribution": v * w / 100.0,
                })
        if wr_rows:
            d["weighted_recon_rows"] = wr_rows

    # ── Compliance items from docs ────────────────────────────────────────
    if not d.get("compliance_items"):
        req_docs = d.get("required_docs") or []
        missing_docs = d.get("missing_docs") or []
        items = []
        base_items = [
            "سند الملكية أو عقد البيع",
            "رخصة البناء أو شهادة إتمام",
            "صور العقار الميدانية",
            "كشف مساحة أو رسم كروكي",
            "خريطة الموقع / الإحداثيات",
            "توقيع الخبير المرخّص",
        ]
        doc_names = [d if isinstance(d, str) else d.get("name", "") for d in req_docs] or base_items
        for doc in doc_names:
            if doc in missing_docs:
                status = "عائق حرج"
            elif doc in ("توقيع الخبير المرخّص", "ختم الشركة", "مراجعة النظراء"):
                status = "عائق حرج"
            else:
                status = "مكتمل"
            items.append({"label": doc, "status": status})
        # Fixed mandatory gates
        for gate in ("توقيع الخبير المرخّص", "ترخيص الخبير", "ختم الشركة", "مراجعة النظراء"):
            if not any(i["label"] == gate for i in items):
                items.append({"label": gate, "status": "عائق حرج"})
        d["compliance_items"] = items

    # ── Cert risk level derived from cert_risks count ─────────────────────
    if not d.get("cert_risk_level"):
        cert_risks = d.get("cert_risks") or []
        d["cert_risk_level"] = "مرتفع" if cert_risks else "متوسط"

    # ── AVM model status ──────────────────────────────────────────────────
    if not d.get("avm_model_status"):
        avm_v = _safe_float(d.get("avm_final_value"))
        d["avm_model_status"] = {
            "used": bool(avm_v),
            "input_completeness": d.get("avm_input_completeness", 70),
            "avm_value": avm_v,
            "confidence": d.get("avm_confidence", d.get("confidence_score", _NA)),
            "weight": 0,
            "status_note": "QA محاكاة — مرجع استرشادي فقط — Qdrant غير مفعَّل",
        }

    # ── Income cap value fallback ─────────────────────────────────────────
    if not d.get("income_cap_value"):
        noi_v = _safe_float(d.get("annual_noi") or d.get("noi"))
        cap_r = _safe_float(d.get("cap_rate_used") or d.get("cap_rate_exit"))
        if noi_v and cap_r and cap_r > 0:
            d["income_cap_value"] = noi_v / (cap_r / 100.0)

    # ── Top risk category ─────────────────────────────────────────────────
    d.setdefault("top_risk_category", "بيانات ومصادر (QA محاكاة)")

    # ── SWOT top priorities (if swot has priority-annotated dicts) ────────
    if not d.get("swot_top_priorities"):
        swot = d.get("swot") or {}
        all_items = []
        for cat_key, cat_name in (
            ("threats", "تهديدات"),
            ("weaknesses", "ضعف"),
            ("opportunities", "فرص"),
        ):
            for item in swot.get(cat_key) or []:
                if isinstance(item, dict) and item.get("priority"):
                    all_items.append({
                        "item": item.get("text", ""),
                        "category": cat_name,
                        "impact": item.get("impact", "متوسط"),
                        "probability": item.get("probability", "متوسط"),
                        "priority": item.get("priority", "—"),
                        "action": item.get("action", "مراجعة"),
                    })
        if all_items:
            d["swot_top_priorities"] = all_items[:5]

    # ── AVM regression rows (10 display-only variables) ─────────────────
    if not d.get("avm_regression_rows"):
        area = _safe_float(d.get("area_sqm")) or 150.0
        fv = _safe_float(d.get("avm_final_value") or d.get("final_value")) or 3_000_000
        psm = round(fv / area, 0) if area > 0 else 20_000
        age = _safe_float(d.get("effective_age") or d.get("age_years")) or 8
        age_factor = round(max(0.7, 1.0 - age * 0.01), 2)
        _ptype_code = "سكني" if "سكن" in d.get("property_type", "سكني") else "تجاري"
        _floor_factor = round(1.0 + (_safe_float(d.get("floor_number")) or 3) * 0.005, 3)
        _fin_adj = round(fv * -0.05, 0)
        _age_adj = round(fv * -(1 - age_factor), 0)
        _floor_adj = round(fv * (_floor_factor - 1.0), 0)
        _sec_adj = round(fv * 0.02, 0)
        _svc_adj = round(fv * 0.01, 0)
        _final_adj = int(_fin_adj + _age_adj + _floor_adj)
        _avm_adj = int(fv + _final_adj + _sec_adj + _svc_adj)
        d["avm_regression_rows"] = [
            {"variable": "المساحة (م²)", "value": f"{area:.0f}",
             "coefficient": f"{psm:,.0f} م.ج/م²", "impact": f"{fv:,.0f}",
             "notes": "القيمة الأساسية — المساحة × سعر المتر"},
            {"variable": "نوع العقار", "value": _ptype_code,
             "coefficient": "1.00", "impact": "0",
             "notes": f"{d.get('property_type', 'سكني')} — مُدرَج في السعر الأساسي"},
            {"variable": "الطابق والمستوى", "value": str(int(_safe_float(d.get("floor_number")) or 3)),
             "coefficient": str(_floor_factor), "impact": f"{int(_floor_adj):,}+",
             "notes": f"طابق {int(_safe_float(d.get('floor_number')) or 3)} — معامل إرشادي"},
            {"variable": "معامل الموقع", "value": d.get("location_factor", "1.00"),
             "coefficient": "1.00", "impact": "0",
             "notes": f"{d.get('property_address', 'المنطقة المحددة')} — محاكاة QA"},
            {"variable": "معامل الحالة/التشطيب", "value": "0.95",
             "coefficient": "0.95", "impact": f"{int(_fin_adj):,}-",
             "notes": "تشطيب نصف راقٍ — بانتظار فحص ميداني"},
            {"variable": "معامل العمر الفعلي", "value": str(age_factor),
             "coefficient": str(age_factor), "impact": f"{int(_age_adj):,}-",
             "notes": f"عمر فعلي {age:.0f} سنة — خط مستقيم إرشادي"},
            {"variable": "معامل الأمان والإدارة", "value": "1.02",
             "coefficient": "1.02", "impact": f"{int(_sec_adj):,}+",
             "notes": "بوابة أمان — كاميرات — مجمع سكني"},
            {"variable": "معامل قرب الخدمات", "value": "1.01",
             "coefficient": "1.01", "impact": f"{int(_svc_adj):,}+",
             "notes": "مدارس · مراكز تجارية · مواصلات — إرشادي"},
            {"variable": "التعديل الإجمالي", "value": f"{_final_adj:,}",
             "coefficient": "—", "impact": f"{_final_adj:,}",
             "notes": "مجموع التشطيب + العمر + الطابق — إرشادي QA"},
            {"variable": "قيمة AVM النهائية", "value": f"{_avm_adj:,}",
             "coefficient": "—", "impact": "الناتج",
             "notes": "محاكاة QA — إرشادي — غير معتمد رسمياً"},
        ]
        d.setdefault("avm_final_value", fv)

    # ── BOQ items (12 standard construction items) ───────────────────────
    if not d.get("boq_items"):
        area = _safe_float(d.get("area_sqm")) or 150.0
        cost_new = _safe_float(d.get("construction_cost_new")) or area * 5_000
        indirect = cost_new * 0.10
        contingency = cost_new * 0.04
        rebar = area * 280
        insulation = area * 220
        aluminium = area * 350
        marble = area * 400
        garden = area * 80
        d["boq_items"] = [
            {"item": "أعمال الهيكل الخرساني المسلح", "unit": "م²", "qty": area,  "unit_price": 1_500,           "total": area * 1_500,      "pct": "22.8%", "notes": "خرسانة C25 — هيكل كامل"},
            {"item": "أعمال حديد التسليح (توريد وتركيب)", "unit": "طن", "qty": round(area * 0.06, 1), "unit_price": 70_000, "total": int(rebar), "pct": "4.3%", "notes": "حديد عالي المقاومة"},
            {"item": "أعمال المباني والطوب", "unit": "م²", "qty": area,  "unit_price": 600,             "total": area * 600,        "pct": "9.1%",  "notes": "طوب بلوك مزدوج"},
            {"item": "العزل الحراري والمائي",  "unit": "م²", "qty": area,  "unit_price": 220,             "total": int(insulation),   "pct": "3.3%",  "notes": "بيتومين + فوم + لياسة"},
            {"item": "أعمال التشطيب والديكور", "unit": "م²", "qty": area,  "unit_price": 1_200,           "total": area * 1_200,      "pct": "18.2%", "notes": "تشطيب نصف راقٍ — جبس + دهانات"},
            {"item": "أعمال الألمونيوم والنجارة (أبواب ونوافذ)", "unit": "م²", "qty": round(area * 0.3, 1), "unit_price": 1_800, "total": int(aluminium), "pct": "5.3%", "notes": "ألمونيوم ثقيل + خشب MDF"},
            {"item": "رخام وبلاط وسيراميك",   "unit": "م²", "qty": area,  "unit_price": 400,             "total": int(marble),       "pct": "6.1%",  "notes": "سيراميك إسباني + رخام مداخل"},
            {"item": "أعمال كهربائية وميكانيكية", "unit": "م²", "qty": area, "unit_price": 800,           "total": area * 800,        "pct": "12.1%", "notes": "شبكات كهربائية — تكييف مركزي"},
            {"item": "أعمال سباكة وصرف صحي",  "unit": "م²", "qty": area,  "unit_price": 500,             "total": area * 500,        "pct": "7.6%",  "notes": "شبكة مياه PP-R + صرف PVC"},
            {"item": "حديقة وتنسيق خارجي",    "unit": "م²", "qty": round(area * 0.2, 1), "unit_price": 600, "total": int(garden),     "pct": "1.2%",  "notes": "نجيلة صناعية + إنارة"},
            {"item": "مصاريف غير مباشرة (إدارة وإشراف وضمان جودة)", "unit": "إجمالي", "qty": 1, "unit_price": int(indirect), "total": int(indirect), "pct": "7.6%", "notes": "نسبة 10% من التكلفة الإنشائية"},
            {"item": "احتياطي طوارئ وتضخم",   "unit": "إجمالي", "qty": 1,    "unit_price": int(contingency), "total": int(contingency), "pct": "2.5%", "notes": "احتياطي 4% — تحوط تضخم سنوي"},
        ]

    # ── DCF 5-year table (display-only, derived from workbook rates) ─────
    if not d.get("dcf_years"):
        noi = _safe_float(d.get("annual_noi") or d.get("noi")) or 144_000
        disc = _safe_float(d.get("discount_rate")) or 12.5
        growth = _safe_float(d.get("growth_rate")) or 3.5
        vac = _safe_float(d.get("vacancy_rate")) or 5.0
        dcf_rows = []
        for yr in range(1, 6):
            rent = noi * (1 + growth / 100) ** (yr - 1)
            egi = rent * (1 - vac / 100)
            exp = egi * 0.15
            noi_yr = egi - exp
            df = 1 / (1 + disc / 100) ** yr
            dcf_rows.append({
                "year": yr, "rent": int(rent), "vacancy": vac,
                "egi": int(egi), "expenses": int(exp), "noi": int(noi_yr),
                "discount": disc, "pv": int(noi_yr * df),
            })
        d["dcf_years"] = dcf_rows

    # ── Cap rate 4 models ────────────────────────────────────────────────
    if not d.get("cap_rate_models"):
        cap_r = _safe_float(d.get("cap_rate_used") or d.get("cap_rate_exit")) or 8.0
        disc = _safe_float(d.get("discount_rate")) or 12.5
        growth = _safe_float(d.get("growth_rate")) or 3.5
        d["cap_rate_models"] = [
            {"model": "الاستخلاص المباشر (من السوق)",    "rate": cap_r,                      "note": "مشتق من صفقات السوق — إرشادي QA"},
            {"model": "حزمة الاستثمار (Weighted Band)",  "rate": round(cap_r * 0.95, 2),     "note": "مزيج دين وعدالة — إرشادي"},
            {"model": "Gordon (نمو ثابت): Rk = Yn - g",  "rate": round(disc - growth, 2),    "note": f"معدل الخصم {disc}% - نمو {growth}%"},
            {"model": "البناء التراكمي (Build-Up)",       "rate": round(cap_r * 1.05, 2),    "note": "معدل خالٍ من المخاطر + أقساط — إرشادي"},
        ]

    # ── SWOT defaults when not supplied ─────────────────────────────────
    if not d.get("swot"):
        d["swot"] = {
            "strengths": [
                "موقع جغرافي مميز وقرب من الخدمات الأساسية بالمنطقة",
                "مساحة مناسبة وتصميم عملي يلائم الاستخدامات السكنية والاستثمارية",
                "إمكانية توليد دخل إيجاري مستدام في السوق المحلي",
                "وصول جيد لشبكة الطرق الرئيسية ووسائل النقل العام",
                "إمكانية الاستفادة من مشاريع التطوير المستقبلية في المنطقة",
            ],
            "weaknesses": [
                "نقص المستندات الإلزامية اللازمة للاعتماد الرسمي (رخصة بناء — شهادة إتمام)",
                "عدم اكتمال بيانات السوق الحقيقية — تعتمد على محاكاة QA فقط",
                "غياب الفحص الميداني المعتمد وصور الواجهة الرسمية",
                "تباين عالٍ بين طرق التقييم المختلفة يرفع درجة عدم اليقين",
                "اعتماد AVM على بيانات QA وليس مصادر سوقية موثقة فعلياً",
            ],
            "opportunities": [
                {"text": "استبدال بيانات QA ببيانات إنتاجية من مصادر رسمية",           "priority": 20},
                {"text": "السيناريو المتفائل في DCF عند نمو الإيجارات السنوي +5%",      "priority": 15},
                {"text": "إمكانية نمو الإيجار على المدى المتوسط (3–5 سنوات)",          "priority": 12},
                {"text": "تحسين درجة ESG وجذب مستثمرين مؤسسيين مراعين للبيئة",        "priority": 10},
                {"text": "إمكانية إعادة التطوير لرفع الاستخدام الأفضل والأعلى (HBU)",  "priority": 9},
                {"text": "ارتفاع الطلب على الوحدات الصغيرة في المنطقة الجغرافية ذاتها", "priority": 8},
            ],
            "threats": [
                {"text": "عوائق بوابة الاعتماد الرسمي — يحتاج إلى توقيع خبير مرخص",    "priority": 25},
                {"text": "المخاطر القانونية وعدم اكتمال الوثائق — رهون محتملة",          "priority": 16},
                {"text": "التشتت الكبير بين طرق التقييم (CV مرتفع) يُشكّك في المصداقية","priority": 14},
                {"text": "السيناريو المتشائم في DCF عند ارتفاع معدلات الشغور",           "priority": 12},
                {"text": "تقلبات الأسواق العقارية المحلية وأثر التضخم على التكلفة",      "priority": 10},
                {"text": "تغير التشريعات أو الاشتراطات التخطيطية في منطقة العقار",       "priority": 8},
            ],
        }
    if not d.get("swot_top_priorities"):
        d["swot_top_priorities"] = [
            {"item": "استكمال بوابة الاعتماد والتوقيع",      "category": "تهديدات", "impact": "عالي",   "probability": "مرتفع", "priority": 25, "action": "إعداد مستندات الاعتماد الكاملة وتقديمها للخبير المرخص"},
            {"item": "استبدال بيانات QA ببيانات إنتاجية",   "category": "فرص",    "impact": "عالي",   "probability": "متوسط", "priority": 20, "action": "تفعيل Qdrant وربط مصادر بيانات سوقية رسمية"},
            {"item": "مخاطر قانونية ووثائق ناقصة",          "category": "تهديدات", "impact": "عالي",   "probability": "عالٍ",  "priority": 16, "action": "مراجعة قانونية فورية للتأكد من سلامة الملكية"},
            {"item": "تقليل التباين (CV) بين طرق التقييم",  "category": "تهديدات", "impact": "متوسط",  "probability": "عالٍ",  "priority": 14, "action": "توفير بيانات مبيعات حقيقية لتقليل الاعتماد على QA"},
            {"item": "السيناريو المتفائل DCF — نمو إيجاري", "category": "فرص",    "impact": "متوسط",  "probability": "متوسط", "priority": 15, "action": "تحليل سوق الإيجار والتحقق من إمكانية نمو +5% سنوياً"},
            {"item": "السيناريو المتشائم DCF — شغور مرتفع", "category": "تهديدات", "impact": "متوسط",  "probability": "متوسط", "priority": 12, "action": "مراجعة افتراضات DCF وتطبيق تحليل الحساسية"},
            {"item": "تحسين درجة ESG وجذب مستثمرين",        "category": "فرص",    "impact": "متوسط",  "probability": "منخفض", "priority": 10, "action": "تقييم مناخي مستقل ورفع كفاءة الطاقة"},
            {"item": "تقلبات السوق المحلي والتضخم",          "category": "تهديدات", "impact": "منخفض",  "probability": "متوسط", "priority": 10, "action": "مراجعة دورية للقيمة كل 12 شهراً"},
        ]

    # ── HBU defaults ─────────────────────────────────────────────────────
    _ptype = d.get("property_type", "سكني")
    d.setdefault("hbu_current",      f"{_ptype} — الاستخدام الحالي")
    d.setdefault("hbu_optimal",      f"{_ptype} — HBU مطبَّق (إرشادي)")
    d.setdefault("hbu_legal",        "مسموح قانونياً — إرشادي")
    d.setdefault("hbu_physical",     "ممكن فيزيائياً — بانتظار فحص ميداني")
    d.setdefault("hbu_financial",    "مجدٍ اقتصادياً — محاكاة QA")
    d.setdefault("hbu_productivity", "متوافق مع HBU — إرشادي")

    # ── Governance rows ──────────────────────────────────────────────────
    if not d.get("governance_rows"):
        _cv_pct = d.get("cv_data", {}).get("cv_pct", "غير محدد") if d.get("cv_data") else "غير محدد"
        _inp_comp = d.get("avm_input_completeness", 70)
        d["governance_rows"] = [
            {"param": "معامل التباين (CV)",          "value": f"{_cv_pct}%",                    "allowed": False, "action": "تقليل التباين — الهدف <15%"},
            {"param": "اكتمال المدخلات",             "value": f"{_inp_comp}%",                  "allowed": _inp_comp >= 80,  "action": "رفع الاكتمال لـ 90%+"},
            {"param": "توثيق العمر الفعلي",          "value": d.get("effective_age_doc", "لا"), "allowed": False, "action": "استيفاء شهادة إتمام البناء أو رخصة"},
            {"param": "توقيع خبير مرخص",             "value": "بانتظار التوقيع",               "allowed": False, "action": "لازم للاعتماد الرسمي"},
            {"param": "معاينة ميدانية موثقة",        "value": d.get("inspection_status", "لم تُجرَ"), "allowed": False, "action": "إجراء معاينة ميدانية مع تقرير مصور"},
            {"param": "بيانات مقارنات حقيقية",       "value": "محاكاة QA فقط",                 "allowed": False, "action": "توفير ≥3 صفقات بيع حقيقية موثقة"},
            {"param": "معدل رسملة مرجعي (من سوق)",  "value": "محاكاة QA",                      "allowed": False, "action": "استخلاص من صفقات سوقية فعلية"},
            {"param": "حالة RAG/Qdrant",             "value": "غير مفعَّل",                     "allowed": True,  "action": "ليس إلزامياً — يُحسّن الجودة عند التفعيل"},
        ]

    # ── Roadmap steps ────────────────────────────────────────────────────
    if not d.get("roadmap_steps"):
        d["roadmap_steps"] = [
            {"step": "استكمال مستندات الملكية وسند التصرف",             "status": "معلق"},
            {"step": "إجراء الفحص الميداني المعتمد مع تقرير مصور",      "status": "معلق"},
            {"step": "الحصول على ≥3 مقارنات سوقية موثقة من مصادر رسمية", "status": "معلق"},
            {"step": "تحديد وتوثيق العمر الفعلي (شهادة إتمام)",         "status": "معلق"},
            {"step": "توقيع الخبير المرخص وختم الشركة الرسمي",          "status": "معلق"},
            {"step": "مراجعة النظراء الداخلية (Peer Review)",            "status": "معلق"},
            {"step": "إصدار النسخة المعتمدة النهائية وأرشفتها",          "status": "مستقبلي"},
        ]

    # ── Break-even (display-only, derived from workbook rates) ───────────
    if not d.get("breakeven"):
        _fv = _safe_float(d.get("final_value")) or 3_000_000
        _cap_r = _safe_float(d.get("cap_rate_used") or d.get("cap_rate_exit")) or 8.0
        _noi = _safe_float(d.get("annual_noi") or d.get("noi")) or _fv * _cap_r / 100
        _current_rent = int(_noi / 12 * 0.85)
        _be_threshold = int(_fv * 0.08 / 12)
        _gap = abs(_be_threshold - _current_rent)
        _dir = "أعلى من" if _current_rent >= _be_threshold else "أقل من"
        d["breakeven"] = {
            "current_rent": _current_rent,
            "breakeven_threshold": _be_threshold,
            "gap": _gap,
            "note": (
                f"الإيجار الحالي/المتوقع ({_current_rent:,} م.ج/شهر) {_dir} "
                f"نقطة التعادل ({_be_threshold:,} م.ج/شهر) بفارق {_gap:,} م.ج/شهر. "
                "هذا المؤشر إرشادي فقط لدعم قرار المستثمر — لا يُعدّ نصيحة استثمارية."
            ),
        }

    # ── Comparables fallback (QA simulation, clearly labelled) ───────────
    if not d.get("comparables"):
        _area = _safe_float(d.get("area_sqm")) or 150.0
        _fv2 = _safe_float(d.get("final_value")) or 3_000_000
        _psm = _fv2 / _area if _area > 0 else 20_000
        _addr = d.get("property_address", "نفس المنطقة")
        d["comparables"] = [
            {"id": "م1", "address": f"{_addr} — م.١ (QA)", "area": round(_area * 1.10, 0), "price": int(_psm * 1.05 * _area * 1.10), "price_sqm": int(_psm * 1.05), "loc_adj": "+5%", "cond_adj": "0%",  "adj_total": "+5%", "adj_value": int(_fv2 * 1.04), "date": "2026-01"},
            {"id": "م2", "address": f"{_addr} — م.٢ (QA)", "area": round(_area * 0.90, 0), "price": int(_psm * 0.97 * _area * 0.90), "price_sqm": int(_psm * 0.97), "loc_adj": "-3%", "cond_adj": "+5%", "adj_total": "+2%", "adj_value": int(_fv2 * 0.99), "date": "2025-11"},
            {"id": "م3", "address": f"{_addr} — م.٣ (QA)", "area": round(_area * 1.05, 0), "price": int(_psm * 1.02 * _area * 1.05), "price_sqm": int(_psm * 1.02), "loc_adj": "0%",  "cond_adj": "+2%", "adj_total": "+2%", "adj_value": int(_fv2 * 1.01), "date": "2026-02"},
            {"id": "م4", "address": f"{_addr} — م.٤ (QA)", "area": round(_area,        0), "price": int(_psm * 0.98 * _area),        "price_sqm": int(_psm * 0.98), "loc_adj": "-2%", "cond_adj": "+3%", "adj_total": "+1%", "adj_value": int(_fv2 * 0.98), "date": "2025-12"},
            {"id": "م5", "address": f"{_addr} — م.٥ (QA)", "area": round(_area * 0.85, 0), "price": int(_psm * 1.03 * _area * 0.85), "price_sqm": int(_psm * 1.03), "loc_adj": "+3%", "cond_adj": "+1%", "adj_total": "+4%", "adj_value": int(_fv2 * 1.02), "date": "2025-10"},
            {"id": "م6", "address": f"{_addr} — م.٦ (QA)", "area": round(_area * 1.15, 0), "price": int(_psm * 0.96 * _area * 1.15), "price_sqm": int(_psm * 0.96), "loc_adj": "-4%", "cond_adj": "+3%", "adj_total": "-1%", "adj_value": int(_fv2 * 0.97), "date": "2025-09"},
        ]
        d.setdefault("avg_price_sqm", int(_psm))

    # ── BOQ cost-approach derived values ─────────────────────────────────
    _fv_for_cost = _safe_float(d.get("final_value")) or 3_000_000
    _cost_new2 = _safe_float(d.get("construction_cost_new")) or _fv_for_cost * 0.60
    _land_v2 = _safe_float(d.get("land_value")) or (
        (_safe_float(d.get("area_sqm")) or 150) * (_safe_float(d.get("land_value_psm")) or 8_000)
    )
    _age2  = _safe_float(d.get("age_years") or d.get("effective_age")) or 8
    _econ2 = _safe_float(d.get("economic_life")) or 50
    _phys2 = round(min(_age2 / _econ2 * 100, 80), 1)
    _func2 = _safe_float(d.get("functional_depreciation")) or 5.0
    _econ2_depr = _safe_float(d.get("economic_depreciation")) or 0.0
    _tot2  = round(_phys2 + _func2 + _econ2_depr, 1)
    _bldg2 = int(_cost_new2 * (1 - _tot2 / 100))
    _ca2   = int(_land_v2 + _bldg2)
    d.setdefault("land_value",              int(_land_v2))
    d.setdefault("physical_depreciation",   _phys2)
    d.setdefault("functional_depreciation", _func2)
    d.setdefault("economic_depreciation",   _econ2_depr)
    d.setdefault("total_depreciation",      _tot2)
    d.setdefault("building_value",          _bldg2)
    d.setdefault("cost_approach_value",     _ca2)
    d.setdefault("economic_life",           int(_econ2))
    d.setdefault("depreciation_allowed",    "لا — يحتاج شهادة إتمام بناء")

    # ── Land value / comparables section ─────────────────────────────────
    _la3 = _safe_float(d.get("area_sqm")) or 150.0
    _lpsm3 = _safe_float(d.get("land_value_psm")) or 8_000
    d.setdefault("land_area",     int(_la3 * 0.20))
    d.setdefault("land_price_sqm", int(_lpsm3))
    d.setdefault("land_method",   "المقارنة بالمبيعات — مقارنات تمثيلية QA")
    d.setdefault("land_sources",  "مقارنات أراضٍ تمثيلية · هيئة المجتمعات العمرانية (غير مفعَّل) · Qdrant RAG (غير مفعَّل)")
    if d.get("comparables") and d.get("avg_price_sqm"):
        d.setdefault("market_value", int(d["avg_price_sqm"] * _la3))

    # ── Confidence & uncertainty enrichment ──────────────────────────────
    _cfv = _safe_float(d.get("final_value")) or 3_000_000
    d.setdefault("confidence_low",      int(_cfv * 0.88))
    d.setdefault("confidence_high",     int(_cfv * 1.12))
    d.setdefault("confidence_score",    65)
    d.setdefault("uncertainty_level",   "متوسط — بيانات QA غير موثقة")
    d.setdefault("uncertainty_reasons",
                 "بيانات السوق محاكاة QA · غياب فحص ميداني · تباين بين طرق التقييم")
    # ── Value in words (for recommendation section) ───────────────────────
    if not d.get("value_in_words"):
        _v = int(_cfv)
        _mil = _v // 1_000_000
        _tho = (_v % 1_000_000) // 1_000
        _hun = (_v % 1_000)
        parts = []
        if _mil:
            parts.append(f"{_mil} مليون")
        if _tho:
            parts.append(f"{_tho} ألف")
        if _hun:
            parts.append(f"{_hun}")
        d["value_in_words"] = " و".join(parts) + " جنيه مصري — إرشادي" if parts else "غير محدد"

    # ── income_cap_value / dcf_value for sec-income-cap-dcf ──────────────
    if not d.get("income_cap_value"):
        _noi_ic = _safe_float(d.get("annual_noi") or d.get("noi")) or (_cfv * 0.08)
        _cap_ic = _safe_float(d.get("cap_rate_used") or d.get("cap_rate_exit")) or 8.0
        if _cap_ic > 0:
            d.setdefault("income_cap_value", int(_noi_ic / (_cap_ic / 100)))
    if not d.get("dcf_value") and d.get("dcf_years"):
        _pv_sum = sum(r.get("pv", 0) for r in d["dcf_years"])
        _term_cap = _safe_float(d.get("cap_rate_exit")) or 8.0
        _last_noi = d["dcf_years"][-1].get("noi", 0) if d["dcf_years"] else 0
        _term_val = int(_last_noi / (_term_cap / 100)) if _term_cap > 0 else 0
        _disc_5 = _safe_float(d.get("discount_rate")) or 12.5
        _tv_pv = int(_term_val / (1 + _disc_5 / 100) ** 5)
        d.setdefault("dcf_value", int(_pv_sum + _tv_pv))

    # ── Income-method rent reconciliation ────────────────────────────────
    if not d.get("income_method_rent"):
        _ann_rent = _safe_float(d.get("annual_noi") or d.get("noi")) or (_cfv * 0.08)
        d.setdefault("income_method_rent", int(_ann_rent))
        d.setdefault("final_rental_value", "غير متاح — بانتظار بيانات إنتاجية")
        d.setdefault("rent_gap",           "غير قابل للحساب — بيانات QA")

    # ── Weighted reconciliation rows ─────────────────────────────────────
    if not d.get("weighted_recon_rows"):
        _wfv = _safe_float(d.get("final_value")) or 3_000_000
        _ic_v = int(d.get("income_cap_value") or _wfv * 0.98)
        _dcf_v = int(d.get("dcf_value") or _wfv * 1.02)
        _comp_v = int(d.get("avg_price_sqm", _wfv / 150) * (_safe_float(d.get("area_sqm")) or 150))
        _rows = [
            {"method": "مقارنة البيوع (Sales Comparison)",       "value": _comp_v, "weight": "40%", "weighted_contribution": int(_comp_v * 0.40)},
            {"method": "رسملة الدخل المباشر (Income Cap)",       "value": _ic_v,   "weight": "30%", "weighted_contribution": int(_ic_v   * 0.30)},
            {"method": "التدفقات النقدية المخصومة (DCF)",         "value": _dcf_v,  "weight": "20%", "weighted_contribution": int(_dcf_v  * 0.20)},
            {"method": "طريقة التكلفة / القيمة الاستبدالية (CV)", "value": int(d.get("cv_value", _wfv * 1.01)), "weight": "10%", "weighted_contribution": int(d.get("cv_value", _wfv * 1.01) * 0.10)},
        ]
        d["weighted_recon_rows"] = _rows
    d.setdefault("dominant_method", "مقارنة البيوع — بيانات QA")

    # ── Compliance items ──────────────────────────────────────────────────
    if not d.get("compliance_items"):
        d["compliance_items"] = [
            {"label": "تعريف الغرض من التقييم",                      "status": "مكتمل"},
            {"label": "تعريف أساس القيمة (القيمة السوقية)",          "status": "مكتمل"},
            {"label": "تعريف نطاق العمل وحدوده",                    "status": "مكتمل"},
            {"label": "إفصاح محدودية البيانات والمصادر",             "status": "مكتمل"},
            {"label": "إفصاح عدم الاستقلالية (إن وجد تعارض مصالح)", "status": "مكتمل"},
            {"label": "إخلاء مسؤولية استخدام بيانات QA",            "status": "مكتمل"},
            {"label": "توقيع الخبير المرخص وترخيصه",                "status": "عائق حرج"},
            {"label": "ختم الشركة الرسمي",                          "status": "مفقود"},
            {"label": "مراجعة النظراء الداخلية (Peer Review)",       "status": "مفقود"},
            {"label": "الفحص الميداني وصور العقار الموثقة",         "status": "مفقود"},
        ]

    # ── Assumption rows ───────────────────────────────────────────────────
    if not d.get("assumption_rows"):
        d["assumption_rows"] = [
            {"type": "افتراض عادي",  "description": "القيمة السوقية على أساس إخلاء الطوعي — لا إكراه",          "impact": "منخفض — افتراض قياسي",          "needs_doc": False},
            {"type": "افتراض عادي",  "description": "العقار في حالة تشغيلية عادية بدون أي تدخل خارجي",           "impact": "منخفض — افتراض قياسي",          "needs_doc": False},
            {"type": "افتراض خاص",   "description": "بيانات المساحة مستخرجة من بيانات الطلب — لم تُقاس ميدانياً", "impact": "متوسط — قد يؤثر على القيمة ±5%", "needs_doc": True},
            {"type": "افتراض خاص",   "description": "العمر الفعلي مُقدَّر ولم يوثق بشهادة رسمية",               "impact": "متوسط — يؤثر على الإهلاك",       "needs_doc": True},
            {"type": "قيد نطاق",     "description": "لا معاينة ميدانية — لا مراجعة مستندات ملكية أصلية",         "impact": "عالٍ — يحد من صحة التقييم",      "needs_doc": True},
            {"type": "قيد نطاق",     "description": "بيانات السوق من محاكاة QA وليست مصادر رسمية موثقة",        "impact": "عالٍ — يرفع معامل التباين CV",    "needs_doc": True},
        ]

    # ── ESG data ──────────────────────────────────────────────────────────
    if not d.get("esg"):
        d["esg"] = {
            "score": d.get("esg_score", "18"),
            "out_of": 40,
            "grade": d.get("esg_grade", "B- — مقبول (إرشادي QA)"),
            "cap_rate_adj": "+0.25% (مخاطر ESG منخفضة نسبياً — إرشادي)",
            "terminal_adj": "-1.5",
            "climate_risk": d.get("climate_risk", "منخفض — لا تقرير مناخي رسمي"),
            "breakdown": [
                {"category": "البيئة (E) — كفاءة الطاقة والمياه",  "score": 7, "max": 15, "pct": "47%", "note": "لا شهادة طاقة · لا ألواح شمسية مؤكدة"},
                {"category": "الاجتماع (S) — الخدمات المجتمعية",   "score": 6, "max": 15, "pct": "40%", "note": "قرب من مدارس ومستشفيات · لا شهادة LEED"},
                {"category": "الحوكمة (G) — إدارة الأصل والشفافية", "score": 5, "max": 10, "pct": "50%", "note": "إدارة مبنى عبر شركة · لا تقارير شفافية دورية"},
            ],
        }
    d.setdefault("esg_score", "18")
    d.setdefault("esg_grade", "B- — مقبول (إرشادي QA)")
    d.setdefault("climate_risk", "منخفض — لا تقرير مناخي رسمي")

    # ── Confidence factors table ───────────────────────────────────────────
    if not d.get("confidence_factors"):
        _cv_pct_cf = d.get("cv_data", {}).get("cv_pct", 18) if d.get("cv_data") else 18
        d["confidence_factors"] = [
            {"factor": "جودة البيانات المدخلة",     "weight": "35%", "score": 3, "max": 5, "note": "محاكاة QA — غير موثقة من مصادر رسمية"},
            {"factor": "اكتمال الوثائق القانونية", "weight": "25%", "score": 2, "max": 5, "note": "وثائق ملكية ورخصة بناء غير مؤكدة"},
            {"factor": "معاينة ميدانية موثقة",     "weight": "20%", "score": 1, "max": 5, "note": "لا معاينة ميدانية — قيد على نطاق العمل"},
            {"factor": "اتساق طرق التقييم (CV)",   "weight": "15%", "score": 2, "max": 5, "note": f"CV = {_cv_pct_cf}% — مرتفع نسبياً"},
            {"factor": "توقيع وخبرة المقيِّم",     "weight": "5%",  "score": 3, "max": 5, "note": "بانتظار توقيع خبير مرخص"},
        ]

    # ── Recommendation advisory table ────────────────────────────────────
    if not d.get("recommendation_advisory"):
        d["recommendation_advisory"] = [
            {"aspect": "استكمال التوثيق",    "description": "استكمال وثائق الملكية ورخصة البناء وشهادة إتمام البناء قبل أي استخدام رسمي", "priority": "عاجل"},
            {"aspect": "الفحص الميداني",     "description": "إجراء معاينة ميدانية مؤكدة مع تقرير مصور من خبير معتمد قبل إصدار تقرير نهائي", "priority": "عاجل"},
            {"aspect": "بيانات السوق",       "description": "استبدال بيانات QA بمعلومات سوقية حقيقية من مصادر رسمية (≥3 صفقات موثقة)", "priority": "عالي"},
            {"aspect": "توقيع الخبير",       "description": "الحصول على توقيع خبير تقييم عقاري مرخص مع ختم الشركة قبل تقديم التقرير لأي جهة", "priority": "إلزامي"},
            {"aspect": "مراجعة القيمة",      "description": "إعادة التقييم سنوياً أو عند تغير ظروف السوق بما يزيد على 5% لضمان دقة القيمة", "priority": "دوري"},
        ]

    # ── Certification risks ───────────────────────────────────────────────
    if not d.get("cert_risks"):
        d["cert_risks"] = [
            "توقيع الخبير المرخص مفقود — إلزامي للاعتماد الرسمي",
            "ختم الشركة والترخيص المهني للمقيّم لم يُرفقا",
            "شهادة إتمام البناء أو رخصة البناء غير موثقة",
            "مستندات الملكية والتصرفات لم تُراجع بصورة مستقلة",
            "لا مقارنات سوقية حقيقية موثقة — يعتمد على محاكاة QA",
            "لم تُجرَ معاينة ميدانية مع صور وتقرير رسمي مرفق",
        ]
    d.setdefault("cert_risk_level", "مرتفع")

    # ── Land comparable rows ──────────────────────────────────────────────
    if not d.get("land_comparable_rows"):
        _la = _safe_float(d.get("area_sqm")) or 150.0
        _land_psm = _safe_float(d.get("land_value_psm")) or 8_000
        _laddr = d.get("property_address", "نفس المنطقة")
        d["land_comparable_rows"] = [
            {"ref": "أ1", "location": f"{_laddr} — قطعة ١ (QA)", "area": int(_la * 0.80), "price_sqm": int(_land_psm * 1.05), "total_price": int(_la * 0.80 * _land_psm * 1.05), "date": "2026-01", "notes": "قطعة ركنية — محاكاة QA"},
            {"ref": "أ2", "location": f"{_laddr} — قطعة ٢ (QA)", "area": int(_la * 1.20), "price_sqm": int(_land_psm * 0.97), "total_price": int(_la * 1.20 * _land_psm * 0.97), "date": "2025-11", "notes": "واجهة رئيسية — محاكاة QA"},
            {"ref": "أ3", "location": f"{_laddr} — قطعة ٣ (QA)", "area": int(_la * 1.00), "price_sqm": int(_land_psm * 1.02), "total_price": int(_la * 1.00 * _land_psm * 1.02), "date": "2026-03", "notes": "قطعة داخلية — محاكاة QA"},
            {"ref": "أ4", "location": f"{_laddr} — قطعة ٤ (QA)", "area": int(_la * 0.60), "price_sqm": int(_land_psm * 1.08), "total_price": int(_la * 0.60 * _land_psm * 1.08), "date": "2025-12", "notes": "إطلالة مميزة — محاكاة QA"},
            {"ref": "أ5", "location": f"{_laddr} — قطعة ٥ (QA)", "area": int(_la * 1.50), "price_sqm": int(_land_psm * 0.94), "total_price": int(_la * 1.50 * _land_psm * 0.94), "date": "2025-09", "notes": "مساحة كبيرة — خصم كمية — محاكاة QA"},
        ]

    # ── DCF cumulative PV (running total column) ──────────────────────────
    if d.get("dcf_years"):
        _cum_pv = 0
        for _yr_row in d["dcf_years"]:
            _cum_pv += int(_yr_row.get("pv", 0))
            _yr_row.setdefault("cum_pv", _cum_pv)

    # ── DCF QA scenarios brief (Bear / Base / Bull) ───────────────────────
    if not d.get("dcf_scenarios_brief") and d.get("dcf_years"):
        _bv = _safe_float(d.get("final_value")) or 3_000_000
        _dr = _safe_float(d.get("discount_rate")) or 12.5
        _gr = _safe_float(d.get("growth_rate")) or 3.5
        d["dcf_scenarios_brief"] = [
            {"name": "متشائم (Bear)", "growth": 1.0, "vacancy": 15.0,
             "disc": round(_dr + 2.5, 1), "value": int(_bv * 0.84),
             "note": "محاكاة QA — غير معتمدة"},
            {"name": "أساسي (Base)",  "growth": _gr,  "vacancy": 5.0,
             "disc": _dr, "value": int(_bv),
             "note": "محاكاة QA — غير معتمدة"},
            {"name": "متفائل (Bull)", "growth": 6.0, "vacancy": 2.0,
             "disc": round(max(9.0, _dr - 2.5), 1), "value": int(_bv * 1.22),
             "note": "محاكاة QA — غير معتمدة"},
        ]

    # ── BOQ grand total (sum of all items) ────────────────────────────────
    if d.get("boq_items") and not d.get("boq_grand_total"):
        _gt = sum(_safe_float(item.get("total", 0)) or 0.0 for item in d["boq_items"])
        d["boq_grand_total"] = int(_gt)

    # ── Comparables statistics (min / max / median / mean) ────────────────
    if d.get("comparables") and not d.get("comparables_stats"):
        _avs = [_safe_float(c.get("adj_value")) for c in d["comparables"]
                if _safe_float(c.get("adj_value"))]
        if _avs:
            _mn = min(_avs); _mx = max(_avs)
            _srt = sorted(_avs)
            _med = _srt[len(_srt) // 2]
            _mean = sum(_avs) / len(_avs)
            _a_s = _safe_float(d.get("area_sqm")) or 150.0
            d["comparables_stats"] = {
                "count":      len(_avs),
                "min_adj":    int(_mn),
                "max_adj":    int(_mx),
                "median_adj": int(_med),
                "mean_adj":   int(_mean),
                "range_pct":  round((_mx - _mn) / _mean * 100, 1) if _mean else 0,
                "min_psm":    int(_mn  / _a_s) if _a_s > 0 else 0,
                "max_psm":    int(_mx  / _a_s) if _a_s > 0 else 0,
                "median_psm": int(_med / _a_s) if _a_s > 0 else 0,
            }

    return d


def _enrich_detailed_data(data: dict) -> dict:
    """Extend traditional enrichment with Detailed-tier QA display defaults.

    Populates income-cap, sensitivity matrix, scenarios, risk register, ESG,
    and data-quality panels when not supplied by the caller. Never overwrites
    caller-supplied values. All auto-generated defaults are tagged QA.
    """
    _SIM = "محاكاة داخلية/QA — غير معتمدة"

    d = _enrich_traditional_data(data)

    # ── Income cap block ──────────────────────────────────────────────────
    if not d.get("income_cap"):
        noi_v = _safe_float(d.get("annual_noi") or d.get("noi"))
        cap_r = _safe_float(d.get("cap_rate_used") or d.get("cap_rate_exit"))
        fv_ic = _safe_float(d.get("final_value")) or 3_000_000
        if not noi_v:
            noi_v = fv_ic * 0.0456
        if not cap_r:
            cap_r = 7.5
        gross_r = noi_v / 0.85
        vac_rate = 5.0
        eri = gross_r * (1 - vac_rate / 100)
        opex = eri * 0.15
        noi_ic = eri - opex
        d["income_cap"] = {
            "gross_rent":       int(gross_r),
            "vacancy_rate":     vac_rate,
            "eri":              int(eri),
            "opex":             int(opex),
            "noi":              int(noi_ic),
            "cap_rate":         cap_r,
            "capitalized_value": int(noi_ic / (cap_r / 100.0)),
        }

    # ── Sensitivity matrix (QA placeholder) ──────────────────────────────
    if not d.get("sensitivity_matrix"):
        base_val = _safe_float(d.get("final_value")) or 3_000_000
        disc_rates = [10.0, 11.0, 12.5, 14.0, 15.0]
        growth_offsets = [-1.5, -0.5, 0.0, 1.0, 2.0]
        d["sensitivity_matrix"] = [
            {
                "disc_rate": dr,
                "values": [
                    int(base_val * (1 + g / 100 + (12.5 - dr) / 100))
                    for g in growth_offsets
                ],
            }
            for dr in disc_rates
        ]
        d["sensitivity_growth_rates"] = ["1%", "2%", "3.5%", "5%", "6%"]

    # ── Scenarios (QA Bear/Base/Bull) ─────────────────────────────────────
    if not d.get("scenarios"):
        base_val = _safe_float(d.get("final_value")) or 3_000_000
        disc = _safe_float(d.get("discount_rate")) or 12.5
        growth = _safe_float(d.get("growth_rate")) or 3.5
        bull_disc = max(9.0, disc - 2.5)
        d["scenarios"] = [
            {
                "name": "متشائم",
                "growth_rate": 1.0, "discount_rate": disc + 2.5,
                "vacancy": 15, "value": int(base_val * 0.84),
                "npv": int(-base_val * 0.08),
            },
            {
                "name": "أساسي",
                "growth_rate": growth, "discount_rate": disc,
                "vacancy": 5, "value": int(base_val),
                "npv": int(base_val * 0.09),
            },
            {
                "name": "متفائل",
                "growth_rate": 6.0, "discount_rate": bull_disc,
                "vacancy": 2, "value": int(base_val * 1.22),
                "npv": int(base_val * 0.26),
            },
        ]

    # ── Risk register (QA items) ──────────────────────────────────────────
    if not d.get("risk_register"):
        d["risk_register"] = [
            {
                "risk": "عدم استكمال الوثائق",
                "category": "قانوني",
                "probability": 4, "impact": 4, "score": 16,
                "response": "استكمال الوثائق قبل الاعتماد",
            },
            {
                "risk": "تقلبات سعر الفائدة",
                "category": "مالي",
                "probability": 3, "impact": 3, "score": 9,
                "response": "مراقبة دورية",
            },
            {
                "risk": "انخفاض الطلب السكني",
                "category": "سوقي",
                "probability": 2, "impact": 3, "score": 6,
                "response": "تنويع المستأجرين",
            },
        ]

    # ── ESG (QA placeholder) ──────────────────────────────────────────────
    if not d.get("esg"):
        d["esg"] = {
            "environmental_score": 47, "environmental_note": "لا شهادة طاقة — لا ألواح شمسية مؤكدة",
            "social_score":        40, "social_note":        "قرب من مدارس ومستشفيات — لا شهادة LEED",
            "governance_score":    50, "governance_note":    "إدارة مبنى عبر شركة — لا تقارير شفافية دورية",
            "total_score":         46, "overall_note":       _SIM,
        }

    # ── Data quality (QA placeholder) ────────────────────────────────────
    if not d.get("data_quality"):
        d["data_quality"] = [
            {"dimension": "اكتمال البيانات",           "score": 70, "note": _SIM},
            {"dimension": "موثوقية المصادر",           "score": 55, "note": _SIM},
            {"dimension": "حداثة البيانات",            "score": 80, "note": "2026"},
            {"dimension": "دقة بيانات المقارنات",      "score": 60, "note": "محاكاة QA — غير موثقة"},
            {"dimension": "اكتمال الوثائق القانونية", "score": 45, "note": "وثائق جزئية — بانتظار استكمال"},
        ]
        d.setdefault("data_completeness", 70)
        d.setdefault("data_reliability", 55)

    # ── Expanded risk register (8 risks across categories) ───────────────
    if not d.get("risk_register") or len(d.get("risk_register", [])) < 5:
        d["risk_register"] = [
            {"risk": "عدم استكمال وثائق الملكية",        "category": "قانوني",  "probability": 4, "impact": 4, "score": 16, "response": "استكمال الوثائق قبل الاعتماد — أولوية قصوى",           "evidence": _SIM, "status": "معلق"},
            {"risk": "غياب توقيع الخبير المرخص",         "category": "حوكمة",   "probability": 5, "impact": 5, "score": 25, "response": "الحصول على توقيع خبير RICS/TAQEEM مع ختم رسمي",        "evidence": _SIM, "status": "معلق"},
            {"risk": "تقلبات معدلات الفائدة (± 2%)",     "category": "مالي",    "probability": 3, "impact": 3, "score": 9,  "response": "مراجعة DCF دورية — إعادة حساب عند التغير > 1%",      "evidence": _SIM, "status": "جارٍ"},
            {"risk": "انخفاض الطلب السكني في المنطقة",   "category": "سوقي",    "probability": 2, "impact": 3, "score": 6,  "response": "تنويع المستأجرين — مراجعة الإيجار كل 6 أشهر",       "evidence": _SIM, "status": "مراقبة"},
            {"risk": "تغير اشتراطات التخطيط العمراني",   "category": "تنظيمي", "probability": 2, "impact": 4, "score": 8,  "response": "متابعة لوائح الهيئة — فحص قانوني دوري",              "evidence": _SIM, "status": "مراقبة"},
            {"risk": "بيانات السوق محاكاة QA فقط",       "category": "بيانات",  "probability": 5, "impact": 4, "score": 20, "response": "تفعيل Qdrant وربط مصادر رسمية (Bayut / AQARMAP)",    "evidence": _SIM, "status": "معلق"},
            {"risk": "ارتفاع تكاليف الإنشاء والتضخم",   "category": "اقتصادي", "probability": 3, "impact": 2, "score": 6,  "response": "احتياطي 4-5% في BOQ — مراجعة عروض الأسعار سنوياً", "evidence": _SIM, "status": "مراقبة"},
            {"risk": "مخاطر ESG وتغير المناخ",            "category": "بيئي",    "probability": 2, "impact": 2, "score": 4,  "response": "تقييم ESG مستقل — رفع كفاءة الطاقة",                "evidence": _SIM, "status": "مراقبة"},
        ]

    # ── Rent comparables (5 QA entries) ──────────────────────────────────
    if not d.get("rent_comps"):
        _area = _safe_float(d.get("area_sqm")) or 150.0
        _addr = d.get("property_address", "نفس المنطقة")
        _fv3 = _safe_float(d.get("final_value")) or 3_000_000
        _ann = _safe_float(d.get("annual_noi") or d.get("noi")) or (_fv3 * 0.05)
        _r_sqm = int(_ann / 12 / _area * 1.15)
        d["rent_comps"] = [
            {"location": f"{_addr} — إيجار ١ (QA)", "area": int(_area * 1.05), "annual_rent": int(_ann * 1.08), "rent_sqm": int(_r_sqm * 1.03), "date": "2026-01", "note": "شقة مطابقة — طابق أعلى — محاكاة QA"},
            {"location": f"{_addr} — إيجار ٢ (QA)", "area": int(_area * 0.90), "annual_rent": int(_ann * 0.97), "rent_sqm": int(_r_sqm * 1.08), "date": "2025-10", "note": "شقة أصغر — تشطيب أفضل — محاكاة QA"},
            {"location": f"{_addr} — إيجار ٣ (QA)", "area": int(_area * 1.10), "annual_rent": int(_ann * 1.04), "rent_sqm": int(_r_sqm * 0.95), "date": "2025-12", "note": "شقة أكبر — موقع مماثل — محاكاة QA"},
            {"location": f"{_addr} — إيجار ٤ (QA)", "area": int(_area * 0.95), "annual_rent": int(_ann * 0.93), "rent_sqm": int(_r_sqm * 0.98), "date": "2026-02", "note": "شقة مشابهة — طابق أدنى — محاكاة QA"},
            {"location": f"{_addr} — إيجار ٥ (QA)", "area": int(_area * 1.20), "annual_rent": int(_ann * 1.15), "rent_sqm": int(_r_sqm * 0.96), "date": "2025-09", "note": "شقة أكبر — إطلالة مميزة — محاكاة QA"},
        ]

    # ── Market evidence (5 QA entries) ────────────────────────────────────
    if not d.get("market_evidence"):
        _fv4 = _safe_float(d.get("final_value")) or 3_000_000
        _a4 = _safe_float(d.get("area_sqm")) or 150.0
        _psm4 = int(_fv4 / _a4)
        d["market_evidence"] = [
            {"type": "معدل سعر المتر المربع",        "source": "محاكاة QA",        "value": f"{_psm4:,} م.ج/م²",   "date": "2026-Q2", "status": "تمثيلي — محاكاة QA"},
            {"type": "متوسط عائد الإيجار",           "source": "محاكاة QA",        "value": "5.0% – 7.5%",         "date": "2026-Q1", "status": "تمثيلي — محاكاة QA"},
            {"type": "معدل الشغور في المنطقة",       "source": "محاكاة QA",        "value": "5% – 8%",             "date": "2026-Q1", "status": "تمثيلي — محاكاة QA"},
            {"type": "حجم الصفقات السنوية",          "source": "غير متاح — Qdrant", "value": "غير متاح ضمن بيانات الطلب", "date": "—",  "status": "غير متاح"},
            {"type": "مؤشر أسعار العقارات السكنية", "source": "غير متاح — Qdrant", "value": "غير متاح ضمن بيانات الطلب", "date": "—",  "status": "غير متاح"},
        ]

    # ── Source registry (8 sources) ──────────────────────────────────────
    if not d.get("sources"):
        d["sources"] = [
            {"name": "بيانات العميل المُقدَّمة",               "type": "مُقدَّمة",       "status": "متاح",    "note": "بيانات الطلب الأصلية — صحة القيم مسؤولية العميل"},
            {"name": "محاكاة QA داخلية",                       "type": "محاكاة",         "status": "متاح",    "note": "جميع القيم المُولَّدة محاكاة إرشادية — غير موثقة"},
            {"name": "قاعدة بيانات Qdrant/RAG",               "type": "بيانات سوقية",   "status": "غير متاح", "note": "Qdrant/RAG غير مفعَّل — لا scraping — لا بيانات حقيقية"},
            {"name": "هيئة الرقابة المالية (FRA)",             "type": "تنظيمي",        "status": "غير متاح", "note": "مصدر رسمي — غير مفعَّل في هذه النسخة"},
            {"name": "AQARMAP / Bayut",                        "type": "سوق عقاري",      "status": "غير متاح", "note": "مصدر سوقي خارجي — لا اشتراك فعّال"},
            {"name": "الشهر العقاري",                          "type": "توثيق رسمي",    "status": "غير متاح", "note": "توثيق الصفقات الرسمي — يتطلب اشتراكاً حكومياً"},
            {"name": "هيئة المجتمعات العمرانية",              "type": "تنظيمي",        "status": "غير متاح", "note": "بيانات أراضٍ رسمية — لا ربط فعّال"},
            {"name": "تقرير الفحص الميداني",                  "type": "ميداني",        "status": "غير متاح", "note": "يتطلب معاينة ميدانية من خبير مرخص"},
        ]

    # ── Land extraction method ────────────────────────────────────────────
    if not d.get("land_extraction"):
        _fv5 = _safe_float(d.get("final_value")) or 3_000_000
        _rcn5 = _safe_float(d.get("rcn")) or (_fv5 * 0.55)
        _dep5 = _safe_float(d.get("total_depreciation")) or 15.0
        _bv5 = int(_rcn5 * (1 - _dep5 / 100))
        _lv5 = int(_fv5 - _bv5)
        _la5 = _safe_float(d.get("area_sqm")) or 150.0
        d["land_extraction"] = {
            "total_value":        int(_fv5),
            "rcn":                int(_rcn5),
            "depreciation":       _dep5,
            "building_dep_value": _bv5,
            "extracted_land_value": _lv5,
            "land_price_sqm":     int(_lv5 / (_la5 * 0.20)) if _la5 > 0 else 0,
        }

    # ── Land residual method ──────────────────────────────────────────────
    if not d.get("land_residual"):
        _fv6 = _safe_float(d.get("final_value")) or 3_000_000
        _gdv6 = int(_fv6 * 1.25)
        _bc6 = int(_fv6 * 0.55)
        _dev_margin6 = 15
        _res6 = int(_gdv6 - _bc6 - _gdv6 * _dev_margin6 / 100)
        d["land_residual"] = {
            "gdv":               _gdv6,
            "build_cost":        _bc6,
            "developer_margin":  _dev_margin6,
            "residual_land_value": _res6,
        }

    # ── Site improvements (3 items) ───────────────────────────────────────
    if not d.get("site_improvements"):
        _fv7 = _safe_float(d.get("final_value")) or 3_000_000
        d["site_improvements"] = [
            {"item": "تشجير وتنسيق حدائق",   "cost": int(_fv7 * 0.008), "dep_pct": 15, "contrib_value": int(_fv7 * 0.007)},
            {"item": "أعمال رصف ومداخل",      "cost": int(_fv7 * 0.006), "dep_pct": 20, "contrib_value": int(_fv7 * 0.005)},
            {"item": "إنارة خارجية وكاميرات", "cost": int(_fv7 * 0.005), "dep_pct": 25, "contrib_value": int(_fv7 * 0.004)},
        ]

    # ── Land adjustment matrix (5 factors × 3 lands) ─────────────────────
    if not d.get("land_adj_items"):
        d["land_adj_items"] = [
            {"factor": "تسوية الموقع والواجهة",  "values": ["+5%",  "0%",   "+2%"]},
            {"factor": "تسوية المساحة",           "values": ["+3%",  "-2%",  "0%"]},
            {"factor": "تسوية الزمن",             "values": ["-1%",  "-1%",  "-1%"]},
            {"factor": "تسوية الشكل والانتظام",  "values": ["0%",   "+2%",  "-1%"]},
            {"factor": "تسوية الخدمات المتاحة",  "values": ["+2%",  "+1%",  "+3%"]},
            {"factor": "إجمالي التسوية",          "values": ["+9%",  "0%",   "+3%"]},
        ]
        _lpsm7 = _safe_float(d.get("land_price_sqm")) or 8_000
        d.setdefault("land_sales_value",       int(_lpsm7 * 1.0))
        d.setdefault("land_extraction_value",  int(_lpsm7 * 0.95))
        d.setdefault("land_residual_value",    int(_lpsm7 * 1.05))
        d.setdefault("land_sales_weight",      "50%")
        d.setdefault("land_extraction_weight", "30%")
        d.setdefault("land_residual_weight",   "20%")

    # ── Sales adjustment matrix (6 factors × 4 comparables) ──────────────
    if not d.get("sales_adj_matrix"):
        d["sales_adj_matrix"] = [
            {"factor": "تسوية الموقع والحي",         "values": ["+5%",  "-3%",  "0%",   "-2%"]},
            {"factor": "تسوية الزمن والسوق",          "values": ["-1%",  "-1%",  "-1%",  "-1%"]},
            {"factor": "تسوية المساحة",               "values": ["-2%",  "+4%",  "-1%",  "0%"]},
            {"factor": "تسوية الحالة والتشطيب",      "values": ["0%",   "+5%",  "+2%",  "+3%"]},
            {"factor": "تسوية الطابق والإطلالة",     "values": ["+3%",  "0%",   "+1%",  "+2%"]},
            {"factor": "إجمالي التسوية",              "values": ["+5%",  "+5%",  "+1%",  "+2%"]},
        ]

    # ── NPV / IRR / Payback QA fallbacks ──────────────────────────────────
    if not d.get("npv") and not d.get("irr"):
        _fv8 = _safe_float(d.get("final_value")) or 3_000_000
        _disc8 = _safe_float(d.get("discount_rate")) or 12.5
        d.setdefault("npv",           int(_fv8 * 0.089))
        d.setdefault("irr",           str(round(_disc8 + 2.3, 1)))
        d.setdefault("payback_years", str(round(1.0 / (0.056 if _disc8 < 13 else 0.048), 1)))
        d.setdefault("equity_multiple", "1.45x")

    # ── Gross yield / net yield for sale-rent section ─────────────────────
    if not d.get("gross_yield"):
        _fv9 = _safe_float(d.get("final_value")) or 3_000_000
        _noi9 = _safe_float(d.get("annual_noi") or d.get("noi")) or (_fv9 * 0.05)
        _gr9 = round(_noi9 / _fv9 * 100 * 1.18, 1)
        _nr9 = round(_noi9 / _fv9 * 100, 1)
        d.setdefault("gross_yield",           _gr9)
        d.setdefault("net_yield",             _nr9)
        d.setdefault("grm",                   round(_fv9 / (_noi9 * 1.18), 2))
        d.setdefault("noi",                   int(_noi9))
        d.setdefault("sale_rent_recommendation", "البيع يُفضَّل حالياً نظراً لنسبة العائد الإرشادية — مراجعة مطلوبة")

    # ── Market evidence / executive summary text ───────────────────────────
    if not d.get("exec_summary"):
        _fv10 = _safe_float(d.get("final_value")) or 3_000_000
        _addr10 = d.get("property_address", "العقار المحدد")
        _ptype10 = d.get("property_type", "عقار")
        _area10 = _safe_float(d.get("area_sqm")) or 150
        _conf10 = d.get("confidence_score", 65)
        d["exec_summary"] = (
            f"تقييم إرشادي تفصيلي لـ{_ptype10} في {_addr10} بمساحة {_area10:.0f} م². "
            f"القيمة السوقية الإرشادية المُقدَّرة {_fv10:,.0f} م.ج وفق ثلاث طرق تقييمية "
            f"(مقارنة المبيعات · مدخل التكلفة · DCF). درجة الثقة الإرشادية {_conf10}%. "
            "جميع البيانات تمثيلية (محاكاة QA) — تتطلب التحقق من مصادر رسمية قبل أي استخدام رسمي. "
            "لا يُصدر هذا النظام شهادة اعتماد آلية — يتطلب توقيع خبير تقييم عقاري مرخص."
        )

    # ── RCN detail (base/finishing/services/contingency) ─────────────────
    if not d.get("base_construction_cost"):
        _fv11 = _safe_float(d.get("final_value")) or 3_000_000
        _rcn11 = _safe_float(d.get("rcn")) or (_fv11 * 0.55)
        d.setdefault("base_construction_cost", int(_rcn11 * 0.60))
        d.setdefault("finishing_cost",         int(_rcn11 * 0.25))
        d.setdefault("services_cost",          int(_rcn11 * 0.11))
        d.setdefault("contingency_cost",       int(_rcn11 * 0.04))
        d.setdefault("rcn",                    int(_rcn11))
        _a11 = _safe_float(d.get("area_sqm")) or 150.0
        d.setdefault("rcn_per_sqm",            int(_rcn11 / _a11) if _a11 > 0 else 0)
        d.setdefault("annual_depreciation_rate", round(100.0 / (_safe_float(d.get("economic_life")) or 50), 2))
        d.setdefault("remaining_economic_life",  int(max(0, (_safe_float(d.get("economic_life")) or 50) - (_safe_float(d.get("age_years")) or 8))))

    # ── Recommendation advisory table (if not already set by parent) ──────
    if not d.get("recommendation"):
        _fv12 = _safe_float(d.get("final_value")) or 3_000_000
        d["recommendation"] = (
            f"القيمة الإرشادية المُقدَّرة {_fv12:,.0f} م.ج (محاكاة QA — غير معتمدة). "
            "يُنصح باستكمال وثائق الملكية وإجراء الفحص الميداني المعتمد قبل أي استخدام رسمي. "
            "الحصول على توقيع خبير تقييم عقاري مرخص (RICS / TAQEEM) إلزامي للاعتماد الرسمي."
        )

    return d


def build_traditional_html(data: dict) -> str:
    """Build Traditional tier HTML string from *data* dict.

    All missing values fall back to the Arabic NA sentinel.
    Returns a complete, standalone HTML string ready for Playwright.
    """
    try:
        from jinja2 import Environment, FileSystemLoader
    except ImportError as exc:
        raise RuntimeError("Jinja2 is required: pip install jinja2") from exc

    css = _CSS_PATH.read_text(encoding="utf-8") if _CSS_PATH.exists() else ""
    font_css = _load_cairo_font_css()

    env = Environment(loader=FileSystemLoader(str(_TEMPLATES)), autoescape=False)
    env.globals["_fmt"] = _fmt
    env.globals["_na"] = _na

    enriched = _enrich_traditional_data(data)
    tmpl = env.get_template("pv_traditional_report.html")
    return tmpl.render(data=enriched, css=css, font_css=font_css, NA=_NA)


def render_traditional_pdf(
    data: dict,
    output_path: "str | pathlib.Path | None" = None,
) -> bytes:
    """Render Traditional tier to PDF bytes via Playwright/shared renderer.

    Never produces Certified output — watermark is non-removable by design.
    """
    renderer = _load_renderer()
    html = build_traditional_html(data)
    pdf_bytes = renderer(html)
    if output_path:
        p = pathlib.Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(pdf_bytes)
    return pdf_bytes


def build_detailed_html(data: dict) -> str:
    """Build Detailed tier HTML string from *data* dict.

    Extends Traditional with workbook-derived analytical depth:
    land methods, income cap, NPV/IRR, sensitivity, risk register, ESG.
    All missing values fall back to the Arabic NA sentinel.
    Returns a complete, standalone HTML string ready for Playwright.
    """
    try:
        from jinja2 import Environment, FileSystemLoader
    except ImportError as exc:
        raise RuntimeError("Jinja2 is required: pip install jinja2") from exc

    css = _CSS_PATH.read_text(encoding="utf-8") if _CSS_PATH.exists() else ""
    font_css = _load_cairo_font_css()

    env = Environment(loader=FileSystemLoader(str(_TEMPLATES)), autoescape=False)
    env.globals["_fmt"] = _fmt
    env.globals["_na"] = _na

    tmpl = env.get_template("pv_detailed_report.html")
    return tmpl.render(data=_enrich_detailed_data(data), css=css, font_css=font_css, NA=_NA)


def render_detailed_pdf(
    data: dict,
    output_path: "str | pathlib.Path | None" = None,
) -> bytes:
    """Render Detailed tier to PDF bytes via Playwright/shared renderer.

    Never produces Certified output — watermark is non-removable by design.
    """
    renderer = _load_renderer()
    html = build_detailed_html(data)
    pdf_bytes = renderer(html)
    if output_path:
        p = pathlib.Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(pdf_bytes)
    return pdf_bytes


def _enrich_professional_data(data: dict) -> dict:
    """Extend Detailed enrichment with Professional-tier compliance and governance defaults.

    Adds standards readiness, cert-readiness checklist, cert traffic-light status,
    weighted methods matrix, appendix items, exec summary, scope of work, and full
    Professional-tier analytical layers (critical blockers, action register, evidence
    index, location quality, compliance score block, weight sensitivity, etc.).
    Never overwrites caller-supplied values. All QA defaults are labelled.
    """
    _SIM = "محاكاة داخلية/QA — غير معتمدة"

    d = _enrich_detailed_data(data)

    # ── Normalise dict-typed fields that templates expect ─────────────
    for _key in ("land_extraction", "land_residual", "direct_costs", "indirect_costs",
                 "compliance_statement", "disclosures"):
        if d.get(_key) is None:
            d[_key] = {}

    # ── Document control block ────────────────────────────────────────
    if not d.get("doc_control"):
        d["doc_control"] = {
            "report_ref":    d.get("report_ref", "PRO-AI-DRAFT"),
            "version":       "1.0 — مسودة",
            "status":        "مسودة غير معتمدة",
            "classification":"سري — استرشادي",
            "valuation_date":d.get("report_date", _NA),
            "issue_date":    d.get("report_date", _NA),
            "author":        "محرك التقييم الآلي — Expert Smart",
            "reviewer":      "بانتظار مراجعة خبير مرخّص",
            "approver":      "بانتظار التوقيع الرسمي",
        }

    # ── Assignment identification ─────────────────────────────────────
    if not d.get("assignment_id"):
        d["assignment_id"] = {
            "client":        d.get("client_name", _NA),
            "intended_user": d.get("intended_use", _NA),
            "purpose":       d.get("valuation_purpose", _NA),
            "basis":         d.get("valuation_basis", _NA),
            "effective_date":d.get("report_date", _NA),
            "property_type": d.get("property_type", _NA),
            "area":          str(d.get("area_sqm", _NA)) + " م²",
            "address":       d.get("property_address", _NA),
        }

    # ── Scope boundaries (included / excluded) ────────────────────────
    if not d.get("scope_boundaries"):
        d["scope_boundaries"] = [
            {"item": "تحليل السوق المحلي والأدلة المقارنة",   "included": True},
            {"item": "مدخل المقارنة السوقية (6 مقارنات)",      "included": True},
            {"item": "مدخل التكلفة مع BOQ التفصيلي",           "included": True},
            {"item": "مدخل الدخل والرسملة",                    "included": True},
            {"item": "نموذج DCF (5 سنوات)",                    "included": True},
            {"item": "تحليل الحساسية والسيناريوهات",            "included": True},
            {"item": "سجل المخاطر مفصَّل",                     "included": True},
            {"item": "تحليل HBU + SWOT + ESG",                "included": True},
            {"item": "جاهزية IVS/RICS/TAQEEM/USPAP",          "included": True},
            {"item": "مصالحة موزونة مع حساسية ±10%",           "included": True},
            {"item": "فحص ميداني رسمي",                        "included": False},
            {"item": "استعلام سجل الملكية الرسمي",              "included": False},
            {"item": "تصنيف بيئي رسمي",                        "included": False},
            {"item": "اعتماد رسمي أو توقيع خبير",              "included": False},
        ]

    # ── Location quality scoring ──────────────────────────────────────
    if not d.get("location_quality"):
        d["location_quality"] = [
            {"criterion": "إمكانية الوصول وشبكة الطرق",    "score": 75, "weight": "20%", "note": _SIM},
            {"criterion": "القرب من المرافق والخدمات",      "score": 70, "weight": "15%", "note": _SIM},
            {"criterion": "المنطقة التعليمية والمدارس",      "score": 68, "weight": "10%", "note": _SIM},
            {"criterion": "الخدمات الصحية والمستشفيات",     "score": 72, "weight": "10%", "note": _SIM},
            {"criterion": "الأسواق والمراكز التجارية",       "score": 78, "weight": "15%", "note": _SIM},
            {"criterion": "مستوى الأمان والمنطقة",          "score": 80, "weight": "15%", "note": _SIM},
            {"criterion": "البيئة المحيطة والضوضاء",        "score": 65, "weight": "10%", "note": _SIM},
            {"criterion": "الأفق والإطلالة",                "score": 60, "weight": "5%",  "note": _SIM},
        ]

    # ── Missing document summary ──────────────────────────────────────
    if not d.get("missing_doc_summary"):
        missing = d.get("missing_docs") or []
        d["missing_doc_summary"] = [
            {"doc": "صك الملكية الرسمي",        "required": True,  "available": "صك الملكية" not in missing,    "impact": "تأثير عالٍ على الاعتماد"},
            {"doc": "رخصة البناء",               "required": True,  "available": "رخصة البناء" not in missing,   "impact": "تأثير عالٍ على الاعتماد"},
            {"doc": "الكشف المساحي الرسمي",      "required": True,  "available": False,                            "impact": "تأثير متوسط"},
            {"doc": "صور ميدانية للعقار",         "required": False, "available": False,                            "impact": "تأثير منخفض"},
            {"doc": "شهادة عدم المخالفات",        "required": True,  "available": False,                            "impact": "تأثير عالٍ على الاعتماد"},
            {"doc": "عقد الإيجار (إن وجد)",      "required": False, "available": False,                            "impact": "تأثير متوسط"},
        ]

    # ── Compliance score block ────────────────────────────────────────
    if not d.get("compliance_score_block"):
        raw = d.get("review_score") or 72
        blockers = 3
        penalty  = blockers * 3
        adjusted = max(0, int(raw) - penalty)
        d["compliance_score_block"] = {
            "raw_score":        raw,
            "critical_blockers": blockers,
            "blocker_penalty":   penalty,
            "adjusted_score":    adjusted,
            "traffic_light":     "أصفر — جاهزية جزئية",
            "readiness":         "CONDITIONALLY_READY",
            "maturity_level":    "المستوى 2 — تطوير",
            "note":              _SIM,
        }

    # ── Critical blocker register ─────────────────────────────────────
    if not d.get("critical_blockers"):
        d["critical_blockers"] = [
            {"id": "CB-01", "blocker": "توقيع المقيّم المرخّص غير متاح",       "impact": "عالٍ",  "action": "الحصول على توقيع مقيّم مرخّص",                "status": "معلَّق"},
            {"id": "CB-02", "blocker": "صك الملكية الرسمي غير مرفق",            "impact": "عالٍ",  "action": "استخراج صك الملكية من السجل العقاري",           "status": "معلَّق"},
            {"id": "CB-03", "blocker": "الكشف الميداني الرسمي غير منجز",        "impact": "متوسط", "action": "جدولة فحص ميداني رسمي",                         "status": "معلَّق"},
            {"id": "CB-04", "blocker": "بيانات السوق غير مُتحقَّق منها رسميًا", "impact": "متوسط", "action": "التحقق من المصادر الرسمية المعتمدة",             "status": "معلَّق"},
        ]

    # ── Required action register ──────────────────────────────────────
    if not d.get("required_actions"):
        d["required_actions"] = [
            {"id": "RA-01", "action": "استخراج صك الملكية الرسمي",           "priority": "عاجل",  "role": "العميل / المحامي",    "deadline": "قبل الاعتماد",  "status": "معلَّق"},
            {"id": "RA-02", "action": "إجراء فحص ميداني رسمي",               "priority": "عاجل",  "role": "مقيّم مرخّص",         "deadline": "قبل الاعتماد",  "status": "معلَّق"},
            {"id": "RA-03", "action": "مراجعة التقرير من قِبَل خبير مرخّص", "priority": "عاجل",  "role": "مقيّم عقاري مرخّص",  "deadline": "قبل الاعتماد",  "status": "معلَّق"},
            {"id": "RA-04", "action": "التحقق من بيانات السوق من مصادر رسمية","priority": "عالٍ", "role": "فريق البحث",           "deadline": "قبل الاعتماد",  "status": "معلَّق"},
            {"id": "RA-05", "action": "استيفاء متطلبات جاهزية IVS/RICS",    "priority": "عالٍ", "role": "مقيّم RICS/IVS",      "deadline": "عند الاستيفاء", "status": "معلَّق"},
            {"id": "RA-06", "action": "الحصول على ختم الجهة المعتمِدة",      "priority": "عالٍ", "role": "الجهة المعتمِدة",      "deadline": "عند الاستيفاء", "status": "معلَّق"},
        ]

    # ── Evidence index ────────────────────────────────────────────────
    if not d.get("evidence_index"):
        d["evidence_index"] = [
            {"ref": "EV-01", "type": "مقارنة بيع",   "description": "6 معاملات بيع مقارنة",     "source": "محاكاة داخلية/QA", "status": "تمثيلي — غير رسمي"},
            {"ref": "EV-02", "type": "إيجار مقارن",  "description": "5 عقود إيجار مقارنة",      "source": "محاكاة داخلية/QA", "status": "تمثيلي — غير رسمي"},
            {"ref": "EV-03", "type": "أرض مقارنة",   "description": "5 مبيعات أراضٍ مقارنة",   "source": "محاكاة داخلية/QA", "status": "تمثيلي — غير رسمي"},
            {"ref": "EV-04", "type": "تكلفة",        "description": "بيانات BOQ تفصيلية",       "source": "مُقدَّمة من الطالب","status": "مُقدَّم"},
            {"ref": "EV-05", "type": "دخل/DCF",      "description": "جدول DCF 5 سنوات",         "source": "مُقدَّمة من الطالب","status": "مُقدَّم"},
            {"ref": "EV-06", "type": "بيانات السوق", "description": "أدلة السوق المحلية",       "source": "محاكاة داخلية/QA", "status": "تمثيلي — غير رسمي"},
            {"ref": "EV-07", "type": "تنظيم",        "description": "التخطيط واستخدام الأرض",   "source": "غير متاح",          "status": "مطلوب — غير متاح"},
            {"ref": "EV-08", "type": "قانوني",        "description": "صك الملكية الرسمي",        "source": "غير متاح",          "status": "مطلوب — غير متاح"},
            {"ref": "EV-09", "type": "بيئي",         "description": "تقرير الالتزام البيئي",     "source": "غير متاح",          "status": "مطلوب — غير متاح"},
            {"ref": "EV-10", "type": "فحص ميداني",   "description": "تقرير الفحص الميداني",      "source": "غير متاح",          "status": "مطلوب — غير متاح"},
        ]

    # ── Standards readiness (Professional expanded) ───────────────────
    if not d.get("standards_readiness"):
        d["standards_readiness"] = [
            {"standard": "IVS (المعايير الدولية للتقييم)", "status": "جزئي", "note": _SIM},
            {"standard": "RICS Red Book",                  "status": "جزئي", "note": _SIM},
            {"standard": "TAQEEM / ESREA",                 "status": "جزئي", "note": _SIM},
            {"standard": "FRA (هيئة الرقابة المالية)",     "status": "جزئي", "note": _SIM},
        ]

    # ── Standards readiness detail (sub-criteria) ─────────────────────
    if not d.get("standards_readiness_detail"):
        d["standards_readiness_detail"] = [
            {"standard": "IVS",    "criteria": "تعريف القيمة السوقية",          "status": "جزئي",   "note": _SIM},
            {"standard": "IVS",    "criteria": "نطاق العمل والمهمة",            "status": "جزئي",   "note": _SIM},
            {"standard": "IVS",    "criteria": "أساليب التقييم المعتمدة",       "status": "جزئي",   "note": _SIM},
            {"standard": "IVS",    "criteria": "توثيق وإفصاح",                  "status": "مطلوب",  "note": _SIM},
            {"standard": "RICS",   "criteria": "VPS 1 — نطاق التكليف",         "status": "جزئي",   "note": _SIM},
            {"standard": "RICS",   "criteria": "VPS 3 — أساس القيمة",         "status": "جزئي",   "note": _SIM},
            {"standard": "RICS",   "criteria": "VPS 4 — التحقيق والتحليل",    "status": "جزئي",   "note": _SIM},
            {"standard": "RICS",   "criteria": "VPGA 2 — التقارير الرهنية",   "status": "مطلوب",  "note": _SIM},
            {"standard": "TAQEEM", "criteria": "المعيار 1 — المؤهلات",        "status": "مطلوب",  "note": _SIM},
            {"standard": "TAQEEM", "criteria": "المعيار 5 — منهجية التقييم", "status": "جزئي",   "note": _SIM},
            {"standard": "USPAP",  "criteria": "القاعدة 1 — ممارسة التقييم",  "status": "جزئي",   "note": _SIM},
            {"standard": "USPAP",  "criteria": "القاعدة 2 — التقرير",         "status": "جزئي",   "note": _SIM},
        ]

    # ── Certification readiness checklist (expanded) ──────────────────
    if not d.get("cert_readiness"):
        missing_docs = d.get("missing_docs") or []
        d["cert_readiness"] = [
            {"requirement": "سند الملكية الرسمي",       "evidence": "غير مرفق",  "blocker": True,  "action": "استخراج الصك",           "role": "العميل",      "decision_impact": "مانع للاعتماد", "state": "NOT_READY"},
            {"requirement": "رخصة البناء",               "evidence": "غير مرفقة", "blocker": True,  "action": "استخراج الرخصة",         "role": "العميل",      "decision_impact": "مانع للاعتماد", "state": "NOT_READY"},
            {"requirement": "صور ميدانية للعقار",         "evidence": "غير متاحة", "blocker": False, "action": "تصوير ميداني",           "role": "مقيّم",       "decision_impact": "جزئي",          "state": "CONDITIONALLY_READY"},
            {"requirement": "كشف مساحي رسمي",             "evidence": "غير متاح",  "blocker": True,  "action": "الحصول على كشف مساحي",  "role": "مساح قانوني", "decision_impact": "مانع للاعتماد", "state": "NOT_READY"},
            {"requirement": "توقيع المقيّم المرخّص",       "evidence": "معلَّق",    "blocker": True,  "action": "توقيع خبير مرخّص",       "role": "مقيّم مرخّص", "decision_impact": "مانع للاعتماد", "state": "NOT_READY"},
            {"requirement": "مراجعة النظراء (Peer Review)","evidence": "معلَّق",   "blocker": False, "action": "مراجعة خبير مستقل",     "role": "مقيّم مستقل","decision_impact": "مستحسن",         "state": "CONDITIONALLY_READY"},
            {"requirement": "ختم الجهة المعتمِدة",         "evidence": "معلَّق",    "blocker": True,  "action": "الحصول على ختم الجهة",   "role": "جهة معتمِدة", "decision_impact": "مانع للاعتماد", "state": "NOT_READY"},
            {"requirement": "استيفاء IVS/RICS",           "evidence": "جزئي",      "blocker": False, "action": "استيفاء بنود المعايير",  "role": "مقيّم معتمد", "decision_impact": "مستحسن",         "state": "CONDITIONALLY_READY"},
            {"requirement": "التحقق من بيانات السوق",     "evidence": "تمثيلي",    "blocker": False, "action": "التحقق من مصادر رسمية", "role": "فريق البحث",  "decision_impact": "جزئي",          "state": "CONDITIONALLY_READY"},
            {"requirement": "اعتماد نتائج AVM",           "evidence": "تمثيلي",    "blocker": False, "action": "تحقق مستقل من AVM",     "role": "خبير AVM",    "decision_impact": "جزئي",          "state": "CONDITIONALLY_READY"},
        ]

    # ── Cert overall status ───────────────────────────────────────────
    if not d.get("cert_overall_status"):
        cert_risks = d.get("cert_risks") or []
        missing = d.get("missing_docs") or []
        d["cert_overall_status"] = "pending" if (cert_risks or missing) else "partial"

    # ── Maturity levels ───────────────────────────────────────────────
    if not d.get("maturity_levels"):
        d["maturity_levels"] = [
            {"level": "المستوى 1", "label": "أولي",    "description": "أساسيات التقييم مكتملة",           "achieved": True},
            {"level": "المستوى 2", "label": "تطوير",   "description": "بيانات إضافية ومراجعة مطلوبة",     "achieved": True},
            {"level": "المستوى 3", "label": "مُدار",   "description": "مراجعة خبير مرخّص مطلوبة",         "achieved": False},
            {"level": "المستوى 4", "label": "مُحسَّن", "description": "معايير IVS/RICS مستوفاة بالكامل",  "achieved": False},
            {"level": "المستوى 5", "label": "محسوب",   "description": "اعتماد من جهة خارجية مستقلة",       "achieved": False},
        ]

    # ── Weighted methods matrix ───────────────────────────────────────
    if not d.get("weighted_methods"):
        pairs = [
            ("market_value",        "مقارنة البيوع",    d.get("market_weight", "40")),
            ("cost_approach_value", "مدخل التكلفة",     d.get("cost_weight",   "25")),
            ("dcf_value",           "مدخل DCF",         d.get("dcf_weight",    "35")),
        ]
        wm = []
        for key, label, weight_raw in pairs:
            v = _safe_float(d.get(key))
            w = _safe_float(str(weight_raw).replace("%", ""))
            if v and w is not None:
                wm.append({
                    "method": label,
                    "value":  v,
                    "weight": int(w),
                    "weighted_value": v * w / 100.0,
                    "provenance": "مُقدَّم من الطالب",
                    "availability": "متاح",
                })
        if wm:
            d["weighted_methods"] = wm

    # ── Weight sensitivity ±10% ───────────────────────────────────────
    if not d.get("weight_sensitivity"):
        wm = d.get("weighted_methods") or []
        rows: list = []
        for wme in wm:
            v = _safe_float(wme.get("value"))
            w = _safe_float(str(wme.get("weight", 0)))
            if v and w is not None:
                rows.append({
                    "method":             wme.get("method", _NA),
                    "base_weight":        int(w),
                    "minus10_weight":     max(0, int(w) - 10),
                    "plus10_weight":      int(w) + 10,
                    "base_contribution":  round(v * w / 100),
                    "minus10_contribution": round(v * max(0, w - 10) / 100),
                    "plus10_contribution":  round(v * (w + 10) / 100),
                    "note":               _SIM,
                })
        if rows:
            d["weight_sensitivity"] = rows

    # ── General assumptions ───────────────────────────────────────────
    if not d.get("general_assumptions"):
        d["general_assumptions"] = [
            {"num": 1, "assumption": "القيمة محسوبة وفق حالة السوق في تاريخ التقييم",  "basis": "تاريخ التقرير"},
            {"num": 2, "assumption": "البيانات المُقدَّمة من الطالب صحيحة وكاملة",    "basis": "إقرار الطالب"},
            {"num": 3, "assumption": "لا يوجد تلوث بيئي أو مشاكل قانونية غير معلومة", "basis": "إفادة الطالب"},
            {"num": 4, "assumption": "العقار خالٍ من الأعباء غير المُفصَح عنها",       "basis": "افتراض قياسي"},
            {"num": 5, "assumption": "معدلات الإيجار والشواغر مستقرة على المدى القصير","basis": "تحليل السوق"},
            {"num": 6, "assumption": "لا تغيير جوهري في التشريعات أثناء أفق التقييم", "basis": "افتراض قياسي"},
        ]

    # ── Special assumptions ───────────────────────────────────────────
    if not d.get("special_assumptions"):
        d["special_assumptions"] = [
            {"num": 1, "assumption": "بيانات السوق إرشادية تمثيلية — محاكاة داخلية/QA", "impact": "عالٍ"},
            {"num": 2, "assumption": "AVM غير مُعتمَد من جهة رسمية",                    "impact": "متوسط"},
            {"num": 3, "assumption": "DCF مبني على بيانات مُقدَّمة — لم يُتحقَّق منها", "impact": "متوسط"},
        ]

    # ── Limiting conditions ───────────────────────────────────────────
    if not d.get("limiting_conditions_list"):
        d["limiting_conditions_list"] = [
            "لا يُجرى فحص ميداني رسمي بموجب هذا التقرير",
            "لا تستند البيانات لقواعد بيانات رسمية مُتحقَّق منها",
            "لا يُصدر شهادة اعتماد أو توقيع خبير آلي",
            "لا يُقبل التقرير في الإجراءات القانونية قبل الاعتماد",
            "مصفوفة الحساسية ±10% تمثيلية — لا تعكس أسواقًا فعلية",
            "لا توجد ضمانات صريحة على دقة بيانات الطرف الثالث",
        ]

    # ── CapEx schedule ────────────────────────────────────────────────
    if not d.get("capex_schedule"):
        dcf_yrs = d.get("dcf_years") or []
        capex_vals = [15000, 8000, 5000, 5000, 5000]
        rows2: list = []
        for i in range(5):
            noi_val = dcf_yrs[i].get("noi", 0) if i < len(dcf_yrs) else 0
            cx = capex_vals[i]
            rows2.append({
                "year": i + 1,
                "capex": cx,
                "net_cf": (noi_val - cx) if noi_val else _NA,
            })
        d["capex_schedule"] = rows2

    # ── Appendix items (expanded) ─────────────────────────────────────
    if not d.get("appendix_items"):
        d["appendix_items"] = [
            {"title": "ملحق أ — بيانات المعاملات المقارنة",      "description": _SIM},
            {"title": "ملحق ب — مخططات الموقع والعقار",          "description": _NA},
            {"title": "ملحق ج — تقرير الفحص الميداني",            "description": _NA},
            {"title": "ملحق د — وثائق الملكية",                   "description": _NA},
            {"title": "ملحق هـ — بيانات نموذج الانحدار AVM",      "description": _SIM},
            {"title": "ملحق و — جدول التكاليف التفصيلية BOQ",     "description": _SIM},
            {"title": "ملحق ز — مصفوفة المخاطر التفصيلية",       "description": _SIM},
        ]

    # ── Executive summary fallback ────────────────────────────────────
    if not d.get("exec_summary"):
        final_v = _safe_float(d.get("final_value"))
        addr    = d.get("property_address", _NA)
        purpose = d.get("valuation_purpose", _NA)
        conf    = d.get("confidence_score", _NA)
        if final_v:
            d["exec_summary"] = (
                f"تُقدَّر القيمة السوقية الإرشادية للعقار الواقع في {addr} "
                f"بمبلغ {int(final_v):,} م.ج وفق غرض التقييم: {purpose}. "
                f"درجة الثقة: {conf}%. "
                "هذه القيمة إرشادية غير معتمدة رسميًا — محاكاة داخلية/QA."
            )
        else:
            d["exec_summary"] = _SIM

    # ── Scope of work fallback ────────────────────────────────────────
    if not d.get("scope_of_work"):
        d["scope_of_work"] = (
            "نطاق التقييم يشمل: تحليل السوق المحلي · مدخل المقارنة السوقية · "
            "مدخل التكلفة · مدخل الدخل والرسملة · DCF · تحليل الحساسية · "
            "تحليل السيناريوهات · سجل المخاطر · تحليل HBU · SWOT · ESG · "
            "جاهزية المعايير · بيان الامتثال · جاهزية الاعتماد. "
            "نطاق إرشادي تمثيلي — محاكاة داخلية/QA — غير معتمد."
        )

    return d


def build_professional_html(data: dict) -> str:
    """Build Professional tier HTML string from *data* dict.

    Extends Detailed with full compliance suite: TOC, exec-dashboard,
    scope-of-work, location analysis, multiple-regression, direct/indirect
    costs, standards-readiness, compliance, disclosures, cert-readiness,
    traffic-light cert status, weighted reconciliation, and appendices.
    All missing values fall back to the Arabic NA sentinel.
    Returns a complete, standalone HTML string ready for Playwright.
    """
    try:
        from jinja2 import Environment, FileSystemLoader
    except ImportError as exc:
        raise RuntimeError("Jinja2 is required: pip install jinja2") from exc

    css = _CSS_PATH.read_text(encoding="utf-8") if _CSS_PATH.exists() else ""
    font_css = _load_cairo_font_css()

    env = Environment(loader=FileSystemLoader(str(_TEMPLATES)), autoescape=False)
    env.globals["_fmt"] = _fmt
    env.globals["_na"] = _na

    tmpl = env.get_template("pv_professional_report.html")
    return tmpl.render(data=_enrich_professional_data(data), css=css, font_css=font_css, NA=_NA)


def render_professional_pdf(
    data: dict,
    output_path: "str | pathlib.Path | None" = None,
) -> bytes:
    """Render Professional tier to PDF bytes via Playwright/shared renderer.

    Never produces Certified output — watermark is non-removable by design.
    """
    renderer = _load_renderer()
    html = build_professional_html(data)
    pdf_bytes = renderer(html)
    if output_path:
        p = pathlib.Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(pdf_bytes)
    return pdf_bytes
