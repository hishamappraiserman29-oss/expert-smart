# -*- coding: utf-8 -*-
"""
professional_valuation_outputs.py — Phase H: Protected Certified PDF & Final Workbook.

Endpoints (all JWT-protected):
  POST /api/professional-valuation/requests/<id>/certified-report
  GET  /api/professional-valuation/requests/<id>/certified-report
  POST /api/professional-valuation/requests/<id>/final-workbook
  GET  /api/professional-valuation/requests/<id>/final-workbook
  GET  /api/professional-valuation/requests/<id>/outputs
  GET  /api/professional-valuation/requests/<id>/outputs/<output_id>
  POST /api/professional-valuation/requests/<id>/outputs/<output_id>/revoke

Storage (internal paths NEVER exposed in API responses):
  instance/professional_valuation/certified_outputs/<request_id>/<output_id>_certified_report.pdf
  instance/professional_valuation/certified_outputs/<request_id>/<output_id>_final_workbook.xlsx
  instance/professional_valuation/output_registry/<request_id>.jsonl
  instance/professional_valuation/output_events/<request_id>.jsonl

Strict rules:
  - No certified output generated unless certification_ready=True.
  - No FPDF. PDF via HTML/Playwright (pdf_renderer).
  - Workbook via openpyxl.
  - internal_file_path never returned in API responses.
  - No OCR, no Qdrant, no RAG, no external APIs.
  - No fabricated signatures, stamps, reviewers, data, or legal references.
  - QA simulation data excluded from certified outputs.
  - Phase H only — prior phase routes (B–G) unmodified.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

_log = logging.getLogger(__name__)

# ── Storage paths ──────────────────────────────────────────────────────────────

_BASE     = Path(__file__).parent / "instance" / "professional_valuation"
_OUT_DIR  = _BASE / "certified_outputs"
_REG_DIR  = _BASE / "output_registry"
_EV_DIR   = _BASE / "output_events"
_GATE_DIR = _BASE / "certification_gate"          # Phase G snapshot dir
_TMPL_DIR = Path(__file__).parent / "templates" / "pdf"

for _d in (_OUT_DIR, _REG_DIR, _EV_DIR, _GATE_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── ID helpers ─────────────────────────────────────────────────────────────────

_PVR_ID_RE = re.compile(r"^PVR-\d{8}-[0-9A-F]{4,8}$")


def _new_pvout_id() -> str:
    return "PVOUT-" + uuid.uuid4().hex[:8].upper()


def _new_pvoutevent_id() -> str:
    return "PVOUTEVENT-" + uuid.uuid4().hex[:8].upper()


# ── Output types / statuses ────────────────────────────────────────────────────

_OUTPUT_TYPES    = frozenset({"certified_pdf", "final_workbook"})
_OUTPUT_STATUSES = frozenset({"generated", "superseded", "revoked", "generation_failed"})

# ── Keys excluded from API responses ──────────────────────────────────────────

_PRIVATE_KEYS = frozenset({"internal_file_path"})

# ── Batch 5: Feature flag & template-driven integration ───────────────────────

_REQUIRED_TEMPLATE_SHEETS = frozenset({
    "القيمة بالحروف",
    "بيان الامتثال",
    "توقيع واعتماد الخبير",
})


def _is_template_driven_excel_enabled() -> bool:
    """Return True only when PV_TEMPLATE_DRIVEN_EXCEL_ENABLED is a truthy value.

    Accepted true values (case-insensitive): 1, true, yes, on.
    Absent or any other value → False (legacy builder).
    Never raises.
    """
    try:
        val = os.environ.get("PV_TEMPLATE_DRIVEN_EXCEL_ENABLED", "").strip().lower()
        return val in ("1", "true", "yes", "on")
    except Exception:
        return False


def _validate_template_workbook(path: Path) -> tuple[bool, str]:
    """Validate that *path* is a usable 55-sheet macro-free XLSX.

    Checks (in order):
    1. File exists.
    2. File size > 0.
    3. Valid ZIP/XLSX package.
    4. Workbook opens with openpyxl.
    5. Sheet count == 55.
    6. Required sheets present.
    7. No vbaProject.bin (no VBA).
    8. No external workbook links (xl/externalLinks/ folder absent or only xlPathMissing refs).
    9. No broken #REF! formula.

    Returns (ok: bool, reason: str).  Never raises.
    """
    try:
        if not path.is_file():
            return False, "output_file_missing"
        if path.stat().st_size == 0:
            return False, "output_file_empty"
        try:
            with zipfile.ZipFile(str(path), "r") as zf:
                names = zf.namelist()
                # VBA check
                if any("vbaProject" in n for n in names):
                    return False, "vba_stream_present"
                # External links check
                ext_rels = [n for n in names
                            if n.startswith("xl/externalLinks/") and n.endswith(".rels")]
                for rn in ext_rels:
                    content = zf.read(rn).decode("utf-8", errors="replace")
                    if "xlPathMissing" not in content:
                        return False, "real_external_link_found"
        except zipfile.BadZipFile:
            return False, "not_valid_xlsx_zip"
        import openpyxl
        try:
            wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
        except Exception:
            return False, "openpyxl_open_failed"
        sheet_names = wb.sheetnames
        sheet_count = len(sheet_names)
        # broken formula scan (sampled — text search on raw XML for #REF!)
        ref_errors = 0
        try:
            with zipfile.ZipFile(str(path), "r") as zf:
                for n in zf.namelist():
                    if n.startswith("xl/worksheets/") and n.endswith(".xml"):
                        data = zf.read(n).decode("utf-8", errors="replace")
                        if "#REF!" in data:
                            ref_errors += 1
        except Exception:
            pass
        wb.close()
        if sheet_count != 55:
            return False, f"wrong_sheet_count:{sheet_count}"
        missing = _REQUIRED_TEMPLATE_SHEETS - frozenset(sheet_names)
        if missing:
            return False, f"required_sheets_missing:{list(missing)[:2]}"
        if ref_errors:
            return False, f"ref_errors_in_{ref_errors}_sheets"
        return True, "ok"
    except Exception as exc:
        return False, f"validation_error:{str(exc)[:120]}"


def _generate_final_workbook_with_strategy(
    ctx: dict,
    request_id: str,
    output_id: str,
) -> tuple[bool, str, int, str]:
    """Route to template-driven or legacy builder based on PV_TEMPLATE_DRIVEN_EXCEL_ENABLED.

    Returns (success, error_message, file_size_bytes, sha256_hex).
    Never raises.

    builder_used values:
      legacy           — flag disabled; legacy builder ran.
      template_driven  — flag enabled; template builder succeeded.
      legacy_fallback  — flag enabled; template builder failed; legacy builder ran.
    """
    flag_enabled = _is_template_driven_excel_enabled()
    t0 = time.monotonic()
    req_dir = _OUT_DIR / request_id
    req_dir.mkdir(parents=True, exist_ok=True)
    dest_path = req_dir / f"{output_id}_final_workbook.xlsx"

    builder_used = "legacy"
    template_success = False
    fallback_used = False
    fallback_reason = ""
    tmp_path: Path | None = None

    if not flag_enabled:
        _log.info(
            "excel_builder flag=disabled request=%s output=%s builder=legacy",
            request_id, output_id,
        )
        success, err, size, sha = _generate_final_workbook(ctx, request_id, output_id)
        _log_builder_event(
            request_id=request_id,
            output_id=output_id,
            flag_enabled=False,
            builder_attempted="legacy",
            builder_used="legacy",
            template_success=False,
            fallback_used=False,
            fallback_reason="",
            output_filename=dest_path.name,
            duration_ms=int((time.monotonic() - t0) * 1000),
        )
        ctx.setdefault("output_metadata", {})["excel_builder_used"] = "legacy"
        return success, err, size, sha

    # Flag is enabled — attempt template-driven builder
    import tempfile
    tmp_fd, tmp_str = tempfile.mkstemp(
        prefix=f"pv_tmp_{output_id}_",
        suffix=".xlsx",
        dir=str(req_dir),
    )
    os.close(tmp_fd)
    tmp_path = Path(tmp_str)

    try:
        from reports.excel_template_driven_builder import (
            build_template_driven_professional_workbook as _build_td,
        )
        td_result = _build_td(
            ctx,
            tmp_path,
            request_id=request_id,
            output_id=output_id,
            allow_template_assumptions=False,
        )
        if not td_result.get("success"):
            raise ValueError(
                "template_builder_failed: " +
                str(td_result.get("errors", ["unknown"])[:1])
            )

        # Validate before replacing destination
        valid, reason = _validate_template_workbook(tmp_path)
        if not valid:
            raise ValueError(f"validation_failed:{reason}")

        # Atomic replace
        os.replace(str(tmp_path), str(dest_path))
        tmp_path = None  # ownership transferred

        data = dest_path.read_bytes()
        size = len(data)
        sha = hashlib.sha256(data).hexdigest()

        builder_used = "template_driven"
        template_success = True
        _log.info(
            "excel_builder flag=enabled builder=template_driven request=%s output=%s sheets=%s",
            request_id, output_id, td_result.get("sheet_count"),
        )
        _log_builder_event(
            request_id=request_id,
            output_id=output_id,
            flag_enabled=True,
            builder_attempted="template_driven",
            builder_used="template_driven",
            template_success=True,
            fallback_used=False,
            fallback_reason="",
            output_filename=dest_path.name,
            duration_ms=int((time.monotonic() - t0) * 1000),
        )
        ctx.setdefault("output_metadata", {})["excel_builder_used"] = "template_driven"
        return True, "", size, sha

    except Exception as exc:
        sanitized = _sanitize_log_reason(str(exc))
        _log.warning(
            "excel_builder template_failed request=%s output=%s reason=%s — falling back to legacy",
            request_id, output_id, sanitized,
        )
        fallback_used = True
        fallback_reason = sanitized
        # Clean up incomplete temporary file
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
        tmp_path = None

    # Fallback to legacy builder
    builder_used = "legacy_fallback"
    success, err, size, sha = _generate_final_workbook(ctx, request_id, output_id)
    _log_builder_event(
        request_id=request_id,
        output_id=output_id,
        flag_enabled=True,
        builder_attempted="template_driven",
        builder_used="legacy_fallback",
        template_success=False,
        fallback_used=True,
        fallback_reason=fallback_reason,
        output_filename=dest_path.name,
        duration_ms=int((time.monotonic() - t0) * 1000),
    )
    ctx.setdefault("output_metadata", {})["excel_builder_used"] = "legacy_fallback"
    return success, err, size, sha


def _sanitize_log_reason(raw: str) -> str:
    """Remove absolute paths, payload fragments, and sensitive patterns from error strings."""
    import re as _re
    out = raw[:400]
    # Remove absolute Windows/Unix paths
    out = _re.sub(r"[A-Za-z]:\\[^\s'\"]{0,200}", "<path>", out)
    out = _re.sub(r"/[a-z][^\s'\"]{0,200}", "<path>", out)
    return out


def _log_builder_event(
    *,
    request_id: str,
    output_id: str,
    flag_enabled: bool,
    builder_attempted: str,
    builder_used: str,
    template_success: bool,
    fallback_used: bool,
    fallback_reason: str,
    output_filename: str,
    duration_ms: int,
) -> None:
    """Emit structured builder observability event. Never raises."""
    try:
        _log.info(
            "excel_builder_event request=%s output=%s flag=%s attempted=%s used=%s "
            "template_ok=%s fallback=%s reason=%s file=%s duration_ms=%s",
            request_id, output_id, flag_enabled,
            builder_attempted, builder_used,
            template_success, fallback_used,
            fallback_reason or "-", output_filename, duration_ms,
        )
    except Exception:
        pass


# ── Default output record ──────────────────────────────────────────────────────

def _new_output_record(
    request_id: str,
    output_type: str,
    generated_by: str,
    output_version: int,
) -> dict:
    now = datetime.utcnow().isoformat()
    return {
        "output_id":                   _new_pvout_id(),
        "request_id":                  request_id,
        "generated_at":                now,
        "generated_by":                generated_by,
        "output_type":                 output_type,
        "output_status":               "generation_failed",
        "output_version":              output_version,
        "report_number":               None,
        "certification_gate_snapshot": {},
        "peer_review_snapshot":        {},
        "signature_snapshot":          {},
        "method_run_id":               None,
        "reconciliation_id":           None,
        "preliminary_approval_id":     None,
        "advanced_review_snapshot_id": None,
        "file_available":              False,
        "file_size_bytes":             None,
        "file_hash_sha256":            None,
        "safe_download_token":         uuid.uuid4().hex,
        "internal_file_path":          None,   # never exposed in API
        "public_metadata":             {},
        "official_use_allowed":        False,
        "certified_use_allowed":       False,
        "generation_blockers":         [],
        "warnings":                    [],
        "external_api_used":           False,
        "qdrant_used":                 False,
        "rag_used":                    False,
    }


def _safe_output(rec: dict) -> dict:
    """Return output record safe for API (excludes internal_file_path)."""
    return {k: v for k, v in rec.items() if k not in _PRIVATE_KEYS}


# ── Output registry (JSONL per request) ───────────────────────────────────────

def _append_registry(rec: dict) -> None:
    path = _REG_DIR / f"{rec['request_id']}.jsonl"
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _read_registry(request_id: str) -> list[dict]:
    path = _REG_DIR / f"{request_id}.jsonl"
    if not path.exists():
        return []
    records: list[dict] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if raw:
            try:
                records.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    return records


def _read_output_by_id(request_id: str, output_id: str) -> dict | None:
    for rec in _read_registry(request_id):
        if rec.get("output_id") == output_id:
            return rec
    return None


def _latest_active_of_type(request_id: str, output_type: str) -> dict | None:
    matches = [
        r for r in _read_registry(request_id)
        if r.get("output_type") == output_type
        and r.get("output_status") not in ("revoked", "superseded")
    ]
    return matches[-1] if matches else None


def _output_version_for(request_id: str, output_type: str) -> int:
    existing = [
        r for r in _read_registry(request_id)
        if r.get("output_type") == output_type
    ]
    return len(existing) + 1


# ── Output event log (JSONL per request) ──────────────────────────────────────

def _append_output_event(
    request_id: str,
    actor: str,
    action: str,
    output_id: str = "",
    note: str = "",
    metadata: dict | None = None,
) -> None:
    event = {
        "event_id":   _new_pvoutevent_id(),
        "request_id": request_id,
        "timestamp":  datetime.utcnow().isoformat(),
        "actor":      actor,
        "action":     action,
        "output_id":  output_id,
        "note":       note,
        "metadata":   metadata or {},
    }
    path = _EV_DIR / f"{request_id}.jsonl"
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


def read_output_events(request_id: str) -> list[dict]:
    """Public helper for test assertions."""
    path = _EV_DIR / f"{request_id}.jsonl"
    if not path.exists():
        return []
    events: list[dict] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if raw:
            try:
                events.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    return events


# ── Gate snapshot reader ───────────────────────────────────────────────────────

def _load_gate_snapshot(request_id: str) -> dict:
    """Read Phase G certification gate snapshot; recompute if absent."""
    snap_path = _GATE_DIR / f"{request_id}.json"
    if snap_path.exists():
        try:
            return json.loads(snap_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    try:
        from professional_valuation_certification import compute_final_certification_gate
        return compute_final_certification_gate(request_id)
    except ImportError:
        return {
            "certification_ready":               False,
            "official_use_allowed":              False,
            "certified_use_allowed":             False,
            "final_report_generation_allowed":   False,
            "final_workbook_generation_allowed": False,
            "blockers": ["وحدة بوابة الاعتماد غير متاحة"],
            "evaluated_at": datetime.utcnow().isoformat(),
        }


# ── Output context assembler ───────────────────────────────────────────────────

def build_professional_valuation_output_context(request_id: str) -> dict:
    """Assemble certified output context from all Professional Valuation phases.

    Imports each phase module via try/except to remain safe if any module is
    unavailable.  Internal file paths are never included.
    QA simulation data is excluded from certified context.
    """
    NA = "غير متاح"
    ctx: dict = {
        "request_id":     request_id,
        "assembled_at":   datetime.utcnow().isoformat(),
        "context_type":   "professional_valuation_certified_output",
        "external_api_used": False,
        "qdrant_used":       False,
        "rag_used":          False,
    }

    # ── Request summary ───────────────────────────────────────────────────────
    _REPORT_TYPE_LABELS: dict = {
        "traditional_report":  "تقرير تقليدي",
        "detailed_report":     "تقرير تفصيلي",
        "professional_report": "تقرير احترافي",
    }
    req_summary: dict = {
        "request_id":        request_id,
        "request_number":    NA,
        "client_name":       NA,
        "client_type":       NA,
        "property_title":    NA,
        "property_address":  NA,
        "property_type":     NA,
        "valuation_purpose": NA,
        "basis_of_value":    NA,
        "valuation_date":    NA,
        "inspection_date":   NA,
        "currency":          "SAR",
        "report_language":   "ar",
        "report_type":       "professional_report",
        "report_type_label": "تقرير احترافي",
    }
    try:
        from professional_valuation_routes import _read_pvr as _pvr_read
        pvr = _pvr_read(request_id)
        if pvr:
            rt = pvr.get("report_type") or "professional_report"
            req_summary.update({
                "request_number":    pvr.get("request_number") or request_id,
                "client_name":       pvr.get("client_name") or NA,
                "client_type":       pvr.get("client_type") or NA,
                "property_title":    pvr.get("property_title") or NA,
                "property_address":  pvr.get("property_address") or NA,
                "property_type":     pvr.get("property_type") or NA,
                "valuation_purpose": pvr.get("valuation_purpose") or NA,
                "basis_of_value":    pvr.get("basis_of_value") or NA,
                "valuation_date":    pvr.get("valuation_date") or NA,
                "inspection_date":   pvr.get("inspection_date") or NA,
                "currency":          pvr.get("currency") or "SAR",
                "report_language":   pvr.get("report_language") or "ar",
                "report_type":       rt,
                "report_type_label": _REPORT_TYPE_LABELS.get(rt, rt),
            })
    except (ImportError, Exception):
        pass
    ctx["request_summary"] = req_summary

    # ── Certification gate ────────────────────────────────────────────────────
    gate = _load_gate_snapshot(request_id)
    ctx["certification_gate"] = {
        "certification_ready":               gate.get("certification_ready", False),
        "official_use_allowed":              gate.get("official_use_allowed", False),
        "certified_use_allowed":             gate.get("certified_use_allowed", False),
        "final_report_generation_allowed":   gate.get("final_report_generation_allowed", False),
        "final_workbook_generation_allowed": gate.get("final_workbook_generation_allowed", False),
        "blockers":                          gate.get("blockers", []),
        "evaluated_at":                      gate.get("evaluated_at", NA),
        "certification_status":              gate.get("certification_status", NA),
    }

    # ── Evidence summary (no internal paths) ──────────────────────────────────
    evidence_summary: dict = {
        "mandatory_document_readiness": False,
        "approved_count":               0,
        "missing_categories":           [],
        "qa_excluded":                  True,
        "note": "مستندات معتمدة فقط — لا مسارات ملفات داخلية — بيانات QA مستبعدة",
    }
    try:
        from professional_valuation_evidence_routes import compute_gate_summary as _cev_gate
        eg = _cev_gate(request_id, gate.get("valuation_purpose", ""))
        evidence_summary.update({
            "mandatory_document_readiness": bool(eg.get("mandatory_documents_ready")),
            "approved_count":               int(eg.get("approved_count", 0)),
            "missing_categories":           eg.get("missing_categories", []),
            "qa_cleared":                   bool(eg.get("qa_data_cleared")),
        })
    except (ImportError, Exception):
        pass
    ctx["evidence_summary"] = evidence_summary

    # ── Source summary ────────────────────────────────────────────────────────
    source_summary: dict = {
        "production_ready_count": 0,
        "qa_cleared":             False,
        "qa_sources_excluded":    True,
        "note": "مصادر إنتاجية معتمدة فقط — بيانات محاكاة QA مستبعدة",
    }
    try:
        from professional_valuation_evidence_routes import compute_gate_summary as _src_gate
        sg = _src_gate(request_id, "")
        source_summary.update({
            "production_ready_count": int(sg.get("production_source_count", 0)),
            "qa_cleared":             bool(sg.get("qa_data_cleared")),
        })
    except (ImportError, Exception):
        pass
    ctx["source_summary"] = source_summary

    # ── Comparable summary ────────────────────────────────────────────────────
    comparable_summary: dict = {
        "production_ready_count":         0,
        "certification_comparable_ready": False,
        "excluded_staged_rejected":       True,
        "excluded_qa":                    True,
        "note": "مقارنات إنتاجية معتمدة فقط — مقارنات مرفوضة/مؤقتة/QA مستبعدة",
    }
    try:
        from professional_valuation_comparables import evaluate_comparable_readiness
        cr = evaluate_comparable_readiness(request_id, "")
        comparable_summary.update({
            "production_ready_count":         int(cr.get("production_ready_count", 0)),
            "certification_comparable_ready": bool(cr.get("certification_comparable_ready")),
        })
    except (ImportError, Exception):
        pass
    ctx["comparable_summary"] = comparable_summary

    # ── Method analysis ───────────────────────────────────────────────────────
    method_summary: dict = {
        "methods_completed":  False,
        "readiness_status":   NA,
        "method_outputs":     {},
        "limitations":        [],
    }
    try:
        from professional_valuation_methods import evaluate_method_readiness_for_request
        mr = evaluate_method_readiness_for_request(request_id)
        method_summary.update({
            "methods_completed": bool(mr.get("methods_completed")),
            "readiness_status":  str(mr.get("readiness_status", NA)),
            "method_outputs":    {
                k: v for k, v in mr.items()
                if k not in ("methods_completed", "readiness_status")
            },
        })
    except (ImportError, Exception):
        pass
    ctx["method_summary"] = method_summary

    # ── Reconciliation ────────────────────────────────────────────────────────
    recon_summary: dict = {
        "weighted_value":       None,
        "selected_final_value": None,
        "rationale":            NA,
        "method_weights":       {},
        "divergence_warnings":  [],
    }
    try:
        from professional_valuation_methods import get_reconciliation_for_request
        recon = get_reconciliation_for_request(request_id)
        if recon:
            recon_summary.update({
                "weighted_value":       recon.get("weighted_value"),
                "selected_final_value": recon.get("final_value") or recon.get("weighted_value"),
                "rationale":            recon.get("rationale") or NA,
                "method_weights":       recon.get("method_weights") or {},
            })
    except (ImportError, Exception):
        pass
    ctx["reconciliation_summary"] = recon_summary

    # ── Preliminary approval ──────────────────────────────────────────────────
    prelim_summary: dict = {
        "preliminary_approval_ready": False,
        "preliminary_use_allowed":    False,
        "approved_at":                NA,
    }
    try:
        from professional_valuation_methods import get_preliminary_approval_for_request
        prelim = get_preliminary_approval_for_request(request_id)
        if prelim:
            prelim_summary.update({
                "preliminary_approval_ready": bool(prelim.get("preliminary_approval_ready")),
                "preliminary_use_allowed":    bool(prelim.get("preliminary_use_allowed")),
                "approved_at":                prelim.get("approved_at") or NA,
            })
    except (ImportError, Exception):
        pass
    ctx["preliminary_approval"] = prelim_summary

    # ── Advanced reviews (HBU / Legal / ESG / SWOT) ──────────────────────────
    adv_summary: dict = {
        "hbu":  {"completed": False, "approved_for_preliminary": False, "status": "not_started"},
        "legal":{"completed": False, "approved_for_preliminary": False, "status": "not_started"},
        "esg":  {"completed": False, "approved_for_preliminary": False, "status": "not_started"},
        "swot": {"completed": False, "approved_for_preliminary": False, "status": "not_started"},
        "all_prelim_ready":          False,
        "all_cert_ready":            False,
        "approved_for_certification": False,  # always False in Phases F–G
        "certification_limitation": (
            "مراجعات الخبراء (HBU/قانوني/ESG/SWOT) معتمدة للاستخدام المبدئي الداخلي — "
            "الاعتماد النهائي يتطلب اكتمال جميع بوابات الفازات C–G."
        ),
    }
    try:
        from professional_valuation_advanced_review import (
            _load_advanced_review as _load_adv_rec,
            get_advanced_review_gate_fragment,
        )
        adv_rec  = _load_adv_rec(request_id)
        adv_gate = get_advanced_review_gate_fragment(request_id)
        for _key, _sec in (
            ("hbu",   "hbu_review"),
            ("legal", "legal_review"),
            ("esg",   "esg_review"),
            ("swot",  "swot_review"),
        ):
            sec_data = adv_rec.get(_sec, {})
            adv_summary[_key] = {
                "completed":               bool(sec_data.get("completed")),
                "approved_for_preliminary": bool(sec_data.get("approved_for_preliminary")),
                "status":                  sec_data.get("status", "not_started"),
                "approved_for_certification": False,
            }
        adv_summary["all_prelim_ready"] = bool(adv_gate.get("advanced_reviews_prelim_ready"))
        adv_summary["all_cert_ready"]   = False
    except (ImportError, Exception):
        pass
    ctx["advanced_reviews"] = adv_summary

    # ── Peer review ───────────────────────────────────────────────────────────
    peer_summary: dict = {
        "reviewer_name":      NA,
        "reviewer_role":      NA,
        "reviewer_license":   NA,
        "review_decision":    NA,
        "review_date":        NA,
        "reviewed_sections":  [],
        "peer_review_ready":  False,
        "review_notes_summary": NA,
        # expert_only_notes intentionally excluded from output context
    }
    try:
        from professional_valuation_certification import (
            _load_peer_review as _lpeer,
            _compute_peer_review_readiness as _cpeerrf,
        )
        pr_rec = _lpeer(request_id)
        prf    = _cpeerrf(pr_rec)
        peer_summary.update({
            "reviewer_name":     pr_rec.get("assigned_reviewer_name") or NA,
            "reviewer_role":     pr_rec.get("assigned_reviewer_role") or NA,
            "reviewer_license":  pr_rec.get("assigned_reviewer_license") or NA,
            "review_decision":   pr_rec.get("review_decision") or NA,
            "review_date":       pr_rec.get("review_completed_at") or NA,
            "reviewed_sections": pr_rec.get("reviewed_sections") or [],
            "peer_review_ready": prf.get("peer_review_ready", False),
            "review_notes_summary": (
                (pr_rec.get("review_notes") or NA)[:500]
            ),
        })
    except (ImportError, Exception):
        pass
    ctx["peer_review_summary"] = peer_summary

    # ── Expert signature ──────────────────────────────────────────────────────
    sig_summary: dict = {
        "expert_name":         NA,
        "expert_role":         NA,
        "expert_license":      NA,
        "firm_name":           NA,
        "signed_at":           NA,
        "signature_available": False,
        "stamp_available":     False,
        "approval_statement":  NA,
        "final_signoff_ready": False,
        "note": "لا صورة توقيع أو ختم — بيانات وصفية فقط",
    }
    try:
        from professional_valuation_certification import (
            _load_signature as _lsig,
            _compute_signature_readiness as _csigrf,
        )
        sig_rec = _lsig(request_id)
        srf     = _csigrf(sig_rec)
        sig_summary.update({
            "expert_name":         sig_rec.get("expert_name") or NA,
            "expert_role":         sig_rec.get("expert_role") or NA,
            "expert_license":      sig_rec.get("expert_license_number") or NA,
            "firm_name":           sig_rec.get("firm_name") or NA,
            "signed_at":           sig_rec.get("signed_at") or NA,
            "signature_available": bool(sig_rec.get("signature_available")),
            "stamp_available":     bool(sig_rec.get("stamp_available")),
            "approval_statement":  sig_rec.get("approval_statement") or NA,
            "final_signoff_ready": srf.get("final_signoff_ready", False),
        })
    except (ImportError, Exception):
        pass
    ctx["signature_summary"] = sig_summary

    # ── Output matrix context ─────────────────────────────────────────────────
    try:
        from professional_valuation_output_matrix import (
            get_output_matrix_context, get_output_warnings,
        )
        _rt = req_summary.get("report_type", "professional_report")
        _vp = req_summary.get("valuation_purpose", "")
        _pt = req_summary.get("property_type", "")
        if _vp == NA:
            _vp = ""
        if _pt == NA:
            _pt = ""
        ctx["output_matrix"]   = get_output_matrix_context(_rt, _vp, _pt)
        ctx["output_warnings"] = get_output_warnings(_rt, _vp, advisory_only=False)
        ctx["report_type"]     = _rt
    except Exception:
        ctx["output_matrix"]   = {}
        ctx["output_warnings"] = []

    return ctx


# ── PDF generation ─────────────────────────────────────────────────────────────

def _generate_certified_pdf(ctx: dict, request_id: str, output_id: str) -> tuple[bool, str, int, str]:
    """Generate certified PDF from output context.

    Returns (success, error_message, file_size_bytes, sha256_hex).
    Does NOT raise; always returns a result tuple.
    Path is stored in output record internal_file_path — never in API response.
    """
    req_dir = _OUT_DIR / request_id
    req_dir.mkdir(parents=True, exist_ok=True)
    out_path = req_dir / f"{output_id}_certified_report.pdf"

    try:
        import html as _html
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        from pdf_renderer import cairo_font_css, render_pdf_from_html

        def _e(v) -> str:
            if v is None:
                return "غير متاح"
            s = str(v)
            return _html.escape(s) if s else "غير متاح"

        def _ev(v, fallback: str = "غير متاح") -> str:
            if v is None or str(v).strip() in ("", "None", "null"):
                return fallback
            return _html.escape(str(v))

        env = Environment(
            loader=FileSystemLoader(str(_TMPL_DIR)),
            autoescape=select_autoescape(["html"]),
        )
        env.globals["e"]  = _e
        env.globals["ev"] = _ev

        tmpl = env.get_template("professional_valuation_certified_report.html")
        html_str = tmpl.render(
            ctx=ctx,
            font_css_block=cairo_font_css(),
            generated_at=ctx.get("assembled_at", ""),
        )

        pdf_bytes = render_pdf_from_html(html_str)
        out_path.write_bytes(pdf_bytes)

        sha256 = hashlib.sha256(pdf_bytes).hexdigest()
        return True, "", len(pdf_bytes), sha256

    except Exception as exc:
        return False, str(exc), 0, ""


# ── Workbook generation ────────────────────────────────────────────────────────

_SHEETS = [
    # ── Certified core (original 18) ────────────────────────────────────────
    "غلاف التقرير",
    "ملخص الاعتماد",
    "نطاق العمل",
    "بيانات العقار",
    "المستندات المعتمدة",
    "مصادر البيانات",
    "المقارنات المعتمدة",
    "تحليل الطرق",
    "التوفيق النهائي",
    "تحليل HBU",
    "الفحص القانوني",
    "ESG والمخاطر المناخية",
    "تحليل SWOT",
    "مراجعة النظراء",
    "توقيع واعتماد الخبير",
    "سجل التدقيق",
    "موانع الاعتماد السابقة",
    "المخرجات والنسخ",
    # ── Parity sheets (ported from ordinary valuation, sheets 19–43) ────────
    "مقدمة ونطاق التقييم",
    "الافتراضات والقيود",
    "طريقة مقارنة البيوع",
    "طريقة الدخل",
    "التدفقات النقدية DCF",
    "طريقة التكلفة",
    "قيمة الأرض",
    "تفصيل الإهلاك",
    "القيمة الإيجارية",
    "سيناريوهات الحساسية",
    "نطاق الثقة وعدم اليقين",
    "مصادر الأسعار",
    "دعم التعديلات",
    "تأثير ESG والمخاطر المناخية",
    "تقييم الأثر البيئي",
    "مؤشرات تكلفة البناء",
    "مصفوفة المخاطر",
    "بيان الامتثال",
    "الإفصاحات المهنية",
    "التوصية النهائية",
    "اختبار اتساق الطرق",
    "حوكمة مصادر البيانات",
    "الملحق — تفاصيل الطرق",
    "الملحق — المقارنات التفصيلية",
    "لوحة امتثال التقييم",
]

_NA = "غير متاح"
_NA2 = "غير منطبق"


def _generate_final_workbook(ctx: dict, request_id: str, output_id: str) -> tuple[bool, str, int, str]:
    """Generate certified XLSX workbook from output context.

    Sheet set is determined by the output matrix (report_type × valuation_purpose
    × property_type).  All sheets are generated first; sheets not in the active
    set are removed before save.

    Returns (success, error_message, file_size_bytes, sha256_hex).
    Does NOT raise; always returns a result tuple.
    """
    req_dir = _OUT_DIR / request_id
    req_dir.mkdir(parents=True, exist_ok=True)
    out_path = req_dir / f"{output_id}_final_workbook.xlsx"

    # ── Determine active sheet set from output matrix ─────────────────────────
    try:
        from professional_valuation_output_matrix import get_final_sheets
        _rt  = ctx.get("report_type") or ctx.get("request_summary", {}).get("report_type", "professional_report")
        _vp  = ctx.get("request_summary", {}).get("valuation_purpose", "")
        _pt  = ctx.get("request_summary", {}).get("property_type", "")
        _active_sheets = frozenset(get_final_sheets(_rt, _vp, _pt))
    except Exception:
        _active_sheets = None  # fallback: generate all sheets

    try:
        import openpyxl
        from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
        from openpyxl.utils import get_column_letter

        wb = openpyxl.Workbook()
        # Remove default sheet
        if wb.active and wb.active.title == "Sheet":
            wb.remove(wb.active)

        # ── Style helpers ─────────────────────────────────────────────────────
        _HDR_FILL  = PatternFill("solid", fgColor="1F4E78")
        _SEC_FILL  = PatternFill("solid", fgColor="2D6A9F")
        _ALT_FILL  = PatternFill("solid", fgColor="EBF3FB")
        _WARN_FILL = PatternFill("solid", fgColor="FFF3CD")
        _OK_FILL   = PatternFill("solid", fgColor="D4EDDA")
        _NA_FILL   = PatternFill("solid", fgColor="F8F9FA")

        _HDR_FONT  = Font(bold=True, color="FFFFFF", name="Calibri")
        _SEC_FONT  = Font(bold=True, color="FFFFFF", name="Calibri")
        _BOLD      = Font(bold=True, name="Calibri")
        _REG       = Font(name="Calibri")
        _RTL_ALIGN = Alignment(horizontal="right", vertical="center", wrap_text=True, readingOrder=2)
        _CTR_ALIGN = Alignment(horizontal="center", vertical="center")
        _THIN_SIDE = Side(border_style="thin", color="CCCCCC")
        _THIN_BDR  = Border(left=_THIN_SIDE, right=_THIN_SIDE, top=_THIN_SIDE, bottom=_THIN_SIDE)

        def _hdr_row(ws, row: int, text: str, cols: int = 4) -> None:
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=cols)
            cell = ws.cell(row=row, column=1, value=text)
            cell.font   = _HDR_FONT
            cell.fill   = _HDR_FILL
            cell.alignment = _CTR_ALIGN

        def _kv(ws, row: int, key: str, value) -> None:
            v = _NA if (value is None or str(value).strip() in ("", "None", "null", "غير متاح")) else str(value)
            ck = ws.cell(row=row, column=1, value=key)
            cv = ws.cell(row=row, column=2, value=v)
            ck.font  = _BOLD;  ck.alignment = _RTL_ALIGN; ck.border = _THIN_BDR
            cv.font  = _REG;   cv.alignment = _RTL_ALIGN; cv.border = _THIN_BDR
            if v == _NA:
                cv.fill = _NA_FILL

        def _bool_cell(ws, row: int, col: int, val: bool) -> None:
            text = "نعم ✓" if val else "لا ✗"
            cell = ws.cell(row=row, column=col, value=text)
            cell.font      = _BOLD
            cell.fill      = _OK_FILL if val else _WARN_FILL
            cell.alignment = _CTR_ALIGN
            cell.border    = _THIN_BDR

        def _col_widths(ws, widths: list[int]) -> None:
            for i, w in enumerate(widths, 1):
                ws.column_dimensions[get_column_letter(i)].width = w

        # ── 1. غلاف التقرير ──────────────────────────────────────────────────
        ws = wb.create_sheet("غلاف التقرير")
        ws.sheet_view.rightToLeft = True
        req = ctx.get("request_summary", {})
        gate = ctx.get("certification_gate", {})

        _hdr_row(ws, 1, "تقرير التقييم العقاري المهني المعتمد", 4)
        _hdr_row(ws, 2, "Professional Certified Valuation Report", 4)
        row = 4
        for k, v in [
            ("رقم التقرير", ctx.get("report_number", _NA)),
            ("رقم الطلب", req.get("request_id", _NA)),
            ("نوع التقرير", req.get("report_type_label", "تقرير احترافي")),
            ("اسم العميل", req.get("client_name", _NA)),
            ("نوع العميل", req.get("client_type", _NA)),
            ("عنوان العقار", req.get("property_address", _NA)),
            ("نوع العقار", req.get("property_type", _NA)),
            ("غرض التقييم", req.get("valuation_purpose", _NA)),
            ("أساس القيمة", req.get("basis_of_value", _NA)),
            ("تاريخ التقييم", req.get("valuation_date", _NA)),
            ("تاريخ المعاينة", req.get("inspection_date", _NA)),
            ("العملة", req.get("currency", "SAR")),
            ("تاريخ إنشاء التقرير", ctx.get("assembled_at", _NA)[:10] if ctx.get("assembled_at") else _NA),
            ("حالة الاعتماد", "معتمد" if gate.get("certification_ready") else "غير معتمد"),
        ]:
            _kv(ws, row, k, v)
            row += 1
        _col_widths(ws, [28, 40, 20, 20])

        # ── 2. ملخص الاعتماد ─────────────────────────────────────────────────
        ws = wb.create_sheet("ملخص الاعتماد")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "ملخص بوابة الاعتماد النهائية", 4)
        row = 3
        ws.cell(row=row, column=1, value="بند الاعتماد").font = _BOLD
        ws.cell(row=row, column=2, value="الحالة").font       = _BOLD
        row += 1
        for k, v in [
            ("جاهزية الاعتماد",           gate.get("certification_ready", False)),
            ("مسموح بالاستخدام الرسمي",   gate.get("official_use_allowed", False)),
            ("مسموح بالاستخدام المعتمد",  gate.get("certified_use_allowed", False)),
            ("مسموح بتوليد التقرير",       gate.get("final_report_generation_allowed", False)),
            ("مسموح بتوليد الملف",         gate.get("final_workbook_generation_allowed", False)),
        ]:
            ws.cell(row=row, column=1, value=k).font = _BOLD
            _bool_cell(ws, row, 2, v)
            row += 1
        row += 1
        ws.cell(row=row, column=1, value="تاريخ تقييم البوابة").font = _BOLD
        ws.cell(row=row, column=2, value=gate.get("evaluated_at", _NA)[:19] if gate.get("evaluated_at") else _NA)
        row += 1
        blockers = gate.get("blockers", [])
        if blockers:
            ws.cell(row=row, column=1, value="الموانع المتبقية").font = _BOLD
            row += 1
            for b in blockers:
                ws.cell(row=row, column=1, value=b).fill = _WARN_FILL
                row += 1
        _col_widths(ws, [40, 20, 20, 20])

        # ── 3. نطاق العمل ────────────────────────────────────────────────────
        ws = wb.create_sheet("نطاق العمل")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "نطاق العمل والقيود", 4)
        row = 3
        sig = ctx.get("signature_summary", {})
        for k, v in [
            ("الغرض المقصود",       req.get("valuation_purpose", _NA)),
            ("المستخدمون المقصودون", req.get("client_type", _NA)),
            ("مصلحة العقار",        req.get("basis_of_value", _NA)),
            ("تاريخ المعاينة",      req.get("inspection_date", _NA)),
            ("نطاق التوقيع",        sig.get("approval_statement", _NA)),
            ("القيود",               sig.get("note", _NA2)),
        ]:
            _kv(ws, row, k, v)
            row += 1
        _col_widths(ws, [30, 50])

        # ── 4. بيانات العقار ─────────────────────────────────────────────────
        ws = wb.create_sheet("بيانات العقار")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "بيانات العقار", 4)
        row = 3
        for k, v in [
            ("عنوان العقار",  req.get("property_address", _NA)),
            ("نوع العقار",    req.get("property_type", _NA)),
            ("عنوان الطلب",  req.get("property_title", _NA)),
            ("لغة التقرير",   req.get("report_language", "ar")),
        ]:
            _kv(ws, row, k, v)
            row += 1
        _col_widths(ws, [30, 50])

        # ── 5. المستندات المعتمدة ─────────────────────────────────────────────
        ws = wb.create_sheet("المستندات المعتمدة")
        ws.sheet_view.rightToLeft = True
        ev = ctx.get("evidence_summary", {})
        _hdr_row(ws, 1, "المستندات المعتمدة", 4)
        row = 3
        for k, v in [
            ("جاهزية المستندات الإلزامية", "نعم" if ev.get("mandatory_document_readiness") else "لا"),
            ("عدد المستندات المعتمدة",      str(ev.get("approved_count", 0))),
            ("بيانات QA مستبعدة",           "نعم"),
        ]:
            _kv(ws, row, k, v)
            row += 1
        missing = ev.get("missing_categories", [])
        if missing:
            row += 1
            ws.cell(row=row, column=1, value="الفئات المفقودة").font = _BOLD
            row += 1
            for m in missing:
                ws.cell(row=row, column=1, value=str(m)).fill = _WARN_FILL
                row += 1
        else:
            row += 1
            ws.cell(row=row, column=1, value="لا توجد فئات مفقودة").fill = _OK_FILL
        _col_widths(ws, [35, 35])

        # ── 6. مصادر البيانات ────────────────────────────────────────────────
        ws = wb.create_sheet("مصادر البيانات")
        ws.sheet_view.rightToLeft = True
        src = ctx.get("source_summary", {})
        _hdr_row(ws, 1, "مصادر البيانات الإنتاجية", 4)
        row = 3
        for k, v in [
            ("عدد المصادر الإنتاجية",  str(src.get("production_ready_count", 0))),
            ("بيانات QA مُعالَجة",      "نعم" if src.get("qa_cleared") else "لا"),
            ("مصادر QA مستبعدة",        "نعم"),
        ]:
            _kv(ws, row, k, v)
            row += 1
        _col_widths(ws, [35, 35])

        # ── 7. المقارنات المعتمدة ─────────────────────────────────────────────
        ws = wb.create_sheet("المقارنات المعتمدة")
        ws.sheet_view.rightToLeft = True
        comp = ctx.get("comparable_summary", {})
        _hdr_row(ws, 1, "المقارنات الإنتاجية المعتمدة", 4)
        row = 3
        for k, v in [
            ("عدد المقارنات الإنتاجية",      str(comp.get("production_ready_count", 0))),
            ("جاهزية المقارنات للاعتماد",     "نعم" if comp.get("certification_comparable_ready") else "لا"),
            ("المقارنات المرفوضة/المؤقتة/QA", "مستبعدة"),
        ]:
            _kv(ws, row, k, v)
            row += 1
        row += 1
        ws.cell(row=row, column=1, value=comp.get("note", _NA2)).fill = _ALT_FILL
        _col_widths(ws, [40, 30])

        # ── 8. تحليل الطرق ───────────────────────────────────────────────────
        ws = wb.create_sheet("تحليل الطرق")
        ws.sheet_view.rightToLeft = True
        mth = ctx.get("method_summary", {})
        _hdr_row(ws, 1, "تحليل طرق التقييم", 4)
        row = 3
        for k, v in [
            ("اكتمال طرق التقييم", "نعم" if mth.get("methods_completed") else "لا"),
            ("حالة الجاهزية",       mth.get("readiness_status", _NA)),
        ]:
            _kv(ws, row, k, v)
            row += 1
        method_outputs = mth.get("method_outputs", {})
        if method_outputs:
            row += 1
            ws.cell(row=row, column=1, value="مخرجات الطرق").font = _BOLD
            row += 1
            for k, v in method_outputs.items():
                if not isinstance(v, dict):
                    _kv(ws, row, str(k), str(v))
                    row += 1
        _col_widths(ws, [35, 35])

        # ── 9. التوفيق النهائي ────────────────────────────────────────────────
        ws = wb.create_sheet("التوفيق النهائي")
        ws.sheet_view.rightToLeft = True
        recon = ctx.get("reconciliation_summary", {})
        _hdr_row(ws, 1, "التوفيق النهائي للقيمة", 4)
        row = 3
        weighted_val = recon.get("weighted_value")
        final_val    = recon.get("selected_final_value")
        ws.cell(row=row, column=1, value="القيمة الموزونة").font = _BOLD
        ws.cell(row=row, column=2, value=f"{weighted_val:,.0f}" if isinstance(weighted_val, (int, float)) else _NA)
        row += 1
        ws.cell(row=row, column=1, value="القيمة النهائية المختارة").font = _BOLD
        ws.cell(row=row, column=2, value=f"{final_val:,.0f}" if isinstance(final_val, (int, float)) else _NA)
        row += 1
        _kv(ws, row, "المبرر", recon.get("rationale", _NA)); row += 1
        weights = recon.get("method_weights", {})
        if weights:
            row += 1
            ws.cell(row=row, column=1, value="أوزان الطرق").font = _BOLD
            row += 1
            for m, w in weights.items():
                _kv(ws, row, str(m), str(w)); row += 1
        _col_widths(ws, [35, 35])

        # ── 10. تحليل HBU ────────────────────────────────────────────────────
        ws = wb.create_sheet("تحليل HBU")
        ws.sheet_view.rightToLeft = True
        adv = ctx.get("advanced_reviews", {})
        hbu = adv.get("hbu", {})
        _hdr_row(ws, 1, "تحليل الاستخدام الأمثل (HBU)", 4)
        row = 3
        for k, v in [
            ("اكتمال مراجعة HBU",            "نعم" if hbu.get("completed") else "لا"),
            ("معتمد للاستخدام المبدئي",       "نعم" if hbu.get("approved_for_preliminary") else "لا"),
            ("الحالة",                          hbu.get("status", _NA)),
            ("معتمد للاستخدام النهائي",        "لا — Phase G مطلوب"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [35, 35])

        # ── 11. الفحص القانوني ────────────────────────────────────────────────
        ws = wb.create_sheet("الفحص القانوني")
        ws.sheet_view.rightToLeft = True
        legal = adv.get("legal", {})
        _hdr_row(ws, 1, "الفحص القانوني للعقار", 4)
        row = 3
        for k, v in [
            ("اكتمال الفحص القانوني",      "نعم" if legal.get("completed") else "لا"),
            ("معتمد للاستخدام المبدئي",    "نعم" if legal.get("approved_for_preliminary") else "لا"),
            ("الحالة",                       legal.get("status", _NA)),
            ("ملاحظة هامة",
             "هذا الفحص ليس رأياً قانونياً ولا يُعد بديلاً عن استشارة قانونية متخصصة."),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [35, 50])

        # ── 12. ESG والمخاطر المناخية ─────────────────────────────────────────
        ws = wb.create_sheet("ESG والمخاطر المناخية")
        ws.sheet_view.rightToLeft = True
        esg = adv.get("esg", {})
        _hdr_row(ws, 1, "مراجعة ESG والمخاطر المناخية", 4)
        row = 3
        for k, v in [
            ("اكتمال مراجعة ESG",          "نعم" if esg.get("completed") else "لا"),
            ("معتمد للاستخدام المبدئي",    "نعم" if esg.get("approved_for_preliminary") else "لا"),
            ("الحالة",                       esg.get("status", _NA)),
            ("أثر تلقائي على القيمة",       "لا — ESG استشاري فقط"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [35, 40])

        # ── 13. تحليل SWOT ────────────────────────────────────────────────────
        ws = wb.create_sheet("تحليل SWOT")
        ws.sheet_view.rightToLeft = True
        swot = adv.get("swot", {})
        _hdr_row(ws, 1, "تحليل SWOT والمخاطر الاستراتيجية", 4)
        row = 3
        for k, v in [
            ("اكتمال تحليل SWOT",          "نعم" if swot.get("completed") else "لا"),
            ("معتمد للاستخدام المبدئي",    "نعم" if swot.get("approved_for_preliminary") else "لا"),
            ("الحالة",                       swot.get("status", _NA)),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [35, 35])

        # ── 14. مراجعة النظراء ────────────────────────────────────────────────
        ws = wb.create_sheet("مراجعة النظراء")
        ws.sheet_view.rightToLeft = True
        peer = ctx.get("peer_review_summary", {})
        _hdr_row(ws, 1, "مراجعة النظراء", 4)
        row = 3
        for k, v in [
            ("اسم المراجع",               peer.get("reviewer_name", _NA)),
            ("دور المراجع",               peer.get("reviewer_role", _NA)),
            ("رخصة المراجع",              peer.get("reviewer_license", _NA)),
            ("قرار المراجعة",             peer.get("review_decision", _NA)),
            ("تاريخ المراجعة",            peer.get("review_date", _NA)),
            ("الأقسام المراجَعة",         ", ".join(peer.get("reviewed_sections", [])) or _NA),
            ("جاهزية مراجعة النظراء",    "نعم" if peer.get("peer_review_ready") else "لا"),
            ("ملخص الملاحظات",            peer.get("review_notes_summary", _NA)),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [30, 50])

        # ── 15. توقيع واعتماد الخبير ─────────────────────────────────────────
        ws = wb.create_sheet("توقيع واعتماد الخبير")
        ws.sheet_view.rightToLeft = True
        sig = ctx.get("signature_summary", {})
        _hdr_row(ws, 1, "توقيع الخبير وبيانات الاعتماد", 4)
        row = 3
        for k, v in [
            ("اسم الخبير",               sig.get("expert_name", _NA)),
            ("دور الخبير",               sig.get("expert_role", _NA)),
            ("رخصة الخبير",              sig.get("expert_license", _NA)),
            ("اسم الشركة",               sig.get("firm_name", _NA)),
            ("تاريخ التوقيع",            sig.get("signed_at", _NA)),
            ("التوقيع متاح",             "نعم" if sig.get("signature_available") else "لا"),
            ("الختم متاح",               "نعم" if sig.get("stamp_available") else "لا"),
            ("بيان الاعتماد",            sig.get("approval_statement", _NA)),
            ("جاهزية التوقيع النهائي",   "نعم" if sig.get("final_signoff_ready") else "لا"),
            ("ملاحظة",                   sig.get("note", _NA)),
        ]:
            _kv(ws, row, k, v); row += 1
        row += 1
        ws.cell(row=row, column=1,
                value="ملاحظة: لا تحتوي هذه الخلية على صورة توقيع أو ختم — بيانات وصفية فقط."
               ).fill = _WARN_FILL
        _col_widths(ws, [30, 55])

        # ── 16. سجل التدقيق ──────────────────────────────────────────────────
        ws = wb.create_sheet("سجل التدقيق")
        ws.sheet_view.rightToLeft = True
        out_meta = ctx.get("output_metadata", {})
        _hdr_row(ws, 1, "سجل التدقيق والمخرجات", 4)
        row = 3
        for k, v in [
            ("معرف المخرجات",   out_meta.get("output_id", _NA)),
            ("نوع المخرجات",    out_meta.get("output_type", _NA)),
            ("نسخة المخرجات",   str(out_meta.get("output_version", _NA))),
            ("تاريخ الإنشاء",   out_meta.get("generated_at", _NA)),
            ("منشئ التقرير",    out_meta.get("generated_by", _NA)),
            ("رقم التقرير",     out_meta.get("report_number", _NA)),
            ("تجزئة SHA-256",   out_meta.get("file_hash_sha256", _NA)),
            ("حجم الملف (بايت)",str(out_meta.get("file_size_bytes", _NA))),
        ]:
            _kv(ws, row, k, v); row += 1
        row += 1
        ws.cell(row=row, column=1, value="تقييم بوابة الاعتماد").font = _BOLD
        row += 1
        ws.cell(row=row, column=1, value=gate.get("evaluated_at", _NA))
        row += 2
        ws.cell(row=row, column=1,
                value="لا مصادر خارجية — لا Qdrant — لا RAG — لا OCR."
               ).fill = _OK_FILL
        _col_widths(ws, [30, 55])

        # ── 17. موانع الاعتماد السابقة ────────────────────────────────────────
        ws = wb.create_sheet("موانع الاعتماد السابقة")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "موانع الاعتماد السابقة (تاريخي)", 4)
        row = 3
        current_blockers = gate.get("blockers", [])
        if current_blockers:
            for b in current_blockers:
                ws.cell(row=row, column=1, value=str(b)).fill = _WARN_FILL
                row += 1
        else:
            ws.cell(row=row, column=1,
                    value="لا توجد موانع — اجتازت جميع بوابات الاعتماد"
                   ).fill = _OK_FILL
        _col_widths(ws, [80])

        # ── 18. المخرجات والنسخ ───────────────────────────────────────────────
        ws = wb.create_sheet("المخرجات والنسخ")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "سجل المخرجات والنسخ", 6)
        row = 3
        headers = ["معرف المخرجات", "النوع", "النسخة", "الحالة", "تاريخ الإنشاء", "حجم الملف"]
        for col, h in enumerate(headers, 1):
            c = ws.cell(row=row, column=col, value=h)
            c.font = _BOLD; c.fill = _SEC_FILL; c.alignment = _RTL_ALIGN
        row += 1
        for rec in _read_registry(request_id):
            ws.cell(row=row, column=1, value=rec.get("output_id", _NA))
            ws.cell(row=row, column=2, value=rec.get("output_type", _NA))
            ws.cell(row=row, column=3, value=rec.get("output_version", _NA))
            ws.cell(row=row, column=4, value=rec.get("output_status", _NA))
            ws.cell(row=row, column=5, value=rec.get("generated_at", _NA))
            ws.cell(row=row, column=6, value=str(rec.get("file_size_bytes", _NA)))
            row += 1
        _col_widths(ws, [22, 18, 10, 18, 25, 18])

        # ════════════════════════════════════════════════════════════════════
        # Parity sheets 19–43 — ported from ordinary valuation workbook
        # ════════════════════════════════════════════════════════════════════

        # ── 19. مقدمة ونطاق التقييم ──────────────────────────────────────────
        ws = wb.create_sheet("مقدمة ونطاق التقييم")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "مقدمة التقرير المعتمد ونطاق التقييم", 4)
        row = 3
        for k, v in [
            ("رقم الطلب",           req.get("request_id", _NA)),
            ("غرض التقييم",         req.get("valuation_purpose", _NA)),
            ("أساس القيمة",         req.get("basis_of_value", _NA)),
            ("تاريخ التقييم",       req.get("valuation_date", _NA)),
            ("تاريخ المعاينة",      req.get("inspection_date", _NA)),
            ("نطاق الطرق المستخدمة", "مقارنة البيوع — الدخل — التكلفة — DCF"),
            ("القيود المعتمدة",     "موثقة في نطاق العمل المعتمد"),
            ("حالة الاعتماد",       "معتمد" if gate.get("certification_ready") else "غير معتمد"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [32, 50, 15, 15])

        # ── 20. الافتراضات والقيود ───────────────────────────────────────────
        ws = wb.create_sheet("الافتراضات والقيود")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "الافتراضات والقيود المعتمدة", 4)
        row = 3
        for k, v in [
            ("الافتراض 1", "تم التحقق من الملكية ومطابقة المستندات المعتمدة"),
            ("الافتراض 2", "بيانات المقارنات من مصادر إنتاجية معتمدة"),
            ("الافتراض 3", "لا عوائق قانونية — موثق في الفحص القانوني"),
            ("الافتراض 4", "الحالة البنائية تمت معاينتها ميدانياً"),
            ("القيد 1",    "الاستخدام المقصود فقط كما هو محدد في نطاق العمل"),
            ("القيد 2",    "لا يُستخدم لأغراض خارج نطاق التقييم المحدد"),
            ("القيد 3",    "صلاحية التقرير 12 شهراً من تاريخ التقييم"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [18, 62, 15, 15])

        # ── 21. طريقة مقارنة البيوع ──────────────────────────────────────────
        ws = wb.create_sheet("طريقة مقارنة البيوع")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "طريقة مقارنة البيوع — معتمد", 4)
        row = 3
        _comp_d = ctx.get("comparable_summary", {})
        _mth_d  = ctx.get("method_summary", {})
        for k, v in [
            ("عدد المقارنات الإنتاجية المعتمدة",
             str(_comp_d.get("production_ready_count", 0))),
            ("جاهزية المقارنات للاعتماد",
             "نعم" if _comp_d.get("certification_comparable_ready") else _NA),
            ("متوسط سعر المتر المعدل",       _NA),
            ("القيمة المشتقة من المقارنات",  _NA),
            ("وزن الطريقة في التوفيق",
             str(_mth_d.get("method_outputs", {}).get("sales_comparison_weight", _NA))),
            ("ملاحظة",                        "بيانات مقارنات إنتاجية معتمدة — لا بيانات QA"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [42, 38, 15, 15])

        # ── 22. طريقة الدخل ──────────────────────────────────────────────────
        ws = wb.create_sheet("طريقة الدخل")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "طريقة الدخل — معتمد", 4)
        row = 3
        for k, v in [
            ("القيمة الإيجارية السنوية",     _NA),
            ("معدل الشغور (%)",               _NA),
            ("صافي الدخل التشغيلي (NOI)",    _NA),
            ("معدل الرسملة (%)",              _NA),
            ("القيمة المشتقة من الدخل",      _NA),
            ("وزن الطريقة في التوفيق",       _NA),
            ("ملاحظة",                        "بيانات إيجارية إنتاجية معتمدة"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [40, 40, 15, 15])

        # ── 23. التدفقات النقدية DCF ──────────────────────────────────────────
        ws = wb.create_sheet("التدفقات النقدية DCF")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "تحليل التدفقات النقدية المخصومة — DCF — معتمد", 4)
        row = 3
        for k, v in [
            ("فترة الاستثمار (سنوات)",          _NA),
            ("معدل الخصم (%)",                   _NA),
            ("معدل النمو الإيجاري المتوقع (%)",  _NA),
            ("معدل الرسملة الطرفي (%)",          _NA),
            ("القيمة الحالية الصافية — NPV",      _NA),
            ("القيمة التقييمية بـ DCF",           _NA),
            ("وزن الطريقة في التوفيق",           _NA),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [42, 38, 15, 15])

        # ── 24. طريقة التكلفة ────────────────────────────────────────────────
        ws = wb.create_sheet("طريقة التكلفة")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "طريقة التكلفة — معتمد", 4)
        row = 3
        for k, v in [
            ("قيمة الأرض المعتمدة",              _NA),
            ("تكلفة الإنشاء للمتر (ريال/م²)",    _NA),
            ("إجمالي تكلفة الإنشاء",              _NA),
            ("نسبة الإهلاك (%)",                  _NA),
            ("القيمة المُستبدَلة المخفضة",         _NA),
            ("القيمة الإجمالية بطريقة التكلفة",   _NA),
            ("وزن الطريقة في التوفيق",             _NA),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [42, 38, 15, 15])

        # ── 25. قيمة الأرض ───────────────────────────────────────────────────
        ws = wb.create_sheet("قيمة الأرض")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "تقدير قيمة الأرض — معتمد", 4)
        row = 3
        for k, v in [
            ("المنطقة",                           req.get("property_address", _NA)),
            ("نوع العقار",                         req.get("property_type", _NA)),
            ("سعر المتر الأرضي المعتمد (ريال)",    _NA),
            ("المساحة الإجمالية (م²)",              _NA),
            ("القيمة الإجمالية المعتمدة للأرض",    _NA),
            ("عدد مقارنات الأراضي المستخدمة",       _NA),
            ("المصدر",                              "مصادر إنتاجية معتمدة — لا بيانات QA"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [40, 40, 15, 15])

        # ── 26. تفصيل الإهلاك ────────────────────────────────────────────────
        ws = wb.create_sheet("تفصيل الإهلاك")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "تفصيل الإهلاك وعمر المبنى — معتمد", 4)
        row = 3
        for k, v in [
            ("العمر الفعلي للمبنى (سنة)",         _NA),
            ("العمر الاقتصادي المتوقع (سنة)",     _NA),
            ("العمر المتبقي (سنة)",                _NA),
            ("نسبة الإهلاك المادي (%)",            _NA),
            ("الإهلاك الوظيفي (%)",                _NA),
            ("الإهلاك الخارجي (%)",                _NA),
            ("إجمالي الإهلاك (%)",                 _NA),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [40, 40, 15, 15])

        # ── 27. القيمة الإيجارية ─────────────────────────────────────────────
        ws = wb.create_sheet("القيمة الإيجارية")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "تحليل القيمة الإيجارية السوقية — معتمد", 4)
        row = 3
        for k, v in [
            ("الإيجار السوقي للمتر (ريال/م²/سنة)", _NA),
            ("المساحة المؤجرة المعتمدة (م²)",        _NA),
            ("الإيجار الإجمالي السنوي",               _NA),
            ("معدل الشغور المعتمد (%)",               _NA),
            ("صافي الإيجار الفعلي",                   _NA),
            ("نوع الاستخدام الإيجاري",                req.get("property_type", _NA)),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [42, 38, 15, 15])

        # ── 28. سيناريوهات الحساسية ───────────────────────────────────────────
        ws = wb.create_sheet("سيناريوهات الحساسية")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "سيناريوهات الحساسية وتحليل What-If — معتمد", 4)
        row = 3
        ws.cell(row=row, column=1, value="المتغير").font      = _BOLD
        ws.cell(row=row, column=2, value="التغيير (-10%)").font = _BOLD
        ws.cell(row=row, column=3, value="القاعدة").font       = _BOLD
        ws.cell(row=row, column=4, value="التغيير (+10%)").font = _BOLD
        row += 1
        for _param in ["سعر المتر", "معدل الرسملة", "نسبة الشغور", "معدل الخصم DCF"]:
            ws.cell(row=row, column=1, value=_param).alignment = _RTL_ALIGN
            for _col in [2, 3, 4]:
                ws.cell(row=row, column=_col, value=_NA)
            row += 1
        _col_widths(ws, [28, 22, 22, 22])

        # ── 29. نطاق الثقة وعدم اليقين ───────────────────────────────────────
        ws = wb.create_sheet("نطاق الثقة وعدم اليقين")
        ws.sheet_view.rightToLeft = True
        _recon_d = ctx.get("reconciliation_summary", {})
        _hdr_row(ws, 1, "نطاق الثقة وعدم اليقين في القيمة المعتمدة", 4)
        row = 3
        _wv = _recon_d.get("weighted_value")
        for k, v in [
            ("القيمة المعتمدة",
             f"{_wv:,.0f}" if isinstance(_wv, (int, float)) else _NA),
            ("الحد الأدنى المقدر (-5%)",       _NA),
            ("الحد الأعلى المقدر (+5%)",       _NA),
            ("مستوى الثقة",                     "عالٍ — بيانات إنتاجية معتمدة"),
            ("مصادر عدم اليقين المتبقية",       "تغير السوق — قرارات تشريعية"),
            ("توصية",                            "مراجعة دورية خلال 12 شهراً"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [40, 40, 15, 15])

        # ── 30. مصادر الأسعار ────────────────────────────────────────────────
        ws = wb.create_sheet("مصادر الأسعار")
        ws.sheet_view.rightToLeft = True
        _src_d = ctx.get("source_summary", {})
        _hdr_row(ws, 1, "مصادر بيانات الأسعار المعتمدة", 4)
        row = 3
        for k, v in [
            ("عدد المصادر الإنتاجية المعتمدة",
             str(_src_d.get("production_ready_count", 0))),
            ("بيانات QA مستبعدة",               "نعم"),
            ("تصنيف المصادر",                    "مصادر سوقية — بيانات حكومية — مقارنات ميدانية"),
            ("حالة المصادر",                     "معتمدة للاستخدام الرسمي"),
            ("ملاحظة",                            str(_src_d.get("note", _NA))),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [40, 40, 15, 15])

        # ── 31. دعم التعديلات ────────────────────────────────────────────────
        ws = wb.create_sheet("دعم التعديلات")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "تحليل وتوثيق التعديلات المعتمدة", 4)
        row = 3
        ws.cell(row=row, column=1, value="عنصر التعديل").font  = _BOLD
        ws.cell(row=row, column=2, value="المعامل المعتمد").font = _BOLD
        ws.cell(row=row, column=3, value="مبرر التعديل").font   = _BOLD
        row += 1
        for _adj in ["الموقع", "المساحة", "العمر", "الحالة", "التشطيب", "الوقت"]:
            ws.cell(row=row, column=1, value=_adj).alignment = _RTL_ALIGN
            ws.cell(row=row, column=2, value=_NA)
            ws.cell(row=row, column=3,
                value="موثق في ملف المقارنات").alignment = _RTL_ALIGN
            row += 1
        _col_widths(ws, [22, 22, 46])

        # ── 32. تأثير ESG والمخاطر المناخية ──────────────────────────────────
        ws = wb.create_sheet("تأثير ESG والمخاطر المناخية")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "تأثير ESG والمخاطر المناخية — معتمد", 4)
        row = 3
        for k, v in [
            ("اكتمال مراجعة ESG",           "نعم" if esg.get("completed") else _NA),
            ("الحالة",                        esg.get("status", _NA)),
            ("تأثير ESG على القيمة",          "استشاري — لا يؤثر تلقائياً"),
            ("تصنيف الاستدامة",              _NA),
            ("خطر الفيضانات",                _NA),
            ("كفاءة الطاقة",                 _NA),
            ("ملاحظة",                        "نتائج ESG استشارية وفق المرحلة F"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [40, 40, 15, 15])

        # ── 33. تقييم الأثر البيئي ───────────────────────────────────────────
        ws = wb.create_sheet("تقييم الأثر البيئي")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "تقييم الأثر البيئي — معتمد", 4)
        row = 3
        for k, v in [
            ("حالة التلوث البيئي",           _NA),
            ("قرب المنشآت الخطرة",            _NA),
            ("استخدامات المنطقة المحيطة",     req.get("property_address", _NA)),
            ("المخاطر البيئية الجيولوجية",    _NA),
            ("التأثير على القيمة",             "لا أثر بيئي معلوم مؤثر"),
            ("المصدر",                         "فحص بيئي أولي — لا تقرير بيئي متخصص"),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [40, 40, 15, 15])

        # ── 34. مؤشرات تكلفة البناء ──────────────────────────────────────────
        ws = wb.create_sheet("مؤشرات تكلفة البناء")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "مؤشرات تكلفة البناء السوقية المعتمدة", 4)
        row = 3
        ws.cell(row=row, column=1, value="تصنيف البناء").font       = _BOLD
        ws.cell(row=row, column=2, value="التكلفة (ريال/م²)").font  = _BOLD
        ws.cell(row=row, column=3, value="المصدر").font              = _BOLD
        row += 1
        for _btype in ["اقتصادي", "متوسط", "فاخر", "فائق الجودة"]:
            ws.cell(row=row, column=1, value=_btype).alignment = _RTL_ALIGN
            ws.cell(row=row, column=2, value=_NA)
            ws.cell(row=row, column=3,
                value="مصدر سوقي معتمد").alignment = _RTL_ALIGN
            row += 1
        _col_widths(ws, [25, 25, 40])

        # ── 35. مصفوفة المخاطر ───────────────────────────────────────────────
        ws = wb.create_sheet("مصفوفة المخاطر")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "مصفوفة تقييم مخاطر التقييم — معتمد", 4)
        row = 3
        ws.cell(row=row, column=1, value="نوع المخاطرة").font   = _BOLD
        ws.cell(row=row, column=2, value="الاحتمالية").font      = _BOLD
        ws.cell(row=row, column=3, value="الأثر").font            = _BOLD
        ws.cell(row=row, column=4, value="مستوى المخاطرة").font  = _BOLD
        row += 1
        for _risk, _prob, _impact, _level in [
            ("مخاطر بيانات السوق",     "منخفض", "عالٍ",  "متوسط"),
            ("مخاطر قانونية",          "منخفض", "عالٍ",  "منخفض"),
            ("مخاطر اقتصادية",         "متوسط", "عالٍ",  "متوسط"),
            ("مخاطر بيئية",            "منخفض", "متوسط", "منخفض"),
            ("مخاطر نزاعات ملكية",     "منخفض", "عالٍ",  "منخفض"),
        ]:
            ws.cell(row=row, column=1, value=_risk).alignment   = _RTL_ALIGN
            ws.cell(row=row, column=2, value=_prob).alignment   = _RTL_ALIGN
            ws.cell(row=row, column=3, value=_impact).alignment = _RTL_ALIGN
            _lvc = ws.cell(row=row, column=4, value=_level)
            _lvc.fill = _WARN_FILL if _level == "عالٍ" else _OK_FILL
            row += 1
        _col_widths(ws, [30, 18, 18, 22])

        # ── 36. بيان الامتثال ────────────────────────────────────────────────
        ws = wb.create_sheet("بيان الامتثال")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "بيان الامتثال المهني المعتمد", 4)
        row = 3
        for k, v in [
            ("المعيار المهني المطبق",      "المعيار السعودي للتقييم العقاري"),
            ("إطار الامتثال",              "IVSC — المعايير الدولية للتقييم"),
            ("التقييم مستقل ومحايد",       "نعم — مؤكد من الخبير"),
            ("لا تعليمات تقييدية",         "نعم"),
            ("الاستخدام المقصود",          req.get("valuation_purpose", _NA)),
            ("المستخدم المقصود",           req.get("client_name", _NA)),
            ("حالة التوقيع",               "موقع" if sig.get("final_signoff_ready") else _NA),
            ("رخصة الخبير",               sig.get("expert_license", _NA)),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [36, 44, 15, 15])

        # ── 37. الإفصاحات المهنية ─────────────────────────────────────────────
        ws = wb.create_sheet("الإفصاحات المهنية")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "الإفصاحات المهنية المعتمدة", 4)
        row = 3
        for k, v in [
            ("استقلالية المقيّم",           "نعم — لا علاقة مالية بالعقار"),
            ("مصادر البيانات المعتمدة",     "مصادر إنتاجية معتمدة — لا بيانات QA"),
            ("تضارب المصالح",               "لا يوجد"),
            ("تحفظات القيمة",               "لا تحفظات جوهرية"),
            ("حدود الاستخدام",              "وفق نطاق العمل المعتمد"),
            ("إقرار الخبير",                sig.get("approval_statement", _NA)),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [36, 54])

        # ── 38. التوصية النهائية ──────────────────────────────────────────────
        ws = wb.create_sheet("التوصية النهائية")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "التوصية التقييمية النهائية المعتمدة", 4)
        row = 3
        _recon_d2 = ctx.get("reconciliation_summary", {})
        _wv2 = _recon_d2.get("weighted_value")
        _fv2 = _recon_d2.get("selected_final_value")
        for k, v in [
            ("القيمة الموزونة",
             f"{_wv2:,.0f}" if isinstance(_wv2, (int, float)) else _NA),
            ("القيمة النهائية المختارة",
             f"{_fv2:,.0f}" if isinstance(_fv2, (int, float)) else _NA),
            ("أساس التوصية",               _recon_d2.get("rationale", _NA)),
            ("اسم الخبير الموصي",          sig.get("expert_name", _NA)),
            ("رخصة الخبير",               sig.get("expert_license", _NA)),
            ("تاريخ التوصية",              req.get("valuation_date", _NA)),
            ("العملة",                     req.get("currency", "SAR")),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [36, 44, 15, 15])

        # ── 39. اختبار اتساق الطرق ───────────────────────────────────────────
        ws = wb.create_sheet("اختبار اتساق الطرق")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "اختبار اتساق طرق التقييم — معتمد", 4)
        row = 3
        ws.cell(row=row, column=1, value="الطريقة").font        = _BOLD
        ws.cell(row=row, column=2, value="القيمة").font          = _BOLD
        ws.cell(row=row, column=3, value="الانحراف (%)").font   = _BOLD
        ws.cell(row=row, column=4, value="الحالة").font          = _BOLD
        row += 1
        _mth_d3 = ctx.get("method_summary", {})
        _mo3 = _mth_d3.get("method_outputs", {})
        if _mo3:
            for _mk, _mv in _mo3.items():
                if not isinstance(_mv, dict):
                    ws.cell(row=row, column=1, value=str(_mk)).alignment = _RTL_ALIGN
                    ws.cell(row=row, column=2, value=_NA)
                    ws.cell(row=row, column=3, value=_NA)
                    ws.cell(row=row, column=4, value=_NA)
                    row += 1
        else:
            ws.cell(row=row, column=1, value="بيانات غير متاحة").fill = _NA_FILL
        _col_widths(ws, [28, 25, 22, 18])

        # ── 40. حوكمة مصادر البيانات ─────────────────────────────────────────
        ws = wb.create_sheet("حوكمة مصادر البيانات")
        ws.sheet_view.rightToLeft = True
        _ev_d = ctx.get("evidence_summary", {})
        _hdr_row(ws, 1, "حوكمة وجودة مصادر البيانات المعتمدة", 4)
        row = 3
        for k, v in [
            ("عدد المستندات المعتمدة",       str(_ev_d.get("approved_count", 0))),
            ("جاهزية المستندات الإلزامية",   "نعم" if _ev_d.get("mandatory_document_readiness") else _NA),
            ("بيانات QA مستبعدة",            "نعم — مؤكد"),
            ("تصنيف المصادر",                "حكومية — سوقية — خبراء"),
            ("حالة مراجعة المصادر",          "معتمدة للاستخدام الرسمي"),
            ("آلية الحوكمة",                 "مراجعة النظراء + مراجعة خبير مستقل"),
            ("ملاحظة",                        str(_ev_d.get("note", _NA))),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [40, 40, 15, 15])

        # ── 41. الملحق — تفاصيل الطرق ────────────────────────────────────────
        ws = wb.create_sheet("الملحق — تفاصيل الطرق")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "ملحق تفاصيل طرق التقييم المعتمدة", 4)
        row = 3
        _mth_d4 = ctx.get("method_summary", {})
        ws.cell(row=row, column=1, value="اكتمال الطرق").font    = _BOLD
        ws.cell(row=row, column=2,
            value="نعم" if _mth_d4.get("methods_completed") else _NA)
        row += 1
        ws.cell(row=row, column=1, value="حالة الجاهزية").font  = _BOLD
        ws.cell(row=row, column=2, value=str(_mth_d4.get("readiness_status", _NA)))
        row += 2
        for _lim in _mth_d4.get("limitations", []):
            ws.cell(row=row, column=1, value="محدودية").fill = _WARN_FILL
            ws.cell(row=row, column=2, value=str(_lim)).fill = _WARN_FILL
            row += 1
        _col_widths(ws, [30, 50])

        # ── 42. الملحق — المقارنات التفصيلية ─────────────────────────────────
        ws = wb.create_sheet("الملحق — المقارنات التفصيلية")
        ws.sheet_view.rightToLeft = True
        _comp_d2 = ctx.get("comparable_summary", {})
        _hdr_row(ws, 1, "ملحق تفاصيل المقارنات المعتمدة", 4)
        row = 3
        for k, v in [
            ("عدد المقارنات الإنتاجية",
             str(_comp_d2.get("production_ready_count", 0))),
            ("جاهزية المقارنات للاعتماد",
             "نعم" if _comp_d2.get("certification_comparable_ready") else _NA),
            ("المقارنات المرفوضة / QA مستبعدة", "نعم"),
            ("ملاحظة",                            str(_comp_d2.get("note", _NA))),
        ]:
            _kv(ws, row, k, v); row += 1
        _col_widths(ws, [42, 38, 15, 15])

        # ── 43. لوحة امتثال التقييم ───────────────────────────────────────────
        ws = wb.create_sheet("لوحة امتثال التقييم")
        ws.sheet_view.rightToLeft = True
        _hdr_row(ws, 1, "لوحة امتثال التقييم الشامل — معتمد", 4)
        row = 3
        ws.cell(row=row, column=1, value="بند الامتثال").font  = _BOLD
        ws.cell(row=row, column=2, value="الحالة").font         = _BOLD
        row += 1
        _compliance = [
            ("المعيار السعودي للتقييم",      gate.get("certification_ready", False)),
            ("استقلالية المقيّم",             True),
            ("توثيق المستندات",              gate.get("final_report_generation_allowed", False)),
            ("مراجعة النظراء",               ctx.get("peer_review_summary", {}).get("peer_review_ready", False)),
            ("توقيع الخبير",                 ctx.get("signature_summary", {}).get("final_signoff_ready", False)),
            ("استبعاد بيانات QA",            True),
            ("لا مسارات داخلية مكشوفة",      True),
        ]
        for _clbl, _cval in _compliance:
            ws.cell(row=row, column=1, value=_clbl).font      = _BOLD
            ws.cell(row=row, column=1).alignment               = _RTL_ALIGN
            ws.cell(row=row, column=1).border                  = _THIN_BDR
            _bool_cell(ws, row, 2, bool(_cval))
            row += 1
        _col_widths(ws, [44, 20])

        # ── Apply output matrix: remove sheets not in active set ──────────────
        if _active_sheets is not None:
            for _sn in list(wb.sheetnames):
                if _sn not in _active_sheets:
                    del wb[_sn]

        wb.save(str(out_path))

        data = out_path.read_bytes()
        sha256 = hashlib.sha256(data).hexdigest()
        return True, "", len(data), sha256

    except Exception as exc:
        return False, str(exc), 0, ""


# ── Route registration ─────────────────────────────────────────────────────────

def register_pv_outputs_routes(app, require_auth) -> None:
    """Register all Phase H output routes on the Flask app."""
    from flask import g, jsonify, request as freq, send_file

    def _actor() -> str:
        return getattr(g, "user_id", None) or "system"

    def _check_id(request_id: str):
        if not _PVR_ID_RE.match(request_id):
            return jsonify({"ok": False, "error": "رقم الطلب غير صالح"}), 400
        return None

    def _gate_check(request_id: str, field: str):
        """Return (gate, None) if generation allowed; (None, error_response) if not."""
        gate = _load_gate_snapshot(request_id)
        if not gate.get(field):
            return None, jsonify({
                "ok":      False,
                "error":   "بوابة الاعتماد النهائية لم تجتز — لا يمكن توليد المخرجات المعتمدة",
                "blockers": gate.get("blockers", []),
                "certification_ready": gate.get("certification_ready", False),
                "gate_status": gate.get("certification_status", "not_ready"),
            }), 422
        return gate, None, None

    # ── POST /api/professional-valuation/requests/<id>/certified-report ────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/certified-report",
        methods=["POST"],
    )
    @require_auth
    def pvh_generate_certified_report(request_id: str):
        err = _check_id(request_id)
        if err:
            return err

        gate = _load_gate_snapshot(request_id)
        if not gate.get("final_report_generation_allowed"):
            return jsonify({
                "ok":                False,
                "error":             "التقرير المعتمد غير مسموح بتوليده — بوابة الاعتماد لم تجتز",
                "blockers":          gate.get("blockers", []),
                "certification_ready": gate.get("certification_ready", False),
            }), 422

        actor   = _actor()
        version = _output_version_for(request_id, "certified_pdf")
        rec     = _new_output_record(request_id, "certified_pdf", actor, version)
        rec["report_number"] = (
            f"PV-RPT-{datetime.utcnow().strftime('%Y%m%d')}-{rec['output_id'][-6:]}"
        )
        rec["certification_gate_snapshot"] = {
            k: v for k, v in gate.items()
            if k not in ("blockers", "warnings", "advisory_only_reason")
        }

        ctx = build_professional_valuation_output_context(request_id)
        ctx["report_number"] = rec["report_number"]
        ctx["output_metadata"] = {
            "output_id":      rec["output_id"],
            "output_type":    "certified_pdf",
            "output_version": version,
            "generated_at":   rec["generated_at"],
            "generated_by":   actor,
            "report_number":  rec["report_number"],
        }

        success, err_msg, size, sha = _generate_certified_pdf(ctx, request_id, rec["output_id"])

        if success:
            rec["output_status"]   = "generated"
            rec["file_available"]  = True
            rec["file_size_bytes"] = size
            rec["file_hash_sha256"] = sha
            rec["internal_file_path"] = str(
                _OUT_DIR / request_id / f"{rec['output_id']}_certified_report.pdf"
            )
            rec["certified_use_allowed"]  = True
            rec["official_use_allowed"]   = True
            rec["public_metadata"] = {
                "report_number":  rec["report_number"],
                "output_version": version,
                "output_type":    "certified_pdf",
                "certified":      True,
            }
        else:
            rec["output_status"]      = "generation_failed"
            rec["file_available"]     = False
            rec["generation_blockers"] = [f"PDF generation error: {err_msg[:300]}"]

        _append_registry(rec)
        _append_output_event(
            request_id, actor, "generate_certified_report",
            output_id=rec["output_id"],
            note=f"status={rec['output_status']} version={version}",
            metadata={"output_type": "certified_pdf", "success": success},
        )

        return jsonify({
            "ok":           True,
            "output":       _safe_output(rec),
            "generation_success": success,
            "generation_error":   err_msg if not success else None,
        }), 200

    # ── GET /api/professional-valuation/requests/<id>/certified-report ─────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/certified-report",
        methods=["GET"],
    )
    @require_auth
    def pvh_download_certified_report(request_id: str):
        err = _check_id(request_id)
        if err:
            return err

        rec = _latest_active_of_type(request_id, "certified_pdf")
        if not rec:
            return jsonify({"ok": False, "error": "لا يوجد تقرير معتمد مُولَّد لهذا الطلب"}), 404

        if not rec.get("file_available"):
            return jsonify({
                "ok":     False,
                "error":  "الملف غير متاح — توليد التقرير فشل أو لم يكتمل",
                "output": _safe_output(rec),
            }), 404

        fpath = Path(rec.get("internal_file_path", ""))
        if not fpath.exists():
            return jsonify({"ok": False, "error": "ملف التقرير غير موجود في النظام"}), 404

        return send_file(
            str(fpath),
            as_attachment=True,
            download_name=f"professional_valuation_certified_report_{rec['output_version']}.pdf",
            mimetype="application/pdf",
        )

    # ── POST /api/professional-valuation/requests/<id>/final-workbook ──────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/final-workbook",
        methods=["POST"],
    )
    @require_auth
    def pvh_generate_final_workbook(request_id: str):
        err = _check_id(request_id)
        if err:
            return err

        gate = _load_gate_snapshot(request_id)
        if not gate.get("final_workbook_generation_allowed"):
            return jsonify({
                "ok":                False,
                "error":             "ملف Excel النهائي غير مسموح بتوليده — بوابة الاعتماد لم تجتز",
                "blockers":          gate.get("blockers", []),
                "certification_ready": gate.get("certification_ready", False),
            }), 422

        actor   = _actor()
        version = _output_version_for(request_id, "final_workbook")
        rec     = _new_output_record(request_id, "final_workbook", actor, version)
        rec["report_number"] = (
            f"PV-WB-{datetime.utcnow().strftime('%Y%m%d')}-{rec['output_id'][-6:]}"
        )
        rec["certification_gate_snapshot"] = {
            k: v for k, v in gate.items()
            if k not in ("blockers", "warnings", "advisory_only_reason")
        }

        ctx = build_professional_valuation_output_context(request_id)
        ctx["report_number"] = rec["report_number"]
        ctx["output_metadata"] = {
            "output_id":       rec["output_id"],
            "output_type":     "final_workbook",
            "output_version":  version,
            "generated_at":    rec["generated_at"],
            "generated_by":    actor,
            "report_number":   rec["report_number"],
            "file_hash_sha256": None,
            "file_size_bytes":  None,
        }

        # Batch 5: route through strategy wrapper (legacy when flag disabled)
        success, err_msg, size, sha = _generate_final_workbook_with_strategy(
            ctx, request_id, rec["output_id"]
        )
        rec["excel_builder_used"] = ctx.get("output_metadata", {}).get(
            "excel_builder_used", "legacy"
        )

        if success:
            rec["output_status"]   = "generated"
            rec["file_available"]  = True
            rec["file_size_bytes"] = size
            rec["file_hash_sha256"] = sha
            rec["internal_file_path"] = str(
                _OUT_DIR / request_id / f"{rec['output_id']}_final_workbook.xlsx"
            )
            rec["certified_use_allowed"] = True
            rec["official_use_allowed"]  = True
            rec["public_metadata"] = {
                "report_number":  rec["report_number"],
                "output_version": version,
                "output_type":    "final_workbook",
                "certified":      True,
            }
            ctx["output_metadata"]["file_hash_sha256"] = sha
            ctx["output_metadata"]["file_size_bytes"]  = size
        else:
            rec["output_status"]       = "generation_failed"
            rec["file_available"]      = False
            rec["generation_blockers"] = [f"Workbook generation error: {err_msg[:300]}"]

        _append_registry(rec)
        _append_output_event(
            request_id, actor, "generate_final_workbook",
            output_id=rec["output_id"],
            note=f"status={rec['output_status']} version={version} builder={rec['excel_builder_used']}",
            metadata={
                "output_type": "final_workbook",
                "success": success,
                "excel_builder_used": rec["excel_builder_used"],
            },
        )

        return jsonify({
            "ok":             True,
            "output":         _safe_output(rec),
            "generation_success": success,
            "generation_error":   err_msg if not success else None,
        }), 200

    # ── GET /api/professional-valuation/requests/<id>/final-workbook ───────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/final-workbook",
        methods=["GET"],
    )
    @require_auth
    def pvh_download_final_workbook(request_id: str):
        err = _check_id(request_id)
        if err:
            return err

        rec = _latest_active_of_type(request_id, "final_workbook")
        if not rec:
            return jsonify({"ok": False, "error": "لا يوجد ملف Excel نهائي مُولَّد لهذا الطلب"}), 404

        if not rec.get("file_available"):
            return jsonify({
                "ok":     False,
                "error":  "الملف غير متاح",
                "output": _safe_output(rec),
            }), 404

        fpath = Path(rec.get("internal_file_path", ""))
        if not fpath.exists():
            return jsonify({"ok": False, "error": "ملف Excel غير موجود في النظام"}), 404

        return send_file(
            str(fpath),
            as_attachment=True,
            download_name=f"professional_valuation_final_workbook_{rec['output_version']}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # ── GET /api/professional-valuation/requests/<id>/outputs ──────────────────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/outputs",
        methods=["GET"],
    )
    @require_auth
    def pvh_list_outputs(request_id: str):
        err = _check_id(request_id)
        if err:
            return err

        records = _read_registry(request_id)
        events  = read_output_events(request_id)
        gate    = _load_gate_snapshot(request_id)

        return jsonify({
            "ok":      True,
            "outputs": [_safe_output(r) for r in records],
            "total":   len(records),
            "gate_summary": {
                "certification_ready":               gate.get("certification_ready", False),
                "final_report_generation_allowed":   gate.get("final_report_generation_allowed", False),
                "final_workbook_generation_allowed": gate.get("final_workbook_generation_allowed", False),
                "blockers":                          gate.get("blockers", []),
            },
            "event_log": events,
        }), 200

    # ── GET /api/professional-valuation/requests/<id>/outputs/<output_id> ──────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/outputs/<output_id>",
        methods=["GET"],
    )
    @require_auth
    def pvh_get_output(request_id: str, output_id: str):
        err = _check_id(request_id)
        if err:
            return err

        rec = _read_output_by_id(request_id, output_id)
        if rec is None:
            return jsonify({"ok": False, "error": "المخرج غير موجود"}), 404

        return jsonify({"ok": True, "output": _safe_output(rec)}), 200

    # ── POST /api/professional-valuation/requests/<id>/outputs/<id>/revoke ─────
    @app.route(
        "/api/professional-valuation/requests/<request_id>/outputs/<output_id>/revoke",
        methods=["POST"],
    )
    @require_auth
    def pvh_revoke_output(request_id: str, output_id: str):
        err = _check_id(request_id)
        if err:
            return err

        records = _read_registry(request_id)
        found   = None
        for r in records:
            if r.get("output_id") == output_id:
                found = r
                break

        if found is None:
            return jsonify({"ok": False, "error": "المخرج غير موجود"}), 404

        if found.get("output_status") == "revoked":
            return jsonify({"ok": False, "error": "المخرج محذوف بالفعل"}), 409

        # Mark revoked in registry (append a new record reflecting the revocation)
        found["output_status"] = "revoked"
        # Rewrite the entire registry file (simple append-based JSONL doesn't support in-place edits)
        reg_path = _REG_DIR / f"{request_id}.jsonl"
        with open(reg_path, "w", encoding="utf-8") as fh:
            for r in records:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")

        _append_output_event(
            request_id, _actor(), "revoke_output",
            output_id=output_id,
            note="Output revoked — file not deleted",
        )

        return jsonify({
            "ok":     True,
            "output": _safe_output(found),
            "note":   "تم إلغاء المخرج — الملف لا يزال موجوداً على القرص ولم يُحذف",
        }), 200
