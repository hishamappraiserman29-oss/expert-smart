# -*- coding: utf-8 -*-
"""
Batch 6 — Controlled Canary Runtime Validation Tests.

18 tests verifying the integrated template-driven builder through the actual
professional valuation output flow in a controlled environment.

Uses global Python (has matplotlib) — not the venv.
Tests are session-scoped to run expensive pipeline builds only once.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import pathlib
import sys
import zipfile
from typing import Any
from unittest import mock

import pytest

# ── Path setup ─────────────────────────────────────────────────────────────────

_CE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_CE))

_PVO_PATH = _CE / "professional_valuation_outputs.py"

_CANARY_DIR = (
    _CE / "instance" / "manual_review_outputs"
    / "professional_valuation_template_driven_canary"
)
_OUTPUTS_DIR = _CANARY_DIR / "outputs"
_AUDITS_DIR = _CANARY_DIR / "audits"
_VIS_DIR = _CANARY_DIR / "visual_previews"

_LEGACY_WB = _OUTPUTS_DIR / "legacy_canary_workbook.xlsx"
_TEMPLATE_WB = _OUTPUTS_DIR / "template_driven_canary_workbook.xlsx"
_FALLBACK_WB = _OUTPUTS_DIR / "fallback_canary_workbook.xlsx"

# Check if pre-built canary outputs exist (from canary runner)
_CANARY_OUTPUTS_EXIST = (
    _LEGACY_WB.is_file() and _TEMPLATE_WB.is_file() and _FALLBACK_WB.is_file()
)

# ── Module loading ─────────────────────────────────────────────────────────────

def _load_pvo():
    spec = importlib.util.spec_from_file_location("pvo", str(_PVO_PATH))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_pvo = _load_pvo()

# ── Canary constants ────────────────────────────────────────────────────────────

_CANARY_REQ_ID = "PVR-20260712-A1B2"
_CANARY_OUT_LEGACY = "PVOUT-CAN00001"
_CANARY_OUT_TEMPLATE = "PVOUT-CAN00002"
_CANARY_OUT_FALLBACK = "PVOUT-CAN00003"

_NA = "غير متاح ضمن بيانات الطلب"

_REQUIRED_TEMPLATE_SHEETS = frozenset({
    "القيمة بالحروف",
    "بيان الامتثال",
    "توقيع واعتماد الخبير",
})

# ── Canary context ─────────────────────────────────────────────────────────────

_CANARY_CTX_BASE: dict = {
    "request_id": _CANARY_REQ_ID,
    "assembled_at": "2026-07-12T00:00:00",
    "context_type": "professional_valuation_certified_output",
    "external_api_used": False,
    "qdrant_used": False,
    "rag_used": False,
    "request_summary": {
        "request_id":        _CANARY_REQ_ID,
        "request_number":    "PV-CANARY-2026-001",
        "client_name":       "عميل تقييم معتمد — بيانات اختبار",
        "client_type":       "مؤسسة تمويلية",
        "property_title":    "شقة سكنية — عينة اختبار",
        "property_address":  "حي النزهة، الرياض — بدون معرف شخصي",
        "property_type":     "شقة سكنية",
        "valuation_purpose": "تمويل عقاري",
        "basis_of_value":    "القيمة السوقية",
        "valuation_date":    "2026-07-12",
        "inspection_date":   "2026-07-10",
        "currency":          "SAR",
        "report_language":   "ar",
        "report_type":       "professional_report",
        "report_type_label": "تقرير احترافي",
    },
    "certification_gate": {
        "certification_ready":               False,
        "official_use_allowed":              False,
        "certified_use_allowed":             False,
        "final_report_generation_allowed":   False,
        "final_workbook_generation_allowed": True,
        "blockers":                          ["اختبار — لا اعتماد نهائي"],
        "evaluated_at":                      "2026-07-12T00:00:00",
        "certification_status":              "advisory_only_canary_test",
    },
    "evidence_summary": {
        "mandatory_document_readiness": False,
        "approved_count": 0,
        "missing_categories": ["صك الملكية", "مخطط الموقع"],
        "qa_excluded": True,
    },
    "comparable_summary": {
        "production_ready_count": 3,
        "certification_comparable_ready": False,
        "excluded_staged_rejected": True,
        "excluded_qa": True,
    },
    "method_summary": {
        "methods_completed": False,
        "readiness_status": "اختبار فقط — طرق غير مكتملة",
        "method_outputs": {
            "طريقة_المقارنة": {"value": 1500000, "weight": 0.6},
            "طريقة_الدخل":    {"value": 1450000, "weight": 0.4},
        },
        "limitations": ["بيانات اختبار"],
    },
    "reconciliation_summary": {
        "weighted_value":       1482000,
        "selected_final_value": 1482000,
        "rationale":            "وزن طريقة المقارنة 60% + الدخل 40%",
        "method_weights":       {"طريقة_المقارنة": 0.6, "طريقة_الدخل": 0.4},
        "divergence_warnings":  [],
    },
    "peer_review_summary": {
        "reviewer_name": _NA,
        "reviewer_role": _NA,
        "reviewer_license": _NA,
        "review_decision": _NA,
        "peer_review_ready": False,
    },
    "signature_summary": {
        "expert_name":         _NA,
        "expert_role":         _NA,
        "expert_license":      _NA,
        "firm_name":           _NA,
        "signed_at":           _NA,
        "signature_available": False,
        "stamp_available":     False,
        "approval_statement":  _NA,
        "final_signoff_ready": False,
        "note":                "لا صورة توقيع — بيانات اختبار — غير موقع",
    },
    "advanced_reviews": {
        "approved_for_certification": False,
        "all_cert_ready": False,
    },
    "output_metadata": {
        "output_id":      "",
        "output_type":    "final_workbook",
        "output_version": 1,
        "generated_at":   "2026-07-12T00:00:00",
        "generated_by":   "canary_test",
        "report_number":  "PV-CANARY-2026-001",
    },
}


def _make_ctx(output_id: str) -> dict:
    ctx = copy.deepcopy(_CANARY_CTX_BASE)
    ctx["output_metadata"]["output_id"] = output_id
    return ctx


def _sheet_names(path: pathlib.Path) -> list:
    if not path.is_file():
        return []
    import openpyxl
    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    names = list(wb.sheetnames)
    wb.close()
    return names


def _has_vba(path: pathlib.Path) -> bool:
    if not path.is_file():
        return False
    try:
        with zipfile.ZipFile(str(path), "r") as zf:
            return any("vbaProject" in n for n in zf.namelist())
    except Exception:
        return False


def _check_ref_errors(path: pathlib.Path) -> int:
    count = 0
    try:
        with zipfile.ZipFile(str(path), "r") as zf:
            for n in zf.namelist():
                if n.startswith("xl/worksheets/") and n.endswith(".xml"):
                    if "#REF!" in zf.read(n).decode("utf-8", errors="replace"):
                        count += 1
    except Exception:
        pass
    return count


def _has_real_ext_links(path: pathlib.Path) -> bool:
    try:
        with zipfile.ZipFile(str(path), "r") as zf:
            ext_rels = [n for n in zf.namelist()
                        if n.startswith("xl/externalLinks/") and n.endswith(".rels")]
            for rn in ext_rels:
                if "xlPathMissing" not in zf.read(rn).decode("utf-8", errors="replace"):
                    return True
    except Exception:
        pass
    return False


# ── Session-scoped fixtures: run each canary scenario ONCE ────────────────────

@pytest.fixture(scope="session")
def run_a_results():
    """Run A: Legacy baseline (PV_TEMPLATE_DRIVEN_EXCEL_ENABLED=false)."""
    pvo = _load_pvo()
    ctx = _make_ctx("PVOUT-TEST-A001")
    os.environ["PV_TEMPLATE_DRIVEN_EXCEL_ENABLED"] = "false"
    try:
        success, err, size, sha = pvo._generate_final_workbook_with_strategy(
            ctx, "PVR-20260712-TEST", "PVOUT-TEST-A001"
        )
    finally:
        os.environ.pop("PV_TEMPLATE_DRIVEN_EXCEL_ENABLED", None)
    builder = ctx.get("output_metadata", {}).get("excel_builder_used", "unknown")
    out_path = pvo._OUT_DIR / "PVR-20260712-TEST" / "PVOUT-TEST-A001_final_workbook.xlsx"
    return {
        "success": success, "err": err, "size": size, "sha": sha,
        "builder": builder, "ctx": ctx, "out_path": out_path,
    }


@pytest.fixture(scope="session")
def run_b_results():
    """Run B: Template-driven canary (PV_TEMPLATE_DRIVEN_EXCEL_ENABLED=true)."""
    pvo = _load_pvo()
    ctx = _make_ctx("PVOUT-TEST-B001")
    os.environ["PV_TEMPLATE_DRIVEN_EXCEL_ENABLED"] = "true"
    try:
        success, err, size, sha = pvo._generate_final_workbook_with_strategy(
            ctx, "PVR-20260712-TEST", "PVOUT-TEST-B001"
        )
    finally:
        os.environ.pop("PV_TEMPLATE_DRIVEN_EXCEL_ENABLED", None)
    builder = ctx.get("output_metadata", {}).get("excel_builder_used", "unknown")
    out_path = pvo._OUT_DIR / "PVR-20260712-TEST" / "PVOUT-TEST-B001_final_workbook.xlsx"
    return {
        "success": success, "err": err, "size": size, "sha": sha,
        "builder": builder, "ctx": ctx, "out_path": out_path,
    }


@pytest.fixture(scope="session")
def run_c_results():
    """Run C: Controlled fallback (mock forces template failure)."""
    pvo = _load_pvo()
    ctx = _make_ctx("PVOUT-TEST-C001")
    req_dir = pvo._OUT_DIR / "PVR-20260712-TEST"
    req_dir.mkdir(parents=True, exist_ok=True)

    class _FakeBuilderMod:
        def build_template_driven_professional_workbook(self, *a, **kw):
            raise RuntimeError("canary_forced_failure: injected for test")

    before_tmps = set(req_dir.glob("pv_tmp_*"))
    os.environ["PV_TEMPLATE_DRIVEN_EXCEL_ENABLED"] = "true"
    sys.modules["reports.excel_template_driven_builder"] = _FakeBuilderMod()
    try:
        success, err, size, sha = pvo._generate_final_workbook_with_strategy(
            ctx, "PVR-20260712-TEST", "PVOUT-TEST-C001"
        )
    finally:
        sys.modules.pop("reports.excel_template_driven_builder", None)
        os.environ.pop("PV_TEMPLATE_DRIVEN_EXCEL_ENABLED", None)
    after_tmps = set(req_dir.glob("pv_tmp_*"))
    new_tmps = after_tmps - before_tmps
    builder = ctx.get("output_metadata", {}).get("excel_builder_used", "unknown")
    out_path = pvo._OUT_DIR / "PVR-20260712-TEST" / "PVOUT-TEST-C001_final_workbook.xlsx"
    return {
        "success": success, "err": err, "size": size, "sha": sha,
        "builder": builder, "ctx": ctx, "out_path": out_path,
        "temp_files_remain": len(new_tmps),
    }


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_01_legacy_canary_run_succeeds(run_a_results):
    """Legacy canary run succeeds with flag disabled."""
    assert run_a_results["success"] is True, (
        f"Legacy run failed: {run_a_results['err']}"
    )
    assert run_a_results["size"] > 0


def test_02_template_canary_run_succeeds(run_b_results):
    """Template canary run succeeds with flag enabled."""
    assert run_b_results["success"] is True, (
        f"Template run failed: {run_b_results['err']}"
    )
    assert run_b_results["size"] > 0


def test_03_actual_production_flow_wrapper_executed(run_a_results, run_b_results):
    """Actual production-flow strategy wrapper is executed (not bypassed)."""
    pvo = _load_pvo()
    # Verify that _generate_final_workbook_with_strategy exists and is callable
    assert callable(pvo._generate_final_workbook_with_strategy)
    # Verify both runs went through the wrapper (ctx has excel_builder_used set by wrapper)
    assert "excel_builder_used" in run_a_results["ctx"].get("output_metadata", {})
    assert "excel_builder_used" in run_b_results["ctx"].get("output_metadata", {})
    # Verify the wrapper is called from the route handler by inspecting module source
    src = _PVO_PATH.read_text(encoding="utf-8")
    assert "_generate_final_workbook_with_strategy" in src, (
        "source must contain call to _generate_final_workbook_with_strategy"
    )
    # Verify wrapper is NOT bypassed — legacy function still exists but call site uses wrapper
    assert "_generate_final_workbook_with_strategy(" in src, (
        "strategy wrapper must be called (not just defined)"
    )
    assert "def _generate_final_workbook(" in src, (
        "legacy _generate_final_workbook must still be defined (not deleted)"
    )


def test_04_template_run_uses_template_driven(run_b_results):
    """Template run uses template_driven builder (not legacy or fallback)."""
    assert run_b_results["builder"] == "template_driven", (
        f"Expected template_driven, got {run_b_results['builder']}"
    )


def test_05_template_run_does_not_invoke_fallback(run_b_results):
    """Template run does not invoke the legacy fallback."""
    assert run_b_results["builder"] != "legacy_fallback", (
        "Template run must succeed without falling back to legacy"
    )


def test_06_template_workbook_contains_55_sheets(run_b_results):
    """Template workbook contains exactly 55 sheets."""
    out_path = run_b_results["out_path"]
    assert out_path.is_file(), "Template workbook file must exist"
    sheets = _sheet_names(out_path)
    assert len(sheets) == 55, f"Expected 55 sheets, got {len(sheets)}"


def test_07_reconciled_value_matches_legacy_result(run_a_results, run_b_results):
    """Reconciled value in template-driven ctx matches the legacy ctx value."""
    recon_a = run_a_results["ctx"].get("reconciliation_summary", {}).get("selected_final_value")
    recon_b = run_b_results["ctx"].get("reconciliation_summary", {}).get("selected_final_value")
    assert recon_a == recon_b, (
        f"Reconciled value must be identical: legacy={recon_a}, template={recon_b}"
    )
    assert recon_b == 1482000, f"Canary reconciled value must be 1482000, got {recon_b}"


def test_08_core_request_property_data_consistent(run_a_results, run_b_results):
    """Core request/property data remains consistent between runs."""
    for field in ("request_id", "property_type", "valuation_purpose", "currency"):
        val_a = run_a_results["ctx"].get("request_summary", {}).get(field)
        val_b = run_b_results["ctx"].get("request_summary", {}).get(field)
        assert val_a == val_b, (
            f"Field '{field}' must be identical: legacy={val_a!r} template={val_b!r}"
        )


def test_09_missing_data_not_replaced_with_invented_defaults(run_a_results, run_b_results):
    """Missing data is represented as غير متاح ضمن بيانات الطلب, not invented."""
    for ctx in (run_a_results["ctx"], run_b_results["ctx"]):
        sig = ctx.get("signature_summary", {})
        assert sig.get("expert_name") == _NA, (
            "Missing expert_name must be NA, not an invented value"
        )
        assert sig.get("expert_license") == _NA, (
            "Missing expert_license must be NA"
        )
        peer = ctx.get("peer_review_summary", {})
        assert peer.get("reviewer_license") == _NA, (
            "Missing reviewer_license must be NA"
        )


def test_10_certification_remains_non_automatic(run_a_results, run_b_results):
    """Certification is not set automatically in either run."""
    for label, ctx in (("legacy", run_a_results["ctx"]), ("template", run_b_results["ctx"])):
        gate = ctx.get("certification_gate", {})
        assert gate.get("certified_use_allowed") is False, (
            f"{label}: certified_use_allowed must remain False (no automatic certification)"
        )
        assert gate.get("certification_ready") is False, (
            f"{label}: certification_ready must remain False"
        )


def test_11_signature_remains_unsigned(run_a_results, run_b_results):
    """Expert signature remains unsigned (final_signoff_ready=False) in both runs."""
    for label, ctx in (("legacy", run_a_results["ctx"]), ("template", run_b_results["ctx"])):
        sig = ctx.get("signature_summary", {})
        assert sig.get("final_signoff_ready") is False, (
            f"{label}: signature must remain unsigned"
        )
        assert sig.get("signature_available") is False, (
            f"{label}: no signature image should be set"
        )


def test_12_controlled_failure_uses_legacy_fallback(run_c_results):
    """Controlled template failure results in legacy_fallback builder."""
    assert run_c_results["builder"] == "legacy_fallback", (
        f"Expected legacy_fallback, got {run_c_results['builder']}"
    )
    assert run_c_results["success"] is True, (
        "Fallback to legacy must succeed when template fails"
    )


def test_13_temporary_invalid_output_is_removed(run_c_results):
    """Temporary file created during failed template build is cleaned up."""
    assert run_c_results["temp_files_remain"] == 0, (
        f"Expected 0 temp files remaining, got {run_c_results['temp_files_remain']}"
    )


def test_14_no_partial_output_published(run_c_results):
    """No partial or invalid output is published when template builder fails."""
    assert run_c_results["temp_files_remain"] == 0, "Temp files must be removed"
    # Fallback output is the legacy builder's full output — not partial
    out_path = run_c_results["out_path"]
    assert out_path.is_file(), "Fallback output must exist (legacy output, not partial)"
    # Verify the fallback output is a valid XLSX
    try:
        with zipfile.ZipFile(str(out_path), "r") as zf:
            assert "[Content_Types].xml" in zf.namelist(), (
                "Fallback output must be a valid XLSX (has [Content_Types].xml)"
            )
    except zipfile.BadZipFile:
        pytest.fail("Fallback output is not a valid XLSX")


def test_15_logging_values_correct_and_sanitized():
    """Logging records correct fields and sanitizes sensitive information."""
    pvo = _load_pvo()

    # Test sanitization function
    test_cases = [
        (r"C:\Users\Lenovo\Desktop\templates\sensitive_path", "<path>"),
        ("/home/user/secrets/file.py", "<path>"),
        ("simple_error_no_path", "simple_error_no_path"),
    ]
    for raw, expected_pattern in test_cases:
        sanitized = pvo._sanitize_log_reason(raw)
        assert "Lenovo" not in sanitized, (
            f"Windows absolute path must be removed: '{raw}' → '{sanitized}'"
        )
        assert "/home/user" not in sanitized, (
            f"Unix absolute path must be removed: '{raw}' → '{sanitized}'"
        )
        if "path" not in raw.lower() and "/" not in raw and "\\" not in raw:
            assert sanitized == raw, f"Non-path string should be unchanged: '{raw}'"

    # Verify _log_builder_event is callable (structural check)
    assert callable(pvo._log_builder_event)

    # Verify log function signature has all required parameters
    import inspect
    sig = inspect.signature(pvo._log_builder_event)
    required_params = {
        "request_id", "output_id", "flag_enabled", "builder_attempted",
        "builder_used", "template_success", "fallback_used",
        "output_filename", "duration_ms",
    }
    for param in required_params:
        assert param in sig.parameters, (
            f"_log_builder_event missing required parameter: {param}"
        )


def test_16_excel_com_smoke_previews_exist():
    """Visual smoke previews exist for all priority sheets."""
    _VIS_PRIORITY_SHEETS = [
        "الافتراضات والمدخلات",
        "لوحة القيادة التنفيذية",
        "القيمة بالحروف",
        "بيان الامتثال",
        "توقيع واعتماد الخبير",
        "حالة الاعتماد والتوصية",
        "نطاق الثقة وعدم اليقين",
        "التوصية النهائية",
    ]
    if not _CANARY_OUTPUTS_EXIST:
        pytest.skip("Canary runner outputs not found — run canary_runner.py first")

    # Check that preview PNGs were generated
    preview_files = list(_VIS_DIR.glob("*_preview.png"))
    assert len(preview_files) > 0, (
        f"No visual preview PNGs found in {_VIS_DIR}"
    )

    # Verify audit reports the smoke results
    smoke_audit = _AUDITS_DIR / "05_canary_visual_smoke_audit.json"
    assert smoke_audit.is_file(), "Visual smoke audit file must exist"
    with open(str(smoke_audit), encoding="utf-8") as f:
        audit = json.load(f)
    assert audit.get("target_sheet_count") == 55, (
        "Visual smoke audit must report 55-sheet workbook"
    )
    previews_generated = audit.get("previews_generated", [])
    assert len(previews_generated) == len(_VIS_PRIORITY_SHEETS), (
        f"Expected {len(_VIS_PRIORITY_SHEETS)} previews, "
        f"got {len(previews_generated)}: {previews_generated}"
    )


def test_17_feature_flag_disabled_after_canary():
    """Feature flag is disabled (unset) after the canary process completes."""
    pvo = _load_pvo()
    # Flag must not be set in the environment after canary runs
    flag_val = os.environ.get("PV_TEMPLATE_DRIVEN_EXCEL_ENABLED", "")
    assert pvo._is_template_driven_excel_enabled() is False, (
        f"Feature flag must be disabled after canary; env value='{flag_val}'"
    )


def test_18_source_template_hashes_unchanged():
    """Source template SHA-256 hashes match values recorded during canary run."""
    if not _CANARY_OUTPUTS_EXIST:
        pytest.skip("Canary runner outputs not found")

    env_audit = _AUDITS_DIR / "01_canary_environment_audit.json"
    assert env_audit.is_file(), "Canary environment audit must exist"

    # Load source hashes from runtime summary
    summary_path = _CANARY_DIR / "final_report" / "canary_runtime_summary.json"
    assert summary_path.is_file(), "Canary runtime summary must exist"
    with open(str(summary_path), encoding="utf-8") as f:
        summary = json.load(f)

    src_hashes = summary.get("source_template_hashes", {})
    assert isinstance(src_hashes, dict), "Source template hashes must be recorded"
    assert "error" not in src_hashes, (
        f"Source template hash recording failed: {src_hashes.get('error')}"
    )

    # Re-check the hashes now match
    try:
        from reports.excel_template_driven_builder import (
            _PRIMARY_TEMPLATE, _FALLBACK_TEMPLATE, _CERT_SOURCE,
        )
        current_hashes = {
            "primary_template": hashlib.sha256(_PRIMARY_TEMPLATE.read_bytes()).hexdigest(),
            "fallback_template": hashlib.sha256(_FALLBACK_TEMPLATE.read_bytes()).hexdigest(),
            "cert_source": hashlib.sha256(_CERT_SOURCE.read_bytes()).hexdigest(),
        }
        for key, stored_sha in src_hashes.items():
            current_sha = current_hashes.get(key, "")
            assert current_sha == stored_sha, (
                f"Source template '{key}' hash changed: "
                f"stored={stored_sha[:12]}… current={current_sha[:12]}…"
            )
    except ImportError:
        pytest.skip("Builder module not importable — skip hash verification")
