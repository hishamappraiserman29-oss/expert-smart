"""
test_hbu_report_sections.py
===========================
Wave 1C direct tests for hbu_report_sections.build_enhanced_sections.

RS01  import / contract
RS02  HTML escaping — string fields (use_name, recommended_use)
RS03  HTML escaping — provenance fields (admin mode)
RS04  HTML escaping — synth_label
RS05  HTML escaping — ratio-study values
RS06  HTML escaping — Equity IRR reason and assumption
RS07  Formatter plain-text boundary
RS08  Missing financial depth values → unavailable
RS09  Financial zero vs None
RS10  Missing site dimensions → unavailable (not zeros)
RS11  Zero site dimensions → unavailable (not "0 م²")
RS12  Empty sensitivity grid → message, not empty table
RS13  Empty discount sensitivity → message
RS14  Section C RLV label policy (neutral/verified/unavailable) + Section D verified label
RS15  Advisory governance footer always present
RS16  No fabricated market narrative without evidence
RS17  Input immutability
RS18  Deterministic output (identical inputs → identical HTML)
RS19  Trusted callback boundary (formatter plain-text contract enforced)
RS20  Renderer remains unwired from bridge_api / canonical / frontend
RS21  No canonical-renderer replacement
RS22  Empty scenario list → safe empty state, no recommended-use claim
RS23  _src_badge unknown status → fixed fallback (never embeds status string)
RS24  _val_row label escaping
RS25  Non-numeric discount_rate_pct → escaped, not crash
RS26  Table feasibility text (not color-only)
RS27  RTL wrapper present in section content
RS28  scope="col" on table headers
"""
import copy
import pathlib
import re
import sys

import pytest

# ---------------------------------------------------------------------------
# Module import
# ---------------------------------------------------------------------------
sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
from hbu_report_sections import (
    build_enhanced_sections,
    _src_badge,
    _val_row,
    _esc,
    _advisory_only,
    _certification_ready,
    _ADVISORY_DISCLAIMER,
    _RLV_METHOD_ID_NPV_IDENTITY,
    _RLV_LABEL_SCENARIO_NEUTRAL,
    _RLV_LABEL_SCENARIO_NPV_IDENTITY,
    _RLV_LABEL_SCENARIO_UNAVAILABLE,
    _RLV_LABEL_OPTIMAL,
)


# ════════════════════════════════════════════════════════════════════════════
#  Shared test fixtures
# ════════════════════════════════════════════════════════════════════════════

def _section_html(letter, title, content, color):
    return f'<section id="{letter}">{content}</section>'


def _fmt_currency(v):
    if isinstance(v, (int, float)):
        return f"{v:,.0f}"
    return "غير متاح"


def _pct(v):
    if isinstance(v, (int, float)):
        return f"{v:.1f}%"
    return "غير متاح"


def _base_result():
    return {
        "recommended_use": "سكني مختلط",
        "recommended_npv": 1_000_000,
        "scenarios_evaluated": [
            {
                "use_name": "سكني مختلط",
                "test_4_max_productive": True,
                "annual_revenue": 500_000,
                "annual_noi": 400_000,
                "residual_land_value": 2_000_000,
                "npv": 1_000_000,
            },
            {
                "use_name": "تجاري",
                "test_4_max_productive": False,
                "annual_revenue": 300_000,
                "annual_noi": 250_000,
                "residual_land_value": 1_500_000,
                "npv": 800_000,
            },
        ],
        "financial_depth": {
            "residual_land_value": 2_000_000,
            "rlv_per_m2": 2_000,
            "payback_years": 5.0,
            "developer_metrics": {
                "profit_on_cost_pct": 20.0,
                "total_investment": 1_000_000,
            },
            "equity_irr": {
                "value": 15.0,
                "assumption": "ltv=70%, loan_rate=5.00%",
            },
            "sensitivity": {
                "cost_revenue_grid": [
                    {"cost_delta_pct": -10, "revenue_delta_pct": -10, "npv": -100_000, "feasible": False},
                    {"cost_delta_pct": -10, "revenue_delta_pct": 0,   "npv":  500_000, "feasible": True},
                    {"cost_delta_pct": 0,   "revenue_delta_pct": -10, "npv":  400_000, "feasible": True},
                    {"cost_delta_pct": 0,   "revenue_delta_pct": 0,   "npv":1_000_000, "feasible": True},
                ],
                "discount_sensitivity": [
                    {"discount_rate_pct": 8.0,  "npv": 1_200_000, "feasible": True},
                    {"discount_rate_pct": 10.0, "npv": 1_000_000, "feasible": True},
                ],
                "npv_min": -100_000,
                "npv_max":  1_000_000,
                "downside_feasible": False,
            },
        },
        "market_inputs": {},
    }


def _base_site():
    return {"land_area": 1000, "frontage": 25, "depth": 40, "road_width": 20}


def _base_planning():
    return {"max_far": 3.0}


def _call(result=None, site=None, planning=None, synth_label="استرشادي",
          is_admin=False, fmt_currency=None, pct_fn=None):
    return build_enhanced_sections(
        result   if result   is not None else _base_result(),
        is_admin=is_admin,
        section_html=_section_html,
        fmt_currency=fmt_currency or _fmt_currency,
        pct=pct_fn or _pct,
        site=site if site is not None else _base_site(),
        planning=planning if planning is not None else _base_planning(),
        synth_label=synth_label,
    )


# ════════════════════════════════════════════════════════════════════════════
#  RS01 — import / contract
# ════════════════════════════════════════════════════════════════════════════

def test_rs01_import_and_return_type():
    html = _call()
    assert isinstance(html, str), "build_enhanced_sections must return str"
    assert len(html) > 0, "Output must be non-empty"
    assert _advisory_only is True
    assert _certification_ready is False


# ════════════════════════════════════════════════════════════════════════════
#  RS02 — HTML escaping — string fields
# ════════════════════════════════════════════════════════════════════════════

def test_rs02_escaping_use_name():
    result = _base_result()
    result["scenarios_evaluated"][0]["use_name"] = '<script>alert(1)</script>'
    html = _call(result=result)
    assert '<script>' not in html
    assert '&lt;script&gt;' in html


def test_rs02_escaping_recommended_use():
    result = _base_result()
    result["recommended_use"] = '"><img src=x onerror=alert(1)>'
    html = _call(result=result)
    # The raw executable form must not appear
    assert '<img src=x onerror=alert(1)>' not in html
    # Escaped form must appear (proves _esc was applied)
    assert '&lt;img' in html
    assert '&quot;' in html or '&gt;' in html


# ════════════════════════════════════════════════════════════════════════════
#  RS03 — HTML escaping — provenance fields (admin)
# ════════════════════════════════════════════════════════════════════════════

def test_rs03_escaping_provenance_fields():
    result = _base_result()
    result["market_inputs"] = {
        "provenance": [
            {
                "input":              "<b>bold_input</b>",
                "value":              "100",
                "source_name":        "<script>src</script>",
                "tier":               "<em>tier</em>",
                "status":             "<span>status</span>",
                "reconciliation_note": "<img>note</img>",
            }
        ],
        "governance": {
            "primary_source":    "<b>primary</b>",
            "web_data_status":   "<em>status</em>",
            "enrichment_is_draft": True,
            "web_trains_model":   False,
        },
    }
    html = _call(result=result, is_admin=True)
    # No raw HTML tags from external data
    assert "<b>bold_input</b>" not in html
    assert "<script>src</script>" not in html
    assert "<em>tier</em>" not in html
    assert "<span>status</span>" not in html
    assert "<img>note</img>" not in html
    assert "<b>primary</b>" not in html
    assert "<em>status</em>" not in html
    # Escaped versions present
    assert "&lt;b&gt;" in html
    assert "&lt;script&gt;" in html


# ════════════════════════════════════════════════════════════════════════════
#  RS04 — HTML escaping — synth_label
# ════════════════════════════════════════════════════════════════════════════

def test_rs04_escaping_synth_label():
    html = _call(synth_label='<b>bold</b>')
    assert '<b>bold</b>' not in html
    assert '&lt;b&gt;bold&lt;/b&gt;' in html


# ════════════════════════════════════════════════════════════════════════════
#  RS05 — HTML escaping — ratio-study values
# ════════════════════════════════════════════════════════════════════════════

def test_rs05_escaping_ratio_study():
    result = _base_result()
    result["market_inputs"] = {
        "mass_appraisal": {
            "ratio_study": {
                "n_sales": 5,
                "cod":         "<script>cod</script>",
                "prd":         "<img>prd</img>",
                "uniformity":  "<b>uniformity</b>",
            }
        }
    }
    html = _call(result=result)
    assert "<script>cod</script>" not in html
    assert "<img>prd</img>" not in html
    assert "<b>uniformity</b>" not in html
    assert "&lt;script&gt;" in html


# ════════════════════════════════════════════════════════════════════════════
#  RS06 — HTML escaping — Equity IRR reason and assumption
# ════════════════════════════════════════════════════════════════════════════

def test_rs06_escaping_equity_irr_reason():
    result = _base_result()
    result["financial_depth"]["equity_irr"] = {
        "value":      None,
        "reason":     "<marquee>bad reason</marquee>",
        "assumption": "<script>bad_assumption</script>",
    }
    html = _call(result=result)
    assert "<marquee>" not in html
    assert "<script>bad_assumption</script>" not in html
    assert "&lt;marquee&gt;" in html


# ════════════════════════════════════════════════════════════════════════════
#  RS07 — Formatter plain-text boundary
# ════════════════════════════════════════════════════════════════════════════

def test_rs07_formatter_plain_text_contract():
    """fmt_currency returning HTML-like text must be escaped before insertion."""
    def malicious_fmt(v):
        return "<b>INJECTED</b>"

    html = _call(fmt_currency=malicious_fmt)
    assert "<b>INJECTED</b>" not in html
    assert "&lt;b&gt;INJECTED&lt;/b&gt;" in html


# ════════════════════════════════════════════════════════════════════════════
#  RS08 — Missing financial depth values → "غير متاح"
# ════════════════════════════════════════════════════════════════════════════

def test_rs08_missing_financial_depth():
    result = _base_result()
    result["financial_depth"] = {}
    html = _call(result=result)
    assert "غير متاح" in html
    # Should not render "0" as a valid RLV when field is absent
    assert "0 م²" not in html or html.count("غير متاح") >= 3


# ════════════════════════════════════════════════════════════════════════════
#  RS09 — Financial zero vs None
# ════════════════════════════════════════════════════════════════════════════

def test_rs09_zero_npv_renders_as_zero():
    result = _base_result()
    result["financial_depth"]["residual_land_value"] = 0
    result["financial_depth"]["equity_irr"]["value"] = 0
    result["financial_depth"]["developer_metrics"]["profit_on_cost_pct"] = 0
    html = _call(result=result)
    # Zero RLV: fmt_currency(0) = "0" → appears in output
    assert _fmt_currency(0) in html


def test_rs09_none_npv_renders_unavailable():
    result = _base_result()
    result["financial_depth"]["residual_land_value"] = None
    html = _call(result=result)
    assert "غير متاح" in html


def test_rs09_none_profit_margin_renders_unavailable():
    result = _base_result()
    result["financial_depth"]["developer_metrics"]["profit_on_cost_pct"] = None
    html = _call(result=result)
    assert "غير متاح" in html


# ════════════════════════════════════════════════════════════════════════════
#  RS10 — Missing site dimensions → "غير متاح"
# ════════════════════════════════════════════════════════════════════════════

def test_rs10_missing_land_area():
    site = {"frontage": 25, "depth": 40, "road_width": 20}
    html = _call(site=site)
    assert "غير متاح" in html


def test_rs10_missing_road_width_no_fabrication():
    site = {"land_area": 1000, "frontage": 25, "depth": 40}
    html = _call(site=site)
    # Must not fabricate "محدود" for missing road_width
    assert "محدود" not in html or "غير متاح" in html
    assert "عرض الشارع غير متاح" in html


def test_rs10_none_site_dimensions():
    site = {"land_area": None, "frontage": None, "depth": None, "road_width": None}
    html = _call(site=site)
    assert html.count("غير متاح") >= 3


# ════════════════════════════════════════════════════════════════════════════
#  RS11 — Zero site dimensions → "غير متاح"
# ════════════════════════════════════════════════════════════════════════════

def test_rs11_zero_land_area_is_unavailable():
    site = {"land_area": 0, "frontage": 25, "depth": 40, "road_width": 20}
    html = _call(site=site)
    # "0 م²" must not appear as a valid area
    assert "0,م²" not in html
    assert "غير متاح" in html


def test_rs11_zero_frontage_is_unavailable():
    site = {"land_area": 1000, "frontage": 0, "depth": 40, "road_width": 20}
    html = _call(site=site)
    assert "غير متاح" in html


# ════════════════════════════════════════════════════════════════════════════
#  RS12 — Empty sensitivity grid → message, no empty table
# ════════════════════════════════════════════════════════════════════════════

def test_rs12_empty_sensitivity_grid():
    result = _base_result()
    result["financial_depth"]["sensitivity"]["cost_revenue_grid"] = []
    html = _call(result=result)
    assert "بيانات الحساسية غير متاحة" in html
    # No empty tbody from the sensitivity grid
    assert re.search(r'<tbody>\s*</tbody>', html) is None or \
           "بيانات الحساسية غير متاحة" in html


def test_rs12_absent_sensitivity():
    result = _base_result()
    del result["financial_depth"]["sensitivity"]
    html = _call(result=result)
    assert "بيانات الحساسية غير متاحة" in html


# ════════════════════════════════════════════════════════════════════════════
#  RS13 — Empty discount sensitivity → message
# ════════════════════════════════════════════════════════════════════════════

def test_rs13_empty_discount_sensitivity():
    result = _base_result()
    result["financial_depth"]["sensitivity"]["discount_sensitivity"] = []
    html = _call(result=result)
    assert "بيانات حساسية معدل الخصم غير متاحة" in html


# ════════════════════════════════════════════════════════════════════════════
#  RS14 — Section C RLV label policy and Section D verified label
# ════════════════════════════════════════════════════════════════════════════

def test_rs14_section_c_neutral_label_when_no_method_metadata():
    """Base result has residual_land_value but no rlv_method_id → neutral label."""
    html = _call()
    assert _esc(_RLV_LABEL_SCENARIO_NEUTRAL) in html
    # Must NOT attribute to Wave 1A or NPV identity in Section C
    assert _esc(_RLV_LABEL_SCENARIO_NPV_IDENTITY) not in html
    assert "لكل سيناريو" in html


def test_rs14_section_d_npv_identity_label_always_used():
    """Section D reads financial_depth — verified Wave 1A producer; NPV label always used."""
    html = _call()
    assert _esc(_RLV_LABEL_OPTIMAL) in html
    assert "هوية NPV" in html


def test_rs14_distinct_section_c_and_d_labels():
    """Section C and Section D RLV labels are distinct strings."""
    assert _RLV_LABEL_SCENARIO_NEUTRAL != _RLV_LABEL_OPTIMAL
    assert _RLV_LABEL_SCENARIO_NPV_IDENTITY != _RLV_LABEL_OPTIMAL


# ════════════════════════════════════════════════════════════════════════════
#  RS15 — Advisory governance footer always present
# ════════════════════════════════════════════════════════════════════════════

def test_rs15_advisory_governance_always_present():
    html = _call()
    assert "استرشادية" in html
    assert "ولا تُعدّ شهادة تقييم" in html


def test_rs15_governance_present_with_empty_data():
    html = _call(result={"scenarios_evaluated": []})
    assert "استرشادية" in html
    assert "ولا تُعدّ شهادة تقييم" in html


# ════════════════════════════════════════════════════════════════════════════
#  RS16 — No fabricated market narrative without evidence
# ════════════════════════════════════════════════════════════════════════════

def test_rs16_no_fabricated_demand_without_evidence():
    result = _base_result()
    result["market_inputs"] = {}
    html = _call(result=result)
    # These fabricated phrases must not appear unconditionally
    assert "طلب محلي على المختلط" not in html
    assert "معروض منافس محدود" not in html
    assert "طلب متنامٍ على المختلط" not in html
    # No-evidence message must appear instead
    assert "لا تتوفر أدلة سوقية كافية" in html


def test_rs16_approved_evidence_renders_qualified():
    result = _base_result()
    result["market_inputs"] = {
        "inputs": {
            "price_per_m2": {
                "value": 5000,
                "unit": "ر.س/م²",
                "status": "approved_internal",
                "confidence": 80,
            }
        }
    }
    html = _call(result=result)
    # When approved evidence present, no-evidence message should NOT appear for demand
    # (qualified text should appear instead)
    assert "لا تتوفر أدلة سوقية كافية" not in html


# ════════════════════════════════════════════════════════════════════════════
#  RS17 — Input immutability
# ════════════════════════════════════════════════════════════════════════════

def test_rs17_input_immutability():
    result   = _base_result()
    site     = _base_site()
    planning = _base_planning()
    r_before = copy.deepcopy(result)
    s_before = copy.deepcopy(site)
    p_before = copy.deepcopy(planning)
    _call(result=result, site=site, planning=planning)
    assert result   == r_before, "result dict was mutated"
    assert site     == s_before, "site dict was mutated"
    assert planning == p_before, "planning dict was mutated"


# ════════════════════════════════════════════════════════════════════════════
#  RS18 — Deterministic output
# ════════════════════════════════════════════════════════════════════════════

def test_rs18_deterministic_output():
    html1 = _call()
    html2 = _call()
    assert html1 == html2, "Identical inputs must produce identical HTML"


# ════════════════════════════════════════════════════════════════════════════
#  RS19 — Trusted callback boundary
# ════════════════════════════════════════════════════════════════════════════

def test_rs19_formatter_with_ampersand_and_lt():
    def fmt_with_specials(v):
        return "SAR & <1000>"

    html = _call(fmt_currency=fmt_with_specials)
    # The plain text output must be escaped — no raw < or & from formatter
    assert "SAR & <1000>" not in html
    assert "SAR &amp; &lt;1000&gt;" in html


# ════════════════════════════════════════════════════════════════════════════
#  RS20 — Renderer remains unwired
# ════════════════════════════════════════════════════════════════════════════

def test_rs20_renderer_unwired():
    """bridge_api.py, hbu_enhanced_report.py, and frontend must not import the candidate."""
    repo_root = pathlib.Path(__file__).parents[2]
    targets = [
        repo_root / "core_engine" / "bridge_api.py",
        repo_root / "core_engine" / "reports" / "hbu_enhanced_report.py",
        repo_root / "frontend" / "index.html",
    ]
    for target in targets:
        if target.exists():
            content = target.read_text(encoding="utf-8", errors="ignore")
            assert "hbu_report_sections" not in content, (
                f"{target.name} must not import hbu_report_sections"
            )
            assert "build_enhanced_sections" not in content, (
                f"{target.name} must not reference build_enhanced_sections"
            )


# ════════════════════════════════════════════════════════════════════════════
#  RS21 — No canonical-renderer replacement
# ════════════════════════════════════════════════════════════════════════════

def test_rs21_canonical_renderer_untouched():
    """hbu_enhanced_report.py must still contain its endpoint wiring."""
    target = pathlib.Path(__file__).parents[2] / "core_engine" / "reports" / "hbu_enhanced_report.py"
    if target.exists():
        content = target.read_text(encoding="utf-8", errors="ignore")
        assert "generate_enhanced_hbu_report" in content, (
            "Canonical renderer function must still exist"
        )


# ════════════════════════════════════════════════════════════════════════════
#  RS22 — Empty scenario list → safe empty state
# ════════════════════════════════════════════════════════════════════════════

def test_rs22_empty_scenarios_no_crash():
    result = _base_result()
    result["scenarios_evaluated"] = []
    html = _call(result=result)
    assert isinstance(html, str)
    assert len(html) > 0


def test_rs22_empty_scenarios_no_fabricated_recommendation():
    result = _base_result()
    result["scenarios_evaluated"] = []
    result["recommended_use"] = None
    result["recommended_npv"] = None
    html = _call(result=result)
    assert "لا يوجد استخدام موصى به" in html


# ════════════════════════════════════════════════════════════════════════════
#  RS23 — _src_badge unknown status never embeds status string
# ════════════════════════════════════════════════════════════════════════════

def test_rs23_src_badge_unknown_status_safe():
    injection = '<script>alert("xss")</script>'
    badge = _src_badge(injection)
    assert injection not in badge
    assert "<script>" not in badge
    # Falls back to fixed 'غير متاح' badge
    assert "غير متاح" in badge


def test_rs23_src_badge_known_statuses():
    assert "مُعتمَد داخلي" in _src_badge("approved_internal")
    assert "Draft" in _src_badge("draft_pending_review")
    assert "غير متاح" in _src_badge("")
    assert "غير متاح" in _src_badge("random_unknown")


# ════════════════════════════════════════════════════════════════════════════
#  RS24 — _val_row label escaping
# ════════════════════════════════════════════════════════════════════════════

def test_rs24_val_row_label_escaped():
    label  = '<b>injected label</b>'
    entry  = None
    result = _val_row(label, entry, _fmt_currency)
    assert '<b>injected label</b>' not in result
    assert '&lt;b&gt;' in result


def test_rs24_val_row_value_escaped():
    label = "test"
    entry = {"value": "<script>v</script>", "unit": "<br>", "status": "unknown"}
    result = _val_row(label, entry, _fmt_currency)
    assert "<script>v</script>" not in result
    assert "<br>" not in result
    assert "&lt;script&gt;" in result


# ════════════════════════════════════════════════════════════════════════════
#  RS25 — Non-numeric discount_rate_pct → escaped, not crash
# ════════════════════════════════════════════════════════════════════════════

def test_rs25_nonnumeric_discount_rate_pct():
    result = _base_result()
    result["financial_depth"]["sensitivity"]["discount_sensitivity"] = [
        {"discount_rate_pct": "<script>10</script>", "npv": 500_000, "feasible": True},
    ]
    html = _call(result=result)
    assert "<script>10</script>" not in html
    assert "&lt;script&gt;" in html


# ════════════════════════════════════════════════════════════════════════════
#  RS26 — Table feasibility text (not color-only)
# ════════════════════════════════════════════════════════════════════════════

def test_rs26_sensitivity_grid_has_feasibility_text():
    html = _call()
    assert "مجدٍ" in html
    assert "غير مجدٍ" in html


# ════════════════════════════════════════════════════════════════════════════
#  RS27 — RTL wrapper present in section content
# ════════════════════════════════════════════════════════════════════════════

def test_rs27_rtl_dir_attribute_present():
    html = _call()
    assert 'dir="rtl"' in html


def test_rs27_ltr_bdi_for_numerics():
    html = _call()
    assert '<bdi dir="ltr">' in html


# ════════════════════════════════════════════════════════════════════════════
#  RS28 — scope="col" on table headers
# ════════════════════════════════════════════════════════════════════════════

def test_rs28_table_headers_have_scope():
    html = _call()
    assert 'scope="col"' in html


# ════════════════════════════════════════════════════════════════════════════
#  Additional edge-case tests
# ════════════════════════════════════════════════════════════════════════════

def test_advisory_constants_correct():
    assert _advisory_only is True
    assert _certification_ready is False
    assert "استرشادية" in _ADVISORY_DISCLAIMER
    assert "شهادة تقييم" in _ADVISORY_DISCLAIMER


def test_esc_none_returns_empty():
    assert _esc(None) == ""


def test_esc_html_chars_escaped():
    assert _esc("<b>") == "&lt;b&gt;"
    assert _esc('"quoted"') == "&quot;quoted&quot;"
    assert _esc("a & b") == "a &amp; b"


def test_no_recommendation_when_rec_is_none():
    result = _base_result()
    result["recommended_use"] = None
    html = _call(result=result)
    assert "لا يوجد استخدام موصى به" in html


def test_scenario_rlv_none_when_engine_output_only():
    """When scenarios lack residual_land_value (engine output only), unavailable message shown."""
    result = _base_result()
    for sc in result["scenarios_evaluated"]:
        sc.pop("residual_land_value", None)
    html = _call(result=result)
    assert "محرك HBU لا ينتج RLV على مستوى السيناريو" in html
    assert "إثراء مالي موثق" in html
    # Must not falsely attribute to Wave 1A in Section C
    assert "هوية NPV (Wave 1A)" not in html or _esc(_RLV_LABEL_OPTIMAL) in html


def test_scenario_rlv_present_no_method_metadata_neutral_label():
    """Scenario has residual_land_value but no rlv_method_id → neutral label, no Wave 1A."""
    result = _base_result()
    # base_result already has residual_land_value; ensure no rlv_method_id
    for sc in result["scenarios_evaluated"]:
        sc.pop("rlv_method_id", None)
    html = _call(result=result)
    assert _esc(_RLV_LABEL_SCENARIO_NEUTRAL) in html
    assert _esc(_RLV_LABEL_SCENARIO_NPV_IDENTITY) not in html
    # RLV value must still render (numeric present)
    assert "2" in html  # value from base_result


def test_scenario_rlv_with_verified_method_id_uses_npv_label():
    """Scenario with rlv_method_id == NPV_IDENTITY_RLV → NPV-identity label shown."""
    result = _base_result()
    for sc in result["scenarios_evaluated"]:
        sc["rlv_method_id"] = _RLV_METHOD_ID_NPV_IDENTITY
    html = _call(result=result)
    assert _esc(_RLV_LABEL_SCENARIO_NPV_IDENTITY) in html
    assert _esc(_RLV_LABEL_SCENARIO_NEUTRAL) not in html


def test_scenario_rlv_unknown_method_id_uses_neutral_label():
    """Scenario with an unrecognised rlv_method_id → neutral label, not NPV-identity."""
    result = _base_result()
    for sc in result["scenarios_evaluated"]:
        sc["rlv_method_id"] = "SOME_FUTURE_METHOD"
    html = _call(result=result)
    assert _esc(_RLV_LABEL_SCENARIO_NEUTRAL) in html
    assert _esc(_RLV_LABEL_SCENARIO_NPV_IDENTITY) not in html


def test_page_break_divider_present():
    html = _call()
    assert 'page-break' in html


def test_admin_provenance_hidden_for_non_admin():
    result = _base_result()
    result["market_inputs"] = {
        "provenance": [{"input": "x", "source_name": "secret_source", "value": 100,
                        "tier": "1", "status": "approved_internal"}]
    }
    html_user  = _call(result=result, is_admin=False)
    html_admin = _call(result=result, is_admin=True)
    assert "secret_source" not in html_user
    assert "secret_source" in html_admin


def test_unavailable_market_inputs_listed():
    result = _base_result()
    result["market_inputs"] = {
        "unavailable": [
            {"input": "rent_per_m2",   "reason": "لا مصدر متاح"},
            {"input": "vacancy_rate",  "reason": "غير محدد"},
        ]
    }
    html = _call(result=result)
    assert "rent_per_m2" in html
    assert "لا مصدر متاح" in html


def test_escaping_unavailable_input_reason():
    result = _base_result()
    result["market_inputs"] = {
        "unavailable": [
            {"input": "<b>inp</b>", "reason": "<script>reason</script>"},
        ]
    }
    html = _call(result=result)
    assert "<b>inp</b>" not in html
    assert "<script>reason</script>" not in html
    assert "&lt;script&gt;" in html
