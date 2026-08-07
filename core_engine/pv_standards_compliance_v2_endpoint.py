"""
Standards Compliance v2 — Flask endpoint module  (Wave 4A hardened)

Routes (Admin-only, POLICY_A):
  POST   /api/standards-compliance-v2/runs
  GET    /api/standards-compliance-v2/runs/<run_id>
  GET    /api/standards-compliance-v2/runs/<run_id>/artifacts/<artifact_key>
  DELETE /api/standards-compliance-v2/runs/<run_id>

Security: BoundedSemaphore(1).  Per-run isolation.  Bounded stream parsing.
          lstat/open/fstat validated handles.  Atomic registration.
"""
from __future__ import annotations

import datetime
import enum
import json
import logging
import os
import pathlib
import re
import shutil
import stat
import threading
import time
import uuid
from typing import Any, Callable

_LOG = logging.getLogger(__name__)

# ── Shared semaphore (POST + DELETE must acquire) ──────────────────────────────
_SEMAPHORE = threading.BoundedSemaphore(1)

# ── Stable module-level constants ─────────────────────────────────────────────
_CASE_ID   = "QA-COMPLIANCE-VISUAL-001"
_RUN_ID_RE = re.compile(r"^[0-9a-f]{32}$")

_GOVERNANCE_KEYS: frozenset[str] = frozenset({
    "advisory_only", "certification_ready", "fake_signature_created",
    "ml_suggestion_only", "ml_trained_on_approved_only",
    "ml_auto_decision", "synthetic_data",
})
_METADATA_TOP_KEYS: frozenset[str] = frozenset({
    "schema_version", "run_id", "case_id", "created_at",
    "status", "score", "governance", "artifact_keys",
})
_METADATA_MAX_BYTES = 65_536

# (filename_template, mime_type, disposition, max_bytes)
_ARTIFACT_MAP: dict[str, tuple[str, str, str, int]] = {
    "user_html":    (
        "compliance_v2_{cid}_user.html",
        "text/html; charset=utf-8",
        "inline",
        5_242_880,
    ),
    "admin_html":   (
        "compliance_v2_{cid}_admin.html",
        "text/html; charset=utf-8",
        "inline",
        5_242_880,
    ),
    "user_pdf":     (
        "compliance_v2_{cid}_user.pdf",
        "application/pdf",
        "attachment",
        10_485_760,
    ),
    "admin_pdf":    (
        "compliance_v2_{cid}_admin.pdf",
        "application/pdf",
        "attachment",
        10_485_760,
    ),
    "admin_xlsx":   (
        "compliance_v2_{cid}_admin.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "attachment",
        10_485_760,
    ),
    "audit_report": (
        "compliance_v2_visual_qa_report.json",
        "application/json",
        "attachment",
        1_048_576,
    ),
    "audit_cross":  (
        "compliance_v2_cross_format.json",
        "application/json",
        "attachment",
        1_048_576,
    ),
    "audit_content": (
        "compliance_v2_content_audit.json",
        "application/json",
        "attachment",
        1_048_576,
    ),
}

_AUDIT_SUBDIR_KEYS: frozenset[str] = frozenset({
    "audit_report", "audit_cross", "audit_content",
})

_CSP_HTML = (
    "default-src 'none'; style-src 'unsafe-inline'; "
    "img-src data: blob:; font-src data:; base-uri 'none'; frame-ancestors 'none'"
)

_RETENTION_TTL    = 86_400   # 24 h
_PRE_GEN_TARGET   = 9
_MAX_COMPLETED    = 10
_DELETE_MAX_DEPTH = 4
_DELETE_MAX_ENTRIES = 200
_FILE_ATTRIBUTE_REPARSE_POINT = 0x400  # Windows

# ── Structural allowlist — exact Generator-derived filenames and categories ─────
_ROOT_ALLOWED_FILES: frozenset[str] = frozenset({"run_metadata.json"})
_ROOT_ALLOWED_DIRS: frozenset[str]  = frozenset({"artifacts", "screenshots", "audits"})
_ARTIFACTS_ALLOWED: frozenset[str]  = frozenset({
    f"compliance_v2_{_CASE_ID}_user.html",
    f"compliance_v2_{_CASE_ID}_admin.html",
    f"compliance_v2_{_CASE_ID}_user.pdf",
    f"compliance_v2_{_CASE_ID}_admin.pdf",
    f"compliance_v2_{_CASE_ID}_admin.xlsx",
})
_AUDITS_ALLOWED: frozenset[str] = frozenset({
    "compliance_v2_visual_qa_report.json",
    "compliance_v2_cross_format.json",
    "compliance_v2_content_audit.json",
})
_SS_CATEGORIES_ALLOWED: frozenset[str] = frozenset({
    "user_html", "admin_html", "user_pdf", "admin_pdf",
})
_SS_PNG_PATTERNS: dict = {
    "user_html":  re.compile(r"^user_(section_(0[1-9]|1[0-5])|full)\.png$"),
    "admin_html": re.compile(r"^admin_(section_(0[1-9]|1[0-5])|full)\.png$"),
    "user_pdf":   re.compile(r"^user_pdf_page_(0[1-9]|[1-6][0-9]|7[0-6])\.png$"),
    "admin_pdf":  re.compile(r"^admin_pdf_page_(0[1-9]|[1-6][0-9]|7[0-6])\.png$"),
}


class _DelResult(enum.Enum):
    DELETED                   = "DELETED"
    NOT_FOUND                 = "NOT_FOUND"
    REFUSED_OUTSIDE_ROOT      = "REFUSED_OUTSIDE_ROOT"
    REFUSED_REPARSE_POINT     = "REFUSED_REPARSE_POINT"
    REFUSED_UNKNOWN_STRUCTURE = "REFUSED_UNKNOWN_STRUCTURE"
    FAILED_IO                 = "FAILED_IO"


# ── Module-level helpers (exposed for tests) ──────────────────────────────────

def _is_link_or_reparse_lstat(st: os.stat_result) -> bool:
    if stat.S_ISLNK(st.st_mode):
        return True
    return bool(
        getattr(st, "st_file_attributes", 0) & _FILE_ATTRIBUTE_REPARSE_POINT
    )


# ── Registration function ─────────────────────────────────────────────────────

def register_standards_compliance_v2(
    app: Any,
    require_auth: Callable,
    _is_admin: Callable,
    OUTPUTS: "str | pathlib.Path",
) -> None:
    """Atomic registration — raises RuntimeError before Blueprint registration on any failure."""

    # ── 0. Idempotency guard ────────────────────────────────────────────────────
    if app.extensions.get("sc_v2_registered"):
        return

    # ── 1. Absolute configured root (CWD-independent) ─────────────────────────
    outputs_path = pathlib.Path(OUTPUTS).absolute()
    case_path    = outputs_path / "visual_qa_standards_compliance_v2"

    # ── 2. Validate OUTPUTS root ───────────────────────────────────────────────
    try:
        out_st = os.lstat(outputs_path)
    except OSError as exc:
        raise RuntimeError("V2: OUTPUTS does not exist") from exc

    if not stat.S_ISDIR(out_st.st_mode):
        raise RuntimeError("V2: OUTPUTS is not a real directory")
    if _is_link_or_reparse_lstat(out_st):
        raise RuntimeError("V2: OUTPUTS is a symlink or reparse point")

    out_dev = out_st.st_dev
    out_ino = out_st.st_ino

    # ── 3. Create / validate case root ────────────────────────────────────────
    try:
        case_path.mkdir(parents=True, exist_ok=True)
        case_st = os.lstat(case_path)
    except OSError as exc:
        raise RuntimeError("V2: case root creation failed") from exc

    if not stat.S_ISDIR(case_st.st_mode):
        raise RuntimeError("V2: case_path is not a real directory")
    if _is_link_or_reparse_lstat(case_st):
        raise RuntimeError("V2: case_path is a symlink or reparse point")

    case_dev = case_st.st_dev
    case_ino = case_st.st_ino

    try:
        outputs_resolved = outputs_path.resolve()
        case_resolved    = case_path.resolve()
    except OSError as exc:
        raise RuntimeError("V2: root resolve failed") from exc

    # ── 4. Import and validate generator ──────────────────────────────────────
    try:
        from standards_compliance_v2_generator import (  # type: ignore
            run_standards_compliance_v2_visual_qa as _generate,
            advisory_only         as _adv,
            certification_ready   as _cert,
            fake_signature_created as _fsc,
            ml_suggestion_only    as _mlsug,
            ml_trained_on_approved_only as _mltrain,
            ml_auto_decision      as _mlad,
            synthetic_data        as _synth,
        )
    except ImportError as exc:
        raise RuntimeError("V2: generator import failed") from exc

    # Build the governance dict once at registration time
    _governance = {
        "advisory_only":              _adv,
        "certification_ready":        _cert,
        "fake_signature_created":     _fsc,
        "ml_suggestion_only":         _mlsug,
        "ml_trained_on_approved_only": _mltrain,
        "ml_auto_decision":           _mlad,
        "synthetic_data":             _synth,
    }

    # ── 5. Collision preflight ─────────────────────────────────────────────────
    _endpoint_names = (
        "sc_v2.sc_v2_post_run",
        "sc_v2.sc_v2_get_metadata",
        "sc_v2.sc_v2_get_artifact",
        "sc_v2.sc_v2_delete_run",
    )
    for ep_name in _endpoint_names:
        if ep_name in app.view_functions:
            raise RuntimeError(f"V2: endpoint collision: {ep_name}")

    _route_methods = (
        ("/api/standards-compliance-v2/runs", "POST"),
        ("/api/standards-compliance-v2/runs/<run_id>", "GET"),
        ("/api/standards-compliance-v2/runs/<run_id>/artifacts/<artifact_key>", "GET"),
        ("/api/standards-compliance-v2/runs/<run_id>", "DELETE"),
    )
    existing_pairs: set[tuple[str, str]] = {
        (r.rule, m)
        for r in app.url_map.iter_rules()
        for m in (r.methods or [])
    }
    for rule, method in _route_methods:
        if (rule, method) in existing_pairs:
            raise RuntimeError(f"V2: route collision: {method} {rule}")

    # ── 6. Build Blueprint ────────────────────────────────────────────────────
    from flask import Blueprint, g, jsonify, make_response  # type: ignore

    bp = Blueprint("sc_v2", __name__)

    # ── Closure helpers ────────────────────────────────────────────────────────

    def _revalidate_roots() -> None:
        try:
            st_out = os.lstat(outputs_path)
            if not stat.S_ISDIR(st_out.st_mode):
                raise RuntimeError("V2: outputs root changed to non-dir")
            if st_out.st_dev != out_dev or st_out.st_ino != out_ino:
                raise RuntimeError("V2: outputs root identity changed")
            st_case = os.lstat(case_path)
            if not stat.S_ISDIR(st_case.st_mode):
                raise RuntimeError("V2: case root changed to non-dir")
            if st_case.st_dev != case_dev or st_case.st_ino != case_ino:
                raise RuntimeError("V2: case root identity changed")
        except RuntimeError:
            raise
        except OSError as exc:
            raise RuntimeError("V2: root revalidation OS error") from exc

    def _valid_run_id(run_id: str) -> bool:
        return bool(_RUN_ID_RE.match(run_id))

    def _read_metadata(run_id: str) -> dict[str, Any]:
        meta_path = case_path / run_id / "run_metadata.json"
        handle = None
        try:
            st_lstat = os.lstat(meta_path)
            if not stat.S_ISREG(st_lstat.st_mode):
                raise RuntimeError("metadata is not a regular file")
            if _is_link_or_reparse_lstat(st_lstat):
                raise RuntimeError("metadata is a symlink or reparse point")
            if st_lstat.st_size > _METADATA_MAX_BYTES:
                raise RuntimeError("metadata pre-open size exceeded")
            handle = open(meta_path, "rb")  # noqa: WPS515
            st_fstat = os.fstat(handle.fileno())
            if st_lstat.st_ino != 0 and st_fstat.st_ino != 0:
                if (st_lstat.st_dev, st_lstat.st_ino) != (st_fstat.st_dev, st_fstat.st_ino):
                    raise RuntimeError("metadata identity mismatch")
            if st_fstat.st_size > _METADATA_MAX_BYTES:
                raise RuntimeError("metadata grew after open")
            raw = handle.read()
            return json.loads(raw.decode("utf-8"))
        finally:
            if handle is not None:
                try:
                    handle.close()
                except OSError:
                    pass

    def _list_completed_runs() -> list[pathlib.Path]:
        result: list[pathlib.Path] = []
        try:
            for entry in os.scandir(case_path):
                if not _valid_run_id(entry.name):
                    continue
                try:
                    st = os.lstat(entry.path)
                except OSError:
                    continue
                if not stat.S_ISDIR(st.st_mode):
                    continue
                if _is_link_or_reparse_lstat(st):
                    continue
                meta = pathlib.Path(entry.path) / "run_metadata.json"
                if meta.exists():
                    result.append(pathlib.Path(entry.path))
        except OSError:
            pass
        return result

    def _cleanup_expired() -> None:
        now = datetime.datetime.now(datetime.timezone.utc)
        for run_path in _list_completed_runs():
            try:
                data = _read_metadata(run_path.name)
                created_str = data.get("created_at", "")
                created = datetime.datetime.fromisoformat(created_str)
                age = (now - created).total_seconds()
                if age > _RETENTION_TTL:
                    _safe_delete_run_dir(run_path)
            except Exception:
                pass

    def _cleanup_orphans() -> None:
        cutoff = time.time() - _RETENTION_TTL
        try:
            for entry in os.scandir(case_path):
                if not _valid_run_id(entry.name):
                    continue
                try:
                    st = os.lstat(entry.path)
                except OSError:
                    continue
                if not stat.S_ISDIR(st.st_mode) or _is_link_or_reparse_lstat(st):
                    continue
                meta = pathlib.Path(entry.path) / "run_metadata.json"
                if not meta.exists() and st.st_mtime < cutoff:
                    _safe_delete_run_dir(pathlib.Path(entry.path))
        except OSError:
            pass

    def _safe_delete_run_dir(run_path: pathlib.Path) -> _DelResult:
        try:
            st = os.lstat(run_path)
        except FileNotFoundError:
            return _DelResult.NOT_FOUND
        except OSError:
            return _DelResult.FAILED_IO

        if run_path.parent != case_path:
            return _DelResult.REFUSED_OUTSIDE_ROOT

        if not stat.S_ISDIR(st.st_mode):
            return _DelResult.REFUSED_UNKNOWN_STRUCTURE
        if _is_link_or_reparse_lstat(st):
            return _DelResult.REFUSED_REPARSE_POINT

        # Structural allowlist scan — Generator-derived exact structure only
        entry_count = 0
        try:
            # ── Level 0: run root ─────────────────────────────────────────────
            try:
                root_entries = list(os.scandir(run_path))
            except OSError:
                return _DelResult.FAILED_IO
            for e in root_entries:
                entry_count += 1
                if entry_count > _DELETE_MAX_ENTRIES:
                    return _DelResult.REFUSED_UNKNOWN_STRUCTURE
                try:
                    est = os.lstat(e.path)
                except OSError:
                    return _DelResult.FAILED_IO
                if _is_link_or_reparse_lstat(est):
                    return _DelResult.REFUSED_REPARSE_POINT
                if stat.S_ISREG(est.st_mode):
                    if e.name not in _ROOT_ALLOWED_FILES:
                        return _DelResult.REFUSED_UNKNOWN_STRUCTURE
                elif stat.S_ISDIR(est.st_mode):
                    if e.name not in _ROOT_ALLOWED_DIRS:
                        return _DelResult.REFUSED_UNKNOWN_STRUCTURE
                else:
                    return _DelResult.REFUSED_UNKNOWN_STRUCTURE

            # ── Level 1a: artifacts/ ──────────────────────────────────────────
            arts_path = run_path / "artifacts"
            if arts_path.exists():
                try:
                    arts_entries = list(os.scandir(arts_path))
                except OSError:
                    return _DelResult.FAILED_IO
                for e in arts_entries:
                    entry_count += 1
                    if entry_count > _DELETE_MAX_ENTRIES:
                        return _DelResult.REFUSED_UNKNOWN_STRUCTURE
                    try:
                        est = os.lstat(e.path)
                    except OSError:
                        return _DelResult.FAILED_IO
                    if _is_link_or_reparse_lstat(est):
                        return _DelResult.REFUSED_REPARSE_POINT
                    if not stat.S_ISREG(est.st_mode):
                        return _DelResult.REFUSED_UNKNOWN_STRUCTURE
                    if e.name not in _ARTIFACTS_ALLOWED:
                        return _DelResult.REFUSED_UNKNOWN_STRUCTURE

            # ── Level 1b: audits/ ─────────────────────────────────────────────
            aud_path = run_path / "audits"
            if aud_path.exists():
                try:
                    aud_entries = list(os.scandir(aud_path))
                except OSError:
                    return _DelResult.FAILED_IO
                for e in aud_entries:
                    entry_count += 1
                    if entry_count > _DELETE_MAX_ENTRIES:
                        return _DelResult.REFUSED_UNKNOWN_STRUCTURE
                    try:
                        est = os.lstat(e.path)
                    except OSError:
                        return _DelResult.FAILED_IO
                    if _is_link_or_reparse_lstat(est):
                        return _DelResult.REFUSED_REPARSE_POINT
                    if not stat.S_ISREG(est.st_mode):
                        return _DelResult.REFUSED_UNKNOWN_STRUCTURE
                    if e.name not in _AUDITS_ALLOWED:
                        return _DelResult.REFUSED_UNKNOWN_STRUCTURE

            # ── Level 1c + 2: screenshots/ + categories ───────────────────────
            ss_path = run_path / "screenshots"
            if ss_path.exists():
                try:
                    ss_entries = list(os.scandir(ss_path))
                except OSError:
                    return _DelResult.FAILED_IO
                for cat_e in ss_entries:
                    entry_count += 1
                    if entry_count > _DELETE_MAX_ENTRIES:
                        return _DelResult.REFUSED_UNKNOWN_STRUCTURE
                    try:
                        cat_st = os.lstat(cat_e.path)
                    except OSError:
                        return _DelResult.FAILED_IO
                    if _is_link_or_reparse_lstat(cat_st):
                        return _DelResult.REFUSED_REPARSE_POINT
                    if not stat.S_ISDIR(cat_st.st_mode):
                        return _DelResult.REFUSED_UNKNOWN_STRUCTURE
                    if cat_e.name not in _SS_CATEGORIES_ALLOWED:
                        return _DelResult.REFUSED_UNKNOWN_STRUCTURE
                    # Level 2: PNG files only — no subdirectories
                    cat_path = pathlib.Path(cat_e.path)
                    png_re = _SS_PNG_PATTERNS[cat_e.name]
                    try:
                        png_entries = list(os.scandir(cat_path))
                    except OSError:
                        return _DelResult.FAILED_IO
                    for png_e in png_entries:
                        entry_count += 1
                        if entry_count > _DELETE_MAX_ENTRIES:
                            return _DelResult.REFUSED_UNKNOWN_STRUCTURE
                        try:
                            png_st = os.lstat(png_e.path)
                        except OSError:
                            return _DelResult.FAILED_IO
                        if _is_link_or_reparse_lstat(png_st):
                            return _DelResult.REFUSED_REPARSE_POINT
                        if stat.S_ISDIR(png_st.st_mode):
                            return _DelResult.REFUSED_UNKNOWN_STRUCTURE
                        if not stat.S_ISREG(png_st.st_mode):
                            return _DelResult.REFUSED_UNKNOWN_STRUCTURE
                        if not png_re.match(png_e.name):
                            return _DelResult.REFUSED_UNKNOWN_STRUCTURE

        except OSError:
            return _DelResult.FAILED_IO

        try:
            shutil.rmtree(str(run_path), ignore_errors=False)
        except OSError:
            return _DelResult.FAILED_IO

        # lstat postcondition — presence of any object = FAILED_IO
        try:
            os.lstat(run_path)
            return _DelResult.FAILED_IO
        except FileNotFoundError:
            return _DelResult.DELETED
        except OSError:
            return _DelResult.FAILED_IO

    def _parse_post_body() -> "tuple[dict, object]":
        from flask import request  # type: ignore
        raw = request.stream.read(257)
        if len(raw) > 256:
            return {}, (jsonify({"ok": False, "error": "PAYLOAD_TOO_LARGE"}), 413)
        if len(raw) == 0:
            return {}, None
        ct = (request.content_type or "").lower()
        if not ct.startswith("application/json"):
            return {}, (jsonify({"ok": False, "error": "UNSUPPORTED_MEDIA_TYPE"}), 415)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            return {}, (jsonify({"ok": False, "error": "INVALID_JSON"}), 400)
        try:
            body = json.loads(text)
        except json.JSONDecodeError:
            return {}, (jsonify({"ok": False, "error": "INVALID_JSON"}), 400)
        if not isinstance(body, dict):
            return {}, (jsonify({"ok": False, "error": "INVALID_REQUEST"}), 400)
        if body:
            return {}, (jsonify({"ok": False, "error": "UNKNOWN_FIELD"}), 400)
        return {}, None

    def _open_artifact_validated(
        artifact_path: pathlib.Path,
        run_dir: pathlib.Path,
        max_bytes: int,
    ) -> bytes:
        """Read artifact using lstat/open/fstat validated-handle model."""
        # Validate parent chain up to run_dir
        parent = artifact_path.parent
        while parent != run_dir and parent != artifact_path.parent.parent:
            try:
                pst = os.lstat(parent)
            except OSError:
                raise RuntimeError("parent stat failed")
            if not stat.S_ISDIR(pst.st_mode) or _is_link_or_reparse_lstat(pst):
                raise RuntimeError("parent is not a real directory")
            if parent == run_dir:
                break
            parent = parent.parent

        st_lstat = os.lstat(artifact_path)
        if not stat.S_ISREG(st_lstat.st_mode):
            raise RuntimeError("not a regular file")
        if _is_link_or_reparse_lstat(st_lstat):
            raise RuntimeError("artifact is a symlink or reparse point")
        if st_lstat.st_size > max_bytes:
            raise RuntimeError("artifact pre-open size exceeded")

        handle = None
        try:
            handle = open(artifact_path, "rb")  # noqa: WPS515
            st_fstat = os.fstat(handle.fileno())
            if st_lstat.st_ino != 0 and st_fstat.st_ino != 0:
                if (st_lstat.st_dev, st_lstat.st_ino) != (st_fstat.st_dev, st_fstat.st_ino):
                    raise RuntimeError("artifact identity mismatch")
            if st_fstat.st_size > max_bytes:
                raise RuntimeError("artifact grew after open")
            return handle.read()
        finally:
            if handle is not None:
                try:
                    handle.close()
                except OSError:
                    pass

    # ── Route: POST /api/standards-compliance-v2/runs ─────────────────────────

    @bp.route("/api/standards-compliance-v2/runs", methods=["POST"])
    @require_auth
    def sc_v2_post_run():
        if not _is_admin(g.user_id):
            return jsonify({"ok": False, "error": "FORBIDDEN", "error_code": "FORBIDDEN"}), 403

        body, err = _parse_post_body()
        if err is not None:
            return err

        if not _SEMAPHORE.acquire(blocking=False):
            return jsonify({"ok": False, "error": "CAPACITY_BUSY"}), 503

        run_id   = uuid.uuid4().hex
        run_path = case_path / run_id

        try:
            _revalidate_roots()
            _cleanup_expired()
            _cleanup_orphans()

            # Reduction loop: skip refused, attempt all candidates before 507
            valid_runs = _list_completed_runs()
            attempted_ids: set[str] = set()
            while len(valid_runs) > _PRE_GEN_TARGET:
                candidates: list[tuple[str, pathlib.Path]] = []
                for rp in valid_runs:
                    if rp.name in attempted_ids:
                        continue
                    try:
                        d = _read_metadata(rp.name)
                        candidates.append((d.get("created_at", ""), rp))
                    except Exception:
                        attempted_ids.add(rp.name)
                if not candidates:
                    break
                candidates.sort(key=lambda x: x[0])
                oldest_rp = candidates[0][1]
                attempted_ids.add(oldest_rp.name)
                _safe_delete_run_dir(oldest_rp)
                valid_runs = _list_completed_runs()

            valid_runs = _list_completed_runs()
            if len(valid_runs) > _PRE_GEN_TARGET:
                return jsonify({"ok": False, "error": "RETENTION_CAPACITY_EXCEEDED"}), 507

            t0 = time.monotonic()
            try:
                result = _generate(
                    output_root=str(case_path),
                    run_id=run_id,
                    case_id=_CASE_ID,
                    overwrite=False,
                )
            except Exception:
                _LOG.exception("V2 generator failed run_id=%s", run_id)
                _safe_delete_run_dir(run_path)
                return jsonify({"ok": False, "error": "GENERATION_FAILED"}), 500

            elapsed = time.monotonic() - t0

            now_utc = datetime.datetime.now(datetime.timezone.utc)
            metadata: dict[str, Any] = {
                "schema_version": 1,
                "run_id":        run_id,
                "case_id":       _CASE_ID,
                "created_at":    now_utc.isoformat(),
                "status":        "completed",
                "score": {
                    "overall_pass":      result.get("overall_pass"),
                    "score_pct":         result.get("score_pct"),
                    "traffic_light":     result.get("traffic_light"),
                    "cross_format_pass": result.get("cross_format_pass"),
                    "mismatches":        result.get("mismatches", []),
                    "user_pdf_pages":    result.get("user_pdf_pages"),
                    "admin_pdf_pages":   result.get("admin_pdf_pages"),
                    "excel_sheets":      result.get("excel_sheets"),
                    "ml_ready":          result.get("ml_ready"),
                },
                "governance":     _governance,
                "artifact_keys":  sorted(_ARTIFACT_MAP.keys()),
            }

            meta_path = run_path / "run_metadata.json"
            tmp_path  = run_path / "run_metadata.json.tmp"
            try:
                with open(tmp_path, "w", encoding="utf-8") as fh:
                    json.dump(metadata, fh, ensure_ascii=False, indent=2)
                    fh.flush()
                    os.fsync(fh.fileno())
                os.replace(str(tmp_path), str(meta_path))
            except Exception:
                _LOG.exception("V2 metadata write failed run_id=%s", run_id)
                tmp_path.unlink(missing_ok=True)
                _safe_delete_run_dir(run_path)
                return jsonify({"ok": False, "error": "STORAGE_ERROR"}), 500

            # Post-generation capacity enforcement
            all_runs = _list_completed_runs()
            if len(all_runs) > _MAX_COMPLETED:
                timed: list[tuple[str, pathlib.Path]] = []
                for rp in all_runs:
                    if rp.name == run_id:
                        continue
                    try:
                        d = _read_metadata(rp.name)
                        timed.append((d.get("created_at", ""), rp))
                    except Exception:
                        pass
                timed.sort(key=lambda x: x[0])
                excess = len(all_runs) - _MAX_COMPLETED
                for _, rp in timed[:excess]:
                    _safe_delete_run_dir(rp)

            return jsonify({
                "ok":                True,
                "run_id":            run_id,
                "status":            "completed",
                "score_pct":         result.get("score_pct"),
                "traffic_light":     result.get("traffic_light"),
                "overall_pass":      result.get("overall_pass"),
                "elapsed_seconds":   round(elapsed, 2),
                "advisory_only":     _governance["advisory_only"],
                "certification_ready": _governance["certification_ready"],
                "synthetic_data":    _governance["synthetic_data"],
            }), 200

        finally:
            _SEMAPHORE.release()

    # ── Route: GET /api/standards-compliance-v2/runs/<run_id> ─────────────────

    @bp.route("/api/standards-compliance-v2/runs/<run_id>", methods=["GET"])
    @require_auth
    def sc_v2_get_metadata(run_id: str):
        if not _is_admin(g.user_id):
            return jsonify({"ok": False, "error": "FORBIDDEN", "error_code": "FORBIDDEN"}), 403
        if not _valid_run_id(run_id):
            return jsonify({"ok": False, "error": "RUN_NOT_FOUND"}), 404
        try:
            _revalidate_roots()
            data = _read_metadata(run_id)
        except Exception:
            return jsonify({"ok": False, "error": "RUN_NOT_FOUND"}), 404

        body_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        resp = make_response(body_bytes)
        resp.headers["Content-Type"]  = "application/json"
        resp.headers["Cache-Control"] = "no-store"
        return resp, 200

    # ── Route: GET /api/standards-compliance-v2/runs/<run_id>/artifacts/<artifact_key>

    @bp.route(
        "/api/standards-compliance-v2/runs/<run_id>/artifacts/<artifact_key>",
        methods=["GET"],
    )
    @require_auth
    def sc_v2_get_artifact(run_id: str, artifact_key: str):
        if not _is_admin(g.user_id):
            return jsonify({"ok": False, "error": "FORBIDDEN", "error_code": "FORBIDDEN"}), 403
        if not _valid_run_id(run_id):
            return jsonify({"ok": False, "error": "ARTIFACT_NOT_FOUND"}), 404
        if artifact_key not in _ARTIFACT_MAP:
            return jsonify({"ok": False, "error": "ARTIFACT_NOT_FOUND"}), 404

        try:
            _revalidate_roots()
        except RuntimeError:
            return jsonify({"ok": False, "error": "ARTIFACT_NOT_FOUND"}), 404

        filename_tpl, mime, disposition, max_bytes = _ARTIFACT_MAP[artifact_key]
        filename = filename_tpl.format(cid=_CASE_ID)

        run_dir = case_path / run_id
        if artifact_key in _AUDIT_SUBDIR_KEYS:
            artifact_path = run_dir / "audits" / filename
        else:
            artifact_path = run_dir / "artifacts" / filename

        try:
            data = _open_artifact_validated(artifact_path, run_dir, max_bytes)
        except Exception:
            return jsonify({"ok": False, "error": "ARTIFACT_NOT_FOUND"}), 404

        resp = make_response(data)
        resp.headers["Content-Type"]          = mime
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Cache-Control"]          = "no-store"
        resp.headers["Pragma"]                 = "no-cache"
        resp.headers["Content-Disposition"]   = f'{disposition}; filename="{filename}"'
        if artifact_key in ("user_html", "admin_html"):
            resp.headers["Content-Security-Policy"] = _CSP_HTML
        return resp, 200

    # ── Route: DELETE /api/standards-compliance-v2/runs/<run_id> ──────────────

    @bp.route("/api/standards-compliance-v2/runs/<run_id>", methods=["DELETE"])
    @require_auth
    def sc_v2_delete_run(run_id: str):
        if not _is_admin(g.user_id):
            return jsonify({"ok": False, "error": "FORBIDDEN", "error_code": "FORBIDDEN"}), 403
        if not _valid_run_id(run_id):
            return jsonify({"ok": False, "error": "RUN_NOT_FOUND"}), 404

        if not _SEMAPHORE.acquire(blocking=False):
            return jsonify({"ok": False, "error": "CAPACITY_BUSY"}), 503

        try:
            _revalidate_roots()
            run_path = case_path / run_id
            result   = _safe_delete_run_dir(run_path)

            if result == _DelResult.DELETED:
                return jsonify({"ok": True, "deleted": True, "run_id": run_id}), 200
            if result == _DelResult.NOT_FOUND:
                return jsonify({"ok": False, "error": "RUN_NOT_FOUND"}), 404
            if result in (
                _DelResult.REFUSED_OUTSIDE_ROOT,
                _DelResult.REFUSED_REPARSE_POINT,
                _DelResult.REFUSED_UNKNOWN_STRUCTURE,
            ):
                return jsonify({"ok": False, "error": "RUN_DELETE_REFUSED"}), 409
            # FAILED_IO
            return jsonify({"ok": False, "error": "STORAGE_ERROR"}), 500

        finally:
            _SEMAPHORE.release()

    # ── Register Blueprint ─────────────────────────────────────────────────────
    app.register_blueprint(bp)
    app.extensions["sc_v2_registered"] = True
