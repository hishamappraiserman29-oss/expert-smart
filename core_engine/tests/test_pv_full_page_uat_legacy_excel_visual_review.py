# test_pv_full_page_uat_legacy_excel_visual_review.py
# Part M — Backend tests for Full Page UAT & Legacy Excel Visual Review
# advisory_only=True | not_real_training=True | no_commit=True

import json
import pathlib
import ast
import pytest

QA = pathlib.Path(
    "core_engine/instance/manual_review_outputs/"
    "professional_valuation_full_page_uat_legacy_excel_visual_review"
)
REFS   = QA / "legacy_references"
INV    = QA / "legacy_inventory"
PREV   = QA / "excel_visual_previews"
SEC2   = QA / "section2_asset_requirements"
SEC3   = QA / "section3_scope_purpose"
SEC4   = QA / "section4_standards"
CHAT   = QA / "chat_box_outputs"
PDF    = QA / "pdf_outputs"
EXCEL  = QA / "excel_comparison_audits"
VR     = QA / "visual_review"
TLOGS  = QA / "test_logs"
FINAL  = QA / "final_report"

HTML   = pathlib.Path("frontend/index.html")
BRIDGE = pathlib.Path("core_engine/bridge_api.py")


# ── UAT-B01: QA output folder exists ──────────────────────────────────────────
def test_UAT_B01_qa_output_folder_exists():
    assert QA.exists(), f"QA folder missing: {QA}"


# ── UAT-B02: Both legacy Excel references found ───────────────────────────────
def test_UAT_B02_both_legacy_excel_references_found():
    gf   = REFS / "Report_ES_GRAND_FINAL_v4.xlsm"
    ultra= REFS / "Report_ES_ULTRA.xlsm"
    assert gf.exists(),    f"GRAND_FINAL_v4 not found: {gf}"
    assert ultra.exists(), f"ULTRA not found: {ultra}"
    assert gf.stat().st_size   > 100_000, "GRAND_FINAL_v4 suspiciously small"
    assert ultra.stat().st_size > 50_000, "ULTRA suspiciously small"


# ── UAT-B03: Legacy Excel inventories generated ───────────────────────────────
def test_UAT_B03_legacy_excel_inventories_generated():
    gf_inv   = INV / "Report_ES_GRAND_FINAL_v4_inventory.json"
    ul_inv   = INV / "Report_ES_ULTRA_inventory.json"
    summary  = INV / "legacy_excel_comparison_summary.json"
    gf_names = INV / "Report_ES_GRAND_FINAL_v4_sheet_names.txt"
    ul_names = INV / "Report_ES_ULTRA_sheet_names.txt"
    for p in [gf_inv, ul_inv, summary, gf_names, ul_names]:
        assert p.exists(), f"Inventory file missing: {p}"

    gf_data = json.loads(gf_inv.read_text(encoding="utf-8"))
    assert gf_data["workbook_found"] is True
    assert gf_data["sheet_count"] >= 40, "Expected 44 sheets in GRAND_FINAL_v4"

    ul_data = json.loads(ul_inv.read_text(encoding="utf-8"))
    assert ul_data["workbook_found"] is True
    assert ul_data["sheet_count"] >= 24, "Expected 26 sheets in ULTRA"


# ── UAT-B04: Legacy visual previews generated ─────────────────────────────────
def test_UAT_B04_legacy_visual_previews_generated():
    previews = [
        PREV / "legacy_grand_final_index_preview.html",
        PREV / "legacy_ultra_index_preview.html",
        PREV / "generated_vs_legacy_side_by_side_summary.html",
    ]
    for p in previews:
        assert p.exists(), f"Preview missing: {p}"
        content = p.read_text(encoding="utf-8")
        assert len(content) > 500, f"Preview too short: {p}"


# ── UAT-B05: Section 2 audit generated ───────────────────────────────────────
def test_UAT_B05_section2_audit_generated():
    audit = SEC2 / "section2_asset_requirements_audit.json"
    assert audit.exists()
    data = json.loads(audit.read_text(encoding="utf-8"))
    assert data["validation_result"] == "PASS"
    assert len(data["common_assets_validated"]) >= 8
    assert data["no_internal_paths_in_dom"] is True


# ── UAT-B06: Section 3 audit generated ───────────────────────────────────────
def test_UAT_B06_section3_audit_generated():
    audit = SEC3 / "section3_purpose_scope_audit.json"
    assert audit.exists()
    data = json.loads(audit.read_text(encoding="utf-8"))
    assert data["validation_result"] == "PASS"
    assert data["main_purpose_label_visible"] is True
    assert data["duplicate_purpose_logical_path_visible"] is False
    assert data["duplicate_professional_purpose_path_visible"] is False


# ── UAT-B07: Section 4 audit generated ───────────────────────────────────────
def test_UAT_B07_section4_audit_generated():
    audit = SEC4 / "section4_standards_layout_audit.json"
    assert audit.exists()
    data = json.loads(audit.read_text(encoding="utf-8"))
    assert data["validation_result"] == "PASS"
    assert data["layout"] == "horizontal_compact_chips"
    assert data["old_vertical_blocks_removed"] is True
    standards = data["standards_preserved"]
    for std in ["USPAP", "IVS 2025", "RICS Red Book 2025", "IFRS 13", "Basel III"]:
        assert std in standards, f"Standard missing: {std}"


# ── UAT-B08: Chat Box audit generated ────────────────────────────────────────
def test_UAT_B08_chat_box_audit_generated():
    audit = CHAT / "chat_box_report_controls_audit.json"
    assert audit.exists()
    data = json.loads(audit.read_text(encoding="utf-8"))
    assert data["validation_result"] == "PASS"
    assert data["unified_label_visible_once"] is True
    assert data["visible_report_types_count"] == 7
    assert data["duplicate_pdf_button_visible"] is False
    assert data["duplicate_chat_key_button_visible"] is False


# ── UAT-B09: PDF output audit generated ──────────────────────────────────────
def test_UAT_B09_pdf_output_audit_generated():
    audit = PDF / "pdf_visual_quality_audit.json"
    assert audit.exists()
    data = json.loads(audit.read_text(encoding="utf-8"))
    assert data["no_fake_stamp_signature"] is True
    assert data["advisory_unless_certification_ready"] is True
    assert data["no_internal_paths"] is True


# ── UAT-B10: Excel output comparison audit generated ─────────────────────────
def test_UAT_B10_excel_comparison_audit_generated():
    audit = EXCEL / "generated_vs_legacy_excel_quality_gap_analysis.json"
    assert audit.exists()
    data = json.loads(audit.read_text(encoding="utf-8"))
    assert data["legacy_references_used"] is True
    assert "Report_ES_GRAND_FINAL_v4.xlsm" in data["legacy_files"]
    assert "Report_ES_ULTRA.xlsm" in data["legacy_files"]
    assert len(data["critical_gaps"]) > 0, "Critical gaps must be documented"
    assert len(data["recommended_next_fixes"]) > 0


# ── UAT-B11: No old requirements deleted from HTML ───────────────────────────
def test_UAT_B11_no_old_requirements_deleted():
    html = HTML.read_text(encoding="utf-8")
    # Core requirement identifiers must remain
    assert "pro-val-asset-type-select"            in html
    assert "pro-val-special-asset-requirements-panel" in html
    assert "pro-val-requirements-group-descriptive" in html
    assert "pro-val-requirements-group-physical"    in html
    assert "متطلبات تقييم"                         in html


# ── UAT-B12: No old options deleted from HTML ────────────────────────────────
def test_UAT_B12_no_old_options_deleted():
    html = HTML.read_text(encoding="utf-8")
    # Core asset options
    assert "وحدة سكنية"          in html
    assert "أرض فضاء"            in html
    assert "محل تجاري"           in html
    assert "فنادق ومنتجعات"      in html
    # Section 3 options
    assert "الغرض الرئيسي للتقييم" in html
    assert "المسار المهني"          in html
    # Section 4 standards
    assert "USPAP"                in html
    assert "IVS 2025"             in html
    assert "Basel III"            in html
    # Chat box 7 report types
    assert "traditional_report"           in html
    assert "detailed_report"              in html
    assert "professional_report"          in html
    assert "hbu_analysis_report"          in html
    assert "standards_compliance_report"  in html


# ── UAT-B13: No internal paths in HTML ───────────────────────────────────────
def test_UAT_B13_no_internal_paths_in_html():
    html = HTML.read_text(encoding="utf-8")
    forbidden = [
        r"C:\\Users\\",
        r"C:/Users/",
        "/home/",
        "AppData",
        "Desktop",
        "__file__",
    ]
    for pat in forbidden:
        assert pat not in html, f"Internal path found in HTML: {pat}"


# ── UAT-B14: No fake certification in HTML ───────────────────────────────────
def test_UAT_B14_no_fake_certification():
    html = HTML.read_text(encoding="utf-8")
    assert "advisory_only"    in html
    assert "not_real_training" in html
    fake_phrases = [
        "شهادة معتمدة نهائية",
        "certified_final_valuation",
        "FINAL_CERTIFIED",
    ]
    for phrase in fake_phrases:
        assert phrase not in html, f"Fake certification phrase found: {phrase}"


# ── UAT-B15: Ordinary valuation unaffected ───────────────────────────────────
def test_UAT_B15_ordinary_valuation_unaffected():
    html = HTML.read_text(encoding="utf-8")
    assert "simple-valuation"   in html or "simple_valuation" in html
    assert "composite-valuation" in html or "تقييم مبسط"    in html or "ordinary" in html.lower()


# ── UAT-B16: Tax appeal unaffected ───────────────────────────────────────────
def test_UAT_B16_tax_appeal_unaffected():
    html = HTML.read_text(encoding="utf-8")
    assert "tax-appeal"       in html or "tax_appeal"    in html
    assert "الاعتراض الضريبي" in html or "tax appeal"    in html.lower()


# ── UAT-B17: bridge_api.py parses cleanly ────────────────────────────────────
def test_UAT_B17_bridge_api_parses():
    src = BRIDGE.read_text(encoding="utf-8")
    try:
        ast.parse(src)
    except SyntaxError as e:
        pytest.fail(f"bridge_api.py has syntax error: {e}")
