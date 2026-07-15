"""
test_pv_excel_reference_parity.py
Tests for the Excel Reference Parity workbook and audit trail.
Run: python -m pytest core_engine/tests/test_pv_excel_reference_parity.py -q
"""
from __future__ import annotations
import json, pathlib
import pytest

_ROOT = pathlib.Path(__file__).parent.parent
_OUT  = _ROOT / "instance" / "manual_review_outputs" / "professional_valuation_excel_reference_parity"
_XL   = _OUT / "excel_outputs"
_AUD  = _OUT / "audits"
_PREV = _OUT / "visual_previews"
_RPT  = _OUT / "final_report"

_WB   = _XL  / "core_valuation_master_workbook_reference_parity.xlsx"
_IDX  = _PREV / "OPEN_EXCEL_REFERENCE_PARITY_REVIEW.html"
_FRPT = _RPT  / "final_excel_reference_parity_report.txt"

# ── Directory / file existence ────────────────────────────────────────────────

def test_FT01_output_dir_exists():
    assert _OUT.is_dir(), "Output directory missing"

def test_FT02_excel_workbook_exists():
    assert _WB.exists(), "Workbook file missing"

def test_FT03_workbook_non_empty():
    assert _WB.stat().st_size > 50_000, f"Workbook too small: {_WB.stat().st_size} bytes"

def test_FT04_visual_index_exists():
    assert _IDX.exists(), "Visual index HTML missing"

def test_FT05_final_report_exists():
    assert _FRPT.exists(), "Final report missing"

# ── Audit files ───────────────────────────────────────────────────────────────

def test_FT06_all_5_audits_exist():
    for i in range(1, 6):
        prefix = f"{i:02d}_"
        matches = list(_AUD.glob(prefix + "*.json"))
        assert matches, f"Audit {prefix}* missing"

def test_FT07_all_audits_advisory_only():
    for f in sorted(_AUD.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        assert d.get("advisory_only") is True, f"{f.name}: advisory_only != True"

def test_FT08_all_audits_no_fake_sources():
    for f in sorted(_AUD.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        assert d.get("fake_sources_created") is False, f"{f.name}: fake_sources_created != False"

def test_FT09_no_fake_credentials():
    for aud_name in ["03_traditional_methods_formula_audit.json",
                     "04_modern_methods_formula_audit.json",
                     "05_dashboard_final_qa_audit.json"]:
        p = _AUD / aud_name
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        assert d.get("fake_signature_created") is False, f"{aud_name}: fake_signature_created"
        assert d.get("fake_valuer_created") is False,    f"{aud_name}: fake_valuer_created"
        assert d.get("fake_license_created") is False,   f"{aud_name}: fake_license_created"

def test_FT10_no_fake_ann_output():
    p = _AUD / "04_modern_methods_formula_audit.json"
    assert p.exists()
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d.get("fake_ann_output") is False, "fake_ann_output must be False"
    assert d.get("ann_production_ready") is False, "ann_production_ready must be False"

# ── Workbook content ──────────────────────────────────────────────────────────

def test_FT11_workbook_has_50_sheets():
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")
    wb = openpyxl.load_workbook(_WB, read_only=True, data_only=True)
    assert len(wb.sheetnames) == 50, f"Expected 50 sheets, got {len(wb.sheetnames)}"
    wb.close()

def test_FT12_required_sheets_present():
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")
    required = [
        "Cover", "Sheet Index", "Executive Dashboard", "Charts Dashboard",
        "Print Report Summary", "Changelog",
        "NPV Analysis", "IRR Analysis", "Payback Analysis",
        "Risk Matrix", "Risk Register", "Sensitivity Matrix",
        "ESG Sustainability", "Standards Readiness", "Certification Readiness",
        "Method Reconciliation", "Final Value",
    ]
    wb = openpyxl.load_workbook(_WB, read_only=True, data_only=True)
    names = wb.sheetnames
    wb.close()
    for name in required:
        assert name in names, f"Sheet '{name}' missing"

def test_FT13_final_value_cell():
    """Executive Dashboard row 10 (cell B10, 0-indexed) should contain 1,130,000."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")
    wb = openpyxl.load_workbook(_WB, read_only=True, data_only=True)
    ws = wb["Executive Dashboard"]
    # Scan all cells in rows 6-40 for the final value
    found = False
    for row in ws.iter_rows(min_row=6, max_row=40, values_only=True):
        for cell in row:
            if cell == 1_130_000:
                found = True
                break
    wb.close()
    assert found, "Final value 1,130,000 not found in Executive Dashboard"

def test_FT14_workbook_size_reasonable():
    size_kb = _WB.stat().st_size // 1024
    assert size_kb >= 80, f"Workbook too small ({size_kb} KB) — likely corrupted"
    assert size_kb <= 5_000, f"Workbook suspiciously large ({size_kb} KB)"

# ── Visual index ──────────────────────────────────────────────────────────────

def test_FT15_no_internal_paths_in_index():
    content = _IDX.read_text(encoding="utf-8", errors="ignore")
    assert r"C:\Users\Lenovo" not in content, "Internal Windows path exposed in HTML"
    assert "C:/Users/Lenovo" not in content, "Internal Windows path exposed in HTML"

def test_FT16_visual_index_has_kpi_section():
    content = _IDX.read_text(encoding="utf-8", errors="ignore")
    assert "1,130,000" in content, "Final value missing from visual index"
    assert "advisory_only" in content, "Safety flag missing from visual index"

# ── Final report ──────────────────────────────────────────────────────────────

def test_FT17_final_report_status():
    d = json.loads(_FRPT.read_text(encoding="utf-8"))
    assert d.get("overall_status") in ("PASS", "PARTIAL"), "overall_status must be PASS or PARTIAL"
    assert d.get("advisory_only") is True
    assert d.get("fake_sources_created") is False
    assert d.get("fake_signature_created") is False
    assert d.get("internal_paths_exposed") is False

def test_FT18_final_report_has_blockers():
    d = json.loads(_FRPT.read_text(encoding="utf-8"))
    blockers = d.get("blockers", [])
    assert isinstance(blockers, list) and len(blockers) > 0, "Blockers list must be non-empty"

def test_FT19_audit_05_has_charts():
    p = _AUD / "05_dashboard_final_qa_audit.json"
    assert p.exists()
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d.get("charts_embedded", 0) >= 4, "Expected at least 4 embedded charts"
    assert d.get("kpi_cards_added") is True, "KPI cards flag missing"
    assert d.get("status") == "PASS"
