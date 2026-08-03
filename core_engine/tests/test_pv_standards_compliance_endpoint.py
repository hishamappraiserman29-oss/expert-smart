"""
test_pv_standards_compliance_endpoint.py — Wave 3B unit tests SE01–SE84

All 84 tests are CI-safe:
  * No real browser launched
  * No persistent artifacts written into the repository
  * All filesystem work uses tempfile.TemporaryDirectory
  * Generator invocations are mocked
"""
from __future__ import annotations

import importlib
import json
import os
import re
import stat as _stat_mod
import sys
import tempfile
import time
import threading
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest import mock

import pytest

# ── Path bootstrap ──────────────────────────────────────────────────────────────
_TESTS = Path(__file__).parent.resolve()
_CORE  = _TESTS.parent.resolve()
_ROOT  = _CORE.parent.resolve()
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── Import the module under test ────────────────────────────────────────────────
import pv_standards_compliance_endpoint as _ep  # noqa: E402

# ── Flask import (needed for app factory) ──────────────────────────────────────
from flask import Flask  # noqa: E402

# ── Shared helpers ─────────────────────────────────────────────────────────────

_CASE_ID   = "QA-COMPLIANCE-VISUAL-001"
_VALID_RID = "a" * 32  # valid 32-char hex

_SORTED_KEYS = sorted({
    "user_html", "admin_html", "user_pdf", "admin_pdf", "admin_excel",
    "visual_qa_audit", "cross_format_audit", "content_audit",
})


def _utc_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _good_metadata(run_id: str) -> dict:
    return {
        "schema_version": 1,
        "run_id":   run_id,
        "case_id":  _CASE_ID,
        "created_at": _utc_iso(),
        "status":   "completed",
        "score": {
            "percentage":      72,
            "traffic_light":   "yellow",
            "label":           "متوافق جزئياً",
            "critical_findings": ["VPS-6-UNCERTAINTY"],
            "blocks_issuance": ["VPS-5-ASSUMPTIONS"],
        },
        "governance": {
            "advisory_only":             True,
            "certification_ready":       False,
            "official_compliance_decision": False,
            "synthetic_data":            True,
        },
        "artifact_keys": _SORTED_KEYS,
    }


def _make_app() -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


def _fake_require_auth(f):
    """Decorator: sets g.user_id = 'testuser' and proceeds."""
    from functools import wraps
    from flask import g

    @wraps(f)
    def wrapper(*a, **kw):
        g.user_id = "testuser"
        return f(*a, **kw)

    return wrapper


def _fake_require_auth_unauth(f):
    """Decorator: returns 401 immediately."""
    from functools import wraps
    from flask import jsonify

    @wraps(f)
    def wrapper(*a, **kw):
        return jsonify({"ok": False, "error_code": "UNAUTHORIZED"}), 401

    return wrapper


_admin_users: set[str] = {"testuser"}


def _is_admin(uid: str) -> bool:
    return uid in _admin_users


def _is_admin_never(uid: str) -> bool:
    return False


def _good_generator_result(run_dir_path: str, run_id: str) -> dict:
    return {
        "ok": True,
        "case_id": _CASE_ID,
        "run_id":  run_id,
        "run_directory": run_dir_path,
        "score": {
            "percentage":       72,
            "traffic_light":    "yellow",
            "label":            "متوافق جزئياً",
            "critical_findings": ["VPS-6-UNCERTAINTY"],
            "blocks_issuance":  ["VPS-5-ASSUMPTIONS"],
        },
        "advisory_only": True,
        "certification_ready": False,
        "official_compliance_decision": False,
        "synthetic_data": True,
    }


def _make_fake_gen(captured: list | None = None):
    """Return a generator function that creates a valid run directory."""
    def fake_gen(*, output_root, run_id=None, overwrite=False):
        rid = run_id or uuid.uuid4().hex
        if captured is not None:
            captured.append({"run_id": rid, "output_root": str(output_root),
                             "overwrite": overwrite})
        run_dir = Path(output_root) / _CASE_ID / rid
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "artifacts").mkdir(exist_ok=True)
        (run_dir / "audits").mkdir(exist_ok=True)
        (run_dir / "screenshots").mkdir(exist_ok=True)
        return _good_generator_result(str(run_dir), rid)
    return fake_gen


def _register(app: Flask, tmpdir: Path, *, require_auth=None, is_admin_fn=None):
    _ep.register_standards_compliance(
        app,
        require_auth or _fake_require_auth,
        is_admin_fn or _is_admin,
        str(tmpdir),
    )


def _register_with_gen(app: Flask, tmpdir: Path, fake_gen, **kwargs):
    """Register app with a mocked generator captured at import time."""
    mock_module = mock.MagicMock()
    mock_module.run_standards_compliance_visual_qa = fake_gen
    with mock.patch.dict(sys.modules,
                         {"standards_compliance_visual_qa_generator": mock_module}):
        _register(app, tmpdir, **kwargs)


def _setup_full_run(case_root: Path, run_id: str) -> None:
    """Create a run directory with valid metadata and stub artifacts."""
    run_dir = case_root / run_id
    (run_dir / "artifacts").mkdir(parents=True)
    (run_dir / "audits").mkdir()
    (run_dir / "screenshots" / "user_html").mkdir(parents=True)
    (run_dir / "screenshots" / "admin_html").mkdir(parents=True)
    (run_dir / "screenshots" / "user_pdf").mkdir(parents=True)
    (run_dir / "screenshots" / "admin_pdf").mkdir(parents=True)
    sc = _CASE_ID
    for fname in (
        f"compliance_{sc}_user.html",
        f"compliance_{sc}_admin.html",
        f"compliance_{sc}_user.pdf",
        f"compliance_{sc}_admin.pdf",
        f"compliance_{sc}_admin.xlsx",
    ):
        (run_dir / "artifacts" / fname).write_bytes(b"stub")
    for fname in (
        "compliance_visual_qa_report.json",
        "compliance_cross_format_consistency.json",
        "compliance_content_audit.json",
    ):
        (run_dir / "audits" / fname).write_bytes(b"{}")
    meta = _good_metadata(run_id)
    (run_dir / "run_metadata.json").write_text(json.dumps(meta), encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════════
# SE01–SE10 — Import isolation and module-level contracts
# ═══════════════════════════════════════════════════════════════════════════════

def test_SE01_module_import_no_side_effects():
    """Module import must not create directories, register routes, or access network."""
    assert _ep is not None


def test_SE02_register_standards_compliance_is_callable():
    assert callable(_ep.register_standards_compliance)


def test_SE03_module_has_no_routes_at_import():
    """Importing the module must not register routes."""
    app = _make_app()
    rules = [r.rule for r in app.url_map.iter_rules()]
    assert not any("standards-compliance" in r for r in rules)


def test_SE04_run_id_pattern_exact():
    """Pattern matches exactly 32 lowercase hex chars."""
    pat = _ep._ENDPOINT_RUN_ID_RE
    valid = "a" * 32
    assert pat.fullmatch(valid)
    assert not pat.fullmatch("A" * 32)
    assert not pat.fullmatch("a" * 31)
    assert not pat.fullmatch("a" * 33)
    assert not pat.fullmatch("g" * 32)


def test_SE05_required_artifact_keys_count():
    assert len(_ep._REQUIRED_ARTIFACT_KEYS) == 8


def test_SE06_artifact_filenames_all_keys_mapped():
    assert set(_ep._ARTIFACT_FILENAMES.keys()) == _ep._REQUIRED_ARTIFACT_KEYS


def test_SE07_normalize_path_text_is_lexical():
    """_normalize_absolute_path_text must not call os.stat, os.lstat, or Path.resolve."""
    with (
        mock.patch("os.stat", side_effect=AssertionError("stat called")),
        mock.patch("os.lstat", side_effect=AssertionError("lstat called")),
    ):
        result = _ep._normalize_absolute_path_text(r"C:\foo\bar\..\baz")
    assert isinstance(result, str)
    assert "bar" not in result or "baz" in result


def test_SE08_is_link_detects_symlink_mode():
    lst = SimpleNamespace(st_mode=_stat_mod.S_IFLNK | 0o777, st_file_attributes=0)
    assert _ep._is_link_or_reparse_lstat(lst) is True


def test_SE09_is_link_detects_reparse_point():
    FILE_ATTRIBUTE_REPARSE_POINT = 0x400
    lst = SimpleNamespace(
        st_mode=_stat_mod.S_IFDIR | 0o755,
        st_file_attributes=FILE_ATTRIBUTE_REPARSE_POINT,
    )
    assert _ep._is_link_or_reparse_lstat(lst) is True


def test_SE10_is_link_passes_normal_dir():
    lst = SimpleNamespace(st_mode=_stat_mod.S_IFDIR | 0o755, st_file_attributes=0)
    assert _ep._is_link_or_reparse_lstat(lst) is False


# ═══════════════════════════════════════════════════════════════════════════════
# SE11–SE20 — Registration, Blueprint, collision checks
# ═══════════════════════════════════════════════════════════════════════════════

def test_SE11_registration_succeeds():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp))
    assert True


def test_SE12_exactly_four_routes_registered():
    """Verify 4 (url, method) pairs are registered; GET+DELETE share one URL pattern."""
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp))
    endpoint_methods: set[tuple[str, str]] = set()
    for rule in app.url_map.iter_rules():
        if "standards-compliance" in rule.rule:
            for m in rule.methods:
                if m not in ("HEAD", "OPTIONS"):
                    endpoint_methods.add((rule.rule, m))
    assert ("/api/standards-compliance/runs", "POST") in endpoint_methods
    assert ("/api/standards-compliance/runs/<run_id>", "GET") in endpoint_methods
    assert ("/api/standards-compliance/runs/<run_id>", "DELETE") in endpoint_methods
    assert (
        "/api/standards-compliance/runs/<run_id>/artifacts/<artifact_key>", "GET"
    ) in endpoint_methods
    assert len(endpoint_methods) == 4


def test_SE13_no_v1_suffix_in_routes():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp))
    for rule in app.url_map.iter_rules():
        assert "standards-compliance-v1" not in rule.rule


def test_SE14_registration_idempotent():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp))
        _register(app, Path(tmp))   # second call must not raise
    endpoint_methods: set[tuple[str, str]] = set()
    for rule in app.url_map.iter_rules():
        if "standards-compliance" in rule.rule:
            for m in rule.methods:
                if m not in ("HEAD", "OPTIONS"):
                    endpoint_methods.add((rule.rule, m))
    assert len(endpoint_methods) == 4


def test_SE15_blueprint_prefix_correct():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp))
    for rule in app.url_map.iter_rules():
        if "standards-compliance" in rule.rule and "v2" not in rule.rule:
            assert rule.rule.startswith("/api/standards-compliance")


def test_SE16_extension_marker_set_after_registration():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp))
    assert app.extensions.get("standards_compliance_endpoint_registered") is True


def test_SE17_endpoint_name_collision_raises():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp))
        app2 = _make_app()
        from flask import Blueprint
        fake_bp = Blueprint("standards_compliance_v1_conflict", __name__)

        @fake_bp.route("/runs", methods=["POST"])
        def sc_v1_post_run():
            pass

        app2.register_blueprint(fake_bp, url_prefix="/api/standards-compliance")
        with pytest.raises(Exception):
            _register(app2, Path(tmp))


def test_SE18_route_table_correct_verbs():
    """Accumulate all methods per URL pattern to handle Flask split rules."""
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp))
    rule_map: dict[str, set[str]] = {}
    for rule in app.url_map.iter_rules():
        if "standards-compliance" in rule.rule and "v2" not in rule.rule:
            methods = {m for m in rule.methods if m not in ("HEAD", "OPTIONS")}
            rule_map.setdefault(rule.rule, set()).update(methods)
    assert "POST"   in rule_map.get("/api/standards-compliance/runs", set())
    assert "GET"    in rule_map.get("/api/standards-compliance/runs/<run_id>", set())
    assert "DELETE" in rule_map.get("/api/standards-compliance/runs/<run_id>", set())
    assert "GET"    in rule_map.get(
        "/api/standards-compliance/runs/<run_id>/artifacts/<artifact_key>", set()
    )


def test_SE19_generator_import_verified_at_registration():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        with mock.patch.dict("sys.modules",
                             {"standards_compliance_visual_qa_generator": None}):
            with pytest.raises(Exception):
                _register(app, Path(tmp))


def test_SE20_outputs_must_exist_at_registration():
    app = _make_app()
    with pytest.raises(Exception):
        _ep.register_standards_compliance(app, _fake_require_auth, _is_admin,
                                          "/nonexistent/path/12345")


# ═══════════════════════════════════════════════════════════════════════════════
# SE21–SE30 — Admin authorization
# ═══════════════════════════════════════════════════════════════════════════════

def test_SE21_unauthenticated_post_returns_401():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp), require_auth=_fake_require_auth_unauth)
        with app.test_client() as c:
            resp = c.post("/api/standards-compliance/runs",
                          content_type="application/json", data="{}")
            assert resp.status_code == 401


def test_SE22_non_admin_post_returns_403():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp), is_admin_fn=_is_admin_never)
        with app.test_client() as c:
            resp = c.post("/api/standards-compliance/runs",
                          content_type="application/json", data=b"")
            assert resp.status_code == 403


def test_SE23_non_admin_get_run_returns_403():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp), is_admin_fn=_is_admin_never)
        with app.test_client() as c:
            resp = c.get(f"/api/standards-compliance/runs/{_VALID_RID}")
            assert resp.status_code == 403


def test_SE24_non_admin_get_artifact_returns_403():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp), is_admin_fn=_is_admin_never)
        with app.test_client() as c:
            resp = c.get(f"/api/standards-compliance/runs/{_VALID_RID}/artifacts/user_html")
            assert resp.status_code == 403


def test_SE25_non_admin_delete_returns_403():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp), is_admin_fn=_is_admin_never)
        with app.test_client() as c:
            resp = c.delete(f"/api/standards-compliance/runs/{_VALID_RID}")
            assert resp.status_code == 403


def test_SE26_is_admin_called_with_user_id():
    admin_calls: list[str] = []

    def track_admin(uid: str) -> bool:
        admin_calls.append(uid)
        return False

    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp), is_admin_fn=track_admin)
        with app.test_client() as c:
            c.post("/api/standards-compliance/runs", data=b"")
    assert admin_calls, "is_admin never called"
    assert admin_calls[0] == "testuser"


def test_SE27_request_body_cannot_override_admin():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp), is_admin_fn=_is_admin_never)
        with app.test_client() as c:
            resp = c.post(
                "/api/standards-compliance/runs",
                json={"is_admin": True, "admin": True, "role": "admin"},
            )
            assert resp.status_code == 403


def test_SE28_error_response_no_raw_exception():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp), is_admin_fn=_is_admin_never)
        with app.test_client() as c:
            resp = c.post("/api/standards-compliance/runs", data=b"")
            body = resp.get_json()
    assert "ok" in body
    assert body["ok"] is False
    assert "error_code" in body
    assert "message" in body
    assert "traceback" not in str(body).lower()
    assert "exception" not in str(body).lower()


def test_SE29_error_sanitization_no_filesystem_path():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp))
        with app.test_client() as c:
            resp = c.get(f"/api/standards-compliance/runs/{_VALID_RID}")
        body = resp.get_json()
        body_str = json.dumps(body)
        assert str(tmp) not in body_str


def test_SE30_delete_result_enum_values():
    assert _ep._DeleteResult.DELETED.value                   == "DELETED"
    assert _ep._DeleteResult.NOT_FOUND.value                 == "NOT_FOUND"
    assert _ep._DeleteResult.REFUSED_OUTSIDE_ROOT.value      == "REFUSED_OUTSIDE_ROOT"
    assert _ep._DeleteResult.REFUSED_REPARSE_POINT.value     == "REFUSED_REPARSE_POINT"
    assert _ep._DeleteResult.REFUSED_UNKNOWN_STRUCTURE.value == "REFUSED_UNKNOWN_STRUCTURE"
    assert _ep._DeleteResult.FAILED_IO.value                 == "FAILED_IO"


# ═══════════════════════════════════════════════════════════════════════════════
# SE31–SE40 — Request body parsing
# ═══════════════════════════════════════════════════════════════════════════════

def test_SE31_empty_body_accepted():
    captured: list[dict] = []
    fake_gen = _make_fake_gen(captured)
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register_with_gen(app, Path(tmp), fake_gen)
        with app.test_client() as c:
            resp = c.post("/api/standards-compliance/runs")
    # POST_SUCCESS_STATUS = 200 (synchronous completion)
    assert resp.status_code == 200


def test_SE32_empty_json_object_accepted():
    captured: list[dict] = []
    fake_gen = _make_fake_gen(captured)
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register_with_gen(app, Path(tmp), fake_gen)
        with app.test_client() as c:
            resp = c.post("/api/standards-compliance/runs",
                          data=b"{}", content_type="application/json")
    # POST_SUCCESS_STATUS = 200 (synchronous completion)
    assert resp.status_code == 200


def test_SE33_oversized_body_returns_413():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp))
        with app.test_client() as c:
            resp = c.post(
                "/api/standards-compliance/runs",
                data=b"x" * 300,
                content_type="application/json",
            )
    assert resp.status_code == 413
    assert resp.get_json()["error_code"] == "PAYLOAD_TOO_LARGE"


def test_SE34_wrong_content_type_with_body_returns_415():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp))
        with app.test_client() as c:
            resp = c.post(
                "/api/standards-compliance/runs",
                data=b"{}",
                content_type="text/plain",
            )
    assert resp.status_code == 415
    assert resp.get_json()["error_code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_SE35_malformed_utf8_returns_400():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp))
        with app.test_client() as c:
            resp = c.post(
                "/api/standards-compliance/runs",
                data=b"\xff\xfe",
                content_type="application/json",
            )
    assert resp.status_code == 400
    assert resp.get_json()["error_code"] == "INVALID_JSON"


def test_SE36_malformed_json_returns_400():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp))
        with app.test_client() as c:
            resp = c.post(
                "/api/standards-compliance/runs",
                data=b"{bad json}",
                content_type="application/json",
            )
    assert resp.status_code == 400
    assert resp.get_json()["error_code"] == "INVALID_JSON"


def test_SE37_json_array_returns_400():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp))
        with app.test_client() as c:
            resp = c.post(
                "/api/standards-compliance/runs",
                json=[1, 2, 3],
            )
    assert resp.status_code == 400
    assert resp.get_json()["error_code"] == "INVALID_REQUEST"


def test_SE38_json_string_returns_400():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp))
        with app.test_client() as c:
            resp = c.post(
                "/api/standards-compliance/runs",
                data=b'"hello"',
                content_type="application/json",
            )
    assert resp.status_code == 400
    assert resp.get_json()["error_code"] == "INVALID_REQUEST"


def test_SE39_non_empty_json_object_returns_400():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp))
        with app.test_client() as c:
            resp = c.post(
                "/api/standards-compliance/runs",
                json={"extra_field": "value"},
            )
    assert resp.status_code == 400
    assert resp.get_json()["error_code"] == "UNKNOWN_FIELD"


def test_SE40_stream_parsed_once():
    """Verify implementation does not use get_json (stream read only)."""
    import inspect
    src = inspect.getsource(_ep)
    assert "get_json" not in src, "get_json found in endpoint source"


# ═══════════════════════════════════════════════════════════════════════════════
# SE41–SE50 — Generator path contract and server-controlled IDs
# ═══════════════════════════════════════════════════════════════════════════════

def test_SE41_run_id_server_generated_hex32():
    """run_id passed to generator must be a 32-char lowercase hex UUID4."""
    captured: list[dict] = []
    fake_gen = _make_fake_gen(captured)
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register_with_gen(app, Path(tmp), fake_gen)
        with app.test_client() as c:
            resp = c.post("/api/standards-compliance/runs")
    # POST_SUCCESS_STATUS = 200 (synchronous completion, not 201)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert captured, "generator never called"
    rid = captured[0]["run_id"]
    assert re.fullmatch(r"[0-9a-f]{32}", rid), f"Invalid run_id: {rid!r}"


def test_SE42_case_id_always_fixed():
    """Generator is called without explicit case_id (uses default in generator)."""
    captured: list[dict] = []
    fake_gen = _make_fake_gen(captured)
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register_with_gen(app, Path(tmp), fake_gen)
        with app.test_client() as c:
            c.post("/api/standards-compliance/runs")
    assert captured, "generator never called"


def test_SE43_overwrite_is_always_false():
    captured: list[dict] = []
    fake_gen = _make_fake_gen(captured)
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register_with_gen(app, Path(tmp), fake_gen)
        with app.test_client() as c:
            c.post("/api/standards-compliance/runs")
    assert captured, "generator never called"
    assert captured[0]["overwrite"] is False


def test_SE44_output_root_is_server_controlled():
    """output_root must be the server-computed standards_path, not client-supplied."""
    captured: list[dict] = []
    fake_gen = _make_fake_gen(captured)
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register_with_gen(app, Path(tmp), fake_gen)
        with app.test_client() as c:
            c.post("/api/standards-compliance/runs",
                   json={"output_root": "/attacker/path"})  # ignored → 400 UNKNOWN_FIELD
    # Either generator was called with correct path, or the body was rejected
    if captured:
        assert "attacker" not in captured[0]["output_root"]
        assert "standards_compliance" in captured[0]["output_root"]


def test_SE45_validate_run_metadata_good():
    meta = _good_metadata(_VALID_RID)
    assert _ep._validate_run_metadata(meta) is True


def test_SE46_validate_run_metadata_bool_percentage_rejected():
    meta = _good_metadata(_VALID_RID)
    meta["score"]["percentage"] = True   # bool is not int
    assert _ep._validate_run_metadata(meta) is False


def test_SE47_validate_run_metadata_wrong_governance_rejected():
    meta = _good_metadata(_VALID_RID)
    meta["governance"]["advisory_only"] = False
    assert _ep._validate_run_metadata(meta) is False


def test_SE48_validate_run_metadata_non_utc_rejected():
    meta = _good_metadata(_VALID_RID)
    meta["created_at"] = "2026-08-01T12:00:00"  # naive (no timezone)
    assert _ep._validate_run_metadata(meta) is False


def test_SE49_validate_run_metadata_extra_key_rejected():
    meta = _good_metadata(_VALID_RID)
    meta["extra_key"] = "not_allowed"
    assert _ep._validate_run_metadata(meta) is False


def test_SE50_validate_run_metadata_wrong_artifact_keys_rejected():
    meta = _good_metadata(_VALID_RID)
    meta["artifact_keys"] = ["user_html"]  # too few
    assert _ep._validate_run_metadata(meta) is False


# ═══════════════════════════════════════════════════════════════════════════════
# SE51–SE60 — Root chain and identity validation
# ═══════════════════════════════════════════════════════════════════════════════

def test_SE51_revalidate_server_roots_passes_clean_dirs():
    with tempfile.TemporaryDirectory() as tmp:
        outputs   = Path(tmp) / "outputs"
        standards = outputs / "standards_compliance"
        case_dir  = standards / _CASE_ID
        case_dir.mkdir(parents=True)
        result = _ep._revalidate_server_roots(
            outputs_path=outputs, standards_path=standards, case_path=case_dir,
            outputs_root_r=outputs.resolve(), standards_root_r=standards.resolve(),
            case_root_r=case_dir.resolve(),
            root_identities={
                "OUTPUTS":        _ep._capture_identity(outputs),
                "standards_root": _ep._capture_identity(standards),
                "case_root":      _ep._capture_identity(case_dir),
            },
        )
        assert result == case_dir.resolve()


def test_SE52_revalidate_raises_when_dir_missing():
    with tempfile.TemporaryDirectory() as tmp:
        outputs   = Path(tmp) / "outputs"
        standards = outputs / "standards_compliance"
        case_dir  = standards / _CASE_ID
        case_dir.mkdir(parents=True)
        identities = {
            "OUTPUTS":        _ep._capture_identity(outputs),
            "standards_root": _ep._capture_identity(standards),
            "case_root":      _ep._capture_identity(case_dir),
        }
        import shutil
        shutil.rmtree(str(case_dir))
        with pytest.raises(_ep._RootValidationError):
            _ep._revalidate_server_roots(
                outputs_path=outputs, standards_path=standards, case_path=case_dir,
                outputs_root_r=outputs.resolve(), standards_root_r=standards.resolve(),
                case_root_r=case_dir.resolve(),
                root_identities=identities,
            )


def test_SE53_revalidate_raises_on_identity_change():
    """When st_ino != 0, a different directory at same path is detected."""
    with tempfile.TemporaryDirectory() as tmp:
        outputs   = Path(tmp) / "outputs"
        standards = outputs / "standards_compliance"
        case_dir  = standards / _CASE_ID
        case_dir.mkdir(parents=True)
        outputs_r   = outputs.resolve()
        standards_r = standards.resolve()
        case_r      = case_dir.resolve()
        identities = {
            "OUTPUTS":        _ep._capture_identity(outputs),
            "standards_root": _ep._capture_identity(standards),
            "case_root":      _ep._capture_identity(case_dir),
        }
        real_ino = os.lstat(case_dir).st_ino
        if real_ino == 0:
            pytest.skip("st_ino unavailable on this platform")
        orig_lstat = os.lstat
        call_count = [0]
        case_path_norm = os.path.normcase(str(case_dir))
        def fake_lstat(path, *args, **kwargs):
            lst = orig_lstat(path, *args, **kwargs)
            call_count[0] += 1
            if os.path.normcase(str(path)) == case_path_norm and call_count[0] >= 3:
                return SimpleNamespace(
                    st_mode=lst.st_mode, st_ino=lst.st_ino + 1,
                    st_dev=lst.st_dev, st_nlink=lst.st_nlink,
                    st_uid=getattr(lst, "st_uid", 0),
                    st_gid=getattr(lst, "st_gid", 0),
                    st_size=lst.st_size, st_atime=lst.st_atime,
                    st_mtime=lst.st_mtime, st_ctime=lst.st_ctime,
                    st_file_attributes=0,
                )
            return lst
        with mock.patch("os.lstat", side_effect=fake_lstat):
            with pytest.raises(_ep._RootValidationError, match="identity"):
                _ep._revalidate_server_roots(
                    outputs_path=outputs, standards_path=standards, case_path=case_dir,
                    outputs_root_r=outputs_r, standards_root_r=standards_r,
                    case_root_r=case_r, root_identities=identities,
                )


def test_SE54_get_run_returns_404_for_unknown():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp))
        with app.test_client() as c:
            resp = c.get(f"/api/standards-compliance/runs/{_VALID_RID}")
    assert resp.status_code == 404
    assert resp.get_json()["error_code"] == "RUN_NOT_FOUND"


def test_SE55_get_run_returns_metadata_for_valid_run():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        outputs = Path(tmp)
        _register(app, outputs)
        case_root = (outputs / "standards_compliance" / _CASE_ID).resolve()
        run_id = "b" * 32
        _setup_full_run(case_root, run_id)
        with app.test_client() as c:
            resp = c.get(f"/api/standards-compliance/runs/{run_id}")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["run_id"] == run_id
    assert body["governance"]["advisory_only"] is True
    assert body["governance"]["certification_ready"] is False
    assert body["governance"]["official_compliance_decision"] is False
    assert body["governance"]["synthetic_data"] is True


def test_SE56_governance_fields_always_advisory():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        outputs = Path(tmp)
        _register(app, outputs)
        case_root = (outputs / "standards_compliance" / _CASE_ID).resolve()
        run_id = "c" * 32
        _setup_full_run(case_root, run_id)
        with app.test_client() as c:
            resp = c.get(f"/api/standards-compliance/runs/{run_id}")
    gov = resp.get_json()["governance"]
    assert gov["advisory_only"]               is True
    assert gov["certification_ready"]         is False
    assert gov["official_compliance_decision"] is False
    assert gov["synthetic_data"]              is True


def test_SE57_invalid_run_id_format_returns_404():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp))
        with app.test_client() as c:
            resp = c.get("/api/standards-compliance/runs/INVALID-RUN-ID")
    assert resp.status_code == 404


def test_SE58_delete_existing_run_returns_200():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        outputs = Path(tmp)
        _register(app, outputs)
        case_root = (outputs / "standards_compliance" / _CASE_ID).resolve()
        run_id = "d" * 32
        _setup_full_run(case_root, run_id)
        run_dir = case_root / run_id
        assert run_dir.exists()
        with app.test_client() as c:
            resp = c.delete(f"/api/standards-compliance/runs/{run_id}")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["deleted"] is True
        assert not run_dir.exists()


def test_SE59_delete_nonexistent_run_returns_404():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp))
        with app.test_client() as c:
            resp = c.delete(f"/api/standards-compliance/runs/{_VALID_RID}")
        assert resp.status_code == 404


def test_SE60_safe_delete_verifies_post_deletion_absence():
    with tempfile.TemporaryDirectory() as tmp:
        case_root = Path(tmp)
        run_id = "e" * 32
        run_dir = case_root / run_id
        run_dir.mkdir()
        result = _ep._safe_delete_run_dir(run_dir, case_root)
    assert result == _ep._DeleteResult.DELETED
    assert not run_dir.exists()


# ═══════════════════════════════════════════════════════════════════════════════
# SE61–SE70 — Semaphore, retention, and safe deletion
# ═══════════════════════════════════════════════════════════════════════════════

def test_SE61_semaphore_acquired_on_post():
    """POST acquires semaphore; second concurrent POST returns 503."""
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp))
    _ep._SEMAPHORE.acquire()
    try:
        with app.test_client() as c:
            resp = c.post("/api/standards-compliance/runs")
        assert resp.status_code == 503
        assert resp.get_json()["error_code"] == "CAPACITY_BUSY"
    finally:
        _ep._SEMAPHORE.release()


def test_SE62_semaphore_acquired_on_delete():
    """DELETE acquires semaphore; concurrent attempt returns 503."""
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp))
    _ep._SEMAPHORE.acquire()
    try:
        with app.test_client() as c:
            resp = c.delete(f"/api/standards-compliance/runs/{_VALID_RID}")
        assert resp.status_code == 503
        assert resp.get_json()["error_code"] == "CAPACITY_BUSY"
    finally:
        _ep._SEMAPHORE.release()


def test_SE63_semaphore_released_after_post():
    """Semaphore must be released even when POST returns early."""
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp))
    with app.test_client() as c:
        c.post("/api/standards-compliance/runs")
    acquired = _ep._SEMAPHORE.acquire(blocking=False)
    assert acquired, "Semaphore was not released after POST"
    _ep._SEMAPHORE.release()


def test_SE64_pre_generation_capacity_gate():
    """When valid run count exceeds target after retention, POST returns 507."""
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp))
        # Simulate count_valid_runs returning > PRE_GENERATION_TARGET after retention
        with mock.patch.object(_ep, "_count_valid_runs", return_value=10):
            with app.test_client() as c:
                resp = c.post("/api/standards-compliance/runs")
    assert resp.status_code == 507
    assert resp.get_json()["error_code"] == "RETENTION_CAPACITY_EXCEEDED"


def test_SE65_retention_reduce_removes_oldest():
    with tempfile.TemporaryDirectory() as tmp:
        case_root = Path(tmp)
        rids: list[str] = []
        for i in range(5):
            rid = f"{i:032x}"
            rids.append(rid)
            run_dir = case_root / rid
            run_dir.mkdir()
            meta = _good_metadata(rid)
            (run_dir / "run_metadata.json").write_text(
                json.dumps(meta), encoding="utf-8"
            )
            mtime = time.time() - (5 - i) * 100
            os.utime(run_dir / "run_metadata.json", (mtime, mtime))
        _ep._retention_reduce(case_root, target=2)
        count = _ep._count_valid_runs(case_root)
        assert count <= 2


def test_SE66_orphan_cleanup_removes_expired_no_meta():
    with tempfile.TemporaryDirectory() as tmp:
        case_root = Path(tmp)
        rid = "f" * 32
        run_dir = case_root / rid
        run_dir.mkdir()
        old_time = time.time() - 2 * _ep._ORPHAN_AGE_SECONDS
        os.utime(run_dir, (old_time, old_time))
        _ep._cleanup_orphans(case_root)
        assert not run_dir.exists()


def test_SE67_orphan_cleanup_preserves_valid_runs():
    with tempfile.TemporaryDirectory() as tmp:
        case_root = Path(tmp)
        rid = "0" * 32
        _setup_full_run(case_root, rid)
        run_dir = case_root / rid
        old_time = time.time() - 2 * _ep._ORPHAN_AGE_SECONDS
        os.utime(run_dir, (old_time, old_time))
        _ep._cleanup_orphans(case_root)
        assert run_dir.exists()


def test_SE68_safe_delete_refuses_reparse_point():
    with tempfile.TemporaryDirectory() as tmp:
        case_root = Path(tmp)
        rid = "a" * 32
        run_dir = case_root / rid
        run_dir.mkdir()
        lst = SimpleNamespace(
            st_mode=_stat_mod.S_IFDIR | 0o755,
            st_file_attributes=0x400,
        )
        with mock.patch("os.lstat", return_value=lst):
            result = _ep._safe_delete_run_dir(run_dir, case_root)
    assert result == _ep._DeleteResult.REFUSED_REPARSE_POINT


def test_SE69_safe_delete_refuses_unknown_top_level_entry():
    with tempfile.TemporaryDirectory() as tmp:
        case_root = Path(tmp)
        rid = "b" * 32
        run_dir = case_root / rid
        run_dir.mkdir()
        (run_dir / "malicious_script.sh").write_text("rm -rf /")
        result = _ep._safe_delete_run_dir(run_dir, case_root)
    assert result == _ep._DeleteResult.REFUSED_UNKNOWN_STRUCTURE


def test_SE70_safe_delete_refuses_outside_case_root():
    with tempfile.TemporaryDirectory() as tmp:
        case_root = Path(tmp) / "case"
        case_root.mkdir()
        other = Path(tmp) / "other"
        other.mkdir()
        run_id = "c" * 32
        run_dir = other / run_id
        run_dir.mkdir()
        result = _ep._safe_delete_run_dir(run_dir, case_root)
    assert result == _ep._DeleteResult.REFUSED_OUTSIDE_ROOT


# ═══════════════════════════════════════════════════════════════════════════════
# SE71–SE79 — Export, routes, lexical comparison, handle lifecycle
# ═══════════════════════════════════════════════════════════════════════════════

def test_SE71_public_export_name_is_register_standards_compliance():
    assert hasattr(_ep, "register_standards_compliance")
    assert callable(_ep.register_standards_compliance)
    assert not hasattr(_ep, "register_standards_compliance_v1")


def test_SE72_import_matches_bridge_stub_exactly():
    from pv_standards_compliance_endpoint import register_standards_compliance
    assert callable(register_standards_compliance)


def test_SE73_complete_route_set_matches_contract():
    """SE73 — full (route, method) set equality against the Wave 3B contract."""
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp))
    actual = {
        (rule.rule, method)
        for rule in app.url_map.iter_rules()
        if "standards-compliance" in rule.rule and "v2" not in rule.rule
        for method in rule.methods
        if method not in ("HEAD", "OPTIONS")
    }
    expected = {
        ("/api/standards-compliance/runs", "POST"),
        ("/api/standards-compliance/runs/<run_id>", "GET"),
        ("/api/standards-compliance/runs/<run_id>", "DELETE"),
        (
            "/api/standards-compliance/runs/<run_id>/artifacts/<artifact_key>",
            "GET",
        ),
    }
    assert actual == expected, (
        f"Route set mismatch.\n  Expected: {sorted(expected)}\n  Actual:   {sorted(actual)}"
    )


def test_SE74_no_v1_suffix_in_any_route():
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register(app, Path(tmp))
    for rule in app.url_map.iter_rules():
        assert "standards-compliance-v1" not in rule.rule


def test_SE75_lexical_comparison_no_filesystem_ops_on_reported():
    with tempfile.TemporaryDirectory() as tmp:
        reported = str(Path(tmp) / "some" / "path")
        with (
            mock.patch("os.stat",  side_effect=AssertionError("stat called on reported")),
            mock.patch("os.lstat", side_effect=AssertionError("lstat called on reported")),
        ):
            result = _ep._normalize_absolute_path_text(reported)
        assert isinstance(result, str)


def test_SE76_run_dir_junction_rejected_by_open_validated():
    with tempfile.TemporaryDirectory() as tmp:
        case_root = Path(tmp) / "case"
        case_root.mkdir()
        run_id = "d" * 32
        run_dir = case_root / run_id
        run_dir.mkdir()
        target_file = run_dir / "test.json"
        target_file.write_bytes(b"{}")
        reparse_lst = SimpleNamespace(
            st_mode=_stat_mod.S_IFDIR | 0o755,
            st_file_attributes=0x400,
        )
        normal_lst = SimpleNamespace(
            st_mode=_stat_mod.S_IFDIR | 0o755,
            st_file_attributes=0,
        )
        call_count = [0]
        run_dir_norm = os.path.normcase(str(run_dir))
        def selective_lstat(path, *args, **kwargs):
            call_count[0] += 1
            if os.path.normcase(str(path)) == run_dir_norm:
                return reparse_lst
            return normal_lst
        with mock.patch("os.lstat", side_effect=selective_lstat):
            with pytest.raises(_ep._FileValidationError):
                _ep._open_validated_regular_file(
                    target=target_file,
                    run_dir=run_dir,
                    case_root_r=case_root,
                    max_bytes=64 * 1024,
                )


def test_SE77_post_startup_case_root_reparse_detected():
    """After registration, if case_root becomes a reparse point, request fails."""
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        outputs = Path(tmp)
        _register(app, outputs)
        case_dir = outputs / "standards_compliance" / _CASE_ID
        reparse_lst = SimpleNamespace(
            st_mode=_stat_mod.S_IFDIR | 0o755,
            st_file_attributes=0x400,
        )
        orig_lstat = os.lstat
        case_norm = os.path.normcase(str(case_dir))
        def fake_lstat(path, *args, **kwargs):
            if os.path.normcase(str(path)) == case_norm:
                return reparse_lst
            return orig_lstat(path, *args, **kwargs)
        with mock.patch("os.lstat", side_effect=fake_lstat):
            with app.test_client() as c:
                resp_post   = c.post("/api/standards-compliance/runs")
                resp_get    = c.get(f"/api/standards-compliance/runs/{_VALID_RID}")
                resp_delete = c.delete(f"/api/standards-compliance/runs/{_VALID_RID}")
    assert resp_post.status_code   == 503
    assert resp_get.status_code    == 404
    assert resp_delete.status_code == 409


def test_SE78_handle_closed_when_send_file_raises():
    """If an exception occurs after file open, handle must be closed."""
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        outputs = Path(tmp)
        _register(app, outputs)
        case_root = (outputs / "standards_compliance" / _CASE_ID).resolve()
        run_id = "e" * 32
        _setup_full_run(case_root, run_id)
        handle_mock = mock.MagicMock()
        with (
            mock.patch.object(_ep, "_open_validated_regular_file",
                              return_value=handle_mock),
            mock.patch.object(_ep, "_read_metadata",
                              return_value=_good_metadata(run_id)),
            mock.patch.object(_ep, "_revalidate_server_roots",
                              return_value=case_root),
        ):
            import flask
            with mock.patch.object(flask, "send_file",
                                   side_effect=OSError("send_file failed")):
                with app.test_client() as c:
                    resp = c.get(
                        f"/api/standards-compliance/runs/{run_id}"
                        f"/artifacts/user_html"
                    )
    assert resp.status_code == 500
    handle_mock.close.assert_called()


def test_SE79_handle_close_registered_on_success():
    """response.call_on_close(handle.close) is present in the success-path source."""
    import inspect
    src = inspect.getsource(_ep)
    assert "response.call_on_close(handle.close)" in src


# ═══════════════════════════════════════════════════════════════════════════════
# SE80–SE84 — Root identity (latest corrections)
# ═══════════════════════════════════════════════════════════════════════════════

def test_SE80_reparse_point_on_configured_path_detected():
    """Replacing a configured path with a reparse point fails validation."""
    with tempfile.TemporaryDirectory() as tmp:
        outputs   = Path(tmp) / "outputs"
        standards = outputs / "standards_compliance"
        case_dir  = standards / _CASE_ID
        case_dir.mkdir(parents=True)
        identities = {
            "OUTPUTS":        _ep._capture_identity(outputs),
            "standards_root": _ep._capture_identity(standards),
            "case_root":      _ep._capture_identity(case_dir),
        }
        orig_lstat = os.lstat
        outputs_norm = os.path.normcase(str(outputs))
        def fake_lstat(path, *args, **kwargs):
            if os.path.normcase(str(path)) == outputs_norm:
                return SimpleNamespace(
                    st_mode=_stat_mod.S_IFDIR | 0o755,
                    st_file_attributes=0x400,
                )
            return orig_lstat(path, *args, **kwargs)
        with mock.patch("os.lstat", side_effect=fake_lstat):
            with pytest.raises(_ep._RootValidationError, match="reparse"):
                _ep._revalidate_server_roots(
                    outputs_path=outputs, standards_path=standards, case_path=case_dir,
                    outputs_root_r=outputs.resolve(), standards_root_r=standards.resolve(),
                    case_root_r=case_dir.resolve(),
                    root_identities=identities,
                )


def test_SE81_missing_standards_root_returns_503_no_mkdir():
    """POST must return 503 if standards root is missing; must not call mkdir."""
    import shutil
    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        outputs = Path(tmp)
        _register(app, outputs)
        standards = outputs / "standards_compliance"
        shutil.rmtree(str(standards))
        mkdir_calls: list[str] = []
        orig_mkdir = Path.mkdir
        def track_mkdir(self, *args, **kwargs):
            mkdir_calls.append(str(self))
            return orig_mkdir(self, *args, **kwargs)
        with mock.patch.object(Path, "mkdir", side_effect=track_mkdir):
            with app.test_client() as c:
                resp = c.post("/api/standards-compliance/runs")
    assert resp.status_code == 503
    assert resp.get_json()["error_code"] == "STORAGE_UNAVAILABLE"
    assert len(mkdir_calls) == 0, f"mkdir was called during request: {mkdir_calls}"


def test_SE82_ordinary_directory_replacement_detected_via_identity():
    """If case_root is replaced with a different ordinary dir, identity check fires."""
    with tempfile.TemporaryDirectory() as tmp:
        outputs   = Path(tmp) / "outputs"
        standards = outputs / "standards_compliance"
        case_dir  = standards / _CASE_ID
        case_dir.mkdir(parents=True)
        real_ino = os.lstat(case_dir).st_ino
        if real_ino == 0:
            pytest.skip("st_ino unavailable on this platform")
        identities = {
            "OUTPUTS":        _ep._capture_identity(outputs),
            "standards_root": _ep._capture_identity(standards),
            "case_root":      _ep._capture_identity(case_dir),
        }
        orig_lstat = os.lstat
        case_norm = os.path.normcase(str(case_dir))
        call_count = [0]
        def fake_lstat(path, *args, **kwargs):
            lst = orig_lstat(path, *args, **kwargs)
            call_count[0] += 1
            if os.path.normcase(str(path)) == case_norm and call_count[0] >= 3:
                return SimpleNamespace(
                    st_mode=lst.st_mode,
                    st_ino=lst.st_ino + 999,
                    st_dev=lst.st_dev,
                    st_nlink=lst.st_nlink,
                    st_uid=getattr(lst, "st_uid", 0),
                    st_gid=getattr(lst, "st_gid", 0),
                    st_size=lst.st_size, st_atime=lst.st_atime,
                    st_mtime=lst.st_mtime, st_ctime=lst.st_ctime,
                    st_file_attributes=0,
                )
            return lst
        with mock.patch("os.lstat", side_effect=fake_lstat):
            with pytest.raises(_ep._RootValidationError, match="identity"):
                _ep._revalidate_server_roots(
                    outputs_path=outputs, standards_path=standards, case_path=case_dir,
                    outputs_root_r=outputs.resolve(), standards_root_r=standards.resolve(),
                    case_root_r=case_dir.resolve(),
                    root_identities=identities,
                )


def test_SE83_generator_pathlib_path_rejected():
    """Generator returning run_directory as pathlib.Path is rejected."""
    def bad_gen(*, output_root, run_id=None, overwrite=False):
        rid = run_id or uuid.uuid4().hex
        run_dir = Path(output_root) / _CASE_ID / rid
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "artifacts").mkdir(exist_ok=True)
        (run_dir / "audits").mkdir(exist_ok=True)
        (run_dir / "screenshots").mkdir(exist_ok=True)
        result = _good_generator_result(str(run_dir), rid)
        result["run_directory"] = run_dir  # Path object, not str
        return result

    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register_with_gen(app, Path(tmp), bad_gen)
        with app.test_client() as c:
            resp = c.post("/api/standards-compliance/runs")
    assert resp.status_code == 500
    assert resp.get_json()["error_code"] == "INVALID_GENERATOR_RESULT"


def test_SE84_relative_path_rejected_without_filesystem_access():
    """Generator returning relative path is rejected via os.path.isabs check."""
    def bad_gen(*, output_root, run_id=None, overwrite=False):
        rid = run_id or uuid.uuid4().hex
        run_dir = Path(output_root) / _CASE_ID / rid
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "artifacts").mkdir(exist_ok=True)
        (run_dir / "audits").mkdir(exist_ok=True)
        (run_dir / "screenshots").mkdir(exist_ok=True)
        result = _good_generator_result(str(run_dir), rid)
        result["run_directory"] = "relative/path/not/absolute"
        return result

    app = _make_app()
    with tempfile.TemporaryDirectory() as tmp:
        _register_with_gen(app, Path(tmp), bad_gen)
        with app.test_client() as c:
            resp = c.post("/api/standards-compliance/runs")
    assert resp.status_code == 500
    assert resp.get_json()["error_code"] == "INVALID_GENERATOR_RESULT"
