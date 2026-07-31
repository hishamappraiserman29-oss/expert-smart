"""
professional_valuation_core_pdf_generator.py
Generates three genuinely distinct core valuation report PDFs:
  traditional_report.pdf  — 8+ pages
  detailed_report.pdf     — 14+ pages
  professional_report.pdf — 20+ pages

Uses Chrome headless for proper PDF rendering.
All report content is in English. advisory_only=True | not_real_training=True
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from professional_valuation_core_report_examples import (
    SUBJECT, COMPARABLES, ADJUSTMENTS, ADJUSTED_PRICES_PER_SQM,
    INDICATED_MARKET_VALUE_PER_SQM, INDICATED_MARKET_VALUE,
    INCOME, COST, AVM, RECONCILIATION,
    DCF_5YEAR, DCF_10YEAR, SCENARIOS, PROBABILITY_WEIGHTED_VALUE,
    SENSITIVITY_MATRIX, RISKS, STANDARDS, DATA_INPUTS,
    METHOD_SELECTION, HBU, RECONCILIATION_SCORECARD,
    ADVISORY_NOTE,
)

_CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
_GENERATED_AT = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', Arial, Helvetica, sans-serif;
       font-size: 10pt; color: #1a1a1a; line-height: 1.45; }
h1 { font-size: 19pt; color: #1a3a5c; text-align: center; margin-bottom: 8px; letter-spacing: .5px; }
h2 { font-size: 12pt; color: #1a3a5c; border-bottom: 2px solid #1a3a5c;
     padding-bottom: 3px; margin: 18px 0 7px; }
h3 { font-size: 10.5pt; color: #2c5f8a; margin: 12px 0 4px; }
p  { margin: 5px 0; }
ul { margin: 4px 0 4px 18px; }
li { margin: 2px 0; font-size: 9.5pt; }
table { width: 100%; border-collapse: collapse; margin: 7px 0; font-size: 9.5pt; }
th { background: #1a3a5c; color: #fff; padding: 5px 8px; text-align: left; }
td { padding: 4px 8px; border: 1px solid #c8d4e0; vertical-align: top; }
tr:nth-child(even) td { background: #f0f5fa; }
.kv td:first-child { font-weight: bold; background: #e4edf5; width: 36%; }
.advisory { background: #fff8e1; border: 2px solid #e6a817;
            padding: 10px 14px; margin: 12px 0; border-radius: 4px; font-size: 9.5pt; }
.advisory strong { color: #8a5700; font-size: 10pt; }
.cover { text-align: center; padding: 28px 20px; border: 3px solid #1a3a5c;
         margin-bottom: 18px; border-radius: 8px; background: #f5f9fd; }
.cover .sub { font-size: 11pt; color: #555; margin: 5px 0 14px; }
.cover .badge { display: inline-block; background: #fff3cd; border: 1px solid #e6a817;
                color: #8a5700; padding: 3px 12px; border-radius: 12px;
                font-size: 9pt; font-weight: bold; margin: 6px 0 14px; }
.val-box { background: #e4edf5; border-left: 4px solid #1a3a5c; padding: 8px 14px;
           margin: 9px 0; font-size: 11pt; font-weight: bold; color: #1a3a5c; }
.note { font-size: 8.5pt; color: #666; font-style: italic; margin-top: 3px; }
.ok  { color: #1e7e34; font-weight: bold; }
.warn{ color: #856404; font-weight: bold; }
.nok { color: #721c24; font-weight: bold; }
.hl  { background: #fffde7; padding: 7px 11px; border-left: 3px solid #f9a825; margin: 7px 0; }
.footer { margin-top: 20px; border-top: 1px solid #bbb; padding-top: 6px;
          font-size: 8pt; color: #888; text-align: center; }
@page { size: A4; margin: 16mm 14mm; }
"""

# ── HTML primitives ──────────────────────────────────────────────────────────

def _kv(pairs: list[tuple]) -> str:
    rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in pairs)
    return f'<table class="kv">{rows}</table>'

def _tbl(headers: list[str], rows: list[list], note: str = "") -> str:
    ths = "".join(f"<th>{h}</th>" for h in headers)
    trs = "".join(
        "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
        for row in rows
    )
    n = f'<p class="note">* {note}</p>' if note else ""
    return f"<table><thead><tr>{ths}</tr></thead><tbody>{trs}</tbody></table>{n}"

def _sec(num: str, title: str, body: str) -> str:
    return f'<h2>{num}. {title}</h2>\n{body}\n'

def _wrap(title: str, body: str) -> str:
    return (
        "<!DOCTYPE html>\n<html lang='en'>\n<head>\n"
        f"<meta charset='UTF-8'/>\n<title>{title}</title>\n"
        f"<style>{_CSS}</style>\n</head>\n<body>\n{body}\n</body>\n</html>"
    )

# ── Shared section builders ──────────────────────────────────────────────────

def _cover(report_type_label: str, depth_label: str) -> str:
    s = SUBJECT
    return (
        f'<div class="cover">'
        f'<h1>{report_type_label.upper()}</h1>'
        f'<p class="sub">Professional Real Estate Valuation — {depth_label}</p>'
        f'<div class="badge">ADVISORY ONLY — NOT FOR OFFICIAL USE</div>'
        + _kv([
            ("Report Reference",  s["request_id"]),
            ("Valuation Date",    s["valuation_date"]),
            ("Inspection Date",   s["inspection_date"]),
            ("Property Address",  s["property_address"]),
            ("Property Type",     s["property_type"]),
            ("Gross Floor Area",  f'{s["gross_floor_area_m2"]} m²'),
            ("Valuation Purpose", s["purpose"]),
            ("Basis of Value",    s["basis_of_value"]),
            ("Currency",          s["currency"]),
            ("Client",            s["client"]),
            ("Generated",         _GENERATED_AT),
            ("Status",            "ADVISORY ONLY — Expert Review Required"),
        ])
        + "</div>"
    )

def _advisory_banner() -> str:
    return (
        '<div class="advisory"><strong>⚠ IMPORTANT ADVISORY NOTICE</strong><br/>'
        "This report is preliminary and advisory only. It is not valid for official, "
        "legal, or financial use without review and final certification by a licensed "
        "valuation expert. All indicated values are illustrative and must not be used "
        "in any transaction without expert confirmation. "
        f"<em>{ADVISORY_NOTE}</em></div>"
    )

def _property_identification() -> str:
    s = SUBJECT
    return _kv([
        ("Property Address",    s["property_address"]),
        ("Plot Number",         s["plot_number"]),
        ("District",            s["district"]),
        ("City / Country",      f'{s["city"]}, {s["country"]}'),
        ("Coordinates",         s["coordinates"]),
        ("Property Type",       s["property_type"]),
        ("Tenure",              s["tenure"]),
        ("Zoning",              s["zoning"]),
        ("Building Permit",     f'Issued {s["building_permit_year"]}'),
        ("Gross Floor Area",    f'{s["gross_floor_area_m2"]} m²'),
        ("Net Internal Area",   f'{s["net_internal_area_m2"]} m²'),
        ("Floor Level",         s["floor"]),
        ("Building Age",        f'{s["age_years"]} years'),
        ("Bedrooms / Bathrooms",f'{s["bedrooms"]} / {s["bathrooms"]}'),
        ("Parking",             s["parking"]),
        ("Legal Status",        s["legal_status"]),
    ])

def _purpose_scope_table() -> str:
    s = SUBJECT
    return _kv([
        ("Purpose of Valuation",  s["purpose"]),
        ("Basis of Value",        s["basis_of_value"]),
        ("Client / Instructing Party", s["client"]),
        ("Client Type",           s["client_type"]),
        ("Intended Use",          "Mortgage / Collateral Valuation"),
        ("Intended Users",        "Instructing institution; licensed valuation expert"),
        ("Valuation Date",        s["valuation_date"]),
        ("Inspection Date",       s["inspection_date"]),
        ("Report Date",           s["report_date"]),
        ("Currency",              s["currency"]),
    ])

def _data_quality_section() -> str:
    return (
        "<p>The data quality assessment evaluates the completeness and reliability "
        "of inputs used in this valuation report.</p>"
        + _kv([
            ("Data Quality Level",           "Acceptable (Illustrative)"),
            ("Minimum Required Fields",      "Confirmed — Property address, type, area, purpose, basis of value"),
            ("Comparable Evidence",          "5 comparable sales identified within 2 km"),
            ("Income Data",                  "Market rent and vacancy rate: indicative"),
            ("Cost Data",                    "RCN and depreciation: indicative"),
            ("Legal / Title",                "Indicative — confirmation pending"),
            ("Report Readiness",             "Advisory Draft — Expert Review Required"),
            ("Missing Critical Inputs",      "Title confirmation; legal review; formal inspection certificate"),
        ])
        + '<p class="note">All values are illustrative. Report readiness cannot exceed "advisory draft" without confirmed inputs.</p>'
    )

def _applied_standards_brief() -> str:
    return (
        "<p>This valuation has been prepared having regard to the following standards:</p>"
        + _tbl(
            ["Standard", "Reference", "Status"],
            [
                ["International Valuation Standards", "IVS 2025 (IVSC)", "Addressed"],
                ["RICS Red Book",                     "RICS VPS / PS 2025", "Addressed"],
                ["Saudi FRA Requirements",            "FRA SA",           "Addressed"],
                ["Basel III Collateral Guidance",     "Basel III / IV",   "Noted"],
            ]
        )
    )

def _market_approach_simple() -> str:
    rows = [[c["id"], c["address"], f'{c["area_m2"]} m²',
             f'SAR {c["price_sar"]:,}', f'SAR {c["price_per_sqm"]:,}',
             c["sale_date"]] for c in COMPARABLES]
    tbl = _tbl(["#", "Address", "Area", "Sale Price", "SAR/m²", "Date"], rows,
               note=ADVISORY_NOTE)
    adj_rows = [
        ["C1", "+0%", "+3%", "+0%", "-2%", "+0%", "SAR 6,425"],
        ["C2", "-2%", "-5%", "+0%", "+2%", "+0%", "SAR 6,531"],
        ["C3", "-5%", "+4%", "-3%", "-3%", "+4%", "SAR 6,232"],
        ["C4", "-3%", "-3%", "+0%", "+3%", "+0%", "SAR 6,557"],
        ["C5", "+0%", "-8%", "+0%", "+4%", "+0%", "SAR 6,512"],
    ]
    adj_tbl = _tbl(["Comp", "Location", "Size", "Condition", "Floor", "Parking", "Adj. SAR/m²"],
                   adj_rows, note="Net adjustments applied to comparable sale prices per m²")
    return (
        "<p>The Market (Sales Comparison) Approach estimates value by comparing the subject "
        "property with recent sales of similar properties, adjusted for material differences.</p>"
        + "<h3>Comparable Sales Summary</h3>" + tbl
        + "<h3>Adjustment Summary (Mini Example)</h3>" + adj_tbl
        + '<div class="val-box">Market Approach — Indicated Value: '
        f'≈ SAR {INDICATED_MARKET_VALUE:,} '
        f'(SAR {INDICATED_MARKET_VALUE_PER_SQM:,}/m² × {SUBJECT["gross_floor_area_m2"]} m²)</div>'
        + '<p class="note">' + ADVISORY_NOTE + "</p>"
    )

def _income_approach_simple() -> str:
    I = INCOME
    rows = [
        ["Gross Market Rent (Annual)",    f'SAR {I["gross_market_rent_annual"]:,}'],
        [f'Less: Vacancy ({I["vacancy_rate_pct"]}%)', f'(SAR {I["vacancy_deduction"]:,})'],
        ["Effective Gross Income (EGI)",  f'SAR {I["effective_gross_income"]:,}'],
        ["Less: Total Operating Expenses",f'(SAR {I["total_opex"]:,})'],
        ["Net Operating Income (NOI)",    f'SAR {I["net_operating_income"]:,}'],
        [f'Capitalisation Rate',          f'{I["cap_rate_pct"]}%'],
        ["Indicated Income Value",        f'SAR {I["indicated_income_value"]:,}'],
    ]
    return (
        "<p>The Income (Capitalisation) Approach converts the Net Operating Income (NOI) "
        "into a capital value by applying a market-derived capitalisation rate.</p>"
        + _tbl(["Item", "Amount (SAR)"], rows, note=ADVISORY_NOTE)
        + '<div class="val-box">Income Approach — Indicated Value: '
        f'SAR {I["indicated_income_value"]:,}</div>'
    )

def _cost_approach_simple() -> str:
    C = COST
    rows = [
        ["Land Area",                       f'{C["land_area_m2"]} m²'],
        ["Land Value (SAR/m²)",             f'SAR {C["land_value_per_sqm"]:,}'],
        ["Land Value",                      f'SAR {C["land_value"]:,}'],
        ["Gross Replacement Cost (GRC)",    f'SAR {C["gross_replacement_cost"]:,}'],
        [f'Less: Depreciation ({C["physical_depreciation_pct"]}%)', f'(SAR {C["total_depreciation_sar"]:,})'],
        ["Depreciated Improvement Value",   f'SAR {C["depreciated_improvement_value"]:,}'],
        ["Indicated Cost Value",            f'SAR {C["indicated_cost_value"]:,}'],
    ]
    return (
        "<p>The Cost Approach estimates value as the land value plus the depreciated "
        "replacement cost of improvements. Depreciation is calculated using the "
        "age-to-life method.</p>"
        + _tbl(["Component", "Amount (SAR)"], rows, note=ADVISORY_NOTE)
        + '<div class="val-box">Cost Approach — Indicated Value: '
        f'SAR {C["indicated_cost_value"]:,}</div>'
    )

def _avm_section() -> str:
    A = AVM
    return (
        "<p>An Automated Valuation Model (AVM) is used as a supporting cross-check. "
        "It does not replace the three traditional approaches.</p>"
        + _kv([
            ("Model Type",          A["model_type"]),
            ("Confidence Level",    A["confidence_level"]),
            ("Data Sources",        f'{A["data_sources_count"]} independent sources'),
            ("Comparables Used",    str(A["comparables_used"])),
            ("AVM Low (95% CI)",    f'SAR {A["avm_low_95pct"]:,}'),
            ("AVM Midpoint",        f'SAR {A["avm_midpoint"]:,}'),
            ("AVM High (95% CI)",   f'SAR {A["avm_high_95pct"]:,}'),
            ("Advisory Note",       A["note"]),
        ])
    )

def _reconciliation_simple() -> str:
    R = RECONCILIATION
    rows = [
        ["Market Approach",  f'SAR {R["market_value"]:,}',  f'{R["market_approach_weight_pct"]}%',
         f'SAR {R["market_contribution"]:,}'],
        ["Income Approach",  f'SAR {R["income_value"]:,}',  f'{R["income_approach_weight_pct"]}%',
         f'SAR {R["income_contribution"]:,}'],
        ["Cost Approach",    f'SAR {R["cost_value"]:,}',    f'{R["cost_approach_weight_pct"]}%',
         f'SAR {R["cost_contribution"]:,}'],
        ["Weighted Total",   "—",                           "100%",
         f'SAR {R["weighted_total"]:,}'],
        ["<strong>Adopted Value</strong>", f'<strong>SAR {R["adopted_value"]:,}</strong>', "—", "—"],
    ]
    return (
        "<p>" + R["rationale"] + "</p>"
        + _tbl(["Approach", "Indicated Value", "Weight", "Contribution"], rows)
        + '<div class="val-box">Reconciled Market Value: SAR '
        f'{R["adopted_value"]:,} (illustrative)</div>'
    )

def _value_conclusion() -> str:
    R = RECONCILIATION
    return (
        '<div class="hl">'
        f'<strong>Adopted Market Value (Illustrative): SAR {R["adopted_value"]:,}</strong><br/>'
        f'Property: {SUBJECT["property_address"]}<br/>'
        f'Basis of Value: {SUBJECT["basis_of_value"]}<br/>'
        f'Valuation Date: {SUBJECT["valuation_date"]}<br/>'
        "Status: ADVISORY ONLY — Requires expert review and certification before official use."
        "</div>"
        + '<p class="note">' + ADVISORY_NOTE + "</p>"
    )

def _assumptions_brief() -> str:
    items = [
        "This report is advisory only and does not constitute a certified valuation.",
        "All comparable sales are indicative and have not been independently verified.",
        "The inspection was visual only; no structural surveys or specialist reports were undertaken.",
        "Legal title and ownership have not been independently verified; assumed free of encumbrances.",
        "All values are expressed in Saudi Riyal (SAR) as at the valuation date.",
        "Market conditions are as at the valuation date; no allowance for future changes.",
        "No allowance has been made for taxation, acquisition costs, or disposal costs.",
        "Expert review and formal certification are required before this report may be used officially.",
    ]
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"

def _advisory_notice() -> str:
    return (
        '<div class="advisory"><strong>Expert Review Required</strong><br/>'
        "This report has been prepared as an advisory draft only. It must be reviewed, "
        "verified, and certified by a qualified and licensed valuation expert before it "
        "may be used for any official, legal, financial, or regulatory purpose.<br/><br/>"
        "<strong>certification_ready = False | advisory_only = True | fake_approval_created = False</strong>"
        "</div>"
    )

def _footer() -> str:
    return (
        f'<div class="footer">Advisory Report — Expert_Smart Professional Valuation System — '
        f'Generated {_GENERATED_AT} — Not for official use without expert certification</div>'
    )

# ── Traditional Report HTML ─────────────────────────────────────────────────

def build_traditional_html() -> str:
    body = (
        _cover("Traditional Valuation Report", "Concise Three-Approach Report")
        + _advisory_banner()
        + _sec("1", "Executive Summary",
            "<p>This Traditional Valuation Report presents a concise analysis of the subject property "
            "using the three standard valuation approaches: Market (Sales Comparison), "
            "Income (Capitalisation), and Cost. An AVM-assisted cross-check is included.</p>"
            "<p>The subject property is a residential apartment in Al-Narjes District, North Riyadh, "
            f'with a gross floor area of {SUBJECT["gross_floor_area_m2"]} m². '
            f'The valuation date is {SUBJECT["valuation_date"]}.</p>'
            "<p>This report is advisory only. All values are illustrative pending expert review.</p>")
        + _sec("2", "Purpose and Scope", _purpose_scope_table())
        + _sec("3", "Asset Identification", _property_identification())
        + _sec("4", "Data Quality and Completeness", _data_quality_section())
        + _sec("5", "Applied Standards", _applied_standards_brief())
        + _sec("6", "Traditional Valuation Methods Overview",
            "<p>This report applies the three traditional approaches recognised under IVS 2025:</p>"
            "<ul>"
            "<li><strong>Market Approach</strong> — Sales comparison using adjusted comparable transactions.</li>"
            "<li><strong>Income Approach</strong> — Direct capitalisation of Net Operating Income.</li>"
            "<li><strong>Cost Approach</strong> — Land value plus depreciated replacement cost of improvements.</li>"
            "</ul>"
            "<p>An AVM-assisted indication is included as a supporting tool only.</p>")
        + _sec("7", "Market Approach", _market_approach_simple())
        + _sec("8", "Income Approach", _income_approach_simple())
        + _sec("9", "Cost Approach", _cost_approach_simple())
        + _sec("10", "AVM-Assisted Indication", _avm_section())
        + _sec("11", "Reconciliation", _reconciliation_simple())
        + _sec("12", "Value Conclusion", _value_conclusion())
        + _sec("13", "Assumptions and Limiting Conditions", _assumptions_brief())
        + _sec("14", "Advisory / Expert Review Notice", _advisory_notice())
        + "<h2>Appendix — Abbreviations</h2>"
        + _tbl(["Abbreviation", "Definition"], [
            ["AVM",  "Automated Valuation Model"],
            ["EGI",  "Effective Gross Income"],
            ["GFA",  "Gross Floor Area"],
            ["IVS",  "International Valuation Standards"],
            ["NOI",  "Net Operating Income"],
            ["RCN",  "Replacement Cost New"],
            ["RICS", "Royal Institution of Chartered Surveyors"],
            ["SAR",  "Saudi Arabian Riyal"],
        ])
        + _footer()
    )
    return _wrap("Traditional Valuation Report", body)


# ── Detailed Report HTML ─────────────────────────────────────────────────────

def _comparable_grid_detailed() -> str:
    rows = [[c["id"], c["address"][:30], f'{c["area_m2"]}', f'{c["price_per_sqm"]:,}',
             c["condition"], c["floor"], c["parking"], c["sale_date"],
             f'{c["distance_km"]} km'] for c in COMPARABLES]
    return _tbl(
        ["#", "Address", "m²", "SAR/m²", "Condition", "Floor", "Parking", "Date", "Dist."],
        rows, note=ADVISORY_NOTE
    )

def _adjustment_matrix() -> str:
    adj_names = list(ADJUSTMENTS.keys())
    headers = ["Adjustment"] + [c["id"] for c in COMPARABLES]
    rows = []
    for key in adj_names:
        a = ADJUSTMENTS[key]
        row = [a["label"]] + [f'{v:+d}%' for v in a["values"]]
        rows.append(row)
    total_adj = []
    for i in range(len(COMPARABLES)):
        total = sum(ADJUSTMENTS[k]["values"][i] for k in adj_names)
        total_adj.append(f'{total:+d}%')
    rows.append(["<strong>Net Adjustment</strong>"] + [f"<strong>{v}</strong>" for v in total_adj])
    rows.append(["<strong>Adjusted SAR/m²</strong>"] +
                [f"<strong>SAR {v:,}</strong>" for v in ADJUSTED_PRICES_PER_SQM])
    return _tbl(headers, rows, note="Adjustments applied to comparable sale prices per m²")

def _income_full() -> str:
    I = INCOME
    rows = [
        ["Gross Market Rent (Annual)",        f'SAR {I["gross_market_rent_annual"]:,}', "100.0%"],
        [f'Less: Vacancy ({I["vacancy_rate_pct"]}%)',  f'(SAR {I["vacancy_deduction"]:,})', f'{I["vacancy_rate_pct"]}%'],
        ["Effective Gross Income (EGI)",      f'SAR {I["effective_gross_income"]:,}', ""],
        [f'Management Fee ({I["management_fee_pct"]}%)', f'(SAR {I["management_fee"]:,})', ""],
        [f'Maintenance ({I["maintenance_pct"]}%)',       f'(SAR {I["maintenance"]:,})',    ""],
        [f'Insurance ({I["insurance_pct"]}%)',           f'(SAR {I["insurance"]:,})',      ""],
        [f'Service Charge ({I["service_charge_pct"]}%)',f'(SAR {I["service_charge"]:,})', ""],
        ["Other Operating Expenses",          f'(SAR {I["other_opex"]:,})',       ""],
        ["Total Operating Expenses",          f'(SAR {I["total_opex"]:,})',        ""],
        ["Net Operating Income (NOI)",        f'SAR {I["net_operating_income"]:,}', ""],
        ["Capitalisation Rate",               f'{I["cap_rate_pct"]}%',             ""],
        ["Indicated Income Value (NOI / Cap)", f'SAR {I["indicated_income_value"]:,}', ""],
    ]
    return _tbl(["Item", "Amount (SAR)", "Note"], rows, note=ADVISORY_NOTE)

def _cost_full() -> str:
    C = COST
    rows = [
        ["Land Area",                          f'{C["land_area_m2"]} m²',              "Gross"],
        ["Land Value Rate",                    f'SAR {C["land_value_per_sqm"]:,} / m²', "Indicative"],
        ["Land Value",                         f'SAR {C["land_value"]:,}',             ""],
        ["Replacement Cost Rate (RCN)",        f'SAR {C["replacement_cost_per_sqm"]:,} / m²', "Indicative"],
        ["Gross Replacement Cost (GRC)",       f'SAR {C["gross_replacement_cost"]:,}', ""],
        ["Building Age",                       f'{C["age_years"]} years',              ""],
        ["Effective Life",                     f'{C["effective_life_years"]} years',   "Age/life method"],
        ["Physical Depreciation",              f'{C["physical_depreciation_pct"]}%',  f'SAR {C["total_depreciation_sar"]:,}'],
        ["Functional Obsolescence",            f'{C["functional_obsolescence_pct"]}%', "None identified"],
        ["Economic Obsolescence",              f'{C["economic_obsolescence_pct"]}%',  "None identified"],
        ["Total Depreciation",                 f'SAR {C["total_depreciation_sar"]:,}', ""],
        ["Depreciated Improvement Value",      f'SAR {C["depreciated_improvement_value"]:,}', ""],
        ["Indicated Cost Value",               f'SAR {C["indicated_cost_value"]:,}',  "Land + Improvements"],
    ]
    return _tbl(["Component", "Value", "Note"], rows, note=ADVISORY_NOTE)

def _dcf_mini() -> str:
    D = DCF_5YEAR
    rows = [[str(y), f'SAR {noi:,}', f'{pv:.4f}', f'SAR {pv_n:,}']
            for y, noi, pv, pv_n in zip(D["years"], D["noi"], D["pv_factor"], D["pv_noi"])]
    summary = [
        ["Cumulative PV of NOI",    f'SAR {D["cumulative_pv_noi"]:,}', "", ""],
        ["Terminal Value (Year 5)", f'SAR {D["terminal_value"]:,}',    "", ""],
        ["PV of Terminal Value",    f'SAR {D["pv_terminal"]:,}',       "", ""],
        ["Total DCF Value",         f'SAR {D["total_dcf_value"]:,}',   "", ""],
    ]
    return (
        f'<p>Discount Rate: {D["discount_rate_pct"]}% | Growth Rate: {D["growth_rate_pct"]}% | '
        f'Terminal Cap Rate: {D["terminal_cap_rate_pct"]}% | Projection: 5 years</p>'
        + _tbl(["Year", "NOI (SAR)", "PV Factor", "PV of NOI"], rows + summary,
               note=ADVISORY_NOTE)
    )

def _sensitivity_snapshot() -> str:
    cap_rates = [4.50, 5.00, 5.50]
    disc_rates = [7.5, 8.0, 8.5]
    data = {
        (4.50, 7.5): 1_282_000, (5.00, 7.5): 1_205_000, (5.50, 7.5): 1_143_000,
        (4.50, 8.0): 1_226_000, (5.00, 8.0): 1_154_000, (5.50, 8.0): 1_095_000,
        (4.50, 8.5): 1_174_000, (5.00, 8.5): 1_106_000, (5.50, 8.5): 1_051_000,
    }
    headers = ["Disc. Rate \\ Cap Rate"] + [f'{cr}%' for cr in cap_rates]
    rows = []
    for dr in disc_rates:
        row = [f'{dr}%'] + [f'SAR {data[(cr, dr)]:,}' for cr in cap_rates]
        rows.append(row)
    return _tbl(headers, rows, note="DCF value sensitivity to discount rate and capitalisation rate — Indicative")

def _risk_notes_section() -> str:
    rows = [[r["id"], r["category"], r["description"][:45],
             r["probability"], r["impact"], r["mitigation"][:40]] for r in RISKS[:6]]
    return (
        "<p>The following risks have been identified and assessed in the preparation of this report:</p>"
        + _tbl(["ID", "Category", "Description", "Probability", "Impact", "Mitigation"], rows,
               note=ADVISORY_NOTE)
    )

def _legal_doc_review() -> str:
    docs = [
        ["Title Deed",             "Registered",  "Freehold",   "Confirmed (indicative)"],
        ["Building Permit",        "Available",   "2018",       "Confirmed"],
        ["Survey / Floor Plans",   "Available",   "2019",       "Indicative"],
        ["Lease Agreements",       "Not Provided","—",          "Outstanding — required"],
        ["Service Charge Records", "Partial",     "2024/2025",  "Indicative"],
        ["Municipality Certificate","Available",  "2024",       "Confirmed"],
        ["Insurance Policy",       "Not Provided","—",          "Outstanding"],
        ["Mortgage / Encumbrance", "Clear (assumed)","—",       "Indicative"],
    ]
    return _tbl(["Document", "Status", "Date / Reference", "Notes"], docs,
                note="Document review is indicative only. Independent legal verification required.")

def _site_analysis() -> str:
    return _kv([
        ("District",             "Al-Narjes, North Riyadh"),
        ("Character",            "Established residential neighbourhood"),
        ("Access",               "Main arterial road + internal estate roads"),
        ("Public Transport",     "Bus routes within 500m; Metro extension planned"),
        ("Amenities",            "Schools, mosques, retail centres within 1–2 km"),
        ("Market Trend",         "Stable to slightly positive (illustrative)"),
        ("Demand Level",         "High — strong demand for 4BR apartments in this district"),
        ("Supply",               "Limited new supply; predominantly established stock"),
        ("Flood / Environment",  "No known flood risk; no environmental constraints identified"),
    ])

def _building_breakdown() -> str:
    rows = [
        ["Living Areas",    "Lounge, dining, family",  "75 m²",  "Good"],
        ["Bedrooms",        "4 bedrooms",              "70 m²",  "Good"],
        ["Bathrooms",       "3 bathrooms",             "18 m²",  "Good"],
        ["Kitchen",         "Fitted kitchen",          "14 m²",  "Good"],
        ["Utility / Store", "Utility room",            "5 m²",   "Good"],
        ["Entrance / Hall", "Entrance lobby",          "3 m²",   "Good"],
        ["Total GFA",       "—",                       "185 m²", "Good — 6 years old"],
    ]
    return _tbl(["Component", "Description", "Area", "Condition"], rows)

def _requirement_completion() -> str:
    items = [
        ("Property address and identification", "✓ Complete"),
        ("Property type and use",               "✓ Complete"),
        ("Gross floor area",                    "✓ Complete"),
        ("Valuation purpose and basis",         "✓ Complete"),
        ("Inspection completed",                "✓ Complete"),
        ("Comparable sales (min. 3)",           "✓ Complete (5 identified)"),
        ("Income data",                         "⚠ Indicative only"),
        ("Legal / title status",                "⚠ Confirmation pending"),
        ("Lease / tenancy agreements",          "✗ Not provided"),
        ("Structural survey",                   "✗ Not commissioned"),
    ]
    return _tbl(["Requirement", "Status"], items)

def _reconciliation_detailed() -> str:
    R = RECONCILIATION
    rows = [
        ["Market Approach",  f'SAR {R["market_value"]:,}',  f'{R["market_approach_weight_pct"]}%',
         f'SAR {R["market_contribution"]:,}', "High — adequate evidence"],
        ["Income Approach",  f'SAR {R["income_value"]:,}',  f'{R["income_approach_weight_pct"]}%',
         f'SAR {R["income_contribution"]:,}', "Medium — indicative data"],
        ["Cost Approach",    f'SAR {R["cost_value"]:,}',    f'{R["cost_approach_weight_pct"]}%',
         f'SAR {R["cost_contribution"]:,}', "Medium — floor value"],
        ["<strong>Weighted Total</strong>", "—", "<strong>100%</strong>",
         f'<strong>SAR {R["weighted_total"]:,}</strong>', ""],
        ["<strong>Adopted Value</strong>",
         f'<strong>SAR {R["adopted_value"]:,}</strong>', "—", "—", "Rounded"],
    ]
    return (
        "<p>" + R["rationale"] + "</p>"
        + _tbl(["Approach", "Indicated Value", "Weight", "Contribution", "Reliability"], rows)
        + '<div class="val-box">Reconciled Adopted Market Value: SAR '
        f'{R["adopted_value"]:,} (illustrative)</div>'
    )

def build_detailed_html() -> str:
    body = (
        _cover("Detailed Valuation Report", "Expanded Calculation and Evidence Support")
        + _advisory_banner()
        + _sec("1", "Executive Summary",
            "<p>This Detailed Valuation Report provides a more comprehensive analysis than a "
            "traditional report. It includes expanded comparable evidence, a full adjustment matrix, "
            "operating income assumptions, cost breakdown, a 5-year DCF summary, sensitivity snapshot, "
            "and identified risk notes.</p>"
            + _kv([
                ("Property",      SUBJECT["property_address"]),
                ("Property Type", SUBJECT["property_type"]),
                ("GFA",           f'{SUBJECT["gross_floor_area_m2"]} m²'),
                ("Adopted Value", f'SAR {RECONCILIATION["adopted_value"]:,} (illustrative)'),
                ("Valuation Date",SUBJECT["valuation_date"]),
                ("Status",        "ADVISORY ONLY"),
            ]))
        + _sec("2", "Instruction and Assignment Summary",
            _kv([
                ("Client / Instructing Party", SUBJECT["client"]),
                ("Client Type",               SUBJECT["client_type"]),
                ("Purpose of Valuation",      SUBJECT["purpose"]),
                ("Basis of Value",            SUBJECT["basis_of_value"]),
                ("Report Type",               "Detailed Valuation Report"),
                ("Date of Instruction",       "20 June 2026 (illustrative)"),
                ("Valuation Date",            SUBJECT["valuation_date"]),
                ("Report Date",               SUBJECT["report_date"]),
                ("Fee Basis",                 "Fixed (illustrative)"),
                ("Conflict Check",            "None identified (illustrative)"),
            ]))
        + _sec("3", "Purpose, Intended Use, and Intended Users", _purpose_scope_table())
        + _sec("4", "Scope of Work",
            "<p>The scope of work for this Detailed Valuation Report includes:</p>"
            "<ul>"
            "<li>Physical inspection of the subject property.</li>"
            "<li>Review of available title and planning documentation.</li>"
            "<li>Research and analysis of comparable sales evidence within a 2 km radius.</li>"
            "<li>Application of the Market, Income, and Cost Approaches.</li>"
            "<li>Preparation of a 5-year DCF cross-check.</li>"
            "<li>Sensitivity analysis of key assumptions.</li>"
            "<li>Identification of principal risks.</li>"
            "<li>Reconciliation of approach indications and value conclusion.</li>"
            "</ul>"
            "<p>This report does not include a full Highest and Best Use study, "
            "a full standards compliance matrix, or advanced scenario analysis. "
            "These are available in the Professional Valuation Report.</p>")
        + _sec("5", "Asset Identification", _property_identification())
        + _sec("6", "Legal and Document Review", _legal_doc_review())
        + _sec("7", "Site and Location Analysis", _site_analysis())
        + _sec("8", "Building / Component Breakdown", _building_breakdown())
        + _sec("9", "Requirement Completion Summary", _requirement_completion())
        + _sec("10", "Data Quality and Completeness", _data_quality_section())
        + _sec("11", "Market Evidence Summary",
            "<p>The market evidence research was conducted within a 2 km radius of the subject "
            "property, focussing on residential apartments transacted in the six months prior to "
            "the valuation date. The following evidence was identified:</p>"
            + _kv([
                ("Market Area",         "Al-Narjes and adjacent districts, North Riyadh"),
                ("Evidence Period",      "January – June 2026"),
                ("Sales Identified",    "5 comparable sales"),
                ("Price Range (SAR/m²)","SAR 6,229 – SAR 6,950"),
                ("Average (SAR/m²)",    "SAR 6,612 (unadjusted)"),
                ("Market Trend",        "Stable; slight upward pressure in Al-Narjes"),
                ("Data Sources",        "Market research; indicative data only"),
            ]))
        + _sec("12", "Comparable Sales Grid", _comparable_grid_detailed())
        + _sec("13", "Adjustment Matrix", _adjustment_matrix())
        + _sec("14", "Income Data and Operating Assumptions", _income_full())
        + _sec("15", "Cost Inputs and Depreciation Assumptions", _cost_full())
        + _sec("16", "Market Approach Calculation", _market_approach_simple())
        + _sec("17", "Income Approach Calculation", _income_approach_simple())
        + _sec("18", "Cost Approach Calculation", _cost_approach_simple())
        + _sec("19", "DCF Summary (5-Year Projection)", _dcf_mini())
        + _sec("20", "Sensitivity Snapshot", _sensitivity_snapshot())
        + _sec("21", "Risk Notes", _risk_notes_section())
        + _sec("22", "Reconciliation", _reconciliation_detailed())
        + _sec("23", "Value Conclusion", _value_conclusion())
        + _sec("24", "Assumptions and Limiting Conditions",
            _assumptions_brief()
            + "<ul><li>The DCF analysis is indicative and uses estimated inputs; it is not a substitute for a full investment appraisal.</li>"
            "<li>The sensitivity analysis illustrates the range of outcomes under varied assumptions; actual outcomes may differ.</li>"
            "<li>Risk notes are advisory only; independent risk assessment is recommended.</li></ul>")
        + "<h2>Appendix A — Comparable Detail Reference</h2>"
        + _tbl(["#", "Address", "Sale Price", "SAR/m²", "Area (m²)", "Age", "Condition", "Date"],
               [[c["id"], c["address"], f'SAR {c["price_sar"]:,}',
                 f'SAR {c["price_per_sqm"]:,}', str(c["area_m2"]),
                 f'{c["age_years"]} yrs', c["condition"], c["sale_date"]] for c in COMPARABLES])
        + "<h2>Appendix B — Document Checklist</h2>"
        + _tbl(["Document", "Required", "Status"],
               [["Title Deed", "Yes", "Indicative"], ["Building Permit", "Yes", "Confirmed"],
                ["Survey Plans", "Yes", "Indicative"], ["Lease Agreements", "Yes", "Not Provided"],
                ["Insurance", "Recommended", "Not Provided"]])
        + "<h2>Appendix C — Methodology Notes</h2>"
        + "<p>Market Approach: Sales comparison with six adjustment factors applied per comparable. "
        "Income Approach: Direct capitalisation (NOI ÷ Cap Rate). "
        "Cost Approach: Land value + GRC × (1 − physical depreciation). "
        "DCF: 5-year projection with terminal value at Year 5.</p>"
        + _advisory_notice()
        + _footer()
    )
    return _wrap("Detailed Valuation Report", body)


# ── Professional Report HTML ─────────────────────────────────────────────────

def _dcf_full() -> str:
    D = DCF_10YEAR
    rows = [[str(y), f'SAR {noi:,}', f'{pv:.4f}', f'SAR {pv_n:,}']
            for y, noi, pv, pv_n in zip(D["years"], D["noi"], D["pv_factor"], D["pv_noi"])]
    summary = [
        ["Cumulative PV of NOI (10 yrs)", f'SAR {D["cumulative_pv_noi"]:,}',  "", ""],
        ["Terminal NOI (Year 11)",         f'SAR {D["terminal_noi"]:,}',       "", ""],
        ["Terminal Value",                 f'SAR {D["terminal_value"]:,}',     "", ""],
        ["PV of Terminal Value",           f'SAR {D["pv_terminal"]:,}',        "", ""],
        ["<strong>Total DCF Value</strong>",f'<strong>SAR {D["total_dcf_value"]:,}</strong>', "", ""],
    ]
    return (
        f'<p>10-year projection | Discount Rate: {D["discount_rate_pct"]}% | '
        f'Growth Rate: {D["growth_rate_pct"]}% | Terminal Cap Rate: {D["terminal_cap_rate_pct"]}%</p>'
        + _tbl(["Year", "NOI (SAR)", "PV Factor", "PV of NOI"], rows + summary,
               note=ADVISORY_NOTE)
    )

def _hbu_section() -> str:
    H = HBU
    return (
        f'<p><strong>Current Use:</strong> {H["current_use"]}</p>'
        + "<h3>Test 1 — Legally Permissible</h3>"
        + '<p class="ok">PASS</p><p>' + H["legally_permissible"]["result"] + "</p>"
        + _kv([("Zoning", SUBJECT["zoning"]), ("Status", H["legally_permissible"]["status"])])
        + "<h3>Test 2 — Physically Possible</h3>"
        + '<p class="ok">PASS</p><p>' + H["physically_possible"]["result"] + "</p>"
        + _kv([("Condition", f'{SUBJECT["age_years"]}-year-old building in good condition'),
               ("Status", H["physically_possible"]["status"])])
        + "<h3>Test 3 — Financially Feasible</h3>"
        + '<p class="ok">PASS</p><p>' + H["financially_feasible"]["result"] + "</p>"
        + _kv([("NOI", f'SAR {INCOME["net_operating_income"]:,}'),
               ("Capitalisation Rate", INCOME["cap_rate_pct"]),
               ("Status", H["financially_feasible"]["status"])])
        + "<h3>Test 4 — Maximally Productive</h3>"
        + '<p class="ok">PASS</p><p>' + H["maximally_productive"]["result"] + "</p>"
        + '<div class="val-box">HBU Conclusion: ' + H["hbu_conclusion"] + "</div>"
    )

def _scenario_table() -> str:
    headers = ["Scenario", "Growth %", "Disc. Rate %", "Cap Rate %", "Occupancy %",
               "DCF Value", "Market Value", "Adopted Value", "Probability %"]
    rows = [[s["name"], f'{s["growth_pct"]}%', f'{s["discount_rate_pct"]}%',
             f'{s["cap_rate_pct"]}%', f'{s["occupancy_pct"]}%',
             f'SAR {s["dcf_value"]:,}', f'SAR {s["market_value"]:,}',
             f'SAR {s["adopted_value"]:,}', f'{s["probability_pct"]}%'] for s in SCENARIOS]
    rows.append(["Probability-Weighted Value", "—", "—", "—", "—", "—", "—",
                 f'<strong>SAR {PROBABILITY_WEIGHTED_VALUE:,}</strong>', "100%"])
    return _tbl(headers, rows, note=ADVISORY_NOTE)

def _sensitivity_full() -> str:
    SM = SENSITIVITY_MATRIX
    headers = [f'{SM["row_variable"]} \\ {SM["col_variable"]}'] + [f'{c}%' for c in SM["cols"]]
    rows = []
    for i, dr in enumerate(SM["rows"]):
        row = [f'{dr}%'] + [f'SAR {v:,}' for v in SM["values"][i]]
        rows.append(row)
    return _tbl(headers, rows, note="DCF value sensitivity — Indicative. Base case highlighted at DR=8.0% / CR=5.00%.")

def _risk_matrix_full() -> str:
    rows = [[r["id"], r["category"], r["description"][:38],
             r["probability"], r["impact"], str(r["score"]), r["mitigation"][:38]] for r in RISKS]
    return _tbl(["ID", "Category", "Description", "Probability", "Impact", "Score (1-9)", "Mitigation"],
                rows, note="Risk scores: probability × impact (indicative)")

def _avm_reliability() -> str:
    A = AVM
    return (
        "<p>The AVM is used as a cross-check only and does not replace the three traditional approaches. "
        "The model applies a hedonic pricing methodology using multiple data sources.</p>"
        + _kv([
            ("Model Type",               A["model_type"]),
            ("Confidence Level",         A["confidence_level"]),
            ("95% Confidence Interval",  f'SAR {A["avm_low_95pct"]:,} – SAR {A["avm_high_95pct"]:,}'),
            ("AVM Midpoint",             f'SAR {A["avm_midpoint"]:,}'),
            ("Data Sources",             f'{A["data_sources_count"]} independent sources'),
            ("Comparables in Model",     str(A["comparables_used"])),
            ("AVM vs Market Approach",   "Consistent — within 3% of Market Approach indication"),
            ("AVM Reliability",          "Moderate — suitable for cross-check only"),
            ("Advisory Note",            A["note"]),
        ])
    )

def _weighted_reconciliation_scorecard() -> str:
    headers = ["Method", "Indicated Value", "Weight %", "Reliability", "Data Quality", "Contribution"]
    rows = []
    for r in RECONCILIATION_SCORECARD:
        iv = f'SAR {r["indicated_value"]:,}' if r["indicated_value"] else "—"
        w  = f'{r["weight_pct"]}%' if r["weight_pct"] is not None else "—"
        c  = f'SAR {r["contribution"]:,}' if r["contribution"] else "—"
        rows.append([f'<strong>{r["method"]}</strong>' if "Total" in r["method"] or "Adopted" in r["method"] else r["method"],
                     iv, w, r["reliability"], r["data_quality"], c])
    return _tbl(headers, rows, note=ADVISORY_NOTE)

def _applied_standards_matrix() -> str:
    rows = [[s["code"], s["name"], s["status"], s["notes"]] for s in STANDARDS]
    return _tbl(["Standard Code", "Standard Name", "Status", "Notes"], rows,
                note="Indicative compliance mapping. Full compliance review requires expert confirmation.")

def _data_inputs_register() -> str:
    rows = [[d["input"], d["source"], d["value"], d["reliability"], d["status"]] for d in DATA_INPUTS]
    return _tbl(["Input", "Source", "Value", "Reliability", "Status"], rows,
                note=ADVISORY_NOTE)

def _method_selection_matrix() -> str:
    rows = [[m["method"], m["data_available"], m["applicable"],
             f'{m["weight_pct"]}%', m["justification"]] for m in METHOD_SELECTION]
    return _tbl(["Method", "Data Available", "Applicable", "Weight", "Justification"], rows)

def _certification_gate() -> str:
    return (
        _kv([
            ("certification_ready",          "False"),
            ("advisory_only",                "True"),
            ("fake_approval_created",        "False"),
            ("fake_signature_created",       "False"),
            ("official_use_allowed",         "False"),
            ("Expert Review Status",         "Requested — Pending"),
            ("Blockers to Certification",    "Legal confirmation; lease data; formal inspection certificate; expert sign-off"),
            ("Next Step",                    "Submit to licensed valuation expert for review, verification, and certification"),
        ])
        + '<div class="advisory"><strong>Expert Review and Certification Required</strong><br/>'
        "This report must be reviewed and certified by a qualified, licensed valuation expert "
        "before it may be used for any official, legal, financial, or regulatory purpose. "
        "The Expert_Smart system does not issue final certifications automatically.</div>"
    )

def _ownership_summary() -> str:
    return _kv([
        ("Registered Owner",     "Registered owner per title deed (indicative)"),
        ("Tenure",               SUBJECT["tenure"]),
        ("Title Reference",      f'Plot {SUBJECT["plot_number"]}, {SUBJECT["district"]} District'),
        ("Encumbrances",         "None known (indicative — legal confirmation required)"),
        ("Legal Status",         SUBJECT["legal_status"]),
        ("Occupancy",            "Owner-occupied / vacant at inspection (indicative)"),
    ])

def _requirement_dashboard() -> str:
    items = [
        ("Asset Identification",         "✓ Complete",  "ok"),
        ("Purpose and Basis of Value",   "✓ Complete",  "ok"),
        ("Scope of Work",                "✓ Complete",  "ok"),
        ("Physical Inspection",          "✓ Completed 28/06/2026", "ok"),
        ("Comparable Sales (min. 3)",    "✓ 5 identified","ok"),
        ("Income Data",                  "⚠ Indicative",  "warn"),
        ("Legal / Title Confirmation",   "⚠ Pending",     "warn"),
        ("Lease Agreements",             "✗ Not provided","nok"),
        ("Structural Survey",            "✗ Not commissioned","nok"),
        ("Environmental Search",         "⚠ Not required (advisory)","warn"),
        ("Market Research",              "✓ Complete",    "ok"),
        ("Standards Compliance Check",   "✓ Indicative",  "ok"),
        ("Expert Review",                "⚠ Pending",     "warn"),
        ("Certification Gate",           "✗ Not yet met", "nok"),
    ]
    rows = [[k, f'<span class="{cls}">{v}</span>'] for k, v, cls in items]
    return _tbl(["Requirement", "Status"], rows)

def build_professional_html() -> str:
    body = (
        _cover("Professional Valuation Report", "Comprehensive Multi-Method Analysis")
        + _advisory_banner()
        + _sec("1", "Executive Summary",
            "<p>This Professional Valuation Report is the most advanced and comprehensive "
            "of the three core report types. It applies all three traditional valuation approaches, "
            "a full 10-year Discounted Cash Flow analysis, Highest and Best Use analysis, "
            "scenario analysis (base / upside / downside), full sensitivity matrix, "
            "risk-adjusted valuation discussion, AVM reliability assessment, "
            "a weighted reconciliation scorecard, and an applied standards matrix.</p>"
            + _kv([
                ("Property",       SUBJECT["property_address"]),
                ("Property Type",  SUBJECT["property_type"]),
                ("GFA",            f'{SUBJECT["gross_floor_area_m2"]} m²'),
                ("Adopted Value",  f'SAR {RECONCILIATION["adopted_value"]:,} (illustrative)'),
                ("Prob-Weighted",  f'SAR {PROBABILITY_WEIGHTED_VALUE:,} (illustrative)'),
                ("Valuation Date", SUBJECT["valuation_date"]),
                ("Report Status",  "ADVISORY ONLY — Certification Required"),
            ]))
        + _sec("2", "Valuation Instruction and Scope of Work",
            _kv([
                ("Client",                SUBJECT["client"]),
                ("Client Type",           SUBJECT["client_type"]),
                ("Purpose",               SUBJECT["purpose"]),
                ("Basis of Value",        SUBJECT["basis_of_value"]),
                ("Report Type",           "Professional Valuation Report"),
                ("Valuation Date",        SUBJECT["valuation_date"]),
                ("Inspection Date",       SUBJECT["inspection_date"]),
                ("Report Date",           SUBJECT["report_date"]),
            ])
            + "<p>The scope includes all three traditional approaches, DCF, HBU, scenario and "
            "sensitivity analysis, risk assessment, AVM cross-check, and a weighted reconciliation. "
            "This report exceeds the scope of both the Traditional and Detailed report types.</p>")
        + _sec("3", "Basis of Value and Premise of Value",
            _kv([
                ("Basis of Value",     SUBJECT["basis_of_value"]),
                ("Definition",         "Market Value: the estimated amount for which an asset should "
                                       "exchange on the valuation date between a willing buyer and a "
                                       "willing seller in an arm's-length transaction, after proper "
                                       "marketing, where parties each acted knowledgeably, prudently, "
                                       "and without compulsion. (IVS 2025, IVS 104.1)"),
                ("Premise of Value",   "As-Is — Existing residential use"),
                ("Special Assumptions","None"),
                ("Hypothetical Cond.", "None"),
            ]))
        + _sec("4", "Intended Use and Intended Users", _purpose_scope_table())
        + _sec("5", "Asset Identification and Ownership Summary",
            _property_identification() + _ownership_summary())
        + _sec("6", "Legal / Document Review", _legal_doc_review())
        + _sec("7", "Location and Market Context", _site_analysis())
        + _sec("8", "Asset Requirement Completion Dashboard", _requirement_dashboard())
        + _sec("9", "Data Quality and Completeness", _data_quality_section())
        + _sec("10", "Component / Building / Use Breakdown", _building_breakdown())
        + _sec("11", "Applied Standards Matrix", _applied_standards_matrix())
        + _sec("12", "Data and Inputs Register", _data_inputs_register())
        + _sec("13", "Valuation Method Selection Matrix", _method_selection_matrix())
        + _sec("14", "Market Approach", _market_approach_simple())
        + _sec("15", "Income Approach", _income_approach_simple())
        + _sec("16", "Cost Approach", _cost_approach_simple())
        + _sec("17", "Discounted Cash Flow Analysis (10-Year)", _dcf_full())
        + _sec("18", "Residual / Development Method",
            "<p>The Residual / Development Method is not applicable to this property as it is "
            "a completed residential apartment with no development potential within the current "
            "planning consent. No residual appraisal has been prepared.</p>")
        + _sec("19", "Highest and Best Use (HBU) Summary", _hbu_section())
        + _sec("20", "Scenario Analysis", _scenario_table())
        + _sec("21", "Sensitivity Analysis", _sensitivity_full())
        + _sec("22", "Risk-Adjusted Valuation Discussion",
            "<p>The risk-adjusted valuation integrates the risk scoring matrix with the "
            "scenario analysis to produce a probability-weighted value range.</p>"
            + _kv([
                ("Base Case Value",           f'SAR {SCENARIOS[0]["adopted_value"]:,} (60% probability)'),
                ("Upside Case Value",         f'SAR {SCENARIOS[1]["adopted_value"]:,} (25% probability)'),
                ("Downside Case Value",       f'SAR {SCENARIOS[2]["adopted_value"]:,} (15% probability)'),
                ("Probability-Weighted Value",f'SAR {PROBABILITY_WEIGHTED_VALUE:,}'),
                ("Market Approach Value",     f'SAR {RECONCILIATION["market_value"]:,}'),
                ("Risk-Adjusted Range",       f'SAR {SCENARIOS[2]["adopted_value"]:,} – SAR {SCENARIOS[1]["adopted_value"]:,}'),
                ("Overall Risk Assessment",   "Moderate — primary risks are market softening and discount rate changes"),
            ])
            + _risk_matrix_full())
        + _sec("23", "AVM-Assisted Indication and Reliability", _avm_reliability())
        + _sec("24", "Weighted Reconciliation Model", _weighted_reconciliation_scorecard()
            + '<div class="val-box">Adopted Market Value: SAR '
            f'{RECONCILIATION["adopted_value"]:,} (illustrative)</div>')
        + _sec("25", "Value Conclusion", _value_conclusion())
        + _sec("26", "Assumptions and Limiting Conditions",
            _assumptions_brief()
            + "<ul>"
            "<li>The DCF analysis uses indicative growth, discount, and terminal cap rate assumptions.</li>"
            "<li>Scenario and sensitivity analysis illustrate possible outcomes; actual results may differ.</li>"
            "<li>The HBU conclusion is advisory only and does not constitute planning advice.</li>"
            "<li>AVM output is indicative and should not be relied upon as a standalone valuation.</li>"
            "<li>The applied standards matrix is indicative; full compliance confirmation requires expert review.</li>"
            "</ul>")
        + _sec("27", "Expert Review and Certification Gate", _certification_gate())
        + "<h2>Appendix A — Comparable Detail</h2>"
        + _tbl(["#", "Address", "Sale Price", "SAR/m²", "m²", "Age", "Condition", "Date"],
               [[c["id"], c["address"], f'SAR {c["price_sar"]:,}',
                 f'SAR {c["price_per_sqm"]:,}', str(c["area_m2"]),
                 f'{c["age_years"]} yrs', c["condition"], c["sale_date"]] for c in COMPARABLES])
        + "<h2>Appendix B — DCF Full Calculation Detail</h2>"
        + _dcf_full()
        + "<h2>Appendix C — Standards and References</h2>"
        + _applied_standards_matrix()
        + "<h2>Appendix D — Risk Register</h2>"
        + _risk_matrix_full()
        + _advisory_notice()
        + _footer()
    )
    return _wrap("Professional Valuation Report", body)


# ── PDF Renderer ─────────────────────────────────────────────────────────────

def render_pdf_chrome(html_str: str, output_path: Path) -> bool:
    if not _CHROME.exists():
        return False
    tmp_html = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".html", mode="w",
                                         encoding="utf-8", delete=False) as f:
            f.write(html_str)
            tmp_html = f.name
        result = subprocess.run(
            [str(_CHROME), "--headless", "--disable-gpu",
             f"--print-to-pdf={output_path}",
             "--no-pdf-header-footer",
             "--run-all-compositor-stages-before-draw",
             "--disable-extensions", "--no-sandbox",
             tmp_html],
            capture_output=True, timeout=90,
        )
        return output_path.exists() and output_path.stat().st_size > 1000
    except Exception:
        return False
    finally:
        if tmp_html:
            try:
                os.unlink(tmp_html)
            except Exception:
                pass


# ── Main generator ───────────────────────────────────────────────────────────

def generate_all_pdfs(pdf_dir: Path, preview_dir: Path) -> dict:
    pdf_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, dict] = {}
    reports = [
        ("traditional_report",  build_traditional_html,  "Traditional Valuation Report"),
        ("detailed_report",     build_detailed_html,     "Detailed Valuation Report"),
        ("professional_report", build_professional_html, "Professional Valuation Report"),
    ]

    for key, builder, label in reports:
        html = builder()
        html_path = preview_dir / f"{key}_preview.html"
        pdf_path  = pdf_dir / f"{key}.pdf"

        html_path.write_text(html, encoding="utf-8")
        ok = render_pdf_chrome(html, pdf_path)

        results[key] = {
            "label":       label,
            "pdf_path":    str(pdf_path),
            "html_path":   str(html_path),
            "pdf_exists":  pdf_path.exists(),
            "pdf_size_bytes": pdf_path.stat().st_size if pdf_path.exists() else 0,
            "rendered_ok": ok,
        }

    return results


if __name__ == "__main__":
    here = Path(__file__).parent
    qa_root = here / "instance" / "manual_review_outputs" / \
              "professional_valuation_final_core_workflow_and_report_qa"
    res = generate_all_pdfs(qa_root / "pdf_outputs", qa_root / "pdf_visual_previews")
    for k, v in res.items():
        status = "OK" if v["rendered_ok"] else "FAILED"
        print(f"[{status}] {k}: {v['pdf_size_bytes']:,} bytes")
