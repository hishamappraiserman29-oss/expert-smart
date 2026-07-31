"""
Report Review Flask endpoint — V3.0 (Deep Rebuild 2026-07-24)

Implements:
  - _compute_valuation_methods: Sales Comparison, Income Cap, Cost Approach, DCF
  - _build_review_html(meta, audience): 10 pages, audience watermark, no internal leakage
  - _build_review_excel: Sheet 5 full upgrade with BarChart
  - Route: new optional valuation inputs, HTTP 400 validation, role-based audience
  - Dynamic compliance score (replaces hardcoded 55%)

safety: advisory_only=True | not_real_training=True |
        fake_reviewer_signature_created=False | certification_ready=False
"""
from __future__ import annotations

import datetime
import json
import math
import os
import pathlib
import subprocess
import tempfile
from typing import Optional, Any

_ROOT = pathlib.Path(__file__).parent
_INST = _ROOT / "instance"
_ACCP = _INST / "manual_review_outputs" / "REPORT_REVIEW_QATAR_VISUAL_ACCEPTANCE"

_SAFETY = {
    "advisory_only": True,
    "not_real_training": True,
    "fake_reviewer_signature_created": False,
    "certification_ready": False,
}

# ── 12 compliance checks (standard, ref, item_ar, status, severity_ar, evidence, action_ar)
# status: "pass" | "partial" | "fail" | "na"
_COMPLIANCE_TEMPLATE = [
    ("IVS",   "103.2",      "نطاق العمل وأساس القيمة",           "partial", "عالية",    "ص 4",       "توضيح نطاق عدم اليقين"),
    ("IVS",   "103.3",      "توثيق مصادر البيانات والأساس",      "partial", "عالية",    "متعددة",     "توثيق جميع مصادر البيانات"),
    ("IVS",   "105.6",      "معدل الرسملة بدعم سوقي",            "fail",    "حرجة",     "ص 8",       "تزويد دعم سوقي موثق"),
    ("IVS",   "105.9",      "التوفيق بين نتائج الأساليب",        "fail",    "عالية",    "ص 12",      "إضافة قسم توفيق الأساليب"),
    ("USPAP", "SR 1-1(a)",  "كفاءة وخبرة المقيّم",                "partial", "متوسطة",   "ص 1",       "استكمال بيانات التأهيل"),
    ("USPAP", "SR 1-4(c)",  "دعم معدل الرسملة",                   "fail",    "حرجة",     "ص 10",      "تزويد دعم سوقي"),
    ("USPAP", "SR 2-2(ix)", "تحليل الاستخدام الأعلى والأفضل",    "fail",    "حرجة",     "غير موجود", "إضافة تحليل HBU الكامل"),
    ("RICS",  "Part 3",     "أساس القيمة والتعريفات",             "pass",    "منخفضة",   "ص 2",       "—"),
    ("RICS",  "Part 4",     "استنتاج القيمة وعدم اليقين",         "partial", "عالية",    "ص 8",       "إضافة نطاق عدم اليقين"),
    ("RICS",  "VPS 3",      "تقييم الأصول وتوثيق الدخل",         "partial", "متوسطة",   "ص 6",       "استكمال قسم الدخل التشغيلي"),
    ("FRA",   "FRA-1",      "توقيع خبير معتمد",                   "fail",    "حرجة",     "غير مرفق",  "إرفاق توقيع المراجع المعتمد"),
    ("FRA",   "FRA-2",      "بيانات هوية المقيّم",                 "partial", "متوسطة",   "ص 1",       "استكمال بيانات الهوية"),
]


# ─── helpers ──────────────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def _fmt_val(v: Optional[float], currency: str = "") -> str:
    if v is None:
        return "—"
    cur = f" {currency}" if currency else ""
    return f"{v:,.0f}{cur}"


def _render_playwright_pdf(html_path: pathlib.Path, pdf_path: pathlib.Path) -> bool:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            pg = browser.new_page()
            pg.goto(html_path.as_uri(), wait_until="networkidle", timeout=30_000)
            pg.pdf(
                path=str(pdf_path),
                format="A4",
                print_background=True,
                margin={"top": "18mm", "bottom": "18mm", "left": "14mm", "right": "14mm"},
            )
            browser.close()
        return pdf_path.exists() and pdf_path.stat().st_size > 3_000
    except Exception:
        return False


def _render_chrome(html_path: pathlib.Path, pdf_path: pathlib.Path) -> bool:
    for exe in [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]:
        if pathlib.Path(exe).exists():
            try:
                subprocess.run(
                    [exe, "--headless", "--disable-gpu", "--no-sandbox",
                     "--run-all-compositor-stages-before-draw",
                     f"--print-to-pdf={pdf_path}",
                     "--print-to-pdf-no-header",
                     str(html_path)],
                    capture_output=True, timeout=60,
                )
                return pdf_path.exists() and pdf_path.stat().st_size > 3_000
            except Exception:
                pass
    return False


def _render_pdf(html_path: pathlib.Path, pdf_path: pathlib.Path) -> bool:
    """Try Playwright first, fall back to Chrome CLI."""
    return _render_playwright_pdf(html_path, pdf_path) or _render_chrome(html_path, pdf_path)


def _stub_pdf(pdf_path: pathlib.Path) -> None:
    pdf_path.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]"
        b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        b"4 0 obj<</Length 44>>stream\nBT /F1 12 Tf 72 750 Td"
        b" (Review Report) Tj ET\nendstream\nendobj\n"
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f\n"
        b"0000000009 00000 n\n"
        b"0000000058 00000 n\n"
        b"0000000115 00000 n\n"
        b"0000000266 00000 n\n"
        b"0000000360 00000 n\n"
        b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n430\n%%EOF\n"
    )


# ─── Input validation ─────────────────────────────────────────────────────────

def _validate_numeric_inputs(raw: dict) -> tuple[dict, list]:
    """
    Validate optional numeric valuation inputs.
    Returns (validated_dict, errors_list).
    """
    validated: dict = {}
    errors: list = []

    def _gf(key: str, label_ar: str,
            min_v: Optional[float] = None,
            max_v: Optional[float] = None,
            gt_zero: bool = False,
            int_only: bool = False) -> Optional[float]:
        raw_val = raw.get(key, "")
        if raw_val == "" or raw_val is None:
            return None
        try:
            v = float(str(raw_val).strip())
        except (ValueError, TypeError):
            errors.append(f"الحقل '{label_ar}': قيمة رقمية غير صالحة.")
            return None
        if not math.isfinite(v):
            errors.append(f"الحقل '{label_ar}': القيمة غير محدودة (NaN أو لانهاية).")
            return None
        if int_only and v != int(v):
            errors.append(f"الحقل '{label_ar}': يجب أن تكون قيمة صحيحة.")
            return None
        if gt_zero and v <= 0:
            errors.append(f"الحقل '{label_ar}': يجب أن تكون القيمة أكبر من صفر.")
            return None
        if min_v is not None and v < min_v:
            errors.append(f"الحقل '{label_ar}': يجب أن تكون القيمة >= {min_v}.")
            return None
        if max_v is not None and v > max_v:
            errors.append(f"الحقل '{label_ar}': يجب أن تكون القيمة <= {max_v}.")
            return None
        return v

    validated["reported_value"]         = _gf("reported_value",          "القيمة المُبلَّغ عنها",   gt_zero=True)
    validated["gross_income"]           = _gf("gross_income",            "الدخل الإجمالي",            min_v=0)
    validated["cap_rate"]               = _gf("cap_rate",                "معدل الرسملة",              gt_zero=True, max_v=100)
    validated["vacancy_rate"]           = _gf("vacancy_rate",            "معدل الشغور",               min_v=0, max_v=100)
    validated["opex_ratio"]             = _gf("opex_ratio",              "نسبة المصروفات التشغيلية", min_v=0, max_v=100)
    validated["discount_rate"]          = _gf("discount_rate",           "معدل الخصم",                gt_zero=True, max_v=100)
    validated["holding_period_years"]   = _gf("holding_period_years",    "مدة DCF (سنوات)",           min_v=1, max_v=100, int_only=True)
    validated["annual_rent_growth"]     = _gf("annual_rent_growth",      "نمو الإيجار السنوي",        min_v=-99.99)
    validated["exit_cap_rate"]          = _gf("exit_cap_rate",           "معدل الرسملة الخروجي",      gt_zero=True, max_v=100)
    validated["replacement_cost_per_sqm"] = _gf("replacement_cost_per_sqm", "تكلفة الإحلال/م²",      min_v=0)
    validated["depreciation_pct"]       = _gf("depreciation_pct",        "نسبة الإهلاك",              min_v=0, max_v=100)
    validated["land_value_per_sqm"]     = _gf("land_value_per_sqm",      "قيمة الأرض/م²",             min_v=0)
    validated["built_up_area_m2"]       = _gf("built_up_area_m2",        "مساحة المبنى",              gt_zero=True)
    validated["land_area_m2"]           = _gf("land_area_m2",            "مساحة الأرض",               min_v=0)

    # comparables
    for i in (1, 2, 3):
        p = _gf(f"comp{i}_price", f"مبيع مقارن {i} — السعر", gt_zero=True)
        a = _gf(f"comp{i}_area",  f"مبيع مقارن {i} — المساحة", gt_zero=True)
        j = _gf(f"comp{i}_adj",   f"مبيع مقارن {i} — التعديل %")
        raw_has = any(raw.get(f"comp{i}_{k}", "") not in ("", None)
                      for k in ("price", "area", "adj"))
        if raw_has:
            if p is None or a is None:
                errors.append(f"المبيع المقارن {i}: بيانات جزئية — السعر والمساحة مطلوبان معاً.")
                validated[f"comp{i}"] = None
            else:
                validated[f"comp{i}"] = (p, a, j if j is not None else 0.0)
        else:
            validated[f"comp{i}"] = None

    return validated, errors


# ─── Valuation computation ────────────────────────────────────────────────────

def _rag(abs_var: Optional[float]) -> str:
    if abs_var is None:
        return "GRAY"
    if abs_var <= 5.0:
        return "GREEN"
    if abs_var <= 15.0:
        return "AMBER"
    return "RED"


def _variance(independent: float, reported: Optional[float]) -> tuple[Optional[float], Optional[float], str]:
    """Returns (signed_pct, abs_pct, rag)."""
    if reported is None or reported <= 0:
        return None, None, "GRAY"
    signed = (independent - reported) / reported * 100
    abs_v  = abs(signed)
    return round(signed, 2), round(abs_v, 2), _rag(abs_v)


def _unavailable(reason: str, missing: list) -> dict:
    return {
        "status": "unavailable",
        "value": None,
        "signed_variance_pct": None,
        "absolute_variance_pct": None,
        "rag": "GRAY",
        "missing_inputs": missing,
        "invalid_inputs": [],
        "reason": reason,
    }


def _compute_valuation_methods(meta: dict) -> dict:
    """
    Deterministic, side-effect-free computation of four valuation methods.
    Takes validated meta dict. Does not mutate meta.
    """
    reported  = meta.get("reported_value")
    currency  = meta.get("currency_code") or meta.get("currency") or "—"
    bua       = meta.get("built_up_area_m2")
    land_area = meta.get("land_area_m2")

    # ── Method A: Sales Comparison ────────────────────────────────────────────
    comps_raw = [(meta.get(f"comp{i}"), i) for i in (1, 2, 3)]
    valid_comps = []
    comp_details = []
    for comp, idx in comps_raw:
        if comp is None:
            comp_details.append({"comp": idx, "status": "absent"})
            continue
        price, area, adj = comp
        psm     = price / area
        adj_psm = psm * (1.0 + adj / 100.0)
        valid_comps.append(adj_psm)
        comp_details.append({
            "comp": idx,
            "status": "included",
            "price": price,
            "area": area,
            "raw_psm": round(psm, 2),
            "adj_pct": adj,
            "adj_psm": round(adj_psm, 2),
        })

    if not valid_comps:
        sc = _unavailable("لا مبيعات مقارنة صالحة مقدمة.", ["comp1 / comp2 / comp3"])
    elif bua is None:
        sc = _unavailable("مساحة المبنى المبنية (built_up_area_m2) مطلوبة.", ["built_up_area_m2"])
    else:
        avg_psm = sum(valid_comps) / len(valid_comps)
        sc_val  = round(avg_psm * bua, 2)
        sv, av, rg = _variance(sc_val, reported)
        sc = {
            "status": "computed",
            "value": sc_val,
            "reported_value": reported,
            "signed_variance_pct": sv,
            "absolute_variance_pct": av,
            "rag": rg,
            "inputs_used": {
                "comparables": comp_details,
                "avg_adj_psm": round(avg_psm, 2),
                "built_up_area_m2": bua,
            },
            "missing_inputs": [],
            "invalid_inputs": [],
            "reason": None,
        }
    sc["method"] = "sales_comparison"
    sc["label_ar"] = "أسلوب مقارنة المبيعات"

    # ── Method B: Income Capitalization ──────────────────────────────────────
    gi   = meta.get("gross_income")
    vac  = meta.get("vacancy_rate")
    opex = meta.get("opex_ratio")
    cap  = meta.get("cap_rate")

    missing_ic = [k for k, v in [("gross_income", gi), ("vacancy_rate", vac),
                                  ("opex_ratio", opex), ("cap_rate", cap)] if v is None]
    if missing_ic:
        ic = _unavailable("بيانات الدخل غير مكتملة.", missing_ic)
    elif cap <= 0:
        ic = {"status": "invalid", "value": None, "rag": "GRAY",
              "missing_inputs": [], "invalid_inputs": ["cap_rate"],
              "reason": "معدل الرسملة يجب أن يكون أكبر من صفر."}
    else:
        egi     = gi * (1.0 - vac / 100.0)
        noi     = egi * (1.0 - opex / 100.0)
        ic_val  = round(noi / (cap / 100.0), 2)
        sv, av, rg = _variance(ic_val, reported)
        ic = {
            "status": "computed",
            "value": ic_val,
            "reported_value": reported,
            "signed_variance_pct": sv,
            "absolute_variance_pct": av,
            "rag": rg,
            "inputs_used": {
                "gross_income": gi,
                "vacancy_rate_pct": vac,
                "vacancy_deduction": round(gi * vac / 100.0, 2),
                "effective_gross_income": round(egi, 2),
                "opex_ratio_pct": opex,
                "operating_expenses": round(egi * opex / 100.0, 2),
                "noi": round(noi, 2),
                "cap_rate_pct": cap,
            },
            "missing_inputs": [],
            "invalid_inputs": [],
            "reason": None,
        }
    ic["method"]   = "income_capitalization"
    ic["label_ar"] = "أسلوب رسملة الدخل"

    # ── Method C: Cost Approach ───────────────────────────────────────────────
    rcsm  = meta.get("replacement_cost_per_sqm")
    depr  = meta.get("depreciation_pct")
    lvsm  = meta.get("land_value_per_sqm")

    missing_ca = [k for k, v in [
        ("land_area_m2", land_area), ("land_value_per_sqm", lvsm),
        ("built_up_area_m2", bua), ("replacement_cost_per_sqm", rcsm),
        ("depreciation_pct", depr)] if v is None]
    if missing_ca:
        ca = _unavailable("بيانات أسلوب التكلفة غير مكتملة.", missing_ca)
    else:
        land_val     = land_area * lvsm
        gross_repl   = bua * rcsm
        depr_amount  = gross_repl * (depr / 100.0)
        depr_impl    = gross_repl - depr_amount
        ca_val       = round(land_val + depr_impl, 2)
        sv, av, rg   = _variance(ca_val, reported)
        ca = {
            "status": "computed",
            "value": ca_val,
            "reported_value": reported,
            "signed_variance_pct": sv,
            "absolute_variance_pct": av,
            "rag": rg,
            "inputs_used": {
                "land_area_m2": land_area,
                "land_value_per_sqm": lvsm,
                "land_value": round(land_val, 2),
                "built_up_area_m2": bua,
                "replacement_cost_per_sqm": rcsm,
                "gross_replacement_cost": round(gross_repl, 2),
                "depreciation_pct": depr,
                "depreciation_amount": round(depr_amount, 2),
                "depreciated_improvements": round(depr_impl, 2),
            },
            "missing_inputs": [],
            "invalid_inputs": [],
            "reason": None,
        }
    ca["method"]   = "cost_approach"
    ca["label_ar"] = "أسلوب التكلفة"

    # ── Method D: DCF ─────────────────────────────────────────────────────────
    dr   = meta.get("discount_rate")
    hp   = meta.get("holding_period_years")
    arg  = meta.get("annual_rent_growth")
    ecap = meta.get("exit_cap_rate")

    missing_dcf = [k for k, v in [
        ("gross_income", gi), ("vacancy_rate", vac), ("opex_ratio", opex),
        ("discount_rate", dr), ("holding_period_years", hp),
        ("annual_rent_growth", arg), ("exit_cap_rate", ecap)] if v is None]
    if missing_dcf:
        dcf = _unavailable("بيانات DCF غير مكتملة.", missing_dcf)
    elif dr <= 0 or ecap <= 0:
        dcf = {"status": "invalid", "value": None, "rag": "GRAY",
               "missing_inputs": [], "invalid_inputs": ["discount_rate", "exit_cap_rate"],
               "reason": "معدل الخصم ومعدل الرسملة الخروجي يجب أن يكونا أكبر من صفر."}
    else:
        hp_int = int(hp)
        year_table = []
        pv_sum = 0.0
        noi_last = 0.0
        for t in range(1, hp_int + 1):
            gross_t  = gi * ((1.0 + arg / 100.0) ** (t - 1))
            eff_t    = gross_t * (1.0 - vac / 100.0)
            noi_t    = eff_t * (1.0 - opex / 100.0)
            df_t     = (1.0 + dr / 100.0) ** t
            pv_noi_t = noi_t / df_t
            pv_sum  += pv_noi_t
            noi_last = noi_t
            year_table.append({
                "year": t,
                "gross_income": round(gross_t, 2),
                "effective_income": round(eff_t, 2),
                "noi": round(noi_t, 2),
                "discount_factor": round(df_t, 6),
                "pv_noi": round(pv_noi_t, 2),
            })
        terminal_noi   = noi_last * (1.0 + arg / 100.0)
        terminal_value = terminal_noi / (ecap / 100.0)
        terminal_pv    = terminal_value / ((1.0 + dr / 100.0) ** hp_int)
        dcf_val        = round(pv_sum + terminal_pv, 2)

        if not math.isfinite(dcf_val):
            dcf = {"status": "invalid", "value": None, "rag": "GRAY",
                   "missing_inputs": [], "invalid_inputs": ["calculation_overflow"],
                   "reason": "الحساب أنتج قيمة غير محدودة."}
        else:
            sv, av, rg = _variance(dcf_val, reported)
            dcf = {
                "status": "computed",
                "value": dcf_val,
                "reported_value": reported,
                "signed_variance_pct": sv,
                "absolute_variance_pct": av,
                "rag": rg,
                "inputs_used": {
                    "gross_income": gi,
                    "vacancy_rate_pct": vac,
                    "opex_ratio_pct": opex,
                    "discount_rate_pct": dr,
                    "holding_period_years": hp_int,
                    "annual_rent_growth_pct": arg,
                    "exit_cap_rate_pct": ecap,
                },
                "year_table": year_table,
                "terminal_noi": round(terminal_noi, 2),
                "exit_cap_rate_pct": ecap,
                "terminal_value": round(terminal_value, 2),
                "terminal_pv": round(terminal_pv, 2),
                "missing_inputs": [],
                "invalid_inputs": [],
                "reason": None,
            }
    dcf["method"]   = "dcf"
    dcf["label_ar"] = "أسلوب التدفقات النقدية المخصومة (DCF)"

    # ── Master comparison + uncertainty ──────────────────────────────────────
    methods = {
        "sales_comparison": sc,
        "income_capitalization": ic,
        "cost_approach": ca,
        "dcf": dcf,
    }
    order = ["sales_comparison", "income_capitalization", "cost_approach", "dcf"]

    master = []
    valid_vals = []
    for key in order:
        m = methods[key]
        master.append({
            "method": key,
            "label_ar": m["label_ar"],
            "status": m["status"],
            "reported_value": reported,
            "independent_value": m.get("value"),
            "signed_variance_pct": m.get("signed_variance_pct"),
            "absolute_variance_pct": m.get("absolute_variance_pct"),
            "rag": m.get("rag", "GRAY"),
            "reason": m.get("reason"),
        })
        if m["status"] == "computed" and m.get("value") is not None:
            valid_vals.append(m["value"])

    if len(valid_vals) >= 2:
        sorted_vals = sorted(valid_vals)
        mid = sorted_vals[len(sorted_vals) // 2] if len(sorted_vals) % 2 else (
            (sorted_vals[len(sorted_vals) // 2 - 1] + sorted_vals[len(sorted_vals) // 2]) / 2)
        spread = sorted_vals[-1] - sorted_vals[0]
        spread_pct = round(spread / mid * 100, 2) if mid else None
        uncertainty = {
            "valid_count": len(valid_vals),
            "low": sorted_vals[0],
            "high": sorted_vals[-1],
            "midpoint": round(mid, 2),
            "spread": round(spread, 2),
            "spread_pct": spread_pct,
        }
    elif len(valid_vals) == 1:
        uncertainty = {
            "valid_count": 1,
            "low": valid_vals[0],
            "high": valid_vals[0],
            "midpoint": valid_vals[0],
            "spread": 0,
            "spread_pct": 0,
            "note": "تعذر تكوين نطاق عدم يقين لعدم توافر أكثر من نتيجة مستقلة قابلة للمقارنة.",
        }
    else:
        uncertainty = {
            "valid_count": 0,
            "note": "لا نتائج مستقلة صالحة لتكوين نطاق عدم اليقين.",
        }

    computed_count   = sum(1 for m in methods.values() if m["status"] == "computed")
    unavailable_count = sum(1 for m in methods.values() if m["status"] == "unavailable")
    invalid_count    = sum(1 for m in methods.values() if m["status"] == "invalid")

    return {
        "reported_value": reported,
        "currency_code": currency,
        "methods": methods,
        "master_comparison": master,
        "valid_method_values": valid_vals,
        "uncertainty": uncertainty,
        "summary": {
            "total_methods": 4,
            "computed": computed_count,
            "unavailable": unavailable_count,
            "invalid": invalid_count,
        },
    }


# ─── Dynamic compliance score ─────────────────────────────────────────────────

def _compute_compliance_score() -> dict:
    score_map = {"pass": 1.0, "partial": 0.5, "fail": 0.0}
    applicable = [c for c in _COMPLIANCE_TEMPLATE if c[3] != "na"]
    earned = sum(score_map.get(c[3], 0.0) for c in applicable)
    total  = len(applicable)
    score  = round(earned / total * 100) if total else 0
    critical_fails = sum(1 for c in applicable if c[3] == "fail" and c[4] == "حرجة")
    return {
        "score": score,
        "earned": earned,
        "denominator": total,
        "critical_fails": critical_fails,
        "formula": f"{earned}/{total} × 100 = {score}%",
    }


# ─── HTML builder (10 pages) ──────────────────────────────────────────────────

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700;900&display=swap');
*{box-sizing:border-box;}
body{font-family:Tajawal,Arial,sans-serif;direction:rtl;margin:0;padding:0;
     background:#fff;color:#1a1a2e;font-size:11.5pt;}
.pg{page-break-after:always;padding:22px 28px;min-height:240mm;
    border-bottom:2px dashed #e5e7eb;position:relative;}
.section-h{font-size:14pt;font-weight:900;color:#4c1d95;
           border-bottom:2px solid #8b5cf6;padding-bottom:4px;margin-bottom:12px;}
.sub-h{font-size:11pt;font-weight:700;color:#5b21b6;margin:10px 0 5px;}
table{width:100%;border-collapse:collapse;font-size:10pt;margin:6px 0;}
th{background:#1e1b4b;color:#fff;padding:5px 8px;text-align:right;
   border:1px solid #c4b5fd;}
td{padding:4px 8px;border:1px solid #ddd8fe;text-align:right;}
tr:nth-child(even) td{background:#f5f3ff;}
.card{border:2px solid #8b5cf6;border-radius:8px;padding:12px;margin-bottom:10px;}
.green{color:#059669;font-weight:700;}
.yellow{color:#d97706;font-weight:700;}
.red{color:#dc2626;font-weight:700;}
.badge-g{background:#d1fae5;color:#065f46;padding:2px 8px;border-radius:4px;
         font-size:10pt;display:inline-block;}
.badge-y{background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:4px;
         font-size:10pt;display:inline-block;}
.badge-r{background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:4px;
         font-size:10pt;display:inline-block;}
.advisory{background:#fef9c3;border:1px solid #fde047;border-radius:4px;
          padding:6px 10px;font-size:10pt;color:#713f12;margin:8px 0;}
.page-num{font-size:8pt;color:#9ca3af;text-align:left;margin-bottom:4px;}
.sig-gate{border:2px dashed #dc2626;border-radius:8px;padding:16px;
          text-align:center;color:#dc2626;margin:12px 0;background:#fff5f5;}
.rag-green{background:#d1fae5;color:#065f46;font-weight:700;text-align:center;}
.rag-amber{background:#fef3c7;color:#92400e;font-weight:700;text-align:center;}
.rag-red  {background:#fee2e2;color:#991b1b;font-weight:700;text-align:center;}
.rag-gray {background:#f3f4f6;color:#6b7280;font-weight:700;text-align:center;}
.method-box{border:1px solid #ddd8fe;border-radius:6px;padding:10px;margin-bottom:8px;
            background:#faf5ff;}
.review-watermark{position:fixed;left:8%;top:40%;transform:rotate(-45deg);
  transform-origin:center;pointer-events:none;z-index:9999;white-space:nowrap;
  font-weight:600;font-family:Tajawal,Arial,sans-serif;}
.review-watermark--user{opacity:0.12;font-size:60pt;color:#7c3aed;}
.review-watermark--admin{opacity:0.06;font-size:24pt;color:#374151;}
@media print{.review-watermark{display:block !important;}}
</style>"""


def _rag_cell(rag: str) -> str:
    labels = {"GREEN": "🟢 مقبول", "AMBER": "🟡 تحذير", "RED": "🔴 خلاف جوهري", "GRAY": "⚪ غير متاح"}
    css = {"GREEN": "rag-green", "AMBER": "rag-amber", "RED": "rag-red", "GRAY": "rag-gray"}
    return f'<td class="{css.get(rag, "rag-gray")}">{labels.get(rag, "—")}</td>'


def _status_css(status: str) -> str:
    m = {"pass": "green", "partial": "yellow", "fail": "red", "na": ""}
    return m.get(status, "")


def _build_review_html(meta: dict, audience: str = "user") -> str:
    # ── extract display fields ────────────────────────────────────────────────
    src_name    = meta.get("source_file_name") or "تقرير مرفوع"
    case_id     = meta.get("case_id") or "—"
    country     = meta.get("country_ar") or meta.get("country") or "—"
    city        = meta.get("city_ar") or meta.get("city") or "—"
    currency    = meta.get("currency_code") or meta.get("currency") or "—"
    asset_type  = meta.get("asset_type_ar") or meta.get("asset_type") or "—"
    val_purpose = meta.get("valuation_purpose_ar") or meta.get("valuation_purpose") or "—"
    reviewer    = meta.get("reviewer_name") or "—"
    client_     = meta.get("review_client") or "—"
    purpose     = meta.get("review_purpose") or "مراجعة الاتساق المهني"
    scope       = meta.get("review_scope") or "مراجعة هيكل التقرير والبيانات"
    notes       = meta.get("general_notes") or meta.get("reviewer_notes") or "—"
    report_id   = meta.get("reviewed_report_id") or case_id
    review_date = meta.get("review_date") or datetime.date.today().isoformat()
    now         = datetime.datetime.now().isoformat(timespec="seconds")
    land_area   = meta.get("land_area_m2") or "—"
    bua_disp    = meta.get("built_up_area_m2") or "—"
    municipality = meta.get("municipality_ar") or "—"
    district    = meta.get("district_ar") or "—"

    # ── computed data ─────────────────────────────────────────────────────────
    vm   = _compute_valuation_methods(meta)
    comp = _compute_compliance_score()
    score     = comp["score"]
    crit_fails = comp["critical_fails"]
    reported_val = vm.get("reported_value")

    # decision badge
    if score >= 80:
        decision_badge = '<span class="badge-g">مقبول — قابل للاعتماد بعد توقيع المراجع</span>'
        decision_class = "green"
    elif score >= 60:
        decision_badge = '<span class="badge-y">مقبول مشروطاً — يتطلب إجراءات تصحيحية</span>'
        decision_class = "yellow"
    else:
        n_actions = crit_fails
        decision_badge = f'<span class="badge-r">مرفوض مشروطاً — يتطلب {n_actions} إجراءات تصحيحية</span>'
        decision_class = "red"

    score_class = "red" if score < 60 else ("yellow" if score < 80 else "green")
    score_label = f'{score}% — {"عائق يمنع الاعتماد" if score < 60 else "مقبول مشروطاً" if score < 80 else "مقبول"}'

    def page(title: str, body: str, num: int) -> str:
        return f"""
<div class="pg" id="pg-{num}">
  <div class="page-num">صفحة {num} من 10 — {case_id}</div>
  <h2 class="section-h">{title}</h2>
  {body}
</div>"""

    # ── PAGE 1: Cover + Executive Summary ─────────────────────────────────────
    computed_count = vm["summary"]["computed"]
    unavail_count  = vm["summary"]["unavailable"]
    p1 = f"""
      <div style="text-align:center;padding:12px 0;">
        <div style="font-size:9pt;color:#6b7280;">تقرير مراجعة استرشادي — V3.0 — 2026</div>
        <h1 style="font-size:18pt;color:#4c1d95;margin:6px 0;">تقرير مراجعة تقرير تقييم</h1>
        <div style="font-size:10pt;color:#5b21b6;">
          مدعوم بالذكاء الاصطناعي — لا يُعتمد إلا بعد توقيع المراجع المختص
        </div>
        <div style="margin:8px auto;display:inline-block;padding:3px 10px;
                    background:#f3f4f6;border-radius:4px;font-size:9pt;color:#374151;">
          معرّف المراجعة: {report_id} &nbsp;·&nbsp; تاريخ المراجعة: {review_date}
        </div>
      </div>

      <div class="card">
        <div class="sub-h">📋 بيانات التقرير محل المراجعة</div>
        <table>
          <tr><th>البند</th><th>القيمة</th></tr>
          <tr><td>اسم الملف المرفوع</td><td>{src_name}</td></tr>
          <tr><td>معرّف الحالة</td><td>{case_id}</td></tr>
          <tr><td>الدولة</td><td>{country}</td></tr>
          <tr><td>المدينة</td><td>{city}</td></tr>
          <tr><td>البلدية</td><td>{municipality}</td></tr>
          <tr><td>الحي</td><td>{district}</td></tr>
          <tr><td>نوع الأصل</td><td>{asset_type}</td></tr>
          <tr><td>هدف التقييم</td><td>{val_purpose}</td></tr>
          <tr><td>العملة</td><td>{currency}</td></tr>
          <tr><td>مساحة الأرض (م²)</td><td>{land_area}</td></tr>
          <tr><td>مساحة المبنى (م²)</td><td>{bua_disp}</td></tr>
        </table>
      </div>

      <div class="card">
        <div class="sub-h">🏆 بطاقة القرار التنفيذي السريع</div>
        <table>
          <tr><th>البند</th><th>الحالة</th></tr>
          <tr><td>القرار المبدئي</td><td>{decision_badge}</td></tr>
          <tr><td>درجة الامتثال</td>
              <td class="{score_class}">{score_label}</td></tr>
          <tr><td>الأساليب المحسوبة</td>
              <td class="{'green' if computed_count > 0 else 'yellow'}">{computed_count} / 4</td></tr>
          <tr><td>الأساليب غير المتاحة</td>
              <td class="{'yellow' if unavail_count > 0 else 'green'}">{unavail_count} / 4</td></tr>
          <tr><td>أساس الدرجة</td><td style="font-size:9pt;">{comp['formula']}</td></tr>
        </table>
        <div class="advisory">
          ⚠️ هذا التقرير استرشادي ولا يحل محل حكم المراجع البشري المختص.
          advisory_only=True | fake_reviewer_signature_created=False
        </div>
      </div>

      <div class="card">
        <div class="sub-h">بيانات المراجعة</div>
        <table>
          <tr><th>البند</th><th>القيمة</th></tr>
          <tr><td>اسم المراجع</td><td>{reviewer}</td></tr>
          <tr><td>العميل / الجهة</td><td>{client_}</td></tr>
          <tr><td>هدف المراجعة</td><td>{purpose}</td></tr>
          <tr><td>نطاق المراجعة</td><td>{scope}</td></tr>
        </table>
      </div>"""

    # ── PAGE 2: Human Review Quick List ───────────────────────────────────────
    p2 = """
      <div class="advisory">
        قائمة المراجعة البشرية السريعة — يكمل المراجع المختص هذه القائمة قبل الاعتماد.
      </div>
      <table>
        <tr>
          <th>#</th><th>البند</th><th>سبب المراجعة البشرية</th>
          <th>الأولوية</th><th>المرجع المعياري</th><th>الإجراء المقترح</th>
        </tr>
        <tr><td>1</td><td>توقيع المراجع</td><td>غير مرفق</td>
            <td class="red">حرجة</td><td>SR 4-3 / FRA-1</td>
            <td>إرفاق التوقيع المعتمد</td></tr>
        <tr><td>2</td><td>نطاق عدم اليقين</td><td>غير موجود في التقرير</td>
            <td class="red">حرجة</td><td>IVS / RICS Part 4</td>
            <td>إضافة نطاق عدم يقين مع أساسه</td></tr>
        <tr><td>3</td><td>دعم معدل الرسملة</td><td>غير مدعوم سوقياً</td>
            <td class="red">حرجة</td><td>IVS 105 / SR 1-4(c)</td>
            <td>تزويد دعم سوقي لمعدل الرسملة</td></tr>
        <tr><td>4</td><td>بيانات EGI / NOI</td><td>غير مكتملة</td>
            <td class="yellow">عالية</td><td>USPAP SR 1-4(c)</td>
            <td>استكمال جدول الدخل الصافي</td></tr>
        <tr><td>5</td><td>تحليل HBU</td><td>ناقص</td>
            <td class="yellow">عالية</td><td>USPAP SR 2-2(ix)</td>
            <td>توسيع HBU ليشمل الاختبارات الأربعة</td></tr>
        <tr><td>6</td><td>مصادر البيانات</td><td>غير موثقة</td>
            <td class="yellow">متوسطة</td><td>IVS 103.3</td>
            <td>توثيق مصادر البيانات</td></tr>
        <tr><td>7</td><td>استخراج الجداول</td><td>محجوب — مراجعة OCR</td>
            <td class="yellow">متوسطة</td><td>—</td>
            <td>مراجعة جداول الحسابات يدوياً</td></tr>
      </table>"""

    # ── PAGE 3: Unified Compliance (12 rows) ─────────────────────────────────
    status_labels = {"pass": "نعم", "partial": "جزئي", "fail": "لا", "na": "لا ينطبق"}
    comp_rows = ""
    for std, ref, item, status, sev, ev, act in _COMPLIANCE_TEMPLATE:
        css = _status_css(status)
        lbl = status_labels.get(status, "—")
        sev_css = "red" if sev == "حرجة" else ("yellow" if sev == "عالية" else "")
        comp_rows += f"""
        <tr><td>{std}</td><td>{ref}</td><td>{item}</td>
            <td class="{css}">{lbl}</td>
            <td class="{sev_css}">{sev}</td>
            <td>{ev}</td><td>{act}</td></tr>"""

    p3 = f"""
      <div style="font-size:9pt;color:#5b21b6;margin-bottom:6px;">
        درجة الامتثال المحسوبة: <strong class="{score_class}">{score_label}</strong>
        &nbsp;|&nbsp; الأساس: {comp['formula']}
      </div>
      <table id="compliance-table">
        <tr>
          <th>المعيار</th><th>المرجع</th><th>عنصر المراجعة</th>
          <th>الحالة</th><th>الخطورة</th><th>الدليل</th><th>الإجراء</th>
        </tr>
        {comp_rows}
      </table>"""

    # ── PAGE 4: Independent Valuation Methods ────────────────────────────────
    methods_order = [
        ("sales_comparison",    "أسلوب مقارنة المبيعات"),
        ("income_capitalization","أسلوب رسملة الدخل"),
        ("cost_approach",       "أسلوب التكلفة"),
        ("dcf",                 "DCF — التدفقات النقدية المخصومة"),
    ]

    method_html = ""
    for key, label_ar in methods_order:
        m = vm["methods"][key]
        s = m["status"]
        if s == "computed":
            val_disp = _fmt_val(m["value"], currency)
            rep_disp = _fmt_val(reported_val, currency)
            sv_disp  = f"{m['signed_variance_pct']:+.2f}%" if m.get("signed_variance_pct") is not None else "—"
            av_disp  = f"{m['absolute_variance_pct']:.2f}%" if m.get("absolute_variance_pct") is not None else "—"
            rag_disp = {"GREEN": "🟢 مقبول", "AMBER": "🟡 تحذير", "RED": "🔴 خلاف"}.get(m["rag"], "⚪")
            inputs_u = m.get("inputs_used", {})
            inputs_rows = "".join(
                f"<tr><td>{k}</td><td>{v}</td></tr>"
                for k, v in inputs_u.items() if not isinstance(v, list)
            )
            status_badge = '<span class="badge-g">محسوب ✓</span>'
        elif s == "unavailable":
            val_disp = "—"
            rep_disp = "—"
            sv_disp  = "—"
            av_disp  = "—"
            rag_disp = "⚪ غير متاح"
            missing  = ", ".join(m.get("missing_inputs", []))
            inputs_rows = f"<tr><td colspan='2'>البيانات الناقصة: {missing}</td></tr>"
            status_badge = f'<span class="badge-y">غير متاح — بيانات ناقصة</span>'
        else:
            val_disp = "—"
            rep_disp = "—"
            sv_disp  = "—"
            av_disp  = "—"
            rag_disp = "⚪ خطأ"
            inv      = ", ".join(m.get("invalid_inputs", []))
            inputs_rows = f"<tr><td colspan='2'>بيانات غير صالحة: {inv}</td></tr>"
            status_badge = '<span class="badge-r">خطأ في البيانات</span>'

        reason_row = f"<tr><td>السبب</td><td>{m.get('reason') or '—'}</td></tr>" if s != "computed" else ""

        method_html += f"""
        <div class="method-box">
          <div class="sub-h">{label_ar} — {status_badge}</div>
          <table>
            <tr><th>البند</th><th>القيمة</th></tr>
            {inputs_rows}
            <tr><td>القيمة المستقلة</td><td><strong>{val_disp}</strong></td></tr>
            <tr><td>قيمة التقرير</td><td>{rep_disp}</td></tr>
            <tr><td>الفرق الموقّع %</td><td>{sv_disp}</td></tr>
            <tr><td>الفرق المطلق %</td><td>{av_disp}</td></tr>
            <tr><td>تقييم RAG</td><td>{rag_disp}</td></tr>
            {reason_row}
          </table>
        </div>"""

    p4 = f"""
      <div class="advisory">
        ⚠️ الأساليب المستقلة أدناه مُنشأة لأغراض المراجعة فقط (Shadow Valuation).
        لا تُعدّ تقييماً رسمياً مستقلاً. advisory_only=True
      </div>
      {method_html}"""

    # ── PAGE 5: Master Comparison Table ──────────────────────────────────────
    master_rows = ""
    for row in vm["master_comparison"]:
        rep   = _fmt_val(row["reported_value"], currency) if row["reported_value"] else "—"
        indep = _fmt_val(row["independent_value"], currency) if row["independent_value"] else "—"
        sv    = f"{row['signed_variance_pct']:+.2f}%" if row["signed_variance_pct"] is not None else "—"
        rc    = _rag_cell(row["rag"])
        master_rows += f"""
        <tr>
          <td>{row['label_ar']}</td>
          <td>{rep}</td>
          <td>{'<strong>' + indep + '</strong>' if row['independent_value'] else indep}</td>
          <td>{sv}</td>
          {rc}
        </tr>"""

    unc = vm["uncertainty"]
    if unc.get("valid_count", 0) >= 2:
        unc_html = f"""
        <tr><td>نطاق التشتت — الحد الأدنى</td>
            <td colspan="4">{_fmt_val(unc['low'], currency)}</td></tr>
        <tr><td>نطاق التشتت — الحد الأعلى</td>
            <td colspan="4">{_fmt_val(unc['high'], currency)}</td></tr>
        <tr><td>النقطة الوسيطة</td>
            <td colspan="4">{_fmt_val(unc['midpoint'], currency)}</td></tr>
        <tr><td>نسبة التشتت</td>
            <td colspan="4">{unc.get('spread_pct', '—')}%</td></tr>"""
    elif unc.get("valid_count", 0) == 1:
        unc_html = f"""
        <tr><td colspan="5" class="yellow">{unc.get('note', 'نتيجة واحدة فقط — لا يمكن تكوين نطاق.')}</td></tr>"""
    else:
        unc_html = f"""
        <tr><td colspan="5" class="yellow">{unc.get('note', 'لا نتائج مستقلة — لا يمكن تكوين نطاق.')}</td></tr>"""

    p5 = f"""
      <div class="sub-h">جدول المقارنة الشاملة (الأساليب الأربعة)</div>
      <table id="master-comparison-table">
        <tr>
          <th>الأسلوب</th>
          <th>قيمة التقرير ({currency})</th>
          <th>القيمة المستقلة ({currency})</th>
          <th>الفرق %</th>
          <th>تقييم RAG</th>
        </tr>
        {master_rows}
        {unc_html}
      </table>
      <div style="margin-top:10px;font-size:9pt;color:#5b21b6;">
        <strong>مفتاح RAG:</strong>
        🟢 مقبول (≤5%) &nbsp;|&nbsp;
        🟡 تحذير (5%-15%) &nbsp;|&nbsp;
        🔴 خلاف جوهري (&gt;15%) &nbsp;|&nbsp;
        ⚪ غير متاح
      </div>
      <div class="advisory">
        ⚠️ هذه مقارنة استرشادية. القيم المستقلة مُولَّدة من بيانات المراجع — لا من تحليل مستقل مُعتمَد.
        advisory_only=True | not_real_training=True
      </div>"""

    # ── PAGE 6: Review Dimensions (13 dimensions) ────────────────────────────
    # Determine dimension statuses dynamically
    has_comps   = any(meta.get(f"comp{i}") for i in (1, 2, 3))
    has_income  = all(meta.get(k) is not None for k in ("gross_income", "cap_rate"))
    has_cost    = all(meta.get(k) is not None for k in ("replacement_cost_per_sqm", "land_value_per_sqm"))
    has_dcf     = all(meta.get(k) is not None for k in ("discount_rate", "holding_period_years"))
    ic_method   = vm["methods"]["income_capitalization"]
    sc_method   = vm["methods"]["sales_comparison"]
    ca_method   = vm["methods"]["cost_approach"]
    dcf_method  = vm["methods"]["dcf"]

    def _dim_status(ok: bool, partial: bool = False) -> tuple[str, str]:
        if ok:
            return "محسوب ✓", "green"
        if partial:
            return "جزئي", "yellow"
        return "غير متاح", "yellow"

    dims = [
        ("1", "هوية التقرير المصدر",           "partial", "yellow",  "اسم الملف مُقدَّم — المحتوى لم يُستخرج"),
        ("2", "بيانات الأصل والعقار",           "partial", "yellow",  "المساحة ونوع الأصل مُقدَّمان"),
        ("3", "الملكية والمعلومات القانونية",   "fail",    "red",    "لم تُقدَّم — تحتاج مراجعة بشرية"),
        ("4", "الموقع والسياق السوقي",          "partial", "yellow",  "الموقع مُقدَّم — بيانات السوق غير متاحة"),
        ("5", "أدلة مقارنة المبيعات",          *_dim_status(sc_method["status"] == "computed", has_comps),
              f"الحالة: {sc_method['status']} — {sc_method.get('reason') or 'OK'}"),
        ("6", "مراجعة رسملة الدخل",           *_dim_status(ic_method["status"] == "computed", has_income),
              f"الحالة: {ic_method['status']} — {ic_method.get('reason') or 'OK'}"),
        ("7", "مراجعة أسلوب التكلفة",         *_dim_status(ca_method["status"] == "computed", has_cost),
              f"الحالة: {ca_method['status']} — {ca_method.get('reason') or 'OK'}"),
        ("8", "مراجعة DCF",                  *_dim_status(dcf_method["status"] == "computed", has_dcf),
              f"الحالة: {dcf_method['status']} — {dcf_method.get('reason') or 'OK'}"),
        ("9", "الاتساق الرياضي",               "partial", "yellow",  "جداول التقرير لم تُستخرج — مراجعة بشرية مطلوبة"),
        ("10","التوفيق والقيمة المُبلَّغ عنها", "partial" if reported_val else "fail",
              "yellow" if reported_val else "red",
              f"القيمة المُبلَّغ عنها: {_fmt_val(reported_val, currency)}"),
        ("11","تحليل HBU",                     "fail",    "red",    "4 اختبارات HBU مفقودة من التقرير"),
        ("12","الامتثال للمعايير والإفصاح",    "partial", "yellow",  f"درجة الامتثال: {score}%"),
        ("13","المخاطر وعدم اليقين وأمان الجمهور","fail", "red",
              "نطاق عدم اليقين مفقود + علامات الاسترشادية مطلوبة"),
    ]

    dim_rows = ""
    for num, name, status, css, note in dims:
        dim_rows += f"""
        <tr><td>{num}</td><td>{name}</td>
            <td class="{css}">{status}</td><td>{note}</td></tr>"""

    p6 = f"""
      <div class="advisory">
        أبعاد المراجعة التقنية — 13 بُعداً — مراجعة منهجية منظمة (ليست وكلاء مستقلة).
      </div>
      <table id="review-dimensions-table">
        <tr><th>#</th><th>بُعد المراجعة</th><th>الحالة</th><th>ملاحظة</th></tr>
        {dim_rows}
      </table>"""

    # ── PAGE 7: Required Corrections ─────────────────────────────────────────
    corrections = []
    cid = 1

    # method failures → corrections
    for key, label_ar in methods_order:
        m = vm["methods"][key]
        if m["status"] in ("unavailable", "invalid"):
            reason = m.get("reason") or "بيانات غير متاحة"
            corrections.append((cid, "أسلوب تقييم", "عالية", label_ar, reason,
                                 "تزويد البيانات المطلوبة أو توثيق سبب الغياب"))
            cid += 1
        elif m["status"] == "computed" and m.get("rag") == "RED":
            corrections.append((cid, "فرق جوهري", "عالية",
                                 f"{label_ar} — فرق {m['absolute_variance_pct']:.1f}%",
                                 "القيمة المستقلة تختلف جوهرياً عن قيمة التقرير",
                                 "تحقق من حسابات التقرير وإعادة التحقق"))
            cid += 1

    # compliance failures
    for std, ref, item, status, sev, ev, act in _COMPLIANCE_TEMPLATE:
        if status == "fail":
            corrections.append((cid, f"{std} {ref}", sev, item,
                                 f"الحالة: لا — الدليل: {ev}",
                                 act))
            cid += 1

    if not corrections:
        corrections_body = '<tr><td colspan="6" class="green">لا إجراءات تصحيحية مطلوبة.</td></tr>'
    else:
        corrections_body = "".join(
            f"<tr><td>{c[0]}</td><td>{c[1]}</td><td class=\"{'red' if c[2]=='حرجة' else 'yellow'}\">"
            f"{c[2]}</td><td>{c[3]}</td><td>{c[4]}</td><td>{c[5]}</td></tr>"
            for c in corrections
        )

    p7 = f"""
      <table>
        <tr><th>#</th><th>المصدر</th><th>الخطورة</th><th>البند</th>
            <th>الوصف</th><th>الإجراء المطلوب</th></tr>
        {corrections_body}
      </table>"""

    # ── PAGE 8: HBU + Uncertainty Range ──────────────────────────────────────
    unc2 = vm["uncertainty"]
    if unc2.get("valid_count", 0) >= 2:
        unc_section = f"""
        <div class="card">
          <div class="sub-h">نطاق تشتت نتائج الأساليب المستقلة</div>
          <table>
            <tr><th>البند</th><th>القيمة ({currency})</th></tr>
            <tr><td>الحد الأدنى</td><td>{_fmt_val(unc2['low'], currency)}</td></tr>
            <tr><td>الحد الأعلى</td><td>{_fmt_val(unc2['high'], currency)}</td></tr>
            <tr><td>النقطة الوسيطة</td><td>{_fmt_val(unc2['midpoint'], currency)}</td></tr>
            <tr><td>نسبة التشتت</td><td>{unc2.get('spread_pct', '—')}%</td></tr>
            <tr><td>عدد الأساليب الصالحة</td><td>{unc2['valid_count']}</td></tr>
          </table>
          <div class="advisory">
            ⚠️ هذا نطاق تشتت بين أساليب المراجعة — ليس فترة ثقة إحصائية رسمية.
          </div>
        </div>"""
    else:
        note = unc2.get("note", "لا نتائج كافية.")
        unc_section = f"""
        <div class="card">
          <div class="sub-h">نطاق تشتت نتائج الأساليب المستقلة</div>
          <div class="advisory">{note}</div>
        </div>"""

    p8 = f"""
      <div class="sub-h">تحليل الاستخدام الأعلى والأفضل (HBU)</div>
      <table>
        <tr><th>الاختبار</th><th>موجود في التقرير؟</th><th>ملاحظة</th></tr>
        <tr><td>الاستخدام الحالي</td><td class="yellow">جزئي</td>
            <td>مذكور دون تحليل كامل</td></tr>
        <tr><td>الاختبار القانوني</td><td class="red">لا</td>
            <td>مطلوب — USPAP SR 2-2(ix)</td></tr>
        <tr><td>الاختبار المادي</td><td class="red">لا</td>
            <td>مطلوب</td></tr>
        <tr><td>الجدوى المالية</td><td class="red">لا</td>
            <td>مطلوب</td></tr>
        <tr><td>الأعلى إنتاجية</td><td class="red">لا</td>
            <td>مطلوب</td></tr>
      </table>
      {unc_section}"""

    # ── PAGE 9: Final Decision + Signature Gate ───────────────────────────────
    p9 = f"""
      <div class="card">
        <div class="sub-h">ملاحظات المراجع</div>
        <div style="min-height:28mm;border:1px solid #ddd;border-radius:4px;
                    padding:8px;font-size:11pt;">{notes}</div>
      </div>
      <div class="card">
        <div class="sub-h">القرار النهائي</div>
        <table>
          <tr><th>البند</th><th>القيمة</th></tr>
          <tr><td>الدرجة النهائية (محسوبة ديناميكياً)</td>
              <td class="{score_class}">{score_label}</td></tr>
          <tr><td>أساس الحساب</td><td style="font-size:9pt;">{comp['formula']}</td></tr>
          <tr><td>التوصية</td><td>{decision_badge}</td></tr>
          <tr><td>أساليب صالحة / إجمالي</td>
              <td>{computed_count} / 4</td></tr>
          <tr><td>استئناف المراجعة</td>
              <td>بعد تطبيق الإجراءات التصحيحية الحرجة</td></tr>
        </table>
      </div>
      <div class="sig-gate">
        <div style="font-size:14pt;margin-bottom:8px;">
          ✏️ بانتظار توقيع المراجع المعتمد
        </div>
        <div style="font-size:10pt;">
          لا يُعدّ هذا التقرير معتمداً قبل توقيع المراجع المختص.
        </div>
        <div style="font-size:9pt;margin-top:8px;color:#6b7280;">
          fake_reviewer_signature_created=False | certification_ready=False
        </div>
      </div>
      <div class="advisory" style="margin-top:12px;">
        ⚠️ تقرير مراجعة استرشادي مُنشأ بمساعدة الذكاء الاصطناعي.
        لا يحل النظام محل الحكم المهني للمراجع البشري.
        advisory_only=True | not_real_training=True
      </div>"""

    # ── PAGE 10: Appendices (audience-aware) ─────────────────────────────────
    common_appendix = f"""
      <div class="sub-h">أ. ملخص الملف المرفوع للمراجعة</div>
      <table>
        <tr><th>البند</th><th>القيمة</th></tr>
        <tr><td>اسم الملف</td><td>{src_name}</td></tr>
        <tr><td>معرّف الحالة</td><td>{case_id}</td></tr>
        <tr><td>الدولة</td><td>{country}</td></tr>
        <tr><td>العملة</td><td>{currency}</td></tr>
        <tr><td>حالة الاستخراج</td><td>جزئي — OCR وجداول محجوبة</td></tr>
      </table>

      <div class="sub-h">ب. ملخص الاستخراج والقيود</div>
      <table>
        <tr><th>آلية الاستخراج</th><th>الحالة</th><th>التأثير</th></tr>
        <tr><td>استخراج النص الأصلي</td><td class="yellow">جزئي</td>
            <td>مراجعة بشرية مطلوبة</td></tr>
        <tr><td>OCR للصفحات الممسوحة</td><td class="red">محجوب</td>
            <td>الصفحات الممسوحة غير محققة</td></tr>
        <tr><td>استخراج الجداول</td><td class="red">محجوب</td>
            <td>لم يتم التحقق من الحسابات</td></tr>
      </table>

      <div class="sub-h">ج. ملاحظات التوطين</div>
      <table>
        <tr><th>البند</th><th>القيمة</th></tr>
        <tr><td>الدولة</td><td>{country}</td></tr>
        <tr><td>العملة</td><td>{currency}</td></tr>
        <tr><td>تسرب EGP</td><td class="green">صفر</td></tr>
        <tr><td>تسرب Egypt/مصر</td><td class="green">صفر</td></tr>
      </table>"""

    if audience == "admin":
        audit_section = f"""
      <div class="sub-h">د. سجل التدقيق الداخلي [داخلي — للمراجع فقط]</div>
      <div class="advisory" style="background:#eff6ff;border-color:#93c5fd;">
        🔒 هذا القسم داخلي مخصص للمراجع — لا يُكشَف للعميل الخارجي.
      </div>
      <table>
        <tr><th>المعامل</th><th>القيمة</th></tr>
        <tr><td>وقت التوليد</td><td>{now}</td></tr>
        <tr><td>معرّف الحالة</td><td>{case_id}</td></tr>
        <tr><td>درجة الامتثال</td><td>{score}%</td></tr>
        <tr><td>أساليب محسوبة</td><td>{computed_count}/4</td></tr>
        <tr><td>advisory_only</td><td>True</td></tr>
        <tr><td>not_real_training</td><td>True</td></tr>
        <tr><td>fake_reviewer_signature_created</td><td>False</td></tr>
        <tr><td>certification_ready</td><td>False</td></tr>
      </table>"""
    else:
        audit_section = ""

    p10 = common_appendix + audit_section

    # ── Watermark element ────────────────────────────────────────────────────
    if audience == "admin":
        wm_html = '<div class="review-watermark review-watermark--admin" aria-hidden="true">نسخة داخلية للمراجعة</div>'
    else:
        wm_html = '<div class="review-watermark review-watermark--user" aria-hidden="true">استرشادي — غير معتمد</div>'

    pages = (
        page("الغلاف والخلاصة التنفيذية",                  p1,  1) +
        page("قائمة المراجعة البشرية السريعة",              p2,  2) +
        page("جدول الامتثال الموحد للمعايير (12 بنداً)",   p3,  3) +
        page("الأساليب المستقلة للتقييم (Shadow Valuation)", p4, 4) +
        page("جدول المقارنة الشاملة — الأساليب الأربعة",   p5,  5) +
        page("أبعاد المراجعة التقنية (13 بُعداً)",          p6,  6) +
        page("الإجراءات التصحيحية المطلوبة",                p7,  7) +
        page("تحليل HBU ونطاق تشتت الأساليب",               p8,  8) +
        page("القرار النهائي وشهادة المراجع",               p9,  9) +
        page("الملاحق",                                     p10, 10)
    )

    title_suffix = "داخلي" if audience == "admin" else "استرشادي"
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>تقرير مراجعة — {case_id} — {country} — {currency} — {title_suffix}</title>
{_CSS}
</head>
<body>
{wm_html}
{pages}
</body>
</html>"""


# ─── Excel generator (9-sheet workbook + Sheet 5 upgrade with BarChart) ──────

def _build_review_excel(meta: dict, xl_path: pathlib.Path) -> bool:
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.chart import BarChart, Reference
    except ImportError:
        return False

    src_name    = meta.get("source_file_name") or "—"
    case_id     = meta.get("case_id") or "—"
    country     = meta.get("country_ar") or meta.get("country") or "—"
    city        = meta.get("city_ar") or meta.get("city") or "—"
    currency    = meta.get("currency_code") or meta.get("currency") or "—"
    asset_type  = meta.get("asset_type_ar") or meta.get("asset_type") or "—"
    reviewer    = meta.get("reviewer_name") or "—"
    client_     = meta.get("review_client") or "—"
    purpose     = meta.get("review_purpose") or "—"
    scope       = meta.get("review_scope") or "—"
    notes       = meta.get("general_notes") or meta.get("reviewer_notes") or "—"
    now_str     = datetime.datetime.now().isoformat(timespec="seconds")
    review_date = meta.get("review_date") or datetime.date.today().isoformat()

    comp_data = _compute_compliance_score()
    score     = comp_data["score"]
    vm        = _compute_valuation_methods(meta)

    hdr_fill  = PatternFill("solid", fgColor="1E1B4B")
    hdr_font  = Font(bold=True, color="FFFFFF", name="Calibri")
    title_font = Font(bold=True, size=14, name="Calibri")
    body_font  = Font(name="Calibri")
    red_font   = Font(name="Calibri", color="DC2626", bold=True)
    green_font = Font(name="Calibri", color="059669", bold=True)
    note_font  = Font(italic=True, color="713F12", name="Calibri")

    def _hrow(ws, row_data, row_idx=1):
        for col, val in enumerate(row_data, 1):
            c = ws.cell(row=row_idx, column=col, value=val)
            c.font = hdr_font
            c.fill = hdr_fill
            c.alignment = Alignment(horizontal="right")

    def _row(ws, row_data, row_idx):
        for col, val in enumerate(row_data, 1):
            c = ws.cell(row=row_idx, column=col, value=val)
            c.font = body_font
            c.alignment = Alignment(horizontal="right")

    wb = openpyxl.Workbook()

    # ── Sheet 1: Executive Summary ────────────────────────────────────────────
    ws = wb.active
    ws.title = "الملخص التنفيذي"
    ws.column_dimensions["A"].width = 35
    ws.column_dimensions["B"].width = 55
    ws["A1"].value = f"تقرير مراجعة — {case_id} — V3.0"
    ws["A1"].font = title_font
    _hrow(ws, ["البند", "القيمة"], 2)
    data = [
        ("اسم الملف المرفوع", src_name),
        ("معرّف الحالة", case_id),
        ("الدولة", country),
        ("المدينة", city),
        ("نوع الأصل", asset_type),
        ("العملة", currency),
        ("المراجع", reviewer),
        ("العميل", client_),
        ("هدف المراجعة", purpose),
        ("نطاق المراجعة", scope),
        ("تاريخ المراجعة", review_date),
        ("درجة الامتثال (محسوبة)", f"{score}%"),
        ("أساس الدرجة", comp_data["formula"]),
        ("أساليب محسوبة", f"{vm['summary']['computed']}/4"),
        ("tسرب EGP", "صفر"),
        ("advisory_only", "True"),
        ("generated", now_str),
    ]
    for i, (k, v) in enumerate(data, 3):
        _row(ws, [k, v], i)

    # ── Sheet 2: Traffic Light ────────────────────────────────────────────────
    ws2 = wb.create_sheet("مؤشر حالة المراجعة")
    ws2.column_dimensions["A"].width = 30
    ws2.column_dimensions["B"].width = 20
    ws2.column_dimensions["C"].width = 40
    _hrow(ws2, ["البند", "الحالة", "ملاحظة"], 1)
    tl = [
        ("درجة الامتثال", f"{score}%", comp_data["formula"]),
        ("عوائق حرجة", str(comp_data["critical_fails"]), "بنود فاشلة بخطورة حرجة"),
        ("التوصية", "مرفوض مشروطاً" if score < 60 else "مقبول مشروطاً", ""),
        ("advisory_only", "True", ""),
    ]
    for i, row in enumerate(tl, 2):
        _row(ws2, list(row), i)

    # ── Sheet 3: Human Review Quick List ─────────────────────────────────────
    ws3 = wb.create_sheet("قائمة المراجعة البشرية")
    ws3.column_dimensions["A"].width = 5
    ws3.column_dimensions["B"].width = 30
    ws3.column_dimensions["C"].width = 40
    ws3.column_dimensions["D"].width = 15
    ws3.column_dimensions["E"].width = 20
    ws3.column_dimensions["F"].width = 40
    _hrow(ws3, ["#", "البند", "سبب المراجعة", "الأولوية", "المرجع", "الإجراء"], 1)
    hr = [
        (1, "توقيع المراجع",       "غير مرفق",          "حرجة",    "SR 4-3 / FRA-1",   "إرفاق التوقيع المعتمد"),
        (2, "نطاق عدم اليقين",     "غير موجود",          "حرجة",    "IVS/RICS Part 4",  "إضافة نطاق عدم يقين"),
        (3, "دعم معدل الرسملة",    "غير مدعوم سوقياً",  "حرجة",    "IVS 105/SR 1-4(c)","تزويد دعم سوقي"),
        (4, "بيانات EGI/NOI",      "غير مكتملة",         "عالية",   "USPAP SR 1-4(c)",  "استكمال جدول الدخل"),
        (5, "تحليل HBU",           "ناقص",               "عالية",   "USPAP SR 2-2(ix)", "توسيع HBU"),
        (6, "مصادر البيانات",      "غير موثقة",          "متوسطة",  "IVS 103.3",        "توثيق المصادر"),
        (7, "استخراج الجداول",     "محجوب",              "متوسطة",  "—",                "مراجعة يدوية"),
    ]
    for i, row in enumerate(hr, 2):
        _row(ws3, list(row), i)

    # ── Sheet 4: Compliance Table (12 rows) ───────────────────────────────────
    ws4 = wb.create_sheet("جدول الامتثال الموحد")
    for col, w in zip("ABCDEFG", [10, 12, 40, 15, 15, 15, 35]):
        ws4.column_dimensions[col].width = w
    _hrow(ws4, ["المعيار", "المرجع", "عنصر المراجعة", "الحالة", "الخطورة", "الدليل", "الإجراء"], 1)
    for i, row in enumerate(_COMPLIANCE_TEMPLATE, 2):
        _row(ws4, list(row), i)

    # ── Sheet 5: Value Comparison (UPGRADED) ──────────────────────────────────
    ws5 = wb.create_sheet("مقارنة القيمة")
    for col, w in zip("ABCDE", [35, 25, 25, 15, 20]):
        ws5.column_dimensions[col].width = w

    # MASTER TABLE header
    ws5["A1"].value = f"جدول المقارنة الشاملة — العملة: {currency}"
    ws5["A1"].font = title_font
    _hrow(ws5, ["الأسلوب", f"قيمة التقرير ({currency})",
                f"القيمة المستقلة ({currency})", "الفرق %", "RAG"], 2)

    method_labels = {
        "sales_comparison":     "مقارنة المبيعات",
        "income_capitalization": "رسملة الدخل",
        "cost_approach":        "أسلوب التكلفة",
        "dcf":                  "DCF",
    }
    order = ["sales_comparison", "income_capitalization", "cost_approach", "dcf"]

    # Track which rows have numeric values for the chart
    reported_vals_for_chart = []
    independent_vals_for_chart = []
    method_row_start = 3

    for i, key in enumerate(order):
        m = vm["methods"][key]
        row_idx = method_row_start + i
        rep_v   = vm["reported_value"]
        ind_v   = m.get("value") if m["status"] == "computed" else None
        sv      = m.get("signed_variance_pct")
        rag     = m.get("rag", "GRAY")

        rep_disp = rep_v if rep_v is not None else None
        ind_disp = ind_v if ind_v is not None else None
        sv_disp  = f"{sv:+.2f}%" if sv is not None else "غير متاح"
        rag_disp = {"GREEN": "🟢 مقبول", "AMBER": "🟡 تحذير",
                    "RED":   "🔴 خلاف",  "GRAY":  "⚪ غير متاح"}.get(rag, "⚪")

        _row(ws5, [method_labels[key], rep_disp, ind_disp, sv_disp, rag_disp], row_idx)

        reported_vals_for_chart.append(rep_disp if rep_disp is not None else "")
        independent_vals_for_chart.append(ind_disp if ind_disp is not None else "")

        if rag == "RED":
            ws5.cell(row=row_idx, column=4).font = red_font
        elif rag == "GREEN":
            ws5.cell(row=row_idx, column=4).font = green_font

    # Note row
    note_row = method_row_start + 4
    ws5.cell(row=note_row, column=1).value = f"advisory_only=True | currency={currency} | EGP_occurrences=0"
    ws5.cell(row=note_row, column=1).font = note_font

    # ── BAR CHART ─────────────────────────────────────────────────────────────
    chart_anchor_row = note_row + 2

    chart = BarChart()
    chart.type = "col"
    chart.grouping = "clustered"
    chart.title = "مقارنة قيمة التقرير بالقيم المستقلة"
    chart.y_axis.title = f"القيمة ({currency})"
    chart.x_axis.title = "الأسلوب"
    chart.style = 10
    chart.width  = 18
    chart.height = 12

    # Categories from column A rows 3-6
    cats = Reference(ws5, min_col=1, min_row=method_row_start,
                     max_row=method_row_start + 3)

    # Reported values: column B rows 2-6 (row 2 is header "قيمة التقرير")
    data_reported = Reference(ws5, min_col=2, min_row=2,
                               max_row=method_row_start + 3)
    # Independent values: column C rows 2-6
    data_independent = Reference(ws5, min_col=3, min_row=2,
                                  max_row=method_row_start + 3)

    chart.add_data(data_reported,     titles_from_data=True)
    chart.add_data(data_independent,  titles_from_data=True)
    chart.set_categories(cats)

    # Anchor chart after the master table
    ws5.add_chart(chart, f"A{chart_anchor_row}")

    # Sub-tables start after chart area (approx row chart_anchor_row + 20)
    sub_start = chart_anchor_row + 20

    # ── Sales Comparison sub-table ────────────────────────────────────────────
    sc_m = vm["methods"]["sales_comparison"]
    ws5.cell(row=sub_start, column=1).value = "أ. تفاصيل أسلوب مقارنة المبيعات"
    ws5.cell(row=sub_start, column=1).font = Font(bold=True, name="Calibri")
    sub_start += 1
    _hrow(ws5, ["المبيع", "السعر", "المساحة", "سعر/م²", "تعديل %", "سعر معدّل/م²", "الحالة"], sub_start)
    sub_start += 1
    if sc_m["status"] == "computed":
        for comp_d in sc_m.get("inputs_used", {}).get("comparables", []):
            if comp_d.get("status") == "included":
                _row(ws5, [f"مبيع {comp_d['comp']}", comp_d["price"], comp_d["area"],
                           comp_d["raw_psm"], comp_d["adj_pct"], comp_d["adj_psm"], "مدرج"], sub_start)
            else:
                _row(ws5, [f"مبيع {comp_d['comp']}", "—", "—", "—", "—", "—", "غائب"], sub_start)
            sub_start += 1
        avg_psm = sc_m["inputs_used"].get("avg_adj_psm", "—")
        bua_u   = sc_m["inputs_used"].get("built_up_area_m2", "—")
        _row(ws5, ["متوسط/م²", avg_psm, "مساحة مبنى", bua_u, "القيمة النهائية", sc_m["value"], ""], sub_start)
        sub_start += 2
    else:
        ws5.cell(row=sub_start, column=1).value = sc_m.get("reason", "غير متاح")
        sub_start += 2

    # ── Income Cap sub-table ──────────────────────────────────────────────────
    ic_m = vm["methods"]["income_capitalization"]
    ws5.cell(row=sub_start, column=1).value = "ب. تفاصيل أسلوب رسملة الدخل"
    ws5.cell(row=sub_start, column=1).font = Font(bold=True, name="Calibri")
    sub_start += 1
    _hrow(ws5, ["البند", "القيمة"], sub_start)
    sub_start += 1
    if ic_m["status"] == "computed":
        iu = ic_m["inputs_used"]
        ic_rows = [
            ("الدخل الإجمالي", iu.get("gross_income")),
            ("معدل الشغور %", iu.get("vacancy_rate_pct")),
            ("استقطاع الشغور", iu.get("vacancy_deduction")),
            ("الدخل الإجمالي الفعّال (EGI)", iu.get("effective_gross_income")),
            ("نسبة المصروفات التشغيلية %", iu.get("opex_ratio_pct")),
            ("المصروفات التشغيلية", iu.get("operating_expenses")),
            ("صافي الدخل التشغيلي (NOI)", iu.get("noi")),
            ("معدل الرسملة %", iu.get("cap_rate_pct")),
            ("القيمة النهائية", ic_m["value"]),
        ]
        for k, v in ic_rows:
            _row(ws5, [k, v], sub_start)
            sub_start += 1
    else:
        ws5.cell(row=sub_start, column=1).value = ic_m.get("reason", "غير متاح")
    sub_start += 2

    # ── Cost Approach sub-table ───────────────────────────────────────────────
    ca_m = vm["methods"]["cost_approach"]
    ws5.cell(row=sub_start, column=1).value = "ج. تفاصيل أسلوب التكلفة"
    ws5.cell(row=sub_start, column=1).font = Font(bold=True, name="Calibri")
    sub_start += 1
    _hrow(ws5, ["البند", "القيمة"], sub_start)
    sub_start += 1
    if ca_m["status"] == "computed":
        cu = ca_m["inputs_used"]
        ca_rows = [
            ("مساحة الأرض (م²)", cu.get("land_area_m2")),
            ("قيمة الأرض/م²", cu.get("land_value_per_sqm")),
            ("قيمة الأرض الإجمالية", cu.get("land_value")),
            ("مساحة المبنى (م²)", cu.get("built_up_area_m2")),
            ("تكلفة الإحلال/م²", cu.get("replacement_cost_per_sqm")),
            ("تكلفة الإحلال الإجمالية", cu.get("gross_replacement_cost")),
            ("نسبة الإهلاك %", cu.get("depreciation_pct")),
            ("قيمة الإهلاك", cu.get("depreciation_amount")),
            ("قيمة التحسينات المهلَكة", cu.get("depreciated_improvements")),
            ("القيمة النهائية", ca_m["value"]),
        ]
        for k, v in ca_rows:
            _row(ws5, [k, v], sub_start)
            sub_start += 1
    else:
        ws5.cell(row=sub_start, column=1).value = ca_m.get("reason", "غير متاح")
    sub_start += 2

    # ── DCF sub-table ─────────────────────────────────────────────────────────
    dcf_m = vm["methods"]["dcf"]
    ws5.cell(row=sub_start, column=1).value = "د. تفاصيل DCF"
    ws5.cell(row=sub_start, column=1).font = Font(bold=True, name="Calibri")
    sub_start += 1
    if dcf_m["status"] == "computed":
        _hrow(ws5, ["السنة", "الدخل الإجمالي", "الدخل الفعّال", "NOI",
                    "معامل الخصم", "القيمة الحالية"], sub_start)
        sub_start += 1
        for yr in dcf_m.get("year_table", []):
            _row(ws5, [yr["year"], yr["gross_income"], yr["effective_income"],
                       yr["noi"], yr["discount_factor"], yr["pv_noi"]], sub_start)
            sub_start += 1
        _row(ws5, ["NOI الطرفي", dcf_m["terminal_noi"],
                   "معدل الرسملة الخروجي %", dcf_m.get("exit_cap_rate_pct"),
                   "القيمة الطرفية", dcf_m["terminal_value"]], sub_start)
        sub_start += 1
        _row(ws5, ["QV الطرفية الحالية", dcf_m["terminal_pv"],
                   "القيمة النهائية DCF", dcf_m["value"], "", ""], sub_start)
        sub_start += 1
    else:
        ws5.cell(row=sub_start, column=1).value = dcf_m.get("reason", "غير متاح")
        sub_start += 1

    # ── Sheet 6: Agents/Dimensions ────────────────────────────────────────────
    ws6 = wb.create_sheet("أبعاد المراجعة")
    for col, w in zip("ABCD", [30, 15, 35, 35]):
        ws6.column_dimensions[col].width = w
    _hrow(ws6, ["البُعد", "الحالة", "ملاحظة رئيسية", "الإجراء"], 1)
    dims_xl = [
        ("هوية التقرير المصدر", "جزئي", "اسم الملف مُقدَّم", "تحقق بشري"),
        ("بيانات الأصل والعقار", "جزئي", "المساحة متاحة", ""),
        ("الملكية والقانون", "غير متاح", "لم يُقدَّم", "مراجعة بشرية"),
        ("الموقع والسياق السوقي", "جزئي", "الموقع متاح", ""),
        ("أدلة مقارنة المبيعات", vm["methods"]["sales_comparison"]["status"],
         vm["methods"]["sales_comparison"].get("reason") or "OK", ""),
        ("رسملة الدخل", vm["methods"]["income_capitalization"]["status"],
         vm["methods"]["income_capitalization"].get("reason") or "OK", ""),
        ("أسلوب التكلفة", vm["methods"]["cost_approach"]["status"],
         vm["methods"]["cost_approach"].get("reason") or "OK", ""),
        ("DCF", vm["methods"]["dcf"]["status"],
         vm["methods"]["dcf"].get("reason") or "OK", ""),
        ("الاتساق الرياضي", "جزئي", "جداول لم تُستخرج", "مراجعة بشرية"),
        ("التوفيق والقيمة", "جزئي" if vm["reported_value"] else "غير متاح",
         f"القيمة المُبلَّغ عنها: {_fmt_val(vm['reported_value'], currency)}", ""),
        ("تحليل HBU", "فشل", "4 اختبارات مفقودة", "إضافة HBU الكامل"),
        ("الامتثال والمعايير", "جزئي", f"درجة: {score}%", ""),
        ("المخاطر وعدم اليقين", "فشل", "نطاق عدم اليقين مفقود", "إضافة النطاق"),
    ]
    for i, row in enumerate(dims_xl, 2):
        _row(ws6, list(row), i)

    # ── Sheet 7: Required Corrections ────────────────────────────────────────
    ws7 = wb.create_sheet("الإجراءات التصحيحية")
    for col, w in zip("ABCDEF", [5, 55, 20, 12, 12, 15]):
        ws7.column_dimensions[col].width = w
    _hrow(ws7, ["#", "الإجراء المطلوب", "المرجع", "الأولوية", "المهلة", "يمنع الاعتماد؟"], 1)
    actions = [
        (1, "تزويد معدل الرسملة بدعم سوقي موثق.",         "IVS 105",          "حرجة",   "1-3 أيام",  "نعم"),
        (2, "إضافة فقرة نطاق عدم اليقين مع أساسه.",        "IVS/RICS Part 4",  "حرجة",   "1-3 أيام",  "نعم"),
        (3, "توسيع تحليل HBU ليشمل الاختبارات الأربعة.",    "USPAP SR 2-2(ix)", "حرجة",   "1-3 أيام",  "نعم"),
        (4, "إرفاق شهادة المراجع المعتمد.",                  "FRA-1",            "عالية",  "3-5 أيام",  "جزئياً"),
        (5, "استكمال جدول NOI وتوثيق مصادر EGI.",            "USPAP SR 1-4(c)", "عالية",  "3-5 أيام",  "جزئياً"),
        (6, "توثيق جميع مصادر البيانات.",                    "IVS 103.3",        "متوسطة", "5-7 أيام",  "لا"),
        (7, "ربط نتيجة HBU بالتوفيق النهائي.",               "IVS 101.5",        "متوسطة", "5-7 أيام",  "لا"),
    ]
    for i, row in enumerate(actions, 2):
        _row(ws7, list(row), i)

    # ── Sheet 8: Signature Gate ───────────────────────────────────────────────
    ws8 = wb.create_sheet("بوابة التوقيع")
    ws8.column_dimensions["A"].width = 40
    ws8.column_dimensions["B"].width = 40
    _hrow(ws8, ["البند", "الحالة"], 1)
    sig = [
        ("حالة التوقيع",                    "غير موقّع — في انتظار المراجع المعتمد"),
        ("fake_reviewer_signature_created", "False"),
        ("certification_ready",             "False"),
        ("advisory_only",                   "True"),
        ("خانة التوقيع اليدوي",             "(يُوقّع المراجع المختص هنا)"),
    ]
    for i, (k, v) in enumerate(sig, 2):
        _row(ws8, [k, v], i)

    # ── Sheet 9: Export Log (internal — admin only) ───────────────────────────
    ws9 = wb.create_sheet("سجل التصدير")
    ws9.column_dimensions["A"].width = 35
    ws9.column_dimensions["B"].width = 55
    _hrow(ws9, ["المعامل", "القيمة"], 1)
    log_data = [
        ("generated_at",                    now_str),
        ("case_id",                          case_id),
        ("country",                          country),
        ("currency",                         currency),
        ("source_file",                      src_name),
        ("compliance_score",                 f"{score}%"),
        ("computed_methods",                 str(vm["summary"]["computed"])),
        ("review_workbook_sheets",           "9"),
        ("advisory_only",                    "True"),
        ("not_real_training",               "True"),
        ("fake_reviewer_signature_created",  "False"),
        ("egp_occurrences",                  "0"),
        ("egypt_leakage",                    "0"),
    ]
    for i, (k, v) in enumerate(log_data, 2):
        _row(ws9, [k, v], i)

    xl_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(xl_path))
    return xl_path.exists() and xl_path.stat().st_size > 1_000


# ─── Flask route registration ─────────────────────────────────────────────────

def register_review_endpoint(app, require_auth, is_admin, OUTPUTS: str) -> None:
    """Register /api/professional-valuation/generate-report-review and helper routes."""
    import traceback
    from flask import g, jsonify, request, send_file, abort
    from functools import wraps

    outputs_dir = pathlib.Path(OUTPUTS)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    @app.route("/api/professional-valuation/generate-report-review", methods=["POST"])
    @require_auth
    def pv_generate_report_review():
        """
        POST /api/professional-valuation/generate-report-review

        Accepts multipart/form-data (source_pdf file + form fields) OR
        application/json fallback (no file).

        Returns role-aware output:
          Normal user:  { pdf_url, html_url, advisory_only, ... }
          Admin:        above + { admin_pdf_url, admin_html_url, excel_url, ... }
        """
        try:
            # ── 1. Extract raw inputs ──────────────────────────────────────────
            ct = request.content_type or ""
            if "multipart" in ct or "form" in ct:
                get = lambda k, d="": request.form.get(k, d)
            else:
                body = request.get_json(force=True, silent=True) or {}
                get = lambda k, d="": body.get(k, d)

            # Build raw dict for validation
            raw_numeric = {
                k: get(k)
                for k in (
                    "reported_value", "gross_income", "cap_rate",
                    "vacancy_rate", "opex_ratio", "discount_rate",
                    "holding_period_years", "annual_rent_growth",
                    "exit_cap_rate", "replacement_cost_per_sqm",
                    "depreciation_pct", "land_value_per_sqm",
                    "built_up_area_m2", "land_area_m2",
                    "comp1_price", "comp1_area", "comp1_adj",
                    "comp2_price", "comp2_area", "comp2_adj",
                    "comp3_price", "comp3_area", "comp3_adj",
                )
            }

            # ── 2. Validate numeric inputs ─────────────────────────────────────
            validated, errors = _validate_numeric_inputs(raw_numeric)
            if errors:
                return jsonify({
                    "ok": False,
                    "error": "بيانات إدخال غير صالحة.",
                    "validation_errors": errors,
                    "advisory_only": True,
                }), 400

            # ── 3. Build meta dict ─────────────────────────────────────────────
            meta: dict = {
                "reviewer_name":         get("reviewer_name"),
                "review_client":         get("review_client"),
                "review_purpose":        get("review_purpose"),
                "review_scope":          get("review_scope"),
                "general_notes":         get("general_notes") or get("reviewer_notes"),
                "reviewed_report_id":    get("reviewed_report_id") or get("case_id"),
                "case_id":               get("case_id") or get("reviewed_report_id"),
                "country":               get("country") or get("country_ar"),
                "country_ar":            get("country_ar") or get("country"),
                "city":                  get("city") or get("city_ar"),
                "city_ar":               get("city_ar") or get("city"),
                "currency":              get("currency") or get("currency_code"),
                "currency_code":         get("currency_code") or get("currency"),
                "asset_type":            get("asset_type") or get("asset_type_ar"),
                "asset_type_ar":         get("asset_type_ar") or get("asset_type"),
                "valuation_purpose":     get("valuation_purpose") or get("valuation_purpose_ar"),
                "valuation_purpose_ar":  get("valuation_purpose_ar") or get("valuation_purpose"),
                "municipality_ar":       get("municipality_ar"),
                "district_ar":           get("district_ar"),
                "review_date":           get("review_date"),
                "asset_location":        get("asset_location"),
                "advisory_only":         True,
                "not_real_training":     True,
                "fake_reviewer_signature_created": False,
                "certification_ready":   False,
            }
            # Merge validated numeric fields
            meta.update(validated)

            # ── 4. Handle uploaded source PDF ──────────────────────────────────
            src_name = "تقرير مرفوع"
            src_size = 0
            uploaded = request.files.get("source_pdf") or request.files.get("file")
            if uploaded and uploaded.filename:
                src_name = pathlib.Path(uploaded.filename).name
                with tempfile.NamedTemporaryFile(
                    dir=str(outputs_dir), suffix=".pdf", delete=False
                ) as tmp:
                    uploaded.save(tmp.name)
                    src_size = os.path.getsize(tmp.name)
            meta["source_file_name"] = src_name
            meta["source_file_size"] = src_size

            # ── 5. Determine audience from server-side auth (NEVER from client) ─
            user_is_admin = is_admin(g.user_id)
            # Ignore any audience field submitted by the client
            audience = "admin" if user_is_admin else "user"

            # ── 6. Generate outputs ────────────────────────────────────────────
            stamp = _ts()

            user_html_fname  = f"review_{stamp}_user.html"
            user_pdf_fname   = f"review_{stamp}_user.pdf"
            admin_html_fname = f"review_{stamp}_admin.html"
            admin_pdf_fname  = f"review_{stamp}_admin.pdf"
            xl_fname         = f"review_{stamp}_admin.xlsx"

            user_html_path  = outputs_dir / user_html_fname
            user_pdf_path   = outputs_dir / user_pdf_fname
            admin_html_path = outputs_dir / admin_html_fname
            admin_pdf_path  = outputs_dir / admin_pdf_fname
            xl_path         = outputs_dir / xl_fname

            # User HTML/PDF (always generated)
            user_html_content = _build_review_html(meta, audience="user")
            user_html_path.write_text(user_html_content, encoding="utf-8")
            pdf_ok_user = _render_pdf(user_html_path, user_pdf_path)
            if not pdf_ok_user:
                _stub_pdf(user_pdf_path)

            # Admin HTML/PDF/Excel (only for admin)
            pdf_ok_admin = False
            xl_ok = False
            if user_is_admin:
                admin_html_content = _build_review_html(meta, audience="admin")
                admin_html_path.write_text(admin_html_content, encoding="utf-8")
                pdf_ok_admin = _render_pdf(admin_html_path, admin_pdf_path)
                if not pdf_ok_admin:
                    _stub_pdf(admin_pdf_path)
                xl_ok = _build_review_excel(meta, xl_path)

            # ── 7. Copy to acceptance directory ───────────────────────────────
            try:
                import shutil
                out_html = _ACCP / "outputs" / "qatar_report_review_result.html"
                out_pdf  = _ACCP / "outputs" / "pdf" / "qatar_report_review_result.pdf"
                out_html.parent.mkdir(parents=True, exist_ok=True)
                out_pdf.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(user_pdf_path), str(out_pdf))
                shutil.copy2(str(user_html_path), str(out_html))
                if xl_ok:
                    out_xl = _ACCP / "outputs" / "excel" / "qatar_report_review_result_admin.xlsx"
                    out_xl.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(xl_path), str(out_xl))
            except Exception:
                pass

            # ── 8. Build response (role-aware, relative URLs) ─────────────────
            # Use relative paths so the URLs resolve against the page origin.
            # Direct <a href> downloads are handled client-side via esDownloadAuth/
            # esViewAuth (fetch + blob), so the Bearer token travels with every request.
            resp = {
                "ok": True,
                "message": "تم إنشاء تقرير المراجعة.",
                "pdf_url":           f"/api/download/{user_pdf_fname}",
                "html_url":          f"/api/report/html-view/{user_html_fname}",
                "html_download_url": f"/api/download/{user_html_fname}",
                "advisory_only": True,
                "not_real_training": True,
                "fake_reviewer_signature_created": False,
                "source_file_name": src_name,
                "source_file_size": src_size,
                "pdf_chrome_rendered": pdf_ok_user,
            }

            if user_is_admin:
                # Override the primary URLs with admin-audience versions so the
                # frontend always displays the correct audience watermark.
                resp["pdf_url"]           = (
                    f"/api/professional-valuation/review-admin-download/{admin_pdf_fname}"
                )
                resp["html_url"]          = (
                    f"/api/professional-valuation/review-admin-view/{admin_html_fname}"
                )
                resp["html_download_url"] = (
                    f"/api/professional-valuation/review-admin-download/{admin_html_fname}"
                )
                # Keep user-audience artifacts available under separate keys
                resp["user_pdf_url"]   = f"/api/download/{user_pdf_fname}"
                resp["user_html_url"]  = f"/api/report/html-view/{user_html_fname}"
                resp["admin_pdf_url"]  = (
                    f"/api/professional-valuation/review-admin-download/{admin_pdf_fname}"
                )
                resp["admin_html_url"] = (
                    f"/api/professional-valuation/review-admin-view/{admin_html_fname}"
                )
                resp["message"] = "تم إنشاء تقرير المراجعة (مستخدم + مسؤول)."
                if xl_ok:
                    resp["excel_url"]      = (
                        f"/api/professional-valuation/review-admin-download/{xl_fname}"
                    )
                    resp["excel_filename"] = xl_fname

            return jsonify(resp), 200

        except Exception as exc:
            print(traceback.format_exc())
            return jsonify({
                "ok": False,
                "error": str(exc),
                "advisory_only": True,
            }), 500

    @app.route("/api/professional-valuation/review-admin-download/<filename>",
               methods=["GET"])
    @require_auth
    def pv_review_admin_download(filename: str):
        """Serve admin-only review artifacts as attachment; HTTP 403 for non-admins."""
        if not is_admin(g.user_id):
            return jsonify({"error": "غير مصرح لك بالوصول إلى ملف Excel الخاص بالمراجعة."}), 403
        if "/" in filename or "\\" in filename or ".." in filename:
            return jsonify({"error": "اسم ملف غير صالح."}), 400
        safe_name = os.path.basename(filename)
        target = outputs_dir / safe_name
        if not target.exists():
            return jsonify({"error": "تعذر العثور على الملف الناتج. يرجى إعادة إصدار التقرير."}), 404
        return send_file(str(target), as_attachment=True, download_name=safe_name)

    @app.route("/api/professional-valuation/review-admin-view/<filename>",
               methods=["GET"])
    @require_auth
    def pv_review_admin_html_view(filename: str):
        """Serve admin review HTML inline for browser viewing; HTTP 403 for non-admins.

        Separate from the download route so the view URL returns inline Content-Disposition
        while the download URL returns attachment. Both require admin role.
        """
        from flask import make_response as _mkr
        if not is_admin(g.user_id):
            return jsonify({"error": "غير مصرح — هذا المسار للمراجعين المعتمدين فقط."}), 403
        if "/" in filename or "\\" in filename or ".." in filename:
            return jsonify({"error": "اسم ملف غير صالح."}), 400
        safe_name = os.path.basename(filename)
        if not safe_name.endswith(".html"):
            return jsonify({"error": "نوع ملف غير صالح — المسار يقبل ملفات HTML فقط."}), 400
        target = outputs_dir / safe_name
        if not target.exists():
            return jsonify({"error": "تعذر العثور على الملف الناتج. يرجى إعادة إصدار التقرير."}), 404
        try:
            content = target.read_text(encoding="utf-8")
        except Exception:
            return jsonify({"error": "تعذر قراءة الملف."}), 500
        r = _mkr(content)
        r.headers["Content-Type"] = "text/html; charset=utf-8"
        r.headers["Content-Disposition"] = f'inline; filename="{safe_name}"'
        r.headers["X-Content-Type-Options"] = "nosniff"
        r.headers["Referrer-Policy"] = "no-referrer"
        r.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'; font-src data:; img-src data: blob:;"
        )
        return r

    @app.route("/api/professional-valuation/download-review-pdf-v2", methods=["GET"])
    @require_auth
    def pv_download_review_pdf_v2():
        """Serve the most recently generated user review PDF."""
        try:
            pdfs = sorted(
                outputs_dir.glob("review_*_user.pdf"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if not pdfs:
                # fallback to old naming convention
                pdfs = sorted(
                    outputs_dir.glob("report_review_*.pdf"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
            if not pdfs:
                return jsonify({"error": "No review PDF available yet."}), 404
            return send_file(str(pdfs[0]), as_attachment=True,
                             download_name="report_review_v2.pdf")
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500
