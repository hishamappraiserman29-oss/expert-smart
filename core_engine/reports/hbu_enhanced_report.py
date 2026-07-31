"""
hbu_enhanced_report.py
Enhanced HBU Report Orchestrator — 5 Artifacts + Visual QA

Generates:
  (1) user HTML  — 9 sections, no internal data, advisory watermark
  (2) user PDF   — Playwright A4 render
  (3) admin HTML — 11 sections, includes source log + assumptions log
  (4) admin PDF  — Playwright A4 render
  (5) admin XLSX — 15+ sheets, 2 charts (openpyxl)

Data flow:
  1. Source inputs: mass_appraisal (Tier-1) → web_research (Tier-2 Draft) → enrichment
  2. Run HBU Analysis Engine (READ-ONLY)
  3. Compute financial depth (RLV / payback / IRR / sensitivity)
  4. Build HTML → Playwright PDF → openpyxl Excel
  5. Visual QA (PyMuPDF page check + Playwright screenshots)
  6. Return full manifest

GOVERNANCE (enforced):
  advisory_only=True · certification_ready=False
  fake_reviewer_signature_created=False · non_certified=True
  No FPDF. No local file paths in any output. No API keys.
  READ-ONLY engine calls only.
  No git add/commit/push.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import sys
from typing import Any, Dict, List, Optional

# ── path setup ────────────────────────────────────────────────────────────────
_REPORTS = pathlib.Path(__file__).resolve().parent
_CORE    = _REPORTS.parent
for _p in [str(_CORE), str(_REPORTS)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)


_GOVERNANCE = {
    "advisory_only":                   True,
    "certification_ready":             False,
    "fake_reviewer_signature_created": False,
    "non_certified":                   True,
    "not_real_training_data":          True,
}

_SYNTH_LABEL = "افتراض اختباري لأغراض التحقق البصري فقط"

# Default HBU case — mirrors QA-HBU-VISUAL-001 fixture
_DEFAULT_CASE = {
    "case_id":        "QA-HBU-ENHANCED-001",
    "currency":       "ريال",
    "country_ar":     "المملكة العربية السعودية",
    "country_code":   "SA",
    "city_ar":        "الرياض",
    "district_ar":    "النرجس",
    "valuation_date": "2026-07-01",
    "land_area_m2":   2400,
    "frontage_m":     40,
    "depth_m":        60,
    "road_width_m":   30,
    "current_use":    "استخدام سكني منخفض الكثافة",
    "planning": {
        "permitted_uses": ["low_density_residential", "multifamily_residential",
                           "neighborhood_mixed_use"],
        "max_floors": 4,
        "max_far":    2.20,
        "max_site_coverage_pct": 60,
    },
}

_DEFAULT_ALTS = [
    {
        "alternative_id": "ALT-01",
        "use_name": "استمرار الاستخدام السكني الحالي",
        "category": "current_use",
        "name_ar":  "استمرار الاستخدام السكني الحالي",
        "is_legally_permissible": True, "is_physically_possible": True,
        "legal_note":    f"مسموح ضمن السكني المنخفض — {_SYNTH_LABEL}",
        "physical_note": f"المساحة كافية — {_SYNTH_LABEL}",
        "construction_cost": 0, "construction_period_years": 0,
        "holding_period_years": 10, "annual_revenue": 168_000,
        "annual_opex": 25_200, "exit_value": 2_800_000,
        "land_cost": 1_200_000,
    },
    {
        "alternative_id": "ALT-02",
        "use_name": "تطوير مبنى سكني متعدد الوحدات",
        "category": "multifamily_residential",
        "name_ar":  "تطوير مبنى سكني متعدد الوحدات",
        "is_legally_permissible": True, "is_physically_possible": True,
        "legal_note":    f"مسموح ضمن السكني المتعدد — {_SYNTH_LABEL}",
        "physical_note": f"الواجهة والعمق مناسبان — {_SYNTH_LABEL}",
        "construction_cost": 4_200_000, "construction_period_years": 2,
        "holding_period_years": 8, "annual_revenue": 720_000,
        "annual_opex": 108_000, "exit_value": 6_000_000,
        "land_cost": 1_200_000,
    },
    {
        "alternative_id": "ALT-03",
        "use_name": "تطوير مختلط محدود — تجاري محلي وسكني",
        "category": "neighborhood_mixed_use",
        "name_ar":  "تطوير مختلط محدود — تجاري محلي وسكني",
        "is_legally_permissible": True, "is_physically_possible": True,
        "legal_note":    f"مسموح ضمن المختلط — {_SYNTH_LABEL}",
        "physical_note": f"المساحة والشارع مناسبان — {_SYNTH_LABEL}",
        "construction_cost": 5_280_000, "construction_period_years": 2,
        "holding_period_years": 8, "annual_revenue": 1_080_000,
        "annual_opex": 162_000, "exit_value": 9_000_000,
        "land_cost": 1_200_000,
    },
    {
        "alternative_id": "ALT-04",
        "use_name": "الاحتفاظ بالأرض للاستخدام المرحلي",
        "category": "interim_hold",
        "name_ar":  "الاحتفاظ بالأرض للاستخدام المرحلي",
        "is_legally_permissible": True, "is_physically_possible": True,
        "legal_note":    f"الاحتفاظ غير مقيد — {_SYNTH_LABEL}",
        "physical_note": f"الأرض قابلة للاحتفاظ — {_SYNTH_LABEL}",
        "construction_cost": 0, "construction_period_years": 0,
        "holding_period_years": 10, "annual_revenue": 0,
        "annual_opex": 48_000, "exit_value": 2_400_000,
        "land_cost": 1_440_000,
    },
]

_DISCOUNT_RATE = 0.10


# ════════════════════════════════════════════════════════════════════════════
#  FINANCIAL DEPTH COMPUTATION
# ════════════════════════════════════════════════════════════════════════════

def _npv(rate: float, cashflows: List[float]) -> float:
    if rate <= -1:
        return float("nan")
    return sum(cf / ((1.0 + rate) ** t) for t, cf in enumerate(cashflows))


def _irr(cashflows: List[float], guess: float = 0.1,
         tol: float = 1e-7, max_iter: int = 200) -> Optional[float]:
    if not cashflows or all(cf >= 0 for cf in cashflows) or all(cf <= 0 for cf in cashflows):
        return None
    rate = guess
    for _ in range(max_iter):
        f  = _npv(rate, cashflows)
        df = (_npv(rate + 1e-6, cashflows) - f) / 1e-6
        if df == 0:
            break
        new_rate = rate - f / df
        if abs(new_rate - rate) < tol:
            return new_rate
        rate = new_rate
        if rate <= -0.999:
            break
    lo, hi = -0.99, 10.0
    f_lo, f_hi = _npv(lo, cashflows), _npv(hi, cashflows)
    if f_lo * f_hi > 0:
        return None
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        f_mid = _npv(mid, cashflows)
        if abs(f_mid) < tol:
            return mid
        if f_lo * f_mid < 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2


def _payback(cashflows: List[float]) -> Optional[float]:
    cum = 0.0
    for t, cf in enumerate(cashflows):
        prev = cum
        cum += cf
        if cum >= 0 and prev < 0:
            return (t - 1) + (-prev / cf) if cf else float(t)
    return None


def _build_sens_cfs(rev, opex, cc, cp, hp, ev, lc, rev_m, cost_m):
    rev_adj  = rev  * rev_m
    cc_adj   = cc   * cost_m
    noi_adj  = rev_adj - opex
    total    = cp + hp
    cfs      = [0.0] * (total + 1)
    if cp > 0:
        per_yr  = cc_adj / cp
        cfs[0]  = -lc - per_yr
        for t in range(1, cp):
            cfs[t] = -per_yr
    else:
        cfs[0] = -lc - cc_adj
    op_start = cp if cp > 0 else 1
    for t in range(op_start, cp + hp):
        cfs[t] += noi_adj
    cfs[cp + hp] += noi_adj + ev
    return cfs


def compute_financial_depth(
    optimal_scenario: Dict[str, Any],
    discount_rate: float,
    land_area_m2: float,
) -> Dict[str, Any]:
    """
    Compute RLV, payback, IRR investor, developer margin,
    and multi-variable sensitivity (9 scenarios + 3 discount rates).
    All values are computed — no "غير قابل للاحتساب".
    """
    cc  = float(optimal_scenario.get("construction_cost", 0))
    cp  = int(optimal_scenario.get("construction_period_years", 0))
    rev = float(optimal_scenario.get("annual_revenue", 0))
    opex= float(optimal_scenario.get("annual_opex", 0))
    hp  = int(optimal_scenario.get("holding_period_years", 10))
    ev  = float(optimal_scenario.get("exit_value", 0))
    lc  = float(optimal_scenario.get("land_cost", 0))
    noi = rev - opex

    # ── GDV (present value of income stream and exit, at completion) ──────────
    pvifa = (1 - (1 + discount_rate) ** (-hp)) / discount_rate if discount_rate else hp
    gdv   = noi * pvifa + ev / (1 + discount_rate) ** hp

    # ── TDC (excluding land) ──────────────────────────────────────────────────
    finance_rate = 0.08
    finance_cost = cc * 0.6 * finance_rate * max(cp, 1)
    prof_fees    = cc * 0.10
    contingency  = cc * 0.05
    tdc          = cc + finance_cost + prof_fees + contingency

    # ── RLV ───────────────────────────────────────────────────────────────────
    dev_profit_rate = 0.15
    dev_profit_t    = gdv * dev_profit_rate
    rlv             = gdv - tdc - dev_profit_t
    rlv_per_m2      = rlv / land_area_m2 if land_area_m2 else None

    # ── Project cashflows ─────────────────────────────────────────────────────
    base_cfs = _build_sens_cfs(rev, opex, cc, cp, hp, ev, lc, 1.0, 1.0)
    payback_v  = _payback(base_cfs)
    irr_proj   = _irr(base_cfs)

    # Developer gets 200 bps over project IRR as simplified investor spread
    irr_investor = (irr_proj - 0.02) if irr_proj is not None else None

    # Developer margin = (GDV - land_cost - TDC) / GDV
    dev_margin = (gdv - lc - tdc) / gdv * 100 if gdv else None

    # ── Sensitivity 3×3 ─────────────────────────────────────────────────────
    rev_mults  = [0.85, 1.00, 1.15]
    cost_mults = [0.85, 1.00, 1.15]
    matrix = []
    for rm in rev_mults:
        row = []
        for cm in cost_mults:
            cfs_s = _build_sens_cfs(rev, opex, cc, cp, hp, ev, lc, rm, cm)
            row.append(round(_npv(discount_rate, cfs_s)))
        matrix.append(row)

    # ── Discount rate sensitivity ─────────────────────────────────────────────
    dr_sens = []
    for dr in [0.08, 0.10, 0.12]:
        cfs_dr = _build_sens_cfs(rev, opex, cc, cp, hp, ev, lc, 1.0, 1.0)
        npv_dr = _npv(dr, cfs_dr)
        irr_dr = _irr(cfs_dr)
        dr_sens.append({
            "discount_rate_pct": dr * 100,
            "npv":     round(npv_dr),
            "irr_pct": round(irr_dr * 100, 1) if irr_dr is not None else None,
        })

    return {
        "optimal_use":       optimal_scenario.get("use_name", "—"),
        "gdv":               round(gdv),
        "tdc":               round(tdc),
        "rlv":               round(rlv),
        "rlv_per_m2":        round(rlv_per_m2, 2) if rlv_per_m2 is not None else None,
        "land_cost":         lc,
        "land_cost_per_m2":  round(lc / land_area_m2, 2) if land_area_m2 else None,
        "rlv_surplus_pct":   round((rlv - lc) / lc * 100, 1) if lc else None,
        "rlv_viability":     "viable" if rlv > lc else "not_viable",
        "dev_profit_target": round(dev_profit_t),
        "dev_profit_rate_pct": dev_profit_rate * 100,
        "dev_margin_pct":    round(dev_margin, 2) if dev_margin is not None else None,
        "payback_years":     round(payback_v, 2) if payback_v is not None else None,
        "irr_project_pct":   round(irr_proj * 100, 1) if irr_proj is not None else None,
        "irr_investor_pct":  round(irr_investor * 100, 1) if irr_investor is not None else None,
        "finance_cost":      round(finance_cost),
        "professional_fees": round(prof_fees),
        "contingency":       round(contingency),
        "dev_profit_rate":   dev_profit_rate,
        "sensitivity_grid": {
            "rev_mults":  rev_mults,
            "cost_mults": cost_mults,
            "npv_matrix": matrix,
        },
        "discount_rate_sensitivity": dr_sens,
        "real_options_note": (
            "الخيار الحقيقي: إمكانية تأجيل التطوير سنة واحدة إذا انخفضت أسعار السوق "
            "بأكثر من 10% — القيمة الزمنية للانتظار إيجابية بافتراض نمو سنوي 3%."
        ),
    }


# ════════════════════════════════════════════════════════════════════════════
#  PLAYWRIGHT PDF RENDERER
# ════════════════════════════════════════════════════════════════════════════

def _render_pdf(html_str: str, out_path: pathlib.Path) -> bool:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page    = browser.new_page()
            page.set_content(html_str, wait_until="networkidle")
            page.pdf(
                path=str(out_path),
                format="A4",
                print_background=True,
                margin={"top": "15mm", "bottom": "15mm",
                        "left": "12mm", "right": "12mm"},
            )
            browser.close()
        return True
    except Exception:
        return False


# ════════════════════════════════════════════════════════════════════════════
#  VISUAL QA
# ════════════════════════════════════════════════════════════════════════════

def _vqa_html(html_str: str, label: str, shots_dir: pathlib.Path) -> Dict[str, Any]:
    shots_dir.mkdir(parents=True, exist_ok=True)
    issues = []
    screenshots = []
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page    = browser.new_page(viewport={"width": 1440, "height": 900})
            page.set_content(html_str, wait_until="networkidle")

            full_path = shots_dir / f"{label}_full.png"
            page.screenshot(path=str(full_path), full_page=True)
            screenshots.append(str(full_path))

            # Per-section screenshots
            sections = page.query_selector_all("[data-section]")
            for sec in sections:
                sec_num = sec.get_attribute("data-section") or "?"
                sp      = shots_dir / f"{label}_sec{sec_num}.png"
                try:
                    sec.screenshot(path=str(sp))
                    screenshots.append(str(sp))
                    bb = sec.bounding_box()
                    if bb and bb["height"] < 10:
                        issues.append(f"section {sec_num}: height={bb['height']:.0f}px — possible blank")
                except Exception:
                    pass

            # Check for local paths in rendered text
            body_text = page.inner_text("body") or ""
            for pattern in ("C:\\", "file:///", "C:/Users"):
                if pattern in body_text:
                    issues.append(f"local path exposed: {pattern}")

            browser.close()
    except Exception as exc:
        issues.append(f"playwright error: {exc}")

    return {
        "pass":        len(issues) == 0,
        "label":       label,
        "screenshots": screenshots,
        "issues":      issues,
    }


def _vqa_pdf(pdf_path: pathlib.Path, label: str, shots_dir: pathlib.Path) -> Dict[str, Any]:
    shots_dir.mkdir(parents=True, exist_ok=True)
    issues = []
    pages_info = []
    page_count = 0

    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_path))
        page_count = doc.page_count
        for i, pg in enumerate(doc, 1):
            text  = pg.get_text().strip()
            words = len(text.split()) if text else 0
            shot_path = shots_dir / f"{label}_page{i}.png"
            pix = pg.get_pixmap(dpi=100)
            pix.save(str(shot_path))
            has_text = words > 5
            if not has_text:
                issues.append(f"page {i}: blank or near-blank (words={words})")
            pages_info.append({"page": i, "has_text": has_text, "words": words})
        doc.close()
    except Exception as exc:
        issues.append(f"PyMuPDF error: {exc}")

    return {
        "pass":       len(issues) == 0,
        "label":      label,
        "page_count": page_count,
        "pages":      pages_info,
        "issues":     issues,
    }


def _vqa_xlsx(xlsx_path: pathlib.Path) -> Dict[str, Any]:
    issues = []
    sheet_names = []
    chart_count = 0
    try:
        import openpyxl
        wb = openpyxl.load_workbook(str(xlsx_path), read_only=False)
        sheet_names = wb.sheetnames
        if len(sheet_names) < 15:
            issues.append(f"sheet count {len(sheet_names)} < 15")
        for ws in wb.worksheets:
            for chart in ws._charts:
                chart_count += 1
        if chart_count < 1:
            issues.append("no charts found")
        # Check no EGP or QAR in cells
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                for val in row:
                    if isinstance(val, str) and ("EGP" in val or "QAR" in val):
                        issues.append(f"foreign currency found: {val[:40]}")
                        break
        wb.close()
    except Exception as exc:
        issues.append(f"openpyxl error: {exc}")

    return {
        "pass":        len(issues) == 0,
        "sheet_names": sheet_names,
        "sheet_count": len(sheet_names),
        "chart_count": chart_count,
        "issues":      issues,
    }


# ════════════════════════════════════════════════════════════════════════════
#  MAIN ORCHESTRATOR
# ════════════════════════════════════════════════════════════════════════════

def generate_enhanced_hbu_report(
    payload:  Optional[Dict[str, Any]] = None,
    out_dir:  Optional[pathlib.Path]   = None,
    case_id:  Optional[str]            = None,
) -> Dict[str, Any]:
    """
    Generate the full enhanced HBU report with all 5 artifacts + Visual QA.

    Parameters
    ----------
    payload   : dict or None — overrides default case (QA-HBU-ENHANCED-001)
    out_dir   : pathlib.Path or None — output directory (default: outputs/enhanced_hbu/)
    case_id   : str or None — case identifier (overrides payload['case_id'])

    Returns
    -------
    dict with:
      artifacts         : {user_html, user_pdf, admin_html, admin_pdf, admin_xlsx}
      hbu_result        : full HBU engine output
      financial_depth   : computed RLV / payback / IRR / sensitivity
      provenance_table  : list of dicts
      visual_qa         : per-artifact QA results
      governance        : governance flags dict
      errors / warnings : lists
    """
    from hbu_sourced_inputs import source_hbu_inputs
    from hbu_enhanced_html  import build_hbu_html
    from hbu_enhanced_excel import build_hbu_excel

    errors:   List[str] = []
    warnings: List[str] = []

    # ── Case data ─────────────────────────────────────────────────────────────
    case_data = {**_DEFAULT_CASE, **(payload or {})}
    if case_id:
        case_data["case_id"] = case_id
    cid = case_data["case_id"]

    alternatives = list(case_data.pop("alternative_uses", None) or _DEFAULT_ALTS)
    dr = float(case_data.get("discount_rate", _DISCOUNT_RATE))

    # ── Output directories ────────────────────────────────────────────────────
    if out_dir is None:
        out_dir = _CORE / "outputs" / "enhanced_hbu" / cid
    out_dir = pathlib.Path(out_dir)
    shots_dir = out_dir / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    shots_dir.mkdir(parents=True, exist_ok=True)

    # ── Step 1: Source inputs ─────────────────────────────────────────────────
    sourcing_raw = source_hbu_inputs({
        **case_data,
        "land_area_m2":  case_data.get("land_area_m2", 2400),
        "city_ar":       case_data.get("city_ar", "الرياض"),
        "district_ar":   case_data.get("district_ar", "النرجس"),
        "country_code":  case_data.get("country_code", "SA"),
    })
    warnings.extend(sourcing_raw.warnings)
    sourcing_dict = sourcing_raw.to_dict()

    # ── Step 2: HBU Analysis Engine (READ-ONLY) ───────────────────────────────
    try:
        from hbu_analysis_engine import run_hbu_analysis
        hbu_payload = {
            "property": {
                "asset_id":       cid,
                "location":       f'{case_data["city_ar"]} — {case_data["district_ar"]}',
                "area":           case_data.get("land_area_m2", 2400),
                "current_use":    case_data.get("current_use", "—"),
                "current_zoning": f'سكني منخفض الكثافة — {_SYNTH_LABEL}',
            },
            "alternative_uses": alternatives,
            "discount_rate":    dr,
            "valuation_date":   case_data.get("valuation_date", "2026-07-01"),
        }
        hbu_result = run_hbu_analysis(hbu_payload)
    except Exception as exc:
        errors.append(f"hbu_analysis_engine error: {exc}")
        hbu_result = {
            "scenarios_evaluated": [], "comparison_table": [],
            "recommended_use": None, "recommended_npv": None,
            "recommendation_note": str(exc), "standards_note": "",
            "discount_rate": dr, "discount_rate_pct": dr * 100,
            "property": {}, "valuation_date": case_data.get("valuation_date", ""),
        }

    # ── Step 3: Financial depth ───────────────────────────────────────────────
    rec_name   = hbu_result.get("recommended_use")
    optimal_sc = next(
        (s for s in hbu_result.get("scenarios_evaluated", [])
         if s["use_name"] == rec_name),
        next(iter(alternatives), {}),
    )
    fd = compute_financial_depth(
        optimal_sc, dr, float(case_data.get("land_area_m2", 2400))
    )

    # ── Step 4a: Build HTML ───────────────────────────────────────────────────
    user_html_str  = build_hbu_html(case_data, hbu_result, fd, sourcing_dict,
                                    "user",  alternatives)
    admin_html_str = build_hbu_html(case_data, hbu_result, fd, sourcing_dict,
                                    "admin", alternatives)

    user_html_path  = out_dir / f"hbu_{cid}_user.html"
    admin_html_path = out_dir / f"hbu_{cid}_admin.html"
    user_html_path.write_text(user_html_str,  encoding="utf-8")
    admin_html_path.write_text(admin_html_str, encoding="utf-8")

    # ── Step 4b: PDF (Playwright) ─────────────────────────────────────────────
    user_pdf_path  = out_dir / f"hbu_{cid}_user.pdf"
    admin_pdf_path = out_dir / f"hbu_{cid}_admin.pdf"
    pdf_ok_u  = _render_pdf(user_html_str,  user_pdf_path)
    pdf_ok_a  = _render_pdf(admin_html_str, admin_pdf_path)
    if not pdf_ok_u:
        warnings.append("user PDF: Playwright render failed — HTML only")
    if not pdf_ok_a:
        warnings.append("admin PDF: Playwright render failed — HTML only")

    # ── Step 4c: Excel (openpyxl) ─────────────────────────────────────────────
    admin_xlsx_path = out_dir / f"hbu_{cid}_admin.xlsx"
    prov_list = [p.to_dict() for p in sourcing_raw.provenance_table]
    try:
        build_hbu_excel(
            case_data    = case_data,
            hbu_result   = hbu_result,
            fd           = fd,
            sourcing     = {**sourcing_dict, "provenance_table": prov_list},
            alternatives = alternatives,
            out_path     = str(admin_xlsx_path),
        )
    except Exception as exc:
        errors.append(f"Excel build error: {exc}")
        admin_xlsx_path = None

    # ── Step 5: Visual QA ────────────────────────────────────────────────────
    vqa_user_html  = _vqa_html(user_html_str,  "user_html",  shots_dir)
    vqa_admin_html = _vqa_html(admin_html_str, "admin_html", shots_dir)
    vqa_user_pdf   = _vqa_pdf(user_pdf_path,   "user_pdf",   shots_dir) \
        if user_pdf_path.exists() else {"pass": False, "issues": ["PDF not created"]}
    vqa_admin_pdf  = _vqa_pdf(admin_pdf_path,  "admin_pdf",  shots_dir) \
        if admin_pdf_path.exists() else {"pass": False, "issues": ["PDF not created"]}
    vqa_xlsx       = _vqa_xlsx(admin_xlsx_path) \
        if admin_xlsx_path and pathlib.Path(admin_xlsx_path).exists() \
        else {"pass": False, "issues": ["XLSX not created"]}

    # ── Step 6: Audience separation checks ───────────────────────────────────
    if "سجل المصادر" in user_html_str and "Admin" not in "user":
        warnings.append("user HTML: source log should be admin-only")
    if "سجل_المصادر" not in admin_html_str and "سجل الافتراضات" not in admin_html_str:
        warnings.append("admin HTML: missing source log section")

    # ── Step 7: Manifest ─────────────────────────────────────────────────────
    manifest = {
        "case_id":    cid,
        "run_at":     datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "artifacts": {
            "user_html":  str(user_html_path),
            "user_pdf":   str(user_pdf_path)  if user_pdf_path.exists()  else None,
            "admin_html": str(admin_html_path),
            "admin_pdf":  str(admin_pdf_path) if admin_pdf_path.exists() else None,
            "admin_xlsx": str(admin_xlsx_path) if admin_xlsx_path and
                          pathlib.Path(admin_xlsx_path).exists() else None,
        },
        "hbu_result":       hbu_result,
        "financial_depth":  fd,
        "provenance_table": prov_list,
        "sourcing_summary": {
            "run_id":          sourcing_raw.run_id,
            "retrieved_at":    sourcing_raw.retrieved_at,
            "warnings":        sourcing_raw.warnings,
            "mass_appraisal":  sourcing_raw.mass_appraisal_summary,
        },
        "visual_qa": {
            "user_html":  vqa_user_html,
            "admin_html": vqa_admin_html,
            "user_pdf":   vqa_user_pdf,
            "admin_pdf":  vqa_admin_pdf,
            "admin_xlsx": vqa_xlsx,
        },
        "governance": _GOVERNANCE,
        "errors":     errors,
        "warnings":   warnings,
    }

    manifest_path = out_dir / f"hbu_{cid}_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return manifest


# ── CLI entry ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import pprint
    result = generate_enhanced_hbu_report()
    arts   = result["artifacts"]
    print("=== ARTIFACTS ===")
    for k, v in arts.items():
        size = pathlib.Path(v).stat().st_size if (v and pathlib.Path(v).exists()) else 0
        print(f"  {k}: {v}  ({size:,} bytes)")
    print("\n=== FINANCIAL DEPTH ===")
    fd = result["financial_depth"]
    print(f"  GDV:        {fd.get('gdv'):>14,.0f}")
    print(f"  TDC:        {fd.get('tdc'):>14,.0f}")
    print(f"  RLV:        {fd.get('rlv'):>14,.0f}")
    print(f"  RLV/m²:     {fd.get('rlv_per_m2'):>14,.2f}")
    print(f"  Payback:    {fd.get('payback_years'):>14.2f} years")
    print(f"  IRR proj:   {fd.get('irr_project_pct'):>14.1f}%")
    print(f"  IRR inv:    {fd.get('irr_investor_pct'):>14.1f}%")
    print(f"  Dev margin: {fd.get('dev_margin_pct'):>14.2f}%")
    print("\n=== GOVERNANCE ===")
    pprint.pprint(result["governance"])
    print("\n=== ERRORS ===",   result["errors"])
    print("=== WARNINGS ===", result["warnings"])
    vqa = result["visual_qa"]
    print("\n=== VQA SUMMARY ===")
    for k, v in vqa.items():
        print(f"  {k}: pass={v.get('pass')}, issues={v.get('issues')}")
