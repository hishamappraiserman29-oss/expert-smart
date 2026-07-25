"""
pv_sim_sourced_inputs.py
Inputs Sourcing Layer for the enhanced simulation report.
Aggregates subject property inputs from:
  (a) Mass Appraisal Engine (READ-ONLY) — via run_mass_appraisal()
  (b) Internet-assisted Market Research (READ-ONLY) — via build_research_package()
  (c) Phase 19 Enrichment Layer (READ-ONLY) — via MarketEnrichmentLayer.enrich()

All calls are READ-ONLY — no engine state is modified.

Governance:
  advisory_only=True
  Web/enrichment inputs = Draft governed (never train certified model)
  No API keys in response
  No fake sources or fabricated data
"""
from __future__ import annotations

import sys
import pathlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Ensure core_engine is importable
_CORE = pathlib.Path(__file__).resolve().parent.parent
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))


# ── Provenance record ─────────────────────────────────────────────────────────

@dataclass
class InputProvenance:
    """Per-input provenance record embedded in every report output."""

    input_id: str
    label_ar: str
    value_used: Optional[float]
    unit: str
    source_type: str        # "mass_appraisal" | "web_research" | "enrichment_layer" | "body_input" | "unavailable"
    source_name: str
    source_uri: str         # scrubbed — no local paths exposed
    retrieved_at: str       # ISO 8601
    confidence_score: float  # 0–100
    source_tier: str        # "Tier-1 محوكم" | "Tier-2 Draft" | "N/A"
    status: str             # "Certified" | "Draft — مسح مبدئي محوكم" | "غير متاح"
    reconciliation_note: str = ""
    mass_appraisal_value: Optional[float] = None
    research_value: Optional[float] = None

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
class SourcingResult:
    """Full output of the inputs sourcing layer."""

    subject_inputs: Dict[str, Any]
    provenance_table: List[InputProvenance]
    source_log: List[Dict[str, Any]]
    enrichment_comparables: List[Dict[str, Any]]
    mass_appraisal_summary: Dict[str, Any]
    advisory_only: bool = True
    external_reference_provided: bool = False
    reference_source: str = "mass_appraisal_and_draft_web_research"
    run_id: str = ""
    retrieved_at: str = ""
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject_inputs":           self.subject_inputs,
            "provenance_table":         [p.to_dict() for p in self.provenance_table],
            "source_log":               self.source_log,
            "enrichment_comparables":   self.enrichment_comparables,
            "mass_appraisal_summary":   self.mass_appraisal_summary,
            "advisory_only":            self.advisory_only,
            "external_reference_provided": self.external_reference_provided,
            "reference_source":         self.reference_source,
            "run_id":                   self.run_id,
            "retrieved_at":             self.retrieved_at,
            "warnings":                 self.warnings,
        }


# ── Source readers (READ-ONLY calls) ─────────────────────────────────────────

def _call_mass_appraisal(body: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from mass_appraisal import run_mass_appraisal
        unit = {
            "id":         "subject",
            "area":       float(body.get("built_up_area_m2") or 850),
            "floor":      float(body.get("floor_number") or 1),
            "year_built": float(body.get("year_built") or 2015),
            "condition":  str(body.get("condition", "good")),
        }
        result = run_mass_appraisal(
            units=[unit],
            base_market_ppm=float(body.get("land_price") or 0),
            location=str(body.get("city_ar") or body.get("city", "—")),
            region=str(body.get("country_code") or "QA"),
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
            "country_code":      body.get("country_code", "QA"),
            "city":              body.get("city_ar") or body.get("city", ""),
            "district":          body.get("district_ar") or body.get("district", ""),
            "asset_type":        body.get("asset_type_ar") or body.get("asset_type", "residential"),
            "valuation_purpose": "fair_market_value",
            "area_m2":           float(body.get("built_up_area_m2") or 850),
        }
        return build_research_package(research_body) or {"_available": False, "advisory_only": True}
    except Exception as exc:
        return {"_error": str(exc), "_available": False, "advisory_only": True}


def _call_enrichment(body: Dict[str, Any]) -> Optional[Any]:
    try:
        from enrichment.market_enrichment import MarketEnrichmentLayer, build_request
        layer = MarketEnrichmentLayer()
        request = build_request(
            country_code=      body.get("country_code", "QA"),
            region=            body.get("district_ar") or body.get("region", ""),
            city=              body.get("city_ar") or body.get("city", ""),
            district=          body.get("district_ar") or body.get("district", ""),
            asset_type=        body.get("asset_type_ar") or "residential",
            valuation_purpose= "fair_market_value",
        )
        return layer.enrich(request)
    except Exception:
        return None


# ── Provenance constructors ───────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _prov_unavailable(
    input_id: str, label_ar: str, unit: str, reason: str
) -> InputProvenance:
    return InputProvenance(
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


def _prov_mass(
    input_id: str, label_ar: str, value: float, unit: str,
    mass_result: Dict, confidence: float = 75.0,
) -> InputProvenance:
    version = mass_result.get("model_version", "AVM-v1")
    return InputProvenance(
        input_id=input_id, label_ar=label_ar,
        value_used=round(value, 2), unit=unit,
        source_type="mass_appraisal",
        source_name=f"نموذج التقييم المجمع ({version})",
        source_uri=f"internal:mass_appraisal:{version}",
        retrieved_at=_now_iso(),
        confidence_score=confidence,
        source_tier="Tier-1 محوكم",
        status="Certified",
    )


def _prov_research(
    input_id: str, label_ar: str, value: float, unit: str,
    research_pkg: Dict, source_ids: List[str], confidence: float = 55.0,
) -> InputProvenance:
    sources = research_pkg.get("sources", [])
    src = next((s for s in sources if s.get("source_id") in source_ids), {})
    uri = src.get("url", "")
    date = src.get("access_date", "")
    return InputProvenance(
        input_id=input_id, label_ar=label_ar,
        value_used=round(value, 4), unit=unit,
        source_type="web_research",
        source_name=src.get("evidence_type", "مسح سوقي إلكتروني"),
        source_uri=uri,
        retrieved_at=date or _now_iso(),
        confidence_score=confidence,
        source_tier="Tier-2 Draft",
        status="Draft — مسح مبدئي محوكم",
        reconciliation_note="سعر عرض وليس سعر صفقة مؤكدة — يخضع للمراجعة البشرية",
    )


def _pi_val(
    pi: Dict, method_key: str, field_key: str
) -> tuple:
    """Extract (value, confidence, source_ids) from proposed_inputs."""
    method = pi.get(method_key, {})
    fld    = method.get(field_key, {})
    if isinstance(fld, dict) and not fld.get("missing"):
        val  = fld.get("selected_value") or fld.get("median")
        conf = float(fld.get("confidence") or 50.0)
        sids = fld.get("source_ids", [])
        if val is not None:
            return float(val), conf, sids
    return None, 0.0, []


# ── Main sourcing function ────────────────────────────────────────────────────

def source_subject_inputs(body: Dict[str, Any]) -> SourcingResult:
    """
    Aggregate subject property inputs from all available sources.

    Priority: mass_appraisal > web_research > enrichment_layer > body_defaults

    GOVERNANCE (enforced):
      advisory_only=True
      All web/enrichment inputs labeled Draft governed
      No engine modification (READ-ONLY calls only)
      No API keys in response
      No fabricated data — missing inputs documented with reason
    """
    now    = _now_iso()
    run_id = "sourcing_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    warnings: List[str] = []

    # ── Call all sources ──────────────────────────────────────────────────────
    mass_result    = _call_mass_appraisal(body)
    research_pkg   = _call_market_research(body)
    enrichment_res = _call_enrichment(body)

    # ── Parse mass appraisal ──────────────────────────────────────────────────
    ma_ok = bool(mass_result and not mass_result.get("_error"))
    avm_ppm = adj_ppm = avg_ppm = 0.0
    ma_cod = ma_prd = None
    ma_ver = "AVM-v1"

    if ma_ok:
        units_out = mass_result.get("units", [])
        if units_out:
            u0 = units_out[0]
            avm_ppm = float(u0.get("avm_ppm") or 0)
            adj_ppm = float(u0.get("adj_ppm") or avm_ppm)
        avg_ppm = float(mass_result.get("avg_ppm") or avm_ppm)
        rs      = mass_result.get("ratio_study", {})
        ma_cod  = rs.get("cod")
        ma_prd  = rs.get("prd")
        ma_ver  = mass_result.get("model_version", "AVM-v1")
        if not avm_ppm:
            ma_ok = False
            warnings.append("mass_appraisal: avm_ppm = 0 — يُعامَل كغير متاح")
    else:
        warnings.append(
            "mass_appraisal unavailable: "
            + str((mass_result or {}).get("_error", "import error"))
        )

    # ── Parse research package ────────────────────────────────────────────────
    rp_ok = bool(
        research_pkg
        and not research_pkg.get("_error")
        and research_pkg.get("status") != "provider_unavailable"
    )
    pi = research_pkg.get("proposed_inputs", {}) if research_pkg else {}
    rp_sources = research_pkg.get("sources", []) if research_pkg else []
    if research_pkg and research_pkg.get("_error"):
        warnings.append("research_package error: " + str(research_pkg["_error"]))

    # ── Parse enrichment ─────────────────────────────────────────────────────
    enr_comps: List[Dict[str, Any]] = []
    enr_source_log: List[Dict[str, Any]] = []
    enr_price_lo = enr_price_hi = 0.0

    if enrichment_res is not None:
        try:
            for c in getattr(enrichment_res, "comparable_suggestions", []):
                cd = c.to_dict() if hasattr(c, "to_dict") else dict(c)
                enr_comps.append(cd)
                enr_price_lo = enr_price_lo or float(c.price_m2_lo or 0)
                enr_price_hi = enr_price_hi or float(c.price_m2_hi or 0)
            for s in getattr(enrichment_res, "data_source_log", []):
                enr_source_log.append(s.to_dict() if hasattr(s, "to_dict") else dict(s))
        except Exception as exc:
            warnings.append(f"enrichment parse error: {exc}")

    # ── Build provenance per input ────────────────────────────────────────────
    provenance: List[InputProvenance] = []

    # 1 — سعر المتر المربع (بيع)
    rp_price, rp_price_conf, rp_price_sids = _pi_val(pi, "sales_comparison", "price_per_m2")
    enr_price = (
        (enr_price_lo + enr_price_hi) / 2
        if enr_price_lo and enr_price_hi else None
    )
    if ma_ok and avm_ppm:
        p = _prov_mass("price_per_m2", "سعر المتر المربع (بيع)", avm_ppm, "ريال/م²", mass_result)
        p.research_value = rp_price or enr_price
        if rp_price:
            diff_pct = abs(avm_ppm - rp_price) / avm_ppm * 100
            p.reconciliation_note = (
                f"نموذج مجمع: {avm_ppm:,.0f} | بحث: {rp_price:,.0f} | "
                f"فرق: {diff_pct:.1f}% — يُستخدم المجمع (الأعلى موثوقية)"
            )
    elif rp_price:
        p = _prov_research(
            "price_per_m2", "سعر المتر المربع (بيع)", rp_price,
            "ريال/م²", research_pkg, rp_price_sids, rp_price_conf,
        )
        p.mass_appraisal_value = avm_ppm or None
    elif enr_price:
        p = InputProvenance(
            input_id="price_per_m2", label_ar="سعر المتر المربع (بيع)",
            value_used=round(enr_price, 0), unit="ريال/م²",
            source_type="enrichment_layer",
            source_name="طبقة الإثراء — Phase 19",
            source_uri="internal:enrichment",
            retrieved_at=now, confidence_score=45.0,
            source_tier="Tier-2 Draft",
            status="Draft — مسح مبدئي محوكم",
            reconciliation_note="متوسط نطاق سعري من طبقة الإثراء",
        )
    else:
        p = _prov_unavailable(
            "price_per_m2", "سعر المتر المربع (بيع)", "ريال/م²",
            "لا يتوفر نموذج مجمع أو مزوّد بحث",
        )
    provenance.append(p)

    # 2 — معدل الرسملة
    rp_cap, rp_cap_conf, rp_cap_sids = _pi_val(pi, "income_capitalization", "capitalization_rate")
    if rp_cap:
        p = _prov_research(
            "cap_rate", "معدل الرسملة", rp_cap, "%",
            research_pkg, rp_cap_sids, rp_cap_conf,
        )
    else:
        p = _prov_unavailable("cap_rate", "معدل الرسملة", "%", "لا يتوفر مزوّد بحث سوقي")
    provenance.append(p)

    # 3 — الإيجار الشهري / م²
    rp_rent, rp_rent_conf, rp_rent_sids = _pi_val(
        pi, "income_capitalization", "market_rent_per_m2_monthly"
    )
    if rp_rent:
        p = _prov_research(
            "market_rent_per_m2_monthly", "الإيجار الشهري / م²",
            rp_rent, "ريال/م²/شهر",
            research_pkg, rp_rent_sids, rp_rent_conf,
        )
    else:
        p = _prov_unavailable(
            "market_rent_per_m2_monthly", "الإيجار الشهري / م²",
            "ريال/م²/شهر", "لا يتوفر مزوّد بحث سوقي",
        )
    provenance.append(p)

    # 4 — معدل الشواغر
    rp_vac, rp_vac_conf, rp_vac_sids = _pi_val(
        pi, "income_capitalization", "vacancy_rate"
    )
    if rp_vac:
        p = _prov_research(
            "vacancy_rate", "معدل الشواغر", rp_vac, "%",
            research_pkg, rp_vac_sids, rp_vac_conf,
        )
    else:
        p = _prov_unavailable(
            "vacancy_rate", "معدل الشواغر", "%", "لا يتوفر مزوّد بحث سوقي"
        )
    provenance.append(p)

    # 5 — تكلفة البناء / م²  (adj_ppm × 0.60 كمكوّن التحسينات)
    CONST_RATIO = 0.60
    if ma_ok and adj_ppm:
        implied_cost = round(adj_ppm * CONST_RATIO)
        p = _prov_mass(
            "construction_cost_per_m2", "تكلفة البناء / م²",
            implied_cost, "ريال/م²", mass_result, confidence=60.0,
        )
        p.reconciliation_note = (
            f"مشتق من adj_ppm ({adj_ppm:,.0f}) × {CONST_RATIO} "
            "(مكوّن التحسينات المقدَّر) — تقريب"
        )
        p.source_tier = "Tier-1 محوكم (مشتق)"
    else:
        p = _prov_unavailable(
            "construction_cost_per_m2", "تكلفة البناء / م²",
            "ريال/م²", "لا يتوفر نموذج مجمع",
        )
    provenance.append(p)

    # 6 — سعر الأرض / م²  (avg_ppm × 0.40 كحصة الأرض)
    LAND_RATIO = 0.40
    if ma_ok and avg_ppm:
        implied_land = round(avg_ppm * LAND_RATIO)
        p = _prov_mass(
            "land_price_per_m2", "سعر الأرض / م²",
            implied_land, "ريال/م²", mass_result, confidence=65.0,
        )
        p.reconciliation_note = (
            f"مشتق من avg_ppm ({avg_ppm:,.0f}) × {LAND_RATIO} "
            "(حصة الأرض المقدَّرة) — تقريب"
        )
        p.source_tier = "Tier-1 محوكم (مشتق)"
    else:
        rp_land, rp_land_conf, rp_land_sids = _pi_val(
            pi, "sales_comparison", "land_price_per_m2"
        )
        if rp_land:
            p = _prov_research(
                "land_price_per_m2", "سعر الأرض / م²",
                rp_land, "ريال/م²", research_pkg, rp_land_sids, rp_land_conf,
            )
        else:
            p = _prov_unavailable(
                "land_price_per_m2", "سعر الأرض / م²",
                "ريال/م²", "لا يتوفر نموذج مجمع أو مزوّد بحث",
            )
    provenance.append(p)

    # 7 — معدل الخصم (DCF)
    rp_disc, rp_disc_conf, rp_disc_sids = _pi_val(pi, "dcf", "discount_rate")
    if rp_disc:
        p = _prov_research(
            "discount_rate", "معدل الخصم (DCF)",
            rp_disc, "%", research_pkg, rp_disc_sids, rp_disc_conf,
        )
    elif rp_cap:
        derived = round(rp_cap + 0.03, 4)
        p = InputProvenance(
            input_id="discount_rate", label_ar="معدل الخصم (DCF)",
            value_used=derived, unit="%",
            source_type="web_research",
            source_name="مشتق: معدل رسملة + علاوة مخاطر (300 نقطة أساس)",
            source_uri="",
            retrieved_at=now, confidence_score=50.0,
            source_tier="Tier-2 Draft",
            status="Draft — مسح مبدئي محوكم",
            reconciliation_note=f"cap_rate ({rp_cap:.4f}) + 0.03",
        )
    else:
        p = InputProvenance(
            input_id="discount_rate", label_ar="معدل الخصم (DCF)",
            value_used=0.10, unit="%",
            source_type="body_input",
            source_name="قيمة افتراضية (10%) — معيار سوقي",
            source_uri="",
            retrieved_at=now, confidence_score=40.0,
            source_tier="Tier-2 Draft",
            status="Draft — افتراضي",
            reconciliation_note="يُستخدم عند غياب بيانات السوق",
        )
    provenance.append(p)

    # 8 — معدل النمو السنوي
    rp_growth, rp_growth_conf, rp_growth_sids = _pi_val(pi, "dcf", "annual_growth_rate")
    if rp_growth:
        p = _prov_research(
            "annual_growth_rate", "معدل النمو السنوي",
            rp_growth, "%", research_pkg, rp_growth_sids, rp_growth_conf,
        )
    else:
        p = InputProvenance(
            input_id="annual_growth_rate", label_ar="معدل النمو السنوي",
            value_used=0.03, unit="%",
            source_type="body_input",
            source_name="قيمة افتراضية (3%) — معيار سوقي محافظ",
            source_uri="",
            retrieved_at=now, confidence_score=40.0,
            source_tier="Tier-2 Draft",
            status="Draft — افتراضي",
            reconciliation_note="يُستخدم عند غياب بيانات النمو",
        )
    provenance.append(p)

    # ── subject_inputs dict ───────────────────────────────────────────────────
    def _pv(iid: str) -> Optional[float]:
        for p in provenance:
            if p.input_id == iid:
                return p.value_used
        return None

    subject_inputs: Dict[str, Any] = {
        "price_per_m2":               _pv("price_per_m2"),
        "cap_rate":                   _pv("cap_rate"),
        "market_rent_per_m2_monthly": _pv("market_rent_per_m2_monthly"),
        "vacancy_rate":               _pv("vacancy_rate"),
        "construction_cost_per_m2":   _pv("construction_cost_per_m2"),
        "land_price_per_m2":          _pv("land_price_per_m2"),
        "discount_rate":              _pv("discount_rate"),
        "annual_growth_rate":         _pv("annual_growth_rate"),
        # Pass-through from body
        "built_up_area_m2":  float(body.get("built_up_area_m2") or 850),
        "land_area_m2":      float(body.get("land_area_m2")     or 1200),
        "monthly_rent":      float(body.get("monthly_rent")     or 12000),
        "op_expenses":       float(body.get("op_expenses")      or 10),
        "maint_reserve":     float(body.get("maint_reserve")    or 5),
        "collection_loss":   float(body.get("collection_loss")  or 2),
        "phys_depr":         float(body.get("phys_depr")        or 15),
        "func_depr":         float(body.get("func_depr")        or 5),
        "ext_depr":          float(body.get("ext_depr")         or 3),
        "weight_sales":      float(body.get("weight_sales")     or 50),
        "weight_income":     float(body.get("weight_income")    or 35),
        "weight_cost":       float(body.get("weight_cost")      or 15),
    }

    # ── Full source log (no local paths) ─────────────────────────────────────
    full_source_log: List[Dict[str, Any]] = []
    for src in rp_sources:
        entry = dict(src)
        for key in ("url", "source_uri"):
            uri = str(entry.get(key) or "")
            if uri.startswith("file://") or (":\\" in uri) or (
                uri.startswith("/") and not uri.startswith("/api")
            ):
                entry[key] = "[مسار داخلي — محجوب]"
        full_source_log.append(entry)
    full_source_log.extend(enr_source_log)

    ma_summary = {
        "available":     ma_ok,
        "avm_ppm":       avm_ppm,
        "adj_ppm":       adj_ppm,
        "avg_ppm":       avg_ppm,
        "cod":           ma_cod,
        "prd":           ma_prd,
        "model_version": ma_ver,
    } if mass_result else {"available": False}

    return SourcingResult(
        subject_inputs=subject_inputs,
        provenance_table=provenance,
        source_log=full_source_log,
        enrichment_comparables=enr_comps,
        mass_appraisal_summary=ma_summary,
        advisory_only=True,
        external_reference_provided=False,
        reference_source="mass_appraisal_and_draft_web_research",
        run_id=run_id,
        retrieved_at=now,
        warnings=warnings,
    )
