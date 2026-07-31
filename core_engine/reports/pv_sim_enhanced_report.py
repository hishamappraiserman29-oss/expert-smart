"""
pv_sim_enhanced_report.py
Orchestrator — generates all 5 enhanced simulation report formats:

  user PDF    — Playwright, advisory watermark, no source log
  user HTML   — advisory watermark, provenance + methods + comparison
  admin PDF   — Playwright, full content including source log
  admin HTML  — provenance + methods + comparison + source log
  admin Excel — 10 base sheets + 2 new sheets + 3 charts

Governance (enforced throughout):
  advisory_only=True · certification_ready=False
  fake_signature_created=False · non_certified=True
  Web inputs = Draft governed — no certified model training
  No local paths in any output
  No FPDF — Playwright only for PDF
"""
from __future__ import annotations

import datetime
import pathlib
import sys
from typing import Any, Dict, Optional

_CORE = pathlib.Path(__file__).resolve().parent.parent
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

_SAFETY: Dict[str, Any] = {
    "advisory_only":          True,
    "certification_ready":    False,
    "fake_signature_created": False,
    "non_certified":          True,
    "not_real_training":      True,
}


def generate_enhanced_simulation_report(
    body: Dict[str, Any],
    outputs_dir: pathlib.Path,
    run_id: str = "",
    currency: str = "QAR",
) -> Dict[str, Any]:
    """
    Generate all 5 enhanced simulation report formats for the given body.

    Returns
    -------
    {
      "run_id"          : str,
      "artifacts"       : { user_html, user_pdf, admin_html, admin_pdf, admin_xlsx },
      "provenance_table": [...],
      "methods_result"  : {...},
      "sourcing_result" : {...},
      "governance"      : _SAFETY,
      "warnings"        : [...],
      "errors"          : [...],
    }
    """
    if not run_id:
        run_id = "ENH_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    outputs_dir = pathlib.Path(outputs_dir)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    errors: list = []
    warnings: list = []

    # ── Import base simulation functions (READ-ONLY) ──────────────────────────
    try:
        from pv_report_simulation_endpoint import (
            _extract_inputs,
            _run_three_scenarios,
            _shadow_sales_comparison,
            _shadow_income_approach,
            _shadow_cost_approach,
            _shadow_dcf,
            _shadow_reconciliation,
            _build_comparison_table,
            _build_simulation_html_v2,
            _render_playwright_pdf,
            _build_simulation_excel_v2,
            _stub_pdf,
        )
    except ImportError as exc:
        errors.append(f"base simulation import failed: {exc}")
        return {"run_id": run_id, "errors": errors, "governance": _SAFETY}

    # ── Source inputs (READ-ONLY) ─────────────────────────────────────────────
    from .pv_sim_sourced_inputs import source_subject_inputs
    sourcing_result = source_subject_inputs(body)
    warnings.extend(sourcing_result.warnings)

    # ── Base simulation ───────────────────────────────────────────────────────
    inputs    = _extract_inputs(body)
    meta      = _build_meta(body, inputs)
    scenarios = _run_three_scenarios(inputs)

    weights = {
        "sales":  inputs["weight_sales"],
        "income": inputs["weight_income"],
        "cost":   inputs["weight_cost"],
    }
    sh_sales  = _shadow_sales_comparison(inputs, currency)
    sh_income = _shadow_income_approach(inputs, currency)
    sh_cost   = _shadow_cost_approach(inputs, currency)
    sh_dcf    = _shadow_dcf(inputs, currency)
    sh_recon  = _shadow_reconciliation(sh_sales, sh_income, sh_cost, weights, currency)
    shadow_results   = [sh_sales, sh_income, sh_cost, sh_dcf, sh_recon]
    comparison_table = _build_comparison_table(scenarios, shadow_results)

    # ── Apply methods to subject property ─────────────────────────────────────
    from .pv_sim_market_methods import apply_methods_to_subject
    methods_result = apply_methods_to_subject(
        sourcing_result, body, scenarios, shadow_results, currency
    )

    # ── Build HTML (user + admin) and PDFs ────────────────────────────────────
    from .pv_sim_enhanced_html import inject_enhanced_sections

    artifacts: Dict[str, Optional[str]] = {
        "user_html":  None,
        "user_pdf":   None,
        "admin_html": None,
        "admin_pdf":  None,
        "admin_xlsx": None,
    }

    for audience in ("user", "admin"):
        base_html = _build_simulation_html_v2(
            meta, scenarios, shadow_results, comparison_table, audience, currency
        )
        enhanced_html = inject_enhanced_sections(
            base_html, sourcing_result, methods_result, audience, currency
        )

        html_path = outputs_dir / f"simulation_{run_id}_{audience}.html"
        html_path.write_text(enhanced_html, encoding="utf-8")
        artifacts[f"{audience}_html"] = str(html_path)

        pdf_path = outputs_dir / f"simulation_{run_id}_{audience}.pdf"
        pdf_ok   = _render_playwright_pdf(html_path, pdf_path)
        if not pdf_ok:
            warnings.append(f"Playwright PDF failed ({audience}) — using stub")
            _stub_pdf(pdf_path, f"محاكاة معززة — {audience}")
        artifacts[f"{audience}_pdf"] = str(pdf_path)

    # ── Build admin Excel + enhanced sheets ───────────────────────────────────
    from .pv_sim_enhanced_excel import add_enhanced_sheets

    xl_fname = f"simulation_{run_id}_admin.xlsx"
    xl_ok    = _build_simulation_excel_v2(
        meta, scenarios, shadow_results, comparison_table, outputs_dir, xl_fname, currency
    )
    xl_path  = outputs_dir / xl_fname

    if xl_ok and xl_path.exists():
        try:
            from openpyxl import load_workbook
            wb = load_workbook(str(xl_path))
            wb = add_enhanced_sheets(wb, sourcing_result.provenance_table, methods_result)
            wb.save(str(xl_path))
        except Exception as exc:
            errors.append(f"Excel enhanced sheets failed: {exc}")
    else:
        errors.append("Base Excel generation failed — enhanced sheets skipped")

    artifacts["admin_xlsx"] = str(xl_path) if xl_path.exists() else None

    return {
        "run_id":           run_id,
        "artifacts":        artifacts,
        "provenance_table": [p.to_dict() for p in sourcing_result.provenance_table],
        "methods_result":   methods_result.to_dict(),
        "sourcing_result":  sourcing_result.to_dict(),
        "governance":       _SAFETY,
        "warnings":         warnings,
        "errors":           errors,
    }


def _build_meta(body: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
    city     = body.get("city_ar", "")
    district = body.get("district_ar", "")
    return {
        "case_id":          body.get("case_id", "—"),
        "simulation_date":  body.get(
            "simulation_date",
            datetime.datetime.now().strftime("%Y-%m-%d"),
        ),
        "asset_type_ar":    body.get("asset_type_ar", "عقار"),
        "country_ar":       body.get("country_ar", ""),
        "city_ar":          city,
        "district_ar":      district,
        "property_location": f"{city} — {district}".strip(" —"),
        "land_area_m2":     inputs["land_area_m2"],
        "built_up_area_m2": inputs["built_up_area_m2"],
        "weight_sales":     inputs["weight_sales"],
        "weight_income":    inputs["weight_income"],
        "weight_cost":      inputs["weight_cost"],
    }
