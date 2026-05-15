"""
Tests for core_engine/reports/report_profiles.py — the centralized report
profile registry.

Run from repo root:
    $env:PYTHONPATH = (Get-Location).Path + ';' + (Get-Location).Path + '\\core_engine'
    python tests/test_report_profiles.py
"""
from __future__ import annotations

import io
import os
import sys

# Force UTF-8 stdout so Arabic names print safely on Windows cp1252 terminals
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core_engine"))

CHECKS_PASSED = 0
CHECKS_FAILED = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global CHECKS_PASSED, CHECKS_FAILED
    if condition:
        print(f"  [PASS] {label}")
        CHECKS_PASSED += 1
    else:
        print(f"  [FAIL] {label}" + (f" -- {detail}" if detail else ""))
        CHECKS_FAILED += 1


# ── Import ────────────────────────────────────────────────────────────────────
try:
    from reports.report_profiles import (
        ReportProfile,
        _PROFILES,
        normalize_report_style,
        get_report_profile,
        is_legacy,
        is_detailed,
        is_professional_template,
        should_exclude_advanced_sheets,
        get_legacy_excluded_sheets,
        normalize_sheet_name,
        is_legacy_excluded_sheet,
    )
except Exception as _imp_err:
    print(f"[FATAL] Import failed: {_imp_err}")
    sys.exit(1)


# ── 1. Profile existence ───────────────────────────────────────────────────────
print("\nSection 1: Profile existence")
check("legacy profile exists",               "legacy"                in _PROFILES)
check("detailed profile exists",             "detailed"              in _PROFILES)
check("professional_template profile exists","professional_template" in _PROFILES)

legacy_p  = _PROFILES.get("legacy")
detailed_p = _PROFILES.get("detailed")
prof_p     = _PROFILES.get("professional_template")

check("legacy is ReportProfile",                isinstance(legacy_p,   ReportProfile))
check("detailed is ReportProfile",              isinstance(detailed_p, ReportProfile))
check("professional_template is ReportProfile", isinstance(prof_p,     ReportProfile))


# ── 2. Legacy metadata ────────────────────────────────────────────────────────
print("\nSection 2: Legacy profile metadata")
check("legacy label_ar",                      legacy_p.label_ar == "التقرير التقليدي")
check("legacy label_en",                      legacy_p.label_en == "Legacy Report")
check("legacy include_advanced_analytics=F",  legacy_p.include_advanced_analytics is False)
check("legacy exclude_advanced_sheets=T",     legacy_p.exclude_advanced_sheets is True)
check("legacy include_sales_adjustment=T",    legacy_p.include_sales_adjustment_matrix is True)
check("legacy default_output_ext=.xlsx",      legacy_p.default_output_ext == ".xlsx")


# ── 3. Detailed metadata ──────────────────────────────────────────────────────
print("\nSection 3: Detailed profile metadata")
check("detailed label_ar",                    detailed_p.label_ar == "التقرير التفصيلي")
check("detailed label_en",                    detailed_p.label_en == "Detailed Report")
check("detailed include_advanced_analytics=T",detailed_p.include_advanced_analytics is True)
check("detailed exclude_advanced_sheets=F",   detailed_p.exclude_advanced_sheets is False)
check("detailed include_sales_adjustment=T",  detailed_p.include_sales_adjustment_matrix is True)


# ── 4. Professional template metadata ─────────────────────────────────────────
print("\nSection 4: Professional template profile metadata")
check("prof label_ar",                        prof_p.label_ar == "التقرير الاحترافي بالقالب")
check("prof label_en",                        prof_p.label_en == "Professional Template Report")
check("prof uses_template=T",                 prof_p.uses_template is True)
check("prof template_path set",               prof_p.template_path is not None and len(prof_p.template_path) > 0)
check("prof template_path contains xlsm",     ".xlsm" in (prof_p.template_path or ""))
check("prof exclude_advanced_sheets=F",       prof_p.exclude_advanced_sheets is False)


# ── 5. normalize_report_style / get_report_profile ───────────────────────────
print("\nSection 5: normalize_report_style and get_report_profile")
check("normalize 'legacy'",               normalize_report_style("legacy")                == "legacy")
check("normalize 'detailed'",             normalize_report_style("detailed")              == "detailed")
check("normalize 'professional_template'",normalize_report_style("professional_template") == "professional_template")
check("normalize None -> legacy",         normalize_report_style(None)                    == "legacy")
check("normalize '' -> legacy",           normalize_report_style("")                      == "legacy")
check("normalize unknown -> legacy",      normalize_report_style("nonexistent_style")     == "legacy")
check("normalize '  legacy  ' (spaces)",  normalize_report_style("  legacy  ")            == "legacy")

check("get_report_profile('legacy') style",    get_report_profile("legacy").style    == "legacy")
check("get_report_profile('detailed') style",  get_report_profile("detailed").style  == "detailed")
check("get_report_profile(None) -> legacy",    get_report_profile(None).style        == "legacy")
check("get_report_profile('bad') -> legacy",   get_report_profile("bad").style       == "legacy")


# ── 6. Predicate helpers ──────────────────────────────────────────────────────
print("\nSection 6: is_legacy / is_detailed / is_professional_template")
check("is_legacy('legacy')",               is_legacy("legacy"))
check("is_legacy(None) -> True",           is_legacy(None))
check("is_legacy('detailed') -> False",    not is_legacy("detailed"))

check("is_detailed('detailed')",           is_detailed("detailed"))
check("is_detailed('legacy') -> False",    not is_detailed("legacy"))
check("is_detailed(None) -> False",        not is_detailed(None))

check("is_professional_template(prof)",    is_professional_template("professional_template"))
check("is_professional_template(None)->F", not is_professional_template(None))


# ── 7. should_exclude_advanced_sheets ────────────────────────────────────────
print("\nSection 7: should_exclude_advanced_sheets")
check("legacy excludes advanced sheets",              should_exclude_advanced_sheets("legacy"))
check("detailed does NOT exclude advanced sheets",    not should_exclude_advanced_sheets("detailed"))
check("professional_template does NOT exclude adv",   not should_exclude_advanced_sheets("professional_template"))
check("unknown style (->legacy) excludes adv sheets", should_exclude_advanced_sheets("unknown"))
check("None (->legacy) excludes adv sheets",          should_exclude_advanced_sheets(None))


# ── 8. get_legacy_excluded_sheets ─────────────────────────────────────────────
print("\nSection 8: get_legacy_excluded_sheets")
excluded = get_legacy_excluded_sheets()
check("returns frozenset",  isinstance(excluded, frozenset))
check("non-empty",          len(excluded) > 0)

_arabic_keywords = [
    "التحليل المكاني", "التحليل المكانى",
    "الانحدار المتعدد", "الإنحدار المتعدد",
    "الخيارات الحقيقية",
    "لوحة القيادة التنفيذية",
    "الشبكات العصبية",
    "السلاسل الزمنية",
    "استخبارات السوق", "إستخبارات السوق",
]
for _kw in _arabic_keywords:
    check(f"excluded contains Arabic '{_kw}'", _kw in excluded)

_english_keywords = [
    "spatial analysis", "multiple regression", "real options",
    "executive dashboard", "neural networks", "time series", "market intelligence",
]
for _en in _english_keywords:
    check(f"excluded contains English '{_en}'", _en in excluded)


# ── 9. normalize_sheet_name ───────────────────────────────────────────────────
print("\nSection 9: normalize_sheet_name")
check("strips whitespace",      normalize_sheet_name("  Hello  ") == "hello")
check("lowercases ASCII",       normalize_sheet_name("Spatial Analysis") == "spatial analysis")
check("Arabic unchanged case",  normalize_sheet_name(" التحليل المكاني ") == "التحليل المكاني")


# ── 10. is_legacy_excluded_sheet — real sheet names ──────────────────────────
print("\nSection 10: is_legacy_excluded_sheet — real sheet names")

# Exact-match names
_exact_excluded = [
    "التحليل المكاني",
    "التحليل المكانى",
    "الانحدار المتعدد",
    "الإنحدار المتعدد",
    "الخيارات الحقيقية",
    "لوحة القيادة التنفيذية",
    "الشبكات العصبية",
    "السلاسل الزمنية",
    "استخبارات السوق",
    "إستخبارات السوق",
    "Spatial Analysis",
    "Multiple Regression",
    "Real Options",
    "Executive Dashboard",
    "Neural Networks",
    "Time Series",
    "Market Intelligence",
]
for _name in _exact_excluded:
    check(f"exact: '{_name}' excluded", is_legacy_excluded_sheet(_name))

# Real prefixed template names (substring match)
_prefixed_excluded = [
    "ANN — الشبكات العصبية",
    "ARIMA — السلاسل الزمنية",
    "استخبارات السوق — MI",
]
for _name in _prefixed_excluded:
    check(f"prefixed: '{_name}' excluded", is_legacy_excluded_sheet(_name))

# Sheets that must NOT be excluded
_safe_sheets = [
    "الافتراضات والمدخلات",
    "التقرير",
    "مقارنات البيوع",
    "DCF — التدفقات النقدية",
    "أفضل وأعلى استخدام — HABU",
    "Summary",
    "Three Approaches",
    "Certification",
]
for _name in _safe_sheets:
    check(f"safe: '{_name}' NOT excluded", not is_legacy_excluded_sheet(_name))


# ── 11. excel_builder still exports _LEGACY_EXCLUDED_SHEETS ───────────────────
print("\nSection 11: excel_builder backward-compatibility")
try:
    from reports.excel_builder import _LEGACY_EXCLUDED_SHEETS as _eb_excluded
    check("excel_builder._LEGACY_EXCLUDED_SHEETS importable", True)
    check("excel_builder set equals registry set",
          _eb_excluded == get_legacy_excluded_sheets())
except Exception as _e:
    check("excel_builder._LEGACY_EXCLUDED_SHEETS importable", False, str(_e))


# ── Summary ────────────────────────────────────────────────────────────────────
total = CHECKS_PASSED + CHECKS_FAILED
print(f"\n{'='*60}")
print(f"Results: {CHECKS_PASSED}/{total} passed")
if CHECKS_FAILED:
    print("SOME CHECKS FAILED")
    sys.exit(1)
else:
    print("ALL CHECKS PASSED")
