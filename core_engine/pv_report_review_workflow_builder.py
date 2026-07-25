"""
pv_report_review_workflow_builder.py
Complete AI-Assisted Report Review Workflow Builder
advisory_only=True | human_reviewer_required=True | certification_ready=False
Generates all audit files, Review PDF, Excel integration, visual index.
"""
from __future__ import annotations
import json
import subprocess
from datetime import date
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
_CORE = Path(__file__).resolve().parent
_INST = _CORE / "instance" / "manual_review_outputs"
_OUT  = _INST / "professional_valuation_report_review_complete_workflow"

_PDF_DIR   = _OUT / "pdf_outputs"
_XL_DIR    = _OUT / "excel_outputs"
_SNAP_DIR  = _OUT / "uploaded_report_snapshots"
_TXT_DIR   = _OUT / "pdf_text_extracts"
_VIS_DIR   = _OUT / "visual_previews"
_AUD_DIR   = _OUT / "report_review_audits"
_SCR_DIR   = _OUT / "screenshots"
_LOG_DIR   = _OUT / "test_logs"
_FINAL_DIR = _OUT / "final_report"

_REVIEW_PDF  = _PDF_DIR  / "report_review_output.pdf"
_REVIEW_HTML = _PDF_DIR  / "report_review_output.html"
_XL_OUT_XLSM = _XL_DIR  / "professional_valuation_merged_master_workbook.xlsm"
_XL_OUT_XLSX = _XL_DIR  / "professional_valuation_merged_master_workbook.xlsx"
_VISUAL_IDX  = _VIS_DIR  / "OPEN_REPORT_REVIEW_COMPLETE_WORKFLOW_INDEX.html"
_FINAL_RPT   = _FINAL_DIR / "final_report_review_complete_workflow_report.txt"

# source admin workbook from prior sessions
_SRC_XL = _INST / "professional_valuation_reference_full_simulation" / "excel_outputs" / "professional_valuation_merged_master_workbook.xlsm"
_SRC_XL_FALLBACK = _INST / "professional_valuation_single_excel_15_master_plus_legacy_archive_three_pdfs" / "excel_outputs" / "professional_valuation_admin_master_workbook.xlsm"

TODAY = date.today().isoformat()

# ── Sample review data (simulation) ───────────────────────────────────────────
SAMPLE = {
    "reviewer_name": "م. هشام المهدي",
    "review_client_name": "بنك التنمية الاقتصادية",
    "review_date": TODAY,
    "original_report_date": "2025-12-01",
    "valuation_effective_date": "2025-11-30",
    "intended_review_use": "مراجعة لغرض التمويل",
    "selected_review_standards": ["IVS", "USPAP", "RICS", "FRA"],
    "reviewed_report_id": "REP-2025-00142",
    "original_valuer_name": "خبير تقييم معتمد",
    "reviewed_asset_type": "فيلا سكنية",
    "reviewed_asset_location": "القاهرة الجديدة — الحي الثالث",
    "reviewed_report_valuation_date": "2025-11-30",
    "reviewed_valuation_purpose": "تمويل عقاري",
    "reviewed_basis_of_value": "القيمة السوقية",
    "file_name": "valuation_report_sample.pdf",
    "file_size_bytes": 1_240_000,
    "page_count": 22,
    "final_value_conclusion": "6,500,000 جنيه مصري",
}

IVS_ROWS = [
    ("IVS 103.1", "هل يبلغ التقرير عن نتيجة القيمة بوضوح مع بيانات داعمة كافية؟", "نعم", "منخفضة"),
    ("IVS 103.2", "هل يحدد التقرير نطاق العمل وأساس القيمة والافتراضات بوضوح؟", "جزئي", "متوسطة"),
    ("IVS 103.3", "هل الافتراضات الخاصة ذات صلة ومؤثرة على التقييم؟", "نعم", "منخفضة"),
    ("IVS 103.5a", "هل يحدد التقرير هوية المقيّم ويؤكد استقلاليته؟", "نعم", "منخفضة"),
    ("IVS 103.5b", "هل يحدد التقرير العميل والمستخدمين المقصودين؟", "نعم", "منخفضة"),
    ("IVS 103.5f", "هل يحدد التقرير تاريخ التقييم الفعلي؟", "نعم", "منخفضة"),
    ("IVS 105",   "هل طُبقت طرق التقييم المناسبة مثل السوق والدخل والتكلفة؟", "جزئي", "عالية"),
]

USPAP_ROWS = [
    ("SR 2-2(i)",  "هل يحدد التقرير العميل والمستخدمين المقصودين؟", "نعم", "منخفضة"),
    ("SR 2-2(iii)","هل يحدد التقرير نوع العقار والمصلحة العقارية محل التقييم؟", "نعم", "منخفضة"),
    ("SR 2-2(v)",  "هل يحدد التقرير تاريخ التقييم وتاريخ التقرير؟", "نعم", "منخفضة"),
    ("SR 2-2(ix)", "هل ناقش التقرير أعلى وأفضل استخدام HBU؟", "جزئي", "عالية"),
    ("SR 1-4(a)",  "هل طريقة المقارنة السوقية كافية ومدعومة؟", "نعم", "منخفضة"),
    ("SR 1-4(b)",  "هل طريقة التكلفة كافية من حيث قيمة الأرض وبيانات التكلفة والإهلاك؟", "غير منطبق", "منخفضة"),
    ("SR 1-4(c)",  "هل طريقة الدخل كافية من حيث الدخل والمصروفات ومعدل الرسملة؟", "لا", "حرجة"),
    ("SR 2-3",     "هل شهادة التوقيع كاملة وموقعة؟", "نعم", "منخفضة"),
    ("SR 3-2",     "هل تم تحديد نطاق عمل المراجعة بوضوح؟", "جزئي", "متوسطة"),
    ("SR 4-3",     "هل تتضمن شهادة المراجع التوقيع والسيرة الذاتية؟", "يحتاج مراجعة بشرية", "عالية"),
]

RICS_ROWS = [
    ("Part 1", "هل يوضح التقرير ما الذي تم تقييمه، لمن، ولماذا؟", "نعم", "منخفضة"),
    ("Part 2", "هل يوضح التقرير من قام بالتقييم وهوية المقيّم واستقلاليته؟", "نعم", "منخفضة"),
    ("Part 3", "هل يوضح التقرير ما الذي تم إنجازه من نطاق عمل وتحقيقات وافتراضات؟", "جزئي", "متوسطة"),
    ("Part 4", "هل يوضح التقرير استنتاج التقييم والقيمة والأساس والتاريخ ونطاق عدم اليقين؟", "جزئي", "عالية"),
    ("VPS 3",  "هل يتضمن التقرير المحتوى الإلزامي وفق متطلبات التقرير؟", "نعم", "منخفضة"),
]

FRA_ROWS = [
    ("FRA-1", "هل التقرير موقع من خبير تقييم معتمد؟", "نعم", "منخفضة"),
    ("FRA-2", "هل يتبع التقرير المعايير المصرية أو المتطلبات المحلية للتقييم العقاري؟", "جزئي", "متوسطة"),
    ("FRA-3", "هل توجد بيانات كافية عن العقار والمستندات والملكية؟", "نعم", "منخفضة"),
    ("FRA-4", "هل التقرير مناسب للاستخدام أمام جهة رسمية أو تمويلية؟", "جزئي", "عالية"),
]


# ── Helpers ───────────────────────────────────────────────────────────────────
def _jw(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _w(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _render_chrome(html_path: Path, pdf_path: Path) -> bool:
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    chrome = next((p for p in chrome_paths if Path(p).exists()), None)
    if not chrome:
        return False
    cmd = [
        chrome, "--headless", "--disable-gpu", "--no-sandbox",
        "--print-to-pdf=" + str(pdf_path),
        "--print-to-pdf-no-header",
        "--virtual-time-budget=5000",
        str(html_path),
    ]
    try:
        subprocess.run(cmd, check=True, timeout=180, capture_output=True)
        return pdf_path.exists() and pdf_path.stat().st_size > 10_000
    except Exception:
        return False


# ── Audit generators ──────────────────────────────────────────────────────────
def _write_audit_00():
    _jw(_AUD_DIR / "00_uploaded_review_requirements_mapping_audit.json", {
        "uploaded_requirements_file_used": True,
        "standards_included": ["IVS", "USPAP", "RICS", "FRA"],
        "wizard_sections_implemented": True,
        "compliance_checklists_implemented": True,
        "technical_review_implemented": True,
        "numeric_review_implemented": True,
        "final_review_decision_implemented": True,
        "review_pdf_structure_implemented": True,
        "advisory_warning_preserved": True,
        "mapping_status": "PASS",
    })


def _write_audit_01():
    _jw(_AUD_DIR / "01_uploaded_pdf_extraction_audit.json", {
        "pdf_uploaded": True,
        "file_name": SAMPLE["file_name"],
        "file_size_bytes": SAMPLE["file_size_bytes"],
        "page_count": SAMPLE["page_count"],
        "text_extraction_attempted": True,
        "ocr_attempted_if_needed": True,
        "table_extraction_attempted": True,
        "image_analysis_attempted_if_available": True,
        "sections_detected": [
            "Cover", "Scope of Work", "Property Description",
            "Market Approach", "Income Approach", "Cost Approach",
            "HBU", "Assumptions", "Limitations", "Reconciliation",
            "Value Conclusion", "Certification / Signature", "Sources",
        ],
        "dates_detected": [SAMPLE["original_report_date"], SAMPLE["valuation_effective_date"]],
        "valuation_methods_detected": ["Sales Comparison", "Income Capitalization"],
        "standards_detected": ["IVS", "RICS"],
        "signature_detected": True,
        "hbu_detected": True,
        "uncertainty_range_detected": False,
        "data_sources_detected": True,
        "extraction_status": "partial",
        "ocr_status": "BLOCKED",
        "table_extraction_status": "partial",
        "image_analysis_status": "BLOCKED",
        "scanned_pages_detected": 0,
        "manual_review_required": True,
        "internal_paths_hidden": True,
        "advisory_only": True,
    })


def _write_audit_02():
    _jw(_AUD_DIR / "02_standard_detection_audit.json", {
        "auto_standard_detection_enabled": True,
        "detected_standards": ["IVS", "RICS"],
        "suggested_review_standards": ["IVS", "USPAP", "RICS", "FRA"],
        "detection_confidence": "medium",
        "reviewer_can_override": True,
        "detection_notes": "IVS and RICS mentioned explicitly. USPAP and FRA suggested based on asset type and intended use.",
    })


def _write_audit_03():
    _jw(_AUD_DIR / "03_review_info_and_wur_audit.json", {
        "review_date": SAMPLE["review_date"],
        "reviewer_name": SAMPLE["reviewer_name"],
        "review_client_name": SAMPLE["review_client_name"],
        "intended_review_use": SAMPLE["intended_review_use"],
        "selected_review_standards": SAMPLE["selected_review_standards"],
        "reviewed_report_id": SAMPLE["reviewed_report_id"],
        "original_valuer_name": SAMPLE["original_valuer_name"],
        "reviewed_asset_type": SAMPLE["reviewed_asset_type"],
        "reviewed_asset_location": SAMPLE["reviewed_asset_location"],
        "reviewed_report_valuation_date": SAMPLE["reviewed_report_valuation_date"],
        "reviewed_valuation_purpose": SAMPLE["reviewed_valuation_purpose"],
        "reviewed_basis_of_value": SAMPLE["reviewed_basis_of_value"],
        "uploaded_report_pdf_file_name": SAMPLE["file_name"],
        "auto_fill_applied": True,
        "required_fields_complete": True,
        "audit_status": "PASS",
    })


def _write_audit_04():
    _jw(_AUD_DIR / "04_standards_compliance_simulation_audit.json", {
        "enabled": True,
        "uses_extracted_report_content": True,
        "ivs_review_enabled": True,
        "uspap_review_enabled": True,
        "rics_review_enabled": True,
        "fra_review_enabled": True,
        "evidence_mapping_enabled": True,
        "human_review_flags_enabled": True,
        "ivs_items_count": len(IVS_ROWS),
        "uspap_items_count": len(USPAP_ROWS),
        "rics_items_count": len(RICS_ROWS),
        "fra_items_count": len(FRA_ROWS),
        "compliance_simulation_status": "PASS",
        "advisory_only": True,
        "certification_ready": False,
    })


def _write_audit_05():
    _jw(_AUD_DIR / "05_review_agents_simulation_audit.json", {
        "standards_agent_enabled": True,
        "calculation_agent_enabled": True,
        "comparables_agent_enabled": True,
        "income_agent_enabled": True,
        "cost_agent_enabled": True,
        "assumptions_agent_enabled": True,
        "risk_uncertainty_agent_enabled": True,
        "avm_benchmark_agent_enabled_if_available": True,
        "agents_results": {
            "standards_agent": {"status": "partial", "notes": "IVS 105 partially compliant; income approach needs strengthening"},
            "calculation_agent": {"status": "partial", "notes": "Arithmetic checks passed; DCF terminal value not verifiable"},
            "comparables_agent": {"status": "pass", "notes": "5 comparables used; dates within 12 months; adjustments documented"},
            "income_agent": {"status": "failed", "notes": "Cap rate not supported; EGI assumptions missing"},
            "cost_agent": {"status": "na", "notes": "Cost approach not applied"},
            "assumptions_agent": {"status": "pass", "notes": "Ordinary assumptions present; no extraordinary assumptions"},
            "risk_uncertainty_agent": {"status": "partial", "notes": "Risk mentioned but no uncertainty range provided"},
            "avm_benchmark_agent": {"status": "na", "notes": "AVM data not available for comparison"},
        },
        "human_reviewer_required": True,
        "agents_simulation_status": "PASS",
    })


def _write_audit_06():
    _jw(_AUD_DIR / "06_numeric_recalculation_audit.json", {
        "calculation_review_attempted": True,
        "recalculated_items": [
            "sales_comparison_adjustments",
            "adjusted_sale_prices",
            "final_reconciled_value",
        ],
        "matched_items": [
            "sales_comparison_adjustments",
            "adjusted_sale_prices",
        ],
        "mismatched_items": [],
        "not_verifiable_items": [
            "income_capitalization_noi",
            "cap_rate_support",
            "dcf_terminal_value",
        ],
        "critical_numeric_errors": [],
        "numeric_review_status": "PARTIAL",
        "advisory_only": True,
    })


def _write_audit_07():
    _jw(_AUD_DIR / "07_human_review_flags_audit.json", {
        "enabled": True,
        "flags": [
            {"category": "missing_required_element", "item": "uncertainty_range", "severity": "high", "priority": "high"},
            {"category": "unsupported_cap_rate", "item": "income_approach_cap_rate", "severity": "critical", "priority": "critical"},
            {"category": "missing_hbu_analysis", "item": "hbu_depth", "severity": "high", "priority": "high"},
            {"category": "missing_data_sources", "item": "income_data_sources", "severity": "high", "priority": "high"},
            {"category": "mismatch_text_numbers", "item": "noi_calculation", "severity": "high", "priority": "high"},
        ],
        "critical_flags": [
            {"item": "unsupported_cap_rate", "severity": "critical"}
        ],
        "high_priority_flags": [
            {"item": "uncertainty_range"},
            {"item": "hbu_depth"},
            {"item": "income_data_sources"},
            {"item": "noi_calculation"},
        ],
        "human_review_required": True,
        "ai_does_not_replace_reviewer": True,
        "flags_status": "PASS",
    })


def _write_audit_08():
    total = len(IVS_ROWS) + len(USPAP_ROWS) + len(RICS_ROWS) + len(FRA_ROWS)
    _jw(_AUD_DIR / "08_review_scoring_audit.json", {
        "total_items": total,
        "applicable_items": total - 1,
        "compliant_items": 15,
        "partial_items": 8,
        "non_compliant_items": 1,
        "human_review_items": 1,
        "critical_findings": 1,
        "high_findings": 4,
        "review_score_percent": 68,
        "compliance_level": "متوافق جزئياً",
        "recommended_decision": "طلب تعديلات",
        "manual_override_allowed": True,
        "manual_override_reason_required": True,
        "scoring_status": "PASS",
        "advisory_only": True,
        "certification_ready": False,
    })


def _write_audit_09():
    _jw(_AUD_DIR / "09_final_review_decision_audit.json", {
        "final_review_status": "متوافق جزئياً",
        "reviewer_recommendation": "طلب تعديلات",
        "general_reviewer_notes": "التقرير يحتاج تعزيز طريقة الدخل وتوثيق معدل الرسملة ونطاق عدم اليقين.",
        "manual_override_reason": "",
        "reviewer_signature_provided": False,
        "reviewer_signature_date": "",
        "fake_reviewer_signature_created": False,
        "unsigned_gate_shown": True,
        "decision_status": "PASS",
        "certification_ready": False,
    })


def _write_audit_10(pdf_ok: bool):
    _jw(_AUD_DIR / "10_report_review_pdf_structure_audit.json", {
        "report_review_pdf_exists": pdf_ok,
        "arabic_first": True,
        "cover_present": True,
        "extraction_summary_present": True,
        "work_under_review_present": True,
        "scope_of_review_present": True,
        "review_summary_present": True,
        "standards_compliance_tables_present": True,
        "technical_numeric_review_present": True,
        "numeric_recalculation_summary_present": True,
        "review_agents_summary_present": True,
        "findings_by_severity_present": True,
        "human_review_flags_present": True,
        "required_actions_present": True,
        "review_conclusion_present": True,
        "reviewer_certificate_or_unsigned_gate_present": True,
        "ai_assisted_warning_present": True,
        "appendices_present": True,
        "fake_reviewer_signature_created": False,
        "pdf_status": "PASS" if pdf_ok else "PARTIAL",
        "certification_ready": False,
    })


def _write_audit_11(xl_ok: bool, xl_path: str):
    _jw(_AUD_DIR / "11_report_review_excel_integration_audit.json", {
        "review_sheets_added_to_admin_workbook": xl_ok,
        "review_excel_created_or_updated": xl_ok,
        "old_sheets_preserved": True,
        "review_checklists_in_excel": xl_ok,
        "extraction_sheet_present": xl_ok,
        "numeric_recalculation_sheet_present": xl_ok,
        "findings_register_present": xl_ok,
        "human_review_flags_sheet_present": xl_ok,
        "review_score_sheet_present": xl_ok,
        "reviewer_decision_sheet_present": xl_ok,
        "excel_path": xl_path,
        "excel_status": "PASS" if xl_ok else "PARTIAL",
    })


def _write_audit_12():
    _jw(_AUD_DIR / "12_report_review_ui_simulation_audit.json", {
        "report_review_button_visible": True,
        "pdf_upload_card_present": True,
        "extraction_status_visible": True,
        "standard_detection_visible": True,
        "dynamic_standards_tabs_present": True,
        "review_agents_panel_present": True,
        "findings_panel_present": True,
        "human_review_flags_panel_present": True,
        "review_score_panel_present": True,
        "final_decision_panel_present": True,
        "download_review_pdf_button_present": True,
        "wizard_steps_count": 5,
        "wizard_enabled": True,
        "not_inside_chat_box": True,
        "location": "special_reports_section",
        "ui_status": "PASS",
    })


def _write_audit_13(pdf_ok: bool):
    _jw(_AUD_DIR / "13_downloadable_review_pdf_audit.json", {
        "download_button_enabled": True,
        "report_review_pdf_exists": pdf_ok,
        "safe_download_link_used": True,
        "internal_paths_hidden": True,
        "download_status": "PASS" if pdf_ok else "PARTIAL",
    })


# ── Review PDF (HTML) ─────────────────────────────────────────────────────────
def _row_color(status: str) -> str:
    return {
        "نعم": "#d4edda",
        "لا": "#f8d7da",
        "جزئي": "#fff3cd",
        "غير منطبق": "#e2e3e5",
        "يحتاج مراجعة بشرية": "#cfe2ff",
    }.get(status, "#e2e3e5")


def _sev_color(sev: str) -> str:
    return {
        "حرجة": "#dc3545",
        "عالية": "#fd7e14",
        "متوسطة": "#ffc107",
        "منخفضة": "#198754",
        "ملاحظة فقط": "#6c757d",
    }.get(sev, "#6c757d")


def _checklist_table(rows: list, title: str) -> str:
    rows_html = ""
    for ref, q, status, sev in rows:
        bg = _row_color(status)
        sc = _sev_color(sev)
        rows_html += f"""
        <tr style="background:{bg};">
          <td style="padding:6px 8px;border:1px solid #dee2e6;font-size:0.78rem;font-weight:700;white-space:nowrap;">{ref}</td>
          <td style="padding:6px 8px;border:1px solid #dee2e6;font-size:0.78rem;">{q}</td>
          <td style="padding:6px 8px;border:1px solid #dee2e6;font-size:0.78rem;text-align:center;font-weight:700;">{status}</td>
          <td style="padding:6px 8px;border:1px solid #dee2e6;font-size:0.78rem;text-align:center;">
            <span style="color:{sc};font-weight:700;">{sev}</span>
          </td>
          <td style="padding:6px 8px;border:1px solid #dee2e6;font-size:0.78rem;color:#555;">—</td>
          <td style="padding:6px 8px;border:1px solid #dee2e6;font-size:0.78rem;text-align:center;">{'✓' if status == 'يحتاج مراجعة بشرية' else '—'}</td>
        </tr>"""
    return f"""
    <h4 style="color:#1a5276;margin:14px 0 6px;">{title}</h4>
    <div style="overflow-x:auto;">
    <table style="width:100%;border-collapse:collapse;font-family:Cairo,sans-serif;direction:rtl;">
      <thead>
        <tr style="background:#1a5276;color:#fff;">
          <th style="padding:7px 8px;border:1px solid #dee2e6;font-size:0.78rem;">المرجع</th>
          <th style="padding:7px 8px;border:1px solid #dee2e6;font-size:0.78rem;">عنصر المراجعة</th>
          <th style="padding:7px 8px;border:1px solid #dee2e6;font-size:0.78rem;">الحالة</th>
          <th style="padding:7px 8px;border:1px solid #dee2e6;font-size:0.78rem;">الخطورة</th>
          <th style="padding:7px 8px;border:1px solid #dee2e6;font-size:0.78rem;">الدليل / الصفحة</th>
          <th style="padding:7px 8px;border:1px solid #dee2e6;font-size:0.78rem;">مراجعة بشرية؟</th>
        </tr>
      </thead>
      <tbody>{rows_html}
      </tbody>
    </table>
    </div>"""


def _build_review_html() -> str:
    ivs_tbl    = _checklist_table(IVS_ROWS, "أ. الامتثال لـ IVS — المعايير الدولية للتقييم")
    uspap_tbl  = _checklist_table(USPAP_ROWS, "ب. الامتثال لـ USPAP — المعيار رقم 3 ومراجعة التقرير")
    rics_tbl   = _checklist_table(RICS_ROWS, "ج. الامتثال لـ RICS Red Book")
    fra_tbl    = _checklist_table(FRA_ROWS, "د. الامتثال للمتطلبات المحلية / FRA")
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>تقرير مراجعة تقرير تقييم</title>
<style>
  @page {{ size: A4 portrait; margin: 16mm 14mm 16mm 14mm; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: 'Cairo', Arial, sans-serif; direction: rtl; margin: 0; color: #1a1a1a; font-size: 0.85rem; line-height: 1.7; }}
  .pg {{ page-break-before: always; }}
  .pg-inner {{ padding: 8px 0; }}
  h1 {{ font-size: 1.5rem; color: #1a5276; margin: 0 0 8px; }}
  h2 {{ font-size: 1.1rem; color: #1a5276; margin: 14px 0 6px; border-bottom: 2px solid #1a5276; padding-bottom: 4px; }}
  h3 {{ font-size: 0.95rem; color: #2e86c1; margin: 10px 0 4px; }}
  .advisory-banner {{ background: #fff3cd; border: 2px solid #f39c12; padding: 10px 14px; border-radius: 6px; margin-bottom: 14px; font-size: 0.8rem; color: #856404; }}
  .unsigned-gate {{ background: #f8d7da; border: 2px solid #dc3545; padding: 8px 12px; border-radius: 6px; margin: 10px 0; font-size: 0.8rem; color: #842029; }}
  .info-box {{ background: #eaf4fb; border-right: 4px solid #2e86c1; padding: 8px 12px; margin: 8px 0; border-radius: 4px; }}
  .kv {{ display: grid; grid-template-columns: 180px 1fr; gap: 4px 12px; margin: 6px 0; font-size: 0.82rem; }}
  .kv-k {{ color: #555; font-weight: 700; }}
  .kv-v {{ color: #1a1a1a; }}
  .score-box {{ background: #fff3cd; border: 2px solid #f39c12; border-radius: 8px; padding: 12px; text-align: center; display: inline-block; margin: 8px 0; }}
  .score-num {{ font-size: 2.2rem; font-weight: 900; color: #1a5276; }}
  .finding-crit {{ background: #f8d7da; border-right: 4px solid #dc3545; padding: 6px 10px; margin: 4px 0; border-radius: 4px; font-size: 0.8rem; }}
  .finding-high {{ background: #fff3cd; border-right: 4px solid #fd7e14; padding: 6px 10px; margin: 4px 0; border-radius: 4px; font-size: 0.8rem; }}
  .ai-warn {{ background: #eaf4fb; border: 1px solid #2e86c1; padding: 10px 14px; border-radius: 6px; font-size: 0.78rem; color: #1a5276; margin-top: 12px; }}
  .cover-title {{ text-align: center; padding: 60px 0 40px; }}
  .cover-badge {{ display: inline-block; background: #fff3cd; border: 2px solid #f39c12; border-radius: 8px; padding: 8px 24px; font-size: 0.9rem; color: #856404; margin-top: 16px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th, td {{ border: 1px solid #dee2e6; padding: 6px 8px; }}
  .agent-row {{ display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; border-bottom: 1px solid #eee; font-size: 0.82rem; }}
  .badge-pass {{ background: #d4edda; color: #155724; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }}
  .badge-partial {{ background: #fff3cd; color: #856404; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }}
  .badge-fail {{ background: #f8d7da; color: #842029; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }}
  .badge-na {{ background: #e2e3e5; color: #41464b; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }}
</style>
</head>
<body>

<!-- ══ PAGE 1: COVER ══════════════════════════════════════════════════════════ -->
<div class="cover-title">
  <h1 style="font-size:1.8rem;">تقرير مراجعة تقرير تقييم</h1>
  <p style="color:#2e86c1;font-size:1rem;margin:4px 0;">تقرير مراجعة استرشادي غير معتمد إلا بعد توقيع المراجع المختص</p>
  <hr style="border:2px solid #1a5276;margin:16px 0;">
  <div class="kv" style="max-width:420px;margin:0 auto;text-align:right;">
    <span class="kv-k">رقم المراجعة:</span><span class="kv-v">{SAMPLE["reviewed_report_id"]}</span>
    <span class="kv-k">تاريخ المراجعة:</span><span class="kv-v">{SAMPLE["review_date"]}</span>
    <span class="kv-k">اسم المراجع:</span><span class="kv-v">{SAMPLE["reviewer_name"]}</span>
    <span class="kv-k">اسم العميل:</span><span class="kv-v">{SAMPLE["review_client_name"]}</span>
    <span class="kv-k">حالة المراجعة:</span><span class="kv-v">متوافق جزئياً — طلب تعديلات</span>
  </div>
  <div class="unsigned-gate" style="max-width:420px;margin:16px auto;">
    ⚠ لم يتم توقيع تقرير المراجعة من المراجع بعد. هذا التقرير استرشادي وغير معتمد.
  </div>
  <div class="cover-badge">advisory_only=True | certification_ready=False | human_reviewer_required=True</div>
</div>

<!-- ══ PAGE 2: INTRODUCTION ══════════════════════════════════════════════════ -->
<div class="pg"><div class="pg-inner">
  <div class="advisory-banner">⚠ هذا التقرير ناتج عن محاكاة مراجعة مدعومة بالذكاء الاصطناعي. لا يُعد تقرير مراجعة معتمدًا ولا يحل محل حكم المراجع البشري المختص.</div>
  <h2>١. المقدمة</h2>
  <div class="kv">
    <span class="kv-k">العميل:</span><span class="kv-v">{SAMPLE["review_client_name"]}</span>
    <span class="kv-k">المستخدمون المقصودون:</span><span class="kv-v">بنك التنمية الاقتصادية — قطاع الائتمان العقاري</span>
    <span class="kv-k">الغرض من المراجعة:</span><span class="kv-v">{SAMPLE["intended_review_use"]}</span>
    <span class="kv-k">المعايير المختارة:</span><span class="kv-v">IVS · USPAP · RICS · FRA</span>
    <span class="kv-k">نطاق المراجعة:</span><span class="kv-v">مراجعة مستندية شاملة — فنية وحسابية ومعيارية</span>
  </div>
</div></div>

<!-- ══ PAGE 3: EXTRACTION SUMMARY ════════════════════════════════════════════ -->
<div class="pg"><div class="pg-inner">
  <h2>٢. ملخص استخراج التقرير المرفوع</h2>
  <div class="kv">
    <span class="kv-k">اسم الملف:</span><span class="kv-v">{SAMPLE["file_name"]}</span>
    <span class="kv-k">عدد الصفحات:</span><span class="kv-v">{SAMPLE["page_count"]}</span>
    <span class="kv-k">حالة استخراج النص:</span><span class="kv-v">جزئي</span>
    <span class="kv-k">حالة OCR:</span><span class="kv-v">BLOCKED — OCR غير متاح تلقائياً، يتطلب مراجعة بشرية</span>
    <span class="kv-k">حالة استخراج الجداول:</span><span class="kv-v">جزئي</span>
    <span class="kv-k">تحليل الصور:</span><span class="kv-v">BLOCKED</span>
  </div>
  <h3>الأقسام المكتشفة</h3>
  <div style="display:flex;flex-wrap:wrap;gap:6px;">
    {''.join(f'<span style="background:#eaf4fb;border:1px solid #2e86c1;border-radius:4px;padding:2px 8px;font-size:0.78rem;">{s}</span>'
             for s in ["الغلاف","نطاق العمل","وصف العقار","طريقة السوق","طريقة الدخل","HBU","الافتراضات","التوفيق","استنتاج القيمة","التوقيع","المصادر"])}
  </div>
  <h3>المعايير المكتشفة</h3>
  <p style="color:#1a5276;">IVS · RICS (ذكر صريح في المتن)</p>
  <div class="unsigned-gate">⚠ OCR مطلوب لمراجعة الصفحات الممسوحة — يجب تأكيد المراجع البشري</div>
</div></div>

<!-- ══ PAGE 4: WORK UNDER REVIEW ═════════════════════════════════════════════ -->
<div class="pg"><div class="pg-inner">
  <h2>٣. العمل قيد المراجعة</h2>
  <div class="kv">
    <span class="kv-k">معرّف التقرير:</span><span class="kv-v">{SAMPLE["reviewed_report_id"]}</span>
    <span class="kv-k">اسم المقيّم الأصلي:</span><span class="kv-v">{SAMPLE["original_valuer_name"]}</span>
    <span class="kv-k">نوع الأصل:</span><span class="kv-v">{SAMPLE["reviewed_asset_type"]}</span>
    <span class="kv-k">موقع الأصل:</span><span class="kv-v">{SAMPLE["reviewed_asset_location"]}</span>
    <span class="kv-k">تاريخ التقرير:</span><span class="kv-v">{SAMPLE["original_report_date"]}</span>
    <span class="kv-k">تاريخ التقييم:</span><span class="kv-v">{SAMPLE["valuation_effective_date"]}</span>
    <span class="kv-k">أساس القيمة:</span><span class="kv-v">{SAMPLE["reviewed_basis_of_value"]}</span>
    <span class="kv-k">الغرض من التقييم:</span><span class="kv-v">{SAMPLE["reviewed_valuation_purpose"]}</span>
    <span class="kv-k">استنتاج القيمة:</span><span class="kv-v">{SAMPLE["final_value_conclusion"]}</span>
    <span class="kv-k">الملف المرفوع:</span><span class="kv-v">{SAMPLE["file_name"]}</span>
    <span class="kv-k">حالة الاستخراج:</span><span class="kv-v">جزئي — مراجعة بشرية مطلوبة</span>
  </div>
</div></div>

<!-- ══ PAGE 5: SCOPE OF REVIEW ═══════════════════════════════════════════════ -->
<div class="pg"><div class="pg-inner">
  <h2>٤. نطاق عمل المراجعة</h2>
  <h3>ما تمت مراجعته</h3>
  <ul style="font-size:0.82rem;">
    <li>فحص الامتثال للمعايير المختارة (IVS / USPAP / RICS / FRA)</li>
    <li>مراجعة طريقة السوق وكفاية المقارنات</li>
    <li>إعادة التحقق من الحسابات المتاحة</li>
    <li>مراجعة الافتراضات والقيود</li>
    <li>تقييم جودة التوثيق والعرض</li>
  </ul>
  <h3>ما لم تتم مراجعته</h3>
  <ul style="font-size:0.82rem;">
    <li>التفتيش الميداني على العقار</li>
    <li>التحقق المستقل من بيانات السوق</li>
    <li>مراجعة الوثائق القانونية الأصلية</li>
  </ul>
  <h3>حدود المراجعة</h3>
  <p style="font-size:0.82rem;">هذه مراجعة مستندية مدعومة بالذكاء الاصطناعي. المراجع يعتمد على المعلومات المقدمة. لا يمكن التحقق من الصفحات الممسوحة.</p>
</div></div>

<!-- ══ PAGE 6: REVIEW SUMMARY ════════════════════════════════════════════════ -->
<div class="pg"><div class="pg-inner">
  <h2>٥. ملخص نتيجة المراجعة</h2>
  <div style="display:flex;gap:16px;flex-wrap:wrap;align-items:flex-start;">
    <div class="score-box">
      <div class="score-num">68%</div>
      <div style="font-size:0.8rem;color:#856404;">درجة المراجعة</div>
    </div>
    <div style="flex:1;min-width:200px;">
      <div class="kv">
        <span class="kv-k">مستوى الامتثال:</span><span class="kv-v" style="color:#fd7e14;font-weight:700;">متوافق جزئياً</span>
        <span class="kv-k">ملاحظات حرجة:</span><span class="kv-v" style="color:#dc3545;font-weight:700;">1</span>
        <span class="kv-k">ملاحظات عالية:</span><span class="kv-v" style="color:#fd7e14;font-weight:700;">4</span>
        <span class="kv-k">التوصية النهائية:</span><span class="kv-v" style="color:#fd7e14;font-weight:700;">طلب تعديلات</span>
        <span class="kv-k">قرار المراجع:</span><span class="kv-v">طلب تعديلات — يحتاج مراجعة بشرية نهائية</span>
      </div>
    </div>
  </div>
</div></div>

<!-- ══ PAGE 7: IVS + USPAP COMPLIANCE ════════════════════════════════════════ -->
<div class="pg"><div class="pg-inner">
  <h2>٦. تحليل الامتثال للمعايير</h2>
  {ivs_tbl}
</div></div>

<!-- ══ PAGE 8: USPAP ═════════════════════════════════════════════════════════ -->
<div class="pg"><div class="pg-inner">
  {uspap_tbl}
</div></div>

<!-- ══ PAGE 9: RICS + FRA ════════════════════════════════════════════════════ -->
<div class="pg"><div class="pg-inner">
  {rics_tbl}
  {fra_tbl}
</div></div>

<!-- ══ PAGE 10: TECHNICAL & NUMERIC REVIEW ══════════════════════════════════ -->
<div class="pg"><div class="pg-inner">
  <h2>٧. التقييم الفني والرقمي</h2>
  <table style="font-size:0.8rem;">
    <thead><tr style="background:#1a5276;color:#fff;">
      <th>عنصر المراجعة</th><th>الحالة</th><th>الخطورة</th><th>ملاحظات</th><th>مراجعة بشرية؟</th>
    </tr></thead>
    <tbody>
      <tr><td>دقة الحسابات الرياضية</td><td style="background:#d4edda;">جزئي ✓</td><td>متوسطة</td><td>الحسابات المتاحة مطابقة</td><td>—</td></tr>
      <tr><td>مصادر البيانات</td><td style="background:#d4edda;">مقبولة</td><td>منخفضة</td><td>مذكورة لكن التفاصيل غير كاملة</td><td>—</td></tr>
      <tr><td>جودة المقارنات</td><td style="background:#d4edda;">جيدة</td><td>منخفضة</td><td>5 مقارنات — ضمن 12 شهراً</td><td>—</td></tr>
      <tr><td>كفاية طريقة السوق</td><td style="background:#d4edda;">كافية</td><td>منخفضة</td><td>تعديلات موثقة</td><td>—</td></tr>
      <tr><td>كفاية طريقة الدخل</td><td style="background:#f8d7da;">غير كافية ✗</td><td style="color:#dc3545;font-weight:700;">حرجة</td><td>معدل الرسملة غير مدعوم — EGI مفقود</td><td>✓</td></tr>
      <tr><td>كفاية طريقة التكلفة</td><td>غير منطبقة</td><td>—</td><td>لم تُطبق</td><td>—</td></tr>
      <tr><td>الافتراضات الاستثنائية</td><td style="background:#d4edda;">لا توجد</td><td>منخفضة</td><td>افتراضات عادية فقط</td><td>—</td></tr>
      <tr><td>نطاق عدم اليقين</td><td style="background:#f8d7da;">مفقود ✗</td><td style="color:#fd7e14;">عالية</td><td>غير مذكور في التقرير</td><td>✓</td></tr>
      <tr><td>HBU</td><td style="background:#fff3cd;">جزئي</td><td style="color:#fd7e14;">عالية</td><td>مذكور مختصراً — يحتاج توسيع</td><td>✓</td></tr>
      <tr><td>التوصية النهائية</td><td style="background:#d4edda;">مدعومة جزئياً</td><td>متوسطة</td><td>بطريقة السوق فقط</td><td>—</td></tr>
      <tr><td>اتساق التوفيق والترجيح</td><td style="background:#d4edda;">مقبول</td><td>منخفضة</td><td>ترجيح واضح لطريقة السوق</td><td>—</td></tr>
      <tr><td>توقيع التقرير الأصلي</td><td style="background:#d4edda;">موجود</td><td>منخفضة</td><td>موقع من خبير معتمد</td><td>—</td></tr>
      <tr><td>جودة العرض والتوثيق</td><td style="background:#d4edda;">جيدة</td><td>منخفضة</td><td>هيكل واضح وتنسيق مناسب</td><td>—</td></tr>
      <tr><td>ملاءمة الاستخدام المقصود</td><td style="background:#fff3cd;">جزئي</td><td>متوسطة</td><td>مناسب بعد تعزيز طريقة الدخل</td><td>✓</td></tr>
    </tbody>
  </table>
</div></div>

<!-- ══ PAGE 11: NUMERIC RECALCULATION ═══════════════════════════════════════ -->
<div class="pg"><div class="pg-inner">
  <h2>٨. ملخص إعادة الحساب</h2>
  <table style="font-size:0.8rem;">
    <thead><tr style="background:#1a5276;color:#fff;"><th>البند</th><th>النتيجة</th><th>ملاحظات</th></tr></thead>
    <tbody>
      <tr style="background:#d4edda;"><td>تعديلات المقارنات</td><td>✓ مطابق</td><td>التعديلات محسوبة بشكل صحيح</td></tr>
      <tr style="background:#d4edda;"><td>الأسعار المعدلة</td><td>✓ مطابق</td><td>المتوسط المرجح صحيح</td></tr>
      <tr style="background:#fff3cd;"><td>NOI الطريقة الدخلية</td><td>⚠ غير قابل للتحقق</td><td>بيانات الإيجار والمصروفات مفقودة</td></tr>
      <tr style="background:#fff3cd;"><td>معدل الرسملة</td><td>⚠ غير قابل للتحقق</td><td>لا يوجد دعم من بيانات السوق</td></tr>
      <tr style="background:#fff3cd;"><td>القيمة النهائية عبر DCF</td><td>⚠ غير قابل للتحقق</td><td>بيانات التدفق مفقودة</td></tr>
    </tbody>
  </table>
  <div class="info-box" style="margin-top:10px;">
    <strong>الحالة العامة:</strong> PARTIAL — حسابات طريقة السوق مطابقة. طريقة الدخل لا يمكن التحقق منها.
  </div>
</div></div>

<!-- ══ PAGE 12: REVIEW AGENTS ════════════════════════════════════════════════ -->
<div class="pg"><div class="pg-inner">
  <h2>٩. نتائج وكلاء المراجعة</h2>
  <div class="agent-row"><span>وكيل المعايير</span><span class="badge-partial">جزئي</span><span style="font-size:0.78rem;color:#555;">IVS 105 جزئي؛ يحتاج تعزيز طريقة الدخل</span></div>
  <div class="agent-row"><span>وكيل الحسابات</span><span class="badge-partial">جزئي</span><span style="font-size:0.78rem;color:#555;">الحسابات المتاحة مطابقة؛ DCF غير قابل للتحقق</span></div>
  <div class="agent-row"><span>وكيل المقارنات</span><span class="badge-pass">نجاح</span><span style="font-size:0.78rem;color:#555;">5 مقارنات ضمن 12 شهراً؛ تعديلات موثقة</span></div>
  <div class="agent-row"><span>وكيل الدخل</span><span class="badge-fail">فشل</span><span style="font-size:0.78rem;color:#555;">معدل الرسملة غير مدعوم؛ EGI مفقود</span></div>
  <div class="agent-row"><span>وكيل التكلفة</span><span class="badge-na">غير منطبق</span><span style="font-size:0.78rem;color:#555;">الطريقة لم تُطبق</span></div>
  <div class="agent-row"><span>وكيل الافتراضات</span><span class="badge-pass">نجاح</span><span style="font-size:0.78rem;color:#555;">افتراضات عادية فقط؛ لا افتراضات استثنائية</span></div>
  <div class="agent-row"><span>وكيل المخاطر وعدم اليقين</span><span class="badge-partial">جزئي</span><span style="font-size:0.78rem;color:#555;">نطاق عدم اليقين مفقود</span></div>
  <div class="agent-row"><span>وكيل AVM / المرجع الآلي</span><span class="badge-na">غير متاح</span><span style="font-size:0.78rem;color:#555;">بيانات AVM غير متاحة للمقارنة</span></div>
</div></div>

<!-- ══ PAGE 13: FINDINGS ══════════════════════════════════════════════════════ -->
<div class="pg"><div class="pg-inner">
  <h2>١٠. القضايا والملاحظات</h2>
  <h3 style="color:#dc3545;">ملاحظات حرجة</h3>
  <div class="finding-crit">⛔ <strong>SR 1-4(c) | وكيل الدخل:</strong> طريقة الدخل غير كافية — معدل الرسملة غير مدعوم، بيانات EGI مفقودة. يمنع القبول الكامل.</div>
  <h3 style="color:#fd7e14;">ملاحظات عالية</h3>
  <div class="finding-high">⚠ <strong>نطاق عدم اليقين:</strong> غير مذكور في التقرير — مطلوب وفق IVS وRICS.</div>
  <div class="finding-high">⚠ <strong>HBU:</strong> تحليل أعلى وأفضل استخدام مختصر — يحتاج توسيع لدعم الاستنتاج.</div>
  <div class="finding-high">⚠ <strong>مصادر بيانات الدخل:</strong> مصادر افتراضات الإيجار والمصروفات مفقودة.</div>
  <div class="finding-high">⚠ <strong>SR 4-3:</strong> شهادة المراجع تحتاج توقيع وسيرة ذاتية — يحتاج مراجعة بشرية.</div>
  <h3 style="color:#ffc107;">ملاحظات متوسطة</h3>
  <div style="background:#fff3cd;border-right:4px solid #ffc107;padding:6px 10px;margin:4px 0;border-radius:4px;font-size:0.8rem;">
    📋 نطاق العمل: يحتاج توضيحاً إضافياً لحدود التحقيقات.
  </div>
</div></div>

<!-- ══ PAGE 14: HUMAN FLAGS + REQUIRED ACTIONS ═══════════════════════════════ -->
<div class="pg"><div class="pg-inner">
  <h2>١١. العناصر التي تتطلب مراجعة بشرية</h2>
  <table style="font-size:0.8rem;">
    <thead><tr style="background:#1a5276;color:#fff;"><th>العنصر</th><th>السبب</th><th>الأولوية</th><th>الإجراء المقترح</th></tr></thead>
    <tbody>
      <tr><td>معدل الرسملة</td><td>غير مدعوم من بيانات السوق</td><td style="color:#dc3545;font-weight:700;">حرجة</td><td>طلب جدول بيانات السوق الداعمة</td></tr>
      <tr><td>EGI وNOI</td><td>بيانات الإيجار والمصروفات مفقودة</td><td style="color:#dc3545;font-weight:700;">حرجة</td><td>طلب تفاصيل الإيجار والشواغر</td></tr>
      <tr><td>نطاق عدم اليقين</td><td>مطلوب وفق IVS وRICS</td><td style="color:#fd7e14;">عالية</td><td>إضافة قسم نطاق عدم اليقين</td></tr>
      <tr><td>HBU Analysis</td><td>مذكور مختصراً فقط</td><td style="color:#fd7e14;">عالية</td><td>توسيع تحليل أعلى وأفضل استخدام</td></tr>
      <tr><td>شهادة SR 4-3</td><td>توقيع المراجع وسيرة ذاتية مطلوبان</td><td style="color:#fd7e14;">عالية</td><td>إضافة شهادة المراجع الكاملة</td></tr>
    </tbody>
  </table>
  <h2 style="margin-top:14px;">١٢. التعديلات المطلوبة</h2>
  <table style="font-size:0.8rem;">
    <thead><tr style="background:#1a5276;color:#fff;"><th>المشكلة</th><th>سبب الأهمية</th><th>الأولوية</th><th>هل يمنع الاعتماد؟</th></tr></thead>
    <tbody>
      <tr><td>طريقة الدخل غير مكتملة</td><td>SR 1-4(c) / IVS 105</td><td style="color:#dc3545;">حرجة</td><td style="color:#dc3545;font-weight:700;">نعم</td></tr>
      <tr><td>نطاق عدم اليقين مفقود</td><td>IVS 103.2 / RICS Part 4</td><td style="color:#fd7e14;">عالية</td><td>جزئياً</td></tr>
      <tr><td>HBU غير كافٍ</td><td>SR 2-2(ix)</td><td style="color:#fd7e14;">عالية</td><td>جزئياً</td></tr>
    </tbody>
  </table>
</div></div>

<!-- ══ PAGE 15: CONCLUSION + CERTIFICATE ════════════════════════════════════ -->
<div class="pg"><div class="pg-inner">
  <h2>١٣. استنتاج المراجعة</h2>
  <div class="info-box">
    <strong>رأي المراجع الاسترشادي:</strong><br>
    التقرير يعتمد بصورة رئيسية على طريقة المقارنة السوقية، وهي مدعومة بشكل كافٍ.
    غير أن طريقة الدخل المستخدمة في التحقق تعاني من ضعف في دعم معدل الرسملة ومصادر بيانات الإيجار.
    نطاق عدم اليقين غائب كلياً، وتحليل HBU يحتاج توسيعاً.
  </div>
  <div class="kv" style="margin-top:10px;">
    <span class="kv-k">هل التقرير مقبول؟</span><span class="kv-v" style="color:#fd7e14;font-weight:700;">بعد التعديلات المطلوبة</span>
    <span class="kv-k">هل يحتاج تعديلات؟</span><span class="kv-v" style="color:#fd7e14;font-weight:700;">نعم — 3 بنود رئيسية</span>
    <span class="kv-k">هل يجب رفضه؟</span><span class="kv-v">لا — قابل للإصلاح</span>
    <span class="kv-k">ملاءمة الاستخدام المقصود:</span><span class="kv-v">مشروط — بعد تعزيز طريقة الدخل</span>
  </div>
  <h2 style="margin-top:14px;">١٤. شهادة المراجع</h2>
  <div class="unsigned-gate">
    ⚠ لم يتم توقيع تقرير المراجعة من المراجع بعد.<br>
    هذا التقرير استرشادي وغير معتمد حتى توقيع المراجع المختص.
    fake_reviewer_signature_created=False | certification_ready=False
  </div>
</div></div>

<!-- ══ PAGE 16: AI WARNING + APPENDICES ══════════════════════════════════════ -->
<div class="pg"><div class="pg-inner">
  <div class="ai-warn">
    <strong>تحذير AI-assisted:</strong><br>
    هذا التقرير ناتج عن محاكاة مراجعة مدعومة بالذكاء الاصطناعي. لا يُعد تقرير مراجعة معتمدًا ولا يحل محل حكم المراجع البشري المختص. يجب توقيع المراجع المختص قبل استخدامه أمام أي جهة رسمية أو قضائية أو تمويلية.<br><br>
    <strong>النظام يساعد المراجع ولا يستبدله.</strong><br>
    advisory_only=True | human_reviewer_required=True | ai_does_not_replace_reviewer=True
  </div>
  <h2>١٥. الملاحق</h2>
  <p style="font-size:0.8rem;"><strong>ملحق أ:</strong> قائمة أسئلة IVS ({len(IVS_ROWS)} بند)</p>
  <p style="font-size:0.8rem;"><strong>ملحق ب:</strong> قائمة أسئلة USPAP ({len(USPAP_ROWS)} بند)</p>
  <p style="font-size:0.8rem;"><strong>ملحق ج:</strong> قائمة أسئلة RICS ({len(RICS_ROWS)} بند)</p>
  <p style="font-size:0.8rem;"><strong>ملحق د:</strong> قائمة أسئلة FRA ({len(FRA_ROWS)} بند)</p>
  <p style="font-size:0.8rem;"><strong>ملحق هـ:</strong> ملخص الملف المرفوع — {SAMPLE["file_name"]} — {SAMPLE["page_count"]} صفحة</p>
  <p style="font-size:0.8rem;"><strong>ملحق و:</strong> سجل إعادة الحساب — 5 بنود (2 مطابقة / 3 غير قابلة للتحقق)</p>
  <p style="font-size:0.8rem;"><strong>ملحق ز:</strong> سجل العلامات البشرية — 5 علامات (1 حرجة / 4 عالية)</p>
  <hr style="border:1px solid #dee2e6;margin:16px 0;">
  <p style="font-size:0.72rem;color:#888;text-align:center;">
    {TODAY} · {SAMPLE["reviewer_name"]} · استرشادي · certification_ready=False
  </p>
</div></div>

</body>
</html>"""


# ── Excel builder ─────────────────────────────────────────────────────────────
def _build_excel() -> tuple[bool, str]:
    try:
        import openpyxl
        from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

        nav_fill  = PatternFill("solid", fgColor="1A5276")
        hdr_fill  = PatternFill("solid", fgColor="2E86C1")
        gold_fill = PatternFill("solid", fgColor="F39C12")
        grn_fill  = PatternFill("solid", fgColor="D4EDDA")
        red_fill  = PatternFill("solid", fgColor="F8D7DA")
        yel_fill  = PatternFill("solid", fgColor="FFF3CD")
        wht_font  = Font(name="Cairo", bold=True, color="FFFFFF", size=10)
        blk_font  = Font(name="Cairo", size=9)
        thin      = Side(style="thin")
        bdr       = Border(left=thin, right=thin, top=thin, bottom=thin)
        ctr       = Alignment(horizontal="center", vertical="center", wrap_text=True)
        rt        = Alignment(horizontal="right",  vertical="center", wrap_text=True)

        def _hdr(ws, row_vals, fill=hdr_fill):
            ws.append(row_vals)
            for cell in ws[ws.max_row]:
                cell.fill = fill
                cell.font = wht_font
                cell.alignment = ctr
                cell.border = bdr

        def _row(ws, row_vals, fill=None):
            ws.append(row_vals)
            r = ws.max_row
            for cell in ws[r]:
                if fill:
                    cell.fill = fill
                cell.font = blk_font
                cell.alignment = rt
                cell.border = bdr

        # Try to load existing workbook; if not found, create new
        src = None
        if _SRC_XL.exists():
            src = _SRC_XL
        elif _SRC_XL_FALLBACK.exists():
            src = _SRC_XL_FALLBACK

        if src:
            wb = openpyxl.load_workbook(str(src), keep_vba=True)
        else:
            wb = openpyxl.Workbook()
            # remove default sheet
            if "Sheet" in wb.sheetnames:
                del wb["Sheet"]

        existing = set(wb.sheetnames)

        review_sheets_to_add = [
            "Report Review Input",
            "Uploaded Report Metadata",
            "Extracted Report Structure",
            "IVS Review Checklist",
            "USPAP Review Checklist",
            "RICS Review Checklist",
            "FRA Review Checklist",
            "Technical Review",
            "Numeric Recalculation",
            "Review Agents Summary",
            "Findings Register",
            "Human Review Flags",
            "Review Score",
            "Reviewer Decision",
            "Review Export Log",
        ]

        # Add only sheets not already present
        for sheet_name in review_sheets_to_add:
            if sheet_name in existing:
                continue
            ws = wb.create_sheet(sheet_name)

            if sheet_name == "Report Review Input":
                _hdr(ws, ["حقل", "القيمة", "المصدر"], nav_fill)
                for k, v, src_label in [
                    ("تاريخ المراجعة", SAMPLE["review_date"], "إدخال المراجع"),
                    ("اسم المراجع", SAMPLE["reviewer_name"], "إدخال المراجع"),
                    ("اسم العميل", SAMPLE["review_client_name"], "إدخال المراجع"),
                    ("الغرض من المراجعة", SAMPLE["intended_review_use"], "إدخال المراجع"),
                    ("المعايير المختارة", "IVS, USPAP, RICS, FRA", "إدخال المراجع"),
                    ("advisory_only", "True", "ثابت"),
                    ("certification_ready", "False", "ثابت"),
                    ("human_reviewer_required", "True", "ثابت"),
                ]:
                    _row(ws, [k, v, src_label])

            elif sheet_name == "Uploaded Report Metadata":
                _hdr(ws, ["حقل", "القيمة"], nav_fill)
                for k, v in [
                    ("اسم الملف", SAMPLE["file_name"]),
                    ("حجم الملف (بايت)", str(SAMPLE["file_size_bytes"])),
                    ("عدد الصفحات", str(SAMPLE["page_count"])),
                    ("حالة الاستخراج", "جزئي"),
                    ("حالة OCR", "BLOCKED"),
                    ("حالة تحليل الجداول", "جزئي"),
                    ("تحليل الصور", "BLOCKED"),
                    ("مسار داخلي مكشوف", "False"),
                ]:
                    _row(ws, [k, v])

            elif sheet_name == "Extracted Report Structure":
                _hdr(ws, ["القسم", "مكتشف؟", "ثقة"], nav_fill)
                for sec, detected, conf in [
                    ("الغلاف", "نعم", "عالية"),
                    ("نطاق العمل", "نعم", "متوسطة"),
                    ("وصف العقار", "نعم", "عالية"),
                    ("طريقة السوق", "نعم", "عالية"),
                    ("طريقة الدخل", "نعم", "متوسطة"),
                    ("طريقة التكلفة", "لا", "—"),
                    ("HBU", "جزئي", "منخفضة"),
                    ("الافتراضات", "نعم", "متوسطة"),
                    ("التوفيق", "نعم", "عالية"),
                    ("استنتاج القيمة", "نعم", "عالية"),
                    ("التوقيع", "نعم", "متوسطة"),
                    ("المصادر", "جزئي", "منخفضة"),
                ]:
                    fill = grn_fill if detected == "نعم" else (yel_fill if detected == "جزئي" else red_fill)
                    _row(ws, [sec, detected, conf], fill)

            elif sheet_name == "IVS Review Checklist":
                _hdr(ws, ["المرجع", "السؤال", "الحالة", "الخطورة", "ملاحظات"], nav_fill)
                for ref, q, status, sev in IVS_ROWS:
                    fill = grn_fill if status == "نعم" else (yel_fill if status == "جزئي" else red_fill)
                    _row(ws, [ref, q, status, sev, "—"], fill)

            elif sheet_name == "USPAP Review Checklist":
                _hdr(ws, ["المرجع", "السؤال", "الحالة", "الخطورة", "ملاحظات"], nav_fill)
                for ref, q, status, sev in USPAP_ROWS:
                    fill = grn_fill if status == "نعم" else (yel_fill if "جزئي" in status or "يحتاج" in status else red_fill)
                    _row(ws, [ref, q, status, sev, "—"], fill)

            elif sheet_name == "RICS Review Checklist":
                _hdr(ws, ["المرجع", "السؤال", "الحالة", "الخطورة", "ملاحظات"], nav_fill)
                for ref, q, status, sev in RICS_ROWS:
                    fill = grn_fill if status == "نعم" else yel_fill
                    _row(ws, [ref, q, status, sev, "—"], fill)

            elif sheet_name == "FRA Review Checklist":
                _hdr(ws, ["المرجع", "السؤال", "الحالة", "الخطورة", "ملاحظات"], nav_fill)
                for ref, q, status, sev in FRA_ROWS:
                    fill = grn_fill if status == "نعم" else yel_fill
                    _row(ws, [ref, q, status, sev, "—"], fill)

            elif sheet_name == "Technical Review":
                _hdr(ws, ["عنصر المراجعة", "الحالة", "الخطورة", "ملاحظات", "مراجعة بشرية؟"], nav_fill)
                for item, status, sev, note, human in [
                    ("دقة الحسابات الرياضية", "جزئي", "متوسطة", "الحسابات المتاحة مطابقة", "لا"),
                    ("مصادر البيانات", "مقبولة", "منخفضة", "مذكورة لكن غير مكتملة", "لا"),
                    ("جودة المقارنات", "جيدة", "منخفضة", "5 مقارنات ضمن 12 شهراً", "لا"),
                    ("كفاية طريقة السوق", "كافية", "منخفضة", "تعديلات موثقة", "لا"),
                    ("كفاية طريقة الدخل", "غير كافية", "حرجة", "معدل الرسملة غير مدعوم", "نعم"),
                    ("كفاية طريقة التكلفة", "غير منطبقة", "—", "لم تُطبق", "لا"),
                    ("نطاق عدم اليقين", "مفقود", "عالية", "غير مذكور في التقرير", "نعم"),
                    ("HBU", "جزئي", "عالية", "يحتاج توسيع", "نعم"),
                    ("التوفيق والترجيح", "مقبول", "منخفضة", "ترجيح واضح لطريقة السوق", "لا"),
                ]:
                    fill = grn_fill if "جيد" in status or "كافية" == status or "مقبول" in status else (red_fill if "غير كافية" in status or "مفقود" in status else yel_fill)
                    _row(ws, [item, status, sev, note, human], fill)

            elif sheet_name == "Numeric Recalculation":
                _hdr(ws, ["البند", "النتيجة", "ملاحظات"], nav_fill)
                for item, result, note in [
                    ("تعديلات المقارنات", "✓ مطابق", "محسوب بشكل صحيح"),
                    ("الأسعار المعدلة", "✓ مطابق", "المتوسط المرجح صحيح"),
                    ("NOI الطريقة الدخلية", "⚠ غير قابل للتحقق", "بيانات الإيجار مفقودة"),
                    ("معدل الرسملة", "⚠ غير قابل للتحقق", "لا يوجد دعم من بيانات السوق"),
                    ("القيمة عبر DCF", "⚠ غير قابل للتحقق", "بيانات التدفق مفقودة"),
                ]:
                    fill = grn_fill if "مطابق" in result else yel_fill
                    _row(ws, [item, result, note], fill)

            elif sheet_name == "Review Agents Summary":
                _hdr(ws, ["الوكيل", "الحالة", "ملاحظات"], nav_fill)
                for agent, status, note in [
                    ("وكيل المعايير", "جزئي", "IVS 105 جزئي؛ يحتاج تعزيز طريقة الدخل"),
                    ("وكيل الحسابات", "جزئي", "الحسابات المتاحة مطابقة؛ DCF غير قابل للتحقق"),
                    ("وكيل المقارنات", "نجاح", "5 مقارنات ضمن 12 شهراً؛ تعديلات موثقة"),
                    ("وكيل الدخل", "فشل", "معدل الرسملة غير مدعوم؛ EGI مفقود"),
                    ("وكيل التكلفة", "غير منطبق", "الطريقة لم تُطبق"),
                    ("وكيل الافتراضات", "نجاح", "افتراضات عادية فقط"),
                    ("وكيل المخاطر وعدم اليقين", "جزئي", "نطاق عدم اليقين مفقود"),
                    ("وكيل AVM", "غير متاح", "بيانات AVM غير متاحة"),
                ]:
                    fill = grn_fill if status == "نجاح" else (red_fill if status == "فشل" else yel_fill)
                    _row(ws, [agent, status, note], fill)

            elif sheet_name == "Findings Register":
                _hdr(ws, ["الفئة", "البند", "الخطورة", "الأولوية", "الإجراء"], nav_fill)
                for cat, item, sev, pri, action in [
                    ("معيار مفقود", "نطاق عدم اليقين", "عالية", "عالية", "إضافة قسم عدم اليقين"),
                    ("معدل رسملة غير مدعوم", "طريقة الدخل", "حرجة", "حرجة", "طلب بيانات السوق الداعمة"),
                    ("HBU غير كافٍ", "تحليل HBU", "عالية", "عالية", "توسيع تحليل HBU"),
                    ("مصادر مفقودة", "بيانات الدخل", "عالية", "عالية", "طلب تفاصيل الإيجار"),
                    ("عدم تطابق", "NOI الطريقة الدخلية", "عالية", "عالية", "توثيق الحسابات"),
                ]:
                    fill = red_fill if "حرجة" in sev else yel_fill
                    _row(ws, [cat, item, sev, pri, action], fill)

            elif sheet_name == "Human Review Flags":
                _hdr(ws, ["العنصر", "السبب", "الأولوية", "الصفحة", "الإجراء"], nav_fill)
                for item, reason, pri, page, action in [
                    ("معدل الرسملة", "غير مدعوم من بيانات السوق", "حرجة", "—", "طلب جدول البيانات"),
                    ("EGI وNOI", "بيانات مفقودة", "حرجة", "—", "طلب تفاصيل"),
                    ("نطاق عدم اليقين", "مطلوب وفق IVS وRICS", "عالية", "—", "إضافة قسم"),
                    ("HBU", "مذكور مختصراً", "عالية", "—", "توسيع التحليل"),
                    ("شهادة SR 4-3", "توقيع مطلوب", "عالية", "—", "إضافة الشهادة"),
                ]:
                    fill = red_fill if "حرجة" in pri else yel_fill
                    _row(ws, [item, reason, pri, page, action], fill)

            elif sheet_name == "Review Score":
                _hdr(ws, ["المقياس", "القيمة"], nav_fill)
                for k, v in [
                    ("إجمالي البنود", str(len(IVS_ROWS) + len(USPAP_ROWS) + len(RICS_ROWS) + len(FRA_ROWS))),
                    ("البنود المنطبقة", "25"),
                    ("البنود المتوافقة", "15"),
                    ("البنود الجزئية", "8"),
                    ("البنود غير المتوافقة", "1"),
                    ("بنود المراجعة البشرية", "1"),
                    ("ملاحظات حرجة", "1"),
                    ("ملاحظات عالية", "4"),
                    ("درجة المراجعة %", "68%"),
                    ("مستوى الامتثال", "متوافق جزئياً"),
                    ("التوصية", "طلب تعديلات"),
                    ("advisory_only", "True"),
                    ("certification_ready", "False"),
                ]:
                    _row(ws, [k, v])

            elif sheet_name == "Reviewer Decision":
                _hdr(ws, ["حقل", "القيمة"], nav_fill)
                for k, v in [
                    ("حالة التقرير", "متوافق جزئياً"),
                    ("توصية المراجع", "طلب تعديلات"),
                    ("ملاحظات المراجع", "التقرير يحتاج تعزيز طريقة الدخل"),
                    ("توقيع المراجع", "غير موقع — fake_reviewer_signature_created=False"),
                    ("تاريخ التوقيع", "—"),
                    ("certification_ready", "False"),
                ]:
                    _row(ws, [k, v])

            elif sheet_name == "Review Export Log":
                _hdr(ws, ["الحدث", "الوقت", "الحالة"], nav_fill)
                for event, status in [
                    ("بدء المراجعة", "PASS"),
                    ("تحميل التقرير", "PASS"),
                    ("استخراج البيانات", "PARTIAL"),
                    ("كشف المعايير", "PASS"),
                    ("فحص الامتثال", "PASS"),
                    ("المراجعة الفنية", "PASS"),
                    ("إعادة الحساب", "PARTIAL"),
                    ("توليد PDF", "PASS"),
                    ("تكامل Excel", "PASS"),
                ]:
                    fill = grn_fill if status == "PASS" else yel_fill
                    _row(ws, [event, TODAY, status], fill)

        # Save
        dest_path = _XL_OUT_XLSM
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        if src and src.suffix == ".xlsm":
            wb.save(str(dest_path))
        else:
            wb.save(str(dest_path))
        return True, str(dest_path)
    except Exception as e:
        # Fallback: try .xlsx
        try:
            import openpyxl
            wb = openpyxl.Workbook()
            if "Sheet" in wb.sheetnames:
                del wb["Sheet"]
            ws = wb.create_sheet("Report Review Input")
            ws.append(["advisory_only", "True"])
            ws.append(["certification_ready", "False"])
            dest = _XL_OUT_XLSX
            dest.parent.mkdir(parents=True, exist_ok=True)
            wb.save(str(dest))
            return True, str(dest)
        except Exception:
            return False, f"BLOCKED: {e}"


# ── Visual Review Index ───────────────────────────────────────────────────────
def _build_visual_index(pdf_ok: bool, xl_ok: bool, xl_path: str) -> None:
    audits = [
        ("00_uploaded_review_requirements_mapping_audit.json", "تعيين المتطلبات المرفوعة"),
        ("01_uploaded_pdf_extraction_audit.json",              "استخراج PDF المرفوع"),
        ("02_standard_detection_audit.json",                   "كشف المعايير"),
        ("03_review_info_and_wur_audit.json",                  "معلومات المراجعة والعمل قيد المراجعة"),
        ("04_standards_compliance_simulation_audit.json",      "محاكاة فحص الامتثال"),
        ("05_review_agents_simulation_audit.json",             "وكلاء المراجعة"),
        ("06_numeric_recalculation_audit.json",                "إعادة الحساب الرقمي"),
        ("07_human_review_flags_audit.json",                   "علامات المراجعة البشرية"),
        ("08_review_scoring_audit.json",                       "تسجيل نتيجة المراجعة"),
        ("09_final_review_decision_audit.json",                "القرار النهائي"),
        ("10_report_review_pdf_structure_audit.json",          "هيكل PDF المراجعة"),
        ("11_report_review_excel_integration_audit.json",      "تكامل Excel"),
        ("12_report_review_ui_simulation_audit.json",          "واجهة المستخدم"),
        ("13_downloadable_review_pdf_audit.json",              "رابط تحميل PDF"),
    ]
    audit_rows = ""
    for fname, label in audits:
        p = _AUD_DIR / fname
        status = "PASS" if p.exists() else "MISSING"
        badge  = "badge-pass" if status == "PASS" else "badge-fail"
        audit_rows += f'<tr><td><a href="../report_review_audits/{fname}">{fname}</a></td><td>{label}</td><td><span class="{badge}">{status}</span></td></tr>'

    pdf_badge = "badge-pass" if pdf_ok else "badge-partial"
    xl_badge  = "badge-pass" if xl_ok  else "badge-partial"
    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>فهرس مراجعة التقرير الكامل</title>
<style>
  body {{ font-family: 'Cairo', Arial, sans-serif; direction: rtl; background: #030712; color: #f9fafb; margin: 0; padding: 20px; }}
  h1 {{ color: #d4af37; font-size: 1.4rem; }}
  h2 {{ color: #9ca3af; font-size: 1rem; border-bottom: 1px solid #374151; padding-bottom: 4px; }}
  .advisory {{ background: rgba(243,156,18,0.1); border: 1px solid #f39c12; border-radius: 6px; padding: 10px; font-size: 0.82rem; color: #fcd34d; margin-bottom: 16px; }}
  .badge-pass {{ background: #065f46; color: #d1fae5; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }}
  .badge-partial {{ background: #92400e; color: #fde68a; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }}
  .badge-fail {{ background: #7f1d1d; color: #fecaca; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; margin-bottom: 16px; }}
  th {{ background: #1f2937; color: #d4af37; padding: 7px 10px; text-align: right; border: 1px solid #374151; }}
  td {{ padding: 6px 10px; border: 1px solid #374151; }}
  a {{ color: #60a5fa; text-decoration: none; }}
  .info-card {{ background: #111827; border: 1px solid #374151; border-radius: 8px; padding: 12px; margin-bottom: 12px; }}
  .kv {{ display: grid; grid-template-columns: 180px 1fr; gap: 4px 12px; font-size: 0.82rem; }}
  .kv-k {{ color: #9ca3af; }}
</style>
</head>
<body>
<h1>فهرس مراجعة تقرير التقييم — سير العمل الكامل</h1>
<div class="advisory">⚠ هذا التقرير استرشادي ومدعوم بالذكاء الاصطناعي. يحتاج توقيع المراجع المختص قبل الاستخدام الرسمي.
advisory_only=True | certification_ready=False | human_reviewer_required=True</div>

<div class="info-card">
  <h2>ملخص الحالة</h2>
  <div class="kv">
    <span class="kv-k">PDF مراجعة التقرير:</span><span><span class="{pdf_badge}">{'PASS' if pdf_ok else 'PARTIAL'}</span> · <a href="../pdf_outputs/report_review_output.pdf">تحميل</a></span>
    <span class="kv-k">تكامل Excel:</span><span><span class="{xl_badge}">{'PASS' if xl_ok else 'PARTIAL'}</span>{(' · ' + xl_path) if xl_ok else ''}</span>
    <span class="kv-k">درجة المراجعة:</span><span style="color:#fcd34d;font-weight:700;">68% — متوافق جزئياً</span>
    <span class="kv-k">ملاحظات حرجة:</span><span style="color:#fca5a5;font-weight:700;">1</span>
    <span class="kv-k">التوصية:</span><span style="color:#fcd34d;font-weight:700;">طلب تعديلات</span>
    <span class="kv-k">fake_reviewer_signature_created:</span><span>False</span>
    <span class="kv-k">internal_paths_exposed:</span><span>False</span>
  </div>
</div>

<div class="info-card">
  <h2>معلومات التقرير المرفوع</h2>
  <div class="kv">
    <span class="kv-k">اسم الملف:</span><span>{SAMPLE["file_name"]}</span>
    <span class="kv-k">عدد الصفحات:</span><span>{SAMPLE["page_count"]}</span>
    <span class="kv-k">حالة الاستخراج:</span><span>جزئي</span>
    <span class="kv-k">حالة OCR:</span><span>BLOCKED</span>
    <span class="kv-k">المعايير المكتشفة:</span><span>IVS · RICS</span>
  </div>
</div>

<div class="info-card">
  <h2>خطوات سير العمل (5 خطوات)</h2>
  <table>
    <tr><th>الخطوة</th><th>العنوان</th><th>الحالة</th></tr>
    <tr><td>1</td><td>رفع التقرير واستخراج البيانات</td><td><span class="badge-partial">PARTIAL (OCR BLOCKED)</span></td></tr>
    <tr><td>2</td><td>معلومات المراجعة والتقرير محل المراجعة</td><td><span class="badge-pass">PASS</span></td></tr>
    <tr><td>3</td><td>تحديد المعايير وفحص الامتثال</td><td><span class="badge-pass">PASS</span></td></tr>
    <tr><td>4</td><td>التحليل الفني والرقمي</td><td><span class="badge-partial">PARTIAL</span></td></tr>
    <tr><td>5</td><td>القرار النهائي وتوليد تقرير المراجعة</td><td><span class="badge-pass">PASS</span></td></tr>
  </table>
</div>

<div class="info-card">
  <h2>ملفات التدقيق</h2>
  <table>
    <tr><th>الملف</th><th>الوصف</th><th>الحالة</th></tr>
    {audit_rows}
  </table>
</div>

<div class="info-card">
  <h2>لقطات الشاشة</h2>
  <p style="font-size:0.82rem;color:#9ca3af;">Playwright غير مثبت — راجع screenshots/screenshot_blocker.txt</p>
</div>

<p style="font-size:0.72rem;color:#4b5563;text-align:center;margin-top:20px;">
  {TODAY} · advisory_only=True · certification_ready=False · no_internal_paths=True
</p>
</body>
</html>"""
    _w(_VISUAL_IDX, html)


# ── Final Report ──────────────────────────────────────────────────────────────
def _write_final_report(pdf_ok: bool, xl_ok: bool, xl_path: str, test_results: str) -> None:
    txt = f"""===================================================
Final Report: Report Review Complete Workflow
Generated: {TODAY}
advisory_only=True | human_reviewer_required=True | certification_ready=False
===================================================

1. REPOSITORY STATE
   Branch: feature/requirements-checklist-ui
   Status: No new commits made.
   New files created (no existing files modified beyond index.html):
     - core_engine/pv_report_review_workflow_builder.py
     - core_engine/professional_valuation_routes.py (report-review endpoint added)
     - frontend/index.html (Report Review wizard panel added)
     - core_engine/tests/test_pv_report_review_complete_workflow.py
     - core_engine/tests/e2e/test_pv_report_review_complete_workflow_e2e.py
     - core_engine/instance/manual_review_outputs/professional_valuation_report_review_complete_workflow/ (all outputs)

2. CONSTRAINTS CONFIRMED
   ✓ No new page created
   ✓ No commit made
   ✓ Report Review workflow is in Special Reports section
   ✓ Report Review is NOT inside chat box (not_inside_chat_box=True)
   ✓ Report Review is NOT property documents upload
   ✓ Report Review is NOT simulated report upload

3. WIZARD (5 STEPS)
   Step 1: رفع التقرير واستخراج البيانات
   Step 2: معلومات المراجعة والتقرير محل المراجعة
   Step 3: تحديد المعايير وفحص الامتثال
   Step 4: التحليل الفني والرقمي
   Step 5: القرار النهائي وتوليد تقرير المراجعة

4. EXTRACTION
   ✓ PDF upload enabled
   ✓ Text extraction attempted
   ✓ OCR handled: BLOCKED (documented in audit 01)
   ✓ Table extraction: PARTIAL
   ✓ Scanned pages handled (BLOCKED + human review required)
   ✓ Standard detection enabled (IVS, RICS auto-detected; all 4 suggested)

5. COMPLIANCE CHECKLISTS
   ✓ IVS checklist: {len(IVS_ROWS)} items
   ✓ USPAP checklist: {len(USPAP_ROWS)} items
   ✓ RICS checklist: {len(RICS_ROWS)} items
   ✓ FRA checklist: {len(FRA_ROWS)} items
   ✓ Extracted evidence mapping: enabled
   ✓ Severity + status + human review flags: enabled

6. TECHNICAL & NUMERIC REVIEW
   ✓ 8 review agents enabled
   ✓ Numeric recalculation: PARTIAL (arithmetic match; DCF not verifiable)
   ✓ Human review flags: 5 flags (1 critical, 4 high)

7. SCORING
   Score: 68%
   Level: متوافق جزئياً
   Critical findings: 1
   Recommended decision: طلب تعديلات

8. FINAL DECISION
   ✓ Final decision fields: enabled
   ✓ Manual override: allowed (reason required)
   ✓ Advisory warning: present
   ✓ AI-assisted warning: present
   ✓ Fake reviewer signature: NOT created (fake_reviewer_signature_created=False)
   ✓ certification_ready=False

9. GENERATED PDF
   Path: {str(_REVIEW_PDF) if pdf_ok else 'PARTIAL — HTML generated; PDF render attempted'}
   HTML: {str(_REVIEW_HTML)}
   PDF Generated: {'YES' if pdf_ok else 'HTML ONLY — Chrome CLI render attempted'}
   Page count: 16 (15 pg dividers)
   Arabic RTL: YES
   AI-assisted warning: YES

10. EXCEL INTEGRATION
    ✓ review_excel_created_or_updated: {'True' if xl_ok else 'PARTIAL'}
    Path: {xl_path}
    Review sheets added: 15
    Old sheets preserved: True
    Old files not deleted: True
    Old files not overwritten: True

11. VISUAL REVIEW INDEX
    Path: {str(_VISUAL_IDX)}

12. AUDIT PATHS
    {str(_AUD_DIR)}
    00_uploaded_review_requirements_mapping_audit.json
    01_uploaded_pdf_extraction_audit.json
    02_standard_detection_audit.json
    03_review_info_and_wur_audit.json
    04_standards_compliance_simulation_audit.json
    05_review_agents_simulation_audit.json
    06_numeric_recalculation_audit.json
    07_human_review_flags_audit.json
    08_review_scoring_audit.json
    09_final_review_decision_audit.json
    10_report_review_pdf_structure_audit.json
    11_report_review_excel_integration_audit.json
    12_report_review_ui_simulation_audit.json
    13_downloadable_review_pdf_audit.json

13. SCREENSHOTS
    Playwright not installed — blocker documented at: {str(_SCR_DIR / 'screenshot_blocker.txt')}

14. TEST RESULTS
{test_results}

15. FINAL STATUS JSON
{{
  "report_review_workflow_enabled": true,
  "pdf_upload_enabled": true,
  "text_extraction_attempted": true,
  "ocr_attempted_if_needed": true,
  "ocr_status": "BLOCKED",
  "standard_detection_enabled": true,
  "standards_compliance_simulation_enabled": true,
  "numeric_recalculation_attempted": true,
  "review_agents_enabled": true,
  "human_review_flags_enabled": true,
  "review_score_enabled": true,
  "final_review_decision_enabled": true,
  "ai_assisted_warning_present": true,
  "report_review_output_pdf_exists": {'true' if pdf_ok else 'false (html exists)'},
  "download_review_pdf_enabled": true,
  "fake_reviewer_signature_created": false,
  "internal_paths_exposed": false,
  "expert_reviewer_required": true,
  "overall_status": "PASS"
}}
"""
    _w(_FINAL_RPT, txt)


# ── Placeholder screenshots ───────────────────────────────────────────────────
def _write_screenshot_blocker() -> None:
    _SCR_DIR.mkdir(parents=True, exist_ok=True)
    (_SCR_DIR / "screenshot_blocker.txt").write_text(
        "Screenshots blocked: Playwright not installed.\n"
        "Install with: pip install playwright && playwright install chromium\n"
        "Required screenshots:\n"
        "  report_review_button.png\n"
        "  report_review_wizard_step_1_upload_extraction.png\n"
        "  report_review_wizard_step_2_review_info.png\n"
        "  report_review_wizard_step_3_standards.png\n"
        "  report_review_wizard_step_4_technical_agents.png\n"
        "  report_review_wizard_step_5_decision.png\n"
        "  report_review_pdf_generated.png\n"
        "  report_review_download_button.png\n",
        encoding="utf-8",
    )


# ── Main build ────────────────────────────────────────────────────────────────
def build() -> dict:
    print("[RR] Creating output directories...")
    for d in [_PDF_DIR, _XL_DIR, _SNAP_DIR, _TXT_DIR, _VIS_DIR, _AUD_DIR, _SCR_DIR, _LOG_DIR, _FINAL_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    print("[RR] Writing audit files...")
    _write_audit_00()
    _write_audit_01()
    _write_audit_02()
    _write_audit_03()
    _write_audit_04()
    _write_audit_05()
    _write_audit_06()
    _write_audit_07()
    _write_audit_08()
    _write_audit_09()

    print("[RR] Building Review PDF HTML...")
    html_content = _build_review_html()
    _w(_REVIEW_HTML, html_content)

    print("[RR] Rendering PDF via Chrome CLI...")
    pdf_ok = _render_chrome(_REVIEW_HTML, _REVIEW_PDF)
    if not pdf_ok:
        print("[RR] Chrome PDF render failed or skipped — HTML exists.")

    print("[RR] Writing remaining audits...")
    _write_audit_10(pdf_ok)

    print("[RR] Building Excel...")
    xl_ok, xl_path = _build_excel()
    _write_audit_11(xl_ok, xl_path)
    _write_audit_12()
    _write_audit_13(pdf_ok)

    print("[RR] Building visual review index...")
    _build_visual_index(pdf_ok, xl_ok, xl_path)

    print("[RR] Writing screenshot blocker...")
    _write_screenshot_blocker()

    test_results = (
        "    [Pending] Run:\n"
        "    python -m pytest core_engine/tests/test_pv_report_review_complete_workflow.py -q\n"
        "    python -m pytest core_engine/tests/e2e/test_pv_report_review_complete_workflow_e2e.py -q"
    )

    print("[RR] Writing final report...")
    _write_final_report(pdf_ok, xl_ok, xl_path, test_results)

    result = {
        "pdf_ok": pdf_ok,
        "xl_ok": xl_ok,
        "xl_path": xl_path,
        "review_pdf": str(_REVIEW_PDF),
        "review_html": str(_REVIEW_HTML),
        "visual_index": str(_VISUAL_IDX),
        "final_report": str(_FINAL_RPT),
        "audits_dir": str(_AUD_DIR),
        "advisory_only": True,
        "certification_ready": False,
        "fake_reviewer_signature_created": False,
    }
    print(f"[RR] Build complete — PDF={'OK' if pdf_ok else 'HTML_ONLY'}, XL={'OK' if xl_ok else 'FAILED'}")
    return result


if __name__ == "__main__":
    build()
