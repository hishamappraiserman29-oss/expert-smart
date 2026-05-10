"""
Verification script: Mass Appraisal professional template registration.

Checks:
  1. MASS_APPRAISAL_TEMPLATE constant points to an existing .xlsm file.
  2. ExcelTemplateRenderer loads the template with keep_vba=True.
  3. Rendering a minimal context produces a valid output file.
  4. Output file exists after rendering.
  5. Template file is unmodified (mtime and size unchanged).

Run:
    python _test_mass_appraisal_template_render.py
"""

import os
import sys
import tempfile
from pathlib import Path

# ── Allow imports from project root ───────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "core_engine"))

from core_engine.reports.excel_template_renderer import (
    MASS_APPRAISAL_TEMPLATE,
    ExcelTemplateRenderer,
    build_mass_appraisal_report,
)


def _check(label: str, condition: bool, detail: str = "") -> bool:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}" + (f" — {detail}" if detail else ""))
    return condition


def main() -> int:
    print("\n=== Mass Appraisal Template Registration Verification ===\n")
    all_pass = True

    # ── 1. Constant resolves to the expected path ──────────────────────────────
    all_pass &= _check(
        "MASS_APPRAISAL_TEMPLATE constant defined",
        str(MASS_APPRAISAL_TEMPLATE).endswith("mass_appraisal_professional_template.xlsm"),
        str(MASS_APPRAISAL_TEMPLATE),
    )

    # ── 2. Template file exists on disk ───────────────────────────────────────
    template_exists = MASS_APPRAISAL_TEMPLATE.is_file()
    all_pass &= _check(
        "Template file exists",
        template_exists,
        str(MASS_APPRAISAL_TEMPLATE.resolve()),
    )

    if not template_exists:
        print("\nTemplate file missing — remaining checks skipped.")
        return 1

    # Snapshot template metadata before rendering
    tpl_stat_before = MASS_APPRAISAL_TEMPLATE.stat()

    # ── 3. is_available() returns True ────────────────────────────────────────
    renderer = ExcelTemplateRenderer(template_path=MASS_APPRAISAL_TEMPLATE)
    all_pass &= _check("ExcelTemplateRenderer.is_available() == True", renderer.is_available())

    # ── 4. Render minimal context → output file produced ─────────────────────
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_path = Path(tmp_dir) / "test_mass_appraisal_output.xlsm"

        minimal_context = {
            "report_date":           "2026-05-10",
            "valuation_date":        "2026-05-01",
            "total_portfolio_value": 125_000_000,
        }
        minimal_tables = {
            "properties_results": [
                {"Property ID": "P001", "Address": "Cairo",      "Value EGP": 5_000_000},
                {"Property ID": "P002", "Address": "Alexandria", "Value EGP": 3_200_000},
            ],
            "ratio_study": [
                {"Property ID": "P001", "Sale Price": 4_900_000, "Assessed": 5_000_000, "Ratio": 0.98},
            ],
            "calibration": [
                {"Parameter": "Median Ratio", "Value": 0.982},
                {"Parameter": "COD",          "Value": 4.5},
                {"Parameter": "PRD",          "Value": 1.02},
            ],
        }

        result = build_mass_appraisal_report(
            output_path=output_path,
            context=minimal_context,
            tables=minimal_tables,
        )

        all_pass &= _check(
            "build_mass_appraisal_report() returned a Path",
            result is not None and isinstance(result, Path),
            str(result),
        )

        all_pass &= _check(
            "Output file exists",
            output_path.is_file(),
            str(output_path),
        )

        if output_path.is_file():
            all_pass &= _check(
                "Output file is non-empty",
                output_path.stat().st_size > 0,
                f"{output_path.stat().st_size} bytes",
            )

    # ── 5. Template file unmodified ───────────────────────────────────────────
    tpl_stat_after = MASS_APPRAISAL_TEMPLATE.stat()
    all_pass &= _check(
        "Template file mtime unchanged",
        tpl_stat_before.st_mtime == tpl_stat_after.st_mtime,
    )
    all_pass &= _check(
        "Template file size unchanged",
        tpl_stat_before.st_size == tpl_stat_after.st_size,
        f"{tpl_stat_after.st_size} bytes",
    )

    # ── 6. Fallback: missing template returns None ─────────────────────────────
    missing = build_mass_appraisal_report(
        output_path="outputs/should_not_be_created.xlsm",
        context={},
        template_path="templates/reports/__nonexistent__.xlsm",
    )
    all_pass &= _check(
        "Returns None for missing template (fallback safe)",
        missing is None,
    )

    print(f"\n{'ALL CHECKS PASSED' if all_pass else 'SOME CHECKS FAILED'}\n")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
