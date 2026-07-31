"""
Standards Compliance v2 — Flask endpoint module
Routes:
  POST /api/standards-compliance-v2/generate
  GET  /api/standards-compliance-v2/artifact/<filename>       (user HTML/PDF)
  GET  /api/standards-compliance-v2/admin-artifact/<filename> (admin HTML/PDF/Excel)
  GET  /api/standards-compliance-v2/user-pdf
  GET  /api/standards-compliance-v2/admin-pdf   (admin only)
  GET  /api/standards-compliance-v2/admin-excel (admin only)

Role rules: Excel + admin artifacts = HTTP 403 for non-admins.
"""
from __future__ import annotations

import os
import pathlib
import traceback
from typing import Any, Callable

_ROOT      = pathlib.Path(__file__).parent
_ARTIFACTS = _ROOT / "outputs" / "visual_qa_standards_compliance_v2" / "artifacts"
_CSP       = "default-src 'none'; style-src 'unsafe-inline'; font-src data:; img-src data: blob:;"


def _safe(filename: str) -> bool:
    return "/" not in filename and "\\" not in filename and ".." not in filename


def register_standards_compliance_v2(
    app: Any,
    require_auth: Callable,
    _is_admin: Callable,
    OUTPUTS: pathlib.Path,
) -> None:
    from flask import g, jsonify, send_file, make_response  # type: ignore

    is_admin = _is_admin

    @app.route("/api/standards-compliance-v2/generate", methods=["POST"])
    @require_auth
    def sc_v2_generate():
        try:
            from standards_compliance_v2_generator import (
                run_standards_compliance_v2_visual_qa, CASE_ID, SCORE_V2,
                advisory_only, certification_ready, fake_signature_created,
                ml_suggestion_only, ml_auto_decision,
            )
        except ImportError as exc:
            return jsonify({"ok": False, "error": f"فشل استيراد مولّد v2: {exc}", "advisory_only": True}), 500

        try:
            report = run_standards_compliance_v2_visual_qa()
        except Exception as exc:
            print(traceback.format_exc())
            return jsonify({"ok": False, "error": str(exc), "advisory_only": True}), 500

        user_is_admin = is_admin(g.user_id)
        cid = CASE_ID

        resp: dict[str, Any] = {
            "ok": True,
            "message": "تم إنشاء تقرير الامتثال v2.",
            "case_id": cid,
            "score_pct": SCORE_V2["percentage"],
            "traffic_light": SCORE_V2["traffic_light"],
            "score_label": SCORE_V2["label"],
            "blocks_issuance": SCORE_V2["blocks_issuance"],
            "critical_findings": SCORE_V2["critical_findings"],
            "cross_format_pass": report.get("cross_format_pass", False),
            "advisory_only": advisory_only,
            "certification_ready": certification_ready,
            "fake_signature_created": fake_signature_created,
            "ml_suggestion_only": ml_suggestion_only,
            "ml_auto_decision": ml_auto_decision,
            "html_url": f"/api/standards-compliance-v2/artifact/compliance_v2_{cid}_user.html",
            "pdf_url":  f"/api/standards-compliance-v2/artifact/compliance_v2_{cid}_user.pdf",
        }

        if user_is_admin:
            resp["message"] = "تم إنشاء تقرير الامتثال v2 (مستخدم + مسؤول)."
            resp["admin_html_url"]  = f"/api/standards-compliance-v2/admin-artifact/compliance_v2_{cid}_admin.html"
            resp["admin_pdf_url"]   = f"/api/standards-compliance-v2/admin-artifact/compliance_v2_{cid}_admin.pdf"
            resp["excel_url"]       = f"/api/standards-compliance-v2/admin-artifact/compliance_v2_{cid}_admin.xlsx"
            resp["excel_filename"]  = f"compliance_v2_{cid}_admin.xlsx"
            resp["html_url"]        = resp["admin_html_url"]
            resp["pdf_url"]         = resp["admin_pdf_url"]

        return jsonify(resp), 200

    @app.route("/api/standards-compliance-v2/artifact/<filename>", methods=["GET"])
    @require_auth
    def sc_v2_artifact(filename: str):
        if not _safe(filename):
            return jsonify({"error": "اسم ملف غير صالح."}), 400
        safe = os.path.basename(filename)
        target = _ARTIFACTS / safe
        if not target.exists():
            return jsonify({"error": "الملف غير موجود — يرجى تشغيل المولّد أولاً."}), 404
        if safe.endswith(".xlsx"):
            return jsonify({"error": "ملفات Excel متاحة للمسؤولين فقط."}), 403
        if safe.endswith(".html"):
            content = target.read_text(encoding="utf-8")
            r = make_response(content)
            r.headers["Content-Type"] = "text/html; charset=utf-8"
            r.headers["Content-Disposition"] = f'inline; filename="{safe}"'
            r.headers["Content-Security-Policy"] = _CSP
            r.headers["X-Content-Type-Options"] = "nosniff"
            return r
        return send_file(str(target), as_attachment=True, download_name=safe)

    @app.route("/api/standards-compliance-v2/admin-artifact/<filename>", methods=["GET"])
    @require_auth
    def sc_v2_admin_artifact(filename: str):
        if not is_admin(g.user_id):
            return jsonify({"error": "غير مصرح — المسؤولون فقط."}), 403
        if not _safe(filename):
            return jsonify({"error": "اسم ملف غير صالح."}), 400
        safe = os.path.basename(filename)
        target = _ARTIFACTS / safe
        if not target.exists():
            return jsonify({"error": "الملف غير موجود — يرجى تشغيل المولّد أولاً."}), 404
        if safe.endswith(".html"):
            content = target.read_text(encoding="utf-8")
            r = make_response(content)
            r.headers["Content-Type"] = "text/html; charset=utf-8"
            r.headers["Content-Disposition"] = f'inline; filename="{safe}"'
            r.headers["Content-Security-Policy"] = _CSP
            r.headers["X-Content-Type-Options"] = "nosniff"
            return r
        return send_file(str(target), as_attachment=True, download_name=safe)

    @app.route("/api/standards-compliance-v2/user-pdf", methods=["GET"])
    @require_auth
    def sc_v2_user_pdf():
        pdfs = sorted(_ARTIFACTS.glob("compliance_v2_*_user.pdf"),
                      key=lambda p: p.stat().st_mtime, reverse=True)
        if not pdfs:
            return jsonify({"error": "لا يوجد PDF — يرجى تشغيل المولّد أولاً."}), 404
        return send_file(str(pdfs[0]), as_attachment=True, download_name=pdfs[0].name)

    @app.route("/api/standards-compliance-v2/admin-pdf", methods=["GET"])
    @require_auth
    def sc_v2_admin_pdf():
        if not is_admin(g.user_id):
            return jsonify({"error": "غير مصرح — المسؤولون فقط."}), 403
        pdfs = sorted(_ARTIFACTS.glob("compliance_v2_*_admin.pdf"),
                      key=lambda p: p.stat().st_mtime, reverse=True)
        if not pdfs:
            return jsonify({"error": "لا يوجد PDF للمسؤول."}), 404
        return send_file(str(pdfs[0]), as_attachment=True, download_name=pdfs[0].name)

    @app.route("/api/standards-compliance-v2/admin-excel", methods=["GET"])
    @require_auth
    def sc_v2_admin_excel():
        if not is_admin(g.user_id):
            return jsonify({"error": "غير مصرح — ملفات Excel للمسؤولين فقط."}), 403
        xlsxs = sorted(_ARTIFACTS.glob("compliance_v2_*_admin.xlsx"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        if not xlsxs:
            return jsonify({"error": "لا يوجد Excel — يرجى تشغيل المولّد أولاً."}), 404
        return send_file(str(xlsxs[0]), as_attachment=True, download_name=xlsxs[0].name)
