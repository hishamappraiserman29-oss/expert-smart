"""
pv_standards_compliance_endpoint.py — Wave 3B Standards Compliance Endpoint

Admin-only. Static synthetic diagnostic. No certification claims.
Public export: register_standards_compliance(app, require_auth, _is_admin, OUTPUTS)
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import stat as _stat_mod
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import BinaryIO, Mapping

_log = logging.getLogger(__name__)

# ── Module-level semaphore (POST and DELETE share this) ────────────────────────
_SEMAPHORE = threading.BoundedSemaphore(1)

# ── Constants ──────────────────────────────────────────────────────────────────
_CASE_ID               = "QA-COMPLIANCE-VISUAL-001"
_ENDPOINT_RUN_ID_RE    = re.compile(r"^[0-9a-f]{32}$")
_MAX_COMPLETED_RUNS    = 10
_PRE_GENERATION_TARGET = 9
_ORPHAN_AGE_SECONDS    = 86_400     # 24 h
_MAX_SCAN_DEPTH        = 5
_MAX_ENTRIES_PER_DIR   = 200

_SAFE_CASE_ID = "QA-COMPLIANCE-VISUAL-001"

# Artifact key → (subdir, filename)
_ARTIFACT_FILENAMES: dict[str, tuple[str, str]] = {
    "user_html":          ("artifacts", f"compliance_{_SAFE_CASE_ID}_user.html"),
    "admin_html":         ("artifacts", f"compliance_{_SAFE_CASE_ID}_admin.html"),
    "user_pdf":           ("artifacts", f"compliance_{_SAFE_CASE_ID}_user.pdf"),
    "admin_pdf":          ("artifacts", f"compliance_{_SAFE_CASE_ID}_admin.pdf"),
    "admin_excel":        ("artifacts", f"compliance_{_SAFE_CASE_ID}_admin.xlsx"),
    "visual_qa_audit":    ("audits",    "compliance_visual_qa_report.json"),
    "cross_format_audit": ("audits",    "compliance_cross_format_consistency.json"),
    "content_audit":      ("audits",    "compliance_content_audit.json"),
}

_ARTIFACT_SIZE_LIMITS: dict[str, int] = {
    "run_metadata.json":   64 * 1024,
    "user_html":           10 * 1024 * 1024,
    "admin_html":          10 * 1024 * 1024,
    "user_pdf":           100 * 1024 * 1024,
    "admin_pdf":          100 * 1024 * 1024,
    "admin_excel":         50 * 1024 * 1024,
    "visual_qa_audit":      5 * 1024 * 1024,
    "cross_format_audit":   5 * 1024 * 1024,
    "content_audit":        5 * 1024 * 1024,
}

# True = attachment, False = inline
_ARTIFACT_DISPOSITION: dict[str, bool] = {
    "user_html":          False,
    "admin_html":         False,
    "user_pdf":           True,
    "admin_pdf":          True,
    "admin_excel":        True,
    "visual_qa_audit":    True,
    "cross_format_audit": True,
    "content_audit":      True,
}

_ARTIFACT_MIMETYPES: dict[str, str] = {
    "user_html":          "text/html; charset=utf-8",
    "admin_html":         "text/html; charset=utf-8",
    "user_pdf":           "application/pdf",
    "admin_pdf":          "application/pdf",
    "admin_excel":        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "visual_qa_audit":    "application/json",
    "cross_format_audit": "application/json",
    "content_audit":      "application/json",
}

_APPROVED_RUN_TOP_ENTRIES = frozenset({
    "artifacts", "audits", "screenshots",
    "run_metadata.json", "run_metadata.json.tmp",
})
_APPROVED_EXTENSIONS = frozenset({".html", ".pdf", ".xlsx", ".json", ".png", ".tmp"})

_V1_REQUIRED_TOP_KEYS = frozenset({
    "schema_version", "run_id", "case_id", "created_at",
    "status", "score", "governance", "artifact_keys",
})
_V1_REQUIRED_SCORE_KEYS = frozenset({
    "percentage", "traffic_light", "label",
    "critical_findings", "blocks_issuance",
})
_V1_REQUIRED_GOVERNANCE_KEYS = frozenset({
    "advisory_only", "certification_ready",
    "official_compliance_decision", "synthetic_data",
})
_REQUIRED_ARTIFACT_KEYS = frozenset({
    "user_html", "admin_html", "user_pdf", "admin_pdf", "admin_excel",
    "visual_qa_audit", "cross_format_audit", "content_audit",
})

_SORTED_ARTIFACT_KEYS = sorted(_REQUIRED_ARTIFACT_KEYS)

_HTML_CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; "
    "img-src data: blob:; font-src data:; "
    "base-uri 'none'; frame-ancestors 'none'"
)


# ── Dataclasses ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class _RootIdentity:
    st_dev: int
    st_ino: int


@dataclass(frozen=True)
class _ServerRoots:
    outputs_path:    Path
    standards_path:  Path
    case_path:       Path
    outputs_root_r:  Path
    standards_root_r: Path
    case_root_r:     Path
    identities:      dict  # label -> _RootIdentity


# ── Enums ──────────────────────────────────────────────────────────────────────

class _DeleteResult(Enum):
    DELETED                   = "DELETED"
    NOT_FOUND                 = "NOT_FOUND"
    REFUSED_OUTSIDE_ROOT      = "REFUSED_OUTSIDE_ROOT"
    REFUSED_REPARSE_POINT     = "REFUSED_REPARSE_POINT"
    REFUSED_UNKNOWN_STRUCTURE = "REFUSED_UNKNOWN_STRUCTURE"
    FAILED_IO                 = "FAILED_IO"


# ── Exceptions ─────────────────────────────────────────────────────────────────

class _RootValidationError(Exception):
    pass


class _FileValidationError(Exception):
    pass


# ── Path safety ────────────────────────────────────────────────────────────────

def _normalize_absolute_path_text(value: "str | os.PathLike[str]") -> str:
    return os.path.normcase(
        os.path.abspath(os.path.normpath(os.fspath(value)))
    )


def _is_link_or_reparse_lstat(lst) -> bool:
    if _stat_mod.S_ISLNK(lst.st_mode):
        return True
    attrs = getattr(lst, "st_file_attributes", 0) or 0
    reparse_flag = getattr(_stat_mod, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attrs & reparse_flag)


def _capture_identity(path: Path) -> _RootIdentity:
    lst = os.lstat(path)
    return _RootIdentity(st_dev=lst.st_dev, st_ino=lst.st_ino)


# ── Root chain validation ──────────────────────────────────────────────────────

def _revalidate_server_roots(
    *,
    outputs_path: Path,
    standards_path: Path,
    case_path: Path,
    outputs_root_r: Path,
    standards_root_r: Path,
    case_root_r: Path,
    root_identities: "Mapping[str, _RootIdentity]",
) -> Path:
    resolved: dict[str, Path] = {}
    for configured, reg_resolved, label in (
        (outputs_path,   outputs_root_r,   "OUTPUTS"),
        (standards_path, standards_root_r, "standards_root"),
        (case_path,      case_root_r,      "case_root"),
    ):
        try:
            lst = os.lstat(configured)
        except OSError as exc:
            raise _RootValidationError(f"{label}: lstat failed: {exc}")
        if not _stat_mod.S_ISDIR(lst.st_mode):
            raise _RootValidationError(f"{label}: not a directory")
        if _is_link_or_reparse_lstat(lst):
            raise _RootValidationError(f"{label}: is a reparse point or symlink")
        reg_id = root_identities[label]
        if lst.st_ino != 0:
            if lst.st_dev != reg_id.st_dev or lst.st_ino != reg_id.st_ino:
                raise _RootValidationError(f"{label}: directory identity changed")
        try:
            current_r = configured.resolve()
        except OSError as exc:
            raise _RootValidationError(f"{label}: resolve failed: {exc}")
        if current_r != reg_resolved:
            raise _RootValidationError(f"{label}: resolved target changed")
        resolved[label] = current_r
    try:
        resolved["standards_root"].relative_to(resolved["OUTPUTS"])
    except ValueError:
        raise _RootValidationError("standards_root no longer under OUTPUTS")
    try:
        resolved["case_root"].relative_to(resolved["standards_root"])
    except ValueError:
        raise _RootValidationError("case_root no longer under standards_root")
    return resolved["case_root"]


# ── Safe file opening ──────────────────────────────────────────────────────────

def _open_validated_regular_file(
    *,
    target: Path,
    run_dir: Path,
    case_root_r: Path,
    max_bytes: int,
) -> BinaryIO:
    # 1. Re-lstat case_root_r
    try:
        lst = os.lstat(case_root_r)
    except OSError as exc:
        raise _FileValidationError(f"case_root lstat failed: {exc}")
    if not _stat_mod.S_ISDIR(lst.st_mode):
        raise _FileValidationError("case_root: not a directory")
    if _is_link_or_reparse_lstat(lst):
        raise _FileValidationError("case_root: is a reparse point")
    # 2-3. lstat run_dir
    try:
        lst = os.lstat(run_dir)
    except OSError as exc:
        raise _FileValidationError(f"run_dir lstat failed: {exc}")
    if not _stat_mod.S_ISDIR(lst.st_mode):
        raise _FileValidationError("run_dir: not a directory")
    if _is_link_or_reparse_lstat(lst):
        raise _FileValidationError("run_dir: is a reparse point")
    # 4. run_dir name pattern
    if not _ENDPOINT_RUN_ID_RE.fullmatch(run_dir.name):
        raise _FileValidationError("run_dir: name does not match run-ID pattern")
    # 5. Lexical containment
    try:
        run_dir.relative_to(case_root_r)
    except ValueError:
        raise _FileValidationError("run_dir: not under case_root_r")
    # 6. Target under run_dir
    try:
        target.relative_to(run_dir)
    except ValueError:
        raise _FileValidationError("target: not under run_dir")
    # 7. Walk ancestors between target and run_dir
    current = target.parent
    while current != run_dir and current != current.parent:
        try:
            anc = os.lstat(current)
        except OSError as exc:
            raise _FileValidationError(f"ancestor lstat failed: {exc}")
        if not _stat_mod.S_ISDIR(anc.st_mode):
            raise _FileValidationError(f"ancestor not a directory: {current.name}")
        if _is_link_or_reparse_lstat(anc):
            raise _FileValidationError(f"ancestor is a reparse point: {current.name}")
        current = current.parent
    # 8. lstat target
    try:
        target_lst = os.lstat(target)
    except OSError as exc:
        raise _FileValidationError(f"target lstat failed: {exc}")
    if not _stat_mod.S_ISREG(target_lst.st_mode):
        raise _FileValidationError("target: not a regular file")
    if _is_link_or_reparse_lstat(target_lst):
        raise _FileValidationError("target: is a reparse point or symlink")
    if target_lst.st_size > max_bytes:
        raise _FileValidationError("target: exceeds size limit")
    # 9. open → fstat → identity
    handle = None
    try:
        handle = open(target, "rb")
        target_fst = os.fstat(handle.fileno())
    except OSError as exc:
        if handle is not None:
            handle.close()
        raise _FileValidationError(f"target open/fstat failed: {exc}")
    try:
        if target_lst.st_ino != 0:
            if (target_lst.st_dev != target_fst.st_dev
                    or target_lst.st_ino != target_fst.st_ino):
                raise _FileValidationError("target: lstat/fstat identity mismatch")
        if not _stat_mod.S_ISREG(target_fst.st_mode):
            raise _FileValidationError("target: not a regular file after open")
    except _FileValidationError:
        handle.close()
        raise
    return handle


# ── Metadata validation ────────────────────────────────────────────────────────

def _validate_run_metadata(data: object) -> bool:
    if not isinstance(data, dict):
        return False
    if set(data.keys()) != _V1_REQUIRED_TOP_KEYS:
        return False
    score = data.get("score")
    if not isinstance(score, dict):
        return False
    if set(score.keys()) != _V1_REQUIRED_SCORE_KEYS:
        return False
    pct = score.get("percentage")
    if type(pct) is not int:  # rejects bool
        return False
    if not (0 <= pct <= 100):
        return False
    if score.get("traffic_light") not in {"green", "yellow", "red"}:
        return False
    if not isinstance(score.get("label"), str):
        return False
    for k in ("critical_findings", "blocks_issuance"):
        v = score.get(k)
        if not isinstance(v, list):
            return False
        if not all(isinstance(x, str) for x in v):
            return False
    gov = data.get("governance")
    if not isinstance(gov, dict):
        return False
    if set(gov.keys()) != _V1_REQUIRED_GOVERNANCE_KEYS:
        return False
    if gov.get("advisory_only") is not True:
        return False
    if gov.get("certification_ready") is not False:
        return False
    if gov.get("official_compliance_decision") is not False:
        return False
    if gov.get("synthetic_data") is not True:
        return False
    ak = data.get("artifact_keys")
    if not isinstance(ak, list):
        return False
    if len(ak) != 8 or len(set(ak)) != 8:
        return False
    if set(ak) != _REQUIRED_ARTIFACT_KEYS:
        return False
    created_at = data.get("created_at")
    if not isinstance(created_at, str):
        return False
    try:
        dt = datetime.fromisoformat(created_at)
        if dt.utcoffset() != timedelta(0):
            return False
    except (ValueError, TypeError):
        return False
    if not isinstance(data.get("run_id"), str):
        return False
    if not isinstance(data.get("case_id"), str):
        return False
    return True


def _read_metadata(metadata_path: Path, run_dir: Path, case_root_r: Path) -> "dict | None":
    handle = None
    try:
        handle = _open_validated_regular_file(
            target=metadata_path,
            run_dir=run_dir,
            case_root_r=case_root_r,
            max_bytes=_ARTIFACT_SIZE_LIMITS["run_metadata.json"],
        )
        raw = handle.read()
    except (_FileValidationError, OSError):
        return None
    finally:
        if handle is not None:
            handle.close()
    try:
        data = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not _validate_run_metadata(data):
        return None
    return data


# ── Run directory enumeration ──────────────────────────────────────────────────

def _list_run_dirs(case_root_r: Path) -> "list[tuple[float, Path]]":
    result: list[tuple[float, Path]] = []
    try:
        for entry in os.scandir(case_root_r):
            if not entry.is_dir(follow_symlinks=False):
                continue
            if not _ENDPOINT_RUN_ID_RE.fullmatch(entry.name):
                continue
            try:
                lst = entry.stat(follow_symlinks=False)
                if _is_link_or_reparse_lstat(lst):
                    continue
                result.append((lst.st_mtime, Path(entry.path)))
            except OSError:
                continue
    except OSError:
        pass
    return result


def _count_valid_runs(case_root_r: Path) -> int:
    count = 0
    for _, run_dir in _list_run_dirs(case_root_r):
        if _read_metadata(run_dir / "run_metadata.json", run_dir, case_root_r) is not None:
            count += 1
    return count


# ── Orphan cleanup ─────────────────────────────────────────────────────────────

def _cleanup_orphans(case_root_r: Path) -> None:
    now = time.time()
    for mtime, run_dir in _list_run_dirs(case_root_r):
        if now - mtime < _ORPHAN_AGE_SECONDS:
            continue
        if _read_metadata(run_dir / "run_metadata.json", run_dir, case_root_r) is not None:
            continue  # has valid metadata — not an orphan
        result = _safe_delete_run_dir(run_dir, case_root_r)
        if result not in (_DeleteResult.DELETED, _DeleteResult.NOT_FOUND):
            _log.warning("Orphan cleanup skipped %s: %s", run_dir.name, result.value)


# ── Retention ──────────────────────────────────────────────────────────────────

def _retention_reduce(
    case_root_r: Path,
    *,
    target: int,
    skip_run_id: "str | None" = None,
) -> None:
    runs: list[tuple[float, Path]] = []
    for _, run_dir in _list_run_dirs(case_root_r):
        if skip_run_id and run_dir.name == skip_run_id:
            continue
        if _read_metadata(run_dir / "run_metadata.json", run_dir, case_root_r) is not None:
            try:
                mtime = os.lstat(run_dir / "run_metadata.json").st_mtime
            except OSError:
                mtime = 0.0
            runs.append((mtime, run_dir))
    runs.sort(key=lambda x: x[0])  # oldest first
    valid_count = len(runs) + (1 if skip_run_id else 0)
    for _, run_dir in runs:
        if valid_count <= target:
            break
        r = _safe_delete_run_dir(run_dir, case_root_r)
        if r == _DeleteResult.DELETED:
            valid_count -= 1


# ── Safe deletion ──────────────────────────────────────────────────────────────

def _scan_for_delete(path: Path, case_root_r: Path, depth: int) -> "_DeleteResult | None":
    if depth > _MAX_SCAN_DEPTH:
        return _DeleteResult.REFUSED_UNKNOWN_STRUCTURE
    try:
        entries = list(os.scandir(path))
    except OSError as exc:
        _log.error("scandir failed during delete scan: %s", exc)
        return _DeleteResult.FAILED_IO
    if len(entries) > _MAX_ENTRIES_PER_DIR:
        return _DeleteResult.REFUSED_UNKNOWN_STRUCTURE
    for entry in entries:
        try:
            e_lst = entry.stat(follow_symlinks=False)
        except OSError as exc:
            _log.error("entry stat failed during delete scan: %s", exc)
            return _DeleteResult.FAILED_IO
        if _is_link_or_reparse_lstat(e_lst):
            return _DeleteResult.REFUSED_REPARSE_POINT
        entry_path = Path(entry.path)
        try:
            entry_path.relative_to(case_root_r)
        except ValueError:
            return _DeleteResult.REFUSED_OUTSIDE_ROOT
        if depth == 0 and entry.name not in _APPROVED_RUN_TOP_ENTRIES:
            _log.warning("Unknown top-level entry: %s", entry.name)
            return _DeleteResult.REFUSED_UNKNOWN_STRUCTURE
        if entry.is_dir(follow_symlinks=False):
            sub = _scan_for_delete(entry_path, case_root_r, depth + 1)
            if sub is not None:
                return sub
        else:
            ext = os.path.splitext(entry.name)[1].lower()
            if ext not in _APPROVED_EXTENSIONS:
                _log.warning("Unknown extension in run dir: %s", entry.name)
                return _DeleteResult.REFUSED_UNKNOWN_STRUCTURE
    return None


def _safe_delete_run_dir(run_dir: Path, case_root_r: Path) -> _DeleteResult:
    try:
        lst = os.lstat(run_dir)
    except FileNotFoundError:
        return _DeleteResult.NOT_FOUND
    except OSError as exc:
        _log.error("lstat(run_dir) failed: %s", exc)
        return _DeleteResult.FAILED_IO
    if _is_link_or_reparse_lstat(lst):
        return _DeleteResult.REFUSED_REPARSE_POINT
    if not _stat_mod.S_ISDIR(lst.st_mode):
        return _DeleteResult.REFUSED_UNKNOWN_STRUCTURE
    try:
        run_dir.relative_to(case_root_r)
    except ValueError:
        return _DeleteResult.REFUSED_OUTSIDE_ROOT
    if not _ENDPOINT_RUN_ID_RE.fullmatch(run_dir.name):
        return _DeleteResult.REFUSED_UNKNOWN_STRUCTURE
    scan = _scan_for_delete(run_dir, case_root_r, depth=0)
    if scan is not None:
        return scan
    try:
        shutil.rmtree(run_dir)
    except OSError as exc:
        _log.error("rmtree(%s) failed: %s", run_dir.name, exc)
        return _DeleteResult.FAILED_IO
    # Verify post-delete absence
    try:
        os.lstat(run_dir)
        _log.error("rmtree OK but dir still present: %s", run_dir.name)
        return _DeleteResult.FAILED_IO
    except FileNotFoundError:
        return _DeleteResult.DELETED
    except OSError as exc:
        _log.error("post-delete lstat unexpected error: %s", exc)
        return _DeleteResult.FAILED_IO


# ── Security headers ───────────────────────────────────────────────────────────

def _apply_artifact_headers(response: object, artifact_key: str) -> None:
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    if artifact_key in ("user_html", "admin_html"):
        response.headers["Content-Security-Policy"] = _HTML_CSP
    # Disposition is handled by send_file; explicit header only for non-inline
    if _ARTIFACT_DISPOSITION.get(artifact_key):
        response.headers["Content-Disposition"] = (
            f"attachment; filename=\"{_ARTIFACT_FILENAMES[artifact_key][1]}\""
        )


# ── Error response helper ──────────────────────────────────────────────────────

def _err(jsonify_fn, code: str, msg: str, status: int):
    r = jsonify_fn({"ok": False, "error_code": code, "message": msg})
    return r, status


# ── Public registration export ─────────────────────────────────────────────────

def register_standards_compliance(app, require_auth, _is_admin, OUTPUTS) -> None:  # noqa: N803
    """Register Wave 3B V1 standards-compliance routes onto *app*.

    Matches the import stub in bridge_api.py exactly.
    Idempotent — second call is a no-op.
    No routes, directories, browsers, or network calls at import time.
    """
    from flask import Blueprint, g, jsonify, request, send_file  # noqa: PLC0415

    # ── Idempotency guard ──────────────────────────────────────────────────────
    if app.extensions.get("standards_compliance_endpoint_registered"):
        return

    # ── 1. Validate OUTPUTS ────────────────────────────────────────────────────
    outputs_path = Path(OUTPUTS).absolute()
    try:
        lst = os.lstat(outputs_path)
    except OSError as exc:
        raise RuntimeError(f"OUTPUTS lstat failed: {exc}") from exc
    if not _stat_mod.S_ISDIR(lst.st_mode):
        raise RuntimeError("OUTPUTS is not a directory")
    if _is_link_or_reparse_lstat(lst):
        raise RuntimeError("OUTPUTS is a reparse point or symlink")

    # ── 2. Create server-controlled subdirectories (registration only) ─────────
    standards_path = outputs_path / "standards_compliance"
    case_path      = standards_path / _CASE_ID
    for path in (standards_path, case_path):
        try:
            path.mkdir(parents=False, exist_ok=True)
        except OSError as exc:
            raise RuntimeError(f"Cannot create {path.name}: {exc}") from exc
        try:
            lst = os.lstat(path)
        except OSError as exc:
            raise RuntimeError(f"{path.name}: lstat after mkdir failed: {exc}") from exc
        if not _stat_mod.S_ISDIR(lst.st_mode):
            raise RuntimeError(f"{path.name}: not a directory after creation")
        if _is_link_or_reparse_lstat(lst):
            raise RuntimeError(f"{path.name}: is a reparse point after creation")

    # ── 3. Resolve all paths ───────────────────────────────────────────────────
    outputs_root_r   = outputs_path.resolve()
    standards_root_r = standards_path.resolve()
    case_root_r      = case_path.resolve()

    try:
        standards_root_r.relative_to(outputs_root_r)
    except ValueError as exc:
        raise RuntimeError("standards_path not under OUTPUTS") from exc
    try:
        case_root_r.relative_to(standards_root_r)
    except ValueError as exc:
        raise RuntimeError("case_path not under standards_path") from exc

    # ── 4. Capture root identities ─────────────────────────────────────────────
    root_identities: dict[str, _RootIdentity] = {
        "OUTPUTS":        _capture_identity(outputs_path),
        "standards_root": _capture_identity(standards_path),
        "case_root":      _capture_identity(case_path),
    }

    # ── 5. Build roots context (captured by closures) ──────────────────────────
    roots = _ServerRoots(
        outputs_path=outputs_path,
        standards_path=standards_path,
        case_path=case_path,
        outputs_root_r=outputs_root_r,
        standards_root_r=standards_root_r,
        case_root_r=case_root_r,
        identities=root_identities,
    )

    # ── 6. Verify generator import ────────────────────────────────────────────
    try:
        from standards_compliance_visual_qa_generator import (  # noqa: PLC0415
            run_standards_compliance_visual_qa,
        )
    except ImportError as exc:
        raise RuntimeError(f"Cannot import generator: {exc}") from exc

    # ── 7. Blueprint and collision checks ─────────────────────────────────────
    bp = Blueprint("standards_compliance_v1", __name__)
    bp_name = "standards_compliance_v1"

    expected_endpoints = {
        f"{bp_name}.sc_v1_post_run",
        f"{bp_name}.sc_v1_get_run",
        f"{bp_name}.sc_v1_get_artifact",
        f"{bp_name}.sc_v1_delete_run",
    }
    existing = set(app.view_functions.keys())
    collisions = expected_endpoints & existing
    if collisions:
        raise RuntimeError(f"Endpoint name collisions: {collisions}")

    expected_routes = {
        ("/api/standards-compliance/runs", "POST"),
        ("/api/standards-compliance/runs/<run_id>", "GET"),
        ("/api/standards-compliance/runs/<run_id>/artifacts/<artifact_key>", "GET"),
        ("/api/standards-compliance/runs/<run_id>", "DELETE"),
    }
    existing_rules = {
        (str(rule), method)
        for rule in app.url_map.iter_rules()
        for method in rule.methods
        if method not in ("HEAD", "OPTIONS")
    }
    route_collisions = expected_routes & existing_rules
    if route_collisions:
        raise RuntimeError(f"Route collisions: {route_collisions}")

    # ── 8. Define helpers for closures ─────────────────────────────────────────

    def _roots_revalidate() -> Path:
        return _revalidate_server_roots(
            outputs_path=roots.outputs_path,
            standards_path=roots.standards_path,
            case_path=roots.case_path,
            outputs_root_r=roots.outputs_root_r,
            standards_root_r=roots.standards_root_r,
            case_root_r=roots.case_root_r,
            root_identities=roots.identities,
        )

    # ── 9. Route handlers ──────────────────────────────────────────────────────

    @bp.route("/runs", methods=["POST"])
    @require_auth
    def sc_v1_post_run():
        if not _is_admin(g.user_id):
            return _err(jsonify, "FORBIDDEN", "Admin access required.", 403)

        # Body parsing — single stream read
        raw = request.stream.read(257)
        if len(raw) > 256:
            return _err(jsonify, "PAYLOAD_TOO_LARGE", "Request body too large.", 413)

        if raw:
            ct = (request.content_type or "").lower()
            if "application/json" not in ct:
                return _err(jsonify, "UNSUPPORTED_MEDIA_TYPE",
                            "Content-Type must be application/json.", 415)
            try:
                body_text = raw.decode("utf-8")
            except UnicodeDecodeError:
                return _err(jsonify, "INVALID_JSON", "Malformed UTF-8.", 400)
            try:
                body = json.loads(body_text)
            except json.JSONDecodeError:
                return _err(jsonify, "INVALID_JSON", "Malformed JSON.", 400)
            if not isinstance(body, dict):
                return _err(jsonify, "INVALID_REQUEST",
                            "Request body must be a JSON object or empty.", 400)
            if body:
                return _err(jsonify, "UNKNOWN_FIELD",
                            "No fields are accepted in request body.", 400)

        # Acquire semaphore
        if not _SEMAPHORE.acquire(blocking=False):
            return _err(jsonify, "CAPACITY_BUSY",
                        "Another operation is in progress.", 503)
        try:
            # Revalidate roots
            try:
                cur_case_r = _roots_revalidate()
            except _RootValidationError as exc:
                _log.error("POST root revalidation failed: %s", exc)
                return _err(jsonify, "STORAGE_UNAVAILABLE",
                            "Storage is unavailable.", 503)

            # Orphan cleanup + pre-generation retention
            _cleanup_orphans(cur_case_r)
            _retention_reduce(cur_case_r, target=_PRE_GENERATION_TARGET)

            # Capacity gate
            valid_count = _count_valid_runs(cur_case_r)
            if valid_count > _PRE_GENERATION_TARGET:
                return _err(jsonify, "RETENTION_CAPACITY_EXCEEDED",
                            "Storage capacity exceeded. Try again later.", 507)

            # Generate
            server_run_id   = uuid.uuid4().hex
            expected_run_dir = cur_case_r / server_run_id

            try:
                result = run_standards_compliance_visual_qa(
                    output_root=roots.standards_root_r,
                    run_id=server_run_id,
                    overwrite=False,
                )
            except Exception as exc:
                _log.error("Generator raised: %s", exc)
                _safe_delete_run_dir(expected_run_dir, cur_case_r)
                return _err(jsonify, "GENERATION_FAILED", "Internal error.", 500)

            if not (isinstance(result, dict) and result.get("ok")):
                _safe_delete_run_dir(expected_run_dir, cur_case_r)
                return _err(jsonify, "INVALID_GENERATOR_RESULT", "Internal error.", 500)

            # Validate reported path — exact str, absolute, lexical compare only
            reported_value = result.get("run_directory")
            if type(reported_value) is not str:
                _safe_delete_run_dir(expected_run_dir, cur_case_r)
                return _err(jsonify, "INVALID_GENERATOR_RESULT", "Internal error.", 500)
            if not os.path.isabs(reported_value):
                _safe_delete_run_dir(expected_run_dir, cur_case_r)
                return _err(jsonify, "INVALID_GENERATOR_RESULT", "Internal error.", 500)
            if (_normalize_absolute_path_text(reported_value)
                    != _normalize_absolute_path_text(expected_run_dir)):
                _safe_delete_run_dir(expected_run_dir, cur_case_r)
                return _err(jsonify, "INVALID_GENERATOR_RESULT", "Internal error.", 500)

            # Extract score (never trust blindly — validate types)
            gen_score = result.get("score") or {}
            pct = gen_score.get("percentage", 0)
            if type(pct) is not int:
                pct = 0
            pct = max(0, min(100, pct))
            tl = gen_score.get("traffic_light", "red")
            if tl not in ("green", "yellow", "red"):
                tl = "red"
            lbl = gen_score.get("label", "")
            if not isinstance(lbl, str):
                lbl = ""
            crit = [x for x in gen_score.get("critical_findings", [])
                    if isinstance(x, str)]
            blks = [x for x in gen_score.get("blocks_issuance", [])
                    if isinstance(x, str)]

            # Atomic metadata write
            now_utc = datetime.now(tz=timezone.utc)
            metadata: dict = {
                "schema_version": 1,
                "run_id":   server_run_id,
                "case_id":  _CASE_ID,
                "created_at": now_utc.isoformat(),
                "status":   "completed",
                "score": {
                    "percentage":      pct,
                    "traffic_light":   tl,
                    "label":           lbl,
                    "critical_findings": crit,
                    "blocks_issuance": blks,
                },
                "governance": {
                    "advisory_only":             True,
                    "certification_ready":       False,
                    "official_compliance_decision": False,
                    "synthetic_data":            True,
                },
                "artifact_keys": _SORTED_ARTIFACT_KEYS,
            }
            final_meta = expected_run_dir / "run_metadata.json"
            tmp_meta   = expected_run_dir / "run_metadata.json.tmp"
            try:
                with open(str(tmp_meta), "w", encoding="utf-8", newline="\n") as fh:
                    json.dump(metadata, fh, ensure_ascii=False, indent=2)
                    fh.flush()
                    os.fsync(fh.fileno())
                os.replace(str(tmp_meta), str(final_meta))
            except OSError as exc:
                _log.error("Metadata write failed: %s", exc)
                try:
                    os.unlink(str(tmp_meta))
                except OSError:
                    pass
                _safe_delete_run_dir(expected_run_dir, cur_case_r)
                return _err(jsonify, "METADATA_WRITE_FAILED", "Internal error.", 500)

            # Post-generation capacity enforcement
            post_count = _count_valid_runs(cur_case_r)
            if post_count > _MAX_COMPLETED_RUNS:
                _retention_reduce(cur_case_r, target=_MAX_COMPLETED_RUNS,
                                  skip_run_id=server_run_id)
                post_count = _count_valid_runs(cur_case_r)
                if post_count > _MAX_COMPLETED_RUNS:
                    dr = _safe_delete_run_dir(expected_run_dir, cur_case_r)
                    if dr != _DeleteResult.DELETED:
                        _log.error("Cannot restore capacity; delete result: %s", dr.value)
                        return _err(jsonify, "STORAGE_STATE_INCONSISTENT",
                                    "Internal error.", 500)
                    return _err(jsonify, "RETENTION_CAPACITY_EXCEEDED",
                                "Storage capacity exceeded.", 507)

            resp = jsonify({
                "ok":          True,
                "run_id":      server_run_id,
                "case_id":     _CASE_ID,
                "status":      "completed",
                "score":       metadata["score"],
                "governance":  metadata["governance"],
                "artifact_keys": metadata["artifact_keys"],
                "created_at":  metadata["created_at"],
            })
            resp.headers["Cache-Control"] = "no-store"
            return resp, 200

        finally:
            _SEMAPHORE.release()

    # ── GET run metadata ───────────────────────────────────────────────────────

    @bp.route("/runs/<run_id>", methods=["GET"])
    @require_auth
    def sc_v1_get_run(run_id: str):
        if not _is_admin(g.user_id):
            return _err(jsonify, "FORBIDDEN", "Admin access required.", 403)
        if not _ENDPOINT_RUN_ID_RE.fullmatch(run_id):
            return _err(jsonify, "RUN_NOT_FOUND", "Run not found.", 404)
        try:
            cur_case_r = _roots_revalidate()
        except _RootValidationError:
            return _err(jsonify, "RUN_NOT_FOUND", "Run not found.", 404)
        run_dir = cur_case_r / run_id
        meta = _read_metadata(run_dir / "run_metadata.json", run_dir, cur_case_r)
        if meta is None:
            return _err(jsonify, "RUN_NOT_FOUND", "Run not found.", 404)
        resp = jsonify({
            "ok":          True,
            "run_id":      meta["run_id"],
            "case_id":     meta["case_id"],
            "status":      meta["status"],
            "score":       meta["score"],
            "governance":  meta["governance"],
            "artifact_keys": meta["artifact_keys"],
            "created_at":  meta["created_at"],
        })
        resp.headers["Cache-Control"] = "no-store"
        return resp, 200

    # ── GET artifact ───────────────────────────────────────────────────────────

    @bp.route("/runs/<run_id>/artifacts/<artifact_key>", methods=["GET"])
    @require_auth
    def sc_v1_get_artifact(run_id: str, artifact_key: str):
        if not _is_admin(g.user_id):
            return _err(jsonify, "FORBIDDEN", "Admin access required.", 403)
        if not _ENDPOINT_RUN_ID_RE.fullmatch(run_id):
            return _err(jsonify, "ARTIFACT_NOT_FOUND", "Artifact not found.", 404)
        if artifact_key not in _ARTIFACT_FILENAMES:
            return _err(jsonify, "ARTIFACT_NOT_FOUND", "Artifact not found.", 404)
        try:
            cur_case_r = _roots_revalidate()
        except _RootValidationError:
            return _err(jsonify, "ARTIFACT_NOT_FOUND", "Artifact not found.", 404)
        run_dir = cur_case_r / run_id
        # Run must have valid metadata (GET retention race → 404)
        meta = _read_metadata(run_dir / "run_metadata.json", run_dir, cur_case_r)
        if meta is None:
            return _err(jsonify, "ARTIFACT_NOT_FOUND", "Artifact not found.", 404)
        if artifact_key not in meta.get("artifact_keys", []):
            return _err(jsonify, "ARTIFACT_NOT_FOUND", "Artifact not found.", 404)
        subdir, filename = _ARTIFACT_FILENAMES[artifact_key]
        artifact_path = run_dir / subdir / filename
        handle = None
        try:
            handle = _open_validated_regular_file(
                target=artifact_path,
                run_dir=run_dir,
                case_root_r=cur_case_r,
                max_bytes=_ARTIFACT_SIZE_LIMITS[artifact_key],
            )
            response = send_file(
                handle,
                mimetype=_ARTIFACT_MIMETYPES[artifact_key],
                as_attachment=_ARTIFACT_DISPOSITION[artifact_key],
                download_name=filename,
            )
        except _FileValidationError:
            if handle is not None:
                handle.close()
            return _err(jsonify, "ARTIFACT_NOT_FOUND", "Artifact not found.", 404)
        except Exception:
            if handle is not None:
                handle.close()
            return _err(jsonify, "INTERNAL_ERROR", "Internal error.", 500)
        _apply_artifact_headers(response, artifact_key)
        response.call_on_close(handle.close)
        return response

    # ── DELETE run ─────────────────────────────────────────────────────────────

    @bp.route("/runs/<run_id>", methods=["DELETE"])
    @require_auth
    def sc_v1_delete_run(run_id: str):
        if not _is_admin(g.user_id):
            return _err(jsonify, "FORBIDDEN", "Admin access required.", 403)
        if not _ENDPOINT_RUN_ID_RE.fullmatch(run_id):
            return _err(jsonify, "RUN_NOT_FOUND", "Run not found.", 404)
        if not _SEMAPHORE.acquire(blocking=False):
            return _err(jsonify, "CAPACITY_BUSY",
                        "Another operation is in progress.", 503)
        try:
            try:
                cur_case_r = _roots_revalidate()
            except _RootValidationError:
                return _err(jsonify, "RUN_DELETE_REFUSED", "Cannot delete run.", 409)
            run_dir = cur_case_r / run_id
            dr = _safe_delete_run_dir(run_dir, cur_case_r)
            if dr == _DeleteResult.DELETED:
                resp = jsonify({"ok": True, "run_id": run_id, "deleted": True})
                resp.headers["Cache-Control"] = "no-store"
                return resp, 200
            if dr == _DeleteResult.NOT_FOUND:
                return _err(jsonify, "RUN_NOT_FOUND", "Run not found.", 404)
            if dr.value.startswith("REFUSED"):
                return _err(jsonify, "RUN_DELETE_REFUSED", "Cannot delete run.", 409)
            return _err(jsonify, "RUN_DELETE_FAILED", "Internal error.", 500)
        finally:
            _SEMAPHORE.release()

    # ── 10. Register Blueprint ─────────────────────────────────────────────────
    app.register_blueprint(bp, url_prefix="/api/standards-compliance")

    # ── 11. Set idempotency marker after successful registration ───────────────
    app.extensions["standards_compliance_endpoint_registered"] = True
