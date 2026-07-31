"""
hbu_sourced_inputs.py
HBU Inputs Sourcing Bridge — Mass Appraisal + Web Research + Enrichment

Aggregates HBU-specific market context inputs from:
  (a) Mass Appraisal Engine  (READ-ONLY) — run_mass_appraisal()
  (b) Market Research Draft  (READ-ONLY) — build_research_package()
  (c) Phase 19 Enrichment    (READ-ONLY) — MarketEnrichmentLayer.enrich()

Priority chain: mass_appraisal > web_research > enrichment_layer
All inputs carry full provenance records.

GOVERNANCE (enforced):
  advisory_only=True
  Web/enrichment inputs = Draft governed (never certified training data)
  No fabrication — unavailable inputs documented with reason
  No API keys exposed in any output
  READ-ONLY calls only — no engine state modified
"""
from __future__ import annotations

import sys
import pathlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_CORE = pathlib.Path(__file__).resolve().parent.parent
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

_DRAFT_LABEL = "Draft — مسح مبدئي محوكم"
_DRAFT_NOTE  = "سعر عرض وليس سعر صفقة مؤكدة — يخضع للمراجعة البشرية"


# ─── Provenance record ────────────────────────────────────────────────────────

@dataclass
class HBUInputProvenance:
    input_id:           str
    label_ar:           str
    value_used:         Optional[float]
    unit:               str
    source_type:        str   # mass_appraisal | web_research | enrichment_layer | body_default | unavailable
    source_name:        str
    source_uri:         str   # no local paths
    retrieved_at:       str   # ISO 8601
    confidence_score:   float # 0–100
    source_tier:        str   # "Tier-1 محوكم" | "Tier-2 Draft" | "N/A"
    status:             str   # "Certified" | "Draft — مسح مبدئي محوكم" | "غير متاح"
    reconciliation_note: str = ""
    mass_appraisal_value: Optional[float] = None
    research_value:        Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_id":            self.input_id,
            "label_ar":            self.label_ar,
            "value_used":          self.value_used,
            "unit":                self.unit,
            "source_type":         self.source_type,
            "source_name":         self.source_name,
            "source_uri":          self.source_uri,
            "retrieved_at":        self.retrieved_at,
            "confidence_score":    self.confidence_score,
            "source_tier":         self.source_tier,
            "status":              self.status,
            "reconciliation_note": self.reconciliation_note,
            "mass_appraisal_value": self.mass_appraisal_value,
            "research_value":       self.research_value,
        }


@dataclass
class HBUSourcingResult:
    market_inputs:        Dict[str, Any]
    provenance_table:     List[HBUInputProvenance]
    source_log:           List[Dict[str, Any]]
    enrichment_comps:     List[Dict[str, Any]]
    mass_appraisal_summary: Dict[str, Any]
    advisory_only:        bool = True
    run_id:               str  = ""
    retrieved_at:         str  = ""
    warnings:             List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "market_inputs":       self.market_inputs,
            "provenance_table":    [p.to_dict() for p in self.provenance_table],
            "source_log":          self.source_log,
            "enrichment_comps":    self.enrichment_comps,
            "mass_appraisal_summary": self.mass_appraisal_summary,
            "advisory_only":       self.advisory_only,
            "run_id":              self.run_id,
            "retrieved_at":        self.retrieved_at,
            "warnings":            self.warnings,
        }


# ─── Source callers (READ-ONLY) ────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _call_mass_appraisal(body: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from mass_appraisal import run_mass_appraisal
        unit = {
            "id":         "hbu_subject",
            "area":       float(body.get("land_area_m2") or 2400),
            "floor":      1,
            "year_built": float(body.get("year_built") or 2015),
            "condition":  str(body.get("condition", "good")),
        }
        result = run_mass_appraisal(
            units=[unit],
            base_market_ppm=0.0,
            location=str(body.get("city_ar") or body.get("city", "الرياض")),
            region=str(body.get("country_code") or "SA"),
            method="avm",
            purpose="fair_market",
        )
        return result or {"_available": False}
    except Exception as exc:
        return {"_error": str(exc), "_available": False}


def _call_market_research(body: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from valuation_market_research import build_research_package
        research_body = {
            "country_code":      body.get("country_code", "SA"),
            "city":              body.get("city_ar") or body.get("city", "الرياض"),
            "district":          body.get("district_ar") or body.get("district", ""),
            "asset_type":        "أرض — land",
            "valuation_purpose": "highest_best_use",
            "area_m2":           float(body.get("land_area_m2") or 2400),
        }
        return build_research_package(research_body) or {"_available": False, "advisory_only": True}
    except Exception as exc:
        return {"_error": str(exc), "_available": False, "advisory_only": True}


def _call_enrichment(body: Dict[str, Any]) -> Optional[Any]:
    try:
        from enrichment.market_enrichment import MarketEnrichmentLayer, build_request
        layer = MarketEnrichmentLayer()
        request = build_request(
            country_code=      body.get("country_code", "SA"),
            region=            body.get("district_ar") or body.get("region", ""),
            city=              body.get("city_ar") or "الرياض",
            district=          body.get("district_ar") or "",
            asset_type=        "أرض — land",
            valuation_purpose= "highest_best_use",
        )
        return layer.enrich(request)
    except Exception:
        return None


# ─── Provenance constructors ───────────────────────────────────────────────────

def _prov_mass(input_id, label_ar, value, unit, mass_result, confidence=75.0,
               note="") -> HBUInputProvenance:
    ver = mass_result.get("model_version", "AVM-v1")
    return HBUInputProvenance(
        input_id=input_id, label_ar=label_ar,
        value_used=round(value, 2), unit=unit,
        source_type="mass_appraisal",
        source_name=f"نموذج التقييم الجماعي ({ver})",
        source_uri=f"internal:mass_appraisal:{ver}",
        retrieved_at=_now_iso(),
        confidence_score=confidence,
        source_tier="Tier-1 محوكم",
        status="Certified",
        reconciliation_note=note,
    )


def _prov_research(input_id, label_ar, value, unit, research_pkg,
                   source_ids, confidence=55.0) -> HBUInputProvenance:
    sources = research_pkg.get("sources", [])
    src = next((s for s in sources if s.get("source_id") in source_ids), {})
    return HBUInputProvenance(
        input_id=input_id, label_ar=label_ar,
        value_used=round(value, 4), unit=unit,
        source_type="web_research",
        source_name=src.get("evidence_type", "مسح سوقي إلكتروني"),
        source_uri=src.get("url", ""),
        retrieved_at=src.get("access_date", _now_iso()),
        confidence_score=confidence,
        source_tier="Tier-2 Draft",
        status=_DRAFT_LABEL,
        reconciliation_note=_DRAFT_NOTE,
    )


def _prov_enr(input_id, label_ar, value, unit, note="") -> HBUInputProvenance:
    return HBUInputProvenance(
        input_id=input_id, label_ar=label_ar,
        value_used=round(value, 4) if value is not None else None, unit=unit,
        source_type="enrichment_layer",
        source_name="طبقة الإثراء — Phase 19",
        source_uri="internal:enrichment",
        retrieved_at=_now_iso(),
        confidence_score=45.0,
        source_tier="Tier-2 Draft",
        status=_DRAFT_LABEL,
        reconciliation_note=note or "طبقة إثراء محلية — قيد المراجعة البشرية",
    )


def _prov_na(input_id, label_ar, unit, reason) -> HBUInputProvenance:
    return HBUInputProvenance(
        input_id=input_id, label_ar=label_ar,
        value_used=None, unit=unit,
        source_type="unavailable",
        source_name="غير متاح",
        source_uri="",
        retrieved_at=_now_iso(),
        confidence_score=0.0,
        source_tier="N/A",
        status="غير متاح",
        reconciliation_note=f"السبب: {reason}",
    )


def _prov_default(input_id, label_ar, value, unit, note) -> HBUInputProvenance:
    return HBUInputProvenance(
        input_id=input_id, label_ar=label_ar,
        value_used=value, unit=unit,
        source_type="body_default",
        source_name="قيمة معيارية افتراضية",
        source_uri="",
        retrieved_at=_now_iso(),
        confidence_score=40.0,
        source_tier="Tier-2 Draft",
        status="Draft — افتراضي",
        reconciliation_note=note,
    )


def _pi_val(pi, method_key, field_key):
    method = pi.get(method_key, {})
    fld    = method.get(field_key, {})
    if isinstance(fld, dict) and not fld.get("missing"):
        val  = fld.get("selected_value") or fld.get("median")
        conf = float(fld.get("confidence") or 50.0)
        sids = fld.get("source_ids", [])
        if val is not None:
            return float(val), conf, sids
    return None, 0.0, []


# ─── Main sourcing function ────────────────────────────────────────────────────

def source_hbu_inputs(body: Dict[str, Any]) -> HBUSourcingResult:
    """
    Aggregate HBU market context inputs from all available sources.

    Returns HBUSourcingResult with:
      - 10+ HBUInputProvenance records (one per HBU market input)
      - Mass appraisal summary (READ-ONLY, Tier-1 Certified)
      - Enrichment comparables and source log
      - All Draft web inputs labeled per governance rules
      - Missing inputs documented with reason (never fabricated)
    """
    now    = _now_iso()
    run_id = "hbu_sourcing_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    warnings: List[str] = []

    land_area = float(body.get("land_area_m2") or 2400)

    # ── 1. Call all three READ-ONLY sources ───────────────────────────────────
    mass_result    = _call_mass_appraisal(body)
    research_pkg   = _call_market_research(body)
    enrichment_res = _call_enrichment(body)

    # ── 2. Parse mass appraisal ───────────────────────────────────────────────
    ma_ok = bool(mass_result and not mass_result.get("_error"))
    avm_ppm = adj_ppm = avg_ppm = 0.0
    ma_cod = ma_prd = None
    ma_ver = "AVM-v1"
    ma_unit_value = 0.0

    if ma_ok:
        units_out = mass_result.get("units", [])
        if units_out:
            u0 = units_out[0]
            avm_ppm = float(u0.get("avm_ppm") or 0)
            adj_ppm = float(u0.get("adj_ppm") or avm_ppm)
            ma_unit_value = float(u0.get("unit_value") or 0)
        avg_ppm = float(mass_result.get("avg_ppm") or avm_ppm)
        rs      = mass_result.get("ratio_study", {})
        ma_cod  = rs.get("cod")
        ma_prd  = rs.get("prd")
        ma_ver  = mass_result.get("model_version", "AVM-v1")
        if not avm_ppm:
            ma_ok = False
            warnings.append("mass_appraisal: avm_ppm = 0 — يُعامَل كغير متاح")
    else:
        warnings.append("mass_appraisal unavailable: "
                        + str((mass_result or {}).get("_error", "import error")))

    # ── 3. Parse research package ─────────────────────────────────────────────
    rp_ok = bool(
        research_pkg
        and not research_pkg.get("_error")
        and research_pkg.get("status") != "provider_unavailable"
    )
    pi = research_pkg.get("proposed_inputs", {}) if research_pkg else {}
    rp_sources = research_pkg.get("sources", []) if research_pkg else []
    if research_pkg and research_pkg.get("_error"):
        warnings.append("research_package error: " + str(research_pkg["_error"]))

    # ── 4. Parse enrichment ───────────────────────────────────────────────────
    enr_comps: List[Dict[str, Any]] = []
    enr_source_log: List[Dict[str, Any]] = []
    enr_indicators: Dict[str, Any] = {}
    enr_price_lo = enr_price_hi = 0.0

    if enrichment_res is not None:
        try:
            for c in getattr(enrichment_res, "comparable_suggestions", []):
                cd = c.to_dict() if hasattr(c, "to_dict") else dict(c)
                enr_comps.append(cd)
                if not enr_price_lo:
                    enr_price_lo = float(c.price_m2_lo or 0)
                    enr_price_hi = float(c.price_m2_hi or 0)
            for s in getattr(enrichment_res, "data_source_log", []):
                enr_source_log.append(s.to_dict() if hasattr(s, "to_dict") else dict(s))
            enr_indicators = dict(getattr(enrichment_res, "market_indicators", {}) or {})
        except Exception as exc:
            warnings.append(f"enrichment parse error: {exc}")

    # ── 5. Build provenance per HBU market input ──────────────────────────────
    provenance: List[HBUInputProvenance] = []

    # I-01 سعر المتر المربع (مؤشر السوق المجمع)
    LAND_RATIO = 0.40
    if ma_ok and avm_ppm:
        land_ppm_ma = round(avm_ppm * LAND_RATIO)
        p = _prov_mass(
            "land_ppm_indicator", "سعر المتر المربع (مؤشر سوق مجمع)",
            land_ppm_ma, "ريال/م²", mass_result, confidence=70.0,
            note=(
                f"مشتق من avm_ppm ({avm_ppm:,.0f}) × {LAND_RATIO} "
                f"(حصة الأرض التقديرية) — الإصدار: {ma_ver}"
            ),
        )
        p.source_tier = "Tier-1 محوكم (مشتق)"
    else:
        rp_price, rp_price_conf, rp_price_sids = _pi_val(pi, "sales_comparison", "price_per_m2")
        if rp_price:
            p = _prov_research("land_ppm_indicator", "سعر المتر المربع (مؤشر سوق مجمع)",
                               rp_price, "ريال/م²", research_pkg, rp_price_sids, rp_price_conf)
        else:
            p = _prov_na("land_ppm_indicator", "سعر المتر المربع (مؤشر سوق مجمع)",
                         "ريال/م²", "لا يتوفر نموذج مجمع ولا مزوّد بحث")
    provenance.append(p)

    # I-02 القيمة السوقية التأشيرية الإجمالية
    if ma_ok and ma_unit_value:
        p = _prov_mass(
            "market_value_indicator", "القيمة السوقية التأشيرية",
            ma_unit_value, "ريال", mass_result, confidence=72.0,
            note=f"قيمة الوحدة من النموذج المجمع ({ma_ver})",
        )
    else:
        p = _prov_na("market_value_indicator", "القيمة السوقية التأشيرية",
                     "ريال", "لا يتوفر نموذج مجمع")
    provenance.append(p)

    # I-03 معدل الرسملة (Cap Rate)
    rp_cap, rp_cap_conf, rp_cap_sids = _pi_val(pi, "income_capitalization", "capitalization_rate")
    enr_cap = enr_indicators.get("cap_rate") or enr_indicators.get("capitalization_rate")
    if rp_cap:
        p = _prov_research("cap_rate", "معدل الرسملة", rp_cap, "%",
                           research_pkg, rp_cap_sids, rp_cap_conf)
    elif enr_cap:
        p = _prov_enr("cap_rate", "معدل الرسملة", float(enr_cap), "%")
    else:
        p = _prov_default("cap_rate", "معدل الرسملة", 0.08, "%",
                          "قيمة معيارية (8%) لسوق الرياض السكني — يُستخدم عند غياب البيانات")
    provenance.append(p)

    # I-04 إيجار شهري سكني / م²
    rp_rent, rp_rent_conf, rp_rent_sids = _pi_val(
        pi, "income_capitalization", "market_rent_per_m2_monthly")
    enr_rent = enr_indicators.get("monthly_rent") or enr_indicators.get("rent_per_m2")
    if rp_rent:
        p = _prov_research("market_rent_residential_pm2", "الإيجار الشهري السكني / م²",
                           rp_rent, "ريال/م²/شهر", research_pkg, rp_rent_sids, rp_rent_conf)
    elif enr_rent:
        p = _prov_enr("market_rent_residential_pm2", "الإيجار الشهري السكني / م²",
                      float(enr_rent), "ريال/م²/شهر")
    else:
        p = _prov_na("market_rent_residential_pm2", "الإيجار الشهري السكني / م²",
                     "ريال/م²/شهر", "لا يتوفر مزوّد بحث أو إثراء للإيجار السكني")
    provenance.append(p)

    # I-05 إيجار شهري تجاري / م²
    rp_crent, rp_crent_conf, rp_crent_sids = _pi_val(
        pi, "income_capitalization", "market_rent_commercial_per_m2_monthly")
    if rp_crent:
        p = _prov_research("market_rent_commercial_pm2", "الإيجار الشهري التجاري / م²",
                           rp_crent, "ريال/م²/شهر", research_pkg, rp_crent_sids, rp_crent_conf)
    else:
        p = _prov_na("market_rent_commercial_pm2", "الإيجار الشهري التجاري / م²",
                     "ريال/م²/شهر", "لا يتوفر مزوّد بحث للإيجار التجاري")
    provenance.append(p)

    # I-06 تكلفة البناء / م² (مشتقة من النموذج أو Draft)
    CONSTR_RATIO = 0.55
    if ma_ok and adj_ppm:
        constr_ppm = round(adj_ppm * CONSTR_RATIO)
        p = _prov_mass(
            "construction_cost_pm2", "تكلفة البناء / م²",
            constr_ppm, "ريال/م²", mass_result, confidence=60.0,
            note=(
                f"مشتق من adj_ppm ({adj_ppm:,.0f}) × {CONSTR_RATIO} "
                "(مكوّن التحسينات التقديري) — تقريب"
            ),
        )
        p.source_tier = "Tier-1 محوكم (مشتق)"
    else:
        rp_cc, rp_cc_conf, rp_cc_sids = _pi_val(pi, "cost_approach", "construction_cost_per_m2")
        if rp_cc:
            p = _prov_research("construction_cost_pm2", "تكلفة البناء / م²",
                               rp_cc, "ريال/م²", research_pkg, rp_cc_sids, rp_cc_conf)
        else:
            p = _prov_na("construction_cost_pm2", "تكلفة البناء / م²",
                         "ريال/م²", "لا يتوفر نموذج مجمع أو مزوّد بحث")
    provenance.append(p)

    # I-07 معدل الخصم
    rp_disc, rp_disc_conf, rp_disc_sids = _pi_val(pi, "dcf", "discount_rate")
    if rp_disc:
        p = _prov_research("discount_rate", "معدل الخصم (DCF)",
                           rp_disc, "%", research_pkg, rp_disc_sids, rp_disc_conf)
    elif rp_cap:
        derived = round(rp_cap + 0.03, 4)
        p = _prov_default("discount_rate", "معدل الخصم (DCF)", derived, "%",
                          f"مشتق: cap_rate ({rp_cap:.4f}) + علاوة مخاطر 300 نقطة أساس")
    else:
        p = _prov_default("discount_rate", "معدل الخصم (DCF)", 0.10, "%",
                          "قيمة معيارية (10%) — يُستخدم عند غياب بيانات السوق")
    provenance.append(p)

    # I-08 معدل الإشغال السكني
    enr_occ = enr_indicators.get("occupancy_rate") or enr_indicators.get("occupancy")
    rp_occ, rp_occ_conf, rp_occ_sids = _pi_val(pi, "income_capitalization", "occupancy_rate")
    if rp_occ:
        p = _prov_research("occupancy_residential", "معدل الإشغال السكني",
                           rp_occ, "%", research_pkg, rp_occ_sids, rp_occ_conf)
    elif enr_occ:
        p = _prov_enr("occupancy_residential", "معدل الإشغال السكني",
                      float(enr_occ), "%")
    else:
        p = _prov_na("occupancy_residential", "معدل الإشغال السكني",
                     "%", "لا يتوفر مزوّد بيانات للإشغال")
    provenance.append(p)

    # I-09 معدل الاستيعاب (Absorption Rate)
    enr_abs = enr_indicators.get("absorption_rate") or enr_indicators.get("absorption_months")
    if enr_abs:
        p = _prov_enr("absorption_rate_pct", "معدل الاستيعاب السوقي",
                      float(enr_abs), "% شهرياً أو شهر",
                      "معدل استيعاب الوحدات الجديدة — مؤشر إثراء محلي")
    else:
        p = _prov_na("absorption_rate_pct", "معدل الاستيعاب السوقي",
                     "% شهرياً", "لا يتوفر مزوّد بيانات الاستيعاب")
    provenance.append(p)

    # I-10 معدل النمو السنوي
    rp_growth, rp_growth_conf, rp_growth_sids = _pi_val(pi, "dcf", "annual_growth_rate")
    if rp_growth:
        p = _prov_research("annual_growth_rate", "معدل النمو السنوي",
                           rp_growth, "%", research_pkg, rp_growth_sids, rp_growth_conf)
    else:
        p = _prov_default("annual_growth_rate", "معدل النمو السنوي", 0.03, "%",
                          "قيمة محافظة (3%) — معيار سوقي متحفظ لسوق الرياض")
    provenance.append(p)

    # I-11 نسبة الشواغر السوقية
    enr_vac = enr_indicators.get("vacancy_rate")
    rp_vac, rp_vac_conf, rp_vac_sids = _pi_val(pi, "income_capitalization", "vacancy_rate")
    if rp_vac:
        p = _prov_research("market_vacancy_rate", "معدل الشواغر السوقي",
                           rp_vac, "%", research_pkg, rp_vac_sids, rp_vac_conf)
    elif enr_vac:
        p = _prov_enr("market_vacancy_rate", "معدل الشواغر السوقي",
                      float(enr_vac), "%")
    else:
        p = _prov_na("market_vacancy_rate", "معدل الشواغر السوقي",
                     "%", "لا يتوفر مزوّد بيانات الشواغر")
    provenance.append(p)

    # ── 6. market_inputs dict ─────────────────────────────────────────────────
    def _v(iid: str) -> Optional[float]:
        for p in provenance:
            if p.input_id == iid:
                return p.value_used
        return None

    market_inputs: Dict[str, Any] = {
        "land_ppm_indicator":         _v("land_ppm_indicator"),
        "market_value_indicator":     _v("market_value_indicator"),
        "cap_rate":                   _v("cap_rate"),
        "market_rent_residential_pm2": _v("market_rent_residential_pm2"),
        "market_rent_commercial_pm2":  _v("market_rent_commercial_pm2"),
        "construction_cost_pm2":       _v("construction_cost_pm2"),
        "discount_rate":               _v("discount_rate"),
        "occupancy_residential":       _v("occupancy_residential"),
        "absorption_rate_pct":         _v("absorption_rate_pct"),
        "annual_growth_rate":          _v("annual_growth_rate"),
        "market_vacancy_rate":         _v("market_vacancy_rate"),
        "avm_ppm_raw":                avm_ppm,
        "adj_ppm_raw":                adj_ppm,
        "avg_ppm_raw":                avg_ppm,
        "land_area_m2":               land_area,
    }

    # ── 7. Clean source log (no local paths) ──────────────────────────────────
    full_source_log: List[Dict[str, Any]] = []
    for src in rp_sources:
        entry = dict(src)
        for k in ("url", "source_uri"):
            uri = str(entry.get(k) or "")
            if uri.startswith("file://") or ":\\" in uri or (
                    uri.startswith("/") and not uri.startswith("/api")):
                entry[k] = "[مسار داخلي — محجوب]"
        full_source_log.append(entry)
    full_source_log.extend(enr_source_log)

    ma_summary = {
        "available":     ma_ok,
        "avm_ppm":       avm_ppm,
        "adj_ppm":       adj_ppm,
        "avg_ppm":       avg_ppm,
        "unit_value":    ma_unit_value,
        "land_area_m2":  land_area,
        "cod":           ma_cod,
        "prd":           ma_prd,
        "model_version": ma_ver,
        "model_note":    (
            "نموذج OLS Hedonic v1 (r²≈0.83) — معايَر على وحدات مبنية. "
            "مضاعف SA=2.5. المُشتقَّات (land_ppm_indicator) تقريبية."
        ),
    } if mass_result else {"available": False}

    return HBUSourcingResult(
        market_inputs=market_inputs,
        provenance_table=provenance,
        source_log=full_source_log,
        enrichment_comps=enr_comps,
        mass_appraisal_summary=ma_summary,
        advisory_only=True,
        run_id=run_id,
        retrieved_at=now,
        warnings=warnings,
    )
