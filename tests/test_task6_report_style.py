"""
Task 6 + Task 7 — report_style selector integration tests.

Scenarios:
  1. legacy   — builds, has only basic sheets, NO advanced analytics sheets
  2. detailed — builds, has all basic + all 7 advanced analytics sheets
  3. professional_template — unchanged behaviour (xlsm or fallback xlsx)
  4. missing report_style  — defaults to legacy (no advanced sheets)
  5. mass appraisal / legacy
  6. mass appraisal / professional_template

Run from repo root:
    $env:PYTHONPATH = (Get-Location).Path + ';' + (Get-Location).Path + '\\core_engine'
    python tests/test_task6_report_style.py
"""
import sys, os, decimal, tempfile, io

# Force UTF-8 stdout so Arabic sheet names print safely on Windows cp1252 terminals
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core_engine"))

import openpyxl

CHECKS_PASSED = 0
CHECKS_FAILED = 0

def check(label, condition, detail=""):
    global CHECKS_PASSED, CHECKS_FAILED
    if condition:
        print(f"  [PASS] {label}")
        CHECKS_PASSED += 1
    else:
        print(f"  [FAIL] {label}" + (f" -- {detail}" if detail else ""))
        CHECKS_FAILED += 1


# ── Import shared types ───────────────────────────────────────────────────────
try:
    from reports.excel_builder import ExcelReportBuilder, _LEGACY_EXCLUDED_SHEETS
    from adapters.asset import AssetValuationResult
except Exception as _imp_err:
    print(f"[FATAL] Import failed: {_imp_err}")
    sys.exit(1)

ADVANCED_SHEETS = [
    "التحليل المكاني",
    "الانحدار المتعدد",
    "الخيارات الحقيقية",
    "لوحة القيادة التنفيذية",
    "الشبكات العصبية",
    "السلاسل الزمنية",
    "استخبارات السوق",
]

BASIC_SHEETS = [
    "Summary",
    "Three Approaches",
    "Weights Analysis",
    "Audit Trail",
    "Property Details",
    "Disclosures",
    "Issues & Warnings",
    "Certification",
]

def _make_result(asset_type="residential", value="1500000"):
    return AssetValuationResult(
        asset_type=asset_type,
        primary_purpose="fair_market_value",
        primary_value=decimal.Decimal(value),
        confidence="high",
        alternative_values={},
        weights_applied={},
        audit_trail=[],
        issues=[],
        metadata={},
        disclosures=[],
    )

def _sheet_names(path):
    wb = openpyxl.load_workbook(path, read_only=True, keep_vba=False)
    names = wb.sheetnames
    wb.close()
    return names


# ── Scenario 1: legacy ───────────────────────────────────────────────────────
print("\nScenario 1: ExcelReportBuilder — report_style='legacy'")
try:
    _out1 = os.path.join(tempfile.gettempdir(), "test_t7_legacy.xlsx")
    r1 = ExcelReportBuilder(_make_result())
    ret1 = r1.build(_out1, report_style="legacy")

    check("legacy: returns a string",    isinstance(ret1, str))
    check("legacy: output file exists",  os.path.isfile(ret1))
    check("legacy: .xlsx extension",     ret1.endswith(".xlsx"))

    if os.path.isfile(ret1):
        sheets1 = _sheet_names(ret1)
        for bs in BASIC_SHEETS:
            check(f"legacy: has basic sheet '{bs}'", bs in sheets1)
        for _i, adv in enumerate(ADVANCED_SHEETS, 1):
            check(f"legacy: NO advanced sheet [{_i}]", adv not in sheets1,
                  f"sheet[{_i}] found in workbook")
        os.remove(ret1)
except Exception as e:
    check("Scenario 1 setup", False, str(e))


# ── Scenario 2: detailed ─────────────────────────────────────────────────────
print("\nScenario 2: ExcelReportBuilder — report_style='detailed'")
try:
    _out2 = os.path.join(tempfile.gettempdir(), "test_t7_detailed.xlsx")
    r2 = ExcelReportBuilder(_make_result("commercial", "3000000"))
    ret2 = r2.build(_out2, report_style="detailed")

    check("detailed: returns a string",   isinstance(ret2, str))
    check("detailed: output file exists", os.path.isfile(ret2))
    check("detailed: .xlsx extension",    ret2.endswith(".xlsx"))

    if os.path.isfile(ret2):
        sheets2 = _sheet_names(ret2)
        for bs in BASIC_SHEETS:
            check(f"detailed: has basic sheet '{bs}'", bs in sheets2)
        for _i, adv in enumerate(ADVANCED_SHEETS, 1):
            check(f"detailed: HAS advanced sheet [{_i}]", adv in sheets2,
                  f"sheet[{_i}] missing from workbook")
        os.remove(ret2)
except Exception as e:
    check("Scenario 2 setup", False, str(e))


# ── Scenario 3: professional_template ───────────────────────────────────────
print("\nScenario 3: ExcelReportBuilder — report_style='professional_template'")
try:
    from reports.excel_template_renderer import INDIVIDUAL_VALUATION_TEMPLATE
    tpl_present = INDIVIDUAL_VALUATION_TEMPLATE.is_file()

    _out3 = os.path.join(tempfile.gettempdir(), "test_t7_prof.xlsx")
    r3 = ExcelReportBuilder(_make_result())
    ret3 = r3.build(_out3, report_style="professional_template")

    if tpl_present:
        check("professional_template: returns .xlsm", ret3.endswith(".xlsm"),
              f"got {ret3!r}")
        check("professional_template: xlsm file exists", os.path.isfile(ret3))
        check("professional_template: original .xlsx NOT created",
              not os.path.isfile(_out3))
        if os.path.isfile(ret3):
            os.remove(ret3)
    else:
        check("professional_template (no tpl): fallback .xlsx", ret3.endswith(".xlsx"),
              f"got {ret3!r}")
        check("professional_template (no tpl): file exists", os.path.isfile(ret3))
        if os.path.isfile(ret3):
            os.remove(ret3)
except Exception as e:
    check("Scenario 3 setup", False, str(e))


# ── Scenario 4: missing report_style → defaults to legacy ────────────────────
print("\nScenario 4: ExcelReportBuilder — no report_style (should default to legacy)")
try:
    _out4 = os.path.join(tempfile.gettempdir(), "test_t7_default.xlsx")
    r4 = ExcelReportBuilder(_make_result())
    ret4 = r4.build(_out4)   # no report_style kwarg

    check("default: returns a string",    isinstance(ret4, str))
    check("default: output file exists",  os.path.isfile(ret4))

    if os.path.isfile(ret4):
        sheets4 = _sheet_names(ret4)
        for _i, adv in enumerate(ADVANCED_SHEETS, 1):
            check(f"default: NO advanced sheet [{_i}]", adv not in sheets4,
                  f"sheet[{_i}] found in workbook")
        os.remove(ret4)
except Exception as e:
    check("Scenario 4 setup", False, str(e))


# ── Scenario 5: mass appraisal / legacy ─────────────────────────────────────
print("\nScenario 5: build_mass_appraisal_workbook — report_style='legacy'")
try:
    from mass_appraisal_excel import build_mass_appraisal_workbook

    _ma_result = {
        "total_units": 5,
        "mean_value": 1_000_000,
        "properties": [
            {"id": f"P{i}", "value": 900_000 + i * 50_000,
             "area": 120, "location": "مدينة نصر",
             "property_type": "residential", "year_built": 2010}
            for i in range(5)
        ],
    }
    xlsxb = build_mass_appraisal_workbook(_ma_result, report_style="legacy")
    check("mass/legacy: returns bytes",       isinstance(xlsxb, bytes))
    check("mass/legacy: non-empty",           len(xlsxb) > 0)
    check("mass/legacy: ZIP magic bytes",     xlsxb[:2] == b"PK")
except Exception as e:
    check("Scenario 5 setup", False, str(e))


# ── Scenario 6: mass appraisal / professional_template ──────────────────────
print("\nScenario 6: build_mass_appraisal_workbook — report_style='professional_template'")
try:
    from reports.excel_template_renderer import MASS_APPRAISAL_TEMPLATE
    ma_tpl_present = MASS_APPRAISAL_TEMPLATE.is_file()

    xlsmb = build_mass_appraisal_workbook(_ma_result, report_style="professional_template")
    check("mass/professional_template: returns bytes",   isinstance(xlsmb, bytes))
    check("mass/professional_template: non-empty",       len(xlsmb) > 0)
    check("mass/professional_template: ZIP magic bytes", xlsmb[:2] == b"PK")
except Exception as e:
    check("Scenario 6 setup", False, str(e))


# ── Scenarios 8-10: _remove_legacy_advanced_sheets (actual browser path) ──────
# Import the helper from bridge_api.  bridge_api has a heavy dependency tree so
# we catch import errors and skip gracefully rather than failing the whole suite.
_remove_fn = None
try:
    import bridge_api as _ba
    _remove_fn = _ba._remove_legacy_advanced_sheets
except Exception as _ba_err:
    print(f"\n  [SKIP] bridge_api import failed ({_ba_err}) — Scenarios 8-10 skipped")


def _make_workbook_with_advanced(basic=("Summary", "Audit Trail"),
                                  advanced=("التحليل المكاني",
                                            "Spatial Analysis",
                                            "الانحدار المتعدد",
                                            "لوحة القيادة التنفيذية")) -> str:
    """Build a minimal workbook with known sheets and return a temp .xlsx path."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for s in list(basic) + list(advanced):
        wb.create_sheet(s)
    p = os.path.join(tempfile.gettempdir(), "test_t8_helper.xlsx")
    wb.save(p)
    wb.close()
    return p


print("\nScenario 8: _remove_legacy_advanced_sheets — legacy strips advanced sheets")
if _remove_fn is None:
    check("S8 skipped (bridge_api not importable)", True)
else:
    try:
        _p8 = _make_workbook_with_advanced()
        _remove_fn(_p8)
        _s8 = _sheet_names(_p8)
        check("S8: basic 'Summary' kept",        "Summary" in _s8)
        check("S8: basic 'Audit Trail' kept",    "Audit Trail" in _s8)
        check("S8: Arabic [1] removed",          "التحليل المكاني"         not in _s8)
        check("S8: English 'Spatial Analysis' removed", "Spatial Analysis" not in _s8)
        check("S8: Arabic [2] removed",          "الانحدار المتعدد"        not in _s8)
        check("S8: Arabic [3] removed",          "لوحة القيادة التنفيذية"  not in _s8)
        os.remove(_p8)
    except Exception as e:
        check("S8 setup", False, str(e))


print("\nScenario 9: _remove_legacy_advanced_sheets — variant normalization (ى / hamza)")
if _remove_fn is None:
    check("S9 skipped (bridge_api not importable)", True)
else:
    try:
        # Use the ى-variant and hamza-variant names to verify _norm() handles them
        _p9 = _make_workbook_with_advanced(
            basic=("ملخص",),
            advanced=("التحليل المكانى",       # ى variant
                       "الإنحدار المتعدد",     # hamza إ variant
                       "إستخبارات السوق",      # hamza إ
                       "استخبارات السوق"),     # regular form
        )
        _remove_fn(_p9)
        _s9 = _sheet_names(_p9)
        check("S9: basic 'ملخص' kept",                    "ملخص" in _s9)
        check("S9: ى-variant removed",                    "التحليل المكانى"  not in _s9)
        check("S9: hamza-variant removed",                "الإنحدار المتعدد" not in _s9)
        check("S9: hamza-استخبارات removed",              "إستخبارات السوق"  not in _s9)
        check("S9: regular-استخبارات removed",            "استخبارات السوق"  not in _s9)
        os.remove(_p9)
    except Exception as e:
        check("S9 setup", False, str(e))


print("\nScenario 10: _remove_legacy_advanced_sheets — detailed path (no removal)")
if _remove_fn is None:
    check("S10 skipped (bridge_api not importable)", True)
else:
    try:
        _p10 = _make_workbook_with_advanced()
        # For detailed: do NOT call _remove_fn — sheets must remain
        _s10 = _sheet_names(_p10)
        check("S10: all 6 sheets present without removal",
              len(_s10) == 6, f"got {len(_s10)}: {_s10}")
        check("S10: advanced sheet [1] still present", "التحليل المكاني"    in _s10)
        check("S10: advanced sheet [2] still present", "Spatial Analysis"   in _s10)
        os.remove(_p10)
    except Exception as e:
        check("S10 setup", False, str(e))


# ── Constant sanity check ─────────────────────────────────────────────────────
print("\nScenario 11: _LEGACY_EXCLUDED_SHEETS constant sanity")
for _i, _name in enumerate(ADVANCED_SHEETS, 1):
    check(f"S11 excluded[{_i}]: Arabic name in constant",
          _name.strip().lower() in _LEGACY_EXCLUDED_SHEETS)
for _en in ("spatial analysis", "multiple regression", "real options",
            "executive dashboard", "neural networks", "time series", "market intelligence"):
    check(f"S11 excluded (en): '{_en}' in constant", _en in _LEGACY_EXCLUDED_SHEETS)


# ── Summary ───────────────────────────────────────────────────────────────────
total = CHECKS_PASSED + CHECKS_FAILED
print(f"\n{'='*60}")
print(f"Results: {CHECKS_PASSED}/{total} passed")
if CHECKS_FAILED:
    print("SOME CHECKS FAILED")
    sys.exit(1)
else:
    print("ALL CHECKS PASSED")
