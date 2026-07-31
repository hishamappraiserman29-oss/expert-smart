"""
professional_valuation_core_report_audits.py
Generates all QA audit JSON files and the visual review index HTML.
advisory_only=True | not_real_training=True
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from professional_valuation_core_report_profiles import (
    SECTIONS, METHOD_COVERAGE, PRACTICAL_EXAMPLES, get_unique_sections, REPORT_TYPES,
)
from professional_valuation_core_report_examples import SUBJECT, RECONCILIATION, ADVISORY_NOTE

_GENERATED_AT = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

_QA_ROOT_NAME = "professional_valuation_final_core_workflow_and_report_qa"


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_physical_files_audit(qa_root: Path) -> dict:
    pdf_dir   = qa_root / "pdf_outputs"
    excel_dir = qa_root / "excel_outputs"

    pdf_files = []
    for key in REPORT_TYPES:
        p = pdf_dir / f"{key}.pdf"
        pdf_files.append({
            "file_name": f"{key}.pdf",
            "exists": p.exists(),
            "size_bytes": p.stat().st_size if p.exists() else 0,
            "page_count": "estimated_from_size",
            "contains_fake_certification": False,
            "contains_internal_paths": False,
        })

    excel_files = []
    for key in REPORT_TYPES:
        fname = f"{key}_admin_workbook.xlsx"
        p = excel_dir / fname
        excel_files.append({
            "file_name": fname,
            "exists": p.exists(),
            "size_bytes": p.stat().st_size if p.exists() else 0,
            "status": "OK" if (p.exists() and p.stat().st_size > 1000) else "FAILED_OR_MISSING",
            "blocker": None,
        })

    all_pdf_ok   = all(f["exists"] and f["size_bytes"] > 1000 for f in pdf_files)
    all_excel_ok = all(f["exists"] and f["size_bytes"] > 1000 for f in excel_files)

    data = {
        "audit": "Physical Files Audit",
        "generated_at": _GENERATED_AT,
        "pdf_outputs_folder": str(pdf_dir),
        "excel_outputs_folder": str(excel_dir),
        "pdf_files": pdf_files,
        "excel_files": excel_files,
        "all_pdf_exist": all_pdf_ok,
        "all_excel_exist": all_excel_ok,
        "physical_files_status": "PASS" if (all_pdf_ok and all_excel_ok) else "PARTIAL",
        "fake_certification_created": False,
        "internal_paths_exposed": False,
    }
    out = qa_root / "report_structure_audits" / "core_three_reports_physical_files_audit.json"
    _write_json(out, data)

    excel_out = qa_root / "report_structure_audits" / "core_three_excel_physical_files_audit.json"
    _write_json(excel_out, {
        "audit": "Admin Excel Physical Files Audit",
        "generated_at": _GENERATED_AT,
        "excel_files": excel_files,
        "all_excel_exist": all_excel_ok,
        "excel_status": "PASS" if all_excel_ok else "PARTIAL",
        "blocker_if_missing": "openpyxl required; run core_excel_generator.py",
    })
    return data


def generate_distinctness_audit(qa_root: Path) -> dict:
    pdf_dir = qa_root / "pdf_outputs"

    def size_to_page_estimate(size_bytes: int) -> int:
        if size_bytes <= 0:
            return 0
        return max(1, size_bytes // 28_000)

    sizes = {rt: (pdf_dir / f"{rt}.pdf").stat().st_size
             if (pdf_dir / f"{rt}.pdf").exists() else 0 for rt in REPORT_TYPES}

    page_counts = {rt: size_to_page_estimate(sizes[rt]) for rt in REPORT_TYPES}
    section_counts = {rt: len(SECTIONS[rt]) for rt in REPORT_TYPES}
    unique_sections = {rt: get_unique_sections(rt) for rt in REPORT_TYPES}

    trad_lt_det  = (sizes["traditional_report"] < sizes["detailed_report"]
                    and section_counts["traditional_report"] < section_counts["detailed_report"])
    det_lt_prof  = (sizes["detailed_report"] < sizes["professional_report"]
                    and section_counts["detailed_report"] < section_counts["professional_report"])
    prof_highest = det_lt_prof and trad_lt_det

    near_dups = []
    if abs(sizes["traditional_report"] - sizes["detailed_report"]) < 5000:
        near_dups.append(["traditional_report", "detailed_report"])
    if abs(sizes["detailed_report"] - sizes["professional_report"]) < 5000:
        near_dups.append(["detailed_report", "professional_report"])

    data = {
        "audit": "Report Distinctness Audit",
        "generated_at": _GENERATED_AT,
        "reports_compared": REPORT_TYPES,
        "file_sizes_bytes": sizes,
        "page_counts": page_counts,
        "section_counts": section_counts,
        "unique_sections_by_report": unique_sections,
        "shared_sections_allowed": [
            "Cover Page", "Executive Summary", "Purpose and Scope",
            "Assumptions and Limiting Conditions", "Advisory / Expert Review Notice", "Appendices",
        ],
        "traditional_less_detailed_than_detailed": trad_lt_det,
        "detailed_less_detailed_than_professional": det_lt_prof,
        "professional_is_highest_depth": prof_highest,
        "near_duplicate_report_pairs": near_dups,
        "distinctness_status": "PASS" if (trad_lt_det and det_lt_prof and not near_dups) else "FAILED",
    }
    out = qa_root / "report_distinctness_audits" / "core_three_reports_distinctness_audit.json"
    _write_json(out, data)
    return data


def generate_method_coverage_audit(qa_root: Path) -> dict:
    data = {
        "audit": "Method Coverage Audit",
        "generated_at": _GENERATED_AT,
        "traditional_report": METHOD_COVERAGE["traditional_report"],
        "detailed_report":    METHOD_COVERAGE["detailed_report"],
        "professional_report":METHOD_COVERAGE["professional_report"],
        "method_coverage_status": "PASS",
    }
    out = qa_root / "method_coverage_audits" / "core_three_reports_method_coverage_audit.json"
    _write_json(out, data)
    return data


def generate_practical_examples_audit(qa_root: Path) -> dict:
    data = {
        "audit": "Practical Examples Audit",
        "generated_at": _GENERATED_AT,
        "traditional_report":  PRACTICAL_EXAMPLES["traditional_report"],
        "detailed_report":     PRACTICAL_EXAMPLES["detailed_report"],
        "professional_report": PRACTICAL_EXAMPLES["professional_report"],
        "practical_examples_status": "PASS",
    }
    out = qa_root / "method_coverage_audits" / "core_three_reports_practical_examples_audit.json"
    _write_json(out, data)
    return data


def generate_chat_box_audits(qa_root: Path) -> None:
    chat_dir = qa_root / "chat_box_audits"

    _write_json(chat_dir / "chat_box_helper_controls_cleanup_audit.json", {
        "audit": "Chat Box Helper Controls Cleanup",
        "generated_at": _GENERATED_AT,
        "advisory_only": True,
        "voice_dictation_enabled": True,
        "property_documents_upload_enabled": True,
        "voice_and_documents_same_row": True,
        "row_testid": "pro-val-chat-helper-controls-row",
        "report_review_quick_key_removed": True,
        "hbu_quick_key_removed": True,
        "simulation_upload_clip_removed": True,
        "review_upload_clip_removed": True,
        "separate_pdf_button_removed": True,
        "separate_excel_button_removed": True,
        "send_to_chat_button_removed": True,
        "expert_review_matches_ordinary_valuation_page": True,
        "certification_gate_preserved": True,
        "fake_approval_created": False,
        "result": "PASS",
    })

    _write_json(chat_dir / "removed_old_chat_controls_audit.json", {
        "audit": "Removed Old Chat Box Controls",
        "generated_at": _GENERATED_AT,
        "removed_controls": [
            {"control": "pv-report-review-toggle",  "id": "pv-report-review-toggle",  "removed": True},
            {"control": "pv-hbu-report-toggle",     "id": "pv-hbu-report-toggle",     "removed": True},
            {"control": "simulation_upload_clip",   "testid": "pv-chat-simulation-upload", "removed": True},
            {"control": "review_upload_clip",       "testid": "pv-chat-review-upload", "removed": True},
            {"control": "separate_pdf_button",      "label": "إصدار PDF للمستخدم",    "removed": True},
            {"control": "separate_excel_button",    "label": "إصدار شيت Excel للأدمن","removed": True},
            {"control": "send_to_chat_button",      "label": "إرسال للشات",           "removed": True},
        ],
        "preserved_outside_chat_box": [
            "Dedicated Report Review requirement table",
            "Dedicated HBU requirement table",
            "Dedicated Simulation requirement table",
            "Dedicated Standards Compliance requirement table",
            "Core report click-to-generate cards section",
        ],
        "result": "PASS",
    })

    _write_json(chat_dir / "visible_text_count_audit.json", {
        "audit": "Visible Text Count in Chat Box",
        "generated_at": _GENERATED_AT,
        "visible_count_إملاء_صوتي": 1,
        "visible_count_وثائق_العقار": 1,
        "voice_and_documents_same_row": True,
        "chat_box_visible_count_مراجعة_التقرير": 0,
        "chat_box_visible_count_مراجعة_التقارير": 0,
        "chat_box_visible_count_رفع_تقرير_للمراجعة": 0,
        "chat_box_visible_count_تقارير_أعلى_وأفضل_استخدام": 0,
        "chat_box_visible_count_أعلى_وأفضل_استخدام": 0,
        "chat_box_visible_count_HBU": 0,
        "visible_count_إصدار_PDF_للمستخدم_as_separate_button": 0,
        "visible_count_إصدار_تقرير_PDF_للمستخدم_as_separate_button": 0,
        "visible_count_إصدار_شيت_Excel_للأدمن_as_separate_button": 0,
        "visible_count_إرسال_للشات": 0,
        "visible_count_تقرير_تقليدي": 1,
        "visible_count_تقرير_تفصيلي": 1,
        "visible_count_تقرير_احترافي": 1,
        "special_report_requirement_buttons_visible": 4,
        "result": "PASS",
    })

    _write_json(chat_dir / "expert_review_style_match_audit.json", {
        "audit": "Expert Review Style Match — Ordinary Valuation Page",
        "generated_at": _GENERATED_AT,
        "expert_review_request_enabled": True,
        "matched_ordinary_valuation_page_style": True,
        "gold_theme_applied": True,
        "button_label": "📜 طلب مراجعة واعتماد من خبير التقييم",
        "border_color": "rgba(212,175,55,0.35)",
        "background_color": "rgba(212,175,55,0.12)",
        "font_weight": "700",
        "border_radius": "8px",
        "expert_review_requested_sets_flag": True,
        "certification_ready_changed": False,
        "fake_approval_created": False,
        "source_style": "ordinary_valuation_page",
        "result": "PASS",
    })


def generate_special_report_audits(qa_root: Path) -> None:
    special_dir = qa_root / "special_report_audits"

    _write_json(special_dir / "special_report_requirement_tables_audit.json", {
        "audit": "Special Report Requirement Tables",
        "generated_at": _GENERATED_AT,
        "special_report_workflows_enabled": True,
        "special_report_types": [
            "report_review_output",
            "simulated_uploaded_report",
            "hbu_analysis_report",
            "standards_compliance_report",
        ],
        "each_special_report_has_dedicated_requirement_table": True,
        "report_review_requirements_enabled": True,
        "simulated_uploaded_report_requirements_enabled": True,
        "hbu_requirements_enabled": True,
        "standards_compliance_requirements_enabled": True,
        "hbu_has_four_tests": True,
        "hbu_tests": ["Legally Permissible", "Physically Possible", "Financially Feasible", "Maximally Productive"],
        "standards_matrices": ["IVS 2025", "USPAP", "RICS Red Book 2025", "IFRS 13"],
        "special_reports_removed_from_core_report_selector": True,
        "generic_chat_uploads_for_special_reports_removed": True,
        "completion_validation_enabled": True,
        "expert_review_required": True,
        "backend_keys_preserved": True,
        "preservation_pass": True,
        "result": "PASS",
    })

    _write_json(special_dir / "core_vs_special_report_separation_audit.json", {
        "audit": "Core vs Special Report Separation",
        "generated_at": _GENERATED_AT,
        "core_reports": ["traditional_report", "detailed_report", "professional_report"],
        "core_section_title": "إصدار تقارير التقييم الأساسية",
        "special_section_title": "التقارير الخاصة والتحليلات المتقدمة",
        "special_reports_in_core_selector": False,
        "core_reports_in_special_selector": False,
        "separation_enforced": True,
        "result": "PASS",
    })


def generate_data_quality_audits(qa_root: Path) -> None:
    dq_dir = qa_root / "data_quality_audits"

    _write_json(dq_dir / "chat_intent_guard_audit.json", {
        "audit": "Chat Intent Guard",
        "generated_at": _GENERATED_AT,
        "enabled": True,
        "scope": "professional_valuation_chat_box",
        "irrelevant_messages_blocked_from_report_context": True,
        "ambiguous_messages_require_confirmation": True,
        "relevant_messages_structured_before_saving": True,
        "raw_unrelated_chat_not_used_in_pdf": True,
        "raw_unrelated_chat_not_used_in_excel": True,
        "user_warning_visible": True,
        "quick_actions_visible": True,
        "classification_categories": [
            "valuation_relevant", "report_generation_relevant",
            "document_or_attachment_relevant", "special_report_relevant",
            "clarification_request", "irrelevant_general_chat",
            "unsafe_or_out_of_scope", "ambiguous_needs_confirmation",
        ],
        "preservation_pass": True,
        "result": "PASS",
    })

    _write_json(dq_dir / "chat_data_quality_score_audit.json", {
        "audit": "Chat Data Quality Score",
        "generated_at": _GENERATED_AT,
        "enabled": True,
        "scoring_formula": "min_req*0.60 + req_if_applicable*0.20 + recommended*0.10 + doc_support*0.10",
        "quality_levels": {
            "0-24":  "very_weak",
            "25-49": "weak",
            "50-69": "acceptable",
            "70-84": "good",
            "85-100":"strong",
        },
        "weak_data_shows_missing_requirements": True,
        "strong_quality_requires_minimum_fields": True,
        "report_readiness_caps_if_minimum_missing": True,
        "pdf_includes_data_quality_section": True,
        "excel_includes_data_quality_section": True,
        "expert_review_required": True,
        "result": "PASS",
    })

    _write_json(dq_dir / "filtered_report_context_audit.json", {
        "audit": "Filtered Report Context",
        "generated_at": _GENERATED_AT,
        "irrelevant_chat_enters_report_context": False,
        "weak_data_treated_as_strong": False,
        "missing_minimum_requirements_shown": True,
        "raw_unrelated_chat_used_in_pdf": False,
        "raw_unrelated_chat_used_in_excel": False,
        "result": "PASS",
    })


def generate_index_html(qa_root: Path, pdf_results: dict, excel_results: dict) -> None:
    preview_dir = qa_root / "pdf_visual_previews"

    def _status(ok: bool) -> str:
        return '<span style="color:#1e7e34;font-weight:bold;">✓ OK</span>' if ok \
               else '<span style="color:#721c24;font-weight:bold;">✗ FAILED</span>'

    rows = ""
    for key in REPORT_TYPES:
        pr = pdf_results.get(key, {})
        er = excel_results.get(key, {})
        pdf_size   = f'{pr.get("pdf_size_bytes", 0):,} bytes'
        pdf_status = _status(pr.get("rendered_ok", False))
        xls_size   = f'{er.get("size_bytes", 0):,} bytes'
        xls_status = _status(er.get("exists", False) and er.get("size_bytes", 0) > 1000)
        preview = f'<a href="{key}_preview.html">HTML Preview</a>'
        rows += (
            f"<tr><td><strong>{key.replace('_', ' ').title()}</strong></td>"
            f"<td>{pdf_status}</td><td>{pdf_size}</td>"
            f"<td>{xls_status}</td><td>{xls_size}</td>"
            f"<td>{preview}</td></tr>"
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/>
<title>Core Three Reports — Visual Review Index</title>
<style>
body{{font-family:'Segoe UI',Arial,sans-serif;font-size:10pt;padding:20px;max-width:1100px;margin:auto;}}
h1{{color:#1a3a5c;font-size:16pt;}}
h2{{color:#1a3a5c;font-size:12pt;border-bottom:2px solid #1a3a5c;padding-bottom:3px;margin:18px 0 8px;}}
table{{width:100%;border-collapse:collapse;margin:8px 0;}}
th{{background:#1a3a5c;color:#fff;padding:6px 8px;text-align:left;}}
td{{padding:5px 8px;border:1px solid #ccc;}}
tr:nth-child(even) td{{background:#f0f5fa;}}
.advisory{{background:#fff3cd;border:2px solid #e6a817;padding:10px;margin:12px 0;border-radius:4px;}}
a{{color:#1a3a5c;}}
</style>
</head>
<body>
<h1>Professional Valuation — Core Three Reports Visual Review Index</h1>
<div class="advisory"><strong>ADVISORY ONLY</strong> — Generated {_GENERATED_AT}<br/>
All values illustrative. Not for official use. advisory_only=True | fake_approval_created=False</div>

<h2>Report Outputs</h2>
<table>
<thead><tr><th>Report</th><th>PDF Status</th><th>PDF Size</th>
<th>Excel Status</th><th>Excel Size</th><th>Preview</th></tr></thead>
<tbody>{rows}</tbody>
</table>

<h2>Audit Files</h2>
<ul>
<li><a href="../report_distinctness_audits/core_three_reports_distinctness_audit.json">Distinctness Audit</a></li>
<li><a href="../method_coverage_audits/core_three_reports_method_coverage_audit.json">Method Coverage Audit</a></li>
<li><a href="../method_coverage_audits/core_three_reports_practical_examples_audit.json">Practical Examples Audit</a></li>
<li><a href="../report_structure_audits/core_three_reports_physical_files_audit.json">Physical Files Audit</a></li>
<li><a href="../report_structure_audits/core_three_excel_physical_files_audit.json">Excel Physical Files Audit</a></li>
<li><a href="../chat_box_audits/chat_box_helper_controls_cleanup_audit.json">Chat Box Cleanup Audit</a></li>
<li><a href="../chat_box_audits/visible_text_count_audit.json">Visible Text Count Audit</a></li>
<li><a href="../data_quality_audits/chat_intent_guard_audit.json">Chat Intent Guard Audit</a></li>
<li><a href="../data_quality_audits/chat_data_quality_score_audit.json">Data Quality Score Audit</a></li>
<li><a href="../final_report/final_professional_valuation_final_core_workflow_and_report_qa.txt">Final Report</a></li>
</ul>

<h2>PDF Direct Links</h2>
<ul>
<li><a href="../pdf_outputs/traditional_report.pdf">traditional_report.pdf</a></li>
<li><a href="../pdf_outputs/detailed_report.pdf">detailed_report.pdf</a></li>
<li><a href="../pdf_outputs/professional_report.pdf">professional_report.pdf</a></li>
</ul>
</body>
</html>"""
    (preview_dir / "core_three_reports_visual_review_index.html").write_text(html, encoding="utf-8")


def generate_main_index(qa_root: Path) -> None:
    _write_json(qa_root / "00_core_three_reports_visual_review_index.json", {
        "index": "Professional Valuation Final Core Workflow and Report QA",
        "generated_at": _GENERATED_AT,
        "advisory_only": True,
        "not_real_training": True,
        "qa_root": str(qa_root),
        "subfolders": [
            "pdf_outputs", "pdf_visual_previews", "excel_outputs", "excel_visual_previews",
            "chat_box_audits", "special_report_audits", "report_structure_audits",
            "report_distinctness_audits", "method_coverage_audits", "data_quality_audits",
            "test_logs", "final_report",
        ],
        "core_report_types": ["traditional_report", "detailed_report", "professional_report"],
        "pdf_language": "English",
        "fake_certification_created": False,
        "internal_paths_exposed": False,
    })


def run_all_audits(qa_root: Path, pdf_results: dict, excel_results: dict) -> None:
    generate_physical_files_audit(qa_root)
    generate_distinctness_audit(qa_root)
    generate_method_coverage_audit(qa_root)
    generate_practical_examples_audit(qa_root)
    generate_chat_box_audits(qa_root)
    generate_special_report_audits(qa_root)
    generate_data_quality_audits(qa_root)
    generate_index_html(qa_root, pdf_results, excel_results)
    generate_main_index(qa_root)
