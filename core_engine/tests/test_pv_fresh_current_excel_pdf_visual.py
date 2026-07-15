# -*- coding: utf-8 -*-
"""
Batch 11 — 26 tests for Fresh Current Excel and PDF Generation + Final Visual Test.
Run with:
  .venv\\Scripts\\python.exe -m pytest core_engine/tests/test_pv_fresh_current_excel_pdf_visual.py -q
"""
import json
import pathlib
import re

import pytest

PROJ   = pathlib.Path(__file__).resolve().parent.parent.parent
CE     = PROJ / "core_engine"
BASE   = (CE / "instance" / "manual_review_outputs" /
          "professional_valuation_fresh_current_visual_test")
AUDITS = BASE / "audits"
FINAL  = BASE / "final_report"
VIS    = BASE / "visual_index"
LOGS   = BASE / "test_logs"
ACTUAL = BASE / "actual_files"
XL_PNG = BASE / "excel_sheet_pngs"
RP_T   = BASE / "pdf_page_pngs" / "traditional"
RP_D   = BASE / "pdf_page_pngs" / "detailed"
RP_P   = BASE / "pdf_page_pngs" / "professional"


def _j(name: str) -> dict:
    p = AUDITS / name
    assert p.exists(), f"Audit file missing: {name}"
    return json.loads(p.read_text(encoding="utf-8"))


# ── 01 — Project .venv used ───────────────────────────────────────────────────
def test_01_venv_used():
    env = _j("01_fresh_run_environment.json")
    exe = env["sys_executable"].lower().replace("\\", "/")
    assert ".venv" in exe, f"Expected .venv in executable path, got: {exe}"


# ── 02 — Excel COM 16.0 ──────────────────────────────────────────────────────
def test_02_excel_com_16():
    env = _j("01_fresh_run_environment.json")
    ver = str(env.get("excel_com_version", ""))
    assert ver.startswith("16"), f"Expected Excel 16.x, got {ver}"


# ── 03 — Batch start timestamp recorded ──────────────────────────────────────
def test_03_batch_start_recorded():
    env = _j("01_fresh_run_environment.json")
    assert env.get("batch_start"), "batch_start not recorded"
    # Must be an ISO timestamp
    assert "T" in env["batch_start"], "batch_start not ISO format"


# ── 04 — All four final artifacts generated after batch start ────────────────
def test_04_all_artifacts_generated_after_batch_start():
    gate = _j("05_current_file_age_gate.json")
    assert gate["all_age_ok"] is True, (
        "One or more artifacts predate the batch start — age gate FAIL"
    )


# ── 05 — No previous Batch artifact reused ───────────────────────────────────
def test_05_no_old_batch_artifact():
    gen = _j("03_fresh_excel_generation.json")
    assert gen["generated_during_batch"] is True
    pdf_gen = _j("04_fresh_pdf_generation.json")
    for tier in ("traditional", "detailed", "professional"):
        assert pdf_gen.get(tier, {}).get("generated_during_batch") is True, (
            f"{tier} PDF not generated during this batch"
        )


# ── 06 — Excel through integrated production flow ────────────────────────────
def test_06_excel_integrated_flow():
    gen = _j("03_fresh_excel_generation.json")
    assert gen["success"] is True, f"Excel generation failed: {gen.get('error')}"
    # builder_used must be set (template_driven or legacy_fallback — not unknown)
    assert gen["builder_used"] not in ("unknown", ""), (
        f"builder_used not set: {gen['builder_used']}"
    )


# ── 07 — builder_used = template_driven ──────────────────────────────────────
def test_07_builder_template_driven():
    gen = _j("03_fresh_excel_generation.json")
    assert gen["builder_used"] == "template_driven", (
        f"Expected template_driven, got {gen['builder_used']}"
    )


# ── 08 — fallback_used = false ───────────────────────────────────────────────
def test_08_no_fallback():
    gen = _j("03_fresh_excel_generation.json")
    assert gen["fallback_used"] is False, (
        f"Fallback was used: {gen['builder_used']}"
    )


# ── 09 — Excel has exactly 55 sheets ─────────────────────────────────────────
def test_09_excel_55_sheets():
    gen = _j("03_fresh_excel_generation.json")
    assert gen["sheet_count"] == 55, (
        f"Expected 55 sheets, got {gen['sheet_count']}"
    )


# ── 10 — Traditional PDF newly generated ─────────────────────────────────────
def test_10_traditional_pdf_generated():
    pdf_gen = _j("04_fresh_pdf_generation.json")
    t = pdf_gen.get("traditional", {})
    assert t.get("success") is True, f"Traditional PDF generation failed: {t.get('error')}"
    assert t.get("page_count", 0) >= 1, "Traditional PDF has no pages"


# ── 11 — Detailed PDF newly generated ────────────────────────────────────────
def test_11_detailed_pdf_generated():
    pdf_gen = _j("04_fresh_pdf_generation.json")
    d = pdf_gen.get("detailed", {})
    assert d.get("success") is True, f"Detailed PDF generation failed: {d.get('error')}"
    assert d.get("page_count", 0) >= 1, "Detailed PDF has no pages"


# ── 12 — Professional PDF newly generated ────────────────────────────────────
def test_12_professional_pdf_generated():
    pdf_gen = _j("04_fresh_pdf_generation.json")
    p = pdf_gen.get("professional", {})
    assert p.get("success") is True, f"Professional PDF generation failed: {p.get('error')}"
    assert p.get("page_count", 0) >= 1, "Professional PDF has no pages"


# ── 13 — All four files share same controlled context ────────────────────────
def test_13_same_context():
    prov = _j("02_fresh_input_provenance.json")
    assert prov.get("same_context_excel_and_pdfs") is True
    assert prov.get("sensitive_values_excluded") is True


# ── 14 — All 55 Excel sheets rendered via Excel COM ──────────────────────────
def test_14_all_55_sheets_rendered():
    render = _j("06_fresh_excel_real_render.json")
    assert render["renderer"] == "Excel COM"
    assert render["sheets_exported"] == 55, (
        f"Only {render['sheets_exported']} sheets exported (expected 55)"
    )


# ── 15 — Every PDF page rendered ─────────────────────────────────────────────
def test_15_every_pdf_page_rendered():
    render = _j("08_fresh_pdf_render_results.json")
    assert render.get("total_failed_pages", 0) == 0, (
        f"PDF render failures: {render['total_failed_pages']}"
    )
    for tier in ("traditional", "detailed", "professional"):
        t = render.get(tier, {})
        assert t.get("rendered_count", 0) > 0, f"{tier} PDF: no pages rendered"
        assert t.get("rendered_count") == t.get("page_count"), (
            f"{tier} PDF: rendered {t.get('rendered_count')} != total {t.get('page_count')}"
        )


# ── 16 — No critical visual defect ───────────────────────────────────────────
def test_16_no_critical_defect():
    excel_vis = _j("07_fresh_excel_visual_results.json")
    assert excel_vis["fail_count"] == 0, (
        f"Excel visual FAILED sheets: {excel_vis['fail_count']}"
    )


# ── 17 — Excel/PDF values consistent ─────────────────────────────────────────
def test_17_consistency_pass():
    cons = _j("10_fresh_excel_pdf_consistency.json")
    assert cons["overall_consistency"] is True, (
        "Excel/PDF consistency check failed"
    )
    assert not cons.get("critical_inconsistency", False), (
        "Critical inconsistency detected"
    )


# ── 18 — Value in words sheet exists and rendered ────────────────────────────
def test_18_value_in_words_rendered():
    excel_vis = _j("07_fresh_excel_visual_results.json")
    sheet_names = [s["sheet_name"] for s in excel_vis.get("sheets", [])]
    has_viw = any("بالحروف" in sn for sn in sheet_names)
    assert has_viw, "القيمة بالحروف sheet not found in workbook"
    viw_sheet = next((s for s in excel_vis["sheets"] if "بالحروف" in s["sheet_name"]), None)
    assert viw_sheet is not None
    assert viw_sheet["png_count"] >= 1, "القيمة بالحروف sheet has no rendered PNG"


# ── 19 — Certification states consistent ─────────────────────────────────────
def test_19_certification_state_consistent():
    cons = _j("10_fresh_excel_pdf_consistency.json")
    cert_rows = [c for c in cons["comparisons"] if c["field"] == "certification_state"]
    assert cert_rows, "No certification_state comparison found"
    assert cert_rows[0]["status"] == "PASS"


# ── 20 — Signature states consistent ─────────────────────────────────────────
def test_20_signature_state_consistent():
    cons = _j("10_fresh_excel_pdf_consistency.json")
    sig_rows = [c for c in cons["comparisons"] if c["field"] == "signature_state"]
    assert sig_rows, "No signature_state comparison found"
    assert sig_rows[0]["status"] == "PASS"


# ── 21 — Source artifacts unchanged after rendering ──────────────────────────
def test_21_source_artifacts_unchanged():
    render = _j("06_fresh_excel_real_render.json")
    assert render["hash_unchanged"] is True, "Workbook hash changed during rendering!"


# ── 22 — No orphan Excel process from batch11 ────────────────────────────────
def test_22_no_orphan_excel():
    render = _j("06_fresh_excel_real_render.json")
    before = render.get("orphan_excel_before", 0)
    after  = render.get("orphan_excel_after", 0)
    net_new = after - before
    assert net_new <= 0, f"Net new orphan Excel processes: {net_new}"


# ── 23 — Manifest exists ─────────────────────────────────────────────────────
def test_23_manifest_exists():
    md  = ACTUAL / "00_CURRENT_FILES_MANIFEST.md"
    jsn = ACTUAL / "00_CURRENT_FILES_MANIFEST.json"
    assert md.exists(),  "Manifest MD missing"
    assert jsn.exists(), "Manifest JSON missing"
    data = json.loads(jsn.read_text(encoding="utf-8"))
    assert data["total_files"] == 4, f"Manifest has {data['total_files']} files (expected 4)"
    assert data["all_generated_during_batch"] is True


# ── 24 — Open-all HTML page exists ───────────────────────────────────────────
def test_24_open_all_html_exists():
    idx = VIS / "OPEN_ALL_CURRENT_EXCEL_AND_PDF_FILES.html"
    assert idx.exists(), "Open-all HTML page missing"
    size = idx.stat().st_size
    assert size > 4000, f"HTML seems too small: {size} bytes"


# ── 25 — Four direct file links in HTML ──────────────────────────────────────
def test_25_four_direct_links_in_html():
    idx = VIS / "OPEN_ALL_CURRENT_EXCEL_AND_PDF_FILES.html"
    assert idx.exists(), "Open-all HTML page missing"
    content = idx.read_text(encoding="utf-8", errors="replace")
    required = [
        "01_FINAL_PRODUCTION_EXCEL_55_SHEETS.xlsx",
        "02_TRADITIONAL_REPORT.pdf",
        "03_DETAILED_REPORT.pdf",
        "04_PROFESSIONAL_REPORT.pdf",
    ]
    missing = [r for r in required if r not in content]
    assert not missing, f"Links missing from HTML: {missing}"


# ── 26 — No absolute path in HTML ────────────────────────────────────────────
def test_26_no_absolute_path_in_html():
    idx = VIS / "OPEN_ALL_CURRENT_EXCEL_AND_PDF_FILES.html"
    assert idx.exists()
    content = idx.read_text(encoding="utf-8", errors="replace")
    bad = re.findall(r'C:\\Users\\[A-Za-z]|/home/[a-z]', content)
    assert not bad, f"Absolute paths found in HTML: {bad[:5]}"
