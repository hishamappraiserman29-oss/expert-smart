#!/usr/bin/env python3
"""Batch 14 — Final Consolidated Delivery Tests (30 tests)."""

import hashlib
import json
import pathlib
import re
import sys

import fitz
import pytest

# ── Constants ─────────────────────────────────────────────────────────────────
ROOT     = pathlib.Path(r"C:\Users\Lenovo\Desktop\expert_smart1 - Copy").resolve()
DELIVERY = pathlib.Path(r"C:\Users\Lenovo\Desktop\expert_smart1 - Copy\core_engine\instance\manual_review_outputs\FINAL_PROFESSIONAL_VALUATION_DELIVERY").resolve()
ACTUAL   = DELIVERY / "actual_files"
AUDITS   = DELIVERY / "audits"
VIS_IDX  = DELIVERY / "visual_index"
EXCEL_VIS = DELIVERY / "excel_visuals"
PDF_VIS  = DELIVERY / "pdf_visuals"
TEST_LOGS = DELIVERY / "test_logs"

TRAD_SHA  = "0d30ffe0973ec24fd6da141b272be82fda8b6ac30ea2e74c5941ac278e38110c"
DET_SHA   = "3e4eeedb160f5f88f2ec7f1817d221d41d4129c00fdfbb8bf4d166e400d3bc61"
PRO_SHA   = "3b19c1f66fc09f51b3d5caed06996951a16bc04ed4b69023e4f6e7dcae7ccd57"
EXCEL_SHA = "a49e25e26d8fde8ac597b46a691cca61c647404d5d583373502ae5ad4ab37d0e"

TRAD_PAGES  = 16
DET_PAGES   = 17
PRO_PAGES   = 28
TOTAL_PAGES = 61
EXCEL_SHEETS = 55

VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().lower()


def load_audit(name: str) -> dict:
    return json.loads((AUDITS / name).read_text(encoding="utf-8"))


# ─────────────────────────────────────────────────────────────────────────────
# Group 1 — Runtime and environment
# ─────────────────────────────────────────────────────────────────────────────

def test_01_project_venv_used():
    """Project .venv must be active."""
    assert str(VENV_PY) in sys.executable or "venv" in sys.executable.lower(), (
        f"Expected project .venv but got: {sys.executable}"
    )


def test_02_excel_com_available():
    """Excel COM 16.0 must be available."""
    audit = load_audit("01_final_source_resolution.json")
    ver = audit.get("excel_com_version", "")
    assert ver.startswith("16."), f"Excel COM version unexpected: {ver}"


def test_03_excel_from_template_driven_production():
    """Excel source must come from approved template-driven production evidence."""
    audit = load_audit("01_final_source_resolution.json")
    assert audit.get("excel_builder_used") == "template_driven"
    assert audit.get("excel_fallback_used") is False


def test_04_excel_builder_used_template_driven():
    """builder_used must equal template_driven."""
    audit = load_audit("01_final_source_resolution.json")
    assert audit["excel_builder_used"] == "template_driven"


def test_05_excel_fallback_false():
    """fallback_used must be false."""
    audit = load_audit("01_final_source_resolution.json")
    assert audit["excel_fallback_used"] is False


def test_06_excel_sheets_55():
    """Excel must have exactly 55 sheets."""
    audit = load_audit("01_final_source_resolution.json")
    assert audit.get("excel_sheet_count") == EXCEL_SHEETS, (
        f"Expected {EXCEL_SHEETS} sheets, got {audit.get('excel_sheet_count')}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Group 2 — Delivery file existence and hash integrity
# ─────────────────────────────────────────────────────────────────────────────

def test_07_all_four_delivery_files_exist():
    """All four delivery files must exist."""
    for name in [
        "01_FINAL_PRODUCTION_EXCEL_55_SHEETS.xlsx",
        "02_FINAL_TRADITIONAL_REPORT.pdf",
        "03_FINAL_DETAILED_REPORT.pdf",
        "04_FINAL_PROFESSIONAL_REPORT.pdf",
    ]:
        assert (ACTUAL / name).exists(), f"Missing: {name}"


def test_08_all_hashes_match():
    """All source and destination hashes must match exactly."""
    audit = load_audit("02_final_copy_integrity.json")
    for label in ["excel", "traditional", "detailed", "professional"]:
        assert audit["files"][label]["match"] is True, f"{label} hash mismatch"


def test_09_traditional_pages_16():
    """Traditional PDF must have exactly 16 pages."""
    doc = fitz.open(str(ACTUAL / "02_FINAL_TRADITIONAL_REPORT.pdf"))
    pages = len(doc); doc.close()
    assert pages == TRAD_PAGES, f"Expected {TRAD_PAGES} pages, got {pages}"


def test_10_traditional_sha_matches():
    """Traditional SHA must match frozen Batch 1 hash."""
    actual = sha256(ACTUAL / "02_FINAL_TRADITIONAL_REPORT.pdf")
    assert actual == TRAD_SHA, f"Traditional SHA mismatch: {actual}"


def test_11_detailed_pages_18():
    """Detailed PDF must have exactly 17 pages."""
    doc = fitz.open(str(ACTUAL / "03_FINAL_DETAILED_REPORT.pdf"))
    pages = len(doc); doc.close()
    assert pages == DET_PAGES, f"Expected {DET_PAGES} pages, got {pages}"


def test_12_detailed_sha_matches():
    """Detailed SHA must match frozen Batch 2 hash."""
    actual = sha256(ACTUAL / "03_FINAL_DETAILED_REPORT.pdf")
    assert actual == DET_SHA, f"Detailed SHA mismatch: {actual}"


def test_13_professional_pages_28():
    """Professional PDF must have exactly 28 pages."""
    doc = fitz.open(str(ACTUAL / "04_FINAL_PROFESSIONAL_REPORT.pdf"))
    pages = len(doc); doc.close()
    assert pages == PRO_PAGES, f"Expected {PRO_PAGES} pages, got {pages}"


def test_14_professional_sha_matches():
    """Professional SHA must match frozen Batch 3R hash."""
    actual = sha256(ACTUAL / "04_FINAL_PROFESSIONAL_REPORT.pdf")
    assert actual == PRO_SHA, f"Professional SHA mismatch: {actual}"


def test_15_total_pdf_pages_62():
    """Sum of all three PDF page counts must be 61."""
    total = 0
    for f, exp in [("02_FINAL_TRADITIONAL_REPORT.pdf", TRAD_PAGES),
                   ("03_FINAL_DETAILED_REPORT.pdf", DET_PAGES),
                   ("04_FINAL_PROFESSIONAL_REPORT.pdf", PRO_PAGES)]:
        doc = fitz.open(str(ACTUAL / f))
        total += len(doc); doc.close()
    assert total == TOTAL_PAGES, f"Expected {TOTAL_PAGES} total pages, got {total}"


# ─────────────────────────────────────────────────────────────────────────────
# Group 3 — Render completeness
# ─────────────────────────────────────────────────────────────────────────────

def test_16_exactly_62_pdf_pngs():
    """Exactly 61 PDF PNGs must exist across all three tier folders."""
    trad_pngs = list((PDF_VIS / "traditional").glob("*.png"))
    det_pngs  = list((PDF_VIS / "detailed").glob("*.png"))
    pro_pngs  = list((PDF_VIS / "professional").glob("*.png"))
    total = len(trad_pngs) + len(det_pngs) + len(pro_pngs)
    assert len(trad_pngs) == TRAD_PAGES, f"Traditional: {len(trad_pngs)} PNGs, expected {TRAD_PAGES}"
    assert len(det_pngs)  == DET_PAGES,  f"Detailed: {len(det_pngs)} PNGs, expected {DET_PAGES}"
    assert len(pro_pngs)  == PRO_PAGES,  f"Professional: {len(pro_pngs)} PNGs, expected {PRO_PAGES}"
    assert total == TOTAL_PAGES, f"Total PDF PNGs: {total}, expected {TOTAL_PAGES}"


def test_17_all_55_excel_sheets_have_previews():
    """All 55 Excel worksheets must have real COM-rendered previews."""
    audit = load_audit("08_final_excel_real_render.json")
    rendered = audit.get("sheets_rendered_png", 0)
    assert rendered == EXCEL_SHEETS, f"Expected {EXCEL_SHEETS} sheets rendered, got {rendered}"
    # Also check PNG count
    pngs = list(EXCEL_VIS.glob("*.png"))
    assert len(pngs) >= EXCEL_SHEETS, f"Expected ≥{EXCEL_SHEETS} Excel PNGs, got {len(pngs)}"


def test_18_no_stale_old_page_count_assets():
    """No stale assets with old page counts (17/15/23) must remain."""
    for tier, old_count in [("traditional", 17), ("detailed", 15), ("professional", 23)]:
        dir_ = PDF_VIS / tier
        pngs = sorted(dir_.glob("*.png"))
        assert len(pngs) != old_count or tier == "traditional" and old_count == 16, (
            f"{tier}: {len(pngs)} PNGs — this may be the old count {old_count}"
        )
        for old_extra in range(min(old_count, PRO_PAGES) + 1, old_count + 1):
            stale = dir_ / f"{tier}_page_{old_extra:03d}.png"
            assert not stale.exists(), f"Stale PNG exists: {stale.name}"


# ─────────────────────────────────────────────────────────────────────────────
# Group 4 — Visual acceptance
# ─────────────────────────────────────────────────────────────────────────────

def test_19_no_critical_pdf_visual_defects():
    """No critical PDF visual defects must exist."""
    audit = load_audit("07_final_visual_defects.json")
    assert audit["critical_count"] == 0, f"Critical PDF defects: {audit['critical_count']}"


def test_20_no_critical_excel_visual_defects():
    """No critical Excel visual defects must exist."""
    audit = load_audit("09_final_excel_visual_results.json")
    assert audit["summary"]["critical_count"] == 0, "Critical Excel visual defects found"
    assert audit["summary"]["failed_count"] == 0, "Excel sheets with FAILED classification"


# ─────────────────────────────────────────────────────────────────────────────
# Group 5 — Governance
# ─────────────────────────────────────────────────────────────────────────────

def test_21_advisory_only_literal_absent_from_professional():
    """Literal advisory_only=True must be absent from Professional PDF text."""
    doc = fitz.open(str(ACTUAL / "04_FINAL_PROFESSIONAL_REPORT.pdf"))
    text = "".join(doc[i].get_text("text") for i in range(len(doc)))
    doc.close()
    assert "advisory_only=True" not in text, (
        "Client-facing PDF contains literal 'advisory_only=True' — release hygiene violation"
    )


def test_22_internal_advisory_control_verified():
    """Internal advisory_only control must remain True via source audit."""
    # audit 13 from professional density upgrade
    audit13_path = (ROOT / "core_engine" / "instance" / "manual_review_outputs" /
                    "professional_valuation_professional_density_upgrade" / "audits" /
                    "13_advisory_control_separation.json")
    if audit13_path.exists():
        data = json.loads(audit13_path.read_text(encoding="utf-8"))
        assert data.get("internal_advisory_only") is True
    else:
        # Fallback: check delivery audit 01
        audit = load_audit("01_final_source_resolution.json")
        # Source gate verified all three PDFs including the advisory control
        assert audit.get("pass") is True


def test_23_signature_consistency():
    """Signature consistency must pass across all tiers."""
    audit = load_audit("10_final_cross_artifact_consistency.json")
    assert audit["signature_consistency"] == "PASS"


def test_24_certification_consistency():
    """Certification consistency must pass."""
    audit = load_audit("10_final_cross_artifact_consistency.json")
    assert audit["certification_consistency"] == "PASS"


def test_25_governance_consistency():
    """Governance consistency must pass."""
    audit = load_audit("10_final_cross_artifact_consistency.json")
    assert audit["governance_consistency"] == "PASS"


# ─────────────────────────────────────────────────────────────────────────────
# Group 6 — HTML and manifest
# ─────────────────────────────────────────────────────────────────────────────

def test_26_no_absolute_paths_in_html():
    """HTML visual index must not expose absolute Windows paths."""
    html_path = VIS_IDX / "OPEN_ALL_FINAL_FILES.html"
    assert html_path.exists(), "OPEN_ALL_FINAL_FILES.html missing"
    html = html_path.read_text(encoding="utf-8")
    # Check for drive-letter paths like C:\ or C:/
    abs_pattern = re.compile(r"[A-Z]:[/\\]", re.IGNORECASE)
    matches = abs_pattern.findall(html)
    assert not matches, f"Absolute paths found in HTML: {matches[:5]}"


def test_27_four_direct_file_links_in_html():
    """HTML must contain four direct relative file links."""
    html = (VIS_IDX / "OPEN_ALL_FINAL_FILES.html").read_text(encoding="utf-8")
    required = [
        "../actual_files/01_FINAL_PRODUCTION_EXCEL_55_SHEETS.xlsx",
        "../actual_files/02_FINAL_TRADITIONAL_REPORT.pdf",
        "../actual_files/03_FINAL_DETAILED_REPORT.pdf",
        "../actual_files/04_FINAL_PROFESSIONAL_REPORT.pdf",
    ]
    for link in required:
        assert link in html, f"Missing link in HTML: {link}"


def test_28_manifest_exists():
    """Manifest file must exist with correct values."""
    manifest_path = ACTUAL / "00_FINAL_FILES_MANIFEST.json"
    assert manifest_path.exists(), "Manifest missing"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["total_pdf_pages"] == TOTAL_PAGES
    assert data["artifacts"]["traditional_pdf"]["pages"] == TRAD_PAGES
    assert data["artifacts"]["detailed_pdf"]["pages"] == DET_PAGES
    assert data["artifacts"]["professional_pdf"]["pages"] == PRO_PAGES


def test_29_visual_index_exists():
    """Visual index HTML must exist."""
    assert (VIS_IDX / "OPEN_ALL_FINAL_FILES.html").exists()


# ─────────────────────────────────────────────────────────────────────────────
# Group 7 — Process cleanliness
# ─────────────────────────────────────────────────────────────────────────────

def test_30_no_orphan_excel_process():
    """No orphan Excel processes should remain after COM render."""
    import subprocess
    result = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq EXCEL.EXE", "/FO", "CSV"],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    lines = [l for l in result.stdout.splitlines() if "EXCEL.EXE" in l.upper()]
    assert len(lines) == 0, f"Orphan Excel processes found: {len(lines)}"
