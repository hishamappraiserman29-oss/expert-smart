"""
hbu_inputs_bridge.py
====================
HBU Inputs Sourcing Bridge — طبقة استكمال مدخلات موضوع التقييم لتقرير أعلى وأفضل استخدام (HBU).

الغرض
-----
استكمال المدخلات السوقية اللازمة لتقرير HBU من مصدرين بأولوية شفّافة وحوكمة صارمة:
  1) صفحة/محرّك التقييم الجماعي (mass_appraisal.run_mass_appraisal) — READ-ONLY —
     المصدر الداخلي الأساسي: سعر المتر (avg_ppm) · نطاق المقارنات · دراسة النسب IAAO.
  2) طبقة الإثراء السوقي المحوكمة (enrichment.MarketEnrichmentLayer) — Draft فقط —
     لسدّ ما لا يوفّره المجمع (الإيجار/معدل الرسملة/نسبة الشغور)؛ تبقى pending_human_review
     ولا تُعتمد ولا تُقدَّم كبيانات رسمية ولا تُدرّب النموذج المعتمد.

مبادئ حاكمة (مطبَّقة هنا — Governance Fixes Wave 1B)
---------------------------------------------------
  • READ-ONLY: نستدعي دوال المحرّكين فقط — لا نغيّر منطقهما إطلاقًا.
  • أولوية المصادر: المجمع (approved_internal) > الإثراء (draft_pending_review).
  • لا تلفيق: عند غياب المصدرين لمُدخل → يُسجَّل في unavailable مع السبب، بلا رقم وهمي.
  • كل مُدخل يحمل: القيمة · المصدر · الثقة · الطبقة · الحالة + ملاحظة توفيق (Provenance).
  • الإثراء بالـ opt-in فقط (enable_enrichment / enrichment_layer / use_mock_enrichment):
    Data Minimization — لا يُنشأ provider حقيقي بدون طلب صريح.
  • حارس الجغرافيا: المصادر المقيّدة بدولة مختلفة تُرسَل إلى unavailable لا inputs.
  • الثقة من الدليل لا الافتراض: من COD دراسة النسب IAAO؛ وإلا confidence=None + سبب.
  • تنظيف المؤقتات: الدليكتوري المؤقت (work_dir=None) يُنشأ ويُحذف داخل نفس الاستدعاء.
  • الـ Exceptions تنتشر كما هي — لا fallback وهمي ينبثق من خطأ.

هذه الوحدة إضافية بحتة — لا تمسّ hbu_analysis_engine ولا mass_appraisal ولا enrichment.
"""
from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, FrozenSet, List, Optional

# ── استيراد المحرّكات القائمة READ-ONLY ──────────────────────────────────────
try:  # pragma: no cover - import shim
    from mass_appraisal import run_mass_appraisal  # type: ignore
except ImportError:  # pragma: no cover
    from core_engine.mass_appraisal import run_mass_appraisal  # type: ignore

try:  # pragma: no cover - import shim
    from enrichment.market_enrichment import MarketEnrichmentLayer, build_request  # type: ignore
except ImportError:  # pragma: no cover
    from core_engine.enrichment.market_enrichment import (  # type: ignore
        MarketEnrichmentLayer,
        build_request,
    )

# مفردات الطبقة/الحالة (Provenance vocabulary)
TIER_INTERNAL_PRIMARY = "internal_primary"   # مُعتمَد من محرّك التقييم الجماعي
TIER_WEB_DRAFT = "web_draft"                 # إثراء/مسح محوكم — Draft
STATUS_APPROVED_INT = "approved_internal"
STATUS_DRAFT = "draft_pending_review"
STATUS_UNAVAILABLE = "unavailable"

# Geography restriction map: source_name → frozenset of valid ISO-3166-1 alpha-2 codes.
# Sources absent from this map are unrestricted (MockMarketProvider, KnowledgeStoreProvider).
# When a restricted source is returned for a geography outside its valid set,
# ALL enrichment values from that run are treated as geographically unsupported.
_GEOGRAPHY_RESTRICTED_SOURCES: Dict[str, FrozenSet[str]] = {
    "EgyptianPriceRangeDictionary": frozenset({"EG", "EGP"}),
}


def _enrichment_covers_geography(enr: Any, country_code: str) -> bool:
    """
    Returns False when any data_source_log entry is restricted to a geography that
    excludes country_code.  Mock and knowledge-store entries are unrestricted.
    Absence of coverage metadata is treated as unrestricted (conservative default).
    """
    requested = country_code.upper()
    for entry in (enr.data_source_log or []):
        sn = getattr(entry, "source_name", "") or ""
        valid = _GEOGRAPHY_RESTRICTED_SOURCES.get(sn)
        if valid is not None and requested not in valid:
            return False
    return True


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _num(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _input_entry(
    value: Any,
    unit: str,
    source_kind: str,
    source_name: str,
    model_or_uri: str,
    confidence: Optional[float],
    tier: str,
    status: str,
    retrieved_at: str,
    note: str = "",
    *,
    confidence_status: Optional[str] = None,
    confidence_reason: Optional[str] = None,
) -> Dict[str, Any]:
    entry: Dict[str, Any] = {
        "value": value,
        "unit": unit,
        "source_kind": source_kind,          # mass_appraisal | enrichment_draft
        "source_name": source_name,
        "model_or_uri": model_or_uri,
        "confidence": confidence,
        "tier": tier,
        "status": status,
        "retrieved_at": retrieved_at,
        "reconciliation_note": note,
    }
    if confidence_status is not None:
        entry["confidence_status"] = confidence_status
    if confidence_reason is not None:
        entry["confidence_reason"] = confidence_reason
    return entry


def build_hbu_inputs(
    case: Dict[str, Any],
    *,
    work_dir: Optional[str] = None,
    enrichment_layer: Optional[MarketEnrichmentLayer] = None,
    use_mock_enrichment: bool = False,
    enable_enrichment: bool = False,
) -> Dict[str, Any]:
    """
    يبني مدخلات موضوع التقييم لتقرير HBU + جدول مصدرية، من المجمع (أساسي) ثم الإثراء (Draft).

    المعاملات:
      case               — dict يتضمن: case_id, country_code, region, city, district,
                           asset_type, valuation_purpose, land_area_m2,
                           comparable_units: [{id, area, floor, year_built, condition, sale_price?}]
      work_dir           — مجلد التصدير للمجمع.
                           إذا None: يُنشأ مجلد مؤقت داخليًا ويُحذف تلقائيًا عند الانتهاء.
                           إذا مرّر المستدعي قيمة: هو المسؤول عن دورة حياة المجلد.
      enrichment_layer   — طبقة إثراء جاهزة (Dependency Injection) — تُمكّن الإثراء.
      use_mock_enrichment — True لتفعيل MockMarketProvider في بيئة الاختبار.
      enable_enrichment  — True لإنشاء طبقة حقيقية بمزودات محلية/Qdrant.
                           إذا كانت الثلاثة False ولا enrichment_layer → الإثراء غير مُفعَّل
                           (Data Minimization: لا providers تُنشأ بدون طلب صريح).

    base_market_ppm: عند غياب القيمة يُمرَّر 0 (Neutral Sentinel مثبت) — _market_adjustment
    تتجاهل معامل market_ppm تمامًا، وبالتالي 0 لا يؤثر على avg_ppm أو الناتج النهائي.
    التحقق في test_hb10_base_market_ppm_neutral_sentinel.

    Returns: dict فيه subject · inputs · provenance · unavailable · mass_appraisal ·
             enrichment_draft · governance · generated_at
    """
    retrieved = _now_iso()
    country = case.get("country_code", "SA")
    region = case.get("region", country)
    city = case.get("city", "")
    district = case.get("district", "")
    asset_type = case.get("asset_type", "residential")
    purpose = case.get("valuation_purpose", "market_value")

    inputs: Dict[str, Any] = {}
    provenance: List[Dict[str, Any]] = []
    unavailable: List[Dict[str, str]] = []

    # ── 1) المصدر الداخلي الأساسي: محرّك التقييم الجماعي (READ-ONLY) ───────────────
    ma: Dict[str, Any] = {}
    comps = case.get("comparable_units") or []
    if comps:
        _ma_kwargs: Dict[str, Any] = dict(
            base_market_ppm=float(case.get("base_market_ppm", 0) or 0),
            location=city or region,
            region=region,
            method=case.get("mass_method", "both"),
            purpose=case.get("mass_purpose", "fair_market"),
        )
        if work_dir is not None:
            # Caller-supplied directory — caller manages lifecycle
            ma = run_mass_appraisal(comps, output_dir=work_dir, **_ma_kwargs)
        else:
            # Auto-temp: create, run, clean up on exit (Exceptions still propagate)
            with tempfile.TemporaryDirectory(prefix="hbu_ma_") as _tmp:
                ma = run_mass_appraisal(comps, output_dir=_tmp, **_ma_kwargs)

    ma_ok = bool(ma) and "avg_ppm" in ma and ma.get("n_units", 0) > 0

    ma_model = (
        f"mass_appraisal.run_mass_appraisal(method={ma.get('method', '-')})" if ma_ok else ""
    )

    # Confidence: derived from IAAO ratio study evidence only — no fixed fallback
    ma_conf: Optional[float] = None
    _ma_conf_status: Optional[str] = None
    _ma_conf_reason: Optional[str] = None
    if ma_ok:
        rs = ma.get("ratio_study", {}) or {}
        if rs.get("n_sales", 0) > 0 and rs.get("cod") is not None:
            # COD = coefficient of dispersion; lower COD → higher confidence (clamped 50–95)
            ma_conf = max(50.0, min(95.0, 100.0 - float(rs["cod"])))
        else:
            # No ratio study → no evidence for confidence; never invent a heuristic number
            _ma_conf_status = "unavailable"
            _ma_conf_reason = "ratio_study_missing"

    # ── 2) الإثراء المحوكم (Opt-in — Draft — يبقى pending_human_review) ─────────────
    _enr_active = (
        enrichment_layer is not None
        or use_mock_enrichment
        or enable_enrichment
    )

    geo_ok: Optional[bool] = None
    sv: Dict[str, Any] = {}
    enr_mi: Dict[str, Any] = {}
    enr_conf: Optional[float] = None
    enr_src = ""
    enr_uri = ""
    enr_is_draft = False
    enr_dict: Dict[str, Any] = {"status": "enrichment_not_enabled"}

    if _enr_active:
        layer = enrichment_layer or MarketEnrichmentLayer(use_mock=use_mock_enrichment)
        enr = layer.enrich(build_request(country, region, city, district, asset_type, purpose))
        geo_ok = _enrichment_covers_geography(enr, country)
        sv = (enr.suggested_values or {}) if geo_ok else {}
        enr_mi = (enr.market_indicators or {}) if geo_ok else {}
        enr_conf = enr.confidence_score
        enr_src = enr.data_source_log[0].source_name if enr.data_source_log else "enrichment"
        enr_uri = enr.data_source_log[0].source_uri if enr.data_source_log else ""
        enr_is_draft = (enr.approval_status != "approved") and (not enr.can_generate_final_report())
        enr_dict = enr.to_dict()

    def _enr_gap_reason(default_msg: str) -> str:
        """Unavailability reason when enrichment is the expected source but didn't deliver."""
        if not _enr_active:
            return "enrichment_not_enabled"
        if geo_ok is False:
            return "enrichment_geography_unsupported"
        return default_msg

    # ── سعر المتر (price_per_m2): المجمع أساسي، الإثراء Draft عند الحاجة ─────────────
    ma_ppm = _num(ma.get("avg_ppm")) if ma_ok else None
    enr_ppm = _num(sv.get("comp_avg_price_m2"))
    if ma_ppm is not None:
        note = ""
        if enr_ppm is not None:
            note = (
                f"تعارض: المجمع {ma_ppm:,.0f} مقابل إثراء Draft {enr_ppm:,.0f} — "
                "المُختار: المجمع (مُعتمَد داخلي > Draft)."
            )
        inputs["price_per_m2"] = _input_entry(
            round(ma_ppm, 0), "SAR/m²", "mass_appraisal", "Mass Appraisal Engine",
            ma_model, ma_conf, TIER_INTERNAL_PRIMARY, STATUS_APPROVED_INT, retrieved, note,
            confidence_status=_ma_conf_status, confidence_reason=_ma_conf_reason,
        )
    elif enr_ppm is not None:
        inputs["price_per_m2"] = _input_entry(
            round(enr_ppm, 0), "SAR/m²", "enrichment_draft", enr_src, enr_uri,
            enr_conf, TIER_WEB_DRAFT, STATUS_DRAFT, retrieved,
            "من الإثراء المحوكم Draft — لا يُعتمد إلا بمراجعة الخبير.",
        )
    else:
        unavailable.append({
            "input": "price_per_m2",
            "reason": _enr_gap_reason("لا مجمع (بلا مقارنات) ولا إثراء — لا يُلفَّق رقم."),
        })

    # ── نطاق سعر المقارنات (comparable_ppm_range) ────────────────────────────────────
    if ma_ok and ma.get("portfolio_summary"):
        ps = ma["portfolio_summary"]
        inputs["comparable_ppm_range"] = _input_entry(
            [ps.get("min_ppm"), ps.get("max_ppm")], "SAR/m²", "mass_appraisal",
            "Mass Appraisal Engine", ma_model, ma_conf,
            TIER_INTERNAL_PRIMARY, STATUS_APPROVED_INT, retrieved,
            confidence_status=_ma_conf_status, confidence_reason=_ma_conf_reason,
        )
    else:
        lo = _num(enr_mi.get("price_range_lo"))
        hi = _num(enr_mi.get("price_range_hi"))
        if lo is not None and hi is not None:
            inputs["comparable_ppm_range"] = _input_entry(
                [lo, hi], "SAR/m²", "enrichment_draft", enr_src, enr_uri, enr_conf,
                TIER_WEB_DRAFT, STATUS_DRAFT, retrieved, "نطاق Draft محوكم.",
            )

    # ── الإيجار/الرسملة/الشغور: من الإثراء Draft، وإلا unavailable (بلا تلفيق) ─────────
    for key, uni, label in [
        ("rent_per_m2", "SAR/m²/yr", "الإيجار السنوي/م²"),
        ("cap_rate_range", "%", "معدل الرسملة"),
        ("market_vacancy_rate", "%", "نسبة الشغور"),
    ]:
        val = sv.get(key)
        if val is not None:
            inputs[key] = _input_entry(
                val, uni, "enrichment_draft", enr_src, enr_uri, enr_conf,
                TIER_WEB_DRAFT, STATUS_DRAFT, retrieved,
                "من الإثراء المحوكم Draft — لا يُدرّب النموذج المعتمد.",
            )
        else:
            unavailable.append({
                "input": key,
                "reason": _enr_gap_reason(
                    f"{label}: غير متوفّر من المجمع ولا الإثراء — لا يُلفَّق."
                ),
            })

    # ── دراسة النسب (IAAO) كمؤشّر جودة داخلي ────────────────────────────────────────
    if ma_ok and (ma.get("ratio_study") or {}).get("n_sales", 0) > 0:
        rs = ma["ratio_study"]
        inputs["ratio_study_iaao"] = _input_entry(
            {"cod": rs.get("cod"), "prd": rs.get("prd"), "uniformity": rs.get("uniformity")},
            "IAAO", "mass_appraisal", "Mass Appraisal Engine (ratio study)",
            ma_model, ma_conf, TIER_INTERNAL_PRIMARY, STATUS_APPROVED_INT, retrieved,
            confidence_status=_ma_conf_status, confidence_reason=_ma_conf_reason,
        )

    # ── جدول المصدرية (Provenance) — صف لكل مُدخل ──────────────────────────────────
    for name, e in inputs.items():
        row: Dict[str, Any] = {
            "input": name,
            "value": e["value"],
            "source_kind": e["source_kind"],
            "source_name": e["source_name"],
            "model_or_uri": e["model_or_uri"],
            "confidence": e["confidence"],
            "tier": e["tier"],
            "status": e["status"],
            "retrieved_at": e["retrieved_at"],
            "reconciliation_note": e["reconciliation_note"],
        }
        if "confidence_status" in e:
            row["confidence_status"] = e["confidence_status"]
        if "confidence_reason" in e:
            row["confidence_reason"] = e["confidence_reason"]
        provenance.append(row)

    governance = {
        "advisory_only": True,
        "engines_readonly": True,
        "web_data_status": "draft_pending_review",
        "web_trains_model": False,
        "enrichment_is_draft": enr_is_draft,
        "fake_official_data": False,
        "primary_source": "mass_appraisal" if ma_ok else ("enrichment_draft" if inputs else "none"),
    }

    return {
        "case_id": case.get("case_id", ""),
        "subject": {
            "country_code": country, "region": region, "city": city, "district": district,
            "asset_type": asset_type, "valuation_purpose": purpose,
            "land_area_m2": case.get("land_area_m2"),
        },
        "inputs": inputs,
        "provenance": provenance,
        "unavailable": unavailable,
        "mass_appraisal": {
            "used": ma_ok,
            "avg_ppm": ma.get("avg_ppm") if ma_ok else None,
            "n_units": ma.get("n_units") if ma_ok else 0,
            "ratio_study": ma.get("ratio_study") if ma_ok else None,
            "portfolio_summary": ma.get("portfolio_summary") if ma_ok else None,
        },
        "enrichment_draft": enr_dict,
        "governance": governance,
        "generated_at": retrieved,
    }
