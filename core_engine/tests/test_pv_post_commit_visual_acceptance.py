"""
Post-Commit Visual Acceptance Tests — FINAL_PROFESSIONAL_VALUATION_DELIVERY
25 tests verifying repository state, artifact integrity, rendering completeness,
visual inspection results, defect classification, and governance compliance.

Evidence-based: tests 17 and 25 read from COM-scan audit 20 and cell-evidence
audit 17, not from manually updated summary files.

DO NOT stage or commit this file automatically.
"""

import json
import os
import pathlib
import pytest

# ── Paths ─────────────────────────────────────────────────────────────────────
DELIVERY = pathlib.Path(
    r"C:\Users\Lenovo\Desktop\expert_smart1 - Copy"
    r"\core_engine\instance\manual_review_outputs"
    r"\FINAL_PROFESSIONAL_VALUATION_DELIVERY"
)
ACTUAL = DELIVERY / "actual_files"
AUDITS = DELIVERY / "post_commit_visual_acceptance" / "audits"
EXCEL_VISUALS = DELIVERY / "post_commit_visual_acceptance" / "excel_visuals"
PDF_VISUALS = DELIVERY / "post_commit_visual_acceptance" / "pdf_visuals"
VISUAL_INDEX = DELIVERY / "post_commit_visual_acceptance" / "visual_index"


# ── Fixtures ───────────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def git_state():
    return json.loads((AUDITS / "01_post_commit_state.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def artifact_identity():
    return json.loads((AUDITS / "02_final_artifact_identity.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def excel_render():
    return json.loads((AUDITS / "03_excel_com_render.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def excel_visual():
    return json.loads((AUDITS / "04_excel_visual_results.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def pdf_render():
    return json.loads((AUDITS / "05_pdf_page_render.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def pdf_visual():
    return json.loads((AUDITS / "06_pdf_visual_results.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def defects():
    return json.loads((AUDITS / "07_visual_defects.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def hash_integrity():
    return json.loads((AUDITS / "08_post_render_hash_integrity.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def com_render_evidence():
    """Audit 19 — fresh full COM render of all 55 sheets (evidence-based)."""
    return json.loads((AUDITS / "19_evidence_based_excel_com_render.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def excel_visual_evidence():
    """Audit 20 — COM CalculateFullRebuild cell scan of all 55 sheets (evidence-based)."""
    return json.loads((AUDITS / "20_evidence_based_excel_visual_results.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def cell_evidence():
    """Audit 17 — per-cell COM inspection of sheets 9, 12, and 34."""
    return json.loads((AUDITS / "17_affected_sheet_cell_evidence.json").read_text(encoding="utf-8-sig"))


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 1 — Repository State (Tests 1–6)
# ══════════════════════════════════════════════════════════════════════════════

def test_01_branch_is_correct(git_state):
    assert git_state["branch"] == "feature/requirements-checklist-ui"


def test_02_head_matches_expected(git_state):
    assert git_state["final_head"] == "76e9824af59eb74396628c9c10f5e6b0d3fc7fee"
    assert git_state["head_confirmed"] is True


def test_03_six_commits_created(git_state):
    assert git_state["total_commits_created"] == 6
    assert len(git_state["commits"]) == 6


def test_04_218_paths_committed(git_state):
    assert git_state["total_paths_committed"] == 218
    assert git_state["unexpected_paths"] == 0


def test_05_no_push_executed(git_state):
    assert git_state["push_executed"] is False


def test_06_index_is_empty(git_state):
    assert git_state["index_empty"] is True
    assert git_state["staged_file_count"] == 0
    assert git_state["modified_tracked_files"] == 0


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 2 — Artifact Identity (Tests 7–11)
# ══════════════════════════════════════════════════════════════════════════════

def test_07_excel_artifact_exists_55_sheets(artifact_identity):
    art = artifact_identity["artifacts"]["excel"]
    assert art["sheets"] == 55
    assert art["sheets_match"] is True
    assert (ACTUAL / "01_FINAL_PRODUCTION_EXCEL_55_SHEETS.xlsx").exists()


def test_08_traditional_pdf_16_pages(artifact_identity):
    art = artifact_identity["artifacts"]["traditional"]
    assert art["pages"] == 16
    assert art["pages_match"] is True
    assert (ACTUAL / "02_FINAL_TRADITIONAL_REPORT.pdf").exists()


def test_09_detailed_pdf_18_pages(artifact_identity):
    art = artifact_identity["artifacts"]["detailed"]
    assert art["pages"] == 18
    assert art["pages_match"] is True
    assert (ACTUAL / "03_FINAL_DETAILED_REPORT.pdf").exists()


def test_10_professional_pdf_28_pages(artifact_identity):
    art = artifact_identity["artifacts"]["professional"]
    assert art["pages"] == 28
    assert art["pages_match"] is True
    assert (ACTUAL / "04_FINAL_PROFESSIONAL_REPORT.pdf").exists()


def test_11_excel_baseline_hash_recorded(artifact_identity):
    sha = artifact_identity["artifacts"]["excel"]["sha256"]
    assert len(sha) == 64
    # SHA of canonical Excel from FINAL_PRE_PUSH_EXCEL_PDF_VISUAL_ACCEPTANCE
    assert sha == "96030ffd963506538b7727883b3bfdbd418c6ccc5d1e781aa7774236028dc31b"


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 3 — Post-Render Hash Integrity (Tests 12–13)
# ══════════════════════════════════════════════════════════════════════════════

def test_12_all_four_hashes_unchanged(hash_integrity):
    assert hash_integrity["summary"]["hashes_unchanged"] == 4
    assert hash_integrity["summary"]["hashes_changed"] == 0
    assert hash_integrity["summary"]["all_artifacts_intact"] is True


def test_13_hash_integrity_status_pass(hash_integrity):
    assert hash_integrity["status"] == "PASS"
    for art in hash_integrity["artifacts"]:
        assert art["hash_unchanged"] is True, f"Hash changed for {art['file']}"
        assert art["size_unchanged"] is True


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 4 — Excel COM Rendering (Tests 14–16)
# ══════════════════════════════════════════════════════════════════════════════

def test_14_excel_55_sheets_rendered(excel_render):
    assert excel_render["rendered_sheets"] == 55
    assert excel_render["expected_sheet_count"] == 55
    assert excel_render["render_complete"] is True


def test_15_excel_334_pngs_generated(excel_render):
    assert excel_render["total_png_count"] == 334


def test_16_no_orphan_excel_processes(excel_render):
    assert excel_render["orphan_excel_processes"] == 0
    assert excel_render["excel_sha_unchanged"] is True


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 5 — Excel Visual Inspection (Tests 17–18)
# ══════════════════════════════════════════════════════════════════════════════

def test_17_excel_zero_failed_sheets_after_defect_closure(excel_visual_evidence):
    """Reads from COM CalculateFullRebuild cell scan (audit 20) — not a manually updated summary."""
    ev = excel_visual_evidence
    # Derived from COM scan; fails if audit 20 reports any failed sheets
    assert ev["failed_count"] == 0, f"COM scan found {ev['failed_count']} failed sheets"
    # COM scan must find zero formula-error cells across all 55 sheets
    assert ev["total_formula_error_cells"] == 0, (
        f"COM scan found {ev['total_formula_error_cells']} formula-error cells"
    )
    # Count integrity: PASS + WARNING + FAILED must equal total_sheets
    total = ev["pass_count"] + ev["warning_count"] + ev["failed_count"]
    assert total == ev["total_sheets"] == 55, (
        f"Sheet count mismatch: {total} != 55 (pass={ev['pass_count']} warn={ev['warning_count']} fail={ev['failed_count']})"
    )
    # No FAILED status in per-sheet list
    failed_indices = {s["index"] for s in ev["sheets"] if s["status"] == "FAILED"}
    assert failed_indices == set(), f"Unexpected FAILED sheets in COM scan: {failed_indices}"
    # Sheets 9, 12, 34 must have zero error cells individually
    affected = {9, 12, 34}
    for s in ev["sheets"]:
        if s["index"] in affected:
            assert s["error_cells"] == 0, (
                f"Sheet {s['index']} still has {s['error_cells']} formula-error cells after fix"
            )


def test_18_excel_global_governance_checks(excel_visual):
    g = excel_visual["global_checks"]
    assert g["no_fake_signature"] is True
    assert g["no_auto_certification"] is True
    assert g["no_advisory_only_true_python_literal"] is True
    assert g["no_fake_stamp"] is True
    assert g["signature_gate_visible"] is True
    assert g["certification_blocked"] is True


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 6 — PDF Page Rendering (Test 19)
# ══════════════════════════════════════════════════════════════════════════════

def test_19_62_pdf_pages_rendered(pdf_render):
    assert pdf_render["totals"]["rendered_pages"] == 62
    assert pdf_render["totals"]["pages_match"] is True
    assert pdf_render["totals"]["missing_pngs"] == 0
    assert pdf_render["status"] == "PASS"


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 7 — PDF Visual Inspection (Tests 20–22)
# ══════════════════════════════════════════════════════════════════════════════

def test_20_pdf_no_failed_pages(pdf_visual):
    for report_key, report in pdf_visual["reports"].items():
        assert report["failed_count"] == 0, (
            f"PDF '{report_key}' has {report['failed_count']} failed pages"
        )


def test_21_pdf_global_no_fake_signature(pdf_visual):
    g = pdf_visual["global_checks"]
    assert g["no_fake_signature"] is True
    assert g["no_auto_certification"] is True
    assert g["no_advisory_only_true_python_literal"] is True
    assert g["no_fake_stamp"] is True


def test_22_pdf_watermark_and_arabic_on_all_inspected_pages(pdf_visual):
    g = pdf_visual["global_checks"]
    assert g["watermark_on_every_inspected_page"] is True
    assert g["arabic_shaping_correct"] is True
    assert g["rtl_layout_correct"] is True


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 8 — Defect Classification (Test 23)
# ══════════════════════════════════════════════════════════════════════════════

def test_23_zero_critical_and_major_defects(defects):
    assert defects["defect_counts"]["critical"] == 0
    assert defects["defect_counts"]["major"] == 0
    assert len(defects["critical_defects"]) == 0
    assert len(defects["major_defects"]) == 0
    assert defects["delivery_recommendation"] == "ACCEPTED"
    closure = defects["major_defects_closure"]
    resolved_ids = {r["id"] for r in closure["resolved"]}
    assert resolved_ids == {"MAJ-01", "MAJ-02", "MAJ-03"}
    assert all(r["status"] == "CLOSED" for r in closure["resolved"])


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 9 — HTML Index + Release Tests (Tests 24)
# ══════════════════════════════════════════════════════════════════════════════

def test_24_visual_index_html_exists_and_release_tests_passed(git_state):
    html_path = (
        DELIVERY / "post_commit_visual_acceptance"
        / "visual_index" / "OPEN_POST_COMMIT_VISUAL_ACCEPTANCE.html"
    )
    assert html_path.exists(), f"Visual index HTML not found at {html_path}"
    # Release tests — 132/132 passed; 0 failed; 0 skipped.
    # SHA-based skip replaced with physical content check (TestTraditionalRegression).
    rt = git_state["release_tests"]
    assert rt["passed"] == 132
    assert rt["failed"] == 0
    assert rt["skipped"] == 0
    assert rt["total"] == 132


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 10 — Evidence Chain Consistency (Test 25)
# ══════════════════════════════════════════════════════════════════════════════

def test_25_evidence_chain_consistency(
    com_render_evidence, excel_visual_evidence, cell_evidence, defects, artifact_identity
):
    """
    Cross-audit consistency: workbook binary → COM render → cell scan → defect audit.
    Fails if any link in the chain contradicts another.
    """
    # 1. COM render was clean: all 55 sheets rendered, no errors, SHA unchanged
    assert com_render_evidence["sheets_rendered"] == 55, (
        f"COM render only rendered {com_render_evidence['sheets_rendered']}/55 sheets"
    )
    assert com_render_evidence["render_errors"] == 0, (
        f"COM render had {com_render_evidence['render_errors']} errors"
    )
    assert com_render_evidence["sha_unchanged"] is True, (
        "COM render modified the workbook (read-only open should never change SHA)"
    )

    # 2. Cell scan found zero errors, 55 sheets accounted for
    ev = excel_visual_evidence
    assert ev["total_formula_error_cells"] == 0
    assert ev["failed_count"] == 0
    assert ev["pass_count"] + ev["warning_count"] + ev["failed_count"] == 55

    # 3. Per-sheet cell evidence: all 3 affected sheets clean
    assert cell_evidence["totals"]["total_error_cells_after_recalculation"] == 0
    assert cell_evidence["totals"]["all_three_defects_closed"] is True

    # 4. Defect audit agrees with cell scan
    assert defects["defect_counts"]["major"] == 0
    assert defects["delivery_recommendation"] == "ACCEPTED"

    # 5. SHA cross-check: artifact_identity, COM render, and cell scan all name same SHA
    art_sha = artifact_identity["artifacts"]["excel"]["sha256"]
    render_sha = com_render_evidence["sha_after"]
    visual_sha = ev["sha256"]
    assert art_sha == render_sha == visual_sha, (
        f"SHA inconsistency: artifact={art_sha[:12]} render={render_sha[:12]} visual={visual_sha[:12]}"
    )
