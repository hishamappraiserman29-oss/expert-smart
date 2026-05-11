"""
Task 6 — report_style selector integration tests.
Covers four combinations:
  1. individual / legacy
  2. individual / professional_template (template present => xlsm)
  3. mass appraisal / legacy
  4. mass appraisal / professional_template (template present => xlsm)
Run from repo root:
    python _test_task6_report_style.py
"""
import sys, os, types, importlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core_engine"))

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


# ── Scenario 1: individual / legacy ─────────────────────────────────────────
print("\nScenario 1: ExcelReportBuilder — report_style='legacy'")
try:
    from reports.excel_builder import ExcelReportBuilder
    from adapters.asset import AssetValuationResult

    _result = AssetValuationResult(
        asset_type="residential",
        primary_purpose="fair_market_value",
        primary_value=__import__("decimal").Decimal("1500000"),
        confidence="high",
        alternative_values={},
        weights_applied={},
        audit_trail=[],
        issues=[],
        metadata={},
        disclosures=[],
    )
    import tempfile, pathlib
    _out = os.path.join(tempfile.gettempdir(), "test_t6_legacy.xlsx")
    builder = ExcelReportBuilder(_result)
    returned = builder.build(_out, report_style="legacy")
    check("legacy: returns a string", isinstance(returned, str))
    check("legacy: output file exists", os.path.isfile(returned))
    check("legacy: no xlsm for legacy", not returned.endswith(".xlsm"))
    if os.path.isfile(returned):
        os.remove(returned)
except Exception as e:
    check("Scenario 1 setup", False, str(e))


# ── Scenario 2: individual / professional_template ───────────────────────────
print("\nScenario 2: ExcelReportBuilder — report_style='professional_template'")
try:
    from reports.excel_template_renderer import INDIVIDUAL_VALUATION_TEMPLATE
    from adapters.asset import AssetValuationResult as _AVR2
    tpl_present = INDIVIDUAL_VALUATION_TEMPLATE.is_file()

    _result2 = _AVR2(
        asset_type="commercial",
        primary_purpose="fair_market_value",
        primary_value=__import__("decimal").Decimal("3000000"),
        confidence="medium",
        alternative_values={},
        weights_applied={},
        audit_trail=[],
        issues=[],
        metadata={},
        disclosures=[],
    )
    _out2 = os.path.join(tempfile.gettempdir(), "test_t6_prof.xlsx")
    builder2 = ExcelReportBuilder(_result2)
    returned2 = builder2.build(_out2, report_style="professional_template")

    if tpl_present:
        check("professional_template: returns xlsm", returned2.endswith(".xlsm"),
              f"got {returned2!r}")
        check("professional_template: xlsm file exists", os.path.isfile(returned2))
        check("professional_template: original .xlsx NOT created",
              not os.path.isfile(_out2))
        if os.path.isfile(returned2):
            os.remove(returned2)
    else:
        # Template absent => fallback to legacy xlsx
        check("professional_template (no tpl): fallback is xlsx", returned2.endswith(".xlsx"),
              f"got {returned2!r}")
        check("professional_template (no tpl): file exists", os.path.isfile(returned2))
        if os.path.isfile(returned2):
            os.remove(returned2)
except Exception as e:
    check("Scenario 2 setup", False, str(e))


# ── Scenario 3: mass appraisal / legacy ─────────────────────────────────────
print("\nScenario 3: build_mass_appraisal_workbook — report_style='legacy'")
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
    check("mass/legacy: returns bytes", isinstance(xlsxb, bytes))
    check("mass/legacy: non-empty", len(xlsxb) > 0)
    # Legacy output starts with PK (ZIP/xlsx magic bytes)
    check("mass/legacy: xlsx magic bytes", xlsxb[:2] == b"PK")
except Exception as e:
    check("Scenario 3 setup", False, str(e))


# ── Scenario 4: mass appraisal / professional_template ──────────────────────
print("\nScenario 4: build_mass_appraisal_workbook — report_style='professional_template'")
try:
    from reports.excel_template_renderer import MASS_APPRAISAL_TEMPLATE
    ma_tpl_present = MASS_APPRAISAL_TEMPLATE.is_file()

    xlsmb = build_mass_appraisal_workbook(_ma_result, report_style="professional_template")
    check("mass/professional_template: returns bytes", isinstance(xlsmb, bytes))
    check("mass/professional_template: non-empty", len(xlsmb) > 0)
    if ma_tpl_present:
        # xlsm files still start with PK (ZIP-based)
        check("mass/professional_template: ZIP magic bytes", xlsmb[:2] == b"PK")
    else:
        check("mass/professional_template (no tpl): fallback returns bytes",
              xlsmb[:2] == b"PK")
except Exception as e:
    check("Scenario 4 setup", False, str(e))


# ── Summary ───────────────────────────────────────────────────────────────────
total = CHECKS_PASSED + CHECKS_FAILED
print(f"\n{'='*55}")
print(f"Results: {CHECKS_PASSED}/{total} passed")
if CHECKS_FAILED:
    print("SOME CHECKS FAILED")
    sys.exit(1)
else:
    print("ALL CHECKS PASSED")
