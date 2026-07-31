"""
pv_sim_enhanced_html.py
Builds new HTML sections for the enhanced simulation report:
  Section 11 — Provenance Table
  Section 12 — Applied Methods on Subject Property
  Section 13 — Methods Comparison Table
  Section 14 — Full Source Log (admin only)

Injected into base HTML before </body>.
Governance badge emitted in every section.
No local paths exposed in any rendered output.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .pv_sim_sourced_inputs import InputProvenance, SourcingResult
from .pv_sim_market_methods import MethodResult, MethodsResult


# ── Section wrapper ───────────────────────────────────────────────────────────

def _section(
    num: str,
    title_ar: str,
    content_html: str,
    color: str = "#38bdf8",
) -> str:
    return f"""
<section data-section="{num}" id="enhanced_{num}"
  style="margin-bottom:28px;padding:22px;border-radius:12px;
         border:1px solid {color}44;background:rgba(17,24,39,0.65);">
  <h2 style="color:{color};margin:0 0 16px 0;font-size:1.05rem;
             border-bottom:1px solid {color}33;padding-bottom:8px;">
    {num}. {title_ar}
  </h2>
  {content_html}
</section>"""


def _governance_badge() -> str:
    return (
        "<div style='background:rgba(251,191,36,0.12);border:1px solid #fbbf2440;"
        "border-radius:6px;padding:8px 14px;margin-bottom:14px;"
        "font-size:0.75rem;color:#fbbf24;'>"
        "⚠ استرشادي — Draft محوكم | advisory_only=True | certification_ready=False | "
        "fake_signature_created=False | non_certified=True"
        "</div>"
    )


def _table(headers: List[str], rows_html: str) -> str:
    ths = "".join(f"<th>{h}</th>" for h in headers)
    return (
        "<div style='overflow-x:auto;'>"
        f"<table><thead><tr>{ths}</tr></thead>"
        f"<tbody>{rows_html}</tbody></table>"
        "</div>"
    )


def _fmt_val(v: Optional[float], unit: str = "") -> str:
    if v is None:
        return "<span style='color:#9ca3af'>غير متاح</span>"
    return f"{v:,.2f} {unit}".strip()


def _rag_cell(rag: str) -> str:
    color_map = {
        "🟢": "#22c55e", "🟡": "#eab308",
        "🔴": "#ef4444", "⚪": "#9ca3af",
    }
    color = color_map.get(rag, "#9ca3af")
    return (
        f"<span style='color:{color};font-size:1.1rem;"
        f"font-weight:700;'>{rag}</span>"
    )


def _status_badge(status: str) -> str:
    if "Draft" in status or "مسح" in status or "افتراضي" in status:
        bg, fg = "rgba(251,191,36,0.15)", "#fbbf24"
    elif "Certified" in status:
        bg, fg = "rgba(34,197,94,0.15)", "#22c55e"
    else:
        bg, fg = "rgba(156,163,175,0.10)", "#9ca3af"
    return (
        f"<span style='background:{bg};color:{fg};border-radius:4px;"
        f"padding:2px 8px;font-size:0.7rem;white-space:nowrap;'>{status}</span>"
    )


# ── Section 11 — Provenance Table ─────────────────────────────────────────────

def build_provenance_section(
    provenance_table: List[InputProvenance],
    audience: str,
) -> str:
    headers = [
        "المدخل", "القيمة المستخدمة", "المصدر",
        "التاريخ", "الثقة %", "الفئة", "الحالة", "ملاحظة التسوية",
    ]
    rows_html = ""
    for p in provenance_table:
        uri_cell = (
            f"<span title='' style='color:#64748b;font-size:0.7rem;'>"
            f"{p.source_name}</span>"
        )
        rows_html += (
            "<tr>"
            f"<td>{p.label_ar}</td>"
            f"<td style='font-weight:600;color:#e2e8f0;'>{_fmt_val(p.value_used, p.unit)}</td>"
            f"<td>{uri_cell}</td>"
            f"<td style='color:#9ca3af;font-size:0.75rem;'>{p.retrieved_at[:10]}</td>"
            f"<td>{p.confidence_score:.0f}%</td>"
            f"<td style='font-size:0.75rem;color:#94a3b8;'>{p.source_tier}</td>"
            f"<td>{_status_badge(p.status)}</td>"
            f"<td style='font-size:0.72rem;color:#9ca3af;'>{p.reconciliation_note or '—'}</td>"
            "</tr>"
        )

    note = (
        "<p style='color:#64748b;font-size:0.75rem;margin-top:12px;'>"
        "«Draft» = مسح مبدئي محوكم — لا يُمثّل بيانات سوقية رسمية ولا يُدرَّب عليه النموذج المعتمد. "
        "«Certified» = مستخرج من نموذج التقييم المجمع (AVM) بمعايير IAAO."
        "</p>"
    )
    return _section(
        "11", "جدول المصدرية — Provenance Table",
        _governance_badge() + _table(headers, rows_html) + note,
        color="#38bdf8",
    )


# ── Section 12 — Applied Methods on Subject Property ─────────────────────────

def build_applied_methods_section(
    methods_result: MethodsResult,
    audience: str,
    currency: str = "QAR",
) -> str:
    parts = []
    for m in methods_result.methods:
        if m.computed_value is not None:
            val_html = (
                f"<span style='color:#22c55e;font-size:1.1rem;font-weight:700;'>"
                f"{m.computed_value:,.0f} {currency}</span>"
            )
        else:
            val_html = "<span style='color:#9ca3af'>غير متاح</span>"

        steps_rows = ""
        for step in m.calculation_steps:
            v = step.get("value")
            if isinstance(v, list):
                # Nested table (comparables / cash flows)
                if v:
                    inner_rows = ""
                    for row in v:
                        if isinstance(row, dict):
                            inner_rows += "<tr>" + "".join(
                                f"<td style='font-size:0.7rem;color:#94a3b8;padding:2px 6px;'>{val}</td>"
                                for val in row.values()
                            ) + "</tr>"
                    steps_rows += (
                        f"<tr><td colspan='2' style='padding:2px 0;'>"
                        f"<table style='width:100%;border-collapse:collapse;'>"
                        f"<tbody>{inner_rows}</tbody></table></td></tr>"
                    )
            else:
                steps_rows += (
                    f"<tr>"
                    f"<td style='color:#9ca3af;font-size:0.78rem;padding:4px 0;'>{step.get('label', '')}</td>"
                    f"<td style='color:#e2e8f0;font-weight:600;font-size:0.8rem;padding:4px 0;'>{v}</td>"
                    "</tr>"
                )

        color = "#818cf8"
        parts.append(
            f"<div style='margin-bottom:18px;padding:14px;border-radius:8px;"
            f"border:1px solid {color}33;background:rgba(17,24,39,0.45);'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;'>"
            f"<span style='color:{color};font-weight:700;font-size:0.95rem;'>{m.method_name_ar}</span>"
            f"{val_html}</div>"
            f"<div style='font-size:0.72rem;color:#64748b;margin-bottom:8px;'>"
            f"مصدر المدخلات: {m.input_source_summary}</div>"
            f"<table style='width:100%;'><tbody>{steps_rows}</tbody></table>"
            f"</div>"
        )

    # Reconciliation box
    rec = methods_result.reconciliation
    rv  = rec.get("reconciled_value")
    lo  = rec.get("advisory_range_lo")
    hi  = rec.get("advisory_range_hi")

    recon_val_html = (
        f"<strong style='color:#f1f5f9;'>{rv:,.0f} {currency}</strong>"
        if rv else "غير متاح"
    )
    range_html = (
        f"<span style='color:#94a3b8;'>{lo:,.0f} – {hi:,.0f} {currency}</span>"
        if (lo and hi) else "—"
    )
    recon_html = (
        "<div style='background:rgba(251,191,36,0.08);border:1px solid #fbbf2430;"
        "border-radius:8px;padding:14px;margin-top:10px;'>"
        "<div style='color:#fbbf24;font-weight:700;margin-bottom:8px;'>التوفيق الاستشاري</div>"
        "<div style='display:flex;gap:24px;flex-wrap:wrap;font-size:0.85rem;'>"
        f"<div>القيمة المجمَّعة: {recon_val_html}</div>"
        f"<div>النطاق الاستشاري: {range_html}</div>"
        f"<div>{_rag_cell(rec.get('rag_status', '⚪'))}</div>"
        "</div>"
        f"<div style='color:#64748b;font-size:0.75rem;margin-top:8px;'>{rec.get('note', '')}</div>"
        "</div>"
    )

    content = _governance_badge() + "\n".join(parts) + recon_html
    return _section(
        "12", "تطبيق الأساليب على موضوع التقييم (بمدخلات مصدرية)",
        content, color="#818cf8",
    )


# ── Section 13 — Methods Comparison Table ────────────────────────────────────

def build_comparison_table_section(
    comparison_table: List[Dict[str, Any]],
    audience: str,
    currency: str = "QAR",
) -> str:
    headers = [
        "الأسلوب",
        "قيمة التقرير (Base)",
        "القيمة المحسوبة (الموضوع)",
        "الفرق",
        "الفرق %",
        "الحالة",
        "مصدر المدخلات",
    ]
    rows_html = ""
    for row in comparison_table:
        sv = row.get("simulation_value")
        cv = row.get("computed_value")
        da = row.get("diff_amount")
        dp = row.get("diff_pct")
        rag = row.get("rag_status", "⚪")
        src = row.get("input_source_summary", "—")

        sv_cell = (
            f"{sv:,.0f} {currency}"
            if sv else "<span style='color:#9ca3af'>—</span>"
        )
        cv_cell = (
            f"<span style='font-weight:700;color:#e2e8f0;'>{cv:,.0f} {currency}</span>"
            if cv else "<span style='color:#9ca3af'>غير متاح</span>"
        )
        da_cell = f"{da:+,.0f}" if da is not None else "—"
        dp_cell = f"{dp:+.1f}%" if dp is not None else "—"

        rows_html += (
            "<tr>"
            f"<td style='font-weight:600;'>{row.get('method_name_ar', row.get('method_id'))}</td>"
            f"<td>{sv_cell}</td>"
            f"<td>{cv_cell}</td>"
            f"<td style='color:#94a3b8;'>{da_cell}</td>"
            f"<td style='color:#94a3b8;'>{dp_cell}</td>"
            f"<td>{_rag_cell(rag)}</td>"
            f"<td style='font-size:0.72rem;color:#64748b;'>{src}</td>"
            "</tr>"
        )

    legend = (
        "<div style='margin-top:10px;font-size:0.72rem;color:#64748b;'>"
        "🟢 فرق &lt; 10% &nbsp;|&nbsp; 🟡 فرق 10–25% &nbsp;|&nbsp; "
        "🔴 فرق &gt; 25% &nbsp;|&nbsp; ⚪ غير متاح"
        "</div>"
    )
    return _section(
        "13", "جدول مقارنة الأساليب — Methods Comparison Table",
        _governance_badge() + _table(headers, rows_html) + legend,
        color="#f59e0b",
    )


# ── Section 14 — Full Source Log (admin only) ─────────────────────────────────

def build_source_log_section(
    source_log: List[Dict[str, Any]],
    mass_appraisal_summary: Dict[str, Any],
    warnings: List[str],
) -> str:
    headers = [
        "معرّف المصدر", "النوع", "الاسم",
        "URI (مختصر)", "تاريخ المصدر", "الثقة %", "طريقة الاستخراج",
    ]
    rows_html = ""
    for s in source_log:
        uri = str(s.get("source_uri") or s.get("url") or "")
        # Never expose local paths
        if (uri.startswith("file://") or ":\\" in uri
                or (uri.startswith("/") and not uri.startswith("/api"))):
            uri = "[مسار داخلي — محجوب]"

        rows_html += (
            "<tr>"
            f"<td style='font-size:0.72rem;color:#94a3b8;'>{str(s.get('source_id', '—'))[:20]}</td>"
            f"<td style='font-size:0.75rem;'>{s.get('source_type', '—')}</td>"
            f"<td style='font-size:0.75rem;'>{s.get('source_name', s.get('evidence_type', '—'))}</td>"
            f"<td style='font-size:0.68rem;color:#64748b;'>{uri[:60] or '—'}</td>"
            f"<td style='font-size:0.72rem;'>"
            f"{str(s.get('source_date') or s.get('access_date') or '—')[:10]}</td>"
            f"<td>{float(s.get('confidence_score', s.get('confidence', 0))):.0f}%</td>"
            f"<td style='font-size:0.72rem;color:#64748b;'>{s.get('extraction_method', '—')}</td>"
            "</tr>"
        )

    if not rows_html:
        rows_html = (
            "<tr><td colspan='7' style='text-align:center;color:#9ca3af;padding:12px;'>"
            "لا توجد مصادر خارجية مسجَّلة</td></tr>"
        )

    # Mass appraisal summary box
    ma = mass_appraisal_summary or {}
    ma_html = ""
    if ma.get("available"):
        ma_html = (
            "<div style='margin-top:14px;padding:12px;border-radius:6px;"
            "background:rgba(34,197,94,0.06);border:1px solid #22c55e20;'>"
            "<div style='color:#22c55e;font-weight:600;margin-bottom:6px;font-size:0.85rem;'>"
            "نموذج التقييم المجمع (AVM)</div>"
            "<div style='display:flex;gap:20px;flex-wrap:wrap;font-size:0.8rem;color:#94a3b8;'>"
            f"<span>avg_ppm: <strong style='color:#e2e8f0;'>{ma.get('avg_ppm', 0):,.0f}</strong></span>"
            f"<span>avm_ppm: <strong style='color:#e2e8f0;'>{ma.get('avm_ppm', 0):,.0f}</strong></span>"
            f"<span>adj_ppm: <strong style='color:#e2e8f0;'>{ma.get('adj_ppm', 0):,.0f}</strong></span>"
            f"<span>COD: <strong style='color:#e2e8f0;'>{ma.get('cod', '—')}</strong></span>"
            f"<span>PRD: <strong style='color:#e2e8f0;'>{ma.get('prd', '—')}</strong></span>"
            f"<span>الإصدار: <strong style='color:#e2e8f0;'>{ma.get('model_version', '—')}</strong></span>"
            "</div></div>"
        )

    # Warnings box
    warn_html = ""
    if warnings:
        warn_items = "".join(f"<li style='margin-bottom:3px;'>{w}</li>" for w in warnings)
        warn_html = (
            "<div style='margin-top:10px;padding:10px;border-radius:6px;"
            "background:rgba(239,68,68,0.06);border:1px solid #ef444420;'>"
            "<div style='color:#ef4444;font-size:0.78rem;margin-bottom:4px;'>تحذيرات النظام:</div>"
            f"<ul style='margin:0;padding-right:16px;color:#9ca3af;font-size:0.75rem;'>{warn_items}</ul>"
            "</div>"
        )

    admin_badge = (
        "<div style='background:rgba(239,68,68,0.08);border:1px solid #ef444430;"
        "border-radius:6px;padding:8px 14px;margin-bottom:12px;font-size:0.75rem;color:#ef4444;'>"
        "🔒 سجل المصادر الكامل — للمراجع الداخلي فقط | لا يُشارَك مع المستخدم الخارجي"
        "</div>"
    )
    content = admin_badge + _table(headers, rows_html) + ma_html + warn_html

    return _section(
        "14", "سجل المصادر الكامل — Full Source Log (Admin)",
        content, color="#ef4444",
    )


# ── Main injection entry point ────────────────────────────────────────────────

def inject_enhanced_sections(
    base_html: str,
    sourcing_result: SourcingResult,
    methods_result: MethodsResult,
    audience: str,
    currency: str = "QAR",
) -> str:
    """
    Inject enhanced sections 11–14 into base simulation HTML before </body>.

    audience="user"  → sections 11, 12, 13 (no source log)
    audience="admin" → sections 11, 12, 13, 14
    """
    new_html = (
        build_provenance_section(sourcing_result.provenance_table, audience)
        + build_applied_methods_section(methods_result, audience, currency)
        + build_comparison_table_section(methods_result.comparison_table, audience, currency)
    )

    if audience == "admin":
        new_html += build_source_log_section(
            sourcing_result.source_log,
            sourcing_result.mass_appraisal_summary,
            sourcing_result.warnings,
        )

    if "</body>" in base_html:
        return base_html.replace("</body>", new_html + "\n</body>", 1)
    return base_html + new_html
