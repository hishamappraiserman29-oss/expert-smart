"""
professional_valuation_methods.py — Method Analysis Workspace & Reconciliation (Phase E).

Endpoints (all JWT-protected):
  GET  /api/professional-valuation/methods/catalogue
  GET  /api/professional-valuation/requests/<id>/methods/context
  POST /api/professional-valuation/requests/<id>/methods/run
  GET  /api/professional-valuation/requests/<id>/methods/runs
  GET  /api/professional-valuation/requests/<id>/methods/runs/<run_id>
  POST /api/professional-valuation/requests/<id>/reconciliation

Storage (internal paths never exposed in API responses):
  instance/professional_valuation/method_runs/<request_id>.jsonl
  instance/professional_valuation/reconciliation/<request_id>.json

Phase E scope: advisory method calculations, reconciliation preview, method readiness gate.
  - No OCR, no Qdrant, no RAG, no external APIs.
  - production_ready defaults to False.
  - certification_ready always False in Phase E.
  - no_certified_output_generated always True.
"""
from __future__ import annotations

import json
import math
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── Storage ───────────────────────────────────────────────────────────────────

_BASE             = Path(__file__).parent / "instance" / "professional_valuation"
_RUNS_DIR         = _BASE / "method_runs"
_RECON_DIR        = _BASE / "reconciliation"
_COMP_DIR         = _BASE / "comparables"
_PRELIM_DIR       = _BASE / "preliminary_approvals"

for _d in (_RUNS_DIR, _RECON_DIR, _COMP_DIR, _PRELIM_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── ID validators ─────────────────────────────────────────────────────────────

_PVR_ID_RE  = re.compile(r"^PVR-\d{8}-[0-9A-F]{4}$")
_PVMR_ID_RE = re.compile(r"^PVMR-[0-9A-F]{8}$")

def _new_pvmr_id() -> str:
    return "PVMR-" + uuid.uuid4().hex[:8].upper()

def _new_pvrc_id() -> str:
    return "PVRC-" + uuid.uuid4().hex[:8].upper()

def _new_pvpa_id() -> str:
    return "PVPA-" + uuid.uuid4().hex[:8].upper()

# ── Method catalogue ──────────────────────────────────────────────────────────

METHOD_CATALOGUE: list[dict] = [
    {
        "method_key":      "sales_comparison",
        "method_label_ar": "مقارنة المبيعات",
        "required_inputs": ["area_m2", "approved_sales_comparables"],
        "optional_inputs": ["adjusted_price_per_m2"],
        "advisory_note":   "يتطلب مقارنات بيعية معتمدة للتحليل.",
    },
    {
        "method_key":      "rental_comparison",
        "method_label_ar": "مقارنة الإيجارات",
        "required_inputs": ["area_m2", "approved_rental_comparables"],
        "optional_inputs": ["adjusted_rent_per_m2"],
        "advisory_note":   "يتطلب مقارنات إيجارية معتمدة للتحليل.",
    },
    {
        "method_key":      "cost_approach",
        "method_label_ar": "نهج التكلفة",
        "required_inputs": ["construction_cost_per_m2", "land_price_per_m2"],
        "optional_inputs": ["effective_age", "economic_life", "physical_depreciation_percent",
                            "functional_obsolescence_percent", "external_obsolescence_percent"],
        "advisory_note":   "استشاري فقط — يتطلب تكلفة البناء وسعر الأرض.",
    },
    {
        "method_key":      "direct_capitalization",
        "method_label_ar": "الرسملة المباشرة",
        "required_inputs": ["cap_rate", "monthly_rent_or_annual_rent"],
        "optional_inputs": ["vacancy_rate", "operating_expense_rate"],
        "advisory_note":   "يتطلب معدل الرسملة وقيمة الإيجار.",
    },
    {
        "method_key":      "dcf",
        "method_label_ar": "التدفق النقدي المخصوم (DCF)",
        "required_inputs": ["discount_rate", "terminal_cap_rate", "starting_noi"],
        "optional_inputs": ["forecast_years", "rent_growth_rate", "vacancy_rate",
                            "expense_growth_rate", "exit_year"],
        "advisory_note":   "استشاري فقط — يتطلب معدل الخصم ومعدل الرسملة النهائية والدخل الصافي.",
    },
    {
        "method_key":      "land_residual",
        "method_label_ar": "الرسوب على الأرض / القيمة المتبقية",
        "required_inputs": ["construction_cost_per_m2", "indicated_value"],
        "optional_inputs": [],
        "advisory_note":   "استشاري فقط — يشترط توافر قيمة إجمالية وتكاليف بناء.",
    },
    {
        "method_key":      "mass_appraisal_reference",
        "method_label_ar": "مرجع التقييم الشامل (استشاري)",
        "required_inputs": ["area_m2"],
        "optional_inputs": ["zone_id", "property_type"],
        "advisory_note":   "استشاري فقط — لا توجد قاعدة بيانات إنتاجية في المرحلة الحالية.",
    },
]

_METHOD_KEYS: frozenset[str] = frozenset(m["method_key"] for m in METHOD_CATALOGUE)

# ── Approved-comparable filter ────────────────────────────────────────────────

_APPROVED_STATUSES: frozenset[str] = frozenset({
    "approved_for_analysis",
    "approved_as_production_comparable",
})

def _load_approved_comparables(request_id: str) -> list[dict]:
    """Return all non-QA approved comparables for a request."""
    path = _COMP_DIR / f"{request_id}.jsonl"
    if not path.exists():
        return []
    rows: list[dict] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("status") in _APPROVED_STATUSES:
                rows.append(rec)
    return rows


def _load_all_comparables(request_id: str) -> list[dict]:
    """Return all comparables (for context display, filtered in calculations)."""
    path = _COMP_DIR / f"{request_id}.jsonl"
    if not path.exists():
        return []
    rows: list[dict] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows

# ── Safe numeric helpers ──────────────────────────────────────────────────────

def _safe_float(v, default=None):
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f) or abs(f) > 1e15:
            return default
        return f
    except (TypeError, ValueError):
        return default


def _median(values: list[float]) -> float:
    s = sorted(values)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def _round2(v) -> Optional[float]:
    if v is None:
        return None
    return round(float(v), 2)

# ── Method calculations ───────────────────────────────────────────────────────

def _calc_sales_comparison(comps: list[dict], subject_inputs: dict) -> dict:
    sales = [c for c in comps if c.get("comparable_type") == "sales_comparable"
             and not c.get("qa_simulation")]
    qa_sales = [c for c in comps if c.get("comparable_type") == "sales_comparable"
                and c.get("qa_simulation")]

    if not sales and not qa_sales:
        return {
            "method_key": "sales_comparison",
            "method_label_ar": "مقارنة المبيعات",
            "method_status": "insufficient_data",
            "data_readiness": "no_approved_comparables",
            "comparable_ids_used": [],
            "warnings": ["لا توجد مقارنات بيعية معتمدة."],
            "production_ready": False,
        }

    use_comps = sales if sales else qa_sales
    is_qa_only = not bool(sales)

    prices = []
    adj_prices = []
    ids_used = []
    for c in use_comps:
        p = _safe_float(c.get("price_per_m2"))
        if p and p > 0:
            prices.append(p)
            ids_used.append(c.get("comparable_id", ""))
            ap = _safe_float(c.get("adjusted_price_per_m2"))
            if ap and ap > 0:
                adj_prices.append(ap)

    if not prices:
        return {
            "method_key": "sales_comparison",
            "method_label_ar": "مقارنة المبيعات",
            "method_status": "insufficient_data",
            "data_readiness": "no_price_per_m2_available",
            "comparable_ids_used": ids_used,
            "warnings": ["لا توجد قيم سعر/م² في المقارنات المعتمدة."],
            "production_ready": False,
        }

    avg = sum(prices) / len(prices)
    med = _median(prices)
    mn  = min(prices)
    mx  = max(prices)
    adj_avg = (sum(adj_prices) / len(adj_prices)) if adj_prices else None
    selected_p = adj_avg if adj_avg else avg

    area = _safe_float(subject_inputs.get("subject_area_m2"))
    indicated_value = _round2(selected_p * area) if area else None

    calc = {
        "average_price_per_m2":          _round2(avg),
        "median_price_per_m2":           _round2(med),
        "min_price_per_m2":              _round2(mn),
        "max_price_per_m2":              _round2(mx),
        "adjusted_average_price_per_m2": _round2(adj_avg),
        "selected_price_per_m2":         _round2(selected_p),
        "comparables_count":             len(use_comps),
    }

    warnings = []
    limitations = []
    if is_qa_only:
        warnings.append("المقارنات المستخدمة هي بيانات QA فقط — ليست إنتاجية.")
        limitations.append("qa_only_comparables")
    if not area:
        limitations.append("subject_area_missing — لا توجد قيمة إشارية إجمالية.")

    return {
        "method_key":           "sales_comparison",
        "method_label_ar":      "مقارنة المبيعات",
        "method_status":        "calculated",
        "data_readiness":       "qa_advisory" if is_qa_only else "production_advisory",
        "comparable_ids_used":  ids_used,
        "calculation_summary":  calc,
        "indicated_value":      indicated_value,
        "confidence_level":     "low" if is_qa_only else ("medium" if len(prices) < 3 else "high"),
        "reliability_score":    0.4 if is_qa_only else (0.6 if len(prices) < 3 else 0.85),
        "limitations":          limitations,
        "warnings":             warnings,
        "production_ready":     False,
    }


def _calc_rental_comparison(comps: list[dict], subject_inputs: dict) -> dict:
    rentals = [c for c in comps if c.get("comparable_type") == "rental_comparable"
               and not c.get("qa_simulation")]
    qa_rentals = [c for c in comps if c.get("comparable_type") == "rental_comparable"
                  and c.get("qa_simulation")]

    if not rentals and not qa_rentals:
        return {
            "method_key": "rental_comparison",
            "method_label_ar": "مقارنة الإيجارات",
            "method_status": "insufficient_data",
            "data_readiness": "no_approved_comparables",
            "comparable_ids_used": [],
            "warnings": ["لا توجد مقارنات إيجارية معتمدة."],
            "production_ready": False,
        }

    use_comps = rentals if rentals else qa_rentals
    is_qa_only = not bool(rentals)

    rents = []
    adj_rents = []
    ids_used = []
    for c in use_comps:
        r = _safe_float(c.get("rent_per_m2"))
        if r and r > 0:
            rents.append(r)
            ids_used.append(c.get("comparable_id", ""))
            ar = _safe_float(c.get("adjusted_rent_per_m2"))
            if ar and ar > 0:
                adj_rents.append(ar)

    if not rents:
        return {
            "method_key": "rental_comparison",
            "method_label_ar": "مقارنة الإيجارات",
            "method_status": "insufficient_data",
            "data_readiness": "no_rent_per_m2_available",
            "comparable_ids_used": ids_used,
            "warnings": ["لا توجد قيم إيجار/م² في المقارنات المعتمدة."],
            "production_ready": False,
        }

    avg = sum(rents) / len(rents)
    med = _median(rents)
    mn  = min(rents)
    mx  = max(rents)
    adj_avg = (sum(adj_rents) / len(adj_rents)) if adj_rents else None
    selected_r = adj_avg if adj_avg else avg

    area = _safe_float(subject_inputs.get("subject_area_m2"))
    indicated_monthly = _round2(selected_r * area) if area else None
    indicated_annual  = _round2(indicated_monthly * 12) if indicated_monthly else None

    calc = {
        "average_rent_per_m2":          _round2(avg),
        "median_rent_per_m2":           _round2(med),
        "min_rent_per_m2":              _round2(mn),
        "max_rent_per_m2":              _round2(mx),
        "adjusted_average_rent_per_m2": _round2(adj_avg),
        "selected_rent_per_m2":         _round2(selected_r),
        "comparables_count":            len(use_comps),
    }

    warnings = []
    limitations = []
    if is_qa_only:
        warnings.append("المقارنات المستخدمة هي بيانات QA فقط — ليست إنتاجية.")
        limitations.append("qa_only_comparables")
    if not area:
        limitations.append("subject_area_missing — لا توجد قيمة إشارية إجمالية.")

    return {
        "method_key":              "rental_comparison",
        "method_label_ar":         "مقارنة الإيجارات",
        "method_status":           "calculated",
        "data_readiness":          "qa_advisory" if is_qa_only else "production_advisory",
        "comparable_ids_used":     ids_used,
        "calculation_summary":     calc,
        "indicated_monthly_rent":  indicated_monthly,
        "indicated_annual_rent":   indicated_annual,
        "confidence_level":        "low" if is_qa_only else ("medium" if len(rents) < 3 else "high"),
        "reliability_score":       0.4 if is_qa_only else (0.6 if len(rents) < 3 else 0.85),
        "limitations":             limitations,
        "warnings":                warnings,
        "production_ready":        False,
    }


def _calc_cost_approach(subject_inputs: dict) -> dict:
    key = "cost_approach"
    label = "نهج التكلفة"

    cc  = _safe_float(subject_inputs.get("construction_cost_per_m2"))
    lp  = _safe_float(subject_inputs.get("land_price_per_m2"))
    ba  = _safe_float(subject_inputs.get("subject_area_m2"))
    la  = _safe_float(subject_inputs.get("land_area_m2")) or ba

    if not cc or not lp:
        return {
            "method_key": key, "method_label_ar": label,
            "method_status": "insufficient_data",
            "data_readiness": "missing_cost_or_land_price",
            "warnings": ["تكلفة البناء أو سعر الأرض مفقود."],
            "production_ready": False,
        }

    if not ba:
        return {
            "method_key": key, "method_label_ar": label,
            "method_status": "insufficient_data",
            "data_readiness": "missing_building_area",
            "warnings": ["مساحة المبنى مفقودة."],
            "production_ready": False,
        }

    rcn = ba * cc
    lv  = la * lp

    eff  = _safe_float(subject_inputs.get("effective_age"))
    life = _safe_float(subject_inputs.get("economic_life"))
    phys = _safe_float(subject_inputs.get("physical_depreciation_percent"))
    func = _safe_float(subject_inputs.get("functional_obsolescence_percent")) or 0.0
    ext  = _safe_float(subject_inputs.get("external_obsolescence_percent")) or 0.0

    limitations = []
    if phys is not None:
        dep_pct = phys + func + ext
    elif eff is not None and life is not None and life > 0:
        dep_pct = min((eff / life) * 100, 100.0)
    else:
        dep_pct = 0.0
        limitations.append("العمر الاقتصادي أو الاستهلاك مفقود — تم اعتماد استهلاك صفر.")

    dep_val = rcn * (dep_pct / 100.0)
    drc     = rcn - dep_val
    ind_val = lv + drc

    calc = {
        "replacement_cost_new":       _round2(rcn),
        "land_value":                 _round2(lv),
        "depreciation_percent":       _round2(dep_pct),
        "depreciation_value":         _round2(dep_val),
        "depreciated_replacement_cost": _round2(drc),
    }

    return {
        "method_key":          key,
        "method_label_ar":     label,
        "method_status":       "calculated",
        "data_readiness":      "advisory",
        "calculation_summary": calc,
        "indicated_value":     _round2(ind_val),
        "limitations":         limitations,
        "warnings":            (["المدخلات من مصادر غير إنتاجية أو تقديرية."]
                                if not limitations else []),
        "production_ready":    False,
    }


def _calc_direct_cap(subject_inputs: dict) -> dict:
    key   = "direct_capitalization"
    label = "الرسملة المباشرة"

    cap = _safe_float(subject_inputs.get("cap_rate"))
    if not cap or cap <= 0:
        return {
            "method_key": key, "method_label_ar": label,
            "method_status": "insufficient_data",
            "data_readiness": "missing_cap_rate",
            "warnings": ["معدل الرسملة مفقود أو صفر."],
            "production_ready": False,
        }

    monthly = _safe_float(subject_inputs.get("monthly_rent"))
    annual  = _safe_float(subject_inputs.get("annual_rent"))
    if annual and annual > 0:
        agi = annual
    elif monthly and monthly > 0:
        agi = monthly * 12
    else:
        return {
            "method_key": key, "method_label_ar": label,
            "method_status": "insufficient_data",
            "data_readiness": "missing_rent",
            "warnings": ["الإيجار الشهري أو السنوي مفقود."],
            "production_ready": False,
        }

    vac_rate  = _safe_float(subject_inputs.get("vacancy_rate")) or 0.0
    exp_rate  = _safe_float(subject_inputs.get("operating_expense_rate")) or 0.0

    vac_loss  = agi * (vac_rate / 100.0)
    egi       = agi - vac_loss
    op_exp    = egi * (exp_rate / 100.0)
    noi       = egi - op_exp
    ind_val   = noi / (cap / 100.0) if cap else None

    calc = {
        "annual_gross_income":  _round2(agi),
        "vacancy_loss":         _round2(vac_loss),
        "effective_gross_income": _round2(egi),
        "operating_expenses":   _round2(op_exp),
        "noi":                  _round2(noi),
        "cap_rate_used":        cap,
    }

    return {
        "method_key":          key,
        "method_label_ar":     label,
        "method_status":       "calculated",
        "data_readiness":      "advisory",
        "calculation_summary": calc,
        "indicated_value":     _round2(ind_val),
        "limitations":         ["معدل الرسملة تقديري — يحتاج مراجعة خبير."],
        "warnings":            [],
        "production_ready":    False,
    }


def _calc_dcf(subject_inputs: dict) -> dict:
    key   = "dcf"
    label = "التدفق النقدي المخصوم (DCF)"

    dr  = _safe_float(subject_inputs.get("discount_rate"))
    tcr = _safe_float(subject_inputs.get("terminal_cap_rate"))
    noi = _safe_float(subject_inputs.get("starting_noi"))

    if not dr or dr <= 0:
        return {
            "method_key": key, "method_label_ar": label,
            "method_status": "insufficient_data",
            "data_readiness": "missing_discount_rate",
            "warnings": ["معدل الخصم مفقود أو صفر."],
            "production_ready": False,
        }
    if not tcr or tcr <= 0:
        return {
            "method_key": key, "method_label_ar": label,
            "method_status": "insufficient_data",
            "data_readiness": "missing_terminal_cap_rate",
            "warnings": ["معدل الرسملة النهائية مفقود أو صفر."],
            "production_ready": False,
        }
    if not noi or noi <= 0:
        return {
            "method_key": key, "method_label_ar": label,
            "method_status": "insufficient_data",
            "data_readiness": "missing_starting_noi",
            "warnings": ["الدخل الصافي الابتدائي (NOI) مفقود أو صفر."],
            "production_ready": False,
        }

    years        = int(_safe_float(subject_inputs.get("forecast_years")) or 5)
    years        = max(1, min(years, 30))
    growth       = (_safe_float(subject_inputs.get("rent_growth_rate")) or 0.0) / 100.0
    vac_rate     = (_safe_float(subject_inputs.get("vacancy_rate")) or 0.0) / 100.0
    exp_growth   = (_safe_float(subject_inputs.get("expense_growth_rate")) or 0.0) / 100.0
    dr_dec       = dr / 100.0
    tcr_dec      = tcr / 100.0

    cf_rows = []
    total_pv = 0.0
    cur_noi  = noi
    for yr in range(1, years + 1):
        cf = cur_noi * (1 - vac_rate)
        df = 1.0 / ((1 + dr_dec) ** yr)
        pv = cf * df
        total_pv += pv
        cf_rows.append({
            "year":            yr,
            "noi":             _round2(cur_noi),
            "cash_flow":       _round2(cf),
            "discount_factor": round(df, 6),
            "present_value":   _round2(pv),
        })
        cur_noi = cur_noi * (1 + growth) * (1 + exp_growth if exp_growth else 1)

    terminal_noi = cur_noi
    terminal_val = terminal_noi / tcr_dec
    terminal_df  = 1.0 / ((1 + dr_dec) ** years)
    pv_terminal  = terminal_val * terminal_df
    total_dcf    = total_pv + pv_terminal

    calc = {
        "forecast_years":         years,
        "discount_rate":          dr,
        "terminal_cap_rate":      tcr,
        "yearly_cash_flows":      cf_rows,
        "pv_of_cash_flows":       _round2(total_pv),
        "terminal_value":         _round2(terminal_val),
        "pv_of_terminal_value":   _round2(pv_terminal),
    }

    return {
        "method_key":          key,
        "method_label_ar":     label,
        "method_status":       "calculated",
        "data_readiness":      "advisory",
        "calculation_summary": calc,
        "indicated_value":     _round2(total_dcf),
        "limitations":         ["افتراضات DCF تقديرية — تحتاج مراجعة خبير."],
        "warnings":            [],
        "production_ready":    False,
    }


def _calc_land_residual(subject_inputs: dict) -> dict:
    key   = "land_residual"
    label = "الرسوب على الأرض / القيمة المتبقية"

    cc  = _safe_float(subject_inputs.get("construction_cost_per_m2"))
    ba  = _safe_float(subject_inputs.get("subject_area_m2"))
    ind = _safe_float(subject_inputs.get("indicated_value_for_land_residual"))

    if not cc or not ba or not ind:
        return {
            "method_key": key, "method_label_ar": label,
            "method_status": "insufficient_data",
            "data_readiness": "missing_inputs",
            "warnings": ["تكلفة البناء أو القيمة الإجمالية مفقودة."],
            "production_ready": False,
        }

    building_cost = cc * ba
    land_residual = ind - building_cost

    calc = {
        "building_cost":  _round2(building_cost),
        "total_value":    _round2(ind),
        "land_residual":  _round2(land_residual),
    }

    return {
        "method_key":          key,
        "method_label_ar":     label,
        "method_status":       "calculated",
        "data_readiness":      "advisory",
        "calculation_summary": calc,
        "indicated_value":     _round2(land_residual),
        "limitations":         ["القيمة الإجمالية المدخلة استشارية."],
        "warnings":            [],
        "production_ready":    False,
    }


def _calc_mass_appraisal_ref(subject_inputs: dict) -> dict:
    area = _safe_float(subject_inputs.get("subject_area_m2"))
    return {
        "method_key":      "mass_appraisal_reference",
        "method_label_ar": "مرجع التقييم الشامل (استشاري)",
        "method_status":   "advisory_only",
        "data_readiness":  "no_production_dataset",
        "indicated_value": None,
        "limitations":     ["لا توجد قاعدة بيانات إنتاجية — نتيجة استشارية فقط."],
        "warnings":        ["هذه الطريقة استشارية ولا تُستخدم في الاستنتاج النهائي."],
        "production_ready": False,
    }


# ── Run all selected methods ──────────────────────────────────────────────────

def _run_methods(
    selected_methods: list[str],
    approved_comps: list[dict],
    subject_inputs: dict,
) -> list[dict]:
    results = []
    for mk in selected_methods:
        if mk not in _METHOD_KEYS:
            continue
        try:
            if mk == "sales_comparison":
                r = _calc_sales_comparison(approved_comps, subject_inputs)
            elif mk == "rental_comparison":
                r = _calc_rental_comparison(approved_comps, subject_inputs)
            elif mk == "cost_approach":
                r = _calc_cost_approach(subject_inputs)
            elif mk == "direct_capitalization":
                r = _calc_direct_cap(subject_inputs)
            elif mk == "dcf":
                r = _calc_dcf(subject_inputs)
            elif mk == "land_residual":
                r = _calc_land_residual(subject_inputs)
            elif mk == "mass_appraisal_reference":
                r = _calc_mass_appraisal_ref(subject_inputs)
            else:
                r = {
                    "method_key": mk, "method_status": "not_implemented",
                    "warnings": ["الطريقة غير مدعومة في المرحلة الحالية."],
                    "production_ready": False,
                }
        except Exception as exc:
            r = {
                "method_key":    mk,
                "method_status": "error",
                "warnings":      [f"خطأ داخلي: {exc}"],
                "production_ready": False,
            }
        results.append(r)
    return results


# ── Method readiness gate ─────────────────────────────────────────────────────

def evaluate_method_readiness(method_outputs: list[dict]) -> dict:
    completed    = [o for o in method_outputs if o.get("method_status") == "calculated"
                    and (o.get("indicated_value") or o.get("indicated_monthly_rent"))]
    insufficient = [o for o in method_outputs if o.get("method_status") == "insufficient_data"]
    advisory     = [o for o in method_outputs if o.get("method_status") == "advisory_only"]
    prod_ready   = []  # always empty in Phase E

    methods_completed = bool(completed)
    blockers: list[str] = []
    required_actions: list[str] = []

    if not methods_completed:
        blockers.append("لا توجد طرق تقييم مكتملة ببيانات كافية.")
        required_actions.append("أضف مقارنات معتمدة أو أدخل مدخلات الطريقة المطلوبة.")

    qa_only_methods = [o for o in completed
                       if o.get("data_readiness") in ("qa_advisory",)]
    if qa_only_methods:
        blockers.append("نتائج الطرق تعتمد على بيانات غير إنتاجية أو غير معتمدة.")

    return {
        "method_readiness_status":    "ready" if methods_completed else "incomplete",
        "selected_methods":           [o.get("method_key") for o in method_outputs],
        "completed_methods":          [o.get("method_key") for o in completed],
        "insufficient_methods":       [o.get("method_key") for o in insufficient],
        "production_ready_methods":   prod_ready,
        "advisory_methods":           [o.get("method_key") for o in advisory],
        "method_blockers":            blockers,
        "required_actions":           required_actions,
        "methods_completed":          methods_completed,
        "certification_method_ready": False,  # always False in Phase E
    }


# ── Reconciliation ────────────────────────────────────────────────────────────

def _build_reconciliation(
    method_outputs: list[dict],
    method_weights: dict,
    selected_final_value: Optional[float],
    rationale: str,
    expert_confirmation: bool,
) -> dict:
    # Collect methods with indicated values
    values: dict[str, float] = {}
    for o in method_outputs:
        mk  = o.get("method_key", "")
        val = _safe_float(o.get("indicated_value"))
        if val and val > 0 and o.get("method_status") == "calculated":
            values[mk] = val

    if not values:
        return {
            "weighted_value":                 None,
            "selected_final_value":           None,
            "selected_final_value_status":    "insufficient_data",
            "lower_bound":                    None,
            "upper_bound":                    None,
            "dispersion_analysis":            {},
            "coefficient_of_variation":       None,
            "divergence_flags":               ["لا توجد قيم تقييمية مكتملة للمقارنة."],
            "dominant_method":                None,
            "production_ready":               False,
            "certification_reconciliation_ready": False,
        }

    # Normalize weights
    raw_weights: dict[str, float] = {}
    for mk in values:
        w = _safe_float((method_weights or {}).get(mk)) or 0.0
        raw_weights[mk] = w

    total_w = sum(raw_weights.values())
    warnings_recon: list[str] = []
    if total_w <= 0:
        # Equal weights fallback
        eq = 100.0 / len(values)
        norm_weights = {mk: eq for mk in values}
        warnings_recon.append("لم يتم تحديد أوزان — تم اعتماد أوزان متساوية.")
    elif abs(total_w - 100.0) > 0.01:
        norm_weights = {mk: (w / total_w * 100) for mk, w in raw_weights.items()}
        warnings_recon.append(f"مجموع الأوزان {round(total_w,1)}% — تم التطبيع إلى 100%.")
    else:
        norm_weights = raw_weights

    weighted_sum = sum(values[mk] * (norm_weights.get(mk, 0) / 100.0) for mk in values)

    # Dispersion
    vals_list = list(values.values())
    mean_v    = sum(vals_list) / len(vals_list)
    if len(vals_list) > 1:
        variance = sum((v - mean_v) ** 2 for v in vals_list) / len(vals_list)
        std_dev  = math.sqrt(variance)
        cv       = (std_dev / mean_v * 100) if mean_v else 0.0
    else:
        std_dev = 0.0
        cv      = 0.0

    divergence_flags: list[str] = []
    if cv > 20:
        divergence_flags.append("تشتت عالٍ بين طرق التقييم — CV > 20%.")
    elif cv > 10:
        divergence_flags.append("تشتت متوسط بين طرق التقييم — CV بين 10%-20%.")

    dominant = max(norm_weights, key=lambda k: norm_weights.get(k, 0)) if norm_weights else None

    final_val = selected_final_value if (selected_final_value and selected_final_value > 0) else weighted_sum
    fv_status = ("expert_selected_pending_approval" if (selected_final_value and selected_final_value > 0)
                 else "system_recommended_pending_expert_confirmation")

    expert_status = "approved_for_analysis" if expert_confirmation else "draft"

    return {
        "selected_method_weights":        norm_weights,
        "method_values":                  values,
        "weighted_value":                 _round2(weighted_sum),
        "selected_final_value":           _round2(final_val),
        "selected_final_value_status":    fv_status,
        "lower_bound":                    _round2(min(vals_list)),
        "upper_bound":                    _round2(max(vals_list)),
        "dispersion_analysis": {
            "mean":    _round2(mean_v),
            "std_dev": _round2(std_dev),
            "cv_pct":  _round2(cv),
        },
        "coefficient_of_variation":       _round2(cv),
        "divergence_flags":               divergence_flags,
        "warnings":                       warnings_recon,
        "dominant_method":                dominant,
        "rationale":                      rationale or "",
        "expert_confirmation_required":   True,
        "expert_review_status":           expert_status,
        "production_ready":               False,
        "certification_reconciliation_ready": False,
    }


# ── JSONL persistence ─────────────────────────────────────────────────────────

def _append_run(request_id: str, rec: dict) -> None:
    path = _RUNS_DIR / f"{request_id}.jsonl"
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _read_runs(request_id: str) -> list[dict]:
    path = _RUNS_DIR / f"{request_id}.jsonl"
    if not path.exists():
        return []
    rows: list[dict] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    rows.reverse()
    return rows


def _read_run(request_id: str, run_id: str) -> Optional[dict]:
    for r in _read_runs(request_id):
        if r.get("method_run_id") == run_id:
            return r
    return None


def _save_reconciliation(request_id: str, rec: dict) -> None:
    path = _RECON_DIR / f"{request_id}.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=2)


def _read_reconciliation(request_id: str) -> Optional[dict]:
    path = _RECON_DIR / f"{request_id}.json"
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _save_preliminary_approval(request_id: str, rec: dict) -> None:
    path = _PRELIM_DIR / f"{request_id}.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=2)


def _read_preliminary_approval(request_id: str) -> Optional[dict]:
    path = _PRELIM_DIR / f"{request_id}.json"
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _run_safe(rec: dict) -> dict:
    """Strip internal paths; return API-safe run record."""
    return {k: v for k, v in rec.items() if k != "_internal"}


# ── Route registration ────────────────────────────────────────────────────────

def register_pv_method_routes(app, require_auth, limiter=None) -> None:
    """Register all Phase E method analysis routes."""
    from flask import jsonify, request as freq

    # Deferred import to avoid circular dependency
    def _load_request(request_id: str):
        try:
            from professional_valuation_routes import _read_pvr
            return _read_pvr(request_id)
        except Exception:
            return None

    # ── GET /methods/catalogue ────────────────────────────────────────────────
    @app.route("/api/professional-valuation/methods/catalogue", methods=["GET"])
    @require_auth
    def pv_methods_catalogue():
        return jsonify({"ok": True, "methods": METHOD_CATALOGUE}), 200

    # ── GET /requests/<id>/methods/context ────────────────────────────────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/methods/context",
        methods=["GET"],
    )
    @require_auth
    def pv_methods_context(request_id: str):
        if not _PVR_ID_RE.match(request_id):
            return jsonify({"ok": False, "error": "request_id غير صالح"}), 400
        req = _load_request(request_id)
        if not req:
            return jsonify({"ok": False, "error": "الطلب غير موجود"}), 404

        approved = _load_approved_comparables(request_id)
        all_comps = _load_all_comparables(request_id)
        latest_run = (_read_runs(request_id) or [None])[0]
        recon = _read_reconciliation(request_id)

        readiness = evaluate_method_readiness(
            latest_run.get("method_outputs", []) if latest_run else []
        )

        return jsonify({
            "ok":                   True,
            "request_id":           request_id,
            "approved_comparables": approved,
            "total_comparables":    len(all_comps),
            "method_readiness":     readiness,
            "latest_run":           _run_safe(latest_run) if latest_run else None,
            "reconciliation":       recon,
            "supported_methods":    [m["method_key"] for m in METHOD_CATALOGUE],
            "advisory_only_reason": (
                "Phase E — method analysis is advisory only. "
                "Does not generate certified reports."
            ),
        }), 200

    # ── POST /requests/<id>/methods/run ───────────────────────────────────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/methods/run",
        methods=["POST"],
    )
    @require_auth
    def pv_methods_run(request_id: str):
        if not _PVR_ID_RE.match(request_id):
            return jsonify({"ok": False, "error": "request_id غير صالح"}), 400
        req = _load_request(request_id)
        if not req:
            return jsonify({"ok": False, "error": "الطلب غير موجود"}), 404

        body = freq.get_json(silent=True) or {}
        selected_methods = body.get("selected_methods") or []
        subject_inputs   = body.get("subject_inputs") or {}
        method_weights   = body.get("method_weights") or {}
        notes            = str(body.get("notes") or "")[:1000]
        run_type         = str(body.get("run_type") or "advisory_calculation")

        if not isinstance(selected_methods, list) or not selected_methods:
            return jsonify({"ok": False, "error": "selected_methods مطلوب"}), 422

        invalid = [m for m in selected_methods if m not in _METHOD_KEYS]
        if invalid:
            return jsonify({
                "ok": False,
                "error": f"طرق غير معروفة: {invalid}",
            }), 422

        approved_comps = _load_approved_comparables(request_id)
        method_outputs = _run_methods(selected_methods, approved_comps, subject_inputs)
        readiness      = evaluate_method_readiness(method_outputs)

        recon_preview = _build_reconciliation(
            method_outputs, method_weights,
            selected_final_value=None, rationale="", expert_confirmation=False,
        )

        run_id = _new_pvmr_id()
        now    = datetime.utcnow().isoformat() + "Z"
        run_rec = {
            "method_run_id":            run_id,
            "request_id":               request_id,
            "created_at":               now,
            "run_type":                 run_type,
            "status":                   "calculated",
            "selected_methods":         selected_methods,
            "method_outputs":           method_outputs,
            "reconciliation_summary":   recon_preview,
            "readiness_summary":        readiness,
            "notes":                    notes,
            "warnings":                 [],
            "errors":                   [],
            "production_ready":         False,
            "expert_review_status":     "draft",
            "external_api_used":        False,
            "qdrant_used":              False,
            "rag_used":                 False,
            "no_certified_output_generated": True,
        }
        _append_run(request_id, run_rec)
        _save_reconciliation(request_id, {
            "reconciliation_id": _new_pvrc_id(),
            "request_id":        request_id,
            "created_at":        now,
            **recon_preview,
        })

        # Build updated gate summary (no circular import)
        gate = _build_gate_with_methods(request_id, req.get("valuation_purpose", ""),
                                        readiness, recon_preview)

        return jsonify({
            "ok":                   True,
            "method_run_id":        run_id,
            "method_outputs":       method_outputs,
            "reconciliation_preview": recon_preview,
            "method_readiness":     readiness,
            "certification_gate_summary": gate,
        }), 201

    # ── GET /requests/<id>/methods/runs ───────────────────────────────────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/methods/runs",
        methods=["GET"],
    )
    @require_auth
    def pv_methods_runs_list(request_id: str):
        if not _PVR_ID_RE.match(request_id):
            return jsonify({"ok": False, "error": "request_id غير صالح"}), 400
        runs = _read_runs(request_id)
        return jsonify({"ok": True, "runs": [_run_safe(r) for r in runs],
                        "total": len(runs)}), 200

    # ── GET /requests/<id>/methods/runs/<run_id> ──────────────────────────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/methods/runs/<run_id>",
        methods=["GET"],
    )
    @require_auth
    def pv_methods_run_detail(request_id: str, run_id: str):
        if not _PVR_ID_RE.match(request_id):
            return jsonify({"ok": False, "error": "request_id غير صالح"}), 400
        if not _PVMR_ID_RE.match(run_id):
            return jsonify({"ok": False, "error": "run_id غير صالح"}), 400
        run = _read_run(request_id, run_id)
        if not run:
            return jsonify({"ok": False, "error": "تشغيل غير موجود"}), 404
        return jsonify({"ok": True, "run": _run_safe(run)}), 200

    # ── POST /requests/<id>/preliminary-approval ─────────────────────────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/preliminary-approval",
        methods=["POST"],
    )
    @require_auth
    def pv_preliminary_approval(request_id: str):
        if not _PVR_ID_RE.match(request_id):
            return jsonify({"ok": False, "error": "request_id غير صالح"}), 400
        req = _load_request(request_id)
        if not req:
            return jsonify({"ok": False, "error": "الطلب غير موجود"}), 404

        body          = freq.get_json(silent=True) or {}
        method_run_id = str(body.get("method_run_id") or "").strip()
        approval_note = str(body.get("approval_note") or "").strip()

        if not method_run_id:
            return jsonify({"ok": False, "error": "method_run_id مطلوب"}), 422
        if not approval_note:
            return jsonify({"ok": False, "error": "approval_note مطلوب"}), 422

        run = _read_run(request_id, method_run_id) if _PVMR_ID_RE.match(method_run_id) else None
        if not run:
            return jsonify({"ok": False, "error": "تشغيل الطرق غير موجود"}), 404

        sufficient = [
            o for o in run.get("method_outputs", [])
            if o.get("method_status") == "calculated"
            and (o.get("indicated_value") or o.get("indicated_monthly_rent"))
        ]
        if not sufficient:
            return jsonify({
                "ok": False,
                "error": "لا توجد طرق تقييم مكتملة — لا يمكن الاعتماد المبدئي.",
            }), 422

        recon = _read_reconciliation(request_id)
        if not recon or recon.get("weighted_value") is None:
            return jsonify({
                "ok": False,
                "error": "لا يوجد توفيق معتمد — أضف توفيقاً أولاً.",
            }), 422

        now      = datetime.utcnow().isoformat() + "Z"
        prelim_id = _new_pvpa_id()
        warning_text = (
            "تقرير مبدئي معتمد داخلياً — "
            "غير صالح للاستخدام الرسمي أو الاعتماد النهائي"
        )

        prelim_rec = {
            "preliminary_approval_id":    prelim_id,
            "request_id":                 request_id,
            "method_run_id":              method_run_id,
            "reconciliation_id":          recon.get("reconciliation_id", ""),
            "approved_at":                now,
            "approval_note":              approval_note[:2000],
            "preliminary_approval_ready": True,
            "preliminary_use_allowed":    True,
            "official_use_allowed":       False,
            "certified_use_allowed":      False,
            "limitations": [
                "هذا اعتماد مبدئي داخلي فقط.",
                "لا يصلح للاستخدام الرسمي أو القانوني.",
                "لم تكتمل بوابات الاعتماد النهائي.",
            ],
            "warning_text":               warning_text,
            "certification_ready":        False,
            "production_ready":           False,
            "no_certified_output_generated": True,
        }
        _save_preliminary_approval(request_id, prelim_rec)

        readiness = evaluate_method_readiness(run.get("method_outputs", []))
        gate = _build_gate_with_methods(
            request_id, req.get("valuation_purpose", ""), readiness, recon,
        )

        return jsonify({
            "ok":                         True,
            "preliminary_approval_id":    prelim_id,
            "preliminary_approval_ready": True,
            "preliminary_use_allowed":    True,
            "official_use_allowed":       False,
            "certified_use_allowed":      False,
            "warning_text":               warning_text,
            "certification_gate_summary": gate,
        }), 200

    # ── POST /requests/<id>/reconciliation ───────────────────────────────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/reconciliation",
        methods=["POST"],
    )
    @require_auth
    def pv_reconciliation_save(request_id: str):
        if not _PVR_ID_RE.match(request_id):
            return jsonify({"ok": False, "error": "request_id غير صالح"}), 400
        req = _load_request(request_id)
        if not req:
            return jsonify({"ok": False, "error": "الطلب غير موجود"}), 404

        body                 = freq.get_json(silent=True) or {}
        method_weights       = body.get("method_weights") or {}
        selected_final_value = _safe_float(body.get("selected_final_value"))
        rationale            = str(body.get("rationale") or "")[:2000]
        expert_confirmation  = bool(body.get("expert_confirmation", False))

        # Load latest run outputs for reconciliation
        latest_run = (_read_runs(request_id) or [None])[0]
        method_outputs = latest_run.get("method_outputs", []) if latest_run else []

        recon = _build_reconciliation(
            method_outputs, method_weights,
            selected_final_value, rationale, expert_confirmation,
        )
        recon_rec = {
            "reconciliation_id": _new_pvrc_id(),
            "request_id":        request_id,
            "created_at":        datetime.utcnow().isoformat() + "Z",
            **recon,
        }
        _save_reconciliation(request_id, recon_rec)

        readiness = evaluate_method_readiness(method_outputs)
        gate = _build_gate_with_methods(request_id, req.get("valuation_purpose", ""),
                                        readiness, recon)

        return jsonify({
            "ok":                         True,
            "reconciliation":             recon_rec,
            "certification_gate_summary": gate,
        }), 200


# ── Gate helper (no circular imports) ────────────────────────────────────────

def _build_gate_with_methods(
    request_id: str,
    valuation_purpose: str,
    readiness: dict,
    recon: dict,
) -> dict:
    """Compose gate summary with Phase E fields. Never sets certification_ready=True."""
    try:
        from professional_valuation_routes import _get_gate_summary
        gate = _get_gate_summary(request_id, valuation_purpose)
    except Exception:
        gate = {
            "certification_ready":       False,
            "qa_data_cleared":           False,
            "real_sources_ready":        False,
            "mandatory_documents_ready": False,
            "comparables_ready":         False,
            "blockers":                  [],
            "advisory_only_reason":      "Phase E — advisory only.",
        }

    gate["methods_completed"]        = readiness.get("methods_completed", False)
    gate["reconciliation_completed"] = bool(recon and recon.get("weighted_value") is not None)
    gate["certification_ready"]      = False  # always False in Phase E

    # Preliminary approval fields (Phase E addendum)
    prelim = _read_preliminary_approval(request_id)
    gate["preliminary_approval_ready"] = bool(prelim and prelim.get("preliminary_approval_ready"))
    gate["preliminary_use_allowed"]    = bool(prelim and prelim.get("preliminary_use_allowed"))
    gate["certified_use_allowed"]      = False  # always False in Phase E

    if not gate["methods_completed"]:
        blocker = "لا توجد طرق تقييم مكتملة ببيانات كافية."
        if blocker not in gate.get("blockers", []):
            gate.setdefault("blockers", []).append(blocker)

    blockers = gate.setdefault("blockers", [])
    for b in ["مراجعة الأقران مطلوبة.", "التوقيع مطلوب."]:
        if b not in blockers:
            blockers.append(b)

    gate["advisory_only_reason"] = (
        "Phase E — method analysis is advisory only. "
        "Preliminary internal approval allowed; certified report generation blocked. "
        "certification_ready=false."
    )
    return gate


def evaluate_method_readiness_for_request(request_id: str) -> dict:
    """Public helper for gate integration in professional_valuation_routes."""
    latest_run = (_read_runs(request_id) or [None])[0]
    outputs = latest_run.get("method_outputs", []) if latest_run else []
    return evaluate_method_readiness(outputs)


def get_reconciliation_for_request(request_id: str) -> Optional[dict]:
    """Public helper for gate integration."""
    return _read_reconciliation(request_id)


def get_preliminary_approval_for_request(request_id: str) -> Optional[dict]:
    """Public helper for gate integration — returns preliminary approval record or None."""
    return _read_preliminary_approval(request_id)
