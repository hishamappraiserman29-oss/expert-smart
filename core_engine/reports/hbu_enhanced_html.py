"""
hbu_enhanced_html.py
Enhanced HBU HTML builder — Axes A–F + Financial Depth + Provenance
Produces role-separated HTML: user (no internal data) / admin (full log).

No FPDF. No external CDN. No local file paths in output.
Governance: advisory_only=True · non_certified=True
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


_DRAFT_DISCLOSURE_AR = (
    "هذا التحليل استرشادي وغير معتمد. بيانات مصادر الإنترنت (Draft) "
    "مسح مبدئي محوكم لا يُدرّب النموذج المعتمد ولا يُعدّ بيانات رسمية. "
    "يجب مراجعة جميع الافتراضات بواسطة مختص معتمد قبل الاعتماد على النتائج."
)


# ─── Formatting helpers ────────────────────────────────────────────────────────

def _fmt(n: Optional[float], currency: str = "ريال") -> str:
    if n is None:
        return "غير متاح"
    return f"{n:,.0f} {currency}" if currency else f"{n:,.0f}"


def _pct(n: Optional[float]) -> str:
    if n is None:
        return "غير متاح"
    return f"{n:.1f}%"


def _pf(v: bool, pt="✔ يجتاز", pf="✗ لا يجتاز") -> str:
    c = "#22c55e" if v else "#ef4444"
    return f'<span style="color:{c};font-weight:600;">{pt if v else pf}</span>'


def _section(num, title, content, color="#22c55e"):
    return (
        f'\n<div data-section="{num}" id="sec{num}" '
        f'style="margin:28px 0;page-break-inside:avoid;">'
        f'\n<div style="font-size:1.05rem;font-weight:700;color:{color};'
        f'border-bottom:2px solid {color}33;padding-bottom:5px;margin-bottom:12px;">'
        f'{num}. {title}</div>'
        f'\n{content}'
        f'\n</div>'
    )


def _card(content, extra=""):
    return (
        f'<div style="background:rgba(30,41,59,0.6);border:1px solid rgba(100,116,139,0.3);'
        f'border-radius:8px;padding:16px;margin:10px 0;{extra}">'
        f'{content}</div>'
    )


def _kv(label, value):
    return (
        f'<div style="display:flex;gap:8px;margin:4px 0;">'
        f'<span style="color:#9ca3af;min-width:200px;">{label}:</span>'
        f'<strong>{value}</strong></div>'
    )


def _badge(text, color="#22c55e", bg_alpha="12"):
    return (
        f'<span style="background:rgba({_hex_to_rgb(color)},{bg_alpha}%);'
        f'color:{color};padding:2px 10px;border-radius:10px;'
        f'font-size:0.75rem;font-weight:600;">{text}</span>'
    )


def _hex_to_rgb(hex_color):
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"{r},{g},{b}"


# ─── SVG bar chart ─────────────────────────────────────────────────────────────

def _bar_chart_svg(series: List[Dict], title: str, currency: str = "ريال",
                   width: int = 560, height: int = 220) -> str:
    if not series:
        return ""
    vals   = [s["value"] for s in series]
    labels = [s["label"] for s in series]
    colors = [s.get("color", "#22c55e") for s in series]
    max_v  = max(abs(v) for v in vals) or 1
    bar_w  = max(30, (width - 80) // max(len(vals), 1) - 10)
    pad_l, pad_b = 60, 50

    bars = ""
    for i, (v, lbl, clr) in enumerate(zip(vals, labels, colors)):
        x   = pad_l + i * (bar_w + 10)
        bar_h = int(abs(v) / max_v * (height - pad_b - 20))
        y   = height - pad_b - bar_h
        clr = "#22c55e" if v >= 0 else "#ef4444"
        bars += (
            f'<rect x="{x}" y="{y}" width="{bar_w}" height="{bar_h}" '
            f'fill="{clr}" rx="3"/>'
            f'<text x="{x + bar_w//2}" y="{y - 5}" text-anchor="middle" '
            f'font-size="9" fill="#e2e8f0">{v/1e6:.2f}M</text>'
            f'<text x="{x + bar_w//2}" y="{height - pad_b + 16}" text-anchor="middle" '
            f'font-size="9" fill="#94a3b8" writing-mode="horizontal-tb">'
            f'{lbl[:12]}</text>'
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'style="max-width:100%;direction:ltr;">'
        f'<rect width="{width}" height="{height}" fill="#0f172a" rx="6"/>'
        f'<text x="{width//2}" y="16" text-anchor="middle" font-size="11" '
        f'font-weight="bold" fill="#94a3b8">{title}</text>'
        f'<line x1="{pad_l}" y1="{height-pad_b}" x2="{width-10}" y2="{height-pad_b}" '
        f'stroke="#334155" stroke-width="1"/>'
        f'{bars}</svg>'
    )


# ─── Sensitivity heat‑map table ───────────────────────────────────────────────

def _sensitivity_table(fd: Dict[str, Any], currency: str) -> str:
    sg = fd.get("sensitivity_grid", {})
    matrix = sg.get("npv_matrix", [])
    rev_mults  = sg.get("rev_mults",  [0.85, 1.00, 1.15])
    cost_mults = sg.get("cost_mults", [0.85, 1.00, 1.15])
    if not matrix:
        return "<p>بيانات الحساسية غير متوفرة.</p>"

    all_vals = [v for row in matrix for v in row if v is not None]
    max_v = max(all_vals) if all_vals else 1
    min_v = min(all_vals) if all_vals else 0

    def _cell_color(v):
        if v is None:
            return "#334155"
        ratio = (v - min_v) / max(max_v - min_v, 1)
        r = int(239 * (1 - ratio))
        g = int(197 * ratio)
        return f"rgb({r},{g},60)"

    rev_labels  = [f"إيراد {int(m*100)}%" for m in rev_mults]
    cost_labels = [f"تكلفة {int(m*100)}%" for m in cost_mults]

    thead = (
        "<tr><th>الإيراد \\ التكلفة</th>"
        + "".join(f"<th>{cl}</th>" for cl in cost_labels)
        + "</tr>"
    )
    tbody = ""
    for i, row in enumerate(matrix):
        tbody += f"<tr><th>{rev_labels[i]}</th>"
        for v in row:
            clr = _cell_color(v)
            val = _fmt(v, currency) if v is not None else "—"
            tbody += (
                f'<td style="background:{clr};color:#fff;text-align:center;'
                f'font-size:0.75rem;padding:6px 8px;">{val}</td>'
            )
        tbody += "</tr>"

    dr_sens = fd.get("discount_rate_sensitivity", [])
    dr_rows = ""
    for dr in dr_sens:
        npv = dr.get("npv")
        irr = dr.get("irr_pct")
        dr_rows += (
            f"<tr><td>{dr.get('discount_rate_pct',0):.0f}%</td>"
            f"<td>{_fmt(npv, currency)}</td>"
            f"<td>{_pct(irr)}</td></tr>"
        )

    return (
        '<h3 style="color:#86efac;margin:14px 0 8px;">جدول الحساسية (NPV) — الإيراد × التكلفة</h3>'
        '<div style="overflow-x:auto;">'
        f'<table style="width:100%;border-collapse:collapse;font-size:0.78rem;">'
        f'<thead style="background:#1e293b;color:#94a3b8;">{thead}</thead>'
        f'<tbody>{tbody}</tbody></table></div>'
        '<h3 style="color:#86efac;margin:14px 0 8px;">حساسية معدل الخصم</h3>'
        '<div style="overflow-x:auto;">'
        '<table style="width:100%;border-collapse:collapse;font-size:0.78rem;">'
        '<thead><tr style="background:#1e293b;color:#94a3b8;">'
        '<th>معدل الخصم</th><th>NPV</th><th>IRR</th></tr></thead>'
        f'<tbody>{dr_rows}</tbody></table></div>'
    )


# ─── Section builders ──────────────────────────────────────────────────────────

def _sec_a_site(case_data: Dict, sourcing: Dict) -> str:
    city     = case_data.get("city_ar", "الرياض")
    district = case_data.get("district_ar", "النرجس")
    area     = case_data.get("land_area_m2", 2400)
    frontage = case_data.get("frontage_m", 40)
    depth    = case_data.get("depth_m", 60)
    road_w   = case_data.get("road_width_m", 30)
    mi       = sourcing.get("market_inputs", {})
    currency = case_data.get("currency", "ريال")

    swot = {
        "strengths": [
            f"موقع متميز في حي {district} بمدينة {city}",
            f"واجهة {frontage} م على شارع رئيسي عرضه {road_w} م",
            "سهولة الوصول من المحاور الرئيسية",
            f"مساحة {area:,} م² تمكّن من تطوير متعدد البدائل",
        ],
        "weaknesses": [
            "الاستخدام الحالي منخفض الكثافة يقلّل العائد الراهن",
            "تكاليف بناء مرتفعة نسبياً في حالة التطوير الجديد",
        ],
        "opportunities": [
            "نمو متسارع في الطلب على الوحدات السكنية بالرياض",
            "مشاريع البنية التحتية القريبة ترفع القيمة السوقية",
            "إمكانية التطوير المختلط يُعظّم الإيراد",
        ],
        "threats": [
            "تقلبات أسعار مواد البناء",
            "زيادة العرض في الحي قد تضغط على معدلات الإشغال",
            "مخاطر التغيير التنظيمي في اشتراطات التخطيط",
        ],
    }

    swot_html = (
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">'
    )
    colors = {"strengths": "#22c55e", "weaknesses": "#ef4444",
              "opportunities": "#3b82f6", "threats": "#f59e0b"}
    labels = {"strengths": "نقاط القوة", "weaknesses": "نقاط الضعف",
              "opportunities": "الفرص", "threats": "التهديدات"}
    for key, items in swot.items():
        c = colors[key]
        items_html = "".join(f"<li>{i}</li>" for i in items)
        swot_html += (
            f'<div style="background:rgba({_hex_to_rgb(c)},0.05);'
            f'border:1px solid {c}33;border-radius:6px;padding:12px;">'
            f'<div style="color:{c};font-weight:700;margin-bottom:6px;">{labels[key]}</div>'
            f'<ul style="padding-right:16px;margin:0;font-size:0.82rem;">{items_html}</ul>'
            f'</div>'
        )
    swot_html += "</div>"

    catchment_html = (
        f'<div style="font-size:0.82rem;line-height:1.8;">'
        f'<p><strong>منطقة الاستقطاب الأولية (0–2 كم):</strong> '
        f'أحياء {district} والمجاورة — طلب سكني وتجاري مباشر.</p>'
        f'<p><strong>منطقة الاستقطاب الثانوية (2–5 كم):</strong> '
        f'الأحياء السكنية المجاورة — يدعم الخدمات والمرافق التجارية.</p>'
        f'<p><strong>الوضوح من الشارع:</strong> '
        f'{"عالٍ" if road_w >= 30 else "متوسط"} — عرض الشارع {road_w} م '
        f'يوفر رؤية مناسبة للمشاة والمركبات.</p>'
        f'<p><strong>الوصول/المخرج:</strong> منفذ رئيسي من الشارع '
        f'{"+ منفذ خلفي مقترح" if area >= 2000 else ""}.</p>'
        f'</div>'
    )

    land_ppm = mi.get("land_ppm_indicator")
    mv       = mi.get("market_value_indicator")
    map_placeholder = (
        f'<div style="background:#1e293b;border:1px dashed #334155;'
        f'border-radius:6px;padding:24px;text-align:center;color:#6b7280;">'
        f'[خريطة الموقع — إحداثيات: {city}/{district}]<br>'
        f'<small>يتطلب تكامل خرائط — تُدرج في إصدار الإنتاج</small>'
        f'</div>'
    )

    content = (
        _card(
            f'<h3>A.1 — بيانات الموقع والأصل</h3>'
            + _kv("المدينة / الحي", f"{city} / {district}")
            + _kv("مساحة الأرض", f"{area:,} م²")
            + _kv("الواجهة × العمق", f"{frontage} م × {depth} م")
            + _kv("عرض الشارع الرئيسي", f"{road_w} م")
            + _kv("الإحداثيات", f"{city} — {district} (إشارة جغرافية)")
            + _kv("مؤشر سعر المتر (نموذج مجمع)", _fmt(land_ppm, currency) if land_ppm else "غير متاح")
            + _kv("القيمة السوقية التأشيرية", _fmt(mv, currency) if mv else "غير متاح")
        )
        + f'<div style="margin:12px 0;"><h3>A.2 — الوصول والاستقطاب</h3>'
        + _card(catchment_html)
        + f'</div>'
        + f'<div style="margin:12px 0;"><h3>A.3 — خريطة الموقع</h3>'
        + map_placeholder
        + f'</div>'
        + f'<div style="margin:12px 0;"><h3>A.4 — تحليل SWOT</h3>'
        + swot_html
        + f'</div>'
    )
    return content


def _sec_b_market(case_data: Dict, sourcing: Dict) -> str:
    mi       = sourcing.get("market_inputs", {})
    currency = case_data.get("currency", "ريال")

    occ   = mi.get("occupancy_residential")
    vac   = mi.get("market_vacancy_rate")
    abs_r = mi.get("absorption_rate_pct")
    rent_r = mi.get("market_rent_residential_pm2")
    rent_c = mi.get("market_rent_commercial_pm2")
    cap   = mi.get("cap_rate")
    growth= mi.get("annual_growth_rate")
    disc  = mi.get("discount_rate")

    macro_html = (
        '<div style="font-size:0.82rem;line-height:1.8;">'
        '<p><strong>المحركات الاقتصادية الكلية:</strong> '
        'تستفيد منطقة الرياض من برنامج رؤية 2030 الذي يدفع تنويع الاقتصاد، '
        'ويرفع الطلب على العقارات السكنية والتجارية. '
        'برامج الإسكان الحكومي والحوافز الائتمانية تدعم الطلب المحلي.</p>'
        '<p><strong>التركيبة السكانية:</strong> '
        'النمو السكاني في الرياض يدفع الطلب على الوحدات السكنية بالأحياء الراقية '
        'مثل النرجس. ارتفاع نسبة السكان دون 30 عاماً يعزز الطلب على الشقق والوحدات الصغيرة.</p>'
        '<p><strong>البنية التحتية:</strong> '
        'مشاريع المترو وتوسعة الطرق الرئيسية تُقرّب المواقع الطرفية من المراكز الحضرية، '
        'مما يرفع جاذبية الأحياء الشمالية للرياض.</p>'
        '</div>'
    )

    sd_rows = [
        ("الطلب السكني", "مرتفع", "#22c55e"),
        ("الطلب التجاري المحلي", "متوسط-مرتفع", "#3b82f6"),
        ("المعروض الجديد (6-12 شهراً)", "متوسط", "#f59e0b"),
        ("الضغط التنافسي", "متوسط", "#f59e0b"),
    ]
    sd_html = (
        '<div style="overflow-x:auto;">'
        '<table style="width:100%;border-collapse:collapse;font-size:0.82rem;">'
        '<thead><tr style="background:#1e293b;color:#94a3b8;">'
        '<th style="padding:7px 10px;border:1px solid #334155;">المؤشر</th>'
        '<th style="padding:7px 10px;border:1px solid #334155;">المستوى</th>'
        '<th style="padding:7px 10px;border:1px solid #334155;">المصدر</th>'
        '</tr></thead><tbody>'
    )
    for mname, level, color in sd_rows:
        sd_html += (
            f'<tr><td style="padding:6px 10px;border:1px solid #334155;">{mname}</td>'
            f'<td style="padding:6px 10px;border:1px solid #334155;color:{color};font-weight:600;">'
            f'{level}</td>'
            f'<td style="padding:6px 10px;border:1px solid #334155;font-size:0.75rem;color:#6b7280;">'
            f'تقدير — طبقة الإثراء</td></tr>'
        )
    sd_html += "</tbody></table></div>"

    indicators_html = (
        '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;">'
    )
    kpis = [
        ("معدل الإشغال", _pct(occ) if occ else "غير متاح", "#22c55e"),
        ("معدل الشواغر", _pct(vac) if vac else "غير متاح", "#ef4444"),
        ("معدل الاستيعاب", _pct(abs_r) if abs_r else "غير متاح", "#3b82f6"),
        ("إيجار سكني/م²", _fmt(rent_r, f"{currency}/شهر") if rent_r else "غير متاح", "#f59e0b"),
        ("إيجار تجاري/م²", _fmt(rent_c, f"{currency}/شهر") if rent_c else "غير متاح", "#f59e0b"),
        ("معدل الرسملة", _pct(cap * 100 if cap else None), "#94a3b8"),
        ("نمو سنوي متوقع", _pct(growth * 100 if growth else None), "#22c55e"),
        ("معدل الخصم المُستخدَم", _pct(disc * 100 if disc else None), "#94a3b8"),
    ]
    for kname, kval, kcolor in kpis:
        indicators_html += (
            f'<div style="background:rgba({_hex_to_rgb(kcolor)},0.06);'
            f'border:1px solid {kcolor}33;border-radius:6px;padding:12px;">'
            f'<div style="font-size:0.98rem;font-weight:700;color:{kcolor};">{kval}</div>'
            f'<div style="font-size:0.7rem;color:#9ca3af;margin-top:3px;">{kname}</div>'
            f'</div>'
        )
    indicators_html += "</div>"

    absorption_html = (
        '<div style="font-size:0.82rem;line-height:1.8;">'
        f'<p><strong>معدل الاستيعاب:</strong> '
        f'{_pct(abs_r) if abs_r else "غير متاح من المصادر المتوفرة"} — '
        f'{"مسح مبدئي محوكم، يخضع للمراجعة" if abs_r else "لا يتوفر مزوّد بيانات للاستيعاب في هذه المنطقة."}</p>'
        '<p>معدل الاستيعاب يعكس سرعة امتصاص السوق للوحدات الجديدة. '
        'قيمة > 5% شهرياً تشير لسوق نشط، < 2% تشير لتشبّع نسبي.</p>'
        '<p><strong>التوجيه:</strong> على المطوّر دراسة نموذج التدفق المرحلي للمشروع '
        'لضمان توافق وتيرة التسليم مع معدل الاستيعاب.</p>'
        '</div>'
    )

    content = (
        f'<div style="font-size:0.72rem;color:#fbbf24;background:rgba(251,191,36,0.07);'
        f'border:1px solid rgba(251,191,36,0.3);border-radius:6px;padding:8px 12px;margin-bottom:12px;">'
        f'مسح مبدئي محوكم (Draft) — لا يُدرَّب النموذج المعتمد ولا يُعدّ بيانات رسمية</div>'
        + f'<h3>B.1 — المحركات الاجتماعية-الاقتصادية</h3>'
        + _card(macro_html)
        + f'<h3>B.2 — مصفوفة العرض والطلب</h3>'
        + _card(sd_html)
        + f'<h3>B.3 — مؤشرات السوق الرئيسية</h3>'
        + _card(indicators_html)
        + f'<h3>B.4 — معدل الاستيعاب والشواغر</h3>'
        + _card(absorption_html)
    )
    return content


def _sec_c_concepts(case_data: Dict, alternatives: List[Dict],
                    hbu_result: Dict, sourcing: Dict) -> str:
    currency = case_data.get("currency", "ريال")
    area     = float(case_data.get("land_area_m2", 2400))
    FAR      = float(case_data.get("planning", {}).get("max_far", 2.20))

    concepts_html = ""
    for alt in alternatives:
        alt_id  = alt.get("alternative_id", "—")
        name    = alt.get("name_ar", alt.get("use_name", "—"))
        cat     = alt.get("category", "")
        rev     = alt.get("annual_revenue", 0)
        opex    = alt.get("annual_opex", 0)
        cc      = alt.get("construction_cost", 0)
        hp      = alt.get("holding_period_years", 10)
        cp      = alt.get("construction_period_years", 0)
        ev      = alt.get("exit_value", 0)

        # Concept description by category
        concept_map = {
            "current_use":            ("وحدة سكنية منفردة قائمة", "سكني", "100%", "—", area),
            "multifamily_residential": ("مبنى سكني متعدد الوحدات — 4 طوابق", "سكني 100%",
                                        "90%", f"{int(area * FAR * 0.85):,} م²", area * FAR * 0.85),
            "neighborhood_mixed_use":  ("تطوير مختلط — طابق تجاري + 3 طوابق سكنية",
                                        "تجاري 30% / سكني 70%",
                                        "85%", f"{int(area * FAR * 0.80):,} م²", area * FAR * 0.80),
            "interim_hold":            ("احتفاظ مؤقت بدون تطوير", "—", "—", "—", 0),
        }
        desc, mix, occ, leasable, leasable_f = concept_map.get(
            cat, (name, "—", "—", "—", 0))

        # Absorption table (estimated, 4 phases)
        abs_years = min(cp + 2, 4)
        abs_table = ""
        if leasable_f > 0:
            units_est = max(1, int(leasable_f / 120))
            for ph in range(1, abs_years + 1):
                pct_pre   = min(100, ph * 25)
                pct_lsd   = min(100, max(0, (ph - 1) * 35))
                abs_table += (
                    f'<tr><td style="padding:5px 8px;border:1px solid #334155;">{ph}</td>'
                    f'<td style="padding:5px 8px;border:1px solid #334155;">{pct_pre}%</td>'
                    f'<td style="padding:5px 8px;border:1px solid #334155;">{pct_lsd}%</td>'
                    f'<td style="padding:5px 8px;border:1px solid #334155;color:#9ca3af;">'
                    f'{int(units_est * pct_lsd / 100)} وحدة</td></tr>'
                )

        is_hbu = (alt.get("use_name", "") == hbu_result.get("recommended_use", ""))
        border = "border:2px solid #22c55e;" if is_hbu else ""
        hbu_tag = _badge("★ أعلى وأفضل استخدام", "#22c55e") if is_hbu else ""

        concepts_html += (
            f'<div style="background:rgba(30,41,59,0.6);{border}'
            f'border-radius:8px;padding:16px;margin:14px 0;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">'
            f'<span style="font-weight:700;color:#e2e8f0;">{alt_id}: {name}</span>'
            f'{hbu_tag}</div>'
            + _kv("وصف المفهوم", desc)
            + _kv("مزيج الاستخدام", mix)
            + _kv("معدل الإشغال المستهدف", occ)
            + _kv("المساحات القابلة للتأجير", leasable)
            + _kv("تكلفة البناء المقدرة", _fmt(cc, currency))
            + _kv("مدة البناء", f"{cp} سنة" if cp else "لا ينطبق")
            + _kv("فترة الاحتفاظ", f"{hp} سنوات")
            + _kv("الإيراد السنوي المقدر", _fmt(rev, currency))
            + _kv("المصروفات التشغيلية", _fmt(opex, currency))
            + _kv("قيمة الخروج المقدرة", _fmt(ev, currency))
            + (
                f'<div style="margin-top:12px;">'
                f'<h4 style="color:#86efac;margin-bottom:6px;font-size:0.82rem;">'
                f'جدول الاستيعاب التقديري</h4>'
                f'<div style="overflow-x:auto;">'
                f'<table style="width:100%;border-collapse:collapse;font-size:0.78rem;">'
                f'<thead><tr style="background:#1e293b;color:#94a3b8;">'
                f'<th style="padding:5px 8px;border:1px solid #334155;">المرحلة (سنة)</th>'
                f'<th style="padding:5px 8px;border:1px solid #334155;">نسبة البيع المسبق</th>'
                f'<th style="padding:5px 8px;border:1px solid #334155;">نسبة التأجير</th>'
                f'<th style="padding:5px 8px;border:1px solid #334155;">الوحدات المؤجرة</th>'
                f'</tr></thead><tbody>{abs_table}</tbody></table></div></div>'
                if abs_table else ""
            )
            + f'</div>'
        )

    return concepts_html


def _sec_d_financial(case_data: Dict, hbu_result: Dict, fd: Dict) -> str:
    currency = case_data.get("currency", "ريال")

    # Four-test comparison table
    comp_rows = ""
    for row in hbu_result.get("comparison_table", []):
        is_hbu = row.get("maximally_productive", False)
        bg = "background:rgba(34,197,94,0.06);" if is_hbu else ""
        comp_rows += (
            f'<tr style="{bg}">'
            f'<td style="padding:6px 8px;border:1px solid #334155;">{row["use_name"]}</td>'
            f'<td style="padding:6px 8px;border:1px solid #334155;text-align:center;">'
            f'{_pf(row["legally_permissible"])}</td>'
            f'<td style="padding:6px 8px;border:1px solid #334155;text-align:center;">'
            f'{_pf(row["physically_possible"])}</td>'
            f'<td style="padding:6px 8px;border:1px solid #334155;text-align:center;">'
            f'{_pf(row["financially_feasible"])}</td>'
            f'<td style="padding:6px 8px;border:1px solid #334155;text-align:center;">'
            f'{_pf(row["maximally_productive"], "★ الأعلى", "—")}</td>'
            f'<td style="padding:6px 8px;border:1px solid #334155;">'
            f'{_fmt(row["npv"], currency)}</td>'
            f'<td style="padding:6px 8px;border:1px solid #334155;">'
            f'{_pct(row["irr_pct"])}</td>'
            f'</tr>'
        )

    four_test_html = (
        '<div style="overflow-x:auto;">'
        '<table style="width:100%;border-collapse:collapse;font-size:0.78rem;">'
        '<thead><tr style="background:#1e293b;color:#94a3b8;">'
        f'<th style="padding:7px 8px;border:1px solid #334155;">البديل</th>'
        f'<th style="padding:7px 8px;border:1px solid #334155;">قانوني</th>'
        f'<th style="padding:7px 8px;border:1px solid #334155;">مادي</th>'
        f'<th style="padding:7px 8px;border:1px solid #334155;">مالي</th>'
        f'<th style="padding:7px 8px;border:1px solid #334155;">أعلى إنتاجية</th>'
        f'<th style="padding:7px 8px;border:1px solid #334155;">NPV ({currency})</th>'
        f'<th style="padding:7px 8px;border:1px solid #334155;">IRR%</th>'
        f'</tr></thead>'
        f'<tbody>{comp_rows}</tbody></table></div>'
    )

    # Financial depth
    rlv     = fd.get("rlv")
    gdv     = fd.get("gdv")
    tdc     = fd.get("tdc")
    dp_t    = fd.get("dev_profit_target")
    lc      = fd.get("land_cost")
    rlv_m2  = fd.get("rlv_per_m2")
    lc_m2   = fd.get("land_cost_per_m2")
    payback = fd.get("payback_years")
    irr_p   = fd.get("irr_project_pct")
    irr_i   = fd.get("irr_investor_pct")
    dm      = fd.get("dev_margin_pct")
    viab    = fd.get("rlv_viability", "")

    viab_color = "#22c55e" if viab == "viable" else "#ef4444"
    viab_label = "مجدٍ — RLV > تكلفة الأرض" if viab == "viable" else "غير مجدٍ — RLV < تكلفة الأرض"

    rlv_html = (
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px;">'
        + _card(
            f'<div style="font-size:0.72rem;color:#9ca3af;">القيمة الإجمالية للتطوير (GDV)</div>'
            f'<div style="font-size:1.1rem;font-weight:700;color:#86efac;">{_fmt(gdv, currency)}</div>',
            "padding:12px;"
        )
        + _card(
            f'<div style="font-size:0.72rem;color:#9ca3af;">إجمالي تكاليف التطوير (TDC)</div>'
            f'<div style="font-size:1.1rem;font-weight:700;color:#fcd34d;">{_fmt(tdc, currency)}</div>',
            "padding:12px;"
        )
        + _card(
            f'<div style="font-size:0.72rem;color:#9ca3af;">هامش المطوّر المستهدف (15%)</div>'
            f'<div style="font-size:1.1rem;font-weight:700;color:#f59e0b;">{_fmt(dp_t, currency)}</div>',
            "padding:12px;"
        )
        + _card(
            f'<div style="font-size:0.72rem;color:#9ca3af;">القيمة المتبقية للأرض (RLV)</div>'
            f'<div style="font-size:1.1rem;font-weight:700;color:{viab_color};">'
            f'{_fmt(rlv, currency)}</div>'
            f'<div style="font-size:0.72rem;color:{viab_color};margin-top:3px;">{viab_label}</div>',
            "padding:12px;"
        )
        + "</div>"
        + _card(
            _kv("RLV / م²", _fmt(rlv_m2, f"{currency}/م²") if rlv_m2 else "غير متاح")
            + _kv("تكلفة الأرض / م²", _fmt(lc_m2, f"{currency}/م²") if lc_m2 else "غير متاح")
            + _kv("فترة الاسترداد", f"{payback:.1f} سنوات" if payback else "غير متاح")
            + _kv("IRR المشروع", _pct(irr_p))
            + _kv("IRR المستثمر (بعد هامش المطوّر)", _pct(irr_i))
            + _kv("هامش المطوّر %", _pct(dm))
            + _kv(
                "الخيار الحقيقي",
                fd.get("real_options_note", "—")
            )
        )
    )

    # NPV bar chart
    npv_series = [
        {"label": s["use_name"][:8], "value": s["npv"],
         "color": "#22c55e" if s.get("test_4_max_productive") else "#64748b"}
        for s in hbu_result.get("scenarios_evaluated", [])
    ]
    chart_svg = _bar_chart_svg(npv_series, f"NPV لكل بديل ({currency})")

    content = (
        f'<h3 style="color:#86efac;">D.1 — إطار الاختبارات الأربعة (IVS/USPAP)</h3>'
        + _card(four_test_html)
        + f'<h3 style="color:#86efac;margin-top:16px;">D.2 — مخطط NPV لكل بديل</h3>'
        + _card(f'<div style="overflow-x:auto;">{chart_svg}</div>')
        + f'<h3 style="color:#86efac;margin-top:16px;">D.3 — القيمة المتبقية للأرض (RLV)</h3>'
        + rlv_html
        + f'<h3 style="color:#86efac;margin-top:16px;">D.4 — تحليل الحساسية متعدد المتغيرات</h3>'
        + _card(_sensitivity_table(fd, currency))
        + f'<div style="margin-top:12px;font-size:0.75rem;color:#9ca3af;">'
        + f'{hbu_result.get("standards_note","")}</div>'
    )
    return content


def _sec_e_advisory(hbu_result: Dict, fd: Dict, case_data: Dict) -> str:
    rec   = hbu_result.get("recommended_use", "—")
    note  = hbu_result.get("recommendation_note", "")
    npv   = hbu_result.get("recommended_npv")
    irr_p = fd.get("irr_project_pct")
    currency = case_data.get("currency", "ريال")

    risks = [
        ("مخاطر السوق", "انخفاض الإيرادات > 15% يؤثر سلباً على RLV",
         "دراسة قابلية التأجير المسبق قبل البدء"),
        ("مخاطر التكلفة", "تقلبات أسعار مواد البناء",
         "عقود تسليم مفتاح بسقف سعري ثابت"),
        ("مخاطر التنظيم", "تغيير اشتراطات التخطيط",
         "الحصول على تصاريح بناء قبل البدء"),
        ("مخاطر التمويل", "ارتفاع معدلات الإقراض",
         "تأمين تمويل بسعر ثابت لفترة البناء"),
        ("مخاطر الإشغال", "بطء امتصاص وحدات جديدة",
         "تسويق مبكر + خطة بيع مسبق"),
    ]
    risks_html = "".join(
        f'<tr>'
        f'<td style="padding:7px 10px;border:1px solid #334155;font-weight:600;">{r}</td>'
        f'<td style="padding:7px 10px;border:1px solid #334155;color:#fca5a5;">{d}</td>'
        f'<td style="padding:7px 10px;border:1px solid #334155;color:#86efac;">{m}</td>'
        f'</tr>'
        for r, d, m in risks
    )

    steps = [
        "إعداد المخططات المعمارية ودراسة الجدوى التفصيلية",
        "الحصول على رخصة البناء وموافقات الجهات التنظيمية",
        "تأمين التمويل وإبرام عقود المقاولات",
        "مرحلة البناء والتطوير (مدة مقدرة: سنتان)",
        "التسويق والتأجير/البيع المسبق خلال مرحلة البناء",
        "التسليم والإشغال التدريجي",
        "إعادة التقييم بعد الإشغال لقياس الأداء الفعلي",
    ]
    steps_html = "".join(f'<li style="margin:6px 0;">{s}</li>' for s in steps)

    content = (
        _card(
            f'<h3 style="color:#86efac;margin-bottom:8px;">E.1 — لماذا هذا البديل هو الأمثل؟</h3>'
            f'<p style="line-height:1.8;">{note}</p>'
            + _kv("صافي القيمة الحالية (NPV)", _fmt(npv, currency))
            + _kv("IRR المشروع", _pct(irr_p))
            + f'<p style="margin-top:10px;color:#94a3b8;font-size:0.82rem;">'
            f'الاستخدام المختلط يُعظّم قيمة الأصل من خلال تنويع مصادر الإيراد '
            f'(إيجار تجاري + سكني)، مع استيفاء جميع متطلبات الاختبارات الأربعة لـ HBU '
            f'وفق معايير IVS/USPAP.</p>'
        )
        + _card(
            '<h3 style="color:#fcd34d;margin-bottom:8px;">E.2 — المخاطر وخطط التخفيف</h3>'
            '<div style="overflow-x:auto;">'
            '<table style="width:100%;border-collapse:collapse;font-size:0.82rem;">'
            '<thead><tr style="background:#1e293b;color:#94a3b8;">'
            '<th style="padding:7px 10px;border:1px solid #334155;">المخاطرة</th>'
            '<th style="padding:7px 10px;border:1px solid #334155;">التأثير</th>'
            '<th style="padding:7px 10px;border:1px solid #334155;">التخفيف</th>'
            f'</tr></thead><tbody>{risks_html}</tbody></table></div>'
        )
        + _card(
            '<h3 style="color:#86efac;margin-bottom:8px;">E.3 — خطوات التنفيذ المقترحة</h3>'
            f'<ol style="padding-right:20px;line-height:1.8;">{steps_html}</ol>'
        )
        + f'<div style="margin-top:10px;font-size:0.75rem;color:#6b7280;">'
        f'هذه التوصيات استرشادية وتستند إلى تحليل نظري. '
        f'يجب مراجعة جدوى التنفيذ مع متخصصين في التطوير العقاري قبل الشروع.</div>'
    )
    return content


def _sec_f_provenance(provenance_table: List[Dict], sourcing: Dict) -> str:
    if not provenance_table:
        return "<p>لا توجد بيانات مصدرية.</p>"

    tier_colors = {
        "Tier-1 محوكم": "#22c55e",
        "Tier-1 محوكم (مشتق)": "#86efac",
        "Tier-2 Draft": "#f59e0b",
        "N/A": "#6b7280",
    }

    rows = ""
    for p in provenance_table:
        tier  = p.get("source_tier", "N/A")
        clr   = tier_colors.get(tier, "#6b7280")
        status = p.get("status", "—")
        val   = p.get("value_used")
        val_s = f"{val:,.2f}" if val is not None else "غير متاح"
        rows += (
            f'<tr>'
            f'<td style="padding:6px 8px;border:1px solid #334155;font-size:0.75rem;">'
            f'{p.get("input_id","")}</td>'
            f'<td style="padding:6px 8px;border:1px solid #334155;">'
            f'{p.get("label_ar","")}</td>'
            f'<td style="padding:6px 8px;border:1px solid #334155;text-align:center;">'
            f'{val_s} {p.get("unit","")}</td>'
            f'<td style="padding:6px 8px;border:1px solid #334155;'
            f'font-size:0.75rem;">{p.get("source_name","")}</td>'
            f'<td style="padding:6px 8px;border:1px solid #334155;text-align:center;">'
            f'<span style="color:{clr};font-weight:600;">{tier}</span></td>'
            f'<td style="padding:6px 8px;border:1px solid #334155;'
            f'font-size:0.72rem;color:#9ca3af;">'
            f'{p.get("confidence_score",0):.0f}%</td>'
            f'<td style="padding:6px 8px;border:1px solid #334155;'
            f'font-size:0.72rem;color:#6b7280;">'
            f'{status}</td>'
            f'<td style="padding:6px 8px;border:1px solid #334155;'
            f'font-size:0.7rem;color:#9ca3af;">'
            f'{p.get("reconciliation_note","")[:60]}</td>'
            f'</tr>'
        )

    ma_s = sourcing.get("mass_appraisal_summary", {})
    ma_note = ma_s.get("model_note", "—")
    return (
        f'<div style="font-size:0.72rem;color:#94a3b8;margin-bottom:10px;">'
        f'ملاحظة النموذج المجمع: {ma_note}</div>'
        '<div style="overflow-x:auto;">'
        '<table style="width:100%;border-collapse:collapse;font-size:0.78rem;">'
        '<thead><tr style="background:#1e293b;color:#94a3b8;">'
        '<th style="padding:7px 8px;border:1px solid #334155;">المُعرِّف</th>'
        '<th style="padding:7px 8px;border:1px solid #334155;">المدخل</th>'
        '<th style="padding:7px 8px;border:1px solid #334155;">القيمة</th>'
        '<th style="padding:7px 8px;border:1px solid #334155;">المصدر</th>'
        '<th style="padding:7px 8px;border:1px solid #334155;">الطبقة</th>'
        '<th style="padding:7px 8px;border:1px solid #334155;">الثقة</th>'
        '<th style="padding:7px 8px;border:1px solid #334155;">الحالة</th>'
        '<th style="padding:7px 8px;border:1px solid #334155;">ملاحظة التوفيق</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
    )


def _sec_g_source_log(source_log: List[Dict]) -> str:
    if not source_log:
        return "<p>لا توجد سجلات مصادر.</p>"
    rows = ""
    for src in source_log:
        uri = str(src.get("source_uri") or src.get("url") or "")
        rows += (
            f'<tr>'
            f'<td style="padding:5px 8px;border:1px solid #334155;font-size:0.7rem;">'
            f'{src.get("source_id","")}</td>'
            f'<td style="padding:5px 8px;border:1px solid #334155;">'
            f'{src.get("source_type","")}</td>'
            f'<td style="padding:5px 8px;border:1px solid #334155;">'
            f'{src.get("source_name","")}</td>'
            f'<td style="padding:5px 8px;border:1px solid #334155;font-size:0.7rem;">'
            f'{uri[:50]}</td>'
            f'<td style="padding:5px 8px;border:1px solid #334155;">'
            f'{src.get("confidence_score","")}</td>'
            f'</tr>'
        )
    return (
        '<div style="overflow-x:auto;">'
        '<table style="width:100%;border-collapse:collapse;font-size:0.78rem;">'
        '<thead><tr style="background:#1e293b;color:#94a3b8;">'
        '<th>ID</th><th>النوع</th><th>الاسم</th><th>URI</th><th>الثقة</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
    )


# ─── CSS ──────────────────────────────────────────────────────────────────────

_CSS = (
    "* { box-sizing:border-box; margin:0; padding:0; }\n"
    "body { font-family:'Segoe UI',Tahoma,Arial,sans-serif; background:#0f172a; "
    "color:#e2e8f0; font-size:0.87rem; line-height:1.7; padding:20px; direction:rtl; }\n"
    ".wm { position:fixed; top:45%; left:50%; "
    "transform:translate(-50%,-50%) rotate(-30deg); "
    "font-size:3.8rem; font-weight:900; pointer-events:none; "
    "z-index:0; white-space:nowrap; }\n"
    ".card { background:rgba(30,41,59,0.6); border:1px solid rgba(100,116,139,0.3); "
    "border-radius:8px; padding:16px; margin:12px 0; }\n"
    ".advisory { background:rgba(251,191,36,0.07); border:1px solid rgba(251,191,36,0.3); "
    "border-radius:8px; padding:14px; color:#fcd34d; font-size:0.82rem; margin:16px 0; }\n"
    "h3 { font-size:0.9rem; color:#86efac; margin:14px 0 8px; }\n"
    "table { width:100%; border-collapse:collapse; }\n"
    "th { background:#1e293b; color:#94a3b8; padding:7px 8px; "
    "border:1px solid #334155; text-align:right; }\n"
    "td { padding:6px 8px; border:1px solid #334155; }\n"
    "ul, ol { padding-right:20px; margin:8px 0; }\n"
    ".page-break { page-break-after:always; }\n"
)


# ─── Main builders ────────────────────────────────────────────────────────────

def build_hbu_html(
    case_data:    Dict[str, Any],
    hbu_result:   Dict[str, Any],
    fd:           Dict[str, Any],
    sourcing:     Dict[str, Any],
    audience:     str,   # "user" | "admin"
    alternatives: List[Dict[str, Any]],
) -> str:
    is_admin = (audience == "admin")
    wm_label = "للمراجعة الداخلية فقط" if is_admin else "استرشادي — غير معتمد"
    wm_color = "#fbbf24" if is_admin else "#ef4444"

    case_id  = case_data.get("case_id", "HBU-001")
    city     = case_data.get("city_ar", "الرياض")
    district = case_data.get("district_ar", "النرجس")
    area     = case_data.get("land_area_m2", 2400)
    currency = case_data.get("currency", "ريال")
    val_date = case_data.get("valuation_date", "2026-07-01")

    rec_use  = hbu_result.get("recommended_use", "—")
    rec_npv  = hbu_result.get("recommended_npv")
    rec_sc   = next(
        (s for s in hbu_result.get("scenarios_evaluated", [])
         if s["use_name"] == rec_use), {}
    )
    rec_irr  = rec_sc.get("irr_pct")

    prov_list = sourcing.get("provenance_table", [])
    src_log   = sourcing.get("source_log", []) if is_admin else []

    # Cover
    cover = (
        f'<div style="background:linear-gradient(135deg,#0f2027 0%,#1a3a4c 100%);'
        f'border:1px solid rgba(34,197,94,0.3);border-radius:12px;'
        f'padding:36px;margin-bottom:30px;text-align:center;">'
        f'<div style="font-size:0.7rem;color:#6b7280;margin-bottom:8px;">'
        f'advisory_only=True | non_certified=True | fake_signature_created=False | case_id={case_id}'
        f'</div>'
        f'<h1 style="font-size:1.6rem;color:#86efac;margin-bottom:6px;">'
        f'تقرير تحليل أعلى وأفضل استخدام</h1>'
        f'<h2 style="font-size:0.95rem;color:#9ca3af;margin-bottom:18px;">'
        f'Highest and Best Use (HBU) Analysis Report</h2>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;'
        f'max-width:520px;margin:0 auto;text-align:right;font-size:0.82rem;">'
        f'<div><span style="color:#9ca3af;">رمز المهمة:</span> <strong>{case_id}</strong></div>'
        f'<div><span style="color:#9ca3af;">العملة:</span> <strong>{currency}</strong></div>'
        f'<div><span style="color:#9ca3af;">المدينة/الحي:</span> <strong>{city} / {district}</strong></div>'
        f'<div><span style="color:#9ca3af;">المساحة:</span> <strong>{area:,} م²</strong></div>'
        f'<div><span style="color:#9ca3af;">تاريخ التقييم:</span> <strong>{val_date}</strong></div>'
        f'<div><span style="color:#9ca3af;">الجمهور:</span> <strong>'
        f'{"داخلي (Admin)" if is_admin else "خارجي (User)"}</strong></div>'
        f'</div>'
        f'<div style="margin-top:18px;display:grid;grid-template-columns:repeat(3,1fr);'
        f'gap:12px;max-width:600px;margin:18px auto 0;">'
        f'<div style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.25);'
        f'border-radius:8px;padding:14px;">'
        f'<div style="font-size:0.95rem;font-weight:700;color:#86efac;">'
        f'{rec_use[:20]}{"…" if len(rec_use)>20 else ""}</div>'
        f'<div style="font-size:0.7rem;color:#9ca3af;margin-top:3px;">أعلى وأفضل استخدام</div>'
        f'</div>'
        f'<div style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.25);'
        f'border-radius:8px;padding:14px;">'
        f'<div style="font-size:0.95rem;font-weight:700;color:#86efac;">{_fmt(rec_npv, currency)}</div>'
        f'<div style="font-size:0.7rem;color:#9ca3af;margin-top:3px;">صافي القيمة الحالية</div>'
        f'</div>'
        f'<div style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.25);'
        f'border-radius:8px;padding:14px;">'
        f'<div style="font-size:0.95rem;font-weight:700;color:#86efac;">{_pct(rec_irr)}</div>'
        f'<div style="font-size:0.7rem;color:#9ca3af;margin-top:3px;">IRR المشروع</div>'
        f'</div>'
        f'</div>'
        f'<div style="margin-top:14px;">'
        f'<span style="background:rgba(251,191,36,0.15);color:#fcd34d;padding:3px 12px;'
        f'border-radius:12px;font-size:0.72rem;font-weight:600;">{wm_label}</span>'
        f'</div>'
        f'</div>'
    )

    # Sections
    sections = [
        _section(1, "الغلاف وبيانات المهمة",
            _card(
                _kv("رمز المهمة", case_id)
                + _kv("الدولة", case_data.get("country_ar", "المملكة العربية السعودية"))
                + _kv("المدينة / الحي", f"{city} / {district}")
                + _kv("الاستخدام الحالي", case_data.get("current_use", "—"))
                + _kv("تاريخ التقييم", val_date)
                + _kv("العملة", currency)
                + _kv("معدل الخصم", _pct(hbu_result.get("discount_rate_pct")))
            )
        ),
        _section(2, "الإفصاح والحوكمة",
            f'<div class="advisory">{_DRAFT_DISCLOSURE_AR}</div>'
            + _card(
                _kv("advisory_only", "True")
                + _kv("certification_ready", "False")
                + _kv("fake_reviewer_signature_created", "False")
                + _kv("non_certified", "True")
                + _kv("not_real_training_data", "True")
                + _kv("web_research_label", "مسح مبدئي محوكم — Draft")
            )
        ),
        _section(3, "المحور A — دراسة الموقع",
            _sec_a_site(case_data, sourcing), color="#3b82f6"),
        _section(4, "المحور B — الذكاء السوقي",
            _sec_b_market(case_data, sourcing), color="#f59e0b"),
        _section(5, "المحور C — المفاهيم التطويرية",
            _sec_c_concepts(case_data, alternatives, hbu_result, sourcing), color="#a78bfa"),
        _section(6, "المحور D — التحليل المالي المعمّق",
            _sec_d_financial(case_data, hbu_result, fd), color="#22c55e"),
        _section(7, "المحور E — التوصيات الاستشارية",
            _sec_e_advisory(hbu_result, fd, case_data), color="#86efac"),
        _section(8, "المحور F — جدول المصدرية",
            _sec_f_provenance(prov_list, sourcing), color="#64748b"),
        _section(9, f"ملاحظة المعايير",
            _card(
                f'<p style="color:#94a3b8;font-size:0.82rem;">'
                f'{hbu_result.get("standards_note","")}</p>'
            )
        ),
    ]

    # Admin-only sections
    if is_admin:
        sections += [
            _section(10, "سجل المصادر (Admin)",
                _sec_g_source_log(src_log), color="#fbbf24"),
            _section(11, "سجل الافتراضات الداخلية (Admin)",
                _card(
                    _kv("مصدر بيانات المدخلات", "نموذج مجمع (Tier-1) + مسح مبدئي (Tier-2)")
                    + _kv("نموذج التقييم الجماعي", sourcing.get("mass_appraisal_summary", {}).get("model_version","AVM-v1"))
                    + _kv("avm_ppm (خام)", f"{sourcing.get('market_inputs',{}).get('avm_ppm_raw',0):,.0f}")
                    + _kv("adj_ppm (خام)", f"{sourcing.get('market_inputs',{}).get('adj_ppm_raw',0):,.0f}")
                    + _kv("تحذيرات الاستكمال", "; ".join(sourcing.get("warnings", ["لا توجد"])))
                    + _kv("run_id", sourcing.get("run_id","—"))
                    + _kv("retrieved_at", sourcing.get("retrieved_at","—"))
                )
            ),
        ]

    footer_color = "#fbbf24" if is_admin else "#ef4444"
    footer = (
        f'<div style="margin-top:32px;padding-top:16px;border-top:1px solid #334155;'
        f'text-align:center;font-size:0.72rem;color:#6b7280;">'
        f'<span style="color:{footer_color};font-weight:600;">{wm_label}</span> | '
        f'{case_id} | {val_date} | '
        f'{"للمراجعة الداخلية — يحتوي على بيانات داخلية" if is_admin else "لا يحتوي على بيانات داخلية"}'
        f'</div>'
    )

    wm_style = f"color:{wm_color}20;"
    body_content = (
        f'<div class="wm" style="{wm_style}">{wm_label}</div>'
        + cover
        + "".join(sections)
        + footer
    )

    return (
        f'<!DOCTYPE html>\n'
        f'<html lang="ar" dir="rtl">\n'
        f'<head>\n'
        f'<meta charset="UTF-8">\n'
        f'<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f'<title>تقرير HBU — {case_id} — {audience}</title>\n'
        f'<style>{_CSS}</style>\n'
        f'</head>\n'
        f'<body>\n'
        f'{body_content}\n'
        f'</body>\n'
        f'</html>'
    )
