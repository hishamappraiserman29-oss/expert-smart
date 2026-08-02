"""
hbu_report_sections.py
======================
أقسام HBU المطوّرة (المحاور A–E) — تُغلق فجوات تحليل الفجوات المعتمد:
  A) دراسة الموقع (دخول/خروج · وضوح/جاذبية · استقطاب · SWOT)
  B) تحليل السوق والاستيعاب (سعر المتر/المقارنات/الإيجار/الرسملة/الشغور + عرض/طلب + استيعاب)
  C) المفاهيم التطويرية والاستيعاب (لكل بديل: مكوّنات + مساحة بناء + استيعاب)
  D) العمق المالي (RLV/استرداد/هامش مطوّر/عائد مستثمر + حساسية محسوبة) + جدول المصدرية (أدمن)
  E) التوصيات الاستشارية السردية (لماذا الأمثل · مخاطر/تخفيف · خطوات تنفيذ)

Library-only migration component.

This module is not wired to a route, report pipeline, or frontend.
The canonical active HBU renderer remains
core_engine/reports/hbu_enhanced_report.py.

Future integration or replacement of canonical rendering requires
a separate architecture approval gate (post-Wave 1C).

Runtime status  : INACTIVE_LIBRARY
Wiring status   : LIBRARY_ONLY_UNWIRED
Code quality    : PRODUCTION_HARDENED
Canonical renderer: core_engine/reports/hbu_enhanced_report.py
Source-of-truth changed: False

Pipeline position (informational — not enforced here):
  Wave 1B  hbu_inputs_bridge.build_hbu_inputs()
      populates result["market_inputs"]
  HBU engine  hbu_analysis_engine.run_hbu_analysis()
      produces scenarios_evaluated, recommended_use, etc.
  Wave 1A  hbu_financial_depth.enhance_hbu_financials()
      adds result["financial_depth"] and per-scenario residual_land_value
  Wave 1C  build_enhanced_sections()  -- this module (render only)

المبدأ: هذه الوحدة تُنتج HTML فقط — لا تستورد أي طبقة upstream.

Governance:
  advisory_only      = True
  certification_ready = False
"""
from __future__ import annotations

import html as _html
from typing import Any, Callable, Dict, List, Optional

# ── Type aliases ─────────────────────────────────────────────────────────────
SectionFn = Callable[..., str]
FmtFn = Callable[[Optional[float]], str]

# ── Module-level governance constants ────────────────────────────────────────
_advisory_only: bool = True
_certification_ready: bool = False
_ADVISORY_DISCLAIMER = (
    "هذه الأقسام استرشادية فقط، ولا تُعدّ شهادة تقييم، "
    "أو تقريرًا نهائيًا، أو إثباتًا قانونيًا لجواز الاستخدام."
)

# ── RLV methodology identifiers ───────────────────────────────────────────────
#
# Section C (scenario-level):
#   The canonical HBU engine (hbu_analysis_engine._evaluate_scenario) does NOT
#   produce residual_land_value.  A value found at sc["residual_land_value"] may
#   arrive from Wave 1A enhance_hbu_financials or any other enrichment path.
#   Its producer is confirmed ONLY when the scenario carries explicit provenance:
#     sc["rlv_method_id"] == "NPV_IDENTITY_RLV"
#   Otherwise a neutral label is used; Wave 1A is never assumed by default.
#
# Section D (financial_depth):
#   result["financial_depth"]["residual_land_value"] is produced exclusively by
#   hbu_financial_depth.enhance_hbu_financials (Wave 1A), formula RLV = NPV +
#   land_cost.  The NPV-identity label is verified and always used for Section D.

_RLV_METHOD_ID_NPV_IDENTITY = "NPV_IDENTITY_RLV"
_RLV_METHOD_WAVE1A          = "هوية NPV (Wave 1A)"

# Section C labels — chosen at render time based on per-scenario provenance
_RLV_LABEL_SCENARIO_NPV_IDENTITY = (
    "القيمة المتبقية للأرض لكل سيناريو — " + _RLV_METHOD_WAVE1A
)
_RLV_LABEL_SCENARIO_NEUTRAL = (
    "القيمة المتبقية للأرض لكل سيناريو — المنهج غير موثق"
)
_RLV_LABEL_SCENARIO_UNAVAILABLE = (
    "غير متاح — محرك HBU لا ينتج RLV على مستوى السيناريو، ويلزم إثراء مالي موثق."
)

# Section D labels — verified Wave 1A producer; constant
_RLV_LABEL_OPTIMAL = "القيمة المتبقية للأرض — " + _RLV_METHOD_WAVE1A
_RLV_LABEL_PER_M2  = "RLV لكل م² — " + _RLV_METHOD_WAVE1A


# ════════════════════════════════════════════════════════════════════════════
#  Centralized escaping helper
# ════════════════════════════════════════════════════════════════════════════

def _esc(value: Any) -> str:
    """Escape any value for safe HTML text or attribute insertion."""
    return _html.escape("" if value is None else str(value), quote=True)


# ════════════════════════════════════════════════════════════════════════════
#  Private helpers
# ════════════════════════════════════════════════════════════════════════════

def _src_badge(status: str) -> str:
    """
    Return an HTML badge span for the given source status.

    Security note: `status` is compared for equality only and is NEVER
    interpolated into the returned HTML. Unknown statuses map to the fixed
    'unavailable' badge. This function is safe without further escaping.
    """
    if status == "approved_internal":
        return (
            '<span style="background:rgba(34,197,94,0.15);color:#86efac;'
            'padding:1px 8px;border-radius:4px;font-size:0.68rem;">'
            'مصدر: التقييم الجماعي (مُعتمَد داخلي)</span>'
        )
    if status == "draft_pending_review":
        return (
            '<span style="background:rgba(251,191,36,0.15);color:#fcd34d;'
            'padding:1px 8px;border-radius:4px;font-size:0.68rem;">'
            'مسح مبدئي محوكم — Draft</span>'
        )
    return (
        '<span style="background:rgba(148,163,184,0.15);color:#cbd5e1;'
        'padding:1px 8px;border-radius:4px;font-size:0.68rem;">غير متاح</span>'
    )


def _inp(mi: Dict[str, Any], key: str) -> Optional[Dict[str, Any]]:
    return (mi.get("inputs") or {}).get(key)


def _val_row(label: str, entry: Optional[Dict[str, Any]], fmt_currency: FmtFn) -> str:
    """Render one market-indicator table row with full HTML escaping."""
    safe_label = _esc(label)
    if not entry:
        return (
            f'<tr><td>{safe_label}</td><td>غير متاح</td>'
            f'<td>{_src_badge("unavailable")}</td><td>—</td></tr>'
        )
    v = entry.get("value")
    unit = entry.get("unit", "")
    if isinstance(v, list):
        vs = " – ".join(f"{x:,.0f}" for x in v if isinstance(x, (int, float)))
    elif isinstance(v, (int, float)):
        vs = f"{v:,.0f}"
    else:
        vs = _esc(str(v) if v is not None else "")
    safe_unit = _esc(unit)
    conf = entry.get("confidence")
    conf_s = f"{conf:.0f}%" if isinstance(conf, (int, float)) else "—"
    return (
        f'<tr><td>{safe_label}</td>'
        f'<td><bdi dir="ltr">{vs}</bdi> {safe_unit}</td>'
        f'<td>{_src_badge(entry.get("status", ""))}</td>'
        f'<td>ثقة {_esc(conf_s)}</td></tr>'
    )


# ════════════════════════════════════════════════════════════════════════════
#  A) دراسة الموقع
# ════════════════════════════════════════════════════════════════════════════

def _section_location(site: Dict[str, Any], section_html: SectionFn, synth: str) -> str:
    area_raw     = site.get("land_area")
    frontage_raw = site.get("frontage")
    depth_raw    = site.get("depth")
    road_raw     = site.get("road_width")

    # Physical dimensions: None or <= 0 are invalid for a development site
    area_valid     = isinstance(area_raw,     (int, float)) and area_raw     > 0
    frontage_valid = isinstance(frontage_raw, (int, float)) and frontage_raw > 0
    depth_valid    = isinstance(depth_raw,    (int, float)) and depth_raw    > 0
    road_valid     = isinstance(road_raw,     (int, float)) and road_raw     > 0

    area_txt     = f"{area_raw:,.0f} م²" if area_valid else "غير متاح"
    frontage_txt = str(int(frontage_raw)) if frontage_valid else "غير متاح"
    depth_txt    = str(int(depth_raw))    if depth_valid    else "غير متاح"

    if road_valid:
        road_f = float(road_raw)
        access_label  = "ممتاز" if road_f >= 25 else "جيد" if road_f >= 15 else "مقبول"
        road_txt       = f"{road_raw} م"
        road_dlalatah  = f"سهولة الدخول/الخروج: {access_label}"
        catchment_line = f"الدخول/الخروج: شارع بعرض {road_raw} م يتيح حركة مركبات."
    else:
        road_txt       = "غير متاح"
        road_dlalatah  = "عرض الشارع غير متاح — لا يمكن تقييم سهولة الدخول/الخروج"
        catchment_line = "عرض الشارع غير متاح — لا يمكن تقييم سهولة الدخول/الخروج."

    if frontage_valid and depth_valid:
        ratio = float(frontage_raw) / float(depth_raw)
        shape = "منتظم" if 0.5 <= ratio <= 2.0 else "غير منتظم"
        shape_cell = f"{frontage_txt} × {depth_txt} م"
    else:
        shape      = "غير محدد"
        shape_cell = f"{frontage_txt} × {depth_txt} م"

    visibility = (
        ("عالية" if float(frontage_raw) >= 30 else "متوسطة")
        if frontage_valid else "غير محدد"
    )
    swot_strength = (
        _esc(f"واجهة: {frontage_txt} م، شكل: {shape}")
        if frontage_valid else "بيانات الموقع غير مكتملة"
    )
    safe_synth = _esc(synth)

    content = (
        '<div style="overflow-x:auto">'
        '<div class="card" dir="rtl">'
        '<h3>خصائص الموقع المادية</h3>'
        '<table><thead><tr>'
        '<th scope="col">البند</th>'
        '<th scope="col">القيمة</th>'
        '<th scope="col">الدلالة</th>'
        '</tr></thead><tbody>'
        f'<tr><td>المساحة</td>'
        f'<td><bdi dir="ltr">{_esc(area_txt)}</bdi></td>'
        f'<td>كتلة تطويرية</td></tr>'
        f'<tr><td>الواجهة × العمق</td>'
        f'<td><bdi dir="ltr">{_esc(shape_cell)}</bdi></td>'
        f'<td>الشكل: {_esc(shape)}</td></tr>'
        f'<tr><td>عرض الشارع</td>'
        f'<td><bdi dir="ltr">{_esc(road_txt)}</bdi></td>'
        f'<td>{_esc(road_dlalatah)}</td></tr>'
        f'<tr><td>وضوح/جاذبية الواجهة</td>'
        f'<td>{_esc(visibility)}</td>'
        f'<td>ظهور بصري للاستخدام التجاري</td></tr>'
        '</tbody></table>'
        f'<div class="synth">{safe_synth}: تقييمات الجاذبية والاستقطاب استرشادية تُراجَع ميدانياً.</div>'
        '</div></div>'
        '<div style="overflow-x:auto">'
        '<div class="card" dir="rtl"><h3>تحليل الدخول والخروج والاستقطاب</h3><ul>'
        f'<li>{_esc(catchment_line)}</li>'
        '<li>المنطقة الخدمية (Catchment): نطاق سير قريب + نطاق مركبات ضمن الحي.</li>'
        '<li>الجاذبية: تُراجَع ميدانياً وفق الواجهة الفعلية.</li>'
        '</ul></div></div>'
        '<div style="overflow-x:auto">'
        '<div class="card" dir="rtl"><h3>تحليل SWOT للموقع</h3>'
        '<table><thead><tr>'
        '<th scope="col">قوة</th>'
        '<th scope="col">ضعف</th>'
        '<th scope="col">فرص</th>'
        '<th scope="col">تهديدات</th>'
        '</tr></thead><tbody>'
        f'<tr><td>{swot_strength}</td>'
        '<td>يحتاج دراسة سوق محلية موثقة</td>'
        '<td>يتطلب دراسة سوق لتحديد الطلب</td>'
        '<td>حساسية للتكلفة/معدل الخصم</td></tr>'
        '</tbody></table>'
        f'<div class="synth">{safe_synth}</div>'
        '</div></div>'
    )
    return section_html(
        "أ",
        "دراسة الموقع (الدخول/الخروج · الجاذبية · الاستقطاب · SWOT)",
        content,
        "#38bdf8",
    )


# ════════════════════════════════════════════════════════════════════════════
#  B) تحليل السوق والاستيعاب
# ════════════════════════════════════════════════════════════════════════════

def _section_market(
    mi: Dict[str, Any],
    section_html: SectionFn,
    fmt_currency: FmtFn,
    is_admin: bool,
    synth: str,
) -> str:
    rows = (
        _val_row("سعر المتر (تقديري)",       _inp(mi, "price_per_m2"),         fmt_currency)
        + _val_row("نطاق أسعار المقارنات",   _inp(mi, "comparable_ppm_range"), fmt_currency)
        + _val_row("الإيجار السنوي/م²",       _inp(mi, "rent_per_m2"),          fmt_currency)
        + _val_row("معدل الرسملة",            _inp(mi, "cap_rate_range"),        fmt_currency)
        + _val_row("نسبة الشغور",             _inp(mi, "market_vacancy_rate"),   fmt_currency)
    )

    unavailable = mi.get("unavailable") or []
    unav_html = ""
    if unavailable:
        items = "".join(
            f'<li>{_esc(u.get("input", ""))}: {_esc(u.get("reason", ""))}</li>'
            for u in unavailable
        )
        unav_html = (
            '<div style="overflow-x:auto">'
            '<div class="card" dir="rtl"><h3>مدخلات غير متاحة (لا تُلفَّق)</h3>'
            f'<ul>{items}</ul></div></div>'
        )

    prov = mi.get("mass_appraisal") or {}
    ratio = prov.get("ratio_study") or {}
    ratio_html = ""
    if ratio.get("n_sales", 0) > 0:
        ratio_html = (
            '<div class="synth">'
            f'جودة التقييم الجماعي (IAAO): COD={_esc(ratio.get("cod"))} · '
            f'PRD={_esc(ratio.get("prd"))} · التجانس: {_esc(ratio.get("uniformity"))}'
            '</div>'
        )

    # Supply/demand: conditional on evidence; no fabrication
    inputs_dict = mi.get("inputs") or {}
    ev_keys = ("price_per_m2", "comparable_ppm_range", "rent_per_m2")
    has_approved = any(
        (inputs_dict.get(k) or {}).get("status") == "approved_internal" for k in ev_keys
    )
    has_draft = any(
        (inputs_dict.get(k) or {}).get("status") == "draft_pending_review" for k in ev_keys
    )

    _no_evidence = (
        "لا تتوفر أدلة سوقية كافية لإصدار استنتاج عن العرض أو الطلب — "
        "يلزم إجراء دراسة سوق محلية موثقة."
    )

    if has_approved:
        demand_txt = "يُشير التقييم الجماعي المعتمد إلى طلب في المنطقة — راجع تقرير نسبة التقييم للتفاصيل."
        supply_txt = "راجع بيانات المقارنات المعتمدة لتقدير المعروض المنافس."
    elif has_draft:
        demand_txt = "بيانات مسودة (Draft) — تحتاج مراجعة خبير قبل الاستنتاج."
        supply_txt = "بيانات مسودة (Draft) — تحتاج مراجعة خبير قبل الاستنتاج."
    else:
        demand_txt = _no_evidence
        supply_txt = _no_evidence

    safe_synth = _esc(synth)

    content = (
        '<div style="overflow-x:auto">'
        '<div class="card" dir="rtl"><h3>مؤشّرات السوق (المصدر موسوم)</h3>'
        '<table><thead><tr>'
        '<th scope="col">المؤشّر</th>'
        '<th scope="col">القيمة</th>'
        '<th scope="col">المصدر</th>'
        '<th scope="col">الثقة</th>'
        '</tr></thead>'
        f'<tbody>{rows}</tbody></table>'
        f'{ratio_html}'
        '<div class="gov">الأولوية للمُعتمَد من التقييم الجماعي؛ بيانات الإثراء Draft لا تُعتمد إلا '
        'بمراجعة الخبير ولا تُدرّب النموذج المعتمد ولا تُقدَّم كبيانات رسمية.</div>'
        '</div></div>'
        + unav_html
        + '<div style="overflow-x:auto">'
        '<div class="card" dir="rtl"><h3>العرض والطلب والاستيعاب</h3>'
        '<table><thead><tr>'
        '<th scope="col">العنصر</th>'
        '<th scope="col">القراءة</th>'
        '</tr></thead><tbody>'
        f'<tr><td>الطلب</td><td>{_esc(demand_txt)}</td></tr>'
        f'<tr><td>العرض</td><td>{_esc(supply_txt)}</td></tr>'
        '<tr><td>الاستيعاب</td><td>تصريف تدريجي للوحدات على مدى فترة التشغيل '
        '(يُقدَّر لكل مفهوم في القسم ج)</td></tr>'
        '</tbody></table>'
        f'<div class="synth">{safe_synth}: قراءات العرض/الطلب استرشادية حتى توثيقها من مصادر معتمدة.</div>'
        '</div></div>'
    )
    return section_html(
        "ب",
        "تحليل السوق والاستيعاب (مؤشّرات موسومة المصدر)",
        content,
        "#38bdf8",
    )


# ════════════════════════════════════════════════════════════════════════════
#  C) المفاهيم التطويرية والاستيعاب
# ════════════════════════════════════════════════════════════════════════════

def _section_concepts(
    result: Dict[str, Any],
    planning: Dict[str, Any],
    land_area: float,
    section_html: SectionFn,
    fmt_currency: FmtFn,
    synth: str,
) -> str:
    far_raw = planning.get("max_far")
    if isinstance(far_raw, (int, float)) and far_raw > 0:
        far = float(far_raw)
        buildable = land_area * far if land_area > 0 else 0.0
        far_label = f"FAR {far}"
        buildable_txt = (
            f"{buildable:,.0f} م²" if land_area > 0
            else "غير متاح (مساحة الأرض غير محددة)"
        )
    else:
        far = 0.0
        buildable = 0.0
        far_label = "غير محدد"
        buildable_txt = "غير متاح (نسبة البناء غير محددة)"

    scenarios = result.get("scenarios_evaluated") or []
    safe_synth = _esc(synth)

    if not scenarios:
        cards = (
            '<div class="card" dir="rtl">'
            '<p class="synth">لا تتوفر سيناريوهات تطويرية محسوبة.</p>'
            '</div>'
        )
    else:
        cards = ""
        for sc in scenarios:
            rev = sc.get("annual_revenue")
            noi = sc.get("annual_noi")
            rlv = sc.get("residual_land_value")
            star = "★ " if sc.get("test_4_max_productive") else ""
            safe_name = _esc(sc.get("use_name") or "")
            rev_n = rev if isinstance(rev, (int, float)) else None
            noi_n = noi if isinstance(noi, (int, float)) else None
            absorb = (
                "تصريف تدريجي على فترة التشغيل حتى الاستقرار"
                if (isinstance(rev, (int, float)) and rev > 0 and buildable > 0)
                else "—"
            )
            # Scenario RLV label and display depend on per-scenario provenance.
            # The engine does not produce residual_land_value; Wave 1A attribution
            # requires explicit rlv_method_id == "NPV_IDENTITY_RLV".
            if rlv is None:
                rlv_label   = "القيمة المتبقية للأرض لكل سيناريو"
                rlv_display = _esc(_RLV_LABEL_SCENARIO_UNAVAILABLE)
            elif sc.get("rlv_method_id") == _RLV_METHOD_ID_NPV_IDENTITY:
                rlv_label   = _RLV_LABEL_SCENARIO_NPV_IDENTITY
                rlv_display = f'<bdi dir="ltr">{_esc(fmt_currency(rlv))}</bdi>'
            else:
                rlv_label   = _RLV_LABEL_SCENARIO_NEUTRAL
                rlv_display = f'<bdi dir="ltr">{_esc(fmt_currency(rlv))}</bdi>'
            cards += (
                '<div style="overflow-x:auto">'
                '<div class="card" dir="rtl">'
                f'<h3>{star}{safe_name}</h3>'
                '<table><tbody>'
                f'<tr><td>أقصى مسطح بناء ({_esc(far_label)})</td>'
                f'<td><bdi dir="ltr">{_esc(buildable_txt)}</bdi></td></tr>'
                f'<tr><td>الإيراد السنوي</td>'
                f'<td><bdi dir="ltr">{_esc(fmt_currency(rev_n))}</bdi></td></tr>'
                f'<tr><td>صافي الدخل التشغيلي</td>'
                f'<td><bdi dir="ltr">{_esc(fmt_currency(noi_n))}</bdi></td></tr>'
                f'<tr><td>{_esc(rlv_label)}</td>'
                f'<td>{rlv_display}</td></tr>'
                f'<tr><td>الاستيعاب السوقي</td>'
                f'<td>{_esc(absorb)}</td></tr>'
                '</tbody></table>'
                '</div></div>'
            )

    content = (
        cards
        + '<div class="card" dir="rtl">'
        f'<div class="synth">{safe_synth}: مكوّنات المفاهيم والاستيعاب استرشادية تُحدَّد تفصيلاً في مرحلة التصميم.</div>'
        '</div>'
    )
    return section_html(
        "ج", "المفاهيم التطويرية والاستيعاب السوقي", content, "#38bdf8"
    )


# ════════════════════════════════════════════════════════════════════════════
#  D) العمق المالي + جدول المصدرية (أدمن)
# ════════════════════════════════════════════════════════════════════════════

def _section_financial_depth(
    result: Dict[str, Any],
    section_html: SectionFn,
    fmt_currency: FmtFn,
    pct: FmtFn,
    is_admin: bool,
    synth: str,
) -> str:
    fd   = result.get("financial_depth") or {}
    sens = fd.get("sensitivity") or {}
    grid = sens.get("cost_revenue_grid") or []
    dm   = fd.get("developer_metrics") or {}
    eq   = fd.get("equity_irr") or {}
    safe_synth = _esc(synth)

    # ── Summary metrics ───────────────────────────────────────────────────
    # RLV (Wave 1A NPV identity). Distinguish None from zero.
    rlv_raw    = fd.get("residual_land_value")
    rlv_m2_raw = fd.get("rlv_per_m2")
    rlv_txt    = (
        f'<bdi dir="ltr">{_esc(fmt_currency(rlv_raw))}</bdi>'
        if rlv_raw is not None else "غير متاح"
    )
    rlv_m2_txt = (
        f'<bdi dir="ltr">{_esc(fmt_currency(rlv_m2_raw))}</bdi>'
        if rlv_m2_raw is not None else "غير متاح"
    )

    # Payback: None → unavailable; zero would be unusual but valid
    _pv = fd.get("payback_years")
    payback_txt = f"{_pv:.1f} سنة" if isinstance(_pv, (int, float)) else "غير متاح"

    # Developer margin: None → unavailable; zero (break-even) is valid
    _poc = dm.get("profit_on_cost_pct")
    poc_txt = f"{_poc}%" if isinstance(_poc, (int, float)) else "غير متاح"

    # Total investment: None → unavailable; zero would be unusual but valid
    _tot = dm.get("total_investment")
    tot_inv_txt = (
        f'<bdi dir="ltr">{_esc(fmt_currency(_tot))}</bdi>'
        if isinstance(_tot, (int, float)) else "غير متاح"
    )

    # Equity IRR: None → unavailable + escaped reason; numeric value → display
    _eqv = eq.get("value")
    _eqr = eq.get("reason", "يتطلب بنية تمويل")
    _eqa = eq.get("assumption")
    if isinstance(_eqv, (int, float)):
        eq_txt = f"{_eqv}%"
    else:
        eq_txt = f"غير متاح — {_esc(_eqr)}"

    synth_fin = (
        f'<div class="synth">{safe_synth}: افتراض التمويل ({_esc(_eqa)}).</div>'
        if _eqa else ""
    )

    summary = (
        '<div style="overflow-x:auto">'
        '<div class="card" dir="rtl"><h3>مقاييس العمق المالي للاستخدام الأمثل</h3>'
        '<table><tbody>'
        f'<tr><td>{_esc(_RLV_LABEL_OPTIMAL)}</td><td>{rlv_txt}</td></tr>'
        f'<tr><td>{_esc(_RLV_LABEL_PER_M2)}</td><td>{rlv_m2_txt}</td></tr>'
        f'<tr><td>فترة الاسترداد</td>'
        f'<td><bdi dir="ltr">{_esc(payback_txt)}</bdi></td></tr>'
        f'<tr><td>هامش الربح على التكلفة</td>'
        f'<td><bdi dir="ltr">{_esc(poc_txt)}</bdi></td></tr>'
        f'<tr><td>إجمالي الاستثمار</td><td>{tot_inv_txt}</td></tr>'
        f'<tr><td>عائد المستثمر (Equity IRR)</td>'
        f'<td><bdi dir="ltr">{eq_txt}</bdi></td></tr>'
        '</tbody></table>'
        + synth_fin
        + '</div></div>'
    )

    # ── Sensitivity grid ──────────────────────────────────────────────────
    if not grid:
        sens_html = (
            '<div class="card" dir="rtl"><h3>تحليل الحساسية (محسوب — NPV)</h3>'
            '<p class="synth">بيانات الحساسية غير متاحة — يتطلّب التحليل معدل خصم '
            'وتدفقات نقدية محسوبة.</p>'
            '</div>'
        )
    else:
        cost_deltas = sorted({c["cost_delta_pct"] for c in grid})
        rev_deltas  = sorted({c["revenue_delta_pct"] for c in grid})
        head = "".join(
            f'<th scope="col">إيراد {r:+d}%</th>' for r in rev_deltas
        )
        body = ""
        for cd in cost_deltas:
            cells = ""
            for rd in rev_deltas:
                cell = next(
                    (c for c in grid
                     if c["cost_delta_pct"] == cd and c["revenue_delta_pct"] == rd),
                    None,
                )
                npv      = cell["npv"]      if cell else None
                feasible = cell["feasible"] if cell else False
                color    = "#22c55e" if (npv is not None and npv > 0) else "#ef4444"
                feasibility_label = "مجدٍ" if feasible else "غير مجدٍ"
                cells += (
                    f'<td style="color:{color};">'
                    f'<bdi dir="ltr">{_esc(fmt_currency(npv))}</bdi>'
                    f'<br><small>{feasibility_label}</small>'
                    f'</td>'
                )
            body += f'<tr><td>تكلفة {cd:+d}%</td>{cells}</tr>'

        disc = sens.get("discount_sensitivity") or []
        if disc:
            disc_rows = ""
            for r in disc:
                dr_pct = r.get("discount_rate_pct")
                dr_txt = (
                    f"{dr_pct}%" if isinstance(dr_pct, (int, float))
                    else _esc(str(dr_pct))
                )
                disc_rows += (
                    f'<tr><td>خصم {dr_txt}</td>'
                    f'<td><bdi dir="ltr">{_esc(fmt_currency(r.get("npv")))}</bdi></td>'
                    f'<td>{"مجدٍ" if r.get("feasible") else "غير مجدٍ"}</td></tr>'
                )
            disc_section = (
                '<h3>حساسية معدل الخصم</h3>'
                '<div style="overflow-x:auto">'
                '<table><thead><tr>'
                '<th scope="col">معدل الخصم</th>'
                '<th scope="col">NPV</th>'
                '<th scope="col">الحكم</th>'
                '</tr></thead>'
                f'<tbody>{disc_rows}</tbody></table></div>'
            )
        else:
            disc_section = (
                '<p class="synth">بيانات حساسية معدل الخصم غير متاحة.</p>'
            )

        npv_min = sens.get("npv_min")
        npv_max = sens.get("npv_max")
        range_txt = (
            f'النطاق: <bdi dir="ltr">{_esc(fmt_currency(npv_min))}</bdi> … '
            f'<bdi dir="ltr">{_esc(fmt_currency(npv_max))}</bdi>'
            if npv_min is not None or npv_max is not None
            else "نطاق NPV غير متاح"
        )
        downside_txt = "نعم" if sens.get("downside_feasible") else "لا"

        sens_html = (
            '<div style="overflow-x:auto">'
            '<div class="card" dir="rtl"><h3>تحليل الحساسية (محسوب — NPV)</h3>'
            '<div style="overflow-x:auto">'
            f'<table><thead><tr><th scope="col">السيناريو</th>{head}</tr></thead>'
            f'<tbody>{body}</tbody></table></div>'
            + disc_section
            + f'<div class="synth">{range_txt} · مقاوم للهبوط: {downside_txt}</div>'
            '</div></div>'
        )

    # ── Provenance table — admin only ────────────────────────────────────
    prov_html = ""
    if is_admin:
        mi_inner = result.get("market_inputs") or {}
        prov     = mi_inner.get("provenance") or []
        prov_rows = ""
        for p in prov:
            val = p.get("value")
            if isinstance(val, list):
                vs = _esc(" – ".join(str(x) for x in val if x is not None))
            elif isinstance(val, (int, float)):
                vs = f"{val:,.0f}"
            else:
                vs = _esc(str(val) if val is not None else "—")
            prov_rows += (
                '<tr>'
                f'<td>{_esc(str(p.get("input") or ""))}</td>'
                f'<td><bdi dir="ltr">{vs}</bdi></td>'
                f'<td>{_esc(str(p.get("source_name") or ""))}</td>'
                f'<td>{_esc(str(p.get("tier") or ""))}</td>'
                f'<td>{_esc(str(p.get("status") or ""))}</td>'
                f'<td style="font-size:0.7rem;color:#9ca3af;">'
                f'{_esc(str(p.get("reconciliation_note") or "") or "—")}</td>'
                '</tr>'
            )
        gov = mi_inner.get("governance") or {}
        prov_html = (
            '<div style="overflow-x:auto">'
            '<div class="card" dir="rtl" style="border-color:rgba(251,191,36,0.3);">'
            '<h3>جدول المصدرية (Provenance) — للمراجعة الداخلية فقط</h3>'
            '<div style="overflow-x:auto">'
            '<table><thead><tr>'
            '<th scope="col">المُدخل</th>'
            '<th scope="col">القيمة</th>'
            '<th scope="col">المصدر</th>'
            '<th scope="col">الطبقة</th>'
            '<th scope="col">الحالة</th>'
            '<th scope="col">ملاحظة التوفيق</th>'
            '</tr></thead>'
            f'<tbody>{prov_rows}</tbody></table></div>'
            f'<div class="gov">'
            f'المصدر الأساسي: {_esc(str(gov.get("primary_source") or "-"))} · '
            f'حالة بيانات النت: {_esc(str(gov.get("web_data_status") or "-"))} · '
            f'الإثراء Draft: {_esc(str(gov.get("enrichment_is_draft") or "-"))} · '
            f'يُدرّب النموذج: {_esc(str(gov.get("web_trains_model") or "-"))}'
            '</div>'
            '</div></div>'
        )

    return section_html(
        "د",
        "العمق المالي (RLV · استرداد · حساسية محسوبة · عائد مستثمر)",
        summary + sens_html + prov_html,
        "#38bdf8",
    )


# ════════════════════════════════════════════════════════════════════════════
#  E) التوصيات الاستشارية السردية
# ════════════════════════════════════════════════════════════════════════════

def _section_recommendations(
    result: Dict[str, Any],
    section_html: SectionFn,
    fmt_currency: FmtFn,
    synth: str,
) -> str:
    rec  = result.get("recommended_use")
    npv  = result.get("recommended_npv")
    fd   = result.get("financial_depth") or {}
    sens = fd.get("sensitivity") or {}
    resilient = (
        "مقاوم لسيناريوهات الهبوط (تكلفة+/إيراد−)"
        if sens.get("downside_feasible")
        else "حسّاس لسيناريوهات الهبوط — يتطلب هامش أمان"
    )
    rlv_raw = fd.get("residual_land_value")
    rlv_display = (
        f'<bdi dir="ltr">{_esc(fmt_currency(rlv_raw))}</bdi>'
        if rlv_raw is not None else "غير متاح"
    )
    safe_synth = _esc(synth)

    if rec is not None:
        safe_rec = _esc(rec)
        npv_n    = npv if isinstance(npv, (int, float)) else None
        safe_npv = _esc(fmt_currency(npv_n))
        rec_html = (
            f'<p>الاستخدام الموصى به: '
            f'<strong style="color:#86efac;">{safe_rec}</strong> — '
            f'بأعلى صافي قيمة حالية (<bdi dir="ltr">{safe_npv}</bdi>) '
            f'واجتيازٍ للاختبارات الأربعة، '
            f'وبقيمة أرض متبقية {rlv_display}.</p>'
        )
    else:
        rec_html = (
            '<p>لا يوجد استخدام موصى به — لم يجتز أي سيناريو الاختبارات الأربعة. '
            'يُوصى بإعادة دراسة المعاملات أو افتراضات السوق.</p>'
        )

    content = (
        '<div class="card" dir="rtl"><h3>السيناريو المفضّل ومسوّغاته</h3>'
        + rec_html
        + f'<p>ملمح المخاطرة: {_esc(resilient)}.</p></div>'
        '<div style="overflow-x:auto">'
        '<div class="card" dir="rtl"><h3>المخاطر والتخفيف</h3>'
        '<table><thead><tr>'
        '<th scope="col">المخاطرة</th>'
        '<th scope="col">التخفيف</th>'
        '</tr></thead><tbody>'
        '<tr><td>ارتفاع تكاليف الإنشاء</td>'
        '<td>تثبيت عقود + احتياطي طوارئ + مراجعة الحساسية</td></tr>'
        '<tr><td>بطء الاستيعاب السوقي</td>'
        '<td>تسويق مبكر + مرونة مزيج الاستخدامات</td></tr>'
        '<tr><td>تغيّر معدل الخصم/التمويل</td>'
        '<td>هيكل تمويل متحفّظ + سيناريو خصم أعلى</td></tr>'
        '</tbody></table></div></div>'
        '<div class="card" dir="rtl"><h3>خطوات التنفيذ الموصى بها</h3><ul>'
        '<li>توثيق الاشتراطات النظامية الفعلية لدى جهات الترخيص.</li>'
        '<li>توثيق مؤشّرات السوق (إيجار/رسملة/شغور) من مصادر معتمدة بدل مدخلات Draft.</li>'
        '<li>تصميم أوّلي للمفهوم الأمثل + دراسة استيعاب تفصيلية.</li>'
        '<li>مراجعة خبير معتمد قبل أي اعتماد رسمي.</li>'
        '</ul></div>'
        f'<div class="synth">{safe_synth}: التوصيات استرشادية ولا تُعدّ شهادة تقييم أو قراراً نهائياً.</div>'
        f'<div class="gov">{_esc(_ADVISORY_DISCLAIMER)}</div>'
    )
    return section_html(
        "هـ",
        "التوصيات الاستشارية (المسوّغات · المخاطر · خطوات التنفيذ)",
        content,
        "#38bdf8",
    )


# ════════════════════════════════════════════════════════════════════════════
#  Public aggregator
# ════════════════════════════════════════════════════════════════════════════

def build_enhanced_sections(
    result: Dict[str, Any],
    *,
    is_admin: bool,
    section_html: SectionFn,
    fmt_currency: FmtFn,
    pct: FmtFn,
    site: Dict[str, Any],
    planning: Dict[str, Any],
    synth_label: str,
) -> str:
    """
    Build HBU report sections A-E as a joined HTML fragment.

    The provenance table in section D is shown only when is_admin is True.

    Callback contracts (callers must honour):
      section_html  -- trusted HTML wrapper; must NOT be constructed from
                       untrusted request data; its output is not escaped here.
      fmt_currency  -- returns PLAIN TEXT only (no HTML markup); output is
                       wrapped in _esc() before every HTML insertion.
      pct           -- returns PLAIN TEXT only; same escaping rule.
    """
    mi = result.get("market_inputs") or {}
    land_area_raw = site.get("land_area")
    land_area = (
        float(land_area_raw)
        if isinstance(land_area_raw, (int, float)) and land_area_raw > 0
        else 0.0
    )
    parts: List[str] = [
        _section_location(site, section_html, synth_label),
        _section_market(mi, section_html, fmt_currency, is_admin, synth_label),
        _section_concepts(result, planning, land_area, section_html, fmt_currency, synth_label),
        _section_financial_depth(result, section_html, fmt_currency, pct, is_admin, synth_label),
        _section_recommendations(result, section_html, fmt_currency, synth_label),
    ]
    return "\n<div class=\"page-break\"></div>\n".join(parts)
