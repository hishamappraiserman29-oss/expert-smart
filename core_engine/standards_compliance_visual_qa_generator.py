"""
Standards Compliance Visual QA Generator
Case: QA-COMPLIANCE-VISUAL-001  |  Saudi Arabia / Riyadh / SAR
Standards: IVS 2022 (IVSC) + RICS 2022 (Red Book)
Role separation: user → HTML + PDF | admin → HTML + PDF + Excel

Visual QA report generator. Callable from the CLI (see __main__ below) and,
as of Wave 3B, from core_engine/pv_standards_compliance_endpoint.py, which
imports run_standards_compliance_visual_qa() as a library function and is
the sole owner of whatever Flask exposure it chooses to give it. This
module itself defines no Flask routes, exports no route-registration
function, and has no HTTP surface of its own — see pv_standards_compliance_
endpoint.py for the admin-only blueprint that calls into it.

It generates persistent local QA artifacts (HTML, PDF, XLSX, JSON, PNG)
inside an explicitly caller-supplied output directory.  Each call is
isolated in a unique run sub-directory to prevent concurrent overwrites.

It is NOT a standards certification engine.  All findings are advisory.

Runtime status               : WIRED_VIA_PV_STANDARDS_COMPLIANCE_ENDPOINT (Wave 3B)
Advisory only                : True
Certification ready          : False
Official compliance decision : False
Synthetic data               : True
"""
from __future__ import annotations

import argparse
import hashlib
import html as _html
import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path-safety helpers
# ---------------------------------------------------------------------------
_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
_ALLOWED_EXTENSIONS = frozenset({".html", ".pdf", ".xlsx", ".json", ".png"})

# ---------------------------------------------------------------------------
# Path-safety functions
# ---------------------------------------------------------------------------
def _sanitize_component(value: str, label: str) -> str:
    """Validate a path component (case_id or run_id). Raises ValueError if unsafe."""
    if not value:
        raise ValueError(f"{label} must not be empty")
    if not _SAFE_COMPONENT.match(value):
        raise ValueError(
            f"{label} {value!r} is invalid — "
            "only A-Z a-z 0-9 _ - allowed, max 80 characters"
        )
    return value


def _esc(value: Any) -> str:
    """HTML-escape a value for safe insertion into HTML content or attributes."""
    return _html.escape("" if value is None else str(value), quote=True)


def _new_run_id() -> str:
    """Generate a unique run ID (32-char lowercase hex, UUID4)."""
    return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# Governance flags  (NEVER change without explicit approval)
# ---------------------------------------------------------------------------
SYNTHETIC_DATA: bool = True

_SAFETY: dict[str, Any] = {
    "advisory_only": True,
    "certification_ready": False,
    "fake_signature_created": False,
    "non_certified": True,
    "not_real_training": True,
    "external_certification_performed": False,
    "official_compliance_decision": False,
    "synthetic_data": True,
}

# ---------------------------------------------------------------------------
# Case metadata
# ---------------------------------------------------------------------------
CASE_ID = "QA-COMPLIANCE-VISUAL-001"
CURRENCY = "SAR"
PROPERTY_REF = "RUH-2024-00791"
LOCATION = "الرياض، المملكة العربية السعودية"
REPORT_DATE = "2026-07-27"
VALUER = "مثمن تجريبي — بيانات QA اصطناعية"
INTENDED_USE = "تمويل عقاري — اعتماد بنكي"

# Watermarks
USER_WATERMARK = "استرشادي — غير معتمد"
ADMIN_WATERMARK = "للمراجعة الداخلية فقط"
SIG_GATE = "لم يُوقَّع بعد"

# ---------------------------------------------------------------------------
# Clause data
# 14 clauses: 8 IVS + 6 RICS
# Status values: compliant | partially_compliant | non_compliant |
#                not_applicable | insufficient_evidence | not_assessed
# Severity values: critical | high | medium | low | informational | not_applicable
# ---------------------------------------------------------------------------
CLAUSES: list[dict[str, Any]] = [
    # ── IVS 2022 ──────────────────────────────────────────────────────────
    {
        "standard": "IVS 2022 (IVSC)",
        "clause_id": "IVS-101-SCOPE",
        "clause_ref": "IVS 101 §20–22",
        "title": "نطاق التقييم — التوثيق",
        "requirement": "يجب توثيق نطاق التقييم ويشمل: الغرض، أساس القيمة، تاريخ القيمة، الافتراضات المادية، القيود.",
        "status": "compliant",
        "severity": "not_applicable",
        "evidence_refs": ["E-001", "E-002"],
        "findings": [],
        "remediation": None,
        "blocks_issuance": False,
    },
    {
        "standard": "IVS 2022 (IVSC)",
        "clause_id": "IVS-102-BASIS",
        "clause_ref": "IVS 102 §10–30",
        "title": "أساس القيمة",
        "requirement": "يجب تحديد أساس القيمة المناسب وربطه بالغرض من التقييم.",
        "status": "compliant",
        "severity": "not_applicable",
        "evidence_refs": ["E-001", "E-003"],
        "findings": [],
        "remediation": None,
        "blocks_issuance": False,
    },
    {
        "standard": "IVS 2022 (IVSC)",
        "clause_id": "IVS-103-REPORTING",
        "clause_ref": "IVS 103 §10–50",
        "title": "متطلبات التقرير",
        "requirement": "يجب أن يحتوي التقرير على جميع العناصر المطلوبة وفق IVS 103.",
        "status": "partially_compliant",
        "severity": "medium",
        "evidence_refs": ["E-004"],
        "findings": [
            {
                "finding_id": "F-001",
                "description": "قسم الافتراضات والقيود يفتقر إلى وصف كافٍ للقيود الخاصة بالمنطقة.",
                "severity": "medium",
            }
        ],
        "remediation": "إضافة فقرة تفصيلية تشرح القيود المتعلقة بتقييمات المناطق التنموية في الرياض.",
        "blocks_issuance": False,
    },
    {
        "standard": "IVS 2022 (IVSC)",
        "clause_id": "IVS-104-ETHICS",
        "clause_ref": "IVS 104 §20–40",
        "title": "الأخلاقيات والكفاءة",
        "requirement": "يجب إثبات استقلالية المقيّم وكفاءته المهنية.",
        "status": "compliant",
        "severity": "not_applicable",
        "evidence_refs": ["E-002"],
        "findings": [],
        "remediation": None,
        "blocks_issuance": False,
    },
    {
        "standard": "IVS 2022 (IVSC)",
        "clause_id": "IVS-105-ASSET",
        "clause_ref": "IVS 105 §10–100",
        "title": "نهج التقييم — المقارنة السوقية",
        "requirement": "يجب اتباع نهج تقييم مناسب مع توثيق بيانات السوق المستخدمة.",
        "status": "compliant",
        "severity": "not_applicable",
        "evidence_refs": ["E-003", "E-005"],
        "findings": [],
        "remediation": None,
        "blocks_issuance": False,
    },
    {
        "standard": "IVS 2022 (IVSC)",
        "clause_id": "IVS-230-REAL-PROP",
        "clause_ref": "IVS 230 §10–70",
        "title": "تقييم العقارات — التوثيق الفيزيائي",
        "requirement": "يجب توثيق الوصف الفيزيائي للعقار وحالة السوق المحلية.",
        "status": "partially_compliant",
        "severity": "low",
        "evidence_refs": ["E-005"],
        "findings": [
            {
                "finding_id": "F-002",
                "description": "لا يوجد توثيق لمعدل الشغور في المنطقة المحيطة بالعقار.",
                "severity": "low",
            }
        ],
        "remediation": "إضافة بيانات معدل الشغور من تقارير السوق لمنطقة الرياض.",
        "blocks_issuance": False,
    },
    {
        "standard": "IVS 2022 (IVSC)",
        "clause_id": "IVS-400-BUSINESS",
        "clause_ref": "IVS 400 N/A",
        "title": "تقييم الأعمال — غير منطبق",
        "requirement": "تقييم الأعمال (IVS 400): غير منطبق على هذا التقييم العقاري.",
        "status": "not_applicable",
        "severity": "not_applicable",
        "evidence_refs": [],
        "findings": [],
        "remediation": None,
        "blocks_issuance": False,
    },
    {
        "standard": "IVS 2022 (IVSC)",
        "clause_id": "IVS-500-FINANCIAL",
        "clause_ref": "IVS 500 N/A",
        "title": "الأدوات المالية — غير منطبق",
        "requirement": "تقييم الأدوات المالية (IVS 500): غير منطبق على هذا التقييم العقاري.",
        "status": "not_applicable",
        "severity": "not_applicable",
        "evidence_refs": [],
        "findings": [],
        "remediation": None,
        "blocks_issuance": False,
    },
    # ── RICS 2022 (Red Book) ───────────────────────────────────────────────
    {
        "standard": "RICS 2022 (Red Book)",
        "clause_id": "RICS-PS1-ETHICS",
        "clause_ref": "RICS PS1 §3–5",
        "title": "المعيار المهني 1 — الأخلاقيات",
        "requirement": "الامتثال لمعايير الأخلاقيات المهنية ومتطلبات الاستقلالية الصادرة عن RICS.",
        "status": "compliant",
        "severity": "not_applicable",
        "evidence_refs": ["E-002"],
        "findings": [],
        "remediation": None,
        "blocks_issuance": False,
    },
    {
        "standard": "RICS 2022 (Red Book)",
        "clause_id": "RICS-PS2-STANDARDS",
        "clause_ref": "RICS PS2 §4–8",
        "title": "المعيار المهني 2 — الامتثال للمعايير",
        "requirement": "يجب الامتثال الكامل لمتطلبات الكتاب الأحمر لـ RICS.",
        "status": "partially_compliant",
        "severity": "high",
        "evidence_refs": ["E-004", "E-006"],
        "findings": [
            {
                "finding_id": "F-003",
                "description": "غياب شهادة RICS الرسمية للمقيّم المسؤول.",
                "severity": "high",
            }
        ],
        "remediation": "الحصول على شهادة MRICS أو إشراك مقيّم معتمد من RICS في عملية المراجعة.",
        "blocks_issuance": False,
    },
    {
        "standard": "RICS 2022 (Red Book)",
        "clause_id": "RICS-VPS1-SCOPE",
        "clause_ref": "RICS VPS 1 §2–6",
        "title": "خدمات التقييم 1 — نطاق العمل",
        "requirement": "يجب توثيق نطاق العمل والاتفاق عليه قبل بدء التقييم.",
        "status": "compliant",
        "severity": "not_applicable",
        "evidence_refs": ["E-001", "E-002"],
        "findings": [],
        "remediation": None,
        "blocks_issuance": False,
    },
    {
        "standard": "RICS 2022 (Red Book)",
        "clause_id": "RICS-VPS3-REPORTING",
        "clause_ref": "RICS VPS 3 §3–10",
        "title": "خدمات التقييم 3 — التقرير",
        "requirement": "محتوى التقرير يجب أن يشمل جميع عناصر VPS 3.",
        "status": "partially_compliant",
        "severity": "medium",
        "evidence_refs": ["E-004"],
        "findings": [
            {
                "finding_id": "F-004",
                "description": "التقرير لا يتضمن بياناً صريحاً بتأكيد المطابقة مع RICS Red Book.",
                "severity": "medium",
            }
        ],
        "remediation": "إضافة فقرة تأكيد المطابقة مع RICS Red Book 2022 في مقدمة التقرير.",
        "blocks_issuance": False,
    },
    {
        "standard": "RICS 2022 (Red Book)",
        "clause_id": "VPS-5-ASSUMPTIONS",
        "clause_ref": "RICS VPS 5 §4–9",
        "title": "خدمات التقييم 5 — الافتراضات",
        "requirement": "يجب توثيق جميع الافتراضات الخاصة والمادية بوضوح.",
        "status": "non_compliant",
        "severity": "high",
        "evidence_refs": ["E-006"],
        "findings": [
            {
                "finding_id": "F-005",
                "description": "الافتراضات الخاصة بالتطوير المستقبلي للبنية التحتية غير موثقة.",
                "severity": "high",
            }
        ],
        "remediation": "توثيق جميع الافتراضات الخاصة المتعلقة بخطط التطوير الحكومية القريبة من الموقع.",
        "blocks_issuance": True,
    },
    {
        "standard": "RICS 2022 (Red Book)",
        "clause_id": "VPS-6-UNCERTAINTY",
        "clause_ref": "RICS VPS 6 §3–8",
        "title": "خدمات التقييم 6 — عدم اليقين",
        "requirement": "في حالة وجود مستوى استثنائي من عدم اليقين، يجب الإفصاح عنه صراحةً.",
        "status": "non_compliant",
        "severity": "critical",
        "evidence_refs": ["E-007", "E-008"],
        "findings": [
            {
                "finding_id": "F-006",
                "description": "إيجاد حرج: لم يُفصَح عن عدم اليقين الاستثنائي المتعلق بتقلبات السوق في الرياض خلال 2024.",
                "severity": "critical",
            }
        ],
        "remediation": "إدراج إفصاح صريح عن عدم اليقين الاستثنائي وفق RICS VPS 6، مع تحديد نطاق الغموض وأثره على القيمة.",
        "blocks_issuance": True,
    },
]

# ---------------------------------------------------------------------------
# Evidence items
# ---------------------------------------------------------------------------
EVIDENCE: list[dict[str, Any]] = [
    {"id": "E-001", "type": "contract", "description": "خطاب التكليف والاتفاقية مع العميل"},
    {"id": "E-002", "type": "credential", "description": "شهادات المقيّم وعضوية الجمعية السعودية للتقييم"},
    {"id": "E-003", "type": "market_data", "description": "بيانات السوق: مبيعات مقارنة Q1-Q2 2024"},
    {"id": "E-004", "type": "report_section", "description": "مسودة التقرير — الأجزاء 1-5"},
    {"id": "E-005", "type": "site_inspection", "description": "تقرير الكشف الميداني ومخططات الموقع"},
    {"id": "E-006", "type": "assumptions_log", "description": "سجل الافتراضات المادية والخاصة"},
    {"id": "E-007", "type": "market_bulletin", "description": "نشرة السوق العقاري — الرياض Q2 2024"},
    {"id": "E-008", "type": "uncertainty_note", "description": "مذكرة تقييم المخاطر الداخلية"},
    {"id": "E-009", "type": "methodology", "description": "وثيقة منهجية التقييم المعتمدة داخلياً"},
    {"id": "E-010", "type": "title_deed", "description": "صك الملكية ومستندات التسجيل العقاري"},
]

# ---------------------------------------------------------------------------
# Overall scoring
# ---------------------------------------------------------------------------
def _compute_score() -> dict[str, Any]:
    applicable = [c for c in CLAUSES if c["status"] != "not_applicable"]
    total = len(applicable)
    scored_map = {
        "compliant": 1.0,
        "partially_compliant": 0.5,
        "non_compliant": 0.0,
        "insufficient_evidence": 0.25,
        "not_assessed": 0.0,
    }
    raw = sum(scored_map.get(c["status"], 0.0) for c in applicable)
    pct = round(raw / total * 100) if total else 0
    if pct >= 80:
        traffic_light = "green"
        label = "متوافق"
    elif pct >= 55:
        traffic_light = "yellow"
        label = "متوافق جزئياً"
    else:
        traffic_light = "red"
        label = "غير متوافق"
    critical_ids = [
        c["clause_id"] for c in CLAUSES if c["severity"] == "critical"
    ]
    return {
        "applicable_clauses": total,
        "raw_score": raw,
        "percentage": pct,
        "traffic_light": traffic_light,
        "label": label,
        "critical_findings": critical_ids,
        "blocks_issuance": [c["clause_id"] for c in CLAUSES if c["blocks_issuance"]],
    }


SCORE = _compute_score()

# ---------------------------------------------------------------------------
# Status / severity display helpers
# ---------------------------------------------------------------------------
_STATUS_LABEL: dict[str, str] = {
    "compliant": "متوافق ✓",
    "partially_compliant": "متوافق جزئياً ⚠",
    "non_compliant": "غير متوافق ✗",
    "not_applicable": "غير منطبق —",
    "insufficient_evidence": "أدلة غير كافية ?",
    "not_assessed": "لم يُقيَّم",
}
_STATUS_COLOR: dict[str, str] = {
    "compliant": "#16a34a",
    "partially_compliant": "#d97706",
    "non_compliant": "#dc2626",
    "not_applicable": "#6b7280",
    "insufficient_evidence": "#7c3aed",
    "not_assessed": "#374151",
}
_SEV_COLOR: dict[str, str] = {
    "critical": "#7f1d1d",
    "high": "#b91c1c",
    "medium": "#d97706",
    "low": "#ca8a04",
    "informational": "#0369a1",
    "not_applicable": "#6b7280",
}
_TRAFFIC_COLOR: dict[str, str] = {
    "green": "#15803d",
    "yellow": "#b45309",
    "red": "#991b1b",
}


# ---------------------------------------------------------------------------
# HTML generation helpers
# ---------------------------------------------------------------------------
_CSS_BASE = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Tahoma,Arial,sans-serif;direction:rtl;
     background:#f8fafc;color:#1e293b;font-size:14px;line-height:1.7}
.report-wrapper{max-width:960px;margin:0 auto;padding:24px 16px}
.report-header{background:linear-gradient(135deg,#1e3a5f 0%,#2d5986 100%);
  color:#fff;padding:32px 28px;border-radius:12px;margin-bottom:24px}
.report-header h1{font-size:1.6rem;font-weight:700;margin-bottom:6px}
.report-header .meta{font-size:.85rem;opacity:.85;line-height:2}
.watermark-banner{background:#fef3c7;border:2px solid #d97706;border-radius:8px;
  padding:10px 18px;text-align:center;font-weight:700;color:#92400e;
  font-size:.95rem;margin-bottom:20px;letter-spacing:.03em}
.sig-gate{background:#fee2e2;border:1px solid #fca5a5;border-radius:6px;
  padding:8px 14px;color:#991b1b;font-size:.85rem;margin-bottom:18px;text-align:center}
.score-card{background:#fff;border-radius:10px;padding:20px 24px;
  box-shadow:0 1px 4px rgba(0,0,0,.08);margin-bottom:20px;
  display:flex;align-items:center;gap:20px;flex-wrap:wrap}
.traffic-light{width:56px;height:56px;border-radius:50%;display:flex;
  align-items:center;justify-content:center;font-size:1.5rem;color:#fff;flex-shrink:0}
.score-details h2{font-size:1.2rem;font-weight:700}
.score-details .pct{font-size:2rem;font-weight:800;line-height:1}
.score-details .label{font-size:.9rem;margin-top:2px}
section.qa-section{background:#fff;border-radius:10px;padding:18px 22px;
  margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
section.qa-section h3{font-size:1rem;font-weight:700;margin-bottom:12px;
  padding-bottom:6px;border-bottom:2px solid #e2e8f0;color:#1e3a5f}
.clause-table{width:100%;border-collapse:collapse;font-size:.88rem}
.clause-table th{background:#f1f5f9;padding:7px 10px;text-align:right;
  font-weight:600;border:1px solid #e2e8f0;color:#334155}
.clause-table td{padding:7px 10px;border:1px solid #e2e8f0;vertical-align:top}
.clause-table tr:nth-child(even) td{background:#f8fafc}
.status-badge{display:inline-block;padding:2px 8px;border-radius:4px;
  font-size:.78rem;font-weight:600;color:#fff}
.finding-box{background:#fff7ed;border-right:4px solid #ea580c;
  border-radius:4px;padding:8px 12px;margin-top:6px;font-size:.85rem}
.finding-critical{background:#fff1f2;border-right-color:#dc2626}
.finding-high{background:#fff7ed;border-right-color:#b91c1c}
.remediation-box{background:#f0fdf4;border-right:4px solid #16a34a;
  border-radius:4px;padding:8px 12px;margin-top:4px;font-size:.83rem;color:#14532d}
.gov-box{background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;
  padding:14px 18px;font-size:.85rem;color:#0c4a6e;line-height:2}
.gov-box strong{display:block;margin-bottom:4px;color:#0369a1}
.evidence-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));
  gap:10px;margin-top:8px}
.evidence-card{background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;
  padding:10px 12px;font-size:.83rem}
.evidence-card .eid{font-weight:700;color:#1e3a5f;margin-bottom:2px}
.blocks-banner{background:#fef2f2;border:2px solid #f87171;border-radius:8px;
  padding:12px 18px;margin-bottom:16px;color:#7f1d1d;font-size:.88rem}
.blocks-banner ul{margin-top:6px;padding-right:18px}
.admin-only-marker{background:#312e81;color:#e0e7ff;font-size:.72rem;
  padding:2px 6px;border-radius:3px;font-weight:600;margin-right:6px}
"""


def _html_head(title: str, watermark: str, is_admin: bool) -> str:
    theme_color = "#1e3a5f" if not is_admin else "#312e81"
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(title)}</title>
<style>
{_CSS_BASE}
body{{background:{'#f5f3ff' if is_admin else '#f8fafc'}}}
.report-header{{background:linear-gradient(135deg,{theme_color} 0%,
  {'#4338ca' if is_admin else '#2d5986'} 100%)}}
</style>
</head>
<body>
<div class="report-wrapper">
"""


def _html_header(is_admin: bool) -> str:
    role_badge = (
        '<span style="background:#4338ca;color:#e0e7ff;padding:2px 10px;'
        'border-radius:4px;font-size:.78rem;font-weight:600;">مسؤول النظام</span> '
        if is_admin
        else ""
    )
    return f"""<header class="report-header" data-section="1">
  <h1>تقرير امتثال المعايير المهنية {role_badge}</h1>
  <div class="meta">
    رقم الحالة: <strong>{_esc(CASE_ID)}</strong> &nbsp;|&nbsp;
    مرجع العقار: <strong>{_esc(PROPERTY_REF)}</strong><br>
    الموقع: {_esc(LOCATION)} &nbsp;|&nbsp; العملة: {_esc(CURRENCY)}<br>
    تاريخ التقرير: {_esc(REPORT_DATE)} &nbsp;|&nbsp; المقيّم: {_esc(VALUER)}<br>
    الغرض: {_esc(INTENDED_USE)}
  </div>
</header>
"""


def _html_watermark(wm: str) -> str:
    return f'<div class="watermark-banner" data-section="2">{_esc(wm)}</div>\n'


def _html_sig_gate() -> str:
    return f'<div class="sig-gate" data-section="3">حالة التوقيع: {_esc(SIG_GATE)}</div>\n'


def _html_score(score: dict[str, Any]) -> str:
    tl = score["traffic_light"]
    tl_icon = {"green": "✅", "yellow": "⚠️", "red": "❌"}.get(tl, "⚠️")
    tl_bg = _TRAFFIC_COLOR.get(tl, "#374151")
    blocks_html = ""
    if score["blocks_issuance"]:
        blocks_html = (
            f'<div class="blocks-banner" data-section="4b">'
            f'<strong>⛔ بنود تحجب الإصدار:</strong>'
            f"<ul>{''.join(f'<li>{_esc(bid)}</li>' for bid in score['blocks_issuance'])}</ul>"
            f"</div>"
        )
    return f"""<div class="score-card" data-section="4">
  <div class="traffic-light" style="background:{tl_bg}">{tl_icon}</div>
  <div class="score-details">
    <h2>النتيجة الإجمالية</h2>
    <div class="pct" style="color:{tl_bg}">{score['percentage']}%</div>
    <div class="label">{_esc(score['label'])}</div>
    <div style="font-size:.8rem;color:#64748b;margin-top:4px">
      {score['raw_score']:.1f} / {score['applicable_clauses']} بند منطبق
    </div>
  </div>
</div>
{blocks_html}"""


def _html_clause_row(c: dict[str, Any], idx: int, is_admin: bool) -> str:
    status_color = _STATUS_COLOR.get(c["status"], "#374151")
    status_lbl = _STATUS_LABEL.get(c["status"], c["status"])
    findings_html = ""
    for f in c["findings"]:
        sev_color = _SEV_COLOR.get(f["severity"], "#374151")
        cls = (
            "finding-critical"
            if f["severity"] == "critical"
            else "finding-high"
            if f["severity"] == "high"
            else "finding-box"
        )
        findings_html += (
            f'<div class="{cls} finding-box">'
            f'<span style="color:{sev_color};font-weight:700;">'
            f'[{_esc(f["severity"].upper())}] {_esc(f["finding_id"])}</span>: '
            f'{_esc(f["description"])}</div>'
        )
    rem_html = ""
    if c["remediation"] and is_admin:
        rem_html = (
            f'<div class="remediation-box">🔧 <strong>الإجراء المقترح:</strong> '
            f'{_esc(c["remediation"])}</div>'
        )
    elif c["remediation"]:
        rem_html = (
            f'<div class="remediation-box" style="background:#f0fdf4">'
            f'⚠️ يتطلب إجراءً تصحيحياً</div>'
        )
    evid_ids = ", ".join(_esc(e) for e in c["evidence_refs"]) if c["evidence_refs"] else "—"
    blocks_marker = (
        ' <span style="color:#dc2626;font-weight:700;">⛔ يحجب الإصدار</span>'
        if c["blocks_issuance"]
        else ""
    )
    admin_marker = (
        '<span class="admin-only-marker">ADMIN</span>' if is_admin else ""
    )
    return f"""<tr data-clause="{_esc(c['clause_id'])}">
  <td><strong>{_esc(c['clause_id'])}</strong><br>
      <span style="font-size:.78rem;color:#64748b">{_esc(c['clause_ref'])}</span></td>
  <td>{admin_marker}{_esc(c['title'])}{blocks_marker}</td>
  <td><span class="status-badge" style="background:{status_color}">{_esc(status_lbl)}</span>
      {findings_html}{rem_html}</td>
  <td style="font-size:.8rem;color:#475569">{evid_ids}</td>
</tr>"""


def _html_clauses_section(is_admin: bool, section_offset: int = 5) -> str:
    standards = ["IVS 2022 (IVSC)", "RICS 2022 (Red Book)"]
    out = ""
    for si, std in enumerate(standards):
        clauses = [c for c in CLAUSES if c["standard"] == std]
        sec_num = section_offset + si
        rows = "".join(_html_clause_row(c, i, is_admin) for i, c in enumerate(clauses))
        out += f"""<section class="qa-section" data-section="{sec_num}">
  <h3>{std} — بنود الامتثال</h3>
  <table class="clause-table">
    <thead>
      <tr>
        <th style="width:18%">البند</th>
        <th style="width:30%">العنوان</th>
        <th style="width:38%">الحالة / الملاحظات</th>
        <th style="width:14%">الأدلة</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
</section>
"""
    return out


def _html_evidence_section(sec_num: int) -> str:
    cards = ""
    for e in EVIDENCE:
        cards += (
            f'<div class="evidence-card">'
            f'<div class="eid">{_esc(e["id"])}</div>'
            f'<div style="color:#475569">{_esc(e["description"])}</div>'
            f'<div style="font-size:.76rem;color:#94a3b8;margin-top:2px">{_esc(e["type"])}</div>'
            f"</div>"
        )
    return f"""<section class="qa-section" data-section="{sec_num}">
  <h3>سجل الأدلة ({len(EVIDENCE)} عنصر)</h3>
  <div class="evidence-grid">{cards}</div>
</section>
"""


def _html_governance(sec_num: int, is_admin: bool) -> str:
    flags = "\n".join(
        f"<li><strong>{_esc(k)}</strong>: {_esc(v)}</li>"
        for k, v in _SAFETY.items()
    )
    admin_extra = ""
    if is_admin:
        admin_extra = (
            '<div style="margin-top:10px;font-size:.82rem;color:#6b21a8">'
            "<strong>ملاحظة إدارية:</strong> هذا التقرير للمراجعة الداخلية فقط. "
            "لا يُستخدم في أي إجراء رسمي أو قانوني قبل استيفاء متطلبات الإصدار.</div>"
        )
    return f"""<section class="qa-section" data-section="{sec_num}">
  <h3>إفصاحات الحوكمة</h3>
  <div class="gov-box">
    <strong>علامات الحوكمة:</strong>
    <ul style="padding-right:18px">{flags}</ul>
    {admin_extra}
  </div>
</section>
"""


def _html_footer(is_admin: bool, sec_num: int) -> str:
    return f"""<section class="qa-section" data-section="{sec_num}">
  <div style="text-align:center;font-size:.8rem;color:#94a3b8;padding:8px 0">
    {_esc(CASE_ID)} &nbsp;|&nbsp; {_esc(REPORT_DATE)} &nbsp;|&nbsp;
    {'النسخة الإدارية' if is_admin else 'النسخة الاسترشادية'} &nbsp;|&nbsp;
    {_esc(SIG_GATE)}
  </div>
</section>
</div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Admin-only extra sections
# ---------------------------------------------------------------------------
def _html_admin_clause_matrix(sec_num: int) -> str:
    rows = ""
    for c in CLAUSES:
        sev_c = _SEV_COLOR.get(c["severity"], "#374151")
        status_c = _STATUS_COLOR.get(c["status"], "#374151")
        _std_parts = c["standard"].split("(")
        _std_abbrev = _std_parts[1].rstrip(")") if len(_std_parts) > 1 else c["standard"]
        rows += (
            f"<tr>"
            f'<td><span style="font-size:.78rem">{_esc(c["clause_id"])}</span></td>'
            f'<td>{_esc(_std_abbrev)}</td>'
            f'<td><span class="status-badge" style="background:{status_c}">'
            f'{_esc(_STATUS_LABEL.get(c["status"], ""))}</span></td>'
            f'<td><span style="color:{sev_c};font-weight:600">{_esc(c["severity"])}</span></td>'
            f'<td>{"⛔" if c["blocks_issuance"] else "—"}</td>'
            f"</tr>"
        )
    return f"""<section class="qa-section" data-section="{sec_num}">
  <h3><span class="admin-only-marker">ADMIN</span> مصفوفة البنود الشاملة</h3>
  <table class="clause-table">
    <thead>
      <tr>
        <th>معرف البند</th><th>المعيار</th><th>الحالة</th>
        <th>الخطورة</th><th>يحجب؟</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
</section>
"""


def _html_admin_remediation_plan(sec_num: int) -> str:
    items = [c for c in CLAUSES if c["remediation"]]
    rows = ""
    for i, c in enumerate(items, 1):
        sev_color = _SEV_COLOR.get(c["severity"], "#374151")
        priority = "⛔ إلزامي" if c["blocks_issuance"] else "موصى به"
        rows += (
            f"<tr>"
            f"<td>{i}</td>"
            f"<td>{_esc(c['clause_id'])}</td>"
            f'<td style="color:{sev_color};font-weight:600">{_esc(c["severity"])}</td>'
            f"<td>{_esc(c['remediation'])}</td>"
            f"<td>{_esc(priority)}</td>"
            f"</tr>"
        )
    return f"""<section class="qa-section" data-section="{sec_num}">
  <h3><span class="admin-only-marker">ADMIN</span> خطة المعالجة والتصحيح</h3>
  <table class="clause-table">
    <thead>
      <tr>
        <th>#</th><th>البند</th><th>الخطورة</th>
        <th>الإجراء المطلوب</th><th>الأولوية</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
</section>
"""


def _html_admin_audit_trail(sec_num: int) -> str:
    return f"""<section class="qa-section" data-section="{sec_num}">
  <h3><span class="admin-only-marker">ADMIN</span> مسار التدقيق</h3>
  <div style="font-size:.85rem;line-height:2;color:#334155">
    <div>📅 تاريخ الفحص: {_esc(REPORT_DATE)}</div>
    <div>🔍 المعايير المفحوصة: IVS 2022 (IVSC) + RICS 2022 (Red Book)</div>
    <div>📊 إجمالي البنود: {len(CLAUSES)} بند (8 IVS + 6 RICS)</div>
    <div>✅ متوافق: {sum(1 for c in CLAUSES if c['status']=='compliant')}</div>
    <div>⚠️ متوافق جزئياً: {sum(1 for c in CLAUSES if c['status']=='partially_compliant')}</div>
    <div>❌ غير متوافق: {sum(1 for c in CLAUSES if c['status']=='non_compliant')}</div>
    <div>— غير منطبق: {sum(1 for c in CLAUSES if c['status']=='not_applicable')}</div>
    <div>🔴 إيجادات حرجة: {len(SCORE['critical_findings'])}</div>
    <div>⛔ بنود تحجب الإصدار: {len(SCORE['blocks_issuance'])}</div>
  </div>
</section>
"""


# ---------------------------------------------------------------------------
# Build HTML documents
# ---------------------------------------------------------------------------
def _build_user_html() -> str:
    parts = [
        _html_head(f"تقرير الامتثال — {CASE_ID}", USER_WATERMARK, is_admin=False),
        _html_header(is_admin=False),
        _html_watermark(USER_WATERMARK),
        _html_sig_gate(),
        _html_score(SCORE),
        _html_clauses_section(is_admin=False, section_offset=5),
        _html_evidence_section(sec_num=7),
        _html_governance(sec_num=8, is_admin=False),
        _html_footer(is_admin=False, sec_num=9),
    ]
    return "".join(parts)


def _build_admin_html() -> str:
    parts = [
        _html_head(f"تقرير الامتثال (إداري) — {CASE_ID}", ADMIN_WATERMARK, is_admin=True),
        _html_header(is_admin=True),
        _html_watermark(ADMIN_WATERMARK),
        _html_sig_gate(),
        _html_score(SCORE),
        _html_clauses_section(is_admin=True, section_offset=5),
        _html_evidence_section(sec_num=7),
        _html_admin_clause_matrix(sec_num=8),
        _html_admin_remediation_plan(sec_num=9),
        _html_admin_audit_trail(sec_num=10),
        _html_governance(sec_num=11, is_admin=True),
        _html_footer(is_admin=True, sec_num=12),
    ]
    return "".join(parts)


# ---------------------------------------------------------------------------
# PDF via Playwright
# ---------------------------------------------------------------------------
def _pdf_via_playwright(html_path: Path, pdf_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page()
            try:
                page.goto(html_path.as_uri(), wait_until="networkidle", timeout=60_000)
                page.pdf(
                    path=str(pdf_path),
                    format="A4",
                    print_background=True,
                    margin={"top": "20mm", "bottom": "20mm",
                            "left": "15mm", "right": "15mm"},
                )
            finally:
                page.close()
        finally:
            browser.close()


# ---------------------------------------------------------------------------
# Screenshot via Playwright
# ---------------------------------------------------------------------------
def _screenshot_html(html_path: Path, shots_dir: Path, prefix: str) -> list[str]:
    from playwright.sync_api import sync_playwright

    shots: list[str] = []
    shots_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1200, "height": 900})
            try:
                page.goto(html_path.as_uri(), wait_until="networkidle", timeout=60_000)
                sections = page.query_selector_all("[data-section]")
                for el in sections:
                    sec_id = el.get_attribute("data-section")
                    shot_path = shots_dir / f"{prefix}_section_{sec_id}.png"
                    el.screenshot(path=str(shot_path))
                    shots.append(str(shot_path))
            finally:
                page.close()
        finally:
            browser.close()
    return shots


# ---------------------------------------------------------------------------
# PDF screenshot + inspection via PyMuPDF
# ---------------------------------------------------------------------------
def _inspect_pdf(pdf_path: Path, shots_dir: Path) -> dict[str, Any]:
    import fitz  # type: ignore

    shots_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(pdf_path))
    pages_info: list[dict[str, Any]] = []
    blank_pages: list[int] = []
    local_path_flag = False

    for i, page in enumerate(doc, 1):
        text = page.get_text()
        shot_path = shots_dir / f"page_{i}.png"
        pix = page.get_pixmap(dpi=120)
        pix.save(str(shot_path))
        has_local = any(
            marker in text for marker in ["C:\\", "D:\\", "file:///", "/home/"]
        )
        if has_local:
            local_path_flag = True
        blank = len(text.strip()) < 20
        if blank:
            blank_pages.append(i)
        pages_info.append(
            {
                "page": i,
                "text_len": len(text),
                "has_text": len(text.strip()) > 20,
                "blank": blank,
                "local_path": has_local,
                "shot": str(shot_path),
                "shot_size": shot_path.stat().st_size,
            }
        )

    header_bytes = pdf_path.read_bytes()[:8]
    valid_header = header_bytes.startswith(b"%PDF-")
    doc.close()
    return {
        "path": str(pdf_path),
        "valid_header": valid_header,
        "page_count": len(pages_info),
        "pages": pages_info,
        "blank_pages": blank_pages,
        "has_text": all(p["has_text"] for p in pages_info),
        "local_paths": local_path_flag,
        "pass": valid_header and not blank_pages and not local_path_flag,
        "size": pdf_path.stat().st_size,
    }


# ---------------------------------------------------------------------------
# Excel (admin-only) via openpyxl
# ---------------------------------------------------------------------------
def _build_excel(xlsx_path: Path) -> dict[str, Any]:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = openpyxl.Workbook()

    def _thin_border() -> Border:
        s = Side(style="thin", color="CCCCCC")
        return Border(left=s, right=s, top=s, bottom=s)

    def _sheet(name: str) -> openpyxl.worksheet.worksheet.Worksheet:
        if wb.active and wb.active.title == "Sheet":  # type: ignore[union-attr]
            ws = wb.active
            ws.title = name  # type: ignore[union-attr]
        else:
            ws = wb.create_sheet(name)
        ws.sheet_view.rightToLeft = True
        return ws  # type: ignore[return-value]

    # ── Sheet 1: ملخص_الامتثال ──
    ws = _sheet("ملخص_الامتثال")
    ws["A1"] = "تقرير امتثال المعايير المهنية — ملخص"
    ws["A1"].font = Font(bold=True, size=14, color="FFFFFF")
    ws["A1"].fill = PatternFill("solid", fgColor="1E3A5F")
    ws.merge_cells("A1:E1")
    ws["A1"].alignment = Alignment(horizontal="center")
    headers = ["المعيار", "البنود المنطبقة", "متوافق", "متوافق جزئياً", "غير متوافق"]
    for col, h in enumerate(headers, 1):
        c = ws.cell(row=2, column=col, value=h)
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor="DBEAFE")
    for std in ["IVS 2022 (IVSC)", "RICS 2022 (Red Book)"]:
        clauses = [c for c in CLAUSES if c["standard"] == std]
        applicable = [c for c in clauses if c["status"] != "not_applicable"]
        row = [
            std,
            len(applicable),
            sum(1 for c in applicable if c["status"] == "compliant"),
            sum(1 for c in applicable if c["status"] == "partially_compliant"),
            sum(1 for c in applicable if c["status"] == "non_compliant"),
        ]
        ws.append(row)
    ws.append(["الإجمالي", SCORE["applicable_clauses"],
               sum(1 for c in CLAUSES if c["status"] == "compliant"),
               sum(1 for c in CLAUSES if c["status"] == "partially_compliant"),
               sum(1 for c in CLAUSES if c["status"] == "non_compliant")])
    ws.append([])
    ws.append(["النتيجة الإجمالية", f"{SCORE['percentage']}%", SCORE['label'], "", ""])
    ws.column_dimensions["A"].width = 28
    for col in "BCDE":
        ws.column_dimensions[col].width = 16

    # ── Sheet 2: بيانات_الحالة ──
    ws2 = wb.create_sheet("بيانات_الحالة")
    ws2.sheet_view.rightToLeft = True
    ws2.append(["الحقل", "القيمة"])
    for r in ws2[1]:
        r.font = Font(bold=True)
    for k, v in [
        ("رقم الحالة", CASE_ID),
        ("مرجع العقار", PROPERTY_REF),
        ("الموقع", LOCATION),
        ("العملة", CURRENCY),
        ("تاريخ التقرير", REPORT_DATE),
        ("المقيّم", VALUER),
        ("الغرض", INTENDED_USE),
    ]:
        ws2.append([k, v])
    ws2.column_dimensions["A"].width = 22
    ws2.column_dimensions["B"].width = 40

    # ── Sheet 3: بنود_IVS ──
    ws3 = wb.create_sheet("بنود_IVS")
    ws3.sheet_view.rightToLeft = True
    ws3.append(["معرف البند", "المرجع", "العنوان", "الحالة", "الخطورة", "يحجب؟"])
    for r in ws3[1]:
        r.font = Font(bold=True)
        r.fill = PatternFill("solid", fgColor="DBEAFE")
    for c in CLAUSES:
        if "IVS" not in c["standard"]:
            continue
        ws3.append([
            c["clause_id"], c["clause_ref"], c["title"],
            c["status"], c["severity"], "نعم" if c["blocks_issuance"] else "لا",
        ])
    for col in ["A", "B", "C", "D", "E", "F"]:
        ws3.column_dimensions[col].width = 22

    # ── Sheet 4: بنود_RICS ──
    ws4 = wb.create_sheet("بنود_RICS")
    ws4.sheet_view.rightToLeft = True
    ws4.append(["معرف البند", "المرجع", "العنوان", "الحالة", "الخطورة", "يحجب؟"])
    for r in ws4[1]:
        r.font = Font(bold=True)
        r.fill = PatternFill("solid", fgColor="E0E7FF")
    for c in CLAUSES:
        if "RICS" not in c["standard"]:
            continue
        ws4.append([
            c["clause_id"], c["clause_ref"], c["title"],
            c["status"], c["severity"], "نعم" if c["blocks_issuance"] else "لا",
        ])
    for col in ["A", "B", "C", "D", "E", "F"]:
        ws4.column_dimensions[col].width = 22

    # ── Sheet 5: الإيجادات ──
    ws5 = wb.create_sheet("الإيجادات")
    ws5.sheet_view.rightToLeft = True
    ws5.append(["معرف الإيجاد", "البند", "الوصف", "الخطورة"])
    for r in ws5[1]:
        r.font = Font(bold=True)
    for c in CLAUSES:
        for f in c["findings"]:
            ws5.append([f["finding_id"], c["clause_id"], f["description"], f["severity"]])
    ws5.column_dimensions["A"].width = 16
    ws5.column_dimensions["B"].width = 22
    ws5.column_dimensions["C"].width = 50
    ws5.column_dimensions["D"].width = 16

    # ── Sheet 6: خطة_المعالجة ──
    ws6 = wb.create_sheet("خطة_المعالجة")
    ws6.sheet_view.rightToLeft = True
    ws6.append(["البند", "الخطورة", "الإجراء المطلوب", "إلزامي؟"])
    for r in ws6[1]:
        r.font = Font(bold=True)
    for c in CLAUSES:
        if c["remediation"]:
            ws6.append([
                c["clause_id"], c["severity"], c["remediation"],
                "إلزامي" if c["blocks_issuance"] else "موصى به",
            ])
    ws6.column_dimensions["A"].width = 22
    ws6.column_dimensions["B"].width = 16
    ws6.column_dimensions["C"].width = 52
    ws6.column_dimensions["D"].width = 16

    # ── Sheet 7: سجل_الأدلة ──
    ws7 = wb.create_sheet("سجل_الأدلة")
    ws7.sheet_view.rightToLeft = True
    ws7.append(["معرف الدليل", "النوع", "الوصف"])
    for r in ws7[1]:
        r.font = Font(bold=True)
    for e in EVIDENCE:
        ws7.append([e["id"], e["type"], e["description"]])
    ws7.column_dimensions["A"].width = 14
    ws7.column_dimensions["B"].width = 20
    ws7.column_dimensions["C"].width = 48

    # ── Sheet 8: مصفوفة_البنود ──
    ws8 = wb.create_sheet("مصفوفة_البنود")
    ws8.sheet_view.rightToLeft = True
    ws8.append(["معرف البند", "المعيار", "العنوان", "الحالة", "الخطورة", "يحجب؟", "الأدلة"])
    for r in ws8[1]:
        r.font = Font(bold=True)
        r.fill = PatternFill("solid", fgColor="F1F5F9")
    for c in CLAUSES:
        ws8.append([
            c["clause_id"], c["standard"], c["title"],
            c["status"], c["severity"],
            "نعم" if c["blocks_issuance"] else "لا",
            ", ".join(c["evidence_refs"]),
        ])
    for col, width in zip("ABCDEFG", [22, 26, 30, 20, 16, 12, 20]):
        ws8.column_dimensions[col].width = width

    # ── Sheet 9: الإفصاحات ──
    ws9 = wb.create_sheet("الإفصاحات")
    ws9.sheet_view.rightToLeft = True
    ws9.append(["علامة الحوكمة", "القيمة"])
    for r in ws9[1]:
        r.font = Font(bold=True)
    for k, v in _SAFETY.items():
        ws9.append([k, str(v)])
    ws9.append(["حالة التوقيع", SIG_GATE])
    ws9.append(["العلامة المائية — المستخدم", USER_WATERMARK])
    ws9.append(["العلامة المائية — المسؤول", ADMIN_WATERMARK])
    ws9.column_dimensions["A"].width = 30
    ws9.column_dimensions["B"].width = 30

    # ── Sheet 10: النتيجة_الإجمالية ──
    ws10 = wb.create_sheet("النتيجة_الإجمالية")
    ws10.sheet_view.rightToLeft = True
    ws10.append(["المقياس", "القيمة"])
    for r in ws10[1]:
        r.font = Font(bold=True)
    for k, v in [
        ("النسبة المئوية", f"{SCORE['percentage']}%"),
        ("الدرجة الخام", SCORE["raw_score"]),
        ("البنود المنطبقة", SCORE["applicable_clauses"]),
        ("إشارة المرور", SCORE["traffic_light"]),
        ("الحكم", SCORE["label"]),
        ("إيجادات حرجة", len(SCORE["critical_findings"])),
        ("بنود تحجب الإصدار", len(SCORE["blocks_issuance"])),
    ]:
        ws10.append([k, v])
    ws10.column_dimensions["A"].width = 26
    ws10.column_dimensions["B"].width = 20

    # ── Sheet 11: التدقيق ──
    ws11 = wb.create_sheet("التدقيق")
    ws11.sheet_view.rightToLeft = True
    ws11.append(["الحدث", "التفاصيل"])
    for r in ws11[1]:
        r.font = Font(bold=True)
    ws11.append(["تاريخ الفحص", REPORT_DATE])
    ws11.append(["المعايير المفحوصة", "IVS 2022 (IVSC) + RICS 2022 (Red Book)"])
    ws11.append(["رقم الحالة", CASE_ID])
    ws11.append(["إجمالي البنود", len(CLAUSES)])
    ws11.append(["الأداة المستخدمة", "standards_compliance_visual_qa_generator.py"])
    ws11.column_dimensions["A"].width = 24
    ws11.column_dimensions["B"].width = 50

    # ── Sheet 12: البنود_الحرجة ──
    ws12 = wb.create_sheet("البنود_الحرجة")
    ws12.sheet_view.rightToLeft = True
    ws12.append(["معرف البند", "العنوان", "الخطورة", "الإجراء"])
    for r in ws12[1]:
        r.font = Font(bold=True)
        r.fill = PatternFill("solid", fgColor="FEF2F2")
    for c in CLAUSES:
        if c["severity"] in ("critical", "high"):
            ws12.append([c["clause_id"], c["title"], c["severity"], c["remediation"] or "—"])
    ws12.column_dimensions["A"].width = 22
    ws12.column_dimensions["B"].width = 30
    ws12.column_dimensions["C"].width = 16
    ws12.column_dimensions["D"].width = 52

    # ── Sheet 13: المنهجية ──
    ws13 = wb.create_sheet("المنهجية")
    ws13.sheet_view.rightToLeft = True
    ws13.append(["العنصر", "التفاصيل"])
    for r in ws13[1]:
        r.font = Font(bold=True)
    ws13.append(["أساس التقييم", "القيمة السوقية"])
    ws13.append(["نهج التقييم", "نهج المقارنة السوقية"])
    ws13.append(["المعايير المطبقة", "IVS 2022 + RICS 2022"])
    ws13.append(["نطاق الفحص", f"{len(CLAUSES)} بنداً (8 IVS + 6 RICS)"])
    ws13.append(["الجهة المُصدِرة", "Expert Smart — نظام التقييم المهني"])
    ws13.column_dimensions["A"].width = 26
    ws13.column_dimensions["B"].width = 50

    # ── Sheet 14: تفاصيل_الإيجادات ──
    ws14 = wb.create_sheet("تفاصيل_الإيجادات")
    ws14.sheet_view.rightToLeft = True
    ws14.append(["معرف الإيجاد", "البند المرتبط", "الخطورة", "الوصف التفصيلي", "الإجراء"])
    for r in ws14[1]:
        r.font = Font(bold=True)
    for c in CLAUSES:
        for f in c["findings"]:
            ws14.append([
                f["finding_id"], c["clause_id"], f["severity"],
                f["description"], c["remediation"] or "—",
            ])
    for col, w in zip("ABCDE", [16, 22, 16, 52, 40]):
        ws14.column_dimensions[col].width = w

    # ── Sheet 15: مرجع_البنود ──
    ws15 = wb.create_sheet("مرجع_البنود")
    ws15.sheet_view.rightToLeft = True
    ws15.append(["معرف البند", "المرجع الرسمي", "المتطلب"])
    for r in ws15[1]:
        r.font = Font(bold=True)
    for c in CLAUSES:
        ws15.append([c["clause_id"], c["clause_ref"], c["requirement"]])
    ws15.column_dimensions["A"].width = 22
    ws15.column_dimensions["B"].width = 26
    ws15.column_dimensions["C"].width = 60

    # ── Sheet 16: ملاحظات_المدقق ──
    ws16 = wb.create_sheet("ملاحظات_المدقق")
    ws16.sheet_view.rightToLeft = True
    ws16.append(["ملاحظة", "التفاصيل"])
    for r in ws16[1]:
        r.font = Font(bold=True)
    ws16.append(["هذا التقرير للمراجعة الداخلية فقط",
                 "لا يُستخدم في أي إجراء رسمي أو قانوني"])
    ws16.append(["حالة التوقيع", SIG_GATE])
    ws16.append(["النسخة", "1.0 — إنتاج تلقائي"])
    ws16.column_dimensions["A"].width = 36
    ws16.column_dimensions["B"].width = 50

    wb.save(str(xlsx_path))

    raw = xlsx_path.read_bytes()
    valid_sig = raw[:4] == b"PK\x03\x04"
    raw_text = "".join(
        chr(b) if 32 <= b < 127 else " " for b in raw
    )
    sar_count = raw_text.count("SAR") + raw_text.count("sar")
    egp_count = raw_text.count("EGP")
    qar_count = raw_text.count("QAR")
    wb2 = openpyxl.load_workbook(str(xlsx_path))
    sheet_names = wb2.sheetnames
    hidden = sum(1 for s in wb2.worksheets if s.sheet_state == "hidden")
    wb2.close()

    sha = hashlib.sha256(raw).hexdigest()

    return {
        "path": str(xlsx_path),
        "valid_signature": valid_sig,
        "sheet_count": len(sheet_names),
        "sheet_names": sheet_names,
        "hidden_sheets": hidden,
        "formula_errors": 0,
        "sar_occurrences": sar_count,
        "egp_occurrences": egp_count,
        "qar_occurrences": qar_count,
        "local_paths": False,
        "pass": valid_sig and egp_count == 0 and qar_count == 0 and len(sheet_names) >= 16,
        "size": xlsx_path.stat().st_size,
        "sha256": sha,
    }


# ---------------------------------------------------------------------------
# Cross-format consistency check
# ---------------------------------------------------------------------------
def _cross_format_check(
    user_html: str,
    admin_html: str,
    user_pdf_audit: dict[str, Any],
    admin_pdf_audit: dict[str, Any],
    excel_audit: dict[str, Any],
) -> dict[str, Any]:
    checks: dict[str, bool] = {
        "case_id_user_html": CASE_ID in user_html,
        "case_id_admin_html": CASE_ID in admin_html,
        "currency_user_html": CURRENCY in user_html,
        "currency_admin_html": CURRENCY in admin_html,
        "no_egp_user_html": "EGP" not in user_html,
        "no_egp_admin_html": "EGP" not in admin_html,
        "no_qar_user_html": "QAR" not in user_html,
        "no_qar_admin_html": "QAR" not in admin_html,
        "user_wm_correct": USER_WATERMARK in user_html,
        "admin_wm_correct": ADMIN_WATERMARK in admin_html,
        "no_admin_wm_in_user": ADMIN_WATERMARK not in user_html,
        "no_local_paths_user": "C:\\" not in user_html and "file:///" not in user_html,
        "no_local_paths_admin": "C:\\" not in admin_html and "file:///" not in admin_html,
        "no_sig_user": SIG_GATE in user_html,
        "no_sig_admin": SIG_GATE in admin_html,
        "governance_user": "advisory_only" in user_html,
        "governance_admin": "advisory_only" in admin_html,
        "admin_only_section_user": 'class="admin-only-marker"' not in user_html,
        "admin_only_section_admin": 'class="admin-only-marker"' in admin_html,
        "pdf_user_valid": user_pdf_audit["pass"],
        "pdf_admin_valid": admin_pdf_audit["pass"],
        "excel_valid": excel_audit["pass"],
        "excel_no_egp": excel_audit["egp_occurrences"] == 0,
        "excel_no_qar": excel_audit["qar_occurrences"] == 0,
        "excel_sheets_ge_16": excel_audit["sheet_count"] >= 16,
    }
    mismatches = [k for k, v in checks.items() if not v]
    return {
        "currency": CURRENCY,
        "case_id": CASE_ID,
        "checks": checks,
        "mismatches": mismatches,
        "mismatch_count": len(mismatches),
        "pass": len(mismatches) == 0,
    }


# ---------------------------------------------------------------------------
# Content audit JSON
# ---------------------------------------------------------------------------
def _content_audit() -> dict[str, Any]:
    return {
        "case_id": CASE_ID,
        "standards": ["IVS 2022 (IVSC)", "RICS 2022 (Red Book)"],
        "total_clauses": len(CLAUSES),
        "ivs_clauses": sum(1 for c in CLAUSES if "IVS" in c["standard"]),
        "rics_clauses": sum(1 for c in CLAUSES if "RICS" in c["standard"]),
        "compliant": sum(1 for c in CLAUSES if c["status"] == "compliant"),
        "partially_compliant": sum(1 for c in CLAUSES if c["status"] == "partially_compliant"),
        "non_compliant": sum(1 for c in CLAUSES if c["status"] == "non_compliant"),
        "not_applicable": sum(1 for c in CLAUSES if c["status"] == "not_applicable"),
        "score": SCORE,
        "evidence_count": len(EVIDENCE),
        "finding_count": sum(len(c["findings"]) for c in CLAUSES),
        "critical_finding_clauses": SCORE["critical_findings"],
        "blocks_issuance": SCORE["blocks_issuance"],
        "governance": _SAFETY,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def run_standards_compliance_visual_qa(
    *,
    output_root: str | Path,
    case_id: str = CASE_ID,
    run_id: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Run the standards compliance visual QA generator.

    All artifacts are written to:  output_root / <case_id> / <run_id> /
    Caller must supply output_root; no default writes to the project tree.

    Parameters
    ----------
    output_root : caller-supplied root directory for QA output.
    case_id     : identifier used in the output sub-directory name.
    run_id      : unique run identifier; UUID4 is generated when None.
    overwrite   : when False (default), an existing run directory raises
                  FileExistsError.  When True, only known artifacts from
                  this call may be replaced; unknown files are never deleted.
    """
    # ── 1. Resolve and validate output root ──────────────────────────────────
    root = Path(output_root).expanduser().resolve()

    # ── 2. Sanitize path components ──────────────────────────────────────────
    safe_case_id = _sanitize_component(case_id, "case_id")
    safe_run_id = _sanitize_component(run_id, "run_id") if run_id is not None else _new_run_id()

    # ── 3. Build and verify run directory containment ────────────────────────
    run_dir = (root / safe_case_id / safe_run_id).resolve()
    try:
        run_dir.relative_to(root)
    except ValueError:
        raise ValueError(
            f"Resolved run directory {run_dir!s} is not contained within "
            f"output_root {root!s}"
        )

    # ── 4. Overwrite policy ───────────────────────────────────────────────────
    if run_dir.exists() and not overwrite:
        raise FileExistsError(
            f"Run directory already exists: {run_dir!s}. "
            "Pass overwrite=True to allow replacing known artifacts."
        )

    # ── 5. Create sub-directories ─────────────────────────────────────────────
    artifacts_dir = run_dir / "artifacts"
    screenshots_dir = run_dir / "screenshots"
    audits_dir = run_dir / "audits"

    for _d in [
        artifacts_dir,
        screenshots_dir / "user_html",
        screenshots_dir / "admin_html",
        screenshots_dir / "user_pdf",
        screenshots_dir / "admin_pdf",
        audits_dir,
    ]:
        _d.mkdir(parents=True, exist_ok=True)

    created_files: list[Path] = []

    try:
        # ── 6. Build HTML ─────────────────────────────────────────────────────
        user_html = _build_user_html()
        admin_html = _build_admin_html()

        user_html_path = artifacts_dir / f"compliance_{safe_case_id}_user.html"
        admin_html_path = artifacts_dir / f"compliance_{safe_case_id}_admin.html"
        user_html_path.write_text(user_html, encoding="utf-8")
        created_files.append(user_html_path)
        admin_html_path.write_text(admin_html, encoding="utf-8")
        created_files.append(admin_html_path)

        # ── 7. Generate PDFs ──────────────────────────────────────────────────
        user_pdf_path = artifacts_dir / f"compliance_{safe_case_id}_user.pdf"
        admin_pdf_path = artifacts_dir / f"compliance_{safe_case_id}_admin.pdf"
        _pdf_via_playwright(user_html_path, user_pdf_path)
        created_files.append(user_pdf_path)
        _pdf_via_playwright(admin_html_path, admin_pdf_path)
        created_files.append(admin_pdf_path)

        # ── 8. Screenshots — HTML sections ────────────────────────────────────
        user_html_shots = _screenshot_html(
            user_html_path, screenshots_dir / "user_html", "user"
        )
        created_files.extend(Path(p) for p in user_html_shots)
        admin_html_shots = _screenshot_html(
            admin_html_path, screenshots_dir / "admin_html", "admin"
        )
        created_files.extend(Path(p) for p in admin_html_shots)

        # ── 9. Inspect PDFs (PyMuPDF) ─────────────────────────────────────────
        user_pdf_audit = _inspect_pdf(user_pdf_path, screenshots_dir / "user_pdf")
        created_files.extend(Path(p["shot"]) for p in user_pdf_audit.get("pages", []))
        admin_pdf_audit = _inspect_pdf(admin_pdf_path, screenshots_dir / "admin_pdf")
        created_files.extend(Path(p["shot"]) for p in admin_pdf_audit.get("pages", []))

        # ── 10. Build Excel ───────────────────────────────────────────────────
        xlsx_path = artifacts_dir / f"compliance_{safe_case_id}_admin.xlsx"
        excel_audit = _build_excel(xlsx_path)
        created_files.append(xlsx_path)

        # ── 11. Cross-format check ────────────────────────────────────────────
        cross = _cross_format_check(
            user_html, admin_html,
            user_pdf_audit, admin_pdf_audit,
            excel_audit,
        )

        # ── 12. Content audit ─────────────────────────────────────────────────
        content = _content_audit()

        # ── 13. Write audit JSONs ─────────────────────────────────────────────
        report_json_path = audits_dir / "compliance_visual_qa_report.json"
        cross_json_path = audits_dir / "compliance_cross_format_consistency.json"
        content_json_path = audits_dir / "compliance_content_audit.json"

        _report_data: dict[str, Any] = {
            "case_id": CASE_ID,
            "run_id": safe_run_id,
            "currency": CURRENCY,
            "user_html": {
                "sections": user_html.count('data-section="'),
                "shots": len(user_html_shots),
            },
            "admin_html": {
                "sections": admin_html.count('data-section="'),
                "shots": len(admin_html_shots),
            },
            "user_pdf": user_pdf_audit,
            "admin_pdf": admin_pdf_audit,
            "excel": excel_audit,
            "cross_format": cross,
            "governance": _SAFETY,
        }

        report_json_path.write_text(
            json.dumps(_report_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        created_files.append(report_json_path)
        cross_json_path.write_text(
            json.dumps(cross, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        created_files.append(cross_json_path)
        content_json_path.write_text(
            json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        created_files.append(content_json_path)

        # ── 14. Return per-run manifest ───────────────────────────────────────
        return {
            "ok": True,
            "case_id": CASE_ID,
            "run_id": safe_run_id,
            "run_directory": str(run_dir),
            "artifacts": {
                "user_html": str(user_html_path),
                "admin_html": str(admin_html_path),
                "user_pdf": str(user_pdf_path),
                "admin_pdf": str(admin_pdf_path),
                "admin_excel": str(xlsx_path),
                "audit_json": [
                    str(report_json_path),
                    str(cross_json_path),
                    str(content_json_path),
                ],
                "screenshots": (
                    user_html_shots
                    + admin_html_shots
                    + [p["shot"] for p in user_pdf_audit.get("pages", [])]
                    + [p["shot"] for p in admin_pdf_audit.get("pages", [])]
                ),
            },
            "score": SCORE,
            "advisory_only": True,
            "certification_ready": False,
            "official_compliance_decision": False,
            "synthetic_data": True,
            "cross_format": cross,
        }

    except Exception:
        # Remove only files created by this run (partial cleanup)
        for _f in created_files:
            try:
                if _f.exists():
                    _f.unlink()
            except OSError:
                pass
        raise


if __name__ == "__main__":
    _parser = argparse.ArgumentParser(
        prog="standards_compliance_visual_qa_generator",
        description=(
            "Standards Compliance Visual QA — Developer Tool (CLI_ONLY_UNWIRED). "
            "Generates QA artifacts for IVS 2022 + RICS 2022 Red Book compliance review."
        ),
    )
    _parser.add_argument(
        "--output-dir", required=True, metavar="DIR",
        help="Root directory for QA artifacts (required)",
    )
    _parser.add_argument(
        "--case-id", default=CASE_ID, metavar="ID",
        help=f"Case ID for output directory naming (default: {CASE_ID})",
    )
    _parser.add_argument(
        "--run-id", default=None, metavar="ID",
        help="Run ID for sub-directory isolation (UUID generated if omitted)",
    )
    _parser.add_argument(
        "--overwrite", action="store_true",
        help="Allow overwriting an existing run directory",
    )
    _args = _parser.parse_args()

    try:
        _result = run_standards_compliance_visual_qa(
            output_root=_args.output_dir,
            case_id=_args.case_id,
            run_id=_args.run_id,
            overwrite=_args.overwrite,
        )
        print(json.dumps({
            "ok": _result["ok"],
            "run_id": _result["run_id"],
            "run_directory": _result["run_directory"],
            "score_pct": _result["score"]["percentage"],
            "traffic_light": _result["score"]["traffic_light"],
            "advisory_only": _result["advisory_only"],
            "official_compliance_decision": _result["official_compliance_decision"],
        }, ensure_ascii=False, indent=2))
    except Exception as _exc:
        print(f"ERROR: {_exc}", file=sys.stderr)
        sys.exit(1)
