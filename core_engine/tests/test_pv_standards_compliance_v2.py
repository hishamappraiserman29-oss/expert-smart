"""
Standards Compliance v2 — test suite
217 tests: SC2-01..SC2-28 (retained) + SV01..SV153 (V2 security governance)
         + RET-BOUND-1..4 + RET-SKIP-1 (retention boundary)
         + DEL-BOUND-1..4 + UNKNOWN-1..7 (deletion boundary, Generator-derived allowlist)
         + SS-BOUND-1..12 (screenshot filename boundary, Generator-contract regex)
           HTML: section_01-15 + full (max 16); PDF: page_01-76 (cap _PDF_SCREENSHOT_CAP=76)
         + PARTIAL-1..8 (partial-run rollback safety)
Run: python -m pytest tests/test_pv_standards_compliance_v2.py -q
"""
from __future__ import annotations

import contextlib
import inspect
import json
import pathlib
import sys
import tempfile
import threading
import unittest.mock as mock
import uuid

_CORE = pathlib.Path(__file__).resolve().parents[1]
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

_OUT  = _CORE / "outputs" / "visual_qa_standards_compliance_v2"
_ARTS = _OUT / "artifacts"
_SS   = _OUT / "screenshots"
_AUD  = _OUT / "audits"
_CID  = "QA-COMPLIANCE-VISUAL-001"

_VALID_STATUS = {
    "compliant", "partially_compliant", "non_compliant",
    "not_applicable", "insufficient_evidence", "not_assessed",
}
_VALID_SEV = {"critical", "high", "medium", "low", "informational", "not_applicable"}

import pv_standards_compliance_v2_endpoint as _ep2  # noqa: E402
_V2_GEN_MOD = "standards_compliance_v2_generator"


# ── SC2 legacy helpers ─────────────────────────────────────────────────────────

def _read_audit(name: str) -> dict:
    p = _AUD / name
    assert p.exists(), f"Audit file missing: {name}"
    return json.loads(p.read_text(encoding="utf-8"))


def _user_html() -> str:
    return (_ARTS / f"compliance_v2_{_CID}_user.html").read_text(encoding="utf-8")


def _admin_html() -> str:
    return (_ARTS / f"compliance_v2_{_CID}_admin.html").read_text(encoding="utf-8")


# ── SV helpers ─────────────────────────────────────────────────────────────────

_FAKE_SCORE: dict = {
    "overall_pass": True, "score_pct": 78, "traffic_light": "yellow",
    "cross_format_pass": True, "mismatches": [], "user_pdf_pages": 4,
    "admin_pdf_pages": 6, "excel_sheets": 32, "ml_ready": False,
}

_EXPECTED_ARTIFACT_KEYS = sorted([
    "user_html", "admin_html", "user_pdf", "admin_pdf",
    "admin_xlsx", "audit_report", "audit_cross", "audit_content",
])

_EXPECTED_GOVERNANCE_KEYS = {
    "advisory_only", "certification_ready", "fake_signature_created",
    "ml_suggestion_only", "ml_trained_on_approved_only",
    "ml_auto_decision", "synthetic_data",
}

_EXPECTED_METADATA_TOP_KEYS = {
    "schema_version", "run_id", "case_id", "created_at",
    "status", "score", "governance", "artifact_keys",
}


def _default_fake_gen():
    def _run(*, output_root, run_id, case_id=_CID, overwrite=False):
        run_dir = pathlib.Path(output_root) / run_id
        if run_dir.exists() and not overwrite:
            raise FileExistsError(f"Run directory already exists: {run_dir}")
        arts = run_dir / "artifacts"
        aud  = run_dir / "audits"
        arts.mkdir(parents=True, exist_ok=True)
        aud.mkdir(parents=True, exist_ok=True)
        (arts / f"compliance_v2_{case_id}_user.html").write_bytes(b"<html>user</html>")
        (arts / f"compliance_v2_{case_id}_admin.html").write_bytes(b"<html>admin</html>")
        (arts / f"compliance_v2_{case_id}_user.pdf").write_bytes(b"%PDF-1.4 fake user")
        (arts / f"compliance_v2_{case_id}_admin.pdf").write_bytes(b"%PDF-1.4 fake admin")
        (arts / f"compliance_v2_{case_id}_admin.xlsx").write_bytes(b"PK\x03\x04fake xlsx content")
        (aud / "compliance_v2_visual_qa_report.json").write_bytes(
            json.dumps({"ok": True, "excel": {"sheet_count": 32}}).encode()
        )
        (aud / "compliance_v2_cross_format.json").write_bytes(
            json.dumps({"pass": True, "mismatches": []}).encode()
        )
        (aud / "compliance_v2_content_audit.json").write_bytes(
            json.dumps({"ok": True}).encode()
        )
        return dict(_FAKE_SCORE)
    return _run


def _make_gen_module(fake_fn=None, **overrides):
    m = mock.MagicMock()
    m.run_standards_compliance_v2_visual_qa = fake_fn or _default_fake_gen()
    m.advisory_only               = overrides.get("advisory_only", True)
    m.certification_ready         = overrides.get("certification_ready", False)
    m.fake_signature_created      = overrides.get("fake_signature_created", False)
    m.ml_suggestion_only          = overrides.get("ml_suggestion_only", True)
    m.ml_trained_on_approved_only = overrides.get("ml_trained_on_approved_only", True)
    m.ml_auto_decision            = overrides.get("ml_auto_decision", False)
    m.synthetic_data              = overrides.get("synthetic_data", True)
    m.CASE_ID                     = _CID
    return m


def _make_app():
    from flask import Flask  # type: ignore
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


def _fake_require_auth(fn):
    from functools import wraps
    from flask import g, request, jsonify  # type: ignore
    @wraps(fn)
    def _w(*a, **kw):
        tok = request.headers.get("X-Test-Auth", "")
        if not tok:
            return jsonify({"ok": False, "error": "UNAUTHORIZED"}), 401
        g.user_id = tok
        return fn(*a, **kw)
    return _w


def _is_admin_yes(uid: str) -> bool:
    return True


def _is_admin_no(uid: str) -> bool:
    return False


def _register_v2(app, tmp_path: str, *, ra=None, ia=None, gm=None) -> None:
    from pv_standards_compliance_v2_endpoint import register_standards_compliance_v2
    mod = gm or _make_gen_module()
    with mock.patch.dict(sys.modules, {_V2_GEN_MOD: mod}):
        register_standards_compliance_v2(
            app, ra or _fake_require_auth, ia or _is_admin_yes, tmp_path,
        )


@contextlib.contextmanager
def _client_ctx(*, is_admin=True, gen_fn=None, gen_kw=None):
    gm = _make_gen_module(fake_fn=gen_fn or _default_fake_gen(), **(gen_kw or {}))
    ia = _is_admin_yes if is_admin else _is_admin_no
    with tempfile.TemporaryDirectory() as tmpdir:
        app = _make_app()
        _register_v2(app, tmpdir, ia=ia, gm=gm)
        with app.test_client() as client:
            yield client, tmpdir


def _admin_hdr():
    return {"X-Test-Auth": "admin"}


def _do_post(client, *, body=None, ct=None, extra_headers=None):
    h = dict(_admin_hdr())
    if ct is not None:
        h["Content-Type"] = ct
    if extra_headers:
        h.update(extra_headers)
    kw: dict = {}
    if body is not None:
        kw["data"] = body
    return client.post("/api/standards-compliance-v2/runs", headers=h, **kw)


def _post_run(client) -> str:
    resp = _do_post(client)
    assert resp.status_code == 200, resp.data
    return json.loads(resp.data)["run_id"]


def _get_meta(client, run_id: str):
    return client.get(
        f"/api/standards-compliance-v2/runs/{run_id}",
        headers=_admin_hdr(),
    )


def _get_art(client, run_id: str, key: str):
    return client.get(
        f"/api/standards-compliance-v2/runs/{run_id}/artifacts/{key}",
        headers=_admin_hdr(),
    )


def _del_run(client, run_id: str):
    return client.delete(
        f"/api/standards-compliance-v2/runs/{run_id}",
        headers=_admin_hdr(),
    )


def _valid_run_id_str() -> str:
    return uuid.uuid4().hex


# ── SC2-01–10: Module structure ───────────────────────────────────────────────

def test_SC2_01_generator_callable():
    from standards_compliance_v2_generator import run_standards_compliance_v2_visual_qa
    assert callable(run_standards_compliance_v2_visual_qa)


def test_SC2_02_case_id():
    from standards_compliance_v2_generator import CASE_ID
    assert CASE_ID == "QA-COMPLIANCE-VISUAL-001"


def test_SC2_03_currency_sar():
    from standards_compliance_v2_generator import CURRENCY
    assert CURRENCY == "SAR"


def test_SC2_04_clauses_count_30():
    from standards_compliance_v2_generator import CLAUSES
    assert len(CLAUSES) == 30, f"Expected 30 clauses, got {len(CLAUSES)}"


def test_SC2_05_evidence_count_10():
    from standards_compliance_v2_generator import EVIDENCE
    assert len(EVIDENCE) == 10


def test_SC2_06_score_v2_keys():
    from standards_compliance_v2_generator import SCORE_V2
    for key in ("percentage", "traffic_light", "label", "blocks_issuance",
                "critical_findings", "standard_scores", "applicable_clauses"):
        assert key in SCORE_V2, f"SCORE_V2 missing key: {key}"


def test_SC2_07_endpoint_callable():
    from pv_standards_compliance_v2_endpoint import register_standards_compliance_v2
    assert callable(register_standards_compliance_v2)


def test_SC2_08_bridge_callable():
    from compliance_inputs_bridge import ComplianceInputsBridge
    b = ComplianceInputsBridge()
    assert callable(b.build_provenance_table)


def test_SC2_09_ml_layer_callable():
    from compliance_ml_layer import ComplianceMLLayer
    ml = ComplianceMLLayer()
    assert callable(ml.suggest)
    assert callable(ml.record_feedback)
    assert callable(ml.train_on_approved)


def test_SC2_10_generator_version():
    from standards_compliance_v2_generator import GENERATOR_VERSION
    assert GENERATOR_VERSION.startswith("2.")


# ── SC2-11–20: Clause data integrity ─────────────────────────────────────────

def test_SC2_11_all_clauses_have_required_fields():
    from standards_compliance_v2_generator import CLAUSES
    required = {"standard", "clause_id", "clause_ref", "title", "requirement",
                "status", "severity", "evidence_refs", "findings", "remediation", "blocks_issuance"}
    for cl in CLAUSES:
        missing = required - set(cl.keys())
        assert not missing, f"{cl.get('clause_id')} missing: {missing}"


def test_SC2_12_clause_status_valid():
    from standards_compliance_v2_generator import CLAUSES
    for cl in CLAUSES:
        assert cl["status"] in _VALID_STATUS, f"{cl['clause_id']}: bad status {cl['status']}"


def test_SC2_13_clause_severity_valid():
    from standards_compliance_v2_generator import CLAUSES
    for cl in CLAUSES:
        assert cl["severity"] in _VALID_SEV, f"{cl['clause_id']}: bad severity {cl['severity']}"


def test_SC2_14_ivs_clauses_count_10():
    from standards_compliance_v2_generator import CLAUSES
    ivs = [c for c in CLAUSES if "IVS" in c["standard"]]
    assert len(ivs) == 10, f"Expected 10 IVS clauses, got {len(ivs)}"


def test_SC2_15_rics_clauses_count_6():
    from standards_compliance_v2_generator import CLAUSES
    rics = [c for c in CLAUSES if "RICS" in c["standard"]]
    assert len(rics) == 6, f"Expected 6 RICS clauses, got {len(rics)}"


def test_SC2_16_basel_clauses_count_4():
    from standards_compliance_v2_generator import CLAUSES
    bas = [c for c in CLAUSES if "Basel" in c["standard"]]
    assert len(bas) == 4, f"Expected 4 Basel clauses, got {len(bas)}"


def test_SC2_17_taqyeem_clauses_count_4():
    from standards_compliance_v2_generator import CLAUSES
    taq = [c for c in CLAUSES if "تقييم" in c["standard"]]
    assert len(taq) == 4, f"Expected 4 Taqyeem clauses, got {len(taq)}"


def test_SC2_18_vps6_critical_blocks():
    from standards_compliance_v2_generator import CLAUSES
    cl = next((c for c in CLAUSES if c["clause_id"] == "VPS-6-UNCERTAINTY"), None)
    assert cl is not None
    assert cl["severity"] == "critical"
    assert cl["blocks_issuance"] is True


def test_SC2_19_vps5_blocks():
    from standards_compliance_v2_generator import CLAUSES
    cl = next((c for c in CLAUSES if c["clause_id"] == "VPS-5-ASSUMPTIONS"), None)
    assert cl is not None
    assert cl["blocks_issuance"] is True


def test_SC2_20_clauses_have_materiality():
    from standards_compliance_v2_generator import CLAUSES
    for cl in CLAUSES:
        assert "materiality" in cl, f"{cl['clause_id']} missing materiality"
        assert cl["materiality"] in ("material", "non_material", "not_applicable")


# ── SC2-21–28: Score computation ──────────────────────────────────────────────

def test_SC2_21_score_in_yellow_zone():
    from standards_compliance_v2_generator import SCORE_V2
    pct = SCORE_V2["percentage"]
    assert 50 <= pct <= 85, f"Score {pct}% outside expected yellow zone"


def test_SC2_22_traffic_light_yellow():
    from standards_compliance_v2_generator import SCORE_V2
    assert SCORE_V2["traffic_light"] == "yellow"


def test_SC2_23_label_arabic():
    from standards_compliance_v2_generator import SCORE_V2
    assert "متوافق" in SCORE_V2["label"]


def test_SC2_24_blocks_issuance_list():
    from standards_compliance_v2_generator import SCORE_V2
    bi = SCORE_V2["blocks_issuance"]
    assert isinstance(bi, list) and len(bi) >= 1


def test_SC2_25_critical_findings_ge_1():
    from standards_compliance_v2_generator import SCORE_V2
    cf = SCORE_V2["critical_findings"]
    assert len(cf) >= 1


def test_SC2_26_standard_scores_6_standards():
    from standards_compliance_v2_generator import SCORE_V2
    assert len(SCORE_V2["standard_scores"]) == 6


def test_SC2_27_standard_scores_pct_valid():
    from standards_compliance_v2_generator import SCORE_V2
    for std, v in SCORE_V2["standard_scores"].items():
        assert 0 <= v["pct"] <= 100, f"{std}: pct={v['pct']} out of range"


def test_SC2_28_applicable_clauses_lt_total():
    from standards_compliance_v2_generator import SCORE_V2, CLAUSES
    assert SCORE_V2["applicable_clauses"] <= len(CLAUSES)


# ── SV Group 1 (SV01-SV14): Module-level constants ───────────────────────────

def test_SV01_semaphore_is_bounded_semaphore():
    assert isinstance(_ep2._SEMAPHORE, type(threading.BoundedSemaphore(1)))


def test_SV02_case_id_constant():
    assert _ep2._CASE_ID == "QA-COMPLIANCE-VISUAL-001"


def test_SV03_run_id_re_accepts_valid():
    assert _ep2._RUN_ID_RE.match("a" * 32) is not None


def test_SV04_run_id_re_rejects_uppercase():
    assert _ep2._RUN_ID_RE.match("A" * 32) is None


def test_SV05_run_id_re_rejects_short():
    assert _ep2._RUN_ID_RE.match("abc123") is None


def test_SV06_governance_keys_is_frozenset():
    assert isinstance(_ep2._GOVERNANCE_KEYS, frozenset)


def test_SV07_governance_keys_count_7():
    assert len(_ep2._GOVERNANCE_KEYS) == 7


def test_SV08_governance_keys_exact_set():
    assert _ep2._GOVERNANCE_KEYS == _EXPECTED_GOVERNANCE_KEYS


def test_SV09_metadata_top_keys_is_frozenset():
    assert isinstance(_ep2._METADATA_TOP_KEYS, frozenset)


def test_SV10_metadata_top_keys_count_8():
    assert len(_ep2._METADATA_TOP_KEYS) == 8


def test_SV11_metadata_top_keys_exact_set():
    assert _ep2._METADATA_TOP_KEYS == _EXPECTED_METADATA_TOP_KEYS


def test_SV12_metadata_max_bytes():
    assert _ep2._METADATA_MAX_BYTES == 65_536


def test_SV13_artifact_map_count_8():
    assert len(_ep2._ARTIFACT_MAP) == 8


def test_SV14_artifact_map_keys():
    assert sorted(_ep2._ARTIFACT_MAP.keys()) == _EXPECTED_ARTIFACT_KEYS


# ── SV Group 2 (SV15-SV21): _DelResult enum ──────────────────────────────────

def test_SV15_del_result_count_6():
    assert len(_ep2._DelResult) == 6


def test_SV16_del_result_deleted():
    assert _ep2._DelResult.DELETED.value == "DELETED"


def test_SV17_del_result_not_found():
    assert _ep2._DelResult.NOT_FOUND.value == "NOT_FOUND"


def test_SV18_del_result_refused_outside_root():
    assert _ep2._DelResult.REFUSED_OUTSIDE_ROOT.value == "REFUSED_OUTSIDE_ROOT"


def test_SV19_del_result_refused_reparse():
    assert _ep2._DelResult.REFUSED_REPARSE_POINT.value == "REFUSED_REPARSE_POINT"


def test_SV20_del_result_refused_unknown():
    assert _ep2._DelResult.REFUSED_UNKNOWN_STRUCTURE.value == "REFUSED_UNKNOWN_STRUCTURE"


def test_SV21_del_result_failed_io():
    assert _ep2._DelResult.FAILED_IO.value == "FAILED_IO"


# ── SV Group 3 (SV22-SV28): _is_link_or_reparse_lstat + ARTIFACT_MAP spots ──

def test_SV22_is_link_or_reparse_callable():
    assert callable(_ep2._is_link_or_reparse_lstat)


def test_SV23_is_link_false_for_regular_file():
    import os
    with tempfile.NamedTemporaryFile(delete=False) as f:
        p = pathlib.Path(f.name)
    try:
        st = os.lstat(p)
        assert _ep2._is_link_or_reparse_lstat(st) is False
    finally:
        p.unlink(missing_ok=True)


def test_SV24_is_link_false_for_regular_dir():
    import os
    with tempfile.TemporaryDirectory() as d:
        st = os.lstat(d)
        assert _ep2._is_link_or_reparse_lstat(st) is False


def test_SV25_artifact_map_user_html_disposition_inline():
    assert _ep2._ARTIFACT_MAP["user_html"][2] == "inline"


def test_SV26_artifact_map_user_pdf_disposition_attachment():
    assert _ep2._ARTIFACT_MAP["user_pdf"][2] == "attachment"


def test_SV27_artifact_map_audit_report_mime_json():
    assert _ep2._ARTIFACT_MAP["audit_report"][1] == "application/json"


def test_SV28_audit_subdir_keys_exact():
    assert isinstance(_ep2._AUDIT_SUBDIR_KEYS, frozenset)
    assert len(_ep2._AUDIT_SUBDIR_KEYS) == 3
    assert _ep2._AUDIT_SUBDIR_KEYS == frozenset({"audit_report", "audit_cross", "audit_content"})


# ── SV Group 4 (SV29-SV40): Registration behavior ────────────────────────────

def test_SV29_registration_sets_extension():
    with tempfile.TemporaryDirectory() as tmpdir:
        app = _make_app()
        _register_v2(app, tmpdir)
        assert app.extensions.get("sc_v2_registered") is True


def test_SV30_registration_idempotent():
    with tempfile.TemporaryDirectory() as tmpdir:
        app = _make_app()
        _register_v2(app, tmpdir)
        _register_v2(app, tmpdir)  # second call must not raise
        assert app.extensions.get("sc_v2_registered") is True


def test_SV31_raises_for_missing_outputs():
    app = _make_app()
    gm = _make_gen_module()
    from pv_standards_compliance_v2_endpoint import register_standards_compliance_v2
    import pytest
    with mock.patch.dict(sys.modules, {_V2_GEN_MOD: gm}):
        try:
            register_standards_compliance_v2(
                app, _fake_require_auth, _is_admin_yes,
                "/nonexistent/path/that/does/not/exist",
            )
            assert False, "Expected RuntimeError"
        except RuntimeError:
            pass


def test_SV32_raises_for_generator_import_failure():
    from pv_standards_compliance_v2_endpoint import register_standards_compliance_v2
    with tempfile.TemporaryDirectory() as tmpdir:
        app = _make_app()
        with mock.patch.dict(sys.modules, {_V2_GEN_MOD: None}):
            try:
                register_standards_compliance_v2(
                    app, _fake_require_auth, _is_admin_yes, tmpdir,
                )
                assert False, "Expected RuntimeError"
            except RuntimeError:
                pass


def test_SV33_post_run_endpoint_registered():
    with tempfile.TemporaryDirectory() as tmpdir:
        app = _make_app()
        _register_v2(app, tmpdir)
        assert "sc_v2.sc_v2_post_run" in app.view_functions


def test_SV34_get_metadata_endpoint_registered():
    with tempfile.TemporaryDirectory() as tmpdir:
        app = _make_app()
        _register_v2(app, tmpdir)
        assert "sc_v2.sc_v2_get_metadata" in app.view_functions


def test_SV35_get_artifact_endpoint_registered():
    with tempfile.TemporaryDirectory() as tmpdir:
        app = _make_app()
        _register_v2(app, tmpdir)
        assert "sc_v2.sc_v2_get_artifact" in app.view_functions


def test_SV36_delete_run_endpoint_registered():
    with tempfile.TemporaryDirectory() as tmpdir:
        app = _make_app()
        _register_v2(app, tmpdir)
        assert "sc_v2.sc_v2_delete_run" in app.view_functions


def test_SV37_post_route_in_url_map():
    with tempfile.TemporaryDirectory() as tmpdir:
        app = _make_app()
        _register_v2(app, tmpdir)
        rules = {(r.rule, m) for r in app.url_map.iter_rules() for m in (r.methods or [])}
        assert ("/api/standards-compliance-v2/runs", "POST") in rules


def test_SV38_get_metadata_route_in_url_map():
    with tempfile.TemporaryDirectory() as tmpdir:
        app = _make_app()
        _register_v2(app, tmpdir)
        rules = {r.rule for r in app.url_map.iter_rules()}
        assert "/api/standards-compliance-v2/runs/<run_id>" in rules


def test_SV39_get_artifact_route_in_url_map():
    with tempfile.TemporaryDirectory() as tmpdir:
        app = _make_app()
        _register_v2(app, tmpdir)
        rules = {r.rule for r in app.url_map.iter_rules()}
        assert "/api/standards-compliance-v2/runs/<run_id>/artifacts/<artifact_key>" in rules


def test_SV40_after_failure_extension_not_set():
    app = _make_app()
    gm = _make_gen_module()
    from pv_standards_compliance_v2_endpoint import register_standards_compliance_v2
    with mock.patch.dict(sys.modules, {_V2_GEN_MOD: gm}):
        try:
            register_standards_compliance_v2(
                app, _fake_require_auth, _is_admin_yes,
                "/no/such/path",
            )
        except RuntimeError:
            pass
    assert not app.extensions.get("sc_v2_registered")
    assert "sc_v2.sc_v2_post_run" not in app.view_functions


# ── SV Group 5 (SV41-SV50): POST auth and body parsing ───────────────────────

def test_SV41_post_without_auth_401():
    with _client_ctx() as (client, _):
        resp = client.post("/api/standards-compliance-v2/runs")
        assert resp.status_code == 401


def test_SV42_post_non_admin_403():
    with _client_ctx(is_admin=False) as (client, _):
        resp = client.post("/api/standards-compliance-v2/runs",
                           headers=_admin_hdr())
        assert resp.status_code == 403


def test_SV43_post_empty_body_200():
    with _client_ctx() as (client, _):
        resp = _do_post(client)
        assert resp.status_code == 200


def test_SV44_post_empty_json_object_200():
    with _client_ctx() as (client, _):
        resp = _do_post(client, body=b"{}", ct="application/json")
        assert resp.status_code == 200


def test_SV45_post_extra_field_400():
    with _client_ctx() as (client, _):
        resp = _do_post(client, body=b'{"mode":"fast"}', ct="application/json")
        assert resp.status_code == 400
        assert b"UNKNOWN_FIELD" in resp.data


def test_SV46_post_wrong_content_type_415():
    with _client_ctx() as (client, _):
        resp = _do_post(client, body=b"hello", ct="text/plain")
        assert resp.status_code == 415


def test_SV47_post_oversized_body_413():
    with _client_ctx() as (client, _):
        resp = _do_post(client, body=b"x" * 257, ct="application/json")
        assert resp.status_code == 413


def test_SV48_post_invalid_json_400():
    with _client_ctx() as (client, _):
        resp = _do_post(client, body=b"{bad json", ct="application/json")
        assert resp.status_code == 400
        assert b"INVALID_JSON" in resp.data


def test_SV49_post_json_array_400():
    with _client_ctx() as (client, _):
        resp = _do_post(client, body=b"[]", ct="application/json")
        assert resp.status_code == 400
        assert b"INVALID_REQUEST" in resp.data


def test_SV50_post_non_utf8_bytes_400():
    with _client_ctx() as (client, _):
        resp = _do_post(client, body=b"\xff\xfe" + b"x" * 10, ct="application/json")
        assert resp.status_code == 400


# ── SV Group 6 (SV51-SV62): POST success response ────────────────────────────

def test_SV51_post_returns_200():
    with _client_ctx() as (client, _):
        assert _do_post(client).status_code == 200


def test_SV52_post_response_ok_true():
    with _client_ctx() as (client, _):
        d = json.loads(_do_post(client).data)
        assert d["ok"] is True


def test_SV53_post_run_id_is_32_hex():
    with _client_ctx() as (client, _):
        d = json.loads(_do_post(client).data)
        rid = d["run_id"]
        assert isinstance(rid, str)
        assert _ep2._RUN_ID_RE.match(rid) is not None


def test_SV54_post_status_completed():
    with _client_ctx() as (client, _):
        d = json.loads(_do_post(client).data)
        assert d["status"] == "completed"


def test_SV55_post_advisory_only_true():
    with _client_ctx() as (client, _):
        d = json.loads(_do_post(client).data)
        assert d["advisory_only"] is True


def test_SV56_post_certification_ready_false():
    with _client_ctx() as (client, _):
        d = json.loads(_do_post(client).data)
        assert d["certification_ready"] is False


def test_SV57_post_synthetic_data_true():
    with _client_ctx() as (client, _):
        d = json.loads(_do_post(client).data)
        assert d["synthetic_data"] is True


def test_SV58_post_response_has_elapsed_seconds():
    with _client_ctx() as (client, _):
        d = json.loads(_do_post(client).data)
        assert "elapsed_seconds" in d
        assert isinstance(d["elapsed_seconds"], (int, float))


def test_SV59_post_creates_run_dir():
    with _client_ctx() as (client, tmpdir):
        d = json.loads(_do_post(client).data)
        run_dir = pathlib.Path(tmpdir) / "visual_qa_standards_compliance_v2" / d["run_id"]
        assert run_dir.is_dir()


def test_SV60_post_creates_metadata_file():
    with _client_ctx() as (client, tmpdir):
        d = json.loads(_do_post(client).data)
        meta = (
            pathlib.Path(tmpdir) / "visual_qa_standards_compliance_v2"
            / d["run_id"] / "run_metadata.json"
        )
        assert meta.is_file()


def test_SV61_post_metadata_is_valid_json():
    with _client_ctx() as (client, tmpdir):
        d = json.loads(_do_post(client).data)
        meta = (
            pathlib.Path(tmpdir) / "visual_qa_standards_compliance_v2"
            / d["run_id"] / "run_metadata.json"
        )
        obj = json.loads(meta.read_bytes())
        assert isinstance(obj, dict)


def test_SV62_post_metadata_schema_version_1():
    with _client_ctx() as (client, tmpdir):
        d = json.loads(_do_post(client).data)
        meta = (
            pathlib.Path(tmpdir) / "visual_qa_standards_compliance_v2"
            / d["run_id"] / "run_metadata.json"
        )
        obj = json.loads(meta.read_bytes())
        assert obj["schema_version"] == 1


# ── SV Group 7 (SV63-SV68): POST metadata content ────────────────────────────

def test_SV63_metadata_run_id_matches():
    with _client_ctx() as (client, tmpdir):
        d = json.loads(_do_post(client).data)
        meta_path = (
            pathlib.Path(tmpdir) / "visual_qa_standards_compliance_v2"
            / d["run_id"] / "run_metadata.json"
        )
        obj = json.loads(meta_path.read_bytes())
        assert obj["run_id"] == d["run_id"]


def test_SV64_metadata_case_id():
    with _client_ctx() as (client, tmpdir):
        d = json.loads(_do_post(client).data)
        meta_path = (
            pathlib.Path(tmpdir) / "visual_qa_standards_compliance_v2"
            / d["run_id"] / "run_metadata.json"
        )
        obj = json.loads(meta_path.read_bytes())
        assert obj["case_id"] == _CID


def test_SV65_metadata_status_completed():
    with _client_ctx() as (client, tmpdir):
        d = json.loads(_do_post(client).data)
        meta_path = (
            pathlib.Path(tmpdir) / "visual_qa_standards_compliance_v2"
            / d["run_id"] / "run_metadata.json"
        )
        obj = json.loads(meta_path.read_bytes())
        assert obj["status"] == "completed"


def test_SV66_metadata_governance_has_7_keys():
    with _client_ctx() as (client, tmpdir):
        d = json.loads(_do_post(client).data)
        meta_path = (
            pathlib.Path(tmpdir) / "visual_qa_standards_compliance_v2"
            / d["run_id"] / "run_metadata.json"
        )
        obj = json.loads(meta_path.read_bytes())
        assert set(obj["governance"].keys()) == _EXPECTED_GOVERNANCE_KEYS


def test_SV67_metadata_governance_synthetic_data():
    with _client_ctx() as (client, tmpdir):
        d = json.loads(_do_post(client).data)
        meta_path = (
            pathlib.Path(tmpdir) / "visual_qa_standards_compliance_v2"
            / d["run_id"] / "run_metadata.json"
        )
        obj = json.loads(meta_path.read_bytes())
        assert obj["governance"]["synthetic_data"] is True


def test_SV68_metadata_artifact_keys_sorted():
    with _client_ctx() as (client, tmpdir):
        d = json.loads(_do_post(client).data)
        meta_path = (
            pathlib.Path(tmpdir) / "visual_qa_standards_compliance_v2"
            / d["run_id"] / "run_metadata.json"
        )
        obj = json.loads(meta_path.read_bytes())
        assert obj["artifact_keys"] == _EXPECTED_ARTIFACT_KEYS


# ── SV Group 8 (SV69-SV73): POST failure cases ───────────────────────────────

def _raising_gen():
    def _run(*, output_root, run_id, case_id=_CID, overwrite=False):
        raise RuntimeError("intentional test failure")
    return _run


def test_SV69_post_500_on_generator_exception():
    with _client_ctx(gen_fn=_raising_gen()) as (client, _):
        resp = _do_post(client)
        assert resp.status_code == 500
        assert b"GENERATION_FAILED" in resp.data


def test_SV70_post_cleans_run_dir_on_gen_failure():
    with _client_ctx(gen_fn=_raising_gen()) as (client, tmpdir):
        _do_post(client)
        case_dir = pathlib.Path(tmpdir) / "visual_qa_standards_compliance_v2"
        # No run directories should remain (all cleaned up)
        run_dirs = [p for p in case_dir.iterdir() if p.is_dir()] if case_dir.exists() else []
        assert run_dirs == []


def test_SV71_post_503_when_semaphore_held():
    _ep2._SEMAPHORE.acquire()
    try:
        with _client_ctx() as (client, _):
            resp = _do_post(client)
            assert resp.status_code == 503
            assert b"CAPACITY_BUSY" in resp.data
    finally:
        _ep2._SEMAPHORE.release()


def test_SV72_semaphore_released_after_success():
    with _client_ctx() as (client, _):
        resp = _do_post(client)
        assert resp.status_code == 200
    acquired = _ep2._SEMAPHORE.acquire(blocking=False)
    try:
        assert acquired, "Semaphore not released after successful POST"
    finally:
        if acquired:
            _ep2._SEMAPHORE.release()


def test_SV73_semaphore_released_after_gen_failure():
    with _client_ctx(gen_fn=_raising_gen()) as (client, _):
        resp = _do_post(client)
        assert resp.status_code == 500
    acquired = _ep2._SEMAPHORE.acquire(blocking=False)
    try:
        assert acquired, "Semaphore not released after generator failure"
    finally:
        if acquired:
            _ep2._SEMAPHORE.release()


# ── SV Group 9 (SV74-SV82): GET metadata route ───────────────────────────────

def test_SV74_get_meta_no_auth_401():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        resp = client.get(f"/api/standards-compliance-v2/runs/{rid}")
        assert resp.status_code == 401


def test_SV75_get_meta_non_admin_403():
    with _client_ctx(is_admin=False) as (client, _):
        rid = _valid_run_id_str()
        resp = client.get(
            f"/api/standards-compliance-v2/runs/{rid}",
            headers=_admin_hdr(),
        )
        assert resp.status_code == 403


def test_SV76_get_meta_invalid_run_id_short_404():
    with _client_ctx() as (client, _):
        resp = _get_meta(client, "abc123")
        assert resp.status_code == 404


def test_SV77_get_meta_uppercase_run_id_404():
    with _client_ctx() as (client, _):
        resp = _get_meta(client, "A" * 32)
        assert resp.status_code == 404


def test_SV78_get_meta_nonexistent_valid_run_id_404():
    with _client_ctx() as (client, _):
        resp = _get_meta(client, _valid_run_id_str())
        assert resp.status_code == 404


def test_SV79_get_meta_existing_run_200():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        assert _get_meta(client, rid).status_code == 200


def test_SV80_get_meta_content_type_json():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        resp = _get_meta(client, rid)
        assert "application/json" in resp.content_type


def test_SV81_get_meta_cache_control_no_store():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        resp = _get_meta(client, rid)
        assert "no-store" in resp.headers.get("Cache-Control", "")


def test_SV82_get_meta_body_has_8_keys():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        resp = _get_meta(client, rid)
        obj = json.loads(resp.data)
        assert set(obj.keys()) == _EXPECTED_METADATA_TOP_KEYS


# ── SV Group 10 (SV83-SV87): GET metadata content ────────────────────────────

def test_SV83_get_meta_run_id_matches():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        obj = json.loads(_get_meta(client, rid).data)
        assert obj["run_id"] == rid


def test_SV84_get_meta_case_id():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        obj = json.loads(_get_meta(client, rid).data)
        assert obj["case_id"] == _CID


def test_SV85_get_meta_status_completed():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        obj = json.loads(_get_meta(client, rid).data)
        assert obj["status"] == "completed"


def test_SV86_get_meta_governance_synthetic_data():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        obj = json.loads(_get_meta(client, rid).data)
        assert obj["governance"]["synthetic_data"] is True


def test_SV87_get_meta_artifact_keys_sorted():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        obj = json.loads(_get_meta(client, rid).data)
        assert obj["artifact_keys"] == _EXPECTED_ARTIFACT_KEYS


# ── SV Group 11 (SV88-SV102): GET artifact route ─────────────────────────────

def test_SV88_get_artifact_no_auth_401():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        resp = client.get(f"/api/standards-compliance-v2/runs/{rid}/artifacts/user_html")
        assert resp.status_code == 401


def test_SV89_get_artifact_non_admin_403():
    with _client_ctx(is_admin=False) as (client, _):
        rid = _valid_run_id_str()
        resp = client.get(
            f"/api/standards-compliance-v2/runs/{rid}/artifacts/user_html",
            headers=_admin_hdr(),
        )
        assert resp.status_code == 403


def test_SV90_get_artifact_invalid_run_id_404():
    with _client_ctx() as (client, _):
        resp = _get_art(client, "bad", "user_html")
        assert resp.status_code == 404


def test_SV91_get_artifact_unknown_key_404():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        resp = _get_art(client, rid, "no_such_key")
        assert resp.status_code == 404


def test_SV92_get_artifact_missing_file_404():
    with _client_ctx() as (client, _):
        resp = _get_art(client, _valid_run_id_str(), "user_html")
        assert resp.status_code == 404


def test_SV93_get_user_html_200():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        assert _get_art(client, rid, "user_html").status_code == 200


def test_SV94_get_admin_html_200():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        assert _get_art(client, rid, "admin_html").status_code == 200


def test_SV95_get_user_pdf_200():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        assert _get_art(client, rid, "user_pdf").status_code == 200


def test_SV96_get_admin_pdf_200():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        assert _get_art(client, rid, "admin_pdf").status_code == 200


def test_SV97_get_admin_xlsx_200():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        assert _get_art(client, rid, "admin_xlsx").status_code == 200


def test_SV98_get_audit_report_200():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        assert _get_art(client, rid, "audit_report").status_code == 200


def test_SV99_get_audit_cross_200():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        assert _get_art(client, rid, "audit_cross").status_code == 200


def test_SV100_get_audit_content_200():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        assert _get_art(client, rid, "audit_content").status_code == 200


def test_SV101_user_html_has_csp_header():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        resp = _get_art(client, rid, "user_html")
        assert "Content-Security-Policy" in resp.headers


def test_SV102_admin_html_has_csp_header():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        resp = _get_art(client, rid, "admin_html")
        assert "Content-Security-Policy" in resp.headers


# ── SV Group 12 (SV103-SV117): GET artifact headers ──────────────────────────

def test_SV103_user_html_x_content_type_nosniff():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        resp = _get_art(client, rid, "user_html")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"


def test_SV104_user_html_cache_control_no_store():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        resp = _get_art(client, rid, "user_html")
        assert "no-store" in resp.headers.get("Cache-Control", "")


def test_SV105_user_html_content_type():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        resp = _get_art(client, rid, "user_html")
        assert "text/html" in resp.content_type


def test_SV106_user_html_content_disposition_inline():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        resp = _get_art(client, rid, "user_html")
        assert resp.headers.get("Content-Disposition", "").startswith("inline")


def test_SV107_user_pdf_content_type():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        resp = _get_art(client, rid, "user_pdf")
        assert "application/pdf" in resp.content_type


def test_SV108_user_pdf_content_disposition_attachment():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        resp = _get_art(client, rid, "user_pdf")
        assert resp.headers.get("Content-Disposition", "").startswith("attachment")


def test_SV109_admin_xlsx_content_type_ooxml():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        resp = _get_art(client, rid, "admin_xlsx")
        assert "openxmlformats" in resp.content_type


def test_SV110_admin_xlsx_content_disposition_attachment():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        resp = _get_art(client, rid, "admin_xlsx")
        assert resp.headers.get("Content-Disposition", "").startswith("attachment")


def test_SV111_audit_report_content_type_json():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        resp = _get_art(client, rid, "audit_report")
        assert "application/json" in resp.content_type


def test_SV112_audit_report_content_disposition_attachment():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        resp = _get_art(client, rid, "audit_report")
        assert resp.headers.get("Content-Disposition", "").startswith("attachment")


def test_SV113_user_pdf_data_starts_with_pdf_header():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        resp = _get_art(client, rid, "user_pdf")
        assert resp.data[:4] == b"%PDF"


def test_SV114_admin_xlsx_data_starts_with_pk_header():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        resp = _get_art(client, rid, "admin_xlsx")
        assert resp.data[:2] == b"PK"


def test_SV115_audit_report_data_is_valid_json():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        resp = _get_art(client, rid, "audit_report")
        obj = json.loads(resp.data)
        assert isinstance(obj, dict)


def test_SV116_user_pdf_has_no_csp_header():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        resp = _get_art(client, rid, "user_pdf")
        assert "Content-Security-Policy" not in resp.headers


def test_SV117_audit_cross_data_is_valid_json():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        resp = _get_art(client, rid, "audit_cross")
        obj = json.loads(resp.data)
        assert isinstance(obj, dict)


# ── SV Group 13 (SV118-SV122): DELETE route ──────────────────────────────────

def test_SV118_delete_no_auth_401():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        resp = client.delete(f"/api/standards-compliance-v2/runs/{rid}")
        assert resp.status_code == 401


def test_SV119_delete_non_admin_403():
    with _client_ctx(is_admin=False) as (client, _):
        rid = _valid_run_id_str()
        resp = client.delete(
            f"/api/standards-compliance-v2/runs/{rid}",
            headers=_admin_hdr(),
        )
        assert resp.status_code == 403


def test_SV120_delete_invalid_run_id_404():
    with _client_ctx() as (client, _):
        resp = _del_run(client, "bad")
        assert resp.status_code == 404


def test_SV121_delete_nonexistent_valid_run_id_404():
    with _client_ctx() as (client, _):
        resp = _del_run(client, _valid_run_id_str())
        assert resp.status_code == 404


def test_SV122_delete_existing_run_200():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        resp = _del_run(client, rid)
        assert resp.status_code == 200


# ── SV Group 14 (SV123-SV128): DELETE behavior ───────────────────────────────

def test_SV123_delete_response_ok_deleted():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        d = json.loads(_del_run(client, rid).data)
        assert d["ok"] is True
        assert d["deleted"] is True


def test_SV124_delete_response_run_id_matches():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        d = json.loads(_del_run(client, rid).data)
        assert d["run_id"] == rid


def test_SV125_delete_removes_run_dir():
    with _client_ctx() as (client, tmpdir):
        rid = _post_run(client)
        run_dir = (
            pathlib.Path(tmpdir) / "visual_qa_standards_compliance_v2" / rid
        )
        assert run_dir.is_dir()
        _del_run(client, rid)
        assert not run_dir.exists()


def test_SV126_delete_503_when_semaphore_held():
    _ep2._SEMAPHORE.acquire()
    try:
        with _client_ctx() as (client, _):
            resp = _del_run(client, _valid_run_id_str())
            assert resp.status_code == 503
    finally:
        _ep2._SEMAPHORE.release()


def test_SV127_second_delete_404():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        _del_run(client, rid)
        resp = _del_run(client, rid)
        assert resp.status_code == 404


def test_SV128_delete_releases_semaphore():
    with _client_ctx() as (client, _):
        rid = _post_run(client)
        _del_run(client, rid)
    acquired = _ep2._SEMAPHORE.acquire(blocking=False)
    try:
        assert acquired, "Semaphore not released after DELETE"
    finally:
        if acquired:
            _ep2._SEMAPHORE.release()


# ── SV Group 15 (SV129-SV137): Generator isolation (fake gen) ────────────────

def test_SV129_fake_gen_creates_run_dir():
    fn = _default_fake_gen()
    with tempfile.TemporaryDirectory() as tmpdir:
        rid = uuid.uuid4().hex
        fn(output_root=tmpdir, run_id=rid)
        assert (pathlib.Path(tmpdir) / rid).is_dir()


def test_SV130_fake_gen_creates_artifacts_subdir():
    fn = _default_fake_gen()
    with tempfile.TemporaryDirectory() as tmpdir:
        rid = uuid.uuid4().hex
        fn(output_root=tmpdir, run_id=rid)
        assert (pathlib.Path(tmpdir) / rid / "artifacts").is_dir()


def test_SV131_fake_gen_creates_audits_subdir():
    fn = _default_fake_gen()
    with tempfile.TemporaryDirectory() as tmpdir:
        rid = uuid.uuid4().hex
        fn(output_root=tmpdir, run_id=rid)
        assert (pathlib.Path(tmpdir) / rid / "audits").is_dir()


def test_SV132_fake_gen_creates_user_html():
    fn = _default_fake_gen()
    with tempfile.TemporaryDirectory() as tmpdir:
        rid = uuid.uuid4().hex
        fn(output_root=tmpdir, run_id=rid)
        p = pathlib.Path(tmpdir) / rid / "artifacts" / f"compliance_v2_{_CID}_user.html"
        assert p.is_file()


def test_SV133_fake_gen_creates_admin_html():
    fn = _default_fake_gen()
    with tempfile.TemporaryDirectory() as tmpdir:
        rid = uuid.uuid4().hex
        fn(output_root=tmpdir, run_id=rid)
        p = pathlib.Path(tmpdir) / rid / "artifacts" / f"compliance_v2_{_CID}_admin.html"
        assert p.is_file()


def test_SV134_fake_gen_creates_user_pdf():
    fn = _default_fake_gen()
    with tempfile.TemporaryDirectory() as tmpdir:
        rid = uuid.uuid4().hex
        fn(output_root=tmpdir, run_id=rid)
        p = pathlib.Path(tmpdir) / rid / "artifacts" / f"compliance_v2_{_CID}_user.pdf"
        assert p.is_file()


def test_SV135_fake_gen_creates_admin_pdf():
    fn = _default_fake_gen()
    with tempfile.TemporaryDirectory() as tmpdir:
        rid = uuid.uuid4().hex
        fn(output_root=tmpdir, run_id=rid)
        p = pathlib.Path(tmpdir) / rid / "artifacts" / f"compliance_v2_{_CID}_admin.pdf"
        assert p.is_file()


def test_SV136_fake_gen_creates_admin_xlsx():
    fn = _default_fake_gen()
    with tempfile.TemporaryDirectory() as tmpdir:
        rid = uuid.uuid4().hex
        fn(output_root=tmpdir, run_id=rid)
        p = pathlib.Path(tmpdir) / rid / "artifacts" / f"compliance_v2_{_CID}_admin.xlsx"
        assert p.is_file()


def test_SV137_fake_gen_raises_file_exists_error():
    fn = _default_fake_gen()
    with tempfile.TemporaryDirectory() as tmpdir:
        rid = uuid.uuid4().hex
        fn(output_root=tmpdir, run_id=rid)
        try:
            fn(output_root=tmpdir, run_id=rid, overwrite=False)
            assert False, "Expected FileExistsError"
        except FileExistsError:
            pass


# ── SV Group 16 (SV138-SV143): Generator module constants ────────────────────

def test_SV138_generator_advisory_only_true():
    from standards_compliance_v2_generator import advisory_only
    assert advisory_only is True


def test_SV139_generator_certification_ready_false():
    from standards_compliance_v2_generator import certification_ready
    assert certification_ready is False


def test_SV140_generator_fake_signature_created_false():
    from standards_compliance_v2_generator import fake_signature_created
    assert fake_signature_created is False


def test_SV141_generator_ml_suggestion_only_true():
    from standards_compliance_v2_generator import ml_suggestion_only
    assert ml_suggestion_only is True


def test_SV142_generator_ml_auto_decision_false():
    from standards_compliance_v2_generator import ml_auto_decision
    assert ml_auto_decision is False


def test_SV143_generator_synthetic_data_true():
    from standards_compliance_v2_generator import synthetic_data
    assert synthetic_data is True


# ── SV Group 17 (SV144): Generator function signature ────────────────────────

def test_SV144_generator_all_params_keyword_only():
    from standards_compliance_v2_generator import run_standards_compliance_v2_visual_qa
    sig = inspect.signature(run_standards_compliance_v2_visual_qa)
    for name, param in sig.parameters.items():
        assert param.kind == inspect.Parameter.KEYWORD_ONLY, (
            f"Parameter '{name}' is not keyword-only "
            f"(kind={param.kind})"
        )


# ── SV Group 18 (SV145-SV147): Fake generator return dict contract ───────────

def test_SV145_fake_gen_returns_overall_pass():
    fn = _default_fake_gen()
    with tempfile.TemporaryDirectory() as tmpdir:
        rid = uuid.uuid4().hex
        result = fn(output_root=tmpdir, run_id=rid)
        assert "overall_pass" in result


def test_SV146_fake_gen_returns_score_pct():
    fn = _default_fake_gen()
    with tempfile.TemporaryDirectory() as tmpdir:
        rid = uuid.uuid4().hex
        result = fn(output_root=tmpdir, run_id=rid)
        assert "score_pct" in result


def test_SV147_fake_gen_returns_traffic_light():
    fn = _default_fake_gen()
    with tempfile.TemporaryDirectory() as tmpdir:
        rid = uuid.uuid4().hex
        result = fn(output_root=tmpdir, run_id=rid)
        assert "traffic_light" in result


# ── SV Group 19 (SV148-SV153): _ARTIFACT_MAP completeness ────────────────────

def test_SV148_artifact_map_values_are_4_tuples():
    for key, val in _ep2._ARTIFACT_MAP.items():
        assert isinstance(val, tuple) and len(val) == 4, (
            f"_ARTIFACT_MAP[{key!r}] is not a 4-tuple"
        )


def test_SV149_audit_subdir_keys_is_frozenset():
    assert isinstance(_ep2._AUDIT_SUBDIR_KEYS, frozenset)


def test_SV150_audit_subdir_keys_count_3():
    assert len(_ep2._AUDIT_SUBDIR_KEYS) == 3


def test_SV151_audit_subdir_keys_contains_all_three():
    assert "audit_report" in _ep2._AUDIT_SUBDIR_KEYS
    assert "audit_cross"  in _ep2._AUDIT_SUBDIR_KEYS
    assert "audit_content" in _ep2._AUDIT_SUBDIR_KEYS


def test_SV152_csp_html_contains_frame_ancestors():
    assert "frame-ancestors 'none'" in _ep2._CSP_HTML


def test_SV153_csp_html_contains_base_uri():
    assert "base-uri 'none'" in _ep2._CSP_HTML


# ── Retention-boundary helpers ─────────────────────────────────────────────────

def _case_path(tmpdir: str) -> pathlib.Path:
    return pathlib.Path(tmpdir) / "visual_qa_standards_compliance_v2"


def _iso(seconds_ago: int) -> str:
    import datetime as _dt
    ts = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(seconds=seconds_ago)
    return ts.isoformat()


def _create_completed_run(
    case_path: pathlib.Path,
    created_at: str,
    deletable: bool = True,
) -> str:
    """Create a minimal completed run directory with metadata."""
    run_id = uuid.uuid4().hex
    run_dir = case_path / run_id
    arts = run_dir / "artifacts"
    aud  = run_dir / "audits"
    arts.mkdir(parents=True)
    aud.mkdir()
    (arts / f"compliance_v2_{_CID}_user.html").write_bytes(b"<html>u</html>")
    (arts / f"compliance_v2_{_CID}_admin.html").write_bytes(b"<html>a</html>")
    (arts / f"compliance_v2_{_CID}_user.pdf").write_bytes(b"%PDF-1.4 u")
    (arts / f"compliance_v2_{_CID}_admin.pdf").write_bytes(b"%PDF-1.4 a")
    (arts / f"compliance_v2_{_CID}_admin.xlsx").write_bytes(b"PK\x03\x04fake")
    (aud / "compliance_v2_visual_qa_report.json").write_bytes(b'{"ok":true}')
    (aud / "compliance_v2_cross_format.json").write_bytes(b'{"pass":true}')
    (aud / "compliance_v2_content_audit.json").write_bytes(b'{"ok":true}')
    if not deletable:
        deep = run_dir / "a" / "b" / "c" / "d" / "e"
        deep.mkdir(parents=True)
    meta = {
        "schema_version": 1,
        "run_id":         run_id,
        "case_id":        _CID,
        "created_at":     created_at,
        "status":         "completed",
        "score":          {},
        "governance":     {},
        "artifact_keys":  sorted(_ep2._ARTIFACT_MAP.keys()),
    }
    (run_dir / "run_metadata.json").write_bytes(json.dumps(meta).encode())
    return run_id


# ── RET-BOUND-1: 10 valid runs, oldest deletable → 200 ────────────────────────

def test_RET_BOUND_1_ten_runs_oldest_deleted_generator_called():
    """10 completed runs; oldest deletable. POST must delete it, call generator → 200."""
    gen_calls: list = []

    def _counting_gen(*, output_root, run_id, case_id=_CID, overwrite=False):
        gen_calls.append(run_id)
        return _default_fake_gen()(
            output_root=output_root, run_id=run_id, case_id=case_id, overwrite=overwrite,
        )

    with _client_ctx(gen_fn=_counting_gen) as (client, tmpdir):
        cp = _case_path(tmpdir)
        for i in range(10):
            _create_completed_run(cp, _iso(10000 - i * 1000))

        resp = _do_post(client)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
        assert len(gen_calls) == 1, f"Expected 1 generator call, got {len(gen_calls)}"


# ── RET-BOUND-2: 10 valid runs, ALL REFUSED → 507 ────────────────────────────

def test_RET_BOUND_2_ten_runs_oldest_refused_507():
    """10 completed runs, all with unknown structure (REFUSED). POST must return 507."""
    with _client_ctx() as (client, tmpdir):
        cp = _case_path(tmpdir)
        for i in range(10):
            _create_completed_run(cp, _iso(10000 - i * 1000), deletable=False)

        resp = _do_post(client)
        assert resp.status_code == 507, f"Expected 507, got {resp.status_code}: {resp.data}"
        body = json.loads(resp.data)
        assert body["error"] == "RETENTION_CAPACITY_EXCEEDED"


# ── RET-BOUND-3: 11 valid runs, two oldest deleted → 200 ─────────────────────

def test_RET_BOUND_3_eleven_runs_two_deleted_generator_called():
    """11 completed runs; two oldest deletable. POST must delete two and call generator → 200."""
    gen_calls: list = []

    def _counting_gen(*, output_root, run_id, case_id=_CID, overwrite=False):
        gen_calls.append(run_id)
        return _default_fake_gen()(
            output_root=output_root, run_id=run_id, case_id=case_id, overwrite=overwrite,
        )

    with _client_ctx(gen_fn=_counting_gen) as (client, tmpdir):
        cp = _case_path(tmpdir)
        for i in range(11):
            _create_completed_run(cp, _iso(11000 - i * 1000))

        resp = _do_post(client)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
        assert len(gen_calls) == 1, f"Expected 1 generator call, got {len(gen_calls)}"


# ── RET-BOUND-4: Sort uses parsed created_at, not dir name or mtime ──────────

def test_RET_BOUND_4_sort_by_created_at_not_name_or_mtime():
    """
    10 runs; the run with oldest created_at is created LAST (newer dir name, newer mtime).
    POST must delete that specific run by sorted created_at, not lexicographic name or mtime.
    """
    gen_calls: list = []

    def _counting_gen(*, output_root, run_id, case_id=_CID, overwrite=False):
        gen_calls.append(run_id)
        return _default_fake_gen()(
            output_root=output_root, run_id=run_id, case_id=case_id, overwrite=overwrite,
        )

    with _client_ctx(gen_fn=_counting_gen) as (client, tmpdir):
        cp = _case_path(tmpdir)
        recent_ids = []
        for i in range(9):
            rid = _create_completed_run(cp, _iso(100 + i * 10))
            recent_ids.append(rid)
        oldest_id = _create_completed_run(cp, _iso(3600))

        resp = _do_post(client)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
        assert len(gen_calls) == 1
        assert not (cp / oldest_id).exists(), "Oldest by created_at must be deleted"
        for rid in recent_ids:
            assert (cp / rid).exists(), f"Recent run {rid} was wrongly deleted"


# ── Deletion-boundary helpers ──────────────────────────────────────────────────

def _make_run_in_case(case_path: pathlib.Path, extra_fn=None) -> str:
    """Create a minimal run dir in case_path. extra_fn(run_dir) adds extra structure."""
    run_id = uuid.uuid4().hex
    run_dir = case_path / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "schema_version": 1,
        "run_id":         run_id,
        "case_id":        _CID,
        "created_at":     "2026-01-01T00:00:00+00:00",
        "status":         "completed",
        "score":          {},
        "governance":     {},
        "artifact_keys":  [],
    }
    (run_dir / "run_metadata.json").write_bytes(json.dumps(meta).encode())
    if extra_fn:
        extra_fn(run_dir)
    return run_id


def _make_gen_run_shape(
    case_path: pathlib.Path,
    *,
    with_screenshots: bool = True,
    ss_pngs: dict | None = None,
) -> str:
    """Create a Generator-derived run dir with exact allowlisted structure."""
    run_id = uuid.uuid4().hex
    run_dir = case_path / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "schema_version": 1, "run_id": run_id, "case_id": _CID,
        "created_at": "2026-01-01T00:00:00+00:00",
        "status": "completed", "score": {}, "governance": {}, "artifact_keys": [],
    }
    (run_dir / "run_metadata.json").write_bytes(json.dumps(meta).encode())
    arts = run_dir / "artifacts"
    arts.mkdir()
    (arts / f"compliance_v2_{_CID}_user.html").write_bytes(b"<html/>")
    (arts / f"compliance_v2_{_CID}_admin.html").write_bytes(b"<html/>")
    (arts / f"compliance_v2_{_CID}_user.pdf").write_bytes(b"%PDF")
    (arts / f"compliance_v2_{_CID}_admin.pdf").write_bytes(b"%PDF")
    (arts / f"compliance_v2_{_CID}_admin.xlsx").write_bytes(b"PK")
    aud = run_dir / "audits"
    aud.mkdir()
    (aud / "compliance_v2_visual_qa_report.json").write_bytes(b"{}")
    (aud / "compliance_v2_cross_format.json").write_bytes(b"{}")
    (aud / "compliance_v2_content_audit.json").write_bytes(b"{}")
    if with_screenshots:
        ss = run_dir / "screenshots"
        default_pngs: dict = ss_pngs or {
            "user_html":  ["user_section_01.png", "user_full.png"],
            "admin_html": ["admin_section_01.png", "admin_full.png"],
            "user_pdf":   ["user_pdf_page_01.png"],
            "admin_pdf":  ["admin_pdf_page_01.png"],
        }
        for cat, png_names in default_pngs.items():
            cat_dir = ss / cat
            cat_dir.mkdir(parents=True, exist_ok=True)
            for name in png_names:
                (cat_dir / name).write_bytes(b"\x89PNG\r\n")
    return run_id


def _make_partial_run(cp: pathlib.Path, dirs: list, files: dict) -> str:
    """Create a partial run directory (no run_metadata.json unless supplied in files)."""
    run_id = uuid.uuid4().hex
    run_dir = cp / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    for d in dirs:
        (run_dir / d).mkdir(parents=True, exist_ok=True)
    for path_str, content in files.items():
        p = run_dir / path_str
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
    return run_id


# ── DEL-BOUND-1: Generator-valid structure (deepest: screenshots/cat/img.png) → accepted ──

def test_DEL_BOUND_VALID_DEPTH_accepted():
    """Run with Generator-shaped structure (deepest: screenshots/user_html/img.png) must be DELETED."""
    with _client_ctx() as (client, tmpdir):
        cp = _case_path(tmpdir)
        run_id = _make_gen_run_shape(cp)
        resp = _del_run(client, run_id)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
        body = json.loads(resp.data)
        assert body["ok"] is True and body["deleted"] is True


# ── DEL-BOUND-2: nested dir inside screenshot category → REFUSED, rmtree=0 ────

def test_DEL_BOUND_INVALID_DEPTH_refused():
    """Nested directory inside a screenshot category must be REFUSED; shutil.rmtree must not be called."""
    with mock.patch("shutil.rmtree") as mock_rmtree:
        with _client_ctx() as (client, tmpdir):
            cp = _case_path(tmpdir)
            run_id = _make_gen_run_shape(cp)
            # Add an unexpected nested directory inside screenshots/user_html/
            (cp / run_id / "screenshots" / "user_html" / "nested").mkdir()
            resp = _del_run(client, run_id)
            assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.data}"
            body = json.loads(resp.data)
            assert body["error"] == "RUN_DELETE_REFUSED"
            assert mock_rmtree.call_count == 0, (
                f"shutil.rmtree must not be called on refused delete; "
                f"got {mock_rmtree.call_count} calls"
            )


# ── DEL-BOUND-3: Generator-shaped run with exactly 200 entries → accepted ─────

def test_DEL_BOUND_entries_200_accepted():
    """A Generator-shaped run with exactly 200 total entries must be DELETED (not refused).

    Entry breakdown: 16 base (root×4 + arts×5 + aud×3 + ss-cats×4)
    + 16 user_html (sections 01-15 + full) + 16 admin_html + 76 user_pdf + 76 admin_pdf = 200.
    All PNG names match the tightened Generator-derived allowlist.
    """
    with _client_ctx() as (client, tmpdir):
        cp = _case_path(tmpdir)
        ss_pngs = {
            "user_html":  ["user_full.png"] + [f"user_section_{i:02d}.png" for i in range(1, 16)],
            "admin_html": ["admin_full.png"] + [f"admin_section_{i:02d}.png" for i in range(1, 16)],
            "user_pdf":   [f"user_pdf_page_{i:02d}.png" for i in range(1, 77)],
            "admin_pdf":  [f"admin_pdf_page_{i:02d}.png" for i in range(1, 77)],
        }
        run_id = _make_gen_run_shape(cp, ss_pngs=ss_pngs)
        resp = _del_run(client, run_id)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
        body = json.loads(resp.data)
        assert body["ok"] is True and body["deleted"] is True


# ── DEL-BOUND-4: Generator-shaped run with 201 entries → REFUSED, rmtree=0 ───

def test_DEL_BOUND_entries_201_refused():
    """A Generator-shaped run with a 77th admin_pdf PNG must be REFUSED; shutil.rmtree must not be called.

    Entry breakdown: 16 base + 16+16+76+77 PNGs = 201 entries attempted.
    admin_pdf_page_77.png is beyond the Generator cap (76); refusal occurs at the regex allowlist check.
    """
    with mock.patch("shutil.rmtree") as mock_rmtree:
        with _client_ctx() as (client, tmpdir):
            cp = _case_path(tmpdir)
            ss_pngs = {
                "user_html":  ["user_full.png"] + [f"user_section_{i:02d}.png" for i in range(1, 16)],
                "admin_html": ["admin_full.png"] + [f"admin_section_{i:02d}.png" for i in range(1, 16)],
                "user_pdf":   [f"user_pdf_page_{i:02d}.png" for i in range(1, 77)],
                "admin_pdf":  [f"admin_pdf_page_{i:02d}.png" for i in range(1, 78)],
            }
            run_id = _make_gen_run_shape(cp, ss_pngs=ss_pngs)
            resp = _del_run(client, run_id)
            assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.data}"
            body = json.loads(resp.data)
            assert body["error"] == "RUN_DELETE_REFUSED"
            assert mock_rmtree.call_count == 0, (
                f"shutil.rmtree must not be called on refused delete; "
                f"got {mock_rmtree.call_count} calls"
            )


# ── UNKNOWN-1..7: Generator-derived allowlist rejects unknown elements ─────────

def test_UNKNOWN_1_unexpected_root_file():
    """Unexpected file at run root → REFUSED_UNKNOWN_STRUCTURE; shutil.rmtree must not be called."""
    with mock.patch("shutil.rmtree") as mock_rmtree:
        with _client_ctx() as (client, tmpdir):
            cp = _case_path(tmpdir)
            run_id = _make_gen_run_shape(cp)
            (cp / run_id / "foreign.txt").write_bytes(b"bad")
            resp = _del_run(client, run_id)
            assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.data}"
            assert json.loads(resp.data)["error"] == "RUN_DELETE_REFUSED"
            assert mock_rmtree.call_count == 0


def test_UNKNOWN_2_unexpected_root_directory():
    """Unexpected directory at run root → REFUSED_UNKNOWN_STRUCTURE; shutil.rmtree must not be called."""
    with mock.patch("shutil.rmtree") as mock_rmtree:
        with _client_ctx() as (client, tmpdir):
            cp = _case_path(tmpdir)
            run_id = _make_gen_run_shape(cp)
            (cp / run_id / "backup").mkdir()
            resp = _del_run(client, run_id)
            assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.data}"
            assert json.loads(resp.data)["error"] == "RUN_DELETE_REFUSED"
            assert mock_rmtree.call_count == 0


def test_UNKNOWN_3_unexpected_artifacts_file():
    """Unexpected file in artifacts/ → REFUSED_UNKNOWN_STRUCTURE; shutil.rmtree must not be called."""
    with mock.patch("shutil.rmtree") as mock_rmtree:
        with _client_ctx() as (client, tmpdir):
            cp = _case_path(tmpdir)
            run_id = _make_gen_run_shape(cp)
            (cp / run_id / "artifacts" / "unexpected.bin").write_bytes(b"bad")
            resp = _del_run(client, run_id)
            assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.data}"
            assert json.loads(resp.data)["error"] == "RUN_DELETE_REFUSED"
            assert mock_rmtree.call_count == 0


def test_UNKNOWN_4_unexpected_audits_file():
    """Unexpected file in audits/ → REFUSED_UNKNOWN_STRUCTURE; shutil.rmtree must not be called."""
    with mock.patch("shutil.rmtree") as mock_rmtree:
        with _client_ctx() as (client, tmpdir):
            cp = _case_path(tmpdir)
            run_id = _make_gen_run_shape(cp)
            (cp / run_id / "audits" / "extra.json").write_bytes(b"{}")
            resp = _del_run(client, run_id)
            assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.data}"
            assert json.loads(resp.data)["error"] == "RUN_DELETE_REFUSED"
            assert mock_rmtree.call_count == 0


def test_UNKNOWN_5_unexpected_screenshot_category():
    """Unexpected directory in screenshots/ → REFUSED_UNKNOWN_STRUCTURE; shutil.rmtree must not be called."""
    with mock.patch("shutil.rmtree") as mock_rmtree:
        with _client_ctx() as (client, tmpdir):
            cp = _case_path(tmpdir)
            run_id = _make_gen_run_shape(cp)
            (cp / run_id / "screenshots" / "unknown-category").mkdir()
            resp = _del_run(client, run_id)
            assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.data}"
            assert json.loads(resp.data)["error"] == "RUN_DELETE_REFUSED"
            assert mock_rmtree.call_count == 0


def test_UNKNOWN_6_unexpected_screenshot_extension():
    """Unexpected file extension in screenshot category → REFUSED_UNKNOWN_STRUCTURE; rmtree=0."""
    with mock.patch("shutil.rmtree") as mock_rmtree:
        with _client_ctx() as (client, tmpdir):
            cp = _case_path(tmpdir)
            run_id = _make_gen_run_shape(cp)
            (cp / run_id / "screenshots" / "user_html" / "image.jpg").write_bytes(b"JFIF")
            resp = _del_run(client, run_id)
            assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.data}"
            assert json.loads(resp.data)["error"] == "RUN_DELETE_REFUSED"
            assert mock_rmtree.call_count == 0


def test_UNKNOWN_7_unexpected_nested_screenshot_directory():
    """Nested directory inside screenshot category → REFUSED_UNKNOWN_STRUCTURE; shutil.rmtree must not be called."""
    with mock.patch("shutil.rmtree") as mock_rmtree:
        with _client_ctx() as (client, tmpdir):
            cp = _case_path(tmpdir)
            run_id = _make_gen_run_shape(cp)
            (cp / run_id / "screenshots" / "admin_html" / "nested").mkdir()
            resp = _del_run(client, run_id)
            assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.data}"
            assert json.loads(resp.data)["error"] == "RUN_DELETE_REFUSED"
            assert mock_rmtree.call_count == 0


# ── RET-SKIP-1: oldest refused, second-oldest deleted → generator called, 200 ──

def test_RET_SKIP_REFUSED_second_oldest_deleted():
    """Skip-refused algorithm: oldest run is REFUSED; algorithm skips it, deletes second-oldest → 200."""
    gen_calls: list = []

    def _counting_gen(*, output_root, run_id, case_id=_CID, overwrite=False):
        gen_calls.append(run_id)
        return _default_fake_gen()(
            output_root=output_root, run_id=run_id, case_id=case_id, overwrite=overwrite,
        )

    with _client_ctx(gen_fn=_counting_gen) as (client, tmpdir):
        cp = _case_path(tmpdir)
        _create_completed_run(cp, _iso(10000), deletable=False)  # oldest: REFUSED
        for i in range(9):
            _create_completed_run(cp, _iso(9000 - i * 500))  # 9 deletable runs

        resp = _do_post(client)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
        assert len(gen_calls) == 1, f"Expected 1 generator call, got {len(gen_calls)}"


# ── SS-BOUND-1..12: Screenshot filename boundary tests (tightened Generator-derived regex) ───


def test_SS_BOUND_UH_section_15_accepted():
    """user_html/user_section_15.png (highest valid index) must be accepted → DELETED."""
    with _client_ctx() as (client, tmpdir):
        cp = _case_path(tmpdir)
        run_id = _make_gen_run_shape(cp, ss_pngs={
            "user_html": ["user_section_15.png", "user_full.png"],
        })
        resp = _del_run(client, run_id)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
        assert json.loads(resp.data)["deleted"] is True


def test_SS_BOUND_UH_section_16_refused():
    """user_html/user_section_16.png (one over max) must refuse → 409; rmtree=0."""
    with mock.patch("shutil.rmtree") as mock_rmtree:
        with _client_ctx() as (client, tmpdir):
            cp = _case_path(tmpdir)
            run_id = _make_gen_run_shape(cp)
            (cp / run_id / "screenshots" / "user_html" / "user_section_16.png").write_bytes(b"\x89PNG\r\n")
            resp = _del_run(client, run_id)
            assert resp.status_code == 409
            assert json.loads(resp.data)["error"] == "RUN_DELETE_REFUSED"
            assert mock_rmtree.call_count == 0


def test_SS_BOUND_UH_section_00_refused():
    """user_html/user_section_00.png (below minimum) must refuse → 409; rmtree=0."""
    with mock.patch("shutil.rmtree") as mock_rmtree:
        with _client_ctx() as (client, tmpdir):
            cp = _case_path(tmpdir)
            run_id = _make_gen_run_shape(cp)
            (cp / run_id / "screenshots" / "user_html" / "user_section_00.png").write_bytes(b"\x89PNG\r\n")
            resp = _del_run(client, run_id)
            assert resp.status_code == 409
            assert json.loads(resp.data)["error"] == "RUN_DELETE_REFUSED"
            assert mock_rmtree.call_count == 0


def test_SS_BOUND_AH_section_15_accepted():
    """admin_html/admin_section_15.png (highest valid index) must be accepted → DELETED."""
    with _client_ctx() as (client, tmpdir):
        cp = _case_path(tmpdir)
        run_id = _make_gen_run_shape(cp, ss_pngs={
            "admin_html": ["admin_section_15.png", "admin_full.png"],
        })
        resp = _del_run(client, run_id)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
        assert json.loads(resp.data)["deleted"] is True


def test_SS_BOUND_AH_section_16_refused():
    """admin_html/admin_section_16.png (one over max) must refuse → 409; rmtree=0."""
    with mock.patch("shutil.rmtree") as mock_rmtree:
        with _client_ctx() as (client, tmpdir):
            cp = _case_path(tmpdir)
            run_id = _make_gen_run_shape(cp)
            (cp / run_id / "screenshots" / "admin_html" / "admin_section_16.png").write_bytes(b"\x89PNG\r\n")
            resp = _del_run(client, run_id)
            assert resp.status_code == 409
            assert json.loads(resp.data)["error"] == "RUN_DELETE_REFUSED"
            assert mock_rmtree.call_count == 0


def test_SS_BOUND_AH_section_00_refused():
    """admin_html/admin_section_00.png (below minimum) must refuse → 409; rmtree=0."""
    with mock.patch("shutil.rmtree") as mock_rmtree:
        with _client_ctx() as (client, tmpdir):
            cp = _case_path(tmpdir)
            run_id = _make_gen_run_shape(cp)
            (cp / run_id / "screenshots" / "admin_html" / "admin_section_00.png").write_bytes(b"\x89PNG\r\n")
            resp = _del_run(client, run_id)
            assert resp.status_code == 409
            assert json.loads(resp.data)["error"] == "RUN_DELETE_REFUSED"
            assert mock_rmtree.call_count == 0


def test_SS_BOUND_UP_page_76_accepted():
    """user_pdf/user_pdf_page_76.png (highest Generator-capped page) must be accepted → DELETED."""
    with _client_ctx() as (client, tmpdir):
        cp = _case_path(tmpdir)
        run_id = _make_gen_run_shape(cp, ss_pngs={
            "user_pdf": ["user_pdf_page_76.png"],
        })
        resp = _del_run(client, run_id)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
        assert json.loads(resp.data)["deleted"] is True


def test_SS_BOUND_UP_page_77_refused():
    """user_pdf/user_pdf_page_77.png (one beyond Generator cap of 76) must refuse → 409; rmtree=0."""
    with mock.patch("shutil.rmtree") as mock_rmtree:
        with _client_ctx() as (client, tmpdir):
            cp = _case_path(tmpdir)
            run_id = _make_gen_run_shape(cp)
            (cp / run_id / "screenshots" / "user_pdf" / "user_pdf_page_77.png").write_bytes(b"\x89PNG\r\n")
            resp = _del_run(client, run_id)
            assert resp.status_code == 409
            assert json.loads(resp.data)["error"] == "RUN_DELETE_REFUSED"
            assert mock_rmtree.call_count == 0


def test_SS_BOUND_UP_page_00_refused():
    """user_pdf/user_pdf_page_00.png (zero page) must refuse → 409; rmtree=0."""
    with mock.patch("shutil.rmtree") as mock_rmtree:
        with _client_ctx() as (client, tmpdir):
            cp = _case_path(tmpdir)
            run_id = _make_gen_run_shape(cp)
            (cp / run_id / "screenshots" / "user_pdf" / "user_pdf_page_00.png").write_bytes(b"\x89PNG\r\n")
            resp = _del_run(client, run_id)
            assert resp.status_code == 409
            assert json.loads(resp.data)["error"] == "RUN_DELETE_REFUSED"
            assert mock_rmtree.call_count == 0


def test_SS_BOUND_AP_page_76_accepted():
    """admin_pdf/admin_pdf_page_76.png (highest Generator-capped page) must be accepted → DELETED."""
    with _client_ctx() as (client, tmpdir):
        cp = _case_path(tmpdir)
        run_id = _make_gen_run_shape(cp, ss_pngs={
            "admin_pdf": ["admin_pdf_page_76.png"],
        })
        resp = _del_run(client, run_id)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
        assert json.loads(resp.data)["deleted"] is True


def test_SS_BOUND_AP_page_77_refused():
    """admin_pdf/admin_pdf_page_77.png (one beyond Generator cap of 76) must refuse → 409; rmtree=0."""
    with mock.patch("shutil.rmtree") as mock_rmtree:
        with _client_ctx() as (client, tmpdir):
            cp = _case_path(tmpdir)
            run_id = _make_gen_run_shape(cp)
            (cp / run_id / "screenshots" / "admin_pdf" / "admin_pdf_page_77.png").write_bytes(b"\x89PNG\r\n")
            resp = _del_run(client, run_id)
            assert resp.status_code == 409
            assert json.loads(resp.data)["error"] == "RUN_DELETE_REFUSED"
            assert mock_rmtree.call_count == 0


def test_SS_BOUND_AP_page_00_refused():
    """admin_pdf/admin_pdf_page_00.png (zero page) must refuse → 409; rmtree=0."""
    with mock.patch("shutil.rmtree") as mock_rmtree:
        with _client_ctx() as (client, tmpdir):
            cp = _case_path(tmpdir)
            run_id = _make_gen_run_shape(cp)
            (cp / run_id / "screenshots" / "admin_pdf" / "admin_pdf_page_00.png").write_bytes(b"\x89PNG\r\n")
            resp = _del_run(client, run_id)
            assert resp.status_code == 409
            assert json.loads(resp.data)["error"] == "RUN_DELETE_REFUSED"
            assert mock_rmtree.call_count == 0


# ── PARTIAL-1..8: Partial-run rollback safety tests ───────────────────────────


def test_PARTIAL_1_empty_run_dir_deleted():
    """Empty run directory (interrupted before Generator creates anything) → DELETED."""
    with _client_ctx() as (client, tmpdir):
        cp = _case_path(tmpdir)
        run_id = _make_partial_run(cp, [], {})
        resp = _del_run(client, run_id)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
        assert json.loads(resp.data)["deleted"] is True


def test_PARTIAL_2_only_artifacts_dir_deleted():
    """Run with only empty artifacts/ directory (Generator created dirs but no files) → DELETED."""
    with _client_ctx() as (client, tmpdir):
        cp = _case_path(tmpdir)
        run_id = _make_partial_run(cp, ["artifacts"], {})
        resp = _del_run(client, run_id)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
        assert json.loads(resp.data)["deleted"] is True


def test_PARTIAL_3_one_approved_artifact_deleted():
    """Run with one approved artifact file (interrupted mid-generation) → DELETED."""
    with _client_ctx() as (client, tmpdir):
        cp = _case_path(tmpdir)
        run_id = _make_partial_run(cp, [], {
            f"artifacts/compliance_v2_{_CID}_user.html": b"<html/>",
        })
        resp = _del_run(client, run_id)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
        assert json.loads(resp.data)["deleted"] is True


def test_PARTIAL_4_only_audits_dir_deleted():
    """Run with only empty audits/ directory → DELETED."""
    with _client_ctx() as (client, tmpdir):
        cp = _case_path(tmpdir)
        run_id = _make_partial_run(cp, ["audits"], {})
        resp = _del_run(client, run_id)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
        assert json.loads(resp.data)["deleted"] is True


def test_PARTIAL_5_one_approved_audit_deleted():
    """Run with one approved audit JSON file → DELETED."""
    with _client_ctx() as (client, tmpdir):
        cp = _case_path(tmpdir)
        run_id = _make_partial_run(cp, [], {
            "audits/compliance_v2_visual_qa_report.json": b"{}",
        })
        resp = _del_run(client, run_id)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
        assert json.loads(resp.data)["deleted"] is True


def test_PARTIAL_6_only_screenshots_dir_deleted():
    """Run with only empty screenshots/ directory → DELETED."""
    with _client_ctx() as (client, tmpdir):
        cp = _case_path(tmpdir)
        run_id = _make_partial_run(cp, ["screenshots"], {})
        resp = _del_run(client, run_id)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
        assert json.loads(resp.data)["deleted"] is True


def test_PARTIAL_7_one_approved_screenshot_category_deleted():
    """Run with one approved empty screenshot category → DELETED."""
    with _client_ctx() as (client, tmpdir):
        cp = _case_path(tmpdir)
        run_id = _make_partial_run(cp, ["screenshots/user_html"], {})
        resp = _del_run(client, run_id)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
        assert json.loads(resp.data)["deleted"] is True


def test_PARTIAL_8_one_approved_png_deleted():
    """Run with one approved PNG file (category + single screenshot) → DELETED."""
    with _client_ctx() as (client, tmpdir):
        cp = _case_path(tmpdir)
        run_id = _make_partial_run(cp, [], {
            "screenshots/user_html/user_section_01.png": b"\x89PNG\r\n",
        })
        resp = _del_run(client, run_id)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
        assert json.loads(resp.data)["deleted"] is True
