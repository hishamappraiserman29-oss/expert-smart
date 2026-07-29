"""
test_mv_outputs.py — P10 tests: Outputs & Security (O-01, O-03, O-05, O-06).
Tests: OP-01 → OP-09
"""
import hashlib
import pytest

from core_engine.mass_valuation.output_builder import OutputBuilder
from core_engine.mass_valuation.audit_recorder import (
    build_audit_record,
    compute_artifact_hashes,
)


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

_RUN = {
    "run_id":                  "r-op-001",
    "run_name":                "P10 Test Run",
    "property_type":           "residential",
    "jurisdiction":            "SA-01",
    "status":                  "validated",
    "method":                  "avm",
    "n_predicted_properties":  1,
    "advisory_only":           True,
    "certification_ready":     False,
    "dataset_hash":            "a" * 64,
    "model_hash":              "b" * 64,
    "random_seed":             42,
    "audit_trail_id":          "audit-op-001",
    "predictions": [
        {
            "prediction_id":           "pred-op-001",
            "property_id":             "P-OP",
            "estimated_value":         2_000_000.0,
            "unit_value":              10_000.0,
            "prediction_interval_low": 1_800_000.0,
            "prediction_interval_high":2_200_000.0,
            "confidence":              0.85,
            "distribution_status":     "normal",
            "limitations":             [],
            "advisory_only":           True,
        }
    ],
}

_OB = OutputBuilder()


# ---------------------------------------------------------------------------
# OP-01 → OP-02  Excel export role gate (O-01)
# ---------------------------------------------------------------------------

def test_op_01_export_excel_raises_for_user_role():
    """O-01: export_excel must raise PermissionError for role='user'."""
    with pytest.raises(PermissionError, match="O-01"):
        _OB.export_excel(_RUN, role="user")


def test_op_02_export_excel_raises_for_analyst_role():
    """O-01: export_excel must raise PermissionError for role='analyst'."""
    with pytest.raises(PermissionError, match="O-01"):
        _OB.export_excel(_RUN, role="analyst")


def test_op_03_export_excel_allowed_for_admin():
    """O-01: export_excel must succeed for role='admin' and return bytes."""
    data = _OB.export_excel(_RUN, role="admin")
    assert isinstance(data, bytes)
    assert len(data) > 0


# ---------------------------------------------------------------------------
# OP-04 → OP-05  Admin HTML adm-marker (O-03)
# ---------------------------------------------------------------------------

def test_op_04_admin_html_contains_adm_marker():
    """O-03: Admin HTML must contain <div class="adm-marker"> wrapping admin sections."""
    html = _OB.export_html(_RUN, role="admin").decode("utf-8")
    assert '<div class="adm-marker">' in html, (
        "Admin HTML must contain at least one <div class=\"adm-marker\"> block"
    )


def test_op_05_user_html_has_no_adm_marker():
    """O-03: User HTML must not expose any adm-marker sections."""
    html = _OB.export_html(_RUN, role="user").decode("utf-8")
    assert "adm-marker" not in html, (
        "User HTML must not contain adm-marker — admin-only sections must be omitted"
    )


# ---------------------------------------------------------------------------
# OP-06  Artifact hashes match actual SHA-256 (O-05)
# ---------------------------------------------------------------------------

def test_op_06_artifact_hashes_match_sha256():
    """O-05: compute_artifact_hashes must produce SHA-256 digests matching the byte content."""
    html_bytes  = _OB.export_html(_RUN, role="admin")
    xlsx_bytes  = _OB.export_excel(_RUN, role="admin")

    hashes = compute_artifact_hashes({
        "report_admin.html": html_bytes,
        "report_admin.xlsx": xlsx_bytes,
    })

    assert len(hashes) == 2
    for name, digest in hashes.items():
        assert len(digest) == 64, f"{name}: expected 64-char SHA-256, got {len(digest)}"
        assert all(c in "0123456789abcdef" for c in digest), (
            f"{name}: SHA-256 digest must be lowercase hex"
        )

    # Verify digests actually match the content
    expected_html = hashlib.sha256(html_bytes).hexdigest()
    expected_xlsx = hashlib.sha256(xlsx_bytes).hexdigest()
    assert hashes["report_admin.html"] == expected_html
    assert hashes["report_admin.xlsx"] == expected_xlsx


def test_op_07_audit_record_stores_artifact_hashes():
    """O-05: build_audit_record must persist supplied artifact_hashes into the audit record."""
    html_bytes = _OB.export_html(_RUN, role="admin")
    hashes = compute_artifact_hashes({"report_admin.html": html_bytes})

    record = build_audit_record(_RUN, artifact_hashes=hashes)
    assert record["artifact_hashes"] == hashes, (
        "artifact_hashes in audit record must match what was supplied"
    )


# ---------------------------------------------------------------------------
# OP-08 → OP-09  File signatures (O-06)
# ---------------------------------------------------------------------------

def test_op_08_html_output_starts_with_doctype():
    """O-06: export_html output must start with <!DOCTYPE html> for both roles."""
    for role in ("user", "admin"):
        data = _OB.export_html(_RUN, role=role)
        assert data.startswith(b"<!DOCTYPE html>"), (
            f"HTML output for role='{role}' must start with <!DOCTYPE html>"
        )
        assert OutputBuilder.check_file_signature(data, "html"), (
            f"check_file_signature must accept the HTML output for role='{role}'"
        )


def test_op_09_xlsx_output_starts_with_pk_magic():
    """O-06: export_excel output must start with PK magic bytes (valid XLSX/ZIP)."""
    data = _OB.export_excel(_RUN, role="admin")
    assert data[:4] == b"PK\x03\x04", (
        "XLSX output must begin with PK\\x03\\x04 (ZIP local file header)"
    )
    assert OutputBuilder.check_file_signature(data, "xlsx"), (
        "check_file_signature must accept the XLSX output"
    )
